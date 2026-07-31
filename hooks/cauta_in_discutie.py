# -*- coding: utf-8 -*-
"""Cauta un termen in transcrierea unei discutii Claude Code.

Discutiile stau ca .jsonl in ~/.claude/projects/<dosar>/. Fara argument de fisier,
se ia cea mai recent modificata din dosarul de proiect curent.

  python cauta_in_discutie.py "raporturi comerciale"
  python cauta_in_discutie.py "art. 136" --tot        # si mesajele mele, nu doar ale lui
  python cauta_in_discutie.py "Buhagiar" --fisier X.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

RADACINA = Path(os.path.expanduser("~")) / ".claude" / "projects"


def _fara_diacritice(s: str) -> str:
    tab = str.maketrans({"ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
                         "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T"})
    return s.translate(tab)


def _text(mesaj) -> str:
    """Continutul unui mesaj, oricare ar fi forma lui."""
    c = mesaj.get("content")
    if isinstance(c, str):
        return c
    bucati = []
    for parte in (c or []):
        if not isinstance(parte, dict):
            continue
        if parte.get("type") == "text":
            bucati.append(parte.get("text", ""))
        elif parte.get("type") == "tool_result":
            v = parte.get("content")
            if isinstance(v, str):
                bucati.append(v)
    return "\n".join(bucati)


def alege_fisier() -> Path | None:
    candidate = list(RADACINA.glob("*/*.jsonl"))
    return max(candidate, key=lambda p: p.stat().st_mtime) if candidate else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Cauta in transcrierea discutiei.")
    ap.add_argument("termen")
    ap.add_argument("--fisier", help="calea unui .jsonl anume")
    ap.add_argument("--tot", action="store_true", help="cauta si in raspunsurile asistentului")
    ap.add_argument("--context", type=int, default=180, help="caractere in jurul potrivirii")
    a = ap.parse_args(argv)

    cale = Path(a.fisier) if a.fisier else alege_fisier()
    if not cale or not cale.exists():
        print("nu am gasit nicio transcriere in %s" % RADACINA)
        return 1

    tinta = _fara_diacritice(a.termen).lower()
    gasite = 0
    for nr, linie in enumerate(cale.open(encoding="utf-8", errors="replace"), 1):
        try:
            d = json.loads(linie)
        except ValueError:
            continue
        m = d.get("message") or {}
        rol = m.get("role") or d.get("type") or ""
        if not a.tot and rol != "user":
            continue
        t = _text(m)
        plat = _fara_diacritice(t).lower()
        for poz in [x.start() for x in re.finditer(re.escape(tinta), plat)]:
            gasite += 1
            i, j = max(0, poz - a.context), poz + len(tinta) + a.context
            extras = " ".join(t[i:j].split())
            print("\n[%s] linia %d" % (rol, nr))
            print("  ...%s..." % extras)
    print("\n%d potriviri in %s" % (gasite, cale.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
