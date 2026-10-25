# SPDX-License-Identifier: LGPL-2.1-or-later
"""Guia "vindo do SolidWorks / ZW3D": onde fica, no Prumo, cada comando que você já conhece.

Tabela pesquisável (nome no SolidWorks, nome em outros CAD — ZW3D, Inventor, Fusion — e o
comando no Prumo), com "Mostrar onde" (pisca o botão na faixa) e as diferenças de conceito que
mais confundem quem migra.
"""

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets

# (área, SolidWorks, outros CAD (ZW3D / Inventor / Fusion), no Prumo, aba, [comandos], observação)
EQUIVALENCIAS = [
    ("Peça", "Esboço", "Sketch", "Esboço", "peca", ["PartDesign_CompSketches", "PartDesign_NewSketch"],
     "Prefira apoiar o esboço nos planos da origem: esboço em face gerada pode quebrar se o modelo mudar."),
    ("Peça", "Padrão linear de entidades do esboço", "Sketch linear pattern", "Padrão linear", "esboco",
     ["Sketcher_Translate"], "Dentro do esboço: selecione a geometria e defina cópias e espaçamento no painel."),
    ("Peça", "Padrão circular de entidades do esboço", "Sketch circular pattern", "Padrão circular", "esboco",
     ["Sketcher_Rotate"], "Dentro do esboço: selecione a geometria, clique no centro e defina o número de cópias."),
    ("Peça", "Esboço 3D", "3D Sketch", "Esboço 3D", "peca", ["Prumo_Esboco3D"],
     "Clique na vista: o ponto cai no plano do último ponto; Tab troca o plano (XY, YZ, ZX), Esc termina o "
     "trecho. Serve de esqueleto de estrutura e caminho de tubo."),
    ("Peça", "Ressalto/Base extrudado", "Extrude / Extrusion", "Extrusão", "peca", ["PartDesign_Pad"],
     "Sem esboço selecionado, o comando pede o esboço."),
    ("Peça", "Corte extrudado", "Extrude (cut) / Pocket", "Cavidade", "peca", ["PartDesign_Pocket"], ""),
    ("Peça", "Barra de retrocesso (rollback)", "Rollback bar / History", "Régua de histórico", "peca",
     ["Prumo_ReguaHistorico"], "Arraste a régua amarela no painel Histórico do corpo; novas operações entram ali."),
    ("Peça", "Ressalto revolucionado", "Revolve", "Revolução", "peca", ["PartDesign_Revolution"], ""),
    ("Peça", "Corte revolucionado", "Revolve (cut)", "Ranhura", "peca", ["PartDesign_Groove"], ""),
    ("Peça", "Varredura", "Sweep", "Varredura", "peca", ["PartDesign_AdditivePipe"], ""),
    ("Peça", "Loft", "Loft", "Loft", "peca", ["PartDesign_AdditiveLoft"], ""),
    ("Peça", "Filete", "Fillet", "Arredondar", "peca", ["PartDesign_Fillet"],
     "Deixe arredondamentos e chanfros para o fim do histórico."),
    ("Peça", "Chanfro", "Chamfer", "Chanfro", "peca", ["PartDesign_Chamfer"], ""),
    ("Peça", "Assistente de furação", "Hole", "Furo", "peca", ["PartDesign_Hole"], "Furos com rosca, rebaixo e escareado."),
    ("Peça", "Casca", "Shell", "Casca", "peca", ["PartDesign_Thickness"], ""),
    ("Peça", "Inclinação", "Draft", "Ângulo de saída", "peca", ["PartDesign_Draft"], ""),
    ("Peça", "Espelhar", "Mirror", "Espelhar", "peca", ["PartDesign_Mirrored"], ""),
    ("Peça", "Padrão linear", "Linear pattern", "Padrão linear", "peca", ["PartDesign_LinearPattern"], ""),
    ("Peça", "Padrão circular", "Circular pattern", "Padrão circular", "peca", ["PartDesign_PolarPattern"], ""),
    ("Peça", "Geometria de referência (plano)", "Datum plane / Work plane", "Referências", "peca",
     ["PartDesign_CompDatums"], ""),
    ("Peça", "Instant3D (arrastar cotas)", "Edit feature dimensions", "Cotas da operação", "peca", ["Prumo_Cotas"],
     "Duplo clique na face mostra as cotas da operação para editar."),
    ("Peça", "Propriedades personalizadas", "iProperties / Attributes", "Propriedades da peça", "peca",
     ["Prumo_Propriedades"], "Código, denominação, revisão e material alimentam a lista de materiais e a legenda."),
    ("Peça", "Configurações / Tabela de projeto", "Configurations / iParts", "Variantes da peça", "peca",
     ["Prumo_Variantes"], "Parâmetros (P, M, G...) ligados às cotas por expressão."),
    ("Peça", "DriveWorksXpress", "iLogic / Rules", "Modelo com regras", "peca", ["Prumo_Modelo"],
     "Placa com furos, flange, suporte em L, eixo escalonado, com regras de projeto."),
    ("Peça", "Combinar (subtrair/adicionar)", "Boolean / Combine", "Subtrair, Unir, Interseção", "peca",
     ["Part_Cut", "Part_Fuse", "Part_Common"], "Subtrair: primeiro a peça base, depois a ferramenta."),
    ("Avaliar", "Propriedades de massa", "Mass properties", "Propriedades de massa", "peca", ["Prumo_Massa"], ""),
    ("Avaliar", "Medir", "Measure", "Medir", "inicio", ["Std_Measure"], ""),
    ("Tubulação", "Routing (tubulação)", "Piping / Pipe Routing", "Tubos e conexões", "tubulacao", ["Prumo_Tubulacao"],
     "Desenhe o traçado com o Esboço 3D (aba Tubulação → Esboço 3D); joelhos, tês e reduções saem do catálogo (PVC soldável Tigre)."),
    ("Estruturas", "Membro estrutural", "Frame generator / Structure", "Estrutura soldada", "estruturas",
     ["Prumo_Estrutura"], "Perfis brasileiros (W, U, L, tubos, metalon) sobre as linhas de um esboço."),
    ("Estruturas", "Perfil personalizado (biblioteca de perfis)", "Custom profile", "Seção personalizada",
     "estruturas", ["Prumo_SecaoPersonalizada"], "Esboço fechado vira perfil, com área, inércias e torção."),
    ("Estruturas", "Grupos de membros", "Frame members", "Editar estrutura", "estruturas", ["Prumo_EditarEstrutura"], ""),
    ("Estruturas", "Aparar/estender", "Trim / Notch", "Cantos", "estruturas", ["Prumo_Cantos"],
     "Meia-esquadria, topo (qual passa) e recorte pelo contorno."),
    ("Estruturas", "Cantoneira (gusset)", "Gusset", "Reforço", "estruturas", ["Prumo_Reforco"], ""),
    ("Estruturas", "Tampa de extremidade", "End cap", "Tampa de extremidade", "estruturas", ["Prumo_Tampa"], ""),
    ("Estruturas", "Cordão de solda", "Weld bead", "Cordão de solda", "estruturas", ["Prumo_Solda"], ""),
    ("Estruturas", "Lista de corte", "Cut list", "Lista de corte", "estruturas", ["Prumo_ListaDeCorte"], ""),
    ("Chapa", "Flange-base/aba", "Base flange", "Parede base", "chapa", ["SheetMetal_AddBase"], ""),
    ("Chapa", "Flange de aresta", "Edge flange / Flange", "Aba", "chapa", ["SheetMetal_AddWall"], ""),
    ("Chapa", "Bainha", "Hem", "Bainha", "chapa", ["SheetMetal_AddHem"], ""),
    ("Chapa", "Planificar", "Unfold / Flat pattern", "Planificar / Planificar em DXF", "chapa",
     ["Prumo_ChapaDXF", "SheetMetal_Unfold"], "Planificar em DXF usa o fator K do material e grava contorno e dobras."),
    ("Chapa", "Tabela de dobra / fator K", "Bend table / K-factor", "Tabela de fator K", "chapa", ["Prumo_TabelaK"],
     "Aço carbono, inox, alumínio e DIN 6935."),
    ("Montagem", "Inserir componentes", "Place / Insert component", "Inserir componente", "montagem",
     ["Assembly_Insert"], ""),
    ("Montagem", "Posicionamento coincidente", "Mate / Constraint (flush)", "Coincidente / distância", "montagem",
     ["Assembly_CreateJointDistance"], "Distância 0 = coincidente."),
    ("Montagem", "Posicionamento concêntrico", "Insert / Axis constraint", "Concêntrica", "montagem",
     ["Assembly_CreateJointCylindrical"], ""),
    ("Montagem", "Fixar componente", "Ground", "Fixar peça", "montagem", ["Assembly_ToggleGrounded"],
     "Uma peça fixa é obrigatória antes de montar."),
    ("Montagem", "Detecção de interferência", "Analyze interference", "Verificar interferência", "montagem",
     ["Prumo_Interferencia"], ""),
    ("Montagem", "Pack and Go", "Copy design / Pack and Go", "Copiar projeto", "inicio", ["Prumo_CopiarProjeto"], ""),
    ("Desenho", "Folha de desenho", "Drawing sheet", "Folha ABNT", "desenho", ["Prumo_NovaFolha"],
     "A0 a A4 com legenda brasileira; com a peça selecionada, já coloca as vistas no 1º diedro."),
    ("Desenho", "Vista de modelo / projetada", "Base / Projected view", "Vista", "desenho", ["TechDraw_View"], ""),
    ("Desenho", "Vista de seção", "Section view", "Corte", "desenho", ["TechDraw_SectionGroup"], ""),
    ("Desenho", "Vista de detalhe", "Detail view", "Detalhe", "desenho", ["TechDraw_DetailView"], ""),
    ("Desenho", "Cota inteligente", "Dimension", "Cota", "desenho", ["TechDraw_CompDimensionTools"], ""),
    ("Desenho", "Balão", "Balloon", "Balão", "desenho", ["TechDraw_Balloon"], ""),
    ("Desenho", "Lista de materiais", "Parts list / BOM", "Lista de materiais", "desenho", ["Prumo_ListaMateriais"], ""),
    ("Simulação", "SimulationXpress / Simulation", "Stress analysis", "Assistente de simulação", "simulacao",
     ["Prumo_AssistenteFEM"], ""),
    ("Simulação", "Simulation (vigas / estrutura soldada)", "Frame analysis", "Simular estrutura", "estruturas",
     ["Prumo_AnaliseEstrutura"], "Apoios clicando nos nós, combinações NBR 8681 e verificação NBR 8800."),
    ("Simulação", "Simulation Advisor (estrutura soldada)", "Frame analysis wizard", "Assistente de estruturas",
     "estruturas", ["Prumo_AssistenteEstrutura"], "Passo a passo com pendências, cálculo, ligações e memória."),
    ("Simulação", "Simulation: articulação / treliça (beam joints)", "Beam end release", "Rótula / treliça",
     "estruturas", ["Prumo_AnaliseEstrutura"], "No painel da simulação: modo Rótula, clicando perto da ponta."),
]

CONCEITOS = [
    ("Corpo (Body)", "Toda peça da aba Peça fica dentro de um Corpo, que guarda as operações em ordem. Em geral, "
                     "um corpo = uma peça."),
    ("Árvore do modelo", "É a FeatureManager. Se o painel sumir, Início → Árvore do modelo traz de volta."),
    ("Ponta (Tip)", "A barra de reversão do SolidWorks é a 'ponta' do corpo: botão direito na operação → "
                    "Definir ponta, para inserir operações no meio do histórico."),
    ("Esboço em face", "Esboço em face gerada pode quebrar quando uma operação anterior muda (problema de nomes "
                       "de face). Prefira os planos da origem ou planos de referência."),
    ("Função antes ou peça antes", "Os dois jeitos funcionam no Prumo: sem seleção, o comando abre um painel que "
                                   "diz o que selecionar."),
    ("Bancadas", "O FreeCAD organiza os comandos em bancadas (Peça, Sólidos, Chapa...). No Prumo a faixa troca de "
                 "bancada sozinha conforme a aba."),
]


def filtrar(texto):
    t = (texto or "").strip().lower()
    if not t:
        return list(EQUIVALENCIAS)
    return [e for e in EQUIVALENCIAS if any(t in str(x).lower() for x in e[:4] + (e[6],))]


class GuiaMigracao(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        import PrumoPainel as P
        self.setObjectName("PrumoPainel")
        self.setStyleSheet(P.qss())
        self.setWindowTitle("Vindo do SolidWorks / ZW3D")
        raiz = QtWidgets.QVBoxLayout(self)
        raiz.setContentsMargins(10, 10, 10, 10)
        raiz.setSpacing(10)
        card1, lay = P.bloco("Onde fica cada comando", "selecao")
        raiz.addWidget(card1, 3)
        self.busca = QtWidgets.QLineEdit()
        self.busca.setPlaceholderText("Procure pelo nome que você conhece (ex.: filete, posicionamento, gusset)")
        self.busca.textChanged.connect(self._preencher)
        lay.addWidget(self.busca)
        self.tabela = QtWidgets.QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["Área", "SolidWorks", "Outros CAD (ZW3D, Inventor, Fusion)",
                                               "No Prumo", "Observação"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tabela.doubleClicked.connect(lambda *_: self.mostrar_onde())
        lay.addWidget(self.tabela, 1)
        bl = QtWidgets.QHBoxLayout()
        self.bt_onde = QtWidgets.QPushButton("Mostrar onde")
        self.bt_onde.clicked.connect(self.mostrar_onde)
        bl.addWidget(self.bt_onde)
        bl.addStretch(1)
        lay.addLayout(bl)
        card2, lay2 = P.bloco("Diferenças de conceito", "info")
        raiz.addWidget(card2, 2)
        txt = "".join("<p><b>%s.</b> %s</p>" % c for c in CONCEITOS)
        lb = QtWidgets.QLabel(txt)
        lb.setWordWrap(True)
        lb.setAlignment(QtCore.Qt.AlignTop)
        lay2.addWidget(lb)
        self._linhas = []
        self._preencher()

    def _preencher(self, *_a):
        self._linhas = filtrar(self.busca.text())
        self.tabela.setRowCount(len(self._linhas))
        for r, e in enumerate(self._linhas):
            for c, v in enumerate((e[0], e[1], e[2], e[3], e[6])):
                it = QtWidgets.QTableWidgetItem(v)
                it.setToolTip(v)
                self.tabela.setItem(r, c, it)
        self.tabela.resizeColumnsToContents()
        self.tabela.setWordWrap(True)
        self.tabela.resizeRowsToContents()
        if self._linhas:
            self.tabela.selectRow(0)

    def mostrar_onde(self):
        r = self.tabela.currentRow()
        if not (0 <= r < len(self._linhas)):
            return False
        e = self._linhas[r]
        try:
            import PrumoTutorial
            return PrumoTutorial.destacar(e[4], e[5])
        except Exception:
            return False


_estado = {"dock": None}


def mostrar():
    mw = FreeCADGui.getMainWindow()
    dock = _estado["dock"]
    try:
        vivo = dock is not None and dock.objectName() is not None
    except RuntimeError:
        vivo = False
    if not vivo:
        dock = QtWidgets.QDockWidget("Vindo do SolidWorks / ZW3D", mw)
        dock.setObjectName("PrumoGuiaMigracao")
        dock.setWidget(GuiaMigracao(dock))
        dock.setMinimumWidth(420)
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        _estado["dock"] = dock
    dock.show()
    dock.raise_()
    try:
        import PrumoPainelLateral
        PrumoPainelLateral.acomodar(dock)     # vira aba do painel lateral
    except Exception:
        pass
    return dock


class CmdGuiaMigracao:
    def GetResources(self):
        import PrumoTutorial
        return {"Pixmap": PrumoTutorial.ICON, "MenuText": "Vindo do SolidWorks / ZW3D",
                "ToolTip": "Onde fica, no Prumo, cada comando que você já conhece de outro CAD, e as diferenças "
                           "de conceito que mais confundem."}

    def IsActive(self):
        return True

    def Activated(self):
        mostrar()
