"""Client sintact.ro — Wolters Kluwer Romania: legislatie, jurisprudenta, doctrina.

Sintact expune un API JSON intern (verificat live iulie 2026, apelat dintr-o sesiune
Playwright autentificata, vezi auth.SintactSession):
  - POST /api/search.direct.hit.get.json        -> gaseste un act/decizie EXACT dupa citare
    (ex. "Legea 190/2018", "Decizia 22/2020"); daca nu exista, nu intoarce nro/versionId.
  - POST /api/searchResults.get.json            -> cautare full-text.
  - POST /api/searchResults.get.narrowings.json -> fatetele disponibile pentru o cautare.
  - GET  /api/act.get.json?nro=..&versionId=..  -> continutul XHTML integral al documentului,
    inclusiv pentru hotarari judecatoresti.

FILTRAREA SE FACE SERVER-SIDE (corectie 2026-07-27):
  Campul `documentMainType` din payloadul de cautare separa fondurile documentare:
  ACT (legislatie), JURISPRUDENCE (jurisprudenta), PUBLICATION (doctrina), TOOLS.
  Versiunea anterioara a acestui client nu il trimitea si incerca sa distinga
  categoriile client-side dupa `lawType`. Hotararile instantelor nationale au
  `lawType: null`, deci cadeau in "altele" si dispareau complet la filtrarea pe
  jurisprudenta: baza de sentinte de judecatorie, tribunal si curte de apel parea
  inexistenta, desi abonamentul o acopera (peste 4.500 de hotarari doar pe
  Legea 295/2004). Semnalul real de categorie este `documentProductionType`
  (COURT_JURISPRUDENCE / CNSC_JURISPRUDENCE / COMMON_ACT / MONOGRAPH_FRAGMENT).

Fatetele de jurisprudenta (instanta, tip hotarare, solutie, sediu, obiect, domeniu)
se trimit ca liste de identificatori numerici `nrs`, nu ca etichete text; etichetele
sunt respinse cu raspuns gol. Identificatorii se citesc din narrowings, de aceea
`search_jurisprudence` rezolva singur etichetele in id-uri inainte de cautare.
"""

import logging
import re
import unicodedata
from datetime import date
from html import unescape

from bs4 import BeautifulSoup

from auth import SintactSession, SINTACT_BASE

logger = logging.getLogger("legal-verificator.sintact")

SEARCH_URL = f"{SINTACT_BASE}/api/searchResults.get.json"
DIRECT_HIT_URL = f"{SINTACT_BASE}/api/search.direct.hit.get.json"
NARROWINGS_URL = f"{SINTACT_BASE}/api/searchResults.get.narrowings.json"
ACT_URL = f"{SINTACT_BASE}/api/act.get.json"

# Fondurile documentare, asa cum le numeste API-ul in `documentMainType`.
_MAIN_TYPE_BY_CATEGORY = {
    "legislatie": "ACT",
    "jurisprudenta": "JURISPRUDENCE",
    "doctrina": "PUBLICATION",
    "unelte": "TOOLS",
}

_JURISPRUDENCE_PROD_TYPES = {"COURT_JURISPRUDENCE", "CNSC_JURISPRUDENCE"}
_LEGISLATION_TYPES = {"lege", "oug", "og", "ordonanta de urgenta", "ordonanta", "hg",
                      "hotararea guvernului", "cod", "constitutie", "ordin", "regulament", "directiva"}

# Peste acest prag serverul incetineste vizibil fara sa dea mai multa acoperire utila.
_MAX_HITS_PP = 100


def _point_in_time() -> str:
    """Data de referinta a versiunii legislative ceruta de API (formatul folosit de
    aplicatia web: YYYY-MM-DD). Fara acest camp, POST-urile intorc raspuns gol."""
    return date.today().isoformat()


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def fold_diacritics(s: str) -> str:
    """Litere mici, fara diacritice, pentru orice comparatie de text juridic romanesc.

    Descompunerea NFKD separa semnul diacritic de litera, iar filtrarea semnelor
    combinate acopera deopotriva varianta cu virgula dedesubt (ș, U+0219) si cea cu
    sedila (ş, U+015F), care coexista in documentele oficiale. Fara pasul asta,
    'excepţia' si 'exceptia' raman doua cuvinte diferite la comparare, iar o citare
    reala scrisa fara diacritice primeste verdict de citare inventata.

    Pliaza CARACTER CU CARACTER si pastreaza lungimea sirului. O normalizare aplicata
    pe tot textul deodata ar extinde ligaturile ('ﬁ' -> 'fi') si ar decala pozitiile,
    iar apelantii cauta un cuvant in textul pliat si taie citatul-proba din textul
    original, la acelasi offset. Cand o litera nu se pliaza pe exact un caracter, se
    pastreaza forma initiala, tocmai ca offseturile sa ramana aliniate."""
    out = []
    for ch in (s or ""):
        low = ch.lower()
        if len(low) != 1:
            low = ch
        base = "".join(c for c in unicodedata.normalize("NFKD", low)
                       if not unicodedata.combining(c))
        out.append(base if len(base) == 1 else low)
    return "".join(out)


def _norm(s: str) -> str:
    """Normalizare pentru potrivirea etichetelor de fateta, cu spatiile colapsate.
    Utilizatorul scrie 'Curtea de Apel', fateta poate contine alta grafie, iar
    potrivirea nu trebuie sa depinda de asta."""
    return re.sub(r"\s+", " ", fold_diacritics(s).strip())


def _doc_url(nro: int, version_id: int, category: str = "") -> str:
    if not nro:
        return ""
    route = "jurisprudence" if category == "jurisprudenta" else "act"
    return f"{SINTACT_BASE}/#/{route}/{nro}/{version_id}"


# Titlurile de jurisprudenta au forma:
#   "Decizie nr. 454/2018 din 03-oct-2018, Curtea de Apel Oradea, nerespectarea ... (Penal)"
# Unele au numarul lipsa ("- nr. /2000 din ...") sau identificator generat ("RJ 7387949g6/2026").
_TITLE_RE = re.compile(
    r"^(?P<tip>.*?)\s*nr\.\s*(?P<numar>[^/]*?/\d{4}|\S*)\s+din\s+(?P<data>[\w.\-]+)\s*,\s*"
    r"(?P<instanta>[^,]+?)\s*(?:,\s*(?P<obiect>.*))?$"
)


def _parse_jurisprudence_title(title: str) -> dict:
    """Descompune titlul unei hotarari in campuri citabile. Fara asta, modelul ar
    trebui sa reextraga instanta si data din sirul brut la fiecare citare."""
    m = _TITLE_RE.match(title or "")
    if not m:
        return {}
    tip = (m.group("tip") or "").strip(" -")
    obiect = (m.group("obiect") or "").strip()
    materie = ""
    mm = re.search(r"\(([^()]+)\)\s*$", obiect)
    if mm:
        materie = mm.group(1).strip()
        obiect = obiect[: mm.start()].strip()
    return {
        "tip_hotarare": tip,
        "numar": (m.group("numar") or "").strip(),
        "data": (m.group("data") or "").strip(),
        "instanta": (m.group("instanta") or "").strip(),
        "obiect": obiect,
        "materie": materie,
    }


def _map_doc(d: dict) -> dict:
    prod_type = (d.get("documentProductionType") or d.get("documentType") or "").strip().upper()
    law_type = (d.get("lawType") or "").strip()

    if prod_type in _JURISPRUDENCE_PROD_TYPES:
        category = "jurisprudenta"
    elif prod_type == "MONOGRAPH_FRAGMENT" or d.get("resourceType") == "MONOGRAPH_FRAGMENT":
        category = "doctrina"
    elif prod_type == "COMMON_ACT" or law_type.lower() in _LEGISLATION_TYPES:
        category = "legislatie"
    else:
        category = "altele"

    title = _strip_tags(d.get("title", ""))
    snippets = [_strip_tags(s.get("snippet", "")) for s in (d.get("snippetWithLink") or [])]
    out = {
        "title": title,
        "lawType": law_type,
        "category": category,
        "documentProductionType": prod_type,
        "validity": d.get("validity", ""),
        "nro": d.get("nro"),
        "versionId": d.get("versionId"),
        "url": _doc_url(d.get("nro"), d.get("versionId"), category),
        "snippets": [s for s in snippets if s][:3],
        "source": "sintact.ro",
    }
    if category == "jurisprudenta":
        out.update(_parse_jurisprudence_title(title))
    return out


def _search_body(query: str, category: str = None, max_results: int = 10,
                 start_from: int = 0, sort_by_date: bool = False) -> dict:
    body = {
        "searchLang": "RO",
        "queryString": query,
        "startFrom": start_from,
        "sortBy": "DATE_DESC" if sort_by_date else "DEFAULT",
        "pointInTime": _point_in_time(),
        "analyzer": False,
        "showMeAutoThesis": False,
        "hitsPp": min(max(max_results, 10), _MAX_HITS_PP),
    }
    main_type = _MAIN_TYPE_BY_CATEGORY.get((category or "").strip().lower())
    if main_type:
        body["documentMainType"] = main_type
    return body


async def search(session: SintactSession, query: str, category: str = None,
                  max_results: int = 10, start_from: int = 0,
                  sort_by_date: bool = False) -> dict:
    """Cautare full-text pe sintact.ro prin API-ul intern, sesiune autentificata.

    `category` (legislatie / jurisprudenta / doctrina) se aplica SERVER-SIDE prin
    documentMainType, deci nu mai pierde rezultate din cauza paginarii."""
    if not await session.ensure_authenticated():
        return {"results": [], "total": 0, "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata. Verifica SINTACT_EMAIL/SINTACT_PASSWORD in .env."}

    body = _search_body(query, category, max_results, start_from, sort_by_date)
    try:
        data = await session.post_json(SEARCH_URL, body)
    except Exception as e:
        logger.error("sintact search error: %s", e)
        return {"results": [], "total": 0, "source": "sintact.ro", "error": str(e)}

    docs = [_map_doc(d) for d in (data.get("documentList") or [])]
    return {
        "results": docs[:max_results],
        "returned": len(docs[:max_results]),
        "total_available": data.get("availableHitCount"),
        "jurisprudence_available": data.get("jurisprudenceCount"),
        "start_from": start_from,
        "category": category or "toate",
        "source": "sintact.ro",
    }


# ── Fatete de jurisprudenta ───────────────────────────────────────────────────

# Campurile de fateta acceptate de searchResults.get.json, cu numele lor din API.
_JURIS_FACET_FIELDS = {
    "instanta": "authorClasses",
    "tip_hotarare": "jurisprudenceTypes",
    "solutie": "typeOfDecision",
    "sediu": "seatList",
    "obiect": "jurisprudenceCaseObjects",
    "domeniu": "domains",
    "stadiu": "stageOfProcedure",
    "sectie": "jurisprudenceSection",
}

# Prescurtarile uzuale in practica, ca modelul sa nu trebuiasca sa scrie eticheta exacta.
# Se aplica DOAR ca rezerva, dupa ce potrivirea directa a esuat: altfel un alias ar
# deturna o eticheta reala mai ingusta catre una mai larga ("Sentinta civila", 12
# hotarari, ar ajunge la "Sentinta", 1873), adica exact largirea tacuta de evitat.
_LABEL_ALIASES = {
    "iccj": "inalta curte de casatie si justitie",
    "inalta curte": "inalta curte de casatie si justitie",
    "curte de apel": "curtea de apel",
    "ca": "curtea de apel",
    "tribunal": "tribunalul",
    "judecatorie": "judecatoria",
    "cnsc": "consiliul national de solutionare a contestatiilor",
    "admisa": "admis",
    "respinsa": "respins",
}


def _facet_values(narrowings: dict, api_field: str) -> list:
    """Valorile unei fatete, indiferent daca API-ul o cheama pe nume de raspuns sau
    pe requestField (cele doua coincid la fatetele de jurisprudenta, dar nu peste tot)."""
    for key, val in (narrowings or {}).items():
        if not isinstance(val, dict):
            continue
        if key == api_field or val.get("requestField") == api_field:
            out = []
            for v in (val.get("values") or []):
                ident = v.get("nrs", v.get("conceptId"))
                if ident is not None:
                    out.append({"label": v.get("label", ""), "id": ident, "count": v.get("count", 0)})
            return out
    return []


def _resolve_labels(values: list, wanted) -> tuple:
    """Traduce etichete umane in identificatori `nrs`. Intoarce (ids, potrivite, nepotrivite).

    Potrivirea merge in trepte: egalitate normalizata, apoi prefix, apoi substring.
    Ce nu se potriveste NU se ignora in tacere, ci se raporteaza inapoi, altfel
    un filtru gresit ar da un rezultat mai larg decat crede cel care l-a cerut."""
    if wanted is None:
        return [], [], []
    if isinstance(wanted, (str, int)):
        wanted = [wanted]

    def _match(key):
        return (next((v for v in values if _norm(v["label"]) == key), None)
                or next((v for v in values if _norm(v["label"]).startswith(key)), None)
                or next((v for v in values if key in _norm(v["label"])), None))

    ids, matched, unmatched = [], [], []
    for w in wanted:
        if isinstance(w, int):
            ids.append(w)
            matched.append(str(w))
            continue
        key = _norm(w)
        hit = _match(key)
        if hit is None and key in _LABEL_ALIASES:
            hit = _match(_LABEL_ALIASES[key])
        if hit:
            ids.append(hit["id"])
            matched.append(hit["label"])
        else:
            unmatched.append(w)
    return ids, matched, unmatched


async def get_jurisprudence_facets(session: SintactSession, query: str) -> dict:
    """Filtrele disponibile pentru o cautare de jurisprudenta, cu etichete si numar
    de hotarari. Se apeleaza inainte de a filtra, ca filtrul sa fie ales din valori
    reale, nu ghicit."""
    if not await session.ensure_authenticated():
        return {"error": "Autentificare sintact.ro esuata.", "source": "sintact.ro"}

    body = {"documentMainType": "JURISPRUDENCE", "searchLang": "RO", "queryString": query,
            "pointInTime": _point_in_time(), "showMeAutoThesis": False, "limitedFacet": True}
    try:
        nar = await session.post_json(NARROWINGS_URL, body) or {}
    except Exception as e:
        logger.error("sintact narrowings error: %s", e)
        return {"error": str(e), "source": "sintact.ro"}

    facets = {}
    for friendly, api_field in _JURIS_FACET_FIELDS.items():
        vals = _facet_values(nar, api_field)
        if vals:
            facets[friendly] = [{"label": v["label"], "hotarari": v["count"]} for v in vals[:40]]

    total = next((v.get("count") for v in ((nar.get("documentMainType") or {}).get("values") or [])
                  if v.get("label") == "JURISPRUDENCE"), None)

    return {"query": query, "jurisprudenta_disponibila": total,
            "filtre": facets, "source": "sintact.ro"}


async def search_jurisprudence(session: SintactSession, query: str, instanta=None,
                                tip_hotarare=None, solutie=None, sediu=None, obiect=None,
                                domeniu=None, stadiu=None, sectie=None,
                                data_de_la: str = None, data_pana_la: str = None,
                                sort_by_date: bool = False, max_results: int = 20,
                                start_from: int = 0) -> dict:
    """Cautare in fondul de jurisprudenta nationala (judecatorii, tribunale, curti de
    apel, ICCJ, CNSC), cu filtrele reale ale platformei.

    Etichetele primite (ex. instanta="Curtea de Apel", solutie="Admis") se rezolva in
    identificatorii numerici ceruti de API printr-un apel de narrowings pe aceeasi
    interogare, fiindca API-ul respinge etichetele text cu raspuns gol."""
    if not await session.ensure_authenticated():
        return {"results": [], "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata. Verifica SINTACT_EMAIL/SINTACT_PASSWORD in .env."}

    body = _search_body(query, "jurisprudenta", max_results, start_from, sort_by_date)

    requested = {"instanta": instanta, "tip_hotarare": tip_hotarare, "solutie": solutie,
                 "sediu": sediu, "obiect": obiect, "domeniu": domeniu,
                 "stadiu": stadiu, "sectie": sectie}
    applied, unmatched = {}, {}

    if any(v is not None for v in requested.values()):
        nar_body = {"documentMainType": "JURISPRUDENCE", "searchLang": "RO", "queryString": query,
                    "pointInTime": _point_in_time(), "showMeAutoThesis": False, "limitedFacet": True}
        try:
            nar = await session.post_json(NARROWINGS_URL, nar_body) or {}
        except Exception as e:
            logger.error("sintact narrowings error: %s", e)
            nar = {}
        for friendly, wanted in requested.items():
            if wanted is None:
                continue
            api_field = _JURIS_FACET_FIELDS[friendly]
            ids, matched, miss = _resolve_labels(_facet_values(nar, api_field), wanted)
            if ids:
                body[api_field] = ids
                applied[friendly] = matched
            if miss:
                unmatched[friendly] = miss

    if data_de_la:
        body["issueDateFrom"] = data_de_la
    if data_pana_la:
        body["issueDateTo"] = data_pana_la

    try:
        data = await session.post_json(SEARCH_URL, body)
    except Exception as e:
        logger.error("sintact jurisprudence search error: %s", e)
        return {"results": [], "source": "sintact.ro", "error": str(e)}

    if not data:
        return {"results": [], "source": "sintact.ro",
                "error": "sintact.ro a respins cererea (raspuns gol). Verifica valorile filtrelor "
                         "cu sintact_jurisprudence_filters.",
                "filtre_aplicate": applied, "filtre_nepotrivite": unmatched}

    docs = [_map_doc(d) for d in (data.get("documentList") or [])][:max_results]
    out = {
        "results": docs,
        "returned": len(docs),
        "total_available": data.get("availableHitCount"),
        "start_from": start_from,
        "filtre_aplicate": applied,
        "source": "sintact.ro",
    }
    if unmatched:
        out["filtre_nepotrivite"] = unmatched
        out["avertisment"] = ("Unele filtre nu s-au potrivit cu nicio valoare disponibila si NU au fost "
                              "aplicate; rezultatele sunt mai largi decat filtrul cerut. Verifica "
                              "valorile reale cu sintact_jurisprudence_filters.")
    return out


# ── Decizii CCR ───────────────────────────────────────────────────────────────

_CCR_AUTHOR_LABEL = "Curtea Constitutionala"


async def _ccr_candidates(session: SintactSession, number, year) -> list:
    """Deciziile CCR nr. number/year de pe sintact.ro, izolate prin fateta de autor.

    Cautarea 'direct hit' NU e sigura aici: pe "Decizia 22/2020" intoarce o decizie
    ICCJ, iar pe "Decizia 55/2020" una a prim-ministrului, fiindca acelasi numar se
    repeta la emitenti diferiti in acelasi an. Fondul ACT expune fateta `authors`,
    care separa emitentul, si numai ea face identificarea neechivoca."""
    query = f"Decizia {number}/{year}"
    nar = await session.post_json(NARROWINGS_URL, {
        "documentMainType": "ACT", "searchLang": "RO", "queryString": query,
        "pointInTime": _point_in_time(), "showMeAutoThesis": False, "limitedFacet": True}) or {}
    ids, _, _ = _resolve_labels(_facet_values(nar, "authors"), _CCR_AUTHOR_LABEL)
    if not ids:
        return []

    body = _search_body(query, "legislatie", 20)
    body["authors"] = ids
    data = await session.post_json(SEARCH_URL, body) or {}

    token = f"{number}/{year}"
    out = []
    for d in (data.get("documentList") or []):
        doc = _map_doc(d)
        if token in re.sub(r"\s+", "", doc["title"]):
            out.append(doc)
    return out


def _auth_failure(msg: str) -> dict:
    return {"found": False, "auth_failed": True, "source": "sintact.ro",
            "error": f"Autentificare sintact.ro esuata. {msg}"}


async def search_ccr_decision(session: SintactSession, number, year) -> dict:
    """Cauta o decizie CCR pe sintact.ro. `auth_failed` distinge sesiunea cazuta de
    decizia pur si simplu negasita, ca apelantul sa stie daca merita sa treaca pe
    sursele de rezerva."""
    if not await session.ensure_authenticated():
        return _auth_failure("Verifica SINTACT_EMAIL/SINTACT_PASSWORD in .env.")
    try:
        cands = await _ccr_candidates(session, number, year)
    except Exception as e:
        logger.error("sintact CCR search error: %s", e)
        return {"found": False, "error": str(e), "source": "sintact.ro"}

    if not cands:
        return {"found": False, "source": "sintact.ro",
                "error": f"Decizia CCR nr. {number}/{year} nu a fost gasita pe sintact.ro."}

    first = cands[0]
    out = {"found": True, "title": first["title"], "url": first["url"],
           "nro": first["nro"], "versionId": first["versionId"],
           "validity": first.get("validity", ""), "source": "sintact.ro"}
    if len(cands) > 1:
        out["multiple_matches"] = True
        out["all_matches"] = cands
        out["warning"] = (f"Exista {len(cands)} decizii CCR nr. {number}/{year} pe sintact.ro. "
                          "Verifica subiectul pentru a o alege pe cea corecta.")
    return out


async def fetch_ccr_text(session: SintactSession, number, year) -> dict:
    """Textul integral al unei decizii CCR de pe sintact.ro."""
    found = await search_ccr_decision(session, number, year)
    if not found.get("found"):
        return {"text": "", "source": "sintact.ro",
                "auth_failed": found.get("auth_failed", False),
                "error": found.get("error", f"Decizia CCR nr. {number}/{year} nu a fost gasita.")}

    doc = await fetch_document(session, found["nro"], found["versionId"])
    if found.get("warning"):
        doc["warning"] = found["warning"]
    return doc


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
        fallback = await search(session, query, max_results=5)
        for r in fallback.get("results", []):
            if query.strip().lower() in r["title"].lower():
                return {"status": "CONFIRMAT", "title": r["title"], "url": r["url"],
                        "validity": r["validity"], "nro": r["nro"], "versionId": r["versionId"],
                        "source": "sintact.ro", "via": "search_fallback"}
        return {"status": "NEGASIT", "query": query, "source": "sintact.ro",
                "warning": "Nicio potrivire exacta pe sintact.ro, posibil citare inventata sau formulata gresit."}

    doc = await fetch_document(session, nro, version_id)
    return {"status": "CONFIRMAT", "title": doc.get("title", ""),
            "url": doc.get("url") or _doc_url(nro, version_id),
            "nro": nro, "versionId": version_id, "source": "sintact.ro", "via": "direct_hit"}


async def fetch_document(session: SintactSession, nro: int, version_id: int,
                          max_chars: int = 0) -> dict:
    """Descarca textul integral al unui document de pe sintact.ro: act normativ,
    decizie CCR/ICCJ sau hotarare a unei instante nationale (acelasi endpoint)."""
    if not await session.ensure_authenticated():
        return {"text": "", "title": "", "source": "sintact.ro",
                "error": "Autentificare sintact.ro esuata."}

    url = f"{ACT_URL}?nro={nro}&versionId={version_id}&translation=RO"
    try:
        data = await session.fetch_json(url)
    except Exception as e:
        logger.error("sintact fetch_document error: %s", e)
        return {"text": "", "title": "", "source": "sintact.ro", "error": str(e)}

    prod_type = (data.get("docProdType") or data.get("documentType") or "").strip().upper()
    category = "jurisprudenta" if prod_type in _JURISPRUDENCE_PROD_TYPES else "legislatie"

    content_html = data.get("content", "")
    text = ""
    if content_html:
        # Continutul vine ca XHTML cu declaratie XML in fata; html.parser o lasa in
        # text daca nu e taiata, si ar ajunge in citat.
        content_html = re.sub(r"^\s*<\?xml[^>]*\?>", "", content_html)
        text = BeautifulSoup(content_html, "html.parser").get_text("\n", strip=True)

    title = data.get("title", "")
    out = {
        "title": title,
        "text": text[:max_chars] if max_chars and len(text) > max_chars else text,
        "truncated": bool(max_chars and len(text) > max_chars),
        "chars": len(text),
        "category": category,
        "url": _doc_url(nro, version_id, category),
        "source": "sintact.ro",
    }
    if category == "jurisprudenta":
        out.update(_parse_jurisprudence_title(_strip_tags(title)))
    return out
