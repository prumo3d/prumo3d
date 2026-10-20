# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - folhas de desenho ABNT (A0 a A4) e criação de folha com vistas e legenda preenchida.
"""Folhas de desenho no padrão brasileiro.

Modelos em Resources/folhas, gerados por prumo-build/ferramentas/gerar_folhas_abnt.py:
- NBR 16752 (vigente; dimensões da ISO 5457: margem esquerda 20 mm, demais 10 mm, legenda 180 mm);
- NBR 10068 (padrão anterior, ainda comum: margem esquerda 25 mm, legenda 175/178 mm).
A0 a A3 em paisagem; A4 em retrato (e paisagem). Legenda com empresa, cliente/obra, título,
material, massa, tolerâncias gerais, desenhista, verificado, aprovado, data, responsável técnico,
CREA/CFT, ART, escala, unidade, 1º diedro, formato, folha, número do desenho e revisão.
"""

import os
import time

import FreeCAD
import FreeCADGui

import PrumoUtil

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets

DIR_FOLHAS = os.path.join(PrumoUtil.RES_DIR, "folhas")
FORMATOS = ["A0", "A1", "A2", "A3", "A4"]
NORMAS = {"NBR16752": "ABNT NBR 16752 (atual)", "NBR10068": "ABNT NBR 10068 (anterior)"}
NORMA_PADRAO = "NBR16752"
FORMATO_PADRAO = "A3"

CAMPOS = ["empresa", "cliente", "titulo", "material", "massa", "tolerancias", "desenhista",
          "verificado", "aprovado", "data", "resp_tecnico", "crea", "art", "escala", "unidade",
          "formato", "folha", "numero", "revisao"]


def arquivo(formato, norma=NORMA_PADRAO, retrato=None):
    if retrato is None:
        retrato = formato == "A4"
    nome = "Prumo_%s_%s_%s.svg" % (formato, "Retrato" if retrato else "Paisagem", norma)
    return os.path.join(DIR_FOLHAS, nome)


def lista_modelos():
    if not os.path.isdir(DIR_FOLHAS):
        return []
    return sorted(os.path.join(DIR_FOLHAS, n) for n in os.listdir(DIR_FOLHAS) if n.endswith(".svg"))


def aplicar_preferencias(forcar=False):
    """Faz do modelo ABNT A3 (NBR 16752) o padrão do Desenho técnico.

    Só muda na primeira vez (ou se a preferência aponta para um arquivo que não existe), para
    respeitar a escolha do usuário depois."""
    g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
    f = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Files")
    atual = f.GetString("TemplateFile", "")
    padrao = arquivo(FORMATO_PADRAO)
    if not os.path.isfile(padrao):
        return False
    if forcar or not g.GetBool("FolhasABNTAplicadas", False) or (atual and not os.path.isfile(atual)):
        f.SetString("TemplateFile", padrao)
        f.SetString("TemplateDir", DIR_FOLHAS)
        g.SetBool("FolhasABNTAplicadas", True)
        # 1º diedro, como na prática brasileira
        FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/General").SetInt("ProjectionAngle", 0)
        return True
    return False


def campos_padrao(doc, objs=None):
    """Valores iniciais da legenda a partir do documento e das peças selecionadas."""
    v = {"data": time.strftime("%d/%m/%Y"), "unidade": "mm", "revisao": "0",
         "titulo": doc.Label if doc else "", "empresa": getattr(doc, "Company", "") or "",
         "desenhista": getattr(doc, "CreatedBy", "") or "", "folha": "1 / 1"}
    g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
    for chave in ("empresa", "resp_tecnico", "crea", "tolerancias"):
        salvo = g.GetString("Folha_" + chave, "")
        if salvo and not v.get(chave):
            v[chave] = salvo
    if objs:
        try:
            import PrumoMassa
            r = PrumoMassa.calcular(objs)
            if r.massa > 0:
                v["massa"] = PrumoUtil.fmt(r.massa, 3)
            mats = {it[1] for it in r.itens if it[5]}
            if len(mats) == 1:
                v["material"] = mats.pop()
        except Exception:
            pass
    return v


def lembrar_campos(campos):
    """Guarda empresa, responsável técnico, CREA e tolerâncias para as próximas folhas."""
    g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
    for chave in ("empresa", "resp_tecnico", "crea", "tolerancias"):
        if campos.get(chave):
            g.SetString("Folha_" + chave, campos[chave])


def nova_folha(doc, formato=FORMATO_PADRAO, norma=NORMA_PADRAO, retrato=None, campos=None,
               objs=None, escala=None):
    """Cria a folha com o modelo ABNT e a legenda preenchida. Com `objs`, coloca as vistas
    (frontal, superior e lateral no 1º diedro) e a isométrica. Retorna a folha."""
    caminho = arquivo(formato, norma, retrato)
    if not os.path.isfile(caminho):
        raise FileNotFoundError(caminho)
    doc.openTransaction("Nova folha ABNT")
    page = doc.addObject("TechDraw::DrawPage", "Folha")
    page.Label = "Folha %s" % formato
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Modelo")
    tpl.Label = "Modelo %s %s" % (formato, NORMAS[norma].split(" (")[0])
    tpl.Template = caminho
    page.Template = tpl
    doc.recompute()
    valores = campos_padrao(doc, objs)
    valores["formato"] = formato
    if campos:
        valores.update({k: v for k, v in campos.items() if v is not None})
    if escala:
        page.Scale = escala
        valores["escala"] = _texto_escala(escala)
    et = dict(tpl.EditableTexts)
    for k, val in valores.items():
        if k in et:
            et[k] = str(val)
    tpl.EditableTexts = et
    if objs:
        _vistas(doc, page, objs, escala)
        valores["escala"] = _texto_escala(page.Scale)
        et = dict(tpl.EditableTexts)
        et["escala"] = valores["escala"]
        tpl.EditableTexts = et
    doc.recompute()
    doc.commitTransaction()
    return page


def _texto_escala(e):
    if e >= 1:
        n = round(e, 2)
        return ("%g:1" % n).replace(".", ",")
    return ("1:%g" % round(1.0 / e, 2)).replace(".", ",")


# série 1-2-5 (ISO 5455 / NBR 8196): ampliação, natural e redução
ESCALAS_NORMAIS = [50, 20, 10, 5, 2, 1, 1 / 2.0, 1 / 5.0, 1 / 10.0, 1 / 20.0, 1 / 50.0,
                   1 / 100.0, 1 / 200.0, 1 / 500.0, 1 / 1000.0]


def escala_que_cabe(objs, larg_util, alt_util):
    """Maior escala normalizada em que três vistas (frontal, superior, lateral) cabem."""
    import Part
    bb = None
    for o, sh in PrumoUtil.pecas(objs):
        bb = sh.BoundBox if bb is None else bb.united(sh.BoundBox)
    if bb is None:
        return 1.0
    # 1º diedro: frontal (X×Z) + lateral (Y×Z) lado a lado; superior (X×Y) embaixo da frontal
    larg = bb.XLength + bb.YLength
    alt = bb.ZLength + bb.YLength
    for e in ESCALAS_NORMAIS:
        if larg * e * 1.45 <= larg_util and alt * e * 1.45 <= alt_util:
            return e
    return ESCALAS_NORMAIS[-1]


def _vistas(doc, page, objs, escala=None):
    fontes = [o for o, _sh in PrumoUtil.pecas(objs)]
    fontes = list(dict.fromkeys(objs if objs else fontes))
    try:
        larg = float(page.Template.Width)
        alt = float(page.Template.Height)
    except Exception:
        larg, alt = 420.0, 297.0
    larg_util, alt_util = larg - 30, alt - 20 - 60  # tira margens e a legenda
    e = escala or escala_que_cabe(fontes, larg_util, alt_util)
    page.Scale = e
    grupo = doc.addObject("TechDraw::DrawProjGroup", "Vistas")
    grupo.Label = "Vistas"
    page.addView(grupo)
    grupo.Source = fontes
    grupo.ProjectionType = "First angle"
    grupo.ScaleType = "Page"
    grupo.addProjection("Front")
    grupo.addProjection("Top")
    grupo.addProjection("Left")   # no 1º diedro a vista lateral esquerda fica à direita da frontal
    grupo.X = larg * 0.42
    grupo.Y = (alt + 60) * 0.55
    grupo.AutoDistribute = True
    iso = doc.addObject("TechDraw::DrawViewPart", "Isometrica")
    iso.Label = "Isométrica"
    page.addView(iso)
    iso.Source = fontes
    iso.Direction = FreeCAD.Vector(1, -1, 1)
    iso.XDirection = FreeCAD.Vector(1, 1, 0)
    iso.ScaleType = "Custom"
    iso.Scale = e * 0.6
    iso.X = larg * 0.80
    iso.Y = alt * 0.70
    doc.recompute()
    return grupo


# ============================================================================ diálogo
class DialogoFolha(QtWidgets.QDialog):
    def __init__(self, doc, objs, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.objs = objs
        self.setWindowTitle("Nova folha ABNT")
        lay = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.formato = QtWidgets.QComboBox()
        self.formato.addItems(FORMATOS)
        self.formato.setCurrentText(FREECAD_PARAM().GetString("FolhaFormato", FORMATO_PADRAO))
        self.retrato = QtWidgets.QCheckBox("Retrato (folha em pé)")
        self.norma = QtWidgets.QComboBox()
        for k, v in NORMAS.items():
            self.norma.addItem(v, k)
        idx = self.norma.findData(FREECAD_PARAM().GetString("FolhaNorma", NORMA_PADRAO))
        self.norma.setCurrentIndex(max(idx, 0))
        self.formato.currentTextChanged.connect(self._formato)
        self._formato(self.formato.currentText())
        form.addRow("Formato", self.formato)
        form.addRow("", self.retrato)
        form.addRow("Padrão da folha", self.norma)
        valores = campos_padrao(doc, objs)
        self.campos = {}
        for chave, rotulo in (("titulo", "Título"), ("numero", "Nº do desenho"), ("empresa", "Empresa"),
                              ("cliente", "Cliente / obra"), ("material", "Material"),
                              ("tolerancias", "Tolerâncias gerais"), ("desenhista", "Desenhista"),
                              ("resp_tecnico", "Responsável técnico"), ("crea", "CREA / CFT"),
                              ("art", "ART nº"), ("revisao", "Revisão")):
            w = QtWidgets.QLineEdit(valores.get(chave, ""))
            self.campos[chave] = w
            form.addRow(rotulo, w)
        self.massa = valores.get("massa", "")
        self.vistas = QtWidgets.QCheckBox("Colocar as vistas (frontal, superior, lateral e isométrica)")
        self.vistas.setChecked(bool(objs))
        self.vistas.setEnabled(bool(objs))
        lay.addLayout(form)
        lay.addWidget(self.vistas)
        if not objs:
            dica = QtWidgets.QLabel("Selecione peças antes de abrir para já colocar as vistas.")
            dica.setStyleSheet("color:#5B6876")
            lay.addWidget(dica)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Criar folha")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _formato(self, f):
        self.retrato.setEnabled(f == "A4")
        self.retrato.setChecked(f == "A4")

    def valores(self):
        c = {k: w.text().strip() for k, w in self.campos.items()}
        if self.massa:
            c["massa"] = self.massa
        return c

    def criar(self):
        formato = self.formato.currentText()
        norma = self.norma.currentData()
        FREECAD_PARAM().SetString("FolhaFormato", formato)
        FREECAD_PARAM().SetString("FolhaNorma", norma)
        campos = self.valores()
        lembrar_campos(campos)
        return nova_folha(self.doc, formato, norma, self.retrato.isChecked() if formato == "A4" else False,
                          campos, self.objs if self.vistas.isChecked() else None)


def FREECAD_PARAM():
    return FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)


class CmdNovaFolha:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"),
                "MenuText": "Nova folha ABNT",
                "ToolTip": "Folha de desenho A0 a A4 no padrão ABNT (NBR 16752 ou NBR 10068), com a "
                           "legenda preenchida e, se houver peças selecionadas, as vistas no 1º diedro."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        try:
            import TechDraw  # noqa: F401
            import TechDrawGui  # noqa: F401
        except ImportError:
            pass
        doc = FreeCAD.ActiveDocument
        objs = [o for o in FreeCADGui.Selection.getSelection() if PrumoUtil.pecas([o])]
        d = DialogoFolha(doc, objs, FreeCADGui.getMainWindow())
        if d.exec():
            page = d.criar()
            try:
                page.ViewObject.doubleClicked()
            except Exception:
                pass
