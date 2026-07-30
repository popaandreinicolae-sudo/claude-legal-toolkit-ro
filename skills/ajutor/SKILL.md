---
name: ajutor
description: |
  Ce comenzi are autorul de tastat si ce se aprinde singur. Invocata prin /ajutor, sau la cuvintele "ce comenzi am", "am uitat comenzile", "ce pot sa iti cer", "ce stie toolkit-ul", "cum se cheama comanda". Se citeste din skill-urile instalate, deci nu poate ramane in urma.
version: 1.0
last_updated: 2026-07-30
---

# Ce comenzi am

Lista de la `/` are saptesprezece intrari si cele mai multe se aprind singure, deci
comenzile pe care autorul le tasteaza efectiv se pierd printre ele.

## Cum raspunzi

Ruleaza si arata rezultatul:

```bash
python "$HOME/.claude/scripts/comenzi.py"
```

Cu `--toate` intra in raspuns si skill-urile automate, cand autorul le cere.

In Claude Desktop, unde scripturile nu ruleaza, raspunzi din ce vezi in lista de skill-uri
a plugin-ului: comenzile de tastat sunt cele a caror descriere spune "Invocata prin /".

## De ce nu se scrie lista aici

Lista de unelte a serverului persona era scrisa de mana si a ramas in urma de doua ori, cu
patru unelte cu tot. Un ajutor care minte e mai rau decat lipsa lui. Scriptul citeste
skill-urile instalate si le clasifica dupa cum se declara ele insele, deci nu are cum sa
ramana in urma.

Cand adaugi un skill nou pe care autorul urmeaza sa il tasteze, scrie in descrierea lui
"Invocata prin /nume". Asta e singurul lucru care il face sa apara aici.

## Ce mai spui la final

Ca poate tasta `/` in Claude Code pentru lista completa, si ca nu e obligat sa stie numele:
ii poate spune in cuvinte ce vrea, fiindca fiecare skill are cuvintele lui de declansare.
