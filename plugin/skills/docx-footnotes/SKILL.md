---
name: docx-footnotes
description: >
  Genereaza un document Word nou, de la zero, in stilul de casa al cabinetului, cu note
  de subsol corecte. Declanseaza la "genereaza docx", "creaza document word", "fa-mi un
  document", "docx cu note de subsol", "livrare docx", "pune-l in Word", "act nou in Word".
  NU se aplica pe un document primit sau existent, acolo lucreaza docx-track-changes.
---

# Generare .docx in stilul de casa

## Cand se aplica

Acest skill acopera documentul scris de la zero. Pe un document care exista deja,
primit de la client, de la partea adversa sau scris anterior, nu se aplica nimic de
aici, fiindca generarea din nou pierde formatarea, notele si structura originalului.
Acolo lucreaza `docx-track-changes` pentru text si `docx-safe-edit` ca plasa de
siguranta.

Notele de subsol noi adaugate intr-un document existent au propriul instrument,
`~/.claude/skills/docx-track-changes/scripts/docx_footnotes.py`, care le introduce ca
revizii urmarite si isi ia marimea fontului din documentul gazda. Nu reimplementa
inserarea de note peste el.

## Stilul de casa, masurat

Valorile de mai jos vin din 136 de documente .docx proprii, ponderate dupa cate
caractere poarta fiecare setare. Procentul arata cat de dominanta este valoarea in
corpus, deci cat de sigur poti sa o aplici fara sa intrebi.

| Element | Valoare | Dominanta |
|---|---|---|
| Font, corp si note | Georgia | 82% din caractere, 84% din impliciturile documentelor |
| Marime corp | 10 pt | 43%, urmata de 11 pt cu 13% |
| Aliniere | justified | 95% |
| Interlinie | cel putin 14 pt (`w:line="280"`, `w:lineRule="atLeast"`) | 40%, plus 14,7 pt cu 33% |
| Spatiu inainte de paragraf | 6 pt | 56% |
| Spatiu dupa paragraf | 6 pt | 44% |
| Alineat prima linie | 1,27 cm | 49%, plus 1,25 cm cu 22% |
| Margine sus | 2 cm | 73% |
| Margine jos | 0,71 cm | 74% |
| Margine stanga | 3,5 cm | 74% |
| Margine dreapta | 1,5 cm | 72% |
| Note de subsol | Georgia 8 pt | 97% fontul, 66% marimea |

Interlinia „cel putin" conteaza. Word o trateaza altfel decat interlinia exacta,
fiindca lasa randul sa creasca atunci cand un caracter mai inalt sau un indice o cer,
in loc sa il taie. Documentele tale o folosesc in 70% din paragrafe, deci pastreaz-o.

Marginea de jos de 0,71 cm si cea din stanga de 3,5 cm sunt semnatura vizuala a
actelor tale. Nu le inlocui cu valorile simetrice obisnuite decat daca ceri asta
explicit pentru un document anume.

## Implementare

```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(0.71)
    section.left_margin = Cm(3.5)
    section.right_margin = Cm(1.5)

normal = doc.styles["Normal"]
normal.font.name = "Georgia"
normal.font.size = Pt(10)

pf = normal.paragraph_format
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.first_line_indent = Cm(1.27)
pf.space_before = Pt(6)
pf.space_after = Pt(6)
pf.line_spacing = Pt(14)                          # scrie lineRule="exact"
pf.line_spacing_rule = WD_LINE_SPACING.AT_LEAST   # il corecteaza in "atLeast"
```

Ordinea ultimelor doua linii nu e optionala. `line_spacing` cu o valoare de tip
lungime scrie `w:lineRule="exact"`, iar randul se taie cand un caracter depaseste
14 pt. Suprascrierea regulii imediat dupa pastreaza inaltimea si schimba doar
comportamentul.

Pentru diacriticele romanesti, Georgia le acopera complet, cu virgula dedesubt la
ș si ț. Daca fontul lipseste de pe masina care deschide documentul, Word cade pe un
substitut, asa ca declara-l si pentru scriptul est-european:

```python
from docx.oxml.ns import qn
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Georgia")
normal.element.rPr.rFonts.set(qn("w:cs"), "Georgia")
```

## Note de subsol

python-docx nu are API nativ pentru note de subsol. Ai doua cai, dupa ce urmeaza sa
faci cu documentul.

Cand documentul pleaca curat, fara redline, construieste `word/footnotes.xml` direct,
cu Georgia 8 pt pe textul notei. Cand documentul urmeaza sa fie revizuit, scrie intai
corpul si adauga notele pe urma, cu scriptul `docx_footnotes.py`, care le marcheaza ca
insertii urmarite.

Referinta din corp ramane superscript automat, iar textul notei se aliniaza justified,
cu interlinie simpla, fara alineat de prima linie.

## Metadate

Documentul generat de la zero primeste numele tau la ambele campuri.

```python
core = doc.core_properties
core.author = "Adrian Zamfir"
core.last_modified_by = "Adrian Zamfir"
```

Nu scrie un numar de revizii. Un `revision` inventat falsifica istoricul de editare al
fisierului, iar campul nu aduce nimic documentului.

Pe un document primit, regula se schimba, vezi `docx-safe-edit`. Autorul original ramane
al lui, se schimba numai `last_modified_by`.

## Format academic, la cerere

Pentru un articol de revista sau o lucrare care cere formatul Scolii Doctorale UB Drept,
stilul de casa se lasa deoparte si se aplica Times New Roman 12 pt corp, 10 pt note,
14 pt titluri de capitol, interlinie 1,5, margini de 2,5 cm sus si jos, 3 cm stanga,
2 cm dreapta. Citarile se fac dupa skill-ul `ub-drept-citation`. Treci pe formatul asta
numai cand documentul chiar merge la o revista sau la facultate, nu implicit.

## Reguli

1. Documentul se scrie in romana. Engleza intra numai cand o ceri pentru documentul
   respectiv.
2. Actele complexe se scriu in paragrafe mari si dezvoltate, nu in liste schematice.
3. Fara emoji si fara marcaje decorative.
4. Daca documentul urmeaza sa plece ca redline, tracked changes raman in el. Regula
   „elimina tracked changes inainte de livrare" se aplica numai documentelor livrate
   curat.
5. Verifica deschiderea inainte de livrare, cu `docx-livrare-check`.
