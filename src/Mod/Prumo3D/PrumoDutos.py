# SPDX-License-Identifier: LGPL-2.1-or-later
"""Prumo 3D: dutos de ar-condicionado (HVAC) na aba Tubulação.

As peças são as da FreeCAD Parts Library (pasta HVAC/Ducts), de Francisco Rosa, CC-BY 3.0
(Resources/hvac/CREDITOS.md). Cada peça é paramétrica: um conjunto de variáveis (VarSet) comanda bocas,
comprimento ou ângulo, chapa, flanges e isolamento, e uma planilha da própria peça calcula as áreas.

O Prumo copia a peça escolhida para o projeto (sem as folhas de desenho que vêm no arquivo), dá a ela um
nome em português e mostra as variáveis num painel em português. Para mudar depois: selecione a peça e
use "Editar duto" (ou mude as variáveis na propriedade do VarSet).
"""
import os
import re

import FreeCAD

import PrumoUtil

PASTA = os.path.join(PrumoUtil.RES_DIR, "hvac")

# (id, nome, arquivo)
PECAS = [
    ("ret_reto", "Duto retangular reto", "Duct_linear_rectangular_complete.FCStd"),
    ("ret_curva", "Curva retangular", "Duct_curved_rectangular_complete.FCStd"),
    ("red_reto", "Duto redondo reto", "Duct_linear_circular_complete.FCStd"),
    ("red_curva", "Curva redonda", "Duct_curved_circular_complete.FCStd"),
    ("oval_reto", "Duto oval reto", "Duct_linear_oval_complete.FCStd"),
    ("oval_curva", "Curva oval", "Duct_curved_oval_complete.FCStd"),
    ("red_oval_reto", "Transição redondo–oval", "Duct_linear_circular_oval_complete.FCStd"),
    ("red_oval_curva", "Curva de transição redondo–oval", "Duct_curved_circular_oval_complete.FCStd"),
    ("ret_red_reto", "Transição retangular–redondo", "Duct_linear_rectangular_circular_complete.FCStd"),
    ("ret_red_curva", "Curva de transição retangular–redondo", "Duct_curved_rectangular_circular_complete.FCStd"),
    ("ret_oval_reto", "Transição retangular–oval", "Duct_linear_rectangular_oval_complete.FCStd"),
    ("ret_oval_curva", "Curva de transição retangular–oval", "Duct_curved_rectangular_oval_complete.FCStd"),
    ("flex", "Duto flexível", "Duct_flex_complete.FCStd"),
]
POR_ID = {p[0]: p for p in PECAS}

# nomes das variáveis em português (o resto sai do próprio nome)
ROTULOS = {
    "Duct_Diameter1": "Diâmetro da boca 1", "Duct_Diameter2": "Diâmetro da boca 2",
    "Duct_Opening1_width": "Largura da boca 1", "Duct_Opening1_height": "Altura da boca 1",
    "Duct_Opening2_width": "Largura da boca 2", "Duct_Opening2_height": "Altura da boca 2",
    "Duct_Opening1_diameter": "Diâmetro da boca 1", "Duct_Opening2_diameter": "Diâmetro da boca 2",
    "Duct_Opening1_distance_between_arcs": "Trecho reto do oval (boca 1)",
    "Duct_Opening2_distance_between_arcs": "Trecho reto do oval (boca 2)",
    "Duct_Opening1_horizontal_position": "Deslocamento horizontal da boca 1",
    "Duct_Opening1_vertical_position": "Deslocamento vertical da boca 1",
    "Duct_Opening2_horizontal_position": "Deslocamento horizontal da boca 2",
    "Duct_Opening2_horizontal_positon": "Deslocamento horizontal da boca 2",
    "Duct_Opening2_vertical_position": "Deslocamento vertical da boca 2",
    "Duct_Opening2_closure": "Fechar a boca 2", "Duct_Sheet_thickness": "Espessura da chapa",
    "Duct_Length": "Comprimento", "Duct_Flip_axis": "Inverter o sentido",
    "Duct_Show_volume_only": "Mostrar só o volume interno", "Duct_Duct": "Mostrar o duto",
    "Duct_Duct_external": "Duto externo", "Duct_Duct_internal": "Duto interno",
    "Duct_Opening1_axis_flip": "Inverter a boca 1", "Duct_Opening2_axis_flip": "Inverter a boca 2",
    "Flange_Flange1": "Flange na boca 1", "Flange_Flange2": "Flange na boca 2",
    "Flange_Flange_01": "Flange na boca 1", "Flange_Flange_02": "Flange na boca 2",
    "Flange_Height": "Altura do flange", "Flange_Thickness": "Espessura do flange",
    "Insulation_Insulation": "Com isolamento", "Insulation_Thickness": "Espessura do isolamento",
}
GRUPOS = [("Duct_", "Duto"), ("Flange_", "Flanges"), ("Insulation_", "Isolamento")]
NAO_MOSTRAR = {"Duct_Axis", "Duct_Axis_Bezier_curve", "Duct_Opening1_axis", "Duct_Opening2_axis",
               "Materials_Insulation", "Materials_Sheet_metal"}
TIPOS_DESENHO = ("TechDraw::",)


def rotulo(prop):
    if prop in ROTULOS:
        return ROTULOS[prop]
    t = re.sub(r"^(Duct|Flange|Insulation|Materials)_", "", prop).replace("_", " ")
    return t[:1].upper() + t[1:]


def variaveis(varset):
    """[(grupo, [(propriedade, rótulo, tipo)])] do VarSet, na ordem do arquivo."""
    res = []
    for pref, nome in GRUPOS:
        itens = []
        for p in varset.PropertiesList:
            if not p.startswith(pref) or p in NAO_MOSTRAR:
                continue
            tipo = varset.getTypeIdOfProperty(p)
            if tipo in ("App::PropertyLength", "App::PropertyDistance", "App::PropertyBool",
                        "App::PropertyFloat", "App::PropertyAngle", "App::PropertyInteger"):
                itens.append((p, rotulo(p), tipo))
        if itens:
            res.append((nome, itens))
    return res


def eixo(varset):
    """O objeto do eixo (linha ou arco) que comanda comprimento ou ângulo e a posição da peça."""
    for p in ("Duct_Axis", "Duct_Axis_Bezier_curve"):
        if p in varset.PropertiesList:
            return getattr(varset, p)
    return None


def _novos(doc, antes):
    return [o for o in doc.Objects if o.Name not in antes]


def inserir(doc, pid, posicao=None, valores=None):
    """Copia a peça para o documento. Devolve (grupo, varset)."""
    _id, nome, arq = POR_ID[pid]
    caminho = os.path.join(PASTA, arq)
    antes = {o.Name for o in doc.Objects}
    # copia do arquivo só a peça: as folhas de desenho que vêm nele não entram no projeto (apagá-las depois de
    # copiar derruba o programa com a vista da folha ainda montando)
    origem = FreeCAD.openDocument(caminho, True)
    try:
        objs = [o for o in origem.Objects if not o.TypeId.startswith(TIPOS_DESENHO)]
        doc.copyObject(objs, False)
    finally:
        FreeCAD.closeDocument(origem.Name)
        FreeCAD.setActiveDocument(doc.Name)
        if FreeCAD.GuiUp:
            import FreeCADGui
            FreeCADGui.setActiveDocument(doc.Name)
    novos = _novos(doc, antes)
    varset = next((o for o in novos if o.TypeId == "App::VarSet"), None)
    if varset is None:
        raise RuntimeError("a peça %s não tem as variáveis (VarSet)" % arq)
    # o grupo de cima da peça (sem pai entre os novos)
    grupos = [o for o in novos if o.isDerivedFrom("App::DocumentObjectGroup")]
    topo = None
    for g in grupos:
        if not any(g in getattr(h, "Group", []) for h in grupos if h is not g):
            topo = g
            break
    n = sum(1 for o in doc.Objects if o.isDerivedFrom("App::DocumentObjectGroup") and
            o.Label.startswith(nome)) + 1
    if topo is not None:
        topo.Label = "%s %d" % (nome, n)
        for p, v in (("PrumoDuto", pid),):
            if p not in topo.PropertiesList:
                topo.addProperty("App::PropertyString", p, "Prumo", "Peça de duto do catálogo HVAC")
                topo.setEditorMode(p, 1)
            setattr(topo, p, v)
    varset.Label = "Variáveis do duto %d" % n
    for p, v in (valores or {}).items():
        definir(varset, p, v)
    ax = eixo(varset)
    if posicao is not None and ax is not None:
        ax.Placement.Base = posicao
    doc.recompute()
    doc.recompute()          # a planilha de áreas lê o resultado da primeira passada
    return topo, varset


def definir(varset, prop, valor):
    if prop == "_comprimento":
        ax = eixo(varset)
        if ax is not None and "Length" in ax.PropertiesList:
            ax.Length = valor
        return
    if prop == "_raio":
        ax = eixo(varset)
        if ax is not None and "Radius" in ax.PropertiesList:
            ax.Radius = valor
        return
    if prop == "_angulo":
        ax = eixo(varset)
        if ax is not None and "LastAngle" in ax.PropertiesList:
            ax.LastAngle = float(ax.FirstAngle.Value if hasattr(ax.FirstAngle, "Value") else ax.FirstAngle) + valor
        return
    setattr(varset, prop, valor)


def geometria_do_eixo(varset):
    """[(chave, rótulo, valor)] do comprimento (reta) ou raio e ângulo (curva)."""
    ax = eixo(varset)
    res = []
    if ax is None:
        return res
    if "Radius" in ax.PropertiesList and "LastAngle" in ax.PropertiesList:
        ang = float(ax.LastAngle) - float(ax.FirstAngle) if not hasattr(ax.LastAngle, "Value") else \
            ax.LastAngle.Value - ax.FirstAngle.Value
        res.append(("_raio", "Raio do eixo", float(ax.Radius)))
        res.append(("_angulo", "Ângulo da curva", round(ang, 3)))
    elif "Length" in ax.PropertiesList and "Duct_Length" not in varset.PropertiesList:
        res.append(("_comprimento", "Comprimento", float(ax.Length)))
    return res


def varset_da_selecao():
    import FreeCADGui
    for o in FreeCADGui.Selection.getSelection():
        alvo = [o] + list(o.InListRecursive)
        for a in alvo:
            if a.TypeId == "App::VarSet" and ("Duct_Axis" in a.PropertiesList or
                                              "Duct_Axis_Bezier_curve" in a.PropertiesList):
                return a
            for f in getattr(a, "Group", []) or []:
                if f.TypeId == "App::VarSet" and "Duct_Sheet_thickness" in f.PropertiesList:
                    return f
        for f in getattr(o, "OutListRecursive", []):
            if f.TypeId == "App::VarSet" and "Duct_Sheet_thickness" in f.PropertiesList:
                return f
    return None


# ------------------------------------------------------------------ janela
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtWidgets

    class JanelaDutos(QtWidgets.QDialog):
        """Escolher a peça (ou editar a selecionada) e ajustar as variáveis em português."""

        def __init__(self, varset=None, parent=None):
            super().__init__(parent or FreeCADGui.getMainWindow())
            import PrumoUI as UI
            self.setObjectName("PrumoUI")
            self.setStyleSheet(UI.qss())
            self.setWindowTitle("Editar duto" if varset is not None else "Dutos de ar-condicionado")
            self.resize(720, 560)
            self.varset = varset
            lay = QtWidgets.QHBoxLayout(self)
            self.lista = QtWidgets.QListWidget()
            self.lista.setObjectName("PrumoDutosLista")
            self.lista.setFixedWidth(270)
            for pid, nome, _a in PECAS:
                it = QtWidgets.QListWidgetItem(nome)
                it.setData(QtCore.Qt.UserRole, pid)
                self.lista.addItem(it)
            lay.addWidget(self.lista)
            col = QtWidgets.QVBoxLayout()
            self.area = QtWidgets.QScrollArea()
            self.area.setWidgetResizable(True)
            col.addWidget(self.area, 1)
            nota = QtWidgets.QLabel("Peças de Francisco Rosa (FreeCAD Parts Library, CC-BY 3.0). "
                                    "Selecione um ponto antes para inserir ali.")
            nota.setObjectName("PrumoSub")
            nota.setWordWrap(True)
            col.addWidget(nota)
            bts = QtWidgets.QHBoxLayout()
            bts.addStretch(1)
            fechar = QtWidgets.QPushButton("Fechar")
            fechar.clicked.connect(self.reject)
            self.ok = QtWidgets.QPushButton("Aplicar" if varset is not None else "Inserir")
            self.ok.setObjectName("PrumoPrimario")
            self.ok.setDefault(True)
            self.ok.clicked.connect(self.aplicar)
            bts.addWidget(fechar)
            bts.addWidget(self.ok)
            col.addLayout(bts)
            lay.addLayout(col, 1)
            self.campos = {}
            self.inseridos = []
            if varset is not None:
                self.lista.hide()
                self._montar(varset)
            else:
                self.lista.currentRowChanged.connect(lambda _i: self._modelo())
                self.lista.setCurrentRow(0)

        def peca(self):
            it = self.lista.currentItem()
            return it.data(QtCore.Qt.UserRole) if it is not None else None

        def _modelo(self):
            """Mostra as variáveis da peça escolhida (lidas do próprio arquivo, sem abrir janela)."""
            pid = self.peca()
            if not pid:
                return
            doc = FreeCAD.openDocument(os.path.join(PASTA, POR_ID[pid][2]), True)
            try:
                vs = next(o for o in doc.Objects if o.TypeId == "App::VarSet")
                self._montar(vs, ler_so=True)
            finally:
                FreeCAD.closeDocument(doc.Name)

        def _montar(self, vs, ler_so=False):
            w = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(w)
            self.campos = {}
            for chave, rot, val in geometria_do_eixo(vs):
                sp = QtWidgets.QDoubleSpinBox()
                sp.setRange(1, 360 if chave == "_angulo" else 100000)
                sp.setDecimals(1)
                sp.setSuffix(" °" if chave == "_angulo" else " mm")
                sp.setValue(val)
                form.addRow(rot, sp)
                self.campos[chave] = ("num", sp)
            for grupo, itens in variaveis(vs):
                t = QtWidgets.QLabel(grupo)
                t.setStyleSheet("color: #003A70; font-weight: 600; margin-top: 6px;")
                form.addRow(t)
                for p, rot, tipo in itens:
                    v = getattr(vs, p)
                    if tipo == "App::PropertyBool":
                        cb = QtWidgets.QCheckBox()
                        cb.setChecked(bool(v))
                        form.addRow(rot, cb)
                        self.campos[p] = ("bool", cb)
                    else:
                        sp = QtWidgets.QDoubleSpinBox()
                        sp.setRange(-100000 if tipo == "App::PropertyDistance" else 0, 100000)
                        sp.setDecimals(1)
                        sp.setSuffix(" mm" if "Length" in tipo or "Distance" in tipo else "")
                        sp.setValue(float(v))
                        form.addRow(rot, sp)
                        self.campos[p] = ("num", sp)
            self.area.setWidget(w)

        def valores(self):
            res = {}
            for p, (tipo, w) in self.campos.items():
                res[p] = w.isChecked() if tipo == "bool" else w.value()
            return res

        def aplicar(self):
            doc = FreeCAD.ActiveDocument or FreeCAD.newDocument()
            doc.openTransaction("Duto de ar-condicionado")
            try:
                if self.varset is not None:
                    for p, v in self.valores().items():
                        definir(self.varset, p, v)
                    doc.recompute()
                    doc.recompute()
                    res = self.varset
                else:
                    import PrumoComponentes
                    res = inserir(doc, self.peca(), PrumoComponentes.ponto_da_selecao(), self.valores())
                    self.inseridos.append(res)
            except Exception as exc:
                doc.abortTransaction()
                import PrumoAvisoClique as AV
                AV.mostrar("Não deu para %s o duto: %s" % ("ajustar" if self.varset else "inserir", exc), "erro")
                return None
            doc.commitTransaction()
            try:
                if len(doc.Objects) and self.varset is None:
                    FreeCADGui.SendMsgToActiveView("ViewFit")
            except Exception:
                pass
            return res

    _J = {"j": None}

    class CmdDutos:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("dutos.svg"), "MenuText": "Dutos de ar-condicionado",
                    "ToolTip": "Inserir duto de ar-condicionado (HVAC): reto, curva, transição ou flexível, com "
                               "flanges e isolamento. Peças de Francisco Rosa (FreeCAD Parts Library)."}

        def IsActive(self):
            return True

        def Activated(self):
            j = JanelaDutos()
            _J["j"] = j
            j.show()

    class CmdEditarDuto:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("dutos.svg"), "MenuText": "Editar duto",
                    "ToolTip": "Selecione um duto e ajuste bocas, comprimento ou ângulo, chapa, flanges e isolamento."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and bool(FreeCADGui.Selection.getSelection())

        def Activated(self):
            vs = varset_da_selecao()
            if vs is None:
                import PrumoAvisoClique as AV
                AV.mostrar("Editar duto: selecione uma peça de duto inserida pelo Prumo.")
                return
            j = JanelaDutos(vs)
            _J["j"] = j
            j.show()

    def registrar_comandos():
        FreeCADGui.addCommand("Prumo_Dutos", CmdDutos())
        FreeCADGui.addCommand("Prumo_EditarDuto", CmdEditarDuto())
