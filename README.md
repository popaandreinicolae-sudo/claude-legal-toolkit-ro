# Claude Legal & Academic Toolkit (RO)

Set de skill-uri, subagenti, hook-uri si servere MCP pentru Claude Code si Claude Desktop,
construit pentru redactare juridica si academica in limba romana, cu accent pe **anti-halucinare**
(verificarea citarilor prin surse primare) si **anti-AI-tone** (text care nu suna a robot).

Poti clona repo-ul, completa configurarile-sablon cu propriile tale credentiale si folosi acelasi
sistem pe care il folosesc eu zilnic.

## Ce contine

| Folder | Continut |
|---|---|
| `skills/` | Skill-uri Claude. Cele proprii: anti-halucinare (document si energetic), `constitutional-law-ro`, `cyber-law-ro`, `task-contract`, `source-pack-grounding`, `ub-drept-citation`, `verificare-citari-gate`. Plus skill-uri third-party incluse pentru comoditate (vezi ATRIBUIRI). |
| `agents/` | Subagenti de audit read-only: `citation-verifier`, `fact-checker-document`, `fact-checker-energetic`, `juridic-style-reviewer`, `anti-ai-tone-reviewer`, `hallucination-redteam`, `quality-gate`, `source-pack-builder`, `legislatie-watcher`, plus o colectie generica de agenti specializati. |
| `hooks/` | Hook-uri Python deterministe (anti-halucinare factuala + anti-AI-tone): `citation_guard.py`, `phantom_source_guard.py`, `numeric_consistency_guard.py`, `ai_tone_hook.py` s.a. Plus `SYSTEM_CONTRACT.md` si `reference_names.json`. |
| `mcp-servers/` | Servere MCP: `legal-verificator-ro` (CCR + legislatie RO), `legal-research-mcp` (eurlex, hudoc, zotero, doctrine-verifier), `semantic-scholar`, `anti-ai-tone`, `cognee`. |
| `config/` | Sabloane `.example` pentru `settings.json`, `claude_desktop_config.json` si `CLAUDE.md`. |

## Securitate

Repo-ul **nu contine niciun secret**. Toate credentialele (parole lege5/6, cheie Zotero, endpoint-uri,
emailuri) au fost scoase si inlocuite cu substituenti in fisierele `.example`. Tu completezi propriile
valori local, in fisiere ignorate de git (`.gitignore` le blocheaza deja). Nu comite niciodata
`settings.json`, `claude_desktop_config.json`, `.env` sau `config.json` cu valori reale.

## Instalare

Vezi [INSTALL.md](INSTALL.md) pentru pasi detaliati (Windows). Pe scurt:

1. Cloneaza repo-ul.
2. Copiaza fisierele din `config/` fara sufixul `.example` si completeaza caile si credentialele.
3. Instaleaza dependintele Python si Node pentru serverele MCP pe care le vrei.
4. Reporneste Claude Desktop / Claude Code.

## Atribuiri

Skill-urile juridice romanesti, subagentii de audit, hook-urile si serverele MCP mici sunt munca mea
si sunt sub licenta MIT (vezi [LICENSE](LICENSE)). Componentele third-party incluse (skill-uri oficiale
Anthropic, colectia de agenti generici, skill-urile de tip humanizer) raman sub licentele lor originale;
pastreaza fisierele LICENSE aferente acolo unde exista.
