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
valor duvidoso na tabela de origem (erro de impressão provável) e são usados com aviso.
"""

TIGRE_SOLDAVEL = {
    "id": "pvc-soldavel-af",
    "nome": "PVC soldável água fria (marrom)",
    "material": "PVC rígido",
    "fabricante": "Tigre",
    "fonte": "Tigre, Catálogo Técnico Predial Água Fria (fev/2008), Linha Soldável, p. 08–15. O Catálogo "
             "Predial 2025 (TG1.386-25) e o Manual Técnico 2025 trazem só códigos e bitolas, sem as cotas",
    "norma": "ABNT NBR 5648 – Tubos e conexões de PVC-U com junta soldável para sistemas prediais de água "
             "fria – Requisitos (citada no Manual Técnico Tigre 2025, p. 81; edição vigente a checar)",
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
    # cruzeta e com a bucha curta; a conferir na norma
    "bolsa": {20: 16.0, 25: 18.5, 32: 22.0, 40: 26.0, 50: 31.0, 60: 36.0, 75: 43.5, 85: 48.5, 110: 58.8},
    # diâmetro externo do corpo: cota D3 do cap soldável (p. 10)
    "corpo": {20: 28.5, 25: 34.0, 32: 43.0, 40: 52.0, 50: 63.0, 60: 76.0, 75: 95.0, 85: 104.4, 110: 134.9},
    # Joelho 90° soldável (p. 12): na tabela as linhas A e D saíram trocadas; A é a coluna 27…124
    "joelho90": {20: 27.0, 25: 32.0, 32: 39.0, 40: 47.0, 50: 57.0, 60: 67.0, 75: 87.2, 85: 97.7, 110: 124.0},
    # Joelho 45° soldável (p. 11): idem, A é a coluna 22,3…85,5
    "joelho45": {20: 22.3, 25: 24.5, 32: 29.5, 40: 35.5, 50: 42.5, 60: 49.5, 75: 60.0, 85: 67.5, 110: 85.5},
    # Tê soldável (p. 14): cota B (centro até a face)
    "te": {20: 27.0, 25: 32.0, 32: 39.0, 40: 47.0, 50: 57.0, 60: 71.3, 75: 87.2, 85: 97.7, 110: 124.0},
    # Cruzeta soldável (p. 10): só 20 e 50 mm; cota A
    "cruzeta": {20: 32.0, 50: 57.0},
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
        (85, 75): 48.5, (110, 85): 31.0,
    },
    # Bucha de redução soldável longa (p. 10)
    "bucha_longa": {
        (32, 20): 44.0, (40, 20): 51.6, (40, 25): 51.8, (50, 20): 55.8, (50, 25): 31.0, (50, 32): 61.3,
        (60, 25): 70.5, (60, 32): 70.9, (60, 40): 71.3, (60, 50): 71.8, (75, 50): 95.1, (85, 60): 95.1,
        (110, 60): 140.0, (110, 75): 130.0,
    },
    # Luva de redução soldável (p. 13): comprimento total A
    "luva_reducao": {
        (25, 20): 41.0, (32, 25): 53.0, (40, 32): 68.0, (50, 25): 65.2, (60, 50): 72.5, (75, 60): 91.8,
        (110, 75): 132.0,
    },
    # Cap soldável (p. 10): comprimento A
    "cap": {20: 16.0, 25: 18.5, 32: 22.0, 40: 26.0, 50: 31.0, 60: 36.0, 75: 43.5, 85: 48.5, 110: 58.8},
    "a_conferir": {
        ("bucha_curta", (110, 85)): "A = 31 mm, menor que a bolsa de 110 (provável erro na tabela)",
        ("bucha_longa", (50, 25)): "A = 31 mm, fora da sequência da tabela",
        ("cruzeta", 20): "na tabela, D = 25 para a cruzeta de 20",
        ("bolsa", None): "profundidade da bolsa tirada da cota A do cap",
    },
}

LINHAS = {TIGRE_SOLDAVEL["id"]: TIGRE_SOLDAVEL}
PADRAO = TIGRE_SOLDAVEL["id"]


def linha(lid):
    return LINHAS.get(lid) or LINHAS[PADRAO]


def nomes():
    return [(lid, l["nome"] + " — " + l["fabricante"]) for lid, l in LINHAS.items()]
