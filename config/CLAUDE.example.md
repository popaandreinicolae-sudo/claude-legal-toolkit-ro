# CLAUDE.md (sablon), configurare globala Claude Code pentru redactare juridica/academica

> Copiaza in `~/.claude/CLAUDE.md` si completeaza blocul de identitate cu datele tale.
> Acest fisier este "constitutia" proiectelor tale: reguli de stil, workflow obligatoriu si
> sistemul anti-halucinare pe care agentul le respecta la fiecare sarcina.

<identitate>
Completeaza: nume, profesie, roluri, domenii de expertiza, teme de cercetare.
Exemplu: "Jurist, doctorand Drept, consilier juridic. Teme: [...]"
</identitate>

<workflow_obligatoriu>
La orice sarcina de redactare juridica/academica, urmeaza secventa Research, Plan, Implement, Review:

1. RESEARCH, inainte de a scrie: verifica sursele prin MCP-urile juridice (legal-verificator-ro, hudoc, eurlex, semantic-scholar); aplica skill-ul de anti-halucinare.
2. PLAN, inainte de implementare: schiteaza structura argumentativa, identifica normele ancorate, cere confirmarea utilizatorului inainte de redactare lunga.
3. IMPLEMENT: aplica skill-urile de analiza si de anti-AI-tone la text peste 500 de cuvinte, plus formatul de citare.
4. REVIEW, inainte de livrare: invoca subagentii de audit (anti-ai-tone-reviewer, juridic-style-reviewer) si trece prin quality-gate.
</workflow_obligatoriu>

<reguli_de_stil_obligatorii>
Aplica la orice output text peste 500 de cuvinte non-cod:

1. Apozitii cu virgule, nu cu liniute.
2. Maximum o liniuta de dialog per pagina, doar la atribuire citat sau interval.
3. Zero constructii de tip eticheta-doua-puncte in corpul textului.
4. Zero paralelism negativ ("Nu X, ci Y").
5. Hedging redus, maximum trei per pagina.
6. Diateza activa implicit; pasivul academic doar la citari verbatim.
7. Zero truisme de deschidere si zero artefacte de chatbot.
8. Variaza lungimea propozitiilor.
9. Pentru referinte juridice, marcheaza [NEVERIFICAT] daca nu ai sursa confirmata.
10. Numarul de elemente din enumerari il decide continutul, nu un tipar fix.
</reguli_de_stil_obligatorii>

<sistem_anti_halucinare>
Strat determinist prin hook-uri PostToolUse (cod care nu poate halucina):

1. citation_guard.py, verifica fiecare citare juridica prin surse primare si tabelul reference_names.json.
2. phantom_source_guard.py, semnaleaza sursele-fantoma si atribuirile fara identificator.
3. numeric_consistency_guard.py, prinde erorile de ordin de marime si pragurile contradictorii.
4. ai_tone_hook.py, scor de naturalete pentru fiecare text scris.

Precedenta anti-contradictie: sursa primara MCP > indiciu de hook > memoria modelului.
Hook-urile sunt CONSULTATIVE, nu blocheaza singure; verificarea de retea se face la quality-gate.
Comutator: ANTIHALU_OFF=1 dezactiveaza stratul factual.

Detalii in hooks/SYSTEM_CONTRACT.md.
</sistem_anti_halucinare>
