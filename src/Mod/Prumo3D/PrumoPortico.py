# SPDX-License-Identifier: LGPL-2.1-or-later
"""Cálculo de pórticos espaciais pelo método da rigidez direta (análise linear de 1ª ordem).

Unidades internas: N, mm, MPa (N/mm²). Cargas de entrada: kN, kN/m, kN·m (convertidas aqui).

Barras de Euler-Bernoulli com 6 graus de liberdade por nó (3 deslocamentos e 3 rotações). Eixos
locais da barra: x ao longo da barra; y e z nos eixos principais da seção (para perfis I e U,
z = altura do perfil e y = largura: a flexão "em torno de y" usa a maior inércia).

Hipóteses (vão para a memória de cálculo):
- análise elástica linear de 1ª ordem (sem efeito P-Δ), material elástico;
- barras ligadas rigidamente nos nós (sem rótulas internas);
- as barras ficam sobre as linhas do esqueleto (excentricidades do ponto de fixação desprezadas);
- deformação por cortante desprezada.
"""

import math

import numpy as np

G_GRAV = 9.80665e-3          # N/kg → peso em N por kg (1 kgf = 9,80665 N); massa_kgm·G_GRAV = N/mm


class Secao:
    """Rigidez da seção: A, Iy (maior, flexão no plano x-z local), Iz, J em mm."""

    def __init__(self, A, Iy, Iz, J, E=200000.0, Gc=77000.0, massa_kgm=0.0, nome=""):
        self.A, self.Iy, self.Iz, self.J = float(A), float(Iy), float(Iz), float(J)
        self.E, self.G = float(E), float(Gc)
        self.massa_kgm = float(massa_kgm)
        self.nome = nome


class Barra:
    """Barra entre os nós i e j. eixo_z: vetor que dá a direção do eixo local z (altura da seção)."""

    def __init__(self, i, j, secao, eixo_z, nome="", origem=None):
        self.i, self.j = int(i), int(j)
        self.secao = secao
        self.eixo_z = np.array(eixo_z, dtype=float)
        self.nome = nome
        self.origem = origem            # (índice da barra do Prumo, x inicial ao longo dela em mm)


class Caso:
    """Caso de carga: cargas nos nós, distribuídas e concentradas nas barras."""

    def __init__(self, nome, tipo="permanente", peso_proprio=False):
        self.nome = nome
        self.tipo = tipo
        self.peso_proprio = bool(peso_proprio)
        self.nos = []          # (nó, [Fx, Fy, Fz] kN, [Mx, My, Mz] kN·m) — eixos globais
        self.distribuidas = []  # (barra, [qx, qy, qz] kN/m, global=True)
        self.pontuais = []      # (barra, a em mm a partir do nó i, [Px, Py, Pz] kN, global=True)


class Modelo:
    def __init__(self):
        self.nos = []           # np.array([x, y, z]) mm
        self.barras = []
        self.apoios = {}        # nó: [6 bools] (ux, uy, uz, rx, ry, rz) travados

    def no(self, p, tol=1e-3):
        p = np.array(p, dtype=float)
        for k, q in enumerate(self.nos):
            if np.linalg.norm(q - p) < tol:
                return k
        self.nos.append(p)
        return len(self.nos) - 1

    # ------------------------------------------------------------ geometria da barra
    def eixos(self, b):
        """Matriz 3×3 com as linhas x, y, z locais (em coordenadas globais) e o comprimento."""
        pi, pj = self.nos[b.i], self.nos[b.j]
        x = pj - pi
        L = np.linalg.norm(x)
        if L < 1e-9:
            raise ValueError("barra %s com comprimento zero" % b.nome)
        x = x / L
        z = b.eixo_z - x * np.dot(b.eixo_z, x)
        if np.linalg.norm(z) < 1e-9:
            z = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
            z = z - x * np.dot(z, x)
        z = z / np.linalg.norm(z)
        y = np.cross(z, x)
        return np.vstack([x, y, z]), L

    @staticmethod
    def rigidez_local(s, L):
        E, G, A, Iy, Iz, J = s.E, s.G, s.A, s.Iy, s.Iz, s.J
        k = np.zeros((12, 12))
        ea = E * A / L
        gj = G * J / L
        k[0, 0] = k[6, 6] = ea
        k[0, 6] = k[6, 0] = -ea
        k[3, 3] = k[9, 9] = gj
        k[3, 9] = k[9, 3] = -gj
        # flexão no plano x-y (em torno de z): v, θz
        a, b, c, d = 12 * E * Iz / L ** 3, 6 * E * Iz / L ** 2, 4 * E * Iz / L, 2 * E * Iz / L
        for (r, cc, val) in ((1, 1, a), (1, 5, b), (1, 7, -a), (1, 11, b), (5, 5, c), (5, 7, -b), (5, 11, d),
                             (7, 7, a), (7, 11, -b), (11, 11, c)):
            k[r, cc] = k[cc, r] = val
        # flexão no plano x-z (em torno de y): w, θy
        a, b, c, d = 12 * E * Iy / L ** 3, 6 * E * Iy / L ** 2, 4 * E * Iy / L, 2 * E * Iy / L
        for (r, cc, val) in ((2, 2, a), (2, 4, -b), (2, 8, -a), (2, 10, -b), (4, 4, c), (4, 8, b), (4, 10, d),
                             (8, 8, a), (8, 10, b), (10, 10, c)):
            k[r, cc] = k[cc, r] = val
        return k

    @staticmethod
    def rigidez_geometrica(N, L):
        """Matriz geométrica (consistente) da barra com força normal N (tração +), eixos locais."""
        kg = np.zeros((12, 12))
        if N == 0:
            return kg
        c = N / L
        A = np.array([[6 / 5, L / 10, -6 / 5, L / 10], [L / 10, 2 * L * L / 15, -L / 10, -L * L / 30],
                      [-6 / 5, -L / 10, 6 / 5, -L / 10], [L / 10, -L * L / 30, -L / 10, 2 * L * L / 15]]) * c
        B = np.array([[6 / 5, -L / 10, -6 / 5, -L / 10], [-L / 10, 2 * L * L / 15, L / 10, -L * L / 30],
                      [-6 / 5, L / 10, 6 / 5, L / 10], [-L / 10, -L * L / 30, L / 10, 2 * L * L / 15]]) * c
        for M, idx in ((A, (1, 5, 7, 11)), (B, (2, 4, 8, 10))):
            for a, ia in enumerate(idx):
                for b, ib in enumerate(idx):
                    kg[ia, ib] += M[a, b]
        return kg

    @staticmethod
    def _T(R):
        T = np.zeros((12, 12))
        for n in range(4):
            T[3 * n:3 * n + 3, 3 * n:3 * n + 3] = R
        return T

    # ------------------------------------------------------------ cargas na barra (locais)
    def _cargas_locais(self, caso, nb, b, R, L):
        """[(qx, qy, qz) uniforme local N/mm], [(a, Px, Py, Pz) local N] da barra nb no caso."""
        dist, pont = [], []
        if caso.peso_proprio and b.secao.massa_kgm:
            q = np.array([0.0, 0.0, -b.secao.massa_kgm * G_GRAV])      # N/mm (kg/m · g = N/m = N/mm·1e-3)
            dist.append(R @ q)
        for (k, q, glob) in caso.distribuidas:
            if k == nb:
                q = np.array(q, dtype=float)          # kN/m = N/mm
                dist.append(R @ q if glob else q)
        for (k, a, P, glob) in caso.pontuais:
            if k == nb:
                P = np.array(P, dtype=float) * 1000.0
                pont.append((float(a), R @ P if glob else P))
        return dist, pont

    @staticmethod
    def _engaste_perfeito(dist, pont, L):
        """Forças de engaste perfeito (12) em eixos locais, para cargas uniformes e concentradas."""
        f = np.zeros(12)
        for q in dist:
            qx, qy, qz = q
            f[0] += -qx * L / 2
            f[6] += -qx * L / 2
            f[1] += -qy * L / 2
            f[7] += -qy * L / 2
            f[5] += -qy * L ** 2 / 12
            f[11] += qy * L ** 2 / 12
            f[2] += -qz * L / 2
            f[8] += -qz * L / 2
            f[4] += qz * L ** 2 / 12
            f[10] += -qz * L ** 2 / 12
        for a, P in pont:
            a = min(max(a, 0.0), L)
            b = L - a
            Px, Py, Pz = P
            f[0] += -Px * b / L
            f[6] += -Px * a / L
            f[1] += -Py * b * b * (3 * a + b) / L ** 3
            f[7] += -Py * a * a * (a + 3 * b) / L ** 3
            f[5] += -Py * a * b * b / L ** 2
            f[11] += Py * a * a * b / L ** 2
            f[2] += -Pz * b * b * (3 * a + b) / L ** 3
            f[8] += -Pz * a * a * (a + 3 * b) / L ** 3
            f[4] += Pz * a * b * b / L ** 2
            f[10] += -Pz * a * a * b / L ** 2
        return f

    # ------------------------------------------------------------ solução
    def resolver(self, caso_ou_combinacao, segunda_ordem=False):
        """Resolve um caso ou uma combinação [(caso, fator)]. Retorna Resultado.

        segunda_ordem=True: análise P-Δ (rigidez geométrica, iterada até convergir); o resultado
        traz o fator de amplificação dos deslocamentos (2ª ordem / 1ª ordem)."""
        partes = caso_ou_combinacao if isinstance(caso_ou_combinacao, (list, tuple)) else [(caso_ou_combinacao, 1.0)]
        n = len(self.nos)
        ndof = 6 * n
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)
        info = []
        for nb, b in enumerate(self.barras):
            R, L = self.eixos(b)
            T = self._T(R)
            k = self.rigidez_local(b.secao, L)
            kg = T.T @ k @ T
            idx = list(range(6 * b.i, 6 * b.i + 6)) + list(range(6 * b.j, 6 * b.j + 6))
            K[np.ix_(idx, idx)] += kg
            dist_t, pont_t, fe_t = [], [], np.zeros(12)
            for caso, fator in partes:
                dist, pont = self._cargas_locais(caso, nb, b, R, L)
                dist = [q * fator for q in dist]
                pont = [(a, P * fator) for a, P in pont]
                fe_t += self._engaste_perfeito(dist, pont, L)
                dist_t += dist
                pont_t += pont
            F[idx] -= T.T @ fe_t
            info.append((R, L, T, k, fe_t, dist_t, pont_t, idx))
        for caso, fator in partes:
            for (no, forca, momento) in caso.nos:
                F[6 * no:6 * no + 3] += np.array(forca, dtype=float) * 1000.0 * fator
                F[6 * no + 3:6 * no + 6] += np.array(momento, dtype=float) * 1e6 * fator
        presos = np.zeros(ndof, dtype=bool)
        for no, travas in self.apoios.items():
            for g in range(6):
                if travas[g]:
                    presos[6 * no + g] = True
        livres = ~presos
        if not presos.any():
            raise ValueError("a estrutura não tem apoios: clique nos nós para apoiar")
        Kff = K[np.ix_(livres, livres)]
        # nós sem barra ou graus sem rigidez (ex.: rotação de nó só de treliça) ficam travados
        diag = np.abs(np.diag(Kff))
        if (diag < 1e-9 * max(1.0, diag.max())).any():
            raise ValueError("há graus de liberdade sem rigidez (nó solto?)")
        try:
            uf = np.linalg.solve(Kff, F[livres])
        except np.linalg.LinAlgError:
            raise ValueError("a estrutura é instável (mecanismo): faltam apoios ou travamentos")
        if not np.all(np.isfinite(uf)) or np.linalg.cond(Kff) > 1e15:
            raise ValueError("a estrutura é instável (mecanismo): faltam apoios ou travamentos")
        u = np.zeros(ndof)
        u[livres] = uf
        u1 = u.copy()
        kgs = [np.zeros((12, 12)) for _ in info]
        iteracoes = 0
        if segunda_ordem:
            for iteracoes in range(1, 41):
                Kt = K.copy()
                for nb, (R, L, T, k, fe, dist, pont, idx) in enumerate(info):
                    f = (k + kgs[nb]) @ (T @ u[idx]) + fe
                    kgs[nb] = self.rigidez_geometrica(-f[0], L)
                    Kt[np.ix_(idx, idx)] += T.T @ kgs[nb] @ T
                Ktf = Kt[np.ix_(livres, livres)]
                try:
                    novo = np.linalg.solve(Ktf, F[livres])
                    ok = np.all(np.isfinite(novo))
                except np.linalg.LinAlgError:
                    ok = False
                if ok:
                    ok = np.min(np.linalg.eigvalsh((Ktf + Ktf.T) / 2.0)) > 0
                if not ok:
                    raise ValueError("instabilidade global na análise de 2ª ordem: as cargas passam da carga "
                                     "crítica da estrutura. Confira os travamentos fora do plano (um pórtico plano só com "
                                     "apoios na base gira de lado) e os perfis")
                dif = np.max(np.abs(novo - u[livres])) if novo.size else 0.0
                u[livres] = novo
                if dif <= 1e-6 * max(1.0, np.max(np.abs(novo))):
                    break
            K = Kt
        reac = K @ u - F
        res = Resultado(self, u, reac, presos)
        res.segunda_ordem = segunda_ordem
        res.iteracoes = iteracoes
        tr1 = max((np.linalg.norm(u1[6 * n:6 * n + 3]) for n in range(n)), default=0.0)
        tr2 = max((np.linalg.norm(u[6 * n:6 * n + 3]) for n in range(n)), default=0.0)
        res.amplificacao = tr2 / tr1 if tr1 > 1e-12 else 1.0
        for nb, (R, L, T, k, fe, dist, pont, idx) in enumerate(info):
            ul = T @ u[idx]
            res.extremos.append((k + kgs[nb]) @ ul + fe)
            res.cargas.append((dist, pont))
            res.geo.append((R, L))
        return res


class Resultado:
    """Deslocamentos (mm, rad), reações (N, N·mm) e esforços nas barras."""

    def __init__(self, modelo, u, reac, presos):
        self.modelo = modelo
        self.u = u
        self.reac = reac
        self.presos = presos
        self.extremos = []      # 12 forças locais nas pontas de cada barra (convenção da matriz)
        self.segunda_ordem = False
        self.iteracoes = 0
        self.amplificacao = 1.0
        self.cargas = []
        self.geo = []

    def deslocamento(self, no):
        return self.u[6 * no:6 * no + 3]

    def reacao(self, no):
        """(Fx, Fy, Fz) em kN, (Mx, My, Mz) em kN·m."""
        r = self.reac[6 * no:6 * no + 6]
        return r[:3] / 1000.0, r[3:] / 1e6

    def esforcos(self, nb, x):
        """Esforços internos na seção x (mm a partir do nó i) da barra nb, em N e N·mm.

        Face positiva da seção (normal +x local): N > 0 é tração. My > 0 traciona o lado -z da seção
        (a fibra de baixo, com z para cima: viga biapoiada com carga para baixo tem My > 0); Mz > 0
        traciona o lado -y. Vy, Vz e T seguem a regra da mão direita na face positiva."""
        f = self.extremos[nb]
        dist, pont = self.cargas[nb]
        sx, sy, sz = f[0], f[1], f[2]
        smy = f[4] + x * f[2]
        smz = f[5] - x * f[1]
        for qx, qy, qz in dist:
            sx += qx * x
            sy += qy * x
            sz += qz * x
            smy += qz * x * x / 2.0
            smz -= qy * x * x / 2.0
        for a, (Px, Py, Pz) in pont:
            if a < x:
                sx += Px
                sy += Py
                sz += Pz
                smy += (x - a) * Pz
                smz -= (x - a) * Py
        return {"N": -sx, "Vy": -sy, "Vz": -sz, "T": -f[3], "My": smy, "Mz": -smz}

    def diagrama(self, nb, pontos=11):
        R, L = self.geo[nb]
        xs = [L * k / (pontos - 1) for k in range(pontos)]
        for a, _P in self.cargas[nb][1]:
            for xa in (a - 1e-6, a + 1e-6):
                if 0 < xa < L:
                    xs.append(xa)
        xs.sort()
        return [(x, self.esforcos(nb, x)) for x in xs]

    def maximos(self, nb, pontos=21):
        """Maiores valores absolutos de cada esforço na barra (N, N·mm)."""
        m = {}
        for _x, e in self.diagrama(nb, pontos):
            for k, v in e.items():
                if abs(v) > abs(m.get(k, 0.0)):
                    m[k] = v
        return m

    def flecha_local(self, nb, pontos=21):
        """Maior deslocamento transversal relativo à corda (mm), no plano de cada eixo: (y, z)."""
        R, L = self.geo[nb]
        b = self.modelo.barras[nb]
        di = R @ self.u[6 * b.i:6 * b.i + 3]
        dj = R @ self.u[6 * b.j:6 * b.j + 3]
        ri = R @ self.u[6 * b.i + 3:6 * b.i + 6]
        rj = R @ self.u[6 * b.j + 3:6 * b.j + 6]
        s = b.secao
        dist, pont = self.cargas[nb]
        maxy = maxz = 0.0
        for k in range(1, pontos - 1):
            x = L * k / (pontos - 1)
            xi = x / L
            h1 = 1 - 3 * xi ** 2 + 2 * xi ** 3
            h2 = x * (1 - xi) ** 2
            h3 = 3 * xi ** 2 - 2 * xi ** 3
            h4 = x * (xi ** 2 - xi)
            v = h1 * di[1] + h2 * ri[2] + h3 * dj[1] + h4 * rj[2]
            w = h1 * di[2] - h2 * ri[1] + h3 * dj[2] - h4 * rj[1]
            # parcela das cargas no vão (viga biengastada sob a carga)
            for qx, qy, qz in dist:
                v += qy * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iz)
                w += qz * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iy)
            for a, (Px, Py, Pz) in pont:
                v += _flecha_pontual_biengastada(Py, a, x, L, s.E * s.Iz)
                w += _flecha_pontual_biengastada(Pz, a, x, L, s.E * s.Iy)
            corda_y = di[1] + (dj[1] - di[1]) * xi
            corda_z = di[2] + (dj[2] - di[2]) * xi
            maxy = max(maxy, abs(v - corda_y))
            maxz = max(maxz, abs(w - corda_z))
        return maxy, maxz


def _deslocamento_no_vao(r, nb, x):
    """(v, w) locais da barra nb na posição x, em relação à reta entre as suas pontas (mm, com sinal)."""
    m = r.modelo
    b = m.barras[nb]
    R, L = r.geo[nb]
    di = R @ r.u[6 * b.i:6 * b.i + 3]
    dj = R @ r.u[6 * b.j:6 * b.j + 3]
    ri = R @ r.u[6 * b.i + 3:6 * b.i + 6]
    rj = R @ r.u[6 * b.j + 3:6 * b.j + 6]
    s = b.secao
    dist, pont = r.cargas[nb]
    xi = x / L
    h1, h2 = 1 - 3 * xi ** 2 + 2 * xi ** 3, x * (1 - xi) ** 2
    h3, h4 = 3 * xi ** 2 - 2 * xi ** 3, x * (xi ** 2 - xi)
    v = h1 * di[1] + h2 * ri[2] + h3 * dj[1] + h4 * rj[2]
    w = h1 * di[2] - h2 * ri[1] + h3 * dj[2] - h4 * rj[1]
    for qx, qy, qz in dist:
        v += qy * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iz)
        w += qz * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iy)
    for a, (Px, Py, Pz) in pont:
        v += _flecha_pontual_biengastada(Py, a, x, L, s.E * s.Iz)
        w += _flecha_pontual_biengastada(Pz, a, x, L, s.E * s.Iy)
    v -= di[1] + (dj[1] - di[1]) * xi
    w -= di[2] + (dj[2] - di[2]) * xi
    return v, w


def _flecha_pontual_biengastada(P, a, x, L, EI):
    """Deslocamento em x de uma viga biengastada com carga P em a (Roark)."""
    if P == 0:
        return 0.0
    b = L - a
    if x <= a:
        return P * b * b * x * x * (3 * a * L - x * (3 * a + b)) / (6 * EI * L ** 3)
    xr = L - x
    return P * a * a * xr * xr * (3 * b * L - xr * (3 * b + a)) / (6 * EI * L ** 3)
