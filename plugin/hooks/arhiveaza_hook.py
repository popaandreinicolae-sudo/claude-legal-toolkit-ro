#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arhiveaza_hook.py

Pune in arhiva de livrari documentele pe care le produc si le duc in dosarele autorului.

Ruleaza dupa uneltele care scriu, PostToolUse. Perechea lui, fara_suprascriere.py, ruleaza
inainte si opreste scrierea peste un document existent; acesta ruleaza dupa si pastreaza
copia de referinta a ce a plecat.

Arhivarea nu poate sta numai in scripturile de generare, fiindca livrarea se face de cele
mai multe ori printr-o copiere obisnuita, iar acolo niciun script al nostru nu mai e
implicat. Exact asa a plecat documentul din 30 iulie 2026.

Discriminatorul
---------------
Se arhiveaza numai copierile care PORNESC din dosarul meu de lucru. Cand mut un document
al autorului dintr-un dosar al lui in altul, nu se arhiveaza nimic: nu am fata de ce sa il
compar, iar arhiva ar deveni o gramada de acte de client stand in afara dosarelor lor.

Nu blocheaza nimic si nu scrie nimic in dosarele autorului. Fail-open.
Comutator: ARHIVA_LIVRARI_OFF=1.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

COPIERI = ("cp", "copy", "mv", "move", "Copy-Item", "Move-Item", "robocopy", "xcopy")


def _absolut(cale: str, radacina: str) -> str:
    """Calea, adusa la forma absoluta fata de dosarul in care a rulat comanda.

    Comenzile se scriu de obicei cu sursa relativa, "cp gata.docx D:/Dosar/act.docx".
    Fara radacina, discriminatorul nu poate vedea ca sursa e in dosarul meu de lucru si
    rateaza tocmai livrarile. Verificat pe cazul real, la prima proba a hook-ului.
    """
    cale = (cale or "").strip().strip('"').strip("'")
    if not cale:
        return cale
    p = os.path.expanduser(cale)
    if os.path.isabs(p) or re.match(r"^[A-Za-z]:", p):
        return p
    return os.path.normpath(os.path.join(radacina or os.getcwd(), p))


def perechi_din_comanda(cmd: str) -> list:
    """[(sursa, tinta)] pentru fiecare copiere sau mutare din comanda."""
    perechi = []
    for bucata in re.split(r"&&|\|\||;|\n", cmd or ""):
        bucata = bucata.strip()
        if not bucata:
            continue
        try:
            parti = shlex.split(bucata, posix=True)
        except ValueError:
            parti = bucata.split()
        if not parti or os.path.basename(parti[0]) not in COPIERI:
            continue
        argumente = [p for p in parti[1:] if not p.startswith("-")]
        if len(argumente) >= 2:
            perechi.append((argumente[-2], argumente[-1]))
    return perechi


def main() -> int:
    if os.environ.get("ARHIVA_LIVRARI_OFF") == "1":
        return 0
    try:
        date = json.load(sys.stdin)
    except Exception:
        return 0

    if (date.get("tool_name") or "") not in ("Bash", "PowerShell"):
        return 0
    perechi = perechi_din_comanda((date.get("tool_input") or {}).get("command") or "")
    if not perechi:
        return 0

    radacina = date.get("cwd") or os.getcwd()

    try:
        import arhiva_livrari as al
    except ImportError:
        return 0

    for sursa, tinta in perechi:
        sursa = _absolut(sursa, radacina)
        tinta = _absolut(tinta, radacina)
        try:
            if not al.e_livrare(tinta, sursa):
                continue
            intrare = al.adauga(tinta, motiv="livrare")
        except Exception:
            continue
        if intrare:
            # Mesajul ajunge la model, ca sa stie ca exista o copie de referinta.
            sys.stderr.write("  copie de referinta pastrata: %s\n" % intrare["copie"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
