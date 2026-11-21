# Conferência — Aging de Títulos

| # | Métrica | Filtro | Esperado | Fonte da conferência | Obtido no PBI | OK? |
|---|---|---|---|---|---|---|
| 1 | Saldo em Aberto | nenhum | `SELECT SUM(vl_parcela - vl_pago) FROM bi.vw_titulos_receber WHERE status <> 'C'` | SQL direto | | |
| 2 | Valor Vencido | nenhum | mesma consulta com `dt_pagamento IS NULL AND dt_vencimento < hoje` | SQL direto | | |
| 3 | Vencido + A Vencer = Saldo | nenhum | `TRUE` | consulta DAX #1 abaixo | | |
| 4 | Clientes Inadimplentes | Regional = Sul | relatório de cobrança do ERP | ERP | | |

## Consultas DAX de conferência

Rode no **Exibição de consulta DAX** do Power BI Desktop (ou via Power BI Modeling MCP).

```dax
// 1) Totais de controle
EVALUATE
ROW (
    "Saldo em Aberto", [Saldo em Aberto],
    "Valor Vencido", [Valor Vencido],
    "Valor a Vencer", [Valor a Vencer],
    "Vencido + A Vencer = Saldo?", [Valor Vencido] + [Valor a Vencer] = [Saldo em Aberto],
    "Parcelas em Aberto", [Parcelas em Aberto]
)

// 2) Vencido por faixa (deve somar o Valor Vencido)
EVALUATE
SUMMARIZECOLUMNS (
    'Fato Titulos'[Faixa Atraso],
    "Vencido", [Valor Vencido]
)
ORDER BY 'Fato Titulos'[Faixa Atraso]
```
