#!/usr/bin/env python3
"""
Custom Status Line pentru Claude Code.
Afiseaza:
- Model curent
- Ultimul scor anti-AI tone obtinut (din session_audit)
- Numar MCP-uri active
- Sesiune timp scurs

Configurare in settings.json:
{
    "statusLine": {
        "command": "python %USERPROFILE%/.claude/scripts/status_line.py"
    }
}

Primeste JSON pe stdin cu model, working_dir, transcript_path, output_style,
token_usage.
"""

import json
import sys
import re
from pathlib import Path


def latest_ai_tone_score() -> str:
    audit_dir = Path("%USERPROFILE%/.claude/scripts")
    audits = sorted(audit_dir.glob("_session_audit_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not audits:
        return "n/a"
    try:
        text = audits[0].read_text(encoding="utf-8", errors="ignore")
        scores = re.findall(r"\[\s*(\d+)/100\]", text)
        if scores:
            return f"{min(int(s) for s in scores)}/100"
    except Exception:
        pass
    return "n/a"


def short_path(path: str) -> str:
    if not path:
        return "?"
    p = Path(path)
    parts = p.parts
    if len(parts) > 3:
        return "..." + "/".join(parts[-2:])
    return str(p.name) if p.name else str(p)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    model = payload.get("model", {}).get("display_name", "?") if isinstance(payload.get("model"), dict) else payload.get("model", "?")
    cwd = short_path(payload.get("workspace", {}).get("current_dir", "") if isinstance(payload.get("workspace"), dict) else payload.get("cwd", ""))

    ai_score = latest_ai_tone_score()
    score_color = "\033[32m" if ai_score != "n/a" and int(ai_score.split("/")[0]) >= 80 else ("\033[33m" if ai_score != "n/a" and int(ai_score.split("/")[0]) >= 60 else "\033[31m") if ai_score != "n/a" else "\033[90m"

    parts = [
        f"\033[36m{model}\033[0m",
        f"\033[90m{cwd}\033[0m",
        f"{score_color}AI:{ai_score}\033[0m",
    ]
    print(" | ".join(parts))


if __name__ == "__main__":
    main()
