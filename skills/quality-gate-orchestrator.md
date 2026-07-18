---
name: quality-gate-orchestrator
description: >
  Final quality gate for doctoral documents. Runs ALL verification checks before delivery.
  Triggers: "quality gate", "verificare finala", "livrare", "final check", "pre-delivery".
---

# Quality Gate Orchestrator — Verificare Finala Document Doctoral

## CHECKLIST OBLIGATORIU (executa in ordine)

### 1. VERIFICARE NOTE DE SUBSOL
- [ ] Toate notele au surse reale (verificate prin MCP)
- [ ] Toate numele de autori sunt complete (prenume + nume)
- [ ] Toate paginile sunt confirmate sau marcate [neverificat]
- [ ] Stilul de citare e unitar (format UB Drept)
- [ ] Nu exista note goale sau incomplete

### 2. VERIFICARE JURIDICA
- [ ] Toate actele normative sunt in vigoare (sau marcat explicit abrogat)
- [ ] Toate deciziile CCR exista si au subiectul corect
- [ ] Toate hotararile CEDO au numarul de cerere corect
- [ ] Toate cauzele CJUE au ECLI-ul corect
- [ ] Rationamentele juridice sunt consistente logic

### 3. VERIFICARE LINGVISTICA
- [ ] Zero fraze tipice AI ("genuinely", "honestly", "straightforward", "deep dive", "leverage")
- [ ] Zero "In esenta" repetat
- [ ] Zero "Merita mentionat ca" excesiv
- [ ] Acorduri gramaticale corecte
- [ ] Acronime: integral la prima aparitie + in note, acronim in rest

### 4. VERIFICARE FORMAT
- [ ] TNR 12 corp, TNR 10 note, TNR 14 titluri
- [ ] Justified peste tot
- [ ] Line spacing 1.5 corp, simplu note
- [ ] Margini: 2.5 sus/jos, 3 stanga, 2 dreapta
- [ ] Numerotare pagini jos-centru
- [ ] Bold/italic conform regulilor

### 5. VERIFICARE METADATA (anti-AI)
- [ ] Author = "Andrei Nicolae Popa"
- [ ] lastModifiedBy = "Andrei Nicolae Popa"
- [ ] Revision = numar plauzibil (10-20)
- [ ] Zero comentarii, tracked changes
- [ ] Zero stiluri cu nume suspecte
- [ ] Zero caractere invizibile ZWSP/ZWNJ

### 6. VERIFICARE BIBLIOGRAFIE
- [ ] Toate sursele din note sunt in bibliografie
- [ ] Nu exista surse in bibliografie care lipsesc din note
- [ ] Ordonare corecta pe categorii
- [ ] Deduplicare completa

### 7. TEST TEHNIC
```python
from docx import Document
d = Document('final.docx')
print(f"{len(d.paragraphs)} paragrafe OK")
print(f"{len(d.footnotes)} note OK")
```

## OUTPUT
Raport cu: items verificate / corecte / cu probleme / neverificate.
