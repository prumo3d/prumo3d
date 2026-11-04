# SPDX-License-Identifier: LGPL-2.1-or-later
"""Barra de varredura: uma barra (redonda ou quadrada, maciça ou tubo) ao longo de todas as linhas de um esboço.

Como a "Barra de varredura" do ZW3D: escolhe-se o esboço (comum ou Esboço 3D) e cada linha vira uma barra; as
barras que se cruzam ou se encontram são unidas num sólido só (dá para fazer grade, xadrez, chapa expandida,
gradil). Opções:

- perfil redondo (diâmetro externo e interno; interno 0 = barra maciça), quadrado, sextavado (entre faces), oval
  (largura e altura) ou quadrifólio (quatro lóbulos), com espessura de parede (0 = barra maciça);
- unir as barras num sólido só (nos encontros, a redonda ganha uma esfera e a quadrada se prolonga meio lado, para
  o encontro ficar fechado);
- raio nos cantos: os cantos das linhas retas viram curvas desse raio (como barra dobrada).

No esboço comum, a barra quadrada fica com duas faces paralelas ao plano do esboço.
"""

import math

import FreeCAD

import PrumoUtil

PERFIS = ("Redondo", "Quadrado", "Sextavado", "Oval", "Quadrifólio")
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
    """Direção 'para cima' da barra (perfil não redondo), perpendicular à direção d."""
    for cand in ([normal] if normal is not None else []) + [FreeCAD.Vector(0, 0, 1), FreeCAD.Vector(1, 0, 0)]:
        up = cand - d * cand.dot(d)
        if up.Length > 1e-6:
            up.normalize()
            return up
    return FreeCAD.Vector(0, 1, 0)


def secao_local(perfil, medida, altura=0.0):
    """Face da seção no plano XY local (x = lado, y = 'para cima'), centrada na origem.

    Redondo: diâmetro; Quadrado: lado; Sextavado: distância entre faces (chave), com duas faces paralelas ao
    plano do esboço; Oval: largura × altura (altura 0 = 60 % da largura); Quadrifólio: largura total (quatro
    lóbulos)."""
    import Part
    V = FreeCAD.Vector
    if perfil == "Redondo":
        return Part.Face(Part.Wire([Part.makeCircle(medida / 2.0)]))
    if perfil == "Quadrado":
        h = medida / 2.0
        return Part.Face(Part.makePolygon([V(-h, -h, 0), V(h, -h, 0), V(h, h, 0), V(-h, h, 0), V(-h, -h, 0)]))
    if perfil == "Sextavado":
        r = medida / math.sqrt(3.0)          # raio do círculo pelos cantos; entre faces = medida
        pts = [V(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k)), 0) for k in range(6)]
        return Part.Face(Part.makePolygon(pts + [pts[0]]))
    if perfil == "Oval":
        a, b = medida / 2.0, (altura if altura > 0 else 0.6 * medida) / 2.0
        if abs(a - b) < 1e-9:
            return Part.Face(Part.Wire([Part.makeCircle(a)]))
        el = Part.Ellipse(V(a, 0, 0), V(0, b, 0), V(0, 0, 0)) if a > b else Part.Ellipse(V(0, b, 0), V(a, 0, 0),
                                                                                         V(0, 0, 0))
        return Part.Face(Part.Wire([el.toShape()]))
    if perfil == "Quadrifólio":
        r = medida / 4.0
        discos = [Part.Face(Part.Wire([Part.makeCircle(r, V(x, y, 0))])) for x, y in ((r, 0), (-r, 0), (0, r), (0, -r))]
        miolo = Part.Face(Part.Wire([Part.makeCircle(r * 1.05)]))
        u = miolo.fuse(discos).removeSplitter()
        return Part.Face(u.Faces[0].OuterWire) if len(u.Faces) > 1 else u.Faces[0]
    raise ValueError("Perfil desconhecido: %s" % perfil)


def secao_interna(perfil, medida, altura, parede):
    """Seção do vazio (tubo): a externa recuada da parede."""
    face = secao_local(perfil, medida, altura)
    junta = 2 if perfil in ("Quadrado", "Sextavado") else 0     # cantos vivos ficam vivos
    of = face.makeOffset2D(-parede, junta)
    f = of.Faces[0] if of.Faces else Part_face(of)
    return f


def Part_face(w):
    import Part
    return Part.Face(w if w.ShapeType == "Wire" else w.Wires[0])


def _base(d, normal):
    up = _referencia(d, normal)
    lado = up.cross(d)                     # (lado, up, d) forma um sistema de mão direita
    return lado, up


def _no_lugar(face, origem, lado, up, d):
    m = FreeCAD.Matrix(lado.x, up.x, d.x, 0, lado.y, up.y, d.y, 0, lado.z, up.z, d.z, 0, 0, 0, 0, 1)
    f = face.copy()
    f.Placement = FreeCAD.Placement(origem, FreeCAD.Rotation(m))
    return f


def _barra_reta(a, b, face, ext_a, ext_b, normal):
    d = b - a
    comp = d.Length
    d.normalize()
    ini = a - d * ext_a
    total = comp + ext_a + ext_b
    lado, up = _base(d, normal)
    return _no_lugar(face, ini, lado, up, d).extrude(d * total)


def _barra_curva(e, face, redondo, normal):
    import Part
    t0 = e.tangentAt(e.FirstParameter)
    t0.normalize()
    p0 = e.valueAt(e.FirstParameter)
    # numa curva plana (arco), a barra acompanha o plano do arco
    binormal = FreeCAD.Vector(e.Curve.Axis) if hasattr(e.Curve, "Axis") else normal
    lado, up = _base(t0, binormal)
    perfil_w = _no_lugar(face, p0, lado, up, t0).OuterWire
    ps = Part.BRepOffsetAPI.MakePipeShell(Part.Wire([e]))
    if not redondo:
        try:
            ps.setBiNormalMode(binormal if binormal is not None else FreeCAD.Vector(0, 0, 1))
        except Exception:
            pass
    ps.add(perfil_w, False, False)
    ps.build()
    ps.makeSolid()
    return ps.shape()


def _no_revolvido(face, p, normal):
    """Peça do encontro para perfis curvos (oval, quadrifólio): a seção girada em torno da normal do plano,
    como a esfera da barra redonda. Cada barra que chega ao centro encosta nela pela própria seção."""
    import Part
    n = FreeCAD.Vector(normal) if normal is not None else FreeCAD.Vector(0, 0, 1)
    n.normalize()
    d = n.cross(FreeCAD.Vector(1, 0, 0))
    if d.Length < 1e-6:
        d = n.cross(FreeCAD.Vector(0, 1, 0))
    d.normalize()
    lado, up = _base(d, n)
    # 1 % maior que a seção: sem isso o encontro fica tangente à barra e o booleano falha ou demora
    face = face.copy()
    face.scale(1.01, FreeCAD.Vector(0, 0, 0))
    bb = face.BoundBox
    metade = face.common(Part.makeBox(bb.XMax + 1.0, bb.YLength + 2.0, 2.0, FreeCAD.Vector(0, bb.YMin - 1.0, -1.0)))
    f = _no_lugar(metade.Faces[0], p, lado, up, d)
    return f.revolve(p, up, 360)


def _graus(arestas, tol):
    """Quantas barras chegam em cada ponta (por proximidade: ponta encostada no meio de outra linha, ou pontas
    que quase se tocam, contam como encontro)."""
    import Part
    graus = {}
    for i, e in enumerate(arestas):
        for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
            k = _chave(p)
            if k in graus:
                continue
            v = Part.Vertex(p)
            n = 0
            for x in arestas:
                try:
                    if x.distToShape(v)[0] <= tol:
                        n += 1
                except Exception:
                    pass
            graus[k] = n
    return graus


def montar(arestas, perfil="Redondo", medida=10.0, interna=0.0, unir=True, normal=None, altura=0.0):
    """Sólido da barra ao longo das arestas. medida: diâmetro (redondo), lado (quadrado), entre faces
    (sextavado) ou largura (oval, quadrifólio); altura: só do oval; interna: diâmetro interno (redondo) ou
    espessura da parede (demais); 0 = maciça. Devolve (forma, comprimento total do caminho)."""
    import Part
    if perfil not in PERFIS:
        raise ValueError("Perfil desconhecido: %s" % perfil)
    if not arestas:
        raise ValueError("O caminho não tem linhas.")
    if medida <= 0:
        raise ValueError("A medida da barra tem de ser maior que zero.")
    redondo = perfil == "Redondo"
    menor = min(medida, altura if (perfil == "Oval" and altura > 0) else medida)
    if redondo and interna >= medida:
        raise ValueError("A medida interna tem de ser menor que a externa.")
    if not redondo and interna > 0 and 2 * interna >= menor:
        raise ValueError("A parede é grossa demais para essa barra.")
    tol = max(0.01, 0.05 * menor)
    grau = _graus(arestas, tol)
    maior = max(medida, altura if perfil == "Oval" else 0.0)
    if perfil == "Sextavado":
        maior = medida / math.sqrt(3.0) * 2.0

    def solidos(face, ext, raio_esfera):
        r = []
        for e in arestas:
            a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if _reta(e):
                ea = ext if grau[_chave(a)] > 1 else 0.0
                eb = ext if grau[_chave(b)] > 1 else 0.0
                r.append(_barra_reta(a, b, face, ea, eb, normal))
            else:
                r.append(_barra_curva(e, face, redondo, normal))
        if unir and (redondo or curvo):
            vistos = set()
            for e in arestas:
                for p in (e.Vertexes[0].Point, e.Vertexes[-1].Point):
                    k = _chave(p)
                    if grau[k] > 1 and k not in vistos:
                        vistos.add(k)
                        r.append(Part.makeSphere(raio_esfera, p) if redondo else _no_revolvido(face, p, normal))
        return r

    # perfis de lados curvos cruzando com a mesma altura se tocam tangentes (o booleano falha): no encontro
    # eles ganham a seção girada (como a esfera da redonda) em vez de prolongar
    curvo = perfil in ("Oval", "Quadrifólio")
    face_ext = secao_local(perfil, medida, altura)
    ext_ext = (maior / 2.0) if (unir and not redondo and not curvo) else 0.0
    ext = solidos(face_ext, ext_ext, medida / 2.0)
    vazio = None
    if interna > 0:
        if redondo:
            face_int, ext_int, r_int = secao_local("Redondo", interna), 0.0, interna / 2.0
        else:
            face_int, ext_int, r_int = secao_interna(perfil, medida, altura, interna), max(0.0, ext_ext - interna), 0.0
        vazio = solidos(face_int, ext_int, r_int)
    def juntar(lista):
        if len(lista) == 1:
            return lista[0]
        u = lista[0].fuse(lista[1:])
        if not u.isValid():   # encontro tangente (perfis curvos): o booleano com tolerância fecha
            u = lista[0].fuse(lista[1:], max(1e-5, 1e-5 * medida))
        return u

    if unir:
        forma = juntar(ext)
        if vazio:
            c = forma.cut(juntar(vazio))
            if not c.isValid():
                c = forma.cut([juntar(vazio)], max(1e-5, 1e-5 * medida))
            forma = c
        try:
            forma = forma.removeSplitter()
        except Exception:
            pass
    else:
        if vazio:
            ext = [s.cut(i) for s, i in zip(ext, vazio)]
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
        add("App::PropertyLength", "Lado", "Barra não redonda: lado (quadrado), entre faces (sextavado), largura "
            "(oval, quadrifólio)", 10.0)
        add("App::PropertyLength", "Parede", "Barra não redonda: espessura da parede (0 = maciça)", 0.0)
        add("App::PropertyLength", "Altura", "Barra oval: altura (0 = 60 % da largura)", 0.0)
        try:   # documento antigo: a lista de perfis ganha os novos, mantendo o escolhido
            if set(obj.getEnumerationsOfProperty("Perfil")) != set(PERFIS):
                atual = obj.Perfil
                obj.Perfil = list(PERFIS)
                obj.Perfil = atual if atual in PERFIS else "Redondo"
        except Exception:
            pass
        add("App::PropertyBool", "Unir", "Une as barras num sólido só (encontros fechados)", True)
        add("App::PropertyLength", "RaioCantos", "Raio nos cantos das linhas retas (0 = canto vivo)", 0.0)
        add("App::PropertyLength", "Comprimento", "Comprimento total das barras (pelo eixo)", 0.0, "Resultado")
        obj.setEditorMode("Comprimento", 1)

    def onDocumentRestored(self, obj):
        self._props(obj)

    def execute(self, obj):
        import Part
        arestas = arredondar_cantos(arestas_do_caminho(obj.Caminho), float(obj.RaioCantos))
        if obj.Perfil == "Redondo":
            medida, interna = float(obj.Diametro), float(obj.DiametroInterno)
        else:
            medida, interna = float(obj.Lado), float(obj.Parede)
        try:
            forma, comp = montar(arestas, obj.Perfil, medida, interna, bool(obj.Unir), _normal_do_plano(obj.Caminho),
                                 float(getattr(obj, "Altura", 0.0)))
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


def criar(caminho, perfil="Redondo", medida=10.0, interna_ou_parede=0.0, unir=True, raio=0.0, doc=None, altura=0.0):
    doc = doc or caminho.Document
    obj = doc.addObject("Part::FeaturePython", "BarraVarredura")
    BarraVarredura(obj)
    obj.Label = "Barra de varredura"
    obj.Caminho = caminho
    obj.Perfil = perfil
    if perfil == "Redondo":
        obj.Diametro, obj.DiametroInterno = medida, interna_ou_parede
    else:
        obj.Lado, obj.Parede = medida, interna_ou_parede
    obj.Altura = altura
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
                 "(grade, xadrez, chapa expandida). Perfil redondo, quadrado, sextavado, oval ou quadrifólio, maciço ou tubo.")

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
            self.altura = self._mm(0.0)
            s1.linha("espessura", self.altura, "Altura do oval (0 = 60 % da largura).", "Altura")
            self._s1 = s1
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

        ROTULO_MEDIDA = {"Redondo": "Diâmetro", "Quadrado": "Lado", "Sextavado": "Entre faces", "Oval": "Largura",
                         "Quadrifólio": "Largura"}
        DICA_MEDIDA = {"Redondo": "Diâmetro externo da barra.", "Quadrado": "Lado da barra quadrada.",
                       "Sextavado": "Distância entre faces (medida da chave).", "Oval": "Largura do oval.",
                       "Quadrifólio": "Largura total dos quatro lóbulos."}

        def _perfil(self, *_a):
            pf = self.perfil.currentData()
            redondo = pf == "Redondo"
            try:
                for lb in self.form.findChildren(QtWidgets.QLabel):
                    if lb.text() in set(self.ROTULO_MEDIDA.values()):
                        lb.setText(self.ROTULO_MEDIDA[pf])
                    elif lb.text() in ("Interno", "Parede"):
                        lb.setText("Interno" if redondo else "Parede")
                    elif lb.text() == "Altura":
                        lb.setVisible(pf == "Oval")
            except Exception:
                pass
            self.altura.setVisible(pf == "Oval")
            self.medida.setToolTip(self.DICA_MEDIDA[pf])
            self.interna.setToolTip("Diâmetro interno (tubo); 0 = barra maciça." if redondo
                                    else "Espessura da parede (tubo); 0 = barra maciça.")

        def pendencia(self):
            if not self.caminho.valores():
                return "Escolha o esboço com as linhas da barra."
            if self.medida.value() <= 0:
                return "A medida da barra tem de ser maior que zero."
            pf = self.perfil.currentData()
            if pf != "Redondo":
                menor = self.medida.value()
                if pf == "Oval" and self.altura.value() > 0:
                    menor = min(menor, self.altura.value())
                if self.interna.value() > 0 and 2 * self.interna.value() >= menor:
                    return "A parede é grossa demais para essa barra."
            elif self.interna.value() >= self.medida.value():
                return "O diâmetro interno tem de ser menor que o externo."
            return None

        def pronto_texto(self):
            return "OK cria a barra ao longo de todas as linhas do esboço."

        def carregar(self, obj):
            self.caminho.aceitar(obj.Caminho)
            self.perfil.setCurrentIndex(max(0, self.perfil.findData(obj.Perfil)))
            if obj.Perfil != "Redondo":
                self.medida.setValue(float(obj.Lado))
                self.interna.setValue(float(obj.Parede))
            else:
                self.medida.setValue(float(obj.Diametro))
                self.interna.setValue(float(obj.DiametroInterno))
            self.altura.setValue(float(getattr(obj, "Altura", 0.0)))
            self.unir.setChecked(bool(obj.Unir))
            self.raio.setValue(float(obj.RaioCantos))

        def props_edicao(self):
            q = self.perfil.currentData() != "Redondo"
            d = {"Caminho": self.caminho.valores()[0], "Perfil": self.perfil.currentData(),
                 "Unir": self.unir.isChecked(), "RaioCantos": self.raio.value(), "Altura": self.altura.value()}
            if q:
                d.update({"Lado": self.medida.value(), "Parede": self.interna.value()})
            else:
                d.update({"Diametro": self.medida.value(), "DiametroInterno": self.interna.value()})
            return d

        def executar(self):
            obj = criar(self.caminho.valores()[0], self.perfil.currentData(), self.medida.value(),
                        self.interna.value(), self.unir.isChecked(), self.raio.value(), altura=self.altura.value())
            return [obj]

    class CmdBarraVarredura:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("barra_varredura.svg"), "MenuText": "Barra de varredura",
                    "ToolTip": "Barra redonda, quadrada, sextavada, oval ou quadrifólio (maciça ou tubo) ao longo de todas as linhas de um esboço; "
                               "as que se cruzam ficam unidas: grade, xadrez, chapa expandida, gradil."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelBarra().mostrar()


def registrar_comandos():
    if FreeCADGui is not None and P is not None:
        FreeCADGui.addCommand("Prumo_BarraVarredura", CmdBarraVarredura())
