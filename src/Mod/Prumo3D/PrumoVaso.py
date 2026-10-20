# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - assistente de vaso de pressão (costado, tampos e bocais, com espessuras calculadas).
"""Vaso de pressão horizontal: costado cilíndrico, dois tampos e bocais radiais.

Espessuras mínimas pelas fórmulas do ASME BPVC Seção VIII, Divisão 1 (pressão interna):
- costado, tensão circunferencial (UG-27(c)(1)):  t = P·R / (S·E − 0,6·P)
- costado, tensão longitudinal (UG-27(c)(2)):     t = P·R / (2·S·E + 0,4·P)
- tampo elíptico 2:1 (UG-32(d)):                  t = P·D / (2·S·E − 0,2·P)
- tampo torisférico, L = diâmetro externo e r = 6 % de L (UG-32(e)):  t = 0,885·P·L / (S·E − 0,1·P)
- tampo hemisférico (UG-32(f)):                   t = P·L / (2·S·E − 0,2·P)
com R, D e L internos já somados à sobre-espessura de corrosão (raio + CA). No torisférico padrão o raio
interno da coroa L é igual ao diâmetro externo do rebordo (D + 2·t), por isso t é resolvido junto com L.
A eficiência E da junta longitudinal é usada também nos tampos (tampo sem costura: informe E conforme
UW-12). Limites de aplicação verificados (avisos): costado P ≤ 0,385·S·E e t ≤ R/2; longitudinal
P ≤ 1,25·S·E; hemisférico P ≤ 0,665·S·E e t ≤ 0,356·L; elíptico e torisférico t/L ≥ 0,002. A espessura adotada
é a mínima mais a corrosão; a PMTA (pressão máxima de trabalho admissível) é recalculada com a
espessura adotada menos a corrosão.

A tensão admissível S é informada pelo usuário (ASME Seção II, Parte D, para o material e a
temperatura de projeto): o Prumo não sugere valores. Reforço de aberturas (UG-37), pressão
externa/vácuo (UG-28), cargas de vento/sismo e apoios NÃO são calculados. O resultado é um
pré-dimensionamento: a edição vigente do código e o projeto final ficam com o responsável técnico.
"""

import math

import FreeCAD
import FreeCADGui

import PrumoUtil
from PrumoUtil import fmt

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets

TAMPOS = ["Elíptico 2:1", "Torisférico (L = D ext., r = 6 %)", "Hemisférico"]


def tipo_tampo(tipo):
    """Índice do tipo de tampo (0 elíptico, 1 torisférico, 2 hemisférico); aceita rótulos antigos."""
    t = (tipo or "").lower()
    if t.startswith("tori"):
        return 1
    if t.startswith("hemi"):
        return 2
    if t.startswith("el") or t.startswith("elí"):
        return 0
    raise ValueError("tipo de tampo desconhecido: %s" % tipo)
MPA_KGF = 10.1971621  # 1 MPa = 10,197 kgf/cm²


# ============================================================================ cálculo
class Calculo:
    def __init__(self, D, P, S, E, CA=0.0, tampo=TAMPOS[0], E_circ=None):
        """D interno (mm), P (MPa), S (MPa), E eficiência da junta longitudinal (0–1),
        CA corrosão (mm), E_circ eficiência da junta circunferencial (padrão = E)."""
        if D <= 0 or P <= 0 or S <= 0 or not (0 < E <= 1) or CA < 0:
            raise ValueError("Diâmetro, pressão, tensão admissível e eficiência precisam ser positivos "
                             "(eficiência até 1; corrosão não negativa).")
        self.D, self.P, self.S, self.E, self.CA = float(D), float(P), float(S), float(E), float(CA)
        self.E_circ = float(E_circ) if E_circ else self.E
        if not (0 < self.E_circ <= 1):
            raise ValueError("Eficiência da junta circunferencial fora de 0–1.")
        self.tampo = tampo
        self.tipo = tipo_tampo(tampo)
        Rc = self.D / 2.0 + self.CA
        Dc = self.D + 2 * self.CA
        P, S, E, Ec = self.P, self.S, self.E, self.E_circ

        def div(num, den, onde):
            if den <= 0:
                raise ValueError("Pressão alta demais para a fórmula do %s (denominador ≤ 0): "
                                 "aumente S·E ou reduza P." % onde)
            return num / den

        self.t_circ = div(P * Rc, S * E - 0.6 * P, "costado")
        self.t_long = div(P * Rc, 2 * S * Ec + 0.4 * P, "costado")
        self.t_costado = max(self.t_circ, self.t_long)
        self.L_tampo = None
        if self.tipo == 0:
            self.t_tampo = div(P * Dc, 2 * S * E - 0.2 * P, "tampo elíptico")
        elif self.tipo == 1:
            # L (corroído) = D + 2·(t + CA) + CA  →  t = k·(D + 3·CA) / (1 − 2k)
            k = div(0.885 * P, S * E - 0.1 * P, "tampo torisférico")
            self.t_tampo = div(k * (self.D + 3 * self.CA), 1 - 2 * k, "tampo torisférico")
            self.L_tampo = self.D + 2 * (self.t_tampo + self.CA) + self.CA
        else:
            self.t_tampo = div(P * Rc, 2 * S * E - 0.2 * P, "tampo hemisférico")
            self.L_tampo = Rc
        self.avisos = []
        if P > 0.385 * S * E:
            self.avisos.append("P > 0,385·S·E: fora do limite de aplicação da fórmula do costado "
                               "(conferir UG-27 e Apêndice 1-2).")
        if self.t_circ > Rc / 2.0:
            self.avisos.append("Espessura maior que metade do raio: casca espessa (conferir Apêndice 1-2).")
        if P > 1.25 * S * Ec:
            self.avisos.append("P > 1,25·S·E: fora do limite da fórmula longitudinal (conferir UG-27(c)(2)).")
        if self.tipo == 2:
            if P > 0.665 * S * E:
                self.avisos.append("P > 0,665·S·E: fora do limite da fórmula do tampo hemisférico.")
            if self.t_tampo > 0.356 * self.L_tampo:
                self.avisos.append("t > 0,356·L: tampo hemisférico espesso (conferir Apêndice 1-3).")
        else:
            L_ref = 0.9 * Dc if self.tipo == 0 else self.L_tampo
            if self.t_tampo / L_ref < 0.002:
                self.avisos.append("t/L < 0,002: fora do limite das fórmulas de UG-32 para este tampo "
                                   "(conferir Apêndice 1-4).")

    def minimos_com_corrosao(self):
        return self.t_costado + self.CA, self.t_tampo + self.CA

    def pmta_costado(self, t_adotada):
        """PMTA do costado com a espessura adotada (MPa)."""
        tc = t_adotada - self.CA
        Rc = self.D / 2.0 + self.CA
        if tc <= 0:
            return 0.0
        p1 = self.S * self.E * tc / (Rc + 0.6 * tc)
        den2 = Rc - 0.4 * tc
        p2 = 2 * self.S * self.E_circ * tc / den2 if den2 > 0 else float("inf")
        return min(p1, p2)

    def pmta_tampo(self, t_adotada):
        tc = t_adotada - self.CA
        Dc = self.D + 2 * self.CA
        Rc = Dc / 2.0
        if tc <= 0:
            return 0.0
        S, E = self.S, self.E
        if self.tipo == 0:
            return 2 * S * E * tc / (Dc + 0.2 * tc)
        if self.tipo == 1:
            L = self.D + 2 * t_adotada + self.CA  # coroa = diâmetro externo, corroída
            return S * E * tc / (0.885 * L + 0.1 * tc)
        return 2 * S * E * tc / (Rc + 0.2 * tc)


# espessuras de chapa em frações de polegada (conversão exata); disponibilidade comercial: a conferir
CHAPAS_MM = [4.76, 6.35, 7.94, 9.53, 11.11, 12.70, 15.88, 19.05, 22.23, 25.40, 28.58, 31.75, 34.93,
             38.10, 44.45, 50.80, 57.15, 63.50, 76.20]


def chapa_acima(t):
    """Primeira espessura da lista igual ou maior que t (mm)."""
    for c in CHAPAS_MM:
        if c >= t - 1e-9:
            return c
    return math.ceil(t)


# ============================================================================ geometria
def _domo(R, perfil, apice_x):
    """Sólido de revolução (eixo X) entre o plano x = 0, o eixo e a curva `perfil` (0,R)→(apice_x,0)."""
    import Part
    linhas = list(perfil.Edges) + [
        Part.LineSegment(FreeCAD.Vector(apice_x, 0, 0), FreeCAD.Vector(0, 0, 0)).toShape(),
        Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, R, 0)).toShape()]
    w = Part.Wire(Part.__sortEdges__(linhas))
    f = Part.Face(w)
    return f.revolve(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 360)


def _curva_eliptica(a, b):
    """Quarto de elipse de (0, a) até (-b, 0) — semieixo radial a, axial b."""
    import Part
    if a < b:
        raise ValueError("elipse inválida")
    # Part.Ellipse(ponta do eixo maior, ponta do eixo menor, centro): maior na radial (Y)
    el = Part.Ellipse(FreeCAD.Vector(0, a, 0), FreeCAD.Vector(-b, 0, 0), FreeCAD.Vector(0, 0, 0))
    u1 = el.parameter(FreeCAD.Vector(0, a, 0))
    u2 = el.parameter(FreeCAD.Vector(-b, 0, 0))
    if u2 < u1:
        u1, u2 = u2, u1
    if u2 - u1 > math.pi:  # pega o quarto de elipse, não os outros três
        u1, u2 = u2, u1 + 2 * math.pi
    return Part.ArcOfEllipse(el, u1, u2).toShape()


def _curva_torisferica(Ri, L, r):
    """Perfil interno torisférico: raio de rebordo r tangente ao costado e coroa de raio L."""
    import Part
    K = FreeCAD.Vector(0, Ri - r, 0)
    cx = math.sqrt((L - r) ** 2 - (Ri - r) ** 2)
    C = FreeCAD.Vector(cx, 0, 0)
    d = (K - C)
    d.normalize()
    T = K + d * r  # ponto de tangência entre rebordo e coroa
    meio_k = K + (d + FreeCAD.Vector(0, 1, 0)).normalize() * r
    arco_k = Part.Arc(FreeCAD.Vector(0, Ri, 0), meio_k, T).toShape()
    apice = FreeCAD.Vector(cx - L, 0, 0)
    dm = (T - C) + (apice - C)
    dm.normalize()
    arco_c = Part.Arc(T, C + dm * L, apice).toShape()
    return Part.Wire([arco_k, arco_c]), cx - L


def tampo(Ri, t, tipo):
    """Tampo com a face plana em x = 0 voltado para x negativo."""
    import Part
    Ro = Ri + t
    n = tipo_tampo(tipo)
    if n == 0:
        dentro = _domo(Ri, _curva_eliptica(Ri, Ri / 2.0), -Ri / 2.0)
        fora = _domo(Ro, _curva_eliptica(Ro, Ri / 2.0 + t), -(Ri / 2.0 + t))
    elif n == 1:
        L, r = _coroa_rebordo(Ri, t)
        wi, ai = _curva_torisferica(Ri, L, r)
        wo, ao = _curva_torisferica_externa(Ri, L, r, t)
        dentro = _domo(Ri, wi, ai)
        fora = _domo(Ro, wo, ao)
    else:
        s_i = Part.makeSphere(Ri)
        s_o = Part.makeSphere(Ro)
        meio = Part.makeBox(2 * Ro, 4 * Ro, 4 * Ro, FreeCAD.Vector(-2 * Ro, -2 * Ro, -2 * Ro))
        dentro = s_i.common(meio)
        fora = s_o.common(meio)
    return fora.cut(dentro)


def _curva_torisferica_externa(Ri, L, r, t):
    """Mesmo centro dos arcos internos, raios r + t e L + t."""
    import Part
    K = FreeCAD.Vector(0, Ri - r, 0)
    cx = math.sqrt((L - r) ** 2 - (Ri - r) ** 2)
    C = FreeCAD.Vector(cx, 0, 0)
    d = (K - C)
    d.normalize()
    T = K + d * (r + t)
    meio_k = K + (d + FreeCAD.Vector(0, 1, 0)).normalize() * (r + t)
    arco_k = Part.Arc(FreeCAD.Vector(0, Ri + t, 0), meio_k, T).toShape()
    apice = FreeCAD.Vector(cx - (L + t), 0, 0)
    dm = (T - C) + (apice - C)
    dm.normalize()
    arco_c = Part.Arc(T, C + dm * (L + t), apice).toShape()
    return Part.Wire([arco_k, arco_c]), cx - (L + t)


def _coroa_rebordo(Ri, t):
    """Torisférico padrão: raio interno da coroa L = diâmetro externo (2·Ri + 2·t); rebordo r = 6 % de L."""
    L = 2 * Ri + 2 * t
    return L, 0.06 * L


def altura_tampo(Ri, t, tipo):
    n = tipo_tampo(tipo)
    if n == 0:
        return Ri / 2.0 + t
    if n == 1:
        L, r = _coroa_rebordo(Ri, t)
        cx = math.sqrt((L - r) ** 2 - (Ri - r) ** 2)
        return (L + t) - cx
    return Ri + t


def geometria(D, comp, t_costado, t_tampo, tipo_tampo, bocais=()):
    """Sólido do vaso (eixo X, costado de x = 0 a x = comp). bocais: [(x, ângulo°, De, esp, projeção)]."""
    import Part
    Ri = D / 2.0
    Ro = Ri + t_costado
    eixo = FreeCAD.Vector(1, 0, 0)
    cost = Part.makeCylinder(Ro, comp, FreeCAD.Vector(), eixo).cut(Part.makeCylinder(Ri, comp, FreeCAD.Vector(), eixo))
    t1 = tampo(Ri, t_tampo, tipo_tampo)
    t2 = t1.mirror(FreeCAD.Vector(comp / 2.0, 0, 0), eixo)
    if abs(t_tampo - t_costado) > 1e-9:
        # transição: o tampo encosta no costado pelo diâmetro interno
        pass
    vaso = cost.fuse([t1, t2])
    furos = []
    for (x, ang, De, esp, proj) in bocais:
        a = math.radians(ang)
        d = FreeCAD.Vector(0, math.cos(a), math.sin(a))
        base = FreeCAD.Vector(x, 0, 0)
        tubo = Part.makeCylinder(De / 2.0, Ro + proj, base, d).cut(
            Part.makeCylinder(De / 2.0 - esp, Ro + proj, base, d))
        tubo = tubo.cut(Part.makeCylinder(Ri, comp, FreeCAD.Vector(), eixo))
        vaso = vaso.fuse(tubo)
        furos.append(Part.makeCylinder(De / 2.0 - esp, Ro + proj, base, d))
    for f in furos:
        vaso = vaso.cut(f)
    vaso = vaso.removeSplitter()
    return vaso


def volume_interno(D, comp, tipo, t_tampo=0.0):
    """Volume interno (m³): costado + 2 tampos (fórmulas de volume interno dos tampos)."""
    Ri = D / 2.0
    v = math.pi * Ri ** 2 * comp
    n = tipo_tampo(tipo)
    if n == 0:
        vt = 2.0 / 3.0 * math.pi * Ri ** 2 * (Ri / 2.0)
    elif n == 2:
        vt = 2.0 / 3.0 * math.pi * Ri ** 3
    else:
        vt = None
    if vt is None:
        L, r = _coroa_rebordo(Ri, t_tampo)
        wi, ai = _curva_torisferica(Ri, L, r)
        vt = _domo(Ri, wi, ai).Volume
    return (v + 2 * vt) * 1e-9


# ============================================================================ objeto
class Vaso:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyLength", "DiametroInterno", "Projeto", "Diâmetro interno do costado", 1000.0)
        add("App::PropertyLength", "ComprimentoCostado", "Projeto", "Comprimento entre linhas de tangência", 2000.0)
        add("App::PropertyFloat", "PressaoProjeto", "Projeto", "Pressão de projeto (MPa, manométrica)", 1.0)
        add("App::PropertyString", "TemperaturaProjeto", "Projeto", "Temperatura de projeto (texto)", "")
        add("App::PropertyString", "MaterialChapa", "Projeto", "Especificação do material", "")
        add("App::PropertyFloat", "TensaoAdmissivel", "Projeto",
            "Tensão admissível S na temperatura de projeto (MPa) — ASME II-D", 0.0)
        add("App::PropertyFloat", "EficienciaJunta", "Projeto", "Eficiência da junta longitudinal E (0–1)", 1.0)
        add("App::PropertyLength", "Corrosao", "Projeto", "Sobre-espessura de corrosão", 0.0)
        add("App::PropertyEnumeration", "TipoTampo", "Projeto", "Tipo de tampo")
        if not obj.TipoTampo:
            obj.TipoTampo = TAMPOS
        add("App::PropertyLength", "EspessuraCostado", "Adotado", "Espessura adotada do costado (0 = automática)", 0.0)
        add("App::PropertyLength", "EspessuraTampo", "Adotado", "Espessura adotada dos tampos (0 = automática)", 0.0)
        add("App::PropertyStringList", "Bocais", "Adotado",
            "Bocais: 'posição mm; ângulo °; perfil do tubo; projeção mm' por linha")
        for n, d in (("MinimoCostado", "Espessura mínima do costado com corrosão (mm)"),
                     ("MinimoTampo", "Espessura mínima do tampo com corrosão (mm)"),
                     ("PMTACostado", "PMTA do costado com a espessura adotada (MPa)"),
                     ("PMTATampo", "PMTA do tampo com a espessura adotada (MPa)"),
                     ("VolumeInterno", "Volume interno (m³)"), ("MassaVazio", "Massa vazio (kg, aço)")):
            add("App::PropertyFloat", n, "Resultados", d, 0.0, ro=True)
        add("App::PropertyStringList", "Avisos", "Resultados", "Avisos do cálculo", [], ro=True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def calculo(self, obj):
        return Calculo(obj.DiametroInterno.Value, obj.PressaoProjeto, obj.TensaoAdmissivel,
                       obj.EficienciaJunta, obj.Corrosao.Value, obj.TipoTampo)

    def execute(self, obj):
        if obj.TensaoAdmissivel <= 0:
            obj.Avisos = ["Informe a tensão admissível S do material (ASME II-D)."]
            return
        try:
            c = self.calculo(obj)
        except (ValueError, ZeroDivisionError) as ex:
            obj.Avisos = ["Cálculo não realizado: %s" % ex]
            for n in ("MinimoCostado", "MinimoTampo", "PMTACostado", "PMTATampo"):
                setattr(obj, n, 0.0)
            return
        mc, mt = c.minimos_com_corrosao()
        tc = obj.EspessuraCostado.Value or chapa_acima(mc)
        tt = obj.EspessuraTampo.Value or chapa_acima(mt)
        avisos = list(c.avisos)
        if tc < mc - 1e-9:
            avisos.append("Espessura adotada do costado menor que a mínima.")
        if tt < mt - 1e-9:
            avisos.append("Espessura adotada do tampo menor que a mínima.")
        bocais = []
        for linha in obj.Bocais:
            b = interpretar_bocal(linha)
            if b is None:
                avisos.append("Bocal não reconhecido: %s" % linha)
                continue
            raio_bocal = b[2] / 2.0
            if b[0] - raio_bocal < 0 or b[0] + raio_bocal > obj.ComprimentoCostado.Value:
                avisos.append("Bocal fora do costado (posição de 0 a %s, com o tubo inteiro): %s — ignorado."
                              % (fmt(obj.ComprimentoCostado.Value, 0, "mm"), linha))
                continue
            bocais.append(b)
        obj.Shape = geometria(obj.DiametroInterno.Value, obj.ComprimentoCostado.Value, tc, tt, obj.TipoTampo, bocais)
        obj.MinimoCostado = mc
        obj.MinimoTampo = mt
        obj.PMTACostado = c.pmta_costado(tc)
        obj.PMTATampo = c.pmta_tampo(tt)
        obj.VolumeInterno = volume_interno(obj.DiametroInterno.Value, obj.ComprimentoCostado.Value, obj.TipoTampo, tt)
        obj.MassaVazio = obj.Shape.Volume * 7850e-9
        obj.Avisos = avisos

    def dumps(self):
        return None

    def loads(self, state):
        return None


def interpretar_bocal(linha):
    """'1200; 90; Tubo 2" Sch 40; 150' -> (x, ângulo, De, esp, projeção)."""
    import PrumoPerfis
    partes = [p.strip() for p in linha.split(";")]
    if len(partes) != 4:
        return None
    try:
        x = float(partes[0].replace(",", "."))
        ang = float(partes[1].replace(",", "."))
        proj = float(partes[3].replace(",", "."))
    except ValueError:
        return None
    it = PrumoPerfis.perfil(partes[2])
    if it is None or it["tipo"] != "TUBO":
        return None
    return (x, ang, it["D"], it["esp"], proj)


class VPVaso:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        return PrumoUtil.icone("vaso.svg")

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc, D, comp, P, S, E, CA=0.0, tipo=TAMPOS[0], material="", temperatura="", bocais=(),
          t_costado=0.0, t_tampo=0.0):
    doc.openTransaction("Vaso de pressão")
    v = doc.addObject("Part::FeaturePython", "VasoDePressao")
    v.Label = "Vaso de pressão"
    Vaso(v)
    v.DiametroInterno = D
    v.ComprimentoCostado = comp
    v.PressaoProjeto = P
    v.TensaoAdmissivel = S
    v.EficienciaJunta = E
    v.Corrosao = CA
    v.TipoTampo = tipo
    v.MaterialChapa = material
    v.TemperaturaProjeto = temperatura
    v.Bocais = list(bocais)
    v.EspessuraCostado = t_costado
    v.EspessuraTampo = t_tampo
    if FreeCAD.GuiUp:
        VPVaso(v.ViewObject)
    doc.recompute()
    doc.commitTransaction()
    return v


def memoria(v):
    """Memória de cálculo (texto)."""
    try:
        c = v.Proxy.calculo(v)
    except (ValueError, ZeroDivisionError) as ex:
        return "Vaso de pressão — cálculo não realizado: %s" % ex
    L = ["Vaso de pressão — memória de pré-dimensionamento (Prumo 3D)",
         "Referência: ASME BPVC Seção VIII, Divisão 1 — UG-27 (costado) e UG-32 (tampos). "
         "Conferir a edição vigente.", ""]
    L.append("Diâmetro interno: %s   Comprimento entre tangentes: %s" % (
        fmt(v.DiametroInterno.Value, 1, "mm"), fmt(v.ComprimentoCostado.Value, 1, "mm")))
    L.append("Pressão de projeto: %s (%s)   Temperatura: %s" % (
        fmt(v.PressaoProjeto, 3, "MPa"), fmt(v.PressaoProjeto * MPA_KGF, 2, "kgf/cm²"), v.TemperaturaProjeto or "—"))
    L.append("Material: %s   S = %s   E = %s   Corrosão = %s" % (
        v.MaterialChapa or "—", fmt(v.TensaoAdmissivel, 1, "MPa"), fmt(v.EficienciaJunta, 2),
        fmt(v.Corrosao.Value, 2, "mm")))
    L.append("")
    L.append("Costado — circunferencial: t = P·R/(S·E − 0,6·P) = %s" % fmt(c.t_circ, 3, "mm"))
    L.append("Costado — longitudinal:    t = P·R/(2·S·E + 0,4·P) = %s" % fmt(c.t_long, 3, "mm"))
    form = {0: "t = P·D/(2·S·E − 0,2·P)", 1: "t = 0,885·P·L/(S·E − 0,1·P)", 2: "t = P·L/(2·S·E − 0,2·P)"}[c.tipo]
    L.append("Tampo (%s): %s = %s" % (v.TipoTampo, form, fmt(c.t_tampo, 3, "mm")))
    if c.tipo == 1:
        L.append("  L = raio interno da coroa = diâmetro externo do rebordo (corroído) = %s; r = 6 %% de L"
                 % fmt(c.L_tampo, 1, "mm"))
    L.append("  E usado nos tampos = %s (mesma eficiência da junta longitudinal; tampo sem costura: "
             "conferir UW-12)" % fmt(c.E, 2))
    L.append("Mínimas com corrosão: costado %s, tampo %s" % (fmt(v.MinimoCostado, 2, "mm"), fmt(v.MinimoTampo, 2, "mm")))
    tc = v.EspessuraCostado.Value or chapa_acima(v.MinimoCostado)
    tt = v.EspessuraTampo.Value or chapa_acima(v.MinimoTampo)
    L.append("Adotadas: costado %s, tampo %s" % (fmt(tc, 2, "mm"), fmt(tt, 2, "mm")))
    L.append("PMTA (espessura adotada − corrosão): costado %s, tampo %s → vaso %s" % (
        fmt(v.PMTACostado, 3, "MPa"), fmt(v.PMTATampo, 3, "MPa"), fmt(min(v.PMTACostado, v.PMTATampo), 3, "MPa")))
    L.append("Volume interno: %s   P·V: %s   Massa vazio (aço): %s" % (
        fmt(v.VolumeInterno, 3, "m³"), fmt(v.PressaoProjeto * v.VolumeInterno, 3, "MPa·m³"), fmt(v.MassaVazio, 1, "kg")))
    if v.Avisos:
        L.append("")
        L.append("Avisos:")
        L.extend("  • " + a for a in v.Avisos)
    L.append("")
    L.append("Não calculados: reforço de aberturas (UG-37), pressão externa/vácuo (UG-28), cargas de vento,")
    L.append("sismo, apoios e teste hidrostático. Enquadramento na NR-13: conferir no texto vigente.")
    return "\n".join(L)


# ============================================================================ interface
class DialogoVaso(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vaso de pressão")
        self.setMinimumWidth(620)
        lay = QtWidgets.QHBoxLayout(self)
        esq = QtWidgets.QVBoxLayout()
        form = QtWidgets.QFormLayout()

        def num(v, mn, mx, dec, suf):
            w = QtWidgets.QDoubleSpinBox()
            w.setRange(mn, mx)
            w.setDecimals(dec)
            w.setValue(v)
            w.setSuffix(suf)
            w.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
            w.valueChanged.connect(self.atualizar)
            return w

        self.D = num(1000, 50, 20000, 1, " mm")
        self.L = num(2000, 0, 100000, 1, " mm")
        self.P = num(1.0, 0.001, 100, 3, " MPa")
        self.S = num(0.0, 0.0, 2000, 1, " MPa")
        self.S.setSpecialValueText("informe (ASME II-D)")
        self.E = QtWidgets.QComboBox()
        for v, txt in ((1.0, "1,00 — radiografia total"), (0.85, "0,85 — radiografia por amostragem"),
                       (0.70, "0,70 — sem radiografia")):
            self.E.addItem(txt, v)
        self.E.currentIndexChanged.connect(self.atualizar)
        self.CA = num(0.0, 0, 20, 2, " mm")
        self.tampo = QtWidgets.QComboBox()
        self.tampo.addItems(TAMPOS)
        self.tampo.currentIndexChanged.connect(self.atualizar)
        self.material = QtWidgets.QLineEdit()
        self.material.setPlaceholderText("ex.: ASTM A516 Gr. 70")
        self.temp = QtWidgets.QLineEdit()
        self.temp.setPlaceholderText("ex.: 150 °C")
        for rot, w in (("Diâmetro interno", self.D), ("Comprimento entre tangentes", self.L),
                       ("Pressão de projeto", self.P), ("Tensão admissível S", self.S),
                       ("Eficiência da junta E", self.E), ("Sobre-espessura de corrosão", self.CA),
                       ("Tampos", self.tampo), ("Material", self.material), ("Temperatura de projeto", self.temp)):
            form.addRow(rot, w)
        esq.addLayout(form)
        esq.addWidget(QtWidgets.QLabel("Bocais (posição mm; ângulo °; tubo; projeção mm), um por linha:"))
        self.bocais = QtWidgets.QPlainTextEdit()
        self.bocais.setPlaceholderText('300; 90; Tubo 2" Sch 40; 150')
        self.bocais.setMaximumHeight(90)
        esq.addWidget(self.bocais)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Criar vaso")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        esq.addWidget(bb)
        lay.addLayout(esq, 3)
        self.saida = QtWidgets.QTextBrowser()
        self.saida.setMinimumWidth(260)
        lay.addWidget(self.saida, 2)
        self.atualizar()

    def atualizar(self, *_a):
        if self.S.value() <= 0:
            self.saida.setHtml("<p style='color:#B5523F'>Informe a tensão admissível S do material na "
                               "temperatura de projeto (ASME Seção II, Parte D).</p>")
            return
        try:
            c = Calculo(self.D.value(), self.P.value(), self.S.value(), self.E.currentData(),
                        self.CA.value(), self.tampo.currentText())
        except (ValueError, ZeroDivisionError) as exc:
            self.saida.setHtml("<p style='color:#B5523F'>%s</p>" % exc)
            return
        mc, mt = c.minimos_com_corrosao()
        html = ["<h3 style='color:#003A70;margin:0'>Espessuras mínimas</h3>",
                "<p>Costado: <b>%s</b><br>Tampos: <b>%s</b></p>" % (fmt(mc, 2, "mm"), fmt(mt, 2, "mm")),
                "<p style='color:#5B6876'>Chapa sugerida: costado %s, tampos %s<br>"
                "(frações de polegada; disponibilidade a conferir)</p>" % (fmt(chapa_acima(mc), 2, "mm"),
                                                                            fmt(chapa_acima(mt), 2, "mm")),
                "<p>PMTA com essas chapas: <b>%s</b></p>" % fmt(min(c.pmta_costado(chapa_acima(mc)),
                                                                     c.pmta_tampo(chapa_acima(mt))), 3, "MPa")]
        for a in c.avisos:
            html.append("<p style='color:#B5523F'>%s</p>" % a)
        html.append("<p style='color:#5B6876;font-size:8pt'>ASME VIII-1, UG-27 e UG-32. Pré-dimensionamento: "
                    "não inclui reforço de aberturas (UG-37), vácuo (UG-28) nem apoios.</p>")
        self.saida.setHtml("".join(html))

    def _ok(self):
        if self.S.value() <= 0:
            QtWidgets.QMessageBox.warning(self, "Vaso de pressão", "Informe a tensão admissível S.")
            return
        try:
            Calculo(self.D.value(), self.P.value(), self.S.value(), self.E.currentData(),
                    self.CA.value(), self.tampo.currentText())
        except (ValueError, ZeroDivisionError) as exc:
            QtWidgets.QMessageBox.warning(self, "Vaso de pressão", str(exc))
            return
        linhas = [l.strip() for l in self.bocais.toPlainText().splitlines() if l.strip()]
        ruins = [l for l in linhas if interpretar_bocal(l) is None]
        if ruins:
            QtWidgets.QMessageBox.warning(self, "Vaso de pressão",
                                          "Bocal não reconhecido:\n%s\n\nUse: posição; ângulo; tubo (ex.: Tubo 2\" "
                                          "Sch 40); projeção" % "\n".join(ruins))
            return
        self.linhas_bocais = linhas
        self.accept()


class CmdVaso:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("vaso.svg"),
                "MenuText": "Vaso de pressão",
                "ToolTip": "Costado, tampos e bocais com espessuras pelo ASME VIII-1 (UG-27 e UG-32), "
                           "PMTA e memória de cálculo. Pré-dimensionamento."}

    def IsActive(self):
        return True

    def Activated(self):
        doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Vaso")
        d = DialogoVaso(FreeCADGui.getMainWindow())
        if not d.exec():
            return
        v = criar(doc, d.D.value(), d.L.value(), d.P.value(), d.S.value(), d.E.currentData(), d.CA.value(),
                  d.tampo.currentText(), d.material.text().strip(), d.temp.text().strip(),
                  getattr(d, "linhas_bocais", []))
        FreeCAD.Console.PrintMessage(memoria(v) + "\n")
        try:
            FreeCADGui.SendMsgToActiveView("ViewFit")
        except Exception:
            pass


class CmdMemoriaVaso:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("vaso.svg"),
                "MenuText": "Memória de cálculo do vaso",
                "ToolTip": "Mostra a memória de pré-dimensionamento do vaso selecionado, para copiar."}

    def IsActive(self):
        return any("PressaoProjeto" in o.PropertiesList for o in FreeCADGui.Selection.getSelection())

    def Activated(self):
        v = [o for o in FreeCADGui.Selection.getSelection() if "PressaoProjeto" in o.PropertiesList][0]
        d = QtWidgets.QDialog(FreeCADGui.getMainWindow())
        d.setWindowTitle("Memória de cálculo — " + v.Label)
        d.resize(700, 520)
        lay = QtWidgets.QVBoxLayout(d)
        t = QtWidgets.QPlainTextEdit(memoria(v))
        t.setReadOnly(True)
        lay.addWidget(t)
        b = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        b.rejected.connect(d.reject)
        lay.addWidget(b)
        d.exec()
