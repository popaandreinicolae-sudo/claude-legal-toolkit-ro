#!/usr/bin/env python3
"""
Compara doua versiuni .docx pentru identificarea diferentelor cantitative.
Output: raport markdown cu sectiuni Adaugate, Eliminate, Modificate.

Util la detectarea halucinatiilor: cifre, capitole, anexe inventate intr-o versiune
si eliminate in alta.

Usage:
    python compare_docx_versions.py original.docx revizuit.docx [--output raport.md]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

try:
    from docx import Document
except ImportError:
    print("python-docx nu este instalat. Rulez: pip install python-docx", file=sys.stderr)
    sys.exit(1)


NUMBER_PATTERN = re.compile(
    r'\b(\d+[\.,]?\d*)\s*(milioane|miliarde|milion|miliard|EUR|RON|lei|MW|GW|kW|MWh|GWh|kWh|km|ha|m²|km²|%)\b',
    re.IGNORECASE
)

CHAPTER_PATTERN = re.compile(
    r'^(CAPITOLUL\s+[IVXLCM]+|Cap\.\s*\d+|Capitolul\s+[IVXLCM]+|Anexa\s+[A-Z])',
    re.IGNORECASE
)

CITATION_PATTERN = re.compile(
    r'\b(Decizia\s+(?:nr\.?\s*)?\d+/\d{4}|art\.?\s*\d+(?:\s*alin\.?\s*\(\d+\))?|OUG\s+\d+/\d{4}|Legea\s+\d+/\d{4}|HG\s+\d+/\d{4}|M\.Of\.|Hotararea\s+CEDO|Cauza\s+C-\d+/\d+|ECLI:EU:C:\d{4}:\d+)',
    re.IGNORECASE
)


def extract_paragraphs(docx_path: Path) -> list[str]:
    doc = Document(str(docx_path))
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def extract_numbers(text: str) -> list[tuple[str, str]]:
    """Returneaza (cifra, unitate) pentru fiecare numar cu unitate detectat."""
    return [(m.group(1), m.group(2)) for m in NUMBER_PATTERN.finditer(text)]


def extract_chapters(paragraphs: list[str]) -> list[str]:
    chapters = []
    for p in paragraphs:
        m = CHAPTER_PATTERN.match(p)
        if m:
            chapters.append(p[:120])
    return chapters


def extract_citations(text: str) -> set[str]:
    return set(m.group(0).lower() for m in CITATION_PATTERN.finditer(text))


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_matched_paragraphs(p1: list[str], p2: list[str], threshold: float = 0.6) -> tuple[set[int], set[int], list[tuple[int, int, float]]]:
    """Returneaza (only_in_1, only_in_2, matched_pairs)."""
    matched_1 = set()
    matched_2 = set()
    matched_pairs = []

    for i, a in enumerate(p1):
        if len(a) < 20:
            continue
        best_score = 0
        best_j = -1
        for j, b in enumerate(p2):
            if j in matched_2 or len(b) < 20:
                continue
            score = similarity(a[:300], b[:300])
            if score > best_score:
                best_score = score
                best_j = j
        if best_score >= threshold:
            matched_1.add(i)
            matched_2.add(best_j)
            matched_pairs.append((i, best_j, best_score))

    only_in_1 = set(range(len(p1))) - matched_1
    only_in_2 = set(range(len(p2))) - matched_2
    return only_in_1, only_in_2, matched_pairs


def generate_report(docx1: Path, docx2: Path) -> str:
    p1 = extract_paragraphs(docx1)
    p2 = extract_paragraphs(docx2)

    text1 = "\n".join(p1)
    text2 = "\n".join(p2)

    chapters1 = extract_chapters(p1)
    chapters2 = extract_chapters(p2)
    chapters_only_1 = [c for c in chapters1 if c not in chapters2]
    chapters_only_2 = [c for c in chapters2 if c not in chapters1]

    numbers1 = extract_numbers(text1)
    numbers2 = extract_numbers(text2)
    numbers_only_1 = [(c, u) for c, u in numbers1 if (c, u) not in numbers2]
    numbers_only_2 = [(c, u) for c, u in numbers2 if (c, u) not in numbers1]

    citations1 = extract_citations(text1)
    citations2 = extract_citations(text2)
    citations_only_1 = citations1 - citations2
    citations_only_2 = citations2 - citations1

    only_in_1, only_in_2, matched = find_matched_paragraphs(p1, p2)

    lines = []
    lines.append(f"# Raport comparativ versiuni document")
    lines.append("")
    lines.append(f"Versiune A: `{docx1.name}`")
    lines.append(f"Versiune B: `{docx2.name}`")
    lines.append("")
    lines.append(f"Paragrafe A: {len(p1)}  |  Paragrafe B: {len(p2)}  |  Match-uri: {len(matched)}")
    lines.append(f"Cuvinte A: {sum(len(p.split()) for p in p1)}  |  Cuvinte B: {sum(len(p.split()) for p in p2)}")
    lines.append("")

    lines.append("## Capitole prezente DOAR in versiunea A (potential halucinate sau eliminate)")
    if chapters_only_1:
        for c in chapters_only_1:
            lines.append(f"- {c}")
    else:
        lines.append("Niciun capitol unic.")
    lines.append("")

    lines.append("## Capitole prezente DOAR in versiunea B (adaugate dupa)")
    if chapters_only_2:
        for c in chapters_only_2:
            lines.append(f"- {c}")
    else:
        lines.append("Niciun capitol unic.")
    lines.append("")

    lines.append("## Cifre cu unitati prezente DOAR in versiunea A (potential halucinate)")
    if numbers_only_1:
        for cifra, unitate in numbers_only_1[:50]:
            lines.append(f"- {cifra} {unitate}")
        if len(numbers_only_1) > 50:
            lines.append(f"... plus {len(numbers_only_1) - 50} adiționale.")
    else:
        lines.append("Niciun numar unic.")
    lines.append("")

    lines.append("## Cifre cu unitati prezente DOAR in versiunea B (adaugate ulterior)")
    if numbers_only_2:
        for cifra, unitate in numbers_only_2[:50]:
            lines.append(f"- {cifra} {unitate}")
        if len(numbers_only_2) > 50:
            lines.append(f"... plus {len(numbers_only_2) - 50} adiționale.")
    else:
        lines.append("Niciun numar unic.")
    lines.append("")

    lines.append("## Citari juridice DOAR in versiunea A")
    if citations_only_1:
        for c in sorted(citations_only_1):
            lines.append(f"- {c}")
    else:
        lines.append("Niciuna.")
    lines.append("")

    lines.append("## Citari juridice DOAR in versiunea B")
    if citations_only_2:
        for c in sorted(citations_only_2):
            lines.append(f"- {c}")
    else:
        lines.append("Niciuna.")
    lines.append("")

    lines.append("## Paragrafe prezente DOAR in versiunea A (eliminate la revizuire)")
    lines.append(f"Total: {len(only_in_1)}")
    for idx in sorted(only_in_1)[:30]:
        snippet = p1[idx][:250]
        lines.append(f"- [{idx}]: {snippet}")
    if len(only_in_1) > 30:
        lines.append(f"... plus {len(only_in_1) - 30} adiționale.")
    lines.append("")

    lines.append("## Paragrafe prezente DOAR in versiunea B (adaugate la revizuire)")
    lines.append(f"Total: {len(only_in_2)}")
    for idx in sorted(only_in_2)[:30]:
        snippet = p2[idx][:250]
        lines.append(f"- [{idx}]: {snippet}")
    if len(only_in_2) > 30:
        lines.append(f"... plus {len(only_in_2) - 30} adiționale.")
    lines.append("")

    lines.append("## Interpretare")
    lines.append("")
    lines.append("Cifrele si capitolele prezente DOAR in versiunea A sunt candidate la halucinari, daca versiunea B este corectura finala.")
    lines.append("Cifrele prezente DOAR in versiunea B au fost adaugate manual cu sursa, deci sunt verificate.")
    lines.append("Citarile juridice trebuie verificate prin MCP-uri specifice.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compara doua versiuni .docx pentru detectare halucinatii.")
    parser.add_argument("docx1", type=Path, help="Prima versiune (potential cu halucinatii)")
    parser.add_argument("docx2", type=Path, help="A doua versiune (corectata)")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Fisier de output markdown")
    parser.add_argument("--json", action="store_true", help="Output JSON in loc de markdown")
    args = parser.parse_args()

    if not args.docx1.exists():
        print(f"Fisier inexistent: {args.docx1}", file=sys.stderr)
        sys.exit(1)
    if not args.docx2.exists():
        print(f"Fisier inexistent: {args.docx2}", file=sys.stderr)
        sys.exit(1)

    report = generate_report(args.docx1, args.docx2)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"Raport salvat la: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
