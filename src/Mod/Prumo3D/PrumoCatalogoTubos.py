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
    "nomes": {"luva_reducao": "Redução {suf} {D} × {d}"},
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

# ============================================================== aço carbono, solda de topo (ASME)
# Medidas conferidas em duas fontes independentes em 29/10/2026 (ver "fonte" das linhas). Diâmetros pelo DN
# (mm) com a polegada (NPS) ao lado.
NPS = {15: "1/2", 20: "3/4", 25: "1", 32: "1-1/4", 40: "1-1/2", 50: "2", 65: "2-1/2", 80: "3", 100: "4",
       150: "6", 200: "8", 250: "10", 300: "12"}
_DN_ACO = tuple(NPS)

# ASME B36.10M: DE, parede SCH 40 e SCH 80 (mm) e massa (kg/m)
_B3610 = {   # DN: (DE, e40, kg/m 40, e80, kg/m 80)
    15: (21.3, 2.77, 1.27, 3.73, 1.62), 20: (26.7, 2.87, 1.69, 3.91, 2.20), 25: (33.4, 3.38, 2.50, 4.55, 3.24),
    32: (42.2, 3.56, 3.39, 4.85, 4.47), 40: (48.3, 3.68, 4.05, 5.08, 5.41), 50: (60.3, 3.91, 5.44, 5.54, 7.48),
    65: (73.0, 5.16, 8.63, 7.01, 11.41), 80: (88.9, 5.49, 11.29, 7.62, 15.27),
    100: (114.3, 6.02, 16.07, 8.56, 22.32), 150: (168.3, 7.11, 28.26, 10.97, 42.56),
    200: (219.1, 8.18, 42.55, 12.70, 64.64), 250: (273.1, 9.27, 60.31, 15.09, 96.01),
    300: (323.9, 10.31, 79.73, 17.48, 132.1)}

# ASME B16.9 (raio longo): A curva 90°, B curva 45°, C tê (centro à ponta; ramal M = C no tê reto),
# cap E (parede até o limite) e E1 (parede maior), parede-limite do cap
_B169 = {    # DN: (A, B, C, E, E1, limite)
    15: (38, 16, 25, 25, 25, 4.57), 20: (38, 19, 29, 25, 25, 3.81), 25: (38, 22, 38, 38, 38, 4.57),
    32: (48, 25, 48, 38, 38, 4.83), 40: (57, 29, 57, 38, 38, 5.08), 50: (76, 35, 64, 38, 44, 5.59),
    65: (95, 44, 76, 38, 51, 7.11), 80: (114, 51, 86, 51, 64, 7.62), 100: (152, 64, 105, 64, 76, 8.64),
    150: (229, 95, 143, 89, 102, 10.92), 200: (305, 127, 178, 102, 127, 12.70),
    250: (381, 159, 216, 127, 152, 12.70), 300: (457, 190, 254, 152, 178, 12.70)}
# tê de redução B16.9: (DN da linha, DN do ramal) -> (C, M)
_TE_RED = {
    (20, 15): (29, 29), (25, 20): (38, 38), (25, 15): (38, 38), (32, 25): (48, 48), (32, 20): (48, 48),
    (40, 32): (57, 57), (40, 25): (57, 57), (40, 20): (57, 57), (50, 40): (64, 60), (50, 32): (64, 57),
    (50, 25): (64, 51), (65, 50): (76, 70), (65, 40): (76, 67), (65, 32): (76, 64), (80, 65): (86, 83),
    (80, 50): (86, 76), (80, 40): (86, 73), (100, 80): (105, 98), (100, 65): (105, 95), (100, 50): (105, 89),
    (150, 100): (143, 130), (150, 80): (143, 124), (200, 150): (178, 168), (200, 100): (178, 156),
    (250, 200): (216, 203), (250, 150): (216, 194), (300, 250): (254, 241), (300, 200): (254, 229)}
# redução concêntrica B16.9: (maior, menor) -> H (ponta a ponta)
_RED_H = {
    (20, 15): 38, (25, 20): 51, (25, 15): 51, (32, 25): 51, (32, 20): 51, (40, 32): 64, (40, 25): 64,
    (50, 40): 76, (50, 32): 76, (65, 50): 89, (65, 40): 89, (80, 65): 89, (80, 50): 89, (100, 80): 102,
    (100, 65): 102, (150, 100): 140, (150, 80): 140, (200, 150): 152, (200, 100): 152, (250, 200): 178,
    (250, 150): 178, (300, 250): 203, (300, 200): 203}

# ASME B16.5, flange de pescoço (WN) face com ressalto (RF), valores métricos da edição atual. tf e Y não
# incluem o ressalto de 2 mm (B16.5-2003 6.4.1 e prefácio da B16.5-2017). Estojo: comprimento para face com
# ressalto e junta espiralada de 4,5 mm.
_WN = {   # classe: {DN: (O, tf, X, A, Y, D_ressalto, círculo de furação, furos, estojo pol, estojo mm)}
    150: {15: (90, 9.6, 30, 21.3, 46, 34.9, 60.3, 4, "1/2", 55), 20: (100, 11.2, 38, 26.7, 51, 42.9, 69.9, 4, "1/2", 65),
          25: (110, 12.7, 49, 33.4, 54, 50.8, 79.4, 4, "1/2", 65), 32: (115, 14.3, 59, 42.2, 56, 63.5, 88.9, 4, "1/2", 70),
          40: (125, 15.9, 65, 48.3, 60, 73.0, 98.4, 4, "1/2", 70), 50: (150, 17.5, 78, 60.3, 62, 92.1, 120.7, 4, "5/8", 85),
          65: (180, 20.7, 90, 73.0, 68, 104.8, 139.7, 4, "5/8", 90), 80: (190, 22.3, 108, 88.9, 68, 127.0, 152.4, 4, "5/8", 90),
          100: (230, 22.3, 135, 114.3, 75, 157.2, 190.5, 8, "5/8", 90),
          150: (280, 23.9, 192, 168.3, 87, 215.9, 241.3, 8, "3/4", 100),
          200: (345, 27.0, 246, 219.1, 100, 269.9, 298.5, 8, "3/4", 110),
          250: (405, 28.6, 305, 273.0, 100, 323.8, 362.0, 12, "7/8", 115),
          300: (485, 30.2, 365, 323.8, 113, 381.0, 431.8, 12, "7/8", 120)},
    300: {15: (95, 12.7, 38, 21.3, 51, 34.9, 66.7, 4, "1/2", 65), 20: (115, 14.3, 48, 26.7, 56, 42.9, 82.6, 4, "5/8", 75),
          25: (125, 15.9, 54, 33.4, 60, 50.8, 88.9, 4, "5/8", 75), 32: (135, 17.5, 64, 42.2, 64, 63.5, 98.4, 4, "5/8", 85),
          40: (155, 19.1, 70, 48.3, 67, 73.0, 114.3, 4, "3/4", 90), 50: (165, 20.7, 84, 60.3, 68, 92.1, 127.0, 8, "5/8", 90),
          65: (190, 23.9, 100, 73.0, 75, 104.8, 149.2, 8, "3/4", 100), 80: (210, 27.0, 117, 88.9, 78, 127.0, 168.3, 8, "3/4", 110),
          100: (255, 30.2, 146, 114.3, 84, 157.2, 200.0, 8, "3/4", 115),
          150: (320, 35.0, 206, 168.3, 97, 215.9, 269.9, 12, "3/4", 120),
          200: (380, 39.7, 260, 219.1, 110, 269.9, 330.2, 12, "7/8", 140),
          250: (445, 46.1, 321, 273.0, 116, 323.8, 387.4, 16, "1", 160),
          300: (520, 49.3, 375, 323.8, 129, 381.0, 450.8, 16, "1-1/8", 170)}}
# ASME B16.10-2022, válvulas de aço flangeadas RF: face a face (mm), com o ressalto incluído. Conferido em
# wermac.org e projectmaterials.com (iguais célula a célula); Milwaukee Valve e Dongsan Valve confirmam de
# DN 50 para cima. Retenção portinhola classe 150 DN 150 = 356 (nota da tabela; uma fonte dá 406, a do globo).
# Esfera: padrão curto (passagem reduzida), que é o mais comum; a passagem plena usa o padrão longo.
_FF = {
    "gaveta": {150: (108, 117, 127, 140, 165, 178, 190, 203, 229, 267, 292, 330, 356),
               300: (140, 152, 165, 178, 190, 216, 241, 282, 305, 403, 419, 457, 502)},
    "globo": {150: (108, 117, 127, 140, 165, 203, 216, 241, 292, 406, 495, 622, 698),
              300: (152, 178, 203, 216, 229, 267, 292, 318, 356, 444, 559, 622, 711)},
    "retencao": {150: (108, 117, 127, 140, 165, 203, 216, 241, 292, 356, 495, 622, 698),
                 300: (None, None, 216, 229, 241, 267, 292, 318, 356, 444, 533, 622, 711)},
    "esfera": {150: (108, 117, 127, 140, 165, 178, 190, 203, 229, 267, 292, 330, 356),
               300: (140, 152, 165, 178, 190, 216, 241, 282, 305, 403, 419, 457, 502)},
}
# altura do centro ao topo (aberta) e diâmetro do volante, classe 150 (Milwaukee Valve): só para o desenho
_ALTURA = {"gaveta": {50: (455, 200), 65: (494, 200), 80: (553, 250), 100: (633, 250), 150: (827, 300),
                      200: (1015, 350), 250: (1211, 450), 300: (1411, 500)},
           "globo": {50: (383, 200), 65: (436, 250), 80: (456, 250), 100: (531, 300), 150: (583, 350),
                     200: (670, 400)}}
NOMES_VALVULA = {"gaveta": "Válvula gaveta", "globo": "Válvula globo", "retencao": "Válvula de retenção portinhola",
                 "esfera": "Válvula esfera (passagem reduzida)"}
TIPOS_VALVULA = ("gaveta", "globo", "esfera", "retencao")


def _valvulas():
    out = {}
    for tipo, cls in _FF.items():
        out[tipo] = {}
        for cl, vals in cls.items():
            out[tipo][cl] = {dn: float(v) for dn, v in zip(_DN_ACO, vals) if v is not None}
    return out


def valvula(L, tipo, d):
    """{"ff": face a face, "altura", "volante"} da válvula na classe da linha, ou None."""
    L = linha(L)
    vs = L.get("valvulas") or {}
    if tipo not in vs:
        return None
    cl = L.get("classe") or 150
    ff = vs[tipo].get(cl, {}).get(d)
    if ff is None:
        return None
    alt, vol = (_ALTURA.get(tipo, {}).get(d) or (None, None))
    tb = L["tubos"][d]["De"]
    if alt is None:          # sem dado de catálogo: proporção só para o desenho
        alt, vol = 3.2 * tb + 160.0, max(100.0, 1.6 * tb)
    return {"ff": ff, "altura": float(alt), "volante": float(vol)}


RESSALTO_RF = 2.0               # mm, classes 150 e 300
JUNTA_ESPIRALADA = 4.5          # mm, elemento de vedação (ASME B16.20)


def _pol_mm(txt):
    """'1-1/8' -> 28,575 mm."""
    tot = 0.0
    for parte in txt.split("-"):
        if "/" in parte:
            a, b = parte.split("/")
            tot += float(a) / float(b)
        else:
            tot += float(parte)
    return tot * 25.4


def _flanges():
    out = {}
    for cl, tab in _WN.items():
        out[cl] = {}
        for dn, (O, tf, X, A, Y, Drf, bc, n, est, est_mm) in tab.items():
            out[cl][dn] = {"O": float(O), "tf": tf + RESSALTO_RF, "X": float(X), "A": A,
                           # da ponta de solda até a face de vedação (o ressalto entra na conta)
                           "Y": Y + RESSALTO_RF, "D_ressalto": Drf, "bc": bc, "furos": n,
                           # furo só para o desenho: estojo + 1/8"
                           "furo": _pol_mm(est) + 3.2,
                           "estojo": '%s" × %d mm' % (est, est_mm)}
    return out


FONTE_ASME = ("Tubos ASME B36.10M (projectmaterials.com e ssmalloys.com; até DN 200 também InfraBuild); conexões "
              "ASME B16.9-2018 (tabelas ssmalloys.com e wermac.org, iguais célula a célula); flanges ASME B16.5 "
              "classe 150 (hardhatengineer.com e jsksteelmetal.com, conferidas com wermac.org e texasflange.com "
              "em polegadas) e classe 300 (hardhatengineer.com, conferida em polegadas com apiint.com). "
              "Consultas em 29/10/2026")


def _linha_topo(sch):
    i = 1 if sch == 40 else 3
    tubos = {dn: {"De": v[0], "e": v[i], "bolsa_tubo": 0.0, "kg_m": v[i + 1]} for dn, v in _B3610.items()}
    cap = {dn: float(v[3] if tubos[dn]["e"] <= v[5] else v[4]) for dn, v in _B169.items()}
    return {
        "id": "aco-topo-sch%d" % sch,
        "nome": "Aço carbono solda de topo SCH %d" % sch,
        "material": "Aço carbono",
        "materiais": {"tubo": "Aço carbono ASTM A106 Gr. B (típico)", "conexao": "Aço carbono ASTM A234 WPB (típico)",
                      "flange": "Aço carbono forjado ASTM A105 (típico)",
                      "junta": "Espiralada aço inox + grafite, anel centralizador (típico)",
                      "estojo": "ASTM A193 B7 com porcas A194 2H (típico)",
                      "valvula": "Corpo de aço carbono fundido ASTM A216 WCB (típico)"},
        "fabricante": "Padrão ASME",
        "sufixo": "SCH %d" % sch,
        "sch": "SCH %d" % sch,
        "solda_topo": True,
        "emenda": "solda",
        "nps": NPS,
        "nomes": {"joelho90": "Curva 90° raio longo {dn} {sch}", "joelho45": "Curva 45° raio longo {dn} {sch}",
                  "te": "Tê {dn} {sch}", "te_reducao": "Tê de redução {D} × {d} {sch}",
                  "luva_reducao": "Redução concêntrica {D} × {d} {sch}", "cap": "Cap (tampão) {dn} {sch}",
                  "tubo": "Tubo de aço carbono sem costura {dn} {sch}",
                  "flange": "Flange de pescoço (WN) classe {classe} RF {dn} {sch}",
                  "junta": "Junta espiralada classe {classe} {dn}",
                  "valvula": "{nome} classe {classe} RF {dn}"},
        "fonte": FONTE_ASME + "; válvulas ASME B16.10-2022 (wermac.org e projectmaterials.com)",
        "norma": "ASME B36.10M (tubos), ASME B16.9 (conexões de solda de topo), ASME B16.5 (flanges), ASME "
                 "B16.20 (juntas) e ASME B16.10 (face a face das válvulas); edições a checar na especificação do "
                 "projeto",
        "pressao": "Conforme cálculo da linha (ASME B31.3 ou B31.1) e classe do flange",
        "temperatura_max": "Conforme especificação de material",
        "cor": (0.42, 0.45, 0.48),
        "barra": 6000.0,
        "diametros": _DN_ACO,
        "tubos": tubos,
        "bolsa": {dn: 0.0 for dn in _DN_ACO},
        "corpo": {dn: tubos[dn]["De"] for dn in _DN_ACO},
        "joelho90": {dn: float(v[0]) for dn, v in _B169.items()},
        "joelho45": {dn: float(v[1]) for dn, v in _B169.items()},
        "te": {dn: float(v[2]) for dn, v in _B169.items()},
        "te_ramal": {dn: float(v[2]) for dn, v in _B169.items()},
        "te_reducao": {k: (2.0 * c, float(m)) for k, (c, m) in _TE_RED.items()},
        "cruzeta": {},
        "luva": {},
        "luva_reducao": {k: float(h) for k, h in _RED_H.items()},
        "bucha_curta": {},
        "bucha_longa": {},
        "cap": cap,
        "flanges": _flanges(),
        "valvulas": _valvulas(),
        "junta_espessura": JUNTA_ESPIRALADA,
        "densidade": 7850.0,
        "a_conferir": {},
    }


ACO_TOPO_40 = _linha_topo(40)
ACO_TOPO_80 = _linha_topo(80)


# ============================================================== aço carbono roscado (BSP)
# Tubos ABNT NBR 5580 classe M (média), catálogo Tuper "Tubos Pretos e Galvanizados" (jul/2022) p. 6, conferido
# com Tubos Verola e UMS. Conexões de ferro fundido maleável Tupy (catálogo atual e anterior), conferidas com
# Crane (BS EN 10242) e Georg Fischer; penetração da rosca pela EN 10242:2025 tabela 5 (= Crane = GF).
_DN_ROSCA = (15, 20, 25, 32, 40, 50, 65, 80, 100)
_NBR5580_M = {15: (21.3, 2.65, 1.219), 20: (26.9, 2.65, 1.585), 25: (33.7, 3.35, 2.507), 32: (42.4, 3.35, 3.226),
              40: (48.3, 3.35, 3.714), 50: (60.3, 3.75, 5.230), 65: (76.1, 3.75, 6.691), 80: (88.9, 4.00, 8.375),
              100: (114.3, 4.50, 12.185)}
_LE = {15: 13.0, 20: 15.0, 25: 17.0, 32: 19.0, 40: 19.0, 50: 24.0, 65: 27.0, 80: 30.0, 100: 36.0}
_TUPY_LUVA = {15: 36.0, 20: 39.0, 25: 45.0, 32: 50.0, 40: 55.0, 50: 65.0, 65: 74.0, 80: 80.0, 100: 94.0}
_TUPY_BUCHA = {15: 24.0, 20: 26.0, 25: 29.0, 32: 31.0, 40: 31.0, 50: 35.0, 65: 40.0, 80: 44.0, 100: 51.0}


def _pares(dns, n=2):
    """(maior, menor) com o menor até n bitolas abaixo."""
    out = []
    for i, D in enumerate(dns):
        for d in dns[max(0, i - n):i]:
            out.append((D, d))
    return out


ACO_ROSCA_M = {
    "id": "aco-rosca-nbr5580-m",
    "nome": "Aço carbono roscado BSP (NBR 5580 classe M)",
    "material": "Aço carbono",
    "materiais": {"tubo": "Aço carbono NBR 5580 classe M, galvanizado ou preto",
                  "conexao": "Ferro fundido maleável galvanizado (NBR 6943)"},
    "fabricante": "Tuper / Tupy",
    "sufixo": "",
    "nps": NPS,
    "emenda": "luva",
    "bucha_rosca": True,
    "nomes": {"joelho90": "Cotovelo 90° {dn}", "joelho45": "Cotovelo 45° {dn}", "te": "Tê {dn}",
              "te_reducao": "Tê de redução {D} × {d}", "cruzeta": "Cruzeta {dn}", "luva": "Luva {dn}",
              "luva_reducao": "Luva de redução {D} × {d}", "bucha_curta": "Bucha de redução {D} × {d}",
              "cap": "Tampão {dn}", "uniao": "União {dn}",
              "tubo": "Tubo de aço carbono NBR 5580 classe M {dn} com rosca BSP"},
    "fonte": "Tubos: Tuper, Tubos Pretos e Galvanizados (jul/2022) p. 6, conferido com Tubos Verola e UMS. "
             "Conexões: Tupy, catálogo de conexões (atual p. 17–21 e anterior p. 18–22), cotovelos, tês e "
             "luva de redução iguais aos da Crane e da Georg Fischer; penetração da rosca pela EN 10242:2025 "
             "(tabela 5). Consultas em 29/10/2026",
    "norma": "Tubos ABNT NBR 5580 (edição 2015, a checar); conexões ABNT NBR 6943 (edição 2025, a checar) / "
             "ISO 49 / EN 10242; rosca ABNT NBR NM ISO 7-1",
    "pressao": "Conforme NBR 5580 e NBR 6943 (a checar para a classe e o fluido)",
    "temperatura_max": "Conforme NBR 6943 (a checar)",
    "cor": (0.70, 0.72, 0.74),
    "barra": 6000.0,
    "diametros": _DN_ROSCA,
    "tubos": {dn: {"De": v[0], "e": v[1], "kg_m": v[2],
                   # emenda com luva: as pontas ficam afastadas (luva − 2 × penetração)
                   "bolsa_tubo": -(_TUPY_LUVA[dn] - 2 * _LE[dn])} for dn, v in _NBR5580_M.items()},
    "bolsa": dict(_LE),
    # corpo só para o desenho (o catálogo não publica o diâmetro externo do corpo)
    "corpo": {dn: round(v[0] * 1.3, 1) for dn, v in _NBR5580_M.items()},
    "joelho90": {15: 28.0, 20: 33.0, 25: 38.0, 32: 45.0, 40: 50.0, 50: 58.0, 65: 69.0, 80: 78.0, 100: 96.0},
    "joelho45": {15: 22.0, 20: 25.0, 25: 28.0, 32: 33.0, 40: 36.0, 50: 43.0, 65: 50.0, 80: 55.0, 100: 66.0},
    "te": {15: 28.0, 20: 33.0, 25: 38.0, 32: 45.0, 40: 50.0, 50: 58.0, 65: 69.0, 80: 78.0, 100: 96.0},
    "cruzeta": {15: 28.0, 20: 33.0, 25: 38.0, 32: 45.0, 40: 50.0, 50: 58.0, 65: 69.0, 80: 78.0, 100: 97.0},
    "luva": dict(_TUPY_LUVA),
    # tê de redução (linha × ramal): (comprimento na linha = 2 × a, centro até a face do ramal)
    "te_reducao": {(20, 15): (60.0, 31.0), (25, 15): (64.0, 34.0), (25, 20): (70.0, 36.0), (32, 20): (72.0, 41.0),
                   (32, 25): (80.0, 42.0), (40, 25): (84.0, 46.0), (40, 32): (92.0, 48.0), (50, 25): (88.0, 52.0),
                   (50, 32): (96.0, 54.0), (50, 40): (104.0, 55.0), (65, 50): (122.0, 66.0), (80, 50): (128.0, 73.0),
                   (100, 50): (140.0, 86.0), (100, 80): (168.0, 92.0)},
    "luva_reducao": {(20, 15): 39.0, (25, 15): 45.0, (25, 20): 45.0, (32, 20): 50.0, (32, 25): 50.0, (40, 25): 55.0,
                     (40, 32): 55.0, (50, 25): 65.0, (50, 32): 65.0, (50, 40): 65.0, (65, 50): 74.0, (80, 50): 80.0,
                     (80, 65): 80.0, (100, 80): 94.0},
    # bucha de redução: comprimento total pela bitola maior
    "bucha_curta": {(D, d): _TUPY_BUCHA[D] for D, d in _pares(_DN_ROSCA)},
    "bucha_longa": {},
    "cap": {15: 23.0, 20: 25.5, 25: 29.0, 32: 31.0, 40: 31.0, 50: 38.0, 65: 42.0, 80: 46.0, 100: 56.0},
    "uniao": {15: 48.0, 20: 52.0, 25: 58.0, 32: 65.0, 40: 70.0, 50: 78.0, 65: 85.0, 80: 95.0, 100: 110.0},
    "densidade": 7850.0,
    "a_conferir": dict(
        [(("cruzeta", 100), "cruzeta 4\": só o catálogo Tupy dá a cota (97 mm)")]
        + [(("uniao", d), "união: comprimento lido do catálogo Tupy anterior; a Crane dá valores até 3 mm "
                          "menores") for d in _DN_ROSCA]
        + [(("cap", d), "tampão: Tupy e Crane divergem em até 4 mm") for d in _DN_ROSCA]),
}


LINHAS = {TIGRE_SOLDAVEL["id"]: TIGRE_SOLDAVEL, TIGRE_AQUATHERM["id"]: TIGRE_AQUATHERM,
          TIGRE_ESGOTO["id"]: TIGRE_ESGOTO, ACO_TOPO_40["id"]: ACO_TOPO_40, ACO_TOPO_80["id"]: ACO_TOPO_80,
          ACO_ROSCA_M["id"]: ACO_ROSCA_M}
PADRAO = TIGRE_SOLDAVEL["id"]


def linha(lid):
    if isinstance(lid, dict):
        return lid
    return LINHAS.get(lid) or LINHAS[PADRAO]


# nomes das peças na lista de materiais; cada linha pode trocar os que quiser em "nomes"
NOMES_PADRAO = {
    "joelho90": "Joelho 90° {suf} {dn}",
    "joelho45": "Joelho 45° {suf} {dn}",
    "te": "Tê {suf} {dn}",
    "te_reducao": "Tê de redução soldável {D} × {d}",
    "cruzeta": "Cruzeta {suf} {dn}",
    "luva": "Luva {suf} {dn}",
    "luva_reducao": "Luva de redução soldável {D} × {d}",
    "bucha_curta": "Bucha de redução soldável curta {D} × {d}",
    "bucha_longa": "Bucha de redução soldável longa {D} × {d}",
    "cap": "Cap {suf} {dn}",
    "registro": "Registro de esfera soldável {dn}",
    "tubo": "Tubo {suf} {dn}",
    "uniao": "União {dn}",
    "flange": "Flange classe {classe} {dn}",
    "junta": "Junta para flange classe {classe} {dn}",
    "estojo": "Estojo {est} com 2 porcas",
    "valvula": "{nome} {dn}",
}


def nome_peca(L, chave, **kw):
    t = dict(NOMES_PADRAO)
    t.update(L.get("nomes") or {})
    kw.setdefault("suf", L.get("sufixo", "soldável"))
    kw.setdefault("classe", L.get("classe", ""))
    kw.setdefault("sch", L.get("sch", ""))
    return " ".join(t[chave].format(**kw).split())


def flange(L, d):
    """Medidas do flange da linha no diâmetro d, na classe escolhida (L["classe"]); None se não houver."""
    L = linha(L)
    fl = L.get("flanges") or {}
    if not fl:
        return None
    cl = L.get("classe") or sorted(fl)[0]
    return (fl.get(cl) or {}).get(d)


def rotulo(L, d):
    """Como o diâmetro aparece para quem usa: '25 mm' (PVC), 'DN 100' (esgoto), 'DN 50 (2")' (aço)."""
    L = linha(L)
    if L.get("nps") and d in L["nps"]:
        return 'DN %d (%s")' % (d, L["nps"][d])
    return L.get("rotulo_dn", "%d mm") % d


def rotulo_curto(L, d):
    """Diâmetro nas reduções: '2"' no aço, o número nas outras linhas."""
    L = linha(L)
    if L.get("nps") and d in L["nps"]:
        return '%s"' % L["nps"][d]
    return "%d" % d


def dn_do_texto(txt):
    """Número do diâmetro em '25 mm', 'DN 100' ou 'DN 50 (2")'."""
    import re
    m = re.search(r"\d+", str(txt))
    return int(m.group()) if m else 0


def a_conferir(L, chave, k):
    """Motivo, se a medida (chave, k) da linha está marcada como a conferir; senão None."""
    return (L.get("a_conferir") or {}).get((chave, k))


def nomes():
    return [(lid, l["nome"] + " — " + l["fabricante"]) for lid, l in LINHAS.items()]
