---
name: zero-legal-hallucination
description: >
  Prevents ALL legal hallucinations. MANDATORY before writing any legal reference.
  Triggers: any mention of law, article, decision, court case, legal principle.
---

# Zero Legal Hallucination Protocol

## REGULA ABSOLUTA

INAINTE de a scrie orice referinta juridica, VERIFICA prin tool:

1. **Decizie CCR** → `verify_ccr_citation` sau `fetch_ccr_decision_text`
2. **Hotarare CEDO** → `hudoc_search_cases` sau `hudoc_get_judgment`
3. **Cauza CJUE** → `eurlex_search_caselaw` sau `eurlex_get_celex`
4. **Lege/OUG/HG Romania** → `search_legislation` sau `lege5_search`
5. **Directiva/Regulament UE** → `eurlex_search_legislation`
6. **Articol specific** → `fetch_article_text`
7. **Doctrina** → `scholar_search` sau `academic-search`

## DACA NU POTI VERIFICA

Scrie: `[NEVERIFICAT — necesita confirmare manuala]`

NU inventa:
- Numere de decizie
- Numere de cerere CEDO
- Numere de cauza CJUE
- Pagini din carti
- Ani de publicare
- Edituri
- Prenume de autori
- Numere de articol/alineat

## VERIFICARE INCRUCISATA

Pentru surse critice (CCR, CEDO, CJUE), verifica pe DOUA surse diferite:
- CCR: legislatie.just.ro + lege5.ro
- CEDO: hudoc + WebSearch
- CJUE: eurlex + WebSearch
