# Consultas do modelo (Aging de Títulos)

Um arquivo por tabela do modelo. **Nome do arquivo = nome da tabela no Power BI.**

```sql
-- @table: Fato Titulos
-- @description: Títulos a receber em aberto e liquidados
-- @grain: 1 linha por título por parcela
-- @connection: acme-erp        (opcional; padrão = ficha.toml)
-- @mode: import                       (import | directquery)
SELECT ...
```

Depois de editar, rode `pbw sincronizar-sql aging-de-titulos` para gravar a consulta no modelo
(1 etapa de Power Query: `Fonte`). Nunca edite a consulta direto no Power Query.
