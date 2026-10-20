# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - lista de materiais automática (planilha + tabela na folha de desenho).
"""Lista de materiais (LM).

Junta as peças da montagem (ou da seleção, ou do documento) contando as repetidas, com material,
dimensões e massa. O resultado vai para uma planilha "Lista de materiais" que se atualiza com o
comando de novo e pode ser colocada na folha de desenho como tabela.
"""

import FreeCAD
import FreeCADGui

import PrumoUtil
from PrumoUtil import fmt, fmt_dim

try:
    from PySide import QtWidgets
except ImportError:  # pragma: no cover
    from PySide2 import QtWidgets

NOME_PLANILHA = "ListaDeMateriais"
COLUNAS = ["Item", "Qtd.", "Denominação", "Material", "Dimensões (mm)", "Massa unit. (kg)",
           "Massa total (kg)", "Observação"]
LARGURAS = [40, 40, 220, 140, 170, 115, 120, 140]


class Linha:
    def __init__(self, chave, denominacao, material, dimensoes, massa, obs=""):
        self.chave = chave
        self.qtd = 0
        self.denominacao = denominacao
        self.material = material
        self.dimensoes = dimensoes
        self.massa = massa
        self.obs = obs

    @property
    def massa_total(self):
        return self.massa * self.qtd


def _alvo(obj):
    if obj.TypeId == "App::Link" and obj.LinkedObject is not None:
        return obj.LinkedObject
    return obj


def _prop(obj, *nomes):
    for n in nomes:
        if n in obj.PropertiesList:
            v = getattr(obj, n)
            if v not in (None, ""):
                return v
    return None


def _dimensoes(obj, sh):
    """Texto de dimensões: perfil e comprimento, chapa e espessura, ou caixa envolvente."""
    perfil = _prop(obj, "Perfil")
    comp = _prop(obj, "ComprimentoCorte", "Comprimento")
    if perfil:
        c = comp.Value if hasattr(comp, "Value") else comp
        return "%s × %s" % (perfil, fmt_dim(c)) if c else str(perfil)
    esp = _prop(obj, "Espessura", "thickness")
    if esp is not None:
        e = esp.Value if hasattr(esp, "Value") else float(esp)
        bb = sh.BoundBox
        lados = sorted([bb.XLength, bb.YLength, bb.ZLength], reverse=True)
        return "Chapa %s — %s × %s" % (fmt_dim(e), fmt_dim(lados[0]), fmt_dim(lados[1]))
    # caixa envolvente no sistema da própria peça (sem a posição na montagem)
    try:
        sh0 = obj.Shape.copy()
        sh0.Placement = FreeCAD.Placement()
        bb = sh0.BoundBox
    except Exception:
        bb = sh.BoundBox
    lados = sorted([bb.XLength, bb.YLength, bb.ZLength], reverse=True)
    return " × ".join(fmt_dim(x) for x in lados)


def coletar(objs, densidade_padrao=None):
    """Linhas da lista de materiais para os objetos (abre montagens, partes e grupos)."""
    if densidade_padrao is None:
        densidade_padrao = PrumoUtil.densidade_padrao()
    linhas = {}
    ordem = []
    for obj, sh in PrumoUtil.pecas(objs):
        base = _alvo(obj)
        perfil = _prop(base, "Perfil")
        if perfil:
            comp = _prop(base, "ComprimentoCorte", "Comprimento")
            c = round(comp.Value if hasattr(comp, "Value") else float(comp or 0), 1)
            chave = ("perfil", str(perfil), c, str(_prop(base, "Material") or ""))
        elif _prop(base, "Denominacao") and "Norma" in base.PropertiesList:
            # peça padronizada (fixador): iguais pela descrição e material
            chave = ("padrao", str(base.Denominacao), str(_prop(base, "Material") or ""))
        else:
            chave = ("obj", base.Document.Name, base.Name)
        if chave not in linhas:
            nome_mat, dens, definido = PrumoUtil.material(base)
            if not definido:
                dens = densidade_padrao
            massa = sum(s.Volume for s in sh.Solids) * dens * 1e-9
            den = _prop(base, "Denominacao") or base.Label
            obs = _prop(base, "Observacao") or ("" if definido else "material a definir")
            if chave[0] == "padrao":
                mat_txt = _prop(base, "Material")
                nome_mat, definido = (mat_txt or "—", True)
                obs = "" if _prop(base, "SituacaoDados") in (None, "confirmado") else "dimensões a conferir"
            if perfil:
                # barra de perfil: massa linear do catálogo × comprimento; material em texto
                if "Massa" in base.PropertiesList and base.Massa:
                    massa = float(base.Massa)
                mat_txt = _prop(base, "Material")
                nome_mat, definido = (mat_txt, True) if mat_txt else ("—", True)
                den = "Barra " + str(perfil)
                obs = "" if _prop(base, "SituacaoDados") in (None, "confirmado") else "perfil a conferir"
            linhas[chave] = Linha(chave, den, nome_mat if definido else "—", _dimensoes(base, sh),
                                  massa, obs)
            ordem.append(chave)
        linhas[chave].qtd += 1
    return [linhas[k] for k in ordem]


def gravar_planilha(doc, linhas, titulo="Lista de materiais"):
    """Cria ou atualiza a planilha da lista de materiais. Retorna a planilha."""
    sheet = doc.getObject(NOME_PLANILHA)
    if sheet is None:
        sheet = doc.addObject("Spreadsheet::Sheet", NOME_PLANILHA)
        sheet.Label = titulo
    else:
        sheet.clearAll()
    cols = "ABCDEFGH"
    for i, (nome, larg) in enumerate(zip(COLUNAS, LARGURAS)):
        sheet.set("%s1" % cols[i], nome)
        sheet.setColumnWidth(cols[i], larg)
    sheet.setStyle("A1:H1", "bold")
    sheet.setBackground("A1:H1", (0.0, 0.227, 0.439))
    sheet.setForeground("A1:H1", (1.0, 1.0, 1.0))
    sheet.setAlignment("A1:H1", "center|vcenter")
    total = 0.0
    for n, ln in enumerate(linhas, 1):
        r = n + 1
        sheet.set("A%d" % r, str(n))
        sheet.set("B%d" % r, str(ln.qtd))
        sheet.set("C%d" % r, "'" + ln.denominacao)
        sheet.set("D%d" % r, "'" + ln.material)
        sheet.set("E%d" % r, "'" + ln.dimensoes)
        sheet.set("F%d" % r, "'" + fmt(ln.massa, 3))
        sheet.set("G%d" % r, "'" + fmt(ln.massa_total, 3))
        sheet.set("H%d" % r, "'" + ln.obs)
        total += ln.massa_total
    r = len(linhas) + 2
    sheet.set("F%d" % r, "Total")
    sheet.set("G%d" % r, "'" + fmt(total, 3))
    sheet.setStyle("F%d:G%d" % (r, r), "bold")
    sheet.setAlignment("A2:B%d" % r, "center|vcenter")
    sheet.setAlignment("F2:G%d" % r, "right|vcenter")
    doc.recompute()
    return sheet


ALTURA_LINHA_MM = 5.0   # altura de cada linha da tabela na folha
PX_MM = 25.4 / 96.0     # o TechDraw desenha a planilha com as medidas em pixels a 96 ppp
TEXTO_MM = 2.5          # altura do texto na folha (NBR 8402: 2,5 mm)


def _desc_do_modelo(page):
    try:
        with open(page.Template.Template, encoding="utf-8") as fh:
            return fh.read(4000)
    except Exception:
        return ""


def margens_da_folha(page):
    """(esquerda, direita, superior, inferior) em mm, lidas do modelo Prumo; padrão 20/10/10/10."""
    import re
    m = re.search(r"esquerda ([\d.]+), direita ([\d.]+), superior ([\d.]+), inferior ([\d.]+)",
                  _desc_do_modelo(page))
    return tuple(float(x) for x in m.groups()) if m else (20.0, 10.0, 10.0, 10.0)


def altura_legenda(page):
    """Altura da legenda (mm) do modelo Prumo, ou None se não for um modelo Prumo."""
    import re
    m = re.search(r"Legenda [\d.]+ × ([\d.]+) mm", _desc_do_modelo(page))
    return float(m.group(1)) if m else None


def tamanho_tabela(sheet, n_linhas, escala):
    """(largura, altura) da tabela na folha, em mm."""
    larg = sum(sheet.getColumnWidth(c) for c in "ABCDEFGH") * PX_MM * escala
    alt = sum(sheet.getRowHeight(str(r)) for r in range(1, n_linhas + 3)) * PX_MM * escala
    return larg, alt


def inserir_na_folha(page, sheet, n_linhas):
    """Coloca a planilha na folha como tabela: logo acima da legenda, alinhada à direita do quadro
    (folhas Prumo), ou no canto superior direito do quadro (outros modelos).

    As larguras e alturas da planilha são em pixels; a vista é reduzida para que cada linha fique
    com ALTURA_LINHA_MM e o texto com TEXTO_MM na folha."""
    doc = page.Document
    nome = "TabelaListaDeMateriais"
    vista = None
    for v in page.Views:
        if v.TypeId == "TechDraw::DrawViewSpreadsheet" and v.Source == sheet:
            vista = v
    if vista is None:
        vista = doc.addObject("TechDraw::DrawViewSpreadsheet", nome)
        vista.Label = "Lista de materiais"
        vista.Source = sheet
        page.addView(vista)
    vista.CellStart = "A1"
    vista.CellEnd = "H%d" % (n_linhas + 2)
    alt_px = float(sheet.getRowHeight("1")) or 30.0
    escala = ALTURA_LINHA_MM / (alt_px * PX_MM)
    try:
        vista.ScaleType = "Custom"
    except Exception:
        pass
    vista.Scale = escala
    vista.TextSize = TEXTO_MM / (PX_MM * escala)
    vista.LineWidth = 0.35 / PX_MM  # a espessura do traço não acompanha a escala da vista
    try:
        larg = float(page.Template.Width)
        alt = float(page.Template.Height)
        _e, d, sup, inf = margens_da_folha(page)
        w, h = tamanho_tabela(sheet, n_linhas, escala)
        h_leg = altura_legenda(page)
        vista.X = larg - d - w / 2.0
        if h_leg is not None:
            vista.Y = inf + h_leg + 3.0 + h / 2.0   # TechDraw: Y a partir da borda de baixo
        else:
            vista.X = larg - d - 5.0 - w / 2.0
            vista.Y = alt - sup - 5.0 - h / 2.0
    except Exception as exc:
        FreeCAD.Console.PrintLog("Prumo: posição da lista na folha: %s\n" % exc)
    doc.recompute()
    return vista


def _objetos_alvo():
    sel = FreeCADGui.Selection.getSelection()
    if sel:
        return sel
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return []
    montagens = [o for o in doc.Objects if o.TypeId == "Assembly::AssemblyObject"]
    if montagens:
        return montagens[:1]
    return [o for o in doc.RootObjects if o.TypeId not in ("App::Origin", "Spreadsheet::Sheet")
            and not o.isDerivedFrom("TechDraw::DrawPage")]


class CmdListaMateriais:
    def GetResources(self):
        return {"Pixmap": PrumoUtil.icone("lista_materiais.svg"),
                "MenuText": "Lista de materiais",
                "ToolTip": "Cria (ou atualiza) a planilha da lista de materiais da montagem, da "
                           "seleção ou do documento: quantidade, material, dimensões e massa. "
                           "Com uma folha de desenho aberta, coloca a tabela na folha."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        objs = _objetos_alvo()
        linhas = coletar(objs)
        if not linhas:
            QtWidgets.QMessageBox.information(FreeCADGui.getMainWindow(), "Lista de materiais",
                                              "Nenhuma peça encontrada.")
            return
        doc.openTransaction("Lista de materiais")
        sheet = gravar_planilha(doc, linhas)
        pages = [o for o in doc.Objects if o.isDerivedFrom("TechDraw::DrawPage")]
        page = None
        try:
            mdi = FreeCADGui.getMainWindow().centralWidget().activeSubWindow()
            titulo = mdi.windowTitle() if mdi else ""
            page = next((p for p in pages if p.Label in titulo), None)
        except Exception:
            page = None
        if page is not None:
            inserir_na_folha(page, sheet, len(linhas))
        doc.commitTransaction()
        FreeCAD.Console.PrintMessage("Prumo: lista de materiais com %d itens em '%s'.\n"
                                     % (len(linhas), sheet.Label))
