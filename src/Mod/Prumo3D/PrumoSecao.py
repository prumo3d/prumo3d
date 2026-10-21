# SPDX-License-Identifier: LGPL-2.1-or-later
"""Propriedades geométricas das seções do catálogo (para o cálculo de estruturas).

Eixos da seção (os mesmos do desenho da barra, PrumoPerfis.contorno):
- u = largura (horizontal no desenho da seção), v = altura;
- "x" é o eixo u (flexão em torno dele usa a altura v: maior inércia nos perfis I e U);
- "y" é o eixo v.

Unidades: mm, mm², mm³, mm⁴, mm⁶.

Perfis W/HP: a área e as inércias contam os raios de concordância alma-mesa (R do catálogo).
Perfis U e I americanos, cantoneiras e tubos: seção sem raios (as abas inclinadas e os cantos
arredondados não estão no catálogo) — valores um pouco menores que os de catálogo (a favor da
segurança na resistência, contra na rigidez). Por isso cada seção traz o campo "aproximada".
"""

import math

import PrumoPerfis


# ----------------------------------------------------------------- polígonos (fórmulas de Green)
def _area_centroide(pts):
    a = cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a *= 0.5
    if abs(a) < 1e-15:
        return 0.0, 0.0, 0.0
    return a, cx / (6.0 * a), cy / (6.0 * a)


def _segundos(pts):
    """(Ixx = ∫y², Iyy = ∫x², Ixy = ∫xy) em torno da origem (com sinal da orientação)."""
    ixx = iyy = ixy = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        ixx += (y0 * y0 + y0 * y1 + y1 * y1) * c
        iyy += (x0 * x0 + x0 * x1 + x1 * x1) * c
        ixy += (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0) * c
    return ixx / 12.0, iyy / 12.0, ixy / 24.0


def _orientar(pts, positivo=True):
    a = _area_centroide(pts)[0]
    if (a > 0) != positivo:
        return list(reversed(pts))
    return list(pts)


def _cortar(pts, eixo, valor, acima=True):
    """Parte do polígono com coordenada (eixo 0 = x, 1 = y) ≥ valor (acima) ou ≤ valor."""
    def dentro(p):
        return p[eixo] >= valor if acima else p[eixo] <= valor

    def corte(p, q):
        t = (valor - p[eixo]) / (q[eixo] - p[eixo])
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))

    res = []
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        if dentro(q):
            if not dentro(p):
                res.append(corte(p, q))
            res.append(q)
        elif dentro(p):
            res.append(corte(p, q))
    return res


def _arco(cx, cy, r, a0, a1, n=8):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


# ----------------------------------------------------------------- contornos com raios
def _poligonos(it):
    """[(pontos, sinal)] da seção: +1 cheio, -1 furo (u = largura, v = altura, centrada na caixa)."""
    t = it["tipo"]
    if t == "I" and it.get("R"):
        d, bf, tw, tf, R = it["d"], it["bf"], it["tw"], it["tf"], it["R"]
        a, b, w, f = bf / 2.0, d / 2.0, tw / 2.0, tf
        # contorno com os quatro raios alma-mesa (arcos tangentes à mesa e à alma)
        pts = [(-a, -b), (a, -b), (a, -b + f)]
        pts += _arco(w + R, -b + f + R, R, -math.pi / 2, -math.pi)[0:]
        pts += _arco(w + R, b - f - R, R, math.pi, math.pi / 2)
        pts += [(a, b - f), (a, b), (-a, b), (-a, b - f)]
        pts += _arco(-w - R, b - f - R, R, math.pi / 2, 0.0)
        pts += _arco(-w - R, -b + f + R, R, 0.0, -math.pi / 2)
        pts += [(-a, -b + f)]
        return [(_orientar(pts), 1)]
    ext, furos = PrumoPerfis.contorno(it)
    if isinstance(ext, tuple):
        return None
    return [(_orientar(ext), 1)] + [(_orientar(f), -1) for f in furos]


# ----------------------------------------------------------------- propriedades
def _plastico(pols, eixo, area):
    """Módulo plástico em torno do eixo (0: flexão com fibras em x → Zy; 1: fibras em y → Zx)."""
    coords = [p[eixo] for pts, _s in pols for p in pts]
    lo, hi = min(coords), max(coords)

    def area_acima(c):
        return sum(s * abs(_area_centroide(_cortar(pts, eixo, c, True))[0]) if len(_cortar(pts, eixo, c, True)) > 2
                   else 0.0 for pts, s in pols)

    for _ in range(80):    # linha neutra plástica: metade da área de cada lado
        m = (lo + hi) / 2.0
        if area_acima(m) > area / 2.0:
            lo = m
        else:
            hi = m
    c = (lo + hi) / 2.0
    z = 0.0
    for pts, s in pols:
        for acima in (True, False):
            p = _cortar(pts, eixo, c, acima)
            if len(p) < 3:
                continue
            a, cx, cy = _area_centroide(p)
            centro = cy if eixo == 1 else cx
            z += s * abs(a) * abs(centro - c)
    return z


def propriedades(perfil):
    """dict com A, Ix, Iy, Wx, Wy, Zx, Zy, rx, ry, J, Cw, I1, I2 (principais), rmin, centróide
    (cu, cv) em relação ao centro da caixa, x0/y0 (centro de cisalhamento em relação ao centróide),
    medidas para a flambagem local e 'aproximada'."""
    it = PrumoPerfis.perfil(perfil) if isinstance(perfil, str) else perfil
    if it is None:
        raise ValueError("perfil desconhecido: %s" % perfil)
    chave = it["nome"]
    if chave in _cache:
        return dict(_cache[chave])
    t = it["tipo"]
    p = {"nome": it["nome"], "tipo": t, "aproximada": not (t == "I" and it.get("R")) and t != "POL"}
    if t == "TUBO":
        D, e = it["D"], it["esp"]
        di = D - 2 * e
        A = math.pi * (D ** 2 - di ** 2) / 4.0
        I = math.pi * (D ** 4 - di ** 4) / 64.0
        p.update(A=A, Ix=I, Iy=I, Ixy=0.0, cu=0.0, cv=0.0, Wx=I / (D / 2), Wy=I / (D / 2),
                 Zx=(D ** 3 - di ** 3) / 6.0, Zy=(D ** 3 - di ** 3) / 6.0,
                 J=2 * I, Cw=0.0, D=D, t=e, aproximada=False)
    else:
        pols = _poligonos(it)
        A = cu = cv = 0.0
        for pts, s in pols:
            a, x, y = _area_centroide(pts)
            A += s * a
            cu += s * a * x
            cv += s * a * y
        cu /= A
        cv /= A
        ixx = iyy = ixy = 0.0
        for pts, s in pols:
            mov = [(x - cu, y - cv) for x, y in pts]
            a, b, c = _segundos(mov)
            ixx += s * a
            iyy += s * b
            ixy += s * c
        us = [x for pts, _s in pols for x, _y in pts]
        vs = [y for pts, _s in pols for _x, y in pts]
        p.update(A=A, Ix=ixx, Iy=iyy, Ixy=ixy, cu=cu, cv=cv,
                 Wx=ixx / max(max(vs) - cv, cv - min(vs)), Wy=iyy / max(max(us) - cu, cu - min(us)),
                 Zx=_plastico(pols, 1, A), Zy=_plastico(pols, 0, A))
        p.update(_torcao(it, p))
    m = (p["Ix"] + p["Iy"]) / 2.0
    r = math.sqrt(((p["Ix"] - p["Iy"]) / 2.0) ** 2 + p["Ixy"] ** 2)
    p["I1"], p["I2"] = m + r, m - r
    # eixos principais: ângulo th do eixo de maior inércia (I1) em relação a u (largura)
    p["theta"] = 0.5 * math.atan2(-2 * p["Ixy"], p["Ix"] - p["Iy"]) if abs(p["Ixy"]) > 1e-9 * p["Ix"] else 0.0
    if t == "TUBO":
        p["W1"] = p["W2"] = p["Wx"]
    else:
        # módulos elásticos nos eixos principais (cantoneira): distância máxima às fibras
        c, s_ = math.cos(p["theta"]), math.sin(p["theta"])
        pts = [(x - p["cu"], y - p["cv"]) for pol, _s in _poligonos(it) for x, y in pol]
        # coordenada ao longo do eixo de menor inércia (n2) e do de maior (n1)
        d1 = max(abs(-x * s_ + y * c) for x, y in pts)     # distância ao eixo 1 (flexão em torno de 1)
        d2 = max(abs(x * c + y * s_) for x, y in pts)      # distância ao eixo 2
        p["W1"] = p["I1"] / d1
        p["W2"] = p["I2"] / d2
    p["rx"] = math.sqrt(p["Ix"] / p["A"])
    p["ry"] = math.sqrt(p["Iy"] / p["A"])
    p["rmin"] = math.sqrt(max(p["I2"], 0.0) / p["A"])
    p.setdefault("x0", 0.0)
    p.setdefault("y0", 0.0)
    p.update(_elementos(it))
    p["massa_kgm"] = float(it["massa"])
    _cache[chave] = p
    return dict(p)


_cache = {}


def _torcao(it, p):
    """Constante de torção J, de empenamento Cw e centro de cisalhamento (x0, y0) em relação ao centróide.

    Fórmulas de perfis de paredes finas (Timoshenko & Gere; as mesmas usadas nos catálogos)."""
    t = it["tipo"]
    if t == "I":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        h0 = d - tf
        J = (2 * bf * tf ** 3 + (d - 2 * tf) * tw ** 3) / 3.0
        Iyf = tf * bf ** 3 / 12.0
        return {"J": J, "Cw": Iyf * h0 ** 2 / 2.0, "x0": 0.0, "y0": 0.0}
    if t == "U":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        h0 = d - tf
        b1 = bf - tw / 2.0
        J = (2 * b1 * tf ** 3 + h0 * tw ** 3) / 3.0
        Cw = tf * b1 ** 3 * h0 ** 2 / 12.0 * (3 * b1 * tf + 2 * h0 * tw) / (6 * b1 * tf + h0 * tw)
        e = 3 * b1 ** 2 * tf / (6 * b1 * tf + h0 * tw)     # da linha média da alma, para fora das abas
        alma_u = -bf / 2.0 + tw / 2.0                    # linha média da alma (u)
        return {"J": J, "Cw": Cw, "x0": (alma_u - e) - p["cu"], "y0": 0.0}
    if t == "L":
        s, e = it["aba"], it["esp"]
        J = (2 * s - e) * e ** 3 / 3.0
        canto = -s / 2.0 + e / 2.0                       # cruzamento das linhas médias das abas
        return {"J": J, "Cw": 0.0, "x0": canto - p["cu"], "y0": canto - p["cv"]}
    if t == "TQ":
        s, e = it["lado"], it["esp"]
        bm = s - e
        J = 4 * (bm * bm) ** 2 * e / (4 * bm)
        return {"J": J, "Cw": 0.0, "x0": 0.0, "y0": 0.0}
    if t == "POL":
        # seção personalizada: empenamento de Saint-Venant por elementos finitos (PrumoSecaoGeral) →
        # J, centro de cisalhamento, Cw e coeficientes de Wagner; se a malha falhar, J pela função de
        # Prandtl e Cw = 0 com o centro de cisalhamento no centróide (aviso na verificação)
        ext = [tuple(q) for q in it["contorno"]]
        furos = [[tuple(q) for q in f] for f in it.get("furos", [])]
        try:
            import PrumoSecaoGeral as SG
            g = SG.empenamento(ext, furos)
            return {"J": g["J"], "Cw": g["Cw"], "x0": g["x0"], "y0": g["y0"], "geral": g}
        except Exception as ex:
            import PrumoSecaoPersonalizada as SP
            return {"J": SP.constante_torcao(ext, furos), "Cw": 0.0, "x0": 0.0, "y0": 0.0,
                    "geral": None, "erro_geral": str(ex)}
    raise ValueError(t)


def _elementos(it):
    """Relações largura/espessura para a flambagem local (b/t das mesas, h/tw da alma, D/t)."""
    t = it["tipo"]
    if t == "I":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        h = d - 2 * tf - 2 * it.get("R", 0.0)
        return {"bt_mesa": (bf / 2.0) / tf, "h_tw": h / tw, "h": h, "tw": tw, "tf": tf, "bf": bf, "d": d}
    if t == "U":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        h = d - 2 * tf
        return {"bt_mesa": bf / tf, "h_tw": h / tw, "h": h, "tw": tw, "tf": tf, "bf": bf, "d": d}
    if t == "L":
        return {"bt_aba": it["aba"] / it["esp"], "b": it["aba"], "t": it["esp"]}
    if t == "TQ":
        s, e = it["lado"], it["esp"]
        b = s - 3 * e           # parte plana (raio externo ~ 1,5 t, a checar com o fabricante)
        return {"bt_parede": b / e, "b": s, "t": e, "h": b}
    if t == "POL":
        try:
            import PrumoSecaoGeral as SG
            ext = [tuple(q) for q in it["contorno"]]
            furos = [[tuple(q) for q in f] for f in it.get("furos", [])]
            return {"chapas": SG.chapas(ext, furos)}
        except Exception:
            return {"chapas": []}
    if t == "TUBO":
        return {"D_t": it["D"] / it["esp"]}
    return {}
