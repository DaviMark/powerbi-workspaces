---
agent: agent
argument-hint: "caminho do dashboard ou descrição"
description: "Troca a fonte de dados de um dashboard (ex.: SQL Server → HANA/BigQuery)"
---
Siga o workflow **E. CONNECTION** do `AGENTS.md`: use `pbw conectar <pasta> -c <perfil>` e reescreva
`trabalho-da-ia/sql/*.sql` no dialeto da nova fonte, depois `pbw sincronizar-sql <pasta>`.
