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
            vista.getSceneGraph().addChild(self.raiz)

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
            try:
                e = pn.obj.Shape.getElement(sub)
                meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
                meio = pn.obj.Placement.inverse().multVec(meio) if not pn.obj.Placement.isIdentity() else meio
            except Exception:
                return
            pts = pn.obj.Pontos
            melhor, dmin = None, None
            for k, (i, j) in enumerate(pn.segs()):
                a, b = FreeCAD.Vector(pts[i]), FreeCAD.Vector(pts[j])
                d = (meio - (a + b) * 0.5).Length
                if dmin is None or d < dmin:
                    melhor, dmin = k, d
            if melhor is not None:
                somar = bool(QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier)
                pn.selecionar_segmentos([melhor], somar=somar)

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
            self.plano = "XY"
            self.form = QtWidgets.QWidget()
            self.form.setWindowTitle("Esboço 3D")
            self.form.setWindowIcon(QtGui.QIcon(PrumoUtil.icone("esboco3d.svg")))
            import PrumoPainel as P
            raiz = QtWidgets.QVBoxLayout(self.form)
            dica = P.Mensagem(
                "Clique em <b>Desenhar</b> e vá clicando na vista: o ponto cai no plano que passa pelo "
                "último ponto (<b>Tab</b> troca XY → YZ → ZX) e encaixa em vértices e pontas de arestas. "
                "<b>Esc</b> termina o trecho; o próximo clique começa um ramal. O comprimento aparece junto ao "
                "cursor: para uma medida exata, <b>digite o número e tecle Enter</b> (o ponto vai na direção do "
                "cursor).")
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
            self.bt_clicar.setToolTip("Clique na vista para pôr pontos; Tab troca o plano, Esc termina o trecho")
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
            self.lb_plano = QtWidgets.QLabel(self.plano)
            self.lb_plano.setStyleSheet("font-weight:700; color:#003A70;")
            bt_plano = QtWidgets.QPushButton("Trocar (Tab)")
            bt_plano.clicked.connect(self.trocar_plano)
            hp.addWidget(self.lb_plano)
            hp.addWidget(bt_plano)
            hp.addStretch(1)
            fl.addRow("Plano de desenho", hp)
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

        def adicionar(self, p_local, coincide=None):
            """Põe um ponto. Com as restrições automáticas: a linha nova ao longo de um eixo ganha a
            restrição do eixo; o primeiro ponto de um ramal clicado sobre um ponto do esboço fica preso
            nele (coincidente)."""
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
                    if e:
                        k = len(segmentos(pts, quebras, False)) - 1
                        rs.append("eixo:%d:%s" % (k, e))
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
            self.plano = proximo_plano(self.plano)
            self.lb_plano.setText(self.plano)
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

        def ponto_em(self, pos):
            """(ponto global, tipo) sob o cursor: vértice/ponta de aresta encaixa; senão o plano."""
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
            p0, d = self._raio_da_vista(pos)
            p = no_plano(p0, d, base, self.plano)
            if p is None:
                return None, "plano %s de perfil para a vista: tecle Tab" % self.plano
            return na_grade(p, base, self.passo.value(), self.plano), "plano " + self.plano

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
                self._previa.linha(ini, p)
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
            self.adicionar(self.obj.Placement.inverse().multVec(p), coincide=getattr(self, "_idx_encaixe", None))
            self._mover(ev)

        def _mostrar_estado(self):
            pts = self.pontos()
            comp = PrumoUtil.fmt(float(self.obj.Comprimento), 1)
            linhas = ["%d ponto(s), %d trecho(s), comprimento %s mm" % (
                len(pts), len(trechos(pts, self.obj.Quebras)), comp) if pts else "Nenhum ponto ainda."]
            if self._vista is not None:
                linhas.append("<b>Plano %s</b> — <b>Tab</b> troca o plano; <b>Esc</b> termina o trecho "
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
