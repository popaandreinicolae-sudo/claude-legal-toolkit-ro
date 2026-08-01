---
name: pdf-scanat
description: >
  Citirea unui PDF scanat, adica una din care extragerea de text intoarce gol, cum sunt
  hotararile descarcate de pe portalul instantelor. Converteste paginile in imagini si le
  citeste. Declanseaza la "nu pot citi PDF-ul", "PDF scanat", "hotarare de pe portal",
  "document finalizat", "citeste sentinta din PDF", "extrage textul din scanare",
  "ce scrie in incheiere", "PDF prea mare", "fisier de zeci de MB", "nu are text",
  "scoate paginile ca imagini".
---

# PDF scanat, cum se citeste

## Cand se aplica

Extragerea de text intoarce gol sau aproape gol. Fisierul e mare, adesea peste 100 MB, si
citirea directa il refuza. Numele fisierului nu spune nimic; portalul instantelor descarca
tot ce e finalizat sub numele `document finalizat.pdf`, indiferent daca inauntru e o
sentinta, o incheiere sau un certificat.

Inainte de conversie, verifica daca chiar e nevoie. Un PDF cu strat de text se citeste
direct, iar conversia in imagini ar fi munca in plus si citire mai slaba.

## Comanda

    python ~/.claude/skills/pdf-scanat/scripts/pdf_in_imagini.py --input "cale.pdf"

Implicit scoate primele patru pagini, langa PDF, intr-un folder cu numele lui. Alte forme:

    --pagini 1-8          intervalul
    --pagini 1,3,7        pagini razlete
    --pagini toate        tot documentul
    --output "D:\...\X"   alt folder

Dupa conversie, paginile se citesc ca orice imagine. Actele oficiale scanate se citesc bine,
inclusiv stampilele si numerele scrise de mana.

## De ce nu merge altfel

Extragerea de imagini din bibliotecile obisnuite cere Pillow, care lipseste frecvent de pe
masina. Scriptul nu instaleaza nimic si nu depinde de el:

Imaginile DCTDecode sunt deja JPEG in interiorul fisierului, deci se scriu ca atare.

Imaginile FlateDecode sunt esantioane brute comprimate cu zlib, exact compresia folosita si
de PNG. Pagina se reimpacheteaza direct, adaugand octetul de filtru la inceputul fiecarui
rand. Fara conversie de format si fara pierdere.

Spatiul de culoare declarat poate fi indirect, de pilda `/ICCBased`, caz in care numarul de
canale nu se poate citi din declaratie. Se deduce din cate esantioane au iesit la
decomprimare, impartite la numarul de pixeli. CMYK se converteste aproximativ in RGB,
fiindca PNG nu il cunoaste.

## Ce se cauta intr-o hotarare scanata

Ordinea utila, din experienta pe dosarele proprii. Prima pagina poarta instanta, numarul de
dosar, numarul si data hotararii, completul. Ultimele pagini poarta dispozitivul si
mentiunea de ramanere definitiva. Certificatele si anexele stau spre final, pe pagini
separate, adesea in alt format decat restul.

La un dosar de asociatie, cifrele care se cauta sunt numarul dosarului, numarul si data
sentintei sau incheierii, numarul si data certificatului de inscriere a persoanei juridice,
numarul si data inscrierii in registrul special, plus codul de identificare fiscala de pe
certificatul ANAF. Toate intra apoi in cererile catre instanta si in cererile catre ANS sau
catre autoritatea care raspunde de vanatoare.

## Curatenie

Imaginile ocupa cateva MB pe pagina. Cand ai terminat de citit, pastreaza in dosarul
clientului numai paginile care conteaza, restul se sterg.
