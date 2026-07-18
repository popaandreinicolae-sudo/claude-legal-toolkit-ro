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
python "%USERPROFILE%/.claude/scripts/build_source_pack.py" --refs "<lista referinte>" --out "%USERPROFILE%/source_pack.md"
```

Completezi cu MCP-urile `eurlex` (statut in vigoare prin check_in_force), `hudoc` (CEDO) si `doctrine-verifier` (doctrina cu DOI/ISBN).

## Disciplina de redactare

Citezi doar ce apare in pachet, cu extras real. Orice afirmatie fara acoperire in pachet se marcheaza `[NEVERIFICAT]`. Nu adaugi din memorie citari care nu sunt in pachet. Pentru actele UE folosesti forma in vigoare confirmata, nu cea abrogata. Volumul documentului urmeaza substanta surselor reale, nu invers.
