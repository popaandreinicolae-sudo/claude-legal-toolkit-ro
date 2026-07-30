#!/usr/bin/env python3
"""
citation_core.py — extragere si verificare a citarilor juridice romanesti si UE.

Reutilizabil de:
  - hook-ul PostToolUse citation_guard.py (verificare automata la scriere);
  - orice script care vrea sa valideze citari fara a trece prin protocolul MCP.

Verificarea legislatiei/deciziilor RO se face DIRECT prin clientul legislatie_client
al serverului legal-verificator-ro (legislatie.just.ro, gratuit, fara credentiale).
Verificarea statutului actelor UE in vigoare/abrogat se face prin lista de referinta
reference_names.json plus, optional, prin tool-ul MCP eurlex check_in_force.

Cache pe disc cu TTL 7 zile in scripts/.citation_cache.json.
Fail-open: orice eroare de retea/import => verdict NEVERIFICAT, niciodata exceptie.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_CACHE_FILE = _SCRIPT_DIR / ".citation_cache.json"
_REF_FILE = _SCRIPT_DIR / "reference_names.json"
_LEGAL_SRC = _SCRIPT_DIR.parent / "mcp-servers" / "legal-verificator-ro" / "src" / "legal_verificator"

_CACHE_TTL = 7 * 24 * 3600

# ---------------------------------------------------------------- regex

# Formele scrise in litere si cu diacritice sunt cele care ajung in acte, iar tabelul de
# mai jos le rata pana pe 30 iulie 2026: "Hotararea Guvernului nr. 130/2005" era prinsa,
# dar "Hotărârea Guvernului nr. 11/2018" nu, fiindca alternativele erau scrise fara
# diacritice. La fel, "Ordonanța de urgență a Guvernului nr. 158/1999", forma completa de
# citare, trecea nesemnalata. Ordinea alternativelor conteaza: cele lungi stau inaintea
# celor scurte, altfel "Ordonanta" ar inghiti "Ordonanta de urgenta".
_ACT_WORD = (
    r"(Legea|Lege"
    r"|O\.?U\.?G\.?|Ordonan[tțţ]a\s+de\s+urgen[tțţ][aă](?:\s+a\s+Guvernului)?"
    r"|Ordonan[tțţ]a\s+Guvernului|O\.?G\.?|Ordonan[tțţ]a"
    r"|H\.?G\.?|Hot[aă]r[aâ]rea\s+Guvernului|Hot[aă]r[aâ]rea"
    r"|Ordinul|Ordin|Codul)"
)
_NUM_YEAR = r"(\d{1,4})\s*[\/]\s*(\d{4})"

# Permite un token de instanta intre "Decizia" si numar (ICCJ, CCR, nr., a Curtii...).
#
# Data completa e obligatorie in citarea juridica romaneasca, "Decizia nr. 363 din 7 mai
# 2015", si asa scriem in acte. Pattern-ul cerea insa anul imediat dupa "din", deci
# prindea numai forma scurta "Decizia nr. 22/2016" si rata tocmai forma pe care o
# folosim la livrare. Ziua si luna sunt acum optionale intre "din" si an.
# Curtea scrie numerele de peste o mie cu punct, "Decizia nr. 1.205 din 20 septembrie
# 2011". Punctul se accepta la citire si se scoate la normalizare, ca cheia sa fie una
# singura pentru aceeasi decizie.
RE_CCR = re.compile(
    r"Deciz(?:ia|ie|iei|iile|iilor)\b[^\d\n]{0,18}?(\d{1,2}\.\d{3}|\d{1,5})"
    r"\s*(?:\/|din)\s*(?:\d{1,2}\s*[^\d\n]{2,14}?\s*)?(\d{4})",
    re.IGNORECASE)
RE_ACT = re.compile(_ACT_WORD + r"\s*(?:nr\.?\s*)?" + _NUM_YEAR, re.IGNORECASE)
# Formele flexionate conteaza. In textul juridic romanesc actul apare mai des la genitiv
# sau dativ, "potrivit Directivei 2009/73/CE", decat la nominativ. Clasa [aei] prindea
# "Directive" si se oprea inainte de "i" din "Directivei", deci ratam tocmai forma
# dominanta, iar verificarea de act abrogat nu se declansa niciodata pe ea.
RE_DIR = re.compile(r"Directiv(?:elor|ele|ei|a|e)\s*(?:nr\.?\s*)?(\(UE\)\s*)?(\d{1,4})\s*[\/]\s*(\d{1,4})\s*[\/]?\s*(CE|UE|CEE)?", re.IGNORECASE)
# Numerotarea europeana s-a inversat in 2015. Pana atunci numar/an, "Regulamentul nr.
# 1234/2013"; de atunci an/numar, "Regulamentul (UE) 2016/679". Cerand patru cifre la
# final, pattern-ul rata tot ce e adoptat dupa 2015, inclusiv GDPR. Acum accepta ambele
# ordini, iar anul se recunoaste dupa forma lui.
RE_REG = re.compile(r"Regulament(?:elor|ele|ului|ul|e)?\s*(?:\(UE\)\s*)?(?:nr\.?\s*)?(\d{1,5})\s*[\/]\s*(\d{1,5})", re.IGNORECASE)
RE_CJUE = re.compile(r"\b([CT])-(\d{1,4})\s*[\/]\s*(\d{2,4})\b")

_ACT_TYPE_MAP = {
    "lege": "lege", "legea": "lege",
    "oug": "oug", "o.u.g.": "oug", "o.u.g": "oug", "ordonanta de urgenta": "oug",
    "og": "og", "o.g.": "og", "o.g": "og", "ordonanta": "og",
    "hg": "hg", "h.g.": "hg", "h.g": "hg", "hotararea guvernului": "hg", "hotararea": "hg",
    "ordinul": "ordin", "ordin": "ordin", "codul": "cod",
}


# Diacriticele si spatiile multiple cad inainte de cautarea in tabel, ca o singura
# intrare sa acopere toate formele scrise ale aceluiasi tip de act. Se scot si sedilele
# vechi, ş si ţ, fiindca documentele mai vechi si unele baze le folosesc inca.
_FARA_DIACRITICE = str.maketrans({
    "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
    "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ş": "S", "Ț": "T", "Ţ": "T",
})


def _norm_act(word: str) -> str:
    plat = re.sub(r"\s+", " ", word.strip().translate(_FARA_DIACRITICE)).lower()
    # "ordonanta de urgenta a guvernului" si "ordonanta de urgenta" sunt acelasi act.
    plat = plat.replace("ordonanta de urgenta a guvernului", "ordonanta de urgenta")
    plat = plat.replace("ordonanta guvernului", "ordonanta")
    return _ACT_TYPE_MAP.get(plat, plat)


def extract_citations(text: str) -> list:
    """Extrage citarile distincte din text. Returneaza lista de dict-uri."""
    found = {}

    def add(kind, number, year, raw, extra=None):
        key = f"{kind}:{number}/{year}"
        if key not in found:
            d = {"kind": kind, "number": str(number), "year": str(year), "raw": raw.strip()[:80]}
            if extra:
                d.update(extra)
            found[key] = d

    for m in RE_CCR.finditer(text):
        add("ccr", m.group(1).replace(".", ""), m.group(2), m.group(0))
    for m in RE_ACT.finditer(text):
        add("act", m.group(2), m.group(3), m.group(0), {"act_type": _norm_act(m.group(1))})
    for m in RE_DIR.finditer(text):
        add("eu_directive", m.group(2), m.group(3), m.group(0))
    for m in RE_REG.finditer(text):
        a, b = m.group(1), m.group(2)
        # Anul e cel care arata ca un an. Dupa 2015 el sta primul, "2016/679", inainte
        # sta al doilea, "1234/2013". Normalizam la (numar, an), ca cheia sa fie stabila.
        if len(a) == 4 and a.startswith(("19", "20")) and not (len(b) == 4 and b.startswith(("19", "20"))):
            numar, an = b, a
        else:
            numar, an = a, b
        add("eu_regulation", numar, an, m.group(0))
    for m in RE_CJUE.finditer(text):
        add("cjue", f"{m.group(1)}-{m.group(2)}", m.group(3), m.group(0))

    return list(found.values())


# ---------------------------------------------------------------- cache

def _load_cache() -> dict:
    try:
        d = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        return {k: v for k, v in d.items() if now - v.get("ts", 0) < _CACHE_TTL}
    except Exception:
        return {}


def _save_cache(cache: dict):
    # Scriere atomica: mai multe sesiuni (Desktop + Code, hook + subagent) pot ajunge
    # aici simultan, iar un write_text direct lasa fisierul trunchiat pentru cine
    # citeste in acelasi moment. Cu fisier temporar + os.replace, cititorii vad ori
    # varianta veche, ori pe cea noua, niciodata una pe jumatate.
    try:
        tmp = _CACHE_FILE.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass


def _load_reference() -> dict:
    try:
        return json.loads(_REF_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------- RO verification (just.ro)

async def _verify_ro(citations: list, budget_s: float) -> dict:
    """Verifica deciziile CCR si actele RO prin legislatie_client (just.ro)."""
    results = {}
    try:
        if str(_LEGAL_SRC) not in sys.path:
            sys.path.insert(0, str(_LEGAL_SRC))
        import legislatie_client as L
    except Exception as e:
        for c in citations:
            results[f"{c['kind']}:{c['number']}/{c['year']}"] = {"verdict": "NEVERIFICAT", "reason": f"client indisponibil: {e}"}
        return results

    deadline = time.monotonic() + budget_s
    for c in citations:
        if time.monotonic() > deadline:
            results[f"{c['kind']}:{c['number']}/{c['year']}"] = {"verdict": "NEVERIFICAT", "reason": "buget de timp depasit"}
            continue
        key = f"{c['kind']}:{c['number']}/{c['year']}"
        try:
            if c["kind"] == "ccr":
                r = await L.search_ccr(int(c["number"]), int(c["year"]))
                if r.get("found"):
                    results[key] = {"verdict": "CONFIRMAT", "status": "gasit", "url": r.get("url", ""), "title": r.get("title", "")[:90]}
                else:
                    results[key] = {"verdict": "NEGASIT", "reason": "decizie CCR negasita pe just.ro"}
            elif c["kind"] == "act":
                r = await L.search_legislation(c.get("act_type", "lege"), int(c["number"]), int(c["year"]))
                if r.get("found"):
                    results[key] = {"verdict": "CONFIRMAT", "status": r.get("status", "in_vigoare"), "url": r.get("url", ""), "title": r.get("title", "")[:90]}
                else:
                    results[key] = {"verdict": "NEGASIT", "reason": "act negasit pe just.ro"}
            else:
                results[key] = {"verdict": "SKIP"}
        except Exception as e:
            results[key] = {"verdict": "NEVERIFICAT", "reason": f"{type(e).__name__}"}
    return results


def _verify_eu(citations: list, ref: dict) -> dict:
    """Verifica actele UE contra listei de acte abrogate cunoscute (reference_names.json)."""
    results = {}
    abrogated = ref.get("eu_abrogated", {})  # {"2009/73/CE": {"replaced_by": "...", "note": "..."}}
    for c in citations:
        if c["kind"] not in ("eu_directive", "eu_regulation", "cjue"):
            continue
        key = f"{c['kind']}:{c['number']}/{c['year']}"
        token = f"{c['number']}/{c['year']}"
        hit = None
        for ab_key, ab_val in abrogated.items():
            if token in ab_key:
                hit = ab_val
                break
        if hit:
            results[key] = {"verdict": "ABROGAT", "reason": hit.get("note", "act UE abrogat"), "replaced_by": hit.get("replaced_by", "")}
        else:
            results[key] = {"verdict": "NEVERIFICAT", "reason": "act UE neverificat (foloseste eurlex check_in_force)"}
    return results


def verify_text(text: str, budget_s: float = 16.0, cap: int = 25, network: bool = True) -> dict:
    """Punct unic de intrare. Extrage si verifica citarile. Returneaza raport sumar.

    network=False: mod LOCAL rapid (fara apeluri la just.ro). Foloseste doar
    reference_names.json si cache-ul. Pentru hook-uri pe fiecare scriere, ca sa nu
    incetineasca Cowork-ul; verificarea de retea ramane la quality-gate / on-demand.
    network=True: verificare completa prin just.ro (CLI, quality-gate, subagent).

    Niciodata nu arunca exceptie (fail-open).
    """
    out = {"citations": [], "problems": [], "checked": 0, "total": 0, "mode": "network" if network else "local"}
    try:
        cits = extract_citations(text)
    except Exception:
        return out
    out["total"] = len(cits)
    if not cits:
        return out

    cits = cits[:cap]
    out["checked"] = len(cits)
    ref = _load_reference()
    cache = _load_cache()

    # split cached vs to-check
    to_check_ro = []
    results = {}
    for c in cits:
        key = f"{c['kind']}:{c['number']}/{c['year']}"
        if key in cache:
            results[key] = cache[key]["res"]
        elif c["kind"] in ("ccr", "act"):
            to_check_ro.append(c)

    # RO verification (async, budgeted) — DOAR in mod network.
    if to_check_ro and network:
        try:
            ro_res = asyncio.run(_verify_ro(to_check_ro, budget_s))
            results.update(ro_res)
            now = time.time()
            for k, v in ro_res.items():
                if v.get("verdict") in ("CONFIRMAT", "NEGASIT", "ABROGAT"):
                    cache[k] = {"ts": now, "res": v}
            _save_cache(cache)
        except Exception:
            pass

    # EU verification (static reference)
    results.update(_verify_eu([c for c in cits if c["kind"].startswith("eu") or c["kind"] == "cjue"], ref))

    # Denumirile si numerele de acte se caută pe text cu spatiile normalizate. Intr-un
    # document real, "Ministerul Finantelor Publice" cade adesea peste sfarsitul de rand,
    # iar potrivirea pe subsir simplu o rata tocmai in livrabile, nu in teste.
    text_plat = re.sub(r"\s+", " ", text).lower()

    outdated = ref.get("outdated_names", {})  # {"Ministerul Finantelor Publice": "Ministerul Finantelor (din 2021)"}
    for old, new in outdated.items():
        if re.sub(r"\s+", " ", old).lower() in text_plat:
            out["problems"].append(f"DENUMIRE DEPASITA: '{old}' -> foloseste '{new}'")
    # wrong transpositions — context-gated ca sa NU dea fals-pozitiv pe un numar de lege
    # real folosit in alt context. Semnalam doar daca documentul discuta efectiv tema NIS.
    nis_context = any(k in text_plat for k in (
        "nis", "securitate cibernetic", "securitatea retelelor", "retele si sisteme informatic",
        "directiva nis", "operator esential", "operator important"))
    if nis_context:
        for wrong, right in ref.get("wrong_transpositions", {}).items():
            if re.sub(r"\s+", " ", wrong).lower() in text_plat:
                out["problems"].append(f"POSIBILA TRANSPUNERE GRESITA (context NIS): '{wrong}' -> verifica daca actul corect e '{right}'")

    for c in cits:
        key = f"{c['kind']}:{c['number']}/{c['year']}"
        res = results.get(key, {"verdict": "SKIP"})
        c["result"] = res
        out["citations"].append(c)
        v = res.get("verdict")
        if v == "NEGASIT":
            out["problems"].append(f"CITARE NEGASITA (posibil inventata): {c['raw']} [{c['kind']}]")
        elif v == "ABROGAT":
            rb = res.get("replaced_by", "")
            out["problems"].append(f"ACT ABROGAT citat ca in vigoare: {c['raw']}" + (f" -> inlocuit de {rb}" if rb else ""))
        elif v == "CONFIRMAT" and res.get("status") in ("abrogat", "modificat"):
            out["problems"].append(f"ACT {res['status'].upper()}: {c['raw']} (verifica daca forma citata e cea aplicabila)")

    return out


def _strip(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


async def _fetch_decision_text(kind: str, number: int, year: int) -> str:
    if str(_LEGAL_SRC) not in sys.path:
        sys.path.insert(0, str(_LEGAL_SRC))
    import legislatie_client as L
    if kind == "ccr":
        r = await L.fetch_ccr_text(number, year)
        return r.get("text", "") or ""
    # lege/act
    leg = await L.search_legislation("lege", number, year)
    if not leg.get("found"):
        return ""
    import re as _re
    m = _re.search(r"/(\d+)", leg["url"])
    if not m:
        return ""
    text, _u = await L.fetch_printable(m.group(1))
    return text or ""


def verify_attribution(quote: str, kind: str, number, year, threshold: float = 0.82) -> dict:
    """Confirma ca un citat verbatim apare efectiv in textul deciziei/actului atribuit.

    Prinde atribuirile gresite de considerent (citarea exista, dar pasajul e al altei
    decizii). Returneaza verdict CONFIRMAT_IN_TEXT / NEGASIT_IN_TEXT / NEVERIFICAT.
    """
    import difflib
    out = {"quote": quote[:120], "kind": kind, "ref": f"{number}/{year}", "verdict": "NEVERIFICAT"}
    q = _strip(quote)
    if len(q.split()) < 4:
        out["reason"] = "citat prea scurt pentru verificare"
        return out
    try:
        text = asyncio.run(_fetch_decision_text(kind, int(number), int(year)))
    except Exception as e:
        out["reason"] = f"text indisponibil: {type(e).__name__}"
        return out
    if not text:
        out["verdict"] = "NEVERIFICAT"
        out["reason"] = "textul deciziei/actului nu a putut fi obtinut"
        return out

    body = _strip(text)
    qwords = q.split()
    # fereastra reprezentativa din citat (max 14 cuvinte din mijloc)
    window = " ".join(qwords[: min(14, len(qwords))])
    if window in body:
        out["verdict"] = "CONFIRMAT_IN_TEXT"
        out["match"] = "exact"
        return out
    # potrivire fuzzy: cauta cea mai buna fereastra din corp
    bwords = body.split()
    n = len(window.split())
    best = 0.0
    sm = difflib.SequenceMatcher()
    sm.set_seq2(window)
    step = max(1, n // 3)
    for i in range(0, max(1, len(bwords) - n + 1), step):
        cand = " ".join(bwords[i:i + n])
        sm.set_seq1(cand)
        r = sm.ratio()
        if r > best:
            best = r
            if best >= 0.97:
                break
    out["best_ratio"] = round(best, 3)
    if best >= threshold:
        out["verdict"] = "CONFIRMAT_IN_TEXT"
        out["match"] = "fuzzy"
    else:
        out["verdict"] = "NEGASIT_IN_TEXT"
        out["reason"] = "pasajul nu apare in textul atribuit (posibil atribuire gresita)"
    return out


if __name__ == "__main__":
    # CLI:
    #   python citation_core.py <fisier.txt>                  -> verifica citarile
    #   python citation_core.py --attr "<citat>" ccr 17 2015  -> verifica atribuirea
    if len(sys.argv) > 1 and sys.argv[1] == "--attr":
        quote, kind, number, year = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        print(json.dumps(verify_attribution(quote, kind, number, year), ensure_ascii=False, indent=1))
    else:
        path = sys.argv[1] if len(sys.argv) > 1 else None
        txt = Path(path).read_text(encoding="utf-8", errors="ignore") if path else sys.stdin.read()
        print(json.dumps(verify_text(txt), ensure_ascii=False, indent=1))
