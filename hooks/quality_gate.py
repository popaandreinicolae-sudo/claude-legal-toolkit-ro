#!/usr/bin/env python3
"""
quality_gate.py — poarta unica de calitate (Definition of Done) inainte de livrare.

Lantuie toate verificarile deterministe pe un document si intoarce un raport
consolidat cu verdict GO / NO-GO:
  - citari juridice (citation_core), negasite / abrogate / denumiri depasite;
  - surse-fantoma si completitudine (phantom_source_guard);
  - consistenta numerica (numeric_consistency_guard);
  - ton AI (detect_ai_tone.py, scor naturalete).

Subagentul quality-gate adauga deasupra reviewerii LLM (anti-ai-tone-reviewer,
juridic-style-reviewer, citation-verifier). Acest script este nucleul determinist.

Utilizare: python quality_gate.py <fisier.docx|md|txt>  [--json]
"""

import json
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
DETECT = _SCRIPT_DIR / "detect_ai_tone.py"


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


def run_gate(path: Path, network: bool = True) -> dict:
    text = _read(path)
    report = {"file": path.name, "words": len(text.split()), "blocking": [], "escalate": [], "warnings": [], "checks": {}}
    if not text:
        report["error"] = "fisier gol sau ilizibil"
        report["verdict"] = "NO-GO"
        return report

    # Precedenta anti-contradictie:
    #  - BLOCANT doar semnalele de incredere mare (verdict determinist solid):
    #    act UE abrogat (statut EUR-Lex), eroare de ordin de marime, prag contradictoriu,
    #    sursa-fantoma folosita ca temei.
    #  - DE ESCALADAT (nu blocant automat): citari NEGASITE pe just.ro (poate fi un miss,
    #    nu neaparat inventata) si transpuneri context-gated. Acestea se confirma de
    #    subagentul citation-verifier prin MCP-uri (legal-verificator-ro, hudoc, eurlex)
    #    inainte de a deveni NO-GO. Asa evitam stergerea unei citari reale pe fals-pozitiv.
    #  - AVERTISMENT: restul (denumiri depasite, liste incomplete, densitate cifre, ton AI).
    BLOCK_PREFIX = ("ACT ABROGAT", "POSIBILA EROARE DE ORDIN", "PRAG DEFINIT", "SURSA-FANTOMA")
    ESCALATE_PREFIX = ("CITARE NEGASITA", "POSIBILA TRANSPUNERE")

    def classify(prob):
        if prob.startswith(BLOCK_PREFIX):
            report["blocking"].append(prob)
        elif prob.startswith(ESCALATE_PREFIX):
            report["escalate"].append(prob)
        else:
            report["warnings"].append(prob)

    # 1. citari (network controlat: True la poarta on-demand, False la Stop hook pentru viteza)
    try:
        import citation_core
        cit = citation_core.verify_text(text, budget_s=20.0, cap=40, network=network)
        report["checks"]["citations"] = {"total": cit["total"], "problems": cit["problems"]}
        for prob in cit["problems"]:
            classify(prob)
    except Exception as e:
        report["warnings"].append(f"citation check indisponibil: {e}")

    # 2. surse-fantoma / completitudine
    try:
        import phantom_source_guard
        ph = phantom_source_guard.detect(text)
        report["checks"]["phantom"] = ph
        for prob in ph:
            classify(prob)
    except Exception as e:
        report["warnings"].append(f"phantom check indisponibil: {e}")

    # 3. consistenta numerica
    try:
        import numeric_consistency_guard
        nm = numeric_consistency_guard.detect(text)
        report["checks"]["numeric"] = nm
        for prob in nm:
            classify(prob)
    except Exception as e:
        report["warnings"].append(f"numeric check indisponibil: {e}")

    # 4. ton AI
    try:
        res = subprocess.run([sys.executable, str(DETECT), str(path), "--json"],
                             capture_output=True, text=True, timeout=25, encoding="utf-8")
        data = json.loads(res.stdout) if res.stdout else {}
        score = data.get("naturalness_score", 100)
        report["checks"]["ai_tone_score"] = score
        if score < 70:
            report["warnings"].append(f"ton AI: scor naturalete {score}/100 (<70), reaplica anti-ai-tone")
    except Exception as e:
        report["warnings"].append(f"ai-tone check indisponibil: {e}")

    if report["blocking"]:
        report["verdict"] = "NO-GO"
    elif report["escalate"]:
        report["verdict"] = "GO-CU-VERIFICARE"
    else:
        report["verdict"] = "GO"
    return report


def format_report(r: dict) -> str:
    lines = [
        "═══════════════════════════════════════════════════",
        f"QUALITY GATE — {r['file']}  ({r.get('words', 0)} cuvinte)",
        "═══════════════════════════════════════════════════",
        f"VERDICT: {r.get('verdict', '?')}",
        f"Blocante: {len(r.get('blocking', []))} | De escaladat: {len(r.get('escalate', []))} | Avertismente: {len(r.get('warnings', []))}",
        "",
    ]
    if r.get("blocking"):
        lines.append("BLOCANTE (incredere mare, rezolva inainte de livrare):")
        lines += [f"  ✗ {b}" for b in r["blocking"]]
        lines.append("")
    if r.get("escalate"):
        lines.append("DE ESCALADAT (confirma prin citation-verifier inainte de a decide):")
        lines += [f"  → {e}" for e in r["escalate"]]
        lines.append("")
    if r.get("warnings"):
        lines.append("AVERTISMENTE:")
        lines += [f"  ! {w}" for w in r["warnings"][:12]]
        lines.append("")
    sc = r.get("checks", {})
    lines.append(f"Sumar: citari {sc.get('citations', {}).get('total', 0)}, "
                 f"ton {sc.get('ai_tone_score', '?')}/100.")
    v = r.get("verdict")
    if v == "GO":
        lines.append("GO. Pentru livrare externa, ruleaza si reviewerii LLM (citation-verifier, juridic-style-reviewer).")
    elif v == "GO-CU-VERIFICARE":
        lines.append("GO-CU-VERIFICARE. Nimic blocant, dar exista citari neconfirmate pe just.ro. Ruleaza citation-verifier (MCP-uri) inainte de livrare; nu sterge citarile fara verificare.")
    else:
        lines.append("NO-GO. Documentul are probleme blocante de fapt/citare. Nu livra.")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    if not args:
        print("Utilizare: python quality_gate.py <fisier> [--json]")
        sys.exit(0)
    rep = run_gate(Path(args[0]))
    print(json.dumps(rep, ensure_ascii=False, indent=1) if as_json else format_report(rep))
