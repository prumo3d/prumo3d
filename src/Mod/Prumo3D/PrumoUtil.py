# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - funções comuns às ferramentas (números no formato brasileiro, materiais, peças).
"""Utilidades compartilhadas pelas ferramentas do Prumo 3D."""

import os

import FreeCAD

DENSIDADE_ACO = 7850.0  # kg/m³ — usada quando a peça não tem material definido (ajustável)
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.join(DIR, "Resources")


def icone(nome):
    return os.path.join(RES_DIR, "icons", nome)


def fmt(v, casas=2, unidade=""):
    """Número no formato brasileiro: 1.234,56 (ponto nos milhares, vírgula decimal)."""
    if v is None:
        return "—"
    if abs(v) < 0.5 * 10 ** (-casas):
        v = 0.0  # evita "-0,0"
    s = "{:,.{c}f}".format(v, c=casas).replace(",", "X").replace(".", ",").replace("X", ".")
    return s + (" " + unidade if unidade else "")


def fmt_dim(v):
    """Dimensão em mm sem zeros sobrando: 12,5 / 40 / 0,75."""
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return s.replace(".", ",")


def densidade_padrao():
    return FreeCAD.ParamGet(PARAM_PATH).GetFloat("DensidadePadrao", DENSIDADE_ACO)


UUID_SEM_MATERIAL = "7f9fd73b-50c9-41d8-b7b2-575a030c1eeb"   # "Default" do FreeCAD
NOMES_SEM_MATERIAL = ("", "Default", "Sem material (padrão)")


def material(obj):
    """(nome, densidade em kg/m³, definido) do material da peça.

    definido = False quando a peça usa o material "Default" do FreeCAD (sem material escolhido);
    aí a densidade retornada é a padrão do Prumo (aço, 7.850 kg/m³, ajustável)."""
    alvo = obj
    try:
        if obj.TypeId == "App::Link" and obj.LinkedObject is not None:
            alvo = obj.LinkedObject
    except Exception:
        pass
    m = getattr(alvo, "ShapeMaterial", None) if "ShapeMaterial" in getattr(alvo, "PropertiesList", []) \
        else None
    if m is not None and getattr(m, "Name", "") not in NOMES_SEM_MATERIAL \
            and getattr(m, "UUID", "") != UUID_SEM_MATERIAL:
        dens = None
        try:
            q = m.getPhysicalValue("Density")
            dens = float(FreeCAD.Units.Quantity(q).getValueAs("kg/m^3"))
        except Exception:
            try:
                txt = m.PhysicalProperties.get("Density")
                if txt:
                    dens = float(FreeCAD.Units.Quantity(txt).getValueAs("kg/m^3"))
            except Exception:
                dens = None
        if dens and dens > 0:
            return m.Name, dens, True
    return "Não definido (aço)", densidade_padrao(), False


CONTAINERS = ("App::Part", "Assembly::AssemblyObject", "App::DocumentObjectGroup",
              "App::DocumentObjectGroupPython", "Assembly::AssemblyLink")


# operações que sempre "gastam" as formas de entrada (o resultado substitui as originais)
CONSOMEM = ("Part::Cut", "Part::Fuse", "Part::Common", "Part::MultiFuse", "Part::MultiCommon",
            "Part::Section", "Part::Fillet", "Part::Chamfer", "Part::Offset", "Part::Thickness",
            "Part::Extrusion", "Part::Revolution", "Part::Loft", "Part::Sweep", "Part::Compound",
            "Part::RefineFeature", "Part::BooleanFragments", "Part::Slice", "Part::XOR")


def _eh_container(obj):
    if obj.TypeId in CONTAINERS:
        return True
    if obj.TypeId == "App::Link":
        alvo = obj.LinkedObject
        return alvo is not None and alvo.TypeId in CONTAINERS
    return False


def _filhos(obj):
    alvo = obj.LinkedObject if obj.TypeId == "App::Link" and obj.LinkedObject else obj
    filhos = list(getattr(alvo, "Group", []) or [])
    membros = set(filhos)
    res = []
    for f in filhos:
        # pula entradas consumidas por outra forma do mesmo grupo (ex.: caixas de uma subtração)
        # (espelho e clone deixam o original: ele só conta como consumido se estiver oculto)
        consumido = any(o in membros and o.isDerivedFrom("Part::Feature") and not _eh_container(o)
                        and o.TypeId != "PartDesign::Body"
                        and (o.TypeId in CONSOMEM or not getattr(f, "Visibility", True))
                        for o in f.InList)
        if consumido:
            continue
        if f.TypeId in ("App::Origin", "App::Line", "App::Plane", "App::Point", "Sketcher::SketchObject",
                        "Spreadsheet::Sheet", "App::VarSet", "App::TextDocument"):
            continue
        if f.TypeId.startswith("Assembly::") and f.TypeId not in CONTAINERS:
            continue  # juntas, vistas explodidas, grupos de juntas
        if f.isDerivedFrom("PartDesign::Feature") and f.TypeId != "PartDesign::Body":
            continue
        res.append(f)
    return res


def pecas(objs, _matriz=None):
    """Peças (objetos com sólidos) dentro da seleção, já com a posição no espaço.

    Retorna [(obj, shape_posicionada)]. Grupos, partes e montagens são abertos."""
    import Part
    res = []
    for obj in objs:
        if _eh_container(obj):
            if _matriz is None:
                try:  # contêiner selecionado dentro de outro: posição dos pais
                    m = placement_global(obj).multiply(obj.Placement.inverse()).toMatrix()
                except Exception:
                    m = FreeCAD.Matrix()
            else:
                m = FreeCAD.Matrix(_matriz)
            try:
                pl = obj.Placement.toMatrix()
                m = m.multiply(pl)
            except Exception:
                pass
            # (num vínculo, vale a posição do vínculo; a do objeto vinculado é ignorada pelo FreeCAD)
            res.extend(pecas(_filhos(obj), m))
            continue
        try:
            # selecionado direto (dentro de um Body/Part): vale a posição global
            sh = forma_global(obj) if _matriz is None else Part.getShape(obj)
        except Exception:
            continue
        if sh.isNull() or not sh.Solids:
            continue
        if _matriz is not None:
            sh = sh.transformed(_matriz)
        res.append((obj, sh))
    return res


def tem_peca(objs, limite=2000):
    """True se a seleção contém algum sólido. Para na primeira peça achada e não monta formas
    posicionadas (rápido em montagens grandes, para o menu de contexto)."""
    pilha = list(objs)
    vistos = set()
    while pilha and len(vistos) < limite:
        obj = pilha.pop()
        chave = (obj.Document.Name, obj.Name)
        if chave in vistos:
            continue
        vistos.add(chave)
        if _eh_container(obj):
            pilha.extend(_filhos(obj))
            continue
        try:
            sh = obj.Shape if hasattr(obj, "Shape") else None
            if sh is None and obj.TypeId == "App::Link" and obj.LinkedObject is not None:
                sh = getattr(obj.LinkedObject, "Shape", None)
            if sh is not None and not sh.isNull() and sh.Solids:
                return True
        except Exception:
            continue
    return False


def placement_global(obj):
    """Posição global do objeto, incluindo os contêineres (Body, Part) em que está."""
    try:
        return obj.getGlobalPlacement()
    except Exception:
        return obj.Placement if hasattr(obj, "Placement") else FreeCAD.Placement()


def forma_global(obj):
    """Forma do objeto no espaço global (Part.getShape só aplica a posição do próprio objeto)."""
    import Part
    sh = Part.getShape(obj)
    if hasattr(obj, "Placement"):
        pai = placement_global(obj).multiply(obj.Placement.inverse())
        if not pai.isIdentity():
            sh = sh.copy()
            sh.transformShape(pai.toMatrix())
    return sh
