/*
Prumo 3D Installer Language File
Language: Brazilian Portuguese
*/

!insertmacro LANGFILE_EXT "PortugueseBR"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Instalado para o usuário atual)"

${LangFileString} TEXT_WELCOME "Este assistente guiará você na instalação do $(^NameDA).$\r$\n\
				$\r$\n\
				Se já houver uma versão do ${APP_NAME} instalada, feche o programa antes de continuar: \
				a nova versão é instalada por cima, e suas configurações são mantidas.$\r$\n\
				$\r$\n\
				$_CLICK"

${LangFileString} TEXT_FINISH_DESKTOP "Criar atalho na área de trabalho"
${LangFileString} TEXT_FINISH_WEBSITE "Visite a página do ${APP_NAME} para ver as novidades"

${LangFileString} SecFileAssocTitle "Associação de arquivos"
${LangFileString} SecDesktopTitle "Ícone na área de trabalho"

${LangFileString} SecCoreDescription "Os arquivos do ${APP_NAME}."
${LangFileString} SecFileAssocDescription "Arquivos com a extensão .FCStd serão abertos automaticamente no ${APP_NAME}."
${LangFileString} SecDesktopDescription "Um ícone do ${APP_NAME} na área de trabalho."

${LangFileString} InstallRunning "O instalador já está em execução!"
${LangFileString} AlreadyInstalled "O ${APP_NAME} já está instalado neste computador.$\r$\n\
				$\r$\n\
				Deseja instalar esta versão por cima da atual?$\r$\n\
				(Suas configurações são mantidas. Feche o ${APP_NAME} antes de continuar.)"
${LangFileString} NewerInstalled "A versão que você está tentando instalar é mais antiga que a já instalada.$\r$\n\
				  Se é isso mesmo que deseja, desinstale antes o ${APP_NAME} $OldVersionNumber."

${LangFileString} FinishPageRun "Abrir o ${APP_NAME}"

${LangFileString} UnNotInRegistryLabel "Não foi possível encontrar o ${APP_NAME} no Registro do Windows.$\r$\n\
					Os atalhos da área de trabalho e do Menu Iniciar não serão removidos."
${LangFileString} UnInstallRunning "Feche o ${APP_NAME} antes de continuar!"
${LangFileString} UnNotAdminLabel "Para desinstalar o ${APP_NAME} é preciso ter privilégios de administrador!"
${LangFileString} UnReallyRemoveLabel "Tem certeza de que deseja remover completamente o ${APP_NAME} e todos os seus componentes?"
${LangFileString} UnFreeCADPreferencesTitle 'Preferências do usuário do ${APP_NAME}'

${LangFileString} SecUnPreferencesDescription 'Apaga as configurações do ${APP_NAME}$\r$\n\
						(pasta $\"$AppPre\usuário\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						suas ou de todos os usuários (se você for administrador).'
${LangFileString} DialogUnPreferences 'Você escolheu apagar as configurações do ${APP_NAME}.$\r$\n\
						Isso também apaga os complementos instalados.$\r$\n\
						Deseja continuar?'
${LangFileString} SecUnProgramFilesDescription "Desinstala o ${APP_NAME} e todos os seus componentes."

${LangFileString} DirNotEmptyWarning "A pasta '$INSTDIR' já tem arquivos (de uma versão anterior).$\r$\n\
                        $\r$\n\
                        O instalador vai apagar o conteúdo dela e instalar a versão nova.$\r$\n\
                        Suas configurações e seus projetos não ficam nessa pasta e não são apagados.$\r$\n\
                        $\r$\n\
                        Continuar?"
${LangFileString} RMInstDirFailed "Não foi possível apagar a pasta '$INSTDIR'.$\r$\n\
                        Feche o ${APP_NAME} (e qualquer arquivo aberto dessa pasta) e tente de novo."
