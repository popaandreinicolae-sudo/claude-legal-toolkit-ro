#!/usr/bin/env python3
"""
legislatie_watcher.py — monitor de legislatie si jurisprudenta pe temele tezei.

Cauta pe legislatie.just.ro acte si decizii pe cuvintele-cheie ale doctoratului
(securitate cibernetica, restrangerea drepturilor, NIS2 etc.), compara cu ce a
vazut data trecuta (cache) si scrie un briefing doar cu noutatile. Conceput pentru
rulare programata (Scheduled Tasks in Cowork) sau manual.

Utilizare:
  python legislatie_watcher.py [--out briefing.md]
"""

import asyncio
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SEEN = _SCRIPT_DIR / ".watcher_seen.json"
_LEGAL_SRC = _SCRIPT_DIR.parent / "mcp-servers" / "legal-verificator-ro" / "src" / "legal_verificator"

# Teme doctorat / arii de interes.
KEYWORDS = [
    "securitate cibernetica",
    "securitatea retelelor si sistemelor informatice",
    "restrangerea exercitiului unor drepturi",
    "date cu caracter personal",
    "infrastructura critica",
    "stare de urgenta",
    "drepturi si libertati fundamentale",
]


def _load_seen() -> set:
    try:
        return set(json.loads(_SEEN.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save_seen(seen: set):
    try:
        _SEEN.write_text(json.dumps(sorted(seen), ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


async def _search_all() -> dict:
    if str(_LEGAL_SRC) not in sys.path:
        sys.path.insert(0, str(_LEGAL_SRC))
    import legislatie_client as L
    found = {}
    for kw in KEYWORDS:
        try:
            res = await L.search_document(query=kw)
            for r in res[:8]:
                did = r.get("doc_id") or r.get("url", "")
                if did:
                    found.setdefault(did, {"title": r.get("title", "").strip(), "url": r.get("url", ""), "kw": kw})
        except Exception:
            continue
    return found


def run(out_path: str) -> str:
    seen = _load_seen()
    found = asyncio.run(_search_all())
    new = {k: v for k, v in found.items() if k not in seen}

    import time
    stamp = time.strftime("%Y-%m-%d")
    lines = [f"# Briefing legislativ — {stamp}", "",
             f"Monitor pe {len(KEYWORDS)} teme. Verificate {len(found)} rezultate, {len(new)} noi fata de ultima rulare.", ""]
    if not new:
        lines.append("Nicio noutate relevanta fata de ultima verificare.")
    else:
        lines.append("## Noutati de verificat")
        lines.append("")
        for did, v in new.items():
            title = v["title"] or "(fara titlu)"
            lines.append(f"- [{v['kw']}] {title}")
            if v["url"]:
                lines.append(f"  {v['url']}")
        lines.append("")
        lines.append("Reguli: tratati fiecare element ca [NEVERIFICAT] pana la lecturarea sursei; "
                     "confruntati cu actele in vigoare prin legal-verificator-ro inainte de a-l folosi.")

    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    _save_seen(seen | set(found.keys()))
    return f"Briefing scris in {out_path}: {len(new)} noutati din {len(found)} rezultate."


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = str(Path.home() / "Downloads" / "briefing_legislativ.md")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    print(run(out))
