#!/usr/bin/env python3
"""
Stop hook.
La sfarsit de sesiune Claude Code:
1. Auditeaza fisierele .md/.docx scrise/editate in ultimele 60 minute in folder-ele de lucru
2. Genereaza raport in ~/.claude/scripts/_session_audit_<timestamp>.txt
3. Scrie summary scurt in stderr

Nu blocheaza nimic. Nu intrerupe nimic.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

THRESHOLD = 70
DETECT_SCRIPT = Path(__file__).resolve().parent / 'detect_ai_tone.py'
RECENT_WINDOW_SEC = 60 * 60
WATCH_DIRS = [
    Path.home() / 'Downloads',
    Path('%USERPROFILE%/OneDrive/Documents/Claude/Projects'),
]
SKIP_PATTERNS = ('_archive', '_extracted_', 'node_modules', '.git', 'tool-results')


def find_recent_files() -> list:
    cutoff = time.time() - RECENT_WINDOW_SEC
    results = []
    for d in WATCH_DIRS:
        if not d.exists():
            continue
        try:
            for ext in ('*.md', '*.txt', '*.docx'):
                for p in d.rglob(ext):
                    try:
                        if p.stat().st_mtime < cutoff:
                            continue
                        if any(skip in str(p).replace('\\', '/') for skip in SKIP_PATTERNS):
                            continue
                        if p.stat().st_size > 5_000_000:
                            continue
                        results.append(p)
                    except OSError:
                        continue
        except OSError:
            continue
    return results[:50]


def audit_file(path: Path) -> dict | None:
    try:
        result = subprocess.run(
            [sys.executable, str(DETECT_SCRIPT), str(path), '--json'],
            capture_output=True,
            text=True,
            timeout=15,
            encoding='utf-8',
        )
        if not result.stdout:
            return None
        return json.loads(result.stdout)
    except Exception:
        return None


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    files = find_recent_files()
    if not files:
        return 0

    flagged = []
    natural = []
    for p in files:
        data = audit_file(p)
        if not data:
            continue
        score = data.get('naturalness_score', 100)
        if score < THRESHOLD:
            flagged.append((p, score, data.get('verdict', '?')))
        else:
            natural.append((p, score))

    if not flagged and not natural:
        return 0

    # Log rotativ unic (nu un fisier nou per oprire). Pastram ultimele ~500 linii.
    report_path = Path(__file__).resolve().parent / 'session_audit.log'
    lines = [
        '═══════════════════════════════════════════════════',
        f'AUDIT FINAL SESIUNE — {time.strftime("%Y-%m-%d %H:%M:%S")}',
        '═══════════════════════════════════════════════════',
        f'Fisiere auditate: {len(files)}',
        f'Sub prag ({THRESHOLD}/100): {len(flagged)}',
        f'OK: {len(natural)}',
        '',
    ]
    if flagged:
        lines.append('FLAG (necesita revizuire):')
        for p, score, verdict in sorted(flagged, key=lambda x: x[1]):
            lines.append(f'  [{score:3d}/100] {verdict:10s} {p}')
        lines.append('')
    if natural:
        lines.append('OK:')
        for p, score in sorted(natural, key=lambda x: -x[1])[:10]:
            lines.append(f'  [{score:3d}/100] {p}')

    report_text = '\n'.join(lines)
    try:
        prev = ''
        if report_path.exists():
            prev = report_path.read_text(encoding='utf-8', errors='ignore')
        combined = (report_text + '\n\n' + prev).splitlines()[:500]
        report_path.write_text('\n'.join(combined), encoding='utf-8')
    except OSError:
        pass

    summary = f'[SESSION AUDIT] {len(files)} fisiere verificate, {len(flagged)} sub prag {THRESHOLD}/100. Raport: {report_path.name}'
    print(summary, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
