# conexoes/ — perfis de conexão

Cada arquivo aqui descreve **onde** os dados estão, nunca **como entrar**. O dashboard aponta para um
perfil pelo nome (`trabalho-da-ia/ficha.toml › [data] › connection`) e o CLI gera os parâmetros do Power Query.

```
conexoes/
├── sqlserver.example.toml     ← exemplos (versionados)
├── erp.toml                   ← seu perfil (versionado, só endereços)
└── erp.local.toml             ← sobrescreve valores na SUA máquina (ignorado pelo Git)
```

## Criar um perfil

```bash
cp conexoes/saphana.example.toml conexoes/sap.toml   # edite server/prefix
pbw conexoes                 # confere
pbw conectar aging-de-titulos -c sap
```

O `pbw conectar` atualiza a `trabalho-da-ia/ficha.toml`, regenera `expressions.tmdl` (parâmetros `Sap_Server`, …) e
reescreve a partição de cada tabela a partir de `trabalho-da-ia/sql/*.sql`.

## Tipos suportados

| `type` | Fonte | Parâmetros | Power Query gerado (1 etapa) |
|---|---|---|---|
| `sqlserver` | SQL Server, Azure SQL, Fabric Warehouse/SQL endpoint, Synapse | `server`, `database` | `Value.NativeQuery(Sql.Database(…), sql, null, [EnableFolding=true])` |
| `saphana` | SAP HANA | `server` | `SapHana.Database(…, [Implementation="2.0", Query=sql])` |
| `bigquery` | Google BigQuery | `billing_project` | `Value.NativeQuery(GoogleBigQuery.Database(…){…}[Data], sql, …)` |
| `postgresql` | PostgreSQL | `server`, `database` | `Value.NativeQuery(PostgreSQL.Database(…), sql, …)` |
| `snowflake` | Snowflake | `server`, `warehouse`, `database` | `Value.NativeQuery(Snowflake.Databases(…){…}[Data], sql, …)` |
| `databricks` | Databricks SQL | `host`, `http_path`, `catalog` | `Value.NativeQuery(Databricks.Catalogs(…){…}[Data], sql, …)` |
| `oracle` | Oracle | `server` | `Oracle.Database(…, [Query=sql])` |
| `mysql` | MySQL / MariaDB | `server`, `database` | `MySQL.Database(…, [Query=sql])` |

## Um dashboard, mais de uma fonte

A conexão padrão vem do `trabalho-da-ia/ficha.toml`. Uma tabela pode usar outra fonte com um cabeçalho no SQL:

```sql
-- @connection: gcp
SELECT ...
```

## Segurança

- **Credenciais nunca vão para arquivos.** O Power BI pede usuário/senha no Desktop e guarda no cofre do
  Windows; no Service, ficam no gateway/conexão de nuvem. PBIP e PBIT não carregam senhas.
- Se o endereço do servidor for sensível na sua empresa, deixe o valor real só no `*.local.toml`.
- `pbw seguranca` bloqueia commits com `Password=`, chaves privadas, tokens e `*.local.toml`.
- Na primeira atualização o Desktop pede aprovação da consulta nativa — é esperado (Opções › Segurança).
