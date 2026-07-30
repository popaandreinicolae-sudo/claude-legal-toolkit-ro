#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contradictii.py

Cauta reguli care se bat cap in cap intre locurile unde exista reguli.

De ce exista
------------
Pe 30 iulie 2026 autorul a cerut ca "reprezinta" si "constituie" sa fie pastrate, ca
registru juridic. Regula 12 din anti-ai-tone cerea exact opusul, inlocuirea lor cu "este".
Mai rau, textul injectat la fiecare mesaj al lui continea, cuvant cu cuvant, contrariul
instructiunii lui. Conflictul a stat acolo ore intregi si a fost gasit din intamplare, in
timpul unui audit cerut din alt motiv.

Regulile stau acum in cinci feluri de locuri: caietul, CLAUDE.md, instructiunile
serverelor MCP, skill-urile si preferintele de cont. Nimeni nu se uita daca isi raspund.

Ce face si ce nu
----------------
Nu hotaraste cine are dreptate si nu repara nimic. Aduna, din toate sursele, frazele care
dau o instructiune despre acelasi termen, si le pune fata in fata cand polaritatea lor
difera: una spune "se pastreaza", alta "se inlocuieste". Verdictul il da autorul.

Semnalarile sunt candidate, nu certitudini. Un strat care ar decide singur ar corecta
intr-o zi tocmai regula autorului.

Utilizare
---------
    python contradictii.py            # raport citibil
    python contradictii.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ACASA = Path(os.path.expanduser("~"))
REPO = ACASA / "claude-legal-toolkit-ro"

# Cuvintele care arata ca fraza da o instructiune, impartite pe polaritate.
PASTREAZA = ("se pastreaza", "pastreaza", "se prefera", "prefera", "favorizat", "foloseste",
             "se foloseste", "se scrie", "obligatoriu", "mereu", "se aduce", "se cauta",
             "ramane", "raman", "se mentine")
INLOCUIESTE = ("nu se", "nu folosi", "interzis", "zero ", "elimina", "se inlocuieste",
               "inlocuieste", "evita", "niciodata", "nu mai", "devine", "->", "→")


def surse() -> list:
    """[(eticheta, cale, text)] pentru fiecare loc in care exista reguli."""
    out = []

    def adauga(eticheta, cale):
        p = Path(cale)
        if p.is_file():
            try:
                out.append((eticheta, str(p), p.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass

    adauga("CLAUDE.md", ACASA / ".claude" / "CLAUDE.md")
    adauga("preferinte Desktop", REPO / "config" / "preferinte-claude-desktop.md")

    for d in (ACASA / ".claude" / "projects").glob("*/memory"):
        for f in sorted(d.glob("*.md")):
            adauga("caiet: %s" % f.stem, f)

    for f in sorted((ACASA / ".claude" / "skills").glob("*/SKILL.md")):
        adauga("skill: %s" % f.parent.name, f)

    for f in sorted(REPO.glob("mcp-servers/**/server.py")):
        adauga("MCP: %s" % f.parent.name, f)
    persona = Path("D:/PYTHON DEVELOPMENT PROJ/persona-adrian-zamfir/server/app.py")
    adauga("MCP: persona-adrian-zamfir", persona)

    for n in ("prompt_injection_hook.py", "detect_ai_tone.py", "ai_tone_hook.py"):
        adauga("hook: %s" % n, REPO / "hooks" / n)
    return out


def fraze(text: str) -> list:
    """Frazele care par sa dea o instructiune."""
    brut = re.split(r"(?<=[.!?;])\s+|\n", text)
    out = []
    for f in brut:
        f = " ".join(f.split())
        if 12 <= len(f) <= 400:
            out.append(f)
    return out


def termeni_sub_instructiune(fraza: str) -> set:
    """Termenii citati sau evidentiati intr-o fraza de instructiune."""
    t = set()
    for m in re.finditer(r"[„\"'`]([^„\"'`\n]{3,40})[”\"'`]", fraza):
        t.add(m.group(1).strip().lower())
    return {x for x in t if x and not x.isdigit() and x not in PREA_COMUNE}


# Negarea unui verb de inlocuire inseamna pastrare, nu inlocuire. Fara regula asta,
# "reprezinta si constituie NU se schimba" era citit drept instructiune de inlocuire, adica
# exact pe dos, si producea doua semnalari false din trei la prima rulare.
NEGARE_DE_INLOCUIRE = re.compile(
    r"\bnu\s+(?:se\s+|mai\s+)?(?:schimb|inlocui|înlocui|corect|modific|elimin|scoat)", re.I)

# Cuvinte prea comune ca sa fie termeni sub instructiune. "este" apare in fiecare regula de
# copula ca tinta a inlocuirii, si aduna tot ce contine cuvantul.
PREA_COMUNE = {"este", "sunt", "e", "are", "nu", "si", "sau", "x", "y", "z"}


def polaritate(fraza: str) -> str | None:
    jos = fraza.lower()
    if NEGARE_DE_INLOCUIRE.search(jos):
        return "pentru"
    neg = any(m in jos for m in INLOCUIESTE)
    poz = any(m in jos for m in PASTREAZA)
    if neg and not poz:
        return "impotriva"
    if poz and not neg:
        return "pentru"
    if neg and poz:
        return "amestecat"
    return None


def cauta() -> list:
    """Grupurile de fraze care vorbesc despre acelasi termen cu polaritati diferite."""
    pe_termen: dict = {}
    for eticheta, cale, text in surse():
        for f in fraze(text):
            pol = polaritate(f)
            if pol in (None, "amestecat"):
                continue
            for termen in termeni_sub_instructiune(f):
                pe_termen.setdefault(termen, []).append(
                    {"sursa": eticheta, "cale": cale, "polaritate": pol, "fraza": f})

    semnalari = []
    for termen, intrari in sorted(pe_termen.items()):
        surse_distincte = {i["sursa"] for i in intrari}
        polaritati = {i["polaritate"] for i in intrari}
        if len(surse_distincte) < 2 or len(polaritati) < 2:
            continue
        semnalari.append({"termen": termen, "intrari": intrari})
    return semnalari


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Reguli care se contrazic intre surse")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    s = cauta()
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return 0

    print("Am citit %d surse de reguli.\n" % len(surse()))
    if not s:
        print("Nicio contradictie candidata.")
        return 0
    print("%d termen(i) cu instructiuni de sens opus, de judecat de autor:\n" % len(s))
    for x in s:
        print("=" * 74)
        print("TERMEN: %s" % x["termen"])
        for i in x["intrari"][:6]:
            print("  [%s] %-10s %s" % (i["polaritate"][:9], i["sursa"][:22], i["fraza"][:130]))
    print("\nSemnalarile sunt candidate, nu verdicte. Le judeca autorul.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
