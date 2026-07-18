---
name: mcp-fallback-strategy
description: |
  Decision tree pentru cazul când MCP-urile juridice eșuează. Aplică automat când un MCP returnează timeout, 5xx sau zero rezultate. Folosește fallback chains pentru CCR, HUDOC, EUR-Lex, doctrină.
---

# MCP Fallback Strategy

Scop. Prevenirea blocajelor de cercetare juridică atunci când MCP-urile (`legal-verificator-ro`, `hudoc`, `eurlex`, `doctrine-verifier`) returnează timeout, eroare 5xx sau zero rezultate.

## Regula 1. Dacă un MCP eșuează, NU repeta același apel

Dacă `legal-verificator-ro__search_ccr_decision` returnează timeout sau eroare, nu chema același tool a doua oară. Treci direct la fallback.

## Regula 2. Detectare rapidă a eșecului

| Simptom | Acțiune imediată |
|---|---|
| Timeout peste 60 secunde pe orice MCP juridic | Trec la WebSearch plus URL direct |
| Răspuns `{"results": [], "total": 0}` pe HUDOC sau EUR-Lex pentru query specific | Construct URL direct |
| HTTP 502, 503 sau 504 pe `legislatie.just.ro` | Folosesc `lege5_search` (alt MCP tool, sursă diferită) |
| HTTP 404 pe URL hardcodat (de ex. ccr.ro PDF) | Caut URL real prin WebSearch |
| `{"upstream_unavailable": true}` în răspunsul MCP | Sursă alternativă imediat |

## Regula 3. Fallback chains pe sursă

### CCR (decizii Curtea Constituțională)

1. Primary. `legal-verificator-ro__search_ccr_decision` plus `fetch_ccr_decision_text`
2. Fallback A. `legal-verificator-ro__lege5_search` cu `category: "ccr"`
3. Fallback B. `WebSearch` cu query: `"Decizia CCR nr. {N}/{YYYY}" site:ccr.ro OR site:legislatie.just.ro OR site:lege5.ro`
4. Fallback C. `web_fetch` la URL-uri reale CCR (formate cunoscute):
   - `https://www.ccr.ro/decizia-{N}/` (slug bazat pe titlu)
   - `https://www.ccr.ro/wp-content/uploads/{YYYY}/{MM}/Decizie_{N}_{YYYY}.pdf`, variabil
   - Cel mai sigur. Caută mai întâi pagina HTML pe ccr.ro prin WebSearch, apoi descarcă PDF-ul de acolo
5. Fallback D. `WebSearch` la articole juridice (juridice.ro, universuljuridic.ro, hotararicedo.ro), citate frecvent

### Legislație RO

1. Primary. `legal-verificator-ro__search_legislation` plus `fetch_article_text`
2. Fallback A. `legal-verificator-ro__lege5_search` cu `category: "legislatie"`
3. Fallback B. `WebSearch` plus `web_fetch` la `legislatie.just.ro/Public/DetaliiDocumentAfis/{ID}`
4. Fallback C. `web_fetch` la `lege5.ro/Gratuit/...`

### Jurisprudență CEDO (HUDOC)

1. Primary cu app no. `hudoc__hudoc_get_judgment` cu `application_number: "11798/85"` (format exact cu /)
2. Primary cu item ID. `hudoc__hudoc_get_judgment` cu `item_id: "001-57772"`
3. Fallback A. `WebSearch` cu query `"Castells v. Spain" site:hudoc.echr.coe.int` pentru a găsi item ID
4. Fallback B. URL corect (post-fix #12, aprilie 2026):
   - `https://hudoc.echr.coe.int/app/conversion/docx/html?library=ECHR&id=001-XXXXXX&filename=case.docx` (funcțional)
   - NU `https://hudoc.echr.coe.int/app/conversion/docx/html/body/{id}` (returnează 404 din 2025 încolo)
   - Pagina interactivă cu JS: `https://hudoc.echr.coe.int/eng?i=001-XXXXXX` (necesită browser, NU axios)
5. Reguli pentru construct query HUDOC:
   - Nu trimite "Castells Spain" ca freeText, motorul caută în titluri, nu în nume
   - Folosește `appno:"11798/85"` (cu ghilimele și slash)
   - Sau caută numele cauzei: `"CASE OF CASTELLS v. SPAIN"`

### Jurisprudență CJUE (EUR-Lex)

1. Primary cu CELEX. `eurlex__eurlex_get_document` cu `celex_number: "62014CJ0083"`
2. Primary cu case number. `eurlex__eurlex_search_caselaw` cu `case_number: "C-83/14"` (versiunea fix-uită caută CELEX automat)
3. Conversie manuală case în CELEX:
   - Format: `6{YYYY}{TIP}{NNNN}` unde TIP poate fi CJ (judgment), CC (AG opinion), CO (order)
   - Exemplu: C-83/14 încearcă `62014CJ0083`, `62014CC0083`, `62014CO0083`
4. Fallback A. `WebSearch` cu `"CHEZ Razpredelenie" C-83/14 site:eur-lex.europa.eu`
5. Fallback B. `web_fetch` la `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62014CJ0083`

### Doctrină românească

1. Primary. `doctrine-verifier__verify_citation` (probabil va da NOT_FOUND, este normal)
2. Fallback obligatoriu. `WebSearch` pe `libris.ro`, `esteto.ro`, `cartea.ro`, `bibnat.ro`
3. Citare ISBN. WebSearch direct cu titlul exact plus numele autorului, librăriile au ISBN-ul în URL sau meta
4. Editurile C.H. Beck, Hamangiu, Universul Juridic au site-urile lor cu căutare proprie

## Regula 4. web_fetch token overflow (output peste 25K tokens)

Dacă `web_fetch` returnează „Output exceeds maximum allowed tokens" și salvează la `tool-results/...`:

1. NU încerca să citești tot fișierul cu Read.
2. Folosește `Bash` sau `PowerShell` cu `grep` sau `Select-String` cu pattern țintit:

   ```bash
   grep -A 5 -B 2 "termenii_relevanti" /path/to/saved.txt
   ```

3. Sau Python:

   ```python
   import re
   with open(path) as f: content = f.read()
   for match in re.finditer(r'(?i).{0,200}\b(decizie|hotarare).{0,500}', content):
       print(match.group())
   ```

4. Niciodată nu cere `web_fetch` cu același URL a doua oară pentru a obține mai mult. Folosește fișierul salvat.

## Regula 5. Persistare research între sesiuni

Vezi skill `research-context-persist.md`. Pe scurt, salvează findings în `~/.claude/projects/{slug}/memory/research-{topic}.md` cât mai repede.

## Regula 6. Bash sandbox VM disconnect

Dacă apar „VM guest is not connected" repetat (eroare infrastructură):

1. Așteaptă 30 până la 60 de secunde, sandbox-ul se reconectează singur.
2. Nu chema bash de 5 ori sau mai mult consecutiv pe aceeași eroare. Folosește alt tool (Read, Edit, Grep) între timp.
3. Dacă totuși blocat peste 2 minute, raportează utilizatorului și sugerează restart Claude Code.

## Regula 7. Pre-install pachete Node sau Python

Pentru generare DOCX sau PDF, pachete frecvente:

| Limbaj | Pachet | Verificare rapidă |
|---|---|---|
| Python | `python-docx` | `python -c "import docx"` |
| Python | `httpx` | `python -c "import httpx"` |
| Node | `docx` | `node -e "require('docx')"` |
| Node | `axios` | `node -e "require('axios')"` |

Dacă lipsește, instalează înainte de a încerca să-l folosești:

```bash
pip install python-docx httpx beautifulsoup4 lxml
npm install docx axios cheerio
```

## Regula 8. Smart quotes versus ASCII quotes

În cod (Python, JavaScript, JSON), folosește mereu ghilimele ASCII drepte: `"` și `'`. Smart quotes (`"` `"` `'` `'`) cauzează SyntaxError. Când copiezi text dintr-un mesaj utilizator sau markdown, normalizează:

- `"` `"` în `"`
- `'` `'` în `'`
- `–` în `-`
- `…` în `...`

## Trigger-uri automate

Aplică acest skill automat când:

- Apare cuvântul „MCP", „timeout", „502", „504", „not found", „CCR", „HUDOC", „EUR-Lex", „CEDO" în context
- Un tool MCP returnează `error`, `[]` sau timeout
- Înainte de orice cercetare juridică complexă (declanșare proactivă)
