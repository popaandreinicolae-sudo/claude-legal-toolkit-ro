#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_citari.py

Test de regresie pentru extragerea citarilor din citation_core.

De ce exista. Pe 30 iulie 2026, un audit al stratului anti-halucinare a aratat ca
extractorul rata tocmai formele pe care le folosim in acte:

  - "Decizia nr. 363 din 7 mai 2015", forma cu data completa, obligatorie in citarea
    juridica romaneasca. Pattern-ul cerea anul imediat dupa "din", deci prindea numai
    forma scurta "Decizia nr. 22/2016". Din cele 7 decizii citate in excepția de
    neconstituționalitate livrata in dosarul Transcarpat, stratul nu vedea niciuna.
  - "potrivit Directivei 2009/73/CE", forma flexionata, mai frecventa in text decat
    nominativul. Clasa [aei] prindea "Directive" si se oprea inainte de "i", deci
    verificarea de act abrogat nu se declansa niciodata pe ea.
  - "Regulamentul (UE) 2016/679". Numerotarea europeana s-a inversat in 2015, an/numar
    in loc de numar/an. Cerand patru cifre la final, pattern-ul rata tot ce e adoptat
    dupa 2015, inclusiv GDPR.
  - "Decizia nr. 1.205 din 20 septembrie 2011", numarul scris cu separator de mii.
  - "Ministerul Finantelor Publice" cazut peste un sfarsit de rand. Potrivirea pe subsir
    simplu il rata tocmai in livrabile, unde textul e formatat, nu in teste.

Un strat fail-open care rateaza tacut e mai rau decat lipsa lui, fiindca raporteaza curat.
De aceea formele stau scrise aici, ca lista, si se verifica la fiecare rulare.

    python selftest_citari.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import citation_core as cc

# (text, tip asteptat, numar, an). None la numar inseamna "nu trebuie sa gaseasca nimic".
CAZURI = [
    # Decizii, forma cu data completa. Regresia care a motivat testul.
    ("Decizia nr. 363 din 7 mai 2015", "ccr", "363", "2015"),
    ("Decizia nr. 22 din 20 ianuarie 2016", "ccr", "22", "2016"),
    ("Decizia nr. 668 din 18 mai 2011", "ccr", "668", "2011"),
    ("Decizia nr. 51 din 16 februarie 2016", "ccr", "51", "2016"),
    ("Deciziei nr. 405 din 15 iunie 2016", "ccr", "405", "2016"),
    ("Decizia nr. 17 din 21 ianuarie 2015", "ccr", "17", "2015"),
    # Numar cu separator de mii, cum scrie Curtea.
    ("Decizia nr. 1.205 din 20 septembrie 2011", "ccr", "1205", "2011"),
    ("Decizia nr. 1.313 din 4 octombrie 2011", "ccr", "1313", "2011"),
    # Forma scurta si tokenul de instanta.
    ("Decizia CCR nr. 22/2016", "ccr", "22", "2016"),
    ("Decizia ICCJ nr. 64/2026", "ccr", "64", "2026"),
    ("Decizia nr. 302/2017", "ccr", "302", "2017"),
    # Acte interne.
    ("Legea nr. 295/2004 privind regimul armelor", "act", "295", "2004"),
    ("Legea nr. 24/2000 privind normele de tehnica legislativa", "act", "24", "2000"),
    ("OUG nr. 158/1999 privind regimul de control", "act", "158", "1999"),
    ("Legea nr. 47/1992 privind Curtea Constitutionala", "act", "47", "1992"),
    ("Legea nr. 286/2009 privind Codul penal", "act", "286", "2009"),
    # Formele scrise in litere si cu diacritice, cele care ajung efectiv in acte.
    # Pana pe 30 iulie 2026 stratul le rata, desi prindea abrevierile.
    ("Hotararea Guvernului nr. 130/2005", "act", "130", "2005"),
    ("Hotărârea Guvernului nr. 11/2018", "act", "11", "2018"),
    ("H.G. nr. 11/2018 pentru aprobarea normelor", "act", "11", "2018"),
    ("Ordonanța de urgență a Guvernului nr. 158/1999", "act", "158", "1999"),
    ("Ordonanţa de urgenţă a Guvernului nr. 158/1999", "act", "158", "1999"),
    ("Ordonanța Guvernului nr. 2/2001 privind contraventiile", "act", "2", "2001"),
    ("Legea nr. 266/2022 pentru modificarea Legii nr. 232/2016", "act", "266", "2022"),
    # Directive, toate formele flexionate.
    ("Directiva 2009/73/CE privind gazele", "eu_directive", "2009", "73"),
    ("potrivit Directivei 2009/73/CE, in vigoare", "eu_directive", "2009", "73"),
    ("conform Directivelor 2009/72/CE si 2019/944", "eu_directive", "2009", "72"),
    ("Directiva (UE) 2021/555 privind controlul armelor", "eu_directive", "2021", "555"),
    ("Directiva 91/477/CEE", "eu_directive", "91", "477"),
    # Regulamente, ambele numerotari.
    ("Regulamentul (UE) 2016/679 privind protectia datelor", "eu_regulation", "679", "2016"),
    ("Regulamentului 2016/679 privind protectia datelor", "eu_regulation", "679", "2016"),
    ("Regulamentul nr. 1234/2013", "eu_regulation", "1234", "2013"),
    # Cauze CJUE.
    ("Hotararea in cauza C-402/09 Tatu", "cjue", "C-402", "09"),
    # Ce NU trebuie sa produca citari. Un strat care da fals-pozitive se ignora, iar
    # atunci nu mai apara nimic.
    ("Deciziile instantelor de fond au fost casate in 2015.", "ccr", None, None),
    ("Prin decizie definitiva, in anul 2016, s-a dispus.", "ccr", None, None),
    ("Art. 342 alin. (5) din Codul penal, cu 2 infractiuni si 5 ani.", "ccr", None, None),
]

# Semnale locale care trebuie sa apara, chiar cand textul e formatat pe mai multe rânduri.
TEXT_SEMNALE = """Nota de fundamentare.

Potrivit Directivei 2009/73/CE privind piata interna a gazelor naturale, in vigoare,
operatorul are obligatia de a asigura accesul. Ministerul Finantelor
Publice a aprobat alocarea. RADET a raportat pierderi, iar E-Distributie a confirmat
indicatorii.

Transpunerea directivei NIS s-a facut prin Legea 58/2019, act care stabileste
obligatiile operatorilor de servicii esentiale in materie de securitate cibernetica.
"""

SEMNALE_ASTEPTATE = [
    "Ministerul Finantelor Publice",   # cade peste sfarsitul de rand
    "RADET",
    "E-Distributie",
    "Legea 58/2019",
    "2009/73/CE",                      # act abrogat citat ca in vigoare
]


def main() -> int:
    esecuri = 0

    print("=== extragerea citarilor ===")
    for text, tip, numar, an in CAZURI:
        gasite = [c for c in cc.extract_citations(text) if c["kind"] == tip]
        if numar is None:
            ok = not gasite
            detaliu = "curat" if ok else "FALS-POZITIV %s" % [(c["number"], c["year"]) for c in gasite]
        else:
            ok = bool(gasite) and gasite[0]["number"] == numar and gasite[0]["year"] == an
            detaliu = ("%s/%s" % (gasite[0]["number"], gasite[0]["year"])) if gasite else "RATAT"
        if not ok:
            esecuri += 1
        print("  %-6s %-52s %s" % ("ok" if ok else "ESEC", text[:52], detaliu))

    print()
    print("=== semnale locale, pe text formatat ===")
    raport = cc.verify_text(TEXT_SEMNALE, cap=40, network=False)
    problems = " | ".join(raport.get("problems", []))
    for asteptat in SEMNALE_ASTEPTATE:
        ok = asteptat in problems
        if not ok:
            esecuri += 1
        print("  %-6s %s" % ("ok" if ok else "ESEC", asteptat))

    print()
    if esecuri:
        print("REZULTAT: %d esec(uri)" % esecuri)
        return 1
    print("REZULTAT: toate formele de citare sunt prinse, fara fals-pozitive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
