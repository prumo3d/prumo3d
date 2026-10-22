# SPDX-License-Identifier: LGPL-2.1-or-later
"""Detalhe de ligação por elementos finitos (submodelo).

A análise por barras dá os esforços; aqui o Prumo recorta a região de um nó (as barras que chegam
nele, cortadas a uma distância do nó, mais as chapas que ficam dentro: placa de base, reforços,
tampas), funde tudo num sólido só (ligação soldada contínua) e monta um estudo do CalculiX:

* em cada corte, os esforços da combinação escolhida (N, V, M e T da análise por barras) entram por
  um corpo rígido com nó de referência na linha do esqueleto (restrição "Corpo rígido" do FreeCAD);
* nó apoiado: a face de apoio (placa de base ou ponta da barra) fica engastada;
  nó sem apoio: o corte da barra de maior seção fica engastado e recebe o que sobra do equilíbrio.

As tensões perto dos cortes são perturbadas pelo corpo rígido (São Venant): o resultado que vale é o
da zona do nó, que o assistente mostra como "zona de interesse".
"""
import math

import FreeCAD

GAMA_A1 = 1.10


def _vec(a):
    return FreeCAD.Vector(float(a[0]), float(a[1]), float(a[2]))


def _calc(analise):
    calc = getattr(analise.Proxy, "calc", None)
    if calc is None:
        calc = analise.Proxy.calcular_silencioso(analise)
    if calc is None or calc.erro or not calc.resultados:
        raise ValueError("a análise por barras não tem resultado%s" % (
            ": " + calc.erro if calc is not None and calc.erro else ""))
    return calc


# ------------------------------------------------------------------ nós da estrutura
def linhas_no_ponto(calc, P, tol=1.0):
    """[(linha, s ao longo dela)] das linhas que passam pelo ponto P."""
    res = []
    for i, (p0, t, L) in calc.mapa["linhas"].items():
        s = (P - p0).dot(t)
        if -tol < s < L + tol and (p0 + t * s - P).Length < tol:
            res.append((i, min(max(s, 0.0), L)))
    return res


def juntas(analise):
    """Nós que valem um detalhe: onde chegam duas barras ou mais, ou onde há apoio.
    [{"ponto": Vector, "linhas": [(i, s)], "apoio": tipo ou None, "texto": str}]"""
    import PrumoAnaliseEstrutura as A
    calc = _calc(analise)
    apoios = {}
    for k, tipo in analise.Proxy.apoios(analise).items():
        apoios[k] = tipo
    pts = []
    for i, (p0, t, L) in calc.mapa["linhas"].items():
        for q in (p0, p0 + t * L):
            if not any((q - p).Length < 1.0 for p in pts):
                pts.append(FreeCAD.Vector(q))
    for k in apoios:
        q = _vec(A._ponto_da_chave(k))
        if not any((q - p).Length < 1.0 for p in pts):
            pts.append(q)
    res = []
    for P in pts:
        ls = linhas_no_ponto(calc, P)
        apoio = None
        for k, tipo in apoios.items():
            if (_vec(A._ponto_da_chave(k)) - P).Length < 1.0:
                apoio = tipo
        ramos = sum(1 if s < 1.0 or s > calc.mapa["linhas"][i][2] - 1.0 else 2 for i, s in ls)
        if ramos < 2 and apoio is None:
            continue
        txt = "Nó (%s; %s; %s) · barra%s %s" % (
            _f(P.x), _f(P.y), _f(P.z), "s" if len(ls) > 1 else "", ", ".join(str(i + 1) for i, _s in ls))
        if apoio:
            txt += " · " + apoio.lower()
        res.append({"ponto": P, "linhas": ls, "apoio": apoio, "texto": txt})
    return res


def junta_mais_proxima(analise, p):
    js = juntas(analise)
    if not js:
        return None
    return min(js, key=lambda j: (j["ponto"] - p).Length)


def _f(v, casas=0):
    s = ("%." + str(casas) + "f") % v
    if s.lstrip("-").strip("0.") == "":
        s = s.lstrip("-")
    return s.replace(".", ",")


# ------------------------------------------------------------------ esforços no corte
def forca_no_corte(r, eb, x, lado_baixo):
    """Força e momento (globais, N e N·mm, momento em relação ao ponto do corte) que o resto da
    estrutura aplica no pedaço guardado do elemento eb, cortado em x.
    lado_baixo=True: o pedaço guardado é o de 0 a x (o nó fica no início do elemento)."""
    import numpy as np
    import PrumoPortico as PT
    f = r.extremos[eb]
    dist, pont = r.cargas[eb]
    sc, mc = PT.resultante_ate(dist, pont, x)
    s = np.array([f[0], f[1], f[2]], dtype=float) + sc
    m = np.array([f[3], f[4] + x * f[2], f[5] - x * f[1]], dtype=float) + mc
    # s, m: resultante (e momento no corte) do que age no pedaço de 0 a x, fora o corte
    if lado_baixo:
        F, M = -s, -m
    else:
        F, M = s, m
    R, _L = r.geo[eb]
    return _vec(R.T @ F), _vec(R.T @ M)


def _elemento_em(calc, i, s):
    import numpy as np
    for eb, a in calc.mapa["barras"][i]:
        L = float(np.linalg.norm(calc.modelo.nos[calc.modelo.barras[eb].j] - calc.modelo.nos[calc.modelo.barras[eb].i]))
        if a - 1e-6 <= s <= a + L + 1e-6:
            return eb, min(max(s - a, 0.0), L)
    raise ValueError("posição %s fora da barra %d" % (_f(s), i + 1))


def combinacao_que_governa(calc, linhas):
    pior = None
    for i, _s in linhas:
        v = calc.verificacao.get(i)
        if v and (pior is None or v["taxa"] > pior["taxa"]):
            pior = v
    if pior:
        return pior["combinacao"]
    return next(n for n, t, _f2 in calc.combinacoes if t == "ELU")


# ------------------------------------------------------------------ geometria e cargas
class Detalhe:
    """Resultado de montar(): sólido, cortes com esforços, faces de engaste e avisos."""

    def __init__(self):
        self.ponto = None
        self.combinacao = ""
        self.forma = None
        self.cortes = []          # {"linha", "s", "ponto", "dir", "F", "M", "faces", "fixo", "dist"}
        self.faces_fixas = []
        self.texto_fixo = ""
        self.pecas = []           # rótulos das peças incluídas
        self.avisos = []
        self.raio_zona = 0.0
        self.espessura = 0.0
        self.apoio = None
        self.material = ("", 250.0, 400.0)
        self.ligacoes = []        # verificações de solda e parafusos (dicts com "texto" e "taxa")


def _secoes(est):
    import PrumoEstrutura as E
    todas = E.arestas(est.Esqueleto)
    ativas = E.arestas_ativas(est, todas)
    normal = E._normal_esqueleto(todas)
    return lambda i: E.Secao(est, ativas, i, normal)


def _pontos_especiais(calc, i):
    """Posições ao longo da linha i onde há outra ligação (pontas e nós em T)."""
    p0, t, L = calc.mapa["linhas"][i]
    ss = {0.0, L}
    for j, (q0, u, Lj) in calc.mapa["linhas"].items():
        if j == i:
            continue
        for q in (q0, q0 + u * Lj):
            s = (q - p0).dot(t)
            if -1.0 < s < L + 1.0 and (p0 + t * s - q).Length < 1.0:
                ss.add(min(max(s, 0.0), L))
    return sorted(ss)


def montar(analise, ponto, combinacao=None, distancia=0.0):
    """Monta o detalhe do nó mais próximo de `ponto` (Vector). Retorna Detalhe."""
    import Part
    import PrumoEstrutura as E
    import PrumoEstruturaExtras as X
    import PrumoAnaliseEstrutura as A
    calc = _calc(analise)
    est = analise.Estrutura
    j = junta_mais_proxima(analise, FreeCAD.Vector(ponto))
    if j is None:
        raise ValueError("a estrutura não tem nós com duas barras ou apoio")
    d = Detalhe()
    d.ponto = P = j["ponto"]
    d.apoio = j["apoio"]
    d.material = calc.material
    linhas = j["linhas"]
    d.combinacao = combinacao or combinacao_que_governa(calc, linhas)
    tipo = dict((n, t) for n, t, _f2 in calc.combinacoes).get(d.combinacao)
    if tipo is None:
        raise ValueError("combinação desconhecida: %s" % d.combinacao)
    r = calc.resultados[d.combinacao]
    sec = _secoes(est)
    dims = {i: sec(i) for i, _s in linhas}
    h = max(max(s.alt, s.larg) for s in dims.values())
    dist = float(distancia) if distancia and distancia > 0 else max(2.0 * h, 150.0)
    barras = {b.Indice: b for b in E.barras_de(est)}
    pecas = []
    for i, s0 in linhas:
        p0, t, L = calc.mapa["linhas"][i]
        lib = calc.mapa.get("liberacoes", {}).get(i, "")
        trel = ("Barra de treliça", "Só tração (contraventamento)")
        if (s0 < 1.0 and (lib in ("Rótula no início", "Rótula nas duas pontas") or lib in trel)) or \
                (s0 > L - 1.0 and (lib in ("Rótula no fim", "Rótula nas duas pontas") or lib in trel)):
            d.avisos.append("A barra %d é rotulada neste nó no modelo por barras, mas no detalhe ela fica soldada "
                            "(peças fundidas): modele a ligação flexível real para avaliar." % (i + 1))
        esp = _pontos_especiais(calc, i)
        lados = []
        for sinal in (1, -1):
            if (sinal > 0 and s0 > L - 1.0) or (sinal < 0 and s0 < 1.0):
                continue
            prox = [abs(s - s0) for s in esp if (s - s0) * sinal > 1.0]
            D = min(prox) if prox else L
            di = min(dist, 0.45 * D)
            if di < 0.5 * h:
                d.avisos.append("Barra %d: o corte ficou a %s mm do nó (perto da próxima ligação); as tensões "
                                "do detalhe sofrem a influência do corte." % (i + 1, _f(di)))
            sc = s0 + sinal * di
            eb, x = _elemento_em(calc, i, sc)
            F, M = forca_no_corte(r, eb, x, lado_baixo=sinal > 0)
            d.cortes.append({"linha": i, "s": sc, "ponto": p0 + t * sc, "dir": t * sinal, "F": F, "M": M,
                             "faces": [], "fixo": False, "dist": di,
                             "area": calc.mapa["secoes"][i]["A"]})
            lados.append(sc)
        b = barras.get(i)
        if b is None:
            continue
        s_lo = min([sc for sc in lados if sc < s0] or [s0 - 3.0 * h])
        s_hi = max([sc for sc in lados if sc > s0] or [s0 + 3.0 * h])
        cil = Part.makeCylinder(6.0 * h, s_hi - s_lo, p0 + t * s_lo, t)
        peca = b.Shape.common(cil)
        if peca.Solids:
            pecas.append(peca)
            d.pecas.append(b.Label)
    # chapas que ficam inteiras dentro da região
    raio = max(c["dist"] for c in d.cortes) if d.cortes else dist
    for o in getattr(est, "Group", []):
        if E.eh_barra(o) or X.eh_solda(o) or not hasattr(o, "Shape") or not o.Shape.Solids:
            continue
        sh = o.Shape
        try:
            perto = sh.distToShape(Part.Vertex(P))[0] < raio
        except Exception:
            perto = False
        if not perto:
            continue
        bb = sh.BoundBox
        dentro = all((FreeCAD.Vector(x, y, z) - P).Length <= raio * 1.05
                     for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax) for z in (bb.ZMin, bb.ZMax))
        if dentro:
            pecas.append(sh.copy())
            d.pecas.append(o.Label)
        else:
            d.avisos.append("%s passa do corte do detalhe e ficou de fora." % o.Label)
    if not pecas:
        raise ValueError("nenhuma barra com sólido neste nó")
    forma = pecas[0].fuse(pecas[1:]) if len(pecas) > 1 else pecas[0]
    try:
        forma = forma.removeSplitter()
    except Exception:
        pass
    if len(forma.Solids) != 1 and len(pecas) > 1:
        try:
            forma = pecas[0].fuse(pecas[1:], 0.5).removeSplitter()
        except Exception:
            pass
    if len(forma.Solids) != 1:
        raise ValueError("as peças do nó não formaram um sólido só (há folga entre as barras?). Confira os "
                         "cantos da estrutura")
    forma = forma.Solids[0]
    d.forma = forma
    # faces de cada corte
    for c in d.cortes:
        t = c["dir"]
        for k, f in enumerate(forma.Faces):
            if "Plane" not in type(f.Surface).__name__:
                continue
            n = f.Surface.Axis if hasattr(f.Surface, "Axis") else f.normalAt(0, 0)
            cm = f.CenterOfMass
            if abs(abs(n.dot(t)) - 1.0) < 1e-4 and abs((cm - c["ponto"]).dot(t)) < 0.05 \
                    and (cm - c["ponto"]).Length < 3.0 * h:
                c["faces"].append("Face%d" % (k + 1))
        if not c["faces"]:
            raise ValueError("não achei a face do corte da barra %d" % (c["linha"] + 1))
    # engaste
    if d.apoio:
        d.faces_fixas, d.texto_fixo = _faces_de_apoio(d, forma, est, linhas, calc, h)
        if d.apoio != "Engaste":
            d.avisos.append("O apoio é %s no modelo por barras; no detalhe a face de apoio fica engastada "
                            "(a checar a liberdade de giro real da base)." % d.apoio.lower())
    else:
        fixo = max(d.cortes, key=lambda c: (c["area"], -c["linha"]))
        fixo["fixo"] = True
        d.faces_fixas = list(fixo["faces"])
        d.texto_fixo = "corte da barra %d (a de maior seção), engastado: recebe o equilíbrio do nó" % (
            fixo["linha"] + 1)
    d.avisos.append("Cargas aplicadas dentro da região do detalhe (no nó e nos pedaços de barra) não entram: "
                    "o equilíbrio delas vai para o engaste.")
    try:
        d.ligacoes = verificar_ligacoes(calc, r, est, linhas, d.apoio)
    except Exception as ex:
        d.ligacoes = []
        d.avisos.append("Verificação das soldas e parafusos não feita: %s" % ex)
    d.avisos.append("No sólido a ligação fica soldada em toda a volta (peças fundidas); as soldas e os "
                    "chumbadores são verificados à parte pela NBR 8800:2024 (6.2 e 6.3), com os esforços das "
                    "barras no nó.")
    d.raio_zona = 0.8 * min(c["dist"] for c in d.cortes)
    d.espessura = min(2.0 * p.Volume / p.Area for p in pecas)
    return d


# ------------------------------------------------------------------ soldas e chumbadores (6.2 e 6.3)
DIAMETROS_CHUMBADOR = (12.0, 16.0, 20.0, 22.0, 24.0, 27.0, 30.0, 36.0, 42.0, 48.0)
# MPa — a NBR 8800:2024 dá as disposições de bases de pilares para chumbadores de ASTM A36 (Tabela 18,
# nota a); fu do A36 = 400 MPa, o mínimo da Tabela A.2 (o certificado do chumbador manda)
FUB_CHUMBADOR = 400.0


def _contorno_externo(p):
    import PrumoPerfis
    it = PrumoPerfis.perfil(p["nome"]) if PrumoPerfis.perfil(p["nome"]) else None
    if it is None:
        raise ValueError("perfil %s fora do catálogo" % p["nome"])
    ext, _furos = PrumoPerfis.contorno(it)
    if isinstance(ext, tuple):          # tubo redondo
        R = ext[1] / 2.0
        ext = [(R * math.cos(2 * math.pi * k / 48), R * math.sin(2 * math.pi * k / 48)) for k in range(48)]
    return [(u - p.get("cu", 0.0), v - p.get("cv", 0.0)) for u, v in ext]


def _espessura_minima(p):
    t = p["tipo"]
    if t in ("I", "U"):
        return min(p["tw"], p["tf"])
    if t in ("L", "TQ", "TUBO"):
        return p["t"]
    if t == "POL" and p.get("chapas"):
        return min(c["t"] for c in p["chapas"])
    return math.sqrt(p["A"]) / 4.0


def solda_contorno(p, e, fy, fu, perna=None, eletrodo="E70XX"):
    """Filete em todo o contorno externo do perfil, pelo método elástico das linhas de solda: força
    por milímetro de cordão no ponto mais solicitado (somas em módulo, a favor da segurança).
    e: esforços da barra no nó (N, Vy, Vz, T, My em torno do eixo de maior inércia, Mz). Retorna dict."""
    import PrumoNBR8800 as N
    pts = _contorno_externo(p)
    n = len(pts)
    Lw = cu = cv = 0.0
    seg = []
    for k in range(n):
        (u1, v1), (u2, v2) = pts[k], pts[(k + 1) % n]
        L = math.hypot(u2 - u1, v2 - v1)
        if L > 1e-9:
            seg.append((u1, v1, u2, v2, L))
            Lw += L
            cu += L * (u1 + u2) / 2.0
            cv += L * (v1 + v2) / 2.0
    cu /= Lw
    cv /= Lw
    Iu = Iv = 0.0
    for u1, v1, u2, v2, L in seg:
        a1, a2, b1, b2 = v1 - cv, v2 - cv, u1 - cu, u2 - cu
        Iu += L * (a1 * a1 + a1 * a2 + a2 * a2) / 3.0
        Iv += L * (b1 * b1 + b1 * b2 + b2 * b2) / 3.0
    Ip = Iu + Iv
    q = 0.0
    for u, v in pts:
        du, dv = abs(u - cu), abs(v - cv)
        fa = abs(e["N"]) / Lw + abs(e["My"]) * dv / Iu + abs(e["Mz"]) * du / Iv
        fs = math.hypot(abs(e["Vy"]) / Lw + abs(e["T"]) * dv / Ip, abs(e["Vz"]) / Lw + abs(e["T"]) * du / Ip)
        q = max(q, math.hypot(fa, fs))
    fw = N.FW_ELETRODO.get(eletrodo, 485.0)
    por_mm = 0.6 * fw * 0.707 / N.GAMA_W2           # N/mm de cordão por mm de perna
    dw_req = q / por_mm
    t = _espessura_minima(p)
    dw_min = N.perna_minima(t)
    fonte = "cordão do projeto"
    if not perna:
        perna = max(dw_min, math.ceil(dw_req))
        fonte = "sugerida"
    base = min(0.60 * fy * t / N.GAMA_A1, 0.60 * fu * t / N.GAMA_A2)
    res = {"tipo": "solda", "q": q, "Lw": Lw, "dw_req": dw_req, "dw": float(perna), "dw_min": dw_min,
           "fonte": fonte, "taxa_solda": q / (por_mm * perna), "taxa_base": q / base, "t": t}
    res["taxa"] = max(res["taxa_solda"], res["taxa_base"])
    txt = ("filete de %s mm (%s) em todo o contorno (%s mm de cordão): %s N/mm no ponto mais solicitado; "
           "perna necessária %s mm, mínima %s mm; taxa da solda %s, do metal-base (t = %s mm) %s" % (
               _f(perna), fonte, _f(Lw), _f(q), _f(dw_req, 1), _f(dw_min), _f(res["taxa_solda"], 2), _f(t, 1),
               _f(res["taxa_base"], 2)))
    if perna < dw_min:
        txt += "; ATENÇÃO: perna abaixo da mínima"
    if perna > N.perna_maxima(t) + 1e-9:
        txt += "; ATENÇÃO: perna acima da máxima de %s mm ao longo da borda (6.2.6.2.2)" % _f(N.perna_maxima(t), 1)
    res["texto"] = txt
    return res


def chumbadores(placa, e):
    """Chumbadores da placa de base pelo método elástico (sem contar a compressão no concreto: a favor
    da segurança na tração). Retorna dict ou None se a placa não tiver furos."""
    import PrumoNBR8800 as N
    n = int(placa.Furos)
    if not n:
        return None
    L, C = placa.Largura.Value, placa.Comprimento.Value
    hl, hc, borda = L / 2.0, C / 2.0, placa.DistanciaBorda.Value
    if n == 4:
        pos = [(x, y) for x in (-hl + borda, hl - borda) for y in (-hc + borda, hc - borda)]
    else:
        pos = [(0, -hc + borda), (0, hc - borda)] if C >= L else [(-hl + borda, 0), (hl - borda, 0)]
    su = sum(u * u for u, _v in pos)
    sv = sum(v * v for _u, v in pos)
    sr = su + sv
    furo = placa.DiametroFuro.Value
    d = max([x for x in DIAMETROS_CHUMBADOR if x <= furo - 1.5] or [DIAMETROS_CHUMBADOR[0]])
    FvRd, FtRd = N.parafuso(d, FUB_CHUMBADOR, rosca_no_plano=True)
    pior = (0.0, 0.0, 0.0)
    for u, v in pos:
        ft = max(e["N"], 0.0) / n + (abs(e["My"]) * abs(v) / sv if sv else 0.0) + \
            (abs(e["Mz"]) * abs(u) / su if su else 0.0)
        fv = math.hypot(e["Vy"], e["Vz"]) / n + (abs(e["T"]) * math.hypot(u, v) / sr if sr else 0.0)
        it = N.parafuso_interacao(fv, ft, FvRd, FtRd)
        if it > pior[2]:
            pior = (ft, fv, it)
    ft, fv, inter = pior
    sem_braco = []
    if su <= 1e-9 and abs(e["Mz"]) > 1e3:
        sem_braco.append("Mz = %s kN·m" % _f(abs(e["Mz"]) / 1e6, 2))
    if sv <= 1e-9 and abs(e["My"]) > 1e3:
        sem_braco.append("My = %s kN·m" % _f(abs(e["My"]) / 1e6, 2))
    res = {"tipo": "chumbador", "n": n, "d": d, "Ft": ft, "Fv": fv, "FtRd": FtRd, "FvRd": FvRd,
           "taxa": max(ft / FtRd, fv / FvRd, inter)}
    res["texto"] = ("%d chumbadores Ø%s mm (furo %s mm; ASTM A36, fu = %s MPa): tração %s kN × %s kN, "
                    "corte %s kN × %s kN, interação %s; ancoragem no concreto não verificada" % (
                        n, _f(d), _f(furo), _f(FUB_CHUMBADOR), _f(ft / 1e3, 1), _f(FtRd / 1e3, 1), _f(fv / 1e3, 1),
                        _f(FvRd / 1e3, 1), _f(inter, 2)))
    if sem_braco:
        res["taxa"] = max(res["taxa"], 9.99)
        res["texto"] += ("; ATENÇÃO: %s em torno da linha dos chumbadores não é resistido por eles (placa com "
                         "chumbadores numa linha só): use 4 chumbadores ou modele a base como rótula nesse eixo"
                         % " e ".join(sem_braco))
    return res


def verificar_ligacoes(calc, r, est, linhas, apoio):
    """Soldas (barras que terminam no nó) e chumbadores (placa de base) do nó. Lista de dicts."""
    import PrumoEstruturaExtras as X
    fy, fu = calc.material[1], calc.material[2]
    placas = [o for o in getattr(est, "Group", [])
              if type(getattr(o, "Proxy", None)).__name__ == "PlacaBase" and getattr(o, "Barra", None) is not None]
    soldas = [o for o in getattr(est, "Group", []) if X.eh_solda(o)]
    termina = []
    for i, s0 in linhas:
        _p0, _t, L = calc.mapa["linhas"][i]
        if s0 < 1.0 or s0 > L - 1.0:
            termina.append((i, s0, L))
    out = []
    if len(linhas) < 2 and not apoio:
        return out
    # duas barras alinhadas que chegam ao nó por lados opostos: viga contínua desenhada em pedaços
    # (a peça real passa direto pelo nó); não há solda de topo entre elas
    continuas = set()
    saida = {}
    for i, s0, L in termina:
        _p0, t, _L = calc.mapa["linhas"][i]
        saida[i] = t * (1.0 if s0 < 1.0 else -1.0)
    for i in saida:
        for j in saida:
            if i < j and saida[i].dot(saida[j]) < -0.999:
                continuas.update((i, j))
    for i, s0, L in termina:
        if i in continuas:
            continue
        if len(linhas) == 1 and not any(pl.Barra.Indice == i for pl in placas):
            continue        # apoio direto, sem placa: nada a soldar no modelo
        eb, x = _elemento_em(calc, i, min(max(s0, 0.0), L))
        e = r.esforcos(eb, x)
        p = calc.mapa["secoes"][i]
        perna = None
        outras = {j for j, _s in linhas if j != i}
        for so in soldas:
            idx = {getattr(pc, "Indice", None) for pc in so.Pecas}
            placa_aqui = any(pc in placas and getattr(pc.Barra, "Indice", None) == i for pc in so.Pecas)
            if i in idx and (idx & outras or placa_aqui):
                perna = so.Perna.Value
                break
        sd = solda_contorno(p, e, fy, fu, perna)
        sd["barra"] = i + 1
        sd["texto"] = "Barra %d: %s" % (i + 1, sd["texto"])
        out.append(sd)
        k = 0 if s0 < 1.0 else 1
        for pl in placas:
            if pl.Barra.Indice == i and X.PONTAS.index(pl.Ponta) == k:
                ch = chumbadores(pl, e)
                if ch:
                    ch["barra"] = i + 1
                    ch["texto"] = "%s (barra %d): %s" % (pl.Label, i + 1, ch["texto"])
                    out.append(ch)
    return out


def _faces_de_apoio(d, forma, est, linhas, calc, h):
    """Faces engastadas num nó apoiado: a face de baixo da placa de base ou a ponta da barra."""
    P = d.ponto
    cand = []
    for i, s0 in linhas:
        p0, t, L = calc.mapa["linhas"][i]
        for k, f in enumerate(forma.Faces):
            if "Plane" not in type(f.Surface).__name__:
                continue
            n = f.Surface.Axis
            if abs(abs(n.dot(t)) - 1.0) > 1e-4:
                continue
            cm = f.CenterOfMass
            fora = (cm - P).dot(t) * (1 if s0 < 1.0 else -1)   # >0: para dentro da barra
            lateral = (cm - P - t * (cm - P).dot(t)).Length
            if lateral < 4.0 * h and fora <= 0.5:
                cand.append((-fora, k, f.Area))
    if not cand:
        raise ValueError("não achei a face de apoio no nó (ponta da barra ou placa de base)")
    longe = max(c[0] for c in cand)
    faces = ["Face%d" % (k + 1) for dist, k, _a in cand if dist > longe - 0.05]
    txt = "face de baixo da placa de base, engastada" if longe > 0.5 else "ponta da barra no nó, engastada"
    return faces, txt


# ------------------------------------------------------------------ estudo do CalculiX
def criar_estudo(analise, det, tamanho=None):
    """Cria a peça "Detalhe" e um estudo FEM com material, engaste e esforços. Retorna PrumoFEM.Estudo."""
    import ObjectsFem
    import PrumoFEM as F
    doc = analise.Document
    peca = doc.addObject("Part::Feature", "Detalhe")
    peca.Shape = det.forma
    peca.Label = "Detalhe · nó (%s; %s; %s)" % (_f(det.ponto.x), _f(det.ponto.y), _f(det.ponto.z))
    an = ObjectsFem.makeAnalysis(doc, "DetalheFEM")
    an.Label = "Detalhe do nó (%s; %s; %s)" % (_f(det.ponto.x), _f(det.ponto.y), _f(det.ponto.z))
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
    # material
    nome = det.material[0]
    if "padrão" in nome:
        nome = "ASTM A36"
    escolhido = None
    for m in F.materiais():
        if m["nome"] == nome or (nome and nome.lower() in m["nome"].lower() and m["biblioteca"] == "Prumo"):
            escolhido = m
            break
    if escolhido is None:
        escolhido = next((m for m in F.materiais() if "A36" in m["nome"]), F.materiais()[0])
    mat = ObjectsFem.makeMaterialSolid(doc, "Material")
    an.addObject(mat)
    props = dict(escolhido["props"])
    props["YieldStrength"] = "%s MPa" % det.material[1]
    mat.Material = props
    mat.Label = "Material · " + escolhido["nome"]
    # engaste
    fx = ObjectsFem.makeConstraintFixed(doc, "Engaste")
    fx.References = [(peca, tuple(det.faces_fixas))]
    fx.Label = "Engaste · " + det.texto_fixo
    an.addObject(fx)
    # esforços nos cortes
    for c in det.cortes:
        if c["fixo"]:
            continue
        rb = ObjectsFem.makeConstraintRigidBody(doc, "Esforcos")
        rb.References = [(peca, tuple(c["faces"]))]
        rb.ReferenceNode = c["ponto"]
        for eixo, fv, mv in (("X", c["F"].x, c["M"].x), ("Y", c["F"].y, c["M"].y), ("Z", c["F"].z, c["M"].z)):
            setattr(rb, "TranslationalMode" + eixo, "Load")
            setattr(rb, "RotationalMode" + eixo, "Load")
            setattr(rb, "Force" + eixo, "%.6f N" % fv)
            setattr(rb, "Moment" + eixo, "%.6f mm*N" % mv)
        rb.Label = "Barra %d · corte a %s mm · F %s kN · M %s kN·m" % (
            c["linha"] + 1, _f(c["dist"]), _f(c["F"].Length / 1e3, 1), _f(c["M"].Length / 1e6, 2))
        an.addObject(rb)
    est.put("PrumoDetalhe", True, "App::PropertyBool")
    est.put("PrumoLadosRetos", True, "App::PropertyBool")
    est.put("PrumoOtimizarNetgen", True, "App::PropertyBool")
    est.put("PrumoZonaCentro", det.ponto, "App::PropertyVector")
    est.put("PrumoZonaRaio", float(det.raio_zona), "App::PropertyFloat")
    est.put("PrumoGamaA1", GAMA_A1, "App::PropertyFloat")
    est.put("PrumoCombinacao", det.combinacao)
    est.put("PrumoAvisos", list(det.avisos), "App::PropertyStringList")
    import json as _json
    est.put("PrumoLigacoes", _json.dumps([{"texto": x["texto"], "taxa": x["taxa"], "tipo": x["tipo"]}
                                          for x in det.ligacoes]))
    est.put("PrumoAnaliseBarras", analise.Name)
    if tamanho is None:
        tamanho = min(max(det.espessura, 4.0), 20.0)
    est.put("PrumoMalhaSugerida", float(tamanho), "App::PropertyFloat")
    doc.recompute()
    return est


def detalhar(analise, ponto, combinacao=None, distancia=0.0, tamanho=None, calcular=True, progresso=None):
    """montar + criar_estudo + malha + cálculo. Retorna (estudo, detalhe, erro ou "")."""
    import PrumoFEM as F
    det = montar(analise, ponto, combinacao, distancia)
    est = criar_estudo(analise, det, tamanho)
    if not calcular:
        return est, det, ""
    if progresso:
        progresso("Gerando a malha…")
    ok, msg = F.gerar_malha(est, est.get("PrumoMalhaSugerida", 8.0), "2nd")
    if not ok:
        return est, det, msg
    if progresso:
        progresso("Calculando no CalculiX…")
    ok, erro, _dt = F.calcular(est)
    if ok:
        try:
            import json
            est.put("PrumoConferencia", json.dumps(conferencia(analise, det, est)))
        except Exception as ex:
            FreeCAD.Console.PrintWarning("Prumo: conferência do detalhe: %s\n" % ex)
    return est, det, ("" if ok else erro)


def conferencia(analise, det, est):
    """Tensão normal máxima na seção a meio caminho entre o nó e cada corte: sólido x barras."""
    import numpy as np
    calc = _calc(analise)
    r = calc.resultados[det.combinacao]
    res = est.resultados[0]
    nos = res.Mesh.FemMesh.Nodes
    tens = list(zip(res.NodeNumbers, res.NodeStressXX, res.NodeStressYY, res.NodeStressZZ, res.NodeStressXY,
                    res.NodeStressXZ, res.NodeStressYZ))
    out = []
    for c in det.cortes:
        i = c["linha"]
        p0, t, L = calc.mapa["linhas"][i]
        s0 = (det.ponto - p0).dot(t)
        sm = (s0 + c["s"]) / 2.0
        eb, x = _elemento_em(calc, i, sm)
        e = r.esforcos(eb, x)
        pr = calc.mapa["secoes"][i]
        teo = abs(e["N"]) / pr["A"] + abs(e["My"]) / pr["Wx"] + abs(e["Mz"]) / pr["Wy"]
        q = p0 + t * sm
        tv = np.array([t.x, t.y, t.z])
        tol = max(2.0, 0.6 * det.espessura)
        mx = 0.0
        for n, sxx, syy, szz, sxy, sxz, syz in tens:
            p = nos[n]
            if abs((p - q).dot(t)) < tol:
                S = np.array([[sxx, sxy, sxz], [sxy, syy, syz], [sxz, syz, szz]])
                mx = max(mx, abs(float(tv @ S @ tv)))
        out.append({"barra": i + 1, "pos": abs(sm - s0), "fem": mx, "barra_mpa": teo})
    return out


def tensao_na_zona(est):
    """(σ von Mises máx. na zona de interesse, σ máx. total) em MPa."""
    res = est.resultados
    if not res:
        return None, None
    r = res[0]
    c = est.get("PrumoZonaCentro", None)
    raio = est.get("PrumoZonaRaio", 0.0)
    total = max(r.vonMises) if r.vonMises else None
    if c is None or not raio:
        return total, total
    nos = r.Mesh.FemMesh.Nodes
    zona = 0.0
    for n, s in zip(r.NodeNumbers, r.vonMises):
        p = nos.get(n)
        if p is not None and (p - c).Length <= raio:
            zona = max(zona, s)
    return zona, total
