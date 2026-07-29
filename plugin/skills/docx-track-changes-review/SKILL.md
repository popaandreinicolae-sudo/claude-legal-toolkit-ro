---
name: docx-track-changes-review
description: >
  Arhitectura si protocol validat pentru review pe documente Word (.docx) cu track changes reale,
  fara ca documentul sa se corupa (blocheze) si fara ca analiza sa se intrerupa la jumatate.
  APLICA AUTOMAT cand utilizatorul cere "revizuieste documentul", "fa track changes", "redline",
  "modificari urmarite", "corecteaza contractul cu track changes", "review pe docx", sau ofera un .docx
  pentru corectura. Se combina cu skill-ul oficial `docx` (unpack/pack/validate/accept_changes) si cu
  `docx-safe-edit`. Livreaza la final un .docx cu redline pe care omul il accepta in Word.
---

# Review pe .docx cu track changes, arhitectura care nu blocheaza documentul

Acest skill este harta de sistem a fluxului care functioneaza si a fost validat in Claude Desktop
Cowork. Explica ce se intampla in spate, in ce ordine, si de ce documentul nu se corupe si analiza nu
se opreste inainte de final. Il folosesti impreuna cu skill-ul oficial `docx`, care aduce scripturile,
si cu `docx-safe-edit`, care aduce plasa de siguranta.

## 1. Ce este de fapt un track change

Un fisier .docx este o arhiva ZIP cu fisiere XML. Modificarile urmarite traiesc in
`word/document.xml`, ca doua elemente:

- `<w:ins>` marcheaza un text inserat,
- `<w:del>` marcheaza un text sters (textul sters sta in `<w:delText>`, nu in `<w:t>`).

Fiecare poarta autor, data si un id:

```xml
<w:ins w:id="1" w:author="Claude" w:date="2026-07-28T00:00:00Z">
  <w:r><w:t>text inserat</w:t></w:r>
</w:ins>
<w:del w:id="2" w:author="Claude" w:date="2026-07-28T00:00:00Z">
  <w:r><w:delText>text sters</w:delText></w:r>
</w:del>
```

Word citeste aceste elemente si le afiseaza ca redline colorat. Cand omul apasa Accept sau Reject in
Word, elementele se rezolva. Nu exista magie, doar XML corect.

## 2. Fluxul de baza: Unpack, Edit, Pack

Regula de aur: **nu regenera documentul de la zero.** Daca il reconstruiesti cu docx-js sau
python-docx, pierzi formatarea, notele de subsol, stilurile si structura. Il despachetezi, editezi doar
XML-ul vizat, il reimpachetezi cu validare. Trei pasi, in ordine.

**Pas 1, despachetare.**
```bash
python scripts/office/unpack.py document.docx unpacked/
```
Extrage XML-ul, il aranjeaza citibil, uneste run-urile adiacente si transforma ghilimelele curbe in
entitati (`&#x201C;`) ca sa supravietuiasca editarii.

**Pas 2, editare.** Editezi fisierele din `unpacked/word/` cu unealta Edit, prin inlocuire de sir. Nu
scrii scripturi Python pentru asta, complica degeaba si ascund ce se schimba. Inlocuiesti blocul
`<w:r>...</w:r>` intreg cu perechea `<w:del>...</w:del><w:ins>...</w:ins>` asezate ca frati, nu bagi
tag-uri de track change in interiorul unui run.

**Pas 3, reimpachetare.**
```bash
python scripts/office/pack.py unpacked/ output.docx --original document.docx
```
Valideaza cu auto-repair, condenseaza XML-ul si scrie .docx-ul final.

## 3. De ce nu se blocheaza documentul

Un document Word "se blocheaza", adica refuza sa se deschida sau anunta continut corupt, atunci cand
XML-ul devine invalid. Poarta care te apara este validarea de la `pack.py`, care ruleaza validatorul
OOXML (`redlining.py`, `docx.py`) contra schemelor ISO-IEC 29500. Un .docx care trece validarea se
deschide in Word. Aici se pierd majoritatea proiectelor facute in graba, fiindcă sar validarea.

Peste asta se aseaza protocolul din `docx-safe-edit`, ca redundanta:

1. Backup inainte de orice modificare, `shutil.copy2('input.docx', 'input_BACKUP.docx')`.
2. Inlocuiesti un singur fisier in ZIP fara sa atingi restul.
3. Nu stergi niciodata `[Content_Types].xml`, nu modifici `word/_rels/`, nu schimbi structura ZIP-ului.
4. Validezi dupa: python-docx deschide fisierul, XML-ul e valid, LibreOffice il converteste in PDF.

## 4. De ce nu se intrerupe analiza

Aici sta partea de orchestrare, nu de cod. Trei lucruri tin review-ul sa mearga pana la capat.

Hook-urile sunt consultative, nu blocheaza. Contractul de sistem spune limpede ca un hook nu modifica
nimic si nu opreste executia, doar scrie un avertisment. Un semnal de la citation_guard sau de la
detectorul de ton nu anuleaza operatia pe document. Daca vrei sa taci complet stratul factual pe durata
unei revizii lungi, ai comutatorul `ANTIHALU_OFF=1`.

Editarile sunt minime. Marchezi doar ce se schimba, nu rescrii paragrafe intregi ca redline. Operatia
ramane mica, atomica, si nu umple documentul cu mii de elemente care ingreuneaza validarea si afisarea.

Lucrezi incremental pe XML despachetat. Mergi paragraf cu paragraf, aplici modificarea, treci mai
departe. Nu tii tot documentul intr-un singur pas fragil care, daca pica, pica tot.

## 5. Protocolul operational, pas cu pas

Aceasta este reteta pe care o rulezi de fiecare data.

**Pas 0, pregatire.** Faci backup si citesti ce e deja in document, inclusiv redline-urile existente:
```bash
pandoc --track-changes=all document.docx -o _citire.md
```

**Pas 1, despachetare.** `unpack.py` (vezi sectiunea 2).

**Pas 2, analiza de fond.** Aici intra skill-urile juridice de continut (`constitutional-law-ro`,
`cyber-law-ro`, `review-contract`, `verificare-citari-gate`). Decizi ce se modifica si de ce, inainte
sa atingi XML-ul.

**Pas 3, aplicarea redline.** Cu unealta Edit, inlocuiesti fiecare `<w:r>` vizat cu `<w:del>` plus
`<w:ins>`, pastrand `<w:rPr>` original ca sa nu pierzi bold, font sau marime. Autor "Claude" sau numele
recenzentului. Pentru stergerea unui paragraf intreg, marchezi si sfarsitul de paragraf ca sters, altfel
ramane un rand gol dupa Accept.

**Pas 4, reimpachetare cu validare.** `pack.py` (vezi sectiunea 2).

**Pas 5, verificare.** Deschizi cu python-docx si convertesti in PDF ca test final de integritate.

**Pas 6, optional, versiunea curata.** Daca ti se cere documentul cu modificarile deja acceptate:
```bash
python scripts/accept_changes.py output.docx output_curat.docx
```
Altfel lasi redline-ul si omul accepta in Word, ceea ce e comportamentul normal la o revizie juridica.

## 6. Prompt gata de folosit in Cowork

Adrian il da in Claude Desktop Cowork impreuna cu documentul lui:

```
Revizuieste documentul atasat [nume.docx] cu track changes reale.
Reguli:
- Foloseste fluxul unpack -> edit XML -> pack din skill-ul docx, NU regenera documentul.
- Marcheaza fiecare modificare ca <w:ins>/<w:del>, autor "[numele meu]", pastreaza formatarea (w:rPr).
- Editari minime, doar ce se schimba. Nu rescrie paragrafe intregi ca redline.
- Fa backup inainte, valideaza dupa (pack cu validare + deschidere test + PDF).
- Nu atinge [Content_Types].xml sau word/_rels/.
- La final livreaza .docx-ul cu redline. NU accepta modificarile automat, le accept eu in Word.
Analiza de fond: [ce vrei revizuit, ex. conformitate cu Legea X, coerenta citarilor, claritate].
```

## 7. Reguli de aur, de ce nu da eroare

1. Nu regenera documentul, editeaza-l despachetat.
2. Inlocuieste blocul `<w:r>` intreg, nu injecta tag-uri de track change in interiorul unui run.
3. Pastreaza `<w:rPr>` in ambele runuri, de inserare si de stergere.
4. In `<w:del>` folosesti `<w:delText>`, nu `<w:t>`.
5. La stergere de paragraf intreg, marcheaza si `<w:del/>` in `<w:pPr><w:rPr>`.
6. Backup inainte, validare dupa. Fara validare, riscul de document blocat e real.
7. Editari minime. Volumul mare de redline ingreuneaza si validarea, si Word-ul.
8. Nu atinge `[Content_Types].xml` si `word/_rels/`.
9. Livreaza redline, nu accepta modificarile decat daca ti se cere explicit.

## 8. Ce ai nevoie instalat

Scripturile vin cu skill-ul oficial `docx`, deja prezent in acest repo la `skills/_official_docx/`.
In plus:

- `pandoc` pentru citirea cu track changes,
- `python-docx` si `lxml` pentru safe-edit si validare (`pip install python-docx lxml`),
- LibreOffice pentru conversia PDF si pentru `accept_changes.py`.
