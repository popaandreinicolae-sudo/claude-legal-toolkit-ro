# -*- coding: utf-8 -*-
"""Verifica AFIRMATIILE despre ce a decis o hotarare, nu doar existenta citarii.

Stratul existent verifica doua lucruri: ca decizia citata exista (citation_guard) si
ca un citat intre ghilimele apare chiar in ea (verify_attribution). Amandoua cheia pe
citare sau pe ghilimele. O propozitie care SPUNE ce a decis instanta, fara sa citeze,
nu atinge niciun strat.

Asa a trecut, pe 31 iulie 2026, propozitia "Curtea a constatat neconstitutionalitatea
unei singure sintagme [...] astfel a procedat prin Decizia nr. 363/2015 si prin Decizia
nr. 603/2015". Citarile erau reale, verificate, iar textul deciziilor fusese citit in
aceeasi sesiune. Numai ca dispozitivul Deciziei nr. 363/2015 spune "dispozitiile art. 6
din Legea nr. 241/2005 [...] sunt neconstitutionale", adica articolul intreg, iar opinia
separata reproseaza tocmai ca efectele s-au rasfrant asupra intregului articol.

Verificarea de aici compara ce sustine textul cu DISPOZITIVUL real:
  - solutia pretinsa (admisa / respinsa) fata de solutia din dispozitiv;
  - intinderea pretinsa (o sintagma / textul integral) fata de ce a cazut efectiv.

Consultativ si fail-open, ca tot stratul. Nu blocheaza, iese mereu cu 0.
Sursa e sintact, cu just.ro doar ca rezerva, marcata in raport.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import zipfile
from pathlib import Path

_AICI = Path(__file__).resolve().parent
_CACHE = _AICI / ".dispozitiv_cache.json"
_LEGAL_SRC = _AICI.parent / "mcp-servers" / "legal-verificator-ro" / "src" / "legal_verificator"
_TTL = 30 * 24 * 3600

# ------------------------------------------------------------------ tipare

_LUNI = r"(?:ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)"

RE_DECIZIE = re.compile(
    r"Deciz(?:ia|iei|iile|iilor)\s+"
    r"(?:Cur[tţţ]ii\s+Constitu[tţ]ionale\s+)?"
    r"(?:nr\.?\s*)?(\d{1,4})\s*"
    r"(?:/\s*(\d{4})|din\s+\d{1,2}\s+" + _LUNI + r"\s+(\d{4}))",
    re.IGNORECASE,
)

# Verbe prin care textul AFIRMA o solutie. Fara ele, citarea e doctrinara si nu se verifica.
RE_ADMIS = re.compile(
    r"a\s+admis|admi[tţ][âa]nd|a\s+constatat\s+neconstitu|constat[âa]nd\s+neconstitu"
    r"|a\s+declarat\s+neconstitu|(?:este|sunt|era|erau)\s+neconstitu"
    r"|neconstitu[tţ]ionalitatea\s+(?:unei|unor|sintagmei|dispozi|art)",
    re.IGNORECASE,
)
RE_RESPINS = re.compile(
    r"a\s+respins|respins[ăa]\s+ca\s+(?:neintemeiat|ne[îi]ntemeiat|inadmisibil)"
    r"|a\s+constatat\s+constitu[tţ]ionalitatea",
    re.IGNORECASE,
)
RE_SINTAGMA = re.compile(r"sintagm", re.IGNORECASE)

# In dispozitiv.
RE_D_ADMITE = re.compile(r"\bAdmite\b", re.IGNORECASE)
RE_D_RESPINGE = re.compile(r"\bRespinge\b", re.IGNORECASE)


def _fara_diacritice(s: str) -> str:
    tab = str.maketrans({
        "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
        "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T",
    })
    return s.translate(tab)


# ------------------------------------------------------------------ citire document

def citeste(cale: Path) -> str:
    if cale.suffix.lower() == ".docx":
        try:
            from lxml import etree
        except ImportError:
            return ""
        W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        z = zipfile.ZipFile(cale)
        bucati = []
        for parte in ("word/document.xml", "word/footnotes.xml"):
            try:
                rad = etree.fromstring(z.read(parte))
            except KeyError:
                continue
            for p in rad.iter("{%s}p" % W):
                text = []
                for r in p.iter("{%s}r" % W):
                    parinte = r.getparent()
                    if parinte is not None and etree.QName(parinte).localname == "del":
                        continue          # textul sters nu se mai verifica
                    text.append("".join((t.text or "") for t in r.iter("{%s}t" % W)))
                linie = "".join(text).strip()
                if linie:
                    bucati.append(linie)
        return "\n".join(bucati)
    return cale.read_text(encoding="utf-8", errors="replace")


def propozitii(text: str) -> list:
    """Taie pe punct, dar nu pe abrevierile juridice ('art.', 'nr.', 'alin.')."""
    protejat = re.sub(
        r"\b(art|nr|alin|lit|pct|pt|par|paragr|dec|Dec|H\.G|O\.U\.G|O\.G|M\.\s?Of)\.",
        lambda m: m.group(0)[:-1] + "\x00", text)
    brute = re.split(r"(?<=[.!?])\s+|\n", protejat)
    return [b.replace("\x00", ".").strip() for b in brute if b.strip()]


# ------------------------------------------------------------------ sursa

def _cache_citeste() -> dict:
    try:
        d = json.loads(_CACHE.read_text(encoding="utf-8"))
        return {k: v for k, v in d.items() if time.time() - v.get("_t", 0) < _TTL}
    except Exception:
        return {}


def _cache_scrie(d: dict) -> None:
    try:
        _CACHE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def taie_dispozitiv(text: str) -> str:
    """Partea de dupa 'DECIDE:', pana la formula de incheiere."""
    fd = _fara_diacritice(text)
    m = None
    for tipar in (r"[ÎI]n\s+numele\s+legii\s*DECIDE\s*:", r"\bDECIDE\s*:", r"\bDECIDE\b"):
        m = re.search(tipar, fd, re.IGNORECASE)
        if m:
            break
    if not m:
        return ""
    rest = text[m.end():]
    stop = re.search(r"Definitiv[ăa]\s+[şsş]i\s+general|Pronun[tţ]at[ăa]\s+[îi]n\s+[şs]edin",
                     _fara_diacritice(rest), re.IGNORECASE)
    return (rest[:stop.start()] if stop else rest[:4000]).strip()


async def _adu_toate_sintact(nevoi: list) -> dict:
    """O SINGURA sesiune sintact pentru toate deciziile din document.

    Licenta e pe sesiune unica: a doua sesiune deschisa in paralel arunca prima pe SSO,
    iar `fetch` esueaza cu "Failed to fetch". Prima versiune a scriptului deschidea cate
    o sesiune pe decizie, asa incat doar prima citare se confirma pe sintact, iar restul
    cadeau pe sursa de rezerva. De aici si concluziile pe un text trunchiat.
    """
    if str(_LEGAL_SRC) not in sys.path:
        sys.path.insert(0, str(_LEGAL_SRC))
    from auth import SintactSession                      # noqa: E402
    import sintact_client as S                           # noqa: E402

    rezultat = {}
    sesiune = SintactSession()
    try:
        for numar, an in nevoi:
            cheie = "ccr:%s/%s" % (numar, an)
            try:
                r = await S.fetch_ccr_text(sesiune, int(numar), int(an))
                if r.get("text"):
                    rezultat[cheie] = {"sursa": "sintact", "titlu": r.get("title", ""),
                                       "text": r["text"]}
                    continue
                cauta = await S.search_ccr_decision(sesiune, int(numar), int(an))
                if cauta.get("found"):
                    rezultat[cheie] = {"sursa": "sintact", "titlu": cauta.get("title", ""),
                                       "text": ""}
                    continue
                rezultat[cheie] = {"eroare": "negasita pe sintact"}
            except Exception as e:
                rezultat[cheie] = {"eroare": "%s: %s" % (type(e).__name__, e)}
    finally:
        inchide = getattr(sesiune, "close", None)
        if inchide:
            try:
                res = inchide()
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass
    return rezultat


async def _adu_toate_justro(nevoi: list) -> dict:
    """Linia a doua, legislatie.just.ro, cu textul INTEGRAL.

    `fetch_ccr_text` taie inteligent la 30.000 de caractere, pastrand primele 15.000 si
    ultimele 5.000, tocmai ca sa nu piarda dispozitivul. Pentru verificarea unui paragraf
    din mijloc, insa, taietura strica tocmai partea cautata, asa ca se cere textul brut
    prin `fetch_printable`, care nu are plafon.
    """
    if str(_LEGAL_SRC) not in sys.path:
        sys.path.insert(0, str(_LEGAL_SRC))
    import legislatie_client as L                        # noqa: E402

    rezultat = {}
    for numar, an in nevoi:
        cheie = "ccr:%s/%s" % (numar, an)
        try:
            gasit = await L.search_ccr(int(numar), int(an))
            if not gasit.get("found") or not gasit.get("doc_id"):
                rezultat[cheie] = {"eroare": "negasita nici pe sintact, nici pe just.ro"}
                continue
            text, url = await L.fetch_printable(gasit["doc_id"])
            # O decizie a Curtii nu are 1.300 de caractere. Cand cautarea dupa numar da un
            # alt document, sau o pagina-ciot, textul e scurt: 22/2016 a venit asa. Mai bine
            # NEVERIFICAT decat un verdict pe documentul gresit, capcana omonimiei pe numar.
            if len(text or "") < 5000:
                rezultat[cheie] = {"eroare": "pe just.ro a venit un text prea scurt pentru o "
                                             "decizie (%d caractere); posibil alt document"
                                             % len(text or "")}
                continue
            rezultat[cheie] = {
                "sursa": "legislatie.just.ro",
                "avertisment_sursa": "sintact nu a raspuns; text luat de pe legislatie.just.ro, "
                                     "care nu garanteaza forma consolidata la zi",
                "titlu": gasit.get("title", ""), "text": text or "", "url": url,
            }
        except Exception as e:
            rezultat[cheie] = {"eroare": "%s: %s" % (type(e).__name__, e)}
    return rezultat


def incarca(nevoi: list, cache: dict) -> dict:
    """Aduce ce lipseste din cache. Sintact intai, apoi legislatie.just.ro, marcat.

    Ordinea e cea din regulile autorului. Sintact ramane singura sursa care garanteaza
    forma la zi, dar pentru textul unei hotarari deja pronuntate linia a doua e utila si
    e mai buna decat lipsa verdictului: pe 31 iulie 2026, Decizia nr. 405/2016 nu a putut
    fi identificata pe sintact, fiindca `_ccr_candidates` izoleaza emitentul prin fateta
    `authors`, iar pentru acea decizie fateta nu se rezolva si functia iese cu lista goala.
    Ce vine de pe linia a doua poarta `avertisment_sursa` si se raporteaza ca atare.
    """
    lipsa = [(n, a) for n, a in nevoi if "ccr:%s/%s" % (n, a) not in cache]
    if not lipsa:
        return cache
    try:
        proaspete = asyncio.run(_adu_toate_sintact(lipsa))
    except Exception as e:
        proaspete = {"ccr:%s/%s" % (n, a): {"eroare": "%s" % type(e).__name__}
                     for n, a in lipsa}

    ramase = [(n, a) for n, a in lipsa if not proaspete.get("ccr:%s/%s" % (n, a), {}).get("text")]
    if ramase:
        try:
            proaspete.update(asyncio.run(_adu_toate_justro(ramase)))
        except Exception:
            pass

    for cheie, date in proaspete.items():
        date["_t"] = time.time()
        cache[cheie] = date
    return cache


# ------------------------------------------------------------------ analiza

def solutie_reala(date: dict) -> str:
    titlu = date.get("titlu", "") or ""
    if re.search(r"\[\s*A\s*\]", titlu):
        return "ADMIS"
    if re.search(r"\[\s*R\s*\]", titlu):
        return "RESPINS"
    disp = taie_dispozitiv(date.get("text", "") or "")
    if RE_D_ADMITE.search(disp):
        return "ADMIS"
    if RE_D_RESPINGE.search(disp):
        return "RESPINS"
    return "NECUNOSCUT"


def intindere_reala(date: dict) -> tuple:
    """('SINTAGMA'|'INTEGRAL'|'NECUNOSCUT', extras din dispozitiv)."""
    disp = taie_dispozitiv(date.get("text", "") or "")
    if not disp:
        return "NECUNOSCUT", ""
    extras = " ".join(disp.split())[:400]
    if RE_SINTAGMA.search(disp):
        return "SINTAGMA", extras
    if re.search(r"sunt\s+neconstitu|este\s+neconstitu", _fara_diacritice(disp), re.IGNORECASE):
        return "INTEGRAL", extras
    return "NECUNOSCUT", extras


def _afirmatii(text: str) -> list:
    """Frazele care SPUN ce a decis o instanta, cu deciziile invocate in fiecare."""
    iesire = []
    for fraza in propozitii(text):
        decizii = [(m.group(1), m.group(2) or m.group(3)) for m in RE_DECIZIE.finditer(fraza)]
        if not decizii:
            continue
        if not (RE_ADMIS.search(fraza) or RE_RESPINS.search(fraza)):
            continue                       # citare doctrinara, nu afirma o solutie
        iesire.append((fraza, decizii))
    return iesire


def analizeaza(text: str, cache: dict) -> list:
    afirmatii = _afirmatii(text)
    nevoi = sorted({d for _, decizii in afirmatii for d in decizii})
    incarca(nevoi, cache)                  # o singura sesiune pentru tot documentul

    gasite = []
    for fraza, decizii in afirmatii:
        pretinde_admis = bool(RE_ADMIS.search(fraza))
        pretinde_sintagma = bool(RE_SINTAGMA.search(fraza))
        pretins = "ADMIS" if pretinde_admis else "RESPINS"

        for numar, an in decizii:
            date = cache.get("ccr:%s/%s" % (numar, an), {})
            if not date.get("titlu") and not date.get("text"):
                gasite.append({
                    "nivel": "NEVERIFICAT", "decizie": "%s/%s" % (numar, an),
                    "fraza": fraza[:260],
                    "motiv": date.get("eroare", "decizia nu a putut fi adusa de pe sintact"),
                })
                continue
            real = solutie_reala(date)
            intindere, extras = intindere_reala(date)

            if real != "NECUNOSCUT" and real != pretins:
                gasite.append({
                    "nivel": "EROARE", "decizie": "%s/%s" % (numar, an),
                    "fraza": fraza[:260], "sursa": date.get("sursa", ""),
                    "motiv": "textul sustine %s, dispozitivul spune %s" % (pretins, real),
                    "dispozitiv": extras,
                })
                continue

            if pretinde_sintagma and intindere == "INTEGRAL":
                gasite.append({
                    "nivel": "EROARE", "decizie": "%s/%s" % (numar, an),
                    "fraza": fraza[:260], "sursa": date.get("sursa", ""),
                    "motiv": "textul sustine ca a cazut o SINTAGMA; dispozitivul declara "
                             "neconstitutional textul integral",
                    "dispozitiv": extras,
                })
                continue

            if intindere == "NECUNOSCUT":
                gasite.append({
                    "nivel": "NEVERIFICAT", "decizie": "%s/%s" % (numar, an),
                    "fraza": fraza[:260], "sursa": date.get("sursa", ""),
                    "motiv": "dispozitivul nu a putut fi izolat; verifica manual",
                })
    return gasite


def taci_la_inchidere() -> None:
    """Playwright isi inchide subprocesele dupa bucla, iar `__del__` arunca pe Windows
    'I/O operation on closed pipe'. Zgomot pe stderr, fara efect asupra verdictului."""
    def _ignora(arg):
        if isinstance(getattr(arg, "exc_value", None), ValueError):
            return
        sys.__unraisablehook__(arg)
    sys.unraisablehook = _ignora


def main(argv=None) -> int:
    taci_la_inchidere()
    ap = argparse.ArgumentParser(description="Verifica afirmatiile despre dispozitivul deciziilor citate.")
    ap.add_argument("cale", help=".docx, .md sau .txt")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        text = citeste(Path(a.cale))
    except Exception as e:
        print("nu am putut citi documentul: %s" % e)
        return 0                                          # fail-open

    cache = _cache_citeste()
    try:
        rezultate = analizeaza(text, cache)
    except Exception as e:
        print("verificare intrerupta (%s); stratul e consultativ, nu blocheaza" % type(e).__name__)
        return 0
    _cache_scrie(cache)

    if a.json:
        print(json.dumps(rezultate, ensure_ascii=False, indent=1))
        return 0

    erori = [r for r in rezultate if r["nivel"] == "EROARE"]
    altele = [r for r in rezultate if r["nivel"] != "EROARE"]
    if not rezultate:
        print("nicio afirmatie despre dispozitiv de verificat, sau toate se confirma")
        return 0
    for r in erori:
        print("\nEROARE  Decizia nr. %s" % r["decizie"])
        print("  %s" % r["motiv"])
        print("  in text : %s" % r["fraza"])
        if r.get("dispozitiv"):
            print("  dispozitiv (%s): %s" % (r.get("sursa", "?"), r["dispozitiv"][:300]))
    for r in altele:
        print("\n%s  Decizia nr. %s -> %s" % (r["nivel"], r["decizie"], r["motiv"]))
    print("\n%d afirmatii problematice, %d neverificate" % (len(erori), len(altele)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
