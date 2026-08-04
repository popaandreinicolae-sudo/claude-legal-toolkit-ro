#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redline_obligatoriu.py

Prinde versiunea noua de .docx plecata fara documentul cu modificari urmarite.

De ce exista
------------
Regula autorului, scrisa in caiet pe 2 august 2026: orice versiune noua vine insotita de
redline, fara exceptie, si nu doar la documentele primite de la el, ci si la versiunile
mele succesive. A doua zi la 19:54 a plecat oricum un v2 fara redline, fiindca regula
traia numai ca text, iar textul ajunge la model doar pe suprafata care il citeste.

Aici incepe stratul care nu depinde de ce tine modelul minte. Perechea lui pe cealalta
suprafata este campul `instructions` al serverului persona plus poarta de activare din
server/poarta.py; a treia plasa sta in scrie_document.py, care produce redline-ul singur.

Ce prinde
---------
Versiunile scrise prin Write si cele ajunse in dosare prin copiere sau mutare, fiindca
livrarea se face de cele mai multe ori printr-o copiere obisnuita si acolo niciun script
al nostru nu mai e implicat.

Ce nu prinde, deliberat
-----------------------
Primul document dintr-o serie, care nu are fata de ce sa fie comparat. Fisierele de
redline insele. Documentele care poarta deja <w:ins> sau <w:del>, adica sunt ele redline
sub alt nume.

Cod de iesire
-------------
Iese cu 2, ca stderr sa ajunga la model, nu doar in ecranul autorului. Hook-ul tot nu
modifica nimic si nu poate desface scrierea deja facuta; singurul lui efect e ca modelul
afla, cat mai e in sarcina, ca datoreaza un redline. Restul hook-urilor din toolkit ies cu
0 fiindca semnaleaza candidati de verificat, unde un fals-pozitiv ar strica o citare buna.
Aici un fals-pozitiv costa un fisier de redline in plus, deci raportul e invers.

Fail-open. Comutator: REDLINE_OBLIGATORIU_OFF=1.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import zipfile

FEREASTRA_SECUNDE = 300
ETICHETE_REDLINE = ("redline", "track_changes", "track changes")


def _e_redline_dupa_nume(stem: str) -> bool:
    jos = stem.lower()
    return any(e in jos for e in ETICHETE_REDLINE)


def _poarta_revizii(cale: str) -> bool:
    """True cand documentul are deja <w:ins> sau <w:del> in el."""
    try:
        with zipfile.ZipFile(cale) as z:
            for parte in ("word/document.xml", "word/footnotes.xml"):
                try:
                    xml = z.read(parte).decode("utf-8", "replace")
                except KeyError:
                    continue
                if "<w:ins " in xml or "<w:del " in xml:
                    return True
    except (OSError, zipfile.BadZipFile):
        return True  # nu il pot citi, deci nu am ce afirma despre el
    return False


# Marcajul de versiune, in aceeasi lectura pe care o face cale_libera.py din skill-ul
# docx-footnotes: numarul se recunoaste oriunde in nume, iar eticheta de dupa el desparte
# familiile. "act_v1_autor" si "act_v2_redline" sunt siruri diferite. Regula e repetata
# aici, nu importata, fiindca un hook trebuie sa ruleze si cand skill-urile lipsesc.
_TIPAR_VERSIUNE = re.compile(r"^(?P<inainte>.*)_v(?P<nr>\d+)(?P<dupa>(?:_.*)?)$")


def _desparte(stem: str) -> tuple:
    """(inainte, numar, dupa). Fara marcaj, numarul e 1 si coada e goala."""
    m = _TIPAR_VERSIUNE.match(stem)
    if m:
        return m.group("inainte"), int(m.group("nr")), m.group("dupa")
    return stem, 1, ""


def _precedent(cale: str) -> str | None:
    """Cea mai mare versiune ANTERIOARA din aceeasi familie, sau None.

    Numarul decide, nu data de pe disc. Altfel rescrierea lui act.docx dupa ce exista
    act_v2.docx ar cere un redline fata de propriul ei succesor.
    """
    dosar = os.path.dirname(cale) or "."
    stem = os.path.splitext(os.path.basename(cale))[0]
    inainte, nr, dupa = _desparte(stem)
    if not inainte:
        return None
    try:
        vecini = os.listdir(dosar)
    except OSError:
        return None
    candidati = []
    for nume in vecini:
        if not nume.lower().endswith(".docx"):
            continue
        drum = os.path.join(dosar, nume)
        if os.path.abspath(drum) == os.path.abspath(cale):
            continue
        i2, nr2, d2 = _desparte(os.path.splitext(nume)[0])
        if i2 != inainte or d2 != dupa or nr2 >= nr:
            continue
        candidati.append((nr2, drum))
    if not candidati:
        return None
    return max(candidati)[1]


def _are_redline(cale: str) -> bool:
    """True cand in dosar sta deja un redline pentru versiunea asta."""
    dosar = os.path.dirname(cale) or "."
    stem = os.path.splitext(os.path.basename(cale))[0]
    try:
        vecini = os.listdir(dosar)
    except OSError:
        return True
    try:
        scris_la = os.path.getmtime(cale)
    except OSError:
        return True
    for nume in vecini:
        if not nume.lower().endswith(".docx"):
            continue
        vstem = os.path.splitext(nume)[0]
        if not _e_redline_dupa_nume(vstem):
            continue
        if not vstem.lower().startswith(stem.lower()):
            continue
        try:
            if os.path.getmtime(os.path.join(dosar, nume)) >= scris_la - 5:
                return True
        except OSError:
            continue
    return False


def cai_docx(date: dict) -> list:
    """Documentele .docx pe care apelul tocmai le-a scris sau mutat."""
    unealta = date.get("tool_name") or ""
    intrare = date.get("tool_input") or {}
    brute = []
    if unealta in ("Write", "NotebookEdit"):
        brute.append(intrare.get("file_path") or "")
    elif unealta in ("Bash", "PowerShell"):
        cmd = intrare.get("command") or ""
        brute += re.findall(r'"([^"]+\.docx)"', cmd)
        brute += re.findall(r"'([^']+\.docx)'", cmd)
        brute += re.findall(r"(?<![\"'])(\S+\.docx)(?![\"'])", cmd)

    radacina = date.get("cwd") or os.getcwd()
    acum = time.time()
    iesire, vazute = [], set()
    for c in brute:
        c = (c or "").strip().strip('"').strip("'")
        if not c:
            continue
        p = os.path.expanduser(c)
        if not (os.path.isabs(p) or re.match(r"^[A-Za-z]:", p)):
            p = os.path.normpath(os.path.join(radacina, p))
        cheie = os.path.abspath(p).lower()
        if cheie in vazute:
            continue
        vazute.add(cheie)
        try:
            if not os.path.isfile(p) or acum - os.path.getmtime(p) > FEREASTRA_SECUNDE:
                continue
        except OSError:
            continue
        iesire.append(p)
    return iesire


def datoreaza_redline(cale: str) -> str | None:
    """Versiunea precedenta fata de care lipseste redline-ul, sau None."""
    stem = os.path.splitext(os.path.basename(cale))[0]
    if _e_redline_dupa_nume(stem):
        return None
    prec = _precedent(cale)
    if not prec:
        return None
    if _poarta_revizii(cale):
        return None
    if _are_redline(cale):
        return None
    return prec


def main() -> int:
    if os.environ.get("REDLINE_OBLIGATORIU_OFF") == "1":
        return 0
    try:
        date = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0

    lipsuri = []
    for cale in cai_docx(date):
        prec = datoreaza_redline(cale)
        if prec:
            lipsuri.append((cale, prec))
    if not lipsuri:
        return 0

    scriptul = os.path.join(os.path.expanduser("~"), ".claude", "skills",
                            "docx-track-changes", "scripts", "docx_track_changes.py")
    sys.stderr.write(
        "\nREDLINE LIPSA. Regula autorului: orice versiune noua vine insotita de "
        "redline, fara exceptie, inclusiv intre propriile mele versiuni succesive.\n")
    for cale, prec in lipsuri:
        iesire = os.path.splitext(cale)[0] + "_redline_AMZ.docx"
        sys.stderr.write(
            '  %s\n    fata de: %s\n    python "%s" apply --input "%s" '
            '--revised "%s" --output "%s"\n'
            % (cale, prec, scriptul, prec, cale, iesire))
    sys.stderr.write(
        "  Un act de 30 de pagini in care s-au schimbat doua alineate arata identic cu "
        "unul in care s-au schimbat treizeci.\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
