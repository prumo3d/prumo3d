# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verificação de barras de aço pela ABNT NBR 8800:2008 e combinações de ações (NBR 8681:2003).

Cada função devolve o esforço resistente de cálculo e um texto curto com o modo que governou, para
a memória de cálculo. Unidades: N, mm, MPa.

O que entra (com o item da norma no comentário) e o que fica de fora está em LIMITES e A_CHECAR,
reproduzidos na memória de cálculo. As fórmulas e os coeficientes foram conferidos na pesquisa
registrada em prumo-build/ferramentas/nbr8800_fontes.md (fontes públicas que transcrevem a norma).
"""

import math

E_ACO = 200000.0     # MPa — 4.5.2.9 (módulo de elasticidade do aço)
G_ACO = 77000.0      # MPa — 4.5.2.9 (módulo de elasticidade transversal)
GAMA_A1 = 1.10       # Tabela 3 — escoamento, flambagem e instabilidade (combinações normais)
GAMA_A2 = 1.35       # Tabela 3 — ruptura

EDICAO = ("ABNT NBR 8800:2008 e ABNT NBR 8681:2003 — edições substituídas pela NBR 8800:2024 e pela "
          "NBR 8681:2025: conferir com as edições vigentes antes de usar em projeto")

LIMITES = [
    "Análise elástica linear de 1ª ordem; efeitos de 2ª ordem (4.9) não calculados: a estrutura "
    "deve ser de pequena deslocabilidade ou os esforços devem ser amplificados (B1/B2) à parte.",
    "Comprimento de flambagem K·L com o K escolhido na análise (padrão 1,0, que a NBR 8800 admite para "
    "elementos contraventados, E.2.1.2; elemento isolado, como pilar em balanço, pede a Tabela E.1, ex.: "
    "K = 2,1), igual nos dois eixos e na torção; comprimento destravado da mesa comprimida (Lb) igual ao "
    "da barra (Cb pela 5.4.2.3, Rm = 1).",
    "Tração: seção líquida igual à bruta (Ae = Ag, Ct = 1,0): só vale para barras sem furos com a força "
    "entrando por todos os elementos da seção (5.2.4.2 e 5.2.5 a). Cantoneira ligada por uma aba só tem "
    "Ct < 1.",
    "Deslocamentos com a combinação rara (a favor da segurança); pelo C.2.4 o responsável técnico pode "
    "adotar a quase permanente ou a frequente conforme o efeito a evitar.",
    "Seções sem raios de concordância nos perfis U, I americanos, cantoneiras e tubos (o catálogo não "
    "traz); perfis W/HP com os raios. Constante de torção J pelas fórmulas de paredes finas (sem os "
    "raios), menor que a de catálogo (a favor da segurança na FLT).",
    "Torção das barras não verificada (só entra na rigidez).",
    "Cantoneiras simples: flambagem pelo eixo de menor inércia e flexo-torção, sem a esbeltez "
    "efetiva de cantoneira ligada por uma aba; flexão de cantoneiras pelo início do escoamento.",
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


# ------------------------------------------------------------------ flambagem local (Anexo F)
def fator_Q(p, fy):
    """Q = Qs·Qa (Anexo F) e um texto do que governou."""
    E = E_ACO
    t = p["tipo"]
    Qs = Qa = 1.0
    nota = []
    if t in ("I", "U"):
        bt = p["bt_mesa"]
        lim, lim2 = 0.56 * _raiz(E / fy), 1.03 * _raiz(E / fy)        # F.2 c) perfis laminados
        if bt > lim:
            Qs = 1.415 - 0.74 * bt * _raiz(fy / E) if bt <= lim2 else 0.69 * E / (fy * bt ** 2)
            nota.append("mesa esbelta (Qs = %.3f)" % Qs)
        ht = p["h_tw"]
        if ht > 1.49 * _raiz(E / fy):                                     # F.3 (AA, alma)
            Qa = _qa_aa(p, fy, p["h"], p["tw"], 0.34, [p["h"] * p["tw"]])
            nota.append("alma esbelta (Qa = %.3f)" % Qa)
    elif t == "L":
        bt = p["bt_aba"]
        lim, lim2 = 0.45 * _raiz(E / fy), 0.91 * _raiz(E / fy)        # F.2 a) cantoneiras
        if bt > lim:
            Qs = 1.340 - 0.76 * bt * _raiz(fy / E) if bt <= lim2 else 0.53 * E / (fy * bt ** 2)
            nota.append("aba esbelta (Qs = %.3f)" % Qs)
    elif t == "TQ":
        bt = p["bt_parede"]
        if bt > 1.40 * _raiz(E / fy):                                     # F.3, tubos retangulares
            Qa = _qa_aa(p, fy, p["h"], p["t"], 0.38, [p["h"] * p["t"]] * 4)
            nota.append("parede esbelta (Qa = %.3f)" % Qa)
    elif t == "TUBO":
        dt = p["D_t"]
        if dt > 0.11 * E / fy:                                            # F.4
            Qa = 0.038 * E / (fy * dt) + 2.0 / 3.0
            nota.append("parede esbelta (Q = %.3f)" % Qa)
            if dt > 0.45 * E / fy:
                nota.append("D/t acima de 0,45·E/fy: fora do escopo da norma")
    return Qs * Qa, "; ".join(nota)


def _qa_aa(p, fy, b, t, ca, elementos):
    """Qa pela largura efetiva (F.3.2), com σ = fy (a favor da segurança)."""
    E = E_ACO
    s = fy
    bef = 1.92 * t * _raiz(E / s) * (1 - ca / (b / t) * _raiz(E / s))
    bef = min(max(bef, 0.0), b)
    perda = sum((b - bef) * t for _ in elementos)
    return (p["A"] - perda) / p["A"]


# ------------------------------------------------------------------ compressão (5.3 e Anexo E)
def chi(l0):
    """Fator de redução (5.3.3)."""
    if l0 <= 1.5:
        return 0.658 ** (l0 ** 2)
    return 0.877 / l0 ** 2


def forca_ne(p, L, K=1.0, Kz=1.0):
    """Ne (Anexo E): menor entre flexão em x, em y e torção/flexo-torção. Retorna (Ne, modo)."""
    E, G = E_ACO, G_ACO
    Lx = Ly = K * L
    Lz = Kz * L
    t = p["tipo"]
    if t == "L":
        Nmin = math.pi ** 2 * E * p["I2"] / Lx ** 2
        modos = [(Nmin, "flexão (eixo de menor inércia)")]
    else:
        Nex = math.pi ** 2 * E * p["Ix"] / Lx ** 2
        Ney = math.pi ** 2 * E * p["Iy"] / Ly ** 2
        modos = [(Nex, "flexão em x"), (Ney, "flexão em y")]
    x0, y0 = p.get("x0", 0.0), p.get("y0", 0.0)
    r0q = p["rx"] ** 2 + p["ry"] ** 2 + x0 ** 2 + y0 ** 2
    Nez = (math.pi ** 2 * E * p.get("Cw", 0.0) / Lz ** 2 + G * p["J"]) / r0q
    if t in ("I", "TQ", "TUBO"):
        if t == "I":
            modos.append((Nez, "torção"))
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


def compressao(p, fy, L, K=1.0):
    """(Nc,Rd, texto). Inclui o limite de esbeltez KL/r ≤ 200 (5.3.4.1) como aviso."""
    Q, nota_q = fator_Q(p, fy)
    Ne, modo = forca_ne(p, L, K)
    l0 = _raiz(Q * p["A"] * fy / Ne)
    x = chi(l0)
    N = x * Q * p["A"] * fy / GAMA_A1
    rmin = p["rmin"] if p["tipo"] == "L" else min(p["rx"], p["ry"])
    esb = K * L / rmin
    txt = "%s; λ0 = %.2f; χ = %.3f; Q = %.3f" % (modo, l0, x, Q)
    if nota_q:
        txt += " (%s)" % nota_q
    if esb > 200:
        txt += "; ATENÇÃO: KL/r = %.0f > 200" % esb
    return N, txt


# ------------------------------------------------------------------ flexão (5.4.2 e Anexo G)
def _wef_tubo(p, fy):
    """Módulo efetivo do tubo retangular (Nota 4 da Tabela G.1): mesa comprimida com largura bef
    (F.3.2, σ = fy), desprezando o deslocamento da linha neutra (aproximação)."""
    E = E_ACO
    b, t, s = p["h"], p["t"], p["b"]
    bef = 1.92 * t * _raiz(E / fy) * (1 - 0.38 / (b / t) * _raiz(E / fy))
    bef = min(max(bef, 0.0), b)
    I_ef = p["Ix"] - (b - bef) * t * (s / 2.0 - t / 2.0) ** 2
    return I_ef / (s / 2.0)


def _interp(Mpl, Mr, lam, lp, lr, Mcr, Cb=1.0, com_cb=False):
    if lam <= lp:
        return Mpl
    if lam <= lr:
        m = Mpl - (Mpl - Mr) * (lam - lp) / (lr - lp)
        return min(Cb * m, Mpl) if com_cb else m
    return Mcr


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
        lr = 1.38 * _raiz(Iy * J) / (ry * J * b1) * _raiz(1 + _raiz(1 + 27 * Cw * b1 ** 2 / Iy))
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
            modos.append((fy * W, "alma esbelta (Anexo H não aplicado: a checar)"))
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
        lr_t = 2.00 * E * JA / Mr
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
    else:  # cantoneira: início do escoamento (simplificação a favor da segurança)
        modos = [(fy * W, "início do escoamento (cantoneira)")]
    M, modo = min(modos, key=lambda m: m[0])
    M = min(M, 1.5 * W * fy)
    return M / GAMA_A1, modo


def flexao_y(p, fy):
    """My,Rd: flexão em torno do eixo y (menor inércia nos perfis I e U)."""
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
    elif t in ("TQ", "TUBO"):
        return flexao_x(p, fy, 1.0)
    else:
        M, modo = fy * W, "início do escoamento (cantoneira)"
    M = min(M, 1.5 * W * fy)
    return M / GAMA_A1, modo


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
    """5.4.3.6: Vrd = 0,5 τcr Ag / γa1 (td = t: tubo sem costura; com costura, td = 0,93 t)."""
    E = E_ACO
    D_t = p["D_t"]
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
        return _vrd(p["d"] * p["tw"], fy, p["h_tw"], 5.0), "alma"
    if t == "TQ":
        return _vrd(2 * p["h"] * p["t"], fy, p["bt_parede"], 5.0), "paredes"
    if t == "TUBO":
        return _vrd_tubo(p, fy, Lv), "tubo circular (5.4.3.6)"
    return _vrd(p["b"] * p["t"], fy, p["bt_aba"], 1.2), "aba"


def cortante_y(p, fy, Lv=1e9):
    """Cortante na direção da largura (paralela às mesas nos perfis I e U)."""
    t = p["tipo"]
    if t == "I":
        return _vrd(2 * p["bf"] * p["tf"], fy, p["bt_mesa"], 1.2), "mesas"
    if t == "U":
        return _vrd(2 * p["bf"] * p["tf"], fy, p["bt_mesa"], 1.2), "mesas"
    return cortante_z(p, fy, Lv)


# ------------------------------------------------------------------ interação (5.5.1.2)
def interacao(N, NRd, Mx, MxRd, My, MyRd):
    r = abs(N) / NRd if NRd > 0 else 0.0
    m = (abs(Mx) / MxRd if MxRd > 0 else 0.0) + (abs(My) / MyRd if MyRd > 0 else 0.0)
    if r >= 0.2:
        return r + 8.0 / 9.0 * m, "N/NRd + 8/9 (Mx/MxRd + My/MyRd)"
    return r / 2.0 + m, "N/(2 NRd) + Mx/MxRd + My/MyRd"


def cb(m_max, ma, mb, mc):
    """Fator de modificação para diagrama de momento não uniforme (5.4.2.3), Rm = 1."""
    den = 2.5 * m_max + 3 * ma + 4 * mb + 3 * mc
    if den <= 0:
        return 1.0
    return min(12.5 * m_max / den, 3.0)


# ------------------------------------------------------------------ verificação de uma barra
def verificar(p, fy, fu, L, esf, K=1.0):
    """Taxas de uso (esforço solicitante / resistente) de uma barra num conjunto de esforços.

    esf: dict com N (tração +), Mx, My (máximos absolutos), Vz, Vy e os momentos nos quartos do
    vão para o Cb: Mq = (|M| a 1/4, 1/2, 3/4). Retorna dict com taxas e textos."""
    res = {}
    N = esf["N"]
    if N >= 0:
        NRd, modo_n = tracao(p, fy, fu)
    else:
        NRd, modo_n = compressao(p, fy, L, K)
    c = cb(abs(esf["Mx"]), *esf.get("Mq", (abs(esf["Mx"]),) * 3)) if esf["Mx"] else 1.0
    MxRd, modo_mx = flexao_x(p, fy, L, c)
    MyRd, modo_my = flexao_y(p, fy)
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
    res["taxa"] = max(res["taxas"].values())
    res["governa"] = max(res["taxas"], key=res["taxas"].get)
    return res
