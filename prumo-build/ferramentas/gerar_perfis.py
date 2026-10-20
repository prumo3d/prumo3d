# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gera a biblioteca de perfis do Prumo 3D (Resources/perfis/perfis.json) a partir da pesquisa
de catálogos em dados/pesquisa_normas.json (fonte e situação de cada valor).

Cada perfil leva "status": "confirmado" (catálogo oficial do fabricante) ou "a checar" (fonte
secundária, divergência entre fontes ou valor derivado). O Prumo mostra o aviso na tela.

Valores derivados (marcados em "derivado"):
- perfil U e I sem espessura de mesa no catálogo: tf calculado pela massa linear
  (área = massa / 0,785) e pela geometria de mesa constante, sem raios;
- raio R dos perfis W/HP: (d - 2·tf - d') / 2, estimado (o catálogo não traz R).
"""
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, "dados", "pesquisa_normas.json")
SAIDA = os.path.join(AQUI, "..", "..", "src", "Mod", "Prumo3D", "Resources", "perfis", "perfis.json")
RHO_ACO = 7850.0


def nome_pol(prefixo, desig_lbft, massa):
    """'U 3" x 4,10 (1a alma)' -> 'U 3" x 6,1 kg/m (4,10 lb/ft)'."""
    m = re.match(r'\s*([0-9]+)"\s*x\s*([0-9,]+)', desig_lbft)
    kg = ("%.2f" % massa).rstrip("0").rstrip(".").replace(".", ",")
    if not m:
        return "%s %s" % (prefixo, desig_lbft)
    return '%s %s" x %s kg/m (%s lb/ft)' % (prefixo, m.group(1), kg, m.group(2))


def tf_pela_massa(massa, d, bf, tw):
    area = massa / RHO_ACO * 1e6  # mm²
    return (area - d * tw) / (2.0 * (bf - tw))


def main(saida=SAIDA):
    d = json.load(open(DADOS, encoding="utf-8"))
    fontes = d["fontes"]
    p = d["2_perfis_laminados"]
    familias = []

    def fonte(chave):
        f = fontes.get(chave, {})
        return {"chave": chave, "nome": f.get("nome", chave), "url": f.get("url", "")}

    # ---- W / HP (Gerdau)
    itens = []
    for b in p["W_HP_gerdau"]["bitolas"]:
        nome = b["designacao"].replace(" (H)", "")
        itens.append({"nome": nome, "tipo": "I", "d": b["d_mm"], "bf": b["bf_mm"], "tw": b["tw_mm"],
                      "tf": b["tf_mm"], "R": b.get("R_mm_derivado"), "massa": b["massa_kg_m"],
                      "area_cm2": b.get("area_cm2"), "status": b["status"],
                      "derivado": ["R"] if b.get("R_mm_derivado") else []})
    familias.append({"id": "W", "nome": "Perfil W (laminado, abas paralelas)",
                     "norma": "ABNT NBR 15980 / ASTM A6 (catálogo Gerdau)",
                     "fonte": fonte("F_GERDAU_PE"), "itens": [i for i in itens if i["nome"].startswith("W")]})
    familias.append({"id": "HP", "nome": "Perfil HP (laminado, estaca/pilar)",
                     "norma": "ABNT NBR 15980 / ASTM A6 (catálogo Gerdau)",
                     "fonte": fonte("F_GERDAU_PE"), "itens": [i for i in itens if i["nome"].startswith("HP")]})

    # ---- U padrão americano
    itens = []
    vistos = set()
    for b in p["U_padrao_americano"]["oficial_arcelormittal_2019"]["bitolas"]:
        dd, bf, tw, m = b["altura_mm"], b["largura_aba_mm"], b["espessura_alma_mm"], b["massa_kg_m"]
        nome = nome_pol("U", b["designacao_pol_lbft"], m)
        itens.append({"nome": nome, "tipo": "U", "d": dd, "bf": bf, "tw": tw,
                      "tf": round(tf_pela_massa(m, dd, bf, tw), 2), "massa": m, "status": b["status"],
                      "derivado": ["tf"], "fonte": "F_AM_2019"})
        vistos.add((round(dd, 1), round(m, 1)))
    for b in p["U_padrao_americano"]["secundaria_fabrica_do_projeto"]["bitolas"]:
        dd, bf, tw, m = b["altura_mm"], b["largura_aba_mm"], b["espessura_alma_mm"], b["massa_kg_m"]
        if (round(dd, 1), round(m, 1)) in vistos:
            continue
        pol = round(dd / 25.4)
        nome = 'U %d" x %s kg/m' % (pol, ("%.1f" % m).replace(".", ","))
        itens.append({"nome": nome, "tipo": "U", "d": dd, "bf": bf, "tw": tw,
                      "tf": round(tf_pela_massa(m, dd, bf, tw), 2), "massa": m, "status": "a checar",
                      "derivado": ["tf"], "fonte": "F_FAPRO_U"})
        vistos.add((round(dd, 1), round(m, 1)))
    itens.sort(key=lambda i: (i["d"], i["massa"]))
    familias.append({"id": "U", "nome": "Perfil U laminado (padrão americano)", "norma": "ABNT NBR 15980 / ASTM A6",
                     "fonte": fonte("F_AM_2019"), "itens": itens})

    # ---- I padrão americano
    itens = []
    vistos = set()
    for b in p["I_padrao_americano"]["oficial_arcelormittal_2019"]["bitolas"]:
        dd, bf, tw, m = b["altura_mm"], b["largura_mesa_mm"], b["espessura_alma_mm"], b["massa_kg_m"]
        nome = nome_pol("I", b["designacao_pol_lbft"], m)
        itens.append({"nome": nome, "tipo": "I", "d": dd, "bf": bf, "tw": tw,
                      "tf": round(tf_pela_massa(m, dd, bf, tw), 2), "massa": m, "status": b["status"],
                      "derivado": ["tf"], "fonte": "F_AM_2019"})
        vistos.add((round(dd, 1), round(m, 1)))
    for b in p["I_padrao_americano"]["secundaria_fabrica_do_projeto"]["bitolas"]:
        dd, bf, tw, m = b["altura_mm"], b["largura_mesa_mm"], b["espessura_alma_mm"], b["massa_kg_m"]
        if (round(dd, 1), round(m, 1)) in vistos:
            continue
        pol = round(dd / 25.4)
        nome = 'I %d" x %s kg/m' % (pol, ("%.1f" % m).replace(".", ","))
        tf = b.get("espessura_media_mesa_mm")
        itens.append({"nome": nome, "tipo": "I", "d": dd, "bf": bf, "tw": tw,
                      "tf": tf if tf else round(tf_pela_massa(m, dd, bf, tw), 2), "massa": m,
                      "status": "a checar", "derivado": [] if tf else ["tf"], "fonte": "F_FAPRO_I"})
    itens.sort(key=lambda i: (i["d"], i["massa"]))
    familias.append({"id": "I", "nome": "Perfil I laminado (padrão americano)", "norma": "ABNT NBR 15980 / ASTM A6",
                     "fonte": fonte("F_AM_2019"), "itens": itens})

    # ---- Cantoneiras de abas iguais
    itens = []
    for b in p["cantoneiras_abas_iguais"]["metricas_arcelormittal_2019"]["bitolas"]:
        itens.append({"nome": b["designacao"].replace(".", ","), "tipo": "L", "aba": b["aba_mm"],
                      "esp": b["espessura_mm"], "massa": b["massa_kg_m"], "status": b["status"],
                      "derivado": [], "fonte": "F_AM_2019"})
    for b in p["cantoneiras_abas_iguais"]["polegadas_arcelormittal_2019"]["bitolas"]:
        nome = "L " + b["designacao_pol"]
        st = b["status"]
        massa = b["massa_kg_m"]
        der = []
        if st != "confirmado" and b.get("verif_massa_teorica_kg_m"):
            massa = b["verif_massa_teorica_kg_m"]
            der = ["massa"]
        itens.append({"nome": nome, "tipo": "L", "aba": b["aba_mm"], "esp": b["espessura_mm"],
                      "massa": massa, "status": st, "derivado": der, "fonte": "F_AM_2019"})
    familias.append({"id": "L", "nome": "Cantoneira de abas iguais", "norma": "ABNT NBR 15980 / ASTM A6",
                     "fonte": fonte("F_AM_2019"), "itens": itens})

    # ---- Tubos de condução Sch 40 / Sch 80
    itens = []
    for b in d["3_tubos"]["conducao_ASME_B36_10M"]["linhas"]:
        for sch in ("40", "80"):
            e = b.get("sch%s_espessura_mm" % sch)
            if not e:
                continue
            nome = 'Tubo %s" Sch %s' % (b["DN_pol"], sch)
            itens.append({"nome": nome, "tipo": "TUBO", "D": b["diametro_externo_mm"], "esp": e,
                          "massa": b.get("sch%s_massa_kg_m_fonte" % sch) or b.get("sch%s_massa_kg_m_calc" % sch),
                          "status": b["status"], "derivado": [], "fonte": "F_FLUIDS"})
    familias.append({"id": "TUBO", "nome": "Tubo de condução (Sch 40 / Sch 80)",
                     "norma": "ASME B36.10M (NBR 5590 / ASTM A106 / A53)", "fonte": fonte("F_FLUIDS"),
                     "itens": itens})

    # ---- Tubos quadrados (metalon)
    itens = []
    for b in d["3_tubos"]["estruturais_quadrados_retangulares"]["secundaria_fabrica_do_projeto_quadrados"]["bitolas"]:
        itens.append({"nome": "Tubo □ " + b["designacao"], "tipo": "TQ", "lado": b["lado_mm"],
                      "esp": b["espessura_mm"], "massa": b["massa_kg_m"], "status": "a checar",
                      "derivado": [], "fonte": "F_FAPRO_TQ"})
    familias.append({"id": "TQ", "nome": "Tubo quadrado (metalon)", "norma": "a checar (NBR 6591)",
                     "fonte": fonte("F_FAPRO_TQ"), "itens": itens})

    saida_dados = {"descricao": "Biblioteca de perfis do Prumo 3D. Gerada por gerar_perfis.py.",
                   "unidades": "mm, kg/m", "fontes": {k: fonte(k) for k in fontes}, "familias": familias}
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(saida_dados, fh, ensure_ascii=False, indent=1)
    return saida_dados


if __name__ == "__main__":
    r = main(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
    for f in r["familias"]:
        conf = sum(1 for i in f["itens"] if i["status"] == "confirmado")
        print("%-5s %3d itens (%d confirmados)" % (f["id"], len(f["itens"]), conf))
