# SPDX-License-Identifier: LGPL-2.1-or-later
"""Propriedades da peça (como as "propriedades personalizadas" do SolidWorks).

Cada peça (corpo, parte, sólido) pode guardar código, denominação, revisão, acabamento e
observação. Esses dados, mais o material e a massa calculada, alimentam:
- a lista de materiais (colunas Código, Denominação, Material, Massa, Observação);
- a legenda da folha ABNT: uma folha criada para uma peça fica ligada a ela e a legenda
  (título, nº do desenho, revisão, material, massa) acompanha quando a peça muda.
"""

import FreeCAD
import FreeCADGui

import PrumoUtil

GRUPO = "Identificação"
CAMPOS = (("Codigo", "Código", "quantidade", "Código ou número da peça (vai para a lista de materiais e o nº "
                                               "do desenho)"),
          ("Denominacao", "Denominação", "texto", "Nome da peça na lista de materiais e no título da folha"),
          ("Revisao", "Revisão", "texto", "Revisão do desenho (0, A, 1...)"),
          ("Acabamento", "Acabamento", "material", "Pintura, zincagem, polimento..."),
          ("Observacao", "Observação", "texto", "Observação livre na lista de materiais"))
ACOMPANHADAS = ("Codigo", "Denominacao", "Revisao", "ShapeMaterial", "Label", "Shape")


def garantir(obj):
    """Cria as propriedades que faltarem (grupo Identificação). Retorna o objeto."""
    for nome, rotulo, _ic, dica in CAMPOS:
        if nome not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", nome, GRUPO, dica)
    return obj


def ler(obj, nome, padrao=""):
    try:
        v = getattr(obj, nome) if nome in obj.PropertiesList else ""
    except Exception:
        v = ""
    return v if v not in (None, "") else padrao


def massa(obj):
    try:
        import PrumoMassa
        r = PrumoMassa.calcular([obj])
        return r.massa
    except Exception:
        return 0.0


def material(obj):
    nome, _dens, definido = PrumoUtil.material(obj)
    return nome if definido else ""


def legenda_de(obj):
    """Campos da legenda da folha a partir da peça."""
    v = {"titulo": ler(obj, "Denominacao", obj.Label).upper(), "numero": ler(obj, "Codigo"),
         "revisao": ler(obj, "Revisao", "0")}
    mat = material(obj)
    if mat:
        v["material"] = mat
    m = massa(obj)
    if m > 0:
        v["massa"] = PrumoUtil.fmt(m, 3)
    return v


# ------------------------------------------------------------------ folha ligada à peça
def vincular_folha(page, obj):
    if "PrumoPeca" not in page.PropertiesList:
        page.addProperty("App::PropertyLink", "PrumoPeca", "Prumo",
                         "Peça desta folha: a legenda acompanha código, denominação, revisão, material e massa")
    if "LegendaAutomatica" not in page.PropertiesList:
        page.addProperty("App::PropertyBool", "LegendaAutomatica", "Prumo",
                         "A legenda acompanha as propriedades da peça")
        page.LegendaAutomatica = True
    page.PrumoPeca = obj
    return page


def atualizar_legenda(page):
    """Copia os dados da peça ligada para a legenda. Retorna True se mudou algo."""
    try:
        obj = page.PrumoPeca if "PrumoPeca" in page.PropertiesList else None
        if obj is None or not getattr(page, "LegendaAutomatica", False) or page.Template is None:
            return False
        tpl = page.Template
        et = dict(tpl.EditableTexts)
        novo = dict(et)
        for k, val in legenda_de(obj).items():
            if k in novo:
                novo[k] = str(val)
        if novo != et:
            tpl.EditableTexts = novo
            return True
    except Exception as exc:
        if "deleted" not in str(exc):
            FreeCAD.Console.PrintLog("Prumo: legenda automática: %s\n" % exc)
    return False


def folhas_da_peca(obj):
    doc = obj.Document
    res = []
    for p in doc.Objects:
        if p.TypeId == "TechDraw::DrawPage" and "PrumoPeca" in p.PropertiesList:
            alvo = p.PrumoPeca
            if alvo is obj or (alvo is not None and obj in getattr(alvo, "OutListRecursive", [])):
                res.append(p)
    return res


class Observador:
    """Quando a peça muda, a legenda das folhas ligadas a ela acompanha (depois do recálculo)."""

    def __init__(self):
        self._pendentes = set()

    def slotChangedObject(self, obj, prop):
        if prop not in ACOMPANHADAS:
            return
        try:
            doc = obj.Document
            if doc.Restoring:
                return
            folhas = folhas_da_peca(obj)
        except Exception:
            return
        for p in folhas:
            chave = (doc.Name, p.Name)
            if chave in self._pendentes:
                continue
            self._pendentes.add(chave)
            try:
                from PySide import QtCore
                QtCore.QTimer.singleShot(0, lambda c=chave: self._aplicar(c))
            except Exception:
                self._aplicar(chave)

    def _aplicar(self, chave):
        self._pendentes.discard(chave)
        try:
            p = FreeCAD.getDocument(chave[0]).getObject(chave[1])
        except Exception:
            return
        if p is not None:
            atualizar_legenda(p)


_estado = {"obs": None}


def install():
    if _estado["obs"] is None:
        _estado["obs"] = Observador()
        FreeCAD.addDocumentObserver(_estado["obs"])
    return _estado["obs"]


# ------------------------------------------------------------------ painel
def _filtro_peca(obj, subs):
    return [(obj.Label, obj)] if PrumoUtil.pecas([obj]) else []


def materiais_prumo():
    """[(nome, uuid)] da biblioteca Prumo, em ordem alfabética."""
    try:
        import Materials
        mm = Materials.MaterialManager()
        lst = [(m.Name, u) for u, m in mm.Materials.items() if m.LibraryName == "Prumo"]
        return sorted(lst, key=lambda x: x[0].lower())
    except Exception:
        return []


def definir_material(obj, uuid):
    import Materials
    mat = Materials.MaterialManager().getMaterial(uuid)
    alvo = obj.LinkedObject if obj.TypeId == "App::Link" and obj.LinkedObject is not None else obj
    if "ShapeMaterial" not in alvo.PropertiesList:
        raise ValueError("%s não aceita material" % alvo.Label)
    alvo.ShapeMaterial = mat
    return mat


def _painel():
    import PrumoPainel as P
    from PySide import QtWidgets

    class PainelPropriedades(P.PainelTarefa):
        titulo = "Propriedades da peça"
        ajuda = "Escolha a peça. Os dados vão para a lista de materiais e para a legenda da folha."

        def montar(self):
            f = self.form
            s0 = f.secao("Peça", "selecao")
            self.peca = f.caixa(s0, "Peça", _filtro_peca, minimo=1, maximo=1)
            s1 = f.secao("Identificação", "texto")
            self.campos = {}
            for nome, rotulo, ic, dica in CAMPOS:
                self.campos[nome] = s1.linha(ic, QtWidgets.QLineEdit(), dica, rotulo)
            s2 = f.secao("Material e massa", "material")
            self.material = QtWidgets.QComboBox()
            self.material.addItem("(manter)", "")
            for nome, uuid in materiais_prumo():
                self.material.addItem(nome, uuid)
            s2.linha("material", self.material, "Material da biblioteca Prumo (usado na massa, na lista de "
                     "materiais e na simulação).", "Material")
            self.lb_massa = s2.texto("")
            self.peca.mudou.connect(self._carregar)

        def _carregar(self):
            vs = self.peca.valores()
            if not vs:
                return
            o = vs[0]
            for nome, w in self.campos.items():
                w.setText(ler(o, nome))
            if not self.campos["Denominacao"].text():
                self.campos["Denominacao"].setPlaceholderText(o.Label)
            mat = material(o)
            self.lb_massa.setText("Material atual: %s · massa: %s kg" % (mat or "não definido (aço)",
                                                                          PrumoUtil.fmt(massa(o), 3)))

        def executar(self):
            o = self.peca.valores()[0]
            garantir(o)
            for nome, w in self.campos.items():
                setattr(o, nome, w.text().strip())
            uuid = self.material.currentData()
            if uuid:
                definir_material(o, uuid)
            o.Document.recompute()
            for p in folhas_da_peca(o):
                atualizar_legenda(p)
            return o

    return PainelPropriedades


def PainelPropriedades():
    return _painel()()


class CmdPropriedades:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("massa.svg"), "MenuText": "Propriedades da peça",
                "ToolTip": "Código, denominação, revisão, acabamento e material da peça. Alimentam a lista de "
                           "materiais e a legenda da folha (que acompanha as mudanças)."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelPropriedades().mostrar()
