# SPDX-License-Identifier: LGPL-2.1-or-later
"""Usinix: nenhum clique fica sem resposta.

Quando uma ferramenta não pode rodar (sem projeto aberto, sem a seleção que ela pede, em edição de esboço,
fora da bancada certa) ou roda e dá erro, aparece um aviso curto embaixo da janela dizendo o que houve e o
que fazer. Vale para os botões da faixa, a barra de vistas e a busca de comandos.
"""
import re

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    QtCore = QtGui = QtWidgets = None

TEMPO_MS = 7000
_ESTADO = {"aviso": None, "ultimo": ""}


# ------------------------------------------------------------------ o porquê
def _info(nome):
    try:
        return FreeCADGui.Command.get(nome).getInfo() or {}
    except Exception:
        return {}


def _rotulo(nome, rotulo=None):
    if rotulo:
        return " ".join(str(rotulo).split())
    t = _info(nome).get("menuText", "") or nome
    return t.replace("&", "").strip()


def _primeira_frase(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = " ".join(t.split())
    for sep in (". ", "; "):
        if sep in t:
            return t.split(sep, 1)[0] + "."
    return t


def motivo_inativo(nome, rotulo=None):
    """Por que a ferramenta não roda agora, com o que fazer."""
    r = _rotulo(nome, rotulo)
    if FreeCAD.ActiveDocument is None:
        return "%s precisa de um projeto aberto. Crie um novo (Novo) ou abra um arquivo." % r
    try:
        gd = FreeCADGui.ActiveDocument
        em_edicao = gd is not None and gd.getInEdit() is not None
    except Exception:
        em_edicao = False
    if em_edicao and not nome.startswith("Sketcher_"):
        return "%s não funciona com um esboço ou operação em edição. Feche a edição (Fechar ou Esc) e tente de novo." % r
    if nome.startswith("Sketcher_") and not em_edicao and nome not in ("Sketcher_NewSketch", "Sketcher_ValidateSketch"):
        return "%s só funciona dentro de um esboço. Abra um esboço (duplo clique nele) ou crie um novo." % r
    try:
        if FreeCADGui.Control.activeDialog() and not em_edicao:
            return "%s está esperando: há um painel aberto ao lado. Conclua (OK) ou cancele o painel antes." % r
    except Exception:
        pass
    dica = _primeira_frase(_info(nome).get("toolTip", ""))
    sel = FreeCADGui.Selection.getSelectionEx()
    if not sel:
        return ("%s precisa de algo selecionado. Escolha na tela ou na árvore o que a ferramenta usa%s"
                % (r, (": " + dica) if dica else "."))
    return ("%s não pode ser usada com o que está selecionado agora. Confira a seleção%s"
            % (r, (": " + dica) if dica else "."))


# ------------------------------------------------------------------ aviso na tela
if QtWidgets is not None:
    class AvisoClique(QtWidgets.QFrame):
        """Faixa de aviso flutuante, embaixo e no meio da janela, que some sozinha."""

        def __init__(self, parent):
            super().__init__(parent)
            self.setObjectName("PrumoAvisoClique")
            self.setStyleSheet(
                "#PrumoAvisoClique { background: #FFF6D6; border: 1px solid #E0A100; border-left: 5px solid #E0A100;"
                " border-radius: 8px; }"
                "#PrumoAvisoClique[tipo='erro'] { background: #FBE9E5; border-color: #B5523F; }"
                "#PrumoAvisoClique QLabel { background: transparent; color: #3D2E00; font-size: 9.5pt; }"
                "#PrumoAvisoClique[tipo='erro'] QLabel { color: #5A1E12; }"
                "#PrumoAvisoClique QToolButton { border: none; background: transparent; color: #66727F;"
                " font-size: 11pt; }")
            hl = QtWidgets.QHBoxLayout(self)
            hl.setContentsMargins(12, 8, 6, 8)
            self.icone = QtWidgets.QLabel("⚠")
            self.icone.setStyleSheet("font-size: 13pt;")
            self.texto = QtWidgets.QLabel("")
            self.texto.setWordWrap(True)
            self.texto.setTextFormat(QtCore.Qt.PlainText)
            fechar = QtWidgets.QToolButton()
            fechar.setText("×")
            fechar.setToolTip("Fechar o aviso")
            fechar.clicked.connect(self.hide)
            hl.addWidget(self.icone, 0, QtCore.Qt.AlignTop)
            hl.addWidget(self.texto, 1)
            hl.addWidget(fechar, 0, QtCore.Qt.AlignTop)
            self._timer = QtCore.QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self.hide)
            self.hide()

        def mostrar(self, texto, tipo="aviso"):
            self.setProperty("tipo", tipo)
            self.style().unpolish(self)
            self.style().polish(self)
            self.icone.setText("⛔" if tipo == "erro" else "⚠")
            self.texto.setText(texto)
            p = self.parentWidget()
            larg = min(640, max(360, p.width() // 2))
            self.setFixedWidth(larg)
            self.adjustSize()
            self.move((p.width() - self.width()) // 2, p.height() - self.height() - 70)
            self.show()
            self.raise_()
            self._timer.start(TEMPO_MS)


def mostrar(texto, tipo="aviso"):
    """Mostra o aviso (e grava no relatório, para quem estiver com ele aberto)."""
    _ESTADO["ultimo"] = texto
    try:
        FreeCAD.Console.PrintWarning("Usinix: %s\n" % texto)
    except Exception:
        pass
    if QtWidgets is None or not FreeCAD.GuiUp:
        return None
    mw = FreeCADGui.getMainWindow()
    av = _ESTADO.get("aviso")
    try:
        import shiboken6
        vivo = av is not None and shiboken6.isValid(av)
    except Exception:
        vivo = av is not None
    if not vivo:
        av = AvisoClique(mw)
        _ESTADO["aviso"] = av
    av.mostrar(texto, tipo)
    return av


def ultimo():
    return _ESTADO["ultimo"]


# ------------------------------------------------------------------ rodar com aviso
def _relatorio():
    if QtWidgets is None:
        return None
    mw = FreeCADGui.getMainWindow()
    for cls in (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit):
        w = mw.findChild(cls, "ReportOutput")
        if w is not None:
            return w
    return None


PALAVRAS_ERRO = ("traceback", "error", "erro", "exception", "exceção", "falhou", "failed", "não foi possível",
                 "cannot", "can't", "invalid", "inválid")


def _erros_novos(rel, inicio):
    try:
        texto = rel.toPlainText()
    except Exception:
        return []
    novo = texto[inicio:] if inicio <= len(texto) else ""
    linhas = [l.strip() for l in novo.splitlines() if l.strip()]
    ruins = []
    for l in linhas:
        baixo = l.lower()
        if l.startswith("Usinix: "):
            if "falh" in baixo or "erro" in baixo or "não foi possível" in baixo:
                ruins.append(l)
        elif any(p in baixo for p in PALAVRAS_ERRO):
            ruins.append(l)
    return ruins


def _traduzir(msg):
    try:
        import PrumoErros
        pt = PrumoErros.traduzir(msg)
        if pt:
            return pt
    except Exception:
        pass
    return msg


def executar(nome, fn, rotulo=None):
    """Roda fn() (o clique). Se der erro (exceção ou mensagem de erro no relatório), mostra o aviso."""
    rel = _relatorio()
    try:
        inicio = len(rel.toPlainText()) if rel is not None else 0
    except Exception:
        inicio = 0
    try:
        fn()
    except Exception as exc:
        mostrar("%s não foi executada: %s" % (_rotulo(nome, rotulo), _traduzir(str(exc))), "erro")
        return False
    if rel is not None and QtCore is not None:
        def conferir():
            erros = _erros_novos(rel, inicio)
            if erros:
                ult = [e for e in erros if not e.lower().startswith("traceback")]
                msg = (ult or erros)[-1]
                msg = re.sub(r"^(Usinix: )", "", msg)
                mostrar("%s não foi concluída: %s" % (_rotulo(nome, rotulo), _traduzir(msg)), "erro")
        QtCore.QTimer.singleShot(400, conferir)
    return True


def clique_inativo(nome, rotulo=None):
    """Clique numa ferramenta que não pode rodar agora: explica por quê."""
    return mostrar(motivo_inativo(nome, rotulo))
