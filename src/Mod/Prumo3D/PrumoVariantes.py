# SPDX-License-Identifier: LGPL-2.1-or-later
"""Variantes da peça (como as configurações/tabela de projeto do SolidWorks).

Uma planilha "Variantes" guarda os parâmetros (linhas) e as variantes (colunas: P, M, G...).
A coluna B tem os valores da variante ativa, com apelido igual ao nome do parâmetro, e as cotas
do modelo usam esses apelidos em expressões (ex.: Extrusao.Length = Variantes.comprimento).
Trocar a variante ativa (objeto "Variante ativa" na árvore, ou o painel) copia a coluna
escolhida para a coluna B e recalcula o modelo.

Layout da planilha:
    A1 "Parâmetro"  B1 "Valor ativo"  C1 "Unidade"  D1.. nomes das variantes
    A2.. nomes      B2.. valores ativos (apelido = nome)  C2.. unidades  D2.. valores
"""

import re

import FreeCAD

NOME_PLANILHA = "Variantes"
NOME_SELETOR = "VarianteAtiva"
COL_VAR0 = 3   # índice da coluna D (A=0)
_RE_NOME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _limpo(v):
    return str(v).lstrip("'") if v is not None else ""


def planilha(doc):
    for o in doc.Objects:
        if o.TypeId == "Spreadsheet::Sheet" and "PrumoVariantes" in o.PropertiesList:
            return o
    return None


def criar(doc, parametros=(), variantes=("Padrão",)):
    """Cria a planilha de variantes (e o seletor). parametros: [(nome, unidade, [valores...])]."""
    sh = planilha(doc)
    if sh is None:
        sh = doc.addObject("Spreadsheet::Sheet", NOME_PLANILHA)
        sh.Label = "Variantes da peça"
        sh.addProperty("App::PropertyBool", "PrumoVariantes", "Prumo", "Planilha de variantes do Prumo")
        sh.PrumoVariantes = True
        for c, t in (("A1", "Parâmetro"), ("B1", "Valor ativo"), ("C1", "Unidade")):
            sh.set(c, t)
        sh.setStyle("A1:Z1", "bold")
        sh.setColumnWidth("A", 140)
    for i, v in enumerate(variantes):
        if v not in nomes_variantes(sh):
            sh.set("%s1" % _col(COL_VAR0 + len(nomes_variantes(sh))), v)
    for nome, unidade, valores in parametros:
        adicionar_parametro(sh, nome, unidade, valores)
    doc.recompute()
    seletor(doc, criar_se_faltar=True)
    return sh


def nomes_variantes(sh):
    res = []
    i = COL_VAR0
    while True:
        try:
            v = _limpo(sh.getContents("%s1" % _col(i)))
        except Exception:
            v = ""
        if not v:
            return res
        res.append(v)
        i += 1


def parametros(sh):
    """[(linha, nome, unidade)]"""
    res = []
    r = 2
    while True:
        try:
            nome = _limpo(sh.getContents("A%d" % r))
        except Exception:
            nome = ""
        if not nome:
            return res
        try:
            un = _limpo(sh.getContents("C%d" % r))
        except Exception:
            un = ""
        res.append((r, nome, un))
        r += 1


def valor(sh, parametro, variante):
    for r, nome, un in parametros(sh):
        if nome == parametro:
            c = _col(COL_VAR0 + nomes_variantes(sh).index(variante))
            try:
                return _limpo(sh.getContents("%s%d" % (c, r))).lstrip("=")
            except Exception:
                return ""
    raise KeyError(parametro)


def adicionar_parametro(sh, nome, unidade="mm", valores=()):
    if not _RE_NOME.match(nome or ""):
        raise ValueError("nome de parâmetro inválido: %r (use letras, números e _ , sem espaço)" % nome)
    if any(n == nome for _r, n, _u in parametros(sh)):
        raise ValueError("parâmetro já existe: %s" % nome)
    r = len(parametros(sh)) + 2
    sh.set("A%d" % r, nome)
    sh.set("C%d" % r, unidade or "")
    vs = list(valores) or [0]
    nv = max(len(nomes_variantes(sh)), 1)
    for i in range(nv):
        v = vs[i] if i < len(vs) else vs[-1]
        sh.set("%s%d" % (_col(COL_VAR0 + i), r), _texto_valor(v, unidade))
    sh.set("B%d" % r, _texto_valor(vs[0], unidade))
    sh.setAlias("B%d" % r, nome)
    return r


def _texto_valor(v, unidade):
    if isinstance(v, str):
        return v
    s = ("%g" % v)
    return "=%s %s" % (s, unidade) if unidade else s


def adicionar_variante(sh, nome, copiar_de=None):
    vs = nomes_variantes(sh)
    if nome in vs:
        raise ValueError("variante já existe: %s" % nome)
    c = _col(COL_VAR0 + len(vs))
    sh.set("%s1" % c, nome)
    origem = copiar_de or (vs[0] if vs else None)
    for r, _n, un in parametros(sh):
        try:
            v = sh.getContents("%s%d" % (_col(COL_VAR0 + vs.index(origem)), r)) if origem else "0"
        except Exception:
            v = "0"
        sh.set("%s%d" % (c, r), v)
    _atualizar_enum(sh.Document)
    return c


def definir_valor(sh, parametro, variante, v):
    for r, nome, un in parametros(sh):
        if nome == parametro:
            c = _col(COL_VAR0 + nomes_variantes(sh).index(variante))
            sh.set("%s%d" % (c, r), _texto_valor(v, un))
            if ativa(sh.Document) == variante:
                sh.set("B%d" % r, _texto_valor(v, un))
            return
    raise KeyError(parametro)


def aplicar(doc, variante):
    """Torna a variante ativa: copia os valores para a coluna B e recalcula."""
    sh = planilha(doc)
    if sh is None:
        raise ValueError("o documento não tem variantes")
    vs = nomes_variantes(sh)
    if variante not in vs:
        raise ValueError("variante desconhecida: %s" % variante)
    c = _col(COL_VAR0 + vs.index(variante))
    for r, _n, _u in parametros(sh):
        sh.set("B%d" % r, sh.getContents("%s%d" % (c, r)))
    sel = seletor(doc)
    if sel is not None and sel.Variante != variante:
        sel.Proxy.aplicando = True
        try:
            sel.Variante = variante
        finally:
            sel.Proxy.aplicando = False
    doc.recompute()
    return variante


def ativa(doc):
    sel = seletor(doc)
    return sel.Variante if sel is not None else None


def ligar(obj, propriedade, parametro):
    """A propriedade (ex.: 'Length', ou 'Constraints.largura' num esboço) passa a seguir o parâmetro."""
    sh = planilha(obj.Document)
    if sh is None or not any(n == parametro for _r, n, _u in parametros(sh)):
        raise ValueError("parâmetro desconhecido: %s" % parametro)
    obj.setExpression(propriedade, "%s.%s" % (sh.Name, parametro))
    obj.Document.recompute()


# ------------------------------------------------------------------ seletor (na árvore)
class Seletor:
    """Objeto "Variante ativa": trocar a propriedade Variante aplica a variante."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyEnumeration", "Variante", "Variantes", "Variante ativa da peça")
        obj.Proxy = self
        self.aplicando = False

    def onChanged(self, obj, prop):
        if prop != "Variante" or getattr(self, "aplicando", False):
            return
        doc = obj.Document
        # abrindo o arquivo ou no Desfazer/Refazer: a planilha já volta com os valores certos
        if getattr(doc, "Restoring", False) or getattr(doc, "Transacting", False):
            return
        try:
            v = obj.Variante
            if v:
                self.aplicando = True
                aplicar(doc, v)
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: variante: %s\n" % exc)
        finally:
            self.aplicando = False

    def execute(self, obj):
        pass

    def onDocumentRestored(self, obj):
        self.aplicando = False

    def dumps(self):
        return None

    def loads(self, state):
        self.aplicando = False


def seletor(doc, criar_se_faltar=False):
    for o in doc.Objects:
        if o.Name.startswith(NOME_SELETOR) and "Variante" in o.PropertiesList:
            return o
    if not criar_se_faltar:
        return None
    o = doc.addObject("App::FeaturePython", NOME_SELETOR)
    Seletor(o)
    o.Label = "Variante ativa"
    _atualizar_enum(doc)
    return o


def _atualizar_enum(doc):
    sel = seletor(doc)
    sh = planilha(doc)
    if sel is None or sh is None:
        return
    vs = nomes_variantes(sh) or ["Padrão"]
    atual = sel.Variante if sel.Variante in vs else vs[0]
    sel.Proxy.aplicando = True
    try:
        sel.Variante = vs
        sel.Variante = atual
    finally:
        sel.Proxy.aplicando = False


# ------------------------------------------------------------------ painel
TIPOS_MEDIDA = ("App::PropertyLength", "App::PropertyDistance", "App::PropertyAngle", "App::PropertyQuantity",
                "App::PropertyFloat", "App::PropertyInteger", "App::PropertyQuantityConstraint",
                "App::PropertyFloatConstraint", "App::PropertyIntegerConstraint")


def propriedades_numericas(obj):
    """Propriedades de medida que dá para ligar (comprimentos, ângulos e cotas nomeadas do esboço)."""
    res = []
    for p in obj.PropertiesList:
        try:
            t = obj.getTypeIdOfProperty(p)
            st = obj.getPropertyStatus(p)
        except Exception:
            continue
        if t in TIPOS_MEDIDA and "ReadOnly" not in st and "Hidden" not in st and "Output" not in st:
            res.append(p)
    if obj.isDerivedFrom("Sketcher::SketchObject"):
        res += ["Constraints." + c.Name for c in obj.Constraints if c.Name and c.Driving]
    return res


def PainelVariantes(doc=None):
    import PrumoPainel as P
    from PySide import QtWidgets

    class _Painel(P.PainelTarefa):
        titulo = "Variantes da peça"
        ajuda = ("Parâmetros nas linhas, variantes nas colunas (P, M, G...). Ligue cada parâmetro a uma cota "
                 "do modelo e troque a variante ativa.")

        def __init__(self):
            self.doc = doc or FreeCAD.ActiveDocument
            self._mostrado = {}
            # tudo o que o painel faz (criar a tabela, parâmetros, ligar cotas, trocar a variante)
            # fica numa transação: Cancelar desfaz, OK vira um passo só no Desfazer
            self._transacao = self.doc is not None
            if self._transacao:
                self.doc.openTransaction(self.titulo)
            super().__init__()

        def _fechar_transacao(self, gravar):
            if not self._transacao:
                return
            self._transacao = False
            if gravar:
                self.doc.commitTransaction()
            else:
                self.doc.abortTransaction()
            self.doc.recompute()

        def accept(self):
            try:
                self.resultado = self.executar()
            except Exception as ex:
                self.form.mensagem.mostrar(str(ex), "erro")
                return False
            self._fechar_transacao(True)
            self._parar()
            return True

        def reject(self):
            self._fechar_transacao(False)
            self._parar()
            return True

        def close(self):
            self._fechar_transacao(False)
            super().close()

        def montar(self):
            f = self.form
            self.sh = planilha(self.doc) or criar(self.doc)
            s0 = f.secao("Variante ativa", "tipo")
            self.ativa = s0.linha("tipo", QtWidgets.QComboBox(), "A variante que o modelo mostra agora.",
                                  "Variante")
            s1 = f.secao("Tabela", "quantidade")
            self.tabela = s1.widget(QtWidgets.QTableWidget())
            self.tabela.setMinimumHeight(170)
            bl = QtWidgets.QHBoxLayout()
            self.novo_par = QtWidgets.QLineEdit()
            self.novo_par.setPlaceholderText("novo parâmetro (ex.: comprimento)")
            bt_par = QtWidgets.QPushButton("Parâmetro")
            bt_par.clicked.connect(self._add_parametro)
            self.nova_var = QtWidgets.QLineEdit()
            self.nova_var.setPlaceholderText("nova variante (ex.: G)")
            bt_var = QtWidgets.QPushButton("Variante")
            bt_var.clicked.connect(self._add_variante)
            caixa = QtWidgets.QWidget()
            g = QtWidgets.QGridLayout(caixa)
            g.setContentsMargins(0, 0, 0, 0)
            g.addWidget(self.novo_par, 0, 0)
            g.addWidget(bt_par, 0, 1)
            g.addWidget(self.nova_var, 1, 0)
            g.addWidget(bt_var, 1, 1)
            s1.widget(caixa)
            s2 = f.secao("Ligar a uma cota", "comprimento")
            self.objeto = f.caixa(s2, "Operação ou esboço", lambda o, s: [(o.Label, o)] if propriedades_numericas(o)
                                  else [], minimo=0, maximo=1)
            self.prop = s2.linha("comprimento", QtWidgets.QComboBox(), "Cota que vai seguir o parâmetro.",
                                 "Cota")
            self.par = s2.linha("quantidade", QtWidgets.QComboBox(), "Parâmetro da tabela.", "Parâmetro")
            bt_lig = QtWidgets.QPushButton("Ligar")
            bt_lig.clicked.connect(self._ligar)
            s2.widget(bt_lig)
            self.objeto.mudou.connect(self._props)
            self._recarregar()
            self.ativa.currentTextChanged.connect(self._trocar)

        def pendencia(self):
            return None

        def pronto_texto(self):
            return "Edite os valores na tabela; OK grava e aplica a variante ativa."

        def _recarregar(self):
            vs = nomes_variantes(self.sh)
            ps = parametros(self.sh)
            self.tabela.blockSignals(True)
            self.tabela.clear()
            self.tabela.setRowCount(len(ps))
            self.tabela.setColumnCount(len(vs) + 1)
            self.tabela.setHorizontalHeaderLabels(["Unidade"] + vs)
            self.tabela.setVerticalHeaderLabels([n for _r, n, _u in ps])
            self._mostrado = {}
            for i, (r, n, u) in enumerate(ps):
                self.tabela.setItem(i, 0, QtWidgets.QTableWidgetItem(u))
                for j, v in enumerate(vs):
                    txt = valor(self.sh, n, v).lstrip("=")
                    if u and txt.endswith(" " + u):
                        txt = txt[:-len(u) - 1]
                    self.tabela.setItem(i, j + 1, QtWidgets.QTableWidgetItem(txt))
                    self._mostrado[(n, v)] = txt
            self.tabela.blockSignals(False)
            self.ativa.blockSignals(True)
            self.ativa.clear()
            self.ativa.addItems(vs)
            if ativa(self.doc) in vs:
                self.ativa.setCurrentText(ativa(self.doc))
            self.ativa.blockSignals(False)
            self.par.clear()
            self.par.addItems([n for _r, n, _u in ps])

        def gravar_tabela(self):
            vs = nomes_variantes(self.sh)
            ps = parametros(self.sh)
            for i, (r, n, u) in enumerate(ps):
                for j, v in enumerate(vs):
                    it = self.tabela.item(i, j + 1)
                    if it is None:
                        continue
                    bruto = it.text().strip()
                    if bruto == self._mostrado.get((n, v)):
                        continue   # não mexeu: fica como está (inclusive fórmulas)
                    try:
                        definir_valor(self.sh, n, v, float(bruto.replace(",", ".")))
                    except ValueError:
                        # fórmula ou valor com unidade ("largura/2", "20 mm"): grava como expressão
                        definir_valor(self.sh, n, v, bruto if bruto.startswith("=") or not bruto
                                      else "=" + bruto)
                    self._mostrado[(n, v)] = bruto

        def _add_parametro(self):
            nome = self.novo_par.text().strip()
            try:
                self.gravar_tabela()
                adicionar_parametro(self.sh, nome, "mm", [0])
                self.novo_par.clear()
                self._recarregar()
            except ValueError as ex:
                self.form.mensagem.mostrar(str(ex), "erro")

        def _add_variante(self):
            nome = self.nova_var.text().strip()
            try:
                self.gravar_tabela()
                adicionar_variante(self.sh, nome, self.ativa.currentText() or None)
                self.nova_var.clear()
                self._recarregar()
            except ValueError as ex:
                self.form.mensagem.mostrar(str(ex), "erro")

        def _props(self):
            self.prop.clear()
            vs = self.objeto.valores()
            if vs:
                self.prop.addItems(propriedades_numericas(vs[0]))

        def _ligar(self):
            vs = self.objeto.valores()
            if not vs or not self.prop.currentText() or not self.par.currentText():
                self.form.mensagem.mostrar("Escolha a operação, a cota e o parâmetro.", "erro")
                return
            try:
                self.gravar_tabela()
                aplicar(self.doc, self.ativa.currentText())
                ligar(vs[0], self.prop.currentText(), self.par.currentText())
                self.form.mensagem.mostrar("%s.%s segue %s." % (vs[0].Label, self.prop.currentText(),
                                                                 self.par.currentText()), "ok")
            except Exception as ex:
                self.form.mensagem.mostrar(str(ex), "erro")

        def _trocar(self, v):
            if v:
                self.gravar_tabela()
                aplicar(self.doc, v)

        def executar(self):
            self.gravar_tabela()
            if self.ativa.currentText():
                aplicar(self.doc, self.ativa.currentText())
            return self.sh

    return _Painel()


class CmdVariantes:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("lista_corte.svg"), "MenuText": "Variantes da peça",
                "ToolTip": "Tabela de variantes (P, M, G...): parâmetros ligados às cotas do modelo; trocar a "
                           "variante recalcula a peça."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelVariantes().mostrar()
