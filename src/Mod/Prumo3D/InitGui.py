# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - carregado pelo FreeCAD ao iniciar a interface.

import FreeCAD
import FreeCADGui

# Complemento atualizado (sem o pacote inteiro): a cópia em <dados do usuário>/Mod/Prumo3D passa a vez ao
# complemento do programa quando ela ficou para trás ou falhou (ver PrumoComplemento).
_prumo_outro = None
try:
    import inspect as _prumo_inspect
    import PrumoComplemento
    _prumo_outro = PrumoComplemento.ativar(_prumo_inspect.currentframe().f_code.co_filename)
except Exception as _prumo_exc:
    FreeCAD.Console.PrintWarning("Prumo: complemento atualizado: {}\n".format(_prumo_exc))

if _prumo_outro:
    import os as _prumo_os
    PrumoComplemento.executar(_prumo_os.path.join(_prumo_outro, "InitGui.py"), dict(globals()))
else:
    _prumo_erro = None
    try:
        import PrumoGui

        PrumoGui.startup()
    except Exception as exc:  # nunca impedir o FreeCAD de abrir
        _prumo_erro = exc
    _prumo_usuario = False
    try:
        _prumo_usuario = PrumoComplemento.estado()["usuario"]
    except Exception:
        pass
    if _prumo_erro is not None and _prumo_usuario:
        # a cópia atualizada falhou: abre com o complemento do programa (e não tenta mais com ela)
        import os as _prumo_os
        PrumoComplemento.executar(_prumo_os.path.join(PrumoComplemento.falhou(_prumo_erro), "InitGui.py"),
                                  dict(globals()))
    else:
        if _prumo_erro is not None:
            FreeCAD.Console.PrintError("Prumo: falha ao carregar o branding: {}\n".format(_prumo_erro))

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
        if _prumo_usuario:
            PrumoComplemento.abriu_bem()
