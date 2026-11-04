# -*- coding: utf-8 -*-
"""Arredondar em duas etapas quando o arredondamento de uma face (ou de várias arestas) não fecha.

O motor de arredondamento do OpenCASCADE falha ("BRep_API: command not done") quando, no mesmo passo,
há arestas com canto para fora (convexas) e para dentro (côncavas) que se encontram num vértice, como na
face interna de um perfil depois de um corte. Cada aresta sozinha arredonda; todas juntas, não.

Aqui o Prumo testa o arredondamento; se falhar, separa as arestas em dois grupos (para fora / para dentro),
deixa o arredondamento atual só com o primeiro grupo e cria logo depois, no mesmo corpo, um segundo
arredondamento com o outro grupo, com o mesmo raio. Se nem em duas etapas fechar, não muda nada.
"""

import FreeCAD

_AVISO = "Arredondamento feito em duas etapas (cantos para fora e para dentro)."


def _arestas(shape, subs):
    """Arestas (objetos) das referências: FaceN vira as arestas da face; EdgeN, a própria."""
    out = []
    for s in subs:
        try:
            if s.startswith("Face"):
                out.extend(shape.Faces[int(s[4:]) - 1].Edges)
            elif s.startswith("Edge"):
                out.append(shape.Edges[int(s[4:]) - 1])
        except Exception:
            pass
    unicas = []
    for e in out:
        if not any(e.isSame(u) for u in unicas):
            unicas.append(e)
    return unicas


def _meio(e):
    return e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)


def _convexa(shape, e):
    """True para canto para fora, False para dentro, None se não der para dizer."""
    import Part
    try:
        fs = shape.ancestorsOfType(e, Part.Face)
    except Exception:
        return None
    if len(fs) != 2:
        return None
    p = _meio(e)
    try:
        u, v = fs[0].Surface.parameter(p)
        n0 = fs[0].normalAt(u, v)
    except Exception:
        return None
    # a outra face "dobra" para trás da normal da primeira -> canto para fora
    d = fs[1].CenterOfMass - p
    return n0.dot(d) < 0


def _nome_no(shape, e, tol=1e-4):
    """Nome (EdgeN) da aresta de shape que passa pelo meio de e (o arredondamento só apara as pontas)."""
    import Part
    p = Part.Vertex(_meio(e))
    melhor, dist = None, None
    for i, x in enumerate(shape.Edges, 1):
        try:
            d = x.distToShape(p)[0]
        except Exception:
            continue
        if dist is None or d < dist:
            melhor, dist = i, d
    return "Edge%d" % melhor if melhor is not None and dist is not None and dist < tol else None


def _funciona(shape, raio, arestas):
    try:
        r = shape.makeFillet(raio, arestas)
        return r if r.isValid() else None
    except Exception:
        return None


def plano(obj):
    """Grupos (primeiro, segundo) de arestas se o arredondamento só fecha em duas etapas; senão None."""
    if obj is None or obj.TypeId != "PartDesign::Fillet" or getattr(obj, "UseAllEdges", False):
        return None
    try:
        base, subs = obj.Base[0], list(obj.Base[1])
    except Exception:
        return None
    base_sh = getattr(base, "Shape", None)
    if base_sh is None or base_sh.isNull():
        return None
    raio = float(obj.Radius)
    arestas = _arestas(base_sh, subs)
    if len(arestas) < 2 or _funciona(base_sh, raio, arestas) is not None:
        return None
    fora = [e for e in arestas if _convexa(base_sh, e) is True]
    dentro = [e for e in arestas if e not in fora]
    if not fora or not dentro:
        return None
    for a, b in ((fora, dentro), (dentro, fora)):
        r = _funciona(base_sh, raio, a)
        if r is None:
            continue
        nomes_b = [_nome_no(r, e) for e in b]
        if None in nomes_b:
            continue
        if _funciona(r, raio, [r.Edges[int(n[4:]) - 1] for n in nomes_b]) is not None:
            return [_indice(base_sh, e) for e in a], b
    return None


def _indice(shape, e):
    for i, x in enumerate(shape.Edges, 1):
        if x.isSame(e):
            return i
    return None


def dividir(obj):
    """Aplica as duas etapas no documento. Devolve o segundo arredondamento (ou None se não precisou)."""
    p = plano(obj)
    if p is None:
        return None
    base = obj.Base[0]
    base_sh = base.Shape
    _, segundo = p
    primeiro = [e for e in _arestas(base_sh, list(obj.Base[1])) if not any(e.isSame(s) for s in segundo)]
    nomes_a = ["Edge%d" % _indice(base_sh, e) for e in primeiro]
    doc = obj.Document
    obj.Base = (base, nomes_a)
    doc.recompute()
    nomes_b = [_nome_no(obj.Shape, e) for e in segundo]
    if None in nomes_b:
        return None
    body = None
    for o in obj.InList:
        if o.TypeId == "PartDesign::Body":
            body = o
            break
    f2 = doc.addObject("PartDesign::Fillet", "Fillet")
    if body is not None:
        body.insertObject(f2, obj, True)
    f2.Base = (obj, nomes_b)
    f2.Radius = obj.Radius
    for prop in ("Refine",):
        if hasattr(obj, prop) and hasattr(f2, prop):
            setattr(f2, prop, getattr(obj, prop))
    f2.Label = obj.Label + " (2ª etapa)"
    if body is not None and body.Tip == obj:
        body.Tip = f2
    try:
        obj.ViewObject.Visibility = False
        f2.ViewObject.Visibility = True
    except Exception:
        pass
    doc.recompute()
    FreeCAD.Console.PrintMessage(_AVISO + "\n")
    return f2


# ---------------------------------------------------------------- no painel: antes do OK

def ligar_ok(obj):
    """Liga, uma vez, o OK do painel de tarefas: se o arredondamento só fecha em duas etapas, prepara antes
    de o FreeCAD aceitar (assim o OK não dá erro) e cria a segunda etapa quando o painel fecha."""
    try:
        import PrumoTrocarOperacao
        ok = PrumoTrocarOperacao._botao_ok()
    except Exception:
        ok = None
    if ok is None or ok.property("prumo_etapas"):
        return
    ok.setProperty("prumo_etapas", True)
    nome_doc, nome = obj.Document.Name, obj.Name

    def antes():
        doc = FreeCAD.getDocument(nome_doc) if nome_doc in FreeCAD.listDocuments() else None
        o = doc.getObject(nome) if doc else None
        _dbg("OK pressionado em %s" % nome)
        if o is None or plano(o) is None:
            _dbg("sem plano")
            return
        _pendente[(nome_doc, nome)] = True
        p = plano(o)
        primeiro_idx, _ = p
        base = o.Base[0]
        o.Base = (base, ["Edge%d" % i for i in primeiro_idx])  # o OK agora recalcula sem erro
        o.Document.recompute()   # já sai do estado de erro da prévia antes do FreeCAD conferir
        _dbg("base agora %s" % (o.Base[1],))
        _segunda_depois(nome_doc, nome, p)

    ok.pressed.connect(antes)


_pendente = {}


def _dbg(t):
    import os
    c = os.environ.get("PRUMO_DBG_ETAPAS")
    if c:
        open(c, "a").write(t + "\n")


def _segunda_depois(nome_doc, nome, p):
    from PySide import QtCore
    import FreeCADGui

    def tentar(n=[0]):
        n[0] += 1
        try:
            gd = FreeCADGui.getDocument(nome_doc)
            if gd.getInEdit() is not None and n[0] < 50:
                QtCore.QTimer.singleShot(100, tentar)
                return
        except Exception:
            return
        _pendente.pop((nome_doc, nome), None)
        doc = FreeCAD.getDocument(nome_doc)
        o = doc.getObject(nome)
        if o is None:
            return
        _criar_segunda(o, p[1])
    QtCore.QTimer.singleShot(100, tentar)


def _criar_segunda(obj, segundo):
    doc = obj.Document
    doc.openTransaction("Arredondar (2ª etapa)")
    try:
        doc.recompute()
        nomes_b = [_nome_no(obj.Shape, e) for e in segundo]
        if None in nomes_b:
            return
        body = next((o for o in obj.InList if o.TypeId == "PartDesign::Body"), None)
        f2 = doc.addObject("PartDesign::Fillet", "Fillet")
        if body is not None:
            body.insertObject(f2, obj, True)
        f2.Base = (obj, nomes_b)
        f2.Radius = obj.Radius
        if hasattr(obj, "Refine"):
            f2.Refine = obj.Refine
        f2.Label = obj.Label + " (2ª etapa)"
        if body is not None and body.Tip == obj:
            body.Tip = f2
        try:
            obj.ViewObject.Visibility = False
            f2.ViewObject.Visibility = True
        except Exception:
            pass
        doc.recompute()
        FreeCAD.Console.PrintMessage(_AVISO + "\n")
    finally:
        doc.commitTransaction()
