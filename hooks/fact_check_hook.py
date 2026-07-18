#!/usr/bin/env python3
"""
PostToolUse hook pentru fact-check documente profesionale.
Ruleaza pe .docx, .md, .txt cu peste 500 cuvinte.
Detecteaza pattern-uri de halucinare (RADET, BCR fabricat, Trust Fund inventat, capitole goale).
Scrie warning in stderr cand detecteaza probleme critice. Nu blocheaza.
"""

import json
import os
import re
import sys
from pathlib import Path

MIN_WORDS = 500
SUPPORTED_EXT = {'.md', '.txt', '.docx'}
SKIP_PATTERNS = ('_archive', '_extracted_', 'node_modules', '.git', 'tool-results', 'memory', '_session_audit')


def extract_text_from_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""


def detect_hallucinations(text: str) -> tuple[list[str], list[str]]:
    critical = []
    major = []

    chapter_titles = re.findall(
        r'^(CAPITOLUL\s+[IVXLCM]+\.\s*[A-ZĂÂÎȘȚ][^\n]{3,80})',
        text,
        re.MULTILINE,
    )
    for ch_title in chapter_titles:
        idx = text.find(ch_title) + len(ch_title)
        next_500 = text[idx:idx + 500].strip()
        if len(next_500) < 80:
            critical.append(f"CAPITOL POTENTIAL GOL: {ch_title[:80]}")

    if 'RADET' in text and 'CMTEB' not in text:
        critical.append("DENUMIRE DEPASITA: RADET fara mentionarea CMTEB (din 1 dec 2019)")
    if re.search(r'\bE-?Distrib[uu]tie\b', text) or 'Enel Distributie' in text:
        critical.append("DENUMIRE DEPASITA: E-Distributie. Foloseste Retele Electrice Romania S.A.")

    tf_matches = re.findall(r'Trust\s+Fund[^.]*?(\d+(?:[\.,]\d+)?)\s*milioane?\s*EUR', text, re.IGNORECASE)
    if tf_matches:
        critical.append(f"SUSPICIUNE TRUST FUND INVENTAT: {tf_matches[:3]}")

    bcr_matches = re.findall(r'BCR\s*(?:estimat\s+)?(?:de\s+)?(\d+[\.,]\d+)', text, re.IGNORECASE)
    if bcr_matches:
        major.append(f"BCR fara calcul: {bcr_matches[:3]}")

    if re.search(r'Scenariu(l)?\s+(BAU|Strategy|Ambitious)', text, re.IGNORECASE):
        if not re.search(r'\[SCENARIU', text):
            major.append("Scenarii BAU/Strategy/Ambitious fara marcaj [SCENARIU, ipoteza X]")

    suspicious_round = re.findall(r'peste\s+(\d{2,4})\s*milioane?\s+EUR', text, re.IGNORECASE)
    if len(suspicious_round) > 2:
        major.append(f"Cifre rotunde 'peste X milioane EUR' fara sursa: {len(suspicious_round)} aparitii")

    return critical, major


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get('tool_input') or {}
    file_path = tool_input.get('file_path') or ''
    if not file_path:
        return 0

    p = Path(file_path)
    if p.suffix.lower() not in SUPPORTED_EXT:
        return 0
    if any(skip in str(p).replace('\\', '/') for skip in SKIP_PATTERNS):
        return 0
    if not p.exists():
        return 0

    if p.suffix.lower() == '.docx':
        text = extract_text_from_docx(p)
    else:
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return 0

    if len(text.split()) < MIN_WORDS:
        return 0

    critical, major = detect_hallucinations(text)

    if not critical and not major:
        return 0

    msg_lines = [f"[FACT-CHECK HOOK] {p.name}: detectate {len(critical)} critice, {len(major)} majore"]
    for c in critical[:5]:
        msg_lines.append(f"  CRITICAL: {c}")
    for m in major[:5]:
        msg_lines.append(f"  MAJOR: {m}")
    msg_lines.append("Aplica skill anti-hallucination-document. Pentru detalii: invoca subagent fact-checker-document.")

    print('\n'.join(msg_lines), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
