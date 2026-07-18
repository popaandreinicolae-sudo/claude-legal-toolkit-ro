# Web Fetch Deadlock Prevention — Cum să eviți cascada de erori

**Scop**: Eliminarea situației în care `web_fetch` salvează un fișier mare ca JSON single-line, iar apoi NICIUN tool (Read, Grep, Bash) nu îl mai poate procesa.

## Cascada de eroare identificată

```
web_fetch URL mare (>25K tokens) → salvează JSON single-line în tool-results/
  ↓
Read FAIL (limit pe linii ≠ caractere; 1 linie = 128K caractere = 25K tokens depășit)
  ↓
Grep FAIL (text JSON-encoded: "§ 42" → "Â§ 42" sau "§ 42", regex nu match)
  ↓
Bash FAIL (sandbox down sau "Workspace unavailable")
  ↓
DEADLOCK: fișier descărcat dar 100% inaccesibil
```

## Regula 1 — PREVENȚIE PRIMARĂ: nu lăsa overflow să se întâmple

### Înainte de `web_fetch`, întreabă:
- Pagina e probabil > 100K caractere? (orice pagină de știri completă, document juridic, listă dosare)
- DA → folosește URL-uri mai înguste:
  - **HUDOC**: `https://hudoc.echr.coe.int/app/conversion/docx/html?library=ECHR&id={id}` în loc de `/eng?i={id}` (pagina interactivă cu JS)
  - **CNCD**: `https://www.cncd.ro/criteriu/{slug}/?paged=1` (paginat) în loc de listing complet
  - **legislatie.just.ro**: `/Public/FormaPrintabila/{ID}` în loc de `/Public/DetaliiDocument/{ID}` (mai compact)
  - **EUR-Lex**: `?uri=CELEX:{id}` cu specific format `/HTML/` în loc de `/ALL/`

### Pentru pagini lungi cunoscute, folosește MCP-ul juridic
**NU** `web_fetch` direct la `legislatie.just.ro/Public/DetaliiDocument/200293` (138K) — folosește:
```
mcp__legal-verificator-ro__fetch_ccr_decision_text({ number: 136, year: 2018 })
```
care returnează direct text procesat și truncat la 30K caractere cu sumar inteligent.

## Regula 2 — DACĂ overflow s-a întâmplat deja

### Fișierul este la `tool-results/X.txt`. NU încerca să-l citești integral.

**Strategia 1 — Read cu offset/limit pe BYTES**: 
```
Read({ file_path: ..., offset: 0, limit: 200 })  // primele 200 LINII
```
**Atenție**: dacă fișierul e single-line (JSON array), `limit: 200` nu ajută. Verifică prima cu `wc -l` sau `Read({limit: 1})` să vezi dacă e multi-line.

### Strategia 2 — Grep direct pe pattern PROCESAT pentru JSON-escaping

JSON-encoded pattern-uri:
- `§` (§) → în JSON apare ca `"§"` sau `"§"` sau `"&sect;"` (HTML)
- `"` (ghilimele) → `\"`
- `\n` → `\\n`
- Diacritice `ț` → `ț` sau direct dacă encoding e UTF-8

**Pattern Grep adaptat**:
```
Grep pattern: "(?:§|\\\\u00a7|&sect;)\\s*42|paragraph.{0,5}42|par\\.\\s*42"
```
Adică: caut **toate** variantele encoding-ului pentru același caracter.

### Strategia 3 — Folosește Python local (NU bash sandbox) pentru parsare

Dacă ai acces la PowerShell/Bash local (NU sandbox-ul Anthropic), rulează:

```python
import json
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)
# data e array de obiecte sau obiect cu campul "text"
text = data[0].get("text", "") if isinstance(data, list) else data.get("text", "")
# Acum poti grep pe text decodat
import re
for m in re.finditer(r'(?i)paragraph\s*42|§\s*42', text):
    print(m.group(), text[max(0,m.start()-100):m.end()+200])
```

### Strategia 4 — Re-fetch cu URL mai îngust

Dacă URL-ul inițial era prea larg, refetch cu URL specific:
- HUDOC: în loc de pagina completă cauză, fetch direct la **paragraf specific** prin anchor: `?i=001-57772#para-42`
- CNCD: în loc de listing → fetch direct la **decizia specifică** dacă există ID
- Wikipedia: `?action=raw&section=2` pentru o singură secțiune

## Regula 3 — Anti-redirect cancelled

### Domenii cunoscute cu redirect chains problematice

| URL încercat | Redirect chain | URL care merge direct |
|---|---|---|
| `cncd.ro/criteriu/X` | → `www.cncd.ro/...` | `www.cncd.ro/criteriu/X/` (cu trailing slash) |
| `hotnews.ro/X` | → consent wall + tracking | foarte greu — folosește archive.org |
| `euractiv.ro/X` | → consent wall | archive.org sau `archive.ph` |
| `mediafax.ro/X` | direct | OK (1 redirect doar) |
| `agerpres.ro/X` | direct | OK |

### Strategia anti-redirect:

1. **Adaugă mereu `www.`** dacă URL-ul nu are deja
2. **Adaugă trailing slash** pentru paths
3. **Folosește HTTPS direct** (nu `http://` care va redirect la `https://`)
4. **Pentru site-uri cu consent wall**: folosește `https://archive.org/wayback/available?url={URL}` ca să găsești snapshot-ul, apoi fetch la URL-ul snapshot

## Regula 4 — Bash sandbox indisponibil ("Workspace unavailable")

### Diferențiere semantică

| Mesaj | Strategie |
|---|---|
| "VM guest is not connected" | Așteaptă 30-60s — se reconectează singur |
| "Workspace unavailable. Failed to start." | Sandbox MORT pe sesiune — NU mai retry, folosește alternativ |
| "EPERM: operation not permitted" | Permission issue local — verifică sandbox config |

### Alternative la bash sandbox

Pentru procesare fișiere, în lipsa bash:

1. **PowerShell local** (pe Windows host) — nu are limitarea sandbox-ului
2. **Python local** (`C:\Python314\python.exe`) — pentru JSON parsing, regex, etc.
3. **Read tool cu offset pe MULTI-LINE files** — verifică prima dacă e single-line
4. **Grep pe `tool-results/`** — funcționează dacă pattern-ul nu conține caractere JSON-escaped

## Regula 5 — Format fișier ideal pentru `web_fetch` mari

Când scrii cod care folosește `web_fetch` programatic (pentru un tool MCP), salvează:
- **NU**: `[{"text": "...", "url": "..."}]` (single-line JSON array)
- **DA**: text plain cu HTML strip
- **MAI BINE**: JSONL (un obiect per linie) cu metadata header

Pattern recomandat (pseudo):
```python
def save_fetch_result(result):
    out_path = f"research/fetch_{timestamp}.md"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(f"# {result['title']}\n\n")
        f.write(f"Source: {result['url']}\n")
        f.write(f"Fetched: {now}\n\n---\n\n")
        f.write(result['text_plain'])  # HTML stripped, multi-line
    return out_path
```

## Anti-pattern: NU FACE

- ❌ `web_fetch` pe pagină mare → continuare cu Read pe `tool-results/`
- ❌ Retry `web_fetch` pe același URL după token overflow (aceeași eroare)
- ❌ Bash retry de 5+ ori pe "Workspace unavailable"
- ❌ Grep cu patterns simple (`"42"`) pe JSON-encoded files
- ❌ `Read` cu `limit: 1` pe fișier 128K caractere (returnează tot fișierul)

## Trigger-uri automate

Aplică acest skill când:
- `web_fetch` returnează "Output exceeds maximum allowed tokens"
- `Read` returnează "File content (X tokens) exceeds maximum allowed (25000)"
- `Grep` returnează "No matches found" pe fișier care ar trebui să conțină textul
- Bash returnează "Workspace unavailable" sau "VM guest is not connected"
- Detectezi pattern-ul "tool-results/" în context (fișiere salvate de web_fetch)
- Faci research juridic exhaustiv (multiple surse, paginate, JSON arrays)
