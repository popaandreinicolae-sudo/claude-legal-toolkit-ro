#!/usr/bin/env python3
"""
PostToolUse hook — semnalare rapida a citarilor juridice (mod LOCAL, fara retea).

Ruleaza la fiecare Write/Edit pe documente .md/.txt/.docx. Pentru a NU incetini
Cowork-ul, face DOAR verificari locale instant (acte UE abrogate din lista de
referinta, denumiri depasite, transpuneri NIS context-gated, plus citarile deja
in cache). NU apeleaza just.ro pe fiecare scriere. Verificarea de retea a fiecarei
citari se face la quality-gate / la cerere prin subagentul citation-verifier.

Caracter pur CONSULTATIV: semnaleaza candidati de verificat, nu da verdicte si nu
cere modificari. Modelul verifica prin sursa primara inainte de a schimba ceva, ca
sa nu „corecteze" o citare corecta pe baza unui fals-pozitiv.

Contract I/O comun (hook_common). Exit 0 mereu (fail-open). Kill-switch: ANTIHALU_OFF=1.
"""

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import hook_common

MIN_WORDS = 40


def main() -> int:
    payload = hook_common.read_payload()
    p, text = hook_common.eligible(payload, MIN_WORDS)
    if p is None:
        return 0

    try:
        import citation_core
        report = citation_core.verify_text(text, cap=40, network=False)
    except Exception:
        return 0  # fail-open

    problems = report.get('problems', [])
    # Tace pe documente curate. Vorbeste doar cand are un semnal local concret
    # (act abrogat, denumire depasita, transpunere context-gated). Reminderul de
    # verificare prin sursa la livrare traieste in skill-uri, nu pe fiecare scriere.
    if not problems:
        return 0

    total = report.get('total', 0)
    lines = [f"[CITATION-GUARD · advisory] {p.name}: {len(problems)} semnale locale ({total} citari in document)."]
    for prob in problems[:6]:
        lines.append(f"  ? {prob}")
    lines.append("Consultativ. Verifica prin sursa primara (citation-verifier / quality-gate) INAINTE de a modifica; nu sterge o citare doar pe baza acestui semnal.")
    print('\n'.join(lines), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
