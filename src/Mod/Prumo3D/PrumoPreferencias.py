# SPDX-License-Identifier: LGPL-2.1-or-later
"""Preferências do Prumo 3D: as opções que importam no dia a dia, em cartões, sem precisar abrir a janela
completa de preferências do FreeCAD (que continua a um clique).

Cada interruptor grava na hora. O que só vale ao reabrir o programa diz isso ao lado.
"""

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtWidgets

import PrumoUI as UI

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
UNIDADES_PATH = "User parameter:BaseApp/Preferences/Units"

# (parâmetro, rótulo, padrão, vale só ao reabrir?)
APARENCIA = [("TelaInicial", "Mostrar a tela inicial ao abrir", True, False),
             ("RibbonContextual", "Faixa muda de aba conforme o que está em edição", True, False)]
PAINEL = [("PainelLateralUnico", "Painel lateral único (árvore, propriedades e comando em abas)", True, True),
          ("PropriedadesEmCartoes", "Propriedades em cartões", True, False),
          ("PainelDeComando", "Comandos em cartões (no lugar dos formulários do FreeCAD)", True, False),
          ("AbasCompactas", "Abas só com ícone quando falta espaço", True, False),
          ("OcultarLateralNoInicio", "Esconder o painel lateral na tela inicial", True, False)]
ESBOCO = [("RetirarAutomaticasEmConflito", "Retirar relações automáticas que não cabem no desenho", True, False),
          ("ReferenciasAutomaticas", "Referências automáticas ao editar (arestas e faces da peça)", True, False),
          ("EnquadrarAoSairDoEsboco", "Enquadrar a peça ao sair do esboço", True, False)]
ATUALIZACAO = [("VerificarAtualizacoes", "Procurar versão nova ao abrir (no máximo uma vez por dia)", True, False),
               ("AtualizarBetas", "Incluir versões de teste (beta)", True, False)]


ESQUEMAS_PT = {"Internal": "Padrão (mm, kg, s, graus)", "MKS": "MKS (m, kg, s, graus)",
               "Imperial": "Imperial (pol, lb)", "ImperialDecimal": "Imperial decimal (pol)",
               "Centimeter": "Centímetros (cm, m², m³)", "ImperialBuilding": "Imperial para construção (pés e pol)",
               "MmMin": "Peças pequenas e CNC (mm, mm/min)", "ImperialCivil": "Imperial civil (pés, mph)",
               "FEM": "Simulação (mm, N, s)", "MeterDecimal": "Metros decimais (m, m², m³)"}


def _p():
    return FreeCAD.ParamGet(PARAM_PATH)


def _u():
    return FreeCAD.ParamGet(UNIDADES_PATH)


class JanelaPreferencias(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or FreeCADGui.getMainWindow())
        self.setObjectName("PrumoUI")
        self.setWindowTitle("Preferências do Prumo 3D")
        self.setStyleSheet(UI.qss())
        self.setMinimumWidth(520)
        self.resize(560, 720)
        self.campos = {}
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(10)
        t = QtWidgets.QLabel("Preferências")
        t.setStyleSheet(UI.tema("color: #003A70; font-size: 13pt; font-weight: 700;"))
        lay.addWidget(t)
        interno = QtWidgets.QWidget()
        col = QtWidgets.QVBoxLayout(interno)
        col.setContentsMargins(0, 0, 4, 0)
        area = UI.rolagem(interno)
        self.col = col
        col.setSpacing(10)
        self._tema()
        self._grupo("Aparência", "aparencia", APARENCIA)
        self._grupo("Painel lateral", "arvore", PAINEL)
        self._grupo("Esboço", "esboco", ESBOCO)
        self._unidades()
        self._atualizacao()
        self._programacao()
        col.addStretch(1)
        lay.addWidget(area, 1)
        rod = QtWidgets.QHBoxLayout()
        todas = QtWidgets.QPushButton("Todas as preferências do FreeCAD…")
        todas.setAutoDefault(False)
        todas.clicked.connect(self._todas)
        rod.addWidget(todas)
        rod.addStretch(1)
        fechar = QtWidgets.QPushButton("Fechar")
        fechar.setObjectName("PrumoPrimario")
        fechar.setAutoDefault(False)
        fechar.clicked.connect(self.accept)
        rod.addWidget(fechar)
        lay.addLayout(rod)

    # ---------------------------------------------------------------- cartões
    def _grupo(self, titulo, icone, itens):
        c = UI.Cartao(titulo, icone)
        for chave, rotulo, padrao, reabrir in itens:
            sw = UI.Interruptor(_p().GetBool(chave, padrao))
            sw.toggled.connect(lambda on, k=chave: _p().SetBool(k, bool(on)))
            c.linha(rotulo + (" (vale ao reabrir)" if reabrir else ""), sw)
            self.campos[chave] = sw
        self.col.addWidget(c)
        return c

    def _programacao(self):
        """Relatório e console Python: fechados para quem só desenha; quem programa liga aqui."""
        c = UI.Cartao("Para quem programa", "comando")
        g = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
        sw = UI.Interruptor(not g.GetBool("ModoDistribuicao", True))

        def mudar(on):
            g.SetBool("ModoDistribuicao", not bool(on))
            try:
                import PrumoGui
                PrumoGui.apply_modo_distribuicao(not bool(on))
            except Exception:
                pass
        sw.toggled.connect(mudar)
        c.linha("Mostrar Relatório e console Python", sw)
        self.campos["programacao"] = sw
        self.col.addWidget(c)
        return c

    def _tema(self):
        import PrumoEstilo
        c = UI.Cartao("Tema", "aparencia")
        atual = "escuro" if PrumoEstilo.escuro() else "claro"
        seg = UI.Segmentado([("claro", "Claro", "olho"), ("escuro", "Escuro", "olho")], atual, colunas=2)
        seg.mudou.connect(self._trocar_tema)
        c.widget(seg)
        nota = QtWidgets.QLabel("Trocar o tema fecha e abre o Prumo de novo (ele pergunta antes).")
        nota.setObjectName("PrumoSub")
        nota.setWordWrap(True)
        c.widget(nota)
        self.campos["tema"] = seg
        self.col.addWidget(c)

    def _trocar_tema(self, chave):
        import PrumoEstilo
        if (chave == "escuro") == PrumoEstilo.escuro():
            return
        try:
            FreeCADGui.runCommand("Prumo_TemaEscuro", 0)
        finally:
            # se o usuário desistiu, a escolha volta a mostrar o tema atual
            self.campos["tema"].definir("escuro" if PrumoEstilo.escuro() else "claro")

    def _unidades(self):
        c = UI.Cartao("Unidades", "medida")
        cb = QtWidgets.QComboBox()
        cb.setObjectName("PrumoLista")
        cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        cb.setMinimumContentsLength(18)
        cb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        try:
            nomes = list(FreeCAD.Units.listSchemas())
        except Exception:
            nomes = []
        for i, n in enumerate(nomes):
            cb.addItem(ESQUEMAS_PT.get(n, n), i)
        cb.setCurrentIndex(max(0, min(_u().GetInt("UserSchema", 0), cb.count() - 1)))
        cb.activated.connect(self._esquema)
        c.linha("Sistema de unidades", cb)
        self.campos["esquema"] = cb
        dec = QtWidgets.QSpinBox()
        dec.setObjectName("PrumoNum")
        dec.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        dec.setRange(0, 8)
        dec.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        dec.setMaximumWidth(80)
        dec.setValue(_u().GetInt("Decimals", 2))
        dec.valueChanged.connect(self._decimais)
        c.linha("Casas decimais nos campos", dec)
        self.campos["decimais"] = dec
        self.col.addWidget(c)

    def _esquema(self, i):
        _u().SetInt("UserSchema", int(i))
        try:
            FreeCAD.Units.setSchema(int(i))
        except Exception:
            pass

    def _decimais(self, n):
        _u().SetInt("Decimals", int(n))
        try:
            FreeCAD.Units.setDecimals(int(n))
        except Exception:
            pass

    def _atualizacao(self):
        c = self._grupo("Atualizações", "info", ATUALIZACAO)
        b = QtWidgets.QPushButton("Verificar agora")
        b.setAutoDefault(False)
        b.clicked.connect(self._verificar)
        c.widget(b)
        self.campos["verificar"] = b

    def _verificar(self):
        import PrumoAtualizar
        self._verificacao = PrumoAtualizar.verificar_agora(self)

    def _todas(self):
        self.accept()
        QtCore.QTimer.singleShot(0, lambda: FreeCADGui.runCommand("Std_DlgPreferences", 0))


_estado = {"janela": None}


def abrir():
    j = _estado["janela"]
    try:
        if j is not None and j.isVisible():
            j.raise_()
            j.activateWindow()
            return j
    except RuntimeError:
        pass
    j = JanelaPreferencias()
    _estado["janela"] = j
    j.show()
    return j


class CmdPreferencias:
    def GetResources(self):
        return {"Pixmap": "preferences-general", "MenuText": "Preferências",
                "ToolTip": "As opções do Prumo 3D em cartões (tema, painel lateral, esboço, unidades, atualizações)"}

    def IsActive(self):
        return True

    def Activated(self):
        abrir()


def registrar():
    FreeCADGui.addCommand("Prumo_Preferencias", CmdPreferencias())
