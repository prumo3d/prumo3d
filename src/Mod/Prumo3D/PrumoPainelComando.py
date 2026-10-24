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
         "PartDesign::Boolean") + tuple("PartDesign::%s%s" % (a, b) for b in ("Box", "Cylinder", "Sphere", "Cone",
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
         "PartDesign::SubtractivePipe": "comboBoxTransition", "PartDesign::Boolean": "comboType"}
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
    for i in range(lay.count()):
        w = lay.itemAt(i).widget()
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
            self.dica.mostrar("Escolha a face (ou a peça) na vista: o quadro do FreeCAD abaixo mostra o que foi "
                              "escolhido.")
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

    def __init__(self, obj, quadro, parent=None):
        self.modos = []
        QtWidgets.QWidget.__init__(self, parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss() + UI.tema("#PrumoUI { background: transparent; }"))
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

    def _acabamento(self, extra=None):
        if not extra and "Refine" not in self.obj.PropertiesList:
            return
        c = UI.Cartao("Acabamento", "acabamento")
        for rot, w in (extra or []):
            c.linha(rot, w)
        if "Refine" in self.obj.PropertiesList:
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


CLASSES = {"PartDesign::Pad": "PainelComando", "PartDesign::Pocket": "PainelComando",
           "PartDesign::Hole": "PainelFuro", "PartDesign::Revolution": "PainelRevolucao",
           "PartDesign::Groove": "PainelRevolucao", "PartDesign::Fillet": "PainelAcabamentoArestas",
           "PartDesign::Chamfer": "PainelAcabamentoArestas", "PartDesign::LinearPattern": "PainelPadrao",
           "PartDesign::PolarPattern": "PainelPadrao", "PartDesign::Mirrored": "PainelPadrao",
           "PartDesign::Draft": "PainelAngulo", "PartDesign::Thickness": "PainelCasca",
           "PartDesign::AdditiveHelix": "PainelHelice", "PartDesign::SubtractiveHelix": "PainelHelice",
           "PartDesign::AdditiveLoft": "PainelLoft", "PartDesign::SubtractiveLoft": "PainelLoft",
           "PartDesign::AdditivePipe": "PainelVarredura", "PartDesign::SubtractivePipe": "PainelVarredura",
           "PartDesign::Boolean": "PainelBooleana"}
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

    def _passo(self):
        obj = em_edicao() if ligado() else None
        if obj is None:
            if self.painel is not None:
                self._tirar()
            return
        panel = _painel_de_tarefas()
        if panel is None:
            return
        quadro = _quadro_do_formulario(panel, MARCA[obj.TypeId])
        if quadro is None:
            return
        if not self._vivo() or self.painel.parent() is not panel or self.obj is not obj:
            self._tirar()
            self.obj = obj
            self.painel = globals()[CLASSES[obj.TypeId]](obj, quadro, panel)
            lay = panel.layout()
            lay.insertWidget(lay.indexOf(quadro), self.painel)
            return
        self.painel.atualizar()
        self.painel.mostrar_formulario()


_estado = {"encaixe": None}


def instalar():
    if _estado["encaixe"] is None:
        _estado["encaixe"] = Encaixe()
    _estado["encaixe"].iniciar()
    return _estado["encaixe"]


def painel():
    e = _estado["encaixe"]
    return e.painel if e is not None and e._vivo() else None
