#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compara_livrari.py

Arata ce a schimbat autorul in documentele pe care i le-am livrat.

Cum lucreaza
------------
Ia fiecare document din arhiva de livrari, il cauta pe disc SUB ACEEASI DENUMIRE si
compara copia de referinta cu ce e acolo acum. Nu ghiceste si nu cauta ce seamana: cand
documentul nu mai e sub numele livrat, il trece la "de intrebat", iar autorul da calea.

Evidenta si retragerea
----------------------
Fiecare verificare se scrie in evidenta, cu ziua si amprenta de pe disc. Un document
gasit neschimbat doua zile calendaristice la rand iese din comparare. Ii ramane numai
amprenta, care nu costa nimic, si reintra singur cand se schimba. Doua rulari in aceeasi
zi se socotesc una, ca sa nu se retraga documente dintr-o dubla verificare de dimineata.

Provenienta
-----------
Cand livrarea poarta o insemnare de provenienta, adica ciorna de la care am pornit, si
ciorna e neatinsa, modificarile se impart in doua: cele pe text scris de autor si cele pe
text scris de mine. Amandoua sunt lectii, de feluri diferite, si se arata separat. Cand
ciorna s-a schimbat intre timp, se spune pe fata si se arata toate la un loc.

Nu modifica niciun document. Doar citeste.

Utilizare
---------
    python compara_livrari.py                       # toate documentele din rotatie
    python compara_livrari.py --document "<cale>"   # unul singur, oricare ar fi starea lui
    python compara_livrari.py --json                # raport in JSON
    python compara_livrari.py --azi 2026-08-02      # zi simulata, pentru teste
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import zipfile
from datetime import date as _date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arhiva_livrari as al  # noqa: E402

EVIDENTA_VERIFICARI = al.ARHIVA / "verificari.json"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ZILE_LINISTITE_PENTRU_RETRAGERE = 2


# ------------------------------------------------------------------ evidenta
def citeste_verificari() -> dict:
    if not EVIDENTA_VERIFICARI.exists():
        return {}
    try:
        return json.loads(EVIDENTA_VERIFICARI.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def scrie_verificari(d: dict) -> None:
    al.ARHIVA.mkdir(parents=True, exist_ok=True)
    EVIDENTA_VERIFICARI.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


# -------------------------------------------------------------- citire .docx
def paragrafe(cale) -> list:
    with zipfile.ZipFile(cale) as z:
        from lxml import etree
        rad = etree.fromstring(z.read("word/document.xml"))
        out = []
        for p in rad.iter(W + "p"):
            t = "".join(n.text or "" for n in p.iter(W + "t")).strip()
            if t:
                out.append(t)
        return out


def numar_note(cale) -> int:
    with zipfile.ZipFile(cale) as z:
        if "word/footnotes.xml" not in z.namelist():
            return 0
        from lxml import etree
        rad = etree.fromstring(z.read("word/footnotes.xml"))
        return len([n for n in rad.iter(W + "footnote")
                    if n.get(W + "id") not in ("-1", "0", "1")])


# ----------------------------------------------------------------- comparare
def _asemanare(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def compara_texte(vechi: list, nou: list) -> dict:
    """Imparte diferentele in adaugate, scoase si rescrise.

    difflib da inlocuiri, nu rescrieri. Un paragraf inlocuit cu unul foarte asemanator e o
    rescriere, iar cu unul diferit sunt o stergere plus o adaugare. Pragul separa cele doua
    situatii, ca raportul sa nu arate 30 de stergeri si 30 de adaugari acolo unde autorul a
    limpezit 30 de fraze.
    """
    adaugate, scoase, rescrise = [], [], []
    s = difflib.SequenceMatcher(None, vechi, nou)
    for eticheta, i1, i2, j1, j2 in s.get_opcodes():
        if eticheta == "insert":
            adaugate.extend(nou[j1:j2])
        elif eticheta == "delete":
            scoase.extend(vechi[i1:i2])
        elif eticheta == "replace":
            a, b = vechi[i1:i2], nou[j1:j2]
            folosite = set()
            for x in a:
                pereche, scor = None, 0.0
                for k, y in enumerate(b):
                    if k in folosite:
                        continue
                    r = _asemanare(x, y)
                    if r > scor:
                        pereche, scor = k, r
                if pereche is not None and scor >= 0.55:
                    folosite.add(pereche)
                    rescrise.append((x, b[pereche]))
                else:
                    scoase.append(x)
            adaugate.extend(y for k, y in enumerate(b) if k not in folosite)
    return {"adaugate": adaugate, "scoase": scoase, "rescrise": rescrise}


def fraze_schimbate(vechi: str, nou: str) -> list:
    """Bucatile de text care difera intre doua variante ale aceluiasi paragraf."""
    a, b = vechi.split(), nou.split()
    out = []
    for eticheta, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if eticheta == "equal":
            continue
        out.append({
            "fel": {"insert": "adaugat", "delete": "scos", "replace": "schimbat"}[eticheta],
            "inainte": " ".join(a[i1:i2]),
            "dupa": " ".join(b[j1:j2]),
        })
    return out


def _provenienta_valabila(intrare: dict) -> tuple:
    """(paragrafele ciornei, mesaj). Paragrafele lipsesc cand nu se poate verifica."""
    prov = intrare.get("pornit_de_la")
    if not prov:
        return None, None
    c = Path(prov["cale"])
    if not c.is_file():
        return None, "ciorna de la care am pornit nu mai e la %s" % c
    if al.amprenta(c) != prov["amprenta"]:
        return None, "ciorna de la %s s-a schimbat, provenienta nu mai e verificabila" % c.name
    try:
        return paragrafe(c), None
    except Exception as e:  # noqa: BLE001
        return None, "ciorna nu s-a putut citi: %s" % e


def compara_document(intrare: dict) -> dict:
    """Compara o livrare cu ce e acum pe disc."""
    pe_disc = Path(intrare["cale"])
    rezultat = {"cale": str(pe_disc), "nume": pe_disc.name, "livrat_la": intrare["livrat_la"]}

    if not pe_disc.is_file():
        rezultat["stare"] = "negasit"
        return rezultat

    amp = al.amprenta(pe_disc)
    rezultat["amprenta"] = amp
    if amp == intrare["amprenta"]:
        rezultat["stare"] = "neschimbat"
        return rezultat

    referinta = al.cale_copie(intrare)
    try:
        vechi, nou = paragrafe(referinta), paragrafe(pe_disc)
    except Exception as e:  # noqa: BLE001
        rezultat["stare"] = "necitibil"
        rezultat["eroare"] = str(e)
        return rezultat

    d = compara_texte(vechi, nou)
    rezultat.update({
        "stare": "schimbat",
        "paragrafe": {"livrate": len(vechi), "acum": len(nou)},
        "note": {"livrate": numar_note(referinta), "acum": numar_note(pe_disc)},
        "adaugate": d["adaugate"],
        "scoase": d["scoase"],
        "rescrise": [{"inainte": a, "dupa": b, "fraze": fraze_schimbate(a, b)}
                     for a, b in d["rescrise"]],
    })

    # Provenienta: ce a fost scris de autor de la bun inceput si ce am scris eu.
    ale_autorului, mesaj = _provenienta_valabila(intrare)
    if mesaj:
        rezultat["provenienta"] = {"valabila": False, "motiv": mesaj}
    elif ale_autorului is not None:
        set_autor = {p.strip() for p in ale_autorului}

        def cui(text):
            if text.strip() in set_autor:
                return "text al autorului"
            return "text scris de mine"

        rezultat["provenienta"] = {"valabila": True}
        for x in rezultat["rescrise"]:
            x["origine"] = cui(x["inainte"])
        for i, t in enumerate(rezultat["scoase"]):
            rezultat["scoase"][i] = {"text": t, "origine": cui(t)}
    return rezultat


# -------------------------------------------------------------------- rotatie
def ruleaza(azi: _date, doar_documentul=None) -> dict:
    verificari = citeste_verificari()
    raport = {"zi": azi.isoformat(), "schimbate": [], "neschimbate": 0,
              "retrase": 0, "de_intrebat": [], "reintrate": []}

    tinte = al.documente()
    if doar_documentul:
        cheie = str(Path(doar_documentul)).lower()
        tinte = [i for i in tinte if i["cale"].lower() == cheie]
        if not tinte:
            raport["de_intrebat"].append({"cale": str(doar_documentul),
                                          "motiv": "nu exista in arhiva de livrari"})
            return raport

    for intrare in tinte:
        cale = intrare["cale"]
        stare = verificari.get(cale, {})
        retras = bool(stare.get("retras"))

        pe_disc = Path(cale)
        if not pe_disc.is_file():
            raport["de_intrebat"].append({
                "cale": cale,
                "motiv": "documentul nu mai e sub numele livrat; da-mi calea lui acum"})
            continue

        amp = al.amprenta(pe_disc)
        vazuta_ultima_data = stare.get("amprenta_pe_disc", intrare["amprenta"])
        nimic_nou = amp == vazuta_ultima_data
        zi_noua = stare.get("verificat_in_ziua") != azi.isoformat()

        # Linistit inseamna "nu s-a atins de cand m-am uitat ultima oara", nu "e la fel ca
        # la livrare". Confuzia dintre ele tinea un document modificat o data raportat ca
        # schimbat in fiecare zi, cu acelasi continut, si il scotea din regula de retragere.
        if nimic_nou and not doar_documentul:
            linistite = int(stare.get("zile_linistite", 0)) + (1 if zi_noua else 0)
            retras_acum = retras or linistite >= ZILE_LINISTITE_PENTRU_RETRAGERE
            verificari[cale] = {
                "verificat_in_ziua": azi.isoformat(),
                "amprenta_pe_disc": amp,
                "zile_linistite": linistite,
                "retras": retras_acum,
            }
            if retras_acum:
                raport["retrase"] += 1
            else:
                raport["neschimbate"] += 1
            continue

        if retras:
            raport["reintrate"].append(pe_disc.name)

        rez = compara_document(intrare)
        if rez["stare"] == "necitibil":
            raport["de_intrebat"].append({"cale": cale, "motiv": rez.get("eroare", "necitibil")})
            continue

        if rez["stare"] == "neschimbat":
            # S-a atins, dar a ajuns inapoi la forma livrata. Nimic de aratat.
            raport["neschimbate"] += 1
        else:
            raport["schimbate"].append(rez)
        verificari[cale] = {
            "verificat_in_ziua": azi.isoformat(),
            "amprenta_pe_disc": amp,
            "zile_linistite": 0,
            "retras": False,
        }

    scrie_verificari(verificari)
    return raport


# --------------------------------------------------------------------- raport
def tipareste(raport: dict) -> None:
    print("Revizuire, ziua %s\n" % raport["zi"])
    if not raport["schimbate"]:
        print("Nu s-a schimbat nimic.")
    for d in raport["schimbate"]:
        print("=" * 74)
        print(d["nume"])
        print("  livrat la %s | paragrafe %d -> %d | note %d -> %d"
              % (d["livrat_la"], d["paragrafe"]["livrate"], d["paragrafe"]["acum"],
                 d["note"]["livrate"], d["note"]["acum"]))
        prov = d.get("provenienta")
        if prov and not prov["valabila"]:
            print("  provenienta: %s" % prov["motiv"])

        def linie(t, marca):
            print("   %s %s" % (marca, " ".join(t.split())[:150]))

        if d["adaugate"]:
            print("\n  ADAUGATE (%d)" % len(d["adaugate"]))
            for t in d["adaugate"][:20]:
                linie(t, "+")
        if d["scoase"]:
            print("\n  SCOASE (%d)" % len(d["scoase"]))
            for t in d["scoase"][:20]:
                if isinstance(t, dict):
                    print("   - [%s] %s" % (t["origine"], " ".join(t["text"].split())[:130]))
                else:
                    linie(t, "-")
        if d["rescrise"]:
            print("\n  RESCRISE (%d)" % len(d["rescrise"]))
            for x in d["rescrise"][:20]:
                cap = "[%s] " % x["origine"] if x.get("origine") else ""
                print("   ~ %s%s" % (cap, " ".join(x["inainte"].split())[:120]))
                for f in x["fraze"][:4]:
                    print("       %-9s %s  ->  %s"
                          % (f["fel"], f["inainte"][:60] or "(nimic)", f["dupa"][:60] or "(nimic)"))
    print("\n" + "-" * 74)
    print("neschimbate: %d | retrase din rotatie: %d" % (raport["neschimbate"], raport["retrase"]))
    if raport["reintrate"]:
        print("reintrate in rotatie: %s" % ", ".join(raport["reintrate"]))
    for x in raport["de_intrebat"]:
        print("DE INTREBAT: %s  (%s)" % (Path(x["cale"]).name, x["motiv"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ce a schimbat autorul in documentele livrate")
    ap.add_argument("--document", help="o singura cale, indiferent de starea ei in rotatie")
    ap.add_argument("--json", action="store_true", help="raport in JSON")
    ap.add_argument("--azi", help="zi simulata, AAAA-LL-ZZ, pentru teste")
    args = ap.parse_args(argv)

    azi = datetime.strptime(args.azi, "%Y-%m-%d").date() if args.azi else _date.today()
    raport = ruleaza(azi, doar_documentul=args.document)
    if args.json:
        print(json.dumps(raport, ensure_ascii=False, indent=1))
    else:
        tipareste(raport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
