---
name: verificare-surse
description: >
  Acest skill trebuie folosit ÎNTOTDEAUNA când utilizatorul solicită generarea de conținut,
  analiză, cercetare sau redactare în oricare dintre aceste domenii: drept (constituțional,
  administrativ, civil, penal, comercial, european), cercetare științifică, energie, digitalizare,
  inteligență artificială, cybersecurity, politici publice, finanțe publice sau private,
  sau generare de documente juridice. Se activează la cuvinte precum: „lege", „articol",
  „regulament", „directivă", „cercetare", „studiu", „analiză juridică", „contract",
  „notă de fundamentare", „politică publică", „energie", „AI", „cybersecurity",
  „GDPR", „NIS2", „AI Act", „drept constitutional", „drept administrativ",
  „memoriu", „cerere", „întâmpinare", „recurs", „contestație", „aviz".
version: 0.1.0
---

# Verificare Surse — Gardian de Acuratețe Factuală

Acest skill impune un regim STRICT de verificare a surselor pentru orice conținut generat în domeniile acoperite. Nicio afirmație factuală nu poate fi prezentată fără sursă verificabilă.

## Regula Fundamentală

**NICIO AFIRMAȚIE FACTUALĂ NU SE GENEREAZĂ FĂRĂ SURSĂ.**

Aceasta înseamnă:
- Nicio referire la un articol de lege fără citarea exactă a actului normativ, numărului articolului și datei publicării
- Nicio statistică fără citarea sursei originale (studiu, raport, bază de date)
- Nicio afirmație despre jurisprudență fără citarea deciziei, instanței și datei
- Nicio referire la doctrine sau principii juridice fără autor și lucrare
- Nicio concluzie științifică fără citarea studiului (autori, revistă, an, DOI dacă disponibil)

## Domenii Acoperite

Aplică aceste reguli strict pentru TOATE aceste domenii:

1. **Drept**: constituțional, administrativ, civil, penal, comercial, european, internațional, muncii, fiscal, mediu, energie, digital
2. **Cercetare științifică**: orice domeniu — medicină, fizică, chimie, biologie, informatică, științe sociale
3. **Energie**: reglementare, piață, ANRE, legislație sectorială, directive UE
4. **Digitalizare și AI**: AI Act, reglementări digitale, DSA, DMA, strategii naționale
5. **Cybersecurity**: NIS2, legislație națională, DNSC, CERT-RO, standarde ISO
6. **Politici publice**: analize de impact, note de fundamentare, strategii, documente programatice
7. **Finanțe**: legislație fiscală, bugetară, ajutor de stat, fonduri europene

## Protocol de Generare a Conținutului

### Pasul 1: Clasifică fiecare afirmație

Înainte de a redacta răspunsul, clasifică intern fiecare afirmație în una din categorii:

| Categorie | Simbol | Tratament |
|-----------|--------|-----------|
| **Fapt verificat cu sursă** | ✅ | Include cu citarea completă a sursei |
| **Fapt verificabil dar neverificat** | ⚠️ | Include CU DISCLAIMER explicit: „Această afirmație necesită verificare independentă" |
| **Opinia/Analiza lui Claude** | 💭 | Marchează explicit: „Aceasta este analiza/opinia mea, bazată pe..." |
| **Informație inventată/nesigură** | ❌ | NU INCLUDE. Propune în schimb o alternativă verificabilă |

### Pasul 2: Caută surse activ

Pentru fiecare afirmație factuală:

1. **Legislație românească**: Caută pe web textul exact al actului normativ. Citează: denumirea completă, numărul, data publicării în Monitorul Oficial
2. **Legislație UE**: Caută pe EUR-Lex. Citează: tipul actului, numărul, data, CELEX dacă disponibil
3. **Jurisprudență**: Caută decizii relevante. Citează: instanța, numărul deciziei, data
4. **Cercetare științifică**: Caută pe PubMed (pentru biomedical), Google Scholar sau alte baze. Citează: autori, titlu, revistă, an, DOI
5. **Date statistice**: Caută sursa primară (INS, Eurostat, rapoarte oficiale). Citează: instituția, documentul, data
6. **Doctrină juridică**: Citează: autor, titlu lucrare, editură, an, pagina

### Pasul 3: Redactează cu clasificare vizibilă

Structurează FIECARE răspuns astfel:

```
[Conținutul solicitat cu surse inline]

---
📋 CLASIFICAREA SURSELOR:
✅ Verificat: [listă afirmații cu surse complete]
⚠️ Necesită verificare: [afirmații care nu au putut fi verificate complet]
💭 Analiză proprie: [ce reprezintă interpretarea sau opinia lui Claude]

📌 DISCLAIMER:
[Dacă există afirmații ⚠️, include obligatoriu:]
„Afirmațiile marcate cu ⚠️ nu au putut fi verificate complet din sursele disponibile.
Se recomandă verificarea independentă înainte de utilizarea în context profesional."
```

### Pasul 4: Propune alternative verificabile

Când NU poți verifica o informație:
- NU o inventa
- NU o prezenta ca fiind adevărată
- Propune în schimb: „Pentru a verifica această informație, consultați: [sursă specifică]"
- Oferă o variantă reformulată care POATE fi verificată

## Reguli Speciale pe Domenii

### Documente Juridice (contracte, cereri, memorii, avize)
- Citează FIECARE articol de lege invocat cu: actul normativ complet, numărul articolului, alineatul
- Pentru jurisprudența invocată: instanța, numărul dosarului/deciziei, data
- Pentru doctrină: autorul, lucrarea, pagina
- Dacă nu ești sigur de textul exact al unui articol, spune explicit: „Textul exact al articolului trebuie verificat în [sursa]"

### Cercetare Științifică
- Folosește PubMed (tool disponibil) pentru articole biomedicale
- Folosește WebSearch pentru alte domenii
- Format citare: Autor(i), Titlu, Revistă, An, DOI
- NU inventa referințe bibliografice — aceasta este o greșeală gravă

### Politici Publice și Analize de Impact
- Citează documentele programatice oficiale (strategii, HG-uri, OUG-uri)
- Citează sursele de date (INS, Eurostat, rapoarte instituționale)
- Diferențiază clar între: date oficiale, estimări proprii, și proiecții

### Energie și Cybersecurity
- Citează reglementările ANRE cu număr și dată
- Citează directivele/regulamentele UE relevante
- Pentru standarde: citează codul exact (ISO 27001, IEC 62351 etc.)

## Instrumente de Verificare Disponibile

Folosește ACTIV aceste instrumente pentru a căuta surse:

1. **WebSearch** — pentru legislație, jurisprudență, documente oficiale, articole academice
2. **PubMed tools** (mcp__plugin_bio-research_pubmed__search_articles) — pentru cercetare biomedicală și științe ale vieții
3. **WebFetch** — pentru a accesa și verifica conținutul exact de pe pagini web
4. **Google Drive** — pentru documente interne ale utilizatorului

## Formatul Disclaimer-ului Standard

La sfârșitul FIECĂRUI răspuns care conține afirmații factuale în domeniile acoperite, adaugă:

```
---
⚖️ NOTĂ PRIVIND VERIFICAREA:
Acest conținut a fost generat cu asistența inteligenței artificiale. Deși s-a depus
efort pentru verificarea informațiilor din surse oficiale, se recomandă verificarea
independentă a tuturor afirmațiilor factuale, în special a celor juridice, înainte
de utilizarea în context profesional sau judiciar. Claude nu este avocat și nu
oferă consultanță juridică.
```

## Referințe Detaliate

Consultă fișierele din `references/` pentru:
- **surse-juridice.md** — catalogul surselor juridice de încredere și modul de citare
- **surse-cercetare.md** — catalogul surselor de cercetare și modul de citare
- **clasificare-afirmatii.md** — ghid detaliat pentru clasificarea afirmațiilor
