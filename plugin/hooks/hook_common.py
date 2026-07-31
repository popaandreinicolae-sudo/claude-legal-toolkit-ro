#!/usr/bin/env python3
"""
hook_common.py — nucleu comun pentru toate hook-urile anti-halucinare.

Sursa unica de adevar pentru: kill-switch global, skip-patterns, extensii suportate,
citirea textului (.docx/.md/.txt). Toate hook-urile importa de aici, ca sa nu divergheze
intre ele si sa nu produca semnale contradictorii.

Kill-switch: seteaza variabila de mediu ANTIHALU_OFF=1 ca sa dezactivezi instant toate
hook-urile anti-halucinare (fara a le scoate din settings.json). Hook-urile anti-AI-tone
existente NU sunt afectate.
"""

import json
import os
import sys
from pathlib import Path

SUPPORTED_EXT = {'.md', '.txt', '.docx'}

# Skip unic, partajat. Excludem zgomotul (scratch, cod, arhive, fisiere de proba)
# ca hook-urile sa NU ruleze pe scrierile intermediare ale modelului si pe non-livrabile.
SKIP_PATTERNS = (
    '_archive', '_extracted_', 'node_modules', '.git', 'tool-results', 'memory',
    '_session_audit', '_forensic_stage', '_forensic', '_test_corpus', '_payload',
    'proba_', 'qg_test', 'v_old', 'v_new', '_sp_test', '_watch_test',
    '.claude/scripts', '.claude\\scripts', 'dist/', 'dist\\', 'build/', '.cache',
    'source_pack.md', 'briefing_legislativ',
)


def kill_switch_on() -> bool:
    return os.environ.get('ANTIHALU_OFF', '') in ('1', 'true', 'yes', 'on')


def read_payload():
    """Citeste payload-ul JSON al hook-ului de pe stdin. None la eroare."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return None


def target_path(payload) -> Path | None:
    """Extrage calea fisierului tinta din payload, daca e relevant (eligibil)."""
    if not payload:
        return None
    ti = payload.get('tool_input') or {}
    fp = ti.get('file_path') or ''
    if not fp:
        return None
    p = Path(fp)
    if p.suffix.lower() not in SUPPORTED_EXT:
        return None
    norm = str(p).replace('\\', '/')
    if any(skip.replace('\\', '/') in norm for skip in SKIP_PATTERNS):
        return None
    if not p.exists():
        return None
    return p


def _docx_note(p: Path) -> str:
    """Textul notelor de subsol si de final, care nu trece prin python-docx.

    Intr-un act juridic, aparatul critic sta aproape tot in note: deciziile Curtii cu
    numarul si Monitorul Oficial, actele normative, directivele. python-docx expune doar
    paragrafele din corp, deci un strat care se opreste acolo nu vede tocmai citarile pe
    care e pus sa le pazeasca. Masurat pe excepția de neconstituționalitate din dosarul
    Transcarpat, 30 iulie 2026: 10 citari in corp, 14 in note, 5 dintre ele nicaieri
    altundeva.
    """
    import re as _re
    import zipfile as _zip
    bucati = []
    try:
        with _zip.ZipFile(p) as z:
            for parte in ('word/footnotes.xml', 'word/endnotes.xml'):
                if parte not in z.namelist():
                    continue
                xml = z.read(parte).decode('utf-8', 'replace')
                bucati.extend(_re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, _re.S))
    except Exception:
        return ""
    text = " ".join(bucati)
    for cod, car in (('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                     ('&quot;', '"'), ('&apos;', "'")):
        text = text.replace(cod, car)
    return text


def _docx_corp(p: Path) -> str:
    """Corpul documentului, cu modificarile urmarite ACCEPTATE.

    `python-docx` expune la `Paragraph.text` doar run-urile care sunt copii directi ai
    lui `w:p`. Un run din interiorul unui `w:ins` are ca parinte elementul de revizie,
    deci NU apare. Pe un redline asta inseamna ca tot ce am propus eu e invizibil, iar
    stratul anti-halucinare verifica exact partea pe care nu am scris-o.

    Masurat pe 31 iulie 2026, pe excepția din dosarul Transcarpat: 51.068 de caractere
    citite din 86.878. Lipseau, intre altele, doua decizii ale Curtii Constitutionale,
    o cauza CJUE si doua trimiteri la directiva, toate adaugate de mine ca revizii.

    Se citeste varianta ACCEPTATA, fiindca aceea e propunerea supusa verificarii:
    textul din `w:ins` intra, textul din `w:del` iese. Acelasi motiv ca la
    `_docx_note`, alt punct orb al aceleiasi biblioteci.
    """
    try:
        import zipfile
        from lxml import etree
    except ImportError:
        try:
            from docx import Document
            return "\n".join(par.text for par in Document(str(p)).paragraphs if par.text.strip())
        except Exception:
            return ""
    W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    try:
        with zipfile.ZipFile(p) as z:
            rad = etree.fromstring(z.read('word/document.xml'))
    except Exception:
        return ""
    linii = []
    for par in rad.iter('{%s}p' % W):
        bucati = []
        for r in par.iter('{%s}r' % W):
            parinte = r.getparent()
            if parinte is not None and etree.QName(parinte).localname == 'del':
                continue
            bucati.append("".join((t.text or "") for t in r.iter('{%s}t' % W)))
        linie = "".join(bucati).strip()
        if linie:
            linii.append(linie)
    return "\n".join(linii)


def read_text(p: Path) -> str:
    if p.suffix.lower() == '.docx':
        corp = _docx_corp(p)
        if not corp:
            return ""
        note = _docx_note(p)
        return (corp + "\n" + note) if note else corp
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ""


def eligible(payload, min_words: int):
    """Returneaza (path, text) daca fisierul e eligibil si destul de lung, altfel (None, None).

    Respecta kill-switch-ul. Folosit de toate hook-urile pentru un comportament uniform.
    """
    if kill_switch_on():
        return None, None
    p = target_path(payload)
    if p is None:
        return None, None
    text = read_text(p)
    if not text or len(text.split()) < min_words:
        return None, None
    return p, text
