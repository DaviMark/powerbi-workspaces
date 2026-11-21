"""Connection profiles and Power Query (M) templates — one step, zero transformations.

A *profile* lives in conexoes/<name>.toml (committable, NO secrets) and can be
overridden by conexoes/<name>.local.toml (git-ignored) with real hosts.

Power BI never stores passwords in PBIP/PBIT files: credentials stay in Power BI Desktop
(Data source settings) and in the Power BI Service (gateway / cloud connection).
That is why profiles only carry *addresses*, never secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .util import m_string, pascal, read_toml


@dataclass(frozen=True)
class Param:
    key: str          # key inside [parameters]
    suffix: str       # Power BI parameter suffix -> <Prefix>_<Suffix>
    label: str        # human description


@dataclass(frozen=True)
class Connector:
    type: str
    label: str
    params: tuple[Param, ...]
    # builds the single M expression. receives {key: M identifier} and an M text literal
    build: Callable[[dict[str, str], str], str]
    notes: str = ""
    supports_directquery: bool = True


def _nq(source: str, query: str) -> str:
    return f"Value.NativeQuery({source}, {query}, null, [EnableFolding = true])"


CONNECTORS: dict[str, Connector] = {
    "sqlserver": Connector(
        "sqlserver",
        "SQL Server · Azure SQL · Fabric Warehouse/SQL endpoint · Synapse",
        (Param("server", "Server", "Servidor (host[,porta] ou endpoint)"),
         Param("database", "Database", "Banco de dados")),
        lambda p, q: _nq(f"Sql.Database({p['server']}, {p['database']})", q),
    ),
    "saphana": Connector(
        "saphana",
        "SAP HANA",
        (Param("server", "Server", "Servidor:porta (ex.: hana.empresa.local:30015)"),),
        lambda p, q: f'SapHana.Database({p["server"]}, [Implementation = "2.0", Query = {q}])',
        notes="Use views calculadas/CDS do HANA para o star schema. Valide o driver 2.0 no Desktop.",
    ),
    "bigquery": Connector(
        "bigquery",
        "Google BigQuery (GCP)",
        (Param("billing_project", "BillingProject", "Projeto de faturamento (billing project id)"),),
        lambda p, q: _nq(
            f"GoogleBigQuery.Database([BillingProject = {p['billing_project']}])"
            f"{{[Name = {p['billing_project']}]}}[Data]",
            q,
        ),
        notes="Referencie tabelas totalmente qualificadas no SQL: `projeto.dataset.tabela`.",
    ),
    "postgresql": Connector(
        "postgresql",
        "PostgreSQL",
        (Param("server", "Server", "Servidor[:porta]"), Param("database", "Database", "Banco de dados")),
        lambda p, q: _nq(f"PostgreSQL.Database({p['server']}, {p['database']})", q),
    ),
    "snowflake": Connector(
        "snowflake",
        "Snowflake",
        (Param("server", "Server", "Conta (xxx.snowflakecomputing.com)"),
         Param("warehouse", "Warehouse", "Warehouse"),
         Param("database", "Database", "Banco de dados")),
        lambda p, q: _nq(
            f"Snowflake.Databases({p['server']}, {p['warehouse']})"
            f"{{[Name = {p['database']}, Kind = \"Database\"]}}[Data]",
            q,
        ),
    ),
    "databricks": Connector(
        "databricks",
        "Databricks (SQL Warehouse)",
        (Param("host", "Host", "Server hostname"),
         Param("http_path", "HttpPath", "HTTP path do SQL Warehouse"),
         Param("catalog", "Catalog", "Catálogo (Unity Catalog)")),
        lambda p, q: _nq(
            f"Databricks.Catalogs({p['host']}, {p['http_path']}, [Catalog = null, Database = null, "
            f"EnableAutomaticProxyDiscovery = null]){{[Name = {p['catalog']}, Kind = \"Database\"]}}[Data]",
            q,
        ),
    ),
    "oracle": Connector(
        "oracle",
        "Oracle Database",
        (Param("server", "Server", "host:porta/serviço ou alias TNS"),),
        lambda p, q: f"Oracle.Database({p['server']}, [HierarchicalNavigation = true, Query = {q}])",
        supports_directquery=False,
    ),
    "mysql": Connector(
        "mysql",
        "MySQL / MariaDB",
        (Param("server", "Server", "Servidor[:porta]"), Param("database", "Database", "Banco de dados")),
        lambda p, q: f"MySQL.Database({p['server']}, {p['database']}, [ReturnSingleDatabase = true, Query = {q}])",
        supports_directquery=False,
    ),
}


@dataclass
class Profile:
    name: str
    type: str
    description: str
    prefix: str
    values: dict[str, str]
    source_files: list[Path] = field(default_factory=list)
    is_example: bool = False

    @property
    def connector(self) -> Connector:
        return CONNECTORS[self.type]

    def param_ident(self, key: str) -> str:
        param = next(p for p in self.connector.params if p.key == key)
        return f"{self.prefix}_{param.suffix}"

    def identifiers(self) -> dict[str, str]:
        return {p.key: self.param_ident(p.key) for p in self.connector.params}

    def m_expression(self, sql: str) -> str:
        return self.connector.build(self.identifiers(), m_string(sql))


def connections_dir(root: Path) -> Path:
    from .layout import CONNECTIONS
    return root / CONNECTIONS


def list_profiles(root: Path) -> list[str]:
    names: set[str] = set()
    for f in connections_dir(root).glob("*.toml"):
        stem = f.name[: -len(".toml")]
        if stem.endswith(".local"):
            stem = stem[: -len(".local")]
        names.add(stem)
    return sorted(names)


def load_profile(root: Path, name: str) -> Profile:
    folder = connections_dir(root)
    base = folder / f"{name}.toml"
    local = folder / f"{name}.local.toml"
    if not base.exists() and not local.exists():
        available = ", ".join(list_profiles(root)) or "(nenhum)"
        raise SystemExit(f"ERRO: perfil de conexão '{name}' não existe. Disponíveis: {available}")

    data: dict = {}
    files: list[Path] = []
    for f in (base, local):
        if f.exists():
            files.append(f)
            part = read_toml(f)
            for section, content in part.items():
                if isinstance(content, dict):
                    data.setdefault(section, {}).update(content)
                else:
                    data[section] = content

    conn = data.get("connection", {})
    ctype = conn.get("type", "")
    if ctype not in CONNECTORS:
        raise SystemExit(
            f"ERRO: perfil '{name}' tem type='{ctype}'. Tipos suportados: {', '.join(CONNECTORS)}"
        )
    params = {k: str(v) for k, v in data.get("parameters", {}).items()}
    missing = [p.key for p in CONNECTORS[ctype].params if p.key not in params]
    if missing:
        raise SystemExit(f"ERRO: perfil '{name}' sem parâmetros obrigatórios: {', '.join(missing)}")
    return Profile(
        name=name,
        type=ctype,
        description=conn.get("description", ""),
        prefix=conn.get("prefix") or pascal(name),
        values=params,
        source_files=files,
        is_example=name.endswith(".example"),
    )


def expressions_tmdl(profiles: list[Profile]) -> str:
    """Power Query parameters for every profile used by a dashboard."""
    blocks: list[str] = []
    for prof in profiles:
        for p in prof.connector.params:
            value = prof.values[p.key].replace('"', '""')
            ident = prof.param_ident(p.key)
            blocks.append(
                f"/// {p.label} — perfil de conexão '{prof.name}' ({prof.connector.label}).\n"
                f"/// Gerado por `pbw conectar`. Altere em conexoes/{prof.name}.toml, não aqui.\n"
                f'expression {ident} = "{value}" meta [IsParameterQuery=true, Type="Text", '
                f"IsParameterQueryRequired=true]\n"
                f"\tqueryGroup: Parametros\n\n"
                f"\tannotation PBI_ResultType = Text\n"
            )
    return "\n".join(blocks)
