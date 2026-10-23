# SPDX-License-Identifier: LGPL-2.1-or-later
"""Kit visual do Prumo 3D (padrão desde a 0.6): o que os quadros do painel lateral mostram.

Toda tela nova ou alterada usa estas peças, para o sistema inteiro falar a mesma língua:

- Cartao: bloco branco de cantos arredondados, título azul com ícone; linhas "rótulo ........ campo";
  pode ter uma chave no título (o cartão inteiro liga/desliga, como "Segundo lado").
- Interruptor: chave liga/desliga no lugar da caixa de marcar.
- Segmentado: botões com ícone e texto, um ligado por vez (até 4 por linha).
- CampoNumero: número com a unidade ao lado, sem setas, vírgula decimal.
- Chip: etiqueta arredondada para o que foi escolhido (perfil, aresta, face).
- Dica: faixa amarela com a instrução do momento.

Cores (tema claro; o escuro sai do PrumoEstilo.tema): azul #003A70, amarelo #F7BE00, linhas #DCE4EC,
fundo do painel #F5F8FC, cartão #FFFFFF, texto #1F2A36, texto secundário #5B6876.
"""

import FreeCAD

from PySide import QtCore, QtGui, QtWidgets

try:
    import PrumoEstilo
except Exception:  # pragma: no cover
    PrumoEstilo = None

LOCALE = QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil)

AZUL = "#003A70"
AMARELO = "#F7BE00"
LINHA = "#DCE4EC"
FUNDO = "#F5F8FC"
CARTAO = "#FFFFFF"
TEXTO = "#1F2A36"
TEXTO2 = "#5B6876"
VERDE = "#1E7A4C"
VERMELHO = "#A33A2B"


def tema(texto):
    """Passa um trecho de CSS/SVG pelo tema escuro, quando ligado."""
    if PrumoEstilo is None:
        return texto
    try:
        return PrumoEstilo.tema(texto)
    except Exception:
        return texto


def cor(hexcor, papel="fundo"):
    if PrumoEstilo is None:
        return hexcor
    try:
        return PrumoEstilo.cor(hexcor, papel)
    except Exception:
        return hexcor


def escuro():
    try:
        return bool(PrumoEstilo and PrumoEstilo.escuro())
    except Exception:
        return False


# ----------------------------------------------------------------------------------- ícones
# Traço único, 24 × 24, linha 1,8: os mesmos desenhos dos quadros do painel.
ICONES = {
    "arvore": '<path d="M4 5h6M4 12h6M4 19h6M10 5v14M14 8h6M14 16h6"/>',
    "propriedades": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/>'
                    '<circle cx="10" cy="17" r="2"/>',
    "aparencia": '<path d="M12 3a9 9 0 1 0 0 18c1.2 0 1.6-.9 1.2-1.8-.5-1 .2-2.2 1.3-2.2H17a4 4 0 0 0 4-4'
                 'c0-5.5-4-10-9-10z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="11" cy="7" r="1.2"/>'
                 '<circle cx="16" cy="8.5" r="1.2"/>',
    "comando": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
    "solido": '<path d="M4 16l8 4 8-4V8l-8-4-8 4z"/><path d="M4 8l8 4 8-4M12 12v8"/>',
    "perfil": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "esboco": '<path d="M4 18L18 4M4 4h6M4 4v6"/>',
    "seta_cima": '<path d="M12 20V4M8 8l4-4 4 4"/>',
    "seta_baixo": '<path d="M12 4v16M8 16l4 4 4-4"/>',
    "dois_lados": '<path d="M12 4v16M8 8l4-4 4 4M8 16l4 4 4-4"/>',
    "medida": '<path d="M4 8h16M4 14h16M12 8v6"/>',
    "atraves": '<path d="M4 5h16M4 19h16M12 5v14"/>',
    "ate_face": '<path d="M4 5h16M12 5v10M4 15l8 4 8-4"/>',
    "ate_primeira": '<path d="M4 5h16M12 5v8"/><circle cx="12" cy="17" r="3"/>',
    "ate_fim": '<path d="M4 5h16M12 5v14M4 19h16M9 16l3 3 3-3"/>',
    "simetrica": '<path d="M4 12h16M12 4v16"/>',
    "acabamento": '<path d="M4 20l6-6M14 4l6 6-8 8-6-6z"/>',
    "angulo": '<path d="M4 20h16M4 20L16 6"/><path d="M11 20a7 7 0 0 0-2.2-5.1"/>',
    "raio": '<path d="M4 20V10a6 6 0 0 1 6-6h10"/><path d="M10 10l-3.5-3.5"/>',
    "chanfro": '<path d="M4 20V9l5-5h11"/><path d="M4 9l5-5"/>',
    "furo": '<circle cx="12" cy="12" r="6"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/>',
    "padrao": '<circle cx="7" cy="12" r="2.5"/><circle cx="17" cy="12" r="2.5"/><path d="M9.5 12h5"/>',
    "fixacao": '<circle cx="12" cy="12" r="7"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>',
    "corpo": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    "selecao": '<path d="M5 3l12 8-5 1.5L9.5 18z"/>',
    "lista": '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/>'
             '<circle cx="4" cy="18" r="1"/>',
    "olho": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "exibicao_solido": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" fill="#9FB4CA"/>',
    "exibicao_arestas": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" fill="#9FB4CA"/>'
                        '<path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    "exibicao_arame": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    "exibicao_pontos": '<circle cx="5" cy="7" r="1"/><circle cx="19" cy="7" r="1"/><circle cx="12" cy="3" r="1"/>'
                       '<circle cx="12" cy="21" r="1"/><circle cx="5" cy="17" r="1"/><circle cx="19" cy="17" r="1"/>',
    "texto": '<path d="M5 6h14M12 6v13M9 19h6"/>',
    "numero": '<path d="M9 4L7 20M17 4l-2 16M4 9h16M3 15h16"/>',
    "vinculo": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/>'
               '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
}


def svg(nome, traco=None):
    corpo = ICONES.get(nome, ICONES["info"])
    traco = traco or (cor(AZUL, "texto") if escuro() else AZUL)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{}" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>').format(traco, corpo)


_cache_icones = {}


def icone(nome, traco=None):
    """QIcon nítido em qualquer escala (desenhado do SVG em vários tamanhos)."""
    from PySide import QtSvg
    chave = (nome, traco, escuro())
    if chave in _cache_icones:
        return _cache_icones[chave]
    r = QtSvg.QSvgRenderer(QtCore.QByteArray(svg(nome, traco).encode("utf-8")))
    ic = QtGui.QIcon()
    for lado in (16, 18, 20, 24, 32, 40, 48):
        pm = QtGui.QPixmap(lado, lado)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        r.render(p)
        p.end()
        ic.addPixmap(pm)
    _cache_icones[chave] = ic
    return ic


# ----------------------------------------------------------------------------------- estilo
QSS = """
#PrumoUI { background: #F5F8FC; }
#PrumoUI QLabel { background: transparent; color: #1F2A36; }
#PrumoUI QScrollArea, #PrumoUI #PrumoRolagem { background: #F5F8FC; border: 0; }
#PrumoCartao { background: #FFFFFF; border: 1px solid #DCE4EC; border-radius: 10px; }
#PrumoCartao QLabel#PrumoCartaoTitulo { color: #003A70; font-weight: 600; }
#PrumoCartao QLabel#PrumoRotulo { color: #1F2A36; }
QLabel#PrumoSub { color: #5B6876; font-size: 8pt; }
QLabel#PrumoChip { background: #F0F4F8; color: #1F2A36; border-radius: 12px; padding: 3px 10px; }
QLabel#PrumoDica { background: #FFF8DC; color: #4D3B00; border-radius: 8px; padding: 8px 10px; }
QLabel#PrumoDica[tipo="erro"] { background: #FBE9E5; color: #7A2615; }
QLabel#PrumoDica[tipo="ok"] { background: #E5F3ED; color: #1E5C46; }
QToolButton#PrumoSeg { border: 1px solid #DCE4EC; border-radius: 8px; background: #FFFFFF; color: #3B4A59;
                       padding: 5px 2px; }
QToolButton#PrumoSeg:hover { border-color: #7FA3C9; }
QToolButton#PrumoSeg:checked { background: #E6EEF7; border: 1px solid #003A70; color: #003A70; font-weight: 600; }
QDoubleSpinBox#PrumoNum, QSpinBox#PrumoNum, QLineEdit#PrumoCampo, QComboBox#PrumoLista {
    border: 1px solid #C9D3DD; border-radius: 8px; padding: 4px 8px; background: #FFFFFF; color: #1F2A36;
    min-height: 22px; }
QDoubleSpinBox#PrumoNum:focus, QSpinBox#PrumoNum:focus, QLineEdit#PrumoCampo:focus { border-color: #003A70; }
QDoubleSpinBox#PrumoNum[expressao="true"] { background: #F0F4F8; color: #3B4A59; }
QPushButton#PrumoPrimario { background: #003A70; color: #FFFFFF; border: 0; border-radius: 8px;
                            padding: 6px 12px; font-weight: 600; }
QPushButton#PrumoPrimario:hover { background: #0B4F8F; }
QPushButton#PrumoLink, QToolButton#PrumoLink { background: transparent; color: #003A70; border: 0;
                                               font-weight: 600; padding: 2px 4px; }
QToolButton#PrumoAvancado { border: 1px dashed #C9D3DD; border-radius: 10px; background: transparent;
                            color: #5B6876; font-weight: 600; padding: 8px 10px; text-align: left; }
QSlider#PrumoDeslizar::groove:horizontal { height: 4px; background: #DCE4EC; border-radius: 2px; }
QSlider#PrumoDeslizar::sub-page:horizontal { background: #003A70; border-radius: 2px; }
QSlider#PrumoDeslizar::handle:horizontal { background: #FFFFFF; border: 2px solid #003A70; width: 12px;
                                           height: 12px; margin: -6px 0; border-radius: 8px; }
"""


def qss():
    return tema(QSS)


# ----------------------------------------------------------------------------------- peças
class Interruptor(QtWidgets.QAbstractButton):
    """Chave liga/desliga (36 × 20). Sinal: toggled(bool)."""

    def __init__(self, ligado=False, parent=None, dica=""):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(bool(ligado))
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.TabFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        if dica:
            self.setToolTip(dica)

    def sizeHint(self):
        return QtCore.QSize(36, 20)

    def paintEvent(self, _ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(0.5, 0.5, 35, 19)
        on = self.isChecked()
        trilho = QtGui.QColor(cor(AZUL, "texto") if escuro() else AZUL) if on else QtGui.QColor(
            "#4A5563" if escuro() else "#C9D3DD")
        if not self.isEnabled():
            trilho.setAlpha(110)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(trilho)
        p.drawRoundedRect(r, 10, 10)
        x = 18.0 if on else 2.0
        p.setBrush(QtGui.QColor("#FFFFFF"))
        p.drawEllipse(QtCore.QRectF(x, 2.0, 16.0, 16.0))
        if self.hasFocus():
            p.setPen(QtGui.QPen(QtGui.QColor(AMARELO), 1.5))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawRoundedRect(r, 10, 10)
        p.end()


class Segmentado(QtWidgets.QWidget):
    """Botões com ícone e texto, um ligado por vez. opcoes = [(chave, texto, ícone ou None, dica)]."""

    mudou = QtCore.Signal(str)

    def __init__(self, opcoes, atual=None, parent=None, colunas=4):
        super().__init__(parent)
        lay = QtWidgets.QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        colunas = max(1, min(colunas, len(opcoes)))
        for c in range(colunas):
            lay.setColumnStretch(c, 1)
        self.grupo = QtWidgets.QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botoes = {}
        for n, op in enumerate(opcoes):
            chave, texto = op[0], op[1]
            ic = op[2] if len(op) > 2 else None
            dica = op[3] if len(op) > 3 else ""
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoSeg")
            b.setText(texto)
            b.setCheckable(True)
            b.setToolTip(dica or texto)
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            if ic:
                b.setIcon(icone(ic))
                b.setIconSize(QtCore.QSize(18, 18))
                b.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            else:
                b.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
            self.grupo.addButton(b)
            lay.addWidget(b, n // colunas, n % colunas)
            self.botoes[chave] = b
            b.toggled.connect(lambda on, k=chave: on and self.mudou.emit(k))
        self.definir(atual if atual in self.botoes else (opcoes[0][0] if opcoes else None))

    def valor(self):
        for k, b in self.botoes.items():
            if b.isChecked():
                return k
        return None

    def definir(self, chave, silencioso=True):
        b = self.botoes.get(chave)
        if b is None:
            return
        if silencioso:
            self.blockSignals(True)
            b.setChecked(True)
            self.blockSignals(False)
        else:
            b.setChecked(True)


class CampoNumero(QtWidgets.QDoubleSpinBox):
    """Número com unidade (ex.: 10,00 mm). Sem setas; Enter ou sair do campo confirma."""

    def __init__(self, valor=0.0, unidade="", casas=2, minimo=-1e9, maximo=1e9, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoNum")
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setLocale(LOCALE)
        self.setDecimals(casas)
        self.setRange(minimo, maximo)
        self.setKeyboardTracking(False)
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if unidade:
            self.setSuffix(" " + unidade)
        self.setValue(valor)
        self.setMinimumWidth(80)
        self.setMaximumWidth(140)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, ev):
        # a roda do mouse rola o painel, não muda a medida sem querer
        if self.hasFocus():
            super().wheelEvent(ev)
        else:
            ev.ignore()


class Chip(QtWidgets.QLabel):
    def __init__(self, texto, icone_nome=None, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoChip")
        self.setText(texto)
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)


class Dica(QtWidgets.QLabel):
    def __init__(self, texto="", tipo="info", parent=None):
        super().__init__(texto, parent)
        self.setObjectName("PrumoDica")
        self.setWordWrap(True)
        self.mostrar(texto, tipo)

    def mostrar(self, texto, tipo="info"):
        self.setText(texto)
        self.setProperty("tipo", tipo)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(bool(texto))


class Cartao(QtWidgets.QFrame):
    """Bloco com título (ícone + texto) e linhas "rótulo ... campo".

    chave=True põe um Interruptor no título: desligado, o corpo do cartão some (ex.: "Segundo lado").
    """

    def __init__(self, titulo, icone_nome=None, chave=False, ligado=True, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoCartao")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        topo = QtWidgets.QHBoxLayout()
        topo.setSpacing(8)
        if icone_nome:
            ic = QtWidgets.QLabel()
            ic.setPixmap(icone(icone_nome).pixmap(18, 18))
            ic.setFixedSize(18, 18)
            topo.addWidget(ic)
        self.titulo = QtWidgets.QLabel(titulo)
        self.titulo.setObjectName("PrumoCartaoTitulo")
        topo.addWidget(self.titulo, 1)
        self.chave = None
        if chave:
            self.chave = Interruptor(ligado)
            self.chave.toggled.connect(self._alternar)
            topo.addWidget(self.chave)
        lay.addLayout(topo)
        self.corpo = QtWidgets.QWidget()
        self.grade = QtWidgets.QGridLayout(self.corpo)
        self.grade.setContentsMargins(0, 0, 0, 0)
        self.grade.setHorizontalSpacing(10)
        self.grade.setVerticalSpacing(8)
        self.grade.setColumnStretch(0, 1)
        lay.addWidget(self.corpo)
        self._n = 0
        self.linhas = {}
        if chave:
            self._alternar(ligado)

    def _alternar(self, on):
        self.corpo.setVisible(bool(on) and self._n > 0)

    def linha(self, rotulo, widget, dica="", chave=None):
        lb = QtWidgets.QLabel(rotulo)
        lb.setObjectName("PrumoRotulo")
        lb.setWordWrap(True)
        if dica:
            lb.setToolTip(dica)
            widget.setToolTip(dica)
        self.grade.addWidget(lb, self._n, 0)
        self.grade.addWidget(widget, self._n, 1, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self._n += 1
        self.linhas[chave or rotulo] = (lb, widget)
        self.corpo.setVisible(self.chave is None or self.chave.isChecked())
        return widget

    def widget(self, w):
        self.grade.addWidget(w, self._n, 0, 1, 2)
        self._n += 1
        self.corpo.setVisible(self.chave is None or self.chave.isChecked())
        return w

    def mostrar_linha(self, chave, visivel):
        par = self.linhas.get(chave)
        if par:
            for w in par:
                w.setVisible(visivel)

    def vazio(self):
        return self._n == 0


def rolagem(conteudo):
    """Área com rolagem vertical, fundo do painel, sem moldura."""
    sa = QtWidgets.QScrollArea()
    sa.setObjectName("PrumoRolagem")
    sa.setWidgetResizable(True)
    sa.setFrameShape(QtWidgets.QFrame.NoFrame)
    sa.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    sa.setWidget(conteudo)
    sa.viewport().setAutoFillBackground(False)
    conteudo.setAutoFillBackground(False)
    return sa


def coluna(espaco=10, margens=(12, 12, 12, 12)):
    w = QtWidgets.QWidget()
    w.setObjectName("PrumoUI")
    w.setAttribute(QtCore.Qt.WA_StyledBackground, True)
    v = QtWidgets.QVBoxLayout(w)
    v.setContentsMargins(*margens)
    v.setSpacing(espaco)
    return w, v


def raiz(parent=None):
    """Widget-base de um painel no padrão: fundo do painel e o estilo do kit."""
    w = QtWidgets.QWidget(parent)
    w.setObjectName("PrumoUI")
    w.setAttribute(QtCore.Qt.WA_StyledBackground, True)
    w.setStyleSheet(qss())
    return w
