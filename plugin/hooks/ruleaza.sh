#!/bin/sh
# Alege interpretorul disponibil. Pachetul ruleaza si pe Windows, unde comanda e
# `python`, si in masina virtuala Cowork, unde e `python3`.
#
# Iesire 0 cand nu gaseste niciunul: stratul anti-halucinare e fail-open prin
# constructie, deci un hook care nu poate rula raporteaza curat in loc sa blocheze
# sesiunea. Vezi hooks/SYSTEM_CONTRACT.md.
d=$(dirname "$0")
s=$1
shift

# Claude Desktop instalat din Microsoft Store e pachet MSIX. ${CLAUDE_PLUGIN_ROOT} arata
# catre AppData\Roaming\Claude, dar fisierele stau efectiv sub
# AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude.
#
# Ordinea de mai jos nu e intamplatoare. `sh` vede calea redirectionata si citeste acest
# script de acolo fara probleme, dar `python.exe`, lansat ca proces nativ in afara
# containerului, primeste acelasi sir si nu gaseste nimic. Verificat pe eroarea reala:
# comanda pornea, iar Python raporta [Errno 2] pe calea din Roaming. Deci calea tradusa
# are prioritate, chiar daca testul pe cea primita ar trece.
#
# Cand aplicatia reuseste sa puna plugin-ul pe calea scurta din Temp, prin symlink,
# tiparul nu se potriveste, traducerea nu schimba nimic si ramane calea primita.
alt=$(printf '%s' "$d" | sed 's#[Aa]pp[Dd]ata[/\\][Rr]oaming[/\\][Cc]laude[/\\]#AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/#')
if [ -f "$alt/$s" ]; then
  d=$alt
elif [ ! -f "$d/$s" ]; then
  # Scriptul nu exista nicaieri, deci nu avem ce rula. Iesire curata, fara zgomot.
  exit 0
fi

for p in python3 python py; do
  if command -v "$p" >/dev/null 2>&1; then
    exec "$p" "$d/$s" "$@"
  fi
done
exit 0
