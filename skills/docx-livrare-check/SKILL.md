---
name: docx-livrare-check
description: >
  Verifica fisierul .docx inainte sa plece, pe format, metadate si sanatate tehnica.
  Declanseaza la "verifica docx-ul", "gata de trimis", "check fisierul Word", "verifica
  formatul documentului", "ce a ramas in document", "controleaza .docx-ul". Se uita la
  fisier, nu la continut. Citarile, cifrele si tonul le verifica subagentul quality-gate.
---

# Control pe fisierul .docx inainte de trimitere

## Ce acopera si ce nu

Aici se verifica obiectul care pleaca, adica fisierul. Fontul, marimea, marginile,
cine apare scris in proprietati, ce a ramas in el pe langa text, daca se deschide.

Continutul are alta poarta. Citarile inventate sau abrogate, sursele-fantoma, erorile
numerice si tonul artificial le prinde subagentul `quality-gate`, care ruleaza
`quality_gate.py` si cheama reviewerii. Cele doua nu se suprapun si nu se inlocuiesc.
Pe un act care pleaca la instanta le vrei pe amandoua, intai continutul, apoi fisierul.

## Cum se ruleaza

```bash
python "$HOME/.claude/skills/docx-livrare-check/scripts/check_livrare.py" act.docx
```

Trei comutatoare schimba ce inseamna „corect".

`--redline` spune ca reviziile urmarite sunt livrabilul. Fara el, orice revizie ramasa
in document opreste trimiterea, ceea ce e corect pentru un act depus si gresit pentru
un contract intors cu marcaje.

`--academic` compara cu formatul Scolii Doctorale UB Drept, Times New Roman 12, margini
simetrice, in loc de stilul de casa. Se foloseste doar cand documentul chiar merge la o
revista sau la facultate.

`--json` intoarce raportul structurat, pentru cand rulezi verificarea dintr-un lant.

Codul de iesire e 0 cand nu exista probleme blocante si 1 cand exista, deci poate fi
pus intr-un lant care se opreste singur.

## 1. Format

Se compara cu stilul de casa masurat pe 136 de acte proprii, ponderat dupa cate
caractere poarta fiecare setare.

| Element | Stil de casa |
|---|---|
| Font corp si note | Georgia |
| Marime corp | 10 pt |
| Aliniere | justified |
| Interlinie | cel putin 14 pt, `lineRule="atLeast"` |
| Spatiu inainte si dupa paragraf | 6 pt |
| Alineat prima linie | 1,27 cm |
| Margini | 2 cm sus, 0,71 cm jos, 3,5 cm stanga, 1,5 cm dreapta |
| Note de subsol | Georgia 8 pt |

Abaterile de format ies ca avertismente, nu ca blocante. Un act primit pe alt sablon,
sau unul depus la un dosar care cere alt format, ramane valabil. Verificarea iti spune
ca documentul nu arata ca restul actelor tale, tu decizi daca asta conteaza pe cazul
respectiv.

Cand fontul apare ca `(mostenit)`, documentul nu il declara nici in `docDefaults`, nici
pe stilul Normal, nici pe run-uri. Word il afiseaza atunci cu implicitul masinii care il
deschide, deci pe alt calculator poate arata altfel. Merita declarat inainte de
trimitere.

## 2. Metadate

Doua nume diferite traiesc in acelasi document si nu trebuie confundate.

`lastModifiedBy`, din proprietatile fisierului, poarta numele avocatului, Adrian Zamfir.
Nu se vede in text, se citeste doar cine deschide proprietatile. Verificarea blocheaza
trimiterea cand acolo apare numele altcuiva, ceea ce prinde cazul in care documentul
pleaca mai departe purtand scris cine l-a atins ultimul la celalalt cabinet, la client
sau la partea adversa.

Autorul reviziilor urmarite, din `<w:ins>` si `<w:del>`, poarta marca, `AMZ Law Office`.
El se vede in fiecare balon de revizie din Word, deci ajunge sub ochii partii adverse.
Verificarea avertizeaza cand o revizie e semnata cu numele personal in loc de marca.

Numele tau apare in Word in mai multe forme, dupa profilul masinii, „Adrian Zamfir",
„Zamfir Mihai-Adrian", „Adrian-Mihai Zamfir". Verificarea le accepta pe toate, fiindca
se uita la cuvinte, nu la sirul exact.

Campul `author` se trateaza altfel. Pe un document primit ramane al celui care l-a
creat, fiindca proprietatile spun cine a facut documentul, nu cine l-a atins ultimul.
Cand acolo apare alt nume, verificarea da un avertisment si iti lasa decizia, fiindca
din fisier nu se poate distinge documentul chiar primit de actul tau scris peste un
sablon mostenit de la alt cabinet. Al doilea caz cere schimbarea.

Se mai raporteaza comentariile ramase, care blocheaza, plus proprietatile personalizate
si caile de fisier ramase in `docProps`, care avertizeaza. Campurile de tip
`ContentTypeId` sau `DISdUser` vin din sistemul de management documentar al altui
cabinet si spun de unde a plecat sablonul.

Caracterele invizibile, ZWSP, ZWNJ, ZWJ, BOM si cratima moale, blocheaza. Ele strica
cautarea in text si apar la copierea din pagini web sau din PDF.

Nu se scrie niciun numar de revizii. Un `revision` fabricat falsifica istoricul de
editare al fisierului.

## 3. Test tehnic

Se verifica prezenta partilor obligatorii din arhiva, integritatea ZIP-ului, numarul de
paragrafe cu text si numarul de note. Notele goale blocheaza, la fel referintele de
nota care trimit catre o nota inexistenta, fiindca amandoua se vad in Word ca document
stricat.

## Ordinea la livrare

1. `quality-gate` pe continut, verdict GO sau NO-GO.
2. Redactarea sau redline-ul se termina, cu `docx-track-changes`.
3. `docx-livrare-check` pe fisier, cu `--redline` daca marcajele raman.
4. Documentul pleaca.
