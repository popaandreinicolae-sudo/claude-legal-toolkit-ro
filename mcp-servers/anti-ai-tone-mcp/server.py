#!/usr/bin/env python3
"""
Anti-AI Tone MCP Server.
Expune scriptul detect_ai_tone.py ca tool MCP, accesibil in Claude Code SI Claude Desktop.

Tools expuse:
- check_ai_tone(text, language?) -> raport detaliat cu scor + probleme
- quick_score(text) -> doar scor 0-100 (rapid)
- suggest_fixes(text) -> lista concreta de corectii sugerate
- check_file(file_path, language?) -> ruleaza pe fisier existent

Rulare locala, fara API key, fara dependenta externa.
"""
import asyncio
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / 'hooks'
DETECT_SCRIPT = SCRIPT_DIR / 'detect_ai_tone.py'
SKILL_PATH = Path(__file__).resolve().parent.parent.parent / 'skills' / 'anti-ai-tone.md'

app = Server('anti-ai-tone')

# Importam detectorul IN-PROCESS (fara subprocess, fara temp file, fara al doilea
# interpreter Python per apel). Asa apelurile sunt de ordinul milisecundelor si nu mai
# blocheaza bucla de evenimente a serverului MCP.
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from detect_ai_tone import analyze_text as _analyze_text, read_document as _read_document
except Exception:
    _analyze_text = None
    _read_document = None


def _subprocess_detect(target_path: str, language: str) -> dict:
    """Fallback pe subprocess, folosit doar daca importul in-process a esuat."""
    args = [sys.executable, str(DETECT_SCRIPT), str(target_path), '--json']
    if language != 'auto':
        args.extend(['--language', language])
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=25, encoding='utf-8',
        )
        if not result.stdout:
            return {'error': 'No output from detect_ai_tone.py', 'stderr': (result.stderr or '')[:500]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {'error': 'Detection timeout (>25s)'}
    except json.JSONDecodeError as e:
        return {'error': f'JSON parse failed: {e}'}


def run_detection(text: str, language: str = 'auto') -> dict:
    """Analiza in-process pe text brut. Rapida (regex), fara IO de proces."""
    if _analyze_text is not None:
        try:
            return _analyze_text(text, language, '<text>')
        except Exception as e:
            return {'error': f'analyze_text failed: {e}'}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(text)
        tmp_path = f.name
    try:
        return _subprocess_detect(tmp_path, language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def run_detection_file(file_path: str, language: str = 'auto') -> dict:
    """Analiza in-process pe un fisier existent (.md/.txt/.docx).
    Extrage textul din .docx corect, nu trimite octeti binari."""
    if _analyze_text is not None and _read_document is not None:
        try:
            text = _read_document(file_path)
            if not text.strip():
                return {'error': f'fisier gol sau necitibil: {file_path}'}
            return _analyze_text(text, language, str(file_path))
        except Exception as e:
            return {'error': f'detection failed: {e}'}
    return _subprocess_detect(file_path, language)


def format_human_report(data: dict) -> str:
    if 'error' in data:
        return f"EROARE: {data['error']}"

    score = data.get('naturalness_score', 0)
    verdict = data.get('verdict', '?')
    metrics = data.get('metrics', {})
    words = data.get('word_count', 0)

    lines = [
        f'SCOR NATURALETE: {score}/100  [{verdict}]',
        f'CUVINTE: {words}  |  LIMBA: {data.get("language", "?")}',
        '',
    ]

    issues = []
    if metrics.get('em_dash', {}).get('above_threshold'):
        issues.append(f"- em-dash overuse: {metrics['em_dash']['per_page']:.1f}/pag (max 1.0)")
    if metrics.get('appositional_dashes', {}).get('above_threshold'):
        count = metrics['appositional_dashes']['count']
        issues.append(f"- apozitii cu liniute in romana: {count} aparitii (REGULA 2.2 DOOM 3)")
        for ex in metrics['appositional_dashes'].get('examples', [])[:3]:
            issues.append(f"  GRESIT: {ex.get('snippet', '')}")
    if metrics.get('label_colon', {}).get('above_threshold'):
        issues.append(f"- label-colon '**X:** desc': {metrics['label_colon']['count']} (REGULA 0)")
    if metrics.get('negative_parallelism', {}).get('above_threshold'):
        issues.append(f"- paralelisme negative 'nu X, ci Y': {metrics['negative_parallelism']['count']}")
    if metrics.get('colon', {}).get('above_threshold'):
        ratio = metrics['colon']['ratio']
        issues.append(f"- colon overuse: {ratio*100:.0f}% paragrafe au ':' (max 30%)")
    if metrics.get('bullet_density', {}).get('above_threshold'):
        ratio = metrics['bullet_density']['ratio']
        issues.append(f"- bullet density: {ratio*100:.0f}% (max 20%)")
    if metrics.get('rule_of_three', {}).get('above_threshold'):
        issues.append(f"- rule of three obsesiv: {metrics['rule_of_three']['per_10_pages']:.1f}/10 pag (max 5)")
    if metrics.get('chatbot_total', 0) > 0:
        issues.append(f"- chatbot artifacts: {metrics['chatbot_total']}")
    if metrics.get('truisms_total', 0) > 0:
        issues.append(f"- truisme: {metrics['truisms_total']}")
    if metrics.get('conclusions_total', 0) > 0:
        issues.append(f"- inchideri mecanice: {metrics['conclusions_total']}")
    if metrics.get('copula_total', 0) > 3:
        issues.append(f"- copula avoidance: {metrics['copula_total']}")
    if metrics.get('hedging_total', 0) > 5:
        issues.append(f"- hedging excesiv: {metrics['hedging_total']}")
    if metrics.get('ai_vocab_total', 0) > 0:
        issues.append(f"- vocabular AI: {metrics['ai_vocab_total']} aparitii")
        for offender in data.get('top_offenders', {}).get('vocab', [])[:5]:
            issues.append(f"  - {offender.get('marker', '?')} x {offender.get('count', 0)}")

    if issues:
        lines.append('PROBLEME DETECTATE:')
        lines.extend(issues)
    else:
        lines.append('Niciun pattern major detectat.')

    return '\n'.join(lines)


def format_suggestions(data: dict) -> str:
    if 'error' in data:
        return f"EROARE: {data['error']}"

    metrics = data.get('metrics', {})
    suggestions = []

    if metrics.get('appositional_dashes', {}).get('above_threshold'):
        suggestions.append(
            "1. Inlocuieste TOATE liniutele apozitionale cu virgule. "
            "Pattern: 'X — explicatie — Y' devine 'X, explicatie, Y'. "
            "Excepție valabilă: doar la atribuire citat ('— Wiener, 1948') sau interval ('2020-2026')."
        )
    if metrics.get('label_colon', {}).get('above_threshold'):
        suggestions.append(
            "2. Sterge label-colon. '**Aspect:** descriere' devine paragraf normal sau heading H3/H4 urmat de proza."
        )
    if metrics.get('negative_parallelism', {}).get('above_threshold'):
        suggestions.append(
            "3. Inlocuieste 'Nu X, ci Y' cu afirmatii directe pozitive. "
            "'Nu un workaround, o decizie' devine 'O decizie structurala'."
        )
    if metrics.get('copula_total', 0) > 3:
        suggestions.append(
            "4. Restaureaza 'este/are' in locul circumlocuiilor. "
            "'X reprezinta Y' devine 'X este Y'. 'X serveste drept Y' devine 'X este Y'."
        )
    if metrics.get('chatbot_total', 0) > 0:
        suggestions.append(
            "5. Sterge complet artefactele conversationale: "
            "'Sper ca ajuta', 'Excelenta intrebare', 'Sa exploram', 'Hai sa descompunem'."
        )
    if metrics.get('truisms_total', 0) > 2:
        suggestions.append(
            "6. Elimina truismele de deschidere paragraf: "
            "'In contextul actual', 'In era digitala', 'Tehnologia evolueaza'. "
            "Inlocuieste cu un fapt concret, o data, o cifra."
        )
    if metrics.get('rule_of_three', {}).get('above_threshold'):
        suggestions.append(
            "7. Varianta numarul de elemente in enumerari. "
            "Daca ai 4 puncte legitime, scrie 4. Forta 3 doar cand exista 3 in realitate."
        )
    if metrics.get('hedging_total', 0) > 10:
        suggestions.append(
            "8. Afirma direct cand ai date. 'Bugetul a crescut cu 33%' (corect), "
            "NU 'Bugetul pare sa fi crescut cu aproximativ 33%'."
        )
    if metrics.get('ai_vocab_total', 0) > 5:
        offenders = data.get('top_offenders', {}).get('vocab', [])
        if offenders:
            terms = ', '.join(o.get('marker', '') for o in offenders[:5])
            suggestions.append(
                f"9. Inlocuieste termenii AI-vocab supraused: {terms}. "
                f"Lista neagra completa: instrumentul get_skill_rules, sau {SKILL_PATH}."
            )
    if metrics.get('em_dash', {}).get('above_threshold'):
        suggestions.append(
            "10. Maxim 1 em-dash per pagina. Inlocuieste cu virgula, punct, paranteze sau punct si virgula."
        )

    if not suggestions:
        return f"Scor {data.get('naturalness_score')}/100 - text acceptabil, fara corectii majore necesare."

    return '\n\n'.join(suggestions)


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name='check_ai_tone',
            description=(
                'Analiza completa anti-AI tone pentru un text dat. Returneaza scor naturalete '
                '0-100, verdict (NATURAL/REVIZUIRE/AI-LIKE), si lista detaliata de probleme '
                'detectate (em-dash, label-colon, paralelisme, triade, vocabular AI, copula '
                'avoidance, hedging, truisme, chatbot artifacts). Aplica 25 reguli din skill-ul '
                'anti-ai-tone v2.1, optimizat pentru limba romana.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'text': {
                        'type': 'string',
                        'description': 'Textul de analizat (Markdown sau plain text)',
                    },
                    'language': {
                        'type': 'string',
                        'enum': ['ro', 'en', 'auto'],
                        'default': 'auto',
                        'description': 'Limba textului. Auto detecteaza singur.',
                    },
                },
                'required': ['text'],
            },
        ),
        Tool(
            name='quick_score',
            description=(
                'Scor rapid de naturalete 0-100 pentru un text. Util pentru verificare rapida '
                'inainte de livrare. Returneaza doar scorul si verdictul, fara detalii.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'text': {'type': 'string'},
                },
                'required': ['text'],
            },
        ),
        Tool(
            name='suggest_fixes',
            description=(
                'Genereaza lista concreta de corectii pentru a reduce tonul AI dintr-un text. '
                'Returneaza maxim 10 actiuni prioritizate cu exemple specifice de inlocuire.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'text': {'type': 'string'},
                    'language': {'type': 'string', 'enum': ['ro', 'en', 'auto'], 'default': 'auto'},
                },
                'required': ['text'],
            },
        ),
        Tool(
            name='check_file',
            description=(
                'Analiza anti-AI tone pe un fisier existent (.md, .txt, .docx). Calea trebuie '
                'sa fie absoluta. Returneaza raport identic cu check_ai_tone.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'file_path': {
                        'type': 'string',
                        'description': 'Cale absoluta catre fisier',
                    },
                    'language': {'type': 'string', 'enum': ['ro', 'en', 'auto'], 'default': 'auto'},
                },
                'required': ['file_path'],
            },
        ),
        Tool(
            name='get_skill_rules',
            description=(
                'Returneaza continutul integral al skill-ului anti-ai-tone v2.1 (25 reguli, lista '
                'neagra 200+ termeni, exemple). Foloseste cand ai nevoie de regulile complete in '
                'context pentru a auto-corecta un text.'
            ),
            inputSchema={'type': 'object', 'properties': {}},
        ),
        Tool(
            name='fact_check_document',
            description=(
                'Analiza anti-halucinare pe un document profesional. Detecteaza: cifre fara sursa, '
                'capitole goale (slot fillers), anexe fictive cu indicatori inventati, scenarii '
                'cu cifre neverificate, atribuiri eronate, volume programe europene fara sursa, '
                'denumiri institutionale depasite (RADET, E-Distributie). Returneaza raport '
                'structurat cu probleme CRITICE, MAJORE, MINORE plus recomandari concrete de '
                'corectare. Bazat pe pattern-uri tipice de halucinare in documente LLM '
                '(entitati organizationale fabricate, sume inventate, indicatori fara sursa).'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'text': {
                        'type': 'string',
                        'description': 'Continutul documentului de fact-check (Markdown, text plain)',
                    },
                    'sector': {
                        'type': 'string',
                        'enum': ['general', 'energetic', 'juridic'],
                        'default': 'general',
                        'description': 'Sectorul specific pentru reguli sectoriale.',
                    },
                },
                'required': ['text'],
            },
        ),
        Tool(
            name='compare_versions',
            description=(
                'Compara doua versiuni .docx pentru a identifica diferentele cantitative '
                '(cifre, capitole, anexe). Util la detectarea halucinatiilor: continut prezent '
                'doar intr-o versiune indica generare fabricata. Returneaza raport markdown cu '
                'sectiuni Adaugate, Eliminate, Modificate, plus interpretare halucinatii vs '
                'corecturi reale.'
            ),
            inputSchema={
                'type': 'object',
                'properties': {
                    'version_a_path': {
                        'type': 'string',
                        'description': 'Cale absoluta versiune A (potential cu halucinatii)',
                    },
                    'version_b_path': {
                        'type': 'string',
                        'description': 'Cale absoluta versiune B (corectata, baseline)',
                    },
                },
                'required': ['version_a_path', 'version_b_path'],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == 'check_ai_tone':
        text = arguments.get('text', '')
        lang = arguments.get('language', 'auto')
        data = await asyncio.to_thread(run_detection, text, lang)
        return [TextContent(type='text', text=format_human_report(data))]

    if name == 'quick_score':
        text = arguments.get('text', '')
        data = await asyncio.to_thread(run_detection, text, 'auto')
        if 'error' in data:
            return [TextContent(type='text', text=f"EROARE: {data['error']}")]
        score = data.get('naturalness_score', 0)
        verdict = data.get('verdict', '?')
        return [TextContent(type='text', text=f'Scor: {score}/100 [{verdict}]')]

    if name == 'suggest_fixes':
        text = arguments.get('text', '')
        lang = arguments.get('language', 'auto')
        data = await asyncio.to_thread(run_detection, text, lang)
        return [TextContent(type='text', text=format_suggestions(data))]

    if name == 'check_file':
        file_path = arguments.get('file_path', '')
        p = Path(file_path)
        if not p.exists():
            return [TextContent(type='text', text=f'EROARE: fisierul nu exista: {file_path}')]
        lang = arguments.get('language', 'auto')
        data = await asyncio.to_thread(run_detection_file, str(p), lang)
        report = f'FILE: {p.name}\n' + format_human_report(data)
        return [TextContent(type='text', text=report)]

    if name == 'get_skill_rules':
        if not SKILL_PATH.exists():
            return [TextContent(type='text', text=f'EROARE: skill-ul nu exista la {SKILL_PATH}')]
        try:
            return [TextContent(type='text', text=SKILL_PATH.read_text(encoding='utf-8'))]
        except OSError as e:
            return [TextContent(type='text', text=f'EROARE citire skill: {e}')]

    if name == 'fact_check_document':
        text = arguments.get('text', '')
        sector = arguments.get('sector', 'general')
        out = await asyncio.to_thread(fact_check_document_inline, text, sector)
        return [TextContent(type='text', text=out)]

    if name == 'compare_versions':
        path_a = arguments.get('version_a_path', '')
        path_b = arguments.get('version_b_path', '')
        out = await asyncio.to_thread(compare_versions_inline, path_a, path_b)
        return [TextContent(type='text', text=out)]

    return [TextContent(type='text', text=f'Tool necunoscut: {name}')]


def fact_check_document_inline(text: str, sector: str = 'general') -> str:
    """Detectie halucinari intr-un document, fara compare cu sursa primara."""
    import re

    findings_critical = []
    findings_major = []
    findings_minor = []

    suspicious_numbers = re.findall(
        r'\b(\d+(?:[\.,]\d+)?)\s*(angajat[iî]|MW|GWh|MWh|milioane?|miliarde?|EUR|lei|RON|km|ha|m²|km²)\b',
        text,
        re.IGNORECASE,
    )

    chapter_titles = re.findall(
        r'^(CAPITOLUL\s+[IVXLCM]+\.\s*[A-ZĂÂÎȘȚ][^\n]{3,80})',
        text,
        re.MULTILINE,
    )

    for ch_title in chapter_titles:
        after_title_idx = text.find(ch_title) + len(ch_title)
        next_500 = text[after_title_idx:after_title_idx + 500].strip()
        if len(next_500) < 80:
            findings_critical.append(
                f"[CAPITOL POTENTIAL GOL] '{ch_title[:80]}' urmat de continut sub 80 caractere."
            )

    negparallel_matches = re.findall(
        r'Nu\s+\w+[,.]?\s+(?:ci|este|e)\s+\w+', text, re.IGNORECASE
    )
    if len(negparallel_matches) > 1:
        findings_major.append(
            f"[NEGATIVE PARALLELISM] {len(negparallel_matches)} aparitii: {negparallel_matches[:3]}"
        )

    if 'RADET' in text and 'CMTEB' not in text:
        findings_critical.append(
            "[DENUMIRE DEPASITA] 'RADET' fara mentionarea succesorului CMTEB (din 1 dec 2019)."
        )
    if 'E-Distributie' in text or 'Enel Distributie' in text:
        findings_critical.append(
            "[DENUMIRE DEPASITA] 'E-Distributie' sau 'Enel Distributie' este pre-fuziune. "
            "Foloseste 'Retele Electrice Romania S.A.' (din 30 nov 2024)."
        )

    suspicious_round = re.findall(
        r'\b(?:peste\s+)?(\d{2,3})\s*milioane?\s+EUR\b',
        text,
        re.IGNORECASE,
    )
    if len(suspicious_round) > 3:
        findings_major.append(
            f"[CIFRE ROTUNDE FARA SURSA] {len(suspicious_round)} aparitii cu pattern 'peste X milioane EUR'. "
            f"Cere sursa pentru fiecare program european."
        )

    if 'BCR' in text or 'beneficiu-cost' in text.lower():
        bcr_matches = re.findall(r'BCR\s*(?:estimat\s+)?(?:de\s+)?(\d+[\.,]\d+)', text, re.IGNORECASE)
        if bcr_matches:
            findings_major.append(
                f"[INDICATORI FINANCIARI FARA CALCUL] BCR mentionat fara metoda calcul: {bcr_matches[:3]}"
            )

    if 'Trust Fund' in text:
        tf_matches = re.findall(r'Trust\s+Fund[^.]*?(\d+(?:[\.,]\d+)?)\s*(milioane?|EUR)', text, re.IGNORECASE)
        if tf_matches:
            findings_critical.append(
                f"[SUSPICIUNE TRUST FUND INVENTAT] Mentionari Trust Fund cu sume: {tf_matches[:3]}. "
                f"Verifica prin surse primare publice ale finantatorului."
            )

    if re.search(r'Scenariu(l)?\s+(BAU|Strategy|Ambitious)', text, re.IGNORECASE):
        if not re.search(r'\[SCENARIU', text):
            findings_major.append(
                "[SCENARII FARA DISCLAIMER] Scenarii BAU/Strategy/Ambitious mentionate "
                "fara marcaj [SCENARIU, ipoteza X]. Adauga disclaimer obligatoriu."
            )

    lines = []
    lines.append("═" * 60)
    lines.append("FACT-CHECK DOCUMENT INLINE")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Sector: {sector}  |  Cuvinte: {len(text.split())}")
    lines.append(f"Cifre cu unitati: {len(suspicious_numbers)}  |  Capitole: {len(chapter_titles)}")
    lines.append("")

    if findings_critical:
        lines.append("───── PROBLEME CRITICE ─────")
        for f in findings_critical:
            lines.append(f"- {f}")
        lines.append("")

    if findings_major:
        lines.append("───── PROBLEME MAJORE ─────")
        for f in findings_major:
            lines.append(f"- {f}")
        lines.append("")

    if findings_minor:
        lines.append("───── PROBLEME MINORE ─────")
        for f in findings_minor:
            lines.append(f"- {f}")
        lines.append("")

    if not (findings_critical or findings_major or findings_minor):
        lines.append("Nu am detectat pattern-uri evidente de halucinare in document.")
        lines.append("Recomandare: ruleaza compare_versions cu versiunea anterioara pentru audit cantitativ.")
    else:
        n_critical = len(findings_critical)
        n_major = len(findings_major)
        if n_critical >= 3:
            verdict = "RESPINS, necesita revizuire majora"
        elif n_critical >= 1 or n_major >= 5:
            verdict = "REVIZUIRE MAJORA"
        elif n_major >= 1:
            verdict = "REVIZUIRE MINORA"
        else:
            verdict = "APROBAT cu observatii minore"
        lines.append(f"VERDICT: {verdict}")

    return '\n'.join(lines)


def compare_versions_inline(path_a: str, path_b: str) -> str:
    """Invoca scriptul de compare pe doua fisiere .docx."""
    import subprocess

    script_path = Path.home() / '.claude' / 'skills' / 'anti-hallucination-document' / 'scripts' / 'compare_docx_versions.py'
    if not script_path.exists():
        return f"EROARE: scriptul compare_docx_versions.py nu este la {script_path}"

    if not Path(path_a).exists():
        return f"EROARE: versiunea A nu exista: {path_a}"
    if not Path(path_b).exists():
        return f"EROARE: versiunea B nu exista: {path_b}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), path_a, path_b],
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
        )
        if result.returncode != 0:
            return f"EROARE rulare: {result.stderr[:500]}"
        return result.stdout
    except subprocess.TimeoutExpired:
        return "TIMEOUT, compararea depaseste 60 secunde"
    except Exception as e:
        return f"EROARE: {e}"


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == '__main__':
    asyncio.run(main())
