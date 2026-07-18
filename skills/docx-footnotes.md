---
name: docx-footnotes
description: >
  Generate professional DOCX documents with proper footnotes using python-docx.
  Triggers: "genereaza docx", "creaza document word", "docx cu note de subsol", "livrare docx".
---

# DOCX + Footnotes Generator

## FORMAT DOCTORAL UB DREPT

### Corp text
- Font: Times New Roman 12pt
- Justified
- Line spacing: 1.5
- First line indent: 1.27 cm
- Margini: 2.5 cm sus/jos, 3 cm stanga, 2 cm dreapta

### Note de subsol
- Font: Times New Roman 10pt
- Justified
- Line spacing: simplu (1.0)
- Referinta in text: superscript automat

### Titluri
- Capitol: TNR 14pt bold, centrat
- Subcapitol: TNR 12pt bold, stanga
- Sub-subcapitol: TNR 12pt bold italic, stanga

### Numerotare pagini
- Pozitie: jos, centru
- Font: TNR 11pt

## IMPLEMENTARE python-docx

```python
from docx import Document
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

# Margini
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2)

# Stil corp
style = doc.styles['Normal']
font = style.font
font.name = 'Times New Roman'
font.size = Pt(12)
pf = style.paragraph_format
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.line_spacing = 1.5
pf.first_line_indent = Cm(1.27)

# Nota de subsol
footnote = doc.add_footnote("Text nota")  # Necesita docx-footnotes helper
```

## METADATA ANTI-AI

```python
from docx.opc.constants import RELATIONSHIP_TYPE as RT
core = doc.core_properties
core.author = "Andrei Nicolae Popa"
core.last_modified_by = "Andrei Nicolae Popa"
core.revision = 12
core.comments = ""
```

## REGULI
1. Nu genera docx de la zero daca exista deja — editeaza documentul existent
2. Pastreaza footnotes existente — nu le rescrie daca nu e necesar
3. Testeaza deschiderea inainte de livrare
4. Elimina tracked changes si comentarii
