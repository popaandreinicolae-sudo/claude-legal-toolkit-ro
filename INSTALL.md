# Instalare (Windows)

## Cerinte

- Python 3.11+ (`python --version`)
- Node.js 18+ pentru serverele MCP scrise in TypeScript (`node --version`)
- Claude Desktop si/sau Claude Code

## 1. Cloneaza repo-ul

```powershell
git clone https://github.com/<USER>/<REPO>.git
cd <REPO>
```

## 2. Skill-uri, subagenti si hook-uri

Copiaza in folderul tau `~/.claude` (pe Windows: `C:\Users\<TU>\.claude`):

```powershell
Copy-Item -Recurse skills\*  "$env:USERPROFILE\.claude\skills\"
Copy-Item -Recurse agents\*  "$env:USERPROFILE\.claude\agents\"
Copy-Item -Recurse hooks     "$env:USERPROFILE\.claude\scripts"
```

## 3. Configurari (cu credentialele tale)

Copiaza sabloanele fara sufixul `.example` si completeaza-le:

```powershell
Copy-Item config\settings.example.json              "$env:USERPROFILE\.claude\settings.json"
Copy-Item config\CLAUDE.example.md                  "$env:USERPROFILE\.claude\CLAUDE.md"
Copy-Item config\claude_desktop_config.example.json "$env:APPDATA\Claude\claude_desktop_config.json"
```

In fiecare fisier inlocuieste `<REPO>` cu calea absoluta a repo-ului clonat si completeaza credentialele
(parole lege5/6, cheie Zotero etc.). **Nu comite aceste fisiere inapoi in git.**

## 4. Dependinte servere MCP

Python (pentru serverele `.py`):

```powershell
pip install mcp httpx beautifulsoup4 lxml python-docx chromadb
```

Node (pentru eurlex/hudoc/zotero):

```powershell
cd mcp-servers\legal-research-mcp
npm install
npm run build
```

## 5. Reporneste

Inchide si redeschide Claude Desktop / Claude Code. Verifica in setari ca serverele MCP apar conectate.

## Note

- `legal-verificator-ro` are nevoie de un cont valid lege5.ro / lege6.ro.
- Daca un server nu porneste, ruleaza-l manual din terminal ca sa vezi eroarea:
  `python mcp-servers\<server>\server.py`.
