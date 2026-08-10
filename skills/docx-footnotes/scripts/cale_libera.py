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

Verificarea de amprenta
-----------------------
Nu scrie peste fisier, dar pana pe 10 august 2026 asta nu era de ajuns: numele
urmator se alegea corect, insa continutul versiunii noi venea intotdeauna din JSON-ul
dat scriptului, niciodata din ce era pe disc. Cand autorul deschidea versiunea
precedenta si scria in ea, iar cineva cerea apoi "mai fa o versiune, cu adaugirile
astea", regenerarea din sursa arunca in tacere exact ce scrisese el, fiindca
niciun cod nu se uita inapoi la fisierul de pe disc, doar la numele lui.

De aceea `cale_libera` retine, langa fiecare fisier pe care il scrie, o amprenta,
data modificarii si marimea, intr-un `.cale_libera_stare.json` din acelasi dosar.
Inainte sa aleaga urmatoarea versiune, verifica cea mai recenta versiune de pe disc
fata de amprenta ei. Cand nu se potrivesc, sau cand nu exista deloc amprenta, adica
fisierul n-a fost scris niciodata de aceasta unealta, ridica `VersiuneModificata` in
loc sa regenereze orbeste. Cine cheama trebuie fie sa deschida fisierul si sa
construiasca peste continutul lui, fie sa treaca explicit `baza_verificata=True`
dupa ce s-a asigurat ca nu s-a pierdut nimic.

Utilizare
---------
    from cale_libera import cale_libera, inregistreaza, VersiuneModificata
    iesire = cale_libera(args.output)      # intoarce Path, gata de scris
    ...
    doc.save(str(iesire))
    inregistreaza(iesire)                  # dupa fiecare salvare reusita

    python cale_libera.py act.docx         # arata ce cale ar alege
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Ultimul marcaj de versiune din nume, fie la coada, fie urmat de o eticheta.
_TIPAR_VERSIUNE = re.compile(r"^(?P<inainte>.*)_v(?P<nr>\d+)(?P<dupa>(?:_.*)?)$")

_STARE_NUME = ".cale_libera_stare.json"
_TOLERANTA_MTIME = 1.0  # secunde; NTFS rotunjeste uneori la cateva sute de ms


class VersiuneModificata(RuntimeError):
    """Cea mai recenta versiune din familie a fost atinsa pe disc de la generare."""


def _desparte(stem: str):
    """Intoarce (inainte, numar, dupa). Fara marcaj, numarul e 1 si `dupa` e gol."""
    m = _TIPAR_VERSIUNE.match(stem)
    if m:
        return m.group("inainte"), int(m.group("nr")), m.group("dupa")
    return stem, 1, ""


def _compune(inainte: str, nr: int, dupa: str, sufix: str) -> str:
    return "%s_v%d%s%s" % (inainte, nr, dupa, sufix)


def _cale_stare(dosar: Path) -> Path:
    return dosar / _STARE_NUME


def _incarca_stare(dosar: Path) -> dict:
    fisier = _cale_stare(dosar)
    if not fisier.exists():
        return {}
    try:
        return json.loads(fisier.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def inregistreaza(cale) -> None:
    """Retine amprenta fisierului tocmai scris, ca urmatoarea versiune sa poata sti
    daca autorul l-a atins intre timp. Se cheama dupa fiecare `doc.save()` reusit."""
    cale = Path(cale)
    if not cale.exists():
        return
    stat = cale.stat()
    stare = _incarca_stare(cale.parent)
    stare[cale.name] = {"mtime": stat.st_mtime, "marime": stat.st_size}
    try:
        _cale_stare(cale.parent).write_text(
            json.dumps(stare, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # amprenta e o plasa de siguranta, nu un pas care trebuie sa reuseasca


def _verifica_drift(cale: Path) -> str | None:
    """Intoarce None cand fisierul nu s-a schimbat fata de generare, altfel motivul."""
    if not cale.exists():
        return None
    stat = cale.stat()
    stare = _incarca_stare(cale.parent).get(cale.name)
    if stare is None:
        return ("%s nu are amprenta de generare, semn ca nu a fost scris de aceasta "
                "unealta sau ca amprenta s-a pierdut" % cale.name)
    if (stat.st_size != stare.get("marime")
            or abs(stat.st_mtime - stare.get("mtime", 0)) > _TOLERANTA_MTIME):
        return ("%s a fost modificat pe disc dupa ce a fost generat (data sau marimea "
                "nu mai corespund amprentei)" % cale.name)
    return None


def cale_libera(cale, tacut: bool = False, baza_verificata: bool = False) -> Path:
    """Prima cale care nu exista, pornind de la `cale`.

    Cand fisierul cerut nu exista, il intoarce neatins. Cand exista, cauta cea mai mare
    versiune din aceeasi familie si intoarce urmatoarea.

    Inainte sa intoarca acea versiune urmatoare, verifica daca cea mai recenta versiune
    de pe disc mai corespunde cu ce a scris unealta ultima data. Cand nu corespunde,
    ridica `VersiuneModificata` in loc sa aleaga tacut urmatorul nume, fiindca cine
    genereaza actul din JSON, nu din fisierul de pe disc, i-ar arunca autorului munca
    fara sa se vada nimic. `baza_verificata=True` sare peste verificare, pentru cazul in
    care chemarea a citit deja fisierul si a dus mai departe ce era nou in el.
    """
    cale = Path(cale)
    if not cale.exists():
        return cale

    inainte, _, dupa = _desparte(cale.stem)
    dosar, sufix = cale.parent, cale.suffix

    maxim, ultima = 1, cale
    for vecin in dosar.glob("*%s" % sufix):
        i2, nr2, d2 = _desparte(vecin.stem)
        if i2 == inainte and d2 == dupa:
            if nr2 >= maxim:
                maxim, ultima = nr2, vecin
        elif vecin.stem == inainte and not dupa:
            if maxim <= 1:
                ultima = vecin
            maxim = max(maxim, 1)

    if not baza_verificata:
        motiv = _verifica_drift(ultima)
        if motiv:
            raise VersiuneModificata(
                "%s; deschide fisierul si construieste versiunea noua peste continutul "
                "lui, sau cheama din nou cu baza_verificata=True (--baza-verificata in "
                "linia de comanda) daca esti sigur ca nimic din el nu trebuie pastrat"
                % motiv)

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
    """Adauga --suprascrie si --baza-verificata la un ArgumentParser."""
    parser.add_argument(
        "--suprascrie", action="store_true",
        help="scrie peste fisierul existent; implicit se scrie o versiune noua alaturi")
    parser.add_argument(
        "--baza-verificata", action="store_true", dest="baza_verificata",
        help="confirma ca ai citit deja cea mai recenta versiune de pe disc, deci "
             "verificarea de amprenta se poate sari")
    return parser


def alege(cale, suprascrie: bool = False, tacut: bool = False,
          baza_verificata: bool = False) -> Path:
    """Calea de scris, tinand cont de steagurile --suprascrie si --baza-verificata."""
    if suprascrie:
        return Path(cale)
    return cale_libera(cale, tacut=tacut, baza_verificata=baza_verificata)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python cale_libera.py <cale>")
    for arg in sys.argv[1:]:
        try:
            print(cale_libera(arg, tacut=True))
        except VersiuneModificata as e:
            sys.exit(str(e))
