# SPDX-License-Identifier: LGPL-2.1-or-later
"""Barra de varredura: uma barra (redonda ou quadrada, maciça ou tubo) ao longo de todas as linhas de um esboço.

Como a "Barra de varredura" do ZW3D: escolhe-se o esboço (comum ou Esboço 3D) e cada linha vira uma barra; as
barras que se cruzam ou se encontram são unidas num sólido só (dá para fazer grade, xadrez, chapa expandida,
gradil). Opções:

- perfil redondo (diâmetro externo e interno; interno 0 = barra maciça) ou quadrado (lado e espessura da parede;
  espessura 0 = barra maciça);
- unir as barras num sólido só (nos encontros, a redonda ganha uma esfera e a quadrada se prolonga meio lado, para
  o encontro ficar fechado);
- raio nos cantos: os cantos das linhas retas viram curvas desse raio (como barra dobrada).

No esboço comum, a barra quadrada fica com duas faces paralelas ao plano do esboço.
"""

import math

import FreeCAD

import PrumoUtil

PERFIS = ("Redondo", "Quadrado")
TOL = 1e-6
TOL_NO = 1e-4


# ============================================================================ lógica (sem interface)
def _normal_do_plano(caminho):
    """Normal do plano de um esboço comum (global) ou None (Esboço 3D, outras formas)."""
    if caminho is None or caminho.TypeId != "Sketcher::SketchObject":
        return None
    try:
        pl = caminho.getGlobalPlacement()
    except Exception:
        pl = caminho.Placement
    n = pl.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    n.normalize()
    return n


def arestas_do_caminho(caminho):
    """Arestas (globais) do caminho: esboço comum (sem as linhas de construção), Esboço 3D (idem) ou qualquer
    objeto com arestas."""
    if caminho is None:
        return []
    try:
        import PrumoEsboco3D
        if PrumoEsboco3D.e_esboco3d(caminho):
            sh = PrumoEsboco3D.forma_obj(caminho, 0.0)
            pl = caminho.getGlobalPlacement() if hasattr(caminho, "getGlobalPlacement") else caminho.Placement
            sh = sh.copy()
            sh.Placement = pl
            return [e for e in sh.Edges if e.Length > TOL]
    except Exception:
        pass
    sh = PrumoUtil.forma_global(caminho)
    return [e for e in sh.Edges if e.Length > TOL]


def _reta(e):
    import Part
    return isinstance(e.Curve, (Part.Line, Part.LineSegment)) or e.Curve.TypeId == "Part::GeomLine"


def _chave(p):
    return (round(p.x / TOL_NO), round(p.y / TOL_NO), round(p.z / TOL_NO))


def arredondar_cantos(arestas, raio):
    """As linhas retas encadeadas ganham arcos de raio `raio` nos cantos (as curvas ficam como estão)."""
    if raio <= 0:
        return list(arestas)
    import PrumoEsboco3D
    retas = [e for e in arestas if _reta(e)]
    outras = [e for e in arestas if not _reta(e)]
    pontas = {}
    for k, e in enumerate(retas):
        for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
            pontas.setdefault(_chave(p), []).append(k)
    usadas = set()
    novas = []

    def outra_ponta(k, p):
        a, b = retas[k].Vertexes[0].Point, retas[k].Vertexes[-1].Point
        return b if _chave(a) == _chave(p) else a

    def caminhar(k0, p0):
        """Segue a cadeia a partir da ponta p0 da reta k0 enquanto os nós tiverem só duas retas."""
        pts = [p0]
        k, p = k0, p0
        while True:
            usadas.add(k)
            q = outra_ponta(k, p)
            pts.append(q)
            viz = [j for j in pontas[_chave(q)] if j != k]
            if len(pontas[_chave(q)]) != 2 or not viz or viz[0] in usadas:
                fechado = len(pontas[_chave(q)]) == 2 and viz and viz[0] == k0 and _chave(q) == _chave(p0)
                return pts, bool(fechado)
            k, p = viz[0], q

    # começa pelas pontas que não são meio de cadeia (pontas soltas, cruzamentos), depois os laços
    for k, e in enumerate(retas):
        if k in usadas:
            continue
        for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
            if len(pontas[_chave(p)]) != 2 and k not in usadas:
                pts, fechado = caminhar(k, p)
                novas += PrumoEsboco3D.arestas_do_trecho(pts, False, raio)
    for k, e in enumerate(retas):
        if k not in usadas:
            pts, fechado = caminhar(k, e.Vertexes[0].Point)
            if fechado and len(pts) > 2:
                pts = pts[:-1]
            novas += PrumoEsboco3D.arestas_do_trecho(pts, fechado, raio)
    return novas + outras


def _referencia(d, normal):
    """Direção 'para cima' da barra quadrada, perpendicular à direção d."""
    for cand in ([normal] if normal is not None else []) + [FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(1, 0, 0)]:
        up = cand - d * cand.dot(d)
        if up.Length > 1e-6:
            up.normalize()
            return up
    return FreeCAD.Vector(0, 1, 0)


def _barra_reta(a, b, perfil, medida, ext_a, ext_b, normal):
    import Part
    d = b - a
    comp = d.Length
    d.normalize()
    ini = a - d * ext_a
    total = comp + ext_a + ext_b
    if perfil == "Redondo":
        return Part.makeCylinder(medida / 2.0, total, ini, d)
    up = _referencia(d, normal)
    lado = up.cross(d)                     # (lado, up, d) forma um sistema de mão direita
    caixa = Part.makeBox(medida, medida, total)
    m = FreeCAD.Matrix(lado.x, up.x, d.x, 0, lado.y, up.y, d.y, 0, lado.z, up.z, d.z, 0, 0, 0, 0, 1)
    caixa.Placement = FreeCAD.Placement(ini - lado * (medida / 2.0) - up * (medida / 2.0),
                                        FreeCAD.Rotation(m))
    return caixa


def _barra_curva(e, perfil, medida, normal):
    import Part
    t0 = e.tangentAt(e.FirstParameter)
    t0.normalize()
    p0 = e.valueAt(e.FirstParameter)
    # numa curva plana (arco), a barra quadrada acompanha o plano do arco
    binormal = FreeCAD.Vector(e.Curve.Axis) if hasattr(e.Curve, "Axis") else normal
    if perfil == "Redondo":
        perfil_w = Part.Wire([Part.makeCircle(medida / 2.0, p0, t0)])
    else:
        up = _referencia(t0, binormal)
        lado = up.cross(t0)
        h = medida / 2.0
        cantos = [p0 + lado * sx * h + up * sy * h for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        perfil_w = Part.makePolygon(cantos + [cantos[0]])
    ps = Part.BRepOffsetAPI.MakePipeShell(Part.Wire([e]))
    if perfil != "Redondo":
        try:
            ps.setBiNormalMode(binormal if binormal is not None else FreeCAD.Vector(0, 0, 1))
        except Exception:
            pass
    ps.add(perfil_w, False, False)
    ps.build()
    ps.makeSolid()
    return ps.shape()


def montar(arestas, perfil="Redondo", medida=10.0, interna=0.0, unir=True, normal=None):
    """Sólido da barra ao longo das arestas. medida: diâmetro (redondo) ou lado (quadrado); interna: diâmetro
    interno ou lado interno (0 = maciça). Devolve (forma, comprimento total do caminho)."""
    import Part
    if not arestas:
        raise ValueError("O caminho não tem linhas.")
    if medida <= 0:
        raise ValueError("A medida da barra tem de ser maior que zero.")
    if interna >= medida:
        raise ValueError("A medida interna tem de ser menor que a externa.")
    grau = {}
    for e in arestas:
        for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
            grau[_chave(p)] = grau.get(_chave(p), 0) + 1
    # pontos de passagem: encontro que não é ponta solta (cruzamento no meio de uma linha não precisa)

    def solidos(m):
        r = []
        ext = (m / 2.0) if (unir and perfil == "Quadrado") else 0.0
        for e in arestas:
            a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if _reta(e):
                ea = ext if grau[_chave(a)] > 1 else 0.0
                eb = ext if grau[_chave(b)] > 1 else 0.0
                r.append(_barra_reta(a, b, perfil, m, ea, eb, normal))
            else:
                r.append(_barra_curva(e, perfil, m, normal))
        if unir and perfil == "Redondo":
            vistos = set()
            for e in arestas:
                for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
                    k = _chave(p)
                    if grau[k] > 1 and k not in vistos:
                        vistos.add(k)
                        r.append(Part.makeSphere(m / 2.0, p))
        return r

    ext = solidos(medida)
    if unir:
        forma = ext[0].fuse(ext[1:]) if len(ext) > 1 else ext[0]
        if interna > 0:
            inn = solidos(interna)
            vazio = inn[0].fuse(inn[1:]) if len(inn) > 1 else inn[0]
            forma = forma.cut(vazio)
        try:
            forma = forma.removeSplitter()
        except Exception:
            pass
    else:
        if interna > 0:
            ext = [s.cut(i) for s, i in zip(ext, solidos(interna))]
        forma = Part.makeCompound(ext)
    return forma, sum(e.Length for e in arestas)


class BarraVarredura:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, dica, valor=None, grupo="Barra"):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
        add("App::PropertyLinkGlobal", "Caminho", "Esboço (ou Esboço 3D) com as linhas da barra")
        if "Perfil" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Perfil", "Barra", "Seção da barra")
            obj.Perfil = list(PERFIS)
            obj.Perfil = "Redondo"
        add("App::PropertyLength", "Diametro", "Barra redonda: diâmetro externo", 10.0)
        add("App::PropertyLength", "DiametroInterno", "Barra redonda: diâmetro interno (0 = maciça)", 0.0)
        add("App::PropertyLength", "Lado", "Barra quadrada: lado", 10.0)
        add("App::PropertyLength", "Parede", "Barra quadrada: espessura da parede (0 = maciça)", 0.0)
        add("App::PropertyBool", "Unir", "Une as barras num sólido só (encontros fechados)", True)
        add("App::PropertyLength", "RaioCantos", "Raio nos cantos das linhas retas (0 = canto vivo)", 0.0)
        add("App::PropertyLength", "Comprimento", "Comprimento total das barras (pelo eixo)", 0.0, "Resultado")
        obj.setEditorMode("Comprimento", 1)

    def onDocumentRestored(self, obj):
        self._props(obj)

    def execute(self, obj):
        import Part
        arestas = arredondar_cantos(arestas_do_caminho(obj.Caminho), float(obj.RaioCantos))
        if obj.Perfil == "Quadrado":
            medida = float(obj.Lado)
            interna = medida - 2.0 * float(obj.Parede) if float(obj.Parede) > 0 else 0.0
        else:
            medida, interna = float(obj.Diametro), float(obj.DiametroInterno)
        try:
            forma, comp = montar(arestas, obj.Perfil, medida, interna, bool(obj.Unir), _normal_do_plano(obj.Caminho))
        except ValueError as ex:
            FreeCAD.Console.PrintWarning("Prumo: barra de varredura: %s\n" % ex)
            obj.Shape = Part.Shape()
            return
        obj.Shape = forma
        obj.Comprimento = comp

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(caminho, perfil="Redondo", medida=10.0, interna_ou_parede=0.0, unir=True, raio=0.0, doc=None):
    doc = doc or caminho.Document
    obj = doc.addObject("Part::FeaturePython", "BarraVarredura")
    BarraVarredura(obj)
    obj.Label = "Barra de varredura"
    obj.Caminho = caminho
    obj.Perfil = perfil
    if perfil == "Quadrado":
        obj.Lado, obj.Parede = medida, interna_ou_parede
    else:
        obj.Diametro, obj.DiametroInterno = medida, interna_ou_parede
    obj.Unir = unir
    obj.RaioCantos = raio
    if FreeCAD.GuiUp:
        VPBarraVarredura(obj.ViewObject)
        try:
            caminho.ViewObject.Visibility = False
        except Exception:
            pass
    doc.recompute()
    return obj


def e_barra(obj):
    return obj is not None and isinstance(getattr(obj, "Proxy", None), BarraVarredura)


# ============================================================================ interface
try:
    import FreeCADGui
    from PySide import QtWidgets
    import PrumoPainel as P
except ImportError:
    FreeCADGui = None
    P = None


def _filtro_caminho(obj, subs):
    try:
        if e_barra(obj):
            return []
        if obj.TypeId == "Sketcher::SketchObject" or arestas_do_caminho(obj):
            if not getattr(obj, "Shape", None) or not obj.Shape.Solids:
                return [(obj.Label, obj)]
    except Exception:
        pass
    return []


if P is not None:
    class VPBarraVarredura:
        def __init__(self, vobj):
            vobj.Proxy = self

        def attach(self, vobj):
            self.Object = vobj.Object

        def getIcon(self):
            return "PartDesign_AdditivePipe"

        def claimChildren(self):
            c = getattr(self.Object, "Caminho", None)
            return [c] if c is not None else []

        def doubleClicked(self, vobj):
            PainelBarra().editar_objeto(vobj.Object).mostrar()
            return True

        def dumps(self):
            return None

        def loads(self, state):
            return None

    class PainelBarra(P.PainelTarefa):
        titulo = "Barra de varredura"
        ajuda = ("Escolha o esboço: cada linha vira uma barra, e as que se cruzam ou se encontram ficam unidas "
                 "(grade, xadrez, chapa expandida). Perfil redondo ou quadrado, maciço ou tubo.")

        def montar(self):
            f = self.form
            s0 = f.secao("Caminho", "selecao")
            self.caminho = f.caixa(s0, "Esboço", _filtro_caminho, minimo=1, maximo=1,
                                   dica="Esboço comum ou Esboço 3D (as linhas de construção ficam de fora).")
            s1 = f.secao("Perfil", "tipo")
            self.perfil = QtWidgets.QComboBox()
            for p_ in PERFIS:
                self.perfil.addItem(p_, p_)
            s1.linha("tipo", self.perfil, "Seção da barra.", "Perfil")
            self.medida = self._mm(10.0)
            self.lb_medida = s1.linha("espessura", self.medida, "Diâmetro externo da barra.", "Diâmetro")
            self.interna = self._mm(0.0)
            s1.linha("espessura", self.interna, "Diâmetro interno (tubo); 0 = barra maciça.", "Interno")
            s2 = f.secao("Opções", "info")
            self.unir = s2.linha("posicao", P.marcar("Unir as barras (encontros fechados)", True), "")
            self.raio = self._mm(0.0)
            s2.linha("angulo", self.raio, "Os cantos das linhas retas viram curvas desse raio (0 = canto vivo).",
                     "Raio nos cantos")
            self.perfil.currentIndexChanged.connect(self._perfil)
            self._perfil()

        def _mm(self, v):
            w = QtWidgets.QDoubleSpinBox()
            w.setRange(0.0, 100000.0)
            w.setDecimals(2)
            w.setSuffix(" mm")
            w.setValue(v)
            try:
                w.setLocale(P.LOCALE)
            except Exception:
                pass
            return w

        def _perfil(self, *_a):
            quadrado = self.perfil.currentData() == "Quadrado"
            try:
                rotulos = self.form.findChildren(QtWidgets.QLabel)
                for lb in rotulos:
                    if lb.text() in ("Diâmetro", "Lado"):
                        lb.setText("Lado" if quadrado else "Diâmetro")
                    elif lb.text() in ("Interno", "Parede"):
                        lb.setText("Parede" if quadrado else "Interno")
            except Exception:
                pass
            self.medida.setToolTip("Lado da barra quadrada." if quadrado else "Diâmetro externo da barra.")
            self.interna.setToolTip("Espessura da parede (tubo quadrado); 0 = barra maciça." if quadrado
                                    else "Diâmetro interno (tubo); 0 = barra maciça.")

        def pendencia(self):
            if not self.caminho.valores():
                return "Escolha o esboço com as linhas da barra."
            if self.medida.value() <= 0:
                return "A medida da barra tem de ser maior que zero."
            if self.perfil.currentData() == "Quadrado":
                if self.interna.value() > 0 and 2 * self.interna.value() >= self.medida.value():
                    return "A parede é grossa demais para esse lado."
            elif self.interna.value() >= self.medida.value():
                return "O diâmetro interno tem de ser menor que o externo."
            return None

        def pronto_texto(self):
            return "OK cria a barra ao longo de todas as linhas do esboço."

        def carregar(self, obj):
            self.caminho.aceitar(obj.Caminho)
            self.perfil.setCurrentIndex(max(0, self.perfil.findData(obj.Perfil)))
            if obj.Perfil == "Quadrado":
                self.medida.setValue(float(obj.Lado))
                self.interna.setValue(float(obj.Parede))
            else:
                self.medida.setValue(float(obj.Diametro))
                self.interna.setValue(float(obj.DiametroInterno))
            self.unir.setChecked(bool(obj.Unir))
            self.raio.setValue(float(obj.RaioCantos))

        def props_edicao(self):
            q = self.perfil.currentData() == "Quadrado"
            d = {"Caminho": self.caminho.valores()[0], "Perfil": self.perfil.currentData(),
                 "Unir": self.unir.isChecked(), "RaioCantos": self.raio.value()}
            if q:
                d.update({"Lado": self.medida.value(), "Parede": self.interna.value()})
            else:
                d.update({"Diametro": self.medida.value(), "DiametroInterno": self.interna.value()})
            return d

        def executar(self):
            obj = criar(self.caminho.valores()[0], self.perfil.currentData(), self.medida.value(),
                        self.interna.value(), self.unir.isChecked(), self.raio.value())
            return [obj]

    class CmdBarraVarredura:
        def GetResources(self):
            return {"Pixmap": "PartDesign_AdditivePipe", "MenuText": "Barra de varredura",
                    "ToolTip": "Barra redonda ou quadrada (maciça ou tubo) ao longo de todas as linhas de um esboço; "
                               "as que se cruzam ficam unidas: grade, xadrez, chapa expandida, gradil."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelBarra().mostrar()


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_BarraVarredura", CmdBarraVarredura())
