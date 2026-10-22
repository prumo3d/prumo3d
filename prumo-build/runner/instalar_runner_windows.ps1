# Prumo 3D: registra este computador como "runner" próprio do GitHub Actions (repositório prumo3d/prumo3d),
# para gerar os pacotes sem gastar minutos do GitHub.
#
# ATENÇÃO: o runner próprio foi removido em 21/10/2026, quando o repositório ficou público (runner
# próprio em repositório público deixa pull requests de terceiros rodarem código neste computador).
# Não registre de novo sem restringir quem pode disparar workflows.
#
# Uso (PowerShell comum, não precisa ser administrador):
#   1. No GitHub: prumo3d/prumo3d -> Settings -> Actions -> Runners -> New self-hosted runner -> Windows.
#      Copie só o código que aparece depois de "--token" (vale por cerca de 1 hora).
#   2. powershell -ExecutionPolicy Bypass -File C:\dev\prumo3d-scripts\instalar_runner_windows.ps1
#   3. Cole o código quando pedir.
#   4. Para ligar o runner: C:\ar\run.cmd  (deixe a janela aberta enquanto compila).
#
# Pastas: runner em C:\ar (caminho curto, evita limite de caminho do Windows);
#         pacotes prontos em C:\dev\Prumo3D-pacotes\<rótulo>.

$ErrorActionPreference = "Stop"
$Pasta = "C:\ar"
$Pacotes = "C:\dev\Prumo3D-pacotes"
$Repo = "https://github.com/prumo3d/prumo3d"

Write-Host "== Prumo 3D: runner próprio ==" -ForegroundColor Cyan

# Git Bash: os passos do fluxo usam "bash"; o bash.exe do System32 é o do WSL e não serve
$GitBash = "C:\Program Files\Git\bin"
if (-not (Test-Path "$GitBash\bash.exe")) {
    throw "Não achei $GitBash\bash.exe. Instale o Git for Windows (git-scm.com) e rode de novo."
}

if (-not (Test-Path $Pasta)) { New-Item -ItemType Directory -Path $Pasta | Out-Null }
if (-not (Test-Path $Pacotes)) { New-Item -ItemType Directory -Path $Pacotes | Out-Null }

# caminhos longos no git (submódulos e build)
git config --global core.longpaths true

Set-Location $Pasta
if (-not (Test-Path "$Pasta\config.cmd")) {
    Write-Host "Baixando o runner do GitHub Actions (versão mais recente)..."
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/actions/runner/releases/latest" -UseBasicParsing
    $ativo = $rel.assets | Where-Object { $_.name -like "actions-runner-win-x64-*.zip" } | Select-Object -First 1
    if (-not $ativo) { throw "Não encontrei o pacote do runner para Windows x64." }
    $zip = Join-Path $Pasta $ativo.name
    Invoke-WebRequest -Uri $ativo.browser_download_url -OutFile $zip -UseBasicParsing
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $Pasta)
    Remove-Item $zip
    Write-Host "Runner $($rel.tag_name) extraído em $Pasta"
}

$token = Read-Host "Cole o código (token) da página New self-hosted runner"
if ([string]::IsNullOrWhiteSpace($token)) { throw "Sem código, sem registro." }

$nome = "PC-" + $env:COMPUTERNAME
& "$Pasta\config.cmd" --url $Repo --token $token.Trim() --name $nome --labels prumo --work _work --unattended --replace
if ($LASTEXITCODE -ne 0) { throw "O registro falhou (código $LASTEXITCODE). O token pode ter expirado: gere outro." }

# variáveis para os trabalhos: pasta dos pacotes
Set-Content -Path "$Pasta\.env" -Value "PRUMO_PACOTES=$Pacotes" -Encoding ASCII

# PATH dos trabalhos: Git Bash na frente (o runner lê o arquivo .path)
$caminho = if (Test-Path "$Pasta\.path") { (Get-Content "$Pasta\.path" -Raw).Trim() } else { $env:PATH }
if (-not $caminho.StartsWith($GitBash)) { $caminho = "$GitBash;$caminho" }
Set-Content -Path "$Pasta\.path" -Value $caminho -Encoding ASCII

Write-Host ""
Write-Host "Pronto. Runner '$nome' registrado com o rótulo 'prumo'." -ForegroundColor Green
Write-Host "Para ligar:  C:\ar\run.cmd   (deixe a janela aberta enquanto o GitHub compila)"
Write-Host "Pacotes prontos vão para: $Pacotes"
