"""Caminhos longos no Windows — o limite de 260 caracteres do Power BI Desktop.

O Power BI Desktop ainda lê os arquivos do PBIP com a API antiga do Windows: nenhum arquivo pode passar
de 259 caracteres (o 260º é o terminador). O PBIR é fundo por natureza:

    <repo>\\dashboards\\<empresa>\\<área>\\<subárea>\\<dashboard>\\2-power-bi\\
        <Nome>.Report\\definition\\pages\\<20 hex>\\visuals\\<20 hex>\\visual.json

Com o repositório numa pasta comprida (Desktop, OneDrive, SharePoint sincronizado) o Desktop recusa
abrir: "O caminho especificado, o nome do arquivo ou ambos são muito longos".

Este módulo:
- mede o maior caminho de um dashboard, incluindo o visual que o Desktop criará quando o analista
  adicionar um visual novo (ids de 20 caracteres), e compara com uma margem segura;
- no Windows, abre o projeto por uma unidade virtual curta (`subst P: <repo>`): os mesmos arquivos,
  com um caminho muito menor. Nada é copiado nem movido; a unidade some ao reiniciar o Windows e o
  `pbw abrir` a recria.
"""

from __future__ import annotations

import os
import re
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from .layout import POWERBI
from .util import LONG_PREFIX

LIMITE_WINDOWS = 260          # MAX_PATH, com o terminador
LIMITE = 250                  # margem: o Desktop grava arquivos temporários ao salvar
RAIZ_TIPICA = r"C:\Users\analista\repos\powerbi-workspaces"   # usada fora do Windows (CI, Mac, Linux)
PASTA_CURTA = r"C:\pbw"
RAIZ_LONGA = 60               # acima disso, sobra pouco para empresa/área/subárea/dashboard (diagnóstico)
ID = "0" * 20                 # nome de página/visual gerado pelo Power BI Desktop
NOVO_VISUAL = ("definition", "pages", ID, "visuals", ID, "visual.json")
LETRAS = "PWQRSTUVXYZONMLKJIHG"   # ordem de preferência da unidade virtual (P de Power BI)
_SUBST = re.compile(r"^([A-Za-z]):\\:\s*=>\s*(.+?)\s*$")


@dataclass
class Medida:
    caminho: str              # o maior caminho, no formato do Windows
    tamanho: int
    raiz_real: bool           # True = medido com a pasta real do repositório (Windows)

    @property
    def excede(self) -> bool:
        return self.tamanho >= LIMITE


def texto_windows(path: Path | str) -> str:
    """Caminho como o Power BI Desktop o vê (sem o prefixo \\\\?\\ de caminhos longos)."""
    s = str(path)
    return s[len(LONG_PREFIX):] if s.startswith(LONG_PREFIX) else s


def raiz_windows(root: Path) -> tuple[str, bool]:
    """Pasta do repositório no Windows; fora dele, uma pasta típica para estimar."""
    if os.name == "nt":
        return texto_windows(root).rstrip("\\"), True
    return RAIZ_TIPICA, False


def _relativos(root: Path, dash: Path) -> list[tuple[str, ...]]:
    """Partes relativas à raiz de cada arquivo do PBIP + o próximo visual que o Desktop criaria."""
    pbi = dash / POWERBI
    out: list[tuple[str, ...]] = []
    if not pbi.is_dir():
        return out
    base = Path(texto_windows(root))
    for p in pbi.rglob("*"):
        if p.is_file():
            out.append(Path(texto_windows(p)).relative_to(base).parts)
    for report in pbi.glob("*.Report"):
        out.append(Path(texto_windows(report)).relative_to(base).parts + NOVO_VISUAL)
    return out


def medir(root: Path, dash: Path, raiz: str | None = None) -> Medida | None:
    """Maior caminho do PBIP de *dash*, no Windows, a partir de *raiz* (padrão: a pasta real)."""
    if raiz is None:
        raiz, real = raiz_windows(root)
    else:
        real = True
    rels = _relativos(root, dash)
    if not rels:
        return None
    maior = max((str(PureWindowsPath(raiz, *parts)) for parts in rels), key=len)
    return Medida(maior, len(maior), real)


def folga(root: Path, dash: Path) -> int:
    """Quantos caracteres a pasta do repositório ainda pode ter para este dashboard abrir."""
    rels = _relativos(root, dash)
    maior_rel = max((len(str(PureWindowsPath(*parts))) for parts in rels), default=0)
    return LIMITE - 1 - maior_rel        # -1 = a barra entre a raiz e o caminho relativo


def conselho() -> str:
    return (f"Use `pbw abrir`, que abre o projeto por uma unidade curta, ou clone o repositório numa pasta "
            f"curta, como {PASTA_CURTA} (guias/faq.md › caminho muito longo).")


# --------------------------------------------------------------------------- #
# Unidade virtual curta (subst) — só Windows
# --------------------------------------------------------------------------- #


def parse_subst(saida: str) -> dict[str, str]:
    """Saída do `subst` sem argumentos → {"P": r"C:\\pasta"}."""
    out: dict[str, str] = {}
    for linha in saida.splitlines():
        m = _SUBST.match(linha.strip())
        if m:
            out[m.group(1).upper()] = texto_windows(m.group(2))
    return out


def _mesma_pasta(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def escolher_letra(mapeadas: dict[str, str], alvo: str, em_uso: set[str]) -> tuple[str | None, bool]:
    """(letra, já_existia). Reaproveita uma unidade que já aponta para *alvo*."""
    for letra, pasta in sorted(mapeadas.items()):
        if _mesma_pasta(pasta, alvo):
            return letra, True
    for letra in LETRAS:
        if letra not in mapeadas and letra not in em_uso:
            return letra, False
    return None, False


def _subst(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["subst", *args], capture_output=True, text=True, errors="replace", check=False)


def unidades_em_uso() -> set[str]:
    listar = getattr(os, "listdrives", None)          # Python 3.12+ no Windows
    if listar is not None:
        try:
            return {d[0].upper() for d in listar()}
        except OSError:
            pass
    return {c for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")}


def unidade_curta(root: Path) -> str | None:
    """Garante uma unidade (ex.: P:) apontando para a pasta do repositório. Devolve 'P:' ou None."""
    if os.name != "nt":
        return None
    alvo = texto_windows(root).rstrip("\\")
    if alvo.startswith("\\\\"):
        return None                       # pasta de rede (UNC): o subst não aceita
    try:
        mapeadas = parse_subst(_subst().stdout)
        letra, existia = escolher_letra(mapeadas, alvo, unidades_em_uso())
        if letra is None:
            return None
        if not existia and _subst(f"{letra}:", alvo).returncode != 0:
            return None
    except OSError:
        return None
    return f"{letra}:"


def remover_unidade(letra: str) -> bool:
    if os.name != "nt":
        return False
    try:
        return _subst(f"{letra.rstrip(':')}:", "/D").returncode == 0
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# Pasta do repositório (pbw diagnostico)
# --------------------------------------------------------------------------- #


def pasta_sincronizada(root: Path) -> str | None:
    """Nome do serviço quando o repositório está dentro de uma pasta do OneDrive/SharePoint."""
    raiz = texto_windows(root)
    for var in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        pasta = os.environ.get(var)
        if pasta and os.path.normcase(raiz + os.sep).startswith(os.path.normcase(pasta.rstrip("\\/") + os.sep)):
            return "OneDrive/SharePoint"
    if "onedrive" in raiz.lower():
        return "OneDrive"
    return None
