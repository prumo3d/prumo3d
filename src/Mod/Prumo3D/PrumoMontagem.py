# SPDX-License-Identifier: LGPL-2.1-or-later
"""Montagem: restrições com os nomes do SolidWorks que faltavam e padrão de componentes.

- Tangente: a junta "Distância" do FreeCAD com 0 entre uma face curva (cilindro, esfera, cone, toro) e outra
  face (plana ou curva) já é tangência no solver; faltava o botão e a conferência das faces.
- Coincidente: a mesma junta com 0, com o nome que se procura (faces, arestas ou pontos encostados).
- Padrão de componentes (linear e circular): cópias ligadas (App::Link) do componente, com o Placement amarrado
  ao do original por expressão: mexeu no original, as cópias acompanham.
"""

import math

import FreeCAD

try:
    import FreeCADGui
except ImportError:  # pragma: no cover
    FreeCADGui = None


CURVAS = ("Cylinder", "Sphere", "Cone", "Toroid", "SurfaceOfRevolution")
NOMES_SUP = {"Plane": "plana", "Cylinder": "cilíndrica", "Sphere": "esférica", "Cone": "cônica",
             "Toroid": "tórica", "SurfaceOfRevolution": "de revolução"}


# ----------------------------------------------------------------------------------- tangência
def tipo_do_elemento(obj, elemento):
    """'Plane', 'Cylinder'… para faces; 'Edge'/'Vertex' para arestas e pontos; None se não achou."""
    if not elemento:
        return None
    if elemento.startswith("Edge"):
        return "Edge"
    if elemento.startswith("Vertex"):
        return "Vertex"
    try:
        f = obj.getSubObject(elemento)
        return type(f.Surface).__name__
    except Exception:
        return None


def conferir_tangente(tipos):
    """Mensagem do que está errado para uma tangência (None = pode)."""
    tipos = [t for t in tipos if t]
    if len(tipos) < 2:
        return "Escolha uma face em cada peça."
    if any(t in ("Edge", "Vertex") for t in tipos):
        return ("Tangente é entre faces: escolha uma face curva (cilindro, esfera, cone) e outra face, plana ou "
                "curva.")
    if not any(t in CURVAS for t in tipos):
        return "As duas faces são planas: para encostar faces planas use Coincidente."
    return None


def _tipos_das_refs(refs):
    import UtilsAssembly
    tipos = []
    for ref in refs or []:
        try:
            obj = UtilsAssembly.getObject(ref)
            el = UtilsAssembly.getElementName(ref[1][0])
            tipos.append(tipo_do_elemento(obj, el))
        except Exception:
            tipos.append(None)
    return tipos


JUNTAS = {
    "tangente": ("Tangente", "Tangente: face curva encostada (tangente) em outra face. Distância = folga entre "
                             "as superfícies."),
    "coincidente": ("Coincidente", "Coincidente: faces, arestas ou pontos encostados (distância zero)."),
}


def iniciar_junta(chave):
    """Abre o painel da junta Distância com o nome e a conferência da restrição pedida."""
    import CommandCreateJoint
    import JointObject
    rotulo, _dica = JUNTAS[chave]
    CommandCreateJoint.activateJoint(JointObject.JointTypes.index("Distance"))
    task = JointObject.activeTask
    if task is None or not getattr(task, "creating", False) or getattr(task, "joint", None) is None:
        return None
    task.jointName = rotulo
    try:
        task.joint.Label = rotulo
        if "PrumoRestricao" not in task.joint.PropertiesList:
            task.joint.addProperty("App::PropertyString", "PrumoRestricao", "Prumo", "Restrição pedida")
            task.joint.setEditorMode("PrumoRestricao", 1)
        task.joint.PrumoRestricao = chave
        task.joint.Distance = 0.0
    except Exception:
        pass
    original = task.accept

    def accept():
        if chave == "tangente" and getattr(task, "jType", "Distance") == "Distance":
            msg = conferir_tangente(_tipos_das_refs(getattr(task, "refs", [])))
            if msg:
                _avisar(task, msg)
                return False
        return original()

    task.accept = accept
    task.prumo_restricao = chave
    return task


def _avisar(task, msg):
    FreeCAD.Console.PrintWarning("Prumo: %s\n" % msg)
    try:
        from PySide import QtWidgets
        lb = getattr(task, "_prumo_aviso", None)
        if lb is None:
            import PrumoPainel as P
            lb = P.Mensagem(msg)
            task.form.layout().insertWidget(0, lb)
            task._prumo_aviso = lb
        lb.mostrar(msg, "erro") if hasattr(lb, "mostrar") else lb.setText(msg)
        lb.setVisible(True)
        QtWidgets.QApplication.processEvents()
    except Exception:
        pass
    task.ultimo_aviso = msg


# ----------------------------------------------------------------------------------- padrão de componentes
def montagem_de(obj):
    for p in obj.InList:
        if p.TypeId == "Assembly::AssemblyObject":
            return p
    return None


def _num(v):
    return ("%.9g" % float(v)).replace(",", ".")


def _expr_placement(base, rot_eixo, rot_ang, nome_original):
    """Expressão: Placement fixo (deslocamento + giro) aplicado sobre o Placement do original."""
    return ("create(<<placement>>; create(<<vector>>; {bx}; {by}; {bz}); create(<<rotation>>; "
            "create(<<vector>>; {ax}; {ay}; {az}); {ang})) * {orig}.Placement").format(
        bx=_num(base.x), by=_num(base.y), bz=_num(base.z), ax=_num(rot_eixo.x), ay=_num(rot_eixo.y),
        az=_num(rot_eixo.z), ang=_num(rot_ang), orig=nome_original)


def transformacoes(tipo, quantidade, passo=0.0, direcao=None, eixo_ponto=None, eixo_dir=None, angulo_total=360.0):
    """[Placement] de cada cópia (sem a original), no sistema da montagem."""
    res = []
    n = int(quantidade)
    if tipo == "linear":
        d = FreeCAD.Vector(direcao or FreeCAD.Vector(1, 0, 0))
        if d.Length < 1e-12:
            raise ValueError("Direção inválida.")
        d.normalize()
        for k in range(1, n):
            res.append(FreeCAD.Placement(d * (passo * k), FreeCAD.Rotation()))
    else:
        c = FreeCAD.Vector(eixo_ponto or FreeCAD.Vector())
        a = FreeCAD.Vector(eixo_dir or FreeCAD.Vector(0, 0, 1))
        if a.Length < 1e-12:
            raise ValueError("Eixo inválido.")
        a.normalize()
        cheio = abs(abs(angulo_total) - 360.0) < 1e-9
        div = n if cheio else max(n - 1, 1)
        for k in range(1, n):
            ang = angulo_total * k / div
            r = FreeCAD.Rotation(a, ang)
            res.append(FreeCAD.Placement(c - r.multVec(c), r))
    return res


class PadraoComponentes:
    """Objeto do padrão (fica na raiz do documento): guarda o original, as cópias e os parâmetros."""

    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, dica, valor=None):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, "Padrão", dica)
                if valor is not None:
                    setattr(obj, nome, valor)
        add("App::PropertyLink", "Original", "Componente repetido")
        add("App::PropertyLinkListHidden", "Copias", "Cópias criadas pelo padrão")
        add("App::PropertyEnumeration", "Tipo", "Linear ou circular")
        if not obj.Tipo:
            obj.Tipo = ["Linear", "Circular"]
        add("App::PropertyInteger", "Quantidade", "Total de componentes, contando o original", 3)
        add("App::PropertyLength", "Espacamento", "Distância entre as cópias (linear)", 50.0)
        add("App::PropertyVector", "Direcao", "Direção (linear), no sistema da montagem", FreeCAD.Vector(1, 0, 0))
        add("App::PropertyVector", "EixoPonto", "Ponto do eixo (circular)", FreeCAD.Vector())
        add("App::PropertyVector", "EixoDirecao", "Direção do eixo (circular)", FreeCAD.Vector(0, 0, 1))
        add("App::PropertyAngle", "AnguloTotal", "Ângulo coberto (circular); 360 = volta inteira", 360.0)

    def onDocumentRestored(self, obj):
        self._props(obj)

    def dumps(self):
        return None

    def loads(self, state):
        return None

    def execute(self, obj):
        atualizar(obj)


def atualizar(obj):
    """Ajusta o número de cópias e as expressões de posição."""
    orig = obj.Original
    if orig is None:
        return
    asm = montagem_de(orig)
    if asm is None:
        raise ValueError("O componente não está numa montagem.")
    trs = transformacoes("linear" if obj.Tipo == "Linear" else "circular", max(1, obj.Quantidade),
                         float(obj.Espacamento), obj.Direcao, obj.EixoPonto, obj.EixoDirecao, float(obj.AnguloTotal))
    copias = [c for c in obj.Copias if c is not None and c.isValid()]
    doc = obj.Document
    alvo = getattr(orig, "LinkedObject", None) if orig.TypeId == "App::Link" else orig
    while len(copias) < len(trs):
        c = doc.addObject("App::Link", "Copia")
        c.LinkedObject = alvo
        asm.addObject(c)
        copias.append(c)
    while len(copias) > len(trs):
        c = copias.pop()
        try:
            c.setExpression("Placement", None)
            doc.removeObject(c.Name)
        except Exception:
            pass
    for k, (c, pl) in enumerate(zip(copias, trs), start=2):
        r = pl.Rotation
        eixo, ang = r.Axis, math.degrees(r.Angle)
        c.setExpression("Placement", _expr_placement(pl.Base, eixo, ang, orig.Name))
        c.Placement = pl.multiply(orig.Placement)    # já certo agora (a expressão vale no próximo recálculo)
        c.Label = "%s (%d)" % (orig.Label, k)
        try:
            if FreeCAD.GuiUp and orig.ViewObject is not None and c.ViewObject is not None:
                c.ViewObject.ShapeAppearance = orig.ViewObject.ShapeAppearance
        except Exception:
            pass
    obj.Copias = copias


def criar_padrao(original, tipo="linear", quantidade=3, espacamento=50.0, direcao=None, eixo_ponto=None,
                 eixo_dir=None, angulo_total=360.0):
    doc = original.Document
    if montagem_de(original) is None:
        raise ValueError("Escolha um componente que está dentro de uma montagem.")
    if int(quantidade) < 2:
        raise ValueError("A quantidade tem de ser pelo menos 2 (o original e uma cópia).")
    if tipo == "linear" and float(espacamento) <= 0:
        raise ValueError("O espaçamento tem de ser maior que zero.")
    obj = doc.addObject("App::FeaturePython", "PadraoComponentes")
    PadraoComponentes(obj)
    obj.Label = "Padrão de %s" % original.Label
    obj.Original = original
    obj.Tipo = "Linear" if tipo == "linear" else "Circular"
    obj.Quantidade = int(quantidade)
    obj.Espacamento = float(espacamento)
    if direcao is not None:
        obj.Direcao = FreeCAD.Vector(direcao)
    if eixo_ponto is not None:
        obj.EixoPonto = FreeCAD.Vector(eixo_ponto)
    if eixo_dir is not None:
        obj.EixoDirecao = FreeCAD.Vector(eixo_dir)
    obj.AnguloTotal = float(angulo_total)
    if FreeCAD.GuiUp:
        VPPadrao(obj.ViewObject)
    doc.recompute()
    return obj


def componente_do_caminho(raiz, caminho):
    """O componente da montagem dono do que foi clicado: o primeiro objeto do caminho que está direto dentro de
    uma montagem (para uma peça ligada, o próprio vínculo, não a peça de dentro)."""
    cands = [raiz]
    partes = [p for p in (caminho or "").split(".")]
    for i in range(len(partes) - 1):
        try:
            o = raiz.getSubObject(".".join(partes[:i + 1]) + ".", retType=1)
        except Exception:
            o = None
        if o is not None:
            cands.append(o)
    for o in cands:
        if o.TypeId.startswith("Assembly::") or o.TypeId == "App::FeaturePython":
            continue
        if montagem_de(o) is not None:
            return o
    return None


def eixo_de_elemento(obj_raiz, caminho):
    """(ponto, direção) globais de uma aresta reta, aresta circular ou face cilíndrica/plana."""
    try:
        sh = obj_raiz.getSubObject(caminho)       # já na posição global (com o Placement do caminho)
    except Exception:
        sh = None
    if sh is None:
        return None
    if getattr(sh, "ShapeType", "") == "Edge":
        cv = sh.Curve
        n = type(cv).__name__
        if n in ("Line", "LineSegment"):
            p0, p1 = sh.Vertexes[0].Point, sh.Vertexes[-1].Point
            return p0, (p1 - p0)
        if n in ("Circle", "ArcOfCircle"):
            return cv.Center, cv.Axis
    if getattr(sh, "ShapeType", "") == "Face":
        s = sh.Surface
        n = type(s).__name__
        if n == "Cylinder":
            return s.Center, s.Axis
        if n == "Plane":
            return sh.CenterOfMass, sh.normalAt(0, 0)
    return None


# ----------------------------------------------------------------------------------- interface
if FreeCAD.GuiUp:
    try:
        from PySide import QtWidgets
    except ImportError:  # pragma: no cover
        from PySide2 import QtWidgets
    import PrumoPainel as P

    class VPPadrao:
        def __init__(self, vobj):
            vobj.Proxy = self

        def attach(self, vobj):
            self.Object = vobj.Object

        def getIcon(self):
            import PrumoUtil
            return PrumoUtil.icone("padrao_componentes.svg")

        def claimChildren(self):
            return []

        def doubleClicked(self, vobj):
            PainelPadrao(editar=vobj.Object).mostrar()
            return True

        def dumps(self):
            return None

        def loads(self, state):
            return None

    def _filtro_componente(raiz, caminhos):
        res = []
        for c in (caminhos or ("",)):
            o = componente_do_caminho(raiz, c)
            if o is not None and all(o is not v for _t, v in res):
                res.append((o.Label, o))
        return res

    _filtro_componente.caminho_completo = True

    def _filtro_referencia(raiz, caminhos):
        res = []
        for c in caminhos:
            r = eixo_de_elemento(raiz, c)
            if r is not None:
                res.append(("%s (%s)" % (c.split(".")[-1].replace("Edge", "aresta ").replace("Face", "face "),
                                         raiz.Label), r))
        return res

    _filtro_referencia.caminho_completo = True

    class PainelPadrao(P.PainelTarefa):
        titulo = "Padrão de componentes"
        previa = True
        ajuda = ("Escolha o componente e, se quiser, uma aresta ou face que dá a direção (linear) ou o eixo "
                 "(circular). Sem referência: eixo X da montagem (linear) ou eixo Z (circular).")

        def __init__(self, editar=None):
            self._editar = editar
            super().__init__()
            if editar is not None:
                self.editar_objeto(editar)

        def montar(self):
            f = self.form
            s0 = f.secao("O que repetir", "selecao")
            self.comp = f.caixa(s0, "Componente", _filtro_componente, minimo=1, maximo=1,
                                dica="Uma peça da montagem (ou um parafuso, uma porca...).")
            self.ref = f.caixa(s0, "Direção / eixo (opcional)", _filtro_referencia, minimo=0, maximo=1,
                               dica="Aresta reta ou face plana: direção. Aresta circular ou face cilíndrica: eixo.")
            self.comp.mudou.connect(lambda: self.comp.pronta() and self.comp.ativa and
                                    self.form.ativar_caixa(self.ref))
            s1 = f.secao("Padrão", "quantidade")
            self.tipo = P.Opcoes([("linear", "Linear", "comprimento", "Em linha, com espaçamento fixo"),
                                  ("circular", "Circular", "angulo", "Em volta de um eixo")])
            s1.widget(self.tipo)
            self.qtd = QtWidgets.QSpinBox()
            self.qtd.setRange(2, 500)
            self.qtd.setValue(4)
            s1.linha("quantidade", self.qtd, "Total, contando o original.", "Quantidade")
            self.passo = s1.linha("comprimento", P.numero(50.0, 0.01, 1e6), "Distância de uma cópia à próxima.",
                                  "Espaçamento")
            self.angulo = s1.linha("angulo", P.numero(360.0, 1.0, 360.0, "°"), "360° = distribuídas na volta "
                                   "inteira; menos que isso = do primeiro ao último dentro do ângulo.", "Ângulo total")
            self.eixo = P.lista(["X", "Y", "Z"], "X")
            s1.linha("posicao", self.eixo, "Usado quando não há referência escolhida.", "Eixo da montagem")
            self.inverter = P.marcar("Inverter o sentido", False)
            s1.widget(self.inverter)
            self.tipo.mudou.connect(self._tipo)
            self._tipo(self.tipo.valor())

        def _tipo(self, t):
            lin = t == "linear"
            self.passo.setEnabled(lin)
            self.angulo.setEnabled(not lin)
            atual = self.eixo.currentText()
            if not self.ref.valores():
                self.eixo.setCurrentText("X" if lin and atual == "Z" else ("Z" if not lin and atual == "X" else atual))

        def pendencia(self):
            falta = super().pendencia()
            if falta:
                return "Escolha o componente que vai ser repetido."
            return None

        def pronto_texto(self):
            return "Pronto: %d componentes (o original e %d cópias)." % (self.qtd.value(), self.qtd.value() - 1)

        def parametros(self):
            t = self.tipo.valor()
            refs = self.ref.valores()
            e = FreeCAD.Vector(*{"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[self.eixo.currentText()])
            ponto, direcao = FreeCAD.Vector(), e
            if refs:
                ponto, direcao = refs[0]
            direcao = FreeCAD.Vector(direcao)
            if self.inverter.isChecked():
                direcao = direcao * -1.0
            return dict(tipo=t, quantidade=self.qtd.value(), espacamento=self.passo.value(), direcao=direcao,
                        eixo_ponto=ponto, eixo_dir=direcao, angulo_total=self.angulo.value())

        def carregar(self, obj):
            if obj.Original is not None:
                self.comp.aceitar(obj.Original)
            self.tipo.definir("linear" if obj.Tipo == "Linear" else "circular")
            self.qtd.setValue(obj.Quantidade)
            self.passo.setValue(float(obj.Espacamento))
            self.angulo.setValue(float(obj.AnguloTotal))
            self._dir_salva = (FreeCAD.Vector(obj.EixoPonto), FreeCAD.Vector(obj.Direcao if obj.Tipo == "Linear"
                                                                              else obj.EixoDirecao))

        def props_edicao(self):
            p = self.parametros()
            if not self.ref.valores() and getattr(self, "_dir_salva", None) is not None:
                p["eixo_ponto"], p["direcao"] = self._dir_salva
                p["eixo_dir"] = p["direcao"]
            return {"Tipo": "Linear" if p["tipo"] == "linear" else "Circular", "Quantidade": p["quantidade"],
                    "Espacamento": p["espacamento"], "Direcao": p["direcao"], "EixoPonto": p["eixo_ponto"],
                    "EixoDirecao": p["eixo_dir"], "AnguloTotal": p["angulo_total"]}

        def executar(self):
            return [criar_padrao(self.comp.valores()[0], **self.parametros())]

    class CmdJunta:
        def __init__(self, chave, icone):
            self.chave = chave
            self.icone = icone

        def GetResources(self):
            rot, dica = JUNTAS[self.chave]
            return {"Pixmap": self.icone, "MenuText": rot, "ToolTip": dica}

        def IsActive(self):
            try:
                import UtilsAssembly
                return UtilsAssembly.activeAssembly() is not None
            except Exception:
                return False

        def Activated(self):
            iniciar_junta(self.chave)

    class CmdPadrao:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("padrao_componentes.svg"), "MenuText": "Padrão de componentes",
                    "ToolTip": "Repete um componente da montagem em linha ou em volta de um eixo; as cópias "
                               "acompanham o original."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelPadrao().mostrar()

    def registrar_comandos():
        try:
            import Draft_rc  # noqa: F401  (ícones das matrizes)
        except Exception:
            pass
        import PrumoUtil
        FreeCADGui.addCommand("Prumo_JuntaTangente", CmdJunta("tangente", PrumoUtil.icone("junta_tangente.svg")))
        FreeCADGui.addCommand("Prumo_JuntaCoincidente",
                              CmdJunta("coincidente", PrumoUtil.icone("junta_coincidente.svg")))
        FreeCADGui.addCommand("Prumo_PadraoComponentes", CmdPadrao())
