---
applyTo: "**/*.tmdl"
---
TMDL rules: tabs for indentation; quote names with spaces in single quotes; `///` description directly
above every table and measure; measures live in `_Medidas` with `formatString` and `displayFolder`;
never add `lineageTag`; never edit `expressions.tmdl` by hand (run `pbw conectar`);
partitions of source tables are generated from `trabalho-da-ia/sql/*.sql` by `pbw sincronizar-sql`.
After editing run `pbw validar <dashboard>`: the `.pbip` must still open.
