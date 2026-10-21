# SPDX-License-Identifier: LGPL-2.1-or-later
"""Simulação de estruturas por barras: apoios, cargas, combinações (NBR 8681), esforços,
deslocamentos e verificação das barras pela NBR 8800.

O objeto "Análise" fica na árvore ligado à estrutura soldada: guarda apoios, casos de carga e
combinações, e recalcula sozinho quando a estrutura muda (é rápido: cálculo de barras, não de
sólidos). A vista desenha na tela os apoios, as cargas, a taxa de uso em cores, os diagramas de
esforços e a deformada.
"""

import json
import math

import FreeCAD

import PrumoUtil

# ------------------------------------------------------------------ apoios e cargas
APOIOS = {
    "Engaste": [1, 1, 1, 1, 1, 1],
    "Rótula": [1, 1, 1, 0, 0, 0],
    "Rolete (vertical)": [0, 0, 1, 0, 0, 0],
}
LIBERACOES = ["Rótula no início", "Rótula no fim", "Rótula nas duas pontas", "Barra de treliça",
              "Só tração (contraventamento)"]
TRELICAS = ("Barra de treliça", "Só tração (contraventamento)")

DIRECOES = {
    "Para baixo (−Z)": (0, 0, -1), "Para cima (+Z)": (0, 0, 1),
    "+X": (1, 0, 0), "−X": (-1, 0, 0), "+Y": (0, 1, 0), "−Y": (0, -1, 0),
}

# Tipos de caso de carga: (γ desfavorável, γ favorável, ψ0, ψ1, ψ2, grupo)
# Valores conferidos na NBR 8681:2025 (antes: NBR 8800:2008 Tabelas 1 e 2); fontes antigas em
# prumo-build/ferramentas/nbr8800_fontes.md
# γ (desfavorável, favorável) e ψ0, ψ1, ψ2 — ABNT NBR 8681:2025, combinações normais, ações permanentes
# consideradas separadamente
TIPOS_CASO = {
    "Peso próprio da estrutura de aço": (1.25, 1.00, None, None, None, "permanente"),
    "Permanente (equipamentos)": (1.25, 1.00, None, None, None, "permanente"),
    "Permanente (elementos industrializados)": (1.30, 1.00, None, None, None, "permanente"),
    "Permanente (elementos em geral)": (1.50, 1.00, None, None, None, "permanente"),
    "Sobrecarga (sem predominância de equipamentos)": (1.50, 0.0, 0.5, 0.4, 0.3, "variavel"),
    "Sobrecarga (com equipamentos ou pessoas)": (1.50, 0.0, 0.7, 0.6, 0.4, "variavel"),
    "Sobrecarga em cobertura, depósitos e oficinas": (1.50, 0.0, 0.8, 0.7, 0.6, "variavel"),
    "Vento": (1.40, 0.0, 0.6, 0.3, 0.0, "vento"),
    "Temperatura (variação atmosférica)": (1.20, 0.0, 0.6, 0.5, 0.3, "variavel"),
    # gerada por equipamentos: ψ das ações de uso; adotados os maiores (a favor da segurança)
    "Temperatura gerada por equipamentos": (1.50, 0.0, 0.8, 0.7, 0.6, "variavel"),
}
# nomes das versões anteriores (NBR 8681:2003) → atuais
TIPOS_ANTIGOS = {
    "Permanente (elementos em geral e equipamentos)": "Permanente (elementos em geral)",
    "Temperatura": "Temperatura (variação atmosférica)",
}


def tipo_atual(tipo):
    return TIPOS_ANTIGOS.get(tipo, tipo) if tipo not in TIPOS_CASO else tipo
TIPO_PESO = "Peso próprio da estrutura de aço"

LIMITES_FLECHA = {"Cobertura (L/250)": 250.0, "Piso (L/350)": 350.0}
LIMITE_PILAR = 300.0      # deslocamento horizontal relativo das pontas do pilar: H/300


def caso_padrao():
    return {"nome": "Peso próprio", "tipo": TIPO_PESO, "peso_proprio": True, "cargas": []}


def texto_mola(kh, kv):
    """'Mola:kx,ky,kz' (kN/mm) — horizontal igual em x e y."""
    return "Mola:%g,%g,%g" % (kh, kh, kv)


def rigidez_mola(tipo):
    try:
        kx, ky, kz = (float(v) for v in tipo.split(":", 1)[1].split(","))
        return kx, ky, kz
    except (ValueError, IndexError):
        return 0.0, 0.0, 0.0


def _chave_no(p):
    return "%.1f;%.1f;%.1f" % (p[0], p[1], p[2])


def _ponto_da_chave(k):
    return tuple(float(v) for v in k.split(";"))


# ------------------------------------------------------------------ combinações (NBR 8681)
def combinacoes(casos):
    """[(nome, tipo "ELU"/"ELS", [(índice do caso, fator)])] — combinações últimas normais e de
    serviço (rara e quase permanente) a partir dos tipos dos casos."""
    perm = [(k, c) for k, c in enumerate(casos) if TIPOS_CASO[c["tipo"]][5] == "permanente"]
    var = [(k, c) for k, c in enumerate(casos) if TIPOS_CASO[c["tipo"]][5] != "permanente"]
    ventos = [k for k, c in var if TIPOS_CASO[c["tipo"]][5] == "vento"]
    outros = [k for k, c in var if TIPOS_CASO[c["tipo"]][5] != "vento"]
    res = []

    def g(k, favoravel=False):
        t = TIPOS_CASO[casos[k]["tipo"]]
        return t[1] if favoravel else t[0]

    def nome_var(k):
        return casos[k]["nome"]

    # cada combinação usa no máximo um caso de vento (direções de vento não se somam)
    grupos_vento = [[]] + [[v] for v in ventos]
    n = 0
    for vs in grupos_vento:
        variaveis = outros + vs
        favs = [False, True] if vs else [False]       # vento: confere também permanentes favoráveis
        if not variaveis:
            n += 1
            res.append(("ELU %d: só permanentes" % n, "ELU", [(k, g(k)) for k, _c in perm]))
            continue
        for principal in variaveis:
            outras_k = [j for j in variaveis if j != principal]
            # com as secundárias (ψ0) e sem elas: variável favorável não entra (Tabela 1, nota a),
            # ex.: sobrecarga aliviando a sucção do vento
            for com_outras in ([True, False] if outras_k else [True]):
                for fav in favs:
                    fat = [(k, g(k, fav)) for k, _c in perm]
                    t = TIPOS_CASO[casos[principal]["tipo"]]
                    fat.append((principal, t[0]))
                    usadas = outras_k if com_outras else []
                    for j in usadas:
                        tj = TIPOS_CASO[casos[j]["tipo"]]
                        fat.append((j, tj[0] * tj[2]))
                    n += 1
                    res.append(("ELU %d: %s (principal)%s%s" % (
                        n, nome_var(principal), "".join(" + " + nome_var(o) for o in usadas),
                        ", permanentes favoráveis" if fav else ""), "ELU", fat))
    # serviço
    m = 0
    for vs in grupos_vento:
        variaveis = outros + vs
        if not variaveis:
            m += 1
            res.append(("ELS %d: rara, só permanentes" % m, "ELS", [(k, 1.0) for k, _c in perm]))
            continue
        for principal in variaveis:
            fat = [(k, 1.0) for k, _c in perm] + [(principal, 1.0)]
            for j in variaveis:
                if j != principal:
                    fat.append((j, TIPOS_CASO[casos[j]["tipo"]][3]))
            m += 1
            outras = [nome_var(j) for j in variaveis if j != principal]
            res.append(("ELS %d: rara, %s (principal)%s" % (m, nome_var(principal),
                                                            "".join(" + " + o for o in outras)), "ELS", fat))
    for v in ventos:
        # Tabela C.1: sucção nas terças — só a variável de sentido oposto, valor característico
        m += 1
        res.append(("ELS %d: %s sozinho (característico)" % (m, nome_var(v)), "ELS", [(v, 1.0)]))
    return res


# ------------------------------------------------------------------ modelo de cálculo
def montar_modelo(est, casos, apoios, liberacoes=None):
    """(Modelo, [Caso do PrumoPortico], mapa) a partir da estrutura e dos dados da análise.

    mapa: {"barras": {índice da linha: [(índice do elemento, x inicial mm)]}, "nos": {chave: nó}}."""
    import numpy as np
    import PrumoEstrutura as E
    import PrumoPortico as PT
    import PrumoSecao as S
    todas = E.arestas(est.Esqueleto)
    ativas = E.arestas_ativas(est, todas)
    normal = E._normal_esqueleto(todas)
    m = PT.Modelo()
    mapa = {"barras": {}, "nos": {}, "secoes": {}, "linhas": {}, "liberacoes": dict(liberacoes or {})}
    # pontos de nó: pontas de todas as barras
    pontas = []
    for i, e in enumerate(ativas):
        if e is None:
            continue
        if not E._reta(e):
            raise ValueError("a barra %d é curva: o cálculo por barras só aceita barras retas" % (i + 1))
        pontas += [e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)]
    for i, e in enumerate(ativas):
        if e is None:
            continue
        p0 = e.valueAt(e.FirstParameter)
        t = E._dir(e, True)
        L = e.Length
        # nós no meio da barra (ligações em T e apoios dados no meio)
        cortes = {0.0, L}
        for q in pontas:
            s = (q - p0).dot(t)
            if 1.0 < s < L - 1.0 and (p0 + t * s - q).Length < 1.0:
                cortes.add(round(s, 3))
        for k in apoios:
            q = FreeCAD.Vector(*_ponto_da_chave(k))
            s = (q - p0).dot(t)
            if 1.0 < s < L - 1.0 and (p0 + t * s - q).Length < 1.0:
                cortes.add(round(s, 3))
        par = E.parametros(est, i)
        sec_geo = E.Secao(est, ativas, i, normal)
        prop = S.propriedades(par["perfil"])
        # eixos principais (cantoneira): o y local é o eixo de maior inércia (ângulo theta a partir
        # de u, no sentido de v); z = t × y. Espelhar a seção inverte u, logo o sinal do ângulo.
        u, v = sec_geo.u, sec_geo.v
        if abs(prop.get("Ixy", 0.0)) > 1e-6 * prop["Ix"]:
            th = prop["theta"] * (-1.0 if par["espelhar"] else 1.0)
            v = v * math.cos(th) - u * math.sin(th)
            Iy_loc, Iz_loc = prop["I1"], prop["I2"]
        else:
            Iy_loc, Iz_loc = prop["Ix"], prop["Iy"]
        sec = PT.Secao(prop["A"], Iy_loc, Iz_loc, prop["J"], massa_kgm=prop["massa_kgm"], nome=par["perfil"])
        mapa["secoes"][i] = prop
        mapa["linhas"][i] = (p0, t, L)
        xs = sorted(cortes)
        # cada trecho em 4 elementos: diagramas mais finos e efeito P-δ na análise de 2ª ordem
        finos = []
        for a, b in zip(xs[:-1], xs[1:]):
            finos += [a + (b - a) * k / 4.0 for k in range(4)]
        xs = finos + [xs[-1]]
        mapa["barras"][i] = []
        lib = (liberacoes or {}).get(i, "")
        ini = lib in ("Rótula no início", "Rótula nas duas pontas") or lib in TRELICAS
        fim = lib in ("Rótula no fim", "Rótula nas duas pontas") or lib in TRELICAS
        for a, b in zip(xs[:-1], xs[1:]):
            ni = m.no(tuple(p0 + t * a))
            nj = m.no(tuple(p0 + t * b))
            solto = []
            if ini and a == xs[0]:
                solto += list(PT.ROTULA_I)
            if fim and b == xs[-1]:
                solto += list(PT.ROTULA_J)
                if lib in TRELICAS:
                    solto.append(9)          # torção solta numa ponta (senão a barra gira em torno do eixo)
            m.barras.append(PT.Barra(ni, nj, sec, (v.x, v.y, v.z), nome="%d" % (i + 1), origem=(i, a),
                                     liberados=solto, so_tracao=(lib == TRELICAS[1])))
            mapa["barras"][i].append((len(m.barras) - 1, a))
    for k, n in enumerate(m.nos):
        mapa["nos"][_chave_no(n)] = k
    # apoios
    for k, tipo in apoios.items():
        no = _no_mais_proximo(m, _ponto_da_chave(k))
        if no is not None and tipo.startswith("Mola"):
            kx, ky, kz = rigidez_mola(tipo)
            m.molas[no] = [kx * 1000.0, ky * 1000.0, kz * 1000.0, 0.0, 0.0, 0.0]   # kN/mm → N/mm
        elif no is not None and tipo in APOIOS:
            m.apoios[no] = list(APOIOS[tipo])
    # casos
    lista = []
    for c in casos:
        pc = PT.Caso(c["nome"], c["tipo"], c.get("peso_proprio", False))
        for carga in c.get("cargas", []):
            d = np.array(DIRECOES.get(carga.get("direcao", "Para baixo (−Z)"), (0, 0, -1)), dtype=float)
            val = float(carga.get("valor", 0.0))
            if carga["alvo"] == "barra":
                i = int(carga["linha"])
                if i not in mapa["barras"]:
                    continue
                if carga["tipo"] == "distribuida":
                    for eb, _a in mapa["barras"][i]:
                        pc.distribuidas.append((eb, list(d * val), True))
                elif carga["tipo"] == "trapezoidal":
                    # linear de "inicio" a "fim" (mm a partir do início da barra; fim 0 = até o fim)
                    Lb = mapa["linhas"][i][2]
                    a0 = max(0.0, float(carga.get("inicio", 0.0)))
                    b0 = float(carga.get("fim", 0.0)) or Lb
                    b0 = min(b0, Lb)
                    v2 = float(carga.get("valor2", val))
                    trechos = mapa["barras"][i]
                    for (eb, ea), prox in zip(trechos, trechos[1:] + [(None, Lb)]):
                        lo, hi = max(a0, ea), min(b0, prox[1])
                        if hi <= lo or b0 <= a0:
                            continue
                        q_lo = val + (v2 - val) * (lo - a0) / (b0 - a0)
                        q_hi = val + (v2 - val) * (hi - a0) / (b0 - a0)
                        pc.distribuidas.append((eb, list(d * q_lo), True, lo - ea, hi - ea, list(d * q_hi)))
                else:
                    pos = float(carga.get("posicao", 0.0))
                    trechos = mapa["barras"][i]
                    for (eb, a), prox in zip(trechos, trechos[1:] + [(None, mapa["linhas"][i][2])]):
                        if a <= pos <= prox[1]:
                            pc.pontuais.append((eb, pos - a, list(d * val), True))
                            break
            else:
                no = _no_mais_proximo(m, _ponto_da_chave(carga["no"]))
                if no is not None:
                    pc.nos.append((no, list(d * val), [0.0, 0.0, 0.0]))
        lista.append(pc)
    return m, lista, mapa


def _no_mais_proximo(m, p, tol=None):
    import numpy as np
    p = np.array(p, dtype=float)
    melhor, dmin = None, None
    for k, q in enumerate(m.nos):
        d = float(np.linalg.norm(q - p))
        if dmin is None or d < dmin:
            melhor, dmin = k, d
    if tol is not None and (dmin is None or dmin > tol):
        return None
    return melhor


# ------------------------------------------------------------------ cálculo completo
class Calculo:
    """Resultado de uma análise: por combinação, os esforços e as verificações de cada barra."""

    def __init__(self):
        self.modelo = None
        self.mapa = None
        self.combinacoes = []     # (nome, tipo, fatores)
        self.imperfeicoes = {}    # nome da combinação → (texto, Caso com as forças nocionais)
        self.rigidez = 1.0        # 0,8 quando a análise usou a rigidez reduzida
        self.resultados = {}      # nome → Resultado
        self.verificacao = {}     # linha → dict (pior combinação ELU)
        self.flechas = {}         # linha → (flecha mm, limite mm, razão, combinação)
        self.erro = None
        self.material = ("", 250.0, 400.0)
        self.amplificacao = 1.0
        self.avisos = []
        self.membros = {}
        self.modos = None         # [(f Hz, vetor)] quando calculados

    @property
    def taxa_maxima(self):
        vals = [v["taxa"] for v in self.verificacao.values()]
        vals += [f[2] for f in self.flechas.values()]
        return max(vals) if vals else 0.0


def frequencias(calc, casos, n=6):
    """Frequências naturais da estrutura (Hz): massa do peso próprio das barras e das cargas
    permanentes verticais (distribuídas nas barras e nos nós, convertidas em massa)."""
    import numpy as np
    import PrumoPortico as PT
    m = calc.modelo
    extra = {}
    g = 9806.65                               # mm/s²
    m.massas = {}
    for c in casos:
        if TIPOS_CASO.get(c["tipo"], (0, 0, 0, 0, 0, ""))[5] != "permanente":
            continue
        for carga in c.get("cargas", []):
            d = np.array(DIRECOES.get(carga.get("direcao", "Para baixo (−Z)"), (0, 0, -1)), dtype=float)
            if d[2] > -0.5:
                continue                      # só o que pesa (para baixo)
            val = abs(float(carga.get("valor", 0.0)))
            if carga["alvo"] == "barra":
                i = int(carga["linha"])
                if carga["tipo"] in ("distribuida", "trapezoidal"):
                    v2 = abs(float(carga.get("valor2", carga["valor"])))
                    for eb, _a in calc.mapa["barras"].get(i, []):
                        extra[eb] = extra.get(eb, 0.0) + (val + v2) / 2.0 / g      # N/mm → t/mm
                else:
                    pos = float(carga.get("posicao", 0.0))
                    no = None
                    for eb, a0 in calc.mapa["barras"][i]:
                        b = m.barras[eb]
                        Lb = float(np.linalg.norm(m.nos[b.j] - m.nos[b.i]))
                        if a0 - 1e-6 <= pos <= a0 + Lb + 1e-6:
                            no = b.i if pos - a0 <= Lb / 2.0 else b.j
                            break
                    if no is None:
                        no = m.barras[calc.mapa["barras"][i][-1][0]].j
                    m.massas[no] = m.massas.get(no, 0.0) + val * 1000.0 / g
            else:
                no = _no_mais_proximo(m, _ponto_da_chave(carga["no"]))
                if no is not None:
                    m.massas[no] = m.massas.get(no, 0.0) + val * 1000.0 / g
    calc.modos = m.modos(n, extra)
    return calc.modos


def membros(m, mapa):
    """Linhas colineares seguidas que só se encontram entre si (sem outra barra nem apoio no nó)
    formam um membro só (uma viga contínua desenhada em dois pedaços): o comprimento de flambagem
    e o destravado são os do membro. Retorna {linha: (lista de linhas do membro, comprimento,
    extremidade livre?)}."""
    import numpy as np
    grau = {}
    for b in m.barras:
        grau[b.i] = grau.get(b.i, 0) + 1
        grau[b.j] = grau.get(b.j, 0) + 1
    ponta = {}
    for i, (p0, t, L) in mapa["linhas"].items():
        for q in (p0, p0 + t * L):
            no = _no_mais_proximo(m, (q.x, q.y, q.z), 1.0)
            ponta.setdefault(no, []).append(i)
    pai = {i: i for i in mapa["linhas"]}

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i
    rotulados = set()
    for b in m.barras:
        if 4 in b.liberados or 5 in b.liberados:
            rotulados.add(b.i)
        if 10 in b.liberados or 11 in b.liberados:
            rotulados.add(b.j)
    for no, ls in ponta.items():
        if len(ls) == 2 and grau.get(no, 0) == 2 and no not in m.apoios and no not in rotulados:
            a, b = ls
            ta, tb = mapa["linhas"][a][1], mapa["linhas"][b][1]
            if abs(abs(ta.dot(tb)) - 1.0) < 1e-6:
                pai[raiz(a)] = raiz(b)
    grupos = {}
    for i in mapa["linhas"]:
        grupos.setdefault(raiz(i), []).append(i)
    res = {}
    for ls in grupos.values():
        Ltot = sum(mapa["linhas"][i][2] for i in ls)
        # extremidade livre: nó de ponta do membro com uma barra só e sem apoio
        livre = False
        for i in ls:
            p0, t, L = mapa["linhas"][i]
            for q in (p0, p0 + t * L):
                no = _no_mais_proximo(m, (q.x, q.y, q.z), 1.0)
                if grau.get(no, 0) == 1 and no not in m.apoios:
                    livre = True
        for i in ls:
            res[i] = (sorted(ls), Ltot, livre)
    return res


def _com_imperfeicoes(calc, m, casos, lista):
    """Combinações últimas sem vento ganham 4 variantes com forças nocionais (NBR 8800:2024, 4.10.7):
    0,3 % da carga gravitacional de cálculo de cada nó, horizontal, em +X, −X, +Y e −Y. Nas combinações
    com vento as forças nocionais não se somam (o vento já é a ação horizontal)."""
    import PrumoPortico as PT
    novas = []
    for nome, tipo, fatores in calc.combinacoes:
        com_vento = any(f and TIPOS_CASO[casos[k]["tipo"]][5] == "vento" for k, f in fatores)
        if tipo != "ELU" or com_vento:
            novas.append((nome, tipo, fatores))
            continue
        grav = m.cargas_gravitacionais([(lista[k], f) for k, f in fatores if f])
        if not grav.any():
            novas.append((nome, tipo, fatores))
            continue
        for eixo, sinal, rot in ((0, 1, "+X"), (0, -1, "−X"), (1, 1, "+Y"), (1, -1, "−Y")):
            c = PT.Caso("imperfeição %s" % rot, "imperfeicao")
            for no, g in enumerate(grav):
                if g > 0 and not (no in m.apoios and m.apoios[no][eixo]):
                    f = [0.0, 0.0, 0.0]
                    f[eixo] = sinal * 0.003 * g / 1000.0       # kN
                    c.nos.append((no, f, [0.0, 0.0, 0.0]))
            n2 = "%s + imperfeição %s" % (nome, rot)
            calc.imperfeicoes[n2] = ("forças nocionais 0,3 %% %s" % rot, c)
            novas.append((n2, tipo, fatores))
    return novas


def calcular(est, casos, apoios, fy=250.0, fu=400.0, nome_material="", limite_flecha=250.0, K=1.0,
             segunda_ordem=True, liberacoes=None):
    import PrumoNBR8800 as N
    calc = Calculo()
    calc.material = (nome_material, fy, fu)
    m, lista, mapa = montar_modelo(est, casos, apoios, liberacoes)
    calc.modelo, calc.mapa = m, mapa
    calc.combinacoes = combinacoes(casos)
    if not m.apoios and not any(any(k) for k in m.molas.values()):
        calc.erro = "a estrutura não tem apoios: clique nos nós para apoiar"
        return calc
    calc.combinacoes = _com_imperfeicoes(calc, m, casos, lista)
    try:
        partes_de = {}
        for nome, tipo, fatores in calc.combinacoes:
            partes = [(lista[k], f) for k, f in fatores if f]
            if nome in calc.imperfeicoes:
                partes.append((calc.imperfeicoes[nome][1], 1.0))
            partes_de[nome] = partes
            calc.resultados[nome] = m.resolver(partes, segunda_ordem=(segunda_ordem and tipo == "ELU"))
        if segunda_ordem:
            calc.amplificacao = max([r.amplificacao for n2, r in calc.resultados.items()
                                     if n2 in partes_de and dict((x[0], x[1]) for x in calc.combinacoes)[n2] == "ELU"]
                                    or [1.0])
        else:
            # 1ª ordem escolhida: a deslocabilidade é conferida mesmo assim (4.10.4), com uma 2ª ordem à parte
            amp = []
            for nome, tipo, _f in calc.combinacoes:
                if tipo == "ELU":
                    try:
                        amp.append(m.resolver(partes_de[nome], segunda_ordem=True).amplificacao)
                    except ValueError:
                        amp.append(float("inf"))
            calc.amplificacao = max(amp or [1.0])
        # 4.10.4 / 4.10.7 (NBR 8800:2024): média deslocabilidade → rigidez de 80 % nas combinações últimas
        if segunda_ordem and calc.amplificacao > 1.10:
            calc.rigidez = 0.8
            for nome, tipo, _f in calc.combinacoes:
                if tipo == "ELU":
                    calc.resultados[nome] = m.resolver(partes_de[nome], segunda_ordem=True, rigidez=0.8)
    except ValueError as ex:
        calc.erro = str(ex)
        calc.resultados = {}
        return calc
    if nome_material.startswith("ASTM A36 (padrão"):
        calc.avisos.append("Material não informado: verificado como ASTM A36 (fy 250 MPa, fu 400 MPa). "
                           "Confira o aço real das barras.")
    a = calc.amplificacao
    classe = ("pequena" if a <= 1.10 else "média" if a <= 1.40 else "grande")
    if not segunda_ordem:
        if a > 1.10:
            calc.avisos.append("ATENÇÃO: análise de 1ª ordem escolhida, mas a estrutura é de %s deslocabilidade "
                               "(razão %.2f > 1,10): a NBR 8800:2024 exige a análise de 2ª ordem. Ligue a 2ª "
                               "ordem; os resultados de 1ª ordem não valem para a verificação." % (classe, a))
        else:
            calc.avisos.append("Análise de 1ª ordem com forças nocionais de 0,3 %% (±X e ±Y); estrutura de pequena "
                               "deslocabilidade (razão entre deslocamentos horizontais de 2ª e 1ª ordem %.2f)." % a)
    if segunda_ordem:
        txt = ("Análise de 2ª ordem (P-Δ e P-δ) nas combinações últimas, com forças nocionais de 0,3 %% da "
               "carga gravitacional (±X e ±Y) nas combinações sem vento. Maior razão entre deslocamentos "
               "horizontais de 2ª e 1ª ordem, nó a nó: %.2f → %s deslocabilidade (NBR 8800:2024, 4.10.4; "
               "tomada nos nós, não andar a andar)" % (a, classe))
        if calc.rigidez < 1.0:
            txt += "; combinações últimas recalculadas com 80 % da rigidez (EI e EA)"
        calc.avisos.append(txt + ".")
        if a > 1.40:
            calc.avisos.append("GRANDE deslocabilidade (razão %.2f > 1,40): a NBR 8800:2024 pede análise "
                               "que considere as não linearidades geométrica e de material; o cálculo daqui "
                               "(elástico com 80 %% da rigidez) não basta. Enrijeça a estrutura (travamentos, "
                               "perfis) ou faça a análise avançada." % a)
    calc.membros = membros(m, mapa)
    # verificação por linha (barra do Prumo), pior combinação ELU
    for i, trechos in mapa["barras"].items():
        prop = mapa["secoes"][i]
        _ls, Lm, balanco = calc.membros[i]
        Kb = 1.0          # NBR 8800:2024: sem K; Ne com o comprimento destravado do membro
        pior = None
        elems_m = [eb for j in _ls for eb, _a in mapa["barras"][j]] if len(_ls) > 1 else None
        for nome, tipo, _f in calc.combinacoes:
            if tipo != "ELU":
                continue
            r = calc.resultados[nome]
            esf = _esforcos_da_linha(r, trechos, mapa["linhas"][i][2])
            if elems_m:
                esf["Mcb"] = _cb_do_membro(r, elems_m, m)
            # tração e compressão: verifica as duas se aparecerem
            for Nv in sorted({esf["Nmax"], esf["Nmin"]}):
                e2 = dict(esf, N=Nv)
                ver = N.verificar(prop, fy, fu, Lm, e2, balanco=balanco)
                ver["combinacao"] = nome
                ver["esforcos"] = e2
                ver["membro"] = (Lm, Kb, balanco)
                if pior is None or ver["taxa"] > pior["taxa"]:
                    pior = ver
        calc.verificacao[i] = pior
        for a in (pior or {}).get("avisos", []):
            txt = "Barra %d: %s" % (i + 1, a)
            if txt not in calc.avisos:
                calc.avisos.append(txt)
    # deslocamentos (ELS), por membro
    feitos = set()
    for i in mapa["barras"]:
        ls, Lm, balanco = calc.membros[i]
        if tuple(ls) in feitos:
            continue
        feitos.add(tuple(ls))
        t = mapa["linhas"][ls[0]][1]
        horizontal = abs(t.z) < 0.7
        if horizontal:
            # Tabela C.1: L é o vão; no balanço, 2 × o comprimento do balanço
            lim = (2 * Lm if balanco else Lm) / limite_flecha
        else:
            lim = Lm / LIMITE_PILAR
        elementos = [eb for j in ls for eb, _a in mapa["barras"][j]]
        maior = (0.0, None)
        for nome, tipo, _f in calc.combinacoes:
            if tipo != "ELS":
                continue
            r = calc.resultados[nome]
            if horizontal and not balanco:
                f = _flecha_do_membro(r, elementos, m)
            else:
                f = _ponta_do_membro(r, elementos, m, t)
            if f > maior[0]:
                maior = (f, nome)
        for j in ls:
            calc.flechas[j] = (maior[0], lim, maior[0] / lim if lim else 0.0, maior[1],
                               ("flecha do balanço" if balanco else "flecha") if horizontal
                               else "deslocamento horizontal")
    return calc


def _esforcos_da_linha(r, trechos, L):
    """Máximos da barra inteira (todos os trechos) e momentos nos quartos (para o Cb)."""
    Nmax = Nmin = 0.0
    Mx = My = Vz = Vy = 0.0
    amostras = []
    for eb, a in trechos:
        for x, e in r.diagrama(eb, 11):
            Nmax = max(Nmax, e["N"])
            Nmin = min(Nmin, e["N"])
            if abs(e["My"]) > abs(Mx):
                Mx = e["My"]
            if abs(e["Mz"]) > abs(My):
                My = e["Mz"]
            Vz = max(Vz, abs(e["Vz"]))
            Vy = max(Vy, abs(e["Vy"]))
            amostras.append((a + x, abs(e["My"])))

    def m_em(s):
        return min(amostras, key=lambda q: abs(q[0] - s))[1] if amostras else 0.0

    return {"Nmax": Nmax, "Nmin": Nmin, "N": Nmin, "Mx": Mx, "My": My, "Vz": Vz, "Vy": Vy,
            "Mq": (m_em(L / 4), m_em(L / 2), m_em(3 * L / 4))}


def _cb_do_membro(r, elementos, m):
    """(|M|máx, |M| a 1/4, 1/2, 3/4) ao longo de um membro de várias linhas."""
    import numpy as np
    am = []
    for eb in elementos:
        b = m.barras[eb]
        R, _L = r.geo[eb]
        for x, e in r.diagrama(eb, 11):
            am.append((m.nos[b.i] + R[0] * x, abs(e["My"])))
    pos = np.array([p for p, _v in am])
    e = pos[-1] - pos[0]
    n = np.linalg.norm(e)
    if n < 1e-9:
        return None
    s = (pos - pos[0]) @ (e / n)
    s0, s1 = float(s.min()), float(s.max())
    Lm = s1 - s0

    def em(f):
        k = int(np.argmin(np.abs(s - (s0 + f * Lm))))
        return am[k][1]
    return (max(v for _p, v in am), em(0.25), em(0.5), em(0.75))


def _pontos_deslocados(r, elementos, m, n=9):
    """[(posição original, deslocamento total)] ao longo dos elementos (vetores numpy, mm)."""
    import numpy as np
    import PrumoPortico as PT
    res = []
    for eb in elementos:
        b = m.barras[eb]
        R, L = r.geo[eb]
        ui, uj = r.u[6 * b.i:6 * b.i + 3], r.u[6 * b.j:6 * b.j + 3]
        for k in range(n):
            x = L * k / (n - 1)
            xi = x / L
            v, w = PT._deslocamento_no_vao(r, eb, x)
            d = ui + (uj - ui) * xi + R.T @ np.array([0.0, v, w])
            res.append((m.nos[b.i] + R[0] * x, d))
    return res


def _flecha_do_membro(r, elementos, m):
    """Maior deslocamento transversal em relação à reta que liga os deslocamentos das pontas do
    membro (soma a corda de cada trecho com a flecha dentro dele)."""
    import numpy as np
    pts = _pontos_deslocados(r, elementos, m)
    pos = np.array([p for p, _d in pts])
    eixo = pos[-1] - pos[0]
    # pontas do membro: os dois pontos mais afastados ao longo do eixo
    if np.linalg.norm(eixo) < 1e-9:
        return 0.0
    e = eixo / np.linalg.norm(eixo)
    proj = pos @ e
    a, b = int(np.argmin(proj)), int(np.argmax(proj))
    pa, pb = proj[a], proj[b]
    da, db = pts[a][1], pts[b][1]
    maior = 0.0
    for (p, d), s in zip(pts, proj):
        f = (s - pa) / (pb - pa) if pb > pa else 0.0
        rel = d - (da + (db - da) * f)
        rel = rel - e * float(rel @ e)
        maior = max(maior, float(np.linalg.norm(rel)))
    return maior


def _ponta_do_membro(r, elementos, m, t):
    """Balanço ou pilar: deslocamento transversal de uma ponta em relação à outra (o maior)."""
    import numpy as np
    pts = _pontos_deslocados(r, elementos, m)
    tv = np.array([t.x, t.y, t.z])
    proj = [float(p @ tv) for p, _d in pts]
    a, b = int(np.argmin(proj)), int(np.argmax(proj))
    maior = 0.0
    for k in range(len(pts)):
        for ref in (a, b):
            d = pts[k][1] - pts[ref][1]
            d = d - tv * float(d @ tv)
            maior = max(maior, float(np.linalg.norm(d)))
    return maior


# ------------------------------------------------------------------ objeto na árvore
class Analise:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)
        self.calc = None

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyLink", "Estrutura", "Análise", "Estrutura soldada calculada")
        add("App::PropertyLinkListHidden", "Barras", "Análise", "Barras da estrutura (para recalcular quando mudam)")
        add("App::PropertyString", "Material", "Análise", "Material do aço (vazio = o da estrutura)", "")
        add("App::PropertyStringList", "Apoios", "Análise", "Apoios: 'x;y;z=Tipo' (mm)", [])
        add("App::PropertyStringList", "Liberacoes", "Análise", "Rótulas nas pontas das barras: 'linha=Tipo' "
            "(linha a partir de 0)", [])
        add("App::PropertyStringList", "Casos", "Análise", "Casos de carga (JSON)",
            [json.dumps(caso_padrao(), ensure_ascii=False)])
        if "LimiteFlecha" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "LimiteFlecha", "Análise", "Limite de flecha das vigas")
            obj.LimiteFlecha = list(LIMITES_FLECHA)
        if "Mostrar" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Mostrar", "Vista", "O que desenhar na tela")
            obj.Mostrar = MOSTRAR
        elif list(obj.getEnumerationsOfProperty("Mostrar") or []) != MOSTRAR:
            atual = obj.Mostrar
            obj.Mostrar = MOSTRAR
            if atual in MOSTRAR:
                obj.Mostrar = atual
        add("App::PropertyString", "Combinacao", "Vista", "Combinação mostrada (vazio = a pior ELU)", "")
        add("App::PropertyFloat", "Escala", "Vista", "Escala dos diagramas e da deformada (1 = automática)", 1.0)
        add("App::PropertyInteger", "Modo", "Vista", "Modo de vibrar desenhado (1 = o de menor frequência)", 1)
        add("App::PropertyBool", "SegundaOrdem", "Análise", "Análise de 2ª ordem (P-Δ) nas combinações últimas",
            True)
        add("App::PropertyFloat", "K", "Análise", "Não usado desde a NBR 8800:2024 (sem coeficiente K: a "
            "estabilidade global fica com a análise de 2ª ordem com imperfeições)", 1.0)
        try:
            obj.setEditorMode("K", 2)
        except Exception:
            pass
        add("App::PropertyFloat", "TaxaMaxima", "Resultados", "Maior taxa de uso (1,00 = no limite)", 0.0, True)
        add("App::PropertyString", "BarraCritica", "Resultados", "Barra com a maior taxa", "", True)
        add("App::PropertyFloat", "DeslocamentoMax", "Resultados", "Maior deslocamento (mm, ELS)", 0.0, True)
        add("App::PropertyString", "Situacao", "Resultados", "Atende / não atende / erro", "", True)
        add("App::PropertyStringList", "Resumo", "Resultados", "Resumo por barra", [], True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)
        self.calc = None

    def casos(self, obj):
        res = []
        for linha in obj.Casos:
            try:
                c = json.loads(linha)
            except ValueError:
                continue
            c["tipo"] = tipo_atual(c.get("tipo", ""))
            if c["tipo"] not in TIPOS_CASO:
                c["tipo"] = "Permanente (elementos em geral)"
            res.append(c)
        return res or [caso_padrao()]

    def liberacoes(self, obj):
        """{linha: tipo de liberação} (rótulas nas pontas e barras de treliça)."""
        res = {}
        for linha in getattr(obj, "Liberacoes", []) or []:
            k, _s, tipo = linha.partition("=")
            if tipo in LIBERACOES:
                try:
                    res[int(k)] = tipo
                except ValueError:
                    pass
        return res

    def apoios(self, obj):
        res = {}
        for linha in obj.Apoios:
            k, _s, tipo = linha.partition("=")
            if tipo in APOIOS or tipo.startswith("Mola:"):
                res[k.strip()] = tipo
        return res

    def material(self, obj):
        """(nome, fy, fu) do material: o da análise, o da estrutura, ou ASTM A36."""
        import PrumoFEM
        nome = (obj.Material or getattr(obj.Estrutura, "Material", "") or "").strip()
        for d in PrumoFEM.materiais():
            if nome and (d["nome"] == nome or nome.lower() in d["nome"].lower()):
                p = PrumoFEM.props_mat(d["props"])
                if p.get("Sy") and p.get("Su"):
                    return d["nome"], float(p["Sy"]), float(p["Su"])
        return "ASTM A36 (padrão: material não informado)", 250.0, 400.0

    def calcular_silencioso(self, obj):
        """Recalcula só o resultado em memória (para desenhar), sem mudar propriedades."""
        import PrumoEstrutura as E
        est = obj.Estrutura
        if not E.eh_estrutura(est):
            return None
        nome, fy, fu = self.material(obj)
        try:
            self.calc = calcular(est, self.casos(obj), self.apoios(obj), fy, fu, nome,
                                 LIMITES_FLECHA.get(obj.LimiteFlecha, 250.0), obj.K or 1.0,
                                 bool(getattr(obj, "SegundaOrdem", True)), self.liberacoes(obj))
        except Exception:
            self.calc = None
        return self.calc

    def execute(self, obj):
        import PrumoEstrutura as E
        est = obj.Estrutura
        self.calc = None
        if not E.eh_estrutura(est):
            obj.Situacao = "escolha a estrutura"
            return
        bs = E.barras_de(est)
        if list(obj.Barras) != bs:
            obj.Barras = bs
        nome, fy, fu = self.material(obj)
        try:
            calc = calcular(est, self.casos(obj), self.apoios(obj), fy, fu, nome,
                            LIMITES_FLECHA.get(obj.LimiteFlecha, 250.0), obj.K or 1.0,
                                 bool(getattr(obj, "SegundaOrdem", True)), self.liberacoes(obj))
        except Exception as ex:
            obj.Situacao = "erro: %s" % ex
            obj.TaxaMaxima = 0.0
            obj.Resumo = []
            return
        self.calc = calc
        if calc.erro:      # o modelo existe (nós para clicar), mas sem resultado
            obj.Situacao = "erro: %s" % calc.erro
            obj.TaxaMaxima = 0.0
            obj.BarraCritica = ""
            obj.Resumo = []
            return
        tx = calc.taxa_maxima
        obj.TaxaMaxima = round(tx, 4)
        piores = sorted(calc.verificacao.items(), key=lambda kv: -kv[1]["taxa"])
        if piores:
            i, v = piores[0]
            obj.BarraCritica = "Barra %d (%s): %s" % (i + 1, calc.mapa["secoes"][i]["nome"], v["governa"])
        obj.DeslocamentoMax = round(max([f[0] for f in calc.flechas.values()] or [0.0]), 3)
        obj.Situacao = "atende" if tx <= 1.0 else "não atende"
        obj.Resumo = ["Barra %d: %s — taxa %.2f (%s, %s)" % (i + 1, calc.mapa["secoes"][i]["nome"], v["taxa"],
                                                              v["governa"], v["combinacao"])
                      for i, v in piores] + ["Aviso: " + a for a in calc.avisos]

    def dumps(self):
        return None

    def loads(self, state):
        self.calc = None


DEFORMADA_TAXA = "Deformada com a taxa de uso"
MODO_VIBRAR = "Modo de vibrar"
MOSTRAR = ["Taxa de uso", "Momento fletor (M)", "Esforço cortante (V)", "Esforço normal (N)", "Deformada",
           DEFORMADA_TAXA, MODO_VIBRAR, "Cargas e apoios"]


def criar(doc, est):
    o = doc.addObject("App::FeaturePython", "Analise")
    Analise(o)
    o.Label = "Análise de %s" % est.Label
    o.Estrutura = est
    if FreeCAD.GuiUp:
        import PrumoAnaliseVista
        PrumoAnaliseVista.VPAnalise(o.ViewObject)
    doc.recompute()
    return o


def analise_de(est):
    for o in est.InList:
        if "Apoios" in o.PropertiesList and "Casos" in o.PropertiesList:
            return o
    return None
