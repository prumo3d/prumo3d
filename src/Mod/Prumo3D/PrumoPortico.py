# SPDX-License-Identifier: LGPL-2.1-or-later
"""Cálculo de pórticos espaciais pelo método da rigidez direta (análise linear de 1ª ordem).

Unidades internas: N, mm, MPa (N/mm²). Cargas de entrada: kN, kN/m, kN·m (convertidas aqui).

Barras de Euler-Bernoulli com 6 graus de liberdade por nó (3 deslocamentos e 3 rotações). Eixos
locais da barra: x ao longo da barra; y e z nos eixos principais da seção (para perfis I e U,
z = altura do perfil e y = largura: a flexão "em torno de y" usa a maior inércia).

Hipóteses (vão para a memória de cálculo):
- análise elástica linear de 1ª ordem (sem efeito P-Δ), material elástico;
- barras ligadas rigidamente nos nós, salvo as liberações (rótulas) dadas nas pontas, tratadas
  por condensação estática da matriz da barra;
- as barras ficam sobre as linhas do esqueleto (excentricidades do ponto de fixação desprezadas);
- deformação por cortante desprezada.
"""

import math

import numpy as np

G_GRAV = 9.80665e-3          # N/kg → peso em N por kg (1 kgf = 9,80665 N); massa_kgm·G_GRAV = N/mm

# Gauss-Legendre de 4 pontos: exato até grau 7 (carga linear × funções cúbicas)
GAUSS4 = [(-0.8611363115940526, 0.3478548451374538), (-0.3399810435848563, 0.6521451548625461),
          (0.3399810435848563, 0.6521451548625461), (0.8611363115940526, 0.3478548451374538)]

# graus locais de cada ponta: 0-2 deslocamentos, 3 torção, 4-5 flexão (giro em y e z)
ROTULA_I = (4, 5)
ROTULA_J = (10, 11)
TRELICA = (4, 5, 10, 11, 9)       # rótula nas duas pontas e a torção solta numa delas


def _q_em(carga, s):
    """Valor (vetor local, N/mm) da carga distribuída linear `carga` = (a, b, q1, q2) em s."""
    a, b, q1, q2 = carga
    t = (s - a) / (b - a) if b > a else 0.0
    return q1 + (q2 - q1) * t


def _gauss(carga, lo, hi):
    """Carga distribuída em [lo, hi] (dentro de [a, b]) como forças concentradas equivalentes
    nos pontos de Gauss: [(s, força N)]. Exata para integrar com polinômios até grau 6."""
    a, b, _q1, _q2 = carga
    lo, hi = max(lo, a), min(hi, b)
    if hi <= lo:
        return []
    m, h = (lo + hi) / 2.0, (hi - lo) / 2.0
    return [(m + h * g, w * h * _q_em(carga, m + h * g)) for g, w in GAUSS4]


def resultante_ate(dist, pont, x):
    """Soma das forças (3) e momento (3) em relação ao ponto x de tudo o que age em [0, x] da
    barra (cargas distribuídas e concentradas), em eixos locais."""
    s = np.zeros(3)
    m = np.zeros(3)
    for carga in dist:
        for xs, P in _gauss(carga, 0.0, x):
            s += P
            m += np.array([0.0, (x - xs) * P[2], -(x - xs) * P[1]])
    for a, P in pont:
        if a < x:
            s += P
            m += np.array([0.0, (x - a) * P[2], -(x - a) * P[1]])
    return s, m


def flecha_particular(dist, pont, x, L, EIz, EIy):
    """(v, w) da barra biengastada sob as cargas no vão (parcela que se soma às funções de forma)."""
    v = w = 0.0
    for carga in dist:
        for lo, hi in ((0.0, x), (x, L)):        # divide no ponto: o integrando muda de forma em x
            for xs, P in _gauss(carga, lo, hi):
                v += _flecha_pontual_biengastada(P[1], xs, x, L, EIz)
                w += _flecha_pontual_biengastada(P[2], xs, x, L, EIy)
    for a, P in pont:
        v += _flecha_pontual_biengastada(P[1], a, x, L, EIz)
        w += _flecha_pontual_biengastada(P[2], a, x, L, EIy)
    return v, w


def _condensar(kk, fe, liberados):
    """Condensação estática dos graus liberados (rótulas): (k', fe', recuperação)."""
    if not liberados:
        return kk, fe, None
    r = sorted(liberados)
    c = [i for i in range(12) if i not in liberados]
    krr = kk[np.ix_(r, r)]
    try:
        inv = np.linalg.inv(krr)
    except np.linalg.LinAlgError:
        inv = np.linalg.pinv(krr)
    krc = kk[np.ix_(r, c)]
    kcr = kk[np.ix_(c, r)]
    k2 = np.zeros((12, 12))
    k2[np.ix_(c, c)] = kk[np.ix_(c, c)] - kcr @ inv @ krc
    f2 = np.zeros(12)
    f2[c] = fe[c] - kcr @ inv @ fe[r]
    return k2, f2, (r, c, inv, krc, fe[r].copy())


class Secao:
    """Rigidez da seção: A, Iy (maior, flexão no plano x-z local), Iz, J em mm."""

    def __init__(self, A, Iy, Iz, J, E=200000.0, Gc=77000.0, massa_kgm=0.0, nome=""):
        self.A, self.Iy, self.Iz, self.J = float(A), float(Iy), float(Iz), float(J)
        self.E, self.G = float(E), float(Gc)
        self.massa_kgm = float(massa_kgm)
        self.nome = nome


class Barra:
    """Barra entre os nós i e j. eixo_z: vetor que dá a direção do eixo local z (altura da seção)."""

    def __init__(self, i, j, secao, eixo_z, nome="", origem=None, liberados=()):
        self.liberados = tuple(sorted(set(liberados)))   # graus locais soltos (rótulas): 4, 5, 9, 10, 11
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
        self.distribuidas = []  # (barra, [qx, qy, qz] kN/m, global=True[, a, b, [q2]]): linear de a a b (mm)
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
        """[(a, b, q1, q2) distribuída linear local N/mm], [(a, P local N)] da barra nb no caso."""
        dist, pont = [], []
        if caso.peso_proprio and b.secao.massa_kgm:
            q = R @ np.array([0.0, 0.0, -b.secao.massa_kgm * G_GRAV])      # N/mm (kg/m · g)
            dist.append((0.0, L, q, q.copy()))
        for item in caso.distribuidas:
            k, q, glob = item[0], item[1], item[2]
            if k != nb:
                continue
            q1 = np.array(q, dtype=float)          # kN/m = N/mm
            a = float(item[3]) if len(item) > 3 and item[3] is not None else 0.0
            bb = float(item[4]) if len(item) > 4 and item[4] is not None else L
            q2 = np.array(item[5], dtype=float) if len(item) > 5 and item[5] is not None else q1.copy()
            a, bb = max(0.0, min(a, L)), max(0.0, min(bb, L))
            if bb <= a:
                continue
            if glob:
                q1, q2 = R @ q1, R @ q2
            dist.append((a, bb, q1, q2))
        for (k, a, P, glob) in caso.pontuais:
            if k == nb:
                P = np.array(P, dtype=float) * 1000.0
                pont.append((float(a), R @ P if glob else P))
        return dist, pont

    @staticmethod
    def _engaste_perfeito(dist, pont, L):
        """Forças de engaste perfeito (12) em eixos locais: cargas distribuídas lineares (pelos pontos
        de Gauss, exato) e concentradas."""
        f = np.zeros(12)
        tudo = list(pont)
        for carga in dist:
            tudo += _gauss(carga, 0.0, L)
        for a, P in tudo:
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

    def _texto_mecanismo(self, Kff, livres):
        """Mensagem do mecanismo apontando o nó e a direção que se movem sem resistência."""
        txt = "a estrutura é instável (mecanismo): faltam apoios ou travamentos"
        try:
            w, v = np.linalg.eigh((Kff + Kff.T) / 2.0)
            modo = v[:, 0]
            ids = np.where(livres)[0]
            trans = [(abs(modo[k]), ids[k]) for k in range(len(ids)) if ids[k] % 6 < 3]
            if trans and max(trans)[0] > 1e-3:
                _a, g = max(trans)
                q = self.nos[g // 6]
                txt += ": o nó (%.0f; %.0f; %.0f) se move em %s sem nada que o segure" % (q[0], q[1], q[2],
                                                                                        "XYZ"[g % 6])
            else:
                g = ids[int(np.argmax(np.abs(modo)))]
                q = self.nos[g // 6]
                txt += ": o nó (%.0f; %.0f; %.0f) gira sem nada que o segure (rótulas demais?)" % (q[0], q[1], q[2])
        except Exception:
            pass
        return txt

    def _molas_de_giro(self, K, livres):
        """Matriz de molas fracas nos modos só de giro sem rigidez (nós de barras rotuladas)."""
        if not any(b.liberados for b in self.barras):
            return None
        chave = (len(self.nos), tuple(b.liberados for b in self.barras),
                 tuple(sorted((k, tuple(v)) for k, v in self.apoios.items())))
        if getattr(self, "_molas_chave", None) == chave:
            return self._molas_cache
        # todos os giros livres: a rótula de uma barra pode soltar o giro de outra (ex.: pilar
        # rotulado na base com as vigas rotuladas nele gira em torno do próprio eixo)
        sub = [g for g in range(K.shape[0]) if g % 6 >= 3 and livres[g]]
        molas = None
        if sub:
            Ks = K[np.ix_(sub, sub)]
            w, v = np.linalg.eigh((Ks + Ks.T) / 2.0)
            escala = max(1.0, float(np.max(np.abs(np.diag(K)))))
            for k in range(len(w)):
                if w[k] > 1e-9 * escala:
                    break
                vec = np.zeros(K.shape[0])
                vec[sub] = v[:, k]
                if np.linalg.norm(K @ vec) > 1e-6 * escala:
                    continue                      # o modo mexe com outros graus: não é só giro solto
                if molas is None:
                    molas = np.zeros_like(K)
                molas += 1e-6 * escala * np.outer(vec, vec)
        self._molas_chave = chave
        self._molas_cache = molas
        return molas

    # ------------------------------------------------------------ solução
    def resolver(self, caso_ou_combinacao, segunda_ordem=False):
        """Resolve um caso ou uma combinação [(caso, fator)]. Retorna Resultado.

        segunda_ordem=True: análise P-Δ (rigidez geométrica, iterada até convergir); o resultado
        traz o fator de amplificação dos deslocamentos (2ª ordem / 1ª ordem)."""
        partes = caso_ou_combinacao if isinstance(caso_ou_combinacao, (list, tuple)) else [(caso_ou_combinacao, 1.0)]
        n = len(self.nos)
        ndof = 6 * n
        F_nos = np.zeros(ndof)
        info = []
        for nb, b in enumerate(self.barras):
            R, L = self.eixos(b)
            T = self._T(R)
            k = self.rigidez_local(b.secao, L)
            idx = list(range(6 * b.i, 6 * b.i + 6)) + list(range(6 * b.j, 6 * b.j + 6))
            dist_t, pont_t, fe_t = [], [], np.zeros(12)
            for caso, fator in partes:
                dist, pont = self._cargas_locais(caso, nb, b, R, L)
                dist = [(a, bb, q1 * fator, q2 * fator) for a, bb, q1, q2 in dist]
                pont = [(a, P * fator) for a, P in pont]
                fe_t += self._engaste_perfeito(dist, pont, L)
                dist_t += dist
                pont_t += pont
            info.append((R, L, T, k, fe_t, dist_t, pont_t, idx, b.liberados))
        for caso, fator in partes:
            for (no, forca, momento) in caso.nos:
                F_nos[6 * no:6 * no + 3] += np.array(forca, dtype=float) * 1000.0 * fator
                F_nos[6 * no + 3:6 * no + 6] += np.array(momento, dtype=float) * 1e6 * fator

        def montar(kgs):
            K = np.zeros((ndof, ndof))
            F = F_nos.copy()
            cond = []
            for nb, (R, L, T, k, fe, _d, _p, idx, lib) in enumerate(info):
                k2, f2, rec = _condensar(k + kgs[nb], fe, lib)
                K[np.ix_(idx, idx)] += T.T @ k2 @ T
                F[idx] -= T.T @ f2
                cond.append((k2, f2, rec))
            return K, F, cond

        kgs = [np.zeros((12, 12)) for _ in info]
        K, F, cond = montar(kgs)
        presos = np.zeros(ndof, dtype=bool)
        for no, travas in self.apoios.items():
            for g in range(6):
                if travas[g]:
                    presos[6 * no + g] = True
        if not presos.any():
            raise ValueError("a estrutura não tem apoios: clique nos nós para apoiar")
        # giro de nó onde só chegam pontas rotuladas (ex.: nó de treliça): não tem rigidez e não
        # influi em nada; fica travado. Deslocamento sem rigidez é nó solto: erro.
        diag = np.abs(np.diag(K))
        tol = 1e-9 * max(1.0, diag.max())
        self.giros_travados = []
        for g in range(ndof):
            if not presos[g] and diag[g] < tol:
                if g % 6 >= 3:
                    presos[g] = True
                    self.giros_travados.append(g)
                else:
                    q = self.nos[g // 6]
                    raise ValueError("o nó (%.0f; %.0f; %.0f) se desloca em %s sem nada que o segure: nó solto, ou "
                                     "só barras de treliça chegando nele fora do plano delas (falta travamento)"
                                     % (q[0], q[1], q[2], "XYZ"[g % 6]))
        livres = ~presos
        # rótulas podem deixar giros sem rigidez em direções inclinadas (ex.: barra de treliça girando
        # em torno do próprio eixo): são modos de corpo rígido só de giro, sem carga que os excite.
        # Uma mola fraquinha nesses modos (achados uma vez por modelo) deixa o sistema resolvível.
        molas = self._molas_de_giro(K, livres)
        if molas is not None:
            K = K + molas
            self._molas = molas
        Kff = K[np.ix_(livres, livres)]
        try:
            uf = np.linalg.solve(Kff, F[livres])
        except np.linalg.LinAlgError:
            raise ValueError(self._texto_mecanismo(Kff, livres))
        if not np.all(np.isfinite(uf)) or (Kff.size and np.linalg.cond(Kff) > 1e15):
            raise ValueError(self._texto_mecanismo(Kff, livres))
        u = np.zeros(ndof)
        u[livres] = uf
        u1 = u.copy()
        iteracoes = 0
        if segunda_ordem:
            for iteracoes in range(1, 41):
                for nb, (R, L, T, k, fe, _d, _p, idx, lib) in enumerate(info):
                    k2, f2, _rec = cond[nb]
                    f = k2 @ (T @ u[idx]) + f2
                    kgs[nb] = self.rigidez_geometrica(-f[0], L)
                Kt, Ft, cond_t = montar(kgs)
                if molas is not None:
                    Kt = Kt + molas
                Ktf = Kt[np.ix_(livres, livres)]
                try:
                    novo = np.linalg.solve(Ktf, Ft[livres])
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
                cond = cond_t
                K, F = Kt, Ft
                if dif <= 1e-6 * max(1.0, np.max(np.abs(novo))):
                    break
        reac = K @ u - F
        res = Resultado(self, u, reac, presos)
        res.segunda_ordem = segunda_ordem
        res.iteracoes = iteracoes
        tr1 = max((np.linalg.norm(u1[6 * n:6 * n + 3]) for n in range(n)), default=0.0)
        tr2 = max((np.linalg.norm(u[6 * n:6 * n + 3]) for n in range(n)), default=0.0)
        res.amplificacao = tr2 / tr1 if tr1 > 1e-12 else 1.0
        for nb, (R, L, T, k, fe, dist, pont, idx, lib) in enumerate(info):
            k2, f2, rec = cond[nb]
            ul = T @ u[idx]
            res.extremos.append(k2 @ ul + f2)
            if rec is not None:
                # giro da ponta rotulada (diferente do giro do nó)
                r, c, inv, krc, fer = rec
                ul = ul.copy()
                ul[r] = -inv @ (krc @ ul[c] + fer)
            res.locais.append(ul)
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
        self.locais = []        # 12 deslocamentos locais de cada barra (giros das pontas rotuladas incluídos)

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
        sc, mc = resultante_ate(dist, pont, x)
        sx, sy, sz = f[0] + sc[0], f[1] + sc[1], f[2] + sc[2]
        smy = f[4] + x * f[2] + mc[1]
        smz = f[5] - x * f[1] + mc[2]
        return {"N": -sx, "Vy": -sy, "Vz": -sz, "T": -f[3], "My": smy, "Mz": -smz}

    def diagrama(self, nb, pontos=11):
        R, L = self.geo[nb]
        xs = [L * k / (pontos - 1) for k in range(pontos)]
        for a, _P in self.cargas[nb][1]:
            for xa in (a - 1e-6, a + 1e-6):
                if 0 < xa < L:
                    xs.append(xa)
        for a, b, _q1, _q2 in self.cargas[nb][0]:
            for xa in (a, b):
                if 1e-6 < xa < L - 1e-6:
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
        _R, L = self.geo[nb]
        maxy = maxz = 0.0
        for k in range(1, pontos - 1):
            v, w = _deslocamento_no_vao(self, nb, L * k / (pontos - 1))
            maxy = max(maxy, abs(v))
            maxz = max(maxz, abs(w))
        return maxy, maxz


def deslocamento_local(r, nb, x):
    """(u, v, w) locais da barra nb na posição x (mm): funções de forma com os deslocamentos das
    pontas (giros das pontas rotuladas incluídos) mais a parcela das cargas no vão."""
    b = r.modelo.barras[nb]
    _R, L = r.geo[nb]
    ul = r.locais[nb]
    di, ri, dj, rj = ul[0:3], ul[3:6], ul[6:9], ul[9:12]
    s = b.secao
    dist, pont = r.cargas[nb]
    xi = x / L
    h1, h2 = 1 - 3 * xi ** 2 + 2 * xi ** 3, x * (1 - xi) ** 2
    h3, h4 = 3 * xi ** 2 - 2 * xi ** 3, x * (xi ** 2 - xi)
    u = di[0] + (dj[0] - di[0]) * xi
    v = h1 * di[1] + h2 * ri[2] + h3 * dj[1] + h4 * rj[2]
    w = h1 * di[2] - h2 * ri[1] + h3 * dj[2] - h4 * rj[1]
    pv, pw = flecha_particular(dist, pont, x, L, s.E * s.Iz, s.E * s.Iy)
    return u, v + pv, w + pw


def _deslocamento_no_vao(r, nb, x):
    """(v, w) locais da barra nb na posição x, em relação à reta entre as suas pontas (mm, com sinal)."""
    _R, L = r.geo[nb]
    ul = r.locais[nb]
    xi = x / L
    _u, v, w = deslocamento_local(r, nb, x)
    v -= ul[1] + (ul[7] - ul[1]) * xi
    w -= ul[2] + (ul[8] - ul[2]) * xi
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
