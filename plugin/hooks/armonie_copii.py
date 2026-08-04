#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
armonie_copii.py

Cele patru copii ale configuratiei spun acelasi lucru?

    1. ~/.claude/skills si /agents   ce ruleaza in Claude Code, sursa de adevar
    2. repo/skills si /agents        copia versionata, pentru citit si pentru istoric
    3. repo/plugin/...               artefactul generat, cel care pleaca in Desktop
    4. dist/toolkit-juridic-ro.zip   arhiva din care se reinstaleaza

De ce exista
------------
Skill-ul de verificare cerea de mult sa se controleze ca "skill-urile instalate si cele
din repo nu au derapat unele fata de altele", fara sa aiba cu ce. Pe 30 iulie 2026
regulile despre sintact traiau numai in copia instalata, iar in repo statea forma veche,
si nimeni nu a vazut pana cand a dat gres altceva.

Ce nu e derapaj
---------------
Sfarsitul de linie. Git normalizeaza CRLF la scriere, deci acelasi text are alta marime
pe disc in repo fata de ~/.claude. Comparatia se face pe continut normalizat.

Materialul care exista numai in repo. Depozitul tine si skill-urile oficiale Anthropic,
in `_anthropic_official`, si o biblioteca de subagenti neinstalati. Se compara numai
numele care exista in amandoua locurile.

    python armonie_copii.py
"""
from __future__ import annotations

import hashlib
import os
import sys
import zipfile
from pathlib import Path

ACASA = Path(os.path.expanduser("~")) / ".claude"
REPO = Path(os.path.expanduser("~")) / "claude-legal-toolkit-ro"
ARHIVA = REPO / "dist" / "toolkit-juridic-ro.zip"

IGNORATE = ("__pycache__", ".pyc", "_anthropic_official")


def _sarit(cale: str) -> bool:
    return any(x in cale for x in IGNORATE)


def _amprenta(octeti: bytes) -> str:
    """Continut, fara sfarsitul de linie."""
    return hashlib.sha256(octeti.replace(b"\r\n", b"\n")).hexdigest()[:12]


def din_dosar(radacina: Path) -> dict:
    if not radacina.is_dir():
        return {}
    out = {}
    for f in radacina.rglob("*"):
        rel = f.relative_to(radacina).as_posix()
        if f.is_file() and not _sarit(rel):
            out[rel] = _amprenta(f.read_bytes())
    return out


def din_arhiva(cale: Path) -> dict:
    if not cale.exists():
        return {}
    with zipfile.ZipFile(cale) as z:
        nume = [i.filename for i in z.infolist() if not i.is_dir()]
        comun = os.path.commonprefix(nume)
        prefix = comun[:comun.rfind("/") + 1] if "/" in comun else ""
        return {n[len(prefix):]: _amprenta(z.read(n)) for n in nume if not _sarit(n)}


def compara(eticheta: str, a: dict, b: dict, nume_a: str, nume_b: str,
            doar_comune: bool = False) -> int:
    if doar_comune:
        comune = set(a) & set(b)
        a = {k: v for k, v in a.items() if k in comune}
        b = {k: v for k, v in b.items() if k in comune}
    doar_a = sorted(set(a) - set(b))
    doar_b = sorted(set(b) - set(a))
    difera = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    abateri = len(doar_a) + len(doar_b) + len(difera)
    print("[%s] %-38s %d fisiere" % ("OK " if not abateri else "ESEC", eticheta, len(a)))
    for k in doar_a[:8]:
        print("       doar in %s: %s" % (nume_a, k))
    for k in doar_b[:8]:
        print("       doar in %s: %s" % (nume_b, k))
    for k in difera[:8]:
        print("       continut diferit: %s" % k)
    return abateri


def main() -> int:
    abateri = 0
    for dosar in ("skills", "agents"):
        instalat = din_dosar(ACASA / dosar)
        abateri += compara("%s: instalat vs plugin" % dosar, instalat,
                           din_dosar(REPO / "plugin" / dosar), "~/.claude", "plugin")
        abateri += compara("%s: instalat vs repo" % dosar, instalat,
                           din_dosar(REPO / dosar), "~/.claude", "repo",
                           doar_comune=True)
    abateri += compara("arhiva dist vs plugin", din_arhiva(ARHIVA),
                       din_dosar(REPO / "plugin"), "zip", "plugin")

    print()
    if abateri:
        print("REZULTAT: %d abateri. Ruleaza `python tools/build_plugin.py` in depozit, "
              "apoi commit si push." % abateri)
        return 1
    print("REZULTAT: cele patru copii spun acelasi lucru")
    return 0


if __name__ == "__main__":
    sys.exit(main())
