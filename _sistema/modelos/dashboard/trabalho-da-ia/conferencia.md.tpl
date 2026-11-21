# Conferência — {{name}}

> Antes de publicar, os números do Power BI precisam bater com uma fonte confiável
> (consulta direta no banco, relatório oficial, sistema de origem ou o dashboard antigo). **Gate 2.**

| # | Métrica | Filtro | Esperado | Fonte da conferência | Obtido no Power BI | OK? |
|---|---|---|---|---|---|---|
| 1 | TODO | TODO | | consulta SQL / sistema | | |

## Consultas DAX de conferência

Rode no Power BI Desktop em **Exibição de consulta DAX** (ou a IA roda via Power BI Modeling MCP).

```dax
// 1) Totais de controle
EVALUATE
ROW (
    "Atualizado em", [Atualizado em]
)

// 2) Exemplo: uma métrica por mês (troque pela métrica principal)
// EVALUATE
// SUMMARIZECOLUMNS ( 'Calendario'[Ano-Mês], "Valor", [Minha Medida] )
// ORDER BY 'Calendario'[Ano-Mês]
```
