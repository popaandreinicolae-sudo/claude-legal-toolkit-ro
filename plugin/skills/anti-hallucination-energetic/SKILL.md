---
name: anti-hallucination-energetic
description: |
  Protocol specializat anti-halucinare pentru documente despre sectorul energetic. APLICA AUTOMAT la documente, rapoarte, strategii, opinii juridice, fundamentari care abordeaza: sistemul energetic national, sectorul gazier (operatori de transport si distributie gaze, producatori), sectorul electric (operatori de transport si distributie electrica, producatori), termoficare (companii municipale de termoficare, CET, SACET), regenerabile (fotovoltaic, eolian, geotermal, biomasa), eficienta energetica cladiri, mobilitate electrica, securitate energetica, infrastructura critica, ANRE, ANRSC, Ministerul Energiei. Triggere: "energie", "electricitate", "gaze naturale", "termoficare", "SACET", "CET", "cogenerare", "operator distributie", "operator transport", "ANRE", "ANRSC", "regenerabile", "PNRR energie", "PNIESC", "Strategia Energetica", "Fondul Modernizare", "ETS", "MWh", "GWh", "kV", "Gcal", "kWh termic", "regiune metropolitana sectorul energetic", "infrastructura energetica", "tarif energie", "subventie energie". Construit pe baza unui set de halucinatii tipice documentate intr-un raport energetic regional (caz ilustrativ, date si denumiri fictive): personal UIP fabricat, finantare de tip trust fund inventata, scenarii BAU/Strategy/Ambitious cu cifre fictive, volume de programe europene atribuite fara sursa, BCR fabricat, anexa de sensibilitate complet inventata.
version: 1.0
last_updated: 2026-06-01
parent_skill: anti-hallucination-document
---

# Anti-Hallucination Energetic, Sector Specific

Acest skill extinde `anti-hallucination-document` cu reguli si referinte specifice sectorului energetic. Citeste mai intai SKILL.md al parintelui pentru regulile universale, apoi aplica regulile sectoriale de mai jos.

> Nota. Exemplele, denumirile de operatori si cifrele din acest skill sunt ILUSTRATIVE si FICTIVE. Ele descriu un caz de referinta (o "Regiune Metropolitana Alfa", cu municipiul Alfa si judetul Beta) folosit doar pentru a fixa tiparul halucinatiilor. Nu le reutiliza ca date reale, verifica orice valoare prin sursa primara a operatorului concret.

## Surse obligatorii incarcate in Project Knowledge

Pentru orice document despre sectorul energetic al unei regiuni sau al tarii, incarca obligatoriu in Project Knowledge sursele primare relevante. Pentru cazul ilustrativ de referinta, categoriile sunt:

1. Strategia Energetica nationala pe orizontul de planificare, cu actul normativ de adoptare (public)
2. Planul National Integrat in domeniul Energiei si Schimbarilor Climatice, versiunea actualizata transmisa CE (public)
3. Strategia Integrata de Dezvoltare Urbana a municipiului resedinta (SIDU, caz ilustrativ), componentele tematice relevante
4. Plan de dezvoltare al operatorului de distributie electrica (DistribElectric Alfa S.A., fictiv), pe orizontul de planificare
5. Plan de dezvoltare al operatorului de transport electric (OTE Alfa, fictiv), pe orizontul de planificare
6. Raport de audit energetic SACET al companiei municipale de termoficare (TermoAlfa, fictiv), pentru exercitiul financiar de referinta
7. Acte normative cheie (publice): OUG 27/2022, OUG 64/2022, Legea 372/2005, Metodologia Mc001/2022, Legea 121/2014 eficienta energetica
8. Memorandumuri ale producatorului de cogenerare (CogenAlfa, fictiv) cu parteneri tehnologici externi (caz ilustrativ)
9. Cele 4 directive UE relevante (publice): 2018/2001 modificata 2023/2413 (RED III), 2023/1791 EED reformare, 2024/1275 EPBD, Regulamentul 2019/943
10. Documente ANRE: rapoarte periodice, decizii de reglementare a tarifului de distributie (publice)

## Reguli sectoriale specifice

### Regula E1, validare cifre cu unitati corecte

Confuzia intre unitati este halucinatie clasica. Verifica:
- MW este capacitate instalata, MWh este energie produsa pe an
- Gcal/h este capacitate termica, Gcal este energie termica
- kV este nivel tensiune, kW este putere consumator
- m³ este volum gaz natural absolut, m³ normal (Nm³) este la conditii standard
- MJ, GJ, TJ sunt unitati de energie, nu de putere

Cand citezi capacitate, marcheaza explicit: "capacitate instalata X MW" sau "energie produsa Y MWh/an".

### Regula E2, denumiri institutionale oficiale si curente

Folosesti denumirile oficiale curente, actualizate dupa reorganizari, fuziuni sau desfiintari. Exemplele de mai jos sunt FICTIVE, principiul ramane valabil: verifica denumirea reala prin registrul comertului sau prin MCP `legal-verificator-ro`. Halucinari frecvente, cu denumiri pre-reorganizare:
- CORECT: DistribElectric Alfa S.A. (operator rezultat din fuziune, denumire in vigoare de la data de referinta)
- GRESIT: ElectroDistrib Regional (denumire pre-fuziune, depasita)
- CORECT: Compania Municipala Termica Alfa S.A. (TermoAlfa), denumire in vigoare de la data reorganizarii
- GRESIT: Regia de Termoficare RTA (regie desfiintata, transferata la TermoAlfa)
- CORECT: Producatorul de cogenerare Alfa S.A. (CogenAlfa)
- CORECT: Operatorul de Transport Electric Alfa S.A. (OTE Alfa)
- CORECT: Operatorul de Transport Gaze Alfa S.A. (OTG Alfa)
- CORECT: GazDistrib Sud S.A. (parte dintr-un grup de utilitati, fictiv)
- CORECT: HidroProducator Alfa S.A.
- CORECT: GazProducator Alfa S.A.

### Regula E3, cifrele de consum ale regiunii (valori ilustrative)

Cifrele de mai jos sunt PLACEHOLDER-e ilustrative. Intr-un document real, fiecare valoare se preia din datele operatorului si se marcheaza [VERIFICARE] pana la confirmare:
- Municipiul Alfa, consum total anual: [VERIFICARE] cu operatorul de distributie electrica
- Judetul Beta, consum total anual: ≈ X MWh (ilustrativ, de verificat in raportul operatorului)
- Distributie consum judet: ≈ Y MWh medie tensiune plus ≈ Z MWh joasa tensiune (ilustrativ)
- Consum medie tensiune municipiu: ≈ X MWh (ilustrativ)
- Prognoza municipiu pe orizontul de planificare: de la A MW la B MW, crestere de ordinul catorva procente pe an (ilustrativ)
- Prognoza judet pe orizontul de planificare: de la C MW la D MW (ilustrativ)
- Productie locala din surse regenerabile la orizontul planificat: ≈ E MW (plafonata, dependenta de fluxurile de retea) (ilustrativ)

### Regula E4, cifrele SACET (valori ilustrative)

Toate valorile de mai jos sunt PLACEHOLDER-e; preia-le din raportul de audit SACET si marcheaza [VERIFICARE]:
- Lungime retea primara SACET: ≈ X km (ilustrativ)
- Lungime retea secundara SACET: ≈ Y km (ilustrativ)
- Vechime peste 25 ani retea primara: ≈ P% (ilustrativ)
- Vechime peste 25 ani retea secundara: ≈ Q% (ilustrativ)
- Pierderi reale caldura SACET pe exercitiul de referinta: ≈ R% (ilustrativ)
- Avarii retea primara pe exercitiul de referinta: ≈ N (ilustrativ)
- Avarii cumulat sistem pe exercitiul de referinta: ≈ M (ilustrativ)
- Productie de la terti (producator de cogenerare majoritar) in SACET: ≈ S% (ilustrativ)
- Capacitate termica cumulata a CET-urilor producatorului de cogenerare: ≈ T Gcal/h (ilustrativ)
- Pierderi cumulate transformare-transport la nivel national: valoare din Strategia Energetica (citeaza sursa publica exacta)

### Regula E5, indicatori care SUNT OBLIGATORIU marcati ca neverificati

Aceste cifre apar frecvent halucinate. Marcheaza [VERIFICARE NECESARA] daca nu ai sursa primara:
- Numarul exact de apartamente cu centrale termice individuale in municipiu
- Volumul exact al platilor cumulate intre producatorul de cogenerare si operatorul de distributie gaze (estimare de ordinul miliardelor de lei, dar necesita sursa)
- BCR (Benefit-Cost Ratio) pentru proiecte specifice
- Volume aplicabile pe programe europene specifice fara confirmare ministeriala
- Numar angajati in unitatea de implementare a proiectului (UIP) a asociatiei de dezvoltare intercomunitara (ADI Alfa, fictiva)
- Suma unui trust fund de la o institutie financiara internationala pentru dezvoltare institutionala
- Mid-Term Review threshold (NU folosi un prag de disbursement fara sursa oficiala a finantatorului)
- NPV, EIRR per proiect individual
- Procent disbursement pentru milestones

### Regula E6, structura corecta capitole pentru raport energetic

Format validat dupa documentul corectat:
- Cap. I, Diagnoza energetica a regiunii (NU "Contextul energetic" generic)
- Cap. II, SACET
- Cap. III, Electricitate generare si cogenerare
- Cap. IV, Electricitate distributie si transport
- Cap. V, Gaze naturale
- Cap. VI, Eficienta energetica cladiri
- Cap. VII, Iluminat public
- Cap. VIII, Mobilitate electrica
- Cap. IX, Securitate energetica metropolitana
- Cap. X, Roadmap implementare
- Cap. XI, Surse de finantare (NU "Cadru juridic" daca nu ai continut)

NU genera capitole goale ca slot fillers. Daca utilizatorul nu cere explicit capitol cadru juridic plus nu are continut, omite-l.

### Regula E7, scenarii cu disclaimers obligatorii

Cand prezinti scenarii BAU/Strategy/Ambitious:
- Marcheaza fiecare cifra ca [SCENARIU, ipoteza X]
- Mentioneaza ca scenariile sunt constructii analitice, nu prognoze oficiale
- Nu invoca surse oficiale (institutie financiara internationala, ANRE) pentru cifrele scenariilor decat daca au validare publica
- Indica explicit ce variabile fac diferenta intre scenarii

### Regula E8, surse finantare cu volume

Cand mentionezi programe europene de finantare:
- Nume program complet plus perioada de programare 2021-2027 sau 2028-2034
- Volum total aplicabil DOAR daca exista in document oficial alocat sectorului
- Nu inventa volume tip "peste 200 milioane EUR", "peste 800 milioane EUR"
- Pentru PNRR, citeaza componenta specifica plus alocarea oficiala publicata
- Pentru Fondul de Modernizare, citeaza data adoptata plus tara beneficiar plus suma

### Regula E9, valori geotermale (caz ilustrativ)

Valorile de mai jos sunt FICTIVE, pentru o zona geotermala ipotetica (Alfa-Nord). Intr-un document real, preia-le din studiul geologic si marcheaza [VERIFICARE]:
- Suprafata rezervor: ≈ X km² (ilustrativ)
- Temperatura cap sonda: interval de ordinul zecilor de grade Celsius (ilustrativ)
- Debite individuale: interval de ordinul zecilor de litri pe secunda (ilustrativ)
- Acvifer carbonatic: calcare si dolomite (descriere generica)
- Licenta de concesiune activa: un operator infrastructural regional (fictiv), pentru o incinta industriala (caz ilustrativ)
- Valoare estimata proiect geotermal regional: ≈ Y milioane EUR (ilustrativ)

Restul cifrelor geotermale (numar puturi, productie estimata, beneficiari finali) trebuie marcate [SCENARIU] sau [VERIFICARE NECESARA].

### Regula E10, coduri proiecte din portofoliu (SIDU)

Portofoliile de tip SIDU folosesc coduri structurate. Exemplu de conventie (ilustrativ):
- LS-X pentru lista scurta (X numar)
- LL-X pentru lista lunga (X numar)

Exemple ILUSTRATIVE, cu coduri, descrieri si valori fictive:
- LS-01: consolidare seismica plus eficienta energetica cladiri publice, ≈ X milioane EUR
- LS-02: eficienta energetica unitati de invatamant, ≈ Y milioane EUR
- LS-03: iluminat public LED, ≈ Z milioane EUR
- LL-01: retea de statii de reincarcare electrica, ≈ A milioane EUR
- LL-02: capacitati fotovoltaice pe cladiri publice, faza initiala
- LL-03: proiect geotermal regional, ≈ B milioane EUR
- LL-04: capacitate de cogenerare, ≈ C MW instalati

Nu inventa coduri (LS-NEW1, LL-X cu numere neconfirmate) care nu apar in portofoliul oficial. Verifica fiecare cod, descriere si valoare in documentul-sursa.

## Integrare cu MCP-uri si skill-uri

Acest skill ruleaza in pipeline cu:
- `anti-hallucination-document` (parinte, reguli universale)
- `zero-hallucination-citations` (citarea bibliografica)
- `verificare-legislatie` (validare OUG-uri, HG-uri, legi energie)
- `legal-verificator-ro` MCP (verificare acte normative romanesti)
- `eurlex` MCP (verificare directive UE energie)
