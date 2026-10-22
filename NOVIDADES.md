# Novidades do Prumo 3D

O que mudou em cada versão, da mais nova para a mais antiga. Os arquivos para baixar ficam na
[página de versões](https://github.com/prumo3d/prumo3d/releases).

**Como as versões são numeradas** (até a 1.0, todas são beta):

- `0.X.0`: entrou ferramenta nova ou mudou o jeito de usar alguma coisa (ex.: 0.2.0).
- `0.X.Y`: correções e ajustes pequenos, sem ferramenta nova (ex.: 0.1.1).
- `-beta` no fim: versão de teste; guarde cópia dos seus arquivos.

## Em desenvolvimento

Já está no código e entra na próxima versão.

### Novo

- **Tubulação** (aba Estruturas): tubos e conexões automáticos sobre o traçado do Esboço 3D (ou de um
  esboço com linhas retas). Em cada nó entra a peça certa do catálogo: joelho 90° ou 45°, tê, tê de
  redução (ou tê com bucha), luva de redução, cruzeta e cap nas pontas soltas. O tubo de cada trecho sai
  cortado descontando o avanço das conexões, e a lista mostra as peças, as barras de 6 m necessárias
  (com emenda pela bolsa quando o trecho passa da barra) e os avisos (ângulo sem conexão, redução que
  não existe). O diâmetro pode mudar trecho a trecho. "Copiar lista de materiais" leva tudo para a
  planilha. Primeira linha: **PVC soldável água fria Tigre**, de 20 a 110 mm, com as medidas do catálogo
  técnico do fabricante.
- **Registro de esfera na tubulação:** na tabela do painel, informe a distância do início do trecho até o
  registro (20 a 60 mm). O tubo é dividido e cada metade entra numa bolsa do registro.
- **Tubulação na lista de materiais:** a Lista de materiais (e a tabela na folha ABNT) traz um item por
  diâmetro de tubo, em barras, e um por conexão, com o fabricante.

## 0.2.0 beta — 22/10/2026

### Novo

- **Esboço 3D** (abas Esboço e Estruturas): linhas no espaço, ponto a ponto. Clique em **Desenhar** e vá
  clicando na vista: o ponto cai no plano que passa pelo último ponto, e **Tab** troca o plano (XY → YZ
  → ZX). O cursor encaixa em vértices e pontas de arestas e anda de passo em passo (10 mm, ajustável).
  **Esc** termina o trecho e o próximo clique começa um ramal; Esc de novo para de desenhar. Para
  medidas exatas, digite o próximo ponto (absoluto ou ΔX, ΔY, ΔZ a partir do último) e tecle Enter.
  Os cantos podem ser arredondados (curva de tubo). Serve de esqueleto da estrutura soldada e de
  caminho de varredura.

## 0.1.1 beta — 22/10/2026

### Novo

- **Faixa contextual na aba Esboço:** só aparecem as ferramentas que servem no momento. Fora da edição,
  criar, editar, anexar e validar; dentro, desenhar, restrições e modificar. O que depende só da
  seleção continua visível, esmaecido. Para ver tudo, clique com o botão direito na faixa e desmarque
  "Mostrar só as ferramentas do momento".
- **Conferência do esboço ao sair:** pontas quase encostadas (contorno que parece fechado mas está
  aberto), pontas soltas num perfil de extrusão, elementos de tamanho zero e coincidências que faltam
  aparecem num aviso com o botão **Corrigir**, antes de a extrusão falhar.

### Ajustes

- O console Python começa fechado, para não confundir quem está começando (Início → Árvore do modelo e o
  menu Vista → Painéis continuam trazendo os painéis de volta).

## 0.1 beta — 22/10/2026

Primeira versão pública, para Windows e Linux. Baseada no FreeCAD 1.1.4.

### O que tem de novo em relação ao FreeCAD

- **Interface em português** com faixa de abas (Início, Esboço, Peça, Sólidos, Montagem, Desenho,
  Estruturas, Chapa, Planilha, Simulação), tema claro e escuro e tela inicial com exemplos. A faixa
  muda de altura arrastando a borda de baixo, e os grupos de botões se alargam pelos divisores.
- **Painéis de tarefa visuais** (como o PropertyManager do SolidWorks): mensagem no topo, seções com
  ícone, dica em cada campo e caixas de seleção que aceitam a seleção feita antes **ou depois** de
  abrir o comando. Subtrair, Unir e as outras booleanas também pedem a seleção se você chamar sem ela.
- **Árvore do modelo** com nomes em português (Extrusão, Cavidade, Corpo...) e seleção em azul.
- **Ícones do Prumo desde a primeira abertura**, sem precisar aplicar o tema e reiniciar.
- **Materiais usados no Brasil**: a biblioteca traz só aços estruturais (NBR 7007, NBR 6648, ASTM),
  chapas, aços para vaso de pressão, tubos, inox, construção mecânica, ferro fundido, alumínio e latão,
  com norma e fonte em cada um. Arquivos feitos no FreeCAD original abrem com o material certo
  (biblioteca "Compatibilidade", separada).
- **Tutoriais interativos**: "primeira peça" e "estrutura soldada". Cada passo é marcado sozinho
  quando você o faz, e "Mostrar onde" pisca o botão certo na faixa.
- **Esboço:** pontos-ímã em quadrantes, pontos médios e interseções; linhas de inferência
  (alinhamento com pontos existentes); ao concluir o esboço, a vista enquadra o modelo.
- **Régua de histórico** do corpo, como no ZW3D e no SolidWorks: arraste a régua amarela no painel
  Histórico do corpo para recuar o modelo até uma operação; as seguintes ficam em cinza e as novas
  entram naquele ponto. Desfazer volta a régua.
- **Cotas na tela:** duplo clique na peça mostra as cotas da operação para editar ali mesmo.
- **Menu do botão direito** pela seleção (extrusão, cavidade, arredondamento, medir, massa).
- **Propriedades de massa** (massa, centro de gravidade, inércia) e **lista de materiais** com tabela
  na folha.
- **Propriedades da peça** (código, denominação, revisão, acabamento, material): vão para a lista de
  materiais e para a legenda da folha, que acompanha quando a peça muda.
- **Variantes da peça** (P, M, G...) numa tabela de parâmetros ligada às cotas, como as configurações
  do SolidWorks, e **modelos com regras** (placa com furos, flange, suporte em L, eixo escalonado) que
  avisam quando o projeto não fecha.
- **Folhas A0 a A4 no padrão ABNT** (NBR 16752 e NBR 10068), com legenda brasileira (responsável
  técnico, CREA/CFT, ART), vistas no 1º diedro e escalas normalizadas.
- **Estruturas soldadas** com perfis brasileiros (W, HP, U, I, cantoneiras, tubos e metalon):
  grupos de perfis, ponto de fixação, cantos em meia-esquadria ou de topo, recorte pelo contorno,
  reforços (mão-francesa), tampas de tubo, placas de base, cordões de solda, lista de corte e lista
  de soldas. O diálogo Cantos mostra um desenho de cada tratamento. Como no SolidWorks, a estrutura
  começa sem grupo: crie o grupo, escolha o perfil e clique nas linhas do desenho. Cada linha ganha a
  barra na hora, e perfil, giro e ponto de fixação também atualizam a prévia. Aplicar grava e Cancelar
  desfaz. Os números das linhas aparecem sobre o desenho. Cada barra pode ter giro próprio (coluna
  "Giro da barra" ou botão Girar 90°). O lado do perfil ("Sup.", "Inf.") não depende mais do
  sentido em que a linha foi desenhada: num quadro, todas as barras ficam do mesmo lado.
- **Simulação de estruturas por barras** (aba Estruturas → Simular estrutura): clique nos nós para
  pôr apoios (engaste, rótula, rolete), monte os casos de carga (peso próprio automático, cargas
  distribuídas e concentradas nas barras, forças nos nós) e as combinações saem da NBR 8681:2025. Os
  esforços, as reações e a deformada são calculados na hora, e cada barra é verificada (tração,
  compressão com flambagem, flexão com FLT/FLM/FLA, cortante, esforços combinados e flecha), com a
  taxa de uso em cores na tela, os diagramas de N, V e M e a memória de cálculo em PDF. A análise é
  de 2ª ordem (P-Δ) nas combinações últimas e acusa quando a estrutura perde estabilidade (por
  exemplo, pórtico plano sem travamento fora do plano). Balanços e vigas contínuas desenhadas em
  vários pedaços são reconhecidos na flambagem e na flecha.
- **Assistente de estruturas** (abas Estruturas e Simulação): o passo a passo da simulação por barras,
  como o Assistente de simulação. Estrutura, material, apoios, rótulas, casos de carga, critérios,
  conferência de pendências (carga zero, apoio fora de nó, barra que sumiu, falta de vento), cálculo,
  resultados com deslocabilidade, detalhe das ligações e memória de cálculo em PDF.
- **NBR 8800:2024 e NBR 8681:2025**: a verificação foi refeita pelas edições vigentes, conferidas no
  texto da norma. Sem coeficiente K (flambagem com o comprimento real e estabilidade pela análise de
  2ª ordem), forças nocionais de 0,3 % da carga gravitacional em ±X e ±Y, rigidez de 80 % quando a
  estrutura é de média deslocabilidade e aviso na grande, flambagem local pela área efetiva, Cb dentro
  de λr e sem o teto de 3,0, kv = 5,34 e os novos coeficientes de ponderação (equipamentos 1,25,
  industrializados 1,30, temperatura gerada por equipamentos 1,50). Arquivos com os tipos de caso
  antigos abrem com os nomes novos.
- **Molas, contraventamento só de tração e modos de vibrar**: apoio elástico (kN/mm) clicando no nó,
  barras de contraventamento que saem do modelo quando comprimem, e as frequências naturais da
  estrutura com a forma de cada modo desenhada na tela.
- **Detalhe da ligação por elementos finitos**: no painel da simulação, escolha "Detalhar nó" e clique
  numa ligação ou apoio. O Prumo recorta o nó, aplica nos cortes os esforços da análise por barras e
  calcula as tensões no sólido (CalculiX), com a zona de perigo comparada a fy/γa1 e a conferência
  com a teoria de barras. O resultado abre no Assistente de simulação (malha, convergência, relatório).
  As soldas das barras que chegam no nó (filete em todo o contorno: perna necessária, mínima e taxa
  do metal-base) e os chumbadores da placa de base (tração, corte e interação) também são verificados
  pela NBR 8800:2024.
- **Rótulas e treliças**: no painel da simulação, o modo "Rótula" solta o momento na ponta clicada
  da barra (ligação flexível, viga Gerber) ou transforma a barra em treliça (só força normal). As
  rótulas aparecem na tela e na memória de cálculo.
- **Carga variável ou parcial**: carga distribuída trapezoidal ou triangular, em toda a barra ou num
  trecho dela.
- **Seção personalizada** (aba Estruturas): um esboço fechado vira perfil da estrutura soldada
  (chapas compostas, perfis dobrados, perfis fora do catálogo), com área, inércias e constante de
  torção calculadas pelo contorno. O empenamento é resolvido por elementos finitos na própria seção
  (centro de cisalhamento, Cw e J), com flexo-torção e FLT gerais, e as chapas são reconhecidas
  sozinhas para a flambagem local (mesas em balanço, almas, paredes) e o cortante.
- **Vasos de pressão** (aba própria, "Vasos"): formulário com prévia ao vivo para casco, tampos
  (elíptico 2:1, torisférico, hemisférico), diâmetro, comprimento, material, corrosão, bocais e
  suportes (selas, saia ou pernas, na horizontal ou na vertical). Calcula espessuras e PMTA pelo
  ASME VIII Div. 1, a pressão do teste hidrostático ou pneumático, simula o teste por elementos finitos
  de casca e gera a folha A3 com vistas cotadas e a tabela de dados de projeto.
- **Vídeo do comportamento**: grava um MP4 (ou GIF) da estrutura com cargas e apoios, a deformada
  colorida pela taxa de uso, o momento fletor e as barras críticas; no estudo de elementos finitos,
  a peça deformando com as cores de tensão (vermelho = atingiu o limite).
- **Prévia ao vivo** também no reforço, tampa, placa de base, solda e fixadores: o resultado aparece
  no desenho enquanto se mexe no painel, com "Início" e "Fim" marcados nas barras. Os avisos aparecem
  no painel antes de aplicar. Duplo clique na árvore (estrutura, barra, reforço, tampa, placa, solda,
  fixador) abre o mesmo painel, editando o objeto. Cantos, Trocar perfil, Modelos com regras e
  Propriedades da peça também mostram o resultado na hora; o diálogo Cantos marca na tela os cantos
  da linha escolhida.
- **Chapa metálica** (bancada SheetMetal embutida): paredes, dobras e planificação, com **fator K por
  material** (aço, inox, alumínio, DIN 6935) e **planificação em DXF num clique** (contorno e dobras).
- **Montagem:** restrições com os nomes do SolidWorks (coincidente, concêntrica...), **verificar
  interferência** e **copiar projeto** (como o Pack and Go: copia montagem e peças renomeando).
- **Guia "vindo do SolidWorks / ZW3D"**: onde fica cada comando que você já conhece.
- **Peças padronizadas:** parafusos, porcas e arruelas métricas.
