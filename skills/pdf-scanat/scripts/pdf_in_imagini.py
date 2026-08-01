#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdf_in_imagini.py

Scoate paginile unui PDF scanat ca fisiere imagine, ca sa poata fi CITITE.

De ce exista. Hotararile descarcate de pe portalul instantelor sunt aproape intotdeauna
scanari, adica fotografii de pagina fara strat de text. Extragerea de text intoarce gol pe
fiecare pagina, iar fisierele trec frecvent de 100 MB, peste limita citirii directe. Pe
1 august 2026, sentinta de infiintare a unei asociatii statea intr-un fisier de 134 MB cu
24 de pagini si zero caractere extractibile; numarul dosarului, al sentintei si al
certificatului de inscriere nu se puteau afla altfel.

Cum ocoleste dependintele. Extragerea de imagini din pypdf cere Pillow, care lipseste
frecvent. Aici nu se instaleaza nimic:
  - imaginile DCTDecode sunt deja JPEG in fisier, deci se scriu ca atare;
  - imaginile FlateDecode sunt esantioane brute comprimate cu zlib, exact compresia
    folosita si de PNG, deci pagina se reimpacheteaza direct, adaugand octetul de filtru 0
    la inceputul fiecarui rand.

    python pdf_in_imagini.py --input hotarare.pdf
    python pdf_in_imagini.py --input hotarare.pdf --pagini 1-4 --output D:\\Clienti\\X
    python pdf_in_imagini.py --input hotarare.pdf --pagini toate

Fara --output, imaginile se scriu langa PDF, intr-un folder cu numele lui.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import zlib

try:
    import pypdf
except ImportError:
    sys.exit("Lipseste pypdf. Instaleaza-l cu: pip install pypdf")


def _bucata_png(tip: bytes, continut: bytes) -> bytes:
    return (struct.pack(">I", len(continut)) + tip + continut
            + struct.pack(">I", zlib.crc32(tip + continut) & 0xFFFFFFFF))


def scrie_png(cale: str, latime: int, inaltime: int, canale: int, date: bytes) -> None:
    """PNG minimal, fara filtrare pe randuri. Tipul de culoare urmeaza numarul de canale."""
    rand = latime * canale
    brut = bytearray()
    for y in range(inaltime):
        brut.append(0)
        brut += date[y * rand:(y + 1) * rand]
    tip_culoare = {1: 0, 3: 2, 4: 6}[canale]
    ihdr = struct.pack(">IIBBBBB", latime, inaltime, 8, tip_culoare, 0, 0, 0)
    with open(cale, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_bucata_png(b"IHDR", ihdr))
        f.write(_bucata_png(b"IDAT", zlib.compress(bytes(brut), 6)))
        f.write(_bucata_png(b"IEND", b""))


def cmyk_in_rgb(date: bytes) -> bytes:
    """PNG nu cunoaste CMYK. Conversia e aproximativa, suficienta pentru un act scanat."""
    ies = bytearray(len(date) // 4 * 3)
    for i in range(0, len(date), 4):
        c, m, y, k = date[i], date[i + 1], date[i + 2], date[i + 3]
        j = i // 4 * 3
        ies[j] = (255 - c) * (255 - k) // 255
        ies[j + 1] = (255 - m) * (255 - k) // 255
        ies[j + 2] = (255 - y) * (255 - k) // 255
    return bytes(ies)


def _canale_din_marime(date: bytes, w: int, h: int, spatiu: str) -> int:
    """Spatiul de culoare declarat poate fi indirect, de pildă /ICCBased. Numarul real de
    canale se deduce atunci din cate esantioane au iesit la decomprimare."""
    if w and h:
        dedus = len(date) // (w * h)
        if dedus in (1, 3, 4):
            return dedus
    if "CMYK" in spatiu:
        return 4
    if "RGB" in spatiu:
        return 3
    return 1


def extrage_pagina(pagina, index: int, dest: str, prefix: str) -> str | None:
    resurse = pagina.get("/Resources")
    xobj = resurse.get("/XObject") if resurse else None
    if not xobj:
        return None
    xobj = xobj.get_object()
    for nume in xobj:
        ob = xobj[nume].get_object()
        if ob.get("/Subtype") != "/Image":
            continue
        w, h = int(ob.get("/Width", 0)), int(ob.get("/Height", 0))
        filtru = str(ob.get("/Filter"))
        spatiu = str(ob.get("/ColorSpace"))

        if "/DCTDecode" in filtru:
            cale = os.path.join(dest, f"{prefix}_p{index}.jpg")
            with open(cale, "wb") as f:
                f.write(ob._data)
            return cale

        if "/FlateDecode" in filtru:
            date = zlib.decompress(ob._data)
            canale = _canale_din_marime(date, w, h, spatiu)
            if canale == 4:
                date, canale = cmyk_in_rgb(date), 3
            asteptat = w * h * canale
            if len(date) < asteptat:
                print(f"  pagina {index}: date insuficiente, {len(date)} din {asteptat}, sar peste")
                return None
            cale = os.path.join(dest, f"{prefix}_p{index}.png")
            scrie_png(cale, w, h, canale, date[:asteptat])
            return cale

        print(f"  pagina {index}: filtru neacoperit, {filtru}")
        return None
    return None


def parseaza_pagini(text: str, total: int) -> list[int]:
    if not text or text.strip().lower() in ("toate", "all"):
        return list(range(total))
    iesire: list[int] = []
    for bucata in text.split(","):
        bucata = bucata.strip()
        if "-" in bucata:
            a, b = bucata.split("-", 1)
            iesire += list(range(int(a) - 1, int(b)))
        elif bucata:
            iesire.append(int(bucata) - 1)
    return [i for i in iesire if 0 <= i < total]


def main() -> int:
    ap = argparse.ArgumentParser(description="Paginile unui PDF scanat, ca imagini citibile.")
    ap.add_argument("--input", required=True, help="fisierul PDF")
    ap.add_argument("--pagini", default="1-4",
                    help="ex. 1-4, sau 1,3,7, sau 'toate' (implicit 1-4)")
    ap.add_argument("--output", help="folderul de iesire (implicit, langa PDF)")
    a = ap.parse_args()

    if not os.path.exists(a.input):
        return print(f"nu exista: {a.input}") or 2

    cititor = pypdf.PdfReader(a.input)
    total = len(cititor.pages)
    prefix = os.path.splitext(os.path.basename(a.input))[0].replace(" ", "_")[:40]
    dest = a.output or os.path.join(os.path.dirname(os.path.abspath(a.input)), prefix + "_pagini")
    os.makedirs(dest, exist_ok=True)

    indici = parseaza_pagini(a.pagini, total)
    print(f"{os.path.basename(a.input)}: {total} pagini, extrag {len(indici)}")

    text_gasit = False
    scrise = 0
    for i in indici:
        if (cititor.pages[i].extract_text() or "").strip():
            text_gasit = True
        cale = extrage_pagina(cititor.pages[i], i + 1, dest, prefix)
        if cale:
            scrise += 1
            print(f"  pagina {i+1} -> {os.path.basename(cale)} ({os.path.getsize(cale)} octeti)")

    print(f"\n{scrise} imagini in {dest}")
    if text_gasit:
        print("Atentie: paginile au si strat de text, deci PDF-ul se poate citi direct, "
              "fara conversie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
