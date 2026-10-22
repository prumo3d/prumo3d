# SPDX-License-Identifier: LGPL-2.1-or-later
"""Monta as notas da versão para a página de versões do GitHub.

Uso: python notas_da_versao.py 0.2.0-beta > notas.md

Pega em NOVIDADES.md a seção da versão ("## 0.2.0 beta — dd/mm/aaaa"); se ela ainda não existe, usa a
seção "## Em desenvolvimento". Junta com a parte fixa (.github/notas-da-versao.md: como baixar, como
relatar um problema...).
"""
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def secoes(texto):
    """{título: corpo} das seções de nível 2."""
    res = {}
    partes = re.split(r"(?m)^## (.+)$", texto)
    for i in range(1, len(partes), 2):
        res[partes[i].strip()] = partes[i + 1].strip()
    return res


def chave(versao):
    """'0.2.0-beta' / '0.2.0 beta' / 'v0.2.0-beta' -> '0.2.0 beta'."""
    return versao.strip().lstrip("vV").replace("-", " ")


def da_versao(texto, versao):
    """(título, corpo) da seção da versão, ou da seção 'Em desenvolvimento' se ela não existir."""
    alvo = chave(versao)
    for titulo, corpo in secoes(texto).items():
        if titulo.split("—")[0].strip() == alvo:
            return titulo, corpo
    corpo = secoes(texto).get("Em desenvolvimento", "")
    corpo = re.sub(r"^Já está no código.*\n?", "", corpo).strip()
    return alvo, corpo


def montar(versao, raiz=RAIZ):
    with open(os.path.join(raiz, "NOVIDADES.md"), encoding="utf-8") as f:
        novidades = f.read()
    with open(os.path.join(raiz, ".github", "notas-da-versao.md"), encoding="utf-8") as f:
        fixa = f.read().strip()
    titulo, corpo = da_versao(novidades, versao)
    corpo = re.sub(r"(?m)^### ", "#### ", corpo)
    return ("## Prumo 3D %s\n\n### Novidades desta versão\n\n%s\n\n"
            "Histórico completo: [NOVIDADES.md](https://github.com/prumo3d/prumo3d/blob/main/NOVIDADES.md)\n\n"
            "%s\n" % (titulo, corpo or "Correções e ajustes.", fixa))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.write(montar(sys.argv[1]))
