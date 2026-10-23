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
# unidades de pressão: (nome, MPa por unidade, casas). Por definição: 1 kgf/cm² = 98.066,5 Pa;
# 1 psi = 1 lbf/in² = 4,448 221 615 260 5 N / (0,0254 m)² = 6.894,757 Pa
UNIDADES_PRESSAO = [("MPa", 1.0, 3), ("kgf/cm²", 0.0980665, 2), ("psi", 0.006894757293168361, 1)]


def _unidade(nome):
    return next((u for u in UNIDADES_PRESSAO if u[0] == nome), UNIDADES_PRESSAO[0])


def fmt_p(mpa, unidade="MPa"):
    """Pressão na unidade escolhida, com a equivalência entre parênteses: '10,20 kgf/cm² (1,000 MPa)'.
    Em MPa, a equivalência mostrada é em kgf/cm²."""
    nome, fator, casas = _unidade(unidade)
    if nome == "MPa":
        return "%s (%s)" % (fmt(mpa, 3, "MPa"), fmt(mpa * MPA_KGF, 2, "kgf/cm²"))
    return "%s (%s)" % (fmt(mpa / fator, casas, nome), fmt(mpa, 3, "MPa"))


def _unid(v):
    return getattr(v, "UnidadePressao", "MPa") if "UnidadePressao" in getattr(v, "PropertiesList", []) else "MPa"
ORIENTACOES = ["Horizontal", "Vertical"]
SUPORTES = ["Nenhum", "Selas", "Saia", "Pernas"]
TESTES = ["Hidrostático (UG-99(b))", "Pneumático (UG-100)"]
EFICIENCIAS = [(1.0, "1,00 — radiografia total"), (0.85, "0,85 — radiografia por amostragem"),
               (0.70, "0,70 — sem radiografia")]
AGUA = 9.80665e-6     # MPa por mm de coluna d'água (ρ = 1000 kg/m³)


def s_estimado(sy, su):
    """Tensão admissível estimada pelos critérios da ASME II-D (Mandatory Appendix 1, abaixo da
    faixa de fluência): menor entre Su/3,5 e 2/3·Sy. Só referência: o valor de projeto é o da
    tabela 1A da Seção II-D para o material e a temperatura (a checar)."""
    if not sy or not su:
        return 0.0
    return min(su / 3.5, 2.0 * sy / 3.0)


def pressao_teste(pmta, S, S_amb=None, tipo=TESTES[0]):
    """Pressão de teste no topo do vaso (MPa): hidrostático 1,3·PMTA·(S_amb/S) — UG-99(b);
    pneumático 1,1·PMTA·(S_amb/S) — UG-100. Edição vigente do código: a checar."""
    r = (S_amb / S) if (S_amb and S) else 1.0
    k = 1.1 if tipo.startswith("Pneu") else 1.3
    return k * pmta * r


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


def suportes(tipo, D, comp, t_costado, t_tampo, tipo_tampo, pos_selas=0.0, altura=0.0, vertical=False):
    """Sólidos dos suportes no sistema do vaso (eixo X, costado de 0 a comp).
    Selas: duas chapas com berço de 120° (sela) a `pos_selas` das linhas de tangência (0 = 0,2·comp).
    Saia: cilindro abaixo do tampo de baixo (vaso vertical: x < 0). Pernas: quatro tubos."""
    import Part
    Ri = D / 2.0
    Ro = Ri + t_costado
    pecas = []
    if tipo == "Selas":
        a = pos_selas or 0.2 * comp
        h = altura or (Ro + 150.0)            # do eixo até o chão
        larg_sela = max(150.0, 0.2 * D)
        esp = 12.7
        for x in (a, comp - a):
            # chapa vertical (alma) em forma de berço: caixa menos o cilindro do vaso
            caixa = Part.makeBox(esp, 2 * Ro * 0.94, h, FreeCAD.Vector(x - esp / 2, -Ro * 0.94, -h))
            alma = caixa.cut(Part.makeCylinder(Ro, esp * 3, FreeCAD.Vector(x - esp * 1.5, 0, 0),
                                               FreeCAD.Vector(1, 0, 0)))
            base = Part.makeBox(larg_sela, 2 * Ro * 0.94, esp, FreeCAD.Vector(x - larg_sela / 2, -Ro * 0.94, -h))
            # berço: faixa de chapa curva abaixo do vaso (120°)
            ang = math.radians(60)
            berco = Part.makeCylinder(Ro + esp, larg_sela, FreeCAD.Vector(x - larg_sela / 2, 0, 0),
                                      FreeCAD.Vector(1, 0, 0)).cut(
                Part.makeCylinder(Ro, larg_sela, FreeCAD.Vector(x - larg_sela / 2, 0, 0), FreeCAD.Vector(1, 0, 0)))
            corte = Part.makeBox(larg_sela, 2 * (Ro + esp), (Ro + esp) * (1 + math.cos(ang)),
                                 FreeCAD.Vector(x - larg_sela / 2, -(Ro + esp), -(Ro + esp)))
            berco = berco.common(corte).common(
                Part.makeBox(larg_sela, 2 * (Ro + esp) * math.sin(ang), Ro + esp,
                             FreeCAD.Vector(x - larg_sela / 2, -(Ro + esp) * math.sin(ang), -(Ro + esp))))
            pecas += [alma, base, berco]
    elif tipo == "Saia":
        h = altura or max(500.0, 0.5 * D)
        ht = altura_tampo(Ri, t_tampo, tipo_tampo)
        x0 = -max(h, ht + 100.0)
        saia = Part.makeCylinder(Ro, -x0, FreeCAD.Vector(x0, 0, 0), FreeCAD.Vector(1, 0, 0)).cut(
            Part.makeCylinder(Ro - t_costado, -x0, FreeCAD.Vector(x0, 0, 0), FreeCAD.Vector(1, 0, 0)))
        anel = Part.makeCylinder(Ro + 80, 16, FreeCAD.Vector(x0, 0, 0), FreeCAD.Vector(1, 0, 0)).cut(
            Part.makeCylinder(Ro - t_costado - 80, 16, FreeCAD.Vector(x0, 0, 0), FreeCAD.Vector(1, 0, 0)))
        pecas += [saia, anel]
    elif tipo == "Pernas":
        h = altura or max(600.0, 0.6 * D)
        ht = altura_tampo(Ri, t_tampo, tipo_tampo)
        De = 88.9 if D < 1200 else 141.3
        for k in range(4):
            a = math.radians(45 + 90 * k)
            c = FreeCAD.Vector(0, (Ro + De / 2) * math.cos(a), (Ro + De / 2) * math.sin(a))
            perna = Part.makeCylinder(De / 2, h + 300.0, c + FreeCAD.Vector(-(ht + h), 0, 0), FreeCAD.Vector(1, 0, 0))
            perna = perna.cut(Part.makeCylinder(De / 2 - 5.5, h + 300.0, c + FreeCAD.Vector(-(ht + h), 0, 0),
                                                FreeCAD.Vector(1, 0, 0)))
            pecas.append(perna)
    return pecas


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
        if "UnidadePressao" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "UnidadePressao", "Projeto",
                            "Unidade em que as pressões aparecem no painel, na memória e no desenho (o cálculo é em MPa)")
            obj.UnidadePressao = [u[0] for u in UNIDADES_PRESSAO]
            obj.UnidadePressao = "MPa"
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
        if "Orientacao" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Orientacao", "Projeto", "Horizontal ou vertical")
            obj.Orientacao = ORIENTACOES
        if "Suportes" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Suportes", "Adotado", "Selas, saia ou pernas")
            obj.Suportes = SUPORTES
        add("App::PropertyLength", "PosicaoSelas", "Adotado", "Selas: distância da linha de tangência (0 = 0,2·L)",
            0.0)
        add("App::PropertyLength", "AlturaSuporte", "Adotado", "Altura do suporte (0 = automática)", 0.0)
        add("App::PropertyFloat", "TensaoAdmissivelTeste", "Projeto",
            "Tensão admissível S na temperatura do teste (MPa; 0 = igual a S)", 0.0)
        if "TipoTeste" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "TipoTeste", "Teste", "Teste de pressão")
            obj.TipoTeste = TESTES
        for n, d in (("PMTA", "PMTA do vaso (MPa)"), ("PressaoTeste", "Pressão de teste no topo (MPa)"),
                     ("PressaoTesteFundo", "Pressão de teste no ponto mais baixo (MPa, com a coluna d'água)"),
                     ("TensaoTeste", "Tensão de membrana no teste (MPa)"),
                     ("LimiteTeste", "Limite adotado para a tensão no teste: 0,9·Sy (MPa, a checar)")):
            add("App::PropertyFloat", n, "Teste", d, 0.0, ro=True)
        add("App::PropertyFloat", "Sy", "Projeto", "Limite de escoamento do material (MPa; para o teste)", 0.0)
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
        forma = geometria(obj.DiametroInterno.Value, obj.ComprimentoCostado.Value, tc, tt, obj.TipoTampo, bocais)
        vertical = getattr(obj, "Orientacao", "Horizontal") == "Vertical"
        sup = getattr(obj, "Suportes", "Nenhum")
        if sup != "Nenhum":
            if vertical and sup == "Selas":
                avisos.append("Selas são para vaso horizontal: use saia ou pernas no vertical.")
            elif not vertical and sup in ("Saia", "Pernas"):
                avisos.append("Saia e pernas são para vaso vertical: use selas no horizontal.")
            else:
                pecas = suportes(sup, obj.DiametroInterno.Value, obj.ComprimentoCostado.Value, tc, tt,
                                 obj.TipoTampo, obj.PosicaoSelas.Value, obj.AlturaSuporte.Value, vertical)
                if pecas:
                    forma = forma.fuse(pecas).removeSplitter()
        if vertical:
            # eixo do vaso na vertical (Z), linha de tangência de baixo em z = 0. A rotação vai para a
            # geometria (a Placement do objeto sobrescreveria a da forma)
            mat = FreeCAD.Matrix()
            mat.rotateY(math.radians(-90))
            forma = forma.transformGeometry(mat)
        obj.Shape = forma
        obj.MinimoCostado = mc
        obj.MinimoTampo = mt
        obj.PMTACostado = c.pmta_costado(tc)
        obj.PMTATampo = c.pmta_tampo(tt)
        obj.VolumeInterno = volume_interno(obj.DiametroInterno.Value, obj.ComprimentoCostado.Value, obj.TipoTampo, tt)
        obj.MassaVazio = obj.Shape.Volume * 7850e-9
        # teste de pressão
        pmta = min(obj.PMTACostado, obj.PMTATampo)
        obj.PMTA = pmta
        S_t = obj.TensaoAdmissivelTeste or obj.TensaoAdmissivel
        pt = pressao_teste(pmta, obj.TensaoAdmissivel, S_t, obj.TipoTeste)
        obj.PressaoTeste = pt
        Ri = obj.DiametroInterno.Value / 2.0
        if vertical and obj.TipoTeste.startswith("Hidro"):
            H = obj.ComprimentoCostado.Value + 2 * altura_tampo(Ri, tt, obj.TipoTampo)
        elif obj.TipoTeste.startswith("Hidro"):
            H = obj.DiametroInterno.Value
        else:
            H = 0.0
        obj.PressaoTesteFundo = pt + AGUA * H
        # teste com o vaso novo (sem corrosão): membrana circunferencial do costado (UG-27 invertida)
        p_fundo = obj.PressaoTesteFundo
        obj.TensaoTeste = p_fundo * (Ri + 0.6 * tc) / (obj.EficienciaJunta * tc) if tc > 0 else 0.0
        obj.LimiteTeste = 0.9 * obj.Sy if obj.Sy else 0.0
        if obj.LimiteTeste and obj.TensaoTeste > obj.LimiteTeste:
            avisos.append("No teste, a tensão de membrana (%s MPa) passa de 0,9·Sy (%s MPa): reveja a espessura "
                          "ou a pressão de teste (limite a checar no código vigente)."
                          % (fmt(obj.TensaoTeste, 0), fmt(obj.LimiteTeste, 0)))
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

    def doubleClicked(self, vobj):
        abrir_painel(vobj.Object)
        return True

    def setEdit(self, vobj, mode=0):
        if mode == 0:
            abrir_painel(vobj.Object)
            return True
        return False

    def unsetEdit(self, vobj, mode=0):
        return False

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
    u = _unid(v)
    L.append("Pressão de projeto: %s   Temperatura: %s" % (fmt_p(v.PressaoProjeto, u), v.TemperaturaProjeto or "—"))
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
        fmt_p(v.PMTACostado, u), fmt_p(v.PMTATampo, u), fmt_p(min(v.PMTACostado, v.PMTATampo), u)))
    L.append("Volume interno: %s   P·V: %s   Massa vazio (aço): %s" % (
        fmt(v.VolumeInterno, 3, "m³"), fmt(v.PressaoProjeto * v.VolumeInterno, 3, "MPa·m³"), fmt(v.MassaVazio, 1, "kg")))
    if "PressaoTeste" in v.PropertiesList and v.PressaoTeste:
        L.append("")
        L.append("Teste de pressão (%s): Pt = %s × PMTA × (S teste / S projeto) = %s no topo; %s no ponto "
                 "mais baixo (com a coluna d'água)" % (
                     v.TipoTeste, "1,3" if v.TipoTeste.startswith("Hidro") else "1,1",
                     fmt_p(v.PressaoTeste, u), fmt_p(v.PressaoTesteFundo, u)))
        L.append("  Tensão de membrana no costado durante o teste (vaso novo, sem corrosão): %s%s" % (
            fmt(v.TensaoTeste, 1, "MPa"),
            ("  — limite adotado 0,9·Sy = %s (a checar)" % fmt(v.LimiteTeste, 1, "MPa")) if v.LimiteTeste else ""))
    if v.Avisos:
        L.append("")
        L.append("Avisos:")
        L.extend("  • " + a for a in v.Avisos)
    L.append("")
    L.append("Não calculados: reforço de aberturas (UG-37), pressão externa/vácuo (UG-28), cargas de vento,")
    L.append("sismo e apoios. Enquadramento na NR-13 e pressão de teste exigida: conferir no texto vigente.")
    return "\n".join(L)


# ============================================================================ desenho e teste
def casca_media(v):
    """Superfície média do vaso para o modelo de casca (elementos S6 do CalculiX).
    Retorna (forma, grupos) — grupos: {nome: (espessura, [índices de face], papel)} com papel
    "pressao" (faces molhadas, já com a direção de fora) ou "suporte"; e as arestas de apoio."""
    import Part
    from BOPTools import SplitAPI
    D, comp = v.DiametroInterno.Value, v.ComprimentoCostado.Value
    tc = v.EspessuraCostado.Value or chapa_acima(v.MinimoCostado)
    tt = v.EspessuraTampo.Value or chapa_acima(v.MinimoTampo)
    Ri = D / 2.0
    Rm = Ri + tc / 2.0
    eixo = FreeCAD.Vector(1, 0, 0)
    pecas = []      # (face, papel, espessura, origem para a normal)
    cil = [f for f in Part.makeCylinder(Rm, comp, FreeCAD.Vector(), eixo).Faces
           if "Cylinder" in type(f.Surface).__name__][0]
    bocais = []
    for linha in v.Bocais:
        b = interpretar_bocal(linha)
        if b is not None and 0 <= b[0] - b[2] / 2 and b[0] + b[2] / 2 <= comp:
            bocais.append(b)
    for (x, ang, De, esp, proj) in bocais:
        a = math.radians(ang)
        d = FreeCAD.Vector(0, math.cos(a), math.sin(a))
        rn = (De - esp) / 2.0
        cil = cil.cut(Part.makeCylinder(rn, Rm + proj + 10, FreeCAD.Vector(x, 0, 0), d)).Faces[0]
    pecas.append((cil, "costado", tc))
    # tampos (superfície média com o raio do costado; a espessura vem do elemento)
    n = tipo_tampo(v.TipoTampo)
    if n == 0:
        perfil = _curva_eliptica(Rm, Rm / 2.0)
    elif n == 1:
        L, r = _coroa_rebordo(Rm, 0.0)
        perfil, _apice = _curva_torisferica(Rm, L, r)
    else:
        perfil = Part.Arc(FreeCAD.Vector(0, Rm, 0), FreeCAD.Vector(-Rm * math.cos(math.pi / 4), Rm * math.sin(math.pi / 4), 0),
                          FreeCAD.Vector(-Rm, 0, 0)).toShape()
    t1 = perfil.revolve(FreeCAD.Vector(), eixo, 360)
    t2 = t1.mirror(FreeCAD.Vector(comp / 2.0, 0, 0), eixo)
    for t in (t1, t2):
        for f in t.Faces:
            pecas.append((f, "tampo", tt))
    for (x, ang, De, esp, proj) in bocais:
        a = math.radians(ang)
        d = FreeCAD.Vector(0, math.cos(a), math.sin(a))
        rn = (De - esp) / 2.0
        tubo = [f for f in Part.makeCylinder(rn, Rm + proj, FreeCAD.Vector(x, 0, 0), d).Faces
                if "Cylinder" in type(f.Surface).__name__][0]
        tubo = tubo.cut(Part.makeCylinder(Rm, comp, FreeCAD.Vector(), eixo))
        for f in tubo.Faces:
            pecas.append((f, "bocal", esp))
        tampa = Part.Face(Part.Wire(Part.makeCircle(rn, FreeCAD.Vector(x, 0, 0) + d * (Rm + proj), d)))
        pecas.append((tampa, "tampa do bocal", 3.0 * esp))
    vertical = v.Orientacao == "Vertical"
    sup = v.Suportes
    base_z = None
    if sup == "Selas" and not vertical:
        a = v.PosicaoSelas.Value or 0.2 * comp
        h = v.AlturaSuporte.Value or (Rm + tc / 2.0 + 150.0)
        base_z = -h
        for x in (a, comp - a):
            pts = [FreeCAD.Vector(x, -Rm * 0.9, -h), FreeCAD.Vector(x, Rm * 0.9, -h), FreeCAD.Vector(x, Rm * 0.9, 0),
                   FreeCAD.Vector(x, -Rm * 0.9, 0)]
            f = Part.Face(Part.makePolygon(pts + [pts[0]]))
            f = f.cut(Part.Face(Part.Wire(Part.makeCircle(Rm, FreeCAD.Vector(x, 0, 0), eixo)))).Faces[0]
            pecas.append((f, "sela", 12.7))
    elif sup == "Saia" and vertical:
        h = v.AlturaSuporte.Value or max(500.0, 0.5 * D)
        ht = altura_tampo(Ri, tt, v.TipoTampo)
        x0 = -max(h, ht + 100.0)
        saia = [f for f in Part.makeCylinder(Rm, -x0, FreeCAD.Vector(x0, 0, 0), eixo).Faces
                if "Cylinder" in type(f.Surface).__name__][0]
        pecas.append((saia, "saia", tc))
        base_z = x0
    elif sup == "Pernas" and vertical:
        h = v.AlturaSuporte.Value or max(600.0, 0.6 * D)
        ht = altura_tampo(Ri, tt, v.TipoTampo)
        De = 88.9 if D < 1200 else 141.3
        x0 = -(ht + h)
        for k in range(4):
            a = math.radians(45 + 90 * k)
            c = FreeCAD.Vector(x0, Rm * math.cos(a), Rm * math.sin(a))
            perna = [f for f in Part.makeCylinder((De - 5.5) / 2.0, ht + h + 300.0, c, eixo).Faces
                     if "Cylinder" in type(f.Surface).__name__][0]
            pecas.append((perna, "perna", 5.5))
        base_z = x0
    else:
        raise ValueError("escolha os suportes do vaso (selas no horizontal; saia ou pernas no vertical)")
    frag = SplitAPI.booleanFragments([p[0] for p in pecas], "Standard", 0.01)
    if vertical:
        frag.rotate(FreeCAD.Vector(), FreeCAD.Vector(0, 1, 0), -90)
    # classifica cada face resultante pela peça de origem
    grupos = {}
    for k, f in enumerate(frag.Faces):
        c = f.CenterOfMass
        cl = c
        if vertical:
            cl = FreeCAD.Vector(c.z, c.y, -c.x)        # volta para o sistema do vaso (eixo X)
        melhor = min(range(len(pecas)), key=lambda i: pecas[i][0].distToShape(Part.Vertex(cl))[0])
        papel, esp = pecas[melhor][1], pecas[melhor][2]
        grupos.setdefault((papel, round(esp, 3)), []).append(k)
    # arestas de apoio: as mais baixas do modelo (base das selas, da saia ou das pernas)
    zmin = frag.BoundBox.ZMin
    apoio = [k for k, e in enumerate(frag.Edges) if abs(e.BoundBox.ZMax - zmin) < 0.5 and
             abs(e.BoundBox.ZMin - zmin) < 0.5]
    return frag, grupos, apoio, (Rm, comp, vertical)


def _normal_para_fora(face, centro_eixo, vertical, papel, bocal_dir=None):
    """True quando a normal da face aponta para fora do vaso (lado sem pressão)."""
    c = face.CenterOfMass
    try:
        u, w = face.Surface.parameter(c)
        n = face.normalAt(u, w)
    except Exception:
        return True
    p = FreeCAD.Vector(c.z, c.y, -c.x) if vertical else FreeCAD.Vector(c)
    if vertical:
        n = FreeCAD.Vector(n.z, n.y, -n.x)
    Rm, comp = centro_eixo
    if papel == "tampa do bocal":
        ref = FreeCAD.Vector(0, p.y, p.z)
    elif papel == "bocal":
        return _bocal_fora(face, p, n, vertical)
    else:
        x = min(max(p.x, 0.0), comp)
        ref = p - FreeCAD.Vector(x, 0, 0)
    return n.dot(ref) > 0


def _bocal_fora(face, p, n, vertical):
    """Normal de parede de bocal aponta para fora se se afasta do eixo do bocal."""
    # o eixo do bocal passa por (xb, 0, 0) na direção radial do vaso que contém p
    rad = FreeCAD.Vector(0, p.y, p.z)
    if rad.Length < 1e-9:
        return True
    d = rad.normalize()
    # centro da seção do tubo nesse ponto: projeção de p no eixo do tubo (passa pelo plano x = x do eixo)
    # aproximação: o eixo do tubo é a reta pelo ponto (xc, 0, 0) com xc = centro do bocal ≈ x do centro
    # de massa da face (o tubo é simétrico em torno do eixo)
    cm = face.CenterOfMass
    if vertical:
        cm = FreeCAD.Vector(cm.z, cm.y, -cm.x)
    eixo_p = FreeCAD.Vector(cm.x, 0, 0) + d * (FreeCAD.Vector(0, p.y, p.z).dot(d))
    return n.dot(p - eixo_p) > 0


def simular_teste(v, tamanho=None, calcular=True):
    """Teste de pressão por elementos finitos de casca: superfície média do costado, tampos e bocais
    (com tampas cegas), suportes presos na base, pressão de teste nas faces molhadas.
    Retorna (estudo PrumoFEM, erro)."""
    import ObjectsFem
    import PrumoFEM as F
    doc = v.Document
    try:
        forma, grupos, apoio, (Rm, comp, vertical) = casca_media(v)
    except ValueError as ex:
        return None, str(ex)
    if not apoio:
        return None, "não achei a base dos suportes"
    peca = doc.addObject("Part::Feature", "CascaDoVaso")
    peca.Shape = forma
    peca.Label = "Casca do vaso (superfície média)"
    if FreeCAD.GuiUp:
        peca.ViewObject.Visibility = False
    an = ObjectsFem.makeAnalysis(doc, "TesteDePressao")
    an.Label = "Teste de pressão · %s" % v.Label
    try:
        import FemGui
        FemGui.setActiveAnalysis(an)
    except Exception:
        pass
    est = F.Estudo(doc)
    est.analise = an
    est.garantir(peca)
    est.put("PrumoTipo", "static")
    est.solver.AnalysisType = "static"
    mat = ObjectsFem.makeMaterialSolid(doc, "Material")
    an.addObject(mat)
    escolhido = None
    for m in F.materiais():
        if v.MaterialChapa and (m["nome"] == v.MaterialChapa or v.MaterialChapa.lower() in m["nome"].lower()):
            escolhido = m
            break
    if escolhido is None:
        escolhido = next((m for m in F.materiais() if "A516 Gr 70" in m["nome"]), F.materiais()[0])
    props = dict(escolhido["props"])
    if v.Sy:
        props["YieldStrength"] = "%s MPa" % v.Sy
    mat.Material = props
    mat.Label = "Material · " + escolhido["nome"]
    fora, dentro = [], []
    for (papel, esp), ks in sorted(grupos.items()):
        g = ObjectsFem.makeElementGeometry2D(doc, esp, "Espessura")
        g.References = [(peca, tuple("Face%d" % (k + 1) for k in ks))]
        g.Label = "Espessura %s mm · %s" % (fmt(esp, 2), papel)
        an.addObject(g)
        if papel in ("costado", "tampo", "bocal", "tampa do bocal"):
            for k in ks:
                f = forma.Faces[k]
                (fora if _normal_para_fora(f, (Rm, comp), vertical, papel) else dentro).append("Face%d" % (k + 1))
    for nome, lst, rev in (("PressaoTeste", fora, True), ("PressaoTesteB", dentro, False)):
        if not lst:
            continue
        pr = ObjectsFem.makeConstraintPressure(doc, nome)
        pr.References = [(peca, tuple(lst))]
        pr.Pressure = "%s MPa" % v.PressaoTeste
        pr.Reversed = rev
        pr.Label = "Pressão de teste %s MPa" % fmt(v.PressaoTeste, 3)
        an.addObject(pr)
    fx = ObjectsFem.makeConstraintFixed(doc, "Apoios")
    fx.References = [(peca, tuple("Edge%d" % (k + 1) for k in apoio))]
    fx.Label = "Apoios (base dos suportes)"
    an.addObject(fx)
    est.put("PrumoCasca", True, "App::PropertyBool")
    est.put("PrumoAvisos", ["Modelo de casca na superfície média (elementos de 2ª ordem); tampos com o raio "
                            "médio do costado e a espessura própria.",
                            "Pressão de teste uniforme (%s MPa, no topo); a coluna d'água (até %s MPa no fundo) e o "
                            "peso da água não estão no modelo." % (fmt(v.PressaoTeste, 3), fmt(v.PressaoTesteFundo, 3)),
                            "Bocais fechados com tampa cega rígida; flanges e soldas não modelados.",
                            "Suportes presos na base; picos na ligação suporte-costado e na raiz dos bocais "
                            "dependem da malha (avaliar com a convergência)."], "App::PropertyStringList")
    doc.recompute()
    if not calcular:
        return est, ""
    if tamanho is None:
        tamanho = min(max(v.DiametroInterno.Value / 30.0, 15.0), 60.0)
    ok, msg = F.gerar_malha(est, tamanho, "2nd")
    if not ok:
        return est, msg
    ok, erro, _dt = F.calcular(est)
    return est, ("" if ok else erro)


def desenho(v, formato="A3", campos=None):
    """Folha ABNT com as vistas do vaso e a tabela de dados de projeto, bocais e teste."""
    import PrumoFolhas
    doc = v.Document
    c = dict(campos or {})
    c.setdefault("titulo", v.Label)
    c.setdefault("material", v.MaterialChapa or "")
    page = PrumoFolhas.nova_folha(doc, formato, objs=[v], campos=c)
    linhas = tabela_dados(v)
    try:
        ann = doc.addObject("TechDraw::DrawViewAnnotation", "DadosDoVaso")
        ann.Label = "Dados de projeto"
        ann.Text = linhas
        ann.TextSize = 2.6
        ann.LineSpace = 120
        page.addView(ann)
        larg = float(page.Template.Width)
        ann.X = 25.0 + 55.0
        ann.Y = 60.0 + 3.0 * len(linhas) / 2.0 + 18.0
        _cotas(doc, page, v)
    except Exception as ex:
        FreeCAD.Console.PrintWarning("Prumo: tabela do vaso: %s\n" % ex)
    doc.recompute()
    return page


def tabela_dados(v):
    tc = v.EspessuraCostado.Value or chapa_acima(v.MinimoCostado)
    tt = v.EspessuraTampo.Value or chapa_acima(v.MinimoTampo)
    L = ["DADOS DE PROJETO (ASME VIII-1, pré-dimensionamento)",
         "Diâmetro interno: %s   Comprimento TL-TL: %s" % (fmt(v.DiametroInterno.Value, 0, "mm"),
                                                         fmt(v.ComprimentoCostado.Value, 0, "mm")),
         "Pressão de projeto: %s   Temperatura: %s" % (fmt_p(v.PressaoProjeto, _unid(v)),
                                                     v.TemperaturaProjeto or "—"),
         "PMTA: %s" % fmt_p(v.PMTA, _unid(v)),
         "Material: %s   S = %s   E = %s   Corrosão = %s" % (v.MaterialChapa or "—",
                                                            fmt(v.TensaoAdmissivel, 1, "MPa"),
                                                            fmt(v.EficienciaJunta, 2), fmt(v.Corrosao.Value, 1, "mm")),
         "Costado: chapa %s (mín. %s)   Tampos %s: %s (mín. %s)" % (
             fmt(tc, 2, "mm"), fmt(v.MinimoCostado, 2, "mm"), v.TipoTampo.split(" (")[0], fmt(tt, 2, "mm"),
             fmt(v.MinimoTampo, 2, "mm")),
         "Volume interno: %s   Massa vazio: %s" % (fmt(v.VolumeInterno, 3, "m³"), fmt(v.MassaVazio, 0, "kg")),
         "Teste %s: %s no topo" % (v.TipoTeste.split(" (")[0].lower(), fmt_p(v.PressaoTeste, _unid(v)))]
    if v.Bocais:
        L.append("BOCAIS: posição; ângulo; tubo; projeção")
        for k, b in enumerate(v.Bocais):
            L.append("N%d: %s" % (k + 1, b.replace(";", " ;")))
    return L


def _cotas(doc, page, v=None):
    """Cotas gerais na vista frontal (comprimento e altura totais), ligadas aos vértices 3D do vaso:
    acompanham quando o vaso muda."""
    vistas = [o for o in page.Views if o.TypeId == "TechDraw::DrawProjGroup"]
    if not vistas or v is None:
        return []
    frente = None
    for o in vistas[0].Views:
        if getattr(o, "Type", "") == "Front":
            frente = o
    if frente is None:
        return []
    vs = v.Shape.Vertexes
    if len(vs) < 2:
        return []
    idx = list(range(len(vs)))
    feitas = []
    for eixo, tipo in ((0, "DistanceX"), (2, "DistanceY")):
        a = min(idx, key=lambda i: vs[i].Point[eixo])
        b = max(idx, key=lambda i: vs[i].Point[eixo])
        if abs(vs[b].Point[eixo] - vs[a].Point[eixo]) < 1e-6:
            continue
        d = doc.addObject("TechDraw::DrawViewDimension", "Cota")
        d.Type = tipo
        d.MeasureType = "True"
        d.References2D = [(frente, "")]
        d.References3D = [(v, "Vertex%d" % (a + 1)), (v, "Vertex%d" % (b + 1))]
        page.addView(d)
        # fora do desenho: a cota do comprimento embaixo da vista, a da altura à direita
        bb = v.Shape.BoundBox
        e = float(getattr(page, "Scale", 1.0) or 1.0)
        if tipo == "DistanceX":
            d.X, d.Y = 0.0, -(bb.ZLength * e / 2.0 + 8.0)
        else:
            d.X, d.Y = -(bb.XLength * e / 2.0 + 8.0), 0.0     # à esquerda (a vista lateral fica à direita)
        try:
            d.FormatSpec = "%.0f"
        except Exception:
            pass
        feitas.append(d)
    return feitas


# ============================================================================ painel
import PrumoPainel as P


def _materiais_vaso():
    import PrumoFEM
    res = []
    for d in PrumoFEM.materiais():
        if d.get("biblioteca") != "Prumo":
            continue
        pm = PrumoFEM.props_mat(d["props"])
        if pm.get("Sy") and pm.get("Su"):
            res.append((d["nome"], pm["Sy"], pm["Su"], "vaso" in (d.get("grupo") or "").lower()))
    res.sort(key=lambda r: (not r[3], r[0]))
    return res


def _tubos():
    import PrumoPerfis
    fam = PrumoPerfis.familia("TUBO")
    return [it["nome"] for it in fam["itens"]] if fam else []


class PainelVaso(P.PainelTarefa):
    titulo = "Vaso de pressão"
    previa = True
    ajuda = ("Preencha os dados de projeto: o vaso aparece na hora, com as espessuras pelo ASME VIII-1 "
             "(UG-27 e UG-32), a PMTA e a pressão de teste. OK grava; Cancelar desfaz.")

    def montar(self):
        f = self.form
        s1 = f.secao("Geometria", "comprimento")
        self.orient = s1.linha("tipo", P.lista(ORIENTACOES), "Vaso deitado (selas) ou em pé (saia ou pernas).",
                               "Posição")
        self.D = s1.linha("comprimento", P.numero(1000.0, 50.0, 20000.0, " mm", 1), "Diâmetro interno do costado.",
                          "Diâmetro interno")
        self.L = s1.linha("comprimento", P.numero(2000.0, 0.0, 100000.0, " mm", 1), "Comprimento do costado "
                          "entre as linhas de tangência dos tampos.", "Comprimento (TL-TL)")
        self.tampo = s1.linha("tipo", P.lista(TAMPOS), "Tipo dos dois tampos.", "Tampos")
        s2 = f.secao("Projeto", "material")
        caixa_p = QtWidgets.QWidget()
        hp = QtWidgets.QHBoxLayout(caixa_p)
        hp.setContentsMargins(0, 0, 0, 0)
        self.P_ = P.numero(1.0, 0.001, 100.0, "", 3)
        self.unid_p = QtWidgets.QComboBox()
        self.unid_p.setProperty("prumo_letras", 6)
        for nome, _f, _c in UNIDADES_PRESSAO:
            self.unid_p.addItem(nome)
        self.unid_p.setToolTip("Unidade da pressão: MPa, kgf/cm² ou psi (o cálculo é feito em MPa)")
        self._unid_atual = "MPa"
        self.unid_p.currentTextChanged.connect(self._trocar_unidade)
        hp.addWidget(self.P_, 1)
        hp.addWidget(self.unid_p)
        s2.linha("quantidade", caixa_p, "Pressão de projeto (manométrica, no topo), em MPa, kgf/cm² ou psi.",
                 "Pressão")
        self.temp = s2.linha("texto", QtWidgets.QLineEdit(), "Temperatura de projeto (texto, vai para a "
                             "memória e o desenho).", "Temperatura")
        self.temp.setPlaceholderText("ex.: 150 °C")
        self.material = s2.linha("material", QtWidgets.QComboBox(), "Chapa do costado e dos tampos. Sy e Su "
                                 "vêm da biblioteca de materiais do Prumo.", "Material")
        self._mats = _materiais_vaso()
        for nome, sy, su, _v in self._mats:
            self.material.addItem("%s — Sy %s / Su %s MPa" % (nome, fmt(sy, 0), fmt(su, 0)), nome)
        self.S = s2.linha("quantidade", P.numero(0.0, 0.0, 2000.0, " MPa", 1), "Tensão admissível S na "
                          "temperatura de projeto (ASME II-D, Tabela 1A).", "S (projeto)")
        self.bt_s = s2.widget(QtWidgets.QPushButton("Estimar S pelo critério (Su/3,5 e 2/3·Sy)"))
        self.bt_s.setToolTip("Referência abaixo da faixa de fluência; o valor de projeto é o da Seção II-D "
                             "para o material e a temperatura (a checar).")
        self.E = s2.linha("tipo", QtWidgets.QComboBox(), "Eficiência da junta soldada (UW-12).", "Eficiência E")
        for v, txt in EFICIENCIAS:
            self.E.addItem(txt, v)
        self.CA = s2.linha("folga", P.numero(1.5, 0.0, 20.0, " mm", 2), "Sobre-espessura de corrosão.",
                           "Corrosão")
        s3 = f.secao("Espessuras adotadas", "espessura")
        self.tc = s3.linha("espessura", P.numero(0.0, 0.0, 300.0, " mm", 2), "Chapa do costado (0 = a chapa "
                           "comercial acima da mínima).", "Costado")
        self.tt = s3.linha("espessura", P.numero(0.0, 0.0, 300.0, " mm", 2), "Chapa dos tampos (0 = automática).",
                           "Tampos")
        s4 = f.secao("Bocais", "posicao")
        self.tab = s4.widget(QtWidgets.QTableWidget(0, 4))
        self.tab.setHorizontalHeaderLabels(["Posição (mm)", "Ângulo (°)", "Tubo", "Projeção (mm)"])
        self.tab.horizontalHeader().setStretchLastSection(True)
        self.tab.verticalHeader().setVisible(False)
        self.tab.setMinimumHeight(110)
        lin = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(lin)
        hl.setContentsMargins(0, 0, 0, 0)
        self.bt_mais = QtWidgets.QPushButton("Adicionar bocal")
        self.bt_menos = QtWidgets.QPushButton("Remover")
        hl.addWidget(self.bt_mais)
        hl.addWidget(self.bt_menos)
        s4.widget(lin)
        s5 = f.secao("Suportes", "selecao")
        self.sup = s5.linha("tipo", P.lista(SUPORTES, "Selas"), "Horizontal: selas. Vertical: saia ou pernas.",
                            "Tipo")
        self.pos_selas = s5.linha("comprimento", P.numero(0.0, 0.0, 100000.0, " mm", 0), "Selas: distância da "
                                  "linha de tangência (0 = 0,2·L).", "Posição das selas")
        self.alt = s5.linha("comprimento", P.numero(0.0, 0.0, 20000.0, " mm", 0), "Altura do suporte "
                            "(0 = automática).", "Altura")
        s6 = f.secao("Teste de pressão", "empurra")
        self.teste = s6.linha("tipo", P.lista(TESTES), "Hidrostático: 1,3 × PMTA. Pneumático: 1,1 × PMTA. "
                              "Ajustados pela razão S no teste / S de projeto.", "Teste")
        self.S_t = s6.linha("quantidade", P.numero(0.0, 0.0, 2000.0, " MPa", 1), "S na temperatura do teste "
                            "(0 = igual ao S de projeto).", "S (teste)")
        self.resultado = f.secao("Resultado", "info").texto("")
        self.material.currentIndexChanged.connect(lambda *_: self._mudou())
        self.bt_s.clicked.connect(self._estimar_s)
        self.bt_mais.clicked.connect(self._mais_bocal)
        self.bt_menos.clicked.connect(self._menos_bocal)
        self.tab.cellChanged.connect(lambda *_: self._mudou())
        self.orient.currentIndexChanged.connect(self._orient)

    # ---- campos
    def _orient(self, *_a):
        vertical = self.orient.currentText() == "Vertical"
        if vertical and self.sup.currentText() == "Selas":
            self.sup.setCurrentText("Saia")
        if not vertical and self.sup.currentText() in ("Saia", "Pernas"):
            self.sup.setCurrentText("Selas")
        self.pos_selas.setEnabled(not vertical)

    def _sy_su(self):
        nome = self.material.currentData()
        for n, sy, su, _v in self._mats:
            if n == nome:
                return sy, su
        return 0.0, 0.0

    def _estimar_s(self):
        sy, su = self._sy_su()
        self.S.setValue(round(s_estimado(sy, su), 1))

    def _mais_bocal(self):
        r = self.tab.rowCount()
        self.tab.blockSignals(True)
        self.tab.insertRow(r)
        L = self.L.value()
        for c, val in enumerate(("%g" % round(L * (0.25 + 0.5 * (r % 2)), 0), "90", None, "150")):
            if c == 2:
                cb = QtWidgets.QComboBox()
                cb.addItems(_tubos())
                i = cb.findText('Tubo 2" Sch 40')
                cb.setCurrentIndex(max(0, i))
                cb.currentIndexChanged.connect(lambda *_: self._mudou())
                self.tab.setCellWidget(r, c, cb)
            else:
                self.tab.setItem(r, c, QtWidgets.QTableWidgetItem(val))
        self.tab.blockSignals(False)
        self._mudou()

    def _menos_bocal(self):
        r = self.tab.currentRow()
        if r < 0:
            r = self.tab.rowCount() - 1
        if r >= 0:
            self.tab.removeRow(r)
            self._mudou()

    def _linhas_bocais(self):
        res = []
        for r in range(self.tab.rowCount()):
            try:
                pos = self.tab.item(r, 0).text()
                ang = self.tab.item(r, 1).text()
                tubo = self.tab.cellWidget(r, 2).currentText()
                proj = self.tab.item(r, 3).text()
            except Exception:
                continue
            res.append("%s; %s; %s; %s" % (pos, ang, tubo, proj))
        return res

    def _trocar_unidade(self, nova):
        """Troca a unidade do campo mantendo a mesma pressão."""
        mpa = self.pressao_mpa()
        _n, fator, casas = _unidade(nova)
        self._unid_atual = nova
        self.P_.blockSignals(True)
        self.P_.setDecimals(casas)
        self.P_.setRange(0.001 / fator if casas >= 3 else 10 ** -casas, 100.0 / fator)
        self.P_.setValue(mpa / fator)
        self.P_.blockSignals(False)
        self.P_.valueChanged.emit(self.P_.value())

    def pressao_mpa(self):
        return self.P_.value() * _unidade(self._unid_atual)[1]

    def props(self):
        sy, _su = self._sy_su()
        return dict(DiametroInterno=self.D.value(), ComprimentoCostado=self.L.value(), PressaoProjeto=self.pressao_mpa(),
                    UnidadePressao=self._unid_atual,
                    TemperaturaProjeto=self.temp.text().strip(), MaterialChapa=self.material.currentData() or "",
                    TensaoAdmissivel=self.S.value(), EficienciaJunta=self.E.currentData(),
                    Corrosao=self.CA.value(), TipoTampo=self.tampo.currentText(),
                    EspessuraCostado=self.tc.value(), EspessuraTampo=self.tt.value(),
                    Bocais=self._linhas_bocais(), Orientacao=self.orient.currentText(),
                    Suportes=self.sup.currentText(), PosicaoSelas=self.pos_selas.value(),
                    AlturaSuporte=self.alt.value(), TipoTeste=self.teste.currentText(),
                    TensaoAdmissivelTeste=self.S_t.value(), Sy=sy)

    def props_edicao(self):
        return self.props()

    def carregar(self, obj):
        self.orient.setCurrentText(obj.Orientacao)
        self.D.setValue(obj.DiametroInterno.Value)
        self.L.setValue(obj.ComprimentoCostado.Value)
        self.tampo.setCurrentText(obj.TipoTampo)
        self.P_.setValue(obj.PressaoProjeto)
        self._unid_atual = "MPa"
        u = _unid(obj)
        if u != "MPa":
            self.unid_p.setCurrentText(u)
        self.temp.setText(obj.TemperaturaProjeto)
        i = self.material.findData(obj.MaterialChapa)
        if i >= 0:
            self.material.setCurrentIndex(i)
        self.S.setValue(obj.TensaoAdmissivel)
        i = self.E.findData(obj.EficienciaJunta)
        if i >= 0:
            self.E.setCurrentIndex(i)
        self.CA.setValue(obj.Corrosao.Value)
        self.tc.setValue(obj.EspessuraCostado.Value)
        self.tt.setValue(obj.EspessuraTampo.Value)
        self.sup.setCurrentText(obj.Suportes)
        self.pos_selas.setValue(obj.PosicaoSelas.Value)
        self.alt.setValue(obj.AlturaSuporte.Value)
        self.teste.setCurrentText(obj.TipoTeste)
        self.S_t.setValue(obj.TensaoAdmissivelTeste)
        self.tab.setRowCount(0)
        for linha in obj.Bocais:
            partes = [x.strip() for x in linha.split(";")]
            if len(partes) != 4:
                continue
            self._mais_bocal()
            r = self.tab.rowCount() - 1
            self.tab.blockSignals(True)
            self.tab.item(r, 0).setText(partes[0])
            self.tab.item(r, 1).setText(partes[1])
            self.tab.cellWidget(r, 2).setCurrentText(partes[2])
            self.tab.item(r, 3).setText(partes[3])
            self.tab.blockSignals(False)

    def pendencia(self):
        if self.S.value() <= 0:
            return "Informe a tensão admissível S (ASME II-D) ou clique em Estimar S."
        try:
            Calculo(self.D.value(), self.pressao_mpa(), self.S.value(), self.E.currentData(), self.CA.value(),
                    self.tampo.currentText())
        except (ValueError, ZeroDivisionError) as ex:
            return str(ex)
        return None

    def executar(self):
        doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("Vaso")
        v = doc.addObject("Part::FeaturePython", "VasoDePressao")
        v.Label = "Vaso de pressão"
        Vaso(v)
        if FreeCAD.GuiUp:
            VPVaso(v.ViewObject)
        for k, val in self.props().items():
            setattr(v, k, val)
        doc.recompute()
        self._vaso = v
        self._mostrar_resultado(v)
        return [v]

    def aplicar_edicao(self, obj):
        for k, val in self.props().items():
            setattr(obj, k, val)
        obj.Document.recompute()
        self._mostrar_resultado(obj)

    def marcas(self):
        v = self.editando or getattr(self, "_vaso", None)
        if v is None or getattr(v, "Shape", None) is None or v.Shape.isNull():
            return []
        res = []
        try:
            vertical = v.Orientacao == "Vertical"
            for k, linha in enumerate(v.Bocais):
                b = interpretar_bocal(linha)
                if b is None:
                    continue
                x, ang, De, _e, proj = b
                Ro = v.DiametroInterno.Value / 2.0 + (v.EspessuraCostado.Value or chapa_acima(v.MinimoCostado))
                a = math.radians(ang)
                p = FreeCAD.Vector(x, (Ro + proj) * math.cos(a), (Ro + proj) * math.sin(a))
                if vertical:
                    p = FreeCAD.Vector(-p.z, p.y, p.x)
                res.append((p, "N%d" % (k + 1), False))
        except Exception:
            pass
        return res

    def _mostrar_resultado(self, v):
        if not v.Avisos and v.PMTA:
            cor = "#1E5C46"
        else:
            cor = "#7A2E20" if any("menor que a mínima" in a or "não realizado" in a for a in v.Avisos) else "#4D3B00"
        tc = v.EspessuraCostado.Value or chapa_acima(v.MinimoCostado)
        tt = v.EspessuraTampo.Value or chapa_acima(v.MinimoTampo)
        html = ("<b>Costado</b>: mín. %s → chapa %s<br><b>Tampos</b>: mín. %s → chapa %s<br>"
                "<b>PMTA</b> %s<br><b>Teste</b>: %s no topo · %s no fundo<br>"
                "Volume %s · massa vazio %s" % (
                    fmt(v.MinimoCostado, 2, "mm"), fmt(tc, 2, "mm"), fmt(v.MinimoTampo, 2, "mm"), fmt(tt, 2, "mm"),
                    fmt_p(v.PMTA, _unid(v)), fmt_p(v.PressaoTeste, _unid(v)),
                    fmt_p(v.PressaoTesteFundo, _unid(v)), fmt(v.VolumeInterno, 3, "m³"), fmt(v.MassaVazio, 0, "kg")))
        if v.Avisos:
            html += "".join("<br><span style='color:#B5523F'>⚠ %s</span>" % a for a in v.Avisos)
        self.resultado.setText("<span style='color:%s'>%s</span>" % (cor, html))


def abrir_painel(obj=None):
    p = PainelVaso()
    if obj is not None:
        p.editar_objeto(obj)
    return p.mostrar()


def vaso_selecionado():
    for o in FreeCADGui.Selection.getSelection():
        if "PressaoProjeto" in o.PropertiesList:
            return o
    for o in (FreeCAD.ActiveDocument.Objects if FreeCAD.ActiveDocument else []):
        if "PressaoProjeto" in o.PropertiesList:
            return o
    return None


class CmdVaso:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("vaso.svg"),
                "MenuText": "Vaso de pressão",
                "ToolTip": "Formulário do vaso: diâmetro, comprimento, tampos, material, bocais e suportes, com as "
                           "espessuras pelo ASME VIII-1 (UG-27 e UG-32), PMTA e pressão de teste na hora."}

    def IsActive(self):
        return True

    def Activated(self):
        if FreeCAD.ActiveDocument is None:
            FreeCAD.newDocument("Vaso")
        abrir_painel()


class CmdDesenhoVaso:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"), "MenuText": "Desenho do vaso",
                "ToolTip": "Folha ABNT com as vistas do vaso, cotas gerais e a tabela de dados de projeto, "
                           "bocais e teste."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None and vaso_selecionado() is not None

    def Activated(self):
        v = vaso_selecionado()
        page = desenho(v)
        try:
            page.ViewObject.doubleClicked()
        except Exception:
            pass


class CmdTesteVaso:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("assistente_fem.svg"), "MenuText": "Simular teste de pressão",
                "ToolTip": "Elementos finitos do vaso com a pressão de teste nas faces internas e os suportes "
                           "presos: tensões de von Mises comparadas ao escoamento."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None and vaso_selecionado() is not None

    def Activated(self):
        import PrumoFEM
        v = vaso_selecionado()
        mw = FreeCADGui.getMainWindow()
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        doc = v.Document
        doc.openTransaction("Teste de pressão")
        try:
            est, erro = simular_teste(v)
            doc.commitTransaction()
        except Exception as ex:
            doc.abortTransaction()
            est, erro = None, str(ex)
        QtWidgets.QApplication.restoreOverrideCursor()
        if erro:
            QtWidgets.QMessageBox.warning(mw, "Teste de pressão", erro)
        if est is not None:
            if not erro:
                PrumoFEM.mostrar_campo(est, "tensao")
            PrumoFEM.mostrar()


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
