# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - propriedades de massa (massa, centro de gravidade e momentos de inércia).
"""Propriedades de massa num clique.

Usa o material de cada peça (propriedade "Material da forma"); peça sem material entra como aço
(7.850 kg/m³, valor ajustável no próprio painel). Calcula volume, área, massa, centro de
gravidade e o tensor de inércia no centro de gravidade, com os momentos e eixos principais.
"""

import math

import FreeCAD
import FreeCADGui

import PrumoUtil
from PrumoUtil import fmt

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets


class Resultado:
    def __init__(self):
        self.volume = 0.0       # mm³
        self.area = 0.0         # mm²
        self.massa = 0.0        # kg
        self.cg = FreeCAD.Vector()   # mm
        self.inercia = [[0.0] * 3 for _ in range(3)]  # kg·mm², no CG, eixos globais
        self.principais = (0.0, 0.0, 0.0)              # kg·mm²
        self.eixos = (FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0), FreeCAD.Vector(0, 0, 1))
        self.itens = []         # (rótulo, material, densidade, volume mm³, massa kg, definido)
        self.sem_material = []  # rótulos das peças sem material (entraram como densidade padrão)


def _tensor(matriz):
    return [[matriz.A[r * 4 + c] for c in range(3)] for r in range(3)]


def _autovalores(t):
    """Autovalores/autovetores de uma matriz simétrica 3x3 (Jacobi), sem depender do numpy."""
    a = [row[:] for row in t]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(60):
        p, q, maior = 0, 1, 0.0
        for i in range(3):
            for j in range(i + 1, 3):
                if abs(a[i][j]) > maior:
                    p, q, maior = i, j, abs(a[i][j])
        escala = max(abs(a[0][0]) + abs(a[1][1]) + abs(a[2][2]), 1e-300)
        if maior < 1e-14 * escala:
            break
        theta = 0.5 * math.atan2(2 * a[p][q], a[q][q] - a[p][p])
        c, s = math.cos(theta), math.sin(theta)
        for k in range(3):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp - s * akq
            a[k][q] = s * akp + c * akq
        for k in range(3):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk - s * aqk
            a[q][k] = s * apk + c * aqk
        for k in range(3):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    pares = sorted(((a[i][i], FreeCAD.Vector(v[0][i], v[1][i], v[2][i])) for i in range(3)),
                   key=lambda x: x[0])
    return tuple(p[0] for p in pares), tuple(p[1] for p in pares)


def calcular(objs, densidade_padrao=None):
    """Propriedades de massa do conjunto de objetos (peças, corpos, partes, montagens)."""
    if densidade_padrao is None:
        densidade_padrao = PrumoUtil.densidade_padrao()
    r = Resultado()
    partes = []  # (massa kg, cg, tensor no cg da própria peça kg·mm²)
    for obj, sh in PrumoUtil.pecas(objs):
        nome, dens, definido = PrumoUtil.material(obj)
        if not definido:
            dens = densidade_padrao
            r.sem_material.append(obj.Label)
        rho = dens * 1e-9  # kg/mm³
        vol = 0.0
        for sol in sh.Solids:
            v = sol.Volume
            if v <= 0:
                continue
            m = v * rho
            vol += v
            r.area += sol.Area
            partes.append((m, sol.CenterOfMass, [[x * rho for x in row] for row in _tensor(sol.MatrixOfInertia)]))
        r.volume += vol
        r.itens.append((obj.Label, nome, dens, vol, vol * rho, definido))
    r.massa = sum(p[0] for p in partes)
    if r.massa <= 0:
        return r
    cg = FreeCAD.Vector()
    for m, c, _t in partes:
        cg += c * m
    r.cg = cg * (1.0 / r.massa)
    tot = [[0.0] * 3 for _ in range(3)]
    for m, c, t in partes:
        d = c - r.cg
        dd = (d.x, d.y, d.z)
        d2 = d.x * d.x + d.y * d.y + d.z * d.z
        for i in range(3):
            for j in range(3):
                tot[i][j] += t[i][j] + m * ((d2 if i == j else 0.0) - dd[i] * dd[j])
    r.inercia = tot
    r.principais, r.eixos = _autovalores(tot)
    return r


def texto(r):
    """Relatório em texto (para copiar)."""
    linhas = ["Propriedades de massa — Prumo 3D", ""]
    linhas.append("Massa: %s" % fmt(r.massa, 3, "kg"))
    linhas.append("Volume: %s (%s)" % (fmt(r.volume / 1000.0, 2, "cm³"), fmt(r.volume, 0, "mm³")))
    linhas.append("Área de superfície: %s" % fmt(r.area, 1, "mm²"))
    linhas.append("Centro de gravidade: X = %s   Y = %s   Z = %s" % (
        fmt(r.cg.x, 2, "mm"), fmt(r.cg.y, 2, "mm"), fmt(r.cg.z, 2, "mm")))
    linhas.append("")
    linhas.append("Momentos principais de inércia no CG:")
    for i, (val, eixo) in enumerate(zip(r.principais, r.eixos), 1):
        linhas.append("  I%d = %s   eixo (%s; %s; %s)" % (i, fmt(val, 1, "kg·mm²"), fmt(eixo.x, 3),
                                                       fmt(eixo.y, 3), fmt(eixo.z, 3)))
    linhas.append("")
    linhas.append("Tensor de inércia no CG, eixos globais (kg·mm²):")
    for nome, row in zip(("x", "y", "z"), r.inercia):
        linhas.append("  %s: %s" % (nome, "   ".join(fmt(v, 1) for v in row)))
    linhas.append("")
    linhas.append("Peças:")
    for rot, mat, dens, vol, massa, definido in r.itens:
        linhas.append("  %s — %s, %s — %s" % (rot, mat, fmt(dens, 0, "kg/m³"), fmt(massa, 3, "kg")))
    if r.sem_material:
        linhas.append("")
        linhas.append("Sem material definido (calculado com a densidade padrão): " + ", ".join(r.sem_material))
    return "\n".join(linhas)


# ============================================================================ painel
class DialogoMassa(QtWidgets.QDialog):
    def showEvent(self, ev):
        import PrumoPainel
        PrumoPainel.caber_na_tela(self)      # notebook: rolagem em vez de diálogo cortado
        super().showEvent(ev)

    def __init__(self, objs, parent=None):
        super().__init__(parent)
        self.objs = objs
        self.setWindowTitle("Propriedades de massa")
        self.setMinimumWidth(560)
        import PrumoPainel as P
        self.setStyleSheet(P.qss())
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(10)
        card_d, topo = P.bloco("Material", "material", QtWidgets.QHBoxLayout)
        topo.addWidget(QtWidgets.QLabel("Densidade para peças sem material:"))
        self.dens = QtWidgets.QDoubleSpinBox()
        self.dens.setRange(1, 30000)
        self.dens.setDecimals(0)
        self.dens.setSuffix(" kg/m³")
        self.dens.setValue(PrumoUtil.densidade_padrao())
        self.dens.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
        self.dens.valueChanged.connect(self.atualizar)
        topo.addWidget(self.dens)
        topo.addStretch(1)
        lay.addWidget(card_d)
        card_r, cr = P.bloco("Resultado", "info")
        self.saida = QtWidgets.QTextBrowser()
        self.saida.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.saida.setStyleSheet("QTextBrowser { border: 0; background: transparent; }")
        self.saida.setMinimumHeight(340)
        cr.addWidget(self.saida, 1)
        lay.addWidget(card_r, 1)
        bot = QtWidgets.QHBoxLayout()
        self.b_ponto = QtWidgets.QPushButton("Marcar o CG no modelo")
        self.b_ponto.clicked.connect(self.marcar_cg)
        b_copiar = QtWidgets.QPushButton("Copiar")
        b_copiar.clicked.connect(self.copiar)
        b_fechar = QtWidgets.QPushButton("Fechar")
        b_fechar.clicked.connect(self.accept)
        bot.addWidget(self.b_ponto)
        bot.addStretch(1)
        bot.addWidget(b_copiar)
        bot.addWidget(b_fechar)
        lay.addLayout(bot)
        self.resultado = None
        self.atualizar()

    def atualizar(self):
        self.resultado = calcular(self.objs, self.dens.value())
        r = self.resultado
        html = ["<h3 style='color:#003A70;margin:0'>%s</h3>" % fmt(r.massa, 3, "kg")]
        html.append("<table cellspacing='0' cellpadding='3'>")
        def lin(a, b):
            html.append("<tr><td style='color:#5B6876'>%s</td><td><b>%s</b></td></tr>" % (a, b))
        lin("Volume", "%s &nbsp; (%s)" % (fmt(r.volume / 1000.0, 2, "cm³"), fmt(r.volume, 0, "mm³")))
        lin("Área de superfície", fmt(r.area, 1, "mm²"))
        lin("Centro de gravidade", "X %s &nbsp; Y %s &nbsp; Z %s" % (fmt(r.cg.x, 2), fmt(r.cg.y, 2),
                                                                   fmt(r.cg.z, 2, "mm")))
        for i, (val, eixo) in enumerate(zip(r.principais, r.eixos), 1):
            lin("Momento principal I%d" % i, "%s &nbsp; <span style='color:#5B6876'>eixo (%s; %s; %s)</span>"
                % (fmt(val, 1, "kg·mm²"), fmt(eixo.x, 3), fmt(eixo.y, 3), fmt(eixo.z, 3)))
        html.append("</table>")
        html.append("<p style='color:#5B6876;margin-bottom:2px'>Tensor de inércia no CG, eixos globais (kg·mm²)</p>")
        html.append("<table cellspacing='0' cellpadding='3'>")
        for nome, row in zip(("x", "y", "z"), r.inercia):
            html.append("<tr><td style='color:#5B6876'>%s</td>%s</tr>" % (
                nome, "".join("<td align='right'>%s</td>" % fmt(v, 1) for v in row)))
        html.append("</table>")
        html.append("<p style='color:#5B6876;margin-bottom:2px'>Peças</p><table cellspacing='0' cellpadding='3'>")
        for rot, mat, dens, vol, massa, definido in r.itens:
            cor = "#1B2A3A" if definido else "#B5523F"
            html.append("<tr><td>%s</td><td style='color:%s'>%s</td><td align='right'>%s</td>"
                        "<td align='right'><b>%s</b></td></tr>" % (
                            rot, cor, mat, fmt(dens if definido else self.dens.value(), 0, "kg/m³"),
                            fmt(massa if definido else vol * self.dens.value() * 1e-9, 3, "kg")))
        html.append("</table>")
        if r.sem_material:
            html.append("<p style='color:#B5523F'>Peças sem material definido entram com a densidade "
                        "acima. Para usar o material certo, escolha-o na propriedade "
                        "<i>Material da forma</i> da peça.</p>")
        self.saida.setHtml("".join(html))
        self.b_ponto.setEnabled(r.massa > 0)

    def copiar(self):
        QtWidgets.QApplication.clipboard().setText(texto(self.resultado))

    def marcar_cg(self):
        marcar_cg(self.resultado)


def marcar_cg(r, doc=None):
    """Cria (ou move) um ponto 'CentroDeGravidade' no CG calculado."""
    import Part
    doc = doc or FreeCAD.ActiveDocument
    if doc is None or r is None or r.massa <= 0:
        return None
    doc.openTransaction("Marcar centro de gravidade")
    ponto = doc.getObject("CentroDeGravidade")
    if ponto is None:
        ponto = doc.addObject("Part::Vertex", "CentroDeGravidade")
        ponto.Label = "Centro de gravidade"
    ponto.X, ponto.Y, ponto.Z = r.cg.x, r.cg.y, r.cg.z
    doc.recompute()
    doc.commitTransaction()
    try:
        vo = ponto.ViewObject
        vo.PointSize = 10
        vo.PointColor = (0.969, 0.745, 0.0)
    except Exception:
        pass
    return ponto


def _selecao_ou_documento():
    sel = FreeCADGui.Selection.getSelection()
    if sel:
        return sel
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return []
    # documento inteiro: objetos de topo (sem pai) que tenham forma
    return [o for o in doc.RootObjects if o.TypeId != "App::Origin"]


class CmdMassa:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("massa.svg"),
                "MenuText": "Propriedades de massa",
                "ToolTip": "Massa, centro de gravidade e momentos de inércia da seleção (ou do "
                           "documento inteiro), com o material de cada peça."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        objs = _selecao_ou_documento()
        if not PrumoUtil.pecas(objs):
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Propriedades de massa",
                                              "Nenhuma peça sólida na seleção.")
            return
        DialogoMassa(objs, FreeCADGui.getMainWindow()).exec()
