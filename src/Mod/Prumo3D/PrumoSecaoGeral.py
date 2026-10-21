# SPDX-License-Identifier: LGPL-2.1-or-later
"""Propriedades de seção qualquer (seção personalizada) por elementos finitos triangulares.

- Função de empenamento ω de Saint-Venant (Laplace com ∂ω/∂n = y·nx − x·ny no contorno), resolvida
  com triângulos lineares: dá J, o centro de cisalhamento (x0, y0) e a constante de empenamento Cw.
- Coeficientes de Wagner βx, βy nos eixos principais (para Mcr de seções monossimétricas e
  assimétricas).
- Chapas: pares de lados paralelos e próximos do contorno (paredes), com o tipo de apoio das bordas
  (AA: presa nas duas pontas; AL: uma ponta livre), para a flambagem local.

Coordenadas: u (largura) e v (altura) do contorno, como em PrumoSecao; os resultados (x0, y0) são em
relação ao centróide, nos eixos u, v.
"""
import math

import numpy as np


# ------------------------------------------------------------------ malha
def malha(ext, furos, tamanho=None):
    """(nós N×2, triângulos M×3) da seção (furos excluídos), pela malha de superfície do FreeCAD."""
    import FreeCAD as App
    import MeshPart
    import Part

    def face(pts):
        v = [App.Vector(x, y, 0) for x, y in pts]
        return Part.Face(Part.makePolygon(v + [v[0]]))
    f = face(ext)
    for h in furos:
        f = f.cut(face(h))
    if not f.Faces:
        raise ValueError("seção vazia")
    us = [p[0] for p in ext]
    vs = [p[1] for p in ext]
    tmin = espessura_minima(ext, furos)
    if tamanho is None:
        tamanho = max(min(tmin / 4.0, math.sqrt(abs(f.Area)) / 25.0), 0.2)
    m = None
    for kw in (dict(MaxLength=tamanho), dict(Fineness=2, SecondOrder=0, Optimize=1, AllowQuad=0,
                                             MaxLength=tamanho)):
        try:
            m = MeshPart.meshFromShape(Shape=f, **kw)
            if m.CountFacets:
                break
        except Exception:
            m = None
    if m is None or not m.CountFacets:
        raise ValueError("não foi possível gerar a malha da seção")
    pts, tri = m.Topology
    nos = np.array([(p.x, p.y) for p in pts])
    tri = np.array(tri, dtype=int)
    # orientação anti-horária
    a = _areas(nos, tri)
    tri[a < 0] = tri[a < 0][:, [0, 2, 1]]
    keep = np.abs(a) > 1e-12 * (max(us) - min(us)) * (max(vs) - min(vs))
    return nos, tri[keep]


def _areas(nos, tri):
    p0, p1, p2 = nos[tri[:, 0]], nos[tri[:, 1]], nos[tri[:, 2]]
    return 0.5 * ((p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p2[:, 0] - p0[:, 0]) * (p1[:, 1] - p0[:, 1]))


# ------------------------------------------------------------------ empenamento
def empenamento(ext, furos, tamanho=None):
    """dict: A, cu, cv, Ix, Iy, Ixy (centroidais), J, x0, y0 (centro de cisalhamento − centróide),
    Cw, e os coeficientes de Wagner nos eixos principais (beta1, beta2) e o ângulo theta."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    nos, tri = malha(ext, furos, tamanho)
    A_e = _areas(nos, tri)
    A = A_e.sum()
    c = nos[tri].mean(axis=1)                       # centróides dos triângulos
    cu = (A_e * c[:, 0]).sum() / A
    cv = (A_e * c[:, 1]).sum() / A
    X = nos[:, 0] - cu
    Y = nos[:, 1] - cv
    x, y = X[tri], Y[tri]                           # M×3
    # integrais exatas de produtos de funções lineares: ∫fg = A/12 (Σfi gi + Σfi Σgi)
    def int2(f, g):
        return (A_e / 12.0 * ((f * g).sum(axis=1) + f.sum(axis=1) * g.sum(axis=1))).sum()
    Ixx = int2(y, y)
    Iyy = int2(x, x)
    Ixy = int2(x, y)
    # rigidez e carga do problema de empenamento
    b = np.stack([y[:, 1] - y[:, 2], y[:, 2] - y[:, 0], y[:, 0] - y[:, 1]], axis=1) / (2 * A_e[:, None])
    cc = np.stack([x[:, 2] - x[:, 1], x[:, 0] - x[:, 2], x[:, 1] - x[:, 0]], axis=1) / (2 * A_e[:, None])
    ke = (b[:, :, None] * b[:, None, :] + cc[:, :, None] * cc[:, None, :]) * A_e[:, None, None]
    xm, ym = x.mean(axis=1), y.mean(axis=1)
    fe = (b * ym[:, None] - cc * xm[:, None]) * A_e[:, None]
    n = len(nos)
    I = np.repeat(tri, 3, axis=1).ravel()
    Jx = np.tile(tri, (1, 3)).ravel()
    K = sp.coo_matrix((ke.ravel(), (I, Jx)), shape=(n, n)).tocsr()
    F = np.zeros(n)
    np.add.at(F, tri.ravel(), fe.ravel())
    # ω definido a menos de constante: fixa o nó 0
    livres = np.arange(1, n)
    w = np.zeros(n)
    w[livres] = spl.spsolve(K[livres][:, livres].tocsc(), F[livres])
    J = Ixx + Iyy - w @ (K @ w)
    W = w[tri]
    Iw = (A_e / 3.0 * W.sum(axis=1)).sum()
    Iwx = int2(W, x)
    Iwy = int2(W, y)
    # centro de cisalhamento (a, b): ∫ω' x = ∫ω' y = 0 com ω' = ω − b·x + a·y
    M = np.array([[Ixy, -Iyy], [Ixx, -Ixy]])
    a_, b_ = np.linalg.solve(M, [-Iwx, -Iwy])
    w2 = w - b_ * X + a_ * Y
    W2 = w2[tri]
    Iw2 = (A_e / 3.0 * W2.sum(axis=1)).sum()
    Cw = int2(W2, W2) - Iw2 ** 2 / A
    # eixos principais (theta do eixo 1, de maior inércia, em relação a u)
    th = 0.5 * math.atan2(-2 * Ixy, Ixx - Iyy) if abs(Ixy) > 1e-9 * max(Ixx, Iyy) else 0.0
    if Iyy > Ixx and abs(Ixy) <= 1e-9 * max(Ixx, Iyy):
        th = 0.0
    cs, sn = math.cos(th), math.sin(th)
    # coordenadas principais: x1 ao longo do eixo 1, y1 perpendicular (flexão em torno de 1 ↔ y1)
    x1 = x * cs + y * sn
    y1 = -x * sn + y * cs
    I1 = int2(y1, y1)
    I2 = int2(x1, x1)
    x0p = a_ * cs + b_ * sn
    y0p = -a_ * sn + b_ * cs
    # Wagner: β1 = (1/I1) ∫ y1 (x1² + y1²) dA − 2 y0 (flexão em torno do eixo 1); quadratura de grau 2
    # nos pontos médios dos lados (exata para quadráticas; cúbicas: erro pequeno com malha fina)
    def int3(fx, fy):
        tot = 0.0
        for i, j in ((0, 1), (1, 2), (2, 0)):
            xm_ = (fx[:, i] + fx[:, j]) / 2.0
            ym_ = (fy[:, i] + fy[:, j]) / 2.0
            tot = tot + A_e / 3.0 * ym_ * (xm_ ** 2 + ym_ ** 2)
        return tot.sum()
    beta1 = int3(x1, y1) / I1 - 2 * y0p if I1 > 0 else 0.0
    beta2 = int3(-y1, x1) / I2 - 2 * x0p if I2 > 0 else 0.0
    return {"A": A, "cu": cu, "cv": cv, "Ix": Ixx, "Iy": Iyy, "Ixy": Ixy, "J": J, "x0": a_, "y0": b_,
            "Cw": max(Cw, 0.0), "theta": th, "I1": I1, "I2": I2, "x0p": x0p, "y0p": y0p,
            "beta1": beta1, "beta2": beta2, "nos": len(nos), "tri": len(tri)}


# ------------------------------------------------------------------ chapas (paredes)
def _lados(ext, furos):
    res = []
    for pol in [ext] + list(furos):
        n = len(pol)
        for i in range(n):
            p, q = np.array(pol[i], float), np.array(pol[(i + 1) % n], float)
            L = np.linalg.norm(q - p)
            if L > 1e-9:
                res.append((p, q, L))
    return res


def espessura_minima(ext, furos):
    ch = chapas(ext, furos)
    if ch:
        return min(c["t"] for c in ch)
    us = [p[0] for p in ext]
    vs = [p[1] for p in ext]
    return min(max(us) - min(us), max(vs) - min(vs))


def chapas(ext, furos, esbeltez_min=3.0):
    """Paredes da seção: [{b, t, apoiada_nas_duas, direcao (vetor unitário ao longo de b)}].

    Uma parede é um par de lados paralelos, de sentidos opostos, frente a frente a uma distância t
    menor que o comprimento comum b/esbeltez_min. A ponta da parede é livre quando um lado curto
    (≈ t) fecha as duas faces ali; senão ela continua em outra parede (apoio)."""
    def _a2(pol):
        return 0.5 * sum(pol[i][0] * pol[(i + 1) % len(pol)][1] - pol[(i + 1) % len(pol)][0] * pol[i][1]
                         for i in range(len(pol)))
    ext = list(ext) if _a2(ext) > 0 else list(ext)[::-1]                 # externo anti-horário
    furos = [list(f) if _a2(f) < 0 else list(f)[::-1] for f in furos]    # furos horários
    lados = _lados(ext, furos)
    res = []
    usados = set()
    for i, (p, q, L) in enumerate(lados):
        d = (q - p) / L
        melhor = None
        for j, (r, s, L2) in enumerate(lados):
            if j == i:
                continue
            e = (s - r) / L2
            if d @ e > -0.999:          # paralelos e de sentidos opostos
                continue
            nrm = np.array([-d[1], d[0]])
            t = (r - p) @ nrm
            if t <= 1e-6:               # o outro lado precisa estar para dentro (contorno anti-horário)
                continue
            # trecho comum ao longo de d
            a0, a1 = 0.0, L
            b0, b1 = sorted(((r - p) @ d, (s - p) @ d))
            c0, c1 = max(a0, b0), min(a1, b1)
            b = c1 - c0
            if b <= 0 or b < esbeltez_min * t:
                continue
            if melhor is None or t < melhor[1]:
                melhor = (j, t, c0, c1)
        if melhor is None:
            continue
        j, t, c0, c1 = melhor
        chave = tuple(sorted((i, j)))
        if chave in usados:
            continue
        usados.add(chave)
        nrm = np.array([-d[1], d[0]])
        pontas = []
        for cpos in (c0, c1):
            a = p + d * cpos
            b_ = a + nrm * t
            pontas.append(_ponta_livre(a, b_, t, lados))
        livres = sum(pontas)
        b = c1 - c0
        if livres == 1:
            # borda presa: a largura vai até dentro da chapa de apoio (mesa de I: bf/2; aba de cantoneira:
            # aba inteira); soma-se t, a favor da segurança quando o apoio é mais fino
            b += t
        res.append({"b": b, "t": t, "apoiada_nas_duas": livres == 0, "livres": livres,
                    "direcao": (float(d[0]), float(d[1]))})
    return res


def _ponta_livre(a, b, t, lados, tol=0.25):
    """Há um lado ligando a e b (≈ perpendicular, comprimento ≈ t)? Então a ponta é livre."""
    for p, q, L in lados:
        if abs(L - t) > tol * t:
            continue
        for u, v in ((p, q), (q, p)):
            if np.linalg.norm(u - a) < tol * t and np.linalg.norm(v - b) < tol * t:
                return 1
    return 0
