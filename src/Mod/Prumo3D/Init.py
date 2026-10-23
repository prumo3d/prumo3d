# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - carregado antes da janela principal ser montada.

import FreeCAD


def _painel_lateral_unico():
    """Árvore e Propriedades como painéis separados (viram abas do painel lateral Prumo).

    Precisa rodar antes da janela principal: é ao montá-la que o FreeCAD lê quais painéis criar.
    A preferência "PainelLateralUnico" desligada devolve o painel "Modelo" do FreeCAD.
    """
    prumo = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Prumo3D")
    dock = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/DockWindows")
    unico = prumo.GetBool("PainelLateralUnico", True)
    prumo.SetBool("PainelLateralUnico", unico)
    if unico:
        dock.GetGroup("TreeView").SetBool("Enabled", True)
        dock.GetGroup("PropertyView").SetBool("Enabled", True)
        dock.GetGroup("ComboView").SetBool("Enabled", False)
        prumo.SetBool("PainelLateralUnicoAplicado", True)
    elif prumo.GetBool("PainelLateralUnicoAplicado", False):
        # o usuário voltou ao painel do FreeCAD: desfaz o que a Prumo mudou
        dock.GetGroup("TreeView").SetBool("Enabled", False)
        dock.GetGroup("PropertyView").SetBool("Enabled", False)
        dock.GetGroup("ComboView").SetBool("Enabled", True)
        prumo.SetBool("PainelLateralUnicoAplicado", False)


try:
    _painel_lateral_unico()
except Exception as exc:  # nunca impedir o FreeCAD de abrir
    FreeCAD.Console.PrintWarning("Prumo: painel lateral: {}\n".format(exc))
