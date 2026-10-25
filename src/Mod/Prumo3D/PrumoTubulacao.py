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
        forma = PrumoEsboco3D.forma_obj(caminho, 0.0)          # sem as linhas de construção
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


def _arestas_globais(caminho):
    """[(nome 'EdgeN', a, b)] das linhas retas do traçado, em coordenadas globais."""
    import PrumoUtil
    out = []
    try:
        sh = PrumoUtil.forma_global(caminho)
    except Exception:
        return out
    for i, e in enumerate(sh.Edges):
        if e.Length > 1e-6 and len(e.Vertexes) == 2:
            out.append(("Edge%d" % (i + 1), FreeCAD.Vector(e.Vertexes[0].Point), FreeCAD.Vector(e.Vertexes[1].Point)))
    return out


def _mesma_linha(a, b, c, d):
    return ((a - c).Length < TOL_NO and (b - d).Length < TOL_NO) or ((a - d).Length < TOL_NO and (b - c).Length < TOL_NO)


def trechos_das_arestas(caminho, segs, nomes):
    """Índices dos trechos que correspondem às arestas escolhidas na vista (Edge3 → trecho)."""
    arestas = {n: (a, b) for n, a, b in _arestas_globais(caminho)}
    out = []
    for n in nomes:
        if n not in arestas:
            continue
        a, b = arestas[n]
        for i, (c, d) in enumerate(segs):
            if i not in out and _mesma_linha(a, b, c, d):
                out.append(i)
    return sorted(out)


def arestas_dos_trechos(caminho, segs, idxs):
    """Nomes das arestas do traçado que formam os trechos dados (para marcar na vista)."""
    out = []
    arestas = _arestas_globais(caminho)
    for i in idxs:
        if not 0 <= i < len(segs):
            continue
        c, d = segs[i]
        for n, a, b in arestas:
            if _mesma_linha(a, b, c, d) and n not in out:
                out.append(n)
    return out


def com_diametro(itens, idxs, d, padrao):
    """Lista 'trecho: DE' com os trechos idxs passando a d (sem repetir o padrão)."""
    alvo = {i + 1 for i in idxs}
    novos = [x for x in itens if int(x.split(":")[0]) not in alvo]
    if d != padrao:
        novos += ["%d: %d" % (t, d) for t in sorted(alvo)]
    return sorted(novos, key=lambda x: int(x.split(":")[0]))


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


DIRECOES = {"+Z": (0, 0, 1), "-Z": (0, 0, -1), "+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0),
            "-Y": (0, -1, 0)}
NOMES_DIRECAO = {"+Z": "para cima", "-Z": "para baixo", "+X": "+X", "-X": "−X", "+Y": "+Y", "-Y": "−Y",
                 "eixo": "seguindo o tubo"}


def _vdir(chave, u=None):
    if chave == "eixo" or chave not in DIRECOES:
        return None
    return FreeCAD.Vector(*DIRECOES[chave])


def montar(segs, dns, lid=CAT.PADRAO, tampar=False, registros=None, pontos=None):
    """Traçado + diâmetros → tubos, conexões, avisos e lista de corte (sem geometria).
    registros: {trecho (0…): [distância do início do trecho até o centro do registro, mm]}.
    pontos (torneiras): {trecho: [(posição, direção)]}: posição em mm do início, ou "inicio"/"fim" (ponta
    solta); direção "+Z", "-Z", "±X", "±Y" ou "eixo" (na ponta, seguindo o tubo)."""
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

    def conferir(chave, k, peca):
        motivo = CAT.a_conferir(L, chave, k)
        if motivo:
            msg = "%s: medida a conferir no catálogo (%s)." % (peca, motivo)
            if msg not in avisos:
                avisos.append(msg)

    for k, its in inc.items():
        P = nos[k]
        n = len(its)
        if n == 0:
            continue
        if n == 1:
            s, pt, u = its[0]
            recuo[(s, pt)] = 0.0
            ponta = [dr for pos, dr in (pontos or {}).get(s, []) if pos == ("inicio" if pt == 0 else "fim")]
            if ponta:
                d = dns[s]
                dv = _vdir(ponta[0])
                if dv is not None and abs(dv.dot(u)) > 0.99:
                    dv = None                     # na direção do próprio tubo: luva com bucha
                if dv is None:
                    if d not in L.get("luva_bucha", {}):
                        avisos.append("Trecho %d: não há luva com bucha de latão de %d mm no catálogo (torneira "
                                      "na ponta)." % (s + 1, d))
                        continue
                    lb = L["luva_bucha"][d]
                    c = _rec("Luva com bucha", "Luva soldável e com bucha de latão %d × %s" % (d, lb["rosca"]), P,
                             [(s, pt, u, d, -(lb["A"] - bolsa[d]))], L["corpo"][d],
                             ["Torneira %s (representação simplificada)" % lb["rosca"]])
                    c["torneira"] = (P - u * (lb["A"] - bolsa[d]), -u)
                    conexoes.append(c)
                else:
                    if d not in L.get("joelho_bucha", {}):
                        avisos.append("Trecho %d: não há joelho com bucha de latão de %d mm no catálogo (torneira "
                                      "na ponta)." % (s + 1, d))
                        continue
                    jb = L["joelho_bucha"][d]
                    dv = (dv - u * dv.dot(u)).normalize()
                    c = _rec("Joelho com bucha", "Joelho 90° soldável e com bucha de latão %d × %s" % (d, jb["rosca"]),
                             P, [(s, pt, u, d, jb["A"]), (-1, 9, dv, d, jb["A"])], L["corpo"][d],
                             ["Torneira %s (representação simplificada)" % jb["rosca"]])
                    c["torneira"] = (P + dv * jb["A"], dv)
                    conexoes.append(c)
                    recuo[(s, pt)] = jb["A"] - bolsa[d]
                continue
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
                    continua.append(((s1, p1), (s2, p2)))
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
                    conferir("bucha_curta", (D, d), "Bucha curta %d × %d" % (D, d))
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
                            conferir("bucha_curta", (D, dd), "Bucha curta %d × %d" % (D, dd))
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
                    conferir("bucha_curta", (D, dr), "Bucha curta %d × %d" % (D, dr))
                elif (D, dr) in L["bucha_longa"]:
                    extras.append("Bucha de redução soldável longa %d × %d" % (D, dr))
                    conferir("bucha_longa", (D, dr), "Bucha longa %d × %d" % (D, dr))
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
    ponta_peca = {}     # (seg, ponta) -> índice do tubo que chega naquela ponta
    for s, (na, nb) in enumerate(lig):
        if na == nb:
            continue
        a, b = nos[na], nos[nb]
        u = (b - a).normalize()
        comp_seg = (b - a).Length
        ra, rb = recuo.get((s, 0), 0.0), recuo.get((s, 1), 0.0)
        # registros no trecho: dividem o tubo (cada metade entra numa bolsa do registro)
        cortes = []
        for pos in sorted((registros or {}).get(s, [])):
            d = dns[s]
            if d not in L.get("registro", {}):
                avisos.append("Trecho %d: não há registro de %d mm no catálogo." % (s + 1, d))
                continue
            A, bol = L["registro"][d]["A"], L["registro"][d]["bolsa"]
            if pos - A / 2.0 < ra + 1.0 or pos + A / 2.0 > comp_seg - rb - 1.0:
                avisos.append("Trecho %d: o registro a %.0f mm do início não cabe entre as conexões."
                              % (s + 1, pos))
                continue
            cortes.append((pos - (A / 2.0 - bol), pos + (A / 2.0 - bol)))
            conexoes.append(_rec("Registro", "Registro de esfera soldável %d mm" % d, a + u * pos,
                                 [(s, 2, u, d, A / 2.0), (s, 3, -u, d, A / 2.0)], L["registro"][d]["corpo"]))
        for pos, dr in (pontos or {}).get(s, []):
            if pos in ("inicio", "fim"):
                continue
            d = dns[s]
            if d not in L.get("te_bucha", {}):
                avisos.append("Trecho %d: não há tê com bucha de latão de %d mm no catálogo (torneira no meio)."
                              % (s + 1, d))
                continue
            tb_ = L["te_bucha"][d]
            A, bol = tb_["A"], bolsa[d]
            dv = _vdir(dr) or FreeCAD.Vector(0, 0, 1)
            dv = dv - u * dv.dot(u)
            if dv.Length < 1e-6:
                avisos.append("Trecho %d: a torneira no meio não pode sair na direção do próprio tubo." % (s + 1))
                continue
            dv.normalize()
            if pos - A / 2.0 < ra + 1.0 or pos + A / 2.0 > comp_seg - rb - 1.0:
                avisos.append("Trecho %d: a torneira a %.0f mm do início não cabe entre as conexões."
                              % (s + 1, pos))
                continue
            P = a + u * pos
            cortes.append((pos - (A / 2.0 - bol), pos + (A / 2.0 - bol)))
            c = _rec("Tê com bucha", "Tê soldável e com bucha de latão %d × %s" % (d, tb_["rosca"]), P,
                     [(s, 2, u, d, A / 2.0), (s, 3, -u, d, A / 2.0), (-1, 9, dv, d, tb_["B"])], L["corpo"][d],
                     ["Torneira %s (representação simplificada)" % tb_["rosca"]])
            c["torneira"] = (P + dv * tb_["B"], dv)
            conexoes.append(c)
        cortes.sort()
        trechos_tubo = []
        ini = ra
        for c0, c1 in cortes:
            trechos_tubo.append((ini, c0))
            ini = c1
        trechos_tubo.append((ini, comp_seg - rb))
        for k, (t0, t1) in enumerate(trechos_tubo):
            if t1 - t0 <= 1.0:
                avisos.append("Trecho %d curto demais: as conexões das pontas já ocupam o espaço." % (s + 1))
                continue
            tubos.append({"seg": s, "ini": a + u * t0, "fim": a + u * t1, "dn": dns[s], "corte": t1 - t0})
            if k == 0:
                ponta_peca[(s, 0)] = len(tubos) - 1
            if k == len(trechos_tubo) - 1:
                ponta_peca[(s, 1)] = len(tubos) - 1
    # trechos alinhados sem conexão viram um tubo só na lista de corte
    grupo = list(range(len(tubos)))

    def raiz(i):
        while grupo[i] != i:
            grupo[i] = grupo[grupo[i]]
            i = grupo[i]
        return i
    for (s1, p1), (s2, p2) in continua:
        t1, t2 = ponta_peca.get((s1, p1)), ponta_peca.get((s2, p2))
        if t1 is not None and t2 is not None:
            grupo[raiz(t1)] = raiz(t2)
    pecas = {}
    for i, t in enumerate(tubos):
        r = raiz(i)
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


def solido_torneira(p, u):
    """Torneira de parede em volume simples (corpo, castelo e bica): só para ver no modelo."""
    import Part
    corpo = _cil(13.0, p, u, 45.0)
    fim = p + u * 45.0
    baixo = FreeCAD.Vector(0, 0, -1) if abs(u.z) < 0.9 else FreeCAD.Vector(1, 0, 0)
    bica = _cil(6.0, fim - u * 12.0, baixo, 110.0)
    cima = -baixo
    castelo = _cil(9.0, fim - u * 25.0, cima, 35.0).fuse(Part.makeSphere(14.0, fim - u * 25.0 + cima * 40.0))
    return corpo.fuse(bica).fuse(castelo)


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
    if c.get("torneira"):
        corpo = corpo.fuse(solido_torneira(*c["torneira"]))
    if c["tipo"] == "Registro":
        u = c["pernas"][0][2]
        cima = FreeCAD.Vector(0, 0, 1) if abs(u.z) < 0.9 else FreeCAD.Vector(1, 0, 0)
        cima = (cima - u * cima.dot(u)).normalize()
        dd = c["pernas"][0][3]
        rg = L["registro"][dd]
        corpo = corpo.fuse(_cil(rg["corpo"] / 2.0 * 0.55, P, cima, rg["altura"]))
        alavanca = _cil(4.0, P + cima * (rg["altura"] - 4.0), u, rg["alavanca"] * 0.5)
        corpo = corpo.fuse(alavanca)
    if len(c["pernas"]) > 1 and c["tipo"] not in ("Luva", "Luva de redução", "Registro", "Luva com bucha"):
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
        add("App::PropertyStringList", "Registros", "Tubulação",
            "Registros de esfera: 'trecho: distância do início até o centro (mm)' (ex.: '2: 300')", [])
        add("App::PropertyStringList", "Pontos", "Tubulação",
            "Torneiras: 'trecho: posição: direção' — posição em mm do início, ou inicio/fim (ponta solta); "
            "direção +Z, -Z, +X, -X, +Y, -Y ou eixo (ex.: '3: fim: eixo', '2: 800: +Z')", [])
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

    def registros(self, obj):
        reg = {}
        for item in getattr(obj, "Registros", []) or []:
            try:
                t, pos = item.split(":")
                reg.setdefault(int(t) - 1, []).append(float(pos.replace("mm", "").replace(",", ".").strip()))
            except ValueError:
                continue
        return reg

    def pontos(self, obj):
        pts = {}
        for item in getattr(obj, "Pontos", []) or []:
            partes = [x.strip() for x in item.split(":")]
            if len(partes) < 2:
                continue
            try:
                t = int(partes[0]) - 1
            except ValueError:
                continue
            pos = partes[1].lower()
            if pos not in ("inicio", "fim"):
                try:
                    pos = float(pos.replace("mm", "").replace(",", "."))
                except ValueError:
                    continue
            dr = partes[2] if len(partes) > 2 and partes[2] else ("eixo" if pos in ("inicio", "fim") else "+Z")
            pts.setdefault(t, []).append((pos, dr))
        return pts

    def calcular(self, obj):
        segs, avisos = segmentos_do_caminho(obj.Caminho)
        dns = self.diametros(obj, len(segs))
        res = montar(segs, dns, obj.Linha, obj.TamparPontas, self.registros(obj), self.pontos(obj))
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
            import PrumoPainel as P
            raiz = QtWidgets.QVBoxLayout(self.form)
            dica = P.Mensagem(
                "Escolha a linha e o diâmetro: tubos e conexões saem sozinhos em cada nó do traçado "
                "(joelhos, tês, reduções, cruzetas). Na tabela, mude o diâmetro de um trecho ou ponha um "
                "registro de esfera pela distância do início do trecho.")
            raiz.addWidget(dica)
            card_l, fl = P.bloco("Linha", "tipo", QtWidgets.QFormLayout)
            self.lb_caminho = QtWidgets.QLabel(obj.Caminho.Label if obj.Caminho else "—")
            bt_sel = QtWidgets.QPushButton("Usar seleção")
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
            raiz.addWidget(card_l)
            card_s, ls = P.bloco("Trechos escolhidos na vista", "selecao")
            self.lb_sel = QtWidgets.QLabel()
            self.lb_sel.setWordWrap(True)
            ls.addWidget(self.lb_sel)
            hs = QtWidgets.QHBoxLayout()
            self.dn_sel = QtWidgets.QComboBox()
            for d in CAT.linha(self.obj.Linha)["diametros"]:
                self.dn_sel.addItem(_dn_txt(d), d)
            hs.addWidget(self.dn_sel, 1)
            self.bt_aplicar = QtWidgets.QPushButton("Aplicar aos escolhidos")
            self.bt_aplicar.setToolTip("Clique nas linhas do traçado na vista (Ctrl para várias) e aplique o diâmetro")
            self.bt_aplicar.clicked.connect(self.aplicar_selecionados)
            hs.addWidget(self.bt_aplicar)
            ls.addLayout(hs)
            hb = QtWidgets.QHBoxLayout()
            bt_todos = QtWidgets.QPushButton("Escolher todos")
            bt_todos.clicked.connect(lambda: self.marcar_trechos(list(range(len(self._segs())))))
            hb.addWidget(bt_todos)
            bt_mesmo = QtWidgets.QPushButton("Mesmo diâmetro")
            bt_mesmo.setToolTip("Escolhe todos os trechos com o diâmetro dos já escolhidos")
            bt_mesmo.clicked.connect(self.mesmo_diametro)
            hb.addWidget(bt_mesmo)
            bt_limpar = QtWidgets.QPushButton("Limpar")
            bt_limpar.clicked.connect(lambda: self.marcar_trechos([]))
            hb.addWidget(bt_limpar)
            ls.addLayout(hb)
            raiz.addWidget(card_s)
            self.escolhidos = []
            self.ponto_clicado = None
            card_p, lp = P.bloco("Torneiras", "furo")
            dp = QtWidgets.QLabel("Escolha um trecho na vista: a torneira entra na ponta solta (luva ou joelho com "
                                  "bucha de latão) ou no ponto clicado do trecho (tê com bucha, cortando o tubo).")
            dp.setWordWrap(True)
            dp.setObjectName("PrumoSub")
            lp.addWidget(dp)
            hd = QtWidgets.QHBoxLayout()
            hd.addWidget(QtWidgets.QLabel("Saída"))
            self.dir_ponto = QtWidgets.QComboBox()
            for k in ("eixo", "+Z", "-Z", "+X", "-X", "+Y", "-Y"):
                self.dir_ponto.addItem(NOMES_DIRECAO[k], k)
            hd.addWidget(self.dir_ponto, 1)
            lp.addLayout(hd)
            hp = QtWidgets.QHBoxLayout()
            self.bt_ponta = QtWidgets.QPushButton("Na ponta solta")
            self.bt_ponta.clicked.connect(self.torneira_na_ponta)
            hp.addWidget(self.bt_ponta)
            self.bt_meio = QtWidgets.QPushButton("No ponto clicado")
            self.bt_meio.setToolTip("Clique no trecho, na vista, onde a torneira deve ficar")
            self.bt_meio.clicked.connect(self.torneira_no_ponto)
            hp.addWidget(self.bt_meio)
            lp.addLayout(hp)
            self.lista_pontos = QtWidgets.QListWidget()
            self.lista_pontos.setMaximumHeight(90)
            lp.addWidget(self.lista_pontos)
            bt_tirar = QtWidgets.QPushButton("Tirar a torneira escolhida")
            bt_tirar.clicked.connect(self.tirar_ponto)
            lp.addWidget(bt_tirar)
            raiz.addWidget(card_p)
            card_t, lay = P.bloco("Trechos", "comprimento")
            raiz.addWidget(card_t)
            self.tabela = QtWidgets.QTableWidget(0, 4)
            self.tabela.setHorizontalHeaderLabels(["Trecho", "Comprimento (mm)", "DE", "Registro a (mm)"])
            self.tabela.horizontalHeaderItem(3).setToolTip(
                "Distância do início do trecho até o centro do registro de esfera; vários: 300; 1200")
            self.tabela.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            self.tabela.verticalHeader().setVisible(False)
            self.tabela.setMinimumHeight(140)
            self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.tabela.itemSelectionChanged.connect(self._linhas_da_tabela)
            lay.addWidget(self.tabela)
            card_m, lay = P.bloco("Lista de materiais", "quantidade")
            raiz.addWidget(card_m)
            self.res = QtWidgets.QTextBrowser()
            self.res.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.res.setMinimumHeight(200)
            lay.addWidget(self.res)
            bt_copiar = QtWidgets.QPushButton("Copiar lista de materiais")
            bt_copiar.setToolTip("Copia conexões, tubos e barras para colar numa planilha")
            bt_copiar.clicked.connect(self.copiar)
            lay.addWidget(bt_copiar)
            P.adotar(self.form)
            self._atualizar()
            FreeCADGui.Selection.addObserver(self)
            self._observando = True
            self._da_vista()

        # ------------------------------------------------ seleção nos dois sentidos
        def _segs(self):
            res = getattr(self.obj.Proxy, "ultimo", None) or {}
            return res.get("segs", [])

        def _da_vista(self):
            """Trechos escolhidos na vista (linhas do traçado) → cartão e tabela."""
            if self._ocupado or self.obj.Caminho is None:
                return
            nomes = []
            for so in FreeCADGui.Selection.getSelectionEx("", 0):
                if so.Object is self.obj.Caminho:
                    nomes += [n for n in so.SubElementNames if n.startswith("Edge")]
            idxs = trechos_das_arestas(self.obj.Caminho, self._segs(), nomes)
            self._mostrar_escolha(idxs)

        def _mostrar_escolha(self, idxs):
            self.escolhidos = idxs
            n = len(idxs)
            if n:
                self.lb_sel.setText("%d trecho%s: %s" % (n, "s" if n > 1 else "",
                                                        ", ".join(str(i + 1) for i in idxs[:12]) + ("…" if n > 12 else "")))
            else:
                self.lb_sel.setText("Nenhum: clique nas linhas do traçado na vista (Ctrl para várias) "
                                    "ou nas linhas da tabela.")
            self.bt_aplicar.setEnabled(bool(n))
            self._ocupado = True
            try:
                self.tabela.clearSelection()
                modo = self.tabela.selectionMode()
                self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
                for i in idxs:
                    if i < self.tabela.rowCount():
                        self.tabela.selectRow(i)
                self.tabela.setSelectionMode(modo)
            finally:
                self._ocupado = False

        def marcar_trechos(self, idxs):
            """Escolhe os trechos na vista (e no cartão e na tabela)."""
            caminho = self.obj.Caminho
            self._ocupado = True
            try:
                FreeCADGui.Selection.clearSelection()
                if caminho is not None:
                    for n in arestas_dos_trechos(caminho, self._segs(), idxs):
                        FreeCADGui.Selection.addSelection(caminho, n)
            finally:
                self._ocupado = False
            self._mostrar_escolha(sorted(idxs))

        def _linhas_da_tabela(self):
            if self._ocupado:
                return
            idxs = sorted({ix.row() for ix in self.tabela.selectionModel().selectedRows()})
            self.marcar_trechos(idxs)

        # ------------------------------------------------ torneiras
        def _pontas_soltas(self, i):
            """'inicio'/'fim' das pontas do trecho i que não encostam em outro trecho."""
            segs = self._segs()
            if not 0 <= i < len(segs):
                return []
            out = []
            for nome, p in (("inicio", segs[i][0]), ("fim", segs[i][1])):
                outros = [j for j, (a, b) in enumerate(segs) if j != i and
                          ((a - p).Length < TOL_NO or (b - p).Length < TOL_NO)]
                if not outros:
                    out.append(nome)
            return out

        def _gravar_pontos(self, itens):
            self.obj.Pontos = itens
            idxs = list(self.escolhidos)
            self._atualizar()
            self.marcar_trechos(idxs)

        def torneira_na_ponta(self):
            if not self.escolhidos:
                return False
            i = self.escolhidos[0]
            soltas = self._pontas_soltas(i)
            if not soltas:
                self.lb_sel.setText("O trecho %d não tem ponta solta: use \"No ponto clicado\"." % (i + 1))
                return False
            ja = [x for x in self.obj.Pontos if x.split(":")[0].strip() == str(i + 1)]
            livre = [p for p in soltas if not any(":" + p in x.replace(" ", "") for x in ja)]
            if not livre:
                return False
            dr = self.dir_ponto.currentData()
            self._gravar_pontos(list(self.obj.Pontos) + ["%d: %s: %s" % (i + 1, livre[-1], dr)])
            return True

        def torneira_no_ponto(self, pos=None):
            if not self.escolhidos:
                return False
            i = self.escolhidos[0]
            segs = self._segs()
            if pos is None:
                if self.ponto_clicado is None:
                    self.lb_sel.setText("Clique no trecho, na vista, no ponto onde a torneira deve ficar.")
                    return False
                a, b = segs[i]
                u = (b - a)
                pos = max(0.0, min(u.Length, (self.ponto_clicado - a).dot(u.normalize())))
            dr = self.dir_ponto.currentData()
            if dr == "eixo":
                dr = "+Z"
            self._gravar_pontos(list(self.obj.Pontos) + ["%d: %.0f: %s" % (i + 1, pos, dr)])
            return True

        def tirar_ponto(self):
            r = self.lista_pontos.currentRow()
            itens = list(self.obj.Pontos)
            if 0 <= r < len(itens):
                del itens[r]
                self._gravar_pontos(itens)

        def _encher_pontos(self):
            self.lista_pontos.clear()
            for x in self.obj.Pontos:
                partes = [p.strip() for p in x.split(":")]
                pos = partes[1] if len(partes) > 1 else ""
                dr = NOMES_DIRECAO.get(partes[2], partes[2]) if len(partes) > 2 else ""
                onde = {"inicio": "no início", "fim": "no fim"}.get(pos, "a %s mm do início" % pos)
                self.lista_pontos.addItem("Trecho %s, %s, saída %s" % (partes[0], onde, dr))

        def mesmo_diametro(self):
            res = getattr(self.obj.Proxy, "ultimo", None) or {}
            dns = res.get("dns", [])
            alvo = {dns[i] for i in self.escolhidos if i < len(dns)}
            if alvo:
                self.marcar_trechos([i for i, d in enumerate(dns) if d in alvo])

        def aplicar_selecionados(self):
            if not self.escolhidos:
                return
            d = self.dn_sel.currentData()
            padrao = int(str(self.obj.Diametro).split()[0])
            self.obj.DiametrosTrechos = com_diametro(list(self.obj.DiametrosTrechos), self.escolhidos, d, padrao)
            idxs = list(self.escolhidos)
            self._atualizar()
            self.marcar_trechos(idxs)

        # observador de seleção do FreeCAD
        def addSelection(self, doc, obj, sub, pnt):
            try:
                if self.obj.Caminho is not None and obj == self.obj.Caminho.Name and pnt:
                    self.ponto_clicado = FreeCAD.Vector(*pnt)
            except Exception:
                pass
            QtCore.QTimer.singleShot(0, self._da_vista)

        def removeSelection(self, doc, obj, sub):
            QtCore.QTimer.singleShot(0, self._da_vista)

        def clearSelection(self, doc):
            QtCore.QTimer.singleShot(0, self._da_vista)

        def _parar(self):
            if getattr(self, "_observando", False):
                try:
                    FreeCADGui.Selection.removeObserver(self)
                except Exception:
                    pass
                self._observando = False

        def _encher_dn(self):
            self._ocupado = True
            try:
                self.dn.clear()
                L = CAT.linha(self.linha.currentData())
                if hasattr(self, "dn_sel"):
                    self.dn_sel.clear()
                for d in L["diametros"]:
                    self.dn.addItem(_dn_txt(d), d)
                    if hasattr(self, "dn_sel"):
                        self.dn_sel.addItem(_dn_txt(d), d)
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

        def _registro(self, i, ed):
            if self._ocupado:
                return
            itens = [x for x in self.obj.Registros if not x.strip().startswith("%d:" % (i + 1))]
            for parte in ed.text().split(";"):
                parte = parte.strip().replace(".", "").replace(",", ".")
                if parte:
                    try:
                        itens.append("%d: %g" % (i + 1, float(parte)))
                    except ValueError:
                        pass
            if itens != list(self.obj.Registros):
                self.obj.Registros = itens
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
                    pos = self.obj.Proxy.registros(self.obj).get(i, [])
                    ed = QtWidgets.QLineEdit("; ".join(PrumoUtil.fmt(p_, 0) for p_ in pos))
                    ed.setPlaceholderText("sem registro")
                    ed.editingFinished.connect(lambda i=i, ed=ed: self._registro(i, ed))
                    self.tabela.setCellWidget(i, 3, ed)
            finally:
                self._ocupado = False
            if hasattr(self, "lista_pontos"):
                self._encher_pontos()
            import PrumoPainel
            PrumoPainel.estreitar(self.form)
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
            self._parar()
            self.doc.commitTransaction()
            FreeCADGui.Control.closeDialog()
            self.doc.recompute()
            return True

        def reject(self):
            self._parar()
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
                    "Tubulação de novo.\n\nPara desenhar o traçado no espaço, use Peça → Esboço → Esboço 3D.")
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
