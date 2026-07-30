#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regresie pentru hook-ul care opreste suprascrierea documentelor.

Cazul care l-a facut necesar: o comanda de copiere peste un .docx din dosarul cauzei, care
a distrus o ora de munca a autorului pe 30 iulie 2026. Testul verifica atat oprirea, cat
si cele trei situatii in care hook-ul trebuie sa lase lucrurile sa treaca, fiindca un
strat care blocheaza si munca legitima se dezactiveaza si nu mai apara nimic.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "fara_suprascriere.py"


def ruleaza(unealta, intrare):
    p = subprocess.run([sys.executable, str(HOOK)],
                       input=json.dumps({"tool_name": unealta, "tool_input": intrare}),
                       capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def main() -> int:
    rele = 0
    # Dinadins in afara dosarelor temporare: acolo hook-ul lasa liber, fiindca
    # regenerarea peste acelasi nume e chiar scopul unui dosar de lucru.
    radacina = Path.home() / "_proba-suprascriere"
    try:
        dosar = radacina / "Dosar"
        dosar.mkdir(parents=True, exist_ok=True)
        act = dosar / "exceptie.docx"
        act.write_text("documentul autorului")
        cod = dosar / "build.py"
        cod.write_text("# cod")
        nou = dosar / "act_nou.docx"

        cazuri = [
            ("copiere peste un .docx existent", "Bash",
             {"command": 'cp final.docx "%s"' % act}, True),
            ("copiere catre un nume liber", "Bash",
             {"command": 'cp final.docx "%s"' % nou}, False),
            ("mutare peste un .docx existent", "Bash",
             {"command": 'mv gata.docx "%s"' % act}, True),
            ("Copy-Item peste un .docx existent", "PowerShell",
             {"command": 'Copy-Item final.docx "%s"' % act}, True),
            ("Write peste un .docx existent", "Write",
             {"file_path": str(act), "content": "x"}, True),
            ("Write peste un .py existent", "Write",
             {"file_path": str(cod), "content": "x"}, False),
            ("copiere cu --suprascrie cerut expres", "Bash",
             {"command": 'cp --suprascrie final.docx "%s"' % act}, False),
            ("copiere intr-un dosar temporar", "Bash",
             {"command": 'cp a.docx "C:/Users/X/AppData/Local/Temp/scratchpad/a.docx"'}, False),
            ("citire, nu scriere", "Bash",
             {"command": 'python verifica.py "%s"' % act}, False),
        ]

        for eticheta, unealta, intrare, trebuie_oprit in cazuri:
            cod_iesire, mesaj = ruleaza(unealta, intrare)
            oprit = cod_iesire == 2
            ok = oprit == trebuie_oprit
            if not ok:
                rele += 1
            print("  %s %-42s oprit=%s" % ("ok    " if ok else "GRESIT", eticheta, oprit))
            if oprit and "_v2" not in mesaj and trebuie_oprit:
                rele += 1
                print("         mesajul nu propune o cale libera")

        # numerotarea creste, nu refoloseste
        (dosar / "exceptie_v2.docx").write_text("x")
        _, mesaj = ruleaza("Bash", {"command": 'cp f.docx "%s"' % act})
        if "_v3" not in mesaj:
            rele += 1
            print("  GRESIT numerotarea nu a trecut la v3: %s" % mesaj[-90:])
        else:
            print("  ok     numerotarea trece la v3 cand v2 exista")

    finally:
        shutil.rmtree(radacina, ignore_errors=True)

    print()
    print("REZULTAT: %s" % ("toate cazurile trec" if not rele else "%d probleme" % rele))
    return 1 if rele else 0


if __name__ == "__main__":
    sys.exit(main())
