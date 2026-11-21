#!/usr/bin/env python3
"""Power BI Workspaces CLI entry point.

    pbw --help                 (atalho na raiz: pbw.cmd no Windows, ./pbw no macOS/Linux/Git Bash)
    python _sistema/pbw.py --help

Zero dependencies (Python 3.11+ standard library). No network access. No telemetry.
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from workspaces.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
