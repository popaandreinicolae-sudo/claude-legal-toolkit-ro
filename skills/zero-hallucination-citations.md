---
name: zero-hallucination-citations
description: >
  Prevents hallucinated citations, legal references, bibliographic data, and technical values
  in professional documents. MANDATORY when generating: footnotes, bibliographic citations,
  references to legislation (laws, EU directives/regulations), technical values with sources
  (thresholds, EUR/ISBN/DOI codes), direct quotes, project fiches with indicators. Triggers:
  footnote, source, citation, reference, article of law, EUR, DOI, ISBN, pursuant to,
  Official Gazette, directive, regulation, normative act, peer-reviewed, threshold, compliance.
  Activated BEFORE generating any factual claim with a source. Optimized for Romanian/EU
  legislation, World Bank, EC, JRC reports, academic literature. Works in Romanian and English.
  Use this skill whenever Claude produces text containing verifiable references, even if
  the user does not explicitly ask for citations.
---

# Zero Hallucination Citations

## Why this skill exists

Language models have a documented tendency to generate plausible but false citations: invented
publication codes, nonexistent legal articles, fabricated technical values, misattributed quotes.
In professional contexts (World Bank reports, public policy strategies, legal documents,
academic papers, EU-funded project deliverables), a single false citation can invalidate an
entire document and destroy the author's credibility.

This skill imposes a strict verification protocol that makes it impossible to publish an
unverified citation without explicit marking. It does not slow down work, it disciplines it.

## Scope of application

This skill applies to ANY professional document production involving verifiable claims:

- Legal analysis and memoranda (any jurisdiction, with emphasis on Romanian and EU law)
- Policy documents, strategies, action plans
- World Bank, European Commission, or other institutional reports
- Academic papers and research outputs
- Project fiches and grant applications
- Technical reports with regulatory thresholds
- Any text where factual claims are attributed to specific sources

## The error taxonomy

Consult `references/error-taxonomy.md` for the complete list with documented real-world examples.
The eight categories of citation error this skill prevents:

1. Publication code fabrication, meaning inventing EUR, ISBN, DOI codes that do not exist
2. Legal article fabrication, meaning citing a nonexistent article or paragraph from a real law
3. Technical value fabrication, meaning inventing a threshold, area, or percentage without source
4. Source misattribution, meaning real data attributed to the wrong document
5. Quote misattribution, meaning a real quote placed in the wrong report or edition
6. Citation contamination, meaning combining elements from different sources into one footnote
7. Territorial generalization, meaning extending data from one territory to another without filtering
8. Unverifiable data presented as fact, meaning plausible numbers without any identifiable source

Understanding WHY these errors happen is key to preventing them. The model's training data
contains millions of partially correct fragments. A publication code off by one digit, a legal
article number from a neighboring section, a "round" technical value that sounds credible,
all of these feel right to the model but are wrong. The cost of verification is small.
The cost of a published error is enormous.

## The four absolute rules

### Rule 1: Never cite from memory

Never generate from memory: EUR, ISBN or DOI codes; specific legal article numbers with
paragraphs; precise technical values (thresholds, areas, percentages); or direct quotes
in quotation marks.

If you cannot verify in real time (via web search, by reading a user-provided document,
or by accessing a database), then mark it:

```
[UNVERIFIED] The value X is mentioned in [source Y], but I could not confirm the exact
article, page, or figure. I recommend direct verification of the source.
```

The reasoning: the model's memory contains millions of partially correct fragments. A code
EUR 31028 instead of EUR 31269, an art. 2 instead of art. 8, a value of 56 kWh instead
of 120 kWh, all are errors that look correct but are not.

### Rule 2: Verify each element of a citation independently

A bibliographic citation has at minimum 5 verifiable elements. Each must be confirmed
independently:

| Element | Correct example | Typical error |
|---------|----------------|---------------|
| Authors | San-Miguel-Ayanz, J. et al. | Omitting or inventing authors |
| Publication year | 2022 | Confusing publication year with data year |
| Exact title | Forest Fires in Europe...2021 | Approximate title or wrong edition |
| Publication code | EUR 31269 EN | Invented code (EUR 31028) |
| DOI/ISBN | 10.2760/34094 | Fabricated DOI from another report |
| Page/table | Table 55, p. 141 | Invented page number |
| Direct quote | verified verbatim in document | Paraphrase presented as quote |

If you cannot verify an element, mark it explicitly:

```
San-Miguel-Ayanz, J. et al. (2022). Forest Fires in Europe, Middle East and
North Africa 2021. EUR [to verify on cover]. JRC130846.
```

### Rule 3: Mark the type of every piece of information

Every factual claim falls into one of three categories. Mark them:

- **[DATA]**, confirmed with a verified source (you read the document or confirmed via search)
- **[ESTIMATE]**, your own calculation, with methodology explained
- **[UNVERIFIED]**, plausible information but unconfirmed

Never mix categories. An estimate presented as data is a lie. Unverified data presented
without marking is a hallucination.

### Rule 4: Mandatory cross-verification

Before delivering a citation, mentally walk through this checklist:

1. Does the source exist? Have I confirmed the document, report, or legal act exists?
2. Is the edition correct? Do the year, edition number, and code all match the same document?
3. Is the quote from THIS source? Is the cited information actually in the invoked document,
   not in another document from the same series?
4. Does the territory match? Are the data for the specific geographic area mentioned,
   not for a broader or narrower area?
5. Are elements uncontaminated? Do all citation elements (authors, year, code, page,
   quote) come from the same document, not combined from different documents?

## Source-specific procedures

### Legislation (Romanian, EU, or any jurisdiction)

When citing an article from a law, ordinance, government decision, or regulation:

- Never cite a specific article number from memory. Search for the legal text first.
- Legislation is frequently amended. An article valid in 2020 may be repealed by 2025.
- The correct format includes type of act, number, year, article, paragraph, letter.
  Example: "Emergency Ordinance no. 27/1996, art. 8 para. (1)".
  Example: "Regulation (EU) 2024/1991, Art. 4(1)(a)".
- If you cannot access the legal text, say explicitly:
  "I could not verify the current text of art. X of Law Y. I recommend verification
  on the official legal database [legislatie.just.ro / EUR-Lex / relevant national portal]."
- The principle stated in a framework law is often different from the specific values
  set in implementing regulations or technical methodologies. Do not confuse the two.

### Institutional reports (JRC, World Bank, EC, OECD, UN agencies)

Reports from these institutions appear in annual series. Confusion between editions
is the most frequent error. Verify:

- The year in the title (data covered) versus the publication year. They are different.
  "Forest Fires...2021" equals data about 2021, published in 2022.
- The publication code. Each edition has a unique code. Do NOT extrapolate from one edition.
- A quote from the 2020 edition cannot be attributed to the 2021 edition, even if the
  subject is similar.
- Institutional reports often have internal report codes (JRC codes, World Bank report numbers)
  in addition to publication codes (EUR, ISBN). These are different identifiers.

### Technical values and regulatory thresholds

Technical values (nZEB thresholds, zoning areas, emission limits, energy performance
indicators) are defined in specific normative acts or technical methodologies, not in
the framework law.

- The law establishes the principle; the methodology establishes the value.
  Example: Law 372/2005 mandates nZEB, but the concrete values (kWh per m2 per year) are
  in Methodology Mc001/2022 and vary by climate zone and building type.
- Do not invent "round" or "plausible" technical values. If you don't have the exact
  source, say so.
- Technical standards and thresholds change with regulatory updates. Always specify
  the year or version of the standard being cited.

### Geographic and territorial data

Data valid for a country, data valid for a region, data valid for a protected area,
data valid for a specific municipality. These are different territories with fundamentally
different legal regimes.

- Always explicitly mention the geographic area to which the data refer.
- Never generalize from a larger territory to a smaller one without explicit filtering
  and justification.
- Administrative boundaries, statistical regions, and protected area perimeters rarely
  coincide. Be precise about which boundary is being used.

### Academic literature

When citing peer-reviewed papers:

- Verify the DOI exists and resolves to the correct paper (if you have web access).
- Author lists in multi-author papers are easily confused. Verify at least first and last author.
- Conference papers, journal papers, and preprints are different publication types
  with different citation formats.
- Do not generate DOIs from memory. They follow patterns but are not algorithmically
  predictable.

## Footnote format

A correct footnote contains:

```
Authors (Year). Full title in italics. Publication code [if applicable]. Place of
publication: Publisher. DOI: [if applicable]. Available at: [functional URL, if applicable].
Specific element cited: [exact page, table, section].
```

A contaminated footnote, one that mixes elements from different sources, is worse
than no footnote at all, because it creates false confidence in the reader.

## When you don't know, the uncertainty protocol

When you lack sufficient data, do not fill gaps with unmarked estimates. Use:

```
[UNVERIFIED] For [specific indicator] I have not identified verified data in
accessible sources. The data could be obtained from [specific institution].
Until then, I recommend [alternative or proxy value with justification].
```

This is not a weakness; it is a mark of professionalism. A document with 3 explicitly
marked gaps is infinitely more valuable than a document with 3 false citations.

## Final checklist before delivering text with citations

Before sending any text containing footnotes or citations:

- [ ] Does every number have a verified source or an [ESTIMATE] or [UNVERIFIED] marking?
- [ ] Has every EUR, ISBN, or DOI code been confirmed (not generated from memory)?
- [ ] Has every legal article been verified against the current text of the law?
- [ ] Has every direct quote been confirmed verbatim in the invoked document?
- [ ] Do all elements of each footnote come from the same source?
- [ ] Do geographic data correspond exactly to the territory mentioned in the text?
- [ ] Are there no "round" or "plausible" technical values without a source?
- [ ] Are included URLs functional and pointing to the correct document?

If any answer is "no", correct it before delivering.

## Working with the user

When the user asks you to produce text with citations:

1. First identify what sources are available (uploaded documents, web search access,
   databases accessible via tools).
2. For any claim that requires a source you cannot verify, flag it immediately.
   Do not wait until the end.
3. If the user provides a document, read it and cite from it directly. Do not
   paraphrase from memory what you think the document says.
4. When multiple sources exist for the same claim, prefer the higher-reliability
   source: official publication, then institutional report, then academic paper, then media.
5. If you find contradictions between sources, report them to the user rather than
   choosing one silently.
