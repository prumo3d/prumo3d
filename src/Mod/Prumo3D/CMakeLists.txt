# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Prumo 3D: módulo de interface embutido no programa (faixa de ferramentas, tradução pt-BR,
# tela inicial, assistentes, tema e ícones) e identidade do aplicativo (branding.xml).

file(GLOB Prumo3D_SRCS RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}" CONFIGURE_DEPENDS "*.py")
list(APPEND Prumo3D_SRCS package.xml LICENSE LEIA-ME.md)
SOURCE_GROUP("" FILES ${Prumo3D_SRCS})

set(Prumo3D_DIRS
    Resources
    translations
)

ADD_CUSTOM_TARGET(Prumo3D ALL
    SOURCES ${Prumo3D_SRCS}
)

# Árvore de compilação: o programa roda direto da pasta build, como os outros módulos
fc_copy_sources(Prumo3D "${CMAKE_BINARY_DIR}/Mod/Prumo3D" ${Prumo3D_SRCS})
FILE(COPY ${Prumo3D_DIRS} DESTINATION "${CMAKE_BINARY_DIR}/Mod/Prumo3D")
FILE(COPY extras/branding.xml DESTINATION "${CMAKE_BINARY_DIR}/bin")

INSTALL(
    FILES
        ${Prumo3D_SRCS}
    DESTINATION
        Mod/Prumo3D
)

INSTALL(
    DIRECTORY
        ${Prumo3D_DIRS}
    DESTINATION
        Mod/Prumo3D
    PATTERN "__pycache__" EXCLUDE
)

# Nome "Prumo 3D", tela de abertura e pasta de dados do usuário própria (%APPDATA%\Prumo3D,
# ~/.local/share/Prumo3D). O FreeCAD procura o branding.xml na pasta bin do programa.
INSTALL(
    FILES
        extras/branding.xml
    DESTINATION
        ${CMAKE_INSTALL_BINDIR}
)
