# SPDX-License-Identifier: LGPL-2.1-or-later
"""Esboço 3D: linhas por pontos X, Y, Z no espaço, com trechos (ramificações) e curvas nos cantos.

O Sketcher do FreeCAD só desenha num plano. Para caminho de tubo, esqueleto de estrutura espacial ou
trajetória de varredura, o Esboço 3D liga pontos digitados (absolutos ou relativos ao anterior) ou
clicados no modelo (encaixa em vértices e pontas de arestas).

- Pontos: lista de pontos (coordenadas do objeto; a Posição move tudo junto).
- Quebras: índices dos pontos que começam um trecho novo (ramal); o primeiro ponto de um ramal costuma
  ser clicado sobre um ponto já existente.
- Fechado: liga o último ponto ao primeiro (só com um trecho).
- RaioCurva: arredonda os cantos com arcos tangentes (curva de tubo); 0 = cantos vivos.

Serve direto como esqueleto da Estrutura soldada e como trajetória da Varredura do Part.
"""
import math

import FreeCAD

TOL = 1e-6


# ======================================================================== geometria
def trechos(pontos, quebras=()):
    """Divide a lista de pontos nos trechos: [[p0, p1, ...], ...] (pontos repetidos seguidos saem)."""
    pts = [FreeCAD.Vector(p) for p in pontos]
    cortes = sorted({int(i) for i in quebras if 0 < int(i) < len(pts)})
    res = []
    ini = 0
    for c in cortes + [len(pts)]:
        t = []
        for p in pts[ini:c]:
            if not t or (p - t[-1]).Length > TOL:
                t.append(p)
        if t:
            res.append(t)
        ini = c
    return res


def _canto(a, p, b, r):
    """Arco tangente de raio r no canto p (entre a e b): (t1, meio, t2) ou None (alinhado/não cabe)."""
    u1 = a - p
    u2 = b - p
    l1, l2 = u1.Length, u2.Length
    if l1 < TOL or l2 < TOL:
        return None
    u1 = u1 * (1.0 / l1)
    u2 = u2 * (1.0 / l2)
    cos = max(-1.0, min(1.0, u1.dot(u2)))
    teta = math.acos(cos)                    # ângulo interno do canto
    if teta < 1e-6 or math.pi - teta < 1e-6:
        return None                          # volta sobre si ou reto: sem arco
    t = r / math.tan(teta / 2.0)
    if t > l1 + TOL or t > l2 + TOL:
        return None
    w = u1 + u2
    w = w * (1.0 / w.Length)
    centro = p + w * (r / math.sin(teta / 2.0))
    t1 = p + u1 * t
    t2 = p + u2 * t
    meio = centro - w * r
    return t1, meio, t2


def arestas_do_trecho(pts, fechado=False, raio=0.0):
    """Arestas (Part) de um trecho; com raio > 0, os cantos viram arcos tangentes."""
    import Part
    n = len(pts)
    if n < 2:
        return []
    fechar = fechado and n >= 3
    if fechar and (pts[0] - pts[-1]).Length < TOL:
        pts = pts[:-1]
        n = len(pts)
    cantos = {}
    if raio > TOL:
        idx = range(n) if fechar else range(1, n - 1)
        # o raio não pode passar da metade dos trechos vizinhos (dois cantos dividem o mesmo segmento)
        for i in idx:
            a, p, b = pts[i - 1], pts[i], pts[(i + 1) % n]
            c = _canto(p + (a - p) * 0.5, p, p + (b - p) * 0.5, raio)
            if c is not None:
                cantos[i] = c
    ed = []
    segs = list(range(n if fechar else n - 1))
    for i in segs:
        j = (i + 1) % n
        ini = cantos[i][2] if i in cantos else pts[i]
        fim = cantos[j][0] if j in cantos else pts[j]
        if (fim - ini).Length > TOL:
            ed.append(Part.LineSegment(ini, fim).toShape())
        if j in cantos and (j != 0 or fechar):
            t1, meio, t2 = cantos[j]
            ed.append(Part.Arc(t1, meio, t2).toShape())
    return ed


def forma(pontos, quebras=(), fechado=False, raio=0.0):
    """Forma do esboço: um fio por trecho (Compound se houver mais de um)."""
    import Part
    ts = trechos(pontos, quebras)
    fios = []
    for t in ts:
        ed = arestas_do_trecho(t, fechado and len(ts) == 1, raio)
        if ed:
            try:
                fios.append(Part.Wire(ed))
            except Exception:
                fios.append(Part.Compound(ed))
    if not fios:
        return Part.Shape()
    if len(fios) == 1:
        return fios[0]
    return Part.Compound(fios)


# ------------------------------------------------------------------------ desenho no espaço
# Plano de desenho: passa pelo último ponto e troca com Tab (XY → YZ → ZX).
PLANOS = ("XY", "YZ", "ZX")
NORMAIS = {"XY": (0.0, 0.0, 1.0), "YZ": (1.0, 0.0, 0.0), "ZX": (0.0, 1.0, 0.0)}


def proximo_plano(plano):
    return PLANOS[(PLANOS.index(plano) + 1) % len(PLANOS)] if plano in PLANOS else PLANOS[0]


def no_plano(origem, direcao, base, plano):
    """Encontro do raio (origem + t·direção) com o plano que passa por base; None se o plano está de
    perfil para a vista."""
    n = FreeCAD.Vector(*NORMAIS[plano])
    d = FreeCAD.Vector(direcao)
    den = d.dot(n)
    if abs(den) < 1e-6 * max(d.Length, 1e-12):
        return None
    t = (FreeCAD.Vector(base) - FreeCAD.Vector(origem)).dot(n) / den
    return FreeCAD.Vector(origem) + d * t


def na_grade(p, base, passo, plano):
    """Arredonda as coordenadas do plano para múltiplos do passo a partir de base (comprimentos
    redondos); a coordenada normal fica a da base."""
    if passo <= 0:
        return FreeCAD.Vector(p)
    p, base = FreeCAD.Vector(p), FreeCAD.Vector(base)
    c = [p.x, p.y, p.z]
    b = [base.x, base.y, base.z]
    normal = {"XY": 2, "YZ": 0, "ZX": 1}[plano]
    for k in range(3):
        c[k] = b[k] if k == normal else b[k] + round((c[k] - b[k]) / passo) * passo
    return FreeCAD.Vector(*c)


# ======================================================================== objeto
class Esboco3D:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, "Esboço 3D", dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        add("App::PropertyVectorList", "Pontos", "Pontos do esboço (mm, nas coordenadas do objeto)")
        add("App::PropertyIntegerList", "Quebras", "Índices dos pontos que começam um trecho novo (ramal)")
        add("App::PropertyBool", "Fechado", "Liga o último ponto ao primeiro (só com um trecho)", False)
        add("App::PropertyLength", "RaioCurva", "Raio das curvas nos cantos (0 = cantos vivos)", 0.0)
        add("App::PropertyLength", "Comprimento", "Comprimento total das linhas", 0.0, ro=True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def execute(self, obj):
        pl = obj.Placement
        s = forma(obj.Pontos, obj.Quebras, obj.Fechado, float(obj.RaioCurva))
        obj.Shape = s
        obj.Placement = pl
        comp = sum(e.Length for e in s.Edges) if not s.isNull() else 0.0
        if abs(float(obj.Comprimento) - comp) > 1e-9:
            obj.Comprimento = comp

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc=None, pontos=(), quebras=(), fechado=False, raio=0.0, nome="Esboco3D"):
    doc = doc or FreeCAD.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", nome)
    obj.Label = "Esboço 3D"
    Esboco3D(obj)
    obj.Pontos = [FreeCAD.Vector(p) for p in pontos]
    obj.Quebras = list(quebras)
    obj.Fechado = fechado
    obj.RaioCurva = raio
    if FreeCAD.GuiUp:
        VPEsboco3D(obj.ViewObject)
    doc.recompute()
    return obj


def e_esboco3d(obj):
    return obj is not None and isinstance(getattr(obj, "Proxy", None), Esboco3D)


# ======================================================================== interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    import PrumoUtil

    class VPEsboco3D:
        def __init__(self, vobj):
            vobj.Proxy = self
            try:
                vobj.LineWidth = 3.0
                vobj.PointSize = 6.0
                vobj.LineColor = (0.0, 0.227, 0.439)        # azul #003A70
                vobj.PointColor = (0.969, 0.745, 0.0)       # amarelo #F7BE00
            except Exception:
                pass

        def attach(self, vobj):
            self.Object = vobj.Object

        def getIcon(self):
            return PrumoUtil.icone("esboco3d.svg")

        def doubleClicked(self, vobj):
            abrir_painel(vobj.Object)
            return True

        def setEdit(self, vobj, mode=0):
            if mode == 0:
                abrir_painel(vobj.Object)
                return True
            return False

        def unsetEdit(self, vobj, mode=0):
            return False

        def dumps(self):
            return None

        def loads(self, state):
            return None

    def _ponto_clicado(info):
        """Ponto 3D (global) de um getObjectInfo: vértice exato, ponta de aresta próxima ou o ponto da
        superfície. None se não há objeto sob o cursor."""
        if not info:
            return None, ""
        p = FreeCAD.Vector(info["x"], info["y"], info["z"])
        doc = FreeCAD.ActiveDocument
        obj = doc.getObject(info.get("Object", "")) if doc else None
        sub = info.get("Component", "") or ""
        if obj is None or not sub:
            return p, "ponto"
        try:
            forma_sub = obj.getSubObject(sub)
        except Exception:
            forma_sub = None
        if forma_sub is None:
            return p, "ponto"
        if sub.startswith("Vertex"):
            return FreeCAD.Vector(forma_sub.Point), "vértice"
        if sub.startswith("Edge"):
            e = forma_sub
            pontas = [v.Point for v in e.Vertexes]
            if pontas:
                perto = min(pontas, key=lambda q: (q - p).Length)
                if (perto - p).Length <= max(0.08 * e.Length, 1e-6):
                    return FreeCAD.Vector(perto), "ponta da aresta"
            if hasattr(e.Curve, "Center") and hasattr(e.Curve, "Radius"):
                c = FreeCAD.Vector(e.Curve.Center)
                if (c - p).Length > 0.92 * e.Curve.Radius:
                    return p, "aresta"
            return p, "aresta"
        return p, "face"

    class Previa:
        """Linha elástica do último ponto ao cursor e marcador do cursor (Coin)."""

        def __init__(self, vista):
            from pivy import coin
            self.vista = vista
            self.raiz = coin.SoSeparator()
            estilo = coin.SoDrawStyle()
            estilo.lineWidth = 2
            estilo.pointSize = 9
            estilo.linePattern = 0xF0F0
            cor = coin.SoBaseColor()
            cor.rgb = (0.969, 0.745, 0.0)
            self.coords = coin.SoCoordinate3()
            self.linhas = coin.SoLineSet()
            self.linhas.numVertices.setValue(0)
            self.ponto = coin.SoPointSet()
            self.ponto.numPoints.setValue(0)
            pick = coin.SoPickStyle()
            pick.style = coin.SoPickStyle.UNPICKABLE
            for n in (pick, estilo, cor, self.coords, self.linhas, self.ponto):
                self.raiz.addChild(n)
            vista.getSceneGraph().addChild(self.raiz)

        def linha(self, ini, fim):
            pts = [p for p in (ini, fim) if p is not None]
            self.coords.point.setValues(0, len(pts), [(p.x, p.y, p.z) for p in pts])
            self.coords.point.setNum(len(pts))
            self.linhas.numVertices.setValue(2 if len(pts) == 2 else 0)
            self.ponto.numPoints.setValue(1 if fim is not None else 0)
            self.ponto.startIndex.setValue(len(pts) - 1 if fim is not None else 0)

        def remover(self):
            try:
                self.vista.getSceneGraph().removeChild(self.raiz)
            except Exception:
                pass

    def _cursor_na_vista():
        w = QtWidgets.QApplication.widgetAt(QtGui.QCursor.pos())
        while w is not None:
            if "View3DInventor" in w.metaObject().className():
                return True
            w = w.parentWidget()
        return False

    class FiltroTeclas(QtCore.QObject):
        """Tab e Esc durante o desenho: chegam antes de o Qt trocar o foco ou fechar o painel."""

        def __init__(self, painel):
            super().__init__()
            self.painel = painel

        def eventFilter(self, obj, ev):
            if ev.type() != QtCore.QEvent.KeyPress or self.painel._vista is None:
                return False
            if ev.key() not in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Escape):
                return False
            if ev.key() == QtCore.Qt.Key_Tab and not _cursor_na_vista():
                return False          # fora da vista 3D (no painel), Tab segue trocando de campo
            if ev.key() == QtCore.Qt.Key_Tab:
                self.painel.trocar_plano()
            else:
                self.painel.terminar_trecho()
            return True

    class PainelEsboco3D:
        """Pontos em tabela; próximo ponto absoluto ou relativo ao anterior; clique no modelo."""

        def __init__(self, obj, novo):
            self.obj = obj
            self.novo = novo
            self.doc = obj.Document
            self._cb = None
            self._vista = None
            self._ocupado = False
            self._ramal_pendente = False
            self._cb_mov = None
            self._filtro = None
            self._previa = None
            self._candidato = None
            self._ultimo_mouse = None
            self.plano = "XY"
            self.form = QtWidgets.QWidget()
            self.form.setWindowTitle("Esboço 3D")
            self.form.setWindowIcon(QtGui.QIcon(PrumoUtil.icone("esboco3d.svg")))
            lay = QtWidgets.QVBoxLayout(self.form)
            dica = QtWidgets.QLabel(
                "Clique em <b>Desenhar</b> e vá clicando na vista: o ponto cai no plano que passa pelo "
                "último ponto (<b>Tab</b> troca XY → YZ → ZX) e encaixa em vértices e pontas de arestas. "
                "<b>Esc</b> termina o trecho; o próximo clique começa um ramal. Para medidas exatas, "
                "digite o próximo ponto abaixo e tecle Enter.")
            dica.setWordWrap(True)
            lay.addWidget(dica)
            self.tabela = QtWidgets.QTableWidget(0, 3)
            self.tabela.setHorizontalHeaderLabels(["X (mm)", "Y (mm)", "Z (mm)"])
            self.tabela.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.tabela.setMinimumHeight(170)
            self.tabela.cellChanged.connect(self._celula)
            lay.addWidget(self.tabela)
            caixa = QtWidgets.QGroupBox("Próximo ponto")
            g = QtWidgets.QGridLayout(caixa)
            self.relativo = QtWidgets.QCheckBox("Relativo ao último ponto (ΔX, ΔY, ΔZ)")
            self.relativo.setChecked(True)
            g.addWidget(self.relativo, 0, 0, 1, 4)
            self.coord = []
            for i, n in enumerate("XYZ"):
                s = QtWidgets.QDoubleSpinBox()
                s.setRange(-1e7, 1e7)
                s.setDecimals(2)
                s.setSuffix(" mm")
                s.setPrefix(n + " ")
                s.setKeyboardTracking(False)
                s.lineEdit().returnPressed.connect(self.adicionar_digitado)
                g.addWidget(s, 1, i)
                self.coord.append(s)
            bt_add = QtWidgets.QPushButton("Adicionar")
            bt_add.setToolTip("Adiciona o ponto (Enter num dos campos faz o mesmo)")
            bt_add.clicked.connect(self.adicionar_digitado)
            g.addWidget(bt_add, 1, 3)
            lay.addWidget(caixa)
            bl = QtWidgets.QHBoxLayout()
            self.bt_clicar = QtWidgets.QPushButton("Desenhar")
            self.bt_clicar.setCheckable(True)
            self.bt_clicar.setToolTip("Clique na vista para pôr pontos; Tab troca o plano, Esc termina o trecho")
            self.bt_clicar.toggled.connect(self._modo_clique)
            self.bt_ramal = QtWidgets.QPushButton("Novo trecho")
            self.bt_ramal.setCheckable(True)
            self.bt_ramal.setToolTip("O próximo ponto começa uma linha separada (ramal)")
            self.bt_ramal.toggled.connect(self._ramal)
            bt_rem = QtWidgets.QPushButton("Remover ponto")
            bt_rem.setToolTip("Remove o ponto selecionado na tabela (ou o último)")
            bt_rem.clicked.connect(self.remover)
            for b in (self.bt_clicar, self.bt_ramal, bt_rem):
                bl.addWidget(b)
            lay.addLayout(bl)
            fl = QtWidgets.QFormLayout()
            self.fechado = QtWidgets.QCheckBox("Ligar o último ponto ao primeiro")
            self.fechado.setChecked(bool(obj.Fechado))
            self.fechado.toggled.connect(self._opcoes)
            fl.addRow("Fechado", self.fechado)
            self.raio = QtWidgets.QDoubleSpinBox()
            self.raio.setRange(0.0, 1e6)
            self.raio.setDecimals(2)
            self.raio.setSuffix(" mm")
            self.raio.setValue(float(obj.RaioCurva))
            self.raio.setToolTip("Arredonda os cantos com arcos (curva de tubo). 0 = cantos vivos")
            self.raio.valueChanged.connect(self._opcoes)
            fl.addRow("Raio nos cantos", self.raio)
            hp = QtWidgets.QHBoxLayout()
            self.lb_plano = QtWidgets.QLabel(self.plano)
            self.lb_plano.setStyleSheet("font-weight:700; color:#003A70;")
            bt_plano = QtWidgets.QPushButton("Trocar (Tab)")
            bt_plano.clicked.connect(self.trocar_plano)
            hp.addWidget(self.lb_plano)
            hp.addWidget(bt_plano)
            hp.addStretch(1)
            fl.addRow("Plano de desenho", hp)
            self.passo = QtWidgets.QDoubleSpinBox()
            self.passo.setRange(0.0, 1e5)
            self.passo.setDecimals(2)
            self.passo.setSuffix(" mm")
            self.passo.setValue(10.0)
            self.passo.setToolTip("Os pontos clicados no plano andam de passo em passo a partir do último "
                                  "(0 = livre)")
            fl.addRow("Passo do cursor", self.passo)
            lay.addLayout(fl)
            self.estado = QtWidgets.QLabel("")
            self.estado.setWordWrap(True)
            lay.addWidget(self.estado)
            self._encher()

        # ---- dados
        def pontos(self):
            return [FreeCAD.Vector(p) for p in self.obj.Pontos]

        def _gravar(self, pts, quebras=None):
            self.obj.Pontos = pts
            if quebras is not None:
                self.obj.Quebras = sorted({q for q in quebras if 0 < q < len(pts)})
            self.doc.recompute()
            self._encher()

        def _encher(self):
            self._ocupado = True
            try:
                pts = self.pontos()
                quebras = set(self.obj.Quebras)
                self.tabela.setRowCount(len(pts))
                rot = []
                trecho = 1
                for i, p in enumerate(pts):
                    if i in quebras:
                        trecho += 1
                    rot.append(("▶ " if i in quebras else "") + str(i + 1))
                    for j, v in enumerate((p.x, p.y, p.z)):
                        it = QtWidgets.QTableWidgetItem(("%.2f" % v).replace(".", ","))
                        self.tabela.setItem(i, j, it)
                self.tabela.setVerticalHeaderLabels(rot)
                if pts:
                    self.tabela.scrollToBottom()
            finally:
                self._ocupado = False
            self._mostrar_estado()

        def _ramal(self, v):
            self._ramal_pendente = bool(v)
            self._mostrar_estado()

        def _celula(self, lin, col):
            if self._ocupado:
                return
            it = self.tabela.item(lin, col)
            try:
                v = float(it.text().replace(".", "").replace(",", ".")) if "," in it.text() \
                    else float(it.text())
            except (ValueError, AttributeError):
                self._encher()
                return
            pts = self.pontos()
            p = pts[lin]
            pts[lin] = FreeCAD.Vector(*(v if k == col else (p.x, p.y, p.z)[k] for k in range(3)))
            self._gravar(pts)

        def _opcoes(self, *_a):
            self.obj.Fechado = self.fechado.isChecked()
            self.obj.RaioCurva = self.raio.value()
            self.doc.recompute()
            self._encher()

        def adicionar(self, p_local):
            pts = self.pontos()
            quebras = list(self.obj.Quebras)
            if self._ramal_pendente and pts:
                quebras.append(len(pts))
                self.bt_ramal.setChecked(False)
            pts.append(FreeCAD.Vector(p_local))
            self._gravar(pts, quebras)

        def adicionar_digitado(self):
            v = FreeCAD.Vector(*(s.value() for s in self.coord))
            pts = self.pontos()
            if self.relativo.isChecked() and pts and not self._ramal_pendente:
                v = pts[-1] + v
            self.adicionar(v)
            if self.relativo.isChecked():
                for s in self.coord:
                    s.setValue(0.0)
            self.coord[0].setFocus()
            self.coord[0].selectAll()

        def remover(self):
            pts = self.pontos()
            if not pts:
                return
            linhas = sorted({i.row() for i in self.tabela.selectedIndexes()})
            i = linhas[-1] if linhas else len(pts) - 1
            del pts[i]
            quebras = [q - 1 if q > i else q for q in self.obj.Quebras if q != i]
            self._gravar(pts, quebras)

        # ---- desenhar na vista: plano pelo último ponto (Tab troca), encaixe em vértices
        def _modo_clique(self, ligado):
            self._desligar_clique()
            if not ligado:
                self._mostrar_estado()
                return
            gdoc = FreeCADGui.getDocument(self.doc.Name)
            vista = gdoc.activeView() if gdoc else None
            if vista is None or not hasattr(vista, "addEventCallback"):
                self.bt_clicar.setChecked(False)
                return
            self._vista = vista
            self._cb = vista.addEventCallback("SoMouseButtonEvent", self._clique)
            self._cb_mov = vista.addEventCallback("SoLocation2Event", self._mover)
            self._previa = Previa(vista)
            self._filtro = FiltroTeclas(self)
            QtWidgets.QApplication.instance().installEventFilter(self._filtro)
            self._mostrar_estado()

        def _desligar_clique(self):
            if self._vista is not None:
                for tipo, cb in (("SoMouseButtonEvent", self._cb), ("SoLocation2Event", self._cb_mov)):
                    if cb is not None:
                        try:
                            self._vista.removeEventCallback(tipo, cb)
                        except Exception:
                            pass
            if self._filtro is not None:
                QtWidgets.QApplication.instance().removeEventFilter(self._filtro)
            if self._previa is not None:
                self._previa.remover()
            self._cb = self._cb_mov = self._vista = self._filtro = self._previa = None
            self._candidato = None

        def trocar_plano(self):
            self.plano = proximo_plano(self.plano)
            self.lb_plano.setText(self.plano)
            if self._ultimo_mouse is not None and self._vista is not None:
                self._mover({"Position": self._ultimo_mouse})
            self._mostrar_estado()

        def terminar_trecho(self):
            """Esc: o próximo ponto começa um trecho novo; Esc de novo para de desenhar."""
            if self._ramal_pendente or not self.obj.Pontos:
                self.bt_clicar.setChecked(False)
                return
            self.bt_ramal.setChecked(True)
            if self._previa is not None:
                self._previa.linha(None, None)
            self._mostrar_estado()

        def _base_global(self):
            pts = self.pontos()
            if pts and not self._ramal_pendente:
                return self.obj.Placement.multVec(pts[-1])
            return self.obj.Placement.multVec(FreeCAD.Vector())

        def _raio_da_vista(self, pos):
            v = self._vista
            p0 = FreeCAD.Vector(v.getPoint(*pos))
            d = FreeCAD.Vector(v.getViewDirection())
            try:
                cam = v.getCameraNode()
                if cam.getTypeId().getName() == "PerspectiveCamera":
                    olho = FreeCAD.Vector(*cam.position.getValue().getValue())
                    d = p0 - olho
            except Exception:
                pass
            return p0, d

        def ponto_em(self, pos):
            """(ponto global, tipo) sob o cursor: vértice/ponta de aresta encaixa; senão o plano."""
            try:
                info = self._vista.getObjectInfo(pos)
            except Exception:
                info = None
            if info and (info.get("Component", "") or "").startswith(("Vertex", "Edge")):
                p, tipo = _ponto_clicado(info)
                if tipo in ("vértice", "ponta da aresta"):
                    return p, tipo
            base = self._base_global()
            p0, d = self._raio_da_vista(pos)
            p = no_plano(p0, d, base, self.plano)
            if p is None:
                return None, "plano %s de perfil para a vista: tecle Tab" % self.plano
            return na_grade(p, base, self.passo.value(), self.plano), "plano " + self.plano

        def _mover(self, ev):
            pos = ev.get("Position")
            if pos is None or self._vista is None:
                return
            self._ultimo_mouse = pos
            p, tipo = self.ponto_em(pos)
            self._candidato = (p, tipo)
            pts = self.pontos()
            ini = None if (self._ramal_pendente or not pts) else self.obj.Placement.multVec(pts[-1])
            if self._previa is not None:
                self._previa.linha(ini, p)
            self._mostrar_estado()

        def _clique(self, ev):
            if ev.get("Button") != "BUTTON1" or ev.get("State") != "DOWN":
                return
            p, tipo = self.ponto_em(ev["Position"])
            if p is None:
                self.estado.setText(tipo)
                return
            self.adicionar(self.obj.Placement.inverse().multVec(p))
            self._mover(ev)

        def _mostrar_estado(self):
            pts = self.pontos()
            comp = PrumoUtil.fmt(float(self.obj.Comprimento), 1)
            linhas = ["%d ponto(s), %d trecho(s), comprimento %s mm" % (
                len(pts), len(trechos(pts, self.obj.Quebras)), comp) if pts else "Nenhum ponto ainda."]
            if self._vista is not None:
                linhas.append("<b>Plano %s</b> — <b>Tab</b> troca o plano; <b>Esc</b> termina o trecho "
                              "(Esc de novo para de desenhar)." % self.plano)
                c = self._candidato
                if c and c[0] is not None:
                    p = c[0]
                    txt = "Cursor: X %s  Y %s  Z %s (%s)" % (PrumoUtil.fmt(p.x, 1), PrumoUtil.fmt(p.y, 1),
                                                             PrumoUtil.fmt(p.z, 1), c[1])
                    if pts and not self._ramal_pendente:
                        L = (p - self.obj.Placement.multVec(pts[-1])).Length
                        txt += " — trecho de %s mm" % PrumoUtil.fmt(L, 1)
                    linhas.append(txt)
                elif c:
                    linhas.append(c[1])
            if self._ramal_pendente:
                linhas.append("Próximo ponto começa um trecho novo.")
            self.estado.setText("<br>".join(linhas))

        # ---- diálogo
        def getStandardButtons(self):
            return QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        def accept(self):
            self._desligar_clique()
            self.doc.commitTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

        def reject(self):
            self._desligar_clique()
            self.doc.abortTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

    def abrir_painel(obj=None):
        doc = obj.Document if obj is not None else FreeCAD.ActiveDocument
        if doc is None:
            doc = FreeCAD.newDocument()
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        doc.openTransaction("Esboço 3D")
        novo = obj is None
        if novo:
            obj = criar(doc)
        painel = PainelEsboco3D(obj, novo)
        FreeCADGui.Control.showDialog(painel)
        return painel

    class CmdEsboco3D:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("esboco3d.svg"),
                    "MenuText": "Esboço 3D",
                    "ToolTip": "Linhas no espaço por pontos X, Y, Z (digitados ou clicados no modelo), com "
                               "ramais e curvas nos cantos. Serve de esqueleto de estrutura e de caminho de "
                               "tubo ou varredura."}

        def IsActive(self):
            return True

        def Activated(self):
            abrir_painel()
