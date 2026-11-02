# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: desenho da seção dos perfis (miniatura da lista, prévia com cotas e vista técnica).

Usa o contorno do catálogo (PrumoPerfis.contorno) e as medidas do catálogo (PrumoPerfis.cotas).
"""
import math

from PySide import QtCore, QtGui, QtWidgets

import PrumoPerfis

AZUL = QtGui.QColor("#003A70")
CONTORNO = QtGui.QColor("#1E2A38")
ACO = QtGui.QColor("#A9C4E0")
ACO_ESC = QtGui.QColor("#7FA3C9")
AMBAR = QtGui.QColor("#E0A100")
VERM = QtGui.QColor("#B5523F")
GRADE = QtGui.QColor("#E6ECF2")


def fmt(v, casas=None):
    if casas is None:
        casas = 0 if abs(v - round(v)) < 1e-6 else (1 if abs(v * 10 - round(v * 10)) < 1e-6 else 2)
    return ("%.*f" % (casas, v)).replace(".", ",")


def _poligonos(it):
    """[(pontos, é_furo)] em mm (u, v) ou ("circulo", D, Di)."""
    ext, furos = PrumoPerfis.contorno(it)
    if isinstance(ext, tuple):
        return ext
    return [(ext, False)] + [(f, True) for f in furos]


def _caixa(it):
    w, h = PrumoPerfis.dimensoes(it)
    return w, h


def _path(it, T):
    """QPainterPath da seção com a transformação T(u, v) -> QPointF."""
    path = QtGui.QPainterPath()
    path.setFillRule(QtCore.Qt.OddEvenFill)
    pol = _poligonos(it)
    if isinstance(pol, tuple):
        _c, D, Di = pol
        c = T(0, 0)
        r = (T(D / 2, 0).x() - c.x())
        path.addEllipse(c, r, r)
        if Di > 0:
            ri = (T(Di / 2, 0).x() - c.x())
            path.addEllipse(c, ri, ri)
        return path
    for pts, _furo in pol:
        q = QtGui.QPolygonF([T(u, v) for u, v in pts])
        path.addPolygon(q)
        path.closeSubpath()
    return path


def _transformacao(it, rect, margem):
    """Escala e centraliza a seção no retângulo (com margens para as cotas)."""
    w, h = _caixa(it)
    l, t, r, b = margem
    aw = max(rect.width() - l - r, 4)
    ah = max(rect.height() - t - b, 4)
    s = min(aw / max(w, 1e-6), ah / max(h, 1e-6))
    cx = rect.left() + l + aw / 2.0
    cy = rect.top() + t + ah / 2.0

    def T(u, v):
        return QtCore.QPointF(cx + u * s, cy - v * s)
    return T, s, w, h


def _seta(p, a, b, cor):
    """Linha de cota de a até b com setas nas pontas."""
    p.setPen(QtGui.QPen(cor, 1.1))
    p.drawLine(a, b)
    ang = math.atan2(b.y() - a.y(), b.x() - a.x())
    for ponta, d in ((b, ang), (a, ang + math.pi)):
        L, W = 6.0, 2.6
        bx, by = ponta.x() - L * math.cos(d), ponta.y() - L * math.sin(d)
        tri = QtGui.QPolygonF([ponta, QtCore.QPointF(bx + W * math.sin(d), by - W * math.cos(d)),
                               QtCore.QPointF(bx - W * math.sin(d), by + W * math.cos(d))])
        p.setBrush(cor)
        p.drawPolygon(tri)
    p.setBrush(QtCore.Qt.NoBrush)


def _texto(p, pos, s, cor=AZUL, rot=0, tam=8.5, negrito=True, fundo=True):
    f = p.font()
    f.setPointSizeF(tam)
    f.setBold(negrito)
    p.setFont(f)
    fm = QtGui.QFontMetricsF(f)
    w, h = fm.horizontalAdvance(s), fm.height()
    p.save()
    p.translate(pos)
    p.rotate(rot)
    r = QtCore.QRectF(-w / 2 - 2, -h / 2, w + 4, h)
    if fundo:
        p.fillRect(r, QtGui.QColor(255, 255, 255, 220))
    p.setPen(cor)
    p.drawText(r, QtCore.Qt.AlignCenter, s)
    p.restore()


def _chamada(p, alvo, texto, dx, dy, cor=AMBAR):
    """Linha de chamada do ponto alvo até o texto."""
    fim = QtCore.QPointF(alvo.x() + dx, alvo.y() + dy)
    p.setPen(QtGui.QPen(cor, 1.1))
    p.drawLine(alvo, fim)
    p.setBrush(cor)
    p.drawEllipse(alvo, 2.2, 2.2)
    p.setBrush(QtCore.Qt.NoBrush)
    _texto(p, QtCore.QPointF(fim.x() + (18 if dx >= 0 else -18), fim.y()), texto, QtGui.QColor("#7A5600"), tam=8)


def desenhar(p, rect, it, cotas=True, detalhe=False):
    """Desenha a seção no retângulo. cotas: largura e altura; detalhe: também espessuras, CG e grade."""
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    margem = (40, 14, 70, 34) if detalhe else ((30, 8, 12, 26) if cotas else (3, 3, 3, 3))
    T, s, w, h = _transformacao(it, rect, margem)
    if detalhe:
        p.setPen(QtGui.QPen(GRADE, 1))
        passo = 10 ** math.floor(math.log10(max(w, h) / 4.0))
        u = -w / 2
        while u <= w / 2 + 1e-6:
            p.drawLine(T(u, -h / 2 - passo), T(u, h / 2 + passo))
            u += passo
        v = -h / 2
        while v <= h / 2 + 1e-6:
            p.drawLine(T(-w / 2 - passo, v), T(w / 2 + passo, v))
            v += passo
    grad = QtGui.QLinearGradient(T(0, h / 2), T(0, -h / 2))
    grad.setColorAt(0, ACO)
    grad.setColorAt(1, ACO_ESC)
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtGui.QPen(CONTORNO, 1.4 if cotas else 1.2))
    p.drawPath(_path(it, T))
    p.setBrush(QtCore.Qt.NoBrush)
    if cotas:
        tubo = isinstance(_poligonos(it), tuple) or it.get("forma") == "redonda"
        # largura (embaixo)
        y = T(0, -h / 2).y() + 14
        a, b = QtCore.QPointF(T(-w / 2, 0).x(), y), QtCore.QPointF(T(w / 2, 0).x(), y)
        p.setPen(QtGui.QPen(QtGui.QColor("#9FB1C4"), 0.8, QtCore.Qt.DashLine))
        p.drawLine(T(-w / 2, -h / 2), a)
        p.drawLine(T(w / 2, -h / 2), b)
        _seta(p, a, b, AZUL)
        rot_w = ("Ø %s" % fmt(w)) if tubo else ("%s = %s" % (_simbolo_largura(it), fmt(w)))
        _texto(p, QtCore.QPointF((a.x() + b.x()) / 2, y), rot_w)
        if not tubo:
            # altura (à esquerda)
            x = T(-w / 2, 0).x() - 14
            a, b = QtCore.QPointF(x, T(0, -h / 2).y()), QtCore.QPointF(x, T(0, h / 2).y())
            p.setPen(QtGui.QPen(QtGui.QColor("#9FB1C4"), 0.8, QtCore.Qt.DashLine))
            p.drawLine(T(-w / 2, -h / 2), a)
            p.drawLine(T(-w / 2, h / 2), b)
            _seta(p, a, b, AZUL)
            _texto(p, QtCore.QPointF(x, (a.y() + b.y()) / 2), "%s = %s" % (_simbolo_altura(it), fmt(h)), rot=-90)
    if detalhe:
        _espessuras(p, it, T, w, h)
        try:
            import PrumoSecao
            pr = PrumoSecao.propriedades(it)
            cg = T(pr.get("cu", 0.0), pr.get("cv", 0.0))
            p.setPen(QtGui.QPen(VERM, 1.3))
            p.drawEllipse(cg, 5, 5)
            p.drawLine(QtCore.QPointF(cg.x() - 8, cg.y()), QtCore.QPointF(cg.x() + 8, cg.y()))
            p.drawLine(QtCore.QPointF(cg.x(), cg.y() - 8), QtCore.QPointF(cg.x(), cg.y() + 8))
            _texto(p, QtCore.QPointF(cg.x() - 18, cg.y() - 10), "CG", VERM, tam=8)
        except Exception:
            pass
    p.restore()


def _simbolo_largura(it):
    t = it.get("tipo")
    if t in ("I", "U") or it.get("forma") in ("T", "Ue"):
        return "bf"
    if t == "L":
        return "b"
    return "b"


def _simbolo_altura(it):
    t = it.get("tipo")
    if t in ("I", "U") or it.get("forma") == "T":
        return "d"
    if it.get("forma") == "Ue":
        return "bw"
    if t == "L":
        return "b"
    if it.get("forma") == "chata":
        return "t"
    return "h"


def _espessuras(p, it, T, w, h):
    """Chamadas das espessuras (alma, mesa, parede) no desenho técnico."""
    t = it.get("tipo")
    if t in ("I", "U") or it.get("forma") == "T":
        tw, tf = it.get("tw"), it.get("tf")
        if tw:
            u = 0.0 if t != "U" else -w / 2 + tw / 2
            _chamada(p, T(u + tw / 2, 0), "tw = %s" % fmt(tw), 34, -18)
        if tf:
            _chamada(p, T(w / 2 - w * 0.12, h / 2 - tf / 2), "tf = %s" % fmt(tf), 30, -22)
        if it.get("R"):
            _chamada(p, T((tw or 0) / 2 + 1, h / 2 - (tf or 0) - 1), "R = %s" % fmt(it["R"]), 40, 26)
    elif it.get("esp"):
        e = it["esp"]
        if t == "TUBO":
            alvo = T(it["D"] / 2 - e / 2, 0)
        elif t == "L":
            alvo = T(0, -h / 2 + e / 2)
        elif it.get("forma") == "chata":
            return
        else:
            alvo = T(w / 2 - e / 2, 0)
        _chamada(p, alvo, "t = %s" % fmt(e), 30, -24)


def miniatura(it, tam=40):
    """Ícone da seção (para a lista)."""
    pm = QtGui.QPixmap(tam, tam)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setPen(QtGui.QPen(QtGui.QColor("#D5DEE8"), 1))
    p.setBrush(QtGui.QColor("#FFFFFF"))
    p.drawRoundedRect(QtCore.QRectF(0.5, 0.5, tam - 1, tam - 1), 6, 6)
    try:
        desenhar(p, QtCore.QRectF(4, 4, tam - 8, tam - 8), it, cotas=False)
    except Exception:
        pass
    p.end()
    return pm


class DesenhoPerfil(QtWidgets.QWidget):
    """Prévia da seção com as cotas principais (ou o desenho técnico completo)."""

    def __init__(self, detalhe=False, parent=None):
        super().__init__(parent)
        self.it = None
        self.detalhe = detalhe
        self.setMinimumSize(*((420, 340) if detalhe else (200, 150)))

    def mostrar(self, it):
        self.it = it
        self.update()

    def paintEvent(self, _ev):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor("#FFFFFF"))
        p.setPen(QtGui.QPen(QtGui.QColor("#DCE4EC"), 1))
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        if self.it is not None:
            try:
                desenhar(p, QtCore.QRectF(self.rect()).adjusted(6, 6, -6, -6), self.it, cotas=True,
                         detalhe=self.detalhe)
            except Exception as exc:
                p.setPen(VERM)
                p.drawText(self.rect(), QtCore.Qt.AlignCenter, "Sem desenho: %s" % exc)
        p.end()


def tabela_html(it, completa=False):
    """Dados do perfil em tabela (medidas do catálogo, massa, área, fonte; propriedades se completa)."""
    linhas = []
    for rot, v in PrumoPerfis.cotas(it):
        linhas.append((rot, "%s mm" % fmt(v)))
    linhas.append(("Massa linear", "%s kg/m" % fmt(it.get("massa", 0.0), 2)))
    if it.get("area_cm2"):
        linhas.append(("Área da seção", "%s cm²" % fmt(it["area_cm2"], 2)))
    fonte = PrumoPerfis.fonte(it).get("nome", "") if it.get("origem") != "customizado" else "Medidas digitadas"
    html = ["<table cellspacing='0' cellpadding='2' style='font-size:9pt' width='100%'>"]
    for rot, v in linhas:
        html.append("<tr><td style='color:#5B6876;padding-right:14px'>%s</td><td><b>%s</b></td></tr>" % (rot, v))
    if completa:
        try:
            import PrumoSecao
            pr = PrumoSecao.propriedades(it)
            props = [("Ix", pr.get("Ix", 0) / 1e4, "cm⁴"), ("Iy", pr.get("Iy", 0) / 1e4, "cm⁴"),
                     ("Wx", pr.get("Wx", 0) / 1e3, "cm³"), ("Wy", pr.get("Wy", 0) / 1e3, "cm³"),
                     ("Zx", pr.get("Zx", 0) / 1e3, "cm³"), ("Zy", pr.get("Zy", 0) / 1e3, "cm³"),
                     ("rx", pr.get("rx", 0) / 10, "cm"), ("ry", pr.get("ry", 0) / 10, "cm"),
                     ("J", pr.get("J", 0) / 1e4, "cm⁴")]
            html.append("<tr><td colspan='2' style='padding-top:8px;color:#003A70'><b>PROPRIEDADES DA SEÇÃO</b> <span style='color:#5B6876'>(calculadas pelo Prumo)</span><b>"
                        "</b></td></tr>")
            for n, v, u in props:
                if v:
                    html.append("<tr><td style='color:#5B6876'>%s</td><td><b>%s %s</b></td></tr>" % (n, fmt(v, 2), u))
            if pr.get("aproximada"):
                html.append("<tr><td colspan='2' style='color:#7A5600'>Calculadas sem os raios do catálogo "
                            "(um pouco menores que as tabeladas).</td></tr>")
        except Exception:
            pass
    if completa:
        html.append("<tr><td style='color:#5B6876;padding-top:6px'>Fonte</td><td style='padding-top:6px'>%s</td></tr>"
                    % fonte)
    html.append("</table>")
    return "".join(html)


class DialogoTecnico(QtWidgets.QDialog):
    """Vista técnica do perfil: desenho grande com cotas, espessuras e CG, e a tabela de dados."""

    def __init__(self, it, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalhes técnicos — %s" % it["nome"])
        lay = QtWidgets.QVBoxLayout(self)
        tit = QtWidgets.QLabel("<span style='font-size:13pt;font-weight:700;color:#003A70'>%s</span>"
                               % it["nome"])
        lay.addWidget(tit)
        corpo = QtWidgets.QHBoxLayout()
        self.desenho = DesenhoPerfil(detalhe=True)
        self.desenho.mostrar(it)
        corpo.addWidget(self.desenho, 3)
        dados = QtWidgets.QLabel(tabela_html(it, completa=True))
        dados.setTextFormat(QtCore.Qt.RichText)
        dados.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        dados.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        dados.setWordWrap(True)
        caixa = QtWidgets.QScrollArea()
        caixa.setWidgetResizable(True)
        caixa.setWidget(dados)
        caixa.setMinimumWidth(320)
        caixa.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        corpo.addWidget(caixa, 2)
        lay.addLayout(corpo, 1)
        st = QtWidgets.QLabel(PrumoPerfis.descricao_status(it))
        st.setWordWrap(True)
        st.setStyleSheet("color:%s" % ("#2E8B6A" if PrumoPerfis.confiavel(it) else "#B5523F"))
        lay.addWidget(st)
        bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        bb.button(QtWidgets.QDialogButtonBox.Close).setText("Fechar")
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(900, 540)
