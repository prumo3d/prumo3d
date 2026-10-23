# SPDX-License-Identifier: LGPL-2.1-or-later
"""Assistente de análise de estruturas: o passo a passo da simulação por barras, no mesmo formato do
Assistente de simulação (elementos finitos).

Etapas numeradas com estado (vazio, pendência, aviso, ok). Cada etapa confere o que já foi feito e
aponta o que falta; a edição (clicar nos nós, nas barras) continua no painel da simulação, que o
assistente abre já no modo certo. O cálculo só libera sem pendências, e o relatório sai no fim.

A conferência (avaliar) não calcula nada: lê a análise e o último resultado em memória, para poder
rodar a cada segundo sem pesar.
"""
import os

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

import PrumoEstilo
import PrumoFEM as F
from PrumoFEM import OK, AVISO, ERRO, VAZIO

ETAPAS = [
    ("estrutura", "Estrutura", "O que vai ser calculado"),
    ("material", "Material", "Aço das barras"),
    ("apoios", "Apoios", "Onde a estrutura está presa"),
    ("rotulas", "Rótulas e treliças", "Ligações flexíveis (opcional)"),
    ("cargas", "Casos de carga", "Ações sobre a estrutura"),
    ("criterios", "Critérios", "2ª ordem e limites de deslocamento"),
    ("calculo", "Verificar e calcular", "Pendências e cálculo"),
    ("resultado", "Resultados", "Taxas de uso, deslocamentos e avisos"),
    ("ligacoes", "Ligações", "Detalhe do nó por elementos finitos (opcional)"),
    ("relatorio", "Relatório", "Memória de cálculo em PDF"),
]
ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "icons", "assistente_fem.svg")
_estado = {"dock": None}


# =========================================================================== conferência
def _nivel(msgs):
    if any(n == ERRO for n, _m in msgs):
        return ERRO
    return AVISO if msgs else OK


def _calc(an):
    return getattr(getattr(an, "Proxy", None), "calc", None) if an is not None else None


def _desatualizada(an):
    """Os dados mudaram depois do último cálculo (mudar o que a tela mostra não conta)."""
    import PrumoAnaliseEstrutura as A
    try:
        return getattr(an.Proxy, "assinatura", None) != A.assinatura(an)
    except Exception:
        return True


def _componentes(m):
    """Quantos pedaços desligados tem o modelo (barras que não se tocam)."""
    pai = list(range(len(m.nos)))

    def raiz(a):
        while pai[a] != a:
            pai[a] = pai[pai[a]]
            a = pai[a]
        return a
    for b in m.barras:
        pai[raiz(b.i)] = raiz(b.j)
    usados = {b.i for b in m.barras} | {b.j for b in m.barras}
    return len({raiz(n) for n in usados})


def avaliar(an, est=None):
    """Estado de cada etapa: {chave: (nível, resumo, [(nível, mensagem)])} e "_bloqueios"."""
    import PrumoAnaliseEstrutura as A
    import PrumoEstrutura as E
    r = {}
    if an is not None:
        est = an.Estrutura
    calc = _calc(an)

    # 1 estrutura
    if est is None or not E.eh_estrutura(est):
        r["estrutura"] = (VAZIO, "Escolha a estrutura soldada", [(ERRO, "Nenhuma estrutura escolhida.")])
    else:
        msgs = []
        bs = E.barras_de(est)
        if not bs:
            msgs.append((ERRO, "A estrutura não tem barras: crie um grupo de perfis e clique nas linhas."))
        conferir = []
        try:
            import PrumoPerfis
            for b in bs:
                it = PrumoPerfis.perfil(b.Perfil)
                if it is not None and not PrumoPerfis.confiavel(it) and it["nome"] not in conferir:
                    conferir.append(it["nome"])
        except Exception:
            pass
        if conferir:
            msgs.append((AVISO, "Perfil com dados a conferir no catálogo do fabricante: %s." % ", ".join(conferir)))
        if an is None:
            msgs.append((ERRO, "Crie a análise da estrutura (botão abaixo)."))
        elif calc is not None and calc.modelo is not None and calc.modelo.barras:
            n = _componentes(calc.modelo)
            if n > 1:
                msgs.append((ERRO, "A estrutura tem %d partes que não se tocam: confira se as linhas do esqueleto "
                                   "se encontram nos nós." % n))
        r["estrutura"] = (_nivel(msgs), "%s · %d barra%s" % (est.Label, len(bs), "" if len(bs) == 1 else "s"),
                          msgs)

    if an is None:
        for k, _t, sub in ETAPAS[1:]:
            r[k] = (VAZIO, sub, [])
        r["_bloqueios"] = [("estrutura", m) for n, m in r["estrutura"][2] if n == ERRO] or \
            [("estrutura", "Crie a análise.")]
        return r

    # 2 material
    nome, fy, fu = an.Proxy.material(an)
    msgs = []
    if "padrão" in nome:
        msgs.append((AVISO, "Material não informado: verificado como ASTM A36 (fy 250, fu 400 MPa). Escolha o aço "
                            "real das barras."))
    if not (fy > 0 and fu > fy):
        msgs.append((ERRO, "fy e fu do material não fazem sentido (fy %s, fu %s MPa)." % (fy, fu)))
    r["material"] = (_nivel(msgs), "%s · fy %s / fu %s MPa" % (nome.split(" (padrão")[0], F.fmt(fy, 0),
                                                              F.fmt(fu, 0)), msgs)

    # 3 apoios
    apoios = an.Proxy.apoios(an)
    msgs = []
    if not apoios:
        r["apoios"] = (VAZIO, "Clique nos nós para pôr os apoios",
                       [(ERRO, "Sem apoio a estrutura não se sustenta.")])
    else:
        tipos = {}
        for t in apoios.values():
            chave = "mola" if t.startswith("Mola:") else t.lower()
            tipos[chave] = tipos.get(chave, 0) + 1
            if t.startswith("Mola:") and not any(A.rigidez_mola(t)):
                msgs.append((ERRO, "Há mola com rigidez zero: é o mesmo que não ter apoio."))
        if calc is not None and calc.erro:
            msgs.append((ERRO, "O cálculo não fecha: %s." % calc.erro))
        if calc is not None and calc.modelo is not None:
            nos_modelo = calc.modelo.nos
            for k in apoios:
                p = A._ponto_da_chave(k)
                if A._no_mais_proximo(calc.modelo, p, 1.0) is None and nos_modelo:
                    msgs.append((ERRO, "Apoio em (%s) não cai em nenhum nó (o desenho mudou?): tire e ponha de "
                                       "novo." % k.replace(";", "; ")))
        def plural(t, n):
            if n == 1:
                return t
            cab, _sep, resto = t.partition(" ")
            return cab + "s" + (" " + resto if resto else "")
        txt = ", ".join("%d %s" % (n, plural(t, n)) for t, n in sorted(tipos.items()))
        r["apoios"] = (_nivel(msgs), "%d apoio%s: %s" % (len(apoios), "" if len(apoios) == 1 else "s", txt), msgs)

    # 4 rótulas
    lib = an.Proxy.liberacoes(an)
    msgs = []
    if calc is not None and calc.mapa is not None:
        for i in lib:
            if i not in calc.mapa["linhas"]:
                msgs.append((ERRO, "Rótula na barra %d, que não existe mais: tire no painel." % (i + 1)))
    if lib:
        r["rotulas"] = (_nivel(msgs), "%d barra%s com rótula ou treliça" % (len(lib), "" if len(lib) == 1 else "s"),
                        msgs)
    else:
        r["rotulas"] = (OK, "Todas as ligações rígidas (soldadas)", [])

    # 5 cargas
    casos = an.Proxy.casos(an)
    msgs = []
    nlin = len(calc.mapa["linhas"]) if calc is not None and calc.mapa else None
    tem_carga = False
    tem_variavel = tem_vento = False
    for c in casos:
        tipo = A.TIPOS_CASO.get(c["tipo"], (0, 0, 0, 0, 0, ""))[5]
        cargas = c.get("cargas", [])
        if c.get("peso_proprio"):
            tem_carga = True
        if cargas:
            tem_carga = True
        if tipo != "permanente" and cargas:
            tem_variavel = True
        if tipo == "vento":
            tem_vento = True
            if cargas and all(not any(A.DIRECOES.get(x.get("direcao", ""), (0, 0, -1))[:2]) for x in cargas):
                msgs.append((AVISO, "O caso de vento “%s” só tem cargas verticais: confira as pressões laterais."
                             % c["nome"]))
        if not cargas and not c.get("peso_proprio"):
            msgs.append((AVISO, "O caso “%s” está sem cargas." % c["nome"]))
        for x in cargas:
            try:
                v = float(x.get("valor", 0.0))
            except (TypeError, ValueError):
                v = 0.0
            if abs(v) < 1e-12 and abs(float(x.get("valor2", 0.0) or 0.0)) < 1e-12:
                msgs.append((ERRO, "Carga com valor zero no caso “%s”." % c["nome"]))
            if x.get("alvo") == "barra" and nlin is not None and int(x.get("linha", -1)) >= nlin:
                msgs.append((ERRO, "Carga do caso “%s” numa barra que não existe mais (barra %d)." % (
                    c["nome"], int(x["linha"]) + 1)))
            if x.get("alvo") == "no" and calc is not None and calc.modelo is not None and \
                    A._no_mais_proximo(calc.modelo, A._ponto_da_chave(x["no"]), 1.0) is None:
                msgs.append((ERRO, "Carga do caso “%s” num nó que não existe mais." % c["nome"]))
    if not tem_carga:
        r["cargas"] = (VAZIO, "Monte os casos de carga", [(ERRO, "Nenhuma carga: não há o que calcular.")])
    else:
        if not tem_variavel:
            msgs.append((AVISO, "Só cargas permanentes: confira a sobrecarga de uso ou de manutenção exigida pela "
                                "norma da edificação."))
        if not tem_vento:
            msgs.append((AVISO, "Sem caso de vento: se a estrutura fica exposta, as forças de vento (ABNT NBR "
                                "6123) entram como caso próprio."))
        r["cargas"] = (_nivel(msgs), "%d caso%s de carga" % (len(casos), "" if len(casos) == 1 else "s"), msgs)

    # 6 critérios
    msgs = []
    so = bool(getattr(an, "SegundaOrdem", True))
    if not so:
        msgs.append((AVISO, "Análise de 1ª ordem: só vale para estrutura de pequena deslocabilidade (o cálculo "
                            "confere e avisa)."))
    r["criterios"] = (_nivel(msgs), "%s · flecha %s" % ("2ª ordem com imperfeições" if so else "1ª ordem",
                                                         an.LimiteFlecha), msgs)

    # 7 cálculo
    bloq = [(k, m) for k in ("estrutura", "material", "apoios", "rotulas", "cargas", "criterios")
            for n, m in r[k][2] if n == ERRO and not (k == "apoios" and m.startswith("O cálculo não fecha"))]
    r["_bloqueios"] = bloq
    if bloq:
        r["calculo"] = (VAZIO, "1 pendência antes de calcular" if len(bloq) == 1 else
                        "%d pendências antes de calcular" % len(bloq), [])
    elif calc is None or _desatualizada(an):
        r["calculo"] = (AVISO, "Pronto para calcular", [])
    elif calc.erro:
        r["calculo"] = (ERRO, "O cálculo não fechou", [(ERRO, calc.erro)])
    else:
        r["calculo"] = (OK, "%d combinações calculadas" % len(calc.combinacoes), [])

    # 8 resultados
    if calc is None or calc.erro or not calc.verificacao or r["calculo"][0] != OK:
        r["resultado"] = (VAZIO, "Aparece depois do cálculo", [])
    else:
        msgs = []
        tx = calc.taxa_maxima
        for i, v in sorted(calc.verificacao.items(), key=lambda kv: -kv[1]["taxa"]):
            if v["taxa"] > 1.0:
                msgs.append((ERRO, "Barra %d (%s): taxa %s em %s — não atende." % (
                    i + 1, calc.mapa["secoes"][i]["nome"], F.fmt(v["taxa"], 2), v["governa"].lower())))
            elif v["taxa"] > 0.9:
                msgs.append((AVISO, "Barra %d (%s): taxa %s em %s — perto do limite." % (
                    i + 1, calc.mapa["secoes"][i]["nome"], F.fmt(v["taxa"], 2), v["governa"].lower())))
        for i, f in calc.flechas.items():
            if f[2] > 1.0:
                msgs.append((ERRO, "Barra %d: deslocamento %s mm acima do limite de %s mm." % (
                    i + 1, F.fmt(f[0], 1), F.fmt(f[1], 1))))
        for a in calc.avisos:
            nivel = ERRO if ("GRANDE deslocabilidade" in a or a.startswith("ATENÇÃO")) else AVISO
            msgs.append((nivel, a))
        situ = "atende" if tx <= 1.0 else "não atende"
        if any("GRANDE deslocabilidade" in a for a in calc.avisos):
            situ = "grande deslocabilidade: análise insuficiente"
        elif any(a.startswith("ATENÇÃO: análise de 1ª ordem") for a in calc.avisos):
            situ = "1ª ordem não vale: ligue a 2ª ordem"
        r["resultado"] = (ERRO if tx > 1.0 else _nivel(msgs),
                          "Taxa máxima %s · %s" % (F.fmt(tx, 2), situ), msgs)

    # 9 ligações
    estudos = [o for o in an.Document.Objects
               if o.isDerivedFrom("Fem::FemAnalysis") and "Detalhe" in o.Label]
    detalhados = []
    for o in estudos:
        try:
            est_fem = F.Estudo(an.Document)
            est_fem.analise = o
            if est_fem.get("PrumoAnaliseBarras", "") == an.Name:
                detalhados.append(est_fem)
        except Exception:
            continue
    if r["resultado"][0] == VAZIO:
        r["ligacoes"] = (VAZIO, "Depois dos resultados", [])
    elif not detalhados:
        r["ligacoes"] = (AVISO, "Nenhum nó detalhado (opcional)",
                         [(AVISO, "O nó mais solicitado pode ser conferido por elementos finitos sólidos, com as "
                                  "soldas e os chumbadores verificados.")])
    else:
        msgs = []
        import json
        for e in detalhados:
            try:
                for x in json.loads(e.get("PrumoLigacoes", "") or "[]"):
                    if x["taxa"] > 1.0:
                        msgs.append((ERRO, x["texto"]))
            except ValueError:
                pass
        r["ligacoes"] = (_nivel(msgs), "%d nó%s detalhado%s" % (len(detalhados), "" if len(detalhados) == 1 else "s",
                                                               "" if len(detalhados) == 1 else "s"), msgs)

    # 10 relatório
    pdf = getattr(an, "RelatorioPDF", "") if "RelatorioPDF" in an.PropertiesList else ""
    if r["resultado"][0] == VAZIO:
        r["relatorio"] = (VAZIO, "Gere o PDF depois dos resultados", [])
    elif pdf and os.path.exists(pdf):
        r["relatorio"] = (OK, os.path.basename(pdf), [])
    else:
        r["relatorio"] = (VAZIO, "Gere a memória de cálculo", [])
    return r


# =========================================================================== interface
class Assistente(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SwFem")
        self.setStyleSheet(PrumoEstilo.tema(F.QSS))
        self._an_nome = None
        raiz = QtWidgets.QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        topo = QtWidgets.QFrame()
        topo.setObjectName("SwFemTopo")
        tl = QtWidgets.QHBoxLayout(topo)
        tl.setContentsMargins(12, 10, 12, 10)
        ic = QtWidgets.QLabel()
        ic.setPixmap(QtGui.QIcon(ICON).pixmap(34, 34))
        tl.addWidget(ic)
        tv = QtWidgets.QVBoxLayout()
        tv.setSpacing(0)
        t = QtWidgets.QLabel("Assistente de estruturas")
        t.setObjectName("SwFemTitulo")
        self.sub = QtWidgets.QLabel("Siga as etapas na ordem: o cálculo libera quando não houver pendências. "
                                    "Verificação pela NBR 8800:2024 e combinações pela NBR 8681:2025.")
        self.sub.setObjectName("SwFemSub")
        self.sub.setWordWrap(True)
        tv.addWidget(t)
        tv.addWidget(self.sub)
        tl.addLayout(tv, 1)
        raiz.addWidget(topo)
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QtWidgets.QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        cont = QtWidgets.QWidget()
        cont.setObjectName("SwFem")
        self.lista = QtWidgets.QVBoxLayout(cont)
        self.lista.setContentsMargins(10, 10, 10, 10)
        self.lista.setSpacing(8)
        area.setWidget(cont)
        raiz.addWidget(area, 1)
        self.etapas = {}
        for i, (chave, titulo, sub) in enumerate(ETAPAS, 1):
            e = F.Etapa(i, chave, titulo, sub)
            e.abrir.connect(self._alternar)
            self.etapas[chave] = e
            self.lista.addWidget(e)
            getattr(self, "_montar_" + chave)(e.corpo_lay)
        self.lista.addStretch(1)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.atualizar)
        self.timer.start()
        self._ultimo = None
        self.atualizar(force=True)
        self._abrir_proxima()

    # ------------------------------------------------------------ objetos
    def analise(self):
        import PrumoAnaliseEstrutura as A
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return None
        if self._an_nome:
            o = doc.getObject(self._an_nome)
            if o is not None and "Casos" in o.PropertiesList:
                return o
        ans = [o for o in doc.Objects if "Casos" in o.PropertiesList and "Apoios" in o.PropertiesList]
        est = self.estrutura_escolhida()
        if est is not None:
            a = A.analise_de(est)
            if a is not None:
                ans = [a] + [x for x in ans if x != a]
        if ans:
            self._an_nome = ans[0].Name
            return ans[0]
        return None

    def estrutura_escolhida(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return None
        nome = self.cb_est.currentData() if hasattr(self, "cb_est") else None
        return doc.getObject(nome) if nome else None

    # ------------------------------------------------------------ util
    def _alternar(self, etapa):
        abrir = not etapa.aberta()
        for e in self.etapas.values():
            e.set_aberta(False)
        etapa.set_aberta(abrir)

    def abrir_etapa(self, chave):
        for k, e in self.etapas.items():
            e.set_aberta(k == chave)

    def _abrir_proxima(self):
        r = avaliar(self.analise(), self.estrutura_escolhida())
        for chave, _t, _s in ETAPAS:
            if r[chave][0] in (VAZIO, ERRO) and chave not in ("ligacoes",):
                self.abrir_etapa(chave)
                return
        self.abrir_etapa("resultado")

    def _erro(self, texto):
        QtWidgets.QMessageBox.warning(self, "Assistente de estruturas", texto)

    def painel(self, modo=None):
        """Abre (ou reaproveita) o painel da simulação, já no modo de clique pedido."""
        import PrumoAnaliseVista as V
        an = self.analise()
        if an is None:
            self._erro("Escolha a estrutura e crie a análise na etapa 1.")
            return None
        import PrumoPainel
        ativo = PrumoPainel._ATIVO.get("painel")
        if FreeCADGui.Control.activeDialog() and isinstance(ativo, V.PainelAnalise) and ativo.analise == an \
                and ativo._vivo():
            p = ativo
        else:
            p = V.abrir_painel(an.Estrutura, an)
        if modo and p is not None:
            try:
                p.modo.definir(modo)
            except Exception:
                pass
        return p

    def _botao(self, texto, fn, primario=False):
        b = QtWidgets.QPushButton(texto)
        if primario:
            b.setObjectName("SwPrimario")
        b.clicked.connect(fn)
        return b

    # ------------------------------------------------------------ 1 estrutura
    def _montar_estrutura(self, lay):
        lay.addWidget(F._dica("Escolha a estrutura soldada. Cada estrutura tem uma análise, com os apoios, os "
                              "casos de carga e os resultados."))
        self.cb_est = QtWidgets.QComboBox()
        self.cb_est.currentIndexChanged.connect(self._mudou_estrutura)
        lay.addWidget(self.cb_est)
        self.bt_criar = self._botao("Criar a análise desta estrutura", self._criar_analise, True)
        lay.addWidget(F._linha(self.bt_criar, "stretch"))

    def _listar_estruturas(self):
        import PrumoEstrutura as E
        doc = FreeCAD.ActiveDocument
        ests = [o for o in (doc.Objects if doc else []) if E.eh_estrutura(o)]
        atuais = [self.cb_est.itemData(i) for i in range(self.cb_est.count())]
        if atuais == [o.Name for o in ests]:
            return
        an = self.analise()
        self.cb_est.blockSignals(True)
        self.cb_est.clear()
        for o in ests:
            self.cb_est.addItem(o.Label, o.Name)
        if an is not None and an.Estrutura is not None:
            i = self.cb_est.findData(an.Estrutura.Name)
            if i >= 0:
                self.cb_est.setCurrentIndex(i)
        self.cb_est.blockSignals(False)

    def _mudou_estrutura(self, *_a):
        import PrumoAnaliseEstrutura as A
        est = self.estrutura_escolhida()
        a = A.analise_de(est) if est is not None else None
        self._an_nome = a.Name if a is not None else None
        self.atualizar(force=True)

    def _criar_analise(self):
        import PrumoAnaliseEstrutura as A
        est = self.estrutura_escolhida()
        if est is None:
            self._erro("Não há estrutura soldada no documento. Crie uma na aba Estruturas.")
            return
        a = A.analise_de(est)
        if a is None:
            doc = est.Document
            doc.openTransaction("Análise da estrutura")
            a = A.criar(doc, est)
            doc.commitTransaction()
        self._an_nome = a.Name
        self.atualizar(force=True)
        self._abrir_proxima()

    # ------------------------------------------------------------ 2 material
    def _montar_material(self, lay):
        lay.addWidget(F._dica("O aço vem do material das barras da estrutura; dá para trocar no painel da "
                              "simulação (seção Material e critérios)."))
        lay.addWidget(F._linha(self._botao("Escolher o material no painel", lambda: self.painel()), "stretch"))

    # ------------------------------------------------------------ 3 apoios
    def _montar_apoios(self, lay):
        lay.addWidget(F._dica("No painel, escolha o tipo (engaste, rótula, rolete ou mola) e clique nos nós. "
                              "Clicar de novo no mesmo nó tira o apoio."))
        lay.addWidget(F._linha(self._botao("Pôr apoios clicando nos nós", lambda: self.painel("apoio"), True),
                               "stretch"))

    # ------------------------------------------------------------ 4 rótulas
    def _montar_rotulas(self, lay):
        lay.addWidget(F._dica("Ligação flexível (viga apoiada no pilar, Gerber), barra de treliça ou "
                              "contraventamento que só trabalha à tração. Sem nada aqui, todas as ligações são "
                              "rígidas."))
        lay.addWidget(F._linha(self._botao("Rotular barras no painel", lambda: self.painel("rotula")), "stretch"))

    # ------------------------------------------------------------ 5 cargas
    def _montar_cargas(self, lay):
        lay.addWidget(F._dica("Um caso por ação (peso próprio, sobrecarga, vento em cada direção...). O tipo do "
                              "caso define os coeficientes γ e ψ das combinações."))
        self.lb_casos = QtWidgets.QLabel("")
        self.lb_casos.setWordWrap(True)
        lay.addWidget(self.lb_casos)
        lay.addWidget(F._linha(self._botao("Cargas nas barras", lambda: self.painel("barra"), True),
                               self._botao("Cargas nos nós", lambda: self.painel("no")), "stretch"))

    # ------------------------------------------------------------ 6 critérios
    def _montar_criterios(self, lay):
        lay.addWidget(F._dica("A análise de 2ª ordem com forças nocionais é a da NBR 8800:2024; a de 1ª ordem só "
                              "vale para estrutura de pequena deslocabilidade."))
        self.ck_so = QtWidgets.QCheckBox("Análise de 2ª ordem (P-Δ) com imperfeições")
        self.ck_so.toggled.connect(self._mudou_criterio)
        self.cb_flecha = QtWidgets.QComboBox()
        import PrumoAnaliseEstrutura as A
        self.cb_flecha.addItems(list(A.LIMITES_FLECHA))
        self.cb_flecha.currentIndexChanged.connect(self._mudou_criterio)
        lay.addWidget(self.ck_so)
        lay.addWidget(F._linha(QtWidgets.QLabel("Limite de flecha das vigas"), self.cb_flecha, "stretch"))

    def _carregar_criterios(self, an):
        for w in (self.ck_so, self.cb_flecha):
            w.blockSignals(True)
        self.ck_so.setChecked(bool(getattr(an, "SegundaOrdem", True)))
        self.cb_flecha.setCurrentText(an.LimiteFlecha)
        for w in (self.ck_so, self.cb_flecha):
            w.blockSignals(False)

    def _mudou_criterio(self, *_a):
        an = self.analise()
        if an is None:
            return
        doc = an.Document
        doc.openTransaction("Critérios da análise")
        an.SegundaOrdem = self.ck_so.isChecked()
        an.LimiteFlecha = self.cb_flecha.currentText()
        doc.commitTransaction()
        self.atualizar(force=True)

    # ------------------------------------------------------------ 7 cálculo
    def _montar_calculo(self, lay):
        self.lb_pend = QtWidgets.QLabel("")
        self.lb_pend.setObjectName("SwMsg")
        self.lb_pend.setWordWrap(True)
        lay.addWidget(self.lb_pend)
        self.bt_calc = self._botao("Calcular", self.calcular, True)
        lay.addWidget(F._linha(self.bt_calc, "stretch"))

    def calcular(self):
        an = self.analise()
        r = avaliar(an)
        if r["_bloqueios"]:
            self._erro("Resolva as pendências antes de calcular.")
            return False
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            an.touch()
            an.Document.recompute()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self.atualizar(force=True)
        self._abrir_proxima()
        return True

    # ------------------------------------------------------------ 8 resultados
    def _montar_resultado(self, lay):
        self.c_taxa = F._cartao("—", "Maior taxa de uso (1,00 = no limite)")
        self.c_desl = F._cartao("—", "Maior deslocamento (ELS)")
        lay.addWidget(F._linha(self.c_taxa, self.c_desl))
        self.lb_critica = QtWidgets.QLabel("")
        self.lb_critica.setWordWrap(True)
        lay.addWidget(self.lb_critica)
        import PrumoAnaliseEstrutura as A
        self.cb_mostrar = QtWidgets.QComboBox()
        self.cb_mostrar.addItems([m for m in A.MOSTRAR if m != A.MODO_VIBRAR])
        self.cb_mostrar.activated.connect(self._mostrar)
        lay.addWidget(F._linha(QtWidgets.QLabel("Mostrar na tela"), self.cb_mostrar, "stretch"))
        lay.addWidget(F._linha(self._botao("Frequências naturais", self._frequencias),
                               self._botao("Vídeo", self._video), "stretch"))
        self.lb_freq = QtWidgets.QLabel("")
        self.lb_freq.setWordWrap(True)
        lay.addWidget(self.lb_freq)

    def _mostrar(self, *_a):
        an = self.analise()
        if an is not None:
            an.Mostrar = self.cb_mostrar.currentText()
            an.Document.recompute()

    def _frequencias(self):
        import PrumoAnaliseEstrutura as A
        an = self.analise()
        calc = _calc(an)
        if calc is None or calc.erro:
            self._erro("Calcule a estrutura antes.")
            return None
        try:
            modos = A.frequencias(calc, an.Proxy.casos(an), 6)
        except Exception as ex:
            self._erro("Frequências não calculadas: %s" % ex)
            return None
        self.lb_freq.setText("Frequências: " + "; ".join("modo %d: %s Hz" % (k + 1, F.fmt(f, 2))
                                                          for k, (f, _v) in enumerate(modos)))
        return modos

    def _video(self):
        import PrumoVideo
        an = self.analise()
        if an is None or _calc(an) is None:
            self._erro("Calcule a estrutura antes.")
            return
        PrumoVideo.escolher_e_gravar(PrumoVideo.gravar_estrutura, an, "estrutura.mp4")

    # ------------------------------------------------------------ 9 ligações
    def _montar_ligacoes(self, lay):
        lay.addWidget(F._dica("O nó da barra mais solicitada é recortado e calculado como sólido (CalculiX), com "
                              "as soldas e os chumbadores verificados. O resultado abre no Assistente de "
                              "simulação."))
        self.cb_junta = QtWidgets.QComboBox()
        lay.addWidget(self.cb_junta)
        lay.addWidget(F._linha(self._botao("Listar os nós", self._listar_juntas),
                               self._botao("Detalhar o nó", self._detalhar, True), "stretch"))

    def _listar_juntas(self):
        import PrumoDetalheFEM as D
        an = self.analise()
        try:
            js = D.juntas(an)
        except ValueError as ex:
            self._erro(str(ex))
            return []
        calc = _calc(an)
        critica = None
        if calc is not None and calc.verificacao:
            critica = max(calc.verificacao.items(), key=lambda kv: kv[1]["taxa"])[0]
        js.sort(key=lambda j: (0 if critica is not None and any(i == critica for i, _s in j["linhas"]) else 1))
        self.cb_junta.clear()
        for j in js:
            self.cb_junta.addItem(j["texto"], (j["ponto"].x, j["ponto"].y, j["ponto"].z))
        return js

    def _detalhar(self):
        import PrumoAnaliseVista as V
        if self.cb_junta.count() == 0 and not self._listar_juntas():
            return None
        p = self.cb_junta.currentData()
        an = self.analise()
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        return V.detalhar_com_progresso(an, FreeCAD.Vector(*p))

    # ------------------------------------------------------------ 10 relatório
    def _montar_relatorio(self, lay):
        lay.addWidget(F._dica("Memória de cálculo com as hipóteses, as combinações, os diagramas e a verificação "
                              "de cada barra. Os documentos saem com a ART do responsável técnico."))
        lay.addWidget(F._linha(self._botao("Gerar o PDF", self.relatorio, True),
                               self._botao("Abrir", self._abrir_pdf), "stretch"))

    def relatorio(self, caminho=None):
        import PrumoAnaliseRelatorio as R
        an = self.analise()
        if an is None or avaliar(an)["resultado"][0] == VAZIO:
            self._erro("Calcule a estrutura antes de gerar a memória.")
            return None
        if not caminho:
            pasta = os.path.dirname(an.Document.FileName or "") or os.path.expanduser("~")
            caminho, _f = QtWidgets.QFileDialog.getSaveFileName(
                self, "Memória de cálculo", os.path.join(pasta, "Memoria de calculo - %s.pdf" % an.Estrutura.Label),
                "PDF (*.pdf)")
            if not caminho:
                return None
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            R.gerar_pdf(an, caminho)
        except Exception as ex:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._erro("O PDF não foi gerado: %s" % ex)
            return None
        QtWidgets.QApplication.restoreOverrideCursor()
        if "RelatorioPDF" not in an.PropertiesList:
            an.addProperty("App::PropertyString", "RelatorioPDF", "Resultados", "Última memória de cálculo gerada")
            an.setEditorMode("RelatorioPDF", 1)
        an.RelatorioPDF = caminho
        self.atualizar(force=True)
        return caminho

    def _abrir_pdf(self):
        an = self.analise()
        pdf = getattr(an, "RelatorioPDF", "") if an is not None else ""
        if pdf and os.path.exists(pdf):
            from PySide import QtGui
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(pdf))
        else:
            self._erro("Gere o PDF primeiro.")

    # ------------------------------------------------------------ estado
    def atualizar(self, force=False):
        if not self.isVisible() and not force:
            return
        self._listar_estruturas()
        an = self.analise()
        try:
            r = avaliar(an, self.estrutura_escolhida())
        except Exception as ex:
            FreeCAD.Console.PrintWarning("Prumo: assistente de estruturas: %s\n" % ex)
            return
        for chave, e in self.etapas.items():
            nivel, resumo, msgs = r[chave]
            e.atualizar(nivel, resumo, msgs)
        self.bt_criar.setVisible(an is None)
        bloq = r["_bloqueios"]
        if bloq:
            nomes = {k: t for k, t, _s in ETAPAS}
            self.lb_pend.setText("Antes de calcular:\n" + "\n".join("• %s: %s" % (nomes[k], m) for k, m in bloq))
            self.lb_pend.setProperty("nivel", "erro")
        else:
            self.lb_pend.setText("Sem pendências. O cálculo roda as combinações da NBR 8681:2025 com a análise "
                                 "escolhida e verifica cada barra pela NBR 8800:2024.")
            self.lb_pend.setProperty("nivel", "ok")
        self.lb_pend.style().unpolish(self.lb_pend)
        self.lb_pend.style().polish(self.lb_pend)
        self.bt_calc.setEnabled(not bloq and an is not None)
        if an is not None:
            self._carregar_criterios(an)
            casos = an.Proxy.casos(an)
            self.lb_casos.setText("<br>".join("<b>%s</b> — %s · %d carga%s%s" % (
                c["nome"], c["tipo"], len(c.get("cargas", [])), "" if len(c.get("cargas", [])) == 1 else "s",
                " + peso próprio" if c.get("peso_proprio") else "") for c in casos))
            calc = _calc(an)
            if calc is not None and not calc.erro and calc.verificacao:
                self.c_taxa.valor.setText(F.fmt(calc.taxa_maxima, 2))
                self.c_desl.valor.setText(F.fmt(max([f[0] for f in calc.flechas.values()] or [0.0]), 1, "mm"))
                self.lb_critica.setText(an.BarraCritica)
                if self.cb_mostrar.currentText() != an.Mostrar:
                    self.cb_mostrar.setCurrentText(an.Mostrar)


def mostrar():
    mw = FreeCADGui.getMainWindow()
    dock = _estado["dock"]
    if dock is None or not F._vivo(dock):
        for velho in mw.findChildren(QtWidgets.QDockWidget, "PrumoAssistenteEstrutura"):
            velho.setParent(None)
            velho.deleteLater()
        dock = QtWidgets.QDockWidget("Assistente de estruturas", mw)
        dock.setObjectName("PrumoAssistenteEstrutura")
        dock.setWidget(Assistente(dock))
        dock.setMinimumWidth(360)
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        _estado["dock"] = dock
    dock.show()
    dock.raise_()
    try:
        import PrumoPainelLateral
        PrumoPainelLateral.acomodar(dock)     # vira aba do painel lateral
    except Exception:
        pass
    w = dock.widget()
    est = None
    try:
        import PrumoEstrutura as E
        for o in FreeCADGui.Selection.getSelection():
            est = E.estrutura_de(o) or est
    except Exception:
        pass
    if est is not None:
        w._listar_estruturas()
        i = w.cb_est.findData(est.Name)
        if i >= 0:
            w.cb_est.setCurrentIndex(i)
    w.atualizar(force=True)
    w._abrir_proxima()
    return dock


class CmdAssistenteEstrutura:
    def GetResources(self):
        return {"Pixmap": ICON, "MenuText": "Assistente de estruturas",
                "ToolTip": "Passo a passo da simulação por barras: estrutura, material, apoios, rótulas, casos de "
                           "carga, critérios, conferência de pendências, cálculo, resultados, detalhe das "
                           "ligações e memória de cálculo"}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        mostrar()
