#!/bin/bash
# Prumo 3D: AppImage para Linux.
# Baseado no create_bundle.sh do FreeCAD; diferenças marcadas com "Prumo 3D".

set -e
set -x

conda_env="AppDir/usr"
# Prumo 3D: PRUMO_CONDA_ENV aponta para outro ambiente já compilado e instalado (ex.: pixi da raiz)
origem="${PRUMO_CONDA_ENV:-../.pixi/envs/default}"

mkdir -p ${conda_env}

cp -a ${origem}/* ${conda_env}

echo -e "\nDelete unnecessary stuff"
rm -rf ${conda_env}/include
find ${conda_env} -name \*.a -delete

# Prumo 3D: escolhe o nome que existir no ambiente (freecad no pacote, FreeCAD na compilação local)
primeiro() { for n in "$@"; do if [ -e "${conda_env}/bin_tmp/$n" ]; then echo "$n"; return; fi; done; return 1; }

mv ${conda_env}/bin ${conda_env}/bin_tmp
mkdir ${conda_env}/bin
cp ${conda_env}/bin_tmp/$(primeiro freecad FreeCAD) ${conda_env}/bin/prumo3d
cp ${conda_env}/bin_tmp/$(primeiro freecadcmd FreeCADCmd) ${conda_env}/bin/prumo3dcmd
cp ${conda_env}/bin_tmp/ccx ${conda_env}/bin/
cp ${conda_env}/bin_tmp/python ${conda_env}/bin/
cp ${conda_env}/bin_tmp/pip ${conda_env}/bin/
cp ${conda_env}/bin_tmp/pyside6-rcc ${conda_env}/bin/
cp ${conda_env}/bin_tmp/gmsh ${conda_env}/bin/
cp ${conda_env}/bin_tmp/dot ${conda_env}/bin/
cp ${conda_env}/bin_tmp/unflatten ${conda_env}/bin/
cp ${conda_env}/bin_tmp/ffmpeg ${conda_env}/bin/ || echo "aviso: ffmpeg ausente"  # Prumo 3D: vídeo em MP4
cp ${conda_env}/bin_tmp/branding.xml ${conda_env}/bin/  # Prumo 3D: nome, splash e pasta de dados próprios
rm -rf ${conda_env}/bin_tmp

sed -i '1s|.*|#!/usr/bin/env python|' ${conda_env}/bin/pip

# Prumo 3D: o módulo Prumo3D vem em usr/Mod (instalado pelo CMake, como os outros módulos)
test -f ${conda_env}/Mod/Prumo3D/InitGui.py || { echo "erro: módulo Prumo3D ausente em usr/Mod"; exit 1; }

echo -e "\nCopying Icon and Desktop file"
# Prumo 3D: atalho e ícone próprios
rm -f AppDir/*.desktop AppDir/*.svg AppDir/.DirIcon
cat > AppDir/org.prumo3d.Prumo3D.desktop <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Prumo 3D
GenericName=Modelagem 3D paramétrica
Comment=Modelagem 3D paramétrica, desenho técnico e simulação, em português
Exec=AppRun %F
Icon=org.prumo3d.Prumo3D
Terminal=false
Categories=Graphics;Science;Engineering;
MimeType=application/x-extension-fcstd;
DESKTOP
cp ../../../src/Mod/Prumo3D/Resources/icons/prumo.svg AppDir/org.prumo3d.Prumo3D.svg
# o appimagetool novo (out/2026) exige o ícone em PNG e o .DirIcon: o SVG sozinho não serve mais
cp ../../../src/Mod/Prumo3D/Resources/icons/prumo.png AppDir/org.prumo3d.Prumo3D.png
ln -sf org.prumo3d.Prumo3D.png AppDir/.DirIcon

# Remove __pycache__ folders and .pyc files
find . -path "*/__pycache__/*" -delete
find . -name "*.pyc" -type f -delete

# reduce size
rm -rf ${conda_env}/conda-meta/
rm -rf ${conda_env}/doc/global/
rm -rf ${conda_env}/share/gtk-doc/
rm -rf ${conda_env}/lib/cmake/

find . -name "*.h" -type f -delete
find . -name "*.cmake" -type f -delete

python_version=$(${conda_env}/bin/python -c 'import platform; print("py" + platform.python_version_tuple()[0] + platform.python_version_tuple()[1])')
version_name="Prumo3D_${BUILD_TAG}-Linux-$(uname -m)-${python_version}"

echo -e "\################"
echo -e "version_name:  ${version_name}"
echo -e "################"

pixi list -e default > AppDir/packages.txt || true
sed -i "1s/.*/\nLIST OF PACKAGES:/" AppDir/packages.txt

echo "Running Prumo 3D command-line smoke test..."
if ! "${conda_env}/bin/prumo3dcmd" --safe-mode --version; then
    echo "Prumo 3D command-line smoke test failed; the Linux bundle cannot start."
    exit 1
fi

# Prumo 3D: appimagetool numa versão fixa e conferida (a "continuous" muda sem aviso: em 29/10/2026 passou
# a recusar o ícone só em SVG e travou a publicação). A 1.9.0 pede o desktop-file-validate.
AIT_VERSAO="1.9.0"
AIT_SHA256_x86_64="46fdd785094c7f6e545b61afcfb0f3d98d8eab243f644b4b17698c01d06083d1"
ait="appimagetool-$(uname -m).AppImage"
if ! command -v desktop-file-validate >/dev/null 2>&1; then
    (sudo -n apt-get install -y desktop-file-utils || (sudo -n apt-get update && sudo -n apt-get install -y desktop-file-utils)) \
        >/dev/null 2>&1 || echo "aviso: não deu para instalar o desktop-file-utils"
fi
esperado_var="AIT_SHA256_$(uname -m)"
esperado="${!esperado_var:-}"
curl -fL -o "$ait" "https://github.com/AppImage/appimagetool/releases/download/${AIT_VERSAO}/appimagetool-$(uname -m).AppImage"
if [ -n "$esperado" ] && ! echo "${esperado}  ${ait}" | sha256sum -c - ; then
    echo "erro: o appimagetool ${AIT_VERSAO} baixado não confere com a soma esperada"
    exit 1
fi
if ! command -v desktop-file-validate >/dev/null 2>&1; then
    # sem o validador a 1.9.0 não roda: usa a continuous (o AppDir já tem PNG e .DirIcon para ela)
    echo "aviso: sem desktop-file-validate; usando o appimagetool continuous"
    curl -fL -o "$ait" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$(uname -m).AppImage"
fi
chmod a+x "$ait"

echo -e "\nCreate the appimage"
chmod a+x ./AppDir/AppRun
# Prumo 3D: sem atualização automática (zsync) por enquanto; a publicação é feita pelo GitHub Actions
./appimagetool-$(uname -m).AppImage \
  --comp zstd \
  --mksquashfs-opt -Xcompression-level \
  --mksquashfs-opt 22 \
  AppDir ${version_name}.AppImage

echo -e "\nCreate hash"
sha256sum ${version_name}.AppImage > ${version_name}.AppImage-SHA256.txt
