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

TIPOS = ("PartDesign::Pad", "PartDesign::Pocket", "PartDesign::Hole")
# campo que identifica o formulário do FreeCAD de cada comando
MARCA = {"PartDesign::Pad": "changeMode", "PartDesign::Pocket": "changeMode", "PartDesign::Hole": "ThreadType"}
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
        if w.findChild(QtWidgets.QComboBox, marca) is not None:
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
            self.dica.mostrar("")

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


CLASSES = {"PartDesign::Pad": "PainelComando", "PartDesign::Pocket": "PainelComando",
           "PartDesign::Hole": "PainelFuro"}


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
