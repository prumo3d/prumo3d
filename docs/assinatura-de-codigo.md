# Assinatura de código e privacidade

## Situação da assinatura

Os instaladores do Prumo 3D **ainda não são assinados digitalmente**. O pedido ao programa gratuito da
SignPath Foundation (25/10/2026) não foi aprovado por enquanto: o programa exige um projeto com mais
visibilidade pública (estrelas, contribuidores, citações externas). Até haver assinatura, o Windows mostra
o aviso de "editor desconhecido"; cada arquivo da página de versões tem o código SHA-256 ao lado.

O fluxo de publicação já tem a etapa de assinatura pronta (job "Assinar o instalador"), desligada até que
um serviço de assinatura seja configurado.

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

Se a assinatura pela SignPath for contratada (ou o projeto for aprovado no programa gratuito):

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
