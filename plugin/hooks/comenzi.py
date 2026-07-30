#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comenzi.py

Spune ce comenzi are autorul de tastat si ce se aprinde singur.

De ce se citeste din skill-uri, nu dintr-o lista scrisa de mana
---------------------------------------------------------------
Lista de unelte a serverului persona era scrisa de mana si a ramas in urma de doua ori, cu
patru unelte cu tot. Un ajutor care minte e mai rau decat lipsa lui, asa ca aici nu se
scrie nimic pe de rost: se citesc skill-urile instalate si se clasifica dupa cum se declara
ele insele.

Un skill al carui descriere spune "Invocata prin /nume" e o comanda pe care o tastezi.
Restul se aprind singure, la ce lucrezi, si nu au ce cauta intr-un ajutor.

Utilizare
---------
    python comenzi.py
    python comenzi.py --toate     # si cele automate
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SKILLS = Path(os.path.expanduser("~")) / ".claude" / "skills"

# Fluxul de lucru, singurul lucru scris aici de mana, fiindca nu se poate deduce din
# fisiere. Se tine scurt tocmai ca sa nu ramana in urma.
FLUX = [
    ("dimineata", "/revizuire", "vezi ce am schimbat eu in documentele pe care mi le-ai dat"),
    ("dupa modificari in toolkit", "/verificare", "piesele se calca intre ele?"),
]


def _frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    capat = text.find("\n---", 3)
    if capat < 0:
        return {}
    cap = {}
    m = re.search(r"^name:\s*(.+)$", text[3:capat], re.M)
    if m:
        cap["name"] = m.group(1).strip()
    m = re.search(r"description:\s*\|?\s*\n?((?:.|\n)*?)(?=\n\w+:|\Z)", text[3:capat])
    if m:
        cap["description"] = " ".join(m.group(1).split())
    return cap


def skilluri() -> list:
    out = []
    if not SKILLS.is_dir():
        return out
    for d in sorted(SKILLS.iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        try:
            cap = _frontmatter(f.read_text(encoding="utf-8"))
        except OSError:
            continue
        nume = cap.get("name") or d.name
        desc = cap.get("description", "")
        # Se declara singur drept comanda de tastat?
        tastata = bool(re.search(r"[Ii]nvocat[ăa]\s+prin\s*/", desc))
        out.append({"nume": nume, "descriere": desc, "tastata": tastata})
    return out


def _scurt(desc: str, n: int = 92) -> str:
    """Prima propozitie a descrierii, fara lista de cuvinte de declansare."""
    d = re.split(r"(?<=[.!?])\s", desc)[0] if desc else ""
    d = re.sub(r"\s*Invocat[ăa].*$", "", d).strip(" .")
    return (d[:n] + "…") if len(d) > n else d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Comenzile toolkit-ului")
    ap.add_argument("--toate", action="store_true", help="arata si skill-urile automate")
    args = ap.parse_args(argv)

    lista = skilluri()
    tastate = [s for s in lista if s["tastata"]]
    automate = [s for s in lista if not s["tastata"]]

    print("COMENZILE PE CARE LE TASTEZI\n")
    if not tastate:
        print("  niciuna gasita; verifica daca skill-urile sunt instalate in %s" % SKILLS)
    for s in tastate:
        print("  /%-13s %s" % (s["nume"], _scurt(s["descriere"])))

    print("\nCAND SE FOLOSESC\n")
    for cand, comanda, ce in FLUX:
        print("  %-26s %-13s %s" % (cand, comanda, ce))

    print("\n%d skill-uri se aprind singure, la ce lucrezi. Nu le tastezi." % len(automate))
    if args.toate:
        for s in automate:
            print("  %-28s %s" % (s["nume"], _scurt(s["descriere"], 70)))
    else:
        print("Le vezi cu:  python comenzi.py --toate")

    print("\nOricand poti tasta / in Claude Code si iti apare lista completa,")
    print("sau imi poti spune in cuvinte ce vrei, fara sa stii numele comenzii.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
