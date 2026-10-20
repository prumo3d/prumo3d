# SPDX-License-Identifier: LGPL-2.1-or-later
"""Um fluxo só para a seleção: função antes ou peça antes, os dois funcionam.

No FreeCAD, algumas bancadas pedem a peça selecionada antes do comando (operações booleanas do
Sólidos, vistas do Desenho) e outras abrem o comando e pedem a seleção depois (Peça). No Prumo,
quando um comando que exige seleção prévia é chamado sem ela, abre um painel que diz o que
selecionar, mostra o que já foi escolhido e roda o comando ao clicar em OK.

- SELECAO_PRIMEIRO: comandos do FreeCAD tratados assim (a faixa mantém o botão ligado);
- pedir(...): painel genérico usado também pelos comandos do Prumo.
"""

import FreeCAD
import FreeCADGui

import PrumoPainel as P


# ------------------------------------------------------------------------------- filtros
def _solidos(obj, subs):
    try:
        if obj.Shape.Solids or obj.Shape.Shells:
            return [(obj.Label, obj)]
    except Exception:
        pass
    return []


def _formas(obj, subs):
    try:
        if not obj.Shape.isNull():
            return [(obj.Label, obj)]
    except Exception:
        pass
    return []


def _pecas(obj, subs):
    import PrumoUtil
    return [(obj.Label, obj)] if PrumoUtil.pecas([obj]) else []


def _esbocos(obj, subs):
    return [(obj.Label, obj)] if obj.isDerivedFrom("Sketcher::SketchObject") else []


def _estruturas(obj, subs):
    import PrumoEstrutura as E
    e = E.estrutura_de(obj)
    return [(e.Label, e)] if e is not None else []


def _barras(obj, subs):
    import PrumoEstrutura as E
    return [(b.Label, b) for b in E.barras_do_item(obj, subs)]


FILTROS = {"solidos": _solidos, "formas": _formas, "pecas": _pecas, "esbocos": _esbocos,
           "estruturas": _estruturas, "barras": _barras}

# comando: (título, instrução, [(rótulo da caixa, filtro, mínimo, máximo)])
SELECAO_PRIMEIRO = {
    "Part_Cut": ("Subtrair", "Escolha a peça base e depois a ferramenta (a peça que será retirada da base).",
                 [("Peça base", "solidos", 1, 1), ("Ferramenta", "solidos", 1, 1)]),
    "Part_Fuse": ("Unir", "Escolha as peças que viram uma só.", [("Peças", "solidos", 2, None)]),
    "Part_Common": ("Interseção", "Escolha as peças: fica só o volume comum a todas.",
                    [("Peças", "solidos", 2, None)]),
    "Part_Section": ("Seção", "Escolha as duas formas: o resultado é a linha de interseção entre elas.",
                     [("Primeira forma", "formas", 1, 1), ("Segunda forma", "formas", 1, 1)]),
    "Part_BooleanFragments": ("Fragmentos booleanos", "Escolha as peças.", [("Peças", "solidos", 2, None)]),
    "Part_Slice": ("Fatiar em composto", "Escolha a peça e depois as ferramentas de corte.",
                   [("Peça", "solidos", 1, 1), ("Ferramentas de corte", "formas", 1, None)]),
    "Part_SliceApart": ("Fatiar separado", "Escolha a peça e depois as ferramentas de corte.",
                        [("Peça", "solidos", 1, 1), ("Ferramentas de corte", "formas", 1, None)]),
    "Part_XOR": ("XOR booleano", "Escolha as peças.", [("Peças", "solidos", 2, None)]),
    "Part_JoinConnect": ("Conectar formas", "Escolha as peças.", [("Peças", "solidos", 2, None)]),
    "Part_JoinEmbed": ("Embutir formas", "Escolha a peça base e a peça a embutir.",
                       [("Peça base", "solidos", 1, 1), ("Peça a embutir", "solidos", 1, 1)]),
    "Part_JoinCutout": ("Recortar encaixe", "Escolha a peça a recortar e a peça que encaixa.",
                        [("Peça a recortar", "solidos", 1, 1), ("Peça que encaixa", "solidos", 1, 1)]),
    "Part_CompSolidsBooleans": ("Booleanas", "Escolha as peças.", [("Peças", "solidos", 2, None)]),
    "TechDraw_View": ("Vista no desenho", "Escolha as peças para a vista (com uma folha aberta).",
                      [("Peças", "pecas", 1, None)]),
    "TechDraw_ProjectionGroup": ("Grupo de vistas", "Escolha as peças para as vistas (com uma folha aberta).",
                                 [("Peças", "pecas", 1, None)]),
}


def precisa_de_painel(cmd):
    """True se o comando é do tipo 'seleção antes' e a seleção atual não basta (ele está desligado)."""
    if cmd not in SELECAO_PRIMEIRO or FreeCAD.ActiveDocument is None:
        return False
    try:
        return not FreeCADGui.Command.get(cmd).isActive()
    except Exception:
        return True


class PainelSelecao(P.PainelTarefa):
    """Painel genérico: caixas de seleção e, no OK, a função recebe as listas na ordem das caixas."""

    def __init__(self, titulo, instrucao, caixas, ao_confirmar, icone_cmd=None, adiar=True):
        self.adiar = adiar
        self.titulo = titulo
        self.ajuda = instrucao
        self.icone_cmd = icone_cmd
        self._specs = caixas
        self._ao_confirmar = ao_confirmar
        super().__init__()

    def montar(self):
        s = self.form.secao("Seleção", "selecao")
        self.caixas = []
        for rotulo, filtro, minimo, maximo in self._specs:
            f = FILTROS.get(filtro, filtro) if isinstance(filtro, str) else filtro
            self.caixas.append(self.form.caixa(s, rotulo, f, minimo=minimo, maximo=maximo))
        s.texto(self.ajuda)

    def _preencher_com_selecao(self):
        # a seleção anterior vai enchendo as caixas na ordem (base, depois ferramenta...)
        for sel in FreeCADGui.Selection.getSelectionEx("", 0):
            for obj, els, caminhos in P.agrupar_selecao(sel.Object, sel.SubElementNames):
                for c in self.caixas:
                    cheia = c.maximo is not None and len(c.valores()) >= c.maximo
                    if getattr(c.filtro, "caminho_completo", False):
                        alvo, subs = sel.Object, caminhos
                    else:
                        alvo, subs = obj, els
                    if not cheia and c.aceitar(alvo, subs):
                        break
        for c in self.caixas:
            if not c.pronta():
                self.form.ativar_caixa(c)
                break

    def distribuir(self, obj, subnomes=(), raiz=None, caminhos=None):
        c = super().distribuir(obj, subnomes, raiz, caminhos)
        # caixa cheia passa a vez para a próxima (como o "próxima seleção" do SolidWorks)
        if c is not None and c.maximo is not None and len(c.valores()) >= c.maximo:
            i = self.caixas.index(c)
            for prox in self.caixas[i + 1:] + self.caixas[:i]:
                if not prox.pronta():
                    self.form.ativar_caixa(prox)
                    break
        return c

    def executar(self):
        listas = [c.valores() for c in self.caixas]
        if self.adiar:
            # depois que o painel fechar: o passo seguinte costuma abrir outra janela ou painel
            from PySide import QtCore
            QtCore.QTimer.singleShot(0, lambda: self._ao_confirmar(*listas))
            return None
        return self._ao_confirmar(*listas)

    def accept(self):
        # sem transação própria: o comando chamado abre a dele
        falta = self.pendencia()
        if falta:
            self.form.mensagem.mostrar(falta, "erro")
            return False
        try:
            self.resultado = self.executar()
        except Exception as ex:
            self.form.mensagem.mostrar(str(ex), "erro")
            return False
        self._parar()
        return True


def pedir(titulo, instrucao, caixas, ao_confirmar, mostrar=True, adiar=True):
    """Abre o painel de seleção. ao_confirmar(lista1, lista2, ...) roda no OK (logo depois de o painel
    fechar, se adiar=True)."""
    p = PainelSelecao(titulo, instrucao, caixas, ao_confirmar, adiar=adiar)
    if mostrar:
        p.mostrar()
    return p


def rodar_com_selecao(cmd, *listas):
    """Põe a seleção na ordem das caixas e roda o comando do FreeCAD."""
    FreeCADGui.Selection.clearSelection()
    for lst in listas:
        for o in lst:
            FreeCADGui.Selection.addSelection(o)
    FreeCADGui.runCommand(cmd, 0)
    return True


def pedir_para_comando(cmd, mostrar=True, adiar=True):
    titulo, instrucao, caixas = SELECAO_PRIMEIRO[cmd]
    return pedir(titulo, instrucao, caixas, lambda *ls: rodar_com_selecao(cmd, *ls), mostrar, adiar)
