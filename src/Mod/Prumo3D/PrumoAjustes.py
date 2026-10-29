# SPDX-License-Identifier: LGPL-2.1-or-later
"""Ajuste furo/eixo pelo sistema ISO 286 (ABNT NBR 6158), em português e em cartões.

Escolhe-se o ajuste (furo-base ou eixo-base, dos ajustes preferenciais) e a cota; o Prumo põe a classe e os
afastamentos na cota e mostra a folga ou a interferência máxima e mínima.

Tabelas (µm, faixas de dimensão nominal até 500 mm):
- graus de tolerância IT6 a IT11 (ISO 286-1);
- afastamentos fundamentais dos eixos c, d, e, f, g, h (superior, es) e k, n, r, s (inferior, ei);
- furos pela regra da ISO 286-1: A–H com EI = −es do eixo da mesma letra; K e N (até IT8) e R e S (até IT7)
  com ES = −ei + Δ, Δ = IT(n) − IT(n−1); até 3 mm, Δ = 0.
Conferência: todos os valores daqui batem, célula por célula, com a tabela independente que vem com o FreeCAD
(TechDrawTools/TaskHoleShaftFit.py) — o teste T85 refaz essa conferência. Ainda assim, para documento com ART,
conferir com a edição vigente da NBR 6158 / ISO 286-2.
"""

# faixas de dimensão nominal (mm): acima de / até
LIMITES = [0, 3, 6, 10, 14, 18, 24, 30, 40, 50, 65, 80, 100, 120, 140, 160, 180, 200, 225, 250, 280, 315, 355,
           400, 450, 500]

# graus IT (µm) nas 25 faixas acima (as subdivisões repetem o valor da faixa principal)
_IT = {
    6: [6, 8, 9, 11, 11, 13, 13, 16, 16, 19, 19, 22, 22, 25, 25, 25, 29, 29, 29, 32, 32, 36, 36, 40, 40],
    7: [10, 12, 15, 18, 18, 21, 21, 25, 25, 30, 30, 35, 35, 40, 40, 40, 46, 46, 46, 52, 52, 57, 57, 63, 63],
    8: [14, 18, 22, 27, 27, 33, 33, 39, 39, 46, 46, 54, 54, 63, 63, 63, 72, 72, 72, 81, 81, 89, 89, 97, 97],
    9: [25, 30, 36, 43, 43, 52, 52, 62, 62, 74, 74, 87, 87, 100, 100, 100, 115, 115, 115, 130, 130, 140, 140, 155,
        155],
    10: [40, 48, 58, 70, 70, 84, 84, 100, 100, 120, 120, 140, 140, 160, 160, 160, 185, 185, 185, 210, 210, 230, 230,
         250, 250],
    11: [60, 75, 90, 110, 110, 130, 130, 160, 160, 190, 190, 220, 220, 250, 250, 250, 290, 290, 290, 320, 320, 360,
         360, 400, 400],
}

# afastamento superior es (µm) dos eixos a–h
_ES = {
    "c": [-60, -70, -80, -95, -95, -110, -110, -120, -130, -140, -150, -170, -180, -200, -210, -230, -240, -260,
          -280, -300, -330, -360, -400, -440, -480],
    "d": [-20, -30, -40, -50, -50, -65, -65, -80, -80, -100, -100, -120, -120, -145, -145, -145, -170, -170, -170,
          -190, -190, -210, -210, -230, -230],
    "e": [-14, -20, -25, -32, -32, -40, -40, -50, -50, -60, -60, -72, -72, -85, -85, -85, -100, -100, -100, -110,
          -110, -125, -125, -135, -135],
    "f": [-6, -10, -13, -16, -16, -20, -20, -25, -25, -30, -30, -36, -36, -43, -43, -43, -50, -50, -50, -56, -56,
          -62, -62, -68, -68],
    "g": [-2, -4, -5, -6, -6, -7, -7, -9, -9, -10, -10, -12, -12, -14, -14, -14, -15, -15, -15, -17, -17, -18, -18,
          -20, -20],
    "h": [0] * 25,
}

# afastamento inferior ei (µm) dos eixos k–s (k: graus 4 a 7)
_EI = {
    "k": [0, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 5, 5],
    "n": [4, 8, 10, 12, 12, 15, 15, 17, 17, 20, 20, 23, 23, 27, 27, 27, 31, 31, 31, 34, 34, 37, 37, 40, 40],
    "r": [10, 15, 19, 23, 23, 28, 28, 34, 34, 41, 43, 51, 54, 63, 65, 68, 77, 80, 84, 94, 98, 108, 114, 126, 132],
    "s": [14, 19, 23, 28, 28, 35, 35, 43, 43, 53, 59, 71, 79, 92, 100, 108, 122, 130, 140, 158, 170, 190, 208, 232,
          252],
}

# ajustes preferenciais (ISO 286-1), com o uso em português
FURO_BASE = [
    ("H11/c11", "Folga grande: montagem livre, peças fundidas ou com sujeira"),
    ("H9/d9", "Folga livre: mancais com folga larga, polias soltas"),
    ("H8/f7", "Deslizante com folga: mancais de bucha, eixos que giram"),
    ("H7/g6", "Deslizante preciso: guias, pinos que entram com a mão"),
    ("H7/h6", "Localização com folga: montagem justa, desmonta com a mão"),
    ("H7/k6", "Incerto (transição): engrenagem e polia com chaveta"),
    ("H7/n6", "Incerto mais firme: montagem com martelo de borracha"),
    ("H7/r6", "Interferência leve: buchas prensadas, transmite pouca força"),
    ("H7/s6", "Interferência média: prensado a frio ou montado a quente"),
]
EIXO_BASE = [
    ("C11/h11", "Folga grande: montagem livre"),
    ("D9/h9", "Folga livre"),
    ("F8/h7", "Deslizante com folga"),
    ("G7/h6", "Deslizante preciso"),
    ("H7/h6", "Localização com folga"),
    ("K7/h6", "Incerto (transição)"),
    ("N7/h6", "Incerto mais firme"),
    ("R7/h6", "Interferência leve"),
    ("S7/h6", "Interferência média"),
]

SITUACAO_DADOS = "conferir na edição vigente da ABNT NBR 6158 / ISO 286-2"


def faixa(D):
    """Índice da faixa de dimensão nominal (acima de / até)."""
    D = float(D)
    if not 0 < D <= LIMITES[-1]:
        raise ValueError("Dimensão fora das tabelas (até 500 mm).")
    k = 1
    while D > LIMITES[k]:
        k += 1
    return k - 1


def it(grau, D):
    if grau not in _IT:
        raise ValueError("Grau IT%d fora das tabelas (IT6 a IT11)." % grau)
    return _IT[grau][faixa(D)]


def separar(classe):
    """'H7' -> ('H', 7); 'js6' -> ('js', 6)."""
    letras = "".join(c for c in classe if c.isalpha())
    num = "".join(c for c in classe if c.isdigit())
    if not letras or not num:
        raise ValueError("Classe de tolerância inválida: %s" % classe)
    return letras, int(num)


def eixo(letra, grau, D):
    """(afastamento superior, inferior) do eixo, em µm."""
    i = faixa(D)
    t = it(grau, D)
    if letra in _ES:
        es = _ES[letra][i]
        return es, es - t
    if letra in _EI:
        if letra == "k" and not 4 <= grau <= 7:
            raise ValueError("Eixo k só de IT4 a IT7 nestas tabelas.")
        ei = _EI[letra][i]
        return ei + t, ei
    raise ValueError("Eixo %s%d fora das tabelas." % (letra, grau))


def furo(letra, grau, D):
    """(afastamento superior, inferior) do furo, em µm."""
    i = faixa(D)
    t = it(grau, D)
    min_ = letra.lower()
    if letra.isupper() and min_ in _ES:
        EI = -_ES[min_][i]
        return EI + t, EI
    if letra in ("K", "N", "R", "S"):
        limite = 8 if letra in ("K", "N") else 7
        if grau > limite:
            raise ValueError("Furo %s%d fora das tabelas (até IT%d)." % (letra, grau, limite))
        delta = 0 if i == 0 else t - it(grau - 1, D)
        ES = -_EI[min_][i] + delta
        if letra == "K" and i == 0:
            ES = 0
        return ES, ES - t
    raise ValueError("Furo %s%d fora das tabelas." % (letra, grau))


def classe(cl, D):
    letra, grau = separar(cl)
    return furo(letra, grau, D) if letra[0].isupper() else eixo(letra, grau, D)


class Ajuste:
    def __init__(self, nome, D):
        f, e = nome.split("/")
        self.nome, self.D = nome, float(D)
        self.furo_classe, self.eixo_classe = f, e
        self.furo = classe(f, D)        # (sup, inf) µm
        self.eixo = classe(e, D)
        self.folga_max = self.furo[0] - self.eixo[1]      # µm (negativo = interferência)
        self.folga_min = self.furo[1] - self.eixo[0]

    @property
    def tipo(self):
        if self.folga_min >= 0:
            return "folga"
        if self.folga_max <= 0:
            return "interferência"
        return "incerto"

    def resumo(self):
        mm = lambda v: ("%+.3f" % (v / 1000.0)).replace(".", ",")  # noqa: E731
        if self.tipo == "folga":
            txt = "Folga de %s a %s mm" % (mm(self.folga_min)[1:], mm(self.folga_max)[1:])
        elif self.tipo == "interferência":
            txt = "Interferência de %s a %s mm" % (mm(-self.folga_max)[1:], mm(-self.folga_min)[1:])
        else:
            txt = "Incerto: de %s mm de folga a %s mm de interferência" % (mm(self.folga_max)[1:],
                                                                           mm(-self.folga_min)[1:])
        return txt


def _fmt_mm(v):
    return ("%+.3f" % (v / 1000.0)).replace(".", ",") if v else "0"


def aplicar_na_cota(dim, cl):
    """Põe a classe (ex.: H7) e os afastamentos numa cota do desenho."""
    D = abs(float(dim.getRawValue()))
    sup, inf = classe(cl, D)
    fmt = str(dim.FormatSpec)
    base = fmt.split(" ")[0] if " " in fmt and fmt.split(" ")[-1][:1].isalpha() else fmt
    dim.FormatSpec = base + " " + cl
    dim.EqualTolerance = False
    dim.OverTolerance = sup / 1000.0
    dim.UnderTolerance = inf / 1000.0
    for prop, v in (("FormatSpecOverTolerance", sup), ("FormatSpecUnderTolerance", inf)):
        setattr(dim, prop, "(%-0.6w)" if v < 0 else ("(+%-0.6w)" if v > 0 else "( %-0.6w)"))
    dim.recompute()
    return sup, inf


# ======================================================================== interface
import FreeCAD

try:
    import FreeCADGui
    from PySide import QtWidgets
    import PrumoPainel as P
except ImportError:  # pragma: no cover
    FreeCADGui = P = None


def _filtro_cota(obj, subs):
    return [(obj.Label, obj)] if obj.isDerivedFrom("TechDraw::DrawViewDimension") else []


if P is not None:
    class PainelAjuste(P.PainelTarefa):
        titulo = "Ajuste furo/eixo"
        ajuda = ("Escolha a cota do diâmetro (ou digite o diâmetro) e o ajuste. O Prumo põe a classe e os "
                 "afastamentos na cota e mostra a folga ou a interferência.")

        def montar(self):
            f = self.form
            s0 = f.secao("Cota", "selecao")
            self.cota = f.caixa(s0, "Cota do diâmetro", _filtro_cota, minimo=0, maximo=1,
                                dica="Clique na cota na folha. Sem cota, serve como calculadora.")
            self.D = s0.linha("comprimento", P.numero(25.0, 0.1, 500.0, " mm", 2), "Diâmetro nominal (até 500 mm).",
                              "Diâmetro nominal")
            self.peca = P.Opcoes([("furo", "É um furo", "furo", "A cota é do furo"),
                                  ("eixo", "É um eixo", "comprimento", "A cota é do eixo")])
            s0.widget(self.peca)
            s1 = f.secao("Ajuste", "folga")
            self.sistema = P.Opcoes([("furo", "Furo-base (H)", "furo", "O furo é H; o eixo muda (o mais usado)"),
                                     ("eixo", "Eixo-base (h)", "comprimento", "O eixo é h; o furo muda")])
            s1.widget(self.sistema)
            self.ajuste = QtWidgets.QComboBox()
            s1.linha("tipo", self.ajuste, "Ajustes preferenciais da ISO 286.", "Ajuste")
            s2 = f.secao("Resultado", "info")
            self.res = s2.texto("")
            self.nota = s2.texto("Tabelas ISO 286 (ABNT NBR 6158), faixas até 500 mm: %s." % SITUACAO_DADOS)
            self.sistema.mudou.connect(self._listar)
            self.ajuste.currentIndexChanged.connect(self._atualizar_resultado)
            self.D.valueChanged.connect(self._atualizar_resultado)
            self.peca.mudou.connect(self._atualizar_resultado)
            self.cota.mudou.connect(self._cota_mudou)
            self._listar()

        def _cota_mudou(self):
            vs = self.cota.valores()
            if vs:
                try:
                    self.D.setValue(abs(float(vs[0].getRawValue())))
                except Exception:
                    pass
                fmt = str(getattr(vs[0], "FormatSpec", ""))
                if "⌀" in fmt or "Ø" in fmt or getattr(vs[0], "Type", "") == "Diameter":
                    pass
            self._atualizar_resultado()

        def _listar(self, *_a):
            self.ajuste.blockSignals(True)
            self.ajuste.clear()
            for nome, uso in (FURO_BASE if self.sistema.valor() == "furo" else EIXO_BASE):
                self.ajuste.addItem("%s — %s" % (nome, uso), nome)
            self.ajuste.setCurrentIndex(3)
            self.ajuste.blockSignals(False)
            self._atualizar_resultado()

        def atual(self):
            return Ajuste(self.ajuste.currentData(), self.D.value())

        def _atualizar_resultado(self, *_a):
            try:
                a = self.atual()
            except ValueError as ex:
                self.res.setText(str(ex))
                return
            D = self.D.value()
            txt = ("Furo Ø%s %s: %s / %s mm<br>Eixo Ø%s %s: %s / %s mm<br><b>%s</b> (%s)" % (
                ("%g" % D).replace(".", ","), a.furo_classe, _fmt_mm(a.furo[0]), _fmt_mm(a.furo[1]),
                ("%g" % D).replace(".", ","), a.eixo_classe, _fmt_mm(a.eixo[0]), _fmt_mm(a.eixo[1]),
                a.resumo(), a.tipo))
            if self.cota.valores():
                txt += "<br>Na cota vai: %s" % (a.furo_classe if self.peca.valor() == "furo" else a.eixo_classe)
            self.res.setText(txt)

        def pendencia(self):
            try:
                self.atual()
            except ValueError as ex:
                return str(ex)
            return None

        def pronto_texto(self):
            return ("OK põe a classe e os afastamentos na cota." if self.cota.valores()
                    else "Sem cota escolhida: só mostra os valores (escolha a cota para aplicar).")

        def executar(self):
            vs = self.cota.valores()
            if not vs:
                return []
            a = self.atual()
            aplicar_na_cota(vs[0], a.furo_classe if self.peca.valor() == "furo" else a.eixo_classe)
            return vs

    class CmdAjuste:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("cotas.svg"), "MenuText": "Ajuste furo/eixo",
                    "ToolTip": "Ajuste ISO 286 (NBR 6158) em português: põe a classe (H7, g6...) e os "
                               "afastamentos na cota e mostra a folga ou a interferência."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelAjuste().mostrar()


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_AjusteFuroEixo", CmdAjuste())
