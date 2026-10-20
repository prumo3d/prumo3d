# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - faixa de ferramentas (ribbon) em português para o FreeCAD.
"""Substitui as barras de ferramentas clássicas por uma faixa com abas e grupos.

Os botões reaproveitam as ações (QAction) dos próprios comandos do FreeCAD,
então habilitar/desabilitar, marcar e executar continuam sendo do FreeCAD.
Os rótulos são do Prumo 3D, em português, independentes da tradução instalada.
"""

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
L, S = "L", "S"  # botão grande / pequeno
ICON_L, ICON_S = 32, 18

# --------------------------------------------------------------------------
# Nomes das bancadas em português
WB_NAMES = {
    "PartDesignWorkbench": "Peça",
    "SketcherWorkbench": "Esboço",
    "PartWorkbench": "Sólidos",
    "AssemblyWorkbench": "Montagem",
    "TechDrawWorkbench": "Desenho técnico",
    "SpreadsheetWorkbench": "Planilha",
    "PrumoWorkbench": "Prumo",
    "SMWorkbench": "Chapa metálica",
    "DraftWorkbench": "Desenho 2D",
    "BIMWorkbench": "BIM / Arquitetura",
    "CAMWorkbench": "Usinagem (CAM)",
    "FemWorkbench": "Simulação (FEM)",
    "InspectionWorkbench": "Inspeção",
    "MaterialWorkbench": "Materiais",
    "MeshWorkbench": "Malhas",
    "OpenSCADWorkbench": "OpenSCAD",
    "PointsWorkbench": "Nuvem de pontos",
    "ReverseEngineeringWorkbench": "Engenharia reversa",
    "RobotWorkbench": "Robótica",
    "SurfaceWorkbench": "Superfícies",
    "TestWorkbench": "Testes",
    "NoneWorkbench": "Nenhuma",
}

# --------------------------------------------------------------------------
# Abas. Cada item: (comando, tamanho, rótulo). "\n" quebra o rótulo grande.
TABS = [
    {"id": "inicio", "label": "Início", "wb": None, "panels": [
        ("Arquivo", [
            ("Std_New", L, "Novo"), ("Std_Open", L, "Abrir"), ("Std_Save", L, "Salvar"),
            ("Std_SaveAs", S, "Salvar como"), ("Std_Import", S, "Importar"), ("Std_Export", S, "Exportar"),
            ("Std_PrintPdf", S, "Exportar PDF"), ("Std_Print", S, "Imprimir"), ("Std_ProjectInfo", S, "Info. do projeto"),
        ]),
        ("Editar", [
            ("Std_Undo", S, "Desfazer"), ("Std_Redo", S, "Refazer"), ("Std_Refresh", S, "Recalcular"),
            ("Std_Cut", S, "Recortar"), ("Std_Copy", S, "Copiar"), ("Std_Paste", S, "Colar"),
            ("Std_Delete", S, "Excluir"), ("Std_Placement", S, "Posicionamento"), ("Std_Edit", S, "Editar objeto"),
        ]),
        ("Vista", [
            ("Std_ViewFitAll", L, "Enquadrar\ntudo"), ("Std_ViewIsometric", L, "Isométrica"),
            ("Std_ViewFront", S, "Frontal"), ("Std_ViewTop", S, "Superior"), ("Std_ViewRight", S, "Direita"),
            ("Std_ViewRear", S, "Traseira"), ("Std_ViewBottom", S, "Inferior"), ("Std_ViewLeft", S, "Esquerda"),
            ("Std_ViewFitSelection", S, "Enquadrar seleção"), ("Std_DrawStyle", S, "Estilo de exibição"),
            ("Std_AlignToSelection", S, "Alinhar à seleção"),
        ]),
        ("Ferramentas", [
            ("Std_Measure", L, "Medir"), ("Part_SelectFilter", S, "Filtro de seleção"),
            ("Std_ToggleClipPlane", S, "Plano de corte"), ("Prumo_Arvore", S, "Árvore do modelo"),
            ("Std_TreeViewActions", S, "Opções da árvore"),
            ("Std_DlgMacroExecute", S, "Macros"), ("Std_DlgPreferences", L, "Preferências"),
        ]),
        ("Estrutura", [
            ("Std_Part", S, "Nova parte"), ("Std_Group", S, "Novo grupo"), ("Part_Datums", S, "Referências"),
            ("Std_LinkActions", S, "Vínculos"), ("Std_VarSet", S, "Variáveis"),
        ]),
    ]},
    {"id": "esboco", "label": "Esboço", "wb": "SketcherWorkbench", "panels": [
        ("Esboço", [
            ("Sketcher_NewSketch", L, "Novo\nesboço"), ("Sketcher_EditSketch", L, "Editar\nesboço"),
            ("Sketcher_LeaveSketch", L, "Concluir\nesboço"),
            ("Sketcher_MapSketch", S, "Anexar"), ("Sketcher_ReorientSketch", S, "Reorientar"),
            ("Sketcher_ViewSketch", S, "Vista normal"), ("Sketcher_ViewSection", S, "Vista em corte"),
            ("Sketcher_ValidateSketch", S, "Validar"), ("Sketcher_MergeSketches", S, "Mesclar"),
            ("Sketcher_MirrorSketch", S, "Espelhar esboço"),
        ]),
        ("Desenhar", [
            ("Sketcher_CreateLine", L, "Linha"), ("Sketcher_CompCreateRectangles", L, "Retângulo"),
            ("Sketcher_CompCreateConic", L, "Círculo"), ("Sketcher_CompCreateArc", L, "Arco"),
            ("Sketcher_CreatePolyline", S, "Linha e arco tangente"), ("Sketcher_CreatePoint", S, "Ponto"),
            ("Sketcher_CompCreateRegularPolygon", S, "Polígono"), ("Sketcher_CompSlot", S, "Rasgo"),
            ("Sketcher_CompCreateBSpline", S, "Curva B-spline"), ("Sketcher_ToggleConstruction", S, "Construção"),
        ]),
        ("Restrições", [
            ("Sketcher_CompDimensionTools", L, "Cota"),
            ("Sketcher_ConstrainCoincidentUnified", S, "Coincidente"), ("Sketcher_CompHorVer", S, "Horiz. / vert."),
            ("Sketcher_ConstrainParallel", S, "Paralela"), ("Sketcher_ConstrainPerpendicular", S, "Perpendicular"),
            ("Sketcher_ConstrainTangent", S, "Tangente"), ("Sketcher_ConstrainEqual", S, "Igual"),
            ("Sketcher_ConstrainSymmetric", S, "Simétrica"), ("Sketcher_ConstrainBlock", S, "Bloquear"),
            ("Sketcher_CompToggleConstraints", S, "Ativar restrição"),
        ]),
        ("Modificar", [
            ("Sketcher_CompCurveEdition", L, "Aparar"), ("Sketcher_CompCreateFillets", L, "Arredondar"),
            ("Sketcher_CompExternal", L, "Externa"),
            ("Sketcher_Offset", S, "Offset"), ("Sketcher_Symmetry", S, "Espelhar"), ("Sketcher_Translate", S, "Mover / matriz"),
            ("Sketcher_Rotate", S, "Rotacionar"), ("Sketcher_Scale", S, "Escala"), ("Sketcher_CarbonCopy", S, "Cópia carbono"),
            ("Sketcher_RemoveAxesAlignment", S, "Remover alinhamento"),
        ]),
        ("Auxiliares", [
            ("Sketcher_SelectConstraints", S, "Selecionar restrições"),
            ("Sketcher_SelectElementsAssociatedWithConstraints", S, "Selecionar geometria"),
            ("Sketcher_RestoreInternalAlignmentGeometry", S, "Geometria interna"),
            ("Sketcher_SwitchVirtualSpace", S, "Espaço virtual"), ("Sketcher_ArcOverlay", S, "Auxiliar de arcos"),
            ("Sketcher_JoinCurves", S, "Unir curvas"),
        ]),
    ]},
    {"id": "peca", "label": "Peça", "wb": "PartDesignWorkbench", "panels": [
        ("Corpo", [
            ("PartDesign_Body", L, "Novo\ncorpo"), ("PartDesign_CompSketches", L, "Esboço"),
            ("PartDesign_CompDatums", S, "Referências"), ("PartDesign_ShapeBinder", S, "Vínculo de forma"),
            ("PartDesign_SubShapeBinder", S, "Vínculo de subforma"), ("PartDesign_Clone", S, "Clonar"),
        ]),
        ("Adicionar material", [
            ("PartDesign_Pad", L, "Extrusão"), ("PartDesign_Revolution", L, "Revolução"),
            ("PartDesign_AdditiveLoft", S, "Loft"), ("PartDesign_AdditivePipe", S, "Varredura"),
            ("PartDesign_AdditiveHelix", S, "Hélice"), ("PartDesign_CompPrimitiveAdditive", S, "Primitivas"),
        ]),
        ("Remover material", [
            ("PartDesign_Pocket", L, "Cavidade"), ("PartDesign_Hole", L, "Furo"),
            ("PartDesign_Groove", S, "Ranhura"), ("PartDesign_SubtractiveLoft", S, "Loft"),
            ("PartDesign_SubtractivePipe", S, "Varredura"), ("PartDesign_SubtractiveHelix", S, "Hélice"),
            ("PartDesign_CompPrimitiveSubtractive", S, "Primitivas"),
        ]),
        ("Acabamento", [
            ("PartDesign_Fillet", L, "Arredondar"), ("PartDesign_Chamfer", L, "Chanfro"),
            ("PartDesign_Thickness", S, "Casca"), ("PartDesign_Draft", S, "Ângulo de saída"),
        ]),
        ("Padrões", [
            ("PartDesign_Mirrored", L, "Espelhar"), ("PartDesign_LinearPattern", S, "Padrão linear"),
            ("PartDesign_PolarPattern", S, "Padrão circular"), ("PartDesign_MultiTransform", S, "Multitransformação"),
        ]),
        ("Ferramentas", [
            ("PartDesign_Boolean", S, "Booleana"), ("Part_CheckGeometry", S, "Verificar geometria"),
            ("Sketcher_ValidateSketch", S, "Validar esboço"), ("Std_Measure", L, "Medir"),
        ]),
        ("Prumo", [
            ("Prumo_Cotas", L, "Cotas da\noperação"), ("Prumo_Propriedades", L, "Propriedades\nda peça"),
            ("Prumo_Massa", S, "Propriedades de massa"),
            ("Prumo_ListaMateriais", S, "Lista de materiais"), ("Prumo_NovaFolha", S, "Folha ABNT"),
        ]),
    ]},
    {"id": "solidos", "label": "Sólidos", "wb": "PartWorkbench", "panels": [
        ("Primitivas", [
            ("Part_Box", L, "Caixa"), ("Part_Cylinder", L, "Cilindro"),
            ("Part_Sphere", S, "Esfera"), ("Part_Cone", S, "Cone"), ("Part_Torus", S, "Toro"),
            ("Part_Tube", S, "Tubo"), ("Part_Primitives", S, "Mais primitivas"), ("Part_Builder", S, "Construtor"),
        ]),
        ("Criar", [
            ("Part_Extrude", L, "Extrusão"), ("Part_Revolve", L, "Revolução"),
            ("Part_Loft", S, "Loft"), ("Part_Sweep", S, "Varredura"), ("Part_MakeFace", S, "Face de arames"),
            ("Part_RuledSurface", S, "Superfície regrada"),
        ]),
        ("Modificar", [
            ("Part_Fillet", L, "Arredondar"), ("Part_Chamfer", L, "Chanfro"),
            ("Part_Mirror", S, "Espelhar"), ("Part_Scale", S, "Escala"), ("Part_CompOffset", S, "Offset"),
            ("Part_Thickness", S, "Casca"), ("Part_Section", S, "Seção"), ("Part_CrossSections", S, "Seções transversais"),
            ("Part_ProjectionOnSurface", S, "Projetar na superfície"),
        ]),
        ("Booleanas", [
            ("Part_Cut", L, "Subtrair"), ("Part_Fuse", L, "Unir"), ("Part_Common", L, "Interseção"),
            ("Part_Boolean", S, "Booleana"), ("Part_CompJoinFeatures", S, "Juntar formas"),
            ("Part_CompSplitFeatures", S, "Dividir formas"), ("Part_CompCompoundTools", S, "Compostos"),
            ("Part_CheckGeometry", S, "Verificar geometria"), ("Part_Defeaturing", S, "Remover detalhes"),
        ]),
    ]},
    {"id": "montagem", "label": "Montagem", "wb": "AssemblyWorkbench", "panels": [
        ("Montagem", [
            ("Assembly_CreateAssembly", L, "Nova\nmontagem"), ("Assembly_Insert", L, "Inserir\ncomponente"),
            ("Assembly_SolveAssembly", S, "Resolver"), ("Assembly_CreateView", S, "Vista explodida"),
            ("Assembly_CreateSimulation", S, "Simulação"), ("Prumo_ListaMateriais", S, "Lista de materiais"),
            ("Prumo_Massa", S, "Propriedades de massa"), ("Prumo_Propriedades", S, "Propriedades da peça"),
        ]),
        ("Juntas", [
            ("Assembly_ToggleGrounded", L, "Fixar"), ("Assembly_CreateJointFixed", L, "Junta\nfixa"),
            ("Assembly_CreateJointRevolute", S, "Revoluta"), ("Assembly_CreateJointCylindrical", S, "Cilíndrica"),
            ("Assembly_CreateJointSlider", S, "Deslizante"), ("Assembly_CreateJointBall", S, "Esférica"),
            ("Assembly_CreateJointDistance", S, "Distância"), ("Assembly_CreateJointParallel", S, "Paralela"),
            ("Assembly_CreateJointPerpendicular", S, "Perpendicular"), ("Assembly_CreateJointAngle", S, "Ângulo"),
            ("Assembly_CreateJointRackPinion", S, "Pinhão e cremalheira"), ("Assembly_CreateJointScrew", S, "Parafuso"),
            ("Assembly_CreateJointGearBelt", S, "Engrenagem / correia"),
        ]),
    ]},
    {"id": "desenho", "label": "Desenho", "wb": "TechDrawWorkbench", "panels": [
        ("Folha", [
            ("Prumo_NovaFolha", L, "Folha\nABNT"), ("TechDraw_PageDefault", S, "Nova folha"),
            ("TechDraw_PageTemplate", S, "Folha de modelo"), ("Prumo_ListaMateriais", S, "Lista de materiais"),
            ("TechDraw_FillTemplateFields", S, "Preencher carimbo"), ("TechDraw_RedrawPage", S, "Redesenhar"),
            ("TechDraw_PrintAll", S, "Imprimir tudo"),
        ]),
        ("Vistas", [
            ("TechDraw_View", L, "Vista"), ("TechDraw_SectionGroup", L, "Corte"), ("TechDraw_DetailView", L, "Detalhe"),
            ("TechDraw_BrokenView", S, "Vista interrompida"), ("TechDraw_ActiveView", S, "Vista da tela"),
            ("TechDraw_DraftView", S, "Vista 2D"), ("TechDraw_ClipGroup", S, "Recorte"), ("TechDraw_StackGroup", S, "Ordem das vistas"),
        ]),
        ("Cotas", [
            ("TechDraw_CompDimensionTools", L, "Cota"), ("TechDraw_Balloon", L, "Balão"),
            ("TechDraw_AxoLengthDimension", S, "Cota axonométrica"), ("TechDraw_DimensionRepair", S, "Reparar cotas"),
            ("TechDraw_ExtensionInsertPrefixGroup", S, "Prefixo ⌀"), ("TechDraw_ExtensionIncreaseDecreaseGroup", S, "Casas decimais"),
        ]),
        ("Anotação", [
            ("TechDraw_Annotation", L, "Texto"), ("TechDraw_WeldSymbol", L, "Solda"),
            ("TechDraw_LeaderLine", S, "Linha de chamada"), ("TechDraw_RichTextAnnotation", S, "Texto formatado"),
            ("TechDraw_SurfaceFinishSymbols", S, "Rugosidade"), ("TechDraw_HoleShaftFit", S, "Ajuste furo / eixo"),
            ("TechDraw_CenterLineGroup", S, "Linha de centro"), ("TechDraw_ExtensionCircleCenterLinesGroup", S, "Centro de círculo"),
            ("TechDraw_ExtensionThreadsGroup", S, "Rosca cosmética"), ("TechDraw_CosmeticVertexGroup", S, "Vértice cosmético"),
            ("TechDraw_2PointCosmeticLine", S, "Linha cosmética"),
        ]),
        ("Aparência", [
            ("TechDraw_Hatch", S, "Hachura (imagem)"), ("TechDraw_GeometricHatch", S, "Hachura geométrica"),
            ("TechDraw_DecorateLine", S, "Estilo de linha"), ("TechDraw_ShowAll", S, "Arestas ocultas"),
            ("TechDraw_ToggleFrame", S, "Molduras"), ("TechDraw_ExtensionLockUnlockView", S, "Travar vista"),
        ]),
        ("Exportar", [
            ("Std_PrintPdf", L, "PDF"), ("TechDraw_ExportPageDXF", S, "DXF"), ("TechDraw_ExportPageSVG", S, "SVG"),
        ]),
    ]},
    {"id": "estruturas", "label": "Estruturas", "wb": None, "panels": [
        ("Estrutura soldada", [
            ("Prumo_Estrutura", L, "Estrutura\nsoldada"), ("Prumo_EditarEstrutura", L, "Editar\nestrutura"),
            ("Prumo_Cantos", L, "Cantos"),
            ("Prumo_TrocarPerfil", S, "Trocar perfil"), ("Prumo_AtualizarEstrutura", S, "Atualizar estrutura"),
        ]),
        ("Reforços e ligações", [
            ("Prumo_Reforco", L, "Reforço"), ("Prumo_Tampa", L, "Tampa de\nextremidade"),
            ("Prumo_PlacaBase", L, "Placa de\nbase"),
        ]),
        ("Solda", [
            ("Prumo_Solda", L, "Cordão de\nsolda"), ("Prumo_ListaSoldas", S, "Lista de soldas"),
            ("Prumo_ListaDeCorte", S, "Lista de corte"),
        ]),
        ("Peças padronizadas", [
            ("Prumo_Fixador", L, "Parafuso,\nporca, arruela"),
        ]),
        ("Conferir", [
            ("Prumo_Massa", L, "Propriedades\nde massa"), ("Prumo_ListaMateriais", L, "Lista de\nmateriais"),
            ("Prumo_Propriedades", S, "Propriedades da peça"),
            ("Std_Measure", S, "Medir"),
        ]),
        ("Aprender", [("Prumo_TutorialEstrutura", L, "Tutorial")]),
    ]},
    {"id": "chapa", "label": "Chapa", "wb": "SMWorkbench", "panels": [
        ("Criar", [
            ("SheetMetal_AddBase", L, "Parede\nbase"), ("SheetMetal_BaseShape", S, "Formas prontas"),
            ("SheetMetal_FromSolid", S, "Chapa de sólido"), ("SheetMetal_SketchOnSheet", S, "Esboço na chapa"),
        ]),
        ("Dobras e abas", [
            ("SheetMetal_AddWall", L, "Aba"), ("SheetMetal_AddFoldWall", L, "Dobrar\npor linha"),
            ("SheetMetal_Extrude", S, "Estender"), ("SheetMetal_ExtendBySketch", S, "Estender por esboço"),
            ("SheetMetal_AddBend", S, "Dobra em aresta"), ("SheetMetal_AddHem", S, "Bainha"),
            ("SheetMetal_AddJunction", S, "Junção (fenda)"),
        ]),
        ("Recortes", [
            ("SheetMetal_AddCutout", L, "Recorte"), ("SheetMetal_AddRelief", S, "Alívio de dobra"),
            ("SheetMetal_AddCornerRelief", S, "Alívio de canto"), ("SheetMetal_Forming", S, "Estampar"),
        ]),
        ("Planificar", [
            ("SheetMetal_Unfold", L, "Planificar"), ("SheetMetal_UnfoldUpdate", S, "Atualizar planificações"),
        ]),
    ]},
    {"id": "planilha", "label": "Planilha", "wb": "SpreadsheetWorkbench", "panels": [
        ("Planilha", [
            ("Spreadsheet_CreateSheet", L, "Nova\nplanilha"), ("Spreadsheet_Import", S, "Importar"),
            ("Spreadsheet_Export", S, "Exportar"), ("Spreadsheet_SetAlias", S, "Apelido"),
        ]),
        ("Células", [
            ("Spreadsheet_MergeCells", S, "Mesclar"), ("Spreadsheet_SplitCell", S, "Dividir"),
            ("Spreadsheet_StyleBold", S, "Negrito"), ("Spreadsheet_StyleItalic", S, "Itálico"),
            ("Spreadsheet_StyleUnderline", S, "Sublinhado"),
        ]),
        ("Alinhamento", [
            ("Spreadsheet_AlignLeft", S, "Esquerda"), ("Spreadsheet_AlignCenter", S, "Centro"),
            ("Spreadsheet_AlignRight", S, "Direita"), ("Spreadsheet_AlignTop", S, "Topo"),
            ("Spreadsheet_AlignVCenter", S, "Meio"), ("Spreadsheet_AlignBottom", S, "Base"),
        ]),
    ]},
    {"id": "simulacao", "label": "Simulação", "wb": "FemWorkbench", "panels": [
        # Na ordem em que a análise precisa ser montada
        ("Assistente", [("Prumo_AssistenteFEM", L, "Assistente\nde simulação")]),
        ("1 · Estudo", [("FEM_Analysis", L, "Novo\nestudo"), ("FEM_SolverCalculiXCcxTools", L, "Solver\nCalculiX")]),
        ("2 · Material", [("FEM_MaterialSolid", L, "Material\nsólido"), ("FEM_MaterialEditor", S, "Editor de materiais")]),
        ("3 · Fixações", [("FEM_ConstraintFixed", L, "Fixação"), ("FEM_ConstraintDisplacement", S, "Deslocamento imposto"),
                          ("FEM_ConstraintSpring", S, "Mola (apoio elástico)")]),
        ("4 · Cargas", [("FEM_ConstraintForce", L, "Força"), ("FEM_ConstraintPressure", S, "Pressão"),
                        ("FEM_ConstraintSelfWeight", S, "Peso próprio"), ("FEM_ConstraintCentrif", S, "Centrífuga")]),
        ("5 · Malha", [("FEM_MeshGmshFromShape", L, "Gerar\nmalha"), ("FEM_MeshRegion", S, "Refino local"),
                       ("FEM_MeshDisplayInfo", S, "Dados da malha"), ("FEM_MeshClear", S, "Limpar malha")]),
        ("6 · Calcular", [("FEM_SolverRun", L, "Calcular"), ("FEM_SolverControl", S, "Controle do solver")]),
        ("7 · Resultados", [("FEM_ResultShow", L, "Ver\nresultados"), ("FEM_PostFilterWarp", S, "Deformada"),
                            ("FEM_PostFilterClipScalar", S, "Recorte por valor"), ("FEM_PostFilterDataAlongLine", S, "Gráfico ao longo de linha"),
                            ("FEM_ResultsPurge", S, "Limpar resultados")]),
    ]},
    {"id": "prumo", "label": "Prumo", "wb": None, "panels": [
        ("Prumo", [
            ("Prumo_Inicio", L, "Tela\ninicial"), ("Prumo_AplicarTema", L, "Aplicar\ntema"),
            ("Prumo_TemaEscuro", L, "Tema\nescuro"), ("Prumo_Sobre", L, "Sobre"),
        ]),
        ("Interface", [
            ("Prumo_TemaIcones", S, "Tema de ícones"), ("Prumo_BarrasClassicas", S, "Barras clássicas"),
            ("Prumo_RemoverSplash", S, "Splash original"), ("Prumo_ModoDistribuicao", S, "Modo distribuição"),
        ]),
        ("Aprender", [("Prumo_Tutorial", L, "Tutorial\nprimeira peça"),
                      ("Prumo_TutorialEstrutura", L, "Tutorial\nestrutura")]),
        ("Qualidade", [("Prumo_Testes", L, "Testes\nautomáticos")]),
    ]},
]

STD_TOOLBARS = {"File", "Edit", "Clipboard", "Workbench", "Macro", "View", "Individual Views", "Structure", "Help"}

RIBBON_QSS = """
#PrumoRibbon { background: #FFFFFF; }
#PrumoTabRow { background: #F5F8FC; border-bottom: 1px solid #DCE4EC; }
#PrumoTabRow QTabBar { background: transparent; }
#PrumoTabRow QTabBar::tab {
    background: transparent; color: #2E3B4A; border: none;
    padding: 7px 16px 6px 16px; margin: 0 1px; font-size: 10pt;
    border-top: 3px solid transparent;
}
#PrumoTabRow QTabBar::tab:hover { color: #003A70; background: #EAF1F8; }
#PrumoTabRow QTabBar::tab:selected {
    color: #003A70; background: #FFFFFF; font-weight: 600;
    border-top: 3px solid #F7BE00; border-left: 1px solid #DCE4EC; border-right: 1px solid #DCE4EC;
}
#PrumoBrand { color: #003A70; font-weight: 700; font-size: 10.5pt; padding: 0 14px 0 8px; }
#PrumoContent { background: #FFFFFF; border: none; border-bottom: 1px solid #DCE4EC; }
#PrumoContent > QWidget, #PrumoPage, #PrumoCol { background: #FFFFFF; }
#PrumoPage QWidget, #PrumoPage QLabel { background: #FFFFFF; color: #1F2A36; }
#PrumoTabRow QLabel { background: transparent; }
#PrumoPage #PrumoPanelTitle { color: #66727F; font-size: 8pt; padding: 1px 0 3px 0; background: transparent; }
#PrumoPage #PrumoSep { background: #DCE4EC; margin: 6px 0 6px 0; }
#PrumoPanel { background: transparent; border: none; }
#PrumoSplit, #PrumoResto { background: #FFFFFF; }
#PrumoSplit::handle:horizontal { background: #FFFFFF; border-left: 1px solid #DCE4EC; margin: 8px 4px 8px 4px; }
#PrumoSplit::handle:horizontal:hover { border-left: 3px solid #7FA3C9; margin: 8px 3px 8px 3px; }
#PrumoGrip { background: #F5F8FC; border-bottom: 1px solid #DCE4EC; }
#PrumoGrip:hover { background: #DCE8F4; }


#PrumoRibbon QToolButton {
    background: transparent; border: 1px solid transparent; border-radius: 5px;
    color: #1F2A36; padding: 2px 4px; font-size: 9pt;
}
#PrumoRibbon QToolButton:hover { background: #EAF1F8; border-color: #C9DAEA; }
#PrumoRibbon QToolButton:pressed, #PrumoRibbon QToolButton:checked { background: #D8E6F3; border-color: #9FBEDD; }
#PrumoRibbon QToolButton:disabled { color: #A3ADB8; }
#PrumoRibbon QToolButton[sw_size="L"] { padding: 3px 4px 2px 4px; }
#PrumoRibbon QToolButton[sw_size="L"][popupMode="1"] { padding-bottom: 12px; }
#PrumoRibbon QToolButton[sw_size="L"]::menu-button {
    subcontrol-origin: border; subcontrol-position: bottom center;
    width: 100%; height: 11px; border: none; border-top: 1px solid transparent;
    border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;
}
#PrumoRibbon QToolButton[sw_size="L"]::menu-button:hover { background: #D8E6F3; }
#PrumoRibbon QToolButton[sw_size="S"][popupMode="1"] { padding-right: 14px; }
#PrumoRibbon QToolButton::menu-arrow { width: 7px; height: 7px; }
#PrumoQuick QToolButton { padding: 3px; border-radius: 4px; }
#PrumoTabRow QToolButton#PrumoWbBtn {
    background: #FFFFFF; color: #003A70; font-weight: 600; font-size: 9pt;
    border: 1px solid #C9D5E2; border-radius: 6px; padding: 3px 22px 3px 10px; margin: 0 2px;
}
#PrumoTabRow QToolButton#PrumoWbBtn:hover { background: #EAF1F8; border-color: #7FA3C9; }
#PrumoTabRow QToolButton#PrumoWbBtn::menu-indicator {
    subcontrol-origin: padding; subcontrol-position: center right; right: 7px; width: 9px; height: 9px;
}
#PrumoWbSep { color: #D5DEE8; background: transparent; }
"""

# Estilo global complementar (aplicado sobre o tema do FreeCAD)
GLOBAL_QSS = """
/*PRUMO-BEGIN*/
QMenuBar { background: #FFFFFF; border: none; border-bottom: 1px solid #E3EAF2; padding: 2px 6px; }
QMenuBar::item { padding: 4px 10px; border-radius: 4px; color: #1F2A36; background: transparent; }
QMenuBar::item:disabled { color: #9AA7B4; }
QMenuBar::item:selected { background: #EAF1F8; color: #003A70; }
QMenu { background: #FFFFFF; color: #1F2A36; border: 1px solid #D5DEE8; padding: 4px; }
QMenu::item { padding: 5px 26px 5px 26px; border-radius: 4px; color: #1F2A36; background: transparent; }
QMenu::item:disabled { color: #9AA7B4; }
QMenu::item:selected { background: #EAF1F8; color: #003A70; }
QMenu::separator { height: 1px; background: #E3EAF2; margin: 4px 8px; }
QStatusBar { background: #F5F8FC; border-top: 1px solid #E3EAF2; color: #4A5866; }
QDockWidget { font-weight: 600; color: #003A70; }
QDockWidget::title { background: #F5F8FC; padding: 6px 8px; border-bottom: 1px solid #E3EAF2; }
QTabBar::tab:selected { color: #003A70; }
QToolTip { background: #FFFFFF; color: #1F2A36; border: 1px solid #D5DEE8; padding: 8px 10px; }
/*PRUMO-END*/
"""


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def _clean(text):
    return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&").strip()


def _cmd_actions(name):
    try:
        cmd = FreeCADGui.Command.get(name)
    except Exception:
        return []
    if cmd is None:
        return []
    try:
        acts = [a for a in (cmd.getAction() or []) if a is not None]
    except Exception:
        acts = []
    if not acts and (name.startswith("Prumo_") or name.startswith("FEM_")):
        acts = [_own_action(name, cmd)]
    return [a for a in acts if a is not None]


_OWN_ACTIONS = {}


def _own_action(name, cmd):
    """O FreeCAD só cria a QAction de um comando Python quando alguma barra/menu o usa.

    Os comandos Prumo só entram em barras da bancada Prumo 3D, então antes de ela ser
    ativada eles não têm ação. Criamos uma ação própria que executa o comando.
    """
    if name in _OWN_ACTIONS:
        return _OWN_ACTIONS[name]
    try:
        info = cmd.getInfo()
    except Exception:
        info = {}
    import os as _os
    QAction = getattr(QtGui, "QAction", None) or QtWidgets.QAction
    act = QAction(FreeCADGui.getMainWindow())

    def tr(texto):
        # getInfo devolve o texto de origem (inglês): traduz como o FreeCAD faria
        if not texto:
            return texto
        for ctx in (name, cmd.__class__.__name__ if hasattr(cmd, "__class__") else name):
            t = QtCore.QCoreApplication.translate(ctx, texto)
            if t and t != texto:
                return t
        return texto

    act.setText(tr(info.get("menuText")) or name)
    tip = tr(info.get("toolTip") or "")
    act.setToolTip(tip)
    act.setStatusTip(tip)
    pix = info.get("pixmap") or ""
    if pix and _os.path.isfile(pix):
        act.setIcon(QtGui.QIcon(pix))
    elif pix:
        try:
            act.setIcon(FreeCADGui.getIcon(pix))
        except Exception:
            pass
    act.triggered.connect(lambda checked=False, n=name: FreeCADGui.runCommand(n, 0))
    _OWN_ACTIONS[name] = act
    return act


# -------------------------------------------------------------------------- ícones e dicas
import hashlib
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIS_CACHE = {}
_TIP_CACHE = {}


def _t(texto):
    """Cores do tema ativo (claro ou escuro)."""
    try:
        import PrumoEstilo
        return PrumoEstilo.tema(texto)
    except Exception:
        return texto


def _escuro():
    try:
        import PrumoEstilo
        return PrumoEstilo.escuro()
    except Exception:
        return False


def _disabled_pixmap(pm):
    """Versão desabilitada legível: véu cinza-azulado sobre o ícone, 78 % de opacidade."""
    tinted = QtGui.QPixmap(pm.size())
    tinted.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(tinted)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)
    if not _escuro():
        p.fillRect(tinted.rect(), QtGui.QColor(150, 166, 186, 120))
    p.end()
    out = QtGui.QPixmap(pm.size())
    out.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(out)
    p.setOpacity(0.5 if _escuro() else 0.78)
    p.drawPixmap(0, 0, tinted)
    p.end()
    out.setDevicePixelRatio(pm.devicePixelRatio())
    return out


def _with_disabled(icon, size):
    """Mesmo ícone, com o modo Desabilitado desenhado pelo Prumo 3D."""
    if icon.isNull():
        return icon
    key = (icon.cacheKey(), size)
    if key in _DIS_CACHE:
        return _DIS_CACHE[key]
    dpr = 2.0
    pm = icon.pixmap(QtCore.QSize(size, size) * dpr)
    pm.setDevicePixelRatio(dpr)
    out = QtGui.QIcon()
    out.addPixmap(pm, QtGui.QIcon.Normal)
    out.addPixmap(pm, QtGui.QIcon.Active)
    out.addPixmap(_disabled_pixmap(pm), QtGui.QIcon.Disabled)
    _DIS_CACHE[key] = out
    return out


def _tip_image(icon):
    """Grava o ícone em 44 px para usar na dica rica (o QToolTip só aceita arquivo)."""
    d = os.path.join(FreeCAD.getUserAppDataDir(), "PrumoUI", "dicas")
    key = str(icon.cacheKey())
    if key in _TIP_CACHE:
        return _TIP_CACHE[key]
    try:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, hashlib.md5(key.encode()).hexdigest()[:12] + ".png")
        icon.pixmap(88, 88).save(path)
        _TIP_CACHE[key] = path.replace("\\", "/")
    except Exception:
        _TIP_CACHE[key] = None
    return _TIP_CACHE[key]


def _tip_desc(raw, titles):
    """Texto da dica do FreeCAD sem o título repetido e sem o nome interno do comando."""
    if not raw:
        return ""
    doc = QtGui.QTextDocument()
    doc.setHtml(raw) if "<" in raw else doc.setPlainText(raw)
    out = []
    low = {_clean(t).lower() for t in titles if t}
    for line in doc.toPlainText().splitlines():
        t = line.strip()
        if not t or _clean(t).lower() in low:
            continue
        if " " not in t and "_" in t:      # PartDesign_Pad, Std_Open...
            continue
        out.append(t)
    return " ".join(out)


def _rich_tip(icon, title, desc, shortcut):
    img = _tip_image(icon) if not icon.isNull() else None
    body = "<div style='font-weight:600; color:#003A70; font-size:10pt'>{}</div>".format(title)
    if desc:
        body += "<div style='color:#4A5866; margin-top:3px'>{}</div>".format(desc)
    if shortcut:
        body += ("<div style='margin-top:6px'><span style='background:#EEF2F8; color:#003A70; "
                 "font-weight:600'>&nbsp;{}&nbsp;</span></div>").format(shortcut)
    body = _t(body)
    if not img:
        return "<div style='max-width:300px'>{}</div>".format(body)
    return ("<table cellspacing='0' cellpadding='0'><tr>"
            "<td valign='top' style='padding-right:10px'><img src='{}' width='44' height='44'></td>"
            "<td valign='top' width='240'>{}</td></tr></table>").format(img, body)


# --------------------------------------------------------------------------
L_ALTURA = 98   # botão grande: ícone + rótulo em até duas linhas (+ seta de menu)
S_ALTURA = 30   # botão pequeno (três por coluna)

# Altura da área dos botões (arrastável pela borda de baixo da faixa; duplo clique volta ao padrão)
ALTURA_PADRAO, ALTURA_MIN, ALTURA_MAX = 136, 112, 200


def medidas(altura):
    """Tamanhos dos botões e ícones para uma altura da área de botões."""
    altura = max(ALTURA_MIN, min(ALTURA_MAX, int(altura)))
    l_alt = altura - 38
    s_alt = max(26, (l_alt - 6) // 3)
    icon_l = max(24, min(48, int(round(32.0 * l_alt / 98))))
    icon_s = max(16, min(24, int(round(18.0 * s_alt / 30))))
    return {"altura": altura, "L": l_alt, "S": s_alt, "iconL": icon_l, "iconS": icon_s}


_MED = medidas(ALTURA_PADRAO)


def altura_salva():
    h = _params().GetInt("RibbonHeight", 0)
    return ALTURA_PADRAO if h <= 0 else max(ALTURA_MIN, min(ALTURA_MAX, h))


def _quebra(texto):
    """Rótulos longos dos botões grandes em duas linhas, quebrando no espaço mais central."""
    if "\n" in texto or len(texto) <= 11 or " " not in texto:
        return texto
    meio = len(texto) / 2.0
    pos = min((i for i, c in enumerate(texto) if c == " "), key=lambda i: abs(i - meio))
    return texto[:pos] + "\n" + texto[pos + 1:]


class RibbonButton(QtWidgets.QToolButton):
    """Botão ligado a uma ou várias QActions de um comando do FreeCAD."""

    def __init__(self, actions, size, label, parent=None):
        super().__init__(parent)
        self._actions = actions
        self._size = size
        self._label = label
        self._current = actions[0]
        self.setProperty("sw_size", size)
        self.setAutoRaise(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        # Política "Minimum" na horizontal: o botão nunca fica mais estreito que o texto (sem "Enq…tudo");
        # se a janela for estreita, a faixa ganha rolagem em vez de cortar os nomes.
        if size == L:
            self.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            self.setIconSize(QtCore.QSize(_MED["iconL"], _MED["iconL"]))
            self.setMinimumWidth(54)
            self.setFixedHeight(_MED["L"])
            self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        else:
            self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
            self.setIconSize(QtCore.QSize(_MED["iconS"], _MED["iconS"]))
            self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
            self.setFixedHeight(_MED["S"])
        if len(actions) > 1:
            menu = QtWidgets.QMenu(self)
            for a in actions:
                menu.addAction(_proxy_selecao(a, self) or a)
            menu.triggered.connect(self._on_menu)
            self.setMenu(menu)
            self.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.clicked.connect(self._on_click)
        for a in actions:
            a.changed.connect(self._sync)
        self._sync()

    def largura_do_texto(self):
        """Largura que o rótulo precisa (o sizeHint do Qt subestima com folha de estilo e Poppins)."""
        self.ensurePolished()
        fm = QtGui.QFontMetrics(self.font())
        linhas = self.text().split("\n") or [""]
        txt = max(fm.horizontalAdvance(l) for l in linhas) if hasattr(fm, "horizontalAdvance") else \
            max(fm.width(l) for l in linhas)
        if self._size == L:
            return max(54, txt + 16, _MED["iconL"] + 16)
        if self.toolButtonStyle() == QtCore.Qt.ToolButtonIconOnly:
            return _MED["iconS"] + 14 + (14 if self.menu() is not None else 0)
        return _MED["iconS"] + txt + 22 + (14 if self.menu() is not None else 0)

    def _ajustar_largura(self):
        self.setMinimumWidth(self.largura_do_texto())

    def setToolButtonStyle(self, estilo):
        super().setToolButtonStyle(estilo)
        if getattr(self, "_size", None) is not None and self.text():
            self._ajustar_largura()

    def _on_menu(self, action):
        self._current = getattr(action, "_original", action)
        self._sync()

    def nome_comando(self, a=None):
        a = a or self._current
        n = a.whatsThis() if a is not None else ""
        return n or (getattr(self, "_cmd", "") if len(self._actions) == 1 else "")

    def _on_click(self):
        a = self._current
        if _pedir_selecao(self.nome_comando(a)):
            pass
        elif a is not None and a.isEnabled():
            a.trigger()
        self._sync()

    def _sync(self):
        try:
            self._do_sync()
        except RuntimeError:  # botão ou ação já destruídos
            pass

    def _do_sync(self):
        a = self._current
        icon = a.icon()
        if icon.isNull():
            for x in self._actions:
                if not x.icon().isNull():
                    icon = x.icon()
                    break
        self.setIcon(_with_disabled(icon, _MED["iconL"] if self._size == L else _MED["iconS"]))
        txt = self._label if self._label else _clean(a.text())
        self.setText(_quebra(txt) if self._size == L else txt)
        self._ajustar_largura()
        action_title = _clean(a.text())
        title = self._label.replace("\n", " ") if (self._label and len(self._actions) == 1) else action_title
        desc = _tip_desc(a.toolTip() or a.statusTip(), (title, action_title))
        sc = a.shortcut().toString(QtGui.QKeySequence.NativeText)
        key = (title, desc, sc, icon.cacheKey())
        if getattr(self, "_tipkey", None) != key:
            self._tipkey = key
            self.setToolTip(_rich_tip(icon, title, desc, sc))
        enabled = any(x.isEnabled() for x in self._actions) if len(self._actions) > 1 else a.isEnabled()
        if not enabled and _selecao_depois(self.nome_comando(a)):
            enabled = True     # sem seleção, o clique abre o painel que pede a seleção
        self.setEnabled(enabled)
        # Em grupos (menu), o botão não espelha o estado "marcado" da subopção
        checkable = a.isCheckable() and len(self._actions) == 1
        self.setCheckable(checkable)
        if checkable:
            self.setChecked(a.isChecked())


def _selecao_depois(nome):
    """Comando que exige seleção antes mas que, no Prumo, também aceita a seleção depois."""
    try:
        import PrumoSelecao
        return nome in PrumoSelecao.SELECAO_PRIMEIRO and FreeCAD.ActiveDocument is not None
    except Exception:
        return False


def _pedir_selecao(nome):
    """Se o comando precisa de seleção que ainda não existe, abre o painel e devolve True."""
    try:
        import PrumoSelecao
        if PrumoSelecao.precisa_de_painel(nome):
            PrumoSelecao.pedir_para_comando(nome)
            return True
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: seleção para {}: {}\n".format(nome, exc))
    return False


def _proxy_selecao(a, parent):
    """No menu dos grupos, a ação desligada por falta de seleção vira uma cópia sempre ligada."""
    nome = a.whatsThis()
    if not _nome_selecao(nome):
        return None
    QAction = getattr(QtGui, "QAction", None) or QtWidgets.QAction
    px = QAction(a.icon(), a.text(), parent)
    px.setToolTip(a.toolTip())
    px._original = a

    def disparar(checked=False, original=a, n=nome):
        if not _pedir_selecao(n) and original.isEnabled():
            original.trigger()
    px.triggered.connect(disparar)
    return px


def _nome_selecao(nome):
    try:
        import PrumoSelecao
        return nome in PrumoSelecao.SELECAO_PRIMEIRO
    except Exception:
        return False


def _largura_estilo(b, estilo):
    atual = b.toolButtonStyle()
    QtWidgets.QToolButton.setToolButtonStyle(b, estilo)
    w = b.largura_do_texto()
    QtWidgets.QToolButton.setToolButtonStyle(b, atual)
    return w


class RibbonPanel(QtWidgets.QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoPanel")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(4, 3, 4, 0)
        outer.setSpacing(0)
        self.row = QtWidgets.QHBoxLayout()
        self.row.setSpacing(2)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        outer.addLayout(self.row, 1)
        cap = QtWidgets.QLabel(title)
        self._cap = cap
        cap.setObjectName("PrumoPanelTitle")
        cap.setAlignment(QtCore.Qt.AlignCenter)
        cap.setFixedHeight(20)
        outer.addWidget(cap)
        self._col = None
        self.count = 0

    def pequenos(self):
        return [b for b in self.findChildren(QtWidgets.QToolButton) if b.property("sw_size") == S]

    def larguras(self):
        """(natural, compacta): largura com os nomes dos botões pequenos e só com os ícones."""
        nat = comp = 0
        n = 0
        for i in range(self.row.count()):
            w = self.row.itemAt(i).widget()
            if w is None:
                continue
            n += 1
            if isinstance(w, RibbonButton):
                lw = w.largura_do_texto()
                nat += lw
                comp += lw
                continue
            bs = [b for b in w.findChildren(RibbonButton)]
            if not bs:
                continue
            nat += max(_largura_estilo(b, QtCore.Qt.ToolButtonTextBesideIcon) for b in bs)
            comp += max(_largura_estilo(b, QtCore.Qt.ToolButtonIconOnly) for b in bs)
        extra = self.row.spacing() * max(n - 1, 0) + 8
        cap = self._cap.fontMetrics().boundingRect(self._cap.text()).width() + 16
        return max(nat + extra, cap), max(comp + extra, cap)

    def preparar(self):
        self._natural, self._compacta = self.larguras()
        self.setMinimumWidth(self._compacta)

    def compacto(self):
        ps = self.pequenos()
        return bool(ps) and all(b.toolButtonStyle() == QtCore.Qt.ToolButtonIconOnly for b in ps)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        nat = getattr(self, "_natural", None)
        if nat is None:
            return
        # folga de alguns pixels: o divisor arredonda as larguras
        estilo = QtCore.Qt.ToolButtonIconOnly if ev.size().width() < nat - 10 else QtCore.Qt.ToolButtonTextBesideIcon
        for b in self.pequenos():
            if b.toolButtonStyle() != estilo:
                b.setToolButtonStyle(estilo)

    def add(self, btn, size):
        self.count += 1
        if size == L:
            self._col = None
            self.row.addWidget(btn)
            return
        if self._col is None or self._col.count() >= 3:
            w = QtWidgets.QWidget()
            w.setObjectName("PrumoCol")
            w.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self._col = QtWidgets.QVBoxLayout(w)
            self._col.setContentsMargins(0, 0, 0, 0)
            self._col.setSpacing(1)
            self._col.setAlignment(QtCore.Qt.AlignTop)
            self.row.addWidget(w)
        self._col.addWidget(btn)


class AlcaAltura(QtWidgets.QWidget):
    """Borda de baixo da faixa: arrastar muda a altura (botões e ícones acompanham); duplo clique
    volta ao padrão."""

    def __init__(self, ribbon):
        super().__init__(ribbon)
        self.ribbon = ribbon
        self.setObjectName("PrumoGrip")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFixedHeight(6)
        self.setCursor(QtCore.Qt.SizeVerCursor)
        self.setToolTip("Arraste para aumentar ou diminuir a faixa · duplo clique: altura padrão")
        self._y0 = None

    def mousePressEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton:
            self._y0 = ev.globalPosition().y() if hasattr(ev, "globalPosition") else ev.globalY()
            self._h0 = self.ribbon.content.height()

    def mouseMoveEvent(self, ev):
        if self._y0 is None:
            return
        y = ev.globalPosition().y() if hasattr(ev, "globalPosition") else ev.globalY()
        h = max(ALTURA_MIN, min(ALTURA_MAX, int(self._h0 + y - self._y0)))
        self.ribbon.content.setFixedHeight(h)

    def mouseReleaseEvent(self, ev):
        if self._y0 is None:
            return
        self._y0 = None
        self.ribbon.definir_altura(self.ribbon.content.height())

    def mouseDoubleClickEvent(self, ev):
        self.ribbon.definir_altura(ALTURA_PADRAO)


class PrumoRibbon(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PrumoRibbon")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(_t(RIBBON_QSS))
        self._tabs = list(TABS)
        self._dynamic = None  # aba gerada para bancadas sem aba própria
        self._edit_prev = None
        self._building = False

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Linha das abas
        row = QtWidgets.QWidget()
        row.setObjectName("PrumoTabRow")
        row.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        rl = QtWidgets.QHBoxLayout(row)
        rl.setContentsMargins(6, 0, 6, 0)
        rl.setSpacing(4)
        brand = QtWidgets.QLabel()
        brand.setObjectName("PrumoBrand")
        _ic = os.path.join(_HERE, "Resources", "icons", "prumo.svg")
        if os.path.isfile(_ic):
            _pm = QtGui.QIcon(_ic).pixmap(40, 40)
            _pm.setDevicePixelRatio(2.0)
            brand.setText("<table cellspacing='0' cellpadding='0'><tr><td valign='middle'><img src='{}' width='20' height='20'></td>"
                          "<td valign='middle' style='padding-left:6px'>Prumo 3D</td></tr></table>".format(_ic.replace("\\", "/")))
        else:
            brand.setText("Prumo 3D")
        brand.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Preferred)
        rl.addWidget(brand)
        rl.addWidget(self._build_wb_button())
        sep = QtWidgets.QFrame()
        sep.setObjectName("PrumoWbSep")
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setFixedHeight(20)
        rl.addSpacing(4)
        rl.addWidget(sep)
        rl.addSpacing(2)
        self.tabbar = QtWidgets.QTabBar()
        self.tabbar.setDrawBase(False)
        self.tabbar.setExpanding(False)
        self.tabbar.setUsesScrollButtons(False)
        self.tabbar.setElideMode(QtCore.Qt.ElideNone)
        self.tabbar.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.tabbar.setFocusPolicy(QtCore.Qt.NoFocus)
        for t in self._tabs:
            self.tabbar.addTab(t["label"])
        self.tabbar.currentChanged.connect(self._on_tab_changed)
        self.tabbar.tabBarDoubleClicked.connect(self._toggle_collapse)
        rl.addWidget(self.tabbar)
        rl.addStretch(1)
        rl.addWidget(self._build_quick())
        lay.addWidget(row)

        # Área de conteúdo
        self.content = QtWidgets.QScrollArea()
        self.content.setObjectName("PrumoContent")
        self.content.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.content.setWidgetResizable(True)
        self.content.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.content.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.content.viewport().setAutoFillBackground(True)
        pal = self.content.viewport().palette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(_t("background: #FFFFFF").split(": ")[1]))
        self.content.viewport().setPalette(pal)
        global _MED
        _MED = medidas(altura_salva())
        self.content.setFixedHeight(_MED["altura"])
        lay.addWidget(self.content)
        self.grip = AlcaAltura(self)
        lay.addWidget(self.grip)
        self.content.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.content.customContextMenuRequested.connect(self._menu_faixa)

    def _menu_faixa(self, pos):
        m = QtWidgets.QMenu(self)
        a1 = m.addAction("Restaurar a largura dos grupos desta aba")
        a2 = m.addAction("Altura padrão da faixa")
        esc = m.exec(self.content.mapToGlobal(pos)) if hasattr(m, "exec") else m.exec_(self.content.mapToGlobal(pos))
        if esc is a1:
            self.restaurar_larguras()
        elif esc is a2:
            self.definir_altura(ALTURA_PADRAO)

    # ---- seletor de bancadas (logo após a marca)
    def _build_wb_button(self):
        b = QtWidgets.QToolButton()
        b.setObjectName("PrumoWbBtn")
        b.setText("Bancadas")
        b.setToolTip("Trocar de bancada de trabalho")
        b.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        b.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        b.setCursor(QtCore.Qt.PointingHandCursor)
        try:
            import PrumoEstilo
            b.setStyleSheet("QToolButton::menu-indicator { image: url(%s); }" % PrumoEstilo._url("chev_down.svg"))
        except Exception:
            pass
        menu = QtWidgets.QMenu(b)
        menu.aboutToShow.connect(lambda m=menu: self._fill_wb_menu(m))
        b.setMenu(menu)
        self._wb_btn = b
        return b

    def _rotulo_bancada(self, name):
        b = getattr(self, "_wb_btn", None)
        if b is None:
            return
        try:
            wb = FreeCADGui.getWorkbench(name)
            nome = WB_NAMES.get(name) or getattr(wb, "MenuText", name)
        except Exception:
            nome = WB_NAMES.get(name, name)
        b.setText(nome if name not in ("NoneWorkbench", "StartWorkbench") else "Bancadas")
        b.setToolTip("Bancada ativa: {}. Clique para trocar.".format(nome))

    # ---- barra de acesso rápido (direita)
    def _build_quick(self):
        box = QtWidgets.QWidget()
        box.setObjectName("PrumoQuick")
        hl = QtWidgets.QHBoxLayout(box)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(1)
        for name, tip in (("Std_New", "Novo"), ("Std_Open", "Abrir"), ("Std_Save", "Salvar"),
                          ("Std_Undo", "Desfazer"), ("Std_Redo", "Refazer"), ("|", ""),
                          ("Std_Measure", "Medir")):
            if name == "|":
                sep = QtWidgets.QFrame(box)
                sep.setFrameShape(QtWidgets.QFrame.VLine)
                sep.setStyleSheet("color: #3A4450;" if _escuro() else "color: #D5DEE8;")
                sep.setFixedHeight(18)
                hl.addSpacing(4)
                hl.addWidget(sep)
                hl.addSpacing(4)
                continue
            acts = _cmd_actions(name)
            if not acts:
                # Comandos padrão também podem ainda não ter QAction quando a faixa
                # é montada; usamos uma ação própria que executa o comando.
                try:
                    cmd = FreeCADGui.Command.get(name)
                except Exception:
                    cmd = None
                if cmd is not None:
                    a = _own_action(name, cmd)
                    if a is not None:
                        a.setToolTip(tip)
                        acts = [a]
            if acts:
                b = RibbonButton(acts[:1], S, "", box)
                b._cmd = name
                b.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
                b.setIconSize(QtCore.QSize(18, 18))
                b.setFixedSize(28, 28)
                hl.addWidget(b)
        hl.addSpacing(8)
        col = QtWidgets.QToolButton(box)
        col.setArrowType(QtCore.Qt.UpArrow)
        col.setToolTip("Recolher / expandir a faixa (ou duplo clique na aba)")
        col.clicked.connect(self._toggle_collapse)
        self._collapse_btn = col
        hl.addWidget(col)
        return box

    def _fill_wb_menu(self, menu):
        menu.clear()
        wbs = FreeCADGui.listWorkbenches()
        items = []
        try:
            import PrumoGui
            desligadas = set(PrumoGui.bancadas_desligadas())
        except Exception:
            desligadas = set()
        for key, wb in wbs.items():
            if key in ("NoneWorkbench",) or key in desligadas:
                continue
            label = WB_NAMES.get(key) or getattr(wb, "MenuText", key)
            items.append((label, key, wb))
        for label, key, wb in sorted(items, key=lambda x: x[0].lower()):
            icon = QtGui.QIcon()
            try:
                ic = wb.Icon if hasattr(wb, "Icon") else ""
                if isinstance(ic, str) and ic and not ic.lstrip().startswith("/*"):
                    icon = QtGui.QIcon(ic)
            except Exception:
                pass
            # QAction explicita: a sobrecarga addAction(icone, texto) do PySide às vezes devolve outro tipo
            QAction = getattr(QtGui, "QAction", None) or QtWidgets.QAction
            act = QAction(icon, label, menu)
            act.triggered.connect(lambda checked=False, k=key: FreeCADGui.activateWorkbench(k))
            menu.addAction(act)

    def _toggle_collapse(self, *args):
        vis = not self.content.isVisible()
        self.content.setVisible(vis)
        self.grip.setVisible(vis)
        self._collapse_btn.setArrowType(QtCore.Qt.UpArrow if vis else QtCore.Qt.DownArrow)

    # ---- abas
    def tab_index(self, tab_id):
        for i, t in enumerate(self._tabs):
            if t["id"] == tab_id:
                return i
        return -1

    def _on_tab_changed(self, idx):
        if self._building or idx < 0:
            return
        tab = self._tabs[idx]
        wb = tab.get("wb")
        if wb and self._user_click:
            try:
                if FreeCADGui.activeWorkbench().name() != wb:
                    FreeCADGui.activateWorkbench(wb)  # dispara sync_workbench
                    return
            except Exception as exc:
                FreeCAD.Console.PrintWarning("Prumo: {}\n".format(exc))
        self.build(tab)

    _user_click = True

    def select_tab(self, tab_id, user=False):
        idx = self.tab_index(tab_id)
        if idx < 0:
            return
        self._user_click = user
        try:
            if self.tabbar.currentIndex() == idx:
                self.build(self._tabs[idx])
            else:
                self.tabbar.setCurrentIndex(idx)
        finally:
            self._user_click = True

    def sync_workbench(self, name=None):
        """Chamado quando a bancada ativa muda."""
        try:
            name = name or FreeCADGui.activeWorkbench().name()
        except Exception:
            return
        self._rotulo_bancada(name)
        for t in self._tabs:
            if t.get("wb") == name:
                self.select_tab(t["id"])
                return
        if name == "PrumoWorkbench":
            self.select_tab("prumo")
            return
        if name == "StartWorkbench" or name == "NoneWorkbench":
            self.select_tab("inicio")
            return
        self._make_dynamic(name)

    def _make_dynamic(self, name):
        try:
            wb = FreeCADGui.activeWorkbench()
            items = wb.getToolbarItems()
        except Exception:
            items = {}
        mw = FreeCADGui.getMainWindow()
        panels = []
        for tbname, cmds in items.items():
            if tbname in STD_TOOLBARS:
                continue
            tb = mw.findChild(QtWidgets.QToolBar, tbname)
            title = tb.windowTitle() if tb is not None else tbname
            entries = []
            for c in cmds:
                if c == "Separator":
                    continue
                entries.append((c, L if not entries else S, None))
            if entries:
                panels.append((title, entries))
        label = WB_NAMES.get(name) or getattr(wb, "MenuText", name)
        tab = {"id": "dyn", "label": label, "wb": name, "panels": panels}
        self._building = True
        if self._dynamic is None:
            self._tabs.append(tab)
            self.tabbar.addTab(label)
        else:
            self._tabs[-1] = tab
            self.tabbar.setTabText(len(self._tabs) - 1, label)
        self._dynamic = tab
        self._building = False
        self.select_tab("dyn")

    # ---- construção do conteúdo
    def build(self, tab):
        page = QtWidgets.QWidget()
        page.setObjectName("PrumoPage")
        page.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        hl = QtWidgets.QHBoxLayout(page)
        hl.setContentsMargins(6, 2, 6, 0)
        hl.setSpacing(0)
        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.setObjectName("PrumoSplit")
        split.setChildrenCollapsible(False)
        split.setHandleWidth(9)
        paineis = []
        for title, entries in tab["panels"]:
            panel = RibbonPanel(title)
            for cmd, size, label in entries:
                acts = _cmd_actions(cmd)
                if not acts:
                    continue
                btn = RibbonButton(acts, size, label, panel)
                btn._cmd = cmd      # o tutorial acha o botão pelo nome do comando
                panel.add(btn, size)
            if panel.count == 0:
                panel.deleteLater()
                continue
            split.addWidget(panel)
            paineis.append(panel)
        resto = QtWidgets.QWidget()
        resto.setObjectName("PrumoResto")
        split.addWidget(resto)
        # mede com o estilo (fonte e espaçamentos da folha de estilo) já aplicado
        page.setStyleSheet(page.styleSheet())
        for w in [page] + page.findChildren(QtWidgets.QWidget):
            w.ensurePolished()
        for i, pn in enumerate(paineis):
            pn.preparar()
            split.setStretchFactor(i, 0)
        split.setStretchFactor(len(paineis), 1)
        for i in range(1, split.count()):
            split.handle(i).setToolTip("Arraste para alargar ou estreitar o grupo (duplo clique na aba "
                                       "recolhe a faixa)")
        desejado = self._larguras_salvas(tab, paineis)
        self._fixar_minimo(page, split, desejado[:-1])
        split.setSizes(desejado)
        split.splitterMoved.connect(lambda *_a, t=tab, sp=split, pg=page: (self._guardar_larguras(t, sp),
                                                                            self._fixar_minimo(pg, sp)))
        hl.addWidget(split, 1)
        self.split = split
        self.paineis = paineis
        old = self.content.takeWidget()
        self.content.setWidget(page)
        if old is not None:
            old.deleteLater()

    def _fixar_minimo(self, page, split, tam=None):
        """Janela estreita: a faixa rola em vez de espremer os grupos (que só ficam compactos
        quando o próprio usuário arrasta o divisor)."""
        if tam is None:
            tam = split.sizes()[:-1]
        alvo = sum(tam) + split.handleWidth() * len(tam) + 6 * len(tam) + 40
        page.setMinimumWidth(alvo)

    def _chave_larguras(self, tab):
        return "RibbonPaineis_" + str(tab.get("id", "x"))

    def _larguras_salvas(self, tab, paineis):
        nat = [pn._natural for pn in paineis]
        txt = _params().GetString(self._chave_larguras(tab), "")
        try:
            salvas = [int(x) for x in txt.split(",") if x.strip()]
        except ValueError:
            salvas = []
        if len(salvas) == len(paineis):
            nat = [max(pn._compacta, w) for pn, w in zip(paineis, salvas)]
        return nat + [2000]

    def _guardar_larguras(self, tab, split):
        tam = split.sizes()[:-1]
        _params().SetString(self._chave_larguras(tab), ",".join(str(int(x)) for x in tam))

    def restaurar_larguras(self):
        """Volta os grupos da aba atual para a largura natural."""
        tab = self._tabs[self.tabbar.currentIndex()]
        _params().RemString(self._chave_larguras(tab))
        self.build(tab)

    # ---- altura da faixa
    def definir_altura(self, altura, guardar=True):
        global _MED
        _MED = medidas(altura)
        self.content.setFixedHeight(_MED["altura"])
        if guardar:
            _params().SetInt("RibbonHeight", _MED["altura"])
        idx = self.tabbar.currentIndex()
        if 0 <= idx < len(self._tabs):
            self.build(self._tabs[idx])
        return _MED["altura"]

    # ---- edição de esboço: mostra a aba Esboço sem trocar de bancada
    def check_edit(self):
        try:
            gdoc = FreeCADGui.ActiveDocument
            vp = gdoc.getInEdit() if gdoc else None
            editing = bool(vp) and vp.Object.TypeId.startswith("Sketcher::")
        except Exception:
            editing = False
        cur = self._tabs[self.tabbar.currentIndex()]["id"] if self.tabbar.currentIndex() >= 0 else None
        if editing and cur != "esboco" and self._edit_prev is None:
            self._edit_prev = cur
            self.select_tab("esboco")
        elif not editing and self._edit_prev is not None:
            prev, self._edit_prev = self._edit_prev, None
            if cur == "esboco":
                self.select_tab(prev)


# --------------------------------------------------------------------------
_state = {"bar": None, "ribbon": None, "timer": None}


def _hide_native_toolbars():
    mw = FreeCADGui.getMainWindow()
    bar = _state["bar"]
    for tb in mw.findChildren(QtWidgets.QToolBar):
        if tb is bar or tb.parent() is not mw:
            continue
        if tb.isVisible():
            tb.hide()


def _force_light_scheme():
    """Fixa o esquema de cores do Qt no tema Prumo (claro ou escuro), independente do Windows."""
    try:
        hints = QtGui.QGuiApplication.styleHints()
        alvo = QtCore.Qt.ColorScheme.Dark if _escuro() else QtCore.Qt.ColorScheme.Light
        if hasattr(hints, "setColorScheme") and hints.colorScheme() != alvo:
            hints.setColorScheme(alvo)
    except Exception:
        pass
    if _escuro() and not _state.get("paleta"):
        _state["paleta"] = True
        try:
            app = QtWidgets.QApplication.instance()
            pal = QtGui.QPalette(app.palette())
            for role, c in ((QtGui.QPalette.Window, "#161A20"), (QtGui.QPalette.Base, "#1F252D"),
                            (QtGui.QPalette.AlternateBase, "#1B2129"), (QtGui.QPalette.Button, "#1F252D"),
                            (QtGui.QPalette.WindowText, "#E6ECF2"), (QtGui.QPalette.Text, "#E6ECF2"),
                            (QtGui.QPalette.ButtonText, "#E6ECF2"), (QtGui.QPalette.ToolTipBase, "#1F252D"),
                            (QtGui.QPalette.ToolTipText, "#E6ECF2"), (QtGui.QPalette.Highlight, "#2F6FB5"),
                            (QtGui.QPalette.HighlightedText, "#F1F4F8"), (QtGui.QPalette.Link, "#8CBCEB"),
                            (QtGui.QPalette.PlaceholderText, "#6B7785")):
                pal.setColor(role, QtGui.QColor(c))
            pal.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, QtGui.QColor("#7D8996"))
            pal.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, QtGui.QColor("#7D8996"))
            pal.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, QtGui.QColor("#7D8996"))
            app.setPalette(pal)
        except Exception:
            pass


def _apply_global_qss():
    _force_light_scheme()
    app = QtWidgets.QApplication.instance()
    css = app.styleSheet() or ""
    if "/*PRUMO-BEGIN*/" in css:
        return
    extra = ""
    try:
        import PrumoEstilo
        if PrumoEstilo.enabled():
            extra = PrumoEstilo.qss()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: estilo das janelas não aplicado: {}\n".format(exc))
    app.setStyleSheet(css + "\n" + _t(GLOBAL_QSS).replace("/*PRUMO-END*/", extra + "\n/*PRUMO-END*/"))


def _tick():
    if _state["ribbon"] is None:
        return
    _hide_native_toolbars()
    _apply_global_qss()
    _state["ribbon"].check_edit()


def _on_workbench(name):
    rb = _state["ribbon"]
    if rb is None:
        return
    QtCore.QTimer.singleShot(0, _hide_native_toolbars)
    QtCore.QTimer.singleShot(50, lambda: rb.sync_workbench(name))


def install():
    if _state["ribbon"] is not None:
        return _state["ribbon"]
    mw = FreeCADGui.getMainWindow()
    bar = QtWidgets.QToolBar("Faixa Prumo", mw)
    bar.setObjectName("PrumoRibbonBar")
    bar.setMovable(False)
    bar.setFloatable(False)
    bar.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
    bar.toggleViewAction().setVisible(False)
    bar.setStyleSheet(_t("QToolBar#PrumoRibbonBar { border: none; padding: 0; margin: 0; spacing: 0; background: #FFFFFF; }"))
    ribbon = PrumoRibbon(bar)
    ribbon.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    bar.addWidget(ribbon)
    mw.addToolBar(QtCore.Qt.TopToolBarArea, bar)
    _state.update(bar=bar, ribbon=ribbon)
    try:
        mw.workbenchActivated.connect(_on_workbench)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: sinal workbenchActivated indisponível: {}\n".format(exc))
    timer = QtCore.QTimer(mw)
    timer.setInterval(400)
    timer.timeout.connect(_tick)
    timer.start()
    _state["timer"] = timer
    _hide_native_toolbars()
    _apply_global_qss()
    ribbon.sync_workbench()
    return ribbon


def uninstall(restore_toolbars=True):
    mw = FreeCADGui.getMainWindow()
    if _state["timer"] is not None:
        _state["timer"].stop()
    try:
        mw.workbenchActivated.disconnect(_on_workbench)
    except Exception:
        pass
    if _state["bar"] is not None:
        mw.removeToolBar(_state["bar"])
        _state["bar"].deleteLater()
    _state.update(bar=None, ribbon=None, timer=None)
    app = QtWidgets.QApplication.instance()
    css = app.styleSheet() or ""
    if "/*PRUMO-BEGIN*/" in css:
        a = css.index("/*PRUMO-BEGIN*/")
        b = css.index("/*PRUMO-END*/") + len("/*PRUMO-END*/")
        app.setStyleSheet(css[:a] + css[b:])
    if restore_toolbars:
        for tb in mw.findChildren(QtWidgets.QToolBar):
            if tb.parent() is mw and tb.toggleViewAction().isVisible():
                tb.show()


def reload():
    """Para desenvolvimento: recarrega o módulo e reinstala a faixa."""
    import importlib
    import PrumoRibbon as mod
    mod.uninstall(restore_toolbars=False)
    mod = importlib.reload(mod)
    return mod.install()
