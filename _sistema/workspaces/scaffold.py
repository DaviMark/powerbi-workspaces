"""`pbw novo` e `pbw refatorar` — create governed dashboard folders (always with an openable .pbip)."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from typing import Any

from . import brand as brand_mod
from . import pbip, prototipo
from .layout import (ATTACHMENTS, LEGACY, MANIFEST, PLACEHOLDER_PREFIX, POWERBI, REFACTOR, REQUEST, REQUEST_DIR,
                     SQL, TEMPLATE, WORK, dashboards_root)
from .connectors import load_profile
from .util import (info, is_slug, ok, pascal, read_toml, rel, render, slugify, title_from_slug, warn,
                   write_text)

LEVELS = ("empresa", "area", "subarea", "dashboard")


def settings(root: Path) -> dict[str, Any]:
    return read_toml(root / "workspaces.toml")


def analytics_root(root: Path) -> Path:
    return dashboards_root(root, settings(root))


def parse_target(spec: str) -> tuple[list[str], list[str]]:
    """'Acme/Financeiro/Contas a Receber/Aging de Títulos' -> (slugs, display names)."""
    parts = [p.strip() for p in spec.replace("\\", "/").strip("/").split("/") if p.strip()]
    if len(parts) != 4:
        raise SystemExit(
            "ERRO: informe exatamente 4 níveis: <empresa>/<área>/<subárea>/<dashboard>\n"
            '  ex.: pbw novo "Acme/Financeiro/Contas a Receber/Aging de Títulos"'
        )
    slugs = [slugify(p) for p in parts]
    names = [title_from_slug(p) if is_slug(p) else p for p in parts]
    for s, original in zip(slugs, parts):
        if not s:
            raise SystemExit(f"ERRO: nome inválido: {original!r}")
    return slugs, names


def _template_values(root: Path, slugs: list[str], names: list[str], connection: str, brand: str,
                     origin: str) -> dict[str, str]:
    cfg = settings(root)
    prof = load_profile(root, connection)
    return {
        "id": ".".join(slugs),
        "name": names[3],
        "slug": slugs[3],
        "company": names[0], "company_slug": slugs[0],
        "area": names[1], "area_slug": slugs[1],
        "subarea": names[2], "subarea_slug": slugs[2],
        "pname": pascal(names[3]),
        "connection": connection,
        "connection_type": prof.connector.label,
        "brand": brand,
        "date": dt.date.today().isoformat(),
        "culture": cfg.get("project", {}).get("culture", "pt-BR"),
        "language": cfg.get("project", {}).get("language", "pt-BR"),
        "origin": origin,
        "doc_page": cfg.get("report", {}).get("documentation_page", "Documentação"),
    }


def create_dashboard(root: Path, spec: str, connection: str | None = None, brand: str | None = None,
                     origin: str = "new", force: bool = False) -> Path:
    cfg = settings(root)
    slugs, names = parse_target(spec)
    target = analytics_root(root).joinpath(*slugs)
    adopted = False
    if target.exists() and any(target.iterdir()) and not force:
        if not _is_copy_of_template(target, ".".join(slugs)):
            raise SystemExit(f"ERRO: {rel(target, root)} já existe. Use --force para sobrescrever o esqueleto.")
        # A folder copied from nome-da-empresa/… and renamed: rebuild everything except the analyst's request.
        for sub_ in (POWERBI, WORK):
            if (target / sub_).exists():
                shutil.rmtree(target / sub_)
        adopted = True

    connection = connection or cfg.get("defaults", {}).get("connection", "sqlserver.example")
    brand = brand or brand_mod.resolve(root, slugs[0])     # the company's identity, else the default one
    values = _template_values(root, slugs, names, connection, slugs[0], origin)

    # 1) LEIA-ME, 1-seu-pedido/, 3-entrega/ and trabalho-da-ia/ from the templates
    tpl_root = root / TEMPLATE
    for src in sorted(tpl_root.rglob("*")):
        if src.is_dir():
            continue
        dest = target / src.relative_to(tpl_root)
        if dest.name.endswith(".tpl"):
            dest = dest.with_name(dest.name[:-4])
        if dest.name == ".gitkeep" and dest.parent.exists() and any(dest.parent.iterdir()):
            continue
        content = src.read_text(encoding="utf-8")
        keep = adopted and REQUEST_DIR in dest.relative_to(target).parts      # never touch the analyst's request
        write_text(dest, render(content, values), overwrite=not keep and (force or adopted or not dest.exists()))
    if adopted and (target / REQUEST).exists():
        req = (target / REQUEST).read_text(encoding="utf-8")
        write_text(target / REQUEST, req.replace("# Pedido — Nome do Dashboard", f"# Pedido — {names[3]}", 1))

    # 2) PBIP at the top of the dashboard folder — always openable in Power BI Desktop
    rcfg = cfg.get("report", {})
    width, height = int(rcfg.get("width", 1280)), int(rcfg.get("height", 720))
    prof = load_profile(root, connection)
    theme = theme_file = None
    text_color, muted = "#1B1F24", "#5B6470"
    try:
        bdata = brand_mod.load_brand(root, brand)
        theme = brand_mod.build_theme(bdata)
        theme_file = brand_mod.theme_filename(brand)
        text_color = bdata.get("colors", {}).get("text", text_color)
        muted = bdata.get("colors", {}).get("text_muted", muted)
    except SystemExit as exc:
        warn(f"{exc} — relatório criado sem tema.")
    pname = values["pname"]
    pbi = target / POWERBI
    pbip.write_pbip(pbi, pname)
    pbip.write_semantic_model(pbi, pname, names[3], values["culture"], [prof],
                              float(cfg.get("project", {}).get("utc_offset_hours", -3)))
    pbip.write_report(pbi, pname, names[3], theme, theme_file, width, height, values["doc_page"],
                      text_color, muted)
    prototipo.build(root, target, cfg)
    (target / SQL).mkdir(parents=True, exist_ok=True)

    ok(f"Dashboard criado em {rel(target, root)}")
    info(f"Abra no Power BI Desktop: {rel(pbi / (pname + '.pbip'), root)}  (ou: pbw abrir {slugs[3]})")
    origin_brand = "da empresa" if brand == slugs[0] else f"padrão — crie identidade-visual/{slugs[0]}/ para usar a da empresa"
    info(f"Conexão: {connection} ({prof.connector.label}) · Identidade visual: {brand} ({origin_brand})")
    return target


def _is_copy_of_template(target: Path, expected_id: str) -> bool:
    """True when *target* holds a renamed copy of the nome-da-empresa/… template (or only a request)."""
    if not (target / REQUEST_DIR).is_dir():
        return False
    manifest = target / MANIFEST
    if not manifest.exists():
        return True
    try:
        dash_id = read_toml(manifest).get("dashboard", {}).get("id", "")
    except Exception:  # noqa: BLE001
        return True
    return dash_id != expected_id and PLACEHOLDER_PREFIX in dash_id


def refactor_inbox(root: Path) -> Path:
    return root / REFACTOR


def pending_refactors(root: Path) -> list[tuple[Path, str]]:
    """Return (pbit_path, spec) for every template waiting in refatorar/."""
    inbox = refactor_inbox(root)
    out: list[tuple[Path, str]] = []
    for f in sorted(list(inbox.rglob("*.pbit")) + list(inbox.rglob("*.pbix"))):
        parts = f.relative_to(inbox).parts
        if any(p.startswith(PLACEHOLDER_PREFIX) for p in parts[:-1]):
            warn(f"Ignorando {rel(f, root)}: renomeie as pastas nome-da-empresa/nome-da-area/… para os nomes reais.")
            continue
        if len(parts) == 5:          # empresa/area/subarea/dashboard/arquivo.pbit
            spec = "/".join(parts[:4])
        elif len(parts) == 4:        # empresa/area/subarea/Nome do Dashboard.pbit
            spec = "/".join([*parts[:3], f.stem])
        else:
            warn(f"Ignorando {rel(f, root)}: use refatorar/<empresa>/<área>/<subárea>/<dashboard>/arquivo.pbit")
            continue
        out.append((f, spec))
    return out


def run_refactor(root: Path, pbit_path: Path, spec: str, connection: str | None, brand: str | None,
                 force: bool = False) -> Path:
    from . import pbit as pbit_mod

    cfg = settings(root)
    target = create_dashboard(root, spec, connection, brand, origin="refactor", force=force)
    legacy = target / LEGACY
    legacy.mkdir(parents=True, exist_ok=True)
    redact = bool(cfg.get("security", {}).get("redact_extractions", True))
    ex, analysis = pbit_mod.extract(pbit_path, do_redact=redact)
    files = pbit_mod.write_reports(ex, analysis, legacy / "extracao")

    # Move the original and any notes next to it
    dest = legacy / f"original{pbit_path.suffix.lower()}"
    shutil.move(str(pbit_path), dest)
    attachments = target / ATTACHMENTS
    for extra in pbit_path.parent.glob("*"):
        suffix = extra.suffix.lower()
        if extra.is_file() and suffix in {".md", ".txt", ".png", ".jpg", ".jpeg", ".pdf", ".sql"}:
            folder = ("consultas-sql" if suffix == ".sql" else "imagens-e-rascunhos" if suffix in {".png", ".jpg", ".jpeg"}
                      else "documentos")
            name = f"legado-{extra.name}" if suffix in {".md", ".txt"} else extra.name
            (attachments / folder).mkdir(parents=True, exist_ok=True)
            shutil.move(str(extra), attachments / folder / name)
    # clean empty inbox folders
    p = pbit_path.parent
    inbox = refactor_inbox(root)
    while p != inbox and p.exists() and not any(p.iterdir()):
        p.rmdir()
        p = p.parent

    plan = render(REFACTOR_PLAN, {
        "source": pbit_path.name, "findings": "\n".join(f"- {f}" for f in ex.findings) or "- (nenhum)",
        "tables": str(len([t for t in analysis["tables"]])),
        "unused": str(sum(len(v) for v in analysis["unused_columns"].values())),
        "pages": str(len(ex.pages)),
    })
    write_text(legacy / "PLANO.md", plan)
    ok(f"Legado extraído: {len(files)} arquivos em {rel(legacy / 'extracao', root)}")
    if not cfg.get("security", {}).get("commit_legacy_pbit", False):
        info("O arquivo original fica em trabalho-da-ia/legado/ e é ignorado pelo Git (security.commit_legacy_pbit = false).")
    info("Próximo passo: peça à IA → \"refatore o dashboard em " + rel(target, root) + "\"")
    return target


REFACTOR_PLAN = """# Plano de refatoração — `{{source}}`

> Gerado por `pbw refatorar`. A IA segue o fluxo **REFATORAR** do `AGENTS.md`
> e a skill `powerbi-architect` (se instalada).

## O que foi encontrado

- Tabelas: {{tables}} · Páginas: {{pages}} · Colunas sem uso: {{unused}}

{{findings}}

## Checklist da refatoração

- [ ] Ler `extracao/summary.md`, `model.md`, `measures.md`, `power-query.md`, `report.md`
- [ ] Preencher `1-seu-pedido/PEDIDO.md` com as perguntas de negócio que o legado responde (inferidas + confirmadas)
- [ ] Escrever `trabalho-da-ia/desenho.md` (star schema sem colunas sem uso, métricas com paridade, páginas)
- [ ] Rodar `pbw prototipo` e pedir aprovação (**Gate 1**) — o analista abre o `.pbip` e vê as páginas
- [ ] Mover TODA a lógica de Power Query para `trabalho-da-ia/sql/*.sql` (uma consulta por tabela, 1 etapa no PQ)
- [ ] Reescrever medidas com descrição, formato e pasta (paridade numérica com o legado)
- [ ] Trocar as páginas de protótipo pelas páginas reais, com a identidade visual da empresa
- [ ] `trabalho-da-ia/conferencia.md`: comparar números do novo x legado (mesmos filtros) — **Gate 2**
- [ ] `pbw validar` sem erros · LEIA-ME e histórico atualizados
"""
