# -*- coding: utf-8 -*-
"""Ce pun in seama unui paragraf de hotarare trebuie sa fie ACOLO, cuvant cu cuvant.

Regula autorului, 31 iulie 2026: "cand citezi o hotarare, indiferent de instanta, citarea
va fi EXACT ce a zis instanta. ce extrapolam noi de acolo sau concluzionam e altceva, dar
cand zicem ca CCR sau alta instanta zice la par. 20 X chestie, atunci X chestie sa zica,
nu altceva pe care il schimbam noi."

Ce a declansat-o: scrisesem "reţinând la paragraful 20 ca legea penala, atunci cand se
raporteaza la notiuni specifice ALTEI RAMURI DE DREPT...". Decizia nr. 603/2015 spune la
paragraful 20 "Codul penal actual [...] atunci cand se raporteaza la notiuni specifice
DREPTULUI CIVIL". Doi termeni schimbati, amandoi in directia tezei mele. Structura frazei
ramasese identica, deci parea comprimare.

O parafraza fara ghilimele nu are ancora: se verifica doar fata de sens, iar sensul e locul
in care alunec. De aceea verificarea de aici cere DOUA lucruri:

  1. orice atribuire la un paragraf numit poarta un citat intre ghilimele;
  2. citatul apare verbatim CHIAR IN ACEL paragraf al hotararii.

Extrapolarea ramane permisa, dar ca fraza separata, in vocea noastra, fara numar de paragraf.

Consultativ si fail-open. Sursa e sintact, prin acelasi cache si aceeasi sesiune unica
folosite de sustineri_dispozitiv.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_AICI = Path(__file__).resolve().parent
if str(_AICI) not in sys.path:
    sys.path.insert(0, str(_AICI))

import sustineri_dispozitiv as SD                        # noqa: E402

RE_PARAGRAF = re.compile(
    r"(?:paragraf(?:ul|ele|e)?|par\.|pct\.|punct(?:ul|ele)?)\s*(\d{1,3})",
    re.IGNORECASE)

# Ghilimele romanesti, tipografice si drepte.
RE_CITAT = re.compile(r"[„“]([^„“”\"]{12,})[”\"]|\"([^\"]{12,})\"")

# Verbe de atribuire. Fara ele, "paragraful 20" e o simpla trimitere, nu o afirmatie.
RE_ATRIBUIRE = re.compile(
    r"a\s+re[țţ]inut|re[țţ]in[âa]nd|a\s+statuat|a\s+ar[ăa]tat|ar[ăa]t[âa]nd"
    r"|a\s+constatat|constat[âa]nd|a\s+stabilit|stabilind|a\s+subliniat|a\s+precizat"
    r"|potrivit\s+c[ăa]ruia|potrivit\s+c[ăa]reia|[îi]n\s+care\s+a\s+re[țţ]inut",
    re.IGNORECASE)


def _plat(s: str) -> str:
    return " ".join(SD._fara_diacritice(s).lower().split())


_ABREV = re.compile(r"\b(art|nr|alin|lit|pct|par|paragr|dec|H\.G|O\.U\.G|O\.G|M\.\s?Of)\.")

# Teza e pusa in seama unei INSTANTE, nu a unei autoritati administrative.
RE_INSTANTA = re.compile(
    r"Cur(?:tea|[țţ]ii)|[ÎI]nalta\s+Curte|instan[țţ]a\s+suprem[ăa]|instan[țţ]a\s+"
    r"de\s+contencios\s+constitu[țţ]ional|CCR|CJUE|CEDO",
    re.IGNORECASE)

# Identificatori de hotarare, altii decat "Decizia nr. N/AAAA": cauze CJUE si CEDO.
RE_ALT_IDENTIFICATOR = re.compile(
    r"\bC-\d{1,4}\s*/\s*\d{2,4}\b|Hot[ăa]r[âa]rea\s+din\s+\d", re.IGNORECASE)

# Aparatul de citare: publicarea in Monitorul Oficial, cu numar si data.
RE_APARAT = re.compile(
    r"publicat[ăa]?\s+[îi]n\s+Monitorul\s+Oficial[^,;]*(?:,\s*Partea\s+I)?"
    r"(?:,\s*nr\.?\s*[\d.]+)?(?:\s+din\s+[^,;.]{0,32})?",
    re.IGNORECASE)


def fraza_din_jur(bucata: str, poz: int) -> str:
    """Propozitia care contine pozitia data, cu abrevierile juridice protejate.

    O fereastra de latime fixa nu e de ajuns: la note de subsol ea trece peste sfarsitul
    frazei si aduna text strain, iar raportul dintre citat si parafraza iese fals. Asa a
    fost semnalata gresit o nota in care autorul citase corect Decizia nr. 22/2016.
    """
    protejat = _ABREV.sub(lambda m: m.group(0)[:-1] + "\x00", bucata)
    start, sfarsit = 0, len(bucata)
    for m in re.finditer(r"[.!?]\s+", protejat):
        if m.end() <= poz:
            start = m.end()
        else:
            sfarsit = m.start() + 1
            break
    return bucata[start:sfarsit]


def paragrafe_numerotate(text: str) -> dict:
    """{numar: text}. Hotararile CCR isi numeroteaza paragrafele '24. Text...'."""
    plat = " ".join(text.split())
    poz = [(int(m.group(1)), m.start(), m.end())
           for m in re.finditer(r"(?:^|\s)(\d{1,3})\.\s+(?=[A-ZÎÂȘȚĂÎ„])", plat)]
    # pastreaza doar secventa crescatoare, ca sa nu prinda "art. 6." sau "nr. 1."
    curat, astept = [], 0
    for nr, i, j in poz:
        if nr == astept + 1:
            curat.append((nr, i, j))
            astept = nr
    out = {}
    for k, (nr, i, j) in enumerate(curat):
        sfarsit = curat[k + 1][1] if k + 1 < len(curat) else len(plat)
        out[nr] = plat[j:sfarsit].strip()
    return out


def analizeaza(text: str, cache: dict) -> list:
    linii = [l.strip() for l in text.split("\n") if l.strip()]

    # Ce decizii trebuie aduse: cele care au in aceeasi linie o trimitere la paragraf.
    nevoi, sarcini, orfane = set(), [], []
    for linie in linii:
        ultima = None
        # parcurg linia in ordine, tinand minte ultima decizie citata
        evenimente = [("dec", m.start(), (m.group(1), m.group(2) or m.group(3)))
                      for m in SD.RE_DECIZIE.finditer(linie)]
        evenimente += [("par", m.start(), m.group(1)) for m in RE_PARAGRAF.finditer(linie)]
        evenimente.sort(key=lambda e: e[1])
        for tip, poz, val in evenimente:
            if tip == "dec":
                ultima = val
            elif ultima:
                sarcini.append((linie, ultima, int(val), poz))
                nevoi.add(ultima)
            else:
                # Trimitere la un paragraf fara nicio decizie numita in acelasi paragraf de
                # document. Antecedentul sta intr-o fraza de tipul "aceeasi decizie" si se
                # rupe la orice reordonare. Asa a ajuns paragraful 27 din Decizia nr.
                # 363/2015 sa atarne, dupa o mutare, de Decizia nr. 405/2016.
                stanga = max(0, poz - 350)
                fereastra = linie[stanga:poz + 450]
                jur = fraza_din_jur(fereastra, poz - stanga)
                # Se semnaleaza numai cand paragraful INTREG nu poarta niciun identificator
                # de hotarare, iar teza e pusa in seama unei instante. Altfel s-ar aprinde
                # pe punctele unei adrese administrative si pe cauzele CJUE sau CEDO, care
                # se identifica altfel decat prin "Decizia nr.".
                if (RE_ATRIBUIRE.search(jur) and RE_INSTANTA.search(jur)
                        and not RE_ALT_IDENTIFICATOR.search(linie)):
                    orfane.append({
                        "nivel": "EROARE", "decizie": "nenumita", "paragraf": int(val),
                        "motiv": "trimitere la paragraf fara decizie numita in acelasi "
                                 "paragraf; antecedentul se sprijina pe context si se rupe "
                                 "la reordonare",
                        "fraza": jur[:260],
                    })
    if not sarcini:
        return orfane

    SD.incarca(sorted(nevoi), cache)
    gasite = []
    for linie, (numar, an), nr_par, poz in sarcini:
        eticheta = "%s/%s" % (numar, an)
        date = cache.get("ccr:%s/%s" % (numar, an), {})
        if not date.get("text"):
            gasite.append({"nivel": "NEVERIFICAT", "decizie": eticheta, "paragraf": nr_par,
                           "motiv": date.get("eroare", "textul deciziei nu a putut fi adus de pe sintact"),
                           "fraza": linie[:220]})
            continue

        # Fereastra fixa in jurul trimiterii, NU o taiere pe punct.
        # "par. 24" contine un punct, deci un split naiv pe punct pierde marcajul si, cand
        # nu-l gaseste, cade inapoi pe toata linia. Intr-un bloc de note de subsol linia
        # are mii de caractere si aduna citate din alte decizii: asa a fost pus in seama
        # Deciziei nr. 363/2015 un citat pe care autorul il atribuise corect Deciziei
        # nr. 22/2016. O fereastra marginita nu poate face asta.
        stanga = max(0, poz - 350)
        fereastra = linie[stanga:poz + 450]
        bucata = fraza_din_jur(fereastra, poz - stanga)

        atrib = RE_ATRIBUIRE.search(bucata)
        if not atrib:
            continue                       # trimitere simpla, nu pune nimic in seama instantei

        # Clauza pusa efectiv in seama instantei incepe la verbul de atribuire.
        clauza = bucata[atrib.start():]
        citate = [c for pereche in RE_CITAT.findall(clauza) for c in pereche if c]

        # Nu e destul sa EXISTE un citat undeva in preajma. Un citat scurt si incidental,
        # de tipul denumirii sintagmei analizate, lasa sa treaca o parafraza lunga: asa a
        # trecut "legea penala [...] notiuni specifice altei ramuri de drept" langa
        # „raporturi comerciale". Se cere ca partea atribuita sa fie PREPONDERENT verbatim.
        # Aparatul de citare nu e continut pus in seama instantei, deci nu se numara
        # ca parafraza: numarul deciziei, Monitorul Oficial si trimiterea la paragraf.
        util = RE_APARAT.sub(" ", clauza)
        util = SD.RE_DECIZIE.sub(" ", util)
        util = RE_PARAGRAF.sub(" ", util)

        in_ghilimele = sum(len(c) for c in citate)
        parafrazat = max(0, len(" ".join(util.split())) - in_ghilimele)
        if parafrazat > 120 and in_ghilimele < 0.5 * len(clauza):
            gasite.append({
                "nivel": "EROARE", "decizie": eticheta, "paragraf": nr_par,
                "motiv": "atribuire la un paragraf numit, preponderent parafrazata "
                         "(%d caractere in afara ghilimelelor); ce se pune in seama "
                         "instantei se citeaza verbatim" % parafrazat,
                "fraza": clauza[:260],
            })
            continue
        if not citate:
            gasite.append({
                "nivel": "EROARE", "decizie": eticheta, "paragraf": nr_par,
                "motiv": "atribuire la un paragraf numit, fara citat intre ghilimele; "
                         "parafraza nu se poate verifica si aluneca",
                "fraza": clauza[:260],
            })
            continue

        paragrafe = paragrafe_numerotate(date["text"])
        tinta = _plat(paragrafe.get(nr_par, ""))
        tot = _plat(date["text"])
        if not tinta:
            gasite.append({
                "nivel": "NEVERIFICAT", "decizie": eticheta, "paragraf": nr_par,
                "motiv": "paragraful %d nu a putut fi izolat in textul deciziei%s"
                         % (nr_par, " (" + date["avertisment_sursa"] + ")"
                            if date.get("avertisment_sursa") else ""),
                "fraza": clauza[:200],
            })
            continue
        for citat in citate:
            c = _plat(citat)
            if len(c) < 12:
                continue
            if tinta and c in tinta:
                continue
            if c in tot:
                unde = [n for n, t in paragrafe.items() if c in _plat(t)]
                gasite.append({
                    "nivel": "EROARE", "decizie": eticheta, "paragraf": nr_par,
                    "motiv": "citatul nu e in paragraful %d, ci in %s" % (
                        nr_par, ", ".join(str(u) for u in unde) or "alta parte a deciziei"),
                    "fraza": citat[:200],
                })
            else:
                gasite.append({
                    "nivel": "EROARE", "decizie": eticheta, "paragraf": nr_par,
                    "motiv": "citatul nu apare verbatim nicaieri in decizie",
                    "fraza": citat[:200],
                })

    vazute, unice = set(), []
    for g in orfane + gasite:
        cheie = (g["nivel"], g["decizie"], g["paragraf"], g["motiv"], g["fraza"][:80])
        if cheie in vazute:
            continue
        vazute.add(cheie)
        unice.append(g)
    return unice


def main(argv=None) -> int:
    SD.taci_la_inchidere()
    ap = argparse.ArgumentParser(description="Verifica atribuirile la paragrafe de hotarare.")
    ap.add_argument("cale")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        text = SD.citeste(Path(a.cale))
    except Exception as e:
        print("nu am putut citi documentul: %s" % e)
        return 0
    cache = SD._cache_citeste()
    try:
        rez = analizeaza(text, cache)
    except Exception as e:
        print("verificare intrerupta (%s); stratul e consultativ" % type(e).__name__)
        return 0
    SD._cache_scrie(cache)

    if a.json:
        print(json.dumps(rez, ensure_ascii=False, indent=1))
        return 0
    if not rez:
        print("toate atribuirile la paragraf sunt citate si verbatim")
        return 0
    for r in rez:
        print("\n%s  Decizia nr. %s, paragraful %s" % (r["nivel"], r["decizie"], r["paragraf"]))
        print("  %s" % r["motiv"])
        print("  in text: %s" % r["fraza"])
    print("\n%d atribuiri de reparat" % len(rez))
    return 0


if __name__ == "__main__":
    sys.exit(main())
