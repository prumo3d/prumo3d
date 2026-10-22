# SPDX-License-Identifier: LGPL-2.1-or-later
# Prumo 3D - identidade visual para o FreeCAD.
"""Branding Prumo: título e ícone da janela, splash e aplicação do tema."""

import filecmp
import os
import shutil
import xml.etree.ElementTree as ET

import FreeCAD
import FreeCADGui

try:
    from PySide import QtCore, QtGui, QtWidgets  # FreeCAD 1.x (shim PySide)
except ImportError:  # pragma: no cover
    from PySide2 import QtCore, QtGui, QtWidgets

APP_NAME = "Prumo 3D"
PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/Prumo3D"
ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.join(ADDON_DIR, "Resources")
ICON_PATH = os.path.join(RES_DIR, "icons", "prumo.png")
SPLASH_SRC = os.path.join(RES_DIR, "splash_image.png")
# Tema "Prumo Claro": pacote de preferências embutido (share/Gui/PreferencePacks);
# a cópia ao lado do módulo é aceita para quem roda o módulo solto, fora do programa compilado.
PACK_CFG = next(
    (c for c in (
        os.path.join(FreeCAD.getResourceDir(), "Gui", "PreferencePacks", "Prumo Claro", "Prumo Claro.cfg"),
        os.path.join(ADDON_DIR, "Prumo Claro", "Prumo Claro.cfg"),
    ) if os.path.isfile(c)),
    os.path.join(FreeCAD.getResourceDir(), "Gui", "PreferencePacks", "Prumo Claro", "Prumo Claro.cfg"),
)


def _params():
    return FreeCAD.ParamGet(PARAM_PATH)


def _version_text():
    v = FreeCAD.Version()
    txt = "{}.{}".format(v[0], v[1])
    if len(v) > 2 and v[2]:
        txt += "." + str(v[2])
    return txt


def _addon_version():
    try:
        import re
        txt = open(os.path.join(ADDON_DIR, "package.xml"), encoding="utf-8").read()
        return re.search(r"<version>([^<]+)</version>", txt).group(1)
    except Exception:
        return "?"


# --------------------------------------------------------------------- branding
def apply_window_branding():
    """Troca nome da aplicação, título e ícone da janela principal."""
    if not _params().GetBool("RenameWindow", True):
        return
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    # O MainWindow do FreeCAD monta o título a partir do applicationName,
    # então os títulos gerados depois (troca de documento) já saem "Prumo 3D".
    app.setApplicationName(APP_NAME)
    if os.path.isfile(ICON_PATH):
        app.setWindowIcon(QtGui.QIcon(ICON_PATH))
    mw = FreeCADGui.getMainWindow()
    if mw is not None:
        doc = FreeCAD.ActiveDocument
        try:
            import PrumoVersao
            base = "{} {}".format(APP_NAME, PrumoVersao.texto())
        except Exception:
            base = APP_NAME
        mw.setWindowTitle("[*] {} - {}".format(doc.Label, base) if doc else base)


# Versões anteriores da splash Prumo (podem ser substituídas sem perguntar)
OLD_SPLASH_MD5 = {"abaffad5496ffefc6199d1d0254842e1", "61d0f7d3152991b3dac6b8989051b9f8"}


def _is_old_prumo_splash(path):
    import hashlib
    try:
        return hashlib.md5(open(path, "rb").read()).hexdigest() in OLD_SPLASH_MD5
    except OSError:
        return False


def install_splash():
    """Copia a splash para <dados do usuário>/Gui/images/splash_image.png.

    O FreeCAD procura esse arquivo antes da splash padrão, então a troca
    aparece a partir da próxima abertura do programa.
    """
    if not _params().GetBool("InstallSplash", True) or not os.path.isfile(SPLASH_SRC):
        return
    dest_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Gui", "images")
    dest = os.path.join(dest_dir, "splash_image.png")
    if "Prumo3D" in (FreeCAD.ConfigGet("SplashScreen") or ""):
        # programa do Prumo (branding.xml): a splash já vem da instalação. Uma cópia nos dados do
        # usuário teria prioridade e ficaria velha a cada versão — então tira a cópia nossa.
        try:
            if os.path.isfile(dest) and (_params().GetBool("SplashIsOurs", False) or _is_old_prumo_splash(dest)):
                os.remove(dest)
                _params().SetBool("SplashIsOurs", False)
        except OSError as exc:
            FreeCAD.Console.PrintLog("Prumo: splash antiga não removida: {}\n".format(exc))
        return
    try:
        if os.path.isfile(dest) and filecmp.cmp(SPLASH_SRC, dest, shallow=False):
            return
        if os.path.isfile(dest) and not _params().GetBool("SplashIsOurs", False) and not _is_old_prumo_splash(dest):
            # Já existe uma splash personalizada que não é nossa: não sobrescrever.
            FreeCAD.Console.PrintWarning(
                "Prumo: já existe {} — splash Prumo não instalada.\n".format(dest)
            )
            return
        os.makedirs(dest_dir, exist_ok=True)
        shutil.copyfile(SPLASH_SRC, dest)
        _params().SetBool("SplashIsOurs", True)
        FreeCAD.Console.PrintMessage("Prumo: splash instalada (vale na próxima abertura).\n")
    except OSError as exc:
        FreeCAD.Console.PrintWarning("Prumo: não foi possível instalar a splash: {}\n".format(exc))


def remove_splash():
    dest = os.path.join(FreeCAD.getUserAppDataDir(), "Gui", "images", "splash_image.png")
    if os.path.isfile(dest) and _params().GetBool("SplashIsOurs", False):
        os.remove(dest)
    _params().SetBool("SplashIsOurs", False)
    _params().SetBool("InstallSplash", False)


# ------------------------------------------------------------- tema de ícones
ICON_ZIP = os.path.join(RES_DIR, "tema-icones-prumo.zip")
ICON_DIR_PACOTE = os.path.join(RES_DIR, "icones-tema")   # descompactado na instalação (CMake)
BITMAPS = "User parameter:BaseApp/Preferences/Bitmaps"
ICON_PATH_KEY = "CustomPathPrumo"  # lido por BitmapFactory::restoreCustomPaths (prefixo "CustomPath")


def _icon_dir():
    return os.path.join(FreeCAD.getUserAppDataDir(), "PrumoIcones")


def install_icon_theme():
    """Descompacta o tema "Prumo Sóbrio" e o registra antes dos ícones embutidos.

    O FreeCAD lê os caminhos de ícones ao iniciar, então a troca aparece na
    próxima abertura do programa.
    """
    bitmaps = FreeCAD.ParamGet(BITMAPS)
    if not _params().GetBool("IconTheme", True) or not os.path.isfile(ICON_ZIP):
        bitmaps.RemString(ICON_PATH_KEY)
        return
    import zipfile
    # Instalador: o tema já vem descompactado e o branding.xml o registra (ProgramIcons), lido pelo
    # FreeCAD antes de criar qualquer ícone. No tema claro não precisa de mais nada; no escuro, a
    # cópia recolorida vai na frente pelo caminho personalizado.
    if os.path.isdir(ICON_DIR_PACOTE):
        try:
            import PrumoEstilo
            escuro = PrumoEstilo.escuro()
        except Exception:
            escuro = False
        if not escuro:
            bitmaps.RemString(ICON_PATH_KEY)
            return
        stamp = "pacote-{}".format(int(os.path.getmtime(ICON_DIR_PACOTE)))
        try:
            esc = _icon_dir_escuro(ICON_DIR_PACOTE, stamp, os.path.join(FreeCAD.getUserAppDataDir(),
                                                                        "PrumoIconesEscuro"))
            if bitmaps.GetString(ICON_PATH_KEY, "") != esc:
                bitmaps.SetString(ICON_PATH_KEY, esc)
        except OSError as exc:
            FreeCAD.Console.PrintWarning("Prumo: ícones do tema escuro não gerados: {}\n".format(exc))
        return

    dest = _icon_dir()
    stamp = "{}-{}".format(os.path.getsize(ICON_ZIP), int(os.path.getmtime(ICON_ZIP)))
    try:
        if _params().GetString("IconThemeStamp", "") != stamp or not os.path.isdir(dest):
            if os.path.isdir(dest):
                shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest, exist_ok=True)
            with zipfile.ZipFile(ICON_ZIP) as z:
                z.extractall(dest)
            _params().SetString("IconThemeStamp", stamp)
            FreeCAD.Console.PrintMessage("Prumo: tema de ícones instalado (vale na próxima abertura).\n")
        try:
            import PrumoEstilo
            if PrumoEstilo.escuro():
                dest = _icon_dir_escuro(dest, stamp)
        except Exception as exc:  # pragma: no cover
            FreeCAD.Console.PrintWarning("Prumo: ícones do tema escuro não gerados: {}\n".format(exc))
        if bitmaps.GetString(ICON_PATH_KEY, "") != dest:
            bitmaps.SetString(ICON_PATH_KEY, dest)
    except (OSError, zipfile.BadZipFile) as exc:
        FreeCAD.Console.PrintWarning("Prumo: tema de ícones não instalado: {}\n".format(exc))


# Contornos azul-marinho/grafite somem no fundo escuro: viram claros nos ícones.
ICONES_ESCURO = {"#1e2a38": "#c9d6e3", "#003a70": "#8cbceb", "#9fb1c4": "#6f8296"}


def _icon_dir_escuro(dest, stamp, esc=None):
    """Cópia recolorida do tema de ícones para o modo escuro."""
    import re
    esc = esc or dest.rstrip("/\\") + "Escuro"
    if _params().GetString("IconThemeStampEscuro", "") == stamp and os.path.isdir(esc):
        return esc
    shutil.rmtree(esc, ignore_errors=True)
    pat = re.compile("|".join(ICONES_ESCURO), re.I)
    for raiz, _dirs, arqs in os.walk(dest):
        alvo = os.path.join(esc, os.path.relpath(raiz, dest))
        os.makedirs(alvo, exist_ok=True)
        for a in arqs:
            src = os.path.join(raiz, a)
            if a.lower().endswith(".svg"):
                with open(src, encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                with open(os.path.join(alvo, a), "w", encoding="utf-8") as f:
                    f.write(pat.sub(lambda m: ICONES_ESCURO[m.group(0).lower()], txt))
            else:
                shutil.copy2(src, os.path.join(alvo, a))
    _params().SetString("IconThemeStampEscuro", stamp)
    return esc


class CmdTemaEscuro:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ADDON_DIR, "Resources", "icons", "tema_escuro.svg"),
            "MenuText": "Tema escuro",
            "ToolTip": "Alterna entre o tema claro e o tema escuro (reabre o Prumo 3D)",
        }

    def IsActive(self):
        return True

    def Activated(self):
        import PrumoEstilo
        novo = not PrumoEstilo.escuro()
        mw = FreeCADGui.getMainWindow()
        texto = ("Mudar para o tema {}?\n\nO Prumo 3D será fechado e aberto de novo para aplicar cores e ícones. "
                 "Se houver documentos com alterações, ele pergunta se quer salvar.").format(
                     "escuro" if novo else "claro")
        r = QtWidgets.QMessageBox.question(mw, APP_NAME, texto,
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if r != QtWidgets.QMessageBox.Yes:
            return
        aplicar_tema(novo)
        reabrir_freecad()


def aplicar_tema(escuro):
    """Grava a escolha e prepara cores, parâmetros e ícones para a próxima abertura."""
    import PrumoEstilo
    _params().SetBool("TemaEscuro", bool(escuro))
    PrumoEstilo.apply_base_theme_params()
    PrumoEstilo.apply_background(force=True)
    PrumoEstilo.apply_view_colors(force=True)
    install_icon_theme()
    salvar_parametros()


def salvar_parametros():
    """Grava o user.cfg agora: senão a nova janela pode ler a configuração antiga."""
    try:
        FreeCAD.saveParameter()
        return True
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: não foi possível gravar as preferências: {}\n".format(exc))
        return False


def comando_reabrir(pid, exe):
    """Programa e argumentos que esperam este FreeCAD terminar e só então abrem outro."""
    if os.name == "nt":
        ps = ("Wait-Process -Id {pid} -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 500; "
              "Start-Process -FilePath '{exe}'").format(pid=int(pid), exe=exe.replace("'", "''"))
        return "powershell.exe", ["-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps]
    sh = "while kill -0 {pid} 2>/dev/null; do sleep 0.3; done; sleep 0.5; \"{exe}\" >/dev/null 2>&1 &".format(
        pid=int(pid), exe=exe.replace('"', '\\"'))
    return "/bin/sh", ["-c", sh]


def reabrir_freecad():
    """Fecha o FreeCAD (com as perguntas de salvar) e, se fechou mesmo, abre de novo depois que ele sair.

    Antes, a nova janela era aberta antes da antiga fechar: às vezes ela lia o user.cfg antigo e o tema
    não mudava. Agora a nova só abre depois que este processo termina.
    """
    mw = FreeCADGui.getMainWindow()

    def fechar():
        salvar_parametros()
        if not mw.close():          # usuário cancelou ao ser perguntado sobre salvar
            QtWidgets.QMessageBox.information(
                mw, APP_NAME, "Tema gravado. Ele será aplicado na próxima vez que o Prumo 3D abrir.")
            return
        prog, args = comando_reabrir(QtCore.QCoreApplication.applicationPid(),
                                     QtCore.QCoreApplication.applicationFilePath())
        QtCore.QProcess.startDetached(prog, args)

    QtCore.QTimer.singleShot(100, fechar)


class CmdTemaIcones:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Alternar tema de ícones Prumo",
            "ToolTip": "Liga ou desliga o tema de ícones Prumo Sóbrio (vale ao reabrir o Prumo 3D)",
        }

    def Activated(self):
        on = not _params().GetBool("IconTheme", True)
        _params().SetBool("IconTheme", on)
        install_icon_theme()
        QtWidgets.QMessageBox.information(
            FreeCADGui.getMainWindow(), APP_NAME,
            "Tema de ícones Prumo {}.\nFeche e abra o Prumo 3D para ver a mudança.".format(
                "ligado" if on else "desligado"))

    def IsActive(self):
        return True


# ------------------------------------------------------------------------ tema
_SETTERS = {
    "FCUInt": lambda g, n, v: g.SetUnsigned(n, int(v)),
    "FCInt": lambda g, n, v: g.SetInt(n, int(v)),
    "FCFloat": lambda g, n, v: g.SetFloat(n, float(v)),
    "FCBool": lambda g, n, v: g.SetBool(n, v == "1"),
}


def _apply_group(node, path):
    grp = FreeCAD.ParamGet(path)
    for child in node:
        name = child.get("Name")
        if child.tag == "FCParamGroup":
            _apply_group(child, path + "/" + name)
        elif child.tag == "FCText":
            grp.SetString(name, child.text or "")
        elif child.tag in _SETTERS:
            _SETTERS[child.tag](grp, name, child.get("Value"))


OVERLAY_QSS = "Freecad Overlay.qss"


def garantir_overlay_qss():
    """Painel de tarefas sobreposto à vista 3D precisa da folha de estilo do overlay.

    No FreeCAD 27 o painel Tasks fica sobreposto à vista 3D em perfis novos. Sem
    OverlayActiveStyleSheet, o FreeCAD procura "Dark Theme + Dark Background.qss", que
    não existe mais; o painel fica opaco e branco e cobre a peça. Só grava se o valor
    estiver vazio e o arquivo existir na instalação (no 1.1.4 não muda nada visível).
    """
    mw = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/MainWindow")
    if mw.GetString("OverlayActiveStyleSheet", ""):
        return False
    caminho = os.path.join(FreeCAD.getResourceDir(), "Gui", "Stylesheets", "overlay", OVERLAY_QSS)
    if not os.path.isfile(caminho):
        return False
    mw.SetString("OverlayActiveStyleSheet", OVERLAY_QSS)
    return True


def _set_light_stylesheet():
    """Escolhe o stylesheet claro que existe na versão instalada."""
    sheets = os.path.join(FreeCAD.getResourceDir(), "Gui", "Stylesheets")
    mw = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/MainWindow")
    for sheet in ("FreeCAD.qss", "FreeCAD Light.qss"):
        if os.path.isfile(os.path.join(sheets, sheet)):
            mw.SetString("StyleSheet", sheet)
            mw.SetString("Theme", "FreeCAD Light")
            mw.SetString("QtStyle", "FreeCAD")
            garantir_overlay_qss()
            return True
    return False


QUALITY = {
    # Anti-aliasing da vista 3D: 0 nenhum, 1 suavização de linha, 2 MSAA 2x,
    # 3 MSAA 4x, 5 MSAA 6x, 4 MSAA 8x (enum Gui::AntiAliasing). Vale para vistas novas.
    "AntiAliasing": 4,
    # Tesselação das peças (Mod/Part): desvio em % do tamanho e ângulo em graus.
    # Padrão do FreeCAD: 0,2 % e 28,65°. Menor = curvas mais lisas, arquivo mais pesado na tela.
    "MeshDeviation": 0.1,
    "MeshAngularDeflection": 12.0,
}


def apply_quality():
    """Linhas suaves (MSAA 8x) e curvas mais lisas. Vale para vistas abertas depois."""
    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View").SetInt(
        "AntiAliasing", QUALITY["AntiAliasing"])
    part = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Part")
    part.SetFloat("MeshDeviation", QUALITY["MeshDeviation"])
    part.SetFloat("MeshAngularDeflection", QUALITY["MeshAngularDeflection"])


def apply_theme():
    root = ET.parse(PACK_CFG).getroot()
    base = root.find("FCParamGroup[@Name='Root']/FCParamGroup[@Name='BaseApp']")
    _apply_group(base, "User parameter:BaseApp")
    _set_light_stylesheet()
    apply_quality()


# -------------------------------------------------------------------- comandos
class CmdAplicarTema:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Aplicar tema Prumo",
            "ToolTip": "Aplica as cores Prumo na interface e na vista 3D",
        }

    def Activated(self):
        apply_theme()
        QtWidgets.QMessageBox.information(
            FreeCADGui.getMainWindow(),
            APP_NAME,
            "Tema Prumo aplicado.\nFeche e abra o Prumo 3D para ver todas as cores.",
        )

    def IsActive(self):
        return True


PAINEIS_ARVORE = ("Combo View", "ComboView", "Tree view", "TreeView", "Model")


def painel_arvore():
    """O painel da árvore do modelo (Visão combinada; ou Árvore, se o usuário separou os painéis)."""
    from PySide import QtWidgets
    mw = FreeCADGui.getMainWindow()
    docks = {d.objectName(): d for d in mw.findChildren(QtWidgets.QDockWidget)}
    for nome in PAINEIS_ARVORE:
        if nome in docks:
            return docks[nome]
    return None


def mostrar_arvore(mostrar=None):
    """Abre (ou fecha, se já estiver à vista) o painel da árvore. Retorna se ficou visível."""
    d = painel_arvore()
    if d is None:
        return False
    if mostrar is None:
        mostrar = not (d.isVisible() and not d.visibleRegion().isEmpty())
    # Pela ação do menu Exibir → Painéis: o FreeCAD grava o estado do painel quando ela é usada
    # (sem disparar a reaplicação do estado de todos os painéis, o que mexeria nos outros).
    act = d.toggleViewAction()
    if act is not None and d.isVisible() != bool(mostrar):
        act.trigger()
    if bool(mostrar) != d.isVisible():
        d.setVisible(bool(mostrar))
    if mostrar:
        d.raise_()
    return d.isVisible()


class CmdArvore:
    def GetResources(self):
        return {
            "Pixmap": "tree-doc-single",
            "MenuText": "Árvore do modelo",
            "ToolTip": "Mostra ou esconde o painel da árvore do modelo (à esquerda). "
                       "Use se o painel foi fechado sem querer.",
        }

    def Activated(self):
        mostrar_arvore()

    def IsActive(self):
        return True


class CmdSobre:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Sobre o Prumo 3D",
            "ToolTip": "Informações sobre esta distribuição",
        }

    def Activated(self):
        import PrumoSobre
        import PrumoVersao
        PrumoSobre.mostrar("{} · base FreeCAD {}".format(PrumoVersao.texto(), _version_text()),
                            "FreeCAD {} (freecad.org)".format(_version_text()),
                            FreeCADGui.getMainWindow())

    def IsActive(self):
        return True


# ------------------------------------------------------------- documentos: backups e modelos
DOC_PREFS = {
    # grupo BaseApp/Preferences/Document
    "bool": {"CreateBackupFiles": True, "UseFCBakExtension": True, "AutoSaveEnabled": True,
             "RecoveryEnabled": True, "SaveThumbnail": True},
    "int": {"CountBackupFiles": 5, "AutoSaveTimeout": 5, "MaxUndoSize": 50},
    "str": {},
}
DOC_PREFS_VERSION = 1


def apply_document_prefs():
    """Backups com data, recuperação a cada 5 min e 50 passos de desfazer (uma vez por versão)."""
    if _params().GetInt("DocPrefsVersao", 0) >= DOC_PREFS_VERSION:
        return
    d = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Document")
    for k, v in DOC_PREFS["bool"].items():
        d.SetBool(k, v)
    for k, v in DOC_PREFS["int"].items():
        d.SetInt(k, v)
    for k, v in DOC_PREFS["str"].items():
        if not d.GetString(k, ""):
            d.SetString(k, v)
    _params().SetInt("DocPrefsVersao", DOC_PREFS_VERSION)


def apply_template_prefs():
    """Folhas ABNT do Prumo 3D (Resources/folhas) como padrão do Desenho técnico.

    Versões anteriores apontavam para modelos que foram removidos: se a preferência aponta para
    um arquivo que não existe mais, passa a usar a folha ABNT A3. Depois da primeira vez, a
    escolha do usuário é respeitada (ver PrumoFolhas.aplicar_preferencias).
    """
    f = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/TechDraw/Files")
    for chave in ("TemplateDir", "TemplateFile"):
        cur = f.GetString(chave, "")
        antigo = ("Prumo" in cur or "Sework" in cur) and "templates" in cur.replace("\\", "/")
        if antigo and not os.path.exists(cur):
            f.RemString(chave)
    import PrumoFolhas
    PrumoFolhas.aplicar_preferencias()


class _FolhaObserver:
    """Ao criar uma folha com modelo Prumo, grava a data em dd/mm/aaaa.

    O preenchimento automático do FreeCAD usa o formato do sistema em inglês ("17 Oct 2026").
    """

    def slotCreatedObject(self, obj):
        try:
            if obj.TypeId == "TechDraw::DrawSVGTemplate":
                QtCore.QTimer.singleShot(700, lambda o=obj: _fix_folha_date(o))
            elif obj.TypeId in ("App::Plane", "App::Line"):
                ref = (obj.Document.Name, obj.Name)
                # a vista do plano pode ainda não existir no instante da criação: tenta de novo
                for atraso in (0, 250, 1000):
                    QtCore.QTimer.singleShot(atraso, lambda r=ref: pintar_origem(*r))
        except Exception:
            pass

    def slotFinishRestoreDocument(self, doc):
        try:
            nome = doc.Name
            for atraso in (0, 500):
                QtCore.QTimer.singleShot(atraso, lambda n=nome: pintar_origens(FreeCAD.getDocument(n)))
        except Exception:
            pass


# Planos e eixos da origem no azul Prumo; ao passar o mouse ficam no amarelo de destaque
# (HighlightColor, definido no tema). O padrão do FreeCAD é vermelho/verde/azul por eixo.
ORIGEM_PAPEIS = ("XY_Plane", "XZ_Plane", "YZ_Plane", "X_Axis", "Y_Axis", "Z_Axis")


def cor_origem():
    import PrumoEstilo
    return "#8CBCEB" if PrumoEstilo.escuro() else PrumoEstilo.NAVY


def pintar_origem(doc_name, obj_name):
    """Pinta um plano/eixo da origem no azul Prumo.

    O FreeCAD 1.1 fixa a cor dos planos da origem ao criar a vista, a partir das cores
    dos eixos X/Y/Z (vermelho, verde, azul), e ignora mudanças em ShapeColor. Trocar as
    cores dos eixos mudaria também o indicador de eixos do canto. Por isso a Prumo pinta
    o material do próprio plano na cena 3D (nada é gravado no arquivo). O destaque ao
    passar o mouse continua no amarelo de HighlightColor.
    """
    if not _params().GetBool("CoresOrigemPrumo", True):
        return False
    try:
        from pivy import coin
        doc = FreeCAD.getDocument(doc_name)
        obj = doc.getObject(obj_name) if doc else None
        if obj is None or getattr(obj, "Role", "") not in ORIGEM_PAPEIS:
            return False
        vo = obj.ViewObject
        if vo is None:
            return False
        c = QtGui.QColor(cor_origem())
        rgb = (c.redF(), c.greenF(), c.blueF())
        materiais = _materiais_coin(vo.RootNode, coin, [])
        n = 0
        for mat in materiais:
            mat.diffuseColor.setValue(*rgb)
            mat.ambientColor.setValue(*rgb)
            if mat.transparency.getNum() and mat.transparency[0] > 0.8:
                mat.transparency.setValue(0.72)  # 0,85 do FreeCAD some no fundo claro
            n += 1
        return n > 0
    except Exception as exc:
        FreeCAD.Console.PrintLog("Prumo: cor da origem: {}\n".format(exc))
        return False


IGNORAR_NOS = ("PlacementIndicator", "3DAnnotation")


def _materiais_coin(no, coin, acc):
    """Materiais da cena do plano, entrando nos nodekits (SoShapeScale) e pulando o
    indicador de posicionamento, que tem cores próprias."""
    nome = no.getTypeId().getName().getString()
    if any(k in nome for k in IGNORAR_NOS):
        return acc
    if no.isOfType(coin.SoMaterial.getClassTypeId()):
        acc.append(no)
    filhos = no.getChildren()
    if filhos is not None:
        for i in range(filhos.getLength()):
            _materiais_coin(filhos[i], coin, acc)
    return acc


def pintar_origens(doc):
    for o in doc.Objects:
        if getattr(o, "Role", "") in ORIGEM_PAPEIS:
            pintar_origem(doc.Name, o.Name)


def _fix_folha_date(obj):
    import re
    import time
    try:
        if "Prumo" not in (obj.Template or ""):
            return
        et = dict(obj.EditableTexts)
        if "data" in et and not re.match(r"^\d{2}/\d{2}/\d{4}$", et["data"].strip()):
            et["data"] = time.strftime("%d/%m/%Y")
            obj.EditableTexts = et
    except Exception as exc:
        if "deleted" in str(exc):
            return  # a folha (ou o documento) foi fechada antes do ajuste adiado
        FreeCAD.Console.PrintWarning("Prumo: data da folha: {}\n".format(exc))


_folha_obs = {"obj": None}


def install_folha_observer():
    if _folha_obs["obj"] is None:
        _folha_obs["obj"] = _FolhaObserver()
        FreeCAD.addDocumentObserver(_folha_obs["obj"])


# ------------------------------------------------------------- splash por tempo mínimo
def _process_start():
    """Hora (epoch) em que o FreeCAD foi aberto; no Windows lê do próprio processo."""
    import time
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        c, e, kt, u = (wintypes.FILETIME() for _ in range(4))
        if k.GetProcessTimes(k.GetCurrentProcess(), ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(u)):
            val = (c.dwHighDateTime << 32) | c.dwLowDateTime
            return val / 1e7 - 11644473600.0
    except Exception:
        pass
    return time.time()


_splash_hold = {"obj": None, "copy": None}


def _splash_copy_close():
    cp = _splash_hold.get("copy")
    _splash_hold["copy"] = None
    if cp is not None:
        try:
            cp.close()
            cp.deleteLater()
        except RuntimeError:
            pass


class _SplashHold(QtCore.QObject):
    """Quando o FreeCAD fecha a splash, mostra uma cópia no mesmo lugar até o tempo mínimo.

    O objeto e a cópia ficam presos à aplicação, não à splash: o FreeCAD apaga a splash
    original logo depois de fechá-la, e levaria junto o cronômetro.
    """

    def __init__(self, splash, until):
        super().__init__(QtWidgets.QApplication.instance())
        self.splash = splash
        self.until = until
        self.done = False
        splash.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if not self.done and obj is self.splash and ev.type() in (QtCore.QEvent.Hide, QtCore.QEvent.Close):
            self.done = True
            import time
            rest = self.until - time.time()
            if rest > 0.1:
                cp = QtWidgets.QSplashScreen(self.splash.pixmap(), QtCore.Qt.WindowStaysOnTopHint)
                cp.setGeometry(self.splash.geometry())
                cp.show()
                cp.raise_()
                cp.repaint()
                _splash_hold["copy"] = cp
                QtCore.QTimer.singleShot(int(rest * 1000), _splash_copy_close)
            # rede de segurança: nunca deixar a cópia presa
            QtCore.QTimer.singleShot(int(max(rest, 0) * 1000) + 3000, _splash_copy_close)
        return False


def hold_splash():
    secs = min(_params().GetFloat("SplashSegundos", 3.0), 10.0)
    if secs <= 0:
        return
    app = QtWidgets.QApplication.instance()
    splash = next((w for w in app.topLevelWidgets()
                   if isinstance(w, QtWidgets.QSplashScreen) and w.isVisible()), None)
    if splash is None:
        return
    _splash_hold["obj"] = _SplashHold(splash, _process_start() + secs)


# ------------------------------------------------------------- modo distribuição
DEV_DOCKS = ("Python console", "Report view")


def apply_modo_distribuicao(on=None):
    """Esconde (ou mostra) console Python e Relatório, que o usuário final não usa.

    Sem escolha do usuário (menu Prumo → Modo distribuição): o console Python começa sempre fechado
    (confunde quem está começando); o Relatório começa fechado só em tela de notebook. Com o modo
    distribuição desligado de propósito, os dois aparecem (uso de quem programa)."""
    mw = FreeCADGui.getMainWindow()
    if mw is None:
        return
    if on is None and "ModoDistribuicao" not in _params().GetBools():
        import PrumoRibbon
        esconder = {"Python console": True, "Report view": PrumoRibbon.tela_pequena()}
    else:
        if on is None:
            on = _params().GetBool("ModoDistribuicao", False)
        esconder = {n: bool(on) for n in DEV_DOCKS}
    for dock in mw.findChildren(QtWidgets.QDockWidget):
        if dock.objectName() in esconder:
            dock.setVisible(not esconder[dock.objectName()])


class CmdModoDistribuicao:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Modo distribuição",
            "ToolTip": "Liga/desliga o modo para usuário final: esconde o console Python e o Relatório",
            "Checkable": _params().GetBool("ModoDistribuicao", False),
        }

    def Activated(self, checked=None):
        on = bool(checked) if checked is not None else not _params().GetBool("ModoDistribuicao", False)
        _params().SetBool("ModoDistribuicao", on)
        apply_modo_distribuicao(on)

    def IsActive(self):
        return True


class CmdRemoverSplash:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Voltar à splash original",
            "ToolTip": "Remove a splash Prumo e restaura a do FreeCAD",
        }

    def Activated(self):
        remove_splash()
        FreeCAD.Console.PrintMessage("Prumo: splash original restaurada.\n")

    def IsActive(self):
        return True


class CmdBarrasClassicas:
    def GetResources(self):
        return {
            "Pixmap": ICON_PATH,
            "MenuText": "Alternar faixa Prumo / barras clássicas",
            "ToolTip": "Liga ou desliga a faixa de ferramentas Prumo",
        }

    def Activated(self):
        import PrumoRibbon

        if PrumoRibbon._state["ribbon"] is not None:
            PrumoRibbon.uninstall(restore_toolbars=True)
            _params().SetBool("RibbonEnabled", False)
        else:
            PrumoRibbon.install()
            _params().SetBool("RibbonEnabled", True)

    def IsActive(self):
        return True


COMMANDS = ["Prumo_AplicarTema", "Prumo_Sobre"]
MENU_EXTRA = ["Prumo_TemaIcones", "Prumo_BarrasClassicas", "Prumo_RemoverSplash"]


def register_commands():
    FreeCADGui.addCommand("Prumo_AplicarTema", CmdAplicarTema())
    FreeCADGui.addCommand("Prumo_Sobre", CmdSobre())
    FreeCADGui.addCommand("Prumo_Arvore", CmdArvore())
    FreeCADGui.addCommand("Prumo_RemoverSplash", CmdRemoverSplash())
    FreeCADGui.addCommand("Prumo_BarrasClassicas", CmdBarrasClassicas())
    FreeCADGui.addCommand("Prumo_TemaIcones", CmdTemaIcones())
    FreeCADGui.addCommand("Prumo_ModoDistribuicao", CmdModoDistribuicao())
    FreeCADGui.addCommand("Prumo_TemaEscuro", CmdTemaEscuro())
    try:
        import PrumoInicio
        FreeCADGui.addCommand("Prumo_Inicio", PrumoInicio.CmdInicio())
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tela inicial indisponível: {}\n".format(exc))
    for modulo, registro in (("PrumoCotas", lambda m: FreeCADGui.addCommand("Prumo_Cotas", m.CmdCotas())),
                             ("PrumoMassa", lambda m: FreeCADGui.addCommand("Prumo_Massa", m.CmdMassa())),
                             ("PrumoModelos", lambda m: FreeCADGui.addCommand("Prumo_Modelo", m.CmdModelo())),
                             ("PrumoInterferencia", lambda m: FreeCADGui.addCommand("Prumo_Interferencia",
                                                                                    m.CmdInterferencia())),
                             ("PrumoCopiarProjeto", lambda m: FreeCADGui.addCommand("Prumo_CopiarProjeto",
                                                                                    m.CmdCopiarProjeto())),
                             ("PrumoVariantes", lambda m: FreeCADGui.addCommand("Prumo_Variantes",
                                                                                m.CmdVariantes())),
                             ("PrumoChapa", lambda m: (FreeCADGui.addCommand("Prumo_ChapaDXF", m.CmdChapaDXF()),
                                                       FreeCADGui.addCommand("Prumo_TabelaK", m.CmdTabelaK()))),
                             ("PrumoPropriedades", lambda m: (FreeCADGui.addCommand("Prumo_Propriedades",
                                                                                    m.CmdPropriedades()),
                                                              m.install())),
                             ("PrumoBOM", lambda m: FreeCADGui.addCommand("Prumo_ListaMateriais",
                                                                          m.CmdListaMateriais())),
                             ("PrumoFolhas", lambda m: FreeCADGui.addCommand("Prumo_NovaFolha", m.CmdNovaFolha())),
                             ("PrumoEstrutura", lambda m: (
                                 FreeCADGui.addCommand("Prumo_Estrutura", m.CmdEstrutura()),
                                 FreeCADGui.addCommand("Prumo_TrocarPerfil", m.CmdTrocarPerfil()),
                                 FreeCADGui.addCommand("Prumo_ListaDeCorte", m.CmdListaDeCorte()),
                                 FreeCADGui.addCommand("Prumo_AtualizarEstrutura", m.CmdAtualizarEstrutura()),
                                 FreeCADGui.addCommand("Prumo_EditarEstrutura", m.CmdEditarEstrutura()),
                                 FreeCADGui.addCommand("Prumo_Cantos", m.CmdCantos()))),
                             ("PrumoEstruturaExtras", lambda m: m.registrar_comandos()),
                             ("PrumoSecaoPersonalizada", lambda m: FreeCADGui.addCommand(
                                 "Prumo_SecaoPersonalizada", m.CmdSecaoPersonalizada())),
                             ("PrumoAnaliseVista", lambda m: FreeCADGui.addCommand("Prumo_AnaliseEstrutura",
                                                                                  m.CmdAnaliseEstrutura())),
                             ("PrumoRegua", lambda m: (
                                 FreeCADGui.addCommand("Prumo_ReguaHistorico", m.CmdRegua()),
                                 FreeCADGui.getMainWindow().workbenchActivated.connect(m.ao_trocar_bancada))),
                             ("PrumoEsboco3D", lambda m: FreeCADGui.addCommand("Prumo_Esboco3D",
                                                                              m.CmdEsboco3D())),
                             ("PrumoTubulacao", lambda m: FreeCADGui.addCommand("Prumo_Tubulacao",
                                                                               m.CmdTubulacao())),
                             ("PrumoAssistenteEstrutura", lambda m: FreeCADGui.addCommand(
                                 "Prumo_AssistenteEstrutura", m.CmdAssistenteEstrutura())),
                             ("PrumoVaso", lambda m: (
                                 FreeCADGui.addCommand("Prumo_Vaso", m.CmdVaso()),
                                 FreeCADGui.addCommand("Prumo_MemoriaVaso", m.CmdMemoriaVaso()),
                                 FreeCADGui.addCommand("Prumo_DesenhoVaso", m.CmdDesenhoVaso()),
                                 FreeCADGui.addCommand("Prumo_TesteVaso", m.CmdTesteVaso()))),
                             ("PrumoFixadores", lambda m: FreeCADGui.addCommand("Prumo_Fixador", m.CmdFixador())),
                             ("PrumoContexto", lambda m: m.registrar_comandos())):
        try:
            registro(__import__(modulo))
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: {} indisponível: {}\n".format(modulo, exc))
    try:
        import PrumoFEM
        FreeCADGui.addCommand("Prumo_AssistenteFEM", PrumoFEM.CmdAssistenteFEM())
        import PrumoTestes
        FreeCADGui.addCommand("Prumo_Testes", PrumoTestes.CmdTestes())
        import PrumoTutorial
        FreeCADGui.addCommand("Prumo_Tutorial", PrumoTutorial.CmdTutorial())
        FreeCADGui.addCommand("Prumo_TutorialEstrutura", PrumoTutorial.CmdTutorialEstrutura())
        import PrumoGuiaMigracao
        FreeCADGui.addCommand("Prumo_GuiaMigracao", PrumoGuiaMigracao.CmdGuiaMigracao())
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: assistente de simulação indisponível: {}\n".format(exc))


def install_translations():
    """Tradução pt-BR Prumo com prioridade sobre a oficial (ver PrumoI18n)."""
    try:
        import PrumoI18n

        PrumoI18n.install()
        mw = FreeCADGui.getMainWindow()
        if mw is not None:
            mw.workbenchActivated.connect(PrumoI18n.on_workbench)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tradução não aplicada: {}\n".format(exc))


def _start_ribbon():
    if not _params().GetBool("RibbonEnabled", True):
        return
    try:
        import PrumoRibbon

        PrumoRibbon.install()
    except Exception as exc:
        FreeCAD.Console.PrintError("Prumo: falha ao montar a faixa: {}\n".format(exc))


def _start_ferramentas():
    """Menu de contexto pela seleção e duplo clique para as cotas da operação."""
    for modulo in ("PrumoContexto", "PrumoCotas"):
        try:
            __import__(modulo).install()
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: {}: {}\n".format(modulo, exc))
    instalar_ajuste_ao_sair_do_esboco()
    instalar_menu_sobre()
    try:
        aplicar_bancadas_padrao()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: bancadas padrão: {}\n".format(exc))


class _ManipuladorMenu:
    """Ajuda → Sobre abre o Sobre do Prumo (o do FreeCAD, com créditos e licenças, fica no botão
    "Licenças e bibliotecas" do Sobre do Prumo)."""

    def modifyMenuBar(self):
        # Vista: editor de materiais (a bancada Materiais fica desligada) e o botão da árvore
        return [{"insert": "Prumo_Sobre", "menuItem": "Std_About"}, {"remove": "Std_About"},
                {"append": "Material_Edit", "menuItem": "Std_DockViewMenu"},
                {"append": "Prumo_Arvore", "menuItem": "Std_DockViewMenu"}]


# Bancadas que não vêm ligadas no Prumo (o usuário religa em Preferências → Geral → Bancadas).
# O padrão do FreeCAD já desliga Test, Inspection, Robot e OpenSCAD.
BANCADAS_DESLIGADAS = ("MaterialWorkbench", "PointsWorkbench", "RobotWorkbench")
DESLIGADAS_FREECAD = "NoneWorkbench,TestWorkbench,InspectionWorkbench,RobotWorkbench,OpenSCADWorkbench"
VERSAO_BANCADAS = 1


def bancadas_desligadas():
    txt = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Workbenches").GetString("Disabled",
                                                                                          DESLIGADAS_FREECAD)
    return [n for n in txt.split(",") if n]


def aplicar_bancadas_padrao():
    """Uma vez por perfil: desliga Materiais, Nuvem de pontos e Robótica. Se o usuário religar
    depois, fica religada (a marca de versão impede repetir)."""
    p = FreeCAD.ParamGet(PARAM_PATH)
    if p.GetInt("BancadasPadrao", 0) >= VERSAO_BANCADAS:
        return False
    grp = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Workbenches")
    atuais = bancadas_desligadas()
    for n in BANCADAS_DESLIGADAS:
        if n not in atuais:
            atuais.append(n)
    grp.SetString("Disabled", ",".join(atuais))
    ordem = [n for n in grp.GetString("Ordered", "").split(",") if n and n not in BANCADAS_DESLIGADAS]
    if ordem:
        grp.SetString("Ordered", ",".join(ordem))
    p.SetInt("BancadasPadrao", VERSAO_BANCADAS)
    return True


_manip_menu = {"obj": None}


def instalar_menu_sobre():
    if _manip_menu["obj"] is None:
        _manip_menu["obj"] = _ManipuladorMenu()
        FreeCADGui.addWorkbenchManipulator(_manip_menu["obj"])
        try:  # aplica já na bancada ativa
            wb = FreeCADGui.activeWorkbench()
            if wb is not None:
                wb.reloadActive()
        except Exception:
            pass


class _ObservadorEdicao:
    """Ao concluir um esboço, enquadra o modelo inteiro na vista (o Esboço volta a câmera de antes
    da edição, que pode não mostrar um desenho grande)."""

    def slotResetEdit(self, vp):
        try:
            obj = vp.Object
        except Exception:
            return
        if obj is None or obj.TypeId != "Sketcher::SketchObject":
            return
        try:   # conferência do esboço (perfil aberto, pontas quase encostadas...)
            import PrumoValidarEsboco
            PrumoValidarEsboco.ao_sair_do_esboco(obj)
        except Exception as exc:
            FreeCAD.Console.PrintLog("Prumo: conferir esboço: {}\n".format(exc))
        if not FreeCAD.ParamGet(PARAM_PATH).GetBool("EnquadrarAoSairDoEsboco", True):
            return
        # depois que o Esboço restaura a câmera
        QtCore.QTimer.singleShot(150, _enquadrar_vista)


def _enquadrar_vista():
    try:
        gd = FreeCADGui.ActiveDocument
        if gd is not None and gd.getInEdit() is None:
            gd.ActiveView.fitAll()
    except Exception as exc:
        FreeCAD.Console.PrintLog("Prumo: enquadrar vista: {}\n".format(exc))


_observador_edicao = {"obj": None}


def instalar_ajuste_ao_sair_do_esboco():
    if _observador_edicao["obj"] is None:
        _observador_edicao["obj"] = _ObservadorEdicao()
        FreeCADGui.addDocumentObserver(_observador_edicao["obj"])


def _start_guia():
    try:
        import PrumoGuia

        PrumoGuia.install()
    except Exception as exc:
        FreeCAD.Console.PrintError("Prumo: falha no guia ilustrado: {}\n".format(exc))


def _start_inicio():
    try:
        import PrumoInicio
        PrumoInicio.startup()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tela inicial não aberta: {}\n".format(exc))


MATERIAIS_DIR = os.path.join(ADDON_DIR, "Resources", "MateriaisPrumo")


MATERIAIS_PADRAO_DIR = os.path.join(RES_DIR, "MateriaisPadrao")
MAT_RES = "User parameter:BaseApp/Preferences/Mod/Material/Resources"
VERSAO_BIBLIOTECA = 1
BIBLIOTECA_COMPAT = "Compatibilidade (arquivos do FreeCAD)"


def _registrar_biblioteca(nome, pasta, icone=ICON_PATH):
    if not os.path.isdir(pasta):
        return False
    g = FreeCAD.ParamGet(MAT_RES + "/Modules/" + nome)
    if g.GetString("ModuleDir", "") != pasta:
        g.SetString("ModuleDir", pasta)
    if g.GetString("ModuleIcon", "") != icone:
        g.SetString("ModuleIcon", icone)
    g.SetBool("ModuleReadOnly", True)
    return True


def pasta_materiais_sistema(sub=""):
    base = os.path.join(FreeCAD.getResourceDir(), "Mod", "Material", "Resources", "Materials")
    return os.path.join(base, sub) if sub else base


def pasta_compatibilidade():
    """Cópia dos cartões do sistema (sem o material padrão, que já está na biblioteca "Padrão":
    o mesmo identificador em duas bibliotecas faria um esconder o outro)."""
    origem = pasta_materiais_sistema("Standard")
    destino = os.path.join(FreeCAD.getUserAppDataDir(), "Prumo", "MateriaisCompatibilidade")
    marca = os.path.join(destino, ".origem")
    try:
        assinatura = "%s|%s|%s" % (origem, os.path.getmtime(origem), ".".join(FreeCAD.Version()[:3]))
        with open(marca, encoding="utf-8") as f:
            if f.read() == assinatura:
                return destino
    except OSError:
        pass
    try:
        if os.path.isdir(destino):
            shutil.rmtree(destino)
        shutil.copytree(origem, destino,
                        ignore=lambda d, nomes: [n for n in nomes if n == "Default.FCMat"])
        with open(marca, "w", encoding="utf-8") as f:
            f.write(assinatura)
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: biblioteca de compatibilidade de materiais: %s\n" % exc)
    return destino


def install_materials():
    """Bibliotecas de materiais do Prumo.

    - "Prumo": materiais usados no Brasil (aços estruturais, de vaso de pressão, inox, construção
      mecânica, ferro fundido, alumínio, latão), com norma e fonte em cada cartão;
    - "Padrão": o material genérico que o FreeCAD usa em peças sem material;
    - "Aparências" e "Fluidos": cores/acabamentos e fluidos da biblioteca do FreeCAD.
    A biblioteca do sistema do FreeCAD (aços europeus, plásticos, madeira, concreto...) fica
    desligada uma vez por perfil; quem quiser religa em Preferências → Material. Os cartões dela
    continuam carregados numa biblioteca à parte, "Compatibilidade", para que arquivos antigos
    abram com o material certo.
    """
    _registrar_biblioteca("Prumo", MATERIAIS_DIR)
    _registrar_biblioteca("Padrão", MATERIAIS_PADRAO_DIR)
    # As definições dos modelos (elástico linear, densidade, aparência...) vêm da pasta do sistema;
    # sem elas os cartões carregam vazios quando a biblioteca do sistema está desligada.
    modelos = os.path.join(FreeCAD.getResourceDir(), "Mod", "Material", "Resources", "Models")
    g = FreeCAD.ParamGet(MAT_RES + "/Modules/Prumo")
    if os.path.isdir(modelos) and g.GetString("ModuleModelDir", "") != modelos:
        g.SetString("ModuleModelDir", modelos)
    p = _params()
    if p.GetInt("BibliotecaMateriais", 0) < VERSAO_BIBLIOTECA:
        r = FreeCAD.ParamGet(MAT_RES)
        r.SetBool("UseBuiltInMaterials", False)
        r.SetBool("UseMaterialsFromWorkbenches", True)
        p.SetInt("BibliotecaMateriais", VERSAO_BIBLIOTECA)
    if not FreeCAD.ParamGet(MAT_RES).GetBool("UseBuiltInMaterials", True):
        _registrar_biblioteca("Aparências", pasta_materiais_sistema("Appearance"))
        _registrar_biblioteca("Fluidos", pasta_materiais_sistema("Fluid"))
        # Arquivos feitos no FreeCAD original guardam só o identificador do material: sem os
        # cartões do sistema carregados, a peça abriria sem material (e perderia ao salvar).
        _registrar_biblioteca(BIBLIOTECA_COMPAT, pasta_compatibilidade())
    else:   # com a do sistema ligada, não duplica
        for nome in ("Aparências", "Fluidos", BIBLIOTECA_COMPAT):
            FreeCAD.ParamGet(MAT_RES + "/Modules").RemGroup(nome)


def instalar_nomes():
    """Rótulos dos objetos novos em português na árvore (Pad → Extrusão)."""
    import PrumoNomes
    PrumoNomes.install()


def startup():
    try:
        hold_splash()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: splash: {}\n".format(exc))
    try:
        import PrumoInicio
        PrumoInicio.prepare()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: tela inicial: {}\n".format(exc))
    register_commands()
    for fn in (aplicar_bancadas_padrao, instalar_nomes, install_materials, apply_document_prefs, apply_template_prefs,
               install_folha_observer, garantir_overlay_qss):
        try:
            fn()
        except Exception as exc:
            FreeCAD.Console.PrintWarning("Prumo: {}: {}\n".format(fn.__name__, exc))
    install_splash()
    install_translations()
    install_icon_theme()
    try:
        import PrumoEstilo
        PrumoEstilo.install()
    except Exception as exc:
        FreeCAD.Console.PrintWarning("Prumo: estilo não instalado: {}\n".format(exc))
    QtCore.QTimer.singleShot(600, _start_ribbon)
    QtCore.QTimer.singleShot(700, _start_ferramentas)
    QtCore.QTimer.singleShot(900, _start_guia)
    QtCore.QTimer.singleShot(1300, _start_inicio)
    QtCore.QTimer.singleShot(1500, apply_modo_distribuicao)
    QtCore.QTimer.singleShot(4000, apply_modo_distribuicao)   # depois que o FreeCAD restaura os painéis
    # Executa depois que a janela principal termina de montar.
    QtCore.QTimer.singleShot(0, apply_window_branding)
    if not _params().GetBool("QualityApplied", False):
        _params().SetBool("QualityApplied", True)
        apply_quality()
    if _params().GetBool("FirstRun", True):
        _params().SetBool("FirstRun", False)
        if _params().GetBool("ApplyThemeOnFirstRun", True):
            apply_theme()
            FreeCAD.Console.PrintMessage(
                "Prumo: tema aplicado na primeira execução — reabra o FreeCAD.\n")
