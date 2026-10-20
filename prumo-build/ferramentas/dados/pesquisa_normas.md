# Pesquisa de dados técnicos para o Prumo 3D

Data: 19/10/2026. Os dados completos, com fonte e status de cada valor, estão em `pesquisa_normas.json`, no mesmo diretório.

**Critério de status**
- **confirmado**: valor lido em documento oficial (catálogo de fabricante ou ficha de norma) ou em texto da norma reproduzido por universidade, sem divergência entre fontes.
- **a checar**: fonte só secundária ou não oficial, fontes divergentes, extração duvidosa, ou valor calculado.

**Método e limites**
- As tabelas de PDF foram lidas por extração automática, que pode errar a transcrição.
- Por isso o JSON traz campos `verif_*`, que são checagens geométricas independentes: área da seção, massa = área × 0,785, massa teórica de cantoneira e massa de tubo pela fórmula da ASME B36.10M.

---

## 1. Folhas de desenho (ABNT)

### Alerta de vigência

A **ABNT NBR 16752:2020** ("Desenho técnico — Requisitos para apresentação em folhas de desenho", 01/2020, 23 p.) consta como **vigente** em [normas.com.br](https://www.normas.com.br/visualizar/abnt-nbr-nm/11569/abnt-nbr16752-desenho-tecnico-requisitos-para-apresentacao-em-folhas-de-desenho). Seu escopo cobre formatos, elementos gráficos, legenda, dobramento e escalas.

Sobre as normas antigas:
- A [UFRN](https://www.vetorial.design.ufrn.br/src/pdfs/Normas.pdf) afirma que a NBR 16752 substitui a NBR 10582:1988.
- É provável que também tenha substituído a NBR 10068 e a NBR 13142.
- **Status: a checar.** O catálogo da ABNT não pôde ser lido.

Normas novas da mesma família, citadas na [bibliografia da UFABC](https://graduacao.ufabc.edu.br/eiar/docentes/Riascos/ensino/disciplinas/Desenho/Bibliografia.pdf):
- NBR 16861:2020 (linhas e escrita)
- NBR 17006:2021 (métodos de projeção, inclusive o símbolo de diedro)
- NBR 17068:2022 (cotas e tolerâncias)

### Valores da NBR 10068 (out/1987, baseada na ISO 5457): confirmados

Fontes: texto da norma em material do [IFSC](https://docente.ifsc.edu.br/gianpaulo.medeiros/MaterialDidatico/Desenho%20Mecatr%c3%b4nica%20/aula%202/NBR%2010068-Folha%20de%20desenho%20-%20Leiaute%20e%20dimensoes.pdf) e apostila da [UFSJ](https://ufsj.edu.br/portal2-repositorio/File/prof_shiroma/PCG_impressao(1).pdf).

| Formato | Dimensões (mm) | Margem esquerda | Margens direita e demais | Linha do quadro | Legenda (comprimento) |
|---|---|---|---|---|---|
| A0 | 841 × 1189 | 25 | 10 | 1,4 | 175 |
| A1 | 594 × 841 | 25 | 10 | 1,0 | 175 |
| A2 | 420 × 594 | 25 | 7 | 0,7 | 178 |
| A3 | 297 × 420 | 25 | 7 | 0,5 | 178 |
| A4 | 210 × 297 | 25 | 7 | 0,5 | 178 |

**Legenda**
- Fica no canto inferior direito, dentro do quadro.
- A NBR 10068 tabela só a "margem direita". Aplicar o mesmo valor às margens superior e inferior é prática das apostilas e está marcado como a checar.

**Marcas**
- Marcas de centro: 4, no fim dos eixos de simetria.
- Marcas de corte: triângulo isósceles com catetos de 10 mm, ou dois traços de 2 mm em cada canto.

**Quadrículas**
- Número de divisões par, definido pela complexidade do desenho. A norma não fixa o número por formato.
- Malha com lado maior que 25 mm e até 75 mm.
- Traços com largura mínima de 0,5 mm.
- Letras em um lado e números no outro, a partir do canto oposto à legenda. Depois do Z: AA, BB...

### Valores da ISO 5457:1999 e ISO 7200:2004: a checar para a NBR 16752

Fontes: normas cubanas de adoção idêntica, [NC-ISO 5457](https://ftp.isdi.co.cu/Biblioteca/BIBLIOTECA%20UNIVERSITARIA%20DEL%20ISDI/COLECCION%20DIGITAL%20DE%20NORMAS%20CUBANAS/2005/NC%20ISO%205457%20%20a2005%2010p%20sie.pdf) e [NC-ISO 7200](https://ftp.isdi.co.cu/Biblioteca/BIBLIOTECA%20UNIVERSITARIA%20DEL%20ISDI/COLECCION%20DIGITAL%20DE%20NORMAS%20CUBANAS/2005/NC%20ISO%207200%20%20a2005%209p%20rez.pdf).

- Margem esquerda de 20 mm e demais de 10 mm, em todos os formatos.
  - Indício de que a NBR 16752 segue esses valores: questão da FUVEST 2025 cita margens ISO-A de 20/10/10/10 mm ([Gran](https://questoes.grancursosonline.com.br/questoes-de-concursos/legislacao-dos-orgaos-nbr-16752-abnt-432581)).
- Linha do quadro: 0,7 mm.
- Legenda: 180 mm, igual para todos os formatos.
- Marcas de centro: 0,7 mm de espessura, 10 mm além do quadro.
- Marcas de corte: dois retângulos de 10 × 5 mm.
- Quadrículas:
  - Malha de 50 mm a partir dos eixos.
  - Letras sem I e O; caracteres de 3,5 mm.
  - No A4, só nos lados superior e direito.
  - A tabela de divisões por formato não foi extraída. Os valores 24×16, 16×12, 12×8, 8×6 e 6×4 foram calculados, não lidos.

### Campos de legenda

**ISO 7200** (confirmado para a ISO; adoção pela NBR 16752 a checar)
- Obrigatórios: proprietário legal, número de identificação (16 caracteres), data de emissão, número da folha, título (25), aprovado por, criado por, tipo de documento.
- Opcionais: revisão, nº de folhas, idioma, departamento, referência técnica, estado, formato etc.

**Apostila UFSJ** (a checar; a apostila não atribui os campos à NBR 10582)
- Firma, projetista, data, local e assinatura, escala, símbolo do diedro, logotipo, unidade, conteúdo.

### Símbolo do 1º diedro

Tabela da UFSJ, a checar porque a norma de origem não é citada. Relação observada: **H = 2h** e **d (linha) = h/10**.

| h (mm) | 3,5 | 5 | 7 | 10 | 14 | 20 |
|---|---|---|---|---|---|---|
| H (mm) | 7 | 10 | 14 | 20 | 28 | 40 |
| d (mm) | 0,35 | 0,5 | 0,7 | 1 | 1,4 | 2 |

As proporções internas do símbolo (diâmetros dos círculos, comprimento do tronco de cone) não foram encontradas. Devem ser conferidas na NBR 17006.

### Dobramento (NBR 13142)

- Formato final A4 com a legenda visível: confirmado.
- Sequência e cotas das dobras: a checar.
- Ano da edição (1999): a checar.

---

## 2. Perfis laminados

### W e HP (Gerdau): 88 bitolas, de W 150×13,0 a W 610×174,0, HP 200, HP 250 e HP 310

Fontes e status:
- **Confirmado.** Catálogo "Perfis Estruturais Gerdau – Informações Técnicas", Tabela de Bitolas, sem data ([PDF no AECweb](https://api.aecweb.com.br/cls/catalogos/28792/22314/catalogo-gerdau-perfis-estruturais.pdf)). Norma do produto: NBR 15980:2011 e ASTM A6.
- Conferência cruzada com a [Fábrica do Projeto](https://www.fabricadoprojeto.com.br/en/tabelas-de-laminados-trefilados-e-itens-comerciais/tabela-de-perfil-w-h-hp/).
- A verificação de área (2·bf·tf + (d−2tf)·tw, mais o acréscimo dos raios) bateu em todas as 88 linhas.

Colunas: massa, d, bf, tw, tf, h, d' e área.
- **O catálogo não traz R.** O JSON tem um `R_mm_derivado` = (d−2tf−d')/2, que é estimativa, não dado do fabricante.

Divergências (marcadas a checar):
- HP 250×85: bf de 260 (Gerdau) contra 250 (Fábrica do Projeto). A verificação de área favorece 260.
- Designação W 360×44,6 contra 44,0.
- Designação W 360×58,0 contra 57,8.
- W 610×140: massa 142 kg/m na Fábrica do Projeto.
- W 460×52: h de 426 contra 428.
- As bitolas HP aparecem como "W" na Fábrica do Projeto.

### Perfil U padrão americano

- **ArcelorMittal, catálogo de abril de 2019** (oficial, confirmado): bitolas de 3", 4" e 6", 1ª e 2ª alma, com massa, altura, aba e alma.
  - 4"×5,40: a Fábrica do Projeto dá 7,39 kg/m e tw de 4,5 mm. A checar.
- **Fábrica do Projeto** (a checar): série de 3" a 15", 31 linhas.
- **Espessura média da aba: não encontrada em nenhuma fonte.**
- A tabela Gerdau não foi obtida. O catálogo "Barras e Perfis" (02/14) não tinha tabela extraível.

### Cantoneiras de abas iguais (ArcelorMittal 2019)

- **Série métrica**, abas de 40 a 100 mm, espessuras de 3 a 12 mm: confirmada. A massa bate com a geometria em até 3%.
- **Série em polegadas**, de 1/2"×1/8" a 4"×5/8", 41 linhas:
  - Confirmadas, exceto as **9 bitolas de espessura 1/4"**.
  - Nessas 9, a massa extraída está de 12% a 22% abaixo da massa geométrica. Provável deslocamento de linha na extração. A checar.
- Gerdau: só as faixas de bitolas (40–100 mm; 5/8" a 8"). A checar.

### Perfil I padrão americano

- **ArcelorMittal 2019** (confirmado): 4"×7,7, 4"×8,5, 6"×12,5 e 6"×14,8.
- **Fábrica do Projeto** (a checar): série de 3" a 12", 25 linhas, com tf.

---

## 3. Tubos

### Condução (ASME B36.10M), DN 1/2" a 12", Sch 40 e Sch 80: a checar

Fontes:
- Transcrição da ASME B36.10M-2004 na biblioteca [fluids](https://fluids.readthedocs.io/_modules/fluids/piping.html).
- [PDF ASTM A53/A106 no AECweb](https://api.aecweb.com.br/cls/catalogos/schedule/padroes_conducao_hidraulica.pdf), de fabricante não identificado.

Resultado:
- As duas fontes concordam em todas as espessuras até 10".
- A massa calculada por 0,0246615·(D−t)·t confere com a da fonte em até 0,15%.
- Continua "a checar" porque **não foi obtida tabela legível de fabricante brasileiro** (Tenaris, Vallourec, Apolo).

**Alerta importante**
- A Fábrica do Projeto lista Sch 40 = 9,53 mm para 12" e Sch 80 = 12,70 mm para 10" e 12". Esses valores são de STD/XS, não de Sch 40/80.
- Valores corretos pela B36.10M: 10" Sch 80 = 15,09 mm; 12" Sch 40 = 10,31 mm; 12" Sch 80 = 17,48 mm.
- O software deve tratar Sch e STD/XS como séries separadas.
- NBR 5590 e NBR 5580: as edições vigentes não foram verificadas.

### Estruturais quadrados e retangulares: a checar

- **Vallourec** (catálogo oficial de tubos sem costura): a extração desalinhou as colunas de espessura, então a tabela não foi transcrita.
- **Fábrica do Projeto** (metalon quadrado, de 15×15 a 150×150): um subconjunto foi transcrito no JSON. A massa confere com a de cantos vivos.
- NBR 6591: edição não verificada.

---

## 4. Chapas

Faixas de fabricantes (confirmado):
- **Usiminas Chapas Grossas** (dez/2022): 6 a 150 mm; largura 900 a 3.900 mm; comprimento 2.400 a 18.000 mm. O catálogo não lista espessuras comerciais discretas.
- **Usiminas Laminados a Frio** (2021): 0,20 a 3,00 mm.
- **ArcelorMittal Contagem**: chapa a quente (BQ) 1,20–8,50 mm; a frio (BF) 0,40–2,00 mm.

Tabelas a checar:
- Bitolas finas, da 30 à 7 (0,30 a 4,50 mm): só da Fábrica do Projeto, que repete linhas e tem erros.
- Espessuras grossas em polegadas, de 3/16" a 4": também só da Fábrica do Projeto.
- Série métrica usual (6,30 / 8,00 / 9,50 / 12,50 / 16,00 / 19,00 / 22,40 / 25,00...): **não confirmada** em nenhuma fonte.

---

## 5. Símbolos

**Rugosidade**
- **ABNT NBR 8404:1984**: confirmado ([IFPR](https://ifpr.edu.br/paranagua/wp-content/uploads/sites/20/2014/03/21_representacao-de-rugosidade.pdf)). Se ela continua vigente: a checar.
- Posições a–f do símbolo: confirmadas na mesma fonte.
- **ISO 1302:2002 foi retirada e substituída pela ISO 21920-1:2021**: confirmado ([SIS](https://www.sis.se/en/produkter/standardization/technical-drawings/mechanical-engineering-drawings/iso13022002)).

**Soldagem**
- **ISO 2553:2019** é a edição publicada. A ISO/DIS 2553 (ed. 6) teve a votação encerrada em 20/08/2026 e vai substituí-la: confirmado ([ISO](https://committee.iso.org/standard/90897.html?browse=ics)).
- **AWS A2.4:2020** é a edição vigente: confirmado ([ANSI](https://webstore.ansi.org/standards/aws/AWSA22020)).
- **Não foi encontrada norma ABNT de símbolos de soldagem.** A checar.

---

## Pendências principais

1. Confirmar no ABNT Catálogo o cancelamento das NBR 10068, 10582 e 13142 e obter os valores da NBR 16752.
2. Obter as tabelas oficiais Gerdau de U, I e cantoneiras, e corrigir as 9 cantoneiras de 1/4".
3. Obter os dados ainda ausentes:
   - raio R dos perfis W;
   - espessura média da aba dos perfis U;
   - proporções do símbolo de diedro (NBR 17006).
4. Obter tabelas de fabricante brasileiro:
   - tubos de condução (Sch 40/80, NBR 5590);
   - tubos estruturais (NBR 6591).
5. Páginas que ficaram bloqueadas durante a pesquisa:
   - fichas da target/normas.com.br para as NBR 13142 e 8404;
   - e-book do CETAM sobre normas de desenho técnico.
