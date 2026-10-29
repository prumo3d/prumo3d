# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verificação de barras de aço pela ABNT NBR 8800:2024 (Versão Corrigida 2025, com a Errata 1) e
combinações de ações pela ABNT NBR 8681:2025.

Cada função devolve o esforço resistente de cálculo e um texto curto com o modo que governou, para
a memória de cálculo. Unidades: N, mm, MPa.

O que entra (com o item da norma no comentário) e o que fica de fora está em LIMITES e A_CHECAR,
reproduzidos na memória de cálculo. As fórmulas e os coeficientes foram conferidos na pesquisa
registrada em prumo-build/ferramentas/nbr8800_fontes.md; a atualização para a edição de 2024 foi
conferida no texto da norma (catálogo ABNT Confea/Mútua) em 21/10/2026.

Principais mudanças em relação a 2008 já incorporadas: sem coeficiente K (Ne com o comprimento
destravado, a estabilidade global fica com a análise de 2ª ordem com imperfeições — 4.10); flambagem
local na compressão pela área efetiva (5.3.4, Tabelas 4 e 5) em vez de Q; Cb dentro de λr e sem o teto
de 3,0 (Anexo D); kv = 5,34 em almas sem enrijecedores (5.4.3.1); numeração nova (4.10, Anexo B, C, D).
"""

import math

E_ACO = 200000.0     # MPa — 4.6.2 (módulo de elasticidade do aço)
G_ACO = 77000.0      # MPa — 4.6.2 (módulo de elasticidade transversal)
GAMA_A1 = 1.10       # Tabela 3 (4.9.2) — escoamento, flambagem e instabilidade (combinações normais)
GAMA_A2 = 1.35       # Tabela 3 — ruptura
GAMA_W2 = 1.35       # Tabela 9 — metal da solda (combinações normais)
FW_ELETRODO = {"E60XX": 415.0, "E70XX": 485.0, "E80XX": 550.0}   # Tabela A.4 — fw (MPa)

EDICAO = "ABNT NBR 8800:2024 (Versão Corrigida 2025) e ABNT NBR 8681:2025"

LIMITES = [
    "Análise elástica de 2ª ordem (P-Δ e P-δ, cada trecho em 4 elementos) nas combinações últimas, com as "
    "imperfeições de 4.10.7: força nocional de 0,3 % da carga gravitacional de cálculo em cada nó, nas duas "
    "direções horizontais e nos dois sentidos, nas combinações sem ação variável horizontal; com média "
    "deslocabilidade (4.10.4), rigidez reduzida a 80 % (EI e EA). Grande deslocabilidade é avisada (exige "
    "análise com não linearidade de material). Deslocamentos de serviço em 1ª ordem.",
    "Força axial de flambagem Ne com o comprimento destravado L (5.3.5, sem coeficiente K): a estabilidade "
    "global fica com a análise de 2ª ordem. L e Lb são os do membro (linhas colineares seguidas sem outra "
    "barra nem apoio no nó contam como uma barra só); balanço com Cb = 1.",
    "Flambagem local na compressão pela área efetiva (5.3.4, Tabelas 4 e 5), com b das mesas e das almas "
    "conforme 5.1.2.2 (perfis laminados; parede de tubo retangular com a parte plana b = lado − 3t, raio "
    "externo admitido de 1,5t).",
    "Tração: seção líquida igual à bruta (Ae = Ag, Ct = 1,0): só vale para barras sem furos com a força "
    "entrando por todos os elementos da seção (5.2).",
    "Deslocamentos com a combinação rara (a favor da segurança); pelo Anexo B o responsável técnico pode "
    "adotar a quase permanente ou a frequente conforme o efeito a evitar (equipamentos: frequente, B.2).",
    "Seções sem raios de concordância nos perfis U, I americanos, cantoneiras e tubos (o catálogo não "
    "traz); perfis W/HP com os raios. Constante de torção J pelas fórmulas de paredes finas (sem os "
    "raios), menor que a de catálogo (a favor da segurança na FLT).",
    "Torção das barras não verificada; na rigidez entra só a torção uniforme (sem empenamento), a favor "
    "da segurança na estabilidade em planta.",
    "Cantoneiras simples tratadas como ligadas por uma aba em treliça plana (5.3.5.4.2), com a análise nos "
    "eixos principais; flexão de cantoneiras pelo início do escoamento (W1/W2); cortante na aba com kv = 1,2 "
    "(a checar: a cantoneira simples não está na lista de 5.4.1.1).",
    "As barras ficam sobre as linhas do esqueleto (excentricidade do ponto de fixação desprezada).",
]



def _raiz(x):
    return math.sqrt(max(x, 0.0))


# ------------------------------------------------------------------ tração (5.2)
def tracao(p, fy, fu):
    Ag = p["A"]
    esc = Ag * fy / GAMA_A1                  # 5.2.2 a)
    rup = Ag * fu / GAMA_A2                  # 5.2.2 b), Ae = Ag (Ct = 1)
    if esc <= rup:
        return esc, "escoamento da seção bruta"
    return rup, "ruptura da seção líquida (Ae = Ag)"


# ------------------------------------------------------------------ flambagem local (5.3.4)
# (b/t)lim (×√(E/fy)) e c1, c2 da Tabela 5 por grupo de elemento
GRUPOS = {
    "AA tubo retangular": (1.40, 0.20, 1.38),      # grupo 1
    "AA": (1.49, 0.18, 1.31),                      # grupo 2 (almas de I, H e U)
    "AL cantoneira": (0.45, 0.22, 1.49),           # grupo 3 (cantoneira simples)
    "AL mesa laminada": (0.56, 0.22, 1.49),        # grupo 4 (mesas de I, H e U laminados)
    # grupo 5 (mesas soldadas): 0,64·√(E/(fy/kc)); kc = 0,35 (mínimo de 4/√(h/tw)), a favor da segurança
    "AL soldada": (0.64 * math.sqrt(0.35), 0.22, 1.49),
}


def _pol(p):
    """Como chamar a seção poligonal no relatório: a desenhada no projeto ou a de catálogo (T, Ue, tubo
    retangular, barras), as duas verificadas pelo método geral."""
    if p.get("catalogo"):
        return "%s de catálogo, método geral" % p.get("forma_nome", "seção")
    return "seção personalizada"


def elementos_comprimidos(p):
    """[(nome, grupo, b, t, quantos)] dos elementos da seção para 5.3.4."""
    t = p["tipo"]
    if t == "I":
        return [("mesa", "AL mesa laminada", p["bf"] / 2.0, p["tf"], 4), ("alma", "AA", p["h"], p["tw"], 1)]
    if t == "U":
        return [("mesa", "AL mesa laminada", p["bf"], p["tf"], 2), ("alma", "AA", p["h"], p["tw"], 1)]
    if t == "L":
        return [("aba", "AL cantoneira", p["b"], p["t"], 2)]
    if t == "TQ":
        # parte plana da parede: a mesma das outras verificações (lado − 3t, raio externo ≈ 1,5t; a favor
        # da segurança diante do lado − 4t de quando o raio não é conhecido)
        return [("parede", "AA tubo retangular", p["h"], p["t"], 4)]
    return []


def area_efetiva(p, fy, chi):
    """(Aef, texto) pela 5.3.4: elementos com b/t > (b/t)lim/√χ têm largura efetiva bef."""
    E = E_ACO
    if p["tipo"] == "TUBO":
        dt = p["D_t"]
        if dt <= 0.11 * E / fy:
            return p["A"], ""
        txt = "parede de tubo esbelta"
        if dt > 0.45 * E / fy:
            txt += "; D/t acima de 0,45·E/fy: fora do escopo da norma"
        return (0.038 * E / (dt * fy) + 2.0 / 3.0) * p["A"], txt
    if p["tipo"] == "POL":
        return elementos_pol_area_efetiva(p, fy, chi)
    perda = 0.0
    notas = []
    for nome, grupo, b, t, n in elementos_comprimidos(p):
        k, c1, c2 = GRUPOS[grupo]
        lim = k * _raiz(E / fy)
        if t <= 0 or b <= 0 or b / t <= lim / _raiz(chi):
            continue
        sel = (c2 * lim / (b / t)) ** 2 * fy
        r = _raiz(sel / (chi * fy))
        bef = min(max(b * (1 - c1 * r) * r, 0.0), b)
        perda += (b - bef) * t * n
        notas.append("%s esbelta (bef = %.0f de %.0f mm)" % (nome, bef, b))
    return p["A"] - perda, "; ".join(notas)


def elementos_pol_area_efetiva(p, fy, chi):
    """Seção personalizada: elementos retangulares (chapas) detectados no contorno (PrumoSecao)."""
    E = E_ACO
    perda = 0.0
    notas = []
    for el in p.get("chapas", []):
        # chapas de seção montada: AA como parede de caixão (grupo 1), AL como mesa soldada (grupo 5)
        grupo = "AA tubo retangular" if el["apoiada_nas_duas"] else "AL soldada"
        k, c1, c2 = GRUPOS[grupo]
        b, t = el["b"], el["t"]
        lim = k * _raiz(E / fy)
        if t <= 0 or b <= 0 or b / t <= lim / _raiz(chi):
            continue
        sel = (c2 * lim / (b / t)) ** 2 * fy
        r = _raiz(sel / (chi * fy))
        bef = min(max(b * (1 - c1 * r) * r, 0.0), b)
        perda += (b - bef) * t
        notas.append("chapa %s esbelta (bef = %.0f de %.0f mm)" % ("AA" if el["apoiada_nas_duas"] else "AL",
                                                                     bef, b))
    if not p.get("chapas"):
        notas.append(_pol(p) + " sem chapas retangulares reconhecidas: flambagem local não verificada")
    return p["A"] - perda, "; ".join(notas)


# ------------------------------------------------------------------ compressão (5.3 e Anexo E)
def chi(l0):
    """Fator de redução (5.3.3)."""
    if l0 <= 1.5:
        return 0.658 ** (l0 ** 2)
    return 0.877 / l0 ** 2


def forca_ne(p, L, K=1.0, Kz=1.0, uma_aba=True):
    """Ne (5.3.5): menor entre flexão em x, em y e torção/flexo-torção, com o comprimento destravado L
    (sem coeficiente K na edição de 2024; K e Kz ficam só por compatibilidade). Retorna (Ne, modo)."""
    E, G = E_ACO, G_ACO
    Lx = Ly = L
    Lz = L
    t = p["tipo"]
    if t == "L" and uma_aba:
        # 5.3.5.4.2: cantoneira simples ligada por uma aba (treliça plana), abas iguais
        rx1 = p["rx"]
        Lx1 = L
        if Lx1 / rx1 <= 80:
            KL1 = 72 * rx1 + 0.75 * Lx1
        else:
            KL1 = 32 * rx1 + 1.25 * Lx1
        return math.pi ** 2 * E * p["Ix"] / KL1 ** 2, "cantoneira ligada por uma aba (5.3.5.4.2, Lx1,eq = %.0f mm)" % KL1
    if t == "POL" and p.get("geral"):
        return _ne_geral(p, L)
    if t == "L" or (t == "POL" and abs(p.get("Ixy", 0.0)) > 1e-6 * p["Ix"]):
        Nmin = math.pi ** 2 * E * p["I2"] / Lx ** 2
        modos = [(Nmin, "flexão (eixo de menor inércia)")]
    else:
        Nex = math.pi ** 2 * E * p["Ix"] / Lx ** 2
        Ney = math.pi ** 2 * E * p["Iy"] / Ly ** 2
        modos = [(Nex, "flexão em x"), (Ney, "flexão em y")]
    x0, y0 = p.get("x0", 0.0), p.get("y0", 0.0)
    r0q = p["rx"] ** 2 + p["ry"] ** 2 + x0 ** 2 + y0 ** 2
    Nez = (math.pi ** 2 * E * p.get("Cw", 0.0) / Lz ** 2 + G * p["J"]) / r0q
    if t in ("I", "TQ", "TUBO", "POL"):
        if t == "I":
            modos.append((Nez, "torção"))
        elif t == "POL":
            modos.append((Nez, "torção (centro de cisalhamento no centróide: malha da seção falhou, a checar)"))
    elif t == "U":
        # monossimétrico: eixo de simetria x (horizontal da seção, onde fica o centro de cisalhamento)
        Nex = math.pi ** 2 * E * p["Ix"] / Lx ** 2
        H = 1 - (x0 ** 2) / r0q
        Nexz = (Nex + Nez) / (2 * H) * (1 - _raiz(1 - 4 * Nex * Nez * H / (Nex + Nez) ** 2))
        modos.append((Nexz, "flexo-torção"))
    elif t == "L":
        # cantoneira de abas iguais: simetria no eixo principal de maior inércia
        I1 = p["I1"]
        Ne1 = math.pi ** 2 * E * I1 / Lx ** 2
        d0q = x0 ** 2 + y0 ** 2
        H = 1 - d0q / r0q
        Ne1z = (Ne1 + Nez) / (2 * H) * (1 - _raiz(1 - 4 * Ne1 * Nez * H / (Ne1 + Nez) ** 2))
        modos.append((Ne1z, "flexo-torção"))
    return min(modos, key=lambda m: m[0])


def _ne_geral(p, L):
    """Seção qualquer: menor raiz de (N−N1)(N−N2)(N−Nz) − N²(N−N2)(x0/r0)² − N²(N−N1)(y0/r0)² = 0, nos
    eixos principais (x0, y0: centro de cisalhamento − centróide nesses eixos)."""
    import numpy as np
    E, G = E_ACO, G_ACO
    g = p["geral"]
    A = p["A"]
    N1 = math.pi ** 2 * E * g["I1"] / L ** 2
    N2 = math.pi ** 2 * E * g["I2"] / L ** 2
    x0, y0 = g["x0p"], g["y0p"]
    r0q = (g["I1"] + g["I2"]) / A + x0 ** 2 + y0 ** 2
    Nz = (math.pi ** 2 * E * g["Cw"] / L ** 2 + G * p["J"]) / r0q
    a, b = x0 ** 2 / r0q, y0 ** 2 / r0q
    pol = np.polysub(np.polymul(np.polymul([1, -N1], [1, -N2]), [1, -Nz]),
                     np.polyadd(np.polymul([a, 0, 0], [1, -N2]), np.polymul([b, 0, 0], [1, -N1])))
    raizes = [r.real for r in np.roots(pol) if abs(r.imag) <= 1e-6 * abs(r) and r.real > 0]
    Ne = min(raizes) if raizes else min(N1, N2, Nz)
    menor = min((N1, "flexão no eixo principal 1"), (N2, "flexão no eixo principal 2"), (Nz, "torção"))
    if Ne < 0.999 * menor[0]:
        modo = "flexo-torção (%s)" % _pol(p)
    else:
        modo = menor[1] + " (%s)" % _pol(p)
    return Ne, modo


def compressao(p, fy, L, K=1.0, Kz=1.0):
    """(Nc,Rd, texto) pela 5.3: Nc,Rd = χ·Aef·fy/γa1, λ0 = √(Ag·fy/Ne). A esbeltez L/r ≤ 200 é
    recomendação (5.3.7): vira aviso."""
    Ne, modo = forca_ne(p, L)
    l0 = _raiz(p["A"] * fy / Ne)
    x = chi(l0)
    Aef, nota = area_efetiva(p, fy, x)
    N = x * Aef * fy / GAMA_A1
    rmin = p["rmin"] if p["tipo"] in ("L", "POL") else min(p["rx"], p["ry"])
    esb = L / rmin
    txt = "%s; λ0 = %.2f; χ = %.3f; Aef/Ag = %.3f" % (modo, l0, x, Aef / p["A"])
    if nota:
        txt += " (%s)" % nota
    if esb > 200:
        txt += "; ATENÇÃO: L/r = %.0f > 200 (recomendação de 5.3.7)" % esb
    return N, txt


# ------------------------------------------------------------------ flexão (5.4.2 e Anexo G)
def _wef_alma_u(p, fy):
    """Módulo efetivo do U no eixo de menor inércia com a alma comprimida reduzida (bef, F.3.2,
    σ = fy, ca = 0,34), recalculando a linha neutra."""
    E = E_ACO
    h, tw = p["h"], p["tw"]
    bef = 1.92 * tw * _raiz(E / fy) * (1 - 0.34 / (h / tw) * _raiz(E / fy))
    bef = min(max(bef, 0.0), h)
    perda = (h - bef) * tw
    if perda <= 0:
        return p["Wy"]
    # alma no lado das costas do U: u da linha média da alma em relação ao centróide
    xa = -p["bf"] / 2.0 + tw / 2.0 - p["cu"]
    A_ef = p["A"] - perda
    dx = -perda * xa / A_ef
    I_ef = p["Iy"] + p["A"] * dx ** 2 - perda * (xa - dx) ** 2
    c = max(p["bf"] / 2.0 - p["cu"] - dx, p["bf"] / 2.0 + p["cu"] + dx)
    return I_ef / c


def _wef_tubo(p, fy):
    """Módulo efetivo do tubo retangular (Nota 4 da Tabela G.1): mesa comprimida com largura bef
    (F.3.2, σ = fy), desprezando o deslocamento da linha neutra (aproximação)."""
    E = E_ACO
    b, t, s = p["h"], p["t"], p["b"]
    bef = 1.92 * t * _raiz(E / fy) * (1 - 0.38 / (b / t) * _raiz(E / fy))
    bef = min(max(bef, 0.0), b)
    perda = (b - bef) * t                    # área tirada da mesa comprimida (em y = +(s-t)/2)
    if perda <= 0:
        return p["Wx"]
    yp = s / 2.0 - t / 2.0
    A_ef = p["A"] - perda
    dy = -perda * yp / A_ef                  # nova linha neutra (desce)
    I_ef = p["Ix"] + p["A"] * dy ** 2 - perda * (yp - dy) ** 2
    c = max(s / 2.0 - dy, s / 2.0 + dy)
    return I_ef / c


def _interp(Mpl, Mr, lam, lp, lr, Mcr, Cb=1.0, com_cb=False):
    if lam <= lp:
        return Mpl
    if lam <= lr:
        # Anexo D (2024): interpolação linear sem multiplicar por Cb (o Cb já entra em λr e em Mcr)
        return Mpl - (Mpl - Mr) * (lam - lp) / (lr - lp)
    return min(Mcr, Mpl)       # D.2.1: Mcr/γa1 ≤ Mpl/γa1


def flexao_x(p, fy, Lb, Cb=1.0):
    """Mx,Rd: flexão em torno do eixo x (maior inércia nos perfis I e U). (MRd, modo)."""
    E = E_ACO
    t = p["tipo"]
    W, Z = p["Wx"], p["Zx"]
    Mpl = Z * fy
    if t in ("I", "U"):
        sr = 0.3 * fy
        Mr = (fy - sr) * W
        # FLT
        ry, Iy, J, Cw = p["ry"], p["Iy"], p["J"], p["Cw"]
        lam = Lb / ry
        lp = 1.76 * _raiz(E / fy)
        b1 = (fy - sr) * W / (E * J)
        # Tabela D.1 (2024): Cb dentro de λr
        lr = 1.38 * Cb * _raiz(Iy * J) / (ry * J * b1) * _raiz(1 + _raiz(1 + 27 * Cw * b1 ** 2 / (Cb ** 2 * Iy)))
        Mcr = Cb * math.pi ** 2 * E * Iy / Lb ** 2 * _raiz(Cw / Iy * (1 + 0.039 * J * Lb ** 2 / Cw))
        flt = _interp(Mpl, Mr, lam, lp, lr, Mcr, Cb, True)
        # FLM
        lam_m = p["bt_mesa"]
        lpm = 0.38 * _raiz(E / fy)
        lrm = 0.83 * _raiz(E / (fy - sr))
        Mcrm = 0.69 * E / lam_m ** 2 * W
        flm = _interp(Mpl, Mr, lam_m, lpm, lrm, Mcrm)
        # FLA
        lam_a = p["h_tw"]
        lpa, lra = 3.76 * _raiz(E / fy), 5.70 * _raiz(E / fy)
        fla = _interp(Mpl, fy * W, lam_a, lpa, lra, fy * W)     # acima de λr: viga esbelta (a checar)
        modos = [(flt, "FLT (Lb = %.0f mm, Cb = %.2f)" % (Lb, Cb)), (flm, "FLM"), (fla, "FLA")]
        if lam_a > lra:
            modos.append((fy * W, "alma esbelta (Anexo E não aplicado: a checar)"))
    elif t == "TQ":
        # Tabela G.1, caixão e tubo retangular
        sr = 0.3 * fy
        Wef = _wef_tubo(p, fy)
        lam = p["bt_parede"]
        lp, lr = 1.12 * _raiz(E / fy), 1.40 * _raiz(E / fy)
        flm = _interp(Mpl, fy * Wef, lam, lp, lr, Wef ** 2 / W * fy)
        fla = _interp(Mpl, fy * W, lam, 2.42 * _raiz(E / fy), 5.70 * _raiz(E / fy), fy * W)
        JA = _raiz(p["J"] * p["A"])
        Mr = (fy - sr) * W
        lam_t = Lb / p["ry"]
        lp_t = 0.13 * E * JA / Mpl
        lr_t = 2.00 * Cb * E * JA / Mr
        Mcr_t = 2.00 * Cb * E * JA / lam_t if lam_t > 0 else Mpl
        flt = _interp(Mpl, Mr, lam_t, lp_t, lr_t, Mcr_t, Cb, True)
        modos = [(flm, "FLM"), (fla, "FLA"), (flt, "FLT")]
    elif t == "TUBO":
        dt = p["D_t"]
        if dt <= 0.07 * E / fy:
            modos = [(Mpl, "seção compacta")]
        elif dt <= 0.31 * E / fy:
            modos = [((0.021 * E / dt + fy) * W, "flambagem local da parede")]
        else:
            modos = [(0.33 * E / dt * W, "parede esbelta")]
    elif t == "POL":
        return _flexao_pol(p, fy, Lb, Cb, 1)
    else:  # cantoneira: início do escoamento no eixo principal de maior inércia (a favor da segurança)
        W = p["W1"]
        modos = [(fy * W, "início do escoamento (cantoneira, eixo principal de maior inércia)")]
    M, modo = min(modos, key=lambda m: m[0])
    M = min(M, 1.5 * W * fy)
    return M / GAMA_A1, modo


def flexao_y(p, fy, Lb=1.0, Cb=1.0):
    """My,Rd: flexão em torno do eixo y (menor inércia nos perfis I e U). Lb e Cb só valem para a seção
    personalizada, em que o eixo y pode ser o de maior inércia (FLT)."""
    E = E_ACO
    t = p["tipo"]
    W, Z = p["Wy"], p["Zy"]
    Mpl = Z * fy
    if t in ("I", "U"):
        lam = p["bt_mesa"]
        lp, lr = 0.38 * _raiz(E / fy), 0.83 * _raiz(E / (0.7 * fy))
        Mcr = 0.69 * E / lam ** 2 * W
        M = _interp(Mpl, 0.7 * fy * W, lam, lp, lr, Mcr)
        modo = "FLM (eixo de menor inércia)"
        if t == "U":
            # Tabela G.1: FLA da alma do U no eixo de menor inércia (λp = 1,12, λr = 1,40 √(E/fy))
            lam_a = p["h_tw"]
            Wef = _wef_alma_u(p, fy)
            fla = _interp(Mpl, fy * Wef, lam_a, 1.12 * _raiz(E / fy), 1.40 * _raiz(E / fy), Wef ** 2 / W * fy)
            if fla < M:
                M, modo = fla, "FLA da alma (eixo de menor inércia)"
    elif t in ("TQ", "TUBO"):
        return flexao_x(p, fy, 1.0)
    elif t == "POL":
        return _flexao_pol(p, fy, Lb, Cb, 2)
    else:
        W = p["W2"]
        M, modo = fy * W, "início do escoamento (cantoneira, eixo principal de menor inércia)"
    M = min(M, 1.5 * W * fy)
    return M / GAMA_A1, modo


def _eixos_pol(p, eixo):
    """(I_flexão, I_lateral, W, Z, β, direção do eixo de flexão (u, v), r_lateral) da seção qualquer.
    eixo 1: x geométrico (ou o principal de maior inércia se a seção for assimétrica); eixo 2: o outro."""
    g = p.get("geral")
    assim = abs(p.get("Ixy", 0.0)) > 1e-6 * p["Ix"]
    if g:
        th = g["theta"]
        e1 = (math.cos(th), math.sin(th))
        ax = [(g["I1"], g["I2"], g["beta1"], e1), (g["I2"], g["I1"], g["beta2"], (-e1[1], e1[0]))]
        if assim and g["I1"] < g["I2"]:
            ax.reverse()
        Ib, Il, beta, d = ax[eixo - 1]
    else:
        Ib, Il = (p["Ix"], p["Iy"]) if eixo == 1 else (p["Iy"], p["Ix"])
        beta, d = 0.0, ((1.0, 0.0) if eixo == 1 else (0.0, 1.0))
    if assim:
        W = p["W1"] if eixo == 1 else p["W2"]
        Z = W                      # módulo plástico nos eixos principais não calculado: escoamento
    else:
        W, Z = (p["Wx"], p["Zx"]) if eixo == 1 else (p["Wy"], p["Zy"])
    return Ib, Il, W, Z, beta, d, math.sqrt(Il / p["A"])


def _mcr_geral(Il, J, Cw, beta, L, Cb):
    """Momento crítico elástico (seção mono ou assimétrica), no sentido desfavorável do β de Wagner."""
    E, G = E_ACO, G_ACO
    Pe = math.pi ** 2 * E * Il / L ** 2
    return Cb * Pe * (-abs(beta) / 2.0 + _raiz(beta ** 2 / 4.0 + Cw / Il + G * J * L ** 2 / (math.pi ** 2 * E * Il)))


def _flexao_pol(p, fy, Lb, Cb, eixo):
    """Seção personalizada: FLT pelo Mcr geral com os limites da NBR na forma dos perfis I (λp em
    Lb = 1,76·r·√(E/fy); λr onde Mcr = Mr, com Cb) e flambagem local chapa a chapa (mesas: chapas
    paralelas ao eixo de flexão; almas: perpendiculares). Retorna (MRd, modo)."""
    E = E_ACO
    Ib, Il, W, Z, beta, d, rl = _eixos_pol(p, eixo)
    Mpl = min(Z * fy, 1.5 * W * fy)
    sr = 0.3 * fy
    Mr = (fy - sr) * W
    modos = [(Mpl, "plastificação" if Z != W else "início do escoamento (seção assimétrica)")]
    if Il < 0.999 * Ib and Lb > 1.0:
        J, Cw = p["J"], p.get("Cw", 0.0)
        Lp = 1.76 * rl * _raiz(E / fy)
        lo, hi = 1e-3, 1e7
        if _mcr_geral(Il, J, Cw, beta, hi, Cb) >= Mr:
            Lr = hi
        else:
            for _ in range(200):
                mid = _raiz(lo * hi)
                if _mcr_geral(Il, J, Cw, beta, mid, Cb) > Mr:
                    lo = mid
                else:
                    hi = mid
            Lr = hi
        Mcr = _mcr_geral(Il, J, Cw, beta, Lb, Cb)
        if Lb <= Lp:
            flt = Mpl
        elif Lb <= Lr and Lr > Lp:
            flt = Mpl - (Mpl - Mr) * (Lb - Lp) / (Lr - Lp)
        else:
            flt = min(Mcr, Mpl)
        modos.append((flt, "FLT (Lb = %.0f mm, Cb = %.2f, Mcr geral)" % (Lb, Cb)))
    kc = 0.35
    for ch in p.get("chapas", []):
        lam = ch["b"] / ch["t"]
        paralela = abs(ch["direcao"][0] * d[0] + ch["direcao"][1] * d[1]) > math.cos(math.radians(30))
        if paralela or not ch["apoiada_nas_duas"]:
            if ch["apoiada_nas_duas"]:       # mesa de caixão
                lp, lr = 1.12 * _raiz(E / fy), 1.40 * _raiz(E / fy)
                mcr = fy * W * (lr / lam) ** 2
                nome = "FLM (mesa AA)"
            else:                            # mesa soldada em balanço (kc mínimo)
                lp, lr = 0.38 * _raiz(E / fy), 0.95 * _raiz(kc * E / (0.7 * fy))
                mcr = 0.90 * E * kc * W / lam ** 2
                nome = "FLM (mesa AL)"
            mr = Mr
        else:
            lp, lr = 3.76 * _raiz(E / fy), 5.70 * _raiz(E / fy)
            mr = fy * W
            mcr = fy * W * (lr / lam) ** 2
            nome = "FLA"
        if lam <= lp:
            continue
        m = _interp(Mpl, mr, lam, lp, lr, mcr)
        txt = "%s (b/t = %.1f)" % (nome, lam)
        if lam > lr and nome != "FLM (mesa AL)":
            txt += ", acima de λr: aproximado (a checar)"
        modos.append((m, txt))
    M, modo = min(modos, key=lambda x: x[0])
    return M / GAMA_A1, modo + " — " + _pol(p)


# ------------------------------------------------------------------ cortante (5.4.3)
def _vrd(Aw, fy, lam, kv):
    E = E_ACO
    Vpl = 0.60 * Aw * fy
    lp = 1.10 * _raiz(kv * E / fy)
    lr = 1.37 * _raiz(kv * E / fy)
    if lam <= lp:
        return Vpl / GAMA_A1
    if lam <= lr:
        return lp / lam * Vpl / GAMA_A1
    return 1.24 * (lp / lam) ** 2 * Vpl / GAMA_A1


def _vrd_tubo(p, fy, Lv):
    """5.4.3.6: Vrd = 0,5 τcr Ag / γa1, com td = 0,93 t (tubo com costura: a favor da segurança
    também para o sem costura)."""
    E = E_ACO
    D_t = p["D_t"] / 0.93
    D = p["D"]
    Lv = max(Lv, D)
    t1 = 1.60 * E / (_raiz(Lv / D) * D_t ** 1.25)
    t2 = 0.78 * E / D_t ** 1.5
    tcr = min(max(t1, t2), 0.60 * fy)
    return 0.5 * tcr * p["A"] / GAMA_A1


def cortante_z(p, fy, Lv=1e9):
    """Cortante na direção da altura (paralela à alma nos perfis I e U)."""
    t = p["tipo"]
    if t in ("I", "U"):
        return _vrd(p["d"] * p["tw"], fy, p["h_tw"], 5.34), "alma (kv = 5,34)"
    if t == "TQ":
        return _vrd(2 * p["h"] * p["t"], fy, p["bt_parede"], 5.0), "paredes (kv = 5,0)"
    if t == "TUBO":
        return _vrd_tubo(p, fy, Lv), "tubo circular (5.4.3.6)"
    if t == "POL":
        return _cortante_pol(p, fy, (0.0, 1.0))
    return _vrd(p["b"] * p["t"], fy, p["bt_aba"], 1.2), "aba"


def _cortante_pol(p, fy, direcao):
    """Seção personalizada: almas = chapas paralelas à força (até 30°); Aw = Σ b·t, kv = 5,0 com as duas
    bordas presas e 1,2 com borda livre, λ a maior b/t. Sem chapas reconhecidas: Aw = A/2 (a checar)."""
    almas = [c for c in p.get("chapas", [])
             if abs(c["direcao"][0] * direcao[0] + c["direcao"][1] * direcao[1]) > math.cos(math.radians(30))]
    if not almas:
        return 0.6 * fy * p["A"] / 2.0 / GAMA_A1, _pol(p) + " (Av = A/2, a checar)"
    V = 0.0
    for c in almas:
        V += _vrd(c["b"] * c["t"], fy, c["b"] / c["t"], 5.0 if c["apoiada_nas_duas"] else 1.2)
    return V, "%s (%d chapa(s) paralela(s) à força)" % (_pol(p), len(almas))


def cortante_y(p, fy, Lv=1e9):
    """Cortante na direção da largura (paralela às mesas nos perfis I e U)."""
    t = p["tipo"]
    if t == "I":
        return _vrd(2 * p["bf"] * p["tf"], fy, p["bt_mesa"], 1.2), "mesas"
    if t == "U":
        return _vrd(2 * p["bf"] * p["tf"], fy, p["bt_mesa"], 1.2), "mesas"
    if t == "POL":
        return _cortante_pol(p, fy, (1.0, 0.0))
    return cortante_z(p, fy, Lv)


# ------------------------------------------------------------------ interação (5.5.1.2)
def interacao(N, NRd, Mx, MxRd, My, MyRd):
    r = abs(N) / NRd if NRd > 0 else 0.0
    m = (abs(Mx) / MxRd if MxRd > 0 else 0.0) + (abs(My) / MyRd if MyRd > 0 else 0.0)
    if r >= 0.2:
        return r + 8.0 / 9.0 * m, "N/NRd + 8/9 (Mx/MxRd + My/MyRd)"
    return r / 2.0 + m, "N/(2 NRd) + Mx/MxRd + My/MyRd"


def cb(m_max, ma, mb, mc):
    """Fator de modificação para diagrama de momento não uniforme (Anexo D, 2024), Rm = 1."""
    den = 2.5 * m_max + 3 * ma + 4 * mb + 3 * mc
    if den <= 0:
        return 1.0
    return 12.5 * m_max / den          # Anexo D (2024): sem o teto de 3,0


# ------------------------------------------------------------------ verificação de uma barra
def verificar(p, fy, fu, L, esf, K=1.0, Kz=1.0, balanco=False):
    """Taxas de uso (esforço solicitante / resistente) de uma barra num conjunto de esforços.

    esf: dict com N (tração +), Mx, My (máximos absolutos), Vz, Vy e os momentos nos quartos do
    vão para o Cb: Mq = (|M| a 1/4, 1/2, 3/4). Retorna dict com taxas e textos."""
    res = {}
    N = esf["N"]
    if N >= 0:
        NRd, modo_n = tracao(p, fy, fu)
    else:
        NRd, modo_n = compressao(p, fy, L, K, Kz)
    # balanço com extremidade livre sem contenção → Cb = 1,00
    if balanco or not esf["Mx"]:
        c = 1.0
    elif esf.get("Mcb"):        # membro de várias linhas: momentos do membro inteiro
        c = cb(*esf["Mcb"])
    else:
        c = cb(abs(esf["Mx"]), *esf.get("Mq", (abs(esf["Mx"]),) * 3))
    MxRd, modo_mx = flexao_x(p, fy, L, c)
    MyRd, modo_my = flexao_y(p, fy, L, 1.0)
    VzRd, modo_vz = cortante_z(p, fy, L / 2.0)
    VyRd, modo_vy = cortante_y(p, fy, L / 2.0)
    tx_int, f_int = interacao(N, NRd, esf["Mx"], MxRd, esf["My"], MyRd)
    res["taxas"] = {
        "Normal": abs(N) / NRd if NRd else 0.0,
        "Flexão x": abs(esf["Mx"]) / MxRd if MxRd else 0.0,
        "Flexão y": abs(esf["My"]) / MyRd if MyRd else 0.0,
        "Cortante z": abs(esf["Vz"]) / VzRd if VzRd else 0.0,
        "Cortante y": abs(esf["Vy"]) / VyRd if VyRd else 0.0,
        "Combinada": tx_int,
    }
    res["resistencias"] = {"NRd": NRd, "MxRd": MxRd, "MyRd": MyRd, "VzRd": VzRd, "VyRd": VyRd}
    res["modos"] = {"N": modo_n, "Mx": modo_mx, "My": modo_my, "Vz": modo_vz, "Vy": modo_vy,
                    "interacao": f_int, "Cb": c}
    avisos = []
    if p["tipo"] == "TQ":
        avisos.append("tubo retangular de parede fina (metalon) costuma ser formado a frio: a norma é a "
                      "NBR 14762 (verificação pela NBR 8800 a checar)")
    if p.get("formado_a_frio"):
        avisos.append("%s é formado a frio: a norma é a NBR 14762 (verificação pela NBR 8800 a checar)"
                      % p.get("forma_nome", "o perfil"))
    if p["tipo"] == "POL":
        if p.get("geral"):
            avisos.append(_pol(p) + ": centro de cisalhamento, Cw e J por elementos finitos; FLT pelo "
                          "Mcr geral com os limites dos perfis I; chapas classificadas automaticamente "
                          "(mesas em balanço com kc = 0,35). Confira a classificação das chapas no relatório")
        else:
            avisos.append(_pol(p) + ": a malha da seção falhou; flexo-torção e FLT sem empenamento "
                          "(a checar)")
    if p["tipo"] == "L" and N > 0:
        avisos.append("cantoneira tracionada com Ct = 1,0: se for ligada por uma aba só, Ct < 1 (5.2.5)")
    res["avisos"] = avisos
    res["taxa"] = max(res["taxas"].values())
    res["governa"] = max(res["taxas"], key=res["taxas"].get)
    return res


# ------------------------------------------------------------------ ligações (6.2 e 6.3)
# Perna mínima do filete pela menor espessura das partes soldadas (mm) — 6.2.6.2.1 e Tabela 11 da
# NBR 8800:2024 (conferida no texto da norma em 21/10/2026); filetes executados com um só passe
PERNA_MINIMA = ((6.3, 3.0), (12.5, 5.0), (19.0, 6.0), (1e9, 8.0))


def perna_minima(t_menor):
    for lim, dw in PERNA_MINIMA:
        if t_menor <= lim:
            return dw
    return 8.0


def perna_maxima(t_borda):
    """Tamanho máximo do filete ao longo da borda de uma peça de espessura t (6.2.6.2.2): a própria
    espessura abaixo de 6,3 mm; a espessura menos 1,5 mm a partir de 6,3 mm (salvo solda indicada nos
    desenhos como reforçada para obter a garganta total)."""
    return t_borda if t_borda < 6.3 else t_borda - 1.5


def comprimento_minimo_filete(dw):
    """Comprimento efetivo mínimo do filete (6.2.6.2.3): 4 vezes a perna e não menos que 40 mm."""
    return max(4.0 * dw, 40.0)


def solda_filete(dw, comprimento, fy, fu, t_base, eletrodo="E70XX"):
    """Força resistente (N) de um filete de perna dw e comprimento útil dado, ao cisalhamento.

    Metal da solda: 0,6·Aw·fw/γw2 com Aw = 0,707·dw·ℓ (garganta efetiva). Metal-base (na face de fusão,
    cisalhamento): menor de 0,60·fy·Ag/γa1 e 0,60·fu·Anv/γa2, com Ag = Anv = ℓ·t_base (a checar: a área do
    metal-base adotada é a da chapa mais fina ao longo do cordão). Retorna (FRd, texto)."""
    fw = FW_ELETRODO.get(eletrodo, 485.0)
    Aw = 0.707 * dw * comprimento
    Rw = 0.60 * Aw * fw / GAMA_W2
    Ab = comprimento * t_base
    Rb = min(0.60 * fy * Ab / GAMA_A1, 0.60 * fu * Ab / GAMA_A2)
    txt = "filete %.0f mm × %.0f mm (%s): solda %.1f kN, metal-base %.1f kN" % (
        dw, comprimento, eletrodo, Rw / 1000.0, Rb / 1000.0)
    if dw < perna_minima(t_base):
        txt += "; ATENÇÃO: perna abaixo da mínima de %.0f mm (Tabela 11)" % perna_minima(t_base)
    if dw > perna_maxima(t_base) + 1e-9:
        txt += "; ATENÇÃO: perna acima da máxima de %.1f mm ao longo da borda (6.2.6.2.2)" % perna_maxima(t_base)
    if comprimento < comprimento_minimo_filete(dw) - 1e-9:
        txt += "; ATENÇÃO: cordão mais curto que %.0f mm (6.2.6.2.3)" % comprimento_minimo_filete(dw)
    return min(Rw, Rb), txt


def parafuso(d, fub, rosca_no_plano=True, planos=1):
    """(Fv,Rd, Ft,Rd) em N de um parafuso de diâmetro d (mm) — 6.3.3.1 e 6.3.3.2.

    Cisalhamento: 0,45 (rosca no plano de corte, ou parafuso comum) ou 0,56 (alta resistência com a rosca
    fora do plano) × Ab·fub/γa2 por plano. Tração: Abe·fub/γa2 com Abe = 0,75·Ab (6.3.2.2)."""
    Ab = math.pi * d * d / 4.0
    cv = 0.45 if rosca_no_plano else 0.56
    return cv * Ab * fub / GAMA_A2 * planos, 0.75 * Ab * fub / GAMA_A2


def parafuso_interacao(Fv, Ft, FvRd, FtRd):
    """Tração e cisalhamento combinados (6.3.3.4): (Ft,Sd/Ft,Rd)² + (Fv,Sd/Fv,Rd)² ≤ 1,0."""
    return (Ft / FtRd) ** 2 + (Fv / FvRd) ** 2 if FtRd and FvRd else 0.0
