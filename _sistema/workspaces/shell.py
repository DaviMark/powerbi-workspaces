"""App shell — the frame every report page shares (guias/padrao-visual.md).

    ┌────────────┬──────────────────────────────────────────────────────────┐
    │ EMPRESA    │ Relatório › Página                    [Período] [Filtros]│  top bar (52 px)
    │            ├──────────────────────────────────────────────────────────┤
    │ RELATÓRIO  │ Título da página                                         │
    │ ▸ Página 1 │ subtítulo / pergunta                                     │
    │   Página 2 │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                      │  KPI cards
    │            │ └──────┘ └──────┘ └──────┘ └──────┘                      │
    │ APOIO      │ ┌───────────────────┐ ┌───────────────────┐              │  chart cards
    │   Document.│ └───────────────────┘ └───────────────────┘              │
    └────────────┴──────────────────────────────────────────────────────────┘
      sidebar 200 px, brand color

Colors come from the company identity (identidade-visual/<empresa>/trabalho-da-ia/identidade.toml).
Shell visuals are system-managed: their names are stable ids of "shell-*" keys, so they can be
refreshed without touching the page content.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import pbip
from .util import stable_id, write_json

SIDEBAR_W = 200
HEADER_H = 52
M = 20          # content margin
G = 16          # gutter
MAX_NAV = 24


def palette(brand: dict[str, Any] | None) -> dict[str, str]:
    c = (brand or {}).get("colors", {})
    text = c.get("text", "#1B1F24")
    return {
        "sidebar": c.get("sidebar", text),
        "sidebar_text": c.get("sidebar_text", "#FFFFFF"),
        "sidebar_muted": c.get("sidebar_muted", "#A7ADB7"),
        "sidebar_active": c.get("sidebar_active", "#3A4049"),
        "surface": c.get("surface", "#FFFFFF"),
        "border": c.get("border", "#E3E6EA"),
        "canvas": c.get("canvas", "#F5F6F8"),
        "text": text,
        "muted": c.get("text_muted", "#5B6470"),
        "placeholder": c.get("surface_alt", "#EEF1F4"),
    }


def company_name(brand: dict[str, Any] | None, fallback: str) -> str:
    return ((brand or {}).get("brand", {}) or {}).get("name") or fallback


def content_box(width: int, height: int) -> tuple[int, int, int, int]:
    """x0, y0, x1, y1 of the area where page content goes."""
    return SIDEBAR_W + M, HEADER_H + M, width - M, height - M


def filled(visual: dict[str, Any], color: str, radius: int = 0, border: str | None = None) -> dict[str, Any]:
    objs: dict[str, Any] = {
        "background": [{"properties": {"show": pbip.lit("true"),
                                       "color": {"solid": {"color": pbip.text_lit(color)}},
                                       "transparency": pbip.lit("0D")}}],
        "border": [{"properties": {"show": pbip.lit("true" if border else "false"),
                                   **({"color": {"solid": {"color": pbip.text_lit(border)}}} if border else {}),
                                   "radius": pbip.lit(f"{radius}D")}}],
    }
    visual.setdefault("visualContainerObjects", {}).update(objs)
    return visual


def _keys() -> list[str]:
    return (["shell-sidebar", "shell-brand", "shell-sec1", "shell-sec2", "shell-doc", "shell-top", "shell-crumb",
             "shell-period", "shell-filters"] + [f"shell-nav-{i}" for i in range(MAX_NAV)])


def remove(page_dir: Path, pid: str) -> None:
    for key in _keys():
        d = page_dir / "visuals" / stable_id(pid, key)
        if d.exists():
            shutil.rmtree(d)


def write(page_dir: Path, pid: str, *, active: str, pages: list[str], doc_page: str, report_title: str,
          company: str, colors: dict[str, str], width: int, height: int) -> None:
    """(Re)write the shell visuals of one page."""
    remove(page_dir, pid)
    p = colors
    items: list[tuple[str, tuple[int, int, int, int], dict[str, Any]]] = []
    items.append(("shell-sidebar", (0, 0, SIDEBAR_W, height),
                  filled(pbip.textbox(" ", 8), p["sidebar"])))
    items.append(("shell-brand", (20, 18, SIDEBAR_W - 40, 30),
                  pbip.textbox(company.upper(), 11, True, p["sidebar_text"])))
    items.append(("shell-sec1", (20, 68, SIDEBAR_W - 40, 20), pbip.textbox("RELATÓRIO", 8, True, p["sidebar_muted"])))
    y = 92
    for i, name in enumerate([n for n in pages if n != doc_page][:MAX_NAV]):
        on = name == active
        v = pbip.textbox(name, 10, on, p["sidebar_text"] if on else p["sidebar_muted"])
        if on:
            filled(v, p["sidebar_active"], 8)
        items.append((f"shell-nav-{i}", (10, y, SIDEBAR_W - 20, 32), v))
        y += 36
    y += 16
    items.append(("shell-sec2", (20, y, SIDEBAR_W - 40, 20), pbip.textbox("APOIO", 8, True, p["sidebar_muted"])))
    on = active == doc_page
    v = pbip.textbox(doc_page, 10, on, p["sidebar_text"] if on else p["sidebar_muted"])
    if on:
        filled(v, p["sidebar_active"], 8)
    items.append(("shell-doc", (10, y + 24, SIDEBAR_W - 20, 32), v))
    items.append(("shell-top", (SIDEBAR_W, 0, width - SIDEBAR_W, HEADER_H),
                  filled(pbip.textbox(" ", 8), p["surface"], 0)))
    items.append(("shell-crumb", (SIDEBAR_W + M, 12, 560, 28),
                  pbip.textbox(f"{report_title}  ›  {active}", 10, False, p["muted"])))
    items.append(("shell-period", (width - M - 236, 10, 112, 32),
                  filled(pbip.textbox("Período", 9, False, p["muted"]), p["surface"], 8, p["border"])))
    items.append(("shell-filters", (width - M - 112, 10, 112, 32),
                  filled(pbip.textbox("Filtros", 9, False, p["muted"]), p["surface"], 8, p["border"])))
    for z, (key, pos, visual) in enumerate(items):
        vc = pbip.visual_container(pid, key, pos, 100 + z, visual)
        write_json(page_dir / "visuals" / vc["name"] / "visual.json", vc)
