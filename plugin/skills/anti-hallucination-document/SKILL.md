---
name: anti-hallucination-document
description: |
  Protocol universal anti-halucinare pentru orice document profesional generat (raport, articol, opinie, contract, brief, policy paper, document de strategie, prezentare). APLICA AUTOMAT la orice generare de document peste 500 cuvinte care include cifre, sume, procente, denumiri institutionale, articole de lege, decizii, numere proiect, indicatori. Activare la cuvinte: "raport", "articol", "opinie juridica", "policy paper", "white paper", "brief", "memoriu", "strategie", "diagnoza", "fundamentare", "scenariu", "estimare", "proiect", "buget", "cifra", "procent", "milioane", "miliarde", "MWh", "GWh", "km", "ha", "EUR", "RON", "lei". Activare automata la orice document factual cu mize profesionale. Construit pe pattern-ul halucinatiilor identificate in documente profesionale generate de LLM (numere de personal inventate, sume de finantare fabricate, scenarii cu cifre fictive, anexe inventate, capitole goale generate ca slot fillers).
version: 1.0
last_updated: 2026-06-01
---

# Anti-Hallucination Document, Protocol Universal

Acest skill previne halucinarea sistemica documentata in documente profesionale generate de modele LLM. Cazuri tipice prevenite: capitole goale generate ca slot fillers, cifre concrete fabricate (numar de personal, sume de finantare, indicatori economici), scenarii cu indicatori inventati, atribuiri eronate, anexe fictive cu tabele comparative neverificate.

## Principiul fundamental

Orice cifra, suma, procent, denumire institutionala sau atribuire dintr-un document profesional necesita sursa verificabila. Cand sursa lipseste, marcam explicit. Cand exista alternativa de calcul, descriem metoda. Apreciem ca disciplina sursei elimina 90% din halucinari sistematice.

## Cele 12 reguli pozitive

### Regula 1, citeaza pasajul sursa exact

Pentru fiecare afirmatie factuala, citeaza pasajul sursa cu numar pagina, paragraf sau sectiune. Format: `(Sursa: Strategia X 2021-2030, capitolul 4.2, p. 87)` sau `(Sursa: Planul Sectorial Y 2025-2035, obiectiv 3.1, p. 12)`. Daca folosesti Citations API, lasa modelul sa lege automat fragmentele.

### Regula 2, marcheaza [NEVERIFICAT] explicit

Cand o informatie pare plauzibila dar nu ai sursa primara confirmata, marcheaza-o:
```
[NEVERIFICAT, sursa necesara: documentul X sau institutia Y]
```
Format alternativ pentru estimari proprii:
```
[ESTIMARE PROPRIE, metoda de calcul: ...]
```

### Regula 3, distinge intre 3 categorii de informatie

Marcheaza fiecare claim factual:
- `[DATA]`, confirmat cu sursa primara verificata
- `[ESTIMARE]`, calcul propriu cu metoda explicata
- `[NEVERIFICAT]`, plauzibil dar neconfirmat

Niciodata nu amesteca categoriile. O estimare prezentata ca data este minciuna. Date neverificate prezentate ca certe sunt halucinatii.

### Regula 4, scrie cifre rotunde doar daca sunt verificat rotunde

Cifre foarte precise aparute din senin (un numar exact de angajati, un prag rotund de capacitate instalata, un raport cost-beneficiu cu doua zecimale, un procent de absorbtie) sunt marker AI clasic. Inventezi precizie falsa. Cand ai cifra reala, scrie-o exact. Cand nu o ai, marcheaza-o ca neverificata sau elimina-o.

### Regula 5, atribuie cu nume complete

Pentru autori, scrie nume si prenume complete confirmate. Pentru instituții, denumire oficiala completa la prima aparitie. Pentru acte normative, tipul plus numarul plus anul. Daca ai doar o initiala, scrie initiala, nu inventezi prenumele.

### Regula 6, valideaza ca sursa exista inainte de citare

Pentru decizii CCR, hotarari CEDO, cauze CJUE, articole legi, foloseste MCP-urile disponibile (legal-verificator-ro, eurlex, hudoc) sau marcheaza [VERIFICARE NECESARA]. Niciodata din memorie.

### Regula 7, separa fapte de scenarii

Cand generezi scenarii alternative (de exemplu un scenariu de referinta si unul optimist), marcheaza explicit ca scenariile sunt constructii analitice, nu prognoze ale unor surse oficiale. Toate cifrele scenariilor trebuie marcate [SCENARIU, ipoteza X plus ipoteza Y].

### Regula 8, evita anexele de tip slot filler

Daca prompt-ul cere "raport complet cu anexe", nu fabrica continut pentru anexe pe care nu le ai. Intreaba utilizatorul ce continut concret are pentru fiecare anexa. Mai bine 3 anexe verificate decat 6 anexe inventate.

### Regula 9, mentine consistenta numerotarii

Capitolele si sub-sectiunile trebuie numerotate coerent. Daca cap. XI ramane gol, elimina-l, nu lasa slot orfan. Daca cap. XII devine XI dupa eliminare, renumeroteaza si pe 12.1 in 11.1.

### Regula 10, foloseste Project Knowledge daca este disponibil

In Cowork Projects, citeste DIRECT din PDF-urile uploadate. Nu inferezi continutul. Cand un PDF nu este uploadat, intreaba utilizatorul daca poate fi adaugat la Project Knowledge.

### Regula 11, raport final cu sectiune "Surse citate"

La sfarsitul documentului, genereaza obligatoriu o sectiune cu toate sursele citate, paginile exacte, link-urile catre PDF-urile uploadate sau MCP-urile invocate. Aceasta sectiune permite verificare independenta de catre cititor.

### Regula 12, intrebari explicite la inceputul fiecarui capitol

Inainte de a genera un capitol nou, intreaba utilizatorul:
1. Ce surse primare am incarcate pentru acest capitol?
2. Ce cifre cheie sunt obligatorii?
3. Care este audienta finala si pragul de risc al erorilor?

## Protocol activare in Cowork

Cand acest skill devine activ in Cowork prin Skills Directory sau prin upload custom, comportament obligatoriu:

1. La inceputul oricarei sesiuni de drafting, intreaba ce surse sunt disponibile.
2. La fiecare 500 cuvinte generate, ofera utilizatorului oportunitatea de fact-check intermediar.
3. La final, listeaza in raport sectiunea "Surse citate" plus lista [NEVERIFICAT] cu sugestii de verificare.
4. Daca utilizatorul foloseste Citations API, lasa modelul sa lege automat.

## Integrare cu skill-uri si MCP-uri existente

Acest skill ruleaza in pipeline cu:
- `zero-hallucination-citations`, citarea bibliografica corecta
- `verificare-legislatie`, validare acte normative in vigoare
- `anti-ai-tone`, stil natural fara accent AI
- `legal-verificator-ro` MCP, verificare decizii CCR si legislatie RO
- `eurlex` MCP, validare directive si regulamente UE
- `hudoc` MCP, validare hotarari CEDO

## Detalii suplimentare

Vezi `references/checklist-fact-check.md` pentru checklist complet pre-livrare. Vezi `references/marcaje-uncertainty.md` pentru taxonomia marcajelor. Vezi `references/source-types-priority.md` pentru ordinea prioritate surse.

Scriptul `scripts/compare_docx_versions.py` compara automat doua versiuni de document pentru a identifica diferentele cantitative (cifre, capitole, anexe). Scriptul `scripts/verify_citations.py` extrage toate citarile dintr-un document si le valideaza prin MCP-uri disponibile.

## Regula extinsa, verificare de completitudine si surse (adaugata 27 iunie 2026)

Bazata pe auditul forensic care a aratat ca modelul produce volum ca umplutura cand nu are substanta reala. Trei verificari obligatorii inainte de livrare, intarite de hook-ul determinist `phantom_source_guard.py`:

1. Surse-fantoma. Nicio afirmatie de fond nu se sprijina pe o eticheta de sursa neverificabila (Google Drive, zf.ro, economedia.ro, senat.ro, "document intern") sau pe un "studiu confidential/nepublicat" cu citat verbatim. Inlocuiesti cu sursa primara reala sau marchezi `[NEVERIFICAT]`.

2. Atribuiri editoriale. Orice referinta de doctrina cu editie, jurnal sau an supra-specific trebuie sa aiba DOI sau ISBN verificabil prin `doctrine-verifier`. Fara identificator, nu o prezinti ca sursa confirmata. Capcana reala: atribuiri fabricate de tip "editia a patra" sau nume de jurnal inventat.

3. Completitudine structurala. Orice numar anuntat se confrunta cu continutul efectiv. Cand textul spune "cele patru metode", "3 anexe" sau "urmatoarele cinci conditii", lista trebuie sa contina exact atatea elemente. Discrepanta semnaleaza generare oprita prematur sau slot-uri declarate fara umplere.

Volumul mare al unui document coreleaza cu risc crescut de fabricare, nu cu rigoare. Tratezi orice sectiune ampla fara sursa ca un candidat de verificare, nu ca o dovada de seriozitate.
