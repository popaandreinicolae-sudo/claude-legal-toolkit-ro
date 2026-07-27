"""Client sintact.ro — Wolters Kluwer Romania: legislatie, jurisprudenta, doctrina.

Sintact expune un API JSON intern (verificat live iulie 2026, apelat dintr-o sesiune
Playwright autentificata, vezi auth.SintactSession):
  - POST /api/search.direct.hit.get.json  -> gaseste un act/decizie EXACT dupa citare
    (ex. "Legea 190/2018", "Decizia 22/2020"); daca nu exista, nu intoarce nro/versionId.
  - POST /api/searchResults.get.json      -> cautare full-text, lista de documente cu
    lawType ("Lege", "OUG", "Decizie", ...), validity ("ACTUAL"/altele), fragmente.
  - GET  /api/act.get.json?nro=..&versionId=..  -> continutul XHTML integral al actului.

Sintact NU are un parametru documentat de filtrare server-side dupa categorie in
payloadul de cautare; filtrarea legislatie/jurisprudenta/doctrina se face client-side
dupa lawType, dupa rezultatele reale observate (Lege/OUG/OG/HG/Cod = legislatie,
Decizie = jurisprudenta inclusiv CCR/ICCJ/CEDO).
"""

import logging
import re
from datetime import date
from html import unescape

from bs4 import BeautifulSoup

from auth import SintactSession, SINTACT_BASE

logger = logging.getLogger("legal-verificator.sintact")

SEARCH_URL = f"{SINTACT_BASE}/api/searchResults.get.json"
DIRECT_HIT_URL = f"{SINTACT_BASE}/api/search.direct.hit.get.json"
ACT_URL = f"{SINTACT_BASE}/api/act.get.json"

_LEGISLATION_TYPES = {"lege", "oug", "og", "ordonanta de urgenta", "ordonanta", "hg",
                      "hotararea guvernului", "cod", "constitutie", "ordin", "regulament", "directiva"}
_JURISPRUDENCE_TYPES = {"decizie"}


def _point_in_time() -> str:
    """Data de referinta a versiunii legislative ceruta de API (formatul folosit de
    aplicatia web: YYYY-MM-DD). Fara acest camp, POST-urile intorc raspuns gol."""
    return date.today().isoformat()


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _doc_url(nro: int, version_id: int) -> str:
    return f"{SINTACT_BASE}/#/act/{nro}/{version_id}"


def _map_doc(d: dict) -> dict:
    law_type = (d.get("lawType") or "").strip()
    category = ("jurisprudenta" if law_type.lower() in _JURISPRUDENCE_TYPES
                else "legislatie" if law_type.lower() in _LEGISLATION_TYPES
                else "doctrina" if d.get("resourceType") == "MONOGRAPH_FRAGMENT"
                else "altele")
    snippets = [_strip_tags(s.get("snippet", "")) for s in (d.get("snippetWithLink") or [])]
    return {
        "title": _strip_tags(d.get("title", "")),
        "lawType": law_type,
        "category": category,
        "validity": d.get("validity", ""),
        "nro": d.get("nro"),
        "versionId": d.get("versionId"),
        "url": _doc_url(d.get("nro"), d.get("versionId")) if d.get("nro") else "",
        "snippets": [s for s in snippets if s][:3],
        "source": "sintact.ro",
    }


async def search(session: SintactSession, query: str, category: str = None,
                  max_results: int = 10, start_from: int = 0) -> dict:
    """Cautare full-text pe sintact.ro prin API-ul intern, sesiune autentificata."""
    if not await session.ensure_authenticated():
        return {"results": [], "total": 0, "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata. Verifica SINTACT_EMAIL/SINTACT_PASSWORD in .env."}

    body = {
        "searchLang": "RO",
        "queryString": query,
        "startFrom": start_from,
        "sortBy": "DEFAULT",
        "pointInTime": _point_in_time(),
        "analyzer": False,
        "showMeAutoThesis": False,
        "hitsPp": max(max_results, 10),
    }
    try:
        data = await session.post_json(SEARCH_URL, body)
    except Exception as e:
        logger.error("sintact search error: %s", e)
        return {"results": [], "total": 0, "source": "sintact.ro", "error": str(e)}

    docs = [_map_doc(d) for d in (data.get("documentList") or [])]
    if category:
        docs = [d for d in docs if d["category"] == category]
    return {"results": docs[:max_results], "total": len(docs), "source": "sintact.ro"}


async def verify_citation(session: SintactSession, query: str) -> dict:
    """Verifica daca o citare (lege, decizie, articol) e REALA pe sintact.ro, prin
    API-ul de 'direct hit' pe care platforma il foloseste pentru cautari exacte de
    genul 'Legea 190/2018' sau 'Decizia 22/2020'. Nu returneaza nro/versionId daca
    citarea nu se potriveste unui document real."""
    if not await session.ensure_authenticated():
        return {"status": "EROARE", "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata. Verifica SINTACT_EMAIL/SINTACT_PASSWORD in .env."}

    try:
        data = await session.post_json(DIRECT_HIT_URL,
                                       {"queryString": query, "pointInTime": _point_in_time()})
    except Exception as e:
        logger.error("sintact direct-hit error: %s", e)
        return {"status": "EROARE", "source": "sintact.ro", "error": str(e)}

    nro = data.get("nro")
    version_id = data.get("versionId")
    if not nro or not version_id:
        # Fallback: cautare full-text, verifica daca primul rezultat e o potrivire
        # exacta de titlu (unele decizii/coduri nu au "direct hit" desi exista).
        fallback = await search(session, query, max_results=3)
        for r in fallback.get("results", []):
            if query.strip().lower() in r["title"].lower():
                return {"status": "CONFIRMAT", "title": r["title"], "url": r["url"],
                        "validity": r["validity"], "nro": r["nro"], "versionId": r["versionId"],
                        "source": "sintact.ro", "via": "search_fallback"}
        return {"status": "NEGASIT", "query": query, "source": "sintact.ro",
                "warning": "Nicio potrivire exacta pe sintact.ro, posibil citare inventata sau formulata gresit."}

    doc = await fetch_document(session, nro, version_id)
    return {"status": "CONFIRMAT", "title": doc.get("title", ""), "url": _doc_url(nro, version_id),
            "nro": nro, "versionId": version_id, "source": "sintact.ro", "via": "direct_hit"}


async def fetch_document(session: SintactSession, nro: int, version_id: int) -> dict:
    """Descarca textul integral al unui document de pe sintact.ro (act, decizie)."""
    if not await session.ensure_authenticated():
        return {"text": "", "title": "", "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata."}

    url = f"{ACT_URL}?nro={nro}&versionId={version_id}&translation=RO"
    try:
        data = await session.fetch_json(url)
    except Exception as e:
        logger.error("sintact fetch_document error: %s", e)
        return {"text": "", "title": "", "source": "sintact.ro", "error": str(e)}

    title = data.get("title", "")
    content_html = data.get("content", "")
    text = ""
    if content_html:
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text("\n", strip=True)
    return {
        "title": title,
        "text": text,
        "url": _doc_url(nro, version_id),
        "source": "sintact.ro",
    }
