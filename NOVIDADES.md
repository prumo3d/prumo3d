# Novidades do Prumo 3D

O que mudou em cada versão, da mais nova para a mais antiga. Os arquivos para baixar ficam na
[página de versões](https://github.com/prumo3d/prumo3d/releases).

**Como as versões são numeradas** (a 1.0 é a primeira versão final; as anteriores eram beta):

- `X.Y.0`: entrou ferramenta nova ou mudou o jeito de usar alguma coisa (ex.: 1.1.0).
- `X.Y.Z`: correções e ajustes pequenos, sem ferramenta nova (ex.: 1.0.1).
- `-beta` no fim: versão de teste antes da final; guarde cópia dos seus arquivos.

## Em desenvolvimento

### Novidades

- **Esboço 3D: caixinha de comprimento junto do cursor**, como no esboço comum: mostra o comprimento ao vivo;
  é só digitar o número (com o cursor na vista) e teclar Enter: a linha fica com essa medida e a próxima sai do
  ponto novo.
- **Esboço 3D: ímãs.** Perto de um ponto do esboço o cursor gruda nele (e a ponta fica presa ao ponto); perto
  de uma linha, o ponto cai em cima dela; no eixo, a linha para alinhada com um ponto que já existe. Acaba a
  linha que passa raspando ou por cima da outra.
- **Tubulação ajusta o traçado às conexões.** Canto ou ramal desenhado fora dos ângulos que têm conexão na
  linha (até 20° de diferença) gira sozinho para o ângulo da conexão, sem mudar os comprimentos: no PVC e na
  rosca, joelho de 90° ou 45° e tê a 90°. Acontece ao criar a tubulação, ao dar OK no Esboço 3D que ela usa e
  ao trocar a linha; também há o botão **Ajustar traçado às conexões** no painel.
- **Aço: curva cortada.** Na linha de solda de topo, um canto de qualquer ângulo até 90° sai com a curva de 90°
  raio longo cortada no ângulo (na lista: "Curva 90° raio longo … cortada a 73,3°"), com as duas soldas.

### Correções

- **Aviso em inglês ao montar.** O "Ground Part?" que aparece ao inserir a primeira peça na montagem agora sai
  em português ("Fixar a peça?", com Sim, Sempre fixar, Nunca fixar e Não), assim como os avisos de salvar o
  documento antes de inserir peças de outro arquivo, "Alinhar peças" e "Escolha uma peça" da vista explodida.
- **Vistas no meio da folha.** Na Folha ABNT, na Paleta de vistas e nas folhas em lote, as vistas ficam no meio
  da faixa entre a legenda e o alto do quadro, com folga para as cotas, em vez de coladas no alto.
- **Publicação do Linux.** O AppImage passa a ser montado com uma versão fixa e conferida da ferramenta (a
  versão "contínua" mudou sem aviso em 29/10/2026 e travou a publicação da 1.2.1).

## 1.2.1 — 29/10/2026

### Novidades

- **Válvulas na linha de aço.** Na tabela da tubulação de solda de topo, a coluna **Válvulas a (mm)** aceita a
  distância e o tipo (ex.: `300 gaveta; 1200 retenção`): gaveta, globo, esfera (passagem reduzida) e retenção
  portinhola, flangeadas, classe 150 ou 300, com face a face da ASME B16.10-2022 (conferida em duas fontes).
  Cada válvula leva junta e estojos dos dois lados e o flange de pescoço do tubo; o corte desconta tudo.
  No isométrico, símbolo de cada tipo e cota em cadeia até a válvula (e até as juntas de desmontagem).
- **Catálogos de perfis oficiais na Estrutura** (trazidos da bancada Steel Structures, de Marcos Roberto da
  Silva, LGPL-2.1, com crédito em cada perfil): Gerdau tabela de bitolas 01/23 (W, HP, I, U, T e cantoneiras),
  Tuper 2024 (678 tubos quadrados, 1.190 retangulares e 1.131 redondos), Ue da NBR 6355:2012 (85) e barras
  redonda, quadrada e chata da NBR 16683:2018. O tubo Sch 40/80 passa a "confirmado" (B36.10M conferida em duas
  fontes). Tubos e Ue com os cantos e dobras arredondados: a área bate com a massa da tabela (antes, com
  canto vivo, os tubos grossos passavam 7 %, contra a segurança). Inércia conferida com a da NBR 6355 e com o
  sólido de cantos reais. T, tubo retangular, Ue e barras passam pela verificação da NBR 8800 pelo método
  geral; tubos e Ue avisam que são formados a frio (NBR 14762).
  - Desenhos já feitos não mudam: os I e U antigos (mesa estimada pela massa) e o metalon antigo ficam como
    eram, numa lista que só aparece para quem usa, e o aviso diz qual é o equivalente Gerdau.
  - Três U da Gerdau ficaram de fora (3" x 7,44, 10" x 30,80, 12" x 29,76): a própria fonte deixou em revisão.
- **Esboço 3D pelos eixos, como no ZW3D.** Do último ponto saem os eixos X (vermelho), Y (verde) e Z (azul):
  a linha segue o eixo para onde o mouse aponta, para o lado + ou −, e o eixo ativo fica em destaque; longe
  dos eixos a linha fica livre. Cada linha desenhada assim já sai com a restrição do eixo e a cota. Depois de
  desenhar, **duplo clique numa linha** abre a caixinha do comprimento (o que vem depois anda junto, sem
  deformar) e **arrastar a ponta** leva a linha para outro eixo. O painel mostra a situação do esboço: sem
  definição, subdefinido, não resolvido ou bem definido. Tab continua trocando para desenhar num plano.
- **Arredondamento automático** (aba Peça, Acabamento). Arredonda de uma vez todas as arestas de um tipo:
  cantos vivos para fora (quebrar canto), cantos para dentro (raio de concordância) ou todas; se quiser, só as
  paralelas a X, Y ou Z ou só as retas. As arestas escolhidas ficam em destaque antes do OK. Num Corpo vira um
  Arredondamento normal da árvore (editável depois). Raio grande demais avisa e não deixa nada pela metade.
- **Folhas em lote** (aba Desenho). Escolha a montagem, a estrutura ou as peças: sai uma folha ABNT por peça
  fabricada, com as vistas, a legenda da peça, "folha k / n", número do desenho com prefixo (ex.: DES-01) e as
  cotas gerais; peças iguais saem numa folha só com a quantidade no título. Se quiser, já salva o PDF de cada
  folha na pasta Folhas do projeto. Compradas, de referência, cordões de solda e tubulação ficam de fora.
- **Cotas do corte** (aba Desenho, Cotas). Na vista em corte: largura e altura do corte e o diâmetro (ou raio)
  de cada furo e arco cortado, de uma vez.

### Correções

- **Esboço: cota repetida e aviso sem motivo.** Com a ferramenta Cota, o aviso de "super-restrito" aparecia
  mesmo sem cota a mais e sobravam cotas repetidas (uma comandando e outra entre parênteses). O guarda de
  restrições mexia no esboço enquanto a ferramenta ainda mostrava a prévia da cota; agora ele espera a
  ferramenta terminar.
- **Faixa de ferramentas sumida.** Se a janela fosse salva com a faixa oculta, ela não voltava mais (não há
  menu para reativá-la). Agora a faixa sempre reaparece.
- **Queda ao redimensionar o quadro "Como funciona".** O desenho do quadro se redesenhava em cadeia a cada
  redimensionamento e podia derrubar o programa; agora só redesenha quando muda de tamanho.

## 1.2.0 — 29/10/2026

### Novidades

- **Atualização só do complemento (poucos MB).** A partir desta versão, cada versão nova publica também
  `Prumo3D_<versão>-complemento.zip` (cerca de 5 MB, contra centenas de MB do pacote completo). Em Ajuda →
  Sobre → Verificar atualizações, quando ele serve, o Prumo baixa só esse arquivo, confere o SHA-256,
  instala na pasta do usuário (sem pedir administrador) e oferece **Reabrir agora**. Proteções:
  - só aplica sobre a mesma base de FreeCAD e a partir do pacote completo mínimo; senão oferece o pacote
    completo, como antes;
  - se um pacote completo mais novo for instalado depois, ele volta a valer sozinho;
  - se a versão atualizada não abrir, o Prumo abre com a instalada na mesma hora e não tenta mais com ela;
  - "Copiar informações do sistema" diz qual está valendo.
  Quem está na 1.1 baixa o pacote completo uma última vez: o atualizador da 1.1 ainda não conhece o
  complemento.
- **Vasos: perímetro medido com fita métrica.** Em vaso existente não dá para medir o diâmetro por dentro:
  agora a medida do costado pode ser o perímetro externo, medido com fita em volta do vaso (é o padrão no
  painel). O Prumo calcula Ø externo = P/π e Ø interno = Ø externo − 2·t (com a espessura adotada ou, sem ela,
  a chapa comercial da mínima). A memória de cálculo mostra a conta. Projeto novo continua com o diâmetro
  interno.
- **Desenho: solda, rugosidade e ajuste furo/eixo em português.** As três telas agora seguem o padrão de
  cartões do Prumo, com o desenho de cada símbolo no botão:
  - *Solda*: clique na aresta, escolha o tipo (filete, V, meio-V, topo reto, U, J, cordão, tampão) e o lado
    (da seta, oposto ou os dois); a linha de chamada sai para fora da vista, com garganta, comprimento,
    solda em todo o contorno e solda de campo.
  - *Rugosidade*: qualquer processo, usinado ou bruto, Ra com a classe N ao lado; o símbolo fica sempre do
    lado de fora da superfície (embaixo e à direita vai numa linha de chamada, nunca de cabeça para baixo).
  - *Ajuste furo/eixo*: furo-base ou eixo-base com os ajustes preferenciais e o uso de cada um (H7/g6
    deslizante, H7/s6 prensado...). Mostra os afastamentos e a folga ou interferência, e grava a tolerância
    na cota escolhida. Tabelas ISO 286 até 500 mm conferidas célula por célula com a tabela do FreeCAD;
    confira na edição vigente da ABNT NBR 6158 antes de liberar o desenho.
  As ferramentas originais do FreeCAD continuam em "Mais".
- **Tubulação de aço carbono.** Três linhas novas no comando Tubos e conexões:
  - *Solda de topo SCH 40 e SCH 80*: tubos ASME B36.10M, curvas de raio longo, tês, tês de redução, reduções
    concêntricas e caps ASME B16.9 (a curva sai desenhada como curva). Flanges de pescoço ASME B16.5
    classe 150 ou 300 nas pontas soltas (bocal de equipamento) e em juntas de desmontagem no meio do trecho,
    com junta espiralada e estojos na lista. O tubo é cortado até a ponta de solda do pescoço, contando o
    ressalto de 2 mm e a junta. Conta as soldas de topo (inclusive emendas de barra).
  - *Roscada BSP*: tubo NBR 5580 classe M e conexões de ferro maleável (Tupy): cotovelos, tês, tês de
    redução, luvas, buchas (o sextavado entra no desconto), tampões e uniões nas juntas de desmontagem. A
    emenda de barra entra na lista como luva.
  - Medidas conferidas em duas fontes cada; o que diverge entre fabricantes aparece como aviso "a conferir".
    Materiais na lista são os típicos (A106 B, A234 WPB, A105, B7/2H): confira na especificação do projeto.
- **Folha isométrica.** Novo botão na aba Tubulação (e no painel da tubulação): folha A3 com o isométrico
  unifilar da linha, cota de eixo a eixo em cada trecho, balão com o número de cada peça, etiqueta P1, P2…
  em cada tubo, lista de material, lista de corte, soldas e observações. Chamado de novo, atualiza a mesma
  folha. Sai em PDF pelo Salvar PDF de sempre.
- **Montagem: batente de contato e trajetória de um ponto** (ideias do SolidCraft), no próprio Mover junta:
  - *Parar no contato*: com a opção ligada, a peça que gira ou desliza para ao encostar em outra, em vez de
    atravessar (procura o ponto de contato com precisão de centésimos). A mensagem diz em qual peça encostou.
  - *Trajetória de um ponto*: clique num vértice (ou aresta redonda) da peça que se move e em Traçar
    trajetória. O Prumo varre a junta na faixa dela (os limites ou uma volta), desenha a linha por onde o
    ponto passa e devolve a montagem para onde estava. Serve para conferir folga e curso. Com o batente
    ligado, a linha termina no contato. Cancelar tira as trajetórias.

## 1.1.0 — 29/10/2026

### Novidades

- **Montagem com as restrições do SolidWorks:**
  - **Tangente:** face curva (cilindro, esfera, cone) encostada em outra face, plana ou curva. Confere as faces
    e avisa se as duas forem planas (aí é Coincidente).
  - **Coincidente** e **Distância** em botões separados (antes era um botão só).
  - **Padrão de componentes** linear e circular: repete um componente em linha ou em volta de um eixo (aresta,
    face ou eixo da montagem); as cópias acompanham o original e o padrão se edita com duplo clique.
  - **Nova peça aqui:** cria uma peça nova já dentro da montagem.
  - **Mover junta:** gira uma dobradiça ou desliza um deslizante por um controle, vendo a montagem mexer.
    Respeita os limites da junta, e o que está preso à peça vai junto. Cancelar volta tudo para onde estava.
  - **Travar juntos:** prende dois ou mais componentes uns nos outros onde estão (grupo rígido), sem mexer em
    nada.
  - **Verificar interferência com folga mínima:** além das peças que se invadem, lista os pares que ficam mais
    perto que a folga pedida, com a distância.
- **Faixa que mostra o que serve agora:** sem documento aberto, só aparece o que começa um trabalho (Novo,
  Abrir…). Nas abas que dependem de "estar dentro" de algo, aparece só o primeiro passo e uma dica: Desenho
  sem folha aberta (Folha ABNT, Paleta de vistas, Abrir folha), Montagem sem montagem aberta (Nova montagem,
  **Abrir montagem**), Simulação sem estudo (Assistente, Novo estudo) e Planilha sem planilha aberta. As ferramentas raras de cada grupo ficam no botão
  **Mais**. Para ver tudo como antes: Preferências do Prumo, ou botão direito na faixa → desmarque "Mostrar só
  as ferramentas do momento".
- **Aba Desenho na ordem do trabalho:** Folha → Vistas → Cotas → Anotação → Entregar, com **Cotas gerais**,
  **Salvar PDF** (com o número do desenho no nome do arquivo) e **Exportar DXF** em um clique.
- **Cota a mais não deixa o esboço vermelho:** uma cota que sobraria (ou entraria em conflito) vira **cota de
  referência** na hora: continua na tela, mostrando a medida, sem comandar. Um aviso diz o que aconteceu, com
  o botão "Aplicar mesmo assim" para quem quiser. (Restrição geométrica a mais continua com o painel do
  esboço, que avisa e oferece apagar a mais recente.)
- **Erros que já trazem o conserto:** na Tangente com duas faces planas, o aviso tem o botão "Usar
  Coincidente", que grava na hora; numa montagem sem peça fixa, o painel da restrição oferece "Fixar" a
  primeira peça.
- **Lista de materiais com tipo de item:** em Propriedades da peça, "Na lista de materiais" pode ser
  Fabricado (o normal), Comprado (uma linha só, sem as peças de dentro: motor, redutor, cilindro) ou
  Referência (não entra: gabarito, máquina vizinha).
- **Componentes dos sólidos** (aba Montagem): um STEP (ou objeto) com vários sólidos vira uma peça para cada
  sólido, no lugar, prontas para receber restrições.
- **Preferências:** liga e desliga "Faixa só com as ferramentas do momento" (vale na hora) e "Cota a mais vira
  cota de referência".
- **Procurar comando (Ctrl+K ou a lupa no alto da faixa):** digite parte do nome (furo, tangente, cota…) e
  tecle Enter. A faixa vai para a aba da ferramenta, para você aprender onde ela fica. Entende também nomes
  de outros programas (fillet, mate, drive…).
- **Desenho com vistas prontas:**
  - **Paleta de vistas** (aba Desenho): escolha a peça e clique em Frontal, Superior, Lateral esquerda ou
    direita, Inferior, Posterior ou Isométrica. A vista entra na folha na hora, alinhada no 1º diedro, sem
    duplicar. A escala normalizada e a posição das vistas se ajustam para tudo caber, e a legenda acompanha.
    Sem folha aberta, a paleta cria uma folha ABNT A3.
  - **Cotas gerais:** um clique põe o comprimento, a altura e a profundidade totais da peça.
  - **Folha ABNT com arranjos prontos:** frontal, superior, lateral e isométrica; frontal, lateral e
    isométrica; frontal e superior; frontal e isométrica; ou só a isométrica.
- **Vasos: pés de chapa, como nos reservatórios de compressor.** Quatro pés de chapa dobrada (4,75 mm) em
  perfil U, um em cada canto, abertos para as pontas do vaso, recortados no costado e com sapata e furo de
  fixação. Entram também no teste de pressão por elementos finitos, com o apoio nas sapatas.

### Mudanças

- **Painel lateral:** com a aba Árvore fechada, o painel que sobra continua com o nome em português.
- **Sem a aba BIM:** o Prumo passa a focar na engenharia mecânica. A bancada BIM (arquitetura) sai de vista;
  quem precisar pode religá-la em Preferências → Geral → Bancadas.

### Correções

- **Vasos: todo suporte oferecido aparece no modelo.** No vaso deitado, escolher saia ou pernas não construía
  nada. Agora a lista de suportes só mostra o que serve para a posição do vaso (deitado: selas, pés de chapa ou
  pernas; em pé: saia ou pernas), e o vaso deitado ganhou pernas: quatro tubos sob o costado, nas posições das selas.

## 1.0.2 — 28/10/2026

### Novidades

- **Esboço 3D: comprimento durante o desenho.** O comprimento do trecho aparece junto ao cursor enquanto se
  desenha. Para uma medida exata, é só digitar o número (com o cursor na vista) e teclar Enter: o ponto vai
  na direção do cursor (exatamente no eixo, se o cursor estiver alinhado com X, Y ou Z) e o trecho já fica
  cotado. Vírgula decimal e Backspace funcionam; Esc apaga o número digitado. O painel também mostra o
  comprimento ao vivo e aceita o valor digitado.

### Ajustes

- **Testes automáticos (aba Prumo):** a dica dizia "cerca de 1 minuto", mas a bateria completa leva perto de
  uma hora. Agora o botão avisa antes, pede para fechar os projetos abertos e mostra onde fica o relatório.

## 1.0.1 — 28/10/2026

### Correções

- **Atualização automática que parava em "Não foi possível apagar a pasta":** o instalador aberto pelo
  Prumo herdava a pasta de trabalho do programa (dentro da pasta de instalação), e o Windows não deixa
  renomear uma pasta que algum programa usa como pasta de trabalho, nem mostra esse programa na lista. Agora
  o instalador abre a partir da pasta do download e, por garantia, sai sozinho da pasta antiga antes de
  trocá-la. Também tenta de novo por alguns segundos (antivírus) antes de perguntar.
- **Nome da versão no instalador:** mostrava "Prumo 3D 1.1.4" (a versão do FreeCAD de base); agora mostra a
  versão do Prumo.

## 1.0.0 — 28/10/2026

Primeira versão final do Prumo 3D, depois das versões de teste (0.1 a 0.9.12): faixa de ferramentas
só com abas, comandos em cartões no painel lateral, esboço com pontos-ímã, estruturas metálicas calculadas
pela NBR 8800:2024 e NBR 8681:2025, detalhe de ligação por elementos finitos, vasos de pressão (ASME VIII-1),
tubulação de PVC Tigre, chapa metálica, folhas ABNT, BIM e superfícies, tudo em português e com atualização
automática.

### Ajustes

- **Menus em português:** os menus Superfície e Malha (da Simulação) ainda apareciam em inglês.
- **Página do projeto:** imagens novas de todas as abas (tela inicial, esboço, peça, desenho, estruturas,
  simulação, tubulação, vasos, chapa, BIM e superfícies).
- **Tela inicial em tela baixa:** conferida em 1366 × 680 px; a janela não passa da tela e a tela inicial rola.

## 0.9.12 beta — 27/10/2026

### Novidades

- **Tudo em abas, sem o menu de bancadas:** o botão de trocar bancada ao lado da marca saiu. Cada área tem a sua
  aba; entraram duas novas:
  - **BIM:** projeto (terreno, edifício, nível), paredes, lajes, pilares, vigas, portas, janelas, escadas,
    telhados, cotas, cortes, folhas e quantitativos/IFC.
  - **Superfícies:** preencher por arestas ou seções, estender face, curva de concordância, curva sobre malha e
    sólido a partir de faces (loft, varredura e regrada ficam na aba Peça).
- **Esboço › Inserir** (o que antes só a bancada Draft fazia):
  - **Texto:** escreve um texto como linhas e curvas do esboço, pronto para extrudar, cortar ou gravar. Fonte
    Poppins ou qualquer fonte instalada, altura da letra maiúscula em mm, espaço entre letras, posição e giro.
  - **Importar DXF:** traz linhas, arcos, círculos e curvas de um DXF para o esboço, com a unidade do desenho
    (mm, cm, m, pol), escala e opção de levar para a origem. Pontas que se tocam já saem ligadas.
  - **Matriz em caminho:** repete uma peça ao longo de um esboço, arame, hélice ou arestas, com quantidade,
    orientação e recuos no início e no fim.
  - Texto e DXF vão para o esboço em edição (sem tirar o esboço do lugar), para o esboço selecionado ou para um
    esboço novo.
- **Aba Peça › Sólidos completo:** primitivas soltas (cubo, cilindro, esfera, cone, toro, tubo), extrudar, girar,
  loft, varredura, superfície regrada, face de esboços, arredondar, chanfrar, casca, espelhar e booleanas.
- **Bancadas fora de vista:** Desenho 2D (Draft), Malhas, Usinagem (CAM) e Engenharia reversa não aparecem mais.
  Quem usa alguma delas religa nas Preferências (página das bancadas) e abre pelo menu Vista › Bancada; ela
  ganha uma aba enquanto estiver em uso.

### Correções

- **Abas da faixa com o nome inteiro em tela de notebook:** em vez das setas de rolagem, a linha das abas se
  compacta por etapas (menos espaço entre as abas, marca só com o ícone, letra um pouco menor e, por último,
  Desfazer/Refazer/Medir saem do acesso rápido). Conferido com 1100, 1280, 1366, 1440 e 1600 px de largura,
  em todas as abas. As setas ficam só para janela pequena demais.
- **Aba Peça:** o Sólido (primitivas de adicionar material) passa para o grupo Sólidos, com ícone grande; o
  Subtrair fica com ícone pequeno, como Unir e Interseção.
- **Painel lateral voltava para a aba errada ao fechar um comando:** se a aba era trocada logo depois de fechar
  outro comando, a troca não era lembrada. Agora vale sempre a última aba olhada.
- **Aba BIM sem janela de boas-vindas** (em inglês, com predefinições do FreeCAD) na primeira vez, e sem
  fechamento do programa ao fechar um documento depois de usar a aba BIM.

## 0.9.11 beta — 27/10/2026

### Correções

- **Instalador não quebra mais a instalação anterior:** ele apagava a pasta antiga arquivo por arquivo; se algum
  arquivo estivesse preso (antivírus, Explorer, outro programa rodando de dentro da pasta), parava no meio e
  deixava o Prumo inutilizável. Agora: espera também qualquer programa rodando de dentro da pasta (e diz qual,
  se não fechar); renomeia a pasta antiga de uma vez (se algo estiver preso, nada é apagado e a versão
  instalada continua funcionando); instala a nova numa pasta limpa e só então apaga a antiga (o que estiver
  preso sai na próxima reinicialização). Se a instalação for interrompida, a versão anterior volta ao lugar.

## 0.9.10 beta — 27/10/2026

### Correções

- **Esboço preso no modo construção:** o "Alternar construção" (no menu da Linha) é global no FreeCAD e ficava
  ligado para os esboços seguintes; o retângulo saía como construção e a extrusão falhava sem explicação.
  Agora todo esboço abre no modo normal. Clicar duas vezes seguidas em "Linha de construção" também
  deixava o modo preso; corrigido.
- **Tubulação, tubos cruzando pelo meio:** dois trechos que se cruzam no mesmo plano, sem que nenhum termine ali,
  agora recebem a cruzeta (antes um atravessava o outro sem peça e sem aviso).
- **Tubulação, tubos encostados sem conexão:** quando dois tubos se encostam ou se atravessam sem nó em comum
  (por exemplo, cruzando a poucos milímetros de altura), aparece o aviso com os trechos e a sobreposição.
- **Estruturas, diagonal chegando no meio de outra barra (treliça em K/N):** a diagonal entrava dentro da barra
  principal (material sobreposto). Agora encosta na face dela, e as diagonais que chegam no mesmo ponto se
  recortam entre si.
- **Estruturas, linhas que se cruzam no meio:** as barras passavam uma por dentro da outra sem aviso; agora a
  estrutura avisa (na janela e no objeto) para dividir uma das linhas no cruzamento.
- **Aviso de curva sem peça mais claro:** "a linha muda de direção em 60°" no lugar do ângulo entre os trechos.

### Testes

- **Roteiros de uso automáticos:** 17 traçados comuns de tubulação (T pela ponta e pelo meio, cruzeta, joelhos,
  reduções, esgoto, Aquatherm, cruzamentos) 5 roteiros de esboço feitos com o mouse (linha entre quadrantes,
  quadrante a ponto livre, ponto médio, interseção, polilinha), uma peça feita do zero pela faixa
  (extrusão, cavidade, furo, arredondamento, chanfro, padrão, revolução) e 10 esqueletos comuns de estrutura
  (sem material sobreposto entre barras) e uma chapa dobrada do zero (base, aba, planificação, DXF) passam a
  rodar em toda versão, no mesmo programa que vai para a página de versões.

## 0.9.9 beta — 26/10/2026

### Correções

- **Tubulação, ramal no meio do trecho sem tê:** quando o ramal terminava no meio da linha principal (desenhada
  como um trecho só), o tubo do ramal só encostava no principal, sem conexão. Agora a linha principal é
  dividida nesse ponto e entra o tê (ou a junção, no esgoto); diâmetros, registros, torneiras e caixas
  continuam com a numeração dos trechos do traçado.

## 0.9.8 beta — 26/10/2026

### Correções

- **Esboço, linha ligada a pontos-ímã ficava solta:** uma linha entre dois quadrantes (por exemplo, a de baixo
  de dois círculos) passa quase tangente a um deles; o esboço sugeria também essa tangência, que sobrava
  junto com os pontos fixos, e o FreeCAD descartava todas as restrições automáticas da linha. Agora ponto
  capturado por ímã (quadrante, ponto médio, interseção) não ganha tangência sugerida, e a linha sai
  totalmente definida quando os círculos estão.
- **Notebook com escala de 150–200 %:** a janela pedia no mínimo ~1500 px de largura (a linha das abas da
  faixa não encolhia, e cresceu com a aba Tubulação), mais que a tela útil, e o Windows avisava "Unable to
  set geometry". Agora as abas rolam com setas quando falta espaço e a janela cabe em telas a partir de
  ~600 px de largura.

## 0.9.7 beta — 26/10/2026

### Correções

- **Atualização automática quebrava a instalação:** da 0.9.5 para a 0.9.6 o instalador abriu (pelo pedido
  de permissão do Windows), mas o Prumo ainda estava terminando de fechar. O instalador começou a apagar a
  pasta antiga, encontrou arquivos presos, parou no meio e deixou a instalação incompleta. Agora o
  instalador espera o Prumo sair de vez (até 60 s) antes de mexer na pasta e, se algum arquivo ainda
  estiver preso, oferece "Tentar de novo" em vez de abortar.

## 0.9.6 beta — 25/10/2026

### Correções

- **Tubulação, medidas conferidas:** a junção a 45° de esgoto estava com o ramal curto (a cota c vai até o
  fundo da bolsa, não até a face: confirmado porque, nas junções de diâmetros iguais, montante = c + bolsa
  em todas as bitolas). Joelho 45° e tê de esgoto conferidos pela geometria; caixas conferidas com a ficha
  atual da Tigre. Joelho 45° Aquatherm com as cotas do site da Tigre (o catálogo de 2011 repetia o 90°),
  conectores Aquatherm com o comprimento real, e três buchas soldáveis com erro de impressão corrigidas
  (110 × 85, 50 × 25 e 75 × 50). Normas dos tubos conferidas na ABNT: NBR 5688:2018 (esgoto) e
  NBR 15884-1/-2 (CPVC), em vigor. Seguem avisando só o joelho 45° e a junção de DN 200 de esgoto, o joelho
  45° Aquatherm de 35, 42 e 54 e o conector Aquatherm 28 × 1".
- **Junções desenhadas sempre válidas:** com caimento, algumas junções saíam com sólido inválido.

### Melhorias

- **Peças com mais volume na vista 3D:** iluminação nova, com luz principal de cima, preenchimento da
  esquerda e uma luz lateral mais fraca da direita, presas à câmera. Cada face fica com um tom e o
  acabamento padrão das peças novas passou a acetinado, com brilho visível em furos, tubos e
  arredondamentos. Peças já existentes mantêm o acabamento salvo no arquivo.

## 0.9.5 beta — 25/10/2026

### Correções

- **Atualização automática (de novo):** da 0.9.3 para a 0.9.4 o Prumo baixou o instalador e fechou, mas o
  instalador não abriu (o processo que esperava o Prumo fechar não chegou a abri-lo). Agora o instalador é
  aberto pelo próprio Windows (com o pedido de permissão) logo depois que você aceita fechar o Prumo; o
  caminho antigo fica só como reserva. Cada passo fica anotado em `atualizacao.log`, na pasta temporária
  `Prumo3D-atualizacao`, para achar o motivo se algo falhar.
- **Mensagens de erro das operações em português:** o FreeCAD mostrava o erro cru em inglês (ex.: "Failed to
  make thick solid" na casca). 121 mensagens de Peça, Sólidos e esboço agora aparecem em português,
  algumas com a dica do que tentar (casca: espessura menor, outra junção ou outras faces).

## 0.9.4 beta — 25/10/2026

### Melhorias

- **Aba Tubulação:** a ferramenta saiu da aba Estruturas e ganhou aba própria, com Traçado (Esboço 3D e
  esboço plano), Tubos e conexões, e Conferir (verificar interferência, medir, lista de materiais).
- **Tubulação: trechos escolhidos na vista**, como na estrutura soldada: clique nas linhas do traçado
  (Ctrl para várias) e aplique o diâmetro a todas de uma vez; "Escolher todos", "Mesmo diâmetro" e a
  tabela marcam os trechos na vista, e o que se escolhe na vista aparece marcado na tabela.
- **Torneiras na tubulação:** na ponta solta (luva com bucha de latão seguindo o tubo, ou joelho com bucha
  saindo para cima, para baixo ou para o lado) ou no ponto clicado do trecho (tê com bucha de latão, que
  corta o tubo em dois e desconta as bolsas). A torneira aparece em volume simplificado e entra na lista
  de materiais. Medidas das peças com bucha: catálogo Tigre de água fria (2008).
- **Linha de esgoto série normal (Tigre, DN 40 a 200)** na Tubulação: tubos, joelhos 90° e 45°, tê, luva,
  redução excêntrica e cap do catálogo de esgoto (2008). Caimento automático nos trechos horizontais, no
  sentido em que foram desenhados: 2 % até DN 75 e 1 % a partir de DN 100 (ABNT NBR 8160:1999, 4.2.3.2);
  aviso acima de 5 % (4.2.5.2) e em curva na horizontal com joelho 90° (4.2.3.3). Joelho 45° e tê de esgoto
  saem com aviso "a conferir" (rótulos trocados na tabela do catálogo).
- **Linha de água quente CPVC Aquatherm (Tigre, 15 a 114 mm)**: tubos em barras de 3 m, joelhos, tê, luva e
  cap do catálogo técnico Aquatherm (mai/2011); torneira na ponta com conector ou joelho de transição. O
  joelho 45° sai "a conferir" (o catálogo repete a tabela do joelho 90°).
- **Junção a 45° no esgoto:** ramal chegando a 45° pelo lado de montante vira junção simples (DN 40 a 200,
  inclusive 75 × 50, 100 × 50, 100 × 75 e 150 × 100), com o tubo cortado pelas medidas da junção. Centro até
  a face tirado do desenho do catálogo, por isso "a conferir".
- **Caixas de esgoto:** caixa sifonada (100 × 100 × 50, 150 × 150 × 50, 150 × 185 × 75), caixa de inspeção e
  caixa de gordura no nó de uma ponta do traçado; os trechos que chegam ali param na parede da caixa, e o
  Prumo avisa quando o diâmetro do tubo passa da saída ou das entradas da caixa. Medidas do catálogo de
  esgoto (2008); inspeção e gordura "a conferir" (letras sem legenda na tabela).

### Correções

- Clicar numa aba logo ao abrir o programa não volta mais sozinho para a aba Início.

## 0.9.3 beta — 25/10/2026

### Melhorias

- **Verificar geometria:** resumo em cartões acima da lista do FreeCAD — geometria válida ou com defeito,
  sólidos, cascas, faces, arestas, vértices, volume e área.
- **Peso próprio com painel:** criar pelo botão da faixa (ou editar com duplo clique) abre cartões com a
  direção da gravidade (−Z, +Z, ±X, ±Y) e a aceleração em m/s². Cancelar na criação desfaz.
- **Abre na aba Início:** sem documento aberto, a faixa começa na aba Início (antes caía em Peça).
- **Relatório e console Python fechados por padrão**, em qualquer tela. Quem programa liga em
  Preferências → "Para quem programa".

### Correções

- **Atualização automática:** depois de baixar, o Prumo fechava e o instalador não abria (o instalador pede
  permissão de administrador e era aberto por um caminho que não mostra esse pedido). Agora um processo
  à parte espera o Prumo fechar e abre o instalador com o pedido de permissão do Windows. Desistir de
  fechar (na pergunta de salvar) não abre nada.
- O último trecho que lia os quadros do jeito antigo (rolagem de janelas grandes) foi trocado, como o do
  botão OK na 0.9.2.

### Testes

- Verificar geometria de uma caixa (6 faces, 12 arestas, 1.000 mm³); peso próprio criado pela faixa, em −Y
  e 9,81 m/s², e reaberto para editar.
- Atualização: comando que espera o Prumo fechar e abre o instalador pelo Windows; desistir de fechar não
  abre nada. Abertura na aba Início; Relatório e console fechados e ligados pela Preferência.

## 0.9.2 beta — 24/10/2026

### Melhorias

- **Preferências do Prumo:** botão "Preferências" (abas Início e Prumo) abre uma janela em cartões com o
  que importa: tema claro/escuro, tela inicial, faixa contextual, painel lateral (único, propriedades e
  comandos em cartões, abas compactas), esboço (retirar relações automáticas que não cabem, referências
  automáticas, enquadrar ao sair), unidades (sistema em português e casas decimais) e atualizações. Cada
  opção grava na hora; as preferências completas do FreeCAD continuam a um clique.
- **Multitransformação em cartões:** operações a repetir e a lista de transformações em ordem, com
  "+ Espelhar", "+ Padrão linear", "+ Padrão circular", "+ Escala", Editar, Excluir, Subir e Descer (antes
  só pelo menu do botão direito). Ao editar uma transformação, o quadro dela aparece com "Concluir esta
  transformação".
- **Varredura: orientação e seções em cartões.** Os quadros "Orientação da seção" (padrão, fixa, Frenet,
  auxiliar, binormal) e "Transformação da seção" (constante, várias seções, …) ganharam cartões próprios,
  como o resto do painel.
- **Sólidos em cartões:** deslocamento 3D/2D e espessura (faces abertas, distância, modo e cantos),
  transição (loft) e varredura (perfis em ordem com Usar/↑/↓/✕, caminho escolhido na vista, sólido e
  Frenet).
- **Desenho:** texto formatado (texto, editor completo, largura e moldura) em cartões; a hachura ganhou a
  escolha do padrão pelo nome (Madeira, Concreto, Aço…), outro arquivo SVG e a cor.
- **Simulação:** deslocamento imposto (por eixo: livre ou com valor; 0 trava), mola (rigidez normal e
  tangencial em N/mm) e o quadro "Onde vale" (material, espessura de casca, seção de viga…) em cartões,
  com Adicionar na vista e ✕ para tirar.
- **Montagem → Inserir componente em cartões:** procurar pelo nome, peças de cada documento com
  "Inserir" (o botão conta quantas já entraram), abrir outro arquivo e as opções.

### Correções

- Às vezes o Prumo deixava de "enxergar" o botão OK (ou outro botão) do painel de tarefa logo depois de
  fechar outra tarefa: um resto de leitura antiga do layout era confundido com o botão novo no mesmo
  lugar da memória. A leitura dos quadros do painel, da faixa e do guia foi trocada por uma que não deixa
  esse resto.

### Testes

- Preferências: abre pelo comando, grava na hora, unidades com nomes em português.
- Multitransformação: adicionar um padrão linear pelos cartões, concluir e gravar.
- Varredura: orientação Frenet e várias seções pelos cartões.
- Leitura dos quadros de um layout em ordem, sem guardar itens do layout.
- Sólidos: deslocamento com canto vivo, espessura com face aberta, transição entre dois círculos e
  varredura com caminho escolhido (volume conferido: π·10²·40 mm³).
- Desenho: hachura com padrão Madeira e cor vermelha; texto formatado com moldura.
- Simulação: deslocamento imposto em Z, mola em N/mm, Onde vale do material (sólido inteiro).
- Montagem: inserir peça filtrando pelo nome; o link entra na montagem.

## 0.9.1 beta — 24/10/2026

### Correções

- **Linha ligando dois círculos ainda quebrava o esboço** (relatado na 0.8.1, com círculos de Ø50 e
  Ø30): ao desenhar, o FreeCAD punha tangente e duas "Vertical" (alinhamento com os centros), que não
  cabiam juntas; no primeiro recálculo, ele jogava os círculos a bilhões de mm, e o Prumo retirava a
  relação a partir desse desenho já estragado. Agora o Prumo guarda o desenho do instante em que as
  relações entram, testa cada opção de retirada sem mexer no esboço e fica com a que menos move o que já
  estava desenhado, preferindo tirar alinhamentos do cursor e manter a tangente. A retirada entra no
  desfazer (Ctrl+Z).

### Testes

- O caso relatado (Ø50, Ø30, tangente + duas verticais) virou teste: os círculos não podem sair do
  lugar e a tangente tem de ficar.

## 0.9.0 beta — 24/10/2026

### Melhorias

- **Desenho em cartões, parte 2:**
  - **Vista em corte:** letra do corte, para onde ele olha (← Esquerda, → Direita, ↑ Cima, ↓ Baixo), por
    onde passa o plano (X, Y, Z), escala e atualização.
  - **Vista de detalhe:** letra, "Arrastar o círculo na folha", centro (X, Y), raio e escala.
  - **Editar cota:** casas decimais, cota de referência (entre parênteses), teoricamente exata, texto
    livre, tolerância (simétrica ou superior/inferior), tamanho do texto, inverter as setas e estilo.
  - **Editar balão:** texto (nº da peça), forma, tamanho, ponta e linha de chamada.
  - **Hachura:** escala, rotação e deslocamento do padrão.
- **Fixação em cartões:** o quadro "Fixação" do FreeCAD (planos, linhas e pontos auxiliares, primitivas e
  Editar fixação) virou cartões: onde a peça se prende (só as referências usadas e a próxima livre),
  o modo numa lista e o deslocamento (X, Y, Z e rotações), com "Inverter o lado".
- **Sólidos em cartões:** Extrusão (direção, a favor/oposto/simétrica, ângulo de saída, sólido), Revolução
  (eixo X/Y/Z ou aresta, centro, ângulo), Espelhar (plano XY/XZ/YZ ou face, ponto), Escala (igual nos 3
  eixos ou um por eixo) e Arredondar/Chanfrar arestas (forma, Todas/Nenhuma, constante ou variável). Em
  todos, as formas da operação aparecem como interruptores.
- **Montagem → juntas em cartões:** os 13 tipos numa grade com nomes em português (Fixa, Rotação,
  Cilíndrica, Deslizante, Esférica, Distância…), o que foi escolhido na vista, só as medidas do tipo
  escolhido, "Inverter o sentido", os limites (distância e ângulo mínimo/máximo) e como as outras peças
  aparecem enquanto escolhe. A aba do comando se chama "Junta".
- **Simulação em cartões:** Material (o escolhido e densidade, E e ν na unidade usual), Fixação (faces
  presas), Força (valor em N, direção, inverter), Pressão (valor em MPa, inverter) e Gerar malha (tipo,
  tamanhos e ordem). O quadro "Onde vale" do FEM, que estava em inglês, foi traduzido.

### Testes

- Corte (letra e direção), detalhe (raio e letra), cota (casas e referência), balão (texto e forma) e
  hachura (escala): cada painel abre em cartões e o OK grava o que foi mudado.
- Fixação: deslocamento e modo escolhidos nos cartões ficam no plano auxiliar; nas primitivas aparecem
  os dois painéis (medidas e fixação).
- Sólidos: extrusão de 25 mm, revolução de 90°, espelho no plano XZ, escala 2× e arredondar/chanfrar as
  12 arestas de uma caixa, pelos cartões.
- Junta da montagem: trocar o tipo na grade muda a junta e as medidas mostradas.
- Simulação: força de 250 N e pressão de 0,5 MPa pelos cartões ficam gravadas certo (o FreeCAD guarda
  internamente em mN e kPa).

## 0.8.1 beta — 24/10/2026

### Melhorias

- **Desenho → Vista e Grupo de projeção em cartões:** as vistas são escolhidas numa grade que já segue o
  1º diedro (a vista de baixo fica em cima, como na folha), com a direção da frontal dita em palavras
  ("de frente", "de cima"), a escala (da folha, automática ou escolhida, ex.: 1:5) e o arranjo do grupo.
- **Atualização com janela de progresso:** barra, MB baixados, velocidade e tempo que falta, com
  Cancelar. No fim, a mesma janela diz o próximo passo ("Fechar o Prumo e instalar" ou onde ficou o
  arquivo) ou o erro, com "Tentar de novo". "Verificar atualizações" mostra "Procurando…" enquanto consulta.

### Correções

- **"Atualizar agora" não fazia nada** quando a atualização era procurada por Ajuda → Sobre: a janela do
  aviso abria, mas o botão não respondia. Na verificação automática ao abrir já funcionava.

### Testes

- Painel de vistas (grupo com vista inferior no 1º diedro, vista avulsa com escala 1:5) e janela de
  atualização (progresso, próximo passo, erro, e o clique que antes não respondia).

## 0.8.0 beta — 24/10/2026

### Melhorias

- **Mais comandos em cartões:** Ângulo de saída, Casca, Hélice (aditiva e subtrativa), Loft e Varredura
  (aditivos e subtrativos) ganharam o mesmo painel de cartões da Extrusão e do Furo: o que foi escolhido
  na vista, as medidas, interruptores e botões no lugar das listas. O formulário completo do FreeCAD
  continua a um clique.
- **Primitivas e Booleana em cartões:** cubo, cilindro, esfera, cone, elipsoide, toro, prisma e cunha
  (aditivos e subtrativos) mostram as medidas em cartão; a Booleana mostra os corpos e Unir / Cortar /
  Interseção.
- Títulos de quadros que ainda apareciam em inglês na Hélice, no Loft e na Varredura foram traduzidos.
- **Cotas do esboço em cinza escuro:** o azul das cotas se confundia com as linhas do desenho.

### Correções

- **Linha ligando dois círculos quebrava o esboço:** ao desenhar, o FreeCAD põe relações automáticas
  (tangente, vertical, horizontal) que às vezes não cabem juntas. Agora o Prumo retira na hora as
  automáticas que não cabem e avisa quais foram; o esboço continua resolvido. Relações postas à mão
  nunca saem sozinhas: o painel avisa o conflito e oferece apagar a mais recente.
- **Assistentes de estruturas e de simulação:** quando o resumo de uma etapa ocupava duas linhas (ex.:
  "Resultados"), o texto ficava cortado por cima do título.

### Testes

- Novo teste confere que nenhum painel do Prumo nem os assistentes têm texto cortado ou sobreposto.
- Testes dos novos painéis: cada um abre em cartões e o OK grava o que foi mudado.

## 0.7.1 beta — 24/10/2026

### Correções

- **Esboço que não fecha** (ex.: dois círculos e uma linha ligando os dois, com as restrições automáticas
  de tangência e horizontal): o painel do esboço avisava "Totalmente definido". Agora mostra em vermelho
  "O esboço não fecha" ou "Restrições em conflito: Tangente · Linha 3 / Círculo 2…", põe as restrições
  com problema no topo da lista (⚠) e oferece "Apagar a restrição mais recente do conflito".
- **Esboço 3D:** depois de fechar o painel sem OK/Cancelar, qualquer clique de seleção dava erro.
- **Desenho → Preencher campos da folha:** o botão dava erro interno (`false` em vez de `False`) e
  não mostrava quando estava disponível.

### Testes

- Testes de ponta a ponta: todas as ferramentas da faixa (cerca de 270) abrem e fecham com uma peça
  pronta, as ferramentas do esboço ligam e cancelam, e o conflito de restrições aparece e se resolve.

## 0.7.0 beta — 23/10/2026

### Novo

- **Extrusão e Cavidade com painel no padrão Prumo:** ao criar ou editar, a aba do comando mostra os
  cartões Lados (Um lado, Dois lados, Simétrica), Direção 1 e 2 (até onde vai em botões com ícone,
  medida, afastamento, ângulo de saída, inverter), Perfil e Acabamento, no lugar do formulário do
  FreeCAD. Quando o modo pede escolher na vista (Até a face, Até a peça), o quadro do FreeCAD aparece
  embaixo para a escolha; "Formulário completo do FreeCAD" mostra tudo quando quiser.
- **Furo com painel no padrão Prumo:** cartões Furo (padrão de rosca, tamanho, diâmetro), Tipo (Passante,
  Para rosca, Modelada, com a folga), Profundidade (Medida ou Através, ponta cônica), Cabeça (rebaixo,
  escareado… com diâmetro e profundidade) e Acabamento.
- **Revolução e Ranhura** (eixo, até onde gira, ângulos, simétrico, inverter) e **Arredondar e Chanfro**
  (arestas escolhidas com "Escolher arestas na vista", todas as arestas, raio ou o tipo de chanfro com
  distâncias e ângulo) também com painel em cartões.
- **Padrão linear, Padrão circular e Espelhar** com painel em cartões: operações a repetir (Adicionar,
  Tirar), direção ou eixo, comprimento/ângulo total ou distância entre cópias, quantidade, inverter e a
  segunda direção ligada por chave; no Espelhar, o plano de espelho.

### Ajustes

- **Mais telas no padrão novo:** Estrutura soldada, Cantos da estrutura, Propriedades de massa, guia
  "Vem do SolidWorks", Esboço 3D e Tubulação agora em cartões, como o resto do sistema.
- **Assistentes, tutorial, guia "Vem do SolidWorks" e histórico do corpo viram abas do painel lateral**
  enquanto estão abertos (antes abriam num painel separado à direita), com um × no topo para fechar.
- **Cotas na tela** (duplo clique na operação) e **aviso de conferência do esboço** no padrão novo:
  cartão de cantos arredondados, campos com unidade sem setas, aviso em amarelo.
- **Avisos dos painéis voltaram a ter o fundo amarelo** (o estilo da letra apagava o fundo da caixa de
  instrução).

## 0.6.0 beta — 23/10/2026

### Novo

- **Painel lateral único, com as abas no alto:** **Árvore**, **Propriedades** e, só enquanto um comando
  está aberto, a aba dele (ex.: "Esboço002", "Extrusão"). Ao concluir ou cancelar, a aba do comando some
  e o painel volta para a aba em que você estava. Acabaram os painéis Modelo, Tarefas e Dados empilhados
  com título repetido em cima de cada um. (Para voltar ao arranjo do FreeCAD: preferência
  `PainelLateralUnico` em Mod/Prumo3D, vale na próxima abertura.)
- **Propriedades em cartões:** a peça ou operação selecionada aparece com o nome editável, o botão
  **Editar** e cartões com o que importa (na Extrusão: Lados, Direção 1, Direção 2, Perfil, Acabamento),
  com chaves liga/desliga, botões com ícone (Medida, Até a face, Até o fim…) e campos com a unidade.
  Cada mudança entra no desfazer. A tabela completa do FreeCAD continua em **Avançado**.
- **Aba Aparência** (no lugar da antiga aba Vista): cor em amostras (ou outra cor), transparência,
  modo de exibição (Arestas, Sólido, Arame, Pontos), espessura da linha e se dá para selecionar na
  tela, para tudo o que estiver selecionado.
- **Aba do esboço no estilo do SolidWorks:** a situação numa frase ("Totalmente definido", "Faltam 2
  medidas para ficar definido", "Restrições em conflito"); **Relações** com o que está selecionado e os
  botões Horizontal, Vertical, Paralela, Perpendicular, Igual, Colinear, Tangente, Coincidente, Fixar,
  Simétrica e Cotar (só ficam ativos os que servem para a seleção); **Neste esboço** com as relações e
  cotas existentes e × para apagar; **Auxiliares**. As listas do FreeCAD continuam em "Lista completa".
- **Abas compactas:** com o painel estreito, só a aba aberta mostra o nome; as outras ficam com o ícone
  (o nome aparece ao parar o mouse em cima).
- **Atualização pelo próprio Prumo, sem obrigação:** em **Ajuda → Sobre**, o botão **Verificar
  atualizações** e a chave **Verificar ao abrir** (no máximo uma vez por dia). Com versão nova, aparece
  um aviso com "Atualizar agora", "Agora não" e "Pular esta versão". Ao atualizar no Windows, o Prumo
  baixa o instalador, confere o SHA-256 publicado, fecha (perguntando se quer salvar) e abre o
  instalador; no Linux, baixa o AppImage novo na mesma pasta. A consulta só lê a lista de versões
  públicas; nenhum dado é enviado. Primeira versão com o aviso: vale a partir da próxima atualização.

### Ajustes

- **Cotas do esboço em azul**, no tom do sistema (antes vermelhas); o vermelho fica só para erro.
- **Barra de cima da aba Esboço mais limpa:** o botão Restrição e o grupo Auxiliares foram para o painel
  lateral; Validar, Reorientar, Mesclar e Espelhar esboço ficaram num menu "Mais"; saiu o "Linha ↔
  construção" repetido (continua no menu do botão Linha).
- **Mesmo visual em todo o sistema:** caixas de marcar viraram chaves liga/desliga (nas listas e
  tabelas continua a caixa); os quadros dos comandos do FreeCAD e as seções dos painéis Prumo viraram
  cartões brancos de cantos arredondados; botões de opção marcados em azul claro; avisos sem a barra
  lateral. Nos painéis Prumo saiu o quadro com título repetido (a aba já diz o nome do comando).
- **Tela inicial com a área Ajuda**, logo abaixo de Novo projeto: tutorial da primeira peça, tutorial da
  estrutura soldada e "Vem do SolidWorks ou do ZW3D?", em cartões com ícone como os demais.
- **Painéis laterais não abrem mais junto com a tela inicial** quando o FreeCAD restaura o arranjo
  gravado logo depois de abrir.
- **Aviso de boa prática do esboço numa linha**, com "Por quê?" para ler o resto e × para dispensar.

## 0.5.0 beta — 23/10/2026

### Novo

- **Esboço 3D com restrições, cotas e linhas de construção**, no jeito do SolidWorks:
  - linha desenhada ao longo de X, Y ou Z ganha a restrição do eixo sozinha (aparece "X", "Y" ou "Z" ao
    lado dela); o ramal que começa num ponto do esboço fica preso nele;
  - na lista "Linhas e restrições" (ou clicando na linha na vista): **Cotar** o comprimento, **Ao longo de
    X/Y/Z**, **Paralelas**, **Perpendiculares**, **Iguais** e **Construção**; o esboço se ajusta na hora e
    avisa quando as restrições entram em conflito;
  - **linhas de construção** tracejadas: servem de referência para restrições e cotas, mas não entram na
    forma (a estrutura soldada e a tubulação não usam);
  - durante a edição, o resto do modelo fica transparente e os eixos X, Y e Z aparecem no ponto de partida.
- **Esboço 3D no Novo esboço:** fica no menu do botão Esboço da aba Peça (e no Novo esboço da aba
  Esboço); saiu da aba Estruturas.

### Ajustes

- **Modelo e Tarefas em abas no mesmo lugar**, e não mais lado a lado: em notebook os dois juntos
  pediam mais largura que a tela (o aviso "Unable to set geometry"). A aba Tarefas vem para a frente
  quando um comando abre e a Modelo volta quando ele fecha.
- **Na abertura, só a tela inicial:** Modelo e Tarefas começam fechados, também na primeira vez depois de
  instalar; aparecem ao abrir ou criar um arquivo.
- **Instalador do Windows com a marca do Prumo** (imagem lateral, cabeçalho e ícone), sem o logo do
  FreeCAD.

## 0.4.0 beta — 23/10/2026

### Novo

- **Referências automáticas no esboço:** ao abrir um esboço apoiado numa face, todas as arestas dela já
  entram como geometria externa; num plano da origem, entram as arestas do sólido que estão no plano.
  Ao concluir, as referências que não foram usadas saem sozinhas. As feitas à mão com Geometria externa
  ficam. Liga e desliga em Esboço → Referências automáticas.
- **Pressão do vaso em MPa, kgf/cm² ou psi:** escolha a unidade ao lado do campo; o painel, a memória
  de cálculo e o desenho mostram a pressão nessa unidade, com a equivalência em MPa (o cálculo continua
  em MPa).

- **Linha de construção:** no menu do botão Linha (aba Esboço) há a **Linha de construção**, uma linha só de
  referência que guia o desenho e não entra no perfil. Para transformar linhas já desenhadas, selecione e
  use **Linha ↔ construção** (no mesmo menu ou no grupo Desenhar).

### Ajustes

- **Peça e Sólidos juntas:** a aba Sólidos saiu; o que ela tinha sem igual na Peça (subtrair, unir,
  interseção, juntar/dividir formas, seção, projeção, escala, offset) virou o grupo **Sólidos** da aba
  Peça. As "Primitivas" de adicionar e remover material agora se chamam **Sólido** (caixa, cilindro,
  esfera… que se funde à peça ou é tirado dela).
- **Restrições num botão só:** coincidente, horizontal/vertical, paralela, perpendicular, tangente, igual,
  simétrica, bloquear e ativar/desativar viraram um botão grande com menu, como o da Cota.
- **Tela de abertura com a versão certa:** o selo da tela de abertura, o título da janela e o Sobre agora
  mostram a versão do pacote (antes ficavam em 0.1).
- **Régua de histórico** saiu da faixa da aba Peça: liga e desliga no menu Vista.
- **Régua de histórico na árvore do modelo:** a régua amarela agora fica na própria árvore, logo abaixo
  da última operação do corpo, e se arrasta para cima ou para baixo. Duplo clique volta ao modelo
  completo; o botão Régua de histórico liga e desliga.
- **Padrão linear e padrão circular** do esboço ganharam um grupo próprio, com botões grandes, na aba
  Esboço durante a edição (antes ficavam pequenos como "Mover / matriz" e "Rotacionar").
- **Painel de tarefas mais estreito:** listas, botões e campos numéricos não forçam mais o painel a
  alargar (alguns pediam de 400 a 700 px); textos longos quebram linha. O painel para de "pular" de
  largura ao abrir um comando.
- Menos trabalho em segundo plano: a troca de ícones do painel de tarefas procura só dentro dele.

## 0.3.0 beta — 22/10/2026

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
