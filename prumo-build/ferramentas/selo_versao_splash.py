"""Prumo 3D: desenha o selo da versão (ex.: "0.1 BETA") sobre a tela de abertura.

Base: prumo-build/ferramentas/splash/splash_base.png (sem selo).
Saída: src/Mod/Prumo3D/Resources/splash_image.png.
A versão vem do argumento (ex.: python selo_versao_splash.py 0.3.0-beta), de PrumoVersaoCompilada.py
(gravado pelo fluxo de publicação) ou de PrumoVersao.py (VERSAO e CANAL), nessa ordem.
"""
import os
import re

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
MOD = os.path.join(RAIZ, "src", "Mod", "Prumo3D")


def versao(rotulo=None):
    """Texto do selo. Ordem: argumento (ex.: 0.3.0-beta) → PrumoVersaoCompilada.py → PrumoVersao.py."""
    if not rotulo:
        comp = os.path.join(MOD, "PrumoVersaoCompilada.py")
        if os.path.isfile(comp):
            m = re.search(r'VERSAO_COMPILADA\s*=\s*"([^"]*)"', open(comp, encoding="utf-8").read())
            rotulo = m.group(1) if m else None
    if rotulo:
        r = rotulo.strip().lstrip("vV")
        v, c = (r.split("-", 1) + [""])[:2] if "-" in r else (r, "")
        return ("%s %s" % (v, c)).strip().upper()
    txt = open(os.path.join(MOD, "PrumoVersao.py"), encoding="utf-8").read()
    v = re.search(r'^VERSAO\s*=\s*"([^"]+)"', txt, re.M).group(1)
    c = re.search(r'^CANAL\s*=\s*"([^"]*)"', txt, re.M).group(1)
    return ("%s %s" % (v, c)).strip().upper()


def main(rotulo=None):
    im = Image.open(os.path.join(AQUI, "splash", "splash_base.png")).convert("RGB")
    d = ImageDraw.Draw(im)
    fonte = ImageFont.truetype(os.path.join(MOD, "Resources", "fonts", "Poppins-SemiBold.ttf"), 15)
    texto = versao(rotulo)
    l, t, r, b = d.textbbox((0, 0), texto, font=fonte)
    pad_x, pad_y = 12, 5
    x0, y0 = 472, 228   # à direita do traço amarelo sob o nome
    w, h = (r - l) + 2 * pad_x, (b - t) + 2 * pad_y
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h // 2, fill="#F7BE00")
    d.text((x0 + pad_x - l, y0 + pad_y - t), texto, font=fonte, fill="#003A70")
    saida = os.path.join(MOD, "Resources", "splash_image.png")
    im.save(saida, optimize=True)
    print("selo", texto, "->", saida)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
