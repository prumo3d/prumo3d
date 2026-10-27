/*

install.nsh

Installation of program files, dictionaries and external components

*/

#--------------------------------
# Program files

Section -ProgramFiles SecProgramFiles
  # this can make install significantly faster but disables output to "details view"
  # on the install page, which is unreadable with full verbosity anyways
  # this is recommended in docs when working with many small files
  # https://nsis.sourceforge.io/Reference/SetDetailsPrint
  SetDetailsPrint textonly
  StrCpy $PastaAntiga ""
  ${If} $RemoveInstDir == "true"
    ${DetailPrintToBoth} "Cleaning install folder '$INSTDIR'"
    # Prumo 3D: a pasta antiga NUNCA é apagada aos pedaços (arquivo preso no meio deixava meia instalação).
    # 1) espera o Prumo e qualquer programa rodando de dentro dela; 2) renomeia a pasta inteira de uma vez:
    # se algo estiver preso a renomeação falha sem mexer em nada e a instalação antiga segue funcionando;
    # 3) a versão nova entra na pasta limpa e a antiga é apagada no fim (ou na próxima reinicialização).
    ${EsperarFecharApp} limpar
    ${EsperarPastaLivre} "$INSTDIR" limpar
    StrCpy $PastaAntiga "$INSTDIR.antiga"
    ${If} ${FileExists} "$PastaAntiga\*.*"
      RMDir /r /REBOOTOK "$PastaAntiga"
      ${If} ${FileExists} "$PastaAntiga\*.*"
        System::Call "kernel32::GetTickCount()i.r0"
        StrCpy $PastaAntiga "$INSTDIR.antiga-$0"
      ${EndIf}
    ${EndIf}
    renomear_pasta:
    ClearErrors
    Rename "$INSTDIR" "$PastaAntiga"
    ${If} ${Errors}
      ${ProcessosDaPasta} "$INSTDIR" $0 $Presos
      Sleep 2000
      MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(RMInstDirFailed)$\r$\n$\r$\nA versão instalada continua intacta.$\r$\nProgramas usando a pasta: $Presos" /SD IDCANCEL IDRETRY renomear_pasta
      StrCpy $PastaAntiga ""
      Abort
    ${EndIf}
  ${EndIf}

  # turn on logging
  # Note that this can first be done here since the log file is written to $INSTDIR
  # to $INSTDIR must have a valid path before logging can be turned on
  LogSet on

  # Install and register the core FreeCAD files

  # Initializes the plug-ins dir ($PLUGINSDIR) if not already initialized.
  # $PLUGINSDIR is automatically deleted when the installer exits.
  InitPluginsDir

  ${DetailPrintToBoth} "Extracting files..."

  # Binaries
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\bin\'"
  SetOutPath "$INSTDIR\bin"
  # recursively copy all files under bin
  File /r "${FILES_FREECAD}\bin\*.*"

  # MSVC redistributable DLLs
  !ifdef FILES_DEPS
    !echo "Including MSVC Redist files from ${FILES_DEPS}"
    SetOutPath "$INSTDIR\bin"
    File "${FILES_DEPS}\*.*"
  !endif

  # Others
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\data\'"
  SetOutPath "$INSTDIR\data"
  File /r "${FILES_FREECAD}\data\*.*"
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\doc\'"
  SetOutPath "$INSTDIR\doc"
  File /r "${FILES_FREECAD}\doc\*.*"
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\Ext\'"
  SetOutPath "$INSTDIR\Ext"
  File /r "${FILES_FREECAD}\Ext\*.*"
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\lib\'"
  SetOutPath "$INSTDIR\lib"
  File /r "${FILES_FREECAD}\lib\*.*"
  ${DetailPrintToBoth} "Extracting files to '$INSTDIR\Mod\'"
  SetOutPath "$INSTDIR\Mod"
  File /r "${FILES_FREECAD}\Mod\*.*"
  ${DetailPrintToBoth} "Extracting thumbnailer"
  SetOutPath "$INSTDIR"
  File /r "${FILES_THUMBS}"

  SetDetailsPrint both
  DetailPrint "Writing uninstaller to '$INSTDIR'"
  WriteUninstaller "$INSTDIR\${SETUP_UNINSTALLER}"

  # versão nova no lugar: apaga a antiga (o que estiver preso sai na próxima reinicialização)
  ${If} $PastaAntiga != ""
    DetailPrint "Removing previous version '$PastaAntiga'"
    RMDir /r /REBOOTOK "$PastaAntiga"
  ${EndIf}

SectionEnd

# instalação interrompida depois de renomear a pasta antiga: devolve a versão anterior ao lugar
Function .onInstFailed
  ${If} $PastaAntiga != ""
  ${AndIf} ${FileExists} "$PastaAntiga\*.*"
    RMDir /r "$INSTDIR"
    Rename "$PastaAntiga" "$INSTDIR"
  ${EndIf}
FunctionEnd
