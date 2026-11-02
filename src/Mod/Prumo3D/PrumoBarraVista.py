# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: barra de vistas flutuante, pequena, embaixo da vista 3D (como a barra "heads-up" dos outros CAD).

Fica centralizada na parte de baixo de cada vista 3D, por cima do modelo: enquadrar, vistas padrão (com as
demais num menu), estilo de exibição, plano de corte e sombras. Pode ser desligada em Preferências do Prumo
(parâmetro BarraVista).
"""
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
NOME = "PrumoBarraVista"
MARGEM = 10

# (comando, dica) ; "|" separa grupos ; ("menu", rótulo, ícone, [comandos]) abre um menu
ITENS = [
    ("Std_ViewFitAll", "Enquadrar tudo"),
    ("Std_ViewFitSelection", "Enquadrar seleção"),
    "|",
    ("Std_ViewIsometric", "Isométrica"),
    ("Std_ViewFront", "Frontal"),
    ("Std_ViewTop", "Superior"),
    ("Std_ViewRight", "Direita"),
    ("menu", "Outras vistas", "Std_ViewRear",
     [("Std_ViewRear", "Traseira"), ("Std_ViewBottom", "Inferior"), ("Std_ViewLeft", "Esquerda"),
      ("Std_AlignToSelection", "Alinhar à seleção")]),
    "|",
    ("Std_DrawStyle", "Estilo de exibição"),
    ("Std_ToggleClipPlane", "Plano de corte"),
    ("Prumo_Sombras", "Sombras"),
]

QSS = """
QFrame#PrumoBarraVista { background: rgba(255,255,255,235); border: 1px solid #C9D3DE; border-radius: 9px; }
QFrame#PrumoBarraVista QToolButton { border: none; border-radius: 6px; padding: 2px; background: transparent; }
QFrame#PrumoBarraVista QToolButton:hover { background: #E6EEF7; }
QFrame#PrumoBarraVista QToolButton:checked { background: #FDEBB0; }
QFrame#PrumoBarraVista QToolButton::menu-indicator { image: none; width: 0; }
QFrame#PrumoBarraVista QFrame#PrumoBarraVistaSep { background: #D5DEE8; }
"""
QSS_ESCURO = """
QFrame#PrumoBarraVista { background: rgba(38,44,52,235); border: 1px solid #3A4450; border-radius: 9px; }
QFrame#PrumoBarraVista QToolButton { border: none; border-radius: 6px; padding: 2px; background: transparent; }
QFrame#PrumoBarraVista QToolButton:hover { background: #33404D; }
QFrame#PrumoBarraVista QToolButton:checked { background: #5A4A12; }
QFrame#PrumoBarraVista QToolButton::menu-indicator { image: none; width: 0; }
QFrame#PrumoBarraVista QFrame#PrumoBarraVistaSep { background: #3A4450; }
"""


def ligada():
    return FreeCAD.ParamGet(PARAM).GetBool("BarraVista", True)


def _escuro():
    try:
        import PrumoEstilo
        return PrumoEstilo.escuro()
    except Exception:
        return False


def _acao(nome):
    try:
        import PrumoRibbon
        acts = PrumoRibbon._cmd_actions(nome)
        return acts[0] if acts else None
    except Exception:
        return None


def _icone(nome):
    a = _acao(nome)
    if a is not None and not a.icon().isNull():
        return a.icon()
    try:
        return FreeCADGui.getIcon(nome)
    except Exception:
        return QtGui.QIcon()


class BarraVista(QtWidgets.QFrame):
    def __init__(self, vista_qt, parent):
        super().__init__(parent)
        self.setObjectName(NOME)
        self.setStyleSheet(QSS_ESCURO if _escuro() else QSS)
        self._alvo = vista_qt
        hl = QtWidgets.QHBoxLayout(self)
        hl.setContentsMargins(5, 3, 5, 3)
        hl.setSpacing(1)
        self.botoes = {}
        for it in ITENS:
            if it == "|":
                sep = QtWidgets.QFrame(self)
                sep.setObjectName("PrumoBarraVistaSep")
                sep.setFixedSize(1, 18)
                hl.addSpacing(3)
                hl.addWidget(sep)
                hl.addSpacing(3)
                continue
            if it[0] == "menu":
                _m, rotulo, icone, filhos = it
                b = self._botao(icone, rotulo)
                menu = QtWidgets.QMenu(b)
                for nome, dica in filhos:
                    act = menu.addAction(_icone(nome), dica)
                    act.triggered.connect(lambda _c=False, n=nome: self._rodar(n))
                b.setMenu(menu)
                b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
                b.setIcon(_icone(icone))
                hl.addWidget(b)
                self.botoes["menu:" + rotulo] = b
                continue
            nome, dica = it
            if nome == "Prumo_Sombras":
                b = self._botao(nome, dica)
                b.setCheckable(True)
                try:
                    import PrumoSombras
                    b.setChecked(PrumoSombras.ligado())
                except Exception:
                    pass
                b.toggled.connect(self._sombras)
            else:
                a = _acao(nome)
                b = self._botao(nome, dica)
                if a is not None and a.menu() is not None:
                    # comando de grupo (Estilo de exibição): o menu dele abre no clique
                    b.setMenu(a.menu())
                    b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
                else:
                    b.clicked.connect(lambda _c=False, n=nome: self._rodar(n))
            hl.addWidget(b)
            self.botoes[nome] = b
        self.adjustSize()
        vista_qt.installEventFilter(self)
        self.reposicionar()
        self.raise_()
        self.show()

    def _botao(self, nome, dica):
        b = QtWidgets.QToolButton(self)
        b.setIcon(_icone(nome))
        b.setIconSize(QtCore.QSize(18, 18))
        b.setFixedSize(26, 26)
        b.setToolTip(dica)
        b.setAutoRaise(True)
        b.setFocusPolicy(QtCore.Qt.NoFocus)
        return b

    def _rodar(self, nome):
        try:
            FreeCADGui.runCommand(nome, 0)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: %s: %s\n" % (nome, exc))

    def _sombras(self, marcado):
        try:
            import PrumoSombras
            if PrumoSombras.ligado() != bool(marcado):
                PrumoSombras.definir(bool(marcado))
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: sombras: %s\n" % exc)

    def atualizar(self):
        b = self.botoes.get("Prumo_Sombras")
        if b is not None:
            try:
                import PrumoSombras
                b.blockSignals(True)
                b.setChecked(PrumoSombras.ligado())
                b.blockSignals(False)
            except Exception:
                pass

    def reposicionar(self):
        p = self.parentWidget()
        if p is None:
            return
        self.adjustSize()
        x = max(0, (p.width() - self.width()) // 2)
        y = max(0, p.height() - self.height() - MARGEM)
        self.move(x, y)
        self.raise_()

    def eventFilter(self, obj, ev):
        if ev.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
            QtCore.QTimer.singleShot(0, self.reposicionar)
        return False


def _vistas_qt():
    """(widget onde a barra flutua) de cada vista 3D aberta."""
    mw = FreeCADGui.getMainWindow()
    alvos = []
    for w in mw.findChildren(QtWidgets.QGraphicsView):
        if w.metaObject().className() in ("Gui::View3DInventorViewer",) or w.inherits("SIM::Coin3D::Quarter::QuarterWidget"):
            alvos.append(w)
    return alvos


def instalar_nas_vistas():
    """Põe a barra em toda vista 3D que ainda não tem (ou tira, se estiver desligada)."""
    n = 0
    for gv in _vistas_qt():
        barra = gv.findChild(QtWidgets.QFrame, NOME)
        if not ligada():
            if barra is not None:
                barra.deleteLater()
            continue
        if barra is None:
            BarraVista(gv, gv)
            n += 1
        else:
            barra.atualizar()
            barra.reposicionar()
    return n


_ESTADO = {"timer": None}


def instalar():
    """Liga a barra: vistas abertas agora e as que forem abertas depois."""
    if _ESTADO["timer"] is not None:
        return
    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtWidgets.QMdiArea)
    if mdi is not None:
        mdi.subWindowActivated.connect(lambda *_a: QtCore.QTimer.singleShot(0, instalar_nas_vistas))
    t = QtCore.QTimer(mw)
    t.setInterval(1500)        # rede de segurança: vista dividida, nova janela, troca de tema
    t.timeout.connect(instalar_nas_vistas)
    t.start()
    _ESTADO["timer"] = t
    QtCore.QTimer.singleShot(0, instalar_nas_vistas)
