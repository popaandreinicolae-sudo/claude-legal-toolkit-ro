#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_redline.py

Proba stratului care tine regula "orice versiune noua vine insotita de redline".

Acopera cele doua piese deterministe, hook-ul redline_obligatoriu.py, care semnaleaza
versiunea plecata fara redline, si redline_automat.py, care il produce singur la salvare.
Piesele de pe cealalta suprafata, poarta de activare si docx_redline din serverul persona,
au proba lor in depozitul personei.

Se lucreaza pe documente construite aici, nu pe acte reale: proba trebuie sa treaca pe
orice masina si sa nu atinga niciun dosar de client.

    python selftest_redline.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

AICI = Path(__file__).resolve().parent
HOOK = AICI / "redline_obligatoriu.py"
SCRIPTURI = Path.home() / ".claude" / "skills" / "docx-footnotes" / "scripts"
if not SCRIPTURI.exists():
    SCRIPTURI = AICI.parent / "skills" / "docx-footnotes" / "scripts"

cazuri_cazute = []


def verdict(eticheta: str, trecut: bool, detaliu: str = "") -> None:
    print("  [%s] %s%s" % ("ok " if trecut else "CAZUT", eticheta,
                           ("  <- " + detaliu) if detaliu and not trecut else ""))
    if not trecut:
        cazuri_cazute.append(eticheta)


def scrie_docx(cale: Path, paragrafe: list) -> Path:
    from docx import Document  # noqa: PLC0415
    d = Document()
    for p in paragrafe:
        d.add_paragraph(p)
    cale.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(cale))
    os.utime(cale, (time.time(), time.time()))
    return cale


def are_revizii(cale: Path) -> bool:
    with zipfile.ZipFile(cale) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    return "<w:ins " in xml or "<w:del " in xml


def cheama_hook(payload: dict) -> int:
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode


TEXT_VECHI = [
    "Subscrisa, prin avocat, formulam prezentele cereri si exceptii.",
    "In temeiul art. 342 C.proc.pen., invocam nelegalitatea actelor de urmarire penala.",
    "Solicitam constatarea nulitatii absolute a procesului-verbal.",
]
TEXT_NOU = [
    "Subscrisa, prin avocat, formulam prezentele cereri si exceptii.",
    "In temeiul art. 342 si urmatoarele C.proc.pen., invocam nelegalitatea actelor de "
    "urmarire penala.",
    "Solicitam constatarea nulitatii absolute a procesului-verbal de cercetare la fata "
    "locului.",
]


def proba_automat(lucru: Path) -> None:
    print("\n== redline_automat, stratul care produce ==")
    sys.path.insert(0, str(SCRIPTURI))
    try:
        import redline_automat as ra  # noqa: PLC0415
    except ImportError as e:
        verdict("modulul se incarca", False, str(e))
        return

    dosar = lucru / "automat"
    vechi = scrie_docx(dosar / "act.docx", TEXT_VECHI)
    nou = scrie_docx(dosar / "act_v2.docx", TEXT_NOU)

    verdict("precedentul lui act_v2 e act.docx",
            (ra.precedent(nou) or Path("-")).name == "act.docx")
    verdict("primul act nu are precedent", ra.precedent(vechi) is None)

    rez = ra.produ(nou, tacut=True)
    verdict("redline-ul se produce", bool(rez))
    if not rez:
        return
    iesire = Path(rez["redline"])
    verdict("fisierul de redline exista", iesire.exists())
    verdict("poarta <w:ins> sau <w:del>", iesire.exists() and are_revizii(iesire))
    verdict("comparatia s-a facut fata de versiunea precedenta",
            Path(rez["vechi"]).name == "act.docx")

    # A doua rulare nu are voie sa atinga fisierul deja scris.
    inainte = iesire.stat().st_mtime
    rez2 = ra.produ(nou, tacut=True)
    verdict("a doua rulare scrie alaturi, nu peste",
            bool(rez2) and Path(rez2["redline"]) != iesire
            and iesire.stat().st_mtime == inainte)

    verdict("redline-ul nu se compara cu el insusi", ra.produ(iesire, tacut=True) is None)


def proba_hook(lucru: Path) -> None:
    print("\n== redline_obligatoriu, stratul care semnaleaza ==")
    dosar = lucru / "hook"
    vechi = scrie_docx(dosar / "act.docx", TEXT_VECHI)
    nou = scrie_docx(dosar / "act_v2.docx", TEXT_NOU)

    def payload_write(cale: Path) -> dict:
        return {"tool_name": "Write", "tool_input": {"file_path": str(cale)},
                "cwd": str(dosar)}

    verdict("versiunea noua fara redline e semnalata", cheama_hook(payload_write(nou)) == 2)
    verdict("primul act din serie nu e semnalat", cheama_hook(payload_write(vechi)) == 0)

    sys.path.insert(0, str(SCRIPTURI))
    import redline_automat as ra  # noqa: PLC0415
    rez = ra.produ(nou, tacut=True)
    if rez:
        os.utime(nou, (time.time(), time.time()))
        os.utime(Path(rez["redline"]), (time.time(), time.time()))
        verdict("dupa ce redline-ul exista, tace", cheama_hook(payload_write(nou)) == 0)
        verdict("fisierul de redline insusi nu e semnalat",
                cheama_hook(payload_write(Path(rez["redline"]))) == 0)

    # Livrarea prin copiere, drumul pe care nu e implicat niciun script al nostru.
    livrat = dosar / "livrat"
    scrie_docx(livrat / "dosar.docx", TEXT_VECHI)
    tinta = scrie_docx(livrat / "dosar_v2.docx", TEXT_NOU)
    cod = cheama_hook({"tool_name": "PowerShell",
                       "tool_input": {"command": 'Copy-Item "gata.docx" "%s"' % tinta},
                       "cwd": str(dosar)})
    verdict("livrarea prin copiere e prinsa", cod == 2)

    # Un document care poarta deja revizii este el insusi redline, sub alt nume.
    if rez:
        deja = livrat / "altul_v2.docx"
        shutil.copyfile(rez["redline"], deja)
        scrie_docx(livrat / "altul.docx", TEXT_VECHI)
        os.utime(deja, (time.time(), time.time()))
        verdict("documentul cu revizii nu e semnalat", cheama_hook(payload_write(deja)) == 0)

    mediu = dict(os.environ, REDLINE_OBLIGATORIU_OFF="1")
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload_write(tinta)),
                       capture_output=True, text=True, encoding="utf-8", env=mediu)
    verdict("comutatorul REDLINE_OBLIGATORIU_OFF opreste totul", p.returncode == 0)

    p2 = subprocess.run([sys.executable, str(HOOK)], input="nu e json",
                        capture_output=True, text=True, encoding="utf-8")
    verdict("intrarea stricata nu darama hook-ul", p2.returncode == 0)


def main() -> int:
    print("PROBA STRATULUI DE REDLINE")
    lucru = Path(tempfile.mkdtemp(prefix="selftest_redline_"))
    try:
        proba_automat(lucru)
        proba_hook(lucru)
    finally:
        shutil.rmtree(lucru, ignore_errors=True)

    print("\n" + "=" * 60)
    if cazuri_cazute:
        print("CAZUT: " + ", ".join(cazuri_cazute))
        return 1
    print("REZULTAT: versiunea noua nu mai poate pleca fara redline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
