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
    "extrude": "extrusao", "extrusao": "ressalto", "boss": "ressalto", "cut": "cavidade subtrair corte",
    "pocket": "cavidade", "fillet": "arredondar", "filete": "arredondar", "chamfer": "chanfro",
    "pattern": "padrao matriz", "matriz": "padrao", "mirror": "espelhar", "espelho": "espelhar",
    "drawing": "folha desenho", "sheet": "folha", "dimension": "cota", "dimensao": "cota", "medida": "cota medir",
    "bom": "lista materiais", "interference": "interferencia", "explode": "explodida",
    "hole": "furo", "shell": "casca", "revolve": "revolucao", "sweep": "varredura", "loft": "loft", "transicao": "loft",
    "sketch": "esboco", "plano": "plano referencia", "weld": "solda", "gear": "engrenagem",
    "drive": "mover junta", "rigid": "travar", "rigido": "travar", "concentric": "concentrica",
    "tangent": "tangente", "coincident": "coincidente", "parallel": "paralela",
    # Fusion, Inventor, Onshape e outros (inglês e português)
    "pad": "extrusao", "join": "extrusao unir", "combine": "unir subtrair intersecao", "union": "unir",
    "subtract": "subtrair", "intersect": "intersecao", "thicken": "casca", "split": "dividir",
    "draft": "angulo saida", "helix": "helice", "coil": "helice", "thread": "rosca", "knurl": "rosca",
    "joint": "junta", "joints": "junta", "revolute": "dobradica", "slider": "deslizante", "ball": "esferica",
    "insert": "inserir componente", "place": "inserir componente", "derive": "vinculo forma",
    "derived": "vinculo forma", "project": "geometria externa", "projetar": "geometria externa",
    "projection": "geometria externa", "convert": "geometria externa", "trim": "aparar", "offset": "offset",
    "timeline": "arvore modelo", "historico": "arvore modelo", "rollback": "arvore modelo",
    "history": "arvore modelo", "browser": "arvore modelo", "featuremanager": "arvore modelo",
    "balloon": "balao", "parts": "lista materiais", "centermark": "centro circulo",
    "section": "vista corte", "projected": "vista", "baseview": "vista", "isometric": "isometrica",
    "rectangular": "padrao linear", "linear": "padrao linear", "circular": "padrao circular",
    "polar": "padrao circular", "multitransform": "multitransformacao", "body": "corpo", "part": "parte peca",
    "component": "componente", "assembly": "montagem", "sheetmetal": "chapa", "flange": "aba",
    "hem": "bainha", "unfold": "planificar", "flat": "planificar", "frame": "estrutura", "weldment": "estrutura soldada",
    "sweep": "varredura", "pipe": "tubulacao varredura", "rib": "reforco", "web": "reforco",
    "parameters": "variaveis", "parametros": "variaveis", "equations": "variaveis", "equacoes": "variaveis",
    "configuration": "variantes", "configuracao": "variantes", "configuracoes": "variantes",
    "measure": "medir", "inspect": "medir verificar",
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
    "gradil": "barra varredura", "grade": "barra varredura", "xadrez": "barra varredura",
    "chapa expandida": "barra varredura", "vergalhao": "barra varredura", "lote": "folhas lote", "pranchas": "folhas lote", "automatico": "arredondamento automatico",
}


def normalizar(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.lower().replace("\n", " ").replace("&", "").split())


_OUTROS = {}


def _nomes_outros_cad(cmd):
    """Nomes que o comando tem no SolidWorks, ZW3D, Inventor e Fusion (tabela do guia "Vindo do SolidWorks")."""
    if not _OUTROS:
        try:
            import PrumoGuiaMigracao
            for linha in PrumoGuiaMigracao.EQUIVALENCIAS:
                sw, outros, cmds = linha[1], linha[2], linha[5]
                for c in cmds:
                    _OUTROS.setdefault(c, []).extend([sw, outros])
        except Exception:
            _OUTROS["-"] = []
    partes = []
    for c in str(cmd).split("|"):
        for nome in _OUTROS.get(c, []):
            # "Extrude / Extrusion" e "Ressalto/Base extrudado" valem como nomes separados
            for parte in str(nome).replace("(", "/").replace(")", "/").split("/"):
                n = normalizar(parte)
                if n and n not in partes:
                    partes.append(n)
    return partes


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
                if cmd in vistos or (existentes is not None and cmd.split("|")[0] not in existentes):
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
                res.append((cmd, rot, t["id"], t["label"], grupo, busca, _nomes_outros_cad(cmd)))
    # ferramentas da barra de vistas (embaixo da vista 3D): não têm aba
    try:
        import PrumoBarraVista
        itens_barra = []
        for it in PrumoBarraVista.ITENS:
            if it == "|":
                continue
            if it[0] == "menu":
                itens_barra += list(it[3])
            else:
                itens_barra.append(it)
    except Exception:
        itens_barra = []
    for cmd, rot in itens_barra:
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
        busca = normalizar(" ".join((rot, menu, "vista barra de vistas", dica[:200])))
        res.append((cmd, rot, None, "Barra de vistas", "Vistas", busca))
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
        outros = it[6] if len(it) > 6 else []
        palavras_rot = rot.split()
        if rot == q:
            nota = 0
        elif rot.startswith(q):
            nota = 1
        elif any(o == q or o.startswith(q + " ") for o in outros):
            nota = 1.5                         # nome no SolidWorks/Fusion... ("corte extrudado")
        elif all(p in rot for p in palavras):
            nota = 2
        elif extras and any(e in palavras_rot or rot.startswith(e) for e in extras):
            nota = 2.5                         # sinônimo ("shell" -> Casca)
        elif outros and all(any(p in o.split() for o in outros) for p in palavras):
            nota = 3                           # palavra inteira de um nome de outro CAD
        elif all(p in busca for p in palavras):
            nota = 4
        elif extras and any(e in rot for e in extras):
            nota = 4.5
        else:
            continue
        # desempate: mais palavras do sinônimo no rótulo ("bom" -> Lista de materiais antes de Lista de corte)
        acertos = sum(1 for e in extras if e in palavras_rot)
        res.append((nota, -acertos, len(rot), it))
    res.sort(key=lambda x: (x[0], x[1], x[2]))
    return [x[3] for x in res[:limite]]


def rodar(item, ribbon=None):
    """Vai para a aba da ferramenta e roda o comando."""
    import FreeCADGui
    cmd, _rot, aba = item[0], item[1], item[2]
    if ribbon is not None and aba:
        try:
            ribbon.select_tab(aba, user=True)
        except Exception:
            pass
    import PrumoAvisoClique as AV
    try:
        acts = FreeCADGui.Command.get(cmd).getAction() or []
    except Exception:
        acts = []
    if acts and not any(a.isEnabled() for a in acts):
        try:
            import PrumoSelecao
            if PrumoSelecao.precisa_de_painel(cmd):
                PrumoSelecao.pedir_para_comando(cmd)
                return
        except Exception:
            pass
        AV.clique_inativo(cmd, _rot)
        return
    AV.executar(cmd, lambda: FreeCADGui.runCommand(cmd, 0), _rot)


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
            achados = procurar(texto, self.itens())
            if not normalizar(texto) and getattr(self, "padrao", None):
                achados = self.padrao          # caixa da tecla S: sem nada digitado, as ferramentas da aba
            for it in achados:
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
            self.dica.setText(("Ferramentas da aba · digite para procurar todas · Enter roda · Esc fecha"
                               if not texto and getattr(self, "padrao", None)
                               else "Enter roda · ↑↓ escolhe · Esc fecha") if self.lista.count() or not texto
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

        def abrir(self, ancora=None, ponto=None, padrao=None):
            """Abre debaixo da âncora (lupa) ou no ponto (cursor, tecla S). `padrao`: itens mostrados sem texto."""
            self.padrao = padrao
            self.campo.clear()
            self.filtrar("")
            if ponto is not None:
                self.adjustSize()
                tela = QtGui.QGuiApplication.screenAt(ponto) or QtGui.QGuiApplication.primaryScreen()
                g = tela.availableGeometry()
                x = min(max(ponto.x() - 20, g.left()), g.right() - self.width())
                y = min(max(ponto.y() - 20, g.top()), g.bottom() - self.height())
                self.move(x, y)
            elif ancora is not None:
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
