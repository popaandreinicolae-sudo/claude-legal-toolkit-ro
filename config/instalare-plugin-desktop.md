# Instalarea toolkit-ului în Claude Desktop și Cowork

Claude Desktop nu citește `~/.claude`. Skill-urile, subagenții și hook-urile de acolo
rămân pe suprafața Claude Code dacă nu le împachetăm. Pachetul din `plugin/` le duce
dincolo.

## Ce conține pachetul

Se generează cu `tools/build_plugin.py`, din configurația instalată efectiv, deci nu
există o a doua listă de întreținut. `sync-claude.ps1` îl reconstruiește la fiecare
rulare.

| | |
|---|---|
| skill-uri | 14, printre care `docx-track-changes`, `docx-livrare-check`, `ub-drept-citation`, `verificare-citari-gate` |
| subagenți | 10, printre care `quality-gate`, `citation-verifier`, `anti-ai-tone-reviewer` |
| hook-uri | 9 scripturi pe 4 evenimente, cu tot stratul determinist anti-halucinare |

Directorul `plugin/` este artefact generat. Nu îl edita de mână, se rescrie la
următorul build.

## Cum se instalează

Claude Desktop, Settings, Customize, **Plugins**, butonul **Add**. Meniul oferă trei
variante, dintre care ne interesează două.

Calea scurtă trece prin **Upload plugin**, care cere un fișier. Arhiva se construiește
singură la fiecare build:

```
C:\Users\Adrian Zamfir\claude-legal-toolkit-ro\dist\toolkit-juridic-ro.zip
```

Rădăcina arhivei este chiar rădăcina plugin-ului, cu `.claude-plugin`, `skills`,
`agents` și `hooks` la primul nivel, așa cum arată un director de plugin pe disc.

Calea a doua trece prin **Add marketplace**, apoi **Add from a repository**. Câmpul
acceptă doar `owner/repo` de pe GitHub sau un URL de git, deci nu primește o cale locală.
Repo-ul privat pregătit pentru asta este:

```
adrianmzamfir-glitch/toolkit-juridic-roAZ
```

Manifestul stă în `.claude-plugin/marketplace.json` de la rădăcina lui, iar plugin-ul se
numește `toolkit-juridic-ro`. Avantajul acestei căi este actualizarea, un singur Sync
recitește repo-ul, în loc să ceară o arhivă nouă.

Repo-ul e legat local ca al doilea remote, `personal`. `origin` rămâne repo-ul original
al lui Andrei Nicolae Popa, pentru actualizări de la sursă.

Dialogul de încărcare avertizează că plugin-urile încărcate nu sunt controlate de
Anthropic. Firesc, este codul tău, construit din configurația ta.

Aplicația confirmă în jurnale ce a găsit, prin `NativeMarketplaceReader` și
`LocalPluginsReader`. Înainte de instalare ambele raportau zero.

## Ce se schimbă după instalare

În Cowork ajung skill-urile și subagenții. Hook-urile depind de cât din mecanismul
Claude Code preia mașina virtuală, iar asta se vede abia la rulare. Scripturile sunt
scrise fail-open, deci un hook care nu poate porni raportează curat și nu blochează
sesiunea.

Căile din hook-uri au fost rescrise pe `${CLAUDE_PLUGIN_ROOT}`, fiindcă în mașina
virtuală căile absolute de Windows nu există. Interpretorul se alege la rulare, prin
`hooks/ruleaza.sh`, care încearcă `python3`, apoi `python`, apoi `py`. Același pachet
merge și pe Windows și pe Linux.

## Ce NU se instalează în Claude Code

Pachetul e destinat celeilalte suprafețe. Aici ai deja aceleași skill-uri în
`~/.claude/skills` și aceleași hook-uri în `settings.json`. Instalarea plugin-ului și
pe suprafața asta le-ar dubla, iar hook-urile ar rula de două ori pe fiecare scriere.

## Actualizare

Când schimbi ceva în configurația de aici, rulează `sync-claude.ps1`, care reconstruiește
pachetul, apoi comite și împinge în repo.

În Desktop, ordinea contează și nu e cea evidentă.

Butonul **Update** de pe pagina plugin-ului compară cu indexul de pe serverul Anthropic,
iar acela recitește repo-ul de pe GitHub numai când e împins să o facă. Sincronizarea
locală rulează la fiecare 10 minute, dar raportează „Delta: 0 to download", fiindcă
întreabă un index încă nesincronizat. Rezultatul este un buton Update inactiv, deși
versiunea nouă există pe GitHub.

Soluția este să re-adaugi marketplace-ul, prin Add, Add marketplace, Add from a
repository, cu aceeași adresă. Nu se creează un duplicat, se declanșează
`addMarketplaceViaRemote`, adică o citire proaspătă. Abia apoi butonul Update se
activează.

Versiunea pachetului se calculează din numărul de commituri, `1.0.<n>`, tocmai ca fiecare
push să produca una nouă. Un numar fix ar lasa butonul Update inactiv pentru totdeauna.
