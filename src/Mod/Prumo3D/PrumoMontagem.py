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
        if task.prumo_restricao == "tangente" and getattr(task, "jType", "Distance") == "Distance":
            msg = conferir_tangente(_tipos_das_refs(getattr(task, "refs", [])))
            if msg:
                conserto = None
                if "Coincidente" in msg:
                    # o erro já traz o conserto: as mesmas faces, como Coincidente
                    conserto = ("Usar Coincidente", lambda: _trocar_e_gravar(task, "coincidente", original))
                _avisar(task, msg, conserto)
                return False
        return original()

    task.accept = accept
    task.prumo_restricao = chave
    asm = getattr(task, "assembly", None)
    if asm is not None and not pecas_fixas(asm):
        comps = [o for o in asm.Group if o.TypeId != "Assembly::JointGroup" and hasattr(o, "Placement")
                 and not o.TypeId.startswith("Assembly::")]
        if comps:
            _avisar(task, "Nenhuma peça está fixa: ao resolver, a montagem inteira pode se mover.",
                    ("Fixar %s" % comps[0].Label, lambda: _fixar(task, asm, comps[0])), tipo="info")
    return task


def pecas_fixas(asm):
    """Componentes fixos da montagem (juntas "Fixar peça")."""
    try:
        import UtilsAssembly
        grupo = UtilsAssembly.getJointGroup(asm)
        return [g.ObjectToGround for g in grupo.Group if getattr(g, "ObjectToGround", None) is not None]
    except Exception:
        return []


def _fixar(task, asm, comp):
    import JointObject
    import UtilsAssembly
    grupo = UtilsAssembly.getJointGroup(asm)
    g = grupo.newObject("App::FeaturePython", "Fixa")
    JointObject.GroundedJoint(g, comp)
    if FreeCAD.GuiUp:
        try:
            JointObject.ViewProviderGroundedJoint(g.ViewObject)
        except Exception:
            pass
    asm.Document.recompute()
    lb = getattr(task, "_prumo_aviso", None)
    if lb is not None:
        lb.mostrar("%s está fixa: as outras peças se ajustam a ela." % comp.Label, "ok")
        bt = getattr(task, "_prumo_conserto", None)
        if bt is not None:
            bt.setVisible(False)
    return g


def _trocar_e_gravar(task, chave, original):
    """Troca a restrição do painel aberto (ex.: Tangente -> Coincidente) e grava."""
    rotulo, _d = JUNTAS[chave]
    task.prumo_restricao = chave
    task.jointName = rotulo
    try:
        task.joint.Label = rotulo
        task.joint.PrumoRestricao = chave
    except Exception:
        pass
    ok = original()
    FreeCAD.Console.PrintLog("Prumo: troca para %s gravada: %s\n" % (rotulo, ok))
    if ok:
        # fecha depois que o clique do botão (que está dentro do painel) terminar
        from PySide import QtCore
        QtCore.QTimer.singleShot(0, FreeCADGui.Control.closeDialog)
        return True
    return False


def _avisar(task, msg, conserto=None, tipo="erro"):
    """Mensagem no alto do painel da junta; com conserto=(texto, função), um botão que resolve na hora."""
    FreeCAD.Console.PrintWarning("Prumo: %s\n" % msg)
    try:
        from PySide import QtWidgets
        lb = getattr(task, "_prumo_aviso", None)
        if lb is None:
            import PrumoPainel as P
            lb = P.Mensagem(msg)
            task.form.layout().insertWidget(0, lb)
            task._prumo_aviso = lb
        lb.mostrar(msg, tipo) if hasattr(lb, "mostrar") else lb.setText(msg)
        lb.setVisible(True)
        bt = getattr(task, "_prumo_conserto", None)
        if conserto is not None:
            if bt is None:
                bt = QtWidgets.QPushButton()
                bt.setObjectName("PrumoConserto")
                task.form.layout().insertWidget(1, bt)
                task._prumo_conserto = bt
            try:
                bt.clicked.disconnect()
            except Exception:
                pass
            bt.setText(conserto[0])
            bt.clicked.connect(lambda *_a, f=conserto[1]: f())
            bt.setVisible(True)
        elif bt is not None:
            bt.setVisible(False)
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


# ----------------------------------------------------------------------------------- mover junta
# juntas que têm um movimento livre para "pilotar" (como o Drive Joints do Fusion/SolidCraft):
# giro (graus) em torno do eixo z da junta e/ou avanço (mm) ao longo dele
MOVIMENTOS = {"Revolute": ("giro",), "Slider": ("avanco",), "Cylindrical": ("giro", "avanco")}


def juntas_moveis(asm):
    """Juntas da montagem que se podem mover (dobradiça, deslizante, concêntrica)."""
    try:
        import UtilsAssembly
        grupo = UtilsAssembly.getJointGroup(asm)
    except Exception:
        grupo = None
    if grupo is None:
        return []
    return [j for j in grupo.Group if getattr(j, "JointType", "") in MOVIMENTOS
            and not getattr(j, "Suppressed", False) and j.Reference1 and j.Reference2]


def _jcs(j):
    import UtilsAssembly
    return (UtilsAssembly.getJcsGlobalPlc(j.Placement1, j.Reference1),
            UtilsAssembly.getJcsGlobalPlc(j.Placement2, j.Reference2))


def valores_da_junta(j):
    """{"giro": graus, "avanco": mm} atuais da junta (o lado 2 em relação ao lado 1)."""
    p1, p2 = _jcs(j)
    rel = p1.inverse() * p2
    x = rel.Rotation.multVec(FreeCAD.Vector(1, 0, 0))
    r = {}
    for k in MOVIMENTOS[j.JointType]:
        r[k] = math.degrees(math.atan2(x.y, x.x)) if k == "giro" else rel.Base.z
    return r


def limites_da_junta(j):
    """{"giro": (min, max), "avanco": (min, max)}; None onde não há limite."""
    r = {}
    for k in MOVIMENTOS[j.JointType]:
        if k == "giro":
            r[k] = (float(j.AngleMin) if getattr(j, "EnableAngleMin", False) else None,
                    float(j.AngleMax) if getattr(j, "EnableAngleMax", False) else None)
        else:
            r[k] = (float(j.LengthMin) if getattr(j, "EnableLengthMin", False) else None,
                    float(j.LengthMax) if getattr(j, "EnableLengthMax", False) else None)
    return r


def _aterrados(asm):
    try:
        import UtilsAssembly
        grupo = UtilsAssembly.getJointGroup(asm)
        return {getattr(g, "ObjectToGround", None) for g in grupo.Group if hasattr(g, "ObjectToGround")}
    except Exception:
        return set()


def _global_da_montagem(asm):
    try:
        return asm.getGlobalPlacement()
    except Exception:
        return asm.Placement


def mover_junta(j, giro=None, avanco=None):
    """Leva a junta ao giro (graus) / avanço (mm) pedido, dentro dos limites, e resolve a montagem.

    Gira/empurra a peça do lado 2 em torno do eixo da junta (ou a do lado 1, se a 2 estiver fixa) e deixa o
    solver acertar o resto da cadeia. Devolve os valores alcançados."""
    asm = montagem_de(j.Reference1[0]) or montagem_de(j.Reference2[0])
    if asm is None:
        raise ValueError("A junta não está numa montagem.")
    atual = valores_da_junta(j)
    lim = limites_da_junta(j)
    pedido = {"giro": giro, "avanco": avanco}
    delta = {}
    for k in MOVIMENTOS[j.JointType]:
        v = pedido[k]
        if v is None:
            continue
        lo, hi = lim[k]
        if lo is not None:
            v = max(v, lo)
        if hi is not None:
            v = min(v, hi)
        d = v - atual[k]
        if k == "giro":
            d = (d + 180.0) % 360.0 - 180.0    # o caminho mais curto
        delta[k] = d
    if not any(abs(d) > 1e-9 for d in delta.values()):
        return atual
    p1, _p2 = _jcs(j)
    eixo = p1.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    terra = _aterrados(asm)
    peca, sinal = j.Reference2[0], 1.0
    if peca in terra:
        peca, sinal = j.Reference1[0], -1.0
    if peca in terra:
        raise ValueError("As duas peças da junta estão fixas: não há o que mover.")
    T = FreeCAD.Placement()
    if delta.get("giro"):
        T = FreeCAD.Placement(FreeCAD.Vector(), FreeCAD.Rotation(eixo, sinal * delta["giro"]), p1.Base) * T
    if delta.get("avanco"):
        T = FreeCAD.Placement(eixo * (sinal * delta["avanco"]), FreeCAD.Rotation()) * T
    g = _global_da_montagem(asm)
    outra = j.Reference1[0] if peca is j.Reference2[0] else j.Reference2[0]
    for p in _carona(asm, peca, j, terra | {outra}):
        p.Placement = g.inverse() * T * g * p.Placement
    try:
        asm.solve()
    except Exception:
        pass
    asm.Document.recompute()
    return valores_da_junta(j)


def _carona(asm, peca, junta, parar):
    """A peça e tudo o que está preso a ela por outras juntas (sem passar por peças fixas nem voltar ao outro
    lado da junta): vão juntos, como um bloco, e o solver só acerta o que sobrar."""
    try:
        import UtilsAssembly
        juntas = [x for x in UtilsAssembly.getJointGroup(asm).Group
                  if x is not junta and getattr(x, "Reference1", None) and getattr(x, "Reference2", None)
                  and not getattr(x, "Suppressed", False)]
    except Exception:
        juntas = []
    vistos, fila = [peca], [peca]
    while fila:
        atual = fila.pop()
        for x in juntas:
            a, b = x.Reference1[0], x.Reference2[0]
            viz = b if a is atual else (a if b is atual else None)
            if viz is None or viz in parar or any(viz is v for v in vistos):
                continue
            vistos.append(viz)
            fila.append(viz)
    return vistos


# ----------------------------------------------------------------------------------- grupo rígido
def travar_juntos(componentes):
    """Trava os componentes uns nos outros onde estão (o "Rigid Group"/"As-built" do Fusion e do SolidCraft):
    uma junta Fixa do primeiro com cada um dos outros, sem mexer em nada. Devolve as juntas criadas."""
    comps = list(dict.fromkeys(componentes))
    if len(comps) < 2:
        raise ValueError("Escolha pelo menos dois componentes da montagem.")
    asm = montagem_de(comps[0])
    if asm is None or any(montagem_de(c) is not asm for c in comps):
        raise ValueError("Os componentes têm de estar na mesma montagem.")
    import JointObject
    import UtilsAssembly
    grupo = UtilsAssembly.getJointGroup(asm)
    base = comps[0]
    criadas = []
    for c in comps[1:]:
        j = grupo.newObject("App::FeaturePython", "Travados")
        JointObject.Joint(j, 0)            # Fixa
        if FreeCAD.GuiUp:
            try:
                JointObject.ViewProviderJoint(j.ViewObject)
            except Exception:
                pass
        j.Label = "Travados: %s + %s" % (base.Label, c.Label)
        # origem de cada componente; o lado 2 leva a posição atual do 1 como deslocamento: os dois sistemas
        # já coincidem, então o solver não move nada
        j.Reference1 = [base, ["", ""]]
        j.Reference2 = [c, ["", ""]]
        g1 = _global_comp(asm, base)
        g2 = _global_comp(asm, c)
        j.Offset1 = FreeCAD.Placement()
        j.Offset2 = g2.inverse() * g1
        j.Placement1 = FreeCAD.Placement()
        j.Placement2 = j.Offset2
        criadas.append(j)
    try:
        asm.solve()
    except Exception:
        pass
    asm.Document.recompute()
    return criadas


def _global_comp(asm, comp):
    return _global_da_montagem(asm) * comp.Placement


# ----------------------------------------------------------------------------------- componentes dos sólidos
def solidos_de(obj):
    try:
        return list(obj.Shape.Solids)
    except Exception:
        return []


def componentes_dos_solidos(obj, montagem=None):
    """Separa um objeto com vários sólidos (STEP de um corpo só, composto) em uma peça para cada sólido, no
    mesmo lugar, com o mesmo material e a mesma cor. O original fica escondido (Desfazer volta tudo).
    Com `montagem`, as peças novas já entram nela, prontas para as restrições."""
    solidos = solidos_de(obj)
    if len(solidos) < 2:
        raise ValueError("“%s” tem um sólido só: já é uma peça." % obj.Label)
    doc = obj.Document
    novas = []
    cor = None
    try:
        cor = obj.ViewObject.ShapeAppearance if FreeCAD.GuiUp else None
    except Exception:
        cor = None
    for k, sol in enumerate(solidos, 1):
        destino = montagem if montagem is not None else doc
        o = destino.newObject("Part::Feature", "Peca") if montagem is not None else \
            doc.addObject("Part::Feature", "Peca")
        # o sólido vem em coordenadas globais: a peça nova guarda a forma no lugar e Placement neutro
        o.Shape = sol
        o.Label = "%s %d" % (obj.Label, k)
        if hasattr(obj, "Material") and "Material" in o.PropertiesList:
            try:
                o.Material = obj.Material
            except Exception:
                pass
        if cor is not None:
            try:
                o.ViewObject.ShapeAppearance = cor
            except Exception:
                pass
        novas.append(o)
    try:
        obj.Visibility = False
    except Exception:
        pass
    doc.recompute()
    return novas


# ----------------------------------------------------------------------------------- interface
if FreeCAD.GuiUp:
    try:
        from PySide import QtCore, QtWidgets
    except ImportError:  # pragma: no cover
        from PySide2 import QtCore, QtWidgets
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

    class PainelMoverJunta(P.PainelTarefa):
        """Mover junta: escolhe a junta e gira/empurra pelo controle deslizante, vendo a montagem mexer."""
        titulo = "Mover junta"
        ajuda = ("Escolha a junta (dobradiça, deslizante ou concêntrica) e arraste o controle: a peça gira ou "
                 "desliza e o que está preso a ela vai junto. OK deixa onde está; Cancelar volta.")

        def __init__(self, asm=None, junta=None):
            import UtilsAssembly
            self.asm = asm or UtilsAssembly.activeAssembly()
            self._junta_inicial = junta
            self._salvo = UtilsAssembly.saveAssemblyPartsPlacements(self.asm) if self.asm is not None else None
            super().__init__()

        def montar(self):
            f = self.form
            s0 = f.secao("Junta", "selecao")
            self.juntas = QtWidgets.QComboBox()
            for j in (juntas_moveis(self.asm) if self.asm is not None else []):
                self.juntas.addItem("%s (%s)" % (j.Label, {"Revolute": "dobradiça", "Slider": "deslizante",
                                                           "Cylindrical": "concêntrica"}[j.JointType]), j.Name)
            s0.linha("selecao", self.juntas, "Juntas que têm movimento livre.", "Junta")
            s1 = f.secao("Movimento", "angulo")
            self.giro = P.numero(0.0, -360.0, 360.0, "°", 1)
            self.giro.setKeyboardTracking(True)
            self.lin_giro = s1.linha("angulo", self.giro, "Giro em torno do eixo da junta.", "Ângulo")
            self.desl_giro = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            s1.widget(self.desl_giro)
            self.avanco = P.numero(0.0, -1e5, 1e5, " mm", 1)
            self.avanco.setKeyboardTracking(True)
            self.lin_avanco = s1.linha("comprimento", self.avanco, "Avanço ao longo do eixo da junta.", "Avanço")
            self.desl_avanco = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            s1.widget(self.desl_avanco)
            self.limites = QtWidgets.QLabel("")
            self.limites.setWordWrap(True)
            s1.widget(self.limites)
            self._ocupado = False
            self.juntas.currentIndexChanged.connect(self._trocar)
            self.giro.valueChanged.connect(lambda v: self._pedir(giro=v))
            self.avanco.valueChanged.connect(lambda v: self._pedir(avanco=v))
            self.desl_giro.valueChanged.connect(lambda v: self._pedir(giro=v / 10.0))
            self.desl_avanco.valueChanged.connect(lambda v: self._pedir(avanco=v / 10.0))
            if self._junta_inicial is not None:
                i = self.juntas.findData(self._junta_inicial.Name)
                if i >= 0:
                    self.juntas.setCurrentIndex(i)
            self._trocar()

        def junta(self):
            n = self.juntas.currentData()
            return self.asm.Document.getObject(n) if n else None

        def _trocar(self, *_):
            j = self.junta()
            if j is None:
                return
            mov = MOVIMENTOS[j.JointType]
            v = valores_da_junta(j)
            lim = limites_da_junta(j)
            self._ocupado = True
            textos = []
            for k, spin, desl, faixa_padrao in (("giro", self.giro, self.desl_giro, (-180.0, 180.0)),
                                                 ("avanco", self.avanco, self.desl_avanco, (-200.0, 200.0))):
                tem = k in mov
                for w in (spin, desl):
                    w.setEnabled(tem)
                if not tem:
                    continue
                lo, hi = lim[k]
                atual = v[k]
                a = lo if lo is not None else min(faixa_padrao[0], atual - 100.0 if k == "avanco" else faixa_padrao[0])
                b = hi if hi is not None else max(faixa_padrao[1], atual + 100.0 if k == "avanco" else faixa_padrao[1])
                spin.setRange(a, b)
                spin.setValue(atual)
                desl.setRange(int(round(a * 10)), int(round(b * 10)))
                desl.setValue(int(round(atual * 10)))
                un = "°" if k == "giro" else " mm"
                if lo is not None or hi is not None:
                    textos.append("%s: limites %s a %s" % ("Ângulo" if k == "giro" else "Avanço",
                                                           PrumoUtil_fmt(lo, un), PrumoUtil_fmt(hi, un)))
            self.limites.setText("; ".join(textos) or "Sem limites na junta.")
            self._ocupado = False

        def _pedir(self, giro=None, avanco=None):
            if self._ocupado:
                return
            j = self.junta()
            if j is None:
                return
            self._ocupado = True
            try:
                r = mover_junta(j, giro=giro, avanco=avanco)
                if "giro" in r:
                    self.giro.setValue(r["giro"])
                    self.desl_giro.setValue(int(round(r["giro"] * 10)))
                if "avanco" in r:
                    self.avanco.setValue(r["avanco"])
                    self.desl_avanco.setValue(int(round(r["avanco"] * 10)))
                self.form.mensagem.mostrar(self.pronto_texto(), "ok")
            except Exception as ex:
                self.form.mensagem.mostrar(str(ex), "erro")
            finally:
                self._ocupado = False

        def pendencia(self):
            if self.asm is None:
                return "Abra a montagem para editar (duplo clique nela)."
            if self.juntas.count() == 0:
                return "A montagem não tem dobradiça, deslizante nem concêntrica para mover."
            return None

        def pronto_texto(self):
            return "OK deixa a montagem nesta posição; Cancelar volta para onde estava."

        def executar(self):
            return []

        def reject(self):
            if self._salvo is not None:
                import UtilsAssembly
                UtilsAssembly.restoreAssemblyPartsPlacements(self.asm, self._salvo)
                try:
                    self.asm.solve()
                except Exception:
                    pass
                self.asm.Document.recompute()
            return super().reject()

    def PrumoUtil_fmt(v, un):
        if v is None:
            return "livre"
        import PrumoUtil
        return PrumoUtil.fmt(v, 1) + un

    class CmdMoverJunta:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("mover_junta.svg"), "MenuText": "Mover junta",
                    "ToolTip": "Gira uma dobradiça ou desliza um deslizante com um controle, vendo a montagem "
                               "mexer (respeita os limites da junta)."}

        def IsActive(self):
            try:
                import UtilsAssembly
                return UtilsAssembly.activeAssembly() is not None
            except Exception:
                return False

        def Activated(self):
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx()]
            j = next((o for o in sel if getattr(o, "JointType", "") in MOVIMENTOS), None)
            PainelMoverJunta(junta=j).mostrar()

    class PainelTravarJuntos(P.PainelTarefa):
        titulo = "Travar juntos"
        ajuda = ("Escolha dois ou mais componentes: ficam presos uns aos outros onde estão, e passam a se mover "
                 "como um bloco só.")

        def montar(self):
            f = self.form
            s0 = f.secao("Componentes", "selecao")
            self.comps = f.caixa(s0, "Componentes", _filtro_componente, minimo=2,
                                 dica="Clique nas peças na tela ou na árvore.")

        def pendencia(self):
            if len(self.comps.valores()) < 2:
                return "Escolha pelo menos dois componentes."
            return None

        def pronto_texto(self):
            return "Pronto: %d componentes travados juntos, sem sair do lugar." % len(self.comps.valores())

        def executar(self):
            return travar_juntos(self.comps.valores())

    class CmdTravarJuntos:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("travar_juntos.svg"), "MenuText": "Travar juntos",
                    "ToolTip": "Prende dois ou mais componentes uns nos outros onde estão (grupo rígido), sem "
                               "mexer em nada."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelTravarJuntos().mostrar()

    def montagens(doc):
        return [o for o in (doc.Objects if doc else []) if o.TypeId == "Assembly::AssemblyObject"]

    def abrir_montagem(asm):
        """Põe a montagem em edição (o duplo clique na árvore): as restrições passam a funcionar nela."""
        gdoc = FreeCADGui.getDocument(asm.Document.Name)
        if gdoc.getInEdit() is not None:
            gdoc.resetEdit()
        gdoc.setEdit(asm)
        return asm

    class CmdEditarMontagem:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("travar_juntos.svg"), "MenuText": "Abrir montagem",
                    "ToolTip": "Abre a montagem do projeto para editar (o mesmo que o duplo clique nela na "
                               "árvore): as restrições aparecem em seguida."}

        def IsActive(self):
            try:
                import UtilsAssembly
                if UtilsAssembly.activeAssembly() is not None:
                    return False
            except Exception:
                pass
            return bool(montagens(FreeCAD.ActiveDocument))

        def Activated(self):
            ms = montagens(FreeCAD.ActiveDocument)
            if len(ms) == 1:
                abrir_montagem(ms[0])
                return
            m = QtWidgets.QMenu(FreeCADGui.getMainWindow())
            for a in ms:
                acao = m.addAction(a.Label)
                acao.triggered.connect(lambda _=False, a=a: abrir_montagem(a))
            from PySide import QtGui
            m.popup(QtGui.QCursor.pos())
            self._menu = m

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

    class CmdComponentesDosSolidos:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("padrao_componentes.svg"), "MenuText": "Componentes dos sólidos",
                    "ToolTip": "Um STEP (ou objeto) com vários sólidos vira uma peça para cada sólido, no lugar, "
                               "prontas para receber restrições."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            import PrumoSelecao
            import UtilsAssembly

            def varios(obj, subs):
                return [(obj.Label, obj)] if len(solidos_de(obj)) > 1 else []

            def fazer(objs):
                asm = UtilsAssembly.activeAssembly()
                doc = FreeCAD.ActiveDocument
                doc.openTransaction("Componentes dos sólidos")
                try:
                    n = []
                    for o in objs:
                        n += componentes_dos_solidos(o, asm)
                except ValueError as ex:
                    doc.abortTransaction()
                    QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Componentes dos sólidos",
                                                      str(ex))
                    return []
                doc.commitTransaction()
                return n
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx() if len(solidos_de(s.Object)) > 1]
            if sel:
                return fazer(sel)
            return PrumoSelecao.pedir("Componentes dos sólidos",
                                      "Escolha o objeto com vários sólidos (um STEP importado, por exemplo): "
                                      "cada sólido vira uma peça.", [("Objeto", varios, 1, None)],
                                      lambda objs: fazer(objs))

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
        FreeCADGui.addCommand("Prumo_MoverJunta", CmdMoverJunta())
        FreeCADGui.addCommand("Prumo_TravarJuntos", CmdTravarJuntos())
        FreeCADGui.addCommand("Prumo_EditarMontagem", CmdEditarMontagem())
        FreeCADGui.addCommand("Prumo_ComponentesDosSolidos", CmdComponentesDosSolidos())
