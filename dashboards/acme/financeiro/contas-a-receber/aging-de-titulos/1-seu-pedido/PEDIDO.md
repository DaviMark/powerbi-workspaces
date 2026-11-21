# Pedido — Aging de Títulos

> Exemplo fictício (empresa Acme Logística): é assim que um analista preenche o pedido.
>
> Arquivos → `anexos/consultas-sql/`, `anexos/imagens-e-rascunhos/`, `anexos/documentos/`. Cores e logo vêm de `identidade-visual/acme/` automaticamente.

## 1. Objetivo
O financeiro precisa saber, toda manhã, **quanto temos a receber, quanto já venceu e há quanto tempo**,
para priorizar a cobrança.

## 2. Quem usa
Coordenação de contas a receber e diretoria financeira. Reunião de cobrança diária (notebook) e
reunião mensal de resultados (TV).

## 3. Perguntas que o dashboard precisa responder
- Qual o saldo total em aberto e quanto disso está vencido?
- Como o vencido se distribui por faixa de atraso (1–30, 31–60, 61–90, 91–180, > 180 dias)?
- Quais clientes concentram o valor vencido?
- Como o saldo em aberto se distribui pelos meses de vencimento?
- Dá para ver por regional?

## 4. Regras de negócio

| Métrica | Como calcula | O que NÃO entra / exceções |
|---|---|---|
| Saldo em aberto | valor da parcela − valor pago | títulos cancelados (status `C`) |
| Vencido | saldo em aberto com vencimento anterior a hoje | títulos já pagos |
| Prazo médio de atraso | média dos dias de atraso, ponderada pelo saldo vencido | títulos a vencer |

## 5. Visuais que eu quero

| Página | O que mostrar | Tipo de visual (opcional) | Observação |
|---|---|---|---|
| Visão Geral | saldo em aberto, vencido, % vencido e prazo médio | cartões | no topo, bem grandes |
| Visão Geral | vencido por faixa de atraso | colunas | faixas na ordem (1–30 primeiro) |
| Visão Geral | clientes que mais devem | barras | do maior para o menor |
| Visão Geral | saldo em aberto por mês de vencimento | colunas |  |

## 6. Filtros
Regional (o mais importante). Se der: filial, cliente, período de vencimento.

## 7. Dados que você conhece
`anexos/consultas-sql/titulos.sql` — view do ERP com os títulos. Clientes e filiais estão em `bi.vw_clientes`
e `bi.vw_filiais`.

## 8. Restrições
Dados internos, sem dados pessoais de pessoa física. Atualização diária às 6h.
