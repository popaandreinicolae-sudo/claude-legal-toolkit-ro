#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sablon.py

Construieste sablonul de casa dintr-un act real, prin golire, nu prin reconstructie.

De ce asa. Un document Word poarta mult mai mult decat se poate masura si rescrie:
definitiile de stil cu toate variantele lor, numerotarea pe niveluri din numbering.xml,
tema cu paleta de culori, relatiile dintre sectiune si anteturi, `w:titlePg` care face
antetul sa apara doar pe prima pagina, latimea si ancorarea exacta a logo-ului. Orice
incercare de a le reproduce din parametri masurati pierde ceva. Prima varianta a pierdut
exact `titlePg`, deci logo-ul se repeta pe fiecare pagina.

Sablonul pastreaza intreaga arhiva si sterge doar continutul din corp, plus datele
identificabile ale dosarului din care provine.

    python tools/build_sablon.py --sursa "D:/Claude/Persona/act.docx"
    python tools/build_sablon.py --verifica
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TINTA = REPO / "skills" / "docx-footnotes" / "assets" / "sablon-casa.docx"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"
Wn = "{%s}" % W

# Sterse din arhiva: proprietatile personalizate vin din sistemul documentar al altui
# cabinet, iar miniatura arata prima pagina a dosarului original.
DE_SCOS = {"docProps/custom.xml", "docProps/thumbnail.emf", "docProps/thumbnail.jpeg"}

# Golite in docProps/core.xml, ca sablonul sa nu poarte urme ale cauzei de origine.
DE_GOLIT = {f"{{{DC}}}title", f"{{{DC}}}subject", f"{{{DC}}}description",
            f"{{{CP}}}keywords", f"{{{CP}}}category", f"{{{CP}}}lastPrinted",
            f"{{{CP}}}revision", f"{{{DC}}}identifier"}


def goleste_corpul(xml: bytes) -> bytes:
    """Scoate tot continutul din corp si pastreaza numai sectPr.

    sectPr este ultimul copil al lui body si tine marginile, distantele pentru antet si
    subsol, referintele catre ele si `titlePg`. Fara el, documentul pierde tocmai ce am
    venit sa pastram.
    """
    ET.register_namespace("w", W)
    root = ET.fromstring(xml)
    body = root.find(f"{Wn}body")
    if body is None:
        raise SystemExit("document.xml nu are body")

    sect = body.find(f"{Wn}sectPr")
    if sect is None:
        raise SystemExit("document.xml nu are sectPr; sablonul ar pierde antetul")

    for copil in list(body):
        if copil is not sect:
            body.remove(copil)

    # Un paragraf gol inaintea sectiunii, ca documentul sa fie valid si sa aiba unde
    # incepe scrisul.
    p = ET.Element(f"{Wn}p")
    body.insert(0, p)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def curata_proprietatile(xml: bytes) -> bytes:
    ET.register_namespace("cp", CP)
    ET.register_namespace("dc", DC)
    root = ET.fromstring(xml)
    for el in list(root):
        if el.tag in DE_GOLIT:
            root.remove(el)
    for el in root.iter():
        if el.tag == f"{{{DC}}}creator" or el.tag == f"{{{CP}}}lastModifiedBy":
            el.text = "Adrian Zamfir"
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def curata_relatiile(xml: bytes, scoase: set[str]) -> bytes:
    """Scoate relatiile care trimit catre parti eliminate din arhiva.

    Fara asta, `_rels/.rels` pastreaza trimiterea catre docProps/custom.xml, iar orice
    cititor de .docx cade cu "There is no item named". Partea si relatia se sterg
    impreuna, mereu.
    """
    R = "http://schemas.openxmlformats.org/package/2006/relationships"
    ET.register_namespace("", R)
    root = ET.fromstring(xml)
    tinte = {Path(x).name for x in scoase}
    for rel in list(root):
        t = (rel.get("Target") or "").lstrip("/")
        if Path(t).name in tinte:
            root.remove(rel)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def curata_tipurile(xml: bytes, scoase: set[str]) -> bytes:
    """Scoate suprascrierile de tip pentru partile eliminate."""
    CT = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("", CT)
    root = ET.fromstring(xml)
    for el in list(root):
        if el.tag.endswith("Override") and (el.get("PartName") or "").lstrip("/") in scoase:
            root.remove(el)
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def raport(cale: Path) -> None:
    with zipfile.ZipFile(cale) as z:
        nm = z.namelist()
        doc = ET.fromstring(z.read("word/document.xml"))
        sect = doc.find(f"{Wn}body/{Wn}sectPr")
        anteturi = {r.get(f"{Wn}type") for r in sect.iter(f"{Wn}headerReference")}
        subsoluri = {r.get(f"{Wn}type") for r in sect.iter(f"{Wn}footerReference")}
        print(f"  antet doar pe prima pagina: "
              f"{'da' if sect.find(f'{Wn}titlePg') is not None else 'NU'}")
        print(f"  referinte antet: {sorted(x for x in anteturi if x)}")
        print(f"  referinte subsol: {sorted(x for x in subsoluri if x)}")
        print(f"  stiluri: {'da' if 'word/styles.xml' in nm else 'NU'}"
              f", numerotare: {'da' if 'word/numbering.xml' in nm else 'NU'}"
              f", tema: {'da' if any('theme' in x for x in nm) else 'NU'}")
        print(f"  imagini: {sum(1 for x in nm if x.startswith('word/media/'))}")
        print(f"  paragrafe ramase in corp: {sum(1 for _ in doc.iter(f'{Wn}p'))}")
        print(f"  proprietati personalizate: "
              f"{'DA, ar trebui scoase' if 'docProps/custom.xml' in nm else 'niciuna'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sablon de casa dintr-un act real")
    ap.add_argument("--sursa", type=Path)
    ap.add_argument("--verifica", action="store_true", help="raporteaza sablonul existent")
    args = ap.parse_args(argv)

    if args.verifica:
        if not TINTA.exists():
            return print(f"nu exista {TINTA}") or 1
        print(TINTA)
        raport(TINTA)
        return 0

    if not args.sursa or not args.sursa.exists():
        return print("da o sursa existenta cu --sursa") or 1

    TINTA.parent.mkdir(parents=True, exist_ok=True)
    temporar = TINTA.with_suffix(".tmp")

    with zipfile.ZipFile(args.sursa) as zin, \
         zipfile.ZipFile(temporar, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename in DE_SCOS:
                continue
            date = zin.read(item.filename)
            if item.filename == "word/document.xml":
                date = goleste_corpul(date)
            elif item.filename == "docProps/core.xml":
                date = curata_proprietatile(date)
            elif item.filename == "_rels/.rels":
                date = curata_relatiile(date, DE_SCOS)
            elif item.filename == "[Content_Types].xml":
                date = curata_tipurile(date, DE_SCOS)
            zout.writestr(item, date)

    shutil.move(str(temporar), str(TINTA))
    print(f"sablon scris din {args.sursa.name}")
    print(f"  -> {TINTA}  ({TINTA.stat().st_size // 1024} KB)")
    raport(TINTA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
