# SPDX-License-Identifier: LGPL-2.1-or-later
"""Verificar interferência (como no SolidWorks/Inventor): pares de peças que se invadem.

Para cada par de peças (já na posição da montagem), calcula o volume comum. Volume acima da
tolerância = interferência. Peças que só se encostam (volume zero) aparecem à parte, como
contato, se pedido. O resultado vai para um grupo "Interferências" com os volumes em vermelho.
"""

import FreeCAD

import PrumoUtil

TOLERANCIA_MM3 = 1e-3
NOME_GRUPO = "Interferencias"


class Interferencia:
    def __init__(self, a, b, volume, forma):
        self.a, self.b = a, b
        self.volume = volume
        self.forma = forma

    @property
    def texto(self):
        return "%s × %s: %s mm³" % (self.a.Label, self.b.Label, PrumoUtil.fmt(self.volume, 1))


def verificar(objs, tolerancia=TOLERANCIA_MM3, contatos=False):
    """[Interferencia] entre as peças dos objetos (montagens, partes e grupos são abertos).

    Com contatos=True, também lista os pares que só se tocam (volume 0)."""
    pecas = PrumoUtil.pecas(objs)
    res = []
    for i in range(len(pecas)):
        oa, sa = pecas[i]
        for j in range(i + 1, len(pecas)):
            ob, sb = pecas[j]
            if not sa.BoundBox.intersect(sb.BoundBox):
                continue
            try:
                comum = sa.common(sb)
                vol = comum.Volume if comum.Solids else 0.0
            except Exception:
                continue
            if vol > tolerancia:
                res.append(Interferencia(oa, ob, vol, comum))
            elif contatos:
                try:
                    if sa.distToShape(sb)[0] < 1e-6:
                        res.append(Interferencia(oa, ob, 0.0, None))
                except Exception:
                    pass
    res.sort(key=lambda x: -x.volume)
    return res


def mostrar(doc, interferencias):
    """Grupo "Interferências" com os volumes comuns em vermelho (substitui o anterior)."""
    antigo = doc.getObject(NOME_GRUPO)
    if antigo is not None:
        for o in list(antigo.Group):
            doc.removeObject(o.Name)
        doc.removeObject(antigo.Name)
    grupo = doc.addObject("App::DocumentObjectGroup", NOME_GRUPO)
    grupo.Label = "Interferências"
    for k, it in enumerate([x for x in interferencias if x.forma is not None], 1):
        o = doc.addObject("Part::Feature", "Interferencia%03d" % k)
        o.Shape = it.forma
        o.Label = "Interferência %d — %s × %s" % (k, it.a.Label, it.b.Label)
        grupo.addObject(o)
        try:
            vo = o.ViewObject
            vo.ShapeColor = (0.85, 0.12, 0.10)
            vo.Transparency = 20
            vo.LineColor = (0.6, 0.0, 0.0)
        except Exception:
            pass
    doc.recompute()
    return grupo


# ------------------------------------------------------------------ painel
def _filtro(obj, subs):
    return [(obj.Label, obj)] if PrumoUtil.tem_peca([obj]) else []


def PainelInterferencia():
    import PrumoPainel as P
    from PySide import QtWidgets
    import FreeCADGui

    class _Painel(P.PainelTarefa):
        titulo = "Verificar interferência"
        ajuda = "Escolha a montagem (ou as peças) e clique em Verificar. Sem seleção, verifica o documento inteiro."

        def montar(self):
            f = self.form
            s0 = f.secao("Peças", "selecao")
            self.pecas = f.caixa(s0, "Montagem ou peças", _filtro, minimo=0)
            s1 = f.secao("Opções", "folga")
            self.tol = s1.linha("folga", P.numero(TOLERANCIA_MM3, 0.0, 1e6, " mm³", 3),
                                "Volumes comuns menores que isto são ignorados.", "Tolerância")
            self.contatos = s1.linha("lado", P.marcar("Mostrar também peças que só se encostam"), "")
            bt = QtWidgets.QPushButton("Verificar")
            bt.clicked.connect(self.verificar)
            s1.widget(bt)
            s2 = f.secao("Resultado", "info")
            self.lista = s2.widget(QtWidgets.QListWidget())
            self.lista.setMinimumHeight(140)
            self.lista.currentRowChanged.connect(self._selecionar)
            self.resultado = []

        def pendencia(self):
            return None

        def pronto_texto(self):
            return "Clique em Verificar. OK fecha (o grupo Interferências fica na árvore)."

        def _alvos(self):
            vs = self.pecas.valores()
            if vs:
                return vs
            doc = FreeCAD.ActiveDocument
            return [o for o in doc.RootObjects if PrumoUtil.tem_peca([o]) and o.Name != NOME_GRUPO] if doc else []

        def verificar(self):
            self.resultado = verificar(self._alvos(), self.tol.value(), self.contatos.isChecked())
            self.lista.clear()
            n = len([x for x in self.resultado if x.volume > 0])
            for it in self.resultado:
                self.lista.addItem(it.texto if it.volume > 0 else "%s × %s: só encostam" % (it.a.Label, it.b.Label))
            if FreeCAD.ActiveDocument is not None:
                mostrar(FreeCAD.ActiveDocument, self.resultado)
            if n:
                self.form.mensagem.mostrar("%d interferência(s) encontrada(s)." % n, "erro")
            else:
                self.form.mensagem.mostrar("Nenhuma interferência.", "ok")
            return self.resultado

        def _selecionar(self, r):
            if 0 <= r < len(self.resultado):
                it = self.resultado[r]
                FreeCADGui.Selection.clearSelection()
                FreeCADGui.Selection.addSelection(it.a)
                FreeCADGui.Selection.addSelection(it.b)

        def executar(self):
            if not self.resultado:
                self.verificar()
            return self.resultado

        def accept(self):
            self.executar()
            self._parar()
            return True

    return _Painel()


class CmdInterferencia:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("massa.svg"), "MenuText": "Verificar interferência",
                "ToolTip": "Procura peças que se invadem na montagem e mostra o volume comum em vermelho."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelInterferencia().mostrar()
