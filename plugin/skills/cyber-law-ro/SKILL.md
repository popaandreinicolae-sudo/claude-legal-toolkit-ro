---
name: cyber-law-ro
description: |
  Analiza si redactare in dreptul securitatii cibernetice romanesti, transpunerea NIS2, legislatia specifica DNSC, infrastructura critica. APLICA AUTOMAT la sarcini cu Legea 58/2023, OUG 155/2024, Directiva NIS2, GDPR plus securitate cibernetica, incidente cibernetice, operatori esentiali, operatori importanti. Triggere: "Legea 58/2023", "OUG 155/2024", "DNSC", "NIS2", "securitate cibernetica", "incident cibernetic", "infrastructura critica", "operator esential", "operator important", "raportare incidente", "atac cibernetic", "ransomware", "phishing", "vulnerabilitate", "amenintare cibernetica", "rezilienta cibernetica", "CSIRT". Pipeline cu legal-verificator-ro pentru validare acte normative.
version: 1.0
last_updated: 2026-06-01
parent_skill: constitutional-law-ro
---

# Cyber Law Romania

Skill specializat pentru drept cibernetic romanesc, transpunerea NIS2 in legislatia nationala, regimul juridic DNSC, sanctiuni contraventionale, raportare incidente.

## Cadrul juridic actual (2024-2026)

### Legea 58/2023, securitate si aparare cibernetica

Lege adoptata 2023, transpune directiva NIS2 in legislatia romaneasca. Subiect Decizia CCR 70/2023 (respingere obiectie de neconstitutionalitate).

Categorii destinatari:
- Operatori esentiali, lista in HG subsecvent
- Operatori importanti, lista in HG subsecvent
- Autoritati publice cu obligatii specifice

Definitii cheie:
- Securitate cibernetica, art. 2 lit. y, stare de normalitate (sintagma controversata, fara echivalent in dreptul UE)
- Atac cibernetic, art. 2 lit. d
- Incident cibernetic, art. 2 lit. h
- Vulnerabilitate, art. 2 lit. ag

Vezi `references/legea-58-2023-articole.md` pentru extrase cheie.

### OUG 155/2024, masuri suplimentare securitate cibernetica

Adoptata 2024, completeaza Legea 58/2023. Introduce obligatii suplimentare pe monitorizarea retelelor, art. 21. Sanctiuni contraventionale pana la zeci de mii de lei.

Probabilitate inalta de sesizare CCR pe motiv calitate legii.

### Legea 51/1991, siguranta nationala (in vigoare actualizata)

Cadrul general pentru activitati de informatii. Mandatul de securitate nationala (art. 13), eliberat de Inalta Curte de Casatie si Justitie. Distinctie clara intre securitate cibernetica (Legea 58/2023) plus informatii cibernetice (Legea 51/1991).

### Legea 362/2018, prima transpunere NIS1

Transpunere directiva NIS1, inlocuita partial de Legea 58/2023. Verifica prevederile inca in vigoare prin MCP legal-verificator-ro.

## Cadrul UE

Vezi `references/directive-ue-cyber.md` pentru detalii.

- Directiva NIS2 (UE) 2022/2555, transpusa prin Legea 58/2023
- Regulamentul GDPR (UE) 2016/679
- Directiva 2002/58/CE comunicatii electronice
- AI Act (UE) 2024/1689 cu impact pe sisteme AI utilizate in securitate
- CER Directiva (UE) 2022/2557 rezilienta entitati critice

## Autoritati implicate

DNSC, Directoratul National de Securitate Cibernetica. Autoritate competenta principala. Atributii: monitorizare, raportare incidente, sanctiuni contraventionale, cooperare ENISA.

ANCOM, comunicatii electronice. Competenta retele publice de comunicatii.

ANSPDCP, protectia datelor. Competenta GDPR.

SRI, prin departamentul informatii cibernetice. Competenta amenintari la securitatea nationala.

## Termene cheie de raportare

Vezi `references/termene-raportare.md` pentru tabel complet.

- Notificare incident DNSC, 24 ore de la detectie pentru incidente majore
- Raportare detaliata, 72 ore
- Raport final, 30 zile
- ANSPDCP pentru date personale, 72 ore conform GDPR art. 33

## Sanctiuni contraventionale

Vezi `references/sanctiuni-58-2023.md` pentru detalii.

Cuantum maxim, zeci de mii de lei pentru operatori esentiali. Criterii: gravitate incident, recurenta, cifra de afaceri.

## Problema constitutionala critica

Identificarea destinatarului substantial al normei printr-un act administrativ subsecvent (HG) ridica problema calitatii legii.

Decizia CCR 70/2023 a respins obiectia (control a priori), majoritatea considerand legea suficient previzibila. Opinia separata sustine ca trimiterea la legislatia infralegala pentru identificarea destinatarului sanctionator nu indeplineste cerinta de previzibilitate.

Analiza acestei tensiuni: vezi `references/calitatea-legii-cyber.md`.

## Anti-halucinare specifica

NU inventa:
- Numere de articole din Legea 58/2023 sau OUG 155/2024 fara verificare
- Termene de raportare diferite de cele oficiale
- Sanctiuni cu cuantum specific fara articol citat
- Decizii CCR sau hotarari CEDO pe cyber fara verificare prin MCP

Marcheaza [VERIFICARE NECESARA prin mcp__legal-verificator-ro] daca nu ai sursa primara confirmata.

## Pipeline

- `constitutional-law-ro` pentru ancorare in drept constitutional
- `anti-hallucination-document` pentru fact-check
- `ub-drept-citation` pentru citare bibliografica
- MCP `legal-verificator-ro` pentru verificare acte normative
- MCP `eurlex` pentru verificare directive UE
