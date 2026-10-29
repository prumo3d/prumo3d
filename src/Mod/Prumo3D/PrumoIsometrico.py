# SPDX-License-Identifier: LGPL-2.1-or-later
"""Folha isométrica de tubulação (para fabricação e montagem em campo).

Desenho unifilar em perspectiva isométrica (X para leste, Y para norte, Z para cima), sobre a folha ABNT A3:

- linha de centro de cada trecho, com a cota de centro a centro (mm);
- símbolos: solda de topo (ponto), junta roscada ou de bolsa (traço), flange, redução, cap, registro, união;
- número de cada peça (balão) ligado à lista de material, e etiqueta P1, P2… em cada tubo, ligada à lista
  de corte;
- à direita: lista de material, lista de corte, soldas de topo e observações.

O desenho é gerado de novo a cada chamada (a folha guarda o vínculo com a tubulação).
"""
import math

import FreeCAD

import PrumoCatalogoTubos as CAT

C30 = math.cos(math.radians(30.0))
S30 = 0.5

# área útil da folha A3 (coordenadas SVG em mm, y para baixo); legenda em x 230–410, y 229–287
AREA_DESENHO = (25.0, 18.0, 243.0, 282.0)
AREA_TABELAS = (250.0, 16.0, 405.0, 224.0)
FONTE = "sans-serif"
AZUL = "#003A70"


def projetar(p):
    """Ponto 3D → plano isométrico (y para cima)."""
    return ((p.x - p.y) * C30, (p.x + p.y) * S30 + p.z)


def _esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _fmt(v, casas=0):
    return (("%." + str(casas) + "f") % v).replace(".", ",")


# ------------------------------------------------------------------ dados da linha
def dados(obj):
    """Tudo o que a folha precisa, a partir do objeto Tubulação (recalcula)."""
    import PrumoTubulacao as T
    res = obj.Proxy.calcular(obj)
    L = res["linha"]
    lc = T.lista_de_corte(res.get("pecas", []), L)
    # lista de material: tubos primeiro, depois as conexões (com juntas e estojos)
    itens = []
    num_desc = {}
    for d in sorted(lc):
        r = lc[d]
        if L.get("nps"):
            desc = CAT.nome_peca(L, "tubo", dn=CAT.rotulo(L, d))
        else:
            desc = "Tubo %s %d mm" % (L.get("sufixo", ""), d)
        qtd = "%s m" % _fmt(r["total"] / 1000.0, 2)
        itens.append({"desc": " ".join(desc.split()), "qtd": qtd, "material": T.material_de(L, "tubo"),
                      "obs": "%d barra(s) de %s m" % (r["barras"], _fmt(L["barra"] / 1000.0, 0)), "dn": d})
    for desc, n in T.resumo_conexoes(res["conexoes"]).items():
        num_desc[desc] = len(itens) + 1
        itens.append({"desc": desc, "qtd": "%d" % n, "material": T.material_de(L, desc), "obs": ""})
    for i, it in enumerate(itens):
        it["item"] = i + 1
    item_tubo = {it["dn"]: it["item"] for it in itens if "dn" in it}
    # peças de tubo (lista de corte): P1, P2… na ordem dos trechos
    tubos = []
    for k, t in enumerate(res["tubos"]):
        tubos.append({"id": "P%d" % (k + 1), "ini": t["ini"], "fim": t["fim"], "dn": t["dn"],
                      "corte": t["corte"], "trecho": t["seg"] + 1, "item": item_tubo.get(t["dn"])})
    return {"res": res, "linha": L, "itens": itens, "num_desc": num_desc, "tubos": tubos,
            "soldas": T.soldas_de_topo(res), "lc": lc}


# ------------------------------------------------------------------ desenho
class _Svg:
    def __init__(self):
        self.el = []

    def linha(self, a, b, larg=0.35, cor="#000", tracejado=None):
        extra = " stroke-dasharray='%s'" % tracejado if tracejado else ""
        self.el.append("<line x1='%.2f' y1='%.2f' x2='%.2f' y2='%.2f' stroke='%s' stroke-width='%.2f' "
                       "stroke-linecap='round'%s/>" % (a[0], a[1], b[0], b[1], cor, larg, extra))

    def poli(self, pts, larg=0.35, fechar=False, preencher="none"):
        d = " ".join("%.2f,%.2f" % p for p in pts)
        tag = "polygon" if fechar else "polyline"
        self.el.append("<%s points='%s' fill='%s' stroke='#000' stroke-width='%.2f' stroke-linejoin='round'/>"
                       % (tag, d, preencher, larg))

    def circulo(self, c, r, preencher="none", larg=0.25, cor="#000"):
        self.el.append("<circle cx='%.2f' cy='%.2f' r='%.2f' fill='%s' stroke='%s' stroke-width='%.2f'/>"
                       % (c[0], c[1], r, preencher, cor, larg))

    def retangulo(self, x, y, w, h, larg=0.25, preencher="none"):
        self.el.append("<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='%s' stroke='#000' "
                       "stroke-width='%.2f'/>" % (x, y, w, h, preencher, larg))

    def texto(self, p, t, tam=2.5, ancora="start", ang=0.0, negrito=False, cor="#000"):
        rot = " transform='rotate(%.2f %.2f %.2f)'" % (ang, p[0], p[1]) if abs(ang) > 0.01 else ""
        self.el.append("<text x='%.2f' y='%.2f' text-anchor='%s' style='font-size:%.2fpx;font-family:%s;"
                       "font-weight:%s;fill:%s'%s>%s</text>"
                       % (p[0], p[1], ancora, tam, FONTE, "bold" if negrito else "normal", cor, rot, _esc(t)))

    def svg(self, larg=420.0, alt=297.0):
        return ("<svg xmlns='http://www.w3.org/2000/svg' width='%gmm' height='%gmm' viewBox='0 0 %g %g'>%s</svg>"
                % (larg, alt, larg, alt, "".join(self.el)))


def _unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-9 else (1.0, 0.0)


def _dist_seg(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    q = (a[0] + ax * t, a[1] + ay * t)
    return math.hypot(p[0] - q[0], p[1] - q[1])


class _Folha:
    """Converte coordenadas do modelo para a folha e guarda o que já foi desenhado (para não sobrepor)."""

    def __init__(self, pontos3d):
        x0, y0, x1, y1 = AREA_DESENHO
        pr = [projetar(p) for p in pontos3d] or [(0.0, 0.0)]
        minx = min(p[0] for p in pr)
        maxx = max(p[0] for p in pr)
        miny = min(p[1] for p in pr)
        maxy = max(p[1] for p in pr)
        margem = 22.0          # cotas e balões ao redor
        w = max(maxx - minx, 1e-6)
        h = max(maxy - miny, 1e-6)
        self.k = min((x1 - x0 - 2 * margem) / w, (y1 - y0 - 2 * margem) / h)
        cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
        self.ox = (x0 + x1) / 2.0 - cx * self.k
        self.oy = (y0 + y1) / 2.0 + cy * self.k
        self.ocupado = []      # segmentos (a, b) e círculos (c, r) já desenhados

    def p(self, v):
        x, y = projetar(v)
        return (self.ox + x * self.k, self.oy - y * self.k)

    def dir(self, u):
        """Direção 3D → direção na folha (unitária)."""
        x, y = projetar(u)
        return _unit((x, -y))

    def ocupar_seg(self, a, b):
        self.ocupado.append(("s", a, b))

    def ocupar_circ(self, c, r):
        self.ocupado.append(("c", c, r))

    def folga(self, p, r=0.0):
        m = 1e9
        for o in self.ocupado:
            if o[0] == "s":
                m = min(m, _dist_seg(p, o[1], o[2]) - r)
            else:
                m = min(m, math.hypot(p[0] - o[1][0], p[1] - o[1][1]) - o[2] - r)
        x0, y0, x1, y1 = AREA_DESENHO
        m = min(m, p[0] - x0 - r, x1 - p[0] - r, p[1] - y0 - r, y1 - p[1] - r)
        return m


def _perp(d):
    return (-d[1], d[0])


def _marcas_no_trecho(res, a, b):
    """Distâncias (do início do trecho) das válvulas e dos pares de flanges no meio do trecho a→b."""
    comp = (b - a).Length
    if comp < 1.0:
        return []
    u = (b - a) * (1.0 / comp)
    out = []
    flanges = []
    for c in res["conexoes"]:
        if c.get("so_lista") or c["tipo"] not in ("Válvula", "Flange", "União", "Registro"):
            continue
        w = c["no"] - a
        t = w.dot(u)
        if (w - u * t).Length > 1.0 or t < 1.0 or t > comp - 1.0:
            continue
        if c["tipo"] == "Flange":
            flanges.append(t)
        else:
            out.append(t)
    # par de flanges solto (junta de desmontagem): o meio dos dois; os da válvula já estão na válvula
    flanges.sort()
    usados = set()
    for k in range(len(flanges) - 1):
        if k in usados:
            continue
        t1, t2 = flanges[k], flanges[k + 1]
        if t2 - t1 < 20.0 and not any(abs((t1 + t2) / 2.0 - v) < 400.0 and min(abs(t1 - v), abs(t2 - v)) < 400.0
                                       for v in out):
            out.append((t1 + t2) / 2.0)
            usados.update((k, k + 1))
    return sorted(round(t, 1) for t in out)


def _cota(S, F, pa, pb, dw, off, texto, ext_ini=False):
    """Cota de isométrico entre dois pontos da folha, afastada `off` mm na direção dw."""
    ca = (pa[0] + dw[0] * off, pa[1] + dw[1] * off)
    cb = (pb[0] + dw[0] * off, pb[1] + dw[1] * off)
    for p0, p1 in ((pa, ca), (pb, cb)):
        S.linha((p0[0] + dw[0] * 1.5, p0[1] + dw[1] * 1.5), (p1[0] + dw[0] * 1.5, p1[1] + dw[1] * 1.5), 0.18)
    S.linha(ca, cb, 0.18)
    dd = _unit((cb[0] - ca[0], cb[1] - ca[1]))
    n = _perp(dd)
    for p0, sg in ((ca, 1), (cb, -1)):      # traços oblíquos nas pontas (padrão de isométrico)
        S.linha((p0[0] - (dd[0] * sg - n[0]) * 1.0, p0[1] - (dd[1] * sg - n[1]) * 1.0),
                (p0[0] + (dd[0] * sg - n[0]) * 1.0, p0[1] + (dd[1] * sg - n[1]) * 1.0), 0.25)
    ang = math.degrees(math.atan2(dd[1], dd[0]))
    if ang > 90.0:
        ang -= 180.0
    elif ang <= -90.0:
        ang += 180.0
    meio = ((ca[0] + cb[0]) / 2.0, (ca[1] + cb[1]) / 2.0)
    # "para cima" do texto girado; o texto fica do lado de fora (longe do tubo)
    a_r = math.radians(ang)
    cima = (math.sin(a_r), -math.cos(a_r))
    if cima[0] * dw[0] + cima[1] * dw[1] >= 0:
        tp = (meio[0] + cima[0] * 0.8, meio[1] + cima[1] * 0.8)
    else:
        tp = (meio[0] - cima[0] * 3.0, meio[1] - cima[1] * 3.0)
    S.texto(tp, texto, 2.5 if off < 10 else 2.2, "middle", ang)
    F.ocupar_seg(ca, cb)
    F.ocupar_circ(meio, 4.0)


def desenhar(info, titulo=""):
    """SVG da folha inteira (420 × 297 mm): isométrico à esquerda, tabelas à direita."""
    res, L = info["res"], info["linha"]
    segs = res.get("segs") or []
    pts = [a for a, b in segs] + [b for a, b in segs]
    F = _Folha(pts)
    S = _Svg()
    solda_topo = bool(L.get("solda_topo"))
    # linhas de centro
    for a, b in segs:
        pa, pb = F.p(a), F.p(b)
        S.linha(pa, pb, 0.7)
        F.ocupar_seg(pa, pb)
    # juntas (soldas de topo como ponto; rosca/bolsa como traço) e símbolos das conexões
    centro3 = FreeCAD.Vector()
    for q in pts:
        centro3 += q
    centro3 = centro3 * (1.0 / max(1, len(pts)))
    centro = F.p(centro3)
    for c in res["conexoes"]:
        if c.get("so_lista") or c["tipo"] == "Caixa":
            continue
        no = c["no"]
        for s_, p_, u, dd, cf in c["pernas"]:
            if s_ < 0 or cf <= 0:
                continue
            ponta = F.p(no + u * cf)
            d = F.dir(u)
            if c["tipo"] == "Válvula":
                continue
            if solda_topo:
                S.circulo(ponta, 0.75, "#000")
            elif c["tipo"] not in ("Flange", "União"):
                n = _perp(d)
                S.linha((ponta[0] - n[0] * 1.4, ponta[1] - n[1] * 1.4), (ponta[0] + n[0] * 1.4, ponta[1] + n[1] * 1.4), 0.35)
        pn = F.p(no)
        if c["tipo"] == "Flange":
            u = c["pernas"][0][2]
            d = F.dir(u)
            n = _perp(d)
            for off in (0.0, 0.9):
                q = (pn[0] + d[0] * off, pn[1] + d[1] * off)
                S.linha((q[0] - n[0] * 3.0, q[1] - n[1] * 3.0), (q[0] + n[0] * 3.0, q[1] + n[1] * 3.0), 0.5)
        elif c["tipo"] == "Luva de redução":
            (_s1, _p1, u1, d1, a1), (_s2, _p2, u2, d2, a2) = c["pernas"][:2]
            if d1 < d2:
                u1, u2, d1, d2 = u2, u1, d2, d1
            dv = F.dir(u2)
            n = _perp(dv)
            ini = (pn[0] - dv[0] * 2.0, pn[1] - dv[1] * 2.0)
            fim = (pn[0] + dv[0] * 2.0, pn[1] + dv[1] * 2.0)
            S.poli([(ini[0] + n[0] * 2.2, ini[1] + n[1] * 2.2), (fim[0] + n[0] * 1.1, fim[1] + n[1] * 1.1),
                    (fim[0] - n[0] * 1.1, fim[1] - n[1] * 1.1), (ini[0] - n[0] * 2.2, ini[1] - n[1] * 2.2)],
                   0.4, True, "#fff")
        elif c["tipo"] == "Cap":
            u = c["pernas"][0][2]
            d = F.dir(u)
            n = _perp(d)
            q = (pn[0] - d[0] * 1.0, pn[1] - d[1] * 1.0)
            S.linha((q[0] - n[0] * 2.0, q[1] - n[1] * 2.0), (q[0] + n[0] * 2.0, q[1] + n[1] * 2.0), 1.0)
        elif c["tipo"] == "Registro":
            u = c["pernas"][0][2]
            d = F.dir(u)
            n = _perp(d)
            a_ = (pn[0] - d[0] * 3.0, pn[1] - d[1] * 3.0)
            b_ = (pn[0] + d[0] * 3.0, pn[1] + d[1] * 3.0)
            S.poli([(a_[0] + n[0] * 2.0, a_[1] + n[1] * 2.0), (b_[0] - n[0] * 2.0, b_[1] - n[1] * 2.0),
                    (b_[0] + n[0] * 2.0, b_[1] + n[1] * 2.0), (a_[0] - n[0] * 2.0, a_[1] - n[1] * 2.0)],
                   0.4, True, "#fff")
        elif c["tipo"] == "Válvula":
            u = c["pernas"][0][2]
            d = F.dir(u)
            n = _perp(d)
            tipo = c["valvula"]["tipo"]
            a_ = (pn[0] - d[0] * 3.2, pn[1] - d[1] * 3.2)
            b_ = (pn[0] + d[0] * 3.2, pn[1] + d[1] * 3.2)
            t1 = [(a_[0] + n[0] * 2.2, a_[1] + n[1] * 2.2), (pn[0], pn[1]), (a_[0] - n[0] * 2.2, a_[1] - n[1] * 2.2)]
            t2 = [(b_[0] + n[0] * 2.2, b_[1] + n[1] * 2.2), (pn[0], pn[1]), (b_[0] - n[0] * 2.2, b_[1] - n[1] * 2.2)]
            S.poli(t1, 0.4, True, "#fff")
            S.poli(t2, 0.4, True, "#000" if tipo == "retencao" else "#fff")
            for q in (a_, b_):             # faces flangeadas da válvula
                S.linha((q[0] - n[0] * 2.8, q[1] - n[1] * 2.8), (q[0] + n[0] * 2.8, q[1] + n[1] * 2.8), 0.5)
            if tipo == "globo":
                S.circulo(pn, 0.9, "#000")
            elif tipo == "esfera":
                S.circulo(pn, 1.1, "#fff", 0.35)
            if tipo in ("gaveta", "globo"):            # haste do volante
                S.linha(pn, (pn[0] - n[0] * 4.0, pn[1] - n[1] * 4.0), 0.35)
                S.linha((pn[0] - n[0] * 4.0 - d[0] * 1.8, pn[1] - n[1] * 4.0 - d[1] * 1.8),
                        (pn[0] - n[0] * 4.0 + d[0] * 1.8, pn[1] - n[1] * 4.0 + d[1] * 1.8), 0.5)
        elif c["tipo"] == "União":
            u = c["pernas"][0][2]
            d = F.dir(u)
            n = _perp(d)
            for off in (-0.6, 0.6):
                q = (pn[0] + d[0] * off, pn[1] + d[1] * off)
                S.linha((q[0] - n[0] * 2.0, q[1] - n[1] * 2.0), (q[0] + n[0] * 2.0, q[1] + n[1] * 2.0), 0.4)
        F.ocupar_circ(pn, 2.5)
    # cotas de centro a centro, uma por trecho do traçado
    for i, (a, b) in enumerate(segs):
        comp = (b - a).Length
        if comp < 1.0:
            continue
        u = (b - a) * (1.0 / comp)
        cands = []
        for w in (FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0)):
            if abs(w.dot(u)) < 0.2:
                for sg in (1, -1):
                    cands.append(w * sg)
        if not cands:
            cands = [FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(0, 0, -1)]
        melhor = None
        for w in cands:
            dw = F.dir(w)
            pa, pb = F.p(a), F.p(b)
            ca = (pa[0] + dw[0] * 7.0, pa[1] + dw[1] * 7.0)
            cb = (pb[0] + dw[0] * 7.0, pb[1] + dw[1] * 7.0)
            meio = ((ca[0] + cb[0]) / 2.0, (ca[1] + cb[1]) / 2.0)
            # o lado de fora do desenho primeiro; depois o mais livre
            fora = (meio[0] - centro[0]) * dw[0] + (meio[1] - centro[1]) * dw[1]
            amostra = [(ca[0] + (cb[0] - ca[0]) * t_, ca[1] + (cb[1] - ca[1]) * t_) for t_ in (0.1, 0.3, 0.5, 0.7, 0.9)]
            sc = min(min(F.folga(q_, 0.5) for q_ in amostra), 6.0) + (1.5 if fora > 0 else 0.0)
            if melhor is None or sc > melhor[0]:
                melhor = (sc, dw, ca, cb, pa, pb)
        _sc, dw, ca, cb, pa, pb = melhor
        _cota(S, F, pa, pb, dw, 7.0, _fmt(comp, 0))
        # válvulas e juntas no meio do trecho: cota em cadeia na segunda linha (onde fica cada uma)
        marcas = _marcas_no_trecho(res, a, b)
        if marcas:
            pts = [a] + [a + u * m for m in marcas] + [b]
            for k in range(len(pts) - 1):
                _cota(S, F, F.p(pts[k]), F.p(pts[k + 1]), dw, 13.0, _fmt((pts[k + 1] - pts[k]).Length, 0),
                      ext_ini=(k > 0))
    # etiquetas dos tubos (lista de corte)
    for t in info["tubos"]:
        m3 = (t["ini"] + t["fim"]) * 0.5
        pm = F.p(m3)
        d = F.dir(t["fim"] - t["ini"])
        n = _perp(d)
        melhor = None
        for sg in (1, -1):
            q = (pm[0] + n[0] * 4.0 * sg, pm[1] + n[1] * 4.0 * sg)
            sc = F.folga(q, 2.5)
            if melhor is None or sc > melhor[0]:
                melhor = (sc, q)
        q = melhor[1]
        w = 2.2 + 1.5 * len(t["id"])
        S.retangulo(q[0] - w / 2.0, q[1] - 2.0, w, 3.6, 0.2, "#fff")
        S.texto((q[0], q[1] + 0.9), t["id"], 2.3, "middle")
        F.ocupar_circ(q, 2.6)
    # balões das conexões (número do item da lista de material); peças iguais coladas (par de flanges) levam um
    postos = []
    for c in res["conexoes"]:
        if c.get("so_lista") or c["tipo"] == "Caixa":
            continue
        item = info["num_desc"].get(c["desc"])
        if item is None:
            continue
        pn = F.p(c["no"])
        if any(it == item and math.hypot(pn[0] - q_[0], pn[1] - q_[1]) < 6.0 for it, q_ in postos):
            continue
        postos.append((item, pn))
        melhor = None
        for k in range(16):
            ang = 2 * math.pi * k / 16.0
            for dist in (9.0, 13.0):
                q = (pn[0] + math.cos(ang) * dist, pn[1] + math.sin(ang) * dist)
                sc = F.folga(q, 3.0) - (0.15 * dist)
                if melhor is None or sc > melhor[0]:
                    melhor = (sc, q)
        q = melhor[1]
        d = _unit((pn[0] - q[0], pn[1] - q[1]))
        S.linha((q[0] + d[0] * 2.8, q[1] + d[1] * 2.8), (pn[0] - d[0] * 0.8, pn[1] - d[1] * 0.8), 0.18)
        S.circulo(q, 2.8, "#fff", 0.3)
        S.texto((q[0], q[1] + 0.9), str(item), 2.5, "middle")
        F.ocupar_circ(q, 2.8)
        F.ocupar_seg(q, pn)
    # rosa dos ventos: norte = +Y
    x0, y0 = AREA_DESENHO[0] + 10.0, AREA_DESENHO[1] + 12.0
    dn = F.dir(FreeCAD.Vector(0, 1, 0))
    de = F.dir(FreeCAD.Vector(1, 0, 0))
    S.linha((x0, y0), (x0 + dn[0] * 10.0, y0 + dn[1] * 10.0), 0.35)
    S.poli([(x0 + dn[0] * 11.5, y0 + dn[1] * 11.5), (x0 + dn[0] * 8.5 + _perp(dn)[0] * 1.2, y0 + dn[1] * 8.5 + _perp(dn)[1] * 1.2),
            (x0 + dn[0] * 8.5 - _perp(dn)[0] * 1.2, y0 + dn[1] * 8.5 - _perp(dn)[1] * 1.2)], 0.2, True, "#000")
    S.texto((x0 + dn[0] * 14.0, y0 + dn[1] * 14.0 + 1.0), "N", 3.0, "middle", negrito=True)
    S.linha((x0, y0), (x0 + de[0] * 7.0, y0 + de[1] * 7.0), 0.2, tracejado="1,0.8")
    S.texto((x0 + de[0] * 9.5, y0 + de[1] * 9.5 + 1.0), "L", 2.2, "middle")
    S.texto((AREA_DESENHO[0] + 2.0, AREA_DESENHO[3] - 2.0),
            "Isométrico sem escala: vale a cota. Cotas em mm, de eixo a eixo. Norte = +Y do modelo.", 2.0)
    _tabelas(S, info, titulo)
    return S.svg()


def _quebrar(txt, maxc):
    palavras = str(txt).split()
    linhas, atual = [], ""
    for w in palavras:
        if len(atual) + len(w) + (1 if atual else 0) > maxc and atual:
            linhas.append(atual)
            atual = w
        else:
            atual = (atual + " " + w) if atual else w
    if atual:
        linhas.append(atual)
    return linhas or [""]


def _tabelas(S, info, titulo):
    x0, y0, x1, y1 = AREA_TABELAS
    L = info["linha"]
    larg = x1 - x0
    # a fonte diminui até caber (2,5 → 1,8 mm)
    for tam in (2.5, 2.3, 2.1, 1.9, 1.8):
        el_ini = len(S.el)
        y = _desenhar_tabelas(S, info, titulo, x0, y0, larg, tam)
        if y <= y1 or tam == 1.8:
            break
        del S.el[el_ini:]


def _desenhar_tabelas(S, info, titulo, x0, y, larg, tam):
    L = info["linha"]
    lh = tam * 1.45
    cw = tam * 0.56            # largura média de um caractere

    def tabela(nome, colunas, linhas):
        nonlocal y
        S.retangulo(x0, y, larg, lh + 1.2, 0.3, AZUL)
        S.texto((x0 + 1.5, y + lh * 0.82 + 0.3), nome, tam, negrito=True, cor="#fff")
        y += lh + 1.2
        # cabeçalho
        x = x0
        for cab, w, _al in colunas:
            S.texto((x + 1.0, y + lh * 0.8), cab, tam * 0.9, negrito=True)
            x += w
        y += lh
        S.linha((x0, y), (x0 + larg, y), 0.25)
        for lin in linhas:
            quebradas = [_quebrar(v, max(4, int((w - 2.0) / cw))) for v, (_c, w, _a) in zip(lin, colunas)]
            n = max(len(q) for q in quebradas)
            x = x0
            for q, (_c, w, al) in zip(quebradas, colunas):
                for k, t in enumerate(q):
                    px = x + 1.0 if al == "start" else (x + w / 2.0 if al == "middle" else x + w - 1.0)
                    S.texto((px, y + lh * (k + 0.8)), t, tam, al)
                x += w
            y += lh * n + 0.6
            S.linha((x0, y), (x0 + larg, y), 0.12)
        S.retangulo(x0, y - 0.01, 0.01, 0.01, 0.0)
        y += 3.0

    cols = [("Item", 9.0, "middle"), ("Qtd.", 14.0, "middle"), ("Descrição", 84.0, "start"),
            ("Material", larg - 107.0, "start")]
    linhas = []
    for it in info["itens"]:
        desc = it["desc"] + ((" — " + it["obs"]) if it["obs"] else "")
        linhas.append((str(it["item"]), it["qtd"], desc, it["material"]))
    tabela("LISTA DE MATERIAL", cols, linhas)
    cols = [("Peça", 13.0, "middle"), ("Item", 11.0, "middle"), ("Diâmetro", 40.0, "start"),
            ("Corte (mm)", 26.0, "middle"), ("Trecho", larg - 90.0, "middle")]
    linhas = []
    for t in info["tubos"]:
        linhas.append((t["id"], str(t["item"] or "—"), CAT.rotulo(L, t["dn"]), _fmt(t["corte"], 0),
                       str(t["trecho"])))
    tabela("LISTA DE CORTE", cols, linhas)
    notas = ["Linha: %s." % L["nome"]]
    if info["soldas"]:
        notas.append("Soldas de topo: %d (inclui emendas de barra)." % info["soldas"])
    if L.get("flanges"):
        notas.append("Flanges classe %s; tubo cortado até a ponta de solda do pescoço, com o ressalto de 2 mm "
                     "e a junta de %s mm na conta." % (L.get("classe", ""), _fmt(L.get("junta_espessura", 0), 1)))
    notas.append("Comprimento de corte já desconta as conexões; acrescentar a folga de soldagem/rosca da "
                 "especificação de fabricação.")
    notas.append("Medidas: %s." % L["norma"])
    for a in info["res"].get("avisos", []):
        notas.append("Aviso: " + a)
    S.texto((x0, y + tam), "OBSERVAÇÕES", tam, negrito=True, cor=AZUL)
    y += tam * 1.6
    for nt in notas:
        for k, t in enumerate(_quebrar(nt, int(larg / cw))):
            y += lh
            S.texto((x0 + (0.0 if k == 0 else 2.0), y), ("• " if k == 0 else "") + t, tam * 0.92)
    return y


# ------------------------------------------------------------------ folha
def folha_de(obj):
    """Folha isométrica já criada para esta tubulação (ou None)."""
    for o in obj.Document.Objects:
        if o.TypeId == "TechDraw::DrawViewSymbol" and getattr(o, "PrumoIsoDe", None) is obj:
            for p in o.InList:
                if p.TypeId == "TechDraw::DrawPage":
                    return p, o
    return None


def criar_folha(obj, formato="A3"):
    """Cria (ou atualiza) a folha A3 com o isométrico da tubulação. Devolve a folha."""
    import PrumoFolhas
    doc = obj.Document
    info = dados(obj)
    titulo = "Isométrico — %s" % obj.Label
    svg = desenhar(info, titulo)
    ja = folha_de(obj)
    if ja:
        page, sim = ja
        sim.Symbol = svg
        doc.recompute()
        return page
    campos = {"titulo": titulo, "material": info["linha"]["material"], "escala": "Sem escala", "massa": ""}
    page = PrumoFolhas.nova_folha(doc, formato, campos=campos)
    page.Label = "Isométrico %s" % obj.Label
    sim = doc.addObject("TechDraw::DrawViewSymbol", "Isometrico")
    sim.Label = "Isométrico %s" % obj.Label
    sim.addProperty("App::PropertyLink", "PrumoIsoDe", "Prumo", "Tubulação desenhada")
    sim.PrumoIsoDe = obj
    sim.Symbol = svg
    page.addView(sim)
    sim.ScaleType = "Custom"
    sim.Scale = 72.0 / 25.4         # o TechDraw lê as unidades do símbolo em pontos: assim 1 unidade = 1 mm
    try:
        larg, alt = PrumoFolhas._tamanho_folha(page)
    except Exception:
        larg, alt = 420.0, 297.0
    sim.X = larg / 2.0
    sim.Y = alt / 2.0
    doc.recompute()
    if FreeCAD.GuiUp:
        try:
            page.ViewObject.show()
        except Exception:
            pass
    return page


if FreeCAD.GuiUp:
    import FreeCADGui

    import PrumoUtil

    def _tubulacao_escolhida():
        import PrumoTubulacao as T
        for s in FreeCADGui.Selection.getSelection():
            if T.e_tubulacao(s):
                return s
        doc = FreeCAD.ActiveDocument
        if doc is not None:
            ts = [o for o in doc.Objects if T.e_tubulacao(o)]
            if len(ts) == 1:
                return ts[0]
        return None

    class CmdIsometrico:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("tubulacao.svg"),
                    "MenuText": "Folha isométrica",
                    "ToolTip": "Folha A3 com o isométrico da tubulação: cotas de eixo a eixo, números das peças, "
                               "lista de material, lista de corte e soldas. Chamada de novo, atualiza a folha."}

        def IsActive(self):
            return _tubulacao_escolhida() is not None

        def Activated(self):
            obj = _tubulacao_escolhida()
            if obj is None:
                return
            page = criar_folha(obj)
            try:
                import PrumoFolhas
                PrumoFolhas._abrir_folha(page)
            except Exception:
                pass
