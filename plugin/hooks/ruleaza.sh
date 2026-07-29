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
for p in python3 python py; do
  if command -v "$p" >/dev/null 2>&1; then
    exec "$p" "$d/$s" "$@"
  fi
done
exit 0
