# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - biblioteca de perfis estruturais brasileiros (W, HP, U, I, cantoneiras, tubos).
"""Perfis de aço laminado e tubos, com dados de catálogo de fabricantes que produzem no Brasil.

Dados em Resources/perfis/perfis.json (gerado por prumo-build/ferramentas/gerar_perfis.py).
Cada perfil tem "status": "confirmado" (catálogo oficial) ou "a checar" (fonte secundária,
divergência ou valor derivado); o Prumo mostra o aviso na escolha do perfil.

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
    return _cache["d"]


def familias():
    return dados()["familias"]


def familia(fid):
    for f in familias():
        if f["id"] == fid:
            return f
    return None


def perfil(nome):
    dados()
    return _cache["idx"].get(nome)


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
    return it["status"] == "confirmado" and not derivados_relevantes(it)


def descricao_status(it):
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
        return [(-h, -h), (h, -h), (h, h), (-h, h)], [[(-i, -i), (i, -i), (i, i), (-i, i)]]
    if t == "TUBO":
        return ("circulo", it["D"], it["D"] - 2 * it["esp"]), []
    raise ValueError(t)


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
