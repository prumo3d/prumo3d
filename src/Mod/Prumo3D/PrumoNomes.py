# SPDX-License-Identifier: LGPL-2.1-or-later
"""Nomes em português na árvore do modelo.

O FreeCAD dá a cada objeto novo um rótulo igual ao nome interno, em inglês ("Pad", "Pocket001",
"Sketch"). Este observador troca o rótulo pelo nome em português logo depois da criação
("Extrusão", "Cavidade001", "Esboço"). O nome interno (Name) continua o mesmo, então macros,
expressões e arquivos antigos seguem funcionando.

Só age em objetos criados agora: arquivos abertos, objetos colados/importados e desfazer/refazer
ficam como estão.
"""

import re

import FreeCAD

try:
    from PySide import QtCore
except ImportError:  # pragma: no cover
    from PySide2 import QtCore

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"

# rótulo base em inglês → português
NOMES = {
    # Peça (PartDesign)
    "Body": "Corpo", "Sketch": "Esboço", "Pad": "Extrusão", "Pocket": "Cavidade", "Revolution": "Revolução",
    "Groove": "Ranhura", "Hole": "Furo", "Fillet": "Arredondamento", "Chamfer": "Chanfro",
    "Draft": "Ângulo de saída", "Thickness": "Casca", "Mirrored": "Espelhamento",
    "LinearPattern": "Padrão linear", "PolarPattern": "Padrão circular", "MultiTransform": "Transformação múltipla",
    "Scaled": "Escala", "AdditiveLoft": "Loft aditivo", "SubtractiveLoft": "Loft subtrativo",
    "AdditivePipe": "Varredura aditiva", "SubtractivePipe": "Varredura subtrativa",
    "AdditiveHelix": "Hélice aditiva", "SubtractiveHelix": "Hélice subtrativa",
    "AdditiveBox": "Caixa aditiva", "SubtractiveBox": "Caixa subtrativa",
    "AdditiveCylinder": "Cilindro aditivo", "SubtractiveCylinder": "Cilindro subtrativo",
    "AdditiveSphere": "Esfera aditiva", "SubtractiveSphere": "Esfera subtrativa",
    "AdditiveCone": "Cone aditivo", "SubtractiveCone": "Cone subtrativo",
    "DatumPlane": "Plano de referência", "DatumLine": "Linha de referência", "DatumPoint": "Ponto de referência",
    "LocalCoordinateSystem": "Sistema de coordenadas local", "ShapeBinder": "Vínculo de forma",
    "SubShapeBinder": "Vínculo de subforma", "Binder": "Vínculo",
    # origem (eixos e planos)
    "Origin": "Origem", "X_Axis": "Eixo X", "Y_Axis": "Eixo Y", "Z_Axis": "Eixo Z",
    "XY_Plane": "Plano XY", "XZ_Plane": "Plano XZ", "YZ_Plane": "Plano YZ",
    # estrutura do documento
    "Part": "Parte", "Group": "Grupo", "Link": "Vínculo", "VarSet": "Variáveis",
    # Sólidos (Part)
    "Box": "Caixa", "Cylinder": "Cilindro", "Sphere": "Esfera", "Cone": "Cone", "Torus": "Toro",
    "Prism": "Prisma", "Wedge": "Cunha", "Tube": "Tubo", "Cut": "Subtração", "Fusion": "União",
    "Common": "Interseção", "Extrude": "Extrusão", "Revolve": "Revolução", "Mirror": "Espelho",
    "Offset": "Deslocamento", "Offset2D": "Deslocamento 2D", "Loft": "Loft", "Sweep": "Varredura",
    "Section": "Seção", "Compound": "Composto", "Refine": "Refinado",
    # Desenho técnico, planilha, montagem
    "Page": "Folha", "Template": "Modelo de folha", "View": "Vista", "ProjGroup": "Grupo de vistas",
    "Dimension": "Cota", "Balloon": "Balão", "Spreadsheet": "Planilha", "Assembly": "Montagem",
    "Joints": "Juntas", "GroundedJoint": "Fixação", "Measure": "Medida",
}

_RE = re.compile(r"^(.*?)(\d{3})?$")


def traduzir(rotulo):
    """'Pad' → 'Extrusão', 'Pocket001' → 'Cavidade001'. None se não houver tradução."""
    m = _RE.match(rotulo or "")
    if not m:
        return None
    base, num = m.group(1), m.group(2) or ""
    pt = NOMES.get(base)
    return pt + num if pt else None


def _ligado():
    return FreeCAD.ParamGet(PARAM_PATH).GetBool("NomesEmPortugues", True)


def _documento_ocupado(doc):
    for flag in ("Restoring", "Importing", "Transacting"):
        try:
            if getattr(doc, flag):
                return True
        except Exception:
            pass
    return False


def renomear(obj, original):
    """Troca o rótulo se ele ainda for o original em inglês."""
    try:
        if obj is None or obj.Label != original:
            return False
        novo = traduzir(original)
        if not novo:
            return False
        obj.Label = novo
        return True
    except Exception:
        return False


class Observador:
    def slotCreatedObject(self, obj):
        if not _ligado():
            return
        try:
            doc = obj.Document
            if _documento_ocupado(doc):
                return
            original = obj.Label
        except Exception:
            return
        if traduzir(original) is None:
            return
        # adiado: alguns comandos ajustam o objeto logo depois de criá-lo
        QtCore.QTimer.singleShot(0, lambda o=obj, r=original: renomear(o, r))


_estado = {"obs": None}


def install():
    if _estado["obs"] is None:
        _estado["obs"] = Observador()
        FreeCAD.addDocumentObserver(_estado["obs"])
    return _estado["obs"]


def uninstall():
    if _estado["obs"] is not None:
        FreeCAD.removeDocumentObserver(_estado["obs"])
        _estado["obs"] = None
