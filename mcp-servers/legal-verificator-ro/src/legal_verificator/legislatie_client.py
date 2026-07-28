"""Client for legislatie.just.ro — public, no authentication required."""

import asyncio
import logging
import re
import unicodedata
from typing import Optional, Tuple
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("legal-verificator.legislatie")

BASE_URL = "https://legislatie.just.ro"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.7",
}

# Rate limiting: max 5 req/s
_semaphore = asyncio.Semaphore(5)
_last_request = 0.0


class UpstreamUnavailable(Exception):
    """Raised when legislatie.just.ro returns 5xx after all retries."""
    pass


async def _rate_limited_get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    global _last_request
    async with _semaphore:
        now = asyncio.get_event_loop().time()
        wait = max(0, 0.2 - (now - _last_request))
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request = asyncio.get_event_loop().time()

        last_status = None
        for attempt in range(5):
            try:
                resp = await client.get(url, headers=HEADERS, timeout=45.0, **kwargs)
                last_status = resp.status_code
                if resp.status_code >= 500 and attempt < 4:
                    backoff = min(2 ** attempt, 8)
                    logger.warning("legislatie.just.ro %s on %s, retry %d/4 after %ds", resp.status_code, url, attempt + 1, backoff)
                    await asyncio.sleep(backoff)
                    continue
                return resp
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
                if attempt < 4:
                    backoff = min(2 ** attempt, 8)
                    logger.warning("legislatie.just.ro %s on %s, retry %d/4 after %ds", type(e).__name__, url, attempt + 1, backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise UpstreamUnavailable(f"legislatie.just.ro indisponibil dupa 5 incercari: {type(e).__name__}") from e
        if last_status and last_status >= 500:
            raise UpstreamUnavailable(f"legislatie.just.ro a returnat HTTP {last_status} dupa 5 incercari (probabil 502 Bad Gateway / mentenanta server)")
        return resp


async def fetch_url_text(url: str, max_chars: int = 20000) -> dict:
    """Descarca ORICE URL juridic cu user-agent de browser + urmarire redirect + retry,
    apoi extrage textul. Reuseste unde web-fetch-ul generic pica pe blocaje anti-bot (403),
    fiindca trimite UA de browser si urmareste redirect-urile. Extrage text si din PDF."""
    import io
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=45.0) as client:
            resp = await _rate_limited_get(client, url)
    except UpstreamUnavailable as e:
        return {"url": url, "error": str(e)}
    except Exception as e:
        return {"url": url, "error": f"fetch esuat: {type(e).__name__}: {e}"}

    if resp.status_code >= 400:
        hint = ""
        if resp.status_code == 403:
            hint = " (blocaj anti-bot; deja am incercat UA de browser)"
        elif resp.status_code == 404:
            hint = " (URL inexistent/mort; verifica sursa sau foloseste search_legislation/lege6)"
        return {"url": url, "status": resp.status_code, "error": f"HTTP {resp.status_code}{hint}"}

    ctype = resp.headers.get("content-type", "").lower()
    content = resp.content
    if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            source_kind = "pdf"
        except Exception as e:
            return {"url": url, "status": resp.status_code, "error": f"extractie PDF esuata: {type(e).__name__}: {e}"}
    else:
        try:
            soup = BeautifulSoup(content, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text("\n")
            source_kind = "html"
        except Exception:
            text = content.decode("utf-8", errors="ignore")
            source_kind = "raw"

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return {
        "url": str(resp.url),
        "status": resp.status_code,
        "content_type": ctype,
        "source_kind": source_kind,
        "chars": len(text),
        "truncated": len(text) > max_chars,
        "text": text[:max_chars],
    }


async def _get_csrf_token(client: httpx.AsyncClient) -> str:
    """Get CSRF token from legislatie.just.ro homepage."""
    resp = await _rate_limited_get(client, BASE_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_input = soup.find("input", {"name": "__RequestVerificationToken"})
    return csrf_input["value"] if csrf_input else ""


async def search_document(query: str, doc_number: Optional[str] = None,
                          date_from: Optional[str] = None, date_to: Optional[str] = None) -> list:
    """Search for a document on legislatie.just.ro using POST form."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        csrf_token = await _get_csrf_token(client)

        form_data = {
            "__RequestVerificationToken": csrf_token,
            "TitleText": query,
            "ContentText_First": "",
            "opContentText_Second": "",
            "ContentText_Second": "",
            "opContentText_Third": "",
            "ContentText_Third": "",
            "opContentText_Fourth": "",
            "ContentText_Fourth": "",
            "DocumentNumber": doc_number or "",
            "DataSemnariiTextFrom": date_from or "",
            "DataSemnariiTextTo": date_to or "",
            "PublishedInNumber": "",
            "DataPublicariiTextFrom": "",
            "DataPublicariiTextTo": "",
            "ActInForceOnDateTextFrom": "",
            "actiontype": "Căutare",
        }

        resp = await client.post(
            f"{BASE_URL}/",
            data=form_data,
            headers={
                **HEADERS,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": BASE_URL,
                "Origin": BASE_URL,
            },
            timeout=30.0,
        )

        if "/Error" in str(resp.url):
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "/Public/DetaliiDocument/" in href or "/Public/DetaliiDocumentAfis/" in href:
                title = link.get_text(strip=True)
                if title and len(title) > 10:
                    doc_id = re.search(r'/(\d+)', href)
                    results.append({
                        "title": title,
                        "url": f"{BASE_URL}{href}" if href.startswith("/") else href,
                        "doc_id": doc_id.group(1) if doc_id else "",
                    })

        return results[:10]


async def search_ccr(number: int, year: int) -> dict:
    """Search for a CCR decision by number and year on legislatie.just.ro."""
    # Strategy 1: Search by title + document number + year range
    results = await search_document(
        query=f"DECIZIE {number}",
        doc_number=str(number),
        date_from=str(year),
        date_to=str(year),
    )

    # Strategy 2: Broader search without date filter
    if not results:
        results = await search_document(
            query=f"DECIZIE {number}",
            doc_number=str(number),
        )

    # Filter for actual CCR decisions matching the year
    # When multiple decisions have same number (e.g. DCC 70/2023 from Feb vs Oct),
    # return ALL matches so caller can disambiguate by subject
    matches = []
    for r in results:
        title_lower = r["title"].lower()
        if ("decizie" in title_lower or "decizia" in title_lower) and str(year) in r["title"]:
            matches.append({
                "found": True,
                "title": r["title"],
                "url": r["url"],
                "doc_id": r.get("doc_id", ""),
            })

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple decisions with same number — return first but flag disambiguation
        return {
            **matches[0],
            "multiple_matches": True,
            "all_matches": matches,
            "warning": f"Exista {len(matches)} decizii CCR nr. {number}/{year}. Verificati subiectul pentru a selecta cea corecta.",
        }

    return {"found": False}


async def fetch_printable(doc_id: str) -> Tuple[str, str]:
    """Fetch the printable form of a document, return (text, printable_url)."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # First get the document page to find printable link
        doc_url = f"{BASE_URL}/Public/DetaliiDocument/{doc_id}"
        resp = await _rate_limited_get(client, doc_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find printable form link
        printable_link = None
        for a in soup.find_all("a", href=True):
            if "FormaPrintabila" in a["href"]:
                printable_link = a["href"]
                break

        if not printable_link:
            # Fallback: try to extract text from the document page itself
            content = soup.find("div", {"id": "TextAct662"}) or soup.find("div", class_="document-content")
            if content:
                return content.get_text(separator="\n", strip=True), doc_url
            return "", doc_url

        printable_url = f"{BASE_URL}{printable_link}" if printable_link.startswith("/") else printable_link
        resp = await _rate_limited_get(client, printable_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract text from printable page
        body = soup.find("body")
        if body:
            # Remove scripts and styles
            for tag in body.find_all(["script", "style"]):
                tag.decompose()
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        return text, printable_url


async def fetch_ccr_text(number: int, year: int) -> dict:
    """Fetch the full text of a CCR decision."""
    result = await search_ccr(number, year)
    if not result.get("found"):
        return {
            "text": "",
            "source": "legislatie.just.ro",
            "total_chars": 0,
            "truncated": False,
            "error": f"Decizia CCR nr. {number}/{year} nu a fost găsită pe legislatie.just.ro.",
        }

    doc_id = result.get("doc_id", "")
    if not doc_id:
        return {
            "text": "",
            "source": "legislatie.just.ro",
            "total_chars": 0,
            "truncated": False,
            "error": "Nu s-a putut identifica ID-ul documentului.",
        }

    text, printable_url = await fetch_printable(doc_id)

    if not text:
        return {
            "text": "",
            "source": "legislatie.just.ro",
            "total_chars": 0,
            "truncated": False,
            "error": "Textul deciziei nu a putut fi extras.",
        }

    total_chars = len(text)
    truncated = False

    # Smart truncation for very long texts
    if total_chars > 30000:
        # Keep first 15000 (intro + motivare) + last 5000 (dispozitiv)
        text = text[:15000] + "\n\n[...TRUNCAT...]\n\n" + text[-5000:]
        truncated = True

    return {
        "text": text,
        "source": "legislatie.just.ro",
        "total_chars": total_chars,
        "truncated": truncated,
        "printable_url": printable_url,
    }


# legislatie.just.ro doc_id pentru CONSTITUȚIA ROMÂNIEI (republicata 2003).
# Constitutia nu are "numar" (conventia 0/1991), iar formularul de cautare nu o
# regaseste — de aceea o tratam direct prin doc_id-ul ei stabil.
CONSTITUTIE_DOC_ID = "47355"


# Denumirea citibila a tipului de act, folosita in mesaje catre utilizator.
_DISPLAY_NAME = {
    "lege": "LEGE",
    "oug": "ORDONANȚĂ DE URGENȚĂ",
    "og": "ORDONANȚĂ",
    "hg": "HOTĂRÂRE",
    "ordin": "ORDIN",
    "decret": "DECRET",
    "cod": "COD",
    "constitutie": "CONSTITUȚIA",
    "constituție": "CONSTITUȚIA",
}

# Ce se trimite EFECTIV in campul TitleText al formularului. Site-ul are propriul
# vocabular, scrie ordonanta de urgenta "ORD DE URGENTA" si ordonanta simpla "OG",
# iar formularul intoarce zero rezultate daca titlul cerut vine cu diacritice sau
# cu numarul lipit de tip: "ORDONANȚĂ DE URGENȚĂ 57" nu gasea nimic, desi OUG
# 57/2019 exista. Numarul si anul se trimit oricum separat, pe campurile lor, deci
# titlul ramane doar tipul, fara diacritice. Sirul gol inseamna "orice tip",
# necesar la coduri, fiindca un cod poate fi lege (Codul civil, Legea 287/2009)
# sau ordonanta de urgenta (Codul administrativ, OUG 57/2019).
_TITLE_QUERY = {
    "lege": "LEGE",
    "oug": "ORD DE URGENTA",
    "og": "ORDONANTA",
    "hg": "HOTARARE",
    "ordin": "ORDIN",
    "decret": "DECRET",
}

# Un cod nu are tip propriu pe site, e publicat ca lege (Codul civil, Legea
# 287/2009) sau ca ordonanta de urgenta (Codul administrativ, OUG 57/2019).
# Se incearca in ordinea asta, ca sa nu iasa primul act oarecare cu acelasi
# numar si an, care ar fi un fals pozitiv, nu o verificare.
_COD_FALLBACK_TYPES = ("lege", "oug", "decret")

# Cum incepe titlul actului in lista de rezultate, per tip. Filtrul opreste
# confuzia dintre act si randurile vecine (o RECTIFICARE cu acelasi numar si an).
_TITLE_PREFIXES = {
    "lege": ("lege",),
    "oug": ("ord de urgenta", "ordonanta de urgenta", "oug"),
    "og": ("og", "ordonanta"),
    "hg": ("hotarare", "hg"),
    "ordin": ("ordin",),
    "decret": ("decret",),
}


def _fold(s: str) -> str:
    """Litere mici, fara diacritice. Titlurile actelor vin in ASCII de pe site,
    randurile descriptive vin cu diacritice, iar comparatia trebuie sa le vada la fel."""
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _title_is_type(title: str, act_type: str) -> bool:
    """Titlul din lista incepe cu tipul de act cerut. Un tip pe care site-ul nu-l
    are in vocabular se verifica dupa propriul nume, nu se accepta orbeste:
    altfel o cautare de cod ar intoarce primul decret cu acelasi numar si an."""
    prefixes = _TITLE_PREFIXES.get(act_type)
    if not prefixes:
        folded = _fold(act_type).strip()
        if not folded:
            return True
        prefixes = (folded,)
    t = re.sub(r"\s+", " ", _fold(title)).strip()
    t = re.sub(r"^\d+\.\s*", "", t)
    return any(t.startswith(p) for p in prefixes)


async def _search_by_type(key: str, number: int, year: int) -> Optional[dict]:
    """Cauta un act de un tip precis. None inseamna ca tipul asta nu s-a gasit."""
    title_query = _TITLE_QUERY.get(key, _fold(key).upper())

    results = await search_document(
        query=title_query,
        doc_number=str(number),
        date_from=str(year),
        date_to=str(year),
    )
    # Tipul cerut nu figureaza in vocabularul site-ului, deci se cauta pe numar si
    # an, iar tipul se verifica pe titlurile intoarse.
    if not results and title_query:
        results = await search_document(
            query="",
            doc_number=str(number),
            date_from=str(year),
            date_to=str(year),
        )

    for r in results:
        title = r["title"]
        if str(number) in title and str(year) in title and _title_is_type(title, key):
            # Check status from title
            title_lower = title.lower()
            status = "in_vigoare"
            abrogated_by = None
            if "abrogat" in title_lower:
                status = "abrogat"
            elif "modificat" in title_lower or "republicat" in title_lower:
                status = "modificat"

            return {
                "found": True,
                "title": title,
                "status": status,
                "url": r["url"],
                "abrogated_by": abrogated_by,
            }
    return None


async def search_legislation(act_type: str, number: int, year: int) -> dict:
    """Search for a legislative act by type, number, and year."""
    key = (act_type or "").lower()
    if key in ("constitutie", "constituție"):
        return {
            "found": True,
            "title": "CONSTITUȚIA ROMÂNIEI (republicată în M. Of. nr. 767/2003)",
            "status": "in_vigoare",
            "url": f"{BASE_URL}/Public/DetaliiDocument/{CONSTITUTIE_DOC_ID}",
            "abrogated_by": None,
        }

    act_name = _DISPLAY_NAME.get(key, (act_type or "").upper())
    attempts = _COD_FALLBACK_TYPES if key in ("cod", "codul") else (key,)

    for attempt in attempts:
        found = await _search_by_type(attempt, number, year)
        if found:
            if attempt != key:
                found["resolved_as"] = attempt
            return found

    return {"found": False, "error": f"{act_name} nr. {number}/{year} nu a fost găsită pe legislatie.just.ro."}


async def fetch_article(act_type: str, number: int, year: int, article: int,
                        alineat: Optional[int] = None, litera: Optional[str] = None) -> dict:
    """Fetch text of a specific article from a legislative act."""
    # Search for the act first
    leg = await search_legislation(act_type, number, year)
    if not leg.get("found"):
        return {"text": "", "error": leg.get("error", "Act not found")}

    # Get the doc_id from URL
    doc_id_match = re.search(r'/(\d+)', leg["url"])
    if not doc_id_match:
        return {"text": "", "error": "Cannot extract document ID"}

    text, _ = await fetch_printable(doc_id_match.group(1))
    if not text:
        return {"text": "", "error": "Cannot fetch document text"}

    # Find the specific article. Case-insensitive: legile uzuale folosesc "Art. 1",
    # dar Constitutia foloseste "ARTICOLUL 1" (majuscule, cuvant intreg).
    art_patterns = [
        rf'\bArticolul\s*{article}\b',
        rf'\bArt\.\s*{article}\b',
        rf'\bART\.\s*{article}\b',
    ]

    art_start = -1
    for pattern in art_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            art_start = match.start()
            break

    if art_start == -1:
        return {"text": "", "error": f"Articolul {article} nu a fost găsit în text."}

    # Find next article to delimit
    next_art = re.search(
        rf'\bArticolul\s*{article + 1}\b|\bArt\.\s*{article + 1}\b|\bART\.\s*{article + 1}\b',
        text[art_start + 10:], re.IGNORECASE)
    if next_art:
        art_text = text[art_start:art_start + 10 + next_art.start()]
    else:
        art_text = text[art_start:art_start + 3000]  # fallback: take 3000 chars

    # Filter by alineat if specified
    if alineat:
        alin_pattern = rf'\({alineat}\)'
        alin_match = re.search(alin_pattern, art_text)
        if alin_match:
            # Find next alineat
            next_alin = re.search(rf'\({alineat + 1}\)', art_text[alin_match.start():])
            if next_alin:
                art_text = art_text[alin_match.start():alin_match.start() + next_alin.start()]
            else:
                art_text = art_text[alin_match.start():]

    # Filter by litera if specified
    if litera:
        lit_pattern = rf'{litera}\)'
        lit_match = re.search(lit_pattern, art_text)
        if lit_match:
            next_lit = re.search(r'[a-z]\)', art_text[lit_match.end():])
            if next_lit:
                art_text = art_text[lit_match.start():lit_match.end() + next_lit.start()]
            else:
                art_text = art_text[lit_match.start():]

    return {
        "text": art_text.strip(),
        "source": "legislatie.just.ro",
    }
