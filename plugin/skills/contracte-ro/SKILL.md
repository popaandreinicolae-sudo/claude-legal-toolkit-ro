---
name: contracte-ro
description: >
  Harta contractelor casei si metoda de lucru pe orice sarcina de contract: redactare
  noua, revizuire pe document primit, opinie pe clauze, comparare cu modelul, act
  aditional. Se sprijina pe inventarul contractelor proprii (nivel A, formularile casei)
  si al contractelor tertilor din dosare (nivel B, referinta de practica). Declanseaza la
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
nu un sablon rigid. Harta completa sta in `references/harta-modelelor.md`, cu doua
niveluri: A, modelele si revizuirile proprii (~290, sursa de formulari ale casei), si B,
contractele tertilor din dosare (referinta de practica, niciodata formulari ale casei).
Etalonul fiecarei familii si golurile ei stau in `references/familii.md`.

## Prima intrebare, inainte de orice

Familia contractului si sarcina. Familia decide ce modele se deschid; formularea unui
plafon de raspundere din antrepriza nu se transplanteaza intr-o inchiriere. Sarcina
decide fluxul: redactare noua, revizuire pe document primit sau opinie pe clauze.
Inventarul de TEME calatoreste intre familii ca lista de completitudine; FORMULAREA se
preia numai inauntrul familiei din care s-a nascut.

## Fluxul de lucru

1. Incadreaza: familia si sarcina, cu intrebarile de mai sus.
2. Deschide `references/familii.md`, ia etalonul familiei si modelele vecine din harta.
   Cand familia e subtire, adauga referintele de nivel B indicate acolo, cu provenienta
   spusa.
3. Citeste modelele INTEGRAL, regula generala a casei. Pe un document primit spre
   revizuire, citeste-l intai pe el, tot integral, inainte de orice afirmatie despre el.
4. La revizuire, inainte de primul redline, livreaza autorului MATRICEA DE
   COMPLETITUDINE: lista temelor acoperite de modelele noastre bune ale familiei si
   starea fiecareia in documentul primit (acoperita, acoperita partial, lipsa). Temele
   de baza: forta majora cu enumerare, notificari cu persoane de contact si reguli de
   primire, raspundere cu plafoane si excluderi, incetare cu efectele ei, garantii,
   plati cu termene si dobanzi, confidentialitate, supravietuire, asigurari, cesiunea
   contractului, legea aplicabila si jurisdictia, anexe. Lista pleaca la autor si abia
   dupa ce o vede se trece la redline.
5. Clauza noua porneste de la formularea din modelul propriu al familiei, nu din
   memoria modelului AI. Cand familia nu are model propriu, spune-o si lucreaza pe
   referinta B, marcata ca atare.
6. Verifica pe timp: fiecare model poarta anul lui. Clauzele sprijinite pe lege,
   penalitati, dobanda legala, prelucrare de date, insolventa, consumatori, se
   confrunta cu legea la zi pe sintact inainte de preluare, dupa aceeasi regula ca
   doctrina (un model din 2020 descrie legea din 2020).
7. Livrarea merge pe drumurile existente: redline prin docx-track-changes, verificare
   de pachet, obiecte incorporate scoase inainte de plecare, quality-gate.

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
