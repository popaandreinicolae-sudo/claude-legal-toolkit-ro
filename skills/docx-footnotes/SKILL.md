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

## Cum se construieste

Nu porni de la un document gol si nu reconstrui formatul din parametri. Pleaca de la
sablon.

`assets/sablon-casa.docx` este un act real al cabinetului, golit de continut de
`tools/build_sablon.py`. Pornind de la el, formatul vine intreg prin constructie, cele
115 definitii de stil, numerotarea pe niveluri, tema cu paleta ei, relatiile dintre
sectiune si anteturi.

Motivul e o lectie platita. Prima varianta reconstruia totul din valori masurate si
suna corect, dar a pierdut `w:titlePg`, deci logo-ul se repeta pe fiecare pagina in loc
sa apara doar pe prima. Un .docx poarta mai mult decat se poate masura si rescrie.

Ruleaza generatorul:

```bash
python "$HOME/.claude/skills/docx-footnotes/scripts/creeaza_document.py" \
    --output "cale/act.docx" --titlu "CERERE DE CHEMARE IN JUDECATA"
```

`--fara-antet` pentru un document care nu poarta antetul cabinetului. `--academic`
pentru formatul Scolii Doctorale UB Drept. Abia dupa aceea scrii continutul in fisierul
rezultat, cu python-docx.

## Calea sigura, continutul dat scriptului

Cand ai de scris un act intreg, nu construi paragrafele de mana. Scrie continutul intr-un
fisier JSON, cu rolul fiecarui bloc, si lasa scriptul sa aplice forma:

```bash
python "$HOME/.claude/skills/docx-footnotes/scripts/scrie_document.py" \
    --continut act.json --output "cale/cerere.docx"
```

Structura fisierului sta scrisa in antetul scriptului. Pe scurt, `instanta`, `reclamant`,
`parti`, `titlu`, `obiect`, `corp`, `final`. Fiecare element din `corp` poate fi text
simplu, sau un obiect cu `bold` pentru fragmentele de evidentiat, `{"tip": "marcator"}`
pentru enumerari si `{"tip": "titlu"}` pentru titluri de sectiune.

Asa nu mai poti gresi stilul, numerotarea sau bold-ul. Tu scrii dreptul, scriptul pune
forma. Sectiunea urmatoare ramane pentru cazurile in care scrii direct cu python-docx.

## Cum se scrie continutul, stilurile de aplicat

Sablonul aduce recipientul. Daca scrii apoi cu `add_paragraph(text)` si
`add_heading(text)`, iese un document care are marginile corecte si structura altcuiva.
Stilurile trebuie aplicate explicit.

Masurat pe cele 86 de acte proprii, 7660 de paragrafe cu text:

| Stil | Pondere | Pentru ce |
|---|---|---|
| `Bodycunrdeparagraf` | 56% | corpul actului, paragraful numerotat |
| `(Normal)` | 25% | antetul de adresare, identificarea partilor, obiectul |
| `ListParagraph` | 7% | enumerari in interiorul unui paragraf |
| `Parties` | 1% | blocul „in contradictoriu cu", cu numerotare proprie |
| `Recitals` | 1% | considerente, in acte de tip conventie |
| `Heading1` sau `TITLE1` | 2% | titlul actului si titlurile de sectiune |

Scrii asa:

```python
doc.add_paragraph("CATRE: TRIBUNALUL ...", style="Normal").runs[0].bold = True
doc.add_paragraph("In contradictoriu cu", style="Parties")
doc.add_paragraph("cerere de chemare in judecata", style="Heading1")
p = doc.add_paragraph("Prin avizul negativ ...", style="Bodycunrdeparagraf")
```

**Numerotarea corpului nu se scrie in text.** Paragrafele de corp o primesc din `w:numPr`,
deci niciodata „1.", „2." tastate. 61% din paragrafele proprii sunt numerotate automat.

**Capetele de cerere fac excepatie.** Acolo numarul se scrie chiar in text, pe stilul
simplu. Masurat pe actele proprii, 18 din 18 capete de cerere au numarul tastat si
niciunul nu e numerotat automat. Motivul e practic: petitul se citeaza in dispozitiv si
in corespondenta, deci numarul trebuie sa se copieze impreuna cu textul.

**Bold-ul e des si intentionat.** 53% din paragrafele proprii contin cel putin un pasaj
bold, termenii definiti, denumirile partilor, temeiurile invocate. Un act fara bold nu
seamana cu ale tale.

## Structura unei cereri de chemare in judecata

Ordinea masurata pe actele proprii de acest tip:

1. instanta si sectia, `Normal`, bold;
2. identificarea reclamantului cu domiciliul, `Normal`, bold;
3. domiciliul procesual ales, `Normal`, bold;
4. blocul partilor, `Parties`, numerotat, cu paratul in bold;
5. denumirea actului, `Heading1`;
6. obiectul cererii, `Normal`, bold;
7. corpul, `Bodycunrdeparagraf`, numerotat automat, cu bold pe termenii cheie.

## Antetul si subsolul

**Antetul apare numai pe prima pagina.** Toate cele 86 de acte proprii poarta `w:titlePg`,
iar referinta de antet e de tip `first` in 84 dintre ele, fara antet implicit. Subsolul,
in schimb, apare pe toate paginile, cu referinte `first` si `default`.

Antetul poarta logo-ul cabinetului, latime 15,96 cm, aliniat stanga, la 1,96 cm de
marginea de sus. Apare in 82 din 84 de acte proprii cu antet. Vine din sablon, nu se
insereaza de mana.

Pentru un document intern, fara logo, foloseste `--fara-antet`. Scoate numai referinta
catre antet; subsolul si asezarea in pagina raman neatinse.

Subsolul scrie „Pagina N din M", aliniat dreapta, Georgia 7,5 pt, la 0,71 cm de
marginea de jos. Numerele vin din campurile `PAGE` si `NUMPAGES`, nu scrise ca text,
altfel raman blocate la prima pagina. 94% din actele proprii au subsol, iar toate cele
cu subsol poarta numerotarea acolo.

## Titlurile

Vin din sablon, deci nu le configura. Masurat pe definitiile de stil din cele 86 de acte
proprii, `Heading1` poarta culoarea `#590056` in 98% dintre ele, cu majuscule aplicate
prin `w:caps`. `TITLE1`, `Heading2` si `Heading3` nu au culoare proprie si mostenesc.

Bleumarinul `#244061` apare des in titluri, dar ca formatare directa pe run, nu ca
definitie de stil. De aceea nu se seteaza; vine din text acolo unde e nevoie.

Majusculele stau in stil, nu scrise in text. Cine copiaza titlul primeste forma
originala, iar un redline nu marcheaza diferenta de capitalizare ca modificare.

## Numerotarea

Se face automat, prin `w:numPr`, niciodata scrisa ca text in paragraf. Un numar tastat
se strica la prima insertie si apare ca modificare intr-un redline, desi cititorul vede
acelasi lucru.

Schema masurata pe acte proprii merge pe trei niveluri, marcator pe nivelul intai,
litera mica urmata de punct pe al doilea, cifra romana mica pe al treilea. Pentru
structura juridica numerotata se foloseste `decimal` cu tiparul `%1.` pe primul nivel.

## Stilul de casa, masurat

Valorile de mai jos vin din cele 86 de documente cu corpul Georgia, adica actele
proprii, separate de cele primite pe sabloane straine. Distinctia conteaza: pe intreg
corpusul de 136 titlurile pareau Arial in 53% din cazuri, dar corelatia arata ca Arial
venea numai din documentele cu alt font de corp. In actele proprii titlul e Georgia.

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
| Antet | logo AMZ, 15,96 cm latime, la 1,96 cm de sus | 86% au antet, 82 din 84 cu logo |
| Subsol | „Pagina N din M", dreapta, Georgia 7,5 pt | 94% au subsol, 72% cu acest tipar |
| Titluri | Georgia 13 pt, bold, majuscule, centrate | 59% marimea, 71% centrarea |
| Culoare titluri | `#244061` | 58%, urmata de `#1F497D` cu 31% |
| Numerotare | automata, prin `w:numPr` | fara exceptie in actele proprii |

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

## Capcana care ucide livrarea, spatiile de nume

Word raspunde „Word found unreadable content" si refuza sa deschida fisierul cand
atributul `Ignorable` din spatiul Markup Compatibility enumera un prefix pe care
radacina nu il declara. Pachetul e XML valid, se deschide fara reproa in python-docx,
trece validarea de structura si verificarea de format. Word nu il arata.

Lectia e platita. Pe 29 iulie 2026 o excepție de neconstituționalitate a plecat catre
client si nu s-a deschis. Cauza: `assets/sablon-casa.docx` fusese serializat cu lxml,
care a rebotezat prefixele originale in `ns1`, `ns2`, `ns3`, fara sa rescrie lista din
`Ignorable`. Cele zece prefixe de acolo, `w14 w15 w16se w16cid w16 w16cex w16sdtdh
w16sdtfl w16du wp14`, nu mai erau declarate nicaieri. Defectul statea in
`word/document.xml` si in `word/numbering.xml`, deci il moștenea fiecare document
generat din sablon.

Sablonul e reparat, iar copia de dinainte sta alaturi,
`sablon-casa.inainte-de-reparatie-20260730.docx`. Verificarea si reparatia stau in
`scripts/repara_pachet.py`:

```bash
python scripts/repara_pachet.py verifica --input act.docx
python scripts/repara_pachet.py repara  --input act.docx
```

`scrie_document.py` si `creeaza_document.py` cheama `repara_pachet.asigura()` dupa
fiecare salvare, deci un document generat de ele nu mai poate pleca rupt. Verificarea
nu se sare nici cand sablonul e curat, fiindca serializarea poate reintroduce defectul
oricand.

Aceeasi verificare blocheaza in `docx-livrare-check` si in `docx_track_changes.py
verify`. Pe suprafetele care nu pot rula scripturi de skill, adica in Claude Desktop,
cheama instrumentul `docx_verifica_pachet` din serverul MCP `persona-adrian-zamfir`.

Regula: orice .docx produs programatic trece prin verificarea de spatii de nume inainte
de a fi trimis. Nicio alta verificare nu prinde defectul acesta.

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

## Unde scrii fisierul

Cand lucrezi intr-un mediu izolat, cum e Cowork, fisierele scrise in directorul de
lucru al sesiunii nu pot fi deschise din afara lui. Aplicatia ofera un buton „Open in
Word", dar Word ruleaza ca proces nativ pe gazda si primeste o cale pe care nu o vede,
deci raspunde „File access was denied".

Scrie livrabilul intr-un folder montat de pe gazda. In Cowork, Desktop-ul utilizatorului
apare ca `/mnt/Desktop`. Verifica intai ce e montat, cu `ls /mnt`, si alege de acolo.

Pe suprafata Claude Code regula nu se aplica, fiindca acolo scrii direct pe disc.

## Reguli

1. Documentul se scrie in romana. Engleza intra numai cand o ceri pentru documentul
   respectiv.
2. Actele complexe se scriu in paragrafe mari si dezvoltate, nu in liste schematice.
3. Fara emoji si fara marcaje decorative.
4. Daca documentul urmeaza sa plece ca redline, tracked changes raman in el. Regula
   „elimina tracked changes inainte de livrare" se aplica numai documentelor livrate
   curat.
5. Verifica deschiderea inainte de livrare, cu `docx-livrare-check`.
6. Niciun .docx generat programatic nu pleaca fara verificarea de spatii de nume.
   Formatul poate fi impecabil si Word sa refuze totusi fisierul.
