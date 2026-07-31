# -*- coding: utf-8 -*-
"""Scoate obiectele incorporate (OLE) dintr-un .docx, fara sa atinga imaginile reale.

Un document primit de la client poarta adesea obiecte Word incorporate, ramase din
sablonul lui: apar ca pictograme cu numele fisierului sursa, in antet sau in corp. Pe
31 iulie 2026 au ajuns asa doua pictograme „Plangere prealabila_Radulescu Vasile_S" in
antetul unei exceptii de neconstitutionalitate, adica numele altui client, pe un act
care urma sa plece la Curtea Constitutionala.

Se scot elementele `w:object`, relatiile lor si partile catre care trimit, atat
pachetul incorporat cat si pictograma care il reprezinta. Siglele si imaginile
adevarate, care stau in `w:drawing`, raman neatinse.

  python curata_obiecte.py verifica --input act.docx
  python curata_obiecte.py curata   --input act.docx --output act_curat.docx
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"


def _parti_cu_continut(z: zipfile.ZipFile) -> list:
    return [n for n in z.namelist()
            if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]


def _rels(nume: str) -> str:
    p = nume.rsplit("/", 1)
    return "%s/_rels/%s.rels" % (p[0], p[1])


def _descrie(obiect) -> str:
    """Numele afisat al obiectului, cat se poate afla din XML."""
    for et in obiect.iter():
        nume = etree.QName(et).localname
        if nume == "OLEObject":
            prog = et.get("ProgID") or "?"
            return "ProgID=%s" % prog
    return "obiect necunoscut"


def analizeaza(cale: Path) -> dict:
    """{parte: [(descriere, [r:id-uri folosite])]} plus tintele relatiilor."""
    z = zipfile.ZipFile(cale)
    gasite, tinte = {}, {}
    for parte in _parti_cu_continut(z):
        try:
            rad = etree.fromstring(z.read(parte))
        except Exception:
            continue
        obiecte = [e for e in rad.iter("{%s}object" % W)]
        if not obiecte:
            continue
        harta = {}
        try:
            rrad = etree.fromstring(z.read(_rels(parte)))
            for rel in rrad:
                harta[rel.get("Id")] = rel.get("Target")
        except KeyError:
            pass
        lista = []
        for ob in obiecte:
            ids = set()
            for et in ob.iter():
                for atr, val in et.attrib.items():
                    if atr.endswith("}id") or atr.endswith("}embed") or atr == "r:id":
                        if isinstance(val, str) and val.startswith("rId"):
                            ids.add(val)
            lista.append((_descrie(ob), sorted(ids)))
            for i in ids:
                if i in harta:
                    tinte.setdefault(parte, set()).add(harta[i])
        gasite[parte] = lista
    z.close()
    return {"obiecte": gasite, "tinte": tinte}


def curata(intrare: Path, iesire: Path) -> dict:
    zin = zipfile.ZipFile(intrare)
    parti_noi, de_sters, sterse_rel = {}, set(), {}

    for parte in _parti_cu_continut(zin):
        try:
            rad = etree.fromstring(zin.read(parte))
        except Exception:
            continue
        obiecte = [e for e in rad.iter("{%s}object" % W)]
        if not obiecte:
            continue
        ids = set()
        for ob in obiecte:
            for et in ob.iter():
                for atr, val in et.attrib.items():
                    if (atr.endswith("}id") or atr.endswith("}embed")) and \
                            isinstance(val, str) and val.startswith("rId"):
                        ids.add(val)
            parinte = ob.getparent()
            parinte.remove(ob)
            # run ramas gol (doar rPr) se scoate si el
            if etree.QName(parinte).localname == "r":
                copii = [c for c in parinte if etree.QName(c).localname != "rPr"]
                if not copii:
                    bunic = parinte.getparent()
                    if bunic is not None:
                        bunic.remove(parinte)
        parti_noi[parte] = etree.tostring(rad, encoding="UTF-8",
                                          xml_declaration=True, standalone=True)
        sterse_rel[parte] = ids

        # relatiile si tintele lor
        cale_rel = _rels(parte)
        try:
            rrad = etree.fromstring(zin.read(cale_rel))
        except KeyError:
            continue
        for rel in list(rrad):
            if rel.get("Id") in ids:
                tinta = rel.get("Target")
                if tinta and not tinta.startswith("http"):
                    de_sters.add("word/" + tinta.lstrip("/"))
                rrad.remove(rel)
        parti_noi[cale_rel] = etree.tostring(rrad, encoding="UTF-8",
                                             xml_declaration=True, standalone=True)

    if not de_sters:
        zin.close()
        return {"obiecte_scoase": 0, "parti_sterse": []}

    ramase = [n for n in zin.namelist() if n not in de_sters]

    # Content_Types: scoatem Override-urile partilor disparute si Default-urile ramase fara fisiere
    ct = etree.fromstring(zin.read("[Content_Types].xml"))
    ext_ramase = {n.rsplit(".", 1)[-1].lower() for n in ramase if "." in n}
    for el in list(ct):
        nume = etree.QName(el).localname
        if nume == "Override" and el.get("PartName", "").lstrip("/") in de_sters:
            ct.remove(el)
        elif nume == "Default" and (el.get("Extension") or "").lower() not in ext_ramase:
            ct.remove(el)
    parti_noi["[Content_Types].xml"] = etree.tostring(ct, encoding="UTF-8",
                                                     xml_declaration=True, standalone=True)

    iesire.unlink(missing_ok=True)
    zout = zipfile.ZipFile(iesire, "w", zipfile.ZIP_DEFLATED)
    for info in zin.infolist():
        if info.filename in de_sters:
            continue
        date = parti_noi.get(info.filename, zin.read(info.filename))
        zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        zi.compress_type = info.compress_type
        zi.external_attr = info.external_attr
        zout.writestr(zi, date)
    zout.close()
    zin.close()
    return {"obiecte_scoase": sum(len(v) for v in sterse_rel.values()),
            "parti_sterse": sorted(de_sters)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Obiecte incorporate intr-un .docx.")
    ap.add_argument("comanda", choices=["verifica", "curata"])
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    a = ap.parse_args(argv)
    intrare = Path(a.input)

    if a.comanda == "verifica":
        rez = analizeaza(intrare)
        if not rez["obiecte"]:
            print("nu exista obiecte incorporate")
            return 0
        for parte, lista in rez["obiecte"].items():
            print("%s: %d obiect(e)" % (parte, len(lista)))
            for desc, ids in lista:
                print("   %s  relatii: %s" % (desc, ", ".join(ids)))
        for parte, t in rez["tinte"].items():
            print("   tinte in %s: %s" % (parte, ", ".join(sorted(t))))
        print("\nATENTIE: obiectele incorporate se vad ca pictograme in document, "
              "adesea cu numele fisierului din care provin.")
        return 1

    if not a.output:
        print("curata cere --output")
        return 2
    iesire = Path(a.output)
    if iesire.exists():
        print("iesirea exista deja; nu suprascriu")
        return 2
    rez = curata(intrare, iesire)
    print("obiecte scoase: %d" % rez["obiecte_scoase"])
    for p in rez["parti_sterse"]:
        print("  parte stearsa: %s" % p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
