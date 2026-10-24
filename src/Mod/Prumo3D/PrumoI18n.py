# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - tradução pt-BR com prioridade sobre a tradução oficial.
"""Instala as traduções Prumo por cima das oficiais.

1. ``translations/prumo_ptbr.qm``: compilada da tradução pt-BR mais recente
   do repositório do FreeCAD (mais completa que a da versão instalada).
2. ``EXTRA``: textos que nem o repositório traduz, por texto de origem.

O Qt consulta primeiro o tradutor instalado por último. Os módulos do FreeCAD
instalam os tradutores deles ao carregar, então reaplicamos a prioridade na
primeira ativação de cada bancada.
"""

import os

import FreeCAD

try:
    from PySide import QtCore
except ImportError:  # pragma: no cover
    from PySide2 import QtCore

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"

# Textos de origem (inglês) -> português. Aceleradores (&) são opcionais.
EXTRA = {
    # Textos encontrados na auditoria visual (sem tradução na versão 1.1.4)
    "Search preferences…": "Buscar nas preferências…", "Search preferences...": "Buscar nas preferências...",
    "&Content": "&Conteúdo", "&Alias": "&Apelido", "Pad": "Extrusão",
    # Painéis de extrusão/cavidade: mesmos termos dos valores de propriedade
    "Through all": "Através de tudo", "To last": "Até a última face", "To first": "Até a primeira face",
    # Botões padrão dos diálogos (vêm do Qt, sem tradução no FreeCAD)
    "Close": "Fechar", "&Close": "&Fechar", "Cancel": "Cancelar", "&Cancel": "&Cancelar",
    "Apply": "Aplicar", "&Apply": "&Aplicar", "Help": "Ajuda", "&Help": "&Ajuda",
    "Reset": "Redefinir", "Restore Defaults": "Restaurar padrões", "&Yes": "&Sim", "&No": "&Não",
    "Yes to &All": "Sim para &todos", "N&o to All": "Nã&o para todos", "Save": "Salvar", "&Save": "&Salvar",
    "Save All": "Salvar todos", "Discard": "Descartar", "Don't Save": "Não salvar", "Abort": "Abortar",
    "Retry": "Tentar de novo", "Ignore": "Ignorar", "&OK": "&OK", "Open": "Abrir", "&Open": "&Abrir",
    # Vistas
    "&1 Front": "&1 Frontal", "&2 Top": "&2 Superior", "&3 Right": "&3 Direita",
    "&4 Rear": "&4 Traseira", "&5 Bottom": "&5 Inferior", "&6 Left": "&6 Esquerda",
    "Stereo Interleaved &Columns": "Estéreo intercalado por &colunas",
    "Stereo Interleaved &Rows": "Estéreo intercalado por &linhas",
    "Stereo &Off": "Estéreo &desligado", "Stereo &Quad Buffer": "Estéreo &quad buffer",
    "Stereo Re&d/Cyan": "Estéreo &vermelho/ciano",
    # Árvore
    "&1 Sync View": "&1 Sincronizar vista", "&2 Sync Selection": "&2 Sincronizar seleção",
    "&3 Sync Placement": "&3 Sincronizar posicionamento", "&4 Preselection": "&4 Pré-seleção",
    "&5 Record Selection": "&5 Registrar seleção",
    # Arquivo / ferramentas / macro
    "Save Cop&y": "Salvar &cópia", "Clear Recent Files": "Limpar arquivos recentes",
    "&Addon Manager": "Gerenciador de &complementos", "Cu&stomize…": "&Personalizar…",
    "Cu&stomize...": "&Personalizar…", "Ma&cros": "Ma&cros…", "&Material": "&Material",
    "Export Dependency &Graph": "Exportar &grafo de dependências",
    "&Debug Macro": "&Depurar macro", "Step &Into": "Entrar na &função", "Step &Over": "&Pular função",
    "&Stop Debugging": "&Parar depuração", "Toggle &Breakpoint": "Alternar ponto de &interrupção",
    "&Part Design": "&Peça", "Python Console": "Console Python", "Python console": "Console Python",
    "Report View": "Relatório", "Report view": "Relatório",
    # Part / PartDesign
    "Sub-Shape Binder": "Vínculo de subforma", "Cone": "Cone", "Loft": "Loft",
    # Planilha
    "Align &Bottom": "Alinhar na &base", "Align Horizontal &Center": "Centralizar &horizontalmente",
    "Align &Left": "Alinhar à &esquerda", "Align &Right": "Alinhar à &direita", "Align &Top": "Alinhar no &topo",
    "Align &Vertical Center": "Centralizar &verticalmente", "&New Spreadsheet": "&Nova planilha",
    "&Export Spreadsheet": "&Exportar planilha", "&Import Spreadsheet": "&Importar planilha",
    "&Merge Cells": "&Mesclar células", "Set Alias": "Definir apelido", "Sp&lit Cell": "&Dividir célula",
    "&Bold Text": "&Negrito", "&Italic Text": "&Itálico", "&Underline Text": "&Sublinhado",
    # Desenho técnico
    "Centerline Between 2 Lines": "Linha de centro entre 2 linhas",
    "Centerline Between 2 Points": "Linha de centro entre 2 pontos",
    "Centerline Between 2 Faces": "Linha de centro entre 2 faces",
    "Cosmetic Line Through 2 Points": "Linha cosmética por 2 pontos",
    "Angle Dimension From 3 Points": "Cota angular por 3 pontos",
    "Active View": "Vista da tela", "Align Vertices/Edge Horizontally": "Alinhar vértices/aresta na horizontal",
    "Align Vertices/Edge Vertically": "Alinhar vértices/aresta na vertical",
    "Angle Dimension": "Cota angular", "Text Annotation": "Anotação de texto", "BIM View": "Vista BIM",
    "Axonometric Length Dimension": "Cota axonométrica", "Balloon Annotation": "Balão",
    "Offset Vertex": "Vértice deslocado", "Complex Section View": "Corte complexo",
    "Cosmetic 1 Point Circle": "Círculo cosmético por 1 ponto",
    "Cosmetic 2 Point Circle": "Círculo cosmético por 2 pontos",
    "Cosmetic 3 Point Circle": "Círculo cosmético por 3 pontos", "Cosmetic Arc": "Arco cosmético",
    "Edit Line Appearance": "Editar aparência da linha", "Diameter Dimension": "Cota de diâmetro",
    "Repair Dimension References": "Reparar referências das cotas", "Draft View": "Vista 2D (Draft)",
    "Arc Length Annotation": "Anotação de comprimento de arco", "Area Annotation": "Anotação de área",
    "Horizontal Chain Dimension": "Cota em cadeia horizontal",
    "Horizontal Chamfer Dimension": "Cota de chanfro horizontal",
    "Horizontal Coordinate Dimension": "Cota por coordenadas horizontal",
    "Arc Length Dimension": "Cota de comprimento de arco",
    "Oblique Chain Dimension": "Cota em cadeia oblíqua",
    "Oblique Coordinate Dimension": "Cota por coordenadas oblíqua",
    "Vertical Chain Dimension": "Cota em cadeia vertical",
    "Vertical Chamfer Dimension": "Cota de chanfro vertical",
    "Vertical Coordinate Dimension": "Cota por coordenadas vertical",
    "Bolt Circle Centerlines": "Linhas de centro de furação circular",
    "Insert 'n×' Prefix": "Inserir prefixo 'n×'", "Cosmetic Parallel Line": "Linha cosmética paralela",
    "Cosmetic Perpendicular Line": "Linha cosmética perpendicular", "Toggle View Lock": "Travar/destravar vista",
    "Align Chain Dimensions Horizontally": "Alinhar cotas em cadeia na horizontal",
    "Align Oblique Chain Dimensions": "Alinhar cotas em cadeia oblíquas",
    "Align Chain Dimensions Vertically": "Alinhar cotas em cadeia na vertical",
    "Position Section View": "Posicionar vista em corte",
    "Cosmetic Thread Bolt Bottom View": "Rosca cosmética de parafuso (vista inferior)",
    "Cosmetic Thread Bolt Side View": "Rosca cosmética de parafuso (vista lateral)",
    "Cosmetic Thread Hole Bottom View": "Rosca cosmética de furo (vista inferior)",
    "Cosmetic Thread Hole Side View": "Rosca cosmética de furo (vista lateral)",
    "Cosmetic Intersection Vertices": "Vértices cosméticos de interseção",
    "Update Template Fields": "Preencher campos do carimbo", "Geometric Hatch": "Hachura geométrica",
    "Image Hatch": "Hachura por imagem", "Hole/Shaft Fit": "Ajuste furo/eixo",
    "Horizontal Length Dimension": "Cota horizontal", "Horizontal Extent Dimension": "Cota de extensão horizontal",
    "Bitmap Image": "Imagem", "Length Dimension": "Cota linear", "Midpoint Vertices": "Vértices de ponto médio",
    "New Page": "Nova folha", "New Page From Template": "Nova folha a partir de modelo",
    "Project Shape": "Projetar forma", "Quadrant Vertices": "Vértices de quadrante",
    "Radius Dimension": "Cota de raio", "Rich Text Annotation": "Texto formatado", "Share View": "Compartilhar vista",
    "Toggle Edge Visibility": "Mostrar/ocultar arestas", "Spreadsheet View": "Vista de planilha",
    "Surface Finish Symbol": "Símbolo de rugosidade", "Insert SVG": "Inserir SVG",
    "Vertical Length Dimension": "Cota vertical", "Vertical Extent Dimension": "Cota de extensão vertical",
    "New View": "Nova vista", "Weld Symbol": "Símbolo de solda",
    # Títulos dos painéis de tarefa
    "Pad parameters": "Parâmetros da extrusão", "Pad Parameters": "Parâmetros da extrusão",
    "Pocket parameters": "Parâmetros da cavidade", "Pocket Parameters": "Parâmetros da cavidade",
    "Revolution parameters": "Parâmetros da revolução", "Revolution Parameters": "Parâmetros da revolução",
    "Groove parameters": "Parâmetros da ranhura", "Groove Parameters": "Parâmetros da ranhura",
    "Hole parameters": "Parâmetros do furo", "Hole Parameters": "Parâmetros do furo",
    "Fillet parameters": "Parâmetros do arredondamento", "Fillet Parameters": "Parâmetros do arredondamento",
    "Chamfer parameters": "Parâmetros do chanfro", "Chamfer Parameters": "Parâmetros do chanfro",
    "Thickness parameters": "Parâmetros da casca", "Draft parameters": "Parâmetros do ângulo de saída",
    "Helix Parameters": "Parâmetros da hélice", "Loft Parameters": "Parâmetros do loft",
    "Pipe Parameters": "Parâmetros da varredura", "Section Orientation": "Orientação da seção",
    "Section Transformation": "Transformação da seção",
    "Projection Group": "Grupo de projeção",
    "Sketch normal": "Normal do esboço", "Taper angle": "Ângulo de inclinação",
    # Barras de ferramentas (títulos)
    "Individual Views": "Vistas individuais", "Part Design Helper Features": "Auxiliares de peça",
    "Part Design Modeling Features": "Modelagem de peça", "Part Design Dress-Up Features": "Acabamento de peça",
    "Part Design Transformation Features": "Padrões de peça", "Sketcher Tools": "Ferramentas de esboço",
}

# Varredura da 0.1 beta: textos da faixa e dos menus que ainda apareciam em inglês
# (auditoria automática por aba, comparando o texto mostrado com o texto de origem).
EXTRA.update({
    # Arquivo / editar / vista / janelas / ajuda
    "&New Document": "&Novo documento", "Creates a new empty document": "Cria um documento novo, vazio",
    "&Open…": "&Abrir…", "Opens a document or imports files": "Abre um documento ou importa arquivos",
    "Saves the active document": "Salva o documento ativo", "&Undo": "&Desfazer", "&Redo": "&Refazer",
    "Undoes the previous action": "Desfaz a última ação", "Activates this window": "Ativa esta janela",
    "&2 Points": "&2 Pontos", "&4 Hidden line": "&4 Linhas ocultas", "&7 Flat lines": "&7 Faces planas com arestas",
    "<p>Restores the previous tree view selection. Only works if tree RecordSelection mode is switched on.</p>":
        "<p>Volta à seleção anterior na árvore. Só funciona com o modo Registrar seleção da árvore ligado.</p>",
    "<p>Restores the next tree view selection. Only works if tree RecordSelection mode is switched on.</p>":
        "<p>Avança para a próxima seleção na árvore. Só funciona com o modo Registrar seleção da árvore ligado.</p>",
    "Switches stereo viewing to red/cyan": "Visão estéreo vermelho/ciano",
    "Switches stereo viewing to quad buffer": "Visão estéreo quad buffer",
    "Switches stereo viewing to interleaved rows": "Visão estéreo intercalada por linhas",
    "Switches stereo viewing to interleaved columns": "Visão estéreo intercalada por colunas",
    "<p>Toggles the transparency of the selected objects. Transparency can be fine-tuned in the appearance task dialog</p>":
        "<p>Liga/desliga a transparência dos objetos selecionados. O grau de transparência se ajusta em Aparência.</p>",
    "Toggled overlay mode for all docked panels": "Liga/desliga o modo sobreposto de todos os painéis",
    "Manages external workbenches, macros, and preference packs":
        "Gerencia bancadas externas, macros e pacotes de preferências",
    "Starts the debugging of macros": "Inicia a depuração de macros",
    "Stops the debugging of macros": "Para a depuração de macros",
    "Steps to the next line in this file": "Avança para a próxima linha deste arquivo",
    "Steps to the next line executed": "Avança para a próxima linha executada",
    "Adds or removes a breakpoint at this position": "Coloca ou tira um ponto de interrupção nesta posição",
    "Handbook about FreeCAD development": "Manual de desenvolvimento do FreeCAD",
    "Support the FreeCAD development": "Apoie o desenvolvimento do FreeCAD",
    # Peça
    "Lofts the selected sketch or profile along a path and adds it to the body":
        "Cria um sólido de transição (loft) entre os esboços selecionados e soma ao corpo",
    "Lofts the selected sketch or profile along a path and removes it from the body":
        "Cria uma transição (loft) entre os esboços selecionados e retira do corpo",
    # Esboço
    "Exits the active sketch": "Sai do esboço ativo",
    "Creates a continuous polyline. Press the 'M' key to switch segment modes":
        "Cria uma linha contínua. Tecle 'M' para alternar entre reta e arco",
    "Constrains the vertical distance between the selected elements":
        "Restringe a distância vertical entre os elementos selecionados",
    "Creates a fillet between 2 selected lines or at coincident points":
        "Arredonda o canto entre 2 linhas selecionadas ou num ponto comum",
    "Creates a chamfer between 2 selected lines or at coincident points":
        "Chanfra o canto entre 2 linhas selecionadas ou num ponto comum",
    "Translates the selected geometries and enables the creation of 'i' * 'j' copies":
        "Move a geometria selecionada e permite criar 'i' × 'j' cópias (padrão retangular)",
    "Rotates the selected geometry by creating 'n' copies, enabling circular pattern creation":
        "Gira a geometria selecionada criando 'n' cópias (padrão circular)",
    # Sólidos
    "Applies a boolean operations with the selected shapes": "Aplica uma operação booleana nas formas selecionadas",
    "Explode Compound": "Separar composto",
    "Splits up a compound of shapes into separate objects, creating a compound filter for each shape":
        "Separa um composto em objetos independentes (um filtro de composto para cada forma)",
    "Compound Filter": "Filtro de composto",
    "Filters out objects from the selected compound by characteristics like volume,\narea, or length, or by "
    "choosing specific items.\nIf a second object is selected, it will be used as reference, for example,\n"
    "for collision or distance filtering.":
        "Filtra as formas de um composto por volume, área ou comprimento, ou escolhendo itens.\n"
        "Se um segundo objeto for selecionado, ele serve de referência (colisão ou distância).",
    "Connect Shapes": "Conectar formas", "Fuses shapes, taking care to preserve voids":
        "Une as formas preservando os vazios internos",
    "Embed Shapes": "Embutir formas", "Fuses one shape into another, taking care to preserve voids":
        "Embute uma forma na outra preservando os vazios",
    "Cutout Shape": "Recortar encaixe", "Creates a cutout in the selected shape to fit another shape":
        "Recorta a forma selecionada para encaixar a outra",
    "Boolean Fragments": "Fragmentos booleanos",
    "Creates a boolean union which is sliced at the intersections of the selected shapes":
        "Une as formas e divide nas interseções entre elas",
    "Slice to Compound": "Fatiar em composto",
    "Slices the selected object by using other objects as cutting tools and storing the results in one compound":
        "Fatia o objeto usando os outros como ferramentas de corte e guarda as partes num composto",
    "Slice Apart": "Fatiar separado",
    "Slices the selected object by other objects, and splits it apart, creating a compound filter for each slide":
        "Fatia o objeto pelos outros e separa as partes (um filtro de composto para cada fatia)",
    "Boolean XOR": "XOR booleano",
    "Performs an 'exclusive OR' boolean operation with two or more selected objects,\nor with the shapes inside "
    "a compound.\nOverlapping volumes of the shapes will be removed.":
        "Operação 'OU exclusivo' entre dois ou mais objetos, ou entre as formas de um composto.\n"
        "Os volumes sobrepostos são removidos.",
    # Montagem
    "Insert Component": "Inserir componente",
    "<p>Toggles the grounding of a part.</p><p>Grounding a part permanently locks its position in the assembly, "
    "preventing any movement or rotation. You need at least one grounded part before starting to assemble.":
        "<p>Fixa/solta uma peça.</p><p>A peça fixa fica travada na montagem, sem mover nem girar. "
        "É preciso ter pelo menos uma peça fixa antes de montar.",
    "<p>1 - If an assembly is active : Creates a joint permanently locking two parts together, preventing any "
    "movement or rotation</p><p>2 - If a part is active: Positions sub-parts by matching selected coordinate "
    "systems. The second part selected will move.</p>":
        "<p>1 - Com uma montagem ativa: cria uma junta que trava duas peças juntas, sem mover nem girar.</p>"
        "<p>2 - Com uma parte ativa: posiciona as subpeças casando os sistemas de coordenadas selecionados. "
        "A segunda peça selecionada é a que se move.</p>",
    "<p>Creates a rack and pinion joint that links a part with a sliding joint to a part with a revolute "
    "joint</p><p>Selects the same coordinate systems as the revolute and sliding joints. The pitch radius "
    "defines the movement ratio between the rack and the pinion.</p>":
        "<p>Cria uma junta pinhão-cremalheira entre uma peça com junta deslizante e outra com junta de "
        "rotação.</p><p>Selecione os mesmos sistemas de coordenadas das duas juntas. O raio primitivo define "
        "a relação de movimento entre cremalheira e pinhão.</p>",
    "<p>Creates a screw joint that links a part with a sliding joint to a part with a revolute joint</p>"
    "<p>Select the same coordinate systems as the revolute and sliding joints. The pitch radius defines the "
    "movement ratio between the rotating screw and the sliding part.</p>":
        "<p>Cria uma junta de fuso entre uma peça com junta deslizante e outra com junta de rotação.</p>"
        "<p>Selecione os mesmos sistemas de coordenadas das duas juntas. O passo define a relação de "
        "movimento entre o fuso e a peça que desliza.</p>",
    # Desenho técnico
    "Inserts an image of the open 3D view in the current page.\nIf multiple 3D views are open, a selection "
    "dialog will be shown.":
        "Insere na folha uma imagem da vista 3D aberta.\nCom várias vistas 3D abertas, pergunta qual usar.",
    "Inserts a length dimension of an edge or distance between two points":
        "Insere a cota do comprimento de uma aresta ou da distância entre dois pontos",
    "Inserts a horizontal length dimension of an edge or distance between two points":
        "Insere a cota horizontal de uma aresta ou entre dois pontos",
    "Inserts a vertical length dimension of an edge or distance between two points":
        "Insere a cota vertical de uma aresta ou entre dois pontos",
    "Inserts a radius dimension of a circular edge or arc": "Insere a cota de raio de um círculo ou arco",
    "Inserts an annotation showing the area of a selected face": "Insere uma anotação com a área da face selecionada",
    "Inserts a dimension showing the horizontal extent (overall length) of an object or feature.":
        "Insere a cota da extensão horizontal (comprimento total) de um objeto.",
    "Inserts a dimension showing the vertical extent (overall length) of an object or feature.":
        "Insere a cota da extensão vertical (altura total) de um objeto.",
    "Repairs broken or incorrect dimension references": "Repara referências de cotas quebradas ou erradas",
    "Inserts a rich text annotation in the current page": "Insere um texto formatado na folha",
    "Add a cosmetic line that passes through 2 selected points": "Adiciona uma linha cosmética por 2 pontos",
    "Applies a hatch pattern to the selected faces using an image file":
        "Aplica hachura às faces selecionadas a partir de uma imagem",
    "Applies a geometric hatch pattern to the selected faces": "Aplica hachura geométrica às faces selecionadas",
    "Inserts a symbol from an SVG file": "Insere um símbolo de um arquivo SVG",
    "Insert bitmap from a file into a page": "Insere uma imagem de um arquivo na folha",
    "Inserts a bitmap from a file into the current page": "Insere uma imagem de um arquivo na folha",
    "Shares a view on a second page": "Mostra a mesma vista em outra folha",
    "Aligns the selected vertices or edges vertically to the view rotation":
        "Alinha os vértices ou arestas selecionados na vertical da vista",
    "Aligns the selected section view with its source view orthogonally or the selected edge in the section "
    "view to the selected vertex in the base view":
        "Alinha o corte com a vista de origem, ou a aresta selecionada do corte com o vértice da vista base",
    "Inserts an annotation with the calculated arc length of the selected edges":
        "Insere uma anotação com o comprimento de arco das arestas selecionadas",
    "Creates an offset from one selected vertex": "Cria um vértice deslocado a partir do vértice selecionado",
    "Centerline 2 Lines": "Linha de centro entre 2 linhas", "Centerline 2 Points": "Linha de centro entre 2 pontos",
    "Insert '⌀' Prefix": "Inserir prefixo '⌀'", "Insert '□' Prefix": "Inserir prefixo '□'",
    "Remove Prefix": "Remover prefixo",
    "Inserts a '⌀' symbol at the beginning of the dimension": "Põe o símbolo '⌀' antes do valor da cota",
    "Inserts a '□' symbol at the beginning of the dimension": "Põe o símbolo '□' antes do valor da cota",
    "Inserts a repeated feature count at the beginning of the dimension":
        "Põe a quantidade de elementos repetidos ('n×') antes do valor da cota",
    "Removes the prefix symbols at the beginning of the dimension": "Tira os símbolos antes do valor da cota",
    "Locks or unlocks the position of the selected views": "Trava ou destrava a posição das vistas selecionadas",
    "Inserts a simple section view": "Insere um corte simples", "Inserts a complex section view": "Insere um corte composto",
    "Inserts a cosmetic vertex into a view": "Insere um vértice cosmético na vista",
    "Inserts cosmetic vertices at the midpoint of the selected edges":
        "Insere vértices cosméticos no ponto médio das arestas selecionadas",
    "Inserts cosmetic vertices at the quadrant points of the selected circles":
        "Insere vértices cosméticos nos quadrantes dos círculos selecionados",
    "Moves the view up one level": "Sobe a vista um nível", "Moves the view down one level": "Desce a vista um nível",
    "Moves the view to the top of the stack": "Leva a vista para o topo", "Moves the view to the bottom of the stack":
        "Leva a vista para o fundo",
    "Moves the selected view up 1 level in the view stack": "Sobe a vista selecionada um nível",
    "Moves the selected view down 1 level in the view stack": "Desce a vista selecionada um nível",
    "Moves the selected view to the top of the stack": "Leva a vista selecionada para o topo",
    "Moves the selected view to the bottom of the stack": "Leva a vista selecionada para o fundo",
    "Shortens a selected cosmetic line or centerline at both ends by the specified delta distance":
        "Encurta a linha cosmética ou de centro selecionada nas duas pontas",
    "Format/Organize Dimensions": "Formatar/organizar cotas", "TechDraw Extend Dimensions": "Cotas avançadas",
    "Views From Other Workbenches": "Vistas de outras bancadas",
    "Inserts a view of a spreadsheet in the current page": "Insere na folha a vista de uma planilha",
    "Configures the default attributes for cosmetic lines and centerlines, including cascade spacing and delta "
    "distance": "Define o padrão das linhas cosméticas e de centro, incluindo espaçamento em cascata e distância",
    # Chapa metálica
    "New Sketch": "Novo esboço", "Create a new sketch in the active body": "Cria um esboço novo no corpo ativo",
    # Simulação (FEM)
    "New Analysis": "Nova análise", "Creates a solid material": "Cria um material sólido",
    "Creates a fluid material": "Cria um material fluido",
    "Creates a non-linear mechanical material": "Cria um material mecânico não linear",
    "Creates a spring boundary condition on a face": "Cria uma condição de mola numa face",
    "Mesh From Shape by Gmsh": "Malha da forma (Gmsh)", "Mesh From Shape by Netgen": "Malha da forma (Netgen)",
    "Clears the mesh of a FEM mesh object": "Apaga a malha do objeto de malha",
    "Creates a standard FEM solver CalculiX with ccx tools": "Cria o resolvedor CalculiX padrão",
    "Creates a FEM solver CalculiX": "Cria o resolvedor CalculiX",
    "Show Result": "Mostrar resultado", "Shows and visualizes the selected result data":
        "Mostra o resultado selecionado na vista",
    "Purges all results from the active analysis": "Apaga todos os resultados da análise ativa",
    "Warps the geometry along a vector field by a certain factor":
        "Deforma a geometria pelo campo de deslocamentos, com fator de escala",
    "Defines a clip filter which clips a field with a scalar value": "Filtro que recorta pelo valor de um campo",
    "Line Clip Filter": "Filtro ao longo de linha",
    "Defines a clip filter which clips a field along a line": "Filtro que mostra o campo ao longo de uma linha",
    "Creates a beam cross section": "Cria a seção transversal de viga",
    "Creates a beam rotation": "Cria a rotação da seção de viga",
    "Creates a shell plate thickness": "Cria a espessura de casca/chapa",
    "Fluid Section for 1D Flow": "Seção de fluido (escoamento 1D)",
    "Creates a fluid section for 1D flow": "Cria uma seção de fluido para escoamento 1D",
    "Current Density Boundary Condition": "Condição de densidade de corrente",
    "Creates an electric charge density": "Cria uma densidade de carga elétrica",
    "Creates an initial flow velocity condition": "Cria uma condição de velocidade inicial do escoamento",
    "Plane Multi-Point Constraint": "Restrição multiponto plana", "Section Print Feature": "Esforços na seção",
    "Creates a local coordinate system on a face": "Cria um sistema de coordenadas local numa face",
    "Rigid Body Constraint": "Corpo rígido", "Contact Constraint": "Contato", "Tie Constraint": "Ligação (tie)",
    "Body Heat Source": "Fonte de calor no corpo",
    "Creates a constant vacuum permittivity to overwrite standard value":
        "Define a permissividade do vácuo (substitui o valor padrão)",
    "Creates a mesh boundary layer": "Cria camada limite na malha", "Creates a mesh group": "Cria um grupo de malha",
    "FEM Mesh to Mesh": "Malha FEM para malha",
    "Creates an equation for flow": "Cria a equação de escoamento", "Creates an equation for flux": "Cria a equação de fluxo",
    "Creates an equation for heat": "Cria a equação de calor",
    "Creates an equation for elasticity (stress)": "Cria a equação de elasticidade (tensões)",
    "Creates an equation for deformation (nonlinear elasticity)": "Cria a equação de deformação (elasticidade não linear)",
    "Creates an equation for electrostatic": "Cria a equação eletrostática",
    "Creates an equation for electric forces": "Cria a equação de forças elétricas",
    "Creates an equation for magnetodynamic forces": "Cria a equação magnetodinâmica",
    "Creates an equation for 2D magnetodynamic forces": "Cria a equação magnetodinâmica 2D",
    "Creates an equation for static current": "Cria a equação de corrente estática",
    "Static Current Equation": "Equação de corrente estática",
    "Apply Changes to Pipeline": "Aplicar mudanças ao pós-processamento",
    "Applies changes to parameters directly and not on recompute only":
        "Aplica as mudanças de parâmetros na hora, sem esperar o recálculo",
    "Post Pipeline From Result": "Pós-processamento a partir do resultado",
    "Branches the pipeline into a new path": "Abre um novo ramo no pós-processamento",
    "Function Cut Filter": "Filtro de corte por função", "Cuts the data along an implicit function":
        "Corta os dados por uma função implícita",
    "Defines a clip filter which uses functions to define the clipped region":
        "Filtro que recorta a região definida por funções",
    "Adds a post-processing filter that adds glyphs to the mesh vertices for vertex data visualization":
        "Filtro que desenha setas/símbolos nos nós para mostrar os dados",
    "Data at Point Clip Filter": "Filtro de dados no ponto",
    "Defines a clip filter which clips a field data at point": "Filtro que mostra o campo num ponto",
    "Creates a new field from current data": "Cria um campo novo a partir dos dados atuais",
    "Clipping Plane on Face": "Plano de corte na face", "Adds a clipping plane on a selected face":
        "Põe um plano de corte na face selecionada",
    "Remove All Clipping Planes": "Remover todos os planos de corte",
    "Create Histogram": "Criar histograma", "Create Lineplot": "Criar gráfico de linhas", "Create Table": "Criar tabela",
    "Create a Histogram post processing data visualization": "Cria um histograma dos resultados",
    "Create a Lineplot post processing data visualization": "Cria um gráfico de linhas dos resultados",
    "Create a Table post processing data visualization": "Cria uma tabela dos resultados",
    "Data Visualizations": "Visualização de dados",
    "&Geometrical Analysis Features": "&Recursos de análise geométrica",
    "Geometrical Analysis Features": "Recursos de análise geométrica",
    "&Mechanical Boundary Conditions and Loads": "Condições de contorno e cargas &mecânicas",
    "Mechanical Boundary Conditions and Loads": "Condições de contorno e cargas mecânicas",
    "&Thermal Boundary Conditions and Loads": "Condições de contorno e cargas &térmicas",
    "Thermal Boundary Conditions and Loads": "Condições de contorno e cargas térmicas",
    "&Fluid Boundary Conditions": "Condições de contorno de &fluido",
    "Fluid Boundary Conditions": "Condições de contorno de fluido",
    "&Electromagnetic Boundary Conditions": "Condições de contorno &eletromagnéticas",
    "Electromagnetic Boundary Conditions": "Condições de contorno eletromagnéticas",
    "&Overwrite Constants": "&Sobrescrever constantes", "Overwrite Constants": "Sobrescrever constantes",
    "Switches stereo viewing off": "Desliga a visão estéreo",
    "Flat Lines": "Faces planas com arestas", "Points": "Pontos",
    "Solid Material": "Material sólido", "Fluid Material": "Material fluido",
    "Non-Linear Mechanical Material": "Material mecânico não linear",
    "Reinforced Material (Concrete)": "Material armado (concreto)",
    "Fixed Boundary Condition": "Engaste (fixação)", "Displacement Boundary Condition": "Deslocamento prescrito",
    "Spring Boundary Condition": "Apoio elástico (mola)", "Force Load": "Força", "Pressure Load": "Pressão",
    "Gravity Load": "Peso próprio (gravidade)", "Centrifugal Load": "Carga centrífuga",
    "Mesh Refinement": "Refinamento de malha", "Run Solver": "Resolver", "Solver Job Control": "Controle do resolvedor",
    "Warp Filter": "Filtro de deformada", "Scalar Clip Filter": "Filtro por valor", "Purge Results": "Apagar resultados",
    "Beam Cross Section": "Seção de viga", "Beam Rotation": "Rotação da seção de viga",
    "Shell Plate Thickness": "Espessura de casca/chapa",
    "Electrostatic Potential Boundary Condition": "Potencial eletrostático",
    "Magnetization Boundary Condition": "Magnetização", "Electric Charge Density": "Densidade de carga elétrica",
    "Initial Flow Velocity Condition": "Velocidade inicial do escoamento",
    "Initial Pressure Condition": "Pressão inicial", "Flow Velocity Boundary Condition": "Velocidade do escoamento",
    "Initial Temperature": "Temperatura inicial", "Heat Flux Load": "Fluxo de calor",
    "Temperature Boundary Condition": "Temperatura prescrita",
    "Constant Vacuum Permittivity": "Permissividade do vácuo", "Mesh Boundary Layer": "Camada limite da malha",
    "Mesh Group": "Grupo de malha", "Erase Elements": "Apagar elementos", "Solver CalculiX": "Resolvedor CalculiX",
    "Flow Equation": "Equação de escoamento", "Flux Equation": "Equação de fluxo", "Heat Equation": "Equação de calor",
    "Pipeline Branch": "Ramo do pós-processamento", "Region Clip Filter": "Filtro por região",
    "Contours Filter": "Filtro de contornos", "Glyph Filter": "Filtro de setas (glifos)",
    "Stress Linearization Plot": "Linearização de tensões",
    "Defines a stress linearization plot": "Gráfico de linearização de tensões",
    "Calculator Filter": "Filtro calculadora", "FEM Examples": "Exemplos de simulação",
})

# Glossário Prumo por contexto: corrige termos da tradução oficial que
# confundem o usuário brasileiro ("Preencher" para Pad, "Perfuração" para
# Pocket, "Filete" para Fillet...). Chave: (contexto do Qt, texto de origem).
GLOSSARIO = {
    ("CmdPartDesignPad", "Pad"): "Extrusão",
    ("CmdPartDesignPocket", "Pocket"): "Cavidade",
    ("CmdPartDesignFillet", "Fillet"): "Arredondamento",
    ("CmdPartFillet", "Fillet"): "Arredondamento",
    ("WizardShaftTable", "Fillet"): "Arredondamento",
    ("CmdPartDesignDraft", "Draft"): "Ângulo de saída",
    ("CmdPartDesignThickness", "Thickness"): "Casca",
    ("CmdPartThickness", "Thickness"): "Casca",
    ("CmdPartDesignShapeBinder", "Shape Binder"): "Vínculo de forma",
    ("CmdPartDesignSubShapeBinder", "Sub-Shape Binder"): "Vínculo de subforma",
    ("CmdPartDesignAdditiveLoft", "Additive Loft"): "Loft aditivo",
    ("CmdPartDesignSubtractiveLoft", "Subtractive Loft"): "Loft subtrativo",
    ("CmdPartDesignAdditivePipe", "Additive Pipe"): "Varredura aditiva",
    ("CmdPartDesignSubtractivePipe", "Subtractive Pipe"): "Varredura subtrativa",
    ("CmdPartDesignClone", "Clone"): "Clone",
    ("CmdPartDefeaturing", "Defeaturing"): "Remover detalhes",
    ("CmdSketcherCreateFillet", "Fillet"): "Arredondamento",
    ("CmdSketcherCreateConstructionLine", "Construction line"): "Linha de construção",
    ("CmdSketcherCreateConstructionLine",
     "Creates a construction line: reference geometry that guides the sketch and does not become part of the "
     "profile"): "Cria uma linha de construção: geometria de referência que guia o esboço e não entra no perfil",
    ("StdCmdToggleTransparency", "Toggle Transparenc&y"): "Alternar &transparência",
    # Menus das bancadas (o FreeCAD traduz os nomes de menu no contexto "Workbench")
    ("Workbench", "&Part"): "&Sólidos",
    ("Workbench", "&Sheet Metal"): "&Chapa metálica",
    ("Workbench", "Sheet Metal"): "Chapa metálica",
    ("CmdPartRevolve", "Revolve"): "Revolução",
    ("CmdPartBox", "Cube"): "Caixa",
    ("CmdPartBox", "Creates a solid cube"): "Cria uma caixa sólida (bloco retangular)",
    ("CmdPartCut", "Cut"): "Subtrair",
    ("CmdPartCommon", "Intersection"): "Interseção",
    ("PartGui::DlgRevolution", "Revolve"): "Revolução",
    ("CmdTechDrawDetailView", "Detail View"): "Vista de detalhe",
    ("CmdTechDrawSectionView", "Section View"): "Vista em corte",
    ("CmdTechDrawSectionGroup", "Section View"): "Vista em corte",
    ("TechDrawGui::TaskBalloon", "Balloon"): "Balão",
    ("DrawViewBalloon", "Balloon"): "Balão",
    # Chapa metálica (SheetMetal): textos sem tradução pt-BR na versão embutida
    ("SheetMetal", "&Sheet Metal"): "&Chapa metálica",
    ("SheetMetal", "Extruded Cutout"): "Recorte por extrusão",
    ("SheetMetal", "Make Base Wall"): "Parede base",
    ("SheetMetal", "Make Wall"): "Aba com dobra",
    ("SheetMetal", "Make Bend"): "Dobra em canto",
    ("SheetMetal", "Fold a Wall"): "Dobrar por linha",
    ("SheetMetal", "Extend Face"): "Estender face",
    ("SheetMetal", "Extruded cutout from sketch extrusion\n1. Select a face of the sheet metal part (must not be "
                   "the thickness face) and\n2. Select a sketch for the extruded cut (the sketch must be closed).\n"
                   "3. Use Property editor to modify other parameters"):
        "Recorte a partir da extrusão de um esboço\n1. Selecione uma face da chapa (não a face da espessura) e\n"
        "2. Selecione o esboço do recorte (fechado).\n3. Ajuste os demais parâmetros no editor de propriedades",
    ("SheetMetal", "Create a sheetmetal wall from a sketch\n1. Select a Sketch to create bends with walls.\n"
                   "2. Use Property editor to modify other parameters"):
        "Cria a parede de chapa a partir de um esboço\n1. Selecione o esboço (perfil com as dobras).\n"
        "2. Ajuste espessura, raio e comprimento no editor de propriedades",
    ("SheetMetal", "Add base shape"): "Forma pronta",
    ("SheetMetal", "Add basic sheet metal object."): "Insere uma peça de chapa pronta (cantoneira, U, caixa...).",
    ("SheetMetal", "Extends one or more face, connected by a bend on existing sheet metal.\n1. Select edges to create "
                   "bends with walls.\n2. Use Property editor to modify other parameters"):
        "Cria abas ligadas por dobra na chapa existente\n1. Selecione as arestas onde ficam as dobras.\n"
        "2. Ajuste comprimento, ângulo e raio no editor de propriedades",
    ("SheetMetal", "Corner Relief to metal sheet corner.\n1. Select 2 Edges (on flat face that shared with bend faces) "
                   "tocreate Relief on sheetmetal.\n2. Use Property editor to modify default parameters"):
        "Alívio no canto da chapa\n1. Selecione 2 arestas (na face plana vizinha às dobras).\n"
        "2. Ajuste os parâmetros no editor de propriedades",
    ("SheetMetal", "Extends one or more face, on existing sheet metal.\n1. Select edges or thickness side faces to "
                   "extend walls.\n2. Use Property-editor / Task-panel to modify other parameters"):
        "Estende faces da chapa existente\n1. Selecione arestas ou faces de espessura.\n"
        "2. Ajuste no editor de propriedades ou no painel de tarefas",
    ("SheetMetal", "Extend by Sketch"): "Estender por esboço",
    ("SheetMetal", "Extends a side face using a sketch.\n1. Select a sketch to shape the extension (Good for creating "
                   "tabs).\n2. Make sure the sketch is attached to a non-edge face.\n3. Use Property-editor / "
                   "Task-panel to modify other parameters"):
        "Estende uma face lateral com o formato de um esboço (bom para orelhas)\n1. Selecione o esboço.\n"
        "2. O esboço deve estar apoiado numa face (não numa aresta).\n3. Ajuste os demais parâmetros",
    ("SheetMetal", "Fold a wall of metal sheet\n1. Select a flat face on sheet metal and\n2. Select a bend line "
                   "(sketch) on same face (ends of sketch bend lines must extend beyond edges of face) to create "
                   "sheetmetal fold.\n3. Use Property editor to modify other parameters"):
        "Dobra a chapa por uma linha\n1. Selecione uma face plana da chapa e\n2. o esboço com a linha de dobra na "
        "mesma face (a linha deve passar das bordas).\n3. Ajuste os demais parâmetros",
    ("SheetMetal", "Unfold Update"): "Atualizar planificações",
    ("SheetMetal", "Update all unfold objects.\n"): "Recalcula todas as planificações.",
    ("SheetMetal", "Flatten folded sheet metal object with default options\n1. Select flat face on sheetmetal shape.\n"
                   "2. Click this command to unfold the object with last used parameters."):
        "Planifica com as últimas opções usadas\n1. Selecione uma face plana da chapa.\n2. Clique neste comando.",
    ("SheetMetal", "Convert to Sheet Metal"): "Converter em chapa",
    ("SheetMetal", "Convert a solid/shell to a sheet metal object.\n1. Select faces to remove from end result SheetMetal."
                   "\n2. Select edges to rip (mark a seam).\n3. Use Task Panel editor to modify other parameters."):
        "Converte um sólido/casca em chapa\n1. Selecione as faces a retirar.\n2. Selecione as arestas de "
        "abertura (costura).\n3. Ajuste no painel de tarefas.",
    ("SheetMetal", "Make Hem"): "Bainha",
    ("SheetMetal", "Create hems on edges.\n1. Select edges to create bends with walls.\n2. Use Property editor to "
                   "modify other parameters"):
        "Cria bainhas nas arestas\n1. Selecione as arestas.\n2. Ajuste os demais parâmetros",
    ("SheetMetal", "Wrap Cutout"): "Recorte envolvente",
    ("SheetMetal", "Wrap cutout from a Sketch On Sheet metal faces\n1. Select a flat face on sheet metal and\n"
                   "2. Select a sketch on same face to create sheetmetal wrapped cut.\n3. Use Property editor to "
                   "modify other parameters"):
        "Recorte que acompanha as dobras, a partir de um esboço na chapa\n1. Selecione uma face plana e\n"
        "2. o esboço na mesma face.\n3. Ajuste os demais parâmetros",
}


class PrumoTranslator(QtCore.QTranslator):
    """Um único tradutor: dicionário EXTRA primeiro, depois o .qm completo.

    Retorna None (QString nula) quando não sabe traduzir, para o Qt seguir
    para o próximo tradutor da pilha.
    """

    def __init__(self, table, qm_path, parent=None):
        super().__init__(parent)
        self._t = dict(table)
        for k, v in list(table.items()):
            bare = k.replace("&", "")
            if bare not in self._t:
                self._t[bare] = v.replace("&", "")
        try:
            from PrumoPropNames import PROPS
        except Exception:  # pragma: no cover
            PROPS = {}
        self._props = PROPS
        try:
            from PrumoEnums import ENUMS
        except Exception:  # pragma: no cover
            ENUMS = {}
        self._enums = ENUMS
        self._ctx = {}
        for (c, k), v in GLOSSARIO.items():
            self._ctx[(c, k)] = v
            self._ctx.setdefault((c, k.replace("&", "")), v.replace("&", ""))
        self._qm = QtCore.QTranslator()
        self._qm_ok = bool(qm_path) and self._qm.load(qm_path)

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if context == "App::Property":
            hit = self._props.get(sourceText)
            if hit:
                return hit
        if context == "App::PropertyEnumeration":
            return self._enums.get(sourceText)
        hit = self._ctx.get((context, sourceText)) or self._t.get(sourceText)
        if hit:
            return hit
        if self._qm_ok:
            res = self._qm.translate(context, sourceText, disambiguation, n)
            if res:
                return res
        return None

    def isEmpty(self):
        return False


_state = {"tr": None, "seen": set()}


def _app():
    return QtCore.QCoreApplication.instance()


IDIOMA_PTBR = "Portuguese (Brazilian)"


def _language_is_ptbr():
    lang = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General").GetString("Language", "")
    return "Brazil" in lang or lang in ("pt-BR",)


def idioma_padrao_ptbr():
    """Perfil novo (idioma nunca escolhido): usa pt-BR, o idioma do Prumo 3D.

    Sem isso o FreeCAD segue o sistema: cai no português de Portugal ("Ficheiro") ou no inglês,
    e a tradução Prumo não é instalada. Não mexe se o usuário já escolheu um idioma
    (Editar > Preferências > Geral > Idioma). Retorna True se definiu o idioma agora.
    """
    grp = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General")
    if grp.GetString("Language", ""):
        return False
    grp.SetString("Language", IDIOMA_PTBR)
    try:
        import FreeCADGui
        FreeCADGui.setLocale(IDIOMA_PTBR)
    except Exception:
        pass
    return True


def raise_priority():
    """(Re)instala o tradutor Prumo no topo da pilha do Qt."""
    tr = _state["tr"]
    if tr is None:
        return
    app = _app()
    app.removeTranslator(tr)
    app.installTranslator(tr)


def install():
    if not FreeCAD.ParamGet(PARAM_PATH).GetBool("PrumoTranslations", True):
        return
    idioma_padrao_ptbr()
    if not _language_is_ptbr():
        return
    if _state["tr"] is None:
        qm = os.path.join(ADDON_DIR, "translations", "prumo_ptbr.qm")
        _state["tr"] = PrumoTranslator(EXTRA, qm if os.path.isfile(qm) else "")
    raise_priority()
    QtCore.QTimer.singleShot(1500, retitle_docks)


DOCK_TITULOS = {"Report view": "Relatório", "Python console": "Console Python"}


def retitle_docks():
    """Painéis criados antes do tradutor carregar ficam com título em inglês."""
    if _state["tr"] is None:
        return
    try:
        import FreeCADGui
        from PySide import QtWidgets
        mw = FreeCADGui.getMainWindow()
        for dock in mw.findChildren(QtWidgets.QDockWidget):
            novo = DOCK_TITULOS.get(dock.objectName())
            if novo and dock.windowTitle() != novo:
                dock.setWindowTitle(novo)
                act = dock.toggleViewAction()
                if act is not None:
                    act.setText(novo)
    except Exception:  # pragma: no cover
        pass


def uninstall():
    if _state["tr"] is not None:
        _app().removeTranslator(_state["tr"])


def on_workbench(name):
    """Na primeira ativação de cada bancada o módulo instala seus tradutores."""
    if name in _state["seen"]:
        return
    _state["seen"].add(name)
    QtCore.QTimer.singleShot(0, raise_priority)
    QtCore.QTimer.singleShot(200, retitle_docks)
