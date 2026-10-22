# SPDX-License-Identifier: LGPL-2.1-or-later
"""Conferência do esboço ao sair da edição: perfil aberto, pontas quase encostadas, coincidências que
faltam e geometria degenerada, com correção num clique.

O Sketcher já tem o "Validar esboço" (TaskSketcherValidation), mas é preciso lembrar de chamar; o erro
de perfil aberto só aparece depois, quando a extrusão falha. Aqui a conferência roda sozinha ao concluir
o esboço e só avisa quando há problema que importa:

- geometria degenerada (linha ou arco de tamanho zero);
- pontas a menos de FOLGA uma da outra mas separadas (desenho à mão, DXF importado);
- pontas abertas num esboço que precisa ser fechado (perfil de extrusão, cavidade, revolução..., ou
  esboço que mistura contornos fechados e abertos);
- coincidências que faltam (pontas no mesmo lugar sem a restrição) num perfil.

Esboços de caminho, esqueleto de estrutura e linhas soltas de propósito (todos os contornos abertos e
sem quem precise de perfil fechado) não geram aviso.
"""
import math

import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
TOL_EXATA = 1e-4        # mm — mesma tolerância padrão do validador do Sketcher
TOL_DEGENERADA = 1e-6   # mm
FOLGA = 0.1             # mm — pontas mais próximas que isso são tratadas como "quase encostadas"
# operações que precisam de perfil fechado
PRECISA_FECHADO = ("PartDesign::Pad", "PartDesign::Pocket", "PartDesign::Revolution", "PartDesign::Groove",
                   "PartDesign::Hole", "Part::Extrusion", "Part::Revolution", "Part::Face",
                   "PartDesign::AdditiveLoft", "PartDesign::SubtractiveLoft")
_estado = {"aviso": None}


# ======================================================================== conferência
def _consumidores_fechados(sk):
    res = []
    for o in sk.InList:
        if o.TypeId in PRECISA_FECHADO:
            res.append(o)
        elif "Contorno" in o.PropertiesList and getattr(o, "Esboco", None) is sk:
            res.append(o)       # seção personalizada do Prumo: o contorno precisa ser fechado
    return res


def _quase_encostadas(vertices):
    """Pares de pontas abertas separadas por mais que TOL_EXATA e menos que FOLGA: [(d, p, q)]."""
    pares = []
    vs = [FreeCAD.Vector(v) for v in vertices]
    for i in range(len(vs)):
        for j in range(i + 1, len(vs)):
            d = (vs[i] - vs[j]).Length
            if TOL_EXATA < d < FOLGA:
                pares.append((d, vs[i], vs[j]))
    return sorted(pares, key=lambda x: x[0])


def conferir(sk):
    """Problemas do esboço. dict: degeneradas, quase (pares), abertas (pontas), faltam (coincidências),
    precisa_fechado (bool), problemas ([texto]), corrigivel (bool)."""
    r = {"degeneradas": 0, "quase": [], "abertas": [], "faltam": 0, "precisa_fechado": False,
         "problemas": [], "corrigivel": False}
    try:
        shape = sk.Shape
    except Exception:
        return r
    if shape.isNull():
        return r
    r["degeneradas"] = sk.detectDegeneratedGeometries(TOL_DEGENERADA)
    abertas = [FreeCAD.Vector(v) for v in sk.OpenVertices]
    r["abertas"] = abertas
    r["quase"] = _quase_encostadas(abertas)
    fios = shape.Wires
    fechados = [w for w in fios if w.isClosed()]
    misturado = bool(fechados) and len(fechados) < len(fios)
    cons = _consumidores_fechados(sk)
    r["precisa_fechado"] = bool(cons) or misturado
    r["faltam"] = sk.detectMissingPointOnPointConstraints(TOL_EXATA, False)
    # a conferência acima guarda a lista no esboço; não deixa nada pendurado nele
    p = r["problemas"]
    if r["degeneradas"]:
        p.append("%d elemento(s) de tamanho zero (linha ou arco degenerado)." % r["degeneradas"])
    if r["quase"]:
        d = r["quase"][0][0]
        p.append("%d par(es) de pontas quase encostadas (a menor folga é %s mm): o contorno parece fechado "
                 "na tela, mas está aberto." % (len(r["quase"]), _fmt(d)))
    pontas_reais = max(0, len(abertas) - 2 * len(r["quase"]))
    if r["precisa_fechado"] and pontas_reais > 0:
        quem = (" (usado em %s)" % ", ".join(o.Label for o in cons[:3])) if cons else ""
        p.append("%d ponta(s) solta(s) num esboço que precisa ser fechado%s: a extrusão ou cavidade "
                 "pode falhar." % (pontas_reais, quem))
    if r["faltam"] and (r["precisa_fechado"] or r["quase"]):
        p.append("%d encontro(s) de pontas sem a restrição de coincidência: mudar uma cota pode separar "
                 "o contorno." % r["faltam"])
    r["corrigivel"] = bool(r["degeneradas"] or r["quase"] or r["faltam"])
    return r


def _fmt(v):
    if v >= 0.01:
        return ("%.2f" % v).replace(".", ",")
    return ("%.4f" % v).replace(".", ",")


def corrigir(sk, transacao=True):
    """Remove degeneradas e cria as coincidências que faltam (inclusive das pontas quase encostadas).
    Retorna a conferência depois da correção."""
    doc = sk.Document
    r = conferir(sk)
    if transacao:
        doc.openTransaction("Corrigir esboço")
    try:
        if r["degeneradas"]:
            sk.removeDegeneratedGeometries(TOL_DEGENERADA)
        tol = TOL_EXATA
        if r["quase"]:
            tol = min(FOLGA, max(d for d, _p, _q in r["quase"]) * 1.05)
        if sk.detectMissingPointOnPointConstraints(tol, False):
            sk.makeMissingPointOnPointCoincident()
        doc.recompute()
    except Exception:
        if transacao:
            doc.abortTransaction()
        raise
    if transacao:
        doc.commitTransaction()
    return conferir(sk)


# ======================================================================== aviso na tela
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtWidgets

    import PrumoEstilo

    QSS = """
    #SwAvisoEsboco { background: #FFFFFF; border: 1px solid #E0A100; border-left: 5px solid #E0A100;
                     border-radius: 8px; }
    #SwAvisoEsboco QLabel { color: #1F2A36; background: transparent; }
    #SwAvisoEsboco QLabel#SwAvisoTit { color: #003A70; font-weight: 700; font-size: 10pt; }
    #SwAvisoEsboco QPushButton { padding: 4px 10px; }
    #SwAvisoEsboco QPushButton#SwPrimario { background: #003A70; color: #FFFFFF; border: 1px solid #003A70;
                                            font-weight: 600; }
    """

    class Aviso(QtWidgets.QFrame):
        """Aviso não modal no canto da janela, com Corrigir / Ver no validador / Ignorar."""

        def __init__(self, sk, r, parent):
            super().__init__(parent)
            self.setObjectName("SwAvisoEsboco")
            self.setStyleSheet(PrumoEstilo.tema(QSS))
            self.doc_nome, self.sk_nome = sk.Document.Name, sk.Name
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(6)
            t = QtWidgets.QLabel("Esboço “%s”: conferir antes de seguir" % sk.Label)
            t.setObjectName("SwAvisoTit")
            t.setWordWrap(True)
            lay.addWidget(t)
            self.texto = QtWidgets.QLabel("<br>".join("• " + x for x in r["problemas"]))
            self.texto.setWordWrap(True)
            lay.addWidget(self.texto)
            bl = QtWidgets.QHBoxLayout()
            self.bt_corrigir = QtWidgets.QPushButton("Corrigir")
            self.bt_corrigir.setObjectName("SwPrimario")
            self.bt_corrigir.setToolTip("Apaga elementos de tamanho zero e une as pontas (cria as coincidências). "
                                        "Desfazer (Ctrl+Z) volta.")
            self.bt_corrigir.setVisible(r["corrigivel"])
            self.bt_corrigir.clicked.connect(self.corrigir)
            bt_ver = QtWidgets.QPushButton("Ver no validador")
            bt_ver.setToolTip("Abre o Validar esboço do Sketcher, que destaca as pontas na tela")
            bt_ver.clicked.connect(self.ver)
            bt_fechar = QtWidgets.QPushButton("Ignorar")
            bt_fechar.clicked.connect(self.fechar)
            for b in (self.bt_corrigir, bt_ver):
                bl.addWidget(b)
            bl.addStretch(1)
            bl.addWidget(bt_fechar)
            lay.addLayout(bl)
            self.setFixedWidth(400)
            self.adjustSize()
            self._posicionar()
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.fechar)
            self.timer.start(45000)

        def _posicionar(self):
            mw = self.parentWidget()
            area = mw.centralWidget() if mw is not None else None
            if area is None:
                return
            g = area.geometry()
            self.move(g.right() - self.width() - 16, g.bottom() - self.height() - 40)

        def esboco(self):
            doc = FreeCAD.getDocument(self.doc_nome) if self.doc_nome in FreeCAD.listDocuments() else None
            return doc.getObject(self.sk_nome) if doc else None

        def corrigir(self):
            sk = self.esboco()
            if sk is None:
                self.fechar()
                return None
            self.timer.stop()
            try:
                r = corrigir(sk)
            except Exception as ex:
                self.texto.setText("Não foi possível corrigir: %s" % ex)
                return None
            if r["problemas"]:
                self.texto.setText("Corrigido o que dava. Ainda falta:<br>" +
                                   "<br>".join("• " + x for x in r["problemas"]))
                self.bt_corrigir.setVisible(False)
            else:
                self.texto.setText("Pronto: o esboço está fechado e sem pontas soltas. "
                                   "Desfazer (Ctrl+Z) volta, se precisar.")
                self.bt_corrigir.setVisible(False)
                self.timer.start(6000)
            self.adjustSize()
            self._posicionar()
            return r

        def ver(self):
            sk = self.esboco()
            self.fechar()
            if sk is None:
                return
            try:
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(sk)
                FreeCADGui.runCommand("Sketcher_ValidateSketch", 0)
            except Exception as ex:
                FreeCAD.Console.PrintWarning("Prumo: validar esboço: %s\n" % ex)

        def fechar(self):
            self.hide()
            self.deleteLater()
            if _estado["aviso"] is self:
                _estado["aviso"] = None

    def conferir_e_avisar(sk):
        """Roda a conferência e mostra o aviso se houver problema. Retorna o aviso (ou None)."""
        if not FreeCAD.ParamGet(PARAM).GetBool("ConferirEsbocoAoSair", True):
            return None
        try:
            r = conferir(sk)
        except Exception as ex:
            FreeCAD.Console.PrintLog("Prumo: conferir esboço: %s\n" % ex)
            return None
        velho = _estado["aviso"]
        if velho is not None:
            try:
                velho.fechar()
            except RuntimeError:
                pass
        if not r["problemas"]:
            return None
        a = Aviso(sk, r, FreeCADGui.getMainWindow())
        a.show()
        a.raise_()
        _estado["aviso"] = a
        return a

    def ao_sair_do_esboco(sk):
        QtCore.QTimer.singleShot(250, lambda: _seguro(sk))

    def _seguro(sk):
        try:
            if sk.Document is not None:
                conferir_e_avisar(sk)
        except Exception:
            pass
