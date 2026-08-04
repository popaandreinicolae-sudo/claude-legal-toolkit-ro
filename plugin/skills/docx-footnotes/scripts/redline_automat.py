#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
redline_automat.py

Produce singur documentul cu modificari urmarite cand o versiune noua se aseaza langa una
existenta.

De ce exista
------------
Regula autorului, scrisa in caiet pe 2 august 2026: orice versiune noua vine insotita de
redline, fara exceptie, si nu doar la documentele primite de la el, ci si intre versiunile
mele succesive. A doua zi la 19:54 a plecat oricum un v2 fara redline. Regula era scrisa,
dar nimic nu o executa.

Straturile de deasupra spun regula, campul `instructions` al serverului persona, poarta de
activare din server/poarta.py si hook-ul redline_obligatoriu.py. Stratul asta o face, si
lucreaza chiar si cand niciun model nu a citit nicio instructiune.

Familia unui document
---------------------
Se ia de la cale_libera, ca sa nu existe doua intelesuri ale aceluiasi nume in acelasi
skill. "act.docx" si "act_v2.docx" sunt aceeasi familie, "act_v2_redline_AMZ.docx" e alta,
deci redline-urile nu ajung sa fie comparate intre ele.

Fail-open: cand unealta de comparare lipseste sau cade, salvarea ramane buna si se spune
la stderr ce nu s-a putut face. Un act livrat fara redline deranjeaza; un act nesalvat
fiindca redline-ul a esuat ar fi mai rau.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cale_libera import _desparte, cale_libera

AUTOR_REVIZII = "AMZ Law Office"


def _unealta() -> Path | None:
    """docx_track_changes.py, cautat langa skill si apoi in instalarea din ~/.claude."""
    candidate = [
        Path(__file__).resolve().parents[2] / "docx-track-changes" / "scripts"
        / "docx_track_changes.py",
        Path.home() / ".claude" / "skills" / "docx-track-changes" / "scripts"
        / "docx_track_changes.py",
    ]
    for c in candidate:
        if c.exists():
            return c
    return None


def precedent(nou) -> Path | None:
    """Versiunea anterioara din aceeasi familie, cea mai mare sub numarul lui `nou`."""
    nou = Path(nou)
    inainte, nr, dupa = _desparte(nou.stem)
    gasite = []
    for vecin in nou.parent.glob("*%s" % nou.suffix):
        if vecin.resolve() == nou.resolve() or not vecin.is_file():
            continue
        i2, nr2, d2 = _desparte(vecin.stem)
        if i2 == inainte and d2 == dupa and nr2 < nr:
            gasite.append((nr2, vecin))
    if not gasite:
        return None
    return max(gasite)[1]


def produ(nou, vechi=None, autor: str = AUTOR_REVIZII, tacut: bool = False) -> dict | None:
    """Scrie redline-ul intre versiunea precedenta si `nou`. None cand nu se aplica."""
    nou = Path(nou)
    vechi = Path(vechi) if vechi else precedent(nou)
    if vechi is None or not vechi.exists():
        return None

    script = _unealta()
    if script is None:
        if not tacut:
            sys.stderr.write(
                "  redline nefacut: skill-ul docx-track-changes nu e instalat\n")
        return None

    iesire = cale_libera(nou.with_name("%s_redline_AMZ%s" % (nou.stem, nou.suffix)),
                         tacut=True)
    p = subprocess.run(
        [sys.executable, str(script), "apply", "--input", str(vechi),
         "--revised", str(nou), "--output", str(iesire), "--author", autor],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if p.returncode != 0:
        if not tacut:
            sys.stderr.write("  redline nefacut: %s\n"
                             % (p.stderr or p.stdout or "").strip()[:400])
        return None

    try:
        raport = json.loads(p.stdout)
    except ValueError:
        raport = {}

    # Unealta de comparare scrie reviziile peste pachetul versiunii vechi, fiindca asta
    # cere un redline: ce se respinge trebuie sa reproduca originalul. In consecinta,
    # fisierul poarta forma veche, cu marginile, stilurile si anteturile ei. Cand
    # versiunea noua schimba tocmai forma, redline-ul arata ca si cum nimic nu s-ar fi
    # facut. Pe 4 august 2026 autorul a deschis redline-ul in locul actului si a vazut
    # documentul fara antet, fara numerotare si cu alineatul vechi.
    atinse = raport.get("stats", {}).get("changed_paragraphs")
    nota = ("Redline-ul poarta forma versiunii vechi, fiindca peste pachetul ei se scriu "
            "reviziile. Livrabilul e versiunea noua, nu el.")
    if atinse == 0:
        nota += (" Aici niciun paragraf cu text nu s-a schimbat, deci nu are ce arata; "
                 "ce s-a schimbat tine de forma, care nu se vede in reviziile de text.")
    if not tacut:
        sys.stderr.write(
            "  redline fata de %s: %s (%s revizii, %s paragrafe atinse)\n  %s\n"
            % (vechi.name, iesire.name, raport.get("revisions_written", "?"),
               atinse if atinse is not None else "?", nota))
    return {"redline": str(iesire), "vechi": str(vechi), "raport": raport, "nota": nota}


def adauga_optiune(parser):
    """Adauga --fara-redline, pentru cazurile in care chiar nu se vrea."""
    parser.add_argument(
        "--fara-redline", action="store_true", dest="fara_redline",
        help="nu produce documentul cu modificari urmarite fata de versiunea precedenta")
    return parser


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Utilizare: python redline_automat.py <versiune_noua.docx>")
    rez = produ(sys.argv[1])
    print(json.dumps(rez or {"redline": None, "motiv": "nu exista versiune precedenta"},
                     ensure_ascii=False, indent=1))
