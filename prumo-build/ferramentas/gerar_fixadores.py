# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gera Resources/fixadores/fixadores.json (Prumo 3D) a partir de dados/fixadores.json
(levantamento com fonte e situação de cada valor: ISO 4017/4014, ISO 4762, ISO 4032, ISO 7089).

Comprimentos de parafuso: lista levantada (M3 a M10) ou, para os demais diâmetros, a série de
comprimentos nominais entre 2·d e 10·d — marcados "a checar"."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, "dados", "fixadores.json")
SAIDA = os.path.join(AQUI, "..", "..", "src", "Mod", "Prumo3D", "Resources", "fixadores", "fixadores.json")


def main(saida=SAIDA):
    d = json.load(open(DADOS, encoding="utf-8"))
    out = {"descricao": "Fixadores métricos do Prumo 3D. Gerado por gerar_fixadores.py.",
           "unidades": "mm", "fontes": d["fontes"], "passo": d["passo"]}
    for chave in ("iso4017", "iso4762", "iso4032", "iso7089"):
        out[chave] = d[chave]
    serie = d.get("serie_comprimentos_nominais", {}).get("iso4014", {}).get("valores", [])
    comps = {}
    for m in d["iso4017"]:
        lst = d.get("comprimentos_iso4017", {}).get(m)
        if lst and lst.get("valores"):
            comps[m] = lst["valores"]
        elif serie:
            dn = float(m[1:])
            comps[m] = [x for x in serie if 2 * dn <= x <= 10 * dn]
    out["comprimentos"] = comps
    out["observacoes"] = d.get("observacoes", [])
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    r = main(sys.argv[1] if len(sys.argv) > 1 else SAIDA)
    print({k: len(v) for k, v in r.items() if isinstance(v, dict)})
