# SPDX-License-Identifier: LGPL-2.1-or-later
"""Monta a biblioteca de perfis do Prumo (Resources/perfis/perfis.json) com os catálogos oficiais trazidos
da bancada Steel Structures (dados/steel-structures, ver ORIGEM.txt), por cima do que gerar_perfis.py gera.

- W, HP, I, U e cantoneiras: Gerdau, Tabela de Bitolas 01/23 (substituem as famílias antigas);
- T laminado (Gerdau), Ue dobrado (NBR 6355:2012), tubos Tuper 2024 quadrado / retangular / redondo e
  barras maciças da NBR 16683:2018: famílias novas;
- tubo de condução Sch 40/80: medidas da ASME B36.10M já conferidas em duas fontes na linha de aço da
  Tubulação (PrumoCatalogoTubos), que passam a "confirmado";
- nomes antigos continuam valendo: cantoneiras pelo campo "aliases" do perfil novo (diferença de centésimos);
  I e U antigos (mesa estimada pela massa) ficam como eram numa família escondida, com o "substituto" Gerdau,
  para os desenhos já feitos não mudarem sozinhos; perfis de outros fabricantes sem equivalente na Gerdau
  continuam na família, depois dos da Gerdau, com a fonte e o aviso deles.

Uso: python importar_steel_structures.py   (roda gerar_perfis.py antes)
"""
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DADOS = os.path.join(AQUI, "dados", "steel-structures")
MOD = os.path.join(AQUI, "..", "..", "src", "Mod", "Prumo3D")
SAIDA = os.path.join(MOD, "Resources", "perfis", "perfis.json")
CREDITO = ("convertido da bancada Steel Structures de Marcos Roberto da Silva "
           "(github.com/marcos-rds/steel-structures, LGPL-2.1)")


def _num(v, casas=2):
    s = ("%." + str(casas) + "f") % v
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s.replace(".", ",")


def _ler(nome):
    with open(os.path.join(DADOS, nome), encoding="utf-8") as fh:
        return json.load(fh)


def _fonte(cat, chave, extra=""):
    src = cat["catalog"].get("source", {})
    nome = "%s (%s)%s; %s" % (cat["catalog"]["name"], src.get("source_revision", ""), extra, CREDITO)
    return {"chave": chave, "nome": nome, "url": src.get("source_url") or "https://github.com/marcos-rds/steel-structures"}


def arredondar(pts, raios, n=6):
    """Polígono com cada canto trocado por um arco tangente aos dois lados (raio por vértice; 0 = vivo)."""
    out = []
    m = len(pts)
    for i in range(m):
        r = raios[i]
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % m]
        if r <= 0:
            out.append(p1)
            continue
        ax, ay = p0[0] - p1[0], p0[1] - p1[1]
        bx, by = p2[0] - p1[0], p2[1] - p1[1]
        la, lb = math.hypot(ax, ay), math.hypot(bx, by)
        ax, ay, bx, by = ax / la, ay / la, bx / lb, by / lb
        ang = math.acos(max(-1.0, min(1.0, ax * bx + ay * by)))
        dist = r / math.tan(ang / 2.0)
        t1 = (p1[0] + ax * dist, p1[1] + ay * dist)
        t2 = (p1[0] + bx * dist, p1[1] + by * dist)
        bisx, bisy = ax + bx, ay + by
        lbis = math.hypot(bisx, bisy)
        c = (p1[0] + bisx / lbis * r / math.sin(ang / 2.0), p1[1] + bisy / lbis * r / math.sin(ang / 2.0))
        a1 = math.atan2(t1[1] - c[1], t1[0] - c[0])
        a2 = math.atan2(t2[1] - c[1], t2[0] - c[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            a = a1 + da * k / n
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return out


def raio_tubo(t):
    """Raio externo dos cantos dos tubos formados a frio, ≈ 2t: com ele a área bate com a massa da tabela
    Tuper (dentro de 1 %; com canto vivo os tubos grossos passavam 7 %)."""
    return 2.0 * t


def _ret_arred(b, h, r):
    return arredondar(_ret(b, h), [r] * 4)


def _ret(b, h):
    a, c = b / 2.0, h / 2.0
    return [[-a, -c], [a, -c], [a, c], [-a, c]]


def _item_pol(nome, ext, furos, massa, extra=None):
    it = {"nome": nome, "tipo": "POL", "contorno": [[round(x, 4), round(y, 4)] for x, y in ext],
          "furos": [[[round(x, 4), round(y, 4)] for x, y in f] for f in furos], "massa": massa,
          "status": "confirmado", "derivado": [], "origem": "catalogo"}
    it.update(extra or {})
    return it


def gerdau():
    cat = _ler("gerdau_construcao_metalica_2023_01.json")
    fonte = _fonte(cat, "F_GERDAU_2023")
    fams = {"W": [], "HP": [], "I": [], "U": [], "T": [], "L": []}
    for p in cat["profiles"]:
        if p.get("geometry_status") not in (None, "released"):
            continue        # o autor da tabela deixou em revisão técnica (U 3" x 7,44, 10" x 30,80, 12" x 29,76)
        g, s = p["geometry"], p["series_id"]
        m = p["physical_properties"].get("mass_per_length")
        area = p["physical_properties"].get("area")
        nome = p["designation"]
        obs = "sob encomenda" if p.get("availability_status") not in (None, "standard") else ""
        base = {"nome": nome, "massa": m, "area_cm2": area, "status": "confirmado", "derivado": [],
                "fonte": "F_GERDAU_2023"}
        if obs:
            base["obs"] = obs
        if s in ("w", "hp"):
            R = (g["h"] - g["d_prime"]) / 2.0 if g.get("h") and g.get("d_prime") else None
            base.update(tipo="I", d=g["d"], bf=g["bf"], tw=g["tw"], tf=g["tf"], R=R)
            fams[s.upper()].append(base)
        elif s == "i":
            base.update(tipo="I", d=g["d"], bf=g["bf"], tw=g["tw"], tf=g["tf"])
            fams["I"].append(base)
        elif s == "u":
            base.update(tipo="U", d=g["d"], bf=g["bf"], tw=g["tw"], tf=g["tf"])
            fams["U"].append(base)
        elif s == "t":
            d, bf, tw, tf = g["d"], g["bf"], g["tw"], g["tf"]
            a, c, w = bf / 2.0, d / 2.0, tw / 2.0
            ext = [(-a, c), (-a, c - tf), (-w, c - tf), (-w, -c), (w, -c), (w, c - tf), (a, c - tf), (a, c)]
            it = _item_pol(nome, ext[::-1], [], m, {"fonte": "F_GERDAU_2023", "area_cm2": area,
                                                    "d": d, "bf": bf, "tw": tw, "tf": tf, "forma": "T"})
            if obs:
                it["obs"] = obs
            fams["T"].append(it)
        elif s.startswith("equal-angle"):
            base.update(tipo="L", aba=g["b"], esp=g["t"])
            fams["L"].append(base)
    nomes = {"W": "Perfil W (laminado, abas paralelas)", "HP": "Perfil HP (laminado, estaca/pilar)",
             "I": "Perfil I laminado (padrão americano)", "U": "Perfil U laminado (padrão americano)",
             "T": "Perfil T laminado", "L": "Cantoneira de abas iguais"}
    return [{"id": k, "nome": nomes[k], "norma": "ABNT NBR 15980 / ASTM A6 (Gerdau, tabela 01/23)",
             "fonte": fonte, "itens": v} for k, v in fams.items()], fonte


def tuper():
    cat = _ler("tuper_hollow_2024.json")
    fonte = _fonte(cat, "F_TUPER_2024")
    q, r, c = [], [], []
    for p in cat["profiles"]:
        if p.get("geometry_status") != "released":
            continue
        g, s = p["geometry"], p["series_id"]
        m = p["physical_properties"]["mass_per_length"]
        t = g["t"]
        obs = "sob consulta" if p.get("availability_status") == "consultation" else ""
        base = {"massa": round(m, 3), "status": "confirmado", "derivado": [], "fonte": "F_TUPER_2024"}
        if obs:
            base["obs"] = obs
        if s == "shs":
            it = dict(base, nome="Tubo □ %s x %s x %s" % (_num(g["b"]), _num(g["b"]), _num(t)), tipo="TQ",
                      lado=g["b"], esp=t, r_ext=raio_tubo(t))
            q.append(it)
        elif s == "rhs":
            h, b = g["h"], g["b"]
            ro = raio_tubo(t)
            it = _item_pol("Tubo ▭ %s x %s x %s" % (_num(h), _num(b), _num(t)), _ret_arred(b, h, ro),
                           [_ret_arred(b - 2 * t, h - 2 * t, ro - t)], round(m, 3),
                           dict(base, forma="RHS", h=h, b=b, esp=t, r_ext=ro, oco=True))
            r.append(it)
        elif s == "chs":
            it = dict(base, nome="Tubo ○ %s x %s" % (_num(g["d"]), _num(t)), tipo="TUBO", D=g["d"], esp=t)
            c.append(it)
    norma = "Tuper, Tabela Técnica de Produtos 2024 (formados a frio: NBR 14762)"
    return [{"id": "TQT", "nome": "Tubo quadrado Tuper", "norma": norma, "fonte": fonte, "itens": q},
            {"id": "TRT", "nome": "Tubo retangular Tuper", "norma": norma, "fonte": fonte, "itens": r},
            {"id": "TCT", "nome": "Tubo redondo Tuper", "norma": norma, "fonte": fonte, "itens": c}], fonte


def ue():
    cat = _ler("abnt_nbr_6355_2012_a3.json")
    fonte = _fonte(cat, "F_NBR6355")
    itens = []
    for p in cat["profiles"]:
        g = p["geometry"]
        bw, bf, D, t = g["bw"], g["bf"], g["D"], g["t"]
        ri = g.get("ri", t)
        a, b = bf / 2.0, bw / 2.0
        ext = [(-a, -b), (a, -b), (a, -b + D), (a - t, -b + D), (a - t, -b + t), (-a + t, -b + t),
               (-a + t, b - t), (a - t, b - t), (a - t, b - D), (a, b - D), (a, b), (-a, b)]
        # dobras com o raio interno da tabela (ri) e externo ri + t; as pontas dos enrijecedores ficam vivas
        ro = ri + t
        ext = arredondar(ext, [ro, ro, 0, 0, ri, ri, ri, ri, 0, 0, ro, ro])
        itens.append(_item_pol(p["designation"].replace("×", "x"), ext, [], p["physical_properties"]["mass_per_length"],
                               {"fonte": "F_NBR6355", "area_cm2": p["physical_properties"].get("area"),
                                "forma": "Ue", "bw": bw, "bf": bf, "D": D, "esp": t}))
    return [{"id": "UE", "nome": "Perfil U enrijecido (Ue, dobrado)",
             "norma": "ABNT NBR 6355:2012, Tabela A.3 (edição vigente a checar); dimensionamento pela NBR 14762",
             "fonte": fonte, "itens": itens}], fonte


def barras():
    cat = _ler("abnt_nbr_16683_2018_solid.json")
    fonte = _fonte(cat, "F_NBR16683")
    red, qua, cha = [], [], []
    for p in cat["profiles"]:
        g, s = p["geometry"], p["series_id"]
        m = p["physical_properties"]["mass_per_length"]
        pol = (p.get("source_metadata") or {}).get("source_inches")
        sufixo = (' (%s")' % pol) if pol else ""
        extra = {"fonte": "F_NBR16683", "macica": True}
        if s == "round-bar":
            d = g["d"]
            n = 64
            ext = [(d / 2.0 * math.cos(2 * math.pi * k / n), d / 2.0 * math.sin(2 * math.pi * k / n)) for k in range(n)]
            red.append(_item_pol("Barra redonda Ø %s%s" % (_num(d), sufixo), ext, [], m, dict(extra, forma="redonda", D=d)))
        elif s == "square-bar":
            b = g["b"]
            qua.append(_item_pol("Barra quadrada %s x %s%s" % (_num(b), _num(b), sufixo), _ret(b, b), [], m,
                                 dict(extra, forma="quadrada", b=b)))
        elif s == "flat-bar":
            b, t = g["b"], g["t"]
            it = _item_pol("Barra chata %s x %s" % (_num(b), _num(t)), _ret(b, t), [], m,
                           dict(extra, forma="chata", b=b, esp=t))
            geo = b * t * 7.85e-3
            if abs(m - geo) > 0.03 * geo:
                # massa da tabela não fecha com b × t × 7,85 (a própria norma usa essa densidade): fica a
                # massa da geometria, marcada para conferir
                it.update(massa=round(geo, 3), status="a checar", derivado=["massa"])
            cha.append(it)
    norma = "ABNT NBR 16683:2018, versão corrigida de 23/04/2020 (edição vigente a checar)"
    return [{"id": "BR", "nome": "Barra redonda", "norma": norma, "fonte": fonte, "itens": red},
            {"id": "BQ", "nome": "Barra quadrada", "norma": norma, "fonte": fonte, "itens": qua},
            {"id": "BC", "nome": "Barra chata", "norma": norma, "fonte": fonte, "itens": cha}], fonte


def _equivalente(velho, novos):
    t = velho["tipo"]
    for n in novos:
        if n.get("tipo") != t:
            continue
        if t in ("I", "U"):
            if abs(n["d"] - velho["d"]) < 0.6 and abs(n["massa"] - velho["massa"]) <= max(0.06, 0.01 * velho["massa"]):
                return n
        elif t == "L":
            if abs(n["aba"] - velho["aba"]) < 0.2 and abs(n["esp"] - velho["esp"]) < 0.05:
                return n
    return None


def tubos_conducao(fam_antiga):
    """Tubo Sch 40/80 com as medidas conferidas da linha de aço (PrumoCatalogoTubos)."""
    sys.path.insert(0, MOD)
    import PrumoCatalogoTubos as C
    pol_dn = {v.replace("-", " "): dn for dn, v in C.NPS.items()}
    itens = []
    for it in fam_antiga["itens"]:
        it = dict(it)
        nps = it["nome"].split('"')[0].replace("Tubo ", "")
        sch = it["nome"].rsplit(" ", 1)[1]
        dn = pol_dn.get(nps)
        if dn in C._B3610:
            De, e40, m40, e80, m80 = C._B3610[dn]
            e, m = (e40, m40) if sch == "40" else (e80, m80)
            it.update(D=De, esp=e, massa=m, status="confirmado", fonte="F_ASME_B3610")
        itens.append(it)
    fam = dict(fam_antiga, itens=itens, norma="ASME B36.10M (NBR 5590 / ASTM A106 / A53)",
               fonte={"chave": "F_ASME_B3610", "nome": C.FONTE_ASME.split(";")[0], "url": ""})
    return fam


def main(saida=SAIDA):
    import gerar_perfis
    base = gerar_perfis.main(saida)
    antigas = {f["id"]: f for f in base["familias"]}
    fontes = dict(base["fontes"])
    novas_g, fg = gerdau()
    novas_t, ft = tuper()
    novas_u, fu = ue()
    novas_b, fb = barras()
    for f in (fg, ft, fu, fb):
        fontes[f["chave"]] = f
    fontes["F_ASME_B3610"] = {"chave": "F_ASME_B3610", "nome": "ASME B36.10M conferida em duas fontes "
                              "(projectmaterials.com e ssmalloys.com)", "url": ""}
    porid = {f["id"]: f for f in novas_g}
    antigos_iu = []
    for fid in ("W", "HP", "I", "U", "L"):
        novos = porid[fid]["itens"]
        nomes_novos = {n["nome"] for n in novos}
        for v in antigas[fid]["itens"]:
            if v["nome"] in nomes_novos:
                continue
            eq = _equivalente(v, novos)
            if eq is not None and fid in ("I", "U"):
                # I e U antigos tinham a mesa estimada pela massa: ficam como eram (os desenhos já feitos não
                # mudam sozinhos) numa família escondida, apontando para o equivalente da Gerdau
                antigos_iu.append(dict(v, substituto=eq["nome"], fonte=v.get("fonte") or antigas[fid]["fonte"]["chave"]))
            elif eq is not None:
                eq.setdefault("aliases", []).append(v["nome"])
            else:
                # outro fabricante (ArcelorMittal etc.): continua na família, depois dos da Gerdau, com a fonte dele
                v = dict(v)
                v.setdefault("fonte", antigas[fid]["fonte"]["chave"])
                porid[fid]["itens"].append(v)
    tq_antigo = dict(antigas["TQ"], id="TQ", nome="Tubo quadrado (metalon, tabela antiga)", antiga=True)
    familias = (novas_g + [tubos_conducao(antigas["TUBO"])] + novas_t + novas_u + novas_b + [tq_antigo])
    if antigos_iu:
        familias.append({"id": "IU_ANT", "nome": "Perfis I e U (tabela antiga)", "antiga": True,
                         "norma": "tabela anterior do Prumo (mesa estimada pela massa)",
                         "fonte": antigas["U"]["fonte"], "itens": antigos_iu})
    out = {"descricao": "Biblioteca de perfis do Prumo 3D. Gerada por gerar_perfis.py e "
                        "importar_steel_structures.py (catálogos " + CREDITO + ").",
           "unidades": "mm, kg/m", "fontes": fontes, "familias": familias}
    with open(saida, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    sys.path.insert(0, AQUI)
    r = main()
    for f in r["familias"]:
        conf = sum(1 for i in f["itens"] if i["status"] == "confirmado")
        ali = sum(len(i.get("aliases", [])) for i in f["itens"])
        print("%-5s %4d itens (%d confirmados, %d nomes antigos)%s" % (f["id"], len(f["itens"]), conf, ali,
                                                                       " [antiga]" if f.get("antiga") else ""))
