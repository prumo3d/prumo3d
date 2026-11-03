# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: sombras na vista 3D (marca e desmarca na aba Início › Vista; vem desmarcado).

Usa o ShadowGroup do Coin3D (o pivy não traz a classe, então o nó é lido de um texto Inventor, como faz o
BIM em OfflineRenderingUtils.embedLight). A raiz dos objetos da vista (a mesma em que o FreeCAD põe e
tira as peças) passa a ficar dentro de um ShadowGroup com uma luz de sombra vinda de cima e um piso discreto
logo abaixo do modelo, que recebe a sombra. Desligar devolve a raiz ao lugar original. A luz é fixa em relação
ao modelo (sol ao alto, à frente e à esquerda), então a sombra não "anda" ao girar a vista.

As peças só projetam sombra (no piso); não recebem sombra nelas mesmas. A sombra sobre a própria peça, em
placas de vídeo reais, saía em manchas e faixas ("acne" do mapa de sombra) e não acrescenta nada: as faces
já ficam mais claras ou escuras pela luz normal da vista.
"""
import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
NOME_GRUPO = "PrumoSombras"
DIRECAO_LUZ = (0.35, 0.45, -1.0)   # de cima, um pouco da frente e da esquerda: a sombra cai à frente, à vista

TEXTO = """#Inventor V2.1 ascii
ShadowGroup {
    isActive TRUE
    quality 1
    precision 1
    smoothBorder 0.3
    ShadowStyle { style NO_SHADOWING }
    ShadowDirectionalLight {
        direction %g %g %g
        intensity 0.3
    }
    ShadowStyle { style CASTS_SHADOW }
}
"""

TEXTO_PISO = """#Inventor V2.1 ascii
Separator {
    ShadowStyle { style SHADOWED }
    PickStyle { style UNPICKABLE }
    Material { diffuseColor 0.78 0.80 0.83 transparency 0.35 }
    Transform { translation 0 0 0 scaleFactor 1 1 1 }
    Coordinate3 { point [ -1 -1 0, 1 -1 0, 1 1 0, -1 1 0 ] }
    Normal { vector [ 0 0 1 ] }
    NormalBinding { value OVERALL }
    FaceSet { numVertices 4 }
}
"""


def ligado():
    return FreeCAD.ParamGet(PARAM).GetBool("Sombras", False)


def _ler(texto):
    from pivy import coin
    inp = coin.SoInput()
    inp.setBuffer(texto)
    no = coin.SoDB.readAll(inp)
    if no is None:
        raise RuntimeError("Coin sem suporte a sombras (ShadowGroup)")
    # readAll devolve um Separator que embrulha o que foi lido: fica com o nó de dentro
    if no.getNumChildren() == 1 and no.getTypeId().getName().getString() == "Separator":
        filho = no.getChild(0)
        filho.ref()          # o Separator de fora some; o nó de dentro fica vivo
        no.removeAllChildren()
        no = filho
    return no


def _filhos_por_nome(no, nome):
    for i in range(no.getNumChildren()):
        f = no.getChild(i)
        if f.getName().getString() == nome:
            return i, f
    return -1, None


def _no_da_vista(view):
    """Nó raiz dos objetos da vista (SoFCUnifiedSelection): o FreeCAD põe e tira as peças nele."""
    return view.getViewer().getSceneGraph()


def _pai(view, no):
    """(pai, índice) do nó dentro da cena completa da vista (com câmera e luzes)."""
    from pivy import coin
    cena = view.getViewer().getSoRenderManager().getSceneGraph()
    busca = coin.SoSearchAction()
    busca.setNode(no)
    busca.setInterest(coin.SoSearchAction.FIRST)
    busca.setSearchingAll(True)
    busca.apply(cena)
    caminho = busca.getPath()
    if caminho is None or caminho.getLength() < 2:
        return None, -1
    pai = caminho.getNodeFromTail(1)
    return pai, caminho.getIndexFromTail(0)


def _grupo_sombra(view):
    """O ShadowGroup do Prumo, se a vista estiver com sombras."""
    pai, _i = _pai(view, _no_da_vista(view))
    if pai is not None and pai.getName().getString() == NOME_GRUPO:
        return pai
    return None


def _ajustar_piso(view, grupo=None):
    """Piso que só recebe sombra: um quadrado sob o modelo, 3x o tamanho dele, um pouco abaixo do fundo."""
    from pivy import coin
    grupo = grupo or _grupo_sombra(view)
    if grupo is None:
        return
    _i, piso = _filhos_por_nome(grupo, NOME_GRUPO + "Piso")
    if piso is None:
        return
    caixa = None
    try:
        doc = getattr(view, "_prumo_doc", None) or FreeCAD.ActiveDocument
        bb = FreeCAD.BoundBox()
        for o in (doc.Objects if doc else []):
            vo = getattr(o, "ViewObject", None)
            if vo is None or not vo.Visibility or not _conta_para_o_piso(o):
                continue
            try:
                sbb = o.Shape.BoundBox
                if sbb.isValid() and sbb.DiagonalLength < 1e9:
                    bb.add(sbb)
            except Exception:
                pass
        if bb.isValid():
            caixa = (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)
    except Exception:
        caixa = None
    tr = None
    for i in range(piso.getNumChildren()):
        if piso.getChild(i).isOfType(coin.SoTransform.getClassTypeId()):
            tr = piso.getChild(i)
    if tr is None:
        return
    if caixa is None:                      # nenhum sólido à vista: sem piso
        tr.scaleFactor.setValue(1e-6, 1e-6, 1.0)
        return
    x0, y0, z0, x1, y1, z1 = caixa
    tam = max(x1 - x0, y1 - y0, z1 - z0, 1.0)
    folga = max(tam * 0.002, 0.01)
    tr.translation.setValue((x0 + x1) / 2.0, (y0 + y1) / 2.0, z0 - folga)
    tr.scaleFactor.setValue(tam * 1.5, tam * 1.5, 1.0)


DATUMS = ("App::Origin", "App::Line", "App::Plane", "App::Point", "PartDesign::Plane", "PartDesign::Line",
          "PartDesign::Point", "PartDesign::CoordinateSystem", "Sketcher::SketchObject")


def _conta_para_o_piso(o):
    """Só sólidos de verdade definem o piso: planos, eixos e esboços (que aparecem ao criar um esboço) não."""
    if o.TypeId.startswith(DATUMS) or getattr(getattr(o, "Proxy", None), "__class__", None).__name__ == "LinhaGuia":
        return False
    sh = getattr(o, "Shape", None)
    return sh is not None and not sh.isNull() and bool(sh.Solids)


def em_edicao():
    """Esboço, operação ou painel aberto: as sombras saem enquanto isso (planos, eixos e textos de cota
    temporários apareciam duplicados e faziam sombra)."""
    try:
        import FreeCADGui
        for nome in FreeCAD.listDocuments():
            gd = FreeCADGui.getDocument(nome)
            if gd is not None and gd.getInEdit() is not None:
                return True
        return bool(FreeCADGui.Control.activeDialog())
    except Exception:
        return False


def ligar_na_vista(view):
    """Põe a vista com sombras: a raiz dos objetos passa a ficar dentro de um ShadowGroup (com a luz de sombra
    e o piso). O FreeCAD continua pondo e tirando peças na mesma raiz. Devolve True se ficou ligada."""
    if _grupo_sombra(view) is not None:
        _ajustar_piso(view)
        return True
    raiz = _no_da_vista(view)
    pai, i = _pai(view, raiz)
    if pai is None:
        return False
    grupo = _ler(TEXTO % DIRECAO_LUZ)
    if grupo.getTypeId().getName().getString() != "ShadowGroup":
        return False
    grupo.setName(NOME_GRUPO)
    piso = _ler(TEXTO_PISO)
    piso.setName(NOME_GRUPO + "Piso")
    grupo.addChild(piso)
    raiz.ref()
    pai.replaceChild(i, grupo)
    grupo.addChild(raiz)
    raiz.unref()
    _ajustar_piso(view, grupo)
    return True


def desligar_na_vista(view):
    grupo = _grupo_sombra(view)
    if grupo is None:
        return
    pai, i = _pai(view, grupo)
    if pai is None:
        return
    raiz = _no_da_vista(view)
    raiz.ref()
    grupo.removeChild(raiz)
    pai.replaceChild(i, raiz)
    raiz.unref()


def _vistas_3d():
    import FreeCADGui
    vistas = []
    for nome in list(FreeCAD.listDocuments()):
        try:
            gd = FreeCADGui.getDocument(nome)
        except Exception:
            continue
        for v in (gd.mdiViewsOfType("Gui::View3DInventor") if gd else []):
            try:
                v._prumo_doc = gd.Document
            except Exception:
                pass
            vistas.append(v)
    return vistas


def aplicar(ligar=None):
    """Liga ou desliga as sombras em todas as vistas 3D abertas (ligar=None segue a preferência)."""
    ligar = ligado() if ligar is None else ligar
    if ligar and em_edicao():
        ligar = False                # volta sozinha quando a edição acabar (vigia abaixo)
    n = 0
    for v in _vistas_3d():
        try:
            if ligar:
                n += bool(ligar_na_vista(v))
            else:
                desligar_na_vista(v)
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: sombras: %s\n" % exc)
    return n


def definir(ligar):
    FreeCAD.ParamGet(PARAM).SetBool("Sombras", bool(ligar))
    _observar(bool(ligar))
    return aplicar(bool(ligar))


class _Observador:
    """Com sombras ligadas: novas vistas ganham sombra e o piso acompanha o modelo depois de recalcular."""

    def slotRecomputedDocument(self, doc):
        _depois(aplicar)

    def slotCreatedDocument(self, doc):
        _depois(aplicar)

    def slotActivateDocument(self, doc):
        _depois(aplicar)


_OBS = None


def _depois(f):
    try:
        from PySide import QtCore
        QtCore.QTimer.singleShot(0, lambda: f())
    except Exception:
        pass


_VIGIA = {"t": None, "edicao": None}


def _vigiar_edicao(sim):
    """Com sombras ligadas: tira enquanto há edição/painel aberto e põe de volta quando fecha."""
    try:
        from PySide import QtCore, QtWidgets
    except Exception:
        return
    t = _VIGIA["t"]
    if sim and t is None:
        t = QtCore.QTimer(QtWidgets.QApplication.instance())
        t.setInterval(400)

        def tick():
            e = em_edicao()
            if e != _VIGIA["edicao"]:
                _VIGIA["edicao"] = e
                aplicar()
        t.timeout.connect(tick)
        t.start()
        _VIGIA["t"] = t
    elif not sim and t is not None:
        t.stop()
        _VIGIA["t"] = None
        _VIGIA["edicao"] = None


def _observar(sim):
    global _OBS
    _vigiar_edicao(sim)
    if sim and _OBS is None:
        _OBS = _Observador()
        FreeCAD.addDocumentObserver(_OBS)
    elif not sim and _OBS is not None:
        try:
            FreeCAD.removeDocumentObserver(_OBS)
        except Exception:
            pass
        _OBS = None


if FreeCAD.GuiUp:
    import FreeCADGui

    class CmdSombras:
        def GetResources(self):
            import os
            icone = os.path.join(os.path.dirname(__file__), "Resources", "icons", "sombras.svg")
            return {"Pixmap": icone, "MenuText": "Sombras",
                    "ToolTip": "Mostra a sombra das peças na vista 3D: sobre o piso e de uma peça na outra. "
                               "Marque para ligar e desmarque para desligar. Em placas de vídeo fracas ou "
                               "montagens muito grandes pode deixar a vista mais lenta.",
                    "Checkable": ligado()}

        def IsActive(self):
            return True

        def Activated(self, marcado=None):
            novo = bool(marcado) if marcado is not None else not ligado()
            definir(novo)


def registrar_comandos():
    if FreeCAD.GuiUp:
        FreeCADGui.addCommand("Prumo_Sombras", CmdSombras())
        if ligado():
            _observar(True)
            _depois(aplicar)
