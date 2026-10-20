# Prumo 3D: gera os arquivos de exemplo da tela inicial (src/Mod/Prumo3D/Resources/exemplos).
#
# Rodar com a interface do Prumo/FreeCAD aberta (as vistas, cores e miniaturas precisam dela):
#   FreeCAD gerar_exemplos.py      (ou pelo console Python: exec(open(...).read()))
# Grava um registro em <pasta deste arquivo>/gerar_exemplos.log.
import os
import time
import traceback

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore
except ImportError:  # pragma: no cover
    from PySide2 import QtCore

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.environ.get("PRUMO_EXEMPLOS") or os.path.normpath(
    os.path.join(AQUI, "..", "..", "src", "Mod", "Prumo3D", "Resources", "exemplos"))
LOG = os.path.join(AQUI, "gerar_exemplos.log")
V = FreeCAD.Vector


def log(m):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(str(m) + "\n")


def esperar(ms):
    t = time.time()
    while time.time() - t < ms / 1000.0:
        FreeCADGui.updateGui()


def vista_iso(doc):
    gd = FreeCADGui.getDocument(doc.Name)
    FreeCADGui.setActiveDocument(doc.Name)
    v = gd.ActiveView
    v.viewIsometric()
    v.fitAll()
    esperar(400)


def salvar(doc, nome):
    caminho = os.path.join(SAIDA, nome)
    doc.saveAs(caminho)
    log("ok %s (%d objetos)" % (nome, len(doc.Objects)))
    FreeCAD.closeDocument(doc.Name)


def _esboco(doc, corpo, nome, pts, plano="XY"):
    import Part
    sk = corpo.newObject("Sketcher::SketchObject", nome)
    origem = corpo.Origin
    papel = {"XY": "XY_Plane", "XZ": "XZ_Plane", "YZ": "YZ_Plane"}[plano]
    face = [o for o in origem.OriginFeatures if o.Role == papel][0]
    sk.AttachmentSupport = [(face, "")]
    sk.MapMode = "FlatFace"
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    import Sketcher
    for i in range(n):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % n, 1))
    return sk


# ---------------------------------------------------------------- 1. peça com folha ABNT
def exemplo_peca():
    import Part
    import Sketcher
    doc = FreeCAD.newDocument("Suporte")
    doc.Label = "Exemplo — suporte com folha ABNT"
    corpo = doc.addObject("PartDesign::Body", "Suporte")
    corpo.Label = "Suporte"
    sk = _esboco(doc, corpo, "Perfil", [(0, 0), (120, 0), (120, 10), (10, 10), (10, 80), (0, 80)], "XZ")
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))
    pad = corpo.newObject("PartDesign::Pad", "Extrusao")
    pad.Profile = sk
    pad.Length = 60
    if "SideType" in pad.PropertiesList:
        pad.SideType = "Symmetric"
    else:
        pad.Midplane = True
    doc.recompute()
    # dois furos na aba de baixo: esboço no plano XY, levantado até o topo da aba (z = 10)
    sk2 = corpo.newObject("Sketcher::SketchObject", "Furos")
    xy = [o for o in corpo.Origin.OriginFeatures if o.Role == "XY_Plane"][0]
    sk2.AttachmentSupport = [(xy, "")]
    sk2.MapMode = "FlatFace"
    sk2.AttachmentOffset = FreeCAD.Placement(V(0, 0, 10), FreeCAD.Rotation())
    for y in (-15, 15):
        sk2.addGeometry(Part.Circle(V(80, y, 0), V(0, 0, 1), 5.5))
    doc.recompute()
    cav = corpo.newObject("PartDesign::Pocket", "Furacao")
    cav.Profile = sk2
    cav.Type = "ThroughAll"
    doc.recompute()
    try:
        mat = FreeCAD.Material()
        corpo.ViewObject.ShapeAppearance = [mat]
    except Exception:
        pass
    vista_iso(doc)
    try:
        import PrumoFolhas
        PrumoFolhas.nova_folha(doc, "A3", "NBR16752", False,
                               {"titulo": "SUPORTE DE FIXAÇÃO", "material": "ASTM A36",
                                "empresa": "Exemplo Prumo 3D"}, [corpo], None)
        import PrumoBOM
        pagina = [o for o in doc.Objects if o.TypeId == "TechDraw::DrawPage"][0]
        sh = PrumoBOM.gravar_planilha(doc, PrumoBOM.coletar([corpo]))
        PrumoBOM.inserir_na_folha(pagina, sh, len(PrumoBOM.coletar([corpo])))
    except Exception:
        log("folha: " + traceback.format_exc())
    doc.recompute()
    vista_iso(doc)
    salvar(doc, "Exemplo_Suporte_com_folha_ABNT.FCStd")


# ---------------------------------------------------------------- 2. estrutura soldada
def exemplo_estrutura():
    import Part
    import PrumoEstrutura as E
    import PrumoEstruturaExtras as X
    doc = FreeCAD.newDocument("Estrutura")
    doc.Label = "Exemplo — base soldada"
    sk = doc.addObject("Sketcher::SketchObject", "Esqueleto")
    sk.Placement = FreeCAD.Placement(V(), FreeCAD.Rotation(V(1, 0, 0), 90))
    linhas = [((0, 0), (1500, 0)), ((1500, 0), (1500, 900)), ((1500, 900), (0, 900)), ((0, 900), (0, 0)),
              ((750, 0), (750, 900))]
    for a, b in linhas:
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    doc.recompute()
    colunas = "Tubo □ 100 x 100 x 4,75" if E.PrumoPerfis.perfil("Tubo □ 100 x 100 x 4,75") else "W 150 x 18,0"
    travessa = 'Tubo 3" Sch 40' if E.PrumoPerfis.perfil('Tubo 3" Sch 40') else "W 150 x 13,0"
    est = E.criar(doc, sk, "W 150 x 13,0", uniao="Topo", material="ASTM A572 Gr. 50",
                  grupos_extras=[{"nome": "Colunas", "perfil": colunas, "arestas": [1, 3]},
                                 {"nome": "Travessa", "perfil": travessa, "arestas": [4]}])
    E.aplicar_opcao(est, [c for c in E.cantos(est) if c.tipo == "esquadria"], E.OPCOES_ESQUADRIA[3])
    doc.recompute()
    bs = E.barras_de(est)
    X.criar_reforco(bs[2], bs[1], Perna1=200, Perna2=200, Espessura=8, Material="ASTM A36")
    X.criar_reforco(bs[2], bs[3], Perna1=200, Perna2=200, Espessura=8, Material="ASTM A36")
    X.criar_placa_base(bs[1], "Início", Largura=250, Comprimento=250, Espessura=16, Material="ASTM A36")
    X.criar_placa_base(bs[3], "Fim", Largura=250, Comprimento=250, Espessura=16, Material="ASTM A36")
    X.soldar_estrutura(est, 6, X.PROCESSOS[1], "ER70S-6")
    E.gravar_lista_de_corte(doc, E.lista_de_corte([est]))
    X.gravar_lista_de_soldas(doc, X.lista_de_soldas([est]))
    doc.recompute()
    for o in doc.Objects:
        if getattr(o, "Avisos", None):
            log("aviso %s: %s" % (o.Label, list(o.Avisos)))
    vista_iso(doc)
    salvar(doc, "Exemplo_Estrutura_soldada.FCStd")


# ---------------------------------------------------------------- 3. chapa dobrada
def exemplo_chapa():
    import Part
    import SheetMetalBaseCmd
    doc = FreeCAD.newDocument("Chapa")
    doc.Label = "Exemplo — perfil U de chapa dobrada"
    sk = doc.addObject("Sketcher::SketchObject", "PerfilChapa")
    sk.Placement = FreeCAD.Placement(V(), FreeCAD.Rotation(V(1, 0, 0), 90))
    for a, b in (((0, 60), (0, 0)), ((0, 0), (80, 0)), ((80, 0), (80, 40))):
        sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
    doc.recompute()
    base = doc.addObject("Part::FeaturePython", "ChapaDobrada")
    SheetMetalBaseCmd.SMBaseBend(base, sk)
    base.Label = "Chapa dobrada"
    base.Thickness = 2.0
    base.Radius = 2.0
    base.Length = 120.0
    try:
        SheetMetalBaseCmd.SMBaseViewProvider(base.ViewObject)
    except Exception:
        pass
    doc.recompute()
    try:
        sk.ViewObject.Visibility = False
    except Exception:
        pass
    vista_iso(doc)
    salvar(doc, "Exemplo_Chapa_dobrada.FCStd")


def gerar():
    open(LOG, "w", encoding="utf-8").write("")
    os.makedirs(SAIDA, exist_ok=True)
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Document").SetBool("SaveThumbnail", True)
    for f in (exemplo_peca, exemplo_estrutura, exemplo_chapa):
        try:
            f()
        except Exception:
            log("ERRO %s:\n%s" % (f.__name__, traceback.format_exc()))
    log("FIM")


if __name__ == "__main__" or os.environ.get("PRUMO_GERAR_EXEMPLOS"):
    QtCore.QTimer.singleShot(3000, lambda: (gerar(), QtCore.QCoreApplication.quit()
                                            if os.environ.get("PRUMO_SAIR") else None))
