# SPDX-License-Identifier: LGPL-2.1-or-later
"""Esboço › Inserir: texto em geometria, importar DXF e matriz ao longo de um caminho.

Faz no Esboço o que antes só a bancada Draft fazia (ShapeString, importar DXF, PathArray), sem precisar
trocar de bancada. Texto e DXF viram geometria do esboço (linhas, arcos e curvas) — no esboço em edição,
no esboço selecionado ou num esboço novo — e o esboço continua onde estava (o Placement não muda).
"""

import glob
import os

import FreeCAD

try:
    import FreeCADGui
except ImportError:  # pragma: no cover
    FreeCADGui = None

import PrumoUtil

FONTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resources", "fonts")
OUTRA_FONTE = "Outro arquivo de fonte…"
ULTIMO_DXF = {"fora_do_plano": 0}
UNIDADES_DXF = (("milímetros (mm)", 1.0), ("centímetros (cm)", 10.0), ("metros (m)", 1000.0),
                ("polegadas (pol)", 25.4))


# ----------------------------------------------------------------------------------- fontes
def fontes():
    """{nome: arquivo}: as Poppins que vêm com o Prumo primeiro, depois as fontes do sistema."""
    res = {}
    for f in sorted(glob.glob(os.path.join(FONTES_DIR, "*.ttf"))):
        res[os.path.splitext(os.path.basename(f))[0].replace("-", " ")] = f
    pastas = []
    if os.name == "nt":
        pastas.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            pastas.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
    else:
        pastas += ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
                   os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", "/System/Library/Fonts"]
    sistema = {}
    for p in pastas:
        for ext in ("ttf", "otf", "TTF", "OTF"):
            for f in glob.glob(os.path.join(p, "**", "*." + ext), recursive=True):
                nome = os.path.splitext(os.path.basename(f))[0]
                sistema.setdefault(nome, f)
    for nome in sorted(sistema, key=str.lower):
        res.setdefault(nome, sistema[nome])
    return res


def fonte_padrao():
    return os.path.join(FONTES_DIR, "Poppins-Regular.ttf")


# ----------------------------------------------------------------------------------- geometria
def _transformar(arestas, x=0.0, y=0.0, angulo=0.0):
    res = []
    for e in arestas:
        e2 = e.copy()
        if angulo:
            e2.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), angulo)
        if x or y:
            e2.translate(FreeCAD.Vector(x, y, 0))
        res.append(e2)
    return res


def arestas_do_texto(texto, fonte=None, altura=10.0, espacamento=0.0, x=0.0, y=0.0, angulo=0.0):
    """Arestas (no plano XY do esboço) do texto escrito na fonte.

    altura = altura da letra maiúscula (como se cota um texto em desenho técnico), em mm.
    espacamento = espaço extra entre as letras, em mm.
    """
    import Part
    texto = (texto or "").replace("\r", "")
    if not texto.strip():
        raise ValueError("Digite o texto.")
    if altura <= 0:
        raise ValueError("A altura das letras tem de ser maior que zero.")
    fonte = fonte or fonte_padrao()
    if not os.path.isfile(fonte):
        raise ValueError("Arquivo de fonte não encontrado: %s" % fonte)
    try:
        ref = Part.makeWireString("H", fonte, 100.0, 0.0)
        bb = Part.Compound([w for ch in ref for w in ch]).BoundBox
        fator = 100.0 / bb.YLength if bb.YLength > 1e-6 else 1.0
    except Exception:
        fator = 1.0
    tamanho = altura * fator
    arestas = []
    for k, linha in enumerate(texto.split("\n")):
        if not linha.strip():
            continue
        try:
            chars = Part.makeWireString(linha, fonte, tamanho, espacamento)
        except Exception as ex:
            raise ValueError("A fonte não pôde ser lida (%s). Escolha outra." % ex)
        desce = -k * altura * 1.6       # linhas de baixo: 1,6 × a altura da letra
        for ch in chars:
            for w in ch:
                for e in w.Edges:
                    e2 = e.copy()
                    e2.translate(FreeCAD.Vector(0, desce, 0))
                    arestas.append(e2)
    if not arestas:
        raise ValueError("Essa fonte não tem desenho para esse texto.")
    return _transformar(arestas, x, y, angulo)


def arestas_do_dxf(caminho, escala=1.0, na_origem=False):
    """Arestas de um arquivo DXF (no plano XY), já na escala pedida. O arquivo é lido num documento
    temporário que é fechado em seguida (nada fica no projeto além da geometria)."""
    import Import
    if not caminho or not os.path.isfile(caminho):
        raise ValueError("Arquivo DXF não encontrado.")
    if escala <= 0:
        raise ValueError("A escala tem de ser maior que zero.")
    atual = FreeCAD.ActiveDocument
    try:
        tmp = FreeCAD.newDocument("PrumoDXF", hidden=True, temp=True)
    except TypeError:  # pragma: no cover
        tmp = FreeCAD.newDocument("PrumoDXF")
    try:
        FreeCAD.setActiveDocument(tmp.Name)   # o leitor põe as camadas no documento ativo
        Import.readDXF(caminho, tmp.Name, True)
        arestas = []
        for o in tmp.Objects:
            sh = getattr(o, "Shape", None)
            if sh is None or sh.isNull() or not o.TypeId.startswith("Part::"):
                continue
            arestas += [e.copy() for e in sh.Edges]
    finally:
        try:
            FreeCAD.closeDocument(tmp.Name)
        except Exception:
            pass
        if atual is not None:
            try:
                FreeCAD.setActiveDocument(atual.Name)
            except Exception:
                pass
    # o esboço é plano: aresta numa cota Z (elevação do DXF) desce para Z = 0; inclinada fica de fora
    planas = []
    for e in arestas:
        bb = e.BoundBox
        if bb.ZLength > 1e-6:
            continue
        if abs(bb.ZMin) > 1e-9:
            e.translate(FreeCAD.Vector(0, 0, -bb.ZMin))
        planas.append(e)
    ULTIMO_DXF["fora_do_plano"] = len(arestas) - len(planas)
    arestas = planas
    if not arestas:
        raise ValueError("O arquivo não tem linhas, arcos nem curvas para trazer.")
    dx = dy = 0.0
    if na_origem:
        import Part
        bb = Part.Compound(arestas).BoundBox
        dx, dy = -bb.XMin * escala, -bb.YMin * escala
    if escala != 1.0:
        m = FreeCAD.Matrix()
        m.scale(escala, escala, escala)
        arestas = [e.transformGeometry(m) for e in arestas]
    if dx or dy:
        for e in arestas:
            e.translate(FreeCAD.Vector(dx, dy, 0))
    return arestas


def geometria(arestas):
    """Arestas → geometria de esboço (retas, arcos, círculos, elipses e B-splines)."""
    import DraftGeomUtils
    import Part
    normal = FreeCAD.Vector(0, 0, 1)
    res = []
    for e in arestas:
        if e.Length < 1e-7:
            continue
        if DraftGeomUtils.geomType(e) == "BezierCurve":
            e = e.Curve.toBSpline(e.FirstParameter, e.LastParameter).toShape()
        try:
            g = DraftGeomUtils.orientEdge(e, normal, make_arc=True)
        except Exception:
            g = None
        if g is None or isinstance(g, Part.Line):
            try:
                g = Part.LineSegment(e.Vertexes[0].Point, e.Vertexes[-1].Point)
            except Exception:
                continue
        res.append(g)
    return res


def inserir(sk, arestas, ligar_pontas=True):
    """Põe as arestas (coordenadas do plano do esboço) no esboço sk; devolve os índices novos.
    ligar_pontas: pontas que se tocam ganham Coincidente (o contorno fica fechado para extrudar)."""
    geos = geometria(arestas)
    if not geos:
        raise ValueError("Nada para pôr no esboço.")
    n0 = sk.GeometryCount
    sk.addGeometry(geos, False)
    novos = list(range(n0, sk.GeometryCount))
    if ligar_pontas:
        _ligar(sk, novos)
    return novos


def _ligar(sk, indices, tol=1e-4):
    import Sketcher
    pts = []
    for i in indices:
        g = sk.Geometry[i]
        if not hasattr(g, "StartPoint") or g.TypeId == "Part::GeomCircle":
            continue
        pts.append((i, 1, g.StartPoint))
        pts.append((i, 2, g.EndPoint))
    ja = set()
    restr = []
    for a in range(len(pts)):
        if pts[a][:2] in ja:
            continue
        for b in range(a + 1, len(pts)):
            if pts[b][0] == pts[a][0] or pts[b][:2] in ja:
                continue
            if (pts[a][2] - pts[b][2]).Length < tol:
                restr.append(Sketcher.Constraint("Coincident", pts[a][0], pts[a][1], pts[b][0], pts[b][1]))
                ja.add(pts[b][:2])
                break
    if restr:
        sk.addConstraint(restr)
    return len(restr)


# ----------------------------------------------------------------------------------- destino
def esboco_em_edicao():
    try:
        import PrumoPainelEsboco
        return PrumoPainelEsboco.esboco_em_edicao()
    except Exception:
        return None


def esboco_selecionado():
    if FreeCADGui is None or not FreeCAD.GuiUp:
        return None
    for o in FreeCADGui.Selection.getSelection():
        if o.TypeId == "Sketcher::SketchObject":
            return o
    return None


def destino():
    """Esboço que recebe o resultado: o em edição, senão o selecionado, senão None (cria um novo)."""
    return esboco_em_edicao() or esboco_selecionado()


def novo_esboco(doc, nome="Esboço"):
    """Esboço novo no plano XY: dentro do corpo ativo, se houver um."""
    corpo = None
    if FreeCADGui is not None and FreeCAD.GuiUp:
        try:
            v = FreeCADGui.ActiveDocument.ActiveView
            corpo = v.getActiveObject("pdbody") if v is not None else None
        except Exception:
            corpo = None
    if corpo is not None:
        sk = corpo.newObject("Sketcher::SketchObject", "Sketch")
        try:
            xy = [f for f in corpo.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
            sk.AttachmentSupport = [(xy, "")]
            sk.MapMode = "FlatFace"
        except Exception:
            pass
    else:
        sk = doc.addObject("Sketcher::SketchObject", "Sketch")
    sk.Label = nome
    return sk


def colocar(doc, arestas, sk=None, nome="Esboço", ligar_pontas=True):
    """Coloca as arestas em sk (ou num esboço novo); devolve (esboço, índices novos)."""
    if sk is None:
        sk = novo_esboco(doc, nome)
    pl = sk.Placement
    novos = inserir(sk, arestas, ligar_pontas)
    if sk.Placement != pl:  # pragma: no cover - garantia: nada aqui mexe no lugar do esboço
        sk.Placement = pl
    return sk, novos


# ----------------------------------------------------------------------------------- matriz
ALINHAMENTOS = (("Acompanha a curva", "Frenet"), ("Mantém a orientação original", None),
                ("Original, girando com a curva", "Original"))


def matriz_no_caminho(base, caminho, quantidade=4, subelementos=None, alinhar="Frenet",
                      inicio=0.0, fim=0.0):
    """Cópias de base distribuídas ao longo de caminho (aresta, arame, esboço ou hélice)."""
    import Draft
    if base is None or caminho is None:
        raise ValueError("Escolha a peça e o caminho.")
    if base == caminho:
        raise ValueError("A peça e o caminho têm de ser objetos diferentes.")
    if quantidade < 1:
        raise ValueError("A quantidade tem de ser pelo menos 1.")
    obj = Draft.make_path_array(base, caminho, count=int(quantidade), subelements=subelementos or None,
                                align=alinhar is not None, align_mode=alinhar or "Original",
                                start_offset=float(inicio), end_offset=float(fim), use_link=True)
    if obj is None:
        raise ValueError("Não foi possível fazer a matriz com esse caminho.")
    obj.Label = "Matriz em caminho"
    try:
        if FreeCAD.GuiUp and base.ViewObject is not None:
            base.ViewObject.Visibility = False
    except Exception:
        pass
    return obj


# ----------------------------------------------------------------------------------- painéis
if FreeCAD.GuiUp:
    try:
        from PySide import QtCore, QtWidgets
    except ImportError:  # pragma: no cover
        from PySide2 import QtCore, QtWidgets
    import PrumoPainel as P

    def _texto_destino(sk):
        if sk is None:
            return "Vai para um esboço novo, no plano XY%s." % (
                " do corpo ativo" if _corpo_ativo() else "")
        return "Vai para o esboço \"%s\"%s." % (sk.Label, " (em edição)" if sk == esboco_em_edicao() else "")

    def _corpo_ativo():
        try:
            v = FreeCADGui.ActiveDocument.ActiveView
            return v.getActiveObject("pdbody") if v is not None else None
        except Exception:
            return None

    class _PainelNoEsboco(P.PainelTarefa):
        """Base de Texto e DXF: o resultado vai para um esboço. Com o esboço em edição o painel de
        tarefas está ocupado pelo Sketcher, então o painel abre numa janela por cima."""

        nome_novo = "Esboço"

        def __init__(self):
            self.alvo = destino()
            super().__init__()

        def arestas(self):
            raise NotImplementedError

        def executar(self):
            doc = FreeCAD.ActiveDocument
            alvo = self.alvo if self.alvo is not None and self.alvo.Document == doc else None
            sk, novos = colocar(doc, self.arestas(), alvo, self.nome_novo)
            doc.recompute()
            self.resultado_esboco, self.novos = sk, novos
            if alvo is None and FreeCAD.GuiUp:
                try:
                    FreeCADGui.Selection.clearSelection()
                    FreeCADGui.Selection.addSelection(sk)
                except Exception:
                    pass
            return [sk]

        def mostrar(self):
            P.estreitar(self.form)
            if FreeCADGui.Control.activeDialog() and esboco_em_edicao() is not None:
                return self.mostrar_em_janela()
            return self._mostrar()

        def mostrar_em_janela(self):
            dlg = QtWidgets.QDialog(FreeCADGui.getMainWindow())
            dlg.setWindowTitle(self.titulo)
            dlg.setObjectName("PrumoJanelaPainel")
            lay = QtWidgets.QVBoxLayout(dlg)
            lay.setContentsMargins(12, 12, 12, 12)
            lay.addWidget(self.form)
            bb = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            bb.button(QtWidgets.QDialogButtonBox.Ok).setText("Inserir")
            bb.button(QtWidgets.QDialogButtonBox.Cancel).setText("Cancelar")
            lay.addWidget(bb)

            def ok():
                if self.accept():
                    dlg.accept()

            def cancelar():
                self.reject()
                dlg.reject()

            bb.accepted.connect(ok)
            bb.rejected.connect(cancelar)
            dlg.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.janela = dlg
            self.aberto = True
            _JANELA["atual"] = dlg
            dlg.show()
            return self

    _JANELA = {}

    class PainelTexto(_PainelNoEsboco):
        titulo = "Texto no esboço"
        ajuda = "Escreva o texto: as letras viram linhas e curvas do esboço (para extrudar, cortar ou gravar)."
        nome_novo = "Texto"

        def montar(self):
            f = self.form
            s = f.secao("Texto", "texto")
            self.texto = QtWidgets.QPlainTextEdit("Prumo 3D")
            self.texto.setMaximumHeight(70)
            s.linha("texto", self.texto, "Uma ou mais linhas.", "Texto")
            self.fonte = QtWidgets.QComboBox()
            self._fontes = fontes()
            for nome, arq in self._fontes.items():
                self.fonte.addItem(nome, arq)
            self.fonte.addItem(OUTRA_FONTE, "")
            ult = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimaFonteTexto", "")
            i = self.fonte.findData(ult) if ult else -1
            self.fonte.setCurrentIndex(i if i >= 0 else max(0, self.fonte.findData(fonte_padrao())))
            if ult and i < 0 and os.path.isfile(ult):
                self.fonte.insertItem(self.fonte.count() - 1, os.path.basename(ult), ult)
                self.fonte.setCurrentIndex(self.fonte.count() - 2)
            self._fonte_anterior = self.fonte.currentIndex()
            self.fonte.currentIndexChanged.connect(self._escolher_fonte)
            s.linha("tipo", self.fonte, "Poppins vem com o Prumo; as fontes instaladas no computador também "
                                       "aparecem.", "Fonte")
            s2 = f.secao("Tamanho e posição", "escala")
            self.altura = s2.linha("altura", P.numero(10.0, 0.1, 10000.0), "Altura da letra maiúscula.",
                                   "Altura das letras")
            self.espaco = s2.linha("folga", P.numero(0.0, -1000.0, 1000.0), "Espaço extra entre as letras "
                                   "(0 = o normal da fonte).", "Espaço entre letras")
            self.x = s2.linha("posicao", P.numero(0.0, -1e6, 1e6), "Ponto de partida do texto (canto de "
                              "baixo, à esquerda), no plano do esboço.", "Posição X")
            self.y = s2.linha("posicao", P.numero(0.0, -1e6, 1e6), "", "Posição Y")
            self.angulo = s2.linha("angulo", P.numero(0.0, -360.0, 360.0, "°"), "Giro do texto em torno do "
                                   "ponto de partida.", "Ângulo")
            s3 = f.secao("Destino", "folha")
            self.destino_txt = s3.texto(_texto_destino(self.alvo))
            self.texto.textChanged.connect(self.atualizar)
            for w in (self.altura, self.espaco):
                w.valueChanged.connect(self.atualizar)

        def _escolher_fonte(self, i):
            if self.fonte.itemText(i) != OUTRA_FONTE:
                self._fonte_anterior = i
                self.atualizar()
                return
            arq, _f = QtWidgets.QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(), "Arquivo de fonte", "",
                                                            "Fontes (*.ttf *.otf *.TTF *.OTF)")
            self.fonte.blockSignals(True)
            if arq:
                self.fonte.insertItem(self.fonte.count() - 1, os.path.basename(arq), arq)
                self.fonte.setCurrentIndex(self.fonte.count() - 2)
                self._fonte_anterior = self.fonte.currentIndex()
            else:
                self.fonte.setCurrentIndex(self._fonte_anterior)
            self.fonte.blockSignals(False)
            self.atualizar()

        def arquivo_fonte(self):
            return self.fonte.currentData() or fonte_padrao()

        def pendencia(self):
            if not hasattr(self, "texto"):
                return None
            if not self.texto.toPlainText().strip():
                return "Digite o texto."
            return None

        def pronto_texto(self):
            return "Pronto: %s" % _texto_destino(self.alvo)

        def arestas(self):
            FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimaFonteTexto", self.arquivo_fonte())
            return arestas_do_texto(self.texto.toPlainText(), self.arquivo_fonte(), self.altura.value(),
                                    self.espaco.value(), self.x.value(), self.y.value(), self.angulo.value())

    class PainelDXF(_PainelNoEsboco):
        titulo = "Importar DXF"
        ajuda = "Traz as linhas, arcos e curvas de um desenho DXF para o esboço."
        nome_novo = "DXF"

        def __init__(self, caminho=""):
            self._caminho_inicial = caminho
            super().__init__()

        def montar(self):
            f = self.form
            s = f.secao("Arquivo", "folha")
            linha = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(linha)
            h.setContentsMargins(0, 0, 0, 0)
            self.caminho = QtWidgets.QLineEdit(self._caminho_inicial)
            self.caminho.setPlaceholderText("Escolha o arquivo .dxf")
            h.addWidget(self.caminho, 1)
            procurar = QtWidgets.QPushButton("Procurar…")
            procurar.clicked.connect(self._procurar)
            h.addWidget(procurar)
            s.linha("folha", linha, "Desenho DXF (AutoCAD, LibreCAD, QCAD, DraftSight…).", "Arquivo")
            s2 = f.secao("Escala", "escala")
            self.unidade = QtWidgets.QComboBox()
            for nome, fator in UNIDADES_DXF:
                self.unidade.addItem(nome, fator)
            s2.linha("escala", self.unidade, "Em que unidade o desenho foi feito: o Prumo trabalha em mm.",
                     "O desenho está em")
            self.escala = s2.linha("escala", P.numero(1.0, 0.0001, 100000.0, "", 4), "Fator extra (1 = "
                                   "tamanho real; 2 = o dobro).", "Escala")
            self.origem = P.marcar("Levar o desenho para a origem do esboço", False)
            s2.widget(self.origem)
            s3 = f.secao("Destino", "folha")
            self.destino_txt = s3.texto(_texto_destino(self.alvo))
            self.caminho.textChanged.connect(self.atualizar)

        def _procurar(self):
            ult = FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).GetString("UltimaPastaDXF", "")
            arq, _f = QtWidgets.QFileDialog.getOpenFileName(FreeCADGui.getMainWindow(), "Importar DXF", ult,
                                                            "Desenho DXF (*.dxf *.DXF)")
            if arq:
                self.caminho.setText(arq)

        def fator(self):
            return (self.unidade.currentData() or 1.0) * self.escala.value()

        def pendencia(self):
            if not hasattr(self, "caminho"):
                return None
            c = self.caminho.text().strip()
            if not c:
                return "Escolha o arquivo DXF."
            if not os.path.isfile(c):
                return "Arquivo não encontrado: %s" % c
            return None

        def pronto_texto(self):
            return "Pronto: %s" % _texto_destino(self.alvo)

        def arestas(self):
            c = self.caminho.text().strip()
            FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimaPastaDXF", os.path.dirname(c))
            return arestas_do_dxf(c, self.fator(), self.origem.isChecked())

    def _filtro_peca(obj, subs):
        if not hasattr(obj, "Shape") or obj.Shape.isNull() or obj.TypeId.startswith("App::Origin"):
            return []
        if obj.TypeId in ("PartDesign::Plane", "PartDesign::Line", "App::Plane", "App::Line"):
            return []
        if not (obj.Shape.Solids or obj.Shape.Faces):     # esboço/arame é caminho, não peça
            return []
        return [(obj.Label, obj)]

    def _filtro_caminho(obj, subs):
        if not hasattr(obj, "Shape") or obj.Shape.isNull() or not obj.Shape.Edges:
            return []
        arestas = tuple(s for s in subs if s.rpartition(".")[2].startswith("Edge"))
        if arestas:
            return [("%s (%s)" % (obj.Label, ", ".join(a.replace("Edge", "aresta ") for a in arestas)),
                     (obj, arestas))]
        return [(obj.Label, (obj, ()))]

    class PainelMatrizCaminho(P.PainelTarefa):
        titulo = "Matriz em caminho"
        previa = True
        ajuda = "Selecione a peça e depois o caminho (aresta, esboço, arame ou hélice)."

        def montar(self):
            f = self.form
            s = f.secao("O que copiar e por onde", "selecao")
            self.base = f.caixa(s, "Peça a copiar", _filtro_peca, minimo=1, maximo=1,
                                dica="O sólido (ou corpo) que vai ser repetido.")
            self.caminho = f.caixa(s, "Caminho", _filtro_caminho, minimo=1, maximo=1,
                                   dica="Esboço, arame, hélice ou arestas de uma peça.")
            self.base.mudou.connect(self._proxima)
            s2 = f.secao("Cópias", "quantidade")
            self.qtd = QtWidgets.QSpinBox()
            self.qtd.setRange(1, 1000)
            self.qtd.setValue(4)
            s2.linha("quantidade", self.qtd, "Total de peças ao longo do caminho (inclui a primeira).",
                     "Quantidade")
            self.alinhar = QtWidgets.QComboBox()
            for nome, modo in ALINHAMENTOS:
                self.alinhar.addItem(nome, modo)
            s2.linha("angulo", self.alinhar, "Acompanha a curva: cada cópia gira para seguir o caminho.",
                     "Orientação")
            self.inicio = s2.linha("ponta", P.numero(0.0, -1e6, 1e6), "Distância do começo do caminho até a "
                                   "primeira cópia.", "Recuo no início")
            self.fim = s2.linha("ponta", P.numero(0.0, -1e6, 1e6), "Distância da última cópia até o fim do "
                                "caminho.", "Recuo no fim")

        def _proxima(self):
            if self.base.pronta() and self.base.ativa and not self.caminho.pronta():
                self.form.ativar_caixa(self.caminho)

        def pendencia(self):
            falta = super().pendencia()
            if falta:
                return falta
            b = self.base.valores()[0]
            c = self.caminho.valores()[0][0]
            if b == c:
                return "A peça e o caminho têm de ser objetos diferentes."
            return None

        def pronto_texto(self):
            return "Pronto: %d cópias de \"%s\"." % (self.qtd.value(), self.base.valores()[0].Label)

        def executar(self):
            b = self.base.valores()[0]
            c, subs = self.caminho.valores()[0]
            return [matriz_no_caminho(b, c, self.qtd.value(), list(subs) or None,
                                      self.alinhar.currentData(), self.inicio.value(), self.fim.value())]

    # ------------------------------------------------------------------------------- comandos
    def _icone_draft(nome):
        return ":/icons/%s.svg" % nome

    class CmdTextoEsboco:
        def GetResources(self):
            return {"Pixmap": _icone_draft("Draft_ShapeString"), "MenuText": "Texto",
                    "ToolTip": "Escreve um texto como geometria do esboço (letras em linhas e curvas), para "
                               "extrudar, cortar ou gravar. Vai para o esboço em edição, o selecionado ou um novo."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelTexto().mostrar()

    class CmdImportarDXF:
        def GetResources(self):
            return {"Pixmap": _icone_draft("Draft_Wire"), "MenuText": "Importar DXF",
                    "ToolTip": "Traz as linhas, arcos e curvas de um arquivo DXF para o esboço em edição, o "
                               "selecionado ou um novo."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelDXF().mostrar()

    class CmdMatrizCaminho:
        def GetResources(self):
            return {"Pixmap": _icone_draft("Draft_PathArray"), "MenuText": "Matriz em caminho",
                    "ToolTip": "Repete uma peça ao longo de um caminho (esboço, arame, hélice ou arestas)."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None and esboco_em_edicao() is None

        def Activated(self):
            PainelMatrizCaminho().mostrar()

    def registrar_comandos():
        try:
            import Draft_rc  # noqa: F401  (ícones do Draft sem ativar a bancada)
        except Exception:
            pass
        FreeCADGui.addCommand("Prumo_TextoEsboco", CmdTextoEsboco())
        FreeCADGui.addCommand("Prumo_ImportarDXF", CmdImportarDXF())
        FreeCADGui.addCommand("Prumo_MatrizCaminho", CmdMatrizCaminho())
