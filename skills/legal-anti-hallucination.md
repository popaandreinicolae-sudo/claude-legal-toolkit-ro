---
name: legal-anti-hallucination
description: >
  Anti-halucinare juridica. MANDATORY inainte de a scrie orice referinta juridica.
  Triggere: "decizie CCR", "ICCJ", "Legea", "OUG", "OG", "HG", "articol", "art.",
  "Directiva", "Regulamentul", "CEDO", "CJUE", "considerent", "jurisprudenta".
---

# Anti-halucinare juridica

Protocolul canonic este [[zero-legal-hallucination]]. Acest skill il activeaza pe aceleasi
triggere si adauga poarta de verificare la final.

## Reguli

Nicio decizie, lege sau cauza nu se citeaza fara verificare prin sursa primara. Vezi
[[citation-verification-mandatory]].

Actele abrogate nu se citeaza ca fiind in vigoare. Verifica statutul prin MCP `eurlex`
(check_in_force) pentru actele UE si prin `legal-verificator-ro` pentru cele nationale.

Atribuirea de considerent se confirma verbatim cu
`scripts/citation_core.py --attr "<citat>" ccr <nr> <an>`.

## Flux

Foloseste [[verificare-citari-gate]] ca gate obligatoriu si subagentul `citation-verifier`
inainte de livrare. Pentru verificarea surselor, vezi [[legal-source-verification]].
