"""Folder layout — the ONE place that knows where things live.

Rule of thumb for analysts: numbered folders are yours, `trabalho-da-ia/` is the AI's.

Dashboard  (dashboards/<empresa>/<área>/<subárea>/<dashboard>/)
    LEIA-ME.md
    1-seu-pedido/          PEDIDO.md (objetivo, perguntas, regras, visuais) + anexos/
    2-power-bi/            <Nome>.pbip (+ .Report/ .SemanticModel/) — always opens
    3-entrega/             the .pbit to publish
    trabalho-da-ia/        ficha.toml, sql/, desenho.md, conferencia.md, dicionario.md, historico.md

Company visual identity  (identidade-visual/<empresa>/) — applied to EVERY dashboard of that company
    1-cole-aqui/           logo/, manual-da-marca/, cores-e-fontes/, exemplos-de-relatorios/
    trabalho-da-ia/        identidade.toml, diretrizes.md, tema/, logos/
Default identity (companies without a folder): _sistema/identidade-padrao/
"""

from __future__ import annotations

from pathlib import Path

# repository
CONFIG = "workspaces.toml"
DASHBOARDS = "dashboards"
REFACTOR = "refatorar"
BRANDS = "identidade-visual"
CONNECTIONS = "conexoes"
SYSTEM = "_sistema"
TEMPLATE = f"{SYSTEM}/modelos/dashboard"
CATALOG_MD = "CATALOGO.md"
CATALOG_JSON = "catalogo.json"
FOLDER_README = "LEIA-ME.md"
WORK = "trabalho-da-ia"

# dashboard — the analyst's folders
README = "LEIA-ME.md"
REQUEST_DIR = "1-seu-pedido"
REQUEST = f"{REQUEST_DIR}/PEDIDO.md"
ATTACHMENTS = f"{REQUEST_DIR}/anexos"
POWERBI = "2-power-bi"
DELIVERY = "3-entrega"
# dashboard — the AI's folder
MANIFEST = f"{WORK}/ficha.toml"
SQL = f"{WORK}/sql"
DESIGN = f"{WORK}/desenho.md"
CHECKS = f"{WORK}/conferencia.md"
DICTIONARY = f"{WORK}/dicionario.md"
HISTORY = f"{WORK}/historico.md"
LEGACY = f"{WORK}/legado"
CUSTOM_VISUALS = f"{WORK}/visuais-customizados"

DASHBOARD_ITEMS = {README, REQUEST_DIR, POWERBI, DELIVERY, WORK, ".gitkeep", ".gitignore"}
PROTOTYPE_MARK = "PROTÓTIPO"

# company visual identity
BRAND_INBOX = "1-cole-aqui"
BRAND_FILE = f"{WORK}/identidade.toml"
BRAND_GUIDE = f"{WORK}/diretrizes.md"
BRAND_THEME_DIR = f"{WORK}/tema"
BRAND_ASSETS = f"{WORK}/logos"
DEFAULT_BRAND = "padrao"                       # lives in _sistema/, never edited by analysts
DEFAULT_BRAND_DIR = f"{SYSTEM}/identidade-padrao"
BRAND_INBOX_FOLDERS = ("logo", "manual-da-marca", "cores-e-fontes", "exemplos-de-relatorios")
ATTACHMENT_FOLDERS = ("consultas-sql", "imagens-e-rascunhos", "documentos")
PLACEHOLDER_PREFIX = "nome-d"                  # nome-da-empresa/, nome-da-area/… — folders to rename


def dashboards_root(root: Path, cfg: dict | None = None) -> Path:
    cfg = cfg or {}
    return root / cfg.get("structure", {}).get("root", DASHBOARDS)


def powerbi_dir(dash: Path) -> Path:
    return dash / POWERBI


def pbip_files(dash: Path) -> list[Path]:
    return sorted(powerbi_dir(dash).glob("*.pbip"))


def is_placeholder(path: Path) -> bool:
    """nome-da-empresa/nome-da-area/… — the template dashboard that ships with the repository."""
    return any(part.startswith(PLACEHOLDER_PREFIX) for part in path.parts)


def all_dashboards(root: Path, cfg: dict | None = None) -> list[Path]:
    base = dashboards_root(root, cfg)
    return sorted(p.parent.parent for p in base.glob(f"*/*/*/*/{MANIFEST}")
                  if not is_placeholder(p.parent.parent.relative_to(base)))


def company_of(root: Path, dash: Path, cfg: dict | None = None) -> str:
    """First path level under dashboards/ = company slug (also the identity folder name)."""
    try:
        return dash.relative_to(dashboards_root(root, cfg)).parts[0]
    except (ValueError, IndexError):
        return ""
