# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: tecla S abre a caixa de ferramentas no cursor (como a barra S do SolidWorks e a do Fusion/Onshape).

Com o mouse na vista 3D, S abre, onde está o cursor, as ferramentas principais da aba atual e uma linha de
busca no topo (digitar procura em todas as ferramentas, como o Ctrl+K). Enter ou clique roda.

Não vale dentro de um esboço ou de outra edição (lá o S é a relação Simétrica do esboço) nem na aba
Simulação (atalhos "S, ..." das simulações). Pode ser desligada em Preferências do Usinix.
"""
import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
MAX_ITENS = 14
_ESTADO = {"filtro": None, "caixa": None}


def ligada():
    return FreeCAD.ParamGet(PARAM).GetBool("CaixaS", True)


def _em_vista_3d(w):
    while w is not None:
        try:
            if w.inherits("SIM::Coin3D::Quarter::QuarterWidget") or \
                    w.metaObject().className() == "Gui::View3DInventorViewer":
                return True
        except Exception:
            return False
        w = w.parentWidget()
    return False


def pode_abrir():
    if not ligada():
        return False
    try:
        gd = FreeCADGui.ActiveDocument
        if gd is not None and gd.getInEdit() is not None:
            return False                      # esboço/edição: S é dos atalhos de lá
    except Exception:
        pass
    try:
        if FreeCADGui.activeWorkbench().name() == "FemWorkbench":
            return False
    except Exception:
        pass
    return _em_vista_3d(QtWidgets.QApplication.focusWidget()) or _em_vista_3d(
        QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos()))


def itens_da_aba():
    """Ferramentas principais da aba atual (botões grandes primeiro), no formato do índice da busca."""
    import PrumoRibbon
    import PrumoBuscaComandos as B
    rb = PrumoRibbon._state.get("ribbon")
    if rb is None:
        return []
    try:
        aba = rb._tabs[rb.tabbar.currentIndex()]
    except Exception:
        return []
    por_cmd = {it[0]: it for it in B.indice()}
    grandes, pequenos = [], []
    for _grupo, itens in aba.get("panels", []):
        for item in itens:
            cmd, tam = item[0], item[1]
            it = por_cmd.get(cmd)
            if it is None:
                continue
            (grandes if tam == PrumoRibbon.L else pequenos).append(it)
    res = []
    for it in grandes + pequenos:
        if it not in res:
            res.append(it)
    return res[:MAX_ITENS]


def abrir(ponto=None):
    import PrumoBuscaComandos as B
    import PrumoRibbon
    rb = PrumoRibbon._state.get("ribbon")
    caixa = _ESTADO.get("caixa")
    try:
        import shiboken6
        if caixa is not None and not shiboken6.isValid(caixa):
            caixa = None
    except Exception:
        pass
    if caixa is None:
        caixa = B.BuscaComandos(rb, FreeCADGui.getMainWindow())
        caixa.setObjectName("PrumoBusca")
        _ESTADO["caixa"] = caixa
    caixa._itens = None                      # aba ou bancada podem ter mudado
    caixa.abrir(ponto=ponto or QtGui.QCursor.pos(), padrao=itens_da_aba())
    return caixa


class _Filtro(QtCore.QObject):
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t not in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
            return False
        try:
            if ev.key() != QtCore.Qt.Key_S or ev.isAutoRepeat() or \
                    (ev.modifiers() & ~QtCore.Qt.KeypadModifier) != QtCore.Qt.NoModifier:
                return False
            if not isinstance(obj, QtWidgets.QWidget) or obj is not QtWidgets.QApplication.focusWidget():
                return False
            if not pode_abrir():
                return False
        except Exception:
            return False
        if t == QtCore.QEvent.ShortcutOverride:
            ev.accept()                        # o S fica com a vista (não vira começo de "S, B" etc.)
            return True
        QtCore.QTimer.singleShot(0, abrir)
        return True


def instalar():
    if _ESTADO["filtro"] is not None:
        return
    app = QtWidgets.QApplication.instance()
    f = _Filtro(app)
    app.installEventFilter(f)
    _ESTADO["filtro"] = f
