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


OPCOES = {"sem_titulo": False}
# fonte dos textos na cena 3D: sem nome, o Coin usa a fonte padrão (monoespaçada); Arial existe no
# Windows e o fontconfig do Linux troca por uma equivalente (Liberation Sans / DejaVu Sans)
FONTE_3D = "Arial"     # vídeo: o título vai na faixa do quadro, não na cena


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
        if prop in ("Situacao", "TaxaMaxima", "Mostrar", "Combinacao", "Escala", "Apoios", "Casos", "Resumo", "Modo"):
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
        self._rotulas(obj, calc, tam)
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
            elif mostrar == A.DEFORMADA_TAXA:
                self._deformada(m, r, tam, obj.Escala, calc)
            elif mostrar == A.MODO_VIBRAR:
                self._modo(m, calc, tam, obj)
            else:
                chave = {"Momento fletor (M)": "My", "Esforço cortante (V)": "Vz",
                         "Esforço normal (N)": "N"}[mostrar]
                self._diagrama(m, r, chave, tam, obj.Escala)
            if not OPCOES["sem_titulo"]:
                self._texto(_meio_modelo(m), "%s · %s" % (mostrar, nome), (0.0, 0.23, 0.44), 15, centro=True)

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

    def _texto(self, p, txt, cor=(0.0, 0.23, 0.44), tamanho=14, centro=False):
        from pivy import coin
        s = self._sep()
        mat = coin.SoBaseColor()
        mat.rgb.setValue(*cor)
        f = coin.SoFont()
        f.name = FONTE_3D
        f.size = tamanho
        tr = coin.SoTranslation()
        tr.translation.setValue(float(p[0]), float(p[1]), float(p[2]))
        t = coin.SoText2()
        t.string = txt
        if centro:
            t.justification = coin.SoText2.CENTER
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
            if tipo.startswith("Mola"):
                kx, _ky, kz = A.rigidez_mola(tipo)
                self._marcas([p], (0.55, 0.30, 0.05), coin.SoMarkerSet.DIAMOND_FILLED_9_9)
                self._texto((p[0], p[1], p[2] - 0.04 * tam), "Mola %s/%s kN/mm" % (_f(kx), _f(kz)),
                            (0.55, 0.30, 0.05), 12)
                continue
            idx, cor = tipos.get(tipo, tipos["Engaste"])
            self._marcas([p], cor, idx)
            self._texto((p[0], p[1], p[2] - 0.04 * tam), tipo.split(" ")[0], cor, 13)

    def _rotulas(self, obj, calc, tam):
        """Círculo vazado perto da ponta rotulada; "T" no meio da barra de treliça."""
        from pivy import coin
        pts = []
        for i, tipo in obj.Proxy.liberacoes(obj).items():
            if i not in calc.mapa["linhas"]:
                continue
            p0, t, L = calc.mapa["linhas"][i]
            d = min(0.04 * tam, 0.2 * L)
            if tipo in ("Rótula no início", "Rótula nas duas pontas") or tipo in A.TRELICAS:
                pts.append(p0 + t * d)
            if tipo in ("Rótula no fim", "Rótula nas duas pontas") or tipo in A.TRELICAS:
                pts.append(p0 + t * (L - d))
            if tipo in A.TRELICAS:
                self._texto(p0 + t * (L / 2.0), "treliça" if tipo == A.TRELICAS[0] else "só tração",
                            (0.35, 0.35, 0.35), 11)
        self._marcas(pts, (0.0, 0.0, 0.0), coin.SoMarkerSet.CIRCLE_LINE_9_9)

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
                    if carga["tipo"] == "trapezoidal":
                        a0 = float(carga.get("inicio", 0.0))
                        b0 = float(carga.get("fim", 0.0)) or L
                        v1, v2 = float(carga["valor"]), float(carga.get("valor2", carga["valor"]))
                        vm = max(abs(v1), abs(v2), 1e-9)
                        pts, segs = [], []
                        for k in range(7):
                            sk = a0 + (b0 - a0) * k / 6.0
                            vk = v1 + (v2 - v1) * k / 6.0
                            p = p0 + t * sk
                            topo = p - dv * seta * (abs(vk) / vm)
                            segs.append([topo, p])
                            pts.append(topo)
                        segs.append(pts)
                        self._linhas(segs, (0.75, 0.25, 0.05), 2)
                        self._texto(pts[3] - dv * seta * 0.3, "%s → %s kN/m (%s)" % (_f(v1), _f(v2), c["nome"]),
                                    (0.75, 0.25, 0.05), 12)
                    elif carga["tipo"] == "distribuida":
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

    def _modo(self, m, calc, tam, obj):
        import numpy as np
        modos = getattr(calc, "modos", None)
        k = max(1, int(getattr(obj, "Modo", 1) or 1)) - 1
        if not modos or k >= len(modos):
            self._texto(_meio_modelo(m), "Calcule as frequências no painel (Resultados)", (0.6, 0.3, 0.1), 13,
                        centro=True)
            return
        f, phi = modos[k]
        maxd = max(float(np.linalg.norm(phi[6 * n:6 * n + 3])) for n in range(len(m.nos))) or 1.0
        esc = 0.08 * tam / maxd * (obj.Escala or 1.0)
        segs = []
        for b in m.barras:
            a = m.nos[b.i] + phi[6 * b.i:6 * b.i + 3] * esc
            c = m.nos[b.j] + phi[6 * b.j:6 * b.j + 3] * esc
            segs.append([_vec(*a), _vec(*c)])
        self._linhas(segs, (0.45, 0.20, 0.65), 4)
        if not OPCOES["sem_titulo"]:
            self._texto(_meio_modelo(m), "Modo %d · %s Hz" % (k + 1, _f(f, 2)), (0.45, 0.20, 0.65), 15,
                        centro=True)

    def _deformada(self, m, r, tam, escala, calc=None):
        import numpy as np
        maxd = max((float(np.linalg.norm(r.u[6 * n:6 * n + 3])) for n in range(len(m.nos))), default=0.0)
        for nb in range(len(m.barras)):
            maxd = max(maxd, max(r.flecha_local(nb, 7)))
        if maxd <= 0:
            return
        k = 0.06 * tam / maxd * (escala or 1.0)
        grupos = {}
        for nb, b in enumerate(m.barras):
            R, L = m.eixos(b)
            pts = _curva_deformada(r, nb, b, R, L, m, k)
            cor = (0.85, 0.30, 0.20)
            if calc is not None and b.origem is not None:
                i = b.origem[0]
                v = calc.verificacao.get(i)
                if v is not None:
                    cor = _cor_taxa(max(v["taxa"], calc.flechas.get(i, (0, 0, 0))[2]))
            grupos.setdefault(cor, []).append(pts)
        for cor, segs in grupos.items():
            self._linhas(segs, cor, 5 if calc is not None else 3)
        n_max = max(range(len(m.nos)), key=lambda n: float(np.linalg.norm(r.u[6 * n:6 * n + 3])))
        d = r.u[6 * n_max:6 * n_max + 3]
        self._texto(_vec(*m.nos[n_max]) + _vec(*d) * k, "%s mm" % _f(float(np.linalg.norm(d)), 1),
                    (0.85, 0.30, 0.20), 13)


def _curva_deformada(r, nb, b, R, L, m, k, n=9):
    import numpy as np
    import PrumoPortico as PT
    pts = []
    for q in range(n):
        x = L * q / (n - 1)
        u, v, w = PT.deslocamento_local(r, nb, x)
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
    # acima do contorno do modelo também na vista isométrica (o topo projetado sobe ~0,25 do tamanho)
    return _vec(c[0], c[1], top[2] + 0.32 * _tamanho(m))


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
                ("no", "Carga no nó", "posicao", "Clique num nó para aplicar a força do caso"),
                ("rotula", "Rótula", "tipo", "Clique perto da ponta de uma barra para rotular essa ponta, "
                 "ou na barra para torná-la de treliça (escolha abaixo)"),
                ("detalhe", "Detalhar nó", "info", "Clique num nó (ligação ou apoio) para calcular o detalhe "
                 "por elementos finitos sólidos")]
TIPOS_CARGA = ["Distribuída (kN/m)", "Concentrada na barra (kN)", "Distribuída variável / parcial (kN/m)"]
ACOES_ROTULA = ["Rótula na ponta clicada", "Barra de treliça (rótula nas duas pontas)", "Tirar as rótulas da barra",
                "Contraventamento só tração"]


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
                               "Limite de flecha das vigas (Anexo B da NBR 8800:2024).", "Flecha")
        # NBR 8800:2024 não usa K: o campo fica fora da tela (a propriedade antiga é mantida no arquivo)
        self.k = P.numero(obj.K or 1.0, 0.5, 5.0, "", 2)
        self.k.setVisible(False)
        aviso = s0.texto("<span style='color:#B5523F'>%s</span>" % _norma())
        # ---- clique
        s1 = f.secao("O clique na tela", "selecao")
        self.modo = P.Opcoes([(k, t, ic, d) for k, t, ic, d in MODOS_CLIQUE], "apoio")
        s1.widget(self.modo)
        self.tipo_apoio = s1.linha("tipo", P.lista(list(A.APOIOS) + ["Mola (kN/mm)", "Tirar apoio"], "Engaste"),
                                   "Engaste: trava tudo. Rótula: trava deslocamentos e solta rotações. Rolete: "
                                   "só trava a vertical.", "Apoio")
        self.k_v = s1.linha("quantidade", P.numero(10.0, 0.0, 1e7, " kN/mm", 2), "Mola: rigidez vertical "
                            "(apoio elástico: solo, viga de apoio, coxim).", "Mola vertical")
        self.k_h = s1.linha("quantidade", P.numero(0.0, 0.0, 1e7, " kN/mm", 2), "Mola: rigidez horizontal, igual "
                            "em X e Y (0 = solta na horizontal).", "Mola horizontal")
        self.tipo_apoio.currentTextChanged.connect(lambda *_: self._campos_mola())
        self.lista_apoios = s1.widget(QtWidgets.QListWidget())
        self.lista_apoios.setMaximumHeight(90)
        self.acao_rotula = s1.linha("tipo", P.lista(ACOES_ROTULA), "Rótula: a ponta da barra não transmite momento "
                                    "(ligação flexível). Treliça: a barra só trabalha à força normal nas pontas.",
                                    "Rótula")
        self.lista_lib = s1.widget(QtWidgets.QListWidget())
        self.lista_lib.setMaximumHeight(70)
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
        self.valor2 = s3.linha("quantidade", P.numero(5.0, -1e6, 1e6, "", 2), "Variável: valor no fim do trecho "
                               "(kN/m). O Valor acima é o do começo.", "Valor no fim")
        self.fim = s3.linha("comprimento", P.numero(0.0, 0.0, 1e7, " mm", 0), "Variável: onde o trecho carregado "
                            "termina, a partir do Início da barra (0 = até o fim da barra).", "Até")
        self.posicao = s3.linha("comprimento", P.numero(0.0, 0.0, 1e7, " mm", 0), "Concentrada: distância a partir "
                                "do Início da barra. Variável: onde o trecho carregado começa.", "Posição")
        self.tipo_carga.currentIndexChanged.connect(lambda *_: self._campos_carga())
        self._campos_carga()
        self._campos_mola()
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
        self.bt_freq = s4.widget(QtWidgets.QPushButton("Frequências naturais (modos de vibrar)"))
        self.bt_freq.setToolTip("Massa do peso próprio das barras e das cargas permanentes verticais. Útil para "
                                "bancadas com motor, peneira ou bomba: fuja das frequências de operação.")
        self.lista_modos = s4.widget(QtWidgets.QListWidget())
        self.lista_modos.setMaximumHeight(110)
        self.lista_modos.setVisible(False)
        self.bt_video = s4.widget(QtWidgets.QPushButton("Gravar vídeo do comportamento…"))
        self.bt_video.setToolTip("Vídeo com cargas e apoios, a deformada com as cores da taxa de uso, o momento "
                                 "fletor e as barras críticas (MP4 ou GIF)")
        # ---- detalhe por elementos finitos
        s5 = f.secao("Detalhe da ligação (elementos finitos)", "info", aberta=False)
        self.sec_detalhe = s5
        self.det_no = s5.texto("Escolha <b>Detalhar nó</b> no clique e clique numa ligação ou apoio. O Prumo "
                               "recorta o nó, aplica os esforços desta análise nos cortes e calcula as "
                               "tensões no sólido (CalculiX).")
        self.det_comb = s5.linha("tipo", QtWidgets.QComboBox(), "Combinação última usada no detalhe (a que governa "
                                 "as barras do nó, se não escolher).", "Combinação")
        self.det_dist = s5.linha("comprimento", P.numero(0.0, 0.0, 5000.0, " mm", 0), "Distância do nó até o corte "
                                 "de cada barra. 0: automático (2 × a maior altura de perfil).", "Corte a")
        self.bt_detalhe = s5.widget(QtWidgets.QPushButton("Calcular o detalhe"))
        self.bt_detalhe.setEnabled(False)
        self._junta = None
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
        self.bt_detalhe.clicked.connect(self.calcular_detalhe)
        self.bt_video.clicked.connect(self.video)
        self.bt_freq.clicked.connect(self.calcular_modos)
        self.lista_modos.currentRowChanged.connect(self._mostrar_modo)
        self.det_dist.valueChanged.connect(lambda *_: self.mostrar_marcas())
        self.modo.mudou.connect(self._modo_mudou)
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
        if tipo.startswith("Mola"):
            tipo = A.texto_mola(self.k_h.value(), self.k_v.value())
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
        if modo == "detalhe":
            if p is not None:
                self.escolher_junta(p)
            return
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
            if modo == "rotula":
                ponta = None
                calc2 = self.analise.Proxy.calc
                if p is not None and calc2 is not None and i in calc2.mapa["linhas"]:
                    p0, t, L = calc2.mapa["linhas"][i]
                    ponta = "ini" if (p - p0).dot(t) < L / 2.0 else "fim"
                self.liberar(i, ponta)
                try:
                    FreeCADGui.Selection.clearSelection()
                except Exception:
                    pass
                return
            if self.tipo_carga.currentIndex() == 2:
                carga = {"alvo": "barra", "linha": i, "tipo": "trapezoidal", "valor": self.valor.value(),
                         "valor2": self.valor2.value(), "inicio": self.posicao.value(), "fim": self.fim.value(),
                         "direcao": self.direcao.currentText()}
            elif self.tipo_carga.currentIndex() == 0:
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
    def _campos_mola(self):
        mola = self.tipo_apoio.currentText().startswith("Mola")
        self.k_v.setEnabled(mola)
        self.k_h.setEnabled(mola)

    def _campos_carga(self):
        k = self.tipo_carga.currentIndex()
        self.posicao.setEnabled(k in (1, 2))
        self.valor2.setEnabled(k == 2)
        self.fim.setEnabled(k == 2)

    def liberar(self, i, ponta=None):
        """Aplica a ação de rótula escolhida na barra i (ponta: "ini" / "fim", a mais perto do clique)."""
        obj = self.analise
        libs = obj.Proxy.liberacoes(obj)
        acao = self.acao_rotula.currentIndex()
        atual = libs.get(i, "")
        if acao == 1:
            libs[i] = "Barra de treliça"
        elif acao == 3:
            libs[i] = A.TRELICAS[1]
        elif acao == 2:
            libs.pop(i, None)
        else:
            pontas = {"Rótula no início": {"ini"}, "Rótula no fim": {"fim"}, "Rótula nas duas pontas": {"ini", "fim"},
                      "Barra de treliça": {"ini", "fim"}}.get(atual, set())
            pontas ^= {ponta or "ini"}
            nome = {frozenset(["ini"]): "Rótula no início", frozenset(["fim"]): "Rótula no fim",
                    frozenset(["ini", "fim"]): "Rótula nas duas pontas"}.get(frozenset(pontas))
            if nome:
                libs[i] = nome
            else:
                libs.pop(i, None)
        obj.Liberacoes = ["%d=%s" % (k, v) for k, v in sorted(libs.items())]
        self._recalcular()

    def atualizar_resultados(self):
        obj = self.analise
        calc = getattr(obj.Proxy, "calc", None)
        self.lista_lib.clear()
        for i, tipo in sorted(obj.Proxy.liberacoes(obj).items()):
            self.lista_lib.addItem("Barra %d: %s" % (i + 1, tipo.lower()))
        self.lista_apoios.clear()
        for k, tipo in obj.Proxy.apoios(obj).items():
            x, y, z = A._ponto_da_chave(k)
            if tipo.startswith("Mola"):
                kx, _ky, kz = A.rigidez_mola(tipo)
                tipo = "Mola (H %s, V %s kN/mm)" % (_f(kx), _f(kz))
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

    # ---- detalhe por elementos finitos
    def _modo_mudou(self, *_a):
        if self.modo.valor() == "detalhe":
            self.sec_detalhe._alternar(True)
        self.mostrar_marcas()

    def escolher_junta(self, p):
        import PrumoDetalheFEM as D
        try:
            j = D.junta_mais_proxima(self.analise, FreeCAD.Vector(p))
        except ValueError as ex:
            self.form.mensagem.mostrar(str(ex), "erro")
            return None
        if j is None:
            return None
        self._junta = j
        calc = self.analise.Proxy.calc
        self.det_comb.clear()
        gov = D.combinacao_que_governa(calc, j["linhas"])
        self.det_comb.addItem("%s (a que governa)" % gov, gov)
        for nome, tipo, _f2 in calc.combinacoes:
            if tipo == "ELU" and nome != gov:
                self.det_comb.addItem(nome, nome)
        self.det_no.setText("<b>%s</b>" % j["texto"])
        self.bt_detalhe.setEnabled(True)
        self.sec_detalhe._alternar(True)
        self.mostrar_marcas()
        return j

    def marcas(self):
        if self._junta is None or self.modo.valor() != "detalhe":
            return []
        res = [(self._junta["ponto"], "nó do detalhe", True)]
        calc = self.analise.Proxy.calc
        h = 0.0
        try:
            import PrumoDetalheFEM as D
            sec = D._secoes(self.analise.Estrutura)
            h = max(max(sec(i).alt, sec(i).larg) for i, _s in self._junta["linhas"])
        except Exception:
            pass
        d = self.det_dist.value() or max(2.0 * h, 150.0)
        for i, s0 in self._junta["linhas"]:
            p0, t, L = calc.mapa["linhas"][i]
            for sinal in (1, -1):
                sc = s0 + sinal * d
                if 0.0 < sc < L:
                    res.append((p0 + t * sc, "corte · barra %d" % (i + 1), False))
        return res

    def calcular_detalhe(self):
        """Grava a análise (fecha o painel) e calcula o detalhe do nó escolhido; abre o assistente."""
        if self._junta is None:
            return None
        analise = self.analise
        ponto = FreeCAD.Vector(self._junta["ponto"])
        comb = self.det_comb.currentData()
        dist = self.det_dist.value()
        self.accept()
        try:
            FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        return detalhar_com_progresso(analise, ponto, comb, dist)

    def calcular_modos(self):
        calc = getattr(self.analise.Proxy, "calc", None)
        if calc is None or calc.modelo is None or calc.erro:
            self.form.mensagem.mostrar("Calcule a estrutura (apoios) antes das frequências.", "erro")
            return None
        try:
            modos = A.frequencias(calc, self.casos(), 6)
        except Exception as ex:
            self.form.mensagem.mostrar("Frequências não calculadas: %s" % ex, "erro")
            return None
        self.lista_modos.clear()
        for k, (f, _v) in enumerate(modos):
            self.lista_modos.addItem("Modo %d: %s Hz" % (k + 1, _f(f, 2)))
        self.lista_modos.setVisible(True)
        self.lista_modos.setCurrentRow(0)
        return modos

    def _mostrar_modo(self, k):
        if k < 0:
            return
        self.analise.Modo = k + 1
        self.analise.Mostrar = A.MODO_VIBRAR
        i = self.mostrar_r.findText(A.MODO_VIBRAR)
        if i >= 0:
            self.mostrar_r.blockSignals(True)
            self.mostrar_r.setCurrentIndex(i)
            self.mostrar_r.blockSignals(False)
        self.analise.Document.recompute()

    def video(self):
        import PrumoVideo
        calc = getattr(self.analise.Proxy, "calc", None)
        if calc is None or calc.erro:
            self.form.mensagem.mostrar("Calcule a estrutura (apoios e cargas) antes de gravar o vídeo.", "erro")
            return None
        self.remover_marcas()
        return PrumoVideo.escolher_e_gravar(PrumoVideo.gravar_estrutura, self.analise, "estrutura.mp4")

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
        self.remover_marcas()
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
        self.remover_marcas()
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
    if c["tipo"] == "trapezoidal":
        fim = float(c.get("fim", 0.0))
        return "Barra %d: %s a %s kN/m de %s a %s mm, %s" % (
            int(c["linha"]) + 1, _f(c["valor"]), _f(c.get("valor2", c["valor"])), _f(c.get("inicio", 0.0), 0),
            _f(fim, 0) if fim else "fim", c["direcao"])
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


def detalhar_com_progresso(analise, ponto, combinacao=None, distancia=0.0):
    """Calcula o detalhe com o cursor de espera e abre o resultado no assistente de simulação."""
    import PrumoDetalheFEM as D
    import PrumoFEM
    mw = FreeCADGui.getMainWindow()
    doc = analise.Document
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

    def prog(txt):
        try:
            mw.statusBar().showMessage("Detalhe da ligação: " + txt)
        except Exception:
            pass
        QtWidgets.QApplication.processEvents()
    doc.openTransaction("Detalhe da ligação")
    try:
        prog("recortando o nó…")
        est, det, erro = D.detalhar(analise, ponto, combinacao, distancia, progresso=prog)
        doc.commitTransaction()
    except Exception as ex:
        doc.abortTransaction()
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.warning(mw, "Detalhe da ligação", "Não foi possível montar o detalhe: %s" % ex)
        return None
    finally:
        try:
            mw.statusBar().clearMessage()
        except Exception:
            pass
    QtWidgets.QApplication.restoreOverrideCursor()
    try:
        analise.Estrutura.ViewObject.Visibility = False
        analise.ViewObject.Visibility = False
    except Exception:
        pass
    if erro:
        QtWidgets.QMessageBox.warning(mw, "Detalhe da ligação", erro)
    else:
        PrumoFEM.mostrar_campo(est, "tensao")
    try:
        v = FreeCADGui.ActiveDocument.ActiveView
        v.viewIsometric()
        v.fitAll()
        PrumoFEM.mostrar()
    except Exception:
        pass
    return est
