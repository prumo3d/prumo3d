# SPDX-License-Identifier: LGPL-2.1-or-later
"""Memória de cálculo (PDF) da simulação de estruturas por barras, no padrão visual Prumo.

Mesmo estilo do relatório da simulação por elementos finitos (PrumoFEMRelatorio): capa, cabeçalho
e rodapé em todas as páginas, Poppins, azul #003A70 e amarelo #F7BE00.
"""

import os
import tempfile
import time

import FreeCAD
import FreeCADGui

import PrumoFEMRelatorio as R
import PrumoNBR8800 as N
import PrumoAnaliseEstrutura as A
import PrumoUtil

try:
    from PySide import QtCore, QtGui
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui


def _f(v, c=2):
    return PrumoUtil.fmt(float(v), c)


def _captura(analise, modo, pasta):
    v = R._vista()
    if v is None:
        return None
    caminho = os.path.join(pasta, "%s.png" % abs(hash(modo)))
    try:
        analise.Mostrar = modo
        analise.Document.recompute()
        FreeCADGui.updateGui()
        _enquadrar(v, analise)
        FreeCADGui.updateGui()
        v.saveImage(caminho, 1800, 1150, "White")
        return caminho if os.path.isfile(caminho) else None
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: captura '%s' falhou: %s\n" % (modo, exc))
        return None


def _enquadrar(v, analise):
    """Vista de frente/lado/topo para quadros planos; isométrica para estruturas espaciais."""
    import PrumoEstrutura as E
    try:
        n = E._normal_esqueleto(E.arestas(analise.Estrutura.Esqueleto))
    except Exception:
        n = None
    if n is not None and abs(n.y) > 0.99:
        v.viewFront()
    elif n is not None and abs(n.x) > 0.99:
        v.viewRight()
    elif n is not None and abs(n.z) > 0.99:
        v.viewTop()
    else:
        v.viewIsometric()
    v.fitAll()


def _corpo(analise, doc, imgs, largura):
    calc = analise.Proxy.calc
    est = analise.Estrutura
    nome, fy, fu = calc.material
    h = "<h1>1. Objeto e normas</h1>"
    h += "<p>Verificação da estrutura soldada <b>%s</b> por barras (pórtico espacial), com as combinações de " \
         "ações da ABNT NBR 8681:2003 e a verificação das barras de aço pela ABNT NBR 8800:2008.</p>" % est.Label
    h += "<p class='nota' style='color:#B5523F'><b>Normas:</b> %s.</p>" % N.EDICAO
    h += R._tab([R._par("Aço", nome), R._par("fy / fu", "%s / %s MPa" % (_f(fy, 0), _f(fu, 0))),
                 R._par("E / G", "%s / %s MPa" % (_f(N.E_ACO, 0), _f(N.G_ACO, 0))),
                 R._par("γa1 / γa2", "%s / %s" % (_f(N.GAMA_A1), _f(N.GAMA_A2))),
                 R._par("Limite de flecha das vigas", analise.LimiteFlecha),
                 R._par("Coeficiente de flambagem K", _f(analise.K or 1.0) + " (balanços: 2,1)"),
                 R._par("Pilares (deslocamento relativo)", "H/%d" % int(A.LIMITE_PILAR))])
    h += "<h2>Hipóteses e limites do cálculo</h2><ul>" + "".join("<li>%s</li>" % x for x in N.LIMITES) + "</ul>"
    if calc.avisos:
        h += "<h2>Avisos deste cálculo</h2><ul>" + "".join(
            "<li style='color:#B5523F'>%s</li>" % x for x in calc.avisos) + "</ul>"
    # geometria
    h += "<h1>2. Barras e seções</h1>"
    linhas = []
    for i in sorted(calc.mapa["linhas"]):
        p = calc.mapa["secoes"][i]
        L = calc.mapa["linhas"][i][2]
        linhas.append(["%d" % (i + 1), p["nome"] + (" *" if p["aproximada"] else ""), _f(L, 0),
                       _f(p["A"] / 100, 2), _f(p["Ix"] / 1e4, 1), _f(p["Iy"] / 1e4, 1), _f(p["Wx"] / 1e3, 1),
                       _f(p["Zx"] / 1e3, 1), _f(p["J"] / 1e4, 2)])
    h += R._tab(linhas, ["Barra", "Perfil", "L (mm)", "A (cm²)", "Ix (cm⁴)", "Iy (cm⁴)", "Wx (cm³)",
                         "Zx (cm³)", "J (cm⁴)"])
    h += "<p class='nota'>* Seção calculada sem os raios de concordância (o catálogo não traz): valores um " \
         "pouco menores que os de catálogo.</p>"
    if imgs.get("cargas"):
        h += R._img(doc, "cargas", imgs["cargas"], "Apoios e cargas", largura)
    # apoios
    h += "<h1>3. Apoios</h1>"
    h += R._tab([[t, "(%s; %s; %s)" % tuple(_f(v, 0) for v in A._ponto_da_chave(k))]
                 for k, t in analise.Proxy.apoios(analise).items()], ["Tipo", "Posição (mm)"])
    libs = analise.Proxy.liberacoes(analise) if hasattr(analise.Proxy, "liberacoes") else {}
    if libs:
        h += "<h2>Rótulas nas barras</h2>"
        h += R._tab([["%d" % (i + 1), t] for i, t in sorted(libs.items())], ["Barra", "Liberação"])
        h += "<p class='nota'>Rótula: a ponta não transmite momento fletor (ligação flexível). Barra de treliça: " \
             "rótulas nas duas pontas, só força normal vinda dos nós.</p>"
    # cargas
    h += "<h1>4. Casos de carga e combinações</h1>"
    for c in analise.Proxy.casos(analise):
        t = A.TIPOS_CASO[c["tipo"]]
        h += "<h2>%s — %s</h2>" % (c["nome"], c["tipo"])
        itens = []
        if c.get("peso_proprio"):
            itens.append(["Peso próprio das barras (massa linear do catálogo × g)"])
        try:
            import PrumoAnaliseVista as V
            itens += [[V._texto_carga(x)] for x in c.get("cargas", [])]
        except Exception:
            pass
        h += R._tab(itens or [["(sem cargas)"]])
        h += "<p class='nota'>γ desfavorável %s; ψ0 / ψ1 / ψ2: %s</p>" % (
            _f(t[0]), " / ".join("—" if v is None else _f(v) for v in t[2:5]))
    casos = analise.Proxy.casos(analise)
    h += R._tab([[n, tp, " + ".join("%s·%s" % (_f(f), casos[k]["nome"]) for k, f in fat)]
                 for n, tp, fat in calc.combinacoes], ["Combinação", "Tipo", "Fatores"])
    # resultados
    h += "<h1>5. Resultados</h1>"
    for chave, leg in (("taxa", "Taxa de uso das barras (pior combinação última)"),
                       ("momento", "Momento fletor na combinação que governa"),
                       ("deformada", "Deformada (escala exagerada)")):
        if imgs.get(chave):
            h += R._img(doc, chave, imgs[chave], leg, largura)
    h += "<h2>Verificação das barras (NBR 8800)</h2>"
    linhas = []
    for i, v in sorted(calc.verificacao.items(), key=lambda kv: -kv[1]["taxa"]):
        e = v["esforcos"]
        rs = v["resistencias"]
        linhas.append(["%d" % (i + 1), calc.mapa["secoes"][i]["nome"],
                       "%s / %s" % (_f(e["N"] / 1e3, 1), _f(rs["NRd"] / 1e3, 1)),
                       "%s / %s" % (_f(e["Mx"] / 1e6, 2), _f(rs["MxRd"] / 1e6, 2)),
                       "%s / %s" % (_f(e["My"] / 1e6, 2), _f(rs["MyRd"] / 1e6, 2)),
                       "%s / %s" % (_f(e["Vz"] / 1e3, 1), _f(rs["VzRd"] / 1e3, 1)),
                       "<b>%s</b>" % _f(v["taxa"], 2), v["governa"]])
    h += R._tab(linhas, ["Barra", "Perfil", "N / NRd (kN)", "Mx / MxRd (kN·m)", "My / MyRd (kN·m)",
                         "V / VRd (kN)", "Taxa", "Governa"])
    h += "<h2>Detalhe por barra</h2>"
    for i, v in sorted(calc.verificacao.items()):
        md = v["modos"]
        h += "<p><b>Barra %d</b> (%s) — combinação %s. Normal: %s. Flexão x: %s. Flexão y: %s. " \
             "Cortante: %s. Interação: %s.</p>" % (i + 1, calc.mapa["secoes"][i]["nome"], v["combinacao"],
                                                  md["N"], md["Mx"], md["My"], md["Vz"], md["interacao"])
    h += "<h2>Deslocamentos (serviço)</h2>"
    h += R._tab([["%d" % (i + 1), f[4], _f(f[0], 1), _f(f[1], 1), _f(f[2], 2), f[3] or "—"]
                 for i, f in sorted(calc.flechas.items())],
                ["Barra", "Verificação", "Calculado (mm)", "Limite (mm)", "Razão", "Combinação"])
    h += "<h2>Reações de apoio (combinação que governa)</h2>"
    try:
        import PrumoAnaliseVista as V
        nome_c = analise.Combinacao or V._pior_combinacao(calc)
        r = calc.resultados[nome_c]
        lin = []
        for k, t in analise.Proxy.apoios(analise).items():
            no = A._no_mais_proximo(calc.modelo, A._ponto_da_chave(k))
            F, M = r.reacao(no)
            lin.append([t, "(%s)" % "; ".join(_f(v, 0) for v in A._ponto_da_chave(k)),
                        "; ".join(_f(x, 2) for x in F), "; ".join(_f(x, 2) for x in M)])
        h += "<p class='nota'>%s</p>" % nome_c
        h += R._tab(lin, ["Apoio", "Posição (mm)", "Fx; Fy; Fz (kN)", "Mx; My; Mz (kN·m)"])
    except Exception:
        pass
    h += "<h1>6. Conclusão</h1>"
    h += "<p class='destaque'>%s — maior taxa de uso %s (%s).</p>" % (
        "A estrutura ATENDE" if analise.TaxaMaxima <= 1.0 else "A estrutura NÃO ATENDE",
        _f(analise.TaxaMaxima, 2), analise.BarraCritica)
    h += "<p class='nota'>Cálculo automático de apoio ao projeto. Ligações, placas de base, chumbadores, " \
         "soldas e efeitos de 2ª ordem não estão verificados aqui. O documento só tem valor de projeto com a " \
         "responsabilidade técnica de engenheiro habilitado (ART).</p>"
    return h


class _Dados(dict):
    """Adaptador para a capa do relatório de simulação (mesmos campos)."""

    def __init__(self, analise):
        super().__init__()
        self.peca = analise.Estrutura
        self.tipo = "barras"
        self.analise = analise

    def get(self, chave, padrao=""):
        return padrao


def gerar_pdf(analise, caminho):
    if getattr(analise.Proxy, "calc", None) is None:
        analise.Proxy.execute(analise)
    if analise.Proxy.calc is None:
        raise ValueError("a análise não tem resultado: %s" % analise.Situacao)
    pasta = tempfile.mkdtemp(prefix="prumo_mem_")
    antes = analise.Mostrar
    imgs = {}
    try:
        imgs["cargas"] = _captura(analise, "Cargas e apoios", pasta)
        imgs["taxa"] = _captura(analise, "Taxa de uso", pasta)
        imgs["momento"] = _captura(analise, "Momento fletor (M)", pasta)
        imgs["deformada"] = _captura(analise, "Deformada", pasta)
    finally:
        analise.Mostrar = antes
        analise.Document.recompute()
    d = _Dados(analise)
    w = QtGui.QPdfWriter(caminho)
    w.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))
    w.setPageMargins(QtCore.QMarginsF(0, 0, 0, 0))
    w.setResolution(R.DPI)
    w.setTitle("Memória de cálculo — " + analise.Estrutura.Label)
    w.setCreator("Prumo 3D")
    k = R.DPI / 25.4
    W, H = w.width(), w.height()
    escala = R.DPI / 96.0
    topo, base = 22 * k, 18 * k
    larg_doc = (W - 2 * R.MARGEM_MM * k) / escala
    alt_doc = (H - topo - base) / escala
    doc = QtGui.QTextDocument()
    doc.setDefaultStyleSheet(R.CSS)
    f = QtGui.QFont("Poppins")
    f.setPixelSize(14)
    doc.setDefaultFont(f)
    doc.setDocumentMargin(0)
    doc.setHtml(_corpo(analise, doc, imgs, int(larg_doc * 0.78)))
    doc.setTextWidth(larg_doc)
    doc.setPageSize(QtCore.QSizeF(larg_doc, alt_doc))
    paginas = doc.pageCount()
    total = paginas + 1
    p = QtGui.QPainter(w)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    p.setRenderHint(QtGui.QPainter.TextAntialiasing)
    _capa(p, W, H, k, analise)
    for i in range(paginas):
        w.newPage()
        _cabecalho(p, W, k, analise)
        R._rodape(p, W, H, k, i + 2, total)
        p.save()
        p.translate(R.MARGEM_MM * k, topo)
        p.scale(escala, escala)
        p.translate(0, -i * alt_doc)
        doc.drawContents(p, QtCore.QRectF(0, i * alt_doc, larg_doc, alt_doc))
        p.restore()
    p.end()
    return caminho


def _capa(p, W, H, k, analise):
    M = R.MARGEM_MM
    p.fillRect(QtCore.QRectF(0, 0, W, 95 * k), QtGui.QColor(R.NAVY))
    p.fillRect(QtCore.QRectF(0, 95 * k, W, 3 * k), QtGui.QColor(R.YEL))
    if os.path.isfile(R.LOGO):
        p.drawImage(QtCore.QRectF(M * k, 22 * k, 26 * k, 26 * k), QtGui.QImage(R.LOGO))
    p.setPen(QtGui.QColor("#FFFFFF"))
    p.setFont(R._fonte(5.0 * k, QtGui.QFont.DemiBold))
    p.drawText(QtCore.QRectF((M + 32) * k, 24 * k, W, 10 * k), "PRUMO 3D")
    p.setFont(R._fonte(8.5 * k, QtGui.QFont.Bold))
    p.drawText(QtCore.QRectF(M * k, 55 * k, W - 2 * M * k, 30 * k), QtCore.Qt.TextWordWrap,
               "Memória de cálculo — estrutura metálica")
    p.setPen(QtGui.QColor(R.INK))
    p.setFont(R._fonte(5.0 * k, QtGui.QFont.DemiBold))
    p.drawText(QtCore.QRectF(M * k, 112 * k, W, 12 * k), "Verificação por barras · NBR 8800:2008 · NBR 8681:2003")
    linhas = [("Estrutura", analise.Estrutura.Label), ("Situação", analise.Situacao),
              ("Maior taxa de uso", _f(analise.TaxaMaxima, 2)), ("Data", time.strftime("%d/%m/%Y")),
              ("Responsável técnico", "—"), ("CREA", "—"), ("ART nº", "—")]
    y = 130 * k
    for rot, val in linhas:
        p.setPen(QtGui.QColor(R.INK2))
        p.setFont(R._fonte(3.7 * k))
        p.drawText(QtCore.QRectF(M * k, y, 60 * k, 9 * k), rot)
        p.setPen(QtGui.QColor(R.INK))
        p.setFont(R._fonte(3.9 * k, QtGui.QFont.DemiBold))
        p.drawText(QtCore.QRectF((M + 62) * k, y, W - (M * 2 + 62) * k, 9 * k), val)
        y += 9 * k
        p.setPen(QtGui.QPen(QtGui.QColor(R.LINHA), 0.25 * k))
        p.drawLine(QtCore.QPointF(M * k, y - 1.5 * k), QtCore.QPointF(W - M * k, y - 1.5 * k))
    R._rodape(p, W, H, k, None, None)


def _cabecalho(p, W, k, analise):
    M = R.MARGEM_MM
    p.setPen(QtGui.QColor(R.NAVY))
    p.setFont(R._fonte(3.2 * k, QtGui.QFont.DemiBold))
    p.drawText(QtCore.QRectF(M * k, 8 * k, W - 60 * k, 6 * k), QtCore.Qt.AlignVCenter,
               "Memória de cálculo · " + analise.Estrutura.Label)
    p.setPen(QtGui.QColor(R.INK2))
    p.setFont(R._fonte(3.0 * k))
    p.drawText(QtCore.QRectF(W - (M + 60) * k, 8 * k, 60 * k, 6 * k), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
               "PRUMO 3D")
    p.fillRect(QtCore.QRectF(M * k, 15 * k, W - 2 * M * k, 0.5 * k), QtGui.QColor(R.NAVY))
