#!/usr/bin/env python3
"""
PostToolUse hook pentru Claude Code.
Ruleaza detect_ai_tone.py automat pe orice .md/.docx/.txt scris de Claude.
Daca scor naturalete < THRESHOLD, scrie warning structurat in stderr (Claude vede in context urmator).

Citeste JSON din stdin (format Claude Code hooks API).
Iesire silentioasa daca:
- fisier non-text (cod sursa, json, etc.)
- fisier sub MIN_WORDS cuvinte
- scor >= THRESHOLD

Exit codes:
- 0 silentios: trece, fara mesaj
- 0 cu stderr: trece, dar Claude vede warning in context urmator
- niciodata 2 (nu blocam scrisul, doar avertizam)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

THRESHOLD = 70
MIN_WORDS = 200
SUPPORTED_EXT = {'.md', '.txt', '.docx'}
SKIP_PATTERNS = ('_archive', '_extracted_', 'node_modules', '.git', 'tool-results', 'memory')

SCRIPT_DIR = Path(__file__).resolve().parent
DETECT_SCRIPT = SCRIPT_DIR / 'detect_ai_tone.py'


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

    try:
        # .docx trebuie extras corect (paragrafe), nu citit ca octeti binari,
        # altfel numaratoarea de cuvinte e gresita si hook-ul sare peste .docx real.
        if p.suffix.lower() == '.docx':
            from docx import Document
            text = "\n".join(par.text for par in Document(str(p)).paragraphs)
        else:
            text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return 0
    if len(text.split()) < MIN_WORDS:
        return 0

    try:
        result = subprocess.run(
            [sys.executable, str(DETECT_SCRIPT), str(p), '--json'],
            capture_output=True,
            text=True,
            timeout=20,
            encoding='utf-8',
        )
    except Exception:
        return 0

    if not result.stdout:
        return 0

    try:
        data = json.loads(result.stdout)
    except Exception:
        return 0

    score = data.get('naturalness_score', 100)
    if score >= THRESHOLD:
        return 0

    metrics = data.get('metrics', {})
    issues = []
    if metrics.get('em_dash', {}).get('above_threshold'):
        issues.append(f"  - em-dash overuse: {metrics['em_dash']['per_page']:.1f}/pag (max 1.0)")
    if metrics.get('appositional_dashes', {}).get('above_threshold'):
        issues.append(f"  - apozitii cu liniute (RO): {metrics['appositional_dashes']['count']} aparitii (REGULA 2.2 DOOM 3)")
    if metrics.get('label_colon', {}).get('above_threshold'):
        issues.append(f"  - label-colon '**X:** desc': {metrics['label_colon']['count']} (REGULA 0)")
    if metrics.get('negative_parallelism', {}).get('above_threshold'):
        issues.append(f"  - paralelisme negative 'nu X, ci Y': {metrics['negative_parallelism']['count']}")
    if metrics.get('chatbot_total', 0) > 0:
        issues.append(f"  - chatbot artifacts: {metrics['chatbot_total']}")
    if metrics.get('truisms_total', 0) > 2:
        issues.append(f"  - truisme: {metrics['truisms_total']}")
    if metrics.get('copula_total', 0) > 3:
        issues.append(f"  - copula avoidance (reprezinta/constituie/etc): {metrics['copula_total']}")
    if metrics.get('ai_vocab_total', 0) > 5:
        issues.append(f"  - vocabular AI: {metrics['ai_vocab_total']} aparitii")

    msg = [
        f"[ANTI-AI-TONE HOOK] {p.name}: scor naturalete {score}/100 - {data.get('verdict')}",
    ]
    if issues:
        msg.append("Probleme detectate:")
        msg.extend(issues)
    msg.append(f"Reaplicare reguli din ~/.claude/skills/anti-ai-tone.md recomandata.")
    print('\n'.join(msg), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
