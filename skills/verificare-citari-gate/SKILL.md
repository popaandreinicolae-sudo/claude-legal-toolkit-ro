---
name: verificare-citari-gate
description: |
  Gate obligatoriu de verificare a citarilor juridice inainte de livrare. APLICA AUTOMAT la orice document juridic care contine decizii CCR/ICCJ, legi, OUG, OG, HG, ordine, directive sau regulamente UE, cauze CEDO/CJUE, doctrina. Activare la cuvinte: "decizie", "Decizia", "CCR", "ICCJ", "Legea", "OUG", "OG", "HG", "Ordinul", "Directiva", "Regulamentul", "art.", "articolul", "CEDO", "CJUE", "considerent", "jurisprudenta", "opinie juridica", "sesizare", "expunere de motive", "nota de fundamentare", "contestatie", "teza", "articol academic". Construit pe auditul forensic din 27 iunie 2026, care a aratat ca halucinarea de citare juridica este eroarea dominanta si cea mai periculoasa (decizii inventate, acte abrogate citate ca in vigoare, articole inexistente, atribuiri gresite de considerent).
version: 1.0
last_updated: 2026-06-27
---

# Verificare citari gate, protocol obligatoriu

Regula de fier: niciun document cu citari juridice nu pleaca fara verificarea fiecarei citari prin sursa primara. Acest gate este complementar cu hook-ul determinist `citation_guard.py` (care ruleaza automat la fiecare scriere) si cu subagentul `citation-verifier` (audit aprofundat la cerere).

## Cand se aplica

La orice redactare sau revizuire de document juridic care invoca decizii, acte normative, jurisprudenta UE sau doctrina. Cu prioritate la documentele cu miza externa: teza, opinie juridica, sesizare CCR, expunere de motive, contestatie, articol publicabil.

## Protocolul in trei pasi

### Pasul 1, marcaj la generare

Pe masura ce scrii o citare pe care nu ai verificat-o efectiv printr-o sursa in aceasta sesiune, o marchezi imediat `[NEVERIFICAT]`. Nu lasi nicio citare neverificata fara marcaj. Aceasta este regula 14 din CLAUDE.md, incalcata sistematic in trecut.

### Pasul 2, verificare prin surse primare

Inainte de livrare, validezi fiecare citare:
- decizii CCR si legislatie RO, prin MCP `legal-verificator-ro`;
- jurisprudenta CEDO, prin MCP `hudoc`;
- legislatie si jurisprudenta UE, prin MCP `eurlex`, cu atentie speciala la statutul in vigoare/abrogat (tool `check_in_force`);
- doctrina, prin MCP `doctrine-verifier`.

Pentru verificare rapida deterministica poti rula direct:

```bash
python "$HOME/.claude/scripts/citation_core.py" [path]
```

### Pasul 3, audit independent inainte de livrare

Pentru documentele cu miza externa, invoci subagentul `citation-verifier` („verifica citarile @document"). El extrage toate citarile, le valideaza prin MCP-uri, verifica si atribuirea considerentelor si intoarce o lista rosie de citari de eliminat sau corectat.

## Verdicte si actiuni

- CONFIRMAT, citarea exista si statutul corespunde. Elimini marcajul `[NEVERIFICAT]`.
- NEGASIT, citarea nu a fost gasita in nicio sursa primara. O tratezi ca posibil inventata, o elimini sau o reformulezi, nu o livrezi.
- ABROGAT, actul citat ca temei in vigoare este abrogat. Il inlocuiesti cu actul aplicabil (ex. Directiva 2009/73/CE inlocuita de Directiva (UE) 2024/1788).
- ATRIBUIRE GRESITA, considerentul apartine altei decizii. Corectezi numarul sau elimini citatul.
- NEVERIFICAT, sursa nu a raspuns. Pastrezi marcajul si semnalezi utilizatorului, nu prezinti citarea ca sigura.

## Capcane cunoscute (din audit)

Transpunerea NIS, „Legea 58/2019" folosita gresit (verifica actul exact aplicabil). Acte UE abrogate citate ca temei operativ. Decizii ICCJ inexistente cu citat verbatim. Numere de decizii CCR plauzibile dar fabricate. Denumiri institutionale depasite (MFP in loc de MF din 2021). Volumul mare de citari coreleaza cu risc crescut de fabricare, nu cu rigoare.
