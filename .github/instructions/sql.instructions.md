---
applyTo: "**/sql/*.sql"
---
Model SQL rules: one file per model table, header tags `-- @table`, `-- @description`, `-- @grain`
(optional `-- @connection`, `-- @mode`); explicit column list with business-friendly aliases matching the
TMDL `sourceColumn`; CAST to correct types; business rules and filters here (not in Power Query);
no `SELECT *`, no `ORDER BY`; dialect of the connection type in `conexoes/<profile>.toml`.
After editing run `pbw sincronizar-sql <dashboard>`.
