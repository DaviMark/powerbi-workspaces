"""PBIP skeleton generator (PBIR report + TMDL semantic model).

The JSON files follow the official Microsoft schemas (developer.microsoft.com/json-schemas/fabric).
Schema versions are intentionally conservative so that the project opens in any
Power BI Desktop released since mid-2024; Desktop upgrades them on save.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .connectors import Profile, expressions_tmdl
from .util import new_uuid, stable_id, tmdl_name, write_json, write_text

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
S_PBIP = f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json"
S_PLATFORM = f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json"
S_PBIR = f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json"
S_PBISM = f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json"
S_VERSION = f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json"
S_REPORT = f"{SCHEMA}/item/report/definition/report/1.1.0/schema.json"
S_PAGES = f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json"
S_PAGE = f"{SCHEMA}/item/report/definition/page/1.1.0/schema.json"
S_VISUAL = f"{SCHEMA}/item/report/definition/visualContainer/1.1.0/schema.json"


DOC_TABLE = "_Documentacao"
LOAD_TABLE = "_Cargas"
MEASURE_TABLE = "_Medidas"
DATE_TABLE = "Calendario"


# --------------------------------------------------------------------------- #
# PBIR visual helpers
# --------------------------------------------------------------------------- #


def lit(value: str) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": value}}}


def text_lit(text: str) -> dict[str, Any]:
    return lit("'" + text.replace("'", "''") + "'")


def field_column(entity: str, prop: str) -> dict[str, Any]:
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def field_measure(entity: str, prop: str) -> dict[str, Any]:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def projection(field: dict[str, Any], entity: str, prop: str) -> dict[str, Any]:
    return {"field": field, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def container_title(text: str) -> dict[str, Any]:
    return {
        "title": [{"properties": {"show": lit("true"), "text": text_lit(text)}}],
    }


def visual_container(page: str, key: str, pos: tuple[float, float, float, float], z: int,
                     visual: dict[str, Any]) -> dict[str, Any]:
    x, y, w, h = pos
    return {
        "$schema": S_VISUAL,
        "name": stable_id(page, key),
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": visual,
    }


def textbox(text: str, size: int = 14, bold: bool = False, color: str | None = None) -> dict[str, Any]:
    style: dict[str, Any] = {"fontSize": f"{size}pt"}
    if bold:
        style["fontWeight"] = "bold"
    if color:
        style["color"] = color
    return {
        "visualType": "textbox",
        "objects": {
            "general": [
                {"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": style}]}]}}
            ]
        },
        "drillFilterOtherVisuals": True,
    }


def table_visual(entity: str, columns: list[str], title: str) -> dict[str, Any]:
    return {
        "visualType": "tableEx",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [
                        projection(field_column(entity, c), entity, c) for c in columns
                    ]
                }
            }
        },
        "visualContainerObjects": container_title(title),
        "drillFilterOtherVisuals": True,
    }


def card_visual(entity: str, measure: str, title: str | None = None) -> dict[str, Any]:
    visual: dict[str, Any] = {
        "visualType": "card",
        "query": {
            "queryState": {
                "Values": {"projections": [projection(field_measure(entity, measure), entity, measure)]}
            }
        },
        "drillFilterOtherVisuals": True,
    }
    if title:
        visual["visualContainerObjects"] = container_title(title)
    return visual


def page_json(name: str, display: str, width: int, height: int) -> dict[str, Any]:
    return {
        "$schema": S_PAGE,
        "name": name,
        "displayName": display,
        "displayOption": "FitToPage",
        "height": height,
        "width": width,
    }


# --------------------------------------------------------------------------- #
# Semantic model (TMDL)
# --------------------------------------------------------------------------- #


def _indent(text: str, tabs: int) -> str:
    pad = "\t" * tabs
    return "\n".join(pad + line if line.strip() else "" for line in text.strip("\n").splitlines())


def model_tmdl(culture: str) -> str:
    return (
        "model Model\n"
        f"\tculture: {culture}\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n"
        f"\tsourceQueryCulture: {culture}\n"
        "\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n"
        "\t\treturnErrorValuesAsNull\n"
        "\n"
        "queryGroup Parametros\n"
        "\n"
        "\tannotation PBI_QueryGroupOrder = 0\n"
        "\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n"
        "\n"
        'annotation PBI_ProTooling = ["DevMode"]\n'
    )


def database_tmdl(name: str) -> str:
    return f"database {tmdl_name(name)}\n\tcompatibilityLevel: 1601\n\tcompatibilityMode: powerBI\n"


def measures_table_tmdl(utc_offset_hours: float) -> str:
    offset = f"{utc_offset_hours:g}"
    signed = f"{utc_offset_hours:+g}"
    return f"""/// Tabela de medidas do modelo. Nenhuma coluna visível: só medidas, organizadas em pastas.
/// A coluna oculta [Data Carga] registra o momento do último refresh (UTC{signed}h).
table {MEASURE_TABLE}

	/// Texto pronto para o cabeçalho das páginas: "Atualizado em dd/mm/aaaa hh:mm".
	measure 'Atualizado em' = "Atualizado em " & FORMAT ( MAX ( '{MEASURE_TABLE}'[Data Carga] ), "dd/mm/yyyy hh:nn" )
		displayFolder: _Sistema

	column 'Data Carga'
		dataType: dateTime
		isHidden
		formatString: General Date
		summarizeBy: none
		isNameInferred
		isDataTypeInferred
		sourceColumn: [Data Carga]

	partition {MEASURE_TABLE} = calculated
		mode: import
		source = ROW ( "Data Carga", UTCNOW () + ( {offset} / 24 ) )
"""


def date_table_tmdl() -> str:
    dax = """
VAR _inicio = DATE ( YEAR ( TODAY () ) - 3, 1, 1 )
VAR _fim = DATE ( YEAR ( TODAY () ), 12, 31 )
RETURN
    ADDCOLUMNS (
        SELECTCOLUMNS ( CALENDAR ( _inicio, _fim ), "Data", [Date] ),
        "Ano", YEAR ( [Data] ),
        "Mês Nº", MONTH ( [Data] ),
        "Mês", FORMAT ( [Data], "mmm" ),
        "Ano-Mês", FORMAT ( [Data], "yyyy-mm" ),
        "Trimestre", "T" & QUARTER ( [Data] ),
        "Dia da Semana Nº", WEEKDAY ( [Data], 2 ),
        "Dia da Semana", FORMAT ( [Data], "ddd" )
    )
"""
    cols = [
        ("Data", "dateTime", "dd/mm/yyyy", None, True),
        ("Ano", "int64", "0", None, False),
        ("Mês Nº", "int64", "0", None, False),
        ("Mês", "string", None, "Mês Nº", False),
        ("Ano-Mês", "string", None, None, False),
        ("Trimestre", "string", None, None, False),
        ("Dia da Semana Nº", "int64", "0", None, False),
        ("Dia da Semana", "string", None, "Dia da Semana Nº", False),
    ]
    lines = [
        "/// Dimensão calendário (DAX, sem Power Query). Ajuste _inicio/_fim ao período da fato.",
        "/// Marcada como tabela de datas. Auto date/time está desligado no modelo.",
        f"table {DATE_TABLE}",
        "\tdataCategory: Time",
        "",
    ]
    for name, dtype, fmt, sort_by, key in cols:
        lines.append(f"\tcolumn {tmdl_name(name)}")
        lines.append(f"\t\tdataType: {dtype}")
        if key:
            lines.append("\t\tisKey")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append("\t\tsummarizeBy: none")
        lines.append("\t\tisNameInferred")
        lines.append("\t\tisDataTypeInferred")
        lines.append(f"\t\tsourceColumn: [{name}]")
        if sort_by:
            lines.append(f"\t\tsortByColumn: {tmdl_name(sort_by)}")
        lines.append("")
    lines.append(f"\tpartition {DATE_TABLE} = calculated")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(_indent(dax, 4))
    return "\n".join(lines) + "\n"


def doc_table_tmdl() -> str:
    dax = """
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.MEASURES (), NOT [IsHidden] ),
    "Tabela", [Table],
    "Pasta", [DisplayFolder],
    "Medida", [Name],
    "Descrição", [Description],
    "Expressão DAX", [Expression],
    "Formato", [FormatString]
)
"""
    cols = ["Tabela", "Pasta", "Medida", "Descrição", "Expressão DAX", "Formato"]
    return _calc_table(
        DOC_TABLE,
        [
            "/// Catálogo vivo das métricas (INFO.VIEW.MEASURES). Recalculado a cada atualização.",
            "/// Alimenta a página 'Documentação'. Descrições vêm do /// de cada medida no TMDL.",
        ],
        [(c, "string") for c in cols],
        dax,
    )


def load_table_tmdl() -> str:
    dax = f"""
VAR _carga = MAX ( '{MEASURE_TABLE}'[Data Carga] )
RETURN
    ADDCOLUMNS (
        SELECTCOLUMNS (
            FILTER (
                INFO.VIEW.TABLES (),
                ISBLANK ( [Expression] ) && LEFT ( [Name], 1 ) <> "_"
            ),
            "Tabela", [Name],
            "Descrição", [Description],
            "Armazenamento", [StorageMode]
        ),
        "Última Carga", _carga
    )
"""
    return _calc_table(
        LOAD_TABLE,
        [
            "/// Cargas do modelo: tabelas vindas da fonte, modo de armazenamento e último refresh.",
            "/// A descrição de cada tabela (///) deve trazer: fonte, arquivo SQL, grão e conexão.",
        ],
        [("Tabela", "string"), ("Descrição", "string"), ("Armazenamento", "string"),
         ("Última Carga", "dateTime")],
        dax,
    )


def _calc_table(name: str, doc: list[str], cols: list[tuple[str, str]], dax: str) -> str:
    lines = [*doc, f"table {tmdl_name(name)}", ""]
    for col, dtype in cols:
        lines.append(f"\tcolumn {tmdl_name(col)}")
        lines.append(f"\t\tdataType: {dtype}")
        if dtype == "dateTime":
            lines.append("\t\tformatString: dd/mm/yyyy hh:nn")
        lines.append("\t\tsummarizeBy: none")
        lines.append("\t\tisNameInferred")
        lines.append("\t\tisDataTypeInferred")
        lines.append(f"\t\tsourceColumn: [{col}]")
        lines.append("")
    lines.append(f"\tpartition {tmdl_name(name)} = calculated")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(_indent(dax, 4))
    return "\n".join(lines) + "\n"


def source_table_tmdl(table: str, m_expression: str, description: list[str], mode: str = "import") -> str:
    """Stub for a source table. Columns must be declared by the developer/AI."""
    doc = [f"/// {d}" for d in description] or ["/// TODO: fonte, grão e conexão."]
    return "\n".join(
        [
            *doc,
            f"table {tmdl_name(table)}",
            "",
            f"\tpartition {tmdl_name(table)} = m",
            f"\t\tmode: {mode}",
            "\t\tsource =",
            "\t\t\t\tlet",
            f"\t\t\t\t    Fonte = {m_expression}",
            "\t\t\t\tin",
            "\t\t\t\t    Fonte",
            "",
        ]
    )


# --------------------------------------------------------------------------- #
# Whole-project writer
# --------------------------------------------------------------------------- #


def write_semantic_model(src: Path, pname: str, display: str, culture: str,
                         profiles: list[Profile], utc_offset: float) -> None:
    sm = src / f"{pname}.SemanticModel"
    write_json(sm / ".platform", {
        "$schema": S_PLATFORM,
        "metadata": {"type": "SemanticModel", "displayName": display},
        "config": {"version": "2.0", "logicalId": new_uuid()},
    })
    write_json(sm / "definition.pbism", {"$schema": S_PBISM, "version": "4.0", "settings": {}})
    d = sm / "definition"
    write_text(d / "database.tmdl", database_tmdl(pname))
    write_text(d / "model.tmdl", model_tmdl(culture))
    write_text(d / "expressions.tmdl", expressions_tmdl(profiles))
    write_text(d / "tables" / f"{MEASURE_TABLE}.tmdl", measures_table_tmdl(utc_offset))
    write_text(d / "tables" / f"{DATE_TABLE}.tmdl", date_table_tmdl())
    write_text(d / "tables" / f"{DOC_TABLE}.tmdl", doc_table_tmdl())
    write_text(d / "tables" / f"{LOAD_TABLE}.tmdl", load_table_tmdl())


def write_report(src: Path, pname: str, display: str, theme: dict[str, Any] | None,
                 theme_file: str | None, width: int, height: int, doc_page_name: str,
                 text_color: str = "#1B1F24", muted: str = "#5B6470") -> None:
    rp = src / f"{pname}.Report"
    write_json(rp / ".platform", {
        "$schema": S_PLATFORM,
        "metadata": {"type": "Report", "displayName": display},
        "config": {"version": "2.0", "logicalId": new_uuid()},
    })
    write_json(rp / "definition.pbir", {
        "$schema": S_PBIR,
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{pname}.SemanticModel"}},
    })
    d = rp / "definition"
    write_json(d / "version.json", {"$schema": S_VERSION, "version": "2.0.0"})

    # Only the company theme. No Microsoft base theme is shipped or referenced: the company theme
    # (identidade visual) defines colors, fonts and visual styles on its own.
    theme_collection: dict[str, Any] = {}
    packages: list[dict[str, Any]] = []
    if theme and theme_file:
        theme_collection["customTheme"] = {
            "name": theme_file, "reportVersionAtImport": "5.56", "type": "RegisteredResources"}
        packages.append({
            "name": "RegisteredResources", "type": "RegisteredResources",
            "items": [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}],
        })
        write_json(rp / "StaticResources" / "RegisteredResources" / theme_file, theme)

    write_json(d / "report.json", {
        "$schema": S_REPORT,
        "themeCollection": theme_collection,
        "layoutOptimization": "None",
        "objects": {"outspacePane": [{"properties": {"expanded": lit("false")}}]},
        "resourcePackages": packages,
        "settings": {
            "useStylableVisualContainerHeader": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    })

    # ---- pages --------------------------------------------------------------
    # Only the documentation page here; the other pages come from `pbw prototipo` (prototipo.py),
    # which also rewrites pages.json with the final order.
    docs = stable_id(pname, "page-docs")
    write_json(d / "pages" / "pages.json", {"$schema": S_PAGES, "pageOrder": [docs], "activePageName": docs})
    # Documentation page — inside the app shell content area (the shell itself is drawn by shell.py)
    from .shell import G, content_box
    write_json(d / "pages" / docs / "page.json", page_json(docs, doc_page_name, width, height))
    x0, y0, x1, y1 = content_box(width, height)
    top = y0 + 64
    body_h = y1 - top
    left_w = int((x1 - x0 - G) * 0.64)
    right_w = x1 - x0 - G - left_w
    dv = {
        "title": visual_container(docs, "title", (x0, y0, x1 - x0, 30), 1000,
                                  textbox(doc_page_name, 18, True, text_color)),
        "subtitle": visual_container(docs, "subtitle", (x0, y0 + 30, x1 - x0, 22), 1001, textbox(
            "Todas as métricas, regras de negócio e cargas deste relatório, geradas do próprio modelo.",
            10, False, muted)),
        "measures": visual_container(docs, "measures", (x0, top, left_w, body_h), 1002, table_visual(
            DOC_TABLE, ["Pasta", "Medida", "Descrição", "Expressão DAX"], "Métricas")),
        "loads": visual_container(docs, "loads", (x0 + left_w + G, top, right_w, body_h), 1003, table_visual(
            LOAD_TABLE, ["Tabela", "Descrição", "Armazenamento", "Última Carga"], "Cargas")),
    }
    for key, vc in dv.items():
        write_json(d / "pages" / docs / "visuals" / vc["name"] / "visual.json", vc)


def write_pbip(src: Path, pname: str) -> None:
    write_json(src / f"{pname}.pbip", {
        "$schema": S_PBIP,
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{pname}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })


def apply_theme(report: Path, theme: dict[str, Any], theme_file: str) -> None:
    """Register *theme* as the report's custom theme (replacing any previous one)."""
    rj = report / "definition" / "report.json"
    data = load_json(rj)
    reg = report / "StaticResources" / "RegisteredResources"
    tc = data.setdefault("themeCollection", {})
    old = (tc.get("customTheme") or {}).get("name")
    if old and old != theme_file and (reg / old).exists():
        (reg / old).unlink()
    write_json(reg / theme_file, theme)
    tc["customTheme"] = {"name": theme_file,
                         "reportVersionAtImport": (tc.get("customTheme") or {}).get("reportVersionAtImport", "5.56"),
                         "type": "RegisteredResources"}
    packages = data.setdefault("resourcePackages", [])
    regpk = next((pk for pk in packages if pk.get("type") == "RegisteredResources"), None)
    if regpk is None:
        regpk = {"name": "RegisteredResources", "type": "RegisteredResources", "items": []}
        packages.append(regpk)
    regpk["items"] = [i for i in regpk.get("items", []) if i.get("type") != "CustomTheme"] + [
        {"name": theme_file, "path": theme_file, "type": "CustomTheme"}]
    write_json(rj, data)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
