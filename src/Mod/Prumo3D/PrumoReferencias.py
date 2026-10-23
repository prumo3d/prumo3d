# SPDX-License-Identifier: LGPL-2.1-or-later
"""Referências automáticas no esboço (geometria externa por padrão).

No FreeCAD, para desenhar em cima das arestas do modelo é preciso chamar "Geometria externa" e clicar
aresta por aresta. Aqui isso é automático:

- ao abrir um esboço apoiado numa FACE, todas as arestas dessa face entram como geometria externa;
- ao abrir um esboço apoiado num PLANO (da origem ou de referência), entram as arestas do sólido do
  Corpo que estão nesse plano;
- ao concluir o esboço, as referências automáticas que não foram usadas em nenhuma restrição saem,
  para o esboço não ficar preso a arestas que ele não usa (menos quebra quando o modelo muda).

As referências adicionadas à mão (ferramenta Geometria externa) nunca são removidas. Liga e desliga em
Esboço → "Referências automáticas" (parâmetro ReferenciasAutomaticas).
"""
import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
MAX_ARESTAS = 80        # acima disso (face muito recortada, peça grande) não adiciona sozinho
TOL = 1e-4


def ligado():
    return FreeCAD.ParamGet(PARAM).GetBool("ReferenciasAutomaticas", True)


def _externas(sk):
    """[(objeto, subelemento)] na ordem dos índices da geometria externa."""
    res = []
    for o, subs in sk.ExternalGeometry:
        if isinstance(subs, str):
            subs = [subs]
        for s in subs:
            res.append((o, s))
    return res


def _marcar(sk):
    if "ReferenciasAuto" not in sk.PropertiesList:
        sk.addProperty("App::PropertyStringList", "ReferenciasAuto", "Prumo",
                       "Geometria externa que o Prumo pôs sozinho (sai ao concluir se não for usada)")
        sk.setEditorMode("ReferenciasAuto", 2)


def _indice_da_aresta(shape, aresta):
    for i, e in enumerate(shape.Edges):
        if e.isSame(aresta):
            return i + 1
    return None


def _corpo(sk):
    for p in sk.InList:
        if p.isDerivedFrom("PartDesign::Body"):
            return p
    return None


def _solido_anterior(sk, corpo):
    """Sólido do Corpo antes deste esboço: a ponta, se o esboço não é ela."""
    tip = corpo.Tip if corpo is not None else None
    if tip is None or tip is sk or not hasattr(tip, "Shape") or tip.Shape.isNull():
        return None
    return tip


def candidatas(sk):
    """[(objeto, 'EdgeN')] que o esboço deve receber como referência."""
    sup = getattr(sk, "AttachmentSupport", None) or []
    res = []
    for o, subs in sup:
        if isinstance(subs, str):
            subs = [subs]
        for s in subs:
            if s.startswith("Face") and hasattr(o, "Shape"):
                try:
                    face = o.Shape.getElement(s)
                except Exception:
                    continue
                for e in face.Edges:
                    k = _indice_da_aresta(o.Shape, e)
                    if k is not None:
                        res.append((o, "Edge%d" % k))
    if res:
        return res
    # apoiado num plano: arestas do sólido que estão no plano do esboço
    corpo = _corpo(sk)
    alvo = _solido_anterior(sk, corpo)
    if alvo is None:
        return []
    try:
        pl = sk.getGlobalPlacement()
    except Exception:
        pl = sk.Placement
    n = pl.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    p0 = pl.Base
    try:
        shape = alvo.Shape
        glob = alvo.getGlobalPlacement() if hasattr(alvo, "getGlobalPlacement") else alvo.Placement
        loc = glob.multiply(alvo.Placement.inverse())
    except Exception:
        return []
    for i, e in enumerate(shape.Edges):
        try:
            pts = [loc.multVec(v.Point) for v in e.Vertexes]
            pts.append(loc.multVec(e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)))
        except Exception:
            continue
        if all(abs((q - p0).dot(n)) < TOL for q in pts):
            res.append((alvo, "Edge%d" % (i + 1)))
    return res


def ao_entrar(sk):
    """Põe as referências automáticas. Retorna quantas entraram."""
    if not ligado() or sk is None or sk.TypeId != "Sketcher::SketchObject":
        return 0
    try:
        cand = candidatas(sk)
    except Exception as ex:
        FreeCAD.Console.PrintLog("Prumo: referências automáticas: %s\n" % ex)
        return 0
    if not cand or len(cand) > MAX_ARESTAS:
        return 0
    ja = {(o.Name, s) for o, s in _externas(sk)}
    _marcar(sk)
    auto = list(sk.ReferenciasAuto)
    novas = 0
    for o, s in cand:
        if (o.Name, s) in ja:
            continue
        try:
            sk.addExternal(o.Name, s)
        except Exception:
            continue
        auto.append("%s.%s" % (o.Name, s))
        novas += 1
    if novas:
        sk.ReferenciasAuto = auto
        sk.Document.recompute()
    return novas


def usadas(sk):
    """Índices da geometria externa usados em restrições."""
    ids = set()
    for c in sk.Constraints:
        for g in (c.First, c.Second, c.Third):
            if g is not None and g <= -3:
                ids.add(-3 - g)
    return ids


def ao_sair(sk):
    """Tira as referências automáticas não usadas. Retorna quantas saíram."""
    if sk is None or "ReferenciasAuto" not in sk.PropertiesList or not sk.ReferenciasAuto:
        return 0
    auto = set(sk.ReferenciasAuto)
    uso = usadas(sk)
    remover = [k for k, (o, s) in enumerate(_externas(sk)) if "%s.%s" % (o.Name, s) in auto and k not in uso]
    for k in sorted(remover, reverse=True):
        try:
            sk.delExternal(k)
        except Exception as ex:
            FreeCAD.Console.PrintLog("Prumo: tirar referência %d: %s\n" % (k, ex))
    ficam = {"%s.%s" % (o.Name, s) for o, s in _externas(sk)}
    sk.ReferenciasAuto = [x for x in sk.ReferenciasAuto if x in ficam]
    if remover:
        sk.Document.recompute()
    return len(remover)


if FreeCAD.GuiUp:
    import FreeCADGui

    class CmdReferenciasAuto:
        def GetResources(self):
            return {"Pixmap": "Sketcher_External", "MenuText": "Referências automáticas",
                    "ToolTip": "Liga ou desliga a geometria externa automática: ao abrir o esboço, as arestas da "
                               "face de apoio (ou do sólido no plano do esboço) já entram como referência; as "
                               "não usadas saem ao concluir.",
                    "Checkable": ligado()}

        def IsActive(self):
            return True

        def Activated(self, marcado=None):
            g = FreeCAD.ParamGet(PARAM)
            novo = bool(marcado) if marcado is not None else not ligado()
            g.SetBool("ReferenciasAutomaticas", novo)
            if novo:
                try:
                    vp = FreeCADGui.ActiveDocument.getInEdit()
                    if vp is not None:
                        ao_entrar(vp.Object)
                except Exception:
                    pass
