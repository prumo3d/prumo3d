# SPDX-License-Identifier: LGPL-2.1-or-later
"""Copiar projeto (como o Pack and Go do SolidWorks).

Copia o documento e todos os arquivos que ele usa (peças ligadas na montagem, subconjuntos) para
outra pasta, podendo renomear (prefixo, sufixo, troca de texto ou nome a nome), e acerta os
vínculos: a montagem copiada aponta para as peças copiadas. Os arquivos originais não mudam.

Funcionamento: salva cada documento com "Salvar como" na pasta nova, das peças para a montagem
(o FreeCAD atualiza os vínculos de quem ainda vai ser salvo). Depois fecha as cópias e reabre os
originais, ou deixa a cópia aberta se pedido.
"""

import os

import FreeCAD


def documentos(doc):
    """Documentos do projeto, das peças para a montagem (o próprio doc por último)."""
    try:
        return list(doc.getDependentDocuments(True))
    except TypeError:  # pragma: no cover (versões antigas)
        return list(doc.getDependentDocuments())


def nome_novo(caminho, prefixo="", sufixo="", trocar=("", "")):
    base = os.path.splitext(os.path.basename(caminho))[0]
    if trocar and trocar[0]:
        base = base.replace(trocar[0], trocar[1])
    return "%s%s%s.FCStd" % (prefixo, base, sufixo)


def plano(doc, pasta, prefixo="", sufixo="", trocar=("", ""), nomes=None):
    """[(documento, caminho original, caminho novo)] na ordem de cópia."""
    res = []
    usados = set()
    for d in documentos(doc):
        if not d.FileName:
            raise ValueError("salve %s antes de copiar o projeto" % d.Label)
        novo = (nomes or {}).get(d.FileName) or nome_novo(d.FileName, prefixo, sufixo, trocar)
        destino = os.path.join(pasta, novo)
        if os.path.normcase(destino) in usados:
            raise ValueError("dois arquivos ficariam com o mesmo nome: %s" % novo)
        if os.path.normcase(os.path.abspath(destino)) == os.path.normcase(os.path.abspath(d.FileName)):
            raise ValueError("a cópia de %s cairia em cima do original: mude a pasta ou o nome" % d.Label)
        usados.add(os.path.normcase(destino))
        res.append((d, d.FileName, destino))
    return res


def copiar_projeto(doc, pasta, prefixo="", sufixo="", trocar=("", ""), nomes=None, abrir_copia=False,
                   sobrescrever=False):
    """Copia o projeto. Retorna {caminho original: caminho novo}."""
    pasta = os.path.abspath(pasta)
    os.makedirs(pasta, exist_ok=True)
    passos = plano(doc, pasta, prefixo, sufixo, trocar, nomes)
    pendentes = [d.Label for d, _o, _n in passos if _modificado(d)]
    if pendentes:
        raise ValueError("salve antes as mudanças em: %s" % ", ".join(pendentes))
    existentes = [n for _d, _o, n in passos if os.path.exists(n)]
    if existentes and not sobrescrever:
        raise ValueError("já existe na pasta: %s" % ", ".join(os.path.basename(n) for n in existentes))
    principal_orig = doc.FileName
    mapa = {}
    for d, orig, novo in passos:
        d.saveAs(novo)
        mapa[orig] = novo
    principal_novo = mapa[principal_orig]
    # fecha as cópias (que agora estão abertas no lugar dos originais) e reabre o lado pedido
    for d, _o, _n in reversed(passos):
        try:
            FreeCAD.closeDocument(d.Name)
        except Exception:
            pass
    FreeCAD.openDocument(principal_novo if abrir_copia else principal_orig)
    return mapa


def _modificado(d):
    """Mudanças não salvas (marca da interface)."""
    try:
        import FreeCADGui
        gd = FreeCADGui.getDocument(d.Name)
        if gd is not None:
            return bool(gd.Modified)
    except Exception:
        pass
    return False


# ------------------------------------------------------------------ painel
def PainelCopiarProjeto(doc=None):
    import PrumoPainel as P
    from PySide import QtWidgets

    class _Painel(P.PainelTarefa):
        titulo = "Copiar projeto"
        ajuda = "Copia o documento e as peças que ele usa para outra pasta, renomeando e acertando os vínculos."

        def __init__(self):
            self.doc = doc or FreeCAD.ActiveDocument
            super().__init__()

        def montar(self):
            f = self.form
            s0 = f.secao("Destino", "folha")
            self.pasta = s0.linha("folha", QtWidgets.QLineEdit(), "Pasta onde as cópias vão ficar.", "Pasta")
            if self.doc is not None and self.doc.FileName:
                self.pasta.setText(os.path.join(os.path.dirname(self.doc.FileName), "copia"))
            bt = QtWidgets.QPushButton("Escolher pasta…")
            bt.clicked.connect(self._escolher)
            s0.widget(bt)
            s1 = f.secao("Nomes", "texto")
            self.prefixo = s1.linha("texto", QtWidgets.QLineEdit(), "Texto antes do nome de cada arquivo.",
                                    "Prefixo")
            self.sufixo = s1.linha("texto", QtWidgets.QLineEdit(), "Texto depois do nome (antes do .FCStd).",
                                   "Sufixo")
            self.de = s1.linha("lado", QtWidgets.QLineEdit(), "Trocar este texto nos nomes...", "Trocar")
            self.para = s1.linha("lado", QtWidgets.QLineEdit(), "...por este.", "Por")
            self.tabela = s1.widget(QtWidgets.QTableWidget(0, 2))
            self.tabela.setHorizontalHeaderLabels(["Arquivo", "Novo nome"])
            self.tabela.horizontalHeader().setStretchLastSection(True)
            self.tabela.setMinimumHeight(130)
            s2 = f.secao("Depois", "posicao")
            self.abrir = s2.linha("posicao", P.marcar("Abrir a cópia (senão, continua no original)"), "")
            for w in (self.prefixo, self.sufixo, self.de, self.para):
                w.textChanged.connect(lambda *_: self._preencher())
            self._preencher()

        def _escolher(self):
            p = QtWidgets.QFileDialog.getExistingDirectory(None, "Pasta da cópia", self.pasta.text())
            if p:
                self.pasta.setText(p)

        def _preencher(self):
            self.tabela.setRowCount(0)
            if self.doc is None:
                return
            for d in documentos(self.doc):
                if not d.FileName:
                    continue
                r = self.tabela.rowCount()
                self.tabela.insertRow(r)
                it = QtWidgets.QTableWidgetItem(os.path.basename(d.FileName))
                it.setData(32, d.FileName)
                self.tabela.setItem(r, 0, it)
                self.tabela.setItem(r, 1, QtWidgets.QTableWidgetItem(
                    nome_novo(d.FileName, self.prefixo.text(), self.sufixo.text(),
                              (self.de.text(), self.para.text()))))

        def nomes(self):
            res = {}
            for r in range(self.tabela.rowCount()):
                orig = self.tabela.item(r, 0).data(32)
                novo = self.tabela.item(r, 1).text().strip()
                if novo and not novo.lower().endswith(".fcstd"):
                    novo += ".FCStd"
                res[orig] = novo
            return res

        def pendencia(self):
            if self.doc is None or not self.doc.FileName:
                return "Salve o documento antes de copiar o projeto."
            if not self.pasta.text().strip():
                return "Escolha a pasta de destino."
            return None

        def pronto_texto(self):
            return "Pronto: %d arquivo(s) vão para %s." % (self.tabela.rowCount(), self.pasta.text().strip())

        def accept(self):
            # sem transação: a cópia salva e fecha documentos
            falta = self.pendencia()
            if falta:
                self.form.mensagem.mostrar(falta, "erro")
                return False
            try:
                self.resultado = copiar_projeto(self.doc, self.pasta.text().strip(), nomes=self.nomes(),
                                                abrir_copia=self.abrir.isChecked())
            except Exception as ex:
                self.form.mensagem.mostrar(str(ex), "erro")
                return False
            self._parar()
            FreeCAD.Console.PrintMessage("Prumo: projeto copiado (%d arquivos).\n" % len(self.resultado))
            return True

    return _Painel()


class CmdCopiarProjeto:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"), "MenuText": "Copiar projeto",
                "ToolTip": "Copia a montagem e as peças que ela usa para outra pasta, renomeando e mantendo os "
                           "vínculos (como o Pack and Go)."}

    def IsActive(self):
        d = FreeCAD.ActiveDocument
        return d is not None and bool(d.FileName)

    def Activated(self):
        PainelCopiarProjeto().mostrar()
