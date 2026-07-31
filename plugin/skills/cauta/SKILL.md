---
name: cauta
description: |
  Cauta un termen in discutia curenta si arata unde a aparut. Invocata prin /cauta <termen>, sau la cuvintele "cauta in conversatie", "unde am zis de", "gaseste in discutie", "ce am vorbit despre", "unde ai citat". Citeste transcrierea de pe disc, deci vede toata discutia, nu doar ce e pe ecran.
version: 1.0
last_updated: 2026-07-31
---

# Cauta in discutia curenta

Interfata nu are casuta de cautare, iar Ctrl+F prinde doar ce e randat. Transcrierea sta
insa pe disc, ca `.jsonl`, in `~/.claude/projects/<dosar>/`.

## Cum raspunzi

Ruleaza si arata rezultatele:

```bash
python "$HOME/.claude/scripts/cauta_in_discutie.py" "<termen>"
```

Implicit cauta doar in mesajele autorului, fiindca de obicei vrea sa regaseasca ce a cerut.
Adauga `--tot` cand vrea si raspunsurile mele, `--context 400` cand vrea bucati mai lungi.

Scriptul ignora diacriticele, deci "conditionalitate" gaseste si "condiționalitate".

## Ce faci cu rezultatele

Nu le arunca brut. Grupeaza-le pe teme si spune, pentru fiecare, ce s-a stabilit acolo.
Autorul cauta ca sa regaseasca o decizie, o formulare aprobata sau un motiv pentru care
am schimbat ceva, nu ca sa citeasca linii de log.

Cand termenul nu apare deloc, incearca o forma mai scurta sau radacina cuvantului inainte
de a raspunde ca nu exista. "raporturi comerciale" nu gaseste "raporturilor comerciale".

## Cand cauta intr-o discutie mai veche

`--fisier <cale>` tinteste alta transcriere. Fara el, se ia cea mai recent modificata.
Lista discutiilor se vede si cu `/resume`.
