# Aging de Títulos

> **Acme Logística › Financeiro › Contas a Receber** · status: `review` · versão `1.0.0` · conexão `acme-erp`
>
> Exemplo fictício que acompanha o Power BI Workspaces — mostra o resultado esperado de cada etapa.

## Onde coloco o quê

| Quero… | Onde |
|---|---|
| **dizer o que preciso** — objetivo, perguntas, **regras de negócio**, **visuais que quero**, filtros | [`1-seu-pedido/PEDIDO.md`](1-seu-pedido/PEDIDO.md) |
| **mandar arquivos** — SQL que já uso, prints, PDFs | `1-seu-pedido/anexos/` — `consultas-sql/`, `imagens-e-rascunhos/`, `documentos/` |
| **cores e logo** | nada a fazer aqui: vem de `identidade-visual/acme/` (vale para todos os dashboards da Acme) |
| **ver o dashboard** | `2-power-bi/AgingDeTitulos.pbip` (dois cliques) ou `pbw abrir aging-de-titulos` |
| **publicar** | exporte o `.pbit` para `3-entrega/` |
| o resto | `trabalho-da-ia/` — a IA cuida; você não precisa abrir |

## Como abrir

Dois cliques em `2-power-bi/AgingDeTitulos.pbip` ou `pbw abrir aging-de-titulos`. No Power BI Desktop,
informe a credencial do banco quando pedido e clique em **Atualizar**.

## O que é

Painel diário da cobrança: mostra **quanto há a receber, quanto já venceu e há quanto tempo**, para a
equipe priorizar quem cobrar primeiro. Usado na reunião diária de cobrança e no fechamento mensal.

**Perguntas que responde**

1. Qual o saldo em aberto e quanto dele está vencido?
2. Como o vencido se distribui por faixa de atraso?
3. Quais clientes concentram o valor vencido?
4. Como o saldo em aberto se distribui pelos meses de vencimento?

## Como usar

- **Visão Geral** — título-conclusão com o % vencido, 4 KPIs, vencido por faixa, ranking de clientes e
  saldo por mês de vencimento. Filtre por **Regional** no topo; clique em uma faixa para filtrar o resto.
- **Documentação** — todas as métricas com definição e DAX, e as cargas com o horário da última atualização.

## Cargas

| Tabela | Tipo | Grão | Fonte (SQL) | Conexão | Modo |
|---|---|---|---|---|---|
| Fato Titulos | fato | 1 linha por parcela de título | [`Fato Titulos.sql`](trabalho-da-ia/sql/Fato%20Titulos.sql) | `acme-erp` | import |
| Dim Cliente | dimensão | 1 linha por cliente | [`Dim Cliente.sql`](trabalho-da-ia/sql/Dim%20Cliente.sql) | `acme-erp` | import |
| Dim Filial | dimensão | 1 linha por filial | [`Dim Filial.sql`](trabalho-da-ia/sql/Dim%20Filial.sql) | `acme-erp` | import |
| Calendario | dimensão (DAX) | 1 linha por dia | calculada | — | — |

Atualização: diária às 06:00. Faixa de atraso e dias de atraso são calculados **na data da carga**.

## Métricas

Definições de negócio: [`trabalho-da-ia/desenho.md`](trabalho-da-ia/desenho.md) · Dicionário gerado:
[`trabalho-da-ia/dicionario.md`](trabalho-da-ia/dicionario.md) · No relatório: página **Documentação**.

| Métrica | Definição de negócio |
|---|---|
| Saldo em Aberto | Valor ainda não recebido (parcela − pago), sem cancelados |
| Valor Vencido | Saldo em aberto com vencimento anterior à data da carga |
| Valor a Vencer | Saldo em aberto com vencimento hoje ou no futuro |
| % Vencido | Valor vencido ÷ saldo em aberto |
| Prazo Médio de Atraso (dias) | Média de dias de atraso ponderada pelo saldo vencido |
| Clientes Inadimplentes | Clientes com ao menos uma parcela vencida em aberto |
| Parcelas em Aberto | Quantidade de parcelas não pagas |

## Como foi construído

- **Modelo:** star schema com 1 fato e 3 dimensões — ver [`trabalho-da-ia/desenho.md`](trabalho-da-ia/desenho.md).
  Da view do ERP (40+ colunas) importamos **12**; colunas de auditoria e texto livre ficaram de fora.
- **Power Query:** 1 etapa por tabela (`Fonte` com SQL nativo e parâmetros `Erp_Server`/`Erp_Database`).
  Faixa de atraso, tipos e exclusão de cancelados estão no SQL.
- **Medidas:** 8 medidas em `_Medidas`, em 4 pastas, todas com descrição e formato.
- **Decisões:** [`trabalho-da-ia/desenho.md`](trabalho-da-ia/desenho.md) (seção 4).
- **Conferência dos números:** [`trabalho-da-ia/conferencia.md`](trabalho-da-ia/conferencia.md).

## Segurança e privacidade

Classificação: `internal` · Dados pessoais: não (clientes PJ) · RLS: não (decisão ADR-003).

## Histórico

Ver [`trabalho-da-ia/historico.md`](trabalho-da-ia/historico.md).
