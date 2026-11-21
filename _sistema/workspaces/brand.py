"""Company visual identity (identidade-visual/<empresa>/trabalho-da-ia/identidade.toml) -> Power BI theme.

One identity per company, applied automatically to every dashboard of that company.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .layout import BRAND_FILE, BRAND_THEME_DIR, BRANDS, DEFAULT_BRAND, DEFAULT_BRAND_DIR
from .util import read_toml, write_json

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def brand_dir(root: Path, slug: str) -> Path:
    return root / BRANDS / slug


def brand_file(root: Path, slug: str) -> Path:
    if slug == DEFAULT_BRAND:
        return root / DEFAULT_BRAND_DIR / "identidade.toml"
    return brand_dir(root, slug) / BRAND_FILE


def theme_dir(root: Path, slug: str) -> Path:
    if slug == DEFAULT_BRAND:
        return root / DEFAULT_BRAND_DIR / "tema"
    return brand_dir(root, slug) / BRAND_THEME_DIR


def list_brands(root: Path) -> list[str]:
    base = root / BRANDS
    return sorted(p.name for p in base.iterdir() if (p / BRAND_FILE).is_file()) if base.exists() else []


def resolve(root: Path, company: str) -> str:
    """The company's identity when it exists, otherwise the default one."""
    return company if company and brand_file(root, company).is_file() else DEFAULT_BRAND


def load_brand(root: Path, slug: str) -> dict[str, Any]:
    path = brand_file(root, slug)
    if not path.exists():
        raise SystemExit(f"ERRO: identidade visual '{slug}' não encontrada em identidade-visual/{slug}/{BRAND_FILE}")
    data = read_toml(path)
    colors = data.get("colors", {})
    for key, value in colors.items():
        values = value if isinstance(value, list) else [value]
        for v in values:
            if not HEX.match(str(v)):
                raise SystemExit(f"ERRO: identidade '{slug}': cor inválida em colors.{key}: {v!r} (use #RRGGBB)")
    return data


def _solid(color: str) -> dict[str, Any]:
    return {"solid": {"color": color}}


def build_theme(brand: dict[str, Any]) -> dict[str, Any]:
    """Company identity -> Power BI theme in the Workspaces visual standard (guias/padrao-visual.md).

    Not the Microsoft look: brand ramp instead of the default palette, white rounded cards with a hairline
    border, no gridlines or axis titles, legends top-left, quiet labels, generous padding.
    """
    b = brand.get("brand", {})
    c = brand.get("colors", {})
    t = brand.get("typography", {})
    lay = brand.get("layout", {})

    font = t.get("font_family", "Segoe UI")
    font_semibold = t.get("font_family_semibold", f"{font} Semibold" if font == "Segoe UI" else font)
    text = c.get("text", "#1B1F24")
    muted = c.get("text_muted", "#5B6470")
    subtle = c.get("text_subtle", "#8A929C")
    surface = c.get("surface", "#FFFFFF")
    canvas = c.get("canvas", "#F5F6F8")
    border = c.get("border", "#E3E6EA")
    primary = c.get("primary", "#1F3A5F")
    ramp = c.get("ramp") or [primary]
    data = c.get("data") or ramp
    radius = int(lay.get("radius", 12))
    pad = int(lay.get("visual_padding", 16))
    title_size = int(t.get("title_size", 12))
    body = int(t.get("body_size", 10))

    def s(color: str) -> dict[str, Any]:
        return _solid(color)

    return {
        "name": b.get("name", "Identidade"),
        "dataColors": data,
        "foreground": text,
        "foregroundNeutralSecondary": muted,
        "foregroundNeutralTertiary": subtle,
        "background": surface,
        "backgroundLight": canvas,
        "backgroundNeutral": border,
        "tableAccent": primary,
        "good": c.get("positive", "#1E8E3E"),
        "neutral": c.get("warning", "#C77700"),
        "bad": c.get("negative", "#C5221F"),
        "maximum": ramp[0],
        "center": ramp[len(ramp) // 2],
        "minimum": ramp[-1],
        "hyperlink": primary,
        "textClasses": {
            "callout": {"fontSize": int(t.get("kpi_size", 24)), "fontFace": font_semibold, "color": text},
            "title": {"fontSize": title_size, "fontFace": font_semibold, "color": text},
            "header": {"fontSize": int(t.get("header_size", 11)), "fontFace": font_semibold, "color": text},
            "label": {"fontSize": body, "fontFace": font, "color": muted},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": s(surface), "transparency": 0}],
                    "border": [{"show": True, "color": s(border), "radius": radius}],
                    "dropShadow": [{"show": False}],
                    "padding": [{"top": pad, "bottom": pad, "left": pad, "right": pad}],
                    "title": [{"show": True, "fontColor": s(text), "fontSize": title_size,
                               "fontFamily": font_semibold, "alignment": "left"}],
                    "visualHeader": [{"show": True, "foreground": s(subtle), "border": s(surface),
                                      "background": s(surface), "transparency": 0}],
                    "legend": [{"show": True, "position": "TopLeft", "showTitle": False,
                                "labelColor": s(muted), "fontSize": body}],
                    "categoryAxis": [{"showAxisTitle": False, "gridlineShow": False, "labelColor": s(muted),
                                      "fontSize": body}],
                    "valueAxis": [{"showAxisTitle": False, "gridlineShow": False, "show": False}],
                    "labels": [{"color": s(muted), "fontSize": body}],
                    "general": [{"responsive": True}],
                }
            },
            "page": {
                "*": {
                    "background": [{"color": s(canvas), "transparency": 0}],
                    "outspace": [{"color": s(canvas), "transparency": 0}],
                }
            },
            "textbox": {"*": {"background": [{"show": False}], "border": [{"show": False}],
                              "padding": [{"top": 0, "bottom": 0, "left": 0, "right": 0}]}},
            "card": {"*": {"labels": [{"color": s(text), "fontFamily": font_semibold,
                                       "fontSize": int(t.get("kpi_size", 24))}],
                           "categoryLabels": [{"color": s(muted), "fontSize": body}]}},
            "cardVisual": {"*": {"value": [{"fontColor": s(text), "fontFamily": font_semibold}],
                                 "label": [{"fontColor": s(muted)}]}},
            "slicer": {"*": {"header": [{"fontColor": s(muted), "fontFamily": font, "textSize": body}],
                             "items": [{"fontColor": s(text), "fontFamily": font, "textSize": body}]}},
            "tableEx": {"*": {
                "grid": [{"gridVertical": False, "gridHorizontal": True, "gridHorizontalColor": s(border),
                          "rowPadding": 6, "outlineColor": s(border)}],
                "columnHeaders": [{"fontColor": s(muted), "backColor": s(surface),
                                   "fontFamily": font_semibold, "outline": "BottomOnly"}],
                "values": [{"fontColorPrimary": s(text), "backColorPrimary": s(surface),
                            "fontColorSecondary": s(text), "backColorSecondary": s(canvas)}],
            }},
            "pivotTable": {"*": {
                "grid": [{"gridVertical": False, "gridHorizontal": True, "gridHorizontalColor": s(border),
                          "rowPadding": 6, "outlineColor": s(border)}],
                "columnHeaders": [{"fontColor": s(muted), "backColor": s(surface), "fontFamily": font_semibold}],
                "rowHeaders": [{"fontColor": s(text), "backColor": s(surface)}],
                "values": [{"fontColorPrimary": s(text), "backColorPrimary": s(surface)}],
            }},
        },
    }


def theme_filename(slug: str) -> str:
    return f"{slug}-theme.json"


def generate(root: Path, slug: str) -> Path:
    theme = build_theme(load_brand(root, slug))
    out = theme_dir(root, slug) / theme_filename(slug)
    write_json(out, theme)
    return out


def apply_to_dashboards(root: Path, slug: str) -> list[Path]:
    """Write the company theme into the report of every dashboard of that company."""
    from . import pbip
    from .layout import all_dashboards, company_of, powerbi_dir
    from .util import read_toml

    cfg = read_toml(root / "workspaces.toml")
    theme = build_theme(load_brand(root, slug))
    done = []
    for dash in all_dashboards(root, cfg):
        uses = resolve(root, company_of(root, dash, cfg))
        if uses != slug:
            continue
        for report in sorted(powerbi_dir(dash).glob("*.Report")):
            pbip.apply_theme(report, theme, theme_filename(slug))
            done.append(dash)
    return done

