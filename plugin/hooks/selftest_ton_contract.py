#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest_ton_contract.py

Proba exceptiei cerute de autor pe 25 august 2026: stratul anti-AI-tone nu se mai
aplica pe text de contract, dar ramane intreg pe actele semnate de cabinet.

Se verifica trei lucruri, fiindca regula scrisa doar in proza nu tine:
  1. filtrul din hook_common.e_text_de_contract clasifica corect numele si continutul;
  2. ai_tone_hook.py sare peste contract si continua sa semnaleze un memoriu prost scris;
  3. quality_gate.py raporteaza tonul ca sarit pe contract si il masoara in rest.

Se lucreaza pe fisiere construite aici, intr-un director temporar, ca proba sa treaca
pe orice masina si sa nu atinga niciun dosar de client.

    python selftest_ton_contract.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

AICI = Path(__file__).resolve().parent
sys.path.insert(0, str(AICI))

HOOK = AICI / "ai_tone_hook.py"
POARTA = AICI / "quality_gate.py"

CONTRACT = """CONTRACT DE PRESTARI SERVICII

Incheiat astazi, [*], intre partile contractante:

Art. 1 - Obiectul contractului: Prestatorul se obliga sa execute lucrarile din Anexa 1.
Art. 2 - Pretul: Pretul este ferm si se factureaza lunar, pe situatii de lucrari acceptate.
Art. 3 - Termenul: Termenul de executie este de [*] zile lucratoare de la comanda ferma.
Art. 4 - Receptia: Receptia cantitativa se face la predare, cea calitativa in zece zile.
Art. 5 - Raspunderea: Prestatorul raspunde pentru neexecutare, Beneficiarul pentru plata.
Art. 6 - Forta majora: Forta majora exonereaza partea care o invoca si o dovedeste.
Art. 7 - Durata contractului: Durata contractului este de un an de la data semnarii.
Art. 8 - Incetarea contractului: Incetarea contractului opereaza prin acordul scris.
Art. 9 - Notificari: Notificarile se comunica in scris, la adresele din preambul.
Art. 10 - Legea aplicabila: Legea aplicabila este legea romana.

Partile convin ca prezentul contract reprezinta acordul integral dintre ele. Prestatorul,
in calitate de prestator, si Beneficiarul, in calitate de beneficiar, declara ca au
capacitatea juridica de a incheia prezentul contract. Partile convin ca modificarea se
face numai prin inscris semnat de amandoua. Clauze finale: prezentul contract s-a incheiat
in doua exemplare originale. Prestatorul se obliga sa predea documentele justificative
odata cu factura. Beneficiarul se obliga sa achite pretul la scadenta convenita. Prezentul
acord inlocuieste orice intelegere anterioara dintre parti privitoare la acelasi obiect.
"""

CONTRACT_EN = """CONSULTANCY AGREEMENT

This Agreement is made between the parties hereto on the effective date set out below.

1. Scope of Services. The Contractor shall perform the investigations, design and project
supervision services described in Annex 1. The Client shall provide access to the site.
2. Fees. The fees are set out in Annex 2 and shall be invoiced monthly.
3. Governing law. This contract shall be governed by the laws of Romania.
4. Force majeure. Neither party shall be liable for any failure caused by force majeure.
5. Confidential information shall not be disclosed to any third party.
6. Termination of this Agreement may be effected upon thirty days written notice.
7. Entire agreement. This Agreement constitutes the entire agreement between the parties
and supersedes all prior arrangements, subject to the terms set out herein.

In witness whereof the parties hereto have caused this Agreement to be executed by their
duly authorised representatives. The parties agree that each party shall bear its own costs.
"""

MEMORIU = ("# Memoriu de revizuire\n\n"
           + "\n".join("- **Punct %d:** descrierea problemei gasite in clauza analizata." % i
                       for i in range(1, 12))
           + "\n\nNu este vorba de o simpla eroare de redactare, ci de o problema de fond. " * 6
           + "\nIn concluzie, se poate afirma ca este important de mentionat ca analiza de "
             "mai sus, in mod evident, sustine concluzia formulata. " * 6)

esecuri: list[str] = []


def verifica(conditie: bool, descriere: str) -> None:
    print(("  OK   " if conditie else "  ESEC ") + descriere)
    if not conditie:
        esecuri.append(descriere)


def ruleaza_hook(cale: Path) -> str:
    payload = json.dumps({"tool_input": {"file_path": str(cale)}})
    res = subprocess.run([sys.executable, str(HOOK)], input=payload,
                         capture_output=True, text=True, timeout=60, encoding="utf-8")
    return (res.stderr or "")


def main() -> int:
    from hook_common import e_text_de_contract

    print("1. filtrul de clasificare")
    cazuri_da = [
        ("Contract de prestari servicii AQUAVAS.docx", ""),
        ("Contract vanzare autentificat notarial.docx", ""),
        ("Act aditional nr. 3.docx", ""),
        ("CG_Tech_Labs-MSA-Master_Services_Agreement_rev.AZ_v3.docx", ""),
        ("NDA mutual revAZ.docx", ""),
        ("Acord cadru recrutare NEO AR.docx", ""),
        ("Contract comodat_Calea Domneasca nr. 53.docx", ""),
        ("Draft fara nume lamuritor.docx", CONTRACT),
        # Contractul in engleza trebuie sa treaca pe drumul continutului, fara
        # ajutorul numelui. Inainte de 25 august erau doua marcaje englezesti din
        # douazeci si doua, la un prag de patru, deci nu putea trece niciodata, iar
        # contractul-ancora Geotehnikal, de 10.640 de cuvinte, iesea sub strat.
        ("BG02 - 17.09.2025_rev_1_GeotehnikalS_revAZ.docx", CONTRACT_EN),
        ("fisier fara nume lamuritor.docx", CONTRACT_EN),
    ]
    cazuri_nu = [
        ("Memoriu de revizuire contract Electrogrup.docx", ""),
        ("Adresa de inaintare contract DSV.docx", ""),
        ("Opinia noastra pe clauza de neconcurenta.docx", ""),
        ("Matricea de completitudine DSV.md", ""),
        ("Notele scrise Transcarpat.docx", ""),
        ("Raport doctoral capitolul II.md", "text academic despre proportionalitate"),
        # Produsul cabinetului DESPRE un contract ramane sub strat. Cazuri reale,
        # din harta modelelor: pe 25 august filtrul scutea 32 de fisiere de felul
        # asta, printre care un articol publicat sub numele autorului.
        ("Articol Adrian-Mihai Zamfir & Adrian Cristea_Contractul de consultanta imobiliara.docx", ""),
        ("Advice catre Porsche ref. forta majora si impreviziune in contract de locatiune.docx", ""),
        ("Contract - Aquavas - comparatie.docx", ""),
        ("Consulting Agreement Profi vs Template_compare.docx", ""),
        # Cuvinte care contineau, ca subsir, o prescurtare din lista pozitiva:
        # „nda" statea in fondator, suspendare, comanda si standard.
        ("Fondator declaratie.docx", ""),
        ("Act de suspendare executare.docx", ""),
        ("Comanda ferma 4512.docx", ""),
        ("Standard operating notes.docx", ""),
    ]
    for nume, corp in cazuri_da:
        ok, _ = e_text_de_contract(Path(nume), corp)
        verifica(ok, "text de contract: %s" % nume)
    for nume, corp in cazuri_nu:
        ok, _ = e_text_de_contract(Path(nume), corp)
        verifica(not ok, "act al cabinetului: %s" % nume)

    with tempfile.TemporaryDirectory(prefix="ton_contract_") as td:
        d = Path(td)
        c = d / "Contract de prestari servicii proba.md"
        m = d / "Memoriu de revizuire proba.md"
        c.write_text(CONTRACT, encoding="utf-8")
        m.write_text(MEMORIU, encoding="utf-8")

        print("2. hook-ul PostToolUse")
        out_c = ruleaza_hook(c)
        verifica("sarit, text de contract" in out_c,
                 "contractul e sarit, cu motivul spus")
        verifica("scor naturalete" not in out_c,
                 "contractul nu primeste scor de naturalete")
        out_m = ruleaza_hook(m)
        verifica("scor naturalete" in out_m,
                 "memoriul prost scris e in continuare semnalat")

        print("3. poarta de calitate")
        res = subprocess.run([sys.executable, str(POARTA), str(c)],
                             capture_output=True, text=True, timeout=120, encoding="utf-8")
        verifica("ton sarit (text de contract" in (res.stdout or ""),
                 "poarta raporteaza tonul ca sarit pe contract")
        res = subprocess.run([sys.executable, str(POARTA), str(m)],
                             capture_output=True, text=True, timeout=120, encoding="utf-8")
        verifica("/100" in (res.stdout or ""),
                 "poarta masoara in continuare tonul pe memoriu")

    print()
    if esecuri:
        print("ESUAT: %d verificari" % len(esecuri))
        for e in esecuri:
            print("  - " + e)
        return 1
    print("TOATE VERIFICARILE AU TRECUT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
