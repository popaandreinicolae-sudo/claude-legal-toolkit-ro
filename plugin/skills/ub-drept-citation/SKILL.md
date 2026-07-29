---
name: ub-drept-citation
description: |
  Format citare bibliografica oficial Scoala Doctorala Facultatea de Drept Universitatea din Bucuresti. APLICA AUTOMAT la orice generare de note de subsol, bibliografie, citari in lucrari juridice academice romanesti. Triggere: "nota de subsol", "bibliografie", "citare", "raport doctoral", "teza", "articol revista", "tratat", "monografie", "decizie CCR", "hotarare CEDO", "cauza CJUE", "op. cit.", "ibidem", "idem". Acopera toate cazurile, monografie, articol, decizie CCR, hotarare CEDO, cauza CJUE, lucrare colectiva, repetare sursa, format bibliografie finala.
version: 1.0
last_updated: 2026-06-01
---

# UB Drept Citation Format

Skill dedicat pentru format citare bibliografica conform standardelor Scolii Doctorale Facultatea de Drept Universitatea din Bucuresti. Aplicabil la teze de doctorat, articole in reviste juridice romanesti, fundamentari, opinii, memorii.

## Format pentru fiecare tip de sursa

### Monografie sau tratat

```
I. Muraru, E.S. Tanasescu, Drept constitutional si institutii politice, vol. I,
ed. a 15-a, Editura C.H. Beck, Bucuresti, 2017, p. 45.
```

Componente obligatorii: initiala prenume plus nume autor, titlul lucrare in italice, volumul daca exista, editia, editura, oras, an, pagina.

### Articol revista juridica

```
A.-N. Popa, Securitatea nationala ca parte a identitatii constitutionale/nationale,
in Revista de Drept Constitutional, nr. 1/2025, Editura Universul Juridic,
Bucuresti, pp. 101-119.
```

Componente: autor, titlu articol in italice, "in" plus revista, numar plus an, editura, oras, paginile.

### Decizie CCR

```
Curtea Constitutionala a Romaniei, Decizia nr. 70/2023,
publicata in Monitorul Oficial al Romaniei, Partea I, nr. 245
din 24 martie 2023, par. 65.
```

Componente: institutie completa, decizie nr. plus an, M.Of. cu nr. plus data, paragraf citat.

### Hotarare CEDO

```
Curtea Europeana a Drepturilor Omului, Cauza Zakharov contra Rusiei,
Cererea nr. 47143/06, hotararea din 4 decembrie 2015, par. 230.
```

Componente: institutie completa, cauza cu particula "contra" sau "c.", numar cerere format NNNNN/AA, data hotarare, paragraf.

### Cauza CJUE

```
Curtea de Justitie a Uniunii Europene, Cauza C-83/14, CHEZ Razpredelenie Bulgaria AD,
ECLI:EU:C:2015:480, par. 100.
```

Componente: institutie completa, numar cauza C-X/YY, denumire, ECLI complet, paragraf.

### Lucrare colectiva, capitol in carte

```
A.-N. Popa, A.-I. Tuta, Spete recapitulative,
in A. Vertes-Olteanu (coord.), 12 teme de Drept Constitutional,
Editura C.H. Beck, Bucuresti, 2019, pp. 268-287.
```

Componente: autori capitol, titlu capitol in italice, "in" plus coordonator, titlu carte in italice, editura, oras, an, paginile.

### Lege, OUG, HG

```
Legea nr. 58/2023 privind securitatea si apararea cibernetica a Romaniei,
publicata in Monitorul Oficial nr. 214 din 15 martie 2023, art. 25 alin. (2).
```

Componente: tip act, nr. plus an, titlu complet, M.Of. plus data, articolul plus alineatul.

## Repetare sursa

```
Prima citare: I. Muraru, E.S. Tanasescu, Drept constitutional si institutii politice,
              vol. I, ed. a 15-a, Editura C.H. Beck, Bucuresti, 2017, p. 45.

A doua citare: I. Muraru, E.S. Tanasescu, op. cit., p. 67.

Imediat consecutiv: Ibidem, p. 68.

Acelasi autor, alta lucrare: Idem, Drept constitutional, vol. II, p. 90.
```

## Bibliografie finala

Ordonare alfabetica pe nume autor. Subdivizata pe categorii:

1. Tratate si monografii
2. Articole in reviste de specialitate
3. Jurisprudenta CCR
4. Jurisprudenta CEDO si CJUE
5. Legislatie nationala
6. Legislatie europeana
7. Surse online

Pentru fiecare categorie, format identic cu cel din note de subsol, fara paginatie specifica.

## Alte stiluri de citare cand se cere explicit

Vezi `references/alte-stiluri.md` pentru detalii:

- OSCOLA, Oxford Standard for Citation of Legal Authorities, publicatii internationale
- Bluebook, drept american
- APA 7th, lucrari interdisciplinare
- Chicago Manual of Style, cel mai apropiat de stilul romanesc

## DOI plus link-uri online

DOI obligatoriu cand este disponibil:
```
A.-N. Popa, Securitatea nationala ca parte a identitatii constitutionale,
in Revista de Drept Constitutional, nr. 1/2025, p. 101.
DOI: 10.62938/rdc-2025-0006.
```

URL pentru surse online verificabile:
```
Comisia Europeana, Communication on AI, COM(2021) 205 final.
Available at: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52021DC0205.
Accessed 1 iunie 2026.
```

## Anti-halucinare specifica citare

Niciodata nu inventa:
- Numere de decizii CCR, hotarari CEDO, cauze CJUE
- Numere de articole, alineate, paragrafe
- Pagini in tratate (multe carti au schimbat paginatia intre editii)
- Prenume complete autori (daca ai doar initiala, scrie initiala)
- Ani publicare carti, edituri (s-au schimbat intre editii)
- DOI sau ECLI

Pentru fiecare element nesigur, marcheaza [VERIFICARE NECESARA prin MCP-uri].

## Pipeline cu alte skill-uri

- `anti-hallucination-document` pentru fact-check global
- `constitutional-law-ro` pentru continut juridic
- `cyber-law-ro` pentru drept cibernetic
- `format-bibliografie-doctorat-ub` pentru detalii suplimentare bibliografie
- MCP `zotero` pentru import-export referinte bibliografice
- MCP `semantic-scholar` pentru verificare DOI articole academice
