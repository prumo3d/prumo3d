/*
declaration.nsh

Configuration and variables of FreeCAD installer
*/

#--------------------------------
# File locations

!define FILES_LICENSE "license.rtf"

#--------------------------------
# Names and version

# Usinix (antes Prumo 3D): nome próprio para pasta, registro, atalhos e desinstalador, para instalar
# lado a lado com o FreeCAD original sem sobrescrever nada dele. O executável é Usinix.exe
# (ExeName vem do bin\branding.xml, lido pelo write_version_nsh.py).
!define APP_EXE_NAME "${APP_NAME}"
!undef APP_NAME
!define APP_NAME "Usinix"
# identificador sem espaços para chaves de registro, desinstalador e macros
!define APP_ID "Usinix"
# nome do produto até a 1.3.1: o instalador copia as configurações e oferece remover a instalação antiga
!define APP_ID_ANTIGO "Prumo3D"
!define APP_NAME_ANTIGO "Prumo 3D"

!define APP_VERSION_NUMBER "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}.${APP_VERSION_PATCH}.${APP_VERSION_BUILD}"
# For the proposed install folder we use the scheme "FreeCAD x.x"
# however for the Registry, we need the scheme "FreeCAD x.x.x" in order
# to check if it is exactly this version (to support side-by-side installations)
!define APP_SERIES_NAME "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}"
!define APP_SERIES_KEY "${APP_VERSION_MAJOR}${APP_VERSION_MINOR}${APP_VERSION_PATCH}${APP_VERSION_EMERGENCY}"
!define APP_SERIES_KEY2 "${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}.${APP_VERSION_PATCH}${APP_EMERGENCY_DOT}${APP_VERSION_EMERGENCY}"
!define APP_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\${APP_ID}.exe"
!define APP_DIR "${APP_NAME} ${APP_SERIES_NAME}"
# Fixme: FC should use different preferences folder for every release
# preferências ficam em %APPDATA%\Usinix (ExeName do branding.xml), separadas do FreeCAD original
!define APP_DIR_USERDATA "${APP_ID}"
#!define APP_DIR_USERDATA "${APP_NAME}${APP_VERSION_MAJOR}.${APP_VERSION_MINOR}"
!define APP_SHORTCUT_INFO "${APP_NAME} - CAD 3D da metal-mecânica"
!define APP_INFO "Install/Uninstall ${APP_NAME}"
!define APP_WEBPAGE "https://github.com/usinix/usinix"
!define APP_WEBPAGE_INFO "${APP_NAME} Website"
!define APP_WIKI "https://wiki.freecad.org/Main_Page" # documentação do FreeCAD, base do Usinix
!define APP_WIKI_INFO "${APP_NAME} Wiki"
!define APP_COPYRIGHT "${APP_NAME}, baseado no FreeCAD: Copyright © 2001-${COPYRIGHT_YEAR} FreeCAD Team"

!define APP_RUN "bin\${APP_EXE_NAME}.exe"
!define BIN_FREECAD "${APP_EXE_NAME}.exe"
!define BIN_FREECADCMD "${APP_EXE_NAME}cmd.exe"

!define APP_REGKEY "SOFTWARE\${APP_ID}${APP_SERIES_KEY}" # like "FreeCAD0180"
!define APP_REGKEY_SETUP "${APP_REGKEY}\Setup"
!define APP_REGKEY_SETTINGS "${APP_REGKEY}\Settings"

!define APP_REGNAME_DOC "FreeCADPrumo.Document"

!define APP_EXT ".FCStd"
!define APP_EXT1 ".FCStd1"
!define APP_MIME_TYPE "application/x-zip-compressed"

!define APP_EXT_BAK ".FCBak"
!define APP_EXT_MACRO ".FCMacro"
!define APP_EXT_MAT ".FCMat"
!define APP_EXT_SCRIPT ".FCScript"

!define APP_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SETUP_UNINSTALLER_KEY}"

#--------------------------------
# Setup settings

!define SETUP_EXE ${ExeFile}

!define SETUP_ICON "icons\FreeCAD.ico"
!define SETUP_HEADERIMAGE "graphics\header.bmp"
!define SETUP_WIZARDIMAGE "graphics\banner.bmp"
!define SETUP_UNINSTALLER "Uninstall-${APP_ID}.exe"
!define SETUP_UNINSTALLER_KEY "${APP_ID}${APP_SERIES_KEY}"

#--------------------------------
# Variables that are shared between multiple files

Var APPDATemp
Var AppPre
var AppSubfolder
Var AppSuff
Var CreateDesktopIcon
Var CreateFileAssociations
Var OldVersionNumber
Var OriginalCmdInstDir
Var Pointer
Var RemoveInstDir
Var Search
Var StartmenuFolder
Var String
Var UserList
Var LangName
Var PastaAntiga
Var Presos
