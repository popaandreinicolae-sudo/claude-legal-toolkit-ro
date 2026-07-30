#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fara_suprascriere.py

Opreste orice comanda care ar scrie peste un document existent.

De ce exista
------------
Pe 30 iulie 2026 am regenerat un act si l-am copiat peste fisierul din dosarul cauzei,
cu o comanda obisnuita de copiere. Fisierul purta insa modificarile autorului, salvate cu
35 de minute inainte. Copierea a taiat fisierul la zero si a scris imediat la loc, in
aceleasi clustere tocmai eliberate, iar documentul nou de 214 KB a acoperit direct cei
223 KB ai lui.

Nu a mai fost nimic de recuperat. Restore Points si File History nu erau pornite, scrierea
peste un fisier nu trece prin cosul de gunoi, recuperarea automata a Word fusese stearsa
chiar de salvarea lui, iar cautarea in datele brute de pe amandoua discurile, pe doua
formate, a intors numai documente straine. O ora de munca s-a pierdut definitiv.

Instructiunea scrisa nu e de ajuns, fiindca greseala se face intr-o comanda de o linie,
in mijlocul altei treburi. Verificarea trebuie sa fie deterministica.

Ce face
-------
Ruleaza inaintea uneltelor Bash, Write si NotebookEdit. Cand tinta exista deja si e un
document, opreste executia si spune ce cale libera sa foloseasca in loc.

Ce NU opreste
-------------
- fisierele din dosarele de lucru temporare, unde regenerarea e chiar scopul;
- codul si configurarile, adica .py, .json, .md si celelalte; acolo Edit e normal si
  istoricul sta in git;
- comenzile care cer expres suprascrierea, prin steagul --suprascrie.

Comutator: FARA_SUPRASCRIERE_OFF=1 il dezactiveaza.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

# Extensiile pentru care pierderea e ireversibila si nu exista istoric.
PAZITE = {".docx", ".doc", ".rtf", ".odt", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt"}

# Locuri unde regenerarea peste acelasi nume e normala si de dorit.
LIBERE = ("\\temp\\", "/temp/", "\\tmp\\", "/tmp/", "scratchpad",
          "\\appdata\\local\\temp", "\\.cache\\", "/.cache/")

COMENZI_DE_SCRIERE = ("cp", "copy", "mv", "move", "Copy-Item", "Move-Item", "robocopy", "xcopy")


def _e_liber(cale: str) -> bool:
    jos = cale.replace("/", "\\").lower()
    return any(m.replace("/", "\\") in jos for m in LIBERE)


def _urmatoarea(cale: Path) -> Path:
    """Prima cale libera. Aceeasi regula ca in cale_libera.py din skill-uri.

    Marcajul de versiune se recunoaste oriunde in nume, nu doar la coada, fiindca actele
    poarta si o eticheta dupa numar, "_v2_redline_AMZ". Un al doilea marcaj adaugat la
    coada ar da "_v2_redline_AMZ_v2", ilizibil dupa cateva rulari.
    """
    tipar = re.compile(r"^(?P<inainte>.*)_v(?P<nr>\d+)(?P<dupa>(?:_.*)?)$")

    def desparte(stem):
        m = tipar.match(stem)
        return (m.group("inainte"), int(m.group("nr")), m.group("dupa")) if m else (stem, 1, "")

    inainte, _, dupa = desparte(cale.stem)
    maxim = 1
    for vecin in cale.parent.glob("*%s" % cale.suffix):
        i2, nr2, d2 = desparte(vecin.stem)
        if i2 == inainte and d2 == dupa:
            maxim = max(maxim, nr2)
        elif vecin.stem == inainte and not dupa:
            maxim = max(maxim, 1)
    nr = maxim + 1
    noua = cale.parent / ("%s_v%d%s%s" % (inainte, nr, dupa, cale.suffix))
    while noua.exists():
        nr += 1
        noua = cale.parent / ("%s_v%d%s%s" % (inainte, nr, dupa, cale.suffix))
    return noua


def _tinte_din_comanda(cmd: str) -> list:
    """Caile spre care scrie o comanda de copiere sau mutare."""
    if "--suprascrie" in cmd or "-Force" in cmd:
        return []
    tinte = []
    for bucata in re.split(r"&&|\|\||;|\n", cmd):
        bucata = bucata.strip()
        if not bucata:
            continue
        try:
            parti = shlex.split(bucata, posix=True)
        except ValueError:
            parti = bucata.split()
        if not parti:
            continue
        nume = os.path.basename(parti[0])
        if nume not in COMENZI_DE_SCRIERE:
            continue
        argumente = [p for p in parti[1:] if not p.startswith("-")]
        if len(argumente) >= 2:
            tinte.append(argumente[-1])
        # redirectare simpla, "> fisier"
    for m in re.finditer(r">\s*\"?([^\"\s>|]+\.[A-Za-z0-9]{2,5})\"?", cmd):
        tinte.append(m.group(1))
    return tinte


def _problema(tinta: str):
    """Intoarce mesajul de oprire, sau None cand scrierea e in regula."""
    if not tinta:
        return None
    cale = Path(tinta.strip().strip('"').strip("'"))
    if cale.suffix.lower() not in PAZITE:
        return None
    if _e_liber(str(cale)):
        return None
    if cale.is_dir():
        return None
    if not cale.exists():
        return None
    noua = _urmatoarea(cale)
    return (
        "Fisierul %s exista deja si nu se suprascrie.\n"
        "Din clipa in care autorul l-a deschis, poate purta munca lui, iar scrierea peste "
        "el nu se poate desface: nu trece prin cosul de gunoi si nu exista copie.\n"
        "Scrie in %s.\n"
        "Daca inlocuirea e chiar ceruta, spune-o explicit sau adauga --suprascrie."
        % (cale, noua.name)
    )


def main() -> int:
    if os.environ.get("FARA_SUPRASCRIERE_OFF") == "1":
        return 0
    try:
        date = json.load(sys.stdin)
    except Exception:
        return 0

    unealta = date.get("tool_name") or ""
    intrare = date.get("tool_input") or {}

    tinte = []
    if unealta in ("Write", "NotebookEdit"):
        tinte = [intrare.get("file_path") or intrare.get("notebook_path") or ""]
    elif unealta in ("Bash", "PowerShell"):
        tinte = _tinte_din_comanda(intrare.get("command") or "")

    for t in tinte:
        mesaj = _problema(t)
        if mesaj:
            # exit 2 opreste unealta si trimite mesajul inapoi la model
            sys.stderr.write(mesaj + "\n")
            return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail-open: un hook stricat nu blocheaza munca.
        sys.exit(0)
