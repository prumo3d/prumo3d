# SPDX-License-Identifier: LGPL-2.1-or-later
"""Modelos com regras (como o iLogic do Inventor): um formulário gera a peça a partir de parâmetros.

Cada modelo é uma peça paramétrica (objeto "Modelo" na árvore) com os parâmetros no editor de
propriedades e regras de projeto que avisam quando algo não fecha (furo perto demais da borda,
espessura fina para o diâmetro do furo...). Duplo clique no objeto reabre o formulário.

Modelos:
- Placa com furos: placa de base / chapa de ligação com furação em grade e cantos arredondados;
- Flange circular: flange plana com furação em círculo;
- Suporte em L: cantoneira de chapa dobrada com furos nas duas abas;
- Eixo escalonado: trechos de diâmetro × comprimento, com chanfro nas pontas.
As regras de distância mínima furo-borda seguem a prática de 1,5×d (a checar contra a norma de
projeto usada, ex.: NBR 8800 tabela 14 para ligações estruturais).
"""

import math

import FreeCAD

V = FreeCAD.Vector

# (propriedade, rótulo, tipo, padrão, mínimo, máximo, ícone, dica)
MODELOS = {
    "placa": {
        "nome": "Placa com furos",
        "dica": "Placa de base ou chapa de ligação com furação em grade.",
        "parametros": [
            ("Comprimento", "Comprimento", "mm", 300.0, 10.0, 5000.0, "comprimento", "Medida em X"),
            ("Largura", "Largura", "mm", 200.0, 10.0, 5000.0, "largura", "Medida em Y"),
            ("Espessura", "Espessura", "mm", 12.5, 0.5, 200.0, "espessura", "Espessura da chapa"),
            ("RaioCanto", "Raio dos cantos", "mm", 10.0, 0.0, 500.0, "raio", "0 = canto vivo"),
            ("FurosX", "Furos em X", "int", 2, 0, 50, "quantidade", "Quantidade de furos ao longo do comprimento"),
            ("FurosY", "Furos em Y", "int", 2, 0, 50, "quantidade", "Quantidade de furos ao longo da largura"),
            ("DiametroFuro", "Diâmetro do furo", "mm", 18.0, 1.0, 200.0, "furo", "Diâmetro dos furos"),
            ("Borda", "Furo até a borda", "mm", 40.0, 1.0, 1000.0, "folga", "Do centro do furo à borda"),
        ],
    },
    "flange": {
        "nome": "Flange circular",
        "dica": "Flange plana com furação em círculo (PCD).",
        "parametros": [
            ("DiametroExterno", "Diâmetro externo", "mm", 200.0, 10.0, 5000.0, "largura", ""),
            ("DiametroInterno", "Diâmetro interno", "mm", 100.0, 0.0, 5000.0, "furo", "0 = flange cega"),
            ("Espessura", "Espessura", "mm", 16.0, 1.0, 300.0, "espessura", ""),
            ("Furos", "Número de furos", "int", 8, 0, 64, "quantidade", ""),
            ("DiametroFuracao", "Diâmetro da furação (PCD)", "mm", 160.0, 5.0, 5000.0, "posicao",
             "Diâmetro do círculo dos centros dos furos"),
            ("DiametroFuro", "Diâmetro do furo", "mm", 18.0, 1.0, 200.0, "furo", ""),
        ],
    },
    "suporte": {
        "nome": "Suporte em L",
        "dica": "Cantoneira de chapa dobrada com furos nas abas.",
        "parametros": [
            ("Aba1", "Aba horizontal", "mm", 80.0, 5.0, 2000.0, "comprimento", "Comprimento externo da aba de baixo"),
            ("Aba2", "Aba vertical", "mm", 60.0, 5.0, 2000.0, "altura", "Altura externa da aba de pé"),
            ("Largura", "Largura", "mm", 50.0, 5.0, 2000.0, "largura", ""),
            ("Espessura", "Espessura", "mm", 3.0, 0.5, 50.0, "espessura", ""),
            ("RaioDobra", "Raio interno da dobra", "mm", 3.0, 0.0, 200.0, "raio", ""),
            ("DiametroFuro", "Diâmetro do furo", "mm", 9.0, 0.0, 100.0, "furo", "0 = sem furos"),
        ],
    },
    "eixo": {
        "nome": "Eixo escalonado",
        "dica": "Trechos de diâmetro × comprimento ao longo de Z, com chanfro nas pontas.",
        "parametros": [
            ("Trechos", "Trechos (⌀×comprimento; …)", "texto", "30x40; 40x120; 30x40", None, None, "comprimento",
             "Exemplo: 30x40; 40x120; 30x40 (mm)"),
            ("Chanfro", "Chanfro nas pontas", "mm", 1.0, 0.0, 50.0, "chanfro", ""),
        ],
    },
}


# ------------------------------------------------------------------ geometria
def _placa(p):
    import Part
    L, W, t, r = p["Comprimento"], p["Largura"], p["Espessura"], p["RaioCanto"]
    caixa = Part.makeBox(L, W, t)
    if r > 0:
        r = min(r, L / 2.0 - 0.01, W / 2.0 - 0.01)
        verticais = [e for e in caixa.Edges if abs(e.BoundBox.ZLength - t) < 1e-6 and e.BoundBox.XLength < 1e-6
                     and e.BoundBox.YLength < 1e-6]
        caixa = caixa.makeFillet(r, verticais)
    furos = []
    for (x, y) in _grade(L, W, p["FurosX"], p["FurosY"], p["Borda"]):
        furos.append(Part.makeCylinder(p["DiametroFuro"] / 2.0, t + 2, V(x, y, -1)))
    for f in furos:
        caixa = caixa.cut(f)
    return caixa


def _grade(L, W, nx, ny, borda):
    if nx <= 0 or ny <= 0:
        return []
    xs = [borda] if nx == 1 else [borda + i * (L - 2 * borda) / (nx - 1) for i in range(nx)]
    ys = [borda] if ny == 1 else [borda + j * (W - 2 * borda) / (ny - 1) for j in range(ny)]
    return [(x, y) for x in xs for y in ys]


def _flange(p):
    import Part
    de, di, t = p["DiametroExterno"], p["DiametroInterno"], p["Espessura"]
    s = Part.makeCylinder(de / 2.0, t)
    if di > 0:
        s = s.cut(Part.makeCylinder(di / 2.0, t + 2, V(0, 0, -1)))
    n = int(p["Furos"])
    for k in range(n):
        a = 2 * math.pi * k / n
        c = V(p["DiametroFuracao"] / 2.0 * math.cos(a), p["DiametroFuracao"] / 2.0 * math.sin(a), -1)
        s = s.cut(Part.makeCylinder(p["DiametroFuro"] / 2.0, t + 2, c))
    return s


def _suporte(p):
    import Part
    a1, a2, w, t, r = p["Aba1"], p["Aba2"], p["Largura"], p["Espessura"], p["RaioDobra"]
    re_ = r + t
    # aba horizontal em z ∈ [0, t], aba vertical em x ∈ [0, t], dobra com raio interno r
    base = Part.makeBox(a1 - re_, w, t, V(re_, 0, 0))
    pe = Part.makeBox(t, w, a2 - re_, V(0, 0, re_))
    s = base.fuse(pe)
    # quarto de tubo na dobra (raio interno r, externo r+t), centro em (re_, ·, re_)
    tubo = Part.makeCylinder(re_, w, V(re_, 0, re_), V(0, 1, 0))
    if r > 0:
        tubo = tubo.cut(Part.makeCylinder(r, w, V(re_, 0, re_), V(0, 1, 0)))
    quadrante = Part.makeBox(re_, w, re_, V(0, 0, 0))
    s = s.fuse(tubo.common(quadrante))
    s = s.removeSplitter()
    d = p["DiametroFuro"]
    if d > 0:
        xh = re_ + (a1 - re_) / 2.0
        zh = re_ + (a2 - re_) / 2.0
        s = s.cut(Part.makeCylinder(d / 2.0, t + 2, V(xh, w / 2.0, -1), V(0, 0, 1)))
        s = s.cut(Part.makeCylinder(d / 2.0, t + 2, V(-1, w / 2.0, zh), V(1, 0, 0)))
    return s


def trechos(texto):
    """'30x40; 40x120' → [(30.0, 40.0), (40.0, 120.0)]"""
    res = []
    for parte in (texto or "").replace(",", ".").split(";"):
        parte = parte.strip().lower().replace("×", "x")
        if not parte:
            continue
        try:
            d, c = [float(v) for v in parte.split("x")]
        except ValueError:
            raise ValueError("trecho inválido: %r (use diâmetro x comprimento, ex.: 30x40)" % parte)
        if d <= 0 or c <= 0:
            raise ValueError("trecho com medida zero: %r" % parte)
        res.append((d, c))
    if not res:
        raise ValueError("informe ao menos um trecho")
    return res


def _eixo(p):
    import Part
    z = 0.0
    s = None
    ts = trechos(p["Trechos"])
    for d, c in ts:
        cil = Part.makeCylinder(d / 2.0, c, V(0, 0, z))
        s = cil if s is None else s.fuse(cil)
        z += c
    s = s.removeSplitter()
    ch = p["Chanfro"]
    if ch > 0:
        pontas = [e for e in s.Edges if hasattr(e.Curve, "Radius") and
                  (abs(e.BoundBox.ZMin) < 1e-6 or abs(e.BoundBox.ZMax - z) < 1e-6)]
        lim = min(ts[0][0], ts[-1][0]) / 2.0 - 0.01
        try:
            s = s.makeChamfer(min(ch, lim), pontas)
        except Exception:
            pass
    return s


GERADORES = {"placa": _placa, "flange": _flange, "suporte": _suporte, "eixo": _eixo}


# ------------------------------------------------------------------ regras de projeto
def impossivel(tipo, p):
    """Erros que impedem gerar a peça (geometria que não existe). None = pode gerar."""
    if tipo == "suporte":
        minimo = p["Espessura"] + p["RaioDobra"]
        for aba, nome in (("Aba1", "horizontal"), ("Aba2", "vertical")):
            if p[aba] <= minimo + 1e-6:
                return ("A aba %s (%s mm) precisa ser maior que espessura + raio da dobra (%s mm)."
                        % (nome, _f(p[aba]), _f(minimo)))
    elif tipo == "flange":
        if p["DiametroInterno"] >= p["DiametroExterno"]:
            return "O diâmetro interno precisa ser menor que o externo."
    elif tipo == "eixo":
        try:
            trechos(p["Trechos"])
        except ValueError as ex:
            return str(ex)
    return None


def regras(tipo, p):
    """Avisos (não impedem gerar): o que pode estar errado no projeto."""
    av = []
    d = p.get("DiametroFuro", 0)
    if tipo == "placa":
        if p["FurosX"] and p["FurosY"] and p["Borda"] < 1.5 * d:
            av.append("Furo muito perto da borda: use pelo menos 1,5 × ⌀ (%s mm)." % _f(1.5 * d))
        if 2 * p["Borda"] > min(p["Comprimento"], p["Largura"]) and (p["FurosX"] > 1 or p["FurosY"] > 1):
            av.append("A distância à borda não cabe: os furos se sobrepõem.")
        if d > 0 and p["Espessura"] < d / 4.0:
            av.append("Chapa fina para o furo (espessura < ⌀/4): confira o esmagamento.")
    elif tipo == "flange":
        if p["DiametroInterno"] >= p["DiametroExterno"]:
            av.append("Diâmetro interno maior que o externo.")
        anel_ext = (p["DiametroExterno"] - p["DiametroFuracao"]) / 2.0
        anel_int = (p["DiametroFuracao"] - p["DiametroInterno"]) / 2.0
        if p["Furos"] and min(anel_ext, anel_int) < d:
            av.append("A furação fica perto das bordas (menos de 1 ⌀ de material).")
        if p["Furos"] > 1:
            passo = math.pi * p["DiametroFuracao"] / p["Furos"]
            if passo < 2 * d:
                av.append("Furos muito próximos entre si (passo < 2 × ⌀).")
    elif tipo == "suporte":
        if p["RaioDobra"] < p["Espessura"]:
            av.append("Raio de dobra menor que a espessura: verifique o raio mínimo do material.")
        if d > 0 and (p["Aba1"] - p["Espessura"] - p["RaioDobra"]) < 2 * d:
            av.append("Aba horizontal curta para o furo.")
    elif tipo == "eixo":
        ts = trechos(p["Trechos"])
        for (d1, _c1), (d2, _c2) in zip(ts, ts[1:]):
            if max(d1, d2) / min(d1, d2) > 2:
                av.append("Degrau grande entre ⌀%s e ⌀%s: concentração de tensão alta." % (_f(d1), _f(d2)))
    return av


def _f(v):
    try:
        import PrumoUtil
        return PrumoUtil.fmt(v, 1)
    except Exception:
        return str(v)


# ------------------------------------------------------------------ objeto paramétrico
class Modelo:
    def __init__(self, obj, tipo):
        obj.addProperty("App::PropertyString", "TipoModelo", "Modelo", "Tipo do modelo").TipoModelo = tipo
        obj.setEditorMode("TipoModelo", 1)
        for nome, rotulo, kind, padrao, mn, mx, _ic, dica in MODELOS[tipo]["parametros"]:
            if kind == "mm":
                obj.addProperty("App::PropertyLength", nome, "Parâmetros", rotulo + (": " + dica if dica else ""))
            elif kind == "int":
                obj.addProperty("App::PropertyInteger", nome, "Parâmetros", rotulo + (": " + dica if dica else ""))
            else:
                obj.addProperty("App::PropertyString", nome, "Parâmetros", rotulo + (": " + dica if dica else ""))
            setattr(obj, nome, padrao)
        obj.addProperty("App::PropertyStringList", "Avisos", "Modelo", "Regras de projeto não atendidas")
        obj.setEditorMode("Avisos", 1)
        obj.Proxy = self

    def parametros(self, obj):
        p = {}
        for nome, _r, kind, _d, _mn, _mx, _ic, _dc in MODELOS[obj.TipoModelo]["parametros"]:
            v = getattr(obj, nome)
            p[nome] = float(v.Value) if hasattr(v, "Value") else v
        return p

    def execute(self, obj):
        p = self.parametros(obj)
        erro = impossivel(obj.TipoModelo, p)
        if erro:
            raise ValueError(erro)
        obj.Shape = GERADORES[obj.TipoModelo](p)
        obj.Avisos = regras(obj.TipoModelo, p)

    def dumps(self):
        return None

    def loads(self, state):
        return None


class VistaModelo:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.Object = vobj.Object

    def getIcon(self):
        import PrumoUtil
        return PrumoUtil.icone("lista_corte.svg")

    def doubleClicked(self, vobj):
        PainelModelo(vobj.Object).mostrar()
        return True

    def setEdit(self, vobj, mode=0):
        return False

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(doc, tipo, **valores):
    if tipo not in MODELOS:
        raise ValueError("modelo desconhecido: %s" % tipo)
    o = doc.addObject("Part::FeaturePython", "Modelo")
    Modelo(o, tipo)
    for k, v in valores.items():
        setattr(o, k, v)
    o.Label = MODELOS[tipo]["nome"]
    if FreeCAD.GuiUp:
        VistaModelo(o.ViewObject)
    doc.recompute()
    return o


# ------------------------------------------------------------------ painel
def PainelModelo(obj=None):
    import PrumoPainel as P
    from PySide import QtWidgets

    class _Painel(P.PainelTarefa):
        titulo = "Modelo com regras"
        ajuda = "Escolha o modelo e os parâmetros. As regras de projeto avisam o que não fecha."

        def __init__(self):
            self.obj = obj
            super().__init__()

        def montar(self):
            f = self.form
            s0 = f.secao("Modelo", "tipo")
            self.tipo = s0.linha("tipo", QtWidgets.QComboBox(), "Tipo de peça gerada.", "Modelo")
            for k, m in MODELOS.items():
                self.tipo.addItem(m["nome"], k)
            self.dica = s0.texto("")
            self.sec = f.secao("Parâmetros", "comprimento")
            self.campos = {}
            self.avisos = f.secao("Regras de projeto", "info").texto("")
            if self.obj is not None:
                self.tipo.setCurrentIndex(self.tipo.findData(self.obj.TipoModelo))
                self.tipo.setEnabled(False)
            self.tipo.currentIndexChanged.connect(lambda *_: self._campos())
            self._campos()

        def _campos(self):
            lay = self.sec.grade
            while lay.count():
                it = lay.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
                elif it.layout():
                    while it.layout().count():
                        w = it.layout().takeAt(0).widget()
                        if w:
                            w.deleteLater()
            self.sec._linha = 0
            self.campos = {}
            tipo = self.tipo.currentData()
            m = MODELOS[tipo]
            self.dica.setText(m["dica"])
            for nome, rotulo, kind, padrao, mn, mx, ic, dica in m["parametros"]:
                atual = getattr(self.obj, nome) if self.obj is not None else padrao
                atual = float(atual.Value) if hasattr(atual, "Value") else atual
                if kind == "mm":
                    w = P.numero(atual, mn, mx)
                    w.valueChanged.connect(lambda *_: self._regras())
                elif kind == "int":
                    w = QtWidgets.QSpinBox()
                    w.setRange(int(mn), int(mx))
                    w.setValue(int(atual))
                    w.valueChanged.connect(lambda *_: self._regras())
                else:
                    w = QtWidgets.QLineEdit(str(atual))
                    w.textChanged.connect(lambda *_: self._regras())
                self.campos[nome] = self.sec.linha(ic, w, dica or rotulo, rotulo)
            self._regras()

        def valores(self):
            res = {}
            for nome, w in self.campos.items():
                res[nome] = w.text() if isinstance(w, QtWidgets.QLineEdit) else w.value()
            return res

        def _regras(self):
            try:
                av = regras(self.tipo.currentData(), self.valores())
            except ValueError as ex:
                av = [str(ex)]
            self.avisos.setText("<br>".join("• " + a for a in av) if av else "Tudo certo com as regras.")
            self.atualizar()

        def pendencia(self):
            if FreeCAD.ActiveDocument is None:
                return "Abra ou crie um documento."
            try:
                return impossivel(self.tipo.currentData(), self.valores())
            except (KeyError, ValueError) as ex:
                return str(ex)

        def pronto_texto(self):
            return "Pronto: OK %s a peça." % ("atualiza" if self.obj is not None else "gera")

        def executar(self):
            vals = self.valores()
            if self.obj is None:
                self.obj = criar(FreeCAD.ActiveDocument, self.tipo.currentData(), **vals)
            else:
                for k, v in vals.items():
                    setattr(self.obj, k, v)
                self.obj.Document.recompute()
            return self.obj

    return _Painel()


class CmdModelo:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("lista_corte.svg"), "MenuText": "Modelo com regras",
                "ToolTip": "Gera placa com furos, flange, suporte em L ou eixo escalonado a partir de um "
                           "formulário, com regras de projeto que avisam o que não fecha."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelModelo().mostrar()
