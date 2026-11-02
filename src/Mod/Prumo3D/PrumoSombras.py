# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: sombras na vista 3D (marca e desmarca na aba Início › Vista; vem desmarcado).

Usa o ShadowGroup do Coin3D (o pivy não traz a classe, então o nó é lido de um texto Inventor, como faz o
BIM em OfflineRenderingUtils.embedLight). O grupo dos objetos da vista ("ObjectGroup") passa a ficar dentro
de um ShadowGroup com uma luz de sombra vinda de cima e um piso que só recebe sombra, logo abaixo do modelo.
Desligar devolve o grupo dos objetos ao lugar original. A luz é fixa em relação ao modelo (sol ao alto, à
frente e à esquerda), então a sombra não "anda" ao girar a vista.
"""
import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
NOME_GRUPO = "PrumoSombras"
DIRECAO_LUZ = (0.35, 0.45, -1.0)   # de cima, um pouco da frente e da esquerda

TEXTO = """#Inventor V2.1 ascii
ShadowGroup {
    isActive TRUE
    quality 1
    precision 0.6
    smoothBorder 0.3
    ShadowStyle { style NO_SHADOWING }
    ShadowDirectionalLight {
        direction %g %g %g
        intensity 0.55
    }
    ShadowStyle { style CASTS_SHADOW_AND_SHADOWED }
}
"""

TEXTO_PISO = """#Inventor V2.1 ascii
Separator {
    ShadowStyle { style SHADOWED }
    PickStyle { style UNPICKABLE }
    Material { diffuseColor 1 1 1 transparency 0.999 }
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


def _raiz(view):
    return view.getViewer().getSceneGraph()


def _grupo_sombra(view):
    raiz = _raiz(view)
    _i, g = _filhos_por_nome(raiz, NOME_GRUPO)
    return g


def _ajustar_piso(view, grupo=None):
    """Piso que só recebe sombra: um quadrado sob o modelo, 3x o tamanho dele, um pouco abaixo do fundo."""
    from pivy import coin
    grupo = grupo or _grupo_sombra(view)
    if grupo is None:
        return
    _i, piso = _filhos_por_nome(grupo, NOME_GRUPO + "Piso")
    if piso is None:
        return
    _i, objetos = _filhos_por_nome(grupo, "ObjectGroup")
    if objetos is None:
        return
    vp = coin.SbViewportRegion()
    acao = coin.SoGetBoundingBoxAction(vp)
    acao.apply(objetos)
    caixa = acao.getBoundingBox()
    tr = None
    for i in range(piso.getNumChildren()):
        if piso.getChild(i).isOfType(coin.SoTransform.getClassTypeId()):
            tr = piso.getChild(i)
    if caixa.isEmpty() or tr is None:
        return
    mn, mx = caixa.getMin().getValue(), caixa.getMax().getValue()
    cx, cy = (mn[0] + mx[0]) / 2.0, (mn[1] + mx[1]) / 2.0
    tam = max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2], 1.0)
    folga = max(tam * 0.002, 0.01)
    tr.translation.setValue(cx, cy, mn[2] - folga)
    tr.scaleFactor.setValue(tam * 1.5, tam * 1.5, 1.0)


def ligar_na_vista(view):
    """Põe a vista com sombras. Devolve True se ficou ligada."""
    from pivy import coin
    raiz = _raiz(view)
    if _grupo_sombra(view) is not None:
        _ajustar_piso(view)
        return True
    i, objetos = _filhos_por_nome(raiz, "ObjectGroup")
    if objetos is None:
        return False
    d = DIRECAO_LUZ
    grupo = _ler(TEXTO % d)
    if grupo.getTypeId().getName().getString() != "ShadowGroup":
        return False
    grupo.setName(NOME_GRUPO)
    piso = _ler(TEXTO_PISO)
    piso.setName(NOME_GRUPO + "Piso")
    grupo.addChild(piso)
    objetos.ref()
    raiz.replaceChild(i, grupo)
    grupo.addChild(objetos)
    objetos.unref()
    _ajustar_piso(view, grupo)
    return True


def desligar_na_vista(view):
    raiz = _raiz(view)
    i, grupo = _filhos_por_nome(raiz, NOME_GRUPO)
    if grupo is None:
        return
    _j, objetos = _filhos_por_nome(grupo, "ObjectGroup")
    if objetos is None:
        raiz.removeChild(i)
        return
    objetos.ref()
    grupo.removeChild(objetos)
    raiz.replaceChild(i, objetos)
    objetos.unref()


def _vistas_3d():
    import FreeCADGui
    vistas = []
    for nome in list(FreeCAD.listDocuments()):
        try:
            gd = FreeCADGui.getDocument(nome)
        except Exception:
            continue
        for v in (gd.mdiViewsOfType("Gui::View3DInventor") if gd else []):
            vistas.append(v)
    return vistas


def aplicar(ligar=None):
    """Liga ou desliga as sombras em todas as vistas 3D abertas (ligar=None segue a preferência)."""
    ligar = ligado() if ligar is None else ligar
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


def _observar(sim):
    global _OBS
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
