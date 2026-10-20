# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Prumo 3D: bancada de chapa metálica (SheetMetal, de Shai Seger e colaboradores, LGPL-2.1-or-later),
# embutida no programa. Origem e versão em ORIGEM_PRUMO.md.

file(GLOB_RECURSE SheetMetal_FILES RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}" CONFIGURE_DEPENDS
    "*.py" "*.ui" "*.svg" "*.png" "*.qm" "*.qrc" "*.xml" "*.md" "*.gif" "*.jpg" "*.pdf" "*.json"
    "*.csv" "*.FCMacro" "LICENSE")
list(FILTER SheetMetal_FILES EXCLUDE REGEX "^(SMTests|MDS)/|^TestSheetMetal\\.py$")

ADD_CUSTOM_TARGET(SheetMetal ALL SOURCES ${SheetMetal_FILES})

foreach(arquivo ${SheetMetal_FILES})
    get_filename_component(pasta "${arquivo}" DIRECTORY)
    configure_file("${arquivo}" "${CMAKE_BINARY_DIR}/Mod/SheetMetal/${arquivo}" COPYONLY)
    INSTALL(FILES "${arquivo}" DESTINATION "Mod/SheetMetal/${pasta}")
endforeach()
