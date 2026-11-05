# -*- coding: utf-8 -*-
"""Medir (Usinix): painel em português que mede o que estiver selecionado, sem escolher modo.

Um ponto dá a posição; uma aresta, o comprimento (e raio/diâmetro se for círculo); uma face, a área (e o
raio se for cilíndrica); uma peça inteira, volume, área, centro de massa e caixa. Dois itens dão a distância
mínima (com ΔX, ΔY, ΔZ), a distância entre centros quando os dois são redondos e o ângulo quando os dois são
retos ou planos. Mais itens dão a soma de comprimentos e de áreas. A distância aparece também na vista 3D,
numa linha amarela entre os pontos mais próximos.
"""

import math

import FreeCAD
import FreeCADGui

V = FreeCAD.Vector


def _num(x, casas=2):
    s = ("%." + str(casas) + "f") % x
    inteiro, _, dec = s.partition(".")
    neg = inteiro.startswith("-")
    inteiro = inteiro.lstrip("-")
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    return ("-" if neg else "") + ".".join(grupos) + ("," + dec if dec else "")


def mm(x):
    return _num(x) + " mm"


def mm2(x):
    return _num(x) + " mm²"


def mm3(x):
    return _num(x) + " mm³"


def graus(x):
    return _num(x, 2) + "°"


def ponto(p):
    return "X %s · Y %s · Z %s" % (_num(p.x), _num(p.y), _num(p.z))


# ---------------------------------------------------------------- o que é cada item

class Item:
    """Um item medido: o nome mostrado e a forma (já na posição global)."""

    def __init__(self, rotulo, shape):
        self.rotulo = rotulo
        self.shape = shape

    @property
    def tipo(self):
        st = self.shape.ShapeType
        return {"Vertex": "ponto", "Edge": "aresta", "Face": "face"}.get(st, "peça")


def _curva(e):
    try:
        return e.Curve
    except Exception:
        return None


def _circulo(it):
    """Centro, raio e eixo se o item for redondo (aresta circular ou face cilíndrica/esférica)."""
    import Part
    sh = it.shape
    if sh.ShapeType == "Edge":
        c = _curva(sh)
        if isinstance(c, Part.Circle):
            return c.Center, c.Radius, c.Axis
    if sh.ShapeType == "Face":
        s = sh.Surface
        if isinstance(s, (Part.Cylinder, Part.Cone)) and hasattr(s, "Radius"):
            return sh.CenterOfMass, s.Radius, s.Axis
        if isinstance(s, Part.Sphere):
            return s.Center, s.Radius, None
    return None


def _direcao(it):
    """Direção de uma aresta reta, ou normal de uma face plana (com o tipo)."""
    import Part
    sh = it.shape
    if sh.ShapeType == "Edge" and isinstance(_curva(sh), Part.Line):
        d = sh.Vertexes[-1].Point - sh.Vertexes[0].Point
        if d.Length > 1e-9:
            return d.normalize(), "reta"
    if sh.ShapeType == "Face":
        try:
            if isinstance(sh.Surface, Part.Plane):
                u0, u1, v0, v1 = sh.ParameterRange
                return sh.normalAt((u0 + u1) / 2, (v0 + v1) / 2), "plano"
        except Exception:
            pass
    c = _circulo(it)
    if c is not None and c[2] is not None:
        return V(c[2]).normalize(), "eixo"
    return None


def _angulo(a, b):
    """Ângulo entre duas direções (0–90° entre retas/eixos; planos dão o ângulo entre as faces)."""
    (da, ta), (db, tb) = a, b
    cosv = max(-1.0, min(1.0, da.dot(db)))
    ang = math.degrees(math.acos(abs(cosv)))
    if ta == "plano" and tb == "plano":
        return ang                      # entre faces: 0 = paralelas, 90 = perpendiculares
    if (ta == "plano") != (tb == "plano"):
        return 90.0 - ang               # reta x plano: o ângulo com o plano
    return ang


def medir(itens):
    """Lista de (rótulo, valor em texto) e, se houver, o par de pontos mais próximos (para a linha)."""
    out, par = [], None
    if not itens:
        return out, par
    if len(itens) == 1:
        it = itens[0]
        sh = it.shape
        if it.tipo == "ponto":
            out.append(("Posição", ponto(sh.Point)))
        elif it.tipo == "aresta":
            out.append(("Comprimento", mm(sh.Length)))
            c = _circulo(it)
            if c is not None:
                out.append(("Raio", mm(c[1])))
                out.append(("Diâmetro", mm(2 * c[1])))
                out.append(("Centro", ponto(c[0])))
            else:
                out.append(("Do início ao fim", mm(sh.Vertexes[0].Point.distanceToPoint(sh.Vertexes[-1].Point))
                            if len(sh.Vertexes) > 1 else mm(0)))
        elif it.tipo == "face":
            out.append(("Área", mm2(sh.Area)))
            c = _circulo(it)
            if c is not None:
                out.append(("Raio", mm(c[1])))
                out.append(("Diâmetro", mm(2 * c[1])))
            out.append(("Perímetro", mm(sum(e.Length for e in sh.OuterWire.Edges)) if hasattr(sh, "OuterWire")
                        else mm(sum(e.Length for e in sh.Edges))))
        else:
            if sh.Volume > 1e-9:
                out.append(("Volume", mm3(sh.Volume)))
            out.append(("Área", mm2(sh.Area)))
            try:
                out.append(("Centro de massa", ponto(sh.CenterOfMass)))
            except Exception:
                pass
            bb = sh.BoundBox
            out.append(("Tamanho (caixa)", "%s × %s × %s mm" % (_num(bb.XLength), _num(bb.YLength),
                                                               _num(bb.ZLength))))
        return out, par

    if len(itens) == 2:
        a, b = itens
        try:
            d, pares, _ = a.shape.distToShape(b.shape)
            pa, pb = pares[0]
            out.append(("Distância mínima", mm(d)))
            dv = pb - pa
            out.append(("ΔX · ΔY · ΔZ", "%s · %s · %s mm" % (_num(abs(dv.x)), _num(abs(dv.y)), _num(abs(dv.z)))))
            par = (pa, pb)
        except Exception:
            pass
        ca, cb = _circulo(a), _circulo(b)
        if ca is not None and cb is not None:
            out.append(("Entre centros", mm(ca[0].distanceToPoint(cb[0]))))
            if par is None or (ca[0] - cb[0]).Length > 1e-9:
                par = (ca[0], cb[0])
        da, db = _direcao(a), _direcao(b)
        if da is not None and db is not None:
            ang = _angulo(da, db)
            out.append(("Ângulo", graus(ang)))
            if da[1] == "plano" and db[1] == "plano" and ang < 1e-6:
                # faces paralelas: a distância entre os planos
                out.append(("Entre as faces", mm(abs((b.shape.CenterOfMass - a.shape.CenterOfMass).dot(da[0])))))
        return out, par

    arestas = [i for i in itens if i.tipo == "aresta"]
    faces = [i for i in itens if i.tipo == "face"]
    pontos = [i for i in itens if i.tipo == "ponto"]
    if arestas:
        out.append(("Soma dos comprimentos (%d arestas)" % len(arestas), mm(sum(i.shape.Length for i in arestas))))
    if faces:
        out.append(("Soma das áreas (%d faces)" % len(faces), mm2(sum(i.shape.Area for i in faces))))
    if len(pontos) == 3 and len(itens) == 3:
        p0, p1, p2 = (i.shape.Point for i in pontos)
        u, w = p0 - p1, p2 - p1
        if u.Length > 1e-9 and w.Length > 1e-9:
            out.append(("Ângulo no 2º ponto", graus(math.degrees(u.getAngle(w)))))
    return out, par


# ---------------------------------------------------------------- seleção -> itens

def itens_da_selecao():
    import Part
    itens = []
    for s in FreeCADGui.Selection.getSelectionEx("", 0):
        subs = [n for n in s.SubElementNames] or [""]
        for sub in subs:
            try:
                sh = Part.getShape(s.Object, sub, needSubElement=True, retType=0)
            except Exception:
                continue
            if sh is None or sh.isNull():
                continue
            elem = sub.split(".")[-1] if sub else ""
            if not elem:
                try:
                    alvo = s.Object.getSubObject(sub, retType=1) if sub else s.Object
                except Exception:
                    alvo = s.Object
                rot = getattr(alvo, "Label", s.Object.Label)
            else:
                dono = sub[:-len(elem)].rstrip(".").split(".")[-1] or s.Object.Name
                o = s.Object.Document.getObject(dono)
                rot = "%s · %s" % (o.Label if o is not None else dono, _nome_elem(elem))
            itens.append(Item(rot, sh))
    return itens


def _nome_elem(elem):
    for en, pt in (("Vertex", "Ponto "), ("Edge", "Aresta "), ("Face", "Face ")):
        if elem.startswith(en):
            return pt + elem[len(en):]
    return elem


# ---------------------------------------------------------------- linha na vista 3D

class _Linha:
    def __init__(self):
        self.no = None
        self.vista = None

    def mostrar(self, par):
        self.tirar()
        if par is None:
            return
        try:
            from pivy import coin
            vista = FreeCADGui.ActiveDocument.ActiveView
            sg = vista.getSceneGraph()
        except Exception:
            return
        pa, pb = par
        sep = coin.SoSeparator()
        sep.setName("PrumoMedirLinha")
        estilo = coin.SoDrawStyle()
        estilo.lineWidth = 3
        estilo.pointSize = 9
        cor = coin.SoBaseColor()
        cor.rgb.setValue(0.969, 0.745, 0.0)       # amarelo Usinix
        caixa = coin.SoAnnotation()               # por cima do modelo
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, 2, [(pa.x, pa.y, pa.z), (pb.x, pb.y, pb.z)])
        caixa.addChild(estilo)
        caixa.addChild(cor)
        caixa.addChild(coords)
        caixa.addChild(coin.SoLineSet())
        caixa.addChild(coin.SoPointSet())
        sep.addChild(caixa)
        sg.addChild(sep)
        self.no, self.vista = sep, sg

    def tirar(self):
        if self.no is not None and self.vista is not None:
            try:
                self.vista.removeChild(self.no)
            except Exception:
                pass
        self.no = self.vista = None


# ---------------------------------------------------------------- painel

class Painel:
    def __init__(self):
        from PySide import QtCore, QtWidgets
        import PrumoUI as UI
        self.form = UI.raiz()
        self.form.setWindowTitle("Medir")
        lay = QtWidgets.QVBoxLayout(self.form)
        lay.setContentsMargins(0, 0, 0, 0)
        corpo, v = UI.coluna(margens=(0, 4, 0, 4))
        lay.addWidget(corpo)   # o painel de tarefas já rola: sem rolagem dentro (cortava os cartões)
        c = UI.Cartao("Seleção", "selecao")
        self.sel = QtWidgets.QLabel()
        self.sel.setWordWrap(True)
        self.sel.setObjectName("PrumoSub")
        c.widget(self.sel)
        v.addWidget(c)
        self.cartao_res = UI.Cartao("Medidas", "regua" if "regua" in UI.ICONES else None)
        self.grade = QtWidgets.QGridLayout()
        self.grade.setHorizontalSpacing(10)
        self.grade.setVerticalSpacing(6)
        box = QtWidgets.QWidget()
        box.setLayout(self.grade)
        self.cartao_res.widget(box)
        v.addWidget(self.cartao_res)
        botoes = QtWidgets.QHBoxLayout()
        self.bt_copiar = QtWidgets.QPushButton("Copiar medidas")
        self.bt_copiar.clicked.connect(self.copiar)
        self.bt_limpar = QtWidgets.QPushButton("Limpar seleção")
        self.bt_limpar.clicked.connect(lambda: FreeCADGui.Selection.clearSelection())
        botoes.addWidget(self.bt_copiar)
        botoes.addWidget(self.bt_limpar)
        v.addLayout(botoes)
        dica = UI.Dica("Clique em pontos, arestas, faces ou peças. Com Ctrl, junta mais itens: dois itens dão "
                       "distância e ângulo.") if hasattr(UI, "Dica") else QtWidgets.QLabel()
        v.addWidget(dica)
        v.addStretch(1)
        self.linha = _Linha()
        self.linhas = []
        self._timer = QtCore.QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self.atualizar)
        FreeCADGui.Selection.addObserver(self)
        self.atualizar()

    # observador de seleção
    def addSelection(self, *a):
        self._timer.start()

    def removeSelection(self, *a):
        self._timer.start()

    def setSelection(self, *a):
        self._timer.start()

    def clearSelection(self, *a):
        self._timer.start()

    def atualizar(self):
        from PySide import QtCore, QtWidgets
        try:
            itens = itens_da_selecao()
        except Exception:
            itens = []
        if not itens:
            self.sel.setText("Nada selecionado.")
        else:
            nomes = [i.rotulo for i in itens]
            self.sel.setText(", ".join(nomes[:5]) + (" … (+%d)" % (len(nomes) - 5) if len(nomes) > 5 else ""))
        try:
            res, par = medir(itens)
        except Exception as ex:
            res, par = [("Não deu para medir", str(ex))], None
        while self.grade.count():
            w = self.grade.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        if not res and itens:
            res = [("Sem medida para essa combinação", "")]
        for n, (rot, val) in enumerate(res):
            a = QtWidgets.QLabel(rot)
            a.setObjectName("PrumoRotulo")
            a.setWordWrap(True)
            b = QtWidgets.QLabel(val)
            b.setTextInteractionFlags(b.textInteractionFlags() | QtCore.Qt.TextSelectableByMouse)
            f = b.font()
            f.setBold(True)
            b.setFont(f)
            self.grade.addWidget(a, n, 0)
            self.grade.addWidget(b, n, 1, QtCore.Qt.AlignRight)
        self.cartao_res.setVisible(bool(res))
        self.linhas = res
        self.linha.mostrar(par)

    def copiar(self):
        from PySide import QtWidgets
        txt = "\n".join("%s: %s" % (r, v) if v else r for r, v in self.linhas)
        QtWidgets.QApplication.clipboard().setText(txt)

    def _sair(self):
        try:
            FreeCADGui.Selection.removeObserver(self)
        except Exception:
            pass
        self.linha.tirar()

    def getStandardButtons(self):
        from PySide import QtWidgets
        b = QtWidgets.QDialogButtonBox.Close
        return b.value if hasattr(b, "value") else int(b)

    def reject(self):
        self._sair()
        FreeCADGui.Control.closeDialog()
        return True

    def accept(self):
        return self.reject()


def abrir():
    if FreeCADGui.Control.activeDialog():
        FreeCADGui.Control.closeDialog()
    p = Painel()
    FreeCADGui.Control.showDialog(p)
    return p


class CmdMedir:
    def GetResources(self):
        return {"Pixmap": "umf-measurement", "MenuText": "Medir",
                "ToolTip": "Mede o que estiver selecionado: posição, comprimento, raio, área, volume, distância "
                           "e ângulo, em português"}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        abrir()


def registrar_comandos():
    if "Prumo_Medir" not in FreeCADGui.listCommands():
        FreeCADGui.addCommand("Prumo_Medir", CmdMedir())
