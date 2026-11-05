#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: deixa o OpenCV (cv2) do pacote independente do lugar onde foi montado.

O conda grava nos arquivos de configuração do cv2 (cv2/config.py e cv2/config-3.X.py) o caminho absoluto do
ambiente em que foi instalado (ex.: /home/runner/work/.../.pixi/envs/default). No computador de quem instala o
Prumo esse caminho não existe, o cv2 não acha a própria extensão e o "import cv2" falha com "recursion is
detected during loading of cv2 binary extensions". Este script troca cada caminho absoluto por um caminho
relativo à pasta do próprio cv2 (LOADER_DIR, que o carregador do OpenCV já define).

Uso: corrigir_cv2.py <pasta do ambiente copiado para o pacote>
"""
import ast
import ntpath
import os
import posixpath
import re
import sys

LITERAL = re.compile(r"""(?P<q>['"])(?P<s>(?:\\.|(?!(?P=q)).)*)(?P=q)""")


def _modulo_caminho(texto):
    return ntpath if (re.match(r"^[A-Za-z]:[\\/]", texto) or "\\" in texto) else posixpath


def achar_cv2(raiz):
    for pasta, subpastas, arquivos in os.walk(raiz):
        if os.path.basename(pasta) == "cv2" and "config.py" in arquivos and "__init__.py" in arquivos:
            return pasta
    return None


def literais_absolutos(texto):
    """[(trecho com aspas, valor)] dos textos que são caminhos absolutos."""
    r = []
    for m in LITERAL.finditer(texto):
        try:
            valor = ast.literal_eval(m.group(0))
        except Exception:
            continue
        if isinstance(valor, str) and (valor.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", valor)):
            r.append((m.group(0), valor))
    return r


def corrigir(raiz):
    cv2_dir = achar_cv2(raiz)
    if cv2_dir is None:
        print("corrigir_cv2: sem cv2 em %s (nada a fazer)" % raiz)
        return 0
    configs = sorted(f for f in os.listdir(cv2_dir) if re.match(r"^config(-\d+(\.\d+)?)?\.py$", f))
    # a pasta original do cv2: o config-3.X.py aponta para <cv2 original>/python-3.X
    orig_cv2 = None
    for f in configs:
        if f == "config.py":
            continue
        with open(os.path.join(cv2_dir, f), encoding="utf-8") as fh:
            for _t, v in literais_absolutos(fh.read()):
                mod = _modulo_caminho(v)
                if mod.basename(mod.normpath(v)).lower() == "cv2":
                    orig_cv2 = mod.normpath(v)
    if orig_cv2 is None:
        print("corrigir_cv2: caminho original do cv2 não encontrado; os arquivos ficam como estão")
        return 0
    mod = _modulo_caminho(orig_cv2)
    trocas = 0
    for f in configs:
        caminho = os.path.join(cv2_dir, f)
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read()
        novo = texto
        for trecho, valor in literais_absolutos(texto):
            rel = mod.relpath(mod.normpath(valor), orig_cv2)
            partes = [p for p in rel.replace("\\", "/").split("/") if p and p != "."]
            expr = "os.path.normpath(os.path.join(LOADER_DIR%s))" % "".join(", %r" % p for p in partes)
            novo = novo.replace(trecho, expr)
            trocas += 1
        if novo != texto:
            if "import os" not in novo:
                novo = "import os\n" + novo
            with open(caminho, "w", encoding="utf-8") as fh:
                fh.write(novo)
    # conferência: nenhum caminho absoluto pode sobrar
    for f in configs:
        with open(os.path.join(cv2_dir, f), encoding="utf-8") as fh:
            sobra = literais_absolutos(fh.read())
        if sobra:
            print("corrigir_cv2: ainda há caminho absoluto em %s: %s" % (f, sobra))
            return 1
    print("corrigir_cv2: %d caminho(s) do cv2 agora relativos a %s" % (trocas, cv2_dir))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(corrigir(sys.argv[1]))
