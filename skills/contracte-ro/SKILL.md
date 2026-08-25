---
name: contracte-ro
description: >
  Harta contractelor casei si metoda de lucru pe orice sarcina de contract: redactare
  noua, revizuire pe document primit, opinie pe clauze, comparare cu modelul, act
  aditional. Se sprijina pe inventarul contractelor proprii (nivel A, formularile casei)
  si al contractelor tertilor din dosare (nivel B, referinta de practica), si pe metoda
  de redactare a cabinetului, adica operatiunea economica inaintea denumirii, partea
  reprezentata, testul litigiului si controlul dinainte de livrare. Declanseaza la
  "contract", "revizuieste contractul", "fa-mi un contract", "act aditional", "clauza",
  "ce clauze lipsesc", "matrice de completitudine", "MSA", "SOW", "NDA", "DPA",
  "comodat", "cesiune", "inchiriere", "locatiune", "arenda", "leasing", "imprumut",
  "fideiusiune", "antrepriza", "subantrepriza", "executie lucrari", "vanzare-cumparare",
  "SPA", "furnizare", "acord-cadru", "distributie", "franciza", "novatie", "tranzactie",
  "reziliere", "incetare", "forta majora", "raspundere contractuala", "garantie",
  "penalitati", "confidentialitate", "buy-back". NU acopera actele asociatiilor
  (asociatii-ro), mecanica livrarii cu track changes (docx-track-changes) si nici
  procedura de atribuire din achizitiile publice; skill-ul decide CE se scrie, nu CUM
  se livreaza.
---

# Harta contractelor si metoda casei

Scopul, in cuvintele autorului: informatie la care se apeleaza cand lucram pe contracte,
nu un sablon rigid. Modulul are patru referinte, fiecare cu treaba ei:

- `references/harta-modelelor.md`, harta completa, cu doua niveluri: A, modelele si
  revizuirile proprii (~290, sursa de formulari ale casei), si B, contractele tertilor
  din dosare (referinta de practica, niciodata formulari ale casei).
- `references/familii.md`, etalonul fiecarei familii si golurile ei.
- `references/metoda-redactarii.md`, CUM se scrie clauza: operatiunea economica, partea
  reprezentata, testul litigiului, stilul, precizia, nivelul de interventie.
- `references/structura-contractului.md`, ordinea implicita a contractului si matricea de
  completitudine.
- `references/control-inainte-de-livrare.md`, cele cinci controale pe text, plus
  `references/capcane.md` pentru capcanele de proces.

## Prima intrebare, inainte de orice

Familia contractului si sarcina. Familia decide ce modele se deschid; formularea unui
plafon de raspundere din antrepriza nu se transplanteaza intr-o inchiriere. Sarcina
decide fluxul: redactare noua, revizuire pe document primit sau opinie pe clauze.
Inventarul de TEME calatoreste intre familii ca lista de completitudine; FORMULAREA se
preia numai inauntrul familiei din care s-a nascut.

Denumirea contractului nu decide continutul lui. Contractul se construieste din
operatiunea economica reala, iar cele cincisprezece intrebari de la punctul 1 din
`metoda-redactarii.md` se pun inainte de prima fraza. Cand autorul spune pe cine
reprezentam, redactarea se face din perspectiva acelei parti.

## Fluxul de lucru

1. Incadreaza: familia si sarcina, cu intrebarile de mai sus, plus operatiunea economica
   si partea reprezentata.
2. Deschide `references/familii.md`, ia etalonul familiei si modelele vecine din harta.
   Cand familia e subtire, adauga referintele de nivel B indicate acolo, cu provenienta
   spusa.
3. Citeste modelele INTEGRAL, regula generala a casei. Pe un document primit spre
   revizuire, citeste-l intai pe el, tot integral, inainte de orice afirmatie despre el.
4. La revizuire, inainte de primul redline, livreaza autorului MATRICEA DE
   COMPLETITUDINE, adica lista din `references/structura-contractului.md` parcursa tema
   cu tema, cu starea fiecareia in documentul primit (acoperita, acoperita partial,
   lipsa), pusa langa ce acopera modelele noastre bune ale familiei. Matricea pleaca la
   autor si abia dupa ce o vede se trece la redline. Impreuna cu ea merge si triajul pe
   trei categorii, probleme juridice, comerciale si de redactare, in ordinea prioritatii.
5. Clauza noua porneste de la formularea din modelul propriu al familiei, nu din
   memoria modelului AI. Cand familia nu are model propriu, spune-o si lucreaza pe
   referinta B, marcata ca atare. Scrisul urmeaza `references/metoda-redactarii.md`.
6. Verifica modelul contra legii, in doua feluri diferite. Intai pe fond, clauza cu
   clauza, contra legii de azi luate de pe sintact, si intreg chiar cand legea a stat
   pe loc, fiindca modelul poate fi viciat din nastere. Apoi pe timp, in istoricul de
   consolidare, fiindca fiecare model poarta anul lui si un model din 2020 descrie
   legea din 2020. Clauzele expuse sunt penalitatile, dobanda legala, prelucrarea de
   date, insolventa, consumatorii, plafoanele si termenele.
7. Ruleaza `references/control-inainte-de-livrare.md`, cele cinci controale, juridic,
   comercial, de risc, probator si editorial. Ce iese acolo se repara inainte de
   livrare, nu se raporteaza ca observatie.
8. Livrarea merge pe drumurile existente: redline prin docx-track-changes, verificare
   de pachet, obiecte incorporate scoase inainte de plecare, quality-gate.

## Redactarea nu se blocheaza cu intrebari

Pe contracte, formatul de cerere din `references/metoda-redactarii.md`, punctul 18, tine
loc de contract de sarcina. Cand autorul l-a trimis completat, sau cand a dat aceleasi
informatii altfel, redactarea porneste fara confirmare separata. Ce lipseste si nu schimba
structura juridica primeste placeholder, `[●]`, si se semnaleaza scurt la livrare.

Se cere lamurire numai cand alegerea intre doua variante schimba regimul juridic sau
distributia riscurilor. Pasii de citire a modelelor si de verificare pe sintact raman
obligatorii; ei se anunta ca facuti, nu se cer ca permisiune.

## Regimul nivelului B

Contractele tertilor din dosare sunt referinta de practica a pietei, utile mai ales pe
familiile unde nivelul A e subtire (leasing, buy-back, arhitectura acord + conditii
generale + conditii speciale). Provenienta se spune de fiecare data; formularea lor nu
trece drept formularea casei; anul lor se respecta la fel ca la modelele proprii.

## Exceptia de stil

Stilul de casa NU se aplica pe corpul contractului, care e actul partilor, nu al
cabinetului. Antetul, sigla si subsolul cabinetului merg doar pe actele semnate de
avocat: adrese de inaintare, opinii, notificari in numele cabinetului. Aceeasi exceptie
ca la actele asociatiilor.

Exceptia merge si asupra limbii. Stratul anti-AI-tone nu se aplica pe text de contract,
corp, clauze, anexe contractuale si acte aditionale, fiindca genul contractual cere tocmai
ce penalizeaza stratul, titluri de articol urmate de doua puncte, definitii de forma „X
inseamna...", enumerari, alineate simetrice si termeni definiti repetati identic. Se
ruleaza pe ce semneaza cabinetul, adresa de inaintare, opinia, memoriul de revizuire,
matricea de completitudine si mesajul catre client. Regula e pusa in cod, in
`e_text_de_contract` din `hook_common.py`, consultat de hook si de poarta de calitate, cu
proba in `selftest_ton_contract.py`.

## Forma in Word

`docx_scrie_act` si `scrie_document.py` sunt facute pentru actele cabinetului, cu antet,
sigla, subsol si numerotare automata de paragraf. Un contract trecut prin ele ar iesi cu
sigla AMZ pe actul partilor si cu numerotarea de act de instanta peste articolele si
alineatele contractului. Contractul in Word porneste din modelul propriu al familiei,
fisierul .docx de pe disc, si se lucreaza pe el prin docx-track-changes, ceea ce merge in
acelasi sens cu regula ca formularea vine din model. Verificarea de pachet, scoaterea
obiectelor incorporate si perechea clean plus track raman obligatorii.

## Harta e vie, nu arhiva

Intrarile hartii sunt pointeri catre disc. Inainte de folosire, verifica pe disc ca
fisierul exista in forma lui de acum; autorul lucreaza in dosare si lista se schimba.
La fiecare contract nou livrat sau model nou descoperit, adauga intrarea in harta si
reconstruieste plugin-ul, ca sa ajunga si in Desktop. Un inventar care nu creste moare
in sase luni.

## Pe Claude Desktop

Harta si metoda ajung prin plugin. Citirea fisierelor din D:\Clienti depinde insa de
folderele montate in conversatie: cand dosarul nu e montat, harta iti spune ce exista
si unde, iar autorului i se cere sa monteze folderul sau sa mute sarcina in Claude
Code. Nu descrie continutul unui model pe care nu l-ai putut deschide; spune ca vorbesti
din harta, nu din fisier.
