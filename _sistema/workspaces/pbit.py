"""Read a .pbit (Power BI template) WITHOUT Power BI and turn it into AI-friendly docs.

A .pbit is a ZIP file. We only read metadata:
  * DataModelSchema  -> tables, columns, measures, relationships, Power Query (M)
  * Report/Layout    -> legacy report format (pages + visuals)
  * Report/definition/** -> PBIR report format (pages + visuals)
Nothing is executed, nothing is sent anywhere. A .pbix is supported too (metadata only;
the data model binary is never opened).
"""

from __future__ import annotations

import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import write_json, write_text

# Functions whose first literal argument is usually a host / server name
HOST_FUNCS = (
    "Sql.Database", "Sql.Databases", "SapHana.Database", "PostgreSQL.Database", "Oracle.Database",
    "MySQL.Database", "Snowflake.Databases", "Databricks.Catalogs", "Odbc.DataSource", "OleDb.DataSource",
    "Web.Contents", "SharePoint.Files", "SharePoint.Tables", "SharePoint.Contents", "File.Contents",
    "Folder.Files", "Excel.Workbook", "AnalysisServices.Database", "AzureStorage.Blobs",
)
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PQ_HEAVY = (
    "Table.AddColumn", "Table.TransformColumns", "Table.SelectRows", "Table.Group", "Table.NestedJoin",
    "Table.Join", "Table.ExpandTableColumn", "Table.Pivot", "Table.Unpivot", "Table.UnpivotOtherColumns",
    "Table.ReplaceValue", "Table.Combine", "Table.Distinct", "Table.Sort", "Table.Buffer", "List.Generate",
    "Table.FillDown", "Table.SplitColumn", "Table.DuplicateColumn", "Table.TransformColumnTypes",
)
EMBEDDED_DATA = re.compile(r"Binary\.Decompress\(Binary\.FromText\(|Table\.FromRows\(Json\.Document\(")
AUTO_DATE = re.compile(r"^(LocalDateTable_|DateTableTemplate_)")


def _decode(raw: bytes) -> str:
    for enc in ("utf-16", "utf-8-sig", "utf-16-le", "latin-1"):
        try:
            text = raw.decode(enc)
            if text.lstrip().startswith(("{", "[")):
                return text
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _expr(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(v) for v in value)
    return str(value or "")


def redact(text: str) -> str:
    """Hide hosts/IPs that appear as the first literal of connector functions."""
    for fn in HOST_FUNCS:
        text = re.sub(rf'({re.escape(fn)}\(\s*)"([^"]*)"', r'\1"<redacted>"', text)
    return IPV4.sub("<ip-redacted>", text)


@dataclass
class Extraction:
    source: str
    culture: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    expressions: list[dict[str, Any]] = field(default_factory=list)
    roles: list[dict[str, Any]] = field(default_factory=list)
    pages: list[dict[str, Any]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    report_format: str = "unknown"


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


def _read_model(z: zipfile.ZipFile, ex: Extraction, do_redact: bool) -> None:
    if "DataModelSchema" not in z.namelist():
        ex.findings.append("Arquivo sem DataModelSchema (PBIX com modelo binário). Exporte como .pbit.")
        return
    schema = json.loads(_decode(z.read("DataModelSchema")))
    model = schema.get("model", {})
    ex.culture = model.get("culture", "")
    r = redact if do_redact else (lambda s: s)
    for t in model.get("tables", []):
        partitions = []
        for p in t.get("partitions", []):
            src = p.get("source", {})
            partitions.append({
                "name": p.get("name"),
                "mode": p.get("mode", "import"),
                "type": src.get("type", ""),
                "expression": r(_expr(src.get("expression"))),
            })
        ex.tables.append({
            "name": t.get("name"),
            "description": _expr(t.get("description")),
            "isHidden": t.get("isHidden", False),
            "isPrivate": t.get("isPrivate", False),
            "dataCategory": t.get("dataCategory", ""),
            "columns": [
                {
                    "name": c.get("name"),
                    "dataType": c.get("dataType", ""),
                    "type": c.get("type", "data"),
                    "sourceColumn": c.get("sourceColumn", ""),
                    "expression": _expr(c.get("expression")),
                    "isHidden": c.get("isHidden", False),
                    "formatString": c.get("formatString", ""),
                    "sortByColumn": c.get("sortByColumn", ""),
                }
                for c in t.get("columns", [])
                if not str(c.get("name", "")).startswith("RowNumber-")
            ],
            "measures": [
                {
                    "name": m.get("name"),
                    "expression": _expr(m.get("expression")),
                    "formatString": m.get("formatString", ""),
                    "displayFolder": m.get("displayFolder", ""),
                    "description": _expr(m.get("description")),
                    "isHidden": m.get("isHidden", False),
                }
                for m in t.get("measures", [])
            ],
            "hierarchies": [h.get("name") for h in t.get("hierarchies", [])],
            "partitions": partitions,
        })
    for rel in model.get("relationships", []):
        ex.relationships.append({
            "fromTable": rel.get("fromTable"), "fromColumn": rel.get("fromColumn"),
            "toTable": rel.get("toTable"), "toColumn": rel.get("toColumn"),
            "crossFilteringBehavior": rel.get("crossFilteringBehavior", "oneDirection"),
            "isActive": rel.get("isActive", True),
            "fromCardinality": rel.get("fromCardinality", "many"),
            "toCardinality": rel.get("toCardinality", "one"),
        })
    for e in model.get("expressions", []):
        ex.expressions.append({"name": e.get("name"), "kind": e.get("kind", "m"),
                               "expression": r(_expr(e.get("expression")))})
    for role in model.get("roles", []):
        ex.roles.append({
            "name": role.get("name"),
            "filters": [{"table": tp.get("name"), "filter": _expr(tp.get("filterExpression"))}
                        for tp in role.get("tablePermissions", [])],
        })


# --------------------------------------------------------------------------- #
# Report (legacy Layout or PBIR)
# --------------------------------------------------------------------------- #


def _fields_from_query(obj: Any, acc: set[str]) -> None:
    """Collect Entity.Property references from any (legacy or PBIR) query blob."""
    if isinstance(obj, dict):
        if "queryRef" in obj and isinstance(obj["queryRef"], str):
            acc.add(obj["queryRef"])
        if "Property" in obj and "Expression" in obj:
            src = obj["Expression"].get("SourceRef", {}) if isinstance(obj["Expression"], dict) else {}
            ent = src.get("Entity") or src.get("Source")
            if ent:
                acc.add(f"{ent}.{obj['Property']}")
        for v in obj.values():
            _fields_from_query(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _fields_from_query(v, acc)


def _title_of(vis: dict[str, Any]) -> str:
    for key in ("vcObjects", "visualContainerObjects"):
        title = vis.get(key, {}).get("title", [])
        for t in title:
            val = t.get("properties", {}).get("text", {}).get("expr", {}).get("Literal", {}).get("Value")
            if val:
                return str(val).strip("'")
    return ""


def _read_report(z: zipfile.ZipFile, ex: Extraction) -> None:
    names = z.namelist()
    if "Report/Layout" in names:
        ex.report_format = "PBIR-Legacy (Report/Layout)"
        layout = json.loads(_decode(z.read("Report/Layout")))
        for sec in sorted(layout.get("sections", []), key=lambda s: s.get("ordinal", 0)):
            visuals = []
            for vc in sec.get("visualContainers", []):
                try:
                    cfg = json.loads(vc.get("config", "{}"))
                except json.JSONDecodeError:
                    cfg = {}
                sv = cfg.get("singleVisual", {})
                fields: set[str] = set()
                _fields_from_query(sv.get("prototypeQuery", {}), fields)
                _fields_from_query(sv.get("projections", {}), fields)
                visuals.append({
                    "type": sv.get("visualType", "group" if "singleVisualGroup" in cfg else "?"),
                    "title": _title_of(sv),
                    "fields": sorted(fields),
                    "x": vc.get("x"), "y": vc.get("y"), "w": vc.get("width"), "h": vc.get("height"),
                })
            ex.pages.append({
                "name": sec.get("displayName", sec.get("name")),
                "width": sec.get("width"), "height": sec.get("height"),
                "hidden": "\"visibility\":1" in sec.get("config", ""),
                "visuals": visuals,
            })
        return
    pages_dir = "Report/definition/pages/"
    page_files = [n for n in names if n.startswith(pages_dir) and n.endswith("/page.json")]
    if page_files:
        ex.report_format = "PBIR (Report/definition)"
        order: list[str] = []
        if f"{pages_dir}pages.json" in names:
            order = json.loads(_decode(z.read(f"{pages_dir}pages.json"))).get("pageOrder", [])
        by_id: dict[str, dict[str, Any]] = {}
        for pf in page_files:
            page = json.loads(_decode(z.read(pf)))
            pid = pf[len(pages_dir):].split("/")[0]
            visuals = []
            for vf in [n for n in names if n.startswith(f"{pages_dir}{pid}/visuals/") and n.endswith("visual.json")]:
                v = json.loads(_decode(z.read(vf)))
                vis = v.get("visual", {})
                fields: set[str] = set()
                _fields_from_query(vis.get("query", {}), fields)
                pos = v.get("position", {})
                visuals.append({"type": vis.get("visualType", "group" if "visualGroup" in v else "?"),
                                "title": _title_of(vis), "fields": sorted(fields),
                                "x": pos.get("x"), "y": pos.get("y"),
                                "w": pos.get("width"), "h": pos.get("height")})
            by_id[pid] = {"name": page.get("displayName", pid), "width": page.get("width"),
                          "height": page.get("height"), "hidden": page.get("visibility") == "HiddenInViewMode",
                          "visuals": visuals}
        for pid in order + [p for p in by_id if p not in order]:
            if pid in by_id:
                ex.pages.append(by_id[pid])


# --------------------------------------------------------------------------- #
# Analysis (anti-patterns + unused columns)
# --------------------------------------------------------------------------- #

REF_RE = re.compile(r"(?:'((?:[^']|'')+)'|([A-Za-z_][\w]*))?\[([^\]]+)\]")


def _analyse(ex: Extraction) -> dict[str, Any]:
    used: set[tuple[str, str]] = set()
    bare_refs: set[str] = set()
    measure_names = {m["name"] for t in ex.tables for m in t["measures"]}
    for t in ex.tables:
        texts = [m["expression"] for m in t["measures"]] + [c["expression"] for c in t["columns"]]
        for txt in texts:
            for q, plain, col in REF_RE.findall(txt):
                table = (q.replace("''", "'") if q else plain) or ""
                if table:
                    used.add((table, col))
                else:
                    bare_refs.add(col)
        for c in t["columns"]:
            if c.get("sortByColumn"):
                used.add((t["name"], c["sortByColumn"]))
    for r in ex.relationships:
        used.add((r["fromTable"], r["fromColumn"]))
        used.add((r["toTable"], r["toColumn"]))
    for p in ex.pages:
        for v in p["visuals"]:
            for f in v["fields"]:
                if "." in f:
                    ent, _, prop = f.partition(".")
                    used.add((ent, prop))
    for role in ex.roles:
        for f in role["filters"]:
            for q, plain, col in REF_RE.findall(f["filter"]):
                used.add(((q.replace("''", "'") if q else plain) or f["table"], col))

    fact_tables = {r["fromTable"] for r in ex.relationships}
    dim_tables = {r["toTable"] for r in ex.relationships} - fact_tables
    unused: dict[str, list[str]] = defaultdict(list)
    per_table: list[dict[str, Any]] = []
    for t in ex.tables:
        name = t["name"]
        if AUTO_DATE.match(name):
            continue
        steps = 0
        heavy: list[str] = []
        for p in t["partitions"]:
            if p["type"] == "m":
                steps = max(steps, len(re.findall(r"^\s*(?:#\"[^\"]+\"|[A-Za-z_][\w.]*)\s*=", p["expression"], re.M)))
                heavy += [fn for fn in PQ_HEAVY if fn + "(" in p["expression"]]
                if EMBEDDED_DATA.search(p["expression"]):
                    ex.findings.append(f"Tabela '{name}' tem dados embutidos (Inserir Dados). Leve para a fonte.")
        calc_cols = [c["name"] for c in t["columns"] if c["type"] == "calculated"]
        for c in t["columns"]:
            if c["type"] == "rowNumber":
                continue
            if (name, c["name"]) not in used and c["name"] not in bare_refs:
                unused[name].append(c["name"])
        role = "fato" if name in fact_tables else "dimensão" if name in dim_tables else (
            "calculada" if any(p["type"] == "calculated" for p in t["partitions"]) else "isolada")
        per_table.append({"table": name, "role": role, "columns": len(t["columns"]),
                          "measures": len(t["measures"]), "pq_steps": steps,
                          "pq_heavy_functions": sorted(set(heavy)), "calculated_columns": calc_cols,
                          "unused_columns": unused.get(name, [])})
        if steps > 2:
            ex.findings.append(f"Tabela '{name}': {steps} etapas de Power Query — mover lógica para SQL/view.")
        if calc_cols and name in fact_tables:
            ex.findings.append(f"Fato '{name}' tem colunas calculadas ({', '.join(calc_cols)}) — mover para a fonte.")
    if any(AUTO_DATE.match(t["name"]) for t in ex.tables):
        ex.findings.append("Auto date/time LIGADO (tabelas LocalDateTable_*). Desligar e usar dimensão Calendário.")
    for r in ex.relationships:
        if r["crossFilteringBehavior"] == "bothDirections":
            ex.findings.append(f"Relacionamento bidirecional {r['fromTable']} ↔ {r['toTable']} — revisar.")
        if r["fromCardinality"] == "many" and r["toCardinality"] == "many":
            ex.findings.append(f"Relacionamento muitos-para-muitos {r['fromTable']} ↔ {r['toTable']} — revisar grão.")
    no_desc = [m["name"] for t in ex.tables for m in t["measures"] if not m["description"]]
    if no_desc:
        ex.findings.append(f"{len(no_desc)} de {len(measure_names)} medidas sem descrição.")
    implicit = sum(1 for p in ex.pages for v in p["visuals"]
                   for f in v["fields"] if "(" in f and f.split("(")[0] in {"Sum", "Count", "Avg", "Min", "Max"})
    if implicit:
        ex.findings.append(f"{implicit} usos de medidas implícitas em visuais — criar medidas explícitas.")
    return {"tables": per_table, "unused_columns": dict(unused),
            "fact_tables": sorted(fact_tables), "dimension_tables": sorted(dim_tables)}


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def extract(path: Path, do_redact: bool = True) -> tuple[Extraction, dict[str, Any]]:
    if not zipfile.is_zipfile(path):
        raise SystemExit(f"ERRO: {path.name} não é um .pbit/.pbix válido (ZIP).")
    ex = Extraction(source=path.name)
    with zipfile.ZipFile(path) as z:
        _read_model(z, ex, do_redact)
        _read_report(z, ex)
    analysis = _analyse(ex)
    return ex, analysis


def _md_table(rows: list[list[str]], header: list[str]) -> str:
    def esc(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def write_reports(ex: Extraction, analysis: dict[str, Any], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    real_tables = [t for t in ex.tables if not AUTO_DATE.match(t["name"])]
    n_measures = sum(len(t["measures"]) for t in real_tables)
    n_visuals = sum(len(p["visuals"]) for p in ex.pages)
    unused_total = sum(len(v) for v in analysis["unused_columns"].values())

    summary = [
        f"# Extração do legado — `{ex.source}`",
        "",
        "> Gerado por `pbw extrair`. Leitura somente de metadados; nenhum dado foi lido.",
        "> Hosts e IPs foram mascarados (`<redacted>`) por padrão.",
        "",
        "## Visão geral",
        "",
        _md_table([[len(real_tables), n_measures, len(ex.relationships), len(ex.pages), n_visuals,
                    unused_total, ex.report_format]],
                  ["Tabelas", "Medidas", "Relacionamentos", "Páginas", "Visuais", "Colunas sem uso", "Formato"]),
        "",
        "## Diagnóstico (o que a refatoração deve corrigir)",
        "",
        *([f"- {f}" for f in ex.findings] or ["- Nenhum problema estrutural detectado automaticamente."]),
        "",
        "## Tabelas",
        "",
        _md_table([[t["table"], t["role"], t["columns"], len(t["unused_columns"]), t["measures"], t["pq_steps"],
                    ", ".join(t["pq_heavy_functions"]) or "—"] for t in analysis["tables"]],
                  ["Tabela", "Papel", "Colunas", "Sem uso", "Medidas", "Etapas PQ", "Funções PQ pesadas"]),
        "",
        "## Colunas candidatas a NÃO importar (sem uso em medidas, visuais, relacionamentos ou RLS)",
        "",
    ]
    for t, cols in analysis["unused_columns"].items():
        summary.append(f"- **{t}**: {', '.join(cols)}")
    summary += ["", "Arquivos: `model.md`, `measures.md`, `power-query.md`, `report.md`, `extraction.json`.", ""]
    files.append(out / "summary.md")
    write_text(files[-1], "\n".join(summary))

    # model.md with mermaid ER
    er = ["```mermaid", "erDiagram"]
    def ent(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", name)

    for r in ex.relationships:
        card = "||--o{" if r["toCardinality"] == "one" else "}o--o{"
        er.append(f'    {ent(r["toTable"])} {card} {ent(r["fromTable"])} : "{r["toColumn"]}"')
    er.append("```")
    model = ["# Modelo legado", "", *er, "", "## Relacionamentos", "",
             _md_table([[r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"],
                         f'{r["fromCardinality"]}:{r["toCardinality"]}', r["crossFilteringBehavior"],
                         "sim" if r["isActive"] else "não"] for r in ex.relationships],
                       ["De (tabela)", "Coluna", "Para (tabela)", "Coluna", "Cardinalidade", "Filtro", "Ativo"]),
             "", "## Colunas por tabela", ""]
    for t in real_tables:
        model += [f"### {t['name']}", "", _md_table(
            [[c["name"], c["dataType"], c["type"], "sim" if c["isHidden"] else "", c["expression"][:120]]
             for c in t["columns"]], ["Coluna", "Tipo", "Origem", "Oculta", "Expressão (se calculada)"]), ""]
    if ex.roles:
        model += ["## RLS", ""] + [f"- **{r['name']}**: " + "; ".join(
            f"`{f['table']}` → `{f['filter']}`" for f in r["filters"]) for r in ex.roles]
    files.append(out / "model.md")
    write_text(files[-1], "\n".join(model) + "\n")

    meas = ["# Medidas do legado", ""]
    for t in real_tables:
        for m in t["measures"]:
            meas += [f"## [{m['name']}]  ·  _{t['name']}_", "",
                     f"- Pasta: `{m['displayFolder'] or '—'}` · Formato: `{m['formatString'] or '—'}`",
                     f"- Descrição: {m['description'] or '—'}", "", "```dax", m["expression"].strip(), "```", ""]
    files.append(out / "measures.md")
    write_text(files[-1], "\n".join(meas))

    pq = ["# Power Query do legado", "", "> Objetivo da refatoração: zero etapas aqui. Tudo vira SQL na fonte.", ""]
    for e in ex.expressions:
        pq += [f"## Expressão compartilhada: {e['name']}", "", "```powerquery", e["expression"].strip(), "```", ""]
    for t in real_tables:
        for p in t["partitions"]:
            lang = "powerquery" if p["type"] == "m" else "dax"
            pq += [f"## {t['name']}  ·  {p['type']} / {p['mode']}", "", f"```{lang}", p["expression"].strip(), "```", ""]
    files.append(out / "power-query.md")
    write_text(files[-1], "\n".join(pq))

    rep = ["# Relatório legado", "", f"Formato: {ex.report_format}", ""]
    for p in ex.pages:
        rep += [f"## {p['name']}{' (oculta)' if p['hidden'] else ''}  ·  {p['width']}×{p['height']}", "",
                _md_table([[v["type"], v["title"] or "—", ", ".join(v["fields"]) or "—"] for v in p["visuals"]],
                          ["Visual", "Título", "Campos"]), ""]
    files.append(out / "report.md")
    write_text(files[-1], "\n".join(rep))

    files.append(out / "extraction.json")
    write_json(files[-1], {"source": ex.source, "culture": ex.culture, "report_format": ex.report_format,
                           "findings": ex.findings, "analysis": analysis, "tables": ex.tables,
                           "relationships": ex.relationships, "expressions": ex.expressions,
                           "roles": ex.roles, "pages": ex.pages})
    return files


def has_embedded_data(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            if "DataModelSchema" not in z.namelist():
                return False
            return bool(EMBEDDED_DATA.search(_decode(z.read("DataModelSchema"))))
    except (zipfile.BadZipFile, OSError):
        return False


def text_payload(path: Path) -> str:
    """Concatenate the textual metadata of a pbit (for secret scanning)."""
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n in ("DataModelSchema", "Report/Layout", "Connections", "DiagramLayout") or n.endswith(".json"):
                    chunks.append(_decode(z.read(n)))
    except (zipfile.BadZipFile, OSError):
        pass
    return "\n".join(chunks)
