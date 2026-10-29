#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gera Prumo3D_<versão>-complemento.zip: só o complemento (src/Mod/Prumo3D), para atualizar sem baixar o
pacote inteiro. Uso: pacote_complemento.py <tag ou versão> <pasta de saída>

Dentro do .zip: Prumo3D/... (com PrumoVersaoCompilada.py da versão) e Prumo3D/complemento.json com a versão,
a base de FreeCAD e a versão mínima do pacote completo (BASE_MINIMA em PrumoComplemento.py). Ao lado, a soma
SHA-256 no mesmo formato dos outros arquivos."""
import hashlib
import json
import os
import re
import sys
import zipfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MOD = os.path.join(RAIZ, "src", "Mod", "Prumo3D")
FORA = {"__pycache__", ".pytest_cache"}


def base_freecad():
    txt = open(os.path.join(RAIZ, "CMakeLists.txt"), encoding="utf-8").read()
    partes = [re.search(r'set\(PACKAGE_VERSION_%s "(\d+)"\)' % k, txt).group(1) for k in ("MAJOR", "MINOR", "PATCH")]
    return ".".join(partes)


def base_minima():
    txt = open(os.path.join(MOD, "PrumoComplemento.py"), encoding="utf-8").read()
    return re.search(r'^BASE_MINIMA = "([^"]+)"', txt, re.M).group(1)


def gerar(versao, saida):
    versao = versao.lstrip("vV")
    os.makedirs(saida, exist_ok=True)
    nome = "Prumo3D_%s-complemento.zip" % versao
    destino = os.path.join(saida, nome)
    manifesto = {"versao": versao, "freecad": base_freecad(), "base_minima": base_minima()}
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for pasta, subpastas, arquivos in os.walk(MOD):
            subpastas[:] = sorted(d for d in subpastas if d not in FORA)
            for a in sorted(arquivos):
                if a.endswith((".pyc", ".pyo")) or a in ("PrumoVersaoCompilada.py", "complemento.json"):
                    continue
                caminho = os.path.join(pasta, a)
                rel = os.path.relpath(caminho, MOD).replace(os.sep, "/")
                z.write(caminho, "Prumo3D/" + rel)
        z.writestr("Prumo3D/PrumoVersaoCompilada.py", 'VERSAO_COMPILADA = "%s"\n' % versao)
        z.writestr("Prumo3D/complemento.json", json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n")
    # o mesmo complemento.json ao lado, para o Prumo saber se o .zip serve antes de baixar
    with open(os.path.join(saida, "Prumo3D_%s-complemento.json" % versao), "w", encoding="utf-8") as f:
        f.write(json.dumps(manifesto, ensure_ascii=False, indent=1) + "\n")
    h = hashlib.sha256(open(destino, "rb").read()).hexdigest()
    with open(destino + "-SHA256.txt", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (h, nome))
    return destino, manifesto


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    d, m = gerar(sys.argv[1], sys.argv[2])
    print("%s (%.1f MB) %s" % (d, os.path.getsize(d) / 1e6, m))
