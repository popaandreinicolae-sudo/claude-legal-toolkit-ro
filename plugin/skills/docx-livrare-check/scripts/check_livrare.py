#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_livrare.py

Verifica fisierul .docx inainte sa plece: format, metadate, sanatate tehnica.

Nu se atinge de continut. Citarile, sursele-fantoma, cifrele si tonul le verifica
subagentul `quality-gate`, prin quality_gate.py. Aici se uita cineva la fisier, nu la
ce scrie in el.

Stilul de casa contra caruia se compara a fost masurat pe 136 de acte proprii,
ponderat dupa cate caractere poarta fiecare setare. Vezi tabelul din SKILL.md.

Utilizare
---------
    python check_livrare.py document.docx
    python check_livrare.py document.docx --redline     # redline-ul e livrabilul
    python check_livrare.py document.docx --academic    # format UB Drept, nu casa
    python check_livrare.py document.docx --json

Cod de iesire 0 daca nu exista probleme blocante, 1 daca exista.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
DC = "{http://purl.org/dc/elements/1.1/}"

AUTOR = "Adrian Zamfir"          # proprietatile documentului, docProps/core.xml
MARCA_REVIZIE = "AMZ Law Office"  # balonul de revizie din Word, <w:ins> si <w:del>

# Numele apare in Word in mai multe forme, dupa profilul masinii si dupa cum a fost
# scris in acte: "Adrian Zamfir", "Zamfir Mihai-Adrian", "Adrian-Mihai Zamfir". Toate
# sunt ale aceleiasi persoane, deci verificarea se face pe cuvinte, nu pe sir exact.
def e_al_meu(nume: str | None) -> bool:
    if not nume:
        return False
    plat = nume.lower()
    for a, b in (("ă", "a"), ("â", "a"), ("î", "i"), ("ș", "s"), ("ş", "s"),
                 ("ț", "t"), ("ţ", "t")):
        plat = plat.replace(a, b)
    cuvinte = set(re.split(r"[^a-z]+", plat)) - {""}
    if "zamfir" in cuvinte and cuvinte & {"adrian", "mihai", "amz"}:
        return True
    return bool(cuvinte & {"amz"}) and "law" in cuvinte

# stilul de casa masurat; None inseamna ca nu se verifica
CASA = {
    "font": "Georgia",
    "sz_pt": 10.0,
    "jc": "both",
    "line_twips": 280,
    "line_rule": "atLeast",
    "before_pt": 6.0,
    "after_pt": 6.0,
    "first_line_cm": 1.27,
    "margins_cm": {"top": 2.0, "bottom": 0.71, "left": 3.5, "right": 1.5},
    "fn_font": "Georgia",
    "fn_sz_pt": 8.0,
}

ACADEMIC = {
    "font": "Times New Roman",
    "sz_pt": 12.0,
    "jc": "both",
    "line_twips": 360,
    "line_rule": "auto",
    "before_pt": None,
    "after_pt": None,
    "first_line_cm": 1.27,
    "margins_cm": {"top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.0},
    "fn_font": "Times New Roman",
    "fn_sz_pt": 10.0,
}

INVIZIBILE = {
    chr(0x200B): "ZWSP",
    chr(0x200C): "ZWNJ",
    chr(0x200D): "ZWJ",
    chr(0xFEFF): "BOM",
    chr(0x00AD): "cratima moale",
}

MARCAJE_REVIZIE = ("ins", "del", "rPrChange", "pPrChange", "moveFrom", "moveTo")


class Raport:
    def __init__(self):
        self.blocante: list[str] = []
        self.avertismente: list[str] = []
        self.ok: list[str] = []

    def bloc(self, msg):
        self.blocante.append(msg)

    def avert(self, msg):
        self.avertismente.append(msg)

    def bun(self, msg):
        self.ok.append(msg)


def val(el, attr="val"):
    return None if el is None else el.get(f"{W}{attr}")


def citeste(z, nume):
    try:
        return ET.fromstring(z.read(nume))
    except KeyError:
        return None
    except ET.ParseError as e:
        raise SystemExit(f"XML invalid in {nume}: {e}")


def twips_cm(t):
    try:
        return round(int(t) * 2.54 / 1440, 2)
    except (TypeError, ValueError):
        return None


def half_pt(s):
    try:
        return int(s) / 2
    except (TypeError, ValueError):
        return None


def dominant(counter):
    """Valoarea cu cea mai mare pondere si procentul ei."""
    if not counter:
        return None, 0
    v, n = counter.most_common(1)[0]
    return v, round(100 * n / sum(counter.values()))


def verifica_format(z, doc, ref, rap):
    styles = citeste(z, "word/styles.xml")
    normal_font = normal_sz = None
    if styles is not None:
        # implicitul documentului, de unde mostenesc run-urile care nu declara nimic
        d = styles.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
        if d is not None:
            normal_font = val(d.find(f"{W}rFonts"), "ascii")
            normal_sz = val(d.find(f"{W}sz"))
        # stilul Normal, daca il suprascrie
        for s in styles.iter(f"{W}style"):
            if s.get(f"{W}styleId") == "Normal":
                rpr = s.find(f"{W}rPr")
                if rpr is not None:
                    normal_font = val(rpr.find(f"{W}rFonts"), "ascii") or normal_font
                    normal_sz = val(rpr.find(f"{W}sz")) or normal_sz

    fonturi, marimi = collections.Counter(), collections.Counter()
    alin, linii, reguli = collections.Counter(), collections.Counter(), collections.Counter()
    inainte, dupa, alineat = collections.Counter(), collections.Counter(), collections.Counter()

    for para in doc.iter(f"{W}p"):
        ppr = para.find(f"{W}pPr")
        pstyle = val(ppr.find(f"{W}pStyle")) if ppr is not None else None
        if pstyle and pstyle.lower().startswith(("heading", "titl", "toc")):
            continue
        lungime = sum(len(t.text or "") for t in para.iter(f"{W}t"))
        if lungime < 40:
            continue
        if ppr is not None:
            j = val(ppr.find(f"{W}jc"))
            if j:
                alin[j] += 1
            sp = ppr.find(f"{W}spacing")
            if sp is not None:
                if sp.get(f"{W}line"):
                    linii[sp.get(f"{W}line")] += 1
                if sp.get(f"{W}lineRule"):
                    reguli[sp.get(f"{W}lineRule")] += 1
                if sp.get(f"{W}before"):
                    inainte[sp.get(f"{W}before")] += 1
                if sp.get(f"{W}after"):
                    dupa[sp.get(f"{W}after")] += 1
            ind = ppr.find(f"{W}ind")
            if ind is not None and ind.get(f"{W}firstLine"):
                alineat[twips_cm(ind.get(f"{W}firstLine"))] += 1
        for r in para.iter(f"{W}r"):
            rl = sum(len(t.text or "") for t in r.iter(f"{W}t"))
            if rl == 0:
                continue
            rpr = r.find(f"{W}rPr")
            f = val(rpr.find(f"{W}rFonts"), "ascii") if rpr is not None else None
            s = val(rpr.find(f"{W}sz")) if rpr is not None else None
            fonturi[f or normal_font or "(mostenit)"] += rl
            m = half_pt(s) or half_pt(normal_sz)
            if m:
                marimi[m] += rl

    f_dom, f_pct = dominant(fonturi)
    if f_dom and f_dom != ref["font"] and f_dom != "(mostenit)":
        rap.bloc(f"font corp {f_dom} ({f_pct}% din text), asteptat {ref['font']}")
    elif f_dom:
        rap.bun(f"font corp {f_dom} ({f_pct}%)")

    m_dom, m_pct = dominant(marimi)
    if m_dom and abs(m_dom - ref["sz_pt"]) > 0.01:
        rap.avert(f"marime corp {m_dom} pt ({m_pct}%), stilul de casa cere {ref['sz_pt']} pt")
    elif m_dom:
        rap.bun(f"marime corp {m_dom} pt ({m_pct}%)")

    j_dom, j_pct = dominant(alin)
    if j_dom and j_dom != ref["jc"]:
        rap.avert(f"aliniere dominanta {j_dom} ({j_pct}%), asteptat {ref['jc']}")
    elif j_dom:
        rap.bun(f"aliniere {j_dom} ({j_pct}%)")

    r_dom, _ = dominant(reguli)
    l_dom, _ = dominant(linii)
    if ref["line_rule"] and r_dom and r_dom != ref["line_rule"]:
        rap.avert(f"regula de interlinie {r_dom}, stilul de casa cere {ref['line_rule']}")
    if ref["line_twips"] and l_dom and abs(int(l_dom) - ref["line_twips"]) > 20:
        rap.avert(f"interlinie {l_dom} twips, stilul de casa cere ~{ref['line_twips']}")

    for cheie, cnt, eticheta in (("before_pt", inainte, "spatiu inainte"),
                                 ("after_pt", dupa, "spatiu dupa")):
        if ref[cheie] is None:
            continue
        d, _ = dominant(cnt)
        if d and abs(int(d) / 20 - ref[cheie]) > 0.5:
            rap.avert(f"{eticheta} {int(d)/20} pt, stilul de casa cere {ref[cheie]} pt")

    a_dom, _ = dominant(alineat)
    if a_dom is not None and abs(a_dom - ref["first_line_cm"]) > 0.05:
        rap.avert(f"alineat prima linie {a_dom} cm, stilul de casa cere {ref['first_line_cm']} cm")

    pg = doc.find(f"{W}body/{W}sectPr/{W}pgMar")
    if pg is None:
        rap.avert("nu am gasit sectiunea cu marginile")
    else:
        for latura, astept in ref["margins_cm"].items():
            gasit = twips_cm(pg.get(f"{W}{latura}"))
            if gasit is None:
                continue
            if abs(gasit - astept) > 0.06:
                rap.avert(f"margine {latura} {gasit} cm, stilul de casa cere {astept} cm")

    fn = citeste(z, "word/footnotes.xml")
    if fn is not None:
        ff, fs = collections.Counter(), collections.Counter()
        for nota in fn.iter(f"{W}footnote"):
            if nota.get(f"{W}type"):
                continue
            for r in nota.iter(f"{W}r"):
                rl = sum(len(t.text or "") for t in r.iter(f"{W}t"))
                if rl == 0:
                    continue
                rpr = r.find(f"{W}rPr")
                if rpr is None:
                    continue
                if val(rpr.find(f"{W}rFonts"), "ascii"):
                    ff[val(rpr.find(f"{W}rFonts"), "ascii")] += rl
                if half_pt(val(rpr.find(f"{W}sz"))):
                    fs[half_pt(val(rpr.find(f"{W}sz")))] += rl
        d, pct = dominant(ff)
        if d and d != ref["fn_font"]:
            rap.avert(f"font note {d} ({pct}%), asteptat {ref['fn_font']}")
        d, pct = dominant(fs)
        if d and abs(d - ref["fn_sz_pt"]) > 0.01:
            rap.avert(f"marime note {d} pt ({pct}%), stilul de casa cere {ref['fn_sz_pt']} pt")


TITLU_CULORI = {"244061", "1F497D", "1F3864", "365F91", "2F5496"}
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"


def verifica_identitate(z, doc, ref, rap):
    """Antetul cu logo, subsolul cu numerotare, titlurile bleumarin.

    Astea sunt partile de stil pe care o instructiune scrisa in proza nu le poate
    produce, fiindca traiesc in XML: imaginea din antet, campurile PAGE si NUMPAGES,
    culoarea din stilul de titlu. De aceea le verificam separat de fonturi si margini.
    """
    if ref is not CASA:
        return  # formatul academic nu poarta antetul cabinetului

    nume = z.namelist()

    anteturi = [n for n in nume if re.match(r"word/header\d*\.xml$", n)]
    cu_logo = False
    for h in anteturi:
        r = citeste(z, h)
        if r is None:
            continue
        if list(r.iter(f"{WP}extent")) or list(r.iter(f"{W}drawing")) or list(r.iter(f"{W}pict")):
            cu_logo = True
    # Antetul se pune numai pe prima pagina. Toate cele 86 de acte proprii au `titlePg`,
    # iar referinta de antet e de tip `first` in 84 dintre ele, fara antet implicit.
    # Un logo repetat pe fiecare pagina se vede imediat si nu e forma casei.
    sect = doc.find(f"{W}body/{W}sectPr")
    tipuri = set()
    prima_diferita = False
    if sect is not None:
        prima_diferita = sect.find(f"{W}titlePg") is not None
        tipuri = {r.get(f"{W}type") for r in sect.findall(f"{W}headerReference")}

    if cu_logo and prima_diferita and "default" not in tipuri:
        rap.bun("antet cu logo, doar pe prima pagina")
    elif cu_logo and not prima_diferita:
        rap.avert("antetul se repeta pe fiecare pagina; lipseste w:titlePg, "
                  "iar actele proprii il poarta doar pe prima")
    elif cu_logo and "default" in tipuri:
        rap.avert("exista si antet implicit, deci logo-ul apare si pe paginile urmatoare")
    elif anteturi:
        rap.avert("antetul exista dar nu are logo; actele proprii il poarta in 82 din 84 de cazuri")
    else:
        rap.avert("documentul nu are antet; actele proprii au in 86% din cazuri")

    subsoluri = [n for n in nume if re.match(r"word/footer\d*\.xml$", n)]
    cu_numerotare = False
    for f in subsoluri:
        r = citeste(z, f)
        if r is None:
            continue
        instr = " ".join(i.text or "" for i in r.iter(f"{W}instrText"))
        if "PAGE" in instr:
            cu_numerotare = True
    if cu_numerotare:
        rap.bun("subsol cu numerotare automata")
    elif subsoluri:
        rap.avert("subsolul nu are camp PAGE; un numar scris ca text nu se actualizeaza")
    else:
        rap.avert("documentul nu are subsol; actele proprii au in 94% din cazuri")

    # Stilurile aplicate pe paragrafele cu text. Sablonul aduce definitiile, dar
    # continutul scris cu `add_paragraph` simplu ramane pe Normal, iar actul iese cu
    # marginile corecte si structura altcuiva. Masurat pe 7660 de paragrafe proprii:
    # Bodycunrdeparagraf 56%, Normal 25%, bold in 53%, numerotare automata in 61%.
    aplicate = collections.Counter()
    cu_bold = numerotate = cu_text = 0
    for p in doc.iter(f"{W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{W}t")).strip()
        if not text:
            continue
        cu_text += 1
        ppr = p.find(f"{W}pPr")
        aplicate[(val(ppr.find(f"{W}pStyle")) if ppr is not None else None) or "(Normal)"] += 1
        if ppr is not None and ppr.find(f"{W}numPr") is not None:
            numerotate += 1
        for r in p.iter(f"{W}r"):
            rpr = r.find(f"{W}rPr")
            if rpr is not None and rpr.find(f"{W}b") is not None:
                cu_bold += 1
                break

    if cu_text >= 10:
        corp = aplicate.get("Bodycunrdeparagraf", 0)
        if corp * 100 // cu_text < 25:
            rap.avert(f"doar {corp} din {cu_text} paragrafe folosesc stilul de corp "
                      f"Bodycunrdeparagraf; in actele proprii acopera 56%")
        else:
            rap.bun(f"stil de corp aplicat pe {corp * 100 // cu_text}% din paragrafe")
        if numerotate * 100 // cu_text < 30:
            rap.avert(f"doar {numerotate * 100 // cu_text}% din paragrafe sunt numerotate "
                      f"automat; in actele proprii 61%. Numerele scrise ca text se strica "
                      f"la prima insertie.")
        if cu_bold * 100 // cu_text < 25:
            rap.avert(f"bold doar in {cu_bold * 100 // cu_text}% din paragrafe; in actele "
                      f"proprii 53%, pe termeni definiti, parti si temeiuri")

    # Doar stilurile de titlu FOLOSITE efectiv in corp. Un document Word poarta din
    # sablon zeci de stiluri nefolosite, Heading4-9 si variantele Char, cu culorile
    # implicite ale temei. Numarate la gramada, ele acopera culoarea reala a titlurilor.
    folosite = set()
    for p in doc.iter(f"{W}p"):
        ppr = p.find(f"{W}pPr")
        if ppr is None:
            continue
        ps = val(ppr.find(f"{W}pStyle")) or ""
        if ps.lower().startswith(("heading", "title", "titlu")) or "titl" in ps.lower():
            folosite.add(ps)
    if not folosite:
        return

    styles = citeste(z, "word/styles.xml")
    culori = collections.Counter()
    if styles is not None:
        for s in styles.iter(f"{W}style"):
            if (s.get(f"{W}styleId") or "") not in folosite:
                continue
            rpr = s.find(f"{W}rPr")
            if rpr is None:
                continue
            c = val(rpr.find(f"{W}color"))
            if c and c.upper() not in ("AUTO", "000000"):
                culori[c.upper()] += 1
    if not culori:
        rap.avert("titlurile nu au culoare; stilul de casa le scrie bleumarin #244061")
    elif set(culori) & TITLU_CULORI:
        rap.bun(f"titluri colorate #{max(culori, key=culori.get)}")
    else:
        rap.avert(f"culoare de titlu neobisnuita #{max(culori, key=culori.get)}, "
                  f"stilul de casa foloseste #244061")


def verifica_metadate(z, doc, rap, redline):
    core = citeste(z, "docProps/core.xml")
    autor = ultim = None
    if core is not None:
        a = core.find(f"{DC}creator")
        u = core.find(f"{CP}lastModifiedBy")
        autor = a.text if a is not None else None
        ultim = u.text if u is not None else None

    if e_al_meu(ultim):
        rap.bun(f"lastModifiedBy = {ultim!r}")
    elif not ultim:
        rap.avert(f"lastModifiedBy gol, pune {AUTOR!r} inainte de trimitere")
    else:
        rap.bloc(f"lastModifiedBy = {ultim!r}, document strain la ultima salvare. "
                 f"Pune {AUTOR!r}.")

    if not autor:
        rap.avert("documentul nu are autor in proprietati")
    elif e_al_meu(autor):
        rap.bun(f"author = {autor!r}, document propriu")
    else:
        rap.avert(f"author = {autor!r}. Daca documentul e primit, asa ramane. "
                  f"Daca e actul tau scris peste un sablon strain, schimba-l.")

    app = citeste(z, "docProps/app.xml")
    if app is not None:
        for el in app.iter():
            if el.text and ("\\" in el.text or el.text.startswith("/")) and ":" in el.text:
                rap.avert(f"cale de fisier ramasa in docProps/app.xml: {el.text[:60]}")
                break

    custom = citeste(z, "docProps/custom.xml")
    if custom is not None:
        nume = [p.get("name") for p in custom if p.get("name")]
        if nume:
            rap.avert(f"proprietati personalizate ramase: {', '.join(nume[:6])}")

    comentarii = citeste(z, "word/comments.xml")
    if comentarii is not None:
        n = len(list(comentarii.iter(f"{W}comment")))
        if n:
            rap.bloc(f"{n} comentarii ramase in document")

    revizii = collections.Counter()
    for marcaj in MARCAJE_REVIZIE:
        for el in doc.iter(f"{W}{marcaj}"):
            revizii[el.get(f"{W}author") or "(fara autor)"] += 1
    total = sum(revizii.values())
    if total and not redline:
        cine = ", ".join(f"{a} ({n})" for a, n in revizii.most_common())
        rap.bloc(f"{total} revizii urmarite ramase, de la {cine}. "
                 f"Ruleaza cu --redline daca redline-ul e livrabilul.")
    elif total:
        rap.bun(f"{total} revizii urmarite, livrare de tip redline")
        # Reviziile noastre poarta marca, nu numele avocatului, fiindca balonul din Word
        # se citeste la partea adversa si la client.
        ale_noastre = [a for a in revizii if a == MARCA_REVIZIE]
        personale = [a for a in revizii if a != MARCA_REVIZIE and e_al_meu(a)]
        straini = [a for a in revizii
                   if a != MARCA_REVIZIE and not e_al_meu(a) and a != "(fara autor)"]
        if personale:
            rap.avert(f"revizii semnate cu numele avocatului: {', '.join(personale)}. "
                      f"Marca de casa e {MARCA_REVIZIE!r}.")
        if straini:
            rap.avert(f"revizii de la alti autori in document: {', '.join(straini)}")
        if ale_noastre and not personale and not straini:
            rap.bun(f"toate reviziile poarta {MARCA_REVIZIE!r}")
    else:
        rap.bun("zero revizii urmarite")

    gasite = collections.Counter()
    for t in doc.iter(f"{W}t"):
        for ch in (t.text or ""):
            if ch in INVIZIBILE:
                gasite[INVIZIBILE[ch]] += 1
    if gasite:
        rap.bloc("caractere invizibile: " +
                 ", ".join(f"{k} x{v}" for k, v in gasite.most_common()))
    else:
        rap.bun("zero caractere invizibile")


def verifica_tehnic(z, doc, rap):
    for necesar in ("[Content_Types].xml", "word/document.xml", "word/_rels/document.xml.rels"):
        if necesar not in z.namelist():
            rap.bloc(f"lipseste {necesar} din arhiva")

    stricat = z.testzip()
    if stricat:
        rap.bloc(f"arhiva corupta la {stricat}")

    paragrafe = sum(1 for p in doc.iter(f"{W}p")
                    if any((t.text or "").strip() for t in p.iter(f"{W}t")))
    rap.bun(f"{paragrafe} paragrafe cu text")

    fn = citeste(z, "word/footnotes.xml")
    if fn is not None:
        note = [f for f in fn.iter(f"{W}footnote") if f.get(f"{W}type") is None]
        goale = [i + 1 for i, f in enumerate(note)
                 if not "".join(t.text or "" for t in f.iter(f"{W}t")).strip()]
        rap.bun(f"{len(note)} note de subsol")
        if goale:
            rap.bloc(f"note goale: {', '.join(map(str, goale))}")

    ref = {int(r.get(f"{W}id")) for r in doc.iter(f"{W}footnoteReference")
           if r.get(f"{W}id") and r.get(f"{W}id").lstrip("-").isdigit()}
    if fn is not None:
        exista = {int(f.get(f"{W}id")) for f in fn.iter(f"{W}footnote")
                  if f.get(f"{W}id") and f.get(f"{W}id").lstrip("-").isdigit()}
        orfane = ref - exista
        if orfane:
            rap.bloc(f"referinte de nota fara nota: {sorted(orfane)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verificare .docx inainte de trimitere")
    ap.add_argument("docx", type=Path)
    ap.add_argument("--redline", action="store_true",
                    help="reviziile urmarite sunt livrabilul, nu o problema")
    ap.add_argument("--academic", action="store_true",
                    help="compara cu formatul UB Drept, nu cu stilul de casa")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.docx.exists():
        raise SystemExit(f"nu exista: {args.docx}")

    rap = Raport()
    ref = ACADEMIC if args.academic else CASA

    with zipfile.ZipFile(args.docx) as z:
        doc = citeste(z, "word/document.xml")
        if doc is None:
            raise SystemExit("word/document.xml lipseste, fisierul nu e un .docx valid")
        verifica_format(z, doc, ref, rap)
        verifica_identitate(z, doc, ref, rap)
        verifica_metadate(z, doc, rap, args.redline)
        verifica_tehnic(z, doc, rap)

    verdict = "NU TRIMITE" if rap.blocante else "GATA DE TRIMIS"

    if args.json:
        print(json.dumps({"verdict": verdict, "blocante": rap.blocante,
                          "avertismente": rap.avertismente, "ok": rap.ok},
                         ensure_ascii=False, indent=2))
    else:
        print(f"\n{args.docx.name}")
        print(f"profil: {'academic UB Drept' if args.academic else 'stil de casa'}"
              f"{', redline' if args.redline else ''}")
        print(f"\nVERDICT: {verdict}\n")
        if rap.blocante:
            print("BLOCANTE")
            for m in rap.blocante:
                print(f"  x {m}")
            print()
        if rap.avertismente:
            print("AVERTISMENTE")
            for m in rap.avertismente:
                print(f"  ! {m}")
            print()
        print("VERIFICAT")
        for m in rap.ok:
            print(f"  . {m}")
        print()

    return 1 if rap.blocante else 0


if __name__ == "__main__":
    sys.exit(main())
