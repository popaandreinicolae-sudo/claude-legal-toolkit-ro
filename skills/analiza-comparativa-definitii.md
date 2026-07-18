---
name: analiza-comparativa-definitii
description: >
  Extrage, compară și analizează sistematic definițiile juridice ale unui concept
  din multiple instrumente normative, generând tabele comparative și analize critice.
  OBLIGATORIU de folosit ori de câte ori Claude trebuie să compare definiții legale,
  să analizeze evoluția unui concept juridic prin mai multe acte normative, sau să
  identifice diferențe/convergențe între definiții din surse diferite (naționale, UE,
  internaționale, doctrinare). Se activează la: „definiție", „definire", „concept juridic",
  „analiză comparativă", „tabel comparativ", „elemente definitorii", „comparație legislativă",
  „evoluția definiției", „diferențe între definiții", „convergență", „divergență",
  „securitate cibernetică definiție", „securitate națională definiție", „drept fundamental
  definiție", „noțiune autonomă", „calitatea legii", „previzibilitate", „accesibilitate",
  „NIS", „NIS 2", „Cybersecurity Act", „Convenția de la Budapesta", „ISO 27001",
  „NIST", „ENISA", „OUG 155/2024", „Legea 362/2018", „Directiva 2022/2555".
  Se activează AUTOMAT la orice analiză care implică compararea a cel puțin două surse
  normative sau doctrinare pe același concept, chiar dacă utilizatorul nu cere explicit
  un tabel comparativ — o analiză comparativă structurată este întotdeauna mai utilă
  decât o enumerare narativă.
---

# Analiză comparativă a definițiilor juridice

Acest skill ghidează procesul de extragere, structurare și comparare a definițiilor
unui concept juridic din surse normative și doctrinare multiple. Rezultatul este un
instrument de lucru academic: tabel comparativ + analiză critică care poate fi integrat
direct într-un raport de cercetare doctorală, articol sau teză.

Motivul pentru care structura contează: în dreptul constituțional și dreptul UE,
definițiile nu sunt neutre — ele reflectă opțiuni de politică legislativă, delimitează
competențe și determină regimul juridic aplicabil. Două definiții aparent similare
pot avea efecte juridice radical diferite din cauza unui singur element inclus sau omis.
Acest skill te ajută să surprinzi exact aceste nuanțe.

---

## Metoda de lucru — pas cu pas

### Pasul 1: Identificarea conceptului și a perimetrului

Stabilește clar:

- **Conceptul analizat** (ex: „securitate cibernetică", „date cu caracter personal",

  „securitate națională")

- **Perimetrul comparației**: ce categorii de surse incluzi?
  - Legislație națională (România)
  - Legislație UE (directive, regulamente)
  - Tratate internaționale / convenții
  - Standarde tehnice (ISO, NIST)
  - Doctrină (autori de referință)
  - Jurisprudență (CCR, CJUE, CEDO)

Dacă utilizatorul nu specifică perimetrul, folosește implicit toate categoriile relevante
pentru conceptul cerut — mai bine acoperire completă decât lacune.

### Pasul 2: Extragerea definițiilor

Pentru fiecare sursă:

1. **Identifică textul exact** al definiției (citat integral, între ghilimele)
2. **Localizează precis**: articol, alineat, literă, paragraf, pagină
3. **Verifică autenticitatea**: folosește MCP-urile disponibile (legal-verificator-ro,

   EUR-Lex, HUDOC) și skill-urile de verificare (zero-legal-hallucination,
   verificare-legislatie, verificare-surse-citari) pentru a confirma că textul citat
   este real și în vigoare. Nu inventa niciodată textul unei definiții.

4. **Notează contextul**: în ce scop a fost adoptată definiția? Ce problemă rezolvă?

**Unde să cauți definiții (în ordine de prioritate):**

- Art. 2 sau art. 3 din actele normative UE (secțiunea „Definiții")
- Articolele inițiale din legile și OUG-urile românești
- Expunerile de motive / preambuluri (pentru context, nu pentru definiții propriu-zise)
- Secțiunile de definiții din standarde (ISO: secțiunea 3; NIST: glossar)
- Decizii ale CCR, CJUE sau CEDO care definesc incidental un concept

### Pasul 3: Descompunerea în elemente constitutive

Fiecare definiție se descompune în **elemente constitutive** — componentele atomice
care formează definiția. Această descompunere este nucleul analizei comparative.

**Exemplu concret** — definiția „securitate cibernetică":

Directiva NIS 2 (art. 2 pct. 1, Regulamentul Securitatea Cibernetică):
> „securitate cibernetică" înseamnă activitățile necesare pentru protejarea rețelelor
> și a sistemelor informatice, a utilizatorilor acestor sisteme și a altor persoane
> afectate de amenințări cibernetice

Elemente constitutive:

- **Natura**: „activități" (= proces, nu stare)
- **Scop**: „protejare" (= defensiv)
- **Obiect protejat**: rețele, sisteme informatice, utilizatori, alte persoane afectate
- **Amenințare**: „amenințări cibernetice" (termen definit separat)

Această descompunere se face pentru FIECARE definiție identificată.

### Pasul 4: Construcția tabelului comparativ

Tabelul trebuie să conțină cel puțin aceste coloane:

 | # | Instrument | Articol | Definiția (citat) | Elemente cheie | Natura conceptului | Obiect protejat | Observații | 
 | --- | ----------- | --------- | ------------------- | ---------------- | ------------------- | ----------------- | ------------ | 

**Reguli pentru tabel:**

1. **Ordonare cronologică** — de la cel mai vechi instrument la cel mai recent.

   Permite observarea evoluției conceptului în timp.

2. **Citat exact** — textul definiției se citează integral, fără parafrazare.

   Dacă definiția este foarte lungă (>100 cuvinte), se citează partea esențială
   cu `[...]` pentru omisiuni, dar se indică unde poate fi citit textul complet.

3. **Elemente cheie** — lista scurtă a elementelor constitutive extrase la Pasul 3,

   ca bullet points scurte.

4. **Natura conceptului** — clasificare proprie: stare / proces / activitate / proprietate /

   drept / obligație / competență. Această clasificare trebuie argumentată, nu doar afirmată.

5. **Observații** — notează aici: dacă definiția este operațională vs. conceptuală,

   dacă trimite la alte definiții, dacă a fost modificată/abrogată, dacă a fost
   interpretată jurisprudențial.

### Pasul 5: Analiza comparativă critică

După tabel, redactează o analiză structurată care răspunde la:

#### 5.1. Convergențe
Ce elemente apar în toate sau în cele mai multe definiții? Există un „nucleu dur"
al conceptului care persistă indiferent de sursă? Acest nucleu dur este semnificativ
juridic — el reprezintă conținutul minim pe care orice viitoare definiție va trebui
să îl integreze.

#### 5.2. Divergențe
Ce elemente diferă între definiții? Divergențele sunt clasificate în:

- **Divergențe de amplitudine** — o definiție acoperă mai mult decât alta

  (ex: NIS 2 include „utilizatorii" pe lângă sisteme, NIS 1 nu)

- **Divergențe de natură** — definițiile conceptualizează diferit același lucru

  (ex: securitate cibernetică ca „stare" vs. ca „activitate")

- **Divergențe de scop** — definițiile servesc scopuri diferite

  (ex: definiție operațională pentru compliance vs. definiție constituțională
  pentru delimitarea competențelor)

#### 5.3. Evoluția diacronică
Cum s-a transformat definiția în timp? Ce elemente au fost adăugate, eliminate sau
reformulate? Această evoluție reflectă schimbări în percepția amenințărilor,
în distribuția competențelor sau în tehnologie?

#### 5.4. Lacune și probleme
Ce lipsește din definițiile existente? Sunt concepte-satelit nedefinite pe care
definițiile le presupun fără a le clarifica? Există contradicții între definiții
din instrumente care ar trebui să fie coerente (ex: dreptul UE și transpunerea
națională)?

#### 5.5. Implicații constituționale (dacă este relevant)
Cum afectează definițiile exercițiul drepturilor fundamentale? O definiție mai largă
a „securității cibernetice" extinde perimetrul în care statul poate restrânge
drepturi (art. 53 din Constituție). O definiție vagă ridică probleme de previzibilitate
și calitate a legii.

---

## Format de output

Rezultatul complet al analizei trebuie să conțină, în ordine:

1. **Titlu**: „Analiza comparativă a definițiilor conceptului de [X]"
2. **Introducere** (2-3 paragrafe): de ce contează definiția, ce instrumente au fost analizate
3. **Tabel comparativ** (Pasul 4)
4. **Analiză critică** (Pasul 5, cu toate cele 5 subsecțiuni)
5. **Concluzii** (1-2 paragrafe): sinteza elementelor principale, direcții de cercetare
6. **Note de subsol** — formatate conform skill-ului `format-bibliografie-doctorat-ub`

Dacă output-ul este un document Word (.docx), tabelul se formatează cu:

- Header pe fond gri deschis, bold
- Borduri simple, negre
- Font: Times New Roman, 10pt în tabel (corpul textului 12pt)
- Tabelul centrat pe pagină, cu auto-fit pe conținut

---

## Utilizarea MCP-urilor și skill-urilor complementare

Acest skill funcționează cel mai bine când este combinat cu:

- **legal-verificator-ro** — pentru a verifica textul exact al legislației românești

  și al deciziilor CCR citate

- **zero-legal-hallucination** / **verificare-legislatie** — pentru a preveni

  citarea de acte abrogate sau texte fabricate

- **format-bibliografie-doctorat-ub** — pentru formatarea corectă a notelor de subsol
- **verificare-surse-citari** — pentru validarea URL-urilor și referințelor
- **Tavily** / **Scholar Gateway** — pentru identificarea definițiilor din doctrină

  și standarde tehnice

- **EUR-Lex / HUDOC MCP** (dacă disponibil) — pentru textele exacte ale actelor UE

  și hotărârilor CEDO

Dacă nu ai acces la un MCP specific, indică în analiză: „[Text necitabil direct —
de verificat manual pe EUR-Lex/legislatie.just.ro/hudoc.echr.coe.int]".

---

## Exemple de concepte pentru care acest skill este relevant

Această listă nu este exhaustivă — skill-ul se aplică la orice concept juridic
definit în mai multe instrumente:

- Securitate cibernetică / cybersecurity
- Securitate națională
- Date cu caracter personal / personal data
- Operator de servicii esențiale
- Infrastructură critică
- Incident de securitate cibernetică
- Amenințare cibernetică
- Reziliență (digitală, operațională)
- Serviciu digital / platformă online
- Inteligență artificială (sisteme de IA)
- Supraveghere electronică
- Drept la viață privată digitală

---

## Anti-pattern-uri — ce NU trebuie să facă acest skill

1. **Nu inventa definiții.** Dacă nu poți verifica textul exact al unei definiții,

   scrie „[definiția exactă trebuie verificată pe sursa primară]" și indică sursa.

2. **Nu simplifica prin parafrazare.** Tabelul comparativ trebuie să conțină citate

   exacte, nu reformulări. Reformularea este permisă doar în analiza critică (Pasul 5).

3. **Nu omite surse pentru a face tabelul mai „curat".** Un tabel cu 12 rânduri

   care acoperă toate instrumentele relevante este mai util decât unul cu 4 rânduri
   „mai elegant".

4. **Nu forța convergențe false.** Dacă definițiile sunt fundamental diferite, spune-o.

   Divergența este un rezultat de cercetare valid.

5. **Nu ignora standardele tehnice.** ISO 27001, NIST CSF și ENISA sunt surse

   la fel de relevante ca legislația pentru concepte tehnico-juridice precum
   securitatea cibernetică.
