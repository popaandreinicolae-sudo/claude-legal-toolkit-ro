---
name: format-bibliografie-doctorat-ub
description: >
  Formatează automat referințele bibliografice și notele de subsol conform stilului
  Școlii Doctorale de Drept a Universității din București. OBLIGATORIU de folosit ori de câte ori
  Claude generează documente academice, rapoarte de cercetare doctorală, articole științifice,
  memorii, sau orice text cu note de subsol și referințe bibliografice destinate mediului
  academic juridic românesc. Se activează la: „notă de subsol", „footnote", „bibliografie",
  „referință bibliografică", „op. cit.", „ibidem", „idem", „citare", „raport doctoral",
  „teză de doctorat", „articol științific", „revistă de drept", „Editura C.H. Beck",
  „Editura Universul Juridic", „Monitorul Oficial", „ECLI", „HUDOC", „EUR-Lex",
  „Curtea Constituțională", „CEDO", „CJUE", „monografie", „tratat", „curs universitar".
  Se activează AUTOMAT la orice document academic juridic în limba română, chiar dacă
  utilizatorul nu cere explicit formatare bibliografică — un raport doctoral trebuie să
  aibă citări corecte din oficiu.
---

# Formatare bibliografică — Stilul Școlii Doctorale de Drept, Universitatea din București

Acest skill codifică regulile exacte de citare folosite în tezele și rapoartele de cercetare
doctorală din cadrul Școlii Doctorale de Drept a Universității din București. Stilul este
derivat din practica academică românească de drept constituțional și drept public, cu elemente
specifice tradiționale (prescurtări latine, ordine fixă a elementelor, format de publicare
în Monitorul Oficial).

Respectarea exactă a acestor reguli contează pentru că evaluatorii (comisia de îndrumare,
referenții, comisia de susținere) verifică conformitatea formală a citărilor — o greșeală
de format semnalează lipsă de rigoare și poate atrage observații care distrag de la conținutul
de fond.

---

## Reguli generale

1. **Limba citării** urmează limba documentului-gazdă. Dacă documentul este în română, toate

   elementele descriptive (ed., vol., p., pp., nr., par.) sunt în română, chiar dacă sursa
   citată este în altă limbă. Titlul sursei rămâne în limba originală.

2. **Prima citare** a oricărei surse trebuie să fie **completă** — cu toate elementele.

   Citările ulterioare folosesc forme prescurtate (op. cit., ibidem, idem).

3. **Punctuația**: fiecare notă de subsol se termină cu punct final. Elementele din interiorul

   citării sunt separate prin virgulă. Nu se folosește punct și virgulă între elemente.

4. **Numerotarea notelor de subsol**: continuă pe tot documentul (nu se resetează per capitol

   sau per pagină). Numerotarea este arabă, superscript.

5. **Prescurtări standard**:
   - `p.` = pagină unică; `pp.` = interval de pagini (pp. 101-119)
   - `par.` = paragraf (pentru decizii CCR, hotărâri CEDO, hotărâri CJUE)
   - `ed.` = ediția; `vol.` = volumul
   - `nr.` = numărul (pentru reviste, decizii, cereri)
   - `coord.` = coordonator; `trad.` = traducător

6. **Numele autorilor**: Inițială prenume + punct + spațiu + Nume. Pentru autori multipli,

   se leagă cu virgulă, ultimii doi cu „și" (fără virgulă Oxford).
   Exemplu: `I. Muraru, E.S. Tănăsescu` sau `I. Muraru și E.S. Tănăsescu`.

---

## Tipare de citare pe categorii

### 1. Monografii (tratate, cursuri, monografii de autor)

**Tipar:**
```
INIȚIALĂ. NUME, Titlul lucrării în italice, vol. X, ed. a Y-a, Editura Z,
Localitatea, Anul, p. NN.
```

**Exemple:**

Prima citare:
> I. Muraru, E.S. Tănăsescu, *Drept constituțional și instituții politice*, vol. I,
> ed. a 15-a, Editura C.H. Beck, București, 2017, p. 45.

Cu coordonator:
> I. Muraru, E.S. Tănăsescu (coord.), *Constituția României. Comentariu pe articole*,
> ed. a 2-a, Editura C.H. Beck, București, 2019, p. 892.

Autor străin:
> L. Lessig, *Code: And Other Laws of Cyberspace, Version 2.0*, Basic Books,
> New York, 2006, p. 121.

**Reguli specifice:**

- Volumul se indică doar dacă lucrarea are mai multe volume
- Ediția se indică doar dacă nu este prima ediție
- Dacă sunt mai mult de 3 autori: primul autor + „ș.a." (= și alții)
- Titlul este întotdeauna în italice (sau subliniat dacă italicele nu sunt disponibile)

### 2. Articole în reviste de specialitate

**Tipar:**
```
INIȚIALĂ. NUME, Titlul articolului în italice, în Denumirea Revistei, nr. N/An,
Editura Z, Localitatea, pp. X-Y.
```

**Exemple:**

> A.-N. Popa, *Securitatea națională ca valoare constituțională — între suveranitate
> și integrare europeană*, în Revista de Drept Constituțional, nr. 1/2025,
> Editura Universul Juridic, București, pp. 101-119.

Articol în revistă străină:
> M. Zalnieriute, *Technology and the Courts: Artificial Intelligence and Judicial
> Impartiality*, în Modern Law Review, vol. 84, nr. 3/2021, pp. 602-628.

**Reguli specifice:**

- „în" (cu minusculă) precedă numele revistei — este prepoziție, nu parte din titlu
- Numărul revistei include anul: `nr. 1/2025`
- Se indică intervalul complet de pagini al articolului (`pp. X-Y`), nu doar pagina citată
- Dacă se citează o pagină specifică: `pp. 101-119, spec. p. 108`

### 3. Contribuții în volume colective

**Tipar:**
```
INIȚIALĂ. NUME, Titlul contribuției în italice, în INIȚIALĂ. NUME (coord.),
Titlul volumului în italice, Editura Z, Localitatea, Anul, pp. X-Y.
```

**Exemplu:**
> S. Drăgulescu, *Securitatea cibernetică în dreptul constituțional comparat*, în
> E.S. Tănăsescu (coord.), *Drepturile fundamentale în era digitală*, Editura C.H. Beck,
> București, 2024, pp. 145-178.

### 4. Decizii ale Curții Constituționale a României (CCR)

**Tipar:**
```
Curtea Constituțională a României, Decizia nr. N/An, publicată în Monitorul Oficial
al României, Partea I, nr. X din DATA, par. Y.
```

**Exemple:**

> Curtea Constituțională a României, Decizia nr. 70/2023, publicată în Monitorul Oficial
> al României, Partea I, nr. 245 din 24 martie 2023, par. 65.

> Curtea Constituțională a României, Decizia nr. 440/2014, publicată în Monitorul Oficial
> al României, Partea I, nr. 653 din 4 septembrie 2014, par. 32.

**Reguli specifice:**

- Se scrie întotdeauna forma completă „Curtea Constituțională a României" (nu CCR) la prima citare
- Monitorul Oficial: forma completă „Monitorul Oficial al României, Partea I"
- Data din Monitorul Oficial: zi + luna (în litere) + an
- Paragraful se indică cu `par.` (nu „pct.", nu „§")
- Pentru decizii cu opinii separate: adaugă `opiniile separate ale judecătorilor X și Y`

### 5. Hotărâri ale Curții Europene a Drepturilor Omului (CEDO)

**Tipar:**
```
Curtea Europeană a Drepturilor Omului, Cauza NUME c. STAT, Cererea nr. XXXXX/XX,
hotărârea din DATA, par. Y.
```

**Exemple:**

> Curtea Europeană a Drepturilor Omului, Cauza Bărbulescu c. României, Cererea
> nr. 61496/08, hotărârea din 5 septembrie 2017 [Marea Cameră], par. 120.

> Curtea Europeană a Drepturilor Omului, Cauza Big Brother Watch și alții c.
> Regatului Unit, Cererile nr. 58170/13, 62322/14 și 24960/15, hotărârea din
> 25 mai 2021 [Marea Cameră], par. 325.

**Reguli specifice:**

- „c." = contra (nu „vs.", nu „v.")
- Statul se scrie cu articol și la genitiv/dativ: `c. României`, `c. Regatului Unit`
- [Marea Cameră] se indică între paranteze drepte dacă e cazul
- Pentru cereri conexe: `Cererile nr. X, Y și Z`
- Data hotărârii: zi + luna (în litere) + an

### 6. Hotărâri/Concluzii ale Curții de Justiție a Uniunii Europene (CJUE)

**Tipar:**
```
Curtea de Justiție a Uniunii Europene, Cauza C-XXX/XX, Denumirea cauzei în italice,
ECLI:EU:C:YYYY:NNN, par. Z.
```

**Exemple:**

> Curtea de Justiție a Uniunii Europene, Cauza C-311/18, *Data Protection Commissioner
> c. Facebook Ireland și Maximillian Schrems*, ECLI:EU:C:2020:559, par. 176.

> Curtea de Justiție a Uniunii Europene, Cauza C-623/17, *Privacy International*,
> ECLI:EU:C:2020:790, par. 44.

Concluzii ale Avocatului General:
> Concluziile Avocatului General M. Szpunar prezentate în Cauza C-311/18,
> ECLI:EU:C:2019:1145, par. 100.

**Reguli specifice:**

- Se indică ECLI complet (nu doar numărul cauzei)
- Denumirea cauzei în italice
- Pentru Tribunal: `Tribunalul Uniunii Europene` + `ECLI:EU:T:...`
- „Cauza C-" pentru Curte, „Cauza T-" pentru Tribunal
- Cauzele conexe: `Cauzele conexe C-X/XX și C-Y/XX`

### 7. Legislație (națională și europeană)

**Legislație românească:**
> Legea nr. 362/2018 privind asigurarea unui nivel comun ridicat de securitate a rețelelor
> și sistemelor informatice, publicată în Monitorul Oficial al României, Partea I,
> nr. 21 din 8 ianuarie 2019, cu modificările și completările ulterioare.

> Ordonanța de urgență a Guvernului nr. 155/2024 privind măsuri pentru un nivel comun
> ridicat de securitate cibernetică, publicată în Monitorul Oficial al României, Partea I,
> nr. 1186 din 28 noiembrie 2024.

**Legislație europeană:**
> Directiva (UE) 2022/2555 a Parlamentului European și a Consiliului din 14 decembrie 2022
> privind măsuri pentru un nivel comun ridicat de securitate cibernetică în Uniune (NIS 2),
> JO L 333, 27.12.2022, p. 80.

> Regulamentul (UE) 2019/881 al Parlamentului European și al Consiliului din 17 aprilie 2019
> privind ENISA și privind certificarea securității cibernetice (Regulamentul privind
> securitatea cibernetică), JO L 151, 7.6.2019, p. 15.

**Reguli specifice:**

- Actele normative românești: titlu complet + Monitorul Oficial + „cu modificările și completările ulterioare" (dacă a fost modificat)
- Actele UE: titlu complet + Jurnalul Oficial (`JO L NNN, dată, p. X`)
- Nu se pune titlul în italice — este act normativ, nu operă doctrinară
- Constituția: `Constituția României, revizuită prin Legea nr. 429/2003`

### 8. Surse online și documente instituționale

**Tipar:**
```
AUTOR/INSTITUȚIE, Titlul în italice, [tipul documentului, dacă e cazul],
data publicării, disponibil la: URL, accesat la DATA.
```

**Exemple:**

> ENISA, *NIS Investments 2022*, Raport, octombrie 2022, disponibil la:
> https://www.enisa.europa.eu/publications/nis-investments-2022, accesat la 15 martie 2026.

> Comisia Europeană, *Comunicare privind strategia UE de securitate cibernetică
> pentru deceniul digital*, JOIN(2020) 18 final, Bruxelles, 16 decembrie 2020.

**Reguli specifice:**

- „disponibil la:" (cu două puncte) înainte de URL
- „accesat la" + dată completă (zi + lună + an)
- Documentele oficiale UE cu cod: COM(an) nr. final sau JOIN(an) nr. final
- URL-urile nu se pun în italice și nu se încadrează în `< >`

---

## Forme prescurtate (citări repetate)

### op. cit. (opere citato)
Folosit când sursa a mai fost citată anterior, dar nu imediat precedent.

**Tipar:** `INIȚIALĂ. NUME, op. cit., p. NN.`

**Exemplu:**
> I. Muraru, E.S. Tănăsescu, op. cit., p. 52.

**Dacă același autor are mai multe lucrări citate:**
> I. Muraru, E.S. Tănăsescu, *Drept constituțional...*, op. cit., p. 52.

(Se adaugă titlul prescurtat în italice, terminat cu `...`, pentru dezambiguizare.)

### Ibidem
Folosit când se citează exact aceeași sursă ca în nota de subsol imediat precedentă,
dar la o altă pagină/paragraf.

**Exemplu:**
> Ibidem, p. 53.

Sau, dacă și pagina este aceeași:
> Ibidem.

### Idem
Folosit când se citează același autor ca în nota imediat precedentă, dar o lucrare diferită.

**Exemplu:**
> Idem, *Constituția României. Comentariu pe articole*, ed. a 2-a, Editura C.H. Beck,
> București, 2019, p. 341.

---

## Reguli pentru note de subsol în docx

Când generezi un document Word (.docx) cu note de subsol:

1. Folosește `FootnoteReferenceRun` din pachetul `docx` (npm) conform skill-ului

   `docx-footnotes` — citește acel skill înainte de a genera documentul.

2. Fontul notelor de subsol: Times New Roman, 10pt (corpul textului este 12pt).

3. Numerotarea: continuă, arabă, superscript — setată prin `FootnoteReferenceRun`.

4. Textul italic din note (titluri de lucrări) se formatează cu `italics: true` pe

   run-ul respectiv din footnote.

5. Nu combina text normal și italic în același `TextRun` — creează run-uri separate.

---

## Verificare automată — checklist

După generarea oricărui document cu note de subsol, parcurge mental acest checklist:

- [ ] Fiecare notă se termină cu punct?
- [ ] Prima citare a fiecărei surse este completă?
- [ ] Formele prescurtate (op. cit., Ibidem, Idem) sunt folosite corect?
- [ ] Titlurile lucrărilor sunt în italice?
- [ ] Actele normative NU sunt în italice?
- [ ] Datele din Monitorul Oficial sunt complete (nr. + zi + lună + an)?
- [ ] ECLI-urile sunt complete și corect formatate?
- [ ] Paginile: `p.` pentru una, `pp.` pentru interval?
- [ ] Numele autorilor: Inițială. Nume (nu Prenume complet)?
- [ ] „c." pentru CEDO (nu „vs.")?
