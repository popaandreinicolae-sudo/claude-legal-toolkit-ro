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

Si stergerea, din 1 august 2026
-------------------------------
In ziua aceea am generat un set de noua documente pentru un dosar de asociatie, apoi am
descoperit ca le datasem gresit. Le-am regenerat cu data buna si le-am STERS pe cele vechi,
ca sa nu ramana doua seturi in folder. Autorul lucrase intre timp in ele. Ce am sters nu se
mai poate recupera: stergerea din linia de comanda nu trece prin cosul de gunoi, arhiva de
livrari nu le prinsese, copiile-umbra nu exista si File History nu e pornit.

Hook-ul se uita atunci numai dupa copiere, mutare si scriere. Verbul de stergere nu era pe
lista lui, deci comanda a trecut nestingherita. Regula „nu sterg nimic" era scrisa in caiet
de zile intregi si nu a folosit la nimic, fiindca nimic nu o verifica.

Stergerea se trateaza mai sever decat suprascrierea. Suprascrierea lasa macar un fisier de
aceeasi marime, din care se vede ca ceva a existat acolo. Stergerea nu lasa nimic. De aceea
`-Force` NU lasa sa treaca o stergere, iar escape-ul e separat si scris in cuvinte,
--sterge-confirmat.

Ce face
-------
Ruleaza inaintea uneltelor Bash, Write si NotebookEdit. Cand tinta exista deja si e un
document, opreste executia si spune ce cale libera sa foloseasca in loc. Cand comanda contine
un verb de stergere care atinge un document sau dosarele autorului, o opreste si trimite spre
scrierea unei versiuni noi alaturi.

Forma cu conducta, `Get-ChildItem ... | Remove-Item $_.FullName`, nu poarta nicio cale
literala, deci nu poate fi verificata fisier cu fisier. Se opreste oricum, conservator, cand
atinge radacinile in care traiesc actele autorului.

Ce NU opreste
-------------
- fisierele din dosarele de lucru temporare, unde regenerarea e chiar scopul;
- codul si configurarile, adica .py, .json, .md si celelalte; acolo Edit e normal si
  istoricul sta in git;
- comenzile care cer expres suprascrierea, prin steagul --suprascrie;
- stergerile cerute de autor in cuvinte, marcate cu --sterge-confirmat.

Limita cunoscuta: o stergere facuta din interiorul unui script Python nu se vede de aici,
fiindca hook-ul citeste linia de comanda, nu codul rulat. De aceea regula ramane scrisa si
in skill-uri: livrarile proprii nu se sterg, se lasa pe loc si se scrie _v2 alaturi.

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

# Stergerea e mai rea decat suprascrierea: nu lasa nici macar un fisier de aceeasi marime
# din care sa se vada ca ceva a existat. De aceea verbele de stergere se trateaza separat,
# cu escape propriu, iar `-Force` NU le lasa sa treaca.
COMENZI_DE_STERGERE = ("rm", "del", "erase", "unlink", "rmdir", "rd",
                       "Remove-Item", "ri", "Clear-Content")

# Radacinile in care traiesc actele autorului. O stergere care le atinge se opreste chiar
# daca nu se poate citi calea exacta din comanda, fiindca forma cu conducta,
# `Get-ChildItem ... | Remove-Item $_.FullName`, nu poarta nicio cale literala.
RADACINI_PAZITE = ("d:\\clienti", "d:\\modele", "d:\\personale", "d:\\altele", "d:\\claude",
                   "\\onedrive\\", "\\documents\\")

# Escape propriu, diferit de cel de suprascriere. Trebuie scris in cuvinte, ca stergerea sa
# nu poata iesi dintr-un steag pus din obisnuinta.
CONFIRMARE_STERGERE = "--sterge-confirmat"


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


def _are_verb_de_stergere(cmd: str) -> bool:
    """Verbul de stergere se cauta pe pozitie de comanda, la inceput de segment sau dupa o
    conducta, ca sa nu se confunde cu un nume de fisier care contine 'rm' sau 'del'."""
    for bucata in re.split(r"&&|\|\||;|\||\n|\{", cmd):
        parti = bucata.strip().split()
        if parti and os.path.basename(parti[0]) in COMENZI_DE_STERGERE:
            return True
    return False


def _cai_literale(cmd: str) -> list:
    """Caile scrise pe fata in comanda, ghilimelate sau nu, cu extensie pazita."""
    gasite = []
    for m in re.finditer(r"[\"']([^\"']+)[\"']", cmd):
        gasite.append(m.group(1))
    for m in re.finditer(r"(?<![\"'\w])([A-Za-z]:\\[^\s\"';|]+)", cmd):
        gasite.append(m.group(1))
    return [g for g in gasite if Path(g).suffix.lower() in PAZITE]


def _problema_stergere(cmd: str):
    """Intoarce mesajul de oprire pentru o comanda de stergere, sau None."""
    if CONFIRMARE_STERGERE in cmd:
        return None
    if not _are_verb_de_stergere(cmd):
        return None

    jos = cmd.replace("/", "\\").lower()

    # 1. Cai scrise pe fata: se numeste fisierul si se spune ce s-ar pierde.
    for cale_text in _cai_literale(cmd):
        cale = Path(cale_text)
        if _e_liber(str(cale)):
            continue
        return (
            "Comanda ar sterge documentul %s.\n"
            "Documentele nu se sterg, niciodata, nici cele produse de mine. Un fisier sters "
            "din linia de comanda nu trece prin cosul de gunoi si nu lasa nimic in urma.\n"
            "Daca vrei sa scoti din drum o versiune, las-o pe loc si scrie versiunea noua "
            "alaturi, cu %s.\n"
            "Stergerea o cere autorul, in cuvinte, si abia atunci se adauga %s."
            % (cale, _urmatoarea(cale).name, CONFIRMARE_STERGERE)
        )

    # 2. Forma cu conducta, fara cale literala, dar care atinge dosarele autorului.
    atinge_dosarele = any(r in jos for r in RADACINI_PAZITE)
    atinge_documente = any(e in jos for e in PAZITE)
    if (atinge_dosarele or atinge_documente) and not _e_liber(jos):
        return (
            "Comanda contine un verb de stergere si atinge dosarele autorului, fara sa scrie "
            "pe fata ce anume sterge.\n"
            "Documentele nu se sterg. Cand vrei sa scoti din drum o livrare veche, las-o pe "
            "loc si scrie versiunea noua alaturi, cu sufix _v2.\n"
            "Daca stergerea e chiar ceruta de autor, scrie caile una cate una si adauga %s."
            % CONFIRMARE_STERGERE
        )
    return None


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
        cmd = intrare.get("command") or ""
        mesaj = _problema_stergere(cmd)
        if mesaj:
            sys.stderr.write(mesaj + "\n")
            return 2
        tinte = _tinte_din_comanda(cmd)

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
