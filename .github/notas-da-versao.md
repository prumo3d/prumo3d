## Prumo 3D 0.1 beta

Primeira versão de teste do Prumo 3D: modelagem 3D paramétrica em português, com ferramentas para o
dia a dia da engenharia mecânica no Brasil. É baseado no FreeCAD 1.1 e usa os mesmos arquivos `.FCStd`.

> **Versão beta:** feita para testar. Guarde cópia dos seus arquivos e não use ainda em projeto com
> prazo. Relatos de problema são muito bem-vindos (veja "Como relatar um problema").

### O que tem de novo em relação ao FreeCAD

- **Interface em português** com faixa de abas (Início, Esboço, Peça, Sólidos, Montagem, Desenho,
  Estruturas, Chapa, Planilha, Simulação), tema claro e escuro e tela inicial com exemplos.
- **Tutoriais interativos**: "primeira peça" e "estrutura soldada". Cada passo é marcado sozinho
  quando você o faz, e "Mostrar onde" pisca o botão certo na faixa.
- **Esboço:** pontos-ímã em quadrantes, pontos médios e interseções; linhas de inferência
  (alinhamento com pontos existentes); ao concluir o esboço, a vista enquadra o modelo.
- **Cotas na tela:** duplo clique na peça mostra as cotas da operação para editar ali mesmo.
- **Menu do botão direito** pela seleção (extrusão, cavidade, arredondamento, medir, massa).
- **Propriedades de massa** (massa, centro de gravidade, inércia) e **lista de materiais** com tabela
  na folha.
- **Folhas A0 a A4 no padrão ABNT** (NBR 16752 e NBR 10068), com legenda brasileira (responsável
  técnico, CREA/CFT, ART), vistas no 1º diedro e escalas normalizadas.
- **Estruturas soldadas** com perfis brasileiros (W, HP, U, I, cantoneiras, tubos e metalon):
  grupos de perfis, ponto de fixação, cantos em meia-esquadria ou de topo, recorte pelo contorno,
  reforços (mão-francesa), tampas de tubo, placas de base, cordões de solda, lista de corte e lista
  de soldas. O diálogo Cantos mostra um desenho de cada tratamento.
- **Chapa metálica** (bancada SheetMetal embutida): paredes, dobras e planificação.
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
6. **Chapa:** crie uma chapa base, uma dobra e planifique.
7. Salve, feche e abra de novo.

### Limitações conhecidas

- Arquivos com objetos do Prumo (estruturas, reforços, soldas, folhas ABNT) abertos no FreeCAD comum
  mostram as formas, mas esses objetos não são recalculados lá.
- Alguns perfis e tubos estão marcados **"a conferir"** (fonte secundária): o Prumo avisa na escolha
  do perfil. Confira no catálogo do fabricante antes de usar em projeto.
- O vaso de pressão e a análise de estruturas por barras ficaram para versões futuras.

### Como relatar um problema

No Prumo, abra **Ajuda → Sobre** e clique em **Copiar informações do sistema**. Cole esse texto junto
com a descrição do problema (o que fez, o que esperava, o que aconteceu) e, se possível, um print da tela.

---

O Prumo 3D é software livre (LGPL-2.1-or-later), baseado no [FreeCAD](https://www.freecad.org). Não é
um projeto oficial do FreeCAD.
