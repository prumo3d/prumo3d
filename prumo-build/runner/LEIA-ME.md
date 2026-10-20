# Runner próprio (gerar os pacotes no seu computador)

Enquanto o repositório é privado, os minutos do GitHub Actions do plano gratuito acabam rápido (uma
publicação completa leva horas). O fluxo **Publicar versão** roda, por padrão, num computador próprio
registrado como *runner*, sem custo.

## Windows (uma vez)

1. GitHub → `prumo3d/prumo3d` → **Settings → Actions → Runners → New self-hosted runner** → Windows.
   Copie só o código que vem depois de `--token` (vale por cerca de 1 hora).
2. No PowerShell:

   ```powershell
   powershell -ExecutionPolicy Bypass -File C:\dev\prumo3d-scripts\instalar_runner_windows.ps1
   ```

3. Cole o código quando pedir. O runner fica em `C:\ar`, com o rótulo `prumo`.

Requisitos: Git for Windows (o `bash` dele é usado nos passos), Visual Studio 2022 com C++ (o mesmo da
compilação local), uns 40 GB livres.

## Para compilar

1. Ligue o runner: `C:\ar\run.cmd` (deixe a janela aberta).
2. GitHub → **Actions → Publicar versão → Run workflow**: máquina `pc`, plataformas `win-64`.
3. Os pacotes ficam em `C:\dev\Prumo3D-pacotes\<rótulo>-<número>`.

A primeira execução baixa o ambiente do pixi (alguns GB); as seguintes reaproveitam.

## Linux (opcional, depois)

O pacote Linux (AppImage) precisa de um runner Linux — por exemplo dentro do WSL (Ubuntu), registrado
com os rótulos `prumo` e `Linux`.

## Quando o repositório for público

Volte a usar as máquinas do GitHub (máquina `github`, gratuito em repositório público) e desligue o
runner próprio: runner próprio em repositório público executaria código de qualquer pull request.
