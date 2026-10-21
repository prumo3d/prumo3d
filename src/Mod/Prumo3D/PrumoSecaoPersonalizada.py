# SPDX-License-Identifier: LGPL-2.1-or-later
"""Seção personalizada: um perfil desenhado num esboço (ou numa face plana) que vira perfil da
estrutura soldada e entra no cálculo por barras.

O contorno (externo e furos, arcos discretizados) fica guardado no objeto "Seção personalizada" do
documento e é registrado no catálogo de perfis (família "Seções personalizadas") quando o documento
abre. Propriedades: área e inércias pelo polígono; constante de torção J pela função de tensão de
Prandtl resolvida numa malha (furos tratados como regiões de função constante), válida para seções
abertas, fechadas e compostas.
"""
import json
import math

import FreeCAD

FAMILIA = "PERS"
PREFIXO = "Personalizado · "
DENSIDADE = 7850.0   # kg/m³ (aço)


# ------------------------------------------------------------------ geometria
def _base_plana(forma):
    """(origem, eixo u, eixo v, normal) do plano da forma (face plana ou esboço)."""
    try:
        plano = forma.findPlane()
    except Exception:
        plano = None
    if plano is None:
        raise ValueError("a seção precisa ser plana")
    n = FreeCAD.Vector(plano.Axis).normalize()
    ref = FreeCAD.Vector(1, 0, 0) if abs(n.x) < 0.9 else FreeCAD.Vector(0, 1, 0)
    u = (ref - n * ref.dot(n)).normalize()
    v = n.cross(u)
    return FreeCAD.Vector(plano.Position), u, v, n


def _area2(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def contornos_de(forma, desvio=0.05):
    """(externo, [furos]) em 2D (mm), centrados no centro da caixa envolvente. Aceita um esboço
    (fios fechados) ou uma face plana."""
    import Part
    if forma.Faces:
        faces = forma.Faces
        if len(faces) != 1:
            raise ValueError("escolha uma face só (ou um esboço com um contorno externo)")
        fios = faces[0].Wires
    else:
        fios = [w for w in forma.Wires if w.isClosed()]
        if not fios:
            raise ValueError("o esboço não tem contorno fechado")
    o, u, v, _n = _base_plana(forma if forma.Faces else Part.Compound(fios))
    polis = []
    for w in fios:
        pts3 = w.discretize(Deflection=desvio)
        if (pts3[0] - pts3[-1]).Length < 1e-6:
            pts3 = pts3[:-1]
        pts = [((p - o).dot(u), (p - o).dot(v)) for p in pts3]
        if len(pts) < 3:
            continue
        polis.append(pts)
    if not polis:
        raise ValueError("contorno vazio")
    polis.sort(key=lambda p: -abs(_area2(p)))
    ext, furos = polis[0], polis[1:]
    # furos precisam estar dentro do externo
    for f in furos:
        if not _dentro(f[0], ext):
            raise ValueError("há mais de um contorno externo: a seção precisa ser uma peça só (una as chapas)")
    us = [x for x, _y in ext]
    vs = [y for _x, y in ext]
    cu, cv = (min(us) + max(us)) / 2.0, (min(vs) + max(vs)) / 2.0

    def mover(pts):
        q = [(round(x - cu, 6), round(y - cv, 6)) for x, y in pts]
        return q if _area2(q) > 0 else q[::-1]
    ext = mover(ext)
    furos = [mover(f)[::-1] for f in furos]     # furos no sentido horário
    return ext, furos


def _dentro(p, poli):
    x, y = p
    dentro = False
    n = len(poli)
    for i in range(n):
        x1, y1 = poli[i]
        x2, y2 = poli[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                dentro = not dentro
    return dentro


def item_de(nome, ext, furos):
    """Item do catálogo de perfis (tipo POL)."""
    area = abs(_area2(ext)) - sum(abs(_area2(f)) for f in furos)
    if area <= 0:
        raise ValueError("área da seção nula")
    return {"nome": PREFIXO + nome, "tipo": "POL", "contorno": [list(p) for p in ext],
            "furos": [[list(p) for p in f] for f in furos], "massa": area * 1e-6 * DENSIDADE,
            "area_cm2": area / 100.0, "status": "usuario", "derivado": [], "familia": FAMILIA}


# ------------------------------------------------------------------ catálogo
def registrar(it):
    """Põe (ou troca) o item na família de seções personalizadas do catálogo."""
    import PrumoPerfis
    import PrumoSecao
    d = PrumoPerfis.dados()
    fam = PrumoPerfis.familia(FAMILIA)
    if fam is None:
        fam = {"id": FAMILIA, "nome": "Seções personalizadas (desenhadas no projeto)",
               "norma": "desenhada pelo usuário",
               "fonte": {"chave": "USUARIO", "nome": "Seção desenhada no projeto", "url": ""}, "itens": []}
        d["familias"].append(fam)
    fam["itens"] = [x for x in fam["itens"] if x["nome"] != it["nome"]] + [it]
    PrumoPerfis._cache["idx"][it["nome"]] = it
    PrumoSecao._cache.pop(it["nome"], None)
    try:
        import PrumoEstrutura
        for k in [k for k in PrumoEstrutura._centroides if k[0] == it["nome"]]:
            PrumoEstrutura._centroides.pop(k, None)
    except Exception:
        pass
    return it


def desregistrar(nome):
    """Tira o perfil (nome completo) do catálogo; some com a família se ficar vazia."""
    import PrumoPerfis
    d = PrumoPerfis.dados()
    fam = PrumoPerfis.familia(FAMILIA)
    if fam is not None:
        fam["itens"] = [x for x in fam["itens"] if x["nome"] != nome]
        if not fam["itens"]:
            d["familias"].remove(fam)
    PrumoPerfis._cache["idx"].pop(nome, None)


# ------------------------------------------------------------------ torção (Prandtl)
def constante_torcao(ext, furos, h=None, max_celulas=160000):
    """J (mm⁴) pela função de tensão de Prandtl: ∇²φ = -2, φ = 0 no contorno externo e constante
    (incógnita) em cada furo; J = 2∫φ dA. Elementos bilineares numa grade regular."""
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import spsolve
    us = [x for x, _y in ext]
    vs = [y for _x, y in ext]
    x0, x1, y0, y1 = min(us), max(us), min(vs), max(vs)
    area = abs(_area2(ext)) - sum(abs(_area2(f)) for f in furos)
    perim = sum(math.hypot(p[(i + 1) % len(p)][0] - p[i][0], p[(i + 1) % len(p)][1] - p[i][1])
                for p in [ext] + furos for i in range(len(p)))
    t_med = 2.0 * area / perim if perim else 1.0          # espessura média das paredes
    if h is None:
        h = t_med / 6.0
    h = max(h, math.sqrt((x1 - x0) * (y1 - y0) / max_celulas))
    nx = max(2, int(math.ceil((x1 - x0) / h)))
    ny = max(2, int(math.ceil((y1 - y0) / h)))
    hx, hy = (x1 - x0) / nx, (y1 - y0) / ny
    xc = x0 + hx * (np.arange(nx) + 0.5)
    yc = y0 + hy * (np.arange(ny) + 0.5)
    XC, YC = np.meshgrid(xc, yc, indexing="ij")

    def dentro_vet(poli):
        x = XC.ravel()
        y = YC.ravel()
        res = np.zeros(x.shape, dtype=bool)
        n = len(poli)
        for i in range(n):
            xa, ya = poli[i]
            xb, yb = poli[(i + 1) % n]
            cruza = (ya > y) != (yb > y)
            with np.errstate(divide="ignore", invalid="ignore"):
                xcorte = xa + (y - ya) * (xb - xa) / (yb - ya)
            res ^= cruza & (x < xcorte)
        return res.reshape(XC.shape)
    regiao = dentro_vet(ext)
    furo_id = np.full(XC.shape, -1, dtype=int)
    for k, f in enumerate(furos):
        furo_id[dentro_vet(f) & regiao] = k
    material = regiao & (furo_id < 0)
    # nós (nx+1) × (ny+1); incógnita por nó, com nós dos furos amarrados numa incógnita por furo
    nn = (nx + 1) * (ny + 1)

    def nid(i, j):
        return i * (ny + 1) + j
    no_regiao = np.zeros(nn, dtype=bool)
    no_material = np.zeros(nn, dtype=bool)
    no_furo = np.full(nn, -1, dtype=int)
    no_fora = np.zeros(nn, dtype=bool)
    for i in range(nx):
        for j in range(ny):
            ns = (nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1))
            if regiao[i, j]:
                for q in ns:
                    no_regiao[q] = True
                if material[i, j]:
                    for q in ns:
                        no_material[q] = True
                else:
                    for q in ns:
                        no_furo[q] = furo_id[i, j]
            else:
                for q in ns:
                    no_fora[q] = True
    # contorno externo: nó de célula da região que também toca célula de fora (ou a borda da grade)
    borda = np.zeros(nn, dtype=bool)
    for i in (0, nx):
        for j in range(ny + 1):
            borda[nid(i, j)] = True
    for j in (0, ny):
        for i in range(nx + 1):
            borda[nid(i, j)] = True
    zero = no_regiao & (no_fora | borda)
    # numeração das incógnitas
    eq = np.full(nn, -1, dtype=int)
    neq = 0
    eq_furo = []
    for k in range(len(furos)):
        eq_furo.append(neq)
        neq += 1
    for q in range(nn):
        if not no_regiao[q] or zero[q]:
            continue
        if no_furo[q] >= 0 and not no_material[q]:
            eq[q] = eq_furo[no_furo[q]]
        elif no_furo[q] >= 0:
            # nó na borda do furo (toca material e furo): pertence ao furo (φ constante no contorno)
            eq[q] = eq_furo[no_furo[q]]
        else:
            eq[q] = neq
            neq += 1
    # matriz do elemento bilinear (laplaciano) e vetor de carga (∫2N)
    a, b = hx, hy
    ke = np.array([[2 * (b / a + a / b), -2 * b / a + a / b, -(b / a + a / b), b / a - 2 * a / b],
                   [-2 * b / a + a / b, 2 * (b / a + a / b), b / a - 2 * a / b, -(b / a + a / b)],
                   [-(b / a + a / b), b / a - 2 * a / b, 2 * (b / a + a / b), -2 * b / a + a / b],
                   [b / a - 2 * a / b, -(b / a + a / b), -2 * b / a + a / b, 2 * (b / a + a / b)]]) / 6.0
    fe = 2.0 * a * b / 4.0
    rows, cols, vals = [], [], []
    F = np.zeros(neq)
    for i in range(nx):
        for j in range(ny):
            if not regiao[i, j]:
                continue
            ns = (nid(i, j), nid(i + 1, j), nid(i + 1, j + 1), nid(i, j + 1))
            es = [eq[q] for q in ns]
            for r in range(4):
                if es[r] < 0:
                    continue
                F[es[r]] += fe
                if material[i, j]:
                    for c in range(4):
                        if es[c] >= 0:
                            rows.append(es[r])
                            cols.append(es[c])
                            vals.append(ke[r, c])
    if neq == 0:
        return 0.0
    K = coo_matrix((vals, (rows, cols)), shape=(neq, neq)).tocsr()
    # incógnita de furo sem rigidez (furo isolado sem material em volta): evita matriz singular
    diag = K.diagonal()
    if (diag <= 0).any():
        K = K + coo_matrix((np.where(diag <= 0, 1.0, 0.0), (np.arange(neq), np.arange(neq))),
                           shape=(neq, neq)).tocsr()
    phi = spsolve(K, F)
    return float(2.0 * phi @ F / 2.0)


# ------------------------------------------------------------------ objeto do documento
class SecaoPersonalizada:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyLink", "Esboco", "Seção", "Esboço (ou peça com uma face plana) com o contorno da seção")
        add("App::PropertyString", "Nome", "Seção", "Nome do perfil (aparece como 'Personalizado · nome')", "Seção")
        add("App::PropertyString", "Contorno", "Seção", "Contorno calculado (JSON)", "", True)
        add("App::PropertyFloat", "Area", "Propriedades", "Área (cm²)", 0.0, True)
        add("App::PropertyFloat", "Ix", "Propriedades", "Momento de inércia em x (cm⁴)", 0.0, True)
        add("App::PropertyFloat", "Iy", "Propriedades", "Momento de inércia em y (cm⁴)", 0.0, True)
        add("App::PropertyFloat", "J", "Propriedades", "Constante de torção (cm⁴)", 0.0, True)
        add("App::PropertyFloat", "MassaLinear", "Propriedades", "Massa por metro (kg/m, aço)", 0.0, True)
        add("App::PropertyStringList", "Avisos", "Propriedades", "Avisos", [], True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)
        self.registrar_salvo(obj)

    def registrar_salvo(self, obj):
        try:
            it = json.loads(obj.Contorno) if obj.Contorno else None
        except ValueError:
            it = None
        if it:
            registrar(it)

    def execute(self, obj):
        import PrumoSecao
        if obj.Esboco is None:
            obj.Avisos = ["escolha o esboço com o contorno"]
            return
        try:
            ext, furos = contornos_de(obj.Esboco.Shape)
            it = item_de(obj.Nome or obj.Esboco.Label, ext, furos)
            registrar(it)
            p = PrumoSecao.propriedades(it)
        except Exception as ex:
            obj.Avisos = [str(ex)]
            FreeCAD.Console.PrintWarning("Prumo: seção personalizada: %s\n" % ex)
            return
        obj.Contorno = json.dumps(it)
        obj.Area = round(p["A"] / 100.0, 4)
        obj.Ix = round(p["Ix"] / 1e4, 4)
        obj.Iy = round(p["Iy"] / 1e4, 4)
        obj.J = round(p["J"] / 1e4, 5)
        obj.MassaLinear = round(p["massa_kgm"], 3)
        obj.Avisos = []

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc, esboco, nome=None):
    o = doc.addObject("App::FeaturePython", "SecaoPersonalizada")
    SecaoPersonalizada(o)
    o.Esboco = esboco
    o.Nome = nome or esboco.Label
    o.Label = "Seção personalizada · %s" % o.Nome
    if FreeCAD.GuiUp:
        try:
            import PrumoUtil
            o.ViewObject.Proxy = _VP(o.ViewObject)
        except Exception:
            pass
    doc.recompute()
    return o


def registrar_documento(doc):
    """Registra as seções personalizadas de um documento (ao abrir)."""
    for o in doc.Objects:
        if isinstance(getattr(o, "Proxy", None), SecaoPersonalizada):
            o.Proxy.registrar_salvo(o)


class _VP:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        import PrumoUtil
        return PrumoUtil.icone("estrutura.svg")

    def attach(self, vobj):
        self.Object = vobj.Object

    def claimChildren(self):
        e = getattr(self.Object, "Esboco", None)
        return [e] if e is not None else []

    def dumps(self):
        return None

    def loads(self, state):
        return None


class CmdSecaoPersonalizada:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("estrutura.svg"), "MenuText": "Seção personalizada",
                "ToolTip": "Transforma um esboço fechado (ou uma face plana) num perfil da estrutura soldada: "
                           "chapas compostas, perfis dobrados ou fora do catálogo. Área, inércias e torção são "
                           "calculadas e o perfil entra no cálculo por barras."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        import FreeCADGui
        from PySide import QtWidgets
        sel = FreeCADGui.Selection.getSelection()
        mw = FreeCADGui.getMainWindow()
        if not sel or not hasattr(sel[0], "Shape"):
            QtWidgets.QMessageBox.information(mw, "Seção personalizada",
                                              "Selecione o esboço com o contorno da seção (fechado; furos e "
                                              "tubos como contornos internos) e clique de novo.")
            return
        nome, ok = QtWidgets.QInputDialog.getText(mw, "Seção personalizada", "Nome do perfil:",
                                                  text=sel[0].Label)
        if not ok:
            return
        doc = FreeCAD.ActiveDocument
        doc.openTransaction("Seção personalizada")
        o = criar(doc, sel[0], nome.strip() or sel[0].Label)
        doc.commitTransaction()
        if o.Avisos:
            QtWidgets.QMessageBox.warning(mw, "Seção personalizada", "; ".join(o.Avisos))
            return
        QtWidgets.QMessageBox.information(
            mw, "Seção personalizada",
            "Perfil '%s%s' criado.\n\nA = %.2f cm² · Ix = %.1f cm⁴ · Iy = %.1f cm⁴ · J = %.3f cm⁴ · %.2f kg/m\n\n"
            "Ele aparece na família 'Seções personalizadas' ao montar ou editar a estrutura."
            % (PREFIXO, o.Nome, o.Area, o.Ix, o.Iy, o.J, o.MassaLinear))
