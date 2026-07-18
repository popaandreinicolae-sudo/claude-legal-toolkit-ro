---
name: verificare-legislatie
description: |
  Verifică automat că orice act normativ românesc invocat de Claude (legi, OUG-uri, HG-uri, ordine, decizii CCR) este în vigoare, neabrogat și cu textul actualizat la zi. OBLIGATORIU de folosit ori de câte ori Claude citează, invocă sau face referire la orice act normativ românesc, inclusiv articole individuale, alineate sau teze. Se activează la cuvinte precum: „lege", „OUG", „HG", „ordin", „articol", „alineat", „Monitorul Oficial", „abrogat", „în vigoare", „modificat", „republicat", „cod", „regulament", „directivă", „normă metodologică". Se activează AUTOMAT după generarea oricărui document juridic, contract, memoriu, cerere, analiză legislativă, fișă de învățare sau material didactic care conține referințe legislative. Scopul principal este prevenirea citării de acte normative abrogate (de exemplu Legea 393/2004, abrogată prin OUG 57/2019, sau Legea 215/2001, abrogată tot prin OUG 57/2019).
---

# Verificare Legislație în Vigoare

## De ce există acest skill

Modelele de limbaj au o tendință naturală de a cita acte normative din memoria de antrenament, care pot fi între timp abrogate, modificate substanțial sau înlocuite. Exemple reale de erori:

- Legea 393/2004 (Statutul aleșilor locali), abrogată prin art. 597 din OUG 57/2019
- Legea 215/2001 (administrația publică locală), abrogată prin OUG 57/2019
- Legea 188/1999 (statutul funcționarilor publici), abrogată prin OUG 57/2019
- OUG 34/2006 (achiziții publice), abrogată prin Legea 98/2016

Aceste erori sunt grave în context juridic. Un act normativ abrogat citat într-un memoriu, cerere sau document oficial poate compromite întregul demers.

## Regula fundamentală

NICIUN ACT NORMATIV NU SE CITEAZĂ FĂRĂ VERIFICARE PREALABILĂ.

Înainte de a include orice referință legislativă (în text, în note de subsol sau în bibliografie), trebuie verificat:

1. Actul normativ este în vigoare la data curentă
2. Articolul sau alineatul citat există în forma actualizată
3. Textul citat corespunde formei în vigoare, nu unei forme anterioare modificate
4. Dacă actul a fost abrogat, se identifică actul normativ succesor care l-a înlocuit

## Protocol de verificare, pas cu pas

### Pasul 1. Inventariază toate actele normative pe care intenționezi să le citezi

Înainte de a redacta conținutul, fă o listă completă cu fiecare act normativ pe care îl vei invoca. Pentru fiecare, notează:

- Tipul actului (Lege, OUG, HG, Ordin, Decizie CCR etc.)
- Numărul și anul
- Articolele sau alineatele specifice pe care le vei cita

### Pasul 2. Verifică pe Portalul Legislativ oficial (legislatie.just.ro)

Pentru fiecare act normativ din listă:

1. Caută pe web folosind formula: `site:legislatie.just.ro [tip act] [număr] [an]`. Exemplu: `site:legislatie.just.ro Legea 393 2004`
2. Verifică statusul actului pe pagina rezultată:
   - Caută indicația „Abrogat(ă)", „Act abrogat" sau „Nu mai este în vigoare"
   - Caută mențiunea „Forma actualizată" versus „Forma inițială", folosește întotdeauna forma actualizată
   - Caută secțiunea „Acte de modificare" pentru a identifica ultima modificare
3. Dacă actul este abrogat:
   - Identifică actul abrogator (de obicei menționat pe pagina Portalului Legislativ)
   - Caută corespondența: ce articol din noul act înlocuiește dispozițiile pe care voiai să le citezi
   - Citează actul succesor, NU actul abrogat

### Pasul 3. Verifică textul exact al articolelor

După confirmarea că actul este în vigoare:

1. Accesează textul actualizat al actului normativ pe legislatie.just.ro sau euroavocatura.ro
2. Verifică existența articolului. Actele normative sunt frecvent renumerotate după republicare
3. Verifică conținutul alineatului. Alineatele sunt frecvent modificate, abrogate individual sau introduse prin acte de completare
4. Compară textul pe care intenționezi să-l citezi cu textul actualizat de pe Portalul Legislativ

### Pasul 4. Verificare suplimentară pe lege5.ro (dacă disponibil)

Dacă ai acces autentificat la lege5.ro (prin Claude in Chrome sau alt instrument de navigare):

1. Autentifică-te cu credențialele proprii, stocate în variabile de mediu sau într-un fișier de configurare local (nu le include în text)
2. Caută actul normativ în baza de date lege5.ro
3. Verifică secțiunea „Istoric modificări", lege5.ro afișează cronologic toate modificările
4. Verifică dacă există adnotări privind abrogarea sau modificarea articolelor individuale
5. Folosește funcția de comparare versiuni dacă este disponibilă

### Pasul 5. Raportează rezultatele verificării

La finalul verificării, generează un tabel rezumativ:

```
| Act normativ | Status | Ultima modificare | Observații |
|---|---|---|---|
| OUG 57/2019 | În vigoare | L.296/2023 | Forma actualizată |
| L.393/2004 | ABROGAT | Prin OUG 57/2019 | Înlocuit de art. 207, 232 |
```

## Capcane frecvente, ce să verifici cu atenție specială

### Codul administrativ (OUG 57/2019)

OUG 57/2019 a abrogat un număr mare de acte normative prin art. 597. Verifică întotdeauna dacă actul pe care vrei să-l citezi nu a fost înghițit de Codul administrativ. Acte abrogate de OUG 57/2019 (lista neexhaustivă):

- Legea 215/2001 (administrația publică locală)
- Legea 393/2004 (statutul aleșilor locali)
- Legea 188/1999 (statutul funcționarilor publici)
- OG 35/2002 (regulamentul-cadru consilii locale)
- Legea 340/2004 (prefectul și instituția prefectului)
- Legea 7/2004 (codul de conduită funcționari publici)
- Legea 477/2004 (codul de conduită personal contractual)

### Codurile României

Codurile intră frecvent în vigoare etapizat și sunt modificate substanțial:

- Codul civil (Legea 287/2009), în vigoare din 01.10.2011. Verifică dacă nu citezi din Codul civil vechi din 1864.
- Codul de procedură civilă (Legea 134/2010), în vigoare din 15.02.2013.
- Codul penal (Legea 286/2009), în vigoare din 01.02.2014. Verifică dacă nu citezi din Codul penal vechi (Legea 15/1968).
- Codul de procedură penală (Legea 135/2010), în vigoare din 01.02.2014.
- Codul fiscal (Legea 227/2015). Verifică dacă nu citezi din Codul fiscal vechi (Legea 571/2003).
- Codul administrativ (OUG 57/2019), a consolidat zeci de acte normative anterioare.

### Achizițiile publice

- OUG 34/2006, abrogată prin Legea 98/2016 (achiziții clasice) și Legea 99/2016 (achiziții sectoriale)

### Protecția datelor

- Legea 677/2001, abrogată prin Legea 190/2018 (punerea în aplicare a GDPR)

### Dreptul muncii

- Verifică întotdeauna ultima formă a Codului muncii (Legea 53/2003). Este modificat foarte frecvent.

## Verificarea editurii la referințele doctrinare

Pe lângă legislație, verifică și referințele doctrinare:

- Tratatele de drept schimbă frecvent editorul între ediții. De exemplu, Muraru și Tănăsescu au trecut de la C.H. Beck la Hamangiu la ediția a 15-a.
- Verifică ISBN-ul și editorul pe web înainte de a cita o lucrare academică
- Nu presupune că editorul este același ca la ediția anterioară

## Strategia de căutare

Folosește aceste surse în ordinea priorității:

1. `legislatie.just.ro`, Portalul Legislativ oficial al Ministerului Justiției (cea mai autoritară sursă, include starea actului: în vigoare sau abrogat)
2. `WebSearch` cu termeni specifici: `"[act normativ]" "abrogat" OR "in vigoare" OR "modificat"`
3. `euroavocatura.ro`, texte consolidate actualizate
4. `lege5.ro`, bază de date legislativă cu istoric de modificări (necesită autentificare)
5. `cdep.ro`, Camera Deputaților, texte oficiale ale legilor

## Când se activează acest skill

Acest skill se activează AUTOMAT (fără a aștepta solicitarea utilizatorului) în următoarele situații:

1. Generare de conținut juridic, adică orice document, analiză, fișă, memoriu, cerere sau contract care conține referințe legislative
2. Răspuns la întrebări juridice, adică orice întrebare despre legislația românească
3. Verificare post-generare, adică după ce ai generat un document cu referințe legislative, rulează acest protocol pe toate referințele
4. La solicitarea explicită, când utilizatorul cere verificarea legislației

## Format de raportare a erorilor găsite

Când identifici un act normativ abrogat sau modificat, raportează astfel:

```
ATENȚIE: [Act normativ] este ABROGAT sau MODIFICAT
Status: Abrogat prin [act abrogator], art. [X]
Data abrogării: [data]
Act succesor: [actul care l-a înlocuit]
Corespondența articolelor:
  [Art. vechi] în [Art. nou din actul succesor]
Acțiune: Am înlocuit referința cu [actul în vigoare], art. [Y]
```
