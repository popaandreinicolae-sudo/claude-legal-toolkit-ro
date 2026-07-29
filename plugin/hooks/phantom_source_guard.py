#!/usr/bin/env python3
"""
PostToolUse hook — detector de surse-fantoma si umplutura fabricata (LOCAL, instant).

Semnaleaza, determinist si local (fara retea): etichete de sursa neverificabile
folosite ca sursa (Google Drive, zf.ro, studiu confidential), atribuiri editoriale
fara DOI/ISBN, si liste anuntate dar incomplete ("patru metode", doar doua listate).

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

PHANTOM_SOURCE_LABELS = [
    'google drive', 'gdrive', 'zf.ro', 'economedia.ro', 'senat.ro', 'profit.ro',
    'hotnews', 'wikipedia', 'scribd', 'document intern', 'sursa interna',
]
RO_NUM_WORDS = {
    'doua': 2, 'două': 2, 'trei': 3, 'patru': 4, 'cinci': 5, 'sase': 6, 'șase': 6,
    'sapte': 7, 'șapte': 7, 'opt': 8, 'noua': 9, 'nouă': 9, 'zece': 10,
}


def detect(text: str) -> list:
    problems = []
    low = text.lower()
    for label in PHANTOM_SOURCE_LABELS:
        if label in low:
            idx = low.find(label)
            ctx = text[max(0, idx - 40):idx + 40].replace('\n', ' ')
            problems.append(f"SURSA-FANTOMA: '{label}' folosit ca sursa ({ctx.strip()[:70]})")
    for m in re.finditer(r'(studiu(l)?\s+(confiden[tț]ial|nepublicat|intern)[^.\n]{0,60})', text, re.IGNORECASE):
        problems.append(f"SURSA NEVERIFICABILA: {m.group(1).strip()[:70]}")
    for m in re.finditer(r'([A-ZȘȚĂÂÎ][a-zșțăâî]+(?:\s*&\s*[A-ZȘȚĂÂÎ][a-zșțăâî]+)?\s*\(?\d{4}\)?[^.\n]{0,80}(edi[tț]ia|vol\.|volumul|Journal|Review|Transactions)[^.\n]{0,40})', text):
        seg = m.group(1)
        if not re.search(r'(doi|isbn|issn)', seg, re.IGNORECASE):
            problems.append(f"ATRIBUIRE EDITORIALA fara DOI/ISBN (verifica): {seg.strip()[:75]}")
    for m in re.finditer(r'\b(cele|urmatoarele|următoarele|patru|cinci|sase|șase|sapte|șapte|opt|noua|nouă|zece|trei|doua|două|\d+)\s+(metode|anexe|capitole|criterii|principii|conditii|condiții|masuri|măsuri|etape|sectiuni|secțiuni|elemente|puncte)\b', text, re.IGNORECASE):
        word = m.group(1).lower()
        n = RO_NUM_WORDS.get(word) or (int(word) if word.isdigit() else None)
        if not n or n > 12:
            continue
        noun = m.group(2).lower()
        after = text[m.end():m.end() + 2500]
        items = len(re.findall(r'(?m)^\s*(?:[-*•]|\(?[a-z]\)|\d+[.)])\s+', after))
        if 0 < items < n:
            problems.append(f"INCOMPLETITUDINE: anunta {n} {noun} dar lista contine {items} elemente")
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
    lines = [f"[PHANTOM-SOURCE · advisory] {p.name}: {len(problems)} semnale de sursa-fantoma / umplutura."]
    for prob in problems[:8]:
        lines.append(f"  ? {prob}")
    lines.append("Consultativ. Inlocuieste sursele neverificabile cu surse primare reale, completeaza listele anuntate, verifica atribuirile (DOI/ISBN) prin doctrine-verifier.")
    print('\n'.join(lines), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
