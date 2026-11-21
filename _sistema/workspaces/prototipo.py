"""`pbw prototipo` — turns trabalho-da-ia/desenho.md (section "Páginas") into PBIR pages you can open.

Every dashboard always has an openable .pbip. Before any data exists, its pages are a *prototype*:
grey boxes laid out on the 8-px grid, one per visual planned in the design, so the analyst sees the
layout in Power BI Desktop at Gate 1. Cards whose measure already exists are real, bound cards.

A prototype page is any page with a visual containing the text PROTÓTIPO. Running the command again
replaces only prototype pages; pages built for real (no marker) and the documentation page are kept.

Format read from desenho.md:

    ## 3. Páginas
    ### Visão Geral
    **Pergunta:** quanto já venceu e com quem?
    | Zona | Visual | Campos |
    |---|---|---|
    | KPIs | Cartão | [Saldo em Aberto] |
    | Explicação | Colunas | Faixa Atraso × [Valor Vencido] |
    | Filtro | Segmentação | Dim Filial[Regional] |
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import pbip, shell, tmdl
from .layout import DESIGN, PROTOTYPE_MARK, company_of, powerbi_dir
from .util import stable_id, strip_accents, write_json

M, G = 24, 16          # outer margin, gutter (8-px grid)


@dataclass
class Item:
    zone: str          # header | filters | kpis | main | detail
    visual: str
    fields: str


@dataclass
class PageSpec:
    name: str
    question: str = ""
    items: list[Item] = field(default_factory=list)


def _norm(s: str) -> str:
    return strip_accents(s).lower().strip()


def _zone(z: str, visual: str) -> str:
    z, v = _norm(z), _norm(visual)
    if any(k in z or k in v for k in ("filtro", "segmenta", "slicer")):
        return "filters"
    if any(k in z for k in ("capa", "banner", "boas-vindas", "hero")):
        return "hero"
    if any(k in z for k in ("subtitulo", "titulo", "cabecalho", "header")):
        return "header"
    if any(k in z for k in ("kpi", "indicador")) or (v.startswith("cart") and "kpi" in z):
        return "kpis"
    if any(k in z for k in ("detalhe", "detail")) or any(k in v for k in ("tabela", "matriz", "table")):
        return "detail"
    if v.startswith("cart") and not z:
        return "kpis"
    return "main"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_design(text: str, doc_page: str = "Documentação") -> list[PageSpec]:
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if re.match(r"^##\s+(?:\d+\.\s*)?(P[áa]ginas|Wireframe)\b", ln, re.I)), None)
    if start is None:
        return []
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^##\s", lines[i])), len(lines))
    pages: list[PageSpec] = []
    cur: PageSpec | None = None
    header: list[str] | None = None
    for ln in lines[start + 1:end]:
        h = re.match(r"^###\s+(.+)$", ln)
        if h:
            name = h.group(1).strip()
            name = re.sub(r"^P[áa]gina\s*\d*\s*[—:\-–]\s*", "", name, flags=re.I).strip()
            name = re.sub(r"\s*\(.*obrigat.*\)\s*$", "", name, flags=re.I).strip()
            cur = None if _norm(name) == _norm(doc_page) else PageSpec(name)
            if cur:
                pages.append(cur)
            header = None
            continue
        if cur is None:
            continue
        q = re.match(r"^\**\s*Pergunta\s*:?\**\s*:?\s*(.+)$", ln.strip(), re.I)
        if q and not cur.question:
            cur.question = q.group(1).strip().strip("*").strip()
            continue
        if ln.strip().startswith("|"):
            cells = _cells(ln)
            if header is None:
                header = [_norm(c) for c in cells]
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            row = dict(zip(header, cells))
            zone = next((v for k, v in row.items() if k.startswith("zona")), "")
            visual = next((v for k, v in row.items() if k.startswith("visual")), "")
            fields_ = next((v for k, v in row.items() if k.startswith(("campos", "mostra", "o que"))), "")
            if visual or fields_:
                cur.items.append(Item(_zone(zone, visual), visual or "Visual", fields_ or zone))
        else:
            header = None
    return [p for p in pages if p.name]


# --------------------------------------------------------------------------- visuals

def _container_box() -> dict:
    return {
        "background": [{"properties": {"show": pbip.lit("true"),
                                       "color": {"solid": {"color": pbip.text_lit("#F3F4F6")}},
                                       "transparency": pbip.lit("0D")}}],
        "border": [{"properties": {"show": pbip.lit("true"),
                                   "color": {"solid": {"color": pbip.text_lit("#C9CED6")}},
                                   "radius": pbip.lit("8D")}}],
    }


def placeholder(kind: str, text: str, muted: str) -> dict:
    v = pbip.textbox(text, 12, False)
    runs = [{"textRuns": [{"value": kind.upper(), "textStyle": {"fontSize": "9pt", "fontWeight": "bold",
                                                                 "color": muted}}]},
            {"textRuns": [{"value": text, "textStyle": {"fontSize": "12pt"}}]}]
    v["objects"]["general"][0]["properties"]["paragraphs"] = runs
    v["visualContainerObjects"] = _container_box()
    return v


def _measure_of(fields_: str, measures: set[str]) -> str | None:
    names = re.findall(r"\[([^\]]+)\]", fields_) or [fields_.strip()]
    if len(names) == 1 and names[0] in measures:
        return names[0]
    return None


def _row(items: list, y: int, h: int, x0: int, x1: int) -> list[tuple[object, tuple[int, int, int, int]]]:
    n = len(items)
    if not n:
        return []
    w = (x1 - x0 - (n - 1) * G) // n
    return [(it, (x0 + i * (w + G), y, w, h)) for i, it in enumerate(items)]


def layout(spec: PageSpec, width: int, height: int) -> list[tuple[Item | None, tuple[int, int, int, int], str]]:
    """Return (item, position, slot) inside the app shell content area.

    slot: title | question | filter | hero | kpi | main | detail | banner | updated
    """
    x0, y0, x1, y1 = shell.content_box(width, height)
    out: list[tuple[Item | None, tuple[int, int, int, int], str]] = []
    by = {z: [i for i in spec.items if i.zone == z] for z in ("hero", "header", "filters", "kpis", "main", "detail")}
    right = x1 - 184
    out.append((None, (right, y0, 184, 48), "updated"))
    for f in by["filters"][:2]:
        right -= G + 168
        out.append((f, (right, y0, 168, 48), "filter"))
    out.append((None, (x0, y0, right - x0 - G, 30), "title"))
    head = by["header"][0] if by["header"] else None
    out.append((head, (x0, y0 + 30, right - x0 - G, 22), "question"))
    y = y0 + 64
    if by["hero"]:
        out.append((by["hero"][0], (x0, y, x1 - x0, 112), "hero"))
        y += 112 + G
    if by["kpis"]:
        out += [(it, pos, "kpi") for it, pos in _row(by["kpis"][:6], y, 88, x0, x1)]
        y += 88 + G
    bottom = y1 - 12
    main = by["main"] + by["filters"][2:] + by["header"][1:] + by["hero"][1:]
    detail = by["detail"]
    rows_main = [main[i:i + 3] for i in range(0, len(main), 3)] or []
    n_rows = len(rows_main) + (1 if detail else 0)
    if n_rows:
        h = (bottom - y - (n_rows - 1) * G) // n_rows
        h -= h % 8
        for r in rows_main:
            out += [(it, pos, "main") for it, pos in _row(r, y, h, x0, x1)]
            y += h + G
        if detail:
            out += [(it, pos, "detail") for it, pos in _row(detail[:3], y, bottom - y, x0, x1)]
    out.append((None, (x0, height - 18, 640, 14), "banner"))
    return out


# --------------------------------------------------------------------------- write

def _report_dir(dash: Path) -> Path:
    reps = sorted(powerbi_dir(dash).glob("*.Report"))
    if not reps:
        raise SystemExit(f"ERRO: nenhum *.Report em {dash.name}/2-power-bi/. Rode `pbw diagnostico`.")
    return reps[0]


def is_prototype_page(page_dir: Path) -> bool:
    return any(PROTOTYPE_MARK in vj.read_text(encoding="utf-8", errors="ignore")
               for vj in page_dir.glob("visuals/*/visual.json"))


def build(root: Path, dash: Path, cfg: dict) -> tuple[list[str], list[str]]:
    """(re)write prototype pages. Returns (written page names, skipped page names)."""
    rp = cfg.get("report", {})
    width, height = int(rp.get("width", 1280)), int(rp.get("height", 720))
    doc_page = rp.get("documentation_page", "Documentação")
    design = dash / DESIGN
    specs = parse_design(design.read_text(encoding="utf-8"), doc_page) if design.exists() else []
    if not specs:
        specs = [PageSpec("Visão Geral", "Que pergunta esta página responde? (a IA preenche no desenho)",
                          [Item("main", "Rascunho", "Escreva o que você quer em 1-seu-pedido/PEDIDO.md; a IA desenha "
                                                    "esta página e roda `pbw prototipo`.")])]
    measures: set[str] = set()
    definition = tmdl.find_definition(powerbi_dir(dash))
    if definition:
        measures = {m.name for _, m in tmdl.parse_model(definition).measures}
    from . import brand as brand_mod
    from .util import read_toml
    company = company_of(root, dash, cfg)
    try:
        bdata = brand_mod.load_brand(root, brand_mod.resolve(root, company))
    except (SystemExit, OSError, ValueError):
        bdata = {}
    colors = shell.palette(bdata)
    text_color, muted = colors["text"], colors["muted"]
    try:
        ficha = read_toml(dash / "trabalho-da-ia" / "ficha.toml")
    except (OSError, ValueError):
        ficha = {}
    report_title = ficha.get("dashboard", {}).get("name", dash.name)
    company_label = (shell.company_name(bdata, "") if bdata.get("brand", {}).get("slug") == company
                     else ficha.get("ownership", {}).get("company", company))

    report = _report_dir(dash)
    pname = report.name[: -len(".Report")]
    pages_dir = report / "definition" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    pj = pages_dir / "pages.json"
    order: list[str] = json.loads(pj.read_text(encoding="utf-8")).get("pageOrder", []) if pj.exists() else []
    existing: dict[str, tuple[str, bool]] = {}       # page id -> (displayName, prototype?)
    for page in sorted(pages_dir.glob("*/page.json")):
        name = json.loads(page.read_text(encoding="utf-8")).get("displayName", "")
        existing[page.parent.name] = (name, is_prototype_page(page.parent))
    for pid, (_, proto) in list(existing.items()):
        if proto:
            shutil.rmtree(pages_dir / pid)
            del existing[pid]
    real_names = {_norm(n): pid for pid, (n, _) in existing.items()}

    written, skipped, new_order = [], [], []
    for spec in specs:
        if _norm(spec.name) in real_names:
            skipped.append(spec.name)
            new_order.append(real_names[_norm(spec.name)])
            continue
        pid = stable_id(pname, "prototipo", spec.name)
        write_json(pages_dir / pid / "page.json", pbip.page_json(pid, spec.name, width, height))
        z = 1000
        for item, pos, slot in layout(spec, width, height):
            key = f"{slot}-{z}"
            if slot == "updated":
                if "Atualizado em" not in measures:
                    continue
                v = pbip.card_visual(pbip.MEASURE_TABLE, "Atualizado em")
            elif slot == "title":
                v = pbip.textbox(spec.name, 18, True, text_color)
            elif slot == "banner":
                v = pbip.textbox(f"{PROTOTYPE_MARK} · sem dados · gerado de {DESIGN} por `pbw prototipo`. "
                                 "A IA troca cada caixa cinza pelo visual real.", 8, False, muted)
            elif slot == "question" and item is None:
                v = pbip.textbox(spec.question or "Pergunta que esta página responde.", 11, False, muted)
            else:
                assert item is not None
                bound = _measure_of(item.fields, measures)
                if bound and _norm(item.visual).startswith("cart"):
                    v = pbip.card_visual(pbip.MEASURE_TABLE, bound)
                else:
                    v = placeholder(item.visual, item.fields, muted)
            write_json(pages_dir / pid / "visuals" / pbip.stable_id(pid, key) / "visual.json",
                       pbip.visual_container(pid, key, pos, z, v))
            z += 1
        written.append(spec.name)
        new_order.append(pid)
    for pid in order + sorted(existing):
        if pid in existing and pid not in new_order:
            new_order.append(pid)
    doc_ids = [pid for pid, (n, _) in existing.items() if _norm(n) == _norm(doc_page)]
    new_order = [p for p in new_order if p not in doc_ids] + doc_ids
    # app shell (sidebar + top bar) on every page this command manages: prototypes and the documentation page
    names = {}
    for pid in new_order:
        pjf = pages_dir / pid / "page.json"
        if pjf.exists():
            names[pid] = json.loads(pjf.read_text(encoding="utf-8")).get("displayName", "")
    all_names = [names[p] for p in new_order if p in names]
    for pid in new_order:
        if pid in names and (is_prototype_page(pages_dir / pid) or pid in doc_ids):
            shell.write(pages_dir / pid, pid, active=names[pid], pages=all_names, doc_page=doc_page,
                        report_title=report_title, company=company_label, colors=colors,
                        width=width, height=height)
    write_json(pj, {"$schema": pbip.S_PAGES, "pageOrder": new_order, "activePageName": new_order[0]})
    return written, skipped
