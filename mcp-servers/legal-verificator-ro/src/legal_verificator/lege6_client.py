"""Client lege6.ro — acces autentificat la legislatie, jurisprudenta, doctrina.

Lege6.ro este platforma Indaco moderna care inlocuieste lege5.ro. Cautarea se face
prin API-ul intern JSON al platformei (getsearchresults), apelat dintr-o sesiune
logata cu browser (vezi auth.Lege6Session). API-ul intoarce un tabel HTML cu
rezultate; documentele sunt la /app/document/{slug}/...
"""

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from auth import Lege6Session, LEGE6_BASE

logger = logging.getLogger("legal-verificator.lege6")

# regionId = tipul sectiunii in cautarea lege6 (descoperit din API-ul live).
SECTION_REGION = {
    "legislatie": 1,
    "jurisprudenta": 2,
    "doctrina": 6,
    "ccr": 98,
}

SEARCH_API = f"{LEGE6_BASE}/api/services/app/search/getsearchresults"


def _doc_slug(href: str) -> str:
    m = re.search(r"/app/document/([^/?&#]+)", href)
    return m.group(1) if m else ""


def _parse_results(html: str, max_results: int) -> list:
    """Extrage documente distincte din tabelul HTML al cautarii lege6."""
    soup = BeautifulSoup(html, "html.parser")
    by_slug = {}
    # Pastreaza ordinea de relevanta a API-ului (primul rezultat = cel mai relevant);
    # per document retine ancora cu titlul cel mai descriptiv (linkul principal).
    for a in soup.find_all("a", href=True):
        href = a["href"]
        slug = _doc_slug(href)
        if not slug:
            continue
        text = a.get_text(strip=True)
        if not text:
            continue
        full = href if href.startswith("http") else f"{LEGE6_BASE}{href}"
        cur = by_slug.get(slug)
        if cur is None:
            by_slug[slug] = {"title": text, "url": full, "slug": slug, "source": "lege6.ro"}
        elif len(text) > len(cur["title"]):
            cur["title"] = text
            cur["url"] = full
    return list(by_slug.values())[:max_results]


async def search(session: Lege6Session, query: str,
                 category=None, max_results: int = 10) -> dict:
    """Cautare full-text pe lege6.ro prin API-ul intern, sesiune autentificata."""
    if not await session.ensure_authenticated():
        return {"results": [], "total": 0, "source": "lege6.ro",
                "error": "Autentificare lege6.ro esuata. Verifica LEGE6_EMAIL/LEGE6_PASSWORD in .env."}

    region = SECTION_REGION.get(category) if category else None
    url = (f"{SEARCH_API}?searchTerm={quote(query)}"
           f"&page=1&recordsPerPage={max(max_results, 10)}&searchType=0")
    if region is not None:
        url += f"&regionId={region}"

    try:
        data = await session.fetch_json(url)
    except Exception as e:
        logger.error("lege6 search error: %s", e)
        return {"results": [], "total": 0, "source": "lege6.ro", "error": str(e)}

    result = data.get("result") or {}
    html = result.get("htmlResults", "") if isinstance(result, dict) else ""
    if not html:
        return {"results": [], "total": 0, "source": "lege6.ro"}

    results = _parse_results(html, max_results)
    for r in results:
        r["category"] = category or "all"
    return {"results": results, "total": len(results), "source": "lege6.ro"}


async def fetch_document(session: Lege6Session, url: str) -> dict:
    """Descarca textul integral al unui document de pe lege6.ro."""
    if not await session.ensure_authenticated():
        return {"text": "", "title": "", "source": "lege6.ro",
                "error": "Autentificare lege6.ro esuata."}
    doc = await session.goto_text(url)
    return {
        "text": doc.get("text", ""),
        "title": doc.get("title", ""),
        "url": doc.get("url", url),
        "source": "lege6.ro",
    }


async def search_ccr_decision(session: Lege6Session, number: int, year: int) -> dict:
    """Cauta o decizie CCR pe lege6.ro."""
    queries = [
        (f"Decizia {number}/{year} Curtea Constitutionala", "ccr"),
        (f"Decizia nr. {number}/{year}", None),
        (f"DCC {number}/{year}", "jurisprudenta"),
    ]
    token = f"{number}/{year}"
    for query, category in queries:
        result = await search(session, query, category=category, max_results=8)
        for r in result.get("results", []):
            title_norm = re.sub(r"\s+", " ", r["title"])
            if token in title_norm.replace(" ", "") and "deciz" in title_norm.lower()[:12]:
                return {"found": True, "title": r["title"], "url": r["url"], "source": "lege6.ro"}
    return {"found": False, "source": "lege6.ro"}


async def fetch_ccr_text(session: Lege6Session, number: int, year: int) -> dict:
    """Descarca textul integral al unei decizii CCR de pe lege6.ro."""
    result = await search_ccr_decision(session, number, year)
    if not result.get("found"):
        return {"text": "", "source": "lege6.ro", "total_chars": 0, "truncated": False,
                "error": f"Decizia CCR nr. {number}/{year} nu a fost gasita pe lege6.ro."}

    doc = await fetch_document(session, result["url"])
    text = doc.get("text", "")
    total_chars = len(text)
    truncated = False
    if total_chars > 30000:
        text = text[:15000] + "\n\n[...TRUNCAT...]\n\n" + text[-5000:]
        truncated = True
    return {"text": text, "source": "lege6.ro", "total_chars": total_chars,
            "truncated": truncated, "url": result["url"], "title": result.get("title", "")}


async def search_legislation(session: Lege6Session, act_type: str, number: int, year: int) -> dict:
    """Cauta un act normativ pe lege6.ro dupa tip, numar, an."""
    type_map = {
        "lege": "Legea", "oug": "Ordonanta de urgenta", "og": "Ordonanta",
        "hg": "Hotararea Guvernului", "ordin": "Ordin", "cod": "Codul",
        "constitutie": "Constitutia", "constituție": "Constitutia",
    }
    act_name = type_map.get(act_type.lower(), act_type)
    query = f"{act_name} {number}/{year}"
    result = await search(session, query, category="legislatie", max_results=8)
    token = f"{number}/{year}"
    act_first = act_name.split()[0].lower()
    for r in result.get("results", []):
        title = r["title"]
        title_norm = re.sub(r"\s+", " ", title)
        # Tokenul exact "numar/an" SI titlul incepe cu tipul actului (evita deciziile
        # CCR care doar mentioneaza legea in titlu).
        if token in title_norm.replace(" ", "") and act_first in title_norm.lower()[:25]:
            title_lower = title.lower()
            status = "in_vigoare"
            if "abrogat" in title_lower:
                status = "abrogat"
            elif "modificat" in title_lower or "republicat" in title_lower:
                status = "modificat"
            return {"found": True, "title": r["title"], "url": r["url"],
                    "status": status, "source": "lege6.ro"}
    return {"found": False, "source": "lege6.ro"}
