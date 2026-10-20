# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - menu de contexto pela seleção (botão direito na vista 3D e na árvore).
"""Menu de contexto que muda conforme o que está selecionado.

Face plana: "Esboço nesta face", "Extrudar", "Cavidade". Arestas: "Arredondar", "Chanfro".
Esboço: "Extrudar", "Cavidade", "Revolução", "Editar esboço". Operação: "Cotas da operação".
Sempre que houver peça: "Medir" e "Propriedades de massa".

Os itens do Prumo chamam os comandos do FreeCAD (Peça / PartDesign); a bancada é carregada na
hora se ainda não estiver. É feito com o "manipulador de bancada" do FreeCAD, então vale em
qualquer bancada.
"""

import FreeCAD
import FreeCADGui

import PrumoUtil

# comando Prumo -> (comando do FreeCAD, bancada que o registra, rótulo, dica, ícone)
ACOES = {
    "Prumo_CtxEsbocoNaFace": ("PartDesign_NewSketch", "PartDesignWorkbench", "Esboço nesta face",
                              "Cria um esboço apoiado na face selecionada", "Sketcher_NewSketch"),
    "Prumo_CtxExtrudar": ("PartDesign_Pad", "PartDesignWorkbench", "Extrudar",
                          "Extrusão a partir do esboço ou da face selecionada", "PartDesign_Pad"),
    "Prumo_CtxCavidade": ("PartDesign_Pocket", "PartDesignWorkbench", "Cavidade",
                          "Remove material a partir do esboço ou da face selecionada", "PartDesign_Pocket"),
    "Prumo_CtxRevolucao": ("PartDesign_Revolution", "PartDesignWorkbench", "Revolução",
                           "Gira o esboço selecionado em torno de um eixo", "PartDesign_Revolution"),
    "Prumo_CtxFuro": ("PartDesign_Hole", "PartDesignWorkbench", "Furo",
                      "Furo a partir dos círculos do esboço selecionado", "PartDesign_Hole"),
    "Prumo_CtxArredondar": ("PartDesign_Fillet", "PartDesignWorkbench", "Arredondar",
                            "Arredonda as arestas selecionadas", "PartDesign_Fillet"),
    "Prumo_CtxChanfro": ("PartDesign_Chamfer", "PartDesignWorkbench", "Chanfro",
                         "Chanfra as arestas selecionadas", "PartDesign_Chamfer"),
    "Prumo_CtxCasca": ("PartDesign_Thickness", "PartDesignWorkbench", "Casca",
                       "Esvazia a peça tirando as faces selecionadas", "PartDesign_Thickness"),
    "Prumo_CtxEditarEsboco": ("Sketcher_EditSketch", "SketcherWorkbench", "Editar esboço",
                              "Abre o esboço selecionado para edição", "Sketcher_EditSketch"),
    "Prumo_CtxMedir": ("Std_Measure", None, "Medir", "Mede a seleção", "umf-measurement"),
}

ORDEM_VISTA_ANCORA = "Std_ViewFitAll"
ORDEM_ARVORE_ANCORA = "Std_Placement"


def _garantir_comando(cmd, bancada):
    """Carrega a bancada que registra `cmd`, se preciso, sem trocar a bancada ativa."""
    if cmd in FreeCADGui.listCommands():
        return True
    if not bancada:
        return False
    try:
        atual = FreeCADGui.activeWorkbench()
        FreeCADGui.activateWorkbench(bancada)
        if atual is not None:
            FreeCADGui.activateWorkbench(atual.name())
    except Exception:
        return False
    return cmd in FreeCADGui.listCommands()


class CmdAcao:
    def __init__(self, nome):
        self.nome = nome
        self.cmd, self.bancada, self.rotulo, self.dica, self.icone = ACOES[nome]

    def GetResources(self):
        return {"Pixmap": self.icone, "MenuText": self.rotulo, "ToolTip": self.dica}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        if not _garantir_comando(self.cmd, self.bancada):
            FreeCAD.Console.PrintWarning("Prumo: comando %s indisponível\n" % self.cmd)
            return
        FreeCADGui.runCommand(self.cmd, 0)


# ============================================================ análise da seleção
def _tipo_sub(sub):
    nome = sub.split(".")[-1]
    for t in ("Face", "Edge", "Vertex"):
        if nome.startswith(t):
            return t
    return ""


def _face_plana(obj, sub):
    try:
        f = obj.getSubObject(sub)
        return f is not None and f.ShapeType == "Face" and "Plane" in f.Surface.__class__.__name__
    except Exception:
        return False


def _em_corpo(obj):
    try:
        if obj.TypeId == "PartDesign::Body":
            return True
        pai = obj.getParentGeoFeatureGroup()
        return pai is not None and pai.TypeId == "PartDesign::Body"
    except Exception:
        return False


def itens_para(selecao):
    """Comandos a oferecer para a seleção [(obj, [subnomes])]. Lista vazia = nada a acrescentar."""
    if not selecao:
        return []
    itens = []
    objs = [o for o, _ in selecao]
    subs = [(o, s) for o, ss in selecao for s in ss]
    tipos = {_tipo_sub(s) for _o, s in subs}
    so_esbocos = all(o.TypeId == "Sketcher::SketchObject" for o in objs)
    tem_peca = PrumoUtil.tem_peca(objs)

    if so_esbocos and len(objs) == 1 and not subs:
        itens += ["Prumo_CtxExtrudar", "Prumo_CtxCavidade", "Prumo_CtxRevolucao", "Prumo_CtxFuro",
                  "Prumo_CtxEditarEsboco"]
    elif so_esbocos and not subs:
        itens += ["Prumo_CtxExtrudar", "Prumo_CtxCavidade"]
    elif tipos == {"Face"}:
        planas = all(_face_plana(o, s) for o, s in subs)
        corpo = all(_em_corpo(o) for o, _ in subs)
        if planas and len(subs) == 1:
            itens.append("Prumo_CtxEsbocoNaFace")
        if planas and corpo:
            itens += ["Prumo_CtxExtrudar", "Prumo_CtxCavidade"]
        if corpo:
            itens += ["Prumo_CtxArredondar", "Prumo_CtxChanfro", "Prumo_CtxCasca", "Prumo_Cotas"]
    elif tipos == {"Edge"}:
        if all(_em_corpo(o) for o, _ in subs):
            itens += ["Prumo_CtxArredondar", "Prumo_CtxChanfro"]
    elif not subs and len(objs) == 1 and objs[0].isDerivedFrom("PartDesign::Feature") and \
            objs[0].TypeId != "PartDesign::Body":
        itens.append("Prumo_Cotas")

    if subs or tem_peca:
        if itens:
            itens.append("Separator")
        itens.append("Prumo_CtxMedir")
    if tem_peca:
        itens.append("Prumo_Massa")
        itens.append("Prumo_Propriedades")
    return itens


def _selecao_atual():
    res = []
    for s in FreeCADGui.Selection.getSelectionEx():
        res.append((s.Object, list(s.SubElementNames)))
    return res


class Manipulador:
    """Acrescenta os itens do Prumo no começo do menu de contexto."""

    def modifyContextMenu(self, recipient):
        try:
            if not FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetBool("MenuContexto", True):
                return []
            gd = FreeCADGui.ActiveDocument
            if gd is not None and gd.getInEdit() is not None:
                return []  # dentro do esboço/edição, o menu é o do próprio editor
            itens = itens_para(_selecao_atual())
            if not itens:
                return []
            ancora = ORDEM_VISTA_ANCORA if recipient == "View" else ORDEM_ARVORE_ANCORA
            ops = [{"insert": c, "menuItem": ancora} for c in itens]
            ops.append({"insert": "Separator", "menuItem": ancora})
            return ops
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo menu de contexto: %s\n" % exc)
            return []


_estado = {"manip": None}


def registrar_comandos():
    for nome in ACOES:
        FreeCADGui.addCommand(nome, CmdAcao(nome))


def install():
    if _estado["manip"] is None:
        _estado["manip"] = Manipulador()
        FreeCADGui.addWorkbenchManipulator(_estado["manip"])


def uninstall():
    if _estado["manip"] is not None:
        FreeCADGui.removeWorkbenchManipulator(_estado["manip"])
        _estado["manip"] = None
