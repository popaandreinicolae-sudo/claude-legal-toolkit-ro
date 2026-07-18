# CCR URL Patterns — Cum să găsești URL-ul corect al unei decizii CCR

**Scop**: Eliminarea HTTP 404 pe ccr.ro — ghid pentru construirea/găsirea URL-urilor reale ale deciziilor Curții Constituționale.

## Problema

URL-uri ghicite tip `https://www.ccr.ro/wp-content/uploads/2018/04/Decizie_136_2018.pdf` returnează **404** — pattern-ul nu este universal. CCR.ro folosește slug-uri SEO bazate pe titlul deciziei, plus arhivă PDF cu nume variabile.

## Pattern-uri reale CCR.ro

### Pagină HTML decizie
```
https://www.ccr.ro/decizia-{N}-din-{ZZ}-{LL}-{YYYY}/
```
- `{N}` = numărul deciziei
- `{ZZ}` = ziua (cu zero-padding sau nu — variabil)
- `{LL}` = luna în litere mici, română fără diacritice (ex: `martie`, `aprilie`)
- `{YYYY}` = anul

**Exemplu**: Decizia CCR nr. 136/2018 (21 martie 2018) → `https://www.ccr.ro/decizia-136-din-21-martie-2018/`

### PDF arhivă
```
https://www.ccr.ro/wp-content/uploads/{YYYY}/{MM}/{filename}.pdf
```
- `{YYYY}/{MM}` = an/lună **publicare în M.Of.** (NU data deciziei)
- `{filename}` poate fi: `Decizie_{N}_{YYYY}.pdf`, `D{N}_{YYYY}.pdf`, `Dec_{N}.pdf`, sau slug
- **Nu există convenție unică** — variază de la lună la lună

## Strategia corectă

### 1. NU ghici URL-ul — caută

```
WebSearch query: "Decizia CCR nr. 136/2018" site:ccr.ro
```

### 2. Sau caută monitorul oficial

```
WebSearch: "Decizia 136/2018" "Monitorul Oficial" site:legislatie.just.ro
```

### 3. Folosește MCP `legal-verificator-ro` mai întâi

```
mcp__legal-verificator-ro__search_ccr_decision({ number: 136, year: 2018 })
```

Returnează URL real legislatie.just.ro + linkuri secundare.

### 4. Alternative — surse care citează decizia integral

| Sursă | URL pattern | Cum să cauți |
|---|---|---|
| Hotărâri CEDO (înrudite) | `hotararicedo.ro` | WebSearch "decizie 136/2018 ccr" site:hotararicedo.ro |
| Universul juridic | `universuljuridic.ro` | Articole comentariu |
| Juridice.ro | `juridice.ro` | Pagini analiză cu citate |
| Lege5 | `lege5.ro/Gratuit/...` (cu cont) | Search prin MCP lege5_search |
| Legalis | `idrept.ro` (abonament) | Doar dacă utilizatorul are acces |
| C.H. Beck | `legalis.ro` | Idem |

## Format M.Of. — info necesară pentru citare academică

Pentru fiecare decizie CCR, **TREBUIE** identificate:
- **Numărul deciziei** (ex: 136)
- **Data deciziei** (ex: 21 martie 2018)
- **Numărul M.Of.** + Partea (ex: nr. 383, Partea I)
- **Data publicării M.Of.** (ex: 4 mai 2018)

**Citare standard**: `Curtea Constituțională, Decizia nr. 136 din 21 martie 2018, M. Of., Partea I, nr. 383 din 4 mai 2018, par. X`

## Pattern slug-uri SEO ccr.ro (observat empiric)

- `/decizia-{N}-din-{D}-{LUNA}-{YYYY}/`
- `/{action}-decizia-{N}/` (uneori, ex: `comunicat-decizia-136`)
- `/categorie/decizii-{YYYY}/decizia-{N}/`

**Verificare automată URL**:
```
HEAD request → 200 OK → URL valid
404 → încearcă alternativ
301/302 → urmărește redirect
```

## Decizii frecvent citate în doctorat (cache rapid)

Când lucrez în proiectul de doctorat, decizii frecvente (de păstrat în memorie):

| Decizie | M.Of. | Subiect |
|---|---|---|
| 70/2023 | nr. 154/22.02.2023 | Securitate cibernetică = securitate națională |
| 72/2021 | nr. 116/04.02.2021 | Limite ale competenței legislative parlamentare |
| 136/2018 | nr. 383/04.05.2018 | Imunitate parlamentară |
| 619/2016 | nr. 6/04.01.2017 | Calitatea legii (claritate, precizie, previzibilitate) |
| 26/2012 | nr. 116/15.02.2012 | Tehnică legislativă |
| 447/2013 | nr. 674/04.11.2013 | Lipsa clarității afectează drepturile |
| 629/2018 | nr. 879/18.10.2018 | Derogări de la legi organice |

(Lista de extins pe măsură ce apar decizii noi în lucru)

## Trigger-uri automate

Aplică acest skill când:
- Cau URL pentru o decizie CCR specifică
- Primesc 404 pe ccr.ro
- Trebuie să verific o decizie CCR pentru citare academică
- Lucrez în proiect de doctorat sau punct de vedere CCR/CNCD
