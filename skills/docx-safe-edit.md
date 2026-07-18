---
name: docx-safe-edit
description: >
  Safe DOCX editing protocol — edit footnotes and body text without corrupting the document.
  ALWAYS use this protocol when modifying DOCX files.
---

# Safe DOCX Editing Protocol

## REGULA #1: BACKUP INAINTE DE ORICE MODIFICARE

```python
import shutil
shutil.copy2('input.docx', 'input_BACKUP.docx')
```

## REGULA #2: EDITARE FOOTNOTES PRIN LXML (nu python-docx)

python-docx NU are API nativ pentru footnotes. Foloseste lxml direct:

```python
import zipfile, io, shutil, os
from lxml import etree
from copy import deepcopy

def edit_footnote(docx_path, footnote_number, new_text, output_path):
    """Edit a specific footnote by number. Safe — works on copy."""
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    # Copy original
    shutil.copy2(docx_path, output_path)
    
    # Read and modify footnotes.xml
    with zipfile.ZipFile(output_path, 'r') as zin:
        fn_xml = zin.read('word/footnotes.xml')
    
    tree = etree.fromstring(fn_xml)
    footnotes = [f for f in tree.findall(f'.//{ns}footnote') if f.get(f'{ns}type') is None]
    
    if footnote_number < 1 or footnote_number > len(footnotes):
        raise ValueError(f"Footnote {footnote_number} not found (total: {len(footnotes)})")
    
    fn = footnotes[footnote_number - 1]
    
    # Clear existing paragraphs (keep first for structure)
    paragraphs = fn.findall(f'{ns}p')
    for p in paragraphs[1:]:
        fn.remove(p)
    
    # Set new text in first paragraph
    first_p = paragraphs[0]
    for r in first_p.findall(f'{ns}r'):
        # Skip footnote reference run
        if r.find(f'{ns}footnoteRef') is not None:
            continue
        t = r.find(f'{ns}t')
        if t is not None:
            t.text = new_text
            new_text = ""  # Only set once
    
    # Write back
    new_fn_xml = etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
    
    # Replace in zip
    _replace_in_zip(output_path, 'word/footnotes.xml', new_fn_xml)


def _replace_in_zip(zip_path, target_file, new_content):
    """Replace a single file inside a zip without corrupting other files."""
    temp_path = zip_path + '.tmp'
    with zipfile.ZipFile(zip_path, 'r') as zin:
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == target_file:
                    zout.writestr(item, new_content)
                else:
                    zout.writestr(item, zin.read(item.filename))
    os.replace(temp_path, zip_path)
```

## REGULA #3: EDITARE METADATA

```python
from docx import Document
d = Document('output.docx')
d.core_properties.author = "Andrei Nicolae Popa"
d.core_properties.last_modified_by = "Andrei Nicolae Popa"
d.core_properties.revision = 12
d.save('output.docx')
```

## REGULA #4: VALIDARE DUPA EDITARE

```python
# Test 1: python-docx can open it
from docx import Document
d = Document('output.docx')
print(f"{len(d.paragraphs)} paragraphs OK")

# Test 2: footnotes.xml is valid XML
import zipfile
z = zipfile.ZipFile('output.docx')
from lxml import etree
etree.fromstring(z.read('word/footnotes.xml'))
print("Footnotes XML: valid")

# Test 3: LibreOffice can convert to PDF
import subprocess
r = subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', 'output.docx'], capture_output=True)
print("PDF conversion:", "OK" if r.returncode == 0 else "FAILED")
```

## REGULA #5: NICIODATA

- Nu sterge [Content_Types].xml
- Nu modifica word/_rels/
- Nu schimba structura ZIP-ului
- Nu edita direct cu python-docx daca ai footnotes complexe — foloseste lxml
