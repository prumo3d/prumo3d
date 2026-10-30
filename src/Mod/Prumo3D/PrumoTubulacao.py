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


class Valvula(float):
    """Posição (mm do início do trecho) de uma válvula flangeada, com o tipo (gaveta, globo, esfera, retenção)."""

    def __new__(cls, valor, tipo="gaveta"):
        o = float.__new__(cls, valor)
        o.tipo = tipo
        return o


def _mesmo_tipo(pos, q):
    """A posição nova com o mesmo tipo da original (registro, junta ou válvula)."""
    if isinstance(pos, Valvula):
        return Valvula(q, pos.tipo)
    if isinstance(pos, Junta):
        return Junta(q)
    return q


class Junta(float):
    """Posição (mm do início do trecho) de uma junta de desmontagem: par de flanges nas linhas de solda de
    topo, união nas roscadas. Anda junto com os registros quando o trecho é dividido."""
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


def aplicar_caimento(segs, dns, L, ligado=True):
    """Esgoto: inclina os trechos quase horizontais no sentido em que foram desenhados (do início para o fim),
    com a declividade mínima da NBR 8160:1999 (4.2.3.2) pelo diâmetro; os pontos ligados descem juntos.
    Devolve (trechos novos, avisos)."""
    avisos = []
    if not L.get("esgoto"):
        return segs, avisos
    nos, lig = _nos(segs)
    dz = {}
    novos = []
    for i, ((a, b), (na, nb)) in enumerate(zip(segs, lig)):
        h = FreeCAD.Vector(b.x - a.x, b.y - a.y, 0).Length
        comp = (b - a).Length
        if comp < 1e-6:
            novos.append((a, b))
            continue
        horizontal = h > 1e-6 and abs(b.z - a.z) / h < 0.06
        dmin = CAT.declividade_minima(dns[i])
        za = dz.setdefault(na, 0.0)
        if horizontal and ligado:
            atual = (a.z - b.z) / h            # o que já desce no desenho
            queda = max(0.0, dmin * h - (a.z - b.z)) if atual < dmin else 0.0
            alvo = za - queda
            if nb in dz and abs(dz[nb] - alvo) > 0.5:
                avisos.append("Trecho %d: o caimento não fecha com o resto do traçado (diferença de %.0f mm); "
                              "confira o sentido do desenho." % (i + 1, abs(dz[nb] - alvo)))
            else:
                dz[nb] = alvo
        else:
            dz.setdefault(nb, za)
        novos.append((a, b))
    out = []
    for i, ((a, b), (na, nb)) in enumerate(zip(novos, lig)):
        a2 = FreeCAD.Vector(a.x, a.y, a.z + dz.get(na, 0.0))
        b2 = FreeCAD.Vector(b.x, b.y, b.z + dz.get(nb, 0.0))
        h = FreeCAD.Vector(b2.x - a2.x, b2.y - a2.y, 0).Length
        if h > 1e-6 and abs(b2.z - a2.z) / h < 0.06:
            decl = (a2.z - b2.z) / h
            dmin = CAT.declividade_minima(dns[i])
            if decl < dmin - 1e-4:
                avisos.append("Trecho %d: declividade de %.1f %%, abaixo da mínima de %.0f %% para DN %d "
                              "(NBR 8160:1999, 4.2.3.2)." % (i + 1, decl * 100, dmin * 100, dns[i]))
            elif decl > CAT.DECLIVIDADE_MAXIMA + 1e-4:
                avisos.append("Trecho %d: declividade de %.1f %%, acima da máxima de 5 %% (NBR 8160:1999, "
                              "4.2.5.2)." % (i + 1, decl * 100))
        out.append((a2, b2))
    return out, avisos


def dividir_em_tes(segs, dns, registros=None, pontos=None, caixas=None):
    """Ramal que termina no meio de outro trecho (ligação em T desenhada sem quebrar a linha principal):
    divide o trecho principal nesse ponto para o nó receber o tê. Devolve (segs, dns, registros, pontos,
    caixas, origem), com origem[i] = (trecho original, distância do início dele até o início do pedaço i);
    as posições de registros e torneiras passam para o pedaço certo."""
    cortes = {}
    for i, (a, b) in enumerate(segs):
        comp = (b - a).Length
        if comp < 3 * TOL_NO:
            continue
        u = (b - a) * (1.0 / comp)
        for j, (c, d) in enumerate(segs):
            if j == i:
                continue
            for p in (c, d):
                t = (p - a).dot(u)
                if TOL_NO < t < comp - TOL_NO and (a + u * t - p).Length < TOL_NO:
                    lst = cortes.setdefault(i, [])
                    if all(abs(t - x) > TOL_NO for x in lst):
                        lst.append(t)
    # dois trechos que se cruzam pelo meio (nenhum termina ali): divide os dois, e o nó recebe a cruzeta
    for i in range(len(segs)):
        a, b = segs[i]
        li = (b - a).Length
        if li < 3 * TOL_NO:
            continue
        ui = (b - a) * (1.0 / li)
        for j in range(i + 1, len(segs)):
            c, d = segs[j]
            lj = (d - c).Length
            if lj < 3 * TOL_NO:
                continue
            uj = (d - c) * (1.0 / lj)
            n = ui.cross(uj)
            if n.Length < 1e-6:
                continue                    # paralelos
            w = a - c
            bb = ui.dot(uj)
            den = 1.0 - bb * bb
            ti = (bb * uj.dot(w) - ui.dot(w)) / den
            tj = (uj.dot(w) - bb * ui.dot(w)) / den
            if not (TOL_NO < ti < li - TOL_NO and TOL_NO < tj < lj - TOL_NO):
                continue
            if ((a + ui * ti) - (c + uj * tj)).Length > TOL_NO:
                continue                    # passam um por cima do outro, sem se tocar
            for k, t in ((i, ti), (j, tj)):
                lst = cortes.setdefault(k, [])
                if all(abs(t - x) > TOL_NO for x in lst):
                    lst.append(t)
    if not cortes:
        return segs, dns, registros, pontos, caixas, [(i, 0.0) for i in range(len(segs))]
    nsegs, ndns, origem = [], [], []
    pedacos = {}            # trecho original -> [(índice novo, início, fim)]
    for i, (a, b) in enumerate(segs):
        comp = (b - a).Length
        u = (b - a) * (1.0 / comp) if comp > 0 else FreeCAD.Vector()
        ts = [0.0] + sorted(cortes.get(i, [])) + [comp]
        for t0, t1 in zip(ts[:-1], ts[1:]):
            pedacos.setdefault(i, []).append((len(nsegs), t0, t1))
            nsegs.append((a + u * t0, a + u * t1))
            ndns.append(dns[i])
            origem.append((i, t0))

    def onde(i, pos):
        for k, t0, t1 in pedacos[i]:
            if pos <= t1 + 1e-9:
                return k, pos - t0
        k, t0, _t1 = pedacos[i][-1]
        return k, pos - t0
    nreg = None
    if registros:
        nreg = {}
        for i, lst in registros.items():
            for pos in lst:
                k, q = onde(i, pos)
                nreg.setdefault(k, []).append(_mesmo_tipo(pos, q))
    npon = None
    if pontos:
        npon = {}
        for i, lst in pontos.items():
            for pos, dr in lst:
                if pos == "inicio":
                    k, q = pedacos[i][0][0], pos
                elif pos == "fim":
                    k, q = pedacos[i][-1][0], pos
                else:
                    k, q = onde(i, pos)
                npon.setdefault(k, []).append((q, dr))
    ncx = None
    if caixas:
        ncx = {}
        for (i, ponta), tipo in caixas.items():
            k = pedacos[i][0][0] if ponta == "inicio" else pedacos[i][-1][0]
            ncx[(k, ponta)] = tipo
    return nsegs, ndns, nreg, npon, ncx, origem


def _voltar_trechos(res, origem):
    """Devolve a numeração dos trechos do traçado original nos tubos, nas peças e nos avisos."""
    if all(o == (i, 0.0) for i, o in enumerate(origem)):
        return res
    for t in res.get("tubos", []):
        t["pedaco"] = t["seg"]
        t["seg"] = origem[t["seg"]][0]
    for pc in res.get("pecas", []):
        pc["trechos"] = sorted(set(origem[n - 1][0] + 1 for n in pc["trechos"]))
    import re
    res["avisos"] = [re.sub(r"Trecho (\d+)", lambda m: "Trecho %d" % (origem[int(m.group(1)) - 1][0] + 1)
                            if int(m.group(1)) - 1 < len(origem) else m.group(0), a) for a in res["avisos"]]
    return res


def montar(segs, dns, lid=CAT.PADRAO, tampar=False, registros=None, pontos=None, caixas=None, origem=None):
    """Traçado + diâmetros → tubos, conexões (inclusive o tê de um ramal que chega no meio de um trecho),
    avisos e lista de corte. Ver _montar."""
    segs, dns, registros, pontos, caixas, org2 = dividir_em_tes(segs, dns, registros, pontos, caixas)
    if origem is not None:
        org2 = [(origem[i][0], origem[i][1] + t0) for i, t0 in org2]
    res = _voltar_trechos(_montar(segs, dns, lid, tampar, registros, pontos, caixas), org2)
    res["avisos"] += _interferencias(segs, dns, lid, org2)
    return res


def _dist_segmentos(a, b, c, d):
    """Menor distância entre os segmentos ab e cd (3D)."""
    u, v, w = b - a, d - c, a - c
    A, B, C, D, E = u.dot(u), u.dot(v), v.dot(v), u.dot(w), v.dot(w)
    den = A * C - B * B
    sN, sD, tN, tD = 0.0, den, 0.0, den
    if den < 1e-9:
        sN, sD, tN, tD = 0.0, 1.0, E, C
    else:
        sN, tN = B * E - C * D, A * E - B * D
        if sN < 0:
            sN, tN, tD = 0.0, E, C
        elif sN > sD:
            sN, tN, tD = sD, E + B, C
    if tN < 0:
        tN = 0.0
        sN, sD = (0.0, sD) if -D < 0 else ((sD, sD) if -D > A else (-D, A))
    elif tN > tD:
        tN = tD
        sN, sD = (0.0, sD) if (-D + B) < 0 else ((sD, sD) if (-D + B) > A else (-D + B, A))
    sc = 0.0 if abs(sN) < 1e-12 else sN / sD
    tc = 0.0 if abs(tN) < 1e-12 else tN / tD
    return ((w + u * sc) - v * tc).Length


def _interferencias(segs, dns, lid, origem):
    """Tubos que se encostam ou se atravessam sem conexão entre eles (trechos sem nó em comum)."""
    L = CAT.linha(lid)
    nos, lig = _nos(segs)
    av = []
    vistos = set()
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if set(lig[i]) & set(lig[j]):
                continue
            ti, tj = L["tubos"].get(dns[i]), L["tubos"].get(dns[j])
            if not ti or not tj:
                continue
            folga = _dist_segmentos(segs[i][0], segs[i][1], segs[j][0], segs[j][1]) - (ti["De"] + tj["De"]) / 2.0
            if folga < 0:
                par = tuple(sorted((origem[i][0] + 1, origem[j][0] + 1)))
                if par[0] != par[1] and par not in vistos:
                    vistos.add(par)
                    av.append("Trechos %d e %d se encostam ou se atravessam sem conexão (sobreposição de %.0f mm): "
                              "ligue-os num ponto ou afaste-os." % (par[0], par[1], -folga))
    return av


def _montar(segs, dns, lid=CAT.PADRAO, tampar=False, registros=None, pontos=None, caixas=None):
    """Traçado + diâmetros → tubos, conexões, avisos e lista de corte (sem geometria).
    registros: {trecho (0…): [distância do início do trecho até o centro do registro, mm]}.
    caixas (esgoto): {(trecho, "inicio"|"fim"): tipo} — a caixa fica no nó dessa ponta e todos os trechos que
    chegam nele param na parede dela.
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
    tol = L.get("tol_ang", TOL_ANG)
    suf = L.get("sufixo", "soldável")

    def nome_dn(d):
        return CAT.rotulo(L, d)

    def N(chave, dn=None, D=None, d=None, **kw):
        return CAT.nome_peca(L, chave, dn=nome_dn(dn) if dn is not None else "",
                             D=CAT.rotulo_curto(L, D) if D is not None else "",
                             d=CAT.rotulo_curto(L, d) if d is not None else "", **kw)

    def conferir(chave, k, peca):
        motivo = CAT.a_conferir(L, chave, k)
        if motivo:
            msg = "%s: medida a conferir no catálogo (%s)." % (peca, motivo)
            if msg not in avisos:
                avisos.append(msg)

    caixa_no = {}
    for (s_, pt_), tipo in (caixas or {}).items():
        if 0 <= s_ < len(lig):
            caixa_no[lig[s_][0 if pt_ == "inicio" else 1]] = tipo
    for k, its in inc.items():
        P = nos[k]
        n = len(its)
        if n == 0:
            continue
        if k in caixa_no:
            cx = L.get("caixas", {}).get(caixa_no[k])
            if cx is None:
                avisos.append("Nó %d: a linha %s não tem a caixa \"%s\"." % (k + 1, L["nome"], caixa_no[k]))
            else:
                conferir("caixa", caixa_no[k], cx["nome"])
                maior = max(dns[s_] for s_, p_, u_ in its)
                if maior > max(cx["saida"], cx["entrada"]):
                    avisos.append("Nó %d: %s tem saída DN %d e entradas DN %d; chega tubo de DN %d."
                                  % (k + 1, cx["nome"], cx["saida"], cx["entrada"], maior))
                horiz = [u_ for s_, p_, u_ in its if abs(u_.z) < 0.5]
                for s_, p_, u_ in its:
                    recuo[(s_, p_)] = cx["D"] / 2.0 - 3.0 if abs(u_.z) < 0.5 else 0.0
                c = _rec("Caixa", cx["nome"], P, [], cx["D"])
                c["caixa"] = cx
                conexoes.append(c)
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
                    conferir("luva_bucha", d, "Peça da torneira de %s" % nome_dn(d))
                    c = _rec("Luva com bucha", L.get("nome_luva_bucha", "Luva soldável e com bucha de latão %d × %s") % (d, lb["rosca"]), P,
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
                    c = _rec("Joelho com bucha", L.get("nome_joelho_bucha", "Joelho 90° soldável e com bucha de latão %d × %s") % (d, jb["rosca"]),
                             P, [(s, pt, u, d, jb["A"]), (-1, 9, dv, d, jb["A"])], L["corpo"][d],
                             ["Torneira %s (representação simplificada)" % jb["rosca"]])
                    c["torneira"] = (P + dv * jb["A"], dv)
                    conexoes.append(c)
                    recuo[(s, pt)] = jb["A"] - bolsa[d]
                continue
            if tampar == "flange":
                d = dns[s]
                fl = CAT.flange(L, d)
                if fl is None:
                    avisos.append("Trecho %d: não há flange de %s classe %s no catálogo." % (s + 1, nome_dn(d),
                                                                                         L.get("classe", "—")))
                    continue
                c = _rec("Flange", N("flange", dn=d), P, [(s, pt, u, d, fl["Y"])], fl["O"],
                         _extras_flange(L, d, fl, N))
                c["flange"] = fl
                conexoes.append(c)
                recuo[(s, pt)] = fl["Y"]
                continue
            if tampar:
                d = dns[s]
                conferir("cap", d, N("cap", dn=d))
                conexoes.append(_rec("Cap", N("cap", dn=d), P,
                                     [(s, pt, u, d, -(L["cap"][d] - bolsa[d]))], L["corpo"][d]))
            continue
        if n == 2:
            (s1, p1, u1), (s2, p2, u2) = its
            d1, d2 = dns[s1], dns[s2]
            desvio = 180.0 - _ang(u1, u2)
            if desvio < tol:
                if d1 == d2:
                    recuo[(s1, p1)] = recuo[(s2, p2)] = 0.0
                    continua.append(((s1, p1), (s2, p2)))
                    continue
                D, d = max(d1, d2), min(d1, d2)
                if (D, d) in L["luva_reducao"]:
                    A = L["luva_reducao"][(D, d)]
                    folga = (A - bolsa[D] - bolsa[d]) / 2.0
                    pern = [(s, p, u, dd, (folga + bolsa[dd])) for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2))]
                    conexoes.append(_rec("Luva de redução", N("luva_reducao", D=D, d=d), P, pern,
                                         L["corpo"][D]))
                elif (D, d) in L["bucha_curta"] and D in L["luva"]:
                    A = L["luva"][D] / 2.0
                    pern = [(s, p, u, dd, A) for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2))]
                    conexoes.append(_rec("Luva", N("luva", dn=D), P, pern, L["corpo"][D],
                                         [N("bucha_curta", D=D, d=d)]))
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
                if abs(desvio - alvo) < tol:
                    D = max(d1, d2)
                    if D not in L[chave]:
                        avisos.append("%s de %s não está no catálogo (nó %d)." % (rot, nome_dn(D), k + 1))
                        break
                    cf = L[chave][D]
                    conferir(chave, D, "%s %s" % (rot, nome_dn(D)))
                    if L.get("esgoto") and chave == "joelho90" and abs(u1.z) < 0.2 and abs(u2.z) < 0.2:
                        avisos.append("Nó %d: mudança de direção na horizontal com joelho 90°; a NBR 8160:1999 "
                                      "(4.2.3.3) pede peças de até 45° (duas de 45°, ou curva de raio longo)."
                                      % (k + 1))
                    extras = []
                    pern = []
                    for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2)):
                        sal = 0.0
                        if dd != D:
                            if (D, dd) not in L["bucha_curta"]:
                                if L.get("solda_topo"):
                                    avisos.append("Nó %d: a curva muda de %s para %s; ponha a redução "
                                                  "concêntrica num trecho reto." % (k + 1, nome_dn(D), nome_dn(dd)))
                                else:
                                    avisos.append("%s %d com ramal de %d no nó %d: falta bucha %d × %d no "
                                                  "catálogo." % (rot, D, dd, k + 1, D, dd))
                            else:
                                extras.append(N("bucha_curta", D=D, d=dd))
                                conferir("bucha_curta", (D, dd), "Bucha curta %d × %d" % (D, dd))
                                sal = _saliencia_bucha(L, D, dd)
                        pern.append((s, p, u, dd, cf + sal))
                        recuo[(s, p)] = cf + sal - bolsa[dd]
                    conexoes.append(_rec(rot, N(chave, dn=D), P, pern, L["corpo"][D], extras))
                    break
            else:
                D = max(d1, d2)
                if L.get("solda_topo") and tol <= desvio <= 90.0 + tol and D in L["joelho90"] and d1 == d2:
                    # aço: curva de raio longo de 90° cortada no ângulo (o raio é o centro à face da de 90°)
                    cf = L["joelho90"][D] * math.tan(math.radians(min(desvio, 90.0)) / 2.0)
                    conferir("joelho90", D, "Curva 90° %s" % nome_dn(D))
                    pern = [(s, p, u, dd, cf) for s, p, u, dd in ((s1, p1, u1, d1), (s2, p2, u2, d2))]
                    for s, p, u, dd, c_ in pern:
                        recuo[(s, p)] = c_ - bolsa[dd]
                    conexoes.append(_rec("Curva cortada", "%s cortada a %s°" % (
                        N("joelho90", dn=D), ("%.1f" % desvio).rstrip("0").rstrip(".").replace(".", ",")),
                        P, pern, L["corpo"][D]))
                    continue
                avisos.append("Nó %d: a linha muda de direção em %.0f° entre os trechos %d e %d e não há "
                              "conexão para isso no catálogo (%s). Use Ajustar traçado às conexões."
                              % (k + 1, desvio, s1 + 1, s2 + 1,
                                 "uma curva vira no máximo 90°: use duas" if L.get("solda_topo")
                                 else "só curvas de 90° e 45°"))
                recuo[(s1, p1)] = recuo[(s2, p2)] = 0.0
            continue
        if n == 3:
            par = None
            for i in range(3):
                for j in range(i + 1, 3):
                    if 180.0 - _ang(its[i][2], its[j][2]) < tol:
                        par = (i, j)
            if par is None:
                avisos.append("Nó %d: três trechos sem dois alinhados — não há tê para essa geometria. "
                              "Use Ajustar traçado às conexões." % (k + 1))
                for s, p, u in its:
                    recuo[(s, p)] = 0.0
                continue
            ramal = its[3 - par[0] - par[1]]
            corrida = [its[par[0]], its[par[1]]]
            ang_r = _ang(ramal[2], corrida[0][2])
            dr = dns[ramal[0]]
            dc = [dns[c[0]] for c in corrida]
            jn = L.get("juncao") or {}
            if (abs(ang_r - 45.0) < tol or abs(ang_r - 135.0) < tol) and jn:
                # junção a 45°: o ramal aponta para montante (fica a 45° do lado de montante da linha)
                if abs(ang_r - 45.0) < tol:
                    mont, jus = corrida[0], corrida[1]
                else:
                    mont, jus = corrida[1], corrida[0]
                D = max(dns[mont[0]], dns[jus[0]])
                chave = (D, dr) if (D, dr) in jn else None
                if chave is None:
                    avisos.append("Nó %d: não há junção %d × %d no catálogo." % (k + 1, D, dr))
                    for s, p, u in its:
                        recuo[(s, p)] = 0.0
                    continue
                if dns[mont[0]] != dns[jus[0]]:
                    avisos.append("Nó %d: a linha principal muda de diâmetro na junção; ponha a redução num trecho "
                                  "próprio." % (k + 1))
                A, C, c_r = jn[chave]
                conferir("juncao", chave, "Junção %s" % ("%d × %d" % chave))
                # c vai do encontro dos eixos ao fundo da bolsa do ramal: centro até a face = c + bolsa
                pern = [(jus[0], jus[1], jus[2], dns[jus[0]], C), (mont[0], mont[1], mont[2], dns[mont[0]], A - C),
                        (ramal[0], ramal[1], ramal[2], dr, c_r + bolsa[dr])]
                for s, p, u, dd, cf in pern:
                    recuo[(s, p)] = cf - bolsa[dd]
                rot = "Junção simples"
                desc = "Junção simples %s %s" % (suf, ("DN %d" % D) if D == dr else ("DN %d × %d" % (D, dr)))
                conexoes.append(_rec(rot, desc, P, pern, L["corpo"][D]))
                continue
            if abs(ang_r - 90.0) > tol:
                avisos.append("Nó %d: ramal a %.1f° da linha principal; esta linha só tem "
                              "%s. Use Ajustar traçado às conexões." % (
                                  k + 1, ang_r, "tê a 90° e junção a 45°" if L.get("juncao") else "tê a 90°"))
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
                cf_c = L["te"][D]
                cf_r = L.get("te_ramal", {}).get(D, cf_c)
                conferir("te", D, "Tê %s" % nome_dn(D))
                desc = N("te", dn=D)
                rot = "Tê"
            elif (D, dr) in L["te_reducao"]:
                A, B = L["te_reducao"][(D, dr)]
                cf_c, cf_r = A / 2.0, B
                desc = N("te_reducao", D=D, d=dr)
                rot = "Tê de redução"
            else:
                cf_c = cf_r = L["te"][D]
                desc = N("te", dn=D)
                rot = "Tê"
                if (D, dr) in L["bucha_curta"]:
                    extras.append(N("bucha_curta", D=D, d=dr))
                    conferir("bucha_curta", (D, dr), "Bucha curta %d × %d" % (D, dr))
                    cf_r += _saliencia_bucha(L, D, dr)
                elif (D, dr) in L["bucha_longa"]:
                    extras.append(N("bucha_longa", D=D, d=dr))
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
            parceiro = [j for j in range(1, 4) if 180.0 - _ang(its[0][2], its[j][2]) < tol]
            outros = [j for j in range(1, 4) if j not in parceiro]
            ok = (len(parceiro) == 1 and len(outros) == 2 and len(ds) == 1
                  and 180.0 - _ang(its[outros[0]][2], its[outros[1]][2]) < tol
                  and abs(_ang(its[0][2], its[outros[0]][2]) - 90.0) < tol)
            D = max(ds)
            if ok and D in L["cruzeta"]:
                cf = L["cruzeta"][D]
                pern = [(s, p, u, D, cf) for s, p, u in its]
                for s, p, u, dd, c in pern:
                    recuo[(s, p)] = c - bolsa[dd]
                conexoes.append(_rec("Cruzeta", N("cruzeta", dn=D), P, pern, L["corpo"][D]))
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
            if isinstance(pos, Junta):
                junta = _junta(L, s, d, a, u, float(pos), ra, rb, comp_seg, N, nome_dn, avisos)
                if junta:
                    cortes.append(junta[0])
                    conexoes.extend(junta[1])
                continue
            if L.get("valvulas"):
                tipo = getattr(pos, "tipo", "gaveta")
                vv = _valvula_flangeada(L, s, d, a, u, float(pos), tipo, ra, rb, comp_seg, N, nome_dn, avisos)
                if vv:
                    cortes.append(vv[0])
                    conexoes.extend(vv[1])
                continue
            if d not in L.get("registro", {}):
                avisos.append("Trecho %d: não há registro de %d mm no catálogo." % (s + 1, d))
                continue
            A, bol = L["registro"][d]["A"], L["registro"][d]["bolsa"]
            if pos - A / 2.0 < ra + 1.0 or pos + A / 2.0 > comp_seg - rb - 1.0:
                avisos.append("Trecho %d: o registro a %.0f mm do início não cabe entre as conexões."
                              % (s + 1, pos))
                continue
            cortes.append((pos - (A / 2.0 - bol), pos + (A / 2.0 - bol)))
            conexoes.append(_rec("Registro", N("registro", dn=d), a + u * pos,
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
            c = _rec("Tê com bucha", L.get("nome_te_bucha", "Tê soldável e com bucha de latão %d × %s") % (d, tb_["rosca"]), P,
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
    pecas = list(pecas.values())
    # emendas das barras: luva nas linhas roscadas (entra na lista; o tubo segue desenhado inteiro)
    if L.get("emenda") == "luva":
        for d, r in lista_de_corte(pecas, L).items():
            for _i in range(r["emendas"]):
                c = _rec("Luva", N("luva", dn=d), FreeCAD.Vector(), [], L["corpo"].get(d, 0.0))
                c["so_lista"] = True
                conexoes.append(c)
    return {"tubos": tubos, "conexoes": conexoes, "avisos": avisos, "linha": L, "nos": nos,
            "pecas": pecas}


def _saliencia_bucha(L, D, d):
    """Bucha roscada: o sextavado fica para fora da conexão (comprimento − penetração da rosca maior)."""
    if not L.get("bucha_rosca"):
        return 0.0
    return max(0.0, L["bucha_curta"][(D, d)] - L["bolsa"][D])


def _extras_flange(L, d, fl, N):
    """Junta e estojos de uma ligação flangeada (vão com um dos flanges)."""
    ex = [N("junta", dn=d)]
    ex += [N("estojo", dn=d, est=fl["estojo"])] * int(fl["furos"])
    return ex


def _junta(L, s, d, a, u, pos, ra, rb, comp_seg, N, nome_dn, avisos):
    """Junta de desmontagem no meio do trecho. Devolve ((corte_ini, corte_fim), [conexões]) ou None."""
    if L.get("flanges"):
        fl = CAT.flange(L, d)
        if fl is None:
            avisos.append("Trecho %d: não há flange de %s classe %s no catálogo." % (s + 1, nome_dn(d),
                                                                                 L.get("classe", "—")))
            return None
        g = L.get("junta_espessura", 0.0)
        meio = fl["Y"] + g / 2.0
        if pos - meio < ra + 1.0 or pos + meio > comp_seg - rb - 1.0:
            avisos.append("Trecho %d: os flanges a %.0f mm do início não cabem entre as conexões." % (s + 1, pos))
            return None
        f1 = _rec("Flange", N("flange", dn=d), a + u * (pos - g / 2.0), [(s, 2, -u, d, fl["Y"])], fl["O"],
                  _extras_flange(L, d, fl, N))
        f2 = _rec("Flange", N("flange", dn=d), a + u * (pos + g / 2.0), [(s, 3, u, d, fl["Y"])], fl["O"])
        for f in (f1, f2):
            f["flange"] = fl
        return (pos - meio, pos + meio), [f1, f2]
    if L.get("uniao"):
        if d not in L["uniao"]:
            avisos.append("Trecho %d: não há união de %s no catálogo." % (s + 1, nome_dn(d)))
            return None
        A = L["uniao"][d]
        b = L["bolsa"][d]
        motivo = CAT.a_conferir(L, "uniao", d)
        if motivo:
            msg = "%s: medida a conferir no catálogo (%s)." % (N("uniao", dn=d), motivo)
            if msg not in avisos:
                avisos.append(msg)
        if pos - A / 2.0 < ra + 1.0 or pos + A / 2.0 > comp_seg - rb - 1.0:
            avisos.append("Trecho %d: a união a %.0f mm do início não cabe entre as conexões." % (s + 1, pos))
            return None
        c = _rec("União", N("uniao", dn=d), a + u * pos, [(s, 2, u, d, A / 2.0), (s, 3, -u, d, A / 2.0)],
                 L["corpo"][d] * 1.25)
        return (pos - (A / 2.0 - b), pos + (A / 2.0 - b)), [c]
    avisos.append("Trecho %d: a linha %s não tem junta de desmontagem (flange ou união)." % (s + 1, L["nome"]))
    return None


def _valvula_flangeada(L, s, d, a, u, pos, tipo, ra, rb, comp_seg, N, nome_dn, avisos):
    """Válvula flangeada no meio do trecho: a válvula (face a face B16.10), junta e estojos de cada lado e o
    flange de pescoço do tubo. Devolve ((corte_ini, corte_fim), [conexões]) ou None."""
    vv = CAT.valvula(L, tipo, d)
    fl = CAT.flange(L, d)
    nome = CAT.NOMES_VALVULA.get(tipo, tipo)
    if vv is None or fl is None:
        avisos.append("Trecho %d: não há %s de %s classe %s no catálogo." % (s + 1, nome.lower(), nome_dn(d),
                                                                           L.get("classe", "—")))
        return None
    g = L.get("junta_espessura", 0.0)
    meio = vv["ff"] / 2.0 + g + fl["Y"]
    if pos - meio < ra + 1.0 or pos + meio > comp_seg - rb - 1.0:
        avisos.append("Trecho %d: a %s a %.0f mm do início não cabe entre as conexões." % (s + 1, nome.lower(), pos))
        return None
    v = _rec("Válvula", N("valvula", dn=d, nome=nome), a + u * pos,
             [(s, 2, u, d, vv["ff"] / 2.0), (s, 3, -u, d, vv["ff"] / 2.0)], fl["O"])
    v["valvula"] = dict(vv, tipo=tipo)
    v["flange"] = fl
    fs = []
    for sg, pt in ((-1, 2), (1, 3)):
        face = a + u * (pos + sg * (vv["ff"] / 2.0 + g))
        f = _rec("Flange", N("flange", dn=d), face, [(s, pt, u * sg, d, fl["Y"])], fl["O"], _extras_flange(L, d, fl, N))
        f["flange"] = fl
        fs.append(f)
    return (pos - meio, pos + meio), [v] + fs


def solido_valvula(c, L):
    """Válvula em volume simples (só para ver no modelo): flanges da própria válvula, corpo, castelo e volante
    (ou alavanca na esfera; tampa na retenção)."""
    import Part
    P = c["no"]
    vv, fl = c["valvula"], c["flange"]
    u = c["pernas"][0][2]
    dd = c["pernas"][0][3]
    De = L["tubos"][dd]["De"]
    ff = vv["ff"]
    ini = P - u * (ff / 2.0)
    corpo = _cil(fl["O"] / 2.0, ini, u, fl["tf"]).fuse(_cil(fl["O"] / 2.0, P + u * (ff / 2.0 - fl["tf"]), u, fl["tf"]))
    corpo = corpo.fuse(_cil(De * 0.62, ini, u, ff))
    cima = FreeCAD.Vector(0, 0, 1) if abs(u.z) < 0.9 else FreeCAD.Vector(1, 0, 0)
    cima = (cima - u * cima.dot(u)).normalize()
    tipo = vv["tipo"]
    if tipo == "esfera":
        corpo = corpo.fuse(Part.makeSphere(De * 0.85, P))
        corpo = corpo.fuse(_cil(De * 0.12 + 4.0, P, cima, De * 0.9))
        corpo = corpo.fuse(_cil(5.0, P + cima * (De * 0.9), u, max(150.0, 2.5 * De)))
    elif tipo == "retencao":
        corpo = corpo.fuse(Part.makeSphere(De * 0.8, P))
        corpo = corpo.fuse(_cil(De * 0.55, P, cima, De * 0.95))
    else:
        corpo = corpo.fuse(Part.makeSphere(De * (0.85 if tipo == "globo" else 0.7), P))
        corpo = corpo.fuse(_cil(De * 0.35, P, cima, vv["altura"] * 0.55))
        corpo = corpo.fuse(_cil(max(6.0, De * 0.06), P, cima, vv["altura"]))
        aro = Part.makeTorus(vv["volante"] / 2.0, max(4.0, vv["volante"] * 0.03), P + cima * vv["altura"], cima)
        corpo = corpo.fuse(aro)
    ri = De / 2.0 - L["tubos"][dd]["e"]
    return corpo.cut(_cil(ri, ini - u * 0.5, u, ff + 1.0))


def soldas_de_topo(res):
    """Soldas de topo da linha: cada ponta de conexão ligada a tubo, mais as emendas de barra."""
    L = res["linha"]
    if not L.get("solda_topo"):
        return 0
    n = sum(1 for c in res["conexoes"] if not c.get("so_lista") and c["tipo"] not in ("Caixa", "Válvula")
            for p in c["pernas"] if p[0] >= 0)
    n += sum(r["emendas"] for r in lista_de_corte(res.get("pecas", []), L).values())
    return n


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


def solido_caixa(c):
    """Caixa em volume simples: corpo cilíndrico com o fundo abaixo do eixo da saída."""
    cx = c["caixa"]
    P = c["no"]
    fundo = P - FreeCAD.Vector(0, 0, cx["saida"] / 2.0 + 15.0)
    ext = _cil(cx["D"] / 2.0, fundo, FreeCAD.Vector(0, 0, 1), cx["A"])
    inn = _cil(cx["D"] / 2.0 - 3.0, fundo + FreeCAD.Vector(0, 0, 3.0), FreeCAD.Vector(0, 0, 1), cx["A"])
    return ext.cut(inn)


def solido_conexao(c, L):
    """Sólido da conexão. Em junções o corpo do ramal pode ficar quase tangente à bolsa vizinha e a operação
    booleana sair inválida (sobretudo com caimento): refaz com o corpo 4 % mais grosso e, se preciso, mais fino."""
    if c.get("caixa"):
        return solido_caixa(c)
    s = None
    for k in (1.0, 1.04, 0.96, 1.08):
        s = _solido_conexao(c, L, k)
        if s.isValid() and s.Volume > 0:
            return s
    # último recurso: cada perna furada separadamente, juntas num composto (só desenho; volume aproximado)
    import Part
    P, R = c["no"], c["corpo"] / 2.0
    pecas, miolo = [], []
    for _s, _p, u, dd, cf in c["pernas"]:
        tb, b = L["tubos"][dd], L["bolsa"][dd]
        if cf <= 0:
            continue
        ri = tb["De"] / 2.0 - tb["e"]
        perna = _cil(R, P, u, cf).cut(_cil(tb["De"] / 2.0, P + u * (cf - b), u, b + 0.5)).cut(_cil(ri, P, u, cf))
        pecas.append(perna)
        miolo.append(_cil(ri, P, u, cf))
    esf = Part.makeSphere(R, P)
    for m in miolo:
        esf = esf.cut(m)
    pecas.append(esf)
    comp = Part.makeCompound([x for x in pecas if x.isValid()])
    return comp


def solido_flange(c, L):
    """Flange de pescoço: disco (face no nó) e pescoço cônico até a ponta de solda, furado no diâmetro
    interno do tubo; furos dos estojos no círculo de furação."""
    import Part
    fl = c["flange"]
    s_, p_, u, dd, Y = c["pernas"][0]
    P = c["no"]
    tb = L["tubos"][dd]
    ri = tb["De"] / 2.0 - tb["e"]
    corpo = _cil(fl["O"] / 2.0, P, u, fl["tf"])
    pesc = Part.makeCone(fl["X"] / 2.0, tb["De"] / 2.0, Y - fl["tf"], P + u * fl["tf"], u)
    corpo = corpo.fuse(pesc)
    corpo = corpo.cut(_cil(ri, P - u * 0.5, u, Y + 1.0))
    n = int(fl["furos"])
    if n and fl.get("furo") and fl.get("bc"):
        e1 = u.cross(FreeCAD.Vector(0, 0, 1))
        if e1.Length < 1e-6:
            e1 = u.cross(FreeCAD.Vector(1, 0, 0))
        e1.normalize()
        e2 = u.cross(e1)
        for i in range(n):
            ang = 2 * math.pi * (i + 0.5) / n
            q = P + (e1 * math.cos(ang) + e2 * math.sin(ang)) * (fl["bc"] / 2.0)
            corpo = corpo.cut(_cil(fl["furo"] / 2.0, q - u * 0.5, u, fl["tf"] + 1.0))
    return corpo


def solido_curva(c, L):
    """Curva de raio longo (solda de topo): arco de verdade entre as pontas, raio = centro à face / tan(δ/2)."""
    import Part
    P = c["no"]
    (_s1, _p1, u1, d1, A), (_s2, _p2, u2, _d2, _A2) = c["pernas"][:2]
    tb = L["tubos"][d1]
    delta = math.radians(180.0 - _ang(u1, u2))
    Rc = A / math.tan(delta / 2.0)
    bis = (u1 + u2)
    bis.normalize()
    M = P + bis * (math.hypot(A, Rc) - Rc)
    T1, T2 = P + u1 * A, P + u2 * A
    arco = Part.Wire([Part.Arc(T1, M, T2).toShape()])

    def tubo(r):
        aro = Part.Wire([Part.makeCircle(r, T1, -u1)])
        return arco.makePipeShell([aro], True, True)
    return tubo(tb["De"] / 2.0).cut(tubo(tb["De"] / 2.0 - tb["e"]))


def solido_reducao(c, L):
    """Redução concêntrica (solda de topo): cone entre as duas pontas."""
    import Part
    P = c["no"]
    (_s1, _p1, u1, d1, a1), (_s2, _p2, u2, d2, a2) = c["pernas"][:2]
    t1, t2 = L["tubos"][d1], L["tubos"][d2]
    ini = P + u1 * a1
    H = a1 + a2
    ext = Part.makeCone(t1["De"] / 2.0, t2["De"] / 2.0, H, ini, u2)
    inn = Part.makeCone(t1["De"] / 2.0 - t1["e"], t2["De"] / 2.0 - t2["e"], H + 0.02, ini - u2 * 0.01, u2)
    return ext.cut(inn)


def _solido_conexao(c, L, k=1.0):
    import Part
    if c["tipo"] == "Flange":
        return solido_flange(c, L)
    if c["tipo"] == "Válvula":
        return solido_valvula(c, L)
    if L.get("solda_topo") and c["tipo"] in ("Joelho 90°", "Joelho 45°", "Curva cortada") and len(c["pernas"]) == 2 \
            and c["pernas"][0][3] == c["pernas"][1][3]:
        return solido_curva(c, L)
    if L.get("solda_topo") and c["tipo"] == "Luva de redução":
        return solido_reducao(c, L)
    P = c["no"]
    R = c["corpo"] / 2.0 * k
    corpo = None
    furos = []
    for s, pt, u, dd, cf in c["pernas"]:
        tb = L["tubos"][dd]
        b = L["bolsa"][dd]
        if cf < 0:      # cap: a conexão fica para fora da ponta do tubo
            alt = L["cap"][dd]
            ini = P - u * (alt - b)
            parte = _cil(R, ini, u, alt)
            if b > 0:
                furos.append(_cil(tb["De"] / 2.0, P, u, b + 0.5))
            else:
                furos.append(_cil(tb["De"] / 2.0 - tb["e"], P - u * (alt - tb["e"]), u, alt - tb["e"] + 0.5))
        else:
            parte = _cil(R, P, u, cf)
            if b > 0:
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
    if len(c["pernas"]) > 1 and c["tipo"] not in ("Luva", "Luva de redução", "Registro", "Luva com bucha", "União"):
        corpo = corpo.fuse(Part.makeSphere(R, P))
    for f in furos:
        corpo = corpo.cut(f)
    return corpo.removeSplitter() if hasattr(corpo, "removeSplitter") else corpo


def forma(res):
    import Part
    L = res["linha"]
    sol = [solido_tubo(t, L) for t in res["tubos"]]
    for c in res["conexoes"]:
        if c.get("so_lista"):
            continue
        try:
            sol.append(solido_conexao(c, L))
        except Exception as ex:
            res["avisos"].append("Desenho da conexão %s: %s" % (c["desc"], ex))
    return Part.makeCompound(sol) if sol else Part.Shape()


# ======================================================================== objeto
NOMES_CURTOS = {"gaveta": "gaveta", "globo": "globo", "esfera": "esfera", "retencao": "retenção"}


def _ler_valvula(txt):
    """'1.200 retenção' -> (1200.0, 'retencao'); '300' -> (300.0, None); inválido -> (None, None)."""
    import re
    import unicodedata
    t = (txt or "").strip()
    m = re.match(r"^([\d.,]+)\s*(?:mm)?\s*([^\d]*)$", t)
    if not m:
        return None, None
    num = m.group(1).replace(".", "").replace(",", ".")
    try:
        v = float(num)
    except ValueError:
        return None, None
    w = unicodedata.normalize("NFKD", m.group(2).strip().lower()).encode("ascii", "ignore").decode()
    tipo = None
    for k in CAT.TIPOS_VALVULA:
        if w and k.startswith(w[:4]):
            tipo = k
    return v, tipo


TEXTO_EMENDA = {"bolsa": "pela bolsa", "solda": "com solda de topo", "luva": "com luva"}


def _dn_txt(d, L=None):
    """Texto do diâmetro na propriedade e nas listas: 'DN 50 (2")' nas linhas de aço, '25 mm' nas outras
    (como nos arquivos já gravados)."""
    return CAT.rotulo(L, d) if L is not None and L.get("nps") else "%d mm" % d


def _acertar_diametros(obj, L):
    """Lista de diâmetros da linha no objeto, mantendo o atual se existir (aceita '25 mm' de arquivos antigos)."""
    lista = [_dn_txt(d, L) for d in L["diametros"]]
    if list(obj.getEnumerationsOfProperty("Diametro")) == lista:
        return
    atual = CAT.dn_do_texto(obj.Diametro) if obj.Diametro else 25
    obj.Diametro = lista
    if atual in L["diametros"]:
        obj.Diametro = _dn_txt(atual, L)
    else:
        obj.Diametro = lista[min(len(lista) - 1, len(lista) // 2)]


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
        elif list(obj.getEnumerationsOfProperty("Linha")) != list(CAT.LINHAS):
            atual = str(obj.Linha)
            obj.Linha = list(CAT.LINHAS)
            obj.Linha = atual if atual in CAT.LINHAS else CAT.PADRAO
        if "Diametro" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "Diametro", "Tubulação", "Diâmetro padrão")
            L = CAT.linha(obj.Linha)
            obj.Diametro = [_dn_txt(d, L) for d in L["diametros"]]
            obj.Diametro = _dn_txt(25 if 25 in L["diametros"] else L["diametros"][0], L)
        else:
            _acertar_diametros(obj, CAT.linha(obj.Linha))
        add("App::PropertyStringList", "DiametrosTrechos", "Tubulação",
            "Diâmetro de trechos específicos: 'trecho: DE' (ex.: '3: 20')", [])
        add("App::PropertyBool", "TamparPontas", "Tubulação", "Põe cap nas pontas soltas", False)
        add("App::PropertyBool", "Caimento", "Tubulação",
            "Esgoto: inclina os trechos horizontais com a declividade mínima da NBR 8160 (no sentido do desenho)",
            True)
        add("App::PropertyStringList", "Registros", "Tubulação",
            "Registros de esfera: 'trecho: distância do início até o centro (mm)' (ex.: '2: 300')", [])
        add("App::PropertyStringList", "Pontos", "Tubulação",
            "Torneiras: 'trecho: posição: direção' — posição em mm do início, ou inicio/fim (ponta solta); "
            "direção +Z, -Z, +X, -X, +Y, -Y ou eixo (ex.: '3: fim: eixo', '2: 800: +Z')", [])
        add("App::PropertyStringList", "Caixas", "Tubulação",
            "Esgoto: caixas no nó de uma ponta: 'trecho: inicio|fim: tipo' (tipos: sifonada_100, sifonada_150, "
            "sifonada_150_75, inspecao, gordura)", [])
        add("App::PropertyStringList", "Juntas", "Tubulação",
            "Juntas de desmontagem (par de flanges na solda de topo, união na rosca): 'trecho: distância do "
            "início (mm)'", [])
        add("App::PropertyBool", "FlangePontas", "Tubulação",
            "Solda de topo: flange nas pontas soltas (ligação com bocal de equipamento)", False)
        if "ClasseFlange" not in obj.PropertiesList:
            obj.addProperty("App::PropertyEnumeration", "ClasseFlange", "Tubulação", "Classe de pressão dos flanges")
            obj.ClasseFlange = ["150", "300"]
            obj.ClasseFlange = "150"
        add("App::PropertyStringList", "Conexoes", "Resultados", "Conexões (quantidade × peça)", [], ro=True)
        add("App::PropertyStringList", "ListaCorte", "Resultados", "Tubos por diâmetro e barras", [], ro=True)
        add("App::PropertyStringList", "Avisos", "Resultados", "Avisos do traçado", [], ro=True)
        add("App::PropertyLength", "ComprimentoTubos", "Resultados", "Comprimento total de tubo", 0.0, ro=True)
        add("App::PropertyInteger", "Barras", "Resultados", "Barras de tubo necessárias", 0, ro=True)
        add("App::PropertyInteger", "Soldas", "Resultados", "Soldas de topo (linhas de aço soldadas)", 0, ro=True)

    def onDocumentRestored(self, obj):
        obj.Proxy = self
        self._props(obj)

    def onChanged(self, obj, prop):
        """Trocar a linha troca a lista de diâmetros (mantém o atual se existir na linha nova)."""
        if prop != "Linha" or "Diametro" not in obj.PropertiesList or "DiametrosTrechos" not in obj.PropertiesList:
            return
        L = CAT.linha(obj.Linha)
        lista = [_dn_txt(d, L) for d in L["diametros"]]
        if list(obj.getEnumerationsOfProperty("Diametro")) == lista:
            return
        _acertar_diametros(obj, L)
        if FreeCAD.GuiUp and getattr(obj, "ViewObject", None) is not None:
            try:
                obj.ViewObject.ShapeColor = L["cor"]
            except Exception:
                pass
        validos = set(L["diametros"])
        obj.DiametrosTrechos = [x for x in obj.DiametrosTrechos
                                if x.split(":")[1].replace("mm", "").strip().isdigit()
                                and int(x.split(":")[1].replace("mm", "").strip()) in validos]

    def diametros(self, obj, n):
        padrao = CAT.dn_do_texto(obj.Diametro)
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
        """Registros e juntas de desmontagem (Junta) por trecho."""
        reg = {}
        for prop, tipo in (("Registros", float), ("Juntas", Junta)):
            for item in getattr(obj, prop, []) or []:
                try:
                    partes = [x.strip() for x in item.split(":")]
                    v = float(partes[1].replace("mm", "").replace(",", "."))
                    if prop == "Registros" and len(partes) > 2 and partes[2]:
                        v = Valvula(v, partes[2])
                    else:
                        v = tipo(v)
                    reg.setdefault(int(partes[0]) - 1, []).append(v)
                except (ValueError, IndexError):
                    continue
        return reg

    def linha(self, obj):
        """A linha do catálogo com a classe dos flanges escolhida."""
        L = CAT.linha(obj.Linha)
        if L.get("flanges"):
            L = dict(L, classe=int(str(getattr(obj, "ClasseFlange", "150") or "150")))
        return L

    def pontas(self, obj):
        L = CAT.linha(obj.Linha)
        if L.get("flanges") and getattr(obj, "FlangePontas", False):
            return "flange"
        return bool(obj.TamparPontas)

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

    def caixas(self, obj):
        cx = {}
        for item in getattr(obj, "Caixas", []) or []:
            partes = [x.strip() for x in item.split(":")]
            if len(partes) < 3 or partes[1] not in ("inicio", "fim"):
                continue
            try:
                cx[(int(partes[0]) - 1, partes[1])] = partes[2]
            except ValueError:
                continue
        return cx

    def calcular(self, obj):
        segs, avisos = segmentos_do_caminho(obj.Caminho)
        dns = self.diametros(obj, len(segs))
        segs_orig, dns_orig = list(segs), list(dns)      # o painel trabalha com os trechos do traçado
        L = self.linha(obj)
        # ramal no meio de um trecho: divide antes do caimento, para o ponto do tê descer junto
        segs, dns, reg, pon, cx, origem = dividir_em_tes(segs, dns, self.registros(obj), self.pontos(obj),
                                                         self.caixas(obj))
        if L.get("esgoto") and all(d in L["tubos"] for d in dns):
            segs, av = aplicar_caimento(segs, dns, L, bool(getattr(obj, "Caimento", True)))
            avisos += av
        res = montar(segs, dns, L, self.pontas(obj), reg, pon, cx, origem=origem)
        res["avisos"] = avisos + res["avisos"]
        # o painel trabalha com um trecho por linha do traçado: junta de volta os pedaços (já com caimento)
        juntos = {}
        for k, (i, _t0) in enumerate(origem):
            a, b = segs[k]
            juntos[i] = (juntos[i][0], b) if i in juntos else (a, b)
        res["segs"] = [juntos.get(i, sg) for i, sg in enumerate(segs_orig)]
        res["dns"] = dns_orig
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
            linhas.append("Tubo %s: %d barra(s) de %.0f m — peças (mm): %s%s" % (
                CAT.rotulo(L, d) if L.get("nps") else "%d mm" % d, r["barras"], L["barra"] / 1000.0, pcs,
                ("; %d emenda(s) %s" % (r["emendas"], TEXTO_EMENDA.get(L.get("emenda", "bolsa"))))
                if r["emendas"] else ""))
        obj.ListaCorte = linhas
        obj.Barras = barras
        obj.ComprimentoTubos = total
        obj.Avisos = res["avisos"]
        if "Soldas" in obj.PropertiesList:
            obj.Soldas = soldas_de_topo(res)
        self.ultimo = res

    def dumps(self):
        return None

    def loads(self, state):
        return None


# ======================================================================== ajustar o traçado às conexões
TOL_AJUSTE = 20.0     # graus: até essa diferença o ângulo desenhado vira o da conexão (mais que isso, só avisa)


def angulos_da_linha(L):
    """(desvios de canto que têm conexão, ângulos de ramal que têm conexão, canto livre até 90°?)."""
    cantos = [a for a, ch in ((90.0, "joelho90"), (45.0, "joelho45")) if L.get(ch)]
    ramais = [90.0] + ([45.0, 135.0] if L.get("juncao") else [])
    return cantos, ramais, bool(L.get("solda_topo"))


def _girar_para(ref, u, alvo):
    """Direção no plano de (ref, u) que faz `alvo` graus com ref, do lado de u."""
    w = u - ref * u.dot(ref)
    if w.Length < 1e-9:
        return None
    w.normalize()
    a = math.radians(alvo)
    v = ref * math.cos(a) + w * math.sin(a)
    v.normalize()
    return v


def _mais_perto(valor, opcoes):
    return min(opcoes, key=lambda o: abs(o - valor)) if opcoes else None


def ajustes_do_tracado(pontos, segs, L, tol_max=TOL_AJUSTE, ancora=0):
    """Novos pontos com os cantos e ramais nos ângulos que têm conexão na linha L, e a lista do que mudou.

    Percorre o traçado a partir do ponto âncora: o que já foi visto fica parado e o trecho que sai do nó gira (no
    plano dos dois trechos) até o ângulo da conexão mais próxima, levando junto o que vem depois (os
    comprimentos não mudam). Só mexe quando a diferença é de até tol_max graus; acima disso fica como está (o
    aviso da tubulação explica). Devolve (pontos, [(nó, de°, para°)])."""
    import PrumoEsboco3D as E3
    pts = [FreeCAD.Vector(p) for p in pontos]
    tol = L.get("tol_ang", TOL_ANG)
    cantos, ramais, canto_livre = angulos_da_linha(L)
    # pontos no mesmo lugar (ramal preso a um ponto) andam juntos: ligações de comprimento zero
    n = len(pts)
    grupo = list(range(n))
    for i in range(n):
        for j in range(i):
            if (pts[i] - pts[j]).Length < TOL_NO:
                grupo[i] = grupo[j]
                break
    elos = [(i, grupo[i]) for i in range(n) if grupo[i] != i]
    mudancas = []

    def dirs(no):
        """[(k, ponta que fica no nó, direção saindo do nó)] dos trechos que chegam no grupo `no`."""
        r = []
        for k, (i, j) in enumerate(segs):
            for pi, pj in ((i, j), (j, i)):
                if grupo[pi] == no:
                    d = pts[pj] - pts[pi]
                    if d.Length > 1e-9:
                        d.normalize()
                        r.append((k, pi, pj, d))
        return r

    def girar(k, pi, alvo_dir):
        novos = E3.mudar_trecho(pts, list(segs) + elos, k, direcao=alvo_dir, ancora=pi)
        if novos is None:
            return False
        pts[:] = novos
        return True

    visto = {grupo[ancora]}
    fila = [grupo[ancora]]
    while fila:
        no = fila.pop(0)
        its = dirs(no)
        # quem já foi visto (o outro lado está num nó visitado) fica parado
        fixos = [t for t in its if grupo[t[2]] in visto]
        livres = [t for t in its if grupo[t[2]] not in visto]
        if len(its) == 2 and len(fixos) == 1 and livres:
            (_k, _pi, _pj, uf), (k, pi, pj, uo) = fixos[0], livres[0]
            desvio = _ang(uf * -1.0, uo)
            alvo = _mais_perto(desvio, [0.0] + cantos + ([90.0] if canto_livre else []))
            livre = canto_livre and desvio <= 90.0 + tol          # aço: a curva cortada faz qualquer ângulo
            if not livre and abs(alvo - desvio) > tol and abs(alvo - desvio) <= tol_max:
                v = _girar_para(uf * -1.0, uo, alvo)
                if v is not None and girar(k, pi, v):
                    mudancas.append((no, desvio, alvo))
        elif len(its) == 3:
            # a corrida: o par mais perto de alinhado
            pares = [(a, b) for a in range(3) for b in range(a + 1, 3)]
            a, b = max(pares, key=lambda ab: _ang(its[ab[0]][3], its[ab[1]][3]))
            r = 3 - a - b
            c1, c2, rm = its[a], its[b], its[r]
            if 180.0 - _ang(c1[3], c2[3]) > tol and 180.0 - _ang(c1[3], c2[3]) <= tol_max:
                movel = c2 if grupo[c2[2]] not in visto else (c1 if grupo[c1[2]] not in visto else None)
                fixo = c1 if movel is c2 else c2
                if movel is not None and girar(movel[0], movel[1], fixo[3] * -1.0):
                    mudancas.append((no, _ang(c1[3], c2[3]), 180.0))
                    its = dirs(no)
                    c1, c2, rm = its[a], its[b], its[r]
            if grupo[rm[2]] not in visto:
                ang_r = _ang(rm[3], c1[3])
                alvo = _mais_perto(ang_r, ramais)
                if abs(alvo - ang_r) > tol and abs(alvo - ang_r) <= tol_max:
                    v = _girar_para(c1[3], rm[3], alvo)
                    if v is not None and girar(rm[0], rm[1], v):
                        mudancas.append((no, ang_r, alvo))
        for t in dirs(no):
            g = grupo[t[2]]
            if g not in visto:
                visto.add(g)
                fila.append(g)
    return pts, mudancas


def ajustar_tracado(obj):
    """Ajusta o Esboço 3D da tubulação aos ângulos das conexões da linha dela. Devolve a lista de mudanças
    [(nó, de°, para°)] (vazia se nada mudou ou se o traçado não é um Esboço 3D)."""
    import PrumoEsboco3D as E3
    esb = obj.Caminho
    if esb is None or not E3.e_esboco3d(esb):
        return []
    L = CAT.linha(obj.Linha)
    constr = {int(k) for k in getattr(esb, "Construcao", [])}
    todos = E3.segmentos(esb.Pontos, esb.Quebras, esb.Fechado)
    segs = [sg for k, sg in enumerate(todos) if k not in constr]
    novos, mud = ajustes_do_tracado(esb.Pontos, segs, L)
    if not mud:
        return []
    # trecho que girou perde a restrição de eixo que não vale mais
    rs = []
    for r in esb.Restricoes:
        t = r.split(":")
        if t[0] == "eixo" and len(t) > 2:
            k = int(t[1])
            if 0 <= k < len(todos):
                i, j = todos[k]
                d = novos[j] - novos[i]
                e = FreeCAD.Vector(*E3.EIXOS[t[2].strip().upper()])
                if d.Length > 1e-9 and abs(abs(d.normalize().dot(e)) - 1.0) > 1e-6:
                    continue
        rs.append(r)
    esb.Restricoes = rs
    esb.Pontos = novos
    esb.Document.recompute()
    return mud


def ajustar_dependentes(esboco):
    """Depois de editar um Esboço 3D: ajusta os ângulos às conexões das tubulações que usam ele."""
    feitas = []
    for o in list(getattr(esboco, "InList", [])):
        if e_tubulacao(o) and o.Caminho == esboco:
            feitas += ajustar_tracado(o)
    return feitas


def criar(caminho, dn=25, lid=CAT.PADRAO, tampar=False, doc=None, ajustar=True):
    doc = doc or caminho.Document
    obj = doc.addObject("Part::FeaturePython", "Tubulacao")
    obj.Label = "Tubulação"
    Tubulacao(obj)
    obj.Caminho = caminho
    obj.Linha = lid
    obj.Diametro = _dn_txt(dn, CAT.linha(lid))
    obj.TamparPontas = tampar
    if ajustar:
        try:
            mud = ajustar_tracado(obj)
            if mud:
                FreeCAD.Console.PrintMessage("Prumo: traçado ajustado às conexões em %d ponto(s).\n" % len(mud))
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: ajuste do traçado: %s\n" % exc)
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
    res = obj.Proxy.calcular(obj)
    L = res["linha"]
    itens = []
    lc = lista_de_corte(res.get("pecas", []), L)
    for d in sorted(lc):
        r = lc[d]
        tb = L["tubos"][d]
        if L.get("nps"):
            den = "%s (barra de %.0f m)" % (CAT.nome_peca(L, "tubo", dn=CAT.rotulo(L, d)), L["barra"] / 1000.0)
        else:
            den = "Tubo %s %d mm (barra de %.0f m)" % ("soldável" if "soldavel" in L["id"] else "", d,
                                                      L["barra"] / 1000.0)
        itens.append((("tubo", L["id"], d), den, material_de(L, "tubo"), "DE %s × %s — %s m no total" % (
            _num(tb["De"]), _num(tb["e"]), _num(round(r["total"] / 1000.0, 2))), r["barras"], L["fabricante"]))
    for desc, n in resumo_conexoes(res["conexoes"]).items():
        itens.append((("conexao", L["id"], desc), desc, material_de(L, desc), "—", n, L["fabricante"]))
    sd = soldas_de_topo(res)
    if sd:
        itens.append((("solda", L["id"]), "Solda de topo (junta)", "—", "—", sd, "Contagem para inspeção"))
    return itens


def material_de(L, desc):
    """Material da peça: as linhas de aço dão um por tipo (tubo, conexão, flange, junta, estojo)."""
    mats = L.get("materiais")
    if not mats:
        return L["material"]
    d = desc.lower()
    for chave in ("estojo", "junta", "flange", "tubo", "válvula"):
        if d.startswith(chave):
            return mats.get("valvula" if chave == "válvula" else chave, L["material"])
    return mats.get("conexao", L["material"])


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
    if getattr(obj, "Soldas", 0):
        out.append("Soldas de topo: %d" % obj.Soldas)
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
                "(joelhos ou curvas, tês, reduções). Na tabela, mude o diâmetro de um trecho ou ponha registro, "
                "flange ou união pela distância do início do trecho.")
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
            fl.addRow("Diâmetro", self.dn)
            self.cap = QtWidgets.QCheckBox("Pôr cap nas pontas soltas")
            self.cap.setChecked(bool(obj.TamparPontas))
            self.cap.toggled.connect(self._mudou)
            fl.addRow("", self.cap)
            self.fl_pontas = QtWidgets.QCheckBox("Flange nas pontas soltas (bocal de equipamento)")
            self.fl_pontas.setToolTip("A face do flange fica na ponta do traçado; o tubo para no pescoço")
            self.fl_pontas.setChecked(bool(getattr(obj, "FlangePontas", False)))
            self.fl_pontas.toggled.connect(self._mudou)
            fl.addRow("", self.fl_pontas)
            self.classe = QtWidgets.QComboBox()
            for c in ("150", "300"):
                self.classe.addItem("Classe %s" % c, c)
            self.classe.setCurrentIndex(max(0, self.classe.findData(str(getattr(obj, "ClasseFlange", "150")))))
            self.classe.currentIndexChanged.connect(self._mudou)
            self.lb_classe = QtWidgets.QLabel("Flanges")
            fl.addRow(self.lb_classe, self.classe)
            self.caimento = QtWidgets.QCheckBox("Caimento pela NBR 8160 (2 % até DN 75; 1 % de DN 100)")
            self.caimento.setToolTip("Inclina os trechos horizontais no sentido em que foram desenhados")
            self.caimento.setChecked(bool(getattr(obj, "Caimento", True)))
            self.caimento.toggled.connect(self._mudou)
            fl.addRow("", self.caimento)
            self.caimento.setVisible(bool(CAT.linha(obj.Linha).get("esgoto")))
            self.bt_ajustar = QtWidgets.QPushButton("Ajustar traçado às conexões")
            self.bt_ajustar.setToolTip("Gira os trechos do Esboço 3D para os ângulos que têm conexão nesta linha "
                                       "(90° e 45° no PVC e na rosca; tê a 90°), sem mudar os comprimentos. "
                                       "No aço, curva cortada faz qualquer canto até 90°.")
            self.bt_ajustar.clicked.connect(self.ajustar_tracado)
            fl.addRow("", self.bt_ajustar)
            self.lb_ajuste = QtWidgets.QLabel("")
            self.lb_ajuste.setWordWrap(True)
            self.lb_ajuste.setObjectName("PrumoDica")
            fl.addRow("", self.lb_ajuste)
            raiz.addWidget(card_l)
            card_s, ls = P.bloco("Trechos escolhidos na vista", "selecao")
            self.lb_sel = QtWidgets.QLabel()
            self.lb_sel.setWordWrap(True)
            ls.addWidget(self.lb_sel)
            hs = QtWidgets.QHBoxLayout()
            self.dn_sel = QtWidgets.QComboBox()
            for d in CAT.linha(self.obj.Linha)["diametros"]:
                self.dn_sel.addItem(_dn_txt(d, CAT.linha(self.obj.Linha)), d)
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
            self.card_p = card_p
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
            self.card_cx, lc = P.bloco("Caixas de esgoto", "furo")
            dc = QtWidgets.QLabel("Escolha um trecho na vista: a caixa entra na ponta solta dele (ou no fim) e os "
                                  "trechos que chegam ali param na parede da caixa.")
            dc.setWordWrap(True)
            dc.setObjectName("PrumoSub")
            lc.addWidget(dc)
            hc = QtWidgets.QHBoxLayout()
            self.tipo_cx = QtWidgets.QComboBox()
            hc.addWidget(self.tipo_cx, 1)
            bt_cx = QtWidgets.QPushButton("Pôr caixa")
            bt_cx.clicked.connect(self.por_caixa)
            hc.addWidget(bt_cx)
            lc.addLayout(hc)
            self.lista_cx = QtWidgets.QListWidget()
            self.lista_cx.setMaximumHeight(80)
            lc.addWidget(self.lista_cx)
            bt_tcx = QtWidgets.QPushButton("Tirar a caixa escolhida")
            bt_tcx.clicked.connect(self.tirar_caixa)
            lc.addWidget(bt_tcx)
            raiz.addWidget(self.card_cx)
            card_t, lay = P.bloco("Trechos", "comprimento")
            raiz.addWidget(card_t)
            self.tabela = QtWidgets.QTableWidget(0, 5)
            self.tabela.setHorizontalHeaderLabels(["Trecho", "Comprimento (mm)", "Diâmetro", "Registro a (mm)",
                                                   "Flanges a (mm)"])
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
            hm = QtWidgets.QHBoxLayout()
            bt_copiar = QtWidgets.QPushButton("Copiar lista de materiais")
            bt_copiar.setToolTip("Copia conexões, tubos e barras para colar numa planilha")
            bt_copiar.clicked.connect(self.copiar)
            hm.addWidget(bt_copiar)
            self.bt_iso = QtWidgets.QPushButton("Folha isométrica")
            self.bt_iso.setToolTip("Folha A3 com o isométrico da linha, cotas, números das peças, lista de material "
                                   "e lista de corte")
            self.bt_iso.clicked.connect(self.folha_isometrica)
            hm.addWidget(self.bt_iso)
            lay.addLayout(hm)
            P.adotar(self.form)
            self._atualizar()
            FreeCADGui.Selection.addObserver(self)
            self._observando = True
            self._da_vista()

        # ------------------------------------------------ seleção nos dois sentidos
        def _segs(self):
            res = getattr(self.obj.Proxy, "ultimo", None) or {}
            return res.get("segs", [])

        def _vivo(self):
            """O painel ainda está aberto e o objeto existe; senão para de observar a seleção."""
            try:
                import shiboken6
                ok = (self.obj.Document.getObject(self.obj.Name) is not None and shiboken6.isValid(self.form)
                      and bool(FreeCADGui.Control.activeDialog()))
            except Exception:
                ok = False
            if not ok:
                self._parar()
            return ok

        def _da_vista(self):
            """Trechos escolhidos na vista (linhas do traçado) → cartão e tabela."""
            if not self._vivo():
                return
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

        # ------------------------------------------------ caixas
        def _encher_caixas(self):
            L = CAT.linha(self.obj.Linha)
            self.card_cx.setVisible(bool(L.get("caixas")))
            atual = self.tipo_cx.currentData()
            self.tipo_cx.blockSignals(True)
            self.tipo_cx.clear()
            for k, cx in (L.get("caixas") or {}).items():
                self.tipo_cx.addItem(cx["nome"], k)
            if atual is not None and self.tipo_cx.findData(atual) >= 0:
                self.tipo_cx.setCurrentIndex(self.tipo_cx.findData(atual))
            self.tipo_cx.blockSignals(False)
            self.lista_cx.clear()
            for x in self.obj.Caixas:
                partes = [p.strip() for p in x.split(":")]
                nome = (L.get("caixas") or {}).get(partes[2], {}).get("nome", partes[2]) if len(partes) > 2 else x
                self.lista_cx.addItem("%s — trecho %s, %s" % (nome, partes[0], "no início" if partes[1] == "inicio"
                                                              else "no fim"))

        def por_caixa(self):
            if not self.escolhidos or self.tipo_cx.currentData() is None:
                return False
            i = self.escolhidos[0]
            soltas = self._pontas_soltas(i)
            ponta = soltas[-1] if soltas else "fim"
            itens = [x for x in self.obj.Caixas if not x.replace(" ", "").startswith("%d:%s:" % (i + 1, ponta))]
            itens.append("%d: %s: %s" % (i + 1, ponta, self.tipo_cx.currentData()))
            self.obj.Caixas = itens
            idxs = list(self.escolhidos)
            self._atualizar()
            self.marcar_trechos(idxs)
            return True

        def tirar_caixa(self):
            r = self.lista_cx.currentRow()
            itens = list(self.obj.Caixas)
            if 0 <= r < len(itens):
                del itens[r]
                self.obj.Caixas = itens
                self._atualizar()

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
            padrao = CAT.dn_do_texto(self.obj.Diametro)
            self.obj.DiametrosTrechos = com_diametro(list(self.obj.DiametrosTrechos), self.escolhidos, d, padrao)
            idxs = list(self.escolhidos)
            self._atualizar()
            self.marcar_trechos(idxs)

        # observador de seleção do FreeCAD
        def addSelection(self, doc, obj, sub, pnt):
            if not self._vivo():
                return
            try:
                if self.obj.Caminho is not None and obj == self.obj.Caminho.Name and pnt:
                    self.ponto_clicado = FreeCAD.Vector(*pnt)
            except Exception:
                pass
            QtCore.QTimer.singleShot(0, self._da_vista)

        def removeSelection(self, doc, obj, sub):
            if self._vivo():
                QtCore.QTimer.singleShot(0, self._da_vista)

        def clearSelection(self, doc):
            if self._vivo():
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
                    self.dn.addItem(_dn_txt(d, L), d)
                    if hasattr(self, "dn_sel"):
                        self.dn_sel.addItem(_dn_txt(d, L), d)
                atual = CAT.dn_do_texto(self.obj.Diametro)
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
                self.ajustar_tracado(avisar=False)   # outra linha, outros ângulos de conexão
            self.obj.Diametro = _dn_txt(self.dn.currentData(), CAT.linha(self.obj.Linha))
            self.obj.TamparPontas = self.cap.isChecked()
            self.obj.Caimento = self.caimento.isChecked()
            self.obj.FlangePontas = self.fl_pontas.isChecked()
            self.obj.ClasseFlange = self.classe.currentData()
            self.caimento.setVisible(bool(CAT.linha(self.obj.Linha).get("esgoto")))
            self._atualizar()

        def ajustar_tracado(self, avisar=True):
            mud = ajustar_tracado(self.obj)
            if mud:
                txt = "; ".join("%s° → %s°" % (("%.1f" % de).rstrip("0").rstrip(".").replace(".", ","),
                                                ("%.0f" % para)) for _n, de, para in mud[:6])
                self.lb_ajuste.setText("Traçado ajustado em %d ponto(s): %s." % (len(mud), txt))
                self._atualizar()
            elif avisar:
                self.lb_ajuste.setText("Os ângulos do traçado já têm conexão nesta linha (ou estão longe demais "
                                       "de 90°/45° para ajustar sozinho).")
            return mud

        def _dn_trecho(self, i, combo):
            if self._ocupado:
                return
            itens = [x for x in self.obj.DiametrosTrechos if not x.startswith("%d:" % (i + 1))]
            d = combo.currentData()
            padrao = CAT.dn_do_texto(self.obj.Diametro)
            if d != padrao:
                itens.append("%d: %d" % (i + 1, d))
            self.obj.DiametrosTrechos = itens
            self._atualizar()

        def _registro(self, i, ed):
            if self._ocupado:
                return
            itens = [x for x in self.obj.Registros if not x.strip().startswith("%d:" % (i + 1))]
            for parte in ed.text().split(";"):
                num, tipo = _ler_valvula(parte)
                if num is not None:
                    itens.append(("%d: %g: %s" % (i + 1, num, tipo)) if tipo else ("%d: %g" % (i + 1, num)))
            if itens != list(self.obj.Registros):
                self.obj.Registros = itens
                self._atualizar()

        def _juntas(self, i, ed):
            if self._ocupado:
                return
            itens = [x for x in self.obj.Juntas if not x.strip().startswith("%d:" % (i + 1))]
            for parte in ed.text().split(";"):
                parte = parte.strip().replace(".", "").replace(",", ".")
                if parte:
                    try:
                        itens.append("%d: %g" % (i + 1, float(parte)))
                    except ValueError:
                        pass
            if itens != list(self.obj.Juntas):
                self.obj.Juntas = itens
                self._atualizar()

        def _atualizar(self):
            self.doc.recompute()
            res = getattr(self.obj.Proxy, "ultimo", None) or self.obj.Proxy.calcular(self.obj)
            segs, dns = res.get("segs", []), res.get("dns", [])
            L = CAT.linha(self.obj.Linha)
            tem_fl = bool(L.get("flanges"))
            tem_jun = tem_fl or bool(L.get("uniao"))
            self.fl_pontas.setVisible(tem_fl)
            self.classe.setVisible(tem_fl)
            self.lb_classe.setVisible(tem_fl)
            self.cap.setEnabled(not (tem_fl and self.fl_pontas.isChecked()))
            self.tabela.setColumnHidden(3, not (L.get("registro") or L.get("valvulas")))
            self.tabela.horizontalHeaderItem(3).setText("Válvulas a (mm)" if L.get("valvulas") else "Registro a (mm)")
            if L.get("valvulas"):
                self.tabela.horizontalHeaderItem(3).setToolTip(
                    "Distância do início do trecho até o centro da válvula e o tipo: gaveta, globo, esfera ou "
                    "retenção (fluxo no sentido do trecho). Várias: 300 gaveta; 1200 retenção")
            self.card_p.setVisible(bool(L.get("luva_bucha") or L.get("te_bucha") or L.get("joelho_bucha")))
            self.tabela.setColumnHidden(4, not tem_jun)
            self.tabela.horizontalHeaderItem(4).setText("Flanges a (mm)" if tem_fl else "União a (mm)")
            self.tabela.horizontalHeaderItem(4).setToolTip(
                "Junta de desmontagem: distância do início do trecho até a junta (%s); várias: 300; 1200"
                % ("par de flanges, junta e estojos" if tem_fl else "união"))
            self._ocupado = True
            try:
                self.tabela.setRowCount(len(segs))
                for i, (a, b) in enumerate(segs):
                    self.tabela.setItem(i, 0, QtWidgets.QTableWidgetItem(str(i + 1)))
                    self.tabela.setItem(i, 1, QtWidgets.QTableWidgetItem(PrumoUtil.fmt((b - a).Length, 0)))
                    cb = QtWidgets.QComboBox()
                    for d in L["diametros"]:
                        cb.addItem(_dn_txt(d, L), d)
                    cb.setCurrentIndex(max(0, cb.findData(dns[i])))
                    cb.currentIndexChanged.connect(lambda _x, i=i, cb=cb: self._dn_trecho(i, cb))
                    self.tabela.setCellWidget(i, 2, cb)
                    pos = [p_ for p_ in self.obj.Proxy.registros(self.obj).get(i, []) if not isinstance(p_, Junta)]
                    ed = QtWidgets.QLineEdit("; ".join(
                        PrumoUtil.fmt(p_, 0) + ((" " + NOMES_CURTOS.get(getattr(p_, "tipo", "gaveta"), "gaveta"))
                                                if L.get("valvulas") else "")
                        for p_ in pos))
                    ed.setPlaceholderText("ex.: 300 gaveta; 1200 retenção" if L.get("valvulas") else "sem registro")
                    ed.editingFinished.connect(lambda i=i, ed=ed: self._registro(i, ed))
                    self.tabela.setCellWidget(i, 3, ed)
                    jun = [x.split(":", 1)[1].strip() for x in self.obj.Juntas
                           if x.split(":", 1)[0].strip() == str(i + 1)]
                    ej = QtWidgets.QLineEdit("; ".join(PrumoUtil.fmt(float(p_), 0) for p_ in jun))
                    ej.setPlaceholderText("sem junta")
                    ej.editingFinished.connect(lambda i=i, ej=ej: self._juntas(i, ej))
                    self.tabela.setCellWidget(i, 4, ej)
            finally:
                self._ocupado = False
            if hasattr(self, "lista_pontos"):
                self._encher_pontos()
            if hasattr(self, "lista_cx"):
                self._encher_caixas()
            import PrumoPainel
            PrumoPainel.estreitar(self.form)
            html = ["<b>Conexões</b><br>" + ("<br>".join(self.obj.Conexoes) or "—"),
                    "<b>Tubos</b><br>" + ("<br>".join(self.obj.ListaCorte) or "—")]
            if getattr(self.obj, "Soldas", 0):
                html.append("<b>Soldas de topo</b>: %d (para o plano de inspeção)" % self.obj.Soldas)
            if self.obj.Avisos:
                html.append("<b style='color:#B35C00'>Avisos</b><br>" + "<br>".join(self.obj.Avisos))
            html.append("<small>Medidas: %s.<br>Norma: %s.</small>" % (L["fonte"], L["norma"]))
            self.res.setHtml("<br><br>".join(html))

        def copiar(self):
            QtWidgets.QApplication.clipboard().setText(texto_lista(self.obj))

        def folha_isometrica(self):
            import PrumoIsometrico
            self.doc.recompute()
            pg = PrumoIsometrico.criar_folha(self.obj)
            self.ultima_folha = pg
            return pg

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
