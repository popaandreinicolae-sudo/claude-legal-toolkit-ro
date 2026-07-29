---
name: docx-safe-edit-legacy
description: >
  Fisier depasit. Versiunea care se aplica sta in skills/docx-safe-edit/SKILL.md.
---

# Depasit, vezi `skills/docx-safe-edit/SKILL.md`

Acest fisier plat nu se incarca de nimeni si nu trebuie urmat. A fost inlocuit pe
29 iulie 2026 de skill-ul propriu-zis, `skills/docx-safe-edit/SKILL.md`, care se
instaleaza in `~/.claude/skills/` prin `sync-claude.ps1`.

Doua reguli s-au schimbat la mutare, deci varianta veche produce rezultate gresite.

Metadatele nu se mai suprascriu la gramada. Pe un document primit, `author` ramane al
celui care l-a creat, se schimba doar `last_modified_by`. Varianta veche stergea numele
autorului original din proprietatile fisierului.

Numarul de revizii fabricat, `revision = 12`, a fost scos. Falsifica istoricul de
editare si nu aduce nimic documentului.
