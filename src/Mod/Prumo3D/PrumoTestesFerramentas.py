# SPDX-License-Identifier: LGPL-2.1-or-later
"""Testes das ferramentas do Prumo 3D (cotas na tela, menu de contexto, massa, lista de materiais,
pranchas ABNT, perfis e estruturas, chapa metálica, fixadores e vaso de pressão).

Entram no conjunto do comando "Testes automáticos" (PrumoTestes).
"""
import math
import os
import tempfile
import time
import unittest

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    QtCore = QtWidgets = None


# ======================================================================= modelos de teste
def novo_doc(nome):
    return FreeCAD.newDocument(nome)


def fechar(doc):
    try:
        FreeCAD.closeDocument(doc.Name)
    except Exception:
        pass


def esboco_retangulo(body, larg=40.0, alt=20.0, nome="Sketch", suporte=None):
    import Part
    import Sketcher
    doc = body.Document
    sk = body.newObject("Sketcher::SketchObject", nome)
    if suporte is None:
        plano = [o for o in body.Origin.OriginFeatures if o.Role == "XY_Plane"][0]
        sk.AttachmentSupport = (plano, [""])
    else:
        sk.AttachmentSupport = suporte
    sk.MapMode = "FlatFace"
    p = [FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(larg, 0, 0), FreeCAD.Vector(larg, alt, 0),
         FreeCAD.Vector(0, alt, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4]))
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))
    sk.addConstraint(Sketcher.Constraint("Horizontal", 2))
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))
    sk.addConstraint(Sketcher.Constraint("Vertical", 3))
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    i_l = sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, larg))
    sk.renameConstraint(i_l, "Largura")
    sk.addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, alt))
    doc.recompute()
    return sk


def peca_exemplo(doc, larg=40.0, alt=20.0, esp=10.0, furo=5.0, raio=2.0):
    """Corpo com extrusão (bloco), cavidade circular na face de cima e arredondamento."""
    import Part
    import Sketcher
    body = doc.addObject("PartDesign::Body", "Body")
    sk = esboco_retangulo(body, larg, alt)
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk
    pad.Length = esp
    doc.recompute()
    topo = None
    for i, f in enumerate(pad.Shape.Faces, 1):
        if abs(f.CenterOfMass.z - esp) < 1e-6 and abs(f.normalAt(0, 0).z - 1) < 1e-6:
            topo = "Face%d" % i
    sk2 = body.newObject("Sketcher::SketchObject", "Sketch001")
    sk2.AttachmentSupport = (pad, [topo])
    sk2.MapMode = "FlatFace"
    c = sk2.addGeometry(Part.Circle(FreeCAD.Vector(larg / 2, alt / 2, 0), FreeCAD.Vector(0, 0, 1), furo))
    sk2.addConstraint(Sketcher.Constraint("Radius", c, furo))
    sk2.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, c, 3, larg / 2))
    sk2.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, c, 3, alt / 2))
    doc.recompute()
    pk = body.newObject("PartDesign::Pocket", "Pocket")
    pk.Profile = sk2
    pk.Length = esp / 2
    doc.recompute()
    # aresta vertical do canto (x=0, y=0)
    aresta = None
    for i, e in enumerate(pk.Shape.Edges, 1):
        a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
        if abs(a.x) < 1e-6 and abs(a.y) < 1e-6 and abs(b.x) < 1e-6 and abs(b.y) < 1e-6:
            aresta = "Edge%d" % i
    fl = body.newObject("PartDesign::Fillet", "Fillet")
    fl.Base = (pk, [aresta])
    fl.Radius = raio
    doc.recompute()
    return body, sk, pad, sk2, pk, fl


def bloco_simples(doc, larg=40.0, alt=20.0, esp=10.0):
    """Corpo com uma extrusão só (para testes que mudam cotas e recalculam)."""
    body = doc.addObject("PartDesign::Body", "Bloco")
    sk = esboco_retangulo(body, larg, alt, nome="SketchBloco")
    pad = body.newObject("PartDesign::Pad", "PadBloco")
    pad.Profile = sk
    pad.Length = esp
    doc.recompute()
    return body, sk, pad


def face_por(shape, cond):
    for i, f in enumerate(shape.Faces, 1):
        if cond(f):
            return "Face%d" % i
    return None


# ======================================================================= cotas na tela
class T11CotasNaTela(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteCotas")
        self.body, self.sk, self.pad, self.sk2, self.pk, self.fl = peca_exemplo(self.doc)

    def tearDown(self):
        fechar(self.doc)

    def test_modelo_valido(self):
        self.assertTrue(self.body.Shape.isValid())
        self.assertEqual(self.body.Tip, self.fl)

    def test_cotas_da_extrusao_incluem_esboco(self):
        import PrumoCotas
        grupos = PrumoCotas.cotas_da_operacao(self.pad)
        self.assertEqual(grupos[0][0], self.pad.Label)
        rot = {c.rotulo: c for c in grupos[0][1]}
        self.assertIn("Comprimento", rot)
        self.assertAlmostEqual(rot["Comprimento"].valor, 10.0)
        self.assertEqual(rot["Comprimento"].unidade, "mm")
        self.assertEqual(grupos[1][0], self.sk.Label)
        nomes = [c.rotulo for c in grupos[1][1]]
        self.assertTrue(any(n.startswith("Largura") for n in nomes), nomes)

    def test_face_lateral_e_da_extrusao(self):
        import PrumoCotas
        sub = face_por(self.body.Shape, lambda f: abs(f.CenterOfMass.y) < 1e-6 and
                       f.Surface.__class__.__name__ == "Plane")
        self.assertIsNotNone(sub)
        self.assertEqual(PrumoCotas.operacao_da_face(self.body, sub), self.pad)

    def test_parede_do_furo_e_da_cavidade(self):
        import PrumoCotas
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Cylinder" and
                       abs(f.Surface.Radius - 5.0) < 1e-6)
        self.assertEqual(PrumoCotas.operacao_da_face(self.body, sub), self.pk)

    def test_fundo_do_furo_e_da_cavidade(self):
        import PrumoCotas
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Plane" and
                       abs(f.CenterOfMass.z - 5.0) < 1e-6 and abs(abs(f.Surface.Axis.z) - 1) < 1e-6)
        self.assertIsNotNone(sub)
        self.assertEqual(PrumoCotas.operacao_da_face(self.body, sub), self.pk)

    def test_face_do_arredondamento(self):
        import PrumoCotas
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Cylinder" and
                       abs(f.Surface.Radius - 2.0) < 1e-6)
        self.assertEqual(PrumoCotas.operacao_da_face(self.body, sub), self.fl)

    def test_topo_parcialmente_furado_ainda_e_da_extrusao(self):
        import PrumoCotas
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Plane" and
                       abs(f.CenterOfMass.z - 10.0) < 1e-6 and abs(abs(f.Surface.Axis.z) - 1) < 1e-6)
        self.assertIsNotNone(sub)
        self.assertEqual(PrumoCotas.operacao_da_face(self.body, sub), self.pad)

    def test_aplicar_comprimento_recalcula(self):
        import PrumoCotas
        body, sk, pad = bloco_simples(self.doc)
        c = [c for c in PrumoCotas.cotas_de_propriedades(pad) if c.prop == "Length"][0]
        ok, msg = PrumoCotas.aplicar(c, 25.0)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(body.Shape.BoundBox.ZLength, 25.0, places=5)

    def test_objeto_com_erro_sem_relacao_nao_bloqueia(self):
        import PrumoCotas
        body, sk, pad = bloco_simples(self.doc)
        ruim = self.doc.addObject("Part::Box", "CaixaRuim")
        ruim.Length = 0
        self.doc.recompute()
        self.assertTrue("Invalid" in ruim.State or "Error" in ruim.State, ruim.State)
        c = [c for c in PrumoCotas.cotas_de_propriedades(pad) if c.prop == "Length"][0]
        ok, msg = PrumoCotas.aplicar(c, 30.0)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(body.Shape.BoundBox.ZLength, 30.0, places=5)

    def test_profundidade_da_cavidade(self):
        import PrumoCotas
        c = [c for c in PrumoCotas.cotas_de_propriedades(self.pk) if c.prop == "Length"][0]
        ok, msg = PrumoCotas.aplicar(c, 8.0)
        self.assertTrue(ok, msg)
        fundo = [f for f in self.body.Shape.Faces if f.Surface.__class__.__name__ == "Plane"
                 and abs(f.CenterOfMass.z - 2.0) < 1e-6]
        self.assertTrue(fundo)

    def test_aplicar_cota_do_esboco(self):
        import PrumoCotas
        c = [c for c in PrumoCotas.cotas_de_esboco(self.sk) if c.rotulo.startswith("Largura")][0]
        ok, msg = PrumoCotas.aplicar(c, 60.0)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(self.body.Shape.BoundBox.XLength, 60.0, places=5)

    def test_raio_do_furo_e_angulo_em_graus(self):
        import PrumoCotas
        c = [c for c in PrumoCotas.cotas_de_esboco(self.sk2) if "raio" in c.rotulo][0]
        ok, msg = PrumoCotas.aplicar(c, 3.0)
        self.assertTrue(ok, msg)
        cil = [f for f in self.body.Shape.Faces if f.Surface.__class__.__name__ == "Cylinder"
               and abs(f.Surface.Radius - 3.0) < 1e-6]
        self.assertTrue(cil)

    def test_valor_impossivel_volta_o_anterior(self):
        import PrumoCotas
        c = [c for c in PrumoCotas.cotas_de_propriedades(self.fl) if c.prop == "Radius"][0]
        ok, msg = PrumoCotas.aplicar(c, 50.0)   # raio maior que a peça: não fecha
        self.assertFalse(ok)
        self.assertAlmostEqual(self.fl.Radius.Value, 2.0)
        self.assertTrue(self.body.Shape.isValid())

    def test_cota_com_formula_fica_bloqueada(self):
        import PrumoCotas
        self.pad.setExpression("Length", "Sketch.Constraints.Largura / 4")
        self.doc.recompute()
        c = [c for c in PrumoCotas.cotas_de_propriedades(self.pad) if c.prop == "Length"][0]
        self.assertTrue(c.bloqueada)
        ok, _ = PrumoCotas.aplicar(c, 99.0)
        self.assertFalse(ok)

    def test_desfazer_volta_o_valor(self):
        import PrumoCotas
        self.doc.UndoMode = 1
        body, sk, pad = bloco_simples(self.doc)
        c = [c for c in PrumoCotas.cotas_de_propriedades(pad) if c.prop == "Length"][0]
        ok, msg = PrumoCotas.aplicar(c, 30.0)
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(pad.Length.Value, 30.0)
        self.doc.undo()
        self.doc.recompute()
        self.assertAlmostEqual(pad.Length.Value, 10.0)

    def test_painel_abre_e_fecha(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoCotas
        p = PrumoCotas.mostrar(self.pad)
        self.assertTrue(p.isVisible())
        self.assertGreaterEqual(len(p.campos), 3)
        p.close()

    def test_painel_aplica_ao_editar(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoCotas
        body, sk, pad = bloco_simples(self.doc)
        p = PrumoCotas.mostrar(pad)
        cota, w = [(c, w) for c, w in p.campos if getattr(c, "prop", None) == "Length"][0]
        w.setValue(12.5)
        w.editingFinished.emit()
        self.assertAlmostEqual(pad.Length.Value, 12.5)
        self.assertFalse(p.aviso.isVisible())
        p.close()

    def test_painel_mostra_aviso_quando_falha(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoCotas
        p = PrumoCotas.mostrar(self.fl)
        cota, w = [(c, w) for c, w in p.campos if getattr(c, "prop", None) == "Radius"][0]
        w.setValue(50.0)
        w.editingFinished.emit()
        self.assertAlmostEqual(self.fl.Radius.Value, 2.0)
        self.assertAlmostEqual(w.value(), 2.0)
        self.assertTrue(p.aviso.text())
        p.close()

    def test_duplo_clique_abre_painel_da_operacao(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoCotas
        from PySide import QtCore
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Cylinder" and
                       abs(f.Surface.Radius - 5.0) < 1e-6)
        PrumoCotas._abrir_por_duplo_clique(self.body, sub, QtCore.QPoint(200, 200))
        p = PrumoCotas._painel["atual"]
        self.assertIsNotNone(p)
        self.assertEqual(p.obj, self.pk)
        p.close()


# ======================================================================= massa
class T12Massa(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteMassa")

    def tearDown(self):
        fechar(self.doc)

    def _caixa(self, nome, x, y, z, pos=(0, 0, 0)):
        o = self.doc.addObject("Part::Box", nome)
        o.Length, o.Width, o.Height = x, y, z
        o.Placement.Base = FreeCAD.Vector(*pos)
        return o

    def test_caixa_de_aco_sem_material(self):
        import PrumoMassa
        b = self._caixa("Caixa", 100, 50, 20)
        self.doc.recompute()
        r = PrumoMassa.calcular([b], 7850)
        vol = 100 * 50 * 20
        self.assertAlmostEqual(r.volume, vol, places=3)
        self.assertAlmostEqual(r.massa, vol * 7850e-9, places=6)
        self.assertAlmostEqual(r.cg.x, 50, places=6)
        self.assertAlmostEqual(r.cg.y, 25, places=6)
        self.assertAlmostEqual(r.cg.z, 10, places=6)
        self.assertEqual(r.sem_material, [b.Label])

    def test_inercia_analitica_da_caixa(self):
        import PrumoMassa
        b = self._caixa("Caixa", 100, 50, 20)
        self.doc.recompute()
        r = PrumoMassa.calcular([b], 7850)
        m = r.massa
        ixx = m * (50 ** 2 + 20 ** 2) / 12.0
        iyy = m * (100 ** 2 + 20 ** 2) / 12.0
        izz = m * (100 ** 2 + 50 ** 2) / 12.0
        self.assertAlmostEqual(r.inercia[0][0] / ixx, 1.0, places=6)
        self.assertAlmostEqual(r.inercia[1][1] / iyy, 1.0, places=6)
        self.assertAlmostEqual(r.inercia[2][2] / izz, 1.0, places=6)
        self.assertAlmostEqual(abs(r.inercia[0][1]) / ixx, 0.0, places=6)
        p = sorted([ixx, iyy, izz])
        for a, b2 in zip(r.principais, p):
            self.assertAlmostEqual(a / b2, 1.0, places=6)

    def test_duas_pecas_teorema_dos_eixos_paralelos(self):
        import PrumoMassa
        a = self._caixa("A", 10, 10, 10)
        b = self._caixa("B", 10, 10, 10, (100, 0, 0))
        self.doc.recompute()
        r = PrumoMassa.calcular([a, b], 1000)
        m1 = 1000 * 1e-9 * 1000
        self.assertAlmostEqual(r.massa, 2 * m1, places=9)
        self.assertAlmostEqual(r.cg.x, 55, places=6)
        # centros em x=5 e x=105, CG em 55: Izz = 2*(m*(a²+a²)/12) + 2*m*50²
        izz = 2 * (m1 * 200 / 12.0) + 2 * m1 * 50 ** 2
        self.assertAlmostEqual(r.inercia[2][2] / izz, 1.0, places=6)

    def test_material_da_peca_e_usado(self):
        import Materials
        import PrumoMassa
        b = self._caixa("Caixa", 10, 10, 10)
        mm = Materials.MaterialManager()
        alu = None
        for uuid, m in mm.Materials.items():
            if m.Name.startswith("Aluminum") or m.Name.startswith("Alumínio"):
                try:
                    dens = FreeCAD.Units.Quantity(m.getPhysicalValue("Density")).getValueAs("kg/m^3")
                except Exception:
                    continue
                alu = (mm.getMaterial(uuid), float(dens))
                break
        if alu is None:
            self.skipTest("sem material de alumínio na biblioteca")
        b.ShapeMaterial = alu[0]
        self.doc.recompute()
        r = PrumoMassa.calcular([b], 7850)
        self.assertEqual(r.sem_material, [])
        self.assertAlmostEqual(r.massa, 1000 * alu[1] * 1e-9, places=9)

    def test_corpo_partdesign_e_parte(self):
        import PrumoMassa
        part = self.doc.addObject("App::Part", "Parte")
        body, sk, pad = bloco_simples(self.doc)
        part.addObject(body)
        part.Placement.Base = FreeCAD.Vector(0, 0, 100)
        self.doc.recompute()
        r = PrumoMassa.calcular([part], 7850)
        self.assertAlmostEqual(r.volume, 40 * 20 * 10, places=3)
        self.assertAlmostEqual(r.cg.z, 105, places=5)

    def test_vinculo_conta_duas_vezes(self):
        import PrumoMassa
        b = self._caixa("Caixa", 10, 10, 10)
        lk = self.doc.addObject("App::Link", "Copia")
        lk.LinkedObject = b
        lk.Placement.Base = FreeCAD.Vector(50, 0, 0)
        self.doc.recompute()
        r = PrumoMassa.calcular([b, lk], 1000)
        self.assertAlmostEqual(r.volume, 2000, places=3)
        self.assertAlmostEqual(r.cg.x, 30, places=5)

    def test_texto_formatado_em_portugues(self):
        import PrumoMassa
        b = self._caixa("Caixa", 100, 100, 100)
        self.doc.recompute()
        t = PrumoMassa.texto(PrumoMassa.calcular([b], 7850))
        self.assertIn("Massa: 7,850 kg", t)
        self.assertIn("Centro de gravidade", t)

    def test_marcar_cg(self):
        import PrumoMassa
        b = self._caixa("Caixa", 20, 20, 20)
        self.doc.recompute()
        p = PrumoMassa.marcar_cg(PrumoMassa.calcular([b], 7850), self.doc)
        self.assertAlmostEqual(p.Shape.Vertexes[0].Point.x, 10, places=6)

    def test_dialogo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoMassa
        b = self._caixa("Caixa", 20, 20, 20)
        self.doc.recompute()
        d = PrumoMassa.DialogoMassa([b])
        self.assertIn("kg", d.saida.toPlainText())
        d.dens.setValue(1000)
        self.assertAlmostEqual(d.resultado.massa, 8000 * 1e-6, places=9)
        d.copiar()
        d.close()


# ======================================================================= menu de contexto
class T13MenuContexto(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteCtx")
        self.body, self.sk, self.pad, self.sk2, self.pk, self.fl = peca_exemplo(self.doc)

    def tearDown(self):
        fechar(self.doc)

    def test_esboco(self):
        import PrumoContexto
        it = PrumoContexto.itens_para([(self.sk, [])])
        for c in ("Prumo_CtxExtrudar", "Prumo_CtxCavidade", "Prumo_CtxRevolucao", "Prumo_CtxEditarEsboco"):
            self.assertIn(c, it)

    def test_face_plana(self):
        import PrumoContexto
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Plane")
        it = PrumoContexto.itens_para([(self.body, [sub])])
        self.assertEqual(it[0], "Prumo_CtxEsbocoNaFace")
        self.assertIn("Prumo_CtxExtrudar", it)
        self.assertIn("Prumo_Cotas", it)
        self.assertIn("Prumo_Massa", it)

    def test_face_curva_sem_esboco(self):
        import PrumoContexto
        sub = face_por(self.body.Shape, lambda f: f.Surface.__class__.__name__ == "Cylinder")
        it = PrumoContexto.itens_para([(self.body, [sub])])
        self.assertNotIn("Prumo_CtxEsbocoNaFace", it)
        self.assertIn("Prumo_CtxArredondar", it)

    def test_arestas(self):
        import PrumoContexto
        it = PrumoContexto.itens_para([(self.body, ["Edge1", "Edge2"])])
        self.assertEqual(it[:2], ["Prumo_CtxArredondar", "Prumo_CtxChanfro"])

    def test_operacao_na_arvore(self):
        import PrumoContexto
        self.assertIn("Prumo_Cotas", PrumoContexto.itens_para([(self.pad, [])]))

    def test_nada_selecionado(self):
        import PrumoContexto
        self.assertEqual(PrumoContexto.itens_para([]), [])

    def test_tem_peca_rapido_em_montagem_grande(self):
        import time
        import PrumoUtil
        import PrumoContexto
        vazio = self.doc.addObject("App::Part", "SoEsboco")
        vazio.addObject(self.doc.addObject("Sketcher::SketchObject", "EsbSolto"))
        self.assertFalse(PrumoUtil.tem_peca([vazio]))
        grande = self.doc.addObject("App::Part", "Grande")
        caixa = self.doc.addObject("Part::Box", "Peca")
        lks = []
        for i in range(150):
            lk = self.doc.addObject("App::Link", "Lk%d" % i)
            lk.LinkedObject = caixa
            lks.append(lk)
        grande.addObjects(lks)
        lk_conj = self.doc.addObject("App::Link", "LkGrande")
        lk_conj.LinkedObject = grande
        self.doc.recompute()
        self.assertTrue(PrumoUtil.tem_peca([grande]))
        self.assertTrue(PrumoUtil.tem_peca([lk_conj]))
        t0 = time.time()
        for _ in range(20):
            PrumoContexto.itens_para([(grande, [])])
        self.assertLess((time.time() - t0) / 20, 0.05)
        self.assertIn("Prumo_Massa", PrumoContexto.itens_para([(grande, [])]))

    def test_manipulador_gera_insercoes(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoContexto
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.sk)
        ops = PrumoContexto.Manipulador().modifyContextMenu("View")
        FreeCADGui.Selection.clearSelection()
        self.assertTrue(ops)
        self.assertTrue(all(o["menuItem"] == "Std_ViewFitAll" for o in ops))
        self.assertEqual(ops[0]["insert"], "Prumo_CtxExtrudar")

    def test_comandos_registrados(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoContexto
        todos = set(FreeCADGui.Command.listAll())
        for c in list(PrumoContexto.ACOES) + ["Prumo_Cotas", "Prumo_Massa"]:
            self.assertIn(c, todos)

    def test_acao_extrudar_pelo_menu(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        # esboço solto no corpo -> "Extrudar" cria a extrusão
        sk3 = esboco_retangulo(self.body, 5, 5, nome="SketchCtx")
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(sk3)
        antes = len(self.body.Group)
        FreeCADGui.runCommand("Prumo_CtxExtrudar", 0)
        try:
            FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        self.doc.recompute()
        novos = [o for o in self.body.Group if o.TypeId == "PartDesign::Pad" and o.Profile and
                 o.Profile[0] == sk3]
        self.assertTrue(novos, "a extrusão não foi criada (%d -> %d)" % (antes, len(self.body.Group)))


# ======================================================================= lista de materiais
class T14ListaMateriais(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteLM")

    def tearDown(self):
        fechar(self.doc)

    def test_repetidas_contam_quantidade(self):
        import PrumoBOM
        b = self.doc.addObject("Part::Box", "Placa")
        b.Length, b.Width, b.Height = 100, 50, 6
        lk1 = self.doc.addObject("App::Link", "L1")
        lk1.LinkedObject = b
        lk2 = self.doc.addObject("App::Link", "L2")
        lk2.LinkedObject = b
        c = self.doc.addObject("Part::Cylinder", "Pino")
        self.doc.recompute()
        linhas = PrumoBOM.coletar([b, lk1, lk2, c], 7850)
        self.assertEqual(len(linhas), 2)
        placa = [l for l in linhas if l.denominacao == "Placa"][0]
        self.assertEqual(placa.qtd, 3)
        self.assertEqual(placa.dimensoes, "100 × 50 × 6")
        self.assertAlmostEqual(placa.massa, 100 * 50 * 6 * 7850e-9, places=9)
        self.assertAlmostEqual(placa.massa_total, 3 * placa.massa, places=9)

    def test_planilha_e_total(self):
        import PrumoBOM
        b = self.doc.addObject("Part::Box", "Bloco")
        self.doc.recompute()
        linhas = PrumoBOM.coletar([b], 1000)
        sh = PrumoBOM.gravar_planilha(self.doc, linhas)
        self.assertEqual(sh.get("A1"), "Item")
        self.assertEqual(sh.get("C1"), "Código")
        self.assertEqual(sh.get("D2"), "Bloco")
        self.assertEqual(sh.get("G3"), "Total")
        self.assertEqual(sh.get("H3"), "0,001")
        # atualizar não duplica
        sh2 = PrumoBOM.gravar_planilha(self.doc, linhas)
        self.assertIs(sh, sh2)
        self.assertEqual(len([o for o in self.doc.Objects if o.TypeId == "Spreadsheet::Sheet"]), 1)

    def test_espelho_conta_original_e_corte_nao(self):
        import PrumoBOM
        grupo = self.doc.addObject("App::Part", "Conjunto")
        b = self.doc.addObject("Part::Box", "Suporte")
        m = self.doc.addObject("Part::Mirroring", "SuporteEspelhado")
        m.Source = b
        m.Normal = FreeCAD.Vector(1, 0, 0)
        m.Base = FreeCAD.Vector(-5, 0, 0)
        c1 = self.doc.addObject("Part::Box", "Bruto")
        c2 = self.doc.addObject("Part::Cylinder", "Ferramenta")
        cut = self.doc.addObject("Part::Cut", "Usinado")
        cut.Base, cut.Tool = c1, c2
        for o in (b, m, c1, c2, cut):
            grupo.addObject(o)
        self.doc.recompute()
        nomes = sorted(l.denominacao for l in PrumoBOM.coletar([grupo], 7850))
        self.assertEqual(nomes, sorted(["Suporte", "SuporteEspelhado", "Usinado"]))
        # original oculto (ex.: clone que substitui a peça): não conta
        b.Visibility = False
        nomes = sorted(l.denominacao for l in PrumoBOM.coletar([grupo], 7850))
        self.assertEqual(nomes, sorted(["SuporteEspelhado", "Usinado"]))

    def test_peca_selecionada_dentro_de_parte_usa_posicao_global(self):
        import PrumoUtil
        part = self.doc.addObject("App::Part", "Conj")
        part.Placement.Base = FreeCAD.Vector(1000, 0, 0)
        b = self.doc.addObject("Part::Box", "Caixa")
        part.addObject(b)
        self.doc.recompute()
        (_o, sh), = PrumoUtil.pecas([b])
        self.assertAlmostEqual(sh.BoundBox.XMin, 1000.0, places=6)
        (_o, sh), = PrumoUtil.pecas([part])
        self.assertAlmostEqual(sh.BoundBox.XMin, 1000.0, places=6)

    def test_montagem_com_parte(self):
        import PrumoBOM
        part = self.doc.addObject("App::Part", "Conjunto")
        body, sk, pad = bloco_simples(self.doc)
        part.addObject(body)
        cx = self.doc.addObject("Part::Box", "Tampa")
        part.addObject(cx)
        self.doc.recompute()
        linhas = PrumoBOM.coletar([part], 7850)
        nomes = sorted(l.denominacao for l in linhas)
        self.assertEqual(nomes, sorted([body.Label, "Tampa"]))

    def test_montagem_do_freecad_com_vinculos(self):
        import PrumoBOM
        import PrumoMassa
        try:
            asm = self.doc.addObject("Assembly::AssemblyObject", "Montagem")
        except Exception:
            self.skipTest("bancada de montagem indisponível")
        try:
            juntas = self.doc.addObject("Assembly::JointGroup", "Juntas")
            asm.addObject(juntas)
        except Exception:
            pass
        peca = self.doc.addObject("Part::Box", "Bucha")
        peca.Length = peca.Width = peca.Height = 10
        for i in range(3):
            lk = self.doc.addObject("App::Link", "Bucha%d" % i)
            lk.LinkedObject = peca
            lk.Placement.Base = FreeCAD.Vector(20 * i, 0, 0)
            asm.addObject(lk)
        self.doc.recompute()
        linhas = PrumoBOM.coletar([asm], 7850)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0].qtd, 3)
        r = PrumoMassa.calcular([asm], 7850)
        self.assertAlmostEqual(r.volume, 3000, places=3)
        self.assertAlmostEqual(r.cg.x, 25, places=5)

    def test_inserir_na_folha(self):
        if "TechDraw" not in FreeCAD.listDocuments() and not hasattr(FreeCAD, "GuiUp"):
            pass
        import PrumoBOM
        try:
            import TechDraw  # noqa: F401
        except ImportError:
            self.skipTest("TechDraw indisponível")
        b = self.doc.addObject("Part::Box", "Bloco")
        page = self.doc.addObject("TechDraw::DrawPage", "Page")
        tpl = self.doc.addObject("TechDraw::DrawSVGTemplate", "Template")
        import glob
        modelos = glob.glob(os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates", "**",
                                         "*A3*Landscape*.svg"), recursive=True)
        if modelos:
            tpl.Template = modelos[0]
        page.Template = tpl
        self.doc.recompute()
        linhas = PrumoBOM.coletar([b], 7850)
        sh = PrumoBOM.gravar_planilha(self.doc, linhas)
        v = PrumoBOM.inserir_na_folha(page, sh, len(linhas))
        self.assertIn(v, page.Views)
        self.assertEqual(v.CellEnd, "I3")
        v2 = PrumoBOM.inserir_na_folha(page, sh, len(linhas))
        self.assertIs(v, v2)

    def test_tabela_na_folha_abnt_acima_da_legenda(self):
        try:
            import TechDraw  # noqa: F401
        except ImportError:
            self.skipTest("TechDraw indisponível")
        import PrumoBOM
        import PrumoFolhas
        objs = []
        for i in range(5):
            b = self.doc.addObject("Part::Box", "Placa%d" % i)
            b.Length = 100 + i
            objs.append(b)
        self.doc.recompute()
        linhas = PrumoBOM.coletar(objs, 7850)
        sh = PrumoBOM.gravar_planilha(self.doc, linhas)
        page = PrumoFolhas.nova_folha(self.doc, "A3", "NBR16752", False, {}, objs[:1], None)
        v = PrumoBOM.inserir_na_folha(page, sh, len(linhas))
        e, d, sup, inf = PrumoBOM.margens_da_folha(page)
        self.assertEqual((e, d, sup, inf), (20.0, 10.0, 10.0, 10.0))
        h_leg = PrumoBOM.altura_legenda(page)
        self.assertGreater(h_leg, 30)
        w, h = PrumoBOM.tamanho_tabela(sh, len(linhas), v.Scale)
        # linha de 5 mm na folha e tabela mais estreita que a legenda (180 mm)
        self.assertAlmostEqual(h, 5.0 * (len(linhas) + 2), places=6)
        self.assertLess(w, 180.0)
        # alinhada à direita do quadro, logo acima da legenda
        self.assertAlmostEqual(v.X.Value + w / 2.0, 420.0 - d, places=6)
        self.assertAlmostEqual(v.Y.Value - h / 2.0, inf + h_leg + 3.0, places=6)


# ======================================================================= folhas ABNT
class T15FolhasABNT(unittest.TestCase):
    MEDIDAS = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210)}

    def setUp(self):
        self.doc = novo_doc("PrumoTesteFolhas")

    def tearDown(self):
        fechar(self.doc)

    def _svg(self, caminho):
        import xml.etree.ElementTree as ET
        return ET.parse(caminho).getroot()

    def test_doze_modelos(self):
        import PrumoFolhas
        self.assertEqual(len(PrumoFolhas.lista_modelos()), 12)

    def test_dimensoes_das_folhas(self):
        import PrumoFolhas
        for norma in PrumoFolhas.NORMAS:
            for f, (w, h) in self.MEDIDAS.items():
                for retrato in ((True, False) if f == "A4" else (False,)):
                    r = self._svg(PrumoFolhas.arquivo(f, norma, retrato))
                    ww, hh = (h, w) if retrato else (w, h)
                    self.assertEqual(r.get("width"), "%dmm" % ww, (f, norma, retrato))
                    self.assertEqual(r.get("height"), "%dmm" % hh)
                    self.assertEqual(r.get("viewBox"), "0 0 %d %d" % (ww, hh))

    def _quadro(self, caminho):
        r = self._svg(caminho)
        for el in r.iter():
            if el.get("id") == "quadro":
                return (float(el.get("x")), float(el.get("y")), float(el.get("width")),
                        float(el.get("height")), el.get("style"))
        return None

    def test_margens_nbr10068(self):
        import PrumoFolhas
        esperado = {"A0": (25, 10, 1.4), "A1": (25, 10, 1.0), "A2": (25, 7, 0.7), "A3": (25, 7, 0.5),
                    "A4": (25, 7, 0.5)}
        for f, (esq, outra, esp) in esperado.items():
            w, h = self.MEDIDAS[f]
            x, y, qw, qh, est = self._quadro(PrumoFolhas.arquivo(f, "NBR10068", False))
            self.assertAlmostEqual(x, esq)
            self.assertAlmostEqual(y, outra)
            self.assertAlmostEqual(w - (x + qw), outra)
            self.assertAlmostEqual(h - (y + qh), outra)
            self.assertIn("stroke-width:%s" % ("%g" % esp), est)

    def test_margens_nbr16752(self):
        import PrumoFolhas
        for f, (w, h) in self.MEDIDAS.items():
            x, y, qw, qh, est = self._quadro(PrumoFolhas.arquivo(f, "NBR16752", False))
            self.assertEqual((x, y, w - (x + qw), h - (y + qh)), (20, 10, 10, 10))
            self.assertIn("stroke-width:0.7", est)

    def test_legenda_tem_todos_os_campos(self):
        import PrumoFolhas
        ns = "{https://www.freecad.org/wiki/index.php?title=Svg_Namespace}editable"
        for c in PrumoFolhas.lista_modelos():
            r = self._svg(c)
            campos = {el.get(ns) for el in r.iter() if el.get(ns)}
            self.assertEqual(campos, set(PrumoFolhas.CAMPOS), c)

    def test_largura_da_legenda(self):
        import PrumoFolhas
        for norma, larguras in (("NBR16752", {f: 180 for f in self.MEDIDAS}),
                                ("NBR10068", {"A0": 175, "A1": 175, "A2": 178, "A3": 178, "A4": 178})):
            for f, larg in larguras.items():
                r = self._svg(PrumoFolhas.arquivo(f, norma, f == "A4"))
                leg = None
                for el in r.iter():
                    if el.get("id") == "legenda":
                        leg = list(el)[0]
                self.assertAlmostEqual(float(leg.get("width")), larg, msg=(f, norma))

    def test_a4_retrato_cabe_na_largura(self):
        import PrumoFolhas
        for norma in PrumoFolhas.NORMAS:
            x, y, qw, qh, est = self._quadro(PrumoFolhas.arquivo("A4", norma, True))
            r = self._svg(PrumoFolhas.arquivo("A4", norma, True))
            leg = [list(el)[0] for el in r.iter() if el.get("id") == "legenda"][0]
            self.assertLessEqual(float(leg.get("width")), qw + 1e-9)

    def test_nova_folha_preenche_legenda(self):
        import PrumoFolhas
        try:
            import TechDraw  # noqa: F401
        except ImportError:
            self.skipTest("TechDraw indisponível")
        page = PrumoFolhas.nova_folha(self.doc, "A3", campos={"titulo": "Suporte", "numero": "PR-001",
                                                              "art": "123"})
        et = page.Template.EditableTexts
        self.assertEqual(et["titulo"], "Suporte")
        self.assertEqual(et["numero"], "PR-001")
        self.assertEqual(et["formato"], "A3")
        self.assertRegex(et["data"], r"^\d{2}/\d{2}/\d{4}$")
        self.assertEqual(float(page.Template.Width), 420.0)

    def test_nova_folha_com_vistas_no_primeiro_diedro(self):
        import PrumoFolhas
        try:
            import TechDraw  # noqa: F401
        except ImportError:
            self.skipTest("TechDraw indisponível")
        b = self.doc.addObject("Part::Box", "Bloco")
        b.Length, b.Width, b.Height = 300, 120, 80
        self.doc.recompute()
        page = PrumoFolhas.nova_folha(self.doc, "A3", objs=[b])
        grupos = [v for v in page.Views if v.TypeId == "TechDraw::DrawProjGroup"]
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0].ProjectionType, "First angle")
        self.assertLessEqual(page.Scale, 1.0)
        self.assertIn(page.Scale, PrumoFolhas.ESCALAS_NORMAIS)
        self.assertEqual(page.Template.EditableTexts["escala"], PrumoFolhas._texto_escala(page.Scale))
        self.assertIn("massa", page.Template.EditableTexts)
        self.assertTrue(page.Template.EditableTexts["massa"])

    def test_texto_de_escala(self):
        import PrumoFolhas
        self.assertEqual(PrumoFolhas._texto_escala(1), "1:1")
        self.assertEqual(PrumoFolhas._texto_escala(0.5), "1:2")
        self.assertEqual(PrumoFolhas._texto_escala(0.4), "1:2,5")
        self.assertEqual(PrumoFolhas._texto_escala(2), "2:1")
        # só a série 1-2-5
        for e in PrumoFolhas.ESCALAS_NORMAIS:
            n = e if e >= 1 else 1.0 / e
            m = n / 10 ** math.floor(math.log10(n) + 1e-9)
            self.assertTrue(any(abs(m - k) < 1e-9 for k in (1, 2, 5)), e)

    def test_quadriculas_partem_do_centro(self):
        import re
        import PrumoFolhas
        for fmt_, ret, nx, ny in (("A3", False, 8, 6), ("A4", True, 4, 6), ("A0", False, 24, 16), ("A1", False, 16, 12), ("A2", False, 12, 8)):
            caminho = PrumoFolhas.arquivo(fmt_, "NBR16752", ret)
            txt = open(caminho, encoding="utf-8").read()
            larg = float(re.search(r'width="([\d.]+)mm"', txt).group(1))
            g = re.search(r'<g id="quadriculas".*?</g>', txt, re.S).group(0)
            xs = sorted({float(v) for v in re.findall(r'M ([\d.]+),[\d.]+ V', g)})
            ys = sorted({float(v) for v in re.findall(r'M [\d.]+,([\d.]+) H', g)})
            self.assertIn(larg / 2.0, xs, fmt_)
            self.assertEqual(len(xs) + 1, nx, fmt_)
            self.assertEqual(len(ys) + 1, ny, fmt_)
            passos = {round(b - a, 6) for a, b in zip(xs, xs[1:])}
            self.assertEqual(passos, {50.0}, fmt_)

    def test_preferencia_de_modelo_padrao(self):
        import PrumoFolhas
        f = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Files")
        antes = f.GetString("TemplateFile", "")
        try:
            PrumoFolhas.aplicar_preferencias(forcar=True)
            self.assertEqual(f.GetString("TemplateFile"), PrumoFolhas.arquivo("A3"))
        finally:
            if antes:
                f.SetString("TemplateFile", antes)


# ======================================================================= perfis e estruturas
def esboco_linhas(doc, pontos_pares, plano="XY", nome="Esqueleto"):
    """Esboço solto com segmentos [(p1, p2), ...] (coordenadas 2D do esboço)."""
    import Part
    sk = doc.addObject("Sketcher::SketchObject", nome)
    if plano == "XZ":
        sk.Placement = FreeCAD.Placement(FreeCAD.Vector(), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))
    for a, b in pontos_pares:
        sk.addGeometry(Part.LineSegment(FreeCAD.Vector(a[0], a[1], 0), FreeCAD.Vector(b[0], b[1], 0)))
    doc.recompute()
    return sk


class T16Perfis(unittest.TestCase):
    def test_biblioteca_carrega(self):
        import PrumoPerfis
        ids = [f["id"] for f in PrumoPerfis.familias()]
        for fid in ("W", "HP", "U", "I", "L", "TUBO", "TQ"):
            self.assertIn(fid, ids)
        self.assertGreaterEqual(len(PrumoPerfis.nomes("W")), 70)

    def test_valores_de_catalogo_do_w150(self):
        import PrumoPerfis
        it = PrumoPerfis.perfil("W 150 x 13,0")
        self.assertEqual((it["d"], it["bf"], it["tw"], it["tf"]), (148.0, 100.0, 4.3, 4.9))
        self.assertEqual(it["status"], "confirmado")

    def test_area_desenhada_coerente_com_a_massa(self):
        """Seção sem raios: área um pouco menor que a do catálogo (massa/0,785), nunca maior."""
        import PrumoPerfis
        for f in PrumoPerfis.familias():
            for it in f["itens"]:
                a = PrumoPerfis.area_secao(it)
                a_cat = it["massa"] / 7850.0 * 1e6
                self.assertGreater(a, 0, it["nome"])
                self.assertLess(a, a_cat * 1.06, it["nome"])
                self.assertGreater(a, a_cat * 0.85, it["nome"])

    def test_face_valida_para_todos(self):
        import PrumoPerfis
        for f in PrumoPerfis.familias():
            for it in f["itens"][:6]:
                fc = PrumoPerfis.face(it, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0))
                self.assertTrue(fc.isValid(), it["nome"])
                self.assertAlmostEqual(fc.Area, PrumoPerfis.area_secao(it), delta=1e-6 * fc.Area + 1e-6)

    def test_aviso_de_dado_a_conferir(self):
        import PrumoPerfis
        it = PrumoPerfis.perfil("W 150 x 13,0")
        self.assertIn("catálogo", PrumoPerfis.descricao_status(it))
        u = [x for x in PrumoPerfis.familia("U")["itens"] if x["status"] != "confirmado"][0]
        self.assertIn("CONFERIR", PrumoPerfis.descricao_status(u))


class T17Estrutura(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteEstrutura")

    def tearDown(self):
        fechar(self.doc)

    def _quadro(self, plano="XZ", a=1000.0, b=600.0, perfil="W 150 x 13,0", uniao="Meia-esquadria"):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (a, 0)), ((a, 0), (a, b)), ((a, b), (0, b)), ((0, b), (0, 0))], plano)
        est = PrumoEstrutura.criar(self.doc, sk, perfil, uniao=uniao)
        return sk, est, PrumoEstrutura.barras_de(est)

    def test_quatro_barras_validas(self):
        sk, est, bs = self._quadro()
        self.assertEqual(len(bs), 4)
        for b in bs:
            self.assertTrue(b.Shape.isValid(), b.Label)
            self.assertEqual(len(b.Shape.Solids), 1)

    def test_meia_esquadria_45_graus_e_comprimento(self):
        sk, est, bs = self._quadro()
        for b in bs:
            self.assertAlmostEqual(b.CorteInicio.Value, 45.0, places=4)
            self.assertAlmostEqual(b.CorteFim.Value, 45.0, places=4)
        # pórtico vertical: altura do perfil no plano -> comprimento externo = L + d
        horiz = [b for b in bs if b.Indice in (0, 2)][0]
        self.assertAlmostEqual(horiz.ComprimentoCorte.Value, 1000.0 + 148.0, places=3)

    def test_barras_nao_se_sobrepoem(self):
        sk, est, bs = self._quadro()
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                inter = bs[i].Shape.common(bs[j].Shape)
                self.assertLess(inter.Volume, 1e-3, (bs[i].Label, bs[j].Label))

    def test_volume_total_coerente(self):
        import PrumoPerfis
        sk, est, bs = self._quadro()
        it = PrumoPerfis.perfil("W 150 x 13,0")
        area = PrumoPerfis.area_secao(it)
        perim = 2 * (1000 + 600)
        vol = sum(b.Shape.Volume for b in bs)
        # meia-esquadria: volume = área × perímetro na linha de centro
        self.assertAlmostEqual(vol / (area * perim), 1.0, places=4)

    def test_massa_pelo_catalogo(self):
        sk, est, bs = self._quadro()
        b = bs[0]
        self.assertAlmostEqual(b.Massa, 13.0 * b.ComprimentoCorte.Value / 1000.0, places=6)

    def test_plataforma_horizontal_perfil_em_pe(self):
        sk, est, bs = self._quadro(plano="XY")
        bb = bs[0].Shape.BoundBox
        self.assertAlmostEqual(bb.ZLength, 148.0, places=3)   # altura do W na vertical

    def test_uniao_de_topo_sem_sobreposicao(self):
        sk, est, bs = self._quadro(uniao="Topo")
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                self.assertLess(bs[i].Shape.common(bs[j].Shape).Volume, 1e-3)
        cortes = [b.CorteInicio.Value for b in bs] + [b.CorteFim.Value for b in bs]
        self.assertTrue(all(abs(c) < 1e-6 for c in cortes))

    def test_uniao_de_topo_corte_reto_e_comprimentos(self):
        import PrumoPerfis
        sk, est, bs = self._quadro(uniao="Topo")
        it = PrumoPerfis.perfil("W 150 x 13,0")
        d = it["d"]
        por_indice = {b.Indice: b for b in bs}
        # 0 passa nos dois cantos; 1 e 2 passam num e encostam no outro; 3 encosta nos dois
        self.assertAlmostEqual(por_indice[0].ComprimentoCorte.Value, 1000.0 + d, places=3)
        self.assertAlmostEqual(por_indice[1].ComprimentoCorte.Value, 600.0, places=3)
        self.assertAlmostEqual(por_indice[2].ComprimentoCorte.Value, 1000.0, places=3)
        self.assertAlmostEqual(por_indice[3].ComprimentoCorte.Value, 600.0 - d, places=3)
        # corte reto: cada barra é um prisma da seção (12 faces laterais + 2 topos), sem degraus
        for b in bs:
            self.assertEqual(len(b.Shape.Faces), 14, b.Label)
            self.assertAlmostEqual(b.Shape.Volume, PrumoPerfis.area_secao(it) * b.ComprimentoCorte.Value,
                                   delta=1e-6 * b.Shape.Volume)
        # o quadro fecha: volume total = área × perímetro na linha de centro
        vol = sum(b.Shape.Volume for b in bs)
        self.assertAlmostEqual(vol / (PrumoPerfis.area_secao(it) * 3200.0), 1.0, places=6)
        # a barra que encosta toca a face da que passa (folga zero)
        self.assertLess(por_indice[3].Shape.distToShape(por_indice[0].Shape)[0], 1e-6)

    def test_ligacao_em_T(self):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((500, 0), (500, 400))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, "W 200 x 15,0" if PrumoPerfis_tem("W 200 x 15,0") else "W 150 x 13,0")
        bs = PrumoEstrutura.barras_de(est)
        self.assertLess(bs[0].Shape.common(bs[1].Shape).Volume, 1e-3)
        lig = PrumoEstrutura.ligacoes(PrumoEstrutura.arestas(sk), 1)
        self.assertEqual(lig[0].tipo, "topo_T")
        import PrumoPerfis
        d = PrumoPerfis.perfil(bs[0].Perfil)["d"]
        # montante cortado reto na face da mesa superior da viga
        self.assertAlmostEqual(bs[1].ComprimentoCorte.Value, 400.0 - d / 2.0, places=3)
        self.assertEqual(len(bs[1].Shape.Faces), 14)
        self.assertLess(bs[1].Shape.distToShape(bs[0].Shape)[0], 1e-6)

    def test_trocar_perfil_de_uma_barra(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        PrumoEstrutura.trocar_perfil([bs[1]], "L 50 x 5" if PrumoPerfis_tem("L 50 x 5") else
                                     PrumoPerfis_primeiro("L"))
        self.assertTrue(bs[1].Perfil.startswith("L"))
        self.assertEqual(bs[0].Perfil, "W 150 x 13,0")
        self.assertTrue(bs[1].Shape.isValid())

    def test_lista_de_corte(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        linhas = PrumoEstrutura.lista_de_corte([est])
        self.assertEqual(len(linhas), 2)            # 2 × 1.148 e 2 × 748
        self.assertEqual(sorted(l[4] for l in linhas), [2, 2])
        sh = PrumoEstrutura.gravar_lista_de_corte(self.doc, linhas)
        self.assertEqual(sh.get("B2"), "W 150 x 13,0")
        self.assertIn("m", sh.get("C4"))

    def test_lista_de_materiais_agrupa_barras(self):
        import PrumoBOM
        sk, est, bs = self._quadro()
        linhas = PrumoBOM.coletar([est])
        self.assertEqual(len(linhas), 2)
        self.assertTrue(all(l.denominacao.startswith("Barra W 150") for l in linhas))
        self.assertAlmostEqual(sum(l.massa_total for l in linhas), sum(b.Massa for b in bs), places=6)

    def test_editar_esqueleto_recalcula(self):
        sk, est, bs = self._quadro()
        import Sketcher
        sk.moveGeometry(0, 2, FreeCAD.Vector(1200, 0, 0))
        sk.moveGeometry(1, 1, FreeCAD.Vector(1200, 0, 0))
        self.doc.recompute()
        self.assertGreater(bs[0].ComprimentoCorte.Value, 1148.0)

    def test_esqueleto_dentro_de_body_usa_posicao_global(self):
        import PrumoEstrutura
        import Part
        body = self.doc.addObject("PartDesign::Body", "Corpo")
        body.Placement = FreeCAD.Placement(FreeCAD.Vector(5000, 0, 0), FreeCAD.Rotation())
        sk = self.doc.addObject("Sketcher::SketchObject", "EsqNoCorpo")
        body.addObject(sk)
        sk.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1000, 0, 0)))
        self.doc.recompute()
        est = PrumoEstrutura.criar(self.doc, sk, "W 150 x 13,0")
        self.assertEqual(est.getTypeIdOfProperty("Esqueleto"), "App::PropertyLinkGlobal")
        b = PrumoEstrutura.barras_de(est)[0]
        self.assertEqual(b.getTypeIdOfProperty("Esqueleto"), "App::PropertyLinkGlobal")
        self.assertAlmostEqual(b.Shape.BoundBox.XMin, 5000.0, places=3)
        self.assertAlmostEqual(b.Shape.BoundBox.XMax, 6000.0, places=3)

    def test_migra_vinculo_antigo(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        # simula arquivo antigo: PropertyLink comum
        est.removeProperty("Esqueleto")
        est.addProperty("App::PropertyLink", "Esqueleto", "Estrutura", "")
        est.Esqueleto = sk
        est.Proxy.onDocumentRestored(est)
        self.assertEqual(est.getTypeIdOfProperty("Esqueleto"), "App::PropertyLinkGlobal")
        self.assertIs(est.Esqueleto, sk)

    def test_atualizar_com_barra_selecionada(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        self.assertIs(PrumoEstrutura.estrutura_de(bs[2]), est)
        self.assertIs(PrumoEstrutura.estrutura_de(est), est)
        self.assertIsNone(PrumoEstrutura.estrutura_de(sk))
        if FreeCAD.GuiUp:
            import FreeCADGui
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(bs[2])
            FreeCADGui.runCommand("Prumo_AtualizarEstrutura", 0)
            FreeCADGui.Selection.clearSelection()
        else:
            PrumoEstrutura.atualizar(est)
        bs2 = PrumoEstrutura.barras_de(est)
        self.assertEqual(len(bs2), 4)
        barras_doc = [o for o in self.doc.Objects if PrumoEstrutura.eh_barra(o)]
        self.assertEqual(len(barras_doc), 4)          # nenhuma barra órfã
        self.assertTrue(all(b.Estrutura is est for b in barras_doc))

    def test_trocar_perfil_de_barra_sem_linha(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        bs[3].Indice = 9  # linha que não existe mais
        PrumoEstrutura.trocar_perfil([bs[3], bs[0]], "W 150 x 18,0" if PrumoPerfis_tem("W 150 x 18,0")
                                     else PrumoPerfis_primeiro("W"))
        self.assertEqual(len(est.PerfisIndividuais), 4)

    def test_tubo_e_metalon(self):
        import PrumoEstrutura
        import PrumoPerfis
        for fid in ("TUBO", "TQ"):
            sk = esboco_linhas(self.doc, [((0, 0), (500, 0)), ((500, 0), (500, 500))], "XZ", "Esq" + fid)
            est = PrumoEstrutura.criar(self.doc, sk, PrumoPerfis.nomes(fid)[5])
            for b in PrumoEstrutura.barras_de(est):
                self.assertTrue(b.Shape.isValid())
                self.assertGreater(b.Shape.Volume, 0)

    def test_salvar_e_reabrir(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        caminho = os.path.join(tempfile.gettempdir(), "prumo_teste_estrutura.FCStd")
        self.doc.saveAs(caminho)
        nome = self.doc.Name
        FreeCAD.closeDocument(nome)
        self.doc = FreeCAD.openDocument(caminho)
        est2 = [o for o in self.doc.Objects if "Esqueleto" in o.PropertiesList and o.TypeId.startswith("App::")][0]
        bs2 = PrumoEstrutura.barras_de(est2)
        self.assertEqual(len(bs2), 4)
        bs2[0].touch()
        self.doc.recompute()
        self.assertTrue(bs2[0].Shape.isValid())
        os.remove(caminho)


# ======================================================================= chapa metálica
class T18ChapaMetalica(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteChapa")

    def tearDown(self):
        fechar(self.doc)

    def _base(self, a=60.0, b=40.0, esp=2.0, raio=2.0, comp=100.0):
        import Part
        import SheetMetalBaseCmd
        sk = self.doc.addObject("Sketcher::SketchObject", "PerfilChapa")
        sk.Placement = FreeCAD.Placement(FreeCAD.Vector(), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))
        sk.addGeometry(Part.LineSegment(FreeCAD.Vector(0, b, 0), FreeCAD.Vector(0, 0, 0)))
        sk.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(a, 0, 0)))
        self.doc.recompute()
        base = self.doc.addObject("Part::FeaturePython", "BaseBend")
        SheetMetalBaseCmd.SMBaseBend(base, sk)
        base.Thickness = esp
        base.Radius = raio
        base.Length = comp
        self.doc.recompute()
        return sk, base

    def _desdobrar(self, base, k=None):
        import SheetMetalUnfoldCmd
        maior = max(range(len(base.Shape.Faces)), key=lambda i: base.Shape.Faces[i].Area)
        un = self.doc.addObject("Part::FeaturePython", "Unfold")
        SheetMetalUnfoldCmd.SMUnfold(un, base, ["Face%d" % (maior + 1)])
        if k is not None:
            un.KFactor = k
            if "ManualRecompute" in un.PropertiesList:
                un.ManualRecompute = False
            for p in ("MaterialSheet", "UseKFactorTable"):
                if p in un.PropertiesList and un.getTypeIdOfProperty(p) == "App::PropertyBool":
                    setattr(un, p, False)
        self.doc.recompute()
        return un

    def test_parede_com_dobra(self):
        sk, base = self._base()
        self.assertTrue(base.Shape.isValid())
        self.assertEqual(len(base.Shape.Solids), 1)
        cil = [f for f in base.Shape.Faces if f.Surface.__class__.__name__ == "Cylinder"]
        self.assertEqual(len(cil), 2)  # raio interno e externo da dobra

    def test_planificacao(self):
        sk, base = self._base()
        un = self._desdobrar(base)
        sh = un.Shape
        self.assertFalse(sh.isNull())
        bb = sh.BoundBox
        menor = min(bb.XLength, bb.YLength, bb.ZLength)
        self.assertAlmostEqual(menor, 2.0, places=3)        # chapa plana com a espessura
        desenv = max(bb.XLength, bb.YLength, bb.ZLength)
        if abs(desenv - 100.0) < 1e-6:
            desenv = sorted([bb.XLength, bb.YLength, bb.ZLength])[1]
        self.assertGreater(desenv, 60 + 40 - 2 * (2 + 2) - 1)
        self.assertLess(desenv, 60 + 40 + 1)

    def test_comandos_da_chapa(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        atual = FreeCADGui.activeWorkbench().name()
        FreeCADGui.activateWorkbench("SMWorkbench")
        FreeCADGui.activateWorkbench(atual)
        todos = set(FreeCADGui.listCommands())
        for c in ("SheetMetal_AddBase", "SheetMetal_AddWall", "SheetMetal_Unfold", "SheetMetal_AddBend",
                  "SheetMetal_AddCornerRelief", "SheetMetal_FromSolid"):
            self.assertIn(c, todos)


# ======================================================================= vaso de pressão
class T19VasoPressao(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteVaso")

    def tearDown(self):
        fechar(self.doc)

    def test_formulas_do_costado(self):
        import PrumoVaso as V
        c = V.Calculo(1000, 1.0, 138.0, 1.0, 1.5)
        self.assertAlmostEqual(c.t_circ, 501.5 / (138.0 - 0.6), places=9)
        self.assertAlmostEqual(c.t_long, 501.5 / (2 * 138.0 + 0.4), places=9)
        self.assertAlmostEqual(c.t_costado, c.t_circ)

    def test_formulas_dos_tampos(self):
        import PrumoVaso as V
        P, S, E, D = 2.0, 120.0, 0.85, 800.0
        Dc = D + 2 * 3.0
        self.assertAlmostEqual(V.Calculo(D, P, S, E, 3.0, V.TAMPOS[0]).t_tampo, P * Dc / (2 * S * E - 0.2 * P))
        # torisférico padrão: L = raio interno da coroa = diâmetro externo (corroído)
        c = V.Calculo(D, P, S, E, 3.0, V.TAMPOS[1])
        L = D + 2 * (c.t_tampo + 3.0) + 3.0
        self.assertAlmostEqual(c.L_tampo, L)
        self.assertAlmostEqual(c.t_tampo, 0.885 * P * L / (S * E - 0.1 * P))
        self.assertGreater(c.t_tampo, 0.885 * P * Dc / (S * E - 0.1 * P))
        self.assertAlmostEqual(V.Calculo(D, P, S, E, 3.0, V.TAMPOS[2]).t_tampo, P * (Dc / 2) / (2 * S * E - 0.2 * P))

    def test_pmta_inverte_a_espessura(self):
        """Com a espessura exatamente mínima, a PMTA volta à pressão de projeto."""
        import PrumoVaso as V
        for tipo in V.TAMPOS:
            c = V.Calculo(1200, 1.6, 138.0, 0.85, 2.0, tipo)
            mc, mt = c.minimos_com_corrosao()
            self.assertAlmostEqual(c.pmta_costado(mc), 1.6, places=9)
            self.assertAlmostEqual(c.pmta_tampo(mt), 1.6, places=9)

    def test_aviso_fora_do_limite(self):
        import PrumoVaso as V
        c = V.Calculo(500, 60.0, 138.0, 1.0)
        self.assertTrue(any("0,385" in a for a in c.avisos))

    def test_entradas_invalidas(self):
        import PrumoVaso as V
        with self.assertRaises(ValueError):
            V.Calculo(1000, 1.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            V.Calculo(1000, 1.0, 138.0, 1.2)
        with self.assertRaises(ValueError):
            V.Calculo(1000, 1.0, 138.0, 1.0, -1.0)

    def test_denominador_nao_positivo(self):
        import PrumoVaso as V
        # S·E − 0,6·P ≤ 0
        with self.assertRaises(ValueError):
            V.Calculo(1000, 300.0, 138.0, 1.0)
        with self.assertRaises(ValueError):
            V.Calculo(1000, 230.0, 138.0, 1.0)   # exatamente no limite: 138 − 0,6·230 = 0
        # torisférico: 1 − 2k ≤ 0 mesmo com o costado ainda calculável
        with self.assertRaises(ValueError):
            V.Calculo(1000, 80.0, 138.0, 1.0, 0.0, V.TAMPOS[1])

    def test_vaso_com_pressao_impossivel_nao_quebra(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 1000, 300.0, 138.0, 1.0)
        self.assertTrue(any("não realizado" in a for a in v.Avisos))
        self.assertEqual(v.MinimoCostado, 0.0)
        self.assertIn("não realizado", V.memoria(v))

    def test_limites_de_aplicacao(self):
        import PrumoVaso as V
        c = V.Calculo(1000, 100.0, 138.0, 1.0, 0.0, V.TAMPOS[2])
        self.assertTrue(any("0,665" in a for a in c.avisos))
        self.assertTrue(any("0,356" in a for a in c.avisos))
        c = V.Calculo(1000, 0.05, 138.0, 1.0, 0.0, V.TAMPOS[0])
        self.assertTrue(any("0,002" in a for a in c.avisos))
        c = V.Calculo(1000, 1.0, 138.0, 1.0, 0.0, V.TAMPOS[0])
        self.assertEqual(c.avisos, [])

    def test_rotulo_antigo_do_tampo(self):
        import PrumoVaso as V
        self.assertEqual(V.tipo_tampo("Torisférico (L = D, r = 6 %)"), 1)
        self.assertEqual(V.tipo_tampo(V.TAMPOS[0]), 0)
        self.assertEqual(V.tipo_tampo(V.TAMPOS[2]), 2)

    def test_bocal_fora_do_costado(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 2000, 1.0, 138.0, 1.0, 0.0, V.TAMPOS[0],
                    bocais=['2500; 90; Tubo 2" Sch 40; 150', '500; 90; Tubo 2" Sch 40; 150'])
        self.assertTrue(any("fora do costado" in a for a in v.Avisos))
        self.assertTrue(v.Shape.isValid())

    def test_memoria_indica_E_dos_tampos_e_L(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 1000, 1.0, 138.0, 0.85, 1.0, V.TAMPOS[1])
        m = V.memoria(v)
        self.assertIn("E usado nos tampos = 0,85", m)
        self.assertIn("raio interno da coroa", m)

    def test_chapa_acima(self):
        import PrumoVaso as V
        self.assertEqual(V.chapa_acima(5.15), 6.35)
        self.assertEqual(V.chapa_acima(6.35), 6.35)
        self.assertEqual(V.chapa_acima(80.0), 80)

    def test_tampos_validos_e_alturas(self):
        import PrumoVaso as V
        for tipo in V.TAMPOS:
            t = V.tampo(500, 10, tipo)
            self.assertTrue(t.isValid(), tipo)
            self.assertEqual(len(t.Solids), 1)
            self.assertAlmostEqual(t.BoundBox.XLength, V.altura_tampo(500, 10, tipo), places=3)
        # 2:1 → profundidade interna D/4; torisférico padrão → ~0,169·D
        self.assertAlmostEqual(V.altura_tampo(500, 0, V.TAMPOS[0]), 250.0)
        self.assertAlmostEqual(V.altura_tampo(500, 0, V.TAMPOS[1]) / 1000.0, 0.1693, places=3)

    def test_volume_interno(self):
        import PrumoVaso as V
        self.assertAlmostEqual(V.volume_interno(1000, 2000, V.TAMPOS[0]),
                               math.pi * 0.25 * 2 + 2 * (2 / 3.0 * math.pi * 0.25 * 0.25), places=6)
        self.assertAlmostEqual(V.volume_interno(1000, 0, V.TAMPOS[2]), 4 / 3.0 * math.pi * 0.125, places=6)
        tori = (V.volume_interno(1000, 0, V.TAMPOS[1])) / 2
        self.assertAlmostEqual(tori, 0.0809, places=3)   # ≈ 0,0809·D³ para o torisférico padrão

    def test_vaso_completo_com_bocais(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 2000, 1.0, 138.0, 1.0, 1.5, V.TAMPOS[0],
                    bocais=['500; 90; Tubo 2" Sch 40; 150', '1500; 0; Tubo 4" Sch 80; 200'])
        self.assertTrue(v.Shape.isValid())
        self.assertEqual(len(v.Shape.Solids), 1)
        self.assertEqual(list(v.Avisos), [])
        self.assertAlmostEqual(v.MinimoCostado, 501.5 / 137.4 + 1.5, places=6)
        self.assertGreater(v.PMTACostado, 1.0)
        # bocal de 2" passa pelo topo: deve existir furo (face cilíndrica do diâmetro interno do tubo)
        import PrumoPerfis
        it = PrumoPerfis.perfil('Tubo 2" Sch 40')
        ri = it["D"] / 2 - it["esp"]
        self.assertTrue(any(f.Surface.__class__.__name__ == "Cylinder" and abs(f.Surface.Radius - ri) < 1e-6
                            for f in v.Shape.Faces))
        self.assertIn("UG-27", V.memoria(v))

    def test_espessura_adotada_menor_avisa(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 1000, 1.0, 138.0, 1.0, 0.0, V.TAMPOS[2], t_costado=2.0, t_tampo=2.0)
        self.assertTrue(any("costado menor" in a for a in v.Avisos))

    def test_bocal_invalido(self):
        import PrumoVaso as V
        self.assertIsNone(V.interpretar_bocal("500; 90; Tubo 99\" Sch 40; 100"))
        self.assertIsNone(V.interpretar_bocal("500; noventa; Tubo 2\" Sch 40; 100"))
        self.assertIsNotNone(V.interpretar_bocal('500; 90; Tubo 2" Sch 40; 100'))

    def test_sem_tensao_nao_calcula(self):
        import PrumoVaso as V
        v = V.criar(self.doc, 1000, 1000, 1.0, 0.0, 1.0)
        self.assertTrue(v.Shape.isNull())
        self.assertIn("tensão admissível", v.Avisos[0])

    def test_dialogo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoVaso as V
        d = V.DialogoVaso()
        self.assertIn("tensão admissível", d.saida.toPlainText())
        d.S.setValue(138.0)
        self.assertIn("Espessuras mínimas", d.saida.toPlainText())
        d.close()


# ======================================================================= fixadores
class T20Fixadores(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteFixadores")

    def tearDown(self):
        fechar(self.doc)

    def test_tabelas_completas(self):
        import PrumoFixadores as F
        for t in F.TIPOS:
            self.assertEqual(F.diametros(t), ["M3", "M4", "M5", "M6", "M8", "M10", "M12", "M16", "M20", "M24"])

    def test_medidas_de_norma(self):
        import PrumoFixadores as F
        self.assertEqual((F.medidas("sextavado", "M8")["s"], F.medidas("sextavado", "M8")["k"]), (13, 5.3))
        self.assertEqual(F.medidas("allen", "M8")["dk"], 13)
        self.assertEqual(F.medidas("porca", "M8")["m"], 6.8)
        self.assertEqual((F.medidas("arruela", "M8")["d1"], F.medidas("arruela", "M8")["d2"]), (8.4, 16))
        self.assertEqual(F.passo("M8"), 1.25)

    def test_formas_validas_e_dimensoes(self):
        import PrumoFixadores as F
        for t in F.TIPOS:
            for m in F.diametros(t):
                comp = 3 * float(m[1:]) if t in ("sextavado", "allen") else 0
                sh = F.forma(t, m, comp)
                self.assertTrue(sh.isValid(), (t, m))
                self.assertEqual(len(sh.Solids), 1, (t, m))
        sh = F.forma("sextavado", "M10", 40)
        bb = sh.BoundBox
        self.assertAlmostEqual(bb.ZLength, 40 + F.medidas("sextavado", "M10")["k"], places=6)
        self.assertAlmostEqual(min(bb.XLength, bb.YLength), F.medidas("sextavado", "M10")["s"], places=6)
        porca = F.forma("porca", "M12")
        self.assertAlmostEqual(porca.BoundBox.ZLength, F.medidas("porca", "M12")["m"], places=6)

    def test_inserir_no_furo(self):
        import PrumoFixadores as F
        import Part
        b = self.doc.addObject("Part::Box", "Chapa")
        b.Length, b.Width, b.Height = 100, 100, 12
        c = self.doc.addObject("Part::Cylinder", "Furo")
        c.Radius, c.Height = 4.5, 12
        c.Placement.Base = FreeCAD.Vector(50, 50, 0)
        cut = self.doc.addObject("Part::Cut", "ChapaFurada")
        cut.Base, cut.Tool = b, c
        self.doc.recompute()
        aresta = [i for i, e in enumerate(cut.Shape.Edges, 1) if e.Curve.__class__.__name__ == "Circle"
                  and abs(e.Vertexes[0].Point.z - 12) < 1e-6][0]
        pl, diam = F.posicao_no_furo(cut, "Edge%d" % aresta)
        self.assertAlmostEqual(diam, 9.0, places=6)
        self.assertEqual(F.diametro_para_furo(diam), "M8")
        o = F.criar(self.doc, "sextavado", "M8", 30, pl)
        bb = o.Shape.BoundBox
        self.assertAlmostEqual(bb.ZMin, 12 - 30, places=6)   # corpo entra na chapa
        self.assertAlmostEqual(bb.ZMax, 12 + 5.3, places=6)  # cabeça apoiada na face de cima
        self.assertEqual(o.Denominacao, "Parafuso cabeça sextavada ISO 4017 M8 × 30")

    def test_furo_dentro_de_parte_usa_posicao_global(self):
        import PrumoFixadores as F
        part = self.doc.addObject("App::Part", "Conj")
        part.Placement.Base = FreeCAD.Vector(0, 0, 500)
        b = self.doc.addObject("Part::Box", "Chapa")
        b.Length, b.Width, b.Height = 100, 100, 12
        c = self.doc.addObject("Part::Cylinder", "Furo")
        c.Radius, c.Height = 4.5, 12
        c.Placement.Base = FreeCAD.Vector(50, 50, 0)
        cut = self.doc.addObject("Part::Cut", "ChapaFurada")
        cut.Base, cut.Tool = b, c
        part.addObject(cut)
        self.doc.recompute()
        aresta = [i for i, e in enumerate(cut.Shape.Edges, 1) if e.Curve.__class__.__name__ == "Circle"
                  and abs(e.Vertexes[0].Point.z - 12) < 1e-6][0]
        pl, diam = F.posicao_no_furo(part, "%s.Edge%d" % (cut.Name, aresta))
        self.assertAlmostEqual(diam, 9.0, places=6)
        self.assertAlmostEqual(pl.Base.z, 512.0, places=6)
        self.assertAlmostEqual(pl.Base.x, 50.0, places=6)
        self.assertEqual(F.posicao_no_furo(part, "%s.Face1" % cut.Name), (None, None))

    def test_dialogo_valida_comprimento(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoFixadores as F
        d = F.DialogoFixador("M8")
        for txt, esperado in (("30", 30.0), ("12,5", 12.5), ("abc", None), ("0", None), ("-5", None),
                              ("", None), ("100000", None)):
            d.comp.setEditText(txt)
            self.assertEqual(d.comprimento_valido(), esperado, txt)
        d.tipo.setCurrentIndex(list(F.TIPOS).index("porca"))
        self.assertEqual(d.comprimento_valido(), 0.0)
        d.close()

    def test_lista_de_materiais_agrupa_fixadores(self):
        import PrumoFixadores as F
        import PrumoBOM
        for i in range(4):
            F.criar(self.doc, "sextavado", "M8", 30, FreeCAD.Placement(FreeCAD.Vector(30 * i, 0, 0), FreeCAD.Rotation()))
        F.criar(self.doc, "porca", "M8")
        linhas = PrumoBOM.coletar([o for o in self.doc.Objects])
        par = [l for l in linhas if "M8 × 30" in l.denominacao][0]
        self.assertEqual(par.qtd, 4)
        self.assertEqual(len(linhas), 2)

    def test_comprimento_obrigatorio(self):
        import PrumoFixadores as F
        o = F.criar(self.doc, "allen", "M6", 0)
        self.assertTrue("Invalid" in o.State or o.Shape.isNull())

    def test_dialogo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoFixadores as F
        d = F.DialogoFixador("M10")
        self.assertEqual(d.diam.currentText(), "M10")
        t, m, comp, mat = d.valores()
        self.assertGreater(comp, 0)
        d.tipo.setCurrentIndex(d.tipo.findData("arruela"))
        self.assertFalse(d.comp.isEnabled())
        d.close()


def PrumoPerfis_tem(nome):
    import PrumoPerfis
    return PrumoPerfis.perfil(nome) is not None


def PrumoPerfis_primeiro(fid):
    import PrumoPerfis
    return PrumoPerfis.nomes(fid)[0]


# ======================================================================= estruturas: grupos e cantos
TUBO2 = 'Tubo 2" Sch 40'
TQ50 = "Tubo □ 50 x 50 x 3,00"


def _sem_sobreposicao(caso, bs):
    for x in range(len(bs)):
        for y in range(x + 1, len(bs)):
            caso.assertLess(bs[x].Shape.common(bs[y].Shape).Volume, 1e-3, (bs[x].Label, bs[y].Label))


class T22EstruturaGrupos(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteGrupos")

    def tearDown(self):
        fechar(self.doc)

    def _quadro(self, **kw):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)), ((1000, 600), (0, 600)),
                                      ((0, 600), (0, 0))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, kw.pop("perfil", "W 150 x 13,0"), **kw)
        return sk, est, PrumoEstrutura.barras_de(est)

    def test_grupos_com_perfis_diferentes(self):
        sk, est, bs = self._quadro(grupos_extras=[{"nome": "Montantes", "perfil": TQ50, "arestas": [1, 3]}])
        self.assertEqual([b.Perfil for b in bs], ["W 150 x 13,0", TQ50, "W 150 x 13,0", TQ50])
        for b in bs:
            self.assertTrue(b.Shape.isValid())
            self.assertEqual(len(b.Shape.Solids), 1)
        _sem_sobreposicao(self, bs)
        import PrumoEstrutura
        self.assertEqual(PrumoEstrutura.parametros(est, 1)["nome"], "Montantes")
        self.assertEqual(PrumoEstrutura.grupo_da_barra(est, 0), 0)

    def test_editar_grupos_recalcula(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        PrumoEstrutura.definir_grupos(est, [{"nome": "Topo", "perfil": "W 150 x 18,0", "arestas": [2]}])
        self.doc.recompute()
        self.assertEqual(bs[2].Perfil, "W 150 x 18,0")
        self.assertEqual(bs[0].Perfil, "W 150 x 13,0")
        with self.assertRaises(ValueError):
            PrumoEstrutura.definir_grupos(est, [{"perfil": "Perfil inexistente", "arestas": [0]}])

    def test_troca_individual_vence_o_grupo(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro(grupos_extras=[{"perfil": TQ50, "arestas": [1, 3]}])
        PrumoEstrutura.trocar_perfil([bs[1]], "W 150 x 18,0")
        self.assertEqual(bs[1].Perfil, "W 150 x 18,0")
        self.assertEqual(bs[3].Perfil, TQ50)

    def _linha(self, perfil, fixacao, espelhar=False):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0))], "XY", "Linha" + fixacao.replace(" ", "").replace(".", ""))
        est = PrumoEstrutura.criar(self.doc, sk, perfil, alinhamento=fixacao, espelhar=espelhar)
        return PrumoEstrutura.barras_de(est)[0]

    def test_pontos_de_fixacao(self):
        import PrumoPerfis
        it = PrumoPerfis.perfil("W 150 x 13,0")
        d, bf = it["d"], it["bf"]
        # plataforma (plano XY): altura do perfil em Z, largura em Y
        casos = {"Centro": (-bf / 2, bf / 2, -d / 2, d / 2), "Sup. centro": (-bf / 2, bf / 2, -d, 0),
                 "Inf. centro": (-bf / 2, bf / 2, 0, d)}
        for fx, (y0, y1, z0, z1) in casos.items():
            bb = self._linha("W 150 x 13,0", fx).Shape.BoundBox
            self.assertAlmostEqual(bb.ZMin, z0, places=6, msg=fx)
            self.assertAlmostEqual(bb.ZMax, z1, places=6, msg=fx)
            self.assertAlmostEqual(bb.YLength, bf, places=6, msg=fx)
        # cantos: a linha fica num canto da caixa da seção
        for fx in ("Sup. esquerdo", "Sup. direito", "Inf. esquerdo", "Inf. direito", "Meio esquerdo",
                   "Meio direito"):
            bb = self._linha("W 150 x 13,0", fx).Shape.BoundBox
            self.assertTrue(abs(bb.YMin) < 1e-6 or abs(bb.YMax) < 1e-6, fx)
            if fx.startswith("Meio"):
                self.assertAlmostEqual(bb.ZMin, -d / 2, places=6)
            else:
                self.assertTrue(abs(bb.ZMin) < 1e-6 or abs(bb.ZMax) < 1e-6, fx)
        a = self._linha("W 150 x 13,0", "Sup. esquerdo").Shape.BoundBox
        b = self._linha("W 150 x 13,0", "Sup. direito").Shape.BoundBox
        self.assertAlmostEqual(a.YMin + b.YMax, 0.0, places=6)   # lados opostos
        self.assertGreater(abs(a.YMin - b.YMin), bf - 1e-6)

    def test_centroide_da_cantoneira_sobre_a_linha(self):
        b = self._linha("L 50 x 5", "Centroide")
        cm = b.Shape.Solids[0].CenterOfMass
        self.assertLess(math.hypot(cm.y, cm.z), 1e-3)
        c = self._linha("L 50 x 5", "Centro").Shape.Solids[0].CenterOfMass
        self.assertGreater(math.hypot(c.y, c.z), 1.0)

    def test_espelhar_inverte_a_cantoneira(self):
        a = self._linha("L 50 x 5", "Centro").Shape.Solids[0].CenterOfMass
        b = self._linha("L 50 x 5", "Centro", espelhar=True).Shape.Solids[0].CenterOfMass
        self.assertAlmostEqual(a.y, -b.y, places=6)
        self.assertAlmostEqual(a.z, b.z, places=6)
        self.assertGreater(abs(a.y), 1.0)

    def test_alinhamento_antigo_migra(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        est.removeProperty("Fixacao")
        est.Alinhamento = "Topo"
        est.Proxy.onDocumentRestored(est)
        self.assertEqual(est.Fixacao, "Sup. centro")

    def test_selecao_de_linhas_do_esqueleto(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(sk, ["Edge2", "Edge4"])
        sel = PrumoEstrutura.barras_da_selecao()
        self.assertEqual(sorted(b.Indice for b in sel), [1, 3])
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(est)
        self.assertEqual(len(PrumoEstrutura.barras_da_selecao()), 4)
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(bs[2])
        self.assertEqual(PrumoEstrutura.barras_da_selecao(), [bs[2]])
        FreeCADGui.Selection.clearSelection()


class T23EstruturaCantos(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteCantos")

    def tearDown(self):
        fechar(self.doc)

    def _quadro(self, perfil="W 150 x 13,0", uniao="Topo"):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)), ((1000, 600), (0, 600)),
                                      ((0, 600), (0, 0))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, perfil, uniao=uniao)
        return sk, est, PrumoEstrutura.barras_de(est)

    def test_lista_e_grupos_de_cantos(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        cs = PrumoEstrutura.cantos(est)
        self.assertEqual(len(cs), 4)
        self.assertTrue(all(c.tipo == "esquadria" for c in cs))
        self.assertTrue(all(abs(c.angulo - 90) < 1e-6 for c in cs))
        self.assertEqual(len(PrumoEstrutura.agrupar_cantos(cs)), 1)

    def test_passa_a_vertical(self):
        import PrumoEstrutura
        import PrumoPerfis
        sk, est, bs = self._quadro()
        PrumoEstrutura.aplicar_opcao(est, PrumoEstrutura.cantos(est), PrumoEstrutura.OPCOES_ESQUADRIA[3])
        self.doc.recompute()
        d = PrumoPerfis.perfil("W 150 x 13,0")["d"]
        comps = {b.Indice: b.ComprimentoCorte.Value for b in bs}
        self.assertAlmostEqual(comps[1], 600 + d, places=3)
        self.assertAlmostEqual(comps[3], 600 + d, places=3)
        self.assertAlmostEqual(comps[0], 1000 - d, places=3)
        self.assertAlmostEqual(comps[2], 1000 - d, places=3)
        _sem_sobreposicao(self, bs)
        area = PrumoPerfis.area_secao(PrumoPerfis.perfil("W 150 x 13,0"))
        self.assertAlmostEqual(sum(b.Shape.Volume for b in bs) / (area * 3200), 1.0, places=6)
        # e o contrário
        PrumoEstrutura.aplicar_opcao(est, PrumoEstrutura.cantos(est), PrumoEstrutura.OPCOES_ESQUADRIA[4])
        self.doc.recompute()
        self.assertAlmostEqual(bs[0].ComprimentoCorte.Value, 1000 + d, places=3)
        self.assertAlmostEqual(bs[1].ComprimentoCorte.Value, 600 - d, places=3)

    def test_cantos_misturados(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro(uniao="Meia-esquadria")
        c0 = [c for c in PrumoEstrutura.cantos(est) if {c.i, c.j} == {0, 1}]
        PrumoEstrutura.aplicar_opcao(est, c0, PrumoEstrutura.OPCOES_ESQUADRIA[2])  # passa a 1
        self.doc.recompute()
        for b in bs:
            self.assertTrue(b.Shape.isValid())
        _sem_sobreposicao(self, bs)
        self.assertAlmostEqual(bs[0].CorteFim.Value, 0.0, places=6)
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 45.0, places=6)
        self.assertEqual(PrumoEstrutura.tratamento(est, 1, 0, "esquadria"), "passa:1")
        # gravar duas vezes não duplica
        PrumoEstrutura.aplicar_opcao(est, c0, PrumoEstrutura.OPCOES_ESQUADRIA[2])
        self.assertEqual(len([l for l in est.Cantos if l.startswith("0-1=")]), 1)

    def test_recorte_pelo_contorno_tubo_em_tubo(self):
        import PrumoEstrutura
        import PrumoPerfis
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((500, 0), (500, 400))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, TUBO2)
        bs = PrumoEstrutura.barras_de(est)
        D = PrumoPerfis.perfil(TUBO2)["D"]
        self.assertAlmostEqual(bs[1].Shape.BoundBox.ZMin, D / 2, places=6)   # corte reto
        cs = [c for c in PrumoEstrutura.cantos(est) if c.tipo == "topo_T"]
        self.assertEqual(len(cs), 1)
        PrumoEstrutura.aplicar_opcao(est, cs, PrumoEstrutura.OPCOES_T[1])
        self.doc.recompute()
        self.assertTrue(bs[1].Shape.isValid())
        self.assertLess(bs[1].Shape.BoundBox.ZMin, D / 2 - 1.0)              # boca de lobo desce dos lados
        self.assertLess(bs[1].Shape.common(bs[0].Shape).Volume, 1e-2)
        self.assertLess(bs[1].Shape.distToShape(bs[0].Shape)[0], 1e-4)
        self.assertEqual(PrumoEstrutura.cantos(est)[0].descricao_tratamento(), "Recorte pelo contorno")

    def test_no_com_viga_partida(self):
        import PrumoEstrutura
        import PrumoPerfis
        sk = esboco_linhas(self.doc, [((0, 0), (500, 0)), ((500, 0), (1000, 0)), ((500, 0), (500, 400))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, "W 150 x 13,0")
        bs = PrumoEstrutura.barras_de(est)
        d = PrumoPerfis.perfil("W 150 x 13,0")["d"]
        self.assertAlmostEqual(bs[0].ComprimentoCorte.Value, 500, places=3)
        self.assertAlmostEqual(bs[1].ComprimentoCorte.Value, 500, places=3)
        self.assertAlmostEqual(bs[2].ComprimentoCorte.Value, 400 - d / 2, places=3)
        _sem_sobreposicao(self, bs)

    def test_canto_de_tres_barras_no_espaco(self):
        import Part
        import PrumoEstrutura
        arame = self.doc.addObject("Part::Feature", "Arame3D")
        o = FreeCAD.Vector(0, 0, 0)
        arame.Shape = Part.Compound([Part.LineSegment(o, FreeCAD.Vector(800, 0, 0)).toShape(),
                                     Part.LineSegment(o, FreeCAD.Vector(0, 600, 0)).toShape(),
                                     Part.LineSegment(o, FreeCAD.Vector(0, 0, 500)).toShape()])
        self.doc.recompute()
        est = PrumoEstrutura.criar(self.doc, arame, TQ50)
        bs = PrumoEstrutura.barras_de(est)
        self.assertEqual(len(bs), 3)
        for b in bs:
            self.assertTrue(b.Shape.isValid())
            self.assertEqual(len(b.Shape.Solids), 1)
        _sem_sobreposicao(self, bs)

    def test_opcao_invalida(self):
        import PrumoEstrutura
        sk, est, bs = self._quadro()
        with self.assertRaises(ValueError):
            PrumoEstrutura.aplicar_opcao(est, PrumoEstrutura.cantos(est), "Qualquer coisa")


class T24EstruturaExtras(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteExtras")

    def tearDown(self):
        fechar(self.doc)

    def _quadro(self, perfil="W 150 x 13,0", uniao="Meia-esquadria"):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)), ((1000, 600), (0, 600)),
                                      ((0, 600), (0, 0))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, perfil, uniao=uniao)
        return est, PrumoEstrutura.barras_de(est)

    def _linha(self, perfil, pts=((0, 0), (1000, 0)), plano="XZ"):
        import PrumoEstrutura
        sk = esboco_linhas(self.doc, [pts], plano, "L%d" % len(self.doc.Objects))
        est = PrumoEstrutura.criar(self.doc, sk, perfil)
        return PrumoEstrutura.barras_de(est)[0]

    @staticmethod
    def _area(pts):
        return 0.5 * abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                             for i in range(len(pts))))

    def test_reforco_triangular_no_canto(self):
        import PrumoEstruturaExtras as X
        est, bs = self._quadro()
        r = X.criar_reforco(bs[0], bs[1], Perna1=150, Perna2=150, Espessura=8, Chanfro=15)
        self.assertEqual(list(r.Avisos), [])
        self.assertTrue(r.Shape.isValid())
        area = 150 * 150 / 2.0 - 15 * 15 / 2.0
        self.assertAlmostEqual(r.Shape.Volume, area * 8, places=3)
        for b in (bs[0], bs[1]):
            self.assertLess(r.Shape.common(b.Shape).Volume, 1e-3)
            self.assertLess(r.Shape.distToShape(b.Shape)[0], 1e-6)
        self.assertIn("150 × 150 × 8", r.Denominacao)
        self.assertAlmostEqual(r.Massa, area * 8 * 7850e-9, places=9)
        self.assertIn(r, est.Group)

    def test_reforco_poligonal_e_posicao(self):
        import PrumoEstruturaExtras as X
        import PrumoPerfis
        est, bs = self._quadro()
        r = X.criar_reforco(bs[1], bs[2], Tipo="Poligonal", Perna1=200, Perna2=120, Ponta=30, Espessura=6,
                            Chanfro=0, Posicao="Frente")
        pts = [(0, 0), (200, 0), (200, 30), (30, 120), (0, 120)]
        self.assertAlmostEqual(r.Shape.Volume, self._area(pts) * 6, places=3)
        bf = PrumoPerfis.perfil("W 150 x 13,0")["bf"]
        bb = r.Shape.BoundBox
        self.assertAlmostEqual(max(abs(bb.YMin), abs(bb.YMax)), bf / 2.0, places=6)
        self.assertAlmostEqual(bb.YLength, 6.0, places=6)
        for b in bs:
            self.assertLess(r.Shape.common(b.Shape).Volume, 1e-3)

    def test_reforco_em_T_dos_dois_lados(self):
        import PrumoEstrutura
        import PrumoEstruturaExtras as X
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((500, 0), (500, 400))], "XZ")
        est = PrumoEstrutura.criar(self.doc, sk, "W 150 x 13,0")
        bs = PrumoEstrutura.barras_de(est)
        r1 = X.criar_reforco(bs[1], bs[0], Perna1=100, Perna2=100)
        r2 = X.criar_reforco(bs[1], bs[0], Perna1=100, Perna2=100, InverterLado=True)
        for r in (r1, r2):
            self.assertEqual(list(r.Avisos), [])
            for b in bs:
                self.assertLess(r.Shape.common(b.Shape).Volume, 1e-3)
        self.assertLess(r1.Shape.common(r2.Shape).Volume, 1e-6)
        c1, c2 = r1.Shape.CenterOfMass, r2.Shape.CenterOfMass
        self.assertLess(c1.x - 500, 0) if c2.x > 500 else self.assertGreater(c1.x - 500, 0)

    def test_reforco_barras_que_nao_se_tocam(self):
        import PrumoEstruturaExtras as X
        est, bs = self._quadro()
        r = X.criar_reforco(bs[0], bs[2])
        self.assertTrue(r.Avisos)
        self.assertTrue(r.Shape.isNull())

    def test_tampas_externa_e_interna(self):
        import PrumoEstruturaExtras as X
        b = self._linha(TQ50)
        ext = X.criar_tampa(b, "Fim", Tipo="Externa", Espessura=3, Folga=1)
        bb = ext.Shape.BoundBox
        self.assertAlmostEqual(bb.XMin, 1000.0, places=6)
        self.assertAlmostEqual(bb.XMax, 1003.0, places=6)
        self.assertAlmostEqual(ext.Shape.Volume, 48 * 48 * 3, places=3)
        inte = X.criar_tampa(b, "Início", Tipo="Interna", Espessura=3, Folga=0.5)
        bb = inte.Shape.BoundBox
        self.assertAlmostEqual(bb.XMin, 0.0, places=6)
        self.assertAlmostEqual(bb.XMax, 3.0, places=6)
        self.assertLess(inte.Shape.common(b.Shape).Volume, 1e-3)
        self.assertAlmostEqual(inte.Shape.Volume, 43 * 43 * 3, places=3)
        t = self._linha(TUBO2)
        import PrumoPerfis
        D = PrumoPerfis.perfil(TUBO2)["D"]
        tr = X.criar_tampa(t, "Fim", Tipo="Externa", Espessura=4, Folga=0)
        self.assertAlmostEqual(tr.Shape.Volume, math.pi * D * D / 4 * 4, delta=1e-3 * tr.Shape.Volume)

    def test_tampa_recusa_perfil_aberto_e_corte_inclinado(self):
        import PrumoEstruturaExtras as X
        w = self._linha("W 150 x 13,0")
        t = X.criar_tampa(w, "Fim")
        self.assertTrue(any("tubo" in a for a in t.Avisos))
        est, bs = self._quadro(perfil=TQ50)
        t2 = X.criar_tampa(bs[0], "Fim")
        self.assertTrue(any("inclinado" in a for a in t2.Avisos))

    def test_placa_de_base(self):
        import PrumoEstruturaExtras as X
        b = self._linha("W 150 x 13,0", ((0, 0), (0, 1000)))
        pl = X.criar_placa_base(b, "Início", Largura=250, Comprimento=300, Espessura=16, Furos="4",
                                DiametroFuro=22, DistanciaBorda=40)
        self.assertEqual(list(pl.Avisos), [])
        bb = pl.Shape.BoundBox
        self.assertAlmostEqual(bb.ZMax, 0.0, places=6)
        self.assertAlmostEqual(bb.ZMin, -16.0, places=6)
        self.assertAlmostEqual(pl.Shape.Volume, (250 * 300 - 4 * math.pi * 11 ** 2) * 16, delta=0.5)
        self.assertEqual(len([f for f in pl.Shape.Faces if f.Surface.__class__.__name__ == "Cylinder"]), 4)
        self.assertIn("4 furos", pl.Denominacao)
        pl.Furos = "2"
        self.doc.recompute()
        self.assertEqual(len([f for f in pl.Shape.Faces if f.Surface.__class__.__name__ == "Cylinder"]), 2)
        # placa menor que o perfil / furo em cima do perfil
        pl.Largura = 50
        self.doc.recompute()
        self.assertTrue(pl.Avisos)
        pl.Largura, pl.Comprimento, pl.DistanciaBorda = 110, 160, 15
        self.doc.recompute()
        self.assertTrue(any("furo" in a for a in pl.Avisos))

    def test_solda_no_canto_de_topo(self):
        import Part
        import PrumoEstruturaExtras as X
        import PrumoPerfis
        est, bs = self._quadro(uniao="Topo")
        s = X.criar_solda([bs[0], bs[1]], perna=6, processo=X.PROCESSOS[1], eletrodo="ER70S-6")
        it = PrumoPerfis.perfil("W 150 x 13,0")
        perim = PrumoPerfis.face(it, FreeCAD.Vector(), FreeCAD.Vector(1, 0, 0), FreeCAD.Vector(0, 1, 0)).OuterWire.Length
        self.assertAlmostEqual(s.ComprimentoTotal.Value, perim, places=3)
        self.assertAlmostEqual(s.VolumeDepositado, perim * 36 / 2 / 1000.0, places=6)
        self.assertAlmostEqual(s.MassaDepositada, perim * 36 / 2 * 7850e-9, places=9)
        self.assertFalse(s.Shape.isNull())
        self.assertIn(bs[0].Label, s.Juntas)
        self.assertEqual(list(s.Avisos), [])

    def test_solda_meia_esquadria_e_sem_contato(self):
        import PrumoEstruturaExtras as X
        est, bs = self._quadro()
        s = X.criar_solda([bs[0], bs[1]])
        self.assertGreater(s.ComprimentoTotal.Value, 400)
        s2 = X.criar_solda([bs[0], bs[2]])
        self.assertIn("não se tocam", s2.Avisos[0])
        self.assertEqual(s2.ComprimentoTotal.Value, 0.0)
        with self.assertRaises(ValueError):
            X.criar_solda([bs[0]])

    def test_solda_do_reforco(self):
        import PrumoEstruturaExtras as X
        est, bs = self._quadro()
        r = X.criar_reforco(bs[0], bs[1], Perna1=150, Perna2=150, Espessura=8, Chanfro=15)
        s = X.criar_solda([r, bs[0], bs[1]], perna=5)
        self.assertGreater(s.ComprimentoTotal.Value, 2 * 2 * (150 - 15) - 1)
        self.assertEqual(len(s.Juntas.split(";")), 3)  # reforço+A, reforço+B, A+B

    def test_lista_de_soldas_e_lista_de_materiais(self):
        import PrumoBOM
        import PrumoEstruturaExtras as X
        est, bs = self._quadro(uniao="Topo")
        X.criar_reforco(bs[0], bs[1], Material="ASTM A36")
        X.criar_reforco(bs[2], bs[3], Material="ASTM A36")
        s1 = X.criar_solda([bs[0], bs[1]], perna=6)
        s2 = X.criar_solda([bs[1], bs[2]], perna=6)
        soldas = X.lista_de_soldas([est])
        self.assertEqual(soldas, [s1, s2])
        sh = X.gravar_lista_de_soldas(self.doc, soldas)
        self.assertEqual(sh.get("A1"), "Item")
        self.assertEqual(sh.get("B4"), "Total")
        linhas = PrumoBOM.coletar([est], 7850)
        reforcos = [l for l in linhas if l.denominacao.startswith("Reforço")]
        self.assertEqual(len(reforcos), 1)
        self.assertEqual(reforcos[0].qtd, 2)
        self.assertEqual(reforcos[0].material, "ASTM A36")
        self.assertFalse(any("solda" in l.denominacao.lower() for l in linhas))
        self.assertEqual(sum(l.qtd for l in linhas), 6)

    def test_salvar_e_reabrir_com_extras(self):
        import PrumoEstruturaExtras as X
        est, bs = self._quadro(perfil=TQ50, uniao="Topo")
        X.criar_reforco(bs[0], bs[1])
        X.criar_solda([bs[0], bs[1]])
        caminho = os.path.join(tempfile.gettempdir(), "prumo_teste_extras.FCStd")
        self.doc.saveAs(caminho)
        nome = self.doc.Name
        FreeCAD.closeDocument(nome)
        self.doc = FreeCAD.openDocument(caminho)
        for o in self.doc.Objects:
            o.touch()
        self.doc.recompute()
        r = [o for o in self.doc.Objects if o.Name.startswith("Reforco")][0]
        s = [o for o in self.doc.Objects if o.Name.startswith("Solda")][0]
        self.assertTrue(r.Shape.isValid())
        self.assertGreater(s.ComprimentoTotal.Value, 0)


class T25EstruturaInterface(unittest.TestCase):
    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.doc = novo_doc("PrumoTesteEstruturaUI")
        self.sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)),
                                           ((1000, 600), (0, 600)), ((0, 600), (0, 0))], "XZ")

    def tearDown(self):
        FreeCADGui.Selection.clearSelection()
        fechar(self.doc)

    def _escolher_perfil(self, d, nome):
        import PrumoPerfis
        it = PrumoPerfis.perfil(nome)
        d.sel.familia.setCurrentIndex(d.sel.familia.findData(it["familia"]))
        d.sel.perfil.setCurrentIndex(d.sel.perfil.findData(nome))

    def test_criar_com_grupos_pelo_dialogo(self):
        import PrumoEstrutura
        d = PrumoEstrutura.DialogoEstrutura(self.sk)
        self._escolher_perfil(d, "W 150 x 13,0")
        k = d.novo_grupo()
        self.assertEqual(k, 1)
        d.nome.setText("Montantes")
        d.nome.textEdited.emit("Montantes")
        self._escolher_perfil(d, TQ50)
        d.fixacao.setCurrentText("Sup. centro")
        d.atribuir([1, 3])
        est = d.aplicar()
        d.close()
        bs = PrumoEstrutura.barras_de(est)
        self.assertEqual([b.Perfil for b in bs], ["W 150 x 13,0", TQ50, "W 150 x 13,0", TQ50])
        self.assertEqual(PrumoEstrutura.grupos(est)[0]["nome"], "Montantes")
        self.assertEqual(PrumoEstrutura.grupos(est)[0]["fixacao"], "Sup. centro")
        self.assertEqual(list(est.GrupoDaAresta), [0, 1, 0, 1])

    def test_editar_e_trocas_viram_grupo(self):
        import PrumoEstrutura
        est = PrumoEstrutura.criar(self.doc, self.sk, "W 150 x 13,0",
                                   grupos_extras=[{"nome": "Laterais", "perfil": TQ50, "arestas": [1, 3]}])
        bs = PrumoEstrutura.barras_de(est)
        PrumoEstrutura.trocar_perfil([bs[0]], "W 150 x 18,0")
        d = PrumoEstrutura.DialogoEstrutura(self.sk, est)
        self.assertEqual(d.lista.count(), 3)          # padrão, Laterais, Troca
        self.assertEqual(d.da_aresta, [2, 1, 0, 1])
        est2 = d.aplicar()
        d.close()
        self.assertIs(est2, est)
        self.assertEqual(list(est.PerfisIndividuais), [])
        self.assertEqual([b.Perfil for b in bs], ["W 150 x 18,0", TQ50, "W 150 x 13,0", TQ50])
        # remover o grupo das laterais: voltam ao padrão
        d = PrumoEstrutura.DialogoEstrutura(self.sk, est)
        d.lista.setCurrentRow(1)
        d.remover_grupo()
        d.aplicar()
        d.close()
        self.assertEqual([b.Perfil for b in bs], ["W 150 x 18,0", "W 150 x 13,0", "W 150 x 13,0", "W 150 x 13,0"])

    def test_pegar_linhas_selecionadas(self):
        import PrumoEstrutura
        d = PrumoEstrutura.DialogoEstrutura(self.sk)
        d.novo_grupo()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.sk, ["Edge1", "Edge3"])
        d.pegar_selecao()
        self.assertEqual(d.da_aresta, [1, 0, 1, 0])
        d.combos[1].setCurrentIndex(1)                # escolher na tabela
        self.assertEqual(d.da_aresta, [1, 1, 1, 0])
        d.combos[1].setCurrentIndex(0)
        FreeCADGui.Selection.clearSelection()
        d.pegar_selecao()
        self.assertIn("Nenhuma", d.aviso.text())
        d.mostrar_grupo()
        self.assertEqual(sorted(FreeCADGui.Selection.getSelectionEx()[0].SubElementNames), ["Edge1", "Edge3"])
        d.close()

    def test_grupo_vazio_nao_entra(self):
        import PrumoEstrutura
        d = PrumoEstrutura.DialogoEstrutura(self.sk)
        d.novo_grupo()
        est = d.aplicar()
        d.close()
        self.assertEqual(list(est.Grupos), [])

    def test_dialogo_de_cantos(self):
        import PrumoEstrutura
        import PrumoPerfis
        est = PrumoEstrutura.criar(self.doc, self.sk, "W 150 x 13,0", uniao="Topo")
        d = PrumoEstrutura.DialogoCantos(est)
        self.assertEqual(len(d.linhas), 1)
        d.escolher(0, PrumoEstrutura.OPCOES_ESQUADRIA[3])
        d.aplicar()
        d.close()
        dd = PrumoPerfis.perfil("W 150 x 13,0")["d"]
        bs = PrumoEstrutura.barras_de(est)
        self.assertAlmostEqual(bs[1].ComprimentoCorte.Value, 600 + dd, places=3)
        d2 = PrumoEstrutura.DialogoCantos(est, [bs[0]])
        self.assertEqual(len(d2.linhas), 2)
        self.assertEqual(d2.tabela.item(0, 1).text()[:4], "Topo")
        d2.aplicar()      # tudo "(manter)": nada muda
        d2.close()
        self.assertAlmostEqual(bs[1].ComprimentoCorte.Value, 600 + dd, places=3)

    def test_comandos_e_ajudantes_dos_extras(self):
        import PrumoEstrutura
        import PrumoEstruturaExtras as X
        est = PrumoEstrutura.criar(self.doc, self.sk, TQ50, uniao="Topo")
        pares = X.juntas_da_estrutura(est)
        self.assertEqual(len(pares), 4)
        soldas = X.soldar_estrutura(est, 4.0, X.PROCESSOS[1], "ER70S-6")
        self.assertEqual(len(soldas), 4)
        self.assertTrue(all(s.ComprimentoTotal.Value > 0 for s in soldas))
        sk2 = esboco_linhas(self.doc, [((2000, 0), (2000, 800))], "XZ", "Coluna")
        col = PrumoEstrutura.barras_de(PrumoEstrutura.criar(self.doc, sk2, TQ50))[0]
        self.assertEqual(X._pontas_livres(col), [0, 1])
        self.assertEqual(X._ponta_de_baixo(col), 0)
        FreeCADGui.Selection.clearSelection()
        for D in (X.PainelReforco, X.PainelTampa, X.PainelPlaca):
            dl = D()
            self.assertIn("Material", dl.props())
            dl.form.deleteLater()
        dt = X.PainelTampa()
        dt.pontas.setCurrentText("Pontas livres")
        self.assertEqual(dt.pontas_da(col), [0, 1])
        dt.form.deleteLater()
        for nome in ("Prumo_Estrutura", "Prumo_EditarEstrutura", "Prumo_Cantos", "Prumo_Reforco", "Prumo_Tampa",
                     "Prumo_PlacaBase", "Prumo_Solda", "Prumo_ListaSoldas"):
            self.assertIn(nome, FreeCADGui.Command.listAll())


# ======================================================================= esboço: enquadrar ao sair
class T21EnquadrarEsboco(unittest.TestCase):
    def setUp(self):
        self.doc = novo_doc("PrumoTesteEnquadrar")

    def tearDown(self):
        fechar(self.doc)
        FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D").RemBool("EnquadrarAoSairDoEsboco")

    def _esperar(self, ms):
        import time
        t = time.time()
        while time.time() - t < ms / 1000.0:
            FreeCADGui.updateGui()

    def test_esboco_grande_fica_inteiro_na_vista(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGui
        PrumoGui.instalar_ajuste_ao_sair_do_esboco()
        if os.environ.get("PRUMO_SEM_ENQUADRAR"):
            FreeCAD.ParamGet(PrumoGui.PARAM_PATH).SetBool("EnquadrarAoSairDoEsboco", False)
        sk = esboco_linhas(self.doc, [((0, 0), (5000, 0)), ((5000, 0), (5000, 5000)),
                                      ((5000, 5000), (0, 5000)), ((0, 5000), (0, 0))], "XY", "Grande")
        gd = FreeCADGui.getDocument(self.doc.Name)
        FreeCADGui.setActiveDocument(self.doc.Name)
        vista = gd.ActiveView
        vista.viewTop()
        # câmera bem de perto antes da edição (como num desenho pequeno)
        cam = vista.getCameraNode()
        try:
            cam.height.setValue(50.0)
        except Exception:
            pass
        cam.position.setValue(10, 10, 1000)
        self._esperar(100)
        gd.setEdit(sk.Name)
        self._esperar(300)
        gd.resetEdit()
        self._esperar(600)
        vp = vista.graphicsView().viewport()
        larg, alt = vp.width(), vp.height()
        for x, y in ((0, 0), (5000, 0), (5000, 5000), (0, 5000)):
            px, py = vista.getPointOnViewport(FreeCAD.Vector(x, y, 0))
            self.assertTrue(-1 <= px <= larg + 1 and -1 <= py <= alt + 1, (x, y, px, py, larg, alt))

    def test_parametro_desliga(self):
        import PrumoGui
        g = FreeCAD.ParamGet(PrumoGui.PARAM_PATH)
        self.assertTrue(g.GetBool("EnquadrarAoSairDoEsboco", True))


class T26Versao(unittest.TestCase):
    def test_texto_e_base(self):
        import PrumoVersao
        self.assertEqual(PrumoVersao.texto(), "0.1 beta")
        self.assertRegex(PrumoVersao.base_freecad(), r"^\d+\.\d+(\.\d+)?$")

    def test_informacoes_do_sistema(self):
        import PrumoVersao
        txt = PrumoVersao.info_sistema()
        for chave in ("Prumo 3D 0.1 beta", "Base: FreeCAD", "Sistema:", "Python:", "Pasta de dados:"):
            self.assertIn(chave, txt)

    def test_sobre_copia_para_a_area_de_transferencia(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoSobre
        from PySide import QtWidgets
        d = PrumoSobre.SobreDialog("0.1 beta · base FreeCAD 1.1", "FreeCAD 1.1")
        txt = d.copiar_info()
        self.assertEqual(QtWidgets.QApplication.clipboard().text(), txt)
        self.assertIn("Copiado", d.bt_copiar.text())
        d.close()

    def test_menu_ajuda_abre_o_sobre_do_prumo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGui
        PrumoGui.instalar_menu_sobre()
        FreeCADGui.activeWorkbench().reloadActive()
        FreeCADGui.updateGui()
        nomes = []

        def coletar(menu):
            for a in menu.actions():
                nomes.append(a.objectName())
                if a.menu():
                    coletar(a.menu())
        coletar(FreeCADGui.getMainWindow().menuBar())
        self.assertIn("Prumo_Sobre", nomes)
        self.assertNotIn("Std_About", nomes)

    def test_titulo_da_janela_com_a_versao(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGui
        PrumoGui.apply_window_branding()
        self.assertIn("0.1 beta", FreeCADGui.getMainWindow().windowTitle())

    def test_splash_da_instalacao_tem_prioridade(self):
        import shutil
        import PrumoGui
        if "Prumo3D" not in (FreeCAD.ConfigGet("SplashScreen") or ""):
            self.skipTest("sem branding.xml do Prumo")
        dest_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Gui", "images")
        dest = os.path.join(dest_dir, "splash_image.png")
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copyfile(PrumoGui.SPLASH_SRC, dest)
        with open(dest, "ab") as fh:
            fh.write(b"velha")                     # cópia antiga, diferente da atual
        PrumoGui._params().SetBool("SplashIsOurs", True)
        PrumoGui.install_splash()
        self.assertFalse(os.path.isfile(dest))
        self.assertFalse(PrumoGui._params().GetBool("SplashIsOurs", True))
        # uma splash que não é nossa fica onde está
        open(dest, "wb").write(b"do usuario")
        PrumoGui.install_splash()
        self.assertTrue(os.path.isfile(dest))
        os.remove(dest)

    def test_versao_no_pacote(self):
        import re
        pasta = os.path.dirname(os.path.abspath(__file__))
        txt = open(os.path.join(pasta, "package.xml"), encoding="utf-8").read()
        self.assertEqual(re.search(r"<version>([^<]+)</version>", txt).group(1), "0.1.0")


class T27Exemplos(unittest.TestCase):
    def test_exemplos_abrem_validos(self):
        import PrumoInicio
        for arq, _t, _d in PrumoInicio.EXEMPLOS:
            self.assertTrue(os.path.isfile(os.path.join(PrumoInicio.EXEMPLOS_DIR, arq)), arq)
            doc = PrumoInicio.abrir_exemplo(arq)
            try:
                self.assertTrue(doc.FileName.startswith(PrumoInicio.pasta_exemplos_usuario()))
                for o in doc.Objects:
                    o.touch()
                doc.recompute()
                ruins = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
                self.assertEqual(ruins, [], arq)
                self.assertTrue(any(hasattr(o, "Shape") and o.Shape.Solids for o in doc.Objects), arq)
            finally:
                FreeCAD.closeDocument(doc.Name)

    def test_exemplo_da_estrutura_tem_grupos_e_soldas(self):
        import PrumoInicio
        import PrumoEstrutura
        import PrumoEstruturaExtras
        doc = PrumoInicio.abrir_exemplo("Exemplo_Estrutura_soldada.FCStd")
        try:
            est = [o for o in doc.Objects if PrumoEstrutura.eh_estrutura(o)][0]
            self.assertEqual(len(PrumoEstrutura.grupos(est)), 2)
            self.assertGreaterEqual(len(PrumoEstruturaExtras.lista_de_soldas([est])), 4)
        finally:
            FreeCAD.closeDocument(doc.Name)

    def test_reabrir_o_exemplo_nao_duplica(self):
        import PrumoInicio
        a = PrumoInicio.abrir_exemplo("Exemplo_Chapa_dobrada.FCStd")
        b = PrumoInicio.abrir_exemplo("Exemplo_Chapa_dobrada.FCStd")
        try:
            iguais = [d for d in FreeCAD.listDocuments().values() if d.FileName == b.FileName]
            self.assertEqual(len(iguais), 1)
        finally:
            FreeCAD.closeDocument(b.Name)

    def test_tela_inicial_mostra_exemplos(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoInicio
        from PySide import QtWidgets
        w = PrumoInicio.InicioPrumo()
        textos = [l.text() for l in w.findChildren(QtWidgets.QLabel)]
        self.assertIn("Exemplos", textos)
        self.assertIn("Estrutura soldada", textos)
        w.close()


class T28TraducaoEArvore(unittest.TestCase):
    """Varredura de tradução da 0.1 beta e botão que reabre a árvore do modelo."""

    def test_textos_da_varredura_traduzidos(self):
        import PrumoI18n
        if PrumoI18n._state["tr"] is None:
            self.skipTest("tradução Prumo desligada")
        from PySide import QtCore
        tr = QtCore.QCoreApplication.translate
        casos = [("StdCmdNew", "&New Document", "&Novo documento"),
                 ("CmdSketcherCreateFillet", "Fillet", "Arredondamento"),
                 ("CmdPartDefeaturing", "Defeaturing", "Remover detalhes"),
                 ("Workbench", "&Part", "&Sólidos"),
                 ("Workbench", "&Sheet Metal", "&Chapa metálica"),
                 ("FEM_Analysis", "New Analysis", "Nova análise"),
                 ("Part_ExplodeCompound", "Explode Compound", "Separar composto"),
                 ("CmdTechDrawRadiusDimension", "Inserts a radius dimension of a circular edge or arc",
                  "Insere a cota de raio de um círculo ou arco")]
        for ctx, origem, esperado in casos:
            self.assertEqual(tr(ctx, origem), esperado, origem)

    def test_menu_da_chapa_sem_acento_quebrado(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoI18n
        if PrumoI18n._state["tr"] is None:
            self.skipTest("tradução Prumo desligada")
        ativa = FreeCADGui.activeWorkbench().name()
        try:
            FreeCADGui.activateWorkbench("SMWorkbench")
            FreeCADGui.updateGui()
            menus = [a.text() for a in FreeCADGui.getMainWindow().menuBar().actions()]
            self.assertIn("&Chapa metálica", menus)
            self.assertFalse(any("Ã" in m for m in menus), menus)
        finally:
            FreeCADGui.activateWorkbench(ativa)

    def test_botao_arvore_reabre_o_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGui
        import time
        # troca de bancada (outros testes) restaura os painéis com atraso: espera assentar
        t = time.time()
        while time.time() - t < 1.0:
            FreeCADGui.updateGui()
        d = PrumoGui.painel_arvore()
        self.assertIsNotNone(d)
        visivel = d.isVisible()
        try:
            PrumoGui.mostrar_arvore(False)
            FreeCADGui.updateGui()
            self.assertFalse(d.isVisible())
            FreeCADGui.runCommand("Prumo_Arvore", 0)
            FreeCADGui.updateGui()
            self.assertTrue(d.isVisible())
            # continua aberto (a tela inicial e o FreeCAD reaplicam estados com atraso)
            t = time.time()
            while time.time() - t < 1.0:
                FreeCADGui.updateGui()
            self.assertTrue(d.isVisible(), "o painel da árvore fechou sozinho")
        finally:
            PrumoGui.mostrar_arvore(visivel)

    def test_botao_arvore_na_faixa(self):
        import PrumoRibbon
        inicio = [t for t in PrumoRibbon.TABS if t["id"] == "inicio"][0]
        cmds = [c for _p, itens in inicio["panels"] for c, _s, _r in itens]
        self.assertIn("Prumo_Arvore", cmds)


class T29GuiaEstrutura(unittest.TestCase):
    """Tutorial da estrutura soldada e desenhos do diálogo Cantos."""

    def test_passos_do_tutorial_detectados_em_ordem(self):
        import PrumoTutorial as T
        import PrumoEstrutura as E
        import PrumoEstruturaExtras as X
        doc = novo_doc("PrumoTesteTutEstrutura")
        try:
            FreeCAD.setActiveDocument(doc.Name)
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 1)
            sk = esboco_linhas(doc, [((0, 0), (1500, 0)), ((1500, 0), (1500, 900)), ((1500, 900), (0, 900)),
                                     ((0, 900), (0, 0)), ((750, 0), (750, 900))], "XZ")
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 2, "esqueleto → próximo é a estrutura")
            est = E.criar(doc, sk, "W 150 x 13,0")
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 3, "estrutura → próximo são os grupos")
            E.definir_grupos(est, [{"nome": "Colunas", "perfil": TQ50, "arestas": [1, 3]}])
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 4, "grupos → próximo é o canto")
            E.aplicar_opcao(est, [c for c in E.cantos(est) if c.tipo == "esquadria"], E.OPCOES_ESQUADRIA[3])
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 5, "canto → próximo é o reforço")
            bs = E.barras_de(est)
            X.criar_reforco(bs[2], bs[1], Perna1=200, Perna2=200, Espessura=8)
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 6, "reforço → próximo é a solda")
            X.soldar_estrutura(est, 5)
            doc.recompute()
            self.assertEqual(T.passo_atual(T.estado("estrutura")), 7, "solda → próximo é a lista de corte")
            E.gravar_lista_de_corte(doc, E.lista_de_corte([est]))
            doc.recompute()
            feitos = T.estado("estrutura")
            self.assertEqual(feitos[:8], [True] * 8, feitos)
            self.assertFalse(feitos[8], "documento não salvo ainda")
            # o tutorial da peça não se confunde com a estrutura
            self.assertFalse(T.estado("peca")[1])
        finally:
            fechar(doc)

    def test_painel_do_tutorial_da_estrutura(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoTutorial as T
        from PySide import QtWidgets
        w = T.Tutorial(None, "estrutura")
        try:
            self.assertEqual(len(w.itens), len(T.PASSOS_ESTRUTURA))
            self.assertIn("estrutura soldada", w.findChildren(QtWidgets.QLabel)[0].text().lower() +
                          " ".join(l.text().lower() for l in w.findChildren(QtWidgets.QLabel)))
        finally:
            w.timer.stop()
            w.deleteLater()

    def test_trocar_de_tutorial_no_mesmo_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoTutorial as T
        d1 = T.mostrar("peca")
        d2 = T.mostrar("estrutura")
        try:
            self.assertIs(d1, d2)
            self.assertEqual(d2.widget().chave, "estrutura")
            self.assertEqual(d2.windowTitle(), "Tutorial: estrutura soldada")
        finally:
            d2.widget().timer.stop()
            d2.close()

    def test_mostrar_onde_encontra_botoes_da_estrutura(self):
        import PrumoRibbon
        import PrumoTutorial as T
        if PrumoRibbon._state.get("ribbon") is None:
            self.skipTest("faixa Prumo não instalada nesta sessão")
        for i in (2, 3, 4, 5, 6, 7):
            _t, _x, aba, cmds, _k = T.PASSOS_ESTRUTURA[i]
            self.assertTrue(T.destacar(aba, cmds), "botão do passo %d não encontrado" % (i + 1))

    def test_desenhos_dos_cantos_validos(self):
        import PrumoIlustra
        import PrumoEstrutura as E
        try:
            from PySide6 import QtSvg
        except ImportError:  # pragma: no cover
            from PySide2 import QtSvg
        from PySide import QtCore
        vistos = set()
        for tipo, opcoes in (("esquadria", E.OPCOES_ESQUADRIA), ("topo_T", E.OPCOES_T)):
            for op in opcoes:
                svg, nota = PrumoIlustra.canto_svg(op, tipo)
                self.assertTrue(QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8"))).isValid(), op)
                self.assertTrue(nota)
                vistos.add(svg)
        self.assertGreaterEqual(len(vistos), 5, "opções diferentes devem ter desenhos diferentes")

    def test_dialogo_cantos_acompanha_a_escolha(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoEstrutura as E
        doc = novo_doc("PrumoTesteCantosGuia")
        try:
            sk = esboco_linhas(doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)), ((1000, 600), (0, 600)),
                                     ((0, 600), (0, 0)), ((500, 0), (500, 600))], "XZ")
            est = E.criar(doc, sk, "W 150 x 13,0")
            doc.recompute()
            d = E.DialogoCantos(est)
            r = [k for k, g in enumerate(d.linhas) if g[0].tipo == "topo_T"][0]
            d.tabela.setCurrentCell(r, 2)
            d.escolher(r, "Recorte pelo contorno")
            self.assertEqual(d.opcao_mostrada(), ("topo_T", "Recorte pelo contorno"))
            self.assertIn("Recorte pelo contorno", d.nota.text())
            r2 = [k for k, g in enumerate(d.linhas) if g[0].tipo == "esquadria"][0]
            d.tabela.setCurrentCell(r2, 2)
            self.assertEqual(d.opcao_mostrada()[0], "esquadria")
            self.assertIn("Meia-esquadria", d.nota.text())   # (manter) mostra o tratamento de hoje
            d.close()
        finally:
            fechar(doc)


class T30Faixa(unittest.TestCase):
    """Faixa: nomes inteiros, altura arrastável, grupos com divisor arrastável."""

    def setUp(self):
        import PrumoRibbon
        self.R = PrumoRibbon
        self.rb = PrumoRibbon._state.get("ribbon")
        if self.rb is None:
            self.skipTest("faixa Prumo não instalada nesta sessão")
        self.p = FreeCAD.ParamGet(PrumoRibbon.PARAM_PATH)
        self.altura0 = self.rb.content.height()
        self.doc = novo_doc("PrumoTesteFaixa")

    def tearDown(self):
        self.rb.definir_altura(self.altura0)
        for t in self.R.TABS:
            self.p.RemString("RibbonPaineis_" + t["id"])
        fechar(self.doc)

    def _abrir(self, tab_id):
        self.rb.select_tab(tab_id, user=True)
        for _ in range(5):
            FreeCADGui.updateGui()

    def test_medidas_dentro_dos_limites(self):
        R = self.R
        for h in (50, R.ALTURA_MIN, R.ALTURA_PADRAO, 170, R.ALTURA_MAX, 500):
            m = R.medidas(h)
            self.assertTrue(R.ALTURA_MIN <= m["altura"] <= R.ALTURA_MAX)
            self.assertGreaterEqual(m["S"] * 3 + 6, 0)
            self.assertLessEqual(m["S"] * 3, m["L"] + 6)
            self.assertTrue(24 <= m["iconL"] <= 48 and 16 <= m["iconS"] <= 24)
        self.assertGreater(R.medidas(190)["L"], R.medidas(120)["L"])
        self.assertGreaterEqual(R.ALTURA_PADRAO, 136, "a faixa ficou um pouco mais alta")

    def test_nenhum_nome_cortado_em_nenhuma_aba(self):
        cortados = []
        for t in self.R.TABS:
            self._abrir(t["id"])
            for b in self.rb.findChildren(self.R.RibbonButton):
                if b.isVisible() and b.toolButtonStyle() != QtCore.Qt.ToolButtonIconOnly \
                        and b.width() < b.largura_do_texto() - 1:
                    cortados.append("%s: %s" % (t["id"], b.text()))
        self.assertEqual(cortados, [])

    def test_altura_arrastavel_muda_botoes_e_fica_salva(self):
        self._abrir("peca")
        h = self.rb.definir_altura(180)
        FreeCADGui.updateGui()
        self.assertEqual(self.rb.content.height(), 180)
        self.assertEqual(self.p.GetInt("RibbonHeight"), 180)
        grandes = [b for b in self.rb.findChildren(self.R.RibbonButton) if b.property("sw_size") == "L"
                   and b.isVisible()]
        self.assertTrue(grandes)
        self.assertEqual(grandes[0].height(), self.R.medidas(h)["L"])
        self.assertGreater(grandes[0].iconSize().width(), 32)
        # o arraste pela alça usa a mesma função ao soltar
        self.rb.grip._y0, self.rb.grip._h0 = 0, 180
        self.rb.content.setFixedHeight(150)
        self.rb.grip.mouseReleaseEvent(None)
        self.assertEqual(self.p.GetInt("RibbonHeight"), 150)
        self.rb.grip.mouseDoubleClickEvent(None)
        self.assertEqual(self.rb.content.height(), self.R.ALTURA_PADRAO)

    def test_grupos_com_divisor_arrastavel_e_largura_salva(self):
        self._abrir("inicio")
        sp = self.rb.split
        self.assertIsInstance(sp, QtWidgets.QSplitter)
        self.assertEqual(sp.count(), len(self.rb.paineis) + 1)
        tam = sp.sizes()
        tam[0] += 60
        sp.setSizes(tam)
        sp.splitterMoved.emit(tam[0], 1)
        salvo = self.p.GetString("RibbonPaineis_inicio")
        self.assertTrue(salvo)
        largura = sp.sizes()[0]
        self._abrir("peca")
        self._abrir("inicio")
        self.assertAlmostEqual(self.rb.split.sizes()[0], largura, delta=6)
        self.rb.restaurar_larguras()
        self.assertEqual(self.p.GetString("RibbonPaineis_inicio"), "")

    def test_grupo_estreitado_mostra_so_icones_pequenos(self):
        self._abrir("inicio")
        pn = [p for p in self.rb.paineis if p.pequenos()][0]
        self.assertGreater(pn._natural, pn._compacta)
        pn.resize(pn._compacta, pn.height())   # bem abaixo da largura natural
        FreeCADGui.updateGui()
        self.assertTrue(pn.compacto())
        pn.resize(pn._natural + 10, pn.height())
        FreeCADGui.updateGui()
        self.assertFalse(pn.compacto())

    def test_recolher_esconde_a_alca(self):
        self.rb._toggle_collapse()
        try:
            self.assertFalse(self.rb.grip.isVisible())
        finally:
            self.rb._toggle_collapse()
        self.assertTrue(self.rb.content.isVisible())

    def test_tutorial_ainda_acha_os_botoes(self):
        import PrumoTutorial as T
        self.rb.definir_altura(170)
        for _t, _x, aba, cmds, _k in [T.PASSOS[0], T.PASSOS[1], T.PASSOS[-1]] + T.PASSOS_ESTRUTURA[2:8]:
            self.assertTrue(T.destacar(aba, cmds), cmds)

    def test_janela_estreita_rola_sem_compactar(self):
        self._abrir("inicio")
        mw = FreeCADGui.getMainWindow()
        tam0 = mw.size()
        try:
            mw.resize(900, tam0.height())
            for _ in range(10):
                FreeCADGui.updateGui()
            self.assertFalse(any(p.compacto() for p in self.rb.paineis))
        finally:
            mw.resize(tam0)


class T31Bancadas(unittest.TestCase):
    """Bancadas que não vêm ligadas (Materiais, Nuvem de pontos, Robótica) e editor de materiais no
    menu Vista."""

    def setUp(self):
        import PrumoGui
        self.G = PrumoGui
        self.wb = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Workbenches")
        self.pp = FreeCAD.ParamGet(PrumoGui.PARAM_PATH)
        self.dis0 = self.wb.GetString("Disabled", "")
        self.ord0 = self.wb.GetString("Ordered", "")
        self.flag0 = self.pp.GetInt("BancadasPadrao", 0)

    def tearDown(self):
        for k, v in (("Disabled", self.dis0), ("Ordered", self.ord0)):
            if v:
                self.wb.SetString(k, v)
            else:
                self.wb.RemString(k)
        self.pp.SetInt("BancadasPadrao", self.flag0)

    def test_perfil_novo_desliga_as_tres(self):
        self.wb.RemString("Disabled")
        self.wb.SetString("Ordered", "PartDesignWorkbench,MaterialWorkbench,SketcherWorkbench")
        self.pp.RemInt("BancadasPadrao")
        self.assertTrue(self.G.aplicar_bancadas_padrao())
        dis = self.G.bancadas_desligadas()
        for n in ("MaterialWorkbench", "PointsWorkbench", "RobotWorkbench", "TestWorkbench"):
            self.assertIn(n, dis)
        self.assertNotIn("MaterialWorkbench", self.wb.GetString("Ordered"))
        self.assertNotIn("PartDesignWorkbench", dis)

    def test_religada_pelo_usuario_continua_ligada(self):
        self.pp.RemInt("BancadasPadrao")
        self.G.aplicar_bancadas_padrao()
        self.wb.SetString("Disabled", ",".join(n for n in self.G.bancadas_desligadas() if n != "PointsWorkbench"))
        self.assertFalse(self.G.aplicar_bancadas_padrao())
        self.assertNotIn("PointsWorkbench", self.G.bancadas_desligadas())

    def test_seletor_da_faixa_esconde_as_desligadas(self):
        import PrumoRibbon
        rb = PrumoRibbon._state.get("ribbon")
        if rb is None:
            self.skipTest("faixa Prumo não instalada nesta sessão")
        self.pp.RemInt("BancadasPadrao")
        self.G.aplicar_bancadas_padrao()
        m = QtWidgets.QMenu()
        rb._fill_wb_menu(m)
        nomes = [a.text() for a in m.actions()]
        for rot in ("Materiais", "Nuvem de pontos", "Robótica"):
            self.assertNotIn(rot, nomes)
        self.assertIn("Peça", nomes)
        self.assertIn("Chapa metálica", nomes)

    def test_menu_vista_tem_editor_de_materiais_e_arvore(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.G.instalar_menu_sobre()
        FreeCADGui.activeWorkbench().reloadActive()
        FreeCADGui.updateGui()
        mb = FreeCADGui.getMainWindow().menuBar()
        cmds = set()
        for a in mb.actions():
            if a.menu() is not None and a.text().replace("&", "") == "Vista":
                cmds = {x.objectName() for x in a.menu().actions()}
        self.assertIn("Prumo_Arvore", cmds)
        if "Material_Edit" in FreeCADGui.listCommands():
            self.assertIn("Material_Edit", cmds)

    def test_comandos_de_material_continuam_disponiveis(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.assertIn("Std_SetMaterial", FreeCADGui.listCommands())


class T32Arvore(unittest.TestCase):
    """Árvore do modelo: nomes em português, cores sem amarelo forte, olho novo."""

    def _esperar(self):
        for _ in range(5):
            FreeCADGui.updateGui() if FreeCAD.GuiUp else None
            QtCore.QCoreApplication.processEvents()

    def setUp(self):
        import PrumoNomes
        self.N = PrumoNomes
        self.obs = PrumoNomes.install()

    def test_traducao_dos_rotulos(self):
        t = self.N.traduzir
        self.assertEqual(t("Pad"), "Extrusão")
        self.assertEqual(t("Pocket001"), "Cavidade001")
        self.assertEqual(t("XY_Plane"), "Plano XY")
        self.assertIsNone(t("Suporte"))
        self.assertIsNone(t("Pad1234"))

    def test_objetos_novos_ganham_nome_em_portugues(self):
        doc = novo_doc("PrumoTesteNomes")
        try:
            body = doc.addObject("PartDesign::Body", "Body")
            sk = esboco_retangulo(body)
            pad = body.newObject("PartDesign::Pad", "Pad")
            pad.Profile = sk
            pad.Length = 5
            pad2 = body.newObject("PartDesign::Pad", "Pad")
            doc.recompute()
            self._esperar()
            self.assertEqual(body.Label, "Corpo")
            self.assertEqual(sk.Label, "Esboço")
            self.assertEqual(pad.Label, "Extrusão")
            self.assertEqual(pad2.Label, "Extrusão001")
            self.assertEqual(pad.Name, "Pad", "o nome interno não muda")
            papeis = {f.Role: f.Label for f in body.Origin.OriginFeatures}
            # o FreeCAD 1.1 já traduz a origem ("Plano-XY"); o Prumo só cobre se vier em inglês
            self.assertNotIn(papeis.get("XY_Plane"), ("XY_Plane", None))
            self.assertNotIn(papeis.get("Z_Axis"), ("Z_Axis", None))
        finally:
            fechar(doc)

    def test_rotulo_escolhido_pelo_usuario_fica(self):
        doc = novo_doc("PrumoTesteNomes2")
        try:
            b = doc.addObject("Part::Box", "Box")
            b.Label = "Bloco de apoio"
            self._esperar()
            self.assertEqual(b.Label, "Bloco de apoio")
        finally:
            fechar(doc)

    def test_arquivo_aberto_nao_e_renomeado(self):
        caminho = os.path.join(tempfile.mkdtemp(), "nomes_ingles.FCStd")
        p = FreeCAD.ParamGet(self.N.PARAM_PATH)
        p.SetBool("NomesEmPortugues", False)
        try:
            doc = novo_doc("PrumoTesteNomes3")
            doc.addObject("Part::Box", "Box")
            self._esperar()
            doc.saveAs(caminho)
            fechar(doc)
        finally:
            p.RemBool("NomesEmPortugues")
        doc = FreeCAD.openDocument(caminho)
        try:
            self._esperar()
            self.assertEqual(doc.getObject("Box").Label, "Box")
        finally:
            fechar(doc)

    def test_desligavel_nas_preferencias(self):
        p = FreeCAD.ParamGet(self.N.PARAM_PATH)
        p.SetBool("NomesEmPortugues", False)
        doc = novo_doc("PrumoTesteNomes4")
        try:
            b = doc.addObject("Part::Box", "Box")
            self._esperar()
            self.assertEqual(b.Label, "Box")
        finally:
            p.RemBool("NomesEmPortugues")
            fechar(doc)

    def test_cores_da_arvore_sem_amarelo(self):
        import PrumoEstilo as E
        r, g, b = (int(E.TREE_COLORS["TreeActiveColor"][i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreater(b, r, "corpo ativo em tom azulado, não amarelo")
        qss = E._qss_claro()
        if qss:
            self.assertIn("Gui--TreeWidget::item:selected", qss)
            self.assertIn(E.SEL, qss)
        self.assertGreaterEqual(E.VIEW_COLORS_VERSION, 4)

    def test_olho_novo_no_tema_de_icones(self):
        import zipfile
        import PrumoGui
        with zipfile.ZipFile(PrumoGui.ICON_ZIP) as z:
            for n in ("TreeItemVisible.svg", "TreeItemInvisible.svg", "actions/TreeItemVisible.svg"):
                svg = z.read(n).decode("utf-8")
                self.assertNotIn("#F7BE00", svg, n)
                self.assertIn("<svg", svg)
        if FreeCAD.GuiUp:
            try:
                from PySide6 import QtSvg
            except ImportError:  # pragma: no cover
                from PySide2 import QtSvg
            with zipfile.ZipFile(PrumoGui.ICON_ZIP) as z:
                r = QtSvg.QSvgRenderer(QtCore.QByteArray(z.read("TreeItemVisible.svg")))
                self.assertTrue(r.isValid())


class T33PaineisVisuais(unittest.TestCase):
    """Painéis de tarefa no estilo PropertyManager: kit e painéis dos comandos."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.doc = novo_doc("PrumoTestePaineis")
        FreeCAD.setActiveDocument(self.doc.Name)
        FreeCADGui.Selection.clearSelection()

    def tearDown(self):
        FreeCADGui.Selection.clearSelection()
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _estrutura(self, perfil=None):
        import PrumoEstrutura as E
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 0), (1000, 600)), ((1000, 600), (0, 600)),
                                      ((0, 600), (0, 0))], "XZ")
        est = E.criar(self.doc, sk, perfil or TQ50, uniao="Topo")
        self.doc.recompute()
        return est, E.barras_de(est)

    # ---- kit
    def test_icones_validos(self):
        import PrumoPainel as P
        try:
            from PySide6 import QtSvg
        except ImportError:  # pragma: no cover
            from PySide2 import QtSvg
        for nome in P.ICONES:
            r = QtSvg.QSvgRenderer(QtCore.QByteArray(P.svg_icone(nome).encode("utf-8")))
            self.assertTrue(r.isValid(), nome)
            self.assertFalse(P.icone(nome).isNull(), nome)

    def test_secao_recolhe_e_opcoes(self):
        import PrumoPainel as P
        s = P.Secao("Teste", "tipo")
        campo = s.linha("espessura", P.numero(5.0), "dica do campo", "Espessura")
        self.assertEqual(campo.toolTip(), "dica do campo")
        s.topo.setChecked(False)
        self.assertTrue(s.corpo.isHidden())
        s.topo.setChecked(True)
        self.assertFalse(s.corpo.isHidden())
        o = P.Opcoes([("a", "A", "empurra", ""), ("b", "B", "puxa", "")], "b")
        self.assertEqual(o.valor(), "b")
        visto = []
        o.mudou.connect(visto.append)
        o.definir("a")
        self.assertEqual((o.valor(), visto), ("a", ["a"]))
        m = P.Mensagem()
        m.mostrar("erro x", "erro")
        self.assertEqual(m.tipo, "erro")

    def test_caixa_de_selecao_minimo_maximo(self):
        import PrumoPainel as P
        _est, bs = self._estrutura()
        c = P.CaixaSelecao("Barras", lambda o, s: [(o.Label, o)], minimo=2, maximo=2)
        self.assertFalse(c.pronta())
        c.aceitar(bs[0])
        c.aceitar(bs[0])               # repetida não entra
        self.assertEqual(len(c.valores()), 1)
        c.aceitar(bs[1])
        self.assertTrue(c.pronta())
        c.aceitar(bs[2])               # cheia: a mais antiga sai
        self.assertEqual(c.valores(), [bs[1], bs[2]])
        self.assertIn("✓", c.rotulo.text())
        c.limpar()
        self.assertIn("falta 2", c.rotulo.text())

    # ---- painéis dos comandos
    def test_reforco_selecao_antes_de_abrir(self):
        import PrumoEstruturaExtras as X
        _est, bs = self._estrutura()
        FreeCADGui.Selection.addSelection(bs[0])
        FreeCADGui.Selection.addSelection(bs[1])
        p = X.PainelReforco()
        self.assertEqual(p.barras.valores(), [bs[0], bs[1]])
        self.assertIsNone(p.pendencia())
        self.assertEqual(p.form.mensagem.tipo, "ok")
        self.assertTrue(p.accept())
        self.assertEqual(len([o for o in self.doc.Objects if "Perna1" in o.PropertiesList]), 1)

    def test_reforco_selecao_depois_de_abrir(self):
        import PrumoEstruturaExtras as X
        _est, bs = self._estrutura()
        p = X.PainelReforco().mostrar()
        try:
            self.assertFalse(p.barras.pronta())
            self.assertFalse(p.accept(), "sem as barras não executa")
            self.assertEqual(p.form.mensagem.tipo, "erro")
            FreeCADGui.Selection.addSelection(bs[2])
            FreeCADGui.Selection.addSelection(bs[3])
            FreeCADGui.updateGui()
            self.assertEqual(p.barras.valores(), [bs[2], bs[3]])
            self.assertTrue(p.accept())
        finally:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        self.assertEqual(len([o for o in self.doc.Objects if "Perna1" in o.PropertiesList]), 1)

    def test_reforco_barras_que_nao_se_tocam(self):
        import PrumoEstruturaExtras as X
        _est, bs = self._estrutura()
        p = X.PainelReforco()
        p.barras.aceitar(bs[0])
        p.barras.aceitar(bs[2])        # opostas: não se tocam
        self.assertTrue(p.pendencia())
        self.assertFalse(p.accept())
        p.close()

    def test_tampa_placa_e_solda(self):
        import PrumoEstruturaExtras as X
        est, bs = self._estrutura()
        pt = X.PainelPlaca()
        pt.barras.aceitar(bs[1])
        self.assertTrue(pt.accept())
        ps = X.PainelSolda()
        self.assertTrue(ps.pendencia())
        ps.pecas.aceitar(est)
        self.assertIsNone(ps.pendencia())
        self.assertIn("todas as juntas", ps.pecas.lista.item(0).text())
        self.assertTrue(ps.accept())
        self.assertGreaterEqual(len(X.lista_de_soldas([est])), 4)
        # tampa: estrutura de topo tem tubos sem ponta livre -> pede escolher a ponta
        tp = X.PainelTampa()
        tp.barras.aceitar(bs[0])
        tp.pontas.setCurrentText("Início")
        self.assertIsNone(tp.pendencia())
        self.assertTrue(tp.accept())

    def test_folha_pelo_painel(self):
        import PrumoFolhas
        b = self.doc.addObject("Part::Box", "Bloco")
        self.doc.recompute()
        FreeCADGui.Selection.addSelection(b)
        p = PrumoFolhas.PainelFolha(self.doc)
        self.assertEqual(p.objs, [b])
        self.assertTrue(p.vistas.isChecked())
        p.campos["titulo"].setText("BLOCO DE TESTE")
        self.assertTrue(p.accept())
        paginas = [o for o in self.doc.Objects if o.TypeId == "TechDraw::DrawPage"]
        self.assertEqual(len(paginas), 1)

    def test_fixador_pelo_painel(self):
        import PrumoFixadores as F
        p = F.PainelFixador("M10")
        self.assertEqual(p.diam.currentText(), "M10")
        p.comp.setEditText("abc")
        self.assertTrue(p.pendencia())
        p.comp.setEditText("40")
        self.assertIsNone(p.pendencia())
        self.assertTrue(p.accept())
        self.assertTrue(any("M10" in o.Label for o in self.doc.Objects))

    def test_carga_empurra_ou_puxa_com_desenho(self):
        import PrumoPainel as P
        o = P.Opcoes([("empurra", "Empurra a face", "empurra", ""), ("puxa", "Puxa a face", "puxa", "")])
        self.assertEqual(o.valor(), "empurra")
        self.assertEqual(set(o.botoes), {"empurra", "puxa"})

    def test_dialogos_grandes_com_mensagem_e_icones(self):
        import PrumoEstrutura as E
        est, _bs = self._estrutura()
        d = E.DialogoEstrutura(est.Esqueleto, est)
        self.assertTrue(d.mensagem.text())
        d.close()
        c = E.DialogoCantos(est)
        self.assertTrue(c.nota.text())
        c.close()


class T34FluxoDeSelecao(unittest.TestCase):
    """Função antes ou peça antes: os dois caminhos funcionam."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.doc = novo_doc("PrumoTesteFluxo")
        FreeCAD.setActiveDocument(self.doc.Name)
        FreeCADGui.Selection.clearSelection()
        self.a = self.doc.addObject("Part::Box", "A")
        self.b = self.doc.addObject("Part::Cylinder", "B")
        self.b.Radius, self.b.Height = 3, 20
        self.doc.recompute()

    def tearDown(self):
        FreeCADGui.Selection.clearSelection()
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _esperar(self, n=10):
        for _ in range(n):
            FreeCADGui.updateGui()

    def test_comandos_cobertos_existem_e_sao_de_selecao_antes(self):
        import PrumoSelecao as S
        for cmd in ("Part_Cut", "Part_Fuse", "Part_Common", "Part_Section"):
            self.assertIn(cmd, S.SELECAO_PRIMEIRO)
            self.assertTrue(S.precisa_de_painel(cmd), cmd + " sem seleção deveria pedir o painel")

    def test_subtrair_funcao_antes(self):
        import PrumoSelecao as S
        p = S.pedir_para_comando("Part_Cut", mostrar=True, adiar=False)
        try:
            self.assertFalse(p.accept())
            FreeCADGui.Selection.addSelection(self.a)
            self._esperar()
            self.assertEqual(p.caixas[0].valores(), [self.a])
            self.assertTrue(p.caixas[1].ativa, "base cheia: a vez passa para a ferramenta")
            FreeCADGui.Selection.addSelection(self.b)
            self._esperar()
            self.assertEqual(p.caixas[1].valores(), [self.b])
            self.assertTrue(p.accept())
        finally:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        self._esperar()
        cortes = [o for o in self.doc.Objects if o.TypeId == "Part::Cut"]
        self.assertEqual(len(cortes), 1)
        self.assertIs(cortes[0].Base, self.a)
        self.assertIs(cortes[0].Tool, self.b)

    def test_subtrair_peca_antes_preenche_na_ordem(self):
        import PrumoSelecao as S
        FreeCADGui.Selection.addSelection(self.b)
        FreeCADGui.Selection.addSelection(self.a)
        self.assertFalse(S.precisa_de_painel("Part_Cut"), "com seleção o comando roda direto")
        p = S.pedir_para_comando("Part_Cut", mostrar=False, adiar=False)
        self.assertEqual(p.caixas[0].valores(), [self.b])
        self.assertEqual(p.caixas[1].valores(), [self.a])
        p.close()

    def test_unir_aceita_varias(self):
        import PrumoSelecao as S
        c = self.doc.addObject("Part::Sphere", "C")
        self.doc.recompute()
        p = S.pedir_para_comando("Part_Fuse", mostrar=False, adiar=False)
        for o in (self.a, self.b, c):
            p.distribuir(o)
        self.assertEqual(len(p.caixas[0].valores()), 3)
        self.assertTrue(p.accept())
        self._esperar()
        self.assertTrue(any(o.TypeId in ("Part::MultiFuse", "Part::Fuse") for o in self.doc.Objects))

    def test_filtro_recusa_o_que_nao_serve(self):
        import PrumoSelecao as S
        sk = self.doc.addObject("Sketcher::SketchObject", "Esboco")
        self.doc.recompute()
        p = S.pedir_para_comando("Part_Fuse", mostrar=False, adiar=False)
        self.assertIsNone(p.distribuir(sk))
        self.assertEqual(p.caixas[0].valores(), [])
        p.close()

    def test_botao_da_faixa_fica_ligado_e_abre_o_painel(self):
        import PrumoRibbon
        rb = PrumoRibbon._state.get("ribbon")
        if rb is None:
            self.skipTest("faixa Prumo não instalada")
        rb.select_tab("solidos", user=True)
        self._esperar()
        bts = [b for b in rb.findChildren(PrumoRibbon.RibbonButton)
               if any(a.whatsThis() == "Part_Cut" for a in b._actions)]
        if not bts:
            self.skipTest("Subtrair não está na faixa desta sessão")
        b = bts[0]
        b._current = [a for a in b._actions if a.whatsThis() == "Part_Cut"][0]
        b._sync()
        self.assertTrue(b.isEnabled(), "sem seleção o botão continua clicável")
        b._on_click()
        self._esperar()
        dlg = FreeCADGui.Control.activeDialog()
        self.assertTrue(dlg)
        FreeCADGui.Control.closeDialog()

    def test_comandos_do_prumo_pedem_a_selecao_depois(self):
        import PrumoEstrutura as E
        for nome in ("Prumo_EditarEstrutura", "Prumo_Cantos", "Prumo_TrocarPerfil", "Prumo_Estrutura"):
            self.assertTrue(FreeCADGui.Command.get(nome).isActive(), nome)
        sk = esboco_linhas(self.doc, [((0, 0), (800, 0)), ((800, 0), (800, 500))], "XZ")
        FreeCADGui.runCommand("Prumo_Estrutura", 0)
        self._esperar()
        dlg = FreeCADGui.Control.activeDialog()
        self.assertTrue(dlg, "sem esboço selecionado abre o painel que pede o esboço")
        FreeCADGui.Selection.addSelection(sk)
        self._esperar()
        FreeCADGui.Control.closeDialog()
        est = E.criar(self.doc, sk, TQ50)
        self.doc.recompute()
        FreeCADGui.Selection.clearSelection()
        for nome in ("Prumo_Cantos", "Prumo_TrocarPerfil", "Prumo_EditarEstrutura"):
            FreeCADGui.runCommand(nome, 0)
            self._esperar()
            self.assertTrue(FreeCADGui.Control.activeDialog(), nome)
            FreeCADGui.Control.closeDialog()
            self._esperar()

    def test_filtros_da_estrutura(self):
        import PrumoEstrutura as E
        import PrumoSelecao as S
        sk = esboco_linhas(self.doc, [((0, 0), (800, 0)), ((800, 0), (800, 500))], "XZ")
        est = E.criar(self.doc, sk, TQ50)
        self.doc.recompute()
        b0 = E.barras_de(est)[0]
        self.assertEqual(S.FILTROS["estruturas"](b0, ()), [(est.Label, est)])
        self.assertEqual(S.FILTROS["barras"](b0, ()), [(b0.Label, b0)])
        self.assertEqual(E._filtro_esqueleto(sk, ()), [(sk.Label, sk)])
        self.assertEqual(E._filtro_esqueleto(b0, ()), [])
        self.assertEqual(len(E._filtro_estrutura_ou_barras(est, ())), 1)


class T35PropriedadesDaPeca(unittest.TestCase):
    """Código, denominação, revisão e material da peça na lista de materiais e na legenda."""

    def setUp(self):
        self.doc = novo_doc("PrumoTestePropriedades")
        FreeCAD.setActiveDocument(self.doc.Name)
        import PrumoPropriedades
        self.P = PrumoPropriedades
        PrumoPropriedades.install()

    def tearDown(self):
        if FreeCAD.GuiUp:
            FreeCADGui.Selection.clearSelection()
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _esperar(self):
        for _ in range(5):
            if FreeCAD.GuiUp:
                FreeCADGui.updateGui()
            QtCore.QCoreApplication.processEvents()

    def _peca(self, nome="Suporte"):
        b = self.doc.addObject("Part::Box", nome)
        b.Length, b.Width, b.Height = 100, 50, 10
        self.doc.recompute()
        return b

    def _a36(self):
        uuids = [u for n, u in self.P.materiais_prumo() if n == "ASTM A36"]
        if not uuids:
            self.skipTest("biblioteca Prumo não carregada")
        return uuids[0]

    def test_garantir_cria_as_propriedades(self):
        b = self.P.garantir(self._peca())
        for nome, _r, _i, _d in self.P.CAMPOS:
            self.assertIn(nome, b.PropertiesList)
        self.assertEqual(b.getGroupOfProperty("Codigo"), self.P.GRUPO)
        self.P.garantir(b)  # segunda vez não falha

    def test_legenda_da_peca(self):
        b = self.P.garantir(self._peca())
        b.Codigo, b.Denominacao, b.Revisao = "SW-101", "Suporte do motor", "B"
        self.P.definir_material(b, self._a36())
        self.doc.recompute()
        v = self.P.legenda_de(b)
        self.assertEqual(v["titulo"], "SUPORTE DO MOTOR")
        self.assertEqual(v["numero"], "SW-101")
        self.assertEqual(v["revisao"], "B")
        self.assertEqual(v["material"], "ASTM A36")
        import PrumoUtil
        self.assertEqual(v["massa"], PrumoUtil.fmt(100 * 50 * 10 * 7850e-9, 3))   # 100×50×10 mm³ × 7850 kg/m³

    def test_lista_de_materiais_com_codigo_e_acabamento(self):
        import PrumoBOM
        a = self.P.garantir(self._peca("A"))
        a.Codigo, a.Denominacao, a.Acabamento = "SW-1", "Chapa de apoio", "zincado"
        b = self.P.garantir(self._peca("B"))
        b.Codigo, b.Denominacao, b.Acabamento = "SW-1", "Chapa de apoio", "zincado"
        self.doc.recompute()
        linhas = PrumoBOM.coletar([a, b])
        self.assertEqual(len(linhas), 1, "mesmo código e material: uma linha só")
        self.assertEqual(linhas[0].qtd, 2)
        self.assertEqual(linhas[0].codigo, "SW-1")
        self.assertEqual(linhas[0].denominacao, "Chapa de apoio")
        self.assertIn("zincado", linhas[0].obs)
        sh = PrumoBOM.gravar_planilha(self.doc, linhas)
        self.assertEqual(sh.get("C2"), "SW-1")
        self.assertEqual(sh.get("D2"), "Chapa de apoio")

    def test_folha_ligada_acompanha_a_peca(self):
        import PrumoFolhas
        b = self.P.garantir(self._peca())
        b.Codigo, b.Denominacao, b.Revisao = "SW-200", "Suporte", "0"
        self.doc.recompute()
        page = PrumoFolhas.nova_folha(self.doc, "A4", "NBR16752", True, None, [b])
        self.assertIs(page.PrumoPeca, b)
        et = page.Template.EditableTexts
        self.assertEqual(et.get("numero"), "SW-200")
        self.assertEqual(et.get("titulo"), "SUPORTE")
        # muda a peça: a legenda acompanha
        b.Revisao = "1"
        b.Denominacao = "Suporte reforçado"
        self.doc.recompute()
        self._esperar()
        et = page.Template.EditableTexts
        self.assertEqual(et.get("revisao"), "1")
        self.assertEqual(et.get("titulo"), "SUPORTE REFORÇADO")
        # material novo: massa e material na legenda
        self.P.definir_material(b, self._a36())
        self.doc.recompute()
        self._esperar()
        et = page.Template.EditableTexts
        self.assertEqual(et.get("material"), "ASTM A36")
        # legenda manual: desligar a automática
        page.LegendaAutomatica = False
        b.Revisao = "2"
        self.doc.recompute()
        self._esperar()
        self.assertEqual(page.Template.EditableTexts.get("revisao"), "1")

    def test_folha_de_varias_pecas_nao_liga(self):
        import PrumoFolhas
        a, b = self._peca("A"), self._peca("B")
        page = PrumoFolhas.nova_folha(self.doc, "A3", "NBR16752", False, None, [a, b])
        self.assertNotIn("PrumoPeca", page.PropertiesList)

    def test_painel_de_propriedades(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        b = self._peca()
        p = self.P.PainelPropriedades()
        self.assertTrue(p.pendencia())
        p.peca.aceitar(b)
        p.campos["Codigo"].setText("SW-300")
        p.campos["Denominacao"].setText("Base")
        i = p.material.findText("ASTM A36")
        if i >= 0:
            p.material.setCurrentIndex(i)
        self.assertTrue(p.accept())
        self.assertEqual(b.Codigo, "SW-300")
        if i >= 0:
            self.assertEqual(self.P.material(b), "ASTM A36")
        self.assertIn("Prumo_Propriedades", FreeCADGui.Command.listAll())


RAPIDOS = [T11CotasNaTela, T12Massa, T13MenuContexto, T14ListaMateriais, T15FolhasABNT, T16Perfis,
           T17Estrutura, T18ChapaMetalica, T19VasoPressao, T20Fixadores, T21EnquadrarEsboco,
           T22EstruturaGrupos, T23EstruturaCantos, T24EstruturaExtras,
           T25EstruturaInterface, T26Versao, T27Exemplos, T28TraducaoEArvore, T29GuiaEstrutura,
           T30Faixa, T31Bancadas, T32Arvore, T33PaineisVisuais,
           T34FluxoDeSelecao, T35PropriedadesDaPeca]
