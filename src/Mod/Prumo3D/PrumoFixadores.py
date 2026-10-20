# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - peças padronizadas: parafusos, porcas e arruelas métricas.
"""Fixadores métricos (rosca grossa) para inserir no modelo.

- Parafuso cabeça sextavada (ISO 4017, rosca total; ISO 4014, rosca parcial)
- Parafuso cabeça cilíndrica com sextavado interno — "allen" (ISO 4762)
- Porca sextavada (ISO 4032)
- Arruela lisa (ISO 7089)

Dimensões em Resources/fixadores/fixadores.json (gerado por prumo-build/ferramentas/gerar_fixadores.py,
com fonte e situação de cada valor). A rosca é representada pelo diâmetro nominal (sem hélice), como
no desenho simplificado; a profundidade do sextavado interno do allen é representativa (metade da altura
da cabeça).

Com uma aresta circular de furo selecionada, o fixador é colocado no furo: cabeça apoiada na face,
corpo entrando no material.
"""

import json
import math
import os

import FreeCAD
import FreeCADGui

import PrumoUtil
from PrumoUtil import fmt_dim

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets

ARQUIVO = os.path.join(PrumoUtil.RES_DIR, "fixadores", "fixadores.json")
TIPOS = {
    "sextavado": "Parafuso cabeça sextavada",
    "allen": "Parafuso allen (cabeça cilíndrica)",
    "porca": "Porca sextavada",
    "arruela": "Arruela lisa",
}
NORMA = {"sextavado": "ISO 4017", "allen": "ISO 4762", "porca": "ISO 4032", "arruela": "ISO 7089"}
CHAVE = {"sextavado": "iso4017", "allen": "iso4762", "porca": "iso4032", "arruela": "iso7089"}
_cache = {}


def dados():
    if "d" not in _cache:
        with open(ARQUIVO, encoding="utf-8") as fh:
            _cache["d"] = json.load(fh)
    return _cache["d"]


def diametros(tipo):
    tab = dados()[CHAVE[tipo]]
    return sorted(tab.keys(), key=lambda m: float(m[1:]))


def medidas(tipo, m):
    return dados()[CHAVE[tipo]][m]


def comprimentos(tipo, m):
    if tipo not in ("sextavado", "allen"):
        return []
    lst = dados().get("comprimentos", {}).get(m)
    if lst:
        return lst
    return [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100]


def passo(m):
    p = dados().get("passo", {}).get(m)
    return p["valor"] if isinstance(p, dict) else p


def confirmado(tipo, m):
    return medidas(tipo, m).get("status") == "confirmado"


def denominacao(tipo, m, comp=None):
    if tipo in ("sextavado", "allen"):
        return "%s %s %s × %s" % (TIPOS[tipo], NORMA[tipo], m, fmt_dim(comp))
    return "%s %s %s" % (TIPOS[tipo], NORMA[tipo], m)


# ============================================================================ geometria
def _hexagono(s, altura, z0=0.0):
    """Prisma sextavado com distância entre faces s, da cota z0 até z0 + altura."""
    import Part
    r = s / math.sqrt(3.0)  # raio do círculo circunscrito
    pts = [FreeCAD.Vector(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)), z0)
           for i in range(6)]
    f = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return f.extrude(FreeCAD.Vector(0, 0, altura))


def forma(tipo, m, comp=0.0):
    """Forma no sistema local: eixo Z; cabeça acima de z = 0, corpo para baixo (z negativo)."""
    import Part
    md = medidas(tipo, m)
    d = float(m[1:])
    if tipo == "sextavado":
        cab = _hexagono(md["s"], md["k"])
        corpo = Part.makeCylinder(d / 2.0, comp, FreeCAD.Vector(0, 0, -comp))
        return cab.fuse(corpo).removeSplitter()
    if tipo == "allen":
        cab = Part.makeCylinder(md["dk"] / 2.0, md["k"])
        prof = md["k"] / 2.0
        furo = _hexagono(md["s"], prof + 0.01, md["k"] - prof)
        cab = cab.cut(furo)
        corpo = Part.makeCylinder(d / 2.0, comp, FreeCAD.Vector(0, 0, -comp))
        return cab.fuse(corpo).removeSplitter()
    if tipo == "porca":
        h = _hexagono(md["s"], md["m"])
        return h.cut(Part.makeCylinder(d / 2.0, md["m"] + 0.02, FreeCAD.Vector(0, 0, -0.01)))
    if tipo == "arruela":
        anel = Part.makeCylinder(md["d2"] / 2.0, md["h"])
        return anel.cut(Part.makeCylinder(md["d1"] / 2.0, md["h"] + 0.02, FreeCAD.Vector(0, 0, -0.01)))
    raise ValueError(tipo)


class Fixador:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyEnumeration", "Tipo", "Fixador", "Tipo de fixador")
        if not obj.Tipo:
            obj.Tipo = list(TIPOS.keys())
        add("App::PropertyString", "Diametro", "Fixador", "Diâmetro nominal (M6, M8...)")
        add("App::PropertyLength", "Comprimento", "Fixador", "Comprimento do corpo (parafusos)")
        add("App::PropertyString", "Norma", "Fixador", "Norma dimensional", True)
        add("App::PropertyString", "Denominacao", "Fixador", "Descrição para a lista de materiais", True)
        add("App::PropertyString", "Material", "Fixador", "Material / classe (ex.: aço classe 8.8)")
        add("App::PropertyString", "SituacaoDados", "Fixador", "Confirmado ou a conferir", True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        tipo, m = obj.Tipo, obj.Diametro
        if m not in diametros(tipo):
            raise ValueError("diâmetro %s não existe para %s" % (m, TIPOS[tipo]))
        comp = obj.Comprimento.Value
        if tipo in ("sextavado", "allen") and comp <= 0:
            raise ValueError("informe o comprimento do parafuso")
        pl = obj.Placement
        sh = forma(tipo, m, comp)
        obj.Shape = sh
        obj.Placement = pl
        obj.Norma = NORMA[tipo]
        obj.Denominacao = denominacao(tipo, m, comp)
        obj.SituacaoDados = "confirmado" if confirmado(tipo, m) else "a conferir"

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VPFixador:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        return PrumoUtil.icone("fixador.svg")

    def dumps(self):
        return None

    def loads(self, state):
        return None


def posicao_no_furo(obj, nome_aresta):
    """Placement que apoia o fixador na face do furo, com o corpo entrando no material.

    Retorna (placement, diâmetro do furo) ou (None, None) se a aresta não for circular."""
    import Part
    # nome_aresta pode ser um caminho ("Parte.Corpo.Edge3", seleção não resolvida): a forma vem
    # posicionada no espaço global, com as posições dos contêineres e vínculos
    prefixo, _p, elemento = nome_aresta.rpartition(".")
    if prefixo:
        prefixo += "."
    try:
        sh = Part.getShape(obj, prefixo, transform=True)
        e = sh.getElement(elemento)
    except Exception:
        return None, None
    if not hasattr(e, "Curve") or e.Curve.__class__.__name__ != "Circle":
        return None, None
    centro = e.Curve.Center
    eixo = FreeCAD.Vector(e.Curve.Axis).normalize()
    # face plana que contém a aresta: a normal para fora dá o lado da cabeça
    saida = None
    for f in sh.ancestorsOfType(e, Part.Face):
        if f.Surface.__class__.__name__ == "Plane":
            u0, u1, v0, v1 = f.ParameterRange
            n = f.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
            saida = FreeCAD.Vector(n).normalize()
            break
    if saida is None:
        # sem face plana: usa o eixo do círculo
        saida = eixo
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), saida)
    return FreeCAD.Placement(centro, rot), 2.0 * e.Curve.Radius


def diametro_para_furo(diam_furo):
    """Maior rosca que passa no furo (furo ≥ diâmetro nominal)."""
    opcoes = [m for m in diametros("sextavado") if float(m[1:]) <= diam_furo + 1e-6]
    return opcoes[-1] if opcoes else diametros("sextavado")[0]


def criar(doc, tipo, m, comp=0.0, placement=None, material=""):
    doc.openTransaction("Inserir fixador")
    o = doc.addObject("Part::FeaturePython", "Fixador")
    Fixador(o)
    o.Tipo = tipo
    o.Diametro = m
    o.Comprimento = comp
    o.Material = material
    if placement is not None:
        o.Placement = placement
    if FreeCAD.GuiUp:
        VPFixador(o.ViewObject)
        try:
            mat = FreeCAD.Material()
            mat.DiffuseColor = (0.62, 0.64, 0.66)
            o.ViewObject.ShapeAppearance = [mat]
        except Exception:
            pass
    doc.recompute()
    o.Label = denominacao(tipo, m, comp)
    doc.commitTransaction()
    return o


# ============================================================================ interface
import PrumoPainel as P


def _filtro_furo(obj, subs):
    """Aresta circular de um furo → (texto, (placement, diâmetro sugerido))."""
    res = []
    for n in subs:
        if not n.rpartition(".")[2].startswith("Edge"):
            continue
        try:
            pl, furo = posicao_no_furo(obj, n)
        except Exception:
            pl = None
        if pl is not None:
            r = getattr(furo, "Radius", 0.0) if furo is not None else 0.0
            res.append(("Furo ⌀%s mm em %s" % (fmt_dim(2 * r) if r else "?", obj.Label),
                        (n, pl, diametro_para_furo(furo))))
    return res


_filtro_furo.caminho_completo = True   # precisa do caminho: posição dos contêineres e vínculos


class PainelFixador(P.PainelTarefa):
    titulo = "Peças padronizadas"
    ajuda = "Escolha o fixador. Para encaixar num furo, selecione a aresta do furo (opcional)."

    def __init__(self, diam_sugerido=None):
        self._sugerido = diam_sugerido
        super().__init__()

    def montar(self):
        f = self.form
        s0 = f.secao("Furo (opcional)", "furo")
        self.furo = f.caixa(s0, "Aresta do furo", _filtro_furo, minimo=0, maximo=1,
                            dica="Clique na borda circular do furo: o fixador vai para o furo, com a rosca "
                                 "sugerida pelo diâmetro.")
        s1 = f.secao("Fixador", "parafuso")
        self.tipo = QtWidgets.QComboBox()
        for k, v in TIPOS.items():
            self.tipo.addItem("%s (%s)" % (v, NORMA[k]), k)
        s1.linha("tipo", self.tipo, "Parafuso sextavado, allen, porca ou arruela, conforme a norma.", "Tipo")
        self.diam = s1.linha("furo", QtWidgets.QComboBox(), "Rosca métrica grossa.", "Rosca")
        self.comp = s1.linha("comprimento", QtWidgets.QComboBox(), "Comprimento nominal (da cabeça à ponta, "
                             "no sextavado e no allen). Pode digitar.", "Comprimento (mm)")
        self.comp.setEditable(True)
        self.material = s1.linha("material", QtWidgets.QLineEdit(
            FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialFixador", "")),
            "Classe e acabamento (vai para a lista de materiais).", "Material")
        self.material.setPlaceholderText("ex.: aço classe 8.8, zincado")
        self.aviso = s1.texto("")
        self.tipo.currentIndexChanged.connect(self._tipo)
        self.diam.currentIndexChanged.connect(self._diam)
        self._tipo()

    def atualizar(self):
        fs = self.furo.valores() if hasattr(self, "furo") else []
        if fs and fs[0][2] and self.diam.currentText() != fs[0][2]:
            i = self.diam.findText(fs[0][2])
            if i >= 0:
                self.diam.setCurrentIndex(i)
        super().atualizar()

    def pendencia(self):
        if self.comprimento_valido() is None:
            return "Comprimento inválido: informe um número em mm, maior que zero."
        return None

    def pronto_texto(self):
        return "Pronto: o fixador vai %s." % ("para o furo selecionado" if self.furo.valores()
                                               else "para a origem (sem furo selecionado)")

    def comprimento_valido(self):
        """Comprimento digitado (mm) ou None se inválido (vazio, texto, ≤ 0 ou acima de 10·d + 100)."""
        if not self.comp.isEnabled():
            return 0.0
        txt = self.comp.currentText().strip().replace(" ", "").replace(",", ".")
        try:
            v = float(txt)
        except ValueError:
            return None
        if not math.isfinite(v) or v <= 0:
            return None
        try:
            d = float(self.diam.currentText()[1:])
        except ValueError:
            d = 0.0
        if d and v > 10 * d + 100:
            return None
        return v

    def _tipo(self, *_a):
        t = self.tipo.currentData()
        atual = self.diam.currentText() or self._sugerido or "M8"
        self.diam.blockSignals(True)
        self.diam.clear()
        self.diam.addItems(diametros(t))
        i = self.diam.findText(atual)
        self.diam.setCurrentIndex(i if i >= 0 else 0)
        self.diam.blockSignals(False)
        self._diam()

    def _diam(self, *_a):
        t, m = self.tipo.currentData(), self.diam.currentText()
        self.comp.clear()
        lst = comprimentos(t, m)
        self.comp.setEnabled(bool(lst))
        self.comp.addItems([fmt_dim(x) for x in lst])
        if lst:
            self.comp.setCurrentIndex(min(len(lst) - 1, len(lst) // 3))
        if not m:
            return
        md = medidas(t, m)
        ok = md.get("status") == "confirmado"
        self.aviso.setText("<span style='color:%s'>%s</span>" % (
            "#2E8B6A" if ok else "#B5523F",
            "Dimensões confirmadas em catálogo/norma." if ok else "Dimensões A CONFERIR (fonte secundária)."))

    def valores(self):
        t = self.tipo.currentData()
        comp = self.comprimento_valido()
        if comp is None:
            raise ValueError("comprimento inválido: %s" % self.comp.currentText())
        return t, self.diam.currentText(), comp, self.material.text().strip()

    def executar(self):
        tipo, m, comp, mat = self.valores()
        FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimoMaterialFixador", mat)
        fs = self.furo.valores()
        pl = fs[0][1] if fs else None
        return criar(FreeCAD.ActiveDocument, tipo, m, comp, pl, mat)


DialogoFixador = PainelFixador   # nome antigo


class CmdFixador:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("fixador.svg"),
                "MenuText": "Parafuso, porca, arruela",
                "ToolTip": "Insere parafusos (sextavado ISO 4017, allen ISO 4762), porcas (ISO 4032) e arruelas "
                           "(ISO 7089). Com a aresta de um furo selecionada, coloca o fixador no furo."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelFixador().mostrar()
