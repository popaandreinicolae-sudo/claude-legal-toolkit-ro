---
name: revizuire
description: |
  Revizuirea de dimineata: compara documentele livrate autorului cu ce e acum in dosarele lui si arata ce a schimbat el. Invocata prin /revizuire, sau la cuvintele "revizuire de dimineata", "ce am modificat eu", "compara cu ce mi-ai dat", "vezi ce am schimbat in documente". Nu modifica niciun document si nu scrie nimic in caiet fara aprobarea autorului, punct cu punct.
version: 1.0
last_updated: 2026-07-30
---

# Revizuirea de dimineata

Din modificarile autorului se invata, dar numai daca sunt citite. Pe 30 iulie 2026 el a
rescris 33 de paragrafe dintr-o exceptie livrata, a scos trei note de subsol si a adaugat
un argument pe Decizia ICCJ, RIL nr. 10/2019. Nimic din toate astea nu ajunsese la mine;
le-am vazut din intamplare, fiindca mai aveam copia livrata intr-un dosar temporar care
urma sa dispara.

Skill-ul asta inchide bucla. Arhiva pastreaza ce am livrat, compararea arata ce a schimbat
el, iar din diferenta ies reguli pentru caiet, pe care le aproba el.

## Cum se ruleaza

Pe Claude Code:

```bash
python "$HOME/.claude/scripts/compara_livrari.py"
python "$HOME/.claude/scripts/compara_livrari.py" --document "D:/Clienti/.../act.docx"
```

In Claude Desktop, unde scripturile nu ruleaza, se cheama `livrare_compara` din serverul
MCP persona-adrian-zamfir.

## Ce raportezi

Pentru fiecare document schimbat, ce a adaugat, ce a scos, ce a rescris, pe paragrafe,
plus diferentele care conteaza la nivel de fraza. Pentru restul, o singura linie cu cate
au ramas neschimbate si cate sunt retrase din rotatie.

Cand livrarea poarta insemnare de provenienta si ciorna autorului e neatinsa, modificarile
se impart in doua si se arata separat. Amandoua sunt lectii, de feluri diferite:

- pe text scris de mine, afli ce respinge el la scrisul meu, corectura directa;
- pe text scris de el, afli ce inseamna pentru el "mai bun", adica standardul spre care ar
  trebui sa scriu de la prima incercare. Semnalul asta e mai curat, fiindca nu repara
  textul altcuiva.

Nu se arunca niciuna dintre categorii.

## Regulile care nu se incalca

Nu se modifica niciun document din dosarele autorului. Doar se citeste.

Legatura intre livrare si documentul de pe disc se face pe aceeasi denumire. Cand
documentul nu mai e sub numele livrat, NU se ghiceste si NU se cauta ce seamana; se
intreaba autorul care e calea.

Un document neschimbat doua zile calendaristice la rand iese din rotatie si reintra singur
cand se schimba. Doua rulari in aceeasi zi se socotesc una. Regula e in cod, nu in judecata
mea.

## Ce se face la final

Se propun regulile desprinse din modificari, ca intrari pentru caiet, fiecare cu motivul
din spate si cu categoria din care a iesit. **Nimic nu se scrie in caiet fara aprobarea
autorului, punct cu punct.** Regula se deduce, nu se citeste din diferenta: modificarea e
un caz, iar in caiet intra principiul din spatele ei.
