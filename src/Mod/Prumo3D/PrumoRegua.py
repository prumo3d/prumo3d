# SPDX-License-Identifier: LGPL-2.1-or-later
"""Régua de histórico do Corpo (rollback bar), como no ZW3D e no SolidWorks.

Painel lateral com as operações do Corpo ativo, em ordem, e uma régua que se arrasta entre elas.
A régua define a ponta (Tip) do Corpo: o modelo é mostrado como estava naquele ponto, as operações
abaixo da régua ficam em cinza e as novas operações entram logo depois dela. Voltar a régua para o
fim restaura o modelo completo. Cada movimento é uma transação (Desfazer volta a régua).

A lógica (posições, ponta, visibilidade) fica em funções sem interface, para os testes.
"""
import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
_estado = {"dock": None}


# ======================================================================== lógica
def eh_solida(o):
    """Operação que pode ser a ponta do Corpo (feature sólida do PartDesign)."""
    try:
        return o.isDerivedFrom("PartDesign::Feature")
    except Exception:
        return False


def itens(corpo):
    """Objetos do histórico do Corpo, na ordem (esboços, referências e operações)."""
    return [o for o in corpo.Group if not o.isDerivedFrom("App::Origin")]


def posicao_da_ponta(corpo):
    """Quantos itens do histórico ficam acima da régua (0 = régua no topo, Corpo vazio)."""
    ls = itens(corpo)
    tip = corpo.Tip
    if tip is None or tip not in ls:
        return 0 if tip is None and any(eh_solida(o) for o in ls) else len(ls)
    k = ls.index(tip) + 1
    # itens não sólidos logo após a ponta (esboço da próxima operação) continuam acima da régua
    # só se não houver sólido depois deles; a régua fica colada na ponta
    return k


def ponta_para(corpo, pos):
    """Ponta do Corpo para a régua na posição pos: o último sólido acima dela (None se nenhum)."""
    ls = itens(corpo)
    pos = max(0, min(pos, len(ls)))
    for o in reversed(ls[:pos]):
        if eh_solida(o):
            return o
    return None


def mover_regua(corpo, pos, transacao=True):
    """Põe a régua na posição pos (0..len(itens)). Retorna a nova ponta (ou None)."""
    doc = corpo.Document
    ls = itens(corpo)
    pos = max(0, min(int(pos), len(ls)))
    nova = ponta_para(corpo, pos)
    if nova is corpo.Tip:
        return nova
    if transacao:
        doc.openTransaction("Régua de histórico")
    try:
        corpo.Tip = nova
        if FreeCAD.GuiUp:
            # a régua assenta logo abaixo da nova ponta: o que fica abaixo dela (inclusive esboços) some
            _visibilidade(corpo, nova, ls.index(nova) + 1 if nova is not None else 0)
        doc.recompute()
    except Exception:
        if transacao:
            doc.abortTransaction()
        raise
    if transacao:
        doc.commitTransaction()
    return nova


def _visibilidade(corpo, ponta, pos):
    """Como o PartDesign: só a ponta aparece; o que fica abaixo da régua some."""
    ls = itens(corpo)
    for k, o in enumerate(ls):
        vo = getattr(o, "ViewObject", None)
        if vo is None:
            continue
        try:
            if eh_solida(o):
                vo.Visibility = o is ponta
            elif k >= pos and vo.Visibility:
                vo.Visibility = False
        except Exception:
            pass


def ate_o_fim(corpo, transacao=True):
    return mover_regua(corpo, len(itens(corpo)), transacao)


def corpo_ativo():
    """Corpo ativo da vista, ou o Corpo do objeto selecionado."""
    if not FreeCAD.GuiUp:
        return None
    import FreeCADGui
    try:
        v = FreeCADGui.ActiveDocument.ActiveView
        c = v.getActiveObject("pdbody")
        if c is not None:
            return c
    except Exception:
        pass
    try:
        for o in FreeCADGui.Selection.getSelection():
            if o.isDerivedFrom("PartDesign::Body"):
                return o
            for p in o.InList:
                if p.isDerivedFrom("PartDesign::Body"):
                    return p
    except Exception:
        pass
    doc = FreeCAD.ActiveDocument
    if doc is not None:
        cs = [o for o in doc.Objects if o.isDerivedFrom("PartDesign::Body")]
        if len(cs) == 1:
            return cs[0]
    return None


# ======================================================================== interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    import PrumoEstilo

    QSS = """
    #SwRegua { background: #FFFFFF; }
    #SwRegua QLabel#SwReguaTit { color: #003A70; font-weight: 700; }
    #SwRegua QLabel#SwReguaSub { color: #5B6876; font-size: 8.5pt; }
    #SwRegua QListWidget { border: 1px solid #DCE4EC; border-radius: 6px; background: #FFFFFF; }
    #SwRegua QToolButton { border: 1px solid #DCE4EC; border-radius: 5px; padding: 3px 7px; background: #F5F8FC; }
    #SwRegua QToolButton:hover { background: #E8F0F8; }
    """
    COR_REGUA = "#F7BE00"
    COR_ABAIXO = "#9AA7B4"

    class ListaHistorico(QtWidgets.QListWidget):
        """Lista com a régua como um item arrastável (só a régua se move)."""
        regua_solta = QtCore.Signal(int)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
            self.setDefaultDropAction(QtCore.Qt.MoveAction)
            self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        def dropEvent(self, ev):
            item = self.currentItem()
            if item is None or not item.data(QtCore.Qt.UserRole + 1):
                ev.ignore()
                return
            super().dropEvent(ev)
            pos = self.row(item)
            self.regua_solta.emit(pos)

    class Regua(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("SwRegua")
            self.setStyleSheet(PrumoEstilo.tema(QSS))
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(6, 6, 6, 6)
            lay.setSpacing(5)
            self.tit = QtWidgets.QLabel("Nenhum corpo ativo")
            self.tit.setObjectName("SwReguaTit")
            self.sub = QtWidgets.QLabel("Arraste a régua amarela para recuar o modelo.")
            self.sub.setObjectName("SwReguaSub")
            self.sub.setWordWrap(True)
            lay.addWidget(self.tit)
            lay.addWidget(self.sub)
            self.lista = ListaHistorico()
            self.lista.regua_solta.connect(self.mover)
            self.lista.itemDoubleClicked.connect(self._duplo)
            self.lista.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.lista.customContextMenuRequested.connect(self._menu)
            self.lista.setMinimumHeight(170)
            lay.addWidget(self.lista, 1)
            bl = QtWidgets.QHBoxLayout()
            bl.setSpacing(4)
            self.botoes = {}
            for chave, texto, dica in (("inicio", "⏮", "Régua no início (corpo vazio)"),
                                       ("menos", "◀", "Recuar uma operação"),
                                       ("mais", "▶", "Avançar uma operação"),
                                       ("fim", "⏭", "Régua no fim (modelo completo)")):
                b = QtWidgets.QToolButton()
                b.setText(texto)
                b.setToolTip(dica)
                b.clicked.connect(lambda _c=False, k=chave: self._botao(k))
                bl.addWidget(b)
                self.botoes[chave] = b
            bl.addStretch(1)
            lay.addLayout(bl)
            self._corpo_nome = None
            self._doc_nome = None
            self._assin = None
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(700)
            self.timer.timeout.connect(self.atualizar)
            self.timer.start()
            self.atualizar()

        # ---- estado
        def corpo(self):
            doc = FreeCAD.ActiveDocument
            if doc is None:
                return None
            c = corpo_ativo()
            if c is not None:
                self._corpo_nome, self._doc_nome = c.Name, doc.Name
                return c
            if self._corpo_nome and self._doc_nome == doc.Name:
                o = doc.getObject(self._corpo_nome)
                if o is not None and o.isDerivedFrom("PartDesign::Body"):
                    return o
            return None

        def _assinatura(self, c):
            if c is None:
                return None
            return (c.Document.Name, c.Name, c.Label, tuple(o.Name for o in itens(c)),
                    tuple(o.Label for o in itens(c)), c.Tip.Name if c.Tip else None)

        def atualizar(self, force=False):
            try:
                c = self.corpo()
            except Exception:
                c = None
            a = self._assinatura(c)
            if a == self._assin and not force:
                return
            self._assin = a
            self.lista.clear()
            if c is None:
                self.tit.setText("Nenhum corpo ativo")
                self.sub.setText("Ative um corpo (duplo clique na árvore) para ver o histórico.")
                for b in self.botoes.values():
                    b.setEnabled(False)
                return
            for b in self.botoes.values():
                b.setEnabled(True)
            ls = itens(c)
            pos = posicao_da_ponta(c)
            self.tit.setText(c.Label)
            n_abaixo = sum(1 for o in ls[pos:] if eh_solida(o))
            if n_abaixo:
                self.sub.setText("Modelo recuado: %d operação(ões) abaixo da régua não entram. Novas operações "
                                 "entram no ponto da régua." % n_abaixo)
            else:
                self.sub.setText("Modelo completo. Arraste a régua amarela para recuar.")
            for k, o in enumerate(ls):
                if k == pos:
                    self._item_regua()
                it = QtWidgets.QListWidgetItem(o.Label)
                try:
                    it.setIcon(o.ViewObject.Icon)
                except Exception:
                    pass
                it.setData(QtCore.Qt.UserRole, o.Name)
                it.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                if k >= pos:
                    it.setForeground(QtGui.QBrush(QtGui.QColor(COR_ABAIXO)))
                    f = it.font()
                    f.setItalic(True)
                    it.setFont(f)
                self.lista.addItem(it)
            if pos >= len(ls):
                self._item_regua()

        def _item_regua(self):
            it = QtWidgets.QListWidgetItem("▬▬▬▬  régua  ▬▬▬▬")
            it.setData(QtCore.Qt.UserRole + 1, True)
            it.setTextAlignment(QtCore.Qt.AlignCenter)
            it.setForeground(QtGui.QBrush(QtGui.QColor("#4D3B00")))
            it.setBackground(QtGui.QBrush(QtGui.QColor(COR_REGUA)))
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            it.setToolTip("Arraste para cima ou para baixo")
            it.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled)
            self.lista.addItem(it)
            # faixa amarela desenhada por cima (a folha de estilo do tema não deixa o item ter fundo)
            faixa = QtWidgets.QLabel("arraste a régua")
            faixa.setAlignment(QtCore.Qt.AlignCenter)
            faixa.setStyleSheet(PrumoEstilo.tema(
                "background: %s; color: #4D3B00; font-weight: 700; font-size: 8pt; border-radius: 4px;"
                " border: 1px solid #C99A00; margin: 2px 2px;" % COR_REGUA))
            faixa.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            it.setSizeHint(QtCore.QSize(10, 24))
            self.lista.setItemWidget(it, faixa)
            return it

        # ---- ações
        def mover(self, pos):
            c = self.corpo()
            if c is None:
                return None
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                nova = mover_regua(c, pos)
            except Exception as ex:
                FreeCAD.Console.PrintError("Prumo: régua de histórico: %s\n" % ex)
                nova = None
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            self.atualizar(force=True)
            return nova

        def _botao(self, chave):
            c = self.corpo()
            if c is None:
                return
            n = len(itens(c))
            pos = posicao_da_ponta(c)
            sol = [k + 1 for k, o in enumerate(itens(c)) if eh_solida(o)]
            if chave == "inicio":
                alvo = 0
            elif chave == "fim":
                alvo = n
            elif chave == "menos":
                antes = [p for p in sol if p < pos]      # sólidos acima da ponta atual
                alvo = antes[-1] if antes else 0
            else:
                depois = [p for p in sol if p > pos]
                alvo = depois[0] if depois else n
            self.mover(alvo)

        def _linha_para_pos(self, item):
            """Posição da régua logo depois do item clicado (descontando a linha da régua)."""
            linha = self.lista.row(item)
            regua = next(i for i in range(self.lista.count())
                         if self.lista.item(i).data(QtCore.Qt.UserRole + 1))
            return linha + 1 if linha < regua else linha

        def _duplo(self, item):
            if item.data(QtCore.Qt.UserRole + 1):
                return
            self.mover(self._linha_para_pos(item))

        def _menu(self, p):
            item = self.lista.itemAt(p)
            if item is None or item.data(QtCore.Qt.UserRole + 1):
                return
            m = QtWidgets.QMenu(self)
            a1 = m.addAction("Recuar a régua até aqui")
            a2 = m.addAction("Régua no fim (modelo completo)")
            r = m.exec_(self.lista.viewport().mapToGlobal(p))
            if r is a1:
                self.mover(self._linha_para_pos(item))
            elif r is a2:
                self._botao("fim")

    def mostrar(ativar=True):
        mw = FreeCADGui.getMainWindow()
        dock = _estado["dock"]
        vivo = False
        try:
            vivo = dock is not None and dock.objectName() == "PrumoReguaHistorico"
        except RuntimeError:
            vivo = False
        if not vivo:
            for velho in mw.findChildren(QtWidgets.QDockWidget, "PrumoReguaHistorico"):
                velho.setParent(None)
                velho.deleteLater()
            dock = QtWidgets.QDockWidget("Histórico do corpo", mw)
            dock.setObjectName("PrumoReguaHistorico")
            dock.setWidget(Regua(dock))
            mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
            modelo = None
            for d in mw.findChildren(QtWidgets.QDockWidget):
                if d.windowTitle() in ("Modelo", "Model", "Combo View", "Vista combinada"):
                    modelo = d
                    break
            if modelo is not None and not modelo.isFloating():
                mw.splitDockWidget(modelo, dock, QtCore.Qt.Vertical)
                h = max(400, modelo.height() + dock.height())
                mw.resizeDocks([modelo, dock], [int(h * 0.55), int(h * 0.45)], QtCore.Qt.Vertical)
            dock.visibilityChanged.connect(_lembrar)
            _estado["dock"] = dock
        if ativar:
            dock.show()
            dock.raise_()
        dock.widget().atualizar(force=True)
        return dock

    def _lembrar(visivel):
        FreeCAD.ParamGet(PARAM).SetBool("ReguaHistorico", bool(visivel))

    def ao_trocar_bancada(nome):
        """Abre a régua na bancada Peça, se o usuário não a fechou antes."""
        try:
            if nome == "PartDesignWorkbench" and FreeCAD.ParamGet(PARAM).GetBool("ReguaHistorico", True):
                QtCore.QTimer.singleShot(300, lambda: mostrar(True))
        except Exception:
            pass

    class CmdRegua:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("regua_historico.svg"), "MenuText": "Régua de histórico",
                    "ToolTip": "Mostra o histórico do corpo com a régua: arraste para recuar o modelo até uma "
                               "operação e inserir novas operações naquele ponto (como no ZW3D e no SolidWorks)"}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            dock = _estado["dock"]
            try:
                aberto = dock is not None and dock.isVisible()
            except RuntimeError:
                aberto = False
            if aberto:
                dock.hide()
            else:
                mostrar(True)
