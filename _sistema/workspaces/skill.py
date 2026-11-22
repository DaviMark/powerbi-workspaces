"""A skill `powerbi-architect` — onde está instalada, qual versão, e como usar os scripts dela.

O Power BI Workspaces não instala a skill (cada pessoa instala a sua; veja guias/ia-no-vscode.md).
Este módulo só *encontra* uma instalação, para:
- `pbw skill`: mostrar onde está, qual versão e como instalar/atualizar;
- `pbw auditar`: rodar `scripts/audit_pbip.py` da skill (nota de harmonia por página);
- `pbw previa`: rodar `scripts/preview_pbir.py` da skill (prévia das páginas no navegador, sem Windows).
Nada é baixado; nada é executado além dos scripts que a própria pessoa instalou.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

NOME = "powerbi-architect"
REPO = "https://github.com/DaviMark/powerbi-architect"
PROJETO = (".claude/skills", ".github/skills", ".agents/skills")
GLOBAL = (".claude/skills", ".copilot/skills", ".codex/skills")
GRAFO = "powerbi-graph/GRAPH_REPORT.md"
_VERSAO = re.compile(r"^\s*version:\s*[\"']?([0-9][^\"'\s]*)", re.M)


@dataclass
class Instalacao:
    pasta: Path
    versao: str
    escopo: str          # "projeto" | "global" | "plugin"


def versao(pasta: Path) -> str:
    try:
        m = _VERSAO.search((pasta / "SKILL.md").read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return "?"
    return m.group(1) if m else "?"


def instalacoes(root: Path, home: Path | None = None) -> list[Instalacao]:
    home = home if home is not None else Path.home()
    achadas: list[Instalacao] = []
    vistos: set[Path] = set()

    def add(pasta: Path, escopo: str) -> None:
        if (pasta / "SKILL.md").is_file():
            chave = pasta.resolve()
            if chave not in vistos:
                vistos.add(chave)
                achadas.append(Instalacao(pasta, versao(pasta), escopo))

    for base in PROJETO:
        add(root / base / NOME, "projeto")
    for base in GLOBAL:
        add(home / base / NOME, "global")
    plugins = home / ".claude" / "plugins"            # `/plugin install` do Claude Code
    if plugins.is_dir():
        for nivel in range(1, 6):
            for skill_md in plugins.glob("/".join(["*"] * nivel) + f"/skills/{NOME}/SKILL.md"):
                add(skill_md.parent, "plugin")
    return achadas


def script(root: Path, nome: str, home: Path | None = None) -> Path | None:
    """O script *nome* (ex.: audit_pbip.py) da instalação mais próxima: projeto, depois global, depois plugin."""
    for inst in instalacoes(root, home):
        p = inst.pasta / "scripts" / nome
        if p.is_file():
            return p
    return None


def grafo(root: Path) -> Path | None:
    p = root / GRAFO
    return p if p.is_file() else None


def como_instalar() -> list[str]:
    return [
        "Claude Code (um comando, dentro do Claude Code):",
        f"    /plugin install {NOME} --marketplace DaviMark/{NOME}",
        "Todas as IAs neste repositório (Copilot, Claude Code, Cursor, Codex, Gemini):",
        f"    git clone {REPO}.git ../{NOME}",
        f"    Windows (PowerShell):    ..\\{NOME}\\install\\install.ps1 -Target .",
        f"    macOS/Linux/Git Bash:    ../{NOME}/install/install.sh .",
        "Atualizar: `git pull` na pasta da skill e rode o instalador de novo com -Update (PowerShell) ou --update.",
        "Passo a passo: guias/ia-no-vscode.md",
    ]
