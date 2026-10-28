# SPDX-License-Identifier: LGPL-2.1-or-later
"""Esboço que não deixa super-restringir (como o SolidCraft recusa e o SolidWorks oferece "cota acionada").

No FreeCAD, uma restrição a mais deixa o esboço em vermelho ("restrições redundantes/conflitantes") e quem
está começando não sabe o que fazer. Aqui, logo depois de a restrição entrar:

- cota (distância, raio, ângulo...) que sobra ou conflita vira **cota de referência**: continua na tela, só
  mostra a medida, e o esboço segue definido;
- restrição geométrica (horizontal, coincidente...) que sobra ou conflita **não é aplicada**;

e um aviso pequeno diz o que aconteceu, com o botão para voltar atrás se a pessoa quiser mesmo assim.
"""

import FreeCAD

PARAM = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
DIMENSIONAIS = {"Distance", "DistanceX", "DistanceY", "Radius", "Diameter", "Angle", "Weight", "SnellsLaw"}
NOMES = {"Distance": "distância", "DistanceX": "distância horizontal", "DistanceY": "distância vertical",
         "Radius": "raio", "Diameter": "diâmetro", "Angle": "ângulo", "Horizontal": "horizontal",
         "Vertical": "vertical", "Coincident": "coincidente", "Parallel": "paralela",
         "Perpendicular": "perpendicular", "Tangent": "tangente", "Equal": "igual", "Symmetric": "simétrica",
         "PointOnObject": "ponto na curva", "Block": "bloqueio", "Lock": "travamento"}

_estado = {"contagem": {}, "limpo": {}, "ocupado": False, "aviso": None}


def ligado():
    return FreeCAD.ParamGet(PARAM).GetBool("RecusarSuperRestricao", True)


def problematicas(sk):
    """Índices (base 0) das restrições que sobram ou conflitam, depois de resolver."""
    sk.solve()
    return sorted({i - 1 for i in list(sk.ConflictingConstraints) + list(sk.RedundantConstraints)})


def tratar(sk, n_antes):
    """Confere as restrições novas (índices >= n_antes). Devolve [(índice, tipo, "referencia"|"removida")].

    Só mexe se o esboço estava limpo antes: um esboço já em conflito é problema antigo, não da última ação."""
    n = len(sk.Constraints)
    if n <= n_antes:
        return []
    ruins = [i for i in problematicas(sk) if i >= n_antes]
    if not ruins:
        return []
    feitos = []
    # de trás para a frente: remover não mexe nos índices que ainda faltam
    for i in sorted(ruins, reverse=True):
        c = sk.Constraints[i]
        if c.Type in DIMENSIONAIS and c.Driving:
            sk.setDriving(i, False)
            feitos.append((i, c.Type, "referencia"))
        elif c.Type not in DIMENSIONAIS:
            sk.delConstraint(i)
            feitos.append((i, c.Type, "removida"))
    sk.solve()
    return list(reversed(feitos))


def texto(feitos):
    refs = [NOMES.get(t, t) for _i, t, o in feitos if o == "referencia"]
    tirou = [NOMES.get(t, t) for _i, t, o in feitos if o == "removida"]
    partes = []
    if refs:
        partes.append("A cota de %s deixaria o esboço super-restrito (a medida já está definida por outras "
                      "restrições). Ela ficou como <b>cota de referência</b>: mostra a medida, mas não comanda."
                      % ", ".join(refs))
    if tirou:
        partes.append("A restrição %s não foi aplicada: ela já é garantida por outra (ou entraria em conflito)."
                      % ", ".join(tirou))
    return "<br>".join(partes)


# ======================================================================== interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtWidgets
    import PrumoEstilo

    QSS = """
    #PrumoAvisoRestricao { background: #FFFFFF; border: 1px solid #F7BE00; border-left: 5px solid #F7BE00;
                           border-radius: 6px; }
    #PrumoAvisoRestricao QLabel { color: #1E2A38; }
    """

    class AvisoRestricao(QtWidgets.QFrame):
        def __init__(self, sk, feitos, desfazer, parent):
            super().__init__(parent)
            self.setObjectName("PrumoAvisoRestricao")
            self.setStyleSheet(PrumoEstilo.tema(QSS))
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(6)
            self.texto = QtWidgets.QLabel(texto(feitos))
            self.texto.setWordWrap(True)
            lay.addWidget(self.texto)
            bl = QtWidgets.QHBoxLayout()
            self.bt_desfazer = QtWidgets.QPushButton("Aplicar mesmo assim")
            self.bt_desfazer.setToolTip("Volta como estava: o esboço fica super-restrito (em vermelho)")
            self.bt_desfazer.clicked.connect(lambda: (desfazer(), self.fechar()))
            bt_ok = QtWidgets.QPushButton("Entendi")
            bt_ok.clicked.connect(self.fechar)
            bl.addWidget(self.bt_desfazer)
            bl.addStretch(1)
            bl.addWidget(bt_ok)
            lay.addLayout(bl)
            self.setFixedWidth(420)
            self.adjustSize()
            mw = self.parentWidget()
            area = mw.centralWidget() if mw is not None else None
            if area is not None:
                g = area.geometry()
                self.move(g.right() - self.width() - 16, g.bottom() - self.height() - 40)
            self.timer = QtCore.QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.fechar)
            self.timer.start(20000)

        def fechar(self):
            self.hide()
            self.deleteLater()
            if _estado["aviso"] is self:
                _estado["aviso"] = None

    def _em_edicao(sk):
        try:
            gdoc = FreeCADGui.getDocument(sk.Document.Name)
            vp = gdoc.getInEdit() if gdoc else None
            return vp is not None and vp.Object is sk
        except Exception:
            return False

    def conferir_agora(sk, n_antes):
        """Trata as restrições novas e mostra o aviso (devolve a lista do que foi feito)."""
        if _estado["ocupado"] or not ligado():
            return []
        _estado["ocupado"] = True
        try:
            # esboço que já estava em conflito antes: não é a última ação, deixa como está
            if not _estado["limpo"].get((sk.Document.Name, sk.Name), True):
                _estado["limpo"][(sk.Document.Name, sk.Name)] = not problematicas(sk)
                return []
            copia = [sk.Constraints[i] for i in range(n_antes, len(sk.Constraints))]
            doc = sk.Document
            doc.openTransaction("Restrição a mais")
            feitos = tratar(sk, n_antes)
            doc.commitTransaction()
            _estado["contagem"][(doc.Name, sk.Name)] = len(sk.Constraints)
            _estado["limpo"][(doc.Name, sk.Name)] = not problematicas(sk)
        finally:
            _estado["ocupado"] = False
        if not feitos:
            return []

        def desfazer():
            _estado["ocupado"] = True
            try:
                doc.openTransaction("Aplicar mesmo assim")
                for i, _t, o in feitos:
                    if o == "referencia":
                        sk.setDriving(i, True)
                    else:
                        c = copia[i - n_antes]
                        sk.addConstraint(c)
                doc.commitTransaction()
                sk.solve()
                _estado["contagem"][(doc.Name, sk.Name)] = len(sk.Constraints)
                _estado["limpo"][(doc.Name, sk.Name)] = not problematicas(sk)
            finally:
                _estado["ocupado"] = False
        velho = _estado["aviso"]
        if velho is not None:
            try:
                velho.fechar()
            except RuntimeError:
                pass
        a = AvisoRestricao(sk, feitos, desfazer, FreeCADGui.getMainWindow())
        a.show()
        a.raise_()
        _estado["aviso"] = a
        return feitos

    class Observador:
        """Vigia a lista de restrições dos esboços em edição."""

        def slotChangedObject(self, obj, prop):
            if prop != "Constraints" or _estado["ocupado"]:
                return
            try:
                if not obj.isDerivedFrom("Sketcher::SketchObject"):
                    return
            except Exception:
                return
            chave = (obj.Document.Name, obj.Name)
            n = len(obj.Constraints)
            antes = _estado["contagem"].get(chave)
            _estado["contagem"][chave] = n
            if antes is None or n <= antes or not _em_edicao(obj):
                return
            # depois que o comando do Sketcher terminar (ele ainda pode mexer na restrição)
            QtCore.QTimer.singleShot(0, lambda o=obj, a=antes: _seguro(o, a))

    def _seguro(sk, antes):
        try:
            if sk.Document is not None and len(sk.Constraints) > antes:
                conferir_agora(sk, antes)
        except Exception as ex:
            FreeCAD.Console.PrintLog("Prumo: guarda do esboço: %s\n" % ex)

    def ao_editar(sk):
        _estado["contagem"][(sk.Document.Name, sk.Name)] = len(sk.Constraints)
        try:
            _estado["limpo"][(sk.Document.Name, sk.Name)] = not problematicas(sk)
        except Exception:
            _estado["limpo"][(sk.Document.Name, sk.Name)] = True

    _obs = {"obj": None}

    def instalar():
        if _obs["obj"] is None:
            _obs["obj"] = Observador()
            FreeCAD.addDocumentObserver(_obs["obj"])
        return _obs["obj"]
