# SPDX-License-Identifier: LGPL-2.1-or-later
"""Janela "Sobre o Prumo 3D" no padrão visual Prumo."""
import os

from PySide import QtCore, QtGui, QtWidgets

import PrumoEstilo

HERE = os.path.dirname(os.path.abspath(__file__))
ICON_SVG = os.path.join(HERE, "Resources", "icons", "prumo.svg")
ICON_PNG = os.path.join(HERE, "Resources", "icons", "prumo.png")
# endereço público do projeto (ajustar se o repositório mudar de lugar)
URL_PROJETO = "github.com/prumo3d/prumo3d"

QSS = """
#SwSobre { background: #F4F7FB; }
#SwSobreTopo { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0A4D8C, stop:1 #002A52);
               border-bottom: 4px solid #F7BE00; }
#SwSobreTopo QLabel { background: transparent; }
#SwSobreNome { color: #FFFFFF; font-size: 20pt; font-weight: 700; }
#SwSobreVersao { color: #C9DAEA; font-size: 10pt; }
#SwSobreCard { background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 8px; }
#SwSobreCard QLabel { background: transparent; }
#SwSobreRotulo { color: #6B7785; font-size: 8.5pt; }
#SwSobreValor { color: #1F2A36; font-size: 10pt; }
#SwSobreEmpresa { color: #003A70; font-size: 11pt; font-weight: 700; }
#SwSobreLegal { color: #8A96A3; font-size: 8.5pt; }
"""


def _pix(size):
    dpr = max(QtWidgets.QApplication.instance().devicePixelRatio(), 1)
    src = ICON_SVG if os.path.isfile(ICON_SVG) else ICON_PNG
    pm = QtGui.QIcon(src).pixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    return pm


class SobreDialog(QtWidgets.QDialog):
    def __init__(self, versao, base, parent=None):
        super().__init__(parent)
        self.setObjectName("SwSobre")
        self.setWindowTitle("Sobre o Prumo 3D")
        self.setStyleSheet(PrumoEstilo.tema(QSS))
        self.setMinimumWidth(520)
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 16)
        v.setSpacing(14)

        topo = QtWidgets.QFrame()
        topo.setObjectName("SwSobreTopo")
        th = QtWidgets.QHBoxLayout(topo)
        th.setContentsMargins(24, 20, 24, 20)
        th.setSpacing(18)
        ic = QtWidgets.QLabel()
        ic.setPixmap(_pix(84))
        th.addWidget(ic)
        tc = QtWidgets.QVBoxLayout()
        tc.setSpacing(2)
        n = QtWidgets.QLabel("Prumo 3D")
        n.setObjectName("SwSobreNome")
        ver = QtWidgets.QLabel("Versão " + versao)
        ver.setObjectName("SwSobreVersao")
        tc.addStretch(1)
        tc.addWidget(n)
        tc.addWidget(ver)
        tc.addStretch(1)
        th.addLayout(tc, 1)
        v.addWidget(topo)

        card = QtWidgets.QFrame()
        card.setObjectName("SwSobreCard")
        g = QtWidgets.QGridLayout(card)
        g.setContentsMargins(18, 14, 18, 14)
        g.setHorizontalSpacing(18)
        g.setVerticalSpacing(8)
        emp = QtWidgets.QLabel("PRUMO 3D")
        emp.setObjectName("SwSobreEmpresa")
        g.addWidget(emp, 0, 0, 1, 2)
        linhas = [
            ("Para", "Modelagem 3D paramétrica, desenho técnico e simulação"),
            ("Idioma", "Português do Brasil"),
            ("Projeto", URL_PROJETO),
            ("Base", base),
        ]
        try:
            import PrumoVersao
            if PrumoVersao.commit():
                linhas.append(("Código", PrumoVersao.commit()))
        except Exception:
            pass
        for i, (r, val) in enumerate(linhas, start=1):
            a = QtWidgets.QLabel(r)
            a.setObjectName("SwSobreRotulo")
            b = QtWidgets.QLabel(val)
            b.setObjectName("SwSobreValor")
            b.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            g.addWidget(a, i, 0)
            g.addWidget(b, i, 1)
        g.setColumnStretch(1, 1)
        wrap = QtWidgets.QHBoxLayout()
        wrap.setContentsMargins(20, 0, 20, 0)
        wrap.addWidget(card)
        v.addLayout(wrap)

        legal = QtWidgets.QLabel(
            "Software livre sob licença LGPL-2.1-or-later, baseado no FreeCAD (freecad.org). "
            "O Prumo 3D não é um projeto oficial do FreeCAD.")
        legal.setObjectName("SwSobreLegal")
        legal.setWordWrap(True)
        lw = QtWidgets.QHBoxLayout()
        lw.setContentsMargins(22, 0, 22, 0)
        lw.addWidget(legal)
        v.addLayout(lw)

        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        self.bt_copiar = bb.addButton("Copiar informações do sistema", QtWidgets.QDialogButtonBox.ActionRole)
        self.bt_copiar.setToolTip("Versão, sistema e placa de vídeo — cole junto ao relato de um problema")
        self.bt_copiar.clicked.connect(self.copiar_info)
        self.bt_licencas = bb.addButton("Licenças e bibliotecas", QtWidgets.QDialogButtonBox.HelpRole)
        self.bt_licencas.setToolTip("Créditos, licença LGPL e bibliotecas de terceiros (Sobre do FreeCAD)")
        self.bt_licencas.clicked.connect(self.licencas)
        bb.rejected.connect(self.reject)
        bb.button(QtWidgets.QDialogButtonBox.Close).setText("Fechar")
        bb.button(QtWidgets.QDialogButtonBox.Close).setDefault(True)
        bw = QtWidgets.QHBoxLayout()
        bw.setContentsMargins(20, 0, 20, 0)
        bw.addWidget(bb)
        v.addLayout(bw)


    def licencas(self):
        try:
            import FreeCADGui
            FreeCADGui.runCommand("Std_About", 0)
        except Exception:
            pass

    def copiar_info(self):
        import PrumoVersao
        txt = PrumoVersao.info_sistema()
        QtWidgets.QApplication.clipboard().setText(txt)
        self.bt_copiar.setText("Copiado ✓")
        QtCore.QTimer.singleShot(2000, lambda: self.bt_copiar.setText("Copiar informações do sistema"))
        return txt


def mostrar(versao, base, parent=None):
    d = SobreDialog(versao, base, parent)
    return d.exec_() if hasattr(d, "exec_") else d.exec()
