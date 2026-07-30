#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docx_footnotes.py

Insereaza note de subsol NOI intr-un .docx, ca revizii urmarite native.

docx_track_changes.py modifica textul notelor existente, dar nu poate crea note noi:
o nota noua cere un element <w:footnote> in word/footnotes.xml plus un run de
referinta <w:footnoteReference> in corp. Modulul asta acopera exact golul.

De ce ancorare si nu marcaje in text
------------------------------------
Varianta evidenta, un marcaj de tipul [[fn:...]] scris in textul editarii, se rupe.
Motorul de redline compara la nivel de cuvant, iar un spatiu din interiorul marcajului
se poate alinia cu un spatiu din textul original; marcajul ajunge atunci taiat in trei,
cu text original prins la mijloc. Stergerea marcajului distruge acel caracter original
si Reject All nu mai reproduce documentul de plecare. Verificat pe cazul real.

Aici nota se ancoreaza de un fragment de text, nu se strecoara prin diff:

    {"id": "doc:34", "after": "viciul de neconstitutionalitate nu poate fi ignorat.",
     "text": "Decizia Curtii Constitutionale nr. 503 din 20 aprilie 2010, ..."}

Referinta se pune imediat dupa ultimul caracter al ancorei. Daca ancora cade in text
inserat, referinta intra in acelasi <w:ins>; daca ancora cade in text original,
referinta primeste propriul <w:ins>. In ambele cazuri nota apare ca insertie urmarita
si dispare la Reject All.

Ancora trebuie sa apara exact o data in paragraf. Daca lipseste sau e ambigua,
executia se opreste si nu se scrie niciun fisier, ca in restul skill-ului.

Utilizare
---------
    python docx_footnotes.py apply --input revizuit.docx --output final.docx \
        --notes note.json --author "AMZ Law Office"

    python docx_footnotes.py check --input final.docx
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lxml import etree
except ImportError:  # pragma: no cover
    sys.stderr.write("Lipseste lxml. Instaleaza: pip install lxml\n")
    raise

import docx_track_changes as dtc

w = dtc.w
XML_SPACE = dtc.XML_SPACE

DEFAULT_REF_STYLE = "FootnoteReference"
DEFAULT_TEXT_STYLE = "FootnoteText"

# Containere transparente: textul lor face parte din fluxul vizibil al paragrafului.
TRANSPARENT = {w("ins"), w("hyperlink"), w("smartTag")}
# Continut invizibil in varianta finala.
HIDDEN = {w("del"), w("moveFrom")}


class EditError(Exception):
    pass


# --------------------------------------------------------------------------
# Harta caracter -> nod, peste textul vizibil al paragrafului
# --------------------------------------------------------------------------

def _visible_map(paragraph):
    """[(t_node, run_node, start, end)] pentru textul vizibil, in ordinea documentului.

    Aceeasi semantica de text ca dtc.paragraph_text: <w:del> nu se numara.
    """
    out = []
    pos = 0

    def walk(node):
        nonlocal pos
        for child in node:
            tag = child.tag
            if tag == w("pPr") or tag in HIDDEN:
                continue
            if tag == w("r"):
                for sub in child:
                    if sub.tag == w("t"):
                        s = sub.text or ""
                        out.append((sub, child, pos, pos + len(s)))
                        pos += len(s)
            elif tag in TRANSPARENT:
                walk(child)

    walk(paragraph)
    return out


def _split_run_at(t_node, run, k):
    """Taie run-ul in doua la offsetul k din t_node. Intoarce run-ul care ramane in stanga.

    Partea dreapta devine un run nou, imediat dupa, in acelasi parinte.
    """
    text = t_node.text or ""
    if k >= len(text):
        return run
    # k vine intotdeauna din intervalul (a, b], deci taietura cade in interiorul textului
    head, tail = text[:k], text[k:]

    t_node.text = head
    if head:
        t_node.set(XML_SPACE, "preserve")

    new_run = etree.Element(w("r"))
    rpr = run.find(w("rPr"))
    if rpr is not None:
        new_run.append(etree.fromstring(etree.tostring(rpr)))
    # tot ce urmeaza dupa t_node in run-ul original trece in run-ul nou
    moving = []
    seen = False
    for sub in list(run):
        if sub is t_node:
            seen = True
            continue
        if seen and sub.tag != w("rPr"):
            moving.append(sub)
    new_t = etree.SubElement(new_run, w("t"))
    new_t.set(XML_SPACE, "preserve")
    new_t.text = tail
    for m in moving:
        run.remove(m)
        new_run.append(m)

    run.addnext(new_run)
    return run


def _make_ref_run(fid, model_run, ref_style):
    r = etree.Element(w("r"))
    rpr_src = model_run.find(w("rPr"))
    rpr = etree.fromstring(etree.tostring(rpr_src)) if rpr_src is not None else etree.Element(w("rPr"))
    for old in rpr.findall(w("rStyle")):
        rpr.remove(old)
    style = etree.Element(w("rStyle"))
    style.set(w("val"), ref_style)
    rpr.insert(0, style)
    r.append(rpr)
    ref = etree.SubElement(r, w("footnoteReference"))
    ref.set(w("id"), str(fid))
    return r


def _make_note(fid, text, text_style, ref_style, sz):
    note = etree.Element(w("footnote"))
    note.set(w("id"), str(fid))
    p = etree.SubElement(note, w("p"))
    ppr = etree.SubElement(p, w("pPr"))
    etree.SubElement(ppr, w("pStyle")).set(w("val"), text_style)

    r1 = etree.SubElement(p, w("r"))
    rpr1 = etree.SubElement(r1, w("rPr"))
    etree.SubElement(rpr1, w("rStyle")).set(w("val"), ref_style)
    if sz:
        for tag in ("sz", "szCs"):
            etree.SubElement(rpr1, w(tag)).set(w("val"), sz)
    etree.SubElement(r1, w("footnoteRef"))

    r2 = etree.SubElement(p, w("r"))
    if sz:
        rpr2 = etree.SubElement(r2, w("rPr"))
        for tag in ("sz", "szCs"):
            etree.SubElement(rpr2, w(tag)).set(w("val"), sz)
    t = etree.SubElement(r2, w("t"))
    t.set(XML_SPACE, "preserve")
    t.text = " " + text.strip()
    return note


def _note_size(fn_root):
    for note in fn_root.iter(w("footnote")):
        if note.get(w("type")):
            continue
        for sz in note.iter(w("sz")):
            return sz.get(w("val"))
    return None


def _max_id(fn_root):
    ids = []
    for note in fn_root.iter(w("footnote")):
        try:
            ids.append(int(note.get(w("id"))))
        except (TypeError, ValueError):
            pass
    return max(ids) if ids else 0


def _in_ins(node):
    anc = node.getparent()
    while anc is not None and anc.tag != w("p"):
        if anc.tag == w("ins"):
            return anc
        anc = anc.getparent()
    return None


# --------------------------------------------------------------------------
# Aplicarea notelor
# --------------------------------------------------------------------------

def add_footnotes(parts, notes, author, date, ref_style, text_style):
    if "footnotes" not in parts:
        raise EditError(
            "Documentul nu are word/footnotes.xml. Adauga o nota manuala in Word, "
            "salveaza, apoi reia. Tool-ul nu fabrica partea de la zero.")

    doc = parts["document"]
    fn_root = parts["footnotes"].root
    next_id = _max_id(fn_root) + 1
    sz = _note_size(fn_root)
    ids = dtc.RevisionIds(start=9000)

    # grupam pe paragraf si aplicam de la coada spre cap, ca offseturile sa ramana valide
    by_par = {}
    for n, spec in enumerate(notes, 1):
        ref = spec.get("id")
        if ref is None:
            raise EditError("nota #%d: lipseste 'id' (ex. \"doc:34\")" % n)
        part_name, idx = dtc._split_id(ref, "document")
        if part_name != "document":
            raise EditError("nota #%d: referintele se ancoreaza doar in corp (doc:N)" % n)
        if not (0 <= idx < len(doc.paragraphs)):
            raise EditError("nota #%d: paragraful %s nu exista (0..%d)"
                            % (n, ref, len(doc.paragraphs) - 1))
        by_par.setdefault(idx, []).append((n, spec))

    created = []
    for idx in sorted(by_par):
        p = doc.paragraphs[idx]
        placed = []
        for n, spec in by_par[idx]:
            anchor = spec.get("after")
            text = spec.get("text")
            if not anchor:
                raise EditError("nota #%d: lipseste 'after' (fragmentul de ancorare)" % n)
            if not text:
                raise EditError("nota #%d: lipseste 'text' (continutul notei)" % n)
            full = dtc.paragraph_text(p)
            hits = []
            start = full.find(anchor)
            while start != -1:
                hits.append(start)
                start = full.find(anchor, start + 1)
            if not hits:
                raise EditError(
                    "nota #%d: ancora nu exista in doc:%d\n  cautat: %r\n  paragraf: %r"
                    % (n, idx, anchor[:90], full[:160]))
            if len(hits) > 1:
                raise EditError(
                    "nota #%d: ancora apare de %d ori in doc:%d, extinde fragmentul\n  cautat: %r"
                    % (n, len(hits), idx, anchor[:90]))
            placed.append((hits[0] + len(anchor), n, text))

        for pos, n, text in sorted(placed, reverse=True):
            vmap = _visible_map(p)
            target = None
            for t_node, run, a, b in vmap:
                if a < pos <= b:
                    target = (t_node, run, pos - a)
                    break
            if target is None and vmap and pos == 0:
                t_node, run, a, b = vmap[0]
                target = (t_node, run, 0)
            if target is None:
                raise EditError("nota #%d: nu am putut localiza pozitia %d in doc:%d"
                                % (n, pos, idx))

            t_node, run, k = target
            left = _split_run_at(t_node, run, k)
            ref_run = _make_ref_run(next_id, run, ref_style)

            holder = _in_ins(left)
            if holder is None:
                wrapper = etree.Element(w("ins"))
                wrapper.set(w("id"), ids.next())
                wrapper.set(w("author"), author)
                wrapper.set(w("date"), date)
                wrapper.append(ref_run)
                left.addnext(wrapper)
            else:
                left.addnext(ref_run)

            fn_root.append(_make_note(next_id, text, text_style, ref_style, sz))
            created.append((next_id, idx, text))
            next_id += 1

    return created


def cmd_apply(args):
    parts = dtc.load_parts(args.input, ["document", "footnotes"])
    if "document" not in parts:
        sys.stderr.write("Documentul nu contine word/document.xml\n")
        return 2

    # utf-8-sig: PowerShell scrie BOM implicit, iar json.load refuza BOM-ul
    with open(args.notes, encoding="utf-8-sig") as f:
        raw = json.load(f)
    notes = raw.get("notes", raw) if isinstance(raw, dict) else raw
    author = args.author or (raw.get("author") if isinstance(raw, dict) else None) or "Autor"
    date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        created = add_footnotes(parts, notes, author, date, args.ref_style, args.text_style)
    except EditError as e:
        sys.stderr.write("EROARE: %s\n" % e)
        sys.stderr.write("Nu s-a scris niciun fisier.\n")
        return 3

    dtc.save_docx(args.input, args.output, parts)
    report = {"input": args.input, "output": args.output, "author": author,
              "created": [{"footnote_id": f, "paragraph": "doc:%d" % i, "text": t}
                          for f, i, t in created]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_check(args):
    parts = dtc.load_parts(args.input, ["document", "footnotes"])
    doc_root = parts["document"].root
    refs = [r.get(w("id")) for r in doc_root.iter(w("footnoteReference"))]
    notes = []
    if "footnotes" in parts:
        for note in parts["footnotes"].root.iter(w("footnote")):
            if note.get(w("type")):
                continue
            notes.append(note.get(w("id")))
    tracked = sum(1 for r in doc_root.iter(w("footnoteReference")) if _in_ins(r) is not None)

    orphan_ref = [i for i in refs if i not in notes]
    orphan_note = [i for i in notes if i not in refs]
    print("referinte in corp      : %d" % len(refs))
    print("note in footnotes.xml  : %d" % len(notes))
    print("referinte ca insertie  : %d" % tracked)
    print("referinte fara nota    : %s" % (orphan_ref or "niciuna"))
    print("note fara referinta    : %s" % (orphan_note or "niciuna"))
    return 1 if orphan_ref else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Note de subsol noi, ca revizii urmarite, intr-un .docx")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("apply", help="insereaza notele descrise in JSON")
    a.add_argument("--input", required=True)
    a.add_argument("--output", required=True)
    a.add_argument("--notes", required=True)
    a.add_argument("--author", default=None)
    a.add_argument("--ref-style", default=DEFAULT_REF_STYLE)
    a.add_argument("--text-style", default=DEFAULT_TEXT_STYLE)
    a.set_defaults(func=cmd_apply)

    c = sub.add_parser("check", help="verifica integritatea referintelor si notelor")
    c.add_argument("--input", required=True)
    c.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
