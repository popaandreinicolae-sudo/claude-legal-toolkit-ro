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
from auth import Lege5Session, Lege6Session, SintactSession
from sintact_client import (
    search as sintact_search_fn,
    fetch_document as sintact_fetch_doc,
    verify_citation as sintact_verify_citation_fn,
    search_jurisprudence as sintact_search_jurisprudence_fn,
    get_jurisprudence_facets as sintact_facets_fn,
    search_ccr_decision as sintact_search_ccr,
    fetch_ccr_text as sintact_fetch_ccr,
    fold_diacritics,
)
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
sintact_session = SintactSession()


# ── TOOL DEFINITIONS ──────────────────────────────────────────────────────────

# Ordinea in care tool-urile ajung la model. Pozitia in lista cantareste la
# alegerea tool-ului, deci sursa de rezerva asezata inaintea celei primare
# contrazice in fapt ce scrie in descriere. sintact.ro sta primul fiindca are
# abonament activ si sesiunea se autentifica; Indaco (lege6, lege5) inchide lista.
# Un tool care lipseste de aici ajunge la coada, fara sa dispara.
_TOOL_ORDER = (
    # 1. sintact.ro (Wolters Kluwer), sursa primara
    "sintact_verify_citation",
    "sintact_search",
    "sintact_search_jurisprudence",
    "sintact_jurisprudence_filters",
    "sintact_fetch_document",
    # 2. surse oficiale publice
    "search_ccr_decision",
    "fetch_ccr_decision_text",
    "verify_ccr_citation",
    "search_ccr_by_subject",
    "batch_verify_ccr",
    "search_legislation",
    "fetch_article_text",
    "fetch_legal_url",
    # 3. Indaco, rezerva pentru cazul in care sintact nu se autentifica
    "lege6_search",
    "lege6_search_legislation",
    "lege6_fetch_document",
    "lege5_search",
    "lege5_fetch_document",
)


@app.list_tools()
async def list_tools():
    tools = [
        types.Tool(
            name="search_ccr_decision",
            description="Caută o decizie CCR, întâi pe sintact.ro (identificare prin emitent, deci nu "
                        "confundă decizia CCR cu o decizie ICCJ sau a prim-ministrului cu același "
                        "număr), apoi pe legislatie.just.ro. Returnează URL, titlu, data publicării.",
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
            description="Caută un act normativ pe legislatie.just.ro. Verifică dacă e în vigoare sau abrogat. "
                        "Se poate apela în două feluri: fie cu câmpurile separate act_type + number + year, "
                        "fie cu citarea întreagă în 'query' ('Legea 58/2023', 'O.U.G. nr. 155/2024', "
                        "'Codul muncii'), din care tipul, numărul și anul se extrag automat. "
                        "Niciun câmp nu e obligatoriu: cu date incomplete tool-ul întoarce candidați reali "
                        "din căutarea full-text, ca apelul următor să fie precis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Citarea în text liber, ex: 'Legea 58/2023', 'OUG 155/2024', 'Codul penal'. Alternativă la act_type+number+year."},
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, og, hg, ordin, cod, constitutie (acceptă și formele 'Legea', 'O.U.G.', 'H.G.')"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                },
            },
        ),
        types.Tool(
            name="fetch_article_text",
            description="Extrage textul exact al unui articol/alineat/literă din actul normativ specificat. "
                        "Acceptă fie câmpurile separate, fie citarea întreagă în 'query' "
                        "('art. 3 alin. (2) lit. b) din Legea 58/2023', 'art. 53 din Constituție'), "
                        "din care actul, articolul, alineatul și litera se extrag automat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Citarea în text liber, ex: 'art. 3 alin. (2) din Legea 58/2023'. Alternativă la câmpurile separate."},
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, hg, cod, constitutie"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului, 0 pentru Constituție (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                    "article": {"type": ["integer", "string"], "description": "Numărul articolului"},
                    "alineat": {"type": ["integer", "string"], "description": "Numărul alineatului (opțional)"},
                    "litera": {"type": "string", "description": "Litera (opțional, ex: 'a', 'b')"},
                },
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
            description="REZERVA. Căutare full-text pe lege6.ro (Indaco Systems). Sursa primară pentru "
                        "legislație, jurisprudență și doctrină este sintact.ro (sintact_search, "
                        "sintact_search_jurisprudence); lege6.ro se folosește doar dacă sesiunea "
                        "sintact nu se autentifică. Contul lege6 poate să nu fie configurat.",
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
            description="Caută un act normativ pe lege6.ro după tip + nr/an. Returnează status (în vigoare/abrogat/modificat). "
                        "Acceptă și citarea întreagă în 'query' ('Legea 58/2023'), din care tipul, numărul și anul se extrag automat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Citarea în text liber, ex: 'Legea 58/2023'. Alternativă la act_type+number+year."},
                    "act_type": {"type": "string", "description": "Tipul actului: lege, oug, og, hg, ordin, cod, constitutie"},
                    "number": {"type": ["integer", "string"], "description": "Numărul actului (acceptă și alias 'act_number')"},
                    "act_number": {"type": ["integer", "string"], "description": "Alias pentru number"},
                    "year": {"type": ["integer", "string"], "description": "Anul actului (acceptă și alias 'act_year')"},
                    "act_year": {"type": ["integer", "string"], "description": "Alias pentru year"},
                },
            },
        ),
        types.Tool(
            name="sintact_verify_citation",
            description="PRIORITAR pentru verificare citari. Verifica pe sintact.ro (Wolters Kluwer) daca o lege, decizie (CCR/ICCJ/CEDO) sau articol citat CHIAR EXISTA. Foloseste 'direct hit', acelasi mecanism ca bara de cautare sintact, apoi fallback pe cautare full-text. Raspunde CONFIRMAT (cu titlu, url, status validitate) sau NEGASIT.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Citarea de verificat, ex: 'Legea 190/2018', 'Decizia 22/2020', 'Codul Civil art. 1349'"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="sintact_search",
            description="Cautare full-text pe sintact.ro (Wolters Kluwer, cont abonat): legislatie, "
                        "jurisprudenta, doctrina. Filtrarea pe categorie se face server-side, deci "
                        "'jurisprudenta' acopera INCLUSIV hotararile instantelor nationale "
                        "(judecatorii, tribunale, curti de apel), nu doar ce apare in Monitorul Oficial. "
                        "Pentru o cercetare de jurisprudenta cu filtre pe instanta sau solutie, "
                        "foloseste sintact_search_jurisprudence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de cautare"},
                    "category": {"type": "string", "enum": ["legislatie", "jurisprudenta", "doctrina"], "description": "Fondul documentar cautat (optional; se aplica server-side)"},
                    "max_results": {"type": "integer", "description": "Numar maxim de rezultate (default 10, maximum 100)", "default": 10},
                    "start_from": {"type": "integer", "description": "Offset pentru paginare (default 0)", "default": 0},
                    "sort_by_date": {"type": "boolean", "description": "Sorteaza descrescator dupa data in loc de relevanta", "default": False},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="sintact_search_jurisprudence",
            description="PRIORITAR pentru cercetare de jurisprudenta nationala. Cauta in fondul de "
                        "hotarari judecatoresti de pe sintact.ro (judecatorii, tribunale, curti de apel, "
                        "ICCJ, CNSC), cu filtre reale ale platformei: instanta, tip de hotarare, solutie, "
                        "sediu, obiect al cauzei, domeniu, stadiu procesual, interval de date. "
                        "Returneaza pentru fiecare hotarare instanta, numarul, data, obiectul si URL-ul, "
                        "plus nro/versionId pentru descarcarea textului integral. "
                        "Filtrele care nu se potrivesc sunt raportate explicit in 'filtre_nepotrivite', "
                        "deci un rezultat mai larg decat filtrul cerut nu trece neobservat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termeni de cautare, ex: 'Legea 295/2004 anulare permis port arma'"},
                    "instanta": {"type": ["string", "array"], "items": {"type": "string"}, "description": "Tipul instantei: 'Curtea de Apel', 'Tribunalul', 'Judecatoria', 'ICCJ', 'CNSC'"},
                    "tip_hotarare": {"type": ["string", "array"], "items": {"type": "string"}, "description": "'Sentinta', 'Decizie', 'Incheiere', 'Hotarare'"},
                    "solutie": {"type": ["string", "array"], "items": {"type": "string"}, "description": "'Admis', 'Admis in parte', 'Respins', 'Achitat' etc."},
                    "sediu": {"type": ["string", "array"], "items": {"type": "string"}, "description": "Localitatea instantei, ex: 'Bucuresti', 'Cluj', 'Timisoara'"},
                    "obiect": {"type": ["string", "array"], "items": {"type": "string"}, "description": "Obiectul cauzei, ex: 'anulare act administrativ'"},
                    "domeniu": {"type": ["string", "array"], "items": {"type": "string"}, "description": "'Drept penal', 'Drept administrativ', 'Drept civil' etc."},
                    "stadiu": {"type": ["string", "array"], "items": {"type": "string"}, "description": "'Fond', 'Apel', 'Recurs' etc."},
                    "sectie": {"type": ["string", "array"], "items": {"type": "string"}, "description": "Sectia instantei"},
                    "data_de_la": {"type": "string", "description": "Data minima a hotararii, format YYYY-MM-DD"},
                    "data_pana_la": {"type": "string", "description": "Data maxima a hotararii, format YYYY-MM-DD"},
                    "sort_by_date": {"type": "boolean", "description": "Cele mai recente hotarari primele", "default": False},
                    "max_results": {"type": "integer", "description": "Numar maxim de rezultate (default 20, maximum 100)", "default": 20},
                    "start_from": {"type": "integer", "description": "Offset pentru paginare (default 0)", "default": 0},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="sintact_jurisprudence_filters",
            description="Listeaza filtrele DISPONIBILE pentru o cautare de jurisprudenta pe sintact.ro, "
                        "cu etichetele exacte si numarul de hotarari pentru fiecare (instante, tipuri de "
                        "hotarare, solutii, sedii, obiecte ale cauzei, domenii). Apeleaza acest tool "
                        "INAINTE de a filtra, ca filtrele sa fie alese din valori reale, nu ghicite.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termenii cautarii pentru care vrei filtrele"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="sintact_fetch_document",
            description="Descarca textul integral al unui document de pe sintact.ro dupa nro/versionId "
                        "(obtinute din sintact_search, sintact_search_jurisprudence sau "
                        "sintact_verify_citation). Merge si pentru acte normative, si pentru hotarari "
                        "judecatoresti, inclusiv considerentele complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "nro": {"type": "integer", "description": "Identificatorul intern al documentului (camp 'nro')"},
                    "versionId": {"type": "integer", "description": "Versiunea documentului (camp 'versionId')"},
                    "max_chars": {"type": "integer", "description": "Limiteaza textul returnat (0 = integral)", "default": 0},
                },
                "required": ["nro", "versionId"],
            },
        ),
        types.Tool(
            name="lege5_search",
            description="LEGACY, ultima rezervă. Căutare full-text pe lege5.ro (vechea platformă Indaco). "
                        "Sursa primară este sintact.ro. Contul lege5 poate să nu fie configurat.",
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
            description="Verifica in lot mai multe decizii CCR, in paralel pe sursa oficiala, cu sumar la final. Maximum 12 decizii per apel; pentru mai multe, imparte in loturi si apeleaza de mai multe ori.",
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
                        "description": "Lista de decizii CCR de verificat (maximum 12)",
                        "maxItems": 12,
                    },
                },
                "required": ["decisions"],
            },
        ),
    ]

    rank = {name: i for i, name in enumerate(_TOOL_ORDER)}
    return sorted(tools, key=lambda t: rank.get(t.name, len(rank)))


# ── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────

# ORDINEA SURSELOR COMERCIALE (stabilita 2026-07-27)
#   sintact.ro se interogheaza intotdeauna primul: abonamentul e activ, sesiunea se
#   autentifica si acopera legislatia, jurisprudenta nationala si doctrina.
#   lege6.ro si lege5.ro se incearca DOAR daca sesiunea sintact nu se ridica, fiindca
#   nu au credentiale valide (claude_desktop_config.json le tine pe placeholder) si
#   altfel ar consuma timp esuand tacut inaintea sursei care functioneaza.
#   legislatie.just.ro ramane pe pozitia a doua, ca sursa oficiala publica; ordinea
#   ceruta priveste doar raportul dintre sintact, lege5 si lege6.


def _sintact_unavailable(result: dict) -> bool:
    """Sesiunea sintact a cazut, deci sursele de rezerva devin justificate.
    Decizia negasita pe o sesiune sanatoasa NU intra aici: ea inseamna ca sintact a
    raspuns si nu are documentul, iar lege5/lege6 nu au cum sa fie mai bogate."""
    return bool(result.get("auth_failed"))


async def _search_ccr_both(number: int, year: int) -> dict:
    """Cauta o decizie CCR: sintact.ro -> legislatie.just.ro -> (lege6/lege5, doar
    daca autentificarea sintact a esuat)."""
    errors = []
    sintact_down = False

    # 1. sintact.ro (PRIORITAR, abonament activ)
    try:
        result = await sintact_search_ccr(sintact_session, number, year)
        if result.get("found"):
            return result
        sintact_down = _sintact_unavailable(result)
        errors.append(("sintact.ro", result.get("error", "decizia nu a fost gasita")))
    except Exception as e:
        logger.warning("sintact.ro unavailable: %s", e)
        sintact_down = True
        errors.append(("sintact.ro", str(e)))

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

    # 3. Rezerva Indaco, numai cu sintact cazut.
    if not sintact_down:
        return {"found": False, "errors": errors,
                "error": f"Decizia CCR nr. {number}/{year} nu a fost gasita pe sintact.ro "
                         f"si nici pe legislatie.just.ro."}

    for label, fn, session in (("lege6.ro", lege6_search_ccr, lege6_session),
                               ("lege5.ro", lege5_search_ccr, lege5_session)):
        try:
            result = await fn(session, number, year)
            if isinstance(result, dict) and result.get("found"):
                return result
            errors.append((label, "decizia nu a fost gasita"))
        except Exception as e:
            errors.append((label, str(e)))

    return {"found": False, "errors": errors,
            "error": "Decizia nu a fost gasita pe niciuna din sursele disponibile."}


# Peste acest prag lotul depaseste fereastra de asteptare a clientului MCP
# (Claude Desktop taie apelul in jur de 60s), asa ca il refuzam explicit, cu
# instructiunea de a-l imparti, in loc sa-l lasam sa expire fara raspuns.
BATCH_MAX = 12
# Cate verificari merg simultan pe sursa oficiala. Peste 4 nu mai castigam timp
# si incepem sa incarcam inutil just.ro.
BATCH_CONCURRENCY = 4


async def _batch_verify(decisions: list) -> list:
    """Verifica un lot de decizii CCR.

    Sursa oficiala (legislatie.just.ro, prin httpx) merge in paralel: e de circa
    patru ori mai rapida decat calea prin browser si, spre deosebire de ea, se
    poate apela concurent, sesiunile Playwright avand o singura pagina fiecare.
    Ce nu se rezolva acolo trece secvential prin lantul complet lege6 -> just.ro
    -> lege5, ca sa nu pierdem deciziile pe care doar sursele comerciale le au.
    """
    sem = asyncio.Semaphore(BATCH_CONCURRENCY)

    def _looks_like_ccr(text: str) -> bool:
        """Textul chiar provine de la Curtea Constitutionala? Acelasi numar de decizie
        exista in acelasi an la ICCJ, Guvern sau prim-ministru. Cautarea merge pe text
        pliat, deci nu depinde de grafia diacriticelor din sursa."""
        head = fold_diacritics((text or "")[:4000])
        return "curtea constitutionala" in head or "neconstitutionalitate" in head

    async def official(dec: dict) -> tuple:
        async with sem:
            try:
                r = await fetch_ccr_text(dec["number"], dec["year"])
                return dec, (r.get("text") or "")
            except Exception as e:
                logger.warning("just.ro batch fetch %s/%s: %s", dec["number"], dec["year"], e)
                return dec, ""

    fetched = await asyncio.gather(*(official(d) for d in decisions))

    results = []
    for dec, text in fetched:
        if text and not _looks_like_ccr(text):
            # Cautarea dupa numar pe just.ro confunda emitentii: pe "358/2022" a intors
            # o decizie de numire a unui secretar de stat. Un text care nu poarta semnul
            # Curtii ar produce un verdict INCORRECT pe o citare reala, deci se arunca
            # si se reia pe lantul complet, care incepe cu sintact.
            logger.info("batch %s/%s: textul just.ro nu pare decizie CCR, reiau pe lantul complet",
                        dec["number"], dec["year"])
            text = ""
        if not text:
            # Rezerva completa, inclusiv caile prin browser, care se serializeaza.
            try:
                text = (await _fetch_ccr_text_both(dec["number"], dec["year"])).get("text") or ""
            except Exception as e:
                logger.warning("fallback batch fetch %s/%s: %s", dec["number"], dec["year"], e)
        v = (_verify_citation(text, dec["claimed_subject"]) if text
             else {"verdict": "UNVERIFIABLE", "actual_subject": ""})
        results.append({
            "key": f"DCC {dec['number']}/{dec['year']}",
            "verdict": v["verdict"],
            "actual_subject": v.get("actual_subject", ""),
        })
    return results


async def _fetch_ccr_text_both(number: int, year: int) -> dict:
    """Descarca textul unei decizii CCR, cu aceeasi ordine ca `_search_ccr_both`:
    sintact.ro -> legislatie.just.ro -> (lege6/lege5, doar cu sintact cazut)."""
    errors = []
    sintact_down = False

    # 1. sintact.ro PRIORITAR
    try:
        result = await sintact_fetch_ccr(sintact_session, number, year)
        if result.get("text"):
            return result
        sintact_down = _sintact_unavailable(result)
        errors.append(("sintact.ro", result.get("error", "fara text")))
    except Exception as e:
        logger.warning("sintact.ro fetch error: %s", e)
        sintact_down = True
        errors.append(("sintact.ro", str(e)))

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

    # 3. Rezerva Indaco, numai cu sintact cazut.
    if not sintact_down:
        return {"text": "", "errors": errors,
                "error": "Textul deciziei nu a putut fi extras de pe sintact.ro sau legislatie.just.ro."}

    for label, fn, session in (("lege6.ro", lege6_fetch_ccr, lege6_session),
                               ("lege5.ro", lege5_fetch_ccr, lege5_session)):
        try:
            result = await fn(session, number, year)
            if result.get("text"):
                return result
            errors.append((label, result.get("error", "fara text")))
        except Exception as e:
            errors.append((label, str(e)))

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

    # Se ia potrivirea cea mai APROPIATA de inceputul textului, nu prima din lista de
    # tipare. Titlul deciziei deschide documentul ("... referitoare la exceptia de
    # neconstitutionalitate a ..."), insa tiparul cu 'privind' apare mai devreme in
    # lista si prindea numele legii criticate din considerente, de unde subiecte
    # extrase gresit si verdicte INCORRECT pe citari perfect reale.
    best = None
    for p in subject_patterns:
        match = re.search(p, intro)
        if match and (best is None or match.start() < best.start()):
            best = match
    if best:
        actual_subject = best.group(1).strip()[:200]

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

    # Sinonimele sunt scrise cu diacritice in tabel; se pliaza o data, ca sa traiasca
    # in acelasi alfabet cu cuvintele comparate.
    folded_synonyms = {fold_diacritics(k): {fold_diacritics(v) for v in syns}
                       for k, syns in SYNONYMS.items()}

    def expand_words(words):
        expanded = set(words)
        for w in list(words):
            for key, syns in folded_synonyms.items():
                if w == key or w in syns:
                    expanded.add(key)
                    expanded.update(syns)
        return expanded

    # Compararea se face pe text pliat, fara diacritice. Documentele oficiale le poarta,
    # iar subiectul pretins vine deseori tastat fara ele; comparate ca siruri brute,
    # 'excepţia' si 'exceptia' nu se potrivesc, iar scorul cade pana la INCORRECT pe o
    # decizie perfect reala. Masurat pe Decizia 358/2022, 'exceptie de
    # neconstitutionalitate' scadea de la CONFIRMED 0,70 la INCORRECT 0,00.
    claimed_words = set(re.findall(r'\b\w{3,}\b', fold_diacritics(claimed_subject)))
    claimed_expanded = expand_words(claimed_words)
    actual_words = set(re.findall(r'\b\w{3,}\b', fold_diacritics(actual_subject)))

    if not claimed_words:
        return {"verdict": "UNVERIFIABLE", "actual_subject": actual_subject, "relevance_score": 0.0, "evidence": ""}

    # Plafonat la 1: extinderea cu sinonime poate produce mai multe potriviri decat
    # cuvinte cerute, iar un scor de 1,4 raportat ca "relevanta" deruteaza cititorul.
    overlap = claimed_expanded & actual_words
    score = min(1.0, len(overlap) / len(claimed_words)) if claimed_words else 0.0

    # Also check full text (first 10000 chars, not just 2000). Pliat, ca si mai sus;
    # `fold_diacritics` pastreaza lungimea, deci pozitiile raman valabile pe `text`.
    full_lower = fold_diacritics(text[:10000])
    full_hits = sum(1 for w in claimed_expanded if w in full_lower)
    full_score = min(1.0, full_hits / len(claimed_words)) if claimed_words else 0.0

    combined_score = max(score, full_score * 0.7)

    # Check claimed principle
    principle_found = ""
    if claimed_principle:
        folded_principle = fold_diacritics(claimed_principle)
        if folded_principle in full_lower:
            principle_found = claimed_principle
            combined_score = min(1.0, combined_score + 0.3)
        else:
            # Fuzzy: check if most words from principle are in text
            principle_words = set(re.findall(r'\b\w{4,}\b', folded_principle))
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
_TYPE_ALIASES = ("type", "tip", "tip_act", "act_kind", "kind")
_QUERY_ALIASES = ("query", "citation", "citare", "act", "act_title", "title", "titlu", "text", "q")
_LEGISLATION_TOOLS = {"search_legislation", "fetch_article_text", "lege6_search_legislation"}

# Tipurile pe care le inteleg legislatie.just.ro si lege6: forma canonica la stanga
# apelului, oricat de liber ar fi scris tipul in cerere ('Legea', 'O.U.G.', 'H.G.').
# Ordinea conteaza, formele lungi se testeaza inaintea celor scurte, altfel
# "ordonanta de urgenta" ar fi citita ca simpla "ordonanta".
_ACT_KIND_PATTERNS = (
    (r"constitut(?:ia|ie|iei)", "constitutie"),
    (r"ordonant[ae]\s+de\s+urgent[ae](?:\s+a\s+guvernului)?", "oug"),
    (r"\bo\.?\s?u\.?\s?g\.?", "oug"),
    (r"ordonant[ae](?:\s+a)?(?:\s+guvernului)?", "og"),
    (r"\bo\.?\s?g\.?(?=\W|$)", "og"),
    (r"hotarare[a]?(?:\s+(?:de\s+)?guvernului?)?", "hg"),
    (r"\bh\.?\s?g\.?", "hg"),
    (r"\bleg(?:ea|ii|e)\b", "lege"),
    (r"\bl\.?\s*(?=nr\.?|\d)", "lege"),
    (r"\bordin(?:ul)?\b", "ordin"),
    (r"\bcod(?:ul|ului)?\b", "cod"),
    (r"\bdecret(?:ul)?\b", "decret"),
)

_NUM_YEAR_RE = re.compile(r"\b(\d{1,5})\s*[/\-]\s*((?:1[89]|20)\d{2})\b")
_NUM_DIN_YEAR_RE = re.compile(r"\bnr\.?\s*(\d{1,5})\b\D{1,25}?\b((?:1[89]|20)\d{2})\b")
_ART_RE = re.compile(r"\bart(?:icolul|\.|\b)\s*(\d{1,4})")
_ALIN_RE = re.compile(r"\balin(?:eatul|\.|\b)\s*\(?\s*(\d{1,3})\s*\)?")
_LIT_RE = re.compile(r"\blit(?:era|\.|\b)\s*\(?\s*([a-z])\s*\)?")


def _canon_act_type(value) -> Optional[str]:
    """Pliaza orice scriere a tipului de act pe forma canonica ceruta de clienti."""
    if value is None:
        return None
    folded = fold_diacritics(str(value)).strip()
    if not folded:
        return None
    for pattern, canon in _ACT_KIND_PATTERNS:
        if re.fullmatch(pattern, folded) or re.fullmatch(pattern + r"\.?", folded):
            return canon
    for pattern, canon in _ACT_KIND_PATTERNS:
        if re.search(pattern, folded):
            return canon
    return folded.lower()


def _parse_citation(text) -> dict:
    """Sparge o citare scrisa in text liber ('art. 3 alin. (2) din Legea 58/2023')
    in campurile pe care le asteapta clientii. Modelul cheama tool-urile de
    legislatie ca pe orice alta cautare, cu un singur sir, iar fara pasul asta
    apelul cadea pe validarea de schema inainte sa ajunga la server."""
    out: dict = {}
    if not text:
        return out
    t = fold_diacritics(str(text))

    m = _NUM_YEAR_RE.search(t) or _NUM_DIN_YEAR_RE.search(t)
    if m:
        out["number"] = int(m.group(1))
        out["year"] = int(m.group(2))

    # Tipul actului e cel scris cel mai aproape INAINTEA numarului: in "lege de
    # aprobare a OUG 155/2024" numarul apartine ordonantei, nu legii.
    limit = m.start() if m else len(t)
    best = None
    for pattern, canon in _ACT_KIND_PATTERNS:
        for hit in re.finditer(pattern, t):
            if hit.start() >= limit:
                continue
            key = (hit.start(), hit.end() - hit.start())
            if best is None or key > best[0]:
                best = (key, canon)
    if best is None and not m:
        for pattern, canon in _ACT_KIND_PATTERNS:
            hit = re.search(pattern, t)
            if hit:
                best = (((hit.start(), hit.end() - hit.start())), canon)
                break
    if best is not None:
        out["act_type"] = best[1]

    m_art = _ART_RE.search(t)
    if m_art:
        out["article"] = int(m_art.group(1))
        m_alin = _ALIN_RE.search(t, m_art.end())
        if m_alin:
            out["alineat"] = int(m_alin.group(1))
        m_lit = _LIT_RE.search(t, m_art.end())
        if m_lit:
            out["litera"] = m_lit.group(1)
    return out


def _dedupe_candidates(items) -> list:
    """Lista de candidati e ceruta ca sa aleaga modelul, deci randurile de navigare
    ('Vizualizeaza') si acelasi doc_id repetat nu au ce cauta in ea."""
    seen, out = set(), []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title", "")).strip()
        if fold_diacritics(title) in ("vizualizeaza", ""):
            continue
        key = it.get("doc_id") or it.get("url") or title
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _normalize_args(args: dict, name: str = "") -> dict:
    """Accepta aliasurile pe care modelul le trimite frecvent (act_number/act_year),
    citarea data ca text liber, si coercitioneaza numerele date ca text ('334' -> 334).
    Fara acest strat, apeluri corecte semantic esueaza pe nepotriviri de nume/tip."""
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
    if a.get("act_type") is None:
        for alt in _TYPE_ALIASES:
            if a.get(alt) is not None:
                a["act_type"] = a[alt]
                break
    for k in ("number", "year", "article", "alineat", "limit", "max_results"):
        v = a.get(k)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            a[k] = int(v)

    if name in _LEGISLATION_TOOLS:
        free_text = next((a[k] for k in _QUERY_ALIASES if isinstance(a.get(k), str) and a[k].strip()), None)
        if free_text:
            a["query"] = free_text
            parsed = _parse_citation(free_text)
            for k, v in parsed.items():
                if a.get(k) in (None, ""):
                    a[k] = v
        a["act_type"] = _canon_act_type(a.get("act_type"))
        if a.get("act_type") is None:
            a.pop("act_type", None)
    return a


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        arguments = _normalize_args(arguments, name)
        if name in _LEGISLATION_TOOLS:
            # Constitutia nu are numar si an, se identifica prin doc_id fix, deci
            # cerinta de number/year nu i se aplica.
            if arguments.get("act_type") == "constitutie":
                arguments.setdefault("number", 0)
                arguments.setdefault("year", 1991)

            missing = [k for k in ("act_type", "number", "year") if arguments.get(k) in (None, "")]
            if name == "fetch_article_text" and arguments.get("article") in (None, ""):
                missing.append("article")

            if missing:
                # Recuperare eleganta: in loc de eroare seaca, cautam full-text dupa
                # indiciile disponibile si intoarcem candidati cu an, ca modelul sa reapeleze precis.
                number, year = arguments.get("number"), arguments.get("year")
                hint = (arguments.get("query") or " ".join(
                    str(arguments[k]) for k in ("act_type", "number", "year") if arguments.get(k) is not None
                )).strip()
                candidates = []
                # Cand numarul si anul se stiu, dar nu si tipul, cautarea pe campurile
                # structurate ale formularului intoarce chiar actele cu acel numar din
                # acel an, in loc de zgomotul unei cautari de text dupa "58 2023".
                structured = number is not None and year is not None
                if structured:
                    try:
                        candidates = await search_document(
                            query=str(arguments.get("act_type") or ""),
                            doc_number=str(number), date_from=str(year), date_to=str(year),
                        )
                    except Exception:
                        candidates = []
                if not candidates and hint:
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
                candidates = _dedupe_candidates(candidates)[:8]
                return [types.TextContent(type="text", text=json.dumps({
                    "note": "Apelul a fost incomplet, lipsea " + ", ".join(f"'{k}'" for k in missing) +
                            ". Am căutat full-text după indiciile date. Alege actul potrivit din "
                            "'candidates' și reapelează cu act_type + number + year, sau trimite "
                            "citarea întreagă în 'query' (ex: 'Legea 58/2023').",
                    "missing": missing,
                    "query_used": hint,
                    "candidates": candidates,
                    "resolved": {k: arguments.get(k) for k in ("act_type", "number", "year", "article")
                                 if arguments.get(k) is not None},
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

        elif name == "sintact_verify_citation":
            result = await sintact_verify_citation_fn(sintact_session, arguments["query"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sintact_search":
            result = await sintact_search_fn(
                sintact_session,
                arguments["query"],
                arguments.get("category"),
                arguments.get("max_results", 10),
                arguments.get("start_from", 0),
                arguments.get("sort_by_date", False),
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sintact_search_jurisprudence":
            result = await sintact_search_jurisprudence_fn(
                sintact_session,
                arguments["query"],
                instanta=arguments.get("instanta"),
                tip_hotarare=arguments.get("tip_hotarare"),
                solutie=arguments.get("solutie"),
                sediu=arguments.get("sediu"),
                obiect=arguments.get("obiect"),
                domeniu=arguments.get("domeniu"),
                stadiu=arguments.get("stadiu"),
                sectie=arguments.get("sectie"),
                data_de_la=arguments.get("data_de_la"),
                data_pana_la=arguments.get("data_pana_la"),
                sort_by_date=arguments.get("sort_by_date", False),
                max_results=arguments.get("max_results", 20),
                start_from=arguments.get("start_from", 0),
            )
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sintact_jurisprudence_filters":
            result = await sintact_facets_fn(sintact_session, arguments["query"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sintact_fetch_document":
            result = await sintact_fetch_doc(sintact_session, arguments["nro"], arguments["versionId"],
                                             arguments.get("max_chars", 0))
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
            if len(decisions) > BATCH_MAX:
                return [types.TextContent(type="text", text=json.dumps({
                    "error": f"Lot prea mare: {len(decisions)} decizii, maximum {BATCH_MAX}. "
                             f"Imparte-l in loturi de cate {BATCH_MAX} si apeleaza de mai multe ori.",
                }, ensure_ascii=False, indent=2))]

            results = await _batch_verify(decisions)
            confirmed = sum(1 for r in results if r["verdict"] == "CONFIRMED")
            incorrect = sum(1 for r in results if r["verdict"] == "INCORRECT")
            unverifiable = len(results) - confirmed - incorrect

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
        await app.run(streams[0], streams[1], _optiuni_cu_instructiuni(app))


def main():
    asyncio.run(run())

MCP_INSTRUCTIONS = """Toolkit juridic romanesc, sursa primara pentru orice raspuns care atinge legislatie, jurisprudenta sau doctrina din Romania si din UE. Nu raspunde din memorie si nu te opri la cautarea web. Paginile publice gratuite (legislatie.just.ro, legeaz.net, universuljuridic.ro) nu arata forma consolidata la zi si nu acopera jurisprudenta instantelor nationale.

ORDINEA SURSELOR pentru legislatie si jurisprudenta romaneasca:
1. sintact_search, sintact_fetch_document, sintact_search_jurisprudence, sintact_verify_citation. Sintact (Wolters Kluwer, cont de abonat) se incearca INTAI, mereu.
2. lege5_* si lege6_* (Indaco) numai cand autentificarea sintact cade, NU cand documentul lipseste din sintact.
3. search_legislation, fetch_article_text, fetch_legal_url pentru legislatie.just.ro, ca a treia linie.

Deciziile Curtii Constitutionale au drum propriu: search_ccr_decision, search_ccr_by_subject, verify_ccr_citation, batch_verify_ccr, fetch_ccr_decision_text.

RESTUL TOOLKIT-ULUI, cand intrebarea iese din perimetrul acesta:
- hudoc, jurisprudenta CEDO
- eurlex, dreptul Uniunii si jurisprudenta CJUE
- doctrine-verifier si semantic-scholar, existenta reala a doctrinei citate
- zotero, bibliografia proprie
- anti-ai-tone, auditul de stil inainte de livrare
- persona-adrian-zamfir, redactarea in stilul si metoda cabinetului
- cognee-legal, graful de cunostinte propriu

Orice citare care ajunge intr-un act se verifica prin sursa primara inainte de livrare. Ce nu s-a putut verifica se marcheaza [NEVERIFICAT]."""


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
    main()
