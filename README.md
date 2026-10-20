<img src="/src/Mod/Prumo3D/Resources/icons/prumo.svg" height="100px" width="100px" alt="Prumo 3D">

# Prumo 3D

### Modelagem 3D paramétrica em português

[Baixar](https://github.com/prumo3d/prumo3d/releases/latest) •
[Problemas e sugestões](https://github.com/prumo3d/prumo3d/issues) •
[Como contribuir](CONTRIBUTING.md) •
[Documentação do FreeCAD](https://wiki.freecad.org)

O Prumo 3D é um modelador 3D paramétrico livre e gratuito, em português, para projeto mecânico:
peças, montagens, desenho técnico e simulação por elementos finitos. É baseado no
[FreeCAD](https://www.freecad.org) e mantém tudo o que ele oferece, com uma interface reorganizada e
ferramentas que encurtam o caminho entre a ideia e o desenho ou a simulação.

> [!NOTE]
> O Prumo 3D não é um projeto oficial do FreeCAD nem é mantido pela comunidade do FreeCAD.

<!-- Imagens: serão adicionadas a partir das capturas do Prumo 3D (pasta .github/images/prumo). -->

Visão geral
-----------

* **Tudo em português** Menus, painéis, nomes de propriedades e opções de listas traduzidos, inclusive termos
  que a tradução oficial do FreeCAD ainda não cobre.

* **Faixa de ferramentas** Os comandos principais organizados em abas (Início, Esboço, Peça, Sólidos,
  Montagem, Desenho, Estruturas, Chapa, Planilha, Simulação e Prumo), com ícones grandes e rótulos claros. A aba Esboço aparece
  sozinha ao editar um esboço.

* **Tela inicial** Começa uma peça, montagem, desenho técnico, esboço ou planilha com um clique e mostra os
  arquivos recentes.

* **Assistente de simulação** Análise por elementos finitos em etapas guiadas: peça, material, fixações,
  cargas, malha, verificação de pendências, resultados e relatório em PDF.

* **Biblioteca de materiais** Aços estruturais, inoxidáveis, para vasos de pressão, para construção mecânica,
  tubos, forjados e alumínio, com as especificações usadas no Brasil.

* **Tutoriais interativos** "Primeira peça" (esboço, cotas, extrusão, furo, arredondamento e salvar) e
  "Estrutura soldada" (esqueleto, grupos de perfis, cantos, reforço, solda e lista de corte). O painel
  acompanha o que você faz na tela e marca cada passo sozinho.

* **Guia ilustrado** Ao editar extrusão, cavidade, furo, arredondamento, chanfro, padrões e outras operações,
  o painel de tarefas mostra um desenho do que a operação faz no modo escolhido. O diálogo Cantos da
  estrutura soldada mostra o desenho de cada tratamento (meia-esquadria, de topo, recorte pelo contorno).

* **Árvore do modelo** Se o painel da árvore for fechado sem querer, o botão Início → Árvore do modelo
  traz de volta.

* **Esboço com ímãs e inferência** Ao desenhar, aparecem pontos-ímã nos quadrantes de círculos e arcos, no
  meio das linhas e nas interseções; o cursor é atraído e o ponto já recebe as restrições. Linhas tracejadas
  de inferência alinham o cursor na horizontal ou na vertical com pontos existentes.

* **Cotas na tela** Duplo clique numa face mostra as cotas da operação que a criou (comprimento da extrusão,
  raio do arredondamento, diâmetro do furo, cotas do esboço) para mudar o valor ali mesmo.

* **Menu de contexto pela seleção** O botão direito oferece o que faz sentido para o que está selecionado:
  esboço na face, extrudar, cavidade, arredondar, chanfro, medir e propriedades de massa.

* **Propriedades de massa e lista de materiais** Massa, centro de gravidade e momentos de inércia com o
  material de cada peça; lista de materiais da montagem em planilha e como tabela na folha de desenho.

* **Folhas ABNT** Folhas A0 a A4 no padrão da ABNT NBR 16752 (e no da NBR 10068), com legenda brasileira
  (responsável técnico, CREA/CFT, ART, 1º diedro) preenchida a partir do documento e vistas no 1º diedro.

* **Estruturas soldadas** Barras de perfis brasileiros (W, HP, U, I, cantoneiras, tubos e metalon, de
  catálogos de fabricantes) sobre um esqueleto de linhas, em grupos (perfil, giro, ponto de fixação e
  espelhamento por grupo). Cantos em meia-esquadria ou de topo (escolhendo qual barra passa), corte reto ou
  recorte pelo contorno nas ligações em T, nós com três ou mais barras, e cantos parecidos tratados de uma
  vez. Reforços (mão-francesa), tampas de tubo, placas de base com furação, cordões de solda com perna,
  processo e eletrodo, lista de corte e lista de soldas.

* **Chapa metálica** Parede base, abas, dobras, recortes, alívios e planificação (bancada SheetMetal embutida).

* **Peças padronizadas** Parafusos, porcas e arruelas métricas para inserir no modelo.

* **Visual próprio** Tema claro, ícones redesenhados e tela de abertura do Prumo 3D.

* **Testes automatizados** Um conjunto de testes confere tradução, aparência, assistente de simulação e
  comportamento da interface a cada versão.

* **Base sólida** Tudo o que o FreeCAD oferece continua disponível: núcleo geométrico OpenCASCADE, cena 3D
  Coin3D, interface Qt e programação em Python.

Instalação
----------

Baixe a versão mais recente na [página de versões](https://github.com/prumo3d/prumo3d/releases/latest):

| Sistema | Arquivo | Como usar |
|---|---|---|
| Windows 10/11 (64 bits) | `Prumo3D_…-installer.exe` | Rode o instalador. |
| Windows (portátil) | `Prumo3D_…-Windows-….7z` | Descompacte e abra `bin\Prumo3D.exe`. |
| Linux (64 bits) | `Prumo3D_…-Linux-….AppImage` | Marque como executável e abra. Em algumas distribuições é preciso instalar o pacote `libfuse2`. |

O Prumo 3D tem pasta de configurações própria e pode ser instalado ao lado do FreeCAD, sem interferir nele.

Código
------

| Pasta | Conteúdo |
|---|---|
| [`src/Mod/Prumo3D/`](src/Mod/Prumo3D/) | Módulo da interface do Prumo 3D, parte do programa: faixa, tradução, tela inicial, assistentes, tema, ícones e identidade (`extras/branding.xml`) |
| [`src/Gui/PreferencePacks/Prumo Claro/`](src/Gui/PreferencePacks/) | Tema Prumo Claro, embutido como pacote de preferências |
| [`src/Mod/SheetMetal/`](src/Mod/SheetMetal/) | Bancada de chapa metálica (SheetMetal, LGPL), embutida |
| [`prumo-build/`](prumo-build/) | Roteiro de compilação no Windows e ferramentas que geram ícones, tema de ícones e materiais |
| [`prumo-patches/`](prumo-patches/) | Correções aplicadas ao código do FreeCAD |
| [`package/`](package/) | Instalador Windows e empacotamento (Windows e AppImage) |
| [`.github/workflows/publicar.yml`](.github/workflows/publicar.yml) | Geração e publicação automática das versões |

O ramo `main` tem como base o FreeCAD 1.1.4 (estável).

Compilação
----------

**Automática:** cada tag `v*` enviada ao GitHub dispara o fluxo
[Publicar versão](.github/workflows/publicar.yml), que compila no Windows e no Linux e publica os arquivos.
Ele também pode ser rodado à mão pela aba *Actions*, para testes.

**No Windows, localmente:** o roteiro [`prumo-build/compilar.ps1`](prumo-build/compilar.ps1) confere os
pré-requisitos e compila. É preciso:

- Visual Studio 2022 com a carga de trabalho *Desenvolvimento para desktop com C++*;
- Git for Windows;
- [pixi](https://pixi.sh);
- pelo menos 40 GB livres em disco.

Rode `prumo-build\compilar.ps1 -SomenteVerificar` para conferir o ambiente e depois sem o parâmetro para
compilar. Detalhes em [`prumo-build/LEIA-ME.md`](prumo-build/LEIA-ME.md). Para a compilação do FreeCAD em
geral, veja o [Manual do Desenvolvedor do FreeCAD](https://freecad.github.io/DevelopersHandbook/gettingstarted/)
(em inglês).

Como relatar problemas
----------------------

- Procure nos [problemas já abertos](https://github.com/prumo3d/prumo3d/issues) para não repetir um relato;
- Informe a versão em `Ajuda > Sobre` (botão de copiar para a área de transferência);
- Descreva passo a passo como reproduzir o problema;
- Se puder, anexe um arquivo de exemplo (o `.FCStd` compactado em ZIP);
- Se o problema também acontece no FreeCAD, ele provavelmente deve ser relatado no
  [repositório do FreeCAD](https://github.com/FreeCAD/FreeCAD/issues).

Uso e ajuda
-----------

Por ser baseado no FreeCAD, a documentação dele vale para o Prumo 3D (wiki em inglês; muitas páginas têm
versão em português pelo seletor de idioma):

- [Primeiros passos](https://wiki.freecad.org/Getting_started)
- [Lista de recursos](https://wiki.freecad.org/Feature_list)
- [Perguntas frequentes](https://wiki.freecad.org/FAQ)
- [Bancadas de trabalho](https://wiki.freecad.org/Workbenches)
- [Programação em Python](https://wiki.freecad.org/Power_users_hub)

Licença
-------

O Prumo 3D é distribuído sob a mesma licença do FreeCAD, a
[GNU LGPL versão 2.1 ou posterior](LICENSE). O texto da licença é mantido no original em inglês, que é a
versão com validade jurídica.

Créditos
--------

O Prumo 3D existe graças ao trabalho de milhares de pessoas da comunidade do
[FreeCAD](https://www.freecad.org), que desenvolvem e mantêm o programa. Se o FreeCAD é útil para
você, considere [apoiar o projeto original](https://wiki.freecad.org/Donate).
