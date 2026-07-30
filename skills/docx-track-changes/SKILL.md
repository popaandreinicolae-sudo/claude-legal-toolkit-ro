---
name: docx-track-changes
description: |
  Livrarea unui document Word cu modificari urmarite (track changes) native, scrise direct in XML, fara a deschide Word si fara control de desktop. APLICA AUTOMAT ori de cate ori sarcina cere revizuirea, corectarea sau modificarea unui fisier .docx existent care trebuie predat inapoi cu reviziile vizibile. Triggere: "track changes", "modificari urmarite", "cu revizii", "redline", "revizuieste documentul", "corecteaza documentul Word", "modifica .docx", "document formatat identic cu originalul", "sa se vada ce am schimbat", "accept sau resping modificarile", "varianta comparata", "compara cu originalul", "livrabil Word". Interzice explicit preluarea controlului desktopului pentru a edita in Word.
version: 1.0
last_updated: 2026-07-27
---

# Track changes native in .docx

Reviziile Word traiesc ca elemente `<w:ins>` si `<w:del>` in `word/document.xml`. Se scriu
direct in XML. Deschiderea Word-ului prin computer use, cu screenshot-uri si clickuri,
rezolva aceeasi problema mult mai lent, blocheaza ecranul utilizatorului si esueaza la
prima fereastra care apare peste aplicatie.

## Regula

Cand sarcina cere un .docx revizuit, foloseste `scripts/docx_track_changes.py`.
Nu deschide Word. Nu porni computer use. Nu cere permisiune de control al desktopului.

Tool-ul se afla in acest skill:

```
~/.claude/skills/docx-track-changes/scripts/docx_track_changes.py
```

Dependinte: `lxml` si, pentru self-test, `python-docx`. Ambele instalate.

Nu reconstrui documentul de la zero in RTF ca sa obtii revizii. Retiparirea pierde
stilurile, numerotarea automata si notele, transforma numerele de lista in text literal
si produce un redline al carui "original" nu mai e cel real. Editarile pe RTF cer si
potrivire exacta pe secvente de escape, care esueaza tacut. Redlineul se face pe .docx,
peste fisierul original.

## Fluxul in trei pasi

### 1. Citeste documentul cu id-uri stabile

```bash
python ~/.claude/skills/docx-track-changes/scripts/docx_track_changes.py list \
    --input "cale/cerere.docx" --parts document,footnotes
```

Iesirea numeroteaza fiecare paragraf, inclusiv cele din tabele si din notele de subsol:

```
doc:0      [Heading1] Cerere de sesizare a Curtii Constitutionale
doc:1      Subsemnatul, Adrian Zamfir, avocat in Baroul Bucuresti, ...
fn:0        Curtea Constitutionala a Romaniei, Decizia nr. 70/2023, par. 65.
```

Prefixele sunt `doc:` pentru corpul documentului, `fn:` pentru note de subsol,
`en:` pentru note de final.

### 2. Scrie editarile intr-un JSON

Fisierul de editari e livrabilul intermediar. Il salvezi langa document, ca sa ramana
urma a ce s-a schimbat.

```json
{
  "author": "AMZ Law Office",
  "edits": [
    {"op": "replace", "find": "art. 12 din Legea nr. 58/2023",
                      "replace": "art. 12 alin. (2) din Legea nr. 58/2023"},
    {"op": "replace", "find": "termenul", "replace": "termenul de decadere", "all": true},
    {"op": "replace", "part": "footnotes", "find": "par. 65.", "replace": "par. 65-67."},
    {"op": "set_paragraph",    "id": "doc:12", "text": "continutul integral nou al paragrafului"},
    {"op": "insert_after",     "id": "doc:12", "text": "Paragraf nou, adaugat dupa al 12-lea."},
    {"op": "insert_before",    "id": "doc:0",  "text": "Paragraf nou la inceput."},
    {"op": "delete_paragraph", "id": "doc:12"}
  ]
}
```

Reguli pentru `replace`, cea mai folosita operatie. Fara `"all": true` se inlocuieste
doar prima aparitie. Sirul cautat trebuie sa existe in interiorul unui singur paragraf;
un `find` care traverseaza doua paragrafe nu se potriveste. Implicit se cauta in
`document`; pentru note pui `"part": "footnotes"`.

Prefera `replace` cand schimbarea e punctuala si `set_paragraph` cand rescrii fraza
intreaga. `set_paragraph` pastreaza formatarea de paragraf, iar diferentele fata de
textul vechi se calculeaza automat la nivel de cuvant.

### 3. Aplica si verifica

```bash
python ~/.claude/skills/docx-track-changes/scripts/docx_track_changes.py apply \
    --input  "cale/cerere.docx" \
    --output "cale/cerere_revizuit.docx" \
    --edits  "cale/edits.json" \
    --author "AMZ Law Office" \
    --report "cale/raport_revizii.json"

python ~/.claude/skills/docx-track-changes/scripts/docx_track_changes.py verify \
    --input "cale/cerere_revizuit.docx" --detail --strict
```

**Autorul reviziei poarta marca, nu numele avocatului.** Sirul dat prin `--author` ajunge
in fiecare `<w:ins>` si `<w:del>`, deci apare in balonul de revizie pe care il citeste
partea adversa sau clientul. Acolo scrie `AMZ Law Office`, denumirea comerciala sub care
apare public cabinetul. Numele personal ramane in proprietatile fisierului, la
`lastModifiedBy`, care e alt camp si nu se vede in text. Implicitul tool-ului e deja
marca, deci `--author` poate lipsi; il dai explicit numai cand reviziile trebuie sa
poarte alt nume.

`apply` scrie raportul JSON cu numarul de paragrafe modificate, inserate si sterse.
`verify` recitieste fisierul rezultat si listeaza fiecare revizie cu autorul si textul ei,
util pentru a redacta lista de modificari care insoteste livrabilul. Tot el semnaleaza,
in `redline_prea_larg`, marcajele mai late decat modificarea; `--strict` face din ele un
esec, deci verificarea intra intr-un quality gate.

## Note de subsol noi

`docx_track_changes.py` modifica textul notelor existente, prin `"part": "footnotes"`,
dar nu poate crea note noi. O nota noua cere un element `<w:footnote>` in
`word/footnotes.xml` plus un run de referinta in corp. Pentru asta exista un al doilea
tool, rulat DUPA redline:

```bash
python ~/.claude/skills/docx-track-changes/scripts/docx_footnotes.py apply \
    --input  "cale/revizuit.docx" \
    --output "cale/final.docx" \
    --notes  "cale/note.json" \
    --author "AMZ Law Office"
```

Nota se ancoreaza de un fragment de text, nu se strecoara prin diff:

```json
{
  "author": "AMZ Law Office",
  "notes": [
    {"id": "doc:34",
     "after": "viciul de neconstitutionalitate nu poate fi ignorat.",
     "text": "Decizia Curtii Constitutionale nr. 503 din 20 aprilie 2010, publicata in Monitorul Oficial al Romaniei, Partea I, nr. 353 din 28 mai 2010."}
  ]
}
```

Referinta se aseaza imediat dupa ultimul caracter al ancorei. Cand ancora cade in text
inserat, referinta intra in acelasi `<w:ins>`; cand cade in text original, primeste
propriul `<w:ins>`. In ambele cazuri nota apare ca insertie urmarita si dispare la
Reject All. Ancora trebuie sa apara exact o data in paragraf, altfel executia se opreste
fara fisier de iesire, ca peste tot in skill.

Verificarea integritatii, referinte fara nota si note fara referinta:

```bash
python ~/.claude/skills/docx-track-changes/scripts/docx_footnotes.py check --input final.docx
```

De ce ancorare si nu un marcaj de tipul `[[fn:...]]` scris direct in textul editarii:
marcajul se rupe. Motorul de redline compara la nivel de cuvant, iar un spatiu din
interiorul marcajului se aliniaza cu un spatiu din textul original, asa ca marcajul
ajunge taiat in bucati, cu text original prins la mijloc. Stergerea marcajului distruge
atunci un caracter original si Reject All nu mai reproduce documentul de plecare.
Masurat pe caz real, nu presupus.

## Mod alternativ, varianta revizuita ca fisier separat

Cand ai deja documentul rescris integral, sari peste JSON:

```bash
python ~/.claude/skills/docx-track-changes/scripts/docx_track_changes.py apply \
    --input original.docx --output revizuit.docx --revised varianta_noua.docx
```

`--revised` accepta `.docx`, `.txt` sau `.md`, cu un paragraf pe linie la fisierele text.
Alinierea paragrafelor se face prin similaritate, deci mutarile si rescrierile ample sunt
detectate corect. Modul acesta atinge doar corpul documentului, nu si notele de subsol.

## Trei reguli care tin redlineul citibil

**Marcajul acopera cuvantul schimbat, nu fraza din jurul lui.** Cand dintr-o paranteza
e gresit un singur cuvant, se taie acel cuvant. O paranteza intreaga taiata si rescrisa
il pune pe cititor sa parcurga de doua ori acelasi text ca sa gaseasca litera schimbata,
si ascunde modificarea reala intr-un zid rosu.

Regula traieste in cod. Diff-ul lucreaza pe token-uri, deci scrii editarea cum iti vine
mai comod, ca fraza in `find`/`replace` sau ca paragraf intreg in `set_paragraph`, iar
marcajul iese tot pe cuvant. `{"find": "(fiind nelegal pentru aceste aspect)",
"replace": "(fiind nelegal pentru acest aspect)"}` scrie in document exact atat, `aceste`
taiat si `acest` adaugat, cu bold-ul si stilul run-ului original pastrate.

`verify` pazeste celalalt traseu, redlineul scris de mana in XML despachetat, unde
inlocuirea unui `<w:r>` intreg lateste marcajul peste cuvinte nemodificate. Raportul
listeaza in `redline_prea_larg` fiecare pereche care taie si rescrie acelasi cuvant, cu
ce ar fi fost destul sa fie marcat, iar `--strict` intoarce cod de iesire diferit de zero.
Verificat de `selftest.py`, sectiunea [8].


**Impartirea in paragrafe a autorului nu se atinge.** Cand originalul tine un citat
in trei paragrafe, revizuirea il lasa in trei. Comasarea ingreuneaza citirea, schimba
prezentarea sursei si umple redlineul cu un paragraf sters intreg plus unul adaugat
intreg, in locul catorva cuvinte marcate. Rescrii continutul unui paragraf, nu hotarele
dintre ele. Daca o comasare chiar se impune, o propui separat, nu o strecori in redline.

**Diacriticele scrise altfel nu sunt o modificare.** Romana are doua codificari pentru
aceleasi litere, virgula dedesubt (ș U+0219, ț U+021B), forma corecta de azi, si sedila
(ş U+015F, ţ U+0163), forma veche ramasa in bazele de legislatie si jurisprudenta. Un act
care citeaza din ele amesteca ambele scrieri, iar pe ecran arata identic.

Tool-ul le trateaza ca pe aceeasi litera la comparare, prin `fold_echivalente`, deci nu
mai naste revizii pe cuvinte care se citesc la fel, si pastreaza in document grafia din
original, inclusiv in citate. Acelasi tratament primesc spatiul insecabil fata de spatiul
obisnuit si cratima insecabila fata de cratima. Plierea lucreaza NUMAI la comparare;
la scriere nimic nu se normalizeaza.

Masurat pe o exceptie de neconstitutionalitate trecuta printr-o conversie de codificare,
240 din 1270 de marcaje erau cuvinte inlocuite cu ele insele. Verificat de `selftest.py`,
sectiunea [5].

## Cand varianta revizuita vine din alta parte

O varianta scrisa in afara .docx-ului, dintr-un chat, dintr-un PDF sau dintr-o
retiparire, aduce in text ceea ce Word producea singur din formatare. Tool-ul
recunoaste singur doua astfel de cazuri si nu mai naste revizii pentru ele:

1. **numerotarea de lista**, `[12]`, `1.`, `IV.`, `(i)`, `•`. Cand paragraful din
   original are `w:numPr`, numarul vine automat, deci unul scris ca text in varianta
   revizuita se ignora. Altfel ar aparea de doua ori si ar opri Word din a renumerota
   la inserarea unui capitol nou.
2. **majusculele de stil.** Un titlu scris normal si afisat cu majuscule prin
   `w:caps` revine din retiparire integral cu majuscule. Fiecare litera ar iesi
   diferita, iar titlul intreg ar aparea taiat si rescris, cu stilul pierdut, in loc
   de cele doua cuvinte chiar modificate. Comparatia ignora capitalizarea in
   paragrafele afisate cu majuscule, iar in document ramane textul original.

Ce ramane in sarcina ta, fiindcă tool-ul nu are cum sa ghiceasca intentia,
sunt **hotarele de paragraf**, vezi regula de mai sus.

Masurat pe o exceptie de neconstitutionalitate retiparita in RTF, cele trei corecturi
impreuna au scazut reviziile de la 1270 la 803 si paragrafele sterse integral de la 29
la zero, pe acelasi continut revizuit. Verificat de `selftest.py`, sectiunile [5] si [6].

## Ce garanteaza tool-ul

Reject All in Word reproduce byte-identic textul original. Accept All produce exact
varianta ceruta. Formatarea run-urilor, bold, italic, stiluri de caracter, supravietuieste
editarii, inclusiv cand modificarea cade in mijlocul unui run formatat. Referintele de nota
de subsol, imaginile, tabelele si bookmark-urile raman la locul lor. Ambele invariante sunt
verificate de `scripts/selftest.py`.

```bash
python ~/.claude/skills/docx-track-changes/scripts/selftest.py
```

## Verificarea de spatii de nume, in `verify`

`verify` cade cu cod 1 cand atributul `Ignorable` din spatiul Markup Compatibility
enumera un prefix pe care radacina nu il declara. Word refuza atunci fisierul cu mesajul
despre continut ilizibil, desi pachetul e XML valid si toate celelalte verificari trec.
Defectul apare la serializare, cand prefixele originale sunt rebotezate fara ca lista din
`Ignorable` sa fie rescrisa. Verificat pe cazul din 29 iulie 2026. Reparatia:

```bash
python ~/.claude/skills/docx-footnotes/scripts/repara_pachet.py repara --input act.docx
```

## Ce opreste executia

Tool-ul refuza sa scrie fisierul de iesire cand o editare nu se potriveste, si spune care.
Un `find` care nu exista in document, un `id` de paragraf in afara intervalului sau o
operatie necunoscuta intorc cod de iesire diferit de zero si niciun `.docx` nu se creeaza.
Comportamentul e intentionat, in linia protocolului anti-halucinare: mai bine o eroare
explicita decat un document livrat cu o modificare care nu s-a aplicat.

Daca documentul sursa contine deja modificari urmarite, tool-ul avertizeaza pe stderr si
pastreaza reviziile vechi intacte. In cazul asta verifica rezultatul in Word inainte de
livrare.

## Limite cunoscute

Cand un paragraf sters si unul nou stau alaturi, redlineul afiseaza intai paragraful taiat
si apoi pe cel adaugat, conventia obisnuita pentru inlocuiri. Modificarile de formatare
pura, bold adaugat fara schimbare de text, nu se urmaresc, tool-ul urmareste textul.
Antetele si subsolurile nu intra in sfera de aplicare.

## Legatura cu restul sistemului

Trece documentul rezultat prin [quality-gate] si prin `verificare-citari-gate` inainte de
livrare, ca orice document juridic. Reviziile scrise de tool nu ocolesc verificarea
citarilor, ele doar o transporta in .docx.
