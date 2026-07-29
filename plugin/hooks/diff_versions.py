#!/usr/bin/env python3
"""
diff_versions.py — diff factual intre doua versiuni ale unui document.

Scoate la suprafata exact ce s-a schimbat la nivelul faptelor, ca utilizatorul sa
revizuiasca doar delta, nu tot documentul (metoda forensica). Compara:
  - citarile juridice (decizii, legi, directive) adaugate / eliminate;
  - cifrele cu unitati (EUR, %, mc, MWh, km...) adaugate / eliminate / modificate;
  - denumirile institutionale prezente.

Utilizare: python diff_versions.py <vechi.docx|md|txt> <nou.docx|md|txt> [--json]
"""

import json
import re
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

UNIT_RE = re.compile(r'(\d[\d\.,]*)\s*(EUR|euro|lei|RON|%|mc|MWh|GWh|kWh|Gcal|km2|km|ha|MW|kV|mld|milioane|miliarde)', re.IGNORECASE)
INST_RE = re.compile(r'\b(Ministerul [A-ZȘȚĂÂÎ][\w ]{2,30}|Curtea Constitu[tț]ional[aă]|ANRE|ANRSC|DNSC|ICCJ|ANAF|Transgaz|Transelectrica|Hidroelectrica|Romgaz|ELCEN|CMTEB|Guvernul Rom[aâ]niei|Parlamentul)\b')


def _read(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(str(path)).paragraphs if p.text.strip())
        except Exception:
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _citations(text: str) -> set:
    import citation_core
    return {f"{c['kind']}:{c['number']}/{c['year']}" for c in citation_core.extract_citations(text)}


def _figures(text: str) -> set:
    out = set()
    for m in UNIT_RE.finditer(text):
        val = m.group(1).replace(' ', '')
        out.add(f"{val} {m.group(2).lower()}")
    return out


def _institutions(text: str) -> set:
    return {m.group(1).strip() for m in INST_RE.finditer(text)}


def diff(old_path: Path, new_path: Path) -> dict:
    o, n = _read(old_path), _read(new_path)
    co, cn = _citations(o), _citations(n)
    fo, fn = _figures(o), _figures(n)
    io, ino = _institutions(o), _institutions(n)
    return {
        "old": old_path.name, "new": new_path.name,
        "citations": {"added": sorted(cn - co), "removed": sorted(co - cn)},
        "figures": {"added": sorted(fn - fo), "removed": sorted(fo - fn)},
        "institutions": {"added": sorted(ino - io), "removed": sorted(io - ino)},
    }


def format_report(d: dict) -> str:
    lines = [
        "═══════════════════════════════════════════════════",
        f"DIFF FACTUAL  {d['old']}  ->  {d['new']}",
        "═══════════════════════════════════════════════════",
        "",
        "CITARI:",
        *[f"  + {x}" for x in d['citations']['added']],
        *[f"  - {x}" for x in d['citations']['removed']],
        ("  (nicio schimbare de citari)" if not d['citations']['added'] and not d['citations']['removed'] else ""),
        "",
        "CIFRE (cu unitati):",
        *[f"  + {x}" for x in d['figures']['added'][:30]],
        *[f"  - {x}" for x in d['figures']['removed'][:30]],
        ("  (nicio schimbare de cifre)" if not d['figures']['added'] and not d['figures']['removed'] else ""),
        "",
        "INSTITUTII:",
        *[f"  + {x}" for x in d['institutions']['added']],
        *[f"  - {x}" for x in d['institutions']['removed']],
        ("  (nicio schimbare de institutii)" if not d['institutions']['added'] and not d['institutions']['removed'] else ""),
        "",
        "Revizuieste cu prioritate elementele ADAUGATE in versiunea noua: sunt candidatii de fact-check (cifre si citari nou introduse, neverificate inca).",
    ]
    return "\n".join(l for l in lines if l != "")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("Utilizare: python diff_versions.py <vechi> <nou> [--json]")
        sys.exit(0)
    d = diff(Path(args[0]), Path(args[1]))
    print(json.dumps(d, ensure_ascii=False, indent=1) if "--json" in sys.argv else format_report(d))
