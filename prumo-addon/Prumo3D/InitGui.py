# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - carregado pelo FreeCAD ao iniciar a interface.

import FreeCAD
import FreeCADGui

try:
    import PrumoGui

    PrumoGui.startup()
except Exception as exc:  # nunca impedir o FreeCAD de abrir
    FreeCAD.Console.PrintError("Prumo: falha ao carregar o branding: {}\n".format(exc))


class PrumoWorkbench(Workbench):  # noqa: F821  (Workbench é injetado pelo FreeCAD)
    MenuText = "Prumo 3D"
    ToolTip = "Ferramentas do Prumo 3D"

    def __init__(self):
        import PrumoGui

        self.__class__.Icon = PrumoGui.ICON_PATH

    def Initialize(self):
        import PrumoGui

        self.appendToolbar("Prumo", PrumoGui.COMMANDS)
        self.appendMenu("Prumo", PrumoGui.COMMANDS + ["Separator"] + PrumoGui.MENU_EXTRA)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(PrumoWorkbench())
