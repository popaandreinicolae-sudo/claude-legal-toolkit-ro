# Contract de sistem, straturile anti-halucinare

Acest document fixeaza cum lucreaza impreuna straturile, ca sa nu se contrazica si sa nu produca erori mai mari decat absenta lor. Citit de orice agent care intervine pe sistem.

## Principiul de precedenta (rezolva contradictiile)

1. Sursa primara prin MCP (legal-verificator-ro, hudoc, eurlex, doctrine-verifier) este autoritatea finala.
2. Indiciul determinist al unui hook este un semnal de verificat, nu un verdict.
3. Memoria modelului este ultima, niciodata peste o sursa primara.

Cand un hook contrazice o sursa primara confirmata, sursa primara castiga. Un semnal de hook NU justifica singur stergerea sau modificarea unei citari. Verifici prin sursa, apoi decizi.

## Caracterul hook-urilor: consultativ, niciodata automat

Hook-urile scriu doar avertismente (stderr), nu modifica niciun fisier si nu blocheaza scrierea. Marcheaza candidati de verificat. Modelul nu „corecteaza" pe baza unui hook fara a verifica intai prin sursa, ca sa nu strice o citare corecta pe baza unui fals-pozitiv.

## Doua viteze, ca sa nu incetineasca Cowork-ul

- Hook-uri PostToolUse (la fiecare scriere), mod LOCAL instant, fara retea: citation_guard, phantom_source_guard, numeric_consistency_guard. Folosesc doar reguli locale (reference_names.json, regex, cache). ~0,2s fiecare.
- Poarta de retea (on-demand sau la Stop), verificare completa prin just.ro si MCP-uri: quality_gate.py si subagentii citation-verifier / quality-gate. Aici se face validarea reala a fiecarei citari.

Verificarea de retea NU ruleaza pe fiecare scriere. Ruleaza cand ceri quality-gate sau la finalul sesiunii (sumar local rapid).

## Trei clase de severitate (anti-contradictie la poarta)

- BLOCANT (incredere mare): act UE abrogat (statut EUR-Lex), eroare de ordin de marime, prag contradictoriu, sursa-fantoma ca temei. Verdict NO-GO.
- DE ESCALADAT (incredere medie): citare negasita pe just.ro (poate fi un miss al bazei, nu neaparat inventata), transpunere context-gated. NU blocheaza automat; se confirma prin citation-verifier (mai multe surse) inainte de a deveni NO-GO. Asa o citare reala nu e stearsa pe fals-pozitiv.
- AVERTISMENT: denumiri depasite, liste incomplete, densitate de cifre, ton AI.

## Sursa unica de adevar

- hook_common.py, skip-patterns, kill-switch, citire fisiere, comportament uniform.
- reference_names.json, denumiri curente, acte UE abrogate, transpuneri. Toate straturile citesc de aici.

## Comutator de oprire

Variabila de mediu ANTIHALU_OFF=1 dezactiveaza instant toate hook-urile anti-halucinare (fara a le scoate din settings.json). Hook-urile anti-AI-tone existente raman active.

## Ordinea fluxului de redactare

task-contract (ce act) -> source-pack-grounding (surse reale) -> redactare (hook-uri locale advisory la fiecare scriere) -> quality-gate cu citation-verifier si red-team (verificare de retea) inainte de livrare. diff_versions intre versiuni. legislatie-watcher programat, separat.

## Ce NU face sistemul

Nu modifica documente automat. Nu blocheaza scrierea. Nu trimite nimic in cloud (verificarea RO e pe just.ro public). Nu inlocuieste lectura sursei primare de catre jurist.
