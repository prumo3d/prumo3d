# SPDX-License-Identifier: LGPL-2.1-or-later
"""Painéis de tarefa visuais do Prumo 3D (no estilo do PropertyManager do SolidWorks).

Peças do kit:
- Mensagem: caixa amarela no topo com a instrução do momento (ou erro/ok);
- Secao: bloco com título, ícone e seta de recolher;
- linha(icone, widget, dica): campo com ícone à esquerda e dica ao passar o mouse;
- CaixaSelecao: lista do que está selecionado (barra colorida à esquerda), que aceita seleção
  feita ANTES ou DEPOIS de abrir o painel e só fica pronta quando tem o mínimo pedido;
- Opcoes: botões com ícone, um ligado por vez (ex.: Empurra / Puxa);
- PainelTarefa: base para os comandos (accept/reject do painel de tarefas do FreeCAD).

Ícones dos campos (ICONES): desenhos simples em SVG, no azul Prumo.
"""

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets

import PrumoEstilo

NAVY = "#003A70"
AMBAR = "#E0A100"
LOCALE = QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil)

# ----------------------------------------------------------------------------------- ícones
_T = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" ' \
     'stroke="%s" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%%s</svg>' % NAVY
_SETAS = '<path d="M3 12h18M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3"/>'
ICONES = {
    "comprimento": _SETAS + '<path d="M3 6v12M21 6v12" stroke-width="1.2"/>',
    "largura": '<rect x="4" y="7" width="16" height="10" rx="1"/><path d="M4 20h16M4 20l2-1.5M4 20l2 1.5'
               'M20 20l-2-1.5M20 20l-2 1.5" stroke="%s"/>' % AMBAR,
    "altura": '<rect x="7" y="4" width="10" height="16" rx="1"/><path d="M21 4v16M21 4l-1.5 2M21 4l1.5 2'
              'M21 20l-1.5-2M21 20l1.5-2" stroke="%s"/>' % AMBAR,
    "espessura": '<path d="M4 9h16M4 15h16"/><path d="M12 3v6M12 21v-6M12 9l-2-2.5M12 9l2-2.5M12 15l-2 2.5'
                 'M12 15l2 2.5" stroke="%s"/>' % AMBAR,
    "perna": '<path d="M4 20V4M4 20h16"/><path d="M4 12l8 8" stroke="%s" stroke-width="2.2"/>' % AMBAR,
    "angulo": '<path d="M4 20h16M4 20L16 6"/><path d="M11 20a7 7 0 0 0-2.2-5.1" stroke="%s"/>' % AMBAR,
    "raio": '<path d="M4 20V10a6 6 0 0 1 6-6h10"/><path d="M10 10l-3.5-3.5" stroke="%s"/>' % AMBAR,
    "chanfro": '<path d="M4 20V9l5-5h11"/><path d="M4 9l5-5" stroke="%s" stroke-width="2.4"/>' % AMBAR,
    "material": '<rect x="4" y="5" width="16" height="14" rx="1.5"/><path d="M4 11l6-6M4 17L16 5M10 19'
                'l10-10M16 19l4-4" stroke-width="1.1"/>',
    "tipo": '<path d="M4 20V8l6 6V20zM14 20V4h6v16z"/>',
    "posicao": '<circle cx="12" cy="12" r="7"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/>',
    "ponta": '<path d="M3 9h12M3 15h12M15 6v12"/><path d="M18 9l3 3-3 3" stroke="%s"/>' % AMBAR,
    "folga": '<path d="M4 4v16M20 4v16"/><path d="M8 12h8M8 12l2-2M8 12l2 2M16 12l-2-2M16 12l-2 2" '
             'stroke="%s"/>' % AMBAR,
    "furo": '<circle cx="12" cy="12" r="6"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4" stroke-width="1.1"/>',
    "quantidade": '<path d="M9 4L7 20M17 4l-2 16M4 9h16M3 15h16"/>',
    "solda": '<path d="M4 20V5M4 20h15"/><path d="M4 20V12l8 8z" fill="%s" stroke="%s"/>' % (AMBAR, AMBAR),
    "processo": '<path d="M5 19l9-9M14 10l3-3 2 2-3 3z"/><path d="M4 20l2-3M7 21l1-2" stroke="%s"/>' % AMBAR,
    "eletrodo": '<path d="M6 18L18 6"/><path d="M16 4l4 4" stroke-width="2.6"/>',
    "lado": '<path d="M12 3v18"/><path d="M9 8l-5 4 5 4M15 8l5 4-5 4" stroke="%s"/>' % AMBAR,
    "texto": '<path d="M5 6h14M12 6v13M9 19h6"/>',
    "escala": '<rect x="3" y="3" width="8" height="8"/><rect x="9" y="9" width="12" height="12" '
              'stroke="%s"/>' % AMBAR,
    "folha": '<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v4h4M8 17h8M8 13h8" stroke-width="1.2"/>',
    "parafuso": '<path d="M8 4h8v4H8zM10 8v12h4V8"/><path d="M10 11h4M10 14h4M10 17h4" stroke-width="1.1"/>',
    "selecao": '<path d="M5 3l12 8-5 1.5L9.5 18z"/>',
    "empurra": '<rect x="12" y="4" width="8" height="16" rx="1" fill="#D3E1EF"/><path d="M2 12h8M10 12l-3-3'
               'M10 12l-3 3" stroke="%s" stroke-width="2.4"/>' % AMBAR,
    "puxa": '<rect x="12" y="4" width="8" height="16" rx="1" fill="#D3E1EF"/><path d="M10 12H2M2 12l3-3'
            'M2 12l3 3" stroke="%s" stroke-width="2.4"/>' % AMBAR,
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
}


def svg_icone(nome):
    corpo = ICONES.get(nome, ICONES["info"])
    return PrumoEstilo.tema(_T % corpo)


def icone(nome, tamanho=20):
    """QIcon de um dos ícones do kit."""
    r = _renderizador(svg_icone(nome))
    pm = QtGui.QPixmap(tamanho * 2, tamanho * 2)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    r.render(p)
    p.end()
    pm.setDevicePixelRatio(2.0)
    return QtGui.QIcon(pm)


def _renderizador(svg):
    try:
        from PySide6 import QtSvg
    except ImportError:  # pragma: no cover
        from PySide2 import QtSvg
    return QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))


# ----------------------------------------------------------------------------------- estilo
QSS = """
#PrumoPainel { background: #FFFFFF; }
#PrumoPainel QLabel { background: transparent; color: #1F2A36; }
#PrumoMsg { background: #FFF6D6; color: #4D3B00; border-left: 3px solid #E0A100; border-radius: 4px;
            padding: 7px 9px; font-size: 9pt; }
#PrumoMsg[tipo="erro"] { background: #FBE9E5; color: #7A2615; border-left-color: #B5523F; }
#PrumoMsg[tipo="ok"] { background: #E5F3ED; color: #1E5C46; border-left-color: #2E8B6A; }
#PrumoSecaoTopo { background: transparent; border: none; border-bottom: 1px solid #DCE4EC; color: #003A70;
                  font-weight: 600; font-size: 9.5pt; text-align: left; padding: 6px 2px 5px 2px; }
#PrumoSecaoTopo:hover { color: #0B4F8F; }
#PrumoDica { color: #66727F; font-size: 8pt; }
#PrumoCaixaSel { background: #FFFFFF; border: 1px solid #C9D5E2; border-left: 4px solid #E7A6C8;
                 border-radius: 4px; }
#PrumoCaixaSel[ativa="true"] { border-color: #7FA3C9; border-left: 4px solid #D9468F; background: #FBFDFF; }
#PrumoCaixaSel QListWidget { border: none; background: transparent; }
#PrumoCaixaSel QListWidget::item:selected { background: #D6E6F7; color: #1F2A36; }
#PrumoOpcao { border: 1px solid #C9D5E2; border-radius: 6px; padding: 5px 8px; background: #FFFFFF; }
#PrumoOpcao:checked { border: 2px solid #003A70; background: #EAF1F8; }
#PrumoOpcao:hover { border-color: #7FA3C9; }
"""


def qss():
    return PrumoEstilo.tema(QSS)


# ----------------------------------------------------------------------------------- peças
class Mensagem(QtWidgets.QLabel):
    def __init__(self, texto="", parent=None):
        super().__init__(texto, parent)
        self.setObjectName("PrumoMsg")
        self.setWordWrap(True)
        self.setProperty("tipo", "info")
        self.setTextFormat(QtCore.Qt.RichText)

    def mostrar(self, texto, tipo="info"):
        self.setText(texto)
        self.setProperty("tipo", tipo)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(bool(texto))

    @property
    def tipo(self):
        return self.property("tipo")


class Secao(QtWidgets.QWidget):
    """Bloco com título clicável (recolhe/expande) e conteúdo em grade: ícone | campo."""

    def __init__(self, titulo, icone_nome=None, aberta=True, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 2)
        lay.setSpacing(4)
        self.topo = QtWidgets.QToolButton()
        self.topo.setObjectName("PrumoSecaoTopo")
        self.topo.setText(titulo)
        self.topo.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.topo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.topo.setCheckable(True)
        self.topo.setChecked(aberta)
        self.topo.setArrowType(QtCore.Qt.DownArrow if aberta else QtCore.Qt.RightArrow)
        self.topo.toggled.connect(self._alternar)
        lay.addWidget(self.topo)
        self.corpo = QtWidgets.QWidget()
        self.grade = QtWidgets.QGridLayout(self.corpo)
        self.grade.setContentsMargins(2, 2, 2, 2)
        self.grade.setHorizontalSpacing(8)
        self.grade.setVerticalSpacing(6)
        self.grade.setColumnStretch(1, 1)
        lay.addWidget(self.corpo)
        self.corpo.setVisible(aberta)
        self._linha = 0

    def _alternar(self, aberta):
        self.corpo.setVisible(aberta)
        self.topo.setArrowType(QtCore.Qt.DownArrow if aberta else QtCore.Qt.RightArrow)

    @property
    def aberta(self):
        return self.corpo.isVisible() or self.topo.isChecked()

    def linha(self, icone_nome, widget, dica="", rotulo=None):
        """Uma linha da seção: ícone à esquerda, rótulo curto (opcional) e o campo; a dica vira
        tooltip do ícone e do campo."""
        ic = QtWidgets.QLabel()
        if icone_nome:
            ic.setPixmap(icone(icone_nome).pixmap(20, 20))
        ic.setFixedWidth(24)
        ic.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        if dica:
            ic.setToolTip(dica)
            widget.setToolTip(dica)
        self.grade.addWidget(ic, self._linha, 0)
        if rotulo:
            caixa = QtWidgets.QVBoxLayout()
            caixa.setSpacing(1)
            lb = QtWidgets.QLabel(rotulo)
            lb.setObjectName("PrumoDica")
            caixa.addWidget(lb)
            caixa.addWidget(widget)
            self.grade.addLayout(caixa, self._linha, 1)
        else:
            self.grade.addWidget(widget, self._linha, 1)
        self._linha += 1
        return widget

    def texto(self, texto):
        lb = QtWidgets.QLabel(texto)
        lb.setObjectName("PrumoDica")
        lb.setWordWrap(True)
        self.grade.addWidget(lb, self._linha, 0, 1, 2)
        self._linha += 1
        return lb

    def widget(self, w):
        self.grade.addWidget(w, self._linha, 0, 1, 2)
        self._linha += 1
        return w


def rotulo(icone_nome, texto, dica=""):
    """Rótulo com ícone para formulários (QFormLayout.addRow(rotulo(...), campo))."""
    w = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    ic = QtWidgets.QLabel()
    ic.setPixmap(icone(icone_nome).pixmap(18, 18))
    h.addWidget(ic)
    lb = QtWidgets.QLabel(texto)
    h.addWidget(lb)
    h.addStretch(1)
    if dica:
        w.setToolTip(dica)
    return w


def titulo_secao(texto, icone_nome=None):
    """Título de bloco (mesmo visual das seções dos painéis) para diálogos grandes."""
    w = QtWidgets.QWidget()
    h = QtWidgets.QHBoxLayout(w)
    h.setContentsMargins(0, 6, 0, 2)
    h.setSpacing(6)
    if icone_nome:
        ic = QtWidgets.QLabel()
        ic.setPixmap(icone(icone_nome).pixmap(18, 18))
        h.addWidget(ic)
    lb = QtWidgets.QLabel(texto)
    lb.setStyleSheet(PrumoEstilo.tema("color: #003A70; font-weight: 600; font-size: 10pt;"))
    h.addWidget(lb, 1)
    w.setStyleSheet(PrumoEstilo.tema("border-bottom: 1px solid #DCE4EC;"))
    return w


def numero(valor, minimo=0.0, maximo=5000.0, sufixo=" mm", casas=1):
    s = QtWidgets.QDoubleSpinBox()
    s.setRange(minimo, maximo)
    s.setDecimals(casas)
    s.setSuffix(sufixo)
    s.setLocale(LOCALE)
    s.setValue(valor)
    s.setKeyboardTracking(False)
    return s


def lista(itens, atual=None):
    c = QtWidgets.QComboBox()
    c.addItems(list(itens))
    if atual:
        c.setCurrentText(atual)
    return c


def marcar(texto, ligado=False):
    c = QtWidgets.QCheckBox(texto)
    c.setChecked(ligado)
    return c


class Opcoes(QtWidgets.QWidget):
    """Botões com ícone e texto, um ligado por vez."""

    mudou = QtCore.Signal(str)

    def __init__(self, opcoes, atual=None, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.grupo = QtWidgets.QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botoes = {}
        for chave, texto, ic, dica in opcoes:
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoOpcao")
            b.setText(texto)
            b.setIcon(icone(ic, 28))
            b.setIconSize(QtCore.QSize(28, 28))
            b.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            b.setCheckable(True)
            b.setToolTip(dica)
            b.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            self.grupo.addButton(b)
            lay.addWidget(b)
            self.botoes[chave] = b
            b.toggled.connect(lambda on, k=chave: on and self.mudou.emit(k))
        self.definir(atual or opcoes[0][0])
        # estilo próprio (destaque do botão marcado), para valer também fora dos painéis do Prumo,
        # como no Assistente de simulação
        self.setStyleSheet(qss())

    def valor(self):
        for k, b in self.botoes.items():
            if b.isChecked():
                return k
        return None

    def definir(self, chave):
        if chave in self.botoes:
            self.botoes[chave].setChecked(True)


def resolver(raiz, sub):
    """(objeto dono do elemento, elemento) de um caminho de seleção ("Parte.Corpo.Face3").

    Igual ao que o FreeCAD devolve em getSelection(): o objeto mais interno e o nome curto."""
    if not sub or "." not in sub:
        return raiz, sub or ""
    elemento = sub.rsplit(".", 1)[-1]
    try:
        dono = raiz.getSubObject(sub, retType=1)
    except Exception:
        dono = None
    return (dono if dono is not None else raiz), elemento


def agrupar_selecao(raiz, subs):
    """[(objeto, [elementos], [caminhos completos])] de um item de getSelectionEx("", 0)."""
    grupos = []
    for sub in (subs or ("",)):
        o, el = resolver(raiz, sub)
        g = next((x for x in grupos if x[0] is o), None)
        if g is None:
            g = (o, [], [])
            grupos.append(g)
        if el:
            g[1].append(el)
        if sub:
            g[2].append(sub)
    return grupos


_ATIVO = {"painel": None}   # painel do Prumo aberto no painel de tarefas


class CaixaSelecao(QtWidgets.QFrame):
    """O que o comando precisa que esteja selecionado.

    filtro(obj, subnomes) → lista de (texto, valor) aceitos daquela seleção (vazia = ignora).
    Aceita seleção anterior à abertura do painel e seleção feita depois, na vista ou na árvore.
    Clique na caixa para ela receber a seleção (fica ativa: barra rosa forte).
    """

    mudou = QtCore.Signal()

    def __init__(self, titulo, filtro, minimo=1, maximo=None, dica="", parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoCaixaSel")
        self.filtro = filtro
        self.minimo, self.maximo = minimo, maximo
        self.titulo = titulo
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        topo = QtWidgets.QHBoxLayout()
        ic = QtWidgets.QLabel()
        ic.setPixmap(icone("selecao").pixmap(16, 16))
        topo.addWidget(ic)
        self.rotulo = QtWidgets.QLabel(titulo)
        self.rotulo.setObjectName("PrumoDica")
        topo.addWidget(self.rotulo, 1)
        limpar = QtWidgets.QToolButton()
        limpar.setText("Limpar")
        limpar.setAutoRaise(True)
        limpar.clicked.connect(self.limpar)
        topo.addWidget(limpar)
        lay.addLayout(topo)
        self.lista = QtWidgets.QListWidget()
        self.lista.setMinimumHeight(54)
        self.lista.setMaximumHeight(110)
        self.lista.setToolTip(dica or "Selecione na vista 3D ou na árvore. Delete tira o item da lista.")
        lay.addWidget(self.lista)
        self._valores = []
        self.ativa = False
        self._atualizar_rotulo()

    # ---- seleção
    def aceitar(self, obj, subnomes=()):
        """Tenta pôr na caixa um item de seleção; devolve quantos entraram."""
        try:
            itens = self.filtro(obj, tuple(subnomes or ()))
        except Exception:
            itens = []
        n = 0
        for texto, valor in itens or []:
            if valor in self._valores:
                continue
            if self.maximo is not None and len(self._valores) >= self.maximo:
                # cheia: o mais antigo sai (como no SolidWorks)
                self._valores.pop(0)
                self.lista.takeItem(0)
            self._valores.append(valor)
            self.lista.addItem(texto)
            n += 1
        if n:
            self._atualizar_rotulo()
            self.mudou.emit()
        return n

    def remover_valor(self, valor):
        if valor in self._valores:
            i = self._valores.index(valor)
            self._valores.pop(i)
            self.lista.takeItem(i)
            self._atualizar_rotulo()
            self.mudou.emit()

    def limpar(self):
        self._valores = []
        self.lista.clear()
        self._atualizar_rotulo()
        self.mudou.emit()

    def valores(self):
        return list(self._valores)

    def pronta(self):
        return len(self._valores) >= self.minimo

    def _atualizar_rotulo(self):
        n = len(self._valores)
        falta = max(self.minimo - n, 0)
        extra = (" — falta %d" % falta) if falta else " ✓"
        self.rotulo.setText("%s (%d)%s" % (self.titulo, n, extra))

    def definir_ativa(self, on):
        self.ativa = bool(on)
        self.setProperty("ativa", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, ev):
        painel = self.parent()
        while painel is not None and not hasattr(painel, "ativar_caixa"):
            painel = painel.parent()
        if painel is not None:
            painel.ativar_caixa(self)
        super().mousePressEvent(ev)

    def keyPressEvent(self, ev):
        if ev.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            r = self.lista.currentRow()
            if 0 <= r < len(self._valores):
                self.remover_valor(self._valores[r])
                return
        super().keyPressEvent(ev)


class Formulario(QtWidgets.QWidget):
    """Conteúdo do painel: cabeçalho, mensagem e seções."""

    def __init__(self, titulo, icone_cmd=None, ajuda="", parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoPainel")
        self.setStyleSheet(qss())
        self.setWindowTitle(titulo)
        if icone_cmd:
            try:
                self.setWindowIcon(QtGui.QIcon(icone_cmd) if isinstance(icone_cmd, str) else icone_cmd)
            except Exception:
                pass
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(6, 6, 6, 6)
        self.lay.setSpacing(6)
        self.mensagem = Mensagem(ajuda)
        self.lay.addWidget(self.mensagem)
        self.caixas = []
        self._fim = QtWidgets.QWidget()

    def secao(self, titulo, icone_nome=None, aberta=True):
        s = Secao(titulo, icone_nome, aberta)
        self.lay.addWidget(s)
        return s

    def caixa(self, secao, *args, **kw):
        c = CaixaSelecao(*args, **kw)
        secao.widget(c)
        self.caixas.append(c)
        if len(self.caixas) == 1:
            c.definir_ativa(True)
        return c

    def fechar_layout(self):
        self.lay.addStretch(1)

    def ativar_caixa(self, alvo):
        for c in self.caixas:
            c.definir_ativa(c is alvo)

    def caixa_ativa(self):
        for c in self.caixas:
            if c.ativa:
                return c
        return self.caixas[0] if self.caixas else None


# ----------------------------------------------------------------------------------- painel
class PainelTarefa:
    """Base dos painéis de tarefa do Prumo.

    Subclasses montam self.form (Formulario) em montar(), dizem o que falta em pendencia() e
    fazem o trabalho em executar() (dentro de uma transação: Desfazer desfaz tudo de uma vez).
    """

    titulo = "Prumo 3D"
    ajuda = ""
    icone_cmd = None
    texto_ok = "OK"

    def __init__(self):
        self.form = Formulario(self.titulo, self.icone_cmd, self.ajuda)
        self.montar()
        self.form.fechar_layout()
        self._observando = False
        for c in self.form.caixas:
            c.mudou.connect(self.atualizar)
        self._preencher_com_selecao()
        self.atualizar()

    # ---- para as subclasses
    def montar(self):
        pass

    def pendencia(self):
        """Texto do que falta (None = pode executar)."""
        for c in self.form.caixas:
            if not c.pronta():
                return "Selecione: %s." % c.titulo.lower()
        return None

    def executar(self):
        raise NotImplementedError

    # ---- seleção
    def _preencher_com_selecao(self):
        for s in FreeCADGui.Selection.getSelectionEx("", 0):
            for obj, els, caminhos in agrupar_selecao(s.Object, s.SubElementNames):
                self.distribuir(obj, els, s.Object, caminhos)

    def distribuir(self, obj, subnomes=(), raiz=None, caminhos=None):
        """Seleção nova vai para a caixa ativa; se ela não aceitar, tenta as outras.

        obj/subnomes: o objeto dono do elemento e o nome curto ("Face3"), como em
        getSelection(); raiz/caminhos: o objeto do topo e o caminho completo
        ("Parte.Corpo.Face3"), para os filtros marcados com caminho_completo = True.
        """
        ativa = self.form.caixa_ativa()
        ordem = ([ativa] if ativa else []) + [c for c in self.form.caixas if c is not ativa]
        for c in ordem:
            if getattr(c.filtro, "caminho_completo", False) and raiz is not None:
                n = c.aceitar(raiz, caminhos if caminhos is not None else subnomes)
            else:
                n = c.aceitar(obj, subnomes)
            if n:
                return c
        return None

    # observador de seleção do FreeCAD
    def _vivo(self):
        try:
            import shiboken6 as shiboken
        except ImportError:  # pragma: no cover
            import shiboken2 as shiboken
        try:
            return getattr(self, "form", None) is not None and shiboken.isValid(self.form)
        except Exception:
            return False

    def addSelection(self, doc, obj, sub, pnt):
        # painel fechado sem accept/reject (ex.: closeDialog): deixa de observar
        if not self._vivo():
            QtCore.QTimer.singleShot(0, self._parar)
            return
        if getattr(self, "_ignorar_selecao", False):
            return
        try:
            raiz = FreeCAD.getDocument(doc).getObject(obj)
        except Exception:
            return
        if raiz is not None:
            try:
                for o, els, caminhos in agrupar_selecao(raiz, (sub,) if sub else ()):
                    self.distribuir(o, els, raiz, caminhos)
            except (RuntimeError, AttributeError):
                QtCore.QTimer.singleShot(0, self._parar)

    def selecionar_sem_preencher(self, objs):
        """Seleciona na tela sem que a seleção vá para as caixas do painel."""
        self._ignorar_selecao = True
        try:
            FreeCADGui.Selection.clearSelection()
            for o in objs:
                FreeCADGui.Selection.addSelection(o)
        finally:
            self._ignorar_selecao = False

    def setSelection(self, doc):
        pass

    def removeSelection(self, doc, obj, sub):
        pass

    def clearSelection(self, doc):
        pass

    def atualizar(self):
        falta = self.pendencia()
        if falta:
            self.form.mensagem.mostrar(falta, "info")
        else:
            self.form.mensagem.mostrar(self.pronto_texto(), "ok")

    def pronto_texto(self):
        return "Pronto. Confira os valores e clique em OK."

    # ---- painel de tarefas do FreeCAD
    def mostrar(self):
        """Abre no painel de tarefas. Outro painel do Prumo aberto é cancelado; uma tarefa do
        FreeCAD em andamento (edição de esboço, extrusão...) não é fechada à força: avisa e não abre."""
        if FreeCADGui.Control.activeDialog():
            anterior = _ATIVO.get("painel")
            if anterior is not None and anterior is not self and anterior._vivo():
                try:
                    anterior.reject()
                except Exception:
                    pass
                FreeCADGui.Control.closeDialog()
            else:
                self.aberto = False
                msg = ("Há uma tarefa aberta no painel de tarefas. Termine (OK) ou cancele essa tarefa "
                       "antes de abrir \"%s\"." % self.titulo)
                FreeCAD.Console.PrintWarning("Prumo: %s\n" % msg)
                try:   # não modal: não trava quem chamou
                    caixa = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Information, self.titulo, msg,
                                                  QtWidgets.QMessageBox.Ok, FreeCADGui.getMainWindow())
                    caixa.setAttribute(QtCore.Qt.WA_DeleteOnClose)
                    caixa.show()
                    _ATIVO["aviso"] = caixa
                except Exception:
                    pass
                self.close()
                return self
        # seleção sem resolver (objeto do topo + caminho), igual à lida ao abrir o painel
        FreeCADGui.Selection.addObserver(self, 0)
        self._observando = True
        FreeCADGui.Control.showDialog(self)
        _ATIVO["painel"] = self
        self.aberto = True
        return self

    def _parar(self):
        if self._observando:
            try:
                FreeCADGui.Selection.removeObserver(self)
            except Exception:
                pass
            self._observando = False

    def getStandardButtons(self):
        def v(b):
            return b.value if hasattr(b, "value") else int(b)
        return v(QtWidgets.QDialogButtonBox.Ok) | v(QtWidgets.QDialogButtonBox.Cancel)

    def accept(self):
        falta = self.pendencia()
        if falta:
            self.form.mensagem.mostrar(falta, "erro")
            return False
        doc = FreeCAD.ActiveDocument
        if doc is not None:
            doc.openTransaction(self.titulo)
        try:
            self.resultado = self.executar()
        except Exception as ex:
            if doc is not None:
                doc.abortTransaction()
            self.form.mensagem.mostrar(str(ex), "erro")
            return False
        if doc is not None:
            doc.commitTransaction()
            doc.recompute()
        self._parar()
        return True      # o FreeCAD fecha o painel

    def reject(self):
        self._parar()
        return True

    def fechar(self):
        try:
            FreeCADGui.Control.closeDialog()
        except Exception:
            pass

    def close(self):
        """Descarta o painel sem executar (uso fora do painel de tarefas, como nos testes)."""
        self._parar()
        try:
            self.form.deleteLater()
        except RuntimeError:
            pass
