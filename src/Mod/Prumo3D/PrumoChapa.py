# SPDX-License-Identifier: LGPL-2.1-or-later
"""Chapa metálica: fator K por material, espessuras comerciais e planificação em DXF num clique.

Fator K (posição da linha neutra na dobra a ar, padrão ANSI: 0,5 = meio da espessura):
- Aço carbono, inox e alumínio: valores de partida da Durma (fabricante de dobradeiras), por faixa
  de r/t (raio interno / espessura). Fonte: durmapress.com, "K factor in press brake bending".
- DIN 6935 (geral): k = 0,65 + 0,5·log10(r/t) para r/t ≤ 5 (k = 1 acima), convertido para ANSI
  (K = k/2). Fontes: de.wiki.li/Biegeverkürzung, spi.de "ABC der Blechabwicklung",
  modulusmetal.com "DIN 6935".
São valores de partida: confirme com uma dobra de teste na dobradeira que vai fazer a peça.

Raio interno mínimo recomendado (Durma, "minimum bend radius"): aço carbono 1,0·t, inox 1,5·t,
alumínio 5052 0,8·t, alumínio 6061 1,5·t.

Espessuras comerciais (mm): chapa fina de aço em bitola MSG e chapa grossa métrica de usina
(ArcelorMittal, Usiminas; tabela Fábrica do Projeto), inox em bitola USG (Copper Metal) e
alumínio (Alumiangel, Shock Metais). Consultadas em 20/10/2026.
"""

import math
import os

import FreeCAD

FONTE_DURMA = "Durma (durmapress.com) — valores de partida, confirme com dobra de teste"
FONTE_DIN = "DIN 6935, k = 0,65 + 0,5·log10(r/t) convertido para ANSI (K = k/2)"

# chave = r/t máximo da faixa (como as tabelas do SheetMetal): vale para r/t ≤ chave
TABELAS_K = {
    "Aço carbono": ({1.0: 0.40, 3.0: 0.44, 1000.0: 0.50}, FONTE_DURMA),
    "Aço inoxidável": ({1.0: 0.42, 3.0: 0.46, 1000.0: 0.50}, FONTE_DURMA),
    "Alumínio": ({1.0: 0.33, 3.0: 0.40, 1000.0: 0.50}, FONTE_DURMA),
    "DIN 6935 (geral)": ({0.65: 0.28, 0.8: 0.30, 1.0: 0.325, 1.5: 0.37, 2.0: 0.40, 2.5: 0.42, 3.0: 0.44,
                          4.0: 0.48, 1000.0: 0.50}, FONTE_DIN),
}

RAIO_MINIMO = {"Aço carbono": 1.0, "Aço inoxidável": 1.5, "Alumínio 5052": 0.8, "Alumínio 6061": 1.5,
               "Alumínio": 1.5}   # família sem liga definida: o pior caso (6061)

# (espessura mm, designação comercial)
ESPESSURAS = {
    "Aço carbono": [(0.45, "#26"), (0.60, "#24"), (0.75, "#22"), (0.90, "#20"), (1.06, "#19"), (1.20, "#18"),
                    (1.50, "#16"), (1.90, "#14"), (2.00, ""), (2.25, "#13"), (2.65, "#12"), (3.00, "#11"),
                    (3.35, "#10"), (3.75, "#9"), (4.25, "#8"), (4.50, "#7"), (4.75, '3/16"'), (6.30, '1/4"'),
                    (8.00, '5/16"'), (9.50, '3/8"'), (12.50, '1/2"'), (16.00, '5/8"'), (19.00, '3/4"')],
    "Aço inoxidável": [(0.40, "USG 28"), (0.46, "USG 26"), (0.64, "USG 24"), (0.79, "USG 22"),
                       (0.95, "USG 20"), (1.27, "USG 18"), (1.56, "USG 16"), (1.98, "USG 14"),
                       (2.78, "USG 12"), (3.18, "USG 11"), (3.57, "USG 10"), (3.97, "USG 9"), (4.76, "USG 7"),
                       (6.35, '1/4"'), (7.93, '5/16"'), (9.53, '3/8"'), (12.70, '1/2"')],
    "Alumínio": [(0.30, ""), (0.40, ""), (0.50, ""), (0.80, ""), (1.00, ""), (1.20, ""), (1.50, ""), (2.00, ""),
                 (3.00, ""), (4.76, '3/16"'), (5.00, ""), (6.35, '1/4"'), (10.00, "")],
}


def k_fator(material, raio, espessura):
    """Fator K (ANSI) para o material e a razão r/t."""
    tabela = TABELAS_K.get(material, TABELAS_K["DIN 6935 (geral)"])[0]
    if espessura <= 0:
        raise ValueError("espessura deve ser maior que zero")
    rt = raio / espessura
    for chave in sorted(tabela):
        if rt <= chave:
            return tabela[chave]
    return tabela[max(tabela)]


def k_din(raio, espessura):
    """K pela fórmula da DIN 6935 (contínuo), em ANSI."""
    rt = raio / espessura
    if rt <= 0:
        return 0.0
    if rt > 5:
        return 0.5
    return (0.65 + 0.5 * math.log10(rt)) / 2.0


def raio_minimo(material, espessura, nome=""):
    """Raio interno mínimo recomendado. nome: material da peça (ex.: "Alumínio 5052-H32"),
    para pegar a liga dentro da família."""
    for chave in RAIO_MINIMO:
        liga = chave.split(" ", 1)[1] if chave.startswith("Alumínio ") else None
        if liga and material == "Alumínio" and liga in (nome or ""):
            return RAIO_MINIMO[chave] * espessura
    return RAIO_MINIMO.get(material, 1.0) * espessura


def espessura_comercial(material, valor):
    """(espessura, designação) comercial mais próxima."""
    lst = ESPESSURAS.get(material, ESPESSURAS["Aço carbono"])
    return min(lst, key=lambda e: abs(e[0] - valor))


def familia_do_material(nome):
    n = (nome or "").lower()
    if "inox" in n or "aisi" in n or "304" in n or "316" in n or "430" in n:
        return "Aço inoxidável"
    if "alum" in n:
        return "Alumínio"
    return "Aço carbono"


# ------------------------------------------------------------------ tabela para o SheetMetal
def criar_tabela_k(doc, material):
    """Planilha de fator K no formato do SheetMetal (rótulo material_<nome>): aparece na lista de
    tabelas do Planificar. Retorna a planilha."""
    tabela, fonte = TABELAS_K[material]
    rotulo = "material_" + "".join(c if c.isalnum() else "_" for c in material).strip("_")
    for o in doc.getObjectsByLabel(rotulo):
        doc.removeObject(o.Name)
    sh = doc.addObject("Spreadsheet::Sheet", "FatorK")
    sh.Label = rotulo
    sh.set("A1", "Radius / Thickness")
    sh.set("B1", "K-factor (ANSI)")
    for i, chave in enumerate(sorted(tabela), 2):
        sh.set("A%d" % i, str(chave))
        sh.set("B%d" % i, str(tabela[chave]))
    # o padrão (ANSI) vai no título da coluna; a fonte fica numa nota ao lado
    sh.set("D1", "'Fonte")
    sh.set("E1", "'" + fonte)
    sh.setColumnWidth("A", 130)
    sh.setColumnWidth("D", 130)
    doc.recompute()
    return sh


# ------------------------------------------------------------------ planificação
def face_base(obj):
    """Nome da maior face plana (a face de apoio para planificar)."""
    melhor, area = None, -1.0
    for i, f in enumerate(obj.Shape.Faces, 1):
        try:
            plana = f.Surface.isPlanar() if hasattr(f.Surface, "isPlanar") else "Plane" in f.Surface.TypeId
        except Exception:
            plana = "Plane" in str(type(f.Surface))
        if plana and f.Area > area:
            melhor, area = "Face%d" % i, f.Area
    if melhor is None:
        raise ValueError("%s não tem face plana para apoiar a planificação" % obj.Label)
    return melhor


def espessura_raio(obj):
    """(espessura, raio interno) do objeto de chapa, pelas propriedades (SheetMetal)."""
    t = r = None
    for n in ("thickness", "Thickness", "Espessura"):
        if n in obj.PropertiesList:
            v = getattr(obj, n)
            t = float(v.Value if hasattr(v, "Value") else v)
            break
    for n in ("radius", "Radius", "Raio"):
        if n in obj.PropertiesList:
            v = getattr(obj, n)
            r = float(v.Value if hasattr(v, "Value") else v)
            break
    return t, r


def planificar(obj, material="Aço carbono", face=None):
    """(forma planificada, linhas de dobra, normal da face base)."""
    import SheetMetalUnfolder
    tabela = TABELAS_K[material][0]
    face = face or face_base(obj)
    res = SheetMetalUnfolder.getUnfold(dict(tabela), obj, face, "ansi")
    forma, dobras, normal = res[0], res[1], res[2]
    if forma is None:
        raise ValueError("não foi possível planificar %s (código %s)" % (obj.Label, res[4]))
    return forma, dobras, normal


def _no_plano_xy(forma, dobras, normal):
    """Leva a face de baixo da planificação para o plano XY (z = 0)."""
    import Part
    rot = FreeCAD.Rotation(normal, FreeCAD.Vector(0, 0, 1))
    faces = [f for f in forma.Faces
             if abs(abs(f.normalAt(0, 0).dot(normal)) - 1.0) < 1e-6]
    alvo = max(faces, key=lambda f: f.Area)
    m = FreeCAD.Placement(FreeCAD.Vector(), rot).toMatrix()
    # transformação rígida (transformShape): furos e raios continuam círculos e arcos no DXF;
    # transformGeometry converteria tudo em BSpline (e o DXF sairia em segmentos de reta)
    face = alvo.copy()
    face.transformShape(m)
    bb = face.BoundBox
    desl = FreeCAD.Vector(-bb.XMin, -bb.YMin, -bb.ZMin)
    face.translate(desl)
    linhas = []
    if dobras is not None and dobras.Edges:
        d = dobras.copy()
        d.transformShape(m)
        d.translate(desl)
        linhas = d.Edges
    return face, linhas


# ------------------------------------------------------------------ DXF (R12, sem dependências)
def _dxf_entidades(arestas, camada):
    out = []
    for e in arestas:
        c = e.Curve
        nome = type(c).__name__
        if nome in ("Line", "LineSegment"):
            a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
            out += ["0", "LINE", "8", camada, "10", "%.4f" % a.x, "20", "%.4f" % a.y, "30", "0.0",
                    "11", "%.4f" % b.x, "21", "%.4f" % b.y, "31", "0.0"]
        elif nome == "Circle" and e.isClosed():
            out += ["0", "CIRCLE", "8", camada, "10", "%.4f" % c.Center.x, "20", "%.4f" % c.Center.y, "30", "0.0",
                    "40", "%.4f" % c.Radius]
        elif nome == "Circle":
            # ARC do DXF vai sempre no sentido anti-horário: com o eixo para baixo, troca as pontas
            p0, p1 = e.valueAt(e.FirstParameter), e.valueAt(e.LastParameter)
            ini = math.degrees(math.atan2(p0.y - c.Center.y, p0.x - c.Center.x)) % 360.0
            fim = math.degrees(math.atan2(p1.y - c.Center.y, p1.x - c.Center.x)) % 360.0
            if c.Axis.z < 0:
                ini, fim = fim, ini
            out += ["0", "ARC", "8", camada, "10", "%.4f" % c.Center.x, "20", "%.4f" % c.Center.y, "30", "0.0",
                    "40", "%.4f" % c.Radius, "50", "%.4f" % ini, "51", "%.4f" % fim]
        else:
            pts = e.discretize(Deflection=0.01)
            for a, b in zip(pts[:-1], pts[1:]):
                out += ["0", "LINE", "8", camada, "10", "%.4f" % a.x, "20", "%.4f" % a.y, "30", "0.0",
                        "11", "%.4f" % b.x, "21", "%.4f" % b.y, "31", "0.0"]
    return out


def escrever_dxf(caminho, contorno, dobras=()):
    """DXF R12 com as camadas CONTORNO (corte) e DOBRAS (linhas de dobra)."""
    cab = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4",
           "0", "ENDSEC",
           "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", "2",
           "0", "LAYER", "2", "CONTORNO", "70", "0", "62", "7", "6", "CONTINUOUS",
           "0", "LAYER", "2", "DOBRAS", "70", "0", "62", "1", "6", "CONTINUOUS",
           "0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    corpo = _dxf_entidades(contorno, "CONTORNO") + _dxf_entidades(dobras, "DOBRAS")
    fim = ["0", "ENDSEC", "0", "EOF"]
    with open(caminho, "w", encoding="ascii", newline="\r\n") as f:
        f.write("\n".join(cab + corpo + fim) + "\n")
    return caminho


def exportar_dxf(obj, caminho=None, material=None, face=None):
    """Planifica a chapa e grava o DXF (contorno + dobras). Retorna (caminho, face plana, info)."""
    if material is None:
        try:
            import PrumoUtil
            material = familia_do_material(PrumoUtil.material(obj)[0])
        except Exception:
            material = "Aço carbono"
    forma, dobras, normal = planificar(obj, material, face)
    plana, linhas = _no_plano_xy(forma, dobras, normal)
    if caminho is None:
        pasta = os.path.dirname(obj.Document.FileName) if obj.Document.FileName else os.path.expanduser("~")
        caminho = os.path.join(pasta, "%s_planificada.dxf" % obj.Label.replace(" ", "_"))
    escrever_dxf(caminho, plana.Edges, linhas)
    t, r = espessura_raio(obj)
    info = {"material": material, "largura": plana.BoundBox.XLength, "altura": plana.BoundBox.YLength,
            "dobras": len(linhas), "espessura": t, "raio": r,
            "k": k_fator(material, r, t) if (t and r is not None) else None}
    return caminho, plana, info


# ------------------------------------------------------------------ interface
def _filtro_chapa(obj, subs):
    try:
        if obj.Shape.Solids and any("Plane" in type(f.Surface).__name__ for f in obj.Shape.Faces):
            return [(obj.Label, (obj, next((s for s in subs if s.startswith("Face")), None)))]
    except Exception:
        pass
    return []


def PainelChapaDXF():
    import PrumoPainel as P
    from PySide import QtWidgets

    class _Painel(P.PainelTarefa):
        titulo = "Planificar e exportar DXF"
        ajuda = "Escolha a peça de chapa. A face clicada vira a face de apoio (sem clique, a maior face plana)."

        def montar(self):
            f = self.form
            s0 = f.secao("Chapa", "selecao")
            self.chapa = f.caixa(s0, "Peça de chapa", _filtro_chapa, minimo=1, maximo=1)
            s1 = f.secao("Dobra", "raio")
            self.material = s1.linha("material", P.lista(list(TABELAS_K)), "Tabela de fator K usada na "
                                     "planificação.", "Material (fator K)")
            self.info = s1.texto("")
            s2 = f.secao("Arquivo", "folha")
            self.caminho = s2.linha("folha", QtWidgets.QLineEdit(), "Onde gravar o DXF (vazio: ao lado do "
                                    "arquivo do projeto).", "Arquivo DXF")
            self.caminho.setPlaceholderText("<pasta do projeto>/<peça>_planificada.dxf")
            self.tabela = s2.linha("tipo", P.marcar("Criar também a tabela de fator K no documento (para o "
                                                    "Planificar do SheetMetal)"), "Planilha material_… que o "
                                   "Planificar do SheetMetal reconhece.")
            self.chapa.mudou.connect(self._info)
            self.material.currentTextChanged.connect(lambda *_: self._info())

        def _info(self):
            vs = self.chapa.valores()
            if not vs:
                self.info.setText("")
                return
            obj = vs[0][0]
            try:
                import PrumoUtil
                fam = familia_do_material(PrumoUtil.material(obj)[0])
                if self.material.currentText() == "Aço carbono" and fam != "Aço carbono":
                    self.material.setCurrentText(fam)
            except Exception:
                pass
            t, r = espessura_raio(obj)
            if t and r is not None:
                mat = self.material.currentText()
                k = k_fator(mat, r, t)
                txt = "Espessura %s mm · raio %s mm · r/t %s · K = %s" % (
                    _f(t), _f(r), _f(r / t, 2), _f(k, 3))
                try:
                    import PrumoUtil
                    nome_mat = PrumoUtil.material(obj)[0]
                except Exception:
                    nome_mat = ""
                rmin = raio_minimo("Aço carbono" if mat.startswith("DIN") else mat, t, nome_mat)
                if r + 1e-9 < rmin:
                    txt += "<br><span style='color:#B5523F'>Raio menor que o mínimo recomendado (%s mm).</span>" \
                        % _f(rmin)
                self.info.setText(txt)

        def executar(self):
            obj, face = self.chapa.valores()[0]
            mat = self.material.currentText()
            if self.tabela.isChecked():
                criar_tabela_k(obj.Document, mat)
            caminho = self.caminho.text().strip() or None
            arq, _plana, info = exportar_dxf(obj, caminho, mat, face)
            FreeCAD.Console.PrintMessage("Prumo: planificação de %s gravada em %s (%s × %s mm, %d dobras).\n"
                                         % (obj.Label, arq, _f(info["largura"]), _f(info["altura"]),
                                            info["dobras"]))
            self.arquivo = arq
            return arq

    return _Painel()


def _f(v, casas=2):
    try:
        import PrumoUtil
        return PrumoUtil.fmt(v, casas)
    except Exception:
        return ("%.*f" % (casas, v)).replace(".", ",")


class CmdChapaDXF:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("folha_abnt.svg"), "MenuText": "Planificar em DXF",
                "ToolTip": "Planifica a peça de chapa com o fator K do material e grava o DXF (contorno e "
                           "linhas de dobra) num clique."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        PainelChapaDXF().mostrar()


class CmdTabelaK:
    def GetResources(self):
        import PrumoUtil
        return {"Pixmap": PrumoUtil.icone("lista_corte.svg"), "MenuText": "Tabela de fator K",
                "ToolTip": "Cria no documento as tabelas de fator K (aço carbono, inox, alumínio e DIN 6935) "
                           "que o Planificar do SheetMetal reconhece."}

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        doc.openTransaction("Tabelas de fator K")
        try:
            for m in TABELAS_K:
                criar_tabela_k(doc, m)
        except Exception as exc:
            doc.abortTransaction()
            FreeCAD.Console.PrintError("Prumo: tabelas de fator K: %s\n" % exc)
            return
        doc.commitTransaction()
        FreeCAD.Console.PrintMessage("Prumo: tabelas de fator K criadas (escolha no Planificar do SheetMetal).\n")
