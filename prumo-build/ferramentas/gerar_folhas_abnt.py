# SPDX-License-Identifier: LGPL-2.1-or-later
"""Gera as folhas de desenho ABNT do Prumo 3D (SVG para o Desenho técnico / TechDraw).

Uso:
    python gerar_folhas_abnt.py [pasta_de_saida]
(padrão: src/Mod/Prumo3D/Resources/folhas)

Duas famílias:

- NBR16752: ABNT NBR 16752:2020 (Desenho técnico — Requisitos para apresentação em folhas de
  desenho). A norma segue a ISO 5457/ISO 7200; as dimensões usadas aqui são as da ISO 5457
  (margem esquerda 20 mm, demais 10 mm, quadro 0,7 mm, legenda 180 mm). A CONFERIR no texto da
  NBR 16752 (norma paga; valores tirados das normas ISO de adoção idêntica).
- NBR10068: ABNT NBR 10068:1987 (folha de desenho — leiaute e dimensões), substituída pela
  NBR 16752, mas ainda muito usada: margem esquerda 25 mm; demais 10 mm (A0, A1) ou 7 mm
  (A2, A3, A4); quadro 1,4 / 1,0 / 0,7 / 0,5 / 0,5 mm; legenda 175 mm (A0, A1) ou 178 mm.

Todas as medidas estão nas tabelas abaixo, para ajuste num lugar só.
O símbolo do 1º diedro segue a geometria dos modelos ISO do FreeCAD (licença CC0).
"""
import os
import sys

FORMATOS = {  # largura x altura em paisagem (mm)
    "A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210),
}

NORMAS = {
    "NBR16752": {
        "titulo": "ABNT NBR 16752",
        "margem": {f: {"esq": 20, "dir": 10, "sup": 10, "inf": 10} for f in FORMATOS},
        "quadro": {f: 0.7 for f in FORMATOS},
        "legenda": {f: 180 for f in FORMATOS},
        "corte": True,
    },
    "NBR10068": {
        "titulo": "ABNT NBR 10068",
        "margem": {
            "A0": {"esq": 25, "dir": 10, "sup": 10, "inf": 10},
            "A1": {"esq": 25, "dir": 10, "sup": 10, "inf": 10},
            "A2": {"esq": 25, "dir": 7, "sup": 7, "inf": 7},
            "A3": {"esq": 25, "dir": 7, "sup": 7, "inf": 7},
            "A4": {"esq": 25, "dir": 7, "sup": 7, "inf": 7},
        },
        "quadro": {"A0": 1.4, "A1": 1.0, "A2": 0.7, "A3": 0.5, "A4": 0.5},
        "legenda": {"A0": 175, "A1": 175, "A2": 178, "A3": 178, "A4": 178},
        "corte": True,
    },
}

# Legenda (carimbo): linhas de cima para baixo; cada célula = (largura relativa a 180 mm,
# rótulo, campo editável, texto padrão, altura da letra do valor, preenchimento automático)
LEGENDA = [
    (12, [(110, "EMPRESA / PROPRIETÁRIO", "empresa", "", 3.5, "company"),
          (70, "CLIENTE / OBRA", "cliente", "", 3.5, None)]),
    (12, [(180, "TÍTULO", "titulo", "", 5.0, "title")]),
    (8, [(70, "MATERIAL", "material", "", 2.5, None),
         (35, "MASSA (kg)", "massa", "", 2.5, None),
         (75, "TOLERÂNCIAS GERAIS", "tolerancias", "", 2.5, None)]),
    (8, [(50, "DESENHISTA", "desenhista", "", 2.5, "author"),
         (40, "VERIFICADO", "verificado", "", 2.5, None),
         (40, "APROVADO", "aprovado", "", 2.5, None),
         (50, "DATA", "data", "", 2.5, "date")]),
    (8, [(60, "RESPONSÁVEL TÉCNICO", "resp_tecnico", "", 2.5, None),
         (40, "CREA / CFT", "crea", "", 2.5, None),
         (80, "ART Nº", "art", "", 2.5, None)]),
    (10, [(25, "ESCALA", "escala", "1:1", 3.5, "scale"),
          (15, "UNID.", "unidade", "mm", 3.5, None),
          (30, "1º DIEDRO", None, "", 0, None),
          (20, "FORMATO", "formato", "", 3.5, None),
          (25, "FOLHA", "folha", "1 / 1", 3.5, "sheet"),
          (45, "Nº DO DESENHO", "numero", "", 3.5, None),
          (20, "REV.", "revisao", "0", 3.5, None)]),
]
LETRA_ROTULO = 1.8
FONTE = "osifont"


def _f(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def _simbolo_1o_diedro(cx, cy, esc=1.0):
    """Símbolo do 1º diedro centrado em (cx, cy): tronco de cone visto de lado e de frente."""
    s = esc
    # geometria do modelo ISO do FreeCAD (CC0): trapézio 10 de comprimento, alturas 5 e 10;
    # círculos r 2,5 e 5 a 7 mm do fim do trapézio
    x0 = cx - 8.5 * s
    linhas = [
        '<g id="simbolo_1o_diedro" style="fill:none;stroke:#000000;stroke-width:%s;'
        'stroke-linecap:round;stroke-linejoin:round">' % _f(0.35 * s),
        '<path d="M %s,%s L %s,%s V %s L %s,%s Z"/>' % (
            _f(x0 + 10 * s), _f(cy - 5 * s), _f(x0), _f(cy - 2.5 * s), _f(cy + 2.5 * s),
            _f(x0 + 10 * s), _f(cy + 5 * s)),
        '<circle cx="%s" cy="%s" r="%s"/>' % (_f(x0 + 17 * s), _f(cy), _f(2.5 * s)),
        '<circle cx="%s" cy="%s" r="%s"/>' % (_f(x0 + 17 * s), _f(cy), _f(5 * s)),
        '</g>',
        '<g style="fill:none;stroke:#000000;stroke-width:%s;stroke-dasharray:%s,%s,%s,%s">' % (
            _f(0.18 * s), _f(3 * s), _f(0.6 * s), _f(0.4 * s), _f(0.6 * s)),
        '<path d="M %s,%s H %s"/>' % (_f(x0 - 1 * s), _f(cy), _f(x0 + 23 * s)),
        '<path d="M %s,%s V %s"/>' % (_f(x0 + 17 * s), _f(cy - 6 * s), _f(cy + 6 * s)),
        '</g>',
    ]
    return "\n".join(linhas)


def _texto(x, y, txt, tam, campo=None, auto=None, anchor="start", peso="normal", idt=None):
    attrs = ""
    if campo:
        attrs += ' freecad:editable="%s"' % campo
        if auto:
            attrs += ' freecad:autofill="%s"' % auto
    ident = ' id="%s"' % idt if idt else (' id="campo_%s"' % campo if campo else "")
    return ('<text%s x="%s" y="%s"%s style="font-size:%spx;font-family:%s;font-weight:%s;'
            'text-anchor:%s;fill:#000000;stroke:none"><tspan>%s</tspan></text>') % (
        ident, _f(x), _f(y), attrs, _f(tam), FONTE, peso, anchor, txt)


def _grade(larg, alt, m, espessura):
    """Sistema de referência por quadrículas de 50 mm contadas a partir das marcas de centro
    (ISO 5457): letras na vertical (de cima para baixo), números na horizontal (da esquerda);
    as quadrículas das pontas ficam com o que sobra até o quadro (no mínimo 20 mm)."""
    out = []
    x0, y0, x1, y1 = m["esq"], m["sup"], larg - m["dir"], alt - m["inf"]
    passo = 50.0

    def linhas(c, a, b):
        res = []
        k = 0
        while c + k * passo < b - 1e-6 or c - k * passo > a + 1e-6:
            for v in {c + k * passo, c - k * passo}:
                if a + 1e-6 < v < b - 1e-6:
                    res.append(v)
            k += 1
        # quadrícula da ponta menor que 20 mm é juntada à vizinha
        return sorted(set(round(v, 6) for v in res if v - a >= 20.0 - 1e-6 and b - v >= 20.0 - 1e-6))

    lx = linhas(larg / 2.0, x0, x1)
    ly = linhas(alt / 2.0, y0, y1)
    letras = [c for c in "ABCDEFGHJKLMNPQRSTUVWXYZ"]
    ext = min(m["sup"], m["inf"], m["dir"]) * 0.5
    out.append('<g id="quadriculas" style="fill:none;stroke:#000000;stroke-width:0.35">')
    for x in lx:
        out.append('<path d="M %s,%s V %s"/>' % (_f(x), _f(y0), _f(y0 - ext)))
        out.append('<path d="M %s,%s V %s"/>' % (_f(x), _f(y1), _f(y1 + ext)))
    for y in ly:
        out.append('<path d="M %s,%s H %s"/>' % (_f(x0), _f(y), _f(x0 - ext)))
        out.append('<path d="M %s,%s H %s"/>' % (_f(x1), _f(y), _f(x1 + ext)))
    out.append('</g>')
    tam = 2.5
    bx = [x0] + lx + [x1]
    by = [y0] + ly + [y1]
    for i in range(len(bx) - 1):
        x = (bx[i] + bx[i + 1]) / 2.0
        out.append(_texto(x, y0 - ext * 0.35, str(i + 1), tam, anchor="middle"))
        out.append(_texto(x, y1 + ext * 0.35 + tam * 0.75, str(i + 1), tam, anchor="middle"))
    for j in range(len(by) - 1):
        y = (by[j] + by[j + 1]) / 2.0 + tam * 0.35
        out.append(_texto(x0 - ext * 0.5, y, letras[j % len(letras)], tam, anchor="middle"))
        out.append(_texto(x1 + ext * 0.5, y, letras[j % len(letras)], tam, anchor="middle"))
    return out


def _legenda(x_dir, y_inf, largura, formato):
    esc = largura / 180.0
    h_total = sum(h for h, _c in LEGENDA)
    x0 = x_dir - largura
    y = y_inf - h_total
    out = ['<g id="legenda">',
           '<rect x="%s" y="%s" width="%s" height="%s" style="fill:none;stroke:#000000;stroke-width:0.7"/>'
           % (_f(x0), _f(y), _f(largura), _f(h_total))]
    linhas = []
    for h, celulas in LEGENDA:
        x = x0
        if y > y_inf - h_total + 1e-9:
            linhas.append('<path d="M %s,%s H %s"/>' % (_f(x0), _f(y), _f(x_dir)))
        for w, rotulo, campo, padrao, letra, auto in celulas:
            ww = w * esc
            if x > x0 + 1e-9:
                linhas.append('<path d="M %s,%s V %s"/>' % (_f(x), _f(y), _f(y + h)))
            out.append(_texto(x + 1.0, y + LETRA_ROTULO + 0.6, rotulo, LETRA_ROTULO))
            if campo:
                if campo == "formato":
                    padrao = formato
                tx = x + 1.5
                ty = y + h - (h - LETRA_ROTULO - 1.2 - letra) / 2.0 - 0.6
                peso = "bold" if campo in ("titulo", "numero") else "normal"
                out.append(_texto(tx, ty, padrao, letra, campo, auto, peso=peso))
            else:
                out.append(_simbolo_1o_diedro(x + ww / 2.0, y + h / 2.0 + 0.8, 0.55))
            x += ww
        y += h
    out.append('<g style="fill:none;stroke:#000000;stroke-width:0.35">')
    out.extend(linhas)
    out.append('</g>')
    out.append('</g>')
    return out, h_total


def gerar(formato, norma, retrato=False):
    n = NORMAS[norma]
    larg, alt = FORMATOS[formato]
    if retrato:
        larg, alt = alt, larg
    m = n["margem"][formato]
    esp = n["quadro"][formato]
    leg = n["legenda"][formato]
    x0, y0, x1, y1 = m["esq"], m["sup"], larg - m["dir"], alt - m["inf"]
    orient = "Retrato" if retrato else "Paisagem"
    titulo = "Prumo 3D — Folha %s %s — %s" % (formato, orient.lower(), n["titulo"])
    leg_svg, h_leg = _legenda(x1, y1, leg, formato)
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
           '<svg width="%smm" height="%smm" viewBox="0 0 %s %s" version="1.1" id="svg"' % (larg, alt, larg, alt),
           '   xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg"',
           '   xmlns:freecad="https://www.freecad.org/wiki/index.php?title=Svg_Namespace">',
           '<title>%s</title>' % titulo,
           '<desc>Gerado por prumo-build/ferramentas/gerar_folhas_abnt.py. Norma: %s. '
           'Margens (mm): esquerda %s, direita %s, superior %s, inferior %s. Quadro %s mm. '
           'Legenda %s × %s mm.</desc>' % (n["titulo"], m["esq"], m["dir"], m["sup"], m["inf"],
                                           _f(esp), leg, _f(h_leg))]
    # quadro (moldura da área de desenho)
    out.append('<rect id="quadro" x="%s" y="%s" width="%s" height="%s" style="fill:none;stroke:#000000;'
               'stroke-width:%s;stroke-linejoin:miter"/>' % (_f(x0), _f(y0), _f(x1 - x0), _f(y1 - y0), _f(esp)))
    # marcas de centro: no meio de cada lado, da borda do papel até 5 mm para dentro do quadro
    cxm, cym = larg / 2.0, alt / 2.0
    out.append('<g id="marcas_de_centro" style="fill:none;stroke:#000000;stroke-width:0.7">')
    out.append('<path d="M %s,0 V %s"/>' % (_f(cxm), _f(y0 + 5)))
    # embaixo, a marca não entra na legenda quando ela passa pelo meio da folha
    fim_inf = y1 if x1 - leg < cxm else y1 - 5
    out.append('<path d="M %s,%s V %s"/>' % (_f(cxm), _f(alt), _f(fim_inf)))
    out.append('<path d="M 0,%s H %s"/>' % (_f(cym), _f(x0 + 5)))
    out.append('<path d="M %s,%s H %s"/>' % (_f(larg), _f(cym), _f(x1 - 5)))
    out.append('</g>')
    # marcas de corte nos cantos (triângulos de 10 mm)
    if n["corte"]:
        out.append('<g id="marcas_de_corte" style="fill:#000000;stroke:none">')
        for (px, py, sx, sy) in ((0, 0, 1, 1), (larg, 0, -1, 1), (0, alt, 1, -1), (larg, alt, -1, -1)):
            out.append('<path d="M %s,%s L %s,%s L %s,%s Z"/>' % (
                _f(px), _f(py), _f(px + 10 * sx), _f(py), _f(px), _f(py + 10 * sy)))
        out.append('</g>')
    out.extend(_grade(larg, alt, m, esp))
    out.extend(leg_svg)
    out.append(_texto(x1 - leg, y1 - h_leg - 1.0, "Prumo 3D", 1.8, idt="marca"))
    out.append('</svg>')
    return "\n".join(out) + "\n"


def nome_arquivo(formato, norma, retrato):
    return "Prumo_%s_%s_%s.svg" % (formato, "Retrato" if retrato else "Paisagem", norma)


def main(saida):
    os.makedirs(saida, exist_ok=True)
    feitos = []
    for norma in NORMAS:
        for formato in FORMATOS:
            for retrato in ((True, False) if formato == "A4" else (False,)):
                caminho = os.path.join(saida, nome_arquivo(formato, norma, retrato))
                with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(gerar(formato, norma, retrato))
                feitos.append(caminho)
    return feitos


if __name__ == "__main__":
    aqui = os.path.dirname(os.path.abspath(__file__))
    padrao = os.path.join(aqui, "..", "..", "src", "Mod", "Prumo3D", "Resources", "folhas")
    for c in main(sys.argv[1] if len(sys.argv) > 1 else padrao):
        print(c)
