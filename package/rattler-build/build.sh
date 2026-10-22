if [[ ${HOST} =~ .*linux.*  ]]; then
    CMAKE_PRESET=conda-linux-release

    # The Linux conda preset builds with Clang, but conda compiler activation
    # can still provide GCC-only flags.
    for flags_var in CFLAGS CXXFLAGS DEBUG_CFLAGS DEBUG_CXXFLAGS; do
        if [[ -n "${!flags_var:-}" ]]; then
            export "${flags_var}=${!flags_var//-fno-merge-constants/}"
        fi
    done
fi

if [[ ${HOST} =~ .*darwin.* ]]; then
    CMAKE_PRESET=conda-macos-release

    # add hacks for osx here!
    echo "adding hacks for osx"

    # install space-mouse
    /usr/bin/curl -o /tmp/3dFW.dmg -L 'https://download.3dconnexion.com/drivers/mac/10-7-0_B564CC6A-6E81-42b0-82EC-418EA823B81A/3DxWareMac_v10-7-0_r3411.dmg'
    hdiutil attach -readonly /tmp/3dFW.dmg
    sudo installer -package /Volumes/3Dconnexion\ Software/Install\ 3Dconnexion\ software.pkg -target /
    diskutil eject /Volumes/3Dconnexion\ Software
    CMAKE_PLATFORM_FLAGS+=(-DFREECAD_USE_3DCONNEXION:BOOL=ON)
    CMAKE_PLATFORM_FLAGS+=(-D3DCONNEXIONCLIENT_FRAMEWORK:FILEPATH="/Library/Frameworks/3DconnexionClient.framework")

    CXXFLAGS="${CXXFLAGS} -D_LIBCPP_DISABLE_AVAILABILITY"
fi

unset CMAKE_GENERATOR
unset CMAKE_GENERATOR_PLATFORM

# Cache de compilação (ccache) entre versões: o fluxo do GitHub grava a pasta do cache em
# prumo_ccache_dir.txt na raiz do código (o rattler-build não repassa variáveis de ambiente).
# Sem o arquivo (compilação local), o ccache segue o padrão.
if [[ -f "${SRC_DIR}/prumo_ccache_dir.txt" ]]; then
    export CCACHE_DIR="$(tr -d '\r\n' < "${SRC_DIR}/prumo_ccache_dir.txt")"
    # a pasta de trabalho do rattler-build muda a cada compilação: caminhos relativos a ela
    export CCACHE_BASEDIR="$(dirname "${SRC_DIR}")"
    export CCACHE_NOHASHDIR=1
    export CCACHE_COMPILERCHECK=content
    export CCACHE_MAXSIZE=2500M
    mkdir -p "${CCACHE_DIR}"
    ccache -z || true
    echo "ccache: ${CCACHE_DIR} (base ${CCACHE_BASEDIR})"
fi

cmake \
    ${CMAKE_ARGS} \
    --preset ${CMAKE_PRESET} \
    -D CMAKE_IGNORE_PREFIX_PATH="/opt/homebrew;/usr/local/homebrew" \
    -D CMAKE_INCLUDE_PATH:FILEPATH="$PREFIX/include" \
    -D CMAKE_INSTALL_LIBDIR:FILEPATH="$PREFIX/lib" \
    -D CMAKE_INSTALL_PREFIX:FILEPATH="$PREFIX" \
    -D CMAKE_LIBRARY_PATH:FILEPATH="$PREFIX/lib" \
    -D CMAKE_PREFIX_PATH:FILEPATH="$PREFIX" \
    -D FREECAD_USE_EXTERNAL_FMT:BOOL=OFF \
    -D INSTALL_TO_SITEPACKAGES:BOOL=ON \
    -D OCC_INCLUDE_DIR:FILEPATH="$PREFIX/include/opencascade" \
    -D OCC_LIBRARY_DIR:FILEPATH="$PREFIX/lib" \
    -D Python_EXECUTABLE:FILEPATH="$PYTHON" \
    -D Python3_EXECUTABLE:FILEPATH="$PYTHON" \
    -D BUILD_DYNAMIC_LINK_PYTHON:BOOL=OFF \
    -B build \
    -S .

cmake --build build
cmake --install build
ccache -s || true

mv ${PREFIX}/bin/FreeCAD ${PREFIX}/bin/freecad || true
mv ${PREFIX}/bin/FreeCADCmd ${PREFIX}/bin/freecadcmd || true
