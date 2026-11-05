# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: Adicionar / Remover material no próprio painel (como o "Juntar / Cortar" do Fusion e do Onshape).

Errou a escolha entre Extrusão e Cavidade? A chave no topo do painel troca a operação no lugar, sem apagar e
refazer: a operação nova fica na mesma posição do corpo, com o mesmo esboço, as mesmas medidas e fórmulas,
e o que vinha depois (arredondamentos, padrões, fórmulas que citavam a operação) passa a apontar para ela.
Vale para Extrusão ↔ Cavidade, Revolução ↔ Ranhura, Loft, Varredura e Hélice (aditivo ↔ subtrativo).
"""
import re

import FreeCAD

PARES = {
    "PartDesign::Pad": "PartDesign::Pocket",
    "PartDesign::Revolution": "PartDesign::Groove",
    "PartDesign::AdditiveLoft": "PartDesign::SubtractiveLoft",
    "PartDesign::AdditivePipe": "PartDesign::SubtractivePipe",
    "PartDesign::AdditiveHelix": "PartDesign::SubtractiveHelix",
}
PARES.update({v: k for k, v in list(PARES.items())})
ADITIVOS = {"PartDesign::Pad", "PartDesign::Revolution", "PartDesign::AdditiveLoft", "PartDesign::AdditivePipe",
            "PartDesign::AdditiveHelix"}

# propriedades que não se copiam (calculadas, de estrutura do corpo ou só de um dos tipos)
NAO_COPIAR = {"Shape", "BaseFeature", "_Body", "AddSubShape", "Label", "Label2", "ExpressionEngine",
              "Visibility", "Placement", "SuppressedShape", "Suppressed", "AddSubType", "Refine"}
# valores de Type que mudam de nome entre os dois
TIPO_EQUIVALENTE = {("PartDesign::Pad", "UpToLast"): "ThroughAll",
                    ("PartDesign::Pocket", "ThroughAll"): "UpToLast"}


def aditivo(obj):
    return obj.TypeId in ADITIVOS


def pode_trocar(obj):
    return obj is not None and obj.TypeId in PARES


def _corpo(obj):
    try:
        import PartDesign  # noqa: F401
        for o in obj.InList:
            if o.TypeId == "PartDesign::Body":
                return o
    except Exception:
        pass
    return None


def _copiar_propriedades(velho, novo):
    pulados = []
    for nome in velho.PropertiesList:
        if nome in NAO_COPIAR or nome not in novo.PropertiesList:
            continue
        try:
            if "ReadOnly" in velho.getEditorMode(nome) or "Output" in velho.getPropertyStatus(nome):
                continue
        except Exception:
            pass
        valor = getattr(velho, nome)
        try:
            setattr(novo, nome, valor)
        except Exception:
            eq = TIPO_EQUIVALENTE.get((velho.TypeId, valor)) if isinstance(valor, str) else None
            try:
                if eq is None:
                    raise ValueError
                setattr(novo, nome, eq)
            except Exception:
                pulados.append(nome)
    try:
        novo.Refine = velho.Refine
    except Exception:
        pass
    return pulados


def _trocar_nas_ligacoes(o, velho, novo):
    """Aponta para `novo` toda propriedade de ligação de `o` que apontava para `velho`."""
    n = 0
    for nome in o.PropertiesList:
        if nome in ("BaseFeature", "Group", "Tip", "Origin"):
            continue
        try:
            tipo = o.getTypeIdOfProperty(nome)
        except Exception:
            continue
        if "Link" not in tipo:
            continue
        try:
            v = getattr(o, nome)
        except Exception:
            continue
        nv = _trocar_valor(v, velho, novo)
        if nv is not v and nv != v:
            try:
                setattr(o, nome, nv)
                n += 1
            except Exception:
                pass
    return n


def _trocar_valor(v, velho, novo):
    if v is velho or (hasattr(v, "Name") and v == velho):
        return novo
    if isinstance(v, tuple):
        return tuple(_trocar_valor(x, velho, novo) for x in v)
    if isinstance(v, list):
        return [_trocar_valor(x, velho, novo) for x in v]
    return v


def _trocar_nas_formulas(doc, velho, novo):
    """Fórmulas que citavam a operação ("Pad.Length") passam a citar a nova."""
    padrao = re.compile(r"(?<![\w.])%s(?=\.)" % re.escape(velho.Name))
    rotulo = re.compile(r"<<%s>>" % re.escape(velho.Label))
    n = 0
    for o in doc.Objects:
        if o is velho:
            continue
        for caminho, expr in list(getattr(o, "ExpressionEngine", []) or []):
            novo_expr = rotulo.sub("<<%s>>" % novo.Label, padrao.sub(novo.Name, expr))
            if novo_expr != expr:
                try:
                    o.setExpression(caminho, novo_expr)
                    n += 1
                except Exception:
                    pass
    return n


def trocar(velho):
    """Troca a operação pelo par dela (Extrusão ↔ Cavidade etc.) no lugar. Devolve a operação nova."""
    if not pode_trocar(velho):
        raise ValueError("%s não tem par para trocar" % velho.Label)
    doc = velho.Document
    corpo = _corpo(velho)
    if corpo is None:
        raise ValueError("%s não está num corpo" % velho.Label)
    tipo_novo = PARES[velho.TypeId]
    base = tipo_novo.split("::")[1]
    rotulo_padrao = re.match(r"^(%s)\d*$" % "|".join(re.escape(x) for x in (
        velho.TypeId.split("::")[1], "Extrusão", "Cavidade", "Revolução", "Ranhura")), velho.Label or "")
    dependentes = [o for o in velho.InList if o is not corpo]
    doc.openTransaction("Trocar operação")
    try:
        novo = doc.addObject(tipo_novo, base)
        corpo.insertObject(novo, velho, True)
        _copiar_propriedades(velho, novo)
        for caminho, expr in list(velho.ExpressionEngine or []):
            try:
                novo.setExpression(caminho, expr)
            except Exception:
                pass
        if not rotulo_padrao:
            rot = velho.Label
            velho.Label = rot + "_antigo"
            novo.Label = rot          # nome dado pela pessoa fica
        for o in dependentes:
            if o is not novo:
                _trocar_nas_ligacoes(o, velho, novo)
        _trocar_nas_formulas(doc, velho, novo)
        if corpo.Tip == velho:
            corpo.Tip = novo
        try:
            novo.ViewObject.Visibility = bool(velho.ViewObject.Visibility)
            for attr in ("ShapeAppearance", "LineColor", "PointColor", "Transparency"):
                if hasattr(velho.ViewObject, attr):
                    setattr(novo.ViewObject, attr, getattr(velho.ViewObject, attr))
        except Exception:
            pass
        corpo.removeObject(velho)
        doc.removeObject(velho.Name)
        doc.recompute()
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    return novo


# ------------------------------------------------------------------ chave no painel
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtWidgets

    def _botao_ok():
        mw = FreeCADGui.getMainWindow()
        # só o OK do painel de tarefas: outro OK visível na janela (ex.: tela inicial) abriria outra coisa
        vistas = [w for w in mw.findChildren(QtWidgets.QWidget)
                  if w.metaObject().className() == "Gui::TaskView::TaskView" and w.isVisible()]
        caixas = [c for v in vistas for c in v.findChildren(QtWidgets.QDialogButtonBox)]
        for caixa in caixas:
            if not caixa.isVisible():
                continue
            b = caixa.button(QtWidgets.QDialogButtonBox.Ok)
            if b is not None and b.isVisible() and b.isEnabled():
                return b
        return None

    def trocar_em_edicao(obj):
        """Do painel aberto: conclui (OK), troca e reabre o painel na operação nova."""
        nome, doc = obj.Name, obj.Document
        ok = _botao_ok()
        if ok is not None:
            ok.click()
        else:
            try:
                FreeCADGui.getDocument(doc.Name).resetEdit()
            except Exception:
                pass
        import time
        gdoc = FreeCADGui.getDocument(doc.Name)
        fim = time.time() + 3
        while True:  # o OK fecha o painel no próximo giro de eventos
            QtWidgets.QApplication.processEvents()
            try:
                if gdoc.getInEdit() is None or time.time() > fim:
                    break
            except Exception:
                break
            time.sleep(0.02)
        velho = doc.getObject(nome)
        if velho is None:
            return None
        try:
            if FreeCADGui.getDocument(doc.Name).getInEdit() is not None:
                import PrumoAvisoClique as AV
                AV.mostrar("Não deu para trocar: conclua ou corrija a operação antes (o painel não fechou).",
                           "erro")
                return None
        except Exception:
            pass
        try:
            novo = trocar(velho)
        except Exception as exc:
            import PrumoAvisoClique as AV
            AV.mostrar("Não deu para trocar a operação: %s" % exc, "erro")
            return None
        doc_nome, novo_nome = doc.Name, novo.Name

        def reabrir():
            # o documento da peça (não o "ativo", que pode ser outro aberto ao lado)
            try:
                gd = FreeCADGui.getDocument(doc_nome)
                FreeCADGui.setActiveDocument(doc_nome)
                gd.setEdit(novo_nome, 0)
            except Exception:
                pass
        QtCore.QTimer.singleShot(0, reabrir)
        return novo

    def cartao(obj, parent=None):
        """Cartão "Operação" com Adicionar / Remover material para o topo do painel."""
        import PrumoUI as UI
        c = UI.Cartao("Operação", "acabamento")
        seg = UI.Segmentado([("add", "Adicionar material", "seta_cima"),
                             ("rem", "Remover material", "seta_baixo")],
                            "add" if aditivo(obj) else "rem", colunas=2)
        nome, doc_nome = obj.Name, obj.Document.Name

        def mudou(k):
            o = FreeCAD.getDocument(doc_nome).getObject(nome)
            if o is None or (k == "add") == aditivo(o):
                return
            QtCore.QTimer.singleShot(0, lambda: trocar_em_edicao(o))
        seg.mudou.connect(mudou)
        c.widget(seg)
        dica = QtWidgets.QLabel("Troca no lugar: mesmo esboço, medidas e posição na árvore.")
        dica.setObjectName("PrumoSub")
        dica.setWordWrap(True)
        c.widget(dica)
        c.setObjectName("PrumoCartaoOperacao")
        if parent is not None:
            c.setParent(parent)
        return c
