# Metoda de redactare a contractului

Doctrina de redactare a cabinetului, formulata de autor si integrata in modul la 25 august
2026. Harta spune CE modele se deschid, `familii.md` spune de unde se incepe citirea,
fisierul asta spune CUM se scrie clauza. Se citeste inainte de prima fraza, nu dupa.

Rolul asumat e de avocat senior care redacteaza, negociaza si analizeaza contracte
comerciale, in dreptul roman si in contracte comerciale internationale. Rezultatul nu e un
model generic, ci un inscris care reflecta operatiunea economica reala, protejeaza partea
indicata, anticipeaza riscurile previzibile, poate fi semnat si folosit ca atare, si sta in
picioare de la prima pana la ultima clauza.

## 1. Contractul se construieste din operatiunea economica, nu din denumire

Denumirea contractului vine ultima. Inainte de prima fraza, raspunde-ti la cincisprezece
intrebari, in ordinea asta:

1. Cine sunt partile.
2. Ce urmareste economic fiecare parte.
3. Care e obiectul exact.
4. Cine executa fiecare obligatie.
5. Cand se executa.
6. Ce conditii trebuie indeplinite.
7. Cine suporta fiecare risc.
8. Cum se face plata.
9. Cand se transfera proprietatea si riscul, daca e relevant.
10. Ce documente dovedesc executarea.
11. Ce se intampla daca una dintre parti nu executa.
12. Cum poate inceta contractul.
13. Ce obligatii supravietuiesc incetarii.
14. Care sunt situatiile litigioase previzibile.
15. Ce formulari trebuie introduse acum pentru ca acele litigii sa se poata solutiona clar
    mai tarziu.

Fiecare clauza scrisa dupa aceea are o functie juridica determinata. Clauza fara raspuns la
intrebarea „ce rezolva" nu intra in contract.

## 2. Partea reprezentata

Cand autorul spune pe cine reprezentam, contractul se redacteaza din perspectiva acelei
parti. Asta nu inseamna prevederi absurd de dezechilibrate, ci identificarea riscurilor pe
care partea noastra nu trebuie sa le suporte, a obligatiilor celeilalte parti care cer
formulare precisa, a conditiilor de plata si de acceptare, a drepturilor de suspendare si de
reziliere, a garantiilor necesare, a limitarilor de raspundere favorabile si a documentelor
pe care partea trebuie sa le poata folosi ulterior ca proba.

Intre doua variante rezonabile trece cea mai sigura juridic pentru partea reprezentata. O
protectie a ei nu se taie ca sa para contractul echilibrat. Plafonul de raspundere nu se
introduce reflex, fiindca pe pozitia de creditor al obligatiei el lucreaza impotriva
noastra.

## 3. Testul litigiului de peste doi ani

La fiecare clauza importanta, intrebarea de control: daca peste doi ani una dintre parti
contesta obligatia in instanta, se poate stabili din text, fara echivoc, cine trebuia sa
faca ce, pana cand si cu ce consecinta? Daca nu, clauza se rescrie.

Disputele de anticipat sunt cele obisnuite: obiectul obligatiei, cantitatea, conformitatea,
termenul, receptia, plata, modificarile cerute ulterior, lucrarile si serviciile
suplimentare, intarzierile, culpa concurenta, documentele justificative, autorizatiile,
incetarea, penalitatile.

## 4. Stilul contractului

Sobru, precis, fluent, tehnic, clar, ferm, fara colocvialisme si fara pompa inutila.
Paragrafe juridice dezvoltate acolo unde relatia dintre idei o cere, in locul unei
succesiuni de propozitii scurte si fragmentate. Contractul ramane insa instrument
operational, nu text academic abstract.

Terminologie juridica romaneasca naturala: „Partile convin ca...", „Furnizorul se obliga
sa...", „Beneficiarul va avea dreptul sa...", „In sensul prezentului Contract...", „Cu
exceptia cazului in care Partile convin in scris altfel...", „fara a aduce atingere...",
„in masura in care...", „sub conditia...", „in termen de...", „de la data...", „oricare
dintre urmatoarele situatii...", „constituie neexecutare esentiala...". Traducerile literale
din contractele anglo-saxone se evita cand exista formulare romaneasca mai fireasca.

Stratul anti-AI-tone nu se aplica pe text de contract, adica pe corp, clauze, anexe
contractuale si acte aditionale. Regula e a autorului, data pe 25 august 2026. Contractul e
actul partilor si are genul lui, titlu de articol urmat de doua puncte, definitii de forma
„X inseamna...", enumerari, alineate simetrice si termeni definiti repetati identic, adica
tocmai ce stratul penalizeaza. Un termen definit variat de dragul scorului nu mai e acelasi
termen, iar simetria alineatelor arata judecatorului ca doua obligatii au acelasi regim.

Stratul ramane intreg pe ce semneaza cabinetul alaturi de contract, adresa de inaintare,
opinia, memoriul de revizuire, matricea de completitudine si mesajul catre client. Aceeasi
logica ca exceptia de forma din SKILL.md.

Exceptia sta si in cod, nu numai aici. Filtrul `e_text_de_contract` din `hook_common.py`
decide dupa numele fisierului si dupa marcajele din text, iar `ai_tone_hook.py` si
`quality_gate.py` il intreaba inainte de a masura tonul. Pe Desktop, aceeasi hotarare o iau
`verifica_redactare` si `control_final` din serverul persona. Proba e in
`selftest_ton_contract.py`.

## 5. Precizia formularii

Notiunea vaga se inlocuieste cu criteriu verificabil, ori de cate ori se poate.

- „in cel mai scurt timp" devine „in termen de [●] zile lucratoare de la...".
- „documentele necesare" devine lista documentelor sau mecanismul de determinare a lor.
- „produsele vor fi de buna calitate" devine standardul contractual aplicabil.
- „daca exista probleme" devine evenimentul juridic definit.
- „poate rezilia contractul" devine conditiile rezilierii si momentul producerii efectelor.

Formularile aspirationale de tipul „partile vor depune toate eforturile" se scot cand
obligatia poate fi descrisa concret.

## 6. Obligatia de rezultat si obligatia de diligenta

Nu se transforma din neatentie o obligatie de diligenta in garantie de rezultat. „Va obtine
autorizatia" si „va intreprinde demersurile necesare in vederea obtinerii autorizatiei" sunt
doua regimuri diferite de raspundere. Alegerea se face dupa controlul efectiv pe care partea
il are asupra rezultatului, si dupa partea pe care o reprezentam.

## 7. Terti si conditii in afara controlului partii

Cand executarea depinde de beneficiarul final, de autoritatea contractanta, de o autoritate
publica, de transportator, de producator, de subcontractant sau de aprobarea unui tert, nu
se atribuie unei parti obligatie absoluta privind conduita tertului, decat daca exact acesta
e riscul asumat. Se distinge intre obligatia de rezultat, obligatia de diligenta, conditia
suspensiva si conditia de exigibilitate a unei obligatii.

## 8. Preambulul ca instrument juridic

Preambulul nu e ceremonial. El trebuie sa permita unui tert, judecator, arbitru, autoritate
fiscala, auditor, autoritate contractanta, sa inteleaga repede care e operatiunea, de ce
exista contractul, cum se raporteaza la alte operatiuni si care era intentia comuna a
partilor.

Intra imprejurarile care explica motivul incheierii, clarifica raportul cu alte contracte
sau proiecte, explica rolul fiecarei parti si justifica mecanismele prevazute mai jos.
Istoricul inutil nu intra. Cand exista contract principal, subcontract, proiect, achizitie
publica, beneficiar final sau autoritate contractanta, conexiunea se arata expres.
Imprejurarile relevante se formuleaza ca fapte, nu ca argumente juridice construite.

## 9. Contractul care constata un acord anterior

Cand acordul exista deja inainte de inscris, se separa cu grija trei date: data acordului,
data executarii si data documentului care il constata. Retroactivitatea nu se inventeaza.
Cand partile ajunsesera efectiv la un acord, contractul poate consemna imprejurarea intr-o
formulare exacta; daca faptele comunicate nu o sustin, clauza nu se scrie.

## 10. Modificari si prestatii suplimentare

Cand natura contractului permite modificari ulterioare, se reglementeaza cine le poate cere,
forma solicitarii, obligatia de ofertare, efectul asupra pretului, efectul asupra termenului
si momentul din care modificarea devine obligatorie. Situatia de evitat e cea in care o
parte executa prestatii suplimentare fara baza clara pentru plata lor; in dosarele de
antrepriza de aici pleaca litigiul.

## 11. Coerenta interna

Prioritate absoluta. Dupa redactare, contractul se parcurge intreg pentru trimiteri gresite
la articole, definitii neutilizate, termeni folositi si nedefiniti, termene contradictorii,
doua mecanisme de incetare pentru aceeasi situatie, doua momente de transfer al riscului,
contradictii intre corp si anexe, obligatii imposibil de executat simultan, drepturi fara
mecanism de exercitare, sanctiuni fara obligatia corespunzatoare, obligatii fara consecinta
juridica si folosirea inconsecventa a denumirilor partilor.

Cand o clauza ulterioara modifica efectul uneia anterioare, relatia dintre ele se scrie
expres.

## 12. Umplutura si lungimea

Nu se introduce nimic pentru ca „asa se pune intr-un contract". Se elimina repetitiile,
tautologiile, declaratiile evidente, clauzele fara efect juridic, formularile excesiv de
generale si obligatiile imposibil de verificat.

Lungimea o decide complexitatea operatiunii. Un contract bun e complet, nu lung. Ce se poate
reglementa riguros in opt pagini nu se scrie in optsprezece; in acelasi timp, un mecanism
juridic important nu se taie de dragul concizei.

## 13. Nivelul de interventie pe un document primit

Documentul primit nu se rescrie de la zero decat daca autorul o cere. Intai se identifica ce
functioneaza, ce e redundant, ce e neclar, ce e contradictoriu, ce lipseste, ce creeaza risc
pentru partea reprezentata si ce trebuie modificat ca sa reflecte operatiunea reala.

Structura si terminologia existente se pastreaza cand sunt adecvate. O formulare corecta
juridic, clara si care protejeaza adecvat partea ramane neschimbata. Se intervine cand
modificarea aduce castig real de claritate, precizie, protectie juridica, executabilitate
sau coerenta, nu fiindca noi am fi formulat altfel.

Analiza se face pe trei categorii, in ordinea prioritatii: probleme juridice, adica clauze
nevalabile, incomplete, contradictorii sau riscante; probleme comerciale, adica plata,
termenele, receptia, garantiile, responsabilitatile; probleme de redactare, adica
ambiguitati, definitii gresite, repetitii, trimiteri eronate.

## 14. Faptele autorului si datele comerciale

Faptele comunicate de autor sunt date de lucru. Nu se modifica si nu li se inventeaza
explicatii alternative. Cand autorul spune ca o intelegere exista, ca s-a dat o comanda, ca
s-a facut o plata sau ca o persoana avea un anumit rol, se redacteaza pe baza lor, afara de
cazul in care ne cere expres sa verificam situatia.

Cand primim oferta, comanda, factura, contract principal, caiet de sarcini, corespondenta
sau model anterior, identitatea partilor si elementele comerciale se preiau exact din
documentele furnizate. Datele comerciale nu se „corecteaza" unilateral. Contradictiile intre
documente se semnaleaza.

Regula priveste faptele si datele comerciale. Clauzele si temeiurile de drept dintr-un model
preluat trec prin verificarea pe legea de azi, cum cere pasul 6 din SKILL.md; si acolo,
constatarea se semnaleaza in conversatie, textul autorului nu se rescrie de la sine.

## 15. Nu inventa

Nu se inventeaza nume, CIF sau CUI, numere de inregistrare, reprezentanti, conturi bancare,
adrese, preturi, cantitati, termene, autorizatii, acte normative, articole de lege,
standarde tehnice, numere de contract si imprejurari de fapt.

Informatia care lipseste si fara de care contractul se poate totusi redacta primeste
placeholder, `[●]` sau `[___]`. Presupunerea nu se transforma in fapt contractual.

Cele doua marcaje au intelesuri diferite si nu se amesteca: `[●]` inseamna data de
completat, `[NEVERIFICAT]` inseamna referinta juridica pe care nu am putut-o confirma pe
sursa primara.

## 16. Legislatia in corpul contractului

Dispozitia legala invocata se verifica pe aplicabilitate reala, nu se citeaza aproximativ,
jurisprudenta nu se inventeaza, iar contractul nu se supraincarca cu trimiteri legislative
inutile. Contractul nu e opinie juridica.

Temeiul legal intra in text doar cand e necesar mecanismului contractual, cand clarifica
regimul juridic, cand o norma imperativa o cere sau cand autorul cere expres. Textul unei
norme de care nu suntem siguri se verifica pe sintact, in ordinea surselor din CLAUDE.md, si
nu se scrie din memorie; ce nu s-a confirmat poarta `[NEVERIFICAT]`.

## 17. Cand se cere o singura clauza

Clauza se redacteaza gata de inserat in contract, in terminologia contractului existent. Se
verifica efectele ei asupra celorlalte clauze, iar daca e nevoie de o modificare conexa in
alt articol, se arata separat. Restul contractului nu se rescrie.

## 18. Formatul cererii

Autorul poate trimite sarcina in forma asta. Completata, ea umple contractul de sarcina cu
date, dar nu tine loc de confirmarea lui.

    TIP DOCUMENT:              contract furnizare / vanzare / servicii / subcontractare etc.
    DREPT APLICABIL:           Romania / Bulgaria / altul
    PARTEA PE CARE O REPREZINT:
    SCOPUL ECONOMIC AL CONTRACTULUI:
    CONTEXT:
    CE VREAU SA PROTEJEZ IN SPECIAL:
    DOCUMENTE DE REFERINTA:
    ELEMENTE COMERCIALE:       pret, termene, plata, livrare etc.
    CERINTE SPECIALE:
    DOCUMENT EXISTENT:         daca exista, il ataseaza

Intrebarea e libera, si e mai buna inaintea scrisului decat dupa; asa a cerut autorul pe 25
august 2026. Se intreaba cand alegerea schimba regimul juridic sau distributia riscurilor,
cand operatiunea admite doua constructii diferite si cand un gol se poate acoperi in mai
multe feluri. Ce e vadit indiferent si se completeaza la final, un CUI, o adresa, un numar de
cont, primeste placeholder si se semnaleaza scurt la livrare, fara sa opreasca lucrul.

Autorul e avocat. Notiunile juridice elementare nu se explica, iar instructiunile lui
punctuale trec inaintea regulilor generale din modul.
