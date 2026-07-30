#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_track_changes.py

Scrie modificari urmarite (track changes) native Word direct in XML-ul unui .docx,
fara sa deschida Word si fara control de desktop.

Rezultatul contine elemente <w:ins> si <w:del> reale, deci Word arata reviziile
in panoul Review si permite Accept / Reject individual.

Comenzi
-------
  list    Listeaza paragrafele numerotate (id-uri stabile), pentru a construi editarile.
  apply   Aplica modificarile si scrie documentul cu track changes.
  verify  Reciteste un .docx, raporteaza reviziile gasite si semnaleaza marcajele
          mai late decat modificarea, adica taind cuvinte care nu s-au schimbat.

Exemple
-------
  python docx_track_changes.py list --input cerere.docx
  python docx_track_changes.py list --input cerere.docx --parts document,footnotes

  python docx_track_changes.py apply --input cerere.docx --output cerere_revizuit.docx \
      --edits edits.json --author "AMZ Law Office"

  python docx_track_changes.py apply --input cerere.docx --output cerere_revizuit.docx \
      --revised cerere_nou.docx --author "AMZ Law Office"

  python docx_track_changes.py verify --input cerere_revizuit.docx
  python docx_track_changes.py verify --input cerere_revizuit.docx --strict

Format edits.json
-----------------
{
  "author": "AMZ Law Office",
  "edits": [
    {"op": "replace",          "find": "text vechi", "replace": "text nou"},
    {"op": "replace",          "find": "abc", "replace": "abd", "all": true},
    {"op": "replace",          "find": "abc", "replace": "abd", "part": "footnotes"},
    {"op": "set_paragraph",    "id": "doc:12", "text": "continutul integral nou"},
    {"op": "insert_after",     "id": "doc:12", "text": "paragraf nou"},
    {"op": "insert_before",    "id": "doc:0",  "text": "paragraf nou la inceput"},
    {"op": "delete_paragraph", "id": "doc:12"}
  ]
}

Orice editare care nu se potriveste opreste executia cu eroare. Tool-ul nu ghiceste.
"""

from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from cale_libera import alege, adauga_optiune
import argparse
import datetime as _dt
import json
import re
import shutil
import sys
import unicodedata
import zipfile
from copy import deepcopy
from difflib import SequenceMatcher

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.stderr.write("Lipseste lxml. Instaleaza: pip install lxml\n")
    raise

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def w(tag: str) -> str:
    return "{%s}%s" % (W_NS, tag)


XML_SPACE = "{%s}space" % XML_NS

PARTS = {
    "document": "word/document.xml",
    "footnotes": "word/footnotes.xml",
    "endnotes": "word/endnotes.xml",
}
PART_PREFIX = {"document": "doc", "footnotes": "fn", "endnotes": "en"}
PREFIX_PART = {v: k for k, v in PART_PREFIX.items()}

# Containere pe care le desfacem si le reconstruim in jurul run-urilor.
FLATTEN_TAGS = {w("hyperlink"), w("smartTag"), w("ins")}
# Continut deja sters intr-o revizie anterioara: text invizibil, il pastram intact.
FROZEN_TAGS = {w("del"), w("moveFrom")}

TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)


# --------------------------------------------------------------------------
# Atomi: descompunerea unui paragraf in unitati adresabile
# --------------------------------------------------------------------------

class Atom:
    """O unitate minima dintr-un paragraf.

    kind == 'text'   un singur caracter, cu proprietatile run-ului sursa
    kind == 'inline' element din interiorul unui run (nota de subsol, tab, br, imagine)
    kind == 'block'  element de nivel paragraf (bookmark, revizie veche, sdt)
    """

    __slots__ = ("kind", "ch", "el", "rpr", "ctx")

    def __init__(self, kind, ch=None, el=None, rpr=None, ctx=None):
        self.kind = kind
        self.ch = ch
        self.el = el
        self.rpr = rpr
        self.ctx = ctx


class Item:
    """Unitate de iesire, cu modul de revizie atasat."""

    __slots__ = ("kind", "text", "el", "rpr", "ctx", "mode")

    def __init__(self, kind, text=None, el=None, rpr=None, ctx=None, mode="keep"):
        self.kind = kind
        self.text = text
        self.el = el
        self.rpr = rpr
        self.ctx = ctx
        self.mode = mode


def decompose(paragraph) -> list:
    """Sparge un <w:p> in atomi, pastrand tot ce nu e text simplu."""
    atoms: list[Atom] = []

    def walk(node, ctx):
        for child in node:
            tag = child.tag
            if tag == w("pPr"):
                continue
            if tag == w("r"):
                rpr_el = child.find(w("rPr"))
                rpr = deepcopy(rpr_el) if rpr_el is not None else None
                for sub in child:
                    if sub.tag == w("rPr"):
                        continue
                    if sub.tag == w("t"):
                        for ch in (sub.text or ""):
                            atoms.append(Atom("text", ch=ch, rpr=rpr, ctx=ctx))
                    else:
                        atoms.append(Atom("inline", el=deepcopy(sub), rpr=rpr, ctx=ctx))
            elif tag in FLATTEN_TAGS:
                shell = etree.Element(tag, nsmap=child.nsmap)
                for k, v in child.attrib.items():
                    shell.set(k, v)
                walk(child, ctx if ctx is not None else shell)
            else:
                atoms.append(Atom("block", el=deepcopy(child)))

    walk(paragraph, None)
    return atoms


def atoms_text(atoms: list) -> str:
    return "".join(a.ch for a in atoms if a.kind == "text")


def paragraph_text(paragraph) -> str:
    return atoms_text(decompose(paragraph))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", fold_echivalente(s)).strip()


# Perechi de caractere care arata identic pe ecran si se deosebesc doar prin
# codificare. Romana are doua scrieri pentru aceleasi litere, virgula dedesubt
# (ș U+0219, ț U+021B), forma corecta de azi, si sedila (ş U+015F, ţ U+0163),
# forma veche ramasa in bazele de legislatie si jurisprudenta. Un document care
# citeaza din ele amesteca ambele scrieri.
#
# Fara plierea asta, orice conversie de codificare produce revizii pe cuvinte
# care se citesc la fel: "şi" taiat, "și" adaugat. Masurat pe o exceptie de
# neconstitutionalitate, 240 din 1270 de marcaje, aproape jumatate din ce avea
# avocatul de citit, fara nicio informatie in ele. Comparatia le trateaza ca pe
# acelasi cuvant, deci nu se mai naste nicio revizie, iar textul livrat pastreaza
# scrierea din original, inclusiv in citate.
_ECHIVALENTE = str.maketrans({
    "ş": "ș", "Ş": "Ș",          # sedila -> virgula dedesubt
    "ţ": "ț", "Ţ": "Ț",
    " ": " ", " ": " ",  # spatii insecabile
    "‑": "-",                 # cratima insecabila
})


def fold_echivalente(s: str) -> str:
    """Pliaza scrierile care arata la fel. Se foloseste NUMAI la comparare,
    niciodata la scrierea documentului: originalul isi pastreaza grafia."""
    if not s:
        return s
    s = unicodedata.normalize("NFC", s)
    return s.translate(_ECHIVALENTE).replace("­", "")


# Principiul: se compara ce vede cititorul, nu ce e stocat in fisier. Doua locuri
# in care Word afiseaza altceva decat scrie in text, si unde o varianta revizuita
# venita din afara .docx-ului aduce forma afisata inapoi ca text:
#
#   1. numerotarea automata. Paragraful cu w:numPr afiseaza "IV." fara ca "IV."
#      sa existe in text. O varianta care il scrie ca text descrie acelasi lucru.
#   2. majusculele din stil, w:caps. Titlul scris "Incalcarea articolului" se
#      afiseaza "INCALCAREA ARTICOLULUI". O varianta scrisa cu majuscule descrie
#      acelasi titlu.
#
# In ambele cazuri cititorul vede acelasi lucru, deci nu se naste nicio revizie,
# iar in document ramane textul original.
_MARCAJ_LISTA = re.compile(
    r"^[\s ]*(?:"
    r"\[\d{1,4}\]"
    r"|\(?[ivxlcdm]{1,7}\)"
    r"|\(?[IVXLCDM]{1,7}[.)]"
    r"|\d{1,3}(?:\.\d{1,3})*[.)]"
    r"|\(?[a-zA-Z][.)]"
    r"|[•·▪●–—-]"
    r")[\s ]+")


def scoate_marcaj_lista(text: str) -> str:
    return _MARCAJ_LISTA.sub("", text or "", count=1)


def _pornit(el) -> bool:
    """Un fanion OOXML e pornit si cand ii lipseste atributul w:val."""
    if el is None:
        return False
    v = el.get(w("val"))
    return v is None or v not in ("0", "false", "off")


def stiluri_cu_majuscule(path) -> set:
    """Id-urile de stil care afiseaza textul cu majuscule, urmarind si basedOn,
    si stilul de caracter legat, acolo unde sta de fapt w:caps."""
    try:
        with zipfile.ZipFile(path) as z:
            if "word/styles.xml" not in z.namelist():
                return set()
            root = etree.parse(z.open("word/styles.xml")).getroot()
    except Exception:
        return set()

    direct, based, linked = {}, {}, {}
    for st in root.findall(w("style")):
        sid = st.get(w("styleId"))
        if not sid:
            continue
        direct[sid] = _pornit(st.find(w("rPr") + "/" + w("caps")))
        b = st.find(w("basedOn"))
        based[sid] = b.get(w("val")) if b is not None else None
        lk = st.find(w("link"))
        linked[sid] = lk.get(w("val")) if lk is not None else None

    caps = set()
    for sid in direct:
        cur, vazute = sid, set()
        while cur and cur not in vazute:
            vazute.add(cur)
            if direct.get(cur) or direct.get(linked.get(cur) or ""):
                caps.add(sid)
                break
            cur = based.get(cur)
    return caps


def afiseaza_majuscule(paragraph, caps_styles: set) -> bool:
    ps = paragraph.find(w("pPr") + "/" + w("pStyle"))
    if ps is not None and ps.get(w("val")) in caps_styles:
        return True
    if _pornit(paragraph.find(w("pPr") + "/" + w("rPr") + "/" + w("caps"))):
        return True
    for r in paragraph.iter(w("r")):
        rpr = r.find(w("rPr"))
        if rpr is None:
            continue
        if _pornit(rpr.find(w("caps"))):
            return True
        rs = rpr.find(w("rStyle"))
        if rs is not None and rs.get(w("val")) in caps_styles:
            return True
    return False


def are_numerotare(paragraph) -> bool:
    return paragraph.find(w("pPr") + "/" + w("numPr")) is not None


def fold_vizual(s: str, ignora_capitalizarea: bool = False) -> str:
    s = fold_echivalente(s)
    return s.upper() if ignora_capitalizarea else s


# --------------------------------------------------------------------------
# Reconstructia paragrafului din itemi
# --------------------------------------------------------------------------

class RevisionIds:
    def __init__(self, start=1000):
        self.n = start

    def next(self) -> str:
        self.n += 1
        return str(self.n)


def _rpr_key(rpr) -> str:
    if rpr is None:
        return ""
    return etree.tostring(rpr, encoding="unicode")


def _make_run(text, rpr, mode):
    r = etree.Element(w("r"))
    if rpr is not None:
        r.append(deepcopy(rpr))
    tag = w("delText") if mode == "del" else w("t")
    t = etree.SubElement(r, tag)
    t.set(XML_SPACE, "preserve")
    t.text = text
    return r


def _make_inline_run(el, rpr):
    r = etree.Element(w("r"))
    if rpr is not None:
        r.append(deepcopy(rpr))
    r.append(deepcopy(el))
    return r


def _wrap_revision(tag, nodes, author, date, ids):
    holder = etree.Element(w(tag))
    holder.set(w("id"), ids.next())
    holder.set(w("author"), author)
    holder.set(w("date"), date)
    for n in nodes:
        holder.append(n)
    return holder


def _build_runs(group: list) -> list:
    """Transforma itemi consecutivi cu acelasi mod in run-uri, unind textul compatibil."""
    nodes = []
    buf_text = []
    buf_rpr = None
    buf_key = None
    mode = group[0].mode if group else "keep"

    def flush():
        nonlocal buf_text, buf_rpr, buf_key
        if buf_text:
            nodes.append(_make_run("".join(buf_text), buf_rpr, mode))
            buf_text = []
            buf_rpr = None
            buf_key = None

    for it in group:
        if it.kind == "text":
            key = _rpr_key(it.rpr)
            if buf_text and key != buf_key:
                flush()
            if not buf_text:
                buf_rpr = it.rpr
                buf_key = key
            buf_text.append(it.text)
        else:
            flush()
            nodes.append(_make_inline_run(it.el, it.rpr))
    flush()
    return nodes


def rebuild_paragraph(paragraph, items, author, date, ids, mark=None):
    """Rescrie continutul lui <w:p> din itemi. mark in {None, 'ins', 'del'}."""
    ppr = paragraph.find(w("pPr"))
    for child in list(paragraph):
        if child is ppr:
            continue
        paragraph.remove(child)

    out = []
    i = 0
    n = len(items)
    while i < n:
        it = items[i]
        if it.kind == "block":
            out.append(deepcopy(it.el))
            i += 1
            continue

        ctx = it.ctx
        j = i
        while j < n and items[j].kind != "block" and items[j].ctx is ctx:
            j += 1
        chunk = items[i:j]
        i = j

        produced = []
        k = 0
        while k < len(chunk):
            m = chunk[k].mode
            g = k
            while g < len(chunk) and chunk[g].mode == m:
                g += 1
            nodes = _build_runs(chunk[k:g])
            if m == "keep":
                produced.extend(nodes)
            else:
                produced.append(_wrap_revision(m, nodes, author, date, ids))
            k = g

        if ctx is not None:
            shell = deepcopy(ctx)
            for child in list(shell):
                shell.remove(child)
            for nd in produced:
                shell.append(nd)
            out.append(shell)
        else:
            out.extend(produced)

    for nd in out:
        paragraph.append(nd)

    if mark in ("ins", "del"):
        if ppr is None:
            ppr = etree.Element(w("pPr"))
            paragraph.insert(0, ppr)
        rpr = ppr.find(w("rPr"))
        if rpr is None:
            rpr = etree.Element(w("rPr"))
            # CT_PPr cere ordinea: elementele pPrBase, apoi rPr, apoi sectPr, apoi pPrChange
            tail = {w("sectPr"), w("pPrChange")}
            pos = len(ppr)
            for idx, child in enumerate(ppr):
                if child.tag in tail:
                    pos = idx
                    break
            ppr.insert(pos, rpr)
        tagged = etree.Element(w(mark))
        tagged.set(w("id"), ids.next())
        tagged.set(w("author"), author)
        tagged.set(w("date"), date)
        rpr.insert(0, tagged)


# --------------------------------------------------------------------------
# Diff la nivel de cuvant in interiorul unui paragraf
# --------------------------------------------------------------------------

def _token_spans(s: str):
    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(s)]


def build_items(atoms: list, new_text: str | None, force_mode: str | None = None,
                ignora_capitalizarea: bool = False) -> list:
    """Produce itemii de iesire pentru un paragraf.

    force_mode == 'del' marcheaza tot paragraful ca sters.
    new_text is None inseamna paragraf neschimbat.
    """
    items: list[Item] = []
    ptr = 0
    total = len(atoms)

    def mk(a: Atom, mode: str) -> Item:
        if a.kind == "text":
            return Item("text", text=a.ch, rpr=a.rpr, ctx=a.ctx, mode=mode)
        if a.kind == "inline":
            return Item("inline", el=a.el, rpr=a.rpr, ctx=a.ctx, mode=mode)
        return Item("block", el=a.el, mode="keep")

    def last_rpr():
        for it in reversed(items):
            if it.kind == "text":
                return it.rpr, it.ctx
        for k in range(ptr, total):
            if atoms[k].kind == "text":
                return atoms[k].rpr, atoms[k].ctx
        return None, None

    def take(count: int, mode: str):
        nonlocal ptr
        if count <= 0:
            return
        while ptr < total and atoms[ptr].kind != "text":
            items.append(mk(atoms[ptr], "keep"))
            ptr += 1
        taken = 0
        while ptr < total and taken < count:
            a = atoms[ptr]
            items.append(mk(a, mode if a.kind != "block" else "keep"))
            if a.kind == "text":
                taken += 1
            ptr += 1

    def insert(text: str):
        if not text:
            return
        rpr, ctx = last_rpr()
        items.append(Item("text", text=text, rpr=rpr, ctx=ctx, mode="ins"))

    old = atoms_text(atoms)

    if force_mode == "del":
        take(len(old), "del")
    elif new_text is None or (fold_vizual(new_text, ignora_capitalizarea) ==
                              fold_vizual(old, ignora_capitalizarea)):
        # Textul se citeste la fel, chiar daca difera codificarea unei litere sau
        # capitalizarea intr-un paragraf pe care stilul il afiseaza cu majuscule.
        # Se pastreaza originalul, fara nicio revizie.
        take(len(old), "keep")
    else:
        a_tok = _token_spans(old)
        b_tok = _token_spans(new_text)
        sm = SequenceMatcher(None,
                             [fold_vizual(t[0], ignora_capitalizarea) for t in a_tok],
                             [fold_vizual(t[0], ignora_capitalizarea) for t in b_tok],
                             autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            a_len = (a_tok[i2 - 1][2] - a_tok[i1][1]) if i2 > i1 else 0
            b_txt = new_text[b_tok[j1][1]:b_tok[j2 - 1][2]] if j2 > j1 else ""
            if op == "equal":
                take(a_len, "keep")
            elif op == "delete":
                take(a_len, "del")
            elif op == "insert":
                insert(b_txt)
            else:
                take(a_len, "del")
                insert(b_txt)

    while ptr < total:
        items.append(mk(atoms[ptr], "keep"))
        ptr += 1

    return items


# --------------------------------------------------------------------------
# Latimea redlineului: marcajul acopera cuvantul schimbat, nu fraza din jur
# --------------------------------------------------------------------------
#
# Regula ceruta pe 29 iulie 2026: cand dintr-o paranteza e gresit un singur
# cuvant, redlineul marcheaza acel cuvant, nu toata paranteza. Un "(fiind
# nelegal pentru aceste aspect)" taiat intreg si rescris intreg pune avocatul
# sa citeasca de doua ori acelasi text ca sa gaseasca litera schimbata.
#
# `build_items` respecta regula din constructie, fiindca diff-ul lucreaza pe
# token-uri, deci un `find`/`replace` pe fraza intreaga sau un `set_paragraph`
# pe tot paragraful ies tot marcate la nivel de cuvant. Verificarea de mai jos
# pazeste celalalt traseu, redlineul scris de mana in XML despachetat, unde
# inlocuirea unui `<w:r>` intreg lateste marcajul peste cuvinte nemodificate.

def _tokenuri(s: str):
    """Token-urile brute si perechea lor pliata, pentru comparare."""
    bruti = TOKEN_RE.findall(s or "")
    return bruti, [fold_echivalente(t) for t in bruti]


def _margini_comune(sters: str, adaugat: str):
    """Cat se suprapune la capete o pereche stergere/inserare.

    Intoarce (prefix, sufix, miez_sters, miez_adaugat), toate ca text brut.
    """
    a_brut, a_fold = _tokenuri(sters)
    b_brut, b_fold = _tokenuri(adaugat)
    n = min(len(a_fold), len(b_fold))

    pre = 0
    while pre < n and a_fold[pre] == b_fold[pre]:
        pre += 1
    post = 0
    while post < n - pre and a_fold[len(a_fold) - 1 - post] == b_fold[len(b_fold) - 1 - post]:
        post += 1

    end_a = len(a_brut) - post
    end_b = len(b_brut) - post
    return ("".join(a_brut[:pre]),
            "".join(a_brut[end_a:]),
            "".join(a_brut[pre:end_a]),
            "".join(b_brut[pre:end_b]))


def _text_revizie(el) -> str:
    return "".join((t.text or "") for t in el.iter(w("t"), w("delText")))


def _perechi_lipite(paragraph):
    """Perechile <w:del>/<w:ins> asezate una langa alta in acelasi parinte."""
    grupe = {}
    for el in paragraph.iter(w("ins"), w("del")):
        par = el.getparent()
        if par is None or par.tag in (w("rPr"), w("ins"), w("del")):
            continue
        grupe.setdefault(id(par), (par, []))[1].append(el)

    perechi = []
    for par, els in grupe.values():
        kids = list(par)
        for a, b in zip(els, els[1:]):
            if a.tag == b.tag:
                continue
            ia, ib = kids.index(a), kids.index(b)
            if ib <= ia:
                continue
            # intre ele nu are voie sa stea text pastrat, doar spatii
            if any(_text_revizie(k).strip() for k in kids[ia + 1:ib]):
                continue
            perechi.append((a, b) if a.tag == w("del") else (b, a))
    return perechi


def revizii_prea_largi(parts):
    """Reviziile care taie si rescriu cuvinte nemodificate. Raport, nu blocaj."""
    raport = []
    for name, part in parts.items():
        for idx, p in enumerate(part.paragraphs):
            for d, i in _perechi_lipite(p):
                sters, adaugat = _text_revizie(d), _text_revizie(i)
                if not sters or not adaugat:
                    continue
                pre, post, miez_s, miez_a = _margini_comune(sters, adaugat)
                comun = (pre + post).strip()
                if not re.search(r"\w", comun, re.UNICODE):
                    continue
                raport.append({
                    "part": name,
                    "id": part.label(idx),
                    "sters": sters,
                    "adaugat": adaugat,
                    "cuvinte_nemodificate_in_marcaj": comun,
                    "ar_fi_fost_destul": {"sters": miez_s, "adaugat": miez_a},
                })
    return raport


# --------------------------------------------------------------------------
# Alinierea paragrafelor
# --------------------------------------------------------------------------

def _pair_block(a_texts, b_texts, threshold=0.35):
    """Aliniaza doua blocuri de paragrafe schimbate, prin similaritate.

    Intoarce lista de (i sau None, j sau None), in ordine.
    """
    n, m = len(a_texts), len(b_texts)
    if n == 0:
        return [(None, j) for j in range(m)]
    if m == 0:
        return [(i, None) for i in range(n)]
    if n * m > 4000:
        pairs = []
        for k in range(max(n, m)):
            pairs.append((k if k < n else None, k if k < m else None))
        return pairs

    a_fold = [_cheie_aliniere(t) for t in a_texts]
    b_fold = [_cheie_aliniere(t) for t in b_texts]
    ratio = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            r = SequenceMatcher(None, a_fold[i], b_fold[j], autojunk=False).ratio()
            ratio[i][j] = r if r >= threshold else -1.0

    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    move = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            cand = []
            if ratio[i][j] >= 0:
                cand.append((ratio[i][j] + best[i + 1][j + 1], "pair"))
            cand.append((best[i + 1][j], "skip_a"))
            cand.append((best[i][j + 1], "skip_b"))
            score, mv = max(cand, key=lambda c: c[0])
            best[i][j] = score
            move[i][j] = mv

    pairs = []
    i = j = 0
    while i < n and j < m:
        mv = move[i][j]
        if mv == "pair":
            pairs.append((i, j))
            i += 1
            j += 1
        elif mv == "skip_a":
            pairs.append((i, None))
            i += 1
        else:
            pairs.append((None, j))
            j += 1
    while i < n:
        pairs.append((i, None))
        i += 1
    while j < m:
        pairs.append((None, j))
        j += 1
    return pairs


def _cheie_aliniere(s: str) -> str:
    """Cheia dupa care se imperecheaza paragrafele. Capitalizarea si marcajul de
    lista se ignora AICI, fiindca pasul asta doar decide ce paragraf corespunde
    caruia. Un titlu adus inapoi cu majuscule dintr-o retiparire nu mai seamana
    caracter cu caracter cu originalul, deci fara plierea asta nu se mai
    imperecheaza cu el si iese sters intreg si rescris intreg, cu stilul pierdut."""
    return scoate_marcaj_lista(norm(s)).upper()


def align(old_texts, new_texts):
    """Intoarce o lista de operatii (kind, i, j) unde kind in keep/change/delete/insert."""
    sm = SequenceMatcher(None,
                         [_cheie_aliniere(t) for t in old_texts],
                         [_cheie_aliniere(t) for t in new_texts],
                         autojunk=False)
    plan = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                plan.append(("keep", i1 + k, j1 + k))
        elif op == "delete":
            for i in range(i1, i2):
                plan.append(("delete", i, None))
        elif op == "insert":
            for j in range(j1, j2):
                plan.append(("insert", None, j))
        else:
            for pi, pj in _pair_block(old_texts[i1:i2], new_texts[j1:j2]):
                if pi is not None and pj is not None:
                    plan.append(("change", i1 + pi, j1 + pj))
                elif pi is not None:
                    plan.append(("delete", i1 + pi, None))
                else:
                    plan.append(("insert", None, j1 + pj))
    return plan


# --------------------------------------------------------------------------
# Acces la partile documentului
# --------------------------------------------------------------------------

class Part:
    def __init__(self, name, path, tree):
        self.name = name
        self.path = path
        self.tree = tree
        self.root = tree.getroot()
        self.paragraphs = self._collect()
        self.texts = [paragraph_text(p) for p in self.paragraphs]

    def _collect(self):
        if self.name == "document":
            body = self.root.find(w("body"))
            scope = body if body is not None else self.root
            return list(scope.iter(w("p")))
        out = []
        tag = w("footnote") if self.name == "footnotes" else w("endnote")
        for note in self.root.iter(tag):
            if note.get(w("type")):  # separator, continuationSeparator
                continue
            out.extend(list(note.iter(w("p"))))
        return out

    def label(self, idx):
        return "%s:%d" % (PART_PREFIX[self.name], idx)


def load_parts(path, names):
    parts = {}
    with zipfile.ZipFile(path) as z:
        available = set(z.namelist())
        parser = etree.XMLParser(remove_blank_text=False, huge_tree=True)
        for name in names:
            member = PARTS[name]
            if member not in available:
                continue
            tree = etree.parse(z.open(member), parser)
            parts[name] = Part(name, member, tree)
    return parts


def save_docx(src_path, dst_path, parts):
    replacements = {}
    for p in parts.values():
        replacements[p.path] = etree.tostring(
            p.tree, xml_declaration=True, encoding="UTF-8", standalone=True
        )
    with zipfile.ZipFile(src_path) as zin:
        infos = zin.infolist()
        with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in infos:
                data = replacements.get(info.filename)
                if data is None:
                    data = zin.read(info.filename)
                new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                new_info.compress_type = info.compress_type
                new_info.external_attr = info.external_attr
                new_info.internal_attr = info.internal_attr
                new_info.create_system = info.create_system
                zout.writestr(new_info, data)


def has_existing_revisions(parts):
    for p in parts.values():
        for tag in ("ins", "del", "moveFrom", "moveTo"):
            if p.root.find(".//" + w(tag)) is not None:
                return True
    return False


# --------------------------------------------------------------------------
# Editari
# --------------------------------------------------------------------------

def parse_edits(raw):
    if isinstance(raw, dict):
        edits = raw.get("edits", [])
        author = raw.get("author")
    elif isinstance(raw, list):
        edits = raw
        author = None
    else:
        raise ValueError("edits.json trebuie sa fie obiect sau lista")
    return edits, author


def _split_id(ref, default_part):
    if isinstance(ref, int):
        return default_part, ref
    s = str(ref)
    if ":" in s:
        pref, num = s.split(":", 1)
        part = PREFIX_PART.get(pref)
        if part is None:
            raise ValueError("prefix necunoscut in id '%s'" % s)
        return part, int(num)
    return default_part, int(s)


def apply_edits(parts, edits):
    """Construieste textele revizuite pe parte. Intoarce (revised, log)."""
    revised = {name: list(p.texts) for name, p in parts.items()}
    # marcaj pentru stergeri, ca sa nu strice indicii pana la final
    deleted = {name: set() for name in parts}
    inserted = {name: [] for name in parts}  # (pozitie_originala, before/after, text)
    log = []

    for n, ed in enumerate(edits, 1):
        op = ed.get("op", "replace")
        where = "editarea #%d (%s)" % (n, op)

        if op == "replace":
            part_name = ed.get("part", "document")
            if part_name not in parts:
                raise ValueError("%s: partea '%s' lipseste din document" % (where, part_name))
            find = ed.get("find")
            repl = ed.get("replace")
            if find is None or repl is None:
                raise ValueError("%s: cere 'find' si 'replace'" % where)
            all_occ = bool(ed.get("all", False))
            hits = 0
            for i, txt in enumerate(revised[part_name]):
                if i in deleted[part_name] or find not in txt:
                    continue
                count = -1 if all_occ else 1
                revised[part_name][i] = txt.replace(find, repl, count if count > 0 else -1)
                hits += txt.count(find) if all_occ else 1
                if not all_occ:
                    break
            if hits == 0:
                raise ValueError("%s: sirul cautat nu exista in document: %r" % (where, find))
            log.append({"edit": n, "op": op, "part": part_name, "hits": hits})

        elif op == "set_paragraph":
            part_name, idx = _split_id(ed["id"], ed.get("part", "document"))
            _check_idx(parts, part_name, idx, where)
            revised[part_name][idx] = ed["text"]
            log.append({"edit": n, "op": op, "id": "%s:%d" % (PART_PREFIX[part_name], idx)})

        elif op == "delete_paragraph":
            part_name, idx = _split_id(ed["id"], ed.get("part", "document"))
            _check_idx(parts, part_name, idx, where)
            deleted[part_name].add(idx)
            log.append({"edit": n, "op": op, "id": "%s:%d" % (PART_PREFIX[part_name], idx)})

        elif op in ("insert_after", "insert_before"):
            part_name, idx = _split_id(ed["id"], ed.get("part", "document"))
            _check_idx(parts, part_name, idx, where)
            inserted[part_name].append((idx, op, ed["text"]))
            log.append({"edit": n, "op": op, "id": "%s:%d" % (PART_PREFIX[part_name], idx)})

        else:
            raise ValueError("%s: operatie necunoscuta '%s'" % (where, op))

    out = {}
    for name, texts in revised.items():
        seq = []
        by_pos_before = {}
        by_pos_after = {}
        for idx, op, text in inserted[name]:
            (by_pos_before if op == "insert_before" else by_pos_after).setdefault(idx, []).append(text)
        for i, txt in enumerate(texts):
            seq.extend(by_pos_before.get(i, []))
            if i not in deleted[name]:
                seq.append(txt)
            seq.extend(by_pos_after.get(i, []))
        out[name] = seq
    return out, log


def _check_idx(parts, part_name, idx, where):
    if part_name not in parts:
        raise ValueError("%s: partea '%s' lipseste din document" % (where, part_name))
    if not (0 <= idx < len(parts[part_name].paragraphs)):
        raise ValueError("%s: indicele %d e in afara intervalului 0..%d" %
                         (where, idx, len(parts[part_name].paragraphs) - 1))


def read_revised_texts(path):
    low = path.lower()
    if low.endswith(".docx"):
        parts = load_parts(path, ["document"])
        if "document" not in parts:
            raise ValueError("fisierul revizuit nu contine word/document.xml")
        return list(parts["document"].texts)
    with open(path, "r", encoding="utf-8-sig") as fh:
        raw = fh.read()
    lines = [ln.rstrip() for ln in raw.replace("\r\n", "\n").split("\n")]
    return [ln for ln in lines if ln.strip()]


# --------------------------------------------------------------------------
# Motorul principal
# --------------------------------------------------------------------------

def apply_revisions(part: Part, new_texts, author, date, ids, stats, caps_styles=None):
    caps_styles = caps_styles or set()
    plan = align(part.texts, new_texts)
    paragraphs = part.paragraphs
    last_index = len(paragraphs) - 1
    pending_inserts = []

    def _sursa_formei(anchor, precedent):
        """Paragraful de la care noul paragraf isi ia forma.

        Se prefera cel precedent, fiindca textul adaugat continua sectiunea in care a
        fost introdus. Ancora era pana acum paragraful urmator, ceea ce mergea prost
        exact in cazul frecvent al materialului adaugat la sfarsitul unei sectiuni:
        urmatorul e titlul sectiunii care incepe, iar paragrafele noi ieseau cu stilul
        de titlu, deci cu majuscule si cu culoarea titlului. Semnalat de autor pe
        30 iulie 2026, pe redlineul exceptiei Transcarpat.

        Cand precedentul afiseaza majuscule, adica e la rândul lui un titlu, se trece
        pe cel urmator. Daca amandoua sunt titluri, rămâne ancora, ca sa nu se piarda
        poziția.
        """
        if precedent is None:
            return anchor
        if afiseaza_majuscule(precedent, caps_styles) and not afiseaza_majuscule(anchor, caps_styles):
            return anchor
        return precedent

    def flush_inserts(anchor, position, precedent=None):
        nonlocal pending_inserts
        sursa = _sursa_formei(anchor, precedent)
        for text in pending_inserts:
            new_p = etree.Element(w("p"))
            ppr = sursa.find(w("pPr"))
            if ppr is not None:
                new_p.append(deepcopy(ppr))
                sect = new_p.find(w("pPr") + "/" + w("sectPr"))
                if sect is not None:
                    new_p.find(w("pPr")).remove(sect)
            template_rpr = None
            for a in decompose(sursa):
                if a.kind == "text":
                    template_rpr = a.rpr
                    break
            items = [Item("text", text=text, rpr=template_rpr, ctx=None, mode="ins")]
            rebuild_paragraph(new_p, items, author, date, ids, mark="ins")
            parent = anchor.getparent()
            at = list(parent).index(anchor)
            parent.insert(at if position == "before" else at + 1, new_p)
            stats["inserted_paragraphs"] += 1
        pending_inserts = []

    first_anchor = None
    precedent = None
    for kind, i, j in plan:
        if kind == "insert":
            pending_inserts.append(new_texts[j])
            continue

        p = paragraphs[i]
        if first_anchor is None:
            first_anchor = p
        if pending_inserts:
            flush_inserts(p, "before", precedent=precedent)
        precedent = p

        if kind == "keep":
            continue
        if kind == "change":
            atoms = decompose(p)
            text_nou = new_texts[j]
            # Numarul de lista il pune Word din w:numPr, deci un numar scris ca
            # text ar aparea de doua ori si ar bloca renumerotarea automata.
            if are_numerotare(p) and not _MARCAJ_LISTA.match(part.texts[i] or ""):
                text_nou = scoate_marcaj_lista(text_nou)
            items = build_items(atoms, text_nou,
                                ignora_capitalizarea=afiseaza_majuscule(p, caps_styles))
            if any(it.mode != "keep" for it in items):
                stats["changed_paragraphs"] += 1
            rebuild_paragraph(p, items, author, date, ids)
        elif kind == "delete":
            atoms = decompose(p)
            items = build_items(atoms, None, force_mode="del")
            mark = "del" if i < last_index else None
            rebuild_paragraph(p, items, author, date, ids, mark=mark)
            stats["deleted_paragraphs"] += 1

    if pending_inserts:
        anchor = paragraphs[-1] if paragraphs else None
        if anchor is None:
            raise ValueError("documentul nu are paragrafe, nu pot ancora inserarile")
        flush_inserts(anchor, "after")


def enable_track_changes_flag(parts):
    """Nu marcam documentul ca 'inregistreaza modificari' pentru editari viitoare.

    Reviziile scrise de tool sunt deja marcate; forta setarii ar schimba
    comportamentul Word-ului pentru utilizator. Pastram documentul asa cum e.
    """
    return


def cmd_list(args):
    names = [n.strip() for n in args.parts.split(",") if n.strip()]
    names = [PREFIX_PART.get(n, n) for n in names]
    parts = load_parts(args.input, names)
    for name in names:
        if name not in parts:
            continue
        part = parts[name]
        for i, (p, txt) in enumerate(zip(part.paragraphs, part.texts)):
            style = ""
            ppr = p.find(w("pPr"))
            if ppr is not None:
                st = ppr.find(w("pStyle"))
                if st is not None:
                    style = " [%s]" % st.get(w("val"))
            print("%-10s%s %s" % (part.label(i), style, txt))
    return 0


def cmd_apply(args):
    names = [n.strip() for n in args.parts.split(",") if n.strip()]
    names = [PREFIX_PART.get(n, n) for n in names]
    parts = load_parts(args.input, names)
    if "document" not in parts:
        sys.stderr.write("Fisierul nu contine word/document.xml\n")
        return 2

    author = args.author
    date = args.date or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if has_existing_revisions(parts):
        sys.stderr.write(
            "ATENTIE: documentul sursa contine deja modificari urmarite. "
            "Reviziile vechi raman intacte, dar verifica rezultatul in Word.\n")

    if args.edits:
        with open(args.edits, "r", encoding="utf-8-sig") as fh:
            raw = json.load(fh)
        edits, edits_author = parse_edits(raw)
        if edits_author and args.author == PARSER_DEFAULT_AUTHOR:
            author = edits_author
        revised, log = apply_edits(parts, edits)
    elif args.revised:
        revised = {"document": read_revised_texts(args.revised)}
        log = [{"op": "revised-file", "source": args.revised}]
        # Un fisier text nu poate exprima "pastreaza paragraful gol", fiindca
        # cititorul ii arunca liniile goale. Cand originalul are paragrafe goale
        # de spatiere, ele ajung marcate ca stergeri, iar avocatul primeste
        # revizii pe care nu le-a cerut. Semnalam, in loc sa taiem tacut.
        if not args.revised.lower().endswith(".docx"):
            goale = sum(1 for t in parts["document"].texts if not t.strip())
            if goale:
                sys.stderr.write(
                    "Atentie: originalul are %d paragrafe goale, iar fisierul revizuit e text, "
                    "deci ele vor aparea ca paragrafe sterse. Trimite varianta revizuita ca .docx "
                    "daca vrei sa ramana pe loc.\n" % goale)
    else:
        sys.stderr.write("Cere --edits sau --revised\n")
        return 2

    stats = {"changed_paragraphs": 0, "inserted_paragraphs": 0, "deleted_paragraphs": 0}
    id_base = _max_revision_id(parts)
    ids = RevisionIds(start=id_base)

    caps_styles = stiluri_cu_majuscule(args.input)
    for name, new_texts in revised.items():
        if name not in parts:
            continue
        apply_revisions(parts[name], new_texts, author, date, ids, stats, caps_styles)

    args.output = str(alege(args.output, args.suprascrie))
    save_docx(args.input, args.output, parts)

    report = {
        "input": args.input,
        "output": args.output,
        "author": author,
        "date": date,
        "edits": log,
        "stats": stats,
        "revisions_written": ids.n - id_base,
    }
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    total = stats["changed_paragraphs"] + stats["inserted_paragraphs"] + stats["deleted_paragraphs"]
    if total == 0:
        sys.stderr.write("Nicio modificare scrisa. Verifica editarile.\n")
        return 1
    return 0


def _max_revision_id(parts):
    best = 1000
    for p in parts.values():
        for tag in ("ins", "del"):
            for el in p.root.iter(w(tag)):
                try:
                    best = max(best, int(el.get(w("id")) or 0))
                except ValueError:
                    pass
    return best


def spatii_de_nume_rupte(cale):
    """Partile in care Ignorable enumera prefixe pe care radacina nu le declara.

    Word raspunde "Word found unreadable content" si refuza fisierul, desi pachetul e
    XML valid si trece orice alta verificare. Defectul apare la serializare, cand
    prefixele originale sunt rebotezate fara ca lista din Ignorable sa fie rescrisa.
    Verificat pe cazul din 29 iulie 2026.

    Verificarea se ia din repara_pachet.py, care o tine la zi. Copia de mai jos ramane
    numai ca rezerva, pentru cazul in care modulul nu se poate importa. Ea se uita doar la
    Ignorable si doar in word/, iar pe 30 iulie 2026 a ratat un al doilea defect din
    aceeasi familie, prefixul dcterms rebotezat in docProps/core.xml.
    """
    import importlib.util as _imp
    import os as _os
    _cale_modul = _os.path.join(_os.path.expanduser("~"), ".claude", "skills",
                                "docx-footnotes", "scripts", "repara_pachet.py")
    if _os.path.exists(_cale_modul):
        try:
            _spec = _imp.spec_from_file_location("repara_pachet", _cale_modul)
            _modul = _imp.module_from_spec(_spec)
            _spec.loader.exec_module(_modul)
            return _modul.verifica(cale)
        except Exception:
            pass

    import re as _re
    import zipfile as _zip
    rupte = []
    with _zip.ZipFile(cale) as z:
        for parte in z.namelist():
            if not (parte.startswith("word/") and parte.endswith(".xml")):
                continue
            try:
                xml = z.read(parte).decode("utf-8")
            except (KeyError, UnicodeDecodeError):
                continue
            i = xml.find("<w:")
            if i < 0:
                continue
            root = xml[i:xml.find(">", i) + 1]
            declarate = set(_re.findall(r'xmlns:([A-Za-z0-9_]+)=', root))
            ign = _re.search(r'([A-Za-z0-9_]+):Ignorable="([^"]*)"', root)
            if ign:
                lipsa = [p for p in ign.group(2).split() if p not in declarate]
                if lipsa:
                    rupte.append("%s (%s)" % (parte, " ".join(lipsa)))
    return rupte


def cmd_verify(args):
    parts = load_parts(args.input, list(PARTS.keys()))
    found = []
    for name, part in parts.items():
        for tag in ("ins", "del"):
            for el in part.root.iter(w(tag)):
                if el.getparent() is not None and el.getparent().tag == w("rPr"):
                    kind = "paragraph-mark-" + tag
                    text = ""
                else:
                    kind = tag
                    text = "".join(
                        (t.text or "") for t in el.iter(w("t"), w("delText"))
                    )
                found.append({
                    "part": name,
                    "type": kind,
                    "author": el.get(w("author")),
                    "date": el.get(w("date")),
                    "text": text,
                })
    larg = revizii_prea_largi(parts)
    ns_rupte = spatii_de_nume_rupte(args.input)
    summary = {
        "input": args.input,
        "total": len(found),
        "insertions": sum(1 for f in found if f["type"] == "ins"),
        "deletions": sum(1 for f in found if f["type"] == "del"),
        "paragraph_marks": sum(1 for f in found if f["type"].startswith("paragraph-mark")),
        "redline_prea_larg": larg,
        "spatii_de_nume_rupte": ns_rupte,
        "revisions": found if args.detail else found[:20],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if ns_rupte:
        sys.stderr.write(
            "BLOCANT: Word va refuza fisierul, Ignorable enumera prefixe nedeclarate in "
            "%s. Repara cu: python ~/.claude/skills/docx-footnotes/scripts/"
            "repara_pachet.py repara --input %s\n" % ("; ".join(ns_rupte), args.input))
        return 1
    if larg:
        sys.stderr.write(
            "Atentie: %d revizii taie si rescriu cuvinte nemodificate. Marcajul se "
            "ingusteaza la cuvantul schimbat, vezi 'redline_prea_larg'.\n" % len(larg))
        if args.strict:
            return 1
    return 0


# Autorul scris in fiecare <w:ins> si <w:del>, adica numele care apare in balonul de
# revizie din Word, la partea adversa si la client. Poarta marca sub care apare public
# cabinetul, nu numele avocatului. Cerut explicit pe 29 iulie 2026.
# Ramane sentinela pentru regula din cmd_apply: cand edits.json isi declara propriul
# autor si linia de comanda nu a cerut altul, castiga cel din fisier.
PARSER_DEFAULT_AUTHOR = "AMZ Law Office"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Scrie track changes native Word intr-un .docx, fara sa deschida Word.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="listeaza paragrafele numerotate")
    p_list.add_argument("--input", required=True)
    p_list.add_argument("--parts", default="document")
    p_list.set_defaults(func=cmd_list)

    p_apply = sub.add_parser("apply", help="scrie modificarile urmarite")
    p_apply.add_argument("--input", required=True)
    p_apply.add_argument("--output", required=True)
    adauga_optiune(p_apply)
    p_apply.add_argument("--edits", help="fisier JSON cu editari")
    p_apply.add_argument("--revised", help="varianta revizuita (.docx, .txt sau .md)")
    p_apply.add_argument("--author", default=PARSER_DEFAULT_AUTHOR)
    p_apply.add_argument("--date", help="ISO 8601, implicit acum (UTC)")
    p_apply.add_argument("--parts", default="document,footnotes,endnotes")
    p_apply.add_argument("--report", help="scrie raportul JSON in fisier")
    p_apply.set_defaults(func=cmd_apply)

    p_ver = sub.add_parser("verify", help="raporteaza reviziile dintr-un .docx")
    p_ver.add_argument("--input", required=True)
    p_ver.add_argument("--detail", action="store_true")
    p_ver.add_argument("--strict", action="store_true",
                       help="cod de iesire diferit de zero cand un marcaj e mai lat "
                            "decat modificarea")
    p_ver.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError) as exc:
        sys.stderr.write("EROARE: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
