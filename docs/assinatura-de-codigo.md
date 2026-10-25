# Code signing policy (política de assinatura de código)

Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

Assinatura de código gratuita fornecida pela SignPath.io, com certificado da SignPath Foundation.

## O que é assinado

- O instalador do Windows (`Prumo3D_<versão>-Windows-x86_64-py311-installer.exe`) de cada versão
  publicada na [página de versões](https://github.com/prumo3d/prumo3d/releases).
- Só é assinado o que é compilado a partir deste repositório, nas máquinas do GitHub Actions
  (fluxo [`publicar.yml`](../.github/workflows/publicar.yml)). Nada compilado fora dele é assinado.
- Bibliotecas de terceiros incluídas no pacote (FreeCAD, Qt, Python, OpenCASCADE e as demais) não são
  assinadas por este projeto; ficam como os seus autores as distribuem.

## Papéis da equipe

- Committers e revisores (committers and reviewers): [membros com escrita no repositório](https://github.com/prumo3d/prumo3d/graphs/contributors)
- Aprovadores (approvers): [proprietários da organização prumo3d](https://github.com/orgs/prumo3d/people)

Cada versão só é assinada depois de aprovada manualmente por um aprovador na SignPath. Todos os
membros usam autenticação em dois fatores no GitHub e na SignPath.

## Privacidade (privacy policy)

O Prumo 3D não envia nenhuma informação sobre você, seu computador ou seus arquivos.

A única conexão que ele faz sozinho é a procura de versão nova: no máximo uma vez por dia, ao abrir,
consulta a página pública de versões do projeto no GitHub (`api.github.com/repos/prumo3d/prumo3d/releases`).
Essa consulta não leva dado do usuário além do que qualquer acesso a um site leva (endereço IP, sujeito à
[política de privacidade do GitHub](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement)).
Ela pode ser desligada em **Preferências → Atualizações → "Procurar versão nova ao abrir"**.

Downloads de versão nova só acontecem quando o usuário clica em "Atualizar agora".

This program will not transfer any information to other networked systems unless specifically requested
by the user, except the daily check for a new version described above (a request to GitHub's public
releases page, with no user data), which can be turned off in Preferences.

## Configuração na SignPath (para os mantenedores)

Depois que a SignPath aprovar o projeto:

1. No GitHub, em **Settings → Secrets and variables → Actions**:
   - segredo `SIGNPATH_API_TOKEN`: token de um usuário da SignPath com permissão de enviar pedidos;
   - variável `SIGNPATH_ORGANIZATION_ID`: o ID da organização na SignPath;
   - (opcionais, se os nomes forem outros) `SIGNPATH_PROJECT_SLUG` (padrão `prumo3d`),
     `SIGNPATH_POLICY_SLUG` (padrão `release-signing`), `SIGNPATH_ARTIFACT_CONFIG_SLUG` (padrão `instalador`).
2. Na SignPath, ligar o projeto ao GitHub (Trusted Build System) e criar a configuração de artefato
   `instalador`. O GitHub entrega o artefato como ZIP, então a raiz é um `<zip-file>`:

   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <artifact-configuration xmlns="http://signpath.io/artifact-configuration/v1">
     <zip-file>
       <pe-file path="Prumo3D_*-installer.exe" max-matches="1">
         <authenticode-sign/>
       </pe-file>
     </zip-file>
   </artifact-configuration>
   ```

3. Publicar a versão normalmente (Actions → Publicar versão). O job "Assinar o instalador" fica
   esperando a aprovação na SignPath; aprovado, a versão sai com o instalador assinado.
