"""Small, dependency-free helpers shared by every command."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tomllib
import unicodedata
import uuid
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Repository root discovery
# --------------------------------------------------------------------------- #

MARKER = Path("workspaces.toml")


LONG_PREFIX = "\\\\?\\"


def long_path(path: Path) -> Path:
    """Windows: opt into paths longer than 260 characters (deep folders, OneDrive).

    PBIR folders are deep (…/Nome.Report/definition/pages/<id>/visuals/<id>/visual.json); without the
    extended-length prefix Windows refuses to create them and glob() silently skips them.
    """
    path = path.resolve()
    prefix = LONG_PREFIX
    if os.name == "nt" and not str(path).startswith(prefix):
        return Path(prefix + str(path))
    return path


def find_root(start: Path | None = None) -> Path:
    """Walk up from *start* (or cwd) until a folder with workspaces.toml."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / MARKER).is_file():
            return long_path(candidate)
    # Fallback: the repository that contains _sistema/pbw.py
    fallback = Path(__file__).resolve().parents[2]
    if (fallback / MARKER).is_file():
        return long_path(fallback)
    raise SystemExit(
        "ERRO: não encontrei workspaces.toml. Abra o terminal dentro da pasta do Power BI Workspaces."
    )


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def strip_accents(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c))


def slugify(text: str) -> str:
    """'Contas a Receber' -> 'contas-a-receber'."""
    text = strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def is_slug(text: str) -> bool:
    return bool(SLUG_RE.match(text))


def pascal(text: str) -> str:
    """'Aging de Títulos' -> 'AgingDeTitulos'."""
    parts = re.split(r"[^A-Za-z0-9]+", strip_accents(text))
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Dashboard"


def title_from_slug(slug: str) -> str:
    return " ".join(w.capitalize() if len(w) > 2 else w for w in slug.split("-")).strip()


def stable_id(*parts: str, length: int = 20) -> str:
    """Deterministic hex id (PBIR page/visual names)."""
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:length]


def new_uuid() -> str:
    return str(uuid.uuid4())


def tmdl_name(name: str) -> str:
    """Quote a TMDL object name when needed."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def dax_table(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def m_string(text: str) -> str:
    """Encode arbitrary text (e.g. SQL) as a single-line Power Query M text literal."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    out = (
        text.replace("#(", "#(#)(")
        .replace('"', '""')
        .replace("\t", "#(tab)")
        .replace("\n", "#(lf)")
    )
    return f'"{out}"'


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def write_text(path: Path, content: str, *, overwrite: bool = True) -> bool:
    """Write UTF-8 text with LF endings. Returns True if written."""
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return True


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def render(template: str, values: dict[str, str]) -> str:
    """Tiny `{{key}}` renderer. Unknown keys are left intact on purpose."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return str(values.get(key, match.group(0)))

    return re.sub(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}", repl, template)


def rel(path: Path, root: Path) -> str:
    try:
        return long_path(path).relative_to(long_path(root)).as_posix()
    except ValueError:
        return path.as_posix()


def is_text_file(path: Path, sniff: int = 2048) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(sniff)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    return True


# --------------------------------------------------------------------------- #
# Console
# --------------------------------------------------------------------------- #

_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
if os.name == "nt":  # enable ANSI on modern Windows terminals
    os.system("")

_CODES = {"red": "31", "green": "32", "yellow": "33", "blue": "34", "dim": "2", "bold": "1"}


def paint(text: str, color: str) -> str:
    if not _COLOR:
        return text
    return f"\033[{_CODES[color]}m{text}\033[0m"


def ok(msg: str) -> None:
    print(paint("✔ ", "green") + msg)


def info(msg: str) -> None:
    print(paint("• ", "blue") + msg)


def warn(msg: str) -> None:
    print(paint("! ", "yellow") + msg)


def fail(msg: str) -> None:
    print(paint("✖ ", "red") + msg, file=sys.stderr)
