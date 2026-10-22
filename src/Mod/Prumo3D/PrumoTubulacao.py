# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tubulação: tubos e conexões automáticos sobre um traçado (Esboço 3D ou esboço comum).

Em cada nó do traçado a conexão sai do catálogo da linha escolhida:

- 2 linhas a 90° → joelho 90°; a 135° (desvio de 45°) → joelho 45°;
- 2 linhas alinhadas com o mesmo diâmetro → tubo contínuo; com diâmetros diferentes → luva de redução
  (ou luva + bucha de redução);
- 3 linhas (duas alinhadas e uma a 90°) → tê; ramal menor → tê de redução (ou tê + bucha);
- 4 linhas em cruz → cruzeta;
- ponta solta → cap, se pedido.

Ângulo ou combinação que não existe no catálogo vira aviso: o Prumo não inventa conexão. O tubo de cada
trecho é cortado descontando o avanço das conexões (centro até a face menos a bolsa), e a lista de corte
aproveita as barras (com emenda pela bolsa da barra quando o trecho passa do comprimento da barra).
"""
import math

import FreeCAD

import PrumoCatalogoTubos as CAT

TOL_NO = 0.5        # mm: pontas mais próximas que isso são o mesmo nó
TOL_ANG = 1.0       # graus


# ======================================================================== traçado
def segmentos_do_caminho(caminho):
    """[(a, b)] em coordenadas globais e avisos. Esboço 3D usa os pontos (cantos vivos); arcos de
    outros traçados não entram (PVC soldável usa joelhos)."""
    import Part
    avisos = []
    if caminho is None:
        return [], ["Escolha o traçado (Esboço 3D ou esboço)."]
    try:
        import PrumoEsboco3D
        e3d = PrumoEsboco3D.e_esboco3d(caminho)
    except Exception:
        e3d = False
    if e3d:
        forma = PrumoEsboco3D.forma(caminho.Pontos, caminho.Quebras, caminho.Fechado, 0.0)
        pl = caminho.getGlobalPlacement() if hasattr(caminho, "getGlobalPlacement") else caminho.Placement
        forma.Placement = pl
        if float(caminho.RaioCurva) > 0:
            avisos.append("O Esboço 3D tem raio nos cantos; a tubulação usa os cantos vivos (joelhos).")
    else:
        import PrumoEstrutura
        forma = PrumoEstrutura.forma_global(caminho)
    segs = []
    arcos = 0
    for e in forma.Edges:
        if e.Length < 1e-6:
            continue
        if isinstance(e.Curve, (Part.Line, Part.LineSegment)) or e.Curve.TypeId == "Part::GeomLine":
            segs.append((FreeCAD.Vector(e.Vertexes[0].Point), FreeCAD.Vector(e.Vertexes[-1].Point)))
        else:
            arcos += 1
    if arcos:
        avisos.append("%d trecho(s) curvo(s) do traçado ficaram de fora: desenhe com linhas retas "
                      "(as curvas saem nos joelhos)." % arcos)
    return segs, avisos


def _nos(segs):
    """Une as pontas próximas: (lista de pontos dos nós, [(no_a, no_b)] por segmento)."""
    nos = []
    ligacoes = []
    for a, b in segs:
        par = []
        for p in (a, b):
            k = next((i for i, q in enumerate(nos) if (q - p).Length < TOL_NO), None)
            if k is None:
                nos.append(FreeCAD.Vector(p))
                k = len(nos) - 1
            par.append(k)
        ligacoes.append(tuple(par))
    return nos, ligacoes


def _ang(u, v):
    return math.degrees(math.acos(max(-1.0, min(1.0, u.dot(v)))))


# ======================================================================== conexões
def _rec(nome, desc, no, pernas, corpo, extra=()):
    """pernas: [(seg, ponta, direção, dn, centro_face)]."""
    return {"tipo": nome, "desc": desc, "no": no, "pernas": pernas, "corpo": corpo, "extras": list(extra)}


def montar(segs, dns, lid=CAT.PADRAO, tampar=False):
    """Traçado + diâmetros → tubos, conexões, avisos e lista de corte (sem geometria)."""
    L = CAT.linha(lid)
    nos, lig = _nos(segs)
    avisos = []
    inc = {i: [] for i in range(len(nos))}
    for s, (na, nb) in enumerate(lig):
        a, b = nos[na], nos[nb]
        if na == nb:
            avisos.append("Trecho %d tem comprimento zero." % (s + 1))
            continue
        u = (b - a).normalize()
        inc[na].append((s, 0, u))
        inc[nb].append((s, 1, -u))
    recuo = {}          # (seg, ponta) -> mm que o tubo para antes do nó
    conexoes = []
    continua = []       # pares de segmentos que seguem como um tubo só
    for d in dns:
        if d not in L["tubos"]:
            avisos.append("Diâmetro %s não existe na linha %s." % (d, L["nome"]))
            return {"tubos": [], "conexoes": [], "avisos": avisos, "linha": L, "nos": nos}
    bolsa = L["bolsa"]

    def nome_dn(d):
        return "%d mm" % d

    for k, its in inc.items():
        P = nos[k]
        n = len(its)
        if n == 0:
            continue
        if n == 1:
            s, pt, u = its[0]
            recuo[(s, pt)] = 0.0
            if tampar:
                d = dns[s]
                conexoes.append(_rec("Cap", "Cap soldável " + nome_dn(d), P,
                                     [(s, pt, u, d, -(L["cap"][d] - bolsa[d]))], L["corpo"][d]))
            continue
        if n == 2:
            (s1, p1, u1), (s2, p2, u2) = its
            d1, d2 = dns[s1], dns[s2]
            desvio = 180.0 - _ang(u1, u2)
            if desvio < TOL_ANG:
                if d1 == d2:
                    recuo[(s1, p1)] = recuo[(s2, p2)] = 0.0
                    continua.append((s1, s2))
                    continue
                D, d = max(d1, d2), min(d1, d2)
                if (D, d) in L["luva_reducao"]:
                    A = L["luva_reducao"][(D, d)]
                    folga = (A - bolsa[D] - bolsa[d]) / 2.0
                    pern = [(s, p, u, dd, (folga + bolsa[dd])) for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2))]
                    conexoes.append(_rec("Luva de redução", "Luva de redução soldável %d × %d" % (D, d), P, pern,
                                         L["corpo"][D]))
                elif (D, d) in L["bucha_curta"] and D in L["luva"]:
                    A = L["luva"][D] / 2.0
                    pern = [(s, p, u, dd, A) for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2))]
                    conexoes.append(_rec("Luva", "Luva soldável %s" % nome_dn(D), P, pern, L["corpo"][D],
                                         ["Bucha de redução soldável curta %d × %d" % (D, d)]))
                else:
                    avisos.append("Redução %d × %d no nó %d: não há peça no catálogo (faça em etapas)."
                                  % (D, d, k + 1))
                    recuo[(s1, p1)] = recuo[(s2, p2)] = 0.0
                    continue
                for s, p, u, dd, cf in pern:
                    recuo[(s, p)] = cf - bolsa[dd]
                continue
            for alvo, chave, rot in ((90.0, "joelho90", "Joelho 90°"), (45.0, "joelho45", "Joelho 45°")):
                if abs(desvio - alvo) < TOL_ANG:
                    D = max(d1, d2)
                    if D not in L[chave]:
                        avisos.append("%s de %s não está no catálogo (nó %d)." % (rot, nome_dn(D), k + 1))
                        break
                    cf = L[chave][D]
                    extras = []
                    pern = []
                    for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2)):
                        if dd != D:
                            if (D, dd) not in L["bucha_curta"]:
                                avisos.append("%s %d com ramal de %d no nó %d: falta bucha %d × %d no "
                                              "catálogo." % (rot, D, dd, k + 1, D, dd))
                            extras.append("Bucha de redução soldável curta %d × %d" % (D, dd))
                        pern.append((s, p, u, dd, cf))
                        recuo[(s, p)] = cf - bolsa[dd]
                    conexoes.append(_rec(rot, "%s soldável %s" % (rot, nome_dn(D)), P, pern, L["corpo"][D], extras))
                    break
            else:
                avisos.append("Nó %d: ângulo de %.1f° entre os trechos %d e %d não tem conexão no catálogo "
                              "(use 90° ou 45°)." % (k + 1, 180.0 - desvio, s1 + 1, s2 + 1))
                recuo[(s1, p1)] = recuo[(s2, p2)] = 0.0
            continue
        if n == 3:
            par = None
            for i in range(3):
                for j in range(i + 1, 3):
                    if 180.0 - _ang(its[i][2], its[j][2]) < TOL_ANG:
                        par = (i, j)
            if par is None:
                avisos.append("Nó %d: três trechos sem dois alinhados — não há tê para essa geometria."
                              % (k + 1))
                for s, p, u in its:
                    recuo[(s, p)] = 0.0
                continue
            ramal = its[3 - par[0] - par[1]]
            corrida = [its[par[0]], its[par[1]]]
            ang_r = _ang(ramal[2], corrida[0][2])
            dr = dns[ramal[0]]
            dc = [dns[c[0]] for c in corrida]
            if abs(ang_r - 90.0) > TOL_ANG:
                avisos.append("Nó %d: ramal a %.1f° da linha principal; o PVC soldável de água fria só tem "
                              "tê a 90°." % (k + 1, ang_r))
                for s, p, u in its:
                    recuo[(s, p)] = 0.0
                continue
            if dc[0] != dc[1]:
                avisos.append("Nó %d: a linha principal muda de diâmetro (%d e %d) no tê; ponha a redução "
                              "num trecho próprio." % (k + 1, dc[0], dc[1]))
            D = max(dc)
            if dr > D:
                avisos.append("Nó %d: o ramal (%d) é maior que a linha principal (%d)." % (k + 1, dr, D))
                D = dr
            extras = []
            if dr == D:
                cf_c = cf_r = L["te"][D]
                desc = "Tê soldável %s" % nome_dn(D)
                rot = "Tê"
            elif (D, dr) in L["te_reducao"]:
                A, B = L["te_reducao"][(D, dr)]
                cf_c, cf_r = A / 2.0, B
                desc = "Tê de redução soldável %d × %d" % (D, dr)
                rot = "Tê de redução"
            else:
                cf_c = cf_r = L["te"][D]
                desc = "Tê soldável %s" % nome_dn(D)
                rot = "Tê"
                if (D, dr) in L["bucha_curta"]:
                    extras.append("Bucha de redução soldável curta %d × %d" % (D, dr))
                elif (D, dr) in L["bucha_longa"]:
                    extras.append("Bucha de redução soldável longa %d × %d" % (D, dr))
                    cf_r += L["bucha_longa"][(D, dr)] - bolsa[D]
                else:
                    avisos.append("Nó %d: ramal %d num tê de %d sem bucha no catálogo." % (k + 1, dr, D))
            pern = [(c[0], c[1], c[2], dns[c[0]], cf_c) for c in corrida]
            pern.append((ramal[0], ramal[1], ramal[2], dr, cf_r))
            for s, p, u, dd, cf in pern:
                recuo[(s, p)] = cf - bolsa[dd]
            conexoes.append(_rec(rot, desc, P, pern, L["corpo"][D], extras))
            continue
        if n == 4:
            ds = {dns[s] for s, p, u in its}
            parceiro = [j for j in range(1, 4) if 180.0 - _ang(its[0][2], its[j][2]) < TOL_ANG]
            outros = [j for j in range(1, 4) if j not in parceiro]
            ok = (len(parceiro) == 1 and len(outros) == 2 and len(ds) == 1
                  and 180.0 - _ang(its[outros[0]][2], its[outros[1]][2]) < TOL_ANG
                  and abs(_ang(its[0][2], its[outros[0]][2]) - 90.0) < TOL_ANG)
            D = max(ds)
            if ok and D in L["cruzeta"]:
                cf = L["cruzeta"][D]
                pern = [(s, p, u, D, cf) for s, p, u in its]
                for s, p, u, dd, c in pern:
                    recuo[(s, p)] = c - bolsa[dd]
                conexoes.append(_rec("Cruzeta", "Cruzeta soldável %s" % nome_dn(D), P, pern, L["corpo"][D]))
            else:
                avisos.append("Nó %d: cruzamento de 4 trechos sem cruzeta no catálogo para esse caso; "
                              "separe em dois tês." % (k + 1))
                for s, p, u in its:
                    recuo[(s, p)] = 0.0
            continue
        avisos.append("Nó %d: %d trechos chegando no mesmo ponto; não há conexão para isso." % (k + 1, n))
        for s, p, u in its:
            recuo[(s, p)] = 0.0

    tubos = []
    for s, (na, nb) in enumerate(lig):
        if na == nb:
            continue
        a, b = nos[na], nos[nb]
        u = (b - a).normalize()
        ra, rb = recuo.get((s, 0), 0.0), recuo.get((s, 1), 0.0)
        ini = a + u * ra
        fim = b - u * rb
        comp = (b - a).Length - ra - rb
        if comp <= 1.0:
            avisos.append("Trecho %d curto demais: as conexões das pontas já ocupam o espaço." % (s + 1))
            continue
        tubos.append({"seg": s, "ini": ini, "fim": fim, "dn": dns[s], "corte": comp})
    # trechos alinhados sem conexão viram um tubo só na lista de corte
    grupo = list(range(len(segs)))

    def raiz(i):
        while grupo[i] != i:
            grupo[i] = grupo[grupo[i]]
            i = grupo[i]
        return i
    for s1, s2 in continua:
        grupo[raiz(s1)] = raiz(s2)
    pecas = {}
    for t in tubos:
        r = raiz(t["seg"])
        pecas.setdefault(r, {"dn": t["dn"], "corte": 0.0, "trechos": []})
        pecas[r]["corte"] += t["corte"]
        pecas[r]["trechos"].append(t["seg"] + 1)
    return {"tubos": tubos, "conexoes": conexoes, "avisos": avisos, "linha": L, "nos": nos,
            "pecas": list(pecas.values())}


def lista_de_corte(pecas, L):
    """Por diâmetro: peças cortadas, barras usadas (aproveitamento pelo maior primeiro) e emendas."""
    barra = L["barra"]
    res = {}
    for pc in pecas:
        d = pc["dn"]
        bt = L["tubos"][d]["bolsa_tubo"]
        r = res.setdefault(d, {"pecas": [], "barras_inteiras": 0, "emendas": 0, "total": 0.0})
        comp = pc["corte"]
        r["total"] += comp
        if comp <= barra:
            r["pecas"].append(comp)
            continue
        k = 2
        while barra + (k - 1) * (barra - bt) < comp:
            k += 1
        r["barras_inteiras"] += k - 1
        r["emendas"] += k - 1
        r["pecas"].append(comp - (barra + (k - 2) * (barra - bt)) + bt)
    for d, r in res.items():
        sobras = []
        for p in sorted(r["pecas"], reverse=True):
            for i, sb in enumerate(sobras):
                if sb >= p:
                    sobras[i] = sb - p
                    break
            else:
                sobras.append(barra - p)
        r["barras"] = r["barras_inteiras"] + len(sobras)
        r["sobra"] = sum(sobras)
    return res


def resumo_conexoes(conexoes):
    """{descrição: quantidade}, incluindo as buchas."""
    q = {}
    for c in conexoes:
        q[c["desc"]] = q.get(c["desc"], 0) + 1
        for e in c["extras"]:
            q[e] = q.get(e, 0) + 1
    return dict(sorted(q.items()))


# ======================================================================== geometria
def _cil(r, p, u, comp):
    import Part
    return Part.makeCylinder(r, comp, p, u)


def solido_tubo(t, L):
    tb = L["tubos"][t["dn"]]
    u = (t["fim"] - t["ini"]).normalize()
    comp = (t["fim"] - t["ini"]).Length
    ext = _cil(tb["De"] / 2.0, t["ini"], u, comp)
    return ext.cut(_cil(tb["De"] / 2.0 - tb["e"], t["ini"] - u * 0.1, u, comp + 0.2))


def solido_conexao(c, L):
    import Part
    P = c["no"]
    R = c["corpo"] / 2.0
    corpo = None
    furos = []
    for s, pt, u, dd, cf in c["pernas"]:
        tb = L["tubos"][dd]
        b = L["bolsa"][dd]
        if cf < 0:      # cap: a conexão fica para fora da ponta do tubo
            alt = L["cap"][dd]
            ini = P - u * (alt - b)
            parte = _cil(R, ini, u, alt)
            furos.append(_cil(tb["De"] / 2.0, P, u, b + 0.5))
        else:
            parte = _cil(R, P, u, cf)
            furos.append(_cil(tb["De"] / 2.0, P + u * (cf - b), u, b + 0.5))
            furos.append(_cil(tb["De"] / 2.0 - tb["e"], P, u, cf))
        corpo = parte if corpo is None else corpo.fuse(parte)
    if len(c["pernas"]) > 1 and c["tipo"] not in ("Luva", "Luva de redução"):
        corpo = corpo.fuse(Part.makeSphere(R, P))
    for f in furos:
        corpo = corpo.cut(f)
    return corpo.removeSplitter() if hasattr(corpo, "removeSplitter") else corpo


def forma(res):
    import Part
    L = res["linha"]
    sol = [solido_tubo(t, L) for t in res["tubos"]]
    for c in res["conexoes"]:
        try:
            sol.append(solido_conexao(c, L))
        except Exception as ex:
            res["avisos"].append("Desenho da conexão %s: %s" % (c["desc"], ex))
    return Part.makeCompound(sol) if sol else Part.Shape()


# ======================================================================== objeto
def _dn_txt(d):
    return "%d mm" % d


class Tubulacao:
    def __init__(self, obj):
        obj.Proxy = self
        self._props(obj)

    def _props(self, obj):
        def add(tipo, nome, grupo, dica, valor=None, ro=False):
            if nome not in obj.PropertiesList:
                obj.addProperty(tipo, nome, grupo, dica)
                if valor is not None:
                    setattr(obj, nome, valor)
            if ro:
                obj.setEditorMode(nome, 1)
        if "Caminho" not in obj.PropertiesList:
            obj.addProperty("App::PropertyLinkGlobal", "Caminho", "Tubulação",
                            "Traçado (Esboço 3D ou esboço com linhas retas)")
        if "Linha" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Linha", "Tubulação", "Linha de tubos e conexões")
            obj.Linha = list(CAT.LINHAS)
            obj.Linha = CAT.PADRAO
        if "Diametro" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Diametro", "Tubulação", "Diâmetro externo (DE) padrão")
            obj.Diametro = [_dn_txt(d) for d in CAT.linha(obj.Linha)["diametros"]]
            obj.Diametro = _dn_txt(25)
        add("App::PropertyStringList", "DiametrosTrechos", "Tubulação",
            "Diâmetro de trechos específicos: 'trecho: DE' (ex.: '3: 20')", [])
        add("App::PropertyBool", "TamparPontas", "Tubulação", "Põe cap nas pontas soltas", False)
        add("App::PropertyStringList", "Conexoes", "Resultados", "Conexões (quantidade × peça)", [], ro=True)
        add("App::PropertyStringList", "ListaCorte", "Resultados", "Tubos por diâmetro e barras", [], ro=True)
        add("App::PropertyStringList", "Avisos", "Resultados", "Avisos do traçado", [], ro=True)
        add("App::PropertyLength", "ComprimentoTubos", "Resultados", "Comprimento total de tubo", 0.0, ro=True)
        add("App::PropertyInteger", "Barras", "Resultados", "Barras de tubo necessárias", 0, ro=True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def diametros(self, obj, n):
        padrao = int(str(obj.Diametro).split()[0])
        dns = [padrao] * n
        for item in obj.DiametrosTrechos:
            try:
                t, d = item.split(":")
                i = int(t) - 1
                if 0 <= i < n:
                    dns[i] = int(float(d.replace("mm", "").strip()))
            except ValueError:
                continue
        return dns

    def calcular(self, obj):
        segs, avisos = segmentos_do_caminho(obj.Caminho)
        dns = self.diametros(obj, len(segs))
        res = montar(segs, dns, obj.Linha, obj.TamparPontas)
        res["avisos"] = avisos + res["avisos"]
        res["segs"] = segs
        res["dns"] = dns
        return res

    def execute(self, obj):
        res = self.calcular(obj)
        L = res["linha"]
        obj.Shape = forma(res)
        q = resumo_conexoes(res["conexoes"])
        obj.Conexoes = ["%d × %s" % (n, d) for d, n in q.items()]
        lc = lista_de_corte(res.get("pecas", []), L)
        linhas = []
        barras = 0
        total = 0.0
        for d in sorted(lc):
            r = lc[d]
            barras += r["barras"]
            total += r["total"]
            pcs = ", ".join(("%.0f" % p) for p in sorted(r["pecas"], reverse=True))
            linhas.append("Tubo %d mm: %d barra(s) de %.0f m — peças (mm): %s%s" % (
                d, r["barras"], L["barra"] / 1000.0, pcs,
                ("; %d emenda(s) pela bolsa" % r["emendas"]) if r["emendas"] else ""))
        obj.ListaCorte = linhas
        obj.Barras = barras
        obj.ComprimentoTubos = total
        obj.Avisos = res["avisos"]
        self.ultimo = res

    def dumps(self):
        return None

    def loads(self, state):
        return None


def criar(caminho, dn=25, lid=CAT.PADRAO, tampar=False, doc=None):
    doc = doc or caminho.Document
    obj = doc.addObject("Part::FeaturePython", "Tubulacao")
    obj.Label = "Tubulação"
    Tubulacao(obj)
    obj.Caminho = caminho
    obj.Linha = lid
    obj.Diametro = _dn_txt(dn)
    obj.TamparPontas = tampar
    if FreeCAD.GuiUp:
        VPTubulacao(obj.ViewObject)
        try:
            caminho.ViewObject.Visibility = True
        except Exception:
            pass
    doc.recompute()
    return obj


def e_tubulacao(obj):
    return obj is not None and isinstance(getattr(obj, "Proxy", None), Tubulacao)


def linhas_bom(obj):
    """Itens para a lista de materiais: [(chave, denominação, material, dimensões, quantidade, obs)]."""
    L = CAT.linha(obj.Linha)
    res = obj.Proxy.calcular(obj)
    itens = []
    lc = lista_de_corte(res.get("pecas", []), L)
    for d in sorted(lc):
        r = lc[d]
        tb = L["tubos"][d]
        itens.append((("tubo", L["id"], d), "Tubo %s %d mm (barra de %.0f m)" % (
            "soldável" if "soldavel" in L["id"] else "", d, L["barra"] / 1000.0),
            L["material"], "DE %s × %s — %s m no total" % (
                _num(tb["De"]), _num(tb["e"]), _num(round(r["total"] / 1000.0, 2))),
            r["barras"], L["fabricante"]))
    for desc, n in resumo_conexoes(res["conexoes"]).items():
        itens.append((("conexao", L["id"], desc), desc, L["material"], "—", n, L["fabricante"]))
    return itens


def _num(v):
    return ("%g" % v).replace(".", ",")


def texto_lista(obj):
    """Lista de materiais em texto (para copiar para planilha)."""
    L = CAT.linha(obj.Linha)
    out = ["Tubulação: %s" % obj.Label, "Linha: %s (%s)" % (L["nome"], L["fabricante"]),
           "Fonte das medidas: %s" % L["fonte"], "", "Quantidade\tPeça"]
    for c in obj.Conexoes:
        n, d = c.split(" × ", 1)
        out.append("%s\t%s" % (n, d))
    out.append("")
    out.extend(obj.ListaCorte)
    if obj.Avisos:
        out.append("")
        out.append("Avisos:")
        out.extend("- " + a for a in obj.Avisos)
    return "\n".join(out)


# ======================================================================== interface
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets

    import PrumoUtil

    class VPTubulacao:
        def __init__(self, vobj):
            vobj.Proxy = self
            try:
                L = CAT.linha(vobj.Object.Linha)
                vobj.ShapeColor = L["cor"]
            except Exception:
                pass

        def attach(self, vobj):
            self.Object = vobj.Object

        def getIcon(self):
            return PrumoUtil.icone("tubulacao.svg")

        def claimChildren(self):
            return []

        def doubleClicked(self, vobj):
            abrir_painel(vobj.Object)
            return True

        def setEdit(self, vobj, mode=0):
            if mode == 0:
                abrir_painel(vobj.Object)
                return True
            return False

        def unsetEdit(self, vobj, mode=0):
            return False

        def dumps(self):
            return None

        def loads(self, state):
            return None

    class PainelTubulacao:
        def __init__(self, obj):
            self.obj = obj
            self.doc = obj.Document
            self._ocupado = False
            self.form = QtWidgets.QWidget()
            self.form.setWindowTitle("Tubulação")
            self.form.setWindowIcon(QtGui.QIcon(PrumoUtil.icone("tubulacao.svg")))
            lay = QtWidgets.QVBoxLayout(self.form)
            dica = QtWidgets.QLabel(
                "Escolha a linha e o diâmetro: tubos e conexões saem sozinhos em cada nó do traçado "
                "(joelhos, tês, reduções, cruzetas). Para mudar o diâmetro de um trecho, use a tabela.")
            dica.setWordWrap(True)
            lay.addWidget(dica)
            fl = QtWidgets.QFormLayout()
            self.lb_caminho = QtWidgets.QLabel(obj.Caminho.Label if obj.Caminho else "—")
            bt_sel = QtWidgets.QPushButton("Usar a seleção")
            bt_sel.setToolTip("Selecione um Esboço 3D ou esboço na árvore ou na tela e clique aqui")
            bt_sel.clicked.connect(self.usar_selecao)
            hl = QtWidgets.QHBoxLayout()
            hl.addWidget(self.lb_caminho, 1)
            hl.addWidget(bt_sel)
            fl.addRow("Traçado", hl)
            self.linha = QtWidgets.QComboBox()
            for lid, nome in CAT.nomes():
                self.linha.addItem(nome, lid)
            self.linha.setCurrentIndex(max(0, self.linha.findData(obj.Linha)))
            self.linha.currentIndexChanged.connect(self._mudou)
            fl.addRow("Linha", self.linha)
            self.dn = QtWidgets.QComboBox()
            self._encher_dn()
            self.dn.currentIndexChanged.connect(self._mudou)
            fl.addRow("Diâmetro (DE)", self.dn)
            self.cap = QtWidgets.QCheckBox("Pôr cap nas pontas soltas")
            self.cap.setChecked(bool(obj.TamparPontas))
            self.cap.toggled.connect(self._mudou)
            fl.addRow("", self.cap)
            lay.addLayout(fl)
            self.tabela = QtWidgets.QTableWidget(0, 3)
            self.tabela.setHorizontalHeaderLabels(["Trecho", "Comprimento (mm)", "DE"])
            self.tabela.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            self.tabela.verticalHeader().setVisible(False)
            self.tabela.setMinimumHeight(140)
            lay.addWidget(self.tabela)
            self.res = QtWidgets.QTextBrowser()
            self.res.setMinimumHeight(200)
            lay.addWidget(self.res)
            bt_copiar = QtWidgets.QPushButton("Copiar lista de materiais")
            bt_copiar.setToolTip("Copia conexões, tubos e barras para colar numa planilha")
            bt_copiar.clicked.connect(self.copiar)
            lay.addWidget(bt_copiar)
            self._atualizar()

        def _encher_dn(self):
            self._ocupado = True
            try:
                self.dn.clear()
                L = CAT.linha(self.linha.currentData())
                for d in L["diametros"]:
                    self.dn.addItem(_dn_txt(d), d)
                atual = int(str(self.obj.Diametro).split()[0])
                self.dn.setCurrentIndex(max(0, self.dn.findData(atual)))
            finally:
                self._ocupado = False

        def usar_selecao(self):
            for s in FreeCADGui.Selection.getSelection():
                if s is not self.obj and hasattr(s, "Shape") and s.Shape.Edges:
                    self.obj.Caminho = s
                    self.lb_caminho.setText(s.Label)
                    self._atualizar()
                    return

        def _mudou(self, *_a):
            if self._ocupado:
                return
            lid = self.linha.currentData()
            if lid != self.obj.Linha:
                self.obj.Linha = lid
                self._encher_dn()
            self.obj.Diametro = _dn_txt(self.dn.currentData())
            self.obj.TamparPontas = self.cap.isChecked()
            self._atualizar()

        def _dn_trecho(self, i, combo):
            if self._ocupado:
                return
            itens = [x for x in self.obj.DiametrosTrechos if not x.startswith("%d:" % (i + 1))]
            d = combo.currentData()
            padrao = int(str(self.obj.Diametro).split()[0])
            if d != padrao:
                itens.append("%d: %d" % (i + 1, d))
            self.obj.DiametrosTrechos = itens
            self._atualizar()

        def _atualizar(self):
            self.doc.recompute()
            res = getattr(self.obj.Proxy, "ultimo", None) or self.obj.Proxy.calcular(self.obj)
            segs, dns = res.get("segs", []), res.get("dns", [])
            L = CAT.linha(self.obj.Linha)
            self._ocupado = True
            try:
                self.tabela.setRowCount(len(segs))
                for i, (a, b) in enumerate(segs):
                    self.tabela.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
                    self.tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(PrumoUtil.fmt((b - a).Length, 0)))
                    cb = QtWidgets.QComboBox()
                    for d in L["diametros"]:
                        cb.addItem(_dn_txt(d), d)
                    cb.setCurrentIndex(max(0, cb.findData(dns[i])))
                    cb.currentIndexChanged.connect(lambda _x, i=i, cb=cb: self._dn_trecho(i, cb))
                    self.tabela.setCellWidget(i, 2, cb)
            finally:
                self._ocupado = False
            html = ["<b>Conexões</b><br>" + ("<br>".join(self.obj.Conexoes) or "—"),
                    "<b>Tubos</b><br>" + ("<br>".join(self.obj.ListaCorte) or "—")]
            if self.obj.Avisos:
                html.append("<b style='color:#B35C00'>Avisos</b><br>" + "<br>".join(self.obj.Avisos))
            html.append("<small>Medidas: %s.<br>Norma: %s.</small>" % (L["fonte"], L["norma"]))
            self.res.setHtml("<br><br>".join(html))

        def copiar(self):
            QtWidgets.QApplication.clipboard().setText(texto_lista(self.obj))

        def getStandardButtons(self):
            return QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        def accept(self):
            self.doc.commitTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

        def reject(self):
            self.doc.abortTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

    def _caminho_da_selecao():
        for s in FreeCADGui.Selection.getSelection():
            if not e_tubulacao(s) and hasattr(s, "Shape") and s.Shape.Edges:
                return s
        doc = FreeCAD.ActiveDocument
        if doc is not None:
            import PrumoEsboco3D
            e3 = [o for o in doc.Objects if PrumoEsboco3D.e_esboco3d(o)]
            if len(e3) == 1:
                return e3[0]
        return None

    def abrir_painel(obj=None):
        if FreeCADGui.Control.activeDialog():
            FreeCADGui.Control.closeDialog()
        if obj is None:
            caminho = _caminho_da_selecao()
            if caminho is None:
                QtWidgets.QMessageBox.information(
                    FreeCADGui.getMainWindow(), "Tubulação",
                    "Selecione o traçado da tubulação (um Esboço 3D ou um esboço com linhas retas) e chame "
                    "Tubulação de novo.\n\nPara desenhar o traçado no espaço, use Esboço 3D.")
                return None
            doc = caminho.Document
            doc.openTransaction("Tubulação")
            obj = criar(caminho, doc=doc)
        else:
            obj.Document.openTransaction("Editar tubulação")
        painel = PainelTubulacao(obj)
        FreeCADGui.Control.showDialog(painel)
        return painel

    class CmdTubulacao:
        def GetResources(self):
            return {"Pixmap": PrumoUtil.icone("tubulacao.svg"),
                    "MenuText": "Tubulação",
                    "ToolTip": "Tubos e conexões automáticos sobre o traçado (Esboço 3D ou esboço): joelhos, "
                               "tês, reduções e cruzetas do catálogo, tubo cortado na medida e lista de "
                               "materiais."}

        def IsActive(self):
            return FreeCAD.ActiveDocument is not None

        def Activated(self):
            abrir_painel()
