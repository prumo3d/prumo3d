# -*- coding: utf-8 -*-
"""Piso e fechamento (aba Estruturas): preenche um contorno fechado com chapa expandida, chapa perfurada
(tela moeda) ou chapa xadrez.

* Entrada: um esboço fechado (pode ter furos/recortes) ou uma face plana.
* Chapa perfurada: furo, passo e arranjo (60° ou reto); área aberta e peso calculados pela geometria, furos
  reais no modelo (até um limite; acima dele, só a textura).
* Chapa expandida e xadrez: do catálogo (Resources/pisos/pisos.json, valores A CHECAR); o modelo é a
  chapa com o contorno e a textura do padrão; a expandida pode ter a malha recortada (plana, simplificada).
* O padrão corta onde cair; "Centralizar padrão" divide as sobras igualmente.
* Peso: kg/m² do catálogo × área × (densidade do material / aço carbono) para expandida e xadrez;
  volume real × densidade para a perfurada. Entra na lista de materiais com área e peso.
"""

import json
import math
import os

import FreeCAD

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(AQUI, "Resources", "pisos", "pisos.json")
TIPOS = ("Chapa expandida", "Chapa perfurada", "Chapa xadrez")
ARRANJOS = ("60° (desencontrado)", "Reto (90°)")
LIMITE_FUROS = 1000   # acima disso a tela leva segundos para desenhar (cresce mais que linear): só textura
DENS_ACO = 7850.0

_cache = {}


def dados():
    if "d" not in _cache:
        with open(ARQUIVO, encoding="utf-8") as fh:
            _cache["d"] = json.load(fh)
    return _cache["d"]


def materiais():
    return list(dados()["materiais"].keys())


def densidade(material):
    return float(dados()["materiais"].get(material, {"densidade": DENS_ACO})["densidade"])


def malhas():
    return [i["designacao"] for i in dados()["expandida"]["itens"]]


def malha(designacao):
    for i in dados()["expandida"]["itens"]:
        if i["designacao"] == designacao:
            return i
    raise KeyError(designacao)


def xadrezes():
    return [i["designacao"] for i in dados()["xadrez"]["itens"]]


def xadrez(designacao):
    for i in dados()["xadrez"]["itens"]:
        if i["designacao"] == designacao:
            return i
    raise KeyError(designacao)


def area_aberta_perfurada(diametro, passo, arranjo=ARRANJOS[0]):
    """Fração aberta (0–1) da chapa perfurada de furo redondo."""
    if passo <= 0 or diametro <= 0 or diametro >= passo:
        return 0.0
    k = math.pi / (2 * math.sqrt(3)) if arranjo.startswith("60") else math.pi / 4
    return k * (diametro / passo) ** 2


# ---------------------------------------------------------------- geometria

def face_do_contorno(fonte, sub=None):
    """Face plana (com os recortes) a partir de um esboço fechado ou de uma face selecionada."""
    import Part
    sh = fonte.Shape if hasattr(fonte, "Shape") else fonte
    if sub:
        f = sh.getElement(sub) if hasattr(sh, "getElement") else None
        if f is not None and f.ShapeType == "Face":
            return f
    if not getattr(fonte, "TypeId", "").startswith("Sketcher") and len(sh.Faces) == 1 \
            and isinstance(sh.Faces[0].Surface, Part.Plane):
        return sh.Faces[0]
    fechados = [w for w in sh.Wires if w.isClosed()]
    if not fechados:
        raise ValueError("O contorno precisa ser fechado (esboço com linhas que se fecham).")
    try:
        f = Part.makeFace(fechados, "Part::FaceMakerBullseye")
    except Exception:
        f = Part.Face(Part.Wire(max(fechados, key=lambda w: w.BoundBox.DiagonalLength)))
    if f.isNull() or f.Area <= 0:
        raise ValueError("Não deu para formar a chapa com esse contorno.")
    return f.Faces[0] if f.ShapeType != "Face" else f


def referencial(face, angulo=0.0, fonte=None):
    """Origem, eixo u (sentido do padrão), eixo v e normal da face."""
    import Part
    V = FreeCAD.Vector
    u0, u1, v0, v1 = face.ParameterRange
    n = face.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
    n.normalize()
    pl = getattr(fonte, "Placement", None) if (fonte is not None and hasattr(fonte, "TypeId")
                                                and fonte.TypeId.startswith("Sketcher")) else None
    if pl is not None:
        u = pl.Rotation.multVec(V(1, 0, 0))
    else:
        u = V(1, 0, 0) - n * n.x
        if u.Length < 1e-6:
            u = V(0, 1, 0) - n * n.y
    u.normalize()
    if angulo:
        u = FreeCAD.Rotation(n, angulo).multVec(u)
    v = n.cross(u)
    v.normalize()
    return face.CenterOfMass, u, v, n


def _limites_locais(face, origem, u, v):
    xs, ys = [], []
    for vt in face.Vertexes:
        d = vt.Point - origem
        xs.append(d.dot(u))
        ys.append(d.dot(v))
    # arcos podem passar das pontas: soma uma folga pela diagonal da caixa
    folga = 0.05 * face.BoundBox.DiagonalLength
    return min(xs) - folga, max(xs) + folga, min(ys) - folga, max(ys) + folga


def centros(face, origem, u, v, passo_u, passo_v, desencontrado, centralizar):
    """Centros do padrão (em coordenadas globais) que cobrem a face."""
    x0, x1, y0, y1 = _limites_locais(face, origem, u, v)
    pts = []
    if centralizar:
        bx = (x0 + x1) / 2.0
        by = (y0 + y1) / 2.0
    else:
        bx, by = x0 + passo_u / 2.0, y0 + passo_v / 2.0
    i0 = int(math.floor((x0 - bx) / passo_u)) - 1
    i1 = int(math.ceil((x1 - bx) / passo_u)) + 1
    j0 = int(math.floor((y0 - by) / passo_v)) - 1
    j1 = int(math.ceil((y1 - by) / passo_v)) + 1
    for j in range(j0, j1 + 1):
        desl = (passo_u / 2.0) if (desencontrado and j % 2) else 0.0
        for i in range(i0, i1 + 1):
            x = bx + i * passo_u + desl
            y = by + j * passo_v
            if x0 - passo_u <= x <= x1 + passo_u and y0 - passo_v <= y <= y1 + passo_v:
                pts.append(origem + u * x + v * y)
    return pts


def _furos(face, pontos, perfil, raio):
    """Recorta da face os furos (perfil: ponto -> face do furo; raio: maior meia-medida do furo).

    Os furos inteiros (longe da borda e dos recortes) entram direto como furos da face, sem booleano;
    só os que cruzam a borda passam pelo recorte. Assim mil furos levam segundos, não minutos."""
    import Part
    bb = face.BoundBox
    bb.enlarge(raio)
    borda = Part.makeCompound(face.Edges)
    inteiros, cortados = [], []
    for p in pontos:
        if not bb.isInside(p):
            continue
        vt = Part.Vertex(p)
        try:
            d = vt.distToShape(borda)[0]
        except Exception:
            d = 0.0
        if d > raio + 1e-3:
            if face.isInside(p, 1e-6, True):
                inteiros.append(p)
            continue          # longe da borda e fora da face: nada
        cortados.append(p)
    if not inteiros and not cortados:
        return face, 0
    # 1) furos da borda primeiro, com a face ainda simples (booleano rápido)
    faces = [face]
    if cortados:
        corte = face.cut(Part.makeCompound([perfil(p) for p in cortados]))
        faces = list(corte.Faces) or [face]
    # 2) furos inteiros entram direto como contornos internos (sem booleano nem checagem pesada)
    if inteiros:
        por_face = {k: [] for k in range(len(faces))}
        for p in inteiros:
            k = 0
            if len(faces) > 1:
                for kk, f in enumerate(faces):
                    if f.isInside(p, 1e-6, True):
                        k = kk
                        break
            por_face[k].append(p)
        novas = []
        for k, f in enumerate(faces):
            pts = por_face[k]
            if not pts:
                novas.append(f)
                continue
            esperado = f.Area - sum(perfil(p).Area for p in pts)
            nf = None
            # o sentido certo dos furos depende da superfície da face: testa os dois (cada um leva centésimos)
            for inverter in (True, False):
                furos = []
                for p in pts:
                    w = perfil(p).OuterWire.copy()
                    if inverter:
                        w.reverse()
                    furos.append(w)
                fios = [f.OuterWire] + [w for w in f.Wires if not w.isSame(f.OuterWire)] + furos
                try:
                    cand = Part.Face(f.Surface, fios)
                    if abs(cand.Area - esperado) <= 1e-3 * max(f.Area, 1.0):
                        nf = cand
                        break
                except Exception:
                    pass
            if nf is None:   # plano B: booleano (lento, mas certo)
                nf = f.cut(Part.makeCompound([perfil(p) for p in pts]))
            novas.append(nf)
        faces = novas
    base = faces[0] if len(faces) == 1 else Part.makeCompound(faces)
    return base, len(inteiros) + len(cortados)


def montar(face, tipo, espessura, ref, perfurada=None, expandida=None, centralizar=False, real=True):
    """Sólido da chapa (e quantos furos/malhas foram recortados). ref = (origem, u, v, n)."""
    import Part
    origem, u, v, n = ref
    plana = face
    n_furos = 0
    if tipo == "Chapa perfurada" and real and perfurada:
        d, p, arr = perfurada
        des = arr.startswith("60")
        pv = p * math.sqrt(3) / 2.0 if des else p
        pts = centros(face, origem, u, v, p, pv, des, centralizar)
        if len(pts) <= LIMITE_FUROS:
            plana, n_furos = _furos(face, pts, lambda c: Part.Face(Part.Wire([Part.makeCircle(d / 2.0, c, n)])),
                                    d / 2.0)
    elif tipo == "Chapa expandida" and real and expandida:
        a, b, sd, ld = expandida["abertura_a"], expandida["abertura_b"], expandida["malha_sd"], expandida["malha_ld"]
        # LD (diagonal longa) no sentido u; passo LD × SD/2 desencontrado
        pts = centros(face, origem, u, v, ld, sd / 2.0, True, centralizar)
        if len(pts) <= LIMITE_FUROS:
            def losango(c):
                q = [c + u * (b / 2.0), c + v * (a / 2.0), c - u * (b / 2.0), c - v * (a / 2.0)]
                return Part.Face(Part.makePolygon(q + [q[0]]))
            plana, n_furos = _furos(face, pts, losango, max(a, b) / 2.0)
    solido = plana.extrude(n * espessura)
    return solido, n_furos


# ---------------------------------------------------------------- objeto

class PisoChapa:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, doc, valor=None):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, doc)
                if valor is not None:
                    setattr(obj, nome, valor)
        add("App::PropertyLinkSub", "Contorno", "Piso", "Esboço fechado ou face plana a preencher")
        add("App::PropertyEnumeration", "TipoPiso", "Piso", "Chapa expandida, perfurada (tela moeda) ou xadrez")
        if not obj.TipoPiso:
            obj.TipoPiso = list(TIPOS)
        add("App::PropertyEnumeration", "Material", "Piso", "Material da chapa")
        if not obj.Material:
            obj.Material = materiais()
        add("App::PropertyEnumeration", "Malha", "Chapa expandida", "Designação do catálogo (a checar)")
        if not obj.Malha:
            obj.Malha = malhas()
            obj.Malha = "GME-3"
        add("App::PropertyEnumeration", "Xadrez", "Chapa xadrez", "Espessura comercial da chapa xadrez")
        if not obj.Xadrez:
            obj.Xadrez = xadrezes()
            obj.Xadrez = '1/4"'
        add("App::PropertyLength", "DiametroFuro", "Chapa perfurada", "Diâmetro do furo", 20.0)
        add("App::PropertyLength", "Passo", "Chapa perfurada", "Distância entre centros dos furos", 25.0)
        add("App::PropertyEnumeration", "Arranjo", "Chapa perfurada", "Furos desencontrados a 60° ou retos")
        if not obj.Arranjo:
            obj.Arranjo = list(ARRANJOS)
        add("App::PropertyLength", "EspessuraPerfurada", "Chapa perfurada", "Espessura da chapa", 2.0)
        add("App::PropertyAngle", "Direcao", "Padrão", "Giro do padrão no plano (0 = eixo X do esboço)", 0.0)
        add("App::PropertyBool", "Centralizar", "Padrão", "Divide as sobras do padrão igualmente nas bordas", False)
        add("App::PropertyBool", "FurosReais", "Padrão",
            "Recorta os furos/malhas no modelo (perfurada e expandida); desligado = só a textura", True)
        # resultados (só leitura)
        for nome, doc in (("Espessura", "Espessura da chapa (mm)"), ("AreaM2", "Área da chapa (m²)"),
                          ("AreaAberta", "Área aberta (%)"), ("Peso", "Peso (kg)"), ("Massa", "Massa (kg)")):
            add("App::PropertyFloat", nome, "Resultado", doc)
            obj.setEditorMode(nome, 1)
        add("App::PropertyString", "Denominacao", "Resultado", "Descrição para a lista de materiais")
        add("App::PropertyString", "SituacaoDados", "Resultado", "confirmado / a checar")
        add("App::PropertyInteger", "Furos", "Resultado", "Furos ou malhas recortados no modelo")
        for nome in ("Denominacao", "SituacaoDados", "Furos"):
            obj.setEditorMode(nome, 1)
        add("App::PropertyString", "Observacao", "Resultado", "Observação na lista de materiais")
        add("App::PropertyString", "Modelo", "Resultado", "Como a chapa aparece: furos reais ou só a textura")
        obj.setEditorMode("Modelo", 1)

    def onDocumentRestored(self, obj):
        self._props(obj)

    def execute(self, obj):
        import Part
        if obj.Contorno is None:
            obj.Shape = Part.Shape()
            return
        fonte, subs = obj.Contorno
        sub = subs[0] if subs else None
        face = face_do_contorno(fonte, sub)
        ref = referencial(face, float(obj.Direcao), fonte)
        tipo = obj.TipoPiso
        dens = densidade(obj.Material)
        area = face.Area * 1e-6
        perf = exp = None
        if tipo == "Chapa perfurada":
            esp = float(obj.EspessuraPerfurada)
            d, p = float(obj.DiametroFuro), float(obj.Passo)
            if d >= p:
                raise ValueError("O furo tem de ser menor que o passo.")
            perf = (d, p, obj.Arranjo)
            aberta = area_aberta_perfurada(d, p, obj.Arranjo)
            den = "Chapa perfurada furo Ø%s passo %s %s, # %s mm" % (_n(d), _n(p),
                                                                     "60°" if obj.Arranjo.startswith("60") else "reto",
                                                                     _n(esp))
            situ = "confirmado"
        elif tipo == "Chapa expandida":
            exp = malha(obj.Malha)
            esp = float(exp["espessura"])
            aberta = exp["area_aberta"] / 100.0
            den = "Chapa expandida %s (malha %s × %s mm, # %s mm)" % (exp["designacao"], _n(exp["malha_sd"]),
                                                                      _n(exp["malha_ld"]), _n(esp))
            situ = "a checar"
        else:
            x = xadrez(obj.Xadrez)
            esp = float(x["espessura"])
            aberta = 0.0
            den = "Chapa xadrez %s (# %s mm)" % (x["designacao"], _n(esp))
            situ = "a checar"
        solido, n = montar(face, tipo, esp, ref, perf, exp, bool(obj.Centralizar), bool(obj.FurosReais))
        obj.Shape = solido
        obj.Furos = n
        if tipo == "Chapa xadrez":
            obj.Modelo = "chapa com a textura do relevo"
        elif n:
            obj.Modelo = "furos reais (%d)" % n
        elif not obj.FurosReais:
            obj.Modelo = "só a textura (furos reais desligados)"
        else:
            obj.Modelo = "só a textura: mais de %d furos deixariam o modelo lento" % LIMITE_FUROS
        obj.Espessura = esp
        obj.AreaM2 = round(area, 4)
        obj.AreaAberta = round(aberta * 100.0, 1)
        if tipo == "Chapa perfurada":
            peso = area * (1 - aberta) * esp * 1e-3 * dens
        elif tipo == "Chapa expandida":
            peso = area * exp["kg_m2"] * dens / DENS_ACO
        else:
            peso = area * xadrez(obj.Xadrez)["kg_m2"] * dens / DENS_ACO
        obj.Peso = round(peso, 2)
        obj.Massa = obj.Peso
        obj.Denominacao = den + (" — %s" % obj.Material)
        obj.SituacaoDados = situ
        obj.Observacao = "%s m²%s" % (_n(area, 2), "; dados de catálogo a checar" if situ != "confirmado" else "")


def _n(x, casas=None):
    if casas is None:
        s = ("%.2f" % x).rstrip("0").rstrip(".")
    else:
        s = ("%." + str(casas) + "f") % x
    return s.replace(".", ",")


# ---------------------------------------------------------------- aparência (textura do padrão)

COR_MATERIAL = {"Aço carbono": (0.50, 0.52, 0.55), "Aço galvanizado": (0.70, 0.73, 0.76),
                "Inox 304": (0.80, 0.82, 0.84), "Inox 316": (0.80, 0.82, 0.84), "Alumínio": (0.85, 0.86, 0.88)}


def _imagem_padrao(tipo):
    """PNG (uma célula do padrão) gerado na hora, guardado na pasta de dados do usuário."""
    from PySide import QtCore, QtGui
    pasta = os.path.join(FreeCAD.getUserCachePath() if hasattr(FreeCAD, "getUserCachePath")
                         else FreeCAD.getUserAppDataDir(), "PrumoPisos")
    os.makedirs(pasta, exist_ok=True)
    nome = os.path.join(pasta, {"Chapa expandida": "expandida", "Chapa perfurada": "perfurada",
                                "Chapa xadrez": "xadrez"}[tipo] + ".png")
    if os.path.exists(nome):
        return nome
    img = QtGui.QImage(128, 128, QtGui.QImage.Format_RGB32)
    img.fill(QtGui.QColor(225, 228, 232))
    pt = QtGui.QPainter(img)
    pt.setRenderHint(QtGui.QPainter.Antialiasing)
    escuro = QtGui.QColor(70, 75, 82)
    if tipo == "Chapa expandida":
        pt.setPen(QtGui.QPen(QtGui.QColor(150, 155, 160), 10))
        pt.setBrush(escuro)
        for cx, cy in ((64, 64), (0, 0), (128, 0), (0, 128), (128, 128)):
            pt.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(cx + 52, cy), QtCore.QPointF(cx, cy + 26),
                                            QtCore.QPointF(cx - 52, cy), QtCore.QPointF(cx, cy - 26)]))
    elif tipo == "Chapa perfurada":
        pt.setPen(QtCore.Qt.NoPen)
        pt.setBrush(escuro)
        for cx, cy in ((64, 64), (0, 0), (128, 0), (0, 128), (128, 128)):
            pt.drawEllipse(QtCore.QPointF(cx, cy), 40, 40)
    else:
        pt.setPen(QtCore.Qt.NoPen)
        pt.setBrush(QtGui.QColor(160, 165, 170))
        for cx, cy, ang in ((32, 32, 45), (96, 96, 45), (96, 32, -45), (32, 96, -45)):
            pt.save()
            pt.translate(cx, cy)
            pt.rotate(ang)
            pt.drawRoundedRect(QtCore.QRectF(-22, -5, 44, 10), 5, 5)
            pt.restore()
    pt.end()
    img.save(nome)
    return nome


class VistaPiso:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.vobj = vobj
        self._tex = None

    def getIcon(self):
        return os.path.join(AQUI, "Resources", "icons", "piso.svg")

    def updateData(self, obj, prop):
        if prop in ("Shape", "TipoPiso", "Material", "Direcao"):
            self._textura(obj)

    def onChanged(self, vobj, prop):
        pass

    def _textura(self, obj):
        try:
            from pivy import coin
            vobj = obj.ViewObject
            raiz = vobj.RootNode
            if self._tex is not None:
                for n in self._tex:
                    raiz.removeChild(n)
                self._tex = None
            if obj.Shape.isNull() or (obj.TipoPiso == "Chapa perfurada" and obj.Furos):
                cor = COR_MATERIAL.get(obj.Material, (0.6, 0.6, 0.6))
                vobj.ShapeAppearance[0].DiffuseColor = cor if len(cor) == 4 else cor + (0.0,)
                return
            fonte = obj.Contorno[0] if obj.Contorno else None
            face = face_do_contorno(fonte, obj.Contorno[1][0] if obj.Contorno and obj.Contorno[1] else None)
            _o, u, v, _n_ = referencial(face, float(obj.Direcao), fonte)
            if obj.TipoPiso == "Chapa expandida":
                m = malha(obj.Malha)
                pu, pv = m["malha_ld"], m["malha_sd"]
            elif obj.TipoPiso == "Chapa perfurada":
                pu = float(obj.Passo)
                pv = pu * math.sqrt(3) if obj.Arranjo.startswith("60") else pu
            else:
                pu = pv = 40.0
            tex = coin.SoTexture2()
            tex.filename = _imagem_padrao(obj.TipoPiso)
            tex.model = coin.SoTexture2.MODULATE
            coord = coin.SoTextureCoordinatePlane()
            coord.directionS.setValue(coin.SbVec3f(u.x / pu, u.y / pu, u.z / pu))
            coord.directionT.setValue(coin.SbVec3f(v.x / pv, v.y / pv, v.z / pv))
            raiz.insertChild(coord, 0)
            raiz.insertChild(tex, 0)
            self._tex = (tex, coord)
        except Exception:
            self._tex = None

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(fonte, sub=None, tipo="Chapa expandida", doc=None, **kw):
    doc = doc or FreeCAD.ActiveDocument
    obj = doc.addObject("Part::FeaturePython", "Piso")
    PisoChapa(obj)
    obj.Contorno = (fonte, [sub] if sub else [])
    obj.TipoPiso = tipo
    for k, v in kw.items():
        setattr(obj, k, v)
    obj.Label = {"Chapa expandida": "Chapa expandida", "Chapa perfurada": "Chapa perfurada",
                 "Chapa xadrez": "Chapa xadrez"}[tipo]
    if FreeCAD.GuiUp:
        VistaPiso(obj.ViewObject)
        try:
            fonte.ViewObject.Visibility = False
        except Exception:
            pass
    doc.recompute()
    return obj


def e_piso(obj):
    return obj is not None and isinstance(getattr(obj, "Proxy", None), PisoChapa)


# ============================================================================ interface
try:
    import FreeCADGui
    from PySide import QtWidgets
    import PrumoPainel as P
except ImportError:
    FreeCADGui = None
    P = None


def _filtro_contorno(obj, subs):
    """Esboço fechado (o esboço todo) ou face plana (o elemento)."""
    import Part
    try:
        if e_piso(obj):
            return []
        r = []
        faces = [s for s in (subs or ()) if s.startswith("Face")]
        for s in faces:
            f = obj.Shape.getElement(s)
            if isinstance(f.Surface, Part.Plane):
                r.append(("%s · %s" % (obj.Label, s.replace("Face", "Face ")), (obj, s)))
        if r:
            return r
        if obj.TypeId == "Sketcher::SketchObject" and any(w.isClosed() for w in obj.Shape.Wires):
            return [(obj.Label, (obj, None))]
    except Exception:
        pass
    return []


if P is not None:
    class PainelPiso(P.PainelTarefa):
        titulo = "Piso e fechamento"
        ajuda = ("Escolha um esboço fechado (os recortes do esboço ficam vazados) ou uma face plana e o tipo: "
                 "chapa expandida, chapa perfurada (tela moeda) ou chapa xadrez. Área e peso entram na lista "
                 "de materiais.")
        previa = True

        def montar(self):
            f = self.form
            s0 = f.secao("Contorno", "selecao")
            self.contorno = f.caixa(s0, "Contorno", _filtro_contorno, minimo=1, maximo=1,
                                    dica="Esboço fechado ou face plana.")
            s1 = f.secao("Tipo", "tipo")
            self.tipo = P.Opcoes([("Chapa expandida", "Expandida", "tipo", "Chapa expandida (malha losango)"),
                                  ("Chapa perfurada", "Perfurada", "furo", "Chapa perfurada furo redondo (tela moeda)"),
                                  ("Chapa xadrez", "Xadrez", "espessura", "Chapa xadrez (piso antiderrapante)")],
                                 "Chapa expandida")
            s1.widget(self.tipo)
            self.material = P.lista(materiais(), "Aço carbono")
            s1.linha("material", self.material, "Material da chapa.", "Material")
            # uma seção por tipo (só a do tipo escolhido aparece)
            self.s_exp = f.secao("Chapa expandida", "tipo")
            self.malha = P.lista(malhas(), "GME-3")
            self.s_exp.linha("tipo", self.malha, "Malhas EXP (fechamento, proteção) e GME (piso). Catálogo A CHECAR.",
                             "Malha")
            self.s_xad = f.secao("Chapa xadrez", "espessura")
            self.xad = P.lista(xadrezes(), '1/4"')
            self.s_xad.linha("espessura", self.xad, "Espessura comercial (catálogo a checar).", "Espessura")
            self.s_perf = f.secao("Chapa perfurada (tela moeda)", "furo")
            self.furo = P.numero(20.0, 0.5, 500.0)
            self.s_perf.linha("furo", self.furo, "Diâmetro do furo.", "Furo")
            self.passo = P.numero(25.0, 1.0, 1000.0)
            self.s_perf.linha("largura", self.passo, "Distância entre centros dos furos.", "Passo")
            self.arranjo = P.lista(list(ARRANJOS), ARRANJOS[0])
            self.s_perf.linha("tipo", self.arranjo, "Furos desencontrados (60°) ou em linha.", "Arranjo")
            self.esp = P.numero(2.0, 0.3, 50.0, casas=2)
            self.s_perf.linha("espessura", self.esp, "Espessura da chapa perfurada.", "Espessura")
            s2 = f.secao("Padrão", "info")
            self.direcao = P.numero(0.0, -180.0, 180.0, sufixo=" °")
            s2.linha("angulo", self.direcao, "Gira o padrão no plano (0 = eixo X do esboço). Na expandida, a "
                                             "diagonal longa da malha fica nessa direção.", "Direção")
            self.centralizar = s2.linha("posicao", P.marcar("Centralizar o padrão (sobras iguais nas bordas)"), "")
            self.reais = s2.linha("posicao", P.marcar("Furos reais no modelo (até %d)" % LIMITE_FUROS, True), "")
            s3 = f.secao("Resultado", "info")
            self.resultado = QtWidgets.QLabel("—")
            self.resultado.setWordWrap(True)
            s3.widget(self.resultado)
            self.tipo.mudou.connect(self._tipo)
            self._tipo()

        def _tipo(self, *_a):
            t = self.tipo.valor()
            self.s_exp.setVisible(t == "Chapa expandida")
            self.s_xad.setVisible(t == "Chapa xadrez")
            self.s_perf.setVisible(t == "Chapa perfurada")
            self.reais.setVisible(t != "Chapa xadrez")

        def pendencia(self):
            if not self.contorno.valores():
                return "Escolha o esboço fechado ou a face plana."
            if self.tipo.valor() == "Chapa perfurada" and self.furo.value() >= self.passo.value():
                return "O furo tem de ser menor que o passo."
            return None

        def pronto_texto(self):
            return "OK cria a chapa no contorno."

        def _kw(self):
            return {"Material": self.material.currentText(), "Malha": self.malha.currentText(),
                    "Xadrez": self.xad.currentText(), "DiametroFuro": self.furo.value(),
                    "Passo": self.passo.value(), "Arranjo": self.arranjo.currentText(),
                    "EspessuraPerfurada": self.esp.value(), "Direcao": self.direcao.value(),
                    "Centralizar": self.centralizar.isChecked(), "FurosReais": self.reais.isChecked()}

        def carregar(self, obj):
            fonte, subs = obj.Contorno
            self.contorno.aceitar(fonte, list(subs or ()))
            self.tipo.definir(obj.TipoPiso)
            self.material.setCurrentText(obj.Material)
            self.malha.setCurrentText(obj.Malha)
            self.xad.setCurrentText(obj.Xadrez)
            self.furo.setValue(float(obj.DiametroFuro))
            self.passo.setValue(float(obj.Passo))
            self.arranjo.setCurrentText(obj.Arranjo)
            self.esp.setValue(float(obj.EspessuraPerfurada))
            self.direcao.setValue(float(obj.Direcao))
            self.centralizar.setChecked(bool(obj.Centralizar))
            self.reais.setChecked(bool(obj.FurosReais))
            self._tipo()

        def props_edicao(self):
            fonte, sub = self.contorno.valores()[0]
            d = self._kw()
            d["Contorno"] = (fonte, [sub] if sub else [])
            d["TipoPiso"] = self.tipo.valor()
            return d

        def executar(self):
            fonte, sub = self.contorno.valores()[0]
            obj = criar(fonte, sub, self.tipo.valor(), **self._kw())
            self._mostrar_resultado(obj)
            return [obj]

        def _atualizar_previa(self):
            super()._atualizar_previa()
            alvo = self.editando
            if alvo is None:
                doc = self._doc_previa
                nomes = [n for n in self._previa_nomes if doc and doc.getObject(n) is not None
                         and e_piso(doc.getObject(n))]
                alvo = doc.getObject(nomes[0]) if nomes else None
            self._mostrar_resultado(alvo)

        def _mostrar_resultado(self, obj):
            if obj is None or obj.Shape.isNull():
                self.resultado.setText("—")
                return
            linhas = ["Área: %s m²" % _n(obj.AreaM2, 2),
                      "Área aberta: %s %%" % _n(obj.AreaAberta, 1) if obj.TipoPiso != "Chapa xadrez" else None,
                      "Peso: %s kg" % _n(obj.Peso, 2),
                      "Modelo: %s" % obj.Modelo,
                      "Dados de catálogo A CHECAR no fabricante." if obj.SituacaoDados != "confirmado" else None]
            self.resultado.setText("\n".join(l for l in linhas if l))

    class CmdPiso:
        def GetResources(self):
            import PrumoUtil
            return {"Pixmap": PrumoUtil.icone("piso.svg"), "MenuText": "Piso e fechamento",
                    "ToolTip": "Preenche um esboço fechado ou uma face com chapa expandida, chapa perfurada "
                               "(tela moeda) ou chapa xadrez; área e peso na lista de materiais."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            PainelPiso().mostrar()

    def _duplo_clique(self, vobj):
        PainelPiso().editar_objeto(vobj.Object).mostrar()
        return True

    VistaPiso.doubleClicked = _duplo_clique

    def _filhos(self):
        try:
            fonte = self.vobj.Object.Contorno[0]
            return [fonte] if fonte is not None and fonte.TypeId.startswith("Sketcher") else []
        except Exception:
            return []

    VistaPiso.claimChildren = _filhos


def registrar_comandos():
    if FreeCADGui is not None and P is not None and "Prumo_Piso" not in FreeCADGui.listCommands():
        FreeCADGui.addCommand("Prumo_Piso", CmdPiso())
