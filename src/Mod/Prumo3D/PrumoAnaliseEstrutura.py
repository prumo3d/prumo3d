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
DIRECOES = {
    "Para baixo (−Z)": (0, 0, -1), "Para cima (+Z)": (0, 0, 1),
    "+X": (1, 0, 0), "−X": (-1, 0, 0), "+Y": (0, 1, 0), "−Y": (0, -1, 0),
}

# Tipos de caso de carga: (γ desfavorável, γ favorável, ψ0, ψ1, ψ2, grupo)
# Valores da NBR 8800:2008 Tabelas 1 e 2 (que adotam a NBR 8681:2003); fontes em
# prumo-build/ferramentas/nbr8800_fontes.md
TIPOS_CASO = {
    "Peso próprio da estrutura de aço": (1.25, 1.00, None, None, None, "permanente"),
    "Permanente (elementos industrializados)": (1.35, 1.00, None, None, None, "permanente"),
    "Permanente (elementos em geral e equipamentos)": (1.50, 1.00, None, None, None, "permanente"),
    "Sobrecarga (sem predominância de equipamentos)": (1.50, 0.0, 0.5, 0.4, 0.3, "variavel"),
    "Sobrecarga (com equipamentos ou pessoas)": (1.50, 0.0, 0.7, 0.6, 0.4, "variavel"),
    "Vento": (1.40, 0.0, 0.6, 0.3, 0.0, "vento"),
    "Temperatura": (1.20, 0.0, 0.6, 0.5, 0.3, "variavel"),
}
TIPO_PESO = "Peso próprio da estrutura de aço"

LIMITES_FLECHA = {"Cobertura (L/250)": 250.0, "Piso (L/350)": 350.0}
LIMITE_PILAR = 300.0      # deslocamento horizontal relativo das pontas do pilar: H/300


def caso_padrao():
    return {"nome": "Peso próprio", "tipo": TIPO_PESO, "peso_proprio": True, "cargas": []}


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
            for fav in favs:
                fat = [(k, g(k, fav)) for k, _c in perm]
                t = TIPOS_CASO[casos[principal]["tipo"]]
                fat.append((principal, t[0]))
                for j in variaveis:
                    if j != principal:
                        tj = TIPOS_CASO[casos[j]["tipo"]]
                        fat.append((j, tj[0] * tj[2]))
                n += 1
                outras = [nome_var(j) for j in variaveis if j != principal]
                res.append(("ELU %d: %s (principal)%s%s" % (
                    n, nome_var(principal), "".join(" + " + o for o in outras),
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
    return res


# ------------------------------------------------------------------ modelo de cálculo
def montar_modelo(est, casos, apoios):
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
    mapa = {"barras": {}, "nos": {}, "secoes": {}, "linhas": {}}
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
        # eixos principais (cantoneira): gira u, v pelo ângulo principal
        u, v = sec_geo.u, sec_geo.v
        if abs(prop.get("Ixy", 0.0)) > 1e-6 * prop["Ix"]:
            th = 0.5 * math.atan2(-2 * prop["Ixy"], prop["Ix"] - prop["Iy"])
            v = v * math.cos(th) + u * math.sin(th)
            Iy_loc, Iz_loc = prop["I1"], prop["I2"]
            if prop["Ix"] < prop["Iy"]:
                Iy_loc, Iz_loc = prop["I2"], prop["I1"]
        else:
            Iy_loc, Iz_loc = prop["Ix"], prop["Iy"]
        sec = PT.Secao(prop["A"], Iy_loc, Iz_loc, prop["J"], massa_kgm=prop["massa_kgm"], nome=par["perfil"])
        mapa["secoes"][i] = prop
        mapa["linhas"][i] = (p0, t, L)
        xs = sorted(cortes)
        mapa["barras"][i] = []
        for a, b in zip(xs[:-1], xs[1:]):
            ni = m.no(tuple(p0 + t * a))
            nj = m.no(tuple(p0 + t * b))
            m.barras.append(PT.Barra(ni, nj, sec, (v.x, v.y, v.z), nome="%d" % (i + 1), origem=(i, a)))
            mapa["barras"][i].append((len(m.barras) - 1, a))
    for k, n in enumerate(m.nos):
        mapa["nos"][_chave_no(n)] = k
    # apoios
    for k, tipo in apoios.items():
        no = _no_mais_proximo(m, _ponto_da_chave(k))
        if no is not None and tipo in APOIOS:
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
        self.resultados = {}      # nome → Resultado
        self.verificacao = {}     # linha → dict (pior combinação ELU)
        self.flechas = {}         # linha → (flecha mm, limite mm, razão, combinação)
        self.erro = None
        self.material = ("", 250.0, 400.0)

    @property
    def taxa_maxima(self):
        vals = [v["taxa"] for v in self.verificacao.values()]
        vals += [f[2] for f in self.flechas.values()]
        return max(vals) if vals else 0.0


def calcular(est, casos, apoios, fy=250.0, fu=400.0, nome_material="", limite_flecha=250.0, K=1.0):
    import PrumoNBR8800 as N
    calc = Calculo()
    calc.material = (nome_material, fy, fu)
    m, lista, mapa = montar_modelo(est, casos, apoios)
    calc.modelo, calc.mapa = m, mapa
    calc.combinacoes = combinacoes(casos)
    if not m.apoios:
        calc.erro = "a estrutura não tem apoios: clique nos nós para apoiar"
        return calc
    try:
        for nome, tipo, fatores in calc.combinacoes:
            partes = [(lista[k], f) for k, f in fatores if f]
            calc.resultados[nome] = m.resolver(partes)
    except ValueError as ex:
        calc.erro = str(ex)
        calc.resultados = {}
        return calc
    # verificação por linha (barra do Prumo), pior combinação ELU
    for i, trechos in mapa["barras"].items():
        prop = mapa["secoes"][i]
        L = mapa["linhas"][i][2]
        pior = None
        for nome, tipo, _f in calc.combinacoes:
            if tipo != "ELU":
                continue
            r = calc.resultados[nome]
            esf = _esforcos_da_linha(r, trechos, L)
            # tração e compressão: verifica as duas se aparecerem
            for Nv in sorted({esf["Nmax"], esf["Nmin"]}):
                e2 = dict(esf, N=Nv)
                ver = N.verificar(prop, fy, fu, L, e2, K)
                ver["combinacao"] = nome
                ver["esforcos"] = e2
                if pior is None or ver["taxa"] > pior["taxa"]:
                    pior = ver
        calc.verificacao[i] = pior
        # deslocamentos (ELS)
        p0, t, L = mapa["linhas"][i]
        horizontal = abs(t.z) < 0.7
        lim = L / (limite_flecha if horizontal else LIMITE_PILAR)
        maior = (0.0, None)
        for nome, tipo, _f in calc.combinacoes:
            if tipo != "ELS":
                continue
            r = calc.resultados[nome]
            if horizontal:
                f = _flecha_da_linha(r, trechos, m)
            else:
                f = _deriva_do_pilar(r, trechos, m, t)
            if f > maior[0]:
                maior = (f, nome)
        calc.flechas[i] = (maior[0], lim, maior[0] / lim if lim else 0.0, maior[1],
                           "flecha" if horizontal else "deslocamento horizontal")
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


def _flecha_da_linha(r, trechos, m):
    """Flecha da barra inteira em relação à reta entre as pontas (mm)."""
    import numpy as np
    # deslocamentos dos nós da barra inteira em relação à corda + flecha interna de cada trecho
    nos = [m.barras[eb].i for eb, _a in trechos] + [m.barras[trechos[-1][0]].j]
    u0, u1 = r.u[6 * nos[0]:6 * nos[0] + 3], r.u[6 * nos[-1]:6 * nos[-1] + 3]
    p0, p1 = m.nos[nos[0]], m.nos[nos[-1]]
    Lt = float(np.linalg.norm(p1 - p0))
    maior = 0.0
    for k, n in enumerate(nos):
        s = float(np.linalg.norm(m.nos[n] - p0)) / Lt if Lt else 0.0
        rel = r.u[6 * n:6 * n + 3] - (u0 + (u1 - u0) * s)
        eixo = (p1 - p0) / Lt
        rel = rel - eixo * float(np.dot(rel, eixo))
        maior = max(maior, float(np.linalg.norm(rel)))
    for eb, _a in trechos:
        fy_, fz_ = r.flecha_local(eb)
        maior = max(maior, math.hypot(fy_, fz_))
    return maior


def _deriva_do_pilar(r, trechos, m, t):
    import numpy as np
    n0 = m.barras[trechos[0][0]].i
    n1 = m.barras[trechos[-1][0]].j
    d = r.u[6 * n1:6 * n1 + 3] - r.u[6 * n0:6 * n0 + 3]
    tv = np.array([t.x, t.y, t.z])
    d = d - tv * float(np.dot(d, tv))
    return float(np.linalg.norm(d))


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
        add("App::PropertyStringList", "Casos", "Análise", "Casos de carga (JSON)",
            [json.dumps(caso_padrao(), ensure_ascii=False)])
        if "LimiteFlecha" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "LimiteFlecha", "Análise", "Limite de flecha das vigas")
            obj.LimiteFlecha = list(LIMITES_FLECHA)
        if "Mostrar" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Mostrar", "Vista", "O que desenhar na tela")
            obj.Mostrar = MOSTRAR
        add("App::PropertyString", "Combinacao", "Vista", "Combinação mostrada (vazio = a pior ELU)", "")
        add("App::PropertyFloat", "Escala", "Vista", "Escala dos diagramas e da deformada (1 = automática)", 1.0)
        add("App::PropertyFloat", "K", "Análise", "Coeficiente de flambagem K (1,0 para barras contraventadas; "
            "pilar em balanço: 2,1 pela Tabela E.1)", 1.0)
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
                res.append(json.loads(linha))
            except ValueError:
                continue
        return res or [caso_padrao()]

    def apoios(self, obj):
        res = {}
        for linha in obj.Apoios:
            k, _s, tipo = linha.partition("=")
            if tipo in APOIOS:
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
                                 LIMITES_FLECHA.get(obj.LimiteFlecha, 250.0), obj.K or 1.0)
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
                            LIMITES_FLECHA.get(obj.LimiteFlecha, 250.0), obj.K or 1.0)
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
                      for i, v in piores]

    def dumps(self):
        return None

    def loads(self, state):
        self.calc = None


MOSTRAR = ["Taxa de uso", "Momento fletor (M)", "Esforço cortante (V)", "Esforço normal (N)", "Deformada",
           "Cargas e apoios"]


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
