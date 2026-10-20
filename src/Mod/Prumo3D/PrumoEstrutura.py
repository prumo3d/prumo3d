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


def eixos_secao(e, rot_graus, normal):
    """(t, u, v): direção da barra, largura e altura da seção."""
    t = _dir(e, True)
    v = referencia(t, normal)
    if abs(rot_graus) > 1e-9:
        r = FreeCAD.Rotation(t, rot_graus)
        v = r.multVec(v)
    u = v.cross(t).normalize()
    return t, u, v


def _reta(e):
    return e.Curve.__class__.__name__ in ("Line", "LineSegment")


def solido_bruto(e, it, rot_graus, desloc, normal, ext0=0.0, ext1=0.0, espelhar=False):
    """Barra sem recortes sobre a aresta e, prolongada ext0 antes do início e ext1 após o fim.

    desloc = (du, dv): centro da caixa da seção em relação à linha (ver deslocamento()); aceita
    também o nome de uma fixação ou de um alinhamento antigo."""
    import Part
    t, u, v = eixos_secao(e, rot_graus, normal)
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
            if j == i:
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
        passa = [j for j, o in enumerate(eds) if j != i and _ponto_interior(p, o)]
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
    return {"nome": "Padrão", "perfil": est.Perfil,
            "giro": est.Rotacao.Value if hasattr(est.Rotacao, "Value") else float(est.Rotacao),
            "fixacao": _fixacao_da_estrutura(est), "espelhar": bool(getattr(est, "Espelhar", False))}


def grupo_da_barra(est, i):
    """Índice do grupo da aresta i (0 = padrão)."""
    lst = list(getattr(est, "GrupoDaAresta", []) or [])
    k = lst[i] if i < len(lst) else 0
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
        self.t, self.u, self.v = eixos_secao(eds[j], self.giro, normal)
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
    e = eds[i]
    normal = _normal_esqueleto(eds)
    sec = Secao(est, eds, i, normal)
    nome = sec.it["nome"]
    ligs = ligacoes(eds, i)
    ext = _extensoes(est, eds, i, normal, ligs)
    sol = solido_bruto(e, sec.it, sec.giro, (sec.du, sec.dv), normal, ext[0], ext[1], sec.espelhar)
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
                bruto = solido_bruto(eds[j], sj.it, sj.giro, (sj.du, sj.dv), normal, 0.0, 0.0, sj.espelhar)
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

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc, esqueleto, perfil=PERFIL_PADRAO, rotacao=0.0, alinhamento="Centro",
          uniao="Meia-esquadria", material="", grupos_extras=None, espelhar=False):
    """Cria a estrutura e uma barra por linha do esqueleto. Retorna o grupo.

    alinhamento: ponto de fixação (FIXACOES) ou alinhamento antigo (Centro/Topo/Base).
    grupos_extras: [{"nome", "perfil", "giro", "fixacao", "espelhar", "arestas": [índices]}]."""
    if PrumoPerfis.perfil(perfil) is None:
        raise ValueError("perfil desconhecido: %s" % perfil)
    eds = arestas(esqueleto)
    if not eds:
        raise ValueError("o esqueleto não tem linhas")
    fixacao = _ALINHAMENTO_PARA_FIXACAO.get(alinhamento, alinhamento)
    if fixacao not in FIXACOES:
        raise ValueError("ponto de fixação desconhecido: %s" % alinhamento)
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
    definir_grupos(est, grupos_extras or [], len(eds))
    if FreeCAD.GuiUp:
        VPEstrutura(est.ViewObject)
    for i in range(len(eds)):
        _nova_barra(doc, est, i)
    doc.recompute()
    if FreeCAD.GuiUp:
        try:
            esqueleto.ViewObject.Visibility = False
        except Exception:
            pass
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


def definir_grupos(est, grupos_extras, n_arestas=None):
    """Grava os grupos extras e a que grupo pertence cada aresta (as não citadas ficam no padrão)."""
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


def atualizar(est):
    """Cria barras para linhas novas do esqueleto e apaga as que sobraram."""
    doc = est.Document
    eds = arestas(est.Esqueleto)
    atuais = barras_de(est)
    for b in atuais[len(eds):]:
        doc.removeObject(b.Name)
    for i in range(len(atuais), len(eds)):
        _nova_barra(doc, est, i)
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
    eds = arestas(est.Esqueleto)
    res = []
    vistos = set()
    for i in range(len(eds)):
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
    """Família + perfil, com aviso quando o dado é 'a conferir'."""

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


def editar(est, padrao, grupos_extras, uniao=None, material=None):
    """Aplica o grupo padrão, os grupos extras (com as arestas) e as opções gerais à estrutura.

    As trocas individuais de perfil/giro são zeradas: o diálogo já as mostra como grupos."""
    if PrumoPerfis.perfil(padrao["perfil"]) is None:
        raise ValueError("perfil desconhecido: %s" % padrao["perfil"])
    if padrao.get("fixacao", "Centro") not in FIXACOES:
        raise ValueError("ponto de fixação desconhecido: %s" % padrao.get("fixacao"))
    n = len(arestas(est.Esqueleto))
    definir_grupos(est, grupos_extras, n)
    est.Perfil = padrao["perfil"]
    est.Rotacao = float(padrao.get("giro", 0.0))
    est.Fixacao = padrao.get("fixacao", "Centro")
    est.Espelhar = bool(padrao.get("espelhar", False))
    est.PerfisIndividuais = []
    est.RotacoesIndividuais = []
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
        base = padrao if k == 0 else extras[k - 1]
        par = parametros(est, i)
        mudou = par["perfil"] != base["perfil"] or abs(float(par["giro"]) - float(base["giro"])) > 1e-9
        if mudou:
            chave = (par["perfil"], round(float(par["giro"]), 6), base["fixacao"], bool(base["espelhar"]))
            if chave not in trocas:
                g = copy.deepcopy(base)
                g.update({"nome": "Troca: %s" % par["perfil"], "perfil": par["perfil"],
                          "giro": float(par["giro"]), "arestas": []})
                trocas[chave] = g
                extras.append(g)
            trocas[chave]["arestas"].append(i)
        elif k > 0:
            extras[k - 1]["arestas"].append(i)
    return padrao, extras


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


class DialogoEstrutura(QtWidgets.QDialog):
    """Criação e edição da estrutura: grupos de barras (perfil, giro, fixação, espelhar) e as
    linhas do esqueleto de cada grupo. Fica aberto enquanto se seleciona na tela."""

    def __init__(self, esqueleto, est=None, parent=None):
        super().__init__(parent)
        self.esqueleto = esqueleto
        self.est = est
        self.resultado = None
        self.setWindowTitle("Editar estrutura soldada" if est else "Estrutura soldada")
        self.setMinimumSize(820, 600)
        self.resize(860, 800)
        self.eds = arestas(esqueleto)
        if est is not None:
            padrao, extras = grupos_para_edicao(est)
        else:
            g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
            padrao = {"nome": "Padrão", "perfil": g.GetString("UltimoPerfil", PERFIL_PADRAO), "giro": 0.0,
                      "fixacao": "Centro", "espelhar": False}
            if PrumoPerfis.perfil(padrao["perfil"]) is None:
                padrao["perfil"] = PERFIL_PADRAO
            extras = []
        self.grupos_ed = [dict(padrao, nome="Padrão")] + [dict(x) for x in extras]
        self.da_aresta = [0] * len(self.eds)
        for k, g in enumerate(extras, 1):
            for i in g.get("arestas", []):
                if 0 <= i < len(self.eds):
                    self.da_aresta[i] = k
        self._montar()
        self._carregando = False
        self.lista.setCurrentRow(0)

    # ------------------------------------------------------------------ montagem
    def _montar(self):
        lay = QtWidgets.QVBoxLayout(self)
        topo = QtWidgets.QHBoxLayout()
        # grupos
        col = QtWidgets.QVBoxLayout()
        col.addWidget(QtWidgets.QLabel("<b>Grupos de barras</b>"))
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
        topo.addLayout(col)
        # editor do grupo
        ed = QtWidgets.QGroupBox("Grupo")
        fl = QtWidgets.QFormLayout(ed)
        self.nome = QtWidgets.QLineEdit()
        self.sel = SeletorPerfil(self.grupos_ed[0]["perfil"])
        self.giro = QtWidgets.QDoubleSpinBox()
        self.giro.setRange(-360, 360)
        self.giro.setSuffix(" °")
        self.giro.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
        self.fixacao = QtWidgets.QComboBox()
        self.fixacao.addItems(FIXACOES)
        self.fixacao.setToolTip("Ponto da seção que fica sobre a linha do esboço (localizar perfil)")
        self.espelhar = QtWidgets.QCheckBox("Espelhar a seção (abas do U / da cantoneira para o outro lado)")
        fl.addRow("Nome", self.nome)
        fl.addRow(self.sel)
        fl.addRow("Giro", self.giro)
        fl.addRow("Ponto de fixação", self.fixacao)
        fl.addRow("", self.espelhar)
        self.sel.aviso.setMinimumHeight(self.sel.aviso.fontMetrics().lineSpacing() * 4 + 6)
        self.sel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        ed.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        topo.addWidget(ed, 1)
        lay.addLayout(topo, 1)
        # linhas do esqueleto
        lay.addWidget(QtWidgets.QLabel("<b>Linhas do esqueleto</b> — escolha o grupo de cada uma, ou selecione "
                                       "linhas na tela e use o botão abaixo."))
        self.tabela = QtWidgets.QTableWidget(len(self.eds), 3)
        self.tabela.setHorizontalHeaderLabels(["Linha", "Medida", "Grupo"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.combos = []
        for i, e in enumerate(self.eds):
            self.tabela.setItem(i, 0, QtWidgets.QTableWidgetItem("Linha %d" % (i + 1)))
            self.tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(_descricao_aresta(e)))
            cb = QtWidgets.QComboBox()
            cb.currentIndexChanged.connect(lambda k, i=i: self._linha_mudou(i, k))
            self.tabela.setCellWidget(i, 2, cb)
            self.combos.append(cb)
        self.tabela.resizeColumnsToContents()
        self.tabela.setMinimumHeight(min(200, 34 + 30 * max(1, len(self.eds))))
        lay.addWidget(self.tabela, 2)
        bt = QtWidgets.QHBoxLayout()
        self.bt_pegar = QtWidgets.QPushButton("Pôr as linhas selecionadas na tela no grupo atual")
        self.bt_mostrar = QtWidgets.QPushButton("Mostrar na tela as linhas do grupo")
        bt.addWidget(self.bt_pegar)
        bt.addWidget(self.bt_mostrar)
        bt.addStretch(1)
        lay.addLayout(bt)
        # opções gerais
        fg = QtWidgets.QFormLayout()
        self.uniao = QtWidgets.QComboBox()
        self.uniao.addItems(UNIOES)
        self.uniao.setToolTip("Cantos de duas barras. Cada canto pode ser trocado depois em \"Cantos\".")
        self.material = QtWidgets.QLineEdit(
            self.est.Material if self.est is not None else
            FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialPerfil", ""))
        self.material.setPlaceholderText("ex.: ASTM A572 Gr. 50")
        if self.est is not None:
            self.uniao.setCurrentText(self.est.Uniao)
        fg.addRow("Cantos (padrão)", self.uniao)
        fg.addRow("Material", self.material)
        lay.addLayout(fg)
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
        self.nome.textEdited.connect(self._editado)
        self.sel.perfil.currentIndexChanged.connect(self._editado)
        self.giro.valueChanged.connect(self._editado)
        self.fixacao.currentIndexChanged.connect(self._editado)
        self.espelhar.toggled.connect(self._editado)

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
        self.lista.setCurrentRow(min(atual, len(self.grupos_ed) - 1))
        self.lista.blockSignals(False)
        nomes = [g["nome"] for g in self.grupos_ed]
        for i, cb in enumerate(self.combos):
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(nomes)
            cb.setCurrentIndex(self.da_aresta[i])
            cb.blockSignals(False)
        self.bt_remover.setEnabled(self.lista.currentRow() > 0)

    # ------------------------------------------------------------------ edição
    def _grupo_escolhido(self, k):
        if k < 0:
            return
        g = self.grupos_ed[k]
        self._carregando = True
        self.nome.setText(g["nome"])
        self.nome.setEnabled(k > 0)
        it = PrumoPerfis.perfil(g["perfil"])
        if it:
            self.sel.familia.setCurrentIndex(max(0, self.sel.familia.findData(it["familia"])))
            self.sel.perfil.setCurrentIndex(max(0, self.sel.perfil.findData(it["nome"])))
        self.giro.setValue(float(g.get("giro", 0.0)))
        self.fixacao.setCurrentText(g.get("fixacao", "Centro"))
        self.espelhar.setChecked(bool(g.get("espelhar", False)))
        self._carregando = False
        self.bt_remover.setEnabled(k > 0)

    def _editado(self, *_a):
        if getattr(self, "_carregando", True):
            return
        k = self.lista.currentRow()
        if k < 0:
            return
        g = self.grupos_ed[k]
        if k > 0:
            g["nome"] = self.nome.text().strip() or "Grupo %d" % k
        g["perfil"] = self.sel.nome() or g["perfil"]
        g["giro"] = self.giro.value()
        g["fixacao"] = self.fixacao.currentText()
        g["espelhar"] = self.espelhar.isChecked()
        self.lista.item(k).setText(self._rotulo(k))
        for cb in self.combos:
            cb.setItemText(k, g["nome"])

    def _linha_mudou(self, i, k):
        if k < 0:
            return
        self.da_aresta[i] = k
        for j in range(len(self.grupos_ed)):
            self.lista.item(j).setText(self._rotulo(j))

    def novo_grupo(self):
        base = self.grupos_ed[max(0, self.lista.currentRow())]
        k = len(self.grupos_ed)
        self.grupos_ed.append({"nome": "Grupo %d" % k, "perfil": base["perfil"], "giro": 0.0,
                               "fixacao": "Centro", "espelhar": False})
        self._recarregar_lista()
        self.lista.setCurrentRow(k)
        self._grupo_escolhido(k)
        return k

    def remover_grupo(self):
        k = self.lista.currentRow()
        if k <= 0:
            return
        del self.grupos_ed[k]
        self.da_aresta = [0 if x == k else (x - 1 if x > k else x) for x in self.da_aresta]
        self.lista.setCurrentRow(k - 1)
        self._recarregar_lista()
        self._grupo_escolhido(self.lista.currentRow())

    def atribuir(self, indices, k=None):
        """Põe as linhas indicadas no grupo k (padrão: o grupo atual)."""
        if k is None:
            k = self.lista.currentRow()
        for i in indices:
            if 0 <= i < len(self.eds):
                self.da_aresta[i] = k
        self._recarregar_lista()

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

    def aplicar(self):
        """Cria ou atualiza a estrutura. Retorna o objeto (ou levanta ValueError)."""
        padrao, extras = self.dados()
        doc = self.esqueleto.Document
        uniao = self.uniao.currentText()
        material = self.material.text().strip()
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        g.SetString("UltimoPerfil", padrao["perfil"])
        g.SetString("UltimoMaterialPerfil", material)
        if self.est is None:
            self.resultado = criar(doc, self.esqueleto, padrao["perfil"], padrao["giro"], padrao["fixacao"],
                                   uniao, material, extras, padrao["espelhar"])
        else:
            doc.openTransaction("Editar estrutura")
            try:
                editar(self.est, padrao, extras, uniao, material)
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


def abrir_dialogo(esqueleto, est=None):
    d = DialogoEstrutura(esqueleto, est, FreeCADGui.getMainWindow())
    d.setWindowModality(QtCore.Qt.NonModal)
    d.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    _dialogos.append(d)
    d.finished.connect(lambda _r, d=d: _dialogos.remove(d) if d in _dialogos else None)
    d.show()
    return d


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
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(), "Estrutura soldada",
                "Selecione o esboço (ou arame) com as linhas de centro da estrutura.")
            return
        abrir_dialogo(esq)


class CmdEditarEstrutura:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("estrutura_editar.svg"),
                "MenuText": "Editar estrutura",
                "ToolTip": "Grupos de barras: perfil, giro, ponto de fixação e espelhamento de cada grupo, "
                           "e a que grupo pertence cada linha do esqueleto."}

    def IsActive(self):
        return any(estrutura_de(o) is not None for o in FreeCADGui.Selection.getSelection())

    def Activated(self):
        for o in FreeCADGui.Selection.getSelection():
            est = estrutura_de(o)
            if est is not None:
                abrir_dialogo(est.Esqueleto, est)
                return


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
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(), "Trocar perfil",
                "Selecione as barras que vão mudar de perfil (na tela ou na árvore). Também vale "
                "selecionar linhas do esqueleto ou a estrutura inteira.\n\nPara separar a estrutura em "
                "grupos de perfis, use \"Editar estrutura\".")
            return
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
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Trocar")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if not d.exec():
            return
        doc = bs[0].Document
        doc.openTransaction("Trocar perfil")
        try:
            trocar_perfil(bs, sel.nome(), giro.value())
        except Exception as ex:
            doc.abortTransaction()
            QtWidgets.QMessageBox.warning(FreeCADGui.getMainWindow(), "Trocar perfil", str(ex))
            return
        doc.commitTransaction()


class DialogoCantos(QtWidgets.QDialog):
    """Tratamento dos cantos: cantos parecidos agrupados (mesmo tipo, perfis e ângulo), ou um a um
    para as barras selecionadas."""

    MANTER = "(manter)"

    def __init__(self, est, barras=None, parent=None):
        super().__init__(parent)
        self.est = est
        self.setWindowTitle("Cantos da estrutura")
        self.setMinimumSize(720, 360)
        lay = QtWidgets.QVBoxLayout(self)
        todos = cantos(est)
        if barras:
            idx = {b.Indice for b in barras}
            self.linhas = [[c] for c in todos if c.i in idx or c.j in idx]
            lay.addWidget(QtWidgets.QLabel("Cantos das barras selecionadas, um a um."))
        else:
            self.linhas = list(agrupar_cantos(todos).values())
            lay.addWidget(QtWidgets.QLabel("Cantos parecidos estão juntos: a escolha vale para todos do grupo."))
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
        lay.addWidget(self.tabela, 1)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Aplicar")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def escolher(self, linha, opcao):
        self.combos[linha].setCurrentText(opcao)

    def aplicar(self):
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
        return any(estrutura_de(o) is not None for o in FreeCADGui.Selection.getSelection())

    def Activated(self):
        sel = FreeCADGui.Selection.getSelection()
        est = next((estrutura_de(o) for o in sel if estrutura_de(o) is not None), None)
        barras = [o for o in sel if eh_barra(o) and o.Estrutura == est]
        d = DialogoCantos(est, barras if barras and not any(eh_estrutura(o) for o in sel) else None,
                          FreeCADGui.getMainWindow())
        if not d.linhas:
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Cantos",
                                              "Não há cantos de duas barras nem ligações em T aqui.")
            return
        d.exec()


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
