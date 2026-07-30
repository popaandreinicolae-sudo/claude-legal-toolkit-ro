#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_arhiva.py

Regresie pentru arhiva de livrari si pentru comparare.

Doua lucruri se verifica aici, fiindca amandoua se pot strica in tacere.

Discriminatorul de arhivare. Se arhiveaza ce produc eu si duc in dosarele autorului; NU se
arhiveaza un document al lui pe care doar il mut dintr-un dosar in altul. Un discriminator
prea larg umple arhiva cu acte de client stand in afara dosarelor lor, unul prea strans
rateaza tocmai livrarea de urmarit.

Regula de retragere. Un document neschimbat doua zile calendaristice la rand iese din
comparare si reintra cand se schimba. Regula lucreaza pe zile, nu pe rulari, deci nu poate
fi verificata pe o singura zi reala; testul simuleaza zilele.

Testul isi face propriul dosar de arhiva si nu atinge arhiva adevarata.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def docx_de_proba(cale: Path, paragrafe) -> None:
    """Un .docx minimal, cat sa poata fi citit de comparare."""
    corp = "".join(
        "<w:p><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>" % p for p in paragrafe)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           '<w:body>%s</w:body></w:document>' % corp)
    tipuri = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/word/document.xml" ContentType="application/vnd.'
              'openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    cale.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cale, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipuri)
        z.writestr("word/document.xml", doc)


def main() -> int:
    rele = 0
    baza = Path(tempfile.mkdtemp(prefix="proba-arhiva-"))
    # Arhiva de proba, ca sa nu atingem arhiva adevarata.
    import arhiva_livrari as al
    import compara_livrari as cl
    arhiva_reala = al.ARHIVA
    al.ARHIVA = baza / "arhiva"
    al.EVIDENTA = al.ARHIVA / "evidenta.json"
    cl.EVIDENTA_VERIFICARI = al.ARHIVA / "verificari.json"

    try:
        # Dosarul de lucru al meu si dosarul autorului, dinadins in afara %TEMP%
        # pentru al doilea, ca filtrul sa fie pus la incercare pe cazul real.
        lucru = baza / "lucru"
        dosar_autor = Path.home() / "_proba-arhiva" / "Dosar"
        alt_dosar_autor = Path.home() / "_proba-arhiva" / "Alt dosar"
        for d in (lucru, dosar_autor, alt_dosar_autor):
            d.mkdir(parents=True, exist_ok=True)

        print("=== discriminatorul de arhivare ===")
        produs = lucru / "act.docx"
        docx_de_proba(produs, ["Paragraful unu.", "Paragraful doi."])
        al_meu = dosar_autor / "act.docx"
        shutil.copy2(produs, al_meu)

        cazuri = [
            ("livrare, din dosarul meu de lucru", str(produs), str(al_meu), True),
            ("mutarea unui document al autorului", str(al_meu), str(alt_dosar_autor / "act.docx"), False),
            ("copiere intre doua dosare ale autorului", str(alt_dosar_autor / "act.docx"),
             str(dosar_autor / "altul.docx"), False),
        ]
        shutil.copy2(al_meu, alt_dosar_autor / "act.docx")
        shutil.copy2(al_meu, dosar_autor / "altul.docx")
        for eticheta, sursa, tinta, asteptat in cazuri:
            got = al.e_livrare(tinta, sursa)
            ok = got == asteptat
            rele += 0 if ok else 1
            print("  %s %-42s arhiveaza=%s" % ("ok    " if ok else "GRESIT", eticheta, got))

        print("\n=== regula de retragere, pe zile simulate ===")
        al.adauga(produs, cale_livrata=al_meu)

        def zi(z, astept, eticheta):
            nonlocal rele
            r = cl.ruleaza(date.fromisoformat(z))
            stare = ("schimbat" if r["schimbate"] else
                     "retras" if r["retrase"] else
                     "neschimbat" if r["neschimbate"] else "nimic")
            ok = stare == astept
            rele += 0 if ok else 1
            print("  %s %-11s %-34s -> %s" % ("ok    " if ok else "GRESIT", z, eticheta, stare))

        zi("2026-08-01", "neschimbat", "prima zi, neatins")
        zi("2026-08-01", "neschimbat", "a doua rulare in aceeasi zi")
        zi("2026-08-02", "retras", "a doua zi calendaristica, neatins")
        zi("2026-08-03", "retras", "ramane retras cat timp nu se atinge")

        docx_de_proba(al_meu, ["Paragraful unu, rescris.", "Paragraful doi.", "Adaugat."])
        zi("2026-08-04", "schimbat", "autorul l-a modificat, reintra")
        zi("2026-08-05", "neschimbat", "dupa reintrare, numaratoarea o ia de la capat")
        zi("2026-08-06", "retras", "se retrage din nou dupa doua zile")

        print("\n=== ce vede compararea in modificare ===")
        docx_de_proba(al_meu, ["Paragraful unu, rescris altfel.", "Adaugat."])
        r = cl.ruleaza(date.fromisoformat("2026-08-07"))
        d = r["schimbate"][0] if r["schimbate"] else {}
        for cheie, astept in (("rescrise", 1), ("scoase", 1)):
            n = len(d.get(cheie, []))
            ok = n == astept
            rele += 0 if ok else 1
            print("  %s %-12s %d (asteptat %d)" % ("ok    " if ok else "GRESIT", cheie, n, astept))

        print("\n=== documentul disparut de sub numele livrat ===")
        al_meu.unlink()
        r = cl.ruleaza(date.fromisoformat("2026-08-08"))
        ok = bool(r["de_intrebat"])
        rele += 0 if ok else 1
        print("  %s trece la 'de intrebat', nu ghiceste" % ("ok    " if ok else "GRESIT"))

    finally:
        al.ARHIVA = arhiva_reala
        shutil.rmtree(baza, ignore_errors=True)
        shutil.rmtree(Path.home() / "_proba-arhiva", ignore_errors=True)

    print()
    print("REZULTAT: %s" % ("toate cazurile trec" if not rele else "%d probleme" % rele))
    return 1 if rele else 0


if __name__ == "__main__":
    sys.exit(main())
