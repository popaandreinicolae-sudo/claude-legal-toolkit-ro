#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cale_libera.py

Nu scrie niciodata peste un fisier care exista. Intoarce urmatoarea cale libera.

De ce exista
------------
Pe 30 iulie 2026 am copiat un document regenerat peste fisierul in care lucra autorul,
salvat de el cu 35 de minute inainte. Comanda a taiat fisierul la zero si a scris imediat
la loc, in aceleasi clustere tocmai eliberate, iar cei 214 KB noi au acoperit direct cei
223 KB ai lui. Nu exista copie de siguranta: Restore Points si File History nu erau
pornite, iar scrierea peste un fisier nu trece prin cosul de gunoi.

Cautarea in datele brute de pe amandoua discurile, pe doua formate, nu a mai gasit nimic.
Munca lui de o ora s-a pierdut definitiv.

Regula de acum: un fisier livrat nu ramane al meu. Din clipa in care autorul il deschide,
poate purta munca lui, iar data de pe disc e singurul semn. De aceea nu se scrie peste el
niciodata, indiferent cat de sigur pare ca "e acelasi document". Se scrie alaturi, cu
sufix de versiune.

Cum numeroteaza
---------------
    act.docx                     ->  act_v2.docx
    act_v2.docx                  ->  act_v3.docx
    act_v12.docx                 ->  act_v13.docx
    exceptie_v2_redline_AMZ.docx ->  exceptie_v3_redline_AMZ.docx

Marcajul de versiune se recunoaste oriunde in nume, nu doar la coada. Numele actelor
poarta de obicei si o eticheta dupa versiune, "_v2_redline_AMZ", iar adaugarea unui al
doilea marcaj la coada ar da "_v2_redline_AMZ_v2", ilizibil dupa cateva rulari.

Familia unui fisier e data de ce sta in jurul marcajului. "act_v1_autor" si
"act_v2_redline" sunt familii diferite, fiindca eticheta de dupa numar difera, deci fiecare
isi urmeaza propriul sir.

Numerotarea continua de la cea mai mare versiune gasita, nu de la prima libera, ca
stergerea unei versiuni intermediare sa nu duca la refolosirea unui nume.

Utilizare
---------
    from cale_libera import cale_libera
    iesire = cale_libera(args.output)      # intoarce Path, gata de scris

    python cale_libera.py act.docx         # arata ce cale ar alege
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Ultimul marcaj de versiune din nume, fie la coada, fie urmat de o eticheta.
_TIPAR_VERSIUNE = re.compile(r"^(?P<inainte>.*)_v(?P<nr>\d+)(?P<dupa>(?:_.*)?)$")


def _desparte(stem: str):
    """Intoarce (inainte, numar, dupa). Fara marcaj, numarul e 1 si `dupa` e gol."""
    m = _TIPAR_VERSIUNE.match(stem)
    if m:
        return m.group("inainte"), int(m.group("nr")), m.group("dupa")
    return stem, 1, ""


def _compune(inainte: str, nr: int, dupa: str, sufix: str) -> str:
    return "%s_v%d%s%s" % (inainte, nr, dupa, sufix)


def cale_libera(cale, tacut: bool = False) -> Path:
    """Prima cale care nu exista, pornind de la `cale`.

    Cand fisierul cerut nu exista, il intoarce neatins. Cand exista, cauta cea mai mare
    versiune din aceeasi familie si intoarce urmatoarea.
    """
    cale = Path(cale)
    if not cale.exists():
        return cale

    inainte, _, dupa = _desparte(cale.stem)
    dosar, sufix = cale.parent, cale.suffix

    maxim = 1
    for vecin in dosar.glob("*%s" % sufix):
        i2, nr2, d2 = _desparte(vecin.stem)
        if i2 == inainte and d2 == dupa:
            maxim = max(maxim, nr2)
        elif vecin.stem == inainte and not dupa:
            maxim = max(maxim, 1)

    nr = maxim + 1
    noua = dosar / _compune(inainte, nr, dupa, sufix)
    while noua.exists():
        nr += 1
        noua = dosar / _compune(inainte, nr, dupa, sufix)

    if not tacut:
        sys.stderr.write(
            "  %s exista deja si nu se suprascrie; scriu in %s\n" % (cale.name, noua.name))
    return noua


def adauga_optiune(parser):
    """Adauga --suprascrie la un ArgumentParser, pentru cazurile in care chiar se vrea."""
    parser.add_argument(
        "--suprascrie", action="store_true",
        help="scrie peste fisierul existent; implicit se scrie o versiune noua alaturi")
    return parser


def alege(cale, suprascrie: bool = False, tacut: bool = False) -> Path:
    """Calea de scris, tinand cont de steagul --suprascrie."""
    return Path(cale) if suprascrie else cale_libera(cale, tacut=tacut)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python cale_libera.py <cale>")
    for arg in sys.argv[1:]:
        print(cale_libera(arg, tacut=True))
