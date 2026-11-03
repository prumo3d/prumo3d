# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: ao criar um esboço, mostrar os planos com os eixos X, Y e Z.

- Janela "Escolher orientação" (Novo esboço da aba Esboço): o cubo pequeno dá lugar a um desenho dos três
  planos (XY, XZ, YZ) com os eixos e a origem; o plano escolhido fica em destaque.
- Painel de escolha do plano (Esboço da aba Peça): além dos planos, a vista 3D mostra os eixos X, Y e Z da
  origem do corpo. Com o corpo vazio, a vista vai para a isométrica, onde os três planos aparecem.
  Ao fechar o painel o FreeCAD devolve a visibilidade de antes (planos e eixos voltam a ficar ocultos).
"""
import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

AZUL = "#003A70"
AMARELO = "#F7BE00"
TAM = (200, 165)
_ESTADO = {"filtro": None}


# ------------------------------------------------------------------ desenho dos planos
def _iso(x, y, z, esc, ox, oy):
    """Projeção isométrica (X para a direita e para baixo, Y para a direita e para cima, Z para cima)."""
    import math
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    return QtCore.QPointF(ox + (x + y) * c * esc, oy + (x - y) * s * esc - z * esc)


def desenho_planos(plano="XY", invertido=False, largura=TAM[0], altura=TAM[1], escuro=False):
    """QPixmap com os três planos e os eixos; `plano` ("XY", "XZ", "YZ" ou None) fica em destaque."""
    dpr = 2.0
    pm = QtGui.QPixmap(int(largura * dpr), int(altura * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    # extensão do desenho: 1,73·esc na largura; 1,5·esc acima e 0,5·esc abaixo da origem
    esc = min(largura / 1.95, altura / 2.2)
    ox, oy = (largura - 1.73 * esc) / 2.0, (altura - 2.0 * esc) / 2.0 + 1.5 * esc
    base = QtGui.QColor("#8CBCEB" if escuro else AZUL)
    texto = QtGui.QColor("#DCE6F0" if escuro else AZUL)
    a, b = 0.12, 1.0          # os planos começam um pouco afastados da origem, como na vista 3D

    planos = {
        "YZ": [(0, a, a), (0, b, a), (0, b, b), (0, a, b)],
        "XZ": [(a, 0, a), (b, 0, a), (b, 0, b), (a, 0, b)],
        "XY": [(a, a, 0), (b, a, 0), (b, b, 0), (a, b, 0)],
    }
    rotulo_pos = {"YZ": (0, 0.62, 0.80), "XZ": (0.64, 0, 0.78), "XY": (0.70, 0.62, 0)}
    for nome in ("YZ", "XZ", "XY"):
        pts = [_iso(x, y, z, esc, ox, oy) for x, y, z in planos[nome]]
        destaque = (nome == plano)
        cor = QtGui.QColor(AMARELO if destaque else base)
        cor.setAlphaF(0.85 if destaque else 0.32)
        borda = QtGui.QColor("#B88A00" if destaque else base)
        p.setPen(QtGui.QPen(borda, 1.4 if destaque else 1.0))
        p.setBrush(cor)
        p.drawPolygon(QtGui.QPolygonF(pts))
        f = p.font()
        f.setBold(True)
        f.setPointSizeF(9.5 if destaque else 8.5)
        p.setFont(f)
        p.setPen(QtGui.QColor("#3D2E00") if destaque else texto)
        c = _iso(*rotulo_pos[nome], esc=esc, ox=ox, oy=oy)
        p.drawText(QtCore.QRectF(c.x() - 16, c.y() - 9, 32, 18), QtCore.Qt.AlignCenter, nome)

    # eixos e origem
    o = _iso(0, 0, 0, esc, ox, oy)
    f = p.font()
    f.setBold(False)
    f.setPointSizeF(8)
    p.setFont(f)
    for nome, (x, y, z) in (("X", (0.55, 0, 0)), ("Y", (0, 0.45, 0)), ("Z", (0, 0, 0.55))):
        fim = _iso(x, y, z, esc, ox, oy)
        p.setPen(QtGui.QPen(QtGui.QColor("#0B1F33") if not escuro else texto, 1.8))
        p.drawLine(o, fim)
        d = fim - o
        n = max((d.x() ** 2 + d.y() ** 2) ** 0.5, 1)
        q = fim + QtCore.QPointF(d.x() / n * 9, d.y() / n * 9)
        p.drawText(QtCore.QRectF(q.x() - 7, q.y() - 7, 14, 14), QtCore.Qt.AlignCenter, nome)
    p.setPen(QtCore.Qt.NoPen)
    p.setBrush(QtGui.QColor("#3D8BFD"))
    p.drawEllipse(o, 3, 3)

    if plano and invertido:
        p.setPen(texto)
        f.setPointSizeF(7.5)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, altura - 14, largura, 14), QtCore.Qt.AlignCenter, "direção invertida")
    p.end()
    return pm


def _escuro():
    try:
        import PrumoEstilo
        return PrumoEstilo.escuro()
    except Exception:
        return False


# ------------------------------------------------------------------ janela "Escolher orientação"
class _Desenho(QtCore.QObject):
    """Filho da janela que redesenha a prévia. Não guarda objetos Python dos widgets: o PySide invalida esses
    invólucros quando outro código pega o mesmo widget; tudo é buscado de novo a partir de parent()."""

    def atualizar(self, *_a):
        dlg = self.parent()
        if dlg is None:
            return
        rotulo = dlg.findChild(QtWidgets.QLabel, "previewLabel")
        if rotulo is None:
            return
        plano = None
        for n in ("XY", "XZ", "YZ"):
            r = dlg.findChild(QtWidgets.QRadioButton, n + "_radioButton")
            if r is not None and r.isChecked():
                plano = n
        inv = dlg.findChild(QtWidgets.QCheckBox, "Reverse_checkBox")
        rotulo.setPixmap(desenho_planos(plano, bool(inv is not None and inv.isChecked()), escuro=_escuro()))


def ajustar_dialogo(dlg):
    """Troca o cubo da janela de orientação pelo desenho dos planos e o mantém em dia com a escolha."""
    import shiboken6
    if not shiboken6.isValid(dlg) or dlg.findChild(_Desenho) is not None:
        return False
    rotulo = dlg.findChild(QtWidgets.QLabel, "previewLabel")
    radios = [dlg.findChild(QtWidgets.QRadioButton, n + "_radioButton") for n in ("XY", "XZ", "YZ")]
    inv = dlg.findChild(QtWidgets.QCheckBox, "Reverse_checkBox")
    if rotulo is None or None in radios:
        return False
    rotulo.setMinimumSize(*TAM)
    rotulo.setMaximumSize(*TAM)
    rotulo.setToolTip("Planos XY, XZ e YZ com os eixos X, Y e Z; o plano escolhido fica em amarelo.")
    des = _Desenho(dlg)
    # o FreeCAD redesenha o cubo no "clicked"; nossas ligações vêm depois da dele, então o desenho fica por último
    for w in radios + ([inv] if inv is not None else []):
        w.toggled.connect(des.atualizar)
        w.clicked.connect(des.atualizar)
    des.atualizar()
    dlg.adjustSize()
    return True


# ------------------------------------------------------------------ painel de escolha do plano (Peça)
def _origens_em_escolha(doc):
    """Origens com planos mostrados temporariamente (painel de escolha aberto)."""
    res = []
    for o in (doc.Objects if doc else []):
        if o.TypeId not in ("App::Origin", "App::LocalCoordinateSystem"):
            continue
        try:
            filhos = list(o.OriginFeatures)
        except Exception:
            continue
        planos = [f for f in filhos if getattr(f, "Role", "").endswith("_Plane")]
        if planos and any(getattr(f.ViewObject, "Visibility", False) for f in planos):
            res.append((o, filhos))
    return res


def mostrar_eixos():
    """Com o painel de escolha do plano aberto: mostra também os eixos (o FreeCAD só mostra os planos)."""
    try:
        if not FreeCADGui.Control.activeDialog():
            return 0
    except Exception:
        return 0
    doc = FreeCAD.ActiveDocument
    ligados = []
    for _o, filhos in _origens_em_escolha(doc):
        for f in filhos:
            if getattr(f, "Role", "").endswith("_Axis") and not f.ViewObject.Visibility:
                f.ViewObject.Visibility = True
                ligados.append((doc.Name, f.Name))
    if ligados:
        _ESTADO.setdefault("eixos", []).extend(ligados)
        _vista_que_mostra_os_planos(doc)
        _vigiar_fechamento()
    return len(ligados)


def _vigiar_fechamento():
    """Quando o painel fecha, esconde de novo os eixos que a Prumo mostrou (se ainda estiverem à vista)."""
    if _ESTADO.get("vigia") is not None:
        return
    t = QtCore.QTimer(QtWidgets.QApplication.instance())
    t.setInterval(250)

    def conferir():
        try:
            aberto = FreeCADGui.Control.activeDialog()
        except Exception:
            aberto = False
        if aberto:
            return
        restaurar_eixos()
        t.stop()
        t.deleteLater()
        _ESTADO["vigia"] = None

    t.timeout.connect(conferir)
    t.start()
    _ESTADO["vigia"] = t


def restaurar_eixos():
    for doc_nome, nome in _ESTADO.pop("eixos", []):
        try:
            o = FreeCAD.getDocument(doc_nome).getObject(nome)
            if o is not None and o.ViewObject.Visibility:
                o.ViewObject.Visibility = False
        except Exception:
            pass


def _vista_que_mostra_os_planos(doc):
    """Corpo vazio numa vista de topo/frente/lado: os planos XZ e YZ ficariam de perfil. Vai para a isométrica."""
    try:
        for o in doc.Objects:
            vo = getattr(o, "ViewObject", None)
            if (vo is not None and vo.Visibility and hasattr(o, "Shape") and o.TypeId != "PartDesign::Body"
                    and not o.Shape.isNull() and o.Shape.Volume > 1e-9):
                return
        v = FreeCADGui.ActiveDocument.ActiveView
        v.viewIsometric()
        v.fitAll()
        QtCore.QTimer.singleShot(400, lambda: _enquadrar())
    except Exception:
        pass


def _enquadrar():
    try:
        FreeCADGui.ActiveDocument.ActiveView.fitAll()
    except Exception:
        pass


# ------------------------------------------------------------------ ganchos
class _Filtro(QtCore.QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QWidget):
                nome = obj.metaObject().className()
                if nome == "SketcherGui::SketchOrientationDialog":
                    QtCore.QTimer.singleShot(0, lambda d=obj: ajustar_dialogo(d))
                elif nome == "PartDesignGui::TaskFeaturePick":
                    for atraso in (0, 300):
                        QtCore.QTimer.singleShot(atraso, mostrar_eixos)
        except Exception:
            pass
        return False


def instalar():
    if _ESTADO["filtro"] is not None:
        return
    f = _Filtro(QtWidgets.QApplication.instance())
    QtWidgets.QApplication.instance().installEventFilter(f)
    _ESTADO["filtro"] = f
