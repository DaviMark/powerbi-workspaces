"""`pbw documentar` (dicionário técnico por dashboard) e `pbw catalogo` (índice de tudo)."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path

from . import tmdl
from .layout import CATALOG_JSON, CATALOG_MD, DICTIONARY, MANIFEST, README, all_dashboards, dashboards_root, powerbi_dir
from .util import read_toml, rel, write_text

GENERATED = "<!-- GERADO por `pbw documentar`. Não edite à mão: altere o modelo e rode de novo. -->"


def _esc(v: str) -> str:
    return str(v).replace("|", "\\|").replace("\n", "<br>")


def _ent(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def dictionary(dash: Path) -> Path:
    definition = tmdl.find_definition(powerbi_dir(dash))
    if definition is None:
        raise SystemExit(f"ERRO: modelo semântico (*.SemanticModel) não encontrado em {dash.name}/2-power-bi/.")
    model = tmdl.parse_model(definition)
    out: list[str] = [GENERATED, "", "# Dicionário técnico do modelo", ""]
    src_tables = [t for t in model.tables if not t.name.startswith("_")]
    out += [f"Tabelas: **{len(src_tables)}** · Medidas: **{len(model.measures)}** · "
            f"Relacionamentos: **{len(model.relationships)}**", ""]

    if model.relationships:
        out += ["## Diagrama (star schema)", "", "```mermaid", "erDiagram"]
        for r in model.relationships:
            ft, fc, tt, tc = r.ends()
            card = "}o--o{" if (r.from_cardinality == "many" and r.to_cardinality == "many") else "||--o{"
            out.append(f'    {_ent(tt)} {card} {_ent(ft)} : "{tc}"')
        out += ["```", ""]

    out += ["## Tabelas", ""]
    for t in model.tables:
        kind = "calculada (DAX)" if t.is_calculated else "fonte"
        mode = next((p.mode for p in t.partitions if p.mode), "")
        out += [f"### {t.name}", "", f"_Tipo: {kind}{' · ' + mode if mode else ''}"
                f"{' · oculta' if t.is_hidden else ''}{' · tabela de datas' if t.data_category == 'Time' else ''}_",
                "", t.description or "> Sem descrição.", ""]
        if t.columns:
            out += ["| Coluna | Tipo | Oculta | Descrição |", "|---|---|---|---|"]
            for c in t.columns:
                out.append(f"| {_esc(c.name)}{' (chave)' if c.is_key else ''} | {c.data_type} | "
                           f"{'sim' if c.is_hidden else ''} | {_esc(c.description)} |")
            out.append("")

    out += ["## Medidas", ""]
    by_folder: dict[str, list[tuple[tmdl.Table, tmdl.Measure]]] = defaultdict(list)
    for t, m in model.measures:
        by_folder[m.display_folder or "(sem pasta)"].append((t, m))
    for folder in sorted(by_folder):
        out += [f"### {folder}", ""]
        for t, m in sorted(by_folder[folder], key=lambda x: x[1].name):
            out += [f"#### [{m.name}]", "", m.description or "> Sem descrição.", "",
                    f"Formato: `{m.format_string or '—'}` · Tabela: `{t.name}`", "",
                    "```dax", m.expression, "```", ""]

    out += ["## Cargas (Power Query)", "", "| Tabela | Modo | Etapas | Origem |", "|---|---|---|---|"]
    for t in model.tables:
        for p in t.partitions:
            if p.kind == "m":
                steps = len(re.findall(r"^\s*(?:#\"[^\"]+\"|[A-Za-z_][\w.]*)\s*=", p.source, re.M))
                origin = "SQL nativo" if "NativeQuery" in p.source or "Query =" in p.source else "navegação"
                out.append(f"| {_esc(t.name)} | {p.mode or 'import'} | {steps} | {origin} |")
    out.append("")
    target = dash / DICTIONARY
    write_text(target, "\n".join(out))
    return target


def catalog(root: Path) -> Path:
    cfg = read_toml(root / "workspaces.toml")
    base = dashboards_root(root, cfg)
    rows = []
    for dash in all_dashboards(root, cfg):
        d = read_toml(dash / MANIFEST)
        info = d.get("dashboard", {})
        own = d.get("ownership", {})
        data = d.get("data", {})
        sec = d.get("security", {})
        definition = tmdl.find_definition(powerbi_dir(dash))
        n_tables = n_measures = 0
        if definition:
            model = tmdl.parse_model(definition)
            n_tables = len([t for t in model.tables if not t.name.startswith("_") and not t.is_calculated])
            n_measures = len(model.measures)
        rows.append({
            "id": info.get("id", ""), "name": info.get("name", dash.name), "status": info.get("status", ""),
            "version": info.get("version", ""), "path": rel(dash, root),
            "company": own.get("company", ""), "area": own.get("area", ""), "subarea": own.get("subarea", ""),
            "owner": own.get("business_owner", ""), "connection": data.get("connection", ""),
            "classification": sec.get("classification", ""), "tables": n_tables, "measures": n_measures,
        })
    badge = {"draft": "rascunho", "development": "desenvolvimento", "review": "revisão",
             "production": "produção", "deprecated": "descontinuado"}
    lines = ["<!-- GERADO por `pbw catalogo`. Não edite à mão. -->", "", "# Catálogo de dashboards", "",
             f"Atualizado em {dt.date.today().isoformat()} · **{len(rows)}** dashboard(s)", ""]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[f"{r['company']} › {r['area']} › {r['subarea']}"].append(r)
    for g in sorted(groups):
        lines += [f"## {g}", "", "| Dashboard | Status | Versão | Dono | Conexão | Classificação | Tabelas | Medidas |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in groups[g]:
            lines.append(f"| [{r['name']}](../{r['path']}/{README}) | {badge.get(r['status'], r['status'])} | "
                         f"{r['version']} | {r['owner'] or '—'} | `{r['connection']}` | {r['classification']} | "
                         f"{r['tables']} | {r['measures']} |")
        lines.append("")
    out = base / CATALOG_MD
    write_text(out, "\n".join(lines))
    write_text(base / CATALOG_JSON, json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return out
