"""Local secret / sensitive-artifact scanner. No network, no external tools.

Runs in the pre-commit hook and in CI. It is a safety net, not a replacement for
GitHub secret scanning or your company DLP.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import pbit as pbit_mod
from .util import is_text_file, rel

PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("SEC001", "Senha em string de conexão", re.compile(r"(?i)\b(?:password|pwd)\s*=\s*[^;\"'\s{}<>$]{3,}")),
    ("SEC002", "Atribuição de segredo", re.compile(
        r"(?i)\b(?:secret|client_secret|api[_-]?key|access[_-]?token|auth[_-]?token|passwd|senha)\b\s*[:=]\s*[\"'][^\"'\s<>{}$]{6,}[\"']")),
    ("SEC003", "Chave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----")),
    ("SEC004", "Service account GCP", re.compile(r"\"type\"\s*:\s*\"service_account\"")),
    ("SEC005", "AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("SEC006", "Azure storage key / SAS", re.compile(r"(?i)AccountKey=[A-Za-z0-9+/=]{20,}|[?&]sig=[A-Za-z0-9%]{20,}")),
    ("SEC007", "Token GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("SEC008", "Token Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("SEC009", "JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("SEC010", "Connection string com usuário e senha", re.compile(r"(?i)\b(?:uid|user id)\s*=\s*[^;]+;\s*(?:pwd|password)\s*=")),
]

# Files that must never be committed, whatever their content
FORBIDDEN_SUFFIXES = {".pbix": "PBIX contém DADOS. Versione o PBIP.",
                      ".abf": "Cache do modelo (dados).",
                      ".pem": "Chave/certificado.",
                      ".pfx": "Certificado com chave privada.",
                      ".p12": "Certificado com chave privada.",
                      ".key": "Chave privada."}
FORBIDDEN_NAMES = {"localSettings.json": "Configuração local do Power BI (pode conter caminhos/identidades).",
                   "cache.abf": "Cache do modelo (dados).",
                   ".env": "Variáveis de ambiente/segredos."}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache"}
ALLOW_MARK = "pbw:allow-secret"


@dataclass
class Hit:
    rule: str
    message: str
    path: str
    line: int = 0


def tracked_files(root: Path, staged: bool = False) -> list[Path]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged else \
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    try:
        out = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=True).stdout
        return [root / line for line in out.splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for p in root.rglob("*"):
            if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                files.append(p)
        return files


def scan(root: Path, files: list[Path] | None = None, staged: bool = False) -> list[Hit]:
    hits: list[Hit] = []
    for path in files if files is not None else tracked_files(root, staged):
        if not path.is_file():
            continue
        r = rel(path, root)
        name = path.name
        if name in FORBIDDEN_NAMES or (name.startswith(".env") and not name.endswith((".example", ".sample"))):
            hits.append(Hit("SEC100", FORBIDDEN_NAMES.get(name, FORBIDDEN_NAMES[".env"]), r))
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            hits.append(Hit("SEC101", FORBIDDEN_SUFFIXES[path.suffix.lower()], r))
            continue
        if name.endswith(".local.toml"):
            hits.append(Hit("SEC102", "Perfil de conexão local (*.local.toml) não deve ser versionado.", r))
            continue
        if path.suffix.lower() == ".pbit":
            if pbit_mod.has_embedded_data(path):
                hits.append(Hit("SEC103", "PBIT contém tabela com dados embutidos (Inserir Dados).", r))
            payload = pbit_mod.text_payload(path)
            for rule, msg, rx in PATTERNS:
                if rx.search(payload):
                    hits.append(Hit(rule, f"{msg} (dentro do PBIT)", r))
            continue
        if path.stat().st_size > 5_000_000 or not is_text_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK in line:
                continue
            for rule, msg, rx in PATTERNS:
                if rx.search(line):
                    hits.append(Hit(rule, msg, r, n))
    return hits
