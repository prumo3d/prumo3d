> **Versão beta:** feita para testar. Guarde cópia dos seus arquivos e não use ainda em projeto com
> prazo. Relatos de problema são muito bem-vindos (veja "Como relatar um problema").

### Como baixar

| Sistema | Arquivo | Como usar |
|---|---|---|
| Windows 10/11 (64 bits) | `Prumo3D_…-installer.exe` | Rode o instalador. Instala ao lado de um FreeCAD já existente, sem substituí-lo. |
| Windows (portátil) | `Prumo3D_…-Windows-….7z` | Descompacte e abra `bin\Prumo3D.exe`. Não precisa instalar. |
| Linux (64 bits) | `Prumo3D_…-Linux-….AppImage` | Marque como executável (`chmod +x`) e abra. Em algumas distribuições é preciso instalar o pacote `libfuse2`. |

Cada arquivo tem um `-SHA256.txt` com o código de verificação. Nem todos os formatos saem em toda
versão de teste.

Os instaladores ainda não têm assinatura digital: o Windows mostra o aviso de "editor desconhecido".
Clique em **Mais informações → Executar assim mesmo**. Confira o arquivo pelo `-SHA256.txt`.

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
- Vasos de pressão: reforço de aberturas, pressão externa, vento, sismo e cargas nos suportes ainda
  não são calculados (o memorial avisa); o enquadramento na NR-13 fica com o responsável técnico.
- Estruturas: grande deslocabilidade só é avisada (pede análise com não linearidade de material); a
  ancoragem dos chumbadores no concreto não é verificada; a classificação de deslocabilidade usa os
  deslocamentos horizontais nó a nó, não andar a andar.

### Como relatar um problema

No Prumo, abra **Ajuda → Sobre** e clique em **Copiar informações do sistema**. Cole esse texto junto
com a descrição do problema (o que fez, o que esperava, o que aconteceu) e, se possível, um print da tela.

---

O Prumo 3D é software livre (LGPL-2.1-or-later), baseado no [FreeCAD](https://www.freecad.org). Não é
um projeto oficial do FreeCAD.
