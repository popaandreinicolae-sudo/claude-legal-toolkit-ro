#!/usr/bin/env python3
"""
build_source_pack.py — construieste un pachet de surse primare verificate inainte de redactare.

Idee (source grounding): redactarea se face DIN surse reale, nu din memoria modelului.
Primeste o lista de referinte (decizii CCR, legi, OUG etc.) sau un text din care le
extrage, descarca textul real prin legislatie.just.ro (via legal-verificator-ro) si
scrie un pachet .md cu extrase verificate, URL si statut. Redactarea ulterioara
citeaza doar ce apare in pachet; restul se marcheaza [NEVERIFICAT].

Utilizare:
  python build_source_pack.py --refs "Decizia 17/2015; Legea 47/1992; OUG 155/2024" [--out pachet.md]
  python build_source_pack.py --from-file sarcina.txt [--out pachet.md]
"""

import asyncio
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
_LEGAL_SRC = _SCRIPT_DIR.parent / "mcp-servers" / "legal-verificator-ro" / "src" / "legal_verificator"


async def _fetch_one(cit: dict) -> dict:
    if str(_LEGAL_SRC) not in sys.path:
        sys.path.insert(0, str(_LEGAL_SRC))
    import legislatie_client as L
    kind, number, year = cit["kind"], int(cit["number"]), int(cit["year"])
    try:
        if kind == "ccr":
            r = await L.fetch_ccr_text(number, year)
            return {"cit": cit, "found": bool(r.get("text")), "title": "", "url": r.get("printable_url", ""),
                    "text": r.get("text", ""), "status": "gasit" if r.get("text") else "negasit"}
        elif kind == "act":
            leg = await L.search_legislation(cit.get("act_type", "lege"), number, year)
            if not leg.get("found"):
                return {"cit": cit, "found": False, "status": "negasit", "title": "", "url": "", "text": ""}
            import re
            m = re.search(r"/(\d+)", leg["url"])
            text, url = ("", leg["url"])
            if m:
                text, url = await L.fetch_printable(m.group(1))
            return {"cit": cit, "found": True, "title": leg.get("title", ""), "url": url,
                    "status": leg.get("status", "in_vigoare"), "text": text or ""}
    except Exception as e:
        return {"cit": cit, "found": False, "status": f"eroare: {type(e).__name__}", "title": "", "url": "", "text": ""}
    return {"cit": cit, "found": False, "status": "tip nesuportat", "title": "", "url": "", "text": ""}


def build_pack(refs_text: str, out_path: str, excerpt_chars: int = 6000) -> str:
    import citation_core
    cits = citation_core.extract_citations(refs_text)
    cits = [c for c in cits if c["kind"] in ("ccr", "act")]
    if not cits:
        return "Nicio referinta RO (decizie CCR / lege / OUG) detectata in input."

    results = asyncio.run(_gather(cits))
    lines = [
        "# Pachet de surse primare verificate",
        "",
        "Generat de build_source_pack.py prin legislatie.just.ro. Reguli de redactare:",
        "redactezi DOAR pe baza extraselor de mai jos; orice afirmatie fara acoperire in",
        "pachet se marcheaza `[NEVERIFICAT]`; nu adaugi citari care nu apar aici.",
        "",
    ]
    ok = 0
    for r in results:
        c = r["cit"]
        head = f"## {c['raw']}  [{c['kind'].upper()}]"
        if r["found"]:
            ok += 1
            lines += [head,
                      f"- Statut: {r['status']}",
                      f"- Titlu: {r.get('title', '') or '(vezi sursa)'}",
                      f"- Sursa: {r.get('url', '')}",
                      "",
                      "Extras verificat (text real):",
                      "",
                      "```",
                      (r["text"][:excerpt_chars]).strip(),
                      "```",
                      ""]
        else:
            lines += [head,
                      f"- Statut: NEGASIT / {r['status']}",
                      "- ATENTIE: sursa nu a putut fi confirmata. NU o cita ca temei; marcheaza [NEVERIFICAT] sau elimina.",
                      ""]
    lines.insert(5, f"Surse confirmate: {ok}/{len(results)}.")
    out = "\n".join(lines)
    Path(out_path).write_text(out, encoding="utf-8")
    return f"Pachet scris in {out_path}: {ok}/{len(results)} surse confirmate."


async def _gather(cits):
    return [await _fetch_one(c) for c in cits]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", default="")
    ap.add_argument("--from-file", default="")
    ap.add_argument("--out", default=str(Path.home() / "source_pack.md"))
    a = ap.parse_args()
    txt = a.refs
    if a.from_file:
        txt = Path(a.from_file).read_text(encoding="utf-8", errors="ignore")
    if not txt.strip():
        print("Furnizeaza --refs \"Decizia 17/2015; Legea 47/1992\" sau --from-file sarcina.txt")
        sys.exit(0)
    print(build_pack(txt, a.out))
