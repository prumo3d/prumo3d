# SPDX-License-Identifier: LGPL-2.1-or-later
"""Procurar comando: digite parte do nome e Enter roda a ferramenta (como a busca do Fusion e do SolidCraft).

Procura nos rótulos da faixa (em português), no nome do menu e na dica de cada comando, sem ligar para acento
nem maiúscula, e também por sinônimos que quem vem do SolidWorks costuma digitar. Ao rodar, a faixa vai para a
aba da ferramenta, para a pessoa aprender onde ela fica.
"""

import unicodedata


# palavra digitada -> palavras que aparecem no rótulo (para quem vem de outros programas)
SINONIMOS = {
    "mate": "restricao junta", "mates": "restricao junta", "restricao": "junta", "constraint": "restricao",
    "extrude": "extrusao ressalto", "extrusao": "ressalto", "boss": "ressalto", "cut": "corte rebaixo",
    "pocket": "rebaixo", "fillet": "arredondamento", "filete": "arredondamento", "chamfer": "chanfro",
    "pattern": "padrao matriz", "matriz": "padrao", "mirror": "espelhar", "espelho": "espelhar",
    "drawing": "folha desenho", "sheet": "folha", "dimension": "cota", "dimensao": "cota", "medida": "cota medir",
    "bom": "lista materiais", "interference": "interferencia", "explode": "explodida",
    "hole": "furo", "shell": "casca", "revolve": "revolucao", "sweep": "varredura", "loft": "transicao",
    "sketch": "esboco", "plano": "plano referencia", "weld": "solda", "gear": "engrenagem",
    "drive": "mover junta", "rigid": "travar", "rigido": "travar", "concentric": "concentrica",
    "tangent": "tangente", "coincident": "coincidente", "parallel": "paralela",
    # como o pessoal digita (SolidWorks em português, termos de chão de fábrica)
    "ressalto": "extrusao", "base": "extrusao", "nervura": "reforco", "rib": "reforco",
    "referencia": "referencias plano", "datum": "referencias", "pdf": "salvar pdf", "dxf": "exportar dxf",
    "bom": "lista materiais", "lm": "lista materiais", "ldm": "lista materiais", "quantitativo": "lista materiais",
    "carimbo": "folha legenda", "legenda": "folha carimbo", "prancha": "folha", "vista": "vistas paleta",
    "corte": "corte secao", "secao": "corte", "detalhe": "detalhe", "rosca": "rosca furo", "parafuso": "fixador",
    "porca": "fixador", "arruela": "fixador", "solda": "solda cordao", "chapa": "chapa parede dobra",
    "dobra": "dobra aba", "planificar": "planificar", "perfil": "estrutura perfil", "viga": "estrutura",
    "tubo": "tubulacao tubos", "conexao": "tubulacao", "vaso": "vaso pressao", "massa": "massa propriedades",
    "peso": "massa", "medir": "medir", "interferencia": "interferencia", "colisao": "interferencia",
    "explodida": "explodida", "motor": "simulacao", "fem": "simulacao estudo", "tensao": "simulacao",
    "junta": "restricao", "fixar": "fixar peca", "ground": "fixar", "lock": "travar",
}


def normalizar(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.lower().replace("\n", " ").replace("&", "").split())


def indice(tabs=None):
    """[(comando, rótulo, aba_id, aba_rótulo, grupo, texto_de_busca)] de tudo o que está na faixa."""
    if tabs is None:
        import PrumoRibbon
        tabs = PrumoRibbon.TABS
    try:
        import FreeCADGui
        existentes = set(FreeCADGui.listCommands())
    except Exception:
        FreeCADGui, existentes = None, None
    res, vistos = [], set()
    for t in tabs:
        for grupo, itens in t.get("panels", []):
            for item in itens:
                cmd, _tam, rot = item[0], item[1], item[2]
                if cmd in vistos or (existentes is not None and cmd not in existentes):
                    continue
                vistos.add(cmd)
                menu = dica = ""
                if FreeCADGui is not None:
                    try:
                        info = FreeCADGui.Command.get(cmd).getInfo()
                        menu, dica = info.get("menuText", ""), info.get("toolTip", "")
                    except Exception:
                        pass
                rot = " ".join(str(rot).split())
                busca = normalizar(" ".join((rot, menu, t["label"], grupo, dica[:200])))
                res.append((cmd, rot, t["id"], t["label"], grupo, busca))
    return res


def procurar(texto, itens=None, limite=12):
    """Os itens que casam com o texto, os mais certeiros primeiro."""
    q = normalizar(texto)
    if not q:
        return []
    itens = itens if itens is not None else indice()
    palavras = q.split()
    extras = []
    for p in palavras:
        if p in SINONIMOS:
            extras += SINONIMOS[p].split()
    res = []
    for it in itens:
        rot = normalizar(it[1])
        busca = it[5]
        if all(p in busca for p in palavras):
            if rot == q:
                nota = 0
            elif rot.startswith(q):
                nota = 1
            elif all(p in rot for p in palavras):
                nota = 2
            else:
                nota = 4
        elif extras and any(e in rot for e in extras):
            nota = 3
        else:
            continue
        res.append((nota, len(rot), it))
    res.sort(key=lambda x: (x[0], x[1]))
    return [it for _n, _l, it in res[:limite]]


def rodar(item, ribbon=None):
    """Vai para a aba da ferramenta e roda o comando."""
    import FreeCADGui
    cmd, _rot, aba = item[0], item[1], item[2]
    if ribbon is not None:
        try:
            ribbon.select_tab(aba, user=True)
        except Exception:
            pass
    FreeCADGui.runCommand(cmd, 0)


# ------------------------------------------------------------------ janela
try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    class BuscaComandos(QtWidgets.QFrame):
        """Caixinha que abre debaixo do botão da lupa: campo + lista. Enter roda o primeiro (ou o marcado)."""

        def __init__(self, ribbon=None, parent=None):
            super().__init__(parent, QtCore.Qt.Popup)
            self.setObjectName("PrumoBusca")
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.ribbon = ribbon
            self._itens = None
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(8, 8, 8, 8)
            lay.setSpacing(6)
            self.campo = QtWidgets.QLineEdit()
            self.campo.setPlaceholderText("Procurar comando (ex.: furo, tangente, cota)")
            self.campo.setClearButtonEnabled(True)
            lay.addWidget(self.campo)
            self.lista = QtWidgets.QListWidget()
            self.lista.setMinimumWidth(380)
            self.lista.setMinimumHeight(260)
            self.lista.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.lista.setTextElideMode(QtCore.Qt.ElideRight)
            lay.addWidget(self.lista)
            self.dica = QtWidgets.QLabel("Enter roda · ↑↓ escolhe · Esc fecha")
            self.dica.setStyleSheet("color: #6B7785;")
            lay.addWidget(self.dica)
            self.campo.textChanged.connect(self.filtrar)
            self.campo.returnPressed.connect(self.rodar_marcado)
            self.lista.itemActivated.connect(lambda _i: self.rodar_marcado())
            self.campo.installEventFilter(self)
            try:
                import PrumoEstilo
                escuro = PrumoEstilo.escuro()
            except Exception:
                escuro = False
            fundo, borda, texto = ("#1F262E", "#3A4450", "#E6EBF0") if escuro else ("#FFFFFF", "#C9D3DE", "#1E2A38")
            self.setStyleSheet(
                "QFrame#PrumoBusca { background: %s; border: 1px solid %s; border-radius: 8px; }"
                "QLineEdit { padding: 6px 8px; border: 1px solid %s; border-radius: 6px; color: %s; }"
                "QLineEdit:focus { border: 2px solid #003A70; }"
                "QListWidget { border: none; background: transparent; color: %s; }"
                "QListWidget::item { padding: 5px 4px; border-radius: 4px; }"
                "QListWidget::item:selected { background: #FFF4CC; color: #1E2A38; }"
                % (fundo, borda, borda, texto, texto))

        def itens(self):
            if self._itens is None:
                self._itens = indice()
            return self._itens

        def filtrar(self, texto):
            self.lista.clear()
            for it in procurar(texto, self.itens()):
                li = QtWidgets.QListWidgetItem("%s   —   %s › %s" % (it[1], it[3], it[4]))
                try:
                    import FreeCADGui
                    pix = FreeCADGui.Command.get(it[0]).getInfo().get("pixmap", "")
                    if pix:
                        li.setIcon(QtGui.QIcon(pix) if pix.endswith(".svg") or "/" in pix or "\\" in pix
                                   else FreeCADGui.getIcon(pix))
                except Exception:
                    pass
                li.setData(QtCore.Qt.UserRole, it)
                self.lista.addItem(li)
            if self.lista.count():
                self.lista.setCurrentRow(0)
            self.dica.setText("Enter roda · ↑↓ escolhe · Esc fecha" if self.lista.count() or not texto
                              else "Nada com esse nome. Tente outra palavra.")

        def eventFilter(self, obj, ev):
            if obj is self.campo and ev.type() == QtCore.QEvent.KeyPress:
                if ev.key() in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up):
                    r = self.lista.currentRow() + (1 if ev.key() == QtCore.Qt.Key_Down else -1)
                    if 0 <= r < self.lista.count():
                        self.lista.setCurrentRow(r)
                    return True
            return super().eventFilter(obj, ev)

        def rodar_marcado(self):
            li = self.lista.currentItem()
            if li is None:
                return None
            it = li.data(QtCore.Qt.UserRole)
            self.hide()
            QtCore.QTimer.singleShot(0, lambda: rodar(it, self.ribbon))
            return it

        def abrir(self, ancora=None):
            self.campo.clear()
            self.filtrar("")
            if ancora is not None:
                p = ancora.mapToGlobal(QtCore.QPoint(ancora.width(), ancora.height()))
                self.adjustSize()
                self.move(p.x() - self.width(), p.y() + 2)
            self.show()
            self.campo.setFocus()


class CmdProcurarComando:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("busca.svg"), "MenuText": "Procurar comando",
                "ToolTip": "Digite parte do nome de qualquer ferramenta e tecle Enter (Ctrl+K)."}

    def IsActive(self):
        return True

    def Activated(self):
        import PrumoRibbon
        rb = PrumoRibbon._state.get("ribbon")
        if rb is not None:
            rb.procurar_comando()


def registrar_comandos():
    import FreeCADGui
    FreeCADGui.addCommand("Prumo_ProcurarComando", CmdProcurarComando())
