# SPDX-License-Identifier: LGPL-2.1-or-later
"""Painel de comando no padrão Prumo para Extrusão e Cavidade (quadro "Comando ativo" da proposta).

Enquanto uma Extrusão (Pad) ou Cavidade (Pocket) está aberta para edição, o topo da aba do comando
mostra cartões: Lados, Direção 1 (até onde vai, medida, afastamento, ângulo de saída, inverter),
Direção 2 (só com dois lados), Perfil e Acabamento. O formulário do FreeCAD fica escondido.

Os cartões mexem nos campos do próprio formulário do FreeCAD (por nome), não nas propriedades: é o
formulário que grava ao clicar OK, então ele precisa ter os valores certos. Quando o modo pede uma
escolha na vista (até a face, até a peça), o formulário do FreeCAD reaparece logo abaixo para a
escolha; "Formulário completo" mostra tudo a qualquer momento.
"""

import os
import re
import FreeCAD
import FreeCADGui
from PySide import QtCore, QtWidgets

try:
    import shiboken6 as shiboken
except ImportError:  # pragma: no cover
    import shiboken2 as shiboken

import PrumoUI as UI

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"

TIPOS = ("PartDesign::Pad", "PartDesign::Pocket", "PartDesign::Hole", "PartDesign::Revolution",
         "PartDesign::Groove", "PartDesign::Fillet", "PartDesign::Chamfer", "PartDesign::LinearPattern",
         "PartDesign::PolarPattern", "PartDesign::Mirrored", "PartDesign::Draft", "PartDesign::Thickness",
         "PartDesign::AdditiveHelix", "PartDesign::SubtractiveHelix", "PartDesign::AdditiveLoft",
         "PartDesign::SubtractiveLoft", "PartDesign::AdditivePipe", "PartDesign::SubtractivePipe",
         "PartDesign::Boolean", "PartDesign::MultiTransform") + tuple("PartDesign::%s%s" % (a, b) for b in ("Box", "Cylinder", "Sphere", "Cone",
                                       "Ellipsoid", "Torus", "Prism", "Wedge") for a in ("Additive", "Subtractive"))
# campo que identifica o formulário do FreeCAD de cada comando
MARCA = {"PartDesign::Pad": "changeMode", "PartDesign::Pocket": "changeMode", "PartDesign::Hole": "ThreadType",
         "PartDesign::Revolution": "revolveAngle", "PartDesign::Groove": "revolveAngle",
         "PartDesign::Fillet": "filletRadius", "PartDesign::Chamfer": "chamferType",
         "PartDesign::LinearPattern": "listWidgetFeatures", "PartDesign::PolarPattern": "listWidgetFeatures",
         "PartDesign::Mirrored": "listWidgetFeatures", "PartDesign::Draft": "draftAngle",
         "PartDesign::Thickness": "joinComboBox", "PartDesign::AdditiveHelix": "inputMode",
         "PartDesign::SubtractiveHelix": "inputMode", "PartDesign::AdditiveLoft": "checkBoxRuled",
         "PartDesign::SubtractiveLoft": "checkBoxRuled", "PartDesign::AdditivePipe": "comboBoxTransition",
         "PartDesign::SubtractivePipe": "comboBoxTransition", "PartDesign::Boolean": "comboType",
         "PartDesign::MultiTransform": "listTransformFeatures"}
MARCA.update({t: "PartDesignGui__DlgPrimitives" for t in TIPOS if t.startswith(("PartDesign::Additive", "PartDesign::Subtractive"))
              and t.endswith(("Box", "Cylinder", "Sphere", "Cone", "Ellipsoid", "Torus", "Prism", "Wedge"))})
LADOS = [("one", "Um lado", "seta_cima"), ("two", "Dois lados", "dois_lados"), ("sym", "Simétrica", "simetrica")]
MODOS = {
    "PartDesign::Pad": [("Length", "Medida", "medida"), ("UpToLast", "Até o fim", "ate_fim"),
                        ("UpToFirst", "Até a 1ª", "ate_primeira"), ("UpToFace", "Até a face", "ate_face"),
                        ("UpToShape", "Até a peça", "solido")],
    "PartDesign::Pocket": [("Length", "Medida", "medida"), ("ThroughAll", "Através", "atraves"),
                           ("UpToFirst", "Até a 1ª", "ate_primeira"), ("UpToFace", "Até a face", "ate_face"),
                           ("UpToShape", "Até a peça", "solido")],
}
PEDEM_ESCOLHA = ("UpToFace", "UpToShape")     # o usuário escolhe a face/peça na vista


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def ligado():
    return _params().GetBool("PainelDeComando", True)


def em_edicao():
    try:
        gdoc = FreeCADGui.ActiveDocument
        vp = gdoc.getInEdit() if gdoc else None
        obj = vp.Object if vp is not None else None
    except Exception:
        return None
    return obj if obj is not None and obj.TypeId in TIPOS else None


def _painel_de_tarefas():
    mw = FreeCADGui.getMainWindow()
    for w in mw.findChildren(QtWidgets.QWidget):
        if w.metaObject().className() == "Gui::TaskView::TaskPanel" and w.isVisible():
            return w
    return None


def _quadro_do_formulario(panel, marca="changeMode"):
    """O quadro (TaskBox) do FreeCAD que tem o formulário do comando (procura o combo pelo nome)."""
    lay = panel.layout()
    for _i, w in UI.widgets_do_layout(lay):
        if w is None or not shiboken.isValid(w):
            continue
        if w.findChild(QtWidgets.QWidget, marca) is not None:
            return w
    return None


class Formulario:
    """Acesso aos campos do formulário do FreeCAD pelo nome."""

    def __init__(self, quadro):
        self.q = quadro

    def w(self, nome, cls=QtWidgets.QWidget):
        return self.q.findChild(cls, nome)

    def combo(self, nome):
        return self.w(nome, QtWidgets.QComboBox)

    def check(self, nome):
        return self.w(nome, QtWidgets.QCheckBox)

    def numero(self, nome):
        w = self.w(nome, QtWidgets.QAbstractSpinBox)
        if w is None:
            return None
        v = w.property("rawValue")
        return float(v) if v is not None else None

    def espelho(self, nome, traduz=None, largura=190):
        """Lista nossa que reflete (e comanda) uma lista do formulário do FreeCAD."""
        fc = self.combo(nome)
        cb = QtWidgets.QComboBox()
        cb.setObjectName("PrumoLista")
        cb.setMaximumWidth(largura)
        # não exige a largura do maior item (o texto inteiro aparece ao abrir a lista)
        cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(8)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        if fc is None:
            return cb
        for i in range(fc.count()):
            t = fc.itemText(i)
            cb.addItem((traduz or {}).get(t, t))
        cb.setCurrentIndex(fc.currentIndex())
        cb.activated.connect(lambda i: fc.setCurrentIndex(i))
        return cb

    def indice(self, nome):
        c = self.combo(nome)
        return c.currentIndex() if c is not None else -1

    def texto(self, nome):
        c = self.combo(nome)
        return c.currentText() if c is not None else ""

    def visivel(self, nome):
        w = self.w(nome)
        return w is not None and w.isVisibleTo(self.q) and w.isEnabled()

    def por_numero(self, nome, valor):
        w = self.w(nome, QtWidgets.QAbstractSpinBox)
        if w is None:
            return False
        w.setProperty("rawValue", float(valor))
        return True


class PainelComando(QtWidgets.QWidget):
    def __init__(self, obj, quadro, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema("#PrumoUI { background: transparent; }"))
        self.obj = obj
        self.f = Formulario(quadro)
        self.quadro = quadro
        self.modos = MODOS.get(obj.TypeId, [])
        self.nome_medida = "Altura" if obj.TypeId == "PartDesign::Pad" else "Profundidade"
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)
        self.completo = QtWidgets.QToolButton()
        self.completo.setObjectName("PrumoAvancado")
        self.completo.setCheckable(True)
        self.completo.setText("Formulário completo do FreeCAD")
        self.completo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.completo.toggled.connect(lambda _on: self.mostrar_formulario())
        self.assinatura = None
        self.montar()

    # ---------------------------------------------------------------- leitura do formulário
    def estado(self):
        f = self.f
        lados = f.combo("sidesMode")
        m1, m2 = f.combo("changeMode"), f.combo("changeMode2")
        return {
            "lados": LADOS[lados.currentIndex()][0] if lados is not None and 0 <= lados.currentIndex() < 3 else "one",
            "modo1": self.modos[m1.currentIndex()][0] if m1 is not None and 0 <= m1.currentIndex() < len(self.modos)
            else "Length",
            "modo2": self.modos[m2.currentIndex()][0] if m2 is not None and 0 <= m2.currentIndex() < len(self.modos)
            else "Length",
            "comp1": f.numero("lengthEdit"), "comp2": f.numero("lengthEdit2"),
            "afast1": f.numero("offsetEdit"), "afast2": f.numero("offsetEdit2"),
            "saida1": f.numero("taperEdit"), "saida2": f.numero("taperEdit2"),
            "inverter": bool(f.check("checkBoxReversed").isChecked()) if f.check("checkBoxReversed") else False,
            "normal": bool(f.check("checkBoxAlongDirection").isChecked())
            if f.check("checkBoxAlongDirection") else True,
        }

    # ---------------------------------------------------------------- montagem
    def _limpar(self):
        while self.lay.count():
            it = self.lay.takeAt(0)
            w = it.widget()
            if w is not None and w is not self.completo:
                w.setParent(None)
                w.deleteLater()

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}

        c = UI.Cartao("Lados", "dois_lados")
        seg = UI.Segmentado([(k, t, i) for k, t, i in LADOS], e["lados"], colunas=3)
        seg.mudou.connect(self._lados)
        c.widget(seg)
        self.campos["lados"] = seg
        self.lay.addWidget(c)

        self._direcao(1, e)
        if e["lados"] == "two":
            self._direcao(2, e)

        c = UI.Cartao("Perfil", "perfil")
        try:
            prof = self.obj.Profile[0].Label if self.obj.Profile and self.obj.Profile[0] else "—"
        except Exception:
            prof = "—"
        c.widget(UI.Chip(prof))
        if self.f.check("checkBoxAlongDirection") is not None and self.f.check("checkBoxAlongDirection").isVisible():
            sw = UI.Interruptor(e["normal"])
            sw.toggled.connect(lambda on: self._marcar("checkBoxAlongDirection", on))
            c.linha("Na normal do esboço", sw)
            self.campos["normal"] = sw
        self.lay.addWidget(c)

        c = UI.Cartao("Acabamento", "acabamento")
        sw = UI.Interruptor(bool(getattr(self.obj, "Refine", False)))
        sw.toggled.connect(self._refinar)
        c.linha("Unir faces planas (refinar)", sw)
        self.campos["refinar"] = sw
        self.lay.addWidget(c)

        self.dica = UI.Dica("")
        self.lay.addWidget(self.dica)
        self.lay.addWidget(self.completo)
        self.mostrar_formulario()

    def _direcao(self, n, e):
        suf = "" if n == 1 else "2"
        c = UI.Cartao("Direção %d" % n, "seta_cima" if n == 1 else "seta_baixo")
        modo = e["modo%d" % n]
        seg = UI.Segmentado([(k, t, i) for k, t, i in self.modos], modo, colunas=3)
        seg.mudou.connect(lambda k, n=n: self._modo(n, k))
        sub = QtWidgets.QLabel("Até onde vai")
        sub.setObjectName("PrumoSub")
        c.widget(sub)
        c.widget(seg)
        self.campos["modo%d" % n] = seg
        if modo == "Length" and e["comp%d" % n] is not None:
            num = UI.CampoNumero(e["comp%d" % n], "mm", minimo=0.0)
            num.valueChanged.connect(lambda v, s=suf: self.f.por_numero("lengthEdit" + s, v))
            c.linha(self.nome_medida, num)
            self.campos["comp%d" % n] = num
        if modo in ("UpToFace", "UpToFirst", "UpToLast", "UpToShape") and e["afast%d" % n] is not None:
            num = UI.CampoNumero(e["afast%d" % n], "mm")
            num.valueChanged.connect(lambda v, s=suf: self.f.por_numero("offsetEdit" + s, v))
            c.linha("Afastamento", num)
            self.campos["afast%d" % n] = num
        if e["saida%d" % n] is not None:
            num = UI.CampoNumero(e["saida%d" % n], "°")
            num.valueChanged.connect(lambda v, s=suf: self.f.por_numero("taperEdit" + s, v))
            c.linha("Ângulo de saída", num)
            self.campos["saida%d" % n] = num
        if n == 1 and self.f.check("checkBoxReversed") is not None:
            sw = UI.Interruptor(e["inverter"])
            sw.setEnabled(self.f.check("checkBoxReversed").isEnabled())
            sw.toggled.connect(lambda on: self._marcar("checkBoxReversed", on))
            c.linha("Inverter", sw)
            self.campos["inverter"] = sw
        self.lay.addWidget(c)

    # ---------------------------------------------------------------- ações (no formulário do FreeCAD)
    def _lados(self, k):
        cb = self.f.combo("sidesMode")
        if cb is not None:
            cb.setCurrentIndex([x[0] for x in LADOS].index(k))
        QtCore.QTimer.singleShot(0, self.montar)

    def _modo(self, n, k):
        cb = self.f.combo("changeMode" if n == 1 else "changeMode2")
        if cb is not None:
            cb.setCurrentIndex([x[0] for x in self.modos].index(k))
        QtCore.QTimer.singleShot(0, self.montar)

    def _marcar(self, nome, on):
        cb = self.f.check(nome)
        if cb is not None and cb.isChecked() != bool(on):
            cb.setChecked(bool(on))

    def _refinar(self, on):
        try:
            self.obj.Refine = bool(on)
            self.obj.Document.recompute()
        except Exception:
            pass

    # ---------------------------------------------------------------- formulário do FreeCAD
    def precisa_do_formulario(self):
        e = self.estado()
        return e["modo1"] in PEDEM_ESCOLHA or (e["lados"] == "two" and e["modo2"] in PEDEM_ESCOLHA)

    def mostrar_formulario(self):
        escolha = self.precisa_do_formulario()
        mostrar = self.completo.isChecked() or escolha
        if self.quadro is not None and shiboken.isValid(self.quadro):
            self.quadro.setVisible(mostrar)
        if escolha and not self.completo.isChecked():
            self.dica.mostrar(self.dica_extra() or "Escolha a face (ou a peça) na vista: o quadro do FreeCAD abaixo "
                                                   "mostra o que foi escolhido.")
        else:
            self.dica.mostrar(self.dica_extra())

    def dica_extra(self):
        return ""

    def atualizar(self):
        """Mudou algo no formulário do FreeCAD (ou pelo desfazer): remonta, se não estiver digitando."""
        try:
            e = self.estado()
        except Exception:
            return
        assin = tuple(sorted(e.items()))
        if assin == self.assinatura:
            return
        f = QtWidgets.QApplication.focusWidget()
        if f is not None and self.isAncestorOf(f):
            self.assinatura = assin
            return
        self.montar()


ROSCAS_PT = {"None": "Sem rosca (diâmetro livre)", "ISO metric regular": "Métrica ISO grossa",
             "ISO metric fine": "Métrica ISO fina", "UTS coarse": "UNC (polegada, grossa)",
             "UTS fine": "UNF (polegada, fina)", "UTS extra fine": "UNEF (polegada, extrafina)",
             "ANSI pipes": "NPT (tubo, ANSI)", "ISO/BSP pipes": "BSP (tubo, ISO)",
             "BSW whitworth": "Whitworth BSW", "BSF whitworth fine": "Whitworth BSF fina",
             "ISO tyre valves": "Válvula de pneu (ISO)"}
CABECAS_PT = {"None": "Nenhuma (furo reto)", "Counterbore": "Rebaixo", "Countersink": "Escareado",
              "Counterdrill": "Rebaixo cônico", "Cheesehead (deprecated)": "Cabeça cilíndrica (antigo)",
              "Countersink socket screw (deprecated)": "Escareado p/ allen (antigo)",
              "Cap screw (deprecated)": "Cabeça cilíndrica allen (antigo)"}
TIPOS_FURO = [("Clearance / Passthrough", "Passante", "atraves"), ("Tap drill (to be threaded)", "Para rosca", "furo"),
              ("Modeled thread", "Modelada", "padrao")]
FOLGAS_PT = {"Standard": "Normal", "Close": "Justa", "Wide": "Larga"}


class PainelFuro(PainelComando):
    """Furo: rosca e tamanho, tipo (passante, para rosca, modelada), profundidade, cabeça e ponta."""

    def __init__(self, obj, quadro, parent=None):
        self.modos = []
        QtWidgets.QWidget.__init__(self, parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema("#PrumoUI { background: transparent; }"))
        self.obj = obj
        self.f = Formulario(quadro)
        self.quadro = quadro
        self.nome_medida = "Profundidade"
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)
        self.completo = QtWidgets.QToolButton()
        self.completo.setObjectName("PrumoAvancado")
        self.completo.setCheckable(True)
        self.completo.setText("Formulário completo do FreeCAD")
        self.completo.setToolTip("Rosca, folgas, profundidade da rosca e o resto do formulário original")
        self.completo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.completo.toggled.connect(lambda _on: self.mostrar_formulario())
        self.assinatura = None
        self.montar()

    def estado(self):
        f = self.f
        chk = f.check("DrillPointAngled")
        rev = f.check("Reversed")
        return {
            "rosca": f.indice("ThreadType"), "tamanho": f.indice("ThreadSize"), "tipo": f.indice("HoleType"),
            "folga": f.indice("ThreadFit"), "prof_tipo": f.indice("DepthType"), "cabeca": f.indice("HoleCutType"),
            "cabeca_txt": f.texto("HoleCutType"), "n_cabeca": f.combo("HoleCutType").count()
            if f.combo("HoleCutType") else 0, "n_tam": f.combo("ThreadSize").count() if f.combo("ThreadSize") else 0,
            "diam": f.numero("Diameter"), "prof": f.numero("Depth"),
            "cab_d": f.numero("HoleCutDiameter"), "cab_p": f.numero("HoleCutDepth"),
            "ponta": bool(chk.isChecked()) if chk else True, "angulo": f.numero("DrillPointAngle"),
            "inverter": bool(rev.isChecked()) if rev else False,
            "diam_ok": f.visivel("Diameter"), "cab_ok": f.visivel("HoleCutDiameter"),
        }

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        sem_rosca = e["rosca"] <= 0

        c = UI.Cartao("Furo", "furo")
        cb = f.espelho("ThreadType", ROSCAS_PT)
        cb.activated.connect(lambda _i: QtCore.QTimer.singleShot(0, self.montar))
        c.linha("Padrão", cb)
        self.campos["rosca"] = cb
        if not sem_rosca:
            cb = f.espelho("ThreadSize", largura=150)
            cb.activated.connect(lambda _i: QtCore.QTimer.singleShot(0, self.montar))
            c.linha("Tamanho", cb)
            self.campos["tamanho"] = cb
        if e["diam"] is not None:
            num = UI.CampoNumero(e["diam"], "mm", minimo=0.0)
            num.setEnabled(e["diam_ok"])
            num.valueChanged.connect(lambda v: f.por_numero("Diameter", v))
            c.linha("Diâmetro", num)
            self.campos["diam"] = num
        self.lay.addWidget(c)

        if not sem_rosca and f.combo("HoleType") is not None:
            c = UI.Cartao("Tipo", "padrao")
            seg = UI.Segmentado([(str(i), t, ic) for i, (_en, t, ic) in enumerate(TIPOS_FURO)], str(e["tipo"]),
                                colunas=3)
            seg.mudou.connect(lambda k: self._indice("HoleType", int(k)))
            c.widget(seg)
            self.campos["tipo"] = seg
            if e["tipo"] == 0 and f.visivel("ThreadFit"):
                cb = f.espelho("ThreadFit", FOLGAS_PT, largura=150)
                c.linha("Folga", cb)
                self.campos["folga"] = cb
            self.lay.addWidget(c)

        c = UI.Cartao("Profundidade", "seta_baixo")
        seg = UI.Segmentado([("0", "Medida", "medida"), ("1", "Através", "atraves")], str(max(0, e["prof_tipo"])),
                            colunas=2)
        seg.mudou.connect(lambda k: self._indice("DepthType", int(k)))
        c.widget(seg)
        self.campos["prof_tipo"] = seg
        if e["prof_tipo"] == 0 and e["prof"] is not None:
            num = UI.CampoNumero(e["prof"], "mm", minimo=0.0)
            num.valueChanged.connect(lambda v: f.por_numero("Depth", v))
            c.linha("Profundidade", num)
            self.campos["prof"] = num
        if f.check("DrillPointAngled") is not None and e["prof_tipo"] == 0:
            sw = UI.Interruptor(e["ponta"])
            sw.toggled.connect(lambda on: self._marcar("DrillPointAngled", on))
            c.linha("Ponta cônica (broca)", sw)
            self.campos["ponta"] = sw
        self.lay.addWidget(c)

        c = UI.Cartao("Cabeça", "chanfro")
        cb = f.espelho("HoleCutType", CABECAS_PT)
        cb.activated.connect(lambda _i: QtCore.QTimer.singleShot(0, self.montar))
        c.linha("Tipo", cb)
        self.campos["cabeca"] = cb
        if e["cabeca"] > 0 and e["cab_d"] is not None:
            num = UI.CampoNumero(e["cab_d"], "mm", minimo=0.0)
            num.setEnabled(e["cab_ok"])
            num.valueChanged.connect(lambda v: f.por_numero("HoleCutDiameter", v))
            c.linha("Diâmetro da cabeça", num)
            self.campos["cab_d"] = num
            if e["cab_p"] is not None and f.visivel("HoleCutDepth"):
                num = UI.CampoNumero(e["cab_p"], "mm", minimo=0.0)
                num.valueChanged.connect(lambda v: f.por_numero("HoleCutDepth", v))
                c.linha("Profundidade da cabeça", num)
                self.campos["cab_p"] = num
        self.lay.addWidget(c)

        c = UI.Cartao("Acabamento", "acabamento")
        if f.check("Reversed") is not None:
            sw = UI.Interruptor(e["inverter"])
            sw.toggled.connect(lambda on: self._marcar("Reversed", on))
            c.linha("Inverter o sentido", sw)
            self.campos["inverter"] = sw
        sw = UI.Interruptor(bool(getattr(self.obj, "Refine", False)))
        sw.toggled.connect(self._refinar)
        c.linha("Unir faces planas (refinar)", sw)
        self.campos["refinar"] = sw
        self.lay.addWidget(c)

        self.dica = UI.Dica("")
        self.lay.addWidget(self.dica)
        self.lay.addWidget(self.completo)
        self.mostrar_formulario()

    def _indice(self, nome, i):
        cb = self.f.combo(nome)
        if cb is not None and cb.currentIndex() != i:
            cb.setCurrentIndex(i)
        QtCore.QTimer.singleShot(0, self.montar)

    def precisa_do_formulario(self):
        return False


class _Base(PainelComando):
    """Começo comum dos painéis (sem os modos da extrusão)."""

    texto_completo = "Formulário completo do FreeCAD"
    QSS_EXTRA = ""

    def __init__(self, obj, quadro, parent=None):
        self.modos = []
        QtWidgets.QWidget.__init__(self, parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema("#PrumoUI { background: transparent; }" + self.QSS_EXTRA))
        self.obj = obj
        self.f = Formulario(quadro)
        self.quadro = quadro
        self.nome_medida = ""
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)
        self.completo = QtWidgets.QToolButton()
        self.completo.setObjectName("PrumoAvancado")
        self.completo.setCheckable(True)
        self.completo.setText(self.texto_completo)
        self.completo.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.completo.toggled.connect(lambda _on: self.mostrar_formulario())
        self.assinatura = None
        if getattr(self, "TITULO", ""):
            self.setProperty("prumo_titulo", self.TITULO)     # nome da aba do comando no painel lateral
        self.montar()

    def _indice(self, nome, i):
        cb = self.f.combo(nome)
        if cb is not None and cb.currentIndex() != i:
            cb.setCurrentIndex(i)
        QtCore.QTimer.singleShot(0, self.montar)

    def _fim(self):
        self.dica = UI.Dica("")
        self.lay.addWidget(self.dica)
        self.lay.addWidget(self.completo)
        self.mostrar_formulario()

    def _selecao(self, titulo, icone, itens, vazio, botoes, chave="itens"):
        """Cartão com o que foi escolhido na vista e os botões de escolha do FreeCAD (botões de alternar).
        botoes = [(nome no formulário, texto parado, texto escolhendo)]."""
        c = UI.Cartao(titulo, icone)
        n = len(itens)
        lb = QtWidgets.QLabel(("{} escolhido{}: ".format(n, "s" if n != 1 else "") + ", ".join(itens[:6]) +
                               ("…" if n > 6 else "")) if n else vazio)
        lb.setWordWrap(True)
        lb.setObjectName("PrumoSub")
        c.widget(lb)
        self.campos[chave] = lb
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for nome_fc, parado, escolhendo in botoes:
            fb = self.f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            ativo = bool(fb.isCheckable() and fb.isChecked())
            b = QtWidgets.QPushButton(escolhendo if ativo else parado)
            if ativo:
                b.setObjectName("PrumoPrimario")
            b.setEnabled(fb.isEnabled())
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(50, self.montar)))
            hl.addWidget(b)
            self.campos[nome_fc] = b
        hl.addStretch(1)
        c.widget(linha)
        self.lay.addWidget(c)
        return c

    def _lista(self, nome="listWidgetReferences"):
        lw = self.f.w(nome, QtWidgets.QListWidget)
        return tuple(lw.item(i).text() for i in range(lw.count())) if lw is not None else ()

    def _escolhendo(self, *nomes):
        for n in nomes:
            b = self.f.w(n, QtWidgets.QAbstractButton)
            if b is not None and b.isCheckable() and b.isChecked():
                return n
        return None

    def _chave(self, nome, rotulo, cartao, chave=None):
        """Interruptor ligado a um QCheckBox do formulário do FreeCAD (só se ele estiver visível)."""
        cb = self.f.check(nome)
        if cb is None or not cb.isVisibleTo(self.quadro):
            return None
        sw = UI.Interruptor(cb.isChecked())
        sw.setEnabled(cb.isEnabled())
        sw.toggled.connect(lambda on, n=nome: self._marcar(n, on))
        cartao.linha(rotulo, sw)
        self.campos[chave or nome] = sw
        return sw

    def _num(self, nome, rotulo, unid, cartao, minimo=None, chave=None):
        """Campo numérico ligado a um QuantitySpinBox do formulário (só se estiver visível)."""
        w = self.f.w(nome, QtWidgets.QAbstractSpinBox)
        v = self.f.numero(nome)
        if w is None or v is None or not w.isVisibleTo(self.quadro):
            return None
        num = UI.CampoNumero(v, unid) if minimo is None else UI.CampoNumero(v, unid, minimo=minimo)
        num.valueChanged.connect(lambda x, n=nome: self.f.por_numero(n, x))
        cartao.linha(rotulo, num)
        self.campos[chave or nome] = num
        return num

    def _num_un(self, nome, rotulo, unidade, cartao, minimo=None, casas=2, chave=None):
        """Como _num, mas convertendo da unidade interna do FreeCAD (força em mN, pressão em kPa…) para a
        unidade mostrada (N, MPa…). Só lengths e ângulos já vêm na unidade certa no rawValue."""
        w = self.f.w(nome, QtWidgets.QAbstractSpinBox)
        raw = self.f.numero(nome)
        if w is None or raw is None or not w.isVisibleTo(self.quadro):
            return None
        un = FreeCAD.Units.Quantity("1 " + unidade).Unit
        v = FreeCAD.Units.Quantity(raw, un).getValueAs(unidade).Value
        num = UI.CampoNumero(v, unidade, casas=casas) if minimo is None else \
            UI.CampoNumero(v, unidade, casas=casas, minimo=minimo)
        num.valueChanged.connect(
            lambda x, n=nome, u=unidade: self.f.por_numero(n, FreeCAD.Units.Quantity("%r %s" % (float(x), u)).Value))
        cartao.linha(rotulo, num)
        self.campos[chave or nome] = num
        return num

    def _acabamento(self, extra=None):
        if not extra and self.obj is not None and "Refine" not in self.obj.PropertiesList:
            return
        c = UI.Cartao("Acabamento", "acabamento")
        for rot, w in (extra or []):
            c.linha(rot, w)
        if self.obj is not None and "Refine" in self.obj.PropertiesList:
            sw = UI.Interruptor(bool(getattr(self.obj, "Refine", False)))
            sw.toggled.connect(self._refinar)
            c.linha("Unir faces planas (refinar)", sw)
            self.campos["refinar"] = sw
        self.lay.addWidget(c)


# Revolução / Ranhura: modos por posição na lista do FreeCAD
MODOS_REV = {
    "PartDesign::Revolution": [("Ângulo", "angulo"), ("Até o fim", "ate_fim"), ("Até a 1ª", "ate_primeira"),
                               ("Até a face", "ate_face"), ("Dois ângulos", "dois_lados")],
    "PartDesign::Groove": [("Ângulo", "angulo"), ("Através", "atraves"), ("Até a 1ª", "ate_primeira"),
                           ("Até a face", "ate_face"), ("Dois ângulos", "dois_lados")],
}


class PainelRevolucao(_Base):
    """Revolução e Ranhura: eixo, até onde gira, ângulo(s), simétrico, inverter."""

    def estado(self):
        f = self.f
        return {"modo": f.indice("changeMode"), "n": f.combo("changeMode").count() if f.combo("changeMode") else 0,
                "eixo": f.indice("axis"), "n_eixo": f.combo("axis").count() if f.combo("axis") else 0,
                "a1": f.numero("revolveAngle"), "a2": f.numero("revolveAngle2"),
                "meio": bool(f.check("checkBoxMidplane").isChecked()) if f.check("checkBoxMidplane") else False,
                "inv": bool(f.check("checkBoxReversed").isChecked()) if f.check("checkBoxReversed") else False,
                "a2_ok": f.visivel("revolveAngle2"), "a1_ok": f.visivel("revolveAngle")}

    def precisa_do_formulario(self):
        cb = self.f.combo("changeMode")
        return cb is not None and "face" in cb.currentText().lower()

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Eixo", "fixacao")
        cb = f.espelho("axis", {"Base X axis": "Eixo X", "Base Y axis": "Eixo Y", "Base Z axis": "Eixo Z",
                                "Horizontal sketch axis": "Eixo horizontal do esboço",
                                "Vertical sketch axis": "Eixo vertical do esboço", "Select reference…": "Escolher…",
                                "Select reference...": "Escolher…"})
        cb.activated.connect(lambda _i: QtCore.QTimer.singleShot(0, self.montar))
        c.linha("Gira em torno de", cb)
        self.campos["eixo"] = cb
        self.lay.addWidget(c)

        c = UI.Cartao("Até onde gira", "angulo")
        rot = MODOS_REV.get(self.obj.TypeId, [])
        fc = f.combo("changeMode")
        ops = []
        for i in range(fc.count() if fc else 0):
            t, ic = rot[i] if i < len(rot) else (fc.itemText(i), None)
            ops.append((str(i), t, ic))
        seg = UI.Segmentado(ops, str(e["modo"]), colunas=3)
        seg.mudou.connect(lambda k: self._indice("changeMode", int(k)))
        c.widget(seg)
        self.campos["modo"] = seg
        if e["a1"] is not None and e["a1_ok"]:
            num = UI.CampoNumero(e["a1"], "°")
            num.valueChanged.connect(lambda v: f.por_numero("revolveAngle", v))
            c.linha("Ângulo", num)
            self.campos["a1"] = num
        if e["a2"] is not None and e["a2_ok"]:
            num = UI.CampoNumero(e["a2"], "°")
            num.valueChanged.connect(lambda v: f.por_numero("revolveAngle2", v))
            c.linha("Ângulo 2", num)
            self.campos["a2"] = num
        if f.check("checkBoxMidplane") is not None and f.visivel("checkBoxMidplane"):
            sw = UI.Interruptor(e["meio"])
            sw.toggled.connect(lambda on: self._marcar("checkBoxMidplane", on))
            c.linha("Simétrico ao esboço", sw)
            self.campos["meio"] = sw
        if f.check("checkBoxReversed") is not None:
            sw = UI.Interruptor(e["inv"])
            sw.setEnabled(f.check("checkBoxReversed").isEnabled())
            sw.toggled.connect(lambda on: self._marcar("checkBoxReversed", on))
            c.linha("Inverter", sw)
            self.campos["inv"] = sw
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


TIPOS_CHANFRO = [("Distância igual", "chanfro"), ("Duas distâncias", "dois_lados"), ("Distância e ângulo", "angulo")]


class PainelAcabamentoArestas(_Base):
    """Arredondar e Chanfro: arestas escolhidas (lista) e as medidas."""

    def _refs(self):
        lw = self.f.w("listWidgetReferences", QtWidgets.QListWidget)
        return [lw.item(i).text() for i in range(lw.count())] if lw is not None else []

    def estado(self):
        f = self.f
        bt = f.w("buttonRefSel", QtWidgets.QToolButton)
        todas = f.check("checkBoxUseAllEdges")
        flip = f.w("flipDirection", QtWidgets.QAbstractButton)
        return {"refs": tuple(self._refs()), "sel": bool(bt.isChecked()) if bt else False,
                "todas": bool(todas.isChecked()) if todas else False,
                "raio": f.numero("filletRadius"), "tipo": f.indice("chamferType"),
                "d1": f.numero("chamferSize"), "d2": f.numero("chamferSize2"), "ang": f.numero("chamferAngle"),
                "flip": bool(flip.isChecked()) if flip else False, "flip_ok": bool(flip.isEnabled()) if flip else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        arred = self.obj.TypeId == "PartDesign::Fillet"

        c = UI.Cartao("Arestas", "selecao")
        n = len(e["refs"])
        resumo = QtWidgets.QLabel(("Todas as arestas da peça" if e["todas"] else
                                   ("{} escolhida{}: ".format(n, "s" if n != 1 else "") +
                                    ", ".join(e["refs"][:6]) + ("…" if n > 6 else "")) if n else
                                   "Nenhuma aresta escolhida"))
        resumo.setWordWrap(True)
        resumo.setObjectName("PrumoSub")
        c.widget(resumo)
        bt = f.w("buttonRefSel", QtWidgets.QToolButton)
        if bt is not None:
            b = QtWidgets.QPushButton("Concluir a escolha" if e["sel"] else "Escolher arestas na vista")
            b.setObjectName("PrumoPrimario" if e["sel"] else "")
            b.setEnabled(bt.isEnabled())
            b.clicked.connect(lambda: (bt.click(), QtCore.QTimer.singleShot(50, self.montar)))
            c.widget(b)
            self.campos["escolher"] = b
        if f.check("checkBoxUseAllEdges") is not None:
            sw = UI.Interruptor(e["todas"])
            sw.toggled.connect(lambda on: (self._marcar("checkBoxUseAllEdges", on),
                                           QtCore.QTimer.singleShot(0, self.montar)))
            c.linha("Todas as arestas", sw)
            self.campos["todas"] = sw
        if e["sel"]:
            self.dicas_escolha = True
        self.lay.addWidget(c)

        if arred:
            c = UI.Cartao("Arredondamento", "raio")
            num = UI.CampoNumero(e["raio"] or 0.0, "mm", minimo=0.0)
            num.valueChanged.connect(lambda v: f.por_numero("filletRadius", v))
            c.linha("Raio", num)
            self.campos["raio"] = num
            self.lay.addWidget(c)
        else:
            c = UI.Cartao("Chanfro", "chanfro")
            seg = UI.Segmentado([(str(i), t, ic) for i, (t, ic) in enumerate(TIPOS_CHANFRO)], str(max(0, e["tipo"])),
                                colunas=3)
            seg.mudou.connect(lambda k: self._indice("chamferType", int(k)))
            c.widget(seg)
            self.campos["tipo"] = seg
            num = UI.CampoNumero(e["d1"] or 0.0, "mm", minimo=0.0)
            num.valueChanged.connect(lambda v: f.por_numero("chamferSize", v))
            c.linha("Distância", num)
            self.campos["d1"] = num
            if e["tipo"] == 1 and e["d2"] is not None:
                num = UI.CampoNumero(e["d2"], "mm", minimo=0.0)
                num.valueChanged.connect(lambda v: f.por_numero("chamferSize2", v))
                c.linha("Distância 2", num)
                self.campos["d2"] = num
            if e["tipo"] == 2 and e["ang"] is not None:
                num = UI.CampoNumero(e["ang"], "°", minimo=0.0)
                num.valueChanged.connect(lambda v: f.por_numero("chamferAngle", v))
                c.linha("Ângulo", num)
                self.campos["ang"] = num
            if e["tipo"] in (1, 2):
                sw = UI.Interruptor(e["flip"])
                sw.setEnabled(e["flip_ok"])
                fl = f.w("flipDirection", QtWidgets.QAbstractButton)
                sw.toggled.connect(lambda on: fl is not None and fl.isChecked() != on and fl.click())
                c.linha("Inverter o lado", sw)
                self.campos["flip"] = sw
            self.lay.addWidget(c)
        self._acabamento()
        self._fim()

    def dica_extra(self):
        bt = self.f.w("buttonRefSel", QtWidgets.QToolButton)
        if bt is not None and bt.isChecked():
            return ("Clique nas arestas na vista: cada clique põe ou tira uma aresta. Depois, "
                    "\"Concluir a escolha\".")
        return ""

    def precisa_do_formulario(self):
        return False


UINT0 = -2 ** 31     # o UIntSpinBox do FreeCAD guarda o valor deslocado (0 → menor inteiro)
DIRECOES_PT = {"Base X axis": "Eixo X", "Base Y axis": "Eixo Y", "Base Z axis": "Eixo Z",
               "Horizontal sketch axis": "Eixo horizontal do esboço", "Vertical sketch axis": "Eixo vertical do esboço",
               "Normal sketch axis": "Normal ao esboço", "Select reference…": "Escolher…",
               "Select reference...": "Escolher…", "XY_Plane": "Plano XY", "XZ_Plane": "Plano XZ", "YZ_Plane": "Plano YZ"}


def _ativar(cb, i):
    """Troca a lista do FreeCAD como se fosse o usuário (estes formulários escutam 'activated')."""
    if cb is None or i < 0:
        return
    cb.setCurrentIndex(i)
    cb.activated.emit(i)


class PainelPadrao(_Base):
    """Padrão linear, Padrão circular e Espelhar: operações a repetir, direção(ões), quantidade e medidas."""

    def _direcoes(self):
        return [w for w in self.quadro.findChildren(QtWidgets.QWidget)
                if w.metaObject().className() == "PartGui::PatternParametersWidget"]

    def _dir_estado(self, w):
        g = w.findChild(QtWidgets.QGroupBox, "groupBox")
        en = w.findChild(QtWidgets.QCheckBox, "enableCheckbox")
        oc = w.findChild(QtWidgets.QSpinBox, "spinOccurrences")
        ext, esp = w.findChild(QtWidgets.QAbstractSpinBox, "spinExtent"), \
            w.findChild(QtWidgets.QAbstractSpinBox, "spinSpacing")
        cd, cm = w.findChild(QtWidgets.QComboBox, "comboDirection"), w.findChild(QtWidgets.QComboBox, "comboMode")
        ativa = g is not None and g.isVisibleTo(self.quadro) and (not g.isCheckable() or g.isChecked())
        return {"ativa": bool(ativa), "pode": bool(en is not None and en.isVisibleTo(self.quadro)) or bool(ativa),
                "dir": cd.currentIndex() if cd else -1, "n_dir": cd.count() if cd else 0,
                "modo": cm.currentIndex() if cm else 0,
                "ext": float(ext.property("rawValue")) if ext is not None and ext.property("rawValue") is not None
                else None,
                "esp": float(esp.property("rawValue")) if esp is not None and esp.property("rawValue") is not None
                else None,
                "ext_ok": bool(ext is not None and ext.isVisibleTo(self.quadro)),
                "esp_ok": bool(esp is not None and esp.isVisibleTo(self.quadro)),
                "unid": ext.property("unit") if ext is not None else "",
                "n": (oc.value() - UINT0) if oc is not None else None}

    def estado(self):
        lw = self.f.w("listWidgetFeatures", QtWidgets.QListWidget)
        add = self.f.w("buttonAddFeature", QtWidgets.QAbstractButton)
        rem = self.f.w("buttonRemoveFeature", QtWidgets.QAbstractButton)
        e = {"ops": tuple(lw.item(i).text() for i in range(lw.count())) if lw is not None else (),
             "add": bool(add.isChecked()) if add else False, "rem": bool(rem.isChecked()) if rem else False,
             "plano": self.f.indice("comboPlane"),
             "n_plano": self.f.combo("comboPlane").count() if self.f.combo("comboPlane") else 0}
        for i, w in enumerate(self._direcoes()):
            for k, v in self._dir_estado(w).items():
                e["d%d_%s" % (i, k)] = v
        return e

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        circular = self.obj.TypeId == "PartDesign::PolarPattern"

        c = UI.Cartao("Operações a repetir", "padrao")
        ops = e["ops"]
        lb = QtWidgets.QLabel(", ".join(ops) if ops else "Nenhuma operação escolhida")
        lb.setWordWrap(True)
        lb.setObjectName("PrumoSub")
        c.widget(lb)
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for chave, nome_fc, txt_on, txt_off in (("add", "buttonAddFeature", "Concluir", "Adicionar"),
                                                ("rem", "buttonRemoveFeature", "Concluir", "Tirar")):
            fb = f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            b = QtWidgets.QPushButton(txt_on if e[chave] else txt_off)
            if e[chave]:
                b.setObjectName("PrumoPrimario")
            b.setEnabled(fb.isEnabled())
            b.clicked.connect(lambda _=False, fb=fb: (fb.toggle(), QtCore.QTimer.singleShot(50, self.montar)))
            hl.addWidget(b)
            self.campos[chave] = b
        hl.addStretch(1)
        c.widget(linha)
        self.lay.addWidget(c)

        if self.obj.TypeId == "PartDesign::Mirrored":
            c = UI.Cartao("Plano de espelho", "simetrica")
            cb = QtWidgets.QComboBox()
            cb.setObjectName("PrumoLista")
            cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(8)
            fc = f.combo("comboPlane")
            for i in range(fc.count() if fc else 0):
                cb.addItem(DIRECOES_PT.get(fc.itemText(i), fc.itemText(i)))
            cb.setCurrentIndex(e["plano"])
            cb.activated.connect(lambda i: (_ativar(f.combo("comboPlane"), i),
                                            QtCore.QTimer.singleShot(0, self.montar)))
            c.linha("Espelhar em", cb)
            self.campos["plano"] = cb
            self.lay.addWidget(c)

        for i, w in enumerate(self._direcoes()):
            self._cartao_direcao(i, w, e, circular)

        self._acabamento()
        self._fim()

    def _cartao_direcao(self, i, w, e, circular):
        p = "d%d_" % i
        titulo = ("Eixo" if circular else "Direção") + (" %d" % (i + 1) if len(self._direcoes()) > 1 else "")
        segunda = i > 0
        c = UI.Cartao(titulo, "angulo" if circular else ("seta_cima" if i == 0 else "seta_baixo"),
                      chave=segunda, ligado=e[p + "ativa"])
        if segunda:
            en = w.findChild(QtWidgets.QCheckBox, "enableCheckbox")
            g = w.findChild(QtWidgets.QGroupBox, "groupBox")

            def alternar(on, en=en, g=g):
                if on and en is not None:
                    en.setChecked(True)
                elif not on and g is not None and g.isCheckable():
                    g.setChecked(False)
                QtCore.QTimer.singleShot(50, self.montar)
            c.chave.toggled.connect(alternar)
            self.campos[p + "ativa"] = c.chave
        if not segunda or e[p + "ativa"]:
            cd = w.findChild(QtWidgets.QComboBox, "comboDirection")
            cb = QtWidgets.QComboBox()
            cb.setObjectName("PrumoLista")
            cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(8)
            for k in range(cd.count() if cd else 0):
                cb.addItem(DIRECOES_PT.get(cd.itemText(k), cd.itemText(k)))
            cb.setCurrentIndex(e[p + "dir"])
            cb.activated.connect(lambda k, cd=cd: (_ativar(cd, k), QtCore.QTimer.singleShot(0, self.montar)))
            c.linha("Em torno de" if circular else "Ao longo de", cb)
            self.campos[p + "dir"] = cb
            cm = w.findChild(QtWidgets.QComboBox, "comboMode")
            seg = UI.Segmentado([("0", "Ângulo total" if circular else "Comprimento total", "medida"),
                                 ("1", "Entre cópias", "padrao")], str(e[p + "modo"]), colunas=2)
            seg.mudou.connect(lambda k, cm=cm: (_ativar(cm, int(k)), QtCore.QTimer.singleShot(0, self.montar)))
            c.widget(seg)
            self.campos[p + "modo"] = seg
            unid = "°" if circular else "mm"
            if e[p + "ext_ok"] and e[p + "ext"] is not None:
                num = UI.CampoNumero(e[p + "ext"], unid, minimo=0.0)
                ext = w.findChild(QtWidgets.QAbstractSpinBox, "spinExtent")
                num.valueChanged.connect(lambda v, ext=ext: ext.setProperty("rawValue", float(v)))
                c.linha("Ângulo total" if circular else "Comprimento total", num)
                self.campos[p + "ext"] = num
            if e[p + "esp_ok"] and e[p + "esp"] is not None:
                num = UI.CampoNumero(e[p + "esp"], unid, minimo=0.0)
                esp = w.findChild(QtWidgets.QAbstractSpinBox, "spinSpacing")
                num.valueChanged.connect(lambda v, esp=esp: esp.setProperty("rawValue", float(v)))
                c.linha("Entre cópias", num)
                self.campos[p + "esp"] = num
            if e[p + "n"] is not None:
                oc = w.findChild(QtWidgets.QSpinBox, "spinOccurrences")
                n = QtWidgets.QSpinBox()
                n.setObjectName("PrumoNum")
                n.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                n.setRange(1, 10000)
                n.setKeyboardTracking(False)
                n.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                n.setMaximumWidth(120)
                n.setValue(int(e[p + "n"]))
                n.valueChanged.connect(lambda v, oc=oc: oc.setValue(int(v) + UINT0))
                c.linha("Quantidade (com o original)", n)
                self.campos[p + "n"] = n
            rv = w.findChild(QtWidgets.QAbstractButton, "PushButtonReverse")
            if rv is not None:
                b = QtWidgets.QPushButton("Inverter o sentido")
                b.clicked.connect(lambda _=False, rv=rv: rv.click())
                c.widget(b)
        self.lay.addWidget(c)

    def dica_extra(self):
        e = self.estado()
        if e["add"]:
            return "Clique na árvore ou na vista nas operações que quer repetir; depois, \"Concluir\"."
        if e["rem"]:
            return "Clique nas operações que quer tirar do padrão; depois, \"Concluir\"."
        return ""

    def precisa_do_formulario(self):
        return False


DICA_ESCOLHA = {
    "buttonBodyAdd": "Clique nos corpos (na árvore ou na vista) que entram na operação; depois, \"Concluir\".",
    "buttonBodyRemove": "Clique nos corpos que quer tirar; depois, \"Concluir\".",
    "buttonRefSel": "Clique nas faces na vista: cada clique põe ou tira uma face. Depois, \"Concluir\".",
    "buttonPlane": "Clique na face ou no plano que fica parado (plano neutro).",
    "buttonLine": "Clique na aresta ou no eixo que dá a direção de saída do molde.",
    "buttonProfileBase": "Clique no esboço (ou face) do perfil.",
    "buttonSpineBase": "Clique no esboço ou nas arestas do caminho.",
    "buttonRefAdd": "Clique nos itens que quer acrescentar; depois, \"Concluir\".",
    "buttonRefRemove": "Clique nos itens que quer tirar; depois, \"Concluir\".",
}


class _Escolhas(_Base):
    """Painéis em que o principal é escolher coisas na vista (faces, perfis, caminho)."""

    BOTOES = ()

    def dica_extra(self):
        n = self._escolhendo(*self.BOTOES)
        return DICA_ESCOLHA.get(n, "")

    def precisa_do_formulario(self):
        return False


class PainelAngulo(_Escolhas):
    """Ângulo de saída: faces, ângulo, plano neutro e direção de saída."""

    BOTOES = ("buttonRefSel", "buttonPlane", "buttonLine")

    def estado(self):
        f = self.f
        lp, ll = f.w("linePlane", QtWidgets.QLineEdit), f.w("lineLine", QtWidgets.QLineEdit)
        return {"refs": self._lista(), "ang": f.numero("draftAngle"), "esc": self._escolhendo(*self.BOTOES),
                "plano": lp.text() if lp else "", "linha": ll.text() if ll else "",
                "inv": bool(f.check("checkReverse").isChecked()) if f.check("checkReverse") else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._selecao("Faces a inclinar", "selecao", list(e["refs"]), "Nenhuma face escolhida",
                      [("buttonRefSel", "Escolher faces na vista", "Concluir a escolha")], "faces")
        c = UI.Cartao("Inclinação", "angulo")
        self._num("draftAngle", "Ângulo", "°", c, minimo=0.0, chave="ang")
        self._chave("checkReverse", "Inverter o sentido", c, "inv")
        self.lay.addWidget(c)
        c = UI.Cartao("Referências", "fixacao")
        for chave, nome_fc, rot, vazio in (("plano", "buttonPlane", "Plano neutro", "Automático"),
                                           ("linha", "buttonLine", "Direção de saída", "Normal ao plano")):
            fb = self.f.w(nome_fc, QtWidgets.QAbstractButton)
            b = QtWidgets.QPushButton(e[chave] or vazio)
            b.setToolTip("Clique e escolha na vista")
            if fb is not None:
                if fb.isCheckable() and fb.isChecked():
                    b.setObjectName("PrumoPrimario")
                    b.setText("Escolhendo… (clique na vista)")
                b.setEnabled(fb.isEnabled())
                b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(50, self.montar)))
            c.linha(rot, b)
            self.campos[chave] = b
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


MODOS_CASCA = [("0", "Casca", "solido"), ("1", "Tubo", "atraves"), ("2", "Frente e verso", "dois_lados")]
JUNCOES = [("0", "Arredondada", "raio"), ("1", "Canto vivo", "chanfro")]


class PainelCasca(_Escolhas):
    """Casca: faces que ficam abertas, espessura, para dentro, modo e junção."""

    BOTOES = ("buttonRefSel",)

    def estado(self):
        f = self.f
        return {"refs": self._lista(), "esp": f.numero("Value"), "esc": self._escolhendo(*self.BOTOES),
                "modo": f.indice("modeComboBox"), "junta": f.indice("joinComboBox"),
                "dentro": bool(f.check("checkReverse").isChecked()) if f.check("checkReverse") else False,
                "inter": bool(f.check("checkIntersection").isChecked()) if f.check("checkIntersection") else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._selecao("Faces abertas", "selecao", list(e["refs"]), "Nenhuma face escolhida (casca fechada)",
                      [("buttonRefSel", "Escolher faces na vista", "Concluir a escolha")], "faces")
        c = UI.Cartao("Parede", "medida")
        self._num("Value", "Espessura", "mm", c, minimo=0.0, chave="esp")
        self._chave("checkReverse", "Para dentro", c, "dentro")
        self.lay.addWidget(c)
        c = UI.Cartao("Como é feita", "acabamento")
        seg = UI.Segmentado(MODOS_CASCA, str(max(0, e["modo"])), colunas=3)
        seg.mudou.connect(lambda k: (_ativar(self.f.combo("modeComboBox"), int(k)),
                                     QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["modo"] = seg
        sub = QtWidgets.QLabel("Cantos")
        sub.setObjectName("PrumoSub")
        c.widget(sub)
        seg = UI.Segmentado(JUNCOES, str(max(0, e["junta"])), colunas=2)
        seg.mudou.connect(lambda k: (_ativar(self.f.combo("joinComboBox"), int(k)),
                                     QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["junta"] = seg
        self._chave("checkIntersection", "Permitir interseções", c, "inter")
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


MODOS_HELICE = [("0", "Passo e altura", "medida"), ("1", "Passo e voltas", "padrao"),
                ("2", "Altura e voltas", "seta_cima"), ("3", "Com crescimento", "angulo")]


class PainelHelice(_Base):
    """Hélice (aditiva e subtrativa): eixo, como medir e as medidas."""

    def estado(self):
        f = self.f
        vis = tuple(f.visivel(n) for n in ("pitch", "height", "turns", "coneAngle", "growth", "checkBoxOutside"))
        return {"eixo": f.indice("axis"), "n_eixo": f.combo("axis").count() if f.combo("axis") else 0,
                "modo": f.indice("inputMode"), "vis": vis,
                "vals": tuple(f.numero(n) for n in ("pitch", "height", "turns", "coneAngle", "growth")),
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("checkBoxLeftHanded", "checkBoxReversed", "checkBoxOutside"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Eixo", "fixacao")
        fc = f.combo("axis")
        cb = QtWidgets.QComboBox()
        cb.setObjectName("PrumoLista")
        cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(8)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        for i in range(fc.count() if fc else 0):
            t = fc.itemText(i)
            cb.addItem(DIRECOES_PT.get(t, DIRECOES_PT.get(t.replace("-axis", " axis"), t)))
        cb.setCurrentIndex(e["eixo"])
        cb.activated.connect(lambda i: (_ativar(f.combo("axis"), i), QtCore.QTimer.singleShot(0, self.montar)))
        c.linha("Gira em torno de", cb)
        self.campos["eixo"] = cb
        self.lay.addWidget(c)

        c = UI.Cartao("Medidas", "medida")
        im = f.combo("inputMode")
        ops = [o for o in MODOS_HELICE if im is not None and int(o[0]) < im.count()]
        seg = UI.Segmentado(ops, str(max(0, e["modo"])), colunas=2)
        seg.mudou.connect(lambda k: (_ativar(f.combo("inputMode"), int(k)), QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["modo"] = seg
        self._num("pitch", "Passo", "mm", c, minimo=0.0)
        self._num("height", "Altura", "mm", c)
        turns = f.w("turns", QtWidgets.QAbstractSpinBox)
        if turns is not None and turns.isVisibleTo(self.quadro) and f.numero("turns") is not None:
            num = UI.CampoNumero(f.numero("turns"), "", minimo=0.0)
            num.valueChanged.connect(lambda x: f.por_numero("turns", x))
            c.linha("Voltas", num)
            self.campos["turns"] = num
        self._num("coneAngle", "Ângulo do cone", "°", c)
        self._num("growth", "Crescimento por volta", "mm", c)
        self.lay.addWidget(c)

        c = UI.Cartao("Sentido", "seta_cima")
        self._chave("checkBoxLeftHanded", "Rosca à esquerda", c)
        self._chave("checkBoxReversed", "Inverter", c)
        self._chave("checkBoxOutside", "Remover por fora", c)
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()

    def precisa_do_formulario(self):
        cb = self.f.combo("axis")
        return cb is not None and "refer" in cb.currentText().lower()


class PainelLoft(_Escolhas):
    """Loft (aditivo e subtrativo): perfil base, seções e forma."""

    BOTOES = ("buttonProfileBase", "buttonRefAdd", "buttonRefRemove")

    def estado(self):
        f = self.f
        pb = f.w("profileBaseEdit", QtWidgets.QLineEdit)
        return {"base": pb.text() if pb else "", "secoes": self._lista(), "esc": self._escolhendo(*self.BOTOES),
                "regrada": bool(f.check("checkBoxRuled").isChecked()) if f.check("checkBoxRuled") else False,
                "fechado": bool(f.check("checkBoxClosed").isChecked()) if f.check("checkBoxClosed") else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._selecao("Perfil inicial", "perfil", [e["base"]] if e["base"] else [], "Nenhum perfil escolhido",
                      [("buttonProfileBase", "Escolher perfil", "Escolhendo…")], "base")
        self._selecao("Seções (na ordem)", "lista", list(e["secoes"]), "Nenhuma seção: escolha pelo menos uma",
                      [("buttonRefAdd", "Adicionar", "Concluir"), ("buttonRefRemove", "Tirar", "Concluir")],
                      "secoes")
        c = UI.Cartao("Forma", "solido")
        self._chave("checkBoxRuled", "Faces retas entre as seções", c, "regrada")
        self._chave("checkBoxClosed", "Fechar (volta ao primeiro perfil)", c, "fechado")
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


TRANSICOES = [("0", "Transformada", "angulo"), ("1", "Canto reto", "chanfro"), ("2", "Canto redondo", "raio")]


class PainelVarredura(_Escolhas):
    """Varredura (aditiva e subtrativa): perfil, caminho e transição nos cantos.
    Orientação e seções extras continuam nos quadros do FreeCAD logo abaixo."""

    BOTOES = ("buttonProfileBase", "buttonSpineBase", "buttonRefAdd", "buttonRefRemove")

    def estado(self):
        f = self.f
        pb, sb = f.w("profileBaseEdit", QtWidgets.QLineEdit), f.w("spineBaseEdit", QtWidgets.QLineEdit)
        return {"perfil": pb.text() if pb else "", "caminho": sb.text() if sb else "", "arestas": self._lista(),
                "esc": self._escolhendo(*self.BOTOES), "trans": f.indice("comboBoxTransition")}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._selecao("Perfil", "perfil", [e["perfil"]] if e["perfil"] else [], "Nenhum perfil escolhido",
                      [("buttonProfileBase", "Escolher perfil", "Escolhendo…")], "perfil")
        itens = ([e["caminho"]] if e["caminho"] else []) + list(e["arestas"])
        self._selecao("Caminho", "seta_cima", itens, "Nenhum caminho escolhido",
                      [("buttonSpineBase", "Escolher caminho", "Escolhendo…"), ("buttonRefAdd", "Mais arestas", "Concluir"),
                       ("buttonRefRemove", "Tirar", "Concluir")], "caminho")
        c = UI.Cartao("Cantos do caminho", "acabamento")
        seg = UI.Segmentado(TRANSICOES, str(max(0, e["trans"])), colunas=3)
        seg.mudou.connect(lambda k: (_ativar(self.f.combo("comboBoxTransition"), int(k)),
                                     QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["trans"] = seg
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


PRIMITIVAS = {
    "Box": ("Cubo", [("boxLength", "Comprimento"), ("boxWidth", "Largura"), ("boxHeight", "Altura")]),
    "Cylinder": ("Cilindro", [("cylinderRadius", "Raio"), ("cylinderHeight", "Altura"), ("cylinderAngle", "Ângulo")]),
    "Sphere": ("Esfera", [("sphereRadius", "Raio")]),
    "Cone": ("Cone", [("coneRadius1", "Raio da base"), ("coneRadius2", "Raio do topo"), ("coneHeight", "Altura"),
                      ("coneAngle", "Ângulo")]),
    "Ellipsoid": ("Elipsoide", [("ellipsoidRadius1", "Raio 1"), ("ellipsoidRadius2", "Raio 2"),
                                ("ellipsoidRadius3", "Raio 3")]),
    "Torus": ("Toro", [("torusRadius1", "Raio do anel"), ("torusRadius2", "Raio do tubo")]),
    "Prism": ("Prisma", [("prismPolygon", "Lados"), ("prismCircumradius", "Raio circunscrito"),
                         ("prismHeight", "Altura")]),
    "Wedge": ("Cunha", []),
}


def nome_do_campo(objn):
    """Nome em português de um campo de medida das primitivas (ex.: cylinderXSkew → Inclinação em X)."""
    import re
    m = re.match(r"^[a-z]+([XY])Skew$", objn)
    if m:
        return "Inclinação em " + m.group(1)
    m = re.match(r"^[a-z]+Angle(\d)$", objn)
    if m:
        return {"1": "Ângulo inicial", "2": "Ângulo final", "3": "Ângulo de giro"}.get(m.group(1), "Ângulo")
    m = re.match(r"^wedge(X2|Z2|X|Y|Z)(min|max)$", objn)
    if m:
        return "%s %s" % (m.group(1), "mínimo" if m.group(2) == "min" else "máximo")
    return None


def _rotulo_na_grade(w):
    """Texto do rótulo ao lado de um campo, numa grade do formulário do FreeCAD."""
    nome = nome_do_campo(w.objectName())
    if nome:
        return nome
    pai = w.parentWidget()
    lay = pai.layout() if pai is not None else None
    if isinstance(lay, QtWidgets.QGridLayout):
        i = lay.indexOf(w)
        if i >= 0:
            r, c, _rs, _cs = lay.getItemPosition(i)
            for cc in range(c - 1, -1, -1):
                it = lay.itemAtPosition(r, cc)
                if it is not None and isinstance(it.widget(), QtWidgets.QLabel):
                    return it.widget().text().rstrip(":")
    for lb in pai.findChildren(QtWidgets.QLabel) if pai is not None else []:
        if lb.buddy() is w:
            return lb.text().rstrip(":")
    return w.objectName()


class PainelPrimitiva(_Base):
    """Primitivas de Peça (cubo, cilindro, esfera… aditivos e subtrativos): as medidas em cartão.
    A posição (fixação) continua no quadro do FreeCAD logo abaixo."""

    def _tipo(self):
        t = self.obj.TypeId.split("::")[1]
        return t.replace("Additive", "").replace("Subtractive", "")

    def _pagina(self):
        st = self.f.w("widgetStack", QtWidgets.QStackedWidget) or self.q_pilha()
        return st.currentWidget() if st is not None else None

    def q_pilha(self):
        pilhas = self.quadro.findChildren(QtWidgets.QStackedWidget) if self.quadro is not None else []
        return pilhas[0] if pilhas else None

    def _campos(self):
        pg = self._pagina()
        if pg is None:
            return []
        return [w for w in pg.findChildren(QtWidgets.QAbstractSpinBox) if w.isVisibleTo(pg)]

    def estado(self):
        vals = []
        for w in self._campos():
            v = w.property("rawValue") if w.property("rawValue") is not None else w.value()
            vals.append((w.objectName(), round(float(v), 9)))
        return {"tipo": self._tipo(), "vals": tuple(vals)}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        nome, principais = PRIMITIVAS.get(e["tipo"], (e["tipo"], []))
        campos = {w.objectName(): w for w in self._campos()}
        c = UI.Cartao("Medidas · " + nome, "medida")
        usados = set()
        for objn, rot in principais:
            if objn in campos:
                self._campo(c, campos[objn], rot)
                usados.add(objn)
        resto = [w for n, w in campos.items() if n not in usados]
        if not principais:
            for w in resto:
                self._campo(c, w, _rotulo_na_grade(w))
            resto = []
        self.lay.addWidget(c)
        if resto:
            c = UI.Cartao("Mais medidas", "angulo")
            for w in resto:
                self._campo(c, w, _rotulo_na_grade(w))
            self.lay.addWidget(c)
        self._acabamento()
        self._fim()

    def _campo(self, cartao, w, rotulo):
        nome = w.objectName()
        if isinstance(w, QtWidgets.QSpinBox):
            n = QtWidgets.QSpinBox()
            n.setObjectName("PrumoNum")
            n.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            n.setRange(w.minimum(), w.maximum())
            n.setKeyboardTracking(False)
            n.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            n.setMaximumWidth(120)
            n.setValue(w.value())
            n.valueChanged.connect(lambda v, w=w: w.setValue(int(v)))
            cartao.linha(rotulo, n)
            self.campos[nome] = n
            return
        v = w.property("rawValue")
        if v is None:
            return
        unid = "°" if "angle" in nome.lower() or "skew" in nome.lower() else "mm"
        num = UI.CampoNumero(float(v), unid)
        num.valueChanged.connect(lambda x, w=w: w.setProperty("rawValue", float(x)))
        cartao.linha(rotulo, num)
        self.campos[nome] = num

    def precisa_do_formulario(self):
        return False


TIPOS_BOOLEANA = [("0", "Unir", "solido"), ("1", "Cortar", "atraves"), ("2", "Interseção", "dois_lados")]


class PainelBooleana(_Escolhas):
    """Booleana de Peça: corpos que entram e o tipo (unir, cortar, interseção)."""

    BOTOES = ("buttonBodyAdd", "buttonBodyRemove")

    def estado(self):
        return {"corpos": self._lista("listWidgetBodies"), "tipo": self.f.indice("comboType"),
                "esc": self._escolhendo(*self.BOTOES)}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._selecao("Corpos", "corpo", list(e["corpos"]), "Nenhum corpo escolhido",
                      [("buttonBodyAdd", "Adicionar", "Concluir"), ("buttonBodyRemove", "Tirar", "Concluir")],
                      "corpos")
        c = UI.Cartao("Operação", "solido")
        seg = UI.Segmentado(TIPOS_BOOLEANA, str(max(0, e["tipo"])), colunas=3)
        seg.mudou.connect(lambda k: (_ativar(self.f.combo("comboType"), int(k)),
                                     QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["tipo"] = seg
        self.lay.addWidget(c)
        self._acabamento()
        self._fim()


# ----------------------------------------------------------------------------------- Desenho: vistas
# posição de cada caixinha do formulário (chkView0…9) na grade 3 × 4, e o nome da vista em cada diedro
GRADE_VISTAS = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (1, 3),
                7: (2, 0), 8: (2, 1), 9: (2, 2)}
VISTAS_3 = {0: "FrontTopLeft", 1: "Top", 2: "FrontTopRight", 3: "Left", 4: "Front", 5: "Right", 6: "Rear",
            7: "FrontBottomLeft", 8: "Bottom", 9: "FrontBottomRight"}
VISTAS_1 = {0: "FrontBottomRight", 1: "Bottom", 2: "FrontBottomLeft", 3: "Right", 4: "Front", 5: "Left",
            6: "Rear", 7: "FrontTopRight", 8: "Top", 9: "FrontTopLeft"}
NOMES_VISTA = {"Front": "Frontal", "Top": "Superior", "Bottom": "Inferior", "Left": "Lateral esq.",
               "Right": "Lateral dir.", "Rear": "Posterior", "FrontTopLeft": "Isométrica",
               "FrontTopRight": "Isométrica", "FrontBottomLeft": "Isométrica", "FrontBottomRight": "Isométrica"}
DICA_VISTA = {"FrontTopLeft": "Isométrica de cima, pela esquerda", "FrontTopRight": "Isométrica de cima, pela direita",
              "FrontBottomLeft": "Isométrica de baixo, pela esquerda",
              "FrontBottomRight": "Isométrica de baixo, pela direita"}
ESCALAS = [("0", "Da folha", "lista"), ("1", "Automática", "medida"), ("2", "Escolher", "numero")]
DIEDROS = [("0", "1º diedro", "seta_baixo"), ("1", "3º diedro", "seta_cima"), ("2", "Da folha", "lista")]
GIROS = [("butLeftRotate", "←", "Girar para a esquerda"), ("butRightRotate", "→", "Girar para a direita"),
         ("butTopRotate", "↑", "Girar para cima"), ("butDownRotate", "↓", "Girar para baixo"),
         ("butCCWRotate", "⟲", "Girar no sentido anti-horário"), ("butCWRotate", "⟳", "Girar no sentido horário")]


def direcao_em_palavras(texto):
    """'[0.00 -1.00 0.00]' → 'de frente (−Y)'. A direção da vista aponta da peça para quem olha."""
    import re
    nums = re.findall(r"-?\d+(?:[.,]\d+)?", texto or "")
    try:
        v = [float(n.replace(",", ".")) for n in nums[:3]]
    except ValueError:
        return texto
    if len(v) != 3:
        return texto
    nomes = {(0, -1, 0): "de frente (−Y)", (0, 1, 0): "de trás (+Y)", (0, 0, 1): "de cima (+Z)",
             (0, 0, -1): "de baixo (−Z)", (1, 0, 0): "pela direita (+X)", (-1, 0, 0): "pela esquerda (−X)"}
    chave = tuple(int(round(x)) if abs(abs(x) - round(abs(x))) < 1e-3 else None for x in v)
    if chave in nomes:
        return nomes[chave]
    return "na direção ({:.2f}; {:.2f}; {:.2f})".format(*v).replace(".", ",")


def terceiro_diedro(f):
    """O formulário de vistas está no 3º diedro? (o Brasil usa o 1º; o FreeCAD vem no 1º por padrão)"""
    cb = f.combo("projection")
    i = cb.currentIndex() if cb is not None and cb.isVisibleTo(f.q) else -1
    if i == 1:
        return True
    if i == 0:
        return False
    if i == 2:
        try:
            for pg in FreeCAD.ActiveDocument.findObjects(Type="TechDraw::DrawPage"):
                return str(pg.ProjectionType).startswith("Third")
        except Exception:
            return False
        return False
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/General").GetInt(
        "ProjectionAngle", 0) == 1


class PainelVistas(_Base):
    """Desenho → Vista / Grupo de projeção: quais vistas entram (grade no diedro certo), direção da frontal,
    escala e arranjo. Comanda o formulário do FreeCAD, que é quem cria as vistas."""

    QSS_EXTRA = ("QToolButton#PrumoVista { border: 1px solid #DCE4EC; border-radius: 8px; background: #FFFFFF;"
                 " color: #3B4A59; padding: 4px 2px; }"
                 "QToolButton#PrumoVista:hover { border-color: #003A70; color: #003A70; }"
                 "QToolButton#PrumoVista:checked { background: #E6EEF7; border-color: #003A70; color: #003A70;"
                 " font-weight: 600; }"
                 "QToolButton#PrumoVista:disabled { color: #B6C0CA; border-color: #EEF2F6; }")

    def _caixa(self, i):
        return self.f.w("chkView%d" % i, QtWidgets.QCheckBox)

    def estado(self):
        f = self.f
        caixas = []
        for i in range(10):
            c = self._caixa(i)
            caixas.append((bool(c.isChecked()), bool(c.isEnabled()), bool(c.isVisibleTo(self.quadro)))
                          if c is not None else (False, False, False))
        prim = f.w("lePrimary", QtWidgets.QPushButton)
        sx, sy = f.numero("sbXSpacing"), f.numero("sbYSpacing")
        num, den = f.w("sbScaleNum", QtWidgets.QSpinBox), f.w("sbScaleDen", QtWidgets.QSpinBox)
        auto = f.w("cbAutoDistribute", QtWidgets.QCheckBox)
        return {"caixas": tuple(caixas), "terceiro": terceiro_diedro(f), "escala": f.indice("cmbScaleType"),
                "num": num.value() if num else 1, "den": den.value() if den else 1,
                "grupo": bool(f.combo("projection") is not None and f.combo("projection").isVisibleTo(self.quadro)),
                "diedro": f.indice("projection"), "auto": bool(auto.isChecked()) if auto else False,
                "sx": round(sx, 6) if sx is not None else None, "sy": round(sy, 6) if sy is not None else None,
                "prim": prim.text() if prim else ""}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        nomes = VISTAS_3 if e["terceiro"] else VISTAS_1

        # vistas
        c = UI.Cartao("Vistas", "padrao")
        sub = QtWidgets.QLabel("Clique para pôr ou tirar uma vista. A posição é a da folha "
                               "(%s diedro)." % ("3º" if e["terceiro"] else "1º"))
        sub.setObjectName("PrumoSub")
        sub.setWordWrap(True)
        c.widget(sub)
        grade = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(grade)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(4)
        for col in range(4):
            g.setColumnStretch(col, 1)
        secundarias = any(e["caixas"][i][2] for i in range(10) if i != 4)
        for i, (marcada, pode, vis) in enumerate(e["caixas"]):
            nome = nomes[i]
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoVista")
            b.setCheckable(True)
            b.setChecked(marcada)
            b.setText(NOMES_VISTA.get(nome, nome))
            b.setToolTip(DICA_VISTA.get(nome, NOMES_VISTA.get(nome, nome)))
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            b.setMinimumHeight(34)
            b.setEnabled(pode and (vis or i == 4) and (secundarias or i == 4))
            b.clicked.connect(lambda _on=False, i=i: self._alternar(i))
            r, col = GRADE_VISTAS[i]
            g.addWidget(b, r, col)
            self.campos["vista%d" % i] = b
        c.widget(grade)
        if not secundarias:
            aviso = QtWidgets.QLabel("Esta vista é avulsa: para um grupo de vistas, use Grupo de projeção.")
            aviso.setObjectName("PrumoSub")
            aviso.setWordWrap(True)
            c.widget(aviso)
        self.lay.addWidget(c)

        # direção da frontal
        c = UI.Cartao("Direção da vista frontal", "seta_cima")
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for nome_fc, txt, dica in GIROS:
            fb = f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoVista")
            b.setText(txt)
            b.setToolTip(dica)
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            b.setMinimumHeight(30)
            b.setEnabled(fb.isEnabled())
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(80, self.montar)))
            hl.addWidget(b, 1)
            self.campos[nome_fc] = b
        c.widget(linha)
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for nome_fc, txt, dica in (("butFront", "Frente padrão", "Volta a frontal para a frente da peça"),
                                   ("butCam", "Como está na tela", "A frontal fica como a peça aparece na vista 3D "
                                                                   "(ou de frente para a face escolhida)")):
            fb = f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            b = QtWidgets.QPushButton(txt)
            b.setToolTip(dica)
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(80, self.montar)))
            hl.addWidget(b)
            self.campos[nome_fc] = b
        hl.addStretch(1)
        c.widget(linha)
        if e["prim"]:
            lb = QtWidgets.QLabel("A frontal mostra a peça vista " + direcao_em_palavras(e["prim"]))
            lb.setObjectName("PrumoSub")
            c.widget(lb)
        self.lay.addWidget(c)

        # escala
        c = UI.Cartao("Escala", "medida")
        seg = UI.Segmentado(ESCALAS, str(max(0, e["escala"])), colunas=3)
        seg.mudou.connect(lambda k: (self._indice("cmbScaleType", int(k))))
        c.widget(seg)
        self.campos["escala"] = seg
        par = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(par)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for chave, nome_fc in (("num", "sbScaleNum"), ("den", "sbScaleDen")):
            fc = f.w(nome_fc, QtWidgets.QSpinBox)
            n = QtWidgets.QSpinBox()
            n.setObjectName("PrumoNum")
            n.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            n.setRange(1, 100000)
            n.setKeyboardTracking(False)
            n.setAlignment(QtCore.Qt.AlignCenter)
            n.setMaximumWidth(70)
            n.setValue(int(e[chave]))
            n.setEnabled(e["escala"] == 2 and fc is not None)
            if fc is not None:
                n.valueChanged.connect(lambda v, fc=fc: fc.setValue(int(v)))
            hl.addWidget(n)
            self.campos[chave] = n
            if chave == "num":
                dois = QtWidgets.QLabel(":")
                hl.addWidget(dois)
        hl.addStretch(1)
        c.linha("Escala da vista", par)
        self.lay.addWidget(c)

        # arranjo (só em grupo de projeção)
        if e["grupo"]:
            c = UI.Cartao("Arranjo na folha", "lista")
            seg = UI.Segmentado(DIEDROS, str(max(0, e["diedro"])), colunas=3)
            seg.mudou.connect(lambda k: self._indice("projection", int(k)))
            c.widget(seg)
            self.campos["diedro"] = seg
            ab = f.w("cbAutoDistribute", QtWidgets.QCheckBox)
            if ab is not None:
                sw = UI.Interruptor(e["auto"])
                sw.toggled.connect(lambda on, ab=ab: (ab.isChecked() != on and ab.click(),
                                                      QtCore.QTimer.singleShot(50, self.montar)))
                c.linha("Espaçar sozinho", sw)
                self.campos["auto"] = sw
            if e["auto"]:
                self._num("sbXSpacing", "Espaço na horizontal", "mm", c, minimo=0.0, chave="sx")
                self._num("sbYSpacing", "Espaço na vertical", "mm", c, minimo=0.0, chave="sy")
            self.lay.addWidget(c)
        self._fim()

    def _alternar(self, i):
        cx = self._caixa(i)
        if cx is not None and cx.isEnabled():
            cx.setChecked(not cx.isChecked())
        QtCore.QTimer.singleShot(80, self.montar)

    def precisa_do_formulario(self):
        return False


def _texto_espelho(cartao, rotulo, fc, largura=80, campos=None, chave=None):
    """Campo de texto curto ligado a um QLineEdit do formulário (o FreeCAD lê no editingFinished)."""
    le = QtWidgets.QLineEdit(fc.text() if fc is not None else "")
    le.setObjectName("PrumoTexto")
    le.setMaximumWidth(largura)
    le.setAlignment(QtCore.Qt.AlignCenter)
    if fc is None:
        le.setEnabled(False)
    else:
        def passar(le=le, fc=fc):
            if fc.text() != le.text():
                fc.setText(le.text())
                fc.editingFinished.emit()
        le.editingFinished.connect(passar)
    cartao.linha(rotulo, le)
    if campos is not None and chave:
        campos[chave] = le
    return le


def _escala_cartao(painel, cartao, nome_tipo, nome_valor, quantidade=True):
    """Segmentado Da folha / Automática / Escolher + valor quando escolhida (corte e detalhe)."""
    f = painel.f
    i = f.indice(nome_tipo)
    seg = UI.Segmentado(ESCALAS, str(max(0, i)), colunas=3)
    seg.mudou.connect(lambda k: painel._indice(nome_tipo, int(k)))
    cartao.widget(seg)
    painel.campos["escala"] = seg
    w = f.w(nome_valor, QtWidgets.QAbstractSpinBox)
    if w is None:
        return
    if quantidade:
        v = f.numero(nome_valor)
    else:
        v = w.value()
    if v is None:
        return
    num = UI.CampoNumero(float(v), "", casas=4, minimo=0.0001)
    num.setEnabled(i == 2)
    if quantidade:
        num.valueChanged.connect(lambda x: f.por_numero(nome_valor, x))
    else:
        num.valueChanged.connect(lambda x, w=w: w.setValue(float(x)))
    cartao.linha("Fator de escala (ex.: 0,5 = 1:2)", num)
    painel.campos["fator"] = num


DIRECOES_CORTE = [("pbLeft", "← Esquerda", "Olhando para a esquerda"), ("pbRight", "→ Direita", "Olhando para a direita"),
                  ("pbUp", "↑ Cima", "Olhando para cima"), ("pbDown", "↓ Baixo", "Olhando para baixo")]


class PainelCorte(_Base):
    """Desenho → Vista em corte: letra, para onde o corte olha, onde passa o plano, escala e atualização."""

    QSS_EXTRA = PainelVistas.QSS_EXTRA

    def estado(self):
        f = self.f
        le, base = f.w("leSymbol", QtWidgets.QLineEdit), f.w("leBaseView", QtWidgets.QLineEdit)
        sc = f.w("sbScale", QtWidgets.QDoubleSpinBox)
        live = f.w("cbLiveUpdate", QtWidgets.QCheckBox)
        return {"letra": le.text() if le else "", "base": base.text() if base else "",
                "escala": f.indice("cmbScaleType"), "fator": round(sc.value(), 6) if sc else None,
                "org": tuple(f.numero(n) for n in ("sbOrgX", "sbOrgY", "sbOrgZ")),
                "live": bool(live.isChecked()) if live else False,
                "dir_ok": tuple(bool(f.w(n, QtWidgets.QAbstractButton) and
                                     f.w(n, QtWidgets.QAbstractButton).isEnabled()) for n, _t, _d in DIRECOES_CORTE)}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Corte", "texto")
        if e["base"]:
            c.linha("Vista de origem", UI.Chip(e["base"]))
        _texto_espelho(c, "Letra do corte (ex.: A)", f.w("leSymbol", QtWidgets.QLineEdit), campos=self.campos,
                       chave="letra")
        self.lay.addWidget(c)

        c = UI.Cartao("Para onde o corte olha", "seta_cima")
        sub = QtWidgets.QLabel("Escolha a direção: o corte aparece na folha ao lado da vista de origem.")
        sub.setObjectName("PrumoSub")
        sub.setWordWrap(True)
        c.widget(sub)
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for nome_fc, txt, dica in DIRECOES_CORTE:
            fb = f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            b = QtWidgets.QToolButton()
            b.setObjectName("PrumoVista")
            b.setText(txt)
            b.setToolTip(dica)
            b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
            b.setMinimumHeight(32)
            b.setEnabled(fb.isEnabled())
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(150, self.montar)))
            hl.addWidget(b, 1)
            self.campos[nome_fc] = b
        c.widget(linha)
        self.lay.addWidget(c)

        c = UI.Cartao("O plano de corte passa por", "fixacao")
        for nome_fc, rot in (("sbOrgX", "X"), ("sbOrgY", "Y"), ("sbOrgZ", "Z")):
            self._num(nome_fc, rot, "mm", c)
        self.lay.addWidget(c)

        c = UI.Cartao("Escala", "medida")
        _escala_cartao(self, c, "cmbScaleType", "sbScale", quantidade=False)
        self.lay.addWidget(c)

        c = UI.Cartao("Atualização", "acabamento")
        lv = f.w("cbLiveUpdate", QtWidgets.QCheckBox)
        if lv is not None:
            sw = UI.Interruptor(e["live"])
            sw.toggled.connect(lambda on, lv=lv: (lv.isChecked() != on and lv.click(),
                                                  QtCore.QTimer.singleShot(50, self.montar)))
            c.linha("Atualizar a cada mudança", sw)
            self.campos["live"] = sw
        up = f.w("pbUpdateNow", QtWidgets.QAbstractButton)
        if up is not None and not e["live"]:
            b = QtWidgets.QPushButton("Atualizar agora")
            b.clicked.connect(lambda _=False, up=up: up.click())
            c.widget(b)
            self.campos["atualizar"] = b
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


class PainelDetalhe(_Base):
    """Desenho → Vista de detalhe: letra, onde fica o círculo (arrastar na folha, X, Y, raio) e escala."""

    def estado(self):
        f = self.f
        le, base = f.w("leReference", QtWidgets.QLineEdit), f.w("leBaseView", QtWidgets.QLineEdit)
        return {"letra": le.text() if le else "", "base": base.text() if base else "",
                "escala": f.indice("cbScaleType"),
                "nums": tuple(f.numero(n) for n in ("qsbX", "qsbY", "qsbRadius", "qsbScale"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Detalhe", "texto")
        if e["base"]:
            c.linha("Vista de origem", UI.Chip(e["base"]))
        _texto_espelho(c, "Letra do detalhe (ex.: B)", f.w("leReference", QtWidgets.QLineEdit), campos=self.campos,
                       chave="letra")
        self.lay.addWidget(c)

        c = UI.Cartao("Onde fica o círculo", "raio")
        dr = f.w("pbDragger", QtWidgets.QAbstractButton)
        if dr is not None:
            b = QtWidgets.QPushButton("Arrastar o círculo na folha")
            b.setToolTip("Depois de clicar, arraste o círculo sobre a vista de origem")
            b.setEnabled(dr.isEnabled())
            b.clicked.connect(lambda _=False, dr=dr: dr.click())
            c.widget(b)
            self.campos["arrastar"] = b
        self._num("qsbX", "X do centro", "mm", c)
        self._num("qsbY", "Y do centro", "mm", c)
        self._num("qsbRadius", "Raio", "mm", c, minimo=0.0)
        self.lay.addWidget(c)

        c = UI.Cartao("Escala", "medida")
        _escala_cartao(self, c, "cbScaleType", "qsbScale", quantidade=True)
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


def _num_simples(painel, nome, rotulo, unid, cartao, inteiro=False, casas=2, minimo=None, chave=None):
    """Campo ligado a um QSpinBox/QDoubleSpinBox comum do formulário (sem rawValue)."""
    cls = QtWidgets.QSpinBox if inteiro else QtWidgets.QDoubleSpinBox
    w = painel.f.w(nome, cls)
    if w is None or not w.isVisibleTo(painel.quadro):
        return None
    if inteiro:
        n = QtWidgets.QSpinBox()
        n.setObjectName("PrumoNum")
        n.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        n.setRange(w.minimum(), w.maximum())
        n.setKeyboardTracking(False)
        n.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        n.setMaximumWidth(120)
        n.setValue(w.value())
        n.valueChanged.connect(lambda v, w=w: w.setValue(int(v)))
    else:
        n = UI.CampoNumero(w.value(), unid, casas=casas) if minimo is None else \
            UI.CampoNumero(w.value(), unid, casas=casas, minimo=minimo)
        n.valueChanged.connect(lambda v, w=w: w.setValue(float(v)))
    cartao.linha(rotulo, n)
    painel.campos[chave or nome] = n
    return n


class PainelCota(_Base):
    """Desenho → editar uma cota: casas decimais, referência, exata, texto livre, tolerância e aparência."""

    def estado(self):
        f = self.f
        chk = ("cbReference", "cbTheoreticallyExact", "cbArbitrary", "cbEqualTolerance", "cbArrowheads")
        sb = f.w("sbNumDecimals", QtWidgets.QSpinBox)
        le = f.w("leFormatSpecifier", QtWidgets.QLineEdit)
        return {"chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False for n in chk),
                "dec": sb.value() if sb else None, "fmt": le.text() if le else "",
                "tol": (f.numero("qsbOvertolerance"), f.numero("qsbUndertolerance")),
                "fonte": f.numero("qsbFontSize"), "estilo": f.indice("comboDrawingStyle")}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Valor", "numero")
        _num_simples(self, "sbNumDecimals", "Casas decimais", "", c, inteiro=True, chave="dec")
        self._chave("cbReference", "Cota de referência (entre parênteses)", c, "ref")
        self._chave("cbTheoreticallyExact", "Teoricamente exata (em caixa)", c, "exata")
        arb = self._chave("cbArbitrary", "Texto livre no lugar do valor", c, "livre")
        le = f.w("leFormatSpecifier", QtWidgets.QLineEdit)
        if le is not None and arb is not None and e["chk"][2]:
            t = QtWidgets.QLineEdit(le.text())
            t.setObjectName("PrumoTexto")
            t.textChanged.connect(lambda x, le=le: le.setText(x))
            c.linha("Texto", t)
            self.campos["texto"] = t
        self.lay.addWidget(c)

        c = UI.Cartao("Tolerância", "medida")
        self._chave("cbEqualTolerance", "Simétrica (±)", c, "simetrica")
        self._num("qsbOvertolerance", "Superior", "mm", c, chave="sup")
        if not e["chk"][3]:
            self._num("qsbUndertolerance", "Inferior", "mm", c, chave="inf")
        self.lay.addWidget(c)

        c = UI.Cartao("Aparência", "aparencia")
        self._num("qsbFontSize", "Tamanho do texto", "mm", c, minimo=0.1, chave="fonte")
        self._chave("cbArrowheads", "Inverter as setas", c, "setas")
        cb = f.combo("comboDrawingStyle")
        if cb is not None and cb.isVisibleTo(self.quadro):
            lista = f.espelho("comboDrawingStyle", {"ISO oriented": "ISO, texto alinhado à linha",
                                                    "ISO referencing": "ISO, texto em linha de chamada",
                                                    "ASME inlined": "ASME, texto no meio da linha",
                                                    "ASME referencing": "ASME, texto em linha de chamada"},
                              largura=260)
            lista.setMinimumContentsLength(16)
            c.linha("Estilo", lista)
            self.campos["estilo"] = lista
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


FORMAS_BALAO = {"Circular": "Círculo", "None": "Sem forma", "Triangle": "Triângulo", "Inspection": "Inspeção",
                "Hexagon": "Hexágono", "Square": "Quadrado", "Rectangle": "Retângulo", "Line": "Sublinhado"}
PONTAS = {"Filled arrow": "Seta cheia", "Open arrow": "Seta aberta", "Tick": "Traço", "Dot": "Ponto",
          "Open circle": "Círculo aberto", "Fork": "Garfo", "Filled triangle": "Triângulo cheio", "None": "Nenhuma"}


class PainelBalao(_Base):
    """Desenho → editar um balão: texto (número da peça), forma, tamanho, ponta e linha."""

    def estado(self):
        f = self.f
        le = f.w("leText", QtWidgets.QLineEdit)
        return {"texto": le.text() if le else "", "forma": f.indice("comboBubbleShape"),
                "ponta": f.indice("comboEndSymbol"), "linha": f.indice("comboLineVisible"),
                "nums": tuple(f.numero(n) for n in ("qsbFontSize", "qsbShapeScale", "qsbLineWidth"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Balão", "texto")
        le = f.w("leText", QtWidgets.QLineEdit)
        if le is not None:
            t = QtWidgets.QLineEdit(le.text())
            t.setObjectName("PrumoTexto")
            t.setMaximumWidth(120)
            t.setAlignment(QtCore.Qt.AlignCenter)
            t.textChanged.connect(lambda x, le=le: le.setText(x))
            c.linha("Texto (nº da peça)", t)
            self.campos["texto"] = t
        forma = f.espelho("comboBubbleShape", FORMAS_BALAO)
        c.linha("Forma", forma)
        self.campos["forma"] = forma
        self._num("qsbFontSize", "Tamanho do texto", "mm", c, minimo=0.1, chave="fonte")
        self._num("qsbShapeScale", "Escala da forma", "", c, minimo=0.01, chave="escala")
        self.lay.addWidget(c)
        c = UI.Cartao("Linha de chamada", "seta_cima")
        ponta = f.espelho("comboEndSymbol", PONTAS, largura=220)
        ponta.setMinimumContentsLength(14)
        c.linha("Ponta", ponta)
        self.campos["ponta"] = ponta
        lv = f.combo("comboLineVisible")
        if lv is not None:
            sw = UI.Interruptor(lv.currentIndex() == 1)
            sw.toggled.connect(lambda on, lv=lv: lv.setCurrentIndex(1 if on else 0))
            c.linha("Mostrar a linha", sw)
            self.campos["linha"] = sw
        self._num("qsbLineWidth", "Espessura", "mm", c, minimo=0.0, chave="espessura")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


def _botao_cor(painel, cartao, rotulo, fc, chave):
    """Botão de cor ligado a um Gui::ColorButton do formulário (propriedade "color" + sinal changed)."""
    from PySide import QtGui
    if fc is None:
        return None
    cor = fc.property("color")
    b = QtWidgets.QPushButton()
    b.setObjectName("PrumoCor")
    b.setMinimumWidth(80)
    b.setToolTip("Clique para trocar a cor")

    def pintar(c):
        c = QtGui.QColor(c) if c is not None else QtGui.QColor("black")
        b.setText(c.name().upper())
        b.setStyleSheet("QPushButton#PrumoCor { border-left: 14px solid %s; }" % c.name())
    pintar(cor)

    def trocar():
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(fc.property("color")), painel, rotulo)
        if c.isValid():
            painel.definir_cor(fc, c)
            pintar(c)
    b.clicked.connect(trocar)
    cartao.linha(rotulo, b)
    painel.campos[chave] = b
    return b


def _padroes_hachura():
    """Padrões SVG que vêm com o TechDraw: [(nome legível, caminho)]."""
    import glob
    pasta = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Patterns")
    out = []
    for c in sorted(glob.glob(os.path.join(pasta, "*.svg"))):
        nome = os.path.splitext(os.path.basename(c))[0]
        out.append((NOMES_PADRAO.get(nome, nome.replace("_", " ").capitalize()), c))
    return out


NOMES_PADRAO = {"aluminium": "Alumínio", "brick01": "Tijolo", "concrete": "Concreto", "cross": "Cruzado",
                "cuprous": "Cobre", "diagonal1": "Diagonal", "diagonal2": "Diagonal invertida", "earth": "Terra",
                "general_steel": "Aço (geral)", "glass": "Vidro", "hatch45L": "45° à esquerda",
                "hatch45R": "45° à direita", "hbone": "Espinha de peixe", "line": "Linhas", "plus": "Cruzes",
                "simple": "Simples", "solid": "Cheio", "square": "Quadriculado", "steel": "Aço",
                "titanium": "Titânio", "wood": "Madeira", "woodgrain": "Veio de madeira", "zinc": "Zinco"}


class PainelHachura(_Base):
    """Desenho → hachura de face: padrão (arquivo), cor, escala, rotação e deslocamento."""

    def definir_cor(self, fc, c):
        fc.setProperty("color", c)
        QtCore.QMetaObject.invokeMethod(fc, "changed")

    def _arquivo(self):
        fc = self.f.w("fcFile", QtWidgets.QWidget)
        le = fc.findChild(QtWidgets.QLineEdit) if fc is not None else None
        return fc, le

    def definir_arquivo(self, caminho):
        _fc, le = self._arquivo()
        if le is None:
            return
        le.setText(caminho)
        le.editingFinished.emit()
        QtCore.QTimer.singleShot(0, self.montar)

    def estado(self):
        f = self.f
        vals = []
        for n in ("dsbRotation", "dsbOffsetX", "dsbOffsetY"):
            w = f.w(n, QtWidgets.QDoubleSpinBox)
            vals.append(round(w.value(), 6) if w else None)
        _fc, le = self._arquivo()
        cc = f.w("ccColor", QtWidgets.QWidget)
        cor = cc.property("color") if cc is not None else None
        return {"escala": f.numero("sbScale"), "vals": tuple(vals), "arq": le.text() if le else "",
                "cor": cor.name() if cor is not None else ""}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        c = UI.Cartao("Padrão", "padrao")
        cb = QtWidgets.QComboBox()
        cb.setObjectName("PrumoLista")
        cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(8)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        atual = os.path.normcase(os.path.abspath(e["arq"])) if e["arq"] else ""
        idx = -1
        for nome, cam in _padroes_hachura():
            cb.addItem(nome, cam)
            if os.path.normcase(os.path.abspath(cam)) == atual:
                idx = cb.count() - 1
        if idx < 0 and e["arq"]:
            cb.addItem(os.path.basename(e["arq"]), e["arq"])
            idx = cb.count() - 1
        cb.setCurrentIndex(max(idx, 0))
        cb.activated.connect(lambda i, cb=cb: self.definir_arquivo(cb.itemData(i)))
        c.linha("Desenho", cb)
        self.campos["padrao"] = cb
        fc, _le = self._arquivo()
        bt = fc.findChild(QtWidgets.QPushButton) if fc is not None else None
        if bt is not None:
            b = QtWidgets.QPushButton("Outro arquivo (SVG)…")
            b.clicked.connect(lambda _=False, bt=bt: (bt.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.widget(b)
        _botao_cor(self, c, "Cor", self.f.w("ccColor", QtWidgets.QWidget), "cor")
        self.lay.addWidget(c)
        c = UI.Cartao("Tamanho e giro", "medida")
        self._num("sbScale", "Escala do padrão", "", c, minimo=0.0001, chave="escala")
        _num_simples(self, "dsbRotation", "Rotação", "°", c, chave="rotacao")
        self.lay.addWidget(c)
        c = UI.Cartao("Deslocamento do padrão", "fixacao")
        _num_simples(self, "dsbOffsetX", "X", "mm", c, chave="dx")
        _num_simples(self, "dsbOffsetY", "Y", "mm", c, chave="dy")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


ESTILOS_LINHA = {"NoLine": "Sem linha", "Continuous": "Contínua", "Dash": "Tracejada", "Dot": "Pontilhada",
                 "DashDot": "Traço e ponto", "DashDotDot": "Traço e dois pontos"}


class PainelTextoFormatado(_Base):
    """Desenho → texto formatado (RichAnno): o texto, largura máxima e moldura."""

    definir_cor = PainelHachura.definir_cor

    def estado(self):
        f = self.f
        te = f.w("teAnnoText", QtWidgets.QTextEdit)
        sf = f.check("cbShowFrame")
        return {"txt": te.toPlainText() if te else "", "larg": f.numero("dsbMaxWidth"),
                "moldura": bool(sf.isChecked()) if sf else False, "estilo": f.indice("cFrameStyle"),
                "esp": f.numero("dsbWidth")}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        te = f.w("teAnnoText", QtWidgets.QTextEdit)
        c = UI.Cartao("Texto", "texto")
        if te is not None:
            ed = QtWidgets.QTextEdit()
            ed.setObjectName("PrumoTextoLongo")
            ed.setAcceptRichText(True)
            ed.setHtml(te.toHtml())
            ed.setPlaceholderText("Escreva o texto aqui (ou use o editor completo para negrito, tamanhos…)")
            ed.setMinimumHeight(90)
            ed.setMaximumHeight(160)
            ed.setEnabled(te.isEnabled())

            def passar(ed=ed, te=te):
                if ed.toHtml() != te.toHtml():
                    te.blockSignals(True)
                    te.setHtml(ed.toHtml())
                    te.blockSignals(False)
            ed.textChanged.connect(passar)
            c.widget(ed)
            self.campos["texto"] = ed
        pe = f.w("pbEditor", QtWidgets.QAbstractButton)
        if pe is not None:
            b = QtWidgets.QPushButton("Editor completo (negrito, cores, tamanhos)…")
            b.setEnabled(pe.isEnabled())
            b.clicked.connect(lambda _=False, pe=pe: (pe.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.widget(b)
            self.campos["editor"] = b
        self._num("dsbMaxWidth", "Largura máxima", "mm", c, chave="largura")
        dica = QtWidgets.QLabel("-1 = largura automática")
        dica.setObjectName("PrumoSub")
        c.widget(dica)
        self.lay.addWidget(c)
        c = UI.Cartao("Moldura", "exibicao_arestas")
        self._chave("cbShowFrame", "Mostrar moldura", c, "moldura")
        if e["moldura"]:
            cb = f.espelho("cFrameStyle", ESTILOS_LINHA, largura=200)
            c.linha("Linha", cb)
            self.campos["estilo"] = cb
            self._num("dsbWidth", "Espessura", "mm", c, minimo=0.0, chave="espessura")
            _botao_cor(self, c, "Cor", f.w("cpFrameColor", QtWidgets.QWidget), "cor")
        self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        return ""

    def precisa_do_formulario(self):
        return False


# formulários que não dependem de uma operação de Peça em edição: marca → classe
# (marcas únicas de cada formulário do FreeCAD: "cmbScaleType" existe no de vistas e no de corte)
AVULSOS = {"chkView4": "PainelVistas", "gbOrientation": "PainelCorte", "qsbRadius": "PainelDetalhe",
           "gbTolerancing": "PainelCota", "comboBubbleShape": "PainelBalao", "fcFile": "PainelHachura",
           "spinLenFwd": "PainelExtrusaoPart", "selectLine": "PainelRevolucaoPart",
           "referenceLineEdit": "PainelEspelharPart", "rbUniform": "PainelEscalaPart",
           "filletStartRadius": "PainelArestasPart", "advancedOffsetCheckbox": "PainelJunta",
           "partList": "PainelInserirPecas",
           "TaskFemConstraintFixed": "PainelFixacaoFem", "TaskFemConstraintForce": "PainelForcaFem",
           "TaskFemConstraintPressure": "PainelPressaoFem",
           "TaskFemConstraintDisplacement": "PainelDeslocamentoFem", "TaskFemConstraintSpring": "PainelMolaFem", "FemMaterial": "PainelMaterialFem",
           "GmshMesh": "PainelMalhaGmsh", "teAnnoText": "PainelTextoFormatado", "spinOffset": "PainelOffsetPart",
           "checkRuledSurface": "PainelLoftPart", "buttonPath": "PainelVarreduraPart"}


# ----------------------------------------------------------------------------------- Fixação (anexar)
class PainelFixacao(_Base):
    """Quadro "Fixação" do FreeCAD (auxiliares, primitivas, Editar fixação) em cartões: em que a peça se
    prende, o modo e o deslocamento. Fica logo acima do quadro original, que some."""

    texto_completo = "Fixação completa do FreeCAD"

    def _refs(self):
        out = []
        for i in range(1, 5):
            b = self.f.w("buttonRef%d" % i, QtWidgets.QAbstractButton)
            le = self.f.w("lineRef%d" % i, QtWidgets.QLineEdit)
            if b is None or le is None:
                continue
            out.append((i, b, le))
        return out

    def _n_referencias(self):
        """Quantas referências o objeto em edição já tem (None se não der para saber)."""
        try:
            vp = FreeCADGui.ActiveDocument.getInEdit()
            obj = vp.Object if vp is not None else None
            return len(obj.AttachmentSupport) if obj is not None and hasattr(obj, "AttachmentSupport") else None
        except Exception:
            return None

    def _modos(self):
        lw = self.f.w("listOfModes", QtWidgets.QListWidget)
        if lw is None:
            return None, []
        itens = []
        for i in range(lw.count()):
            it = lw.item(i)
            ok = bool(it.flags() & QtCore.Qt.ItemIsEnabled)
            itens.append((i, it.text(), it.toolTip(), ok, it.isSelected()))
        return lw, itens

    def estado(self):
        f = self.f
        refs = tuple((b.text(), le.text(), b.isEnabled(), bool(b.isCheckable() and b.isChecked()))
                     for _i, b, le in self._refs())
        _lw, modos = self._modos()
        gb = f.w("groupBox_AttachmentOffset", QtWidgets.QGroupBox)
        msg = f.w("message", QtWidgets.QLabel)
        return {"refs": refs, "modos": tuple((t, ok, sel) for _i, t, _d, ok, sel in modos),
                "desl": bool(gb.isEnabled()) if gb else False,
                "nums": tuple(f.numero("attachmentOffset" + n) for n in ("X", "Y", "Z", "Roll", "Pitch", "Yaw")),
                "flip": bool(f.check("checkBoxFlip").isChecked()) if f.check("checkBoxFlip") else False,
                "msg": msg.text() if msg else ""}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f

        c = UI.Cartao("Fixação: onde se prende", "fixacao")
        n_refs = self._n_referencias()
        algum = False
        for n, (i, b, le) in enumerate(self._refs()):
            preenchida = n < n_refs if n_refs is not None else bool(le.text().strip()) and b.isEnabled()
            # mostra as preenchidas e a próxima livre (o FreeCAD libera uma de cada vez)
            if n > 0 and not preenchida and (not b.isEnabled() or (n_refs is not None and n > n_refs)):
                continue
            texto = le.text().strip() if preenchida else ""
            algum = True
            escolhendo = bool(b.isCheckable() and b.isChecked()) or "…" in b.text() or "..." in b.text()
            bt = QtWidgets.QPushButton("Escolhendo… clique na vista" if escolhendo else
                                       (texto or "Escolher na vista"))
            bt.setToolTip(texto or "Clique e escolha na vista (face, aresta, ponto ou plano)")
            if escolhendo:
                bt.setObjectName("PrumoPrimario")
            bt.setEnabled(b.isEnabled())
            bt.clicked.connect(lambda _=False, b=b: (b.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.linha("Referência %d" % (n + 1), bt)
            self.campos["ref%d" % i] = bt
        if not algum:
            lb = QtWidgets.QLabel("Solta (sem referência)")
            lb.setObjectName("PrumoSub")
            c.widget(lb)
        self.lay.addWidget(c)

        lw, modos = self._modos()
        if lw is not None and modos:
            c = UI.Cartao("Modo", "lista")
            cb = QtWidgets.QComboBox()
            cb.setObjectName("PrumoLista")
            cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(16)
            cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            atual = 0
            mapa = []
            for i, texto, dica, ok, sel in modos:
                if not ok:
                    continue
                cb.addItem(texto)
                cb.setItemData(cb.count() - 1, dica, QtCore.Qt.ToolTipRole)
                mapa.append(i)
                if sel:
                    atual = cb.count() - 1
            cb.setCurrentIndex(atual)

            def escolher(k, lw=lw, mapa=mapa):
                if 0 <= k < len(mapa):
                    lw.setCurrentRow(mapa[k])
                    it = lw.item(mapa[k])
                    if it is not None and not it.isSelected():
                        it.setSelected(True)
                QtCore.QTimer.singleShot(80, self.montar)
            cb.activated.connect(escolher)
            c.widget(cb)
            self.campos["modo"] = cb
            self.lay.addWidget(c)

        if e["desl"]:
            c = UI.Cartao("Deslocamento", "seta_cima")
            for suf, rot, unid in (("X", "X", "mm"), ("Y", "Y", "mm"), ("Z", "Z", "mm"),
                                   ("Roll", "Rotação em X", "°"), ("Pitch", "Rotação em Y", "°"),
                                   ("Yaw", "Rotação em Z", "°")):
                self._num("attachmentOffset" + suf, rot, unid, c, chave="desl" + suf)
            self._chave("checkBoxFlip", "Inverter o lado", c, "flip")
            self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        msg = self.f.w("message", QtWidgets.QLabel)
        return msg.text().strip() if msg is not None and msg.isVisibleTo(self.quadro) else ""

    def precisa_do_formulario(self):
        return False


class EncaixeFixacao:
    """Põe um painel em cartões acima de um quadro SECUNDÁRIO do FreeCAD sempre que ele aparece no painel de
    tarefas, independente do painel principal (ex.: "Fixação" nas primitivas; orientação e seções da
    Varredura). Por padrão, o quadro Fixação."""

    MARCA = "listOfModes"
    CLASSE = "PainelFixacao"

    def __init__(self, marca=None, classe=None):
        if marca:
            self.MARCA = marca
        if classe:
            self.CLASSE = classe
        self.painel = None
        self.t = QtCore.QTimer(FreeCADGui.getMainWindow())
        self.t.setInterval(300)
        self.t.timeout.connect(self._tick)

    def iniciar(self):
        self.t.start()

    def _vivo(self):
        return self.painel is not None and shiboken.isValid(self.painel)

    def _tirar(self):
        if self._vivo():
            self.painel.hide()
            self.painel.setParent(None)
            self.painel.deleteLater()
        self.painel = None

    def _tick(self):
        try:
            self._passo()
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: fixação: {}\n".format(exc))

    def _passo(self):
        panel = _painel_de_tarefas() if ligado() else None
        classe_fc = CLASSES_SEM_NOME.get(self.MARCA)
        if panel is not None and classe_fc:
            for w in panel.findChildren(QtWidgets.QWidget):
                if w.objectName() != self.MARCA and (w.metaObject().className() == classe_fc or
                                                     type(w).__name__ == classe_fc):
                    w.setObjectName(self.MARCA)
        quadro = _quadro_do_formulario(panel, self.MARCA) if panel is not None else None
        if quadro is None:
            if self.painel is not None:
                self._tirar()
            return
        if not self._vivo() or self.painel.parent() is not panel or self.painel.quadro is not quadro:
            self._tirar()
            self.painel = globals()[self.CLASSE](None, quadro, panel)
            lay = panel.layout()
            lay.insertWidget(lay.indexOf(quadro), self.painel)
            return
        self.painel.atualizar()
        self.painel.mostrar_formulario()


# ----------------------------------------------------------------------------------- Sólidos (Part)
def _formas_cartao(painel, nome_arvore, titulo="Formas", vazio="Nenhuma forma disponível"):
    """Cartão com as formas da lista do FreeCAD como interruptores (ligado = a forma entra na operação)."""
    tree = painel.f.w(nome_arvore, QtWidgets.QTreeWidget)
    c = UI.Cartao(titulo, "solido")
    if tree is None or tree.topLevelItemCount() == 0:
        lb = QtWidgets.QLabel(vazio)
        lb.setObjectName("PrumoSub")
        c.widget(lb)
        painel.lay.addWidget(c)
        return c
    # os formulários de Sólidos usam as linhas SELECIONADAS da lista (não a caixinha)
    for i in range(min(tree.topLevelItemCount(), 12)):
        it = tree.topLevelItem(i)
        sw = UI.Interruptor(it.isSelected())
        sw.toggled.connect(lambda on, it=it: it.setSelected(bool(on)))
        c.linha(it.text(0), sw)
        painel.campos["forma%d" % i] = sw
    if tree.topLevelItemCount() > 12:
        lb = QtWidgets.QLabel("… e mais {} (veja no formulário completo)".format(tree.topLevelItemCount() - 12))
        lb.setObjectName("PrumoSub")
        c.widget(lb)
    painel.lay.addWidget(c)
    return c


def _estado_arvore(f, nome):
    tree = f.w(nome, QtWidgets.QTreeWidget)
    if tree is None:
        return ()
    return tuple((tree.topLevelItem(i).text(0), tree.topLevelItem(i).isSelected())
                 for i in range(tree.topLevelItemCount()))


def _botao_eixo(painel, linha_layout, nome_fc, texto):
    fb = painel.f.w(nome_fc, QtWidgets.QAbstractButton)
    if fb is None:
        return
    b = QtWidgets.QToolButton()
    b.setObjectName("PrumoVista")
    b.setText(texto)
    b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
    b.setMinimumHeight(30)
    b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(80, painel.montar)))
    linha_layout.addWidget(b, 1)
    painel.campos[nome_fc] = b


def _radio(painel, nome):
    r = painel.f.w(nome, QtWidgets.QRadioButton)
    return bool(r.isChecked()) if r is not None else False


DIR_EXTRUSAO = [("rbDirModeNormal", "Normal da face", "seta_cima"), ("rbDirModeEdge", "Ao longo de aresta", "medida"),
                ("rbDirModeCustom", "Escolher", "numero")]


class PainelExtrusaoPart(_Base):
    """Sólidos → Extrusão: formas, direção, comprimento (a favor, oposto, simétrica, ângulo) e sólido."""

    QSS_EXTRA = PainelVistas.QSS_EXTRA

    def estado(self):
        f = self.f
        return {"formas": _estado_arvore(f, "treeWidget"),
                "dir": tuple(_radio(self, n) for n, _t, _i in DIR_EXTRUSAO),
                "nums": tuple(f.numero(n) for n in ("spinLenFwd", "spinLenRev", "spinTaperAngle", "spinTaperAngleRev")),
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("chkReversed", "chkSymmetric", "chkSolid"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        _formas_cartao(self, "treeWidget")
        c = UI.Cartao("Direção", "seta_cima")
        atual = next((n for (n, _t, _i), on in zip(DIR_EXTRUSAO, e["dir"]) if on), DIR_EXTRUSAO[0][0])
        seg = UI.Segmentado([(n, t, i) for n, t, i in DIR_EXTRUSAO], atual, colunas=3)

        def modo(k):
            r = f.w(k, QtWidgets.QRadioButton)
            if r is not None:
                r.setChecked(True)
            QtCore.QTimer.singleShot(0, self.montar)
        seg.mudou.connect(modo)
        c.widget(seg)
        self.campos["dir"] = seg
        if atual == "rbDirModeEdge":
            le = f.w("txtLink", QtWidgets.QLineEdit)
            bt = f.w("btnSelectEdge", QtWidgets.QAbstractButton)
            b = QtWidgets.QPushButton((le.text() if le is not None and le.text() else "Escolher aresta na vista"))
            if bt is not None:
                b.clicked.connect(lambda _=False, bt=bt: (bt.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.linha("Aresta", b)
            self.campos["aresta"] = b
        if atual == "rbDirModeCustom":
            linha = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(linha)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            for n, t in (("btnX", "X"), ("btnY", "Y"), ("btnZ", "Z")):
                _botao_eixo(self, hl, n, t)
            c.widget(linha)
            for n, rot in (("dirX", "X"), ("dirY", "Y"), ("dirZ", "Z")):
                _num_simples(self, n, rot, "", c, casas=3)
        self._chave("chkReversed", "Inverter", c, "inverter")
        self.lay.addWidget(c)
        c = UI.Cartao("Comprimento", "medida")
        self._num("spinLenFwd", "A favor", "mm", c, chave="favor")
        self._chave("chkSymmetric", "Simétrica", c, "simetrica")
        if not e["chk"][1]:
            self._num("spinLenRev", "Em sentido oposto", "mm", c, chave="oposto")
        self._num("spinTaperAngle", "Ângulo de saída", "°", c, chave="saida")
        self.lay.addWidget(c)
        c = UI.Cartao("Resultado", "acabamento")
        self._chave("chkSolid", "Criar sólido (fechar perfis)", c, "solido")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


class PainelRevolucaoPart(_Base):
    """Sólidos → Revolução: formas, eixo (X/Y/Z ou aresta), ângulo, simétrica e sólido."""

    QSS_EXTRA = PainelVistas.QSS_EXTRA

    def estado(self):
        f = self.f
        le = f.w("txtAxisLink", QtWidgets.QLineEdit)
        return {"formas": _estado_arvore(f, "treeWidget"), "eixo": le.text() if le else "",
                "nums": tuple(f.numero(n) for n in ("xPos", "yPos", "zPos", "xDir", "yDir", "zDir", "angle")),
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("checkSymmetric", "checkSolid"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        _formas_cartao(self, "treeWidget")
        c = UI.Cartao("Eixo", "fixacao")
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for n, t in (("btnX", "Eixo X"), ("btnY", "Eixo Y"), ("btnZ", "Eixo Z")):
            _botao_eixo(self, hl, n, t)
        c.widget(linha)
        sl = f.w("selectLine", QtWidgets.QAbstractButton)
        if sl is not None:
            b = QtWidgets.QPushButton(e["eixo"] or "Escolher aresta na vista")
            b.clicked.connect(lambda _=False, sl=sl: (sl.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.linha("Ou uma aresta", b)
            self.campos["aresta"] = b
        for n, rot in (("xPos", "Centro X"), ("yPos", "Centro Y"), ("zPos", "Centro Z")):
            self._num(n, rot, "mm", c)
        self.lay.addWidget(c)
        c = UI.Cartao("Giro", "angulo")
        self._num("angle", "Ângulo", "°", c, chave="angulo")
        self._chave("checkSymmetric", "Simétrico", c, "simetrico")
        self._chave("checkSolid", "Criar sólido (fechar perfis)", c, "solido")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


PLANOS_ESPELHO = {"XY-plane": "Plano XY", "XZ-plane": "Plano XZ", "YZ-plane": "Plano YZ",
                  "Use selected reference": "A referência escolhida"}


class PainelEspelharPart(_Base):
    """Sólidos → Espelhar: formas, plano (XY/XZ/YZ ou uma face) e ponto por onde passa."""

    def estado(self):
        f = self.f
        le = f.w("referenceLineEdit", QtWidgets.QLineEdit)
        return {"formas": _estado_arvore(f, "shapes"), "plano": f.indice("comboBox"),
                "ref": le.text() if le else "", "base": tuple(f.numero(n) for n in ("baseX", "baseY", "baseZ"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        _formas_cartao(self, "shapes")
        c = UI.Cartao("Plano de espelho", "simetrica")
        cb = f.espelho("comboBox", PLANOS_ESPELHO, largura=240)
        cb.activated.connect(lambda _i: QtCore.QTimer.singleShot(0, self.montar))
        c.linha("Espelhar em", cb)
        self.campos["plano"] = cb
        sb = f.w("selectButton", QtWidgets.QAbstractButton)
        if sb is not None:
            b = QtWidgets.QPushButton(e["ref"] or "Escolher face ou plano na vista")
            b.clicked.connect(lambda _=False, sb=sb: (sb.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.linha("Referência", b)
            self.campos["ref"] = b
        self.lay.addWidget(c)
        c = UI.Cartao("O plano passa por", "fixacao")
        for n, rot in (("baseX", "X"), ("baseY", "Y"), ("baseZ", "Z")):
            self._num(n, rot, "mm", c)
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


class PainelEscalaPart(_Base):
    """Sólidos → Escala: formas e fator (o mesmo nos três eixos ou um por eixo)."""

    def estado(self):
        f = self.f
        vals = []
        for n in ("dsbUniformScale", "dsbXScale", "dsbYScale", "dsbZScale"):
            w = f.w(n, QtWidgets.QDoubleSpinBox)
            vals.append(round(w.value(), 6) if w else None)
        return {"formas": _estado_arvore(f, "treeWidget"), "uniforme": _radio(self, "rbUniform"), "vals": tuple(vals)}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        _formas_cartao(self, "treeWidget")
        c = UI.Cartao("Fator de escala", "medida")
        seg = UI.Segmentado([("rbUniform", "Igual nos 3 eixos", "medida"), ("rbNonUniform", "Um por eixo", "padrao")],
                            "rbUniform" if e["uniforme"] else "rbNonUniform", colunas=2)

        def modo(k):
            r = f.w(k, QtWidgets.QRadioButton)
            if r is not None:
                r.setChecked(True)
            QtCore.QTimer.singleShot(0, self.montar)
        seg.mudou.connect(modo)
        c.widget(seg)
        self.campos["modo"] = seg
        if e["uniforme"]:
            _num_simples(self, "dsbUniformScale", "Fator", "", c, casas=4, chave="fator")
        else:
            for n, rot in (("dsbXScale", "Em X"), ("dsbYScale", "Em Y"), ("dsbZScale", "Em Z")):
                _num_simples(self, n, rot, "", c, casas=4)
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


class PainelArestasPart(_Base):
    """Sólidos → Arredondar / Chanfrar arestas: forma, arestas marcadas (na vista ou todas), tipo e medida."""

    QSS_EXTRA = PainelVistas.QSS_EXTRA

    def _chanfro(self):
        lb = self.f.w("labelRadius", QtWidgets.QLabel)
        gb = self.f.w("parameterName", QtWidgets.QGroupBox)
        txt = ((lb.text() if lb else "") + " " + (gb.title() if gb else "")).lower()
        return any(k in txt for k in ("length", "chanfro", "chamfer", "compr"))

    def _marcadas(self):
        tv = self.f.w("treeView", QtWidgets.QTreeView)
        m = tv.model() if tv is not None else None
        if m is None:
            return []
        out = []
        for r in range(m.rowCount()):
            ix = m.index(r, 0)
            if m.data(ix, QtCore.Qt.CheckStateRole) in (QtCore.Qt.Checked, 2, QtCore.Qt.CheckState.Checked):
                out.append(str(m.data(ix, QtCore.Qt.DisplayRole)))
        return out

    def estado(self):
        f = self.f
        return {"forma": f.indice("shapeObject"), "marcadas": tuple(self._marcadas()),
                "faces": _radio(self, "selectFaces"), "tipo": f.indice("filletType"),
                "r": (f.numero("filletStartRadius"), f.numero("filletEndRadius"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        chanfro = self._chanfro()
        c = UI.Cartao("Forma", "solido")
        cb = QtWidgets.QComboBox()
        cb.setObjectName("PrumoLista")
        cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(12)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        fc = f.combo("shapeObject")
        for i in range(fc.count() if fc else 0):
            cb.addItem(fc.itemText(i))
        cb.setCurrentIndex(e["forma"])
        cb.activated.connect(lambda i: (_ativar(f.combo("shapeObject"), i), QtCore.QTimer.singleShot(80, self.montar)))
        c.widget(cb)
        self.campos["forma"] = cb
        self.lay.addWidget(c)

        c = UI.Cartao("Arestas", "selecao")
        n = len(e["marcadas"])
        lb = QtWidgets.QLabel(("{} marcada{}: ".format(n, "s" if n != 1 else "") + ", ".join(e["marcadas"][:6]) +
                               ("…" if n > 6 else "")) if n else "Nenhuma aresta marcada: clique nelas na vista")
        lb.setObjectName("PrumoSub")
        lb.setWordWrap(True)
        c.widget(lb)
        self.campos["resumo"] = lb
        seg = UI.Segmentado([("selectEdges", "Clicar em arestas", "selecao"), ("selectFaces", "Clicar em faces", "solido")],
                            "selectFaces" if e["faces"] else "selectEdges", colunas=2)

        def modo(k):
            r = f.w(k, QtWidgets.QRadioButton)
            if r is not None:
                r.setChecked(True)
            QtCore.QTimer.singleShot(0, self.montar)
        seg.mudou.connect(modo)
        c.widget(seg)
        self.campos["modo"] = seg
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        for nome_fc, txt in (("selectAllButton", "Todas"), ("selectNoneButton", "Nenhuma")):
            fb = f.w(nome_fc, QtWidgets.QAbstractButton)
            if fb is None:
                continue
            b = QtWidgets.QPushButton(txt)
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(80, self.montar)))
            hl.addWidget(b)
            self.campos[nome_fc] = b
        hl.addStretch(1)
        c.widget(linha)
        self.lay.addWidget(c)

        c = UI.Cartao("Chanfro" if chanfro else "Arredondamento", "chanfro" if chanfro else "raio")
        tipos = [("0", "Constante", "medida"), ("1", "Variável", "angulo")]
        seg = UI.Segmentado(tipos, str(max(0, e["tipo"])), colunas=2)
        seg.mudou.connect(lambda k: (_ativar(f.combo("filletType"), int(k)), QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["tipo"] = seg
        medida = "Comprimento" if chanfro else "Raio"
        self._num("filletStartRadius", medida + (" no início" if e["tipo"] == 1 else ""), "mm", c, minimo=0.0,
                  chave="r1")
        if e["tipo"] == 1:
            self._num("filletEndRadius", medida + " no fim", "mm", c, minimo=0.0, chave="r2")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


# ----------------------------------------------------------------------------------- Montagem
MODOS_OFFSET = [("0", "Casca", "solido"), ("1", "Tubo", "atraves"), ("2", "Frente e verso", "dois_lados")]
JUNCOES_PART = [("0", "Arredondada", "raio"), ("1", "Tangente", "angulo"), ("2", "Canto vivo", "chanfro")]


class PainelOffsetPart(_Base):
    """Sólidos → Deslocamento 3D/2D e Espessura (o mesmo formulário do FreeCAD; a espessura tem faces)."""

    def _espessura(self):
        fb = self.f.w("facesButton", QtWidgets.QAbstractButton)
        return fb is not None and fb.isVisibleTo(self.quadro)

    def estado(self):
        f = self.f
        lb = f.w("labelFaces", QtWidgets.QLabel)
        fb = f.w("facesButton", QtWidgets.QAbstractButton)
        return {"val": f.numero("spinOffset"), "modo": f.indice("modeType"), "junta": f.indice("joinType"),
                "n_modos": f.combo("modeType").count() if f.combo("modeType") else 0,
                "faces": lb.text() if lb else "", "esc": bool(fb and fb.isChecked()),
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("intersection", "selfIntersection", "fillOffset", "updateView"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        esp = self._espessura()
        if esp:
            c = UI.Cartao("Faces abertas", "selecao")
            lb = QtWidgets.QLabel(e["faces"] or "Escolha na vista as faces que ficam abertas.")
            lb.setWordWrap(True)
            lb.setObjectName("PrumoSub")
            c.widget(lb)
            fb = f.w("facesButton", QtWidgets.QAbstractButton)
            b = QtWidgets.QPushButton("Concluir a escolha" if e["esc"] else "Escolher faces na vista")
            if e["esc"]:
                b.setObjectName("PrumoPrimario")
            b.setEnabled(fb.isEnabled())
            b.clicked.connect(lambda _=False, fb=fb: (fb.click(), QtCore.QTimer.singleShot(50, self.montar)))
            c.widget(b)
            self.campos["faces"] = b
            self.lay.addWidget(c)
        c = UI.Cartao("Espessura" if esp else "Deslocamento", "medida")
        self._num("spinOffset", "Espessura" if esp else "Distância", "mm", c, chave="valor")
        dica = QtWidgets.QLabel("Valor negativo: para dentro." if esp else "Valor negativo: para dentro da forma.")
        dica.setObjectName("PrumoSub")
        c.widget(dica)
        self.lay.addWidget(c)
        c = UI.Cartao("Como é feito", "acabamento")
        modos = MODOS_OFFSET[:max(1, e["n_modos"])] if e["n_modos"] else MODOS_OFFSET
        if len(modos) > 1:
            seg = UI.Segmentado(modos, str(max(0, e["modo"])), colunas=len(modos))
            seg.mudou.connect(lambda k: (_ativar(self.f.combo("modeType"), int(k)),
                                         QtCore.QTimer.singleShot(0, self.montar)))
            c.widget(seg)
            self.campos["modo"] = seg
        sub = QtWidgets.QLabel("Cantos")
        sub.setObjectName("PrumoSub")
        c.widget(sub)
        seg = UI.Segmentado(JUNCOES_PART, str(max(0, e["junta"])), colunas=3)
        seg.mudou.connect(lambda k: (_ativar(self.f.combo("joinType"), int(k)),
                                     QtCore.QTimer.singleShot(0, self.montar)))
        c.widget(seg)
        self.campos["junta"] = seg
        self._chave("intersection", "Permitir interseções", c, "inter")
        self._chave("selfIntersection", "Permitir autointerseção", c, "auto")
        self._chave("fillOffset", "Preencher (sólido entre a forma e o deslocamento)", c, "preencher")
        self.lay.addWidget(c)
        c = UI.Cartao("Vista", "olho")
        self._chave("updateView", "Atualizar a vista enquanto edita", c, "atualizar")
        self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        return "Clique nas faces na vista; depois, \"Concluir a escolha\"." if self.estado()["esc"] else ""

    def precisa_do_formulario(self):
        return False


def _seletor_acao(painel, titulo, icone, vazio):
    """Cartões para o Gui::ActionSelector do FreeCAD: o que está disponível e o que entra, em ordem."""
    f = painel.f
    disp = f.w("availableTreeWidget", QtWidgets.QTreeWidget)
    sel = f.w("selectedTreeWidget", QtWidgets.QTreeWidget)
    if disp is None or sel is None:
        return

    def acao(arvore, it, botao):
        arvore.setCurrentItem(it)
        b = f.w(botao, QtWidgets.QAbstractButton)
        if b is not None:
            b.setEnabled(True)
            b.click()
        QtCore.QTimer.singleShot(0, painel.montar)

    c = UI.Cartao(titulo, icone)
    if sel.topLevelItemCount() == 0:
        lb = QtWidgets.QLabel(vazio)
        lb.setObjectName("PrumoSub")
        lb.setWordWrap(True)
        c.widget(lb)
    for i in range(sel.topLevelItemCount()):
        it = sel.topLevelItem(i)
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for txt, dica, botao, pode in (("↑", "Subir", "upButton", i > 0),
                                       ("↓", "Descer", "downButton", i < sel.topLevelItemCount() - 1),
                                       ("✕", "Tirar", "removeButton", True)):
            tb = QtWidgets.QToolButton()
            tb.setText(txt)
            tb.setToolTip(dica)
            tb.setAccessibleName(dica)
            tb.setEnabled(pode)
            tb.clicked.connect(lambda _=False, it=it, botao=botao: acao(sel, it, botao))
            hl.addWidget(tb)
            painel.campos["sel%d_%s" % (i, botao)] = tb
        c.linha("{}. {}".format(i + 1, it.text(0)), linha)
    painel.lay.addWidget(c)
    c = UI.Cartao("Disponíveis", "solido")
    if disp.topLevelItemCount() == 0:
        lb = QtWidgets.QLabel("Nada mais para acrescentar.")
        lb.setObjectName("PrumoSub")
        c.widget(lb)
    for i in range(min(disp.topLevelItemCount(), 15)):
        it = disp.topLevelItem(i)
        b = QtWidgets.QPushButton("Usar")
        b.clicked.connect(lambda _=False, it=it: acao(disp, it, "addButton"))
        c.linha(it.text(0), b)
        painel.campos["disp%d" % i] = b
    painel.lay.addWidget(c)


def _estado_seletor(f):
    out = []
    for n in ("availableTreeWidget", "selectedTreeWidget"):
        t = f.w(n, QtWidgets.QTreeWidget)
        out.append(tuple(t.topLevelItem(i).text(0) for i in range(t.topLevelItemCount())) if t else ())
    return tuple(out)


class PainelLoftPart(_Base):
    """Sólidos → Transição (loft): perfis em ordem, sólido, superfície regrada e fechada."""

    def estado(self):
        f = self.f
        return {"lst": _estado_seletor(f),
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("checkSolid", "checkRuledSurface", "checkClosed"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        _seletor_acao(self, "Perfis, na ordem", "padrao", "Escolha pelo menos dois perfis em \"Disponíveis\".")
        c = UI.Cartao("Resultado", "acabamento")
        self._chave("checkSolid", "Criar sólido", c, "solido")
        self._chave("checkRuledSurface", "Superfície regrada (faces retas entre perfis)", c, "regrada")
        self._chave("checkClosed", "Fechar (último perfil liga no primeiro)", c, "fechada")
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


class PainelVarreduraPart(_Base):
    """Sólidos → Varredura: perfis em ordem, caminho (arestas na vista), sólido e Frenet."""

    def estado(self):
        f = self.f
        bp = f.w("buttonPath", QtWidgets.QAbstractButton)
        lb = f.w("labelPath", QtWidgets.QLabel)
        return {"lst": _estado_seletor(f), "esc": bool(bp and bp.isChecked()), "cam": lb.text() if lb else "",
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("checkSolid", "checkFrenet"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        _seletor_acao(self, "Perfis, na ordem", "padrao", "Escolha o perfil em \"Disponíveis\".")
        c = UI.Cartao("Caminho", "seta_cima")
        lb = QtWidgets.QLabel(e["cam"] or "Clique em \"Escolher caminho\", marque as arestas na vista e conclua.")
        lb.setWordWrap(True)
        lb.setObjectName("PrumoSub")
        c.widget(lb)
        bp = f.w("buttonPath", QtWidgets.QAbstractButton)
        if bp is not None:
            b = QtWidgets.QPushButton("Concluir o caminho" if e["esc"] else "Escolher caminho na vista")
            if e["esc"]:
                b.setObjectName("PrumoPrimario")
            b.clicked.connect(lambda _=False, bp=bp: (bp.click(), QtCore.QTimer.singleShot(50, self.montar)))
            c.widget(b)
            self.campos["caminho"] = b
        self.lay.addWidget(c)
        c = UI.Cartao("Resultado", "acabamento")
        self._chave("checkSolid", "Criar sólido", c, "solido")
        self._chave("checkFrenet", "Frenet (seção acompanha a torção do caminho)", c, "frenet")
        self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        return "Clique nas arestas do caminho na vista; depois, \"Concluir o caminho\"." if self.estado()["esc"] else ""

    def precisa_do_formulario(self):
        return False


class PainelInserirPecas(_Base):
    """Montagem → Inserir componente: procurar, peças de cada documento aberto com "Inserir" e as opções."""

    TITULO = "Inserir componente"

    def _itens(self):
        """[(nível, item, é peça)] da lista do FreeCAD, na ordem, sem os escondidos pelo filtro."""
        tree = self.f.w("partList", QtWidgets.QTreeWidget)
        out = []
        if tree is None:
            return out

        def andar(it, nivel):
            if it.isHidden():
                return
            out.append((nivel, it, it.data(0, QtCore.Qt.UserRole) is not None))
            for i in range(it.childCount()):
                andar(it.child(i), nivel + 1)
        for i in range(tree.topLevelItemCount()):
            andar(tree.topLevelItem(i), 0)
        return out

    def estado(self):
        f = self.f
        le = f.w("filterPartList", QtWidgets.QLineEdit)
        return {"itens": tuple((n, it.text(0), peca) for n, it, peca in self._itens()),
                "filtro": le.text() if le else "",
                "chk": tuple(bool(f.check(n).isChecked()) if f.check(n) else False
                             for n in ("CheckBox_ShowOnlyParts", "CheckBox_RigidSubAsm"))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Procurar", "selecao")
        fl = f.w("filterPartList", QtWidgets.QLineEdit)
        if fl is not None:
            le = QtWidgets.QLineEdit(fl.text())
            le.setObjectName("PrumoTexto")
            le.setPlaceholderText("Parte do nome…")
            le.setClearButtonEnabled(True)
            le.textChanged.connect(lambda t, fl=fl: (fl.setText(t), setattr(self, "_digitando", True),
                                                     QtCore.QTimer.singleShot(250, self.atualizar)))
            c.widget(le)
            self.campos["filtro"] = le
            if getattr(self, "_digitando", False):     # a lista refeita não tira o cursor de quem digita
                le.setFocus()
                le.setCursorPosition(len(le.text()))
        ab = f.w("openFileButton", QtWidgets.QAbstractButton)
        if ab is not None:
            b = QtWidgets.QPushButton("Abrir outro arquivo…")
            b.clicked.connect(lambda _=False, ab=ab: (ab.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.widget(b)
            self.campos["abrir"] = b
        self.lay.addWidget(c)
        tree = f.w("partList", QtWidgets.QTreeWidget)
        cartao = None
        n_pecas = 0
        for nivel, it, peca in self._itens():
            if nivel == 0:
                if cartao is not None:
                    self.lay.addWidget(cartao)
                cartao = UI.Cartao(it.text(0), "corpo")
                continue
            if cartao is None:
                continue
            m = re.search(r"\s*:\s*(\d+) inserted$", it.text(0))
            nome = it.text(0)[:m.start()] if m else it.text(0)
            rot = ("    " * (nivel - 1)) + nome
            if not peca:
                lb = QtWidgets.QLabel(rot)
                lb.setObjectName("PrumoSub")
                cartao.widget(lb)
                continue
            b = QtWidgets.QPushButton("Inserir" + (" ({})".format(m.group(1)) if m else ""))
            b.setToolTip("Insere uma cópia ligada (link) desta peça na montagem" +
                         ("; já inserida {} vez(es)".format(m.group(1)) if m else ""))
            b.clicked.connect(lambda _=False, it=it: (tree.itemClicked.emit(it, 0),
                                                      QtCore.QTimer.singleShot(80, self.montar)))
            cartao.linha(rot, b)
            self.campos["peca%d" % n_pecas] = b
            self.campos["nome%d" % n_pecas] = nome
            n_pecas += 1
        if cartao is not None:
            self.lay.addWidget(cartao)
        if n_pecas == 0:
            c = UI.Cartao("Peças", "corpo")
            lb = QtWidgets.QLabel("Nenhuma peça encontrada. Abra o arquivo da peça ou crie uma no documento.")
            lb.setWordWrap(True)
            lb.setObjectName("PrumoSub")
            c.widget(lb)
            self.lay.addWidget(c)
        c = UI.Cartao("Opções", "acabamento")
        self._chave("CheckBox_ShowOnlyParts", "Mostrar só peças (Part), sem sólidos soltos", c, "so_pecas")
        self._chave("CheckBox_RigidSubAsm", "Subconjuntos entram rígidos", c, "rigido")
        self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        return "Cada clique em \"Inserir\" põe mais uma; a primeira peça pode ficar fixa (aterrada)."

    def precisa_do_formulario(self):
        return False


TIPOS_JUNTA = [("Fixed", "Fixa"), ("Revolute", "Rotação"), ("Cylindrical", "Cilíndrica"), ("Slider", "Deslizante"),
               ("Ball", "Esférica"), ("Distance", "Distância"), ("Parallel", "Paralela"),
               ("Perpendicular", "Perpendicular"), ("Angle", "Ângulo"), ("RackPinion", "Cremalheira"),
               ("Screw", "Parafuso"), ("Gears", "Engrenagens"), ("Belt", "Correia")]
DICA_JUNTA = {"Fixed": "As duas peças ficam presas uma na outra", "Revolute": "Gira em torno de um eixo",
              "Cylindrical": "Gira e desliza no mesmo eixo", "Slider": "Desliza ao longo de uma direção",
              "Ball": "Gira em qualquer direção em torno de um ponto", "Distance": "Mantém uma distância",
              "Parallel": "Mantém as direções paralelas", "Perpendicular": "Mantém as direções a 90°",
              "Angle": "Mantém um ângulo", "RackPinion": "Engrenagem com cremalheira",
              "Screw": "Gira e avança pelo passo da rosca", "Gears": "Duas engrenagens",
              "Belt": "Duas polias com correia"}
ISOLAR = ["Transparentes", "Só arestas", "Escondidas", "Desativado"]


class PainelJunta(_Base):
    """Montagem → criar ou editar junta: tipo, o que foi escolhido, medidas, inverter, limites e como as
    outras peças aparecem enquanto escolhe."""

    QSS_EXTRA = PainelVistas.QSS_EXTRA
    TITULO = "Junta"
    MEDIDAS = (("angleSpinbox", "angleLabel", "°"), ("distanceSpinbox", "distanceLabel", "mm"),
               ("distanceSpinbox2", "distanceLabel2", "mm"), ("offsetSpinbox", "offsetLabel", "mm"),
               ("rotationSpinbox", "rotationLabel", "°"))
    LIMITES = (("limitCheckbox1", "limitLenMinSpinbox", "Distância mínima", "mm"),
               ("limitCheckbox2", "limitLenMaxSpinbox", "Distância máxima", "mm"),
               ("limitCheckbox3", "limitRotMinSpinbox", "Ângulo mínimo", "°"),
               ("limitCheckbox4", "limitRotMaxSpinbox", "Ângulo máximo", "°"))

    def estado(self):
        f = self.f
        lw = f.w("featureList", QtWidgets.QListWidget)
        return {"tipo": f.indice("jointType"), "tipo_vis": f.visivel("jointType"),
                "itens": tuple(lw.item(i).text() for i in range(lw.count())) if lw else (),
                "vis": tuple(f.visivel(n) for n, _l, _u in self.MEDIDAS),
                "nums": tuple(f.numero(n) for n, _l, _u in self.MEDIDAS),
                "lim": tuple((f.visivel(c), bool(f.check(c).isChecked()) if f.check(c) else False)
                             for c, _s, _r, _u in self.LIMITES),
                "isolar": f.indice("isolateType")}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        restricao = None
        try:
            import JointObject
            restricao = getattr(JointObject.activeTask, "prumo_restricao", None)
        except Exception:
            restricao = None
        if restricao:
            # Tangente / Coincidente do Prumo: por baixo é a junta Distância; mostra o nome pedido, não a grade
            import PrumoMontagem
            nome, dica = PrumoMontagem.JUNTAS[restricao]
            c = UI.Cartao(nome, "vinculo")
            txt = dica.split(": ", 1)[-1]
            lb = QtWidgets.QLabel(txt[:1].upper() + txt[1:])
            lb.setObjectName("PrumoSub")
            lb.setWordWrap(True)
            c.widget(lb)
            self.campos["restricao"] = lb
            self.lay.addWidget(c)
        elif e["tipo_vis"]:
            c = UI.Cartao("Tipo de junta", "vinculo")
            grade = QtWidgets.QWidget()
            g = QtWidgets.QGridLayout(grade)
            g.setContentsMargins(0, 0, 0, 0)
            g.setSpacing(4)
            for col in range(3):
                g.setColumnStretch(col, 1)
            fc = f.combo("jointType")
            for i, (chave, nome) in enumerate(TIPOS_JUNTA):
                if fc is None or i >= fc.count():
                    break
                b = QtWidgets.QToolButton()
                b.setObjectName("PrumoVista")
                b.setCheckable(True)
                b.setChecked(i == e["tipo"])
                b.setText(nome)
                b.setToolTip(DICA_JUNTA.get(chave, nome))
                b.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
                b.setMinimumHeight(30)
                b.clicked.connect(lambda _=False, i=i: self._indice("jointType", i))
                g.addWidget(b, i // 3, i % 3)
                self.campos["tipo%d" % i] = b
            c.widget(grade)
            self.lay.addWidget(c)

        c = UI.Cartao("Escolhido na vista", "selecao")
        n = len(e["itens"])
        lb = QtWidgets.QLabel(("\n".join(e["itens"][:4]) + ("\n…" if n > 4 else "")) if n else
                              "Nada ainda: clique em uma face, aresta ou ponto de cada peça.")
        lb.setObjectName("PrumoSub")
        lb.setWordWrap(True)
        c.widget(lb)
        self.campos["escolhido"] = lb
        iso = f.combo("isolateType")
        if iso is not None and iso.isVisibleTo(self.quadro):
            cb = QtWidgets.QComboBox()
            cb.setObjectName("PrumoLista")
            for i in range(iso.count()):
                cb.addItem(ISOLAR[i] if i < len(ISOLAR) else iso.itemText(i))
            cb.setCurrentIndex(e["isolar"])
            cb.activated.connect(lambda i, iso=iso: iso.setCurrentIndex(i))
            c.linha("Outras peças enquanto escolhe", cb)
            self.campos["isolar"] = cb
        self.lay.addWidget(c)

        if any(e["vis"]) or f.visivel("PushButtonReverse"):
            c = UI.Cartao("Medidas", "medida")
            for nome, rot, unid in self.MEDIDAS:
                lab = f.w(rot, QtWidgets.QLabel)
                self._num(nome, (lab.text().rstrip(":") if lab is not None else nome), unid, c)
            rv = f.w("PushButtonReverse", QtWidgets.QAbstractButton)
            if rv is not None and rv.isVisibleTo(self.quadro):
                b = QtWidgets.QPushButton("Inverter o sentido")
                b.clicked.connect(lambda _=False, rv=rv: rv.click())
                c.widget(b)
                self.campos["inverter"] = b
            self.lay.addWidget(c)

        if any(vis for vis, _on in e["lim"]):
            c = UI.Cartao("Limites", "seta_cima")
            for (cx, sb, rot, unid), (vis, on) in zip(self.LIMITES, e["lim"]):
                if not vis:
                    continue
                cb = f.check(cx)
                sw = UI.Interruptor(on)
                sw.toggled.connect(lambda v, cb=cb: (cb.setChecked(bool(v)), QtCore.QTimer.singleShot(50, self.montar)))
                c.linha(rot, sw)
                self.campos[cx] = sw
                if on:
                    self._num(sb, "  valor", unid, c)
            self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


# ----------------------------------------------------------------------------------- Simulação (FEM)
DICA_ESCOLHA.update({
    "btnAdd": "Clique nas faces (ou arestas) na vista; depois, \"Concluir\".",
    "btnRemove": "Clique nas que quer tirar; depois, \"Concluir\".",
})


class _PainelRestricaoFem(_Escolhas):
    """Começo comum das restrições do FEM: o que foi escolhido na vista, com Adicionar / Tirar."""

    BOTOES = ("btnAdd", "btnRemove")
    LISTA = "lw_references"
    TITULO_ESCOLHA = "Onde"
    VAZIO = "Nada escolhido: clique em Adicionar e depois nas faces"

    def _cartao_escolha(self):
        self._selecao(self.TITULO_ESCOLHA, "selecao", list(self._lista(self.LISTA)), self.VAZIO,
                      [("btnAdd", "Adicionar", "Concluir"), ("btnRemove", "Tirar", "Concluir")], "refs")

    def estado(self):
        return {"refs": self._lista(self.LISTA), "esc": self._escolhendo(*self.BOTOES)}


class PainelFixacaoFem(_PainelRestricaoFem):
    """Simulação → Fixação: as faces presas."""

    TITULO = "Fixação"
    TITULO_ESCOLHA = "Faces presas"

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._cartao_escolha()
        self._fim()


class PainelForcaFem(_PainelRestricaoFem):
    """Simulação → Força: onde, quanto e para onde."""

    TITULO = "Força"
    LISTA = "listReferences"
    TITULO_ESCOLHA = "Onde a força atua"

    def estado(self):
        f = self.f
        le = f.w("lineDirection", QtWidgets.QLineEdit)
        e = _PainelRestricaoFem.estado(self)
        e.update({"forca": f.numero("spinForce"), "dir": le.text() if le else "",
                  "inv": bool(f.check("checkReverse").isChecked()) if f.check("checkReverse") else False})
        return e

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        self._cartao_escolha()
        c = UI.Cartao("Força", "seta_baixo")
        self._num_un("spinForce", "Valor", "N", c, minimo=0.0, chave="forca")
        bd = f.w("buttonDirection", QtWidgets.QAbstractButton)
        if bd is not None:
            ativo = bool(bd.isCheckable() and bd.isChecked())
            b = QtWidgets.QPushButton("Escolhendo… clique na vista" if ativo else
                                      (e["dir"] or "Normal à face (padrão)"))
            b.setToolTip("Clique e escolha uma aresta, face ou eixo que dá a direção da força")
            if ativo:
                b.setObjectName("PrumoPrimario")
            b.clicked.connect(lambda _=False, bd=bd: (bd.click(), QtCore.QTimer.singleShot(80, self.montar)))
            c.linha("Direção", b)
            self.campos["direcao"] = b
        self._chave("checkReverse", "Inverter o sentido", c, "inverter")
        self.lay.addWidget(c)
        self._fim()


class PainelPressaoFem(_PainelRestricaoFem):
    """Simulação → Pressão: faces, valor e sentido."""

    TITULO = "Pressão"
    TITULO_ESCOLHA = "Faces com pressão"

    def estado(self):
        f = self.f
        e = _PainelRestricaoFem.estado(self)
        e.update({"p": f.numero("if_pressure"),
                  "inv": bool(f.check("checkBoxReverse").isChecked()) if f.check("checkBoxReverse") else False})
        return e

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._cartao_escolha()
        c = UI.Cartao("Pressão", "seta_baixo")
        self._num_un("if_pressure", "Valor", "MPa", c, minimo=0.0, casas=4, chave="pressao")
        self._chave("checkBoxReverse", "Inverter (puxando a face)", c, "inverter")
        self.lay.addWidget(c)
        self._fim()


class PainelOndeVale(_Base):
    """Simulação → quadro "Onde vale" (seletor de geometria das tarefas do FEM feitas em Python: material,
    espessura de casca, seção de viga…): itens escolhidos, Adicionar na vista, tirar um a um."""

    TIPOS_PT = {"Solid": "sólidos", "Face": "faces", "Edge": "arestas", "Vertex": "vértices"}

    def _sel(self):
        return self.quadro.findChild(QtWidgets.QWidget, "PrumoGeoSel")

    def estado(self):
        w = self._sel()
        if w is None:
            return {"ok": False}
        return {"ok": True, "itens": tuple(w.get_allitems_text()), "esc": w.sel_server is not None,
                "solido": bool(getattr(w, "selection_mode_solid", False))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        w = self._sel()
        if w is None:
            self._fim()
            return
        tipos = ", ".join(self.TIPOS_PT.get(t, t) for t in w.sel_elem_types)
        c = UI.Cartao("Onde vale", "selecao")
        if not e["itens"]:
            lb = QtWidgets.QLabel("Vale para tudo que sobrar (nenhum item escolhido)." if w.showHintEmptyList
                                  else "Nada escolhido ainda.")
            lb.setWordWrap(True)
            lb.setObjectName("PrumoSub")
            c.widget(lb)
        for i, txt in enumerate(e["itens"][:20]):
            tb = QtWidgets.QToolButton()
            tb.setText("✕")
            tb.setToolTip("Tirar")
            tb.setAccessibleName("Tirar " + txt)
            tb.clicked.connect(lambda _=False, i=i: self._tirar_item(i))
            c.linha(txt.replace(":", " · "), tb)
            self.campos["tirar%d" % i] = tb
        b = QtWidgets.QPushButton("Parar de escolher" if e["esc"] else "Adicionar na vista")
        if e["esc"]:
            b.setObjectName("PrumoPrimario")
        b.setToolTip("Pode escolher: " + tipos)
        b.clicked.connect(self._alternar)
        c.widget(b)
        self.campos["adicionar"] = b
        if "Solid" in w.sel_elem_types and len(w.sel_elem_types) > 1:
            seg = UI.Segmentado([("std", "Faces e arestas", "selecao"), ("sol", "Sólido inteiro", "solido")],
                                "sol" if e["solido"] else "std", colunas=2)
            seg.mudou.connect(lambda k: ((w.rb_solid if k == "sol" else w.rb_standard).setChecked(True),
                                         QtCore.QTimer.singleShot(0, self.montar)))
            c.widget(seg)
            self.campos["modo"] = seg
        self.lay.addWidget(c)
        self._fim()

    def _tirar_item(self, i):
        w = self._sel()
        if w is None or i >= w.list_References.count():
            return
        w.list_References.setCurrentRow(i)
        w.remove_selected_reference()
        QtCore.QTimer.singleShot(0, self.montar)

    def _alternar(self):
        w = self._sel()
        if w is None:
            return
        if w.sel_server is not None:
            try:
                FreeCADGui.Selection.removeObserver(w.sel_server)
            except Exception:
                pass
            w.sel_server = None
            w.setback_listobj_visibility()
        else:
            w.pushButton_Add.click()
        QtCore.QTimer.singleShot(0, self.montar)

    def dica_extra(self):
        e = self.estado()
        return "Clique na vista nos itens que entram; depois, \"Parar de escolher\"." if e.get("esc") else ""

    def precisa_do_formulario(self):
        return False


EIXOS_DESLOC = [("DisplacementXGB", "spinxDisplacement", "Deslocamento em X", "mm"),
                ("DisplacementYGB", "spinyDisplacement", "Deslocamento em Y", "mm"),
                ("DisplacementZGB", "spinzDisplacement", "Deslocamento em Z", "mm"),
                ("RotationXGB", "spinxRotation", "Giro em torno de X", "°"),
                ("RotationYGB", "spinyRotation", "Giro em torno de Y", "°"),
                ("RotationZGB", "spinzRotation", "Giro em torno de Z", "°")]


class PainelDeslocamentoFem(_PainelRestricaoFem):
    """Simulação → Deslocamento imposto: faces e, por eixo, livre ou com valor (0 = travado nesse eixo)."""

    TITULO = "Deslocamento imposto"
    TITULO_ESCOLHA = "Faces com deslocamento imposto"

    def estado(self):
        f = self.f
        e = _PainelRestricaoFem.estado(self)
        eixos = []
        for gb, sb, _r, _u in EIXOS_DESLOC:
            g = f.w(gb, QtWidgets.QGroupBox)
            eixos.append((bool(g.isChecked()) if g else False, f.numero(sb)))
        e["eixos"] = tuple(eixos)
        return e

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        self._cartao_escolha()
        for titulo, icone, faixa in (("Deslocamento", "seta_cima", EIXOS_DESLOC[:3]),
                                     ("Giro (cascas e vigas)", "angulo", EIXOS_DESLOC[3:])):
            c = UI.Cartao(titulo, icone)
            for gb, sb, rot, unid in faixa:
                g = f.w(gb, QtWidgets.QGroupBox)
                if g is None:
                    continue
                sw = UI.Interruptor(g.isChecked())
                sw.setToolTip("Ligado: o valor abaixo é imposto (0 trava). Desligado: livre nesse eixo.")
                sw.toggled.connect(lambda on, g=g: (g.setChecked(bool(on)), QtCore.QTimer.singleShot(0, self.montar)))
                c.linha(rot, sw)
                self.campos[gb] = sw
                if g.isChecked():
                    self._num(sb, "  valor", unid, c, chave=sb)
            self.lay.addWidget(c)
        dica = QtWidgets.QLabel("Desligado = livre. Ligado com 0 = travado nesse eixo.")
        dica.setObjectName("PrumoSub")
        dica.setWordWrap(True)
        self.lay.addWidget(dica)
        self._fim()


RIGIDEZ_MOLA = {"Normal Stiffness": "Rigidez normal", "Tangential Stiffness": "Rigidez tangencial"}


class PainelMolaFem(_PainelRestricaoFem):
    """Simulação → Mola (apoio elástico): faces e rigidez normal e tangencial."""

    TITULO = "Mola"
    TITULO_ESCOLHA = "Faces apoiadas na mola"

    def estado(self):
        f = self.f
        e = _PainelRestricaoFem.estado(self)
        e.update({"n": f.numero("qsb_norm"), "t": f.numero("qsb_tan")})
        return e

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        self._cartao_escolha()
        c = UI.Cartao("Rigidez", "medida")
        self._num_un("qsb_norm", "Normal à face", "N/mm", c, minimo=0.0, casas=3, chave="normal")
        self._num_un("qsb_tan", "Tangente à face", "N/mm", c, minimo=0.0, casas=3, chave="tangente")
        self.lay.addWidget(c)
        self._fim()


def _br(v, casas=None):
    """Número no formato brasileiro, sem casas sobrando (7900 → '7.900'; 0,3 → '0,3')."""
    if casas is None:
        casas = 0 if abs(v) >= 100 else 2
    t = "{:,.{c}f}".format(v, c=casas).replace(",", "X").replace(".", ",").replace("X", ".")
    if "," in t:
        t = t.rstrip("0").rstrip(",")
    return t


class PainelMaterialFem(_Base):
    """Simulação → Material: o material escolhido e as propriedades usadas no cálculo. A escolha de outro
    material fica na biblioteca do FreeCAD (formulário completo)."""

    TITULO = "Material"
    texto_completo = "Escolher outro material (biblioteca)"
    CAMPOS = (("qsb_density", "Densidade", "kg/m^3"), ("qsb_young_modulus", "Módulo de elasticidade (E)", "GPa"),
              ("qsb_poisson_ratio", "Coeficiente de Poisson (ν)", ""))

    def _nome(self):
        try:
            vp = FreeCADGui.ActiveDocument.getInEdit()
            obj = vp.Object if vp is not None else None
            return str(obj.Material.get("Name", "")) if obj is not None and hasattr(obj, "Material") else ""
        except Exception:
            return ""

    def estado(self):
        f = self.f
        return {"nome": self._nome(), "nums": tuple(f.numero(n) for n, _r, _u in self.CAMPOS),
                "editar": bool(f.check("chbu_allow_edit").isChecked()) if f.check("chbu_allow_edit") else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Material", "solido")
        c.linha("Escolhido", UI.Chip(e["nome"] or "—"))
        self.lay.addWidget(c)
        c = UI.Cartao("Propriedades usadas no cálculo", "numero")
        for nome, rot, unidade in self.CAMPOS:
            raw = f.numero(nome)
            if raw is None:
                continue
            if not raw:
                texto = "—"
            elif unidade:
                un = FreeCAD.Units.Quantity("1 " + unidade).Unit
                v = FreeCAD.Units.Quantity(raw, un).getValueAs(unidade).Value
                texto = "{} {}".format(_br(v), unidade.replace("^3", "³"))
            else:
                texto = _br(raw, 3)
            ch = UI.Chip(texto)
            c.linha(rot, ch)
            self.campos[nome] = ch
        nota = QtWidgets.QLabel("Para ajustar um valor ou escolher outro material, abra a biblioteca abaixo.")
        nota.setObjectName("PrumoSub")
        nota.setWordWrap(True)
        c.widget(nota)
        self.lay.addWidget(c)
        self._fim()

    def precisa_do_formulario(self):
        return False


DIMENSOES_MALHA = {"From Shape": "Da peça", "3D": "Sólida (3D)", "2D": "Casca (2D)", "1D": "Barras (1D)"}
ORDENS_MALHA = {"1st": "1ª ordem (linear)", "2nd": "2ª ordem (quadrática, mais precisa)"}


class PainelMalhaGmsh(_Base):
    """Simulação → Gerar malha: tipo, tamanhos dos elementos, ordem e a saída do Gmsh."""

    TITULO = "Malha"

    def estado(self):
        f = self.f
        te = f.w("te_output", QtWidgets.QTextEdit)
        return {"dim": f.indice("cb_dimension"), "ordem": f.indice("cb_order"),
                "nums": (f.numero("qsb_max_size"), f.numero("qsb_min_size")),
                "saida": (te.toPlainText()[-400:] if te else "")}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Malha", "padrao")
        cb = f.espelho("cb_dimension", DIMENSOES_MALHA, largura=240)
        cb.activated.connect(lambda i: (_ativar(f.combo("cb_dimension"), i)))
        c.linha("Tipo", cb)
        self.campos["dim"] = cb
        self._num("qsb_max_size", "Tamanho máximo do elemento", "mm", c, minimo=0.0, chave="max")
        self._num("qsb_min_size", "Tamanho mínimo (0 = automático)", "mm", c, minimo=0.0, chave="min")
        cb = f.espelho("cb_order", ORDENS_MALHA, largura=300)
        cb.setMinimumContentsLength(18)
        cb.activated.connect(lambda i: (_ativar(f.combo("cb_order"), i)))
        c.linha("Ordem", cb)
        self.campos["ordem"] = cb
        self.lay.addWidget(c)
        if e["saida"].strip():
            c = UI.Cartao("Saída do Gmsh", "info")
            lb = QtWidgets.QLabel("\n".join(e["saida"].strip().splitlines()[-6:]))
            lb.setObjectName("PrumoSub")
            lb.setWordWrap(True)
            c.widget(lb)
            self.lay.addWidget(c)
        self._fim()

    def dica_extra(self):
        return "\"Aplicar\" gera a malha agora; OK gera e fecha."

    def precisa_do_formulario(self):
        return False


TIPOS_MULTI = [("Add Mirror Transformation", "+ Espelhar"), ("Add Linear Pattern", "+ Padrão linear"),
               ("Add Polar Pattern", "+ Padrão circular"), ("Add Scale Transformation", "+ Escala")]
ACOES_ITEM = [("Edit", "Editar"), ("Delete", "Excluir"), ("Move Up", "Subir"), ("Move Down", "Descer")]


def nome_transformacao(rotulo):
    """'Linear_Pattern001' → 'Padrão linear 001' (rótulos padrão do FreeCAD nas transformações)."""
    import re
    m = re.match(r"^(Mirrored|Linear_?Pattern|Polar_?Pattern|Scaled)(\d*)$", rotulo or "")
    if not m:
        return rotulo
    base = {"Mirrored": "Espelhar", "Scaled": "Escala"}.get(m.group(1))
    if base is None:
        base = "Padrão linear" if m.group(1).startswith("Linear") else "Padrão circular"
    return base + (" " + m.group(2) if m.group(2) else "")


class PainelMultiTransform(_Base):
    """Peça → Multitransformação: operações a repetir e a lista de transformações (espelhar, padrões,
    escala) em ordem, com adicionar, editar, excluir, subir e descer. Ao editar uma transformação, o quadro
    dela (do FreeCAD) aparece abaixo, com o OK próprio."""

    def _acoes(self):
        lw = self.f.w("listTransformFeatures", QtWidgets.QListWidget)
        return lw.actions() if lw is not None else []

    def _acao(self, indice):
        acoes = self._acoes()
        return acoes[indice] if 0 <= indice < len(acoes) else None

    def estado(self):
        f = self.f
        lt = f.w("listTransformFeatures", QtWidgets.QListWidget)
        ok = f.w("buttonOK", QtWidgets.QAbstractButton)
        add = f.w("buttonAddFeature", QtWidgets.QAbstractButton)
        rem = f.w("buttonRemoveFeature", QtWidgets.QAbstractButton)
        return {"ops": self._lista("listWidgetFeatures"),
                "add": bool(add.isChecked()) if add else False, "rem": bool(rem.isChecked()) if rem else False,
                "trans": tuple(lt.item(i).text() for i in range(lt.count())) if lt else (),
                "sel": lt.currentRow() if lt else -1,
                "sub": bool(ok is not None and ok.isVisibleTo(self.quadro))}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        self._selecao("Operações a repetir", "padrao", list(e["ops"]), "Nenhuma operação escolhida",
                      [("buttonAddFeature", "Adicionar", "Concluir"), ("buttonRemoveFeature", "Tirar", "Concluir")],
                      "ops")
        c = UI.Cartao("Transformações (aplicadas em ordem)", "lista")
        lt = f.w("listTransformFeatures", QtWidgets.QListWidget)
        lista = QtWidgets.QListWidget()
        lista.setObjectName("PrumoLista")
        for t in e["trans"]:
            lista.addItem(nome_transformacao(t))
        lista.setFixedHeight(max(34, min(len(e["trans"]), 6) * 26 + 8))
        if 0 <= e["sel"] < lista.count():
            lista.setCurrentRow(e["sel"])
        lista.currentRowChanged.connect(lambda r, lt=lt: lt is not None and lt.setCurrentRow(r))
        lista.itemDoubleClicked.connect(lambda _it: self._executar(0))
        if e["trans"]:
            c.widget(lista)
        else:
            vazio = QtWidgets.QLabel("Nenhuma transformação: adicione abaixo.")
            vazio.setObjectName("PrumoSub")
            c.widget(vazio)
        self.campos["lista"] = lista
        grade = QtWidgets.QWidget()
        g = QtWidgets.QGridLayout(grade)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(4)
        for n, (_orig, texto) in enumerate(TIPOS_MULTI):
            b = QtWidgets.QPushButton(texto)
            b.setEnabled(not e["sub"])
            b.clicked.connect(lambda _=False, i=2 + n: self._executar(i))
            g.addWidget(b, n // 2, n % 2)
            self.campos["add%d" % n] = b
        c.widget(grade)
        linha = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(linha)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        for n, (_orig, texto) in enumerate(ACOES_ITEM):
            b = QtWidgets.QPushButton(texto)
            b.setEnabled(bool(e["trans"]) and e["sel"] >= 0 and not e["sub"])
            idx = {0: 0, 1: 1, 2: 6, 3: 7}[n]
            b.clicked.connect(lambda _=False, i=idx: self._executar(i))
            hl.addWidget(b)
            self.campos["item%d" % n] = b
        c.widget(linha)
        self.lay.addWidget(c)
        if e["sub"]:
            ok = f.w("buttonOK", QtWidgets.QAbstractButton)
            b = QtWidgets.QPushButton("Concluir esta transformação")
            b.setObjectName("PrumoPrimario")
            b.clicked.connect(lambda _=False, ok=ok: (ok.click(), QtCore.QTimer.singleShot(100, self.montar)))
            self.lay.addWidget(b)
            self.campos["concluir"] = b
        self._acabamento()
        self._fim()

    def _executar(self, indice):
        a = self._acao(indice)
        if a is not None:
            a.trigger()
        QtCore.QTimer.singleShot(120, self.montar)

    def dica_extra(self):
        e = self.estado()
        if e["sub"]:
            return "Ajuste a transformação no quadro do FreeCAD abaixo e clique em \"Concluir esta transformação\"."
        if e["add"] or e["rem"]:
            return DICA_ESCOLHA.get("buttonRefAdd", "")
        return ""

    def precisa_do_formulario(self):
        ok = self.f.w("buttonOK", QtWidgets.QAbstractButton)
        return bool(ok is not None and ok.isVisibleTo(self.quadro))


MODOS_ORIENTACAO = [("0", "Padrão", "seta_cima"), ("1", "Fixo", "fixacao"), ("2", "Frenet", "angulo"),
                    ("3", "Curva auxiliar", "perfil"), ("4", "Direção dada", "medida")]
DICA_ORIENTACAO = {0: "O perfil acompanha o caminho (o mais comum).",
                   1: "O perfil não gira ao longo do caminho.",
                   2: "O perfil segue a curvatura do caminho (bom para hélices e molas).",
                   3: "Uma segunda curva guia como o perfil gira.",
                   4: "O perfil mantém uma direção fixa (X, Y, Z)."}


class PainelOrientacaoPipe(_Escolhas):
    """Varredura → quadro "Orientação da seção" em cartões."""

    BOTOES = ("buttonProfileBase", "buttonRefAdd", "buttonRefRemove")

    def estado(self):
        f = self.f
        pb = f.w("profileBaseEdit", QtWidgets.QLineEdit)
        vals = []
        for n in ("doubleSpinBoxX", "doubleSpinBoxY", "doubleSpinBoxZ"):
            w = f.w(n, QtWidgets.QDoubleSpinBox)
            vals.append(round(w.value(), 6) if w else None)
        return {"modo": f.indice("comboBoxMode"), "aux": pb.text() if pb else "", "refs": self._lista(),
                "esc": self._escolhendo(*self.BOTOES), "vals": tuple(vals),
                "curv": bool(f.check("curvilinear").isChecked()) if f.check("curvilinear") else False}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        f = self.f
        c = UI.Cartao("Orientação do perfil", "angulo")
        seg = UI.Segmentado(MODOS_ORIENTACAO, str(max(0, e["modo"])), colunas=3)
        seg.mudou.connect(lambda k: self._indice("comboBoxMode", int(k)))
        c.widget(seg)
        self.campos["modo"] = seg
        lb = QtWidgets.QLabel(DICA_ORIENTACAO.get(e["modo"], ""))
        lb.setObjectName("PrumoSub")
        lb.setWordWrap(True)
        c.widget(lb)
        self.lay.addWidget(c)
        if e["modo"] == 3:
            itens = ([e["aux"]] if e["aux"] else []) + list(e["refs"])
            self._selecao("Curva auxiliar", "perfil", itens, "Nenhuma curva escolhida",
                          [("buttonProfileBase", "Escolher curva", "Escolhendo…"), ("buttonRefAdd", "Mais arestas",
                                                                                   "Concluir"),
                           ("buttonRefRemove", "Tirar", "Concluir")], "aux")
            c = UI.Cartao("Curva auxiliar", "acabamento")
            self._chave("curvilinear", "Curvilínea equivalente", c, "curv")
            self.lay.addWidget(c)
        if e["modo"] == 4:
            c = UI.Cartao("Direção", "medida")
            for n, rot in (("doubleSpinBoxX", "X"), ("doubleSpinBoxY", "Y"), ("doubleSpinBoxZ", "Z")):
                _num_simples(self, n, rot, "", c, casas=3)
            self.lay.addWidget(c)
        self._fim()


class PainelSecoesPipe(_Escolhas):
    """Varredura → quadro "Transformação da seção" em cartões: perfil constante ou várias seções."""

    BOTOES = ("buttonRefAdd", "buttonRefRemove")

    def estado(self):
        return {"modo": self.f.indice("comboBoxScaling"), "refs": self._lista(),
                "esc": self._escolhendo(*self.BOTOES)}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        c = UI.Cartao("Seção ao longo do caminho", "perfil")
        seg = UI.Segmentado([("0", "Constante", "medida"), ("1", "Várias seções", "padrao")],
                            str(max(0, e["modo"])), colunas=2)
        seg.mudou.connect(lambda k: self._indice("comboBoxScaling", int(k)))
        c.widget(seg)
        self.campos["modo"] = seg
        self.lay.addWidget(c)
        if e["modo"] == 1:
            self._selecao("Seções (na ordem do caminho)", "lista", list(e["refs"]),
                          "Nenhuma seção: adicione esboços ao longo do caminho",
                          [("buttonRefAdd", "Adicionar", "Concluir"), ("buttonRefRemove", "Tirar", "Concluir")],
                          "secoes")
        self._fim()


# quadros secundários (aparecem junto do painel principal): marca → classe
SECUNDARIOS = [("comboBoxMode", "PainelOrientacaoPipe"), ("comboBoxScaling", "PainelSecoesPipe"),
               ("PrumoGeoSel", "PainelOndeVale"), ("PrumoChecaGeo", "PainelChecaGeometria")]

# quadros do FreeCAD sem nome de objeto: o encaixe dá o nome pela classe (metaObject) antes de procurar
CLASSES_SEM_NOME = {"PrumoGeoSel": "GeometryElementsSelection",
                    "PrumoChecaGeo": "PartGui::TaskCheckGeometryResults"}


CLASSES = {"PartDesign::Pad": "PainelComando", "PartDesign::Pocket": "PainelComando",
           "PartDesign::Hole": "PainelFuro", "PartDesign::Revolution": "PainelRevolucao",
           "PartDesign::Groove": "PainelRevolucao", "PartDesign::Fillet": "PainelAcabamentoArestas",
           "PartDesign::Chamfer": "PainelAcabamentoArestas", "PartDesign::LinearPattern": "PainelPadrao",
           "PartDesign::PolarPattern": "PainelPadrao", "PartDesign::Mirrored": "PainelPadrao",
           "PartDesign::Draft": "PainelAngulo", "PartDesign::Thickness": "PainelCasca",
           "PartDesign::AdditiveHelix": "PainelHelice", "PartDesign::SubtractiveHelix": "PainelHelice",
           "PartDesign::AdditiveLoft": "PainelLoft", "PartDesign::SubtractiveLoft": "PainelLoft",
           "PartDesign::AdditivePipe": "PainelVarredura", "PartDesign::SubtractivePipe": "PainelVarredura",
           "PartDesign::Boolean": "PainelBooleana", "PartDesign::MultiTransform": "PainelMultiTransform"}
CLASSES.update({t: "PainelPrimitiva" for t in MARCA if MARCA[t] == "PartDesignGui__DlgPrimitives"})


class Encaixe:
    """Põe o PainelComando no topo do painel de tarefas enquanto uma Extrusão/Cavidade está em edição."""

    def __init__(self):
        self.painel = None
        self.obj = None
        self.t = QtCore.QTimer(FreeCADGui.getMainWindow())
        self.t.setInterval(300)
        self.t.timeout.connect(self._tick)

    def iniciar(self):
        self.t.start()

    def _vivo(self):
        return self.painel is not None and shiboken.isValid(self.painel)

    def _tirar(self):
        if self._vivo():
            self.painel.hide()
            self.painel.setParent(None)
            self.painel.deleteLater()
        self.painel, self.obj = None, None

    def _tick(self):
        try:
            self._passo()
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: painel de comando: {}\n".format(exc))

    def _avulso(self, panel):
        """(marca, quadro) de um formulário avulso (ex.: vistas do Desenho) no painel de tarefas."""
        for marca in AVULSOS:
            q = _quadro_do_formulario(panel, marca)
            if q is not None:
                return marca, q
        return None, None

    def _passo(self):
        obj = em_edicao() if ligado() else None
        panel = _painel_de_tarefas() if ligado() else None
        marca = None
        if obj is None and panel is not None:
            marca, quadro = self._avulso(panel)
        if obj is None and marca is None:
            if self.painel is not None:
                self._tirar()
            return
        if panel is None:
            return
        if obj is not None:
            quadro = _quadro_do_formulario(panel, MARCA[obj.TypeId])
        if quadro is None:
            return
        chave = obj if obj is not None else marca
        if not self._vivo() or self.painel.parent() is not panel or self.obj is not chave or \
                self.painel.quadro is not quadro:
            self._tirar()
            self.obj = chave
            classe = CLASSES[obj.TypeId] if obj is not None else AVULSOS[marca]
            self.painel = globals()[classe](obj, quadro, panel)
            lay = panel.layout()
            lay.insertWidget(lay.indexOf(quadro), self.painel)
            return
        self.painel.atualizar()
        self.painel.mostrar_formulario()


_estado = {"encaixe": None}


# ----------------------------------------------------------------------------------- Verificar geometria
class PainelChecaGeometria(_Base):
    """Sólidos → Verificar geometria: resumo em cartões acima dos resultados do FreeCAD (a lista de defeitos
    continua lá, para clicar e achar na vista). O resumo é calculado aqui, direto das formas."""

    TITULO = "Verificar geometria"

    def _objetos(self):
        if getattr(self, "_objs", None) is None:
            objs = []
            for so in FreeCADGui.Selection.getSelectionEx():
                o = so.Object
                if o is not None and hasattr(o, "Shape") and o not in objs:
                    objs.append(o)
            self._objs = objs
        return [o for o in self._objs if _vivo_obj(o)]

    def _problemas(self):
        tv = self.quadro.findChild(QtWidgets.QTreeView) if self.quadro is not None else None
        m = tv.model() if tv is not None else None
        if m is None:
            return 0
        n = 0
        for i in range(m.rowCount()):
            n += max(1, m.rowCount(m.index(i, 0)))
        return n

    def estado(self):
        return {"objs": tuple(o.Name for o in self._objetos()), "prob": self._problemas()}

    def montar(self):
        e = self.estado()
        self.assinatura = tuple(sorted(e.items()))
        self._limpar()
        self.campos = {}
        objs = self._objetos()
        if not objs:
            self._fim()
            self.completo.hide()
            return
        for i, o in enumerate(objs[:6]):
            sh = o.Shape
            ok = bool(sh.isValid()) if not sh.isNull() else False
            c = UI.Cartao(o.Label, "solido")
            st = QtWidgets.QLabel("✓ Geometria válida" if ok else "✗ Geometria com defeito — veja a lista abaixo")
            st.setObjectName("PrumoSub")
            st.setStyleSheet("font-weight: 600; color: %s;" % ("#1E7B34" if ok else "#B3261E"))
            c.widget(st)
            self.campos["estado%d" % i] = st
            for rot, n in (("Sólidos", len(sh.Solids)), ("Cascas", len(sh.Shells)), ("Faces", len(sh.Faces)),
                           ("Arestas", len(sh.Edges)), ("Vértices", len(sh.Vertexes))):
                lb = QtWidgets.QLabel(_br(n, 0))
                c.linha(rot, lb)
                self.campos["%s%d" % (rot.lower(), i)] = lb
            if sh.Solids:
                lb = QtWidgets.QLabel("{} mm³".format(_br(sh.Volume, 1)))
                c.linha("Volume", lb)
                self.campos["volume%d" % i] = lb
            if sh.Faces:
                c.linha("Área", QtWidgets.QLabel("{} mm²".format(_br(sh.Area, 1))))
            self.lay.addWidget(c)
        self._fim()
        self.completo.hide()

    def dica_extra(self):
        n = self._problemas()
        return ("{} item(ns) na lista de defeitos abaixo: clique em um para ver onde fica.".format(n)) if n else ""

    def precisa_do_formulario(self):
        return True

    def mostrar_formulario(self):
        # o FreeCAD esconde o quadro de resultados na página de ajustes: o resumo acompanha
        if self.quadro is not None and shiboken.isValid(self.quadro):
            self.setVisible(not self.quadro.isHidden())
        self.dica.mostrar(self.dica_extra())


def _vivo_obj(o):
    try:
        return o.Document is not None and o.Name is not None
    except Exception:
        return False


# ----------------------------------------------------------------------------------- Peso próprio
DIRECOES_GRAVIDADE = [("0,0,-1", "−Z (para baixo)", "seta_baixo"), ("0,0,1", "+Z", "seta_cima"),
                      ("0,-1,0", "−Y", None), ("0,1,0", "+Y", None), ("-1,0,0", "−X", None), ("1,0,0", "+X", None)]


def _chave_direcao(v):
    try:
        n = FreeCAD.Vector(v)
        if n.Length == 0:
            return None
        n.normalize()
    except Exception:
        return None
    for k, _t, _i in DIRECOES_GRAVIDADE:
        x, y, z = (float(c) for c in k.split(","))
        if (n - FreeCAD.Vector(x, y, z)).Length < 1e-6:
            return k
    return None


class PainelPesoProprio(QtWidgets.QWidget):
    """Simulação → Peso próprio: direção da gravidade e aceleração (o FreeCAD não tem painel para isso)."""

    TITULO = "Peso próprio"

    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.setObjectName("PrumoUI")
        self.setWindowTitle("Peso próprio")
        self.setProperty("prumo_titulo", self.TITULO)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema("#PrumoUI { background: transparent; }"))
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.campos = {}
        c = UI.Cartao("Gravidade", "seta_baixo")
        atual = _chave_direcao(obj.GravityDirection)
        seg = UI.Segmentado(DIRECOES_GRAVIDADE, atual or "0,0,-1", colunas=2)
        c.widget(seg)
        self.campos["direcao"] = seg
        self.outra = None
        if atual is None:
            d = obj.GravityDirection
            self.outra = QtWidgets.QLabel("Hoje está em ({:.3g}; {:.3g}; {:.3g}). Escolha uma acima para trocar."
                                          .format(d.x, d.y, d.z))
            self.outra.setObjectName("PrumoSub")
            self.outra.setWordWrap(True)
            c.widget(self.outra)
            seg.grupo.setExclusive(False)
            for b in seg.botoes.values():
                b.setChecked(False)
            seg.grupo.setExclusive(True)
        g = obj.GravityAcceleration.getValueAs("m/s^2").Value
        num = UI.CampoNumero(g, "m/s²", casas=5, minimo=0.0)
        c.linha("Aceleração", num)
        self.campos["aceleracao"] = num
        lay.addWidget(c)
        lay.addWidget(UI.Dica("O peso vem da densidade do material de cada sólido."))
        lay.addStretch(1)

    def aplicar(self):
        k = self.campos["direcao"].valor()
        if k is not None:
            x, y, z = (float(c) for c in k.split(","))
            self.obj.GravityDirection = FreeCAD.Vector(x, y, z)
        self.obj.GravityAcceleration = FreeCAD.Units.Quantity("%r m/s^2" % float(self.campos["aceleracao"].value()))


class TarefaPesoProprio:
    def __init__(self, obj):
        self.obj = obj
        self.form = PainelPesoProprio(obj)

    def getStandardButtons(self):
        def v(b):
            return b.value if hasattr(b, "value") else int(b)
        return v(QtWidgets.QDialogButtonBox.Ok) | v(QtWidgets.QDialogButtonBox.Cancel)

    # como as tarefas do FEM: criado pela faixa, a transação de criação está aberta — o OK grava junto
    # e o Cancelar desfaz a criação
    def accept(self):
        doc = self.obj.Document
        if not doc.HasPendingTransaction:
            doc.openTransaction("Peso próprio")
        self.form.aplicar()
        doc.recompute()
        FreeCADGui.ActiveDocument.resetEdit()
        doc.commitTransaction()
        return True

    def reject(self):
        doc = self.obj.Document
        doc.abortTransaction()
        FreeCADGui.ActiveDocument.resetEdit()
        doc.recompute()
        return True


def _peso_proprio_editavel():
    """Peso próprio ganha painel: duplo clique abre os cartões; criar pela faixa já abre o painel."""
    try:
        from femviewprovider import view_constraint_selfweight as V
        from femviewprovider import view_base_femobject as B
        from femcommands import commands as K
        from femcommands.manager import CommandManager
    except Exception:
        return
    if getattr(V.VPConstraintSelfWeight, "_prumo", False):
        return

    def setEdit(self, vobj, mode=0):
        return B.VPBaseFemObject.setEdit(self, vobj, mode, TarefaPesoProprio, hide_mesh=False)

    def Activated(self):
        self.do_activated = "add_obj_on_gui_set_edit"
        return CommandManager.Activated(self)
    V.VPConstraintSelfWeight.setEdit = setEdit
    K._ConstraintSelfWeight.Activated = Activated
    V.VPConstraintSelfWeight._prumo = True


def instalar():
    if _estado["encaixe"] is None:
        _estado["encaixe"] = Encaixe()
    _estado["encaixe"].iniciar()
    if _estado.get("fixacao") is None:
        _estado["fixacao"] = EncaixeFixacao()
    _estado["fixacao"].iniciar()
    if not _estado.get("extras"):
        _estado["extras"] = [EncaixeFixacao(m, c) for m, c in SECUNDARIOS]
    for e in _estado["extras"]:
        e.iniciar()
    _peso_proprio_editavel()
    return _estado["encaixe"]


def painel_secundario(classe):
    for e in _estado.get("extras") or []:
        if e.CLASSE == classe and e._vivo():
            return e.painel
    return None


def painel_fixacao():
    e = _estado.get("fixacao")
    return e.painel if e is not None and e._vivo() else None


def painel():
    e = _estado["encaixe"]
    return e.painel if e is not None and e._vivo() else None
