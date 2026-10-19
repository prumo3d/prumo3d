# Como contribuir com o Prumo 3D

Obrigado pelo interesse em melhorar o Prumo 3D. Este documento explica como relatar problemas, propor
mudanças e onde cada tipo de contribuição deve ser feito.

## 1. Onde contribuir

O Prumo 3D é formado por duas partes, e cada contribuição tem o seu lugar:

| O que você quer mudar | Onde contribuir |
|---|---|
| Complemento do Prumo 3D (`prumo-addon/`): faixa de ferramentas, tradução, tela inicial, assistente de simulação, tutorial, tema, ícones | Aqui, neste repositório |
| Roteiros de compilação e instalador (`prumo-build/`, `package/`) | Aqui, neste repositório |
| Correção ou recurso no núcleo do FreeCAD que serve para todos os usuários do FreeCAD | No [repositório do FreeCAD](https://github.com/FreeCAD/FreeCAD), seguindo o [processo de contribuição do FreeCAD](https://github.com/FreeCAD/FreeCAD/blob/main/CONTRIBUTING.md) |

Correções que valem para todo o FreeCAD devem ir primeiro para o projeto original. Assim todos se beneficiam e
o Prumo 3D recebe a correção quando atualizar a base.

## 2. Fundamentos

1. O projeto usa o Git e fica hospedado no GitHub, em
   [prumo3d/prumo3d](https://github.com/prumo3d/prumo3d).
2. Problemas e sugestões são registrados como
   [issues](https://github.com/prumo3d/prumo3d/issues).
3. Mudanças no código são propostas por *pull request* (PR).
4. Cada PR deve resolver um único problema bem definido.

## 3. Ramos

O ramo `main` tem como base o FreeCAD 1.1.4 (estável) e é dele que saem as versões publicadas.
Abra seus PRs contra o `main`.

## 4. Licença, autoria e créditos

1. O Prumo 3D é distribuído sob a GNU LGPL versão 2.1 ou posterior, a mesma do FreeCAD. Os detalhes estão
   no arquivo [LICENSE](LICENSE).
2. Toda contribuição deve usar uma licença compatível.
3. As contribuições pertencem a seus autores, a menos que sejam cedidas a outra pessoa.
4. Quem contribui garante, dentro do razoável, que a contribuição não viola direitos autorais ou licenças de
   terceiros.

## 5. Requisitos de uma contribuição

1. Contribuições são enviadas como PR.
2. Use uma conta do GitHub com seu nome real ou um apelido conhecido.
3. O PR deve ser uma resposta mínima e precisa a um problema identificado.
4. Evite acrescentar novas dependências ao projeto, a menos que não haja alternativa.
5. O código deve seguir o estilo do arquivo que está sendo alterado. No complemento Prumo, textos de interface
   são escritos em português do Brasil.
6. Cada commit de um PR deve compilar e funcionar sozinho. Commits intermediários ("checkpoint") devem ser
   unidos antes do envio.
7. O PR deve compilar e passar nos testes do projeto. No complemento Prumo, rode os testes pela aba Prumo
   (comando *Testes automáticos*) antes de enviar.
8. A mensagem de cada commit deve explicar de forma direta o que ele faz.
9. O título do PR deve resumir o que ele faz. Se o PR mudar a interface, a descrição deve trazer imagens de
   antes e depois.
10. Se o PR contiver trabalho de outra pessoa, a descrição deve dar o crédito na primeira linha e os commits
    devem manter a autoria original.
11. Contribuições devem seguir a [Política de IA](AI_POLICY.md).

## 6. Processo

1. Para pedir uma mudança, abra uma issue descrevendo o problema que você enfrenta ou observa.
2. A issue deve ser completa: quem lê não deve precisar visitar outros sites para entender o problema.
3. Concentre-se na tarefa do usuário e no resultado esperado.
4. Para enviar uma solução, abra um PR contra o ramo `main`.
5. A discussão sobre a solução acontece no próprio PR ou na issue relacionada.
6. Os mantenedores revisam e aceitam ou recusam o PR pela interface do GitHub.
7. PRs que ainda precisam de bastante trabalho devem ficar como rascunho (*draft*).
8. Quem abriu a issue pode fechá-la depois de conferir que o PR resolveu o problema.

## 7. Versões

Versões são marcadas com uma *tag* `v…` no ramo `main` (ex.: `v1.1.4`); o GitHub Actions gera os
instaladores e publica tudo na
[página de versões](https://github.com/prumo3d/prumo3d/releases).

---

*Este documento é adaptado do
[processo de contribuição do FreeCAD](https://github.com/FreeCAD/FreeCAD/blob/main/CONTRIBUTING.md).*
