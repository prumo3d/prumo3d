# Prumo 3D - prepara e compila o Prumo 3D no Windows.
# Baseado no roteiro oficial (FreeCAD Developers Handbook - Getting Started, Windows/pixi)
# e nos presets do repositório (conda-windows-*, gerador Ninja + MSVC).
#
# Uso (PowerShell, na pasta do clone):
#   powershell -ExecutionPolicy Bypass -File .\prumo-build\compilar.ps1 -SomenteVerificar
#   powershell -ExecutionPolicy Bypass -File .\prumo-build\compilar.ps1
#   powershell -ExecutionPolicy Bypass -File .\prumo-build\compilar.ps1 -Nucleos 4
param(
    [switch]$SomenteVerificar,
    [int]$Nucleos = 0
)

# "Continue": no Windows PowerShell 5.1, saída de erro de programas externos (git, pixi)
# viraria exceção com "Stop" e interromperia o script sem motivo.
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$log = Join-Path $PSScriptRoot "compilacao.log"
$falhas = 0

function Ok($m)    { Write-Host "  [ok] $m" -ForegroundColor Green }
function Aviso($m) { Write-Host "  [atenção] $m" -ForegroundColor Yellow }
function Falha($m) { Write-Host "  [falta] $m" -ForegroundColor Red; $script:falhas++ }

Write-Host ""
Write-Host "Prumo 3D - verificação do ambiente" -ForegroundColor Cyan
Write-Host "Pasta do código: $repo"
Write-Host ""

# 1) Caminho sem espaços (ambientes conda/pixi costumam falhar com espaços no caminho)
if ($repo -match " ") {
    Aviso "O caminho tem espaços ('$repo'). Ferramentas do pixi/conda podem falhar."
    Aviso "Recomendado: mover o clone para um caminho curto, ex.: C:\dev\Prumo3D"
} else { Ok "Caminho sem espaços" }

# 2) Espaço em disco (ambiente pixi + compilação ocupam dezenas de GB)
$drive = (Get-Item $repo).PSDrive
$livreGB = [math]::Round($drive.Free / 1GB, 1)
if ($livreGB -lt 40) { Falha "Pouco espaço livre em $($drive.Name): ($livreGB GB). Deixe ao menos 40 GB livres." }
else { Ok "Espaço livre em $($drive.Name): $livreGB GB" }

# 3) Git
if (Get-Command git -ErrorAction SilentlyContinue) { Ok "Git: $((git --version) -join ' ')" }
else { Falha "Git não encontrado. Instale o Git for Windows (git-scm.com)." }

# 4) Visual Studio 2022 com C++ (mesma versão usada pelo conda-forge)
$pf86 = ${env:ProgramFiles(x86)}
if (-not $pf86) { $pf86 = "C:\Program Files (x86)" }
$vswhere = Join-Path $pf86 "Microsoft Visual Studio\Installer\vswhere.exe"
$vs = $null
if (Test-Path $vswhere) {
    $vs = & $vswhere -version "[17.0,18.0)" -products * `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
}
if ($vs) { Ok "Visual Studio 2022 com C++: $vs" }
else {
    Falha "Visual Studio 2022 com 'Desenvolvimento para desktop com C++' não encontrado."
    Write-Host "         Instale o Visual Studio Community 2022 e, no instalador, marque" -ForegroundColor Red
    Write-Host "         'Desenvolvimento para desktop com C++'." -ForegroundColor Red
}

# 5) pixi
$pixi = Get-Command pixi -ErrorAction SilentlyContinue
if (-not $pixi -and (Test-Path "$env:USERPROFILE\.pixi\bin\pixi.exe")) {
    $env:Path = "$env:USERPROFILE\.pixi\bin;$env:Path"
    $pixi = Get-Command pixi -ErrorAction SilentlyContinue
}
if ($pixi) { Ok "pixi: $((pixi --version) -join ' ')" }
else {
    Falha "pixi não encontrado."
    Write-Host "         Para instalar (comando oficial):  iwr -useb https://pixi.sh/install.ps1 | iex" -ForegroundColor Red
    Write-Host "         Depois feche e abra o PowerShell." -ForegroundColor Red
}

# 6) Patch de correções Prumo
$patch = Join-Path $repo "prumo-patches\0001-correcoes-ferramentas-inacabadas.patch"
if (Test-Path $patch) {
    git apply --check -R --ignore-whitespace $patch 2>$null
    if ($LASTEXITCODE -eq 0) { Ok "Correções Prumo já aplicadas ao código" }
    else {
        git apply --check --ignore-whitespace $patch 2>$null
        if ($LASTEXITCODE -eq 0) { Aviso "Correções Prumo ainda não aplicadas (serão aplicadas antes de compilar)" }
        else { Aviso "O patch de correções não aplica neste código (talvez já modificado). Será ignorado." }
    }
}

Write-Host ""
if ($falhas -gt 0) {
    Write-Host "Faltam $falhas item(ns). Resolva e rode este script de novo." -ForegroundColor Red
    exit 1
}
if ($SomenteVerificar) {
    Write-Host "Ambiente pronto. Rode sem -SomenteVerificar para compilar." -ForegroundColor Green
    exit 0
}

# --- Compilação -------------------------------------------------------------
if (Test-Path $patch) {
    git apply --check --ignore-whitespace $patch 2>$null
    if ($LASTEXITCODE -eq 0) {
        git apply --ignore-whitespace $patch
        Ok "Correções Prumo aplicadas"
    }
}

# Ícone do aplicativo (executável, janela e instalador) nas cores Prumo
$ic = Join-Path $PSScriptRoot "icones"
if (Test-Path $ic) {
    $mapa = @{
        "icon.ico"             = "src\Main\icon.ico"
        "FreeCAD.ico"          = "package\WindowsInstaller\icons\FreeCAD.ico"
        "freecad.svg"          = "src\Gui\Icons\freecad.svg"
        "freecad-icon-16.png"  = "src\Gui\Icons\freecad-icon-16.png"
        "freecad-icon-32.png"  = "src\Gui\Icons\freecad-icon-32.png"
        "freecad-icon-48.png"  = "src\Gui\Icons\freecad-icon-48.png"
        "freecad-icon-64.png"  = "src\Gui\Icons\freecad-icon-64.png"
    }
    foreach ($k in $mapa.Keys) {
        $dst = Join-Path $repo $mapa[$k]
        if (Test-Path (Split-Path $dst)) { Copy-Item (Join-Path $ic $k) $dst -Force }
    }
    Ok "Ícone Prumo aplicado ao executável e ao instalador"
}

Write-Host ""
Write-Host "Compilando. A primeira vez baixa as dependências e pode levar horas." -ForegroundColor Cyan
Write-Host "Registro completo em: $log"
"=== $(Get-Date -Format 'dd/MM/yyyy HH:mm') ===" | Out-File $log -Encoding utf8

pixi run configure 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { Write-Host "Falhou na configuração. Veja $log" -ForegroundColor Red; exit 1 }

if ($Nucleos -gt 0) { pixi run build -j $Nucleos 2>&1 | Tee-Object -FilePath $log -Append }
else { pixi run build 2>&1 | Tee-Object -FilePath $log -Append }
if ($LASTEXITCODE -ne 0) {
    Write-Host "Falhou na compilação. Veja o fim de $log" -ForegroundColor Red
    Write-Host "Se faltar memória, rode de novo com -Nucleos 4" -ForegroundColor Yellow
    exit 1
}

# Complemento Prumo 3D e identidade no próprio ambiente compilado (como no pacote):
# - Library\Mod\Prumo3D: complemento (o perfil do usuário não é tocado);
# - Library\bin\branding.xml: nome Prumo 3D, splash e pasta de dados %APPDATA%\Prumo3D.
try {
    $src = Join-Path $repo "prumo-addon\Prumo3D"
    $lib = Join-Path $repo ".pixi\envs\default\Library"
    if ((Test-Path $src) -and (Test-Path $lib)) {
        $mod = Join-Path $lib "Mod\Prumo3D"
        if (Test-Path $mod) { Remove-Item -Recurse -Force $mod }
        New-Item -ItemType Directory -Force -Path $mod | Out-Null
        Copy-Item -Path (Join-Path $src "*") -Destination $mod -Recurse -Force
        New-Item -ItemType Directory -Force -Path (Join-Path $lib "bin") | Out-Null
        Copy-Item (Join-Path $src "extras\branding.xml") (Join-Path $lib "bin\branding.xml") -Force
        Ok "Complemento Prumo 3D e branding.xml instalados em $lib"
    } else {
        Aviso "Ambiente compilado não encontrado: complemento Prumo 3D não instalado."
    }
} catch { Aviso "Não foi possível instalar o complemento Prumo 3D: $_" }

Write-Host ""
Write-Host "Compilado. Para abrir o Prumo 3D compilado:  pixi run freecad" -ForegroundColor Green
