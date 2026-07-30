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


def inregistreaza_prefixele(xml: bytes) -> None:
    """Inregistreaza prefixele exact cum le-a scris Word, inainte de serializare.

    ElementTree nu tine minte prefixele, doar URI-urile. La `tostring` inventeaza
    ns0, ns1, ns2 pentru orice namespace neinregistrat. Atributul `mc:Ignorable` e insa
    un simplu sir de text care enumera prefixe, iar ElementTree nu are cum sa il
    rescrie. Rezultatul: radacina declara Markup Compatibility drept ns1, iar Ignorable
    trimite la w14, w15, wp14 si celelalte, care nu mai sunt declarate nicaieri.

    Word refuza atunci fisierul cu "Word found unreadable content", desi pachetul e XML
    valid, se deschide in python-docx si trece orice verificare de format. Lectie
    platita pe 29 iulie 2026, cand un act generat din sablon nu s-a deschis la client.

    Inregistrarea rezolva prefixele chiar folosite in arbore, mc si r. Pe cele declarate
    dar nefolosite, w14 w15 w16se si celelalte, ElementTree le lasa afara oricum, fiindca
    nu emite o declaratie pentru un namespace pe care nimic din arbore nu il atinge.
    Acelea se pun inapoi la final, cu repara_pachet.asigura(), vezi main().
    """
    for prefix, uri in re.findall(rb'xmlns:([A-Za-z0-9_]+)="([^"]+)"', xml[:4000]):
        ET.register_namespace(prefix.decode(), uri.decode())


def goleste_corpul(xml: bytes) -> bytes:
    """Scoate tot continutul din corp si pastreaza numai sectPr.

    sectPr este ultimul copil al lui body si tine marginile, distantele pentru antet si
    subsol, referintele catre ele si `titlePg`. Fara el, documentul pierde tocmai ce am
    venit sa pastram.
    """
    inregistreaza_prefixele(xml)
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
    inregistreaza_prefixele(xml)
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


def reseteaza_numerotarea(xml: bytes) -> bytes:
    """Aduce fiecare flux de numerotare la inceput.

    Actul-sursa continua numerotarea din locul in care ajunsese, deci `w:start` ramane
    la valoarea de acolo. Sablonul mostenea asta si primul paragraf al unui act nou
    aparea ca [21]. Un sablon numeroteaza mereu de la inceput, deci punem `start` pe 1
    la nivelul zero si scoatem suprascrierile de start.
    """
    inregistreaza_prefixele(xml)
    ET.register_namespace("w", W)
    root = ET.fromstring(xml)

    for lvl in root.iter(f"{Wn}lvl"):
        if lvl.get(f"{Wn}ilvl") != "0":
            continue
        start = lvl.find(f"{Wn}start")
        if start is not None:
            start.set(f"{Wn}val", "1")

    for num in root.iter(f"{Wn}num"):
        for ovr in list(num.findall(f"{Wn}lvlOverride")):
            num.remove(ovr)

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


def verifica_spatiile_de_nume(cale: Path) -> list:
    """Partile in care Ignorable enumera prefixe pe care radacina nu le declara.

    Verificarea nu se sare. Serializarea poate reintroduce defectul oricand, iar Word
    refuza atunci fisierul fara sa spuna de ce, dupa ce a trecut tot restul.
    """
    rupte = []
    with zipfile.ZipFile(cale) as z:
        for parte in z.namelist():
            if not (parte.startswith("word/") and parte.endswith(".xml")):
                continue
            xml = z.read(parte).decode("utf-8", "replace")
            i = xml.find("<w:")
            if i < 0:
                continue
            root = xml[i:xml.find(">", i) + 1]
            declarate = set(re.findall(r'xmlns:([A-Za-z0-9_]+)=', root))
            ign = re.search(r'([A-Za-z0-9_]+):Ignorable="([^"]*)"', root)
            if ign:
                lipsa = [p for p in ign.group(2).split() if p not in declarate]
                if lipsa:
                    rupte.append("%s (%s)" % (parte, " ".join(lipsa)))
    return rupte


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
            elif item.filename == "word/numbering.xml":
                date = reseteaza_numerotarea(date)
            elif item.filename == "_rels/.rels":
                date = curata_relatiile(date, DE_SCOS)
            elif item.filename == "[Content_Types].xml":
                date = curata_tipurile(date, DE_SCOS)
            zout.writestr(item, date)

    # Declaratiile pierdute la serializare se pun inapoi, apoi se verifica. Reparatia se
    # face pe fisierul temporar, ca un sablon rupt sa nu ajunga niciodata la destinatie.
    # Word nu spune de ce refuza, deci defectul ar merge nedetectat pana la client, in
    # fiecare document generat din sablon.
    sys.path.insert(0, str(REPO / "skills" / "docx-footnotes" / "scripts"))
    import repara_pachet

    puse = repara_pachet.repara(temporar, backup=False)
    for p in puse:
        print("  declaratii puse inapoi, %s" % p)

    rupte = verifica_spatiile_de_nume(temporar)
    if rupte:
        temporar.unlink(missing_ok=True)
        print("SABLONUL NU A FOST SCRIS. Ignorable enumera prefixe nedeclarate in "
              + "; ".join(rupte), file=sys.stderr)
        print("Reparatia automata nu a rezolvat. Deschide actul-sursa in Word, "
              "salveaza-l, apoi reia.", file=sys.stderr)
        return 1

    shutil.move(str(temporar), str(TINTA))
    print(f"sablon scris din {args.sursa.name}")
    print(f"  -> {TINTA}  ({TINTA.stat().st_size // 1024} KB)")
    raport(TINTA)
    print("  spatii de nume: in regula, Word deschide pachetul")
    return 0


if __name__ == "__main__":
    sys.exit(main())
