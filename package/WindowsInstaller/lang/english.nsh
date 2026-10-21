/*
${APP_NAME} Installer Language File
Language: English
*/

!insertmacro LANGFILE_EXT "English"

${LangFileString} TEXT_INSTALL_CURRENTUSER "(Installed for Current User)"

${LangFileString} TEXT_WELCOME "This wizard will guide you through the installation of $(^NameDA). $\r$\n\
				$\r$\n\
				$_CLICK"

#${LangFileString} TEXT_CONFIGURE_PYTHON "Compiling Python scripts..."

${LangFileString} TEXT_FINISH_DESKTOP "Create desktop shortcut"
${LangFileString} TEXT_FINISH_WEBSITE "Visit freecad.org/ for the latest news, support and tips"

#${LangFileString} FileTypeTitle "FreeCAD-Document"

#${LangFileString} SecAllUsersTitle "Install for all users?"
${LangFileString} SecFileAssocTitle "File associations"
${LangFileString} SecDesktopTitle "Desktop icon"

${LangFileString} SecCoreDescription "The ${APP_NAME} files."
#${LangFileString} SecAllUsersDescription "Install FreeCAD for all users or just the current user."
${LangFileString} SecFileAssocDescription "Files with a .FCStd extension will automatically open in ${APP_NAME}."
${LangFileString} SecDesktopDescription "A ${APP_NAME} icon on the desktop."
#${LangFileString} SecDictionaries "Dictionaries"
#${LangFileString} SecDictionariesDescription "Spell-checker dictionaries that can be downloaded and installed."

#${LangFileString} PathName 'Path to the file $\"xxx.exe$\"'
#${LangFileString} InvalidFolder 'The file $\"xxx.exe$\" is not in the specified path.'

#${LangFileString} DictionariesFailed 'Download of dictionary for language $\"$R3$\" failed.'

#${LangFileString} ConfigInfo "The following configuration of FreeCAD could take a while."

#${LangFileString} RunConfigureFailed "Could not run configure script."
${LangFileString} InstallRunning "The installer is already running!"
${LangFileString} AlreadyInstalled "${APP_NAME} is already installed!$\r$\n\
				Do you nevertheless want to install ${APP_NAME} over the existing version?"
${LangFileString} NewerInstalled "You are trying to install an older version of ${APP_NAME} than what you have installed.$\r$\n\
				  If you really want this, you must uninstall the existing ${APP_NAME} $OldVersionNumber before."

#${LangFileString} FinishPageMessage "Congratulations! FreeCAD has been installed successfully.$\r$\n\
#					$\r$\n\
#					(The first start of FreeCAD might take some seconds.)"
${LangFileString} FinishPageRun "Launch ${APP_NAME}"

${LangFileString} UnNotInRegistryLabel "Unable to find ${APP_NAME} in the registry.$\r$\n\
					Shortcuts on the desktop and in the Start Menu will not be removed."
${LangFileString} UnInstallRunning "You must close ${APP_NAME} first!"
${LangFileString} UnNotAdminLabel "You must have administrator privileges to uninstall ${APP_NAME}!"
${LangFileString} UnReallyRemoveLabel "Are you sure you want to completely remove ${APP_NAME} and all of its components?"
${LangFileString} UnFreeCADPreferencesTitle '${APP_NAME}$\'s user preferences'

#${LangFileString} SecUnProgDescription "Uninstalls xxx."
${LangFileString} SecUnPreferencesDescription 'Deletes ${APP_NAME}$\'s configuration$\r$\n\
						(folder $\"$AppPre\username\$\r$\n\
						$AppSuff\$\r$\n\
						${APP_DIR_USERDATA}$\")$\r$\n\
						for you or for all users (if you are admin).'
${LangFileString} DialogUnPreferences 'You chose to delete the ${APP_NAME} user configuration.$\r$\n\
						This will also delete all installed ${APP_NAME} addons, and will affect the$\r$\n\
						preferences for all versions of ${APP_NAME}.$\r$\n\
						Are you sure you want to proceed?'
${LangFileString} SecUnProgramFilesDescription "Uninstall ${APP_NAME} and all of its components."

${LangFileString} DirNotEmptyWarning "The selected folder '$INSTDIR' is not empty.$\r$\n\
                        The installer will remove all its content before installing. Continue?"
${LangFileString} RMInstDirFailed "Failed to remove '$INSTDIR'.$\r$\n\
                        Make sure you have sufficient permissions and that no files are in use."
