# Fixturi

## sablon-rupt-20260730.docx

Sablonul de casa in forma de dinainte de reparatia din 30 iulie 2026. Il pastram anume
rupt, ca fixtura de regresie.

Defectul: in `word/document.xml` si in `word/numbering.xml`, atributul `Ignorable` din
spatiul Markup Compatibility enumera zece prefixe, `w14 w15 w16se w16cid w16 w16cex
w16sdtdh w16sdtfl w16du wp14`, pe care radacina nu le declara. Word raspunde „Word found
unreadable content" si refuza fisierul, desi pachetul e XML valid, se deschide fara
reproa in python-docx si trece orice verificare de format.

Cauza: `tools/build_sablon.py` serializa cu `xml.etree.ElementTree`, care inregistra doar
prefixul `w` si inventa `ns1`, `ns2`, `ns3` pentru restul. Valoarea din `Ignorable` e un
simplu sir de text, deci ramanea scrisa cu numele vechi. Reparat prin
`inregistreaza_prefixele()`, care citeste declaratiile din radacina bruta si le
inregistreaza pe toate inainte de serializare.

Foloseste fixtura ca sa verifici ca detectia chiar prinde defectul:

```bash
python ../../skills/docx-footnotes/scripts/repara_pachet.py verifica --input sablon-rupt-20260730.docx
# trebuie sa iasa cu cod 1 si sa listeze ambele parti

python ../build_plugin.py    # trebuie sa refuze arhivarea daca un astfel de fisier ajunge in pachet
```

Nu o repara si nu o muta in `assets/`. Rostul ei e sa ramana rupta.
