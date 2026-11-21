# Nome do Dashboard

> **Nome da Empresa › Nome da Area › Nome da Subarea** · status: `draft` · versão `0.1.0`

## Onde coloco o quê

| Quero… | Onde |
|---|---|
| **dizer o que preciso** — objetivo, perguntas, **regras de negócio**, **visuais que quero**, filtros | [`1-seu-pedido/PEDIDO.md`](1-seu-pedido/PEDIDO.md) |
| **mandar arquivos** — SQL que já uso, prints, PDFs, relatório de referência | `1-seu-pedido/anexos/` — `consultas-sql/`, `imagens-e-rascunhos/`, `documentos/` |
| **cores e logo** | nada a fazer aqui: vem de `identidade-visual/nome-da-empresa/` (vale para todos os dashboards da empresa) |
| **ver o dashboard** | `2-power-bi/NomeDoDashboard.pbip` (dois cliques) ou `pbw abrir nome-do-dashboard` |
| **publicar** | exporte o `.pbit` para `3-entrega/` |
| o resto | `trabalho-da-ia/` — a IA cuida; você não precisa abrir |

**Passo a passo:** preencha o `PEDIDO.md` → peça à IA *"crie o dashboard nome-do-dashboard"* → abra o
`.pbip` e aprove as páginas de protótipo → abra de novo e confira os números → exporte o `.pbit`.

<!-- Daqui para baixo a IA mantém. Linguagem de negócio primeiro, detalhes técnicos depois. -->

## Como abrir

Dois cliques em `2-power-bi/NomeDoDashboard.pbip` ou `pbw abrir nome-do-dashboard`. Enquanto o desenho não é
aprovado, as páginas são um **protótipo**: caixas cinza mostrando onde cada visual vai ficar.

## O que é

TODO: em 2–3 frases — que decisão este dashboard apoia, para quem e com que frequência.

**Perguntas que responde**

1. TODO

## Como usar

TODO: páginas, filtros principais e a página **Documentação** (todas as métricas explicadas).

## Cargas

| Tabela | Tipo | Grão | Consulta | Conexão | Modo |
|---|---|---|---|---|---|
| TODO | fato/dimensão | 1 linha por … | `trabalho-da-ia/sql/….sql` | `sqlserver.example` | import |

Atualização: TODO (frequência, horário, gateway).

## Métricas

| Métrica | Definição de negócio |
|---|---|
| TODO | TODO |

## Como foi construído

Modelo, métricas, páginas e decisões: [`trabalho-da-ia/desenho.md`](trabalho-da-ia/desenho.md) ·
Conferência dos números: [`trabalho-da-ia/conferencia.md`](trabalho-da-ia/conferencia.md) ·
Dicionário: [`trabalho-da-ia/dicionario.md`](trabalho-da-ia/dicionario.md) ·
Histórico: [`trabalho-da-ia/historico.md`](trabalho-da-ia/historico.md).

## Segurança e privacidade

Classificação: `internal` · Dados pessoais: não · RLS: não.
