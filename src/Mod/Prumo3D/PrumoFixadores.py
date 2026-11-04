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
        # tipos adicionais (medidas nominais da norma, todos "a checar")
        for k, t in _cache["d"].get("extra", {}).get("tipos", {}).items():
            TIPOS.setdefault(k, t["nome"])
            NORMA.setdefault(k, t["norma"])
    return _cache["d"]


def _extra(tipo):
    return dados().get("extra", {}).get("tipos", {}).get(tipo)


def _tabela(tipo):
    ex = _extra(tipo)
    return ex["tabela"] if ex else dados()[CHAVE[tipo]]


def diametros(tipo):
    return sorted(_tabela(tipo).keys(), key=lambda m: float(m[1:]))


def medidas(tipo, m):
    md = dict(_tabela(tipo)[m])
    if _extra(tipo):
        md.setdefault("status", "a checar")
    return md


def tem_comprimento(tipo):
    ex = _extra(tipo)
    if ex is None:
        return tipo in ("sextavado", "allen")
    return bool(ex.get("comprimentos")) or tipo == "pem_porca"


def comprimentos(tipo, m):
    ex = _extra(tipo)
    if ex is not None:
        if tipo == "pem_porca":   # comprimento da haste = espessura de chapa (código 00, 0, 1, 2)
            return sorted(ex["tabela"].get(m, {}).get("chapa", {}).values())
        return list(ex.get("comprimentos", {}).get(m, []))
    if tipo not in ("sextavado", "allen"):
        return []
    lst = dados().get("comprimentos", {}).get(m)
    if lst:
        return lst
    return [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100]


def passo(m, tipo=None):
    p = dados().get("passo", {}).get(m)
    if p is None and tipo and _extra(tipo):
        return _tabela(tipo).get(m, {}).get("P")
    return p["valor"] if isinstance(p, dict) else p


def confirmado(tipo, m):
    return medidas(tipo, m).get("status") == "confirmado"


def denominacao(tipo, m, comp=None):
    if tem_comprimento(tipo) and comp:
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
    if tipo in ("arruela", "arruela_larga"):
        anel = Part.makeCylinder(md["d2"] / 2.0, md["h"])
        return anel.cut(Part.makeCylinder(md["d1"] / 2.0, md["h"] + 0.02, FreeCAD.Vector(0, 0, -0.01)))
    return _forma_extra(tipo, md, d, comp)


def _furo(d, altura, z0=-0.01):
    import Part
    return Part.makeCylinder(d / 2.0, altura + 0.02, FreeCAD.Vector(0, 0, z0))


def _forma_extra(tipo, md, d, comp):
    """Formas simplificadas (sem rosca) dos tipos adicionais. Cabeça acima de z = 0."""
    import Part
    V = FreeCAD.Vector
    if comp <= 0 and tipo != "pem_porca":   # sem comprimento informado: o menor da série
        comp = (_extra(tipo) or {}).get("comprimentos", {}).get("M%g" % d, [2 * d])[0]

    def corpo(c):
        return Part.makeCylinder(d / 2.0, c, V(0, 0, -c))
    if tipo == "escareado_allen":
        # cabeça cônica (90°) com o topo em z = 0, entra no escareado: corpo abaixo da cabeça
        k = md["k"]
        cab = Part.makeCone(d / 2.0, md["dk"] / 2.0, k, V(0, 0, -k))
        cab = cab.cut(_hexagono(md["s"], md["t"] + 0.01, -md["t"]))
        return cab.fuse(corpo(comp)).removeSplitter()
    if tipo == "abaulado_allen":
        k, r = md["k"], md["dk"] / 2.0
        esfera = Part.makeSphere((r * r + k * k) / (2 * k), V(0, 0, k - (r * r + k * k) / (2 * k)))
        cab = esfera.common(Part.makeCylinder(r, k))
        cab = cab.cut(_hexagono(md["s"], md["t"] + 0.01, k - md["t"]))
        return cab.fuse(corpo(comp)).removeSplitter()
    if tipo == "panela_phillips":
        k, r = md["k"], md["dk"] / 2.0
        cab = Part.makeCylinder(r, k * 0.75).fuse(Part.makeCone(r, r * 0.8, k * 0.25, V(0, 0, k * 0.75)))
        fenda = Part.makeBox(r * 1.2, d * 0.18, k, V(-r * 0.6, -d * 0.09, k * 0.4))
        cruz = fenda.fuse(fenda.rotated(V(0, 0, 0), V(0, 0, 1), 90))
        return cab.cut(cruz).fuse(corpo(comp)).removeSplitter()
    if tipo == "sem_cabeca":
        # topo em z = 0 (rente à peça); sextavado interno no topo; ponta copo embaixo
        haste = Part.makeCylinder(d / 2.0, comp, V(0, 0, -comp))
        haste = haste.cut(_hexagono(md["s"], md["t"] + 0.01, -md["t"]))
        dz = min(md.get("dz", d * 0.5), d * 0.9)
        copo = Part.makeCone(dz / 2.0, d / 2.0 + 0.01, (d - dz) / 2.0 + 0.01, V(0, 0, -comp - 0.005))
        anel = Part.makeCylinder(d / 2.0 + 1, (d - dz) / 2.0, V(0, 0, -comp)).cut(copo)
        return haste.cut(anel).removeSplitter()
    if tipo in ("porca_baixa", "porca_trava"):
        h = md.get("h", md["m"])
        sx = _hexagono(md["s"], md["m"])
        if h > md["m"]:  # anel de náilon acima do sextavado
            sx = sx.fuse(Part.makeCylinder(md["s"] * 0.47, h - md["m"], V(0, 0, md["m"])))
        return sx.cut(_furo(d, h)).removeSplitter()
    if tipo == "porca_flange":
        fl = Part.makeCone(md["dc"] / 2.0, md["s"] * 0.5, md["m"] * 0.3)
        sx = _hexagono(md["s"], md["m"])
        return sx.fuse(fl).cut(_furo(d, md["m"])).removeSplitter()
    if tipo == "porca_cega":
        # sextavado de altura m, cúpula até a altura total h; furo cego
        sx = _hexagono(md["s"], md["m"])
        r = md["dk"] / 2.0
        cup = Part.makeCylinder(r, md["h"] - md["m"] - r, V(0, 0, md["m"])) if md["h"] - md["m"] > r else None
        z_esf = md["h"] - r
        esf = Part.makeSphere(r, V(0, 0, z_esf)).common(Part.makeCylinder(r, r, V(0, 0, z_esf)))
        sol = sx.fuse(esf)
        if cup is not None:
            sol = sol.fuse(cup)
        return sol.cut(Part.makeCylinder(d / 2.0, md["h"] * 0.75, V(0, 0, -0.01))).removeSplitter()
    if tipo == "pem_porca":
        # cabeça (diâmetro E, altura T) apoiada na chapa; haste (diâmetro C) entra na chapa
        haste = comp or min(md.get("chapa", {"": 1.0}).values())
        cab = Part.makeCylinder(md["E"] / 2.0, md["T"])
        col = Part.makeCylinder(md["C"] / 2.0, haste, V(0, 0, -haste))
        return cab.fuse(col).cut(_furo(d, md["T"] + haste, -haste - 0.01)).removeSplitter()
    if tipo == "pem_pino":
        cab = Part.makeCylinder(md["H"] / 2.0, md["S"] * 0.5)
        return cab.fuse(corpo(comp)).removeSplitter()
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
        dados()
        try:
            atuais = obj.getEnumerationsOfProperty("Tipo") or []
        except Exception:
            atuais = []
        if set(atuais) != set(TIPOS):   # documento antigo: acrescenta os tipos novos, mantendo o escolhido
            escolhido = obj.Tipo if atuais else None
            obj.Tipo = list(TIPOS.keys())
            if escolhido in TIPOS:
                obj.Tipo = escolhido
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
        if tem_comprimento(tipo) and tipo != "pem_porca" and comp <= 0:
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

    def doubleClicked(self, vobj):
        """Duplo clique: abre o painel de fixadores editando este (prévia ao vivo)."""
        FreeCADGui.Selection.clearSelection()
        PainelFixador().editar_objeto(vobj.Object).mostrar()
        return True

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
    import PrumoPainel
    propria = not PrumoPainel.EM_PREVIA["ativa"]   # na prévia, a transação é a do painel
    if propria:
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
    if propria:
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
    previa = True
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
        dados()
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
        if _extra(t):
            txt = "Medidas nominais A CHECAR contra a norma %s (forma simplificada, sem rosca)." % NORMA[t]
        else:
            txt = "Dimensões confirmadas em catálogo/norma." if ok else "Dimensões A CONFERIR (fonte secundária)."
        self.aviso.setText("<span style='color:%s'>%s</span>" % ("#2E8B6A" if ok else "#B5523F", txt))

    def valores(self):
        t = self.tipo.currentData()
        comp = self.comprimento_valido()
        if comp is None:
            raise ValueError("comprimento inválido: %s" % self.comp.currentText())
        return t, self.diam.currentText(), comp, self.material.text().strip()

    def carregar(self, obj):
        i = self.tipo.findData(obj.Tipo)
        if i >= 0:
            self.tipo.setCurrentIndex(i)
        self.diam.setCurrentText(obj.Diametro)
        c = obj.Comprimento.Value if hasattr(obj.Comprimento, "Value") else float(obj.Comprimento)
        if self.comp.isEnabled() and c:
            self.comp.setEditText(fmt_dim(c))
        self.material.setText(obj.Material)

    def props_edicao(self):
        tipo, m, comp, mat = self.valores()
        d = dict(Tipo=tipo, Diametro=m, Comprimento=comp, Material=mat)
        fs = self.furo.valores()
        if fs:
            d["Placement"] = fs[0][1]
        return d

    def aplicar_edicao(self, obj):
        super().aplicar_edicao(obj)
        tipo, m, comp, _mat = self.valores()
        nome = denominacao(tipo, m, comp)
        if obj.Label != nome:
            obj.Label = nome
        return obj

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
