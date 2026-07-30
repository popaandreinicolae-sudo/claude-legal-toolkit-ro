"""Client lege5.ro — acces la legislatie, jurisprudenta, doctrina (Playwright).

lege5.ro randeaza rezultatele cautarii in client (JavaScript), deci un client HTTP
simplu primea o pagina goala. Folosim sesiunea browser (auth.Lege5Session): pagina
de cautare e randata complet, apoi extragem linkurile catre documente (/Gratuit/{slug}
sau /App/Document/{slug}). Documentele partajeaza acelasi slug cu lege6.ro.
"""

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

from auth import Lege5Session, LEGE5_BASE

logger = logging.getLogger("legal-verificator.lege5")

# Search_SectionTypeId in cautarea lege5.
SECTION_TYPE = {
    "legislatie": 1,
    "jurisprudenta": 2,
    "doctrina": 157,
    "ccr": 98,
}

_DOC_RE = re.compile(r"/(?:Gratuit|App/Document)/([^/?&#]+)", re.IGNORECASE)


def _doc_slug(href: str) -> str:
    m = _DOC_RE.search(href)
    return m.group(1) if m else ""


def _parse_results(html: str, max_results: int) -> list:
    soup = BeautifulSoup(html, "html.parser")
    by_slug = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        slug = _doc_slug(href)
        if not slug:
            continue
        text = a.get_text(strip=True)
        if not text or len(text) < 8:
            continue
        full = href if href.startswith("http") else f"{LEGE5_BASE}{href}"
        cur = by_slug.get(slug)
        if cur is None:
            by_slug[slug] = {"title": text, "url": full, "slug": slug, "source": "lege5.ro"}
        elif len(text) > len(cur["title"]):
            cur["title"] = text
            cur["url"] = full
    return list(by_slug.values())[:max_results]


async def search(session: Lege5Session, query: str,
                 category=None, max_results: int = 10) -> dict:
    """Cautare full-text pe lege5.ro (pagina SPA randata in browser)."""
    # Login best-effort: cautarea functioneaza si pe free tier.
    await session.ensure_authenticated()

    section = SECTION_TYPE.get(category) if category else None
    url = f"{LEGE5_BASE}/Search?Search_Term={quote(query)}&Rec={max(max_results, 10)}"
    if section is not None:
        url += f"&Search_SectionTypeId={section}"

    try:
        html = await session.goto_rendered_html(url, wait_ms=5500)
    except Exception as e:
        logger.error("lege5 search error: %s", e)
        return {"results": [], "total": 0, "source": "lege5.ro", "error": str(e)}

    results = _parse_results(html, max_results)
    for r in results:
        r["category"] = category or "all"
    return {"results": results, "total": len(results), "source": "lege5.ro"}


# Fara cont, lege5 serveste forma publicata initial in Monitorul Oficial si o anunta
# printr-un banner in corpul actului. Textul arata ca orice alt text de lege, deci
# lipsa modificarilor ulterioare nu se vede la citire: pe 30 iulie 2026, art. 1 din
# Legea nr. 232/2016 a venit de aici fara alin. (3), introdus in 2022.
_BANNER_NECONSOLIDAT = "nu include posibile modificări ulterioare"


async def fetch_document(session: Lege5Session, url: str) -> dict:
    """Descarca textul integral al unui document de pe lege5.ro."""
    await session.ensure_authenticated()
    doc = await session.goto_text(url)
    text = doc.get("text", "")
    iesire = {
        "text": text,
        "title": doc.get("title", ""),
        "url": doc.get("url", url),
        "source": "lege5.ro",
    }
    if _BANNER_NECONSOLIDAT in text:
        iesire["forma"] = "neconsolidata"
        iesire["avertisment"] = (
            "Text servit fara cont, in forma publicata initial in Monitorul Oficial, "
            "fara modificarile ulterioare. NU citi din el forma in vigoare si nu "
            "concluziona ca un alineat lipseste. Verifica pe sintact.ro."
        )
    return iesire


async def search_ccr_decision(session: Lege5Session, number: int, year: int) -> dict:
    """Cauta o decizie CCR pe lege5.ro."""
    token = f"{number}/{year}"
    for query, category in [
        (f"Decizia {number}/{year} Curtea Constitutionala", "ccr"),
        (f"Decizia nr. {number}/{year}", None),
    ]:
        result = await search(session, query, category=category, max_results=8)
        for r in result.get("results", []):
            title_norm = re.sub(r"\s+", " ", r["title"])
            if token in title_norm.replace(" ", "") and "deciz" in title_norm.lower()[:12]:
                return {"found": True, "title": r["title"], "url": r["url"], "source": "lege5.ro"}
    return {"found": False, "source": "lege5.ro"}


async def fetch_ccr_text(session: Lege5Session, number: int, year: int) -> dict:
    """Descarca textul integral al unei decizii CCR de pe lege5.ro."""
    result = await search_ccr_decision(session, number, year)
    if not result.get("found"):
        return {"text": "", "source": "lege5.ro", "total_chars": 0, "truncated": False,
                "error": f"Decizia CCR nr. {number}/{year} nu a fost gasita pe lege5.ro."}
    doc = await fetch_document(session, result["url"])
    text = doc.get("text", "")
    total_chars = len(text)
    truncated = False
    if total_chars > 30000:
        text = text[:15000] + "\n\n[...TRUNCAT...]\n\n" + text[-5000:]
        truncated = True
    return {"text": text, "source": "lege5.ro", "total_chars": total_chars,
            "truncated": truncated, "url": result["url"], "title": result.get("title", "")}
