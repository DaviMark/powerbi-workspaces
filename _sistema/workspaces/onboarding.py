"""`pbw boas-vindas` — decides whether the AI must offer the repository tour at the start of a session.

Rule (AGENTS.md §0): every session, before anything else, the AI asks
    "Quer que eu te explique como o repositório funciona primeiro? Comandos, o que fica em cada pasta e tudo mais?"
unless the analyst already has MORE THAN ONE dashboard of their own, counting
    dashboards/  (real dashboards — not the nome-da-… templates, not examples marked `example = true`)
  + refatorar/   (.pbit / .pbix waiting to be refactored — not inside nome-da-… templates).
"""

from __future__ import annotations

import json
from pathlib import Path

from .layout import MANIFEST, PLACEHOLDER_PREFIX, REFACTOR, all_dashboards
from .util import read_toml

QUESTION = ("Quer que eu te explique como o repositório funciona primeiro? "
            "Comandos, o que fica em cada pasta e tudo mais?")
TOUR = "guias/apresentacao.md"


def own_dashboards(root: Path, cfg: dict | None = None) -> list[Path]:
    out = []
    for dash in all_dashboards(root, cfg):
        try:
            if read_toml(dash / MANIFEST).get("dashboard", {}).get("example", False):
                continue
        except Exception:  # noqa: BLE001  — a broken manifest still counts as the analyst's dashboard
            pass
        out.append(dash)
    return out


def pending_legacy(root: Path) -> list[Path]:
    inbox = root / REFACTOR
    files = list(inbox.rglob("*.pbit")) + list(inbox.rglob("*.pbix")) if inbox.exists() else []
    return [f for f in files if not any(p.startswith(PLACEHOLDER_PREFIX) for p in f.relative_to(inbox).parts)]


def status(root: Path, cfg: dict | None = None) -> dict:
    dashes, legacy = own_dashboards(root, cfg), pending_legacy(root)
    total = len(dashes) + len(legacy)
    return {"dashboards": len(dashes), "refatorar": len(legacy), "total": total, "ask": total <= 1}


def hook_json(root: Path, cfg: dict | None = None) -> str:
    """Claude Code SessionStart hook output (added to the session context)."""
    st = status(root, cfg)
    if st["ask"]:
        ctx = (f"POWER BI WORKSPACES — REGRA DE INÍCIO DE SESSÃO (AGENTS.md §0). O analista tem {st['total']} "
               f"dashboard(s) próprio(s) (dashboards: {st['dashboards']}, refatorar: {st['refatorar']}). "
               f"Antes de qualquer outra coisa, mesmo que a primeira mensagem já seja um pedido, pergunte exatamente: "
               f"\"{QUESTION}\" Se a resposta for sim, siga o roteiro de {TOUR} e depois continue o pedido. "
               f"Se for não, siga direto com o pedido.")
    else:
        ctx = (f"POWER BI WORKSPACES — o analista já tem {st['total']} dashboards próprios; "
               "não ofereça a explicação do repositório, a menos que ele peça.")
    return json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}},
                      ensure_ascii=False)
