# SPDX-License-Identifier: LGPL-2.1-or-later
# Ícones da aba Chapa (bancada SheetMetal) no estilo do guia ilustrado.
#
# A bancada SheetMetal aponta os ícones pelo caminho completo do arquivo, então o tema não os troca:
# estes SVGs são gravados por cima dos originais em src/Mod/SheetMetal/Resources/icons
# (gerar_icones.py --chapa <pasta>).
import math
from nucleo import Icon, SOLID, COPY, CUT, YEL, OUT, NAVY, AMBER, AMBER_FILL, SW, SW_GEO

ICONS = {}
T = 0.9          # espessura da chapa (unidades de modelo)
L = 7.0          # largura da chapa (direção y)


def icon(*names):
    def deco(fn):
        for n in names:
            ICONS[n] = fn
        return fn
    return deco


# ------------------------------------------------------------ chapa dobrada (perfil em x,z extrudado em y)
def _arco(c, r, a0, a1, n=8):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def _desloca(pts, d):
    """Polilinha deslocada de d para o lado esquerdo do sentido de percurso."""
    out = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dz) or 1.0
        out.append((p[0] - dz / n * d, p[1] + dx / n * d))
    return out


def chapa(g, trechos, y0=0.0, y1=L, t=T):
    """Desenha uma chapa: trechos = [(pontos (x,z) da linha média, paleta), ...] em sequência.

    Desenha a face de cima/de dentro (a que aparece na isométrica) e a borda da frente (y = y1)."""
    for pts, pal in trechos:
        sup = _desloca(pts, t / 2)
        inf = _desloca(pts, -t / 2)
        # escolhe a face que olha para o observador (normal com x + z > 0)
        for face, cor in ((inf, pal[2]), (sup, pal[0])):
            for a, b in zip(face, face[1:]):
                dx, dz = b[0] - a[0], b[1] - a[1]
                nx, nz = -dz, dx                     # normal à esquerda do percurso
                lado = 1 if face is sup else -1
                if (nx + nz * 1.2) * lado <= 0:
                    continue
                g.poly([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])],
                       cor if abs(dz) < abs(dx) else pal[2], sw=SW * 0.7)
    for pts, pal in trechos:
        sup = _desloca(pts, t / 2)
        inf = _desloca(pts, -t / 2)
        g.poly([(x, y1, z) for x, z in sup] + [(x, y1, z) for x, z in reversed(inf)], pal[1])


def _contorno(g, trechos, y0=0.0, y1=L, t=T):
    """Contorno grosso da chapa inteira (por cima de tudo), para o ícone ler bem pequeno."""
    pts = [p for tr, _pal in trechos for p in tr]
    sup = _desloca(pts, t / 2)
    g.poly2([g.p(x, y0, z) for x, z in sup], "none", OUT, SW, close=False)


def _l(xa, xb, zt, r=1.2):
    """Linha média de um L: base de xa a xb (em z=0) e aba subindo em xb até zt, com raio r."""
    base = [(xa, 0.0), (xb - r, 0.0)]
    dobra = _arco((xb - r, r), r, -90, 0)
    aba = [(xb, r), (xb, zt)]
    return base, dobra, aba


# ------------------------------------------------------------ criar
@icon("SheetMetal_AddBase")
def base():
    g = Icon()
    b, d, a = _l(0, 9, 7)
    chapa(g, [(b + d[1:] + a[1:], YEL)])
    return g


@icon("SheetMetal_AddBaseShape")
def base_shape():
    g = Icon()
    r = 1.0
    perfil = [(0, 7), (0, r)] + _arco((r, r), r, 180, 270)[1:] + [(9 - r, 0)] + _arco((9 - r, r), r, -90, 0)[1:] + [(9, 7)]
    chapa(g, [(perfil, SOLID)])
    g.badge("plus")
    return g


@icon("SheetMetal_FromSolid")
def from_solid():
    g = Icon()
    g.box(0, 9, 0, L, 0, 6, pal=COPY, opacity=0.8, dash="3,2")
    chapa(g, [([(0, 6 - T / 2), (9 - T / 2, 6 - T / 2), (9 - T / 2, 0)], YEL)])
    return g


@icon("SheetMetal_SketchOnSheet")
def sketch_on_sheet():
    g = Icon()
    chapa(g, [([(0, 0), (10, 0)], SOLID)])
    g.ellipse_iso(5, 3.5, 2.4, T / 2 + 0.01, AMBER_FILL, stroke=AMBER, sw=SW_GEO * 0.9)
    return g


# ------------------------------------------------------------ dobras e abas
@icon("SheetMetal_AddWall")
def wall():
    g = Icon()
    b, d, a = _l(0, 9, 7)
    chapa(g, [(b, SOLID), (d + a[1:], YEL)])
    return g


@icon("SheetMetal_AddFoldWall")
def fold_wall():
    g = Icon()
    chapa(g, [([(0, 0), (5, 0)], SOLID), ([(5, 0), (8.5, 3.5)], YEL)])
    g.line((5, -1, T / 2), (5, L + 1, T / 2), color=AMBER, sw=SW, dash="4,3")
    return g


@icon("SheetMetal_Extrude")
def extrude():
    g = Icon()
    chapa(g, [([(0, 0), (5.5, 0)], SOLID), ([(5.5, 0), (10, 0)], YEL)])
    g.arrow3((6, L / 2, 2.2), (11, L / 2, 2.2))
    return g


@icon("SheetMetal_ExtendBySketch")
def extend_by_sketch():
    g = Icon()
    chapa(g, [([(0, 0), (6, 0)], SOLID)])
    g.profile(6, 10, 1, L - 1, T / 2, fill=True)
    return g


@icon("SheetMetal_AddBend")
def bend():
    g = Icon()
    b, d, a = _l(0, 9, 7, r=3.2)
    chapa(g, [(b, SOLID), (d, YEL), (a, SOLID)], t=1.2)
    return g


@icon("SheetMetal_AddHem")
def hem():
    g = Icon()
    r = 1.3
    perfil_bainha = _arco((9, r), r, -90, 90, n=10) + [(7, 2 * r)]
    chapa(g, [([(0, 0), (9, 0)], SOLID), (perfil_bainha, YEL)])
    return g


@icon("SheetMetal_AddJunction")
def junction():
    g = Icon()
    g.box(0, 9, 0, L, 0, 6, pal=SOLID)
    # fenda vertical na quina da frente
    g.poly([(9, L, 0), (9, L, 6), (9, L - 1.1, 6), (9, L - 1.1, 0)], "#FFFFFF", OUT, SW * 0.8)
    g.poly([(9 - 1.1, L, 6), (9, L, 6), (9, L - 1.1, 6), (9 - 1.1, L - 1.1, 6)], YEL[0], OUT, SW * 0.8)
    g.line((9, L - 0.55, -0.6), (9, L - 0.55, 6.8), color=AMBER, sw=SW, dash="3,2")
    return g


# ------------------------------------------------------------ recortes
@icon("SheetMetal_AddCutout")
def cutout():
    g = Icon()
    chapa(g, [([(0, 0), (10, 0)], SOLID)])
    g.rect3(3, 7, 2, 5, T / 2 + 0.01, CUT[0], stroke=OUT, sw=SW * 0.9)
    return g


@icon("SheetMetal_AddRelief")
def relief():
    g = Icon()
    b, d, a = _l(0, 9, 7)
    chapa(g, [(b + d[1:] + a[1:], SOLID)])
    # alívio: rasgo na ponta da dobra, do lado da frente
    g.poly([(7.4, L, -0.6), (9.6, L, -0.6), (9.6, L, 1.8), (7.4, L, 1.8)], CUT[1], OUT, SW * 0.8)
    g.poly([(7.4, L - 1.4, 1.8), (9.6, L - 1.4, 1.8), (9.6, L, 1.8), (7.4, L, 1.8)], CUT[0], OUT, SW * 0.8)
    return g


@icon("SheetMetal_AddCornerRelief")
def corner_relief():
    g = Icon()
    g.box(0, 9, 0, L, 0, 6, pal=SOLID)
    g.circle2(g.p(9, L, 6), 2.6, CUT[1], OUT, SW)
    return g


@icon("SheetMetal_Forming")
def forming():
    g = Icon()
    chapa(g, [([(0, 0), (10, 0)], SOLID)])
    g.cyl(5, 3.5, 2.4, T / 2, T / 2 + 1.6, pal=YEL)
    return g


# ------------------------------------------------------------ planificar
@icon("SheetMetal_Unfold")
def unfold():
    g = Icon()
    b, d, a = _l(0, 6, 5)
    chapa(g, [(b + d[1:] + a[1:], COPY)])
    g.rect3(0, 12, 9, 9 + L, -3, YEL[0], sw=SW)
    g.arrow3((8, 4, 2), (10, 9.5, -2.5), color=NAVY, sw=SW_GEO * 0.8)
    return g


@icon("SheetMetal_UnfoldUpdate")
def unfold_update():
    g = Icon()
    g.rect3(0, 12, 0, L, 0, YEL[0], sw=SW)
    g.badge("check")
    return g


def gerar(pasta):
    """Grava os ícones por cima dos originais da bancada SheetMetal."""
    import os
    feitos = []
    cache = {}
    for nome, fn in sorted(ICONS.items()):
        if fn not in cache:
            cache[fn] = fn().svg()
        destino = os.path.join(pasta, nome + ".svg")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(cache[fn])
        feitos.append(nome)
    return feitos


if __name__ == "__main__":
    import sys
    print("\n".join(gerar(sys.argv[1])))
