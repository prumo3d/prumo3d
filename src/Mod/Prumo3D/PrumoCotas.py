# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - edição rápida das cotas de uma operação, direto na vista 3D.
"""Cotas da operação na tela.

Duplo clique numa face do modelo (ou o comando "Cotas da operação") abre, junto do cursor, um
painel pequeno com as cotas da operação que criou aquela face: comprimento da extrusão, raio do
arredondamento, diâmetro do furo... e as cotas do esboço que a operação usa. Basta mudar o
valor e apertar Enter: o modelo é recalculado. Se o recálculo falhar, o valor anterior volta.
"""

import math

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
TOL = 1e-6

# Propriedades que são "cotas" de cada tipo de operação, em ordem de importância
PROPS_POR_TIPO = {
    "PartDesign::Pad": ["Length", "Length2", "Offset", "TaperAngle", "TaperAngle2"],
    "PartDesign::Pocket": ["Length", "Length2", "Offset", "TaperAngle", "TaperAngle2"],
    "PartDesign::Revolution": ["Angle", "Angle2"],
    "PartDesign::Groove": ["Angle", "Angle2"],
    "PartDesign::Fillet": ["Radius"],
    "PartDesign::Chamfer": ["Size", "Size2", "Angle"],
    "PartDesign::Hole": ["Diameter", "Depth", "CounterboreDiameter", "CounterboreDepth",
                         "CountersinkAngle", "DrillPointAngle"],
    "PartDesign::Thickness": ["Value"],
    "PartDesign::Draft": ["Angle"],
    "PartDesign::LinearPattern": ["Length", "Occurrences"],
    "PartDesign::PolarPattern": ["Angle", "Occurrences"],
    "PartDesign::AdditiveHelix": ["Pitch", "Height", "Turns", "Angle"],
    "PartDesign::SubtractiveHelix": ["Pitch", "Height", "Turns", "Angle"],
    "PartDesign::AdditiveBox": ["Length", "Width", "Height"],
    "PartDesign::SubtractiveBox": ["Length", "Width", "Height"],
    "PartDesign::AdditiveCylinder": ["Radius", "Height", "Angle"],
    "PartDesign::SubtractiveCylinder": ["Radius", "Height", "Angle"],
    "PartDesign::AdditiveSphere": ["Radius"],
    "PartDesign::SubtractiveSphere": ["Radius"],
    "PartDesign::AdditiveCone": ["Radius1", "Radius2", "Height"],
    "PartDesign::SubtractiveCone": ["Radius1", "Radius2", "Height"],
    "PartDesign::AdditiveTorus": ["Radius1", "Radius2"],
    "PartDesign::SubtractiveTorus": ["Radius1", "Radius2"],
    "PartDesign::AdditivePrism": ["Circumradius", "Height", "Polygon"],
    "PartDesign::SubtractivePrism": ["Circumradius", "Height", "Polygon"],
    "PartDesign::AdditiveWedge": ["Xmax", "Ymax", "Zmax"],
    "PartDesign::SubtractiveWedge": ["Xmax", "Ymax", "Zmax"],
    "Part::Box": ["Length", "Width", "Height"],
    "Part::Cylinder": ["Radius", "Height", "Angle"],
    "Part::Sphere": ["Radius"],
    "Part::Cone": ["Radius1", "Radius2", "Height"],
    "Part::Torus": ["Radius1", "Radius2"],
    "Part::Extrusion": ["LengthFwd", "LengthRev", "TaperAngle"],
    "Part::Revolution": ["Angle"],
    "Part::Fillet": [],
    "Part::Thickness": ["Value"],
}

NOMES = {
    "Length": "Comprimento", "Length2": "Comprimento 2", "Offset": "Deslocamento",
    "TaperAngle": "Ângulo de conicidade", "TaperAngle2": "Ângulo de conicidade 2",
    "Angle": "Ângulo", "Angle2": "Ângulo 2", "Radius": "Raio", "Size": "Tamanho",
    "Size2": "Tamanho 2", "Diameter": "Diâmetro", "Depth": "Profundidade",
    "CounterboreDiameter": "Diâmetro do rebaixo", "CounterboreDepth": "Profundidade do rebaixo",
    "CountersinkAngle": "Ângulo do escareado", "DrillPointAngle": "Ângulo da ponta",
    "Value": "Espessura", "Occurrences": "Ocorrências", "Pitch": "Passo", "Height": "Altura",
    "Turns": "Voltas", "Width": "Largura", "Radius1": "Raio 1", "Radius2": "Raio 2",
    "Circumradius": "Raio circunscrito", "Polygon": "Lados", "Xmax": "X máx.", "Ymax": "Y máx.",
    "Zmax": "Z máx.", "LengthFwd": "Comprimento", "LengthRev": "Comprimento (contrário)",
}

TIPOS_OPERACAO = {
    "Pad": "Extrusão", "Pocket": "Cavidade", "Revolution": "Revolução", "Groove": "Ranhura",
    "Fillet": "Arredondamento", "Chamfer": "Chanfro", "Hole": "Furo", "Thickness": "Casca",
    "Draft": "Ângulo de saída", "LinearPattern": "Padrão linear", "PolarPattern": "Padrão circular",
    "Mirrored": "Espelhamento", "AdditiveHelix": "Hélice", "SubtractiveHelix": "Hélice (remove)",
    "AdditiveLoft": "Loft", "SubtractiveLoft": "Loft (remove)", "AdditivePipe": "Varredura",
    "SubtractivePipe": "Varredura (remove)", "AdditiveBox": "Caixa", "AdditiveCylinder": "Cilindro",
    "SubtractiveBox": "Caixa (remove)", "SubtractiveCylinder": "Cilindro (remove)",
    "Box": "Caixa", "Cylinder": "Cilindro", "Sphere": "Esfera", "Cone": "Cone", "Torus": "Toro",
    "Extrusion": "Extrusão", "SketchObject": "Esboço",
}

TIPOS_RESTRICAO = {
    "Distance": "Distância", "DistanceX": "Distância horizontal", "DistanceY": "Distância vertical",
    "Radius": "Raio", "Diameter": "Diâmetro", "Angle": "Ângulo",
}

PROPS_QUANTIDADE = ("App::PropertyLength", "App::PropertyDistance", "App::PropertyAngle",
                    "App::PropertyQuantity", "App::PropertyFloat", "App::PropertyInteger",
                    "App::PropertyIntegerConstraint", "App::PropertyQuantityConstraint",
                    "App::PropertyFloatConstraint")


# ============================================================================ modelo
class Cota:
    """Uma cota editável: propriedade de operação ou restrição de esboço."""

    def __init__(self, obj, rotulo, valor, unidade, prop=None, indice=None, inteiro=False,
                 bloqueada=False, motivo=""):
        self.obj = obj
        self.rotulo = rotulo
        self.valor = valor          # mm, graus ou número puro
        self.unidade = unidade      # "mm", "°" ou ""
        self.prop = prop            # nome da propriedade (operação)
        self.indice = indice        # índice da restrição (esboço)
        self.inteiro = inteiro
        self.bloqueada = bloqueada  # ligada a fórmula: só leitura
        self.motivo = motivo

    def __repr__(self):
        return "Cota(%s.%s=%s%s)" % (self.obj.Name, self.prop if self.prop else self.indice,
                                     self.valor, self.unidade)


def _expressao(obj, prop):
    try:
        for caminho, expr in obj.ExpressionEngine:
            if caminho == prop or caminho == "." + prop:
                return expr
    except Exception:
        pass
    return None


def _visivel(obj, prop):
    try:
        modo = obj.getEditorMode(prop)
    except Exception:
        return True
    return "Hidden" not in modo


def _valor_prop(obj, prop):
    v = getattr(obj, prop)
    tipo = obj.getTypeIdOfProperty(prop)
    if hasattr(v, "Value") and hasattr(v, "Unit"):
        if "Angle" in tipo or str(v.Unit) == str(FreeCAD.Units.Unit("deg")) or v.Unit.Type == "Angle":
            return float(v.getValueAs("deg")), "°", False
        if v.Unit.Type == "Length":
            return float(v.getValueAs("mm")), "mm", False
        return float(v.Value), "", False
    if isinstance(v, bool):
        return None, "", False
    if isinstance(v, int):
        return int(v), "", True
    if isinstance(v, float):
        return float(v), "", False
    return None, "", False


def cotas_de_propriedades(obj):
    """Cotas da própria operação (propriedades), na ordem de PROPS_POR_TIPO."""
    nomes = list(PROPS_POR_TIPO.get(obj.TypeId, []))
    if not nomes and obj.TypeId not in PROPS_POR_TIPO:
        # tipo desconhecido: comprimentos e ângulos visíveis do grupo da própria operação
        for p in obj.PropertiesList:
            if obj.getTypeIdOfProperty(p) in ("App::PropertyLength", "App::PropertyDistance",
                                              "App::PropertyAngle"):
                if obj.getGroupOfProperty(p) not in ("Base", "Attachment", "Part Design", ""):
                    nomes.append(p)
    cotas = []
    for p in nomes:
        if p not in obj.PropertiesList or not _visivel(obj, p):
            continue
        if obj.getTypeIdOfProperty(p) not in PROPS_QUANTIDADE:
            continue
        valor, unidade, inteiro = _valor_prop(obj, p)
        if valor is None:
            continue
        expr = _expressao(obj, p)
        cotas.append(Cota(obj, NOMES.get(p, p), valor, unidade, prop=p, inteiro=inteiro,
                          bloqueada=expr is not None, motivo=("fórmula: " + expr) if expr else ""))
    return cotas


def cotas_de_esboco(sk):
    """Cotas de valor (distâncias, raios, diâmetros, ângulos) de um esboço, que comandam a forma."""
    cotas = []
    for i, c in enumerate(sk.Constraints):
        if c.Type not in TIPOS_RESTRICAO:
            continue
        if not getattr(c, "Driving", True) or not getattr(c, "IsActive", True):
            continue
        if c.Type == "Angle":
            valor, unidade = math.degrees(c.Value), "°"
        else:
            valor, unidade = c.Value, "mm"
        nome = c.Name if c.Name else "Cota %d" % (i + 1)
        expr = _expressao(sk, "Constraints." + c.Name) if c.Name else None
        if expr is None:
            expr = _expressao(sk, ".Constraints[%d]" % i) or _expressao(sk, "Constraints[%d]" % i)
        cotas.append(Cota(sk, "%s — %s" % (nome, TIPOS_RESTRICAO[c.Type].lower()), valor, unidade,
                          indice=i, bloqueada=expr is not None,
                          motivo=("fórmula: " + expr) if expr else ""))
    return cotas


def esbocos_da_operacao(obj):
    res = []
    for nome in ("Profile", "Sections", "Spine"):
        if nome not in obj.PropertiesList:
            continue
        v = getattr(obj, nome)
        itens = v if isinstance(v, list) else [v]
        for it in itens:
            o = it[0] if isinstance(it, tuple) else it
            if o is not None and getattr(o, "TypeId", "") == "Sketcher::SketchObject" and o not in res:
                res.append(o)
    return res


def cotas_da_operacao(obj):
    """Lista (titulo, [Cota]) por grupo: a operação e cada esboço que ela usa."""
    grupos = []
    if obj.TypeId == "Sketcher::SketchObject":
        return [(obj.Label, cotas_de_esboco(obj))]
    proprias = cotas_de_propriedades(obj)
    if proprias:
        grupos.append((obj.Label, proprias))
    for sk in esbocos_da_operacao(obj):
        c = cotas_de_esboco(sk)
        if c:
            grupos.append((sk.Label, c))
    return grupos


def aplicar(cota, valor):
    """Grava o valor (mm, graus ou número) e recalcula. Em caso de falha, volta o valor antigo.

    Retorna (ok, mensagem)."""
    if cota.bloqueada:
        return False, "Esta cota é definida por uma fórmula (%s)." % cota.motivo
    obj = cota.obj
    doc = obj.Document
    antigo = cota.valor
    def ruins():
        return {o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State}

    ja_ruins = ruins()  # objetos já com erro antes da edição não bloqueiam a cota
    doc.openTransaction("Editar cota")
    try:
        _gravar(cota, valor)
        doc.recompute()
        agora = ruins()
        falhas = [doc.getObject(n) for n in sorted(agora - ja_ruins - {obj.Name})]
        if obj.Name in agora:
            falhas.insert(0, obj)  # o próprio objeto editado precisa fechar
        if falhas:
            raise RuntimeError("o modelo não fecha com esse valor (%s)" % falhas[0].Label)
    except Exception as exc:
        try:
            _gravar(cota, antigo)
            doc.recompute()
        except Exception:
            pass
        doc.abortTransaction()
        return False, "Não foi possível usar %s: %s" % (_fmt(valor, cota.unidade), exc)
    doc.commitTransaction()
    cota.valor = valor
    return True, ""


def _gravar(cota, valor):
    if cota.indice is not None:
        q = FreeCAD.Units.Quantity("%r %s" % (float(valor), "deg" if cota.unidade == "°" else "mm"))
        cota.obj.setDatum(cota.indice, q)
        return
    if cota.inteiro:
        setattr(cota.obj, cota.prop, int(round(valor)))
    elif cota.unidade == "°":
        setattr(cota.obj, cota.prop, FreeCAD.Units.Quantity("%r deg" % float(valor)))
    elif cota.unidade == "mm":
        setattr(cota.obj, cota.prop, FreeCAD.Units.Quantity("%r mm" % float(valor)))
    else:
        setattr(cota.obj, cota.prop, float(valor))


def _fmt(v, unidade):
    if isinstance(v, int):
        return str(v)
    txt = ("%.3f" % v).rstrip("0").rstrip(".").replace(".", ",")
    return txt + (" " + unidade if unidade else "")


# ============================================================ face -> operação
def _pontos_internos(face):
    """Alguns pontos dentro da face (o centro de massa pode cair num furo)."""
    try:
        u0, u1, v0, v1 = face.ParameterRange
    except Exception:
        return []
    pts = []
    for fu in (0.5, 0.3, 0.7, 0.15, 0.85):
        for fv in (0.5, 0.3, 0.7, 0.15, 0.85):
            u = u0 + (u1 - u0) * fu
            v = v0 + (v1 - v0) * fv
            try:
                p = face.valueAt(u, v)
                if face.isInside(p, 1e-6, True):
                    pts.append((p, face.normalAt(u, v)))
            except Exception:
                continue
            if len(pts) >= 3:
                return pts
    return pts


def _mesma_superficie(face, outra, pts):
    if not pts:
        return False
    try:
        if face.Surface.__class__ is not outra.Surface.__class__:
            return False
    except Exception:
        return False
    import Part
    for p, _n in pts:
        try:
            d = outra.distToShape(Part.Vertex(p))[0]
        except Exception:
            return False
        if d > 1e-4:
            return False
    return True


def _face_em(shape, face, pts):
    for f in shape.Faces:
        if _mesma_superficie(face, f, pts):
            return True
    return False


def _cadeia(body):
    """Operações do corpo até a ponta (Tip), da última para a primeira."""
    feats = []
    tip = body.Tip
    for o in body.Group:
        if o.isDerivedFrom("PartDesign::Feature"):
            feats.append(o)
        if o == tip:
            break
    return list(reversed(feats))


def operacao_da_face(obj, subnome):
    """Operação que criou a face `subnome` de `obj` (corpo ou operação). None se não achar."""
    if obj is None:
        return None
    body = None
    if obj.TypeId == "PartDesign::Body":
        body = obj
    elif obj.isDerivedFrom("PartDesign::Feature"):
        try:
            import PartDesign  # noqa: F401
            body = obj.getParentGeoFeatureGroup()
        except Exception:
            body = None
    elif obj.isDerivedFrom("Part::Feature"):
        return obj  # objeto do Part: a própria forma
    if body is None or body.TypeId != "PartDesign::Body":
        return obj if obj.isDerivedFrom("PartDesign::Feature") else None
    if not subnome or not subnome.startswith("Face"):
        return obj if obj != body else body.Tip
    try:
        face = obj.Shape.getElement(subnome)
    except Exception:
        return body.Tip
    pts = _pontos_internos(face)
    for feat in _cadeia(body):
        try:
            tool = feat.AddSubShape if "AddSubShape" in feat.PropertiesList else None
            dressup = feat.isDerivedFrom("PartDesign::DressUp") or \
                feat.isDerivedFrom("PartDesign::Transformed")
            if tool is not None and not tool.isNull() and not dressup:
                if _face_em(tool, face, pts):
                    return feat
            else:
                base = feat.BaseFeature
                if not _face_em(feat.Shape, face, pts):
                    continue
                if base is None or not _face_em(base.Shape, face, pts):
                    return feat
        except Exception:
            continue
    return body.Tip


# ============================================================================ painel
class PainelCotas(QtWidgets.QFrame):
    """Painel flutuante com as cotas da operação."""

    def __init__(self, obj, parent=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setObjectName("PrumoPainelCotas")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.obj = obj
        self.campos = []
        import PrumoUI as UI
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        # padrão visual Prumo (cartão branco, título azul, campos com unidade sem setas)
        self.setStyleSheet(UI.qss() + UI.tema("""
            #PrumoPainelCotas { background: #FFFFFF; border: 1px solid #DCE4EC; border-radius: 10px; }
            #PrumoPainelCotas QLabel { background: transparent; color: #1F2A36; }
            #PrumoPainelCotas QLabel#titulo { color: #003A70; font-weight: 700; font-size: 11pt; }
            #PrumoPainelCotas QLabel#grupo { color: #5B6876; font-weight: 600; font-size: 8.5pt; margin-top: 4px; }
            #PrumoPainelCotas QLabel#aviso { background: #FBE9E5; color: #7A2615; border-radius: 8px; padding: 6px 8px; }
        """))
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        tipo = obj.TypeId.split("::")[-1]
        titulo = QtWidgets.QLabel("%s — %s" % (TIPOS_OPERACAO.get(tipo, tipo), obj.Label))
        titulo.setObjectName("titulo")
        lay.addWidget(titulo)
        grupos = cotas_da_operacao(obj)
        if not grupos:
            lay.addWidget(QtWidgets.QLabel("Esta operação não tem cotas editáveis."))
        for nome, cotas in grupos:
            g = QtWidgets.QLabel(nome)
            g.setObjectName("grupo")
            lay.addWidget(g)
            form = QtWidgets.QFormLayout()
            form.setLabelAlignment(QtCore.Qt.AlignRight)
            for c in cotas:
                if c.inteiro:
                    w = QtWidgets.QSpinBox()
                    w.setRange(-100000, 100000)
                    w.setValue(int(c.valor))
                else:
                    w = QtWidgets.QDoubleSpinBox()
                    w.setDecimals(3)
                    w.setRange(-1e7, 1e7)
                    w.setValue(float(c.valor))
                    if c.unidade:
                        w.setSuffix(" " + c.unidade)
                    w.setGroupSeparatorShown(False)
                w.setLocale(QtCore.QLocale(QtCore.QLocale.Portuguese, QtCore.QLocale.Brazil))
                w.setKeyboardTracking(False)
                w.setObjectName("PrumoNum")
                w.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
                w.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                w.setMinimumWidth(120)
                if c.bloqueada:
                    w.setEnabled(False)
                    w.setToolTip(c.motivo)
                w.editingFinished.connect(lambda c=c, w=w: self._aplicar(c, w))
                form.addRow(c.rotulo, w)
                self.campos.append((c, w))
            lay.addLayout(form)
        self.aviso = QtWidgets.QLabel("")
        self.aviso.setObjectName("aviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        lay.addWidget(self.aviso)
        bot = QtWidgets.QHBoxLayout()
        editar = QtWidgets.QPushButton("Editar operação")
        editar.clicked.connect(self._editar)
        fechar = QtWidgets.QPushButton("Fechar")
        fechar.setObjectName("PrumoPrimario")
        fechar.clicked.connect(self.close)
        bot.addWidget(editar)
        bot.addStretch(1)
        bot.addWidget(fechar)
        lay.addLayout(bot)
        if self.campos:
            QtCore.QTimer.singleShot(0, lambda: (self.campos[0][1].setFocus(),
                                                 self.campos[0][1].selectAll()))

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(ev)

    def _aplicar(self, cota, w):
        novo = w.value()
        if (cota.inteiro and int(novo) == int(cota.valor)) or \
                (not cota.inteiro and abs(float(novo) - float(cota.valor)) < 1e-9):
            return
        ok, msg = aplicar(cota, novo)
        if ok:
            self.aviso.hide()
        else:
            w.blockSignals(True)
            w.setValue(cota.valor)
            w.blockSignals(False)
            self.aviso.setText(msg)
            self.aviso.show()
            self.adjustSize()

    def _editar(self):
        try:
            FreeCADGui.ActiveDocument.setEdit(self.obj.Name)
        except Exception:
            pass
        self.close()


_painel = {"atual": None}


def mostrar(obj, pos=None):
    """Abre o painel de cotas de `obj` em `pos` (coordenadas globais) ou junto do cursor."""
    if obj is None:
        return None
    antigo = _painel["atual"]
    if antigo is not None:
        try:
            antigo.close()
        except Exception:
            pass
    p = PainelCotas(obj, FreeCADGui.getMainWindow())
    p.adjustSize()
    if pos is None:
        pos = QtGui.QCursor.pos() + QtCore.QPoint(16, 16)
    tela = QtWidgets.QApplication.screenAt(pos) or QtWidgets.QApplication.primaryScreen()
    if tela is not None:
        r = tela.availableGeometry()
        x = min(max(r.left(), pos.x()), r.right() - p.width())
        y = min(max(r.top(), pos.y()), r.bottom() - p.height())
        pos = QtCore.QPoint(x, y)
    p.move(pos)
    p.show()
    p.raise_()
    p.activateWindow()
    _painel["atual"] = p
    return p


def operacao_da_selecao():
    sel = FreeCADGui.Selection.getSelectionEx()
    if not sel:
        return None
    s = sel[0]
    sub = s.SubElementNames[0] if s.SubElementNames else ""
    obj = s.Object
    # seleção dentro de um corpo/parte: resolver o objeto real
    if sub and "." in sub:
        try:
            alvo = obj.getSubObject(sub, retType=1)
            if alvo is not None:
                obj = alvo
                sub = sub.split(".")[-1]
        except Exception:
            pass
    return operacao_da_face(obj, sub)


# ============================================================ duplo clique na vista 3D
class _FiltroDuploClique(QtCore.QObject):
    def eventFilter(self, alvo, ev):
        if ev.type() == QtCore.QEvent.MouseButtonDblClick and ev.button() == QtCore.Qt.LeftButton:
            try:
                pre = FreeCADGui.Selection.getPreselection()
                if pre.Object is not None and pre.SubElementNames:
                    if _pode_abrir():
                        pos = ev.globalPos() if hasattr(ev, "globalPos") else \
                            ev.globalPosition().toPoint()
                        obj = pre.Object
                        sub = pre.SubElementNames[0]
                        QtCore.QTimer.singleShot(0, lambda: _abrir_por_duplo_clique(obj, sub, pos))
            except Exception as exc:
                FreeCAD.Console.PrintLog("Prumo cotas: %s\n" % exc)
        return False


def _pode_abrir():
    if not FreeCAD.ParamGet(PARAM_PATH).GetBool("CotasDuploClique", True):
        return False
    try:
        if FreeCADGui.Control.activeDialog():
            return False
        gd = FreeCADGui.ActiveDocument
        if gd is not None and gd.getInEdit() is not None:
            return False
    except Exception:
        pass
    return True


def _abrir_por_duplo_clique(obj, sub, pos):
    sub = sub.split(".")[-1]
    if not sub.startswith("Face"):
        return
    op = operacao_da_face(obj, sub)
    if op is not None and cotas_da_operacao(op):
        mostrar(op, pos + QtCore.QPoint(12, 12))


_filtro = {"obj": None}


def _instalar_nas_vistas():
    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtWidgets.QMdiArea) if mw else None
    if mdi is None:
        return
    if _filtro["obj"] is None:
        _filtro["obj"] = _FiltroDuploClique(mw)
    for sw in mdi.subWindowList():
        w = sw.widget()
        if w is None or w.metaObject().className() != "Gui::View3DInventor":
            continue
        for vw in w.findChildren(QtWidgets.QAbstractScrollArea):
            if vw.metaObject().className() == "Gui::View3DInventorViewer":
                vp = vw.viewport()
                # marca no próprio widget (um id() de widget destruído pode ser reaproveitado)
                if not vp.property("prumoCotasFiltro"):
                    vp.installEventFilter(_filtro["obj"])
                    vp.setProperty("prumoCotasFiltro", True)


def install():
    mw = FreeCADGui.getMainWindow()
    mdi = mw.findChild(QtWidgets.QMdiArea) if mw else None
    if mdi is None:
        return
    mdi.subWindowActivated.connect(lambda _sw: QtCore.QTimer.singleShot(0, _instalar_nas_vistas))
    _instalar_nas_vistas()


# ============================================================================ comando
class CmdCotas:
    def GetResources(self):
        import os
        import PrumoGui
        return {"Pixmap": os.path.join(PrumoGui.RES_DIR, "icons", "cotas.svg"),
                "MenuText": "Cotas da operação",
                "ToolTip": "Mostra junto do cursor as cotas da operação selecionada (ou da face "
                           "selecionada) para mudar o valor na hora. Também abre com duplo clique "
                           "numa face do modelo.",
                "Accel": "Shift+D"}

    def IsActive(self):
        return bool(FreeCADGui.Selection.getSelection())

    def Activated(self):
        op = operacao_da_selecao()
        if op is None or not cotas_da_operacao(op):
            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(), "Cotas da operação",
                "Selecione uma face do modelo ou uma operação (extrusão, furo, arredondamento...).")
            return
        mostrar(op)
