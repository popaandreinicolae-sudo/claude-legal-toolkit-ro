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
import re
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


# --------------------------------------------------------------------------
# Contractul e actul partilor, nu al cabinetului, si are genul lui.
#
# Cerut de autor pe 25 august 2026, dupa integrarea metodei de redactare in
# skill-ul contracte-ro: stratul anti-AI-tone NU se mai aplica pe text de
# contract. Genul contractual cere tocmai ce penalizeaza stratul, titlu de
# articol urmat de doua puncte, definitii de forma „X inseamna...", enumerari
# si repetarea identica a termenilor definiti. Un termen definit variat de
# dragul scorului nu mai e acelasi termen, iar simetria alineatelor arata
# judecatorului ca doua obligatii au acelasi regim.
#
# Exceptia priveste TEXTUL DE CONTRACT: corpul, clauzele, anexele contractuale,
# actele aditionale. Ce semneaza cabinetul alaturi de contract ramane sub strat,
# adresa de inaintare, opinia, memoriul de revizuire, mesajul catre client.
# De aceea filtrul se uita si dupa semne negative in numele fisierului.
#
# ACESTA E SINGURUL FILTRU. Serverul persona il copiaza cuvant cu cuvant, nu il
# rescrie: pe 25 august existau doua variante timp de cateva ore, iar cea de a
# doua, fara semne negative, scutea tocmai memoriul si opinia.
#
# Numele se sparge in cuvinte, nu se cauta ca subsir. Cautat ca subsir, „nda"
# prindea fondator, suspendare, comanda si standard, iar „nota" prindea notarial.
# --------------------------------------------------------------------------

# Cuvinte intregi, potrivite si cu terminatiile lor: contract, contractul,
# contracte, contractare.
_CONTRACT_CUVINTE = (
    'contract', 'aditional', 'addendum', 'amendment', 'agreement',
    'antecontract', 'promisiune', 'conventie', 'comodat', 'subcomodat',
    'cesiune', 'locatiune', 'inchiriere', 'arenda', 'leasing', 'franciza',
    'subcontract', 'antrepriza', 'subantrepriza', 'tranzactie', 'novatie',
    'fideiusiune', 'clauzier', 'clauze', 'anexa', 'contractual',
)

# Prescurtari, potrivite numai ca si cuvant intreg. Aici nu se accepta
# terminatii: „spa" nu are voie sa prinda „spatiu", „sow" nu are voie sa prinda
# „sowing".
_CONTRACT_ACRONIME = ('nda', 'msa', 'sow', 'dpa', 'spa', 'sla', 'loi', 'mou')

# Perechi de cuvinte care se citesc impreuna.
_CONTRACT_EXPRESII = (' acord cadru ', ' acord de confidentialitate ',
                      ' act aditional ', ' conditii generale ',
                      ' conditii speciale ')

# Numele care arata ca fisierul e text al cabinetului DESPRE un contract, nu
# contractul insusi. Ele anuleaza semnul pozitiv de mai sus. Lista a crescut pe
# 25 august, dupa ce filtrul a scutit 32 de fisiere reale, printre care un
# articol publicat sub numele autorului si un advice catre client.
_CONTRACT_NUME_NEGATIV = (
    'opinie', 'memoriu', 'memo', 'nota', 'note', 'adresa', 'scrisoare', 'mesaj',
    'email', 'raport', 'analiza', 'comentarii', 'observatii', 'matrice',
    'rezumat', 'sinteza', 'instructiuni', 'ghid', 'checklist', 'plan',
    'cerere', 'intampinare', 'concluzii', 'actiune', 'plangere', 'contestatie',
    'sesizare', 'exceptie', 'apel', 'recurs', 'somatie', 'notificare',
    'articol', 'advice', 'comparatie', 'compare', 'comparativ', 'summary',
    'sumar', 'propunere', 'tabel', 'procedura', 'prezentare', 'minuta',
    'brief', 'chestionar', 'grila', 'studiu', 'referat', 'expunere',
    'fundamentare', 'strategie', 'audit', 'due', 'diligence', 'memorandum',
)

# Terminatiile romanesti obisnuite, ca semnul sa se caute pe cuvant intreg.
_SUFIXE = ('', 'a', 'e', 'i', 'ul', 'ului', 'le', 'lor', 'ei', 'ii', 'ile',
           'ilor', 'uri', 'urile', 'urilor', 'are', 'ari', 'arii', 'ul')

_CONTRACT_MARCAJE = (
    # romana
    'prezentul contract', 'prezentul act aditional', 'partile contractante',
    'in calitate de prestator', 'in calitate de beneficiar',
    'in calitate de furnizor', 'in calitate de locator', 'in calitate de locatar',
    'in calitate de comodant', 'in calitate de comodatar', 'in calitate de vanzator',
    'in calitate de cumparator', 'in calitate de antreprenor', 'in calitate de client',
    'partile convin', 'se obliga sa', 'prezentul acord', 'clauze finale',
    'incheiat astazi', 'obiectul contractului', 'durata contractului',
    'incetarea contractului', 'forta majora', 'prezenta conventie',
    'obligatiile partilor', 'legea aplicabila', 'in doua exemplare',
    'partile semnatare', 'denuntare unilaterala', 'rezilierea contractului',
    # engleza. Erau doua din douazeci si doua, la un prag de patru, deci un
    # contract in engleza nu putea fi recunoscut niciodata dupa continut, iar
    # contractul-ancora Geotehnikal, de 10.640 de cuvinte, iesea sub strat.
    'this agreement', 'this contract', 'the parties agree', 'the parties hereto',
    'in witness whereof', 'hereby agree', 'entire agreement', 'governing law',
    'force majeure', 'terms and conditions', 'subject to the terms',
    'shall be entitled', 'the supplier shall', 'the contractor shall',
    'the client shall', 'the customer shall', 'the service provider shall',
    'effective date', 'confidential information', 'termination of this',
    'shall not be liable', 'each party shall', 'duly authorised representatives',
    'duly authorized representatives',
)


def _fara_diacritice(s: str) -> str:
    tabel = str.maketrans('ăâîșşțţĂÂÎȘŞȚŢ', 'aaissttAAISSTT')
    return s.translate(tabel)


def _cuvinte(nume: str) -> list:
    return [t for t in re.split('[^a-z0-9]+', nume) if t]


def _potriveste(token: str, radacini: tuple) -> bool:
    for r in radacini:
        if token == r:
            return True
        if token.startswith(r) and token[len(r):] in _SUFIXE:
            return True
    return False


def e_text_de_contract(p, text: str):
    """Spune daca fisierul e text de contract, deci scutit de stratul anti-AI-tone.

    Intoarce (True, motiv) sau (False, ""). Doua drumuri catre da, numele
    fisierului si continutul, amandoua oprite de un semn negativ in nume.
    """
    nume = _fara_diacritice(Path(p).stem.lower()) if p is not None else ''
    tokenuri = _cuvinte(nume)

    if any(_potriveste(t, _CONTRACT_NUME_NEGATIV) for t in tokenuri):
        return False, ""

    if any(_potriveste(t, _CONTRACT_CUVINTE) for t in tokenuri):
        return True, "numele fisierului"
    if any(t in _CONTRACT_ACRONIME for t in tokenuri):
        return True, "numele fisierului"
    nume_spatiat = ' ' + ' '.join(tokenuri) + ' '
    if any(e in nume_spatiat for e in _CONTRACT_EXPRESII):
        return True, "numele fisierului"

    corp = _fara_diacritice((text or '')[:120000].lower())
    gasite = {m for m in _CONTRACT_MARCAJE if m in corp}
    if len(gasite) >= 4:
        return True, "%d marcaje de contract in text" % len(gasite)
    return False, ""
