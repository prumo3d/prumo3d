# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - estruturas soldadas: barras de perfil sobre um esqueleto de linhas.
"""Estruturas soldadas (bases de máquina, plataformas, suportes, pórticos).

Desenhe o esqueleto em linhas (esboço ou arame), escolha o perfil e o Prumo cria uma barra por
linha, com meia-esquadria nos cantos de duas barras e recorte pela peça nas ligações em "T".
A lista de corte sai em planilha: perfil, comprimento, quantidade, ângulos de corte e massa
(massa linear do catálogo × comprimento).

Objetos:
- Estrutura (grupo): esqueleto, perfil padrão, rotação, alinhamento, tipo de união, material e
  as trocas de perfil/rotação de cada barra;
- Barra (forma): uma por linha do esqueleto; a forma é calculada a partir da estrutura.
"""

import math

import FreeCAD
import FreeCADGui

import PrumoPerfis
import PrumoUtil
from PrumoUtil import fmt, fmt_dim

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets

TOL = 1e-6
UNIOES = ["Meia-esquadria", "Topo"]
ALINHAMENTOS = ["Centro", "Topo", "Base"]          # (arquivos antigos; hoje: FIXACOES)
# ponto da seção que fica sobre a linha do esqueleto ("localizar perfil")
FIXACOES = ["Centro", "Centroide", "Sup. esquerdo", "Sup. centro", "Sup. direito", "Meio esquerdo",
            "Meio direito", "Inf. esquerdo", "Inf. centro", "Inf. direito"]
_ALINHAMENTO_PARA_FIXACAO = {"Centro": "Centro", "Topo": "Sup. centro", "Base": "Inf. centro"}
# tratamentos de canto (guardados em Estrutura.Cantos como "i-j=valor")
TRAT_MEIA = "meia"            # meia-esquadria
TRAT_PASSA = "passa:"         # "passa:k": a barra k passa, a outra encosta cortada reta
TRAT_RETO = "reto"            # ligação em T: corte reto na face da que passa
TRAT_CONTORNO = "contorno"    # ligação em T: recorte pelo contorno da que passa (boca de lobo)
PERFIL_PADRAO = "W 150 x 13,0"


# ============================================================================ geometria
placement_global = PrumoUtil.placement_global
forma_global = PrumoUtil.forma_global


def arestas(esqueleto):
    """Arestas do esqueleto no espaço global."""
    return [e for e in forma_global(esqueleto).Edges if e.Length > TOL]


SEM_BARRA = -1   # GrupoDaAresta: linha do esqueleto sem barra


def sem_barra(est):
    """Índices das linhas do esqueleto que não têm barra."""
    return {i for i, k in enumerate(getattr(est, "GrupoDaAresta", []) or []) if k == SEM_BARRA}


def arestas_ativas(est, eds=None):
    """Arestas do esqueleto com None no lugar das linhas sem barra (os índices continuam os mesmos)."""
    if eds is None:
        eds = arestas(est.Esqueleto)
    fora = sem_barra(est)
    return [None if i in fora else e for i, e in enumerate(eds)]


def _link_global(obj, nome, grupo, dica):
    """Vínculo que pode apontar para dentro de um Body/Part sem aviso de escopo
    (migra o PropertyLink de arquivos antigos)."""
    tipo = "App::PropertyLinkGlobal"
    if nome in obj.PropertiesList and obj.getTypeIdOfProperty(nome) != tipo:
        valor = getattr(obj, nome)
        modo = obj.getEditorMode(nome)
        obj.removeProperty(nome)
        obj.addProperty(tipo, nome, grupo, dica)
        setattr(obj, nome, valor)
        obj.setEditorMode(nome, modo)
    elif nome not in obj.PropertiesList:
        obj.addProperty(tipo, nome, grupo, dica)


def _dir(e, no_inicio=True):
    """Direção da aresta saindo da ponta indicada (para dentro da aresta)."""
    if no_inicio:
        u = e.FirstParameter
        t = e.tangentAt(u)
        return FreeCAD.Vector(t).normalize()
    u = e.LastParameter
    t = e.tangentAt(u)
    return FreeCAD.Vector(t).normalize() * -1


def _normal_esqueleto(eds):
    """Normal do plano do esqueleto, se for plano; senão None."""
    import Part
    eds = [e for e in eds if e is not None]
    try:
        w = Part.Compound(eds)
        pl = w.findPlane()
        if pl is not None:
            return FreeCAD.Vector(pl.Axis).normalize()
    except Exception:
        pass
    return None


def referencia(t, normal):
    """Vetor 'para cima' da seção (altura do perfil) para uma barra de direção t."""
    if normal is not None and abs(normal.z) > 0.9:
        cima = FreeCAD.Vector(0, 0, 1)  # plataforma horizontal: altura do perfil na vertical
    elif normal is not None:
        cima = normal.cross(t)          # pórtico vertical: altura no plano do pórtico
    else:
        cima = FreeCAD.Vector(0, 0, 1)
    cima = cima - t * cima.dot(t)
    if cima.Length < 1e-9:
        cima = FreeCAD.Vector(1, 0, 0) - t * t.x
    return cima.normalize()


def _sentido_canonico(e, t, normal, centro):
    """Direção de referência da linha (t ou -t) que não depende do sentido em que a linha foi desenhada:
    o eixo da seção que fica no plano do esqueleto aponta para fora do centro da estrutura. Assim
    "Sup. centro" põe todas as barras de um quadro do mesmo lado (todas por fora), mesmo com linhas
    desenhadas em sentidos diferentes."""
    if centro is None:
        return t
    v = referencia(t, normal)
    u = v.cross(t).normalize()
    if normal is not None:
        no_plano = u if abs(u.dot(normal)) < abs(v.dot(normal)) else v
    else:
        no_plano = u
    try:
        meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
    except Exception:
        meio = e.CenterOfMass
    w = meio - centro
    if normal is not None:
        w = w - normal * w.dot(normal)
    d = no_plano.dot(w)
    if abs(d) < 1e-6 * max(1.0, w.Length) or w.Length < 1e-6:
        # linha que passa pelo centro: o eixo no plano aponta para +Z, senão +X, senão +Y
        for ref in (FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0)):
            d = no_plano.dot(ref)
            if abs(d) > 1e-6:
                break
    return t * -1 if d < 0 else t


def eixos_secao(e, rot_graus, normal, centro=None):
    """(t, u, v): direção da barra, largura e altura da seção.

    t é a direção da linha (como foi desenhada: a barra é extrudada nela); u e v vêm da direção
    canônica (ver _sentido_canonico), para o lado da seção não depender do sentido do desenho."""
    t = _dir(e, True)
    tc = _sentido_canonico(e, t, normal, centro)
    v = referencia(tc, normal)
    if abs(rot_graus) > 1e-9:
        r = FreeCAD.Rotation(tc, rot_graus)
        v = r.multVec(v)
    u = v.cross(tc).normalize()
    return t, u, v


_cache_centro = {}


def centro_esqueleto(esqueleto):
    """Centro (caixa envolvente, espaço global) do esqueleto inteiro: referência do lado das seções."""
    try:
        chave = (esqueleto.Document.Name, esqueleto.Name, str(esqueleto.Shape.BoundBox),
                 str(PrumoUtil.placement_global(esqueleto)))
    except Exception:
        chave = None
    if chave is not None and chave in _cache_centro:
        return _cache_centro[chave]
    c = forma_global(esqueleto).BoundBox.Center
    if chave is not None:
        if len(_cache_centro) > 64:
            _cache_centro.clear()
        _cache_centro[chave] = c
    return c


def _reta(e):
    return e.Curve.__class__.__name__ in ("Line", "LineSegment")


def solido_bruto(e, it, rot_graus, desloc, normal, ext0=0.0, ext1=0.0, espelhar=False, centro=None):
    """Barra sem recortes sobre a aresta e, prolongada ext0 antes do início e ext1 após o fim.

    desloc = (du, dv): centro da caixa da seção em relação à linha (ver deslocamento()); aceita
    também o nome de uma fixação ou de um alinhamento antigo."""
    import Part
    t, u, v = eixos_secao(e, rot_graus, normal, centro)
    if isinstance(desloc, str):
        desloc = deslocamento(it, _ALINHAMENTO_PARA_FIXACAO.get(desloc, desloc), espelhar)
    du, dv = desloc
    if not _reta(e):
        ext0 = ext1 = 0.0
    p0 = e.valueAt(e.FirstParameter) - t * ext0
    f = PrumoPerfis.face(it, p0, u, v, dv, du, espelhar)
    if _reta(e):
        return f.extrude(t * (e.Length + ext0 + ext1))
    w = Part.Wire(e)
    return w.makePipeShell([f.OuterWire], True, True)


_centroides = {}


def deslocamento(it, fixacao="Centro", espelhar=False):
    """(du, dv): onde fica o centro da caixa da seção em relação à linha do esqueleto, para que o
    ponto de fixação escolhido fique sobre a linha (u = largura, v = altura)."""
    larg, alt = PrumoPerfis.dimensoes(it)
    if fixacao == "Centroide":
        chave = (it["nome"], bool(espelhar))
        if chave not in _centroides:
            f = PrumoPerfis.face(it, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0),
                                 0.0, 0.0, espelhar)
            c = f.CenterOfMass
            _centroides[chave] = (c.x, c.y)
        cu, cv = _centroides[chave]
        return -cu, -cv
    partes = fixacao.split(" ")
    if len(partes) != 2:
        return 0.0, 0.0
    v0 = {"Sup.": alt / 2.0, "Inf.": -alt / 2.0}.get(partes[0], 0.0)
    u0 = {"esquerdo": -larg / 2.0, "direito": larg / 2.0}.get(partes[1], 0.0)
    return -u0, -v0


def _meio_espaco(ponto, normal, tam):
    """Caixa grande do lado positivo do plano (ponto, normal)."""
    import Part
    n = FreeCAD.Vector(normal).normalize()
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), n)
    caixa = Part.makeBox(tam, tam, tam)
    caixa.Placement = FreeCAD.Placement(ponto + rot.multVec(FreeCAD.Vector(-tam / 2.0, -tam / 2.0, 0)), rot)
    return caixa


def _ponto_interior(p, e):
    """True se p está sobre a aresta e, longe das pontas."""
    import Part
    try:
        d = e.distToShape(Part.Vertex(p))[0]
    except Exception:
        return False
    if d > 1e-4:
        return False
    a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
    return (p - a).Length > 1e-4 and (p - b).Length > 1e-4


class Ligacao:
    """O que acontece numa ponta de barra."""

    def __init__(self, tipo, outro=None, normal=None, outros=None):
        self.tipo = tipo      # "livre", "esquadria", "topo_T", "multipla", "reta"
        self.outro = outro    # índice da outra barra
        self.normal = normal  # normal do plano de corte (esquadria)
        self.outros = outros or []  # nó múltiplo: [(índice, direção para dentro da barra)]


def ligacoes(eds, i):
    """(ligação na ponta inicial, ligação na ponta final) da barra i."""
    e = eds[i]
    res = []
    for no_inicio in (True, False):
        p = e.valueAt(e.FirstParameter if no_inicio else e.LastParameter)
        a = _dir(e, no_inicio)
        encontros = []
        for j, o in enumerate(eds):
            if j == i or o is None:
                continue
            pa, pb = o.valueAt(o.FirstParameter), o.valueAt(o.LastParameter)
            if (pa - p).Length < 1e-4:
                encontros.append((j, _dir(o, True)))
            elif (pb - p).Length < 1e-4:
                encontros.append((j, _dir(o, False)))
        if len(encontros) == 1:
            j, b = encontros[0]
            if abs(a.dot(b) + 1) < 1e-6:
                res.append(Ligacao("reta", j))
            else:
                n = a - b
                res.append(Ligacao("esquadria", j, n.normalize()))
            continue
        if len(encontros) > 1:
            res.append(Ligacao("multipla", outros=encontros))
            continue
        passa = [j for j, o in enumerate(eds) if j != i and o is not None and _ponto_interior(p, o)]
        if passa:
            res.append(Ligacao("topo_T", passa[0]))
        else:
            res.append(Ligacao("livre"))
    return res


def angulo_corte(normal_plano, t):
    """Ângulo do corte em relação ao corte reto (graus): 0 = reto, 45 = meia-esquadria a 90°."""
    c = abs(FreeCAD.Vector(normal_plano).normalize().dot(t))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


# ============================================================================ parâmetros por barra
def grupos(est):
    """Grupos extras da estrutura (o grupo 0 é o padrão: Perfil, Rotacao, Fixacao, Espelhar)."""
    import json
    res = []
    for linha in getattr(est, "Grupos", []) or []:
        try:
            g = json.loads(linha)
        except ValueError:
            continue
        res.append(g)
    return res


def _fixacao_da_estrutura(est):
    fx = getattr(est, "Fixacao", None)
    if fx:
        return fx
    return _ALINHAMENTO_PARA_FIXACAO.get(getattr(est, "Alinhamento", "Centro"), "Centro")


def grupo_padrao(est):
    return {"nome": getattr(est, "NomeGrupo", "") or "Padrão", "perfil": est.Perfil,
            "giro": est.Rotacao.Value if hasattr(est.Rotacao, "Value") else float(est.Rotacao),
            "fixacao": _fixacao_da_estrutura(est), "espelhar": bool(getattr(est, "Espelhar", False))}


def grupo_da_barra(est, i):
    """Índice do grupo da aresta i (0 = padrão)."""
    lst = list(getattr(est, "GrupoDaAresta", []) or [])
    k = lst[i] if i < len(lst) else 0
    if k == SEM_BARRA:
        return SEM_BARRA
    return k if 0 <= k <= len(grupos(est)) else 0


def parametros(est, i):
    """Perfil, giro, fixação e espelhamento efetivos da barra i (grupo + trocas individuais)."""
    k = grupo_da_barra(est, i)
    g = dict(grupo_padrao(est))
    if k > 0:
        extra = grupos(est)[k - 1]
        for chave in ("nome", "perfil", "giro", "fixacao", "espelhar"):
            if chave in extra:
                g[chave] = extra[chave]
    lst = list(est.PerfisIndividuais)
    if i < len(lst) and lst[i]:
        g["perfil"] = lst[i]
    rots = list(est.RotacoesIndividuais)
    g["giro"] = float(g["giro"]) + (rots[i] if i < len(rots) else 0.0)
    g["grupo"] = k
    return g


def _perfil_da_barra(est, i):
    return parametros(est, i)["perfil"]


def _rotacao_da_barra(est, i):
    return float(parametros(est, i)["giro"])


class Secao:
    """Seção da barra j posicionada: eixos, dimensões e deslocamento."""

    def __init__(self, est, eds, j, normal):
        par = parametros(est, j)
        self.it = PrumoPerfis.perfil(par["perfil"])
        if self.it is None:
            raise ValueError("perfil desconhecido: %s" % par["perfil"])
        self.larg, self.alt = PrumoPerfis.dimensoes(self.it)
        self.giro = float(par["giro"])
        self.espelhar = bool(par["espelhar"])
        self.fixacao = par["fixacao"]
        self.centro = centro_esqueleto(est.Esqueleto)
        self.t, self.u, self.v = eixos_secao(eds[j], self.giro, normal, self.centro)
        self.du, self.dv = deslocamento(self.it, self.fixacao, self.espelhar)

    def extremos(self, n):
        """(mín, máx) da seção ao longo da direção n, medidos a partir da linha do esqueleto."""
        c = n.dot(self.u) * self.du + n.dot(self.v) * self.dv
        r = abs(n.dot(self.u)) * self.larg / 2.0 + abs(n.dot(self.v)) * self.alt / 2.0
        return c - r, c + r


def chave_canto(i, j):
    return "%d-%d" % (min(i, j), max(i, j))


def tratamento(est, i, j, tipo):
    """Tratamento do canto entre as barras i e j ("esquadria" ou "topo_T")."""
    for linha in getattr(est, "Cantos", []) or []:
        k, _s, v = linha.partition("=")
        if k.strip() == chave_canto(i, j):
            v = v.strip()
            if tipo == "esquadria" and (v == TRAT_MEIA or v.startswith(TRAT_PASSA)):
                return v
            if tipo == "topo_T" and v in (TRAT_RETO, TRAT_CONTORNO):
                return v
    if tipo == "topo_T":
        return TRAT_RETO
    if est.Uniao == "Meia-esquadria":
        return TRAT_MEIA
    return TRAT_PASSA + str(min(i, j))


def definir_tratamento(est, i, j, valor):
    """Grava o tratamento do canto i-j (sem duplicar)."""
    chave = chave_canto(i, j)
    lst = [l for l in (getattr(est, "Cantos", []) or []) if l.partition("=")[0].strip() != chave]
    lst.append("%s=%s" % (chave, valor))
    est.Cantos = lst


def _passa(trat):
    return int(trat[len(TRAT_PASSA):]) if trat.startswith(TRAT_PASSA) else None


def _no_multiplo(eds, i, k, lig):
    """Quem passa num nó com 3 ou mais barras: (passantes, colinear?).

    Havendo duas barras alinhadas (uma viga partida no nó), as duas seguem e as outras encostam;
    senão passa a de menor índice."""
    membros = [i] + [j for j, _d in lig.outros]
    dirs = {i: _dir(eds[i], k == 0)}
    dirs.update({j: d for j, d in lig.outros})
    pares = []
    for x in range(len(membros)):
        for y in range(x + 1, len(membros)):
            m, n = membros[x], membros[y]
            if abs(dirs[m].dot(dirs[n]) + 1) < 1e-6:
                pares.append((m, n))
    if pares:
        pares.sort(key=lambda p: min(p))
        return list(pares[0]), True
    return [min(membros)], False


def _extensoes(est, eds, i, normal, ligs=None):
    """Prolongamento (antes do início, após o fim) da barra i.

    Meia-esquadria: o bastante para o plano de corte. Canto de topo: a barra que passa vai até a
    face externa da outra; a que encosta não é prolongada. Nó múltiplo: a que passa cobre todas."""
    e = eds[i]
    sec_i = Secao(est, eds, i, normal)
    if ligs is None:
        ligs = ligacoes(eds, i)
    ext = [0.0, 0.0]
    for k, lig in enumerate(ligs):
        a = _dir(e, k == 0) * -1  # para fora da barra, além da ponta
        if lig.tipo == "esquadria":
            j = lig.outro
            trat = tratamento(est, i, j, "esquadria")
            sec_j = Secao(est, eds, j, normal)
            if trat == TRAT_MEIA:
                ext[k] = 2.0 * (max(sec_i.larg, sec_i.alt) + max(sec_j.larg, sec_j.alt) +
                                abs(sec_i.du) + abs(sec_i.dv) + abs(sec_j.du) + abs(sec_j.dv))
            elif _passa(trat) == i:
                ext[k] = max(0.0, sec_j.extremos(a)[1])
        elif lig.tipo == "multipla":
            passantes, colinear = _no_multiplo(eds, i, k, lig)
            if i in passantes and not colinear:
                ext[k] = max([0.0] + [Secao(est, eds, j, normal).extremos(a)[1] for j, _d in lig.outros])
    return ext


def _face_de_encosto(est, eds, i, k, j, normal):
    """Plano (ponto, normal para dentro da barra i) da face da barra j onde encosta a ponta k de i."""
    e = eds[i]
    p = e.valueAt(e.FirstParameter if k == 0 else e.LastParameter)
    a = _dir(e, k == 0) * -1                      # para fora da barra i, além da ponta
    oe = eds[j]
    try:
        u_par = oe.Curve.parameter(p)
    except Exception:
        u_par = oe.FirstParameter
    to = FreeCAD.Vector(oe.tangentAt(u_par)).normalize()
    n_f = a - to * a.dot(to)
    if n_f.Length < 1e-9:
        return None                               # barras colineares: não há face de encosto
    n_f.normalize()
    sec_j = Secao(est, eds, j, normal)
    d_face = sec_j.extremos(n_f)[0]               # face de j voltada para a barra i
    return p + n_f * d_face, n_f * -1


def _contorno_cheio(est, eds, j, normal, folga=0.0):
    """Sólido cheio do contorno externo da barra j (tubo: cilindro cheio; demais: caixa da seção),
    prolongado nas pontas — para o recorte pelo contorno."""
    import Part
    sec = Secao(est, eds, j, normal)
    e = eds[j]
    m = 2.0 * (sec.larg + sec.alt) + 50.0
    t = sec.t
    p0 = e.valueAt(e.FirstParameter) - t * m
    centro = p0 + sec.u * sec.du + sec.v * sec.dv
    if sec.it["tipo"] == "TUBO":
        f = Part.Face(Part.Wire(Part.makeCircle(sec.larg / 2.0 + folga, centro, t)))
    else:
        hu, hv = sec.larg / 2.0 + folga, sec.alt / 2.0 + folga
        pts = [centro + sec.u * x + sec.v * y for x, y in ((-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv))]
        f = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return f.extrude(t * (e.Length + 2 * m))


def _maior_pedaco(sol, e):
    """Fica com o pedaço que contém o meio da barra."""
    import Part
    if len(sol.Solids) > 1:
        meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
        return min(sol.Solids, key=lambda s: s.distToShape(Part.Vertex(meio))[0])
    return sol


def calcular_barra(est, i, eds=None):
    """(sólido recortado, comprimento de corte, ângulo de corte no início, no fim, perfil)."""
    if eds is None:
        eds = arestas(est.Esqueleto)
    normal = _normal_esqueleto(eds)       # plano do esqueleto inteiro
    eds = arestas_ativas(est, eds)        # vizinhas: só as linhas que têm barra
    e = eds[i]
    if e is None:
        raise ValueError("a linha %d do esqueleto está sem barra" % (i + 1))
    sec = Secao(est, eds, i, normal)
    nome = sec.it["nome"]
    ligs = ligacoes(eds, i)
    ext = _extensoes(est, eds, i, normal, ligs)
    sol = solido_bruto(e, sec.it, sec.giro, (sec.du, sec.dv), normal, ext[0], ext[1], sec.espelhar, sec.centro)
    tam = 4 * (e.Length + sec.larg + sec.alt) + 100 + sum(ext)
    t = _dir(e, True)
    angs = [0.0, 0.0]

    def corte_reto(k, j):
        nonlocal sol
        plano = _face_de_encosto(est, eds, i, k, j, normal)
        if plano is not None:
            ponto, n_corte = plano
            sol = sol.common(_meio_espaco(ponto, n_corte, tam))
            angs[k] = angulo_corte(n_corte, t)

    for k, lig in enumerate(ligs):
        p = e.valueAt(e.FirstParameter if k == 0 else e.LastParameter)
        if lig.tipo == "esquadria":
            trat = tratamento(est, i, lig.outro, "esquadria")
            if trat == TRAT_MEIA:
                sol = sol.common(_meio_espaco(p, lig.normal, tam))
                angs[k] = angulo_corte(lig.normal, t)
            elif _passa(trat) != i:
                corte_reto(k, lig.outro)   # canto de topo: esta encosta na outra
        elif lig.tipo == "topo_T":
            j = lig.outro
            if tratamento(est, i, j, "topo_T") == TRAT_CONTORNO:
                sol = _maior_pedaco(sol.cut(_contorno_cheio(est, eds, j, normal)), e)
            else:
                corte_reto(k, j)
        elif lig.tipo == "multipla":
            passantes, _col = _no_multiplo(eds, i, k, lig)
            if i in passantes:
                continue
            corte_reto(k, passantes[0])
            # tira o que ainda cruzar com as outras que encostam (as de menor índice ficam inteiras)
            for j, _d in lig.outros:
                if j in passantes or j > i:
                    continue
                sj = Secao(est, eds, j, normal)
                bruto = solido_bruto(eds[j], sj.it, sj.giro, (sj.du, sj.dv), normal, 0.0, 0.0, sj.espelhar,
                                     sj.centro)
                sol = _maior_pedaco(sol.cut(bruto), e)
    sol = _maior_pedaco(sol, e)
    if sol.Solids and len(sol.Solids) == 1:
        sol = sol.Solids[0]
    proj = [(vx.Point - e.valueAt(e.FirstParameter)).dot(t) for vx in sol.Vertexes]
    if _reta(e) and proj:
        comp = max(proj) - min(proj)
    else:
        comp = e.Length
    return sol, comp, angs[0], angs[1], nome


# ============================================================================ objetos
class Estrutura:
    """Grupo que guarda os parâmetros da estrutura e contém as barras."""

    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, valor=None):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
        _link_global(obj, "Esqueleto", "Estrutura", "Esboço ou arame com as linhas de centro")
        add("App::PropertyString", "Perfil", "Estrutura", "Perfil padrão das barras", PERFIL_PADRAO)
        add("App::PropertyAngle", "Rotacao", "Estrutura", "Giro do perfil em torno da barra", 0.0)
        add("App::PropertyEnumeration", "Alinhamento", "Estrutura",
            "Posição do perfil em relação à linha do esqueleto")
        if not obj.Alinhamento:
            obj.Alinhamento = ALINHAMENTOS
        add("App::PropertyEnumeration", "Uniao", "Estrutura",
            "Cantos de duas barras: meia-esquadria ou de topo (uma barra recortada pela outra)")
        if not obj.Uniao:
            obj.Uniao = UNIOES
        add("App::PropertyString", "Material", "Estrutura", "Material das barras (texto para a lista)", "")
        add("App::PropertyStringList", "PerfisIndividuais", "Trocas",
            "Perfil de cada barra (vazio = perfil padrão)")
        add("App::PropertyFloatList", "RotacoesIndividuais", "Trocas",
            "Giro adicional de cada barra, em graus")
        # localizar perfil (substitui o Alinhamento de arquivos antigos)
        if "Fixacao" not in obj.PropertiesList:
            antigo = _ALINHAMENTO_PARA_FIXACAO.get(getattr(obj, "Alinhamento", "Centro") or "Centro", "Centro")
            obj.addProperty("App::PropertyEnumeration", "Fixacao", "Estrutura",
                            "Ponto da seção que fica sobre a linha do esqueleto (grupo padrão)")
            obj.Fixacao = FIXACOES
            obj.Fixacao = antigo
        obj.setEditorMode("Alinhamento", 2)
        add("App::PropertyBool", "Espelhar", "Estrutura", "Espelha a seção na largura (grupo padrão)", False)
        add("App::PropertyString", "NomeGrupo", "Grupos", "Nome do primeiro grupo de barras", "Padrão")
        add("App::PropertyStringList", "Grupos", "Grupos",
            "Grupos de barras com perfil próprio (JSON: nome, perfil, giro, fixacao, espelhar)")
        add("App::PropertyIntegerList", "GrupoDaAresta", "Grupos",
            "Grupo de cada linha do esqueleto (0 = padrão)")
        add("App::PropertyStringList", "Cantos", "Cantos",
            "Tratamento de cada canto: 'i-j=meia', 'i-j=passa:k', 'i-j=reto' ou 'i-j=contorno'")

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        if prop in ("Esqueleto", "Perfil", "Rotacao", "Alinhamento", "Uniao", "Material",
                    "PerfisIndividuais", "RotacoesIndividuais", "Fixacao", "Espelhar", "Grupos",
                    "GrupoDaAresta", "Cantos"):
            try:
                for b in barras_de(obj):
                    if prop == "Esqueleto" and b.Esqueleto != obj.Esqueleto:
                        b.Esqueleto = obj.Esqueleto
                    b.touch()
            except Exception:
                pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


class Barra:
    """Uma barra da estrutura. A forma vem de calcular_barra(estrutura, indice)."""

    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if ro:
                    obj.setEditorMode(nome, 1)
        # vínculo "escondido" com a estrutura (o grupo já aponta para a barra: um vínculo comum
        # fecharia um ciclo); a dependência de recálculo vem do esqueleto
        add("App::PropertyLinkHidden", "Estrutura", "Barra", "Estrutura a que a barra pertence")
        novo = "Esqueleto" not in obj.PropertiesList
        _link_global(obj, "Esqueleto", "Barra", "Esqueleto (vem da estrutura)")
        if novo:
            obj.setEditorMode("Esqueleto", 1)
        add("App::PropertyInteger", "Indice", "Barra", "Linha do esqueleto (ordem das arestas)")
        add("App::PropertyString", "Perfil", "Barra", "Perfil usado (troque na estrutura)", True)
        add("App::PropertyLength", "ComprimentoCorte", "Barra", "Comprimento da barra cortada", True)
        add("App::PropertyAngle", "CorteInicio", "Barra", "Ângulo do corte na ponta inicial", True)
        add("App::PropertyAngle", "CorteFim", "Barra", "Ângulo do corte na ponta final", True)
        add("App::PropertyFloat", "MassaLinear", "Barra", "Massa linear do catálogo (kg/m)", True)
        add("App::PropertyFloat", "Massa", "Barra", "Massa da barra (kg)", True)
        add("App::PropertyString", "Material", "Barra", "Material (vem da estrutura)", True)
        add("App::PropertyString", "SituacaoDados", "Barra", "Confirmado no catálogo ou a conferir", True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        est = obj.Estrutura
        if est is None or est.Esqueleto is None:
            return
        eds = arestas(est.Esqueleto)
        if obj.Indice >= len(eds):
            FreeCAD.Console.PrintWarning("Prumo: %s não tem mais linha no esqueleto.\n" % obj.Label)
            return
        if obj.Indice in sem_barra(est):
            return   # a sincronização apaga esta barra
        sol, comp, a0, a1, nome = calcular_barra(est, obj.Indice, eds)
        obj.Shape = sol
        obj.Perfil = nome
        obj.ComprimentoCorte = comp
        obj.CorteInicio = a0
        obj.CorteFim = a1
        it = PrumoPerfis.perfil(nome)
        obj.MassaLinear = float(it["massa"])
        obj.Massa = it["massa"] * comp / 1000.0
        obj.Material = est.Material
        obj.SituacaoDados = "confirmado" if PrumoPerfis.confiavel(it) else "a conferir"

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VPEstrutura:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        return PrumoUtil.icone("estrutura.svg")

    def doubleClicked(self, vobj):
        """Duplo clique: abre o Editar estrutura (o mesmo diálogo da criação, com prévia ao vivo)."""
        est = vobj.Object
        if est.Esqueleto is None:
            return False
        abrir_dialogo(est.Esqueleto, est)
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VPBarra:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        return PrumoUtil.icone("barra.svg")

    def doubleClicked(self, vobj):
        """Duplo clique numa barra: abre o Editar estrutura dela, com a linha da barra marcada."""
        b = vobj.Object
        est = b.Estrutura
        if not eh_estrutura(est) or est.Esqueleto is None:
            return False
        d = abrir_dialogo(est.Esqueleto, est)
        try:
            d._sincronizando = True
            d.tabela.selectRow(b.Indice)
            if d.etiquetas is not None:
                d.etiquetas.destacar(b.Indice)
        finally:
            d._sincronizando = False
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc, esqueleto, perfil=PERFIL_PADRAO, rotacao=0.0, alinhamento="Centro",
          uniao="Meia-esquadria", material="", grupos_extras=None, espelhar=False, linhas_sem_barra=(),
          transacao=True, rotacoes=None):
    """Cria a estrutura e uma barra por linha do esqueleto. Retorna o grupo.

    alinhamento: ponto de fixação (FIXACOES) ou alinhamento antigo (Centro/Topo/Base).
    grupos_extras: [{"nome", "perfil", "giro", "fixacao", "espelhar", "arestas": [índices]}].
    linhas_sem_barra: índices das linhas que ficam sem barra.
    transacao=False: quem chama cuida da transação (diálogo ao vivo)."""
    if PrumoPerfis.perfil(perfil) is None:
        raise ValueError("perfil desconhecido: %s" % perfil)
    eds = arestas(esqueleto)
    if not eds:
        raise ValueError("o esqueleto não tem linhas")
    fixacao = _ALINHAMENTO_PARA_FIXACAO.get(alinhamento, alinhamento)
    if fixacao not in FIXACOES:
        raise ValueError("ponto de fixação desconhecido: %s" % alinhamento)
    if transacao:
        doc.openTransaction("Estrutura soldada")
    est = doc.addObject("App::DocumentObjectGroupPython", "Estrutura")
    Estrutura(est)
    est.Esqueleto = esqueleto
    est.Perfil = perfil
    est.Rotacao = rotacao
    est.Fixacao = fixacao
    est.Espelhar = bool(espelhar)
    est.Uniao = uniao
    est.Material = material
    definir_grupos(est, grupos_extras or [], len(eds), linhas_sem_barra)
    if rotacoes:
        est.RotacoesIndividuais = [float(x) for x in rotacoes]
    if FreeCAD.GuiUp:
        VPEstrutura(est.ViewObject)
    fora = sem_barra(est)
    for i in range(len(eds)):
        if i not in fora:
            _nova_barra(doc, est, i)
    doc.recompute()
    if FreeCAD.GuiUp and transacao:
        try:
            esqueleto.ViewObject.Visibility = False
        except Exception:
            pass
    if transacao:
        doc.commitTransaction()
    return est


def _nova_barra(doc, est, i):
    b = doc.addObject("Part::FeaturePython", "Barra")
    Barra(b)
    b.Estrutura = est
    b.Esqueleto = est.Esqueleto
    b.Indice = i
    if FreeCAD.GuiUp:
        VPBarra(b.ViewObject)
        try:
            b.ViewObject.ShapeAppearance = [_aparencia()]
        except Exception:
            pass
    est.addObject(b)
    return b


def definir_grupos(est, grupos_extras, n_arestas=None, linhas_sem_barra=()):
    """Grava os grupos extras e a que grupo pertence cada aresta (as não citadas ficam no padrão;
    as de linhas_sem_barra ficam sem barra)."""
    import json
    if n_arestas is None:
        n_arestas = len(arestas(est.Esqueleto))
    lst, por_aresta = [], [0] * n_arestas
    for k, g in enumerate(grupos_extras, 1):
        if PrumoPerfis.perfil(g.get("perfil", "")) is None:
            raise ValueError("perfil desconhecido no grupo %s: %s" % (g.get("nome", k), g.get("perfil")))
        fx = g.get("fixacao", "Centro")
        if fx not in FIXACOES:
            raise ValueError("ponto de fixação desconhecido: %s" % fx)
        lst.append(json.dumps({"nome": g.get("nome") or "Grupo %d" % k, "perfil": g["perfil"],
                               "giro": float(g.get("giro", 0.0)), "fixacao": fx,
                               "espelhar": bool(g.get("espelhar", False))}, ensure_ascii=False))
        for i in g.get("arestas", []):
            if 0 <= i < n_arestas:
                por_aresta[i] = k
    for i in linhas_sem_barra or ():
        if 0 <= i < n_arestas:
            por_aresta[i] = SEM_BARRA
    est.Grupos = lst
    est.GrupoDaAresta = por_aresta


def _aparencia():
    import FreeCAD as App
    m = App.Material()
    m.DiffuseColor = (0.55, 0.62, 0.70)
    return m


def eh_estrutura(o):
    return o is not None and o.TypeId == "App::DocumentObjectGroupPython" and \
        "Esqueleto" in o.PropertiesList and "Uniao" in o.PropertiesList


def eh_barra(o):
    return o is not None and o.TypeId == "Part::FeaturePython" and "Indice" in o.PropertiesList and \
        "Estrutura" in o.PropertiesList


def estrutura_de(o):
    """A estrutura do objeto selecionado (ela mesma ou a de uma barra)."""
    if eh_estrutura(o):
        return o
    if eh_barra(o) and eh_estrutura(o.Estrutura):
        return o.Estrutura
    return None


def barras_de(est):
    return sorted([o for o in getattr(est, "Group", []) if o.TypeId == "Part::FeaturePython"
                   and "Indice" in o.PropertiesList], key=lambda o: o.Indice)


def sincronizar_barras(est):
    """Uma barra para cada linha com barra: cria as que faltam e apaga as que sobraram
    (linha sem barra ou que saiu do esqueleto). Retorna (criadas, apagadas)."""
    doc = est.Document
    n = len(arestas(est.Esqueleto))
    fora = sem_barra(est)
    quer = {i for i in range(n) if i not in fora}
    tem = {}
    apagadas = 0
    for b in barras_de(est):
        if b.Indice in quer and b.Indice not in tem:
            tem[b.Indice] = b
        else:
            doc.removeObject(b.Name)
            apagadas += 1
    novas = [_nova_barra(doc, est, i) for i in sorted(quer - set(tem))]
    return novas, apagadas


def atualizar(est):
    """Cria barras para linhas novas do esqueleto e apaga as que sobraram."""
    doc = est.Document
    sincronizar_barras(est)
    for b in barras_de(est):
        b.touch()
    doc.recompute()


def trocar_perfil(barras, perfil=None, giro=None):
    """Troca o perfil e/ou o giro adicional das barras indicadas."""
    if perfil is not None and PrumoPerfis.perfil(perfil) is None:
        raise ValueError("perfil desconhecido: %s" % perfil)
    por_est = {}
    for b in barras:
        por_est.setdefault(b.Estrutura, []).append(b)
    for est, bs in por_est.items():
        n = len(arestas(est.Esqueleto))
        perfis = list(est.PerfisIndividuais) + [""] * max(0, n - len(est.PerfisIndividuais))
        giros = list(est.RotacoesIndividuais) + [0.0] * max(0, n - len(est.RotacoesIndividuais))
        for b in bs:
            if not 0 <= b.Indice < n:
                continue  # barra sem linha no esqueleto (rode "Atualizar estrutura")
            if perfil is not None:
                perfis[b.Indice] = "" if perfil == est.Perfil else perfil
            if giro is not None:
                giros[b.Indice] = float(giro)
        est.PerfisIndividuais = perfis
        est.RotacoesIndividuais = giros
        for b in barras_de(est):
            b.touch()  # vizinhas também: os recortes dependem do perfil ao lado
        est.Document.recompute()


# ============================================================================ cantos
OPCOES_ESQUADRIA = ["Meia-esquadria", "Topo — passa a de menor número", "Topo — passa a de maior número",
                    "Topo — passa a mais vertical", "Topo — passa a mais horizontal"]
OPCOES_T = ["Corte reto", "Recorte pelo contorno"]


class Canto:
    def __init__(self, tipo, i, j, perfil_i, perfil_j, angulo, trat):
        self.tipo = tipo          # "esquadria" (duas pontas) ou "topo_T" (i encosta no meio de j)
        self.i, self.j = i, j
        self.perfis = (perfil_i, perfil_j)
        self.angulo = angulo      # ângulo entre as barras (graus)
        self.tratamento = trat
        self.papel = None         # canto de topo: a que passa é "vertical" / "horizontal" (ou None)

    @property
    def chave_grupo(self):
        return (self.tipo, tuple(sorted(self.perfis)), int(round(self.angulo)))

    def descricao_tratamento(self):
        if self.tipo == "topo_T":
            return OPCOES_T[1] if self.tratamento == TRAT_CONTORNO else OPCOES_T[0]
        if self.tratamento == TRAT_MEIA:
            return "Meia-esquadria"
        if self.papel:
            return "Topo — passa a mais %s" % self.papel
        return "Topo — passa a barra %d" % (_passa(self.tratamento) + 1)


def cantos(est):
    """Cantos de duas barras e ligações em T da estrutura."""
    eds = arestas_ativas(est)
    res = []
    vistos = set()
    for i in range(len(eds)):
        if eds[i] is None:
            continue
        for k, lig in enumerate(ligacoes(eds, i)):
            if lig.tipo not in ("esquadria", "topo_T"):
                continue
            j = lig.outro
            chave = (lig.tipo, min(i, j), max(i, j)) if lig.tipo == "esquadria" else (lig.tipo, i, j)
            if chave in vistos:
                continue
            vistos.add(chave)
            a = _dir(eds[i], k == 0)
            if lig.tipo == "esquadria":
                p = eds[i].valueAt(eds[i].FirstParameter if k == 0 else eds[i].LastParameter)
                oj = eds[j]
                b = _dir(oj, (oj.valueAt(oj.FirstParameter) - p).Length < 1e-4)
                ang = math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))
            else:
                p = eds[i].valueAt(eds[i].FirstParameter if k == 0 else eds[i].LastParameter)
                try:
                    to = FreeCAD.Vector(eds[j].tangentAt(eds[j].Curve.parameter(p))).normalize()
                except Exception:
                    to = _dir(eds[j], True)
                ang = math.degrees(math.acos(min(1.0, abs(a.dot(to)))))
            c = Canto(lig.tipo, i, j, _perfil_da_barra(est, i), _perfil_da_barra(est, j), ang,
                      tratamento(est, i, j, lig.tipo))
            k_passa = _passa(c.tratamento) if lig.tipo == "esquadria" else None
            if k_passa is not None:
                outro = j if k_passa == i else i
                vk, vo = abs(_dir(eds[k_passa], True).z), abs(_dir(eds[outro], True).z)
                if abs(vk - vo) > 1e-6:
                    c.papel = "vertical" if vk > vo else "horizontal"
            res.append(c)
    return res


def agrupar_cantos(lista):
    """Cantos parecidos (mesmo tipo, mesmos perfis, mesmo ângulo) → {chave: [cantos]}."""
    grupos_c = {}
    for c in lista:
        grupos_c.setdefault(c.chave_grupo, []).append(c)
    return grupos_c


def _vertical(eds, i):
    return abs(_dir(eds[i], True).z)


def aplicar_opcao(est, lista, opcao):
    """Aplica uma opção (OPCOES_ESQUADRIA / OPCOES_T) a vários cantos de uma vez."""
    eds = arestas(est.Esqueleto)
    novos = list(getattr(est, "Cantos", []) or [])
    por_chave = {l.partition("=")[0].strip(): l for l in novos}
    for c in lista:
        if c.tipo == "topo_T":
            if opcao not in OPCOES_T:
                raise ValueError("opção inválida para ligação em T: %s" % opcao)
            valor = TRAT_CONTORNO if opcao == OPCOES_T[1] else TRAT_RETO
        else:
            if opcao not in OPCOES_ESQUADRIA:
                raise ValueError("opção inválida para canto: %s" % opcao)
            if opcao == OPCOES_ESQUADRIA[0]:
                valor = TRAT_MEIA
            elif opcao == OPCOES_ESQUADRIA[1]:
                valor = TRAT_PASSA + str(min(c.i, c.j))
            elif opcao == OPCOES_ESQUADRIA[2]:
                valor = TRAT_PASSA + str(max(c.i, c.j))
            else:
                vi, vj = _vertical(eds, c.i), _vertical(eds, c.j)
                quer_vertical = opcao == OPCOES_ESQUADRIA[3]
                if abs(vi - vj) < 1e-6:
                    k = min(c.i, c.j)
                else:
                    k = (c.i if vi > vj else c.j) if quer_vertical else (c.i if vi < vj else c.j)
                valor = TRAT_PASSA + str(k)
        por_chave[chave_canto(c.i, c.j)] = "%s=%s" % (chave_canto(c.i, c.j), valor)
    est.Cantos = list(por_chave.values())


# ============================================================================ lista de corte
NOME_LISTA = "ListaDeCorte"


def lista_de_corte(objs):
    """Linhas (perfil, comprimento mm, ângulo início, ângulo fim, qtd, massa unit., situação)."""
    barras = []
    for o in objs:
        if eh_estrutura(o):
            barras += barras_de(o)
        elif "Indice" in o.PropertiesList and "ComprimentoCorte" in o.PropertiesList:
            barras.append(o)
        elif hasattr(o, "Group"):
            barras += [b for b in o.Group if "ComprimentoCorte" in b.PropertiesList]
    grupos = {}
    ordem = []
    for b in barras:
        comp = round(b.ComprimentoCorte.Value, 1)
        a0, a1 = sorted([round(b.CorteInicio.Value, 1), round(b.CorteFim.Value, 1)])
        chave = (b.Perfil, comp, a0, a1)
        if chave not in grupos:
            grupos[chave] = [b.Perfil, comp, a0, a1, 0, b.MassaLinear * comp / 1000.0, b.SituacaoDados,
                             b.Material]
            ordem.append(chave)
        grupos[chave][4] += 1
    linhas = [grupos[k] for k in ordem]
    linhas.sort(key=lambda l: (l[0], -l[1]))
    return linhas


def gravar_lista_de_corte(doc, linhas):
    sheet = doc.getObject(NOME_LISTA)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", NOME_LISTA)
        sheet.Label = "Lista de corte"
    else:
        sheet.clearAll()
    cab = ["Item", "Perfil", "Comprimento (mm)", "Corte A", "Corte B", "Qtd.", "Massa unit. (kg)",
           "Massa total (kg)", "Material", "Dados"]
    cols = "ABCDEFGHIJ"
    larg = [40, 200, 110, 60, 60, 40, 95, 100, 110, 80]
    for i, (c, w) in enumerate(zip(cab, larg)):
        sheet.set("%s1" % cols[i], c)
        sheet.setColumnWidth(cols[i], w)
    sheet.setStyle("A1:J1", "bold")
    sheet.setBackground("A1:J1", (0.0, 0.227, 0.439))
    sheet.setForeground("A1:J1", (1.0, 1.0, 1.0))
    total = 0.0
    total_m = 0.0
    for n, (perfil, comp, a0, a1, qtd, massa, sit, mat) in enumerate(linhas, 1):
        r = n + 1
        sheet.set("A%d" % r, str(n))
        sheet.set("B%d" % r, "'" + perfil)
        sheet.set("C%d" % r, "'" + fmt(comp, 1))
        sheet.set("D%d" % r, "'%s°" % fmt(a0, 0))
        sheet.set("E%d" % r, "'%s°" % fmt(a1, 0))
        sheet.set("F%d" % r, str(qtd))
        sheet.set("G%d" % r, "'" + fmt(massa, 2))
        sheet.set("H%d" % r, "'" + fmt(massa * qtd, 2))
        sheet.set("I%d" % r, "'" + (mat or "—"))
        sheet.set("J%d" % r, "'" + sit)
        total += massa * qtd
        total_m += comp * qtd / 1000.0
    r = len(linhas) + 2
    sheet.set("B%d" % r, "Total")
    sheet.set("C%d" % r, "'%s m" % fmt(total_m, 2))
    sheet.set("H%d" % r, "'" + fmt(total, 2))
    sheet.setStyle("B%d:H%d" % (r, r), "bold")
    doc.recompute()
    return sheet


# ============================================================================ interface
class SeletorPerfil(QtWidgets.QWidget):
    """Família + perfil, com aviso quando o dado é 'a conferir'. mudou: o perfil escolhido mudou
    (também quando a troca de família cai no primeiro perfil da lista)."""

    mudou = QtCore.Signal()

    def __init__(self, inicial=PERFIL_PADRAO, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QFormLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.familia = QtWidgets.QComboBox()
        for f in PrumoPerfis.familias():
            self.familia.addItem(f["nome"], f["id"])
        self.perfil = QtWidgets.QComboBox()
        self.perfil.setMaxVisibleItems(25)
        self.aviso = QtWidgets.QLabel("")
        self.aviso.setWordWrap(True)
        lay.addRow("Família", self.familia)
        lay.addRow("Perfil", self.perfil)
        lay.addRow("", self.aviso)
        self.familia.currentIndexChanged.connect(self._familia)
        self.perfil.currentIndexChanged.connect(self._aviso)
        self.perfil.currentIndexChanged.connect(lambda *_: self.mudou.emit())
        it = PrumoPerfis.perfil(inicial) or PrumoPerfis.perfil(PERFIL_PADRAO)
        self.familia.setCurrentIndex(max(0, self.familia.findData(it["familia"])))
        self._familia()
        self.perfil.setCurrentIndex(max(0, self.perfil.findData(it["nome"])))
        self._aviso()

    def _familia(self, *_a):
        self.perfil.blockSignals(True)
        self.perfil.clear()
        f = PrumoPerfis.familia(self.familia.currentData())
        for it in f["itens"]:
            marca = "" if PrumoPerfis.confiavel(it) else "  ⚠"
            self.perfil.addItem("%s — %s kg/m%s" % (it["nome"], fmt(it["massa"], 2), marca), it["nome"])
        self.perfil.blockSignals(False)
        self._aviso()
        self.mudou.emit()

    def _aviso(self, *_a):
        it = PrumoPerfis.perfil(self.perfil.currentData() or "")
        if not it:
            self.aviso.setText("")
            return
        ok = PrumoPerfis.confiavel(it)
        f = PrumoPerfis.fonte(it)
        self.aviso.setText("<span style='color:%s'>%s</span><br><span style='color:#5B6876'>Fonte: %s</span>" % (
            "#2E8B6A" if ok else "#B5523F", PrumoPerfis.descricao_status(it), f.get("nome", "")))

    def nome(self):
        return self.perfil.currentData()


def editar(est, padrao, grupos_extras, uniao=None, material=None, linhas_sem_barra=None, rotacoes=None):
    """Aplica o grupo padrão, os grupos extras (com as arestas) e as opções gerais à estrutura.

    As trocas individuais de perfil/giro são zeradas: o diálogo já as mostra como grupos."""
    if PrumoPerfis.perfil(padrao["perfil"]) is None:
        raise ValueError("perfil desconhecido: %s" % padrao["perfil"])
    if padrao.get("fixacao", "Centro") not in FIXACOES:
        raise ValueError("ponto de fixação desconhecido: %s" % padrao.get("fixacao"))
    n = len(arestas(est.Esqueleto))
    if linhas_sem_barra is None:
        linhas_sem_barra = sem_barra(est)
    definir_grupos(est, grupos_extras, n, linhas_sem_barra)
    sincronizar_barras(est)
    est.Perfil = padrao["perfil"]
    est.Rotacao = float(padrao.get("giro", 0.0))
    est.Fixacao = padrao.get("fixacao", "Centro")
    est.Espelhar = bool(padrao.get("espelhar", False))
    if "NomeGrupo" in est.PropertiesList and padrao.get("nome"):
        est.NomeGrupo = padrao["nome"]
    est.PerfisIndividuais = []
    est.RotacoesIndividuais = [float(x) for x in rotacoes] if rotacoes else []
    if uniao is not None:
        est.Uniao = uniao
    if material is not None:
        est.Material = material
    for b in barras_de(est):
        b.touch()
    est.Document.recompute()


def grupos_para_edicao(est):
    """(padrão, extras) da estrutura, com as trocas individuais convertidas em grupos."""
    import copy
    padrao = grupo_padrao(est)
    padrao["giro"] = float(padrao["giro"])
    extras = [dict(g, arestas=[]) for g in grupos(est)]
    n = len(arestas(est.Esqueleto))
    trocas = {}
    for i in range(n):
        k = grupo_da_barra(est, i)
        if k == SEM_BARRA:
            continue
        base = padrao if k == 0 else extras[k - 1]
        par = parametros(est, i)
        # só a troca de perfil vira grupo; o giro próprio da barra fica na própria linha
        # (rotacoes_individuais)
        mudou = par["perfil"] != base["perfil"]
        if mudou:
            chave = (par["perfil"], round(float(base["giro"]), 6), base["fixacao"], bool(base["espelhar"]))
            if chave not in trocas:
                g = copy.deepcopy(base)
                g.update({"nome": "Troca: %s" % par["perfil"], "perfil": par["perfil"],
                          "giro": float(base["giro"]), "arestas": []})
                trocas[chave] = g
                extras.append(g)
            trocas[chave]["arestas"].append(i)
        elif k > 0:
            extras[k - 1]["arestas"].append(i)
    return padrao, extras


def rotacoes_individuais(est):
    """Giro próprio de cada linha (somado ao giro do grupo), em graus."""
    n = len(arestas(est.Esqueleto))
    rots = list(getattr(est, "RotacoesIndividuais", []) or [])
    return [float(rots[i]) if i < len(rots) else 0.0 for i in range(n)]


def _descricao_aresta(e):
    t = _dir(e, True)
    if abs(t.z) > 0.999:
        d = "vertical"
    elif abs(t.z) < 1e-3:
        d = "horizontal"
    else:
        d = "inclinada"
    if not _reta(e):
        d = "curva"
    return "%s mm, %s" % (fmt(e.Length, 0), d)


def _ponto_txt(v):
    return "%s; %s; %s" % (fmt(v.x, 0), fmt(v.y, 0), fmt(v.z, 0))


def _onde_aresta(e):
    """De onde até onde vai a linha (mm, coordenadas globais)."""
    return "de (%s) a (%s)" % (_ponto_txt(e.Vertexes[0].Point), _ponto_txt(e.Vertexes[-1].Point))


def _meio(e):
    try:
        return e.valueAt(e.FirstParameter + 0.5 * (e.LastParameter - e.FirstParameter))
    except Exception:
        return e.CenterOfMass


class EtiquetasNaTela:
    """Números das linhas desenhados na vista 3D (por cima de tudo) enquanto o diálogo está aberto.

    Nada é gravado no arquivo. destacar(i) pinta o número da linha escolhida na tabela."""

    COR = (0.0, 0.227, 0.439)      # azul Prumo #003A70
    COR_DESTAQUE = (0.86, 0.33, 0.0)

    def __init__(self, doc, pontos, textos=None):
        from pivy import coin
        self._coin = coin
        self.vista = None
        self.raiz = None
        self.cores = []
        self.fontes = []
        gd = FreeCADGui.getDocument(doc.Name)
        vista = gd.ActiveView if gd is not None else None
        if vista is None or not hasattr(vista, "getSceneGraph"):
            return
        raiz = coin.SoAnnotation()          # desenha depois da cena, sem ficar escondido atrás das barras
        estilo = coin.SoPickStyle()
        estilo.style = coin.SoPickStyle.UNPICKABLE
        raiz.addChild(estilo)
        for i, p in enumerate(pontos):
            sep = coin.SoSeparator()
            cor = coin.SoBaseColor()
            cor.rgb.setValue(*self.COR)
            fonte = coin.SoFont()
            fonte.size = 18
            fonte.name = "Arial:Bold"
            tr = coin.SoTranslation()
            tr.translation.setValue(p.x, p.y, p.z)
            txt = coin.SoText2()
            txt.string = str(i + 1) if textos is None else str(textos[i])
            txt.justification = coin.SoText2.CENTER
            for n in (cor, fonte, tr, txt):
                sep.addChild(n)
            raiz.addChild(sep)
            self.cores.append(cor)
            self.fontes.append(fonte)
        vista.getSceneGraph().addChild(raiz)
        self.vista, self.raiz = vista, raiz
        self.destacado = None

    def __len__(self):
        return len(self.cores)

    def destacar(self, i):
        """Destaca a etiqueta i (ou uma lista delas)."""
        alvos = set(i) if isinstance(i, (list, tuple, set)) else {i}
        for k, (cor, fonte) in enumerate(zip(self.cores, self.fontes)):
            on = k in alvos
            cor.rgb.setValue(*(self.COR_DESTAQUE if on else self.COR))
            fonte.size = 26 if on else 18
        self.destacado = i

    def remover(self):
        if self.raiz is not None and self.vista is not None:
            try:
                self.vista.getSceneGraph().removeChild(self.raiz)
            except Exception:
                pass
        self.raiz = None
        self.vista = None


ROTULO_SEM_BARRA = "— sem barra —"


class DialogoEstrutura(QtWidgets.QDialog):
    """Criação e edição da estrutura: grupos de barras (perfil, giro, fixação, espelhar) e as
    linhas do esqueleto de cada grupo. Fica aberto enquanto se seleciona na tela.

    ao_vivo=True (como no SolidWorks): clicar numa linha do desenho põe a linha no grupo atual e a
    barra aparece na hora; perfil, giro, ponto de fixação, espelhar e cantos também atualizam a
    prévia na hora. Tudo fica numa transação: Aplicar grava, Cancelar desfaz.
    linhas: na criação, as linhas que começam com barra (None = todas)."""

    def showEvent(self, ev):
        import PrumoPainel
        PrumoPainel.caber_na_tela(self)      # notebook: rolagem em vez de diálogo cortado
        super().showEvent(ev)

    def __init__(self, esqueleto, est=None, parent=None, ao_vivo=False, linhas=None):
        super().__init__(parent)
        self.esqueleto = esqueleto
        self.est = est
        self.resultado = None
        self.ao_vivo = bool(ao_vivo)
        self._transacao = False
        self._criada = False
        self._vis_esqueleto = None
        self.setWindowTitle("Editar estrutura soldada" if est else "Estrutura soldada")
        self.setMinimumSize(820, 600)
        self.resize(860, 800)
        self.eds = arestas(esqueleto)
        if est is not None:
            padrao, extras = grupos_para_edicao(est)
            padrao["nome"] = padrao.get("nome") or "Padrão"
        else:
            g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
            padrao = {"nome": "Padrão", "perfil": g.GetString("UltimoPerfil", PERFIL_PADRAO), "giro": 0.0,
                      "fixacao": "Centro", "espelhar": False}
            if PrumoPerfis.perfil(padrao["perfil"]) is None:
                padrao["perfil"] = PERFIL_PADRAO
            extras = []
        self.grupos_ed = [dict(padrao)] + [dict(x) for x in extras]
        self.da_aresta = [0] * len(self.eds)
        for k, g in enumerate(extras, 1):
            for i in g.get("arestas", []):
                if 0 <= i < len(self.eds):
                    self.da_aresta[i] = k
        self.giro_linha = rotacoes_individuais(est) if est is not None else [0.0] * len(self.eds)
        if est is not None:
            for i in sem_barra(est):
                if i < len(self.da_aresta):
                    self.da_aresta[i] = SEM_BARRA
        elif linhas is not None:
            quer = set(linhas)
            self.da_aresta = [0 if i in quer else SEM_BARRA for i in range(len(self.eds))]
        if est is None and self.ao_vivo:
            # nasce zerado: o primeiro passo é criar um grupo (linhas já selecionadas viram o Grupo 1)
            if linhas:
                self.grupos_ed = [dict(padrao, nome="Grupo 1")]
            else:
                self.grupos_ed = []
                self.da_aresta = [SEM_BARRA] * len(self.eds)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._aplicar_ao_vivo)
        self._montar()
        self._carregando = False
        self.lista.setCurrentRow(0)
        # números das linhas na tela e seleção nos dois sentidos (tabela ↔ vista 3D)
        self.etiquetas = None
        self._sincronizando = False
        try:
            self.etiquetas = EtiquetasNaTela(esqueleto.Document, [_meio(e) for e in self.eds])
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: números das linhas na tela: %s\n" % exc)
        self._observando = False
        try:
            FreeCADGui.Selection.addObserver(self)
            self._observando = True
        except Exception:
            pass
        self.tabela.itemSelectionChanged.connect(self._linhas_escolhidas)
        if self.ao_vivo:
            self._iniciar_ao_vivo()

    # ------------------------------------------------------------------ montagem
    def _montar(self):
        import PrumoPainel as P
        padrao_perfil = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoPerfil", PERFIL_PADRAO)
        if PrumoPerfis.perfil(padrao_perfil) is None:
            padrao_perfil = PERFIL_PADRAO
        self.setStyleSheet(P.qss())
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(10)
        if self.ao_vivo:
            self.mensagem = P.Mensagem("Clique nas linhas do desenho: cada linha clicada ganha a barra do grupo "
                                       "escolhido na hora (clique de novo para tirar). Para outro perfil, crie um "
                                       "grupo e clique nas linhas dele. Tudo é prévia: Aplicar grava, Cancelar "
                                       "desfaz.")
        else:
            self.mensagem = P.Mensagem("1. Escolha o perfil do grupo Padrão (vale para todas as linhas). "
                                       "2. Para outro perfil em algumas linhas, crie um grupo e ponha as linhas "
                                       "nele. 3. Confira os cantos e o material.")
        lay.addWidget(self.mensagem)
        topo = QtWidgets.QHBoxLayout()
        topo.setSpacing(10)
        # grupos
        card_grupos, col = P.bloco("Grupos de barras", "tipo")
        self.lista = QtWidgets.QListWidget()
        self.lista.setMinimumWidth(250)
        self.lista.setMaximumWidth(300)
        col.addWidget(self.lista)
        bl = QtWidgets.QHBoxLayout()
        self.bt_novo = QtWidgets.QPushButton("Novo grupo")
        self.bt_remover = QtWidgets.QPushButton("Remover")
        bl.addWidget(self.bt_novo)
        bl.addWidget(self.bt_remover)
        col.addLayout(bl)
        card_grupos.setMaximumWidth(330)
        topo.addWidget(card_grupos)
        # editor do grupo
        ed, fl = P.bloco("Perfil do grupo", "largura", QtWidgets.QFormLayout)
        self.nome = QtWidgets.QLineEdit()
        self.sel = SeletorPerfil(self.grupos_ed[0]["perfil"] if self.grupos_ed else padrao_perfil)
        self.giro = QtWidgets.QDoubleSpinBox()
        self.giro.setRange(-360, 360)
        self.giro.setSuffix(" °")
        self.giro.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
        self.fixacao = QtWidgets.QComboBox()
        self.fixacao.addItems(FIXACOES)
        self.fixacao.setToolTip("Ponto da seção que fica sobre a linha do esboço (localizar perfil)")
        self.espelhar = QtWidgets.QCheckBox("Espelhar a seção (abas do U / da cantoneira para o outro lado)")
        fl.addRow(P.rotulo("texto", "Nome", "Nome do grupo (aparece na lista de corte)"), self.nome)
        fl.addRow(self.sel)
        fl.addRow(P.rotulo("angulo", "Giro", "Gira a seção em volta da linha"), self.giro)
        fl.addRow(P.rotulo("posicao", "Ponto de fixação", "Ponto da seção que fica sobre a linha"),
                  self.fixacao)
        fl.addRow("", self.espelhar)
        self.sel.aviso.setMinimumHeight(self.sel.aviso.fontMetrics().lineSpacing() * 4 + 6)
        self.sel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        ed.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        topo.addWidget(ed, 1)
        self.editor = ed
        lay.addLayout(topo, 1)
        # linhas do esqueleto
        card_linhas, cl = P.bloco("Linhas do esqueleto", "selecao")
        lay.addWidget(card_linhas, 2)
        dica = QtWidgets.QLabel("O número de cada linha aparece sobre o desenho. Clique numa linha da tabela "
                                "para destacá-la na tela" + (", ou clique no desenho para pôr a linha no grupo "
                                "escolhido." if self.ao_vivo else ", e escolha o grupo de cada linha."))
        dica.setWordWrap(True)
        dica.setObjectName("PrumoDica")
        cl.addWidget(dica)
        self.tabela = QtWidgets.QTableWidget(len(self.eds), 5)
        self.tabela.setHorizontalHeaderLabels(["Linha", "Medida", "Onde (mm)", "Grupo", "Giro da barra"])
        self.tabela.horizontalHeaderItem(4).setToolTip("Giro só desta barra, somado ao giro do grupo")
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.combos = []
        self.giros = []
        for i, e in enumerate(self.eds):
            barra = self._barra_da_linha(i)
            it = QtWidgets.QTableWidgetItem("%d" % (i + 1) + (" · %s" % barra.Label if barra is not None else ""))
            it.setToolTip("Linha %d do esboço%s" % (i + 1, (" — barra %s na árvore" % barra.Label)
                                                         if barra is not None else ""))
            self.tabela.setItem(i, 0, it)
            self.tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(_descricao_aresta(e)))
            self.tabela.setItem(i, 2, QtWidgets.QTableWidgetItem(_onde_aresta(e)))
            for c in (0, 1, 2):
                self.tabela.item(i, c).setFlags(self.tabela.item(i, c).flags() & ~QtCore.Qt.ItemIsEditable)
            cb = QtWidgets.QComboBox()
            cb.currentIndexChanged.connect(lambda k, i=i: self._linha_mudou(i, k))
            self.tabela.setCellWidget(i, 3, cb)
            self.combos.append(cb)
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(-360.0, 360.0)
            sp.setSingleStep(15.0)
            sp.setDecimals(1)
            sp.setSuffix(" °")
            sp.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
            sp.setValue(self.giro_linha[i])
            sp.setToolTip("Giro só desta barra (somado ao giro do grupo)")
            sp.valueChanged.connect(lambda v, i=i: self._giro_mudou(i, v))
            self.tabela.setCellWidget(i, 4, sp)
            self.giros.append(sp)
        self.tabela.resizeColumnsToContents()
        self.tabela.setMinimumHeight(min(200, 34 + 30 * max(1, len(self.eds))))
        cl.addWidget(self.tabela, 1)
        bt = QtWidgets.QHBoxLayout()
        self.bt_pegar = QtWidgets.QPushButton("Pegar seleção da tela")
        self.bt_mostrar = QtWidgets.QPushButton("Mostrar linhas do grupo")
        self.bt_pegar.setToolTip("Põe no grupo escolhido as linhas (ou barras) já selecionadas na tela")
        self.bt_mostrar.setToolTip("Seleciona na tela as linhas do grupo escolhido")
        self.bt_todas = QtWidgets.QPushButton("Todas as linhas")
        self.bt_todas.setToolTip("Põe todas as linhas do esboço no grupo escolhido (todas ganham barra)")
        self.bt_esboco = QtWidgets.QPushButton("Mostrar esboço")
        self.bt_esboco.setCheckable(True)
        self.bt_esboco.setToolTip("Mostra ou esconde as linhas do esboço (esqueleto) na tela")
        try:
            self.bt_esboco.setChecked(bool(self.esqueleto.ViewObject.Visibility))
        except Exception:
            pass
        self.bt_girar = QtWidgets.QPushButton("Girar 90°")
        self.bt_girar.setToolTip("Gira 90° só as barras das linhas marcadas na tabela")
        bt.addWidget(self.bt_esboco)
        bt.addWidget(self.bt_todas)
        bt.addWidget(self.bt_girar)
        bt.addWidget(self.bt_pegar)
        bt.addWidget(self.bt_mostrar)
        bt.addStretch(1)
        cl.addLayout(bt)
        # opções gerais
        card_op, fg = P.bloco("Opções", "chanfro", QtWidgets.QFormLayout)
        self.uniao = QtWidgets.QComboBox()
        self.uniao.addItems(UNIOES)
        self.uniao.setToolTip("Cantos de duas barras. Cada canto pode ser trocado depois em \"Cantos\".")
        self.material = QtWidgets.QLineEdit(
            self.est.Material if self.est is not None else
            FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialPerfil", ""))
        self.material.setPlaceholderText("ex.: ASTM A572 Gr. 50")
        if self.est is not None:
            self.uniao.setCurrentText(self.est.Uniao)
        fg.addRow(P.rotulo("chanfro", "Cantos (padrão)", "Cada canto pode ser trocado depois em Cantos"),
                  self.uniao)
        fg.addRow(P.rotulo("material", "Material", "Vai para a lista de corte e a lista de materiais"),
                  self.material)
        lay.addWidget(card_op)
        self.aviso = QtWidgets.QLabel("")
        self.aviso.setStyleSheet("color:#B5523F")
        lay.addWidget(self.aviso)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar" if self.est else "Criar estrutura")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._recarregar_lista()
        # sinais
        self.lista.currentRowChanged.connect(self._grupo_escolhido)
        self.bt_novo.clicked.connect(self.novo_grupo)
        self.bt_remover.clicked.connect(self.remover_grupo)
        self.bt_pegar.clicked.connect(self.pegar_selecao)
        self.bt_mostrar.clicked.connect(self.mostrar_grupo)
        self.bt_todas.clicked.connect(lambda: self.atribuir(range(len(self.eds))))
        self.bt_esboco.toggled.connect(self.mostrar_esboco)
        self.bt_girar.clicked.connect(lambda: self.girar_linhas(
            sorted({ix.row() for ix in self.tabela.selectedIndexes()}), 90.0))
        self.nome.textEdited.connect(self._editado)
        self.sel.mudou.connect(self._editado)
        self.giro.valueChanged.connect(self._editado)
        self.fixacao.currentIndexChanged.connect(self._editado)
        self.espelhar.toggled.connect(self._editado)
        self.uniao.currentIndexChanged.connect(lambda *_: self._agendar())
        self.material.editingFinished.connect(self._agendar)

    # ------------------------------------------------------------------ tabela ↔ tela
    def _barra_da_linha(self, i):
        if self.est is None:
            return None
        for b in getattr(self.est, "Group", []):
            if eh_barra(b) and b.Indice == i:
                return b
        return None

    def _linhas_escolhidas(self):
        """Linha(s) escolhida(s) na tabela: destaca o número e seleciona a linha (ou a barra) na tela."""
        if self._sincronizando:
            return
        linhas = sorted({ix.row() for ix in self.tabela.selectedIndexes()})
        if self.etiquetas is not None:
            self.etiquetas.destacar(linhas[0] if len(linhas) == 1 else None)
        self._sincronizando = True
        try:
            FreeCADGui.Selection.clearSelection()
            visivel_esq = getattr(getattr(self.esqueleto, "ViewObject", None), "Visibility", True)
            for i in linhas:
                barra = self._barra_da_linha(i)
                if barra is not None and not visivel_esq:
                    FreeCADGui.Selection.addSelection(barra)
                else:
                    FreeCADGui.Selection.addSelection(self.esqueleto, "Edge%d" % (i + 1))
        except Exception:
            pass
        finally:
            self._sincronizando = False

    def _indice_da_selecao(self, obj, sub):
        if obj is self.esqueleto and sub.startswith("Edge") and sub[4:].isdigit():
            return int(sub[4:]) - 1
        if eh_barra(obj) and obj.Esqueleto == self.esqueleto:
            return obj.Indice
        return None

    # observador de seleção do FreeCAD: clique na tela → linha na tabela
    def addSelection(self, doc, obj, sub, pnt):
        if self._sincronizando:
            return
        try:
            o = FreeCAD.getDocument(doc).getObject(obj)
            i = self._indice_da_selecao(o, sub or "")
        except Exception:
            return
        if i is None or not (0 <= i < self.tabela.rowCount()):
            return
        if self.ao_vivo:
            # clique no desenho: a linha entra no grupo atual (ou sai, se já estava nele)
            QtCore.QTimer.singleShot(0, lambda i=i: self.clicar_linha(i))
            return
        self._sincronizando = True
        try:
            self.tabela.selectRow(i)
            self.tabela.scrollToItem(self.tabela.item(i, 0))
            if self.etiquetas is not None:
                self.etiquetas.destacar(i)
        except RuntimeError:
            pass
        finally:
            self._sincronizando = False

    def setSelection(self, doc):
        pass

    def removeSelection(self, doc, obj, sub):
        pass

    def clearSelection(self, doc):
        pass

    def limpar_tela(self):
        if getattr(self, "_observando", False):
            try:
                FreeCADGui.Selection.removeObserver(self)
            except Exception:
                pass
            self._observando = False
        if getattr(self, "etiquetas", None) is not None:
            self.etiquetas.remover()
            self.etiquetas = None

    def done(self, r):
        self._timer.stop()
        if self.ao_vivo and self._transacao:
            self._desfazer_ao_vivo()
        self.limpar_tela()
        super().done(r)

    def closeEvent(self, ev):
        self._timer.stop()
        if self.ao_vivo and self._transacao:
            self._desfazer_ao_vivo()
        self.limpar_tela()
        super().closeEvent(ev)

    # ------------------------------------------------------------------ prévia ao vivo
    def _agendar(self):
        if self.ao_vivo and self._transacao and not getattr(self, "_carregando", True):
            self._timer.start()

    def _iniciar_ao_vivo(self):
        doc = self.esqueleto.Document
        doc.openTransaction("Editar estrutura" if self.est is not None else "Estrutura soldada")
        self._transacao = True
        try:
            self._vis_esqueleto = self.esqueleto.ViewObject.Visibility
        except Exception:
            pass
        self.bt_esboco.setChecked(True)   # as linhas sem barra precisam aparecer para o clique
        self.mostrar_esboco(True)
        self._criar_se_preciso()
        self._estado_sem_grupo()

    def _criar_se_preciso(self):
        """Na criação, a estrutura (prévia) nasce quando existe o primeiro grupo."""
        if self.est is None and self.grupos_ed and self._transacao:
            padrao, extras = self.dados()
            self.est = criar(self.esqueleto.Document, self.esqueleto, padrao["perfil"], padrao["giro"],
                             padrao["fixacao"], self.uniao.currentText(), self.material.text().strip(), extras,
                             padrao["espelhar"], self.linhas_sem_barra(), transacao=False,
                             rotacoes=self.giro_linha)
            self.est.NomeGrupo = padrao.get("nome", "Grupo 1")
            self._criada = True
            self._atualizar_rotulos_tabela()

    def _estado_sem_grupo(self):
        tem = bool(self.grupos_ed)
        self.editor.setEnabled(tem)
        for b in (self.bt_todas, self.bt_pegar, self.bt_mostrar):
            b.setEnabled(tem)
        if not tem:
            self.aviso.setText("")
            self.mensagem.mostrar("Comece criando um grupo de barras (botão Novo grupo): escolha o perfil e "
                                  "clique nas linhas do desenho que levam esse perfil.", "info")
        elif self.ao_vivo:
            self.mensagem.mostrar("Clique nas linhas do desenho: cada linha clicada ganha a barra do grupo "
                                  "escolhido na hora (clique de novo para tirar). Para outro perfil, crie outro "
                                  "grupo. Tudo é prévia: Aplicar grava, Cancelar desfaz.", "info")

    def mostrar_esboco(self, on):
        try:
            self.esqueleto.ViewObject.Visibility = bool(on)
        except Exception:
            pass

    def _aplicar_ao_vivo(self):
        """Leva o que está no diálogo para a estrutura (prévia)."""
        if not (self.ao_vivo and self._transacao):
            return
        self._criar_se_preciso()
        if self.est is None:
            return
        padrao, extras = self.dados()
        try:
            editar(self.est, padrao, extras, self.uniao.currentText(), self.material.text().strip(),
                   self.linhas_sem_barra(), self.giro_linha)
            self.aviso.setText("")
        except Exception as ex:
            self.aviso.setText(str(ex))
        self._atualizar_rotulos_tabela()

    def _atualizar_rotulos_tabela(self):
        for i in range(self.tabela.rowCount()):
            b = self._barra_da_linha(i)
            it = self.tabela.item(i, 0)
            if it is not None:
                it.setText("%d" % (i + 1) + (" · %s" % b.Label if b is not None else " · sem barra"))
        self.tabela.resizeColumnToContents(0)

    def clicar_linha(self, i):
        """Linha clicada no desenho: entra no grupo atual; se já estava nele, fica sem barra."""
        if not (0 <= i < len(self.da_aresta)):
            return
        if not self.grupos_ed:
            self.aviso.setText("Crie um grupo primeiro (botão Novo grupo).")
            return
        k = max(0, self.lista.currentRow())
        self.da_aresta[i] = SEM_BARRA if self.da_aresta[i] == k else k
        self._recarregar_lista()
        self._sincronizando = True
        try:
            self.tabela.selectRow(i)
            if self.etiquetas is not None:
                self.etiquetas.destacar(i)
            FreeCADGui.Selection.clearSelection()
        except RuntimeError:
            pass
        finally:
            self._sincronizando = False
        self._timer.stop()
        self._aplicar_ao_vivo()      # clique: atualiza já (sem esperar)

    def _confirmar_ao_vivo(self):
        self._timer.stop()
        self._aplicar_ao_vivo()
        if self.aviso.text():
            raise ValueError(self.aviso.text())
        doc = self.esqueleto.Document
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        if self.grupos_ed:
            g.SetString("UltimoPerfil", self.grupos_ed[0]["perfil"])
        g.SetString("UltimoMaterialPerfil", self.material.text().strip())
        doc.commitTransaction()
        self._transacao = False
        try:
            self.esqueleto.ViewObject.Visibility = False if barras_de(self.est) else bool(self._vis_esqueleto)
        except Exception:
            pass
        self.resultado = self.est
        return self.resultado

    def _desfazer_ao_vivo(self):
        doc = self.esqueleto.Document
        est_nome = self.est.Name if (self._criada and self.est is not None) else None
        try:
            doc.abortTransaction()
        except Exception:
            pass
        self._transacao = False
        # sem Desfazer ligado no documento: tira à mão a estrutura criada pela prévia
        if est_nome and doc.getObject(est_nome) is not None:
            for b in barras_de(doc.getObject(est_nome)):
                doc.removeObject(b.Name)
            doc.removeObject(est_nome)
        if self._criada:
            self.est = None
        doc.recompute()
        try:
            if self._vis_esqueleto is not None:
                self.esqueleto.ViewObject.Visibility = self._vis_esqueleto
        except Exception:
            pass

    def _rotulo(self, k):
        g = self.grupos_ed[k]
        n = sum(1 for x in self.da_aresta if x == k)
        return "%s — %s (%d)" % (g["nome"], g["perfil"], n)

    def _recarregar_lista(self):
        atual = max(0, self.lista.currentRow())
        self.lista.blockSignals(True)
        self.lista.clear()
        for k in range(len(self.grupos_ed)):
            self.lista.addItem(self._rotulo(k))
        if self.grupos_ed:
            self.lista.setCurrentRow(min(atual, len(self.grupos_ed) - 1))
        self.lista.blockSignals(False)
        nomes = [g["nome"] for g in self.grupos_ed] + [ROTULO_SEM_BARRA]
        for i, cb in enumerate(self.combos):
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(nomes)
            k = self.da_aresta[i]
            cb.setCurrentIndex(len(self.grupos_ed) if k == SEM_BARRA else k)
            cb.blockSignals(False)
        self.bt_remover.setEnabled(self.lista.currentRow() > 0 or (self.ao_vivo and bool(self.grupos_ed)))

    # ------------------------------------------------------------------ edição
    def _grupo_escolhido(self, k):
        if k < 0:
            return
        g = self.grupos_ed[k]
        self._carregando = True
        self.nome.setText(g["nome"])
        self.nome.setEnabled(k > 0 or self.ao_vivo)
        it = PrumoPerfis.perfil(g["perfil"])
        if it:
            self.sel.familia.setCurrentIndex(max(0, self.sel.familia.findData(it["familia"])))
            self.sel.perfil.setCurrentIndex(max(0, self.sel.perfil.findData(it["nome"])))
        self.giro.setValue(float(g.get("giro", 0.0)))
        self.fixacao.setCurrentText(g.get("fixacao", "Centro"))
        self.espelhar.setChecked(bool(g.get("espelhar", False)))
        self._carregando = False
        self.bt_remover.setEnabled(k > 0 or self.ao_vivo)

    def _editado(self, *_a):
        if getattr(self, "_carregando", True):
            return
        k = self.lista.currentRow()
        if k < 0:
            return
        g = self.grupos_ed[k]
        if k > 0 or self.ao_vivo:
            g["nome"] = self.nome.text().strip() or "Grupo %d" % (k + 1)
        g["perfil"] = self.sel.nome() or g["perfil"]
        g["giro"] = self.giro.value()
        g["fixacao"] = self.fixacao.currentText()
        g["espelhar"] = self.espelhar.isChecked()
        self.lista.item(k).setText(self._rotulo(k))
        for cb in self.combos:
            cb.setItemText(k, g["nome"])
        self._agendar()

    def _linha_mudou(self, i, k):
        if k < 0:
            return
        self.da_aresta[i] = SEM_BARRA if k >= len(self.grupos_ed) else k
        for j in range(len(self.grupos_ed)):
            self.lista.item(j).setText(self._rotulo(j))
        self._agendar()

    def _giro_mudou(self, i, v):
        self.giro_linha[i] = float(v)
        self._agendar()

    def girar_linhas(self, linhas, graus=90.0):
        """Soma o giro às barras indicadas (só elas, não o grupo)."""
        if not linhas:
            self.aviso.setText("Marque na tabela as linhas que vão girar.")
            return
        self.aviso.setText("")
        for i in linhas:
            novo = (self.giro_linha[i] + graus + 180.0) % 360.0 - 180.0
            self.giros[i].blockSignals(True)
            self.giros[i].setValue(novo)
            self.giros[i].blockSignals(False)
            self.giro_linha[i] = novo
        self._agendar()

    def novo_grupo(self):
        if self.grupos_ed:
            perfil = self.grupos_ed[max(0, self.lista.currentRow())]["perfil"]
        else:
            perfil = self.dados()[0]["perfil"]
        k = len(self.grupos_ed)
        self.grupos_ed.append({"nome": "Grupo %d" % (k + 1 if self.ao_vivo else k), "perfil": perfil,
                               "giro": 0.0, "fixacao": "Centro", "espelhar": False})
        self._recarregar_lista()
        self.lista.setCurrentRow(k)
        self._grupo_escolhido(k)
        if self.ao_vivo:
            self._estado_sem_grupo()
            self._criar_se_preciso()
            self.nome.setFocus()
            self.nome.selectAll()
        return k

    def remover_grupo(self):
        k = self.lista.currentRow()
        if self.ao_vivo:
            # ao vivo: as linhas do grupo removido ficam sem barra (qualquer grupo pode sair)
            if k < 0 or not self.grupos_ed:
                return
            del self.grupos_ed[k]
            self.da_aresta = [SEM_BARRA if x == k else (x - 1 if x > k else x) for x in self.da_aresta]
            self._recarregar_lista()
            if self.grupos_ed:
                self.lista.setCurrentRow(max(0, k - 1))
                self._grupo_escolhido(self.lista.currentRow())
            self._estado_sem_grupo()
            self._agendar()
            return
        if k <= 0:
            return
        del self.grupos_ed[k]
        self.da_aresta = [0 if x == k else (x - 1 if x > k else x) for x in self.da_aresta]
        self.lista.setCurrentRow(k - 1)
        self._recarregar_lista()
        self._grupo_escolhido(self.lista.currentRow())
        self._agendar()

    def atribuir(self, indices, k=None):
        """Põe as linhas indicadas no grupo k (padrão: o grupo atual)."""
        if k is None:
            k = self.lista.currentRow()
        for i in indices:
            if 0 <= i < len(self.eds):
                self.da_aresta[i] = k
        self._recarregar_lista()
        self._agendar()

    def pegar_selecao(self):
        idx = []
        for s in FreeCADGui.Selection.getSelectionEx():
            if s.Object == self.esqueleto:
                idx += [int(n[4:]) - 1 for n in s.SubElementNames if n.startswith("Edge") and n[4:].isdigit()]
            elif eh_barra(s.Object) and s.Object.Esqueleto == self.esqueleto:
                idx.append(s.Object.Indice)
        if not idx:
            self.aviso.setText("Nenhuma linha do esqueleto (nem barra desta estrutura) selecionada na tela.")
            return
        self.aviso.setText("")
        self.atribuir(idx)

    def mostrar_grupo(self):
        k = self.lista.currentRow()
        FreeCADGui.Selection.clearSelection()
        nomes = ["Edge%d" % (i + 1) for i, x in enumerate(self.da_aresta) if x == k]
        if nomes:
            try:
                FreeCADGui.Selection.addSelection(self.esqueleto, nomes)
            except Exception:
                pass

    # ------------------------------------------------------------------ resultado
    def dados(self):
        if not self.grupos_ed:   # sem grupo: tudo sem barra, o perfil da estrutura fica como está
            base = grupo_padrao(self.est) if self.est is not None else {
                "nome": "Grupo 1", "perfil": FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString(
                    "UltimoPerfil", PERFIL_PADRAO), "giro": 0.0, "fixacao": "Centro", "espelhar": False}
            if PrumoPerfis.perfil(base["perfil"]) is None:
                base["perfil"] = PERFIL_PADRAO
            return dict(base), []
        padrao = dict(self.grupos_ed[0])
        extras = []
        usados = {}
        for k, g in enumerate(self.grupos_ed[1:], 1):
            linhas = [i for i, x in enumerate(self.da_aresta) if x == k]
            if not linhas:
                continue  # grupo vazio não vai para a estrutura
            usados[k] = len(extras) + 1
            extras.append(dict(g, arestas=linhas))
        return padrao, extras

    def linhas_sem_barra(self):
        return [i for i, x in enumerate(self.da_aresta) if x == SEM_BARRA]

    def aplicar(self):
        """Cria ou atualiza a estrutura. Retorna o objeto (ou levanta ValueError)."""
        if all(x == SEM_BARRA for x in self.da_aresta):
            raise ValueError("Nenhuma linha com barra: clique nas linhas do desenho.")
        if self.ao_vivo:
            return self._confirmar_ao_vivo()
        padrao, extras = self.dados()
        doc = self.esqueleto.Document
        uniao = self.uniao.currentText()
        material = self.material.text().strip()
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        g.SetString("UltimoPerfil", padrao["perfil"])
        g.SetString("UltimoMaterialPerfil", material)
        if self.est is None:
            self.resultado = criar(doc, self.esqueleto, padrao["perfil"], padrao["giro"], padrao["fixacao"],
                                   uniao, material, extras, padrao["espelhar"], self.linhas_sem_barra(),
                                   rotacoes=self.giro_linha)
        else:
            doc.openTransaction("Editar estrutura")
            try:
                editar(self.est, padrao, extras, uniao, material, self.linhas_sem_barra(), self.giro_linha)
            except Exception:
                doc.abortTransaction()
                raise
            doc.commitTransaction()
            self.resultado = self.est
        return self.resultado

    def _ok(self):
        try:
            self.aplicar()
        except ValueError as ex:
            self.aviso.setText(str(ex))
            return
        self.accept()


_dialogos = []


def _linhas_pre_selecionadas(esqueleto):
    """Linhas do esboço já selecionadas na tela (Edge3 → 2); vazio se o esboço inteiro foi escolhido."""
    idx = []
    try:
        for s in FreeCADGui.Selection.getSelectionEx():
            if s.Object == esqueleto:
                idx += [int(n[4:]) - 1 for n in s.SubElementNames if n.startswith("Edge") and n[4:].isdigit()]
    except Exception:
        pass
    return idx


def abrir_dialogo(esqueleto, est=None, linhas=None):
    """Abre o diálogo com a prévia ao vivo. Na criação, começam com barra as linhas já
    selecionadas no desenho (nenhuma, se o esboço inteiro foi escolhido: clique nas linhas)."""
    if est is None and linhas is None:
        linhas = _linhas_pre_selecionadas(esqueleto)
    FreeCADGui.Selection.clearSelection()
    d = DialogoEstrutura(esqueleto, est, FreeCADGui.getMainWindow(), ao_vivo=True, linhas=linhas)
    d.setWindowModality(QtCore.Qt.NonModal)
    d.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    _dialogos.append(d)
    d.finished.connect(lambda _r, d=d: _dialogos.remove(d) if d in _dialogos else None)
    d.show()
    return d


def _filtro_esqueleto(obj, subs):
    if eh_estrutura(obj) or eh_barra(obj):
        return []
    try:
        ok = bool(arestas(obj)) and not (hasattr(obj, "Shape") and obj.Shape.Solids)
    except Exception:
        ok = False
    return [(obj.Label, obj)] if ok else []


def _filtro_estrutura_ou_barras(obj, subs):
    if eh_estrutura(obj):
        return [("%s (todos os cantos)" % obj.Label, obj)]
    return [(b.Label, b) for b in barras_do_item(obj, subs)]


def _esqueleto_selecionado():
    for o in FreeCADGui.Selection.getSelection():
        if eh_estrutura(o) or eh_barra(o):
            continue
        try:
            if arestas(o) and not (hasattr(o, "Shape") and o.Shape.Solids):
                return o
        except Exception:
            continue
    return None


class CmdEstrutura:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("estrutura.svg"),
                "MenuText": "Estrutura soldada",
                "ToolTip": "Cria barras de perfil (W, U, I, cantoneira, tubo) sobre as linhas do esboço "
                           "selecionado, em grupos de perfis, com tratamento dos cantos."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        esq = _esqueleto_selecionado()
        if esq is None:
            import PrumoSelecao
            PrumoSelecao.pedir("Estrutura soldada", "Escolha o esboço com as linhas de centro da estrutura "
                               "(na vista ou na árvore).", [("Esboço (esqueleto)", _filtro_esqueleto, 1, 1)],
                               lambda esqs: abrir_dialogo(esqs[0]))
            return
        abrir_dialogo(esq)


class CmdEditarEstrutura:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("estrutura_editar.svg"),
                "MenuText": "Editar estrutura",
                "ToolTip": "Grupos de barras: perfil, giro, ponto de fixação e espelhamento de cada grupo, "
                           "e a que grupo pertence cada linha do esqueleto."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        for o in FreeCADGui.Selection.getSelection():
            est = estrutura_de(o)
            if est is not None:
                abrir_dialogo(est.Esqueleto, est)
                return
        import PrumoSelecao
        PrumoSelecao.pedir("Editar estrutura", "Escolha a estrutura (ou uma barra dela).",
                           [("Estrutura", "estruturas", 1, 1)], lambda ests: abrir_dialogo(ests[0].Esqueleto, ests[0]))


def barras_da_selecao(sel=None):
    """Barras indicadas pela seleção: barras, estruturas inteiras ou linhas do esqueleto."""
    if sel is None:
        sel = FreeCADGui.Selection.getSelectionEx()
    res = []

    def add(b):
        if b not in res:
            res.append(b)

    for s in sel:
        o = s.Object
        if eh_barra(o):
            add(o)
        elif eh_estrutura(o):
            for b in barras_de(o):
                add(b)
        else:
            ests = [e for e in o.InList if eh_estrutura(e) and e.Esqueleto == o]
            nums = [int(n[4:]) - 1 for n in s.SubElementNames if n.startswith("Edge") and n[4:].isdigit()]
            for est in ests:
                for b in barras_de(est):
                    if not nums or b.Indice in nums:
                        add(b)
    return res


class _ItemSel:
    def __init__(self, obj, subs):
        self.Object = obj
        self.SubElementNames = list(subs)


def resolver_item(obj, subs=()):
    """(objeto, [elementos]) de um item de seleção com caminho completo ("Parte.Barra001.Face2")."""
    alvos = []
    for sub in (subs or ("",)):
        o, el = obj, sub
        if sub and "." in sub:
            try:
                dono = obj.getSubObject(sub, retType=1)
                if dono is not None:
                    o = dono
                    el = sub.rsplit(".", 1)[-1]
            except Exception:
                pass
        alvos.append((o, el))
    agrup = {}
    for o, el in alvos:
        agrup.setdefault(o, [])
        if el:
            agrup[o].append(el)
    return list(agrup.items())


def barras_do_item(obj, subs=()):
    """Barras indicadas por um item de seleção (para as caixas de seleção dos painéis)."""
    return barras_da_selecao([_ItemSel(o, els) for o, els in resolver_item(obj, subs)])


class CmdTrocarPerfil:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("barra.svg"),
                "MenuText": "Trocar perfil da barra",
                "ToolTip": "Troca o perfil (e o giro) das barras selecionadas — clique nas barras na tela, "
                           "na árvore ou nas linhas do esqueleto."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        bs = barras_da_selecao()
        if not bs:
            import PrumoSelecao
            PrumoSelecao.pedir("Trocar perfil", "Escolha as barras que vão mudar de perfil (na tela ou na "
                               "árvore). Para separar a estrutura em grupos de perfis, use Editar estrutura.",
                               [("Barras", "barras", 1, None)], lambda barras: self.trocar(barras))
            return
        self.trocar(bs)

    def trocar(self, bs):
        d = QtWidgets.QDialog(FreeCADGui.getMainWindow())
        d.setWindowTitle("Trocar perfil — %d barra(s)" % len(bs))
        lay = QtWidgets.QVBoxLayout(d)
        sel = SeletorPerfil(bs[0].Perfil or PERFIL_PADRAO)
        lay.addWidget(sel)
        giro = QtWidgets.QDoubleSpinBox()
        giro.setRange(-360, 360)
        giro.setSuffix(" °")
        giro.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
        f = QtWidgets.QFormLayout()
        f.addRow("Giro adicional", giro)
        lay.addLayout(f)
        aviso = QtWidgets.QLabel("A troca aparece na tela na hora. Trocar grava; Cancelar volta ao que era.")
        aviso.setWordWrap(True)
        lay.addWidget(aviso)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Trocar")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        self.dialogo, self.sel, self.giro = d, sel, giro
        doc = bs[0].Document
        ests = {b.Estrutura for b in bs}
        antes = {e.Name: (list(e.PerfisIndividuais), list(e.RotacoesIndividuais)) for e in ests}
        doc.openTransaction("Trocar perfil")

        def previa(*_a):
            try:
                trocar_perfil(bs, sel.nome(), giro.value())
                aviso.setText("A troca aparece na tela na hora. Trocar grava; Cancelar volta ao que era.")
            except Exception as ex:
                aviso.setText("<span style='color:#B5523F'>%s</span>" % ex)

        sel.mudou.connect(previa)
        giro.valueChanged.connect(previa)
        previa()
        if self._executar_dialogo(d):
            doc.commitTransaction()
            return
        try:
            doc.abortTransaction()
        except Exception:
            pass
        for e in ests:     # sem Desfazer ligado no documento
            pf, rt = antes[e.Name]
            if list(e.PerfisIndividuais) != pf or list(e.RotacoesIndividuais) != rt:
                e.PerfisIndividuais, e.RotacoesIndividuais = pf, rt
                for b in barras_de(e):
                    b.touch()
        doc.recompute()

    def _executar_dialogo(self, d):
        return bool(d.exec())


class DialogoCantos(QtWidgets.QDialog):
    """Tratamento dos cantos: cantos parecidos agrupados (mesmo tipo, perfis e ângulo), ou um a um
    para as barras selecionadas."""

    MANTER = "(manter)"

    def showEvent(self, ev):
        import PrumoPainel
        PrumoPainel.caber_na_tela(self)      # notebook: rolagem em vez de diálogo cortado
        super().showEvent(ev)

    def __init__(self, est, barras=None, parent=None, ao_vivo=False):
        super().__init__(parent)
        self.est = est
        self.ao_vivo = bool(ao_vivo)
        self._transacao = False
        self._cantos_antes = list(getattr(est, "Cantos", []) or [])
        self.etiquetas = None
        self.setWindowTitle("Cantos da estrutura")
        self.setMinimumSize(1060, 380)
        import PrumoPainel as P
        self.setStyleSheet(P.qss())
        lay = QtWidgets.QVBoxLayout(self)
        card_cantos, cl = P.bloco("Tratamento dos cantos", "chanfro")
        lay.addWidget(card_cantos, 1)
        todos = cantos(est)
        if barras:
            idx = {b.Indice for b in barras}
            self.linhas = [[c] for c in todos if c.i in idx or c.j in idx]
            cl.addWidget(QtWidgets.QLabel("Cantos das barras selecionadas, um a um."))
        else:
            self.linhas = list(agrupar_cantos(todos).values())
            cl.addWidget(QtWidgets.QLabel("Cantos parecidos estão juntos: a escolha vale para todos do grupo."))
        self.tabela = QtWidgets.QTableWidget(len(self.linhas), 3)
        self.tabela.setHorizontalHeaderLabels(["Cantos", "Hoje", "Tratamento"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.verticalHeader().setVisible(False)
        self.combos = []
        for r, grupo in enumerate(self.linhas):
            c = grupo[0]
            tipo = "Canto" if c.tipo == "esquadria" else "Ligação em T"
            if len(grupo) == 1:
                txt = "%s %s° — barras %d e %d (%s / %s)" % (tipo, fmt(c.angulo, 0), c.i + 1, c.j + 1, c.perfis[0],
                                                           c.perfis[1])
            else:
                txt = "%s %s° — %s / %s (%d cantos)" % (tipo, fmt(c.angulo, 0), c.perfis[0], c.perfis[1], len(grupo))
            hoje = sorted({x.descricao_tratamento() for x in grupo})
            self.tabela.setItem(r, 0, QtWidgets.QTableWidgetItem(txt))
            self.tabela.setItem(r, 1, QtWidgets.QTableWidgetItem(hoje[0] if len(hoje) == 1 else "variado"))
            cb = QtWidgets.QComboBox()
            cb.addItems([self.MANTER] + (OPCOES_ESQUADRIA if c.tipo == "esquadria" else OPCOES_T))
            self.tabela.setCellWidget(r, 2, cb)
            self.combos.append(cb)
        self.tabela.resizeColumnsToContents()
        cab = self.tabela.horizontalHeader()
        cab.setStretchLastSection(False)
        cab.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        cab.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        cab.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        self.tabela.setColumnWidth(2, 250)
        for r in range(self.tabela.rowCount()):
            it = self.tabela.item(r, 0)
            it.setToolTip(it.text())
        meio = QtWidgets.QHBoxLayout()
        meio.addWidget(self.tabela, 1)
        # guia ilustrado: desenho do tratamento da linha atual
        guia = QtWidgets.QVBoxLayout()
        self.desenho = None
        try:
            from PySide6 import QtSvgWidgets
            self.desenho = QtSvgWidgets.QSvgWidget()
        except ImportError:  # pragma: no cover
            try:
                from PySide2 import QtSvg
                self.desenho = QtSvg.QSvgWidget()
            except ImportError:
                self.desenho = None
        if self.desenho is not None:
            self.desenho.setFixedSize(260, 200)
            guia.addWidget(self.desenho)
        self.nota = QtWidgets.QLabel("")
        self.nota.setWordWrap(True)
        self.nota.setFixedWidth(260)
        self.nota.setStyleSheet("color: #003A70;")
        guia.addWidget(self.nota)
        guia.addStretch(1)
        meio.addLayout(guia)
        cl.addLayout(meio, 1)
        self.tabela.currentCellChanged.connect(lambda *_: self.atualizar_desenho())
        self.tabela.currentCellChanged.connect(lambda *_: self.marcar_cantos())
        for cb in self.combos:
            cb.currentTextChanged.connect(lambda *_: self.atualizar_desenho())
            cb.currentTextChanged.connect(lambda *_: self.previa())
        if self.linhas:
            self.tabela.setCurrentCell(0, 2)
        self.atualizar_desenho()
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        if self.ao_vivo:
            self.est.Document.openTransaction("Cantos")
            self._transacao = True
        self.marcar_cantos()

    # ---- prévia ao vivo e cantos marcados na tela
    def _no_do_canto(self, c, eds):
        """Ponto do canto: a ponta comum (canto) ou a ponta de i no meio de j (ligação em T)."""
        e, o = eds[c.i], eds[c.j]
        pontas_o = (o.valueAt(o.FirstParameter), o.valueAt(o.LastParameter))
        for p in (e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)):
            if c.tipo == "topo_T":
                if _ponto_interior(p, o):
                    return p
            elif any((p - q).Length < 1e-4 for q in pontas_o):
                return p
        return e.valueAt(e.FirstParameter)

    def marcar_cantos(self):
        """Marca na tela os cantos da linha escolhida na tabela (os outros em azul)."""
        if not FreeCAD.GuiUp:
            return
        if self.etiquetas is not None:
            self.etiquetas.remover()
            self.etiquetas = None
        try:
            eds = arestas(self.est.Esqueleto)
            pontos, textos, dest = [], [], []
            r = self.tabela.currentRow()
            for k, grupo in enumerate(self.linhas):
                for c in grupo:
                    pontos.append(self._no_do_canto(c, eds))
                    textos.append("canto %d" % (k + 1))
                    if k == r:
                        dest.append(len(pontos) - 1)
            if pontos:
                self.etiquetas = EtiquetasNaTela(self.est.Document, pontos, textos)
                self.etiquetas.destacar(dest)
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: marcas dos cantos: %s\n" % exc)

    def _escolhas(self):
        for grupo, cb in zip(self.linhas, self.combos):
            if cb.currentText() != self.MANTER:
                aplicar_opcao(self.est, grupo, cb.currentText())

    def previa(self):
        """Ao vivo: aplica as escolhas na estrutura na hora (Cancelar volta ao que era)."""
        if not self._transacao:
            return
        self.est.Cantos = list(self._cantos_antes)
        self._escolhas()
        for b in barras_de(self.est):
            b.touch()
        self.est.Document.recompute()

    def done(self, r):
        if self._transacao:
            doc = self.est.Document
            self._transacao = False
            if r == QtWidgets.QDialog.Accepted:
                doc.commitTransaction()
            else:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
                if list(self.est.Cantos) != self._cantos_antes:   # sem Desfazer ligado
                    self.est.Cantos = list(self._cantos_antes)
                    for b in barras_de(self.est):
                        b.touch()
                doc.recompute()
        if self.etiquetas is not None:
            self.etiquetas.remover()
            self.etiquetas = None
        super().done(r)

    def escolher(self, linha, opcao):
        self.combos[linha].setCurrentText(opcao)

    def opcao_mostrada(self):
        """(tipo, opção) que o desenho mostra: a escolha da linha atual ou, em "(manter)", a de hoje."""
        r = self.tabela.currentRow()
        if r < 0 or r >= len(self.linhas):
            return None
        c = self.linhas[r][0]
        op = self.combos[r].currentText()
        if op == self.MANTER:
            hoje = c.descricao_tratamento()
            opcoes = OPCOES_ESQUADRIA if c.tipo == "esquadria" else OPCOES_T
            if hoje in opcoes:
                op = hoje
            elif hoje.startswith("Topo — passa a barra"):
                n = int(hoje.rsplit(" ", 1)[-1]) - 1
                op = OPCOES_ESQUADRIA[1] if n == min(c.i, c.j) else OPCOES_ESQUADRIA[2]
            else:
                op = opcoes[0]
        return c.tipo, op

    def atualizar_desenho(self):
        escolha = self.opcao_mostrada()
        if escolha is None:
            return
        try:
            import PrumoIlustra
            svg, nota = PrumoIlustra.canto_svg(escolha[1], escolha[0])
        except Exception as ex:  # pragma: no cover
            self.nota.setText(str(ex))
            return
        if self.desenho is not None:
            self.desenho.load(QtCore.QByteArray(svg.encode("utf-8")))
        self.nota.setText("<b>%s</b><br>%s" % (escolha[1], nota))

    def aplicar(self):
        if self._transacao:      # ao vivo: a prévia já está aplicada; OK grava
            self.previa()
            return
        doc = self.est.Document
        doc.openTransaction("Cantos")
        try:
            for grupo, cb in zip(self.linhas, self.combos):
                if cb.currentText() != self.MANTER:
                    aplicar_opcao(self.est, grupo, cb.currentText())
            for b in barras_de(self.est):
                b.touch()
            doc.recompute()
        except Exception:
            doc.abortTransaction()
            raise
        doc.commitTransaction()

    def _ok(self):
        self.aplicar()
        self.accept()


class CmdCantos:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("cantos.svg"),
                "MenuText": "Cantos",
                "ToolTip": "Meia-esquadria ou de topo (escolhendo qual barra passa), corte reto ou recorte "
                           "pelo contorno nas ligações em T. Cantos parecidos são tratados de uma vez."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        est = next((estrutura_de(o) for o in sel if estrutura_de(o) is not None), None)
        if est is None:
            import PrumoSelecao
            PrumoSelecao.pedir("Cantos", "Escolha a estrutura inteira (todos os cantos) ou algumas barras (só "
                               "os cantos delas).", [("Estrutura ou barras", _filtro_estrutura_ou_barras, 1, None)],
                               lambda itens: abrir_cantos(itens))
            return
        barras = [o for o in sel if eh_barra(o) and o.Estrutura == est]
        abrir_cantos([est] if any(eh_estrutura(o) for o in sel) or not barras else barras)


def abrir_cantos(itens):
    """Diálogo Cantos para a estrutura (itens = [estrutura]) ou para as barras escolhidas."""
    est = next((estrutura_de(o) for o in itens if estrutura_de(o) is not None), None)
    if est is None:
        return None
    barras = [o for o in itens if eh_barra(o) and o.Estrutura == est]
    d = DialogoCantos(est, barras if barras and not any(eh_estrutura(o) for o in itens) else None,
                      FreeCADGui.getMainWindow(), ao_vivo=True)
    if not d.linhas:
        d.reject()
        QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Cantos",
                                          "Não há cantos de duas barras nem ligações em T aqui.")
        return d
    # não modal: dá para girar e aproximar a vista enquanto escolhe (a prévia aparece na hora)
    d.setWindowModality(QtCore.Qt.NonModal)
    d.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    _dialogos.append(d)
    d.finished.connect(lambda _r, d=d: _dialogos.remove(d) if d in _dialogos else None)
    d.show()
    return d


class CmdListaDeCorte:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("lista_corte.svg"),
                "MenuText": "Lista de corte",
                "ToolTip": "Planilha com perfil, comprimento, ângulos de corte, quantidade e massa das "
                           "barras da estrutura soldada (seleção ou documento inteiro)."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        objs = FreeCADGui.Selection.getSelection() or \
            [o for o in doc.Objects if eh_estrutura(o)]
        linhas = lista_de_corte(objs)
        if not linhas:
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Lista de corte",
                                              "Nenhuma barra de estrutura soldada encontrada.")
            return
        doc.openTransaction("Lista de corte")
        gravar_lista_de_corte(doc, linhas)
        doc.commitTransaction()


class CmdAtualizarEstrutura:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("estrutura.svg"),
                "MenuText": "Atualizar estrutura",
                "ToolTip": "Depois de mudar o esqueleto: cria barras nas linhas novas e tira as que sobraram."}

    def IsActive(self):
        return any(estrutura_de(o) is not None for o in FreeCADGui.Selection.getSelection())

    def Activated(self):
        ests = []
        for o in FreeCADGui.Selection.getSelection():
            est = estrutura_de(o)
            if est is not None and est not in ests:
                ests.append(est)
        if not ests:
            return
        doc = ests[0].Document
        doc.openTransaction("Atualizar estrutura")
        try:
            for est in ests:
                atualizar(est)
        except Exception as ex:
            doc.abortTransaction()
            FreeCAD.Console.PrintError("Prumo: não foi possível atualizar a estrutura: %s\n" % ex)
            return
        doc.commitTransaction()
