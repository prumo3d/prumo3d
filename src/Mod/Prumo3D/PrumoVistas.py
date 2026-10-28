# SPDX-License-Identifier: LGPL-2.1-or-later
"""Paleta de vistas e cotas gerais para a aba Desenho.

Um clique põe uma vista (frontal, superior, laterais, inferior, posterior ou isométrica) da peça
numa folha — a folha aberta, uma já existente ou uma folha ABNT nova. As vistas ortogonais entram
no mesmo grupo de projeção (1º diedro), então ficam alinhadas e acompanham a escala da folha.
"Cotas gerais" põe o comprimento, a altura e a profundidade totais da peça nas vistas.
"""

import FreeCAD

import PrumoUtil
import PrumoFolhas

VISTAS = (("Front", "Frontal"), ("Top", "Superior"), ("Left", "Lateral esquerda"),
          ("Right", "Lateral direita"), ("Bottom", "Inferior"), ("Rear", "Posterior"),
          ("Iso", "Isométrica"))
NOMES = dict(VISTAS)
ICONES = {"Front": "vista_frontal.svg", "Top": "vista_superior.svg", "Left": "vista_lateral.svg",
          "Right": "vista_lateral.svg", "Bottom": "vista_superior.svg", "Rear": "vista_frontal.svg",
          "Iso": "vista_iso.svg"}


# ============================================================================ lógica (sem interface)
def folhas(doc):
    return [o for o in (doc.Objects if doc else []) if o.isDerivedFrom("TechDraw::DrawPage")]


def _fontes(objs):
    return list(dict.fromkeys(o for o, _sh in PrumoUtil.pecas(objs)))


def _mesmas(a, b):
    return {o.Name for o in a} == {o.Name for o in b}


def grupo_da_peca(page, objs):
    """Grupo de projeção da folha que mostra exatamente essas peças (ou None)."""
    fontes = _fontes(objs)
    for v in page.Views:
        if v.isDerivedFrom("TechDraw::DrawProjGroup") and _mesmas(v.Source, fontes):
            return v
    return None


def iso_da_peca(page, objs):
    fontes = _fontes(objs)
    for v in page.Views:
        if v.TypeId == "TechDraw::DrawViewPart" and _mesmas(v.Source, fontes) \
                and abs(v.Direction.x - 1) < 1e-6 and abs(v.Direction.y + 1) < 1e-6:
            return v
    return None


def projecoes(grupo):
    return [v.Type for v in grupo.Views] if grupo is not None else []


def vistas_na_folha(page, objs):
    """Chaves das vistas dessa peça que a folha já tem."""
    r = projecoes(grupo_da_peca(page, objs))
    if iso_da_peca(page, objs) is not None:
        r.append("Iso")
    return r


def _so_dessa_peca(page, fontes):
    """A folha só tem vistas dessa peça (então a paleta pode ajustar escala e posições)."""
    for v in page.Views:
        if v.isDerivedFrom("TechDraw::DrawProjGroup") or v.TypeId == "TechDraw::DrawViewPart":
            if not _mesmas(v.Source, fontes):
                return False
    return True


def adicionar_vista(page, objs, chave):
    """Põe a vista `chave` (ver VISTAS) das peças na folha e devolve o objeto criado.

    Se a vista já está lá, devolve a existente sem duplicar. Numa folha só dessa peça, a escala
    normalizada e as posições são refeitas para o conjunto caber, como no arranjo da Folha ABNT."""
    doc = page.Document
    fontes = _fontes(objs)
    if not fontes:
        raise ValueError("Escolha uma peça.")
    if chave not in NOMES:
        raise ValueError("Vista desconhecida: %s" % chave)
    grupo = grupo_da_peca(page, fontes)
    iso = iso_da_peca(page, fontes)
    feito = None
    if chave == "Iso":
        if iso is None:
            iso = PrumoFolhas.nova_iso(doc, page, fontes)
        feito = iso
    else:
        if grupo is None:
            grupo = PrumoFolhas.novo_grupo(doc, page, fontes, ("Front",))
        if chave not in projecoes(grupo):
            grupo.addProjection(chave)
        feito = [v for v in grupo.Views if v.Type == chave][0]
    antes = float(page.Scale or 1.0)
    if _so_dessa_peca(page, fontes):
        PrumoFolhas.posicionar(page, fontes, grupo, iso)
    elif feito is iso and iso is not None:
        iso.Scale = float(page.Scale or 1.0) * PrumoFolhas.FATOR_ISO
    doc.recompute()
    if abs(float(page.Scale or 1.0) - antes) > 1e-9:
        refazer(page)
    return feito


def refazer(page):
    """Depois de mudar a escala da folha, as vistas do grupo só refazem o desenho se forem tocadas."""
    for v in page.Views:
        if v.isDerivedFrom("TechDraw::DrawProjGroup"):
            for it in v.Views:
                it.touch()
        elif v.isDerivedFrom("TechDraw::DrawViewPart"):
            v.touch()
    page.Document.recompute()


def folha_tem_vistas(page):
    return any(v.isDerivedFrom("TechDraw::DrawViewPart") or v.isDerivedFrom("TechDraw::DrawProjGroup")
               for v in page.Views)


# ---------------------------------------------------------------------------- cotas gerais
def _vertices(vista):
    """[(nome, x, y)] dos vértices visíveis da vista, nas coordenadas da vista."""
    r = []
    i = 0
    while True:
        try:
            v = vista.getVertexByIndex(i)
        except Exception:
            break
        if v is None:
            break
        p = v.Point
        r.append(("Vertex%d" % i, p.x, p.y))
        i += 1
        if i > 20000:
            break
    return r


def _largura_esperada(vista):
    """Largura (eixo X da vista, em mm de papel) que a peça deve ter na vista, pela caixa envolvente."""
    bb = PrumoFolhas._caixa(vista.Source)
    if bb is None:
        return None
    xs = []
    for x in (bb.XMin, bb.XMax):
        for y in (bb.YMin, bb.YMax):
            for z in (bb.ZMin, bb.ZMax):
                xs.append(vista.projectPoint(FreeCAD.Vector(x, y, z)).x)
    return max(xs) - min(xs)          # sem escala, como getVertexByIndex devolve


def vista_pronta(vista):
    """A linha oculta (HLR) é calculada em segundo plano, e depois de mudar a escala a geometria antiga
    fica até o cálculo novo terminar: só dá para cotar quando ela bate com a escala atual."""
    vs = _vertices(vista)
    if not vs:
        return False
    try:
        esperada = _largura_esperada(vista)
    except Exception:
        return True
    if not esperada:
        return True
    obtida = max(t[1] for t in vs) - min(t[1] for t in vs)
    # vale para as vistas ortogonais (a caixa projetada é o contorno); a isométrica não é cotada
    return abs(obtida - esperada) <= 0.01 * esperada + 1e-6 or abs(vista.Direction.x - 1) < 1e-6 \
        and abs(vista.Direction.y + 1) < 1e-6


def _extremos(vista, eixo):
    vs = _vertices(vista)
    if len(vs) < 2:
        return None
    k = 1 if eixo == "x" else 2
    a = min(vs, key=lambda t: t[k])
    b = max(vs, key=lambda t: t[k])
    if abs(b[k] - a[k]) < 1e-6:
        return None
    return a, b


def _cota(page, vista, tipo, a, b, rotulo, lado):
    """Cota entre os vértices a e b; `lado` (cima, baixo, esq, dir) diz de que lado da vista ela fica."""
    doc = vista.Document
    d = doc.addObject("TechDraw::DrawViewDimension", "Cota")
    d.Label = rotulo
    d.Type = tipo
    d.MeasureType = "Projected"
    d.References2D = [(vista, a[0]), (vista, b[0])]
    page.addView(d)
    # posição em mm de papel, a partir do centro da vista: 8 mm fora do contorno
    try:
        e = float(vista.getScale())
    except Exception:
        e = float(getattr(vista, "Scale", 1.0) or 1.0)
    vs = _vertices(vista)
    meia_l = max(abs(t[1]) for t in vs) * e
    meia_a = max(abs(t[2]) for t in vs) * e
    d.X, d.Y = {"cima": (0.0, meia_a + 8.0), "baixo": (0.0, -(meia_a + 8.0)),
                "esq": (-(meia_l + 8.0), 0.0), "dir": (meia_l + 8.0, 0.0)}[lado]
    d.recompute()
    return d


def cotas_gerais(page, objs):
    """Comprimento e altura totais na frontal; profundidade na lateral (ou na superior).

    Devolve a lista das cotas criadas. As vistas precisam estar calculadas (ver vista_pronta)."""
    grupo = grupo_da_peca(page, objs)
    if grupo is None:
        raise ValueError("Ponha a vista frontal da peça na folha antes das cotas.")
    por_tipo = {v.Type: v for v in grupo.Views}
    frente = por_tipo.get("Front")
    if frente is None:
        raise ValueError("Falta a vista frontal.")
    criadas = []
    # o lado livre de cada vista no 1º diedro: em cima da frontal só há a inferior; à esquerda, a lateral direita
    ex = _extremos(frente, "x")
    if ex:
        criadas.append(_cota(page, frente, "DistanceX", ex[0], ex[1], "Comprimento total",
                             "baixo" if "Bottom" in por_tipo and "Top" not in por_tipo else "cima"))
    ey = _extremos(frente, "y")
    if ey:
        criadas.append(_cota(page, frente, "DistanceY", ey[0], ey[1], "Altura total",
                             "dir" if "Right" in por_tipo and "Left" not in por_tipo else "esq"))
    lado = por_tipo.get("Left") or por_tipo.get("Right")
    cima = por_tipo.get("Top") or por_tipo.get("Bottom")
    if lado is not None:
        ez = _extremos(lado, "x")
        if ez:
            criadas.append(_cota(page, lado, "DistanceX", ez[0], ez[1], "Profundidade total", "cima"))
    elif cima is not None:
        ez = _extremos(cima, "y")
        if ez:
            criadas.append(_cota(page, cima, "DistanceY", ez[0], ez[1], "Profundidade total", "esq"))
    page.Document.recompute()
    return criadas


def esperar_vistas(vistas, segundos=20.0):
    """Espera o cálculo das vistas (útil em script e nos testes)."""
    import time
    try:
        from PySide import QtWidgets
    except ImportError:
        QtWidgets = None
    fim = time.time() + segundos
    tocar = time.time() + 1.5
    while time.time() < fim:
        atrasadas = [v for v in vistas if not vista_pronta(v)]
        if not atrasadas:
            return True
        if time.time() > tocar:
            # um recálculo pedido enquanto o anterior ainda rodava pode ter sido ignorado: pede de novo
            for v in atrasadas:
                v.touch()
            atrasadas[0].Document.recompute()
            tocar = time.time() + 3.0
        if QtWidgets is not None:
            QtWidgets.QApplication.processEvents()
        time.sleep(0.05)
    return False


# ============================================================================ interface
try:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets
    import PrumoPainel as P
except ImportError:      # sem interface (testes de console)
    FreeCADGui = None
    P = None


def _filtro_pecas(obj, subs):
    return [(obj.Label, obj)] if PrumoUtil.pecas([obj]) else []


NOVA = "__nova__"

if P is not None:
    class PainelPaletaVistas(P.PainelTarefa):
        titulo = "Paleta de vistas"
        ajuda = "Escolha a peça e clique na vista: ela entra na folha na hora."

        def __init__(self, doc=None, objs=None):
            self.doc = doc or FreeCAD.ActiveDocument
            self._objs_iniciais = list(objs or [])
            super().__init__()

        def montar(self):
            f = self.form
            s0 = f.secao("Peça", "selecao")
            self.pecas = f.caixa(s0, "Peça", _filtro_pecas, minimo=1,
                                 dica="Peça, corpo, parte ou montagem.")
            for o in self._objs_iniciais:
                self.pecas.aceitar(o)
            s1 = f.secao("Folha", "folha")
            self.folha = QtWidgets.QComboBox()
            s1.linha("folha", self.folha, "Onde as vistas entram.", "Folha")
            self._encher_folhas()
            s2 = f.secao("Vistas", "posicao")
            grade = QtWidgets.QWidget()
            g = QtWidgets.QGridLayout(grade)
            g.setContentsMargins(0, 0, 0, 0)
            g.setSpacing(4)
            self.botoes = {}
            for i, (k, nome) in enumerate(VISTAS):
                b = QtWidgets.QToolButton()
                b.setText(nome)
                b.setObjectName("vista_" + k)
                try:
                    b.setIcon(QtGui.QIcon(PrumoUtil.icone(ICONES[k])))
                except Exception:
                    pass
                b.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
                b.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
                b.setToolTip("Põe a vista %s na folha (1º diedro)." % nome.lower())
                b.clicked.connect(lambda _=False, k=k: self.por(k))
                g.addWidget(b, i // 2, i % 2)
                self.botoes[k] = b
            s2.linha("posicao", grade, "Um clique põe a vista; as ortogonais ficam alinhadas à frontal.")
            s3 = f.secao("Cotas", "comprimento")
            self.btn_cotas = QtWidgets.QPushButton("Cotas gerais (comprimento, altura, profundidade)")
            self.btn_cotas.setObjectName("cotas_gerais")
            self.btn_cotas.clicked.connect(self.por_cotas)
            s3.linha("comprimento", self.btn_cotas, "Medidas totais da peça nas vistas já colocadas.")
            self.status = QtWidgets.QLabel("")
            self.status.setWordWrap(True)
            s3.linha("info", self.status, "")
            self.pecas.mudou.connect(self._atualizar)
            self.folha.currentIndexChanged.connect(self._atualizar)
            self._atualizar()

        def _encher_folhas(self):
            self.folha.clear()
            atual = None
            try:
                mdi = FreeCADGui.getMainWindow().findChild(QtWidgets.QMdiArea).activeSubWindow()
                titulo = mdi.windowTitle() if mdi else ""
            except Exception:
                titulo = ""
            for p in folhas(self.doc):
                self.folha.addItem(p.Label, p.Name)
                if p.Label and p.Label in titulo:
                    atual = p.Name
            self.folha.addItem("Nova folha ABNT (A3)", NOVA)
            if atual:
                self.folha.setCurrentIndex(self.folha.findData(atual))

        def pagina(self, criar=False):
            nome = self.folha.currentData()
            if nome and nome != NOVA:
                return self.doc.getObject(nome)
            if not criar:
                return None
            campos = PrumoFolhas.campos_padrao(self.doc, self.pecas.valores())
            page = PrumoFolhas.nova_folha(self.doc, "A3", PrumoFolhas.NORMA_PADRAO, False, campos, None)
            self._encher_folhas()
            self.folha.setCurrentIndex(self.folha.findData(page.Name))
            return page

        def _atualizar(self, *_):
            objs = self.pecas.valores()
            page = self.pagina()
            ja = vistas_na_folha(page, objs) if page is not None and objs else []
            for k, b in self.botoes.items():
                b.setEnabled(bool(objs))
                b.setChecked(False)
                b.setCheckable(True)
                b.setChecked(k in ja)
            self.btn_cotas.setEnabled(bool(objs) and "Front" in ja)

        def por(self, chave):
            objs = self.pecas.valores()
            if not objs:
                self.status.setText("Escolha a peça primeiro.")
                return None
            self.doc.openTransaction("Vista " + NOMES[chave])
            try:
                page = self.pagina(criar=True)
                v = adicionar_vista(page, objs, chave)
            finally:
                self.doc.commitTransaction()
            self.status.setText("Vista %s na folha %s." % (NOMES[chave].lower(), page.Label))
            self._atualizar()
            _mostrar(page)
            return v

        def por_cotas(self):
            objs = self.pecas.valores()
            page = self.pagina()
            if page is None or not objs:
                return []
            grupo = grupo_da_peca(page, objs)
            vistas = list(grupo.Views) if grupo is not None else []
            if not all(vista_pronta(v) for v in vistas):
                self.status.setText("Calculando as vistas…")
                if not esperar_vistas(vistas, 15.0):
                    self.status.setText("As vistas ainda estão sendo calculadas; tente de novo.")
                    return []
            self.doc.openTransaction("Cotas gerais")
            try:
                c = cotas_gerais(page, objs)
            except ValueError as ex:
                self.status.setText(str(ex))
                c = []
            finally:
                self.doc.commitTransaction()
            if c:
                self.status.setText("%d cota(s) gerais na folha %s." % (len(c), page.Label))
            return c

        def pendencia(self):
            return None

        def pronto_texto(self):
            return "Clique nas vistas; elas entram na folha na hora."

        def getStandardButtons(self):
            b = QtWidgets.QDialogButtonBox.Close
            return b.value if hasattr(b, "value") else int(b)

        def executar(self):
            return None

    def _mostrar(page):
        try:
            QtCore.QTimer.singleShot(0, page.ViewObject.doubleClicked)
        except Exception:
            pass

    class CmdPaletaVistas:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("paleta_vistas.svg"),
                    "MenuText": "Paleta de vistas",
                    "ToolTip": "Um clique põe a vista frontal, superior, lateral, inferior, posterior ou "
                               "isométrica da peça na folha, alinhadas no 1º diedro. Também põe as cotas "
                               "gerais."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            try:
                import TechDraw  # noqa: F401
                import TechDrawGui  # noqa: F401
            except ImportError:
                pass
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx()]
            PainelPaletaVistas(FreeCAD.ActiveDocument, [o for o in sel if PrumoUtil.pecas([o])]).mostrar()


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_PaletaVistas", CmdPaletaVistas())
