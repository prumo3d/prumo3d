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
ALINHAMENTOS = ["Centro", "Topo", "Base"]
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


def solido_bruto(e, it, rot_graus, alinhamento, normal, ext0=0.0, ext1=0.0):
    """Barra sem recortes sobre a aresta e, prolongada ext0 antes do início e ext1 após o fim."""
    import Part
    t, u, v = eixos_secao(e, rot_graus, normal)
    _larg, alt = PrumoPerfis.dimensoes(it)
    desloc = {"Centro": 0.0, "Topo": -alt / 2.0, "Base": alt / 2.0}.get(alinhamento, 0.0)
    if not _reta(e):
        ext0 = ext1 = 0.0
    p0 = e.valueAt(e.FirstParameter) - t * ext0
    f = PrumoPerfis.face(it, p0, u, v, desloc)
    if _reta(e):
        return f.extrude(t * (e.Length + ext0 + ext1))
    w = Part.Wire(e)
    ps = w.makePipeShell([f.OuterWire], True, True)
    return ps


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

    def __init__(self, tipo, outro=None, normal=None):
        self.tipo = tipo      # "livre", "esquadria", "topo_T", "multipla", "reta"
        self.outro = outro    # índice da outra barra
        self.normal = normal  # normal do plano de corte (esquadria)


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
            res.append(Ligacao("multipla"))
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


# ============================================================================ objetos
def _perfil_da_barra(est, i):
    lst = list(est.PerfisIndividuais)
    if i < len(lst) and lst[i]:
        return lst[i]
    return est.Perfil


def _rotacao_da_barra(est, i):
    lst = list(est.RotacoesIndividuais)
    base = est.Rotacao.Value if hasattr(est.Rotacao, "Value") else float(est.Rotacao)
    if i < len(lst):
        return base + lst[i]
    return base


def _extensoes(est, eds, i, normal, ligs=None):
    """Prolongamento (antes do início, após o fim) da barra i.

    Meia-esquadria: o bastante para o plano de corte. União de topo: a barra que passa (a de
    menor índice no canto) vai até a face externa da outra; a que encosta não é prolongada."""
    e = eds[i]
    it = PrumoPerfis.perfil(_perfil_da_barra(est, i))
    larg, alt = PrumoPerfis.dimensoes(it)
    if ligs is None:
        ligs = ligacoes(eds, i)
    ext = [0.0, 0.0]
    for k, lig in enumerate(ligs):
        if lig.tipo != "esquadria":
            continue
        j = lig.outro
        ito = PrumoPerfis.perfil(_perfil_da_barra(est, j))
        lo, ao = PrumoPerfis.dimensoes(ito) if ito else (larg, alt)
        if est.Uniao == "Meia-esquadria":
            ext[k] = 2.0 * (max(larg, alt) + max(lo, ao))
        elif j > i:
            _to, uo, vo = eixos_secao(eds[j], _rotacao_da_barra(est, j), normal)
            a = _dir(e, k == 0) * -1  # para fora da barra, além da ponta
            desloc_o = {"Centro": 0.0, "Topo": -ao / 2.0, "Base": ao / 2.0}.get(est.Alinhamento, 0.0)
            ext[k] = max(0.0, abs(a.dot(uo)) * lo / 2.0 + abs(a.dot(vo)) * ao / 2.0 + a.dot(vo) * desloc_o)
    return ext


def _face_de_encosto(est, eds, i, k, j, normal):
    """Plano (ponto, normal para dentro da barra i) da face da barra j onde encosta a ponta k de i."""
    e = eds[i]
    p = e.valueAt(e.FirstParameter if k == 0 else e.LastParameter)
    a = _dir(e, k == 0) * -1                      # para fora da barra i, além da ponta
    ito = PrumoPerfis.perfil(_perfil_da_barra(est, j))
    if ito is None:
        return None
    lo, ao = PrumoPerfis.dimensoes(ito)
    oe = eds[j]
    # direção da barra j no ponto de encontro
    try:
        u_par = oe.Curve.parameter(p)
    except Exception:
        u_par = oe.FirstParameter
    to = FreeCAD.Vector(oe.tangentAt(u_par)).normalize()
    _t, uo, vo = eixos_secao(oe, _rotacao_da_barra(est, j), normal)
    n_f = a - to * a.dot(to)
    if n_f.Length < 1e-9:
        return None                               # barras colineares: não há face de encosto
    n_f.normalize()
    desloc_o = {"Centro": 0.0, "Topo": -ao / 2.0, "Base": ao / 2.0}.get(est.Alinhamento, 0.0)
    # extremo da seção de j no sentido -n_f (face voltada para a barra i)
    d_face = n_f.dot(vo) * desloc_o - (abs(n_f.dot(uo)) * lo / 2.0 + abs(n_f.dot(vo)) * ao / 2.0)
    return p + n_f * d_face, n_f * -1


def calcular_barra(est, i, eds=None):
    """(sólido recortado, comprimento de corte, ângulo de corte no início, no fim, perfil)."""
    if eds is None:
        eds = arestas(est.Esqueleto)
    e = eds[i]
    nome = _perfil_da_barra(est, i)
    it = PrumoPerfis.perfil(nome)
    if it is None:
        raise ValueError("perfil desconhecido: %s" % nome)
    normal = _normal_esqueleto(eds)
    larg, alt = PrumoPerfis.dimensoes(it)
    ligs = ligacoes(eds, i)
    ext = _extensoes(est, eds, i, normal, ligs)
    sol = solido_bruto(e, it, _rotacao_da_barra(est, i), est.Alinhamento, normal, ext[0], ext[1])
    tam = 4 * (e.Length + larg + alt) + 100 + sum(ext)
    t = _dir(e, True)
    angs = [0.0, 0.0]
    for k, lig in enumerate(ligs):
        p = e.valueAt(e.FirstParameter if k == 0 else e.LastParameter)
        if lig.tipo == "esquadria" and est.Uniao == "Meia-esquadria":
            sol = sol.common(_meio_espaco(p, lig.normal, tam))
            angs[k] = angulo_corte(lig.normal, t)
        elif lig.tipo == "esquadria" or lig.tipo == "topo_T":
            # união de topo / ligação em T: a barra que encosta é cortada reta na face da que passa
            j = lig.outro
            if lig.tipo == "esquadria" and j > i:
                continue  # num canto "de topo", a de menor índice passa inteira; só a outra é cortada
            plano = _face_de_encosto(est, eds, i, k, j, normal)
            if plano is not None:
                ponto, n_corte = plano
                sol = sol.common(_meio_espaco(ponto, n_corte, tam))
                angs[k] = angulo_corte(n_corte, t)
    if sol.Solids and len(sol.Solids) == 1:
        sol = sol.Solids[0]
    proj = [(vx.Point - e.valueAt(e.FirstParameter)).dot(t) for vx in sol.Vertexes]
    if e.Curve.__class__.__name__ in ("Line", "LineSegment") and proj:
        comp = max(proj) - min(proj)
    else:
        comp = e.Length
    return sol, comp, angs[0], angs[1], nome


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

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        pass

    def onChanged(self, obj, prop):
        if prop in ("Esqueleto", "Perfil", "Rotacao", "Alinhamento", "Uniao", "Material",
                    "PerfisIndividuais", "RotacoesIndividuais"):
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
          uniao="Meia-esquadria", material=""):
    """Cria a estrutura e uma barra por linha do esqueleto. Retorna o grupo."""
    if PrumoPerfis.perfil(perfil) is None:
        raise ValueError("perfil desconhecido: %s" % perfil)
    eds = arestas(esqueleto)
    if not eds:
        raise ValueError("o esqueleto não tem linhas")
    doc.openTransaction("Estrutura soldada")
    est = doc.addObject("App::DocumentObjectGroupPython", "Estrutura")
    Estrutura(est)
    est.Esqueleto = esqueleto
    est.Perfil = perfil
    est.Rotacao = rotacao
    est.Alinhamento = alinhamento
    est.Uniao = uniao
    est.Material = material
    if FreeCAD.GuiUp:
        VPEstrutura(est.ViewObject)
    barras = []
    for i in range(len(eds)):
        b = doc.addObject("Part::FeaturePython", "Barra")
        Barra(b)
        b.Estrutura = est
        b.Esqueleto = esqueleto
        b.Indice = i
        if FreeCAD.GuiUp:
            VPBarra(b.ViewObject)
            try:
                b.ViewObject.ShapeAppearance = [_aparencia()]
            except Exception:
                pass
        est.addObject(b)
        barras.append(b)
    doc.recompute()
    if FreeCAD.GuiUp:
        try:
            esqueleto.ViewObject.Visibility = False
        except Exception:
            pass
    doc.commitTransaction()
    return est


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
        b = doc.addObject("Part::FeaturePython", "Barra")
        Barra(b)
        b.Estrutura = est
        b.Esqueleto = est.Esqueleto
        b.Indice = i
        if FreeCAD.GuiUp:
            VPBarra(b.ViewObject)
        est.addObject(b)
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


class DialogoEstrutura(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estrutura soldada")
        self.setMinimumWidth(460)
        lay = QtWidgets.QVBoxLayout(self)
        self.sel = SeletorPerfil(FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoPerfil", PERFIL_PADRAO))
        lay.addWidget(self.sel)
        form = QtWidgets.QFormLayout()
        self.rot = QtWidgets.QDoubleSpinBox()
        self.rot.setRange(-360, 360)
        self.rot.setSuffix(" °")
        self.rot.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
        self.alin = QtWidgets.QComboBox()
        self.alin.addItems(ALINHAMENTOS)
        self.uniao = QtWidgets.QComboBox()
        self.uniao.addItems(UNIOES)
        self.material = QtWidgets.QLineEdit(FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimoMaterialPerfil", ""))
        self.material.setPlaceholderText("ex.: ASTM A572 Gr. 50")
        form.addRow("Giro do perfil", self.rot)
        form.addRow("Alinhamento", self.alin)
        form.addRow("Cantos", self.uniao)
        form.addRow("Material", self.material)
        lay.addLayout(form)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Criar estrutura")
        bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


def _esqueleto_selecionado():
    for o in FreeCADGui.Selection.getSelection():
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
                           "selecionado, com meia-esquadria nos cantos e recorte nas ligações em T."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        esq = _esqueleto_selecionado()
        if esq is None:
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(), "Estrutura soldada",
                "Selecione o esboço (ou arame) com as linhas de centro da estrutura.")
            return
        d = DialogoEstrutura(FreeCADGui.getMainWindow())
        if not d.exec():
            return
        g = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH)
        g.SetString("UltimoPerfil", d.sel.nome())
        g.SetString("UltimoMaterialPerfil", d.material.text().strip())
        criar(FreeCAD.ActiveDocument, esq, d.sel.nome(), d.rot.value(), d.alin.currentText(),
              d.uniao.currentText(), d.material.text().strip())


class CmdTrocarPerfil:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("barra.svg"),
                "MenuText": "Trocar perfil da barra",
                "ToolTip": "Troca o perfil (e o giro) das barras selecionadas da estrutura soldada."}

    def IsActive(self):
        return any("Indice" in o.PropertiesList and "Estrutura" in o.PropertiesList
                   for o in FreeCADGui.Selection.getSelection())

    def Activated(self):
        bs = [o for o in FreeCADGui.Selection.getSelection() if "Indice" in o.PropertiesList]
        d = QtWidgets.QDialog(FreeCADGui.getMainWindow())
        d.setWindowTitle("Trocar perfil da barra")
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
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        lay.addWidget(bb)
        if d.exec():
            trocar_perfil(bs, sel.nome(), giro.value())


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
