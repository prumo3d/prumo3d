# SPDX-License-Identifier: LGPL-2.1-or-later
"""Aba do esboço (durante a edição): situação, relações e restrições no estilo do SolidWorks.

No lugar dos quadros "Edição de esboço", "Restrições" e "Elementos" do FreeCAD (que continuam a um
clique, em "Lista completa"), o topo da aba do comando mostra:

- a situação do esboço numa frase: "Totalmente definido", "Falta 2 medidas para ficar definido",
  "Restrições em conflito";
- Relações: o que está selecionado (etiquetas) e os botões de relação; só ficam ativos os que servem
  para aquela seleção (duas linhas → Paralela, Perpendicular, Igual, Colinear…);
- Neste esboço: as relações e cotas existentes, com × para apagar;
- Auxiliares: os comandos de seleção e geometria interna que saíram da barra de cima.

O quadro de parâmetros da ferramenta ativa (ex.: modo do círculo) continua do FreeCAD.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtWidgets

try:
    import shiboken6 as shiboken
except ImportError:  # pragma: no cover
    import shiboken2 as shiboken

import PrumoUI as UI

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"

# quadros do FreeCAD escondidos (identificados pela classe do conteúdo, vale em qualquer idioma)
QUADROS_ESCONDIDOS = ("TaskSketcherConstraints", "TaskSketcherElements", "TaskSketcherMessages")

# (chave, texto, ícone SVG (traço), comando)
RELACOES = [
    ("horizontal", "Horizontal", '<path d="M4 12h16"/>', "Sketcher_ConstrainHorizontal"),
    ("vertical", "Vertical", '<path d="M12 4v16"/>', "Sketcher_ConstrainVertical"),
    ("paralela", "Paralela", '<path d="M6 6l12 12M4 12l8 8"/>', "Sketcher_ConstrainParallel"),
    ("perpendicular", "Perpend.", '<path d="M5 19h14M8 19V5"/>', "Sketcher_ConstrainPerpendicular"),
    ("igual", "Igual", '<path d="M5 9h14M5 15h14"/>', "Sketcher_ConstrainEqual"),
    ("colinear", "Colinear", '<path d="M3 12h7M14 12h7"/><circle cx="12" cy="12" r="1.5"/>',
     "Sketcher_ConstrainTangent"),
    ("tangente", "Tangente", '<circle cx="10" cy="12" r="6"/><path d="M16 4v16"/>', "Sketcher_ConstrainTangent"),
    ("coincidente", "Coincid.", '<path d="M4 18h8M12 18V6"/><circle cx="12" cy="18" r="2"/>',
     "Sketcher_ConstrainCoincidentUnified"),
    ("fixar", "Fixar", '<rect x="6" y="10" width="12" height="10" rx="1.5"/><path d="M9 10V7a3 3 0 0 1 6 0v3"/>',
     "Sketcher_ConstrainBlock"),
    ("simetrica", "Simétrica", '<path d="M12 3v18"/><circle cx="6" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/>',
     "Sketcher_ConstrainSymmetric"),
    ("cota", "Cotar", '<path d="M3 12h18M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3M3 6v12M21 6v12"/>',
     "Sketcher_Dimension"),
]
for _k, _t, _svg, _c in RELACOES:
    UI.ICONES.setdefault("rel_" + _k, _svg)

AUXILIARES = [
    ("Sketcher_SelectConstraints", "Selecionar restrições da geometria"),
    ("Sketcher_SelectElementsAssociatedWithConstraints", "Selecionar geometria das restrições"),
    ("Sketcher_RestoreInternalAlignmentGeometry", "Mostrar geometria interna"),
    ("Sketcher_SwitchVirtualSpace", "Trocar espaço virtual"),
    ("Sketcher_ArcOverlay", "Auxiliar de arcos"),
    ("Sketcher_JoinCurves", "Unir curvas"),
]

TIPOS = {
    "Coincident": "Coincidente", "Horizontal": "Horizontal", "Vertical": "Vertical", "Parallel": "Paralela",
    "Perpendicular": "Perpendicular", "Tangent": "Tangente", "Equal": "Igual", "Symmetric": "Simétrica",
    "PointOnObject": "Ponto na curva", "Block": "Fixa", "Distance": "Distância", "DistanceX": "Distância horizontal",
    "DistanceY": "Distância vertical", "Radius": "Raio", "Diameter": "Diâmetro", "Angle": "Ângulo",
    "Lock": "Travada", "SnellsLaw": "Refração", "Weight": "Peso",
}
DIMENSIONAIS = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle")


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def ligado():
    return _params().GetBool("PainelDoEsboco", True)


def esboco_em_edicao():
    try:
        gdoc = FreeCADGui.ActiveDocument
        vp = gdoc.getInEdit() if gdoc else None
        obj = vp.Object if vp is not None else None
    except Exception:
        return None
    if obj is not None and obj.TypeId == "Sketcher::SketchObject":
        return obj
    return None


# ----------------------------------------------------------------------------------- nomes
def nome_geo(sk, i):
    if i == -1:
        return "Eixo X"
    if i == -2:
        return "Eixo Y"
    if i <= -3:
        return "Referência {}".format(-i - 2)
    if i < 0 or i >= len(sk.Geometry):
        return "?"
    g = sk.Geometry[i]
    t = type(g).__name__
    base = {"LineSegment": "Linha", "Circle": "Círculo", "ArcOfCircle": "Arco", "Point": "Ponto",
            "Ellipse": "Elipse", "ArcOfEllipse": "Arco", "BSplineCurve": "Curva"}.get(t, "Elemento")
    return "{} {}".format(base, i + 1)


def texto_restricao(sk, c):
    tipo = TIPOS.get(c.Type, c.Type)
    geos = []
    for g in (c.First, c.Second, getattr(c, "Third", -2000)):
        if g is not None and g > -2000 and not (g == -2000):
            n = nome_geo(sk, g)
            if n not in geos and n != "?":
                geos.append(n)
    alvo = " / ".join(geos[:3])
    if c.Type in DIMENSIONAIS:
        try:
            if c.Type == "Angle":
                import math
                val = "{:.1f}°".format(math.degrees(c.Value)).replace(".", ",")
            else:
                val = "{:g} mm".format(round(float(c.Value), 3)).replace(".", ",")
        except Exception:
            val = ""
        tipo = "{} {}".format(tipo, val).strip()
    if c.Name:
        tipo = "{} ({})".format(tipo, c.Name)
    return "{} · {}".format(tipo, alvo) if alvo else tipo


def restricoes_visiveis(sk):
    """[(índice, restrição)] sem as internas (alinhamento de elipse, B-spline…)."""
    out = []
    for i, c in enumerate(sk.Constraints):
        if c.Type in ("InternalAlignment",):
            continue
        out.append((i, c))
    return out


# ----------------------------------------------------------------------------------- seleção
def selecao_do_esboco(sk):
    """{'linhas': [...], 'curvas': [...], 'pontos': [...], 'nomes': [...]} do que está selecionado."""
    r = {"linhas": [], "curvas": [], "pontos": [], "nomes": [], "restricoes": []}
    try:
        sel = FreeCADGui.Selection.getSelectionEx(sk.Document.Name)
    except Exception:
        sel = []
    for s in sel:
        if s.Object is not sk:
            continue
        for sub in s.SubElementNames:
            if sub.startswith("Edge"):
                i = int(sub[4:]) - 1
                g = sk.Geometry[i] if 0 <= i < len(sk.Geometry) else None
                t = type(g).__name__ if g is not None else ""
                (r["linhas"] if t == "LineSegment" else r["curvas"]).append(i)
                r["nomes"].append(nome_geo(sk, i))
            elif sub in ("H_Axis", "V_Axis"):
                r["linhas"].append(-1 if sub == "H_Axis" else -2)
                r["nomes"].append("Eixo X" if sub == "H_Axis" else "Eixo Y")
            elif sub.startswith("ExternalEdge"):
                r["linhas"].append(-2 - int(sub[12:]))
                r["nomes"].append("Referência {}".format(sub[12:]))
            elif sub.startswith("Vertex") or sub == "RootPoint":
                r["pontos"].append(sub)
                r["nomes"].append("Origem" if sub == "RootPoint" else "Ponto {}".format(sub[6:]))
            elif sub.startswith("Constraint"):
                r["restricoes"].append(int(sub[10:]) - 1)
    return r


def relacoes_possiveis(sel):
    """Chaves das relações que servem para a seleção (as outras ficam apagadas)."""
    L, C, P = len(sel["linhas"]), len(sel["curvas"]), len(sel["pontos"])
    E = L + C
    ok = set()
    if E == 0 and P == 0:
        return ok
    if (L >= 1 and C == 0 and P == 0) or (P == 2 and E == 0):
        ok |= {"horizontal", "vertical"}
    if L >= 2 and C == 0 and P == 0:
        ok |= {"paralela", "igual"}
    if L == 2 and C == 0 and P == 0:
        ok |= {"perpendicular", "colinear"}
    if C >= 2 and L == 0 and P == 0:
        ok.add("igual")
    if E == 2 and C >= 1 and P == 0:
        ok.add("tangente")
    if P >= 2 or (P == 1 and E >= 1) or (C == 2 and L == 0 and P == 0):
        ok.add("coincidente")
    if E >= 1 and P == 0:
        ok.add("fixar")
    if (P == 2 and L == 1 and C == 0) or (P == 3 and E == 0):
        ok.add("simetrica")
    if E >= 1 or P >= 1:
        ok.add("cota")
    return ok


def problemas(sk):
    """Índices (base 0) das restrições em conflito, repetidas ou com defeito (o FreeCAD numera a partir de 1)."""
    out = set()
    for prop in ("ConflictingConstraints", "RedundantConstraints", "MalformedConstraints"):
        try:
            for n in getattr(sk, prop, []) or []:
                if 1 <= int(n) <= len(sk.Constraints):
                    out.add(int(n) - 1)
        except Exception:
            pass
    return out


def _nomes_restricoes(sk, numeros):
    partes = []
    for n in numeros[:3]:
        try:
            partes.append(texto_restricao(sk, sk.Constraints[int(n) - 1]))
        except Exception:
            partes.append(str(n))
    return "; ".join(partes) + ("…" if len(numeros) > 3 else "")


def resolve(sk):
    """Código do resolvedor: 0 ok, -1 não achou solução, -2 repetidas, -3 conflito, -4 com defeito."""
    try:
        return int(sk.solve())
    except Exception:
        return 0


def situacao(sk, codigo=None):
    """(texto, tipo) da situação: tipo 'ok', 'info' ou 'erro'.

    codigo: resultado de resolve(sk), quando já calculado. Sem ele, só as listas do esboço contam
    (e um esboço sem solução apareceria como definido)."""
    try:
        conflito = list(getattr(sk, "ConflictingConstraints", []) or [])
        redund = list(getattr(sk, "RedundantConstraints", []) or [])
        mal = list(getattr(sk, "MalformedConstraints", []) or [])
        dof = int(getattr(sk, "DoF", -1))
    except Exception:
        return "", "info"
    if mal:
        return "Restrição com defeito: {}".format(_nomes_restricoes(sk, mal)), "erro"
    if conflito:
        return "Restrições em conflito: {}".format(_nomes_restricoes(sk, conflito)), "erro"
    if redund:
        return "Restrições repetidas: {}".format(_nomes_restricoes(sk, redund)), "erro"
    if codigo is not None and codigo < 0:
        return ("O esboço não fecha: o resolvedor não achou uma solução com estas restrições (comum quando "
                "entram restrições automáticas demais). Apague a mais recente ou desfaça (Ctrl+Z)."), "erro"
    if dof == 0:
        return "Totalmente definido", "ok"
    if dof > 0:
        return "Falta{} {} medida{} para ficar definido".format("m" if dof > 1 else "", dof,
                                                                "s" if dof > 1 else ""), "info"
    return "", "info"


def retirar_automaticas_em_conflito(sk, base_restricoes, base_geometria):
    """Desenhou geometria nova e as restrições automáticas que vieram junto (tangente, horizontal…) não
    cabem no desenho: apaga as novas que estão no conflito, da mais recente para a mais antiga, até o
    esboço fechar. Só mexe no que entrou depois de base_restricoes, e só se entrou geometria nova.
    Devolve a lista de textos das restrições retiradas (vazia se não mexeu)."""
    if len(sk.Geometry) <= base_geometria or len(sk.Constraints) <= base_restricoes:
        return []
    retiradas = []
    for _ in range(len(sk.Constraints) - base_restricoes):
        codigo = resolve(sk)
        if codigo >= 0 and not problemas(sk):
            break
        ruins = sorted(i for i in problemas(sk) if i >= base_restricoes)
        if not ruins:
            if codigo >= 0 or problemas(sk):
                break             # o problema é de restrição antiga: fica com o usuário (botão do painel)
            ruins = [len(sk.Constraints) - 1]    # sem lista do resolvedor: a mais recente
        i = ruins[-1]
        if i < base_restricoes:
            break
        try:
            retiradas.append(texto_restricao(sk, sk.Constraints[i]))
            sk.delConstraint(i)
        except Exception:
            break
    if retiradas:
        resolve(sk)
        try:
            sk.Document.recompute()
        except Exception:
            pass
    return retiradas


# ----------------------------------------------------------------------------------- painel
class PainelEsboco(QtWidgets.QWidget):
    def __init__(self, sk, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema(
            "#PrumoUI { background: transparent; }"
            "QLabel#PrumoSituacao { font-weight: 600; padding: 2px 0; }"
            "QLabel#PrumoSituacao[tipo=\"ok\"] { color: #1E7A4C; }"
            "QLabel#PrumoSituacao[tipo=\"info\"] { color: #6B5200; }"
            "QLabel#PrumoSituacao[tipo=\"erro\"] { color: #A33A2B; }"
            "QToolButton#PrumoRel { border: 1px solid #DCE4EC; border-radius: 8px; background: #FFFFFF;"
            " color: #3B4A59; padding: 6px 1px; }"
            "QToolButton#PrumoRel:hover { border-color: #003A70; color: #003A70; }"
            "QToolButton#PrumoRel:disabled { color: #B6C0CA; border-color: #EEF2F6; }"
            "QToolButton#PrumoX { border: 0; background: transparent; color: #9AA7B4; font-weight: 600; }"
            "QToolButton#PrumoX:hover { color: #A33A2B; }"
            "QListWidget#PrumoLista { border: 0; background: transparent; }"
            "QListWidget#PrumoLista::item { padding: 3px 2px; border-radius: 6px; }"
            "QListWidget#PrumoLista::item:selected { background: #E6EEF7; color: #003A70; }"))
        self.sk = sk
        self.assinatura = None
        self.base = None          # (restrições, geometria) da última vez que o esboço fechou
        self.aviso_retiradas = []
        self.aviso_assin = None
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.situacao = QtWidgets.QLabel()
        self.situacao.setObjectName("PrumoSituacao")
        self.situacao.setWordWrap(True)
        lay.addWidget(self.situacao)
        # conflito (ex.: restrições automáticas demais ao ligar dois círculos): apaga a mais recente
        self.resolver = QtWidgets.QPushButton("Apagar a restrição mais recente do conflito")
        self.resolver.setObjectName("PrumoPrimario")
        self.resolver.setToolTip("Normalmente é a que entrou sozinha por último (tangente, horizontal…). "
                                 "Desfazer (Ctrl+Z) volta.")
        self.resolver.clicked.connect(self._resolver)
        self.resolver.setVisible(False)
        lay.addWidget(self.resolver)

        # Relações
        self.cartao_rel = UI.Cartao("Relações", "rel_paralela")
        self.chips = QtWidgets.QLabel()
        self.chips.setObjectName("PrumoSub")
        self.chips.setWordWrap(True)
        self.cartao_rel.widget(self.chips)
        grade = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(grade)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(4)
        for c in range(4):
            g.setColumnStretch(c, 1)
        self.botoes = {}
        for n, (k, texto, _svg, cmd) in enumerate(RELACOES):
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoRel")
            b.setText(texto)
            b.setIcon(UI.icone("rel_" + k))
            b.setIconSize(QtCore.QSize(18, 18))
            b.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            b.setToolTip(texto)
            b.clicked.connect(lambda _=False, c=cmd, kk=k: self._relacionar(c, kk))
            g.addWidget(b, n // 4, n % 4)
            self.botoes[k] = b
        self.cartao_rel.widget(grade)
        self.dica_rel = QtWidgets.QLabel("Selecione linhas, círculos ou pontos no desenho: só ficam ativas as "
                                         "relações que servem para eles.")
        self.dica_rel.setObjectName("PrumoSub")
        self.dica_rel.setWordWrap(True)
        self.cartao_rel.widget(self.dica_rel)
        lay.addWidget(self.cartao_rel)

        # Neste esboço
        self.cartao_lista = UI.Cartao("Neste esboço", "lista")
        self.lista = QtWidgets.QListWidget()
        self.lista.setObjectName("PrumoLista")
        self.lista.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.lista.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.lista.itemClicked.connect(self._selecionar_restricao)
        self.cartao_lista.widget(self.lista)
        lay.addWidget(self.cartao_lista)

        # Auxiliares e lista completa do FreeCAD
        self.cartao_aux = UI.Cartao("Auxiliares", "info", chave=True, ligado=False)
        for cmd, texto in AUXILIARES:
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoLink")
            b.setText(texto)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=cmd: self._rodar(c))
            self.cartao_aux.widget(b)
        lay.addWidget(self.cartao_aux)

        self.completa = QtWidgets.QToolButton()
        self.completa.setObjectName("PrumoAvancado")
        self.completa.setCheckable(True)
        self.completa.setText("Lista completa do FreeCAD")
        self.completa.setToolTip("Restrições e elementos nas listas originais do FreeCAD")
        self.completa.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.completa.toggled.connect(self._lista_completa)
        lay.addWidget(self.completa)
        self.atualizar(True)

    # ---------------------------------------------------------------- ações
    def _rodar(self, cmd):
        try:
            FreeCADGui.runCommand(cmd, 0)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: {}: {}\n".format(cmd, exc))
        QtCore.QTimer.singleShot(50, lambda: self.atualizar(True))

    def _relacionar(self, cmd, chave):
        self._rodar(cmd)

    def _apagar(self, i):
        sk = self.sk
        sk.Document.openTransaction("Apagar restrição")
        try:
            sk.delConstraint(i)
            sk.Document.commitTransaction()
        except Exception as exc:
            sk.Document.abortTransaction()
            FreeCAD.Console.PrintWarning("Prumo: não apagou a restrição: {}\n".format(exc))
        sk.Document.recompute()
        self.atualizar(True)

    def _resolver(self):
        ruins = sorted(problemas(self.sk))
        if ruins:
            self._apagar(ruins[-1])
        elif len(self.sk.Constraints):
            self._apagar(len(self.sk.Constraints) - 1)    # sem lista do resolvedor: a última que entrou

    def _selecionar_restricao(self, item):
        i = item.data(QtCore.Qt.UserRole)
        try:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(self.sk.Document.Name, self.sk.Name, "Constraint{}".format(i + 1))
        except Exception:
            pass

    def _lista_completa(self, on):
        mostrar_quadros_do_freecad(bool(on))

    # ---------------------------------------------------------------- atualizar
    def atualizar(self, forcar=False):
        sk = self.sk
        try:
            sel = selecao_do_esboco(sk)
            assin = (len(sk.Constraints), len(sk.Geometry), int(getattr(sk, "DoF", -1)),
                     tuple(sel["nomes"]), tuple((c.Type, c.First, c.Second, round(float(c.Value), 6), c.Name)
                                                 for c in sk.Constraints))
        except Exception:
            return
        if assin == self.assinatura and not forcar:
            return
        if self.aviso_retiradas and self.aviso_assin is not None and assin != self.aviso_assin:
            self.aviso_retiradas = []         # o usuário mexeu de novo: o aviso já cumpriu o papel
        self.assinatura = assin
        self.codigo = resolve(sk)
        if (self.codigo < 0 or problemas(sk)) and self.base is not None and \
                _params().GetBool("RetirarAutomaticasEmConflito", True):
            tiradas = retirar_automaticas_em_conflito(sk, *self.base)
            if tiradas:
                self.aviso_retiradas = tiradas
                self.aviso_assin = None
                return self.atualizar(True)
        if self.aviso_retiradas and self.aviso_assin is None:
            self.aviso_assin = assin
        if self.codigo == 0 and not problemas(sk):
            self.base = (len(sk.Constraints), len(sk.Geometry))
        texto, tipo = situacao(sk, self.codigo)
        if self.aviso_retiradas and tipo != "erro":
            n = len(self.aviso_retiradas)
            texto = ("Relaç{} automática{} retirada{} porque não cabia{} no desenho: {}. Desfazer (Ctrl+Z) volta."
                     .format("ões" if n > 1 else "ão", "s" if n > 1 else "", "s" if n > 1 else "",
                             "m" if n > 1 else "", "; ".join(self.aviso_retiradas)) +
                     ("\n" + texto if texto else ""))
            tipo = "info"
        self.situacao.setText(texto)
        self.situacao.setProperty("tipo", tipo)
        self.situacao.style().unpolish(self.situacao)
        self.situacao.style().polish(self.situacao)
        self.situacao.setVisible(bool(texto))
        ruins = problemas(sk)
        self.resolver.setVisible(bool(ruins) or (self.codigo < 0 and len(sk.Constraints) > 0))

        self.chips.setText("Selecionado: " + ", ".join(sel["nomes"][:6]) + ("…" if len(sel["nomes"]) > 6 else "")
                           if sel["nomes"] else "Nada selecionado")
        ok = relacoes_possiveis(sel)
        for k, b in self.botoes.items():
            b.setEnabled(k in ok)

        visiveis = restricoes_visiveis(sk)
        visiveis.sort(key=lambda par: (par[0] not in ruins, par[0]))      # as com problema primeiro
        self.cartao_lista.titulo.setText("Neste esboço ({})".format(len(visiveis)))
        self.lista.clear()
        for i, c in visiveis:
            it = QtWidgets.QListWidgetItem()
            it.setData(QtCore.Qt.UserRole, i)
            linha = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(linha)
            hl.setContentsMargins(4, 0, 0, 0)
            hl.setSpacing(4)
            lb = QtWidgets.QLabel(("⚠ " if i in ruins else "") + texto_restricao(sk, c))
            lb.setToolTip(lb.text())
            if i in ruins:
                lb.setStyleSheet(UI.tema("color: #A33A2B; font-weight: 600;"))
            elif not getattr(c, "Driving", True):
                lb.setStyleSheet(UI.tema("color: #4D7FAD;"))
            hl.addWidget(lb, 1)
            x = QtWidgets.QToolButton()
            x.setObjectName("PrumoX")
            x.setText("×")
            x.setToolTip("Apagar")
            x.setCursor(QtCore.Qt.PointingHandCursor)
            x.clicked.connect(lambda _=False, ii=i: self._apagar(ii))
            hl.addWidget(x)
            it.setSizeHint(QtCore.QSize(10, 28))
            self.lista.addItem(it)
            self.lista.setItemWidget(it, linha)
        n = len(visiveis)
        self.lista.setFixedHeight(max(32, min(n, 8) * 29 + 4))
        self.lista.setVisible(n > 0)


# ----------------------------------------------------------------------------------- encaixe no painel
def _painel_de_tarefas():
    mw = FreeCADGui.getMainWindow()
    for w in mw.findChildren(QtWidgets.QWidget):
        if w.metaObject().className() == "Gui::TaskView::TaskPanel" and w.isVisible():
            return w
    return None


def _quadros(panel):
    """[(quadro, nome da classe do conteúdo)] dos quadros do FreeCAD no painel de tarefas."""
    out = []
    lay = panel.layout()
    for i in range(lay.count()):
        w = lay.itemAt(i).widget()
        if w is None or not shiboken.isValid(w):
            continue
        nomes = {w.metaObject().className()} | {c.metaObject().className() for c in w.findChildren(QtWidgets.QWidget)}
        for alvo in QUADROS_ESCONDIDOS:
            if any(alvo in n for n in nomes):
                out.append((w, alvo))
                break
    return out


def mostrar_quadros_do_freecad(mostrar):
    panel = _painel_de_tarefas()
    if panel is None:
        return 0
    n = 0
    for w, _alvo in _quadros(panel):
        w.setVisible(bool(mostrar))
        n += 1
    return n


class Encaixe:
    """Põe o PainelEsboco no topo do painel de tarefas enquanto um esboço está em edição."""

    def __init__(self):
        self.painel = None
        self.sk = None
        self.t = QtCore.QTimer(FreeCADGui.getMainWindow())
        self.t.setInterval(300)
        self.t.timeout.connect(self._tick)

    def iniciar(self):
        self.t.start()

    def parar(self):
        self.t.stop()
        self._tirar()

    def _vivo(self):
        return self.painel is not None and shiboken.isValid(self.painel)

    def _tirar(self):
        if self._vivo():
            self.painel.hide()
            self.painel.setParent(None)
            self.painel.deleteLater()
        self.painel, self.sk = None, None

    def _tick(self):
        try:
            self._passo()
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: painel do esboço: {}\n".format(exc))

    def _passo(self):
        sk = esboco_em_edicao() if ligado() else None
        if sk is None:
            if self.painel is not None:
                self._tirar()
            return
        panel = _painel_de_tarefas()
        if panel is None:
            return
        if not self._vivo() or self.painel.parent() is not panel or self.sk is not sk:
            self._tirar()
            self.sk = sk
            self.painel = PainelEsboco(sk, panel)
            lay = panel.layout()
            # logo abaixo do quadro da ferramenta ativa (parâmetros do círculo, da linha…)
            pos = 0
            for i in range(lay.count()):
                w = lay.itemAt(i).widget()
                if w is not None and "TaskSketcherTool" in w.metaObject().className():
                    pos = i + 1
                    break
            lay.insertWidget(pos, self.painel)
        if not self.painel.completa.isChecked():
            for w, _alvo in _quadros(panel):
                if w.isVisible():
                    w.setVisible(False)
        self.painel.atualizar()


_estado = {"encaixe": None}


def instalar():
    if _estado["encaixe"] is None:
        _estado["encaixe"] = Encaixe()
    _estado["encaixe"].iniciar()
    return _estado["encaixe"]


def painel():
    e = _estado["encaixe"]
    return e.painel if e is not None and e._vivo() else None
