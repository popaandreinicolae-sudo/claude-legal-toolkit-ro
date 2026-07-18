#!/usr/bin/env python3
"""
PostToolUse hook — garda numerica si consistenta interna (LOCAL, instant).

Semnaleaza, determinist si local: erori de ordin de marime ("X (anterior Y)" cu
raport 10/100/1000), praguri definite contradictoriu (% vs suma fixa), densitate de
cifre cu unitati fara marker de sursa.

Caracter CONSULTATIV. Contract I/O comun (hook_common). Exit 0 (fail-open). Kill-switch ANTIHALU_OFF=1.
"""

import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
import hook_common

MIN_WORDS = 80

UNIT_RE = r'(?:EUR|euro|lei|RON|USD|mil(?:ioane)?|mld|miliarde|%|mc|MWh|GWh|kWh|Gcal|km2|km|ha|MW|kV)'
SOURCE_MARKERS = ('conform', 'potrivit', 'sursa', 'sursă', 'în baza', 'in baza', '[neverificat]', 'date ', 'statistic', 'raport ', 'art.')


def _num(s: str) -> float:
    s = s.replace('.', '').replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except Exception:
        return 0.0


def detect(text: str) -> list:
    problems = []
    low = text.lower()
    patterns = [
        r'([\d][\d\.\s]{2,})\s*(?:EUR|euro|lei|RON)?\s*\(\s*anterior\s*([\d][\d\.\s]{2,})',
        r'de la\s*([\d][\d\.\s]{2,})\s*(?:EUR|euro|lei|RON)?\s*la\s*([\d][\d\.\s]{2,})',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            a, b = _num(m.group(1)), _num(m.group(2))
            if a > 0 and b > 0:
                ratio = max(a, b) / min(a, b)
                if abs(ratio - 10) < 0.05 or abs(ratio - 100) < 0.5 or abs(ratio - 1000) < 5:
                    problems.append(f"POSIBILA EROARE DE ORDIN DE MARIME (x{round(ratio)}): {m.group(0).strip()[:70]}")
    has_pct = re.search(r'(prag|plafon|semnificativ\w*|tranzacti\w+ semnificativ\w*)[^.\n]{0,60}\d+\s*%', text, re.IGNORECASE)
    has_fixed = re.search(r'(prag|plafon|semnificativ\w*)[^.\n]{0,60}\d[\d\.\s]{3,}\s*(?:EUR|euro|lei|RON)', text, re.IGNORECASE)
    if has_pct and has_fixed:
        problems.append("PRAG DEFINIT CONTRADICTORIU: acelasi prag exprimat si procentual (% din active) si ca suma fixa in EUR/lei. Verifica coerenta.")
    unsourced, examples = 0, []
    for m in re.finditer(r'(\d[\d\.,]{1,})\s*' + UNIT_RE, text):
        ctx = low[max(0, m.start() - 80):m.start() + 30]
        if any(mk in ctx for mk in SOURCE_MARKERS):
            continue
        unsourced += 1
        if len(examples) < 4:
            examples.append(m.group(0).strip()[:30])
    if unsourced >= 6:
        problems.append(f"DENSITATE DE CIFRE FARA SURSA: {unsourced} valori cu unitati fara marker de sursa (ex. {', '.join(examples)}). Ataseaza sursa sau marcheaza [NEVERIFICAT].")
    return problems


def main() -> int:
    payload = hook_common.read_payload()
    p, text = hook_common.eligible(payload, MIN_WORDS)
    if p is None:
        return 0
    try:
        problems = detect(text)
    except Exception:
        return 0
    if not problems:
        return 0
    lines = [f"[NUMERIC · advisory] {p.name}: {len(problems)} semnale de consistenta numerica."]
    for prob in problems[:6]:
        lines.append(f"  ? {prob}")
    lines.append("Consultativ. Verifica pragurile, ataseaza sursa fiecarei cifre sau marcheaza [NEVERIFICAT]. Confrunta definitia procentuala cu sumele fixe.")
    print('\n'.join(lines), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
