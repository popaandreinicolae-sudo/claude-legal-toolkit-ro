"""
Semantic Scholar MCP Server — academic paper search, citation network, author lookup.
API: https://api.semanticscholar.org/graph/v1 (free, no auth required, 100 req/5min)
"""

import asyncio
import json
import os
import sys
import logging
from typing import Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger("semantic-scholar")

app = Server("semantic-scholar")
BASE = "https://api.semanticscholar.org/graph/v1"
HEADERS = {"User-Agent": "LegalResearchMCP/1.0"}
_last_request = 0.0

CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "")
_crossref_last_request = 0.0


async def _rate_limited_get(url, params=None):
    global _last_request
    wait = max(0, 3.0 - (asyncio.get_event_loop().time() - _last_request))
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params, headers=HEADERS)
                if resp.status_code == 429:
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt < 2:
                    await asyncio.sleep(3)
                    continue
                raise
    return {}


async def _crossref_get(path, params=None):
    """GET catre CrossREST API. Foloseste 'polite pool' daca CROSSREF_MAILTO e setat
    (rate-limit mai relaxat), altfel merge anonim, fara autentificare."""
    global _crossref_last_request
    wait = max(0, 1.0 - (asyncio.get_event_loop().time() - _crossref_last_request))
    if wait > 0:
        await asyncio.sleep(wait)
    _crossref_last_request = asyncio.get_event_loop().time()

    params = dict(params or {})
    ua = "LegalResearchMCP/1.0 (mailto:%s)" % CROSSREF_MAILTO if CROSSREF_MAILTO else "LegalResearchMCP/1.0"
    headers = {"User-Agent": ua}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(f"{CROSSREF_BASE}{path}", params=params, headers=headers)
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    await asyncio.sleep(10 * (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt < 2:
                    await asyncio.sleep(3)
                    continue
                raise
    return None


def _crossref_item_summary(item: dict) -> dict:
    date_parts = ((item.get("issued") or {}).get("date-parts") or [[None]])[0]
    authors = item.get("author") or []
    return {
        "doi": item.get("DOI", ""),
        "title": (item.get("title") or [""])[0],
        "authors": [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors],
        "year": date_parts[0] if date_parts else None,
        "container_title": (item.get("container-title") or [""])[0],
        "publisher": item.get("publisher", ""),
        "type": item.get("type", ""),
        "url": item.get("URL", ""),
    }


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="scholar_search",
            description="Cauta articole academice pe Semantic Scholar. Returneaza titlu, autori, an, abstract, citari, DOI, URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de cautare (in engleza pentru rezultate mai bune)"},
                    "year_from": {"type": "integer", "description": "An minim (optional)"},
                    "year_to": {"type": "integer", "description": "An maxim (optional)"},
                    "fields_of_study": {"type": "string", "description": "Domeniu: Law, Computer Science, Political Science, etc."},
                    "open_access_only": {"type": "boolean", "description": "Doar articole open access (default: false)"},
                    "limit": {"type": "integer", "description": "Numar maxim rezultate (default 10, max 100)"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="scholar_paper_details",
            description="Detalii complete despre un articol: abstract, autori, referinte, citari, DOI, PDF link.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Semantic Scholar paper ID, DOI (DOI:10.xxx), arXiv ID (ARXIV:xxx), sau URL"},
                },
                "required": ["paper_id"],
            },
        ),
        types.Tool(
            name="scholar_citations",
            description="Lista articolelor care citeaza un paper dat (cine il citeaza).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper ID sau DOI"},
                    "limit": {"type": "integer", "description": "Numar maxim (default 20)"},
                },
                "required": ["paper_id"],
            },
        ),
        types.Tool(
            name="scholar_references",
            description="Lista referintelor unui paper (ce citeaza el).",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper ID sau DOI"},
                    "limit": {"type": "integer", "description": "Numar maxim (default 20)"},
                },
                "required": ["paper_id"],
            },
        ),
        types.Tool(
            name="scholar_author",
            description="Cauta un autor academic si returneaza publicatiile, h-index, afiliere.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Numele autorului (ex: 'Giovanni De Gregorio')"},
                    "limit": {"type": "integer", "description": "Numar maxim rezultate (default 5)"},
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="scholar_recommendations",
            description="Recomandari de articole similare pe baza unui paper dat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string", "description": "Paper ID sau DOI"},
                    "limit": {"type": "integer", "description": "Numar maxim (default 10)"},
                },
                "required": ["paper_id"],
            },
        ),
        types.Tool(
            name="crossref_verify_doi",
            description="Verifica daca un DOI exista cu adevarat, prin CrossRef (registrul oficial de DOI-uri). Returneaza titlu, autori, an, publicatie sau 'NEGASIT' daca DOI-ul e inventat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {"type": "string", "description": "DOI de verificat, cu sau fara prefixul 'doi:' sau URL (ex: 10.1093/acprof:oso/9780199662463.003.0002)"},
                },
                "required": ["doi"],
            },
        ),
        types.Tool(
            name="crossref_search",
            description="Cauta o lucrare in CrossRef dupa titlu/autor/referinta bibliografica, pentru cazul in care nu ai DOI-ul dar vrei sa confirmi ca lucrarea citata chiar exista.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Titlu, autor sau referinta bibliografica de cautat"},
                    "limit": {"type": "integer", "description": "Numar maxim rezultate (default 5, max 20)"},
                },
                "required": ["query"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "scholar_search":
            query = arguments["query"]
            limit = min(arguments.get("limit", 10), 100)
            params = {
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,abstract,citationCount,url,externalIds,openAccessPdf,publicationTypes,journal",
            }
            if arguments.get("year_from") or arguments.get("year_to"):
                y_from = arguments.get("year_from", 1900)
                y_to = arguments.get("year_to", 2026)
                params["year"] = f"{y_from}-{y_to}"
            if arguments.get("fields_of_study"):
                params["fieldsOfStudy"] = arguments["fields_of_study"]
            if arguments.get("open_access_only"):
                params["openAccessPdf"] = ""

            data = await _rate_limited_get(f"{BASE}/paper/search", params)
            papers = data.get("data", [])
            results = []
            for p in papers:
                ext = p.get("externalIds", {}) or {}
                results.append({
                    "title": p.get("title", ""),
                    "authors": [a.get("name", "") for a in (p.get("authors") or [])],
                    "year": p.get("year"),
                    "citations": p.get("citationCount", 0),
                    "abstract": (p.get("abstract") or "")[:500],
                    "doi": ext.get("DOI", ""),
                    "url": p.get("url", ""),
                    "pdf": (p.get("openAccessPdf") or {}).get("url", ""),
                    "journal": (p.get("journal") or {}).get("name", ""),
                    "paperId": p.get("paperId", ""),
                })
            return [types.TextContent(type="text", text=json.dumps({"total": data.get("total", 0), "results": results}, ensure_ascii=False, indent=2))]

        elif name == "scholar_paper_details":
            pid = arguments["paper_id"]
            fields = "title,authors,year,abstract,citationCount,referenceCount,url,externalIds,openAccessPdf,publicationTypes,journal,fieldsOfStudy,tldr"
            data = await _rate_limited_get(f"{BASE}/paper/{pid}", {"fields": fields})
            ext = data.get("externalIds", {}) or {}
            result = {
                "title": data.get("title", ""),
                "authors": [a.get("name", "") for a in (data.get("authors") or [])],
                "year": data.get("year"),
                "abstract": data.get("abstract", ""),
                "tldr": (data.get("tldr") or {}).get("text", ""),
                "citations": data.get("citationCount", 0),
                "references": data.get("referenceCount", 0),
                "doi": ext.get("DOI", ""),
                "url": data.get("url", ""),
                "pdf": (data.get("openAccessPdf") or {}).get("url", ""),
                "journal": (data.get("journal") or {}).get("name", ""),
                "fields": data.get("fieldsOfStudy", []),
            }
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "scholar_citations":
            pid = arguments["paper_id"]
            limit = min(arguments.get("limit", 20), 100)
            data = await _rate_limited_get(f"{BASE}/paper/{pid}/citations", {"fields": "title,authors,year,citationCount,url", "limit": limit})
            citing = [{"title": c["citingPaper"].get("title", ""), "authors": [a.get("name", "") for a in (c["citingPaper"].get("authors") or [])], "year": c["citingPaper"].get("year"), "citations": c["citingPaper"].get("citationCount", 0)} for c in data.get("data", [])]
            return [types.TextContent(type="text", text=json.dumps({"total": len(citing), "citing_papers": citing}, ensure_ascii=False, indent=2))]

        elif name == "scholar_references":
            pid = arguments["paper_id"]
            limit = min(arguments.get("limit", 20), 100)
            data = await _rate_limited_get(f"{BASE}/paper/{pid}/references", {"fields": "title,authors,year,citationCount,url", "limit": limit})
            refs = [{"title": r["citedPaper"].get("title", ""), "authors": [a.get("name", "") for a in (r["citedPaper"].get("authors") or [])], "year": r["citedPaper"].get("year"), "citations": r["citedPaper"].get("citationCount", 0)} for r in data.get("data", [])]
            return [types.TextContent(type="text", text=json.dumps({"total": len(refs), "referenced_papers": refs}, ensure_ascii=False, indent=2))]

        elif name == "scholar_author":
            aname = arguments["name"]
            limit = min(arguments.get("limit", 5), 20)
            data = await _rate_limited_get(f"{BASE}/author/search", {"query": aname, "limit": limit, "fields": "name,affiliations,paperCount,citationCount,hIndex,papers.title,papers.year"})
            authors = []
            for a in data.get("data", []):
                authors.append({
                    "name": a.get("name", ""),
                    "affiliations": a.get("affiliations", []),
                    "papers": a.get("paperCount", 0),
                    "citations": a.get("citationCount", 0),
                    "hIndex": a.get("hIndex", 0),
                    "recent_papers": [{"title": p.get("title", ""), "year": p.get("year")} for p in (a.get("papers") or [])[:5]],
                })
            return [types.TextContent(type="text", text=json.dumps({"results": authors}, ensure_ascii=False, indent=2))]

        elif name == "scholar_recommendations":
            pid = arguments["paper_id"]
            limit = min(arguments.get("limit", 10), 50)
            data = await _rate_limited_get(f"{BASE}/recommendations/v1/papers/forpaper/{pid}", {"limit": limit, "fields": "title,authors,year,citationCount,abstract,url"})
            recs = [{"title": p.get("title", ""), "authors": [a.get("name", "") for a in (p.get("authors") or [])], "year": p.get("year"), "citations": p.get("citationCount", 0), "abstract": (p.get("abstract") or "")[:300]} for p in data.get("recommendedPapers", [])]
            return [types.TextContent(type="text", text=json.dumps({"recommendations": recs}, ensure_ascii=False, indent=2))]

        elif name == "crossref_verify_doi":
            doi = arguments["doi"].strip()
            for prefix in ("doi:", "DOI:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/"):
                if doi.startswith(prefix):
                    doi = doi[len(prefix):]
                    break
            data = await _crossref_get(f"/works/{doi}")
            if data is None:
                return [types.TextContent(type="text", text=json.dumps({"doi": doi, "status": "NEGASIT", "warning": "DOI inexistent in registrul CrossRef, posibil inventat sau gresit transcris"}, ensure_ascii=False, indent=2))]
            item = _crossref_item_summary(data.get("message", {}))
            item["status"] = "CONFIRMAT"
            return [types.TextContent(type="text", text=json.dumps(item, ensure_ascii=False, indent=2))]

        elif name == "crossref_search":
            query = arguments["query"]
            limit = min(arguments.get("limit", 5), 20)
            data = await _crossref_get("/works", {"query.bibliographic": query, "rows": limit})
            items = ((data or {}).get("message") or {}).get("items", [])
            results = [_crossref_item_summary(it) for it in items]
            total = ((data or {}).get("message") or {}).get("total-results", len(results))
            return [types.TextContent(type="text", text=json.dumps({"total_results": total, "results": results}, ensure_ascii=False, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.exception("Error: %s", e)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e), "suggestion": "Verificati paper_id sau incercati alt query."}))]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
