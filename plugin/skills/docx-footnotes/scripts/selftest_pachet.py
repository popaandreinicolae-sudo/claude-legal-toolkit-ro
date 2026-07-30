#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_pachet.py

Regresie pentru defectele care il fac pe Word sa refuze un .docx generat programatic.

Amandoua sunt din aceeasi familie, un prefix pomenit undeva unde niciun parser nu il
verifica, si amandoua au ajuns la client inainte de a fi prinse:

  29 iulie 2026, mc:Ignorable din word/document.xml enumera prefixe pe care radacina nu
  le declara. Reparat atunci, dar verificarea a ramas limitata la partile din word/.

  30 iulie 2026, docProps/core.xml scrie datele ca ns2:created cu xsi:type="dcterms:W3CDTF".
  Prefixul dcterms nu era declarat nicaieri, iar Word cere si sa fie scris exact asa, nu
  doar declarat. Fiindca verificarea nu se uita in docProps, defectul a supravietuit in
  sablonul de casa si a mers mai departe in fiecare document generat din el. Word le
  deschidea numai dupa promptul de reparare, deci defectul arata ca o ciudatenie a lui
  Word, nu ca o eroare de generare.

Testul lucreaza pe pachete construite in memorie, deci nu cere Word instalat si merge la
fel pe orice masina.

    python selftest_pachet.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repara_pachet as rp  # noqa: E402

CORE_RUPT = (
    "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n"
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
    ' xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ns2="http://purl.org/dc/terms/"'
    ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:creator>Adrian Zamfir</dc:creator>"
    '<ns2:created xsi:type="dcterms:W3CDTF">2022-06-21T08:42:00Z</ns2:created>'
    '<ns2:modified xsi:type="dcterms:W3CDTF">2026-05-26T11:47:00Z</ns2:modified>'
    "</cp:coreProperties>"
)

CORE_BUN = CORE_RUPT.replace('xmlns:ns2="', 'xmlns:dcterms="').replace("ns2:", "dcterms:")

DOC_RUPT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
    ' mc:Ignorable="w14 w15"><w:body><w:p/></w:body></w:document>'
)

DOC_BUN = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
    ' xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"'
    ' xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"'
    ' mc:Ignorable="w14 w15"><w:body><w:p/></w:body></w:document>'
)


def pachet(cale: Path, core: str, doc: str):
    with zipfile.ZipFile(cale, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("docProps/core.xml", core)
        z.writestr("word/document.xml", doc)
        # Parte scrisa corect, din care reparatia isi ia URI-urile prefixelor lipsa.
        z.writestr("word/settings.xml", DOC_BUN.replace("w:document", "w:settings")
                   .replace("<w:body><w:p/></w:body>", ""))


CAZURI = [
    ("core.xml cu prefix rebotezat", CORE_RUPT, DOC_BUN, True),
    ("core.xml scris corect", CORE_BUN, DOC_BUN, False),
    ("Ignorable cu prefixe nedeclarate", CORE_BUN, DOC_RUPT, True),
    ("amandoua rupte", CORE_RUPT, DOC_RUPT, True),
    ("pachet curat", CORE_BUN, DOC_BUN, False),
]


def main() -> int:
    import tempfile
    rele = 0
    with tempfile.TemporaryDirectory() as tmp:
        for eticheta, core, doc, trebuie_semnalat in CAZURI:
            cale = Path(tmp) / "proba.docx"
            pachet(cale, core, doc)
            probleme = rp.verifica(cale)
            semnalat = bool(probleme)
            ok = semnalat == trebuie_semnalat
            stare = "ok    " if ok else "GRESIT"
            if not ok:
                rele += 1
            print("  %s %-34s semnalat=%s" % (stare, eticheta, semnalat))

            if trebuie_semnalat:
                rp.repara(cale, backup=False)
                ramase = rp.verifica(cale)
                if ramase:
                    rele += 1
                    print("         reparatia nu a rezolvat: %s" % ramase[0][:90])
                else:
                    print("         reparat curat")

    print()
    if rele:
        print("REZULTAT: %d probleme" % rele)
        return 1
    print("REZULTAT: ambele familii de defecte sunt prinse si reparate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
