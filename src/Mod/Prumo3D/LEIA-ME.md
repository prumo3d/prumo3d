# Prumo 3D — módulo de interface

Módulo em Python com a interface do Prumo 3D. Faz parte do programa: é compilado e instalado junto com os
outros módulos (`Mod/Prumo3D`), sem instalação separada.

## O que ele faz

| Item | Como |
|---|---|
| Faixa de ferramentas (ribbon) | Abas Início, Esboço, Peça, Sólidos, Montagem, Desenho, Planilha e Prumo. Comandos principais com ícone grande, demais empilhados, grupos com legenda. Rótulos em português escritos para o Prumo 3D. As barras clássicas ficam ocultas. |
| Aba Esboço automática | Ao editar um esboço, a faixa mostra a aba Esboço e volta à anterior ao concluir. |
| Tradução pt-BR completa | `translations/prumo_ptbr.qm` (tradução mais recente do repositório do FreeCAD, mais completa que a da versão 1.1.4) + dicionário `PrumoI18n.EXTRA` para o que nem o repositório traduz. Instalada com prioridade sobre a oficial. |
| Tema "Prumo Claro" | Acento azul #003A70, pré-seleção amarela #F7BE00, vista 3D em degradê branco → #CBD5E0, menus e painéis claros. Força o esquema claro mesmo com o Windows em modo escuro. |
| Tema de ícones "Prumo Sóbrio" | 1.582 ícones do FreeCAD recoloridos para a paleta do Prumo 3D (azul-aço, âmbar, tijolo, sálvia, cinza frio), contornos em ardósia e degradê vertical em todo preenchimento chapado (efeito 3D). Vale para faixa, menus e árvore do modelo. Fica em `Resources/tema-icones-prumo.zip`; o módulo descompacta em `<dados do usuário>/PrumoIcones` e registra em `Bitmaps/CustomPathPrumo`. Liga/desliga na aba Prumo (vale ao reabrir). |
| Guia ilustrado nas tarefas | Ao editar Extrusão, Cavidade, Revolução, Ranhura, Furo, Arredondar, Chanfro, Padrão linear/circular, Espelhar, Casca e Ângulo de saída, aparece no topo do painel Tarefas um desenho isométrico do que a função faz **no modo escolhido** (acompanha as trocas de modo), com legenda e instrução curta. Desenhos em `PrumoIlustra.py`, textos e regras em `PrumoGuia.py`. Desligar: parâmetro `GuiaIlustrado`. |
| Qualidade de exibição | Anti-aliasing MSAA 8x (linhas sem serrilhado) e tesselação mais fina (desvio 0,1 %, ângulo 12°) para curvas lisas. Aplicado uma vez; ajuste em `QUALITY` no `PrumoGui.py`. |
| Splash, título e ícone | Splash Prumo, "Prumo 3D" no título, ícone Prumo. |

## Ferramentas de projeto

| Ferramenta | Módulo | Onde fica |
|---|---|---|
| Cotas da operação (duplo clique numa face; Shift+D) | `PrumoCotas.py` | aba Peça, menu de contexto |
| Menu de contexto pela seleção | `PrumoContexto.py` | botão direito (vista 3D e árvore) |
| Propriedades de massa (massa, CG, inércia) | `PrumoMassa.py` | abas Peça, Montagem, Estruturas |
| Lista de materiais (planilha e tabela na folha) | `PrumoBOM.py` | abas Peça, Montagem, Desenho, Estruturas |
| Folhas ABNT A0–A4 (NBR 16752 e NBR 10068) | `PrumoFolhas.py`, `Resources/folhas/` | abas Desenho e Peça |
| Biblioteca de perfis (W, HP, U, I, L, tubos, metalon) | `PrumoPerfis.py`, `Resources/perfis/perfis.json` | usada pela estrutura e pelo vaso |
| Estrutura soldada, trocar perfil, lista de corte | `PrumoEstrutura.py` | aba Estruturas |
| Vaso de pressão (ASME VIII-1, UG-27/UG-32) | `PrumoVaso.py` | aba Estruturas |
| Parafusos, porcas e arruelas (ISO 4017, 4762, 4032, 7089) | `PrumoFixadores.py`, `Resources/fixadores/` | aba Estruturas |
| Chapa metálica | bancada SheetMetal embutida (`src/Mod/SheetMetal`) | aba Chapa |

Dados de normas e catálogos: cada perfil e cada fixador tem fonte e situação ("confirmado" ou "a
conferir"); o Prumo mostra o aviso na hora da escolha. Os dados de origem e os geradores ficam em
`prumo-build/ferramentas/` (`gerar_perfis.py`, `gerar_fixadores.py`, `gerar_folhas_abnt.py`, pasta `dados/`).

Testes: `PrumoTestesFerramentas.py` (entram no comando *Testes automáticos*).

## Arquivos

- `InitGui.py` — ponto de entrada (carregado pelo FreeCAD)
- `PrumoGui.py` — branding, tema, comandos Prumo
- `PrumoRibbon.py` — a faixa de ferramentas (abas e comandos ficam na lista `TABS`)
- `PrumoI18n.py` — tradução com prioridade e dicionário `EXTRA`
- `PrumoPropNames.py` — nomes de propriedades e grupos do painel Dados/Vista (~500 termos, contexto `App::Property`)
- `extras/branding.xml` — identidade do programa (nome, splash, pasta de dados)
- `Resources/` — splash e ícones
- `translations/prumo_ptbr.qm` — tradução compilada

## Como entra no programa

- `CMakeLists.txt` copia o módulo para `Mod/Prumo3D` (pasta de compilação e instalação) e o
  `extras/branding.xml` para a pasta `bin` do programa. O `branding.xml` dá o nome "Prumo 3D", a tela de
  abertura e a pasta de dados própria (`%APPDATA%\Prumo3D`, `~/.local/share/Prumo3D`).
- O tema "Prumo Claro" fica em `src/Gui/PreferencePacks/Prumo Claro`, entre os pacotes de preferências embutidos.
- Opção do CMake: `BUILD_PRUMO3D` (padrão ON).

## Mudar a faixa

Edite a lista `TABS` em `PrumoRibbon.py`. Cada item é `("NomeDoComando", L ou S, "Rótulo")`:
`L` = ícone grande, `S` = pequeno; `\n` quebra o rótulo grande em duas linhas.
Comando que não existir na versão instalada é ignorado.

## Opções (Ferramentas → Editar parâmetros → BaseApp/Preferences/Mod/Prumo3D)

- `RibbonEnabled` (padrão true) — faixa Prumo; também alternável pelo comando *Alternar faixa Prumo / barras clássicas* na aba Prumo
- `RibbonHeight` (padrão 104) — altura da área de comandos, em px
- `PrumoTranslations` (padrão true) — tradução Prumo
- `RenameWindow`, `InstallSplash`, `ApplyThemeOnFirstRun` (padrão true)

## Atualizar o tema de ícones

`prumo-build/ferramentas/gerar_tema_icones.py <clone do FreeCAD> <pasta de saída>` gera os SVGs. Paleta e intensidade do degradê
ficam nas funções `recolor()` e `shade()`. Depois compacte a pasta em `Resources/tema-icones-prumo.zip`.

## Atualizar a tradução

Com o clone do FreeCAD: `lrelease $(find . -name "*_pt-BR.ts") -qm prumo_ptbr.qm`.

## Licença

LGPL-2.1-or-later, a mesma do FreeCAD.
