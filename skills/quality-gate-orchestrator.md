---
name: quality-gate-orchestrator-legacy
description: >
  Fisier depasit. Verificarea de continut sta la subagentul quality-gate, cea de fisier
  la skills/docx-livrare-check/SKILL.md.
---

# Depasit, impartit in doua pe 29 iulie 2026

Acest fisier plat nu se incarca de nimeni si nu trebuie urmat. Checklistul lui raspundea
la aceleasi declansatoare ca subagentul `quality-gate`, deci pe aceeasi cerere porneau
amandoua si dadeau verdicte diferite. A fost impartit dupa ce verifica fiecare.

Continutul ramane la subagentul `quality-gate`, care ruleaza `hooks/quality_gate.py` si
cheama reviewerii, `citation-verifier`, `juridic-style-reviewer`, `anti-ai-tone-reviewer`.
Acopera sectiunile 1, 2, 3 si 6 din checklistul vechi, note de subsol, verificare
juridica, verificare lingvistica, bibliografie, dar prin surse primare, nu bifat manual.

Fisierul trece la `skills/docx-livrare-check/SKILL.md`, care ruleaza `check_livrare.py`.
Acopera sectiunile 4, 5 si 7, format, metadate, test tehnic, comparate contra stilului
de casa masurat.

Trei reguli din varianta veche au fost corectate. Numele din metadate e cel corect.
Numarul de revizii fabricat a fost scos. Regula „zero tracked changes" a devenit
conditionata, fiindca pe un redline marcajele sunt chiar livrabilul.
