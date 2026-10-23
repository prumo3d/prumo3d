# SPDX-License-Identifier: LGPL-2.1-or-later
"""Painel lateral único do Prumo 3D.

Um painel só à esquerda, com as abas no alto:

    Árvore | Propriedades | <comando ativo>

- Árvore e Propriedades são os painéis "Tree view" e "Property view" do FreeCAD (o Init.py liga os
  dois e desliga o "Modelo", que juntava árvore e propriedades num quadro só).
- A aba do comando (o painel "Tasks") só existe enquanto um comando está aberto: chega com o nome
  do que está sendo editado ("Esboço002", "Extrusão") e some quando ele é concluído ou cancelado,
  devolvendo a aba que estava à frente.
- Sem barra de título em cima de cada painel: a aba é o cabeçalho.

A preferência PainelLateralUnico (Mod/Prumo3D) desligada devolve o arranjo do FreeCAD na próxima
abertura.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"

ARVORE = "Tree view"
PROPRIEDADES = "Property view"
TAREFA = "Tasks"
ORDEM = (ARVORE, PROPRIEDADES, TAREFA)
TITULOS = {ARVORE: "Árvore", PROPRIEDADES: "Propriedades", TAREFA: "Comando"}
LARGURA_TITULO = 18          # caracteres na aba do comando

# Ícones das abas (mesmo traço dos quadros do painel: 24 × 24, linha 1,8)
_SVG = {
    ARVORE: '<path d="M4 5h6M4 12h6M4 19h6M10 5v14M14 8h6M14 16h6"/>',
    PROPRIEDADES: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/>'
                  '<circle cx="10" cy="17" r="2"/>',
    TAREFA: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/>',
}

_estado = {"juntou": False, "ativa": None, "antes": None, "titulo": None, "estilo": None}


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def ligado():
    return _params().GetBool("PainelLateralUnico", True)


def _escuro():
    try:
        import PrumoEstilo
        return PrumoEstilo.escuro()
    except Exception:
        return False


def icone(nome, cor=None):
    """Ícone de traço desenhado a partir do SVG (fica nítido em qualquer escala de tela)."""
    from PySide import QtSvg
    cor = cor or ("#C9D3DD" if _escuro() else "#003A70")
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{}" '
           'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>').format(cor, _SVG[nome])
    r = QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    ic = QtGui.QIcon()
    for lado in (16, 18, 24, 32, 48):
        pm = QtGui.QPixmap(lado, lado)
        pm.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(pm)
        r.render(p)
        p.end()
        ic.addPixmap(pm)
    return ic


def docks(mw=None):
    """{nome: QDockWidget} dos três painéis (os que existirem)."""
    mw = mw or FreeCADGui.getMainWindow()
    if mw is None:
        return {}
    achados = {}
    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName() in ORDEM and d.objectName() not in achados:
            achados[d.objectName()] = d
    return achados


def barra_de_abas(mw=None):
    """A barra de abas (QTabBar da janela principal) que tem a aba Árvore."""
    mw = mw or FreeCADGui.getMainWindow()
    if mw is None:
        return None
    for bar in mw.findChildren(QtWidgets.QTabBar):
        if bar.parent() is not mw:
            continue
        for i in range(bar.count()):
            if bar.tabText(i) == TITULOS[ARVORE]:
                return bar
    return None


# ---------------------------------------------------------------- título da aba do comando
def _cabecalhos_da_tarefa(dock):
    """(texto, ícone) dos cabeçalhos dos quadros do painel de tarefas, na ordem em que aparecem."""
    saida = []
    for b in dock.findChildren(QtWidgets.QToolButton):
        if b.property("class") == "header" and b.text():
            saida.append((b.text(), b.icon()))
    return saida


def titulo_do_comando(dock=None):
    """Nome curto do que está aberto no painel de tarefas e o ícone dele."""
    try:
        gdoc = FreeCADGui.ActiveDocument
        vp = gdoc.getInEdit() if gdoc else None
    except Exception:
        vp = None
    if vp is not None:
        try:
            obj = vp.Object
            texto = obj.Label
            ic = vp.Icon if hasattr(vp, "Icon") else None
            return _curto(texto), ic
        except Exception:
            pass
    if dock is not None:
        cab = _cabecalhos_da_tarefa(dock)
        if cab:
            return _curto(cab[0][0]), cab[0][1]
    return TITULOS[TAREFA], None


def _curto(texto):
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= LARGURA_TITULO else texto[:LARGURA_TITULO - 1].rstrip() + "…"


# ---------------------------------------------------------------- aparência
def estilo_abas():
    esc = _escuro()
    fundo = "#161A20" if esc else "#F5F8FC"
    texto = "#9AA7B4" if esc else "#5B6876"
    ativo = "#E6EEF7" if esc else "#003A70"
    hover = "#222A33" if esc else "#EAF0F6"
    linha = "#2E3742" if esc else "#DCE4EC"
    return (
        "QTabBar {{ background: {fundo}; border: 0; border-bottom: 1px solid {linha}; }}"
        "QTabBar::tab, QTabBar::tab:top {{ background: transparent; color: {texto}; border: 0;"
        " border-bottom: 3px solid transparent; padding: 7px 12px 5px 10px; margin: 0; min-width: 40px;"
        " font-weight: 500; }}"
        "QTabBar::tab:selected, QTabBar::tab:top:selected {{ color: {ativo}; border-bottom: 3px solid #F7BE00;"
        " background: transparent; font-weight: 600; }}"
        "QTabBar::tab:!selected:hover, QTabBar::tab:top:!selected:hover {{ color: {ativo}; background: {hover}; }}"
    ).format(fundo=fundo, texto=texto, ativo=ativo, hover=hover, linha=linha)


def _sem_titulo(d):
    """Tira a barra de título do painel (a aba já diz o que ele é)."""
    if not _params().GetBool("PainelSemTitulo", True):
        return
    atual = d.titleBarWidget()
    if atual is not None and atual.objectName() == "PrumoSemTitulo":
        return
    vazio = QtWidgets.QWidget(d)
    vazio.setObjectName("PrumoSemTitulo")
    vazio.setFixedHeight(0)
    d.setTitleBarWidget(vazio)
    if atual is not None:
        atual.hide()
        atual.deleteLater()


def _nomear(ds):
    for nome in (ARVORE, PROPRIEDADES):
        d = ds.get(nome)
        if d is not None and d.windowTitle() != TITULOS[nome]:
            d.setWindowTitle(TITULOS[nome])
            d.setWindowIcon(icone(nome))


def _icones_das_abas(bar, ds):
    for i in range(bar.count()):
        txt = bar.tabText(i)
        for nome in (ARVORE, PROPRIEDADES):
            if txt == TITULOS[nome]:
                if bar.tabIcon(i).cacheKey() != _estado.get("ic_" + nome, -1):
                    ic = icone(nome)
                    bar.setTabIcon(i, ic)
                    _estado["ic_" + nome] = bar.tabIcon(i).cacheKey()
        tar = ds.get(TAREFA)
        if tar is not None and txt == tar.windowTitle() and _estado.get("ic_tarefa") is not None:
            if bar.tabIcon(i).cacheKey() != _estado.get("ic_tarefa_key", -1):
                bar.setTabIcon(i, _estado["ic_tarefa"])
                _estado["ic_tarefa_key"] = bar.tabIcon(i).cacheKey()


def _estilizar(bar):
    css = estilo_abas()
    if bar.styleSheet() != css:
        bar.setStyleSheet(css)
    if bar.iconSize() != QtCore.QSize(18, 18):
        bar.setIconSize(QtCore.QSize(18, 18))
    if bar.elideMode() != QtCore.Qt.ElideRight:
        bar.setElideMode(QtCore.Qt.ElideRight)


# ---------------------------------------------------------------- arranjo
def _juntar(mw, ds):
    """Uma vez por sessão: os três painéis em abas, à esquerda, na ordem Árvore | Propriedades | comando."""
    arv, prop, tar = ds.get(ARVORE), ds.get(PROPRIEDADES), ds.get(TAREFA)
    if arv is None or prop is None:
        return
    if any(d is not None and d.isFloating() for d in (arv, prop, tar)):
        _estado["juntou"] = True      # o usuário soltou um painel: respeita
        return
    _estado["juntou"] = True
    area = QtCore.Qt.LeftDockWidgetArea
    mw.setTabPosition(area, QtWidgets.QTabWidget.North)
    for d in (arv, prop, tar):
        if d is not None and mw.dockWidgetArea(d) != area:
            mw.addDockWidget(area, d)
    juntos = mw.tabifiedDockWidgets(arv)
    if prop not in juntos:
        mw.tabifyDockWidget(arv, prop)
    if tar is not None and tar not in mw.tabifiedDockWidgets(arv):
        mw.tabifyDockWidget(prop, tar)
    if arv.isVisible():
        arv.raise_()      # começa pela árvore


def _comando(ds, no_inicio):
    """Aba do comando: aparece com o comando, some quando ele fecha."""
    tar = ds.get(TAREFA)
    if tar is None:
        return
    try:
        ativa = bool(FreeCADGui.Control.activeDialog())
    except Exception:
        ativa = False
    if ativa:
        titulo, ic = titulo_do_comando(tar)
        if titulo != tar.windowTitle():
            tar.setWindowTitle(titulo)
        if ic is None or ic.isNull():
            ic = icone(TAREFA)
        if titulo != _estado["titulo"]:
            _estado["titulo"] = titulo
            _estado["ic_tarefa"] = ic
            _estado["ic_tarefa_key"] = -1
    if not ativa and not no_inicio:
        # lembra a aba em uso antes do comando (o FreeCAD já troca de aba ao abrir o comando,
        # antes desta função ver a mudança)
        bar = barra_de_abas()
        if bar is not None and bar.currentIndex() >= 0:
            atual = bar.tabText(bar.currentIndex())
            if atual in (TITULOS[ARVORE], TITULOS[PROPRIEDADES]):
                _estado["antes"] = atual
    if not ativa and not no_inicio and tar.isVisible() and not tar.isFloating():
        tar.hide()        # sem comando não há aba de comando (nem a que o FreeCAD deixa aberta ao montar)
    if ativa == _estado["ativa"]:
        return
    if no_inicio:
        return            # decide quando a tela inicial sair da frente
    _estado["ativa"] = ativa
    if ativa:
        if not tar.isVisible():
            tar.show()
        tar.raise_()
    else:
        _estado["titulo"] = None
        _estado["ic_tarefa"] = None
        if tar.isVisible() and not tar.isFloating():
            tar.hide()
        volta = None
        for nome in (ARVORE, PROPRIEDADES):
            d = ds.get(nome)
            if d is not None and _estado.get("antes") == d.windowTitle():
                volta = d
        volta = volta or ds.get(ARVORE)
        if volta is not None and volta.isVisible():
            volta.raise_()
        tar.setWindowTitle(TITULOS[TAREFA])


def organizar(no_inicio=False):
    """Chamada a cada 400 ms (PrumoInicio): mantém o painel arrumado. Barata quando nada mudou."""
    if not ligado():
        return False
    mw = FreeCADGui.getMainWindow()
    if mw is None:
        return False
    ds = docks(mw)
    if ARVORE not in ds or PROPRIEDADES not in ds:
        return False       # o FreeCAD subiu com o painel "Modelo" (preferência mudou nesta sessão)
    _nomear(ds)
    for d in ds.values():
        _sem_titulo(d)
    if not _estado["juntou"] and not no_inicio:
        _juntar(mw, ds)
    _comando(ds, no_inicio)
    bar = barra_de_abas(mw)
    if bar is not None:
        _estilizar(bar)
        _icones_das_abas(bar, ds)
    return True


def mostrar_propriedades():
    """Leva a aba Propriedades para a frente (usado pelo cartão da seleção e por atalhos)."""
    d = docks().get(PROPRIEDADES)
    if d is not None:
        d.show()
        d.raise_()
    return d
