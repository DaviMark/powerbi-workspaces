"""`pbw validar` — governance rules. Errors block commits/CI; warnings guide quality."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from . import secrets as sec_mod
from . import tmdl
from .connectors import list_profiles
from .layout import (CUSTOM_VISUALS, DASHBOARD_ITEMS, DESIGN, FOLDER_README, CATALOG_JSON, CATALOG_MD,
                     HISTORY, MANIFEST, POWERBI, PROTOTYPE_MARK, README, REFACTOR, REQUEST_DIR, SQL, WORK,
                     dashboards_root, is_placeholder, powerbi_dir)
from .sqlsync import read_sql, select_aliases
from .util import is_slug, read_toml, rel

ERROR, WARN, INFO = "erro", "aviso", "info"

HARDCODED = re.compile(
    r'\b(?:Sql\.Databases?|SapHana\.Database|PostgreSQL\.Database|Oracle\.Database|MySQL\.Database|'
    r'Snowflake\.Databases|Databricks\.Catalogs|GoogleBigQuery\.Database\(\s*\[\s*BillingProject\s*=)\s*\(?\s*"')
PQ_HEAVY = re.compile(
    r"\bTable\.(?:AddColumn|TransformColumns|TransformColumnTypes|SelectRows|Group|NestedJoin|Join|"
    r"ExpandTableColumn|Pivot|Unpivot|UnpivotOtherColumns|ReplaceValue|Combine|Distinct|Sort|FillDown|"
    r"SplitColumn|DuplicateColumn|RenameColumns|RemoveColumns)\(")
REQUIRED_README_SECTIONS = ("## Como abrir", "## O que é", "## Cargas", "## Métricas", "## Como foi construído")
STATUSES = {"draft", "development", "review", "production", "deprecated"}
CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


@dataclass
class Issue:
    level: str
    rule: str
    path: str
    message: str


def _steps(m_source: str) -> int:
    return len(re.findall(r"^\s*(?:#\"[^\"]+\"|[A-Za-z_][\w.]*)\s*=", m_source, re.M))


def validate_dashboard(root: Path, dash: Path, cfg: dict) -> list[Issue]:
    gov = cfg.get("governance", {})
    rp = cfg.get("report", {})
    r = rel(dash, root)
    issues: list[Issue] = []

    def add(level: str, rule: str, msg: str, path: str = r) -> None:
        issues.append(Issue(level, rule, path, msg))

    mf = dash / MANIFEST
    if not mf.exists():
        add(ERROR, "PBW003", f"{MANIFEST} ausente.")
        return issues
    try:
        man = read_toml(mf)
    except Exception as exc:  # noqa: BLE001
        add(ERROR, "PBW003", f"{MANIFEST} inválida: {exc}")
        return issues
    info = man.get("dashboard", {})
    status = info.get("status", "")
    for key in ("id", "name", "status", "version"):
        if not info.get(key):
            add(ERROR, "PBW003", f"{MANIFEST}: [dashboard].{key} obrigatório.")
    if status and status not in STATUSES:
        add(ERROR, "PBW003", f"status '{status}' inválido ({', '.join(sorted(STATUSES))}).")
    expected_id = ".".join(dash.relative_to(dashboards_root(root, cfg)).parts)
    if info.get("id") and info["id"] != expected_id:
        if "nome-d" in info["id"]:
            spec = "/".join(dash.relative_to(dashboards_root(root, cfg)).parts)
            add(ERROR, "PBW003", f"pasta copiada do modelo e renomeada: rode `pbw novo \"{spec}\"` "
                                 "(ou peça à IA para criar o dashboard) — o seu pedido é mantido.")
        else:
            add(ERROR, "PBW003", f"id '{info['id']}' não bate com a pasta ('{expected_id}').")
    conn = man.get("data", {}).get("connection", "")
    profiles = list_profiles(root)
    if not conn:
        add(ERROR, "PBW004", "[data].connection não definido.")
    elif conn not in profiles:
        add(ERROR, "PBW004", f"perfil de conexão '{conn}' não existe em conexoes/.")
    elif conn.endswith(".example") and status in {"review", "production"}:
        add(ERROR, "PBW004", f"dashboard em '{status}' usando perfil de exemplo '{conn}'.")
    secu = man.get("security", {})
    cls = secu.get("classification", "")
    if cls not in CLASSIFICATIONS:
        add(ERROR, "PBW018", f"[security].classification deve ser um de {sorted(CLASSIFICATIONS)}.")
    if cls in {"confidential", "restricted"} and not secu.get("rls", False):
        add(WARN, "PBW018", f"classificação '{cls}' sem RLS — confirme e registre em {DESIGN} (Decisões).")
    if status in {"review", "production"} and not man.get("ownership", {}).get("business_owner"):
        add(ERROR, "PBW003", "dashboard em revisão/produção sem [ownership].business_owner.")

    # docs
    readme = dash / README
    if not readme.exists():
        add(ERROR, "PBW006", f"{README} ausente.")
    else:
        text = readme.read_text(encoding="utf-8")
        for s_ in REQUIRED_README_SECTIONS:
            if s_ not in text:
                add(WARN, "PBW006", f"{README} sem a seção '{s_}'.")
    for d in (REQUEST_DIR, POWERBI, WORK, SQL):
        if not (dash / d).is_dir():
            add(ERROR, "PBW001", f"pasta obrigatória '{d}/' ausente.")
    if not (dash / HISTORY).exists():
        add(WARN, "PBW006", f"{HISTORY} ausente.")
    if status in {"review", "production"}:
        p_ = dash / DESIGN
        if not p_.exists() or "TODO" in p_.read_text(encoding="utf-8"):
            add(WARN, "PBW006", f"{DESIGN} incompleto (ainda contém TODO).")

    # stray items: dashboard root has only the standard folders; 2-power-bi/ only the PBIP trio
    for p_ in dash.iterdir():
        if p_.name not in DASHBOARD_ITEMS:
            add(ERROR, "PBW001", f"item fora do padrão na pasta do dashboard: '{p_.name}' "
                                 "(seus arquivos vão em 1-seu-pedido/anexos/).")
    pbi = powerbi_dir(dash)
    pbips = sorted(pbi.glob("*.pbip")) if pbi.is_dir() else []
    pnames = {p_.stem for p_ in pbips}
    for p_ in (pbi.iterdir() if pbi.is_dir() else []):
        if p_.suffix == ".pbip" or p_.name in {".gitignore", ".gitkeep"}:
            continue
        if p_.is_dir() and p_.suffix in {".Report", ".SemanticModel"} and p_.stem in pnames:
            continue
        add(ERROR, "PBW001", f"item fora do padrão em {POWERBI}/: '{p_.name}'.")

    # PBIP must open in Power BI Desktop
    if len(pbips) != 1:
        add(ERROR, "PBW007", f"{POWERBI}/ deve ter exatamente 1 .pbip (encontrados {len(pbips)}). "
                             "Rode `pbw diagnostico`.")
        return issues
    pbip_file = pbips[0]
    try:
        artifacts = json.loads(pbip_file.read_text(encoding="utf-8")).get("artifacts", [])
        report_paths = [a["report"]["path"] for a in artifacts if "report" in a]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        add(ERROR, "PBW007", f"{pbip_file.name} inválido: {exc}")
        return issues
    if not report_paths or not (pbi / report_paths[0]).is_dir():
        add(ERROR, "PBW007", f"{pbip_file.name} aponta para um relatório que não existe ({report_paths}).")
        return issues
    report = pbi / report_paths[0]
    pbir = report / "definition.pbir"
    try:
        ref = json.loads(pbir.read_text(encoding="utf-8")).get("datasetReference", {})
    except (OSError, json.JSONDecodeError) as exc:
        add(ERROR, "PBW007", f"{rel(pbir, root)} ausente ou inválido: {exc}")
        return issues
    by_path = (ref.get("byPath") or {}).get("path")
    if by_path and not (Path(os.path.normpath(report / by_path)) / "definition.pbism").exists():
        add(ERROR, "PBW007", f"o relatório aponta para '{by_path}', mas lá não há definition.pbism.")
    for j in [p_ for p_ in (report / "definition").rglob("*.json")] + [report / ".platform"]:
        if j.exists():
            try:
                json.loads(j.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                add(ERROR, "PBW007", f"JSON inválido (o Power BI não abre): {rel(j, root)}")
    pages_json = report / "definition" / "pages" / "pages.json"
    if pages_json.exists():
        try:
            order = json.loads(pages_json.read_text(encoding="utf-8")).get("pageOrder", [])
        except json.JSONDecodeError:
            order = []
        missing = [pid for pid in order if not (report / "definition" / "pages" / pid / "page.json").exists()]
        if missing:
            add(ERROR, "PBW007", f"pages.json cita páginas que não existem: {', '.join(missing)}")
    proto = [pj for pj in (report / "definition" / "pages").glob("*/page.json")
             if any(PROTOTYPE_MARK in v.read_text(encoding="utf-8", errors="ignore")
                    for v in pj.parent.glob("visuals/*/visual.json"))]
    if proto:
        lvl = ERROR if status in {"review", "production"} else INFO
        add(lvl, "PBW024", f"{len(proto)} página(s) ainda em protótipo — troque pelos visuais reais antes da revisão.")
    definition = tmdl.find_definition(pbi)
    if definition is None:
        add(ERROR, "PBW007", "*.SemanticModel/definition (TMDL) não encontrado.")
        return issues
    try:
        model = tmdl.parse_model(definition)
    except Exception as exc:  # noqa: BLE001
        add(ERROR, "PBW007", f"falha ao ler TMDL: {exc}")
        return issues

    if model.annotations.get("__PBI_TimeIntelligenceEnabled", "0") != "0":
        add(WARN, "PBW015", "Auto date/time ligado. Desligue (model.tmdl) e use a tabela Calendario.")
    source_tables = [t for t in model.tables if not t.is_calculated]
    max_tables = int(gov.get("max_tables", 12))
    if len(source_tables) > max_tables:
        add(WARN, "PBW013", f"{len(source_tables)} tabelas de fonte (limite {max_tables}). Importe o mínimo.")
    max_steps = int(gov.get("max_pq_steps", 1))
    sql_dir = dash / SQL
    sql_tables = {}
    for f in sorted(sql_dir.glob("*.sql")):
        sf = read_sql(f, conn)
        sql_tables[sf.table] = sf
    fact_names = {tmdl.split_ref(rel_.from_column)[0] for rel_ in model.relationships}

    for t in model.tables:
        tpath = rel(t.file, root)
        if not t.description and not t.name.startswith("_"):
            add(WARN, "PBW010", f"tabela '{t.name}' sem descrição (///).", tpath)
        for p in t.partitions:
            if p.kind != "m":
                continue
            if HARDCODED.search(p.source):
                add(ERROR, "PBW008", f"'{t.name}': fonte com servidor/projeto fixo. Use parâmetros (pbw sincronizar-sql).", tpath)
            steps = _steps(p.source)
            if steps > max_steps:
                add(WARN, "PBW009", f"'{t.name}': {steps} etapas de Power Query (máx. {max_steps}). Leve para o SQL.", tpath)
            heavy = sorted(set(PQ_HEAVY.findall(p.source)))
            if heavy:
                add(WARN, "PBW009", f"'{t.name}': transformações no Power Query ({', '.join(heavy)}).", tpath)
            if t.name not in sql_tables:
                add(WARN, "PBW020", f"'{t.name}': sem sql/{t.name}.sql (fonte da verdade da carga).", tpath)
            if not t.columns:
                add(ERROR, "PBW023", f"'{t.name}': nenhuma coluna declarada no TMDL.", tpath)
            if t.name in sql_tables:
                aliases = select_aliases(sql_tables[t.name].sql)
                if aliases is not None and t.columns:
                    declared = {c.source_column or c.name for c in t.columns if not c.expression}
                    missing = [a for a in aliases if a not in declared]
                    extra = sorted(declared - set(aliases))
                    if missing:
                        add(WARN, "PBW020", f"'{t.name}': colunas do SELECT não declaradas no TMDL: {', '.join(missing)}", tpath)
                    if extra:
                        add(WARN, "PBW020", f"'{t.name}': colunas no TMDL que não estão no SELECT: {', '.join(extra)}", tpath)
        for c in t.columns:
            if c.expression and not t.is_calculated:
                lvl = ERROR if (t.name in fact_names and not gov.get("allow_calculated_columns_in_facts", False)) else WARN
                add(lvl, "PBW019", f"coluna calculada '{t.name}'[{c.name}] — prefira calcular na fonte.", tpath)
        for m in t.measures:
            if gov.get("require_measure_description", True) and not m.description:
                add(WARN, "PBW010", f"medida [{m.name}] sem descrição (///).", tpath)
            if gov.get("require_measure_format", True) and not m.format_string and "FORMAT" not in m.expression.upper():
                add(WARN, "PBW011", f"medida [{m.name}] sem formatString.", tpath)
            if gov.get("require_display_folder", True) and not m.display_folder:
                add(WARN, "PBW012", f"medida [{m.name}] sem displayFolder.", tpath)
    for sf_name in sql_tables:
        if not model.table(sf_name):
            add(WARN, "PBW020", f"sql/ para '{sf_name}' sem tabela no modelo. Rode pbw sincronizar-sql.")
    for rel_ in model.relationships:
        if rel_.cross_filter == "bothDirections" and not gov.get("allow_bidirectional", False):
            add(WARN, "PBW016", f"relacionamento bidirecional {rel_.from_column} ↔ {rel_.to_column}.")
        if rel_.from_cardinality == "many" and rel_.to_cardinality == "many":
            add(WARN, "PBW016", f"relacionamento muitos-para-muitos {rel_.from_column} ↔ {rel_.to_column}.")

    # Report: documentation page
    doc_page = rp.get("documentation_page", "Documentação")
    page_names = []
    for pj in report.glob("definition/pages/*/page.json"):
        try:
            page_names.append(json.loads(pj.read_text(encoding="utf-8")).get("displayName", ""))
        except json.JSONDecodeError:
            pass
    if (report / "report.json").exists() and not (report / "definition").is_dir():
        add(WARN, "PBW014", "relatório em formato PBIR-Legacy (report.json). Salve no formato PBIR.")
    elif doc_page not in page_names:
        add(ERROR, "PBW014", f"página obrigatória '{doc_page}' não encontrada no relatório.")

    # custom visuals must be justified
    if any((dash / CUSTOM_VISUALS).glob("*/pbiviz.json")):
        dec = dash / DESIGN
        if not dec.exists() or "pbiviz" not in dec.read_text(encoding="utf-8").lower():
            add(WARN, "PBW017", f"visual customizado sem decisão registrada ({DESIGN}: por que nenhum visual nativo atende).")
    return issues


def validate_tree(root: Path) -> list[Issue]:
    cfg = read_toml(root / "workspaces.toml")
    base = dashboards_root(root, cfg)
    issues: list[Issue] = []
    if not base.exists():
        return [Issue(ERROR, "PBW001", rel(base, root), "pasta de dashboards não existe.")]
    allowed_root = {FOLDER_README, CATALOG_MD, CATALOG_JSON, ".gitkeep"}
    for p in base.iterdir():
        if p.is_file() and p.name not in allowed_root:
            issues.append(Issue(ERROR, "PBW001", rel(p, root), "arquivo solto na raiz de dashboards/."))
    for level in range(1, 5):
        for p in base.glob("/".join(["*"] * level)):
            if is_placeholder(p.relative_to(base)):
                continue                       # the template dashboard (nome-da-empresa/…) is not validated
            if p.is_file():
                if level == 1 and p.name in allowed_root:
                    continue
                if level < 4 and p.name not in {FOLDER_README, ".gitkeep"}:
                    issues.append(Issue(ERROR, "PBW001", rel(p, root),
                                        "arquivo fora de lugar (só pastas até o nível do dashboard)."))
                continue
            if not is_slug(p.name):
                issues.append(Issue(ERROR, "PBW002", rel(p, root), "nome de pasta deve ser slug (minúsculas-com-hifens)."))
            if level == 4:
                issues.extend(validate_dashboard(root, p, cfg))
    for f in sec_mod.scan(root):
        issues.append(Issue(ERROR, f.rule, f"{f.path}:{f.line}" if f.line else f.path, f.message))
    return issues


def pending_inbox(root: Path) -> list[Issue]:
    inbox = root / REFACTOR
    return [Issue(INFO, "PBW030", rel(p, root), "aguardando refatoração (pbw refatorar).")
            for p in list(inbox.rglob("*.pbit")) + list(inbox.rglob("*.pbix"))]
