# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: "você vem de qual programa?" — o mouse da vista 3D igual ao do CAD que a pessoa já usa.

Girar, arrastar e aproximar a vista é o que mais trava quem chega de outro programa, e o ajuste fica escondido
nas preferências do FreeCAD com nomes que ninguém reconhece ("Revit", "TinkerCAD"). Aqui a escolha é pelo
nome do programa de origem: na tela inicial (até a primeira escolha) e sempre em Preferências do Prumo.

Os estilos são os do próprio FreeCAD; a descrição de cada um vem dos botões que o estilo usa
(src/Gui/Navigation/*NavigationStyle.cpp).
"""
import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
VISTA = "User parameter:BaseApp/Preferences/View"

# (id, nome mostrado, estilo do FreeCAD, girar, arrastar)
PROGRAMAS = [
    ("solidworks", "SolidWorks", "Gui::SolidWorksNavigationStyle",
     "botão do meio", "Ctrl + botão do meio"),
    ("autodesk", "Inventor / Fusion", "Gui::RevitNavigationStyle",
     "Shift + botão do meio", "botão do meio"),
    ("onshape", "Onshape", "Gui::TinkerCADNavigationStyle",
     "botão direito", "botão do meio"),
    ("nx", "Siemens NX", "Gui::SiemensNXNavigationStyle",
     "botão do meio", "botão do meio + direito"),
    ("blender", "Blender", "Gui::BlenderNavigationStyle",
     "botão do meio", "Shift + botão do meio"),
    ("prumo", "Padrão do Prumo", "Gui::CADNavigationStyle",
     "botão do meio + esquerdo (ou + direito)", "botão do meio"),
]
POR_ID = {p[0]: p for p in PROGRAMAS}


def _p():
    return FreeCAD.ParamGet(PARAM)


def perguntado():
    return _p().GetBool("OrigemPerguntada", False)


def atual():
    """Id do programa escolhido; se não houver escolha, o que corresponde ao estilo em uso (ou "prumo")."""
    escolhido = _p().GetString("ProgramaOrigem", "")
    if escolhido in POR_ID:
        return escolhido
    estilo = FreeCAD.ParamGet(VISTA).GetString("NavigationStyle", "Gui::CADNavigationStyle")
    for p in PROGRAMAS:
        if p[2] == estilo:
            return p[0]
    return "prumo"


def descricao(pid):
    p = POR_ID.get(pid, POR_ID["prumo"])
    return "Girar: %s. Arrastar: %s. Aproximar: rodinha do mouse." % (p[3], p[4])


def aplicar(pid):
    """Grava o estilo do mouse do programa escolhido e já troca nas vistas abertas."""
    p = POR_ID.get(pid)
    if p is None:
        return False
    vista = FreeCAD.ParamGet(VISTA)
    vista.SetString("NavigationStyle", p[2])
    vista.SetBool("ZoomAtCursor", True)      # nos quatro programas a rodinha aproxima onde está o cursor
    _p().SetString("ProgramaOrigem", pid)
    _p().SetBool("OrigemPerguntada", True)
    n = 0
    try:
        import FreeCADGui
        for nome in FreeCAD.listDocuments():
            gd = FreeCADGui.getDocument(nome)
            for v in (gd.mdiViewsOfType("Gui::View3DInventor") if gd else []):
                try:
                    v.setNavigationType(p[2])
                    n += 1
                except Exception:
                    pass
    except Exception:
        pass
    return True


def pular():
    _p().SetBool("OrigemPerguntada", True)


if FreeCAD.GuiUp:
    from PySide import QtCore, QtWidgets

    class FaixaOrigem(QtWidgets.QFrame):
        """Faixa da tela inicial: "Vem de outro CAD? Deixe o mouse igual ao dele"."""

        escolhido = QtCore.Signal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("PrumoFaixaOrigem")
            self.setStyleSheet(
                "#PrumoFaixaOrigem { background: #EEF4FA; border: 1px solid #C9D9EA; border-radius: 10px; }"
                "#PrumoFaixaOrigem QLabel { background: transparent; }"
                "#PrumoFaixaOrigem QPushButton { padding: 5px 12px; }")
            v = QtWidgets.QVBoxLayout(self)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(6)
            t = QtWidgets.QLabel("Vem de outro CAD? Deixe o mouse da vista 3D igual ao do programa que você usa:")
            t.setStyleSheet("color: #003A70; font-weight: 600;")
            t.setWordWrap(True)
            v.addWidget(t)
            linha = QtWidgets.QHBoxLayout()
            linha.setSpacing(6)
            self.botoes = {}
            for pid, nome, _e, _g, _a in PROGRAMAS:
                b = QtWidgets.QPushButton(nome)
                b.setToolTip(descricao(pid))
                b.setAutoDefault(False)
                b.clicked.connect(lambda _c=False, i=pid: self._escolher(i))
                linha.addWidget(b)
                self.botoes[pid] = b
            linha.addStretch(1)
            agora_nao = QtWidgets.QPushButton("Agora não")
            agora_nao.setFlat(True)
            agora_nao.setAutoDefault(False)
            agora_nao.clicked.connect(self._pular)
            linha.addWidget(agora_nao)
            v.addLayout(linha)
            self.nota = QtWidgets.QLabel("Dá para trocar depois em Preferências do Prumo (cartão Mouse).")
            self.nota.setStyleSheet("color: #5B6B7B;")
            self.nota.setWordWrap(True)
            v.addWidget(self.nota)

        def _escolher(self, pid):
            aplicar(pid)
            for b in self.botoes.values():
                b.setEnabled(False)
            self.nota.setText("Pronto: mouse como no %s. %s Trocar: Preferências do Prumo, cartão Mouse."
                              % (POR_ID[pid][1], descricao(pid)))
            self.escolhido.emit(pid)
            QtCore.QTimer.singleShot(6000, self.hide)

        def _pular(self):
            pular()
            self.hide()

    def cartao_preferencias(UI):
        """Cartão "Mouse" para a janela de Preferências do Prumo."""
        c = UI.Cartao("Mouse da vista 3D", "olho")
        combo = QtWidgets.QComboBox()
        for pid, nome, *_r in PROGRAMAS:
            combo.addItem("Como no " + nome if pid != "prumo" else nome, pid)
        combo.setCurrentIndex(max(0, combo.findData(atual())))
        nota = QtWidgets.QLabel(descricao(atual()))
        nota.setObjectName("PrumoSub")
        nota.setWordWrap(True)

        def mudou(_i):
            pid = combo.currentData()
            aplicar(pid)
            nota.setText(descricao(pid))
        combo.currentIndexChanged.connect(mudou)
        c.linha("Girar, arrastar e aproximar como no", combo)
        c.widget(nota)
        return c, combo
