"""Selftest pentru forma interogarii trimise la sintact.ro. Ruleaza offline.

    python selftest_sintact_query.py

Pazeste reparatia din 30 iulie 2026. `queryString` se potriveste conjunctiv si tine
cont de vecinatatea cuvintelor, deci nu se comporta ca un motor web: fiecare termen
in plus restrange, iar citarile trebuie scrise oficial, cu "nr." intre denumirea
actului si numar.

Cazul care a demascat problema: Normele metodologice de aplicare a Legii nr. 295/2004,
aprobate prin HG nr. 11/2018, pareau sa lipseasca din Sintact. Existau. Interogarile
erau scrise fara "nr." si cu termeni in plus, iar masuratoarea din ziua aceea, pe
categoria legislatie, arata cat de mult conteaza:

    "Legea 295/2004 privind regimul armelor"      ->    5 rezultate
    "Legea nr. 295/2004 privind regimul armelor"  ->  228 rezultate

Daca cineva scoate normalizarea din `search` sau strica `insereaza_nr`, testul pica.
Nu atinge reteaua, verifica numai transformarea interogarii.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sintact_client import (  # noqa: E402
    contine_citare,
    insereaza_nr,
    scoate_nr,
    _intercaleaza,
    _trepte_scurtare,
)

FAILS = []


def check(label, cond, detail=""):
    if not cond:
        FAILS.append(label)
    print(f"  [{'OK  ' if cond else 'FAIL'}] {label}{(' -> ' + detail) if detail and not cond else ''}")


# ── 1. Inserarea lui "nr." ───────────────────────────────────────────────────
print("\n1. Citarile pleaca in forma oficiala")

CAZURI = [
    ("Legea 295/2004 privind regimul armelor",
     "Legea nr. 295/2004 privind regimul armelor"),
    ("Legii 295/2004", "Legii nr. 295/2004"),
    ("HG 11/2018", "HG nr. 11/2018"),
    ("Ordinul 1115/2015 criterii licenta", "Ordinul nr. 1115/2015 criterii licenta"),
    ("OUG 155/2024", "OUG nr. 155/2024"),
    ("ordonanta de urgenta 57/2019", "ordonanta de urgenta nr. 57/2019"),
    # Diacriticele nu trebuie sa impiedice potrivirea, iar textul original se pastreaza.
    ("Hotărârea 11/2018", "Hotărârea nr. 11/2018"),
    ("Ordonanța 38/2024", "Ordonanța nr. 38/2024"),
    # Spatiere neregulata in jurul barei.
    ("Legea 407 / 2006", "Legea nr. 407/2006"),
    # Mai multe citari in aceeasi interogare.
    ("Legea 407/2006 si Ordinul 1115/2015",
     "Legea nr. 407/2006 si Ordinul nr. 1115/2015"),
]
for intrare, asteptat in CAZURI:
    obtinut = insereaza_nr(intrare)
    check(f"{intrare!r} -> {asteptat!r}", obtinut == asteptat, f"obtinut {obtinut!r}")

print("\n2. Idempotenta si neutralitate")
IDEMPOTENTE = [
    "Legea nr. 295/2004 privind regimul armelor",
    "HG nr. 11/2018",
    "Ordinul nr. 1115/2015",
    "Legea nr.295/2004",
]
for q in IDEMPOTENTE:
    o = insereaza_nr(q)
    check(f"a doua trecere nu mai schimba: {q!r}", insereaza_nr(o) == o, f"obtinut {o!r}")

check("citarea deja normalizata ramane identica",
      insereaza_nr("Legea nr. 295/2004") == "Legea nr. 295/2004")

NEATINSE = [
    "criterii de acordare a licentei pentru gestionarii fondurilor cinegetice",
    "regimul armelor si al munitiilor",
    "dosar 13058/302/2026",          # numar de dosar, nu citare de act
    "art. 3 alin. (2)",
]
for q in NEATINSE:
    check(f"interogare fara citare, neatinsa: {q!r}", insereaza_nr(q) == q,
          f"obtinut {insereaza_nr(q)!r}")

# ── 3. Detectarea citarii ────────────────────────────────────────────────────
print("\n3. Detectarea citarii")
for q in ["Legea 295/2004", "HG nr. 11/2018", "Hotărârea 11/2018", "Ordinul 1115/2015"]:
    check(f"vede citarea in {q!r}", contine_citare(q))
for q in ["regimul armelor", "gestionar fond cinegetic", "art. 3 alin. (2)"]:
    check(f"nu inventeaza citare in {q!r}", not contine_citare(q))

# ── 3b. Perechea fara "nr." ──────────────────────────────────────────────────
print("\n3b. Forma fara \"nr.\", pentru titlul propriu al actului")
PERECHI = [
    ("Legea nr. 295/2004 privind regimul armelor", "Legea 295/2004 privind regimul armelor"),
    ("HG nr. 11/2018", "HG 11/2018"),
    ("Ordinul nr. 1115/2015", "Ordinul 1115/2015"),
    ("Legea 407/2006", "Legea 407/2006"),
    ("Hotărârea nr. 11/2018", "Hotărârea 11/2018"),
]
for intrare, asteptat in PERECHI:
    obtinut = scoate_nr(intrare)
    check(f"{intrare!r} -> {asteptat!r}", obtinut == asteptat, f"obtinut {obtinut!r}")

check("cele doua forme difera cand exista citare",
      insereaza_nr("Legea 295/2004") != scoate_nr("Legea 295/2004"))
check("cele doua forme coincid cand nu exista citare",
      insereaza_nr("regimul armelor") == scoate_nr("regimul armelor"))
for q in ["Legea 295/2004", "Legea nr. 295/2004"]:
    check(f"dus-intors stabil pentru {q!r}",
          insereaza_nr(scoate_nr(q)) == insereaza_nr(q))

# ── 3c. Unirea rezultatelor ──────────────────────────────────────────────────
print("\n3c. Unirea rezultatelor celor doua forme")


def _d(nro, ver=1):
    return {"nro": nro, "versionId": ver, "title": f"act {nro}"}


a, b = [_d(1), _d(2), _d(3)], [_d(9), _d(2), _d(8)]
unite = _intercaleaza([a, b])
check("deduplicheaza dupa (nro, versionId)",
      [d["nro"] for d in unite] == [1, 9, 2, 3, 8],
      f"obtinut {[d['nro'] for d in unite]}")
check("prima potrivire a formei a doua nu e impinsa la coada",
      unite[1]["nro"] == 9, f"obtinut {unite[1]['nro']}")
check("liste inegale nu pierd rezultate",
      len(_intercaleaza([[_d(1)], [_d(2), _d(3), _d(4)]])) == 4)
check("lista goala nu strica unirea",
      [d["nro"] for d in _intercaleaza([[], [_d(5)]])] == [5])
check("aceeasi versiune nu se repeta",
      len(_intercaleaza([[_d(1, 2)], [_d(1, 2)]])) == 1)
check("versiuni diferite ale aceluiasi act raman distincte",
      len(_intercaleaza([[_d(1, 2)], [_d(1, 3)]])) == 2)

# ── 4. Treptele de scurtare ──────────────────────────────────────────────────
print("\n4. Treptele de scurtare taie de la coada")
lunga = "Norme metodologice de aplicare a Legii nr. 295/2004 privind regimul armelor"
trepte = list(_trepte_scurtare(lunga))
check("prima treapta taie exact un cuvant",
      trepte and trepte[0] == " ".join(lunga.split()[:-1]),
      f"obtinut {trepte[0]!r}" if trepte else "nicio treapta")
check("treptele se scurteaza monoton",
      all(len(trepte[i]) > len(trepte[i + 1]) for i in range(len(trepte) - 1)))
check("nu coboara sub patru cuvinte",
      all(len(t.split()) >= 4 for t in trepte),
      f"cea mai scurta are {min((len(t.split()) for t in trepte), default=0)} cuvinte")
check("o interogare deja scurta nu produce trepte",
      list(_trepte_scurtare("regimul armelor")) == [])

# ── Verdict ──────────────────────────────────────────────────────────────────
print()
if FAILS:
    print(f"PICAT: {len(FAILS)} verificari\n  - " + "\n  - ".join(FAILS))
    sys.exit(1)
print("TRECUT: forma interogarii pentru sintact.ro e pazita.")
