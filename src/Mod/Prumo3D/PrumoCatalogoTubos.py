# SPDX-License-Identifier: LGPL-2.1-or-later
"""Catálogo de tubos e conexões para o comando Tubulação.

Cada linha (sistema) traz as medidas que o traçado automático precisa, em mm:

- tubos: De (diâmetro externo), e (espessura), bolsa_tubo (bolsa da barra ponta-bolsa).
- bolsa: profundidade da bolsa soldável das conexões (quanto o tubo entra).
- corpo: diâmetro externo do corpo das conexões (para o desenho).
- joelho90 / joelho45 / te / cruzeta: distância do centro da conexão até a face da bolsa.
- te_reducao: (D, d) -> (A, B): A comprimento total no eixo principal, B centro até a face do ramal.
- bucha_curta / bucha_longa / luva_reducao: (D, d) -> comprimento A.
- luva: comprimento total A.

As medidas vêm do catálogo do fabricante indicado em "fonte". Itens marcados em "a_conferir" saíram com
valor duvidoso na tabela de origem (erro de impressão provável): o traçado usa e avisa.
"""

TIGRE_SOLDAVEL = {
    "id": "pvc-soldavel-af",
    "nome": "PVC soldável água fria (marrom)",
    "material": "PVC rígido",
    "fabricante": "Tigre",
    "fonte": "Tigre, Catálogo Técnico Predial Água Fria (fev/2008), Linha Soldável, p. 08–15. O Catálogo "
             "Predial 2025 (TG1.386-25) e o Manual Técnico 2025 trazem só códigos e bitolas, sem as cotas",
    "norma": "ABNT NBR 5648:2018 – Tubos e conexões de PVC-U com junta soldável para sistemas prediais de "
             "água fria – Requisitos (publicada em 19/12/2018, em vigor, confirmada em 13/12/2023 e em revisão "
             "pela ABNT; conferido no catálogo ABNT em 22/10/2026)",
    "pressao": "Tubos 7,5 kgf/cm² (75 m.c.a.) a 20 °C; conexões 20–50 mm 75 m.c.a., 60–110 mm 100 m.c.a.",
    "temperatura_max": "20 °C",
    "cor": (0.55, 0.36, 0.20),
    "barra": 6000.0,
    "diametros": (20, 25, 32, 40, 50, 60, 75, 85, 110),
    "tubos": {
        20: {"De": 20.0, "e": 1.5, "bolsa_tubo": 32.0},
        25: {"De": 25.0, "e": 1.7, "bolsa_tubo": 32.0},
        32: {"De": 32.0, "e": 2.1, "bolsa_tubo": 32.0},
        40: {"De": 40.0, "e": 2.4, "bolsa_tubo": 40.0},
        50: {"De": 50.0, "e": 3.0, "bolsa_tubo": 50.0},
        60: {"De": 60.0, "e": 3.3, "bolsa_tubo": 60.0},
        75: {"De": 75.0, "e": 4.2, "bolsa_tubo": 70.0},
        85: {"De": 85.0, "e": 4.7, "bolsa_tubo": 77.0},
        110: {"De": 110.0, "e": 6.1, "bolsa_tubo": 91.0},
    },
    # profundidade da bolsa das conexões: cota A do cap soldável (p. 10), que coincide com a cota B da
    # cruzeta, com a bucha curta e com a cota L (bolsa) do registro de esfera VS soldável (p. 41)
    "bolsa": {20: 16.0, 25: 18.5, 32: 22.0, 40: 26.0, 50: 31.0, 60: 36.0, 75: 43.5, 85: 48.5, 110: 58.8},
    # diâmetro externo do corpo: cota D3 do cap soldável (p. 10)
    "corpo": {20: 28.5, 25: 34.0, 32: 43.0, 40: 52.0, 50: 63.0, 60: 76.0, 75: 95.0, 85: 104.4, 110: 134.9},
    # Joelho 90° soldável (p. 12): na tabela as linhas A e D saíram trocadas; A é a coluna 27…124
    "joelho90": {20: 27.0, 25: 32.0, 32: 39.0, 40: 47.0, 50: 57.0, 60: 67.0, 75: 87.2, 85: 97.7, 110: 124.0},
    # Joelho 45° soldável (p. 11): idem, A é a coluna 22,3…85,5
    "joelho45": {20: 22.3, 25: 24.5, 32: 29.5, 40: 35.5, 50: 42.5, 60: 49.5, 75: 60.0, 85: 67.5, 110: 85.5},
    # Tê soldável (p. 14): cota B (centro até a face)
    "te": {20: 27.0, 25: 32.0, 32: 39.0, 40: 47.0, 50: 57.0, 60: 71.3, 75: 87.2, 85: 97.7, 110: 124.0},
    # Cruzeta soldável (p. 10): cota A. A tabela de 2008 chama a primeira de "20", mas a mesma linha traz
    # D = 25, B = 18,5 (bolsa de 25) e o código 22090259, que no Catálogo Predial 2022 é a cruzeta de 25 mm
    # (lá só existem 25 e 50): é a de 25
    "cruzeta": {25: 32.0, 50: 57.0},
    # Luva soldável (p. 13): comprimento total A
    "luva": {20: 35.0, 25: 42.0, 32: 48.0, 40: 56.0, 50: 67.0, 60: 80.0, 75: 102.0, 85: 102.0, 110: 130.0},
    # Tê de redução soldável (p. 14): (A, B)
    "te_reducao": {
        (25, 20): (63.0, 31.0), (32, 25): (78.0, 39.0), (40, 25): (86.2, 41.9), (40, 32): (86.0, 43.0),
        (50, 20): (117.0, 51.0), (50, 25): (117.0, 52.0), (50, 32): (117.0, 53.0), (50, 40): (117.0, 59.0),
        (60, 25): (108.4, 51.7), (75, 50): (151.0, 79.0), (75, 60): (176.0, 81.7), (85, 60): (187.0, 90.0),
        (110, 60): (228.6, 109.0), (110, 75): (210.0, 104.0),
    },
    # Bucha de redução soldável curta (p. 10): fica toda dentro da bolsa maior
    "bucha_curta": {
        (25, 20): 18.5, (32, 25): 22.0, (40, 32): 26.0, (50, 40): 31.0, (60, 50): 36.0, (75, 60): 43.5,
        (85, 75): 48.5, (110, 85): 49.0,
    },
    # Bucha de redução soldável longa (p. 10)
    "bucha_longa": {
        (32, 20): 44.0, (40, 20): 51.6, (40, 25): 51.8, (50, 20): 55.8, (50, 25): 65.0, (50, 32): 61.3,
        (60, 25): 70.5, (60, 32): 70.9, (60, 40): 71.3, (60, 50): 71.8, (75, 50): 86.0, (85, 60): 95.1,
        (110, 60): 140.0, (110, 75): 130.0,
    },
    # Luva de redução soldável (p. 13): comprimento total A
    "luva_reducao": {
        (25, 20): 41.0, (32, 25): 53.0, (40, 32): 68.0, (50, 25): 65.2, (60, 50): 72.5, (75, 60): 91.8,
        (110, 75): 132.0,
    },
    # Cap soldável (p. 10): comprimento A
    "cap": {20: 16.0, 25: 18.5, 32: 22.0, 40: 26.0, 50: 31.0, 60: 36.0, 75: 43.5, 85: 48.5, 110: 58.8},
    # Registro esfera VS soldável (p. 41): A comprimento total, L bolsa, E diâmetro do corpo, B altura,
    # C comprimento da alavanca
    "registro": {
        20: {"A": 74.0, "bolsa": 16.0, "corpo": 50.0, "altura": 56.0, "alavanca": 76.0},
        25: {"A": 87.9, "bolsa": 18.5, "corpo": 61.0, "altura": 64.0, "alavanca": 80.0},
        32: {"A": 99.5, "bolsa": 22.0, "corpo": 68.0, "altura": 70.0, "alavanca": 90.0},
        40: {"A": 118.6, "bolsa": 26.0, "corpo": 83.0, "altura": 74.0, "alavanca": 110.0},
        50: {"A": 138.2, "bolsa": 31.0, "corpo": 96.0, "altura": 96.5, "alavanca": 140.0},
        60: {"A": 165.1, "bolsa": 36.0, "corpo": 115.0, "altura": 107.0, "alavanca": 170.0},
    },
    # massa específica do composto de PVC (para massa dos tubos e conexões)
    "densidade": 1430.0,    # kg/m³
    "fonte_densidade": "Tigre, Ficha Técnica Tubería y Accesorios de PVC Línea Soldable (mai/2021): "
                        "\"peso específico del compuesto: 1,43 g/cm³\" (ficha da Tigre fora do Brasil; o catálogo "
                        "brasileiro não informa)",
    # Pontos de uso (p. 12–14): peças com bucha de latão para rosquear torneira, registro ou chuveiro.
    # Tê soldável e com bucha de latão na bolsa central (p. 14): A comprimento total, B centro até a face da
    # bolsa com rosca
    "te_bucha": {20: {"A": 54.0, "B": 27.0, "rosca": '1/2"'}, 25: {"A": 59.0, "B": 30.5, "rosca": '1/2"'},
                 32: {"A": 72.0, "B": 35.5, "rosca": '3/4"'}},
    # Joelho 90° soldável e com bucha de latão (p. 12): A centro até a face (as duas pernas)
    "joelho_bucha": {20: {"A": 27.0, "rosca": '1/2"'}, 25: {"A": 31.0, "rosca": '1/2"'},
                     32: {"A": 37.0, "rosca": '3/4"'}},
    # Luva soldável e com bucha de latão (p. 13): A comprimento total (o tubo entra na bolsa de um lado)
    "luva_bucha": {20: {"A": 31.0, "rosca": '1/2"'}, 25: {"A": 36.0, "rosca": '1/2"'},
                   32: {"A": 47.6, "rosca": '1"'}},
    # Três linhas da tabela de 2008 vinham com erro de impressão (bucha curta 110 × 85 com A = 31; bucha longa
    # 50 × 25 com A = 31; bucha longa 75 × 50 repetindo a linha 85 × 60). Trocadas pelo comprimento da ficha do
    # produto Tigre no varejo (Telhanorte, consultado em 25/10/2026: 4,9 cm, 6,5 cm e 8,6 cm), que confere com o
    # catálogo nas peças vizinhas (curta 85 × 75: 4,9 cm × 48,5 mm; curta 60 × 50: 3,6 cm × 36 mm; longa
    # 50 × 32: 6,1 cm × 61,3 mm; longa 60 × 50: 7,2 cm × 71,8 mm).
    "a_conferir": {},
}

TIGRE_SOLDAVEL.setdefault("sufixo", "soldável")

# Esgoto: ABNT NBR 8160:1999 – Sistemas prediais de esgoto sanitário – Projeto e execução (publicada em
# 30/09/1999, em vigor, confirmada em 26/05/2022; conferido no catálogo ABNT em 25/10/2026).
#   4.2.3.2: declividades mínimas recomendadas: 2 % para DN ≤ 75; 1 % para DN ≥ 100.
#   4.2.5.2: declividade constante; máxima a considerar 5 %.
#   4.2.3.3: mudanças de direção nos trechos horizontais com peças de ângulo central ≤ 45°.
#   4.2.3.4: de horizontal para vertical (e vice-versa), peças com ângulo central ≤ 90°.
NBR8160 = "ABNT NBR 8160:1999 (em vigor, confirmada em 26/05/2022)"


def declividade_minima(dn):
    """Declividade mínima recomendada (fração), NBR 8160:1999 item 4.2.3.2."""
    return 0.02 if dn <= 75 else 0.01


DECLIVIDADE_MAXIMA = 0.05       # NBR 8160:1999 item 4.2.5.2


TIGRE_ESGOTO = {
    "id": "pvc-esgoto-sn",
    "nome": "PVC esgoto série normal (branco)",
    "material": "PVC rígido",
    "fabricante": "Tigre",
    "sufixo": "esgoto série normal",
    "rotulo_dn": "DN %d",
    "esgoto": True,
    "tol_ang": 3.5,            # o caimento (até 5 %) entorta os ângulos em até ~3°
    "fonte": "Tigre, Catálogo Técnico Predial Esgoto (fev/2008), Série Normal, p. 09–15",
    "norma": NBR8160 + "; tubos e conexões: ABNT NBR 5688:2018 (publicada em 19/12/2018, em vigor, confirmada em "
                       "13/12/2023 e em revisão pela ABNT; conferido no catálogo ABNT em 25/10/2026)",
    "pressao": "Escoamento por gravidade",
    "temperatura_max": "—",
    "cor": (0.93, 0.93, 0.92),
    "barra": 6000.0,
    "diametros": (40, 50, 75, 100, 150, 200),
    # Tubo série normal (p. 09): D externo, e parede, B bolsa da barra
    "tubos": {
        40: {"De": 40.0, "e": 1.2, "bolsa_tubo": 26.0},
        50: {"De": 50.7, "e": 1.6, "bolsa_tubo": 42.0},
        75: {"De": 75.5, "e": 1.7, "bolsa_tubo": 48.0},
        100: {"De": 101.6, "e": 1.8, "bolsa_tubo": 55.0},
        150: {"De": 150.0, "e": 2.5, "bolsa_tubo": 73.0},
        200: {"De": 200.0, "e": 3.6, "bolsa_tubo": 77.0},
    },
    # bolsa das conexões: cota B da luva simples (p. 13), igual à B da junção simples (p. 12)
    "bolsa": {40: 18.0, 50: 39.0, 75: 44.0, 100: 50.0, 150: 67.0, 200: 77.0},
    # corpo para o desenho: D da luva de correr (p. 13) + 2 paredes de conexão (aproximado)
    "corpo": {40: 46.0, 50: 58.0, 75: 84.0, 100: 111.0, 150: 162.0, 200: 213.0},
    # Joelho 90° série normal (p. 10): A, centro até a face da bolsa (confere com C + B)
    "joelho90": {40: 39.0, 50: 70.6, 75: 90.0, 100: 110.0, 150: 144.0, 200: 233.0},
    # Joelho 45° série normal (p. 10): a tabela vem com os rótulos B, D, e, L no lugar de A, B, C, D. A 1ª linha
    # é o centro até a face: descontada a bolsa, sobra 0,41 (tan 22,5°) do recuo do joelho 90°, como manda a
    # geometria (DN 150: 67 + 0,41 × 77 = 99 contra 101,3). Só o DN 200 (198) foge da conta (daria ~142).
    "joelho45": {40: 27.5, 50: 57.6, 75: 68.7, 100: 81.4, 150: 101.3, 200: 198.0},
    # Tê série normal (p. 12): metade de H (comprimento total) na linha principal; B, centro até a face, no
    # ramal (no DN 40 as três valem 39, igual ao joelho 90°; B como comprimento sem a bolsa daria o ramal maior
    # que a linha, o que não existe nas peças pequenas)
    "te": {40: 39.0, 50: 76.0, 75: 97.25, 100: 120.5, 150: 165.0, 200: 220.0},
    "te_ramal": {40: 39.0, 50: 84.6, 75: 109.8, 100: 137.6, 150: 182.5, 200: 188.0},
    "cruzeta": {},
    # Luva simples (p. 13): comprimento total A
    "luva": {40: 39.0, 50: 62.0, 75: 72.2, 100: 83.5, 150: 128.0, 200: 157.0},
    "te_reducao": {},
    "bucha_curta": {},
    "bucha_longa": {},
    # Redução excêntrica (p. 14): comprimento total A
    "luva_reducao": {(75, 50): 108.5, (100, 50): 130.5, (100, 75): 122.0, (150, 100): 148.9, (200, 150): 163.5},
    # Cap (p. 15): comprimento A
    "cap": {40: 18.0, 50: 39.0, 75: 44.0, 100: 50.0, 150: 67.0, 200: 103.0},
    # Junção simples série normal (p. 12): (D, d) -> (A, C, c). A comprimento total da linha principal, C da
    # face de saída (jusante) até o encontro dos eixos, c do encontro até o FUNDO da bolsa do ramal. Prova: nas
    # junções de diâmetros iguais, montante (A − C) = c + bolsa, como pede a geometria da junção a 45°
    # (40: 68 = 50 + 18; 50: 103 = 64 + 39; 75: 138,5 = 94,5 + 44; 100: 179 = 129 + 50; 150: 252 = 185 + 67).
    # A 200 × 200 não fecha (408 contra 262): provável erro de impressão.
    "juncao": {(40, 40): (95.0, 27.0, 50.0), (50, 50): (159.5, 56.5, 64.0), (75, 50): (172.0, 50.0, 79.5),
               (75, 75): (206.5, 68.0, 94.5), (100, 50): (185.0, 44.5, 100.0), (100, 75): (219.6, 61.6, 110.5),
               (100, 100): (259.0, 80.0, 129.0), (150, 100): (282.0, 66.0, 164.0), (150, 150): (351.0, 99.0, 185.0),
               (200, 200): (523.0, 115.0, 185.0)},
    # Caixas (p. 37, 38 e 57). O catálogo não dá legenda das letras: D/D1 é o diâmetro do corpo, A a altura, D2
    # a saída e D3 a entrada. Conferido: nas sifonadas o nome traz as mesmas medidas (100 × 100, 150 × 185), e a
    # ficha Tigre atual (AECweb, 25/10/2026) dá a caixa de gordura com 558 × 300 mm, entrada DN 50 e saída
    # DN 100, e a de inspeção com 218 × 300 mm: diâmetro ~300 e altura, como aqui (modelos de outra edição).
    "caixas": {
        "sifonada_100": {"nome": "Caixa sifonada 100 × 100 × 50", "D": 101.6, "A": 100.0, "saida": 50,
                         "entrada": 40},
        "sifonada_150": {"nome": "Caixa sifonada 150 × 150 × 50", "D": 144.8, "A": 155.0, "saida": 50,
                         "entrada": 40},
        "sifonada_150_75": {"nome": "Caixa sifonada 150 × 185 × 75", "D": 147.0, "A": 185.0, "saida": 75,
                            "entrada": 40},
        "inspecao": {"nome": "Caixa de inspeção", "D": 302.0, "A": 240.0, "saida": 100, "entrada": 100},
        "gordura": {"nome": "Caixa de gordura", "D": 312.0, "A": 591.0, "saida": 100, "entrada": 50},
    },
    "a_conferir": {
        ("joelho45", 200): "joelho 45° DN 200: o catálogo dá 198 mm, fora da geometria das outras bitolas (~142)",
        ("juncao", (200, 200)): "junção 200 × 200: as cotas do catálogo não fecham entre si (provável erro de "
                                "impressão)",
    },
}

_AQ = (15, 22, 28, 35, 42, 54, 73, 89, 114)
TIGRE_AQUATHERM = {
    "id": "cpvc-aquatherm",
    "nome": "CPVC Aquatherm água quente (bege)",
    "material": "CPVC",
    "fabricante": "Tigre",
    "sufixo": "Aquatherm",
    "fonte": "Tigre, Aquatherm® Catálogo Técnico Predial (TG-135-11, mai/2011), p. 21–25",
    "norma": "ABNT NBR 15884-1:2010 Versão Corrigida:2011 (tubos; publicada em 21/10/2010, confirmada em "
             "08/12/2023) e ABNT NBR 15884-2:2011 (conexões; publicada em 27/10/2011, confirmada em 02/05/2024), "
             "ambas em vigor e em revisão pela ABNT; conferido no catálogo ABNT em 25/10/2026",
    "pressao": "ver catálogo Aquatherm",
    "temperatura_max": "ver catálogo Aquatherm",
    "cor": (0.93, 0.87, 0.72),
    "barra": 3000.0,
    "diametros": _AQ,
    # Tubo Aquatherm (p. 21): DE e parede e
    "tubos": {d: {"De": De, "e": e, "bolsa_tubo": 0.0} for d, De, e in (
        (15, 15.0, 1.6), (22, 22.0, 2.0), (28, 28.0, 2.5), (35, 34.9, 3.2), (42, 41.3, 3.8), (54, 54.0, 4.9),
        (73, 73.0, 6.5), (89, 88.9, 7.9), (114, 114.3, 10.2))},
    # bolsa: cota B da luva e do joelho (p. 22)
    "bolsa": dict(zip(_AQ, (13.0, 18.0, 23.0, 28.0, 33.0, 43.0, 44.4, 47.6, 58.7))),
    "corpo": dict(zip(_AQ, (19.0, 27.0, 34.0, 42.0, 50.0, 64.0, 84.0, 101.0, 128.0))),   # aproximado, só desenho
    # Joelho 90° (p. 22): A centro até a face; igual à cota C do tê (p. 23)
    "joelho90": dict(zip(_AQ, (23.0, 31.0, 39.0, 47.0, 55.0, 72.0, 82.6, 93.6, 115.8))),
    # Joelho 45° (o catálogo de 2011 repete a tabela do joelho 90°): cota A da página do produto no site da
    # Tigre (consultada em 25/10/2026). Nas bitolas 35, 42 e 54 o site dá 64, 75 e 98, maiores que o centro até
    # a face do próprio joelho 90° (47, 55, 72): não pode ser o centro até a face. Nessas três fica a estimativa
    # pela geometria das outras bitolas (bolsa + 1,2 × raio × tan 22,5°), marcada a conferir.
    "joelho45": dict(zip(_AQ, (18.0, 24.0, 30.0, 37.0, 43.0, 56.0, 61.9, 66.7, 84.1))),
    # Tê (p. 23): C centro até a face (A = 2C)
    "te": dict(zip(_AQ, (23.0, 31.0, 39.0, 47.0, 55.0, 72.0, 82.5, 93.6, 117.4))),
    "cruzeta": {},
    # Luva (p. 22): comprimento total A
    "luva": dict(zip(_AQ, (29.0, 39.0, 49.0, 59.0, 69.0, 89.0, 93.7, 100.1, 122.2))),
    "te_reducao": {},
    "bucha_curta": {},
    "bucha_longa": {},
    "luva_reducao": {},
    # Cap (p. 23): A
    "cap": dict(zip(_AQ, (13.0, 18.0, 23.0, 28.0, 33.0, 43.0, 44.4, 47.6, 58.7))),
    # Pontos de uso: joelho 90° de transição (p. 24): A; conector (p. 24): B comprimento
    # joelho de transição conferido no site da Tigre (25/10/2026): A = 27; 30,5; 38,3
    "joelho_bucha": {15: {"A": 27.0, "rosca": '1/2"'}, 22: {"A": 30.5, "rosca": '1/2"'},
                     28: {"A": 38.3, "rosca": '1"'}},
    # conector: comprimento total da ficha do produto no varejo (Telhanorte, 25/10/2026): 15 × 1/2" 4,6 cm;
    # 22 × 1/2" 5,6 cm. O 28 × 1" não tem a medida publicada: fica a cota do catálogo, a conferir.
    "luva_bucha": {15: {"A": 46.0, "rosca": '1/2"'}, 22: {"A": 56.0, "rosca": '1/2"'},
                   28: {"A": 64.0, "rosca": '1"'}},
    "nome_luva_bucha": "Conector Aquatherm %d × %s",
    "nome_joelho_bucha": "Joelho 90° de transição Aquatherm %d × %s",
    "a_conferir": dict([(("joelho45", d), "joelho 45° Aquatherm %d: o site da Tigre dá uma cota maior que a do "
                                          "joelho 90°; usada estimativa pela geometria" % d) for d in (35, 42, 54)]
                       + [(("luva_bucha", 28), "conector 28 × 1\": comprimento total não publicado pela Tigre")]),
}

LINHAS = {TIGRE_SOLDAVEL["id"]: TIGRE_SOLDAVEL, TIGRE_AQUATHERM["id"]: TIGRE_AQUATHERM,
          TIGRE_ESGOTO["id"]: TIGRE_ESGOTO}
PADRAO = TIGRE_SOLDAVEL["id"]


def linha(lid):
    return LINHAS.get(lid) or LINHAS[PADRAO]


def a_conferir(L, chave, k):
    """Motivo, se a medida (chave, k) da linha está marcada como a conferir; senão None."""
    return (L.get("a_conferir") or {}).get((chave, k))


def nomes():
    return [(lid, l["nome"] + " — " + l["fabricante"]) for lid, l in LINHAS.items()]
