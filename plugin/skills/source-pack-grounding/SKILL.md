---
name: source-pack-grounding
description: |
  Grounding pe surse primare inainte de redactarea juridica. APLICA AUTOMAT inaintea oricarei redactari care va invoca decizii, legislatie sau jurisprudenta. Activare la cuvinte: "redacteaza opinie", "scrie articol", "expunere de motive", "nota de fundamentare", "intocmeste sesizare", "contestatie", "capitol teza", "analiza constitutionala", "propunere legislativa". Principiul source grounding: redactarea se face DIN surse reale adunate intai, nu din memoria modelului. Complementar cu task-contract (ancorare scop) si verificare-citari-gate (verificare la final).
version: 1.0
last_updated: 2026-06-28
---

# Source-pack grounding, redactarea din surse reale

Regula: inainte de redactarea unui document juridic care invoca surse, aduni intai sursele primare reale intr-un pachet, apoi redactezi din pachet. Verificarea se muta inaintea generarii, unde se produce fabricarea.

## Ordinea corecta a fluxului

1. task-contract, confirmi ce document trebuie produs.
2. source-pack-grounding (acest skill), aduni sursele primare reale.
3. redactare, exclusiv pe baza pachetului.
4. verificare-citari-gate, validare finala a citarilor.

## Cum aduni pachetul

Invoci subagentul `source-pack-builder` sau rulezi direct:

```bash
python "$HOME/.claude/scripts/build_source_pack.py" --refs "<lista referinte>" --out "$HOME/source_pack.md"
```

Completezi cu MCP-urile `eurlex` (statut in vigoare prin check_in_force), `hudoc` (CEDO) si `doctrine-verifier` (doctrina cu DOI/ISBN).

## Legislatia romaneasca intra in pachet numai prin sintact

Ordinea e sintact, apoi Indaco (lege5, lege6), apoi legislatie.just.ro. Nu se sare peste ea: sintact cazut inseamna Indaco, nu legislatie.just.ro.

Singura sursa care arata forma la zi este sintact. Ce vine din celelalte intra in pachet marcat, nu ca text in vigoare, fiindca ratarea nu se vede la citire. Doua capcane masurate:

- Forma neconsolidata. Fara cont, lege5 serveste actul cum a aparut in Monitorul Oficial, fara modificarile ulterioare, si o anunta printr-un banner usor de ratat. Asa a lipsit alin. (3) al art. 1 din Legea nr. 232/2016, introdus in 2022. Serverul marcheaza raspunsul cu `forma: neconsolidata` si `avertisment_sursa`; cand vezi campurile astea, nu conchide ca un alineat lipseste.
- Omonimia pe numar. Acelasi numar si an sunt purtate de acte de tipuri diferite. Cautarea dupa numar a dat Hotararea Camerei Deputatilor nr. 11/2018 in locul H.G. nr. 11/2018, care aproba Normele metodologice de aplicare a Legii nr. 295/2004. Confirmi dupa titlu si emitent, nu dupa numar si an.

Cand corectezi o citare scrisa de autor, pornesti de la ipoteza ca el a avut actul in fata. O citare care nu se confirma pe sintact se marcheaza `[NEVERIFICAT]`, nu se inlocuieste cu ce a intors sursa de rezerva.

## Materialul preluat de la autor intra in pachet ca materie prima

Un act mai vechi al autorului, un model al casei, o clauza, un statut sau o cerere-tip a fost
verificat pentru legea din ziua in care a fost scris. Reutilizarea nu mosteneste verificarea, la
orice lucrati si in orice materie.

Doua defecte diferite, fiecare cu alta verificare. Modelul poate fi depasit, adica legea s-a
schimbat sub el. Poate fi viciat din nastere, adica textul era contrar legii si in ziua in care a
fost scris. Al doilea defect nu iese din comparatia intre cele doua momente, fiindca acolo nu s-a
schimbat nimic.

Ordinea, la fiecare document preluat:

1. Dateaza documentul, anul redactarii si forma legii pe care autorul a avut-o in fata.
2. Adu legea la zi, sintact intai, forma consolidata de azi.
3. Confrunta documentul cu legea de azi, pe fond, clauza cu clauza, si intreg chiar cand legea a
   stat pe loc. Acolo unde legea rezerva o competenta unui organ anume, verifica fiecare atribuire
   in parte. Acolo unde impune o forma, o procedura, un termen sau un plafon, citeste clauza langa
   text.
4. Deschide istoricul de consolidare si compara cele doua momente, modificat, completat, abrogat,
   renumerotat dupa republicare. Pasul acesta prinde temeiurile si trimiterile ramase in urma.

Verificarea nu autorizeaza rescrierea textului autorului. Ce nu se mai confirma se semnaleaza in
conversatie, cu actul modificator si cu forma de azi. Ce ramane neconfirmat poarta [NEVERIFICAT].
Inainte de a spune ca autorul a citat gresit, presupune ca a avut actul in fata si verifica pe
sintact.

## Disciplina de redactare

Citezi doar ce apare in pachet, cu extras real. Orice afirmatie fara acoperire in pachet se marcheaza `[NEVERIFICAT]`. Nu adaugi din memorie citari care nu sunt in pachet. Pentru actele UE folosesti forma in vigoare confirmata, nu cea abrogata. Volumul documentului urmeaza substanta surselor reale, nu invers.
