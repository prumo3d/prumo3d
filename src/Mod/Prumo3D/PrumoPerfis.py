# SPDX-License-Identifier: LGPL-2.1-or-later
# Usinix - biblioteca de perfis estruturais brasileiros (W, HP, U, I, cantoneiras, tubos).
"""Perfis de aço laminado e tubos, com dados de catálogo de fabricantes que produzem no Brasil.

Dados em Resources/perfis/perfis.json (gerado por prumo-build/ferramentas/gerar_perfis.py).
Cada perfil tem "status": "confirmado" (catálogo oficial) ou "a checar" (fonte secundária,
divergência ou valor derivado); o Usinix mostra o aviso na escolha do perfil.

A seção é desenhada sem os raios de concordância; a massa da barra usa a massa linear do
catálogo (kg/m), que já considera os raios.
"""

import json
import math
import os

import FreeCAD

import PrumoUtil

ARQUIVO = os.path.join(PrumoUtil.RES_DIR, "perfis", "perfis.json")
_cache = {}


def dados():
    if "d" not in _cache:
        with open(ARQUIVO, encoding="utf-8") as fh:
            _cache["d"] = json.load(fh)
        _cache["idx"] = {}
        for fam in _cache["d"]["familias"]:
            for it in fam["itens"]:
                it["familia"] = fam["id"]
                _cache["idx"][it["nome"]] = it
        # nomes antigos (tabela anterior) apontam para o perfil equivalente do catálogo atual
        for fam in _cache["d"]["familias"]:
            for it in fam["itens"]:
                for al in it.get("aliases", []):
                    _cache["idx"].setdefault(al, it)
    return _cache["d"]


def familias(com_antigas=True):
    """Famílias da biblioteca; as marcadas "antiga" (tabelas substituídas) só para quem já as usa."""
    fs = dados()["familias"]
    return fs if com_antigas else [f for f in fs if not f.get("antiga")]


def familia(fid):
    if fid == FAMILIA_CUSTOM:
        return familia_customizada()
    for f in familias():
        if f["id"] == fid:
            return f
    return None


def perfil(nome):
    dados()
    it = _cache["idx"].get(nome)
    if it is None and isinstance(nome, str) and nome.startswith(PREFIXO_CUSTOM):
        it = item_customizado(nome)
        if it is not None:
            _cache["idx"][nome] = it
    return it


# ---------------------------------------------------------------- perfis customizados (medidas digitadas)
# O nome guarda as medidas (ex.: "Customizado I 200 x 100 x 6,3 x 8"): a estrutura salva só o nome e o
# perfil volta igual ao abrir o arquivo, sem depender de nada guardado fora dele.
PREFIXO_CUSTOM = "Customizado "
FAMILIA_CUSTOM = "CUSTOM"
DENSIDADE_ACO = 7850.0      # kg/m³
# chave: (rótulo, [(campo, rótulo do campo, valor inicial)])
TIPOS_CUSTOM = {
    "I": ("Perfil I / W / H", [("d", "Altura d", 200.0), ("bf", "Largura da mesa bf", 100.0),
                               ("tw", "Espessura da alma tw", 6.3), ("tf", "Espessura da mesa tf", 8.0)]),
    "U": ("Perfil U", [("d", "Altura d", 150.0), ("bf", "Largura da aba bf", 50.0),
                       ("tw", "Espessura da alma tw", 5.0), ("tf", "Espessura da aba tf", 6.0)]),
    "L": ("Cantoneira (abas iguais)", [("aba", "Aba b", 50.0), ("esp", "Espessura t", 6.35)]),
    "TQ": ("Tubo quadrado", [("lado", "Lado", 50.0), ("esp", "Espessura t", 3.0)]),
    "TR": ("Tubo retangular", [("h", "Altura h", 80.0), ("b", "Largura b", 40.0), ("esp", "Espessura t", 3.0)]),
    "TUBO": ("Tubo redondo", [("D", "Diâmetro externo D", 60.3), ("esp", "Espessura t", 3.6)]),
    "BC": ("Barra chata", [("b", "Largura b", 50.0), ("esp", "Espessura t", 6.35)]),
    "BQ": ("Barra quadrada", [("b", "Lado b", 25.0)]),
    "BR": ("Barra redonda", [("D", "Diâmetro D", 25.0)]),
}


def _num(v):
    t = ("%.3f" % float(v)).rstrip("0").rstrip(".")
    return t.replace(".", ",")


def nome_customizado(tipo, valores):
    """Nome do perfil customizado: guarda o tipo e as medidas em mm."""
    if tipo not in TIPOS_CUSTOM:
        raise ValueError("tipo de perfil customizado desconhecido: %s" % tipo)
    campos = TIPOS_CUSTOM[tipo][1]
    if len(valores) != len(campos):
        raise ValueError("o perfil %s precisa de %d medidas" % (tipo, len(campos)))
    return PREFIXO_CUSTOM + tipo + " " + " x ".join(_num(v) for v in valores)


def ler_customizado(nome):
    """(tipo, [medidas]) de um nome de perfil customizado, ou None."""
    if not isinstance(nome, str) or not nome.startswith(PREFIXO_CUSTOM):
        return None
    resto = nome[len(PREFIXO_CUSTOM):].strip()
    if " " not in resto:
        return None
    tipo, medidas = resto.split(" ", 1)
    if tipo not in TIPOS_CUSTOM:
        return None
    try:
        vals = [float(x.strip().replace(",", ".")) for x in medidas.split(" x ")]
    except ValueError:
        return None
    if len(vals) != len(TIPOS_CUSTOM[tipo][1]) or any(v <= 0 for v in vals):
        return None
    return tipo, vals


def _ret(u0, u1, v0, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def item_customizado(nome):
    """Item do catálogo montado pelas medidas do nome (massa pela geometria, aço 7850 kg/m³)."""
    lido = ler_customizado(nome)
    if lido is None:
        return None
    tipo, vals = lido
    m = dict(zip([c for c, _r, _v in TIPOS_CUSTOM[tipo][1]], vals))
    it = {"nome": nome, "status": "usuario", "origem": "customizado", "derivado": [], "familia": FAMILIA_CUSTOM,
          "tipo_custom": tipo}
    if tipo in ("I", "U"):
        if m["tw"] >= m["bf"] or 2 * m["tf"] >= m["d"]:
            return None
        it.update(tipo=tipo, d=m["d"], bf=m["bf"], tw=m["tw"], tf=m["tf"])
    elif tipo == "L":
        if m["esp"] >= m["aba"]:
            return None
        it.update(tipo="L", aba=m["aba"], esp=m["esp"])
    elif tipo == "TQ":
        if 2 * m["esp"] >= m["lado"]:
            return None
        it.update(tipo="TQ", lado=m["lado"], esp=m["esp"])
    elif tipo == "TR":
        h, b, e = m["h"], m["b"], m["esp"]
        if 2 * e >= min(h, b):
            return None
        it.update(tipo="POL", forma="RHS", h=h, b=b, esp=e, oco=True,
                  contorno=[list(p) for p in _ret(-b / 2, b / 2, -h / 2, h / 2)],
                  furos=[[list(p) for p in _ret(-b / 2 + e, b / 2 - e, -h / 2 + e, h / 2 - e)]])
    elif tipo == "TUBO":
        if 2 * m["esp"] >= m["D"]:
            return None
        it.update(tipo="TUBO", D=m["D"], esp=m["esp"])
    elif tipo == "BC":
        it.update(tipo="POL", forma="chata", b=m["b"], esp=m["esp"], macica=True,
                  contorno=[list(p) for p in _ret(-m["b"] / 2, m["b"] / 2, -m["esp"] / 2, m["esp"] / 2)], furos=[])
    elif tipo == "BQ":
        it.update(tipo="POL", forma="quadrada", b=m["b"], macica=True,
                  contorno=[list(p) for p in _ret(-m["b"] / 2, m["b"] / 2, -m["b"] / 2, m["b"] / 2)], furos=[])
    elif tipo == "BR":
        r = m["D"] / 2.0
        it.update(tipo="POL", forma="redonda", D=m["D"], macica=True, furos=[],
                  contorno=[[r * math.cos(2 * math.pi * k / 64), r * math.sin(2 * math.pi * k / 64)] for k in range(64)])
    area = area_secao(it)
    it["area_cm2"] = round(area / 100.0, 3)
    it["massa"] = area * 1e-6 * DENSIDADE_ACO
    return it


def familia_customizada():
    return {"id": FAMILIA_CUSTOM, "nome": "Customizado (medidas digitadas)", "itens": [],
            "fonte": {"chave": "CUSTOM", "nome": "Medidas digitadas pelo usuário", "url": ""}}


# ---------------------------------------------------------------- cotas para mostrar (catálogo)
ROTULOS_COTA = [("d", "Altura d"), ("h", "Altura h"), ("bw", "Alma bw"), ("bf", "Largura da mesa/aba bf"),
                ("b", "Largura b"), ("aba", "Aba b"), ("lado", "Lado"), ("D", "Diâmetro D"),
                ("tw", "Espessura da alma tw"), ("tf", "Espessura da mesa tf"), ("esp", "Espessura t"),
                ("R", "Raio de concordância R"), ("r_ext", "Raio externo")]


def cotas(it):
    """[(rótulo, valor em mm)] das medidas do perfil, na ordem dos catálogos."""
    out = []
    for k, rot in ROTULOS_COTA:
        v = it.get(k)
        if isinstance(v, (int, float)) and v > 0:
            if k == "D" and it.get("forma") == "Ue":
                rot = "Enrijecedor D"
            if k == "bf" and it.get("forma") == "Ue":
                rot = "Aba bf"
            out.append((rot, float(v)))
    return out


def nomes(fid=None):
    if fid is None:
        return [it["nome"] for f in familias() for it in f["itens"]]
    f = familia(fid)
    return [it["nome"] for it in f["itens"]] if f else []


def fonte(it):
    chave = it.get("fonte")
    if not chave:
        f = familia(it["familia"])
        return f["fonte"] if f else {}
    return dados()["fontes"].get(chave, {"chave": chave, "nome": chave, "url": ""})


def derivados_relevantes(it):
    """Valores derivados que entram no desenho ou na massa (o raio R não é usado)."""
    return [d for d in it.get("derivado", []) if d != "R"]


def confiavel(it):
    if it.get("status") == "usuario":     # seção personalizada: geometria do próprio desenho
        return True
    return it["status"] == "confirmado" and not derivados_relevantes(it)


def descricao_status(it):
    if it.get("origem") == "customizado":
        return "Perfil customizado: medidas digitadas; massa calculada pela geometria (aço, 7.850 kg/m³)."
    if it.get("status") == "usuario":
        return "Seção desenhada no projeto: propriedades calculadas pelo contorno."
    if confiavel(it):
        return "Dados do catálogo do fabricante."
    partes = []
    if it["status"] != "confirmado":
        partes.append("A CONFERIR: fonte secundária ou divergente.")
    nomes_der = {"tf": "espessura da mesa calculada pela massa", "R": "raio estimado",
                 "massa": "massa recalculada pela geometria"}
    if it["status"] == "confirmado":
        partes.append("Dados do catálogo do fabricante.")
    if derivados_relevantes(it):
        partes.append("Valores derivados: " + ", ".join(nomes_der.get(d, d) for d in derivados_relevantes(it)) + ".")
    if it.get("substituto"):
        partes.append("Tabela antiga do Usinix: o equivalente atual é %s (Gerdau 01/23)." % it["substituto"])
    return " ".join(partes)


def dimensoes(it):
    """(largura, altura) da seção em mm."""
    t = it["tipo"]
    if t in ("I", "U"):
        return it["bf"], it["d"]
    if t == "L":
        return it["aba"], it["aba"]
    if t == "TUBO":
        return it["D"], it["D"]
    if t == "TQ":
        return it["lado"], it["lado"]
    if t == "POL":
        us = [p[0] for p in it["contorno"]]
        vs = [p[1] for p in it["contorno"]]
        return max(us) - min(us), max(vs) - min(vs)
    raise ValueError(t)


def contorno(it):
    """Contornos da seção em 2D (u = largura, v = altura), centrada na caixa envolvente.

    Retorna (externo, furos) com listas de pontos (u, v); para tubos redondos, ("circulo", D, D_int)."""
    t = it["tipo"]
    if t == "I":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        a, b, w, f = bf / 2.0, d / 2.0, tw / 2.0, tf
        pts = [(-a, -b), (a, -b), (a, -b + f), (w, -b + f), (w, b - f), (a, b - f), (a, b), (-a, b),
               (-a, b - f), (-w, b - f), (-w, -b + f), (-a, -b + f)]
        return pts, []
    if t == "U":
        d, bf, tw, tf = it["d"], it["bf"], it["tw"], it["tf"]
        a, b = bf / 2.0, d / 2.0
        pts = [(-a, -b), (a, -b), (a, -b + tf), (-a + tw, -b + tf), (-a + tw, b - tf), (a, b - tf),
               (a, b), (-a, b)]
        return pts, []
    if t == "L":
        s, e = it["aba"], it["esp"]
        h = s / 2.0
        pts = [(-h, -h), (h, -h), (h, -h + e), (-h + e, -h + e), (-h + e, h), (-h, h)]
        return pts, []
    if t == "TQ":
        s, e = it["lado"], it["esp"]
        h, i = s / 2.0, s / 2.0 - e
        ext, inn = [(-h, -h), (h, -h), (h, h), (-h, h)], [(-i, -i), (i, -i), (i, i), (-i, i)]
        r = it.get("r_ext") or 0.0
        if r > 0:       # cantos arredondados (tubos Tuper; os da tabela antiga ficam vivos, como eram)
            ext, inn = _cantos(ext, r), _cantos(inn, max(r - e, 0.0))
        return ext, [inn]
    if t == "TUBO":
        return ("circulo", it["D"], it["D"] - 2 * it["esp"]), []
    if t == "POL":      # seção personalizada (PrumoSecaoPersonalizada), já centrada na caixa
        return [tuple(p) for p in it["contorno"]], [[tuple(p) for p in f] for f in it.get("furos", [])]
    raise ValueError(t)


def _cantos(quad, r, n=6):
    """Quadrado/retângulo (4 pontos, sentido anti-horário) com cantos de raio r."""
    if r <= 0:
        return quad
    us = [p[0] for p in quad]
    vs = [p[1] for p in quad]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    out = []
    for cu, cv, a0 in ((u1 - r, v0 + r, -90.0), (u1 - r, v1 - r, 0.0), (u0 + r, v1 - r, 90.0), (u0 + r, v0 + r, 180.0)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            out.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return out


def area_secao(it):
    """Área da seção desenhada (mm²), sem raios."""
    ext, furos = contorno(it)
    if isinstance(ext, tuple):
        _c, D, Di = ext
        return math.pi * (D * D - Di * Di) / 4.0

    def a(p):
        return 0.5 * abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                             for i in range(len(p))))
    return a(ext) - sum(a(f) for f in furos)


def face(it, origem, eixo_u, eixo_v, desloc_v=0.0, desloc_u=0.0, espelhar=False):
    """Face da seção no plano (origem, eixo_u, eixo_v). desloc_v / desloc_u deslocam ao longo da
    altura / largura; espelhar inverte a seção na largura (ex.: abas de um U ou de uma cantoneira)."""
    import Part
    eu = FreeCAD.Vector(eixo_u).normalize()
    ev = FreeCAD.Vector(eixo_v).normalize()
    su = -1.0 if espelhar else 1.0

    def p3(u, v):
        return origem + eu * (su * u + desloc_u) + ev * (v + desloc_v)

    ext, furos = contorno(it)
    if isinstance(ext, tuple):
        _c, D, Di = ext
        n = eu.cross(ev)
        centro = p3(0, 0)
        c1 = Part.Wire(Part.makeCircle(D / 2.0, centro, n))
        c2 = Part.Wire(Part.makeCircle(Di / 2.0, centro, n))
        f = Part.Face(c1)
        return f.cut(Part.Face(c2)).Faces[0]

    def fio(pts):
        vs = [p3(u, v) for u, v in pts]
        return Part.makePolygon(vs + [vs[0]])

    f = Part.Face(fio(ext))
    for furo in furos:
        f = f.cut(Part.Face(fio(furo))).Faces[0]
    return f
