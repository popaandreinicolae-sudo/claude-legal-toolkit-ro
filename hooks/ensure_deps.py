#!/usr/bin/env python3
"""
SessionStart hook — se asigura ca dependintele hook-urilor sunt instalate.

Inlocuieste comanda shell `python -c "import ..." 2>nul || pip install ... 2>nul`,
care presupunea cmd.exe. Rulata sub Git Bash, redirectarea `2>nul` creeaza un fisier
gol numit "nul" in directorul de lucru, iar suprimarea erorilor nu functioneaza.

Nu scrie nimic cand totul e instalat. Exit 0 mereu (fail-open, ca restul hook-urilor).
"""

import importlib.util
import subprocess
import sys

# modul de import -> pachet pip
DEPS = {
    'docx': 'python-docx',
    'httpx': 'httpx',
    'bs4': 'beautifulsoup4',
    'lxml': 'lxml',
}


def main() -> int:
    try:
        missing = [pkg for mod, pkg in DEPS.items() if importlib.util.find_spec(mod) is None]
    except Exception:
        return 0
    if not missing:
        return 0
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--quiet',
             '--disable-pip-version-check', *missing],
            capture_output=True,
            timeout=120,
        )
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
