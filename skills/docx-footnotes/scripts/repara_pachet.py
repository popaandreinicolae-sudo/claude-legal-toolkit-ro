#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repara_pachet.py

Verifica si repara declaratiile de spatiu de nume din partile .xml ale unui .docx.

De ce exista
------------
Word refuza un document cu mesajul "Word found unreadable content" atunci cand
atributul Ignorable din spatiul Markup Compatibility enumera un prefix pe care
radacina nu il declara. Fisierul e XML valid, se deschide fara reproa in python-docx
si trece orice verificare de structura, dar Word il respinge inainte sa il arate.

Cazul care a costat o livrare, 29 iulie 2026: `assets/sablon-casa.docx` fusese
serializat cu lxml, care a rebotezat prefixele originale in ns1, ns2, ns3. Lista din
Ignorable a ramas insa scrisa cu numele vechi, w14 w15 w16se w16cid w16 w16cex
w16sdtdh w16sdtfl w16du wp14, si niciunul nu mai era declarat. Fiecare document
generat din sablon purta defectul, in word/document.xml si in word/numbering.xml.

Reparatia e minimala si nu atinge continutul. Ia URI-urile prefixelor din partile
scrise chiar de Word, adauga pe radacinile afectate doar declaratiile care lipsesc si,
unde prefixul canonic e cunoscut, redenumeste nsN in mc, r sau w, ca fisierul sa arate
ca unul scris de Word.

Regula: orice .docx generat programatic trece prin `verifica` inainte de livrare.
Serializarea cu lxml poate reintroduce defectul oricand, deci verificarea nu se sare
nici cand sablonul e curat.

Utilizare
---------
    python repara_pachet.py verifica --input act.docx
    python repara_pachet.py repara  --input act.docx [--output final.docx]

Fara --output, reparatia se face pe loc, cu o copie de siguranta alaturi.

Ca modul:
    from repara_pachet import verifica, repara
    probleme = verifica("act.docx")     # [] daca fisierul e bun
    repara("act.docx")                  # pe loc, intoarce lista reparatiilor
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

# Prefixele canonice, pentru URI-urile care apar in corpul documentului. Restul
# prefixelor rebotezate ramin cum sunt: numele unui prefix e liber, atat timp cat e
# declarat, iar Word nu are nimic cu ns2 sau ns3 daca xmlns:ns2 exista pe radacina.
CANONIC = {
    "http://schemas.openxmlformats.org/markup-compatibility/2006": "mc",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships": "r",
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main": "w",
}

# Prefixe pe care Word le cere scrise exact asa, nu doar declarate. In docProps/core.xml
# citeste datele dupa numele calificat dcterms:created, iar un ns2:created echivalent din
# punct de vedere XML il face sa refuze pachetul. Defectul a supravietuit reparatiei din
# 29 iulie 2026 fiindca verificarea se uita doar in word/, si a lovit fiecare document
# generat: Word le deschidea numai dupa promptul de reparare.
PREFIX_IMPUS = {
    "http://purl.org/dc/terms/": "dcterms",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://purl.org/dc/dcmitype/": "dcmitype",
    "http://schemas.openxmlformats.org/package/2006/metadata/core-properties": "cp",
}

# Atribute a caror VALOARE pomeneste prefixe. Un prefix nedeclarat scris acolo nu e prins
# de niciun parser, fiindca nu face parte din numele elementului sau al atributului.
ATRIBUTE_CU_PREFIXE = (
    ("Ignorable", "lista"), ("MustUnderstand", "lista"), ("ProcessContent", "lista"),
    ("PreserveElements", "lista"), ("PreserveAttributes", "lista"), ("type", "qname"),
)


def _radacina(xml: str):
    """Intoarce (start, sfarsit, textul) elementului radacina, oricare ar fi prefixul lui."""
    m = re.search(r"<([A-Za-z_][\w.-]*:)?[A-Za-z_][\w.-]*(\s[^>]*)?/?>", xml)
    if not m or xml[m.start():m.start() + 2] in ("<?", "<!"):
        i = xml.find("<w:")
        if i < 0:
            return None, None, None
        j = xml.find(">", i) + 1
        return i, j, xml[i:j]
    return m.start(), m.end(), m.group(0)


def _declaratii(fragment: str) -> dict:
    return dict(re.findall(r'xmlns:([A-Za-z0-9_]+)="([^"]+)"', fragment))


def _parti_xml(z: zipfile.ZipFile):
    """Toate partile XML ale pachetului, nu doar cele din word/.

    Pana pe 30 iulie 2026 aici scria `n.startswith("word/")`, iar docProps/core.xml ramanea
    in afara verificarii. Acolo statea insa defectul care il facea pe Word sa ceara
    reparare la fiecare document generat.
    """
    return [n for n in z.namelist()
            if n.endswith(".xml") and not n.startswith("customXml/")]


def _dictionar_uri(z: zipfile.ZipFile) -> dict:
    """URI-urile prefixelor standard, culese din partile care nu au fost rebotezate."""
    uri = {}
    for parte in _parti_xml(z):
        _, _, root = _radacina(z.read(parte).decode("utf-8"))
        if not root:
            continue
        for prefix, u in _declaratii(root).items():
            if not re.fullmatch(r"ns\d+", prefix):
                uri.setdefault(prefix, u)
    return uri


def verifica(cale) -> list:
    """Lista problemelor de spatiu de nume. Lista goala inseamna fisier bun."""
    probleme = []
    with zipfile.ZipFile(cale) as z:
        for parte in _parti_xml(z):
            xml = z.read(parte).decode("utf-8")
            _, _, root = _radacina(xml)
            if not root:
                continue
            ns = _declaratii(root)
            for nume, fel in ATRIBUTE_CU_PREFIXE:
                for m in re.finditer(r'[A-Za-z0-9_]+:%s="([^"]*)"' % nume, xml):
                    val = m.group(1)
                    bucati = val.split() if fel == "lista" else [val.split(":", 1)[0]]
                    if fel == "qname" and ":" not in val:
                        continue
                    lipsa = [p for p in bucati if p and p not in _declaratii(xml)]
                    if lipsa:
                        probleme.append(
                            "%s: %s=%r pomeneste prefixe nedeclarate: %s"
                            % (parte, nume, val, " ".join(sorted(set(lipsa)))))
            # prefixe folosite in corp fara declaratie in domeniu
            declarate = set(_declaratii(xml)) | {"xml", "xmlns"}
            folosite = (set(re.findall(r"</?([A-Za-z0-9_]+):", xml))
                        | set(re.findall(r"\s([A-Za-z0-9_]+):[A-Za-z]+=", xml)))
            nedeclarate = sorted(folosite - declarate)
            if nedeclarate:
                probleme.append("%s: prefixe folosite fara declaratie: %s"
                                % (parte, " ".join(nedeclarate)))
            # prefixe pe care Word le cere scrise exact asa, nu doar declarate
            for uri, dorit in PREFIX_IMPUS.items():
                actual = next((p for p, u in ns.items() if u == uri), None)
                if actual and actual != dorit:
                    probleme.append("%s: prefixul pentru %s e %r, Word il cere scris %r"
                                    % (parte, uri, actual, dorit))
    return probleme


def repara(cale, iesire=None, backup: bool = True) -> list:
    """Repara pachetul. Intoarce lista reparatiilor facute, goala daca nu era nimic."""
    cale = Path(cale)
    pe_loc = iesire is None
    tinta = Path(iesire) if iesire else cale.with_suffix(cale.suffix + ".tmp")

    facute = []
    with zipfile.ZipFile(cale) as zin:
        uri = _dictionar_uri(zin)
        modificate = {}

        for parte in _parti_xml(zin):
            xml = zin.read(parte).decode("utf-8")
            i, j, root = _radacina(xml)
            if not root:
                continue
            ns = _declaratii(root)

            # Prefixele impuse se rescriu intai, ca declaratia si numele calificate sa
            # ramana potrivite intre ele.
            impuse = {p: PREFIX_IMPUS[u] for p, u in ns.items()
                      if u in PREFIX_IMPUS and PREFIX_IMPUS[u] != p}
            if impuse:
                nou = xml
                for vechi, dorit in impuse.items():
                    nou = nou.replace('xmlns:%s="' % vechi, 'xmlns:%s="' % dorit)
                    nou = re.sub(r"(</?)%s:" % re.escape(vechi), r"\g<1>%s:" % dorit, nou)
                    nou = re.sub(r"(\s)%s:" % re.escape(vechi), r"\g<1>%s:" % dorit, nou)
                modificate[parte] = nou
                facute.append("%s: prefix rescris %s" % (
                    parte, " ".join("%s>%s" % kv for kv in impuse.items())))
                xml = nou
                i, j, root = _radacina(xml)
                ns = _declaratii(root)

            ign = re.search(r'([A-Za-z0-9_]+):Ignorable="([^"]*)"', root)
            if not ign:
                continue
            lipsa = [p for p in ign.group(2).split() if p not in ns]
            if not lipsa:
                continue

            necunoscute = [p for p in lipsa if p not in uri]
            if necunoscute:
                raise RuntimeError(
                    "Nu cunosc URI-ul prefixelor %s din %s. Deschide documentul in Word, "
                    "salveaza-l, apoi reia; Word rescrie declaratiile complet."
                    % (" ".join(necunoscute), parte))

            root_nou = root[:-1].rstrip() + " " + " ".join(
                'xmlns:%s="%s"' % (p, uri[p]) for p in lipsa) + ">"
            corp = xml[j:]

            redenumiri = {p: CANONIC[u] for p, u in ns.items()
                          if re.fullmatch(r"ns\d+", p) and u in CANONIC and CANONIC[u] != p}
            for vechi, nou in redenumiri.items():
                root_nou = root_nou.replace('xmlns:%s=' % vechi, 'xmlns:%s=' % nou)
                root_nou = re.sub(r"(\s)%s:" % vechi, r"\1%s:" % nou, root_nou)
                corp = re.sub(r"(</?)%s:" % vechi, r"\1%s:" % nou, corp)
                corp = re.sub(r"(\s)%s:" % vechi, r"\1%s:" % nou, corp)

            modificate[parte] = xml[:i] + root_nou + corp
            facute.append("%s: declarat %s%s" % (
                parte, " ".join(lipsa),
                ", redenumit " + " ".join("%s>%s" % kv for kv in redenumiri.items())
                if redenumiri else ""))

        if not modificate:
            if not pe_loc:
                shutil.copyfile(cale, tinta)
            return []

        with zipfile.ZipFile(tinta, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                date = (modificate[item.filename].encode("utf-8")
                        if item.filename in modificate else zin.read(item.filename))
                zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                zi.compress_type = item.compress_type
                zi.external_attr = item.external_attr
                zout.writestr(zi, date)

    if pe_loc:
        if backup:
            copie = cale.with_name(cale.stem + ".inainte-de-reparatie" + cale.suffix)
            if not copie.exists():
                shutil.copyfile(cale, copie)
        shutil.move(str(tinta), str(cale))
    return facute


def asigura(cale, tacut: bool = False) -> list:
    """Verifica si, daca e nevoie, repara pe loc. De chemat dupa fiecare generare."""
    probleme = verifica(cale)
    if not probleme:
        return []
    facute = repara(cale, backup=False)
    ramase = verifica(cale)
    if ramase:
        raise RuntimeError("Reparatia nu a rezolvat tot:\n  " + "\n  ".join(ramase))
    if not tacut:
        for f in facute:
            print("  spatiu de nume reparat, %s" % f)
    return facute


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica si repara spatiile de nume ale unui .docx")
    ap.add_argument("actiune", choices=["verifica", "repara"])
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)

    if args.actiune == "verifica":
        probleme = verifica(args.input)
        if probleme:
            print("PROBLEME, Word va refuza fisierul:")
            for p in probleme:
                print("  -", p)
            return 1
        print("spatiile de nume sunt in regula")
        return 0

    facute = repara(args.input, args.output)
    if not facute:
        print("nimic de reparat")
    else:
        for f in facute:
            print("reparat:", f)
    ramase = verifica(args.output or args.input)
    if ramase:
        print("ATENTIE, au ramas probleme:")
        for p in ramase:
            print("  -", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
