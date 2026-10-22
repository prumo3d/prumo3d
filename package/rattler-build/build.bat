@echo on

@REM :: free up extra disk space, compare
@REM :: https://github.com/conda-forge/conda-smithy/issues/1949
@REM rmdir /s /q C:\hostedtoolcache\windows

@REM set "CFLAGS= "
@REM set "CXXFLAGS= -DBOOST_PROGRAM_OPTIONS_DYN_LINK=1"
@REM set "LDFLAGS_SHARED= ucrt.lib"

set "CMAKE_GENERATOR="
set "CMAKE_GENERATOR_PLATFORM="

@REM Cache de compilacao (ccache) entre versoes: o fluxo do GitHub grava a pasta do cache em
@REM prumo_ccache_dir.txt na raiz do codigo (o rattler-build nao repassa variaveis de ambiente).
if not exist "%SRC_DIR%\prumo_ccache_dir.txt" goto sem_ccache
set /p CCACHE_DIR=<"%SRC_DIR%\prumo_ccache_dir.txt"
for %%I in ("%SRC_DIR%\..") do set "CCACHE_BASEDIR=%%~fI"
set "CCACHE_NOHASHDIR=1"
set "CCACHE_COMPILERCHECK=content"
set "CCACHE_MAXSIZE=2500M"
if not exist "%CCACHE_DIR%" mkdir "%CCACHE_DIR%"
ccache -z
echo ccache: %CCACHE_DIR% (base %CCACHE_BASEDIR%)
:sem_ccache

cmake ^
    %CMAKE_ARGS% ^
    --preset conda-windows-release ^
    -D CMAKE_C_COMPILER:STRING="%CC%" ^
    -D CMAKE_CXX_COMPILER:STRING="%CXX%" ^
    -D CMAKE_INCLUDE_PATH:FILEPATH="%LIBRARY_PREFIX%/include" ^
    -D CMAKE_INSTALL_LIBDIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_INSTALL_PREFIX:FILEPATH="%LIBRARY_PREFIX%" ^
    -D CMAKE_LIBRARY_PATH:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_PREFIX_PATH:FILEPATH="%LIBRARY_PREFIX%" ^
    -D FREECAD_USE_EXTERNAL_FMT:BOOL=OFF ^
    -D INSTALL_TO_SITEPACKAGES:BOOL=ON ^
    -D OCC_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/opencascade" ^
    -D OCC_LIBRARY_DIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D Python_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D Python3_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D SMESH_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/smesh" ^
    -D SMESH_LIBRARY:FILEPATH="%LIBRARY_PREFIX%/lib/SMESH.lib" ^
    -D FREECAD_USE_MP_COMPILE_FLAG:BOOL=OFF ^
    -B build ^
    -S .
if %ERRORLEVEL% neq 0 exit 1

ninja -C build install
if %ERRORLEVEL% neq 0 exit 1
ccache -s

ren %LIBRARY_PREFIX%\bin\FreeCAD.exe freecad.exe
ren %LIBRARY_PREFIX%\bin\FreeCADCmd.exe freecadcmd.exe
