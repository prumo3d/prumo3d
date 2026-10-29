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
COLUNAS = ["Item", "Qtd.", "Código", "Denominação", "Material", "Dimensões (mm)", "Massa unit. (kg)",
           "Massa total (kg)", "Observação"]
LARGURAS = [40, 40, 90, 200, 130, 160, 105, 110, 120]
LETRAS = "ABCDEFGHI"
ULTIMA = LETRAS[len(COLUNAS) - 1]


class Linha:
    def __init__(self, chave, denominacao, material, dimensoes, massa, obs="", codigo=""):
        self.chave = chave
        self.codigo = codigo
        self.qtd = 0
        self.denominacao = denominacao
        self.material = material
        self.dimensoes = dimensoes
        self.massa = massa
        self.obs = obs

    @property
    def massa_total(self):
        return None if self.massa is None else self.massa * self.qtd


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


def _tubulacao():
    import PrumoTubulacao
    return PrumoTubulacao


def _e_tubulacao(obj):
    try:
        return _tubulacao().e_tubulacao(obj)
    except Exception:
        return False


# como cada item entra na lista (propriedade NaLista, escolhida em Propriedades da peça)
FABRICADO, COMPRADO, REFERENCIA = "Fabricado", "Comprado", "Referência"
TIPOS_NA_LISTA = (FABRICADO, COMPRADO, REFERENCIA)


def tipo_na_lista(obj):
    v = _prop(_alvo(obj), "NaLista") or _prop(obj, "NaLista")
    return v if v in TIPOS_NA_LISTA else FABRICADO


def _tem_tipos(objs):
    """Alguém marcou Comprado/Referência? (sem isso, a lista sai exatamente como antes)."""
    pilha, vistos = list(objs), set()
    while pilha:
        o = pilha.pop()
        k = (o.Document.Name, o.Name)
        if k in vistos:
            continue
        vistos.add(k)
        if tipo_na_lista(o) != FABRICADO:
            return True
        if PrumoUtil._eh_container(o):
            pilha.extend(PrumoUtil._filhos(o))
    return False


def itens(objs):
    """[(obj, forma, comprado?)]: peças com a posição no espaço, respeitando o tipo na lista:
    Referência não entra (nem o que tem dentro); Comprado entra como um item só (o que tem dentro, não)."""
    import Part
    if not _tem_tipos(objs):
        return [(o, sh, False) for o, sh in PrumoUtil.pecas(objs)]
    res = []
    for o in objs:
        t = tipo_na_lista(o)
        if t == REFERENCIA:
            continue
        if PrumoUtil._eh_container(o):
            if t == COMPRADO:
                ps = PrumoUtil.pecas([o])
                if ps:
                    res.append((o, Part.makeCompound([sh for _o, sh in ps]), True))
            else:
                res.extend(itens(PrumoUtil._filhos(o)))
            continue
        for oo, sh in PrumoUtil.pecas([o]):
            res.append((oo, sh, t == COMPRADO))
    return res


def coletar(objs, densidade_padrao=None):
    """Linhas da lista de materiais para os objetos (abre montagens, partes e grupos)."""
    if densidade_padrao is None:
        densidade_padrao = PrumoUtil.densidade_padrao()
    linhas = {}
    ordem = []
    for obj, sh, comprado in itens(objs):
        base = _alvo(obj)
        if "Perna" in base.PropertiesList and "Pecas" in base.PropertiesList:
            continue  # cordão de solda: vai para a lista de soldas
        if _e_tubulacao(base):
            # tubulação: um item por diâmetro de tubo (em barras) e por conexão
            for chave, den, mat, dim, qtd, obs in _tubulacao().linhas_bom(base):
                if chave not in linhas:
                    linhas[chave] = Linha(chave, den, mat, dim, None, obs)
                    ordem.append(chave)
                linhas[chave].qtd += qtd
            continue
        perfil = _prop(base, "Perfil")
        if perfil:
            comp = _prop(base, "ComprimentoCorte", "Comprimento")
            c = round(comp.Value if hasattr(comp, "Value") else float(comp or 0), 1)
            chave = ("perfil", str(perfil), c, str(_prop(base, "Material") or ""))
        elif _prop(base, "Denominacao") and "Espessura" in base.PropertiesList:
            # chapa da estrutura (reforço, tampa, placa de base): iguais pela descrição e material
            chave = ("chapa", str(base.Denominacao), str(_prop(base, "Material") or ""))
        elif _prop(base, "Denominacao") and "Norma" in base.PropertiesList:
            # peça padronizada (fixador): iguais pela descrição e material
            chave = ("padrao", str(base.Denominacao), str(_prop(base, "Material") or ""))
        elif _prop(base, "Codigo"):
            # peças com código (Propriedades da peça): iguais pelo código e material
            chave = ("codigo", str(base.Codigo), PrumoUtil.material(base)[0])
        else:
            chave = ("obj", base.Document.Name, base.Name)
        if chave not in linhas:
            nome_mat, dens, definido = PrumoUtil.material(base)
            if not definido:
                dens = densidade_padrao
            massa = sum(s.Volume for s in sh.Solids) * dens * 1e-9
            den = _prop(base, "Denominacao") or base.Label
            obs = _prop(base, "Observacao") or ("" if definido else "material a definir")
            if chave[0] == "chapa":
                # material em texto (como nas barras); massa pela densidade padrão (aço)
                mat_txt = _prop(base, "Material")
                nome_mat, definido = (mat_txt, True) if mat_txt else ("—", True)
                massa = sum(s.Volume for s in sh.Solids) * densidade_padrao * 1e-9
                obs = "" if mat_txt else "material a definir"
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
            acab = _prop(base, "Acabamento")
            if acab:
                obs = (obs + "; " if obs else "") + str(acab)
            if comprado:
                obs = "comprado" + ("; " + obs if obs and obs != "material a definir" else "")
            linhas[chave] = Linha(chave, den, nome_mat if definido else "—", _dimensoes(base, sh),
                                  massa, obs, str(_prop(base, "Codigo") or ""))
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
    cols = LETRAS
    for i, (nome, larg) in enumerate(zip(COLUNAS, LARGURAS)):
        sheet.set("%s1" % cols[i], nome)
        sheet.setColumnWidth(cols[i], larg)
    sheet.setStyle("A1:%s1" % ULTIMA, "bold")
    sheet.setBackground("A1:%s1" % ULTIMA, (0.0, 0.227, 0.439))
    sheet.setForeground("A1:%s1" % ULTIMA, (1.0, 1.0, 1.0))
    sheet.setAlignment("A1:%s1" % ULTIMA, "center|vcenter")
    total = 0.0
    for n, ln in enumerate(linhas, 1):
        r = n + 1
        sheet.set("A%d" % r, str(n))
        sheet.set("B%d" % r, str(ln.qtd))
        sheet.set("C%d" % r, "'" + (ln.codigo or ""))
        sheet.set("D%d" % r, "'" + ln.denominacao)
        sheet.set("E%d" % r, "'" + ln.material)
        sheet.set("F%d" % r, "'" + ln.dimensoes)
        sheet.set("G%d" % r, "'" + fmt(ln.massa, 3))
        sheet.set("H%d" % r, "'" + fmt(ln.massa_total, 3))
        sheet.set("I%d" % r, "'" + ln.obs)
        total += ln.massa_total or 0.0
    r = len(linhas) + 2
    sheet.set("G%d" % r, "Total")
    sheet.set("H%d" % r, "'" + fmt(total, 3))
    sheet.setStyle("G%d:H%d" % (r, r), "bold")
    sheet.setAlignment("A2:C%d" % r, "center|vcenter")
    sheet.setAlignment("G2:H%d" % r, "right|vcenter")
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
    larg = sum(sheet.getColumnWidth(c) for c in LETRAS[:len(COLUNAS)]) * PX_MM * escala
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
    vista.CellEnd = "%s%d" % (ULTIMA, n_linhas + 2)
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
