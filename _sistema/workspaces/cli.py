"""Command line interface: `pbw <comando>` (atalhos pbw.cmd / pbw na raiz → python _sistema/pbw.py)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import brand as brand_mod
from . import docs as docs_mod
from . import pbit as pbit_mod
from . import onboarding, prototipo, scaffold, sqlsync
from . import secrets as sec_mod
from . import validate as val_mod
from .connectors import CONNECTORS, list_profiles, load_profile
from .layout import ATTACHMENTS, DESIGN, MANIFEST, REQUEST, all_dashboards, pbip_files
from .util import LONG_PREFIX, fail, find_root, info, long_path, ok, paint, rel, warn

BANNER = r"""
  ┌──────────────────────────────────────────────────┐
  │  Power BI Workspaces · Power BI governado com IA │
  └──────────────────────────────────────────────────┘"""


def _dash(root: Path, arg: str | None) -> Path:
    """Accepts a folder path, a path under dashboards/, a dashboard slug, or nothing (current folder)."""
    if not arg:
        here = Path.cwd().resolve()
        for cand in (here, *here.parents):
            if (cand / MANIFEST).exists():
                return long_path(cand)
        raise SystemExit("ERRO: informe o dashboard (ex.: aging-de-titulos) ou abra o terminal dentro da pasta dele.")
    p = Path(arg)
    for cand in ([p] if p.is_absolute() else [Path.cwd() / p, root / p, scaffold.analytics_root(root) / p]):
        if (cand / MANIFEST).exists():
            return long_path(cand)
    hits = [d for d in all_dashboards(root, scaffold.settings(root)) if d.name == arg.strip("/")]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise SystemExit(f"ERRO: '{arg}' existe em mais de um lugar: "
                         + ", ".join(rel(h, root) for h in hits) + ". Informe o caminho completo.")
    raise SystemExit(f"ERRO: dashboard '{arg}' não encontrado. Veja a lista em dashboards/CATALOGO.md.")


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #


def cmd_new(a: argparse.Namespace, root: Path) -> int:
    target = scaffold.create_dashboard(root, a.path, a.connection, a.brand, force=a.force)
    docs_mod.catalog(root)
    print()
    info("Próximo passo — escreva o que você quer (objetivo, perguntas, regras, visuais):")
    print(f"    {rel(target / REQUEST, root)}")
    print(f"    SQL que você já usa, prints e PDFs vão em {rel(target / ATTACHMENTS, root)}/")
    info('Depois peça à IA: "crie o dashboard ' + target.name + '"')
    return 0


def cmd_open(a: argparse.Namespace, root: Path) -> int:
    dash = _dash(root, a.dashboard)
    files = pbip_files(dash)
    if not files:
        fail(f"{rel(dash, root)}/2-power-bi/ não tem .pbip. Rode `pbw diagnostico` e peça à IA para recriar o projeto.")
        return 1
    target = Path(str(files[0]).replace(LONG_PREFIX, ""))
    print(f"  {target}")
    if os.name == "nt" and not a.print_only:
        os.startfile(target)  # type: ignore[attr-defined]  # abre no Power BI Desktop
        ok("Abrindo no Power BI Desktop…")
    elif not a.print_only:
        info("O Power BI Desktop só existe para Windows: abra este arquivo em uma máquina Windows.")
    return 0


def cmd_prototype(a: argparse.Namespace, root: Path) -> int:
    dash = _dash(root, a.dashboard)
    written, skipped = prototipo.build(root, dash, scaffold.settings(root))
    for n in written:
        ok(f"página de protótipo: {n}")
    for n in skipped:
        info(f"mantida (já construída de verdade): {n}")
    if not (dash / DESIGN).exists():
        warn(f"{DESIGN} não existe — criei só uma página de rascunho.")
    info(f"Veja no Power BI Desktop: pbw abrir {dash.name}")
    return 0


def cmd_refactor(a: argparse.Namespace, root: Path) -> int:
    items = scaffold.pending_refactors(root)
    if a.list or not items:
        if not items:
            info("Nada em refatorar/. Coloque o .pbit em refatorar/<empresa>/<área>/<subárea>/<dashboard>/")
        for f, spec in items:
            print(f"  {rel(f, root)}  →  dashboards/{'/'.join(scaffold.parse_target(spec)[0])}")
        return 0
    for f, spec in items:
        print(paint(f"\n▸ {rel(f, root)}", "bold"))
        scaffold.run_refactor(root, f, spec, a.connection, a.brand, force=a.force)
    docs_mod.catalog(root)
    return 0


def cmd_extract(a: argparse.Namespace, root: Path) -> int:
    src = Path(a.file).resolve()
    out = Path(a.out).resolve() if a.out else src.parent / f"{src.stem}-extracao"
    ex, analysis = pbit_mod.extract(src, do_redact=not a.no_redact)
    files = pbit_mod.write_reports(ex, analysis, out)
    ok(f"{len(files)} arquivos em {out}")
    for f in ex.findings:
        warn(f)
    return 0


def cmd_connections(a: argparse.Namespace, root: Path) -> int:
    if a.types:
        for k, c in CONNECTORS.items():
            params = ", ".join(p.key for p in c.params)
            print(f"  {paint(f'{k:<12}', 'bold')} {c.label}  [{params}]")
        return 0
    names = list_profiles(root)
    if not names:
        warn("Nenhum perfil em conexoes/.")
    for n in names:
        p = load_profile(root, n)
        local = any(f.name.endswith(".local.toml") for f in p.source_files)
        tag = paint(" (local)", "green") if local else (paint(" (exemplo)", "dim") if n.endswith(".example") else "")
        print(f"  {paint(n, 'bold')}{tag}  ·  {p.connector.label}  ·  parâmetros: "
              + ", ".join(p.identifiers().values()))
    return 0


def cmd_connect(a: argparse.Namespace, root: Path) -> int:
    dash = _dash(root, a.dashboard)
    if a.connection:
        sqlsync.set_connection(root, dash, a.connection)
    else:
        sqlsync.sync(root, dash)
    return 0


def cmd_sql_sync(a: argparse.Namespace, root: Path) -> int:
    sqlsync.sync(root, _dash(root, a.dashboard))
    return 0


def cmd_docs(a: argparse.Namespace, root: Path) -> int:
    targets = [_dash(root, a.dashboard)] if a.dashboard else all_dashboards(root, scaffold.settings(root))
    for d in targets:
        ok(f"{rel(docs_mod.dictionary(d), root)}")
    ok(f"{rel(docs_mod.catalog(root), root)}")
    return 0


def cmd_catalog(a: argparse.Namespace, root: Path) -> int:
    ok(rel(docs_mod.catalog(root), root))
    return 0


def cmd_brand(a: argparse.Namespace, root: Path) -> int:
    slugs = [a.slug] if a.slug else brand_mod.list_brands(root)
    if not slugs:
        warn("Nenhuma identidade em identidade-visual/<empresa>/trabalho-da-ia/identidade.toml")
    for s in slugs:
        ok(f"tema gerado: {rel(brand_mod.generate(root, s), root)}")
        for d in brand_mod.apply_to_dashboards(root, s):
            ok(f"  aplicado em {rel(d, root)}")
    return 0


def _print_issues(issues: list[val_mod.Issue], root: Path) -> tuple[int, int]:
    errors = [i for i in issues if i.level == val_mod.ERROR]
    warns = [i for i in issues if i.level == val_mod.WARN]
    for i in issues:
        color = {"erro": "red", "aviso": "yellow", "info": "blue"}[i.level]
        print(f"  {paint(f'{i.level.upper():<5}', color)} {paint(i.rule, 'dim')}  {i.path}  —  {i.message}")
    return len(errors), len(warns)


def cmd_validate(a: argparse.Namespace, root: Path) -> int:
    if a.dashboard:
        cfg = scaffold.settings(root)
        issues = val_mod.validate_dashboard(root, _dash(root, a.dashboard), cfg)
    else:
        issues = val_mod.validate_tree(root) + val_mod.pending_inbox(root)
    n_err, n_warn = _print_issues(issues, root)
    print()
    if n_err:
        fail(f"{n_err} erro(s), {n_warn} aviso(s).")
        return 1
    if n_warn and a.strict:
        fail(f"{n_warn} aviso(s) em modo --strict.")
        return 1
    ok(f"Governança OK · {n_warn} aviso(s).")
    return 0


def cmd_scan(a: argparse.Namespace, root: Path) -> int:
    hits = sec_mod.scan(root, staged=a.staged)
    for h in hits:
        loc = f"{h.path}:{h.line}" if h.line else h.path
        print(f"  {paint('BLOQUEADO', 'red')} {paint(h.rule, 'dim')}  {loc}  —  {h.message}")
    if hits:
        fail(f"{len(hits)} problema(s) de segurança. Nada foi enviado. Corrija antes do commit.")
        print("  Falso positivo? Adicione o comentário `pbw:allow-secret` na linha.")
        return 1
    ok("Nenhum segredo ou artefato sensível encontrado.")
    return 0


HOOK = """#!/bin/sh
# Power BI Workspaces pre-commit — bloqueia dados, segredos e quebras de governança.
PY=$(command -v python3 || command -v python)
"$PY" _sistema/pbw.py seguranca --staged || exit 1
"$PY" _sistema/pbw.py validar || exit 1
"""


def cmd_install_hooks(a: argparse.Namespace, root: Path) -> int:
    git_dir = root / ".git"
    if not git_dir.exists():
        fail("Este diretório ainda não é um repositório Git. Rode `git init` primeiro.")
        return 1
    hook = git_dir / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK, encoding="utf-8", newline="\n")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    ok(f"pre-commit instalado em {rel(hook, root)}")
    return 0


def cmd_welcome(a: argparse.Namespace, root: Path) -> int:
    cfg = scaffold.settings(root)
    if a.hook:
        print(onboarding.hook_json(root, cfg))
        return 0
    st = onboarding.status(root, cfg)
    if a.verificar:
        print(("PERGUNTAR" if st["ask"] else "NAO-PERGUNTAR") +
              f" · dashboards={st['dashboards']} · refatorar={st['refatorar']} · total={st['total']}")
        return 0
    print(BANNER)
    print(f"\n  Seus dashboards: {st['dashboards']} em dashboards/ · {st['refatorar']} esperando em refatorar/\n")
    print("  Por onde começar:")
    print("    1. Leia o guia visual: abra index.html no navegador")
    print("    2. Crie a identidade visual da empresa: identidade-visual/nome-da-empresa/")
    print("    3. Duplique dashboards/nome-da-empresa/…/nome-do-dashboard, renomeie e preencha 1-seu-pedido/PEDIDO.md")
    print("    4. Peça à IA: \"crie o dashboard <nome>\"")
    print(f"\n  Roteiro completo: {onboarding.TOUR}")
    return 0


def cmd_doctor(a: argparse.Namespace, root: Path) -> int:
    print(BANNER)
    checks = []
    checks.append(("Python ≥ 3.11", sys.version_info >= (3, 11), platform.python_version()))
    git = shutil.which("git")
    checks.append(("Git instalado", bool(git), git or "não encontrado"))
    hook = root / ".git" / "hooks" / "pre-commit"
    checks.append(("Hook pre-commit", hook.exists() and "Power BI Workspaces" in hook.read_text(errors="ignore"),
                   "rode: pbw instalar-hooks"))
    profiles = list_profiles(root)
    real = [p for p in profiles if not p.endswith(".example")]
    checks.append(("Perfil de conexão real", bool(real), ", ".join(real) or "copie um *.example.toml em conexoes/"))
    brands = brand_mod.list_brands(root)
    checks.append(("Identidade visual de empresa", bool(brands),
                   ", ".join(brands) or "nenhuma — crie identidade-visual/<empresa>/"))
    skill_paths = [root / ".claude/skills/powerbi-architect/SKILL.md", root / ".github/skills/powerbi-architect/SKILL.md",
                   root / ".agents/skills/powerbi-architect/SKILL.md"]
    checks.append(("Skill powerbi-architect", any(p.exists() for p in skill_paths),
                   "opcional — veja guias/ia-no-vscode.md"))
    dashes = all_dashboards(root, scaffold.settings(root))
    no_pbip = [rel(d, root) for d in dashes if len(pbip_files(d)) != 1]
    checks.append(("Todo dashboard tem 1 .pbip", not no_pbip, ", ".join(no_pbip) or f"{len(dashes)} dashboard(s)"))
    if git:
        try:
            ign = subprocess.run(["git", "check-ignore", "-q", "x.pbix"], cwd=root, capture_output=True).returncode == 0
        except OSError:
            ign = False
        checks.append((".gitignore bloqueia *.pbix", ign, ""))
    for label, good, detail in checks:
        mark = paint("✔", "green") if good else paint("•", "yellow")
        print(f"  {mark} {label:<30} {paint(detail, 'dim')}")
    print()
    info("Power BI Desktop: Arquivo › Opções › Recursos em versão prévia › ative 'Salvar como PBIP' e "
         "'Formato PBIR' (em versões antigas). Para abrir um dashboard: pbw abrir <nome>")
    return 0


# --------------------------------------------------------------------------- #

COMMANDS = [
    # (name, aliases, help)
    ("novo", ["new"], "cria um dashboard: <empresa>/<área>/<subárea>/<dashboard> (já com .pbip para abrir)"),
    ("abrir", ["open"], "abre o .pbip de um dashboard no Power BI Desktop"),
    ("prototipo", ["prototype"], "gera/atualiza as páginas de protótipo a partir de trabalho-da-ia/desenho.md"),
    ("refatorar", ["refactor"], "processa os .pbit de refatorar/ para dashboards/"),
    ("extrair", ["extract"], "extrai metadados de um .pbit para Markdown/JSON (sem Power BI)"),
    ("conexoes", ["connections"], "lista perfis de conexão (ou --tipos)"),
    ("conectar", ["connect"], "aplica/troca o perfil de conexão de um dashboard"),
    ("sincronizar-sql", ["sql-sync"], "grava sql/*.sql no modelo (1 etapa de Power Query)"),
    ("documentar", ["docs"], "gera trabalho-da-ia/dicionario.md (e o catálogo)"),
    ("catalogo", ["catalog"], "gera dashboards/CATALOGO.md"),
    ("identidade", ["brand"], "gera o tema da empresa e aplica em todos os dashboards dela"),
    ("validar", ["validate"], "confere as regras (tudo ou um dashboard)"),
    ("seguranca", ["scan"], "procura senhas e arquivos com dados"),
    ("instalar-hooks", ["install-hooks"], "instala o pre-commit (segurança + validação)"),
    ("diagnostico", ["doctor"], "verifica o ambiente e se todo dashboard abre"),
    ("boas-vindas", ["welcome"], "explica por onde começar (e diz à IA se deve oferecer a explicação)"),
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pbw", description="Power BI Workspaces — Power BI governado, feito com IA.")
    p.add_argument("--version", action="version", version=f"Power BI Workspaces {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="<comando>")
    s: dict[str, argparse.ArgumentParser] = {
        name: sub.add_parser(name, aliases=aliases, help=help_) for name, aliases, help_ in COMMANDS}

    dash_help = "dashboard: nome (aging-de-titulos), caminho, ou vazio = pasta atual"

    s["novo"].add_argument("path", metavar="caminho", help='ex.: "Acme/Financeiro/Contas a Receber/Aging de Títulos"')
    s["novo"].add_argument("--connection", "--conexao", "-c", help="perfil em conexoes/ (padrão: workspaces.toml)")
    s["novo"].add_argument("--brand", "--identidade", "-b", help=argparse.SUPPRESS)
    s["novo"].add_argument("--force", action="store_true")
    s["novo"].set_defaults(fn=cmd_new)

    s["abrir"].add_argument("dashboard", nargs="?", help=dash_help)
    s["abrir"].add_argument("--so-caminho", dest="print_only", action="store_true", help="só mostra o caminho")
    s["abrir"].set_defaults(fn=cmd_open)

    s["prototipo"].add_argument("dashboard", nargs="?", help=dash_help)
    s["prototipo"].set_defaults(fn=cmd_prototype)

    s["refatorar"].add_argument("--list", "--listar", action="store_true", help="só listar o que está esperando")
    s["refatorar"].add_argument("--connection", "--conexao", "-c")
    s["refatorar"].add_argument("--brand", "--identidade", "-b", help=argparse.SUPPRESS)
    s["refatorar"].add_argument("--force", action="store_true")
    s["refatorar"].set_defaults(fn=cmd_refactor)

    s["extrair"].add_argument("file", metavar="arquivo.pbit")
    s["extrair"].add_argument("--out", "--saida")
    s["extrair"].add_argument("--no-redact", action="store_true", help="não mascarar hosts/IPs")
    s["extrair"].set_defaults(fn=cmd_extract)

    s["conexoes"].add_argument("--types", "--tipos", action="store_true")
    s["conexoes"].set_defaults(fn=cmd_connections)

    s["conectar"].add_argument("dashboard", nargs="?", help=dash_help)
    s["conectar"].add_argument("--connection", "--conexao", "-c")
    s["conectar"].set_defaults(fn=cmd_connect)

    s["sincronizar-sql"].add_argument("dashboard", nargs="?", help=dash_help)
    s["sincronizar-sql"].set_defaults(fn=cmd_sql_sync)

    s["documentar"].add_argument("dashboard", nargs="?", help="vazio = todos")
    s["documentar"].set_defaults(fn=cmd_docs)

    s["catalogo"].set_defaults(fn=cmd_catalog)

    s["identidade"].add_argument("slug", nargs="?")
    s["identidade"].set_defaults(fn=cmd_brand)

    s["validar"].add_argument("dashboard", nargs="?", help="vazio = repositório inteiro")
    s["validar"].add_argument("--strict", "--rigoroso", action="store_true", help="avisos também falham")
    s["validar"].set_defaults(fn=cmd_validate)

    s["seguranca"].add_argument("--staged", action="store_true")
    s["seguranca"].set_defaults(fn=cmd_scan)

    s["instalar-hooks"].set_defaults(fn=cmd_install_hooks)
    s["diagnostico"].set_defaults(fn=cmd_doctor)
    s["boas-vindas"].add_argument("--verificar", action="store_true", help="só diz PERGUNTAR ou NAO-PERGUNTAR (para a IA)")
    s["boas-vindas"].add_argument("--hook", action="store_true", help=argparse.SUPPRESS)
    s["boas-vindas"].set_defaults(fn=cmd_welcome)
    return p


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < (3, 11):
        print("Power BI Workspaces requer Python 3.11+ (usa tomllib da biblioteca padrão).", file=sys.stderr)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args(argv)
    root = find_root()
    try:
        return int(args.fn(args, root) or 0)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            fail(exc.code.replace("ERRO: ", ""))
            return 1
        raise
    except KeyboardInterrupt:
        return 130
