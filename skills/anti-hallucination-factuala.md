---
name: anti-hallucination-factuala
description: >
  Anti-halucinare pe date, cifre, procente, sume, denumiri institutionale si atribuiri.
  APLICA AUTOMAT la orice document peste 500 de cuvinte care contine numere sau denumiri.
  Triggere: "cifra", "procent", "suma", "milioane", "miliarde", "EUR", "RON", "lei",
  "MWh", "GWh", "km", "ha", "indicator", "buget", "denumire institutie", "atribuire".
---

# Anti-halucinare factuala

Acest skill este poarta pe fapte, nu pe stil. Canonicul complet se afla in
[[anti-hallucination-document]], aplicabil oricarui document profesional, si in
[[anti-hallucination-energetic]] pentru sectorul energetic.

## Reguli de baza

Orice cifra fara sursa confirmata se marcheaza `[NEVERIFICAT]`. Vezi [[unsourced-figures-neverificat]].

Denumirile institutionale se verifica in `scripts/reference_names.json` (denumiri curente,
de exemplu MF nu MFP). Atribuirile editoriale fara DOI sau ISBN se semnaleaza.

Volumul mare al unui output inseamna risc de fabricare, nu calitate. Vezi [[volume-equals-risk]].

## Verificare determinista

La fiecare scriere ruleaza hook-urile `numeric_consistency_guard.py`, `phantom_source_guard.py`
si `citation_guard.py`. Inainte de livrare ruleaza subagentul `quality-gate` si, la nevoie,
`hallucination-redteam`. Pentru citari juridice foloseste [[zero-legal-hallucination]].
