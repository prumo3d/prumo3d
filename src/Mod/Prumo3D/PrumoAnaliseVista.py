# SPDX-License-Identifier: LGPL-2.1-or-later
"""Interface da simulação de estruturas por barras: desenho na tela (apoios, cargas, taxa de uso,
diagramas, deformada), painel ao vivo e comando.

O painel funciona como o resto do Prumo: tudo o que muda aparece na tela na hora; OK grava,
Cancelar desfaz. O clique na tela põe apoios e escolhe as barras e os nós das cargas.
"""

import json
import math

import FreeCAD
import FreeCADGui

import PrumoUtil
import PrumoAnaliseEstrutura as A

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtWidgets


def _cor_taxa(t):
    """Verde (folga) → amarelo → vermelho (acima de 1,0)."""
    if t > 1.0:
        return (0.85, 0.10, 0.10)
    if t > 0.9:
        return (0.95, 0.45, 0.05)
    if t > 0.7:
        return (0.95, 0.80, 0.10)
    return (0.15, 0.65, 0.30)


# ------------------------------------------------------------------ vista na árvore
class VPAnalise:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        from pivy import coin
        self.Object = vobj.Object
        self.raiz = coin.SoSeparator()
        self.desenho = coin.SoAnnotation()    # por cima das barras (não some dentro dos perfis)
        estilo = coin.SoPickStyle()
        estilo.style = coin.SoPickStyle.UNPICKABLE
        self.raiz.addChild(estilo)
        self.raiz.addChild(self.desenho)
        vobj.addDisplayMode(self.raiz, "Desenho")
        self.destaque = None    # (tipo, valor) realçado pelo painel

    def getDisplayModes(self, vobj):
        return ["Desenho"]

    def getDefaultDisplayMode(self):
        return "Desenho"

    def setDisplayMode(self, modo):
        return modo

    def getIcon(self):
        return PrumoUtil.icone("estrutura.svg")

    def updateData(self, obj, prop):
        if prop in ("Situacao", "TaxaMaxima", "Mostrar", "Combinacao", "Escala", "Apoios", "Casos", "Resumo"):
            self.redesenhar()

    def onChanged(self, vobj, prop):
        if prop == "Visibility":
            self.redesenhar()

    def doubleClicked(self, vobj):
        abrir_painel(vobj.Object.Estrutura, vobj.Object)
        return True

    def setEdit(self, vobj, mode=0):
        if mode != 0:
            return None
        abrir_painel(vobj.Object.Estrutura, vobj.Object)
        return True

    def unsetEdit(self, vobj, mode=0):
        return False

    def dumps(self):
        return None

    def loads(self, state):
        return None

    # ------------------------------------------------------------ desenho
    def redesenhar(self):
        try:
            self._redesenhar()
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: desenho da análise: %s\n" % exc)

    def _redesenhar(self):
        from pivy import coin
        if not hasattr(self, "desenho"):
            return
        self.desenho.removeAllChildren()
        obj = getattr(self, "Object", None)
        if obj is None or obj.Estrutura is None:
            return
        calc = getattr(obj.Proxy, "calc", None)
        if calc is None:
            # arquivo recém-aberto: calcula de novo (sem mexer nas propriedades) e desenha depois
            if not getattr(self, "_calculando", False):
                self._calculando = True
                QtCore.QTimer.singleShot(0, self._calcular_e_desenhar)
            return
        if calc.modelo is None:
            return
        m = calc.modelo
        tam = _tamanho(m)
        mostrar = obj.Mostrar
        self._nos(m, tam)
        self._apoios(obj, m, tam)
        if calc.erro or mostrar == "Cargas e apoios":
            self._cargas(obj, calc, tam)
        elif mostrar == "Taxa de uso":
            self._taxas(calc, tam)
        else:
            nome = obj.Combinacao or _pior_combinacao(calc)
            r = calc.resultados.get(nome)
            if r is None:
                return
            if mostrar == "Deformada":
                self._deformada(m, r, tam, obj.Escala)
            else:
                chave = {"Momento fletor (M)": "My", "Esforço cortante (V)": "Vz",
                         "Esforço normal (N)": "N"}[mostrar]
                self._diagrama(m, r, chave, tam, obj.Escala)
            self._texto(_meio_modelo(m) + _vec(0, 0, 0), "%s · %s" % (mostrar, nome), (0.0, 0.23, 0.44),
                        tam * 0.0 + 14)

    def _calcular_e_desenhar(self):
        self._calculando = False
        try:
            obj = self.Object
            obj.Proxy.calcular_silencioso(obj)
            if getattr(obj.Proxy, "calc", None) is not None:
                self.redesenhar()
        except (ReferenceError, RuntimeError, AttributeError):
            pass       # objeto apagado antes do desenho

    # ---- peças de desenho
    def _sep(self):
        from pivy import coin
        s = coin.SoSeparator()
        self.desenho.addChild(s)
        return s

    def _linhas(self, segmentos, cor, largura=2.0, sep=None):
        from pivy import coin
        if not segmentos:
            return
        s = sep or self._sep()
        mat = coin.SoBaseColor()
        mat.rgb.setValue(*cor)
        est = coin.SoDrawStyle()
        est.lineWidth = largura
        pts = coin.SoCoordinate3()
        lista = []
        nums = []
        for seg in segmentos:
            lista += [tuple(p) for p in seg]
            nums.append(len(seg))
        pts.point.setValues(0, len(lista), lista)
        ls = coin.SoLineSet()
        ls.numVertices.setValues(0, len(nums), nums)
        for n in (mat, est, pts, ls):
            s.addChild(n)

    def _marcas(self, pontos, cor, indice, tamanho=9):
        from pivy import coin
        if not pontos:
            return
        s = self._sep()
        mat = coin.SoBaseColor()
        mat.rgb.setValue(*cor)
        c = coin.SoCoordinate3()
        c.point.setValues(0, len(pontos), [tuple(p) for p in pontos])
        mk = coin.SoMarkerSet()
        mk.markerIndex = indice
        for n in (mat, c, mk):
            s.addChild(n)

    def _texto(self, p, txt, cor=(0.0, 0.23, 0.44), tamanho=14):
        from pivy import coin
        s = self._sep()
        mat = coin.SoBaseColor()
        mat.rgb.setValue(*cor)
        f = coin.SoFont()
        f.size = tamanho
        tr = coin.SoTranslation()
        tr.translation.setValue(float(p[0]), float(p[1]), float(p[2]))
        t = coin.SoText2()
        t.string = txt
        for n in (mat, f, tr, t):
            s.addChild(n)

    def _nos(self, m, tam):
        from pivy import coin
        self._marcas(m.nos, (0.45, 0.50, 0.58), coin.SoMarkerSet.CIRCLE_LINE_7_7)

    def _apoios(self, obj, m, tam):
        from pivy import coin
        tipos = {"Engaste": (coin.SoMarkerSet.SQUARE_FILLED_9_9, (0.0, 0.23, 0.44)),
                 "Rótula": (coin.SoMarkerSet.TRIANGLE_FILLED_9_9, (0.0, 0.23, 0.44)),
                 "Rolete (vertical)": (coin.SoMarkerSet.CIRCLE_FILLED_9_9, (0.0, 0.23, 0.44))}
        for k, tipo in obj.Proxy.apoios(obj).items():
            p = A._ponto_da_chave(k)
            idx, cor = tipos.get(tipo, tipos["Engaste"])
            self._marcas([p], cor, idx)
            self._texto((p[0], p[1], p[2] - 0.04 * tam), tipo.split(" ")[0], cor, 13)

    def _cargas(self, obj, calc, tam):
        casos = obj.Proxy.casos(obj)
        seta = 0.06 * tam
        for c in casos:
            for carga in c.get("cargas", []):
                d = A.DIRECOES.get(carga.get("direcao"), (0, 0, -1))
                dv = _vec(*d)
                if carga["alvo"] == "barra":
                    i = int(carga["linha"])
                    if i not in calc.mapa["linhas"]:
                        continue
                    p0, t, L = calc.mapa["linhas"][i]
                    if carga["tipo"] == "distribuida":
                        pts = [p0 + t * (L * k / 6.0) for k in range(7)]
                        segs = [[p - dv * seta, p] for p in pts]
                        segs.append([p - dv * seta for p in pts])
                        self._linhas(segs, (0.75, 0.25, 0.05), 2)
                        self._texto(pts[3] - dv * seta * 1.3, "%s kN/m (%s)" % (_f(carga["valor"]), c["nome"]),
                                    (0.75, 0.25, 0.05), 12)
                    else:
                        p = p0 + t * float(carga.get("posicao", 0.0))
                        self._linhas([[p - dv * seta * 1.5, p]], (0.75, 0.25, 0.05), 3)
                        self._texto(p - dv * seta * 1.7, "%s kN (%s)" % (_f(carga["valor"]), c["nome"]),
                                    (0.75, 0.25, 0.05), 12)
                else:
                    p = _vec(*A._ponto_da_chave(carga["no"]))
                    self._linhas([[p - dv * seta * 1.5, p]], (0.75, 0.25, 0.05), 3)
                    self._texto(p - dv * seta * 1.7, "%s kN (%s)" % (_f(carga["valor"]), c["nome"]),
                                (0.75, 0.25, 0.05), 12)

    def _taxas(self, calc, tam):
        for i, v in calc.verificacao.items():
            if v is None:
                continue
            p0, t, L = calc.mapa["linhas"][i]
            tx = max(v["taxa"], calc.flechas.get(i, (0, 0, 0))[2])
            self._linhas([[p0, p0 + t * L]], _cor_taxa(tx), 7)
            # rótulo ao lado da barra (não em cima da linha colorida)
            lado = _vec(0, 0, 1) if abs(t.z) < 0.7 else _vec(1, 0, 0)
            self._texto(p0 + t * (L / 2.0) + lado * (0.03 * tam), "barra %d · %s" % (i + 1, _f(tx, 2)),
                        (0.0, 0.23, 0.44) if tx <= 1.0 else (0.85, 0.10, 0.10), 14)

    def _diagrama(self, m, r, chave, tam, escala):
        import numpy as np
        maxv = 0.0
        amostras = []
        for nb, b in enumerate(m.barras):
            R, L = m.eixos(b)
            d = r.diagrama(nb, 11)
            amostras.append((nb, R, d))
            for _x, e in d:
                maxv = max(maxv, abs(e[chave]))
        if maxv <= 0:
            return
        k = 0.12 * tam / maxv * (escala or 1.0)
        segs_pos, segs_neg = [], []
        for nb, R, d in amostras:
            b = m.barras[nb]
            pi = _vec(*m.nos[b.i])
            x_ax = _vec(*R[0])
            z_ax = _vec(*R[2])
            curva = []
            for x, e in d:
                base = pi + x_ax * x
                # momento: desenhado do lado tracionado (M > 0 traciona o lado -z)
                sinal = -1.0 if chave == "My" else 1.0
                p = base + z_ax * (sinal * e[chave] * k)
                curva.append(p)
                (segs_pos if e[chave] >= 0 else segs_neg).append([base, p])
            self._linhas([curva], (0.0, 0.23, 0.44), 2)
            emax = max(d, key=lambda q: abs(q[1][chave]))
            pm = pi + x_ax * emax[0] + z_ax * ((-1.0 if chave == "My" else 1.0) * emax[1][chave] * k)
            un = "kN·m" if chave.startswith("M") else "kN"
            div = 1e6 if chave.startswith("M") else 1e3
            if abs(emax[1][chave]) > 0.05 * maxv:
                self._texto(pm, "%s %s" % (_f(emax[1][chave] / div, 2), un), (0.0, 0.23, 0.44), 12)
        self._linhas(segs_pos, (0.20, 0.45, 0.80), 1)
        self._linhas(segs_neg, (0.85, 0.30, 0.20), 1)

    def _deformada(self, m, r, tam, escala):
        import numpy as np
        maxd = max((float(np.linalg.norm(r.u[6 * n:6 * n + 3])) for n in range(len(m.nos))), default=0.0)
        for nb in range(len(m.barras)):
            maxd = max(maxd, max(r.flecha_local(nb, 7)))
        if maxd <= 0:
            return
        k = 0.06 * tam / maxd * (escala or 1.0)
        segs = []
        for nb, b in enumerate(m.barras):
            R, L = m.eixos(b)
            pts = _curva_deformada(r, nb, b, R, L, m, k)
            segs.append(pts)
        self._linhas(segs, (0.85, 0.30, 0.20), 3)
        n_max = max(range(len(m.nos)), key=lambda n: float(np.linalg.norm(r.u[6 * n:6 * n + 3])))
        d = r.u[6 * n_max:6 * n_max + 3]
        self._texto(_vec(*m.nos[n_max]) + _vec(*d) * k, "%s mm" % _f(float(np.linalg.norm(d)), 1),
                    (0.85, 0.30, 0.20), 13)


def _curva_deformada(r, nb, b, R, L, m, k, n=9):
    import numpy as np
    di = R @ r.u[6 * b.i:6 * b.i + 3]
    dj = R @ r.u[6 * b.j:6 * b.j + 3]
    ri = R @ r.u[6 * b.i + 3:6 * b.i + 6]
    rj = R @ r.u[6 * b.j + 3:6 * b.j + 6]
    s = b.secao
    dist, pont = r.cargas[nb]
    import PrumoPortico as PT
    pts = []
    for q in range(n):
        x = L * q / (n - 1)
        xi = x / L
        h1, h2 = 1 - 3 * xi ** 2 + 2 * xi ** 3, x * (1 - xi) ** 2
        h3, h4 = 3 * xi ** 2 - 2 * xi ** 3, x * (xi ** 2 - xi)
        u = di[0] + (dj[0] - di[0]) * xi
        v = h1 * di[1] + h2 * ri[2] + h3 * dj[1] + h4 * rj[2]
        w = h1 * di[2] - h2 * ri[1] + h3 * dj[2] - h4 * rj[1]
        for qx, qy, qz in dist:
            v += qy * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iz)
            w += qz * x ** 2 * (L - x) ** 2 / (24 * s.E * s.Iy)
        for a, (Px, Py, Pz) in pont:
            v += PT._flecha_pontual_biengastada(Py, a, x, L, s.E * s.Iz)
            w += PT._flecha_pontual_biengastada(Pz, a, x, L, s.E * s.Iy)
        loc = np.array([x + u * k, v * k, w * k])
        g = m.nos[b.i] + R.T @ loc
        pts.append(_vec(*g))
    return pts


def _vec(x, y, z):
    return FreeCAD.Vector(float(x), float(y), float(z))


def _tamanho(m):
    import numpy as np
    if not m.nos:
        return 1000.0
    a = np.array(m.nos)
    return float(np.linalg.norm(a.max(axis=0) - a.min(axis=0))) or 1000.0


def _meio_modelo(m):
    import numpy as np
    a = np.array(m.nos)
    c = (a.max(axis=0) + a.min(axis=0)) / 2.0
    top = a.max(axis=0)
    return _vec(c[0], c[1], top[2] + 0.08 * _tamanho(m))


def _pior_combinacao(calc):
    piores = sorted(calc.verificacao.values(), key=lambda v: -(v or {}).get("taxa", 0))
    if piores and piores[0]:
        return piores[0]["combinacao"]
    return calc.combinacoes[0][0] if calc.combinacoes else ""


def _f(v, casas=2):
    return PrumoUtil.fmt(float(v), casas)


# ------------------------------------------------------------------ painel
import PrumoPainel as P

MODOS_CLIQUE = [("apoio", "Pôr apoio", "selecao", "Clique num nó (ponta de barra) para pôr ou tirar o apoio"),
                ("barra", "Carga na barra", "empurra", "Clique nas barras para aplicar a carga do caso"),
                ("no", "Carga no nó", "posicao", "Clique num nó para aplicar a força do caso")]
TIPOS_CARGA = ["Distribuída (kN/m)", "Concentrada na barra (kN)"]


class PainelAnalise(P.PainelTarefa):
    titulo = "Simulação da estrutura"
    ajuda = ("1. Clique nos nós para pôr os apoios. 2. Monte os casos de carga e clique nas barras ou nós "
             "para aplicar as cargas. 3. Os resultados aparecem na hora (taxa de uso, diagramas, deformada).")

    def __init__(self, analise):
        self.analise = analise
        self._timer = None
        self._transacao_painel = False
        self._criada = False
        super().__init__()

    def montar(self):
        f = self.form
        obj = self.analise
        self._carregando = True
        # ---- material e critérios
        s0 = f.secao("Material e critérios", "material")
        self.material = s0.linha("material", QtWidgets.QComboBox(), "Aço das barras (fy e fu vêm da biblioteca Prumo).",
                                 "Aço")
        import PrumoFEM
        self.material.addItem("(o da estrutura)", "")
        for d in PrumoFEM.materiais():
            p = PrumoFEM.props_mat(d["props"])
            if p.get("Sy") and p.get("Su") and d.get("biblioteca") == "Prumo":
                self.material.addItem("%s — fy %s / fu %s MPa" % (d["nome"], _f(p["Sy"], 0), _f(p["Su"], 0)),
                                      d["nome"])
        i = self.material.findData(obj.Material)
        self.material.setCurrentIndex(max(0, i))
        self.flecha = s0.linha("comprimento", P.lista(list(A.LIMITES_FLECHA), obj.LimiteFlecha),
                               "Limite de flecha das vigas (Anexo C da NBR 8800).", "Flecha")
        self.k = s0.linha("comprimento", P.numero(obj.K or 1.0, 0.5, 5.0, "", 2),
                          "Coeficiente de flambagem: 1,0 para barras contraventadas (E.2.1.2); pilar em "
                          "balanço, 2,1 (Tabela E.1).", "K (flambagem)")
        aviso = s0.texto("<span style='color:#B5523F'>%s</span>" % _norma())
        # ---- clique
        s1 = f.secao("O clique na tela", "selecao")
        self.modo = P.Opcoes([(k, t, ic, d) for k, t, ic, d in MODOS_CLIQUE], "apoio")
        s1.widget(self.modo)
        self.tipo_apoio = s1.linha("tipo", P.lista(list(A.APOIOS) + ["Tirar apoio"], "Engaste"),
                                   "Engaste: trava tudo. Rótula: trava deslocamentos e solta rotações. Rolete: "
                                   "só trava a vertical.", "Apoio")
        self.lista_apoios = s1.widget(QtWidgets.QListWidget())
        self.lista_apoios.setMaximumHeight(90)
        # ---- casos e cargas
        s2 = f.secao("Casos de carga", "empurra")
        self.caso = s2.linha("tipo", QtWidgets.QComboBox(), "Caso de carga em edição (as cargas clicadas vão para "
                             "ele).", "Caso")
        lin = QtWidgets.QWidget()
        hl = QtWidgets.QHBoxLayout(lin)
        hl.setContentsMargins(0, 0, 0, 0)
        self.bt_novo = QtWidgets.QPushButton("Novo caso")
        self.bt_tirar_caso = QtWidgets.QPushButton("Remover caso")
        hl.addWidget(self.bt_novo)
        hl.addWidget(self.bt_tirar_caso)
        s2.widget(lin)
        self.nome_caso = s2.linha("texto", QtWidgets.QLineEdit(), "Nome do caso (aparece nas combinações).", "Nome")
        self.tipo_caso = s2.linha("tipo", P.lista(list(A.TIPOS_CASO)), "Tipo do caso: define os coeficientes γ e ψ "
                                  "das combinações (NBR 8681).", "Tipo")
        self.peso = s2.linha("quantidade", P.marcar("Incluir o peso próprio das barras neste caso"), "")
        s3 = f.secao("Cargas do caso", "empurra")
        self.tipo_carga = s3.linha("tipo", P.lista(TIPOS_CARGA), "Distribuída ao longo da barra ou concentrada "
                                   "num ponto dela.", "Tipo")
        self.valor = s3.linha("quantidade", P.numero(5.0, -1e6, 1e6, "", 2), "kN/m (distribuída) ou kN "
                              "(concentrada e no nó).", "Valor")
        self.direcao = s3.linha("empurra", P.lista(list(A.DIRECOES)), "Direção da carga (eixos globais).", "Direção")
        self.posicao = s3.linha("comprimento", P.numero(0.0, 0.0, 1e7, " mm", 0), "Concentrada: distância a partir "
                                "do Início da barra.", "Posição")
        self.lista_cargas = s3.widget(QtWidgets.QListWidget())
        self.lista_cargas.setMaximumHeight(110)
        self.bt_tirar_carga = s3.widget(QtWidgets.QPushButton("Tirar a carga marcada"))
        # ---- resultados
        s4 = f.secao("Resultados", "info")
        self.mostrar_r = s4.linha("info", P.lista(A.MOSTRAR, obj.Mostrar), "O que desenhar na tela.", "Mostrar")
        self.comb = s4.linha("tipo", QtWidgets.QComboBox(), "Combinação desenhada (diagramas e deformada).",
                             "Combinação")
        self.escala = s4.linha("folga", P.numero(1.0, 0.1, 100.0, "×", 1), "Aumenta ou diminui o desenho dos "
                               "diagramas e da deformada.", "Escala")
        self.resumo = s4.texto("")
        self.tabela = s4.widget(QtWidgets.QTableWidget(0, 4))
        self.tabela.setHorizontalHeaderLabels(["Barra", "Perfil", "Taxa", "Governa"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setMinimumHeight(160)
        self.bt_memoria = s4.widget(QtWidgets.QPushButton("Memória de cálculo (PDF)…"))
        # sinais
        self.material.currentIndexChanged.connect(self._mudou_dados)
        self.flecha.currentIndexChanged.connect(self._mudou_dados)
        self.k.valueChanged.connect(self._mudou_dados)
        self.caso.currentIndexChanged.connect(self._caso_escolhido)
        self.bt_novo.clicked.connect(self.novo_caso)
        self.bt_tirar_caso.clicked.connect(self.remover_caso)
        self.nome_caso.textEdited.connect(self._caso_editado)
        self.tipo_caso.currentIndexChanged.connect(self._caso_editado)
        self.peso.toggled.connect(self._caso_editado)
        self.bt_tirar_carga.clicked.connect(self.tirar_carga)
        self.mostrar_r.currentIndexChanged.connect(self._vista)
        self.comb.currentIndexChanged.connect(self._vista)
        self.escala.valueChanged.connect(self._vista)
        self.tabela.currentCellChanged.connect(lambda *_: self._realcar_barra())
        self.bt_memoria.clicked.connect(self.memoria)
        self._recarregar_casos()
        self._carregando = False
        self.atualizar_resultados()

    # ---- dados
    def casos(self):
        return self.analise.Proxy.casos(self.analise)

    def _gravar_casos(self, casos):
        self.analise.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        self._recalcular()

    def _recarregar_casos(self, atual=None):
        casos = self.casos()
        self.caso.blockSignals(True)
        self.caso.clear()
        for c in casos:
            self.caso.addItem(c["nome"])
        self.caso.setCurrentIndex(min(atual if atual is not None else 0, len(casos) - 1))
        self.caso.blockSignals(False)
        self._caso_escolhido()

    def _caso_escolhido(self, *_a):
        k = self.caso.currentIndex()
        casos = self.casos()
        if not (0 <= k < len(casos)):
            return
        c = casos[k]
        self._carregando, antes = True, self._carregando
        self.nome_caso.setText(c["nome"])
        self.tipo_caso.setCurrentText(c["tipo"])
        self.peso.setChecked(bool(c.get("peso_proprio")))
        self.lista_cargas.clear()
        for carga in c.get("cargas", []):
            self.lista_cargas.addItem(_texto_carga(carga))
        self._carregando = antes

    def _caso_editado(self, *_a):
        if self._carregando:
            return
        k = self.caso.currentIndex()
        casos = self.casos()
        if not (0 <= k < len(casos)):
            return
        casos[k]["nome"] = self.nome_caso.text().strip() or "Caso %d" % (k + 1)
        casos[k]["tipo"] = self.tipo_caso.currentText()
        casos[k]["peso_proprio"] = self.peso.isChecked()
        self.caso.setItemText(k, casos[k]["nome"])
        self._gravar_casos(casos)

    def novo_caso(self, nome=None, tipo=None):
        casos = self.casos()
        casos.append({"nome": nome or "Caso %d" % (len(casos) + 1),
                      "tipo": tipo or "Sobrecarga (sem predominância de equipamentos)",
                      "peso_proprio": False, "cargas": []})
        self._gravar_casos(casos)
        self._recarregar_casos(len(casos) - 1)
        return len(casos) - 1

    def remover_caso(self):
        casos = self.casos()
        k = self.caso.currentIndex()
        if len(casos) <= 1 or not (0 <= k < len(casos)):
            return
        del casos[k]
        self._gravar_casos(casos)
        self._recarregar_casos(max(0, k - 1))

    def adicionar_carga(self, carga):
        casos = self.casos()
        k = max(0, self.caso.currentIndex())
        casos[k].setdefault("cargas", []).append(carga)
        self._gravar_casos(casos)
        self._caso_escolhido()

    def tirar_carga(self):
        casos = self.casos()
        k = max(0, self.caso.currentIndex())
        j = self.lista_cargas.currentRow()
        if 0 <= j < len(casos[k].get("cargas", [])):
            del casos[k]["cargas"][j]
            self._gravar_casos(casos)
            self._caso_escolhido()

    def por_apoio(self, ponto, tipo=None):
        tipo = tipo or self.tipo_apoio.currentText()
        chave = A._chave_no(ponto)
        atuais = self.analise.Proxy.apoios(self.analise)
        if tipo == "Tirar apoio" or atuais.get(chave) == tipo:
            atuais.pop(chave, None)
        else:
            atuais[chave] = tipo
        self.analise.Apoios = ["%s=%s" % kv for kv in atuais.items()]
        self._recalcular()

    def _mudou_dados(self, *_a):
        if self._carregando:
            return
        self.analise.Material = self.material.currentData() or ""
        self.analise.LimiteFlecha = self.flecha.currentText()
        self.analise.K = self.k.value()
        self._recalcular()

    def _vista(self, *_a):
        if self._carregando:
            return
        self.analise.Mostrar = self.mostrar_r.currentText()
        self.analise.Combinacao = self.comb.currentData() or ""
        self.analise.Escala = self.escala.value()

    def _recalcular(self):
        self.analise.touch()
        self.analise.Document.recompute()
        self.atualizar_resultados()

    # ---- clique na tela
    def addSelection(self, doc, obj, sub, pnt):
        if not self._vivo():
            QtCore.QTimer.singleShot(0, self._parar)
            return
        try:
            raiz = FreeCAD.getDocument(doc).getObject(obj)
        except Exception:
            return
        if raiz is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self.clique(raiz, sub, pnt))

    def clique(self, raiz, sub, pnt):
        import PrumoEstrutura as E
        calc = getattr(self.analise.Proxy, "calc", None)
        if calc is None or calc.modelo is None:
            self.analise.Proxy.execute(self.analise)
            calc = self.analise.Proxy.calc
        if calc is None:
            return
        modo = self.modo.valor()
        p = FreeCAD.Vector(*pnt) if pnt else None
        if modo in ("apoio", "no"):
            if p is None:
                return
            no = A._no_mais_proximo(calc.modelo, (p.x, p.y, p.z))
            if no is None:
                return
            q = calc.modelo.nos[no]
            if modo == "apoio":
                self.por_apoio(q)
            else:
                self.adicionar_carga({"alvo": "no", "no": A._chave_no(q), "valor": self.valor.value(),
                                      "direcao": self.direcao.currentText(), "tipo": "no"})
        else:
            o, _el = P.resolver(raiz, sub)
            i = None
            if E.eh_barra(o):
                i = o.Indice
            elif o == self.analise.Estrutura.Esqueleto and _el.startswith("Edge"):
                i = int(_el[4:]) - 1
            if i is None:
                return
            if self.tipo_carga.currentIndex() == 0:
                carga = {"alvo": "barra", "linha": i, "tipo": "distribuida", "valor": self.valor.value(),
                         "direcao": self.direcao.currentText()}
            else:
                carga = {"alvo": "barra", "linha": i, "tipo": "pontual", "valor": self.valor.value(),
                         "posicao": self.posicao.value(), "direcao": self.direcao.currentText()}
            self.adicionar_carga(carga)
        try:
            FreeCADGui.Selection.clearSelection()
        except Exception:
            pass

    # ---- resultados
    def atualizar_resultados(self):
        obj = self.analise
        calc = getattr(obj.Proxy, "calc", None)
        self.lista_apoios.clear()
        for k, tipo in obj.Proxy.apoios(obj).items():
            x, y, z = A._ponto_da_chave(k)
            self.lista_apoios.addItem("%s em (%s; %s; %s)" % (tipo, _f(x, 0), _f(y, 0), _f(z, 0)))
        if calc is None or calc.erro:
            self.resumo.setText("<span style='color:#B5523F'>%s</span>" % (obj.Situacao or "sem resultado"))
            self.tabela.setRowCount(0)
            self.form.mensagem.mostrar((obj.Situacao or "Monte apoios e cargas.").replace("erro: ", ""),
                                       "info")
            return
        ok = obj.TaxaMaxima <= 1.0
        mat = calc.material
        self.resumo.setText(
            "<b>%s</b> · maior taxa de uso <b>%s</b> (%s)<br>Maior deslocamento (ELS): %s mm · aço: %s "
            "(fy %s, fu %s MPa)<br>%d combinações (NBR 8681)" % (
                "Atende" if ok else "NÃO ATENDE", _f(obj.TaxaMaxima, 2), obj.BarraCritica,
                _f(obj.DeslocamentoMax, 1), mat[0], _f(mat[1], 0), _f(mat[2], 0), len(calc.combinacoes))
            + "".join("<br><span style='color:#B5523F'>⚠ %s</span>" % a for a in calc.avisos))
        self.form.mensagem.mostrar("Atende: maior taxa %s." % _f(obj.TaxaMaxima, 2) if ok else
                                   "Não atende: maior taxa %s (%s)." % (_f(obj.TaxaMaxima, 2), obj.BarraCritica),
                                   "ok" if ok else "erro")
        linhas = sorted(calc.verificacao.items(), key=lambda kv: -kv[1]["taxa"])
        self.tabela.setRowCount(len(linhas))
        for r, (i, v) in enumerate(linhas):
            fl = calc.flechas.get(i)
            tx = max(v["taxa"], fl[2] if fl else 0.0)
            gov = v["governa"] if v["taxa"] >= (fl[2] if fl else 0) else "%s (%s mm de %s)" % (
                fl[4], _f(fl[0], 1), _f(fl[1], 1))
            for c, txt in enumerate(("%d" % (i + 1), calc.mapa["secoes"][i]["nome"], _f(tx, 2), gov)):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setData(32, i)
                self.tabela.setItem(r, c, it)
        self.comb.blockSignals(True)
        self.comb.clear()
        self.comb.addItem("(a que governa)", "")
        for nome, _t, _f2 in calc.combinacoes:
            self.comb.addItem(nome, nome)
        i = self.comb.findData(obj.Combinacao)
        self.comb.setCurrentIndex(max(0, i))
        self.comb.blockSignals(False)

    def _realcar_barra(self):
        it = self.tabela.item(self.tabela.currentRow(), 0)
        if it is None:
            return
        i = it.data(32)
        import PrumoEstrutura as E
        for b in E.barras_de(self.analise.Estrutura):
            if b.Indice == i:
                self._sincr = True
                FreeCADGui.Selection.clearSelection()
                self._ignorar_selecao = True
                try:
                    FreeCADGui.Selection.addSelection(b)
                finally:
                    self._ignorar_selecao = False

    def memoria(self):
        import PrumoAnaliseRelatorio as R
        caminho, _f2 = QtWidgets.QFileDialog.getSaveFileName(None, "Memória de cálculo", "memoria-estrutura.pdf",
                                                             "PDF (*.pdf)")
        if caminho:
            R.gerar_pdf(self.analise, caminho)
            self.form.mensagem.mostrar("Memória de cálculo gravada em %s." % caminho, "ok")

    # ---- painel de tarefas
    def pendencia(self):
        return None

    def pronto_texto(self):
        return "Resultados na tela. OK grava a análise; Cancelar desfaz."

    def executar(self):
        return self.analise

    def accept(self):
        if self._transacao_painel:
            self.analise.Document.commitTransaction()
            self._transacao_painel = False
        self._parar()
        return True

    def reject(self):
        if self._transacao_painel:
            doc = self.analise.Document
            nome = self.analise.Name if self._criada else None
            try:
                doc.abortTransaction()
            except Exception:
                pass
            if nome and doc.getObject(nome) is not None:
                doc.removeObject(nome)
            doc.recompute()
            self._transacao_painel = False
        self._parar()
        return True

    def close(self):
        self.reject()
        try:
            self.form.deleteLater()
        except RuntimeError:
            pass


def _norma():
    import PrumoNBR8800 as N
    return N.EDICAO


def _texto_carga(c):
    if c["alvo"] == "no":
        x, y, z = A._ponto_da_chave(c["no"])
        return "Nó (%s; %s; %s): %s kN, %s" % (_f(x, 0), _f(y, 0), _f(z, 0), _f(c["valor"]), c["direcao"])
    if c["tipo"] == "distribuida":
        return "Barra %d: %s kN/m, %s" % (int(c["linha"]) + 1, _f(c["valor"]), c["direcao"])
    return "Barra %d: %s kN a %s mm, %s" % (int(c["linha"]) + 1, _f(c["valor"]), _f(c.get("posicao", 0), 0),
                                           c["direcao"])


def abrir_painel(est, analise=None, mostrar=True):
    """Abre o painel para a análise da estrutura (cria a análise se ainda não houver)."""
    doc = est.Document
    doc.openTransaction("Simulação da estrutura")
    criada = False
    if analise is None:
        analise = A.analise_de(est)
    if analise is None:
        analise = A.criar(doc, est)
        criada = True
    FreeCADGui.Selection.clearSelection()
    p = PainelAnalise(analise)
    p._transacao_painel = True
    p._criada = criada
    if mostrar:
        p.mostrar()
    return p


class CmdAnaliseEstrutura:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("estrutura.svg"), "MenuText": "Simular estrutura",
                "ToolTip": "Cálculo da estrutura soldada por barras: apoios, cargas, combinações (NBR 8681), "
                           "esforços, deslocamentos e verificação das barras pela NBR 8800."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        import PrumoEstrutura as E
        for o in FreeCADGui.Selection.getSelection():
            est = E.estrutura_de(o)
            if est is not None:
                abrir_painel(est)
                return
            if "Apoios" in getattr(o, "PropertiesList", []) and getattr(o, "Estrutura", None) is not None:
                abrir_painel(o.Estrutura, o)
                return
        import PrumoSelecao
        PrumoSelecao.pedir("Simular estrutura", "Escolha a estrutura soldada (ou uma barra dela).",
                           [("Estrutura", "estruturas", 1, 1)], lambda ests: abrir_painel(ests[0]))
