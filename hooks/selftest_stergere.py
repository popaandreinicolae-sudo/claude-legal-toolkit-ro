"""Proba pe hook-ul de suprascriere, partea de stergere. Nu sterge nimic, doar trimite
comenzi la hook si citeste verdictul."""
import json, subprocess, sys

HOOK = r"C:\Users\Adrian Zamfir\claude-legal-toolkit-ro\hooks\fara_suprascriere.py"
PY = sys.executable

CAZURI = [
    # (eticheta, unealta, comanda, trebuie_oprit)
    ("comanda care a distrus documentele, forma cu conducta", "PowerShell",
     'Get-ChildItem "D:\\Clienti\\RBF Outdoor Adventures\\MODIFICARE STATUT" -Filter "2026 07 30_*" '
     '| ForEach-Object { Remove-Item $_.FullName -Force }', True),
    ("stergere cu cale literala de document", "PowerShell",
     'Remove-Item "D:\\Clienti\\RBF Outdoor Adventures\\MODIFICARE STATUT\\statut.docx" -Force', True),
    ("rm din bash pe un act", "Bash",
     'rm "/d/Clienti/RBF Outdoor Adventures/MODIFICARE STATUT/statut.docx"', True),
    ("del pe un pdf din dosar", "PowerShell",
     'del "D:\\Clienti\\X\\anexa.pdf"', True),
    ("stergere in masa fara cale, dar in dosarele autorului", "PowerShell",
     'Get-ChildItem "D:\\Clienti\\X" -Recurse | Remove-Item', True),
    ("-Force nu mai e portita", "PowerShell",
     'Remove-Item "D:\\Clienti\\X\\act.docx" -Force -Recurse', True),
    ("stergere confirmata de autor, trece", "PowerShell",
     'Remove-Item "D:\\Clienti\\X\\act.docx"  # --sterge-confirmat', False),
    ("curatenie in scratchpad, trece", "PowerShell",
     'Remove-Item "C:\\Users\\X\\AppData\\Local\\Temp\\claude\\scratchpad\\proba.docx"', False),
    ("stergere de cod, trece", "Bash",
     'rm /c/Users/X/claude-legal-toolkit-ro/hooks/vechi.py', False),
    ("comanda fara verb de stergere, trece", "PowerShell",
     'Get-ChildItem "D:\\Clienti\\X" -Filter *.docx', False),
    ("cuvant care contine rm, nu e verb, trece", "Bash",
     'echo "termen" > /tmp/x.txt', False),
    ("del din sintaxa Python intr-un python -c, nu e stergere", "Bash",
     'python -c "corp = [1,2,3]; del corp[0]; print(corp)" && echo gata "D:\\Clienti\\X\\a.docx"', False),
    ("copiere peste un act existent, oprita de vechea regula", "PowerShell",
     'Copy-Item nou.docx "D:\\Clienti\\X\\act.docx"', None),
]

pica = 0
for eticheta, unealta, cmd, asteptat in CAZURI:
    intrare = json.dumps({"tool_name": unealta, "tool_input": {"command": cmd}})
    r = subprocess.run([PY, HOOK], input=intrare, capture_output=True, text=True)
    oprit = r.returncode == 2
    if asteptat is None:
        print(f"  [info] {eticheta}: oprit={oprit}")
        continue
    ok = oprit == asteptat
    if not ok:
        pica += 1
    print(f"  [{'OK  ' if ok else 'FAIL'}] {eticheta}: oprit={oprit}, asteptat={asteptat}")
    if oprit and ok and asteptat:
        print("         " + (r.stderr.strip().splitlines() or [""])[0][:100])

print()
if pica:
    print(f"PICAT: {pica} cazuri")
    sys.exit(1)
print("TRECUT: stergerile de documente sunt oprite, curatenia in temp merge mai departe.")
