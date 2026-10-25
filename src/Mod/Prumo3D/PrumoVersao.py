# SPDX-License-Identifier: LGPL-2.1-or-later
"""Versão do Prumo 3D (fonte única: tela de abertura, Sobre, informações do sistema)."""

# Na compilação do GitHub, o fluxo de publicação grava PrumoVersaoCompilada.py com o rótulo da versão
# (ex.: "0.3.0-beta"), e é ele que vale: tela de abertura, título da janela e Sobre acompanham cada
# versão sem editar este arquivo. Sem ele (compilação local), valem os valores abaixo.
VERSAO = "0.9.4"
CANAL = "beta"   # "" na versão final


def separar(rotulo):
    """'0.3.0-beta' -> ('0.3.0', 'beta'); 'v1.0.0' -> ('1.0.0', '')."""
    r = (rotulo or "").strip().lstrip("vV")
    if "-" in r:
        v, c = r.split("-", 1)
        return v, c
    return r, ""


try:
    from PrumoVersaoCompilada import VERSAO_COMPILADA as _rotulo
    if _rotulo:
        VERSAO, CANAL = separar(_rotulo)
except ImportError:
    pass


def texto():
    """Ex.: "0.1 beta"."""
    return ("%s %s" % (VERSAO, CANAL)).strip()


def base_freecad():
    """Ex.: "1.1.4"."""
    import FreeCAD
    v = FreeCAD.Version()
    txt = "%s.%s" % (v[0], v[1])
    if len(v) > 2 and v[2]:
        txt += "." + str(v[2])
    return txt


def commit():
    """Hash curto do código compilado (vazio se não houver)."""
    import FreeCAD
    v = FreeCAD.Version()
    h = v[7] if len(v) > 7 else ""
    return h[:9] if h and h != "Unknown" else ""


def _opengl():
    try:
        from PySide import QtGui
        ctx = QtGui.QOpenGLContext.currentContext()
        if ctx is None:
            import FreeCADGui
            vista = FreeCADGui.ActiveDocument.ActiveView.graphicsView()
            vista.viewport().makeCurrent()
            ctx = QtGui.QOpenGLContext.currentContext()
        if ctx is None:
            return ""
        f = ctx.functions()
        GL_VENDOR, GL_RENDERER, GL_VERSION = 0x1F00, 0x1F01, 0x1F02
        partes = [f.glGetString(GL_RENDERER), f.glGetString(GL_VERSION)]
        return " · ".join(str(p) for p in partes if p)
    except Exception:
        return ""


def info_sistema():
    """Texto para colar num relato de problema (versões, sistema, vídeo, idioma)."""
    import platform
    import sys

    import FreeCAD
    linhas = ["Prumo 3D %s" % texto(),
              "Base: FreeCAD %s" % base_freecad()]
    c = commit()
    if c:
        linhas.append("Código: %s" % c)
    linhas.append("Sistema: %s (%s)" % (platform.platform(), platform.machine()))
    linhas.append("Python: %s" % sys.version.split()[0])
    try:
        from PySide import QtCore
        linhas.append("Qt: %s" % QtCore.qVersion())
    except Exception:
        pass
    try:
        import Part
        linhas.append("OpenCASCADE: %s" % Part.OCC_VERSION)
    except Exception:
        pass
    gl = _opengl()
    if gl:
        linhas.append("Vídeo (OpenGL): %s" % gl)
    try:
        import FreeCADGui
        linhas.append("Idioma: %s" % FreeCADGui.getLocale())
    except Exception:
        pass
    linhas.append("Pasta de dados: %s" % FreeCAD.getUserAppDataDir())
    return "\n".join(linhas)
