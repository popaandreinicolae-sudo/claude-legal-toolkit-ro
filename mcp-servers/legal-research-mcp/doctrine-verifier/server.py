"""
Doctrine Verifier MCP — verifies academic citations via CrossRef, OpenAlex, Google Books.
Covers international AND Romanian doctrine that Semantic Scholar misses.
Free APIs, no auth required.
"""

import asyncio
import json
import sys
import logging
import re
from typing import Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("doctrine-verifier")

app = Server("doctrine-verifier")
_last = 0.0


async def _get(url, params=None, headers=None):
    global _last
    wait = max(0, 1.0 - (asyncio.get_event_loop().time() - _last))
    if wait > 0:
        await asyncio.sleep(wait)
    _last = asyncio.get_event_loop().time()

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params, headers=headers or {"User-Agent": "LegalResearchMCP/1.0"})
                if resp.status_code == 429:
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
                # 404 = identificatorul nu exista, un raspuns valid al sursei.
                # Nu il reincercam si nu il propagam ca eroare de retea: apelantul
                # trebuie sa poata distinge "inventat" de "sursa indisponibila".
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                raise
    return {}


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="crossref_search",
            description="Cauta articole/carti pe CrossRef (100M+ lucrari). Verifica DOI, autori, titlu, an, jurnal, editura.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Titlu sau autori de cautat"},
                    "author": {"type": "string", "description": "Numele autorului (optional)"},
                    "title": {"type": "string", "description": "Titlul exact (optional)"},
                    "doi": {"type": "string", "description": "DOI de verificat (optional)"},
                    "limit": {"type": "integer", "description": "Max rezultate (default 5)"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="crossref_verify_doi",
            description="Verifica un DOI si returneaza metadatele complete (titlu, autori, an, jurnal, pagini).",
            inputSchema={
                "type": "object",
                "properties": {
                    "doi": {"type": "string", "description": "DOI-ul de verificat (ex: 10.1016/j.clsr.2024.105912)"},
                },
                "required": ["doi"],
            },
        ),
        types.Tool(
            name="openalex_search",
            description="Cauta pe OpenAlex (250M+ lucrari academice). Acopera si jurnale europene/romanesti.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de cautare"},
                    "author": {"type": "string", "description": "Filtru autor (optional)"},
                    "year_from": {"type": "integer", "description": "An minim"},
                    "year_to": {"type": "integer", "description": "An maxim"},
                    "limit": {"type": "integer", "description": "Max rezultate (default 10)"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="google_books_search",
            description="Cauta carti pe Google Books. Util pentru doctrina romaneasca (Muraru, Tanasescu, Deleanu, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Titlu, autor sau ISBN"},
                    "author": {"type": "string", "description": "Filtru autor (optional)"},
                    "isbn": {"type": "string", "description": "ISBN de verificat (optional)"},
                    "limit": {"type": "integer", "description": "Max rezultate (default 5)"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="verify_citation",
            description="Verifica o citare bibliografica complet: cauta pe CrossRef + OpenAlex + Google Books simultan. Returneaza CONFIRMED/PARTIAL/NOT_FOUND.",
            inputSchema={
                "type": "object",
                "properties": {
                    "author": {"type": "string", "description": "Autor(i)"},
                    "title": {"type": "string", "description": "Titlul lucrarii"},
                    "year": {"type": "integer", "description": "Anul publicarii"},
                    "journal": {"type": "string", "description": "Revista/jurnal (optional)"},
                    "publisher": {"type": "string", "description": "Editura (optional)"},
                    "pages": {"type": "string", "description": "Paginile citate (optional)"},
                },
                "required": ["author", "title"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "crossref_search":
            params = {"rows": min(arguments.get("limit", 5), 20)}
            if arguments.get("doi"):
                data = await _get(f"https://api.crossref.org/works/{arguments['doi']}")
                item = data.get("message", {})
                return [types.TextContent(type="text", text=json.dumps({
                    "title": " ".join(item.get("title", [])),
                    "authors": [f"{a.get('given','')} {a.get('family','')}" for a in item.get("author", [])],
                    "year": item.get("published", {}).get("date-parts", [[None]])[0][0],
                    "journal": " ".join(item.get("container-title", [])),
                    "doi": item.get("DOI", ""),
                    "publisher": item.get("publisher", ""),
                    "pages": item.get("page", ""),
                    "type": item.get("type", ""),
                }, ensure_ascii=False, indent=2))]

            q_parts = []
            if arguments.get("query"):
                q_parts.append(arguments["query"])
            if arguments.get("author"):
                params["query.author"] = arguments["author"]
            if arguments.get("title"):
                params["query.title"] = arguments["title"]
            params["query"] = " ".join(q_parts) if q_parts else arguments.get("title", "")

            data = await _get("https://api.crossref.org/works", params)
            items = data.get("message", {}).get("items", [])
            results = []
            for item in items:
                results.append({
                    "title": " ".join(item.get("title", [])),
                    "authors": [f"{a.get('given','')} {a.get('family','')}" for a in item.get("author", [])],
                    "year": (item.get("published") or item.get("created", {})).get("date-parts", [[None]])[0][0],
                    "journal": " ".join(item.get("container-title", [])),
                    "doi": item.get("DOI", ""),
                    "publisher": item.get("publisher", ""),
                    "type": item.get("type", ""),
                })
            return [types.TextContent(type="text", text=json.dumps({"count": len(results), "results": results}, ensure_ascii=False, indent=2))]

        elif name == "crossref_verify_doi":
            doi = arguments["doi"].strip()
            for prefix in ("doi:", "DOI:", "https://doi.org/", "http://doi.org/", "https://dx.doi.org/"):
                if doi.startswith(prefix):
                    doi = doi[len(prefix):]
                    break
            data = await _get(f"https://api.crossref.org/works/{doi}")
            if not data:
                return [types.TextContent(type="text", text=json.dumps({
                    "verified": False, "status": "NEGASIT", "doi": doi,
                    "warning": "DOI inexistent pe CrossRef, posibil inventat.",
                }, ensure_ascii=False, indent=2))]
            item = data.get("message", {})
            return [types.TextContent(type="text", text=json.dumps({
                "verified": True,
                "title": " ".join(item.get("title", [])),
                "authors": [f"{a.get('given','')} {a.get('family','')}" for a in item.get("author", [])],
                "year": (item.get("published") or {}).get("date-parts", [[None]])[0][0],
                "journal": " ".join(item.get("container-title", [])),
                "doi": item.get("DOI", ""),
                "publisher": item.get("publisher", ""),
                "pages": item.get("page", ""),
                "isbn": item.get("ISBN", []),
                "issn": item.get("ISSN", []),
                "url": item.get("URL", ""),
            }, ensure_ascii=False, indent=2))]

        elif name == "openalex_search":
            params = {
                "search": arguments["query"],
                "per_page": min(arguments.get("limit", 10), 25),
            }
            if arguments.get("year_from") and arguments.get("year_to"):
                params["filter"] = f"publication_year:{arguments['year_from']}-{arguments['year_to']}"
            elif arguments.get("year_from"):
                params["filter"] = f"publication_year:{arguments['year_from']}-2026"

            data = await _get("https://api.openalex.org/works", params)
            results = []
            for w in data.get("results", []):
                auths = [(a.get("author") or {}).get("display_name", "") for a in (w.get("authorships") or [])]
                results.append({
                    "title": w.get("title", ""),
                    "authors": auths,
                    "year": w.get("publication_year"),
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                    "citations": w.get("cited_by_count", 0),
                    "open_access": w.get("open_access", {}).get("is_oa", False),
                    "url": w.get("id", ""),
                })
            return [types.TextContent(type="text", text=json.dumps({"total": data.get("meta", {}).get("count", 0), "results": results}, ensure_ascii=False, indent=2))]

        elif name == "google_books_search":
            q = arguments["query"]
            if arguments.get("author"):
                q += f"+inauthor:{arguments['author']}"
            if arguments.get("isbn"):
                q += f"+isbn:{arguments['isbn']}"
            params = {"q": q, "maxResults": min(arguments.get("limit", 5), 10)}

            data = await _get("https://www.googleapis.com/books/v1/volumes", params)
            results = []
            for item in data.get("items", []):
                v = item.get("volumeInfo", {})
                results.append({
                    "title": v.get("title", ""),
                    "authors": v.get("authors", []),
                    "year": v.get("publishedDate", "")[:4] if v.get("publishedDate") else None,
                    "publisher": v.get("publisher", ""),
                    "isbn": [i.get("identifier", "") for i in v.get("industryIdentifiers", [])],
                    "pages": v.get("pageCount"),
                    "language": v.get("language", ""),
                    "description": (v.get("description") or "")[:300],
                })
            return [types.TextContent(type="text", text=json.dumps({"total": data.get("totalItems", 0), "results": results}, ensure_ascii=False, indent=2))]

        elif name == "verify_citation":
            author = arguments["author"]
            title = arguments["title"]
            year = arguments.get("year")
            results = {"crossref": None, "openalex": None, "google_books": None}

            # CrossRef
            try:
                cr = await _get("https://api.crossref.org/works", {"query.title": title, "query.author": author, "rows": 3})
                items = cr.get("message", {}).get("items", [])
                if items:
                    best = items[0]
                    results["crossref"] = {
                        "title": " ".join(best.get("title", [])),
                        "authors": [f"{a.get('given','')} {a.get('family','')}" for a in best.get("author", [])],
                        "year": (best.get("published") or best.get("created", {})).get("date-parts", [[None]])[0][0],
                        "doi": best.get("DOI", ""),
                    }
            except Exception:
                pass

            # OpenAlex
            try:
                oa = await _get("https://api.openalex.org/works", {"search": f"{author} {title}", "per_page": 3})
                if oa.get("results"):
                    best = oa["results"][0]
                    results["openalex"] = {
                        "title": best.get("title", ""),
                        "authors": [(a.get("author") or {}).get("display_name", "") for a in (best.get("authorships") or [])],
                        "year": best.get("publication_year"),
                        "doi": (best.get("doi") or "").replace("https://doi.org/", ""),
                    }
            except Exception:
                pass

            # Google Books
            try:
                gb = await _get("https://www.googleapis.com/books/v1/volumes", {"q": f"{title}+inauthor:{author}", "maxResults": 3})
                if gb.get("items"):
                    v = gb["items"][0].get("volumeInfo", {})
                    results["google_books"] = {
                        "title": v.get("title", ""),
                        "authors": v.get("authors", []),
                        "year": v.get("publishedDate", "")[:4] if v.get("publishedDate") else None,
                        "publisher": v.get("publisher", ""),
                    }
            except Exception:
                pass

            # Determine verdict
            found_count = sum(1 for v in results.values() if v is not None)
            if found_count >= 2:
                verdict = "CONFIRMED"
            elif found_count == 1:
                verdict = "PARTIAL"
            else:
                verdict = "NOT_FOUND"

            return [types.TextContent(type="text", text=json.dumps({
                "verdict": verdict,
                "sources_checked": 3,
                "sources_found": found_count,
                "query": {"author": author, "title": title, "year": year},
                "results": results,
            }, ensure_ascii=False, indent=2))]

        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.exception("Error: %s", e)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], _optiuni_cu_instructiuni(app))

MCP_INSTRUCTIONS = """Verifica daca o lucrare de doctrina exista cu adevarat, prin Crossref, OpenAlex si Google Books. Foloseste-l inainte de a cita o carte, un articol sau un DOI intr-un act sau intr-o lucrare academica, fiindca titlurile plauzibile inventate sunt eroarea dominanta la citarea de doctrina. Harta completa de rutare a toolkit-ului sta in instructiunile serverului legal-verificator-ro."""


def _optiuni_cu_instructiuni(app):
    """Ataseaza instructiunile de folosire la raspunsul de initialize.

    Campul `instructions` din MCP este locul standardizat prin care serverul isi
    spune singur cand trebuie folosit. Conteaza pe suprafetele unde regulile din
    ~/.claude/CLAUDE.md nu ajung, adica in Claude Desktop.
    """
    optiuni = app.create_initialization_options()
    optiuni.instructions = MCP_INSTRUCTIONS
    return optiuni


if __name__ == "__main__":
    asyncio.run(main())
