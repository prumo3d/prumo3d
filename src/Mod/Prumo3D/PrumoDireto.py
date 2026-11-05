# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: modelagem direta (ideias da bancada Direct, de Sergio Uhry, reescritas para o Usinix).

- Extrudar face: a face plana vira o perfil de uma Extrusão (como puxar a face). O contorno é copiado para um
  esboço próprio, sem ligar na face, então mudar a peça depois não quebra a extrusão.
- Desenhar na face: corpo novo com um esboço no plano da face, sem ligação com a outra peça.
- Posicionar: encosta face com face (normais opostas) ou leva um ponto a outro.
- Linhas guia: retas de referência no 3D a partir de uma aresta, deslocadas por uma medida; cruzamentos das guias
  viram pontos para o encaixe do cursor; quatro guias (dois pares paralelos) viram a base de uma peça.
- Isolar / restaurar: mostra só a peça (ou o conjunto) escolhida e depois volta como estava.
- Medir X, Y, Z: menor distância entre duas seleções, com as componentes nos eixos.
- Matriz leve: repetição por vínculos (não copia a peça), por intervalo, vão livre ou dimensão total.
- Matriz de furação: um furo ou cavidade repetido em linhas e colunas, sem duplicar o esboço.
"""
import math

import FreeCAD

TOL = 1e-6
V = FreeCAD.Vector


# ------------------------------------------------------------------ utilidades de seleção e geometria
def selecao():
    """[(objeto, nome do subelemento, forma do subelemento, ponto clicado)] na ordem em que foi selecionado."""
    import FreeCADGui
    res = []
    for so in FreeCADGui.Selection.getSelectionEx("", 0):
        obj = so.Object
        subs = list(so.SubElementNames) or [""]
        pts = list(so.PickedPoints)
        for i, sub in enumerate(subs):
            try:
                forma = obj.getSubObject(sub) if sub else getattr(obj, "Shape", None)
            except Exception:
                forma = None
            alvo = obj
            try:
                alvo = obj.getSubObject(sub, retType=1) or obj      # objeto de verdade (ex.: dentro do corpo)
                if isinstance(alvo, tuple):
                    alvo = alvo[0]
            except Exception:
                pass
            res.append((alvo, sub.split(".")[-1] if sub else "", forma, pts[i] if i < len(pts) else None))
    return res


def corpo_de(obj):
    for o in getattr(obj, "InList", []):
        if o.TypeId == "PartDesign::Body":
            return o
    return obj if getattr(obj, "TypeId", "") == "PartDesign::Body" else None


def peca_de(obj):
    """O objeto que se move como peça: o corpo do recurso, ou o próprio objeto solto."""
    c = corpo_de(obj)
    return c if c is not None else obj


def placement_da_face(face):
    """Placement com Z na normal da face plana e X numa aresta reta dela (ou no X global projetado)."""
    plana = face.Surface.TypeId == "Part::GeomPlane"
    if not plana:
        try:
            plana = face.findPlane() is not None
        except Exception:
            plana = False
    if not plana:
        raise ValueError("a face não é plana")
    u0, u1, v0, v1 = face.ParameterRange
    n = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
    n.normalize()
    x = None
    for e in face.Edges:
        if e.Curve.TypeId == "Part::GeomLine":
            d = e.Vertexes[-1].Point - e.Vertexes[0].Point
            if d.Length > TOL:
                x = d.normalize()
                break
    if x is None:
        for cand in (V(1, 0, 0), V(0, 1, 0)):
            x = cand - n * cand.dot(n)
            if x.Length > 1e-3:
                break
        x.normalize()
    y = n.cross(x)
    rot = FreeCAD.Rotation(x, y, n, "ZXY")
    origem = face.Vertexes[0].Point if face.Vertexes else face.CenterOfMass
    return FreeCAD.Placement(origem, rot)


def _arco_no_plano(e):
    """ArcOfCircle no plano XY do esboço a partir de uma aresta de arco já em coordenadas locais."""
    import Part
    a = e.Vertexes[0].Point
    b = e.Vertexes[-1].Point
    m = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
    a.z = b.z = m.z = 0
    arco = Part.ArcOfCircle(a, m, b)
    if arco.Axis.z < 0:
        arco = Part.ArcOfCircle(b, m, a)
    return arco


def geometria_no_esboco(face, pl):
    """Curvas do contorno da face (todos os furos inclusive) no sistema do esboço de placement `pl`."""
    import Part
    inv = pl.inverse().toMatrix()
    geos = []
    for w in face.Wires:
        for e0 in w.Edges:
            e = e0.copy()
            e.transformShape(inv)
            c = e.Curve
            if c.TypeId == "Part::GeomLine":
                p, q = e.Vertexes[0].Point, e.Vertexes[-1].Point
                p.z = q.z = 0
                if (q - p).Length > TOL:
                    geos.append(Part.LineSegment(p, q))
            elif c.TypeId == "Part::GeomCircle":
                if e.isClosed():
                    ctr = V(c.Center.x, c.Center.y, 0)
                    geos.append(Part.Circle(ctr, V(0, 0, 1), c.Radius))
                else:
                    geos.append(_arco_no_plano(e))
            else:
                bs = e.toNurbs().Edges[0].Curve
                pts = [V(p.x, p.y, 0) for p in bs.getPoles()]
                nb = Part.BSplineCurve()
                nb.buildFromPolesMultsKnots(pts, bs.getMultiplicities(), bs.getKnots(), bs.isPeriodic(),
                                            bs.Degree, bs.getWeights())
                geos.append(nb)
    return geos


def esboco_da_face(doc, face, corpo, nome="Esboco", copiar=True):
    pl = placement_da_face(face)
    sk = doc.addObject("Sketcher::SketchObject", nome)
    corpo.addObject(sk)
    sk.MapMode = "Deactivated"
    sk.Placement = corpo.getGlobalPlacement().inverse().multiply(pl) if hasattr(corpo, "getGlobalPlacement") else pl
    if copiar:
        for g in geometria_no_esboco(face, pl):
            sk.addGeometry(g, False)
    return sk


# ------------------------------------------------------------------ extrudar e desenhar na face
def _face_plana_selecionada():
    for obj, sub, forma, _p in selecao():
        if forma is not None and getattr(forma, "ShapeType", "") == "Face":
            try:
                placement_da_face(forma)
            except ValueError:
                raise ValueError("a face selecionada não é plana")
            return obj, sub, forma
    raise ValueError("selecione uma face plana")


def extrudar_face(obj=None, face=None, editar=True):
    """Extrusão a partir do contorno de uma face plana. Devolve a Extrusão (Pad)."""
    import FreeCADGui
    if face is None:
        obj, _sub, face = _face_plana_selecionada()
    doc = obj.Document
    doc.openTransaction("Extrudar face")
    try:
        corpo = corpo_de(obj)
        if corpo is None:
            corpo = doc.addObject("PartDesign::Body", "Body")
            corpo.Label = "Extrusão de %s" % obj.Label
        sk = esboco_da_face(doc, face, corpo, "EsbocoDaFace")
        sk.Label = "Contorno da face"
        pad = doc.addObject("PartDesign::Pad", "Pad")
        corpo.addObject(pad)
        pad.Profile = sk
        pad.Length = 10
        sk.Visibility = False
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    if editar and FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", corpo)
        FreeCADGui.ActiveDocument.setEdit(pad.Name, 0)
    return pad


def desenhar_na_face(obj=None, face=None, editar=True):
    """Peça nova com um esboço vazio no plano da face (sem ligação com a peça da face)."""
    import FreeCADGui
    if face is None:
        obj, _sub, face = _face_plana_selecionada()
    doc = obj.Document
    doc.openTransaction("Desenhar na face")
    try:
        corpo = doc.addObject("PartDesign::Body", "Body")
        corpo.Label = "Peça sobre %s" % obj.Label
        sk = esboco_da_face(doc, face, corpo, "Esboco", copiar=False)
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    if editar and FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", corpo)
        FreeCADGui.ActiveDocument.setEdit(sk.Name, 0)
    return sk


# ------------------------------------------------------------------ posicionar
def _ref(forma, ponto):
    """(ponto, normal ou None) de uma referência: face plana, vértice, aresta (ponto mais próximo do clique)."""
    t = getattr(forma, "ShapeType", "")
    if t == "Vertex":
        return forma.Point, None
    if t == "Face":
        c = forma.CenterOfMass
        if ponto is not None:
            try:
                u, v = forma.Surface.parameter(ponto)
                c = forma.valueAt(u, v)
            except Exception:
                pass
        try:
            u, v = forma.Surface.parameter(c)
            n = forma.normalAt(u, v)
        except Exception:
            n = None
        return c, n
    if t == "Edge":
        if forma.Curve.TypeId == "Part::GeomCircle":
            return forma.Curve.Center, forma.Curve.Axis
        return forma.CenterOfMass, None
    raise ValueError("referência sem posição")


def transformacao_para_encostar(a_pto, a_n, b_pto, b_n, folga=0.0):
    """Placement global que leva a referência A até B (faces ficam frente a frente, com `folga` entre elas)."""
    rot = FreeCAD.Rotation()
    if a_n is not None and b_n is not None:
        rot = FreeCAD.Rotation(a_n, -b_n)
    destino = b_pto + (b_n * folga if b_n is not None else V())
    t = destino - rot.multVec(a_pto)
    return FreeCAD.Placement(t, rot)


def aplicar_global(peca, T):
    """Move a peça pela transformação global T (respeitando o pai: corpo dentro de parte etc.)."""
    try:
        g = peca.getGlobalPlacement()
        pai = g.multiply(peca.Placement.inverse())
    except Exception:
        g, pai = peca.Placement, FreeCAD.Placement()
    novo_global = T.multiply(g)
    peca.Placement = pai.inverse().multiply(novo_global)


def posicionar(folga=0.0):
    """Duas referências selecionadas: a primeira (da peça que se move) vai até a segunda."""
    sel = [s for s in selecao() if s[2] is not None]
    if len(sel) != 2:
        raise ValueError("selecione duas referências: primeiro na peça que vai se mover, depois no destino")
    (oa, _sa, fa, pa), (ob, _sb, fb, pb) = sel
    peca = peca_de(oa)
    if peca is peca_de(ob):
        raise ValueError("as duas referências são da mesma peça")
    a = _ref(fa, pa)
    b = _ref(fb, pb)
    T = transformacao_para_encostar(a[0], a[1], b[0], b[1], folga)
    doc = peca.Document
    doc.openTransaction("Posicionar peça")
    aplicar_global(peca, T)
    doc.recompute()
    doc.commitTransaction()
    return peca


# ------------------------------------------------------------------ linhas guia
COR_GUIA = (0.97, 0.75, 0.0)


class LinhaGuia:
    """Reta de referência: ponto, direção, comprimento e deslocamento (não entra em sólido nem em lista)."""

    def __init__(self, obj, p, d, comp):
        obj.Proxy = self
        obj.addProperty("App::PropertyVector", "Ponto", "Guia", "Ponto da reta")
        obj.addProperty("App::PropertyVector", "Direcao", "Guia", "Direção da reta")
        obj.addProperty("App::PropertyLength", "Comprimento", "Guia", "Comprimento desenhado")
        obj.addProperty("App::PropertyVector", "Deslocamento", "Guia", "Deslocamento da guia em relação à aresta")
        obj.Ponto, obj.Direcao, obj.Comprimento = p, d, comp

    def execute(self, obj):
        import Part
        d = V(obj.Direcao)
        if d.Length < TOL:
            return
        d.normalize()
        c = obj.Ponto + obj.Deslocamento
        h = float(obj.Comprimento) / 2.0
        obj.Shape = Part.LineSegment(c - d * h, c + d * h).toShape()

    def dumps(self):
        return None

    def loads(self, s):
        return None


class VPLinhaGuia:
    def __init__(self, vobj):
        vobj.Proxy = self
        vobj.LineColor = COR_GUIA
        vobj.LineWidth = 1.5
        try:
            vobj.DrawStyle = "Dashdot"
        except Exception:
            pass

    def getIcon(self):
        import PrumoUtil
        return PrumoUtil.icone("linha_guia.svg")

    def dumps(self):
        return None

    def loads(self, s):
        return None


def _tamanho_modelo(doc):
    bb = FreeCAD.BoundBox()
    for o in doc.Objects:
        sh = getattr(o, "Shape", None)
        if o.TypeId.startswith(("App::Origin", "App::Line", "App::Plane", "App::Point")) or \
                getattr(o, "Proxy", None).__class__.__name__ == "LinhaGuia":
            continue
        if sh is not None and not sh.isNull():
            try:
                sbb = sh.BoundBox
                if sbb.isValid() and sbb.DiagonalLength < 1e9:
                    bb.add(sbb)
            except Exception:
                pass
    return max(bb.DiagonalLength if bb.isValid() else 0, 1000.0)


def criar_guia(doc, p, d, deslocamento=V(), comp=None):
    o = doc.addObject("Part::FeaturePython", "LinhaGuia")
    LinhaGuia(o, p, d, comp or 2 * _tamanho_modelo(doc))
    o.Deslocamento = deslocamento
    o.Label = "Linha guia"
    if FreeCAD.GuiUp:
        VPLinhaGuia(o.ViewObject)
    grupo = doc.getObject("PrumoGuias")
    if grupo is None:
        grupo = doc.addObject("App::DocumentObjectGroup", "PrumoGuias")
        grupo.Label = "Linhas guia"
    grupo.addObject(o)
    doc.recompute()
    return o


def guia_da_selecao(distancia=0.0, direcao=None):
    """Guia sobre a aresta reta (ou guia) selecionada, deslocada `distancia` na direção dada (vetor)."""
    for obj, _sub, forma, _p in selecao():
        if forma is not None and getattr(forma, "ShapeType", "") == "Edge" and \
                forma.Curve.TypeId == "Part::GeomLine":
            p0, p1 = forma.Vertexes[0].Point, forma.Vertexes[-1].Point
            d = p1 - p0
            desl = V()
            if direcao is not None and distancia:
                u = V(direcao)
                u = u - d.normalize() * u.dot(d.normalize())     # só a parte perpendicular à guia
                if u.Length < TOL:
                    raise ValueError("a direção do deslocamento é a própria direção da guia")
                desl = u.normalize() * distancia
            doc = obj.Document
            doc.openTransaction("Linha guia")
            g = criar_guia(doc, (p0 + p1) * 0.5, d, desl)
            doc.commitTransaction()
            return g
    raise ValueError("selecione uma aresta reta (ou uma linha guia)")


def guias(doc):
    return [o for o in doc.Objects if getattr(getattr(o, "Proxy", None), "__class__", None).__name__ == "LinhaGuia"]


def cruzamento(g1, g2):
    """Ponto onde duas guias se cruzam (coplanares, não paralelas), ou None."""
    e1, e2 = g1.Shape.Edges[0], g2.Shape.Edges[0]
    d, pares, _info = e1.distToShape(e2)
    if d > 1e-4:
        return None
    a = e1.Vertexes[-1].Point - e1.Vertexes[0].Point
    b = e2.Vertexes[-1].Point - e2.Vertexes[0].Point
    if a.cross(b).Length < 1e-9 * a.Length * b.Length:
        return None
    return pares[0][0]


def atualizar_cruzamentos(doc):
    """Pontos nos cruzamentos de todas as guias (o cursor encaixa neles nas ferramentas de desenho)."""
    import Part
    gs = guias(doc)
    pts = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            p = cruzamento(gs[i], gs[j])
            if p is not None and not any((p - q).Length < 1e-3 for q in pts):
                pts.append(p)
    o = doc.getObject("PrumoCruzamentos")
    if o is None:
        o = doc.addObject("Part::Feature", "PrumoCruzamentos")
        o.Label = "Cruzamentos das guias"
        g = doc.getObject("PrumoGuias")
        if g is not None:
            g.addObject(o)
        if FreeCAD.GuiUp:
            o.ViewObject.PointColor = COR_GUIA
            o.ViewObject.PointSize = 6
    o.Shape = Part.Compound([Part.Vertex(p) for p in pts]) if pts else Part.Shape()
    doc.recompute()
    return pts


def peca_pelas_guias(gs, editar=True):
    """Quatro guias coplanares (dois pares paralelos) viram um retângulo num esboço e a Extrusão de uma peça."""
    import Part
    import FreeCADGui
    if len(gs) != 4:
        raise ValueError("selecione exatamente quatro linhas guia")
    dirs = [(g.Shape.Edges[0].Vertexes[-1].Point - g.Shape.Edges[0].Vertexes[0].Point).normalize() for g in gs]
    par_a = [0] + [i for i in range(1, 4) if abs(abs(dirs[0].dot(dirs[i])) - 1) < 1e-6]
    if len(par_a) != 2:
        raise ValueError("as guias precisam formar dois pares de retas paralelas")
    par_b = [i for i in range(4) if i not in par_a]
    if abs(abs(dirs[par_b[0]].dot(dirs[par_b[1]])) - 1) > 1e-6:
        raise ValueError("as guias precisam formar dois pares de retas paralelas")
    cantos = []
    for i in par_a:
        for j in par_b:
            p = cruzamento(gs[i], gs[j])
            if p is None:
                raise ValueError("as guias não se cruzam (não estão no mesmo plano)")
            cantos.append(p)
    c0, c1, c3, c2 = cantos[0], cantos[1], cantos[2], cantos[3]
    contorno = Part.Face(Part.makePolygon([c0, c1, c2, c3, c0]))
    doc = gs[0].Document
    doc.openTransaction("Peça pelas guias")
    try:
        corpo = doc.addObject("PartDesign::Body", "Body")
        corpo.Label = "Peça pelas guias"
        sk = esboco_da_face(doc, contorno, corpo, "EsbocoGuias")
        pad = doc.addObject("PartDesign::Pad", "Pad")
        corpo.addObject(pad)
        pad.Profile = sk
        pad.Length = 10
        sk.Visibility = False
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    if editar and FreeCAD.GuiUp:
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", corpo)
        FreeCADGui.ActiveDocument.setEdit(pad.Name, 0)
    return pad


# ------------------------------------------------------------------ isolar / restaurar
_ISOLADO = {}


def _ramo(obj):
    """Objetos que precisam ficar visíveis para a peça aparecer: ela, seus pais e o que está dentro dela."""
    vis = {obj}
    for o in obj.InListRecursive:
        if o.isDerivedFrom("App::Part") or o.TypeId == "PartDesign::Body" or \
                o.isDerivedFrom("App::DocumentObjectGroup") or o.TypeId.startswith("Assembly::"):
            vis.add(o)
    for o in getattr(obj, "OutListRecursive", []):
        if obj.isDerivedFrom("App::Part") or obj.TypeId.startswith("Assembly::"):
            vis.add(o)
    tip = getattr(obj, "Tip", None)
    if tip is not None:
        vis.add(tip)
    return vis


def isolar(objs=None):
    """Mostra só as peças escolhidas; chamar de novo (sem seleção) restaura a visibilidade anterior."""
    import FreeCADGui
    doc = FreeCAD.ActiveDocument
    if doc is None:
        raise ValueError("nenhum projeto aberto")
    if doc.Name in _ISOLADO and not objs:
        return restaurar(doc)
    if objs is None:
        objs = [peca_de(s[0]) for s in selecao()]
    if not objs:
        raise ValueError("selecione a peça (ou o conjunto) que quer ver sozinha")
    if doc.Name not in _ISOLADO:
        _ISOLADO[doc.Name] = {o.Name: bool(o.ViewObject.Visibility) for o in doc.Objects
                              if getattr(o, "ViewObject", None) is not None}
    manter = set()
    for o in objs:
        manter |= _ramo(o)
    for o in doc.Objects:
        vo = getattr(o, "ViewObject", None)
        if vo is None or not hasattr(o, "Shape") and not o.isDerivedFrom("App::Part"):
            continue
        if o.TypeId.startswith(("App::Origin", "App::Line", "App::Plane", "App::Point")):
            continue
        estava = _ISOLADO[doc.Name].get(o.Name, False)
        if o in manter:
            vo.Visibility = estava or o in objs
        elif vo.Visibility:
            vo.Visibility = False
    FreeCADGui.Selection.clearSelection()
    return len(objs)


def restaurar(doc=None):
    doc = doc or FreeCAD.ActiveDocument
    estado = _ISOLADO.pop(doc.Name, None) if doc is not None else None
    if not estado:
        return 0
    for nome, vis in estado.items():
        o = doc.getObject(nome)
        if o is not None and getattr(o, "ViewObject", None) is not None:
            o.ViewObject.Visibility = vis
    return len(estado)


def isolado(doc=None):
    doc = doc or FreeCAD.ActiveDocument
    return doc is not None and doc.Name in _ISOLADO


# ------------------------------------------------------------------ medir X, Y, Z
def medir_xyz(sel=None):
    """(distância 3D, dx, dy, dz, ponto A, ponto B) da menor distância entre as duas seleções."""
    sel = [s for s in (sel or selecao()) if s[2] is not None and not s[2].isNull()]
    if len(sel) != 2:
        raise ValueError("selecione dois elementos (vértice, aresta, face ou peça) com Ctrl")
    d, pares, _i = sel[0][2].distToShape(sel[1][2])
    a, b = pares[0]
    v = b - a
    return d, v.x, v.y, v.z, a, b


# ------------------------------------------------------------------ matriz leve
MODOS_MATRIZ = [("intervalo", "Intervalo (de centro a centro)"), ("vao", "Vão livre entre as peças"),
                ("total", "Dimensão total")]


def passo(modo, valor, tamanho, n):
    """Passo entre as cópias a partir do modo: intervalo, vão livre (entre faces) ou dimensão total."""
    if n <= 1:
        return 0.0
    if modo == "intervalo":
        return valor
    if modo == "vao":
        return tamanho + valor
    if modo == "total":
        return (valor - tamanho) / float(n - 1)
    raise ValueError(modo)


def matriz_leve(obj, eixos):
    """eixos: {"X": (n, modo, valor, inverter), ...}. Matriz de vínculos (Draft) com os passos calculados."""
    import Draft
    bb = obj.Shape.BoundBox if hasattr(obj, "Shape") else FreeCAD.BoundBox(0, 0, 0, 0, 0, 0)
    tam = {"X": bb.XLength, "Y": bb.YLength, "Z": bb.ZLength}
    vs, ns = {}, {}
    for e, base in (("X", V(1, 0, 0)), ("Y", V(0, 1, 0)), ("Z", V(0, 0, 1))):
        n, modo, valor, inv = eixos.get(e, (1, "intervalo", 0.0, False))
        p = passo(modo, valor, tam[e], n)
        vs[e] = base * (p * (-1 if inv else 1))
        ns[e] = max(1, int(n))
    doc = obj.Document
    doc.openTransaction("Matriz leve")
    arr = Draft.make_ortho_array(obj, vs["X"], vs["Y"], vs["Z"], ns["X"], ns["Y"], ns["Z"], use_link=True)
    arr.Label = "Matriz leve de %s" % obj.Label
    doc.recompute()
    doc.commitTransaction()
    return arr


# ------------------------------------------------------------------ matriz de furação
def matriz_furacao(op, n_col, passo_col, n_lin, passo_lin):
    """Furo/cavidade repetido em colunas (X do esboço) e linhas (Y do esboço), num Padrão linear de 2 direções."""
    if op.TypeId not in ("PartDesign::Hole", "PartDesign::Pocket"):
        raise ValueError("selecione um Furo ou uma Cavidade")
    corpo = corpo_de(op)
    sk = op.Profile[0] if op.Profile else None
    if corpo is None or sk is None:
        raise ValueError("o furo precisa estar num corpo e ter esboço")
    doc = op.Document
    doc.openTransaction("Matriz de furação")
    try:
        pat = doc.addObject("PartDesign::LinearPattern", "MatrizFuracao")
        corpo.addObject(pat)
        pat.Originals = [op]
        pat.Direction = (sk, ["H_Axis"])
        pat.Mode = "Spacing"
        pat.Offset = passo_col
        pat.Occurrences = max(1, int(n_col))
        pat.Direction2 = (sk, ["V_Axis"])
        pat.Mode2 = "Spacing"
        pat.Offset2 = passo_lin
        pat.Occurrences2 = max(1, int(n_lin))
        pat.Label = "Matriz de furação %d × %d" % (n_col, n_lin)
        corpo.Tip = pat
        op.Visibility = False
        pat.Visibility = True
        doc.recompute()
    except Exception:
        doc.abortTransaction()
        raise
    doc.commitTransaction()
    return pat


# ------------------------------------------------------------------ interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    def _aviso(texto, tipo="aviso"):
        import PrumoAvisoClique as AV
        AV.mostrar(texto, tipo)

    def _rodar(nome, fn):
        try:
            return fn()
        except ValueError as exc:
            _aviso("%s: %s." % (nome, exc))
        except Exception as exc:
            _aviso("%s não foi executada: %s" % (nome, exc), "erro")
        return None

    class _Janela(QtWidgets.QDialog):
        def __init__(self, titulo):
            super().__init__(FreeCADGui.getMainWindow())
            import PrumoUI as UI
            self.setObjectName("PrumoUI")
            self.setStyleSheet(UI.qss())
            self.setWindowTitle(titulo)
            self.form = QtWidgets.QFormLayout()
            lay = QtWidgets.QVBoxLayout(self)
            lay.addLayout(self.form)
            self.nota = QtWidgets.QLabel("")
            self.nota.setObjectName("PrumoSub")
            self.nota.setWordWrap(True)
            lay.addWidget(self.nota)
            bts = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            bts.button(QtWidgets.QDialogButtonBox.Ok).setText("Criar")
            bts.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
            bts.accepted.connect(self.accept)
            bts.rejected.connect(self.reject)
            lay.addWidget(bts)

        def numero(self, rotulo, valor, minimo=-1e6, maximo=1e6, casas=1, sufixo=" mm"):
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(minimo, maximo)
            sp.setDecimals(casas)
            sp.setSuffix(sufixo)
            sp.setValue(valor)
            self.form.addRow(rotulo, sp)
            return sp

        def inteiro(self, rotulo, valor, minimo=1, maximo=500):
            sp = QtWidgets.QSpinBox()
            sp.setRange(minimo, maximo)
            sp.setValue(valor)
            self.form.addRow(rotulo, sp)
            return sp

        def escolha(self, rotulo, itens):
            cb = QtWidgets.QComboBox()
            for chave, texto in itens:
                cb.addItem(texto, chave)
            self.form.addRow(rotulo, cb)
            return cb

    DIRECOES = [("x", "X (global)", V(1, 0, 0)), ("-x", "−X", V(-1, 0, 0)), ("y", "Y (global)", V(0, 1, 0)),
                ("-y", "−Y", V(0, -1, 0)), ("z", "Z (para cima)", V(0, 0, 1)), ("-z", "−Z", V(0, 0, -1))]

    class CmdExtrudarFace:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("extrudar_face.svg"), "MenuText": "Extrudar face",
                    "ToolTip": "Selecione uma face plana: o contorno dela vira uma Extrusão (como puxar a face). "
                               "O contorno é copiado, sem ligar na face, para não quebrar se a peça mudar."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            _rodar("Extrudar face", extrudar_face)

    class CmdDesenharNaFace:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("desenhar_face.svg"), "MenuText": "Desenhar na face",
                    "ToolTip": "Selecione uma face plana: abre um esboço de uma peça nova no plano dela, sem ligação "
                               "com a outra peça."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            _rodar("Desenhar na face", desenhar_na_face)

    class CmdPosicionar:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("posicionar.svg"), "MenuText": "Posicionar peça",
                    "ToolTip": "Selecione (com Ctrl) primeiro a face ou o ponto da peça que vai se mover, depois o "
                               "destino: face com face fica encostada (frente a frente); ponto com ponto se sobrepõe."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            p = _rodar("Posicionar peça", posicionar)
            if p is not None:
                _aviso("%s posicionada. Desfazer: Ctrl+Z." % p.Label)

    class CmdLinhaGuia:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("linha_guia.svg"), "MenuText": "Linha guia",
                    "ToolTip": "Selecione uma aresta reta (ou outra guia): cria uma reta de referência, deslocada "
                               "pela medida que você digitar. Os cruzamentos das guias viram pontos de encaixe."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            if not any(f is not None and getattr(f, "ShapeType", "") == "Edge" for _o, _s, f, _p in selecao()):
                _aviso("Linha guia: selecione uma aresta reta (ou uma linha guia) antes.")
                return
            j = _Janela("Linha guia")
            dist = j.numero("Deslocamento", 0.0)
            dire = j.escolha("Para o lado", [(k, t) for k, t, _v in DIRECOES])
            j.nota.setText("0 = guia em cima da aresta, prolongada. A guia não entra em sólido nem na lista de "
                           "materiais; ficam todas no grupo \"Linhas guia\".")
            if j.exec() != QtWidgets.QDialog.Accepted:
                return
            vet = dict((k, v) for k, _t, v in DIRECOES)[dire.currentData()]
            g = _rodar("Linha guia", lambda: guia_da_selecao(dist.value(), vet))
            if g is not None:
                atualizar_cruzamentos(g.Document)

    class CmdPecaPelasGuias:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("peca_guias.svg"), "MenuText": "Peça pelas guias",
                    "ToolTip": "Selecione quatro linhas guia no mesmo plano (dois pares paralelos): o retângulo entre "
                               "elas vira a base de uma peça nova, e abre a Extrusão."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            gs = [o for o in FreeCADGui.Selection.getSelection()
                  if getattr(getattr(o, "Proxy", None), "__class__", None).__name__ == "LinhaGuia"]
            _rodar("Peça pelas guias", lambda: peca_pelas_guias(gs))

    class CmdIsolar:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("isolar.svg"), "MenuText": "Isolar / restaurar peça",
                    "ToolTip": "Mostra só a peça (ou o conjunto) selecionada. Clique de novo para voltar a ver tudo "
                               "como estava."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            if isolado() and not FreeCADGui.Selection.getSelection():
                restaurar()
                return
            n = _rodar("Isolar peça", isolar)
            if n:
                _aviso("Mostrando só a seleção. Clique em Isolar de novo (sem selecionar nada) para ver tudo.")

    class PainelMedida(QtWidgets.QFrame):
        def __init__(self, parent):
            super().__init__(parent)
            self.setObjectName("PrumoMedidaXYZ")
            self.setStyleSheet("#PrumoMedidaXYZ { background: #FFFFFF; border: 1px solid #C9D3DE; border-radius: 8px; }"
                               "#PrumoMedidaXYZ QLabel { background: transparent; }")
            lay = QtWidgets.QHBoxLayout(self)
            lay.setContentsMargins(12, 8, 6, 8)
            self.texto = QtWidgets.QLabel("")
            self.texto.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            lay.addWidget(self.texto, 1)
            copiar = QtWidgets.QToolButton()
            copiar.setText("Copiar")
            copiar.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.texto.text()
                                                                                      .replace("<b>", "")
                                                                                      .replace("</b>", "")))
            lay.addWidget(copiar)
            fechar = QtWidgets.QToolButton()
            fechar.setText("×")
            fechar.clicked.connect(self.hide)
            lay.addWidget(fechar)

        def mostrar(self, d, dx, dy, dz):
            import PrumoUtil
            f = lambda v: PrumoUtil.fmt(v, 2) + " mm"
            self.texto.setText("<b>Distância: %s</b>   X: %s   Y: %s   Z: %s" % (f(d), f(dx), f(dy), f(dz)))
            p = self.parentWidget()
            self.adjustSize()
            self.move((p.width() - self.width()) // 2, p.height() - self.height() - 120)
            self.show()
            self.raise_()

    _MEDIDA = {"p": None}

    class CmdMedirXYZ:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("medir_xyz.svg"), "MenuText": "Medir X, Y, Z",
                    "ToolTip": "Selecione dois elementos (vértice, aresta, face ou peça) com Ctrl: menor distância "
                               "entre eles e quanto ela vale em X, Y e Z."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            r = _rodar("Medir X, Y, Z", medir_xyz)
            if r is None:
                return
            import shiboken6
            p = _MEDIDA["p"]
            if p is None or not shiboken6.isValid(p):
                p = PainelMedida(FreeCADGui.getMainWindow())
                _MEDIDA["p"] = p
            p.mostrar(*r[:4])

    class CmdMatrizLeve:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("matriz_leve.svg"), "MenuText": "Matriz leve",
                    "ToolTip": "Repete a peça selecionada em X, Y e Z por vínculos (não copia a peça: o arquivo fica "
                               "leve e mudar a original muda todas). Passo por intervalo, vão livre ou dimensão total."}

        def IsActive(self):
            return len(FreeCADGui.Selection.getSelection()) == 1

        def Activated(self):
            obj = peca_de(FreeCADGui.Selection.getSelection()[0])
            j = _Janela("Matriz leve — %s" % obj.Label)
            campos = {}
            bb = obj.Shape.BoundBox if hasattr(obj, "Shape") else None
            for e, tam in (("X", bb.XLength if bb else 0), ("Y", bb.YLength if bb else 0),
                           ("Z", bb.ZLength if bb else 0)):
                t = QtWidgets.QLabel("Eixo %s  (peça com %s mm)" % (e, ("%.1f" % tam).replace(".", ",")))
                t.setStyleSheet("color: #003A70; font-weight: 600; margin-top: 4px;")
                j.form.addRow(t)
                n = j.inteiro("Quantidade (com a original)", 1)
                modo = j.escolha("Medida", MODOS_MATRIZ)
                val = j.numero("Valor", round(tam * 2, 1) if tam else 100.0, 0)
                inv = QtWidgets.QCheckBox("Para o lado negativo")
                j.form.addRow("", inv)
                campos[e] = (n, modo, val, inv)
            j.nota.setText("Vão livre: espaço entre uma peça e a outra. Dimensão total: da primeira face à última.")
            if j.exec() != QtWidgets.QDialog.Accepted:
                return
            eixos = {e: (n.value(), m.currentData(), v.value(), i.isChecked()) for e, (n, m, v, i) in campos.items()}
            _rodar("Matriz leve", lambda: matriz_leve(obj, eixos))

    class CmdMatrizFuracao:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("matriz_furacao.svg"), "MenuText": "Matriz de furação",
                    "ToolTip": "Selecione um Furo ou uma Cavidade: repete em colunas e linhas (nas direções do "
                               "esboço dele), sem duplicar o esboço."}

        def IsActive(self):
            return len(FreeCADGui.Selection.getSelection()) == 1

        def Activated(self):
            op = FreeCADGui.Selection.getSelection()[0]
            if op.TypeId not in ("PartDesign::Hole", "PartDesign::Pocket"):
                _aviso("Matriz de furação: selecione um Furo ou uma Cavidade (o primeiro furo).")
                return
            j = _Janela("Matriz de furação")
            nc = j.inteiro("Colunas (com o furo original)", 3)
            pc = j.numero("Passo entre colunas", 50.0)
            nl = j.inteiro("Linhas", 2)
            pl = j.numero("Passo entre linhas", 50.0)
            j.nota.setText("Colunas seguem o eixo horizontal do esboço do furo; linhas, o vertical. Passo negativo "
                           "inverte o sentido.")
            if j.exec() != QtWidgets.QDialog.Accepted:
                return
            _rodar("Matriz de furação", lambda: matriz_furacao(op, nc.value(), pc.value(), nl.value(), pl.value()))

    def registrar_comandos():
        for nome, cls in (("Prumo_ExtrudarFace", CmdExtrudarFace), ("Prumo_DesenharNaFace", CmdDesenharNaFace),
                          ("Prumo_Posicionar", CmdPosicionar), ("Prumo_LinhaGuia", CmdLinhaGuia),
                          ("Prumo_PecaPelasGuias", CmdPecaPelasGuias), ("Prumo_Isolar", CmdIsolar),
                          ("Prumo_MedirXYZ", CmdMedirXYZ), ("Prumo_MatrizLeve", CmdMatrizLeve),
                          ("Prumo_MatrizFuracao", CmdMatrizFuracao)):
            FreeCADGui.addCommand(nome, cls())
