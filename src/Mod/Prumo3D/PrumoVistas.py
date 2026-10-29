# SPDX-License-Identifier: LGPL-2.1-or-later
"""Paleta de vistas e cotas gerais para a aba Desenho.

Um clique põe uma vista (frontal, superior, laterais, inferior, posterior ou isométrica) da peça
numa folha — a folha aberta, uma já existente ou uma folha ABNT nova. As vistas ortogonais entram
no mesmo grupo de projeção (1º diedro), então ficam alinhadas e acompanham a escala da folha.
"Cotas gerais" põe o comprimento, a altura e a profundidade totais da peça nas vistas.
"""

import math

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


# ---------------------------------------------------------------------------- folhas em lote
def pecas_do_lote(objs):
    """[(peça, quantidade)] das peças fabricadas da seleção (montagem, parte, estrutura ou peças), na ordem
    da árvore e sem repetir: peças iguais (o mesmo objeto, vínculos dele ou o mesmo código) viram uma folha
    só. Ficam de fora as compradas, as de referência, os cordões de solda e a tubulação."""
    import PrumoBOM
    r = []
    chaves = {}
    for obj, _sh, comprado in PrumoBOM.itens(objs):
        if comprado:
            continue
        base = PrumoBOM._alvo(obj)
        props = base.PropertiesList
        if ("Perna" in props and "Pecas" in props) or PrumoBOM._e_tubulacao(base):
            continue
        codigo = str(getattr(base, "Codigo", "") or "").strip() if "Codigo" in props else ""
        chave = ("codigo", codigo) if codigo else ("obj", base.Document.Name, base.Name)
        if chave in chaves:
            r[chaves[chave]][1] += 1
            continue
        chaves[chave] = len(r)
        r.append([base, 1])
    return [(o, q) for o, q in r]


def folhas_em_lote(doc, objs, formato="A3", norma=None, arranjo="3vistas_iso", prefixo="", cotas=True,
                   pasta_pdf=None, retrato=False):
    """Uma folha ABNT por peça (vistas no 1º diedro, legenda da peça, folha "k / n"), com as cotas gerais.

    prefixo: número do desenho de cada folha = prefixo + "-01", "-02"… (vazio: o código da peça, se tiver).
    pasta_pdf: também salva o PDF de cada folha nessa pasta. Devolve [(folha, peça, quantidade)]."""
    norma = norma or PrumoFolhas.NORMA_PADRAO
    lista = pecas_do_lote(objs)
    if not lista:
        raise ValueError("Nenhuma peça fabricada na seleção.")
    n = len(lista)
    feitas = []
    for k, (obj, qtd) in enumerate(lista, 1):
        campos = {"folha": "%d / %d" % (k, n)}
        if prefixo:
            campos["numero"] = "%s-%02d" % (prefixo.rstrip("-"), k)
        if qtd > 1:
            titulo = PrumoFolhas.campos_padrao(doc, [obj]).get("titulo") or obj.Label
            campos["titulo"] = "%s (%d×)" % (titulo, qtd)
        page = PrumoFolhas.nova_folha(doc, formato, norma, retrato if formato == "A4" else False, campos,
                                      [obj], arranjo=arranjo)
        page.Label = "Folha %02d - %s" % (k, obj.Label)
        feitas.append((page, obj, qtd))
    doc.recompute()
    if cotas:
        for page, obj, _q in feitas:
            grupo = grupo_da_peca(page, [obj])
            if grupo is None or "Front" not in projecoes(grupo):
                continue
            esperar_vistas(list(grupo.Views), 20.0)
            try:
                cotas_gerais(page, [obj])
            except ValueError:
                pass
    if pasta_pdf:
        import os
        os.makedirs(pasta_pdf, exist_ok=True)
        for page, _o, _q in feitas:
            try:            # a moldura e a legenda só vão para o PDF depois que a folha foi mostrada
                page.ViewObject.show()
            except Exception:
                pass
            salvar_pdf(page, os.path.join(pasta_pdf, os.path.basename(nome_do_arquivo(page, "pdf"))))
    return feitas


# ---------------------------------------------------------------------------- cotas do corte
def e_corte(vista):
    return vista is not None and vista.isDerivedFrom("TechDraw::DrawViewSection")


def _arestas(vista):
    r = []
    i = 0
    while i < 20000:
        try:
            e = vista.getEdgeByIndex(i)
        except Exception:
            break
        if e is None:
            break
        r.append(("Edge%d" % i, e))
        i += 1
    return r


def circulos_do_corte(vista):
    """[(nome da aresta, raio, centro (x, y), círculo inteiro?)] dos furos e arcos da vista, sem repetir o
    mesmo círculo (mesmo centro e raio)."""
    vistos = []
    r = []
    for nome, e in _arestas(vista):
        c = getattr(e, "Curve", None)
        if c is None or not hasattr(c, "Radius") or not hasattr(c, "Center"):
            continue
        cen = FreeCAD.Vector(c.Center)
        rr = float(c.Radius)
        if any(abs(rr - r0) < 1e-4 and (cen - c0).Length < 1e-4 for r0, c0 in vistos):
            continue
        vistos.append((rr, cen))
        inteiro = e.isClosed() or abs((e.LastParameter - e.FirstParameter) - 2 * math.pi) < 1e-6
        r.append((nome, rr, (cen.x, cen.y), inteiro))
    return r


def cotas_do_corte(page, vista, limite_circulos=12):
    """Cotas na vista em corte: largura e altura totais do corte e o diâmetro (ou raio) de cada furo e
    arco cortado. Devolve as cotas criadas."""
    if not e_corte(vista):
        raise ValueError("Escolha uma vista em corte (Corte, na aba Desenho).")
    if not _vertices(vista):
        raise ValueError("A vista em corte ainda está sendo calculada; tente de novo.")
    doc = page.Document
    criadas = []
    ex = _extremos(vista, "x")
    if ex:
        criadas.append(_cota(page, vista, "DistanceX", ex[0], ex[1], "Largura do corte", "baixo"))
    ey = _extremos(vista, "y")
    if ey:
        criadas.append(_cota(page, vista, "DistanceY", ey[0], ey[1], "Altura do corte", "dir"))
    try:
        e = float(vista.getScale())
    except Exception:
        e = float(getattr(vista, "Scale", 1.0) or 1.0)
    for k, (nome, raio, (cx, cy), inteiro) in enumerate(circulos_do_corte(vista)[:limite_circulos]):
        d = doc.addObject("TechDraw::DrawViewDimension", "Cota")
        d.Type = "Diameter" if inteiro else "Radius"
        d.MeasureType = "Projected"
        d.References2D = [(vista, nome)]
        d.Label = ("Ø %s" if inteiro else "R %s") % PrumoUtil.fmt(2 * raio if inteiro else raio, 1)
        page.addView(d)
        ang = math.radians(45 + 30 * k)
        dist = raio * e + 6.0
        d.X, d.Y = cx * e + dist * math.cos(ang), cy * e + dist * math.sin(ang)
        d.recompute()
        criadas.append(d)
    doc.recompute()
    return criadas


# ---------------------------------------------------------------------------- entregar
def pecas_da_folha(page):
    """Peças mostradas nos grupos de vistas da folha (na ordem em que aparecem), sem repetir."""
    r = []
    for v in page.Views:
        if v.isDerivedFrom("TechDraw::DrawProjGroup") or v.TypeId == "TechDraw::DrawViewPart":
            for o in v.Source:
                if all(o is not x for x in r):
                    r.append(o)
    return r


def nome_do_arquivo(page, extensao):
    """<pasta do projeto>/<nº do desenho ou nome da folha>.<ext>; sem projeto salvo, a pasta pessoal."""
    import os
    import re
    doc = page.Document
    pasta = os.path.dirname(doc.FileName) if doc.FileName else os.path.expanduser("~")
    numero = ""
    try:
        numero = dict(page.Template.EditableTexts).get("numero", "").strip()
    except Exception:
        pass
    base = numero or page.Label or "Folha"
    if doc.FileName and not numero:
        base = "%s - %s" % (os.path.splitext(os.path.basename(doc.FileName))[0], base)
    base = re.sub(r'[<>:"/\\|?*]+', "-", base).strip() or "Folha"
    return os.path.join(pasta, base + "." + extensao)


def salvar_pdf(page, caminho=None):
    import TechDrawGui
    caminho = caminho or nome_do_arquivo(page, "pdf")
    TechDrawGui.exportPageAsPdf(page, caminho)
    return caminho


def exportar_dxf(page, caminho=None):
    import TechDraw
    caminho = caminho or nome_do_arquivo(page, "dxf")
    TechDraw.writeDXFPage(page, caminho)
    return caminho


def folha_ativa():
    """A folha da janela ativa (ou None)."""
    try:
        import FreeCADGui as G
        from PySide import QtWidgets as W
        area = G.getMainWindow().findChild(W.QMdiArea)
        sub = area.activeSubWindow() if area is not None else None
        if sub is None:
            return None
        titulo = sub.windowTitle()
        doc = FreeCAD.ActiveDocument
        for p in folhas(doc):
            if p.Label and (titulo.startswith(p.Label) or (" : " + p.Label) in titulo or p.Label in titulo):
                return p
    except Exception:
        pass
    return None


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


if P is not None:
    class PainelFolhasLote(P.PainelTarefa):
        titulo = "Folhas em lote"
        ajuda = ("Escolha a montagem, a estrutura ou as peças: o Prumo faz uma folha ABNT para cada peça "
                 "fabricada, com as vistas, a legenda da peça e as cotas gerais. Peças iguais saem numa folha só.")

        def __init__(self, doc=None, objs=None):
            self.doc = doc or FreeCAD.ActiveDocument
            self._objs_iniciais = list(objs or [])
            self.feitas = []
            super().__init__()

        def montar(self):
            f = self.form
            s0 = f.secao("Peças", "selecao")
            self.pecas = f.caixa(s0, "Montagem, estrutura ou peças", _filtro_pecas, minimo=1,
                                 dica="Uma montagem inteira, uma parte ou várias peças (Ctrl + clique).")
            for o in self._objs_iniciais:
                self.pecas.aceitar(o)
            self.resumo = QtWidgets.QLabel("")
            self.resumo.setWordWrap(True)
            s0.linha("info", self.resumo, "")
            s1 = f.secao("Folhas", "folha")
            self.formato = s1.linha("folha", P.lista(PrumoFolhas.FORMATOS, PrumoFolhas.FREECAD_PARAM().GetString(
                "FolhaFormato", PrumoFolhas.FORMATO_PADRAO)), "A0 a A4.", "Formato")
            self.arranjo = QtWidgets.QComboBox()
            for k, (rot, _p, _i) in PrumoFolhas.ARRANJOS.items():
                self.arranjo.addItem(rot, k)
            i = self.arranjo.findData(PrumoFolhas.FREECAD_PARAM().GetString("FolhaArranjo",
                                                                            PrumoFolhas.ARRANJO_PADRAO))
            self.arranjo.setCurrentIndex(max(i, 0))
            s1.linha("posicao", self.arranjo, "Quais vistas entram em cada folha (1º diedro).", "Vistas")
            self.prefixo = s1.linha("quantidade", QtWidgets.QLineEdit(""), "Número do desenho de cada folha: "
                                    "prefixo-01, prefixo-02… Vazio: o código da peça (Propriedades da peça).",
                                    "Prefixo do nº")
            self.cotas = s1.linha("comprimento", P.marcar("Cotas gerais em cada folha", True), "")
            self.pdf = s1.linha("folha", P.marcar("Salvar o PDF de cada folha na pasta do projeto", False), "")
            self.pecas.mudou.connect(self._resumir)
            self._resumir()

        def _resumir(self, *_a):
            try:
                lista = pecas_do_lote(self.pecas.valores())
            except Exception:
                lista = []
            if not lista:
                self.resumo.setText("")
                return
            txt = ", ".join("%s%s" % (o.Label, " (%d×)" % q if q > 1 else "") for o, q in lista[:8])
            if len(lista) > 8:
                txt += "…"
            self.resumo.setText("%d folha(s): %s" % (len(lista), txt))

        def pendencia(self):
            if not self.pecas.valores():
                return "Selecione a montagem, a estrutura ou as peças."
            if not pecas_do_lote(self.pecas.valores()):
                return "Nenhuma peça fabricada na seleção (compradas e de referência ficam de fora)."
            return None

        def pronto_texto(self):
            return "OK cria %d folha(s)." % len(pecas_do_lote(self.pecas.valores()))

        def executar(self):
            import os
            formato = self.formato.currentText()
            PrumoFolhas.FREECAD_PARAM().SetString("FolhaFormato", formato)
            PrumoFolhas.FREECAD_PARAM().SetString("FolhaArranjo", self.arranjo.currentData())
            pasta = None
            if self.pdf.isChecked():
                base = os.path.dirname(self.doc.FileName) if self.doc.FileName else os.path.expanduser("~")
                pasta = os.path.join(base, "Folhas")
            self.feitas = folhas_em_lote(self.doc, self.pecas.valores(), formato,
                                         PrumoFolhas.FREECAD_PARAM().GetString("FolhaNorma",
                                                                               PrumoFolhas.NORMA_PADRAO),
                                         self.arranjo.currentData(), self.prefixo.text().strip(),
                                         self.cotas.isChecked(), pasta, formato == "A4")
            if self.feitas:
                _mostrar(self.feitas[0][0])
            FreeCAD.Console.PrintMessage("Prumo: %d folha(s) criadas%s.\n" % (
                len(self.feitas), (" e salvas em PDF em " + pasta) if pasta else ""))
            return [p for p, _o, _q in self.feitas]

    class CmdFolhasLote:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"), "MenuText": "Folhas em lote",
                    "ToolTip": "Uma folha ABNT por peça da montagem ou da estrutura, com as vistas, a legenda "
                               "da peça e as cotas gerais (e o PDF de cada uma, se quiser)."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            try:
                import TechDraw  # noqa: F401
                import TechDrawGui  # noqa: F401
            except ImportError:
                pass
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx()]
            PainelFolhasLote(FreeCAD.ActiveDocument, [o for o in sel if PrumoUtil.pecas([o])]).mostrar()

    class CmdCotasCorte:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("cotas.svg"), "MenuText": "Cotas do corte",
                    "ToolTip": "Na vista em corte selecionada (ou na única da folha): largura e altura do corte "
                               "e o diâmetro de cada furo cortado."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and bool(folhas(FreeCAD.ActiveDocument))

        def Activated(self):
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx()]
            cortes = [o for o in sel if e_corte(o)]
            page = None
            if cortes:
                page = cortes[0].findParentPage() if hasattr(cortes[0], "findParentPage") else None
            if page is None:
                page = _folha_ou_aviso()
                if page is None:
                    return None
            if not cortes:
                cortes = [v for v in page.Views if e_corte(v)]
            if not cortes:
                r = QtWidgets.QMessageBox.question(
                    FreeCADGui.getMainWindow(), "Cotas do corte",
                    "Esta folha ainda não tem vista em corte.\n\nSelecione a vista e clique em Corte "
                    "(aba Desenho) para criar uma. Criar o corte agora?")
                if r == QtWidgets.QMessageBox.Yes:
                    try:
                        FreeCADGui.runCommand("TechDraw_SectionView", 0)
                    except Exception:
                        pass
                return None
            doc = page.Document
            doc.openTransaction("Cotas do corte")
            try:
                c = cotas_do_corte(page, cortes[0])
            except ValueError as ex:
                doc.abortTransaction()
                QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Cotas do corte", str(ex))
                return None
            doc.commitTransaction()
            return c

    def _folha_ou_aviso():
        page = folha_ativa()
        if page is None:
            fs = folhas(FreeCAD.ActiveDocument)
            if len(fs) == 1:
                page = fs[0]
        if page is None:
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Desenho",
                                              "Abra a folha que quer usar (clique na aba dela, embaixo da tela).")
        return page

    def _avisar_arquivo(titulo, caminho):
        import os
        mb = QtWidgets.QMessageBox(FreeCADGui.getMainWindow())
        mb.setWindowTitle(titulo)
        mb.setText("%s salvo em:\n%s" % (titulo.split()[-1], caminho))
        abrir = mb.addButton("Abrir a pasta", QtWidgets.QMessageBox.ActionRole)
        mb.addButton("OK", QtWidgets.QMessageBox.AcceptRole)
        mb.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        mb.buttonClicked.connect(lambda b: b is abrir and QtGui.QDesktopServices.openUrl(
            QtCore.QUrl.fromLocalFile(os.path.dirname(caminho))))
        mb.show()
        return mb

    class CmdAbrirFolha:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"), "MenuText": "Abrir folha",
                    "ToolTip": "Abre uma das folhas de desenho do projeto."}

        def IsActive(self):
            return bool(folhas(FreeCAD.ActiveDocument))

        def Activated(self):
            fs = folhas(FreeCAD.ActiveDocument)
            if len(fs) == 1:
                _mostrar(fs[0])
                return
            m = QtWidgets.QMenu(FreeCADGui.getMainWindow())
            for p in fs:
                a = m.addAction(p.Label)
                a.triggered.connect(lambda _=False, p=p: _mostrar(p))
            m.popup(QtGui.QCursor.pos())
            self._menu = m

    class CmdCotasGerais:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("cotas.svg"), "MenuText": "Cotas gerais",
                    "ToolTip": "Põe o comprimento, a altura e a profundidade totais da peça nas vistas da "
                               "folha aberta."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and bool(folhas(FreeCAD.ActiveDocument))

        def Activated(self):
            page = _folha_ou_aviso()
            if page is None:
                return None
            pecas = pecas_da_folha(page)
            grupos = [v for v in page.Views if v.isDerivedFrom("TechDraw::DrawProjGroup")]
            if not grupos:
                # o erro já traz o conserto: abrir a paleta com a peça escolhida
                r = QtWidgets.QMessageBox.question(
                    FreeCADGui.getMainWindow(), "Cotas gerais",
                    "As cotas gerais vão na vista frontal, e esta folha ainda não tem uma.\n\n"
                    "Abrir a Paleta de vistas para pôr a frontal?")
                if r == QtWidgets.QMessageBox.Yes:
                    PainelPaletaVistas(FreeCAD.ActiveDocument, pecas).mostrar()
                return None
            alvo = _fontes(grupos[0].Source)
            sel = [s.Object for s in FreeCADGui.Selection.getSelectionEx()]
            for g in grupos:
                if any(o is g or o in list(g.Views) for o in sel):
                    alvo = _fontes(g.Source)
            vistas = list(grupo_da_peca(page, alvo).Views)
            esperar_vistas(vistas, 15.0)
            doc = page.Document
            doc.openTransaction("Cotas gerais")
            try:
                c = cotas_gerais(page, alvo)
            except ValueError as ex:
                doc.abortTransaction()
                QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Cotas gerais", str(ex))
                return None
            doc.commitTransaction()
            return c

    class CmdSalvarPDF:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("salvar_pdf.svg"), "MenuText": "Salvar PDF",
                    "ToolTip": "Salva a folha aberta em PDF na pasta do projeto, com o número do desenho no "
                               "nome do arquivo."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and bool(folhas(FreeCAD.ActiveDocument))

        def Activated(self):
            page = _folha_ou_aviso()
            if page is None:
                return None
            caminho, _f = QtWidgets.QFileDialog.getSaveFileName(
                FreeCADGui.getMainWindow(), "Salvar PDF", nome_do_arquivo(page, "pdf"), "PDF (*.pdf)")
            if not caminho:
                return None
            salvar_pdf(page, caminho)
            return _avisar_arquivo("Salvar PDF", caminho)

    class CmdExportarDXF:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("exportar_dxf.svg"), "MenuText": "Exportar DXF",
                    "ToolTip": "Salva a folha aberta em DXF (para CAD 2D, corte a laser e plasma)."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and bool(folhas(FreeCAD.ActiveDocument))

        def Activated(self):
            page = _folha_ou_aviso()
            if page is None:
                return None
            caminho, _f = QtWidgets.QFileDialog.getSaveFileName(
                FreeCADGui.getMainWindow(), "Exportar DXF", nome_do_arquivo(page, "dxf"), "DXF (*.dxf)")
            if not caminho:
                return None
            exportar_dxf(page, caminho)
            return _avisar_arquivo("Exportar DXF", caminho)


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_PaletaVistas", CmdPaletaVistas())
        FreeCADGui.addCommand("Prumo_AbrirFolha", CmdAbrirFolha())
        FreeCADGui.addCommand("Prumo_CotasGerais", CmdCotasGerais())
        FreeCADGui.addCommand("Prumo_SalvarPDF", CmdSalvarPDF())
        FreeCADGui.addCommand("Prumo_ExportarDXF", CmdExportarDXF())
        FreeCADGui.addCommand("Prumo_FolhasLote", CmdFolhasLote())
        FreeCADGui.addCommand("Prumo_CotasCorte", CmdCotasCorte())
