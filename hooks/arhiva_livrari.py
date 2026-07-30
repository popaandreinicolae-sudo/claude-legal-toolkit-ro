#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arhiva_livrari.py

Pastreaza o copie de referinta a fiecarui document livrat autorului.

De ce exista
------------
Pe 30 iulie 2026 autorul a rescris 33 de paragrafe dintr-o exceptie livrata, a scos trei
note de subsol si a adaugat un argument pe Decizia ICCJ, RIL nr. 10/2019. Am putut vedea
asta numai fiindca mai aveam copia livrata in dosarul temporar al sesiunii, care dispare.
A doua zi comparatia ar fi fost imposibila, iar modificarile lui, adica tocmai ce e de
invatat, s-ar fi pierdut fara sa fie citite.

Copia de referinta nu are unde sa stea in dosarul clientului, unde ar incurca, si nici in
dosarul de sesiune, care nu supravietuieste. Sta aici, in afara amandurora.

Ce intra si ce nu
-----------------
Intra NUMAI ce produc eu pentru autor, adica ce iese din lantul de generare sau ce copiez
din dosarul meu de lucru in dosarele lui. Documentele lui, pe care doar le mut sau le
citesc, nu se arhiveaza: nu am fata de ce sa le compar, iar arhiva ar deveni o gramada de
acte de client stand in afara dosarelor lor.

Provenienta
-----------
Cand livrarea porneste de la o cioarna a autorului, se retine calea ciornei, ora si
amprenta ei, fara copie. La comparatie, amprenta spune daca ciorna e tot aceea; daca da,
modificarile se pot imparti in doua, cele pe text scris de el si cele pe text scris de
mine. Amandoua categoriile sunt lectii, dar de feluri diferite, si se arata separat.

Utilizare
---------
    python arhiva_livrari.py adauga "D:/Clienti/.../act.docx" [--sursa <cale ciorna>]
    python arhiva_livrari.py lista
    python arhiva_livrari.py ultima "D:/Clienti/.../act.docx"
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ARHIVA = Path(os.path.expanduser("~")) / ".claude" / "livrari"
EVIDENTA = ARHIVA / "evidenta.json"

# Documentele pentru care are rost o copie de referinta.
PAZITE = {".docx", ".doc", ".rtf", ".odt"}

# Dosarele mele de lucru. O copiere care PORNESTE de aici e o livrare; una care porneste
# din alt dosar al autorului e doar o mutare a unui fisier de-al lui.
DE_LUCRU = ("\\appdata\\local\\temp", "\\temp\\", "/temp/", "\\tmp\\", "/tmp/", "scratchpad")

# Locuri in care nu se arhiveaza nimic, oricare ar fi sursa.
NEARHIVABILE = DE_LUCRU + ("\\.claude\\livrari", "/.claude/livrari", "\\.cache\\", "/.cache/")


def _jos(cale) -> str:
    return str(cale).replace("/", "\\").lower()


def e_dosar_de_lucru(cale) -> bool:
    """Calea sta intr-un dosar de lucru al meu."""
    return any(m.replace("/", "\\") in _jos(cale) for m in DE_LUCRU)


def e_nearhivabil(cale) -> bool:
    return any(m.replace("/", "\\") in _jos(cale) for m in NEARHIVABILE)


def e_livrare(tinta, sursa=None) -> bool:
    """Documentul asta e produs de mine pentru autor?

    Da, cand ajunge intr-un dosar al lui si vine din dosarul meu de lucru. Fara sursa
    cunoscuta, raspunsul e nu: mai bine ratam o arhivare decat sa umplem arhiva cu
    documentele autorului, pe care oricum nu am cu ce sa le compar.
    """
    tinta = Path(tinta)
    if tinta.suffix.lower() not in PAZITE or not tinta.is_file():
        return False
    if e_nearhivabil(tinta):
        return False
    return sursa is not None and e_dosar_de_lucru(sursa)


def amprenta(cale) -> str:
    h = hashlib.sha256()
    with open(cale, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def citeste_evidenta() -> list:
    if not EVIDENTA.exists():
        return []
    try:
        return json.loads(EVIDENTA.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []


def scrie_evidenta(intrari: list) -> None:
    ARHIVA.mkdir(parents=True, exist_ok=True)
    EVIDENTA.write_text(json.dumps(intrari, ensure_ascii=False, indent=1), encoding="utf-8")


def _slug(nume: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", nume)[:80]


def _provenienta(sursa_ciorna) -> dict | None:
    """Calea, ora si amprenta ciornei de la care am pornit. Fara copie."""
    if not sursa_ciorna:
        return None
    c = Path(sursa_ciorna)
    if not c.is_file():
        return None
    return {
        "cale": str(c),
        "citita_la": datetime.fromtimestamp(c.stat().st_mtime).isoformat(timespec="seconds"),
        "amprenta": amprenta(c),
    }


def adauga(cale, motiv: str = "livrare", ciorna=None, cale_livrata=None) -> dict | None:
    """Pune o copie in arhiva. Intoarce intrarea, sau None cand nu e cazul.

    cale: de unde se ia continutul.
    cale_livrata: sub ce cale se inregistreaza, cand difera de `cale`. Serveste cand
      arhivez direct din dosarul meu de lucru documentul care tocmai a plecat; continutul
      e acolo, dar comparatia il va cauta la calea de livrare. Fara ea, propriul filtru de
      dosare de lucru ar refuza arhivarea, cum s-a intamplat la prima incercare.
    """
    cale = Path(cale)
    if not cale.is_file() or cale.suffix.lower() not in PAZITE:
        return None
    inregistrata = Path(cale_livrata) if cale_livrata else cale
    if e_nearhivabil(inregistrata):
        return None

    amp = amprenta(cale)
    intrari = citeste_evidenta()
    # Acelasi continut la aceeasi cale nu se arhiveaza de doua ori.
    for i in intrari:
        if i["cale"].lower() == str(inregistrata).lower() and i["amprenta"] == amp:
            return None

    acum = datetime.now()
    dosar = ARHIVA / acum.strftime("%Y-%m-%d")
    dosar.mkdir(parents=True, exist_ok=True)
    copie = dosar / ("%s__%s%s" % (_slug(inregistrata.stem), acum.strftime("%H%M%S"),
                                   inregistrata.suffix))
    while copie.exists():                       # nu se suprascrie nimic, nici in arhiva
        copie = copie.with_name(copie.stem + "_bis" + copie.suffix)
    shutil.copy2(cale, copie)

    intrare = {
        "cale": str(inregistrata),
        "copie": str(copie.relative_to(ARHIVA)).replace("\\", "/"),
        "livrat_la": acum.isoformat(timespec="seconds"),
        "amprenta": amp,
        "octeti": cale.stat().st_size,
        "motiv": motiv,
    }
    prov = _provenienta(ciorna)
    if prov:
        intrare["pornit_de_la"] = prov
    intrari.append(intrare)
    scrie_evidenta(intrari)
    return intrare


def ultima(cale) -> dict | None:
    """Cea mai recenta copie arhivata pentru o cale data."""
    cheie = str(Path(cale)).lower()
    potrivite = [i for i in citeste_evidenta() if i["cale"].lower() == cheie]
    return max(potrivite, key=lambda i: i["livrat_la"]) if potrivite else None


def documente() -> list:
    """Cate o intrare pe document, cea mai recenta livrare a fiecaruia."""
    dupa_cale: dict = {}
    for i in citeste_evidenta():
        cheie = i["cale"].lower()
        if cheie not in dupa_cale or i["livrat_la"] > dupa_cale[cheie]["livrat_la"]:
            dupa_cale[cheie] = i
    return sorted(dupa_cale.values(), key=lambda i: i["livrat_la"], reverse=True)


def cale_copie(intrare: dict) -> Path:
    return ARHIVA / intrare["copie"]


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("comenzi: adauga <cale> [--sursa <ciorna>], lista, ultima <cale>")
        return 1
    comanda = argv[0]

    if comanda == "adauga":
        if len(argv) < 2:
            print("Lipseste calea.")
            return 1
        ciorna = None
        if "--sursa" in argv:
            k = argv.index("--sursa")
            ciorna = argv[k + 1] if k + 1 < len(argv) else None
        intrare = adauga(argv[1], ciorna=ciorna)
        if intrare:
            print("arhivat: %s -> %s" % (Path(intrare["cale"]).name, intrare["copie"]))
            if intrare.get("pornit_de_la"):
                print("  pornit de la: %s" % intrare["pornit_de_la"]["cale"])
        else:
            print("nimic de arhivat (tip nepotrivit, dosar de lucru, sau continut deja arhivat)")
        return 0

    if comanda == "lista":
        intrari = citeste_evidenta()
        if not intrari:
            print("arhiva e goala")
            return 0
        for i in sorted(intrari, key=lambda x: x["livrat_la"]):
            print("%s  %8d  %s" % (i["livrat_la"], i["octeti"], Path(i["cale"]).name[:66]))
        print("\n%d copii, %d documente distincte" % (len(intrari), len(documente())))
        return 0

    if comanda == "ultima":
        if len(argv) < 2:
            print("Lipseste calea.")
            return 1
        i = ultima(argv[1])
        print(json.dumps(i, ensure_ascii=False, indent=1) if i else "nicio copie arhivata")
        return 0

    print("comenzi: adauga, lista, ultima")
    return 1


if __name__ == "__main__":
    sys.exit(main())
