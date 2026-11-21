---
description: Troca a fonte de dados de um dashboard (ex.: SQL Server → HANA/BigQuery)
argument-hint: [caminho ou descrição]
---
Siga o workflow **E. CONNECTION** do `AGENTS.md`: use `pbw conectar <pasta> -c <perfil>` e reescreva
`trabalho-da-ia/sql/*.sql` no dialeto da nova fonte, depois `pbw sincronizar-sql <pasta>`.

Argumentos: $ARGUMENTS
