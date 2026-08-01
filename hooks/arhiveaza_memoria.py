#!/usr/bin/env python3
"""
Stop hook — pune notitele de memorie sub istoric, dupa fiecare raspuns.

De ce exista. Folderul de memorie tine ce s-a invatat despre metoda de lucru a cabinetului,
o notita pe fisier, citite la inceputul fiecarei conversatii. Pana pe 1 august 2026 nu avea
istoric, deci o suprascriere gresita nu se putea anula. In ziua aceea o inlocuire de date
rulata prea larg a schimbat "30 iulie 2026" in "1 august 2026" si in notite care consemnau
evenimente petrecute chiar pe 30 iulie. Toolkit-ul s-a recuperat dintr-o comanda, fiind sub
git. Notitele au cerut refacere manuala, fisier cu fisier.

Ce face. Daca in folderul de memorie s-a schimbat ceva, comite. Mesajul spune ce fisiere s-au
atins, ca istoricul sa fie citibil fara diff.

Istoricul ramane LOCAL. Hook-ul nu adauga niciun remote si nu impinge nimic: notitele contin
metoda cabinetului si referiri la dosare.

Fail-open, ca restul hook-urilor: orice problema inseamna exit 0, fara sa blocheze raspunsul.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TIMP_MAX = 20


def _git(memorie: Path, *argumente) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(memorie), *argumente],
        capture_output=True, text=True, timeout=TIMP_MAX,
    )


def _folder_memorie() -> Path | None:
    """Calea vine din mediu cand exista, altfel se cade pe locul obisnuit."""
    din_mediu = os.environ.get("CLAUDE_MEMORY_DIR")
    if din_mediu and Path(din_mediu).is_dir():
        return Path(din_mediu)
    implicit = Path.home() / ".claude" / "projects"
    if not implicit.is_dir():
        return None
    candidati = [p for p in implicit.glob("*/memory") if (p / ".git").is_dir()]
    return candidati[0] if len(candidati) == 1 else None


def _rezumat(stare: str) -> str:
    """Numele fisierelor atinse, ca mesajul de commit sa se citeasca singur."""
    nume = []
    for linie in stare.splitlines():
        if len(linie) > 3:
            nume.append(Path(linie[3:].strip().strip('"')).stem)
    if not nume:
        return "notite actualizate"
    if len(nume) <= 3:
        return ", ".join(nume)
    return f"{', '.join(nume[:3])} si inca {len(nume) - 3}"


def main() -> int:
    try:
        sys.stdin.read()
    except Exception:
        pass

    try:
        memorie = _folder_memorie()
        if memorie is None or not (memorie / ".git").is_dir():
            return 0

        stare = _git(memorie, "status", "--porcelain")
        if stare.returncode != 0 or not stare.stdout.strip():
            return 0

        _git(memorie, "add", "-A")
        _git(memorie, "commit", "-q", "-m", f"memorie: {_rezumat(stare.stdout)}")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
