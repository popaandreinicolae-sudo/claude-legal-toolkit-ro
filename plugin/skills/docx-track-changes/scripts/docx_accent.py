#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_accent.py

Pune bold pe termenii definiti dintr-un .docx, ca REVIZIE URMARITA de formatare.

De ce exista
------------
docx_track_changes.py marcheaza inserari si stergeri de text. Formatarea nu intra pe
acolo, iar pe 30 iulie 2026 bold-ul a fost pus direct pe text, nemarcat, fiindca
elementul w:rPrChange nu era implementat nicaieri. Consecinta: Reject All reda cuvintele
autorului, dar accentul rămâne pe ele, deci garantia redlineului se rupe tocmai la
proprietatea pe care o verificam.

Aici bold-ul se scrie cu w:rPrChange, adica exact forma pe care o produce Word cand
urmareste o schimbare de formatare. Word o arata in panoul Review, iar Reject All
readuce formatarea anterioara.

Regulile de accent, masurate pe actele proprii
---------------------------------------------
Bold-ul cade pe termeni definiti, pe parti si pe temeiuri, in 53% din paragrafe. Doua
plafoane il tin departe de bold mecanic, interzis de regula 22 din anti-ai-tone:

  - maximum doua expresii pe paragraf, prima aparitie;
  - maximum patru accente pe termen in tot documentul, formele flexionate ale aceleiasi
    noțiuni socotite impreuna. Fara plafonul al doilea, "destinația militară" ieșea
    accentuat de treizeci si doua de ori intr-un singur act.

Acoperirea se ridica adaugand termeni distincti in lista, nu ridicand plafonul. Un
plafon mare concentreaza accentul pe aceleasi cateva noțiuni, adica exact ce trebuie
evitat.

Utilizare
---------
    python docx_accent.py apply --input act.docx --output act_accentuat.docx \
        --termeni termeni.json --author "AMZ Law Office"

    python docx_accent.py apply --input act.docx --output act_accentuat.docx \
        --termeni termeni.json --netrasat        # bold nemarcat, la cerere expresa

Formatul termeni.json
---------------------
{
  "max_pe_paragraf": 2,
  "max_pe_termen": 4,
  "termeni": ["art. 5 alin. (1)", "destinația militară", "fără drept"],
  "familii": {"destinația militară": "destinatie", "destinație militară": "destinatie"}
}

`termeni` se citeste in ordine, deci scrie formele lungi inaintea celor scurte, ca
"art. 136 alin. (2)" sa fie prins inaintea unui eventual "art. 136". `familii` leaga
formele flexionate sub acelasi plafon.
"""
from __future__ import annotations

import argparse
import os
import datetime as _dt
import json
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cale_libera import alege, adauga_optiune

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.exit("Lipseste lxml. Instaleaza-l cu: pip install lxml")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# Ordinea copiilor lui w:rPr din schema. w:b intra pe poziția lui, iar w:rPrChange
# ultimul. Word refuza documentul cand ordinea nu e respectata.
ORDINE_RPR = [
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
    "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish",
    "webHidden", "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight",
    "u", "effect", "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
    "eastAsianLayout", "specVanish", "oMath", "rPrChange",
]


class AccentError(Exception):
    pass


def _pune_in_rpr(rpr, element, nume: str):
    for vechi in rpr.findall(W + nume):
        rpr.remove(vechi)
    rang = ORDINE_RPR.index(nume)
    for copil in rpr:
        eticheta = copil.tag.split("}")[-1]
        if eticheta in ORDINE_RPR and ORDINE_RPR.index(eticheta) > rang:
            copil.addprevious(element)
            return
    rpr.append(element)


def _rpr(run):
    rpr = run.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        run.insert(0, rpr)
    return rpr


def _accentueaza(run, author, date, ids, trasat: bool):
    """Pune bold pe run. Cand `trasat`, scrie si w:rPrChange cu formatarea anterioara."""
    rpr = _rpr(run)
    if rpr.find(W + "b") is not None:
        return False

    if trasat:
        # Formatarea anterioara se pastreaza inainte de a fi modificata, fara rPrChange
        # din ea, altfel s-ar cuibari revizii una in alta.
        anterior = etree.fromstring(etree.tostring(rpr))
        for vechi in anterior.findall(W + "rPrChange"):
            anterior.remove(vechi)

    b = etree.Element(W + "b")
    _pune_in_rpr(rpr, b, "b")

    if trasat:
        schimbare = etree.Element(W + "rPrChange")
        schimbare.set(W + "id", next(ids))
        schimbare.set(W + "author", author)
        schimbare.set(W + "date", date)
        schimbare.append(anterior)
        _pune_in_rpr(rpr, schimbare, "rPrChange")
    return True


def _in_del(nod):
    """Textul sters nu primeste accent; el dispare la Accept All."""
    p = nod.getparent()
    while p is not None and p.tag != W + "p":
        if p.tag == W + "del":
            return True
        p = p.getparent()
    return False


def _sparge(run, t_nod, start: int, lung: int):
    """Sparge run-ul in trei si intoarce run-ul din mijloc.

    Cand run-ul sta intr-un w:ins, cele trei bucati rămân in acelasi w:ins, fiindca
    inserarea se face in parintele direct.
    """
    text = t_nod.text or ""
    bucati = [text[:start], text[start:start + lung], text[start + lung:]]
    parent = run.getparent()
    poz = list(parent).index(run)

    def clona(conținut):
        nou = etree.fromstring(etree.tostring(run))
        for t in nou.iter(W + "t"):
            t.text = conținut
            t.set(XML_SPACE, "preserve")
        return nou

    r_mijloc = None
    noi = []
    for k, bucata in enumerate(bucati):
        if not bucata and k != 1:
            continue
        nou = clona(bucata)
        if k == 1:
            r_mijloc = nou
        noi.append(nou)
    for k, nou in enumerate(noi):
        parent.insert(poz + k, nou)
    parent.remove(run)
    return r_mijloc


def _ids(start: int = 8000):
    n = start
    while True:
        yield str(n)
        n += 1


def aplica(cale_in, cale_out, spec, author, date, trasat=True):
    termeni = spec.get("termeni") or []
    if not termeni:
        raise AccentError("lista de termeni e goala")
    familii = spec.get("familii") or {}
    max_para = int(spec.get("max_pe_paragraf", 2))
    max_termen = int(spec.get("max_pe_termen", 4))

    zin = zipfile.ZipFile(cale_in)
    doc = etree.fromstring(zin.read("word/document.xml"))
    ids = _ids()

    puse, atinse, total = 0, 0, 0
    consum: dict[str, int] = {}
    pe_termen: dict[str, int] = {}

    for p in doc.iter(W + "p"):
        vizibil = "".join(n.text or "" for n in p.iter(W + "t"))
        if not vizibil.strip():
            continue
        total += 1
        folosite = 0
        for termen in termeni:
            if folosite >= max_para:
                break
            if termen not in vizibil:
                continue
            familie = familii.get(termen, termen)
            if consum.get(familie, 0) >= max_termen:
                continue
            for t_nod in list(p.iter(W + "t")):
                if _in_del(t_nod):
                    continue
                text = t_nod.text or ""
                i = text.find(termen)
                if i < 0:
                    continue
                run = t_nod.getparent()
                if run.tag != W + "r":
                    continue
                rpr = run.find(W + "rPr")
                if rpr is not None and rpr.find(W + "b") is not None:
                    break
                mijloc = _sparge(run, t_nod, i, len(termen))
                if mijloc is not None and _accentueaza(mijloc, author, date, ids, trasat):
                    puse += 1
                    folosite += 1
                    consum[familie] = consum.get(familie, 0) + 1
                    pe_termen[termen] = pe_termen.get(termen, 0) + 1
                break
        if folosite:
            atinse += 1

    date_xml = etree.tostring(doc, encoding="UTF-8", xml_declaration=True, standalone=True)
    Path(cale_out).unlink(missing_ok=True)
    zout = zipfile.ZipFile(cale_out, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        conținut = date_xml if item.filename == "word/document.xml" else zin.read(item.filename)
        zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
        zi.compress_type = item.compress_type
        zi.external_attr = item.external_attr
        zout.writestr(zi, conținut)
    zout.close()
    zin.close()
    return {"accente": puse, "paragrafe_atinse": atinse, "paragrafe_total": total,
            "acoperire_pct": (100 * atinse // max(total, 1)), "pe_termen": pe_termen,
            "trasat": trasat}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bold pe termeni definiti, ca revizie urmarita")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply", help="pune accentul si scrie documentul")
    a.add_argument("--input", required=True, type=Path)
    a.add_argument("--output", required=True, type=Path)
    adauga_optiune(a)
    a.add_argument("--termeni", required=True, type=Path)
    a.add_argument("--author", default="AMZ Law Office")
    a.add_argument("--netrasat", action="store_true",
                   help="bold nemarcat; Reject All nu mai reproduce formatarea originala")
    args = ap.parse_args(argv)

    args.output = alege(args.output, args.suprascrie)
    spec = json.loads(args.termeni.read_text(encoding="utf-8"))
    date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        raport = aplica(args.input, args.output, spec, args.author, date,
                        trasat=not args.netrasat)
    except AccentError as e:
        sys.stderr.write("%s\n" % e)
        return 1
    print(json.dumps(raport, ensure_ascii=False, indent=2))
    if not raport["trasat"]:
        sys.stderr.write("Atentie: accent nemarcat. Reject All reda cuvintele, dar "
                         "bold-ul rămâne pe ele.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
