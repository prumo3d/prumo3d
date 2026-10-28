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
    def __init__(self, a, b, volume, forma, distancia=0.0):
        self.a, self.b = a, b
        self.volume = volume
        self.forma = forma
        self.distancia = distancia      # > 0: não se tocam, mas estão mais perto que a folga pedida

    @property
    def texto(self):
        if self.volume > 0:
            return "%s × %s: %s mm³" % (self.a.Label, self.b.Label, PrumoUtil.fmt(self.volume, 1))
        if self.distancia > 0:
            return "%s × %s: folga de %s mm" % (self.a.Label, self.b.Label, PrumoUtil.fmt(self.distancia, 2))
        return "%s × %s: só encostam" % (self.a.Label, self.b.Label)


def verificar(objs, tolerancia=TOLERANCIA_MM3, contatos=False, folga=0.0):
    """[Interferencia] entre as peças dos objetos (montagens, partes e grupos são abertos).

    Com contatos=True, também lista os pares que só se tocam (volume 0). Com folga > 0 (mm), lista também os
    pares que não se tocam mas ficam mais perto que isso (a "Clearance" do Fusion e do SolidCraft)."""
    pecas = PrumoUtil.pecas(objs)
    res = []
    for i in range(len(pecas)):
        oa, sa = pecas[i]
        for j in range(i + 1, len(pecas)):
            ob, sb = pecas[j]
            ba = FreeCAD.BoundBox(sa.BoundBox)
            if folga > 0:
                ba.enlarge(folga)
            if not ba.intersect(sb.BoundBox):
                continue
            try:
                comum = sa.common(sb)
                vol = comum.Volume if comum.Solids else 0.0
            except Exception:
                continue
            if vol > tolerancia:
                res.append(Interferencia(oa, ob, vol, comum))
            elif contatos or folga > 0:
                try:
                    d = sa.distToShape(sb)[0]
                except Exception:
                    continue
                if d < 1e-6:
                    if contatos:
                        res.append(Interferencia(oa, ob, 0.0, None))
                elif d < folga:
                    res.append(Interferencia(oa, ob, 0.0, None, d))
    # interferências (maior volume primeiro), depois as folgas (menor primeiro), depois os contatos
    res.sort(key=lambda x: (0, -x.volume) if x.volume > 0 else ((1, x.distancia) if x.distancia > 0 else (2, 0)))
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
def _eh_resultado(obj):
    """Sólidos vermelhos do grupo Interferências (não são peças da montagem)."""
    try:
        return obj.Name == NOME_GRUPO or any(p.Name == NOME_GRUPO for p in obj.InList)
    except Exception:
        return False


def _filtro(obj, subs):
    if _eh_resultado(obj):
        return []
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
            self.folga = s1.linha("folga", P.numero(0.0, 0.0, 1000.0, " mm", 2),
                                  "Avisa também os pares que não se tocam mas ficam mais perto que isto "
                                  "(0 = não conferir folga).", "Folga mínima")
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
            return [o for o in doc.RootObjects if PrumoUtil.tem_peca([o]) and not _eh_resultado(o)] if doc else []

        def verificar(self):
            self.resultado = verificar(self._alvos(), self.tol.value(), self.contatos.isChecked(),
                                       self.folga.value())
            self.lista.clear()
            n = len([x for x in self.resultado if x.volume > 0])
            nf = len([x for x in self.resultado if x.distancia > 0])
            for it in self.resultado:
                self.lista.addItem(it.texto)
            if FreeCAD.ActiveDocument is not None:
                mostrar(FreeCAD.ActiveDocument, self.resultado)
            extra = (" %d par(es) com folga menor que %s mm." % (nf, PrumoUtil.fmt(self.folga.value(), 2))) \
                if nf else ""
            if n:
                self.form.mensagem.mostrar("%d interferência(s) encontrada(s).%s" % (n, extra), "erro")
            elif nf:
                self.form.mensagem.mostrar("Nenhuma interferência." + extra, "info")
            else:
                self.form.mensagem.mostrar("Nenhuma interferência.", "ok")
            return self.resultado

        def _selecionar(self, r):
            if 0 <= r < len(self.resultado):
                it = self.resultado[r]
                # só mostra o par: não muda o que vai ser verificado
                self.selecionar_sem_preencher([it.a, it.b])

        def executar(self):
            if not self.resultado:
                self.verificar()
            return self.resultado

        def accept(self):
            try:
                self.executar()
            except Exception as ex:
                self.form.mensagem.mostrar(str(ex), "erro")
                return False
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
