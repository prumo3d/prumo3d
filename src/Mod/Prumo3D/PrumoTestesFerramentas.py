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

    def _local(self, est, b):
        """(umin, umax, vmin, vmax) da seção da barra medidos a partir da linha, nos eixos da seção."""
        import PrumoEstrutura as E
        eds = E.arestas(est.Esqueleto)
        sec = E.Secao(est, eds, b.Indice, E._normal_esqueleto(eds))
        e = eds[b.Indice]
        meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
        corte = b.Shape.slice(sec.t, meio.dot(sec.t))
        pts = [p - meio for w in corte for ed in w.Edges for p in ed.discretize(72)]
        us = [p.dot(sec.u) for p in pts]
        vs = [p.dot(sec.v) for p in pts]
        return min(us), max(us), min(vs), max(vs)

    def test_ponto_de_fixacao_em_todos_os_perfis(self):
        """A linha fica no ponto escolhido da seção (caixa envolvente), para cada família, com e sem
        espelhar e com giro."""
        import PrumoEstrutura as E
        import PrumoPerfis
        sk = esboco_linhas(self.doc, [((0, 0), (1000, 0))], "XY")
        tol = 0.05
        for f in PrumoPerfis.familias():
            nome = f["itens"][len(f["itens"]) // 2]["nome"]
            larg, alt = PrumoPerfis.dimensoes(PrumoPerfis.perfil(nome))
            for espelhar in (False, True):
                for fx in E.FIXACOES:
                    if fx == "Centroide":
                        continue
                    est = E.criar(self.doc, sk, nome, alinhamento=fx, espelhar=espelhar)
                    b = E.barras_de(est)[0]
                    umin, umax, vmin, vmax = self._local(est, b)
                    msg = (nome, fx, espelhar, round(umin, 2), round(umax, 2), round(vmin, 2), round(vmax, 2))
                    self.assertAlmostEqual(umax - umin, larg, delta=tol, msg=msg)
                    self.assertAlmostEqual(vmax - vmin, alt, delta=tol, msg=msg)
                    vert, horiz = fx.split(" ") if " " in fx else ("Meio", "centro")
                    alvo_v = {"Sup.": vmax, "Inf.": vmin}.get(vert, (vmin + vmax) / 2.0)
                    alvo_u = {"esquerdo": umin, "direito": umax}.get(horiz, (umin + umax) / 2.0)
                    self.assertAlmostEqual(alvo_v, 0.0, delta=tol, msg=msg)
                    self.assertAlmostEqual(alvo_u, 0.0, delta=tol, msg=msg)
                    for o in E.barras_de(est):
                        self.doc.removeObject(o.Name)
                    self.doc.removeObject(est.Name)

    def test_lado_da_secao_nao_depende_do_sentido_da_linha(self):
        """Quadro com linhas desenhadas em sentidos misturados: todas as barras ficam do mesmo lado."""
        import PrumoEstrutura as E
        for plano in ("XZ", "XY"):
            sk = esboco_linhas(self.doc, [((0, 0), (1000, 0)), ((1000, 600), (1000, 0)), ((0, 600), (1000, 600)),
                                          ((0, 0), (0, 600))], plano, "Misto" + plano)
            centro = E.centro_esqueleto(sk)
            normal = FreeCAD.Vector(0, -1, 0) if plano == "XZ" else FreeCAD.Vector(0, 0, 1)
            for fx in ("Sup. centro", "Inf. esquerdo", "Meio direito"):
                for giro in (0.0, 90.0):
                    est = E.criar(self.doc, sk, "W 150 x 13,0", rotacao=giro, alinhamento=fx)
                    eds = E.arestas(sk)
                    fora, prof = [], []
                    for b in E.barras_de(est):
                        e = eds[b.Indice]
                        meio = e.valueAt((e.FirstParameter + e.LastParameter) / 2.0)
                        d = b.Shape.BoundBox.Center - meio
                        w = meio - centro
                        w = w - normal * w.dot(normal)
                        w.normalize()
                        fora.append(round(d.dot(w), 2))
                        prof.append(round(d.dot(normal), 2))
                    self.assertEqual(len(set(fora)), 1, (plano, fx, giro, fora))
                    self.assertEqual(len(set(prof)), 1, (plano, fx, giro, prof))
                    for b in E.barras_de(est):
                        self.assertTrue(b.Shape.isValid())
                        self.assertEqual(len(b.Shape.Solids), 1)
                    for o in E.barras_de(est):
                        self.doc.removeObject(o.Name)
                    self.doc.removeObject(est.Name)

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
        p = V.PainelVaso()
        try:
            p.S.setValue(0.0)
            self.assertIn("tensão admissível", p.pendencia())
            p.S.setValue(138.0)
            self.assertIsNone(p.pendencia())
        finally:
            p.form.deleteLater() if hasattr(p.form, "deleteLater") else None

    def test_unidades_de_pressao(self):
        import PrumoVaso as V
        self.assertAlmostEqual(V._unidade("kgf/cm²")[1], 0.0980665, 9)
        self.assertAlmostEqual(V._unidade("psi")[1] * 145.0377377, 1.0, 6)
        self.assertEqual(V.fmt_p(1.0, "kgf/cm²"), "10,20 kgf/cm² (1,000 MPa)")
        self.assertEqual(V.fmt_p(1.0, "psi"), "145,0 psi (1,000 MPa)")
        v = V.criar(self.doc, 1000, 2000, 1.0, 138.0, 1.0)
        v.UnidadePressao = "kgf/cm²"
        self.doc.recompute()
        self.assertIn("Pressão de projeto: 10,20 kgf/cm² (1,000 MPa)", V.memoria(v))
        self.assertTrue(any("kgf/cm² (" in l for l in V.tabela_dados(v)))
        if not FreeCAD.GuiUp:
            return
        p = V.PainelVaso()
        try:
            p.P_.setValue(1.5)
            p.unid_p.setCurrentText("psi")
            self.assertAlmostEqual(p.P_.value(), 217.6, 1)          # 1,5 MPa em psi
            self.assertAlmostEqual(p.pressao_mpa(), 1.5, 3)
            p.unid_p.setCurrentText("kgf/cm²")
            self.assertAlmostEqual(p.P_.value(), 15.30, 2)
            p.P_.setValue(10.0)                                      # 10 kgf/cm²
            pr = p.props()
            self.assertAlmostEqual(pr["PressaoProjeto"], 0.980665, 6)
            self.assertEqual(pr["UnidadePressao"], "kgf/cm²")
            p.carregar(v)
            self.assertEqual(p.unid_p.currentText(), "kgf/cm²")
            self.assertAlmostEqual(p.pressao_mpa(), 1.0, 3)
        finally:
            p.form.deleteLater() if hasattr(p.form, "deleteLater") else None


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

    def _esperar(self, n=10):
        for _ in range(n):
            FreeCADGui.updateGui()
            QtCore.QCoreApplication.processEvents()

    def _estruturas(self):
        import PrumoEstrutura
        return [o for o in self.doc.Objects if PrumoEstrutura.eh_estrutura(o)]

    def test_ao_vivo_clicar_linhas_cria_barras_na_hora(self):
        """Como no SolidWorks: clicar na linha do desenho cria a barra na hora; Aplicar grava."""
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        d = E.DialogoEstrutura(self.sk, ao_vivo=True, linhas=[])
        # nasce zerado: sem grupo, sem estrutura; clicar avisa
        self.assertEqual(d.grupos_ed, [])
        self.assertIsNone(d.est)
        self.assertFalse(d.editor.isEnabled())
        self.assertTrue(self.sk.ViewObject.Visibility, "o esboço precisa aparecer para o clique")
        d.clicar_linha(0)
        self.assertIn("Crie um grupo", d.aviso.text())
        self.assertEqual(d.novo_grupo(), 0)
        self.assertEqual(d.grupos_ed[0]["nome"], "Grupo 1")
        self.assertTrue(d.editor.isEnabled())
        est = d.est
        self.assertIsNotNone(est, "a prévia não criou a estrutura")
        self.assertEqual(E.barras_de(est), [])
        d.clicar_linha(0)
        d.clicar_linha(2)
        self.assertEqual([b.Indice for b in E.barras_de(est)], [0, 2])
        d.clicar_linha(0)                      # clicar de novo tira
        self.assertEqual([b.Indice for b in E.barras_de(est)], [2])
        # clique na tela (observador de seleção)
        FreeCADGui.Selection.addSelection(self.sk, "Edge2")
        self._esperar()
        self.assertEqual([b.Indice for b in E.barras_de(est)], [1, 2])
        self.assertEqual(d.tabela.item(1, 0).text().split(" · ")[0], "2")
        self.assertNotIn("sem barra", d.tabela.item(1, 0).text())
        d._ok()
        self.assertEqual(list(est.GrupoDaAresta), [E.SEM_BARRA, 0, 0, E.SEM_BARRA])
        self.assertEqual(est.NomeGrupo, "Grupo 1")
        self.assertFalse(self.sk.ViewObject.Visibility)
        self.assertEqual(len(self._estruturas()), 1)

    def test_ao_vivo_dois_grupos_remover_e_esboco(self):
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        d = E.DialogoEstrutura(self.sk, ao_vivo=True, linhas=[])
        d.novo_grupo()
        d.nome.setText("Vigas")
        d.nome.textEdited.emit("Vigas")
        self._escolher_perfil(d, "W 150 x 13,0")
        d.clicar_linha(0)
        d.clicar_linha(2)
        d.novo_grupo()
        self._escolher_perfil(d, TQ50)
        d.clicar_linha(1)
        d.clicar_linha(3)
        d._timer.stop()
        d._aplicar_ao_vivo()
        est = d.est
        self.assertEqual([b.Perfil for b in E.barras_de(est)], ["W 150 x 13,0", TQ50, "W 150 x 13,0", TQ50])
        # botão do esboço
        d.bt_esboco.setChecked(False)
        self.assertFalse(self.sk.ViewObject.Visibility)
        d.bt_esboco.setChecked(True)
        self.assertTrue(self.sk.ViewObject.Visibility)
        # remover o primeiro grupo: as linhas dele ficam sem barra e o segundo passa a ser o primeiro
        d.lista.setCurrentRow(0)
        d.remover_grupo()
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertEqual([b.Indice for b in E.barras_de(est)], [1, 3])
        self.assertEqual(est.Perfil, TQ50)
        d._ok()
        self.assertEqual(est.NomeGrupo, "Grupo 2")
        # reabrir para editar: os grupos e as linhas sem barra voltam iguais
        d2 = E.DialogoEstrutura(self.sk, est, ao_vivo=True)
        self.assertEqual([g["nome"] for g in d2.grupos_ed], ["Grupo 2"])
        self.assertEqual(d2.da_aresta, [E.SEM_BARRA, 0, E.SEM_BARRA, 0])
        d2.reject()

    def test_ao_vivo_opcoes_atualizam_a_previa(self):
        """Perfil, giro e ponto de fixação mudam a barra na hora, antes de Aplicar."""
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        d = E.DialogoEstrutura(self.sk, ao_vivo=True, linhas=[0, 1, 2, 3])
        est = d.est
        b0 = E.barras_de(est)[0]
        bb0 = b0.Shape.BoundBox
        d.fixacao.setCurrentText("Sup. centro")
        self._esperar()
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertEqual(est.Fixacao, "Sup. centro")
        self.assertNotAlmostEqual(b0.Shape.BoundBox.ZMax, bb0.ZMax, places=3)
        d.giro.setValue(90)
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertAlmostEqual(float(est.Rotacao), 90.0)
        self._escolher_perfil(d, TQ50)
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertEqual(b0.Perfil, TQ50)
        d.reject()
        self.assertEqual(self._estruturas(), [], "Cancelar não desfez a estrutura da prévia")

    def test_ao_vivo_cancelar_edicao_volta_ao_que_era(self):
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        est = E.criar(self.doc, self.sk, "W 150 x 13,0")
        d = E.DialogoEstrutura(self.sk, est, ao_vivo=True)
        self._escolher_perfil(d, TQ50)
        d.clicar_linha(3)                         # está no Padrão: sai
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertEqual(len(E.barras_de(est)), 3)
        self.assertEqual(E.barras_de(est)[0].Perfil, TQ50)
        d.reject()
        self.doc.recompute()
        bs = E.barras_de(est)
        self.assertEqual(len(bs), 4)
        self.assertEqual([b.Perfil for b in bs], ["W 150 x 13,0"] * 4)
        self.assertEqual(list(est.GrupoDaAresta), [0, 0, 0, 0])

    def test_giro_individual_por_barra(self):
        """Giro só de uma barra (somado ao do grupo), ao vivo; reabrir mostra o giro na linha."""
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        d = E.DialogoEstrutura(self.sk, ao_vivo=True, linhas=[0, 1, 2, 3])
        est = d.est
        self._escolher_perfil(d, "W 150 x 13,0")    # perfil não simétrico: o giro muda a caixa
        d._timer.stop()
        d._aplicar_ao_vivo()
        b1 = [b for b in E.barras_de(est) if b.Indice == 1][0]
        bb = b1.Shape.BoundBox
        d.tabela.selectRow(1)
        d.girar_linhas([1], 90.0)
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertEqual(E.rotacoes_individuais(est), [0.0, 90.0, 0.0, 0.0])
        self.assertAlmostEqual(float(E.parametros(est, 1)["giro"]), 90.0)
        self.assertAlmostEqual(float(E.parametros(est, 0)["giro"]), 0.0)
        bb2 = b1.Shape.BoundBox
        self.assertNotAlmostEqual(bb.XLength, bb2.XLength, places=1, msg="a barra não girou")
        d.giros[2].setValue(45.0)
        d._timer.stop()
        d._aplicar_ao_vivo()
        self.assertAlmostEqual(E.rotacoes_individuais(est)[2], 45.0)
        d._ok()
        d2 = E.DialogoEstrutura(self.sk, est, ao_vivo=True)
        self.assertEqual(len(d2.grupos_ed), 1, "o giro de uma barra não deve virar grupo")
        self.assertEqual(d2.giro_linha, [0.0, 90.0, 45.0, 0.0])
        self.assertAlmostEqual(d2.giros[1].value(), 90.0)
        d2.reject()
        self.assertEqual(E.rotacoes_individuais(est), [0.0, 90.0, 45.0, 0.0])

    def test_trocar_familia_atualiza_o_grupo(self):
        """Trocar só a família (cai no primeiro perfil da lista) também muda o perfil do grupo."""
        import PrumoEstrutura as E
        import PrumoPerfis
        import PrumoUtil
        FreeCAD.ParamGet(PrumoUtil.PARAM_PATH).SetString("UltimoPerfil", TQ50)
        d = E.DialogoEstrutura(self.sk)
        fam = PrumoPerfis.perfil("W 150 x 13,0")["familia"]
        d.sel.familia.setCurrentIndex(d.sel.familia.findData(fam))
        primeiro = PrumoPerfis.familia(fam)["itens"][0]["nome"]
        self.assertEqual(d.grupos_ed[0]["perfil"], primeiro)
        d.close()

    def test_linha_sem_barra_nos_cantos(self):
        """Retângulo sem a linha de baixo: os cantos dela viram pontas livres."""
        import PrumoEstrutura as E
        est = E.criar(self.doc, self.sk, "W 150 x 13,0", linhas_sem_barra=[0])
        self.assertEqual([b.Indice for b in E.barras_de(est)], [1, 2, 3])
        self.assertEqual(len(E.cantos(est)), 2)
        dd = __import__("PrumoPerfis").perfil("W 150 x 13,0")
        b1 = E.barras_de(est)[0]
        self.assertAlmostEqual(b1.CorteInicio.Value, 0.0, places=6, msg="ponta sem vizinha deveria ser reta")
        # devolver a linha: a barra volta e o canto também
        padrao, extras = E.grupos_para_edicao(est)
        E.editar(est, padrao, extras, linhas_sem_barra=[])
        self.assertEqual(len(E.barras_de(est)), 4)
        self.assertEqual(len(E.cantos(est)), 4)
        self.assertTrue(dd)

    def test_numeros_das_linhas_na_tela(self):
        import PrumoEstrutura as E
        d = E.DialogoEstrutura(self.sk)
        self.assertIsNotNone(d.etiquetas)
        self.assertEqual(len(d.etiquetas), 4)
        d.tabela.selectRow(2)
        self.assertEqual(d.etiquetas.destacado, 2)
        sel = FreeCADGui.Selection.getSelectionEx()
        self.assertEqual(sel[0].SubElementNames, ("Edge3",))
        self.assertIn("de (", d.tabela.item(2, 2).text())
        raiz = d.etiquetas.raiz
        grafo = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
        self.assertGreaterEqual(grafo.findChild(raiz), 0)
        d.close()
        self.assertEqual(grafo.findChild(raiz), -1, "os números ficaram na tela depois de fechar")

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
        self.assertEqual(PrumoVersao.texto(), ("%s %s" % (PrumoVersao.VERSAO, PrumoVersao.CANAL)).strip())
        self.assertRegex(PrumoVersao.VERSAO, r"^\d+\.\d+(\.\d+)?$")
        self.assertRegex(PrumoVersao.base_freecad(), r"^\d+\.\d+(\.\d+)?$")

    def test_versao_do_rotulo_da_compilacao(self):
        import PrumoVersao as V
        self.assertEqual(V.separar("0.3.0-beta"), ("0.3.0", "beta"))
        self.assertEqual(V.separar("v1.0.0"), ("1.0.0", ""))
        self.assertEqual(V.separar("1.2.0-rc1"), ("1.2.0", "rc1"))

    def test_informacoes_do_sistema(self):
        import PrumoVersao
        txt = PrumoVersao.info_sistema()
        for chave in ("Prumo 3D " + PrumoVersao.texto(), "Base: FreeCAD", "Sistema:", "Python:", "Pasta de dados:"):
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
        import PrumoVersao
        self.assertIn(PrumoVersao.texto(), FreeCADGui.getMainWindow().windowTitle())

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
    def test_opcoes_tem_destaque_fora_do_painel(self):
        """Empurra/Puxa no Assistente de simulação: o botão marcado aparece destacado."""
        import PrumoPainel as P
        o = P.Opcoes([("empurra", "Empurra", "info", ""), ("puxa", "Puxa", "info", "")])
        self.assertIn("PrumoOpcao", o.styleSheet())
        self.assertIn("checked", o.styleSheet())
        o.deleteLater()

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

    # ---- prévia ao vivo e marcas Início/Fim
    def _conta(self, prop):
        return [o for o in self.doc.Objects if prop in o.PropertiesList]

    def _fechar(self):
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()

    def test_placa_previa_ao_vivo_e_marcas(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        _est, bs = self._estrutura()
        p = X.PainelPlaca().mostrar()
        try:
            self.assertEqual(self._conta("DistanciaBorda"), [])
            p.barras.aceitar(bs[1])
            p.atualizar_previa()
            placas = self._conta("DistanciaBorda")
            self.assertEqual(len(placas), 1, "a placa não apareceu na hora")
            # marcas Início e Fim na barra, com a ponta escolhida destacada
            self.assertIsNotNone(p._etiquetas)
            self.assertEqual(len(p._etiquetas), 2)
            p.ponta.setCurrentText("Início")
            p.atualizar_previa()
            z_ini = self._conta("DistanciaBorda")[0].Shape.BoundBox.Center
            self.assertEqual(p._etiquetas.destacado, [0], "a ponta escolhida não ficou destacada")
            p.ponta.setCurrentText("Fim")
            p.atualizar_previa()
            placas = self._conta("DistanciaBorda")
            self.assertEqual(len(placas), 1, "a prévia antiga ficou no desenho")
            self.assertGreater((placas[0].Shape.BoundBox.Center - z_ini).Length, 100.0)
            p.esp.setValue(25.0)
            p.atualizar_previa()
            self.assertEqual(len(self._conta("DistanciaBorda")), 1)
            self.assertTrue(p.reject())
        finally:
            self._fechar()
        self.assertEqual(self._conta("DistanciaBorda"), [], "Cancelar não tirou a prévia")
        self.assertIsNone(p._etiquetas, "as marcas ficaram na tela")

    def test_previa_ok_grava_e_desfazer_tira_de_uma_vez(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        _est, bs = self._estrutura()
        p = X.PainelTampa().mostrar()
        try:
            p.barras.aceitar(bs[0])
            p.pontas.setCurrentText("As duas pontas")
            p.atualizar_previa()
            self.assertEqual(len(self._conta("Recuo")), 2)
            p.pontas.setCurrentText("Início")
            p.atualizar_previa()
            self.assertEqual(len(self._conta("Recuo")), 1)
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertEqual(len(self._conta("Recuo")), 1)
        self.doc.undo()
        self.assertEqual(self._conta("Recuo"), [], "OK deveria ser um passo só no Desfazer")

    def test_reforco_previa_e_marcas_das_barras(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        _est, bs = self._estrutura()
        p = X.PainelReforco().mostrar()
        try:
            p.barras.aceitar(bs[0])
            p.barras.aceitar(bs[1])
            p.atualizar_previa()
            refs = self._conta("Perna1")
            self.assertEqual(len(refs), 1)
            v1 = refs[0].Shape.Volume
            p.perna1.setValue(300.0)
            p.atualizar_previa()
            refs = self._conta("Perna1")
            self.assertEqual(len(refs), 1)
            self.assertGreater(refs[0].Shape.Volume, v1)
            self.assertEqual(len(p._etiquetas), 2)
        finally:
            p.reject()
            self._fechar()
        self.assertEqual(self._conta("Perna1"), [])

    def test_solda_previa(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        est, _bs = self._estrutura()
        p = X.PainelSolda().mostrar()
        try:
            p.pecas.aceitar(est)
            p.atualizar_previa()
            n = len(X.lista_de_soldas([est]))
            self.assertGreaterEqual(n, 4)
            p.perna.setValue(8.0)
            p.atualizar_previa()
            self.assertEqual(len(X.lista_de_soldas([est])), n, "a prévia duplicou os cordões")
        finally:
            p.reject()
            self._fechar()
        self.assertEqual(len(X.lista_de_soldas([est])), 0)

    # ---- duplo clique na árvore: o mesmo painel, editando o objeto
    def _duplo_clique(self, obj):
        self.assertTrue(obj.ViewObject.Proxy.doubleClicked(obj.ViewObject))
        import PrumoPainel as P
        p = P._ATIVO["painel"]
        self.assertIsNotNone(p)
        return p

    def test_duplo_clique_edita_placa_no_lugar(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        _est, bs = self._estrutura("W 150 x 13,0")
        placa = X.criar_placa_base(bs[1], "Início", Espessura=16.0)
        nome = placa.Name
        p = self._duplo_clique(placa)
        try:
            self.assertIs(p.editando, placa)
            self.assertEqual(p.barras.valores(), [bs[1]])
            self.assertAlmostEqual(p.esp.value(), 16.0)
            self.assertEqual(p.ponta.currentText(), "Início")
            p.esp.setValue(30.0)
            p.atualizar_previa()
            self.assertAlmostEqual(placa.Espessura.Value, 30.0, msg="a prévia não mexeu na placa")
            self.assertEqual(len(self._conta("DistanciaBorda")), 1, "a edição criou outra placa")
            self.assertTrue(p.reject())
        finally:
            self._fechar()
        self.doc.recompute()
        self.assertAlmostEqual(placa.Espessura.Value, 16.0, msg="Cancelar não voltou a espessura")
        # de novo, agora com OK
        p = self._duplo_clique(placa)
        try:
            p.esp.setValue(25.0)
            p.ponta.setCurrentText("Fim")
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertEqual(placa.Name, nome)
        self.assertAlmostEqual(placa.Espessura.Value, 25.0)
        self.assertEqual(placa.Ponta, "Fim")
        self.doc.undo()
        self.assertAlmostEqual(placa.Espessura.Value, 16.0)

    def test_duplo_clique_reforco_tampa_solda(self):
        import PrumoEstruturaExtras as X
        self.doc.UndoMode = 1
        _est, bs = self._estrutura()
        ref = X.criar_reforco(bs[0], bs[1], Perna1=150.0)
        p = self._duplo_clique(ref)
        try:
            self.assertEqual(p.barras.valores(), [bs[0], bs[1]])
            p.perna1.setValue(220.0)
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertAlmostEqual(ref.Perna1.Value, 220.0)
        tampa = X.criar_tampa(bs[0], "Início")
        p = self._duplo_clique(tampa)
        try:
            self.assertEqual(p.pontas.currentText(), "Início")
            p.pontas.setCurrentText("Fim")
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertEqual(tampa.Ponta, "Fim")
        solda = X.criar_solda([bs[0], bs[1]], 5.0)
        p = self._duplo_clique(solda)
        try:
            self.assertEqual(p.pecas.valores(), [bs[0], bs[1]])
            p.perna.setValue(7.0)
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertAlmostEqual(solda.Perna.Value, 7.0)
        self.assertEqual(len([o for o in self.doc.Objects if "Perna1" in o.PropertiesList]), 1)

    def test_duplo_clique_estrutura_e_barra(self):
        import PrumoEstrutura as E
        est, bs = self._estrutura()
        self.assertTrue(est.ViewObject.Proxy.doubleClicked(est.ViewObject))
        d = E._dialogos[-1]
        self.assertIs(d.est, est)
        self.assertTrue(d.ao_vivo)
        d.reject()
        self.assertTrue(bs[2].ViewObject.Proxy.doubleClicked(bs[2].ViewObject))
        d = E._dialogos[-1]
        self.assertEqual(sorted({ix.row() for ix in d.tabela.selectedIndexes()}), [bs[2].Indice])
        d.reject()

    def test_duplo_clique_fixador(self):
        import PrumoFixadores as F
        self.doc.UndoMode = 1
        o = F.criar(self.doc, "sextavado", "M8", 30.0)
        p = self._duplo_clique(o)
        try:
            self.assertEqual(p.diam.currentText(), "M8")
            p.diam.setCurrentText("M10")
            p.comp.setEditText("40")
            p.atualizar_previa()
            self.assertEqual(o.Diametro, "M10")
            self.assertEqual(len([x for x in self.doc.Objects if x.TypeId == "Part::FeaturePython"
                                  and "Diametro" in x.PropertiesList]), 1)
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertIn("M10", o.Label)

    # ---- cantos, trocar perfil, modelos e propriedades ao vivo
    def test_cantos_ao_vivo(self):
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        est, bs = self._estrutura("W 150 x 13,0")      # uniao Topo: cortes retos
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 0.0, places=4)
        d = E.DialogoCantos(est, ao_vivo=True)
        self.assertEqual(len(d.etiquetas), 4, "os cantos não foram marcados na tela")
        d.escolher(0, E.OPCOES_ESQUADRIA[0])           # meia-esquadria
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 45.0, places=3, msg="a prévia não apareceu")
        d.reject()
        self.doc.recompute()
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 0.0, places=4, msg="Cancelar não voltou")
        self.assertIsNone(d.etiquetas)
        d = E.DialogoCantos(est, ao_vivo=True)
        d.escolher(0, E.OPCOES_ESQUADRIA[0])
        d._ok()
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 45.0, places=3)
        self.doc.undo()
        self.doc.recompute()
        self.assertAlmostEqual(bs[0].CorteInicio.Value, 0.0, places=4)

    def test_trocar_perfil_ao_vivo(self):
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        _est, bs = self._estrutura("W 150 x 13,0")
        visto = {}
        teste = self

        class Cmd(E.CmdTrocarPerfil):
            def __init__(self, ok):
                self.ok = ok

            def _executar_dialogo(self, d):
                teste._escolher_perfil(self, TQ50)
                visto["perfil"] = bs[0].Perfil
                return self.ok

        Cmd.sel = property(lambda self: self.__dict__["sel"], lambda self, v: self.__dict__.__setitem__("sel", v))
        Cmd(False).trocar([bs[0]])
        self.assertEqual(visto["perfil"], TQ50, "a troca não apareceu na hora")
        self.assertEqual(bs[0].Perfil, "W 150 x 13,0", "Cancelar não voltou o perfil")
        Cmd(True).trocar([bs[0]])
        self.assertEqual(bs[0].Perfil, TQ50)

    def _escolher_perfil(self, cmd, nome):
        import PrumoPerfis
        it = PrumoPerfis.perfil(nome)
        cmd.sel.familia.setCurrentIndex(cmd.sel.familia.findData(it["familia"]))
        cmd.sel.perfil.setCurrentIndex(cmd.sel.perfil.findData(nome))

    def test_modelo_ao_vivo(self):
        import PrumoModelos as M
        self.doc.UndoMode = 1
        modelos = lambda: [o for o in self.doc.Objects if "TipoModelo" in o.PropertiesList]
        p = M.PainelModelo().mostrar()
        try:
            p.atualizar_previa()
            self.assertEqual(len(modelos()), 1, "a peça não apareceu na hora")
            p.tipo.setCurrentIndex(p.tipo.findData("flange"))
            p.atualizar_previa()
            self.assertEqual([o.TipoModelo for o in modelos()], ["flange"], "a prévia antiga ficou")
            self.assertTrue(p.reject())
        finally:
            self._fechar()
        self.assertEqual(modelos(), [])
        o = M.criar(self.doc, "placa", Comprimento=300)
        p = M.PainelModelo(o).mostrar()
        try:
            p.campos["Comprimento"].setValue(450)
            p.atualizar_previa()
            self.assertAlmostEqual(o.Shape.BoundBox.XLength, 450, places=4)
            self.assertTrue(p.reject())
        finally:
            self._fechar()
        self.doc.recompute()
        self.assertAlmostEqual(o.Shape.BoundBox.XLength, 300, places=4, msg="Cancelar não voltou a medida")

    def test_propriedades_ao_vivo(self):
        import PrumoPropriedades as PP
        self.doc.UndoMode = 1
        b = self.doc.addObject("Part::Box", "Bloco")
        self.doc.recompute()
        p = PP.PainelPropriedades().mostrar()
        try:
            p.peca.aceitar(b)
            p.campos["Codigo"].setText("SW-900")
            p.atualizar_previa()
            self.assertEqual(b.Codigo, "SW-900")
            self.assertTrue(p.accept())
        finally:
            self._fechar()
        self.assertEqual(b.Codigo, "SW-900")
        p = PP.PainelPropriedades().mostrar()
        try:
            p.peca.aceitar(b)
            p.campos["Codigo"].setText("OUTRO")
            p.atualizar_previa()
            self.assertEqual(b.Codigo, "OUTRO")
            self.assertTrue(p.reject())
        finally:
            self._fechar()
        self.assertEqual(b.Codigo, "SW-900", "Cancelar não voltou o código")

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

    def test_nao_fecha_tarefa_do_freecad_em_andamento(self):
        """Com um esboço em edição, abrir um painel do Prumo avisa e não fecha a edição."""
        import PrumoPainel as P
        import PrumoPropriedades as PP
        body = self.doc.addObject("PartDesign::Body", "Corpo")
        sk = body.newObject("Sketcher::SketchObject", "Esboco")
        self.doc.recompute()
        FreeCADGui.getDocument(self.doc.Name).setEdit(sk.Name)
        self._esperar()
        self.assertTrue(FreeCADGui.Control.activeDialog())
        p = PP.PainelPropriedades().mostrar()
        self._esperar()
        self.assertFalse(p.aberto)
        self.assertTrue(FreeCADGui.Control.activeDialog(), "a edição do esboço foi fechada à força")
        self.assertIsNotNone(FreeCADGui.getDocument(self.doc.Name).getInEdit())
        aviso = P._ATIVO.get("aviso")
        if aviso is not None:
            aviso.close()
        FreeCADGui.getDocument(self.doc.Name).resetEdit()
        self._esperar()
        # painel do Prumo aberto: o novo substitui o anterior
        p1 = PP.PainelPropriedades().mostrar()
        self.assertTrue(p1.aberto)
        import PrumoInterferencia as I
        p2 = I.PainelInterferencia().mostrar()
        self._esperar()
        self.assertTrue(p2.aberto)
        self.assertFalse(p1._observando, "o painel anterior continuou observando a seleção")

    def _conjunto(self):
        """Peça furada dentro de uma Parte deslocada 500 mm em z."""
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
        return part, cut, aresta

    def test_resolver_caminho(self):
        import PrumoPainel as P
        part, cut, aresta = self._conjunto()
        self.assertEqual(P.resolver(part, "%s.Edge%d" % (cut.Name, aresta)), (cut, "Edge%d" % aresta))
        self.assertEqual(P.resolver(part, cut.Name + "."), (cut, ""))
        self.assertEqual(P.resolver(cut, "Face1"), (cut, "Face1"))
        self.assertEqual(P.resolver(cut, ""), (cut, ""))
        g = P.agrupar_selecao(part, ("%s.Face1" % cut.Name, "%s.Face2" % cut.Name))
        self.assertEqual(len(g), 1)
        self.assertIs(g[0][0], cut)
        self.assertEqual(g[0][1], ["Face1", "Face2"])

    def test_selecao_antes_e_depois_chegam_iguais(self):
        """Peça dentro de uma Parte: antes e depois de abrir o painel, a caixa recebe a peça (não a Parte)."""
        import PrumoPropriedades as PP
        part, cut, _a = self._conjunto()
        FreeCADGui.Selection.addSelection(self.doc.Name, part.Name, cut.Name + ".")
        p = PP.PainelPropriedades()
        try:
            self.assertEqual(p.peca.valores(), [cut], "seleção antes: veio a Parte em vez da peça")
        finally:
            p.close()
        FreeCADGui.Selection.clearSelection()
        p = PP.PainelPropriedades().mostrar()
        try:
            FreeCADGui.Selection.addSelection(self.doc.Name, part.Name, cut.Name + ".Face1")
            self._esperar()
            self.assertEqual(p.peca.valores(), [cut], "seleção depois: veio a Parte em vez da peça")
        finally:
            FreeCADGui.Control.closeDialog()

    def test_fixador_no_furo_de_peca_na_montagem(self):
        """Clicar no furo de uma peça dentro de uma Parte: o parafuso vai para a posição global."""
        import PrumoFixadores as F
        part, cut, aresta = self._conjunto()
        p = F.PainelFixador().mostrar()
        try:
            FreeCADGui.Selection.addSelection(self.doc.Name, part.Name, "%s.Edge%d" % (cut.Name, aresta))
            self._esperar()
            vs = p.furo.valores()
            self.assertEqual(len(vs), 1)
            self.assertAlmostEqual(vs[0][1].Base.z, 512.0, places=6)
        finally:
            FreeCADGui.Control.closeDialog()
        # seleção antes de abrir o painel: mesmo resultado
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.doc.Name, part.Name, "%s.Edge%d" % (cut.Name, aresta))
        p = F.PainelFixador()
        try:
            self.assertAlmostEqual(p.furo.valores()[0][1].Base.z, 512.0, places=6)
        finally:
            p.close()

    def test_chapa_recebe_a_face_clicada_dentro_da_parte(self):
        import PrumoChapa as C
        import PrumoPainel as P
        part, cut, _a = self._conjunto()
        g = P.agrupar_selecao(part, ("%s.Face6" % cut.Name,))
        obj, els, _c = g[0]
        self.assertEqual(C._filtro_chapa(obj, tuple(els))[0][1], (cut, "Face6"))

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
        rb.select_tab("peca", user=True)
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

    def test_legenda_digitada_a_mao_fica(self):
        """Nº do desenho e revisão digitados na legenda não voltam quando a peça muda."""
        import PrumoFolhas
        b = self._peca()
        self.doc.recompute()
        page = PrumoFolhas.nova_folha(self.doc, "A4", "NBR16752", True, None, [b])
        et = dict(page.Template.EditableTexts)
        et["numero"], et["revisao"] = "DES-012", "B"
        page.Template.EditableTexts = et
        b.Length = 120   # mexe na peça
        b.Label = "Suporte novo"
        self.doc.recompute()
        self._esperar()
        et = page.Template.EditableTexts
        self.assertEqual(et.get("numero"), "DES-012")
        self.assertEqual(et.get("revisao"), "B")
        self.assertEqual(et.get("titulo"), "SUPORTE NOVO", "o que a automática escreveu continua acompanhando")
        # título digitado à mão também fica
        et = dict(page.Template.EditableTexts)
        et["titulo"] = "MEU TÍTULO"
        page.Template.EditableTexts = et
        b.Label = "Outro nome"
        self.doc.recompute()
        self._esperar()
        self.assertEqual(page.Template.EditableTexts.get("titulo"), "MEU TÍTULO")

    def test_painel_folha_nao_apaga_titulo_digitado(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoFolhas
        a, b = self._peca("A"), self._peca("B")
        p = PrumoFolhas.PainelFolha()
        try:
            p.pecas.aceitar(a)
            self.assertEqual(p.campos["titulo"].text(), a.Label.upper())
            p.campos["titulo"].setText("CONJUNTO DA BASE")
            p.pecas.aceitar(b)
            self.assertEqual(p.campos["titulo"].text(), "CONJUNTO DA BASE")
        finally:
            p.close()

    def test_observador_nao_percorre_documento_sem_folha_ligada(self):
        """Sem folha ligada, mudar peças não chama a busca de folhas (documentos grandes)."""
        obs = self.P.install()
        chamadas = []
        original = self.P.folhas_da_peca
        self.P.folhas_da_peca = lambda *a, **k: chamadas.append(1) or original(*a, **k)
        try:
            caixas = [self._peca("B%d" % i) for i in range(20)]
            for c in caixas:
                c.Length = 30
            self.doc.recompute()
            self.assertEqual(chamadas, [])
            # com uma folha ligada passa a acompanhar (o cache vê a folha nova)
            import PrumoFolhas
            page = PrumoFolhas.nova_folha(self.doc, "A4", "NBR16752", True, None, [caixas[0]])
            caixas[0].Label = "Peça ligada"
            self.doc.recompute()
            self._esperar()
            self.assertTrue(chamadas)
            self.assertEqual(page.Template.EditableTexts.get("titulo"), "PEÇA LIGADA")
            # folha apagada: volta ao caso sem folhas
            self.doc.removeObject(page.Name)
            self.assertEqual(obs._folhas(self.doc), [])
        finally:
            self.P.folhas_da_peca = original

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


class T36ChapaFatorKeDXF(unittest.TestCase):
    """Fator K por material, espessuras comerciais e planificação em DXF."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteChapaK")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.pasta = tempfile.mkdtemp()

    def tearDown(self):
        fechar(self.doc)

    def _chapa(self, t=2.0, r=2.0):
        import Part
        import SheetMetalBaseCmd
        V = FreeCAD.Vector
        sk = self.doc.addObject("Sketcher::SketchObject", "Perfil")
        sk.Placement = FreeCAD.Placement(V(), FreeCAD.Rotation(V(1, 0, 0), 90))
        for a, b in (((0, 60), (0, 0)), ((0, 0), (80, 0)), ((80, 0), (80, 40))):
            sk.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)))
        self.doc.recompute()
        base = self.doc.addObject("Part::FeaturePython", "Chapa")
        SheetMetalBaseCmd.SMBaseBend(base, sk)
        base.Thickness, base.Radius, base.Length = t, r, 120.0
        self.doc.recompute()
        return base

    def test_fator_k_por_material_e_faixa(self):
        import PrumoChapa as C
        self.assertEqual(C.k_fator("Aço carbono", 1.0, 2.0), 0.40)    # r/t = 0,5
        self.assertEqual(C.k_fator("Aço carbono", 4.0, 2.0), 0.44)    # r/t = 2
        self.assertEqual(C.k_fator("Aço carbono", 10.0, 2.0), 0.50)   # r/t = 5
        self.assertEqual(C.k_fator("Alumínio", 1.0, 2.0), 0.33)
        self.assertEqual(C.k_fator("Aço inoxidável", 4.0, 2.0), 0.46)
        self.assertAlmostEqual(C.k_din(2.0, 2.0), 0.325, places=4)    # (0,65 + 0)/2
        self.assertAlmostEqual(C.k_din(20.0, 2.0), 0.5)
        for mat, (tab, fonte) in C.TABELAS_K.items():
            self.assertTrue(fonte)
            self.assertTrue(all(0.0 < v <= 0.5 for v in tab.values()), mat)
        with self.assertRaises(ValueError):
            C.k_fator("Aço carbono", 1.0, 0.0)

    def test_espessuras_e_raio_minimo(self):
        import PrumoChapa as C
        self.assertEqual(C.espessura_comercial("Aço carbono", 3.1), (3.00, "#11"))
        self.assertEqual(C.espessura_comercial("Aço carbono", 6.0), (6.30, '1/4"'))
        self.assertEqual(C.espessura_comercial("Aço inoxidável", 1.5)[1], "USG 16")
        self.assertAlmostEqual(C.raio_minimo("Aço inoxidável", 2.0), 3.0)
        self.assertEqual(C.familia_do_material("AISI 304 (A240)"), "Aço inoxidável")
        self.assertEqual(C.familia_do_material("Alumínio 5052-H32"), "Alumínio")
        self.assertEqual(C.familia_do_material("ASTM A36"), "Aço carbono")

    def test_tabela_no_formato_do_sheetmetal(self):
        import PrumoChapa as C
        import SheetMetalKfactor
        sh = C.criar_tabela_k(self.doc, "Aço inoxidável")
        t = SheetMetalKfactor.KFactorLookupTable(sh.Label)
        self.assertEqual(t.k_factor_standard, "ansi")
        self.assertEqual(t.k_factor_lookup, C.TABELAS_K["Aço inoxidável"][0])
        self.assertIn(sh, SheetMetalKfactor.getSpreadSheetNames())
        rotulo = sh.Label
        C.criar_tabela_k(self.doc, "Aço inoxidável")      # recriar não duplica
        self.assertEqual(len(self.doc.getObjectsByLabel(rotulo)), 1)

    def test_planificar_e_dxf(self):
        import PrumoChapa as C
        base = self._chapa()
        arq, plana, info = C.exportar_dxf(base, os.path.join(self.pasta, "chapa.dxf"), "Aço carbono")
        self.assertTrue(os.path.isfile(arq))
        txt = open(arq, encoding="ascii").read()
        for marca in ("SECTION", "ENTITIES", "CONTORNO", "DOBRAS", "EOF", "AC1009"):
            self.assertIn(marca, txt)
        self.assertEqual(info["dobras"], 2)
        self.assertAlmostEqual(info["altura"], 120.0, places=3)
        self.assertAlmostEqual(plana.BoundBox.ZLength, 0.0, places=6)
        self.assertEqual(info["k"], 0.40)
        # com K menor (alumínio) a planificação encurta 2 dobras × π/2 × ΔK × t
        _a, plana_al, _i = C.exportar_dxf(base, os.path.join(self.pasta, "al.dxf"), "Alumínio")
        esperado = 2 * (math.pi / 2) * (0.40 - 0.33) * 2.0
        self.assertAlmostEqual(plana.BoundBox.XLength - plana_al.BoundBox.XLength, esperado, places=2)

    def test_dxf_tem_arcos_e_circulos(self):
        import Part
        import PrumoChapa as C
        f = Part.makePlane(100, 50)
        furo = Part.Face(Part.Wire(Part.makeCircle(5, FreeCAD.Vector(30, 25, 0))))
        placa = f.cut(furo)
        arco = Part.ArcOfCircle(Part.Circle(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), 10), 0, math.pi / 2)
        arq = C.escrever_dxf(os.path.join(self.pasta, "x.dxf"), placa.Edges + [arco.toShape()])
        txt = open(arq, encoding="ascii").read()
        self.assertIn("CIRCLE", txt)
        self.assertIn("ARC", txt)
        self.assertGreaterEqual(txt.count("\nLINE"), 4)

    def test_planificacao_mantem_furos_redondos(self):
        """Face inclinada levada ao plano XY: o furo continua círculo (não vira BSpline/retas)."""
        import Part
        import PrumoChapa as C
        sh = Part.makeBox(100, 50, 3).cut(Part.makeCylinder(5, 3, FreeCAD.Vector(30, 20, 0)))
        sh.rotate(FreeCAD.Vector(), FreeCAD.Vector(1, 1, 0), 37)
        sh.translate(FreeCAD.Vector(10, 20, 30))
        n = FreeCAD.Rotation(FreeCAD.Vector(1, 1, 0), 37).multVec(FreeCAD.Vector(0, 0, 1))
        face, _l = C._no_plano_xy(sh, None, n)
        tipos = sorted(type(e.Curve).__name__ for e in face.Edges)
        self.assertEqual(tipos, ["Circle", "Line", "Line", "Line", "Line"])
        circ = [e for e in face.Edges if type(e.Curve).__name__ == "Circle"][0]
        self.assertAlmostEqual(circ.Curve.Radius, 5.0, places=6)
        self.assertAlmostEqual(face.BoundBox.ZLength, 0.0, places=6)
        self.assertAlmostEqual(face.BoundBox.XMin, 0.0, places=6)
        self.assertAlmostEqual(face.BoundBox.YMin, 0.0, places=6)

    def test_dxf_da_chapa_furada_tem_circulo(self):
        import Part
        import PrumoChapa as C
        base = self._chapa()
        bb = base.Shape.BoundBox
        cil = self.doc.addObject("Part::Cylinder", "Furo")
        cil.Radius, cil.Height = 4.0, 20.0
        cil.Placement.Base = FreeCAD.Vector(40, bb.Center.y, -10)
        furada = self.doc.addObject("Part::Cut", "ChapaFurada")
        furada.Base, furada.Tool = base, cil
        self.doc.recompute()
        arq, plana, _i = C.exportar_dxf(furada, os.path.join(self.pasta, "furada.dxf"), "Aço carbono")
        txt = open(arq, encoding="ascii").read()
        self.assertIn("\nCIRCLE", txt, "o furo saiu em segmentos de reta")
        self.assertLess(txt.count("\nLINE"), 30)

    def test_raio_minimo_por_liga(self):
        import PrumoChapa as C
        self.assertAlmostEqual(C.raio_minimo("Alumínio", 2.0), 3.0, msg="família sem liga: pior caso")
        self.assertAlmostEqual(C.raio_minimo("Alumínio", 2.0, "Alumínio 5052-H32"), 1.6)
        self.assertAlmostEqual(C.raio_minimo("Alumínio", 2.0, "Alumínio 6061-T6 (B209)"), 3.0)

    def test_painel_planificar(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoChapa as C
        base = self._chapa()
        p = C.PainelChapaDXF()
        p.chapa.aceitar(base)
        self.assertIn("K = 0,4", p.info.text().replace("0,400", "0,4"))
        p.caminho.setText(os.path.join(self.pasta, "painel.dxf"))
        p.tabela.setChecked(True)
        self.assertTrue(p.accept())
        self.assertTrue(os.path.isfile(p.arquivo))
        self.assertTrue(self.doc.getObjectsByLabel("material_A_o_carbono") or
                        [o for o in self.doc.Objects if o.Label.startswith("material_")])
        for n in ("Prumo_ChapaDXF", "Prumo_TabelaK"):
            self.assertIn(n, FreeCADGui.Command.listAll())

    def test_raio_abaixo_do_minimo_avisa(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoChapa as C
        base = self._chapa(t=3.0, r=1.0)
        p = C.PainelChapaDXF()
        p.chapa.aceitar(base)
        self.assertIn("mínimo recomendado", p.info.text())
        p.close()


class T37Variantes(unittest.TestCase):
    """Variantes da peça (P, M, G) ligadas às cotas do modelo."""

    def setUp(self):
        import PrumoVariantes
        self.V = PrumoVariantes
        self.doc = novo_doc("PrumoTesteVariantes")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.caixa = self.doc.addObject("Part::Box", "Caixa")
        self.doc.recompute()

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _tabela(self):
        return self.V.criar(self.doc, [("comprimento", "mm", [100, 200, 300]), ("altura", "mm", [10, 20, 30])],
                            ["P", "M", "G"])

    def test_criar_aplicar_e_seletor(self):
        sh = self._tabela()
        self.assertEqual(self.V.nomes_variantes(sh), ["P", "M", "G"])
        self.assertEqual([n for _r, n, _u in self.V.parametros(sh)], ["comprimento", "altura"])
        self.V.ligar(self.caixa, "Length", "comprimento")
        self.V.ligar(self.caixa, "Height", "altura")
        self.assertAlmostEqual(self.caixa.Length.Value, 100.0)
        self.V.aplicar(self.doc, "G")
        self.assertAlmostEqual(self.caixa.Length.Value, 300.0)
        self.assertAlmostEqual(self.caixa.Height.Value, 30.0)
        self.assertEqual(self.V.ativa(self.doc), "G")
        sel = self.V.seletor(self.doc)
        sel.Variante = "M"
        self.doc.recompute()
        self.assertAlmostEqual(self.caixa.Length.Value, 200.0)
        self.assertEqual(self.V.valor(sh, "altura", "M"), "20 mm")

    def test_nova_variante_e_valores(self):
        sh = self._tabela()
        self.V.ligar(self.caixa, "Length", "comprimento")
        self.V.adicionar_variante(sh, "GG", "G")
        self.assertIn("GG", self.V.seletor(self.doc).getEnumerationsOfProperty("Variante"))
        self.V.definir_valor(sh, "comprimento", "GG", 450)
        self.V.aplicar(self.doc, "GG")
        self.assertAlmostEqual(self.caixa.Length.Value, 450.0)
        self.assertEqual(self.V.valor(sh, "altura", "GG"), "30 mm", "copiou os outros valores da G")
        with self.assertRaises(ValueError):
            self.V.adicionar_variante(sh, "GG")
        with self.assertRaises(ValueError):
            self.V.aplicar(self.doc, "XX")

    def test_nomes_de_parametro_validados(self):
        sh = self._tabela()
        for ruim in ("com espaço", "1abc", "", "altura"):
            with self.assertRaises(ValueError):
                self.V.adicionar_parametro(sh, ruim)

    def test_cota_de_esboco(self):
        import Part
        import Sketcher
        sh = self._tabela()
        sk = self.doc.addObject("Sketcher::SketchObject", "Esboco")
        sk.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(50, 0, 0)))
        sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 50.0))
        sk.renameConstraint(0, "largura")
        self.doc.recompute()
        self.assertIn("Constraints.largura", self.V.propriedades_numericas(sk))
        self.V.ligar(sk, "Constraints.largura", "comprimento")
        self.V.aplicar(self.doc, "M")
        self.assertAlmostEqual(sk.Shape.Edges[0].Length, 200.0, places=4)

    def test_salvar_e_reabrir(self):
        sh = self._tabela()
        self.V.ligar(self.caixa, "Length", "comprimento")
        self.V.aplicar(self.doc, "G")
        caminho = os.path.join(tempfile.mkdtemp(), "variantes.FCStd")
        self.doc.saveAs(caminho)
        nome = self.doc.Name
        fechar(self.doc)
        self.doc = FreeCAD.openDocument(caminho)
        self.assertEqual(self.V.ativa(self.doc), "G")
        self.assertAlmostEqual(self.doc.getObject("Caixa").Length.Value, 300.0)
        self.V.aplicar(self.doc, "P")
        self.assertAlmostEqual(self.doc.getObject("Caixa").Length.Value, 100.0)

    def test_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        sh = self._tabela()
        p = self.V.PainelVariantes(self.doc)
        self.assertEqual(p.tabela.rowCount(), 2)
        self.assertEqual(p.tabela.columnCount(), 4)
        p.tabela.item(0, 3).setText("350")          # comprimento na G
        p.novo_par.setText("largura")
        p._add_parametro()
        self.assertEqual(p.tabela.rowCount(), 3)
        p.nova_var.setText("XG")
        p._add_variante()
        self.assertIn("XG", self.V.nomes_variantes(sh))
        p.objeto.aceitar(self.caixa)
        p.prop.setCurrentText("Length")
        p.par.setCurrentText("comprimento")
        p._ligar()
        self.assertEqual(p.form.mensagem.tipo, "ok")
        p.ativa.setCurrentText("G")
        self.assertTrue(p.accept())
        self.assertAlmostEqual(self.caixa.Length.Value, 350.0)
        self.assertIn("Prumo_Variantes", FreeCADGui.Command.listAll())


class T37bVariantesPainel(unittest.TestCase):
    """Painel de variantes: Cancelar desfaz tudo e fórmulas não viram texto."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoVariantes
        self.V = PrumoVariantes
        self.doc = novo_doc("PrumoTesteVarPainel")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.caixa = self.doc.addObject("Part::Box", "Caixa")
        self.doc.recompute()

    def tearDown(self):
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def test_cancelar_desfaz_tudo(self):
        self.doc.UndoMode = 1
        p = self.V.PainelVariantes(self.doc)
        self.assertIsNotNone(self.V.planilha(self.doc))
        p.novo_par.setText("comprimento")
        p._add_parametro()
        p.objeto.aceitar(self.caixa)
        p.prop.setCurrentText("Length")
        p.par.setCurrentText("comprimento")
        p._ligar()
        self.assertTrue(p.reject())
        self.assertIsNone(self.V.planilha(self.doc), "a tabela ficou depois do Cancelar")
        self.assertIsNone(self.V.seletor(self.doc))
        self.assertFalse(self.caixa.ExpressionEngine, "a cota ficou ligada depois do Cancelar")

    def test_ok_vira_um_passo_no_desfazer(self):
        self.doc.UndoMode = 1
        p = self.V.PainelVariantes(self.doc)
        p.novo_par.setText("comprimento")
        p._add_parametro()
        self.assertTrue(p.accept())
        self.assertIsNotNone(self.V.planilha(self.doc))
        self.doc.undo()
        self.assertIsNone(self.V.planilha(self.doc))

    def test_formula_nao_vira_texto(self):
        sh = self.V.criar(self.doc, [("altura", "mm", [10, 20]), ("meia", "mm", [5, 10])], ["P", "G"])
        self.V.definir_valor(sh, "meia", "G", "=altura*2")
        self.doc.recompute()
        p = self.V.PainelVariantes(self.doc)
        try:
            p.gravar_tabela()
            self.assertTrue(sh.getContents(self.V._col(self.V.COL_VAR0 + 1) + "3").startswith("="),
                            "fórmula sem mexer virou texto")
            i = [n for _r, n, _u in self.V.parametros(sh)].index("meia")
            p.tabela.item(i, 2).setText("altura*3")
            p.gravar_tabela()
            self.assertEqual(sh.getContents(self.V._col(self.V.COL_VAR0 + 1) + "3").replace(" ", ""), "=altura*3")
            p.ativa.setCurrentText("G")
            self.doc.recompute()
            self.assertAlmostEqual(float(sh.get("B3").Value if hasattr(sh.get("B3"), "Value") else sh.get("B3")),
                                   60.0)
        finally:
            p.close()

    def test_desfazer_nao_reaplica_variante(self):
        sh = self.V.criar(self.doc, [("comprimento", "mm", [100, 300])], ["P", "G"])
        self.V.ligar(self.caixa, "Length", "comprimento")
        self.V.aplicar(self.doc, "P")
        self.doc.UndoMode = 1
        self.doc.openTransaction("troca")
        self.V.seletor(self.doc).Variante = "G"
        self.doc.commitTransaction()
        self.doc.recompute()
        self.assertAlmostEqual(self.caixa.Length.Value, 300.0)
        self.doc.undo()
        self.doc.recompute()
        self.assertEqual(self.V.seletor(self.doc).Variante, "P")
        self.assertAlmostEqual(self.caixa.Length.Value, 100.0)
        self.assertEqual(self.V.ativa(self.doc), "P")


class T38CopiarProjeto(unittest.TestCase):
    """Copiar projeto: montagem e peças para outra pasta, renomeando e mantendo os vínculos."""

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.orig = os.path.join(self.base, "orig")
        os.makedirs(self.orig)
        self.peca = novo_doc("PrumoTestePacPeca")
        self.bloco = self.peca.addObject("Part::Box", "Bloco")
        self.peca.recompute()
        self.peca.saveAs(os.path.join(self.orig, "Peca.FCStd"))
        self.mont = novo_doc("PrumoTestePacMont")
        self.mont.saveAs(os.path.join(self.orig, "Montagem.FCStd"))
        self.link = self.mont.addObject("App::Link", "Link")
        self.link.LinkedObject = self.bloco
        self.mont.recompute()
        self.mont.save()
        if FreeCAD.GuiUp:
            for d in (self.peca, self.mont):
                FreeCADGui.getDocument(d.Name).Modified = False

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        for n in list(FreeCAD.listDocuments()):
            if FreeCAD.getDocument(n).FileName.startswith(self.base):
                FreeCAD.closeDocument(n)

    def _doc_por_arquivo(self, caminho):
        for d in FreeCAD.listDocuments().values():
            if os.path.normcase(d.FileName) == os.path.normcase(caminho):
                return d
        return FreeCAD.openDocument(caminho)

    def test_plano_na_ordem_das_pecas_para_a_montagem(self):
        import PrumoCopiarProjeto as C
        passos = C.plano(self.mont, os.path.join(self.base, "novo"), prefixo="NOVO_")
        self.assertEqual([os.path.basename(n) for _d, _o, n in passos], ["NOVO_Peca.FCStd", "NOVO_Montagem.FCStd"])
        self.assertEqual(C.nome_novo("/x/Suporte-v1.FCStd", "A_", "_B", ("v1", "v2")), "A_Suporte-v2_B.FCStd")
        with self.assertRaises(ValueError):
            C.plano(self.mont, self.orig)        # cairia em cima dos originais

    def test_copia_com_vinculos_acertados(self):
        import PrumoCopiarProjeto as C
        destino = os.path.join(self.base, "novo")
        mapa = C.copiar_projeto(self.mont, destino, prefixo="NOVO_", abrir_copia=True)
        self.assertEqual(len(mapa), 2)
        for novo in mapa.values():
            self.assertTrue(os.path.isfile(novo))
        copia = self._doc_por_arquivo(os.path.join(destino, "NOVO_Montagem.FCStd"))
        alvo = copia.getObject("Link").LinkedObject
        self.assertIsNotNone(alvo)
        self.assertEqual(os.path.normcase(alvo.Document.FileName),
                         os.path.normcase(os.path.join(destino, "NOVO_Peca.FCStd")))
        # o original continua apontando para a peça original
        for n in list(FreeCAD.listDocuments()):
            FreeCAD.closeDocument(n)
        orig = FreeCAD.openDocument(os.path.join(self.orig, "Montagem.FCStd"))
        self.assertEqual(os.path.normcase(orig.getObject("Link").LinkedObject.Document.FileName),
                         os.path.normcase(os.path.join(self.orig, "Peca.FCStd")))

    def test_nomes_um_a_um_e_conflitos(self):
        import PrumoCopiarProjeto as C
        destino = os.path.join(self.base, "um_a_um")
        nomes = {self.peca.FileName: "SW-100 Chapa.FCStd", self.mont.FileName: "SW-000 Conjunto.FCStd"}
        mapa = C.copiar_projeto(self.mont, destino, nomes=nomes)
        self.assertTrue(os.path.isfile(os.path.join(destino, "SW-100 Chapa.FCStd")))
        # de novo na mesma pasta: recusa sem sobrescrever
        mont = self._doc_por_arquivo(os.path.join(self.orig, "Montagem.FCStd"))
        with self.assertRaises(ValueError):
            C.copiar_projeto(mont, destino, nomes=nomes)
        self.assertIn(os.path.join(self.orig, "Peca.FCStd"), mapa)

    def test_nome_invalido_recusado_antes_de_comecar(self):
        import PrumoCopiarProjeto as C
        destino = os.path.join(self.base, "invalido")
        nomes = {self.peca.FileName: "Peca:1.FCStd"}
        with self.assertRaises(ValueError):
            C.copiar_projeto(self.mont, destino, nomes=nomes)
        self.assertEqual(os.listdir(destino), [], "nada foi gravado")
        self.assertEqual(os.path.normcase(self.peca.FileName), os.path.normcase(os.path.join(self.orig, "Peca.FCStd")))

    def test_falha_no_meio_desfaz(self):
        """A 2ª gravação falha: os originais voltam abertos, apontando para os originais."""
        import PrumoCopiarProjeto as C
        destino = os.path.join(self.base, "falha")
        original = C._salvar_como

        def falha_na_montagem(d, caminho):
            if "Montagem" in caminho:
                raise IOError("disco cheio (simulado)")
            original(d, caminho)
        C._salvar_como = falha_na_montagem
        try:
            with self.assertRaises(ValueError) as cm:
                C.copiar_projeto(self.mont, destino, prefixo="NOVO_")
        finally:
            C._salvar_como = original
        self.assertIn("desfeita", str(cm.exception))
        self.assertFalse(os.path.isfile(os.path.join(destino, "NOVO_Peca.FCStd")), "cópia parcial ficou")
        abertos = {os.path.normcase(d.FileName) for d in FreeCAD.listDocuments().values()}
        self.assertNotIn(os.path.normcase(os.path.join(destino, "NOVO_Peca.FCStd")), abertos)
        mont = self._doc_por_arquivo(os.path.join(self.orig, "Montagem.FCStd"))
        self.assertEqual(os.path.normcase(mont.getObject("Link").LinkedObject.Document.FileName),
                         os.path.normcase(os.path.join(self.orig, "Peca.FCStd")))

    def test_outro_documento_aberto_que_usa_a_peca(self):
        import PrumoCopiarProjeto as C
        outra = novo_doc("PrumoTestePacOutra")
        outra.saveAs(os.path.join(self.orig, "Outra.FCStd"))
        lk = outra.addObject("App::Link", "Link")
        lk.LinkedObject = self.bloco
        outra.recompute()
        outra.save()
        if FreeCAD.GuiUp:
            FreeCADGui.getDocument(outra.Name).Modified = False
        with self.assertRaises(ValueError) as cm:
            C.copiar_projeto(self.mont, os.path.join(self.base, "outra"), prefixo="N_")
        self.assertIn("Outra", str(cm.exception))
        self.assertEqual(os.path.normcase(self.peca.FileName), os.path.normcase(os.path.join(self.orig, "Peca.FCStd")))

    def test_documento_nao_salvo(self):
        import PrumoCopiarProjeto as C
        d = novo_doc("PrumoTesteSemArquivo")
        try:
            with self.assertRaises(ValueError):
                C.plano(d, self.base)
        finally:
            fechar(d)

    def test_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoCopiarProjeto as C
        p = C.PainelCopiarProjeto(self.mont)
        self.assertEqual(p.tabela.rowCount(), 2)
        p.prefixo.setText("X_")
        self.assertEqual(p.tabela.item(1, 1).text(), "X_Montagem.FCStd")
        p.pasta.setText(os.path.join(self.base, "painel"))
        self.assertTrue(p.accept())
        self.assertTrue(os.path.isfile(os.path.join(self.base, "painel", "X_Peca.FCStd")))
        self.assertIn("Prumo_CopiarProjeto", FreeCADGui.Command.listAll())


class T39Montagem(unittest.TestCase):
    """Montagem: restrições com nomes familiares e verificação de interferência."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteInterf")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _caixa(self, nome, x, lado=10.0):
        b = self.doc.addObject("Part::Box", nome)
        b.Length = b.Width = b.Height = lado
        b.Placement.Base = FreeCAD.Vector(x, 0, 0)
        return b

    def test_interferencia_e_contato(self):
        import PrumoInterferencia as I
        a = self._caixa("A", 0)
        b = self._caixa("B", 7)      # invade 3 mm: 3×10×10 = 300 mm³
        c = self._caixa("C", 17)     # encosta na B (x = 17)
        d = self._caixa("D", 100)    # longe
        self.doc.recompute()
        res = I.verificar([a, b, c, d])
        self.assertEqual(len(res), 1)
        self.assertEqual({res[0].a.Name, res[0].b.Name}, {"A", "B"})
        self.assertAlmostEqual(res[0].volume, 300.0, places=3)
        com = I.verificar([a, b, c, d], contatos=True)
        self.assertEqual(len(com), 2)
        self.assertEqual(com[1].volume, 0.0)
        g = I.mostrar(self.doc, res)
        self.assertEqual(len(g.Group), 1)
        self.assertAlmostEqual(g.Group[0].Shape.Volume, 300.0, places=3)
        I.mostrar(self.doc, res)       # repetir substitui o grupo
        self.assertEqual(len([o for o in self.doc.Objects if o.TypeId == "App::DocumentObjectGroup"]), 1)

    def test_interferencia_dentro_de_parte_com_posicao(self):
        import PrumoInterferencia as I
        parte = self.doc.addObject("App::Part", "Conjunto")
        a = self._caixa("A", 0)
        b = self._caixa("B", 20)
        parte.addObject(a)
        parte.addObject(b)
        self.doc.recompute()
        self.assertEqual(I.verificar([parte]), [])
        b.Placement.Base = FreeCAD.Vector(5, 0, 0)
        self.doc.recompute()
        self.assertEqual(len(I.verificar([parte])), 1)

    def test_nomes_familiares_na_faixa(self):
        import PrumoRibbon
        mont = [t for t in PrumoRibbon.TABS if t["id"] == "montagem"][0]
        rotulos = {c: r for _p, itens in mont["panels"] for c, _s, r in itens}
        self.assertIn("Coincidente", rotulos["Assembly_CreateJointDistance"])
        self.assertEqual(rotulos["Assembly_CreateJointCylindrical"], "Concêntrica")
        self.assertIn("Prumo_Interferencia", rotulos)

    def test_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoInterferencia as I
        self._caixa("A", 0)
        self._caixa("B", 5)
        self.doc.recompute()
        p = I.PainelInterferencia()
        res = p.verificar()          # sem seleção: documento inteiro
        self.assertEqual(len(res), 1)
        self.assertEqual(p.lista.count(), 1)
        self.assertEqual(p.form.mensagem.tipo, "erro")
        p.lista.setCurrentRow(0)
        self.assertEqual(len(FreeCADGui.Selection.getSelection()), 2)
        self.assertTrue(p.accept())
        self.assertIn("Prumo_Interferencia", FreeCADGui.Command.listAll())

    def test_clicar_no_resultado_nao_muda_o_que_e_verificado(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoInterferencia as I
        self._caixa("A", 0)
        self._caixa("B", 5)
        self._caixa("C", 12)     # invade a B
        self.doc.recompute()
        FreeCADGui.Selection.clearSelection()
        p = I.PainelInterferencia().mostrar()
        try:
            self.assertEqual(len(p.verificar()), 2)
            p.lista.setCurrentRow(0)
            FreeCADGui.updateGui()
            self.assertEqual(p.pecas.valores(), [], "o par clicado foi parar na caixa de peças")
            self.assertEqual(len(p.verificar()), 2, "a segunda verificação só olhou o par clicado")
            vermelho = self.doc.getObject(I.NOME_GRUPO).Group[0]
            self.assertEqual(I._filtro(vermelho, ()), [], "o sólido de resultado entrou como peça")
        finally:
            FreeCADGui.Control.closeDialog()


class T40ModelosComRegras(unittest.TestCase):
    """Modelos com regras: formulário gera a peça; regras de projeto avisam."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteModelos")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def test_placa_volume_e_regras(self):
        import PrumoModelos as M
        o = M.criar(self.doc, "placa", Comprimento=300, Largura=200, Espessura=10, RaioCanto=0, FurosX=2,
                    FurosY=2, DiametroFuro=20, Borda=40)
        self.assertTrue(o.Shape.isValid())
        esperado = 300 * 200 * 10 - 4 * math.pi * 10 ** 2 * 10
        self.assertAlmostEqual(o.Shape.Volume, esperado, delta=1.0)
        self.assertEqual(list(o.Avisos), [])
        o.Borda = 20                     # < 1,5 × 20
        self.doc.recompute()
        self.assertTrue(any("borda" in a for a in o.Avisos))
        o.RaioCanto = 15
        self.doc.recompute()
        self.assertLess(o.Shape.Volume, esperado)

    def test_flange(self):
        import PrumoModelos as M
        o = M.criar(self.doc, "flange")
        self.assertTrue(o.Shape.isValid())
        p = o.Proxy.parametros(o)
        anel = math.pi / 4 * (p["DiametroExterno"] ** 2 - p["DiametroInterno"] ** 2) * p["Espessura"]
        furos = p["Furos"] * math.pi / 4 * p["DiametroFuro"] ** 2 * p["Espessura"]
        self.assertAlmostEqual(o.Shape.Volume, anel - furos, delta=1.0)
        o.DiametroFuracao = 190          # furos encostam na borda externa
        self.doc.recompute()
        self.assertTrue(o.Avisos)

    def test_suporte_em_l(self):
        import PrumoModelos as M
        o = M.criar(self.doc, "suporte", Aba1=80, Aba2=60, Largura=50, Espessura=3, RaioDobra=3, DiametroFuro=0)
        self.assertTrue(o.Shape.isValid())
        self.assertEqual(len(o.Shape.Solids), 1)
        bb = o.Shape.BoundBox
        self.assertAlmostEqual(bb.XLength, 80, places=6)
        self.assertAlmostEqual(bb.ZLength, 60, places=6)
        # volume = abas retas + quarto de anel
        t, r = 3.0, 3.0
        esperado = 50 * t * ((80 - r - t) + (60 - r - t)) + 50 * math.pi / 4 * ((r + t) ** 2 - r ** 2)
        self.assertAlmostEqual(o.Shape.Volume, esperado, delta=0.5)
        o.RaioDobra = 1
        self.doc.recompute()
        self.assertTrue(any("Raio" in a for a in o.Avisos))

    def test_suporte_com_aba_curta_e_recusado(self):
        """Aba ≤ espessura + raio: erro claro em vez de erro do OCC no recálculo."""
        import PrumoModelos as M
        p = {"Aba1": 5.0, "Aba2": 60.0, "Largura": 50.0, "Espessura": 3.0, "RaioDobra": 3.0, "DiametroFuro": 0.0}
        self.assertIn("aba horizontal", M.impossivel("suporte", p))
        self.assertIsNone(M.impossivel("suporte", dict(p, Aba1=10.0)))
        self.assertTrue(M.impossivel("flange", {"DiametroInterno": 100.0, "DiametroExterno": 90.0}))
        o = M.criar(self.doc, "suporte", Aba1=80, Aba2=60, Largura=50, Espessura=3, RaioDobra=3, DiametroFuro=0)
        vol = o.Shape.Volume
        o.Aba1 = 5
        self.doc.recompute()
        self.assertIn("Invalid", o.State)
        self.assertAlmostEqual(o.Shape.Volume, vol, places=6, msg="a forma anterior foi trocada por lixo")
        if FreeCAD.GuiUp:
            pn = M.PainelModelo()
            try:
                pn.tipo.setCurrentIndex(pn.tipo.findData("suporte"))
                pn.campos["Aba1"].setValue(5)
                pn.campos["Espessura"].setValue(3)
                pn.campos["RaioDobra"].setValue(3)
                self.assertIn("aba horizontal", pn.pendencia())
                self.assertFalse(pn.accept())
            finally:
                pn.close()

    def test_eixo_escalonado(self):
        import PrumoModelos as M
        self.assertEqual(M.trechos("30x40; 40×120;30x40"), [(30, 40), (40, 120), (30, 40)])
        for ruim in ("", "30", "0x10", "abc"):
            with self.assertRaises(ValueError):
                M.trechos(ruim)
        o = M.criar(self.doc, "eixo", Trechos="30x40; 40x120; 30x40", Chanfro=0)
        self.assertAlmostEqual(o.Shape.BoundBox.ZLength, 200, places=6)
        esperado = math.pi / 4 * (30 ** 2 * 80 + 40 ** 2 * 120)
        self.assertAlmostEqual(o.Shape.Volume, esperado, delta=1.0)
        o.Trechos = "20x40; 60x10"
        self.doc.recompute()
        self.assertTrue(any("Degrau" in a for a in o.Avisos))

    def test_salvar_reabrir_e_editar(self):
        import PrumoModelos as M
        o = M.criar(self.doc, "placa")
        caminho = os.path.join(tempfile.mkdtemp(), "modelo.FCStd")
        self.doc.saveAs(caminho)
        fechar(self.doc)
        self.doc = FreeCAD.openDocument(caminho)
        o = self.doc.getObject("Modelo")
        o.Comprimento = 500
        self.doc.recompute()
        self.assertAlmostEqual(o.Shape.BoundBox.XLength, 500, places=6)

    def test_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoModelos as M
        p = M.PainelModelo()
        p.tipo.setCurrentIndex(p.tipo.findData("flange"))
        self.assertIn("DiametroFuracao", p.campos)
        p.campos["Furos"].setValue(4)
        self.assertTrue(p.accept())
        o = p.obj
        self.assertEqual(o.TipoModelo, "flange")
        self.assertEqual(o.Furos, 4)
        # editar o existente
        p2 = M.PainelModelo(o)
        self.assertFalse(p2.tipo.isEnabled())
        p2.campos["Espessura"].setValue(25)
        self.assertTrue(p2.accept())
        self.assertAlmostEqual(o.Shape.BoundBox.ZLength, 25, places=6)
        p3 = M.PainelModelo()
        p3.tipo.setCurrentIndex(p3.tipo.findData("eixo"))
        p3.campos["Trechos"].setText("errado")
        self.assertTrue(p3.pendencia())
        p3.close()
        self.assertIn("Prumo_Modelo", FreeCADGui.Command.listAll())


class T41GuiaMigracao(unittest.TestCase):
    """Guia "vindo do SolidWorks / ZW3D"."""

    def test_comandos_do_guia_existem(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGuiaMigracao as G
        import PrumoRibbon
        todos = set(FreeCADGui.Command.listAll())
        abas = {t["id"] for t in PrumoRibbon.TABS}
        faltando = []
        for area, sw, outros, prumo, aba, cmds, obs in G.EQUIVALENCIAS:
            self.assertIn(aba, abas, prumo)
            self.assertTrue(sw and outros and prumo, prumo)
            if not any(c in todos for c in cmds):
                faltando.append((prumo, cmds))
        # comandos de bancadas ainda não carregadas (ex.: SheetMetal, Assembly) entram ao abrir a bancada
        prumo_faltando = [f for f in faltando if any(c.startswith("Prumo_") for c in f[1])]
        self.assertEqual(prumo_faltando, [])

    def test_busca(self):
        import PrumoGuiaMigracao as G
        self.assertEqual([e[3] for e in G.filtrar("filete")], ["Arredondar"])
        self.assertTrue(any(e[3] == "Reforço" for e in G.filtrar("gusset")))
        self.assertTrue(any(e[3] == "Copiar projeto" for e in G.filtrar("pack and go")))
        self.assertEqual(len(G.filtrar("")), len(G.EQUIVALENCIAS))
        self.assertEqual(G.filtrar("xyzxyz"), [])

    def test_janela_e_mostrar_onde(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGuiaMigracao as G
        import PrumoRibbon
        w = G.GuiaMigracao()
        self.assertEqual(w.tabela.rowCount(), len(G.EQUIVALENCIAS))
        w.busca.setText("cantoneira")
        self.assertEqual(w.tabela.rowCount(), 1)
        self.assertEqual(w.tabela.item(0, 3).text(), "Reforço")
        if PrumoRibbon._state.get("ribbon") is not None:
            self.assertTrue(w.mostrar_onde())
        w.deleteLater()
        d = G.mostrar()
        self.assertTrue(d.isVisible())
        d.close()
        self.assertIn("Prumo_GuiaMigracao", FreeCADGui.Command.listAll())



class T42SimulacaoEstrutura(unittest.TestCase):
    """Simulação por barras: seções, pórtico (casos analíticos), NBR 8800, combinações e interface."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteAnalise")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp:
            FreeCADGui.Selection.clearSelection()
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    # ---- seções
    def test_secao_w_bate_com_o_catalogo(self):
        """W 150 x 13,0: valores da tabela Gerdau (A 16,6 cm², Ix 635, Wx 85,8, Zx 96,4, Iy 82, Cw 4181)."""
        import PrumoSecao as S
        p = S.propriedades("W 150 x 13,0")
        for k, ref, esc in (("A", 16.6, 1e2), ("Ix", 635.0, 1e4), ("Wx", 85.8, 1e3), ("Zx", 96.4, 1e3),
                            ("Iy", 82.0, 1e4), ("Cw", 4181.0, 1e6)):
            self.assertAlmostEqual(p[k] / esc, ref, delta=0.02 * ref, msg=k)
        self.assertLess(p["J"] / 1e4, 1.72, "J sem os raios fica abaixo do catálogo (a favor da segurança)")
        self.assertFalse(p["aproximada"])

    def test_secoes_de_todas_as_familias(self):
        import math
        import PrumoPerfis
        import PrumoSecao as S
        for f in PrumoPerfis.familias():
            for it in (f["itens"][0], f["itens"][-1]):
                p = S.propriedades(it["nome"])
                for k in ("A", "Ix", "Iy", "Wx", "Wy", "Zx", "Zy", "J", "rx", "ry", "rmin"):
                    self.assertGreater(p[k], 0, (it["nome"], k))
                self.assertGreaterEqual(p["Zx"], p["Wx"] * 0.999, it["nome"])
                self.assertLessEqual(p["I2"], min(p["Ix"], p["Iy"]) + 1e-6, it["nome"])
                # massa do catálogo × área calculada: densidade próxima à do aço (raios faltando: até 12 %)
                dens = it["massa"] / (p["A"] * 1e-6)
                self.assertAlmostEqual(dens, 7850, delta=0.12 * 7850, msg=it["nome"])
        tubo = S.propriedades(PrumoPerfis.familia("TUBO")["itens"][0]["nome"])
        D, t = tubo["D"], tubo["t"]
        self.assertAlmostEqual(tubo["Ix"], math.pi * (D ** 4 - (D - 2 * t) ** 4) / 64, places=3)

    # ---- pórtico
    def _viga(self, L=6000.0, apoio_j=(0, 1, 1, 0, 0, 0)):
        import PrumoPortico as PT
        s = PT.Secao(A=4970, Iy=8578e4, Iz=727e4, J=11.9e4, massa_kgm=38.7)
        m = PT.Modelo()
        a, b = m.no((0, 0, 0)), m.no((L, 0, 0))
        m.barras.append(PT.Barra(a, b, s, (0, 0, 1)))
        m.apoios[a] = [1, 1, 1, 1, 0, 0]
        m.apoios[b] = list(apoio_j)
        return PT, m, s, a, b

    def test_viga_biapoiada_e_balanco(self):
        PT, m, s, a, b = self._viga()
        c = PT.Caso("q")
        c.distribuidas.append((0, [0, 0, -10], True))
        r = m.resolver(c)
        self.assertAlmostEqual(r.esforcos(0, 3000)["My"] / 1e6, 45.0, places=6)       # qL²/8
        self.assertAlmostEqual(r.flecha_local(0)[1], 5 * 10 * 6000 ** 4 / (384 * 200000 * 8578e4), places=6)
        self.assertAlmostEqual(r.reacao(a)[0][2], 30.0, places=6)
        m2 = PT.Modelo()
        a, b = m2.no((0, 0, 0)), m2.no((0, 3000, 0))
        m2.barras.append(PT.Barra(a, b, s, (0, 0, 1)))
        m2.apoios[a] = [1] * 6
        c = PT.Caso("P")
        c.nos.append((b, [0, 0, -10], [0, 0, 0]))
        r = m2.resolver(c)
        self.assertAlmostEqual(r.esforcos(0, 0)["My"] / 1e6, -30.0, places=6)          # momento negativo
        self.assertAlmostEqual(r.deslocamento(b)[2], -10e3 * 3000 ** 3 / (3 * 200000 * 8578e4), places=6)

    def test_carga_concentrada_peso_proprio_e_equilibrio(self):
        PT, m, s, a, b = self._viga(4000.0)
        c = PT.Caso("P")
        c.pontuais.append((0, 1000, [0, -5, 0], True))
        r = m.resolver(c)
        self.assertAlmostEqual(r.esforcos(0, 1000)["Mz"] / 1e6, 5 * 1 * 3 / 4, places=6)   # Pab/L
        PT, m, s, a, b = self._viga()
        r = m.resolver(PT.Caso("pp", peso_proprio=True))
        self.assertAlmostEqual(r.reacao(a)[0][2] + r.reacao(b)[0][2], 38.7 * 6 * 9.80665 / 1000, places=6)
        # pórtico: soma das reações = cargas aplicadas
        m = PT.Modelo()
        n = [m.no(p) for p in ((0, 0, 0), (0, 0, 3000), (5000, 0, 3000), (5000, 0, 0))]
        for i, j, z in ((0, 1, (0, 1, 0)), (1, 2, (0, 0, 1)), (2, 3, (0, 1, 0))):
            m.barras.append(PT.Barra(n[i], n[j], s, z))
        m.apoios[n[0]] = m.apoios[n[3]] = [1] * 6
        c = PT.Caso("H")
        c.nos.append((n[1], [10, 0, 0], [0, 0, 0]))
        c.distribuidas.append((1, [0, 0, -5], True))
        r = m.resolver(c)
        soma = r.reacao(n[0])[0] + r.reacao(n[3])[0]
        for x, y in zip(soma, (-10, 0, 25)):
            self.assertAlmostEqual(x, y, places=6)

    def test_balanco_em_l_espacial_com_torcao(self):
        """Balanço em L no plano XY com força vertical na ponta: flexão das duas barras + torção da
        primeira (δ = Pa³/3EI + Pb³/3EI + Pab²/GJ)."""
        import PrumoPortico as PT
        s = PT.Secao(A=4970, Iy=8578e4, Iz=727e4, J=11.9e4)
        m = PT.Modelo()
        a_, b_ = 2000.0, 1500.0
        n0, n1, n2 = m.no((0, 0, 0)), m.no((a_, 0, 0)), m.no((a_, b_, 0))
        m.barras.append(PT.Barra(n0, n1, s, (0, 0, 1)))
        m.barras.append(PT.Barra(n1, n2, s, (0, 0, 1)))
        m.apoios[n0] = [1] * 6
        c = PT.Caso("P")
        c.nos.append((n2, [0, 0, -10], [0, 0, 0]))
        r = m.resolver(c)
        P, E, G, I, J = 10e3, 200000.0, 77000.0, 8578e4, 11.9e4
        esperado = P * a_ ** 3 / (3 * E * I) + P * b_ ** 3 / (3 * E * I) + P * a_ * b_ ** 2 / (G * J)
        self.assertAlmostEqual(-r.deslocamento(n2)[2], esperado, delta=1e-6 * esperado)
        self.assertAlmostEqual(abs(r.esforcos(0, 0)["T"]) / 1e6, P * b_ / 1e6, places=6)

    def test_sem_apoio_ou_mecanismo(self):
        import PrumoPortico as PT
        PT_, m, s, a, b = self._viga()
        m.apoios = {}
        with self.assertRaises(ValueError):
            m.resolver(PT.Caso("x"))
        m.apoios = {a: [0, 0, 1, 0, 0, 0]}
        with self.assertRaises(ValueError):
            m.resolver(PT.Caso("x"))

    # ---- NBR 8800
    def test_nbr8800_formulas(self):
        import math
        import PrumoNBR8800 as N
        import PrumoSecao as S
        p = S.propriedades("W 200 x 22,5")
        fy, fu, E = 250.0, 400.0, 200000.0
        self.assertAlmostEqual(N.chi(1.5), 0.658 ** 2.25, places=12)
        self.assertAlmostEqual(N.chi(1.5), 0.877 / 2.25, places=3)        # continuidade em λ0 = 1,5
        self.assertAlmostEqual(N.tracao(p, fy, fu)[0], p["A"] * fy / 1.10, places=6)
        Nc, _t = N.compressao(p, fy, 100.0)
        self.assertAlmostEqual(Nc, p["A"] * fy / 1.10, delta=0.01 * Nc)    # barra curta: χ ≈ 1
        # FLT: viga travada (Lb pequeno) → Mpl; em λr → Mr; acima, Mcr contínuo
        M_curta, modo = N.flexao_x(p, fy, 200.0)
        self.assertAlmostEqual(M_curta, p["Zx"] * fy / 1.10, places=3)
        sr = 0.3 * fy
        b1 = (fy - sr) * p["Wx"] / (E * p["J"])
        lr = 1.38 * math.sqrt(p["Iy"] * p["J"]) / (p["ry"] * p["J"] * b1) * math.sqrt(
            1 + math.sqrt(1 + 27 * p["Cw"] * b1 ** 2 / p["Iy"]))
        Lr = lr * p["ry"]
        M_r = N.flexao_x(p, fy, Lr * 0.999)[0]
        M_r2 = N.flexao_x(p, fy, Lr * 1.001)[0]
        self.assertAlmostEqual(M_r, M_r2, delta=0.01 * M_r, msg="FLT descontínua em λr")
        self.assertAlmostEqual(M_r, (fy - sr) * p["Wx"] / 1.10, delta=0.01 * M_r)
        self.assertLessEqual(M_curta, 1.5 * p["Wx"] * fy / 1.10 + 1e-6)
        # cortante: alma compacta → Vpl/γa1
        self.assertAlmostEqual(N.cortante_z(p, fy)[0], 0.6 * p["d"] * p["tw"] * fy / 1.10, places=6)
        # Cb: momento linear de M a 0 → 1,67; uniforme → 1,0
        self.assertAlmostEqual(N.cb(1.0, 0.75, 0.5, 0.25), 12.5 / 7.5, places=6)
        self.assertAlmostEqual(N.cb(1.0, 1.0, 1.0, 1.0), 1.0, places=6)
        # interação
        self.assertAlmostEqual(N.interacao(-50, 100, 30, 100, 0, 100)[0], 0.5 + 8 / 9 * 0.3, places=9)
        self.assertAlmostEqual(N.interacao(-10, 100, 30, 100, 0, 100)[0], 0.05 + 0.3, places=9)
        self.assertIn("2024", N.EDICAO)

    def test_combinacoes_nbr8681(self):
        import PrumoAnaliseEstrutura as A
        casos = [A.caso_padrao(),
                 {"nome": "SC", "tipo": "Sobrecarga (sem predominância de equipamentos)", "cargas": []},
                 {"nome": "V0", "tipo": "Vento", "cargas": []},
                 {"nome": "V90", "tipo": "Vento", "cargas": []}]
        cs = A.combinacoes(casos)
        elu = [c for c in cs if c[1] == "ELU"]
        els = [c for c in cs if c[1] == "ELS"]
        for _n, _t, fat in elu:
            ventos = [k for k, f in fat if k in (2, 3) and f]
            self.assertLessEqual(len(ventos), 1, "dois ventos na mesma combinação")
        d = {tuple(sorted(f)): n for n, _t, f in elu}
        self.assertIn(((0, 1.25), (1, 1.5)), d)                       # só sobrecarga
        self.assertIn(((0, 1.25), (1, 1.5), (2, 1.4 * 0.6)), d)       # vento secundário: γ·ψ0
        self.assertIn(((0, 1.0), (1, 0.75), (2, 1.4)), d)            # vento principal, permanente favorável
        self.assertTrue(all(f == 1.0 for _n, _t, fat in els for k, f in fat if k in (0,)))

    # ---- integração com a estrutura e a interface
    def _portico(self, perfil="W 200 x 22,5"):
        import PrumoEstrutura as E
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (5000, 3000)), ((5000, 3000), (5000, 0))],
                           "XZ")
        return E.criar(self.doc, sk, perfil, material="ASTM A36")

    def _analise(self, est):
        import PrumoAnaliseEstrutura as A
        an = A.criar(self.doc, est)
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        casos = an.Proxy.casos(an)
        casos.append({"nome": "Sobrecarga", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                      "cargas": [{"alvo": "barra", "linha": 1, "tipo": "distribuida", "valor": 10.0,
                                  "direcao": "Para baixo (−Z)"}]})
        an.Casos = [__import__("json").dumps(c, ensure_ascii=False) for c in casos]
        self.doc.recompute()
        return an

    def test_analise_da_estrutura(self):
        import PrumoEstrutura as E
        est = self._portico()
        an = self._analise(est)
        self.assertIn(an.Situacao, ("atende", "não atende"), an.Situacao)
        self.assertGreater(an.TaxaMaxima, 0.1)
        self.assertEqual(an.Proxy.material(an)[1], 250.0)
        calc = an.Proxy.calc
        self.assertEqual(sorted(calc.verificacao), [0, 1, 2])
        # equilíbrio da combinação 1,25 G + 1,5 Q: reações verticais = cargas
        nome = [n for n, t, f in calc.combinacoes if t == "ELU" and len(f) == 2][0]
        r = calc.resultados[nome]
        soma = sum(r.reacao(k)[0][2] for k in r.modelo.apoios)
        import PrumoSecao as S
        peso = S.propriedades("W 200 x 22,5")["massa_kgm"] * 11.0 * 9.80665 / 1000
        self.assertAlmostEqual(soma, 1.25 * peso + 1.5 * 10 * 5, places=3)
        tx = an.TaxaMaxima
        # perfil maior: taxa menor (a análise acompanha a estrutura)
        padrao, extras = E.grupos_para_edicao(est)
        padrao["perfil"] = "W 310 x 38,7"
        E.editar(est, padrao, extras)
        self.doc.recompute()
        self.assertLess(an.TaxaMaxima, tx)
        # sem apoios: erro claro
        an.Apoios = []
        self.doc.recompute()
        self.assertIn("apoio", an.Situacao)

    def test_ligacao_em_t_vira_no(self):
        """Barra que chega no meio de outra: o nó entra no meio dela (a carga passa)."""
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (6000, 3000)), ((6000, 3000), (6000, 0)),
                                      ((3000, 3000), (3000, 0))], "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5")
        m, _l, mapa = A.montar_modelo(est, [A.caso_padrao()], {})
        # 2 trechos (dividida no pilar do meio) × 4 elementos cada
        self.assertEqual(len(mapa["barras"][1]), 8, "a viga devia ser dividida no pilar do meio")
        self.assertIsNotNone(A._no_mais_proximo(m, (3000, 0, 3000), 1.0))
        self.assertEqual(len(m.nos), 6 + 3 * 3 + 6)

    def test_painel_clique_e_cancelar(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoAnaliseEstrutura as A
        import PrumoAnaliseVista as V
        import PrumoEstrutura as E
        self.doc.UndoMode = 1
        est = self._portico()
        bs = E.barras_de(est)
        p = V.abrir_painel(est)
        try:
            an = p.analise
            p.clique(bs[0], "", (5.0, 2.0, 10.0))          # perto da base do pilar 1
            p.tipo_apoio.setCurrentText("Rótula")
            p.clique(bs[2], "", (4990.0, 0.0, 20.0))
            self.assertEqual(sorted(an.Proxy.apoios(an).values()), ["Engaste", "Rótula"])
            p.modo.definir("barra")
            k = p.novo_caso("Sobrecarga")
            # um pilar engastado e outro rotulado, sem travamento fora do plano: o pórtico gira em planta
            # só contra a torção do pilar engastado e a 2ª ordem acusa instabilidade (correto).
            an.SegundaOrdem = False
            p.valor.setValue(8.0)
            p.clique(bs[1], "Face1", (2500.0, 0.0, 3000.0))
            casos = an.Proxy.casos(an)
            self.assertEqual(casos[k]["cargas"][0]["linha"], 1)
            self.assertIn(an.Situacao, ("atende", "não atende"))
            self.assertGreater(p.tabela.rowCount(), 0)
            for modo in A.MOSTRAR:
                an.Mostrar = modo
                self.doc.recompute()
            self.assertGreater(an.ViewObject.Proxy.desenho.getNumChildren(), 0, "nada desenhado na tela")
            self.assertTrue(p.reject())
        finally:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        self.assertIsNone(A.analise_de(est), "Cancelar devia tirar a análise criada")

    def test_salvar_reabrir_relatorio_e_duplo_clique(self):
        import os
        import tempfile
        import PrumoAnaliseEstrutura as A
        est = self._portico()
        an = self._analise(est)
        tx = an.TaxaMaxima
        caminho = os.path.join(tempfile.mkdtemp(), "analise.FCStd")
        self.doc.saveAs(caminho)
        fechar(self.doc)
        self.doc = FreeCAD.openDocument(caminho)
        an = [o for o in self.doc.Objects if "Apoios" in o.PropertiesList][0]
        self.doc.recompute()
        an.touch()
        self.doc.recompute()
        self.assertAlmostEqual(an.TaxaMaxima, tx, places=3)
        self.assertEqual(len(an.Proxy.apoios(an)), 2)
        if FreeCAD.GuiUp:
            import PrumoAnaliseRelatorio as R
            pdf = os.path.join(tempfile.mkdtemp(), "memoria.pdf")
            R.gerar_pdf(an, pdf)
            with open(pdf, "rb") as f:
                self.assertEqual(f.read(4), b"%PDF")
            self.assertGreater(os.path.getsize(pdf), 20000)
            self.assertTrue(an.ViewObject.Proxy.doubleClicked(an.ViewObject))
            import PrumoPainel as P
            self.assertIs(P._ATIVO["painel"].analise, an)
            P._ATIVO["painel"].reject()
            FreeCADGui.Control.closeDialog()
            self.assertIs(A.analise_de(an.Estrutura), an, "Cancelar não pode apagar uma análise que já existia")
        self.assertIn("Prumo_AnaliseEstrutura", FreeCADGui.Command.listAll() if FreeCAD.GuiUp else
                      ["Prumo_AnaliseEstrutura"])

    def test_segunda_ordem_pilar_em_balanco(self):
        """Pilar engastado com P e H no topo: δ = H/P·(tan(kL)/k − L) (solução exata)."""
        import math
        import PrumoPortico as PT
        s = PT.Secao(A=2860, Iy=2029e4, Iz=2029e4, J=5e4)
        m = PT.Modelo()
        L, n = 3000.0, 8
        nos = [m.no((0, 0, L * k / n)) for k in range(n + 1)]
        for a, b in zip(nos[:-1], nos[1:]):
            m.barras.append(PT.Barra(a, b, s, (1, 0, 0)))
        m.apoios[nos[0]] = [1] * 6
        c = PT.Caso("PH")
        c.nos.append((nos[-1], [1.0, 0, -300.0], [0, 0, 0]))
        r1 = m.resolver(c)
        r2 = m.resolver(c, segunda_ordem=True)
        k = math.sqrt(300e3 / (200000 * 2029e4))
        exato = 1e3 / 300e3 * (math.tan(k * L) / k - L)
        self.assertAlmostEqual(r2.deslocamento(nos[-1])[0], exato, delta=exato * 1e-3)
        self.assertGreater(r2.amplificacao, 1.1)
        self.assertLess(r1.deslocamento(nos[-1])[0], exato)
        c.nos[0] = (nos[-1], [1.0, 0, -5000.0], [0, 0, 0])     # acima da crítica (≈ 1100 kN)
        with self.assertRaises(ValueError):
            m.resolver(c, segunda_ordem=True)

    def test_flecha_de_viga_dividida_em_trechos(self):
        """Viga com nós no meio: a flecha é a da viga inteira (corda das pontas), não a de um trecho."""
        import PrumoPortico as PT
        import PrumoAnaliseEstrutura as A
        PT_, m, s, a, b = self._viga()
        m = PT.Modelo()
        nos = [m.no((x, 0, 0)) for x in (0, 2000, 4000, 6000)]
        for i, j in zip(nos[:-1], nos[1:]):
            m.barras.append(PT.Barra(i, j, s, (0, 0, 1)))
        m.apoios[nos[0]] = [1, 1, 1, 1, 0, 0]
        m.apoios[nos[-1]] = [0, 1, 1, 0, 0, 0]
        c = PT.Caso("q")
        for k in range(3):
            c.distribuidas.append((k, [0, 0, -10], True))
        r = m.resolver(c)
        exato = 5 * 10 * 6000 ** 4 / (384 * 200000 * 8578e4)
        self.assertAlmostEqual(A._flecha_do_membro(r, [0, 1, 2], m), exato, delta=exato * 1e-3)

    def test_balanco_e_membro_continuo(self):
        """Balanço: Cb = 1, sem K (NBR 8800:2024: L real), flecha da ponta com limite 2L/250. Duas linhas colineares
        seguidas: um membro só (comprimento de flambagem da viga inteira)."""
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (2000, 0))], "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        casos = [A.caso_padrao(), {"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                                   "cargas": [{"alvo": "barra", "linha": 0, "tipo": "distribuida", "valor": 5.0,
                                               "direcao": "Para baixo (−Z)"}]}]
        calc = A.calcular(est, casos, {A._chave_no((0, 0, 0)): "Engaste"})
        self.assertIsNone(calc.erro, calc.erro)
        self.assertTrue(calc.membros[0][2], "a ponta solta devia marcar balanço")
        self.assertEqual(calc.verificacao[0]["membro"][1], 1.0)
        f, lim, _tx, nome, txt = calc.flechas[0]
        self.assertAlmostEqual(lim, 2 * 2000 / 250.0)
        self.assertEqual(txt, "flecha do balanço")
        r = calc.resultados[nome]
        ponta = A._no_mais_proximo(calc.modelo, (2000, 0, 0), 1.0)
        self.assertAlmostEqual(f, abs(r.deslocamento(ponta)[2]), delta=1e-6 + 1e-3 * f)
        # viga contínua desenhada em dois pedaços
        sk2 = esboco_linhas(self.doc, [((0, 0), (3000, 0)), ((3000, 0), (6000, 0))], "XZ", "Esq2")
        est2 = E.criar(self.doc, sk2, "W 200 x 22,5")
        m, _l, mapa = A.montar_modelo(est2, [A.caso_padrao()],
                                      {A._chave_no((0, 0, 0)): "Engaste", A._chave_no((6000, 0, 0)): "Rolete (vertical)"})
        mb = A.membros(m, mapa)
        self.assertEqual(mb[0][0], [0, 1])
        self.assertAlmostEqual(mb[1][1], 6000.0)
        self.assertFalse(mb[0][2])

    def test_combinacoes_de_succao_e_avisos(self):
        import PrumoAnaliseEstrutura as A
        casos = [A.caso_padrao(),
                 {"nome": "Q", "tipo": "Sobrecarga em cobertura, depósitos e oficinas", "cargas": []},
                 {"nome": "V", "tipo": "Vento", "cargas": []}]
        self.assertEqual(A.TIPOS_CASO[casos[1]["tipo"]][2], 0.8)
        cs = A.combinacoes(casos)
        # vento principal, permanentes favoráveis e sem a sobrecarga (que aliviaria a sucção)
        self.assertTrue(any(t == "ELU" and sorted(f) == [(0, 1.0), (2, 1.4)] for _n, t, f in cs))
        # sobrecarga principal com o vento secundário (ψ0 = 0,6)
        self.assertTrue(any(t == "ELU" and sorted(f) == [(0, 1.25), (1, 1.5), (2, 1.4 * 0.6)]
                            for _n, t, f in cs))
        self.assertTrue(any(t == "ELS" and f == [(2, 1.0)] for _n, t, f in cs))
        est = self._portico()
        an = self._analise(est)
        an.Material = ""
        est.Material = ""
        self.doc.recompute()
        calc = an.Proxy.calc
        self.assertTrue(any("Material não informado" in a for a in calc.avisos), calc.avisos)
        self.assertTrue(any("2ª ordem" in a for a in calc.avisos))
        self.assertTrue(any(x.startswith("Aviso:") for x in an.Resumo))


class T43DetalheLigacao(unittest.TestCase):
    """Detalhe de ligação por elementos finitos (submodelo) e vídeo do comportamento."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteDetalhe")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp:
            FreeCADGui.Selection.clearSelection()
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _analise(self):
        import json
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (5000, 3000)), ((5000, 3000), (5000, 0))],
                           "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        self.doc.recompute()
        an = A.criar(self.doc, est)
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        casos = an.Proxy.casos(an)
        casos.append({"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                      "cargas": [{"alvo": "barra", "linha": 1, "tipo": "distribuida", "valor": 10.0,
                                  "direcao": "Para baixo (−Z)"}]})
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        self.doc.recompute()
        return an

    def test_nos_cortes_e_equilibrio(self):
        import PrumoDetalheFEM as D
        an = self._analise()
        js = D.juntas(an)
        self.assertEqual(len(js), 4)
        self.assertEqual(sum(1 for j in js if j["apoio"]), 2)
        det = D.montar(an, FreeCAD.Vector(10, 0, 2990))        # perto do canto: pega o nó do canto
        self.assertLess((det.ponto - FreeCAD.Vector(0, 0, 3000)).Length, 1e-6)
        self.assertEqual(len(det.forma.Solids), 1)
        self.assertEqual(len(det.cortes), 2)
        self.assertEqual(sum(1 for c in det.cortes if c["fixo"]), 1)
        self.assertTrue(all(c["faces"] for c in det.cortes))
        # soldas das barras que terminam no canto
        soldas = [x for x in det.ligacoes if x["tipo"] == "solda"]
        self.assertEqual(len(soldas), 2, det.ligacoes)
        self.assertTrue(all(x["taxa"] > 0 and x["dw"] >= x["dw_min"] for x in soldas))
        # sem carga horizontal: as forças horizontais dos dois cortes se anulam
        self.assertAlmostEqual(sum(c["F"].x for c in det.cortes), 0.0, delta=1.0)
        # a diferença vertical é a carga majorada no pedaço de viga dentro do detalhe (~1,5 × 10 kN/m)
        dz = sum(c["F"].z for c in det.cortes)
        viga = [c for c in det.cortes if c["linha"] == 1][0]
        self.assertGreater(dz, 1.4 * 10.0 * viga["dist"])
        self.assertLess(dz, 1.6 * 10.0 * viga["dist"] + 2000.0)
        # nó apoiado: todos os cortes carregados, a base engastada
        det2 = D.montar(an, FreeCAD.Vector(0, 0, 0))
        self.assertEqual(det2.apoio, "Engaste")
        self.assertFalse(any(c["fixo"] for c in det2.cortes))
        self.assertTrue(det2.faces_fixas)

    def test_detalhe_calculado_confere_com_barras_e_video(self):
        import json
        import os
        import tempfile
        import PrumoDetalheFEM as D
        import PrumoFEM as F
        an = self._analise()
        est, det, erro = D.detalhar(an, FreeCAD.Vector(0, 0, 0), tamanho=14.0)
        self.assertEqual(erro, "", erro)
        e = F.estatisticas(est)
        self.assertGreater(e["svm_max"], 20.0)
        self.assertIn("fy/γa1", F.resumo_resultado(est))
        conf = json.loads(est.get("PrumoConferencia"))
        self.assertEqual(len(conf), 1)
        c = conf[0]
        self.assertLess(abs(c["fem"] - c["barra_mpa"]) / c["barra_mpa"], 0.25, c)
        rb = [o for o in est.cargas if F._eh(o, "Fem::ConstraintRigidBody")]
        self.assertEqual(len(rb), 1)
        self.assertIn("kN", F._descr_restricao(rb[0]))
        if FreeCAD.GuiUp:
            import PrumoVideo as V
            pasta = tempfile.mkdtemp()
            saida = V.gravar_fem(est, os.path.join(pasta, "detalhe.gif"), 320, 180, 4, segundos=1.0)
            self.assertTrue(saida.endswith(".gif") and os.path.getsize(saida) > 1000)
            saida = V.gravar_estrutura(an, os.path.join(pasta, "estrutura.gif"), 320, 180, 4, segundos=2.0)
            self.assertTrue(os.path.getsize(saida) > 1000)
            self.assertEqual(an.Mostrar, "Taxa de uso", "o vídeo tem que devolver a vista como estava")
            import PrumoFEMRelatorio as R
            html = "".join(R._detalhe(est, e))
            self.assertIn("Conferência", html)

    def test_painel_escolhe_no_e_marca_cortes(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoAnaliseVista as V
        an = self._analise()
        p = V.abrir_painel(an.Estrutura, an)
        try:
            p.modo.definir("detalhe")
            p.clique(an.Estrutura, "", (5000.0, 0.0, 2990.0))
            self.assertIsNotNone(p._junta)
            self.assertTrue(p.bt_detalhe.isEnabled())
            textos = [t for _p, t, _d in p.marcas()]
            self.assertIn("nó do detalhe", textos)
            self.assertEqual(sum(1 for t in textos if t.startswith("corte")), 2)
            self.assertGreater(p.det_comb.count(), 0)
        finally:
            p.reject()
            FreeCADGui.Control.closeDialog()


class T44RotulasCargasSecoes(unittest.TestCase):
    """Ideias trazidas do StructureTools: rótulas nas pontas e treliça, carga variável/parcial e
    seção personalizada a partir de um esboço."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteRotulas")
        FreeCAD.setActiveDocument(self.doc.Name)
        self._registrados = []

    def tearDown(self):
        if FreeCAD.GuiUp:
            FreeCADGui.Selection.clearSelection()
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        fechar(self.doc)
        import PrumoSecaoPersonalizada as SP
        for nome in self._registrados:
            SP.desregistrar(nome)

    def _secao(self):
        import PrumoPortico as PT
        return PT, PT.Secao(A=4970, Iy=8578e4, Iz=727e4, J=11.9e4)

    def test_rotulas_viga_gerber_e_trelica(self):
        PT, s = self._secao()
        # viga presa nas duas pontas com rótulas: vira biapoiada
        m = PT.Modelo()
        a, b = m.no((0, 0, 0)), m.no((6000, 0, 0))
        m.barras.append(PT.Barra(a, b, s, (0, 0, 1), liberados=PT.ROTULA_I + PT.ROTULA_J))
        m.apoios[a] = m.apoios[b] = [1] * 6
        c = PT.Caso("q")
        c.distribuidas.append((0, [0, 0, -10], True))
        r = m.resolver(c)
        self.assertAlmostEqual(r.esforcos(0, 3000)["My"] / 1e6, 45.0, places=6)
        self.assertAlmostEqual(r.esforcos(0, 0)["My"], 0.0, places=6)
        self.assertAlmostEqual(r.flecha_local(0)[1], 5 * 10 * 6000 ** 4 / (384 * 200000 * 8578e4), places=6)
        # Gerber: rótula no meio, a parte de fora vira balanço
        m = PT.Modelo()
        a, b, c2 = m.no((0, 0, 0)), m.no((3000, 0, 0)), m.no((6000, 0, 0))
        m.barras.append(PT.Barra(a, b, s, (0, 0, 1)))
        m.barras.append(PT.Barra(b, c2, s, (0, 0, 1), liberados=PT.ROTULA_I))
        m.apoios[a] = [1] * 6
        m.apoios[c2] = [0, 1, 1, 1, 0, 0]
        c = PT.Caso("q")
        c.distribuidas.append((1, [0, 0, -10], True))
        r = m.resolver(c)
        self.assertAlmostEqual(r.esforcos(1, 0)["My"], 0.0, places=6)
        self.assertAlmostEqual(r.esforcos(0, 0)["My"] / 1e6, -45.0, places=6)
        self.assertNotAlmostEqual(r.locais[1][4], r.u[6 * b + 4], places=6)     # giro da ponta rotulada
        # treliça: só força normal, giros dos nós travados sozinhos
        m = PT.Modelo()
        n0, n1, n2 = m.no((0, 0, 0)), m.no((4000, 0, 0)), m.no((2000, 0, 2000))
        for i, j, z in ((n0, n1, (0, 0, 1)), (n0, n2, (0, 1, 0)), (n1, n2, (0, 1, 0))):
            m.barras.append(PT.Barra(i, j, s, z, liberados=PT.TRELICA))
        m.apoios[n0] = [1, 1, 1, 0, 0, 0]
        m.apoios[n1] = [0, 1, 1, 0, 0, 0]
        c = PT.Caso("P")
        c.nos.append((n2, [0, 0, -10], [0, 0, 0]))
        with self.assertRaises(ValueError) as cm:      # treliça plana sem travamento fora do plano
            m.resolver(c)
        self.assertIn("travamento", str(cm.exception))
        m.apoios[n2] = [0, 1, 0, 0, 0, 0]
        for so in (False, True):
            r = m.resolver(c, segunda_ordem=so)
            self.assertAlmostEqual(r.esforcos(0, 10)["N"] / 1e3, 5.0, places=3)
            self.assertAlmostEqual(r.esforcos(1, 10)["N"] / 1e3, -5 * math.sqrt(2), places=2)
            self.assertAlmostEqual(r.esforcos(1, 700)["My"], 0.0, places=3)

    def test_carga_triangular_e_parcial(self):
        PT, s = self._secao()
        m = PT.Modelo()
        a, b = m.no((0, 0, 0)), m.no((6000, 0, 0))
        m.barras.append(PT.Barra(a, b, s, (0, 0, 1)))
        m.apoios[a] = [1, 1, 1, 1, 0, 0]
        m.apoios[b] = [0, 1, 1, 0, 0, 0]
        c = PT.Caso("tri")
        c.distribuidas.append((0, [0, 0, 0], True, 0, 6000, [0, 0, -10]))
        r = m.resolver(c)
        self.assertAlmostEqual(r.reacao(a)[0][2], 10.0, places=6)
        self.assertAlmostEqual(r.reacao(b)[0][2], 20.0, places=6)
        x = 6000 / math.sqrt(3)
        self.assertAlmostEqual(r.esforcos(0, x)["My"] / 1e6, 10 * 6.0 ** 2 / (9 * math.sqrt(3)), places=6)
        self.assertAlmostEqual(r.flecha_local(0, 61)[1], 0.00652 * 10 * 6000 ** 4 / (200000 * 8578e4), delta=0.01)
        c = PT.Caso("parcial")
        c.distribuidas.append((0, [0, 0, -10], True, 2000, 4000))
        r = m.resolver(c)
        self.assertAlmostEqual(r.esforcos(0, 3000)["My"] / 1e6, 25.0, places=6)
        self.assertIn(2000.0, [x for x, _e in r.diagrama(0)])

    def test_analise_com_rotula_e_carga_variavel(self):
        import json
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (5000, 3000)), ((5000, 3000), (5000, 0))],
                           "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        self.doc.recompute()
        an = A.criar(self.doc, est)
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        an.Liberacoes = ["1=Rótula nas duas pontas"]
        casos = [{"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                  "cargas": [{"alvo": "barra", "linha": 1, "tipo": "trapezoidal", "valor": 10.0, "valor2": 10.0,
                              "inicio": 0.0, "fim": 0.0, "direcao": "Para baixo (−Z)"}]}]
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        an.SegundaOrdem = False
        self.doc.recompute()
        calc = an.Proxy.calc
        self.assertIsNone(calc.erro, calc.erro)
        r = calc.resultados[[n for n, t, _f in calc.combinacoes if t == "ELS"][0]]
        # viga rotulada nos pilares: biapoiada, M no meio = qL²/8 = 31,25 kN·m (característico)
        eb, a = [(eb, a) for eb, a in calc.mapa["barras"][1] if a <= 2500.0][-1]
        self.assertAlmostEqual(abs(r.esforcos(eb, 2500.0 - a)["My"]) / 1e6, 31.25, delta=0.05)
        self.assertAlmostEqual(abs(r.esforcos(calc.mapa["barras"][1][0][0], 0.0)["My"]) / 1e6, 0.0, places=4)
        if FreeCAD.GuiUp:
            import PrumoAnaliseVista as V
            p = V.abrir_painel(est, an)
            try:
                p.modo.definir("rotula")
                p.acao_rotula.setCurrentIndex(0)
                p.liberar(1, "ini")              # tira a do início: fica só no fim
                self.assertEqual(an.Proxy.liberacoes(an), {1: "Rótula no fim"})
                p.acao_rotula.setCurrentIndex(1)
                p.clique(E.barras_de(est)[2], "Face1", (5000.0, 0.0, 1500.0))
                self.assertEqual(an.Proxy.liberacoes(an)[2], "Barra de treliça")
                self.assertGreater(p.lista_lib.count(), 1)
                p.tipo_carga.setCurrentIndex(2)
                self.assertTrue(p.valor2.isEnabled() and p.fim.isEnabled())
                self.assertIn("a", V._texto_carga(casos[0]["cargas"][0]))
            finally:
                p.reject()
                FreeCADGui.Control.closeDialog()

    def test_secao_personalizada_tubo_e_calculo(self):
        import os
        import tempfile
        import PrumoPerfis
        import PrumoSecao
        import PrumoSecaoPersonalizada as SP
        import PrumoEstrutura as E
        import PrumoNBR8800 as N
        q = [((-50, -50), (50, -50)), ((50, -50), (50, 50)), ((50, 50), (-50, 50)), ((-50, 50), (-50, -50)),
             ((-45, -45), (45, -45)), ((45, -45), (45, 45)), ((45, 45), (-45, 45)), ((-45, 45), (-45, -45))]
        sk = esboco_linhas(self.doc, q, "XY", "Contorno")
        o = SP.criar(self.doc, sk, "Tubo teste")
        nome = SP.PREFIXO + "Tubo teste"
        self._registrados.append(nome)
        self.assertEqual(o.Avisos, [])
        self.assertAlmostEqual(o.Area, (100 ** 2 - 90 ** 2) / 100.0, places=3)
        self.assertAlmostEqual(o.Ix, (100 ** 4 - 90 ** 4) / 12.0 / 1e4, places=2)
        self.assertLess(abs(o.J * 1e4 - 95 ** 3 * 5) / (95 ** 3 * 5), 0.05)      # Bredt
        it = PrumoPerfis.perfil(nome)
        self.assertIsNotNone(it)
        self.assertIn(nome, PrumoPerfis.nomes(SP.FAMILIA))
        self.assertTrue(PrumoPerfis.confiavel(it))
        p = PrumoSecao.propriedades(nome)
        ver = N.verificar(p, 250.0, 400.0, 3000.0, {"N": -50e3, "Mx": 2e6, "My": 0.0, "Vz": 5e3, "Vy": 0.0})
        self.assertTrue(any("personalizada" in a for a in ver["avisos"]))
        self.assertGreater(ver["taxa"], 0.0)
        # estrutura com o perfil e cálculo por barras
        sk2 = esboco_linhas(self.doc, [((0, 0), (0, 2000)), ((0, 2000), (2000, 2000))], "XZ", "Esq2")
        est = E.criar(self.doc, sk2, nome)
        self.doc.recompute()
        self.assertEqual(len(E.barras_de(est)), 2)
        self.assertTrue(E.barras_de(est)[0].Shape.isValid())
        # salva, tira do catálogo e reabre: o documento registra de novo
        arq = os.path.join(tempfile.mkdtemp(), "secao.FCStd")
        self.doc.saveAs(arq)
        FreeCAD.closeDocument(self.doc.Name)
        SP.desregistrar(nome)
        self.assertIsNone(PrumoPerfis.perfil(nome))
        self.doc = FreeCAD.openDocument(arq)
        self.assertIsNotNone(PrumoPerfis.perfil(nome))


class T45BancadaVasos(unittest.TestCase):
    """Bancada de vasos de pressão: formulário com prévia, suportes, posição, teste de pressão,
    desenho com cotas e tabela, e teste de pressão por elementos finitos de casca."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteVasos")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp:
            FreeCADGui.Selection.clearSelection()
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def test_criterios_e_pressao_de_teste(self):
        import PrumoVaso as V
        self.assertAlmostEqual(V.s_estimado(260.0, 485.0), min(485 / 3.5, 2 * 260 / 3.0))
        self.assertAlmostEqual(V.pressao_teste(1.0, 138.0, 138.0, V.TESTES[0]), 1.3)
        self.assertAlmostEqual(V.pressao_teste(1.0, 120.0, 138.0, V.TESTES[0]), 1.3 * 138 / 120)
        self.assertAlmostEqual(V.pressao_teste(1.0, 138.0, None, V.TESTES[1]), 1.1)

    def _vaso(self, **kw):
        import PrumoVaso as V
        v = V.criar(self.doc, 800, 1500, 1.0, 138.0, 1.0, 1.5, V.TAMPOS[0], "ASTM A516 Gr 70 (SA-516 70)", "100 °C",
                    ['500; 90; Tubo 2" Sch 40; 150'])
        v.Suportes = kw.get("suportes", "Selas")
        v.Sy = 260.0
        for k, val in kw.items():
            if k != "suportes":
                setattr(v, k, val)
        self.doc.recompute()
        return v

    def test_suportes_posicao_e_teste(self):
        import PrumoVaso as V
        v = self._vaso()
        self.assertEqual(v.Avisos, [])
        self.assertTrue(v.Shape.isValid())
        self.assertEqual(len(v.Shape.Solids), 1)
        self.assertAlmostEqual(v.PMTA, min(v.PMTACostado, v.PMTATampo))
        self.assertAlmostEqual(v.PressaoTeste, 1.3 * v.PMTA)
        self.assertAlmostEqual(v.PressaoTesteFundo, v.PressaoTeste + V.AGUA * 800, places=6)
        self.assertLess(v.Shape.BoundBox.ZMin, -400)                  # selas abaixo do vaso
        v.Orientacao = "Vertical"
        v.Suportes = "Saia"
        self.doc.recompute()
        bb = v.Shape.BoundBox
        self.assertGreater(bb.ZLength, bb.XLength)                     # em pé
        self.assertGreater(v.PressaoTesteFundo - v.PressaoTeste, V.AGUA * 1500)
        v.Suportes = "Selas"
        self.doc.recompute()
        self.assertTrue(any("horizontal" in a for a in v.Avisos))
        self.assertIn("Teste de pressão", V.memoria(v))

    def test_desenho_com_cotas_e_tabela(self):
        import PrumoVaso as V
        v = self._vaso()
        page = V.desenho(v)
        tipos = [o.TypeId for o in page.Views]
        self.assertIn("TechDraw::DrawProjGroup", tipos)
        self.assertEqual(tipos.count("TechDraw::DrawViewDimension"), 2)
        ann = [o for o in page.Views if o.TypeId == "TechDraw::DrawViewAnnotation"][0]
        self.assertTrue(any("PMTA" in l for l in ann.Text))
        self.assertTrue(any(l.startswith("N1") for l in ann.Text))

    def test_painel_cria_e_edita(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoVaso as V
        p = V.abrir_painel()
        try:
            i = p.material.findData("ASTM A516 Gr 70 (SA-516 70)")
            self.assertGreaterEqual(i, 0)
            p.material.setCurrentIndex(i)
            p._estimar_s()
            self.assertGreater(p.S.value(), 100.0)
            p._mais_bocal()
            self.assertEqual(len(p._linhas_bocais()), 1)
            self.assertIsNone(p.pendencia())
        finally:
            p.accept()
            FreeCADGui.Control.closeDialog()
        vs = [o for o in self.doc.Objects if "PressaoProjeto" in o.PropertiesList]
        self.assertEqual(len(vs), 1)
        self.assertEqual(len(vs[0].Bocais), 1)
        self.assertGreater(vs[0].PressaoTeste, 0.0)

    def test_teste_de_pressao_casca(self):
        """Membrana no meio do costado: von Mises ≈ √3/2 · P·R/t (casca cilíndrica fechada)."""
        import math
        import PrumoVaso as V
        import PrumoFEM as F
        v = self._vaso()
        est, erro = V.simular_teste(v, tamanho=45.0)
        self.assertEqual(erro, "", erro)
        self.assertEqual(F.avaliar(est)["_bloqueios"], [])
        r = est.resultados[0]
        nos = r.Mesh.FemMesh.Nodes
        tc = V.chapa_acima(v.MinimoCostado)
        Rm = 400 + tc / 2.0
        meio = [s for n, s in zip(r.NodeNumbers, r.vonMises) if abs(nos[n].x - 750) < 60 and nos[n].z > 0.6 * Rm]
        teoria = v.PressaoTeste * Rm / tc * math.sqrt(3) / 2
        self.assertLess(abs(sum(meio) / len(meio) - teoria) / teoria, 0.10)

class T46NBR2024(unittest.TestCase):
    """NBR 8800:2024 / NBR 8681:2025: área efetiva, Cb em λr sem teto, imperfeições (forças nocionais e
    rigidez 80 %), tipos de caso novos com os nomes antigos, seção personalizada completa, solda e
    parafuso."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteNBR2024")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        FreeCAD.closeDocument(self.doc.Name)

    def test_area_efetiva_e_cb(self):
        import math
        import PrumoNBR8800 as N
        import PrumoSecao as S
        fy, E = 250.0, 200000.0
        p = S.propriedades("W 200 x 22,5")
        Aef, nota = N.area_efetiva(p, fy, 1.0)
        self.assertAlmostEqual(Aef, p["A"], msg="W 200 x 22,5 sem elemento esbelto em A36")
        # chapa esbelta: alma de 4 mm com h = 600 mm → bef pela Tabela 5 (c1 = 0,18, c2 = 1,31)
        q = dict(p, tipo="I", h=600.0, tw=4.0, bf=200.0, tf=16.0, A=2 * 200 * 16 + 600 * 4.0)
        Aef, nota = N.area_efetiva(q, fy, 1.0)
        lim = 1.49 * math.sqrt(E / fy)
        sel = (1.31 * lim / 150.0) ** 2 * fy
        r = math.sqrt(sel / fy)
        bef = 600 * (1 - 0.18 * r) * r
        self.assertAlmostEqual(Aef, q["A"] - (600 - bef) * 4.0, places=6)
        self.assertIn("alma", nota)
        # Cb sem o teto de 3,0
        self.assertGreater(N.cb(1.0, 0.0, 0.0, 0.0), 3.0)
        # λr com Cb: a FLT na faixa inelástica não multiplica por Cb e Mcr usa Cb
        M1 = N.flexao_x(p, fy, 4000.0, 1.0)[0]
        M2 = N.flexao_x(p, fy, 4000.0, 2.0)[0]
        self.assertGreater(M2, M1)
        self.assertLessEqual(M2, p["Zx"] * fy / 1.10 + 1e-6)
        # cortante: kv = 5,34 numa alma esbelta
        q2 = dict(p, h_tw=120.0)
        lp = 1.10 * math.sqrt(5.34 * E / fy)
        lr = 1.37 * math.sqrt(5.34 * E / fy)
        self.assertGreater(120.0, lr)
        self.assertAlmostEqual(N.cortante_z(q2, fy)[0], 1.24 * (lp / 120.0) ** 2 * 0.6 * p["d"] * p["tw"] * fy / 1.10,
                               places=6)
        # sem K: Ne com L
        Ne, _m = N.forca_ne(p, 3000.0, K=2.1)
        self.assertAlmostEqual(Ne, N.forca_ne(p, 3000.0)[0])

    def test_tipos_de_caso_8681_2025(self):
        import json
        import PrumoAnaliseEstrutura as A
        self.assertEqual(A.TIPOS_CASO["Permanente (equipamentos)"][0], 1.25)
        self.assertEqual(A.TIPOS_CASO["Permanente (elementos industrializados)"][0], 1.30)
        self.assertEqual(A.TIPOS_CASO["Temperatura gerada por equipamentos"][0], 1.50)
        self.assertEqual(A.tipo_atual("Temperatura"), "Temperatura (variação atmosférica)")
        self.assertEqual(A.tipo_atual("Permanente (elementos em geral e equipamentos)"), "Permanente (elementos em geral)")

        class Obj:
            Casos = [json.dumps({"nome": "T", "tipo": "Temperatura", "cargas": []})]
        self.assertEqual(A.Analise.casos(None, Obj())[0]["tipo"], "Temperatura (variação atmosférica)")

    def _portico(self):
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((6000, 0), (6000, 3000)), ((0, 3000), (6000, 3000))], "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        casos = [A.caso_padrao(), {"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                                   "cargas": [{"alvo": "barra", "linha": 2, "tipo": "distribuida", "valor": 8.0,
                                               "direcao": "Para baixo (−Z)"}]}]
        apoios = {A._chave_no((0, 0, 0)): "Engaste", A._chave_no((6000, 0, 0)): "Engaste"}
        return est, casos, apoios

    def test_forcas_nocionais(self):
        import numpy as np
        import PrumoAnaliseEstrutura as A
        est, casos, apoios = self._portico()
        calc = A.calcular(est, casos, apoios)
        self.assertIsNone(calc.erro, calc.erro)
        nomes = [n for n, t, _f in calc.combinacoes if t == "ELU"]
        self.assertTrue(any(n.endswith("imperfeição +X") for n in nomes), nomes)
        self.assertTrue(any(n.endswith("imperfeição −Y") for n in nomes), nomes)
        self.assertFalse([n for n in nomes if "imperfeição" not in n], "combinação gravitacional sem imperfeição")
        n = [x for x in nomes if x.endswith("imperfeição +X")][0]
        caso = calc.imperfeicoes[n][1]
        H = sum(f[0] for _no, f, _m in caso.nos)
        fat = dict((nm, f) for nm, _t, f in calc.combinacoes)[n]
        _m, lista, _mapa = A.montar_modelo(est, casos, apoios)
        g = calc.modelo.cargas_gravitacionais([(lista[k], f) for k, f in fat if f])
        livres = [k for k in range(len(g)) if k not in calc.modelo.apoios]
        self.assertAlmostEqual(H * 1000.0, 0.003 * g[livres].sum(), delta=1e-6 * g.sum())
        # a reação horizontal total equilibra as forças nocionais
        r = calc.resultados[n]
        Rx = sum(r.reac[6 * k] for k in calc.modelo.apoios)
        self.assertAlmostEqual(-Rx / 1000.0, H, delta=1e-3 * abs(H) + 1e-6)
        self.assertTrue(any("deslocabilidade" in a for a in calc.avisos), calc.avisos)
        # combinação com vento não recebe imperfeição
        casos.append({"nome": "V", "tipo": "Vento", "cargas": [{"alvo": "barra", "linha": 0, "tipo": "distribuida",
                                                                 "valor": 1.0, "direcao": "+X"}]})
        calc2 = A.calcular(est, casos, apoios)
        self.assertIsNone(calc2.erro, calc2.erro)
        for nm, t, f in calc2.combinacoes:
            if any(casos[k]["tipo"] == "Vento" and v for k, v in f):
                self.assertNotIn("imperfeição", nm)

    def test_deslocabilidade_do_pilar_em_balanco(self):
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000))], "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        casos = [{"nome": "P", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                  "cargas": [{"alvo": "no", "no": A._chave_no((0, 0, 3000)), "tipo": "no", "valor": 10.0,
                              "direcao": "Para baixo (−Z)"}]}]
        apoios = {A._chave_no((0, 0, 0)): "Engaste"}
        calc = A.calcular(est, casos, apoios)
        self.assertIsNone(calc.erro, calc.erro)
        self.assertGreater(calc.amplificacao, 1.10)
        self.assertLess(calc.amplificacao, 1.40)
        self.assertEqual(calc.rigidez, 0.8)
        self.assertTrue(any("média deslocabilidade" in x for x in calc.avisos), calc.avisos)
        calc1 = A.calcular(est, casos, apoios, segunda_ordem=False)
        self.assertTrue(any(x.startswith("ATENÇÃO: análise de 1ª ordem") for x in calc1.avisos), calc1.avisos)

    def test_rigidez_reduzida(self):
        import PrumoPortico as PT
        m = PT.Modelo()
        s = PT.Secao(2860.0, 2029e4, 142e4, 6.0e4)
        a, b = m.no((0, 0, 0)), m.no((0, 0, 3000))
        m.barras.append(PT.Barra(a, b, s, (1, 0, 0)))
        m.apoios[a] = [1] * 6
        c = PT.Caso("H")
        c.nos.append((b, [1.0, 0, 0], [0, 0, 0]))
        u1 = m.resolver(c).u[6 * b]
        u8 = m.resolver(c, rigidez=0.8).u[6 * b]
        self.assertAlmostEqual(u8, u1 / 0.8, delta=1e-9 * abs(u1) + 1e-12)

    def test_secao_personalizada_completa(self):
        import PrumoNBR8800 as N
        import PrumoSecao as S
        import PrumoSecaoPersonalizada as SP
        import PrumoSecaoGeral as SG
        d, bf, tw, tf = 300.0, 150.0, 8.0, 12.0
        a, b, w = bf / 2, d / 2, tw / 2
        I = [(-a, -b), (a, -b), (a, -b + tf), (w, -b + tf), (w, b - tf), (a, b - tf), (a, b), (-a, b), (-a, b - tf),
             (-w, b - tf), (-w, -b + tf), (-a, -b + tf)]
        ch = SG.chapas(I, [])
        self.assertEqual(sum(1 for c in ch if not c["apoiada_nas_duas"]), 4)
        self.assertEqual(sum(1 for c in ch if c["apoiada_nas_duas"]), 1)
        it = SP.item_de("I teste 2024", I, [])
        SP.registrar(it)
        try:
            p = S.propriedades(it["nome"])
            pI = S.propriedades({"nome": "I teste 2024 cat", "tipo": "I", "d": d, "bf": bf, "tw": tw, "tf": tf,
                                 "massa": 1.0})
            self.assertAlmostEqual(p["Cw"], pI["Cw"], delta=0.01 * pI["Cw"])
            self.assertAlmostEqual(p["J"], pI["J"], delta=0.02 * pI["J"])
            self.assertAlmostEqual(p["x0"], 0.0, delta=0.05)
            for Lb in (3000.0, 8000.0):
                self.assertAlmostEqual(N.flexao_x(p, 250.0, Lb)[0], N.flexao_x(pI, 250.0, Lb)[0],
                                       delta=0.01 * N.flexao_x(pI, 250.0, Lb)[0])
            self.assertAlmostEqual(N.compressao(p, 250.0, 4000.0)[0], N.compressao(pI, 250.0, 4000.0)[0],
                                   delta=0.01 * N.compressao(pI, 250.0, 4000.0)[0])
        finally:
            SP.desregistrar(it["nome"])
        # U: centro de cisalhamento perto da fórmula de paredes finas
        d, bf, tw, tf = 200.0, 75.0, 6.0, 10.0
        U = [(0, 0), (bf, 0), (bf, tf), (tw, tf), (tw, d - tf), (bf, d - tf), (bf, d), (0, d)]
        g = SG.empenamento(U, [])
        h0, b1 = d - tf, bf - tw / 2
        e = 3 * b1 ** 2 * tf / (6 * b1 * tf + h0 * tw)
        self.assertAlmostEqual(g["cu"] + g["x0"], tw / 2 - e, delta=1.0)

    def test_solda_no_contorno(self):
        import PrumoDetalheFEM as D
        import PrumoSecao as S
        p = S.propriedades("W 200 x 22,5")
        e = {"N": 100000.0, "Vy": 0.0, "Vz": 0.0, "T": 0.0, "My": 0.0, "Mz": 0.0}
        r = D.solda_contorno(p, e, 250.0, 400.0)
        self.assertAlmostEqual(r["q"], 100000.0 / r["Lw"], places=6)
        self.assertAlmostEqual(r["Lw"], 2 * p["d"] + 4 * p["bf"] - 2 * p["tw"], delta=1.0)
        self.assertEqual(r["fonte"], "sugerida")
        r2 = D.solda_contorno(p, dict(e, My=20e6), 250.0, 400.0, perna=3.0)
        self.assertGreater(r2["taxa_solda"], r["taxa_solda"])
        self.assertIn("perna", r2["texto"])

    def test_solda_e_parafuso(self):
        import math
        import PrumoNBR8800 as N
        F, txt = N.solda_filete(6.0, 100.0, 250.0, 400.0, 8.0)
        self.assertAlmostEqual(F, 0.6 * 0.707 * 6 * 100 * 485 / 1.35, places=6)
        self.assertNotIn("ATENÇÃO", txt)
        self.assertIn("ATENÇÃO", N.solda_filete(3.0, 100.0, 250.0, 400.0, 16.0)[1])
        # Tabela 11 (limite 6,3 mm), máximo ao longo da borda (6.2.6.2.2), comprimento mínimo (6.2.6.2.3)
        self.assertEqual(N.perna_minima(6.3), 3.0)
        self.assertEqual(N.perna_minima(6.35), 5.0)
        self.assertEqual(N.perna_maxima(5.0), 5.0)
        self.assertEqual(N.perna_maxima(8.0), 6.5)
        self.assertIn("6.2.6.2.2", N.solda_filete(8.0, 100.0, 250.0, 400.0, 8.0)[1])
        self.assertIn("6.2.6.2.3", N.solda_filete(6.0, 30.0, 250.0, 400.0, 8.0)[1])
        self.assertAlmostEqual(N.parafuso_interacao(30.0, 40.0, 100.0, 100.0), 0.25)
        Fv, Ft = N.parafuso(16.0, 825.0)
        Ab = math.pi * 16 ** 2 / 4
        self.assertAlmostEqual(Fv, 0.45 * Ab * 825 / 1.35)
        self.assertAlmostEqual(Ft, 0.75 * Ab * 825 / 1.35)
        self.assertAlmostEqual(N.parafuso(16.0, 825.0, rosca_no_plano=False)[0], 0.56 * Ab * 825 / 1.35)


class T47MolasTracaoModos(unittest.TestCase):
    """Apoio em mola, contraventamento só de tração e frequências naturais (modos de vibrar)."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteModos")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        FreeCAD.closeDocument(self.doc.Name)

    def test_mola_exata(self):
        import PrumoPortico as PT
        m = PT.Modelo()
        s = PT.Secao(2860.0, 2029e4, 142e4, 6.0e4)
        a, b = m.no((0, 0, 0)), m.no((0, 0, 1000))
        m.barras.append(PT.Barra(a, b, s, (1, 0, 0)))
        m.apoios[a] = [1, 1, 0, 1, 1, 1]
        m.molas[a] = [0, 0, 5000.0, 0, 0, 0]          # 5 kN/mm
        m.apoios[b] = [1, 1, 0, 1, 1, 1]
        c = PT.Caso("P")
        c.nos.append((b, [0, 0, -10.0], [0, 0, 0]))
        r = m.resolver(c)
        self.assertAlmostEqual(r.u[6 * a + 2], -10000.0 / 5000.0, places=9)
        self.assertAlmostEqual(r.u[6 * b + 2], -2.0 - 10000.0 * 1000.0 / (200000.0 * 2860.0), places=9)

    def test_mola_pela_analise(self):
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        sk = esboco_linhas(self.doc, [((0, 0), (4000, 0))], "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        self.doc.recompute()
        mola = A.texto_mola(0.0, 2.0)
        self.assertEqual(A.rigidez_mola(mola), (0.0, 0.0, 2.0))
        casos = [{"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                  "cargas": [{"alvo": "barra", "linha": 0, "tipo": "distribuida", "valor": 5.0,
                              "direcao": "Para baixo (−Z)"}]}]
        calc = A.calcular(est, casos, {A._chave_no((0, 0, 0)): "Engaste", A._chave_no((4000, 0, 0)): mola},
                          segunda_ordem=False)
        self.assertIsNone(calc.erro, calc.erro)
        nome = [n for n, t, _f in calc.combinacoes if t == "ELS"][0]
        r = calc.resultados[nome]
        no_b = A._no_mais_proximo(calc.modelo, (4000, 0, 0), 1.0)
        no_a = A._no_mais_proximo(calc.modelo, (0, 0, 0), 1.0)
        d = r.u[6 * no_b + 2]
        self.assertLess(d, 0.0)
        Fm = -2000.0 * d                                   # N
        self.assertAlmostEqual(r.reac[6 * no_a + 2] + Fm, 5.0 * 4000.0, delta=5.0)

    def test_contraventamento_so_tracao(self):
        import PrumoPortico as PT
        m = PT.Modelo()
        s = PT.Secao(2860.0, 2029e4, 142e4, 6.0e4)
        sb = PT.Secao(300.0, 1e3, 1e3, 1e2)
        n = [m.no(p) for p in ((0, 0, 0), (3000, 0, 0), (0, 0, 3000), (3000, 0, 3000))]
        for i, j in ((0, 2), (1, 3), (2, 3)):
            m.barras.append(PT.Barra(n[i], n[j], s, (0, 1, 0), liberados=PT.TRELICA))
        m.barras.append(PT.Barra(n[0], n[3], sb, (0, 1, 0), liberados=PT.TRELICA, so_tracao=True))
        m.barras.append(PT.Barra(n[1], n[2], sb, (0, 1, 0), liberados=PT.TRELICA, so_tracao=True))
        m.apoios[n[0]] = [1, 1, 1, 0, 0, 0]
        m.apoios[n[1]] = [1, 1, 1, 0, 0, 0]
        m.apoios[n[2]] = [0, 1, 0, 0, 0, 0]
        m.apoios[n[3]] = [0, 1, 0, 0, 0, 0]
        c = PT.Caso("H")
        c.nos.append((n[2], [10.0, 0, 0], [0, 0, 0]))
        r = m.resolver(c)
        self.assertEqual(r.ativos[3:], [True, False])
        N_t = r.esforcos(3, 0.0)["N"]
        self.assertAlmostEqual(N_t, 10000.0 * math.sqrt(2.0), delta=1.0)
        self.assertAlmostEqual(r.esforcos(4, 0.0)["N"], 0.0, delta=1e-6)

    def test_frequencia_viga_biapoiada(self):
        import PrumoPortico as PT
        L, E, Iz, mkg = 6000.0, 200000.0, 142e4, 22.5
        m = PT.Modelo()
        s = PT.Secao(2860.0, 2029e4, Iz, 6.0e4, massa_kgm=mkg)
        nos = [m.no((L * k / 8.0, 0, 0)) for k in range(9)]
        for i, j in zip(nos[:-1], nos[1:]):
            m.barras.append(PT.Barra(i, j, s, (0, 0, 1)))
        m.apoios[nos[0]] = [1, 1, 1, 1, 0, 0]
        m.apoios[nos[-1]] = [0, 1, 1, 1, 0, 0]
        modos = m.modos(3)
        exato = math.pi / (2 * L ** 2) * math.sqrt(E * Iz / (mkg * 1e-6))
        self.assertAlmostEqual(modos[0][0], exato, delta=0.01 * exato)
        self.assertTrue(all(modos[k][0] <= modos[k + 1][0] for k in range(len(modos) - 1)))

    def test_painel_lista_modos(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import json
        import PrumoEstrutura as E
        import PrumoAnaliseEstrutura as A
        import PrumoAnaliseVista as V
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (5000, 3000)), ((5000, 3000), (5000, 0))],
                           "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        self.doc.recompute()
        an = A.criar(self.doc, est)
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        an.Casos = [json.dumps(A.caso_padrao(), ensure_ascii=False)]
        self.doc.recompute()
        p = V.abrir_painel(est, an)
        try:
            modos = p.calcular_modos()
            self.assertTrue(modos)
            self.assertEqual(p.lista_modos.count(), len(modos))
            self.assertIn("Hz", p.lista_modos.item(0).text())
            p.lista_modos.setCurrentRow(1)
            self.assertEqual(an.Modo, 2)
            self.assertEqual(an.Mostrar, A.MODO_VIBRAR)
        finally:
            p.reject()
            FreeCADGui.Control.closeDialog()


class T48AssistenteEstrutura(unittest.TestCase):
    """Assistente de estruturas: etapas com pendências que bloqueiam o cálculo, cálculo, resultados e
    memória de cálculo."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteAssistEst")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
            import PrumoAssistenteEstrutura as AE
            d = AE._estado.get("dock")
            if d is not None and AE.F._vivo(d):
                d.close()
        FreeCAD.closeDocument(self.doc.Name)

    def _estrutura(self):
        import PrumoEstrutura as E
        sk = esboco_linhas(self.doc, [((0, 0), (0, 3000)), ((0, 3000), (5000, 3000)), ((5000, 3000), (5000, 0))],
                           "XZ")
        est = E.criar(self.doc, sk, "W 200 x 22,5", material="ASTM A36")
        self.doc.recompute()
        return est

    def test_conferencia_das_etapas(self):
        import json
        import PrumoAnaliseEstrutura as A
        import PrumoAssistenteEstrutura as AE
        est = self._estrutura()
        r = AE.avaliar(None, est)
        self.assertEqual(r["estrutura"][0], AE.ERRO)
        self.assertTrue(r["_bloqueios"])
        an = A.criar(self.doc, est)
        an.Casos = []
        self.doc.recompute()
        r = AE.avaliar(an)
        self.assertEqual(r["apoios"][0], AE.VAZIO)
        self.assertIn("apoios", [k for k, _m in r["_bloqueios"]])
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        casos = [A.caso_padrao(),
                 {"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                  "cargas": [{"alvo": "barra", "linha": 1, "tipo": "distribuida", "valor": 0.0,
                              "direcao": "Para baixo (−Z)"}]}]
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        self.doc.recompute()
        r = AE.avaliar(an)
        self.assertEqual(r["cargas"][0], AE.ERRO, r["cargas"])
        self.assertTrue(any("valor zero" in m for _k, m in r["_bloqueios"]))
        casos[1]["cargas"][0]["valor"] = 8.0
        casos[1]["cargas"].append({"alvo": "barra", "linha": 7, "tipo": "distribuida", "valor": 1.0,
                                   "direcao": "Para baixo (−Z)"})
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        self.doc.recompute()
        r = AE.avaliar(an)
        self.assertTrue(any("não existe mais" in m for _k, m in r["_bloqueios"]), r["_bloqueios"])
        del casos[1]["cargas"][1]
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        self.doc.recompute()
        r = AE.avaliar(an)
        self.assertEqual(r["_bloqueios"], [])
        self.assertEqual(r["calculo"][0], AE.OK, r["calculo"])
        self.assertIn(r["resultado"][0], (AE.OK, AE.AVISO, AE.ERRO))
        self.assertTrue(any("vento" in m for _n, m in r["cargas"][2]))
        self.assertIn("Taxa máxima", r["resultado"][1])
        # apoio que não cai num nó
        an.Apoios = list(an.Apoios) + ["%s=Engaste" % A._chave_no((2500, 0, 0))]
        self.doc.recompute()
        self.assertTrue(any("não cai em nenhum nó" in m for _k, m in AE.avaliar(an)["_bloqueios"]))

    def test_assistente_calcula_e_gera_relatorio(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import json
        import os
        import tempfile
        import PrumoAnaliseEstrutura as A
        import PrumoAssistenteEstrutura as AE
        est = self._estrutura()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(est)
        dock = AE.mostrar()
        w = dock.widget()
        self.assertEqual(w.estrutura_escolhida(), est)
        self.assertTrue(w.bt_criar.isVisible() or w.analise() is None)
        w._criar_analise()
        an = w.analise()
        self.assertIsNotNone(an)
        self.assertFalse(w.bt_calc.isEnabled(), "sem apoios o cálculo não pode liberar")
        self.assertTrue(w.etapas["apoios"].aberta())
        p = w.painel("apoio")
        self.assertEqual(p.modo.valor(), "apoio")
        p.reject()
        FreeCADGui.Control.closeDialog()
        an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((5000, 0, 0))]
        casos = [A.caso_padrao(), {"nome": "Q", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                                   "cargas": [{"alvo": "barra", "linha": 1, "tipo": "distribuida", "valor": 5.0,
                                               "direcao": "Para baixo (−Z)"}]}]
        an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
        w.atualizar(force=True)
        self.assertTrue(w.bt_calc.isEnabled())
        self.assertTrue(w.calcular())
        r = AE.avaliar(an)
        self.assertEqual(r["calculo"][0], AE.OK)
        self.assertNotEqual(w.c_taxa.valor.text(), "—")
        w.ck_so.setChecked(False)
        self.assertFalse(an.SegundaOrdem)
        w.ck_so.setChecked(True)
        w.calcular()
        modos = w._frequencias()
        self.assertTrue(modos and "Hz" in w.lb_freq.text())
        js = w._listar_juntas()
        self.assertTrue(js and w.cb_junta.count() == len(js))
        pdf = os.path.join(tempfile.mkdtemp(), "memoria.pdf")
        self.assertEqual(w.relatorio(pdf), pdf)
        self.assertTrue(os.path.getsize(pdf) > 10000)
        self.assertEqual(AE.avaliar(an)["relatorio"][0], AE.OK)


class T49ReguaHistorico(unittest.TestCase):
    """Régua de histórico do Corpo: recuar a ponta, inserir no ponto da régua e voltar ao fim."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteRegua")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        FreeCAD.closeDocument(self.doc.Name)

    def _corpo(self):
        import Part
        import Sketcher
        doc = self.doc
        corpo = doc.addObject("PartDesign::Body", "Body")
        sk = corpo.newObject("Sketcher::SketchObject", "Esboco")
        sk.AttachmentSupport = (doc.getObject("XY_Plane") or corpo.Origin.OriginFeatures[3], [""])
        sk.MapMode = "FlatFace"
        V = FreeCAD.Vector
        pts = [V(0, 0, 0), V(40, 0, 0), V(40, 30, 0), V(0, 30, 0)]
        for k in range(4):
            sk.addGeometry(Part.LineSegment(pts[k], pts[(k + 1) % 4]))
        for k in range(4):
            sk.addConstraint(Sketcher.Constraint("Coincident", k, 2, (k + 1) % 4, 1))
        pad = corpo.newObject("PartDesign::Pad", "Extrusao")
        pad.Profile = sk
        pad.Length = 10
        doc.recompute()
        fil = corpo.newObject("PartDesign::Chamfer", "Chanfro")
        fil.Base = (pad, ["Edge1"])
        fil.Size = 2
        doc.recompute()
        return corpo, sk, pad, fil

    def test_recuar_e_voltar(self):
        import PrumoRegua as R
        corpo, sk, pad, fil = self._corpo()
        self.assertIs(corpo.Tip, fil)
        ls = R.itens(corpo)
        self.assertEqual([o.Name for o in ls], [sk.Name, pad.Name, fil.Name])
        self.assertEqual(R.posicao_da_ponta(corpo), 3)
        v_total = corpo.Shape.Volume
        # régua logo depois da extrusão: o chanfro sai do modelo
        self.assertIs(R.mover_regua(corpo, 2), pad)
        self.assertIs(corpo.Tip, pad)
        self.assertAlmostEqual(corpo.Shape.Volume, 40 * 30 * 10, delta=1e-6)
        self.assertGreater(corpo.Shape.Volume, v_total)
        self.assertEqual(R.posicao_da_ponta(corpo), 2)
        # régua logo depois do esboço: nenhum sólido acima → corpo vazio
        self.assertIsNone(R.mover_regua(corpo, 1))
        self.assertIsNone(corpo.Tip)
        self.assertTrue(corpo.Shape.isNull() or corpo.Shape.Volume < 1e-9)
        # Desfazer volta a régua
        self.doc.undo()
        self.assertIs(corpo.Tip, pad)
        # fim
        self.assertIs(R.ate_o_fim(corpo), fil)
        self.assertAlmostEqual(corpo.Shape.Volume, v_total, delta=1e-6)

    def test_nova_operacao_entra_no_ponto_da_regua(self):
        import PrumoRegua as R
        corpo, sk, pad, fil = self._corpo()
        R.mover_regua(corpo, 2)
        furo = corpo.newObject("PartDesign::Chamfer", "Chanfro2")
        furo.Base = (pad, ["Edge3"])
        furo.Size = 1
        self.doc.recompute()
        ls = [o.Name for o in R.itens(corpo)]
        self.assertLess(ls.index(furo.Name), ls.index(fil.Name), ls)
        self.assertIs(corpo.Tip, furo)

    def test_painel(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoRegua as R
        from PySide import QtCore
        corpo, sk, pad, fil = self._corpo()
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", corpo)
        dock = R.mostrar(True)
        try:
            w = dock.widget()
            w.atualizar(force=True)
            textos = [w.lista.item(i).text() for i in range(w.lista.count())]
            self.assertEqual(len(textos), 4)
            self.assertIn("régua", textos[-1])
            w._botao("menos")
            self.assertIs(corpo.Tip, pad)
            regua = [i for i in range(w.lista.count()) if w.lista.item(i).data(QtCore.Qt.UserRole + 1)]
            self.assertEqual(regua, [2])
            self.assertIn("recuado", w.sub.text())
            w._botao("fim")
            self.assertIs(corpo.Tip, fil)
            w.mover(0)
            self.assertIsNone(corpo.Tip)
            w._botao("mais")
            self.assertIs(corpo.Tip, pad)
        finally:
            dock.hide()

    def test_regua_na_arvore(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoRegua as R
        from PySide import QtWidgets
        corpo, sk, pad, fil = self._corpo()
        FreeCADGui.ActiveDocument.ActiveView.setActiveObject("pdbody", corpo)
        mw = FreeCADGui.getMainWindow()
        for d in mw.findChildren(QtWidgets.QDockWidget):
            if d.windowTitle() in ("Modelo", "Model"):
                d.show()
                d.raise_()
        for _ in range(5):
            FreeCADGui.updateGui()
        tree = R.arvore()
        self.assertIsNotNone(tree)
        aberto = False
        for _ in range(30):
            FreeCADGui.updateGui()
            QtWidgets.QApplication.processEvents()
            try:
                it = R.item_do_corpo(tree, corpo)
                if it is not None:
                    it.setExpanded(True)
                    aberto = it.isExpanded()
            except RuntimeError:
                aberto = False          # a árvore refez os itens: procura de novo
            if aberto:
                break
        if not aberto:
            tops = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
            info = [(t.text(0), [t.child(j).text(0) for j in range(t.childCount())]) for t in tops]
            arvs = [(t.isVisible(), t.topLevelItemCount()) for t in mw.findChildren(QtWidgets.QTreeWidget)
                    if "TreeWidget" in t.metaObject().className()]
            self.fail("corpo não achado: %s %s %s / %s" % (self.doc.Label, corpo.Label, info, arvs))
        for _ in range(10):
            FreeCADGui.updateGui()
        ctl = R.instalar_na_arvore()
        ctl.atualizar()
        vs = R.vaos(tree, corpo)
        # vão do início (0), depois da extrusão (o esboço fica dentro dela: 2) e depois do chanfro (3)
        self.assertEqual([p for _y, p in vs], [0, 2, 3])
        self.assertFalse(ctl.faixa.isHidden())
        self.assertAlmostEqual(ctl.faixa.geometry().center().y(), vs[-1][0], delta=4)
        # arrastar a régua até o vão de cima do chanfro recua o modelo
        ctl.soltar(vs[1][0] + 2)
        self.assertIs(corpo.Tip, pad)
        self.assertFalse(ctl.sombra.isHidden())
        ctl.soltar(vs[0][0])
        self.assertIsNone(corpo.Tip)
        ctl.ao_fim()
        self.assertIs(corpo.Tip, fil)
        g = FreeCAD.ParamGet(R.PARAM)
        antes = g.GetBool("ReguaNaArvore", True)
        try:
            g.SetBool("ReguaNaArvore", False)
            ctl.atualizar()
            self.assertTrue(ctl.faixa.isHidden())
        finally:
            g.SetBool("ReguaNaArvore", antes)
            ctl.atualizar()


class T50ConferirEsboco(unittest.TestCase):
    """Conferência do esboço ao sair: pontas quase encostadas, perfil aberto, degeneradas, correção."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteConfEsboco")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        import PrumoValidarEsboco as VE
        a = VE._estado.get("aviso")
        if a is not None:
            try:
                a.fechar()
            except RuntimeError:
                pass
        if FreeCAD.GuiUp and FreeCADGui.ActiveDocument is not None:
            try:
                FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
        FreeCAD.closeDocument(self.doc.Name)

    def _retangulo(self, folga=0.03, degenerada=False, pad=True):
        import Part
        V = FreeCAD.Vector
        corpo = self.doc.addObject("PartDesign::Body", "Body")
        sk = corpo.newObject("Sketcher::SketchObject", "Perfil")
        sk.AttachmentSupport = (corpo.Origin.OriginFeatures[3], [""])
        sk.MapMode = "FlatFace"
        sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(40, 0, 0)))
        sk.addGeometry(Part.LineSegment(V(40, 0, 0), V(40, 30, 0)))
        sk.addGeometry(Part.LineSegment(V(40, 30 + folga, 0), V(0, 30, 0)))
        sk.addGeometry(Part.LineSegment(V(0, 30, 0), V(0, 0, 0)))
        if degenerada:
            sk.addGeometry(Part.LineSegment(V(10, 10, 0), V(10, 10.0000001, 0)))
        p = None
        if pad:
            p = corpo.newObject("PartDesign::Pad", "Extrusao")
            p.Profile = sk
            p.Length = 5
        self.doc.recompute()
        return sk, p

    def test_pontas_quase_encostadas_e_correcao(self):
        import PrumoValidarEsboco as VE
        sk, pad = self._retangulo(folga=0.03, degenerada=True)
        r = VE.conferir(sk)
        self.assertTrue(r["precisa_fechado"])
        self.assertEqual(len(r["quase"]), 1)
        self.assertAlmostEqual(r["quase"][0][0], 0.03, places=6)
        self.assertEqual(r["degeneradas"], 1)
        self.assertTrue(r["corrigivel"])
        self.assertTrue(any("quase encostadas" in x for x in r["problemas"]), r["problemas"])
        r2 = VE.corrigir(sk)
        self.assertEqual(r2["problemas"], [], r2)
        self.assertEqual(len(sk.Shape.Wires), 1)
        self.assertTrue(sk.Shape.Wires[0].isClosed())
        self.assertTrue(pad.Shape.isValid() and pad.Shape.Volume > 5000)
        # Desfazer volta o esboço como estava
        self.doc.undo()
        self.doc.recompute()
        self.assertEqual(len(VE.conferir(sk)["quase"]), 1)

    def test_esboco_aberto_de_proposito_nao_avisa(self):
        import Part
        import PrumoValidarEsboco as VE
        V = FreeCAD.Vector
        sk = self.doc.addObject("Sketcher::SketchObject", "Esqueleto")
        sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(0, 3000, 0)))
        sk.addGeometry(Part.LineSegment(V(0, 3000, 0), V(5000, 3000, 0)))
        self.doc.recompute()
        self.assertEqual(VE.conferir(sk)["problemas"], [])
        # o mesmo esboço como perfil de extrusão (Part): ponta solta passa a importar
        ex = self.doc.addObject("Part::Extrusion", "Ext")
        ex.Base = sk
        self.doc.recompute()
        r = VE.conferir(sk)
        self.assertTrue(r["precisa_fechado"])
        self.assertTrue(any("ponta(s) solta(s)" in x for x in r["problemas"]), r["problemas"])

    def test_retangulo_fechado_sem_aviso(self):
        import PrumoValidarEsboco as VE
        import Sketcher
        sk, pad = self._retangulo(folga=0.0)
        for k in range(4):
            sk.addConstraint(Sketcher.Constraint("Coincident", k, 2, (k + 1) % 4, 1))
        self.doc.recompute()
        self.assertEqual(VE.conferir(sk)["problemas"], [])

    def test_aviso_ao_sair_da_edicao(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoValidarEsboco as VE
        sk, pad = self._retangulo(folga=0.05)
        gd = FreeCADGui.getDocument(self.doc.Name)
        gd.setEdit(sk.Name)
        self._esperar(300)
        gd.resetEdit()
        self._esperar(900)
        a = VE._estado.get("aviso")
        self.assertIsNotNone(a, "devia avisar ao sair do esboço com pontas quase encostadas")
        self.assertTrue(a.bt_corrigir.isVisible())
        a.corrigir()
        self.assertIn("Pronto", a.texto.text())
        self.assertTrue(sk.Shape.Wires[0].isClosed())

    def test_console_python_comeca_fechado(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        from PySide import QtWidgets
        import PrumoGui
        g = FreeCAD.ParamGet(PrumoGui.PARAM_PATH)
        tinha = "ModoDistribuicao" in g.GetBools()
        antes = g.GetBool("ModoDistribuicao", False)
        mw = FreeCADGui.getMainWindow()
        console = mw.findChild(QtWidgets.QDockWidget, "Python console")
        relatorio = mw.findChild(QtWidgets.QDockWidget, "Report view")
        if console is None or relatorio is None:
            self.skipTest("sem o painel do console")
        vis = console.isVisible()
        vis_r = relatorio.isVisible()
        try:
            g.RemBool("ModoDistribuicao")
            console.setVisible(True)
            relatorio.setVisible(True)
            PrumoGui.apply_modo_distribuicao()
            self.assertFalse(console.isVisible(), "o console Python deve começar fechado")
            self.assertFalse(relatorio.isVisible(), "o Relatório deve começar fechado (qualquer tela)")
            g.SetBool("ModoDistribuicao", False)        # desligado de propósito: quem programa vê o console
            PrumoGui.apply_modo_distribuicao()
            self.assertTrue(console.isVisible())
        finally:
            if tinha:
                g.SetBool("ModoDistribuicao", antes)
            else:
                g.RemBool("ModoDistribuicao")
            console.setVisible(vis)
            relatorio.setVisible(vis_r)

    def _esperar(self, ms):
        from PySide import QtCore, QtWidgets
        t = QtCore.QElapsedTimer()
        t.start()
        while t.elapsed() < ms:
            QtWidgets.QApplication.processEvents()


class T51FaixaContextual(unittest.TestCase):
    """Aba Esboço mostra só as ferramentas do momento: fora da edição (criar/editar/validar) e dentro
    (desenhar/restringir/modificar)."""

    def setUp(self):
        import PrumoRibbon
        self.R = PrumoRibbon
        self.rb = PrumoRibbon._state.get("ribbon")
        if self.rb is None:
            self.skipTest("faixa Prumo não instalada nesta sessão")
        self.p = FreeCAD.ParamGet(PrumoRibbon.PARAM_PATH)
        self.tinha = "RibbonContextual" in self.p.GetBools()
        self.antes = self.p.GetBool("RibbonContextual", True)
        self.p.SetBool("RibbonContextual", True)
        self.doc = novo_doc("PrumoTesteFaixaCtx")
        FreeCAD.setActiveDocument(self.doc.Name)
        body = self.doc.addObject("PartDesign::Body", "Body")
        self.sk = esboco_retangulo(body)

    def tearDown(self):
        if FreeCADGui.ActiveDocument is not None:
            try:
                FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
        if self.tinha:
            self.p.SetBool("RibbonContextual", self.antes)
        else:
            self.p.RemBool("RibbonContextual")
        fechar(self.doc)

    def _cmds(self):
        for _ in range(5):
            FreeCADGui.updateGui()
        return {b._cmd for pn in self.rb.paineis for b in pn.findChildren(QtWidgets.QWidget)
                if getattr(b, "_cmd", None)}, len(self.rb.paineis)

    def test_regra(self):
        tab = self.rb._tabs[self.rb.tab_index("esboco")]
        c = self.R.cabe_no_contexto
        self.assertTrue(c(tab, "Esboço", "Sketcher_NewSketch", False))
        self.assertFalse(c(tab, "Esboço", "Sketcher_NewSketch", True))
        self.assertFalse(c(tab, "Desenhar", "Sketcher_CreateLine", False))
        self.assertTrue(c(tab, "Desenhar", "Sketcher_CreateLine", True))
        self.assertFalse(c(tab, "Esboço", "Sketcher_LeaveSketch", False))
        self.assertTrue(c(tab, "Esboço", "Sketcher_LeaveSketch", True))
        peca = self.rb._tabs[self.rb.tab_index("peca")]
        self.assertTrue(c(peca, "Qualquer", "PartDesign_Pad", True))     # outras abas não são filtradas
        self.p.SetBool("RibbonContextual", False)
        self.assertTrue(c(tab, "Desenhar", "Sketcher_CreateLine", False))

    def test_troca_ao_entrar_e_sair(self):
        self.rb.select_tab("esboco", user=True)
        fora, _ = self._cmds()
        self.assertIn("Sketcher_NewSketch", fora)
        self.assertNotIn("Sketcher_CreateLine", fora)
        self.assertNotIn("Sketcher_LeaveSketch", fora)
        FreeCADGui.ActiveDocument.setEdit(self.sk.Name)
        self.rb.check_edit()
        dentro, _ = self._cmds()
        self.assertEqual(self.rb._tabs[self.rb.tabbar.currentIndex()]["id"], "esboco")
        self.assertIn("Sketcher_CreateLine", dentro)
        self.assertIn("Sketcher_LeaveSketch", dentro)
        self.assertNotIn("Sketcher_NewSketch", dentro)
        self.assertIn("Sketcher_Translate", dentro)        # padrão linear
        self.assertIn("Sketcher_Rotate", dentro)           # padrão circular
        self.assertNotIn("Sketcher_ValidateSketch", dentro)
        FreeCADGui.ActiveDocument.resetEdit()
        self.rb.select_tab("esboco", user=True)
        self.rb.check_edit()
        de_novo, _ = self._cmds()
        self.assertIn("Sketcher_NewSketch", de_novo)
        self.assertNotIn("Sketcher_CreateLine", de_novo)



class T52Esboco3D(unittest.TestCase):
    """Esboço 3D: pontos no espaço, ramais, curvas nos cantos, plano com Tab e uso como esqueleto."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteEsboco3D")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def test_polilinha_e_comprimento(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        o = E.criar(self.doc, [V(0, 0, 0), V(1000, 0, 0), V(1000, 0, 500), V(1000, 800, 500)])
        self.assertEqual(len(o.Shape.Edges), 3)
        self.assertAlmostEqual(float(o.Comprimento), 2300.0, 6)
        self.assertEqual(len(o.Shape.Wires), 1)

    def test_ramal_e_fechado(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        o = E.criar(self.doc, [V(0, 0, 0), V(1000, 0, 0), V(1000, 0, 1000), V(500, 0, 0), V(500, 600, 0)],
                    quebras=[3])
        self.assertEqual(len(o.Shape.Wires), 2)
        self.assertEqual(len(o.Shape.Edges), 3)
        o.Quebras = []
        o.Fechado = True
        self.doc.recompute()
        self.assertTrue(o.Shape.Wires[0].isClosed())

    def test_curva_nos_cantos(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        o = E.criar(self.doc, [V(0, 0, 0), V(1000, 0, 0), V(1000, 1000, 0)], raio=100.0)
        tipos = [type(e.Curve).__name__ for e in o.Shape.Edges]
        self.assertIn("Circle", tipos)
        esperado = 900 + 900 + math.pi / 2 * 100
        self.assertAlmostEqual(float(o.Comprimento), esperado, 3)
        self.assertTrue(o.Shape.Wires[0].isValid())
        # arco tangente: varredura de um círculo pelo caminho gera sólido válido
        import Part
        perfil = Part.Wire(Part.makeCircle(20, V(0, 0, 0), V(1, 0, 0)))
        tubo = Part.Wire(o.Shape.Edges).makePipeShell([perfil], True, True)
        self.assertTrue(tubo.isValid())
        self.assertGreater(tubo.Volume, 0)

    def test_plano_e_grade(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        self.assertEqual(E.proximo_plano("XY"), "YZ")
        self.assertEqual(E.proximo_plano("YZ"), "ZX")
        self.assertEqual(E.proximo_plano("ZX"), "XY")
        # vista de cima (olhando -Z) no plano XY que passa por z=300
        p = E.no_plano(V(120, 40, 5000), V(0, 0, -1), V(0, 0, 300), "XY")
        self.assertAlmostEqual(p.z, 300, 6)
        self.assertAlmostEqual(p.x, 120, 6)
        self.assertIsNone(E.no_plano(V(0, 0, 0), V(1, 0, 0), V(0, 0, 0), "XY"))   # plano de perfil
        q = E.na_grade(V(123, 47, 999), V(0, 0, 300), 10.0, "XY")
        self.assertEqual((q.x, q.y, q.z), (120.0, 50.0, 300.0))

    def test_esqueleto_da_estrutura(self):
        import PrumoEsboco3D as E
        import PrumoEstrutura
        V = FreeCAD.Vector
        o = E.criar(self.doc, [V(0, 0, 0), V(0, 0, 1000), V(1000, 0, 1000), V(1000, 800, 1000)])
        self.assertEqual(len(PrumoEstrutura.arestas(o)), 3)

    def test_painel_digitado_e_tab(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoEsboco3D as E
        from PySide import QtCore, QtGui
        pn = E.abrir_painel()
        o = pn.obj
        pn.relativo.setChecked(True)
        for v in ((0, 0, 0), (500, 0, 0), (0, 0, 300)):
            for s_, x in zip(pn.coord, v):
                s_.setValue(x)
            pn.adicionar_digitado()
        self.assertEqual([tuple(p) for p in o.Pontos], [(0, 0, 0), (500, 0, 0), (500, 0, 300)])
        self.assertEqual(pn.tabela.rowCount(), 3)
        # ramal: próximo ponto absoluto começa trecho novo
        pn.bt_ramal.setChecked(True)
        pn.relativo.setChecked(False)
        for s_, x in zip(pn.coord, (250, 0, 0)):
            s_.setValue(x)
        pn.adicionar_digitado()
        for s_, x in zip(pn.coord, (250, 400, 0)):
            s_.setValue(x)
        pn.adicionar_digitado()
        self.assertEqual(list(o.Quebras), [3])
        self.assertEqual(len(o.Shape.Wires), 2)
        # modo desenho: Tab (com o cursor na vista) troca o plano, Esc termina o trecho
        pn.bt_clicar.setChecked(True)
        self.assertIsNotNone(pn._vista)
        original = E._cursor_na_vista
        E._cursor_na_vista = lambda: True
        try:
            ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Tab, QtCore.Qt.NoModifier)
            self.assertTrue(pn._filtro.eventFilter(pn.form, ev))
            self.assertEqual(pn.plano, "YZ")
            ev = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
            pn._filtro.eventFilter(pn.form, ev)
            self.assertTrue(pn._ramal_pendente)
            pn._filtro.eventFilter(pn.form, ev)
            self.assertIsNone(pn._vista, "Esc de novo para de desenhar")
        finally:
            E._cursor_na_vista = original
        pn.remover()
        self.assertEqual(len(o.Pontos), 4)
        pn.accept()
        self.assertIsNotNone(self.doc.getObject(o.Name))

    def test_restricoes_resolvem(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        # linha torta que vira "ao longo de X" com 500 mm; a segunda fica perpendicular a ela e com 300 mm
        o = E.criar(self.doc, [V(0, 0, 0), V(480, 30, 10), V(500, 280, 0)])
        o.Restricoes = ["eixo:0:X", "comprimento:0:500", "perpendicular:0:1", "comprimento:1:300", "eixo:1:Z"]
        ok, erro = E.aplicar_restricoes(o)
        self.doc.recompute()
        self.assertTrue(ok, erro)
        p = o.Pontos
        self.assertAlmostEqual((p[1] - p[0]).Length, 500, 3)
        self.assertAlmostEqual(p[1].y, 0, 4)
        self.assertAlmostEqual(p[1].z, 0, 4)
        self.assertAlmostEqual((p[2] - p[1]).Length, 300, 3)
        self.assertAlmostEqual(abs(p[2].z - p[1].z), 300, 3)
        self.assertEqual((p[0].x, p[0].y, p[0].z), (0, 0, 0))            # o primeiro ponto não sai do lugar
        self.assertIn("cumpridas", o.Situacao)
        o.Restricoes = list(o.Restricoes) + ["comprimento:0:700"]          # conflito com a cota de 500
        ok, _e = E.aplicar_restricoes(o)
        self.assertFalse(ok)
        self.assertIn("conflito", o.Situacao)

    def test_construcao_fica_fora_da_forma(self):
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        o = E.criar(self.doc, [V(0, 0, 0), V(1000, 0, 0), V(1000, 500, 0), V(0, 500, 0)])
        self.assertEqual(len(o.Shape.Edges), 3)
        o.Construcao = [1]
        self.doc.recompute()
        self.assertEqual(len(o.Shape.Edges), 2)
        self.assertAlmostEqual(float(o.Comprimento), 2000, 6)
        import PrumoEstrutura
        self.assertEqual(len(PrumoEstrutura.arestas(o)), 2)               # a estrutura não usa a construção

    def test_painel_restricoes_automaticas_e_botoes(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoEsboco3D as E
        V = FreeCAD.Vector
        pn = E.abrir_painel()
        o = pn.obj
        pn.adicionar(V(0, 0, 0))
        pn.adicionar(V(800, 0, 0))                 # ao longo de X
        pn.adicionar(V(800, 0, 600))               # ao longo de Z
        pn.adicionar(V(1300, 200, 600))            # torta: sem eixo
        self.assertIn("eixo:0:X", o.Restricoes)
        self.assertIn("eixo:1:Z", o.Restricoes)
        self.assertEqual(len([r for r in o.Restricoes if r.startswith("eixo")]), 2)
        self.assertEqual(pn.lista.count(), 3)
        # ramal que sai do ponto P2 (clicado sobre ele): fica preso
        pn.bt_ramal.setChecked(True)
        pn.adicionar(V(800, 0, 0), coincide=1)
        pn.adicionar(V(800, 400, 0))
        self.assertIn("coincidente:4:1", o.Restricoes)
        # cota na primeira linha: o ramal acompanha o ponto P2
        pn.selecionar_segmentos([0])
        pn.cota.setValue(1000)
        pn.cotar()
        self.assertAlmostEqual(o.Pontos[1].x, 1000, 3)
        self.assertAlmostEqual(o.Pontos[4].x, 1000, 3)
        # linha de construção
        pn.selecionar_segmentos([2])
        pn.alternar_construcao()
        self.assertEqual(list(o.Construcao), [2])
        self.assertIn("construção", pn.lista.item(2).text())
        # paralelas: a linha torta fica paralela ao ramal (Y)
        pn.selecionar_segmentos([2, 3])
        pn.relacionar("paralela")
        a, b = o.Pontos[2], o.Pontos[3]
        self.assertAlmostEqual(b.x - a.x, 0, 3)
        self.assertAlmostEqual(b.z - a.z, 0, 3)
        # remover um ponto renumera as restrições
        pn.tabela.clearSelection()
        pn.remover()                                # tira o último (ponta do ramal)
        self.assertFalse(any(r.startswith("paralela") for r in o.Restricoes))
        self.assertIn("coincidente:4:1", o.Restricoes)
        pn.accept()

    def test_cancelar_desfaz(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoEsboco3D as E
        n0 = len(self.doc.Objects)
        pn = E.abrir_painel()
        pn.adicionar(FreeCAD.Vector(1, 2, 3))
        pn.reject()
        self.assertEqual(len(self.doc.Objects), n0)


class T53Tubulacao(unittest.TestCase):
    """Tubulação PVC soldável sobre o Esboço 3D: conexões por nó, corte descontando avanços, lista."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteTubulacao")
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        fechar(self.doc)

    def _tracado(self, pts, quebras=()):
        import PrumoEsboco3D as E
        return E.criar(self.doc, [FreeCAD.Vector(*p) for p in pts], quebras=quebras)

    def test_joelhos_e_corte(self):
        import PrumoTubulacao as T
        import PrumoCatalogoTubos as C
        L = C.linha(C.PADRAO)
        e = self._tracado([(0, 0, 0), (1000, 0, 0), (1000, 0, 1000), (1000, 1000, 1000)])
        t = T.criar(e, dn=25)
        self.assertEqual(t.Conexoes, ["2 × Joelho 90° soldável 25 mm"])
        res = t.Proxy.ultimo
        avanco = L["joelho90"][25] - L["bolsa"][25]
        cortes = sorted(round(x["corte"], 3) for x in res["tubos"])
        self.assertAlmostEqual(cortes[0], 1000 - 2 * avanco, 3)      # trecho do meio: dois joelhos
        self.assertAlmostEqual(cortes[1], 1000 - avanco, 3)
        self.assertEqual(t.Barras, 1)                                  # ~2,98 m cabem numa barra de 6 m
        self.assertFalse(t.Avisos)
        self.assertTrue(t.Shape.isValid())
        self.assertEqual(len(t.Shape.Solids), 5)                        # 3 tubos + 2 joelhos

    def test_te_reducao_e_cap(self):
        import PrumoTubulacao as T
        # linha principal 0-2000 em x, ramal em y no meio
        e = self._tracado([(0, 0, 0), (1000, 0, 0), (2000, 0, 0), (1000, 0, 0), (1000, 800, 0)], quebras=[3])
        t = T.criar(e, dn=50, tampar=True)
        self.assertIn("1 × Tê soldável 50 mm", t.Conexoes)
        t.DiametrosTrechos = ["3: 25"]
        self.doc.recompute()
        self.assertIn("1 × Tê de redução soldável 50 × 25", t.Conexoes)
        self.assertIn("2 × Cap soldável 50 mm", t.Conexoes)
        self.assertIn("1 × Cap soldável 25 mm", t.Conexoes)
        self.assertFalse(t.Avisos)

    def test_45_reducao_alinhada_e_angulo_ruim(self):
        import PrumoTubulacao as T
        e = self._tracado([(0, 0, 0), (1000, 0, 0), (1700, 700, 0)])
        t = T.criar(e, dn=32)
        self.assertEqual(t.Conexoes, ["1 × Joelho 45° soldável 32 mm"])
        e.Pontos = [FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1000, 0, 0), FreeCAD.Vector(2000, 0, 0)]
        t.DiametrosTrechos = ["2: 25"]
        self.doc.recompute()
        self.assertEqual(t.Conexoes, ["1 × Luva de redução soldável 32 × 25"])
        e.Pontos = [FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1000, 0, 0), FreeCAD.Vector(1500, 300, 0)]
        t.DiametrosTrechos = []
        self.doc.recompute()
        self.assertEqual(t.Conexoes, [])
        self.assertTrue(any("ângulo" in a for a in t.Avisos))

    def test_trecho_longo_emenda_e_continuo(self):
        import PrumoTubulacao as T
        e = self._tracado([(0, 0, 0), (4000, 0, 0), (9000, 0, 0)])     # alinhados: um tubo de 9 m
        t = T.criar(e, dn=20)
        self.assertEqual(t.Conexoes, [])
        self.assertEqual(t.Barras, 2)
        self.assertIn("1 emenda(s)", t.ListaCorte[0])

    def test_cruzeta(self):
        import PrumoTubulacao as T
        e = self._tracado([(-500, 0, 0), (500, 0, 0), (0, -500, 0), (0, 0, 0), (0, 500, 0)], quebras=[2])
        # o traçado do ramal passa pelo nó do meio: divide a linha principal no centro
        e.Pontos = [FreeCAD.Vector(-500, 0, 0), FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(500, 0, 0),
                    FreeCAD.Vector(0, -500, 0), FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 500, 0)]
        e.Quebras = [3]
        self.doc.recompute()
        t = T.criar(e, dn=50)
        self.assertEqual(t.Conexoes, ["1 × Cruzeta soldável 50 mm"])

    def test_cruzeta_de_25_e_dados_a_conferir_avisam(self):
        import PrumoTubulacao as T
        import PrumoCatalogoTubos as C
        V = FreeCAD.Vector
        L = C.linha(C.PADRAO)
        self.assertIn(25, L["cruzeta"])
        self.assertNotIn(20, L["cruzeta"], "a 'cruzeta de 20' da tabela de 2008 é a de 25 (código 22090259)")
        self.assertAlmostEqual(L["densidade"], 1430.0)
        # tê de 110 com ramal de 85: não há tê de redução, entra a bucha curta 110 × 85 (medida duvidosa)
        segs = [(V(0, 0, 0), V(1000, 0, 0)), (V(1000, 0, 0), V(2000, 0, 0)), (V(1000, 0, 0), V(1000, 800, 0))]
        r = T.montar(segs, [110, 110, 85])
        self.assertTrue(any("110 × 85" in a and "conferir" in a for a in r["avisos"]), r["avisos"])
        # um tê sem medida duvidosa não avisa nada
        r = T.montar(segs, [50, 50, 50])
        self.assertFalse(r["avisos"])

    def test_registro_divide_o_tubo(self):
        import PrumoTubulacao as T
        import PrumoCatalogoTubos as C
        L = C.linha(C.PADRAO)
        e = self._tracado([(0, 0, 0), (2000, 0, 0)])
        t = T.criar(e, dn=25)
        t.Registros = ["1: 500"]
        self.doc.recompute()
        self.assertEqual(t.Conexoes, ["1 × Registro de esfera soldável 25 mm"])
        rg = L["registro"][25]
        cortes = sorted(round(x["corte"], 2) for x in t.Proxy.ultimo["tubos"])
        self.assertAlmostEqual(cortes[0], 500 - (rg["A"] / 2 - rg["bolsa"]), 2)
        self.assertAlmostEqual(cortes[1], 1500 - (rg["A"] / 2 - rg["bolsa"]), 2)
        self.assertTrue(t.Shape.isValid())
        t.Registros = ["1: 10"]                                 # encostado na ponta: não cabe
        self.doc.recompute()
        self.assertTrue(any("não cabe" in a for a in t.Avisos))
        t.Diametro = "110 mm"
        t.Registros = ["1: 1000"]
        self.doc.recompute()
        self.assertTrue(any("registro de 110" in a for a in t.Avisos))

    def test_lista_de_materiais(self):
        import PrumoTubulacao as T
        import PrumoBOM
        e = self._tracado([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0), (1000, 1000, 800)])
        t = T.criar(e, dn=25)
        linhas = PrumoBOM.coletar([e, t], 7850)
        den = {l.denominacao: l for l in linhas}
        self.assertEqual(den["Joelho 90° soldável 25 mm"].qtd, 2)
        tubo = [l for l in linhas if l.denominacao.startswith("Tubo")][0]
        self.assertEqual(tubo.qtd, 1)
        self.assertEqual(tubo.material, "PVC rígido")
        self.assertIsNone(tubo.massa)
        self.assertEqual(len(linhas), 2)                        # o traçado não entra na lista
        sheet = PrumoBOM.gravar_planilha(self.doc, linhas)
        self.assertEqual(sheet.get("G2"), "—")

    def test_lista_e_painel(self):
        import PrumoTubulacao as T
        e = self._tracado([(0, 0, 0), (1000, 0, 0), (1000, 1000, 0)])
        t = T.criar(e, dn=25)
        txt = T.texto_lista(t)
        self.assertIn("Joelho 90° soldável 25 mm", txt)
        self.assertIn("Tigre", txt)
        if not FreeCAD.GuiUp:
            return
        pn = T.abrir_painel(t)
        self.assertEqual(pn.tabela.rowCount(), 2)
        pn.dn.setCurrentIndex(pn.dn.findData(40))
        self.assertEqual(t.Conexoes, ["1 × Joelho 90° soldável 40 mm"])
        pn.accept()


class T54ReferenciasAutomaticas(unittest.TestCase):
    """Geometria externa por padrão: arestas da face de apoio entram ao abrir; as não usadas saem."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteReferencias")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
        self.antes = self.g.GetBool("ReferenciasAutomaticas", True)
        self.g.SetBool("ReferenciasAutomaticas", True)

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.ActiveDocument is not None:
            try:
                FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
        self.g.SetBool("ReferenciasAutomaticas", self.antes)
        fechar(self.doc)

    def _bloco(self):
        body = self.doc.addObject("PartDesign::Body", "Body")
        sk = esboco_retangulo(body, 40, 20)
        pad = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 10
        self.doc.recompute()
        return body, pad

    def _face_de_cima(self, pad):
        for i, f in enumerate(pad.Shape.Faces):
            if abs(f.normalAt(0, 0).z - 1) < 1e-6 and abs(f.CenterOfMass.z - 10) < 1e-6:
                return "Face%d" % (i + 1)

    def test_face_de_apoio(self):
        import Part
        import Sketcher
        import PrumoReferencias as R
        body, pad = self._bloco()
        sk2 = body.newObject("Sketcher::SketchObject", "Sobre")
        sk2.AttachmentSupport = (pad, [self._face_de_cima(pad)])
        sk2.MapMode = "FlatFace"
        self.doc.recompute()
        self.assertEqual(R.ao_entrar(sk2), 4)
        self.assertEqual(len(R._externas(sk2)), 4)
        self.assertEqual(R.ao_entrar(sk2), 0)                 # não repete
        # uma linha presa a uma das referências: só ela fica ao sair
        g = sk2.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(10, 5, 0)))
        sk2.addConstraint(Sketcher.Constraint("PointOnObject", g, 1, -3))
        self.doc.recompute()
        self.assertEqual(R.ao_sair(sk2), 3)
        self.assertEqual(len(R._externas(sk2)), 1)
        self.assertEqual(len(sk2.ReferenciasAuto), 1)
        self.assertEqual(sk2.Constraints[-1].Second, -3)      # a restrição continua na mesma aresta
        self.doc.recompute()
        self.assertTrue(sk2.isValid())

    def test_plano_da_origem_pega_arestas_no_plano(self):
        import PrumoReferencias as R
        body, pad = self._bloco()
        sk3 = body.newObject("Sketcher::SketchObject", "NoPlano")
        sk3.AttachmentSupport = (body.Origin.OriginFeatures[3], [""])       # XY
        sk3.MapMode = "FlatFace"
        self.doc.recompute()
        self.assertEqual(R.ao_entrar(sk3), 4)                 # a base do bloco está em z = 0

    def test_desligado_e_manual_fica(self):
        import PrumoReferencias as R
        body, pad = self._bloco()
        sk2 = body.newObject("Sketcher::SketchObject", "Sobre")
        sk2.AttachmentSupport = (pad, [self._face_de_cima(pad)])
        sk2.MapMode = "FlatFace"
        sk2.addExternal(pad.Name, "Edge1")                     # referência feita à mão
        self.doc.recompute()
        self.g.SetBool("ReferenciasAutomaticas", False)
        self.assertEqual(R.ao_entrar(sk2), 0)
        self.g.SetBool("ReferenciasAutomaticas", True)
        R.ao_entrar(sk2)
        R.ao_sair(sk2)
        nomes = [s for _o, s in R._externas(sk2)]
        self.assertEqual(nomes, ["Edge1"])                     # a manual não sai

    def test_ao_editar(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoReferencias as R
        from PySide import QtWidgets
        body, pad = self._bloco()
        sk2 = body.newObject("Sketcher::SketchObject", "Sobre")
        sk2.AttachmentSupport = (pad, [self._face_de_cima(pad)])
        sk2.MapMode = "FlatFace"
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(sk2.Name)
        for _ in range(40):
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            if R._externas(sk2):
                break
            import time
            time.sleep(0.02)
        self.assertEqual(len(R._externas(sk2)), 4)
        FreeCADGui.ActiveDocument.resetEdit()
        for _ in range(5):
            FreeCADGui.updateGui()
        self.assertEqual(len(R._externas(sk2)), 0)


def painel_lateral_montado(P):
    """Testes do painel lateral partem dele montado: outro teste pode ter deixado um painel solto,
    escondido ou dentro da janela de 10 s em que a tela inicial esconde os laterais."""
    import time
    from PySide import QtCore, QtWidgets
    try:
        import PrumoInicio
        PrumoInicio._side["esconder_ate"] = 0
    except Exception:
        pass
    mw = FreeCADGui.getMainWindow()
    ds = P.docks(mw)
    achado = []
    for n in (P.ARVORE, P.PROPRIEDADES):
        d = ds.get(n)
        if d is None:
            continue
        if d.isFloating() or not d.isVisible() or mw.dockWidgetArea(d) != QtCore.Qt.LeftDockWidgetArea:
            achado.append("%s solto=%s visivel=%s" % (n, d.isFloating(), d.isVisible()))
            d.setFloating(False)
            d.show()
    if achado or P.barra_de_abas(mw) is None:
        FreeCAD.Console.PrintLog("teste: painel lateral desmontado (%s); remontando\n" % "; ".join(achado))
        P._estado["juntou"] = False
    t = time.time()
    while time.time() - t < 0.5:
        QtWidgets.QApplication.processEvents()
        P.organizar()
        time.sleep(0.02)


class T55PainelLateral(unittest.TestCase):
    """Painel lateral único: Árvore | Propriedades | comando, abas no alto, aba do comando só enquanto ele dura."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelLateral as P
        if not P.ligado() or P.ARVORE not in P.docks():
            self.skipTest("painel lateral único desligado nesta sessão")
        self.P = P
        self.doc = novo_doc("PrumoTestePainel")
        painel_lateral_montado(P)
        FreeCAD.setActiveDocument(self.doc.Name)

    def tearDown(self):
        if FreeCADGui.ActiveDocument is not None:
            try:
                FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
        fechar(self.doc)

    def _assentar(self, s=0.6):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            self.P.organizar()
            time.sleep(0.02)

    def _abas(self):
        bar = self.P.barra_de_abas()
        self.assertIsNotNone(bar, "sem a barra de abas do painel")
        return bar, [t for _n, t in self.P.abas()]

    def _atual(self):
        return self.P.titulo_real(self.P.aba_atual())

    def test_init_liga_arvore_e_propriedades(self):
        dw = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/DockWindows")
        self.assertTrue(dw.GetGroup("TreeView").GetBool("Enabled", False))
        self.assertTrue(dw.GetGroup("PropertyView").GetBool("Enabled", False))
        self.assertFalse(dw.GetGroup("ComboView").GetBool("Enabled", True))
        nomes = {d.objectName() for d in FreeCADGui.getMainWindow().findChildren(
            __import__("PySide").QtWidgets.QDockWidget)}
        self.assertNotIn("Model", nomes, "o painel Modelo do FreeCAD não deveria existir")

    def test_abas_no_alto_sem_titulo(self):
        from PySide import QtCore
        self._assentar()
        bar, abas = self._abas()
        self.assertEqual(abas[:2], ["Árvore", "Propriedades"])
        mw = FreeCADGui.getMainWindow()
        self.assertEqual(mw.tabPosition(QtCore.Qt.LeftDockWidgetArea), __import__("PySide").QtWidgets.QTabWidget.North)
        for nome, d in self.P.docks().items():
            tb = d.titleBarWidget()
            self.assertTrue(tb is not None and tb.objectName() == "PrumoSemTitulo", nome)
        self.assertIn("#F7BE00", bar.styleSheet())
        self.assertFalse(bar.tabIcon(0).isNull(), "aba Árvore sem ícone")

    def test_aba_do_comando_entra_e_sai(self):
        body = self.doc.addObject("PartDesign::Body", "Body")
        sk = esboco_retangulo(body)
        self.doc.recompute()
        self._assentar()
        tar = self.P.docks()[self.P.TAREFA]
        self.assertFalse(tar.isVisible(), "aba do comando aberta sem comando")
        self.P.docks()[self.P.PROPRIEDADES].raise_()
        self._assentar(0.3)
        FreeCADGui.ActiveDocument.setEdit(sk.Name)
        self._assentar()
        bar, abas = self._abas()
        self.assertTrue(tar.isVisible())
        self.assertEqual(self.P.titulo_real(self.P.TAREFA), sk.Label)
        self.assertIn(sk.Label, abas)
        self.assertEqual(self._atual(), sk.Label, "a aba do comando não veio para a frente")
        FreeCADGui.ActiveDocument.resetEdit()
        self._assentar()
        bar, abas = self._abas()
        self.assertFalse(tar.isVisible(), "a aba do comando ficou depois de concluir")
        self.assertNotIn(sk.Label, abas)
        self.assertEqual(self._atual(), "Propriedades", "não voltou para a aba de antes")

    def test_abas_compactas_quando_falta_espaco(self):
        from PySide import QtWidgets
        self._assentar()
        bar = self.P.barra_de_abas()
        ds = self.P.docks()
        mw = FreeCADGui.getMainWindow()
        arv = ds[self.P.ARVORE]
        larg = arv.width()
        try:
            for d in ds.values():
                d.setMaximumWidth(230)          # força o painel estreito
            mw.resizeDocks([arv], [230], __import__("PySide").QtCore.Qt.Horizontal)
            self._assentar(0.5)
            if not self.P._estado["compacto"]:
                self.skipTest("a janela não deixou estreitar o painel")
            atual = self.P.aba_atual()
            for n, d in ds.items():
                if d.isVisible() and n != atual:
                    self.assertEqual(d.windowTitle(), "", n)
                    self.assertEqual(d.toggleViewAction().text(), self.P.titulo_real(n))
            self.assertEqual(ds[atual].windowTitle(), self.P.titulo_real(atual))
        finally:
            for d in ds.values():
                d.setMaximumWidth(16777215)
            mw.resizeDocks([arv], [max(larg, 360)], __import__("PySide").QtCore.Qt.Horizontal)
            self._assentar(0.3)

    def test_titulo_curto(self):
        self.assertEqual(self.P._curto("Esboço002"), "Esboço002")
        longo = self.P._curto("Parâmetros da extrusão com dois lados")
        self.assertLessEqual(len(longo), self.P.LARGURA_TITULO)
        self.assertTrue(longo.endswith("…"))

    def test_cotas_sem_vermelho(self):
        import PrumoEstilo as E
        for tab in (E.VIEW_COLORS, E.VIEW_COLORS_ESC):
            for k in ("ConstrainedDimColor", "ConstrainedIcoColor"):
                c = tab[k].lstrip("#")
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                self.assertFalse(r > g + 40 and r > b + 40, "{} ainda avermelhada: {}".format(k, tab[k]))
        # a cota não pode ter a cor das linhas do desenho: precisa ser um cinza (sem puxar para o azul)
        for tab, linha in ((E.VIEW_COLORS, "EditedEdgeColor"), (E.VIEW_COLORS_ESC, "EditedEdgeColor")):
            cota = tab["ConstrainedDimColor"].lstrip("#")
            r, g, b = int(cota[0:2], 16), int(cota[2:4], 16), int(cota[4:6], 16)
            self.assertLess(max(r, g, b) - min(r, g, b), 40, "cota devia ser cinza: " + tab["ConstrainedDimColor"])
            self.assertNotEqual(tab["ConstrainedDimColor"].upper(), tab[linha].upper())


class T56PropriedadesEAparencia(unittest.TestCase):
    """Abas Propriedades (cartões) e Aparência: montam pela seleção, mudam o modelo, entram no desfazer."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelLateral as P
        P.organizar()
        if P.inspetor() is None or P.aparencia() is None:
            self.skipTest("abas novas não instaladas nesta sessão")
        self.P = P
        self.doc = novo_doc("PrumoTesteInspetor")
        FreeCAD.setActiveDocument(self.doc.Name)
        body = self.doc.addObject("PartDesign::Body", "Body")
        self.sk = esboco_retangulo(body)
        self.pad = body.newObject("PartDesign::Pad", "Pad")
        self.pad.Profile = self.sk
        self.pad.Length = 10
        self.doc.recompute()

    def tearDown(self):
        FreeCADGui.Selection.clearSelection()
        fechar(self.doc)

    def _esp(self, s=0.3):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            time.sleep(0.01)

    def _selecionar(self, *objs):
        FreeCADGui.Selection.clearSelection()
        for o in objs:
            FreeCADGui.Selection.addSelection(o)
        self.P.atualizar(forcar=True)
        self._esp(0.2)
        return self.P.inspetor()

    def test_extrusao_em_cartoes(self):
        self._esp(0.6)                       # o rótulo ganha o nome em português logo depois de criar
        ins = self._selecionar(self.pad)
        self.assertIs(ins.obj, self.pad)
        for p in ("SideType", "Type", "Length", "Reversed", "Refine", "Profile"):
            self.assertIn(p, ins.campos)
        self.assertNotIn("Length2", ins.campos, "Direção 2 aparece com um lado só")
        self.assertEqual(ins.nome.text(), self.pad.Label)

    def test_medida_muda_e_desfaz(self):
        ins = self._selecionar(self.pad)
        ins.campos["Length"].setValue(25.0)
        self._esp()
        self.assertAlmostEqual(self.pad.Length.Value, 25.0, places=6)
        self.assertGreater(self.pad.Shape.Volume, 0)
        self.doc.undo()
        self.doc.recompute()
        self.assertAlmostEqual(self.pad.Length.Value, 10.0, places=6)

    def test_escolha_remonta_os_campos(self):
        ins = self._selecionar(self.pad)
        ins.campos["SideType"].definir("Two sides", silencioso=False)
        self._esp()
        self.assertEqual(self.pad.SideType, "Two sides")
        self.assertIn("Length2", self.P.inspetor().campos)
        self.P.inspetor().campos["Type"].definir("UpToLast", silencioso=False)
        self._esp()
        self.assertEqual(self.pad.Type, "UpToLast")
        self.assertNotIn("Length", self.P.inspetor().campos, "Altura continua com 'Até o fim'")

    def test_chave_liga_desliga(self):
        ins = self._selecionar(self.pad)
        antes = bool(self.pad.Reversed)
        ins.campos["Reversed"].click()
        self._esp()
        self.assertEqual(bool(self.pad.Reversed), not antes)

    def test_objeto_sem_cartao_pronto_sai_por_grupo(self):
        caixa = self.doc.addObject("Part::Box", "Caixa")
        self.doc.recompute()
        ins = self._selecionar(caixa)
        for p in ("Length", "Width", "Height"):
            self.assertIn(p, ins.campos)
        ins.campos["Height"].setValue(33.0)
        self._esp()
        self.assertAlmostEqual(caixa.Height.Value, 33.0, places=6)

    def test_sem_selecao_e_avancado(self):
        ins = self._selecionar()
        self.assertIsNone(ins.obj)
        self.assertFalse(ins.cab.isVisible())
        ins = self._selecionar(self.sk)
        if ins.avancado is not None:
            self.P.abrir_avancado()
            self._esp(0.1)
            self.assertTrue(ins.avancado.isVisible() or not ins.isVisible())
            ins.botao_avancado.setChecked(False)
            self.assertFalse(ins.avancado.isVisible())

    def test_aparencia(self):
        import PrumoInspetor as I
        self._selecionar(self.pad)
        ap = self.P.aparencia()
        ap.montar([self.pad])
        vo = self.pad.ViewObject
        ap.controles["Transparency"].setValue(40)
        self._esp(0.1)
        self.assertEqual(vo.Transparency, 40)
        modos = vo.getEnumerationsOfProperty("DisplayMode")
        alvo = "Wireframe" if "Wireframe" in modos else modos[-1]
        ap.controles["DisplayMode"].definir(alvo, silencioso=False)
        self.assertEqual(vo.DisplayMode, alvo)
        ap._pintar(__import__("PySide").QtGui.QColor("#F7BE00"))
        c = I.cor_de(vo)
        self.assertAlmostEqual(c[0], 0xF7 / 255.0, places=2)
        self.assertAlmostEqual(c[2], 0.0, places=2)

    def test_kit_visual(self):
        import PrumoUI as UI
        sw = UI.Interruptor(False)
        sw.click()
        self.assertTrue(sw.isChecked())
        seg = UI.Segmentado([("a", "A"), ("b", "B")], "b")
        self.assertEqual(seg.valor(), "b")
        n = UI.CampoNumero(12.5, "mm")
        self.assertIn("mm", n.text())
        c = UI.Cartao("Teste", "info", chave=True, ligado=False)
        c.linha("x", UI.Interruptor())
        self.assertTrue(c.corpo.isHidden())
        c.chave.click()
        self.assertFalse(c.corpo.isHidden())


class T57PainelDoEsboco(unittest.TestCase):
    """Aba do esboço: situação, relações pela seleção, lista com apagar; faixa Esboço mais enxuta."""

    def setUp(self):
        self.doc = novo_doc("PrumoTesteEsbocoPainel")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.body = self.doc.addObject("PartDesign::Body", "Body")
        self.sk = esboco_retangulo(self.body)
        self.doc.recompute()

    def tearDown(self):
        if FreeCAD.GuiUp and FreeCADGui.ActiveDocument is not None:
            try:
                FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
            FreeCADGui.Selection.clearSelection()
        fechar(self.doc)

    def _esp(self, s=0.5):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            time.sleep(0.02)

    def test_regras_das_relacoes(self):
        import PrumoPainelEsboco as E
        sel = lambda l=0, c=0, p=0: {"linhas": [0] * l, "curvas": [0] * c, "pontos": ["Vertex1"] * p}  # noqa
        self.assertEqual(E.relacoes_possiveis(sel()), set())
        duas = E.relacoes_possiveis(sel(l=2))
        self.assertTrue({"paralela", "perpendicular", "igual", "colinear"} <= duas)
        self.assertNotIn("tangente", duas)
        self.assertIn("tangente", E.relacoes_possiveis(sel(l=1, c=1)))
        self.assertIn("coincidente", E.relacoes_possiveis(sel(p=2)))
        self.assertIn("horizontal", E.relacoes_possiveis(sel(p=2)))
        self.assertNotIn("paralela", E.relacoes_possiveis(sel(c=2)))
        self.assertIn("igual", E.relacoes_possiveis(sel(c=2)))

    def test_textos(self):
        import PrumoPainelEsboco as E
        txts = [E.texto_restricao(self.sk, c) for _i, c in E.restricoes_visiveis(self.sk)]
        self.assertTrue(any(t.startswith("Coincidente · Linha 1") for t in txts), txts)
        self.assertTrue(any("mm" in t for t in txts), txts)
        self.assertEqual(E.situacao(self.sk), ("Totalmente definido", "ok"))

    def test_painel_na_edicao(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelEsboco as E
        E.instalar()
        FreeCADGui.ActiveDocument.setEdit(self.sk.Name)
        self._esp(1.0)
        p = E.painel()
        self.assertIsNotNone(p, "o painel do esboço não entrou na aba do comando")
        self.assertEqual(p.situacao.text(), "Totalmente definido")
        panel = E._painel_de_tarefas()
        quadros = E._quadros(panel)
        self.assertGreaterEqual(len(quadros), 2)
        self.assertTrue(all(not w.isVisible() for w, _a in quadros), "quadros do FreeCAD continuam abertos")
        # duas linhas: paralela ativa, tangente apagada
        FreeCADGui.Selection.addSelection(self.doc.Name, self.sk.Name, "Edge1")
        FreeCADGui.Selection.addSelection(self.doc.Name, self.sk.Name, "Edge3")
        self._esp(0.5)
        self.assertTrue(p.botoes["paralela"].isEnabled())
        self.assertFalse(p.botoes["tangente"].isEnabled())
        self.assertIn("Linha 1", p.chips.text())
        # apagar uma restrição pela lista e desfazer
        n = len(self.sk.Constraints)
        FreeCADGui.Selection.clearSelection()
        p._apagar(len(self.sk.Constraints) - 1)
        self.assertEqual(len(self.sk.Constraints), n - 1)
        self.assertNotEqual(p.situacao.text(), "Totalmente definido")
        self.doc.undo()
        self.doc.recompute()
        self.assertEqual(len(self.sk.Constraints), n)
        # lista completa do FreeCAD
        p.completa.setChecked(True)
        self._esp(0.4)
        self.assertTrue(any(w.isVisible() for w, _a in E._quadros(panel)))
        p.completa.setChecked(False)
        FreeCADGui.ActiveDocument.resetEdit()
        self._esp(0.6)
        self.assertIsNone(E.painel(), "o painel ficou depois de sair do esboço")

    def test_faixa_do_esboco_enxuta(self):
        import PrumoRibbon
        tab = [t for t in PrumoRibbon.TABS if t["id"] == "esboco"][0]
        nomes = [p[0] for p in tab["panels"]]
        self.assertNotIn("Auxiliares", nomes)
        self.assertNotIn("Restrições", nomes)
        specs = [b[0] for p in tab["panels"] for b in p[1]]
        self.assertIn("Sketcher_CompDimensionTools", specs)
        self.assertFalse(any("Sketcher_ConstrainParallel" in sp for sp in specs))
        self.assertEqual(sum("Sketcher_ToggleConstruction" in sp for sp in specs), 1)

    def test_aviso_compacto(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoGuia
        f = PrumoGuia.GuiaFrame()
        dispensou = []
        f.set_compacto(["Este esboço está preso a uma face. Se a operação mudar, perde a referência."],
                       lambda: dispensou.append(1))
        self.assertIn("Por quê?", f.alert.text())
        self.assertNotIn("perde a referência", f.alert.text())
        f._por_que("mais")
        self.assertIn("perde a referência", f.alert.text())
        f.toggle.click()
        self.assertEqual(dispensou, [1])
        f.set_content("Extrusão", None, "texto")
        self.assertTrue(f.title.isVisibleTo(f))
        f.deleteLater()


class T58TelaInicialAjuda(unittest.TestCase):
    """Tela inicial: área Ajuda logo abaixo de Novo projeto, com três cartões com ícone."""

    def test_area_ajuda(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        from PySide import QtWidgets
        import PrumoInicio
        w = PrumoInicio.InicioPrumo()
        try:
            self.assertEqual(len(w.cartoes_ajuda), 3)
            for c in w.cartoes_ajuda:
                ib = c.findChild(QtWidgets.QLabel, "SwIconBox")
                self.assertIsNotNone(ib.pixmap())
                self.assertFalse(ib.pixmap().isNull(), "cartão de ajuda sem ícone")
            secoes = [l.text() for l in w.findChildren(QtWidgets.QLabel, "SwSecao")]
            self.assertEqual(secoes[:2], ["Novo projeto", "Ajuda"])
            for nome, *_r in PrumoInicio.AJUDA:
                self.assertTrue(os.path.isfile(os.path.join(PrumoInicio.HERE, "Resources", "icons", nome)), nome)
        finally:
            w.deleteLater()


class T59PadraoVisualNosPaineis(unittest.TestCase):
    """Padrão visual em todo o sistema: chaves liga/desliga, cartões, painéis Prumo sem quadro repetido."""

    def test_estilo_global(self):
        import PrumoEstilo as E
        css = E._qss_claro()
        self.assertIn("sw_on.svg", css)
        self.assertRegex(css, r"QCheckBox::indicator \{ width: 32px; height: 18px; \}")
        self.assertIn("QAbstractItemView::indicator:checked", css)      # tabelas continuam com caixa
        self.assertNotIn("border-bottom: 2px solid #F7BE00", css.split("painel de tarefas")[-1])
        self.assertEqual(E.R_CARD, 10)
        for nome in ("sw_on.svg", "sw_off.svg", "sw_on_d.svg", "sw_off_d.svg", "sw_mid.svg"):
            self.assertIn(nome, E.UI_FILES)
            self.assertIn("<svg", E.UI_FILES[nome]())

    def test_secao_e_mensagem_no_padrao(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainel as P
        f = P.Formulario("Teste", None, "Dica do momento")
        sec = f.secao("Bloco", "info")
        self.assertEqual(sec.objectName(), "PrumoSecao")
        self.assertIn("#PrumoSecao", P.qss())
        self.assertNotIn("border-left: 3px", P.qss())
        f.deleteLater()

    def test_aviso_amarelo_aparece(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainel as P
        f = P.Formulario("Teste", None, "Dica do momento")
        f.resize(300, 120)
        f.show()
        FreeCADGui.updateGui()
        img = f.mensagem.grab().toImage()
        self.assertEqual(img.pixelColor(3, img.height() // 2).name(), "#fff8dc",
                         "a mensagem do painel ficou sem o fundo amarelo")
        f.close()
        f.deleteLater()

    def test_dialogos_em_cartoes(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        from PySide import QtWidgets
        import PrumoMassa
        import PrumoGuiaMigracao
        doc = novo_doc("PrumoTesteCartoes")
        try:
            caixa = doc.addObject("Part::Box", "Caixa")
            doc.recompute()
            d = PrumoMassa.DialogoMassa([caixa])
            self.assertGreaterEqual(len(d.findChildren(QtWidgets.QFrame, "PrumoSecao")), 2)
            d.deleteLater()
            g = PrumoGuiaMigracao.GuiaMigracao()
            self.assertGreaterEqual(len(g.findChildren(QtWidgets.QFrame, "PrumoSecao")), 2)
            g.deleteLater()
        finally:
            fechar(doc)

    def test_painel_prumo_sem_quadro_repetido(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import time
        from PySide import QtWidgets
        import PrumoFixadores
        import PrumoPainelLateral as L
        doc = novo_doc("PrumoTesteVisualPainel")
        try:
            painel = PrumoFixadores.PainelFixador()
            FreeCADGui.Control.showDialog(painel)
            t = time.time()
            while time.time() - t < 1.0:
                QtWidgets.QApplication.processEvents()
                FreeCADGui.updateGui()
                L.organizar()
                time.sleep(0.02)
            quadro = None
            w = painel.form.parentWidget()
            while w is not None and quadro is None:
                if w.property("prumo") is True:
                    quadro = w
                w = w.parentWidget()
            self.assertIsNotNone(quadro, "o quadro do FreeCAD não foi integrado ao painel Prumo")
            cab = [f for f in quadro.findChildren(QtWidgets.QFrame) if f.property("class") == "header"
                   and f.parentWidget() is quadro]
            self.assertTrue(all(not f.isVisible() for f in cab))
            if L.ligado() and L.TAREFA in L.docks():
                self.assertEqual(L.titulo_real(L.TAREFA), PrumoFixadores.PainelFixador.titulo)
        finally:
            FreeCADGui.Control.closeDialog()
            fechar(doc)


class T60Atualizacao(unittest.TestCase):
    """Atualização opcional pela página de versões: comparação, escolha, download conferido, avisos."""


    def test_instalador_abre_depois_de_fechar_com_permissao(self):
        """No Windows o instalador pede administrador: tem de ir pelo Start-Process (UAC), esperando o
        Prumo fechar; Popen direto falhava (WinError 740) e o Prumo fechava sem instalar."""
        import sys
        import PrumoAtualizar as A
        antes = sys.platform
        try:
            sys.platform = "win32"
            cmd = A.comando_instalar_depois(r"C:\Users\Ana\Downloads\Prumo3D_0.9.3-beta-installer.exe", 4321)
        finally:
            sys.platform = antes
        self.assertEqual(cmd[0], "powershell.exe")
        script = cmd[-1]
        self.assertIn("Wait-Process -Id 4321", script)
        self.assertIn("Start-Process -FilePath 'C:\\Users\\Ana\\Downloads\\Prumo3D_0.9.3-beta-installer.exe'", script)
        self.assertLess(script.index("Wait-Process"), script.index("Start-Process"))
        # aspas simples no caminho não quebram o comando
        try:
            sys.platform = "win32"
            cmd = A.comando_instalar_depois(r"C:\Users\D'Ávila\x.exe", 1)
        finally:
            sys.platform = antes
        self.assertIn("'C:\\Users\\D''Ávila\\x.exe'", cmd[-1])

    def test_desistir_de_fechar_nao_abre_instalador(self):
        import PrumoAtualizar as A
        chamadas = []
        antigo = A.janela_principal

        class Falsa:
            def __init__(self, fecha):
                self.fecha = fecha

            def close(self):
                return self.fecha
        try:
            A.janela_principal = lambda: Falsa(False)
            self.assertFalse(A.instalar_ao_fechar("/tmp/x.exe", popen=lambda *a, **k: chamadas.append(a)))
            self.assertEqual(chamadas, [])
            A.janela_principal = lambda: Falsa(True)
            self.assertTrue(A.instalar_ao_fechar("/tmp/x.exe", popen=lambda *a, **k: chamadas.append(a)))
            self.assertEqual(len(chamadas), 1)
        finally:
            A.janela_principal = antigo
    def setUp(self):
        import PrumoAtualizar as A
        self.A = A
        self.g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
        self.antes = (self.g.GetBool("VerificarAtualizacoes", True), self.g.GetFloat("UltimaVerificacao", 0.0),
                      self.g.GetString("PularVersao", ""))

    def tearDown(self):
        self.g.SetBool("VerificarAtualizacoes", self.antes[0])
        self.g.SetFloat("UltimaVerificacao", self.antes[1])
        self.g.SetString("PularVersao", self.antes[2])

    def test_comparacao_de_versoes(self):
        A = self.A
        self.assertTrue(A.mais_nova("v0.6.0-beta", "0.5.0-beta"))
        self.assertTrue(A.mais_nova("0.6.0", "0.6.0-beta"))
        self.assertTrue(A.mais_nova("1.0.0", "0.10.0"))
        self.assertTrue(A.mais_nova("0.10.0-beta", "0.9.1-beta"))
        self.assertFalse(A.mais_nova("0.5.0-beta", "0.5.0-beta"))

    def _lista(self):
        def r(tag, pre=True, draft=False):
            return {"tag_name": tag, "prerelease": pre, "draft": draft, "html_url": "https://x/" + tag,
                    "body": "## Prumo 3D\n\n### Novo\n\n- coisa nova\n\n## Downloads\n\nlixo",
                    "assets": [{"name": "Prumo3D_%s-Windows-x86_64-py311-installer.exe" % tag[1:], "size": 10,
                                "browser_download_url": "https://x/a.exe", "digest": "sha256:00"},
                               {"name": "Prumo3D_%s-Linux-x86_64-py311.AppImage" % tag[1:], "size": 20,
                                "browser_download_url": "https://x/a.AppImage", "digest": ""}]}
        return [r("v0.7.0-beta", draft=True), r("v0.6.0-beta"), r("v0.5.1", pre=False), r("v0.5.0-beta")]

    def test_escolhe_a_mais_nova(self):
        A = self.A
        info = A.escolher(self._lista())
        self.assertEqual(info["tag"], "v0.6.0-beta")           # rascunho fica de fora
        self.assertEqual(info["texto"], "0.6.0 beta")
        self.assertEqual(A.escolher(self._lista(), aceitar_beta=False)["tag"], "v0.5.1")
        self.assertTrue(A.tem_novidade(info, "0.5.0-beta"))
        self.assertFalse(A.tem_novidade(info, "0.6.0-beta"))
        self.assertTrue(A.ativo_do_sistema(info, "instalador")["nome"].endswith("-installer.exe"))
        self.assertTrue(A.ativo_do_sistema(info, "appimage")["nome"].endswith(".AppImage"))
        self.assertIsNone(A.ativo_do_sistema(info, "manual"))
        self.assertIn("coisa nova", A._resumo_notas(info["notas"]))
        self.assertNotIn("lixo", A._resumo_notas(info["notas"]))

    def test_download_conferido(self):
        import hashlib
        import tempfile
        A = self.A
        pasta = tempfile.mkdtemp()
        origem = os.path.join(pasta, "origem.bin")
        dados = os.urandom(700 * 1024)
        with open(origem, "wb") as f:
            f.write(dados)
        url = "file:///" + origem.replace("\\", "/").lstrip("/")
        dig = "sha256:" + hashlib.sha256(dados).hexdigest()
        vistos = []
        destino = os.path.join(pasta, "novo.exe")
        A.baixar(url, destino, dig, progresso=lambda f, t: vistos.append(f))
        with open(destino, "rb") as f:
            self.assertEqual(f.read(), dados)
        self.assertGreater(len(vistos), 1)
        ruim = os.path.join(pasta, "ruim.exe")
        with self.assertRaises(ValueError):
            A.baixar(url, ruim, "sha256:" + "0" * 64)
        self.assertFalse(os.path.exists(ruim) or os.path.exists(ruim + ".parte"))
        with self.assertRaises(InterruptedError):
            A.baixar(url, os.path.join(pasta, "c.exe"), cancelado=lambda: True)

    def test_verificacao_automatica_respeita_preferencias(self):
        import time
        A = self.A
        original = A.compilada
        try:
            A.compilada = lambda: True
            self.g.SetBool("VerificarAtualizacoes", True)
            self.g.SetFloat("UltimaVerificacao", time.time() - 2 * A.INTERVALO)
            self.assertTrue(A.deve_verificar_ao_abrir())
            self.g.SetFloat("UltimaVerificacao", time.time() - 60)
            self.assertFalse(A.deve_verificar_ao_abrir(), "verificou duas vezes no mesmo dia")
            self.g.SetFloat("UltimaVerificacao", 0.0)
            self.g.SetBool("VerificarAtualizacoes", False)
            self.assertFalse(A.deve_verificar_ao_abrir(), "verificou com a opção desligada")
            A.compilada = lambda: False
            self.g.SetBool("VerificarAtualizacoes", True)
            self.assertFalse(A.deve_verificar_ao_abrir(), "compilação própria não deve consultar")
        finally:
            A.compilada = original

    def test_aviso_nao_obriga(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        A = self.A
        info = A.escolher(self._lista())
        av = A.AvisoAtualizacao(info, automatico=True)
        self.assertIsNotNone(av.pular)
        self.assertEqual(av.depois.text(), "Agora não")
        self.assertEqual(av.atualizar.text(), "Atualizar agora")
        av.pular.click()
        self.assertEqual(self.g.GetString("PularVersao", ""), "v0.6.0-beta")
        self.assertIsNone(A.AvisoAtualizacao(info, automatico=False).pular)

    def _esp(self, s=0.5):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            time.sleep(0.02)

    def test_atualizar_agora_responde_sem_ninguem_guardar_o_aviso(self):
        """Como no botão do Sobre: o aviso é aberto e ninguém guarda o objeto. O clique tem de funcionar."""
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import gc
        from PySide import QtWidgets
        A = self.A
        info = A.escolher(self._lista())
        chamadas = []
        original = A.atualizar
        A.atualizar = lambda *a, **k: chamadas.append(a) or "teste"
        try:
            A.AvisoAtualizacao(info, automatico=False).mostrar()
            gc.collect()
            self._esp(0.3)
            botoes = [b for w in QtWidgets.QApplication.topLevelWidgets()
                      if isinstance(w, QtWidgets.QDialog) and w.isVisible()
                      and w.windowTitle() == "Atualização do Prumo 3D"
                      for b in w.findChildren(QtWidgets.QPushButton) if b.text() == "Atualizar agora"]
            self.assertTrue(botoes, "o aviso não ficou aberto")
            botoes[-1].click()
            self._esp(0.3)
            self.assertEqual(len(chamadas), 1, "clicar em Atualizar agora não fez nada")
        finally:
            A.atualizar = original

    def _ativo_local(self, dados, digest=None):
        import hashlib
        import tempfile
        pasta = tempfile.mkdtemp()
        origem = os.path.join(pasta, "origem.bin")
        with open(origem, "wb") as f:
            f.write(dados)
        return pasta, {"nome": "Prumo3D_teste-installer.exe", "tamanho": len(dados),
                       "url": "file:///" + origem.replace("\\", "/").lstrip("/"),
                       "digest": digest or "sha256:" + hashlib.sha256(dados).hexdigest()}

    def _esperar(self, j, s=10):
        import time
        t = time.time()
        while not j.estado["fim"] and time.time() - t < s:
            self._esp(0.1)
        self._esp(0.5)

    def test_janela_de_download_mostra_progresso_e_o_proximo_passo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        A = self.A
        pasta, ativo = self._ativo_local(os.urandom(3 * 1024 * 1024))
        j = A.JanelaDownload(ativo, os.path.join(pasta, ativo["nome"]), "instalador", "0.9.0 beta").iniciar()
        try:
            self.assertTrue(j.d.isVisible(), "a janela de progresso não apareceu")
            self._esperar(j)
            self.assertEqual(j.barra.value(), 1000)
            self.assertIn("Pronto", j.situacao.text())
            self.assertTrue(j.principal.isVisible())
            self.assertEqual(j.principal.text(), "Fechar o Prumo e instalar")
            self.assertEqual(j.secundario.text(), "Depois")
            self.assertEqual(textos_com_problema(j.d), [], "texto cortado na janela de atualização")
            self.assertTrue(os.path.exists(os.path.join(pasta, ativo["nome"])))
            j.secundario.click()
            self._esp(0.3)
            self.assertFalse(j.d.isVisible())
        finally:
            j.d.close()

    def test_janela_de_download_mostra_o_erro_e_tenta_de_novo(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        A = self.A
        pasta, ativo = self._ativo_local(os.urandom(200 * 1024), digest="sha256:" + "0" * 64)
        j = A.JanelaDownload(ativo, os.path.join(pasta, ativo["nome"]), "instalador").iniciar()
        try:
            self._esperar(j)
            self.assertIn("Não foi possível", j.situacao.text())
            self.assertIn("SHA-256", j.detalhe.text())
            self.assertEqual(j.principal.text(), "Tentar de novo")
            self.assertTrue(j.d.isVisible(), "o erro tem de aparecer na janela")
        finally:
            j.d.close()

    def test_sobre_tem_botao_e_chave(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoSobre
        d = PrumoSobre.SobreDialog("0.6.0 beta", "FreeCAD 1.1")
        try:
            self.assertEqual(d.bt_atualizar.text(), "Verificar atualizações")
            d.auto.setChecked(False)
            self.assertFalse(self.g.GetBool("VerificarAtualizacoes", True))
            d.auto.setChecked(True)
            self.assertTrue(self.g.GetBool("VerificarAtualizacoes", False))
        finally:
            d.deleteLater()

    def test_consulta_real(self):
        try:
            info = self.A.consultar(timeout=10)
        except Exception as exc:
            self.skipTest("sem acesso à página de versões: {}".format(exc))
        self.assertIsNotNone(info)
        self.assertTrue(info["tag"].startswith("v"))
        self.assertTrue(any(a["nome"].endswith("-installer.exe") for a in info["ativos"]))


class T61PaineisExtrasComoAbas(unittest.TestCase):
    """Assistentes, tutorial, guia de migração e histórico viram abas do painel lateral, com × para fechar."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelLateral as P
        if not P.ligado() or P.ARVORE not in P.docks():
            self.skipTest("painel lateral único desligado nesta sessão")
        self.P = P
        self.doc = novo_doc("PrumoTesteExtras")
        painel_lateral_montado(P)

    def tearDown(self):
        for n in self.P.EXTRAS:
            d = self.P.docks().get(n)
            if d is not None:
                d.close()
        fechar(self.doc)

    def _esp(self, s=0.6):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            self.P.organizar()
            time.sleep(0.02)

    def test_tutorial_e_assistente_viram_abas(self):
        import PrumoTutorial
        import PrumoAssistenteEstrutura
        PrumoAssistenteEstrutura.mostrar()
        PrumoTutorial.mostrar("peca")
        self._esp()
        nomes = [n for n, _t in self.P.abas()]
        self.assertIn("PrumoTutorial", nomes)
        self.assertIn("PrumoAssistenteEstrutura", nomes)
        self.assertEqual(self.P.aba_atual(), "PrumoTutorial", "o último aberto deve vir para a frente")
        d = self.P.docks()["PrumoTutorial"]
        self.assertEqual(d.titleBarWidget().objectName(), "PrumoSemTitulo")
        self.assertEqual(d.widget().objectName(), "PrumoComCabecalho")
        self.assertIsInstance(self.P.conteudo(d), PrumoTutorial.Tutorial)
        # o que os módulos chamam em dock.widget() continua chegando ao conteúdo
        self.assertEqual(d.widget().chave, "peca")
        d.widget().fechar.click()
        self._esp(0.4)
        self.assertFalse(d.isVisible())
        self.assertNotIn("PrumoTutorial", [n for n, _t in self.P.abas()])
        PrumoTutorial.mostrar("peca")
        self._esp(0.4)
        self.assertTrue(d.isVisible())
        self.assertEqual(self.P.aba_atual(), "PrumoTutorial")

    def test_assistente_continua_funcionando(self):
        import PrumoFEM
        dock = PrumoFEM.mostrar()
        self._esp(0.4)
        self.assertIn("PrumoAssistenteFEM", [n for n, _t in self.P.abas()])
        self.assertTrue(dock.isVisible())
        dock.widget().atualizar(force=True)          # chamada antiga, agora pelo cabeçalho


class T62PainelDeComando(unittest.TestCase):
    """Extrusão e Cavidade em edição: cartões no lugar do formulário do FreeCAD, e o OK grava o que se mudou."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        self.doc = novo_doc("PrumoTesteComando")
        FreeCAD.setActiveDocument(self.doc.Name)
        body = self.doc.addObject("PartDesign::Body", "Body")
        self.sk = esboco_retangulo(body)
        self.pad = body.newObject("PartDesign::Pad", "Pad")
        self.pad.Profile = self.sk
        self.pad.Length = 10
        self.doc.recompute()
        self.body = body

    def tearDown(self):
        try:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        fechar(self.doc)

    def _esp(self, s=0.6):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            time.sleep(0.02)

    def _ok(self):
        import time
        from PySide import QtWidgets
        mw = FreeCADGui.getMainWindow()
        # a Fixação pode estar escolhendo referência na vista: sai desse modo (como o usuário faria)
        try:
            import PrumoPainelComando as C
            fx = C.painel_fixacao()
            if fx is not None:
                for k, b in list(fx.campos.items()):
                    if k.startswith("ref") and "Escolhendo" in b.text():
                        b.click()
                        self._esp(0.3)
        except Exception:
            pass
        t = time.time()
        while time.time() - t < 3.0:
            for b in mw.findChildren(QtWidgets.QPushButton):
                if b.isVisible() and b.isEnabled() and b.text().replace("&", "") == "OK" and \
                        b.parentWidget() is not None and isinstance(b.parentWidget(), QtWidgets.QDialogButtonBox):
                    b.click()
                    self._esp(0.6)
                    return True
            self._esp(0.2)
        vis = [b.text() for b in mw.findChildren(QtWidgets.QPushButton) if b.isVisible()][:15]
        oks = []
        for b in mw.findChildren(QtWidgets.QPushButton):
            if b.text().replace("&", "") in ("OK", "Cancelar", "Cancel"):
                cad = []
                w = b
                while w is not None and len(cad) < 8:
                    cad.append("%s:%s%s" % (type(w).__name__, w.objectName(), "" if w.isVisibleTo(w.parentWidget() or w) else "(oculto)"))
                    w = w.parentWidget()
                oks.append("%s vis=%s en=%s geo=%s <- %s" % (b.text(), b.isVisible(), b.isEnabled(), b.geometry().getRect(), " / ".join(cad)))
        vis.append(" || ".join(oks))
        for bb in mw.findChildren(QtWidgets.QDialogButtonBox):
            vis.append("BOX vis=%s: %s" % (bb.isVisible(), [type(x).__name__ for x in bb.buttons()]))
        modais = [w.windowTitle() for w in QtWidgets.QApplication.topLevelWidgets()
                  if isinstance(w, QtWidgets.QDialog) and w.isVisible()]
        raise AssertionError("botão OK não encontrado; diálogo de tarefa=%s; botões visíveis=%s; janelas=%s"
                             % (FreeCADGui.Control.activeDialog(), vis, modais))

    def test_extrusao_em_cartoes_e_ok_grava(self):
        FreeCADGui.ActiveDocument.setEdit(self.pad.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertIsNotNone(p, "o painel de comando não apareceu")
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD continua aberto")
        for k in ("lados", "modo1", "comp1", "inverter", "refinar"):
            self.assertIn(k, p.campos)
        p.campos["comp1"].setValue(27.5)
        self._esp(0.3)
        self.assertAlmostEqual(p.f.numero("lengthEdit"), 27.5, places=6)
        self.assertTrue(self._ok(), "botão OK não encontrado")
        self.assertFalse(FreeCADGui.Control.activeDialog())
        self.assertAlmostEqual(self.pad.Length.Value, 27.5, places=6)
        self.assertIsNone(self.C.painel())

    def test_modo_com_escolha_mostra_o_formulario(self):
        FreeCADGui.ActiveDocument.setEdit(self.pad.Name)
        self._esp(1.2)
        p = self.C.painel()
        p.campos["lados"].definir("two", silencioso=False)
        self._esp(0.8)
        p = self.C.painel()
        self.assertIn("comp2", p.campos)
        p.campos["modo1"].definir("UpToFace", silencioso=False)
        self._esp(0.8)
        p = self.C.painel()
        self.assertTrue(p.quadro.isVisible(), "modo 'Até a face' precisa do quadro do FreeCAD para escolher")
        self.assertNotIn("comp1", p.campos)
        p.campos["modo1"].definir("Length", silencioso=False)
        self._esp(0.8)
        self.assertFalse(self.C.painel().quadro.isVisible())

    def _furo(self):
        import Part
        s2 = self.body.newObject("Sketcher::SketchObject", "Furos")
        s2.AttachmentSupport = [(self.body.Origin.OriginFeatures[3], "")]
        s2.MapMode = "FlatFace"
        s2.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(0, 0, 10), FreeCAD.Rotation())
        s2.addGeometry(Part.Circle(FreeCAD.Vector(20, 10, 0), FreeCAD.Vector(0, 0, 1), 3))
        h = self.body.newObject("PartDesign::Hole", "Hole")
        h.Profile = s2
        self.doc.recompute()
        return h

    def test_furo_em_cartoes(self):
        h = self._furo()
        FreeCADGui.ActiveDocument.setEdit(h.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelFuro")
        self.assertFalse(p.quadro.isVisible())
        self.assertLess(p.minimumSizeHint().width(), 300, "o painel do furo pede largura demais")
        self.assertNotIn("tamanho", p.campos)                 # sem rosca: diâmetro livre
        p.campos["rosca"].setCurrentIndex(1)
        p.campos["rosca"].activated.emit(1)
        self._esp(0.8)
        p = self.C.painel()
        self.assertIn("tamanho", p.campos)
        self.assertIn("tipo", p.campos)
        p.campos["cabeca"].setCurrentIndex(1)
        p.campos["cabeca"].activated.emit(1)
        self._esp(0.8)
        p = self.C.painel()
        self.assertIn("cab_d", p.campos)
        p.campos["prof"].setValue(7.5)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(h.Depth.Value, 7.5, places=6)
        self.assertNotEqual(h.ThreadType, "None")
        self.assertNotEqual(h.HoleCutType, "None")

    def test_revolucao_e_arredondar(self):
        r = self.body.newObject("PartDesign::Revolution", "Revolution")
        sk2 = esboco_retangulo(self.body, 10, 5)
        r.Profile = sk2
        r.ReferenceAxis = (sk2, ["V_Axis"])
        r.Angle = 360
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(r.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelRevolucao")
        self.assertFalse(p.quadro.isVisible())
        p.campos["a1"].setValue(90.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(r.Angle.Value, 90.0, places=6)
        f = self.body.newObject("PartDesign::Fillet", "Fillet")
        f.Base = (r, ["Edge1"])
        f.Radius = 1
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(f.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelAcabamentoArestas")
        self.assertIn("escolher", p.campos)
        p.campos["escolher"].click()
        self._esp(0.4)
        self.assertTrue(self.C.painel().f.w("buttonRefSel", __import__("PySide").QtWidgets.QToolButton).isChecked())
        self.assertIn("Clique nas arestas", self.C.painel().dica.text())
        self.C.painel().campos["escolher"].click()
        self._esp(0.4)
        self.C.painel().campos["raio"].setValue(0.5)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(f.Radius.Value, 0.5, places=6)

    def test_chanfro_tipos(self):
        c = self.body.newObject("PartDesign::Chamfer", "Chamfer")
        c.Base = (self.pad, ["Edge1"])
        c.Size = 1
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(c.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertIn("tipo", p.campos)
        self.assertNotIn("d2", p.campos)
        p.campos["tipo"].definir("1", silencioso=False)
        self._esp(0.8)
        p = self.C.painel()
        self.assertIn("d2", p.campos)
        self.assertIn("flip", p.campos)
        p.campos["d2"].setValue(2.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertEqual(c.ChamferType, "Two distances")
        self.assertAlmostEqual(c.Size2.Value, 2.0, places=6)

    def test_padroes_e_espelhar(self):
        lp = self.body.newObject("PartDesign::LinearPattern", "LinearPattern")
        lp.Originals = [self.pad]
        lp.Direction = (self.sk, ["H_Axis"])
        lp.Length = 100
        lp.Occurrences = 2
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(lp.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelPadrao")
        self.assertFalse(p.quadro.isVisible())
        self.assertIn("d0_n", p.campos)
        self.assertEqual(len(p.estado()["ops"]), 1, "a operação a repetir não aparece no cartão")
        p.campos["d0_n"].setValue(4)
        self._esp(0.3)
        p.campos["d0_ext"].setValue(120.0)
        self._esp(0.4)
        self.assertTrue(self._ok())
        self.assertEqual(lp.Occurrences, 4)
        self.assertAlmostEqual(lp.Length.Value, 120.0, places=6)
        pp = self.body.newObject("PartDesign::PolarPattern", "PolarPattern")
        pp.Originals = [self.pad]
        pp.Axis = (self.sk, ["V_Axis"])
        pp.Occurrences = 3
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(pp.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelPadrao")
        p.campos["d0_n"].setValue(6)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertEqual(pp.Occurrences, 6)
        mi = self.body.newObject("PartDesign::Mirrored", "Mirrored")
        mi.Originals = [self.pad]
        mi.MirrorPlane = (self.sk, ["V_Axis"])
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(mi.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertIn("plano", p.campos)
        self.assertTrue(self._ok())

    def test_cavidade_tem_atraves(self):
        caixa = self.body.newObject("PartDesign::Pocket", "Pocket")
        sk2 = esboco_retangulo(self.body, 10, 5)
        caixa.Profile = sk2
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(caixa.Name)
        self._esp(1.2)
        p = self.C.painel()
        self.assertIsNotNone(p)
        self.assertIn("ThroughAll", p.campos["modo1"].botoes)
        self.assertEqual(p.nome_medida, "Profundidade")


class T63FerramentasDePontaAPonta(unittest.TestCase):
    """Toda ferramenta da faixa abre e fecha sem erro de Python, e o esboço aguenta as ferramentas e conflitos.

    Cada comando roda com uma peça pronta e selecionada (corpo, esboço, extrusão); janelas que se abrem são
    fechadas, painéis cancelados. Falha se aparecer 'Traceback' no relatório ou se o documento quebrar.
    """

    NAO_RODAR = {"Prumo_AplicarTema", "Prumo_TemaEscuro", "Prumo_TemaIcones", "Prumo_Testes",
                 "Prumo_RemoverSplash", "Prumo_ModoDistribuicao", "Prumo_BarrasClassicas", "Std_Print",
                 "Std_PrintPdf", "Std_DlgPreferences", "Std_DlgMacroExecute", "Std_Open", "Std_Import",
                 "Std_Export", "Std_SaveAs", "Std_Save", "Prumo_ChapaDXF", "Std_New", "Prumo_Inicio"}

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        from PySide import QtCore
        self.timer = QtCore.QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._fechar_janelas)
        self.timer.start()

    def tearDown(self):
        self.timer.stop()
        self._limpar_tela()

    # ---------------------------------------------------------------- ajudantes
    @staticmethod
    def _erros_do_prumo(texto):
        """Tracebacks que passam pelo código do Prumo. (Ferramentas do próprio FreeCAD avisam por Traceback
        quando a seleção não serve, ex.: booleana com um sólido só; isso não é defeito do Prumo.)"""
        out = []
        partes = texto.split("Traceback (most recent call last):")[1:]
        for p in partes:
            bloco = p[:1500]
            if "Prumo3D" in bloco or "Prumo" in bloco.split("<class")[0]:
                out.append(bloco[:400].replace("\n", " | "))
        return out

    def _relatorio(self):
        from PySide import QtWidgets
        mw = FreeCADGui.getMainWindow()
        for d in mw.findChildren(QtWidgets.QDockWidget):
            if d.objectName() == "Report view":
                t = d.findChild(QtWidgets.QTextEdit)
                if t is not None:
                    return t.toPlainText()
        return ""

    def _fechar_janelas(self):
        from PySide import QtWidgets
        w = QtWidgets.QApplication.activeModalWidget()
        alvos = [w] if w is not None else []
        # diálogos abertos com show() antes de exec_() nem sempre viram o "modal ativo"
        alvos += [d for d in QtWidgets.QApplication.topLevelWidgets()
                  if isinstance(d, QtWidgets.QDialog) and d.isVisible() and d.isModal() and d is not w]
        for d in alvos:
            try:
                d.reject() if hasattr(d, "reject") else d.close()
            except Exception:
                pass

    def _limpar_tela(self):
        from PySide import QtWidgets
        mw = FreeCADGui.getMainWindow()
        for _ in range(3):
            self._fechar_janelas()
            try:
                if FreeCADGui.Control.activeDialog():
                    FreeCADGui.Control.closeDialog()
            except Exception:
                pass
            try:
                if FreeCADGui.ActiveDocument is not None and FreeCADGui.ActiveDocument.getInEdit() is not None:
                    FreeCADGui.ActiveDocument.resetEdit()
            except Exception:
                pass
            for w in QtWidgets.QApplication.topLevelWidgets():
                if isinstance(w, QtWidgets.QDialog) and w.isVisible() and w is not mw:
                    w.close()
            self._esp(0.1)

    def _esp(self, s=0.3):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            FreeCADGui.updateGui()
            time.sleep(0.01)

    def _cena(self, nome):
        doc = novo_doc(nome)
        FreeCAD.setActiveDocument(doc.Name)
        body = doc.addObject("PartDesign::Body", "Body")
        sk = esboco_retangulo(body)
        pad = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 10
        doc.recompute()
        return doc, body, sk, pad

    @staticmethod
    def _vivo(obj):
        try:
            return obj.Name is not None and obj.Document is not None and obj.isValid()
        except Exception:
            return False

    @staticmethod
    def _comandos_da_aba(tab):
        nomes = []
        for _painel, botoes in tab["panels"]:
            for b in botoes:
                for c in str(b[0]).split("|"):
                    if c and c not in nomes:
                        nomes.append(c)
        return nomes

    # ---------------------------------------------------------------- testes
    def test_cada_ferramenta_da_faixa_abre_e_fecha(self):
        import PrumoRibbon
        erros, rodados = [], 0
        doc = None
        for tab in PrumoRibbon.TABS:
            wb = tab.get("wb")
            for extra in (tab.get("wb_extra") or []) + ([wb] if wb else []):
                try:
                    FreeCADGui.activateWorkbench(extra)
                except Exception:
                    pass
            self._esp(0.2)
            if doc is not None and doc.Name in FreeCAD.listDocuments():
                fechar(doc)
            doc = None
            for d in list(FreeCAD.listDocuments().values()):
                if d.Name.startswith(("Sem", "Unnamed")):
                    fechar(d)
            # janelas de folha (TechDraw) de documento fechado só somem no próximo ciclo da interface;
            # selecionar antes disso derruba o FreeCAD (observador de seleção já apagado)
            self._esp(0.8)
            for cmd in self._comandos_da_aba(tab):
                if cmd in self.NAO_RODAR or cmd not in FreeCADGui.listCommands():
                    continue
                if doc is None or doc.Name not in FreeCAD.listDocuments() or not self._vivo(pad):
                    if doc is not None and doc.Name in FreeCAD.listDocuments():
                        fechar(doc)
                        self._esp(0.8)
                    doc, body, sk, pad = self._cena("PrumoTesteFaixa")
                antes = self._relatorio()
                try:
                    with open(os.path.join(FreeCAD.getUserAppDataDir(), "teste_faixa.log"), "a") as lg:
                        lg.write(cmd + "\n")
                except OSError:
                    pass
                try:
                    FreeCADGui.Selection.clearSelection()
                    FreeCADGui.Selection.addSelection(pad)
                    FreeCADGui.runCommand(cmd, 0)
                    self._esp(0.25)
                except Exception as exc:
                    erros.append("%s: %s" % (cmd, exc))
                self._limpar_tela()
                novo = self._relatorio()[len(antes):]
                for trecho in self._erros_do_prumo(novo):
                    erros.append("%s: %s" % (cmd, trecho))
                rodados += 1
                if doc.Name not in FreeCAD.listDocuments():
                    doc = None
        for d in list(FreeCAD.listDocuments().values()):
            if d.Name.startswith("PrumoTesteFaixa") or d.Name.startswith("Sem") or d.Name.startswith("Unnamed"):
                fechar(d)
        self.assertGreater(rodados, 150, "poucos comandos rodaram: %d" % rodados)
        self.assertEqual(erros, [], "ferramentas com erro:\n" + "\n".join(erros))

    def test_ferramentas_do_esboco_ligam_e_cancelam(self):
        from PySide import QtCore, QtGui, QtWidgets
        import PrumoRibbon
        doc, body, sk, pad = self._cena("PrumoTesteFerramentasEsboco")
        try:
            FreeCADGui.activateWorkbench("SketcherWorkbench")
            FreeCADGui.ActiveDocument.setEdit(sk.Name)
            self._esp(0.8)
            tab = [t for t in PrumoRibbon.TABS if t["id"] == "esboco"][0]
            erros = []
            for cmd in self._comandos_da_aba(tab):
                if cmd not in FreeCADGui.listCommands():
                    continue          # comando só da compilação completa (ex.: linha de construção, em C++)
                if not cmd.startswith("Sketcher_") or cmd in ("Sketcher_LeaveSketch", "Sketcher_NewSketch",
                                                              "Sketcher_EditSketch", "Sketcher_MapSketch",
                                                              "Sketcher_ValidateSketch", "Sketcher_MergeSketches",
                                                              "Sketcher_MirrorSketch", "Sketcher_ReorientSketch"):
                    continue
                if FreeCADGui.ActiveDocument.getInEdit() is None:
                    FreeCADGui.ActiveDocument.setEdit(sk.Name)
                    self._esp(0.5)
                antes = self._relatorio()
                try:
                    FreeCADGui.runCommand(cmd, 0)
                    self._esp(0.2)
                    vista = FreeCADGui.ActiveDocument.ActiveView.graphicsView()
                    for tipo in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                        QtWidgets.QApplication.sendEvent(
                            vista, QtGui.QKeyEvent(tipo, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier))
                    self._esp(0.15)
                except Exception as exc:
                    erros.append("%s: %s" % (cmd, exc))
                self._fechar_janelas()
                novo = self._relatorio()[len(antes):]
                for trecho in self._erros_do_prumo(novo):
                    erros.append("%s: %s" % (cmd, trecho))
            self.assertEqual(erros, [], "\n".join(erros))
        finally:
            self._limpar_tela()
            fechar(doc)

    def _painel_do_esboco(self, E, limite=3.0):
        """O painel do esboço pode estar sendo remontado (ex.: logo depois de retirar restrições): espera."""
        import time
        t = time.time()
        p = E.painel()
        while p is None and time.time() - t < limite:
            self._esp(0.2)
            p = E.painel()
        self.assertIsNotNone(p, "o painel do esboço não voltou; em edição: %s" % FreeCADGui.ActiveDocument.getInEdit())
        return p

    def _circulos_e_linha(self, nome):
        """Esboço em edição com dois círculos de raio e posição fixos (o painel já viu o esboço fechado)."""
        import Part
        import Sketcher
        import PrumoPainelEsboco as E
        E.instalar()
        doc, body, sk, pad = self._cena(nome)
        s2 = body.newObject("Sketcher::SketchObject", "Circulos")
        s2.AttachmentSupport = [(body.Origin.OriginFeatures[3], "")]
        s2.MapMode = "FlatFace"
        doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(s2.Name)
        self._esp(0.8)
        V = FreeCAD.Vector
        s2.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10))
        s2.addConstraint(Sketcher.Constraint("Coincident", 0, 3, -1, 1))
        s2.addConstraint(Sketcher.Constraint("Radius", 0, 10))
        s2.addGeometry(Part.Circle(V(60, 0, 0), V(0, 0, 1), 5))
        s2.addConstraint(Sketcher.Constraint("PointOnObject", 1, 3, -1))
        s2.addConstraint(Sketcher.Constraint("Radius", 1, 5))
        s2.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 1, 3, 60))
        doc.recompute()
        self._esp(0.8)
        return doc, s2

    def test_linha_com_relacoes_automaticas_que_nao_cabem(self):
        """Como desenhar uma linha de um círculo ao outro: as restrições automáticas (tangente nos dois e
        horizontal) não fecham. O painel retira as automáticas que sobram e o esboço continua resolvido."""
        import Part
        import Sketcher
        import PrumoPainelEsboco as E
        doc, s2 = self._circulos_e_linha("PrumoTesteConflitoAuto")
        try:
            n0 = len(s2.Constraints)
            self.assertEqual(E.resolve(s2), 0)
            doc.openTransaction("Linha")
            g = s2.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 10, 0), FreeCAD.Vector(60, 5, 0)))
            s2.addConstraint([Sketcher.Constraint("Tangent", g, 1, 0), Sketcher.Constraint("Tangent", g, 2, 1),
                              Sketcher.Constraint("Horizontal", g)])
            doc.commitTransaction()
            self.assertNotEqual(E.resolve(s2), 0, "a cena devia nascer em conflito")
            self._esp(1.0)
            p = self._painel_do_esboco(E)
            self.assertEqual(E.resolve(s2), 0, "o esboço ficou sem solução")
            self.assertEqual(E.problemas(s2), set())
            self.assertGreaterEqual(len(s2.Constraints), n0, "apagou restrição antiga")
            self.assertLess(len(s2.Constraints), n0 + 3, "não retirou nenhuma automática")
            texto = p.situacao.text().lower()
            self.assertIn("retirada", texto)
            self.assertNotIn("conflito", texto)
            self.assertIsNotNone(FreeCADGui.ActiveDocument.getInEdit(), "o esboço saiu da edição")
        finally:
            self._limpar_tela()
            fechar(doc)

    def test_duas_verticais_automaticas_nao_jogam_os_circulos_longe(self):
        """Caso relatado na 0.8.1: círculos de Ø50 e Ø30 com o centro só no eixo X; a linha de um ao outro
        pega tangente + duas "Vertical" (alinhamento com os centros). O recálculo do FreeCAD com o conflito
        jogava os círculos a bilhões de mm; o Prumo tem de voltar ao desenho e retirar o que menos mexe."""
        import Part
        import Sketcher
        import PrumoPainelEsboco as E
        E.instalar()
        doc, body, sk, pad = self._cena("PrumoTesteDuasVerticais")
        try:
            s2 = body.newObject("Sketcher::SketchObject", "Circulos")
            s2.AttachmentSupport = [(body.Origin.OriginFeatures[3], "")]
            s2.MapMode = "FlatFace"
            doc.recompute()
            FreeCADGui.ActiveDocument.setEdit(s2.Name)
            self._esp(0.8)
            V, Z = FreeCAD.Vector, FreeCAD.Vector(0, 0, 1)
            s2.addGeometry(Part.Circle(V(0, 0, 0), Z, 25))
            s2.addConstraint(Sketcher.Constraint("Diameter", 0, 50))
            s2.addConstraint(Sketcher.Constraint("PointOnObject", 0, 3, -1))
            s2.addGeometry(Part.Circle(V(100, 0, 0), Z, 15))
            s2.addConstraint(Sketcher.Constraint("PointOnObject", 1, 3, -1))
            s2.addConstraint(Sketcher.Constraint("Diameter", 1, 30))
            doc.recompute()
            self._esp(0.8)
            doc.openTransaction("Linha")
            g = s2.addGeometry(Part.LineSegment(V(0, 25, 0), V(100, 15, 0)))
            s2.addConstraint([Sketcher.Constraint("Tangent", g, 1, 0), Sketcher.Constraint("Vertical", g, 1, 0, 3),
                              Sketcher.Constraint("PointOnObject", g, 2, 1), Sketcher.Constraint("Vertical", g, 2, 1, 3)])
            doc.commitTransaction()
            doc.recompute()                        # aqui o FreeCAD joga os círculos longe
            self._esp(1.5)
            self._painel_do_esboco(E)
            self.assertEqual(E.resolve(s2), 0, "o esboço ficou sem solução")
            c1, c2 = s2.getPoint(0, 3), s2.getPoint(1, 3)
            self.assertLess(c1.Length, 5.0, "círculo 1 foi parar em %s" % c1)
            self.assertLess((c2 - V(100, 0, 0)).Length, 5.0, "círculo 2 foi parar em %s" % c2)
            tipos = [c.Type for c in s2.Constraints]
            self.assertIn("Tangent", tipos, "a tangente (a intenção do desenho) devia ficar")
            self.assertEqual(len(s2.Constraints), 7, "devia sair só uma restrição automática")
        finally:
            self._limpar_tela()
            fechar(doc)

    def test_conflito_posto_a_mao_aparece_e_se_resolve(self):
        """Restrição posta pelo usuário (sem geometria nova) que entra em conflito: o painel avisa e o botão
        apaga a mais recente; nada é retirado sozinho."""
        import Part
        import Sketcher
        import PrumoPainelEsboco as E
        doc, s2 = self._circulos_e_linha("PrumoTesteConflito")
        try:
            g = s2.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 10, 0), FreeCAD.Vector(60, 5, 0)))
            s2.addConstraint(Sketcher.Constraint("Tangent", g, 1, 0))
            s2.addConstraint(Sketcher.Constraint("Tangent", g, 2, 1))
            doc.recompute()
            self._esp(0.8)
            self.assertEqual(E.resolve(s2), 0)
            n = len(s2.Constraints)
            s2.addConstraint(Sketcher.Constraint("Horizontal", g))
            self._esp(0.8)
            p = self._painel_do_esboco(E)
            self.assertEqual(len(s2.Constraints), n + 1, "a restrição do usuário não pode sumir sozinha")
            texto = p.situacao.text().lower()
            self.assertTrue("conflito" in texto or "não fecha" in texto, "situação não avisou: " + texto)
            self.assertNotIn("totalmente definido", texto)
            self.assertTrue(p.resolver.isVisible())
            p.resolver.click()
            self._esp(0.6)
            self.assertEqual(len(s2.Constraints), n)
            self.assertEqual(E.problemas(s2), set(), "o conflito continuou depois de apagar a mais recente")
            self.assertEqual(E.resolve(s2), 0, "o esboço continuou sem solução")
            self.assertIsNotNone(FreeCADGui.ActiveDocument.getInEdit(), "o esboço saiu da edição")
        finally:
            self._limpar_tela()
            fechar(doc)


def textos_com_problema(raiz):
    """Rótulos visíveis com texto cortado (quebra de linha sem altura) ou sobrepostos a outro rótulo."""
    from PySide import QtCore, QtWidgets
    # o painel pode ter acabado de ser remontado: deixa o Qt posicionar tudo antes de medir
    for _ in range(3):
        if raiz.layout() is not None:
            raiz.layout().activate()
        QtWidgets.QApplication.processEvents()
    out = []
    labs = [l for l in raiz.findChildren(QtWidgets.QLabel)
            if l.isVisible() and l.text().strip() and l.width() > 0 and l.height() > 0]
    for l in labs:
        if l.wordWrap() and l.hasHeightForWidth():
            precisa = l.heightForWidth(l.width())
            if precisa > l.height() + 3:
                out.append("cortado (%d de %d px): %r" % (l.height(), precisa, l.text()[:60]))
    rets = [(l, QtCore.QRect(l.mapTo(raiz, QtCore.QPoint(0, 0)), l.size())) for l in labs]
    for i, (a, ra) in enumerate(rets):
        for b, rb in rets[i + 1:]:
            if a.isAncestorOf(b) or b.isAncestorOf(a):
                continue
            r = ra.intersected(rb)
            if r.width() > 4 and r.height() > 4:
                out.append("sobreposto: %r x %r" % (a.text()[:40], b.text()[:40]))
    return out


def operacao_em_edicao(tipo, nome_doc="PrumoTesteOperacao"):
    """Documento com a operação de Peça 'tipo' já criada e aberta para edição (painel de tarefas do FreeCAD).
    Devolve (doc, obj). Tipos: Draft, Thickness, AdditiveHelix, SubtractiveHelix, AdditiveLoft, SubtractiveLoft,
    AdditivePipe, SubtractivePipe."""
    import Part
    doc = novo_doc(nome_doc)
    FreeCAD.setActiveDocument(doc.Name)
    body = doc.addObject("PartDesign::Body", "Body")
    planos = {o.Role: o for o in body.Origin.OriginFeatures}
    if tipo in ("Draft", "Thickness", "Boolean") or tipo.startswith("Subtractive"):
        sk = esboco_retangulo(body)
        pad = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 20
        doc.recompute()
    if tipo == "Draft":
        obj = body.newObject("PartDesign::Draft", "Draft")
        obj.Base = (pad, ["Face1"])
        obj.Angle = 2
    elif tipo == "Thickness":
        obj = body.newObject("PartDesign::Thickness", "Thickness")
        obj.Base = (pad, ["Face6"])
        obj.Value = 1
    elif tipo.endswith("Helix"):
        perfil = esboco_retangulo(body, 2.0, 2.0, "Perfil", suporte=(planos["XZ_Plane"], [""]))
        perfil.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(12, 0, 0), FreeCAD.Rotation())
        obj = body.newObject("PartDesign::" + tipo, "Helice")
        obj.Profile = perfil
        obj.ReferenceAxis = (perfil, ["V_Axis"])
        obj.Pitch = 6
        obj.Height = 18
    elif tipo.endswith("Loft"):
        a = esboco_retangulo(body, 10.0, 10.0, "SecaoA")
        b = esboco_retangulo(body, 6.0, 6.0, "SecaoB")
        b.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(2, 2, 15), FreeCAD.Rotation())
        obj = body.newObject("PartDesign::" + tipo, "Loft")
        obj.Profile = a
        obj.Sections = [b]
    elif tipo.endswith("Pipe"):
        perfil = esboco_retangulo(body, 6.0, 6.0, "Perfil")
        cam = body.newObject("Sketcher::SketchObject", "Caminho")
        cam.AttachmentSupport = (planos["XZ_Plane"], [""])
        cam.MapMode = "FlatFace"
        cam.addGeometry(Part.LineSegment(FreeCAD.Vector(3, 0, 0), FreeCAD.Vector(3, 25, 0)))
        obj = body.newObject("PartDesign::" + tipo, "Varredura")
        obj.Profile = perfil
        obj.Spine = (cam, ["Edge1"])
    elif tipo == "Boolean":
        outro = doc.addObject("PartDesign::Body", "Outro")
        sk2 = esboco_retangulo(outro, 10.0, 10.0, "Sketch2")
        p2 = outro.newObject("PartDesign::Pad", "Pad2")
        p2.Profile = sk2
        p2.Length = 30
        doc.recompute()
        obj = body.newObject("PartDesign::Boolean", "Boolean")
        obj.addObject(outro)
        obj.Type = "Cut"
    elif tipo.startswith(("Additive", "Subtractive")):
        obj = body.newObject("PartDesign::" + tipo, "Primitiva")
    else:
        raise ValueError(tipo)
    doc.recompute()
    FreeCADGui.ActiveDocument.setEdit(obj, 0)
    return doc, obj


class T64TextosNasTelas(unittest.TestCase):
    """Nenhum texto cortado ou sobreposto nos painéis do Prumo e nos assistentes."""

    # mesmos ajudantes do T63: fecha janelas modais sozinho e limpa a tela entre comandos
    setUp = T63FerramentasDePontaAPonta.setUp
    tearDown = T63FerramentasDePontaAPonta.tearDown
    _fechar_janelas = T63FerramentasDePontaAPonta._fechar_janelas
    _limpar_tela = T63FerramentasDePontaAPonta._limpar_tela

    def _esp(self, s=0.5):
        import time
        from PySide import QtWidgets
        t = time.time()
        while time.time() - t < s:
            QtWidgets.QApplication.processEvents()
            time.sleep(0.01)

    def test_etapa_com_resumo_longo_cresce(self):
        from PySide import QtWidgets
        import PrumoFEM as F
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        e = F.Etapa(1, "r", "Resultados",
                    "Taxa máxima 0,68 · grande deslocabilidade: análise insuficiente, enrijeça a estrutura")
        lay.addWidget(e)
        lay.addStretch(1)
        w.resize(300, 300)
        w.show()
        try:
            self._esp(0.3)
            self.assertEqual(textos_com_problema(w), [])
            abertas = []
            e.abrir.connect(abertas.append)
            e.cab.click()
            self.assertEqual(abertas, [e], "clicar no cabeçalho abre a etapa")
        finally:
            w.close()

    def test_paineis_do_prumo_sem_texto_cortado(self):
        from PySide import QtWidgets
        import PrumoRibbon
        T63 = T63FerramentasDePontaAPonta
        problemas, abertos, vistos = [], 0, set()
        mw = FreeCADGui.getMainWindow()
        for tab in PrumoRibbon.TABS:
            if tab.get("wb"):
                try:
                    FreeCADGui.activateWorkbench(tab["wb"])
                except Exception:
                    pass
            doc, body, sk, pad = T63._cena(self, "PrumoTesteTextos")
            try:
                for cmd in T63._comandos_da_aba(tab):
                    if not cmd.startswith("Prumo") or cmd in vistos or cmd in T63.NAO_RODAR:
                        continue
                    if cmd not in FreeCADGui.listCommands() or not T63._vivo(pad):
                        continue
                    vistos.add(cmd)
                    FreeCADGui.Selection.clearSelection()
                    FreeCADGui.Selection.addSelection(pad)
                    try:
                        FreeCADGui.runCommand(cmd, 0)
                    except Exception:
                        continue
                    self._esp(0.6)
                    alvos = [w for w in mw.findChildren(QtWidgets.QWidget)
                             if w.metaObject().className() == "Gui::TaskView::TaskView" and w.isVisible()]
                    alvos += [d.widget() for d in mw.findChildren(QtWidgets.QDockWidget)
                              if d.objectName().startswith("PrumoAssistente") and d.isVisible()]
                    for a in alvos:
                        abertos += 1
                        problemas += ["%s: %s" % (cmd, p) for p in textos_com_problema(a)]
                    self._limpar_tela()
                    for d in mw.findChildren(QtWidgets.QDockWidget):
                        if d.objectName().startswith("PrumoAssistente"):
                            d.close()
            finally:
                fechar(doc)
                self._esp(0.8)
        self.assertGreater(abertos, 10, "poucos painéis abriram: %d" % abertos)
        self.assertEqual(problemas, [], "\n".join(problemas))

    def test_assistente_de_estruturas_com_resultado(self):
        import json
        import PrumoEstrutura as E, PrumoAnaliseEstrutura as A, PrumoAssistenteEstrutura as AE
        doc = novo_doc("PrumoTesteTextosEst")
        dock = None
        try:
            sk = esboco_linhas(doc, [((0, 0), (0, 4000)), ((0, 4000), (6000, 4000)), ((6000, 4000), (6000, 0))], "XZ")
            est = E.criar(doc, sk, "W 200 x 22,5", material="ASTM A36")
            doc.recompute()
            an = A.criar(doc, est)
            an.Apoios = ["%s=Engaste" % A._chave_no((0, 0, 0)), "%s=Engaste" % A._chave_no((6000, 0, 0))]
            casos = [A.caso_padrao(), {"nome": "Sobrecarga", "tipo": "Sobrecarga (sem predominância de equipamentos)",
                     "cargas": [{"alvo": "barra", "linha": 1, "tipo": "distribuida", "valor": 4.0,
                                 "direcao": "Para baixo (−Z)"}]}]
            an.Casos = [json.dumps(c, ensure_ascii=False) for c in casos]
            doc.recompute()
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(est)
            dock = AE.mostrar()
            w = dock.widget()
            w.calcular()
            for etapa in ("resultado", "cargas"):
                w.abrir_etapa(etapa)
                self._esp(0.4)
                self.assertEqual(textos_com_problema(w), [], "etapa %s" % etapa)
        finally:
            if dock is not None:
                dock.close()
            fechar(doc)


class T65MaisPaineisDeComando(unittest.TestCase):
    """Ângulo de saída, Casca, Hélice, Loft e Varredura em cartões; o OK grava o que se mudou no cartão."""


    def test_widgets_do_layout_em_ordem_sem_itens(self):
        from PySide import QtWidgets
        import PrumoUI
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        a, b, c = QtWidgets.QLabel("a"), QtWidgets.QLabel("b"), QtWidgets.QLabel("c")
        lay.addWidget(a)
        lay.addStretch(1)
        lay.addWidget(b)
        lay.insertWidget(0, c)
        solto = QtWidgets.QLabel("fora", w)   # filho que não está no layout
        par = PrumoUI.widgets_do_layout(lay)
        self.assertEqual([x.text() for _i, x in par], ["c", "a", "b"])
        self.assertEqual([i for i, _x in par], [0, 1, 3])
        self.assertNotIn(solto, [x for _i, x in par])
        w.deleteLater()
    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        self.doc = None

    def tearDown(self):
        try:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        if self.doc is not None:
            fechar(self.doc)

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok

    def _abrir(self, tipo, classe):
        self.doc, obj = operacao_em_edicao(tipo, "PrumoTesteMaisComandos")
        self._esp(1.2)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % tipo)
        self.assertEqual(type(p).__name__, classe)
        self.assertEqual(textos_com_problema(p), [], tipo)
        self.assertFalse(p.quadro.isVisible(), "%s: o formulário do FreeCAD devia ficar escondido" % tipo)
        import re
        from PySide import QtWidgets
        internos = [l.text() for l in p.findChildren(QtWidgets.QLabel) if re.match(r"^[a-z]+[A-Z]\w*$", l.text())]
        self.assertEqual(internos, [], "%s: rótulo com nome interno do FreeCAD" % tipo)
        return obj, p

    def test_angulo_de_saida(self):
        obj, p = self._abrir("Draft", "PainelAngulo")
        self.assertIn("faces", p.campos)
        p.campos["ang"].setValue(3.0)
        p.campos["ang"].editingFinished.emit()
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(obj.Angle.getValueAs("deg").Value, 3.0, places=3)

    def test_casca(self):
        obj, p = self._abrir("Thickness", "PainelCasca")
        p.campos["esp"].setValue(2.0)
        p.campos["esp"].editingFinished.emit()
        p.campos["junta"].definir("1", silencioso=False)
        self._esp(0.5)
        p = self.C.painel()
        self.assertTrue(self._ok())
        self.assertAlmostEqual(obj.Value.Value, 2.0, places=3)
        self.assertEqual(obj.Join, "Intersection")

    def test_helice_aditiva_e_subtrativa(self):
        obj, p = self._abrir("AdditiveHelix", "PainelHelice")
        p.campos["pitch"].setValue(5.0)
        p.campos["pitch"].editingFinished.emit()
        p.campos["checkBoxLeftHanded"].setChecked(True)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(obj.Pitch.Value, 5.0, places=3)
        self.assertTrue(obj.LeftHanded)
        fechar(self.doc)
        self.doc = None
        obj, p = self._abrir("SubtractiveHelix", "PainelHelice")
        self.assertIn("checkBoxOutside", p.campos, "a subtrativa tem a opção de remover por fora")

    def test_loft(self):
        obj, p = self._abrir("AdditiveLoft", "PainelLoft")
        self.assertIn("SecaoB", p.campos["secoes"].text())
        p.campos["regrada"].setChecked(True)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertTrue(obj.Ruled)

    def test_primitivas(self):
        esperado = {"AdditiveBox": ("boxLength", "Length"), "AdditiveCylinder": ("cylinderRadius", "Radius"),
                    "AdditiveSphere": ("sphereRadius", "Radius"), "AdditiveCone": ("coneHeight", "Height"),
                    "AdditiveTorus": ("torusRadius2", "Radius2"), "AdditivePrism": ("prismHeight", "Height"),
                    "AdditiveEllipsoid": ("ellipsoidRadius1", "Radius1"), "AdditiveWedge": (None, None),
                    "SubtractiveBox": ("boxHeight", "Height")}
        for tipo, (campo, prop) in esperado.items():
            obj, p = self._abrir(tipo, "PainelPrimitiva")
            self.assertTrue(p.campos, "%s: nenhum campo de medida" % tipo)
            if campo:
                self.assertIn(campo, p.campos, tipo)
                p.campos[campo].setValue(7.0)
                self._esp(0.3)
                self.assertTrue(self._ok(), tipo)
                self.assertAlmostEqual(getattr(obj, prop).Value, 7.0, places=3, msg=tipo)
            fechar(self.doc)
            self.doc = None
        obj, p = self._abrir("AdditivePrism", "PainelPrimitiva")
        p.campos["prismPolygon"].setValue(8)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertEqual(obj.Polygon, 8)

    def test_booleana(self):
        obj, p = self._abrir("Boolean", "PainelBooleana")
        self.assertIn("Outro", p.campos["corpos"].text())
        p.campos["tipo"].definir("0", silencioso=False)
        self._esp(0.5)
        self.assertTrue(self._ok())
        self.assertEqual(obj.Type, "Fuse")

    def test_multitransformacao(self):
        self.doc = novo_doc("PrumoTesteMulti")
        FreeCAD.setActiveDocument(self.doc.Name)
        body = self.doc.addObject("PartDesign::Body", "Body")
        sk = esboco_retangulo(body, 10.0, 10.0)
        pad = body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 5
        self.doc.recompute()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(pad)
        FreeCADGui.runCommand("PartDesign_MultiTransform", 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelMultiTransform")
        self.assertEqual(textos_com_problema(p), [])
        self.assertIn("Pad", p.campos["ops"].text())
        p.campos["add1"].click()               # + Padrão linear
        self._esp(1.2)
        p = self.C.painel()
        self.assertTrue(p.estado()["sub"], "a edição da transformação devia abrir")
        self.assertTrue(p.quadro.isVisible(), "o quadro do FreeCAD aparece durante a edição")
        p.campos["concluir"].click()
        self._esp(1.0)
        p = self.C.painel()
        self.assertEqual(len(p.estado()["trans"]), 1)
        self.assertEqual(p.campos["lista"].item(0).text().split()[0], "Padrão")
        self.assertTrue(self._ok())
        mt = self.doc.findObjects(Type="PartDesign::MultiTransform")
        self.assertEqual(len(mt[0].Transformations), 1)

    def test_varredura(self):
        obj, p = self._abrir("AdditivePipe", "PainelVarredura")
        self.assertIn("Perfil", p.campos["perfil"].text())
        ori = self.C.painel_secundario("PainelOrientacaoPipe")
        sec = self.C.painel_secundario("PainelSecoesPipe")
        self.assertIsNotNone(ori, "a orientação da seção devia estar em cartões")
        self.assertIsNotNone(sec, "a transformação da seção devia estar em cartões")
        self.assertFalse(ori.quadro.isVisible())
        self.assertFalse(sec.quadro.isVisible())
        self.assertEqual(textos_com_problema(ori), [])
        ori.campos["modo"].definir("2", silencioso=False)      # Frenet
        sec.campos["modo"].definir("1", silencioso=False)      # várias seções
        self._esp(0.6)
        self.assertEqual(self.C.painel_secundario("PainelSecoesPipe").f.indice("comboBoxScaling"), 1)
        self.assertIn("secoes", self.C.painel_secundario("PainelSecoesPipe").campos)
        p = self.C.painel()
        p.campos["trans"].definir("1", silencioso=False)
        self._esp(0.5)
        self.assertTrue(self._ok())
        self.assertEqual(obj.Transition, "Right corner")
        self.assertEqual(obj.Mode, "Frenet")


class T66PainelDeVistas(unittest.TestCase):
    """Desenho → Grupo de projeção e Vista: cartões no lugar do formulário do FreeCAD; as vistas escolhidas
    na grade (no 1º diedro) viram vistas da folha e a escala escolhida fica na vista."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        self.doc = novo_doc("PrumoTesteVistas")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.body = self.doc.addObject("PartDesign::Body", "Body")
        sk = esboco_retangulo(self.body)
        pad = self.body.newObject("PartDesign::Pad", "Pad")
        pad.Profile = sk
        pad.Length = 10
        self.doc.recompute()
        FreeCADGui.activateWorkbench("TechDrawWorkbench")
        self._esp(0.4)
        FreeCADGui.runCommand("TechDraw_PageDefault", 0)
        self._esp(0.8)

    def tearDown(self):
        try:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        fechar(self.doc)
        self._esp(0.8)      # janelas de folha somem só no próximo ciclo

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok

    def _abrir(self, cmd):
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.body)
        FreeCADGui.runCommand(cmd, 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % cmd)
        self.assertEqual(type(p).__name__, "PainelVistas")
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        return p

    def test_grupo_com_vista_inferior_no_1o_diedro(self):
        p = self._abrir("TechDraw_ProjectionGroup")
        self.assertIn("diedro", p.campos, "grupo de projeção mostra o arranjo")
        self.assertEqual(p.campos["vista1"].text(), "Inferior", "no 1º diedro a vista de baixo fica em cima")
        self.assertEqual(p.campos["vista8"].text(), "Superior")
        self.assertTrue(p.campos["vista4"].isChecked())
        p.campos["vista1"].click()
        self._esp(1.2)
        p = self.C.painel()
        self.assertTrue(p.campos["vista1"].isChecked())
        self.assertTrue(self._ok())
        grupos = self.doc.findObjects(Type="TechDraw::DrawProjGroup")
        self.assertEqual(len(grupos), 1)
        self.assertEqual(sorted(v.Type for v in grupos[0].Views), ["Bottom", "Front"])

    def test_vista_avulsa_com_escala_escolhida(self):
        p = self._abrir("TechDraw_View")
        self.assertNotIn("diedro", p.campos, "vista avulsa não tem arranjo de grupo")
        p.campos["escala"].definir("2", silencioso=False)
        self._esp(0.6)
        p = self.C.painel()
        self.assertTrue(p.campos["den"].isEnabled())
        p.campos["den"].setValue(5)
        self._esp(0.6)
        self.assertTrue(self._ok())
        vistas = [o for o in self.doc.Objects if o.TypeId in ("TechDraw::DrawViewPart", "TechDraw::DrawProjGroupItem")]
        self.assertTrue(vistas)
        self.assertEqual(vistas[0].ScaleType, "Custom")
        self.assertAlmostEqual(vistas[0].Scale, 0.2, places=6)

    def test_direcao_em_palavras(self):
        self.assertEqual(self.C.direcao_em_palavras("[0.00 -1.00 0.00]"), "de frente (−Y)")
        self.assertEqual(self.C.direcao_em_palavras("[0.00 0.00 1.00]"), "de cima (+Z)")
        self.assertIn("direção", self.C.direcao_em_palavras("[0.71 -0.71 0.00]"))


class T67CorteEDetalhe(unittest.TestCase):
    """Desenho → Vista em corte e Vista de detalhe em cartões: a letra, a direção e o raio escolhidos nos
    cartões ficam na vista criada."""

    setUp = T66PainelDeVistas.setUp
    tearDown = T66PainelDeVistas.tearDown
    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok

    def _vista_base(self):
        page = self.doc.findObjects(Type="TechDraw::DrawPage")[0]
        v = self.doc.addObject("TechDraw::DrawViewPart", "Vista")
        page.addView(v)
        v.Source = [self.body]
        v.Direction = FreeCAD.Vector(0, -1, 0)
        self.doc.recompute()
        self._esp(0.8)
        return v

    def _abrir(self, cmd, classe):
        v = self._vista_base()
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(v)
        FreeCADGui.runCommand(cmd, 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % cmd)
        self.assertEqual(type(p).__name__, classe)
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        return p

    def test_corte_com_letra_e_direcao(self):
        p = self._abrir("TechDraw_SectionView", "PainelCorte")
        p.campos["letra"].setText("B")
        p.campos["letra"].editingFinished.emit()
        self._esp(0.3)
        p.campos["pbRight"].click()
        self._esp(1.5)
        self.assertTrue(self._ok())
        cortes = self.doc.findObjects(Type="TechDraw::DrawViewSection")
        self.assertEqual(len(cortes), 1)
        self.assertEqual(cortes[0].SectionSymbol, "B")

    def test_detalhe_com_raio_e_letra(self):
        p = self._abrir("TechDraw_DetailView", "PainelDetalhe")
        p.campos["qsbRadius"].setValue(7.0)
        p.campos["letra"].setText("C")
        p.campos["letra"].editingFinished.emit()
        self._esp(0.5)
        self.assertTrue(self._ok())
        dets = self.doc.findObjects(Type="TechDraw::DrawViewDetail")
        self.assertEqual(len(dets), 1)
        self.assertAlmostEqual(float(dets[0].Radius), 7.0, places=3)
        self.assertEqual(dets[0].Reference, "C")

    def test_vistas_nao_confundem_com_corte(self):
        """O formulário de corte também tem um campo de escala com o mesmo nome do de vistas."""
        import PrumoPainelComando as C
        self.assertNotIn("cmbScaleType", C.AVULSOS)


class T68CotaBalaoHachura(unittest.TestCase):
    """Desenho → editar cota, balão e hachura em cartões; o OK grava o que se mudou nos cartões."""

    setUp = T66PainelDeVistas.setUp
    tearDown = T66PainelDeVistas.tearDown
    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok
    _vista_base = T67CorteEDetalhe._vista_base

    def _editar(self, obj, classe):
        FreeCADGui.ActiveDocument.setEdit(obj.Name)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % classe)
        self.assertEqual(type(p).__name__, classe)
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        return p

    def test_cota(self):
        v = self._vista_base()
        page = self.doc.findObjects(Type="TechDraw::DrawPage")[0]
        dim = self.doc.addObject("TechDraw::DrawViewDimension", "Cota")
        dim.Type = "Distance"
        dim.References2D = [(v, "Edge0")]
        page.addView(dim)
        self.doc.recompute()
        self._esp(0.8)
        p = self._editar(dim, "PainelCota")
        p.campos["dec"].setValue(1)
        p.campos["ref"].setChecked(True)
        self._esp(0.4)
        self.assertTrue(self._ok())
        # 1 casa decimal e cota de referência (o FreeCAD põe os parênteses no formato)
        self.assertEqual(dim.FormatSpec, "(%.1w)")
        self.assertFalse(dim.Arbitrary)

    def test_balao(self):
        v = self._vista_base()
        page = self.doc.findObjects(Type="TechDraw::DrawPage")[0]
        bal = self.doc.addObject("TechDraw::DrawViewBalloon", "Balao")
        bal.SourceView = v
        page.addView(bal)
        bal.Text = "1"
        self.doc.recompute()
        self._esp(0.8)
        p = self._editar(bal, "PainelBalao")
        p.campos["texto"].setText("7")
        p.campos["forma"].setCurrentIndex(4)
        p.campos["forma"].activated.emit(4)
        self._esp(0.4)
        self.assertTrue(self._ok())
        self.assertEqual(bal.Text, "7")
        self.assertEqual(bal.BubbleShape, "Hexagon")

    def test_hachura(self):
        v = self._vista_base()
        hat = self.doc.addObject("TechDraw::DrawHatch", "Hachura")
        hat.Source = (v, ["Face0"])
        self.doc.recompute()
        self._esp(0.8)
        p = self._editar(hat, "PainelHachura")
        p.campos["escala"].setValue(2.5)
        self._esp(0.4)
        cb = p.campos["padrao"]
        i = cb.findText("Madeira")
        self.assertGreaterEqual(i, 0, [cb.itemText(k) for k in range(cb.count())])
        cb.setCurrentIndex(i)
        cb.activated.emit(i)
        self._esp(0.5)
        p = self.C.painel()
        self.assertEqual(p.campos["padrao"].currentText(), "Madeira")
        from PySide import QtGui
        p.definir_cor(p.f.w("ccColor", self.C.QtWidgets.QWidget), QtGui.QColor("#FF0000"))
        self._esp(0.4)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(float(hat.ViewObject.HatchScale), 2.5, places=4)
        self.assertTrue(hat.HatchPattern.replace("\\", "/").endswith("wood.svg"), hat.HatchPattern)
        cor = hat.ViewObject.HatchColor
        self.assertAlmostEqual(cor[0], 1.0, places=2)
        self.assertAlmostEqual(cor[1], 0.0, places=2)

    def test_texto_formatado(self):
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.runCommand("TechDraw_RichTextAnnotation", 0)
        p = None
        for _i in range(20):
            self._esp(0.2)
            p = self.C.painel()
            if p is not None:
                break
        self.assertIsNotNone(p, "o painel do texto formatado não apareceu")
        self.assertEqual(type(p).__name__, "PainelTextoFormatado")
        self.assertFalse(p.quadro.isVisible())
        self.assertEqual(textos_com_problema(p), [])
        p.campos["texto"].setPlainText("Nota 1: rebarbar cantos")
        p.campos["moldura"].setChecked(True)
        self._esp(0.5)
        p = self.C.painel()
        self.assertIn("estilo", p.campos, "com moldura, o estilo da linha aparece")
        self.assertIn("rebarbar", p.campos["texto"].toPlainText())
        self.assertTrue(self._ok())
        an = self.doc.findObjects(Type="TechDraw::DrawRichAnno")
        self.assertEqual(len(an), 1)
        self.assertIn("Nota 1: rebarbar cantos", an[0].AnnoText)
        self.assertTrue(an[0].ShowFrame)


class T69Fixacao(unittest.TestCase):
    """Quadro "Fixação" em cartões: nos auxiliares sozinho, nas primitivas junto do painel de medidas;
    o deslocamento e o modo escolhidos nos cartões ficam no objeto."""

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok
    _fechar_janelas = T63FerramentasDePontaAPonta._fechar_janelas

    def setUp(self):
        T65MaisPaineisDeComando.setUp(self)
        from PySide import QtCore
        self.timer = QtCore.QTimer()          # pergunta do FreeCAD não pode travar a bateria
        self.timer.setInterval(300)
        self.timer.timeout.connect(self._fechar_janelas)
        self.timer.start()

    def tearDown(self):
        self.timer.stop()
        T65MaisPaineisDeComando.tearDown(self)

    def _corpo(self):
        self.doc = novo_doc("PrumoTesteFixacao")
        FreeCAD.setActiveDocument(self.doc.Name)
        body = self.doc.addObject("PartDesign::Body", "Body")
        return body, {o.Role: o for o in body.Origin.OriginFeatures}

    def test_plano_auxiliar_com_deslocamento(self):
        body, planos = self._corpo()
        pl = body.newObject("PartDesign::Plane", "Plano")
        pl.AttachmentSupport = [(planos["XY_Plane"], "")]
        pl.MapMode = "FlatFace"
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(pl.Name)
        self._esp(1.5)
        p = self.C.painel_fixacao()
        self.assertIsNotNone(p, "o painel de fixação não apareceu")
        self.assertFalse(p.quadro.isVisible(), "o quadro Fixação do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        self.assertIn("ref1", p.campos)
        self.assertNotIn("ref3", p.campos, "só a preenchida e a próxima livre aparecem")
        p.campos["deslZ"].setValue(15.0)
        self._esp(0.4)
        from PySide import QtWidgets
        visiveis = [b.text() for b in FreeCADGui.getMainWindow().findChildren(QtWidgets.QPushButton) if b.isVisible()]
        self.assertTrue(self._ok(), "sem OK; diálogo=%s botões=%s" % (FreeCADGui.Control.activeDialog(), visiveis[:12]))
        self.assertAlmostEqual(pl.AttachmentOffset.Base.z, 15.0, places=4)

    def test_modo_escolhido_no_cartao(self):
        body, planos = self._corpo()
        pl = body.newObject("PartDesign::Plane", "Plano")
        pl.AttachmentSupport = [(planos["XY_Plane"], "")]
        pl.MapMode = "FlatFace"
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(pl.Name)
        self._esp(1.5)
        p = self.C.painel_fixacao()
        cb = p.campos["modo"]
        self.assertGreater(cb.count(), 2)
        atual = cb.currentIndex()
        # outro modo que sirva para um plano (o 0 é "Desativado", que o FreeCAD pergunta antes de aceitar)
        alvo = next(i for i in range(1, cb.count()) if i != atual)
        cb.setCurrentIndex(alvo)
        cb.activated.emit(alvo)
        self._esp(0.6)
        self.assertTrue(self._ok())
        self.assertNotEqual(pl.MapMode, "FlatFace", "o modo escolhido no cartão não foi gravado")

    def test_primitiva_tem_os_dois_paineis(self):
        body, _p = self._corpo()
        cx = body.newObject("PartDesign::AdditiveBox", "Cubo")
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(cx.Name)
        self._esp(1.5)
        self.assertEqual(type(self.C.painel()).__name__, "PainelPrimitiva")
        self.assertEqual(type(self.C.painel_fixacao()).__name__, "PainelFixacao")


class T70SolidosEmCartoes(unittest.TestCase):
    """Sólidos (Part): Extrusão, Revolução, Espelhar e Escala em cartões; as formas seguem a seleção da lista
    do FreeCAD e o OK grava o que se mudou nos cartões."""

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok
    _fechar_janelas = T63FerramentasDePontaAPonta._fechar_janelas

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import Part
        from PySide import QtCore
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        FreeCADGui.activateWorkbench("PartWorkbench")
        self.doc = novo_doc("PrumoTesteSolidos")
        FreeCAD.setActiveDocument(self.doc.Name)
        self.perfil = self.doc.addObject("Sketcher::SketchObject", "Perfil")
        V = FreeCAD.Vector
        pts = [V(10, 0, 0), V(30, 0, 0), V(30, 20, 0), V(10, 20, 0)]
        for i in range(4):
            self.perfil.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]))
        self.caixa = self.doc.addObject("Part::Box", "Caixa")
        self.doc.recompute()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self._fechar_janelas)
        self.timer.start()

    def tearDown(self):
        self.timer.stop()
        try:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        fechar(self.doc)

    def _abrir(self, cmd, sel, classe):
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(sel)
        FreeCADGui.runCommand(cmd, 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % cmd)
        self.assertEqual(type(p).__name__, classe)
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        ligadas = [k for k, v in p.campos.items() if k.startswith("forma") and v.isChecked()]
        self.assertEqual(len(ligadas), 1, "a forma selecionada devia aparecer ligada: %s" % ligadas)
        return p

    def _novo(self, tipo):
        return [o for o in self.doc.Objects if o.TypeId == tipo]

    def test_extrusao(self):
        p = self._abrir("Part_Extrude", self.perfil, "PainelExtrusaoPart")
        p.campos["favor"].setValue(25.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        ex = self._novo("Part::Extrusion")
        self.assertEqual(len(ex), 1)
        self.assertAlmostEqual(float(ex[0].LengthFwd), 25.0, places=4)

    def test_revolucao(self):
        p = self._abrir("Part_Revolve", self.perfil, "PainelRevolucaoPart")
        p.campos["angulo"].setValue(90.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        rv = self._novo("Part::Revolution")
        self.assertEqual(len(rv), 1)
        self.assertAlmostEqual(float(rv[0].Angle), 90.0, places=4)

    def test_espelhar_no_plano_xz(self):
        p = self._abrir("Part_Mirror", self.caixa, "PainelEspelharPart")
        p.campos["plano"].setCurrentIndex(1)
        p.campos["plano"].activated.emit(1)
        self._esp(0.4)
        self.assertTrue(self._ok())
        mr = self._novo("Part::Mirroring")
        self.assertEqual(len(mr), 1)
        n = mr[0].Normal
        self.assertAlmostEqual(abs(n.y), 1.0, places=6, msg="plano XZ tem normal em Y: %s" % n)

    def _arestas(self, cmd, tipo, chanfro):
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(self.caixa)
        FreeCADGui.runCommand(cmd, 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertEqual(type(p).__name__, "PainelArestasPart")
        self.assertEqual(p._chanfro(), chanfro)
        self.assertEqual(textos_com_problema(p), [])
        p.campos["selectAllButton"].click()
        self._esp(0.6)
        p = self.C.painel()
        self.assertIn("12 marcadas", p.campos["resumo"].text())
        p.campos["r1"].setValue(2.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        obj = self._novo(tipo)
        self.assertEqual(len(obj), 1)
        self.assertEqual(len(obj[0].Edges), 12)
        self.assertAlmostEqual(obj[0].Edges[0][1], 2.0, places=4)

    def test_arredondar_todas_as_arestas(self):
        self._arestas("Part_Fillet", "Part::Fillet", False)

    def test_chanfrar_todas_as_arestas(self):
        self._arestas("Part_Chamfer", "Part::Chamfer", True)

    def test_escala(self):
        p = self._abrir("Part_Scale", self.caixa, "PainelEscalaPart")
        p.campos["fator"].setValue(2.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        sc = self._novo("Part::Scale")
        self.assertEqual(len(sc), 1)
        self.assertAlmostEqual(float(sc[0].UniformScale), 2.0, places=4)


class T71JuntaDaMontagem(unittest.TestCase):
    """Montagem → junta em cartões: o tipo escolhido na grade muda a junta e mostra só as medidas e os
    limites daquele tipo; a aba do comando se chama "Junta"."""

    _esp = T62PainelDeComando._esp

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        FreeCADGui.activateWorkbench("AssemblyWorkbench")
        self._esp(0.5)
        self.doc = novo_doc("PrumoTesteMontagem")
        FreeCAD.setActiveDocument(self.doc.Name)
        asm = self.doc.addObject("Assembly::AssemblyObject", "Assembly")
        b1 = self.doc.addObject("Part::Box", "Caixa1")
        b2 = self.doc.addObject("Part::Box", "Caixa2")
        b2.Placement.Base = FreeCAD.Vector(30, 0, 0)
        asm.addObject(b1)
        asm.addObject(b2)
        self.doc.recompute()
        FreeCADGui.ActiveDocument.setEdit(asm)
        self._esp(0.8)

    def tearDown(self):
        try:
            if FreeCADGui.Control.activeDialog():
                # Cancelar de verdade: closeDialog não chama o reject da junta, e o filtro de seleção
                # dela ficaria valendo para os testes seguintes
                from PySide import QtWidgets
                for bb in FreeCADGui.getMainWindow().findChildren(QtWidgets.QDialogButtonBox):
                    for b in bb.buttons():
                        if isinstance(b, QtWidgets.QPushButton) and b.isVisible() and \
                                bb.buttonRole(b) == QtWidgets.QDialogButtonBox.RejectRole:
                            b.click()
                            break
                self._esp(0.4)
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
            FreeCADGui.ActiveDocument.resetEdit()
        except Exception:
            pass
        try:
            FreeCADGui.Selection.removeSelectionGate()
        except Exception:
            pass
        fechar(self.doc)

    def test_tipo_muda_as_medidas(self):
        import PrumoPainelLateral as L
        FreeCADGui.runCommand("Assembly_CreateJointDistance", 0)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "o painel da junta não apareceu")
        self.assertEqual(type(p).__name__, "PainelJunta")
        self.assertFalse(p.quadro.isVisible())
        self.assertEqual(textos_com_problema(p), [])
        self.assertTrue(p.campos["tipo5"].isChecked(), "Distância devia vir marcada")
        self.assertIn("distanceSpinbox", p.campos)
        p.campos["tipo1"].click()          # Rotação
        self._esp(0.8)
        p = self.C.painel()
        self.assertEqual(p.f.indice("jointType"), 1)
        self.assertNotIn("distanceSpinbox", p.campos)
        self.assertIn("limitCheckbox3", p.campos, "rotação tem limite de ângulo")
        dock = FreeCADGui.getMainWindow().findChild(__import__("PySide").QtWidgets.QDockWidget, "Tasks")
        self.assertEqual(L.titulo_do_comando(dock)[0], "Junta")

    def test_inserir_peca_pelos_cartoes(self):
        from PySide import QtCore
        peca = self.doc.addObject("Part::Cylinder", "Eixo")
        self.doc.recompute()
        fechador = QtCore.QTimer()
        fechador.setInterval(300)
        fechador.timeout.connect(lambda: T63FerramentasDePontaAPonta._fechar_janelas(self))
        fechador.start()
        try:
            FreeCADGui.runCommand("Assembly_InsertLink", 0)
            self._esp(1.5)
            p = self.C.painel()
            self.assertIsNotNone(p, "o painel de inserir não apareceu")
            self.assertEqual(type(p).__name__, "PainelInserirPecas")
            self.assertFalse(p.quadro.isVisible())
            self.assertEqual(textos_com_problema(p), [])
            p.campos["filtro"].setText("Eix")
            self._esp(0.8)
            p = self.C.painel()
            nomes = [v for k, v in p.campos.items() if k.startswith("nome")]
            self.assertEqual(nomes, ["Eixo"], "o filtro devia deixar só o Eixo: %s" % nomes)
            p.campos["peca0"].click()
            self._esp(1.0)
            p = self.C.painel()
            self.assertIn("(1)", p.campos["peca0"].text(), "o botão devia contar a inserção")
            self.assertTrue(T62PainelDeComando._ok(self))
        finally:
            fechador.stop()
        asm = self.doc.getObject("Assembly")
        links = [o for o in asm.Group if o.TypeId == "App::Link"]
        self.assertEqual(len(links), 1)
        self.assertIs(links[0].LinkedObject, peca)


class T72SimulacaoEmCartoes(unittest.TestCase):
    """Simulação: material, fixação, força, pressão e malha em cartões. Força e pressão aparecem em N e MPa
    (o FreeCAD guarda em mN e kPa) e o OK grava o valor certo."""

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok
    _fechar_janelas = T63FerramentasDePontaAPonta._fechar_janelas

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        import ObjectsFem
        from PySide import QtCore
        import PrumoPainelComando as C
        C.instalar()
        self.C = C
        FreeCADGui.activateWorkbench("FemWorkbench")
        self._esp(0.5)
        self.doc = novo_doc("PrumoTesteSimulacao")
        FreeCAD.setActiveDocument(self.doc.Name)
        cx = self.doc.addObject("Part::Box", "Caixa")
        self.doc.recompute()
        an = ObjectsFem.makeAnalysis(self.doc, "Estudo")
        self.mat = ObjectsFem.makeMaterialSolid(self.doc, "Material")
        self.fixa = ObjectsFem.makeConstraintFixed(self.doc, "Fixa")
        self.fixa.References = [(cx, "Face1")]
        self.forca = ObjectsFem.makeConstraintForce(self.doc, "Forca")
        self.forca.References = [(cx, "Face2")]
        self.pressao = ObjectsFem.makeConstraintPressure(self.doc, "Pressao")
        self.pressao.References = [(cx, "Face6")]
        self.malha = ObjectsFem.makeMeshGmsh(self.doc, "Malha")
        self.malha.Shape = cx
        for o in (self.mat, self.fixa, self.forca, self.pressao, self.malha):
            an.addObject(o)
        self.doc.recompute()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(300)
        self.timer.timeout.connect(self._fechar_janelas)
        self.timer.start()

    def tearDown(self):
        self.timer.stop()
        try:
            if FreeCADGui.Control.activeDialog():
                FreeCADGui.Control.closeDialog()
        except Exception:
            pass
        fechar(self.doc)

    def _editar(self, obj, classe):
        FreeCADGui.ActiveDocument.setEdit(obj.Name)
        self._esp(1.5)
        p = self.C.painel()
        self.assertIsNotNone(p, "%s: o painel em cartões não apareceu" % classe)
        self.assertEqual(type(p).__name__, classe)
        self.assertFalse(p.quadro.isVisible())
        self.assertEqual(textos_com_problema(p), [])
        return p

    def test_forca_em_newton(self):
        p = self._editar(self.forca, "PainelForcaFem")
        self.assertIn("Face2", p.campos["refs"].text())
        p.campos["forca"].setValue(250.0)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(self.forca.Force.getValueAs("N").Value, 250.0, places=4)

    def test_pressao_em_mpa(self):
        p = self._editar(self.pressao, "PainelPressaoFem")
        p.campos["pressao"].setValue(0.5)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(self.pressao.Pressure.getValueAs("MPa").Value, 0.5, places=6)

    def test_fixacao_material_e_malha(self):
        p = self._editar(self.fixa, "PainelFixacaoFem")
        self.assertIn("Face1", p.campos["refs"].text())
        self.assertTrue(self._ok())
        self._esp(0.5)
        p = self._editar(self.mat, "PainelMaterialFem")
        self.assertIn("qsb_young_modulus", p.campos)
        self.assertTrue(self._ok())
        self._esp(0.5)
        p = self._editar(self.malha, "PainelMalhaGmsh")
        p.campos["max"].setValue(4.0)
        self._esp(0.3)
        FreeCADGui.Control.closeDialog()    # OK rodaria o Gmsh; aqui só o cartão importa
        self._esp(0.5)

    def test_deslocamento_imposto_em_z(self):
        import ObjectsFem
        cx = self.doc.getObject("Caixa")
        d = ObjectsFem.makeConstraintDisplacement(self.doc, "Desloc")
        d.References = [(cx, "Face1")]
        self.doc.recompute()
        p = self._editar(d, "PainelDeslocamentoFem")
        self.assertNotIn("spinzDisplacement", p.campos, "eixo livre não mostra valor")
        p.campos["DisplacementZGB"].setChecked(True)
        self._esp(0.4)
        p = self.C.painel()
        self.assertIn("spinzDisplacement", p.campos)
        p.campos["spinzDisplacement"].setValue(0.5)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertFalse(d.zFree)
        self.assertTrue(d.xFree)
        self.assertAlmostEqual(d.zDisplacement.getValueAs("mm").Value, 0.5, places=6)

    def test_mola_em_n_por_mm(self):
        import ObjectsFem
        cx = self.doc.getObject("Caixa")
        m = ObjectsFem.makeConstraintSpring(self.doc, "Mola")
        m.References = [(cx, "Face1")]
        self.doc.recompute()
        p = self._editar(m, "PainelMolaFem")
        p.campos["normal"].setValue(2.0)
        p.campos["tangente"].setValue(0.5)
        self._esp(0.3)
        self.assertTrue(self._ok())
        self.assertAlmostEqual(m.NormalStiffness.getValueAs("N/mm").Value, 2.0, places=6)
        self.assertAlmostEqual(m.TangentialStiffness.getValueAs("N/mm").Value, 0.5, places=6)

    def test_onde_vale_do_material(self):
        cx = self.doc.getObject("Caixa")
        self._editar(self.mat, "PainelMaterialFem")
        self._esp(0.6)
        ov = self.C.painel_secundario("PainelOndeVale")
        self.assertIsNotNone(ov, "o quadro Onde vale devia ganhar cartões")
        self.assertFalse(ov.quadro.isVisible(), "o seletor do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(ov), [])
        self.assertIn("modo", ov.campos, "material aceita sólido inteiro ou faces")
        ov.campos["modo"].definir("sol", silencioso=False)
        self._esp(0.3)
        ov = self.C.painel_secundario("PainelOndeVale")
        ov.campos["adicionar"].click()
        self._esp(0.4)
        ov = self.C.painel_secundario("PainelOndeVale")
        self.assertEqual(ov.campos["adicionar"].text(), "Parar de escolher")
        FreeCADGui.Selection.addSelection(cx, "Face1")
        self._esp(0.6)
        ov = self.C.painel_secundario("PainelOndeVale")
        self.assertIn("tirar0", ov.campos, "o sólido escolhido devia aparecer")
        # o seletor do FreeCAD sai do modo de escolha depois de cada item acrescentado
        self.assertEqual(ov.campos["adicionar"].text(), "Adicionar na vista")
        self.assertTrue(self._ok())
        self.assertEqual([(o.Name, list(sub)) for o, sub in self.mat.References], [("Caixa", ["Solid1"])])

    def _painel_peso(self):
        for _i in range(20):
            self._esp(0.2)
            ws = [w for w in FreeCADGui.getMainWindow().findChildren(self.C.PainelPesoProprio) if w.isVisible()]
            if ws:
                return ws[0]
        return None

    def test_peso_proprio_criado_pela_faixa_abre_painel(self):
        import FemGui
        FemGui.setActiveAnalysis(self.doc.getObject("Estudo"))
        FreeCADGui.runCommand("FEM_ConstraintSelfWeight", 0)
        p = self._painel_peso()
        self.assertIsNotNone(p, "criar o peso próprio devia abrir o painel em cartões")
        self.assertEqual(textos_com_problema(p), [])
        self.assertEqual(p.campos["direcao"].valor(), "0,0,-1")
        p.campos["direcao"].definir("0,-1,0", silencioso=False)
        p.campos["aceleracao"].setValue(9.81)
        self._esp(0.3)
        self.assertTrue(self._ok())
        pp = [o for o in self.doc.Objects if hasattr(o, "GravityDirection")]
        self.assertEqual(len(pp), 1)
        self.assertAlmostEqual(pp[0].GravityDirection.y, -1.0, places=6)
        self.assertAlmostEqual(pp[0].GravityAcceleration.getValueAs("m/s^2").Value, 9.81, places=6)
        # duplo clique (editar) abre de novo, com o que foi gravado
        FreeCADGui.ActiveDocument.setEdit(pp[0].Name)
        p = self._painel_peso()
        self.assertIsNotNone(p, "editar o peso próprio devia abrir o painel")
        self.assertEqual(p.campos["direcao"].valor(), "0,-1,0")
        FreeCADGui.Control.closeDialog()

    def test_unidade_interna(self):
        """Confere a conversão que os cartões usam (se o FreeCAD mudar a unidade interna, o teste avisa)."""
        q = FreeCAD.Units.Quantity("250 N")
        self.assertAlmostEqual(FreeCAD.Units.Quantity(q.Value, q.Unit).getValueAs("N").Value, 250.0)
        self.assertAlmostEqual(FreeCAD.Units.Quantity("1 MPa").Value, 1000.0)


class T73Preferencias(unittest.TestCase):
    """Preferências do Prumo em cartões: abre pelo comando, cada interruptor grava na hora, sem texto
    cortado, unidades com nomes em português."""

    def setUp(self):
        if not FreeCAD.GuiUp:
            self.skipTest("sem interface")
        self.g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
        self.antes = self.g.GetBool("EnquadrarAoSairDoEsboco", True)

    def tearDown(self):
        self.g.SetBool("EnquadrarAoSairDoEsboco", self.antes)
        import PrumoPreferencias as P
        j = P._estado["janela"]
        if j is not None:
            try:
                j.close()
            except RuntimeError:
                pass

    _esp = T62PainelDeComando._esp


    def test_abrir_cai_na_aba_inicio(self):
        import PrumoInicio
        import PrumoRibbon
        rb = PrumoRibbon._state.get("ribbon")
        if rb is None or FreeCAD.listDocuments():
            self.skipTest("sem faixa ou com documento aberto")
        FreeCADGui.activateWorkbench("PartDesignWorkbench")
        self._esp(0.4)
        PrumoInicio.show()
        self._esp(0.3)
        PrumoInicio._faixa_no_inicio()
        self._esp(0.3)
        self.assertEqual(rb._tabs[rb.tabbar.currentIndex()]["id"], "inicio")

    def test_preferencia_mostra_relatorio_e_console(self):
        import PrumoPreferencias as P
        from PySide import QtWidgets
        g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
        tinha = "ModoDistribuicao" in g.GetBools()
        antes = g.GetBool("ModoDistribuicao", True)
        try:
            FreeCADGui.runCommand("Prumo_Preferencias", 0)
            self._esp(0.6)
            j = P._estado["janela"]
            sw = j.campos["programacao"]
            self.assertFalse(sw.isChecked(), "por padrão Relatório e console ficam fechados")
            sw.setChecked(True)
            self._esp(0.3)
            rel = FreeCADGui.getMainWindow().findChild(QtWidgets.QDockWidget, "Report view")
            self.assertFalse(g.GetBool("ModoDistribuicao", True))
            if rel is not None:
                self.assertTrue(rel.isVisible())
            sw.setChecked(False)
            self._esp(0.3)
            if rel is not None:
                self.assertFalse(rel.isVisible())
        finally:
            if tinha:
                g.SetBool("ModoDistribuicao", antes)
            else:
                g.RemBool("ModoDistribuicao")
    def test_abre_e_grava(self):
        import PrumoPreferencias as P
        FreeCADGui.runCommand("Prumo_Preferencias", 0)
        self._esp(0.6)
        j = P._estado["janela"]
        self.assertIsNotNone(j)
        self.assertTrue(j.isVisible())
        self.assertEqual(textos_com_problema(j), [])
        sw = j.campos["EnquadrarAoSairDoEsboco"]
        sw.setChecked(not self.antes)
        self._esp(0.1)
        self.assertEqual(self.g.GetBool("EnquadrarAoSairDoEsboco", True), not self.antes)
        nomes = [j.campos["esquema"].itemText(i) for i in range(j.campos["esquema"].count())]
        self.assertTrue(any(n.startswith("Padrão") for n in nomes), nomes)
        self.assertFalse(any(n in ("Internal", "MKS") for n in nomes), nomes)
        for k in ("PainelLateralUnico", "RetirarAutomaticasEmConflito", "VerificarAtualizacoes", "tema", "decimais"):
            self.assertIn(k, j.campos)

    def test_botao_da_faixa(self):
        import PrumoRibbon
        inicio = [t for t in PrumoRibbon.TABS if t["id"] == "inicio"][0]
        cmds = [b[0] for _p, bs in inicio["panels"] for b in bs]
        self.assertIn("Prumo_Preferencias", cmds)


class T74MaisSolidosEmCartoes(unittest.TestCase):
    """Sólidos (Part): deslocamento, espessura, transição (loft) e varredura em cartões, gravando pelo OK."""

    _esp = T62PainelDeComando._esp
    _ok = T62PainelDeComando._ok
    _fechar_janelas = T63FerramentasDePontaAPonta._fechar_janelas
    setUp = T70SolidosEmCartoes.setUp
    tearDown = T70SolidosEmCartoes.tearDown
    _novo = T70SolidosEmCartoes._novo

    def _so_painel(self, cmd, classe, sel=None, sub=None):
        FreeCADGui.Selection.clearSelection()
        if sel is not None:
            if sub:
                FreeCADGui.Selection.addSelection(sel, sub)
            else:
                FreeCADGui.Selection.addSelection(sel)
        # o primeiro comando depois de trocar de documento às vezes acha o comando ainda inativo
        c = FreeCADGui.Command.get(cmd)
        for _i in range(10):
            if c is None or c.isActive():
                break
            self._esp(0.3)
        FreeCADGui.runCommand(cmd, 0)
        p = None
        for _i in range(25):
            self._esp(0.2)
            p = self.C.painel()
            if p is not None and type(p).__name__ == classe:
                break
        if p is None:
            from PySide import QtWidgets
            dlg = FreeCADGui.Control.activeDialog()
            pan = self.C._painel_de_tarefas()
            nomes = [w.objectName() for w in pan.findChildren(QtWidgets.QWidget) if w.objectName()][:25] \
                if pan is not None else None
            jan = [(type(w).__name__, w.windowTitle()) for w in QtWidgets.QApplication.topLevelWidgets()
                   if w.isVisible()]
            self.fail("%s: o painel em cartões não apareceu; tarefa=%s; ligado=%s; nomes=%s; janelas=%s; objs=%s"
                      % (cmd, dlg, self.C.ligado(), nomes, jan, [o.TypeId for o in self.doc.Objects]))
        self.assertEqual(type(p).__name__, classe)
        self.assertFalse(p.quadro.isVisible(), "o formulário do FreeCAD devia ficar escondido")
        self.assertEqual(textos_com_problema(p), [])
        return p

    def test_deslocamento_3d(self):
        p = self._so_painel("Part_Offset", "PainelOffsetPart", self.caixa)
        self.assertNotIn("faces", p.campos, "deslocamento não tem escolha de faces")
        p.campos["valor"].setValue(2.0)
        self._esp(0.3)
        p.campos["junta"].definir("2", silencioso=False)     # canto vivo
        self._esp(0.5)
        self.assertTrue(self._ok())
        ob = self._novo("Part::Offset")
        self.assertEqual(len(ob), 1)
        self.assertAlmostEqual(float(ob[0].Value), 2.0, places=4)
        self.assertEqual(ob[0].Join, "Intersection")

    def test_espessura_com_face_aberta(self):
        p = self._so_painel("Part_Thickness", "PainelOffsetPart", self.caixa, "Face6")
        self.assertIn("faces", p.campos)
        p.campos["valor"].setValue(-1.5)
        self._esp(0.4)
        self.assertTrue(self._ok())
        ob = self._novo("Part::Thickness")
        self.assertEqual(len(ob), 1)
        self.assertAlmostEqual(float(ob[0].Value), -1.5, places=4)

    def test_verificar_geometria_resumo(self):
        g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Part/CheckGeometry")
        antes = g.GetBool("AutoRun", False)
        g.SetBool("AutoRun", True)
        try:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(self.caixa)
            FreeCADGui.runCommand("Part_CheckGeometry", 0)
            p = None
            for _i in range(25):
                self._esp(0.2)
                p = self.C.painel_secundario("PainelChecaGeometria")
                if p is not None and "estado0" in p.campos:
                    break
            self.assertIsNotNone(p, "o resumo da verificação não apareceu")
            self.assertEqual(textos_com_problema(p), [])
            self.assertIn("válida", p.campos["estado0"].text())
            self.assertEqual(p.campos["faces0"].text(), "6")
            self.assertEqual(p.campos["arestas0"].text(), "12")
            self.assertEqual(p.campos["volume0"].text(), "1.000 mm³")
            self.assertTrue(p.quadro.isVisible(), "a lista de defeitos do FreeCAD continua à vista")
        finally:
            g.SetBool("AutoRun", antes)
            FreeCADGui.Control.closeDialog()

    def _circulos(self):
        c1 = self.doc.addObject("Part::Circle", "Base")
        c1.Radius = 10
        c2 = self.doc.addObject("Part::Circle", "Topo")
        c2.Radius = 5
        c2.Placement.Base = FreeCAD.Vector(0, 0, 30)
        self.doc.recompute()
        return c1, c2

    def test_transicao_entre_dois_circulos(self):
        self._circulos()
        p = self._so_painel("Part_Loft", "PainelLoftPart")
        nomes = [k for k in p.campos if k.startswith("disp")]
        self.assertGreaterEqual(len(nomes), 2, p.campos.keys())
        for nome in ("Base", "Topo"):
            p = self.C.painel()
            alvo = None
            disp = p.f.w("availableTreeWidget", self.C.QtWidgets.QTreeWidget)
            for i in range(disp.topLevelItemCount()):
                if disp.topLevelItem(i).text(0).startswith(nome):
                    alvo = "disp%d" % i
            self.assertIsNotNone(alvo, nome)
            p.campos[alvo].click()
            self._esp(0.5)
        p = self.C.painel()
        self.assertIn("sel1_removeButton", p.campos, "os dois perfis deviam estar na ordem")
        self.assertFalse(p.campos["sel0_upButton"].isEnabled(), "o primeiro não sobe")
        p.campos["solido"].setChecked(True)
        self._esp(0.4)
        self.assertTrue(self._ok())
        ob = self._novo("Part::Loft")
        self.assertEqual(len(ob), 1)
        self.assertEqual([o.Name for o in ob[0].Sections], ["Base", "Topo"])
        self.assertTrue(ob[0].Solid)
        self.assertGreater(ob[0].Shape.Volume, 0)

    def test_varredura_com_caminho_escolhido(self):
        c1, _c2 = self._circulos()
        self.doc.removeObject("Topo")
        lin = self.doc.addObject("Part::Line", "Guia")
        lin.X1, lin.Y1, lin.Z1, lin.X2, lin.Y2, lin.Z2 = 0, 0, 0, 0, 0, 40
        self.doc.recompute()
        p = self._so_painel("Part_Sweep", "PainelVarreduraPart")
        disp = p.f.w("availableTreeWidget", self.C.QtWidgets.QTreeWidget)
        idx = [i for i in range(disp.topLevelItemCount()) if disp.topLevelItem(i).text(0).startswith("Base")]
        self.assertTrue(idx)
        p.campos["disp%d" % idx[0]].click()
        self._esp(0.5)
        p = self.C.painel()
        p.campos["caminho"].click()
        self._esp(0.5)
        p = self.C.painel()
        self.assertEqual(p.campos["caminho"].text(), "Concluir o caminho")
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(lin, "Edge1")
        self._esp(0.3)
        p.campos["caminho"].click()
        self._esp(0.6)
        p = self.C.painel()
        self.assertEqual(p.campos["caminho"].text(), "Escolher caminho na vista")
        p.campos["solido"].setChecked(True)
        self._esp(0.4)
        self.assertTrue(self._ok())
        ob = self._novo("Part::Sweep")
        self.assertEqual(len(ob), 1)
        self.assertEqual(ob[0].Spine[0].Name, "Guia")
        self.assertAlmostEqual(ob[0].Shape.Volume, 3.141592653589793 * 100 * 40, delta=1.0)


RAPIDOS = [T11CotasNaTela, T12Massa, T13MenuContexto, T14ListaMateriais, T15FolhasABNT, T16Perfis,
           T17Estrutura, T18ChapaMetalica, T19VasoPressao, T20Fixadores, T21EnquadrarEsboco,
           T22EstruturaGrupos, T23EstruturaCantos, T24EstruturaExtras,
           T25EstruturaInterface, T26Versao, T27Exemplos, T28TraducaoEArvore, T29GuiaEstrutura,
           T30Faixa, T31Bancadas, T32Arvore, T33PaineisVisuais,
           T34FluxoDeSelecao, T35PropriedadesDaPeca,
           T36ChapaFatorKeDXF, T37Variantes, T37bVariantesPainel, T38CopiarProjeto,
           T39Montagem, T40ModelosComRegras, T41GuiaMigracao, T42SimulacaoEstrutura,
           T43DetalheLigacao, T44RotulasCargasSecoes, T45BancadaVasos, T46NBR2024,
           T47MolasTracaoModos, T48AssistenteEstrutura,
           T49ReguaHistorico, T50ConferirEsboco, T51FaixaContextual, T52Esboco3D, T53Tubulacao, T54ReferenciasAutomaticas,
           T55PainelLateral, T56PropriedadesEAparencia,
           T57PainelDoEsboco, T58TelaInicialAjuda, T59PadraoVisualNosPaineis,
           T60Atualizacao, T61PaineisExtrasComoAbas,
           T62PainelDeComando, T63FerramentasDePontaAPonta, T64TextosNasTelas,
           T65MaisPaineisDeComando, T66PainelDeVistas, T67CorteEDetalhe,
           T68CotaBalaoHachura, T69Fixacao, T70SolidosEmCartoes,
           T71JuntaDaMontagem, T72SimulacaoEmCartoes, T73Preferencias, T74MaisSolidosEmCartoes]
