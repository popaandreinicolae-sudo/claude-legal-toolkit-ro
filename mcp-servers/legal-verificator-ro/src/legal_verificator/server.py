"""
Legal Verificator RO — MCP Server
8 tools for Romanian legal verification: CCR decisions, legislation, jurisprudence.
Sources: legislatie.just.ro (public) + lege5.ro (authenticated).
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import Lege5Session, Lege6Session
from legislatie_client import (
    search_ccr, fetch_ccr_text, search_legislation, fetch_article, fetch_printable, search_document,
    fetch_url_text, UpstreamUnavailable,
)
from lege5_client import (
    search as lege5_search_fn,
    fetch_document as lege5_fetch_doc,
    search_ccr_decision as lege5_search_ccr,
    fetch_ccr_text as lege5_fetch_ccr,
)
from lege6_client import (
    search as lege6_search_fn,
    fetch_document as lege6_fetch_doc,
    search_ccr_decision as lege6_search_ccr,
    fetch_ccr_text as lege6_fetch_ccr,
    search_legislation as lege6_search_legislation,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger("legal-verificator")

app = Server("legal-verificator-ro")
lege5_session = Lege5Session()
lege6_session = Lege6Session()


# ── TOOL DEFINITIONS ──────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="search_ccr_decision",
            description="Caută o decizie CCR pe legislatie.just.ro și lege5.ro. Returnează URL, titlu, data publicării.",
            inputSchema={
                "type": "object",
                "properties": {
                    "number": {"type": ["integer", "string"], "description": "Numărul deciziei CCR"},
                    "year": {"type": ["integer", "string"], "description": "Anul deciziei CCR"},
                },
                "required": ["number", "year"],
            },
        ),
        types.Tool(
            name="fetch_ccr_decision_text",
            description="Descarcă textul integral al unei decizii CCR. Poate extrage doar o secțiune (dispozitiv, motivare, par. X).",
            inputSchema={
                "type": "object",
                "properties": {
                    "number": {"type": ["integer", "string"], "description": "Numărul deciziei CCR"},
                    "year": {"type": ["integer", "string"], "description": "Anul deciziei CCR"},
                    "section": {"type": "string", "description": "Secțiune opțională: 'dispozitiv', 'motivare', 'par. 65' etc."},
                },
                "required": ["number", "year"],
            },
        ),
        types.Tool(
            name="verify_ccr_citation",
            description="Verifică dacă o citare CCR e corectă. Returnează CONFIRMED/INCORRECT/UNVERIFIABLE cu evidență din text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "number": {"type": ["integer", "string"], "description": "Numărul deciziei CCR"},
                    "year": {"type": ["integer", "string"], "description": "Anul deciziei CCR"},
                    "claimed_subject": {"type": "string", "description": "Subiectul pretins al deciziei (ex: 'Cod penal', 'OUG salarială')"},
                    "claimed_principle": {"type": "string", "description": "Principiu sau text specific pretins a fi în decizie"},
                },
                "required": ["number", "year", "claimed_subject"],
            },
        ),
        types.Tool(
            name="search_ccr_by_subject",
            description="Caută o decizie CCR după subiect (util când există mai multe decizii cu același număr). Returnează toate match-urile.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subiectul deciziei (ex: 'Legea securității cibernetice', 'Cod penal')"},
                    "year": {"type": "integer", "description": "Anul deciziei"},
                    "limit": {"type": "integer", "description": "Număr maxim rezultate (default 5)"},
                },
                "required": ["subject"],
            },
        ),
        types.Tool(
            name="search_legislation",
            description="Caută un act normativ pe legislatie.just.ro. Verifică dacă e în vigoare sau abrogat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, og, hg, ordin, cod, constitutie"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                },
                "required": ["act_type"],
            },
        ),
        types.Tool(
            name="fetch_article_text",
            description="Extrage textul exact al unui articol/alineat/literă din actul normativ specificat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, hg, cod, constitutie"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului, 0 pentru Constituție (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                    "article": {"type": ["integer", "string"], "description": "Numărul articolului"},
                    "alineat": {"type": ["integer", "string"], "description": "Numărul alineatului (opțional)"},
                    "litera": {"type": "string", "description": "Litera (opțional, ex: 'a', 'b')"},
                },
                "required": ["act_type", "article"],
            },
        ),
        types.Tool(
            name="fetch_legal_url",
            description="Descarcă și extrage textul oricărui document juridic de la un URL, inclusiv PDF-uri "
                        "și site-uri care blochează boți (control.gov.ro, monitoruloficial etc.). Trimite user-agent "
                        "de browser și urmărește redirect-urile, deci reușește unde web-fetch-ul generic dă "
                        "'Failed to fetch' cu 403. FOLOSEȘTE acest tool când un fetch web al unui act/PDF juridic eșuează.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL-ul complet al documentului (http/https, inclusiv .pdf)"},
                    "max_chars": {"type": "integer", "description": "Limită caractere text returnat (default 20000)"},
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="lege6_search",
            description="PRIORITAR. Căutare full-text pe lege6.ro (Indaco Systems, platforma cea mai actualizată) în legislație, jurisprudență, doctrină. Folosește această sursă PRIMA pentru orice verificare de act normativ sau jurisprudență.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de căutare"},
                    "category": {"type": "string", "description": "Categorie: legislatie, jurisprudenta, doctrina, ccr"},
                    "max_results": {"type": "integer", "description": "Număr maxim de rezultate (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="lege6_fetch_document",
            description="Descarcă conținutul complet al unui document de pe lege6.ro (autentificat).",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL-ul documentului pe lege6.ro"},
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="lege6_search_legislation",
            description="Caută un act normativ pe lege6.ro după tip + nr/an. Returnează status (în vigoare/abrogat/modificat).",
            inputSchema={
                "type": "object",
                "properties": {
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, og, hg, ordin, cod, constitutie"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                },
                "required": ["act_type"],
            },
        ),
        types.Tool(
            name="lege5_search",
            description="LEGACY. Căutare full-text pe lege5.ro (vechea platforma Indaco). Folosiți lege6_search ca sursa primara.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de căutare"},
                    "category": {"type": "string", "description": "Categorie: legislatie, jurisprudenta, doctrina, ccr"},
                    "max_results": {"type": "integer", "description": "Număr maxim de rezultate (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="lege5_fetch_document",
            description="LEGACY. Descarcă conținutul unui document de pe lege5.ro.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL-ul documentului pe lege5.ro"},
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="batch_verify_ccr",
            description="Verifică în lot mai multe decizii CCR. Rate limited, cu sumar la final.",
            inputSchema={
                "type": "object",
                "properties": {
                    "decisions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "number": {"type": "integer"},
                                "year": {"type": "integer"},
                                "claimed_subject": {"type": "string"},
                            },
                            "required": ["number", "year", "claimed_subject"],
                        },
                        "description": "Lista de decizii CCR de verificat",
                    },
                },
                "required": ["decisions"],
            },
        ),
    ]


# ── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────

async def _search_ccr_both(number: int, year: int) -> dict:
    """Search CCR with priority: lege6.ro -> legislatie.just.ro -> lege5.ro.

    lege6.ro contine legislatia si jurisprudenta cea mai actualizata (Indaco Systems).
    Fallback: legislatie.just.ro (oficial). Final fallback: lege5.ro.
    """
    errors = []

    # 1. Lege6.ro (PRIORITAR - cea mai actualizata sursa)
    try:
        result = await lege6_search_ccr(lege6_session, number, year)
        if result.get("found"):
            return result
        errors.append(("lege6.ro", "decizia nu a fost gasita"))
    except Exception as e:
        logger.warning("lege6.ro unavailable: %s", e)
        errors.append(("lege6.ro", str(e)))

    # 2. legislatie.just.ro (oficial, public)
    try:
        result = await search_ccr(number, year)
        if result.get("found"):
            result["source"] = "legislatie.just.ro"
            return result
        errors.append(("legislatie.just.ro", "decizia nu a fost gasita"))
    except UpstreamUnavailable as e:
        logger.warning("legislatie.just.ro unavailable: %s", e)
        errors.append(("legislatie.just.ro", str(e)))
    except Exception as e:
        errors.append(("legislatie.just.ro", str(e)))

    # 3. Lege5.ro (legacy fallback)
    try:
        result = await lege5_search_ccr(lege5_session, number, year)
        if isinstance(result, dict) and result.get("found"):
            return result
        errors.append(("lege5.ro", "decizia nu a fost gasita"))
        return result
    except Exception as e:
        errors.append(("lege5.ro", str(e)))
        return {"found": False, "errors": errors, "error": "Decizia nu a fost gasita pe niciuna din sursele disponibile."}


async def _fetch_ccr_text_both(number: int, year: int) -> dict:
    """Fetch CCR text with priority: lege6.ro -> legislatie.just.ro -> lege5.ro."""
    errors = []

    # 1. Lege6.ro PRIORITAR
    try:
        result = await lege6_fetch_ccr(lege6_session, number, year)
        if result.get("text"):
            return result
        errors.append(("lege6.ro", result.get("error", "fara text")))
    except Exception as e:
        logger.warning("lege6.ro fetch error: %s", e)
        errors.append(("lege6.ro", str(e)))

    # 2. legislatie.just.ro
    try:
        result = await fetch_ccr_text(number, year)
        if result.get("text"):
            return result
        errors.append(("legislatie.just.ro", result.get("error", "fara text")))
    except UpstreamUnavailable as e:
        logger.warning("legislatie.just.ro unavailable for fetch: %s", e)
        errors.append(("legislatie.just.ro", str(e)))
    except Exception as e:
        errors.append(("legislatie.just.ro", str(e)))

    # 3. Lege5.ro
    try:
        result = await lege5_fetch_ccr(lege5_session, number, year)
        if result.get("text"):
            return result
        errors.append(("lege5.ro", result.get("error", "fara text")))
    except Exception as e:
        errors.append(("lege5.ro", str(e)))

    return {"text": "", "errors": errors, "error": "Textul deciziei nu a putut fi extras din nicio sursa."}


def _extract_section(text: str, section: str) -> str:
    """Extract a specific section from CCR decision text."""
    section_lower = section.lower().strip()

    if section_lower == "dispozitiv":
        patterns = [
            r'D\s*I\s*S\s*P\s*U\s*N\s*E',
            r'DECIDE:',
            r'HOTĂRĂȘTE:',
            r'În numele legii',
            r'Curtea Constituțională.*decide:',
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return text[match.start():]
        return text[-3000:]  # fallback: last 3000 chars

    elif section_lower == "motivare":
        disp_patterns = [r'D\s*I\s*S\s*P\s*U\s*N\s*E', r'DECIDE:', r'HOTĂRĂȘTE:']
        end = len(text)
        for p in disp_patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                end = match.start()
                break
        # Skip header (first ~500 chars)
        return text[500:end]

    elif section_lower.startswith("par.") or section_lower.startswith("§"):
        par_num = re.search(r'\d+', section)
        if par_num:
            n = par_num.group()
            match = re.search(rf'{n}\.\s', text)
            if match:
                # Get ~2000 chars from that paragraph
                return text[match.start():match.start() + 2000]

    return text


def _verify_citation(text: str, claimed_subject: str, claimed_principle: Optional[str] = None) -> dict:
    """Verify a CCR citation against actual text."""
    if not text:
        return {"verdict": "UNVERIFIABLE", "actual_subject": "", "relevance_score": 0.0, "evidence": ""}

    # Extract actual subject from first 2000 chars
    intro = text[:2000].lower()
    actual_subject = ""

    # Look for typical CCR decision subject patterns
    subject_patterns = [
        r'obiectul\s+(?:sesizării|excepției|controlului)[\s:]+(.{50,300})',
        r'privind\s+(.{30,200})',
        r'referitoare?\s+la\s+(.{30,200})',
        r'asupra\s+(?:admiterii|respingerii|admisibilității)[\s]+(.{30,200})',
    ]

    for p in subject_patterns:
        match = re.search(p, intro)
        if match:
            actual_subject = match.group(1).strip()[:200]
            break

    if not actual_subject:
        # Fallback: first sentence after title
        actual_subject = intro[:200]

    # Legal synonyms for better matching
    SYNONYMS = {
        "securitate": ["securității", "securitatea", "security"],
        "cibernetica": ["cibernetică", "cibernetice", "cibernetici", "cyber", "cybersecurity"],
        "constitutionalitate": ["constituționalitate", "constituțional", "constitutional", "neconstituționalitate"],
        "lege": ["legii", "legea", "legislație"],
        "decizie": ["deciziei", "decizia"],
        "drept": ["drepturi", "dreptul", "drepturilor"],
        "restrângere": ["restrângerea", "restricționare", "limitare"],
        "suveranitate": ["suveranității", "suveran"],
        "energie": ["energiei", "energetic", "energetică"],
    }

    def expand_words(words):
        expanded = set(words)
        for w in list(words):
            for key, syns in SYNONYMS.items():
                if w == key or w in syns:
                    expanded.add(key)
                    expanded.update(syns)
        return expanded

    # Compare claimed subject with actual
    claimed_words = set(re.findall(r'\b\w{3,}\b', claimed_subject.lower()))
    claimed_expanded = expand_words(claimed_words)
    actual_words = set(re.findall(r'\b\w{3,}\b', actual_subject.lower()))

    if not claimed_words:
        return {"verdict": "UNVERIFIABLE", "actual_subject": actual_subject, "relevance_score": 0.0, "evidence": ""}

    overlap = claimed_expanded & actual_words
    score = len(overlap) / len(claimed_words) if claimed_words else 0.0

    # Also check full text (first 10000 chars, not just 2000)
    full_lower = text[:10000].lower()
    full_hits = sum(1 for w in claimed_expanded if w in full_lower)
    full_score = full_hits / len(claimed_words) if claimed_words else 0.0

    combined_score = max(score, full_score * 0.7)

    # Check claimed principle
    principle_found = ""
    if claimed_principle:
        if claimed_principle.lower() in full_lower:
            principle_found = claimed_principle
            combined_score = min(1.0, combined_score + 0.3)
        else:
            # Fuzzy: check if most words from principle are in text
            principle_words = set(re.findall(r'\b\w{4,}\b', claimed_principle.lower()))
            hits = sum(1 for w in principle_words if w in full_lower)
            if principle_words and hits / len(principle_words) > 0.6:
                combined_score = min(1.0, combined_score + 0.2)

    # Determine verdict
    if combined_score >= 0.5:
        verdict = "CONFIRMED"
    elif combined_score >= 0.2:
        verdict = "UNVERIFIABLE"
    else:
        verdict = "INCORRECT"

    # Extract evidence
    evidence = ""
    for w in claimed_words:
        idx = full_lower.find(w)
        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(text), idx + 100)
            evidence = text[start:end].strip()
            break

    return {
        "verdict": verdict,
        "actual_subject": actual_subject,
        "relevance_score": round(combined_score, 2),
        "evidence": evidence[:300],
    }


_NUM_ALIASES = ("act_number", "act_no", "act_nr", "nr", "numar", "număr", "decision_number")
_YEAR_ALIASES = ("act_year", "an", "anul")
_LEGISLATION_TOOLS = {"search_legislation", "fetch_article_text", "lege6_search_legislation"}


def _normalize_args(args: dict) -> dict:
    """Accepta aliasurile pe care modelul le trimite frecvent (act_number/act_year)
    si coercitioneaza numerele date ca text ('334' -> 334). Fara acest strat,
    apeluri corecte semantic esueaza pe nepotriviri de nume/tip."""
    if not isinstance(args, dict):
        return args
    a = dict(args)
    if a.get("number") is None:
        for alt in _NUM_ALIASES:
            if a.get(alt) is not None:
                a["number"] = a[alt]
                break
    if a.get("year") is None:
        for alt in _YEAR_ALIASES:
            if a.get(alt) is not None:
                a["year"] = a[alt]
                break
    for k in ("number", "year", "article", "alineat", "limit", "max_results"):
        v = a.get(k)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            a[k] = int(v)
    return a


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        arguments = _normalize_args(arguments)
        if name in _LEGISLATION_TOOLS:
            if arguments.get("number") is None or arguments.get("year") is None:
                # Recuperare eleganta: in loc de eroare seaca, cautam full-text dupa
                # indiciile disponibile si intoarcem candidati cu an, ca modelul sa reapeleze precis.
                hint = (arguments.get("query") or " ".join(
                    str(arguments[k]) for k in ("act_type", "number") if arguments.get(k) is not None
                )).strip()
                candidates = []
                if hint:
                    # Intai sursa nativa a tool-ului (lege6, autentificat), apoi just.ro public.
                    if name.startswith("lege6"):
                        try:
                            r = await lege6_search_fn(lege6_session, hint, "legislatie", 8)
                            candidates = r if isinstance(r, list) else (r.get("results") if isinstance(r, dict) else [])
                        except Exception:
                            candidates = []
                    if not candidates:
                        try:
                            candidates = await search_document(hint)
                        except Exception:
                            candidates = []
                    candidates = (candidates or [])[:8]
                return [types.TextContent(type="text", text=json.dumps({
                    "note": "Lipsea 'year' (sau 'number'). Am căutat full-text după indiciile date. "
                            "Alege actul potrivit din 'candidates' și reapelează cu number+year ca întregi.",
                    "query_used": hint,
                    "candidates": candidates,
                    "received_keys": sorted(arguments.keys()),
                }, ensure_ascii=False, indent=2))]

        if name == "search_ccr_decision":
            result = await _search_ccr_both(arguments["number"], arguments["year"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "fetch_ccr_decision_text":
            result = await _fetch_ccr_text_both(arguments["number"], arguments["year"])
            section = arguments.get("section")
            if section and result.get("text"):
                result["text"] = _extract_section(result["text"], section)
                result["section"] = section
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "search_ccr_by_subject":
            subject = arguments["subject"]
            year = arguments.get("year")
            query = f"DECIZIE {subject}"
            if year:
                query += f" {year}"
            results = await search_document(query)
            filtered = []
            for r in results[:arguments.get("limit", 5)]:
                title_lower = r["title"].lower()
                if "decizie" in title_lower or "decizia" in title_lower:
                    filtered.append(r)
            return [types.TextContent(type="text", text=json.dumps({"results": filtered, "count": len(filtered)}, ensure_ascii=False, indent=2))]

        elif name == "verify_ccr_citation":
            text_result = await _fetch_ccr_text_both(arguments["number"], arguments["year"])
            if not text_result.get("text"):
                result = {
                    "verdict": "UNVERIFIABLE",
                    "error": text_result.get("error", f"Decizia CCR nr. {arguments['number']}/{arguments['year']} nu a fost găsită."),
                }
            else:
                result = _verify_citation(
                    text_result["text"],
                    arguments["claimed_subject"],
                    arguments.get("claimed_principle"),
                )
                result["source"] = text_result.get("source", "")
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "search_legislation":
            result = await search_legislation(arguments["act_type"], arguments["number"], arguments["year"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "fetch_article_text":
            result = await fetch_article(
                arguments["act_type"], arguments["number"], arguments["year"],
                arguments["article"], arguments.get("alineat"), arguments.get("litera"),
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "fetch_legal_url":
            result = await fetch_url_text(arguments["url"], arguments.get("max_chars", 20000))
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "lege6_search":
            result = await lege6_search_fn(
                lege6_session,
                arguments["query"],
                arguments.get("category"),
                arguments.get("max_results", 10),
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "lege6_fetch_document":
            result = await lege6_fetch_doc(lege6_session, arguments["url"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "lege6_search_legislation":
            result = await lege6_search_legislation(
                lege6_session,
                arguments["act_type"], arguments["number"], arguments["year"],
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "lege5_search":
            result = await lege5_search_fn(
                lege5_session,
                arguments["query"],
                arguments.get("category"),
                arguments.get("max_results", 10),
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "lege5_fetch_document":
            result = await lege5_fetch_doc(lege5_session, arguments["url"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "batch_verify_ccr":
            decisions = arguments["decisions"]
            results = []
            confirmed = incorrect = unverifiable = 0

            for i, dec in enumerate(decisions):
                text_result = await _fetch_ccr_text_both(dec["number"], dec["year"])
                if text_result.get("text"):
                    v = _verify_citation(text_result["text"], dec["claimed_subject"])
                else:
                    v = {"verdict": "UNVERIFIABLE", "actual_subject": ""}

                key = f"DCC {dec['number']}/{dec['year']}"
                results.append({"key": key, "verdict": v["verdict"], "actual_subject": v.get("actual_subject", "")})

                if v["verdict"] == "CONFIRMED":
                    confirmed += 1
                elif v["verdict"] == "INCORRECT":
                    incorrect += 1
                else:
                    unverifiable += 1

                # Rate limiting: 1 second between batches of 3
                if (i + 1) % 3 == 0:
                    await asyncio.sleep(1.0)

            return [types.TextContent(type="text", text=json.dumps({
                "results": results,
                "summary": {
                    "total": len(decisions),
                    "confirmed": confirmed,
                    "incorrect": incorrect,
                    "unverifiable": unverifiable,
                },
            }, ensure_ascii=False, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Error: Unknown tool {name}")]

    except UpstreamUnavailable as e:
        logger.warning("Upstream unavailable for tool %s: %s", name, e)
        return [types.TextContent(type="text", text=json.dumps({
            "error": str(e),
            "suggestion": "Sursa primara (legislatie.just.ro) este temporar indisponibila. Folositi lege5_search/lege5_fetch_document direct, sau accesati manual https://legislatie.just.ro / https://lege5.ro / https://www.ccr.ro",
            "upstream_unavailable": True,
        }, ensure_ascii=False))]
    except Exception as e:
        logger.exception("Tool error: %s", e)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def run():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
