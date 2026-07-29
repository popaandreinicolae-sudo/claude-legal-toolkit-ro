# Checklist Fact-Check Pre-Livrare

Aplica acest checklist inainte de livrarea oricarui document profesional.

## A. Cifre, sume, procente

- [ ] Fiecare cifra (numar absolut, suma, procent) are sursa citata sau marcaj [ESTIMARE] / [NEVERIFICAT].
- [ ] Cifrele rotunde (44, 100, 1000, 30%) sunt verificat rotunde, nu inventate pentru efect.
- [ ] Sumele in EUR plus RON sunt actualizate la cursul mentionat explicit.
- [ ] Procentele sunt validate cu numitor explicit (procent din ce).
- [ ] Indicatori tip BCR, NPV, EIRR au metoda de calcul descrisa, nu doar cifra.

## B. Denumiri institutionale si autori

- [ ] Fiecare institutie are denumirea oficiala completa la prima aparitie.
- [ ] Acronimele sunt definite in lista dedicata.
- [ ] Autorii au nume si prenume complete confirmate.
- [ ] Atribuirile de opinie sunt verificabile (autor, lucrare, an).

## C. Acte normative si jurisprudenta

- [ ] Fiecare lege, OUG, HG, ordin are numar plus an plus M.Of. citat.
- [ ] Fiecare decizie CCR are numar plus an plus paragraf citat.
- [ ] Fiecare hotarare CEDO are numar cerere plus data hotarare.
- [ ] Fiecare cauza CJUE are CELEX plus ECLI.
- [ ] Actele citate sunt in vigoare la data documentului (verificare prin MCP).

## D. Capitole si anexe

- [ ] Niciun capitol nu este lasat gol (slot filler).
- [ ] Numerotarea capitolelor este consecutiva (X, XI, XII, fara gap).
- [ ] Sub-sectiunile respecta numerotarea capitolului (12.1 pentru cap. XII).
- [ ] Anexele citate in text exista efectiv ca anexe.
- [ ] Anexele cu tabele comparative au sursa pentru fiecare cifra.

## E. Scenarii si proiectii

- [ ] Scenarii alternative (BAU, Strategy, Ambitious) au marcaj [SCENARIU].
- [ ] Cifrele scenariilor au ipoteze explicite mentionate.
- [ ] Proiectiile pana in 2030, 2050 etc. sunt construite cu metode descrise.
- [ ] Indicatori de risc tip "raport beneficiu-cost 3,5" au calcul detaliat.

## F. Structura raport final

- [ ] Sectiunea "Surse citate" exista la final.
- [ ] Lista bibliografica este completa si verificabila.
- [ ] Lista [NEVERIFICAT] cu sugestii de verificare este inclusa.
- [ ] Notele de subsol sunt numerotate consecutiv.

## G. Coerenta intre versiuni

- [ ] Comparativa cu versiunea anterioara (daca exista) prin script compare_docx_versions.py.
- [ ] Diferente cantitative justificate (cifre noi cu surse noi).
- [ ] Capitole noi sau eliminate documentate in changelog.

## H. Verificare finala

- [ ] Subagent fact-checker-document a rulat pe versiunea finala.
- [ ] Toate problemele critice sunt rezolvate sau marcate explicit.
- [ ] Document trimis spre review extern doar dupa fact-check intern.
