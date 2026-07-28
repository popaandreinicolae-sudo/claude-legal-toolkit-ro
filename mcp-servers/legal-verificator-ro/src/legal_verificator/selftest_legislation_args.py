"""Selftest pentru contractul tool-urilor de legislatie. Ruleaza offline.

    python selftest_legislation_args.py

Pazeste reparatia din 28 iulie 2026: `search_legislation` cerea `act_type` ca
proprietate obligatorie, iar apelul fara el era respins de validarea de schema cu
"MCP error -32602: Input validation error", inainte sa ajunga la server. Stratul
de recuperare din call_tool, scris tocmai pentru apeluri incomplete, nu apuca sa
ruleze niciodata. Daca cineva pune la loc `required` pe tool-urile de legislatie
sau scoate parsarea citarii libere, testul asta pica.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonschema  # noqa: E402
import server  # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    if not cond:
        FAILS.append(label)
    print(f"  [{'OK  ' if cond else 'FAIL'}] {label}{(' -> ' + detail) if detail and not cond else ''}")


# ── 1. Schemele ──────────────────────────────────────────────────────────────
tools = asyncio.run(server.list_tools())
schemas = {t.name: t.inputSchema for t in tools}
print(f"\n1. Scheme ({len(tools)} tool-uri)")
for t in tools:
    try:
        jsonschema.Draft202012Validator.check_schema(t.inputSchema)
        ok = True
    except Exception as e:  # noqa: BLE001
        ok, _ = False, print(f"      {e}")
    check(f"schema valida: {t.name}", ok)

for tool_name in sorted(server._LEGISLATION_TOOLS):
    schema = schemas[tool_name]
    check(f"{tool_name} nu mai impune campuri obligatorii", not schema.get("required"),
          str(schema.get("required")))
    check(f"{tool_name} declara 'query'", "query" in schema["properties"])
    try:
        jsonschema.validate({"number": 58, "year": 2023}, schema)
        ok = True
    except jsonschema.ValidationError:
        ok = False
    check(f"{tool_name} accepta apelul fara act_type", ok)

check("search_ccr_decision ramane strict",
      schemas["search_ccr_decision"].get("required") == ["number", "year"])


# ── 1b. Ordinea surselor ─────────────────────────────────────────────────────
# Pozitia in lista cantareste la alegerea tool-ului, deci sintact.ro trebuie sa
# ajunga la model inaintea rezervei Indaco, altfel descrierea zice una si asezarea
# alta. Regresia asta a trimis o cautare pe lege6 desi sintact era sursa ceruta.
print("\n1b. Ordinea surselor")
order = [t.name for t in tools]
check("toate tool-urile sunt asezate explicit",
      set(order) == set(server._TOOL_ORDER),
      f"lipsesc din _TOOL_ORDER: {sorted(set(order) - set(server._TOOL_ORDER))}")
first_sintact = min((i for i, n in enumerate(order) if n.startswith("sintact")), default=99)
first_indaco = min((i for i, n in enumerate(order) if n.startswith(("lege5", "lege6"))), default=-1)
check("sintact.ro ajunge inaintea rezervei Indaco", first_sintact < first_indaco,
      f"sintact pe {first_sintact}, Indaco pe {first_indaco}")
for name in ("lege6_search", "lege5_search"):
    desc = next(t.description for t in tools if t.name == name)
    check(f"{name} se anunta ca rezerva", "REZERV" in desc.upper() or "LEGACY" in desc.upper(),
          desc[:60])
    check(f"{name} nu se mai anunta ca prioritar", "PRIORITAR" not in desc.upper(), desc[:60])


# ── 2. Parsarea citarii in text liber ────────────────────────────────────────
print("\n2. Parsare citare")
CASES = [
    ("Legea 58/2023", {"act_type": "lege", "number": 58, "year": 2023}),
    ("Legea nr. 58/2023", {"act_type": "lege", "number": 58, "year": 2023}),
    ("OUG 155/2024", {"act_type": "oug", "number": 155, "year": 2024}),
    ("O.U.G. nr. 155/2024", {"act_type": "oug", "number": 155, "year": 2024}),
    ("Ordonanța de urgență a Guvernului nr. 155/2024", {"act_type": "oug", "number": 155, "year": 2024}),
    ("Ordonanța Guvernului nr. 2/2001", {"act_type": "og", "number": 2, "year": 2001}),
    ("H.G. nr. 123/2020", {"act_type": "hg", "number": 123, "year": 2020}),
    ("Hotărârea Guvernului nr. 123/2020", {"act_type": "hg", "number": 123, "year": 2020}),
    ("Ordinul nr. 1234/2019", {"act_type": "ordin", "number": 1234, "year": 2019}),
    ("Constituția României", {"act_type": "constitutie"}),
    ("Codul muncii", {"act_type": "cod"}),
    # Numarul apartine ordonantei, nu legii de aprobare.
    ("legea de aprobare a OUG 155/2024", {"act_type": "oug", "number": 155, "year": 2024}),
    ("art. 3 alin. (2) lit. b) din Legea 58/2023",
     {"act_type": "lege", "number": 58, "year": 2023, "article": 3, "alineat": 2, "litera": "b"}),
    ("art. 53 din Constituție", {"act_type": "constitutie", "article": 53}),
    ("articolul 26 din Constituția României", {"act_type": "constitutie", "article": 26}),
]
for text, expected in CASES:
    got = server._parse_citation(text)
    check(f"{text!r}", {k: got.get(k) for k in expected} == expected, f"a iesit {got}")

print("\n   Canonizare tip act")
for raw, want in [("Legea", "lege"), ("lege", "lege"), ("O.U.G.", "oug"), ("oug", "oug"),
                  ("OG", "og"), ("H.G.", "hg"), ("hg", "hg"), ("Ordinul", "ordin"),
                  ("Codul", "cod"), ("Constituția", "constitutie"), ("ordonanță de urgență", "oug")]:
    got = server._canon_act_type(raw)
    check(f"{raw!r} -> {want!r}", got == want, f"a iesit {got!r}")


# ── 3. Normalizarea argumentelor ─────────────────────────────────────────────
print("\n3. Normalizare argumente")
n = server._normalize_args({"query": "Legea 58/2023"}, "search_legislation")
check("citarea libera completeaza act_type/number/year",
      (n.get("act_type"), n.get("number"), n.get("year")) == ("lege", 58, 2023), str(n))

n = server._normalize_args({"act_number": "334", "act_year": "2022", "type": "Legea"}, "search_legislation")
check("aliasuri act_number/act_year/type",
      (n.get("act_type"), n.get("number"), n.get("year")) == ("lege", 334, 2022), str(n))

n = server._normalize_args({"act_type": "lege", "number": 58, "year": 2023, "query": "Legea 999/1999"},
                           "search_legislation")
check("campurile explicite bat textul liber", (n.get("number"), n.get("year")) == (58, 2023), str(n))

n = server._normalize_args({"number": 58, "year": 2023}, "search_ccr_decision")
check("tool-urile non-legislatie nu sunt atinse", "act_type" not in n, str(n))


# ── 4. Rutarea in call_tool, cu reteaua inlocuita ────────────────────────────
print("\n4. Rutare call_tool (offline)")
calls = []


async def fake_search_legislation(act_type, number, year):
    calls.append(("search_legislation", act_type, number, year))
    return {"found": True, "title": f"stub {act_type} {number}/{year}", "status": "in_vigoare"}


async def fake_fetch_article(act_type, number, year, article, alineat=None, litera=None):
    calls.append(("fetch_article", act_type, number, year, article, alineat, litera))
    return {"text": "stub", "article": article}


async def fake_search_document(query, **kw):
    calls.append(("search_document", query, kw))
    return [{"title": f"rezultat pentru {query or kw}", "url": "https://legislatie.just.ro/x", "doc_id": "1"},
            {"title": "Vizualizeaza", "url": "https://legislatie.just.ro/x", "doc_id": "1"}]


server.search_legislation = fake_search_legislation
server.fetch_article = fake_fetch_article
server.search_document = fake_search_document


def run(name, args):
    return json.loads(asyncio.run(server.call_tool(name, args))[0].text)


r = run("search_legislation", {"query": "Legea 58/2023"})
check("search_legislation(query='Legea 58/2023') ajunge la client",
      r.get("found") and calls[-1] == ("search_legislation", "lege", 58, 2023), json.dumps(r, ensure_ascii=False))

r = run("search_legislation", {"number": 58, "year": 2023})
check("fara act_type intoarce candidati, nu eroare de protocol",
      "candidates" in r and r.get("missing") == ["act_type"], json.dumps(r, ensure_ascii=False))
check("candidatii sunt cautati pe numar si an, nu pe text",
      calls[-1][0] == "search_document" and calls[-1][2].get("doc_number") == "58", str(calls[-1]))
check("randurile de navigare nu ajung in candidati",
      all(c["title"] != "Vizualizeaza" for c in r["candidates"]), json.dumps(r["candidates"]))

r = run("search_legislation", {"act_type": "constitutie"})
check("Constitutia nu mai cere number/year", r.get("found") and calls[-1][1] == "constitutie",
      json.dumps(r, ensure_ascii=False))

r = run("fetch_article_text", {"query": "art. 3 alin. (2) lit. b) din Legea 58/2023"})
check("fetch_article_text din citare libera",
      calls[-1] == ("fetch_article", "lege", 58, 2023, 3, 2, "b"), json.dumps(r, ensure_ascii=False))

r = run("fetch_article_text", {"act_type": "lege", "number": 58, "year": 2023})
check("fetch_article_text fara articol raporteaza ce lipseste", r.get("missing") == ["article"],
      json.dumps(r, ensure_ascii=False))

r = run("search_legislation", {})
check("apelul gol nu arunca exceptie", "candidates" in r, json.dumps(r, ensure_ascii=False))

print("\n" + "=" * 62)
if FAILS:
    print(f"ESUAT: {len(FAILS)} verificari")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("TOATE VERIFICARILE AU TRECUT")
