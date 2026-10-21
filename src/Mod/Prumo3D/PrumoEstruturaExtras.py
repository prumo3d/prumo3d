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
    todas = E.arestas(est.Esqueleto)
    if barra.Indice >= len(todas):
        raise ValueError("%s não tem mais linha no esqueleto" % barra.Label)
    normal = E._normal_esqueleto(todas)
    eds = E.arestas_ativas(est, todas)
    if eds[barra.Indice] is None:
        raise ValueError("%s está numa linha sem barra" % barra.Label)
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

    def doubleClicked(self, vobj):
        """Duplo clique na árvore: abre o mesmo painel da criação, editando este objeto."""
        return abrir_edicao(vobj.Object) is not None

    def setEdit(self, vobj, mode=0):
        if mode != 0:
            return None   # outros modos (ex.: Transformar) seguem o padrão do FreeCAD
        return abrir_edicao(vobj.Object) is not None

    def unsetEdit(self, vobj, mode=0):
        return False

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
    import PrumoPainel
    if PrumoPainel.EM_PREVIA["ativa"]:   # prévia de um painel: a transação é a do painel
        o = f()
        doc.recompute()
        return o
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
def _ultimo_material():
    return FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialChapa", "")


def _guardar_material(txt):
    FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimoMaterialChapa", txt)


# ---------------------------------------------------------------- painéis de tarefa (estilo PropertyManager)
import PrumoPainel as P


def _filtro_barras(obj, subs):
    return [(b.Label, b) for b in E.barras_do_item(obj, subs)]


def _filtro_tubos(obj, subs):
    return [(b.Label, b) for b in E.barras_do_item(obj, subs)
            if PrumoPerfis.perfil(b.Perfil) and PrumoPerfis.perfil(b.Perfil)["tipo"] in ("TUBO", "TQ")]


def _filtro_pecas_ou_estrutura(obj, subs):
    res = []
    for o, _els in E.resolver_item(obj, subs):
        if E.eh_estrutura(o):
            res.append(("%s (todas as juntas)" % o.Label, o))
        elif E.eh_barra(o) or (hasattr(o, "Shape") and not eh_solda(o) and o.Shape.Solids):
            res.append((o.Label, o))
    return res


def em_T(a, b):
    _est, eds, _n, _s = _contexto(a)
    return any(E._ponto_interior(p, eds[x.Indice]) for x, y in ((a, b), (b, a))
               for p in (eds[y.Indice].valueAt(eds[y.Indice].FirstParameter),
                         eds[y.Indice].valueAt(eds[y.Indice].LastParameter)))


def _marcas_pontas(barras, escolhidas):
    """Marcas "Início" e "Fim" nas pontas das barras; escolhidas(b) → pontas destacadas (0, 1)."""
    res = []
    for b in barras:
        try:
            quer = set(escolhidas(b))
        except Exception:
            quer = set()
        for k, nome in enumerate(PONTAS):
            try:
                p = ponta(b, k)[0]
            except Exception:
                continue
            res.append((p, nome, k in quer))
    return res


def _meio_da_barra(b):
    _est, eds, _n, _s = _contexto(b)
    e = eds[b.Indice]
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)


class PainelReforco(P.PainelTarefa):
    titulo = "Reforço (mão-francesa)"
    previa = True

    def marcas(self):
        res = []
        for k, b in enumerate(self.barras.valores()):
            try:
                res.append((_meio_da_barra(b), "%dª barra" % (k + 1), False))
            except Exception:
                pass
        return res
    ajuda = "Selecione as duas barras do canto (ou da ligação em T)."

    def montar(self):
        f = self.form
        s1 = f.secao("Barras", "selecao")
        self.barras = f.caixa(s1, "Barras do canto", _filtro_barras, minimo=2, maximo=2,
                              dica="As duas barras que se encontram no canto. Selecione na vista ou na árvore.")
        s2 = f.secao("Forma", "tipo")
        self.tipo = s2.linha("tipo", P.lista(TIPOS_REFORCO), "Triangular: pontas em canto vivo. Poligonal: "
                             "pontas cortadas retas (ponta reta abaixo).", "Tipo")
        self.perna1 = s2.linha("perna", P.numero(150.0), "Quanto o reforço avança sobre a 1ª barra, a partir "
                               "do canto.", "Perna na 1ª barra")
        self.perna2 = s2.linha("perna", P.numero(150.0), "Quanto o reforço avança sobre a 2ª barra.",
                               "Perna na 2ª barra")
        self.ponta_h = s2.linha("ponta", P.numero(30.0), "Largura das pontas retas (só no tipo poligonal).",
                                "Ponta reta")
        self.chanfro = s2.linha("chanfro", P.numero(15.0, maximo=500.0), "Corte no canto interno para a "
                                "solda das barras passar.", "Chanfro do canto")
        s3 = f.secao("Chapa", "espessura")
        self.esp = s3.linha("espessura", P.numero(8.0, maximo=200.0), "Espessura da chapa do reforço.",
                            "Espessura")
        self.posicao = s3.linha("posicao", P.lista(POSICOES), "Onde a chapa fica na largura do perfil.",
                                "Posição")
        self.lados = s3.linha("lado", P.lista(["Um lado", "Os dois lados"]), "Na ligação em T, reforço de um "
                              "lado só ou dos dois.", "Ligação em T")
        self.material = s3.linha("material", QtWidgets.QLineEdit(_ultimo_material()), "Material da chapa "
                                 "(vai para a lista de materiais).", "Material")
        self.material.setPlaceholderText("ex.: ASTM A36")
        self.tipo.currentTextChanged.connect(lambda *_: self._tipo())
        self._tipo()

    def _tipo(self):
        self.ponta_h.setEnabled(self.tipo.currentText() != TIPOS_REFORCO[0])

    def atualizar(self):
        bs = self.barras.valores()
        self.lados.setEnabled(len(bs) == 2 and self._em_T(bs))
        super().atualizar()

    def _em_T(self, bs):
        try:
            return em_T(bs[0], bs[1])
        except Exception:
            return False

    def pendencia(self):
        falta = super().pendencia()
        if falta:
            return falta
        a, b = self.barras.valores()
        try:
            no_entre(a, b)
        except ValueError as ex:
            return str(ex)
        return None

    def props(self):
        return dict(Tipo=self.tipo.currentText(), Perna1=self.perna1.value(), Perna2=self.perna2.value(),
                    Ponta=self.ponta_h.value(), Espessura=self.esp.value(), Chanfro=self.chanfro.value(),
                    Posicao=self.posicao.currentText(), Material=self.material.text().strip())

    def carregar(self, obj):
        for b in (obj.BarraA, obj.BarraB):
            if b is not None:
                self.barras.aceitar(b)
        self.tipo.setCurrentText(obj.Tipo)
        self.perna1.setValue(obj.Perna1.Value)
        self.perna2.setValue(obj.Perna2.Value)
        self.ponta_h.setValue(obj.Ponta.Value)
        self.esp.setValue(obj.Espessura.Value)
        self.chanfro.setValue(obj.Chanfro.Value)
        self.posicao.setCurrentText(obj.Posicao)
        self.material.setText(obj.Material)
        self.lados.setEnabled(False)

    def props_edicao(self):
        a, b = self.barras.valores()
        return dict(self.props(), BarraA=a, BarraB=b)

    def executar(self):
        a, b = self.barras.valores()
        _guardar_material(self.material.text().strip())
        feitos = [criar_reforco(a, b, **self.props())]
        if self._em_T([a, b]) and self.lados.currentText() == "Os dois lados":
            feitos.append(criar_reforco(a, b, InverterLado=True, **self.props()))
        _relatar(feitos)
        return feitos


def _pontas_livres(b):
    _est, eds, _n, _s = _contexto(b)
    return [k for k, lig in enumerate(E.ligacoes(eds, b.Indice)) if lig.tipo == "livre"]


def _ponta_de_baixo(b):
    _est, eds, _n, _s = _contexto(b)
    e = eds[b.Indice]
    return 0 if e.valueAt(e.FirstParameter).z <= e.valueAt(e.LastParameter).z else 1




class PainelTampa(P.PainelTarefa):
    titulo = "Tampa de extremidade"
    previa = True

    def marcas(self):
        return _marcas_pontas(self.barras.valores(), self.pontas_da)
    ajuda = "Selecione as barras de tubo (redondo ou quadrado) que recebem tampa."
    ESCOLHAS = ["Pontas livres", "Início", "Fim", "As duas pontas"]

    def montar(self):
        f = self.form
        s1 = f.secao("Tubos", "selecao")
        self.barras = f.caixa(s1, "Barras de tubo", _filtro_tubos, minimo=1,
                              dica="Só tubos redondos e quadrados/retangulares.")
        s2 = f.secao("Tampa", "tipo")
        self.pontas = s2.linha("ponta", P.lista(self.ESCOLHAS), "Pontas livres: só as que não encostam em "
                               "outra barra.", "Pontas")
        self.tipo = s2.linha("tipo", P.lista(TIPOS_TAMPA), "Por fora: chapa sobre a ponta. Por dentro: "
                             "chapa encaixada no tubo.", "Tipo")
        self.esp = s2.linha("espessura", P.numero(3.0, maximo=100.0), "Espessura da chapa da tampa.",
                            "Espessura")
        self.folga = s2.linha("folga", P.numero(1.0, maximo=50.0, casas=2), "Folga para a solda (por dentro) "
                              "ou recuo da borda (por fora).", "Folga / recuo da borda")
        self.recuo = s2.linha("comprimento", P.numero(0.0, maximo=500.0), "Quanto a tampa interna entra no "
                              "tubo.", "Recuo (interna)")
        self.material = s2.linha("material", QtWidgets.QLineEdit(_ultimo_material()), "Material da chapa.",
                                 "Material")

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

    def carregar(self, obj):
        self.barras.maximo = 1
        if obj.Barra is not None:
            self.barras.aceitar(obj.Barra)
        self.pontas.setCurrentText(obj.Ponta)
        self.tipo.setCurrentText(obj.Tipo)
        self.esp.setValue(obj.Espessura.Value)
        self.folga.setValue(obj.Folga.Value)
        self.recuo.setValue(obj.Recuo.Value)
        self.material.setText(obj.Material)

    def props_edicao(self):
        b = self.barras.valores()[0]
        ks = self.pontas_da(b) or [0]
        return dict(self.props(), Barra=b, Ponta=PONTAS[ks[0]])

    def pendencia(self):
        falta = super().pendencia()
        if falta:
            return falta
        if not any(self.pontas_da(b) for b in self.barras.valores()):
            return "As barras selecionadas não têm pontas livres: escolha Início, Fim ou As duas pontas."
        return None

    def executar(self):
        _guardar_material(self.material.text().strip())
        feitos = [criar_tampa(b, PONTAS[k], **self.props()) for b in self.barras.valores()
                  for k in self.pontas_da(b)]
        _relatar(feitos)
        return feitos


class PainelPlaca(P.PainelTarefa):
    titulo = "Placa de base"
    previa = True

    def marcas(self):
        return _marcas_pontas(self.barras.valores(), lambda b: [self.ponta_da(b)])
    ajuda = "Selecione as colunas (barras) que recebem a placa."
    ESCOLHAS = ["Ponta de baixo", "Início", "Fim"]

    def montar(self):
        f = self.form
        s1 = f.secao("Colunas", "selecao")
        self.barras = f.caixa(s1, "Colunas", _filtro_barras, minimo=1)
        s2 = f.secao("Placa", "largura")
        self.ponta = s2.linha("ponta", P.lista(self.ESCOLHAS), "Em que ponta da coluna fica a placa.",
                              "Ponta")
        self.larg = s2.linha("largura", P.numero(250.0), "Medida na direção da largura do perfil.", "Largura")
        self.comp = s2.linha("altura", P.numero(300.0), "Medida na direção da altura do perfil.",
                             "Comprimento")
        self.esp = s2.linha("espessura", P.numero(16.0, maximo=200.0), "Espessura da placa.", "Espessura")
        self.material = s2.linha("material", QtWidgets.QLineEdit(_ultimo_material()), "Material da placa.",
                                 "Material")
        s3 = f.secao("Furação", "furo")
        self.furos = s3.linha("quantidade", P.lista(["0", "2", "4"], "4"), "Quantidade de furos para os "
                              "chumbadores.", "Furos")
        self.diam = s3.linha("furo", P.numero(22.0, maximo=200.0), "Diâmetro do furo.", "Diâmetro")
        self.borda = s3.linha("folga", P.numero(40.0, maximo=500.0), "Distância do centro do furo até a "
                              "borda da placa.", "Furo até a borda")

    def ponta_da(self, b):
        e = self.ponta.currentText()
        return _ponta_de_baixo(b) if e == "Ponta de baixo" else (0 if e == "Início" else 1)

    def props(self):
        return dict(Largura=self.larg.value(), Comprimento=self.comp.value(), Espessura=self.esp.value(),
                    Furos=self.furos.currentText(), DiametroFuro=self.diam.value(),
                    DistanciaBorda=self.borda.value(), Material=self.material.text().strip())

    def carregar(self, obj):
        self.barras.maximo = 1
        if obj.Barra is not None:
            self.barras.aceitar(obj.Barra)
        self.ponta.setCurrentText(obj.Ponta)
        self.larg.setValue(obj.Largura.Value)
        self.comp.setValue(obj.Comprimento.Value)
        self.esp.setValue(obj.Espessura.Value)
        self.furos.setCurrentText(obj.Furos)
        self.diam.setValue(obj.DiametroFuro.Value)
        self.borda.setValue(obj.DistanciaBorda.Value)
        self.material.setText(obj.Material)

    def props_edicao(self):
        b = self.barras.valores()[0]
        return dict(self.props(), Barra=b, Ponta=PONTAS[self.ponta_da(b)])

    def executar(self):
        _guardar_material(self.material.text().strip())
        feitos = [criar_placa_base(b, PONTAS[self.ponta_da(b)], **self.props()) for b in self.barras.valores()]
        _relatar(feitos)
        return feitos


class PainelSolda(P.PainelTarefa):
    titulo = "Cordão de solda"
    previa = True
    ajuda = "Selecione a estrutura inteira (solda todas as juntas) ou duas ou mais peças que se tocam."

    def montar(self):
        f = self.form
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        s1 = f.secao("Peças", "selecao")
        self.pecas = f.caixa(s1, "Estrutura ou peças", _filtro_pecas_ou_estrutura, minimo=1,
                             dica="Estrutura: um cordão em cada junta. Peças: um cordão nas linhas de contato.")
        s2 = f.secao("Cordão", "solda")
        self.perna = s2.linha("perna", P.numero(g.GetFloat("UltimaPernaSolda", 5.0), maximo=50.0),
                              "Perna (z) do filete: o lado do triângulo da solda.", "Perna do filete (z)")
        self.processo = s2.linha("processo", P.lista(PROCESSOS, g.GetString("UltimoProcessoSolda", PROCESSOS[0])),
                                 "Processo de soldagem (vai para a lista de soldas).", "Processo")
        self.eletrodo = s2.linha("eletrodo", QtWidgets.QLineEdit(g.GetString("UltimoEletrodo", "")),
                                 "Consumível: eletrodo revestido ou arame.", "Eletrodo / arame")
        self.eletrodo.setPlaceholderText("ex.: E7018, ER70S-6")
        self.obs = s2.linha("texto", QtWidgets.QLineEdit(), "Observação livre (ex.: solda contínua).",
                            "Observação")

    def _divide(self):
        vs = self.pecas.valores()
        return [o for o in vs if E.eh_estrutura(o)], [o for o in vs if not E.eh_estrutura(o)]

    def pendencia(self):
        ests, pecas = self._divide()
        if ests:
            return None
        if len(pecas) < 2:
            return "Selecione a estrutura inteira ou duas ou mais peças que se tocam."
        return None

    def pronto_texto(self):
        ests, _p = self._divide()
        if ests:
            return "Pronto: um cordão em cada junta de %s." % ", ".join(e.Label for e in ests)
        return "Pronto: um cordão nas linhas de contato entre as peças."

    def carregar(self, obj):
        for p in obj.Pecas:
            if p is not None:
                self.pecas.aceitar(p)
        self.perna.setValue(obj.Perna.Value)
        self.processo.setCurrentText(obj.Processo)
        self.eletrodo.setText(obj.Eletrodo)
        self.obs.setText(obj.Observacao)

    def props_edicao(self):
        _ests, pecas = self._divide()
        return dict(Pecas=pecas, Perna=self.perna.value(), Processo=self.processo.currentText(),
                    Eletrodo=self.eletrodo.text().strip(), Observacao=self.obs.text().strip())

    def guardar(self):
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        g.SetFloat("UltimaPernaSolda", self.perna.value())
        g.SetString("UltimoProcessoSolda", self.processo.currentText())
        g.SetString("UltimoEletrodo", self.eletrodo.text().strip())

    def executar(self):
        self.guardar()
        ests, pecas = self._divide()
        args = (self.perna.value(), self.processo.currentText(), self.eletrodo.text().strip(),
                self.obs.text().strip())
        if ests:
            feitos = []
            for est in ests:
                feitos += soldar_estrutura(est, *args)
            return feitos
        feitos = [criar_solda(pecas, *args)]
        _relatar(feitos)
        return feitos


def painel_de(obj):
    """Classe do painel que edita o objeto (ou None)."""
    proxy = getattr(obj, "Proxy", None)
    return {Reforco: PainelReforco, Tampa: PainelTampa, PlacaBase: PainelPlaca,
            Solda: PainelSolda}.get(type(proxy))


def abrir_edicao(obj):
    cls = painel_de(obj)
    if cls is None or not FreeCAD.GuiUp:
        return None
    FreeCADGui.Selection.clearSelection()
    p = cls()
    p.editar_objeto(obj)
    return p.mostrar()


def juntas_da_estrutura(est):
    """Pares de barras que se tocam (cantos, ligações em T e nós múltiplos)."""
    eds = E.arestas_ativas(est)
    bs = {b.Indice: b for b in E.barras_de(est)}
    pares = []
    for i in range(len(eds)):
        if eds[i] is None:
            continue
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
    if ruins and P.EM_PREVIA["ativa"]:   # prévia: os avisos aparecem no próprio painel
        P.EM_PREVIA["avisos"] += ["%s: %s" % (o.Label, "; ".join(o.Avisos)) for o in ruins]
        return
    if ruins:
        _aviso("Prumo 3D", "\n".join("%s: %s" % (o.Label, "; ".join(o.Avisos)) for o in ruins))


class CmdReforco:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("reforco.svg"), "MenuText": "Reforço",
                "ToolTip": "Mão-francesa (gusset) triangular ou poligonal no canto entre duas barras, "
                           "apoiada nas faces internas, com chanfro para a solda. Selecione as barras antes "
                           "ou depois de abrir o painel."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelReforco().mostrar()


class CmdTampa:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("tampa.svg"), "MenuText": "Tampa de extremidade",
                "ToolTip": "Fecha as pontas dos tubos, por fora ou por dentro, com folga para a solda."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelTampa().mostrar()


class CmdPlacaBase:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("placa_base.svg"), "MenuText": "Placa de base",
                "ToolTip": "Sapata com furação na ponta das colunas."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelPlaca().mostrar()


class CmdSolda:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("solda.svg"), "MenuText": "Cordão de solda",
                "ToolTip": "Cordão de filete entre peças (barras, reforços, placas). Com a estrutura "
                           "selecionada, solda todas as juntas."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelSolda().mostrar()


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
