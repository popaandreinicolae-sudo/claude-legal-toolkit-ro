---
name: docx-safe-edit
description: >
  Protocol de siguranta la editarea unui .docx existent, ca documentul sa nu se corupa
  si ca metadatele sa ramana corecte. Declanseaza la "editeaza docx", "modifica
  documentul Word", "schimba nota de subsol", "corecteaza .docx", oriunde se scrie
  intr-un fisier Word primit. Se aseaza sub docx-track-changes, ca plasa de siguranta.
---

# Editare .docx fara sa strici documentul

## Unde se aseaza

Traseul principal pentru revizuirea unui document primit ramane
`docx-track-changes`, cu garantiile lui verificate prin selftest, Reject All reproduce
originalul si Accept All produce varianta ceruta. Protocolul de aici acopera restul,
adica situatiile in care trebuie sa umbli direct in XML, si tine regulile care nu se
schimba indiferent de traseu.

## Regula 1, copie inainte de orice

```python
import shutil
shutil.copy2("input.docx", "input_BACKUP.docx")
```

Se lucreaza pe copie. Documentul primit ramane intact pe disc, ca sa poti compara si ca
sa poti relua daca editarea iese prost.

## Regula 2, notele de subsol se editeaza prin lxml

python-docx nu are API nativ pentru note de subsol, iar incercarea de a le atinge prin
el rupe relatiile din pachet. Lucreaza direct pe `word/footnotes.xml`.

```python
import zipfile, os, shutil
from lxml import etree

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def edit_footnote(docx_path, footnote_number, new_text, output_path):
    """Schimba textul unei note, dupa numarul ei vizibil. Lucreaza pe copie."""
    shutil.copy2(docx_path, output_path)

    with zipfile.ZipFile(output_path) as zin:
        fn_xml = zin.read("word/footnotes.xml")

    tree = etree.fromstring(fn_xml)
    notes = [f for f in tree.findall(f".//{NS}footnote") if f.get(f"{NS}type") is None]

    if not 1 <= footnote_number <= len(notes):
        raise ValueError(f"Nota {footnote_number} nu exista (total: {len(notes)})")

    fn = notes[footnote_number - 1]
    paragraphs = fn.findall(f"{NS}p")
    for p in paragraphs[1:]:
        fn.remove(p)

    for r in paragraphs[0].findall(f"{NS}r"):
        if r.find(f"{NS}footnoteRef") is not None:
            continue
        t = r.find(f"{NS}t")
        if t is not None:
            t.text = new_text
            new_text = ""

    out = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    _replace_in_zip(output_path, "word/footnotes.xml", out)


def _replace_in_zip(zip_path, target, content):
    """Inlocuieste un singur fisier din arhiva, fara sa atinga restul."""
    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(zip_path) as zin, \
         zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, content if item.filename == target else zin.read(item.filename))
    os.replace(tmp, zip_path)
```

Cand modificarea trebuie sa apara ca revizie urmarita, nu edita nota direct. Textul
notelor existente se schimba cu `docx_track_changes.py`, iar notele noi se adauga cu
`docx_footnotes.py`. Editarea directa de aici lasa modificarea invizibila in redline.

## Regula 3, metadatele

Documentul primit isi pastreaza autorul. Cine l-a creat ramane scris in fisier, fiindca
proprietatile documentului spun cine l-a facut, nu cine l-a atins ultimul. Se schimba
numai cine l-a modificat.

```python
from docx import Document

d = Document("output.docx")
d.core_properties.last_modified_by = "Adrian Zamfir"
# d.core_properties.author ramane neatins pe un document primit
d.save("output.docx")
```

Pe un document scris de la zero, ambele campuri poarta numele tau, vezi `docx-footnotes`.

Nu scrie un `revision` inventat. Un numar de revizii fabricat falsifica istoricul de
editare al fisierului si nu aduce nimic documentului.

Cand documentul pleaca la o autoritate sau la partea adversa, verifica si ce a ramas in
el pe langa text, comentarii vechi, autori de revizii din alte cabinete, cai de fisier
in proprietatile personalizate. `docx-livrare-check` face lista completa.

## Regula 4, validare dupa editare

```python
# 1. se deschide cu python-docx
from docx import Document
d = Document("output.docx")
print(f"{len(d.paragraphs)} paragrafe OK")

# 2. XML-ul notelor e valid
import zipfile
from lxml import etree
z = zipfile.ZipFile("output.docx")
etree.fromstring(z.read("word/footnotes.xml"))
print("footnotes.xml valid")

# 3. LibreOffice il converteste, deci Word il deschide
import subprocess
r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "output.docx"],
                   capture_output=True)
print("conversie PDF:", "OK" if r.returncode == 0 else "ESUATA")
```

Testul trei are nevoie de LibreOffice instalat. Daca lipseste, spune asta explicit in
raport, nu trece verificarea ca facuta.

## Regula 5, niciodata

- Nu sterge `[Content_Types].xml`.
- Nu modifica `word/_rels/`.
- Nu schimba structura arhivei ZIP, nici ordinea intrarilor.
- Nu edita cu python-docx un document cu note de subsol complexe, foloseste lxml.
- Nu recomasa paragrafele autorului. Un citat pus in trei paragrafe ramane in trei.
- Nu inlocui un `<w:r>` intreg pentru un cuvant schimbat. Sparge run-ul in trei, altfel
  marcajul iese lat si pierde bold-ul termenului definit.
