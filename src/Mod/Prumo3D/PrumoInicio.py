# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tela inicial Prumo: cartões de "Novo projeto" e arquivos recentes com miniatura."""
import os
import zipfile

import FreeCAD
import PrumoEstilo
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "Resources", "icons", "prumo_64.png")
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
TITLE = "Início"

QSS = """
#PrumoInicio { background: #F4F7FB; }
#PrumoInicio QLabel { background: transparent; }
#SwTitulo { color: #003A70; font-size: 18pt; font-weight: 700; }
#SwSub { color: #5B6876; font-size: 10pt; }
#SwSecao { color: #003A70; font-size: 12pt; font-weight: 700; padding-top: 6px; }
#SwSecaoSub { color: #6B7785; font-size: 9pt; }
#SwCard { background: #FFFFFF; border: 1px solid #DCE3EC; border-radius: 8px; }
#SwCard:hover { border-color: #7FA3C9; background: #FBFCFE; }
#PrumoInicio #SwIconBox { background: #EEF2F8; border-radius: 6px; }
#SwCardTitulo { color: #003A70; font-size: 10.5pt; font-weight: 700; }
#SwCardTexto { color: #5B6876; font-size: 9pt; }
#SwVazio { color: #8A96A3; font-size: 9pt; }
#SwRodape { color: #8A96A3; font-size: 8.5pt; }
#PrumoInicio QCheckBox { color: #5B6876; font-size: 9pt; }
#PrumoInicio QScrollArea { border: none; background: transparent; }
"""

NOVOS = [
    ("PartDesign_Body", "Peça", "Modelagem de peça sólida por esboços e operações.", "peca"),
    ("Geoassembly", "Montagem", "Una peças com juntas e monte o conjunto.", "montagem"),
    ("TechDraw_PageDefault", "Desenho técnico", "Folha com vistas, cotas e legenda.", "desenho"),
    ("Sketcher_NewSketch", "Esboço", "Perfil 2D com restrições geométricas.", "esboco"),
    ("Spreadsheet", "Planilha", "Parâmetros e tabelas ligados ao modelo.", "planilha"),
    ("document-open", "Abrir arquivo", "Abra um projeto .FCStd, STEP, IGES, STL…", "abrir"),
]

# Ajuda: os três caminhos para aprender (abaixo de Novo projeto)
AJUDA = [
    ("ajuda_peca.svg", "Tutorial da primeira peça", "Primeira vez no Prumo 3D? Esboço, extrusão, furo e folha em "
                                                     "10 passos.", lambda: _abrir_tutorial("peca")),
    ("ajuda_estrutura.svg", "Tutorial da estrutura soldada", "Perfis, cantos, reforços e placas de base em 9 "
                                                             "passos.", lambda: _abrir_tutorial("estrutura")),
    ("ajuda_migracao.svg", "Vem do SolidWorks ou do ZW3D?", "Veja onde fica cada comando que você já usa.",
     lambda: _abrir_guia_migracao()),
]


def _icone_arquivo(nome, size):
    p = os.path.join(HERE, "Resources", "icons", nome)
    dpr = max(QtWidgets.QApplication.instance().devicePixelRatio(), 1)
    pm = QtGui.QIcon(p).pixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    return pm


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def _icon_path(name):
    d = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Bitmaps").GetString("CustomPathPrumo", "")
    p = os.path.join(d, name + ".svg") if d else ""
    return p if os.path.isfile(p) else None


def _icon(name, size):
    p = _icon_path(name)
    icon = QtGui.QIcon(p) if p else FreeCADGui.getIcon(name) if hasattr(FreeCADGui, "getIcon") else QtGui.QIcon()
    dpr = QtWidgets.QApplication.instance().devicePixelRatio()
    dpr = max(dpr, 1)
    pm = icon.pixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    return pm


def _thumb(path, size):
    try:
        with zipfile.ZipFile(path) as z:
            data = z.read("thumbnails/Thumbnail.png")
        img = QtGui.QImage.fromData(data)
        if img.isNull():
            return None
        dpr = max(QtWidgets.QApplication.instance().devicePixelRatio(), 1)
        pm = QtGui.QPixmap.fromImage(img).scaled(int(size * dpr), int(size * dpr), QtCore.Qt.KeepAspectRatio,
                                                 QtCore.Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        return pm
    except Exception:
        return None


# ---------------------------------------------------------------- ações
def _abrir_guia_migracao():
    try:
        import PrumoGuiaMigracao
        PrumoGuiaMigracao.mostrar()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: guia de migração indisponível: {}\n".format(exc))


def _abrir_tutorial(chave="peca"):
    try:
        import PrumoTutorial
        PrumoTutorial.mostrar(chave)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tutorial indisponível: {}\n".format(exc))


def novo_documento():
    """Documento novo como o Arquivo → Novo do FreeCAD.

    O comando Std_New, além de criar o documento, põe a vista na orientação e na escala
    padrão (isométrica, ~100 mm). Criar só com FreeCAD.newDocument() deixava a câmera de
    fábrica (vista de topo mostrando ~4 mm em volta da origem): ao pedir um esboço, os
    planos da origem (de 8 a 62 mm) ficavam fora da tela.
    """
    try:
        FreeCADGui.runCommand("Std_New")
    except Exception:
        FreeCAD.newDocument()


def _new(kind):
    if kind == "abrir":
        FreeCADGui.runCommand("Std_Open")
        return
    wb, cmd = {
        "peca": ("PartDesignWorkbench", "PartDesign_Body"),
        "montagem": ("AssemblyWorkbench", "Assembly_CreateAssembly"),
        "desenho": ("TechDrawWorkbench", "TechDraw_PageDefault"),
        "esboco": ("SketcherWorkbench", "Sketcher_NewSketch"),
        "planilha": ("SpreadsheetWorkbench", "Spreadsheet_CreateSheet"),
    }[kind]
    novo_documento()
    try:
        FreeCADGui.activateWorkbench(wb)
    except Exception:
        pass
    QtCore.QTimer.singleShot(150, lambda: _run(cmd))
    try:  # a bancada pode já estar ativa (sem sinal de troca): leva a faixa à aba certa
        import PrumoRibbon
        rib = PrumoRibbon._state.get("ribbon")
        if rib is not None:
            rib.sync_workbench(wb)
    except Exception:
        pass


EXEMPLOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "exemplos")
EXEMPLOS = [
    ("Exemplo_Suporte_com_folha_ABNT.FCStd", "Peça com folha ABNT",
     "Suporte com furos, vistas no 1º diedro, legenda e lista de materiais."),
    ("Exemplo_Estrutura_soldada.FCStd", "Estrutura soldada",
     "Grupos de perfis, cantos de topo, reforços, placas de base e soldas."),
    ("Exemplo_Chapa_dobrada.FCStd", "Chapa dobrada",
     "Perfil U de chapa de 2 mm, pronto para planificar."),
]


def pasta_exemplos_usuario():
    return os.path.join(FreeCAD.getUserAppDataDir(), "Exemplos")


def abrir_exemplo(nome):
    """Abre uma cópia do exemplo na pasta do usuário (a instalação pode ser só leitura e o
    original fica intacto para a próxima vez)."""
    import shutil
    origem = os.path.join(EXEMPLOS_DIR, nome)
    if not os.path.isfile(origem):
        FreeCAD.Console.PrintWarning("Prumo: exemplo não encontrado: {}\n".format(origem))
        return None
    destino_dir = pasta_exemplos_usuario()
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, nome)
    shutil.copyfile(origem, destino)
    for d in FreeCAD.listDocuments().values():
        if os.path.normcase(os.path.abspath(d.FileName or "")) == os.path.normcase(os.path.abspath(destino)):
            FreeCAD.closeDocument(d.Name)
    return FreeCAD.openDocument(destino)


def _run(cmd):
    try:
        FreeCADGui.runCommand(cmd)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: {} indisponível: {}\n".format(cmd, exc))


def _open(path):
    if not os.path.isfile(path):
        QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Arquivo não encontrado",
                                          "O arquivo não existe mais:\n" + path)
        return
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fcstd":
        FreeCAD.openDocument(path)
    else:
        FreeCADGui.open(path)


def _recent():
    g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/RecentFiles")
    out = []
    for i in range(g.GetInt("RecentFiles", 8) or 8):
        p = g.GetString("MRU%d" % i, "")
        if p and p not in out:
            out.append(p)
    return out


# ---------------------------------------------------------------- widgets
class Card(QtWidgets.QFrame):
    def __init__(self, pix, title, text, action, box=48, parent=None):
        super().__init__(parent)
        self.setObjectName("SwCard")
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._action = action
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(16)
        ib = QtWidgets.QLabel()
        ib.setObjectName("SwIconBox")
        ib.setFixedSize(box, box)
        ib.setAlignment(QtCore.Qt.AlignCenter)
        if pix is not None:
            ib.setPixmap(pix)
        lay.addWidget(ib, 0, QtCore.Qt.AlignTop)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        t = QtWidgets.QLabel(title)
        t.setObjectName("SwCardTitulo")
        d = QtWidgets.QLabel(text)
        d.setObjectName("SwCardTexto")
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        col.addStretch(1)
        lay.addLayout(col, 1)
        self.setToolTip(text)

    def mouseReleaseEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton and self.rect().contains(ev.pos()):
            QtCore.QTimer.singleShot(0, self._action)
        super().mouseReleaseEvent(ev)


class InicioPrumo(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoInicio")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(PrumoEstilo.tema(QSS))
        self.setWindowTitle(TITLE)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        outer.addWidget(scroll)
        host = QtWidgets.QWidget()
        host.setObjectName("PrumoInicio")
        host.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        scroll.setWidget(host)
        hl = QtWidgets.QHBoxLayout(host)
        hl.setContentsMargins(32, 28, 32, 28)
        hl.addStretch(1)
        self.body = QtWidgets.QWidget()
        self.body.setMaximumWidth(1120)
        self.body.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        hl.addWidget(self.body, 8)
        hl.addStretch(1)
        self.v = QtWidgets.QVBoxLayout(self.body)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(14)
        self.build()

    def _section(self, title, sub=None):
        t = QtWidgets.QLabel(title)
        t.setObjectName("SwSecao")
        self.v.addSpacing(8)
        self.v.addWidget(t)
        if sub:
            s = QtWidgets.QLabel(sub)
            s.setObjectName("SwSecaoSub")
            self.v.addWidget(s)

    def build(self):
        # cabeçalho
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(14)
        if os.path.isfile(LOGO):
            lg = QtWidgets.QLabel()
            pm = QtGui.QPixmap(LOGO)
            lg.setPixmap(pm.scaled(48, 48, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            head.addWidget(lg, 0, QtCore.Qt.AlignTop)
        tc = QtWidgets.QVBoxLayout()
        tc.setSpacing(0)
        t = QtWidgets.QLabel("Prumo 3D")
        t.setObjectName("SwTitulo")
        s = QtWidgets.QLabel("Projetos mecânicos — escolha por onde começar.")
        s.setObjectName("SwSub")
        tc.addWidget(t)
        tc.addWidget(s)
        head.addLayout(tc, 1)
        self.v.addLayout(head)

        # novo projeto
        self._section("Novo projeto")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, (ic, title, text, kind) in enumerate(NOVOS):
            card = Card(_icon(ic, 32), title, text, (lambda k=kind: _new(k)))
            grid.addWidget(card, i // 3, i % 3)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        self.v.addLayout(grid)

        # ajuda: tutoriais e guia de migração, em cartões como os demais
        self._section("Ajuda")
        ga = QtWidgets.QGridLayout()
        ga.setHorizontalSpacing(14)
        ga.setVerticalSpacing(14)
        self.cartoes_ajuda = []
        for i, (arq, titulo, texto, acao) in enumerate(AJUDA):
            card = Card(_icone_arquivo(arq, 34), titulo, texto, acao)
            self.cartoes_ajuda.append(card)
            ga.addWidget(card, i // 3, i % 3)
        for c in range(3):
            ga.setColumnStretch(c, 1)
        self.v.addLayout(ga)

        # exemplos prontos
        exs = [e for e in EXEMPLOS if os.path.isfile(os.path.join(EXEMPLOS_DIR, e[0]))]
        if exs:
            self._section("Exemplos", "Abra, explore a árvore e altere à vontade: é uma cópia.")
            g3 = QtWidgets.QGridLayout()
            g3.setHorizontalSpacing(14)
            g3.setVerticalSpacing(14)
            fallback = _icon("PartDesign_Body", 30)
            for i, (arq, titulo, texto) in enumerate(exs):
                pix = _thumb(os.path.join(EXEMPLOS_DIR, arq), 46)
                card = Card(pix or fallback, titulo, texto, (lambda a=arq: abrir_exemplo(a)))
                g3.addWidget(card, i // 3, i % 3)
            for c in range(3):
                g3.setColumnStretch(c, 1)
            self.v.addLayout(g3)

        # recentes
        rec = _recent()
        self._section("Arquivos recentes", None if rec else None)
        if not rec:
            e = QtWidgets.QLabel("Nenhum arquivo aberto recentemente.")
            e.setObjectName("SwVazio")
            self.v.addWidget(e)
        else:
            g2 = QtWidgets.QGridLayout()
            g2.setHorizontalSpacing(14)
            g2.setVerticalSpacing(14)
            fallback = _icon("PartDesign_Body", 30)
            for i, path in enumerate(rec[:9]):
                name = os.path.basename(path)
                folder = os.path.dirname(path)
                pix = _thumb(path, 46) if path.lower().endswith(".fcstd") else None
                card = Card(pix or fallback, name, folder, (lambda p=path: _open(p)))
                g2.addWidget(card, i // 3, i % 3)
            for c in range(3):
                g2.setColumnStretch(c, 1)
            self.v.addLayout(g2)

        self.v.addStretch(1)
        foot = QtWidgets.QHBoxLayout()
        cb = QtWidgets.QCheckBox("Mostrar esta tela ao abrir o Prumo 3D")
        cb.setChecked(_params().GetBool("TelaInicial", True))
        cb.toggled.connect(_toggle_tela)
        foot.addWidget(cb)
        foot.addStretch(1)
        r = QtWidgets.QLabel("Software livre · baseado no FreeCAD")
        r.setObjectName("SwRodape")
        foot.addWidget(r)
        self.v.addSpacing(10)
        self.v.addLayout(foot)

    def refresh(self):
        while self.v.count():
            it = self.v.takeAt(0)
            _clear(it)
        self.build()


def _toggle_tela(on):
    _params().SetBool("TelaInicial", on)
    prepare()


def _clear(item):
    w = item.widget()
    if w is not None:
        w.deleteLater()
        return
    lay = item.layout()
    if lay is not None:
        while lay.count():
            _clear(lay.takeAt(0))


# ---------------------------------------------------------------- integração com a área MDI
_state = {"sub": None}


def _mdi():
    mw = FreeCADGui.getMainWindow()
    return mw.findChild(QtWidgets.QMdiArea) if mw else None


def _close_stock_start():
    area = _mdi()
    if area is None:
        return
    for sub in area.subWindowList():
        w = sub.widget()
        cn = w.metaObject().className() if w is not None else ""
        if cn.startswith("StartGui::") or cn == "Gui::StartView":
            sub.close()


def show():
    area = _mdi()
    if area is None:
        return
    sub = _state["sub"]
    try:
        alive = sub is not None and sub.widget() is not None and sub in area.subWindowList()
    except RuntimeError:
        alive = False
    if alive:
        sub.widget().refresh()
        area.setActiveSubWindow(sub)
        return
    w = InicioPrumo()
    sub = area.addSubWindow(w)
    sub.setWindowTitle(TITLE)
    sub.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    p = os.path.join(HERE, "Resources", "icons", "prumo.png")
    if os.path.isfile(p):
        sub.setWindowIcon(QtGui.QIcon(p))
    sub.showMaximized()
    _state["sub"] = sub
    _connect_side()
    _safe(_on_subwindow, sub)


def prepare():
    """Antes da janela terminar de montar: impede a tela inicial padrão de abrir.

    Fechar a tela padrão depois de aberta pode derrubar o FreeCAD (Access violation),
    então desligamos o parâmetro do próprio FreeCAD e guardamos que fomos nós.
    """
    start = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Start")
    if _params().GetBool("TelaInicial", True):
        if start.GetBool("ShowOnStartup", True):
            start.SetBool("ShowOnStartup", False)
            _params().SetBool("StartPadraoDesligadoPelaPrumo", True)
    elif _params().GetBool("StartPadraoDesligadoPelaPrumo", False):
        start.SetBool("ShowOnStartup", True)
        _params().SetBool("StartPadraoDesligadoPelaPrumo", False)


# ---------------------------------------------------------------- barra lateral só no trabalho
SIDE_DOCKS = ("Model", "Tasks", "Combo View", "Tree view", "Property view", "PrumoAparencia",
              "PrumoAssistenteEstrutura", "PrumoAssistenteFEM", "PrumoTutorial", "PrumoGuiaMigracao",
              "PrumoReguaHistorico")
_side = {"connected": False}


def _is_start(sub):
    try:
        return sub is not None and isinstance(sub.widget(), InicioPrumo)
    except RuntimeError:
        return False


def _hidden_names():
    txt = _params().GetString("LateralOcultaPelaPrumo", "")
    return [n for n in txt.split("|") if n]


def _set_hidden_names(names):
    _params().SetString("LateralOcultaPelaPrumo", "|".join(sorted(set(names))))


def _on_subwindow(sub):
    """Esconde Modelo/Tarefas enquanto a tela inicial está na frente; devolve ao sair.

    O que a Prumo escondeu fica gravado nas preferências: o FreeCAD salva o layout
    ao fechar, e a barra voltaria escondida na próxima abertura.
    """
    if not _params().GetBool("OcultarLateralNoInicio", True):
        return
    mw = FreeCADGui.getMainWindow()
    if mw is None:
        return
    docks = [d for d in mw.findChildren(QtWidgets.QDockWidget) if d.objectName() in SIDE_DOCKS]
    hidden = _hidden_names()
    inicio = _is_start(sub)
    # só esconde ao ENTRAR na tela inicial: se o usuário reabrir a árvore com ela na frente
    # (botão Árvore do modelo), o painel fica
    ja_estava = _side.get("no_inicio", False)
    _side["no_inicio"] = inicio
    if inicio and ja_estava:
        # nos primeiros segundos o FreeCAD ainda restaura o arranjo gravado e pode reabrir painéis:
        # continua escondendo; depois disso, um painel reaberto pelo usuário fica
        import time
        if time.time() < _side.get("esconder_ate", 0):
            reabertos = [d.objectName() for d in docks if d.isVisible()]
            for d in docks:
                if d.isVisible():
                    d.hide()
            if reabertos:
                _set_hidden_names(hidden + reabertos)
        return
    if inicio:
        newly = [d.objectName() for d in docks if d.isVisible()]
        for d in docks:
            if d.isVisible():
                d.hide()
        if newly:
            _set_hidden_names(hidden + newly)
    elif hidden:
        for d in docks:
            if d.objectName() in hidden:
                d.show()
        _set_hidden_names([])


def _poll_side():
    area = _mdi()
    if area is None:
        return
    _on_subwindow(area.currentSubWindow())
    try:
        import PrumoPainelLateral
        if PrumoPainelLateral.organizar(no_inicio=bool(_side.get("no_inicio"))):
            return
    except Exception as exc:
        if not _side.get("aviso_painel"):
            _side["aviso_painel"] = True
            FreeCAD.Console.PrintWarning("Prumo: painel lateral: {}\n".format(exc))
    _organizar_lateral()


# ---------------------------------------------------------------- Modelo e Tarefas numa coluna só
# O FreeCAD 1.1 abre Modelo e Tarefas como dois painéis lado a lado. Em notebook isso pede mais largura
# do que a tela tem (a janela tenta crescer e o Windows recusa: "Unable to set geometry"). Aqui os dois
# ficam em abas no mesmo lugar; a aba Tarefas vem para a frente quando um comando abre o painel de
# tarefas e a Modelo volta quando ele fecha.
_lat = {"tarefa": False}


def _docks_laterais(mw):
    ds = {d.objectName(): d for d in mw.findChildren(QtWidgets.QDockWidget)}
    return ds.get("Model") or ds.get("Combo View"), ds.get("Tasks")


def _organizar_lateral():
    if not _params().GetBool("ModeloETarefasEmAbas", True):
        return
    mw = FreeCADGui.getMainWindow()
    if mw is None:
        return
    modelo, tarefas = _docks_laterais(mw)
    if modelo is None or tarefas is None or modelo is tarefas:
        return
    if not _lat.get("juntou") and not modelo.isFloating() and not tarefas.isFloating():
        _lat["juntou"] = True          # uma vez por sessão: se o usuário separar depois, fica separado
        juntos = tarefas in mw.tabifiedDockWidgets(modelo)
        if not juntos:
            area = mw.dockWidgetArea(modelo)
            if mw.dockWidgetArea(tarefas) != area:
                mw.addDockWidget(area, tarefas)
            mw.tabifyDockWidget(modelo, tarefas)
    try:
        ativa = bool(FreeCADGui.Control.activeDialog())
    except Exception:
        ativa = False
    if ativa == _lat["tarefa"]:
        return
    _lat["tarefa"] = ativa
    if _side.get("no_inicio"):
        return
    if ativa:
        if not tarefas.isVisible():
            tarefas.show()
        tarefas.raise_()
    elif modelo.isVisible():
        modelo.raise_()


def esconder_laterais_na_abertura():
    """Antes da tela inicial aparecer: Modelo e Tarefas começam fechados (também na primeira abertura
    depois de instalar, quando o FreeCAD ainda não tem o layout gravado)."""
    if not _params().GetBool("OcultarLateralNoInicio", True) or FreeCAD.listDocuments():
        return
    import time
    _side["esconder_ate"] = time.time() + 10
    mw = FreeCADGui.getMainWindow()
    if mw is None:
        return
    nomes = []
    for d in mw.findChildren(QtWidgets.QDockWidget):
        if d.objectName() in SIDE_DOCKS and d.isVisible():
            d.hide()
            nomes.append(d.objectName())
    if nomes:
        _set_hidden_names(_hidden_names() + nomes)
    _side["no_inicio"] = True


def _connect_side():
    """Acompanha a janela ativa (o sinal subWindowActivated nem sempre chega)."""
    if _side["connected"]:
        return
    t = QtCore.QTimer()
    t.setInterval(400)
    t.timeout.connect(lambda: _safe(_poll_side))
    t.start()
    _side["timer"] = t
    _side["connected"] = True


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tela inicial: {}\n".format(exc))


def startup():
    """Na abertura: mostra a tela inicial Prumo quando não há documento aberto."""
    _connect_side()
    _safe(esconder_laterais_na_abertura)
    if not _params().GetBool("TelaInicial", True):
        return
    if not FreeCAD.listDocuments():
        show()
        # abrir o programa cai na aba Início da faixa (não na bancada de partida, Peça); repete depois
        # que o FreeCAD termina de restaurar a bancada
        for atraso in (0, 1500, 3500):
            QtCore.QTimer.singleShot(atraso, _faixa_no_inicio)


def _faixa_no_inicio():
    """Põe a faixa na aba Início se a tela inicial está na frente e nenhum documento foi aberto."""
    try:
        if FreeCAD.listDocuments():
            return
        area = _mdi()
        sub = area.activeSubWindow() if area is not None else None
        if sub is not None and not _is_start(sub):
            return
        import PrumoRibbon
        rb = PrumoRibbon._state.get("ribbon")
        if rb is not None and rb.tab_index("inicio") >= 0:
            atual = rb._tabs[rb.tabbar.currentIndex()] if rb.tabbar.currentIndex() >= 0 else {}
            # aba sem bancada (Estruturas, Tubulação…) só fica na frente se o usuário clicou nela: não tira
            if atual.get("id") != "inicio" and atual.get("wb") is None:
                return
            rb.select_tab("inicio")
    except Exception as exc:
        FreeCAD.Console.PrintLog("Prumo: faixa no Início: {}\n".format(exc))


class CmdInicio:
    def GetResources(self):
        return {"Pixmap": os.path.join(HERE, "Resources", "icons", "prumo.png"),
                "MenuText": "Tela inicial", "ToolTip": "Abre a tela inicial Prumo"}

    def Activated(self):
        show()

    def IsActive(self):
        return True
