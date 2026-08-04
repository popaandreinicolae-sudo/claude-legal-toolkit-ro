---
name: verificare
description: |
  Verificarea de armonie a toolkit-ului: piesele se calca intre ele? Invocata prin /verificare, sau la cuvintele "verifica armonia", "se bat cap in cap", "contradictii intre reguli", "merge totul impreuna", "audit de integrare". Ruleaza cautarea de contradictii intre toate locurile unde exista reguli, plus suitele de regresie si proba serverelor MCP. Raporteaza, nu repara: contradictiile le judeca autorul.
version: 1.0
last_updated: 2026-07-30
---

# Verificarea de armonie

Fiecare piesa merge singura. Intrebarea e daca merg impreuna.

Pe 30 iulie 2026, in aceeasi zi, s-au gasit cinci defecte de tipul "doua straturi spun
lucruri diferite". Cel mai grav: autorul ceruse ca "reprezinta" si "constituie" sa fie
pastrate, iar textul injectat la fiecare mesaj al lui ii spunea modelului, cuvant cu
cuvant, contrariul. A stat acolo ore intregi si a iesit la iveala din intamplare.

## Ce se ruleaza

Contradictii intre regulile din toate sursele, caietul, CLAUDE.md, instructiunile
serverelor MCP, skill-urile, preferintele de cont si hook-urile de stil:

```bash
python "$HOME/.claude/scripts/contradictii.py"
```

Derapajul intre copiile configuratiei, adica intre ce ruleaza in Claude Code, ce e
versionat in depozit, artefactul care pleaca in Desktop si arhiva de reinstalare:

```bash
python "$HOME/.claude/scripts/armonie_copii.py"
```

Suitele de regresie:

```bash
python "$HOME/.claude/scripts/selftest_citari.py"
python "$HOME/.claude/scripts/selftest_suprascriere.py"
python "$HOME/.claude/scripts/selftest_arhiva.py"
python "$HOME/.claude/skills/docx-footnotes/scripts/selftest_pachet.py"
python "D:/PYTHON DEVELOPMENT PROJ/persona-adrian-zamfir/tools/selftest.py"
```

Proba de suprafata Desktop se face pe scripturile EXTRASE DIN ARHIVA, nu pe cele din
`~/.claude`. Cele doua pot diferi oricand, iar ce conteaza acolo e ce pleaca in pachet.

Apoi, pe rand: fiecare server MCP raspunde la un apel ieftin; fiecare hook inregistrat
exista si e fail-open pe intrare stricata; hook-urile nu blocheaza munca legitima a
celorlalte; arhiva de livrari si /revizuire functioneaza.

## Ce NU se face

Contradictiile nu se rezolva singure. Se raporteaza autorului, cu frazele puse fata in
fata, iar el hotaraste care regula ramane. Un strat care ar decide singur ar corecta
intr-o zi tocmai regula lui.

Semnalarile sunt candidate. Cautarea lucreaza pe termeni citati si pe polaritatea frazei,
deci poate arata si perechi care doar par sa se contrazica. Se citeste fiecare inainte de
a fi dusa autorului.

## Ce se raporteaza la final

Cate verificari au trecut si care au cazut, cu numele lor. Contradictiile gasite, fiecare
cu sursele si frazele in conflict. Ce nu s-a putut verifica si de ce.
