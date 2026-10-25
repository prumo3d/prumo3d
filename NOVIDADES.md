# Novidades do Prumo 3D

O que mudou em cada versão, da mais nova para a mais antiga. Os arquivos para baixar ficam na
[página de versões](https://github.com/prumo3d/prumo3d/releases).

**Como as versões são numeradas** (até a 1.0, todas são beta):

- `0.X.0`: entrou ferramenta nova ou mudou o jeito de usar alguma coisa (ex.: 0.2.0).
- `0.X.Y`: correções e ajustes pequenos, sem ferramenta nova (ex.: 0.1.1).
- `-beta` no fim: versão de teste; guarde cópia dos seus arquivos.

## Em desenvolvimento

### Melhorias

- **Verificar geometria:** resumo em cartões acima da lista do FreeCAD — geometria válida ou com defeito,
  sólidos, cascas, faces, arestas, vértices, volume e área.
- **Peso próprio com painel:** criar pelo botão da faixa (ou editar com duplo clique) abre cartões com a
  direção da gravidade (−Z, +Z, ±X, ±Y) e a aceleração em m/s². Cancelar na criação desfaz.

### Correções

- O último trecho que lia os quadros do jeito antigo (rolagem de janelas grandes) foi trocado, como o do
  botão OK na 0.9.2.

### Testes

- Verificar geometria de uma caixa (6 faces, 12 arestas, 1.000 mm³); peso próprio criado pela faixa, em −Y
  e 9,81 m/s², e reaberto para editar.

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
