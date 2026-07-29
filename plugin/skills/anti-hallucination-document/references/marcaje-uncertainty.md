# Taxonomia Marcajelor de Incertitudine

Vocabular consistent pentru marcarea diferitelor categorii de informatie in documente profesionale.
Exemplele de mai jos sunt ilustrative si fictive.

## Marcaje principale

### [DATA]

Informatie confirmata din sursa primara verificata. Se foloseste pentru:
- Cifre din rapoarte oficiale uploadate in Project Knowledge
- Procente din statistici publicate (INS, Eurostat, ANRE)
- Articole de lege verificate prin MCP `legal-verificator-ro`
- Decizii CCR verificate prin MCP plus citate verbatim

Exemplu: `Pierderile de retea au fost de NN,NN% in 20XX [DATA, sursa: raport de audit al operatorului, p. XX].`

### [ESTIMARE]

Calcul propriu construit prin extrapolare sau agregare. Marcat obligatoriu cu metoda. Se foloseste pentru:
- Volume cumulate calculate prin agregare istorica
- Proiectii bazate pe trend istoric
- Indicatori derivati din date primare

Exemplu: `Volumul cumulat al platilor operatorului A catre operatorul B [ESTIMARE PROPRIE, metoda: consum anual inmultit cu tarif reglementat acumulat, sursa primara: rapoartele anuale ale operatorului].`

### [NEVERIFICAT]

Informatie plauzibila dar fara sursa confirmata in momentul redactarii. Marcaj obligatoriu cu indicarea sursei potentiale. Se foloseste pentru:
- Cifre din memoria modelului fara sursa primara accesibila
- Atribuiri partiale (institutie cunoscuta, dar context specific neconfirmat)
- Detalii contextuale plauzibile dar nedocumentate

Exemplu: `Numarul total de unitati din categoria X este de aproximativ N [NEVERIFICAT, sursa necesara: raport statistic al autoritatii de reglementare].`

## Marcaje secundare

### [SCENARIU, ipoteza X]

Pentru constructii analitice care nu reflecta date observate, ci modelari ipotetice.

Exemplu: `Scenariul optimist presupune N-M unitati conectate la o sursa noua pana in 20XX [SCENARIU, ipoteze: faza pilot declanseaza in 20XX plus infrastructura adaptata in cativa ani].`

### [VERIFICARE NECESARA]

Pentru cifre, decizii sau cauze care exista probabil dar trebuie validate prin MCP specific.

Exemplu: `Decizia CCR nr. NNN/20XX [VERIFICARE NECESARA prin mcp__legal-verificator-ro__verify_ccr_citation, subiect declarat: securitate cibernetica].`

### [PRECIZIE LIMITATA]

Pentru date publicate cu interval, nu cu valoare punctuala.

Exemplu: `Indicatorul variaza intre A% si B% [PRECIZIE LIMITATA, sursa: studiu comparativ, interval pentru cazuri similare].`

### [CONFIDENTIAL]

Pentru informatii cu acces restrictionat care nu pot fi citate public.

Exemplu: `Volumul contractat pentru perioada urmatoare [CONFIDENTIAL, sursa: contract comercial cu acces restrictionat].`

### [DEPASIT]

Pentru informatii anterior valide dar care nu mai sunt actuale.

Exemplu: `Denumirea anterioara a institutiei era X [DEPASIT, institutia a fost reorganizata sub denumirea Y la data Z].`

## Reguli de utilizare

1. Niciodata nu lasa o cifra factuala fara marcaj cand sursa nu este evident citata in propozitia anterioara.
2. La sfarsitul documentului, lista [NEVERIFICAT] devine TODO de verificare pentru livrarea finala.
3. La sfarsitul documentului, lista [SCENARIU] permite cititorului sa inteleaga ce este factual versus modelat.
4. Marcajul [DATA] poate fi omis cand intregul capitol foloseste o singura sursa citata in titlu.
5. Marcajul [ESTIMARE] este obligatoriu chiar cand calculul pare evident, pentru transparenta metodei.
