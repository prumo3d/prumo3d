# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - complementos da estrutura soldada: reforços, tampas, placas de base e cordões de solda.
"""Complementos paramétricos das barras da estrutura soldada.

- Reforço (mão-francesa / gusset): chapa triangular ou poligonal no canto entre duas barras,
  apoiada nas faces internas, com chanfro para a solda e posição (centro, frente, trás).
- Tampa de extremidade: fecha a ponta de tubo redondo ou quadrado, por fora ou por dentro,
  com folga para a solda.
- Placa de base (sapata): chapa na ponta da barra, com furação.
- Cordão de solda: segue as linhas de contato entre as peças escolhidas; guarda a perna do
  filete, o processo e o eletrodo, e calcula comprimento, volume e massa de metal depositado.

Os três primeiros entram na lista de materiais como chapas (com denominação e espessura); os
cordões vão para a lista de soldas.
"""

import math

import FreeCAD
import FreeCADGui

import PrumoEstrutura as E
import PrumoPerfis
import PrumoUtil
from PrumoUtil import fmt, fmt_dim

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets

DENSIDADE_ACO = 7850.0  # kg/m³ (metal depositado: aço carbono)
PONTAS = ["Início", "Fim"]
POSICOES = ["Centro", "Frente", "Trás"]
TIPOS_REFORCO = ["Triangular", "Poligonal"]
TIPOS_TAMPA = ["Externa", "Interna"]
PROCESSOS = ["SMAW (eletrodo revestido)", "GMAW (MIG/MAG)", "FCAW (arame tubular)", "GTAW (TIG)",
             "SAW (arco submerso)"]


# ============================================================================ geometria comum
def _contexto(barra):
    """(estrutura, arestas, normal do esqueleto, seção) da barra."""
    est = barra.Estrutura
    if est is None or est.Esqueleto is None:
        raise ValueError("%s não pertence a uma estrutura" % barra.Label)
    eds = E.arestas(est.Esqueleto)
    if barra.Indice >= len(eds):
        raise ValueError("%s não tem mais linha no esqueleto" % barra.Label)
    normal = E._normal_esqueleto(eds)
    return est, eds, normal, E.Secao(est, eds, barra.Indice, normal)


def ponta(barra, k):
    """Ponta k (0 = início, 1 = fim) da barra já cortada.

    Retorna (ponto no eixo da linha na face da ponta, direção para fora, seção, ângulo do corte)."""
    est, eds, normal, sec = _contexto(barra)
    e = eds[barra.Indice]
    if not E._reta(e):
        raise ValueError("ponta de barra curva não é suportada")
    t = E._dir(e, True)
    p0 = e.valueAt(e.FirstParameter)
    proj = [(v.Point - p0).dot(t) for v in barra.Shape.Vertexes]
    if not proj:
        raise ValueError("%s ainda não tem forma" % barra.Label)
    s = min(proj) if k == 0 else max(proj)
    fora = t * (-1 if k == 0 else 1)
    ang = barra.CorteInicio.Value if k == 0 else barra.CorteFim.Value
    return p0 + t * s, fora, sec, ang


def no_entre(bA, bB):
    """Nó entre duas barras: (ponto, direção a para dentro de A, direção b para dentro de B).

    Vale para canto (pontas comuns) e para T (ponta de uma no meio da outra; a direção da que
    passa segue o sentido da linha dela)."""
    _est, eds, _n, _s = _contexto(bA)
    eA, eB = eds[bA.Indice], eds[bB.Indice]
    pontasA = [(eA.valueAt(eA.FirstParameter), True), (eA.valueAt(eA.LastParameter), False)]
    pontasB = [(eB.valueAt(eB.FirstParameter), True), (eB.valueAt(eB.LastParameter), False)]
    for pa, ia in pontasA:
        for pb, ib in pontasB:
            if (pa - pb).Length < 1e-4:
                return pa, E._dir(eA, ia), E._dir(eB, ib)
    for pa, ia in pontasA:
        if E._ponto_interior(pa, eB):
            to = FreeCAD.Vector(eB.tangentAt(eB.Curve.parameter(pa))).normalize()
            return pa, E._dir(eA, ia), to
    for pb, ib in pontasB:
        if E._ponto_interior(pb, eA):
            to = FreeCAD.Vector(eA.tangentAt(eA.Curve.parameter(pb))).normalize()
            return pb, to, E._dir(eB, ib)
    raise ValueError("as barras %s e %s não se encontram" % (bA.Label, bB.Label))


def _poligono(pts):
    import Part
    return Part.Face(Part.makePolygon(list(pts) + [pts[0]]))


# ============================================================================ objetos (base)
class _Base:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _add(self, obj, tipo, nome, grupo, dica, valor=None, ro=False):
        if nome not in obj.PropertiesList:
            obj.addProperty(tipo, nome, grupo, dica)
            if valor is not None:
                setattr(obj, nome, valor)
        if ro:
            obj.setEditorMode(nome, 1)

    def _enum(self, obj, nome, grupo, dica, valores, inicial=None):
        if nome not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", nome, grupo, dica)
            setattr(obj, nome, valores)
            if inicial:
                setattr(obj, nome, inicial)

    def _props_chapa(self, obj):
        self._add(obj, "App::PropertyString", "Material", "Material", "Material da chapa (texto para a lista)", "")
        self._add(obj, "App::PropertyString", "Denominacao", "Material", "Descrição na lista de materiais", "", True)
        self._add(obj, "App::PropertyFloat", "Massa", "Material", "Massa (kg, aço 7.850 kg/m³)", 0.0, True)
        self._add(obj, "App::PropertyStringList", "Avisos", "Material", "Avisos do cálculo", [], True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        try:
            sh, den = self.forma(obj)
        except (ValueError, ZeroDivisionError) as ex:
            obj.Avisos = [str(ex)]
            FreeCAD.Console.PrintWarning("Prumo: %s: %s\n" % (obj.Label, ex))
            return
        obj.Shape = sh
        obj.Avisos = []
        if "Denominacao" in obj.PropertiesList:
            obj.Denominacao = den
        if "Massa" in obj.PropertiesList:
            obj.Massa = sh.Volume * DENSIDADE_ACO * 1e-9

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VPExtra:
    icone = "estrutura.svg"

    def __init__(self, vobj, icone=None):
        vobj.Proxy = self
        if icone:
            self.icone = icone

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        tipo = getattr(getattr(self, "Object", None), "Proxy", None)
        nome = getattr(tipo, "ICONE", self.icone)
        return PrumoUtil.icone(nome)

    def dumps(self):
        return None

    def loads(self, state):
        return None


# ============================================================================ reforço (gusset)
class Reforco(_Base):
    """Chapa de reforço (mão-francesa) no canto entre duas barras."""
    ICONE = "reforco.svg"

    def _props(self, obj):
        self._add(obj, "App::PropertyLink", "BarraA", "Reforço", "Primeira barra do canto")
        self._add(obj, "App::PropertyLink", "BarraB", "Reforço", "Segunda barra do canto")
        self._enum(obj, "Tipo", "Reforço", "Triangular ou poligonal (pontas retas)", TIPOS_REFORCO)
        self._add(obj, "App::PropertyLength", "Perna1", "Reforço", "Comprimento ao longo da barra A", 150.0)
        self._add(obj, "App::PropertyLength", "Perna2", "Reforço", "Comprimento ao longo da barra B", 150.0)
        self._add(obj, "App::PropertyLength", "Ponta", "Reforço", "Altura das pontas retas (poligonal)", 30.0)
        self._add(obj, "App::PropertyLength", "Espessura", "Reforço", "Espessura da chapa", 8.0)
        self._add(obj, "App::PropertyLength", "Chanfro", "Reforço",
                  "Chanfro no canto interno (passagem do cordão de solda)", 15.0)
        self._enum(obj, "Posicao", "Reforço", "Posição na largura do perfil", POSICOES)
        self._add(obj, "App::PropertyBool", "InverterLado", "Reforço",
                  "Ligação em T: põe o reforço do outro lado da barra que passa", False)
        self._props_chapa(obj)

    def forma(self, obj):
        bA, bB = obj.BarraA, obj.BarraB
        if bA is None or bB is None:
            raise ValueError("escolha as duas barras do canto")
        p, a, b = no_entre(bA, bB)
        if obj.InverterLado:
            b = b * -1
        n = a.cross(b)
        if n.Length < 1e-6:
            raise ValueError("barras alinhadas: não há canto para o reforço")
        n.normalize()
        _e, _eds, _nm, secA = _contexto(bA)
        _e, _eds, _nm, secB = _contexto(bB)
        pa = b - a * b.dot(a)          # no plano, perpendicular a A, para o lado de B
        pa.normalize()
        pb = a - b * a.dot(b)          # perpendicular a B, para o lado de A
        pb.normalize()
        hA = secA.extremos(pa)[1]      # face de A voltada para B
        hB = secB.extremos(pb)[1]      # face de B voltada para A
        # canto interno: interseção das retas (p + pa·hA + a·s) e (p + pb·hB + b·r)
        bpa = b.dot(pa)
        if abs(bpa) < 1e-9:
            raise ValueError("ângulo entre as barras inválido")
        r = (hA - hB * pb.dot(pa)) / bpa
        s = hB * pb.dot(a) + r * b.dot(a)
        c = p + pa * hA + a * s
        d1, d2 = obj.Perna1.Value, obj.Perna2.Value
        ch = min(obj.Chanfro.Value, 0.45 * min(d1, d2))
        t = obj.Espessura.Value
        if d1 <= 0 or d2 <= 0 or t <= 0:
            raise ValueError("pernas e espessura precisam ser positivas")
        pts = []
        if ch > 1e-9:
            pts += [c + b * ch, c + a * ch]
        else:
            pts.append(c)
        if obj.Tipo == "Poligonal":
            h = min(obj.Ponta.Value, 0.9 * min(d1, d2))
            pts += [c + a * d1, c + a * d1 + pa * h, c + b * d2 + pb * h, c + b * d2]
        else:
            pts += [c + a * d1, c + b * d2]
        # posição na largura do perfil (direção n)
        frente = min(secA.extremos(n)[1], secB.extremos(n)[1])
        tras = max(secA.extremos(n)[0], secB.extremos(n)[0])
        z0 = {"Centro": -t / 2.0, "Frente": frente - t, "Trás": tras}[obj.Posicao]
        face = _poligono([q + n * z0 for q in pts])
        sh = face.extrude(n * t)
        den = "Reforço %s %s × %s × %s mm" % (obj.Tipo.lower(), fmt_dim(d1), fmt_dim(d2), fmt_dim(t))
        return sh, den


# ============================================================================ tampa de extremidade
class Tampa(_Base):
    """Tampa na ponta de tubo redondo ou quadrado."""
    ICONE = "tampa.svg"

    def _props(self, obj):
        self._add(obj, "App::PropertyLink", "Barra", "Tampa", "Barra de tubo")
        self._enum(obj, "Ponta", "Tampa", "Qual ponta da barra", PONTAS)
        self._enum(obj, "Tipo", "Tampa", "Por fora (sobre a ponta) ou por dentro do tubo", TIPOS_TAMPA)
        self._add(obj, "App::PropertyLength", "Espessura", "Tampa", "Espessura da tampa", 3.0)
        self._add(obj, "App::PropertyLength", "Folga", "Tampa",
                  "Externa: recuo da borda em relação à parede (assento da solda); interna: folga para a parede",
                  1.0)
        self._add(obj, "App::PropertyLength", "Recuo", "Tampa", "Interna: quanto a tampa entra no tubo", 0.0)
        self._props_chapa(obj)

    def forma(self, obj):
        import Part
        b = obj.Barra
        if b is None:
            raise ValueError("escolha a barra")
        k = PONTAS.index(obj.Ponta)
        p, fora, sec, ang = ponta(b, k)
        if abs(ang) > 1e-6:
            raise ValueError("a ponta tem corte inclinado (%s°): a tampa vale só para corte reto" % fmt(ang, 0))
        it = sec.it
        if it["tipo"] not in ("TUBO", "TQ"):
            raise ValueError("tampa de extremidade é para tubo redondo ou quadrado (perfil: %s)" % it["nome"])
        t, folga = obj.Espessura.Value, obj.Folga.Value
        centro = p + sec.u * sec.du + sec.v * sec.dv
        externa = obj.Tipo == "Externa"
        if it["tipo"] == "TUBO":
            d = it["D"] - 2 * folga if externa else it["D"] - 2 * it["esp"] - 2 * folga
            if d <= 0:
                raise ValueError("folga grande demais para o tubo")
            base = centro if externa else centro - fora * obj.Recuo.Value
            face = Part.Face(Part.Wire(Part.makeCircle(d / 2.0, base, fora)))
            den = "Tampa Ø%s × %s mm" % (fmt_dim(d), fmt_dim(t))
        else:
            lado = it["lado"] - 2 * folga if externa else it["lado"] - 2 * it["esp"] - 2 * folga
            if lado <= 0:
                raise ValueError("folga grande demais para o tubo")
            base = centro if externa else centro - fora * obj.Recuo.Value
            h = lado / 2.0
            face = _poligono([base + sec.u * x + sec.v * y for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))])
            den = "Tampa %s × %s × %s mm" % (fmt_dim(lado), fmt_dim(lado), fmt_dim(t))
        sh = face.extrude(fora * t) if externa else face.extrude(fora * -t)
        return sh, den


# ============================================================================ placa de base
class PlacaBase(_Base):
    """Placa de base (sapata) na ponta da barra, com furação."""
    ICONE = "placa_base.svg"

    def _props(self, obj):
        self._add(obj, "App::PropertyLink", "Barra", "Placa", "Barra (coluna)")
        self._enum(obj, "Ponta", "Placa", "Qual ponta da barra", PONTAS)
        self._add(obj, "App::PropertyLength", "Largura", "Placa", "Medida na largura do perfil", 250.0)
        self._add(obj, "App::PropertyLength", "Comprimento", "Placa", "Medida na altura do perfil", 300.0)
        self._add(obj, "App::PropertyLength", "Espessura", "Placa", "Espessura da placa", 16.0)
        self._enum(obj, "Furos", "Placa", "Quantidade de furos", ["0", "2", "4"], "4")
        self._add(obj, "App::PropertyLength", "DiametroFuro", "Placa", "Diâmetro dos furos", 22.0)
        self._add(obj, "App::PropertyLength", "DistanciaBorda", "Placa", "Do centro do furo até a borda", 40.0)
        self._props_chapa(obj)

    def forma(self, obj):
        import Part
        b = obj.Barra
        if b is None:
            raise ValueError("escolha a barra")
        k = PONTAS.index(obj.Ponta)
        p, fora, sec, ang = ponta(b, k)
        if abs(ang) > 1e-6:
            raise ValueError("a ponta tem corte inclinado (%s°): a placa vale só para corte reto" % fmt(ang, 0))
        L, C, t = obj.Largura.Value, obj.Comprimento.Value, obj.Espessura.Value
        if L <= 0 or C <= 0 or t <= 0:
            raise ValueError("medidas da placa precisam ser positivas")
        if L < sec.larg - 1e-6 or C < sec.alt - 1e-6:
            raise ValueError("a placa (%s × %s) é menor que o perfil (%s × %s)" % (
                fmt_dim(L), fmt_dim(C), fmt_dim(sec.larg), fmt_dim(sec.alt)))
        centro = p + sec.u * sec.du + sec.v * sec.dv
        hl, hc = L / 2.0, C / 2.0
        face = _poligono([centro + sec.u * x + sec.v * y for x, y in ((-hl, -hc), (hl, -hc), (hl, hc), (-hl, hc))])
        sh = face.extrude(fora * t)
        n = int(obj.Furos)
        dfuro, borda = obj.DiametroFuro.Value, obj.DistanciaBorda.Value
        if n:
            if borda - dfuro / 2.0 <= 0 or borda >= min(hl, hc):
                raise ValueError("distância da borda incompatível com o furo e a placa")
            if n == 4:
                pos = [(x, y) for x in (-hl + borda, hl - borda) for y in (-hc + borda, hc - borda)]
            else:  # 2 furos na maior medida
                pos = [(0, -hc + borda), (0, hc - borda)] if C >= L else [(-hl + borda, 0), (hl - borda, 0)]
            for x, y in pos:
                cil = Part.makeCylinder(dfuro / 2.0, t + 2, centro + sec.u * x + sec.v * y - fora, fora)
                sh = sh.cut(cil)
            # o furo não pode cair dentro do perfil
            face_perfil = PrumoPerfis.face(sec.it, p, sec.u, sec.v, sec.dv, sec.du, sec.espelhar)
            for x, y in pos:
                q = centro + sec.u * x + sec.v * y
                if face_perfil.distToShape(Part.Vertex(q))[0] < dfuro / 2.0:
                    raise ValueError("furo sobre o perfil: aumente a placa ou a distância da borda")
        den = "Placa de base %s × %s × %s mm" % (fmt_dim(L), fmt_dim(C), fmt_dim(t))
        if n:
            den += " — %d furos Ø%s" % (n, fmt_dim(dfuro))
        return sh.removeSplitter() if hasattr(sh, "removeSplitter") else sh, den


# ============================================================================ cordão de solda
def linhas_de_contato(shA, shB, tol=1e-4):
    """Arestas onde as duas peças se tocam (contorno das áreas de contato)."""
    import Part
    res = []
    for fa in shA.Faces:
        if fa.Surface.__class__.__name__ != "Plane":
            continue
        na = fa.normalAt(*_meio_param(fa))
        for fb in shB.Faces:
            if fb.Surface.__class__.__name__ != "Plane":
                continue
            nb = fb.normalAt(*_meio_param(fb))
            if na.dot(nb) > -1 + 1e-6:
                continue
            if abs((fb.Vertexes[0].Point - fa.Vertexes[0].Point).dot(na)) > tol:
                continue
            if not fa.BoundBox.intersect(fb.BoundBox):
                continue
            try:
                comum = fa.common(fb)
            except Exception:
                continue
            for f in comum.Faces:
                if f.Area > 1e-3:
                    res.extend(f.OuterWire.Edges)
    if res:
        return res
    # contato não plano (ex.: boca de lobo em tubo): interseção das superfícies
    try:
        sec = shA.section(shB)
        return [e for e in sec.Edges if e.Length > tol]
    except Exception:
        return []


def _meio_param(f):
    u0, u1, v0, v1 = f.ParameterRange
    return (u0 + u1) / 2.0, (v0 + v1) / 2.0


class Solda(_Base):
    """Cordão de solda de filete nas linhas de contato entre as peças."""
    ICONE = "solda.svg"

    def _props(self, obj):
        self._add(obj, "App::PropertyLinkList", "Pecas", "Solda", "Peças unidas pelo cordão (duas ou mais)")
        self._add(obj, "App::PropertyLength", "Perna", "Solda", "Perna do filete (z)", 5.0)
        self._enum(obj, "Processo", "Solda", "Processo de soldagem", PROCESSOS)
        self._add(obj, "App::PropertyString", "Eletrodo", "Solda", "Eletrodo / arame (ex.: E7018, ER70S-6)", "")
        self._add(obj, "App::PropertyString", "Observacao", "Solda", "Observação (ex.: todo o contorno)", "")
        self._add(obj, "App::PropertyLength", "ComprimentoTotal", "Resultados", "Soma das linhas de solda", 0.0, True)
        self._add(obj, "App::PropertyFloat", "VolumeDepositado", "Resultados",
                  "Volume do filete (cm³) = L × z² / 2", 0.0, True)
        self._add(obj, "App::PropertyFloat", "MassaDepositada", "Resultados", "Massa do metal depositado (kg)",
                  0.0, True)
        self._add(obj, "App::PropertyString", "Juntas", "Resultados", "Peças unidas", "", True)
        self._add(obj, "App::PropertyStringList", "Avisos", "Resultados", "Avisos", [], True)

    def execute(self, obj):
        import Part
        pecas = [p for p in obj.Pecas if p is not None and hasattr(p, "Shape") and not p.Shape.isNull()]
        avisos = []
        if len(pecas) < 2:
            obj.Avisos = ["escolha ao menos duas peças"]
            return
        z = obj.Perna.Value
        if z <= 0:
            obj.Avisos = ["a perna do filete precisa ser positiva"]
            return
        arestas = []
        juntas = []
        for x in range(len(pecas)):
            for y in range(x + 1, len(pecas)):
                eds = linhas_de_contato(pecas[x].Shape, pecas[y].Shape)
                if eds:
                    arestas.extend(eds)
                    juntas.append("%s + %s" % (pecas[x].Label, pecas[y].Label))
        if not arestas:
            obj.Avisos = ["as peças escolhidas não se tocam"]
            obj.Shape = Part.Shape()
            obj.ComprimentoTotal = 0.0
            obj.VolumeDepositado = obj.MassaDepositada = 0.0
            obj.Juntas = ""
            return
        tubos = []
        for e in arestas:
            try:
                p = e.valueAt(e.FirstParameter)
                tg = e.tangentAt(e.FirstParameter)
                circ = Part.Wire(Part.makeCircle(z / 2.0, p, tg))
                tubos.append(Part.Wire(e).makePipeShell([circ], True, False))
            except Exception:
                avisos.append("trecho de %s mm sem representação" % fmt(e.Length, 1))
        obj.Shape = Part.Compound(tubos) if tubos else Part.Shape()
        L = sum(e.Length for e in arestas)
        vol = L * z * z / 2.0                      # mm³
        obj.ComprimentoTotal = L
        obj.VolumeDepositado = vol / 1000.0       # cm³
        obj.MassaDepositada = vol * DENSIDADE_ACO * 1e-9
        obj.Juntas = "; ".join(juntas)
        obj.Avisos = avisos


def eh_solda(o):
    return o is not None and "Perna" in o.PropertiesList and "Pecas" in o.PropertiesList


# ============================================================================ criação
def _novo(doc, classe, nome, rotulo, **props):
    o = doc.addObject("Part::FeaturePython", nome)
    classe(o)
    o.Label = rotulo
    for k, v in props.items():
        setattr(o, k, v)
    if FreeCAD.GuiUp:
        VPExtra(o.ViewObject)
        try:
            cor = (0.85, 0.55, 0.15) if classe is Solda else (0.42, 0.50, 0.58)
            m = FreeCAD.Material()
            m.DiffuseColor = cor
            o.ViewObject.ShapeAppearance = [m]
        except Exception:
            pass
    est = None
    candidatos = [props.get("BarraA"), props.get("Barra")] + list(props.get("Pecas", []))
    for c in candidatos:
        if c is not None and E.eh_barra(c) and E.eh_estrutura(c.Estrutura):
            est = c.Estrutura
            break
    if est is not None:
        est.addObject(o)
    return o


def _transacao(doc, titulo, f):
    doc.openTransaction(titulo)
    try:
        o = f()
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    return o


def criar_reforco(barraA, barraB, **props):
    doc = barraA.Document
    return _transacao(doc, "Reforço", lambda: _novo(doc, Reforco, "Reforco", "Reforço",
                                                     BarraA=barraA, BarraB=barraB, **props))


def criar_tampa(barra, ponta_txt="Fim", **props):
    doc = barra.Document
    return _transacao(doc, "Tampa", lambda: _novo(doc, Tampa, "Tampa", "Tampa", Barra=barra, Ponta=ponta_txt,
                                                   **props))


def criar_placa_base(barra, ponta_txt="Início", **props):
    doc = barra.Document
    return _transacao(doc, "Placa de base", lambda: _novo(doc, PlacaBase, "PlacaBase", "Placa de base",
                                                           Barra=barra, Ponta=ponta_txt, **props))


def criar_solda(pecas, perna=5.0, processo=PROCESSOS[0], eletrodo="", observacao=""):
    if len(pecas) < 2:
        raise ValueError("escolha ao menos duas peças")
    doc = pecas[0].Document

    def f():
        o = _novo(doc, Solda, "Solda", "Cordão de solda", Pecas=list(pecas), Perna=perna, Processo=processo,
                  Eletrodo=eletrodo, Observacao=observacao)
        return o
    return _transacao(doc, "Cordão de solda", f)


# ============================================================================ lista de soldas
NOME_LISTA_SOLDAS = "ListaDeSoldas"


def lista_de_soldas(objs):
    soldas = []
    for o in objs:
        if eh_solda(o) and o not in soldas:
            soldas.append(o)
        for f in getattr(o, "Group", []) or []:
            if eh_solda(f) and f not in soldas:
                soldas.append(f)
    return soldas


def gravar_lista_de_soldas(doc, soldas):
    sheet = doc.getObject(NOME_LISTA_SOLDAS)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", NOME_LISTA_SOLDAS)
        sheet.Label = "Lista de soldas"
    else:
        sheet.clearAll()
    cab = ["Item", "Junta", "Perna z (mm)", "Comprimento (mm)", "Processo", "Eletrodo", "Volume (cm³)",
           "Massa (kg)", "Observação"]
    larg = [40, 260, 80, 105, 170, 90, 85, 75, 160]
    cols = "ABCDEFGHI"
    for i, (c, w) in enumerate(zip(cab, larg)):
        sheet.set("%s1" % cols[i], c)
        sheet.setColumnWidth(cols[i], w)
    sheet.setStyle("A1:I1", "bold")
    sheet.setBackground("A1:I1", (0.0, 0.227, 0.439))
    sheet.setForeground("A1:I1", (1.0, 1.0, 1.0))
    tl = tv = tm = 0.0
    for n, s in enumerate(soldas, 1):
        r = n + 1
        sheet.set("A%d" % r, str(n))
        sheet.set("B%d" % r, "'" + (s.Juntas or s.Label))
        sheet.set("C%d" % r, "'" + fmt(s.Perna.Value, 1))
        sheet.set("D%d" % r, "'" + fmt(s.ComprimentoTotal.Value, 0))
        sheet.set("E%d" % r, "'" + s.Processo)
        sheet.set("F%d" % r, "'" + (s.Eletrodo or "—"))
        sheet.set("G%d" % r, "'" + fmt(s.VolumeDepositado, 1))
        sheet.set("H%d" % r, "'" + fmt(s.MassaDepositada, 3))
        sheet.set("I%d" % r, "'" + (s.Observacao or ""))
        tl += s.ComprimentoTotal.Value
        tv += s.VolumeDepositado
        tm += s.MassaDepositada
    r = len(soldas) + 2
    sheet.set("B%d" % r, "Total")
    sheet.set("D%d" % r, "'" + fmt(tl, 0))
    sheet.set("G%d" % r, "'" + fmt(tv, 1))
    sheet.set("H%d" % r, "'" + fmt(tm, 3))
    sheet.setStyle("B%d:H%d" % (r, r), "bold")
    doc.recompute()
    return sheet


# ============================================================================ interface
def _spin(valor, maximo=5000.0, sufixo=" mm", casas=1):
    s = QtWidgets.QDoubleSpinBox()
    s.setRange(0.0, maximo)
    s.setDecimals(casas)
    s.setSuffix(sufixo)
    s.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
    s.setValue(valor)
    return s


def _combo(itens, atual=None):
    c = QtWidgets.QComboBox()
    c.addItems(itens)
    if atual:
        c.setCurrentText(atual)
    return c


def _botoes(d, texto_ok):
    bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
    bb.button(QtWidgets.QDialogButtonBox.Ok).setText(texto_ok)
    bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    return bb


def _ultimo_material():
    return FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialChapa", "")


def _guardar_material(txt):
    FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimoMaterialChapa", txt)


class DialogoReforco(QtWidgets.QDialog):
    def __init__(self, em_T=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reforço (mão-francesa)")
        f = QtWidgets.QFormLayout(self)
        self.tipo = _combo(TIPOS_REFORCO)
        self.perna1, self.perna2 = _spin(150.0), _spin(150.0)
        self.ponta_h = _spin(30.0)
        self.esp = _spin(8.0, 200.0)
        self.chanfro = _spin(15.0, 500.0)
        self.posicao = _combo(POSICOES)
        self.lados = _combo(["Um lado", "Os dois lados"])
        self.lados.setEnabled(em_T)
        self.material = QtWidgets.QLineEdit(_ultimo_material())
        self.material.setPlaceholderText("ex.: ASTM A36")
        for rot, w in (("Tipo", self.tipo), ("Perna na 1ª barra", self.perna1), ("Perna na 2ª barra", self.perna2),
                       ("Pontas retas (poligonal)", self.ponta_h), ("Espessura", self.esp),
                       ("Chanfro do canto", self.chanfro), ("Posição", self.posicao), ("Ligação em T", self.lados),
                       ("Material", self.material)):
            f.addRow(rot, w)
        f.addRow(_botoes(self, "Inserir"))

    def props(self):
        return dict(Tipo=self.tipo.currentText(), Perna1=self.perna1.value(), Perna2=self.perna2.value(),
                    Ponta=self.ponta_h.value(), Espessura=self.esp.value(), Chanfro=self.chanfro.value(),
                    Posicao=self.posicao.currentText(), Material=self.material.text().strip())


def _pontas_livres(b):
    _est, eds, _n, _s = _contexto(b)
    return [k for k, lig in enumerate(E.ligacoes(eds, b.Indice)) if lig.tipo == "livre"]


def _ponta_de_baixo(b):
    _est, eds, _n, _s = _contexto(b)
    e = eds[b.Indice]
    return 0 if e.valueAt(e.FirstParameter).z <= e.valueAt(e.LastParameter).z else 1


class DialogoTampa(QtWidgets.QDialog):
    ESCOLHAS = ["Pontas livres", "Início", "Fim", "As duas pontas"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tampa de extremidade")
        f = QtWidgets.QFormLayout(self)
        self.pontas = _combo(self.ESCOLHAS)
        self.tipo = _combo(TIPOS_TAMPA)
        self.esp = _spin(3.0, 100.0)
        self.folga = _spin(1.0, 50.0, casas=2)
        self.recuo = _spin(0.0, 500.0)
        self.material = QtWidgets.QLineEdit(_ultimo_material())
        for rot, w in (("Pontas", self.pontas), ("Tipo", self.tipo), ("Espessura", self.esp),
                       ("Folga / recuo da borda", self.folga), ("Recuo (interna)", self.recuo),
                       ("Material", self.material)):
            f.addRow(rot, w)
        f.addRow(_botoes(self, "Inserir"))

    def pontas_da(self, b):
        e = self.pontas.currentText()
        if e == "Início":
            return [0]
        if e == "Fim":
            return [1]
        if e == "As duas pontas":
            return [0, 1]
        return _pontas_livres(b)

    def props(self):
        return dict(Tipo=self.tipo.currentText(), Espessura=self.esp.value(), Folga=self.folga.value(),
                    Recuo=self.recuo.value(), Material=self.material.text().strip())


class DialogoPlaca(QtWidgets.QDialog):
    ESCOLHAS = ["Ponta de baixo", "Início", "Fim"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Placa de base")
        f = QtWidgets.QFormLayout(self)
        self.ponta = _combo(self.ESCOLHAS)
        self.larg, self.comp, self.esp = _spin(250.0), _spin(300.0), _spin(16.0, 200.0)
        self.furos = _combo(["0", "2", "4"], "4")
        self.diam, self.borda = _spin(22.0, 200.0), _spin(40.0, 500.0)
        self.material = QtWidgets.QLineEdit(_ultimo_material())
        for rot, w in (("Ponta", self.ponta), ("Largura (na largura do perfil)", self.larg),
                       ("Comprimento (na altura do perfil)", self.comp), ("Espessura", self.esp),
                       ("Furos", self.furos), ("Diâmetro do furo", self.diam), ("Furo até a borda", self.borda),
                       ("Material", self.material)):
            f.addRow(rot, w)
        f.addRow(_botoes(self, "Inserir"))

    def ponta_da(self, b):
        e = self.ponta.currentText()
        return _ponta_de_baixo(b) if e == "Ponta de baixo" else (0 if e == "Início" else 1)

    def props(self):
        return dict(Largura=self.larg.value(), Comprimento=self.comp.value(), Espessura=self.esp.value(),
                    Furos=self.furos.currentText(), DiametroFuro=self.diam.value(),
                    DistanciaBorda=self.borda.value(), Material=self.material.text().strip())


class DialogoSolda(QtWidgets.QDialog):
    def __init__(self, parent=None, todas=False):
        super().__init__(parent)
        self.setWindowTitle("Cordão de solda" + (" — todas as juntas" if todas else ""))
        f = QtWidgets.QFormLayout(self)
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        self.perna = _spin(g.GetFloat("UltimaPernaSolda", 5.0), 50.0)
        self.processo = _combo(PROCESSOS, g.GetString("UltimoProcessoSolda", PROCESSOS[0]))
        self.eletrodo = QtWidgets.QLineEdit(g.GetString("UltimoEletrodo", ""))
        self.eletrodo.setPlaceholderText("ex.: E7018, ER70S-6")
        self.obs = QtWidgets.QLineEdit()
        f.addRow("Perna do filete (z)", self.perna)
        f.addRow("Processo", self.processo)
        f.addRow("Eletrodo / arame", self.eletrodo)
        f.addRow("Observação", self.obs)
        f.addRow(_botoes(self, "Inserir"))

    def guardar(self):
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        g.SetFloat("UltimaPernaSolda", self.perna.value())
        g.SetString("UltimoProcessoSolda", self.processo.currentText())
        g.SetString("UltimoEletrodo", self.eletrodo.text().strip())


def juntas_da_estrutura(est):
    """Pares de barras que se tocam (cantos, ligações em T e nós múltiplos)."""
    eds = E.arestas(est.Esqueleto)
    bs = {b.Indice: b for b in E.barras_de(est)}
    pares = []
    for i in range(len(eds)):
        for lig in E.ligacoes(eds, i):
            outros = [lig.outro] if lig.outro is not None else [j for j, _d in lig.outros]
            for j in outros:
                par = (min(i, j), max(i, j))
                if par not in pares and par[0] in bs and par[1] in bs:
                    pares.append(par)
    return [(bs[i], bs[j]) for i, j in pares]


def soldar_estrutura(est, perna=5.0, processo=PROCESSOS[0], eletrodo="", observacao=""):
    """Um cordão por junta da estrutura; juntas que não se tocam são puladas."""
    criadas = []
    for a, b in juntas_da_estrutura(est):
        if not linhas_de_contato(a.Shape, b.Shape):
            continue
        criadas.append(criar_solda([a, b], perna, processo, eletrodo, observacao))
    return criadas


def _aviso(titulo, texto):
    QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), titulo, texto)


def _relatar(objs):
    ruins = [o for o in objs if getattr(o, "Avisos", None)]
    if ruins:
        _aviso("Prumo 3D", "\n".join("%s: %s" % (o.Label, "; ".join(o.Avisos)) for o in ruins))


class CmdReforco:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("reforco.svg"), "MenuText": "Reforço",
                "ToolTip": "Mão-francesa (gusset) triangular ou poligonal no canto entre as duas barras "
                           "selecionadas, apoiada nas faces internas, com chanfro para a solda."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        bs = E.barras_da_selecao()
        if len(bs) != 2:
            _aviso("Reforço", "Selecione as duas barras do canto (ou da ligação em T).")
            return
        try:
            _p, a, b = no_entre(bs[0], bs[1])
        except ValueError as ex:
            _aviso("Reforço", str(ex))
            return
        _est, eds, _n, _s = _contexto(bs[0])
        em_T = any(E._ponto_interior(p, eds[x.Indice]) for x, y in ((bs[0], bs[1]), (bs[1], bs[0]))
                   for p in (eds[y.Indice].valueAt(eds[y.Indice].FirstParameter),
                             eds[y.Indice].valueAt(eds[y.Indice].LastParameter)))
        d = DialogoReforco(em_T, FreeCADGui.getMainWindow())
        if not d.exec():
            return
        _guardar_material(d.material.text().strip())
        feitos = [criar_reforco(bs[0], bs[1], **d.props())]
        if em_T and d.lados.currentText() == "Os dois lados":
            feitos.append(criar_reforco(bs[0], bs[1], InverterLado=True, **d.props()))
        _relatar(feitos)


class CmdTampa:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("tampa.svg"), "MenuText": "Tampa de extremidade",
                "ToolTip": "Fecha as pontas dos tubos selecionados, por fora ou por dentro, com folga para a solda."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        bs = [b for b in E.barras_da_selecao() if PrumoPerfis.perfil(b.Perfil) and
              PrumoPerfis.perfil(b.Perfil)["tipo"] in ("TUBO", "TQ")]
        if not bs:
            _aviso("Tampa de extremidade", "Selecione barras de tubo redondo ou quadrado.")
            return
        d = DialogoTampa(FreeCADGui.getMainWindow())
        if not d.exec():
            return
        _guardar_material(d.material.text().strip())
        feitos = []
        for b in bs:
            for k in d.pontas_da(b):
                feitos.append(criar_tampa(b, PONTAS[k], **d.props()))
        if not feitos:
            _aviso("Tampa de extremidade", "As barras selecionadas não têm pontas livres.")
        _relatar(feitos)


class CmdPlacaBase:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("placa_base.svg"), "MenuText": "Placa de base",
                "ToolTip": "Sapata com furação na ponta das barras (colunas) selecionadas."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        bs = E.barras_da_selecao()
        if not bs:
            _aviso("Placa de base", "Selecione as colunas (barras) que recebem a placa.")
            return
        d = DialogoPlaca(FreeCADGui.getMainWindow())
        if not d.exec():
            return
        _guardar_material(d.material.text().strip())
        _relatar([criar_placa_base(b, PONTAS[d.ponta_da(b)], **d.props()) for b in bs])


class CmdSolda:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("solda.svg"), "MenuText": "Cordão de solda",
                "ToolTip": "Cordão de filete entre as peças selecionadas (barras, reforços, placas). Com a "
                           "estrutura selecionada, solda todas as juntas."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        ests = [o for o in sel if E.eh_estrutura(o)]
        if ests:
            d = DialogoSolda(FreeCADGui.getMainWindow(), todas=True)
            if not d.exec():
                return
            d.guardar()
            n = 0
            for est in ests:
                n += len(soldar_estrutura(est, d.perna.value(), d.processo.currentText(),
                                          d.eletrodo.text().strip(), d.obs.text().strip()))
            _aviso("Cordão de solda", "%d cordões criados." % n)
            return
        pecas = [o for o in sel if hasattr(o, "Shape") and o.Shape.Solids and not eh_solda(o)]
        if len(pecas) < 2:
            _aviso("Cordão de solda", "Selecione duas ou mais peças que se tocam (ou a estrutura inteira).")
            return
        d = DialogoSolda(FreeCADGui.getMainWindow())
        if not d.exec():
            return
        d.guardar()
        _relatar([criar_solda(pecas, d.perna.value(), d.processo.currentText(), d.eletrodo.text().strip(),
                              d.obs.text().strip())])


class CmdListaSoldas:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("lista_soldas.svg"), "MenuText": "Lista de soldas",
                "ToolTip": "Planilha com as juntas, perna, comprimento, processo, eletrodo, volume e massa "
                           "de metal depositado."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        soldas = lista_de_soldas(FreeCADGui.Selection.getSelection() or doc.Objects)
        if not soldas:
            _aviso("Lista de soldas", "Nenhum cordão de solda encontrado.")
            return
        doc.openTransaction("Lista de soldas")
        gravar_lista_de_soldas(doc, soldas)
        doc.commitTransaction()


def registrar_comandos():
    for nome, cmd in (("Prumo_Reforco", CmdReforco()), ("Prumo_Tampa", CmdTampa()),
                      ("Prumo_PlacaBase", CmdPlacaBase()), ("Prumo_Solda", CmdSolda()),
                      ("Prumo_ListaSoldas", CmdListaSoldas())):
        FreeCADGui.addCommand(nome, cmd)
