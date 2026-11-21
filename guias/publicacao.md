# Publicação

Três caminhos, do mais simples ao mais automatizado:

1. **Power BI Desktop** — abra o dashboard (`pbw abrir <dashboard>`) › **Publicar**. Configure credenciais/gateway no Service.
2. **Fabric Git integration** — conecte o workspace a uma pasta do repositório (ex.: `.../src`). Os
   arquivos `.platform` já existem; o workspace sincroniza relatório e modelo semântico a cada commit.
3. **Deployment pipelines / CI** — use os mesmos arquivos PBIP com as APIs do Fabric
   (ex.: `fabric-cicd`) a partir de um pipeline próprio da empresa.

Parâmetros de conexão (`<Prefix>_Server`, …) podem ser trocados por ambiente nas configurações do
modelo semântico no Service ou por regras do deployment pipeline — sem editar o código.

Depois de publicar: atualize `trabalho-da-ia/ficha.toml › [publish]`, a versão e o `trabalho-da-ia/historico.md`.
