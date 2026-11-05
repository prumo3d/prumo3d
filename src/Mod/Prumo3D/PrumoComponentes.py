# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: aba Componentes — modelos prontos que completam o projeto (motor, compressor, válvula, caldeira,
trole, ar comprimido, pessoas, secador e outros).

Não são peças para editar: cada componente é desenhado pelo Usinix a partir do modelo e do tamanho escolhidos
(propriedades Modelo e Tamanho; trocar o tamanho redesenha). Servem para ocupação de espaço, leiaute,
interferência e apresentação.

AS MEDIDAS SÃO REPRESENTATIVAS. Onde há tabela de norma ou catálogo (altura de eixo das carcaças IEC, furação
de flange EN 1092-1 PN 16, palete PBR) os valores foram digitados da memória e estão marcados "a checar" até
serem conferidos na fonte; o resto sai de proporções típicas. Para projeto executivo, confira no catálogo
do fabricante do equipamento escolhido.
"""
import math

import FreeCAD

# ------------------------------------------------------------------ cores (r, g, b)
CORES = {
    "maquina": (0.20, 0.42, 0.62), "verde": (0.24, 0.50, 0.33), "metal": (0.74, 0.76, 0.79),
    "escuro": (0.22, 0.24, 0.27), "amarelo": (0.97, 0.75, 0.0), "vermelho": (0.75, 0.16, 0.14),
    "branco": (0.93, 0.94, 0.95), "cinza": (0.55, 0.58, 0.62), "pele": (0.87, 0.70, 0.56),
    "roupa": (0.17, 0.30, 0.50), "calca": (0.20, 0.22, 0.28), "madeira": (0.72, 0.55, 0.34),
    "laranja": (0.93, 0.47, 0.12), "transparente": (0.80, 0.88, 0.95),
}


# ------------------------------------------------------------------ peças básicas
def _V(x, y, z):
    return FreeCAD.Vector(x, y, z)


def caixa(dx, dy, dz, x=0, y=0, z=0, centro=True):
    """Caixa dx × dy × dz com a base em z; centrada em (x, y) quando centro=True."""
    import Part
    if centro:
        x, y = x - dx / 2.0, y - dy / 2.0
    return Part.makeBox(dx, dy, dz, _V(x, y, z))


def cilindro(r, h, base=(0, 0, 0), eixo=(0, 0, 1)):
    import Part
    return Part.makeCylinder(r, h, _V(*base), _V(*eixo))


def cone(r1, r2, h, base=(0, 0, 0), eixo=(0, 0, 1)):
    import Part
    return Part.makeCone(r1, r2, h, _V(*base), _V(*eixo))


def esfera(r, c=(0, 0, 0)):
    import Part
    return Part.makeSphere(r, _V(*c))


def toro(R, r, c=(0, 0, 0), eixo=(0, 0, 1)):
    import Part
    return Part.makeTorus(R, r, _V(*c), _V(*eixo))


def tampo(r, h, base, eixo):
    """Tampo semielíptico simples (meia esfera achatada) para tanques e caldeiras."""
    s = esfera(r)
    import Part
    meia = s.common(Part.makeBox(2 * r, 2 * r, r, _V(-r, -r, 0)))
    m = FreeCAD.Matrix()
    m.scale(1, 1, h / r)
    meia = meia.transformGeometry(m)
    eixo_v = _V(*eixo)
    rot = FreeCAD.Rotation(_V(0, 0, 1), eixo_v)
    meia.Placement = FreeCAD.Placement(_V(*base), rot)
    return meia


# ------------------------------------------------------------------ motores
# carcaça IEC: (H altura do eixo, A entre furos de pé (largura), B entre furos (comprimento), D ponta de eixo,
# E comprimento da ponta, L comprimento total aproximado). H, A, B, D, E: IEC 60072-1, A CHECAR. L: típico.
CARCACAS_IEC = {
    "63": (63, 100, 80, 11, 23, 215), "71": (71, 112, 90, 14, 30, 245), "80": (80, 125, 100, 19, 40, 276),
    "90S": (90, 140, 100, 24, 50, 304), "90L": (90, 140, 125, 24, 50, 329), "100L": (100, 160, 140, 28, 60, 376),
    "112M": (112, 190, 140, 28, 60, 393), "132S": (132, 216, 140, 38, 80, 452),
    "132M": (132, 216, 178, 38, 80, 490), "160M": (160, 254, 210, 42, 110, 598),
    "160L": (160, 254, 254, 42, 110, 642), "180M": (180, 279, 241, 48, 110, 664),
    "180L": (180, 279, 279, 48, 110, 702), "200L": (200, 318, 305, 55, 110, 767),
    "225S/M": (225, 356, 311, 60, 140, 856), "250S/M": (250, 406, 349, 65, 140, 940),
    "280S/M": (280, 457, 419, 75, 140, 1040), "315S/M": (315, 508, 457, 80, 170, 1210),
}


def motor(tam):
    H, A, B, D, E, L = CARCACAS_IEC[tam]
    rc = H * 0.95                      # raio da carcaça (típico)
    lc = L - E                         # carcaça + tampa do ventilador
    pes = H * 0.14
    partes = []
    # pés e base
    partes.append((caixa(B + 0.5 * H, A + 0.25 * H, pes, x=lc * 0.45, z=0), "maquina"))
    partes.append((caixa(lc * 0.55, rc * 1.3, H - pes, x=lc * 0.45, z=pes), "maquina"))
    # carcaça com aletas, tampa traseira do ventilador, tampa dianteira
    partes.append((cilindro(rc, lc * 0.78, base=(lc * 0.08, 0, H), eixo=(1, 0, 0)), "maquina"))
    for i in range(8):
        a = math.radians(22.5 * i)
        partes.append((caixa(lc * 0.70, rc * 0.08, rc * 0.18, x=lc * 0.46, z=0).transformGeometry(
            _rot_x(a, H, rc * 1.02)), "maquina"))
    partes.append((cilindro(rc * 0.98, lc * 0.14, base=(lc * 0.86, 0, H), eixo=(1, 0, 0)), "escuro"))
    partes.append((cilindro(rc * 0.9, lc * 0.08, base=(0, 0, H), eixo=(1, 0, 0)), "maquina"))
    # ponta de eixo e chaveta
    partes.append((cilindro(D / 2.0, E + lc * 0.02, base=(-E, 0, H), eixo=(1, 0, 0)), "metal"))
    # caixa de ligação e olhal
    cl = rc * 0.75
    partes.append((caixa(cl, cl, cl * 0.6, x=lc * 0.4, z=H + rc * 0.92), "maquina"))
    partes.append((toro(rc * 0.12, rc * 0.03, c=(lc * 0.2, 0, H + rc * 1.12), eixo=(0, 1, 0)), "metal"))
    return partes, {"Carcaça (IEC)": tam, "Altura do eixo H": "%d mm (a checar)" % H,
                    "Ponta de eixo D × E": "%d × %d mm (a checar)" % (D, E), "Comprimento aprox.": "%d mm" % L}


def _rot_x(ang, zc, r):
    """Matriz que leva uma aleta deitada (no chão) para o ângulo `ang` em volta do eixo X na altura zc."""
    m = FreeCAD.Matrix()
    m.move(_V(0, 0, r))
    m2 = FreeCAD.Matrix()
    m2.rotateX(ang)
    m3 = FreeCAD.Matrix()
    m3.move(_V(0, 0, zc))
    return m3.multiply(m2.multiply(m))


# ------------------------------------------------------------------ compressores
def compressor_pistao(volume_l):
    v = float(volume_l) * 1e6                      # mm³
    D = (4 * v / (3 * math.pi)) ** (1 / 3.0)       # tanque com L/D = 3 (típico)
    Lt = 3 * D
    r = D / 2.0
    zc = r + D * 0.25
    partes = [(cilindro(r, Lt, base=(-Lt / 2, 0, zc), eixo=(1, 0, 0)), "vermelho"),
              (tampo(r, r * 0.5, (Lt / 2, 0, zc), (1, 0, 0)), "vermelho"),
              (tampo(r, r * 0.5, (-Lt / 2, 0, zc), (-1, 0, 0)), "vermelho")]
    for x in (-Lt * 0.35, Lt * 0.35):
        partes.append((caixa(D * 0.12, D * 0.9, D * 0.27, x=x, z=0), "escuro"))
    # plataforma, unidade compressora (bloco + 2 cilindros aletados) e motor
    zt = zc + r
    partes.append((caixa(Lt * 0.55, D * 0.75, D * 0.04, x=0, z=zt), "escuro"))
    zp = zt + D * 0.04
    partes.append((caixa(D * 0.45, D * 0.4, D * 0.3, x=-Lt * 0.1, z=zp), "escuro"))
    for dy in (-D * 0.1, D * 0.1):
        partes.append((cilindro(D * 0.08, D * 0.35, base=(-Lt * 0.1, dy, zp + D * 0.3)), "cinza"))
    partes.append((cilindro(D * 0.16, D * 0.5, base=(Lt * 0.12, 0, zp + D * 0.17), eixo=(1, 0, 0)), "maquina"))
    partes.append((cilindro(D * 0.3, D * 0.05, base=(-Lt * 0.1 - D * 0.35, 0, zp + D * 0.2), eixo=(0, 1, 0)), "metal"))
    return partes, {"Reservatório": "%s L" % volume_l, "Diâmetro × comprimento": "%.0f × %.0f mm" % (D, Lt * 1.33),
                    "Medidas": "representativas (L/D = 3)"}


# compressor de parafuso: potência kW -> (comprimento, largura, altura) típicos de gabinete
PARAFUSO_KW = {"7,5": (900, 650, 950), "11": (1000, 700, 1050), "15": (1100, 750, 1150),
               "22": (1300, 850, 1300), "37": (1550, 950, 1500), "55": (1850, 1100, 1650),
               "75": (2100, 1200, 1800)}


def compressor_parafuso(kw):
    c, l, a = PARAFUSO_KW[kw]
    partes = [(caixa(c, l, a * 0.05, z=0), "escuro"),
              (caixa(c, l, a * 0.95, z=a * 0.05), "branco"),
              (caixa(c * 0.3, l * 1.002, a * 0.35, x=c * 0.25, z=a * 0.5), "transparente"),
              (caixa(c * 0.16, l * 0.02, a * 0.12, x=-c * 0.3, y=l / 2, z=a * 0.65), "escuro")]
    return partes, {"Potência": "%s kW" % kw, "Gabinete C × L × A": "%d × %d × %d mm" % (c, l, a),
                    "Medidas": "representativas"}


# ------------------------------------------------------------------ válvulas
# DN -> diâmetro externo do flange EN 1092-1 PN 16 (A CHECAR)
FLANGE_PN16 = {15: 95, 20: 105, 25: 115, 32: 140, 40: 150, 50: 165, 65: 185, 80: 200, 100: 220, 125: 250,
               150: 285, 200: 340, 250: 405, 300: 460}
DNS = sorted(FLANGE_PN16)


def _flanges(dn, face, eixo_x=True):
    Df = FLANGE_PN16[dn]
    e = max(14.0, 0.08 * Df)
    partes = []
    for x in (-face / 2.0, face / 2.0 - e):
        partes.append((cilindro(Df / 2.0, e, base=(x, 0, 0), eixo=(1, 0, 0)), "escuro"))
    return partes, Df, e


def valvula(tipo, dn):
    dn = int(dn)
    face = {"esfera": 1.1, "gaveta": 1.25, "globo": 1.45, "retencao": 1.4, "borboleta": 0.35}[tipo] * dn + \
        {"esfera": 100, "gaveta": 120, "globo": 120, "retencao": 110, "borboleta": 30}[tipo]
    partes = []
    if tipo == "borboleta":
        Df = FLANGE_PN16[dn]
        partes.append((cilindro(Df * 0.42, face, base=(-face / 2, 0, 0), eixo=(1, 0, 0)), "escuro"))
        partes.append((cilindro(dn * 0.08 + 8, Df * 0.35, base=(0, 0, Df * 0.4)), "metal"))
        partes.append((caixa(Df * 0.45, 20, 12, x=Df * 0.18, z=Df * 0.75), "vermelho"))
        return partes, {"DN": dn, "Entre faces": "%.0f mm (representativa)" % face}
    fl, Df, e = _flanges(dn, face)
    partes += fl
    rc = Df * 0.38
    if tipo == "esfera":
        partes.append((esfera(rc * 1.05), "escuro"))
        partes.append((cilindro(rc * 0.7, face - 2 * e, base=(-face / 2 + e, 0, 0), eixo=(1, 0, 0)), "escuro"))
        partes.append((cilindro(dn * 0.06 + 6, rc * 0.6, base=(0, 0, rc * 0.8)), "metal"))
        partes.append((caixa(Df * 1.1, 22, 10, x=Df * 0.45, z=rc * 1.4), "vermelho"))
    else:
        partes.append((cilindro(rc, face - 2 * e, base=(-face / 2 + e, 0, 0), eixo=(1, 0, 0)), "escuro"))
        if tipo in ("gaveta", "globo"):
            corpo = esfera(rc * 1.25) if tipo == "globo" else caixa(rc * 1.3, rc * 1.1, rc * 1.2, z=-rc * 0.6)
            partes.append((corpo, "escuro"))
            hb = Df * (1.1 if tipo == "gaveta" else 0.8)
            partes.append((cilindro(rc * 0.55, hb * 0.55, base=(0, 0, rc * 0.5)), "escuro"))
            partes.append((cilindro(dn * 0.05 + 6, hb * 0.6, base=(0, 0, rc * 0.5 + hb * 0.5)), "metal"))
            partes.append((toro(Df * 0.35, 8 + dn * 0.02, c=(0, 0, rc * 0.5 + hb * 1.05)), "vermelho"))
        else:   # retenção: tampa aparafusada em cima, sem volante
            partes.append((caixa(rc * 1.4, rc * 1.2, rc * 0.9, z=-rc * 0.3), "escuro"))
            partes.append((cilindro(rc * 0.75, rc * 0.25, base=(0, 0, rc * 0.6)), "escuro"))
    return partes, {"DN": dn, "Flange": "PN 16, Ø %d mm (EN 1092-1, a checar)" % Df,
                    "Entre faces": "%.0f mm (representativa)" % face}


# ------------------------------------------------------------------ caldeiras
CALDEIRA_KGH = {"500": (1100, 2600), "1000": (1400, 3200), "2000": (1700, 3900), "4000": (2100, 4800),
                "6000": (2400, 5400), "10000": (2800, 6400)}          # (diâmetro, comprimento) típicos


def caldeira(kgh):
    D, L = CALDEIRA_KGH[kgh]
    r = D / 2.0
    zc = r + D * 0.18
    partes = [(cilindro(r, L, base=(-L / 2, 0, zc), eixo=(1, 0, 0)), "branco")]
    for x in (-L * 0.36, L * 0.36):
        partes.append((caixa(D * 0.15, D * 0.85, zc, x=x, z=0), "escuro"))
    partes.append((caixa(L * 1.05, D * 0.95, D * 0.04, z=0), "escuro"))
    # queimador na frente, câmara traseira, chaminé
    partes.append((cilindro(r * 0.95, D * 0.12, base=(-L / 2 - D * 0.12, 0, zc), eixo=(1, 0, 0)), "cinza"))
    partes.append((caixa(D * 0.45, D * 0.4, D * 0.45, x=-L / 2 - D * 0.35, z=zc - D * 0.22), "vermelho"))
    partes.append((cilindro(r * 0.95, D * 0.1, base=(L / 2, 0, zc), eixo=(1, 0, 0)), "cinza"))
    partes.append((cilindro(D * 0.14, D * 1.1, base=(L / 2 - D * 0.3, 0, zc + r * 0.9)), "escuro"))
    # válvulas no topo e indicador de nível
    for x in (-L * 0.15, L * 0.05):
        partes.append((cilindro(D * 0.045, D * 0.18, base=(x, 0, zc + r * 0.95)), "metal"))
    partes.append((cilindro(D * 0.02, D * 0.3, base=(-L / 2 + D * 0.1, r * 0.8, zc - D * 0.1)), "transparente"))
    return partes, {"Produção de vapor": "%s kg/h" % kgh, "Corpo Ø × comprimento": "%d × %d mm" % (D, L),
                    "Medidas": "representativas (flamotubular horizontal)"}


# ------------------------------------------------------------------ trole (trabalho em altura)
TROLE = {"aba até 150 mm": 150, "aba até 220 mm": 220, "aba até 300 mm": 300}


def trole(faixa):
    bf = TROLE[faixa]
    vao = bf + 30
    partes = []
    # viga (referência, aba de baixo) não entra; placas laterais, rodas e eixo central, olhal em D
    for s in (-1, 1):
        y = s * (vao / 2.0 + 6)
        partes.append((caixa(170, 10, 140, y=y, z=-120), "amarelo"))
        for x in (-50, 50):   # rodas por dentro das placas, rolando sobre a aba
            partes.append((cilindro(22, 14, base=(x, s * (vao / 2.0 - 20) - 7, 0), eixo=(0, 1, 0)), "metal"))
    partes.append((cilindro(8, vao + 40, base=(0, -vao / 2 - 20, -100), eixo=(0, 1, 0)), "metal"))
    partes.append((toro(28, 6, c=(0, 0, -150), eixo=(0, 1, 0)), "escuro"))
    return partes, {"Faixa de aba": faixa, "Uso": "Ancoragem móvel em viga I (trabalho em altura)",
                    "Medidas": "representativas — confira certificação e carga no fabricante"}


# ------------------------------------------------------------------ ar comprimido
ROSCAS = {"1/4\"": 40, "3/8\"": 50, "1/2\"": 60, "3/4\"": 75, "1\"": 90}       # largura do módulo FRL (típica)


def frl(rosca):
    w = ROSCAS[rosca]
    partes = []
    for i, (cor, copo) in enumerate((("escuro", True), ("escuro", False), ("escuro", True))):
        x = (i - 1) * (w + 4)
        partes.append((caixa(w, w, w * 0.9, x=x, z=w * 2.0), cor))
        if copo:
            partes.append((cilindro(w * 0.36, w * 1.8, base=(x, 0, w * 0.2)), "transparente"))
            partes.append((cilindro(w * 0.12, w * 0.2, base=(x, 0, 0)), "metal"))
        else:
            partes.append((cilindro(w * 0.3, w * 0.5, base=(x, 0, w * 2.9)), "escuro"))
            partes.append((cilindro(w * 0.3, 10, base=(x, -w / 2 - 10, w * 2.45), eixo=(0, 1, 0)), "branco"))
    for s in (-1, 1):
        partes.append((cilindro(w * 0.22, w * 0.3, base=(s * (1.5 * w + 4), 0, w * 2.45), eixo=(s, 0, 0)), "metal"))
    return partes, {"Rosca": rosca, "Composição": "Filtro + regulador com manômetro + lubrificador",
                    "Medidas": "representativas"}


def purgador(_t):
    partes = [(cilindro(35, 110, base=(0, 0, 0)), "escuro"), (caixa(90, 70, 60, z=110), "laranja"),
              (cilindro(10, 30, base=(-45, 0, 140), eixo=(-1, 0, 0)), "metal")]
    return partes, {"Tipo": "Purgador eletrônico de condensado", "Medidas": "representativas"}


RESERVATORIO_L = ["300", "500", "1000", "2000", "3000"]


def reservatorio(volume_l):
    v = float(volume_l) * 1e6
    D = (4 * v / (2.5 * math.pi)) ** (1 / 3.0)        # vertical, H/D = 2,5 (típico)
    H = 2.5 * D
    r = D / 2.0
    z0 = D * 0.25
    partes = [(cilindro(r, H, base=(0, 0, z0)), "cinza"), (tampo(r, r * 0.5, (0, 0, z0 + H), (0, 0, 1)), "cinza"),
              (tampo(r, r * 0.5, (0, 0, z0), (0, 0, -1)), "cinza")]
    for i in range(3):
        a = math.radians(120 * i)
        partes.append((cilindro(D * 0.04, z0, base=(r * 0.8 * math.cos(a), r * 0.8 * math.sin(a), 0)), "escuro"))
    partes.append((cilindro(D * 0.05, D * 0.2, base=(0, 0, z0 + H + r * 0.45)), "metal"))
    return partes, {"Volume": "%s L" % volume_l, "Diâmetro × altura do corpo": "%.0f × %.0f mm" % (D, H),
                    "Medidas": "representativas (H/D = 2,5)"}


# ------------------------------------------------------------------ secadores
SECADOR_M3MIN = {"1": (500, 450, 750), "3": (600, 550, 900), "6": (750, 650, 1000), "12": (900, 800, 1250),
                 "25": (1200, 1000, 1500)}


def secador_refrigeracao(vazao):
    c, l, a = SECADOR_M3MIN[vazao]
    partes = [(caixa(c, l, a, z=0), "branco"), (caixa(c * 0.6, l * 1.01, a * 0.3, z=a * 0.55), "cinza")]
    for s in (-1, 1):
        partes.append((cilindro(a * 0.04, c * 0.12, base=(s * c / 2, 0, a * 0.85), eixo=(s, 0, 0)), "metal"))
    return partes, {"Vazão": "%s m³/min" % vazao, "Gabinete C × L × A": "%d × %d × %d mm" % (c, l, a),
                    "Medidas": "representativas"}


def secador_adsorcao(vazao):
    c, l, a = SECADOR_M3MIN[vazao]
    r = l * 0.22
    h = a * 1.1
    partes = [(caixa(c * 1.1, l, 60, z=0), "escuro")]
    for x in (-c * 0.22, c * 0.22):
        partes += [(cilindro(r, h, base=(x, 0, 60)), "verde"), (tampo(r, r * 0.4, (x, 0, 60 + h), (0, 0, 1)), "verde")]
    partes.append((caixa(c * 0.8, r * 0.5, r * 0.5, z=60 + h * 0.08), "metal"))
    partes.append((caixa(c * 0.8, r * 0.5, r * 0.5, z=60 + h * 0.9), "metal"))
    partes.append((caixa(c * 0.25, l * 0.3, a * 0.35, x=0, y=l * 0.35, z=60 + h * 0.3), "cinza"))
    return partes, {"Vazão": "%s m³/min" % vazao, "Tipo": "Duas torres (dessecante)", "Medidas": "representativas"}


# ------------------------------------------------------------------ pessoas
ALTURAS = ["1,60 m", "1,75 m", "1,90 m"]


def pessoa(altura, sentado=False, capacete=True):
    h = float(altura.replace(" m", "").replace(",", ".")) * 1000
    u = h / 8.0                                   # cânone de 8 cabeças
    partes = []
    perna_r, braco_r = u * 0.22, u * 0.17
    if sentado:
        zq = u * 3.3                              # quadril na altura de uma cadeira
        for s in (-1, 1):
            y = s * u * 0.3
            # coxa para a frente (+X, como o pé de quem está em pé), canela descendo até o chão
            partes.append((cilindro(perna_r, u * 1.9, base=(0, y, zq), eixo=(1, 0, 0)), "calca"))
            partes.append((cilindro(perna_r * 0.9, zq, base=(u * 1.9, y, 0)), "calca"))
            partes.append((caixa(u * 0.9, u * 0.35, u * 0.25, x=u * 2.1, y=y, z=0), "escuro"))
        # cadeira: assento sob as coxas, encosto atrás, quatro pés
        partes.append((caixa(u * 2.0, u * 2.0, u * 0.25, x=u * 0.7, z=zq - u * 0.47), "madeira"))
        partes.append((caixa(u * 0.2, u * 2.0, u * 2.2, x=-u * 0.45, z=zq - u * 0.22), "madeira"))
        for px in (-u * 0.2, u * 1.6):
            for py in (-u * 0.9, u * 0.9):
                partes.append((caixa(u * 0.15, u * 0.15, zq - u * 0.47, x=px, y=py, z=0), "escuro"))
        base = zq
    else:
        for s in (-1, 1):
            y = s * u * 0.3
            partes.append((cilindro(perna_r, u * 3.6, base=(0, y, u * 0.25)), "calca"))
            partes.append((caixa(u * 0.9, u * 0.35, u * 0.25, x=u * 0.2, y=y, z=0), "escuro"))
        base = u * 3.85
    # tronco, braços, pescoço, cabeça e capacete
    partes.append((caixa(u * 0.75, u * 1.45, u * 2.9, z=base), "roupa"))
    for s in (-1, 1):
        partes.append((cilindro(braco_r, u * 2.7, base=(0, s * u * 0.88, base + u * 0.1)), "roupa"))
        partes.append((esfera(braco_r * 1.1, c=(0, s * u * 0.88, base + u * 0.05)), "pele"))
    partes.append((cilindro(u * 0.2, u * 0.3, base=(0, 0, base + u * 2.9)), "pele"))
    cab = base + u * 3.2 + u * 0.45
    partes.append((esfera(u * 0.45, c=(0, 0, cab)), "pele"))
    if capacete:
        import Part
        cap = esfera(u * 0.52, c=(0, 0, cab + u * 0.05)).common(
            Part.makeBox(u * 1.2, u * 1.2, u * 0.6, _V(-u * 0.6, -u * 0.6, cab + u * 0.05)))
        partes.append((cap, "amarelo"))
        partes.append((cilindro(u * 0.6, u * 0.04, base=(0, 0, cab + u * 0.05)), "amarelo"))
    info = {"Altura": altura, "Postura": "sentado" if sentado else "em pé",
            "EPI": "capacete" if capacete else "—", "Uso": "escala e ergonomia do leiaute"}
    return partes, info


# ------------------------------------------------------------------ outros
BOMBA_DN = ["32", "40", "50", "65", "80", "100"]


def bomba(dn):
    dn = int(dn)
    k = dn / 50.0
    partes = [(caixa(900 * k, 300 * k, 60 * k, x=150 * k, z=0), "escuro")]
    zc = 60 * k + 160 * k
    partes.append((cilindro(150 * k, 120 * k, base=(-120 * k, 0, zc), eixo=(1, 0, 0)), "maquina"))   # voluta
    partes.append((cilindro(dn / 2.0 + 8, 140 * k, base=(-180 * k, 0, zc), eixo=(-1, 0, 0)), "maquina"))  # sucção
    partes.append((cilindro(dn * 0.4 + 8, 200 * k, base=(-60 * k, 0, zc + 100 * k)), "maquina"))   # recalque
    partes.append((caixa(90 * k, 120 * k, 160 * k, x=40 * k, z=60 * k), "maquina"))
    partes.append((cilindro(110 * k, 500 * k, base=(100 * k, 0, zc), eixo=(1, 0, 0)), "verde"))     # motor
    return partes, {"Bocal de sucção": "DN %d" % dn, "Tipo": "Motobomba centrífuga em base",
                    "Medidas": "representativas"}


TALHA_T = {"0,5 t": 0.5, "1 t": 1.0, "2 t": 2.0, "5 t": 5.0}


def talha(cap):
    k = TALHA_T[cap] ** 0.33
    partes = [(caixa(420 * k, 260 * k, 300 * k, z=0), "amarelo"),
              (cilindro(120 * k, 160 * k, base=(210 * k, 0, 150 * k), eixo=(1, 0, 0)), "amarelo"),
              (toro(35 * k, 10 * k, c=(0, 0, 340 * k), eixo=(0, 1, 0)), "metal"),
              (cilindro(6 * k, 1200 * k, base=(0, 0, -1200 * k)), "metal"),
              (toro(40 * k, 12 * k, c=(0, 0, -1250 * k), eixo=(0, 1, 0)), "escuro")]
    return partes, {"Capacidade": cap, "Tipo": "Talha elétrica de corrente (gancho)", "Medidas": "representativas"}


def quadro(tam):
    a, l, p = {"600 × 400": (600, 400, 200), "800 × 600": (800, 600, 250), "1200 × 800": (1200, 800, 300),
               "2000 × 800": (2000, 800, 600)}[tam]
    partes = [(caixa(p, l, a, z=0 if a >= 2000 else 900), "cinza"),
              (caixa(10, l * 0.9, a * 0.9, x=-p / 2 - 5, z=(0 if a >= 2000 else 900) + a * 0.05), "cinza"),
              (cilindro(12, 20, base=(-p / 2 - 15, l * 0.35, (0 if a >= 2000 else 900) + a * 0.5), eixo=(-1, 0, 0)), "escuro")]
    return partes, {"Altura × largura": tam + " mm", "Instalação": "piso" if a >= 2000 else "parede (base a 900 mm)",
                    "Medidas": "representativas"}


def extintor(tipo):
    m = {"PQS 4 kg": (75, 470), "PQS 6 kg": (80, 520), "PQS 12 kg": (95, 620), "CO2 6 kg": (75, 650),
         "Água 10 L": (90, 600)}[tipo]
    r, h = m
    cor = "vermelho"
    partes = [(cilindro(r, h, base=(0, 0, 0)), cor), (esfera(r, c=(0, 0, h)), cor),
              (cilindro(18, 70, base=(0, 0, h + r * 0.8)), "escuro"),
              (caixa(120, 25, 15, x=40, z=h + r * 0.8 + 70), "escuro")]
    return partes, {"Tipo": tipo, "Medidas": "representativas"}


def palete(tipo):
    c, l, a = {"PBR 1200 × 1000": (1200, 1000, 140), "Europeu 1200 × 800": (1200, 800, 144)}[tipo]
    partes = []
    for i in range(7):
        partes.append((caixa(c, 100, 20, y=-l / 2 + 50 + i * (l - 100) / 6.0, z=a - 20), "madeira"))
    for y in (-l / 2 + 50, 0, l / 2 - 50):
        for x in (-c / 2 + 50, 0, c / 2 - 50):
            partes.append((caixa(100, 100, a - 40, x=x, y=y, z=20), "madeira"))
        partes.append((caixa(c, 100, 20, y=y, z=0), "madeira"))
    return partes, {"Tipo": tipo, "C × L × A": "%d × %d × %d mm (a checar)" % (c, l, a)}


def ventilador(diam):
    d = int(diam)
    partes = [(cilindro(d * 0.75, d * 0.45, base=(0, -d * 0.225, d * 0.8), eixo=(0, 1, 0)), "cinza"),
              (caixa(d * 0.7, d * 0.45, d * 0.75, x=d * 0.35, z=d * 0.8), "cinza"),
              (caixa(d * 1.8, d * 0.6, d * 0.08, x=d * 0.2, z=0), "escuro"),
              (cilindro(d * 0.5, d * 0.25, base=(0, d * 0.225, d * 0.8), eixo=(0, 1, 0)), "cinza"),
              (cilindro(d * 0.22, d * 0.5, base=(-d * 0.65, 0, d * 0.35), eixo=(1, 0, 0)), "verde")]
    return partes, {"Diâmetro do rotor": "%d mm" % d, "Tipo": "Ventilador centrífugo", "Medidas": "representativas"}


# ------------------------------------------------------------------ catálogo
# categoria -> [(id do modelo, nome, tamanhos, função(tamanho) -> (partes, informações))]
CATALOGO = [
    ("motores", "Motores", [
        ("motor_iec", "Motor elétrico trifásico (pés, IEC)", list(CARCACAS_IEC), motor),
    ]),
    ("compressores", "Compressores", [
        ("compressor_pistao", "Compressor de pistão com reservatório", ["50", "100", "200", "360", "500"],
         compressor_pistao),
        ("compressor_parafuso", "Compressor de parafuso (gabinete)", list(PARAFUSO_KW), compressor_parafuso),
    ]),
    ("valvulas", "Válvulas", [
        ("valvula_esfera", "Válvula esfera flangeada", [str(d) for d in DNS], lambda t: valvula("esfera", t)),
        ("valvula_gaveta", "Válvula gaveta flangeada", [str(d) for d in DNS], lambda t: valvula("gaveta", t)),
        ("valvula_globo", "Válvula globo flangeada", [str(d) for d in DNS], lambda t: valvula("globo", t)),
        ("valvula_retencao", "Válvula de retenção flangeada", [str(d) for d in DNS],
         lambda t: valvula("retencao", t)),
        ("valvula_borboleta", "Válvula borboleta (wafer)", [str(d) for d in DNS if d >= 50],
         lambda t: valvula("borboleta", t)),
    ]),
    ("caldeiras", "Caldeiras", [
        ("caldeira_flamotubular", "Caldeira flamotubular horizontal", list(CALDEIRA_KGH), caldeira),
    ]),
    ("altura", "Trabalho em altura", [
        ("trole", "Trole para viga I (ancoragem móvel)", list(TROLE), trole),
    ]),
    ("ar", "Ar comprimido", [
        ("frl", "Conjunto filtro, regulador e lubrificador (FRL)", list(ROSCAS), frl),
        ("purgador", "Purgador eletrônico de condensado", ["padrão"], purgador),
        ("reservatorio", "Reservatório vertical de ar", RESERVATORIO_L, reservatorio),
    ]),
    ("secadores", "Secadores", [
        ("secador_refrigeracao", "Secador por refrigeração", list(SECADOR_M3MIN), secador_refrigeracao),
        ("secador_adsorcao", "Secador por adsorção (duas torres)", list(SECADOR_M3MIN), secador_adsorcao),
    ]),
    ("pessoas", "Pessoas", [
        ("pessoa_pe", "Funcionário em pé (com capacete)", ALTURAS, lambda t: pessoa(t)),
        ("pessoa_sentado", "Funcionário sentado", ALTURAS, lambda t: pessoa(t, sentado=True, capacete=False)),
    ]),
    ("outros", "Outros", [
        ("bomba", "Motobomba centrífuga", BOMBA_DN, bomba),
        ("ventilador", "Ventilador centrífugo", ["250", "400", "630", "800"], ventilador),
        ("talha", "Talha elétrica de corrente", list(TALHA_T), talha),
        ("quadro", "Quadro elétrico", ["600 × 400", "800 × 600", "1200 × 800", "2000 × 800"], quadro),
        ("extintor", "Extintor de incêndio", ["PQS 4 kg", "PQS 6 kg", "PQS 12 kg", "CO2 6 kg", "Água 10 L"],
         extintor),
        ("palete", "Palete", ["PBR 1200 × 1000", "Europeu 1200 × 800"], palete),
    ]),
]
UNIDADE_TAMANHO = {"compressor_pistao": "L", "compressor_parafuso": "kW", "caldeira_flamotubular": "kg/h de vapor",
                   "secador_refrigeracao": "m³/min", "secador_adsorcao": "m³/min", "reservatorio": "L",
                   "valvula_esfera": "DN", "valvula_gaveta": "DN", "valvula_globo": "DN", "valvula_retencao": "DN",
                   "valvula_borboleta": "DN", "bomba": "DN", "ventilador": "mm", "motor_iec": "carcaça"}
MODELOS = {m[0]: (cat, m) for cat, _n, ms in CATALOGO for m in ms}


def gerar(modelo, tamanho):
    """(forma, cores por face, informações) do modelo no tamanho."""
    import Part
    _cat, (_id, _nome, tamanhos, fn) = MODELOS[modelo]
    if tamanho not in tamanhos:
        raise ValueError("%s não tem o tamanho %s" % (_nome, tamanho))
    partes, info = fn(tamanho)
    solidos, cores = [], []
    for forma, cor in partes:
        solidos.append(forma)
        cores += [CORES[cor]] * len(forma.Faces)
    return Part.makeCompound(solidos), cores, info


# ------------------------------------------------------------------ objeto no documento
class Componente:
    """Componente pronto: Modelo e Tamanho escolhem o desenho; a geometria não é para editar."""

    def __init__(self, obj, modelo, tamanho):
        obj.Proxy = self
        self._props(obj)
        obj.Modelo = modelo
        cat, m = MODELOS[modelo]
        obj.Tamanho = list(m[2])
        obj.Tamanho = tamanho
        obj.Categoria = dict((c[0], c[1]) for c in CATALOGO)[cat]
        obj.Nome = m[1]

    def _props(self, obj):
        def add(tipo, nome, dica, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, "Componente", dica)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyString", "Modelo", "Identificador do modelo", True)
        add("App::PropertyEnumeration", "Tamanho", "Tamanho (trocar redesenha o componente)")
        add("App::PropertyString", "Categoria", "Categoria do catálogo", True)
        add("App::PropertyString", "Nome", "Descrição para a lista de materiais", True)
        add("App::PropertyStringList", "Dados", "Medidas principais (representativas)", True)

    def execute(self, obj):
        if not obj.Modelo or obj.Modelo not in MODELOS:
            return
        forma, cores, info = gerar(obj.Modelo, obj.Tamanho)
        pl = obj.Placement
        obj.Shape = forma
        obj.Placement = pl
        obj.Dados = ["%s: %s" % (k, v) for k, v in info.items()]
        self.cores = cores

    def onDocumentRestored(self, obj):
        self._props(obj)

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VPComponente:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def updateData(self, obj, prop):
        if prop == "Shape":
            aplicar_cores(obj)

    def getIcon(self):
        import PrumoUtil
        return PrumoUtil.icone("componentes.svg")

    def dumps(self):
        return None

    def loads(self, state):
        return None


def aplicar_cores(obj):
    try:
        _f, cores, _i = gerar(obj.Modelo, obj.Tamanho)
        if len(cores) == len(obj.Shape.Faces):
            import FreeCADGui  # noqa: F401
            mats = []
            for c in cores:
                m = FreeCAD.Material()
                m.DiffuseColor = c
                mats.append(m)
            obj.ViewObject.ShapeAppearance = mats
    except Exception:
        pass


def inserir(doc, modelo, tamanho, posicao=None):
    o = doc.addObject("Part::FeaturePython", "Componente")
    Componente(o, modelo, tamanho)
    o.Label = MODELOS[modelo][1][1].split(" (")[0] + " " + tamanho
    if FreeCAD.GuiUp:
        VPComponente(o.ViewObject)
    if posicao is not None:
        o.Placement.Base = posicao
    doc.recompute()
    if FreeCAD.GuiUp:
        aplicar_cores(o)
    return o


# ------------------------------------------------------------------ janela e comandos
ICONE_CATEGORIA = {"motores": "comp_motor.svg", "compressores": "comp_compressor.svg",
                   "valvulas": "comp_valvula.svg", "caldeiras": "comp_caldeira.svg", "altura": "comp_trole.svg",
                   "ar": "comp_ar.svg", "secadores": "comp_secador.svg", "pessoas": "comp_pessoa.svg",
                   "outros": "comp_outros.svg"}


def ponto_da_selecao():
    """Onde inserir: o vértice, o centro da aresta/face selecionada ou o ponto clicado; senão a origem."""
    try:
        import FreeCADGui
        for so in FreeCADGui.Selection.getSelectionEx():
            if so.PickedPoints:
                return so.PickedPoints[0]
            for sub in so.SubObjects:
                if sub.ShapeType == "Vertex":
                    return sub.Point
                return sub.CenterOfMass if hasattr(sub, "CenterOfMass") else sub.BoundBox.Center
    except Exception:
        pass
    return None


if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    class JanelaComponentes(QtWidgets.QDialog):
        def __init__(self, categoria=None, parent=None):
            super().__init__(parent or FreeCADGui.getMainWindow())
            import PrumoUI as UI
            import PrumoUtil
            self.setObjectName("PrumoUI")
            self.setStyleSheet(UI.qss())
            self.setWindowTitle("Componentes")
            self.resize(760, 480)
            lay = QtWidgets.QHBoxLayout(self)
            self.cats = QtWidgets.QListWidget()
            self.cats.setObjectName("PrumoComponentesCategorias")
            self.cats.setIconSize(QtCore.QSize(28, 28))
            self.cats.setFixedWidth(200)
            for cid, nome, _ms in CATALOGO:
                it = QtWidgets.QListWidgetItem(QtGui.QIcon(PrumoUtil.icone(ICONE_CATEGORIA[cid])), nome)
                it.setData(QtCore.Qt.UserRole, cid)
                self.cats.addItem(it)
            lay.addWidget(self.cats)
            meio = QtWidgets.QVBoxLayout()
            self.modelos = QtWidgets.QListWidget()
            self.modelos.setObjectName("PrumoComponentesModelos")
            meio.addWidget(self.modelos, 1)
            linha = QtWidgets.QHBoxLayout()
            self.rot_tam = QtWidgets.QLabel("Tamanho")
            self.tamanho = QtWidgets.QComboBox()
            linha.addWidget(self.rot_tam)
            linha.addWidget(self.tamanho, 1)
            meio.addLayout(linha)
            self.info = QtWidgets.QLabel("")
            self.info.setWordWrap(True)
            self.info.setTextFormat(QtCore.Qt.RichText)
            self.info.setMinimumHeight(110)
            self.info.setAlignment(QtCore.Qt.AlignTop)
            meio.addWidget(self.info)
            nota = QtWidgets.QLabel("Componentes para leiaute e apresentação: medidas representativas. "
                                    "Selecione um ponto ou face antes para inserir ali.")
            nota.setObjectName("PrumoSub")
            nota.setWordWrap(True)
            meio.addWidget(nota)
            bts = QtWidgets.QHBoxLayout()
            bts.addStretch(1)
            fechar = QtWidgets.QPushButton("Fechar")
            fechar.clicked.connect(self.reject)
            self.bt_inserir = QtWidgets.QPushButton("Inserir")
            self.bt_inserir.setObjectName("PrumoPrimario")
            self.bt_inserir.setDefault(True)
            self.bt_inserir.clicked.connect(self.inserir)
            bts.addWidget(fechar)
            bts.addWidget(self.bt_inserir)
            meio.addLayout(bts)
            lay.addLayout(meio, 1)
            self.cats.currentRowChanged.connect(self._categoria)
            self.modelos.currentRowChanged.connect(self._modelo)
            self.modelos.itemDoubleClicked.connect(lambda _i: self.inserir())
            self.tamanho.currentIndexChanged.connect(lambda _i: self._mostrar())
            ids = [c[0] for c in CATALOGO]
            self.cats.setCurrentRow(ids.index(categoria) if categoria in ids else 0)
            self.inseridos = []

        def _categoria(self, i):
            self.modelos.clear()
            if i < 0:
                return
            for mid, nome, _t, _f in CATALOGO[i][2]:
                it = QtWidgets.QListWidgetItem(nome)
                it.setData(QtCore.Qt.UserRole, mid)
                self.modelos.addItem(it)
            self.modelos.setCurrentRow(0)

        def modelo(self):
            it = self.modelos.currentItem()
            return it.data(QtCore.Qt.UserRole) if it is not None else None

        def _modelo(self, _i):
            mid = self.modelo()
            self.tamanho.blockSignals(True)
            self.tamanho.clear()
            if mid:
                self.tamanho.addItems(MODELOS[mid][1][2])
                self.rot_tam.setText("Tamanho (%s)" % UNIDADE_TAMANHO.get(mid, "modelo"))
            self.tamanho.blockSignals(False)
            self._mostrar()

        def _mostrar(self):
            mid, tam = self.modelo(), self.tamanho.currentText()
            if not mid or not tam:
                self.info.setText("")
                return
            try:
                _p, info = MODELOS[mid][1][3](tam)
                self.info.setText("<b>%s</b><br>%s" % (MODELOS[mid][1][1], "<br>".join(
                    "%s: %s" % (k, v) for k, v in info.items())))
            except Exception as exc:
                self.info.setText("Não foi possível montar: %s" % exc)

        def inserir(self):
            mid, tam = self.modelo(), self.tamanho.currentText()
            if not mid:
                return None
            doc = FreeCAD.ActiveDocument or FreeCAD.newDocument()
            doc.openTransaction("Inserir componente")
            try:
                o = inserir(doc, mid, tam, ponto_da_selecao())
            finally:
                doc.commitTransaction()
            self.inseridos.append(o)
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(o)
                if len(doc.Objects) == 1:
                    FreeCADGui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass
            return o

    _JANELA = {"j": None}

    def abrir(categoria=None):
        j = JanelaComponentes(categoria)
        _JANELA["j"] = j
        j.show()
        return j

    class CmdComponentes:
        def __init__(self, categoria=None, nome="Componentes"):
            self.categoria, self.nome = categoria, nome

        def GetResources(self):
            import PrumoUtil
            ic = ICONE_CATEGORIA.get(self.categoria, "componentes.svg")
            return {"Pixmap": PrumoUtil.icone(ic), "MenuText": self.nome,
                    "ToolTip": "Inserir %s pronto no projeto (modelo para leiaute; medidas representativas)."
                               % (self.nome.lower() if self.categoria else "componente")}

        def IsActive(self):
            return True

        def Activated(self):
            abrir(self.categoria)

    def registrar_comandos():
        FreeCADGui.addCommand("Prumo_Componentes", CmdComponentes())
        for cid, nome, _ms in CATALOGO:
            FreeCADGui.addCommand("Prumo_Componentes_" + cid, CmdComponentes(cid, nome))
