# Research Context Persist — Salvare cercetare între sesiuni

**Scop**: Eliminarea pierderii de research la context compaction sau la sesiuni noi. Fișierele `tool-results/mcp-workspace-web_fetch-*.txt` din sesiunea anterioară **nu** mai sunt accesibile pe VM nou — toată cercetarea se pierde.

## Regula 1 — Salvează research-ul ÎN MOD PROACTIV ca Markdown

Imediat ce extragi informații utile dintr-un `web_fetch` voluminos, salvează-le în:

```
~/.claude/projects/{project-slug}/research/{topic}-{YYYY-MM-DD}.md
```

Pe Windows: `%USERPROFILE%\.claude\projects\{project-slug}\research\`

**Nu** te baza pe fișierele `tool-results/` din sandbox — sunt efemere.

## Regula 2 — Format research note

```markdown
---
topic: "CCR Decizia 136/2018"
date: 2026-04-27
sources:
  - https://legislatie.just.ro/Public/DetaliiDocumentAfis/200293
  - https://www.zf.ro/politica/cc-despre-imunitatea-parlamentara-...
extracted_via: web_fetch + grep
context: "Punct de vedere pe tema analizata"
---

# CCR 136/2018 — Imunitatea parlamentară

## Dispozitiv (citat verbatim, paragraf 65)

> [Textul exact citat din sursa primară]

## Considerente relevante

- Para 27: [...]
- Para 41: [...]

## Citare formatată academic

Curtea Constituțională, Decizia nr. 136 din 21 martie 2018,
M. Of., Partea I, nr. 383 din 4 mai 2018, par. 65.

## Note metodologice

- Sursa primară (legislatie.just.ro/200293) a returnat 502 — extras prin Wayback / lege5
- Confirmat ISBN ediție comentată: 978-606-XX-XXXX-X
```

## Regula 3 — Folder structure standard

```
~/.claude/projects/{slug}/
├── research/                # extracte web_fetch persistente
│   ├── ccr-decizii.md
│   ├── cedo-cauze.md
│   ├── cjue-cauze.md
│   └── doctrina.md
├── notes/                   # observații proprii
│   └── analiza-{topic}.md
└── outputs/                 # documente generate (DOCX, PDF)
    └── document-output.docx
```

## Regula 4 — La începutul fiecărei sesiuni noi

**Verifică automat** dacă există research persistent pentru proiect:

```bash
ls ~/.claude/projects/$(basename $PWD)/research/ 2>/dev/null
```

Dacă există, citește MD-urile **înainte** de a re-face research pe aceleași teme.

## Regula 5 — Anti-duplicare web_fetch

Înainte de a face un `web_fetch` pe URL deja accesat în trecut:

1. Caută în `~/.claude/projects/*/research/*.md` cu Grep pentru URL-ul respectiv
2. Dacă apare, **citește** fișierul MD în loc de a re-fetch

## Regula 6 — Token overflow → salvare imediată în research

Dacă `web_fetch` salvează în `tool-results/X.txt` (token overflow):

1. Folosește `bash grep` pentru a extrage **doar** secțiunile relevante (max 2-5 KB)
2. Salvează extractul în `research/{topic}.md` cu metadata sursă completă
3. **NU** te baza că fișierul `tool-results/` va fi disponibil în sesiunea următoare

## Regula 7 — Memorie globală pentru fapte juridice cheie

Pentru fapte care depășesc un proiect (ex. „Decizia CCR 70/2023 dispozitiv = securitatea cibernetică e parte a securității naționale"), salvează în:

```
~/.claude/memory/legal-facts/ccr-{N}-{YYYY}.md
```

Acestea sunt accesibile din **orice** proiect.

## Trigger-uri automate

Aplică acest skill **proactiv** când:
- Faci `web_fetch` pe pagină juridică (ccr.ro, legislatie.just.ro, lege5.ro, hudoc.echr.coe.int, eur-lex.europa.eu)
- Output `web_fetch` > 50K caractere
- Începi un proiect juridic nou (verifică research existent)
- Identifici un fact juridic important în context (citează decizie, articol, doctrină)
- Te apropii de context compaction (se vede în UI sau prin lungimea conversației)
