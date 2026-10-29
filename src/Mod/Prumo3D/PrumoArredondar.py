# SPDX-License-Identifier: LGPL-2.1-or-later
"""Arredondamento automático: arredonda de uma vez todas as arestas de um tipo.

Em vez de clicar aresta por aresta, escolhe-se a peça e quais arestas entram:

- vivas convexas (cantos para fora: quebrar canto vivo de chapa, bloco ou fundido);
- côncavas (cantos para dentro: o raio de concordância de fundido, usinado ou solda);
- todas as vivas;

e, se quiser, só as paralelas a X, Y ou Z ou só as retas. Arestas já tangentes (de um arredondamento
anterior, de um furo no cilindro) ficam de fora. Num Corpo do PartDesign vira um Arredondamento normal da
árvore (dá para editar depois); fora dele, um Arredondamento do Part.
"""

import math

import FreeCAD

import PrumoUtil

TIPOS = (("convexas", "Cantos vivos para fora (convexos)"),
         ("concavas", "Cantos para dentro (côncavos)"),
         ("todas", "Todas as arestas vivas"))
DIRECOES = (("", "Qualquer direção"), ("X", "Paralelas a X"), ("Y", "Paralelas a Y"), ("Z", "Paralelas a Z"))
TOL_TANGENTE = 1e-3          # 1 − cos do ângulo entre as faces: abaixo disso a aresta já é lisa
TOL_DIRECAO = 1e-6


# ============================================================================ lógica (sem interface)
def _normal(face, p):
    u, v = face.Surface.parameter(p)
    n = face.normalAt(u, v)
    return FreeCAD.Vector(n)


def _ponto_medio(e):
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)


def classificar(shape):
    """[(nº da aresta a partir de 1, tipo, direção, reta?)] de cada aresta entre duas faces.

    tipo: "convexa", "concava" ou "lisa" (faces tangentes); direção: "X", "Y", "Z" para reta paralela ao
    eixo, "" para as demais."""
    import Part
    res = []
    if shape is None or shape.isNull() or not shape.Solids:
        return res
    solido = shape.Solids[0] if len(shape.Solids) == 1 else shape
    bb = shape.BoundBox
    eps = max(1e-3, 1e-5 * bb.DiagonalLength)
    for i, e in enumerate(shape.Edges, 1):
        faces = shape.ancestorsOfType(e, Part.Face)
        # costura de cilindro ou esfera: a mesma face dos dois lados
        unicas = []
        for f in faces:
            if not any(f.isSame(g) for g in unicas):
                unicas.append(f)
        if len(unicas) != 2 or e.Length < 1e-9:
            continue
        p = _ponto_medio(e)
        try:
            n1, n2 = _normal(unicas[0], p), _normal(unicas[1], p)
        except Exception:
            continue
        reta = isinstance(e.Curve, Part.Line) or e.Curve.TypeId == "Part::GeomLine"
        direcao = ""
        if reta:
            d = e.Vertexes[-1].Point - e.Vertexes[0].Point
            if d.Length > 0:
                d.normalize()
                for nome, eixo in (("X", (1, 0, 0)), ("Y", (0, 1, 0)), ("Z", (0, 0, 1))):
                    if abs(abs(d.dot(FreeCAD.Vector(*eixo))) - 1.0) < TOL_DIRECAO:
                        direcao = nome
        if 1.0 - n1.dot(n2) < TOL_TANGENTE:
            res.append((i, "lisa", direcao, reta))
            continue
        # convexa: o ponto que sai pela face 2 e entra pela face 1 fica fora do sólido
        q = p - n1 * eps + n2 * eps
        try:
            dentro = solido.isInside(q, eps * 1e-3, True)
        except Exception:
            continue
        res.append((i, "concava" if dentro else "convexa", direcao, reta))
    return res


def escolher(shape, tipo="convexas", direcao="", so_retas=False):
    """Nomes ("Edge7") das arestas que o arredondamento automático pega."""
    quer = {"convexas": ("convexa",), "concavas": ("concava",), "todas": ("convexa", "concava")}[tipo]
    r = []
    for i, t, d, reta in classificar(shape):
        if t not in quer:
            continue
        if direcao and d != direcao:
            continue
        if so_retas and not reta:
            continue
        r.append("Edge%d" % i)
    return r


def _alvo(obj):
    """(objeto cuja forma se arredonda, Corpo do PartDesign ou None)."""
    if obj.TypeId == "PartDesign::Body":
        return obj.Tip, obj
    try:
        corpo = obj.getParentGeoFeatureGroup()
    except Exception:
        corpo = None
    if corpo is not None and corpo.TypeId == "PartDesign::Body":
        return corpo.Tip if corpo.Tip is not None else obj, corpo
    return obj, None


def criar(obj, raio, tipo="convexas", direcao="", so_retas=False):
    """Cria o arredondamento e devolve (objeto criado, nº de arestas). Lança ValueError se nada entra."""
    base, corpo = _alvo(obj)
    if base is None or base.Shape.isNull() or not base.Shape.Solids:
        raise ValueError("Escolha uma peça com sólido.")
    if raio <= 0:
        raise ValueError("O raio tem de ser maior que zero.")
    arestas = escolher(base.Shape, tipo, direcao, so_retas)
    if not arestas:
        raise ValueError("Nenhuma aresta desse tipo na peça.")
    doc = base.Document
    if corpo is not None:
        f = corpo.newObject("PartDesign::Fillet", "Arredondamento")
        f.Base = (base, arestas)
        f.Radius = raio
    else:
        f = doc.addObject("Part::Fillet", "Arredondamento")
        f.Base = base
        f.Edges = [(int(a[4:]), raio, raio) for a in arestas]
        try:
            base.Visibility = False
        except Exception:
            pass
    f.Label = "Arredondamento R%s (%s)" % (PrumoUtil.fmt(raio, 2).rstrip("0").rstrip(","),
                                           dict(TIPOS)[tipo].split(" (")[0].lower())
    doc.recompute()
    ok = f.isValid() and not f.Shape.isNull() and f.Shape.isValid()
    if not ok:
        motivo = "raio grande demais para alguma aresta (ou arestas que se cruzam)"
        doc.removeObject(f.Name)
        if corpo is None:
            try:
                base.Visibility = True
            except Exception:
                pass
        doc.recompute()
        raise ValueError("O arredondamento não fechou: %s. Tente um raio menor." % motivo)
    return f, len(arestas)


# ============================================================================ interface
try:
    import FreeCADGui
    from PySide import QtWidgets
    import PrumoPainel as P
except ImportError:
    FreeCADGui = None
    P = None


def _filtro_peca(obj, subs):
    try:
        base, _c = _alvo(obj)
        if base is not None and not base.Shape.isNull() and base.Shape.Solids:
            return [(obj.Label, obj)]
    except Exception:
        pass
    return []


if P is not None:
    class PainelArredondar(P.PainelTarefa):
        titulo = "Arredondamento automático"
        ajuda = ("Escolha a peça, quais arestas entram e o raio: o Prumo arredonda todas de uma vez. As arestas "
                 "escolhidas ficam em destaque na peça.")

        def montar(self):
            f = self.form
            s0 = f.secao("Peça", "selecao")
            self.peca = f.caixa(s0, "Peça", _filtro_peca, minimo=1, maximo=1,
                                dica="Corpo ou sólido. Clique na peça na tela.")
            s1 = f.secao("Arestas", "angulo")
            self.tipo = QtWidgets.QComboBox()
            for k, r in TIPOS:
                self.tipo.addItem(r, k)
            s1.linha("angulo", self.tipo, "Convexas: quebra canto vivo. Côncavas: raio de concordância.",
                     "Quais")
            self.direcao = QtWidgets.QComboBox()
            for k, r in DIRECOES:
                self.direcao.addItem(r, k)
            s1.linha("posicao", self.direcao, "Só as arestas retas paralelas ao eixo.", "Direção")
            self.retas = s1.linha("comprimento", P.marcar("Só arestas retas (deixa os furos e curvas)"), "")
            s2 = f.secao("Raio", "espessura")
            self.raio = QtWidgets.QDoubleSpinBox()
            self.raio.setRange(0.01, 10000.0)
            self.raio.setDecimals(2)
            self.raio.setSuffix(" mm")
            self.raio.setValue(2.0)
            try:
                self.raio.setLocale(P.LOCALE)
            except Exception:
                pass
            s2.linha("espessura", self.raio, "Raio do arredondamento.", "Raio")
            self.contagem = QtWidgets.QLabel("")
            self.contagem.setWordWrap(True)
            s2.linha("info", self.contagem, "")
            for w in (self.tipo, self.direcao):
                w.currentIndexChanged.connect(self.atualizar)
            self.retas.toggled.connect(self.atualizar)

        def escolhidas(self):
            v = self.peca.valores()
            if not v:
                return None, []
            obj = v[0]
            base, _c = _alvo(obj)
            return base, escolher(base.Shape, self.tipo.currentData(), self.direcao.currentData(),
                                  self.retas.isChecked())

        def pendencia(self):
            if not self.peca.valores():
                return "Clique na peça."
            _b, ar = self.escolhidas()
            if not ar:
                return "Nenhuma aresta desse tipo na peça: troque o tipo ou a direção."
            return None

        def atualizar(self, *_a):
            try:
                base, ar = self.escolhidas()
            except Exception:
                base, ar = None, []
            super().atualizar()
            if hasattr(self, "contagem"):
                self.contagem.setText("%d aresta(s) entram." % len(ar) if base is not None else "")
                if base is not None:
                    self._destacar(base, ar)

        def _destacar(self, base, arestas):
            try:
                self._ignorar_selecao = True
                FreeCADGui.Selection.clearSelection()
                if arestas:
                    FreeCADGui.Selection.addSelection(base, arestas)
            except Exception:
                pass
            finally:
                self._ignorar_selecao = False

        def pronto_texto(self):
            return "OK arredonda as arestas em destaque."

        def executar(self):
            obj = self.peca.valores()[0]
            f, n = criar(obj, self.raio.value(), self.tipo.currentData(), self.direcao.currentData(),
                         self.retas.isChecked())
            FreeCAD.Console.PrintMessage("Prumo: %d aresta(s) arredondada(s) com R%s mm.\n"
                                         % (n, PrumoUtil.fmt(self.raio.value(), 2)))
            return [f]

    class CmdArredondarAuto:
        def GetResources(self):
            return {"Pixmap": "PartDesign_Fillet",
                    "MenuText": "Arredondamento automático",
                    "ToolTip": "Arredonda de uma vez todas as arestas de um tipo (cantos vivos para fora, cantos "
                               "para dentro ou todas), se quiser só as paralelas a X, Y ou Z."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelArredondar().mostrar()


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_ArredondarAuto", CmdArredondarAuto())
