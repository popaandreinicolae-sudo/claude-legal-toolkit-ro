---
name: legal-source-verification
description: >
  Verificare surse legale prin MCP-urile juridice inainte de a le cita.
  Triggere: "sursa", "verifica sursa", "confirma decizia", "exista aceasta lege",
  "in vigoare", "abrogat", "link oficial", "just.ro", "EUR-Lex", "HUDOC".
---

# Verificare surse legale

Skill de verificare a existentei si statutului surselor juridice. Complementar cu
[[verificare-surse]] (mai larg) si cu [[legal-anti-hallucination]].

## Unde verifici

Legislatie si decizii nationale prin MCP `legal-verificator-ro` (CCR, ICCJ, legislatie RO,
lege5/lege6). Legislatie UE si CJUE prin MCP `eurlex`. Jurisprudenta CEDO prin MCP `hudoc`.
Doctrina prin MCP `doctrine-verifier`.

## Reguli

O sursa negasita pe just.ro se escaladeaza, nu se sterge automat, fiindca exista
fals-pozitive. Regula de precedenta, sursa primara MCP bate indiciul de hook, care bate
memoria modelului (vezi `scripts/SYSTEM_CONTRACT.md`).

Cand MCP-ul principal nu raspunde, aplica [[mcp-fallback-strategy]]. Pentru pattern-urile de
URL CCR reale, vezi [[ccr-url-patterns]].
