#!/usr/bin/env python3
"""
UserPromptSubmit hook.
Injecteaza in context un reminder anti-AI tone la promptul utilizatorului.
Reminderul apare in <system> tag, nu in promptul vizibil.

Hook este idempotent: nu injecteaza daca utilizatorul a inceput cu /, este meta-comanda.
Skip pe prompt-uri scurte (sub 20 caractere) ca sa nu deranjeze conversatii rapide.
"""
import json
import sys

REMINDER_RO = """[CONTEXT STIL — anti-AI tone v2.1, aplicat la text peste 500 cuvinte non-cod]
Apozitii cu virgule, nu cu liniute (DOOM 3). Zero label-colon "**X:** desc". Zero "Nu X, ci Y". Diateza activa implicit. Zero hedging excesiv. Zero truisme. Zero copula avoidance (X este Y, nu X reprezinta/constituie Y). Zero chatbot artifacts. Persoana I plural la opinie proprie. Anti-AI tone aplicat AUTOMAT, fara sa fie cerut."""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    prompt = (payload.get('prompt') or '').strip()

    if not prompt:
        return 0
    if prompt.startswith('/'):
        return 0
    if len(prompt) < 20:
        return 0
    if prompt.startswith('!') or prompt.startswith('#'):
        return 0

    print(REMINDER_RO)
    return 0


if __name__ == '__main__':
    sys.exit(main())
