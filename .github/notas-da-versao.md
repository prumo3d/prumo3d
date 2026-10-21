## Prumo 3D 0.1 beta

Primeira versão de teste do Prumo 3D: modelagem 3D paramétrica em português, com ferramentas para o
dia a dia da engenharia mecânica no Brasil. É baseado no FreeCAD 1.1 e usa os mesmos arquivos `.FCStd`.

> **Versão beta:** feita para testar. Guarde cópia dos seus arquivos e não use ainda em projeto com
> prazo. Relatos de problema são muito bem-vindos (veja "Como relatar um problema").

### O que tem de novo em relação ao FreeCAD

- **Interface em português** com faixa de abas (Início, Esboço, Peça, Sólidos, Montagem, Desenho,
  Estruturas, Chapa, Planilha, Simulação), tema claro e escuro e tela inicial com exemplos. A faixa
  muda de altura arrastando a borda de baixo, e os grupos de botões se alargam pelos divisores.
- **Painéis de tarefa visuais** (como o PropertyManager do SolidWorks): mensagem no topo, seções com
  ícone, dica em cada campo e caixas de seleção que aceitam a seleção feita antes **ou depois** de
  abrir o comando. Subtrair, Unir e as outras booleanas também pedem a seleção se você chamar sem ela.
- **Árvore do modelo** com nomes em português (Extrusão, Cavidade, Corpo...) e seleção em azul.
- **Materiais usados no Brasil**: a biblioteca traz só aços estruturais (NBR 7007, NBR 6648, ASTM),
  chapas, aços para vaso de pressão, tubos, inox, construção mecânica, ferro fundido, alumínio e latão,
  com norma e fonte em cada um. Arquivos feitos no FreeCAD original abrem com o material certo
  (biblioteca "Compatibilidade", separada).
- **Tutoriais interativos**: "primeira peça" e "estrutura soldada". Cada passo é marcado sozinho
  quando você o faz, e "Mostrar onde" pisca o botão certo na faixa.
- **Esboço:** pontos-ímã em quadrantes, pontos médios e interseções; linhas de inferência
  (alinhamento com pontos existentes); ao concluir o esboço, a vista enquadra o modelo.
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
  distribuídas e concentradas nas barras, forças nos nós) e as combinações saem da NBR 8681. Os
  esforços, as reações e a deformada são calculados na hora, e cada barra é verificada (tração,
  compressão com flambagem, flexão com FLT/FLM/FLA, cortante, esforços combinados e flecha), com a
  taxa de uso em cores na tela, os diagramas de N, V e M e a memória de cálculo em PDF. A análise é
  de 2ª ordem (P-Δ) nas combinações últimas e acusa quando a estrutura perde estabilidade (por
  exemplo, pórtico plano sem travamento fora do plano). Balanços e vigas contínuas desenhadas em
  vários pedaços são reconhecidos na flambagem e na flecha.
- **Detalhe da ligação por elementos finitos**: no painel da simulação, escolha "Detalhar nó" e clique
  numa ligação ou apoio. O Prumo recorta o nó, aplica nos cortes os esforços da análise por barras e
  calcula as tensões no sólido (CalculiX), com a zona de perigo comparada a fy/γa1 e a conferência
  com a teoria de barras. O resultado abre no Assistente de simulação (malha, convergência, relatório).
- **Rótulas e treliças**: no painel da simulação, o modo "Rótula" solta o momento na ponta clicada
  da barra (ligação flexível, viga Gerber) ou transforma a barra em treliça (só força normal). As
  rótulas aparecem na tela e na memória de cálculo.
- **Carga variável ou parcial**: carga distribuída trapezoidal ou triangular, em toda a barra ou num
  trecho dela.
- **Seção personalizada** (aba Estruturas): um esboço fechado vira perfil da estrutura soldada
  (chapas compostas, perfis dobrados, perfis fora do catálogo), com área, inércias e constante de
  torção calculadas pelo contorno. A verificação pela NBR 8800 dessas seções é simplificada (avisada).
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

### Como baixar

| Sistema | Arquivo | Como usar |
|---|---|---|
| Windows 10/11 (64 bits) | `Prumo3D_…-installer.exe` | Rode o instalador. Instala ao lado de um FreeCAD já existente, sem substituí-lo. |
| Windows (portátil) | `Prumo3D_…-Windows-….7z` | Descompacte e abra `bin\Prumo3D.exe`. Não precisa instalar. |
| Linux (64 bits) | `Prumo3D_…-Linux-….AppImage` | Marque como executável (`chmod +x`) e abra. Em algumas distribuições é preciso instalar o pacote `libfuse2`. |

Cada arquivo tem um `-SHA256.txt` com o código de verificação. Nem todos os formatos saem em toda
versão de teste.

Os instaladores ainda não têm assinatura digital: o Windows mostra o aviso de "editor desconhecido".
Clique em **Mais informações → Executar assim mesmo**.

### Roteiro de teste (15 minutos)

1. Abra o Prumo 3D e confira a tela de abertura e a tela inicial. Se o painel da árvore (à esquerda)
   sumir, use **Início → Árvore do modelo**.
2. Em **Exemplos**, abra os três arquivos e explore a árvore à esquerda.
3. **Peça:** faça um esboço com um círculo e uma linha (veja os pontos-ímã), extrude e dê duplo
   clique na peça para mudar uma cota.
4. **Desenho:** com a peça selecionada, crie uma **Folha ABNT A3** e depois a **Lista de materiais**.
5. **Estruturas:** faça o **Tutorial da estrutura** (aba Estruturas → Tutorial): esqueleto, dois
   grupos de perfis, cantos, reforço, cordões de solda e lista de corte.
6. **Chapa:** abra o exemplo da chapa dobrada e use **Planificar em DXF**; abra o DXF no seu CAD 2D.
7. **Montagem:** coloque duas peças que se invadem e use **Verificar interferência**; depois
   **Copiar projeto** para outra pasta.
8. **Peça:** use **Modelo com regras** para gerar uma placa com furos; mude a distância à borda e veja
   o aviso. Em **Variantes da peça**, crie P/M/G e troque a variante ativa.
9. Salve, feche e abra de novo.

### Limitações conhecidas

- Arquivos com objetos do Prumo (estruturas, reforços, soldas, folhas ABNT) abertos no FreeCAD comum
  mostram as formas, mas esses objetos não são recalculados lá.
- Alguns perfis e tubos estão marcados **"a conferir"** (fonte secundária): o Prumo avisa na escolha
  do perfil. Confira no catálogo do fabricante antes de usar em projeto.
- O vaso de pressão ficou para uma versão futura.
- A simulação de estruturas por barras verifica pela NBR 8800:2008 e combina pela NBR 8681:2003, que
  foram substituídas pela NBR 8800:2024 e pela NBR 8681:2025: o resultado aparece com esse aviso e
  serve para pré-dimensionamento até a conferência com as edições vigentes. Imperfeições iniciais da
  análise de 2ª ordem (4.9.7) ainda não entram; barras ligadas rigidamente nos nós; ligações, placas
  de base e soldas não são verificadas.

### Como relatar um problema

No Prumo, abra **Ajuda → Sobre** e clique em **Copiar informações do sistema**. Cole esse texto junto
com a descrição do problema (o que fez, o que esperava, o que aconteceu) e, se possível, um print da tela.

---

O Prumo 3D é software livre (LGPL-2.1-or-later), baseado no [FreeCAD](https://www.freecad.org). Não é
um projeto oficial do FreeCAD.
