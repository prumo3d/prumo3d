# SPDX-License-Identifier: LGPL-2.1-or-later
"""Esboço 3D: linhas por pontos X, Y, Z no espaço, com trechos (ramificações) e curvas nos cantos.

O Sketcher do FreeCAD só desenha num plano. Para caminho de tubo, esqueleto de estrutura espacial ou
trajetória de varredura, o Esboço 3D liga pontos digitados (absolutos ou relativos ao anterior) ou
clicados no modelo (encaixa em vértices e pontas de arestas).

- Pontos: lista de pontos (coordenadas do objeto; a Posição move tudo junto).
- Quebras: índices dos pontos que começam um trecho novo (ramal); o primeiro ponto de um ramal costuma
  ser clicado sobre um ponto já existente.
- Fechado: liga o último ponto ao primeiro (só com um trecho).
- RaioCurva: arredonda os cantos com arcos tangentes (curva de tubo); 0 = cantos vivos.

Serve direto como esqueleto da Estrutura soldada e como trajetória da Varredura do Part.
"""
import math

import FreeCAD

TOL = 1e-6


# ======================================================================== geometria
def trechos(pontos, quebras=()):
    """Divide a lista de pontos nos trechos: [[p0, p1, ...], ...] (pontos repetidos seguidos saem)."""
    pts = [FreeCAD.Vector(p) for p in pontos]
    cortes = sorted({int(i) for i in quebras if 0 < int(i) < len(pts)})
    res = []
    ini = 0
    for c in cortes + [len(pts)]:
        t = []
        for p in pts[ini:c]:
            if not t or (p - t[-1]).Length > TOL:
                t.append(p)
        if t:
            res.append(t)
        ini = c
    return res


def _canto(a, p, b, r):
    """Arco tangente de raio r no canto p (entre a e b): (t1, meio, t2) ou None (alinhado/não cabe)."""
    u1 = a - p
    u2 = b - p
    l1, l2 = u1.Length, u2.Length
    if l1 < TOL or l2 < TOL:
        return None
    u1 = u1 * (1.0 / l1)
    u2 = u2 * (1.0 / l2)
    cos = max(-1.0, min(1.0, u1.dot(u2)))
    teta = math.acos(cos)                    # ângulo interno do canto
    if teta < 1e-6 or math.pi - teta < 1e-6:
        return None                          # volta sobre si ou reto: sem arco
    t = r / math.tan(teta / 2.0)
    if t > l1 + TOL or t > l2 + TOL:
        return None
    w = u1 + u2
    w = w * (1.0 / w.Length)
    centro = p + w * (r / math.sin(teta / 2.0))
    t1 = p + u1 * t
    t2 = p + u2 * t
    meio = centro - w * r
    return t1, meio, t2


def arestas_do_trecho(pts, fechado=False, raio=0.0):
    """Arestas (Part) de um trecho; com raio > 0, os cantos viram arcos tangentes."""
    import Part
    n = len(pts)
    if n < 2:
        return []
    fechar = fechado and n >= 3
    if fechar and (pts[0] - pts[-1]).Length < TOL:
        pts = pts[:-1]
        n = len(pts)
    cantos = {}
    if raio > TOL:
        idx = range(n) if fechar else range(1, n - 1)
        # o raio não pode passar da metade dos trechos vizinhos (dois cantos dividem o mesmo segmento)
        for i in idx:
            a, p, b = pts[i - 1], pts[i], pts[(i + 1) % n]
            c = _canto(p + (a - p) * 0.5, p, p + (b - p) * 0.5, raio)
            if c is not None:
                cantos[i] = c
    ed = []
    segs = list(range(n if fechar else n - 1))
    for i in segs:
        j = (i + 1) % n
        ini = cantos[i][2] if i in cantos else pts[i]
        fim = cantos[j][0] if j in cantos else pts[j]
        if (fim - ini).Length > TOL:
            ed.append(Part.LineSegment(ini, fim).toShape())
        if j in cantos and (j != 0 or fechar):
            t1, meio, t2 = cantos[j]
            ed.append(Part.Arc(t1, meio, t2).toShape())
    return ed


def segmentos(pontos, quebras=(), fechado=False):
    """Segmentos do esboço como pares de índices de pontos [(i, j)], na ordem: o segmento k liga dois
    pontos seguidos do mesmo trecho (as restrições e a construção usam esse k)."""
    n = len(pontos)
    cortes = sorted({int(i) for i in quebras if 0 < int(i) < n})
    res = []
    ini = 0
    for c in cortes + [n]:
        for i in range(ini, c - 1):
            res.append((i, i + 1))
        ini = c
    if fechado and not cortes and n >= 3:
        res.append((n - 1, 0))
    return res


def forma(pontos, quebras=(), fechado=False, raio=0.0, construcao=()):
    """Forma do esboço: um fio por sequência de segmentos normais (Compound se houver mais de um).
    Os segmentos de construção ficam de fora (são só referência: aparecem tracejados na tela)."""
    import Part
    pts = [FreeCAD.Vector(p) for p in pontos]
    segs = segmentos(pts, quebras, fechado)
    constr = {int(k) for k in construcao}
    if not constr:
        ts = trechos(pts, quebras)
        fios = []
        for t in ts:
            ed = arestas_do_trecho(t, fechado and len(ts) == 1, raio)
            if ed:
                try:
                    fios.append(Part.Wire(ed))
                except Exception:
                    fios.append(Part.Compound(ed))
    else:
        # sequências de segmentos normais seguidos viram polilinhas
        corridas = []
        atual = []
        for k, (i, j) in enumerate(segs):
            if k in constr or (pts[j] - pts[i]).Length < TOL:
                if atual:
                    corridas.append(atual)
                atual = []
                continue
            if atual and atual[-1] != i:
                corridas.append(atual)
                atual = []
            if not atual:
                atual = [i]
            atual.append(j)
        if atual:
            corridas.append(atual)
        fios = []
        for c in corridas:
            fechar = len(c) > 3 and c[0] == c[-1]
            cp = [pts[i] for i in (c[:-1] if fechar else c)]
            ed = arestas_do_trecho(cp, fechar, raio)
            if ed:
                try:
                    fios.append(Part.Wire(ed))
                except Exception:
                    fios.append(Part.Compound(ed))
    if not fios:
        return Part.Shape()
    if len(fios) == 1:
        return fios[0]
    return Part.Compound(fios)


# ------------------------------------------------------------------------ restrições
# Texto de cada restrição (propriedade Restricoes): "tipo:arg1:arg2...". Segmentos pelo índice k de
# segmentos(); pontos pelo índice na lista de pontos.
#   eixo:k:X|Y|Z          segmento ao longo do eixo (como "Ao longo de X" do SolidWorks)
#   comprimento:k:mm      cota do segmento
#   paralela:k1:k2 · perpendicular:k1:k2 · igual:k1:k2
#   fixo:i                ponto preso onde está
#   coincidente:i:j       dois pontos no mesmo lugar (ramal que sai de um ponto existente)
TIPOS_RESTRICAO = ("eixo", "comprimento", "paralela", "perpendicular", "igual", "fixo", "coincidente")
EIXOS = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}
TOL_EIXO = 1.0          # graus: segmento desenhado mais perto que isso de um eixo ganha "eixo"


def ler_restricoes(textos):
    res = []
    for t in textos:
        partes = [x.strip() for x in str(t).split(":")]
        if not partes or partes[0] not in TIPOS_RESTRICAO:
            continue
        res.append(partes)
    return res


def eixo_de(d, tol=TOL_EIXO):
    """'X', 'Y' ou 'Z' se o vetor d está a menos de tol graus de um eixo; senão None."""
    d = FreeCAD.Vector(d)
    if d.Length < TOL:
        return None
    u = d * (1.0 / d.Length)
    for nome, e in EIXOS.items():
        if abs(abs(u.dot(FreeCAD.Vector(*e))) - 1.0) < 1.0 - math.cos(math.radians(tol)):
            return nome
    return None


def resolver(pontos, segs, restricoes, ancora=0, fixos_extra=()):
    """Ajusta os pontos para cumprir as restrições (mínimos quadrados, mexendo o mínimo possível).
    Retorna (pontos, ok, maior_erro). O ponto 'ancora' fica parado."""
    import numpy as np
    pts = [FreeCAD.Vector(p) for p in pontos]
    n = len(pts)
    rs = ler_restricoes(restricoes)
    if n == 0 or not rs:
        return pts, True, 0.0
    try:
        from scipy.optimize import least_squares
    except ImportError:
        return pts, False, float("inf")
    x0 = np.array([c for p in pts for c in (p.x, p.y, p.z)], dtype=float)
    escala = max(1.0, float(np.ptp(x0.reshape(-1, 3), axis=0).max()) if n > 1 else 1.0)
    fixos = {ancora} | {int(r[1]) for r in rs if r[0] == "fixo" and r[1].isdigit()} | set(fixos_extra)

    def P(x, i):
        return x[3 * i:3 * i + 3]

    def seg(x, k):
        i, j = segs[k]
        return P(x, j) - P(x, i)

    def resid(x):
        r = []
        for t in rs:
            try:
                if t[0] == "eixo":
                    d = seg(x, int(t[1]))
                    e = np.array(EIXOS[t[2].upper()])
                    r.extend(list(d - e * d.dot(e)))
                elif t[0] == "comprimento":
                    r.append(np.linalg.norm(seg(x, int(t[1]))) - float(t[2].replace(",", ".")))
                elif t[0] in ("paralela", "perpendicular", "igual"):
                    d1, d2 = seg(x, int(t[1])), seg(x, int(t[2]))
                    n1, n2 = np.linalg.norm(d1), np.linalg.norm(d2)
                    if t[0] == "igual":
                        r.append(n1 - n2)
                    elif n1 > 1e-9 and n2 > 1e-9:
                        if t[0] == "paralela":
                            r.extend(list(np.cross(d1, d2) / (n1 * n2) * escala))
                        else:
                            r.append(d1.dot(d2) / (n1 * n2) * escala)
                elif t[0] == "coincidente":
                    r.extend(list(P(x, int(t[1])) - P(x, int(t[2]))))
            except (IndexError, ValueError, KeyError):
                continue
        for i in fixos:
            if 0 <= i < n:
                r.extend(list((P(x, i) - P(x0, i)) * 100.0))
        if reg[0]:
            r.extend(list((x - x0) * reg[0]))   # mexe o mínimo nos pontos livres
        return np.array(r, dtype=float)

    # 1º: com um peso pequeno que segura os pontos livres perto de onde estavam (sem pulos);
    # 2º: sem esse peso, partindo daí, para cumprir as restrições com precisão
    reg = [1e-3]
    sol = least_squares(resid, x0, method="trf", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=400)
    reg[0] = 0.0
    sol = least_squares(resid, sol.x, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=400)
    x = sol.x
    r = resid(x)
    erro = float(np.max(np.abs(r))) if len(r) else 0.0
    novos = [FreeCAD.Vector(pts[i]) if i in fixos else FreeCAD.Vector(*P(x, i)) for i in range(n)]
    return novos, erro < 1e-4 * escala, erro


# ------------------------------------------------------------------------ desenho no espaço
# Plano de desenho: passa pelo último ponto e troca com Tab (XY → YZ → ZX).
PLANOS = ("XY", "YZ", "ZX")
NORMAIS = {"XY": (0.0, 0.0, 1.0), "YZ": (1.0, 0.0, 0.0), "ZX": (0.0, 1.0, 0.0)}


def proximo_plano(plano):
    return PLANOS[(PLANOS.index(plano) + 1) % len(PLANOS)] if plano in PLANOS else PLANOS[0]


def no_plano(origem, direcao, base, plano):
    """Encontro do raio (origem + t·direção) com o plano que passa por base; None se o plano está de
    perfil para a vista."""
    n = FreeCAD.Vector(*NORMAIS[plano])
    d = FreeCAD.Vector(direcao)
    den = d.dot(n)
    if abs(den) < 1e-6 * max(d.Length, 1e-12):
        return None
    t = (FreeCAD.Vector(base) - FreeCAD.Vector(origem)).dot(n) / den
    return FreeCAD.Vector(origem) + d * t


def na_grade(p, base, passo, plano):
    """Arredonda as coordenadas do plano para múltiplos do passo a partir de base (comprimentos
    redondos); a coordenada normal fica a da base."""
    if passo <= 0:
        return FreeCAD.Vector(p)
    p, base = FreeCAD.Vector(p), FreeCAD.Vector(base)
    c = [p.x, p.y, p.z]
    b = [base.x, base.y, base.z]
    normal = {"XY": 2, "YZ": 0, "ZX": 1}[plano]
    for k in range(3):
        c[k] = b[k] if k == normal else b[k] + round((c[k] - b[k]) / passo) * passo
    return FreeCAD.Vector(*c)


# ------------------------------------------------------------------------ desenho pelos eixos (como no ZW3D)
# Do último ponto saem os seis sentidos +X, −X, +Y, −Y, +Z, −Z; a linha vai no sentido para onde o mouse aponta
# na tela, com o comprimento que o mouse marca ao longo dele.
SENTIDOS = (("X", 1), ("X", -1), ("Y", 1), ("Y", -1), ("Z", 1), ("Z", -1))
MODOS = ("EIXOS", "XY", "YZ", "ZX")
# a linha gruda no eixo quando o mouse aponta a menos deste ângulo (na tela) dele; mais longe fica livre
ANGULO_EIXO = 20.0
CORES_EIXO = {"X": (0.85, 0.15, 0.15), "Y": (0.1, 0.6, 0.2), "Z": (0.15, 0.35, 0.9)}
NOMES_DEFINICAO = {"sem": "Sem definição", "sub": "Subdefinido", "erro": "Não resolvido", "bem": "Bem definido"}
CORES_DEFINICAO = {"sem": ("#C62828", "#FFFFFF"), "sub": ("#222222", "#FFFFFF"), "erro": ("#F7BE00", "#003A70"),
                   "bem": ("#003A70", "#FFFFFF")}
NOMES_MODO = {"EIXOS": "Eixos X, Y, Z", "XY": "Plano XY", "YZ": "Plano YZ", "ZX": "Plano ZX"}


def proximo_modo(modo):
    return MODOS[(MODOS.index(modo) + 1) % len(MODOS)] if modo in MODOS else MODOS[0]


def escolher_eixo(base_s, cursor_s, pontas_s, escala, minimo_px=4.0):
    """Eixo pelo mouse. base_s, cursor_s: (x, y) na tela; pontas_s: {"X": (x, y) da ponta de base + escala·X, ...}.
    Devolve (eixo, comprimento com sinal em mm, cosseno do ângulo na tela) do eixo cuja direção na tela fica
    mais perto da do mouse, ou None (mouse em cima do ponto)."""
    mx, my = cursor_s[0] - base_s[0], cursor_s[1] - base_s[1]
    lm = math.hypot(mx, my)
    if lm < minimo_px:
        return None
    melhor = None
    for nome, ponta in pontas_s.items():
        vx, vy = ponta[0] - base_s[0], ponta[1] - base_s[1]
        lv2 = vx * vx + vy * vy
        if lv2 < 1e-6:
            continue                       # eixo apontado para quem olha: não dá para escolher pela tela
        escalar = mx * vx + my * vy
        cos = abs(escalar) / (lm * math.sqrt(lv2))
        if melhor is None or cos > melhor[0]:
            melhor = (cos, nome, escalar / lv2 * escala)
    if melhor is None:
        return None
    return melhor[1], melhor[2], melhor[0]


def lado_que_anda(n, segs, k, ancora=0):
    """Pontos que andam junto quando o trecho k muda (o lado que não tem o ponto âncora), e qual ponta do
    trecho fica nesse lado: (conjunto, ponta) ou (None, None) se o trecho está num laço."""
    i, j = segs[k]
    viz = {p: set() for p in range(n)}
    for m, (a, b) in enumerate(segs):
        if m != k:
            viz[a].add(b)
            viz[b].add(a)

    def alcance(p0):
        vis, fila = {p0}, [p0]
        while fila:
            p = fila.pop()
            for q in viz[p]:
                if q not in vis:
                    vis.add(q)
                    fila.append(q)
        return vis
    lj = alcance(j)
    if i in lj:
        return None, None
    if ancora in lj:
        return alcance(i), i
    return lj, j


def mudar_trecho(pontos, segs, k, comprimento=None, direcao=None, ancora=0):
    """Novo comprimento e/ou nova direção do trecho k, levando junto tudo o que está depois dele (o lado sem a
    âncora): o resto do desenho não se deforma. Devolve a lista nova de pontos (ou None se o trecho está num
    laço: aí quem acerta é o resolvedor)."""
    pts = [FreeCAD.Vector(p) for p in pontos]
    lado, ponta = lado_que_anda(len(pts), segs, k, ancora)
    if lado is None:
        return None
    i, j = segs[k]
    fixo = j if ponta == i else i
    atual = pts[ponta] - pts[fixo]
    L = atual.Length if comprimento is None else float(comprimento)
    if direcao is not None:
        u = FreeCAD.Vector(direcao)
        u.normalize()
    elif atual.Length > TOL:
        u = atual * (1.0 / atual.Length)
    else:
        return None
    desloc = pts[fixo] + u * L - pts[ponta]
    for p in lado:
        pts[p] = pts[p] + desloc
    return pts


def definicao(pontos, segs, restricoes, ancora=0):
    """Situação do esboço, como a barra do ZW3D: ("sem", "sub", "erro" ou "bem", graus de liberdade livres).

    sem: nenhuma restrição; erro: as restrições não fecham; sub: ainda há movimento livre; bem: tudo definido
    (o ponto âncora conta como fixo)."""
    import numpy as np
    n = len(pontos)
    rs = ler_restricoes(restricoes)
    if n < 2:
        return "sem", 0
    if not rs:
        return "sem", 3 * (n - 1)
    _novos, ok, _erro = resolver(pontos, segs, restricoes, ancora)
    if not ok:
        return "erro", 0
    x0 = np.array([c for p in pontos for c in (p.x, p.y, p.z)], dtype=float)
    livres = [c for c in range(3 * n) if c // 3 != ancora and not any(
        r[0] == "fixo" and r[1].isdigit() and int(r[1]) == c // 3 for r in rs)]

    def resid(x):
        P = lambda i: x[3 * i:3 * i + 3]
        out = []
        for t in rs:
            try:
                if t[0] == "eixo":
                    i, j = segs[int(t[1])]
                    d = P(j) - P(i)
                    e = np.array(EIXOS[t[2].upper()])
                    out.extend(list(d - e * d.dot(e)))
                elif t[0] == "comprimento":
                    i, j = segs[int(t[1])]
                    out.append(np.linalg.norm(P(j) - P(i)))
                elif t[0] in ("paralela", "perpendicular", "igual"):
                    i1, j1 = segs[int(t[1])]
                    i2, j2 = segs[int(t[2])]
                    d1, d2 = P(j1) - P(i1), P(j2) - P(i2)
                    n1, n2 = np.linalg.norm(d1), np.linalg.norm(d2)
                    if t[0] == "igual":
                        out.append(n1 - n2)
                    elif n1 > 1e-9 and n2 > 1e-9:
                        if t[0] == "paralela":
                            out.extend(list(np.cross(d1, d2) / (n1 * n2)))
                        else:
                            out.append(d1.dot(d2) / (n1 * n2))
                elif t[0] == "coincidente":
                    out.extend(list(P(int(t[1])) - P(int(t[2]))))
            except (IndexError, ValueError, KeyError):
                continue
        return np.array(out, dtype=float)
    r0 = resid(x0)
    if not len(r0):
        return "sem", len(livres)
    J = np.zeros((len(r0), len(livres)))
    h = 1e-4 * max(1.0, float(np.abs(x0).max()))
    for c, idx in enumerate(livres):
        x = x0.copy()
        x[idx] += h
        J[:, c] = (resid(x) - r0) / h
    rank = int(np.linalg.matrix_rank(J, tol=1e-6 * max(1.0, float(np.abs(J).max()))))
    gl = len(livres) - rank
    return ("bem" if gl == 0 else "sub"), gl


# ======================================================================== objeto
class Esboco3D:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, "Esboço 3D", dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyVectorList", "Pontos", "Pontos do esboço (mm, nas coordenadas do objeto)")
        add("App::PropertyIntegerList", "Quebras", "Índices dos pontos que começam um trecho novo (ramal)")
        add("App::PropertyBool", "Fechado", "Liga o último ponto ao primeiro (só com um trecho)", False)
        add("App::PropertyLength", "RaioCurva", "Raio das curvas nos cantos (0 = cantos vivos)", 0.0)
        add("App::PropertyLength", "Comprimento", "Comprimento total das linhas", 0.0, ro=True)
        add("App::PropertyIntegerList", "Construcao", "Segmentos de construção (só referência; não entram na forma)")
        add("App::PropertyStringList", "Restricoes",
            "Restrições: eixo:k:X, comprimento:k:mm, paralela:k1:k2, perpendicular:k1:k2, igual:k1:k2, fixo:i, "
            "coincidente:i:j (k = segmento, i = ponto)")
        add("App::PropertyString", "Situacao", "Situação das restrições", "", ro=True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        pl = obj.Placement
        s = forma(obj.Pontos, obj.Quebras, obj.Fechado, float(obj.RaioCurva), getattr(obj, "Construcao", []))
        obj.Shape = s
        obj.Placement = pl
        comp = sum(e.Length for e in s.Edges) if not s.isNull() else 0.0
        if abs(float(obj.Comprimento) - comp) > 1e-9:
            obj.Comprimento = comp

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc=None, pontos=(), quebras=(), fechado=False, raio=0.0, nome="Esboco3D"):
    doc = doc or FreeCAD.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", nome)
    obj.Label = "Esboço 3D"
    Esboco3D(obj)
    obj.Pontos = [FreeCAD.Vector(p) for p in pontos]
    obj.Quebras = list(quebras)
    obj.Fechado = fechado
    obj.RaioCurva = raio
    if FreeCAD.GuiUp:
        VPEsboco3D(obj.ViewObject)
    doc.recompute()
    return obj


def aplicar_restricoes(obj, ancora=None):
    """Resolve as restrições e grava os pontos. Retorna (ok, erro)."""
    pts = list(obj.Pontos)
    segs = segmentos(pts, obj.Quebras, obj.Fechado)
    rs = list(getattr(obj, "Restricoes", []) or [])
    if not rs:
        if "Situacao" in obj.PropertiesList and obj.Situacao:
            obj.Situacao = ""
        return True, 0.0
    novos, ok, erro = resolver(pts, segs, rs, ancora=0 if ancora is None else ancora)
    if any((a - b).Length > 1e-9 for a, b in zip(novos, pts)):
        obj.Pontos = novos
    txt = "%d restrição(ões) cumpridas" % len(rs) if ok else \
        "Restrições em conflito: confira cotas e eixos (erro de %s mm)" % ("%.3g" % erro).replace(".", ",")
    if obj.Situacao != txt:
        obj.Situacao = txt
    return ok, erro


def forma_obj(obj, raio=None):
    """Forma das linhas normais (sem construção), com o raio pedido (None = o do objeto)."""
    r = float(obj.RaioCurva) if raio is None else raio
    return forma(obj.Pontos, obj.Quebras, obj.Fechado, r, getattr(obj, "Construcao", []))


def e_esboco3d(obj):
    return obj is not None and isinstance(getattr(obj, "Proxy", None), Esboco3D)


# ======================================================================== interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    import PrumoUtil

    class VPEsboco3D:
        def __init__(self, vobj):
            vobj.Proxy = self
            try:
                vobj.LineWidth = 3.0
                vobj.PointSize = 6.0
                vobj.LineColor = (0.0, 0.227, 0.439)        # azul #003A70
                vobj.PointColor = (0.969, 0.745, 0.0)       # amarelo #F7BE00
            except Exception:
                pass

        def attach(self, vobj):
            self.Object = vobj.Object
            self.selecionados = set()
            self.editando = False
            self._sobre = None
            try:
                from pivy import coin
                self._sobre = coin.SoSeparator()
                vobj.RootNode.addChild(self._sobre)
            except Exception:
                self._sobre = None
            self.desenhar_sobreposicao()

        def updateData(self, obj, prop):
            if prop in ("Pontos", "Quebras", "Construcao", "Restricoes", "Fechado"):
                self.desenhar_sobreposicao()

        def destacar(self, segs, editando=None):
            self.selecionados = set(segs)
            if editando is not None:
                self.editando = editando
            self.desenhar_sobreposicao()

        def desenhar_sobreposicao(self):
            """Linhas de construção tracejadas, segmentos selecionados, rótulos das restrições e, na
            edição, os eixos X/Y/Z no ponto de partida."""
            if getattr(self, "_sobre", None) is None:
                return
            from pivy import coin
            raiz = self._sobre
            raiz.removeAllChildren()
            obj = getattr(self, "Object", None)
            if obj is None or "Pontos" not in obj.PropertiesList:
                return
            pts = [FreeCAD.Vector(p) for p in obj.Pontos]
            segs = segmentos(pts, obj.Quebras, obj.Fechado)
            pick = coin.SoPickStyle()
            pick.style = coin.SoPickStyle.UNPICKABLE
            raiz.addChild(pick)

            def linhas(lista, cor, larg, padrao=0xFFFF):
                if not lista:
                    return
                sep = coin.SoSeparator()
                est = coin.SoDrawStyle()
                est.lineWidth = larg
                est.linePattern = padrao
                c = coin.SoBaseColor()
                c.rgb = cor
                co = coin.SoCoordinate3()
                vals = []
                for a, b in lista:
                    vals.extend([(a.x, a.y, a.z), (b.x, b.y, b.z)])
                co.point.setValues(0, len(vals), vals)
                ls = coin.SoLineSet()
                ls.numVertices.setValues(0, len(lista), [2] * len(lista))
                for n in (est, c, co, ls):
                    sep.addChild(n)
                raiz.addChild(sep)

            def texto(p, txt, cor=(0.0, 0.227, 0.439)):
                sep = coin.SoSeparator()
                t = coin.SoTranslation()
                t.translation = (p.x, p.y, p.z)
                c = coin.SoBaseColor()
                c.rgb = cor
                f = coin.SoFont()
                f.name = "Arial:Bold"
                f.size = 14
                tx = coin.SoText2()
                tx.string = txt
                for n in (t, c, f, tx):
                    sep.addChild(n)
                raiz.addChild(sep)

            constr = {int(k) for k in getattr(obj, "Construcao", [])}
            linhas([(pts[i], pts[j]) for k, (i, j) in enumerate(segs) if k in constr],
                   (0.85, 0.45, 0.0), 2, 0xF0F0)
            linhas([(pts[i], pts[j]) for k, (i, j) in enumerate(segs) if k in self.selecionados],
                   (0.969, 0.745, 0.0), 6)
            # rótulos das restrições (no meio do segmento, um pouco ao lado)
            rot = {}
            grupos = {"paralela": "//", "perpendicular": "_|_", "igual": "="}
            n_rel = 0
            for t in ler_restricoes(getattr(obj, "Restricoes", [])):
                try:
                    if t[0] == "eixo":
                        rot.setdefault(int(t[1]), []).append(t[2].upper())
                    elif t[0] == "comprimento":
                        v = float(t[2].replace(",", "."))
                        rot.setdefault(int(t[1]), []).append(("%g" % round(v, 2)).replace(".", ","))
                    elif t[0] in grupos:
                        n_rel += 1
                        for k in (int(t[1]), int(t[2])):
                            rot.setdefault(k, []).append("%s%d" % (grupos[t[0]], n_rel))
                except (IndexError, ValueError):
                    continue
            for k, lst in rot.items():
                if 0 <= k < len(segs):
                    i, j = segs[k]
                    texto((pts[i] + pts[j]) * 0.5, "  " + " ".join(lst))
            if self.editando and pts:
                o = pts[0]
                tam = 60.0
                if len(pts) > 1:
                    bb = FreeCAD.BoundBox()
                    for p in pts:
                        bb.add(p)
                    tam = max(40.0, bb.DiagonalLength * 0.12)
                for nome, cor in (("X", (0.85, 0.15, 0.15)), ("Y", (0.1, 0.6, 0.2)), ("Z", (0.15, 0.35, 0.9))):
                    e = FreeCAD.Vector(*EIXOS[nome]) * tam
                    linhas([(o, o + e)], cor, 2)
                    texto(o + e, nome, cor)

        def getIcon(self):
            return PrumoUtil.icone("esboco3d.svg")

        def doubleClicked(self, vobj):
            if _painel_aberto(vobj.Object) is None:
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

    def _ponto_clicado(info):
        """Ponto 3D (global) de um getObjectInfo: vértice exato, ponta de aresta próxima ou o ponto da
        superfície. None se não há objeto sob o cursor."""
        if not info:
            return None, ""
        p = FreeCAD.Vector(info["x"], info["y"], info["z"])
        doc = FreeCAD.ActiveDocument
        obj = doc.getObject(info.get("Object", "")) if doc else None
        sub = info.get("Component", "") or ""
        if obj is None or not sub:
            return p, "ponto"
        try:
            forma_sub = obj.getSubObject(sub)
        except Exception:
            forma_sub = None
        if forma_sub is None:
            return p, "ponto"
        if sub.startswith("Vertex"):
            return FreeCAD.Vector(forma_sub.Point), "vértice"
        if sub.startswith("Edge"):
            e = forma_sub
            pontas = [v.Point for v in e.Vertexes]
            if pontas:
                perto = min(pontas, key=lambda q: (q - p).Length)
                if (perto - p).Length <= max(0.08 * e.Length, 1e-6):
                    return FreeCAD.Vector(perto), "ponta da aresta"
            if hasattr(e.Curve, "Center") and hasattr(e.Curve, "Radius"):
                c = FreeCAD.Vector(e.Curve.Center)
                if (c - p).Length > 0.92 * e.Curve.Radius:
                    return p, "aresta"
            return p, "aresta"
        return p, "face"

    class Previa:
        """Linha elástica do último ponto ao cursor e marcador do cursor (Coin)."""

        def __init__(self, vista):
            from pivy import coin
            self.vista = vista
            self.raiz = coin.SoSeparator()
            estilo = coin.SoDrawStyle()
            estilo.lineWidth = 2
            estilo.pointSize = 9
            estilo.linePattern = 0xF0F0
            cor = coin.SoBaseColor()
            cor.rgb = (0.969, 0.745, 0.0)
            self.coords = coin.SoCoordinate3()
            self.linhas = coin.SoLineSet()
            self.linhas.numVertices.setValue(0)
            self.ponto = coin.SoPointSet()
            self.ponto.numPoints.setValue(0)
            pick = coin.SoPickStyle()
            pick.style = coin.SoPickStyle.UNPICKABLE
            for n in (pick, estilo, cor, self.coords, self.linhas, self.ponto):
                self.raiz.addChild(n)
            # comprimento do trecho junto ao cursor (o que se digita aparece aqui)
            self.sep_txt = coin.SoSeparator()
            self.pos_txt = coin.SoTranslation()
            cor_txt = coin.SoBaseColor()
            cor_txt.rgb = (0.0, 0.227, 0.439)
            fonte = coin.SoFont()
            fonte.name = "Arial:Bold"
            fonte.size = 15
            self.txt = coin.SoText2()
            for n in (self.pos_txt, cor_txt, fonte, self.txt):
                self.sep_txt.addChild(n)
            self.raiz.addChild(self.sep_txt)
            self.estilo = estilo
            self.cor = cor
            # eixos X/Y/Z saindo do último ponto (o ativo fica grosso), como no ZW3D
            self.sep_triade = coin.SoSeparator()
            self.raiz.addChild(self.sep_triade)
            self.ativo = None
            vista.getSceneGraph().addChild(self.raiz)

        def triade(self, base, tam, ativo=None):
            """Setas X (vermelha), Y (verde) e Z (azul) de base, com tam mm; ativo = "X"/"Y"/"Z" ou None."""
            from pivy import coin
            self.sep_triade.removeAllChildren()
            self.ativo = ativo
            if base is None or not tam:
                return
            for nome in "XYZ":
                e = FreeCAD.Vector(*EIXOS[nome])
                sep = coin.SoSeparator()
                est = coin.SoDrawStyle()
                est.lineWidth = 6 if nome == ativo else 1.5
                c = coin.SoBaseColor()
                c.rgb = CORES_EIXO[nome]
                co = coin.SoCoordinate3()
                ponta = base + e * tam
                # haste nos dois sentidos (o lado negativo fino e curto) e uma "seta" na ponta positiva
                vals = [(base - e * tam * 0.35), base, base, ponta]
                lado = FreeCAD.Vector(*EIXOS["Z" if nome != "Z" else "X"]) * (tam * 0.06)
                vals += [ponta, ponta - e * (tam * 0.15) + lado, ponta, ponta - e * (tam * 0.15) - lado]
                co.point.setValues(0, len(vals), [(v.x, v.y, v.z) for v in vals])
                ls = coin.SoLineSet()
                ls.numVertices.setValues(0, 4, [2, 2, 2, 2])
                for n in (est, c, co, ls):
                    sep.addChild(n)
                self.sep_triade.addChild(sep)

        def estilo_linha(self, eixo=None):
            """Linha elástica: no eixo, cheia e grossa na cor do eixo; livre, tracejada em amarelo."""
            if eixo:
                self.cor.rgb = CORES_EIXO[eixo]
                self.estilo.lineWidth = 4
                self.estilo.linePattern = 0xFFFF
            else:
                self.cor.rgb = (0.969, 0.745, 0.0)
                self.estilo.lineWidth = 2
                self.estilo.linePattern = 0xF0F0

        def rotulo(self, p, texto):
            """Texto ao lado do ponto p (global); texto vazio esconde."""
            if p is None or not texto:
                self.txt.string = ""
                return
            self.pos_txt.translation = (p.x, p.y, p.z)
            self.txt.string = "   " + texto

        def linha(self, ini, fim):
            pts = [p for p in (ini, fim) if p is not None]
            self.coords.point.setValues(0, len(pts), [(p.x, p.y, p.z) for p in pts])
            self.coords.point.setNum(len(pts))
            self.linhas.numVertices.setValue(2 if len(pts) == 2 else 0)
            self.ponto.numPoints.setValue(1 if fim is not None else 0)
            self.ponto.startIndex.setValue(len(pts) - 1 if fim is not None else 0)

        def remover(self):
            try:
                self.vista.getSceneGraph().removeChild(self.raiz)
            except Exception:
                pass

    def _cursor_na_vista():
        w = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
        while w is not None:
            if "View3DInventor" in w.metaObject().className():
                return True
            w = w.parentWidget()
        return False

    class FiltroTeclas(QtCore.QObject):
        """Tab e Esc durante o desenho: chegam antes de o Qt trocar o foco ou fechar o painel."""

        def __init__(self, painel):
            super().__init__()
            self.painel = painel

        def eventFilter(self, obj, ev):
            if ev.type() != QtCore.QEvent.KeyPress or self.painel._vista is None:
                return False
            if _cursor_na_vista() and self.painel.digitando_tecla(ev):
                return True
            if ev.key() not in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Escape):
                return False
            if ev.key() == QtCore.Qt.Key_Tab and not _cursor_na_vista():
                return False          # fora da vista 3D (no painel), Tab segue trocando de campo
            if ev.key() == QtCore.Qt.Key_Tab:
                self.painel.trocar_plano()
            else:
                self.painel.terminar_trecho()
            return True

    def _remover_observador(obs):
        try:
            FreeCADGui.Selection.removeObserver(obs)
        except Exception:
            pass

    class _ObsSelecao:
        """Clicar numa linha do esboço na vista seleciona a linha na lista do painel."""

        def __init__(self, painel):
            self.painel = painel

        def addSelection(self, doc, obj, sub, pnt):
            pn = self.painel
            try:
                nome = pn.obj.Name
            except Exception:
                # o painel fechou sem passar pelo OK/Cancelar (ou o esboço foi apagado): sai da escuta
                QtCore.QTimer.singleShot(0, lambda: _remover_observador(self))
                return
            if obj != nome or not sub or not sub.startswith("Edge"):
                return
            melhor = pn.segmento_da_aresta(sub)
            if melhor is not None:
                somar = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
                pn.selecionar_segmentos([melhor], somar=somar)

    _PAINEIS = {}

    def _painel_aberto(obj):
        """Painel de edição aberto para este esboço (ou None)."""
        pn = _PAINEIS.get(getattr(obj, "Name", ""))
        if pn is None:
            return None
        try:
            if FreeCADGui.Control.activeDialog() and pn.obj.Name == obj.Name:
                return pn
        except Exception:
            pass
        _PAINEIS.pop(getattr(obj, "Name", ""), None)
        return None

    class _EscFecha(QtCore.QObject):
        """Esc ou perder o foco fecha a caixinha de comprimento sem mudar nada."""

        def __init__(self, painel):
            super().__init__()
            self.painel = painel

        def eventFilter(self, obj, ev):
            t = ev.type()
            if t == QtCore.QEvent.KeyPress and ev.key() == QtCore.Qt.Key_Escape:
                QtCore.QTimer.singleShot(0, self.painel._fechar_editor)
                return True
            if t == QtCore.QEvent.FocusOut and ev.reason() not in (QtCore.Qt.PopupFocusReason,):
                QtCore.QTimer.singleShot(0, self.painel._fechar_editor)
            return False

    class PainelEsboco3D:
        """Pontos em tabela; próximo ponto absoluto ou relativo ao anterior; clique no modelo."""

        def __init__(self, obj, novo):
            self.obj = obj
            self.novo = novo
            self.doc = obj.Document
            self._cb = None
            self._vista = None
            self._ocupado = False
            self._ramal_pendente = False
            self._cb_mov = None
            self._filtro = None
            self._previa = None
            self._candidato = None
            self._ultimo_mouse = None
            self._digitado = ""
            self.modo = "EIXOS"          # EIXOS: a linha segue ±X/±Y/±Z pelo mouse; XY/YZ/ZX: ponto no plano
            self.plano = "XY"            # plano do ponto livre (primeiro ponto, ou mouse longe dos eixos)
            self._eixo_ativo = None
            self._arraste = None
            self._clique_ant = None
            self._editor = None
            self._cbs_edicao = []
            self._vista_edicao = None
            self.form = QtWidgets.QWidget()
            self.form.setWindowTitle("Esboço 3D")
            self.form.setWindowIcon(QtGui.QIcon(PrumoUtil.icone("esboco3d.svg")))
            import PrumoPainel as P
            raiz = QtWidgets.QVBoxLayout(self.form)
            dica = P.Mensagem(
                "Clique em <b>Desenhar</b> e vá clicando na vista: do último ponto saem os eixos X, Y e Z e "
                "a linha segue o eixo para onde o mouse aponta (+ ou −); longe dos eixos ela fica livre. "
                "<b>Tab</b> troca para desenhar num plano (XY, YZ, ZX). Para uma medida exata, <b>digite o "
                "número e tecle Enter</b>. <b>Esc</b> termina o trecho. Depois de desenhar: <b>duplo clique</b> "
                "numa linha muda o comprimento e <b>arrastar a ponta</b> leva a linha para outro eixo.")
            raiz.addWidget(dica)
            card_pts, lay = P.bloco("Pontos", "posicao")
            raiz.addWidget(card_pts)
            self.tabela = QtWidgets.QTableWidget(0, 3)
            self.tabela.setHorizontalHeaderLabels(["X (mm)", "Y (mm)", "Z (mm)"])
            self.tabela.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.tabela.setMinimumHeight(170)
            self.tabela.cellChanged.connect(self._celula)
            lay.addWidget(self.tabela)
            caixa = QtWidgets.QWidget()
            g = QtWidgets.QGridLayout(caixa)
            g.setContentsMargins(0, 4, 0, 0)
            ct = QtWidgets.QWidget()
            hc = QtWidgets.QHBoxLayout(ct)
            hc.setContentsMargins(0, 2, 0, 2)
            lb_ct = QtWidgets.QLabel("Comprimento do trecho")
            lb_ct.setStyleSheet("font-weight:600; color:#003A70;")
            hc.addWidget(lb_ct)
            self.comp_trecho = QtWidgets.QDoubleSpinBox()
            self.comp_trecho.setRange(0.0, 1e7)
            self.comp_trecho.setDecimals(1)
            self.comp_trecho.setSuffix(" mm")
            self.comp_trecho.setKeyboardTracking(False)
            self.comp_trecho.setLocale(P.LOCALE)
            self.comp_trecho.setToolTip("Mostra o comprimento enquanto se desenha. Digite um valor e tecle Enter: o "
                                        "ponto vai na direção do cursor (ao longo do eixo, se o cursor estiver "
                                        "alinhado) e o trecho fica cotado")
            self.comp_trecho.lineEdit().returnPressed.connect(lambda: self.aplicar_comprimento(
                self.comp_trecho.value()))
            hc.addWidget(self.comp_trecho, 1)
            lay.addWidget(ct)
            dica_ct = QtWidgets.QLabel("Desenhando, é só digitar o número com o cursor na vista e teclar Enter.")
            dica_ct.setObjectName("PrumoDica")
            dica_ct.setWordWrap(True)
            lay.addWidget(dica_ct)
            sub = QtWidgets.QLabel("Próximo ponto")
            sub.setObjectName("PrumoDica")
            lay.addWidget(sub)
            self.relativo = QtWidgets.QCheckBox("Relativo ao último ponto (Δ)")
            self.relativo.setToolTip("Marcado: os valores são ΔX, ΔY, ΔZ a partir do último ponto")
            self.relativo.setChecked(True)
            g.addWidget(self.relativo, 0, 0, 1, 4)
            self.coord = []
            for i, n in enumerate("XYZ"):
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(-1e7, 1e7)
                s.setDecimals(2)
                s.setSuffix(" mm")
                s.setPrefix(n + " ")
                s.setKeyboardTracking(False)
                s.lineEdit().returnPressed.connect(self.adicionar_digitado)
                s.setMinimumWidth(70)
                g.addWidget(s, 1 + i // 2, i % 2)
                self.coord.append(s)
            bt_add = QtWidgets.QPushButton("Adicionar")
            bt_add.setToolTip("Adiciona o ponto (Enter num dos campos faz o mesmo)")
            bt_add.clicked.connect(self.adicionar_digitado)
            g.addWidget(bt_add, 2, 1)
            lay.addWidget(caixa)
            bl = QtWidgets.QGridLayout()
            self.bt_clicar = QtWidgets.QPushButton("Desenhar")
            self.bt_clicar.setCheckable(True)
            self.bt_clicar.setToolTip("Clique na vista para pôr pontos; a linha segue o eixo apontado pelo mouse. "
                                      "Tab troca o modo, Esc termina o trecho")
            self.bt_clicar.toggled.connect(self._modo_clique)
            self.bt_ramal = QtWidgets.QPushButton("Novo trecho")
            self.bt_ramal.setCheckable(True)
            self.bt_ramal.setToolTip("O próximo ponto começa uma linha separada (ramal)")
            self.bt_ramal.toggled.connect(self._ramal)
            bt_rem = QtWidgets.QPushButton("Remover ponto")
            bt_rem.setToolTip("Remove o ponto selecionado na tabela (ou o último)")
            bt_rem.clicked.connect(self.remover)
            for k, b in enumerate((self.bt_clicar, self.bt_ramal, bt_rem)):
                bl.addWidget(b, k // 2, k % 2)
            lay.addLayout(bl)
            # ---- linhas e restrições
            gr, gl = P.bloco("Linhas e restrições", "angulo")
            self.auto = QtWidgets.QCheckBox("Restrições automáticas")
            self.auto.setChecked(True)
            self.auto.setToolTip("Linha desenhada ao longo de X, Y ou Z ganha a restrição do eixo; clicar num ponto "
                                 "do próprio esboço prende o ramal nele")
            gl.addWidget(self.auto)
            self.lb_definicao = QtWidgets.QLabel("")
            self.lb_definicao.setAlignment(QtCore.Qt.AlignCenter)
            self.lb_definicao.setToolTip("Situação do esboço: sem definição (nenhuma restrição), subdefinido "
                                         "(ainda há movimento livre), não resolvido (restrições em conflito) "
                                         "ou bem definido")
            gl.addWidget(self.lb_definicao)
            self.lista = QtWidgets.QListWidget()
            self.lista.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            self.lista.setMinimumHeight(110)
            self.lista.setToolTip("Linhas do esboço: selecione uma ou duas (Ctrl) — ou clique nelas na vista — e "
                                  "use os botões abaixo")
            self.lista.itemSelectionChanged.connect(self._sel_lista)
            gl.addWidget(self.lista)
            gb = QtWidgets.QGridLayout()
            self.bt_constr = QtWidgets.QPushButton("Construção")
            self.bt_constr.setToolTip("Linha só de referência (tracejada): não entra na forma, mas serve para "
                                      "restrições e cotas")
            self.bt_constr.clicked.connect(self.alternar_construcao)
            gb.addWidget(self.bt_constr, 0, 0, 1, 3)
            for c, eixo in enumerate("XYZ"):
                b = QtWidgets.QPushButton("Ao longo\nde " + eixo)
                b.setToolTip("A linha selecionada fica paralela ao eixo %s" % eixo)
                b.clicked.connect(lambda _c=False, e=eixo: self.restringir_eixo(e))
                gb.addWidget(b, 1, c)
            self.cota = QtWidgets.QDoubleSpinBox()
            self.cota.setRange(0.01, 1e7)
            self.cota.setDecimals(2)
            self.cota.setSuffix(" mm")
            self.cota.setValue(100.0)
            self.cota.lineEdit().returnPressed.connect(self.cotar)
            gb.addWidget(self.cota, 2, 0, 1, 2)
            bt_cota = QtWidgets.QPushButton("Cotar")
            bt_cota.setToolTip("Fixa o comprimento da linha selecionada")
            bt_cota.clicked.connect(self.cotar)
            gb.addWidget(bt_cota, 2, 2)
            for c, (tipo, txt) in enumerate((("paralela", "Paralelas"), ("perpendicular", "Perpend."),
                                             ("igual", "Iguais"))):
                b = QtWidgets.QPushButton(txt)
                b.setToolTip("Duas linhas selecionadas (Ctrl + clique): %s" % txt.lower())
                b.clicked.connect(lambda _c=False, t=tipo: self.relacionar(t))
                gb.addWidget(b, 3, c)
            bt_tirar = QtWidgets.QPushButton("Tirar restrições da seleção")
            bt_tirar.clicked.connect(self.tirar_restricoes)
            gb.addWidget(bt_tirar, 4, 0, 1, 3)
            gl.addLayout(gb)
            self.situacao = QtWidgets.QLabel("")
            self.situacao.setWordWrap(True)
            gl.addWidget(self.situacao)
            raiz.addWidget(gr)
            card_op, fl = P.bloco("Opções", "info", QtWidgets.QFormLayout)
            self.fechado = QtWidgets.QCheckBox("Ligar o último ponto ao primeiro")
            self.fechado.setChecked(bool(obj.Fechado))
            self.fechado.toggled.connect(self._opcoes)
            fl.addRow("Fechado", self.fechado)
            self.raio = QtWidgets.QDoubleSpinBox()
            self.raio.setRange(0.0, 1e6)
            self.raio.setDecimals(2)
            self.raio.setSuffix(" mm")
            self.raio.setValue(float(obj.RaioCurva))
            self.raio.setToolTip("Arredonda os cantos com arcos (curva de tubo). 0 = cantos vivos")
            self.raio.valueChanged.connect(self._opcoes)
            fl.addRow("Raio nos cantos", self.raio)
            hp = QtWidgets.QHBoxLayout()
            self.lb_plano = QtWidgets.QLabel(NOMES_MODO[self.modo])
            self.lb_plano.setStyleSheet("font-weight:700; color:#003A70;")
            bt_plano = QtWidgets.QPushButton("Trocar (Tab)")
            bt_plano.setToolTip("Eixos X, Y, Z → plano XY → YZ → ZX")
            bt_plano.clicked.connect(self.trocar_plano)
            hp.addWidget(self.lb_plano)
            hp.addWidget(bt_plano)
            hp.addStretch(1)
            fl.addRow("Desenhar por", hp)
            self.passo = QtWidgets.QDoubleSpinBox()
            self.passo.setRange(0.0, 1e5)
            self.passo.setDecimals(2)
            self.passo.setSuffix(" mm")
            self.passo.setValue(10.0)
            self.passo.setToolTip("Os pontos clicados no plano andam de passo em passo a partir do último "
                                  "(0 = livre)")
            fl.addRow("Passo do cursor", self.passo)
            raiz.addWidget(card_op)
            self.estado = QtWidgets.QLabel("")
            self.estado.setWordWrap(True)
            raiz.addWidget(self.estado)
            self._encher()
            import PrumoPainel
            PrumoPainel.adotar(self.form)
            PrumoPainel.estreitar(self.form)
            self._transparencias = {}
            self._focar(True)
            self._obs = _ObsSelecao(self)
            FreeCADGui.Selection.addObserver(self._obs)
            self._destacar_selecao()
            self._ligar_edicao()
            _PAINEIS[obj.Name] = self

        # ---- dados
        def pontos(self):
            return [FreeCAD.Vector(p) for p in self.obj.Pontos]

        def _gravar(self, pts, quebras=None):
            self.obj.Pontos = pts
            if quebras is not None:
                self.obj.Quebras = sorted({q for q in quebras if 0 < q < len(pts)})
            aplicar_restricoes(self.obj)
            self.doc.recompute()
            self._encher()

        def segs(self):
            return segmentos(self.obj.Pontos, self.obj.Quebras, self.obj.Fechado)

        def _restricoes_mudaram(self, rs, constr=None):
            self.obj.Restricoes = rs
            if constr is not None:
                self.obj.Construcao = sorted(set(constr))
            aplicar_restricoes(self.obj)
            self.doc.recompute()
            self._encher()

        # ---- linhas e restrições
        def selecionados(self):
            return sorted({self.lista.row(it) for it in self.lista.selectedItems()})

        def _encher_lista(self):
            pts = self.pontos()
            segs = self.segs()
            constr = set(self.obj.Construcao)
            rot = {}
            for t in ler_restricoes(self.obj.Restricoes):
                if t[0] == "eixo":
                    rot.setdefault(int(t[1]), []).append(t[2].upper())
                elif t[0] == "comprimento":
                    rot.setdefault(int(t[1]), []).append("cota")
                elif t[0] in ("paralela", "perpendicular", "igual"):
                    nome = {"paralela": "paralela", "perpendicular": "perpend.", "igual": "igual"}[t[0]]
                    for k in (int(t[1]), int(t[2])):
                        rot.setdefault(k, []).append(nome)
            sel = set(self.selecionados())
            self.lista.blockSignals(True)
            try:
                self.lista.clear()
                for k, (i, j) in enumerate(segs):
                    L = (pts[j] - pts[i]).Length
                    txt = "%d: P%d→P%d  %s mm" % (k + 1, i + 1, j + 1, PrumoUtil.fmt(L, 1))
                    extra = rot.get(k, [])
                    if k in constr:
                        extra = ["construção"] + extra
                    if extra:
                        txt += "  [" + ", ".join(extra) + "]"
                    it = QtWidgets.QListWidgetItem(txt)
                    if k in constr:
                        it.setForeground(QtGui.QBrush(QtGui.QColor("#B35C00")))
                    self.lista.addItem(it)
                    if k in sel:
                        it.setSelected(True)
            finally:
                self.lista.blockSignals(False)
            self.situacao.setText(self.obj.Situacao or "Sem restrições: as linhas ficam onde foram desenhadas.")
            self._mostrar_definicao()

        def _mostrar_definicao(self):
            try:
                est, gl = definicao(self.pontos(), self.segs(), list(self.obj.Restricoes))
            except Exception:
                est, gl = "erro", 0
            self.definicao = (est, gl)
            txt = NOMES_DEFINICAO[est]
            if est == "sub" and gl:
                txt += " — %d movimento(s) livre(s)" % gl
            fundo, letra = CORES_DEFINICAO[est]
            self.lb_definicao.setText(txt)
            self.lb_definicao.setStyleSheet("background:%s; color:%s; font-weight:700; padding:4px; "
                                            "border-radius:4px;" % (fundo, letra))

        def segmento_da_aresta(self, sub):
            """Índice do segmento do esboço que corresponde à aresta sub ("Edge3") da forma, pelo meio."""
            try:
                e = self.obj.Shape.getElement(sub)
                meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
                meio = self.obj.Placement.inverse().multVec(meio)
            except Exception:
                return None
            pts = self.obj.Pontos
            melhor, dmin = None, None
            for k, (i, j) in enumerate(self.segs()):
                a, b = FreeCAD.Vector(pts[i]), FreeCAD.Vector(pts[j])
                d = (meio - (a + b) * 0.5).Length
                if dmin is None or d < dmin:
                    melhor, dmin = k, d
            return melhor

        # ---- editar depois de desenhar
        def _trocar_restricao(self, rs, tipo, k, valor):
            rs = [r for r in rs if not (r.startswith(tipo + ":") and r.split(":")[1].strip() == str(k))]
            rs.append("%s:%d:%s" % (tipo, k, valor))
            return rs

        def definir_comprimento(self, k, L):
            """Novo comprimento do segmento k: o que vem depois dele anda junto (sem deformar) e o segmento
            fica cotado."""
            segs = self.segs()
            if not (0 <= k < len(segs)) or L is None or L <= 0:
                return False
            novos = mudar_trecho(self.pontos(), segs, k, comprimento=L)
            rs = self._trocar_restricao(list(self.obj.Restricoes), "comprimento", k, "%g" % L)
            self.obj.Restricoes = rs
            if novos is None:                      # segmento num laço: o resolvedor acerta
                self._restricoes_mudaram(rs)
            else:
                self._gravar(novos)
            return True

        def orientar(self, k, eixo, sinal, L=None, ponta=None):
            """Leva o segmento k para o eixo (sinal +1/−1, no sentido de quem fica parado para quem anda),
            com o comprimento L (ou o atual). ponta: índice do ponto que anda (o arrastado; padrão: o segundo).
            O que está do lado da ponta anda junto."""
            segs = self.segs()
            if not (0 <= k < len(segs)):
                return False
            i, j = segs[k]
            fixo = i if ponta in (None, j) else j
            u = FreeCAD.Vector(*EIXOS[eixo]) * float(sinal)        # de quem fica parado para quem anda
            pts = self.pontos()
            L = (pts[j] - pts[i]).Length if L is None else float(L)
            if L <= 1e-9:
                return False
            novos = mudar_trecho(pts, segs, k, comprimento=L, direcao=u, ancora=fixo)
            if novos is None:
                return False
            rs = self._trocar_restricao(list(self.obj.Restricoes), "eixo", k, eixo)
            if any(r.startswith("comprimento:") and r.split(":")[1].strip() == str(k) for r in rs):
                rs = self._trocar_restricao(rs, "comprimento", k, "%g" % L)
            self.obj.Restricoes = rs
            self._gravar(novos)
            return True

        def editar_comprimento(self, k, pos_tela=None):
            """Caixinha sobre a vista com o comprimento do segmento k; Enter aplica, Esc desiste."""
            self._fechar_editor()
            segs = self.segs()
            if not (0 <= k < len(segs)):
                return None
            i, j = segs[k]
            L = (self.obj.Pontos[j] - self.obj.Pontos[i]).Length
            ed = QtWidgets.QLineEdit()
            ed.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
            ed.setStyleSheet("QLineEdit{border:2px solid #003A70; background:#FFFFFF; color:#003A70; "
                             "font-weight:700; padding:2px 6px;}")
            ed.setText(PrumoUtil.fmt(L, 2).replace(" ", ""))
            ed.selectAll()
            ed.setMinimumWidth(110)
            ed.setToolTip("Comprimento da linha %d (mm): Enter aplica, Esc desiste" % (k + 1))
            ed.k = k

            def aplicar():
                try:
                    v = float(ed.text().strip().replace(".", "").replace(",", ".")) if "," in ed.text() \
                        else float(ed.text().strip())
                except ValueError:
                    ed.setStyleSheet(ed.styleSheet().replace("#003A70;", "#C62828;", 1))
                    return
                self._fechar_editor()
                self.definir_comprimento(k, v)

            ed.returnPressed.connect(aplicar)
            ed.aplicar = aplicar
            filtro = _EscFecha(self)
            ed.installEventFilter(filtro)
            ed._filtro = filtro
            pos = QtGui.QCursor.pos() if pos_tela is None else pos_tela
            ed.move(pos + QtCore.QPoint(12, 12))
            ed.show()
            ed.raise_()
            ed.activateWindow()
            ed.setFocus()
            self._editor = ed
            return ed

        def _fechar_editor(self):
            ed, self._editor = self._editor, None
            if ed is not None:
                try:
                    ed.hide()
                    ed.deleteLater()
                except Exception:
                    pass

        def _ligar_edicao(self):
            """Escuta o mouse na vista enquanto o painel está aberto: duplo clique numa linha edita o
            comprimento; arrastar a ponta de uma linha leva a linha para outro eixo."""
            try:
                from pivy import coin
                gdoc = FreeCADGui.getDocument(self.doc.Name)
                vista = gdoc.activeView() if gdoc else None
                if vista is None or not hasattr(vista, "addEventCallbackPivy"):
                    return
                self._vista_edicao = vista
                for tipo, f in ((coin.SoMouseButtonEvent.getClassTypeId(), self._botao_edicao),
                                (coin.SoLocation2Event.getClassTypeId(), self._mover_edicao)):
                    self._cbs_edicao.append((tipo, vista.addEventCallbackPivy(tipo, f)))
            except Exception:
                self._vista_edicao = None

        def _desligar_edicao(self):
            v = self._vista_edicao
            for tipo, cb in self._cbs_edicao:
                try:
                    v.removeEventCallbackPivy(tipo, cb)
                except Exception:
                    pass
            self._cbs_edicao = []
            self._vista_edicao = None
            self._fim_arraste(None)

        def _info_em(self, pos, vista=None):
            v = vista or self._vista_edicao or self._vista
            try:
                return v.getObjectInfo((int(pos[0]), int(pos[1])))
            except Exception:
                return None

        def _botao_edicao(self, cb):
            if self._vista is not None:           # desenhando: os cliques põem pontos
                return
            try:
                ev = cb.getEvent()
                from pivy import coin
                if ev.getButton() != coin.SoMouseButtonEvent.BUTTON1:
                    return
                pos = tuple(ev.getPosition().getValue())
                baixo = ev.getState() == coin.SoButtonEvent.DOWN
            except Exception:
                return
            if self.botao_edicao(pos, baixo):
                cb.setHandled()

        def botao_edicao(self, pos, baixo):
            """Clique fora do desenho. Devolve True se o evento foi usado (não segue para a vista)."""
            if not baixo:
                if self._arraste is not None:
                    self._fim_arraste(pos)
                    return True
                return False
            info = self._info_em(pos)
            if not info or info.get("Object") != self.obj.Name:
                self._clique_ant = None
                return False
            sub = info.get("Component", "") or ""
            if sub.startswith("Vertex"):
                return self._inicio_arraste(info, pos)
            if sub.startswith("Edge"):
                k = self.segmento_da_aresta(sub)
                agora = QtCore.QTime.currentTime().msecsSinceStartOfDay()
                ant = self._clique_ant
                self._clique_ant = (k, agora)
                intervalo = QtWidgets.QApplication.doubleClickInterval()
                if ant and ant[0] == k and k is not None and 0 <= agora - ant[1] <= intervalo:
                    self._clique_ant = None
                    QtCore.QTimer.singleShot(0, lambda: self.editar_comprimento(k))
                    return True
            return False

        def _inicio_arraste(self, info, pos):
            p, _t = _ponto_clicado(info)
            loc = self.obj.Placement.inverse().multVec(p)
            dist = [(FreeCAD.Vector(q) - loc).Length for q in self.obj.Pontos]
            if not dist or min(dist) > 1e-3:
                return False
            j = dist.index(min(dist))
            segs = self.segs()
            # a linha que chega no ponto (o ponto é a ponta dela); no primeiro ponto, a que sai dele
            ks = [k for k, (a, b) in enumerate(segs) if b == j] or [k for k, (a, b) in enumerate(segs) if a == j]
            if not ks:
                return False
            k = ks[0]
            a, b = segs[k]
            fixo = a if b == j else b
            v = self._vista_edicao
            self._arraste = {"k": k, "ponta": j, "fixo": fixo, "alvo": None,
                             "previa": Previa(v) if v is not None else None}
            return True

        def _mover_edicao(self, cb):
            if self._arraste is None:
                return
            try:
                pos = tuple(cb.getEvent().getPosition().getValue())
            except Exception:
                return
            self.mover_arraste(pos)
            cb.setHandled()

        def mover_arraste(self, pos):
            a = self._arraste
            if a is None:
                return None
            base = self.obj.Placement.multVec(self.obj.Pontos[a["fixo"]])
            r = self._eixo_pelo_mouse(pos, base, self._vista_edicao)
            a["alvo"] = r
            pv = a["previa"]
            if pv is not None:
                if r is None:
                    pv.linha(None, None)
                    pv.triade(base, self._tamanho_tela(pos, self._vista_edicao), None)
                    pv.rotulo(None, "")
                else:
                    eixo, sinal, fim = r
                    pv.estilo_linha(eixo)
                    pv.linha(base, fim)
                    pv.triade(base, self._tamanho_tela(pos, self._vista_edicao), eixo)
                    pv.rotulo(fim, "%s%s  %s mm" % ("+" if sinal > 0 else "−", eixo,
                                                     PrumoUtil.fmt((fim - base).Length, 1)))
            return r

        def _fim_arraste(self, pos):
            a, self._arraste = self._arraste, None
            if a is None:
                return False
            if a["previa"] is not None:
                a["previa"].remover()
            r = a["alvo"]
            if pos is not None and r is None:
                return False
            if r is None:
                return False
            eixo, sinal, fim = r
            base = self.obj.Placement.multVec(self.obj.Pontos[a["fixo"]])
            return self.orientar(a["k"], eixo, sinal, (fim - base).Length, ponta=a["ponta"])

        def _sel_lista(self):
            self._destacar_selecao()
            ks = self.selecionados()
            if len(ks) == 1:
                i, j = self.segs()[ks[0]]
                self.cota.blockSignals(True)
                self.cota.setValue(max(0.01, (self.obj.Pontos[j] - self.obj.Pontos[i]).Length))
                self.cota.blockSignals(False)

        def _destacar_selecao(self):
            try:
                self.obj.ViewObject.Proxy.destacar(self.selecionados(), editando=True)
            except Exception:
                pass

        def selecionar_segmentos(self, ks, somar=False):
            if not somar:
                self.lista.clearSelection()
            for k in ks:
                it = self.lista.item(k)
                if it is not None:
                    it.setSelected(True)

        def alternar_construcao(self):
            ks = self.selecionados()
            if not ks:
                return
            constr = set(self.obj.Construcao)
            if all(k in constr for k in ks):
                constr -= set(ks)
            else:
                constr |= set(ks)
            self._restricoes_mudaram(list(self.obj.Restricoes), constr)

        def restringir_eixo(self, eixo):
            ks = self.selecionados()
            if not ks:
                return
            rs = [r for r in self.obj.Restricoes
                  if not (r.startswith("eixo:") and int(r.split(":")[1]) in ks)]
            rs += ["eixo:%d:%s" % (k, eixo) for k in ks]
            self._restricoes_mudaram(rs)

        def cotar(self):
            ks = self.selecionados()
            if not ks:
                return
            v = self.cota.value()
            rs = [r for r in self.obj.Restricoes
                  if not (r.startswith("comprimento:") and int(r.split(":")[1]) in ks)]
            rs += ["comprimento:%d:%g" % (k, v) for k in ks]
            self._restricoes_mudaram(rs)

        def relacionar(self, tipo):
            ks = self.selecionados()
            if len(ks) != 2:
                self.situacao.setText("Selecione duas linhas (Ctrl + clique na lista ou na vista).")
                return
            rs = list(self.obj.Restricoes) + ["%s:%d:%d" % (tipo, ks[0], ks[1])]
            self._restricoes_mudaram(rs)

        def tirar_restricoes(self):
            ks = set(self.selecionados())
            if not ks:
                return
            rs = []
            for r in self.obj.Restricoes:
                t = r.split(":")
                if t[0] in ("eixo", "comprimento") and int(t[1]) in ks:
                    continue
                if t[0] in ("paralela", "perpendicular", "igual") and (int(t[1]) in ks or int(t[2]) in ks):
                    continue
                rs.append(r)
            self._restricoes_mudaram(rs)

        def _focar(self, ligar):
            """Na edição, o resto do modelo fica transparente: o esboço não se perde no meio das peças."""
            if ligar:
                for o in self.doc.Objects:
                    vo = getattr(o, "ViewObject", None)
                    if o is self.obj or vo is None or "Transparency" not in vo.PropertiesList:
                        continue
                    try:
                        if vo.Visibility and vo.Transparency < 75:
                            self._transparencias[o.Name] = vo.Transparency
                            vo.Transparency = 75
                    except Exception:
                        pass
            else:
                for nome, t in self._transparencias.items():
                    o = self.doc.getObject(nome)
                    if o is not None and getattr(o, "ViewObject", None) is not None:
                        try:
                            o.ViewObject.Transparency = t
                        except Exception:
                            pass
                self._transparencias = {}

        def _encher(self):
            self._ocupado = True
            try:
                pts = self.pontos()
                quebras = set(self.obj.Quebras)
                self.tabela.setRowCount(len(pts))
                rot = []
                trecho = 1
                for i, p in enumerate(pts):
                    if i in quebras:
                        trecho += 1
                    rot.append(("▶ " if i in quebras else "") + str(i + 1))
                    for j, v in enumerate((p.x, p.y, p.z)):
                        it = QtWidgets.QTableWidgetItem(("%.2f" % (round(v, 2) + 0.0)).replace(".", ","))
                        self.tabela.setItem(i, j, it)
                self.tabela.setVerticalHeaderLabels(rot)
                if pts:
                    self.tabela.scrollToBottom()
            finally:
                self._ocupado = False
            if hasattr(self, "lista"):
                self._encher_lista()
                self._destacar_selecao()
            self._mostrar_estado()

        def _ramal(self, v):
            self._ramal_pendente = bool(v)
            self._mostrar_estado()

        def _celula(self, lin, col):
            if self._ocupado:
                return
            it = self.tabela.item(lin, col)
            try:
                v = float(it.text().replace(".", "").replace(",", ".")) if "," in it.text() \
                    else float(it.text())
            except (ValueError, AttributeError):
                self._encher()
                return
            pts = self.pontos()
            p = pts[lin]
            pts[lin] = FreeCAD.Vector(*(v if k == col else (p.x, p.y, p.z)[k] for k in range(3)))
            self._gravar(pts)

        def _opcoes(self, *_a):
            self.obj.Fechado = self.fechado.isChecked()
            self.obj.RaioCurva = self.raio.value()
            self.doc.recompute()
            self._encher()

        def adicionar(self, p_local, coincide=None, cotar=False):
            """Põe um ponto. Com as restrições automáticas: a linha nova ao longo de um eixo ganha a
            restrição do eixo (e a cota, com cotar=True: desenhada pelos eixos); o primeiro ponto de um ramal
            clicado sobre um ponto do esboço fica preso nele (coincidente)."""
            pts = self.pontos()
            quebras = list(self.obj.Quebras)
            novo_trecho = self._ramal_pendente and bool(pts)
            if novo_trecho:
                quebras.append(len(pts))
                self.bt_ramal.setChecked(False)
            p = FreeCAD.Vector(p_local)
            pts.append(p)
            rs = list(self.obj.Restricoes)
            if getattr(self, "auto", None) is not None and self.auto.isChecked():
                n = len(pts) - 1
                if coincide is not None and 0 <= coincide < n:
                    if novo_trecho or n == 0:
                        rs.append("coincidente:%d:%d" % (n, coincide))
                if not novo_trecho and n > 0:
                    e = eixo_de(p - pts[n - 1])
                    k = len(segmentos(pts, quebras, False)) - 1
                    if e:
                        rs.append("eixo:%d:%s" % (k, e))
                    if cotar and e and (p - pts[n - 1]).Length > TOL:
                        rs.append("comprimento:%d:%g" % (k, round((p - pts[n - 1]).Length, 6)))
            self.obj.Restricoes = rs
            self._gravar(pts, quebras)

        def adicionar_digitado(self):
            v = FreeCAD.Vector(*(s.value() for s in self.coord))
            pts = self.pontos()
            if self.relativo.isChecked() and pts and not self._ramal_pendente:
                v = pts[-1] + v
            self.adicionar(v)
            if self.relativo.isChecked():
                for s in self.coord:
                    s.setValue(0.0)
            self.coord[0].setFocus()
            self.coord[0].selectAll()

        def remover(self):
            pts = self.pontos()
            if not pts:
                return
            linhas = sorted({i.row() for i in self.tabela.selectedIndexes()})
            i = linhas[-1] if linhas else len(pts) - 1
            antigos = self.segs()
            del pts[i]
            quebras = [q - 1 if q > i else q for q in self.obj.Quebras if q != i]
            novos = segmentos(pts, quebras, self.obj.Fechado)
            # renumera restrições e construção: segmentos pelos pontos que ligam, pontos pelo índice
            ren = {}
            for k, (a, b) in enumerate(antigos):
                if i in (a, b):
                    continue
                par = (a - (a > i), b - (b > i))
                if par in novos:
                    ren[k] = novos.index(par)

            def pt(x):
                x = int(x)
                return None if x == i else x - (x > i)
            rs = []
            for r in self.obj.Restricoes:
                t = r.split(":")
                try:
                    if t[0] in ("eixo", "comprimento"):
                        if int(t[1]) in ren:
                            rs.append(":".join([t[0], str(ren[int(t[1])])] + t[2:]))
                    elif t[0] in ("paralela", "perpendicular", "igual"):
                        if int(t[1]) in ren and int(t[2]) in ren:
                            rs.append("%s:%d:%d" % (t[0], ren[int(t[1])], ren[int(t[2])]))
                    elif t[0] == "fixo":
                        if pt(t[1]) is not None:
                            rs.append("fixo:%d" % pt(t[1]))
                    elif t[0] == "coincidente":
                        a, b = pt(t[1]), pt(t[2])
                        if a is not None and b is not None:
                            rs.append("coincidente:%d:%d" % (a, b))
                except (IndexError, ValueError):
                    continue
            self.obj.Restricoes = rs
            self.obj.Construcao = sorted(ren[k] for k in self.obj.Construcao if k in ren)
            self._gravar(pts, quebras)

        # ---- desenhar na vista: plano pelo último ponto (Tab troca), encaixe em vértices
        def _modo_clique(self, ligado):
            self._desligar_clique()
            if not ligado:
                self._mostrar_estado()
                return
            gdoc = FreeCADGui.getDocument(self.doc.Name)
            vista = gdoc.activeView() if gdoc else None
            if vista is None or not hasattr(vista, "addEventCallback"):
                self.bt_clicar.setChecked(False)
                return
            self._vista = vista
            self._cb = vista.addEventCallback("SoMouseButtonEvent", self._clique)
            self._cb_mov = vista.addEventCallback("SoLocation2Event", self._mover)
            self._previa = Previa(vista)
            self._filtro = FiltroTeclas(self)
            QtWidgets.QApplication.instance().installEventFilter(self._filtro)
            self._mostrar_estado()

        def _desligar_clique(self):
            if self._vista is not None:
                for tipo, cb in (("SoMouseButtonEvent", self._cb), ("SoLocation2Event", self._cb_mov)):
                    if cb is not None:
                        try:
                            self._vista.removeEventCallback(tipo, cb)
                        except Exception:
                            pass
            if self._filtro is not None:
                QtWidgets.QApplication.instance().removeEventFilter(self._filtro)
            if self._previa is not None:
                self._previa.remover()
            self._cb = self._cb_mov = self._vista = self._filtro = self._previa = None
            self._candidato = None

        def trocar_plano(self):
            """Tab: eixos X, Y, Z → plano XY → YZ → ZX → eixos."""
            self.modo = proximo_modo(self.modo)
            if self.modo in PLANOS:
                self.plano = self.modo
            self.lb_plano.setText(NOMES_MODO[self.modo])
            if self._ultimo_mouse is not None and self._vista is not None:
                self._mover({"Position": self._ultimo_mouse})
            self._mostrar_estado()

        def terminar_trecho(self):
            """Esc: o próximo ponto começa um trecho novo; Esc de novo para de desenhar."""
            if self._ramal_pendente or not self.obj.Pontos:
                self.bt_clicar.setChecked(False)
                return
            self.bt_ramal.setChecked(True)
            if self._previa is not None:
                self._previa.linha(None, None)
                self._previa.rotulo(None, "")
                self._previa.triade(None, 0)
            self._mostrar_estado()

        # ---- comprimento digitado durante o desenho
        def _ultimo_global(self):
            pts = self.pontos()
            if not pts or self._ramal_pendente:
                return None
            return self.obj.Placement.multVec(pts[-1])

        def direcao_do_cursor(self):
            """Direção (global, unitária) do último ponto ao cursor; alinhada ao eixo quando o cursor está
            perto de um eixo. None se não há último ponto ou o cursor está em cima dele."""
            ini = self._ultimo_global()
            c = self._candidato
            if ini is None or not c or c[0] is None:
                return None
            d = FreeCAD.Vector(c[0]) - ini
            if d.Length < 1e-6:
                return None
            e = eixo_de(d)
            if e:
                u = FreeCAD.Vector(*EIXOS[e])
                return u if d.dot(u) > 0 else u * -1.0
            return d * (1.0 / d.Length)

        def aplicar_comprimento(self, L):
            """Põe o próximo ponto a L mm do último, na direção do cursor; o trecho ganha a cota."""
            self._digitado = ""
            if L is None or L <= 0:
                self.estado.setText("Comprimento tem de ser maior que zero.")
                return False
            u = self.direcao_do_cursor()
            if u is None:
                self.estado.setText("Mova o cursor na direção do trecho e digite o comprimento.")
                return False
            fim = self._ultimo_global() + u * L
            self.adicionar(self.obj.Placement.inverse().multVec(fim))
            k = len(self.segs()) - 1
            if k >= 0:
                rs = [r for r in self.obj.Restricoes
                      if not (r.startswith("comprimento:") and int(r.split(":")[1]) == k)]
                rs.append("comprimento:%d:%g" % (k, L))
                self._restricoes_mudaram(rs)
            if self._ultimo_mouse is not None and self._vista is not None:
                self._mover({"Position": self._ultimo_mouse})
            else:
                self._mostrar_estado()
            return True

        def digitando_tecla(self, ev):
            """Números, vírgula, Backspace e Enter com o cursor na vista: comprimento do trecho."""
            if self._ultimo_global() is None:
                return False
            k, txt = ev.key(), ev.text()
            if txt and (txt.isdigit() or txt in ",."):
                if txt in ",." and any(c in self._digitado for c in ",."):
                    return True
                self._digitado += "," if txt in ",." else txt
            elif k == QtCore.Qt.Key_Backspace and self._digitado:
                self._digitado = self._digitado[:-1]
            elif k in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and self._digitado:
                try:
                    L = float(self._digitado.replace(",", "."))
                except ValueError:
                    L = None
                self.aplicar_comprimento(L)
                return True
            elif k == QtCore.Qt.Key_Escape and self._digitado:
                self._digitado = ""
            else:
                return False
            self._atualizar_rotulo()
            self._mostrar_estado()
            return True

        def _atualizar_rotulo(self):
            if self._previa is None:
                return
            c = self._candidato
            ini = self._ultimo_global()
            if ini is None or not c or c[0] is None:
                self._previa.rotulo(None, "")
                return
            if self._digitado:
                self._previa.rotulo(c[0], "%s mm  (Enter)" % self._digitado)
            else:
                self._previa.rotulo(c[0], "%s mm" % PrumoUtil.fmt((FreeCAD.Vector(c[0]) - ini).Length, 1))

        def _base_global(self):
            pts = self.pontos()
            if pts and not self._ramal_pendente:
                return self.obj.Placement.multVec(pts[-1])
            return self.obj.Placement.multVec(FreeCAD.Vector())

        def _raio_da_vista(self, pos):
            v = self._vista
            p0 = FreeCAD.Vector(v.getPoint(*pos))
            d = FreeCAD.Vector(v.getViewDirection())
            try:
                cam = v.getCameraNode()
                if cam.getTypeId().getName() == "PerspectiveCamera":
                    olho = FreeCAD.Vector(*cam.position.getValue().getValue())
                    d = p0 - olho
            except Exception:
                pass
            return p0, d

        def _tamanho_tela(self, pos, vista=None):
            """Quantos mm valem ~70 px da tela perto do cursor (tamanho dos eixos desenhados)."""
            v = vista or self._vista
            try:
                a = FreeCAD.Vector(v.getPoint(int(pos[0]), int(pos[1])))
                b = FreeCAD.Vector(v.getPoint(int(pos[0]) + 70, int(pos[1])))
                return max((b - a).Length, 1e-6)
            except Exception:
                return 100.0

        def _eixo_pelo_mouse(self, pos, base, vista=None):
            """(eixo, sinal, ponto global) para onde o mouse aponta a partir de base, se ele está a menos de
            ANGULO_EIXO de um dos eixos na tela; senão None. O comprimento anda de passo em passo."""
            v = vista or self._vista
            if v is None or base is None:
                return None
            tam = self._tamanho_tela(pos, v)
            try:
                bs = tuple(v.getPointOnScreen(base))[:2]
                pontas = {n: tuple(v.getPointOnScreen(base + FreeCAD.Vector(*EIXOS[n]) * tam))[:2] for n in "XYZ"}
            except Exception:
                return None
            r = escolher_eixo(bs, (pos[0], pos[1]), pontas, tam)
            if r is None or r[2] < math.cos(math.radians(ANGULO_EIXO)):
                return None
            eixo, t = r[0], r[1]
            passo = self.passo.value() if hasattr(self, "passo") else 0.0
            if passo > 0:
                t = round(t / passo) * passo
            if abs(t) < 1e-9:
                return None
            sinal = 1 if t > 0 else -1
            return eixo, sinal, base + FreeCAD.Vector(*EIXOS[eixo]) * t

        def _plano_de_frente(self):
            """Plano coordenado mais de frente para a vista (o ponto livre cai nele)."""
            try:
                d = FreeCAD.Vector(self._vista.getViewDirection())
            except Exception:
                return self.plano
            return max(PLANOS, key=lambda pl: abs(d.dot(FreeCAD.Vector(*NORMAIS[pl]))))

        def ponto_em(self, pos):
            """(ponto global, tipo) sob o cursor: vértice/ponta de aresta encaixa; nos eixos, o eixo para onde
            o mouse aponta; senão o plano."""
            self._eixo_ativo = None
            try:
                info = self._vista.getObjectInfo(pos)
            except Exception:
                info = None
            self._idx_encaixe = None
            if info and (info.get("Component", "") or "").startswith(("Vertex", "Edge")):
                p, tipo = _ponto_clicado(info)
                if tipo in ("vértice", "ponta da aresta"):
                    if info.get("Object") == self.obj.Name:
                        # ponto do próprio esboço: o ramal fica preso nele
                        loc = self.obj.Placement.inverse().multVec(p)
                        dist = [(q - loc).Length for q in self.obj.Pontos]
                        if dist and min(dist) < 1e-3:
                            self._idx_encaixe = dist.index(min(dist))
                            return p, "ponto P%d do esboço" % (self._idx_encaixe + 1)
                    return p, tipo
            base = self._base_global()
            plano = self.plano
            if self.modo == "EIXOS":
                if self._ultimo_global() is not None:
                    r = self._eixo_pelo_mouse(pos, base)
                    if r is not None:
                        self._eixo_ativo = r[0]
                        return r[2], "eixo %s%s" % ("+" if r[1] > 0 else "−", r[0])
                plano = self._plano_de_frente()
            p0, d = self._raio_da_vista(pos)
            p = no_plano(p0, d, base, plano)
            if p is None:
                return None, "plano %s de perfil para a vista: tecle Tab" % plano
            tipo = ("livre (plano %s)" % plano) if self.modo == "EIXOS" else "plano " + plano
            return na_grade(p, base, self.passo.value(), plano), tipo

        def _mover(self, ev):
            pos = ev.get("Position")
            if pos is None or self._vista is None:
                return
            self._ultimo_mouse = pos
            p, tipo = self.ponto_em(pos)
            self._candidato = (p, tipo)
            pts = self.pontos()
            ini = None if (self._ramal_pendente or not pts) else self.obj.Placement.multVec(pts[-1])
            if self._previa is not None:
                self._previa.estilo_linha(self._eixo_ativo)
                self._previa.linha(ini, p)
                if ini is not None and self.modo == "EIXOS":
                    self._previa.triade(ini, self._tamanho_tela(pos), self._eixo_ativo)
                else:
                    self._previa.triade(None, 0)
            self._atualizar_rotulo()
            if ini is not None and p is not None and not self.comp_trecho.hasFocus():
                self.comp_trecho.blockSignals(True)
                self.comp_trecho.setValue((p - ini).Length)
                self.comp_trecho.blockSignals(False)
            self._mostrar_estado()

        def _clique(self, ev):
            if ev.get("Button") != "BUTTON1" or ev.get("State") != "DOWN":
                return
            p, tipo = self.ponto_em(ev["Position"])
            if p is None:
                self.estado.setText(tipo)
                return
            self.adicionar(self.obj.Placement.inverse().multVec(p), coincide=getattr(self, "_idx_encaixe", None),
                           cotar=tipo.startswith("eixo"))
            self._mover(ev)

        def _mostrar_estado(self):
            pts = self.pontos()
            comp = PrumoUtil.fmt(float(self.obj.Comprimento), 1)
            linhas = ["%d ponto(s), %d trecho(s), comprimento %s mm" % (
                len(pts), len(trechos(pts, self.obj.Quebras)), comp) if pts else "Nenhum ponto ainda."]
            if self._vista is not None:
                if self.modo == "EIXOS":
                    linhas.append("<b>Eixos X, Y, Z</b> — aponte o mouse para o eixo (+ ou −); <b>Tab</b> troca "
                                  "para um plano; <b>Esc</b> termina o trecho (Esc de novo para de desenhar).")
                else:
                    linhas.append("<b>Plano %s</b> — <b>Tab</b> troca; <b>Esc</b> termina o trecho "
                                  "(Esc de novo para de desenhar)." % self.plano)
                c = self._candidato
                if c and c[0] is not None:
                    p = c[0]
                    txt = "Cursor: X %s  Y %s  Z %s (%s)" % (PrumoUtil.fmt(p.x, 1), PrumoUtil.fmt(p.y, 1),
                                                             PrumoUtil.fmt(p.z, 1), c[1])
                    if pts and not self._ramal_pendente:
                        L = (p - self.obj.Placement.multVec(pts[-1])).Length
                        txt += " — trecho de %s mm" % PrumoUtil.fmt(L, 1)
                    linhas.append(txt)
                elif c:
                    linhas.append(c[1])
            if self._digitado:
                linhas.append("Comprimento digitado: <b>%s mm</b> — Enter põe o ponto na direção do cursor; "
                              "Esc apaga." % self._digitado)
            elif self._vista is not None and pts and not self._ramal_pendente:
                linhas.append("Para um comprimento exato, digite o número (com o cursor na vista) e tecle Enter.")
            if self._ramal_pendente:
                linhas.append("Próximo ponto começa um trecho novo.")
            self.estado.setText("<br>".join(linhas))

        # ---- diálogo
        def getStandardButtons(self):
            return QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        def _sair(self):
            self._desligar_clique()
            self._desligar_edicao()
            self._fechar_editor()
            for nome, pn in list(_PAINEIS.items()):
                if pn is self:
                    _PAINEIS.pop(nome, None)
            try:
                FreeCADGui.Selection.removeObserver(self._obs)
            except Exception:
                pass
            self._focar(False)
            try:
                self.obj.ViewObject.Proxy.destacar([], editando=False)
            except Exception:
                pass

        def accept(self):
            self._sair()
            self.doc.commitTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

        def reject(self):
            self._sair()
            self.doc.abortTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

    def abrir_painel(obj=None):
        doc = obj.Document if obj is not None else FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        doc.openTransaction("Esboço 3D")
        novo = obj is None
        if novo:
            obj = criar(doc)
        painel = PainelEsboco3D(obj, novo)
        FreeCADGui.Control.showDialog(painel)
        return painel

    class CmdEsboco3D:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("esboco3d.svg"),
                    "MenuText": "Esboço 3D",
                    "ToolTip": "Linhas no espaço por pontos X, Y, Z (digitados ou clicados no modelo), com "
                               "ramais e curvas nos cantos. Serve de esqueleto de estrutura e de caminho de "
                               "tubo ou varredura."}

        def IsActive(self):
            return True

        def Activated(self):
            abrir_painel()
