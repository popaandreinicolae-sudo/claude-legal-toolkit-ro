#!/usr/bin/env python3
"""
Stop hook — sumar quality-gate la sfarsit de sesiune (rapid, consultativ, local).

Ruleaza quality_gate in mod LOCAL (fara retea, ca sa nu intarzie inchiderea sesiunii)
pe documentele livrabile atinse recent si tipareste un sumar GO / GO-CU-VERIFICARE /
NO-GO per fisier. Pentru livrare externa, ruleaza la cerere subagentul quality-gate
(cu verificare prin MCP-uri). Nu blocheaza nimic. Kill-switch: ANTIHALU_OFF=1.
"""

import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
import hook_common

RECENT_WINDOW_SEC = 60 * 60
WATCH_DIRS = [
    Path.home() / 'Downloads',
    Path.home() / 'OneDrive' / 'Documents' / 'Claude',
    Path.home() / 'Claude',          # coworkUserFilesPath (Claude Desktop)
    Path('D:/Clienti'),              # livrabile pentru clienti
]
MAX_FILES = 8
MIN_WORDS = 150


def recent_deliverables():
    cutoff = time.time() - RECENT_WINDOW_SEC
    out = []
    for d in WATCH_DIRS:
        if not d.exists():
            continue
        try:
            for ext in ('*.md', '*.docx'):
                for p in d.rglob(ext):
                    try:
                        if p.stat().st_mtime < cutoff or p.stat().st_size > 5_000_000:
                            continue
                        norm = str(p).replace('\\', '/')
                        if any(s.replace('\\', '/') in norm for s in hook_common.SKIP_PATTERNS):
                            continue
                        out.append(p)
                    except OSError:
                        continue
        except OSError:
            continue
    out.sort(key=lambda x: -x.stat().st_mtime)
    return out[:MAX_FILES]


def main() -> int:
    hook_common.read_payload()  # consuma stdin
    if hook_common.kill_switch_on():
        return 0
    try:
        import quality_gate
    except Exception:
        return 0

    files = recent_deliverables()
    if not files:
        return 0

    results = []
    for p in files:
        try:
            r = quality_gate.run_gate(p, network=False)  # LOCAL, rapid
            results.append((p.name, r.get("verdict", "?"), len(r.get("blocking", [])), len(r.get("escalate", []))))
        except Exception:
            continue

    flagged = [r for r in results if r[1] != "GO"]
    if not flagged:
        return 0

    lines = ["[QUALITY-GATE · sumar sesiune] documente livrabile cu semnale (verificare locala):"]
    for name, verdict, nb, ne in flagged:
        lines.append(f"  {verdict}: {name} (blocante {nb}, de escaladat {ne})")
    lines.append("Pentru livrare externa, ruleaza subagentul quality-gate (verificare prin MCP-uri). Consultativ; nu modifica nimic fara verificare prin sursa.")
    print('\n'.join(lines), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
