# SPDX-License-Identifier: LGPL-2.1-or-later
"""Abas Propriedades e Aparência do painel lateral (no lugar das tabelas Dados e Vista do FreeCAD).

Propriedades: cartões com o que importa da peça ou operação selecionada, com chaves liga/desliga,
botões com ícone para as escolhas e campos com unidade. A tabela completa do FreeCAD continua a um
clique, em "Avançado".

Aparência: cor, transparência, modo de exibição, espessura de linha e visibilidade de tudo o que
estiver selecionado.

Cada mudança vira um passo do desfazer ("Alterar Comprimento") e recalcula o documento.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

import PrumoUI as UI

# ----------------------------------------------------------------------------------- textos
# Valores de listas (identificadores gravados no arquivo) → texto na tela
ENUM_PT = {
    "Length": "Medida", "TwoLengths": "Dois lados", "ThroughAll": "Através", "UpToFirst": "Até a 1ª",
    "UpToLast": "Até o fim", "UpToFace": "Até a face", "UpToShape": "Até a peça", "Dimension": "Medida",
    "One side": "Um lado", "Two sides": "Dois lados", "Symmetric": "Simétrica",
    "Flat Lines": "Arestas", "Shaded": "Sólido", "Wireframe": "Arame", "Points": "Pontos",
    "Equal distance": "Distância igual", "Two distances": "Duas distâncias", "Distance and Angle": "Distância e ângulo",
    "Overall Length": "Comprimento total",
    "Deactivated": "Solto", "FlatFace": "Na face", "Translate": "Só mover", "ObjectXY": "Plano XY do objeto",
    "ObjectXZ": "Plano XZ do objeto", "ObjectYZ": "Plano YZ do objeto", "ThreePointsPlane": "Por 3 pontos",
    "NormalToEdge": "Normal à aresta", "TangentPlane": "Tangente", "Concentric": "Concêntrico", "Offset": "Espaçamento", "Extent": "Extensão", "Spacing": "Espaçamento",
}
ENUM_ICONE = {
    "Length": "medida", "ThroughAll": "atraves", "UpToFirst": "ate_primeira", "UpToLast": "ate_fim",
    "UpToFace": "ate_face", "UpToShape": "solido", "One side": "seta_cima", "Two sides": "dois_lados",
    "Symmetric": "simetrica", "Flat Lines": "exibicao_arestas", "Shaded": "exibicao_solido",
    "Wireframe": "exibicao_arame", "Points": "exibicao_pontos",
}
TIPO_PT = {
    "PartDesign::Body": "Corpo", "Sketcher::SketchObject": "Esboço", "PartDesign::Pad": "Extrusão",
    "PartDesign::Pocket": "Cavidade", "PartDesign::Revolution": "Revolução", "PartDesign::Groove": "Ranhura",
    "PartDesign::Hole": "Furo", "PartDesign::Fillet": "Arredondamento", "PartDesign::Chamfer": "Chanfro",
    "PartDesign::Draft": "Ângulo de saída", "PartDesign::Thickness": "Casca",
    "PartDesign::LinearPattern": "Padrão linear", "PartDesign::PolarPattern": "Padrão circular",
    "PartDesign::Mirrored": "Espelhar", "PartDesign::MultiTransform": "Multitransformação",
    "Part::Box": "Cubo", "Part::Cylinder": "Cilindro", "Part::Feature": "Sólido", "App::Part": "Peça",
    "App::DocumentObjectGroup": "Pasta",
}

# Propriedades que nunca vão para os cartões (estão na árvore, no cabeçalho ou são internas)
FORA = {"Label", "Label2", "ExpressionEngine", "Visibility", "Placement", "Shape", "AddSubShape",
        "SuppressedShape", "PreviewShape", "InternalShape", "ShapeMaterial", "Group", "Origin", "BaseFeature",
        "Constraints", "Geometry", "ExternalGeo", "ExternalGeometry", "ExternalTypes", "Exports",
        "AttacherType", "AttacherEngine", "MapPathParameter", "FuzzyTolerance", "AllowMultiFace",
        "ArcFitTolerance", "Direction", "Direction2"}
GRUPOS_FORA = {"Base", "Compatibility"}
SUPORTADOS = {
    "App::PropertyBool": "chave", "App::PropertyEnumeration": "lista", "App::PropertyLength": "qtd",
    "App::PropertyDistance": "qtd", "App::PropertyAngle": "qtd", "App::PropertyQuantity": "qtd",
    "App::PropertyQuantityConstraint": "qtd", "App::PropertyArea": "qtd", "App::PropertyVolume": "qtd",
    "App::PropertyForce": "qtd", "App::PropertyPressure": "qtd", "App::PropertySpeed": "qtd",
    "App::PropertyFloat": "num", "App::PropertyFloatConstraint": "num", "App::PropertyPrecision": "num",
    "App::PropertyInteger": "int", "App::PropertyIntegerConstraint": "int", "App::PropertyPercent": "int",
    "App::PropertyString": "texto", "App::PropertyLink": "vinculo", "App::PropertyLinkSub": "vinculo",
    "App::PropertyLinkSubList": "vinculo", "App::PropertyLinkList": "vinculo", "App::PropertyLinkGlobal": "vinculo",
}

# Operações do PartDesign em cartões montados à mão (o resto sai por grupo de propriedades)
_UM_LADO = lambda o: getattr(o, "SideType", "One side") == "Two sides"   # noqa: E731


def _tipo_e(*valores):
    return lambda o: getattr(o, "Type", None) in valores


def _tipo2_e(*valores):
    return lambda o: getattr(o, "Type2", None) in valores


def _cartoes_extrusao(nome_dir):
    return [
        {"titulo": "Lados", "icone": "dois_lados", "props": [("SideType", None, None)]},
        {"titulo": "Direção 1", "icone": "seta_cima" if nome_dir == "Altura" else "seta_baixo", "props": [
            ("Type", "Até onde vai", None),
            ("Length", nome_dir, _tipo_e("Length")),
            ("Offset", "Afastamento", _tipo_e("UpToFace", "UpToFirst", "UpToLast", "UpToShape")),
            ("TaperAngle", "Ângulo de saída", None),
            ("Reversed", "Inverter", None)]},
        {"titulo": "Direção 2", "icone": "seta_baixo", "se": _UM_LADO, "props": [
            ("Type2", "Até onde vai", None),
            ("Length2", nome_dir, _tipo2_e("Length")),
            ("Offset2", "Afastamento", _tipo2_e("UpToFace", "UpToFirst", "UpToLast", "UpToShape")),
            ("TaperAngle2", "Ângulo de saída", None)]},
        {"titulo": "Perfil", "icone": "perfil", "props": [
            ("Profile", None, None), ("AlongSketchNormal", "Na normal do esboço", None),
            ("UseCustomVector", "Direção personalizada", None)]},
        {"titulo": "Acabamento", "icone": "acabamento", "props": [
            ("Refine", "Unir faces planas (refinar)", None), ("Suppressed", "Suprimir a operação", None)]},
    ]


CURADOS = {
    "PartDesign::Pad": _cartoes_extrusao("Altura"),
    "PartDesign::Pocket": _cartoes_extrusao("Profundidade"),
    "PartDesign::Fillet": [
        {"titulo": "Arredondamento", "icone": "raio", "props": [
            ("Radius", "Raio", None), ("UseAllEdges", "Todas as arestas", None), ("Base", None, None)]},
        {"titulo": "Acabamento", "icone": "acabamento", "props": [
            ("Refine", "Unir faces planas (refinar)", None), ("Suppressed", "Suprimir a operação", None)]}],
    "PartDesign::Chamfer": [
        {"titulo": "Chanfro", "icone": "chanfro", "props": [
            ("ChamferType", "Tipo", None), ("Size", "Distância", None), ("Size2", "Distância 2",
                                                                          lambda o: o.ChamferType == "Two distances"),
            ("Angle", "Ângulo", lambda o: o.ChamferType == "Distance and Angle"),
            ("FlipDirection", "Inverter o lado", None), ("UseAllEdges", "Todas as arestas", None),
            ("Base", None, None)]},
        {"titulo": "Acabamento", "icone": "acabamento", "props": [
            ("Refine", "Unir faces planas (refinar)", None), ("Suppressed", "Suprimir a operação", None)]}],
    "PartDesign::Body": [
        {"titulo": "Corpo", "icone": "corpo", "props": [
            ("Tip", "Operação final", None), ("AllowCompound", "Permitir mais de um sólido", None)]}],
    "Sketcher::SketchObject": [
        {"titulo": "Fixação", "icone": "fixacao", "props": [
            ("AttachmentSupport", "Apoiado em", None), ("MapMode", "Modo", None),
            ("MapReversed", "Inverter o lado", None)]},
        {"titulo": "Esboço", "icone": "esboco", "props": [
            ("MakeInternals", "Criar geometria interna", None)]}],
}


def _espacar(nome):
    """'AlongSketchNormal' → 'Along Sketch Normal' (como o FreeCAD mostra)."""
    out = ""
    for i, ch in enumerate(nome):
        if i and ch.isupper() and (not nome[i - 1].isupper() or (i + 1 < len(nome) and nome[i + 1].islower())):
            out += " "
        out += ch
    return out.replace("_", " ").strip()


def nome_pt(nome):
    try:
        from PrumoPropNames import PROPS
    except Exception:
        PROPS = {}
    esp = _espacar(nome)
    return PROPS.get(esp, esp)


def grupo_pt(grupo):
    try:
        from PrumoPropNames import PROPS
    except Exception:
        PROPS = {}
    return PROPS.get(grupo, grupo)


def tipo_pt(obj):
    t = obj.TypeId
    if t in TIPO_PT:
        return TIPO_PT[t]
    try:
        import PrumoNomes
        n = PrumoNomes.NOMES.get(t.split("::")[-1])
        if n:
            return n
    except Exception:
        pass
    proxy = getattr(obj, "Proxy", None)
    if proxy is not None and hasattr(proxy, "Type"):
        return str(proxy.Type)
    return t.split("::")[-1]


def _status(obj, prop):
    try:
        return obj.getPropertyStatus(prop) or []
    except Exception:
        return []


def _tipo_prop(obj, prop):
    try:
        return obj.getTypeIdOfProperty(prop)
    except Exception:
        return ""


def _expressao(obj, prop):
    try:
        for caminho, expr in obj.ExpressionEngine:
            if caminho == prop:
                return expr
    except Exception:
        pass
    return None


def _valor_qtd(q):
    """(número na unidade preferida, unidade, fator) de uma Quantity."""
    try:
        txt, fator, unid = q.getUserPreferred()
        return q.Value / fator, unid, fator
    except Exception:
        return float(q), "", 1.0


def _rotulo_link(v):
    if v is None:
        return "—"
    if isinstance(v, (list, tuple)):
        if not v:
            return "—"
        if len(v) == 2 and hasattr(v[0], "Label") and isinstance(v[1], (list, tuple, str)):
            subs = [v[1]] if isinstance(v[1], str) else list(v[1])
            subs = [s for s in subs if s]
            return v[0].Label + (" · " + ", ".join(subs[:3]) + ("…" if len(subs) > 3 else "") if subs else "")
        partes = []
        for item in v:
            partes.append(_rotulo_link(item))
        return ", ".join(partes[:3]) + ("…" if len(partes) > 3 else "")
    return getattr(v, "Label", str(v))


def campos_genericos(obj):
    """[(grupo, [props])] das propriedades que dá para mostrar em cartões, na ordem do objeto."""
    grupos = {}
    ordem = []
    for p in obj.PropertiesList:
        if p in FORA or p.startswith("_"):
            continue
        st = _status(obj, p)
        if "Hidden" in st or "ReadOnly" in st or "Output" in st:
            continue
        if _tipo_prop(obj, p) not in SUPORTADOS:
            continue
        g = obj.getGroupOfProperty(p) or "Geral"
        if g in GRUPOS_FORA:
            continue
        if g not in grupos:
            grupos[g] = []
            ordem.append(g)
        grupos[g].append(p)
    return [(g, grupos[g]) for g in ordem]


# ----------------------------------------------------------------------------------- aplicar
def aplicar(obj, prop, valor, rotulo=None, recalcular=True):
    """Muda a propriedade como um passo do desfazer e recalcula."""
    doc = getattr(obj, "Document", None)
    if doc is None and hasattr(obj, "Object"):
        doc = obj.Object.Document
    try:
        if doc is not None:
            doc.openTransaction("Alterar " + (rotulo or nome_pt(prop)))
        setattr(obj, prop, valor)
        if doc is not None:
            doc.commitTransaction()
            if recalcular:
                doc.recompute()
        return True
    except Exception as exc:
        if doc is not None:
            doc.abortTransaction()
        FreeCAD.Console.PrintWarning("Prumo: não foi possível mudar {}: {}\n".format(prop, exc))
        return False


# ----------------------------------------------------------------------------------- Propriedades
class Propriedades(QtWidgets.QWidget):
    """Conteúdo da aba Propriedades. avancado = o PropertyView original do FreeCAD (tabela completa)."""

    def __init__(self, avancado=None, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss())
        self.obj = None
        self.campos = {}
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # cabeçalho: ícone, tipo, nome editável, Editar
        self.cab = QtWidgets.QFrame()
        self.cab.setObjectName("PrumoCabecalho")
        self.cab.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.cab.setStyleSheet(UI.tema("#PrumoCabecalho { background: #FFFFFF; border-bottom: 1px solid #DCE4EC; }"))
        h = QtWidgets.QHBoxLayout(self.cab)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)
        self.ic = QtWidgets.QLabel()
        self.ic.setFixedSize(36, 36)
        self.ic.setAlignment(QtCore.Qt.AlignCenter)
        self.ic.setStyleSheet(UI.tema("background: #E6EEF7; border-radius: 8px;"))
        h.addWidget(self.ic)
        v = QtWidgets.QVBoxLayout()
        v.setSpacing(0)
        self.tipo = QtWidgets.QLabel()
        self.tipo.setObjectName("PrumoSub")
        v.addWidget(self.tipo)
        self.nome = QtWidgets.QLineEdit()
        self.nome.setFrame(False)
        self.nome.setStyleSheet(UI.tema("QLineEdit { background: transparent; border: 0; font-weight: 600; "
                                        "color: #1F2A36; padding: 0; }"))
        self.nome.editingFinished.connect(self._renomear)
        v.addWidget(self.nome)
        h.addLayout(v, 1)
        self.editar = QtWidgets.QPushButton("Editar")
        self.editar.setObjectName("PrumoPrimario")
        self.editar.setCursor(QtCore.Qt.PointingHandCursor)
        self.editar.clicked.connect(self._editar)
        h.addWidget(self.editar)
        lay.addWidget(self.cab)

        # cartões
        self.conteudo, self.col = UI.coluna()
        self.area = UI.rolagem(self.conteudo)
        lay.addWidget(self.area, 1)

        # avançado: a tabela completa do FreeCAD
        self.avancado = avancado
        self.botao_avancado = QtWidgets.QToolButton()
        self.botao_avancado.setObjectName("PrumoAvancado")
        self.botao_avancado.setCheckable(True)
        self.botao_avancado.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.botao_avancado.setCursor(QtCore.Qt.PointingHandCursor)
        self.botao_avancado.toggled.connect(self._modo_avancado)
        rodape = QtWidgets.QWidget()
        rodape.setObjectName("PrumoUI")
        rl = QtWidgets.QVBoxLayout(rodape)
        rl.setContentsMargins(12, 0, 12, 10)
        rl.addWidget(self.botao_avancado)
        lay.addWidget(rodape)
        if avancado is not None:
            avancado.setParent(self)
            lay.addWidget(avancado, 1)
        self._modo_avancado(False)
        self.montar(None)

    # ---------------------------------------------------------------- modo avançado
    def _modo_avancado(self, on):
        on = bool(on) and self.avancado is not None
        self.botao_avancado.setText("‹ Voltar aos cartões" if on else "Avançado (tabela completa)")
        self.area.setVisible(not on)
        self.cab.setVisible(not on and self.obj is not None)
        if self.avancado is not None:
            self.avancado.setVisible(on)
        self.botao_avancado.setVisible(self.avancado is not None)

    def abrir_avancado(self, aba_vista=False):
        self.botao_avancado.setChecked(True)
        if aba_vista and self.avancado is not None:
            for tw in self.avancado.findChildren(QtWidgets.QTabWidget):
                for i in range(tw.count()):
                    if tw.tabText(i) in ("Vista", "View", "Visualização"):
                        tw.setCurrentIndex(i)

    # ---------------------------------------------------------------- cabeçalho
    def _renomear(self):
        if self.obj is None:
            return
        novo = self.nome.text().strip()
        if novo and novo != self.obj.Label:
            aplicar(self.obj, "Label", novo, "nome", recalcular=False)

    def _editar(self):
        if self.obj is None:
            return
        try:
            FreeCADGui.ActiveDocument.setEdit(self.obj.Name, 0)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: {} não abre para edição: {}\n".format(self.obj.Label, exc))

    # ---------------------------------------------------------------- montar
    def _limpar(self):
        while self.col.count():
            it = self.col.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.campos = {}

    def montar(self, obj, quantos=1):
        if obj is not None and not _vivo(obj):
            obj = None
        rol = self.area.verticalScrollBar().value() if obj is not None and obj is self.obj else 0
        self.obj = obj
        self._limpar()
        if obj is None:
            self.cab.setVisible(False)
            self.col.addWidget(UI.Dica("Selecione uma peça, operação ou esboço (na árvore ou na vista) para "
                                       "ver e mudar as propriedades aqui."))
            self.col.addStretch(1)
            return
        self.cab.setVisible(not self.botao_avancado.isChecked())
        vp = getattr(obj, "ViewObject", None)
        ic = getattr(vp, "Icon", None) if vp is not None else None
        if ic is not None and not ic.isNull():
            self.ic.setPixmap(ic.pixmap(22, 22))
        else:
            self.ic.setPixmap(UI.icone("solido").pixmap(22, 22))
        self.tipo.setText(tipo_pt(obj) + ("  ·  {} selecionados".format(quantos) if quantos > 1 else ""))
        self.nome.setText(obj.Label)
        self.nome.setCursorPosition(0)
        editavel = obj.TypeId not in ("App::DocumentObjectGroup", "App::Origin", "App::Line", "App::Plane")
        self.editar.setVisible(editavel)

        cartoes = CURADOS.get(obj.TypeId)
        if cartoes:
            for desc in cartoes:
                se = desc.get("se")
                if se is not None and not _seguro(se, obj):
                    continue
                c = UI.Cartao(desc["titulo"], desc.get("icone"))
                for prop, rotulo, cond in desc["props"]:
                    if prop not in obj.PropertiesList:
                        continue
                    if cond is not None and not _seguro(cond, obj):
                        continue
                    self._campo(c, obj, prop, rotulo)
                if not c.vazio():
                    self.col.addWidget(c)
        else:
            for grupo, props in campos_genericos(obj):
                c = UI.Cartao(grupo_pt(grupo), None)
                for prop in props:
                    self._campo(c, obj, prop, None)
                if not c.vazio():
                    self.col.addWidget(c)
        if not self.campos:
            self.col.addWidget(UI.Dica("Este objeto não tem propriedades simples para mudar aqui. "
                                       "Use \"Avançado\" para a tabela completa."))
        self.col.addStretch(1)
        QtCore.QTimer.singleShot(0, lambda: self.area.verticalScrollBar().setValue(rol))

    def _campo(self, cartao, obj, prop, rotulo):
        tipo = SUPORTADOS.get(_tipo_prop(obj, prop))
        if tipo is None:
            return None
        rotulo = rotulo or nome_pt(prop)
        try:
            valor = getattr(obj, prop)
        except Exception:
            return None
        expr = _expressao(obj, prop)
        ro = "ReadOnly" in _status(obj, prop)
        w = None
        if tipo == "chave":
            w = UI.Interruptor(bool(valor))
            w.toggled.connect(lambda on, p=prop, r=rotulo: self._mudar(p, bool(on), r))
        elif tipo == "lista":
            opcoes = [e for e in obj.getEnumerationsOfProperty(prop) if not str(e).startswith("?")]
            if 1 < len(opcoes) <= 6 and all(len(ENUM_PT.get(e, e)) <= 14 for e in opcoes):
                w = UI.Segmentado([(e, ENUM_PT.get(e, e), ENUM_ICONE.get(e)) for e in opcoes], valor,
                                  colunas=4 if len(opcoes) != 6 else 3)
                w.mudou.connect(lambda k, p=prop, r=rotulo: self._mudar(p, k, r))
                # botões ocupam a largura do cartão; o rótulo vai em cima, pequeno
                if prop != "SideType":
                    sub = QtWidgets.QLabel(rotulo)
                    sub.setObjectName("PrumoSub")
                    cartao.widget(sub)
                cartao.widget(w)
                if ro:
                    w.setEnabled(False)
                self.campos[prop] = w
                return w
            else:
                w = QtWidgets.QComboBox()
                w.setObjectName("PrumoLista")
                for e in opcoes:
                    w.addItem(ENUM_PT.get(e, e), e)
                i = w.findData(valor)
                w.setCurrentIndex(max(0, i))
                w.setMaximumWidth(170)
                w.activated.connect(lambda i, ww=w, p=prop, r=rotulo: self._mudar(p, ww.itemData(i), r))
        elif tipo in ("qtd", "num", "int"):
            if tipo == "qtd":
                num, unid, fator = _valor_qtd(valor)
                w = UI.CampoNumero(num, unid, casas=2)
                w.valueChanged.connect(lambda x, p=prop, r=rotulo, u=unid: self._mudar(
                    p, FreeCAD.Units.Quantity("{} {}".format(repr(float(x)), u)) if u else x, r))
            elif tipo == "num":
                w = UI.CampoNumero(float(valor), "", casas=3)
                w.valueChanged.connect(lambda x, p=prop, r=rotulo: self._mudar(p, float(x), r))
            else:
                w = QtWidgets.QSpinBox()
                w.setObjectName("PrumoNum")
                w.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                w.setRange(-10 ** 9, 10 ** 9)
                w.setKeyboardTracking(False)
                w.setValue(int(valor))
                w.setMaximumWidth(120)
                w.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                if _tipo_prop(obj, prop) == "App::PropertyPercent":
                    w.setRange(0, 100)
                    w.setSuffix(" %")
                w.valueChanged.connect(lambda x, p=prop, r=rotulo: self._mudar(p, int(x), r))
            if expr is not None:
                w.setReadOnly(True)
                w.setProperty("expressao", True)
                w.setToolTip("Definido por fórmula: = {}".format(expr))
        elif tipo == "texto":
            w = QtWidgets.QLineEdit(str(valor))
            w.setObjectName("PrumoCampo")
            w.setMaximumWidth(170)
            w.editingFinished.connect(lambda ww=w, p=prop, r=rotulo: self._mudar(p, ww.text(), r))
        elif tipo == "vinculo":
            texto = _rotulo_link(valor)
            w = UI.Chip(texto)
            if prop in ("Profile", "AttachmentSupport", "Base"):
                caixa = QtWidgets.QWidget()
                hl = QtWidgets.QHBoxLayout(caixa)
                hl.setContentsMargins(0, 0, 0, 0)
                hl.setSpacing(6)
                hl.addWidget(w)
                hl.addStretch(1)
                if prop == "Profile":
                    cartao.widget(caixa)       # o cartão já se chama Perfil
                else:
                    cartao.linha(rotulo, caixa, chave=prop)
                self.campos[prop] = w
                return w
        if w is None:
            return None
        if ro:
            w.setEnabled(False)
        cartao.linha(rotulo, w, chave=prop)
        self.campos[prop] = w
        return w

    def _mudar(self, prop, valor, rotulo):
        obj = self.obj
        if obj is None:
            return
        try:
            atual = getattr(obj, prop)
            if hasattr(atual, "Value") and hasattr(valor, "Value"):
                if abs(atual.Value - valor.Value) < 1e-9:
                    return
            elif atual == valor:
                return
        except Exception:
            pass
        aplicar(obj, prop, valor, rotulo)
        # escolha que muda o que aparece (ex.: Medida → Até a face): remonta depois do clique.
        # Números e textos não remontam (o cursor segue para o próximo campo).
        if isinstance(valor, (bool, str)) and not isinstance(self.campos.get(prop), QtWidgets.QLineEdit):
            QtCore.QTimer.singleShot(0, lambda: self.montar(obj) if self.obj is obj and _vivo(obj) else None)

    def foco_aqui(self):
        f = QtWidgets.QApplication.focusWidget()
        return f is not None and (f is self or self.isAncestorOf(f))


def _vivo(obj):
    """O objeto ainda existe (não foi apagado nem fechou com o documento)?"""
    try:
        return obj.Name is not None and obj.Document is not None
    except Exception:
        return False


def _seguro(fn, obj):
    try:
        return bool(fn(obj))
    except Exception:
        return False


# ----------------------------------------------------------------------------------- Aparência
CORES = (("Aço", "#A7B1BB"), ("Azul", "#003A70"), ("Amarelo", "#F7BE00"), ("Vermelho", "#B23A2B"),
         ("Verde", "#1E7A4C"), ("Cinza escuro", "#4A5563"), ("Preto", "#23272B"))
ESPESSURAS = ((1.0, "Fina"), (2.0, "Média"), (4.0, "Grossa"))


def cor_de(vo):
    """Cor principal (r, g, b) 0–1 do objeto."""
    try:
        mats = vo.ShapeAppearance
        if mats:
            c = mats[0].DiffuseColor
            return tuple(c[:3])
    except Exception:
        pass
    try:
        return tuple(vo.ShapeColor[:3])
    except Exception:
        return None


def pintar(vo, rgb):
    """Pinta o objeto inteiro (todas as faces) na cor rgb 0–1."""
    if "ShapeAppearance" in vo.PropertiesList:
        mats = list(vo.ShapeAppearance)
        if not mats:
            return False
        m = mats[0]
        m.DiffuseColor = (rgb[0], rgb[1], rgb[2], m.DiffuseColor[3] if len(m.DiffuseColor) > 3 else 0.0)
        vo.ShapeAppearance = [m]
        return True
    if "ShapeColor" in vo.PropertiesList:
        vo.ShapeColor = tuple(rgb)
        return True
    return False


class Aparencia(QtWidgets.QWidget):
    """Conteúdo da aba Aparência: vale para tudo o que estiver selecionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoUI")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(UI.qss())
        self.objs = []
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.cab = QtWidgets.QFrame()
        self.cab.setObjectName("PrumoCabecalho")
        self.cab.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.cab.setStyleSheet(UI.tema("#PrumoCabecalho { background: #FFFFFF; border-bottom: 1px solid #DCE4EC; }"))
        h = QtWidgets.QHBoxLayout(self.cab)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)
        self.ic = QtWidgets.QLabel()
        self.ic.setFixedSize(36, 36)
        self.ic.setAlignment(QtCore.Qt.AlignCenter)
        self.ic.setStyleSheet(UI.tema("background: #E6EEF7; border-radius: 8px;"))
        h.addWidget(self.ic)
        v = QtWidgets.QVBoxLayout()
        v.setSpacing(0)
        self.tipo = QtWidgets.QLabel()
        self.tipo.setObjectName("PrumoSub")
        self.nome = QtWidgets.QLabel()
        self.nome.setStyleSheet("font-weight: 600;")
        v.addWidget(self.tipo)
        v.addWidget(self.nome)
        h.addLayout(v, 1)
        self.visivel = UI.Interruptor(True, dica="Mostrar ou esconder")
        self.visivel.toggled.connect(self._visibilidade)
        h.addWidget(self.visivel)
        lay.addWidget(self.cab)
        self.conteudo, self.col = UI.coluna()
        lay.addWidget(UI.rolagem(self.conteudo), 1)
        self.montar([])

    def _limpar(self):
        while self.col.count():
            it = self.col.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _vos(self):
        out = []
        for o in self.objs:
            vo = getattr(o, "ViewObject", None)
            if vo is not None:
                out.append(vo)
        return out

    def montar(self, objs):
        self.objs = [o for o in objs if _vivo(o) and getattr(o, "ViewObject", None) is not None]
        self._limpar()
        self.controles = {}
        if not self.objs:
            self.cab.setVisible(False)
            self.col.addWidget(UI.Dica("Selecione o que quer pintar, deixar transparente ou mudar o jeito de "
                                       "mostrar."))
            self.col.addStretch(1)
            return
        o = self.objs[0]
        vo = o.ViewObject
        self.cab.setVisible(True)
        ic = getattr(vo, "Icon", None)
        self.ic.setPixmap(ic.pixmap(22, 22) if ic is not None and not ic.isNull()
                          else UI.icone("solido").pixmap(22, 22))
        self.tipo.setText(tipo_pt(o) if len(self.objs) == 1 else "{} itens".format(len(self.objs)))
        self.nome.setText(o.Label if len(self.objs) == 1 else ", ".join(x.Label for x in self.objs[:3])
                          + ("…" if len(self.objs) > 3 else ""))
        self.visivel.blockSignals(True)
        self.visivel.setChecked(bool(vo.Visibility))
        self.visivel.blockSignals(False)

        vos = self._vos()
        tem = lambda p: any(p in v.PropertiesList for v in vos)   # noqa: E731

        if tem("ShapeAppearance") or tem("ShapeColor"):
            c = UI.Cartao("Cor", "aparencia")
            linha = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(linha)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(8)
            atual = cor_de(vo)
            self.amostras = []
            for nome, hexcor in CORES:
                b = self._amostra(nome, hexcor, atual)
                hl.addWidget(b)
            outra = QtWidgets.QToolButton()
            outra.setObjectName("PrumoAmostra")
            outra.setToolTip("Outra cor…")
            outra.setFixedSize(28, 28)
            outra.setStyleSheet("QToolButton { border-radius: 14px; border: 2px solid #FFFFFF; background: "
                                "qconicalgradient(cx:0.5, cy:0.5, angle:0, stop:0 #e33, stop:0.2 #ec3, "
                                "stop:0.4 #3c6, stop:0.6 #39e, stop:0.8 #c3e, stop:1 #e33); }")
            outra.clicked.connect(self._outra_cor)
            hl.addWidget(outra)
            hl.addStretch(1)
            c.widget(linha)
            self.col.addWidget(c)

        if tem("Transparency"):
            c = UI.Cartao("Transparência", "olho")
            t = int(getattr(vo, "Transparency", 0) or 0)
            linha = QtWidgets.QWidget()
            hl = QtWidgets.QHBoxLayout(linha)
            hl.setContentsMargins(0, 0, 0, 0)
            s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            s.setObjectName("PrumoDeslizar")
            s.setRange(0, 100)
            s.setValue(t)
            pc = QtWidgets.QLabel("{} %".format(t))
            pc.setMinimumWidth(40)
            pc.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            s.valueChanged.connect(lambda x, lb=pc: lb.setText("{} %".format(x)))
            s.sliderReleased.connect(lambda ss=s: self._todos("Transparency", int(ss.value()), "transparência"))
            s.valueChanged.connect(lambda x, ss=s: (not ss.isSliderDown()) and self._todos(
                "Transparency", int(x), "transparência"))
            hl.addWidget(s, 1)
            hl.addWidget(pc)
            c.widget(linha)
            self.controles["Transparency"] = s
            self.col.addWidget(c)

        c = UI.Cartao("Exibição", "exibicao_arestas")
        if tem("DisplayMode"):
            modos = [m for m in vo.getEnumerationsOfProperty("DisplayMode") if m]
            if 1 < len(modos) <= 6:
                seg = UI.Segmentado([(m, ENUM_PT.get(m, m), ENUM_ICONE.get(m)) for m in modos], vo.DisplayMode,
                                    colunas=4 if len(modos) != 6 else 3)
                seg.mudou.connect(lambda m: self._todos("DisplayMode", m, "modo de exibição"))
                c.widget(seg)
                self.controles["DisplayMode"] = seg
        if tem("LineWidth"):
            lw = float(getattr(vo, "LineWidth", 2.0) or 2.0)
            perto = min(ESPESSURAS, key=lambda e: abs(e[0] - lw))[0]
            seg = UI.Segmentado([(str(v), t) for v, t in ESPESSURAS], str(perto), colunas=3)
            seg.mudou.connect(lambda k: self._todos("LineWidth", float(k), "espessura da linha"))
            c.linha("Espessura da linha", seg)
            seg.setMinimumWidth(170)
            self.controles["LineWidth"] = seg
        if tem("Selectable"):
            sw = UI.Interruptor(bool(getattr(vo, "Selectable", True)))
            sw.toggled.connect(lambda on: self._todos("Selectable", bool(on), "selecionável"))
            c.linha("Selecionável na tela", sw)
            self.controles["Selectable"] = sw
        if not c.vazio():
            self.col.addWidget(c)

        av = QtWidgets.QToolButton()
        av.setObjectName("PrumoAvancado")
        av.setText("Avançado (antiga aba Vista)")
        av.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        av.setCursor(QtCore.Qt.PointingHandCursor)
        av.clicked.connect(self._avancado)
        self.col.addWidget(av)
        self.col.addStretch(1)

    def _amostra(self, nome, hexcor, atual):
        b = QtWidgets.QToolButton()
        b.setObjectName("PrumoAmostra")
        b.setToolTip(nome)
        b.setFixedSize(28, 28)
        q = QtGui.QColor(hexcor)
        marcada = atual is not None and all(abs(a - x) < 0.02 for a, x in zip(atual, (q.redF(), q.greenF(), q.blueF())))
        borda = "#003A70" if marcada else "#C9D3DD"
        b.setStyleSheet("QToolButton {{ border-radius: 14px; background: {}; border: 2px solid #FFFFFF; "
                        "outline: 0; }} QToolButton {{ border: {}px solid {}; }}".format(
                            hexcor, 3 if marcada else 1, borda))
        b.setProperty("marcada", marcada)
        b.clicked.connect(lambda _=False, h=hexcor: self._pintar(QtGui.QColor(h)))
        return b

    def _pintar(self, qcor):
        rgb = (qcor.redF(), qcor.greenF(), qcor.blueF())
        doc = self.objs[0].Document if self.objs else None
        if doc is not None:
            doc.openTransaction("Alterar cor")
        for vo in self._vos():
            try:
                pintar(vo, rgb)
            except Exception as exc:
                FreeCAD.Console.PrintWarning("Prumo: cor: {}\n".format(exc))
        if doc is not None:
            doc.commitTransaction()
        objs = list(self.objs)
        QtCore.QTimer.singleShot(0, lambda: self.montar(objs))

    def _outra_cor(self):
        atual = cor_de(self.objs[0].ViewObject) if self.objs else None
        ini = QtGui.QColor.fromRgbF(*atual) if atual else QtGui.QColor("#A7B1BB")
        c = QtWidgets.QColorDialog.getColor(ini, self, "Cor")
        if c.isValid():
            self._pintar(c)

    def _todos(self, prop, valor, rotulo):
        doc = self.objs[0].Document if self.objs else None
        if doc is not None:
            doc.openTransaction("Alterar " + rotulo)
        for vo in self._vos():
            if prop in vo.PropertiesList:
                try:
                    if getattr(vo, prop) != valor:
                        setattr(vo, prop, valor)
                except Exception as exc:
                    FreeCAD.Console.PrintWarning("Prumo: {}: {}\n".format(rotulo, exc))
        if doc is not None:
            doc.commitTransaction()

    def _visibilidade(self, on):
        for o in self.objs:
            try:
                o.ViewObject.Visibility = bool(on)
            except Exception:
                pass

    def _avancado(self):
        import PrumoPainelLateral
        PrumoPainelLateral.abrir_avancado(aba_vista=True)


# ----------------------------------------------------------------------------------- seleção
def selecionados():
    try:
        sel = FreeCADGui.Selection.getSelection()
    except Exception:
        sel = []
    return [o for o in sel if o is not None]


class Observador:
    """Seleção e mudanças no documento → atualiza as abas (com um pequeno atraso para agrupar)."""

    def __init__(self, ao_mudar):
        self.ao_mudar = ao_mudar
        self.t = QtCore.QTimer()
        self.t.setSingleShot(True)
        self.t.setInterval(120)
        self.t.timeout.connect(self._disparar)
        self.mudou_obj = False

    def _agendar(self):
        self.t.start()

    def _disparar(self):
        try:
            self.ao_mudar()
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: painel de propriedades: {}\n".format(exc))

    # seleção
    def addSelection(self, *a):
        self._agendar()

    def removeSelection(self, *a):
        self._agendar()

    def setSelection(self, *a):
        self._agendar()

    def clearSelection(self, *a):
        self._agendar()

    # documento
    def slotChangedObject(self, obj, prop):
        if prop in ("Shape", "Placement", "_GroupTouched", "ExpressionEngine", "Label2"):
            return
        if obj in selecionados():
            self._agendar()

    def slotDeletedObject(self, obj):
        self._agendar()

    def slotDeletedDocument(self, doc):
        self._agendar()

    def slotActivateDocument(self, doc):
        self._agendar()
