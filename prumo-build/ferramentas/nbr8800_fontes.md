# Pesquisa normativa (fontes do módulo de cálculo de estruturas): NBR 8800:2008 (barras de aço) e NBR 8681:2003 (combinações)

Data da pesquisa: 21/10/2026. Notação: sqrt() = raiz quadrada; ^ = potência; "p." = página impressa da norma.

## 0. Fontes usadas e método

| ID | Fonte | URL | Observação |
|---|---|---|---|
| S1 | Texto integral da ABNT NBR 8800:2008, 2ª edição, 25.08.2008 (247 páginas no PDF) | (link omitido: cópia não oficial de norma protegida por direitos autorais) | Cópia não oficial, com marca d'água de licenciado. O WebFetch só via as primeiras páginas, então o PDF foi aberto no Chrome e o texto extraído página a página com pdf.js. Página impressa = página do PDF − 10. |
| S2 | Texto da NBR 8681, "MAR 2003" (15 páginas, sem errata incorporada) | (link omitido: cópia não oficial de norma protegida por direitos autorais) | Cópia não oficial, extraída do mesmo modo. |
| S3 | Target: ficha da NBR 8800 (aba "Histórico") | https://www.target.com.br/produtos/normas-tecnicas/27466/nbr8800-projeto-de-estruturas-de-aco-e-de-estruturas-mistas-de-aco-e-concreto-de-edificacoes | Lida no navegador. |
| S4 | Target: ficha da NBR 8681 (aba "Histórico") | https://www.target.com.br/produtos/normas-tecnicas/27572/nbr8681-acoes-e-seguranca-nas-estruturas | Lida no navegador. |
| S5 | Boletim CBIC de normas publicadas em 2024 | https://cbic.org.br/wp-content/uploads/2025/02/boletim-alteracoes-de-normas-tecnicas-setor-da-construcao-civil-2024.pdf | |
| S6 | Boletim CBIC jan–mar/2025 | https://cbic.org.br/inovacao/wp-content/uploads/sites/23/2025/06/boletim-de-normas-tecnicas-setor-da-construcao-civil-janfevmar25.pdf | |
| S7 | ABECE, "Em vigor, a nova NBR 8800" (out/2024) | https://site.abece.com.br/em-vigor-a-nova-nbr-8800/ | |
| S8 | ABECE, "NBR 8800 tem versão corrigida publicada" (fev/2025) | https://site.abece.com.br/nbr-8800-tem-versao-corrigida-publicada/ | |
| S9 | CBCA, "Lançamento da ABNT NBR 8800:2024" (08/10/2024) | https://www.cbca-acobrasil.org.br/site/noticia/lancamento-da-abnt-nbr-8800-2024 | |
| S10 | TCC UFRGS "Dimensionamento de estruturas metálicas" (segue a NBR 8800:2008) | https://lume.ufrgs.br/bitstream/handle/10183/28583/000769204.pdf | Fonte secundária, usada para corroborar raízes e frações. |
| S11 | Projeto de Revisão da NBR 8800, versão jan/2007 | (link omitido: cópia não oficial de norma protegida por direitos autorais) | É rascunho. Traz E = 205000 MPa, enquanto o texto final de 2008 traz 200000 MPa. Não use. |

**Limite do método.** A extração de texto de PDF perde os elementos gráficos das fórmulas: o traço do radical e as barras de fração. Montei as fórmulas abaixo a partir da sequência de símbolos extraída. Os radicais estão corroborados por S10 em λ0, no λp/λr do cortante, em λr da FLT e no λp de tubo retangular. Os demais estão listados em "A CHECAR" para conferência visual. Os valores numéricos (coeficientes e constantes) vieram do texto sem ambiguidade.

---

## 1. Vigência (prioridade alta)

| Norma | Situação confirmada | Fonte |
|---|---|---|
| NBR 8800:2008 | Histórico na Target: 04/1986 edição; 08/2008 nova edição; confirmações em 01/2014, 11/2018 e 12/2023; **10/2024 nova edição**; 02/2025 errata e nova edição "(inc.err.)". A edição vigente é a "NBR8800 DE 10/2024 – Projeto de estruturas de aço e de estruturas mistas de aço e concreto de edificações". **A edição de 2008 não é mais a vigente.** Não há errata registrada para a edição de 2008. | S3 |
| NBR 8800:2024 | ABNT/CB-002, "válida a partir de 02/10/2024", status "Publicada". | S5 |
| NBR 8800:2024 (errata) | "(Errata) Projeto de estruturas de aço..." válida a partir de 25/02/2025. | S6 |
| | ABECE: publicada em 2 de outubro de 2024. Em fev/2025, "versão corrigida 2025 da NBR 8800:2024", que ajustou a numeração de seções e corrigiu fórmulas. | S7, S8 |
| | CBCA: notícia de lançamento datada de 08/10/2024. | S9 |
| NBR 8681:2003 | Histórico na Target: 12/1984 edição; 03/1985 errata e "(inc.err.)"; **03/2003 nova edição**; **03/2004 errata**; **04/2004 nova edição (inc.err.)**, que é a versão corrigida de 2004; confirmações em 05/2011, 12/2015, 12/2019 e 03/2024; **09/2025 nova edição**. A vigente é a "NBR8681 DE 09/2025 – Ações e segurança nas estruturas" (23 páginas). **A edição de 2003 (e sua versão corrigida de 2004) não é mais a vigente.** | S4 |

**Divergência:** um artigo de congresso (https://static.even3.com/anais/1418226.pdf) fala em publicação da NBR 8800:2024 "em abril de 2024". Os boletins CBIC (S5) e a ABECE (S7) dizem 02/10/2024. Fico com 02/10/2024.

**Consequência para o software:** rotule o módulo como "NBR 8800:2008 / NBR 8681:2003 (edições substituídas)". Para projeto novo com ART, as edições vigentes são a NBR 8800:2024 (versão corrigida 2025) e a NBR 8681:2025. O conteúdo dessas duas não foi conferido (ver "A CHECAR").

---

## 2. NBR 8800:2008, itens confirmados (fonte S1)

### 2.1 Propriedades do aço e coeficientes de resistência

| Grandeza | Valor | Item / página |
|---|---|---|
| E | 200 000 MPa | 4.5.2.9 a), p. 13 |
| ν_a | 0,3 | 4.5.2.9 b) |
| G | 77 000 MPa | 4.5.2.9 c) |
| β_a (dilatação térmica) | 1,2 × 10^-5 °C^-1 | 4.5.2.9 d) |
| ρ_a | 7 850 kg/m³ | 4.5.2.9 e) |
| γa1 (escoamento, flambagem e instabilidade) | normais 1,10; especiais ou de construção 1,10; excepcionais 1,00 | Tabela 3, 4.8.2.1, p. 23 |
| γa2 (ruptura) | normais 1,35; especiais ou de construção 1,35; excepcionais 1,15 | Tabela 3 |
| (γc / γs, para referência) | 1,40 / 1,15 (normais); 1,20 / 1,15 (especiais); 1,20 / 1,00 (excepcionais) | Tabela 3 |

### 2.2 Tração (5.2, p. 37–43)

- Condição: Nt,Sd ≤ Nt,Rd (5.2.1.2).
- Nt,Rd é o menor de (5.2.2):
  - a) escoamento da seção bruta: Nt,Rd = Ag fy / γa1
  - b) ruptura da seção líquida: Nt,Rd = Ae fu / γa2
- Ae = Ct An (5.2.3).
- **An = Ag em regiões sem furos** (5.2.4.2, p. 39).
- Ct (5.2.5):
  - a) Ct = 1,00 quando a força de tração é transmitida diretamente para cada um dos elementos da seção, por soldas ou parafusos.
  - b) Ct = Ac/Ag quando a força é transmitida somente por soldas transversais.
  - c) Seções abertas com ligação em apenas alguns elementos: Ct = 1 − ec/lc, com limite superior 0,90. Não é permitida ligação que resulte em Ct < 0,60.
  - d) Chapas com solda longitudinal nas duas bordas: Ct = 1,00 se lw ≥ 2b; 0,87 se 2b > lw ≥ 1,5b; 0,75 se 1,5b > lw ≥ b.
  - e) Tubos retangulares com chapa de ligação: conforme o texto da alínea e).
- **Resposta à pergunta "Ae = Ag com Ct = 1 sem furos?":** a norma permite An = Ag quando não há furos (5.2.4.2). Ct, porém, não depende dos furos: depende de como a força entra na barra (5.2.5). Portanto Ae = Ag só vale se não houver furos **e** a ligação transmitir a força a todos os elementos da seção (alínea a). Uma cantoneira soldada só por uma aba, por exemplo, tem Ct < 1 mesmo sem furos. No software, trate isso como uma hipótese declarada pelo usuário, não como padrão silencioso.
- Esbeltez na tração (5.2.8.1, p. 43): **recomenda-se** L/r ≤ 300. Excetuam-se tirantes de barras redondas pré-tensionadas ou barras montadas com pré-tensão. É recomendação: se não for adotada, o responsável técnico define outros limites (5.2.8.3).

### 2.3 Compressão (5.3 e Anexos E e F)

- Nc,Rd = χ Q Ag fy / γa1 (5.3.2, p. 44).
- χ (5.3.3.1):
  - λ0 ≤ 1,5: chi = 0,658^(λ0^2)
  - λ0 > 1,5: chi = 0,877 / λ0^2
  - A Tabela 4 e a Figura 11 dão χ para λ0 ≤ 3,0.
- λ0 = sqrt(Q Ag fy / Ne) (5.3.3.2). A raiz é corroborada por S10, eq. 15.
- Esbeltez (5.3.4.1, p. 46): KL/r ≤ 200, com K de E.2.1.1, E.2.1.2 ou E.2.1.3. Em barras compostas, a esbeltez de cada perfil entre ligações deve ser ≤ 1/2 da KL/r do conjunto (5.3.4.2).
- **Ne, Anexo E (p. 121–125):**
  - E.1.1 Seções duplamente simétricas ou simétricas em relação a um ponto:
    - Nex = π² E Ix / (Kx Lx)²
    - Ney = π² E Iy / (Ky Ly)²
    - Nez = (1/r0²) [π² E Cw / (Kz Lz)² + G J]
    - r0 = sqrt(rx² + ry² + x0² + y0²)
  - E.1.2 Seções monossimétricas com y como eixo de simetria (exceto cantoneira simples de E.1.4):
    - Nex = π² E Ix / (Kx Lx)²
    - Neyz = (Ney + Nez) / {2 [1 − (y0/r0)²]} × [1 − sqrt(1 − 4 Ney Nez [1 − (y0/r0)²] / (Ney + Nez)²)]
    - Se x for o eixo de simetria, troca-se x por y e y0 por x0.
  - E.1.3 Seções assimétricas: Ne é a menor raiz da equação cúbica
    (Ne − Nex)(Ne − Ney)(Ne − Nez) − Ne² (Ne − Ney)(x0/r0)² − Ne² (Ne − Nex)(y0/r0)² = 0
  - E.1.4 Cantoneira simples conectada por uma aba. Condições: carregada nas extremidades pela mesma aba; ligada por solda ou por pelo menos 2 parafusos na direção da força; sem cargas transversais. Então Ne = π² E Ix1 / (Kx1 Lx1)², com Ix1 em relação ao eixo paralelo à aba conectada.
    - E.1.4.2 Barras isoladas, ou diagonais e montantes de treliça plana:
      - 0 ≤ Lx1/rx1 ≤ 80: Kx1 Lx1 = 72 rx1 + 0,75 Lx1
      - Lx1/rx1 > 80: Kx1 Lx1 = 32 rx1 + 1,25 Lx1
      - Abas desiguais (razão ≤ 1,7) ligadas pela aba menor: Kx1 Lx1 ≥ 0,95 Lx1 rx1/rmin, e o valor acima é aumentado de 4 [(be/bs)² − 1] rx1.
    - E.1.4.3 Treliças espaciais:
      - 0 ≤ Lx1/rx1 ≤ 75: Kx1 Lx1 = 60 rx1 + 0,80 Lx1
      - Lx1/rx1 > 75: Kx1 Lx1 = 45 rx1 + Lx1
      - Abas desiguais: mínimo 0,82 Lx1 rx1/rmin, e o valor é aumentado de 6 [(be/bs)² − 1] rx1.
    - E.1.4.4 Outros casos (razão entre abas > 1,7 ou forças transversais): tratar como flexo-compressão.
- **K (E.2):**
  - Tabela E.1, casos (a) a (f): valores teóricos 0,5 / 0,7 / 1,0 / 1,0 / 2,0 / 2,0; valores recomendados 0,65 / 0,80 / 1,2 / 1,0 / 2,1 / 2,0.
  - E.2.1.2 Elementos contraventados: K = 1,0, a menos que se demonstre que um valor menor pode ser usado.
  - E.2.1.3 Barras das subestruturas de contraventamento analisadas por 4.9.7: K = 1,0.
  - **K = 1,0 é o padrão normativo só para esses casos.** Para elemento isolado (por exemplo, em balanço), use a Tabela E.1.
  - E.2.2: Kz = 1,00 com rotação axial impedida e empenamento livre nas duas extremidades; Kz = 2,00 com uma extremidade livre e a outra com rotação e empenamento impedidos.
- **Fator Q, Anexo F (p. 126–129):**
  - F.1.2: Q = 1,00 se todos os b/t ≤ (b/t)lim. Caso contrário, Q = Qs Qa (F.1.3). Só elementos AL: Q = Qs. Só AA: Q = Qa.
  - Tabela F.1, (b/t)lim:
    - Grupo 1 (AA), mesas ou almas de tubos retangulares, lamelas e diafragmas: 1,40 sqrt(E/fy)
    - Grupo 2 (AA), almas de I, H e U; mesas ou almas de caixão; demais AA: 1,49 sqrt(E/fy)
    - Grupo 3 (AL), abas de cantoneiras simples, ou múltiplas com chapas de travejamento: 0,45 sqrt(E/fy)
    - Grupo 4 (AL), mesas de I, H, T e U laminadas; abas de cantoneiras ligadas continuamente ou projetadas de perfis; chapas projetadas: 0,56 sqrt(E/fy)
    - Grupo 5 (AL), mesas de I, H, T e U soldadas: 0,64 sqrt(E/(fy/kc))
    - Grupo 6 (AL), almas de seções T: 0,75 sqrt(E/fy)
  - F.2, Qs:
    - Grupo 3:
      - 0,45 sqrt(E/fy) < b/t ≤ 0,91 sqrt(E/fy): Qs = 1,340 − 0,76 (b/t) sqrt(fy/E)
      - b/t > 0,91 sqrt(E/fy): Qs = 0,53 E / [fy (b/t)²]
    - Grupo 4:
      - 0,56 < b/t·sqrt(fy/E) ≤ 1,03: Qs = 1,415 − 0,74 (b/t) sqrt(fy/E)
      - acima de 1,03: Qs = 0,69 E / [fy (b/t)²]
    - Grupo 5:
      - 0,64 sqrt(E/(fy/kc)) < b/t ≤ 1,17 sqrt(E/(fy/kc)): Qs = 1,415 − 0,65 (b/t) sqrt(fy/(kc E))
      - acima: Qs = 0,90 E kc / [fy (b/t)²]
      - kc = 4 / sqrt(h/tw), com 0,35 ≤ kc ≤ 0,76
    - Grupo 6:
      - 0,75 < b/t·sqrt(fy/E) ≤ 1,03: Qs = 1,908 − 1,22 (b/t) sqrt(fy/E)
      - acima: Qs = 0,69 E / [fy (b/t)²]
    - Com vários elementos AL, adota-se o menor Qs.
  - F.3, Qa (AA):
    - Qa = Aef/Ag, com Aef = Ag − Σ (b − bef) t
    - bef = 1,92 t sqrt(E/σ) [1 − (ca/(b/t)) sqrt(E/σ)] ≤ b
    - ca = 0,38 para mesas ou almas de tubos retangulares; 0,34 para os demais
    - σ = χ fy, com χ calculado com Q = 1,0. Opcionalmente, de forma conservadora, σ = fy.
  - F.4, tubos circulares:
    - Q = 1,00 se D/t ≤ 0,11 E/fy
    - Q = 0,038 E / [fy (D/t)] + 2/3 se 0,11 E/fy < D/t ≤ 0,45 E/fy
    - D/t > 0,45 E/fy não é previsto (F.4.2).
  - **Mapa por seção:**
    - I/H laminado: mesa no grupo 4 (b = bf/2), alma no grupo 2.
    - I/H soldado: mesa no grupo 5, alma no grupo 2.
    - U: mesa no grupo 4 (laminado) ou 5 (soldado), com b = largura total da mesa (5.1.2.2.4 b); alma no grupo 2.
    - Tubo retangular: grupo 1.
    - Cantoneira simples: grupo 3.
    - Tubo circular: F.4.

### 2.4 Momento fletor (5.4.2 e Anexo G)

- Mrd ≤ 1,50 W fy / γa1, com W = módulo elástico mínimo (5.4.2.2, p. 47).
- **Cb** (5.4.2.3):
  - a) Cb = 12,5 Mmax / (2,5 Mmax + 3 MA + 4 MB + 3 MC) × Rm ≤ 3,0
    - Rm = 0,5 + 2 (Iyc/Iy)² para seção monossimétrica em curvatura reversa; Rm = 1,00 nos demais casos.
  - b) Balanço com extremidade livre: Cb = 1,00.
  - 5.4.2.4 Mesa com contenção lateral contínua:
    - Cb = 3,00 − (2/3)(M1/M0) − (8/3) M2/(M0 + M1), quando a mesa contida está tracionada em pelo menos uma extremidade
    - Cb = 2,00 em trecho com momento nulo nas extremidades e carga distribuída, com só a mesa tracionada contida
    - Cb = 1,00 nos outros casos
- **G.2.1, FLT:**
  - λ ≤ λp: Mrd = Mpl/γa1
  - λp < λ ≤ λr: Mrd = (Cb/γa1) [Mpl − (Mpl − Mr)(λ − λp)/(λr − λp)] ≤ Mpl/γa1
  - λ > λr: Mrd = Mcr/γa1 ≤ Mpl/γa1
  - Válido para carga transversal aplicada na semi-altura da seção.
- **G.2.2, FLM e FLA:** as mesmas expressões, sem Cb. Para λ > λr, Mrd = Mcr/γa1, o que não se aplica à FLA (nesse caso vale o Anexo H, viga de alma esbelta).
- Mpl = Z fy. σr = 0,30 fy (Nota 5).
- **Tabela G.1 (p. 134; notas p. 135–136).**
  - I e H duplamente simétricas e U sem torção, flexão no eixo de maior inércia:
    - FLT: Mr = (fy − σr) W; λ = Lb/ry; λp = 1,76 sqrt(E/fy); λr e Mcr pela Nota 1.
    - FLM: Mr = (fy − σr) W; λ = b/t; λp = 0,38 sqrt(E/fy); λr e Mcr pela Nota 6.
    - FLA: Mr = fy W; λ = h/tw; λp = 3,76 sqrt(E/fy); λr = 5,70 sqrt(E/fy).
  - Nota 1:
    - β1 = (fy − σr) W / (E J)
    - λr = [1,38 sqrt(Iy J) / (ry J β1)] × sqrt(1 + sqrt(1 + 27 Cw β1² / Iy)), corroborado por S10
    - Mcr = (Cb π² E Iy / Lb²) × sqrt[(Cw/Iy)(1 + 0,039 J Lb² / Cw)]
    - Cw (I) = Iy (d − tf)² / 4
    - Cw (U) = tf (bf − 0,5tw)³ (d − tf)² / 12 × [3 (bf − 0,5tw) tf + 2 (d − tf) tw] / [6 (bf − 0,5tw) tf + (d − tf) tw]
  - Nota 6:
    - Laminados: Mcr = 0,69 E Wc / λ²; λr = 0,83 sqrt(E/(fy − σr))
    - Soldados: Mcr = 0,90 E kc Wc / λ²; λr = 0,95 sqrt(E/((fy − σr)/kc)), com kc de F.2
  - Nota 8, b de mesa: metade da largura em I/H; largura total em U; parte plana em tubo retangular; distância livre entre almas em caixão.
  - Nota 3, U: FLA só se aplica com a alma comprimida; FLM só com a extremidade livre das mesas comprimida.
  - **I/H e U, flexão no eixo de menor inércia:**
    - FLM: Mr = (fy − σr) W; λ = b/t; λp = 0,38 sqrt(E/fy); λr e Mcr pela Nota 6.
    - FLA (só alma de U): Mr = fy Wef; Mcr = (Wef²/W) fy; λ = h/tw; λp = 1,12 sqrt(E/fy); λr = 1,40 sqrt(E/fy).
    - Nota 7: não há FLT no eixo de menor inércia.
  - **Caixão e tubo retangular duplamente simétricos:**
    - FLT: Mr = (fy − σr) W; Mcr = 2,00 Cb E sqrt(J A) / λ; λ = Lb/ry; λp = 0,13 E sqrt(J A) / Mpl; λr = 2,00 E sqrt(J A) / Mr. Pela Nota 7, só no eixo de maior inércia.
    - FLM: Mr = fy Wef; Mcr = (Wef²/W) fy; λ = b/t; λp = 1,12 sqrt(E/fy); λr = 1,40 sqrt(E/fy).
    - FLA: Mr = fy W; λ = h/tw; λp = 2,42 sqrt(E/fy) (tubo retangular) ou 3,76 sqrt(E/fy) (caixão), pela Nota 10; λr = 5,70 sqrt(E/fy).
    - Wef (Nota 4): módulo com a mesa comprimida de largura bef (F.3.2, com σ = fy).
  - **G.2.7, tubo circular** (único estado-limite é a flambagem local da parede, com D/t ≤ 0,45 E/fy):
    - λ = D/t; λp = 0,07 E/fy; λr = 0,31 E/fy
    - λ ≤ λp: Mrd = Mpl/γa1
    - λp < λ ≤ λr: Mrd = (1/γa1) [0,021 E/(D/t) + fy] W
    - λ > λr: Mrd = (1/γa1) [0,33 E/(D/t)] W
  - G.1.2: o Anexo G vale para alma não esbelta (λ ≤ λr da FLA). Acima disso, Anexo H.

### 2.5 Força cortante (5.4.3, p. 49–52)

- **I, H e U fletidos no eixo perpendicular à alma** (5.4.3.1.1):
  - λ = h/tw; λp = 1,10 sqrt(kv E/fy); λr = 1,37 sqrt(kv E/fy)
  - λ ≤ λp: Vrd = Vpl/γa1
  - λp < λ ≤ λr: Vrd = (λp/λ) Vpl/γa1
  - λ > λr: Vrd = 1,24 (λp/λ)² Vpl/γa1
  - kv = 5,0 para alma sem enrijecedor transversal, ou a/h > 3, ou a/h > [260/(h/tw)]²
  - kv = 5 + 5/(a/h)² nos demais casos
  - h: distância entre faces internas das mesas (soldado); para laminado, desconta-se os 2 raios de concordância.
  - Vpl = 0,60 Aw fy, com Aw = d tw (5.4.3.1.2)
- **Tubo retangular e caixão** (5.4.3.2): mesmo procedimento, com kv = 5,0, h = parte plana da alma (tubo) e Aw = 2 h tw.
- **T** (5.4.3.3): kv = 1,2; h = d; Aw = d tw; d/tw ≤ 260.
- **Dupla cantoneira em T** (5.4.3.4): kv = 1,2; Aw = 2 b t; b/t ≤ 260.
- **I, H e U no eixo de menor inércia** (5.4.3.5): kv = 1,2; h = bf/2 (I, H) ou bf (U); tw = tf; Aw = 2 bf tf.
- **Tubo circular** (5.4.3.6):
  - Vrd = 0,5 τcr Ag / γa1, com τcr o maior entre:
    - τcr = 1,60 E / [sqrt(Lv/D) (D/td)^(5/4)] ≤ 0,60 fy
    - τcr = 0,78 E / (D/td)^(3/2) ≤ 0,60 fy
  - td = 0,93 t (tubo com costura) ou t (sem costura).
  - Lv = distância entre as seções de cortante máxima e nula.

### 2.6 Flexo-tração e flexo-compressão (5.5.1.2, p. 54–55)

- NSd/NRd ≥ 0,2: NSd/NRd + (8/9) (Mx,Sd/Mx,Rd + My,Sd/My,Rd) ≤ 1,0
- NSd/NRd < 0,2: NSd/(2 NRd) + (Mx,Sd/Mx,Rd + My,Sd/My,Rd) ≤ 1,0
- NRd vem de 5.2 (tração) ou 5.3 (compressão). MRd vem de 5.4.
- O cortante é verificado à parte por 5.4.3 (5.5.1.3).
- Os esforços solicitantes devem incluir os efeitos de 2ª ordem (Anexo D, método B1/B2, ou 4.9.7). O software deve receber esses esforços ou calculá-los.

### 2.7 Deslocamentos (Anexo C, Tabela C.1, p. 115–117)

| Elemento | Limite | Notas da tabela |
|---|---|---|
| Travessas de fechamento | L/180 (paralelo ao fechamento); L/120 (perpendicular) | Para L/120, considerar só o vento perpendicular ao fechamento, com valor característico. |
| Terças de cobertura | L/180; L/120 | L/180: combinação **rara**, com variáveis no mesmo sentido da permanente. L/120: só a variável de sentido oposto (sucção), característica. Evitar empoçamento. |
| Vigas de cobertura | L/250 | Evitar empoçamento. Com alvenaria solidarizada: também ≤ 15 mm. |
| Vigas de piso | L/350 | Idem, ≤ 15 mm com alvenaria. |
| Vigas que suportam pilares | L/500 | Idem. |
| Vigas de rolamento, vertical | L/600 (ponte < 200 kN); L/800 (≥ 200 kN, não siderúrgica); L/1000 (siderúrgica ≥ 200 kN) | Combinação **rara**; valor sem impacto. |
| Vigas de rolamento, horizontal | L/400; L/600 (siderúrgica) | Combinação rara. |
| Galpões e edifícios de 1 pavimento | Topo dos pilares em relação à base: H/300. Nível da viga de rolamento em relação à base: H/400. | Ponte siderúrgica: também ≤ 50 mm. Diferença entre pilares do pórtico: ≤ 15 mm. |
| Edifícios de 2 ou mais pavimentos | Topo em relação à base: H/400. Entre pisos consecutivos: h/500. | Interpavimento: só a parcela das forças cortantes do andar. |
| Lajes mistas | ver Anexo Q | |

L é o vão (ou 2× o balanço). H é a altura do pilar ou do nível da viga de rolamento. h é a altura do andar.

**Qual combinação usar (C.2.4):** o responsável técnico decide, exceto onde a Tabela C.1 indica (notas d, e, f, j). δmax normalmente está ligado à aparência e usa combinação **quase permanente**. Se afetar equipamentos ou causar empoçamento, usa-se **frequente**. Se houver dano a elementos sujeitos a fissuração (paredes, forros), usa-se **rara**. Pode-se descontar a contraflecha até o limite de δ1 (C.3.2). Para galpões com alvenaria, a abertura na base da parede deve ser ≤ 1,5 mm (C.3.4).

### 2.8 Aços (Anexo A, Tabelas A.1 e A.2, p. 108–109)

| Aço | fy (MPa) | fu (MPa) | Fonte |
|---|---|---|---|
| NBR 7007 MR 250 | 250 | 400–560 | Tabela A.1 |
| NBR 7007 AR 350 | 350 | 450 | Tabela A.1 |
| NBR 7007 AR 350 COR | 350 | 485 | Tabela A.1 |
| NBR 7007 AR 415 | 415 | 520 | Tabela A.1 |
| ASTM A36 (perfis grupos 1–3; chapas e barras t ≤ 200 mm) | 250 | 400 a 550 | Tabela A.2 |
| ASTM A572 Gr 50 (perfis grupos 1–3; chapas e barras t ≤ 100 mm) | 345 | 450 | Tabela A.2 |

Os valores de NBR 7007 são os que a NBR 8800:2008 transcreve. A Tabela A.1 manda ver a norma do aço para limitações de espessura.

### 2.9 Combinações na NBR 8800:2008 (4.7)

- **Tabela 1, γf**, para combinações normais / especiais ou de construção / excepcionais. Entre parênteses, o valor para efeito favorável.
  - Permanentes diretas:
    - Peso próprio de estruturas metálicas: 1,25 (1,00) / 1,15 (1,00) / 1,10 (1,00)
    - Pré-moldadas: 1,30 / 1,20 / 1,15
    - Moldadas no local, elementos construtivos industrializados e empuxos permanentes: 1,35 / 1,25 / 1,15
    - Industrializados com adições in loco: 1,40 / 1,30 / 1,20
    - Elementos construtivos em geral e equipamentos: 1,50 / 1,40 / 1,30
    - Favorável: sempre (1,00)
  - Indiretas: 1,20 (0) / 1,20 (0) / 0 (0)
  - Variáveis (γq):
    - Temperatura: 1,20 / 1,00 / 1,00
    - Vento: 1,40 / 1,20 / 1,00
    - Ações truncadas: 1,20 / 1,10 / 1,00
    - Demais, incluindo uso e ocupação: 1,50 / 1,30 / 1,00
  - Nota a: ações variáveis e excepcionais favoráveis não entram na combinação.
  - Nota b: a temperatura gerada por equipamentos conta como uso e ocupação.
  - Nota c: permanentes agrupadas nas normais: 1,35 se as ações de uso e ocupação forem > 5 kN/m², ou 1,40 caso contrário. Nas especiais: 1,25 e 1,30. Nas excepcionais: 1,15 e 1,20.
  - Nota d: se as permanentes forem agrupadas, as variáveis podem ser agrupadas com 1,50 (uso > 5 kN/m²) ou 1,40. A temperatura pode ficar isolada com seu próprio γ. Nas especiais: 1,30 e 1,20. Nas excepcionais: 1,00.
- **Tabela 2, ψ0 / ψ1 / ψ2** (p. 19):
  - Uso e ocupação, sem predominância de pesos fixos nem de concentração de pessoas (residencial de acesso restrito): 0,5 / 0,4 / 0,3
  - Com predominância (comercial, escritórios, acesso público): 0,7 / 0,6 / 0,4
  - Bibliotecas, arquivos, depósitos, oficinas, garagens **e sobrecargas em coberturas** (B.5.1): 0,8 / 0,7 / 0,6
  - Vento: 0,6 / 0,3 / 0
  - Temperatura (variação uniforme): 0,6 / 0,5 / 0,3
  - Passarelas: 0,6 / 0,4 / 0,3
  - Vigas de rolamento: 1,0 / 0,8 / 0,5
  - Pilares que suportam vigas de rolamento: 0,7 / 0,6 / 0,4
  - Notas: ψ1 = 1,0 na fadiga; ψ2 = 0 quando a ação principal é sismo.
- **Última normal** (4.7.7.2.1): Fd = Σ(γgi FGi,k) + γq1 FQ1,k + Σ(γqj ψ0j FQj,k). Na NBR 8800, cada variável secundária leva o seu próprio γqj.
- **Especial e de construção** (4.7.7.2.2 e 4.7.7.2.3): mesma forma, com ψ0j,ef. ψ0j,ef = ψ0j, ou ψ2j quando a ação especial atua por tempo muito pequeno.
- **Excepcional** (4.7.7.2.4): Fd = Σ(γgi FGi,k) + FQ,exc + Σ(γqj ψ0j,ef FQj,k).
- **Serviço** (4.7.7.3.2 a 4.7.7.3.4):
  - Quase permanente: Fser = Σ FGi,k + Σ ψ2j FQj,k
  - Frequente: Fser = Σ FGi,k + ψ1 FQ1,k + Σ(j≥2) ψ2j FQj,k
  - Rara: Fser = Σ FGi,k + FQ1,k + Σ(j≥2) ψ1j FQj,k

---

## 3. NBR 8681:2003, itens confirmados (fonte S2, edição "MAR 2003")

- **5.1.3.1 Combinação última normal** (p. 7): Fd = Σ(i=1..m) γgi FGi,k + γq [FQ1,k + Σ(j=2..n) ψ0j FQj,k]. Aqui há **um único γq**, que multiplica o colchete inteiro. Na NBR 8800 (item 2.9 acima), cada variável tem o seu γqj. Para uma mesma lista de ações, o resultado é igual quando todas as variáveis têm o mesmo γq. Com vento (1,4) e sobrecarga (1,5) juntos, a NBR 8800:2008 é explícita: use a forma dela no módulo de aço.
- **Tabela 1, permanentes diretas consideradas separadamente** (p. 9). Valores normal / especial ou de construção / excepcional; favorável 1,0 em todos.
  - Estruturas metálicas: 1,25 / 1,15 / 1,10
  - Pré-moldadas: 1,30 / 1,20 / 1,15
  - Moldadas no local: 1,35 / 1,25 / 1,15
  - Elementos construtivos industrializados: 1,35 / 1,25 / 1,15
  - Industrializados com adições in loco: 1,40 / 1,30 / 1,20
  - Elementos construtivos em geral e equipamentos: 1,50 / 1,40 / 1,30
- **Tabela 2, permanentes diretas agrupadas** (p. 9):
  - Grandes pontes: 1,30 / 1,20 / 1,10
  - Edificação tipo 1 (cargas acidentais > 5 kN/m²) e pontes em geral: 1,35 / 1,25 / 1,15
  - Edificação tipo 2 (≤ 5 kN/m²): 1,40 / 1,30 / 1,20
  - Favorável: 1,0
- **Tabela 3, recalques e retração** (p. 10): γ = 1,2 desfavorável nas combinações normal e especial; 0 nos favoráveis e na excepcional.
- **Tabela 4, variáveis separadas** (p. 10):
  - Normal: truncadas 1,2; temperatura 1,2; vento 1,4; variáveis em geral 1,5
  - Especial ou de construção: 1,1 / 1,0 / 1,2 / 1,3
  - Excepcional: 1,0
- **Tabela 5, variáveis em conjunto** (p. 10): normal 1,5 (pontes e edificação tipo 1) ou 1,4 (tipo 2); especial 1,3 ou 1,2; excepcional 1,0. O projetista escolhe entre a Tabela 4 e a Tabela 5.
- **5.1.4.3:** ação excepcional com γf = 1,0.
- **Tabela 6, ψ0 / ψ1 / ψ2** (p. 11):
  - Cargas acidentais de edifícios:
    - Residencial de acesso restrito: 0,5 / 0,4 / 0,3
    - Comercial, escritórios, acesso público: 0,7 / 0,6 / 0,4
    - Bibliotecas, arquivos, depósitos, oficinas e garagens: 0,8 / 0,7 / 0,6
  - Vento: 0,6 / 0,3 / 0
  - Temperatura: 0,6 / 0,5 / 0,3
  - Cargas móveis:
    - Passarelas: 0,6 / 0,4 / 0,3
    - Pontes rodoviárias: 0,7 / 0,5 / 0,3
    - Pontes ferroviárias não especializadas: 0,8 / 0,7 / 0,5
    - Pontes ferroviárias especializadas: 1,0 / 1,0 / 0,6
    - Vigas de rolamento: 1,0 / 0,8 / 0,5
  - Notas: ψ2 = 0 com sismo; ψ2 × 0,7 com fogo.
  - **Diferença em relação à NBR 8800:** a Tabela 2 da NBR 8800 inclui "sobrecargas em coberturas" na linha 0,8 / 0,7 / 0,6 e acrescenta "pilares que suportam vigas de rolamento" (0,7 / 0,6 / 0,4).
- **5.1.5, combinações de utilização** (p. 12):
  - Quase permanente: Fd,uti = Σ FGi,k + Σ(j=1..n) ψ2j FQj,k
  - Frequente: Fd,uti = Σ FGi,k + ψ1 FQ1,k + Σ(j=2..n) ψ2j FQj,k
  - Rara: Fd,uti = Σ FGi,k + FQ1,k + Σ(j=2..n) ψ1j FQj,k
  - São as mesmas formas da NBR 8800:2008, 4.7.7.3.

---

## 4. Tabela-resumo "Confirmado (fonte, item, URL)"

| # | Conteúdo | Item da norma | Fonte / URL |
|---|---|---|---|
| 1 | E = 200 GPa, G = 77 GPa, ν = 0,3; γa1 = 1,10 e γa2 = 1,35 (normais) | 4.5.2.9; Tabela 3 | S1 |
| 2 | Nt,Rd (escoamento e ruptura); Ae = Ct An; An = Ag sem furos; Ct; L/r ≤ 300 (recomendação) | 5.2.2, 5.2.3, 5.2.4.2, 5.2.5, 5.2.8 | S1; S10 (eq. 6–8, Ct = 1) |
| 3 | Nc,Rd; χ; λ0; KL/r ≤ 200; Ne (E.1.1–E.1.4); K (Tabela E.1, E.2.1.2, E.2.2); Q (Tabela F.1, F.2–F.4) | 5.3.2–5.3.4; Anexos E e F | S1; S10 (eq. 14–17, 22–25, kc) |
| 4 | Mrd FLT, FLM, FLA (I, U, tubos retangulares e circulares, menor eixo); Cb; limite 1,5 W fy/γa1 | 5.4.2.2–5.4.2.4; G.2.1, G.2.2, G.2.7; Tabela G.1 e notas | S1; S10 (Cb, λr FLT, tubo circular) |
| 5 | Vrd; kv; λp, λr; Vpl = 0,60 Aw fy; Aw por seção; tubo circular | 5.4.3.1–5.4.3.6 | S1; S10 (eq. 77–85) |
| 6 | Interação com NSd/NRd ≥ 0,2 e < 0,2 | 5.5.1.2 | S1 |
| 7 | Tabela C.1 e escolha da combinação de serviço | C.2.4, C.3, Tabela C.1 | S1 |
| 8 | fy/fu de MR250, AR350, A36 e A572 Gr50 | Tabelas A.1 e A.2 | S1 |
| 9 | γg, γq e ψ; combinação última normal | NBR 8800 Tabelas 1 e 2, 4.7.7.2.1; NBR 8681 5.1.3.1, Tabelas 1–6 | S1, S2 |
| 10 | Combinações de serviço | NBR 8800 4.7.7.3; NBR 8681 5.1.5 | S1, S2 |
| V | Vigência: NBR 8800 de 10/2024 (errata 02/2025) e NBR 8681 de 09/2025 são as vigentes | — | S3–S9 |

---

## 5. A CHECAR

1. **Radicais e frações.** A extração de texto não captura o traço do radical nem as barras de fração. As fórmulas abaixo foram montadas pela ordem dos símbolos e estão coerentes com a origem AISC 360-05, mas **não foram vistas graficamente**:
   - Tabela F.1 e Qs dos grupos 3 a 6 (sqrt(E/fy), sqrt(fy/E), kc = 4/sqrt(h/tw))
   - bef (F.3.2)
   - Mcr da Nota 1 (raiz externa)
   - Nota 6
   - τcr de tubo circular (sqrt(Lv/D), expoentes 5/4 e 3/2)
   - Expressões de Kx1 Lx1
   - Neyz e r0
   - Rm
   
   Já corroborados por S10: λ0, λp e λr do cortante, λr da FLT, λp de tubo retangular, χ e Cb.
   **Ação:** conferir visualmente nas páginas 44, 50, 121–129 e 134–136 de um exemplar legítimo.
2. **Tabela G.1, linhas "menor eixo (I/H/U)" e "caixão/tubo retangular".** A ordem das colunas (Mr, Mcr, λ, λp, λr) foi reconstruída a partir do texto extraído. Em particular: FLM de tubo com Mr = fy Wef e λp/λr = 1,12/1,40; FLA de U no menor eixo com 1,12/1,40; FLT de tubo com Mr = (fy − σr) W. Conferir visualmente a p. 134.
3. **Errata da NBR 8681 de 03/2004 e versão corrigida de 04/2004.** A cópia lida (S2) é "MAR 2003", sem a errata. Não sei o que a errata alterou. Pode afetar valores das Tabelas 1 a 6.
4. **Conteúdo da NBR 8800:2024 (versão corrigida 2025) e da NBR 8681:2025.** Não verifiquei nenhuma mudança de valor ou fórmula entre essas edições e as de 2008/2003. Isso é necessário se o software for usado em projeto novo.
5. **Cancelamento formal da NBR 8800:2008.** A Target mostra a edição de 10/2024 como "Vigente" e o histórico indica substituição. Não abri a página do catálogo oficial da ABNT (abntcatalogo.com.br). O mesmo vale para a NBR 8681:2003, substituída em 09/2025.
6. **NBR 7007.** Os valores acima são os transcritos na Tabela A.1 da NBR 8800:2008. Não conferi a NBR 7007 vigente nem as limitações de espessura de cada grau.
7. **Itens fora do escopo, não lidos:**
   - 5.2.5 e)/f): Ct de tubos com chapa de ligação
   - 5.2.6: barras ligadas por pinos
   - Tabela 4: valores tabelados de χ
   - Anexo H: alma esbelta
   - 5.5.2: torção
   - Anexo D: B1 e B2 (lido só o início)
   - 4.9: análise de 2ª ordem e imperfeições
   - 5.1.2: classificação AA/AL (lido só 5.1.2.2.4)
8. **Divergência de data da NBR 8800:2024.** Um artigo de congresso diz abril de 2024. CBIC e ABECE dizem 02/10/2024. Adotei 02/10/2024.
9. **Não verificados em Pfeil & Pfeil, Fakury et al. nem em manual do CBCA.** Não encontrei cópias legítimas acessíveis. A confirmação foi feita direto no texto da norma (S1, S2), com corroboração parcial em S10.
