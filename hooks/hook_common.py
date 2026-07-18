#!/usr/bin/env python3
"""
hook_common.py — nucleu comun pentru toate hook-urile anti-halucinare.

Sursa unica de adevar pentru: kill-switch global, skip-patterns, extensii suportate,
citirea textului (.docx/.md/.txt). Toate hook-urile importa de aici, ca sa nu divergheze
intre ele si sa nu produca semnale contradictorii.

Kill-switch: seteaza variabila de mediu ANTIHALU_OFF=1 ca sa dezactivezi instant toate
hook-urile anti-halucinare (fara a le scoate din settings.json). Hook-urile anti-AI-tone
existente NU sunt afectate.
"""

import json
import os
import sys
from pathlib import Path

SUPPORTED_EXT = {'.md', '.txt', '.docx'}

# Skip unic, partajat. Excludem zgomotul (scratch, cod, arhive, fisiere de proba)
# ca hook-urile sa NU ruleze pe scrierile intermediare ale modelului si pe non-livrabile.
SKIP_PATTERNS = (
    '_archive', '_extracted_', 'node_modules', '.git', 'tool-results', 'memory',
    '_session_audit', '_forensic_stage', '_forensic', '_test_corpus', '_payload',
    'proba_', 'qg_test', 'v_old', 'v_new', '_sp_test', '_watch_test',
    '.claude/scripts', '.claude\\scripts', 'dist/', 'dist\\', 'build/', '.cache',
    'source_pack.md', 'briefing_legislativ',
)


def kill_switch_on() -> bool:
    return os.environ.get('ANTIHALU_OFF', '') in ('1', 'true', 'yes', 'on')


def read_payload():
    """Citeste payload-ul JSON al hook-ului de pe stdin. None la eroare."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return None


def target_path(payload) -> Path | None:
    """Extrage calea fisierului tinta din payload, daca e relevant (eligibil)."""
    if not payload:
        return None
    ti = payload.get('tool_input') or {}
    fp = ti.get('file_path') or ''
    if not fp:
        return None
    p = Path(fp)
    if p.suffix.lower() not in SUPPORTED_EXT:
        return None
    norm = str(p).replace('\\', '/')
    if any(skip.replace('\\', '/') in norm for skip in SKIP_PATTERNS):
        return None
    if not p.exists():
        return None
    return p


def read_text(p: Path) -> str:
    if p.suffix.lower() == '.docx':
        try:
            from docx import Document
            return "\n".join(par.text for par in Document(str(p)).paragraphs if par.text.strip())
        except Exception:
            return ""
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ""


def eligible(payload, min_words: int):
    """Returneaza (path, text) daca fisierul e eligibil si destul de lung, altfel (None, None).

    Respecta kill-switch-ul. Folosit de toate hook-urile pentru un comportament uniform.
    """
    if kill_switch_on():
        return None, None
    p = target_path(payload)
    if p is None:
        return None, None
    text = read_text(p)
    if not text or len(text.split()) < min_words:
        return None, None
    return p, text
