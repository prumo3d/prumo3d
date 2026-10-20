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

import math
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
    if objs and len(objs) == 1:
        # uma peça: a legenda vem das propriedades dela (código, denominação, revisão, material, massa)
        try:
            import PrumoPropriedades
            v.update({k: val for k, val in PrumoPropriedades.legenda_de(objs[0]).items() if val})
            return v
        except Exception:
            pass
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
    if objs and len(objs) == 1:
        try:
            import PrumoPropriedades
            PrumoPropriedades.vincular_folha(page, objs[0])
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: folha ligada à peça: %s\n" % exc)
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


ESPACO_VISTAS = 15.0     # mm entre as vistas na folha (como o espaçamento automático do TechDraw)
FATOR_ISO = 0.6          # a isométrica sai menor que as vistas ortogonais


def _caixa(objs):
    bb = None
    for _o, sh in PrumoUtil.pecas(objs):
        bb = sh.BoundBox if bb is None else bb.united(sh.BoundBox)
    return bb


def _medidas_iso(bb):
    """(largura, altura) aproximadas da isométrica (direção 1,-1,1) em escala 1."""
    w = (bb.XLength + bb.YLength) * math.cos(math.radians(30))
    h = bb.ZLength + (bb.XLength + bb.YLength) * 0.5
    return w, h


def escala_que_cabe(objs, larg_util, alt_util):
    """Maior escala normalizada em que as três vistas e a isométrica cabem lado a lado."""
    bb = _caixa(objs)
    if bb is None:
        return 1.0
    iw, ih = _medidas_iso(bb)
    for e in ESCALAS_NORMAIS:
        # 1º diedro: frontal (X×Z) + lateral (Y×Z) lado a lado; superior (X×Y) embaixo da frontal
        larg = (bb.XLength + bb.YLength + iw * FATOR_ISO) * e + 3 * ESPACO_VISTAS
        alt = max((bb.ZLength + bb.YLength) * e + ESPACO_VISTAS, ih * FATOR_ISO * e)
        if larg <= larg_util and alt <= alt_util:
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
    bb = _caixa(fontes)
    topo = 28.0                               # do alto da folha até o alto das vistas
    if bb is not None:
        fx, fy, fz = bb.XLength * e, bb.YLength * e, bb.ZLength * e
        iw, ih = _medidas_iso(bb)
        iw = iw * e * FATOR_ISO
        # conjunto (vistas + isométrica) centrado na largura útil, entre a margem esquerda (20) e
        # a direita (10) do quadro
        total = fx + ESPACO_VISTAS + fy + 2 * ESPACO_VISTAS + iw
        x0 = 20.0 + max(10.0, ((larg - 30.0) - total) / 2.0)
        grupo.X = x0 + fx / 2.0
        grupo.Y = alt - topo - fz / 2.0
        direita_grupo = x0 + fx + ESPACO_VISTAS + fy
    else:
        grupo.X, grupo.Y, direita_grupo = larg * 0.42, (alt + 60) * 0.55, larg * 0.6
    grupo.AutoDistribute = True
    iso = doc.addObject("TechDraw::DrawViewPart", "Isometrica")
    iso.Label = "Isométrica"
    page.addView(iso)
    iso.Source = fontes
    iso.Direction = FreeCAD.Vector(1, -1, 1)
    iso.XDirection = FreeCAD.Vector(1, 1, 0)
    iso.ScaleType = "Custom"
    iso.Scale = e * FATOR_ISO
    if bb is not None:
        iw, ih = _medidas_iso(bb)
        iw, ih = iw * iso.Scale, ih * iso.Scale
        # à direita das vistas, no alto (longe da legenda)
        iso.X = min(larg - 20.0 - iw / 2.0, direita_grupo + 2 * ESPACO_VISTAS + iw / 2.0)
        iso.Y = alt - topo - ih / 2.0
    else:
        iso.X, iso.Y = larg * 0.80, alt * 0.70
    doc.recompute()
    return grupo


# ============================================================================ diálogo
import PrumoPainel as P

CAMPOS_LEGENDA = (("titulo", "Título", "texto"), ("numero", "Nº do desenho", "quantidade"),
                  ("empresa", "Empresa", "folha"), ("cliente", "Cliente / obra", "folha"),
                  ("material", "Material", "material"), ("tolerancias", "Tolerâncias gerais", "folga"),
                  ("desenhista", "Desenhista", "texto"), ("resp_tecnico", "Responsável técnico", "texto"),
                  ("crea", "CREA / CFT", "texto"), ("art", "ART nº", "quantidade"), ("revisao", "Revisão", "texto"))


def _filtro_pecas(obj, subs):
    return [(obj.Label, obj)] if PrumoUtil.pecas([obj]) else []


class PainelFolha(P.PainelTarefa):
    titulo = "Nova folha ABNT"
    ajuda = "Selecione as peças para as vistas (opcional) e confira a legenda."

    def __init__(self, doc=None, objs=None):
        self.doc = doc or FreeCAD.ActiveDocument
        self._objs_iniciais = list(objs or [])
        super().__init__()

    def montar(self):
        f = self.form
        s0 = f.secao("Peças", "selecao")
        self.pecas = f.caixa(s0, "Peças para as vistas", _filtro_pecas, minimo=0,
                             dica="Peças, corpos, partes ou montagens. Sem peças, a folha sai em branco.")
        for o in self._objs_iniciais:
            self.pecas.aceitar(o)
        s1 = f.secao("Folha", "folha")
        self.formato = s1.linha("folha", P.lista(FORMATOS, FREECAD_PARAM().GetString("FolhaFormato",
                                                                                       FORMATO_PADRAO)),
                                "A0 a A4 (NBR 10068).", "Formato")
        self.retrato = s1.linha("altura", P.marcar("Retrato (folha em pé)"), "Só no A4.")
        self.norma = QtWidgets.QComboBox()
        for k, v in NORMAS.items():
            self.norma.addItem(v, k)
        idx = self.norma.findData(FREECAD_PARAM().GetString("FolhaNorma", NORMA_PADRAO))
        self.norma.setCurrentIndex(max(idx, 0))
        s1.linha("tipo", self.norma, "Modelo de legenda: NBR 16752 (atual) ou NBR 10068.", "Padrão da folha")
        self.formato.currentTextChanged.connect(self._formato)
        self._formato(self.formato.currentText())
        s2 = f.secao("Legenda", "texto")
        valores = campos_padrao(self.doc, self.pecas.valores())
        self.campos = {}
        for chave, rotulo, ic in CAMPOS_LEGENDA:
            self.campos[chave] = s2.linha(ic, QtWidgets.QLineEdit(valores.get(chave, "")), rotulo, rotulo)
        self.massa = valores.get("massa", "")
        s3 = f.secao("Vistas", "posicao")
        self.vistas = s3.linha("posicao", P.marcar("Colocar as vistas (frontal, superior, lateral e "
                                                   "isométrica)", bool(self.pecas.valores())),
                               "Vistas no 1º diedro, na escala normalizada que cabe.")
        self.pecas.mudou.connect(self._pecas_mudaram)

    def _pecas_mudaram(self):
        objs = self.pecas.valores()
        self.vistas.setChecked(bool(objs))
        v = campos_padrao(self.doc, objs)
        self.massa = v.get("massa", "")
        for chave in ("material", "numero", "revisao", "titulo"):
            if v.get(chave) and (not self.campos[chave].text().strip() or chave == "titulo"):
                self.campos[chave].setText(v[chave])

    def _formato(self, f):
        self.retrato.setEnabled(f == "A4")
        self.retrato.setChecked(f == "A4")

    def pendencia(self):
        if self.doc is None:
            return "Abra ou crie um documento."
        return None

    def pronto_texto(self):
        n = len(self.pecas.valores())
        return ("Pronto: folha com as vistas de %d peça(s)." % n) if n and self.vistas.isChecked() \
            else "Pronto: folha em branco (selecione peças para as vistas)."

    def valores(self):
        c = {k: w.text().strip() for k, w in self.campos.items()}
        if self.massa:
            c["massa"] = self.massa
        return c

    @property
    def objs(self):
        return self.pecas.valores()

    def criar(self):
        formato = self.formato.currentText()
        norma = self.norma.currentData()
        FREECAD_PARAM().SetString("FolhaFormato", formato)
        FREECAD_PARAM().SetString("FolhaNorma", norma)
        campos = self.valores()
        lembrar_campos(campos)
        return nova_folha(self.doc, formato, norma, self.retrato.isChecked() if formato == "A4" else False,
                          campos, self.objs if self.vistas.isChecked() and self.objs else None)

    def executar(self):
        page = self.criar()
        QtCore.QTimer.singleShot(0, lambda: _abrir_folha(page))
        return page


def _abrir_folha(page):
    try:
        page.ViewObject.doubleClicked()
    except Exception:
        pass


DialogoFolha = PainelFolha   # nome antigo


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
        PainelFolha(FreeCAD.ActiveDocument).mostrar()
