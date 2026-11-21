"""`pbw sincronizar-sql` / `pbw conectar` — SQL files are the single source of truth for every load.

sql/<Tabela>.sql  ──►  tables/<Tabela>.tmdl  (partition with ONE Power Query step)
conexoes/*.toml ──► expressions.tmdl (Power Query parameters)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import pbip, tmdl
from .connectors import Profile, expressions_tmdl, load_profile
from .layout import MANIFEST, SQL, powerbi_dir
from .util import info, ok, read_toml, rel, warn, write_text

HEADER_RE = re.compile(r"^\s*--\s*@(?P<key>[a-z_]+)\s*:\s*(?P<value>.+?)\s*$", re.I)


@dataclass
class SqlFile:
    path: Path
    table: str
    sql: str
    connection: str
    mode: str = "import"
    description: str = ""
    grain: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def read_sql(path: Path, default_connection: str) -> SqlFile:
    text = path.read_text(encoding="utf-8-sig")
    meta: dict[str, str] = {}
    for line in text.splitlines():
        m = HEADER_RE.match(line)
        if m:
            meta[m.group("key").lower()] = m.group("value")
    body = "\n".join(line for line in text.splitlines() if not HEADER_RE.match(line)).strip()
    return SqlFile(
        path=path,
        table=meta.get("table", path.stem),
        sql=body.rstrip().rstrip(";"),
        connection=meta.get("connection", default_connection),
        mode=meta.get("mode", "import").lower(),
        description=meta.get("description", ""),
        grain=meta.get("grain", ""),
        extra=meta,
    )


def dashboard_manifest(dash: Path) -> dict:
    mf = dash / MANIFEST
    if not mf.exists():
        raise SystemExit(f"ERRO: {dash} não tem {MANIFEST} (não é uma pasta de dashboard).")
    return read_toml(mf)


def sql_files(dash: Path, default_connection: str) -> list[SqlFile]:
    return [read_sql(p, default_connection) for p in sorted((dash / SQL).glob("*.sql"))]


def m_lines(profile: Profile, sql: str) -> list[str]:
    return ["let", f"    Fonte = {profile.m_expression(sql)}", "in", "    Fonte"]


def sync(root: Path, dash: Path, quiet: bool = False) -> int:
    manifest = dashboard_manifest(dash)
    default_conn = manifest.get("data", {}).get("connection", "")
    definition = tmdl.find_definition(powerbi_dir(dash))
    if definition is None:
        raise SystemExit(f"ERRO: {dash.name}/2-power-bi/*.SemanticModel não encontrado. Rode `pbw diagnostico`.")
    files = sql_files(dash, default_conn)
    profiles: dict[str, Profile] = {default_conn: load_profile(root, default_conn)} if default_conn else {}
    for f in files:
        if f.connection not in profiles:
            profiles[f.connection] = load_profile(root, f.connection)

    write_text(definition / "expressions.tmdl", expressions_tmdl(list(profiles.values())))
    changed = 0
    for f in files:
        prof = profiles[f.connection]
        if f.mode == "directquery" and not prof.connector.supports_directquery:
            warn(f"{f.path.name}: {prof.connector.label} não suporta DirectQuery com SQL nativo; usando import.")
            f.mode = "import"
        table_file = definition / "tables" / f"{f.table}.tmdl"
        lines = m_lines(prof, f.sql)
        if table_file.exists():
            if tmdl.replace_partition_source(table_file, f.table, lines):
                changed += 1
                if not quiet:
                    info(f"Atualizado: {rel(table_file, root)}")
        else:
            desc = [x for x in (
                f.description,
                f"Grão: {f.grain}" if f.grain else "",
                f"Fonte: trabalho-da-ia/sql/{f.path.name} · Conexão: {f.connection} ({prof.connector.label})",
            ) if x]
            write_text(table_file, pbip.source_table_tmdl(f.table, prof.m_expression(f.sql), desc, f.mode))
            changed += 1
            warn(f"Criado stub {rel(table_file, root)} — declare as colunas (dataType + sourceColumn).")
    if not quiet:
        ok(f"sincronizar-sql: {len(files)} consulta(s), {changed} tabela(s) alterada(s), "
           f"{len(profiles)} perfil(is) de conexão.")
    return changed


def set_connection(root: Path, dash: Path, connection: str) -> None:
    load_profile(root, connection)  # validates
    mf = dash / MANIFEST
    text = mf.read_text(encoding="utf-8")
    new, n = re.subn(r'(?m)^(\s*connection\s*=\s*)"[^"]*"', rf'\g<1>"{connection}"', text, count=1)
    if n == 0:
        raise SystemExit("ERRO: não encontrei `connection = \"...\"` em [data] na trabalho-da-ia/ficha.toml.")
    write_text(mf, new)
    ok(f"ficha.toml → connection = \"{connection}\"")
    sync(root, dash)


# --------------------------------------------------------------------------- #
# SELECT list (best effort) for validation
# --------------------------------------------------------------------------- #


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def select_aliases(sql: str) -> list[str] | None:
    s = _strip_comments(sql)
    depth = 0
    i = 0
    start = end = -1
    low = s.lower()
    while i < len(s):
        ch = s[i]
        if ch in "'\"":
            j = s.find(ch, i + 1)
            i = len(s) if j < 0 else j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0:
            if start < 0 and re.match(r"select\b", low[i:]) and (i == 0 or not low[i - 1].isalnum()):
                start = i + 6
                m = re.match(r"\s+(distinct|top\s+\d+|all)\b", low[start:])
                if m:
                    start += m.end()
            elif start >= 0 and re.match(r"from\b", low[i:]) and not low[i - 1].isalnum():
                end = i
                break
        i += 1
    if start < 0:
        return None
    body = s[start:end if end > 0 else len(s)]
    items, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    out: list[str] = []
    for it in (x.strip() for x in items if x.strip()):
        if it == "*" or it.endswith(".*"):
            return None
        alias = _top_level_alias(it)
        if alias is None:
            m2 = re.search(r"([\[\"`][^\]\"`]+[\]\"`]|[\w$#]+)\s*$", it)
            alias = m2.group(1) if m2 else it
            if "." in alias and not alias.startswith(("[", '"', "`")):
                alias = alias.split(".")[-1]
        out.append(alias.strip().strip("[]\"`"))
    return out


def _top_level_alias(item: str) -> str | None:
    """Text after the last `AS` keyword that is not inside parentheses."""
    depth, last = 0, -1
    low = item.lower()
    i = 0
    while i < len(item):
        ch = item[i]
        if ch in "'\"[`":
            close = {"'": "'", '"': '"', "[": "]", "`": "`"}[ch]
            j = item.find(close, i + 1)
            i = len(item) if j < 0 else j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and low.startswith("as", i) and (i == 0 or not low[i - 1].isalnum()) \
                and (i + 2 < len(low) and low[i + 2].isspace()):
            last = i
        i += 1
    if last < 0:
        return None
    return item[last + 2:].strip()
