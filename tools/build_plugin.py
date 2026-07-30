#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_plugin.py

Impacheteaza configuratia vie din ~/.claude ca plugin Claude Code, ca aceleasi
skill-uri, subagenti si hook-uri sa ajunga si pe suprafetele unde fisierele din
~/.claude nu se citesc, adica in Claude Desktop si in Cowork.

O SINGURA SURSA DE ADEVAR. Nu tine liste proprii. Citeste ce e instalat efectiv:
skill-urile din ~/.claude/skills, subagentii din ~/.claude/agents si hook-urile
declarate in ~/.claude/settings.json. Cand configurarea de aici se schimba, rulezi
scriptul din nou si pachetul o urmeaza. Directorul `plugin/` este artefact generat,
nu se editeaza de mana.

Caile din hook-uri se rescriu pe ${CLAUDE_PLUGIN_ROOT}, fiindca in masina virtuala
Cowork caile absolute de Windows nu exista. Interpretorul se alege la rulare, printr-un
shim, ca acelasi pachet sa mearga si pe Windows si pe Linux.

    python tools/build_plugin.py
    python tools/build_plugin.py --verifica    # raporteaza, nu scrie
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACASA = Path(os.path.expanduser("~")) / ".claude"
IESIRE = REPO / "plugin"

NUME = "toolkit-juridic-ro"


def versiune() -> str:
    """Versiune care creste singura la fiecare commit.

    Claude Desktop decide daca are ce actualiza comparand versiunile, iar butonul
    Update ramane inactiv cand ele coincid. Un numar fix ar bloca orice reparatie
    ulterioara in exact aceeasi capcana, asa ca il legam de numarul de commituri.
    """
    try:
        n = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"1.0.{int(n)}"
    except Exception:  # noqa: BLE001
        return "1.0.0"


VERSIUNE = versiune()

IGNORA = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.bak", "*.log", "*.tmp",
    ".session", ".citation_cache.json", "session_audit.log",
    # Copiile lasate de repara_pachet.py inainte de a repara un fisier. Nu au ce cauta
    # intr-un pachet distribuit, cu atat mai putin un sablon rupt, adica exact ce am
    # scos din drum.
    "*.inainte-de-reparatie*",
)

def docx_rupte(rad) -> list:
    """Sabloanele .docx din pachet pe care Word le va refuza.

    Word raspunde "Word found unreadable content" cand atributul Ignorable din spatiul
    Markup Compatibility enumera un prefix pe care radacina nu il declara. Un sablon
    rupt trimis in pachet strica fiecare document generat din el, pe fiecare masina
    care instaleaza plugin-ul. Lectie platita pe 29 iulie 2026.
    """
    import re as _re
    import zipfile as _zip

    rupte = []
    for docx in Path(rad).rglob("*.docx"):
        try:
            with _zip.ZipFile(docx) as z:
                for parte in z.namelist():
                    if not (parte.startswith("word/") and parte.endswith(".xml")):
                        continue
                    xml = z.read(parte).decode("utf-8", "replace")
                    i = xml.find("<w:")
                    if i < 0:
                        continue
                    root = xml[i:xml.find(">", i) + 1]
                    declarate = set(_re.findall(r'xmlns:([A-Za-z0-9_]+)=', root))
                    ign = _re.search(r'([A-Za-z0-9_]+):Ignorable="([^"]*)"', root)
                    if ign:
                        lipsa = [p for p in ign.group(2).split() if p not in declarate]
                        if lipsa:
                            rupte.append("%s :: %s (%s)"
                                         % (docx.name, parte, " ".join(lipsa)))
        except _zip.BadZipFile:
            rupte.append("%s :: arhiva invalida" % docx.name)
    return rupte


# Fisierele din hooks/ care nu au ce cauta intr-un pachet distribuit.
HOOKS_EXCLUSE = {
    "session_audit.log", ".citation_cache.json", "_martor_citari.md",
    "cost_optimization_setup.py",
}

# Sir brut: secventele \\ trebuie sa ajunga in fisier exact asa, pentru expresia sed.
SHIM = r"""#!/bin/sh
# Alege interpretorul disponibil. Pachetul ruleaza si pe Windows, unde comanda e
# `python`, si in masina virtuala Cowork, unde e `python3`.
#
# Iesire 0 cand nu gaseste niciunul: stratul anti-halucinare e fail-open prin
# constructie, deci un hook care nu poate rula raporteaza curat in loc sa blocheze
# sesiunea. Vezi hooks/SYSTEM_CONTRACT.md.
d=$(dirname "$0")
s=$1
shift

# Claude Desktop instalat din Microsoft Store e pachet MSIX. ${CLAUDE_PLUGIN_ROOT} arata
# catre AppData\Roaming\Claude, dar fisierele stau efectiv sub
# AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude.
#
# Ordinea de mai jos nu e intamplatoare. `sh` vede calea redirectionata si citeste acest
# script de acolo fara probleme, dar `python.exe`, lansat ca proces nativ in afara
# containerului, primeste acelasi sir si nu gaseste nimic. Verificat pe eroarea reala:
# comanda pornea, iar Python raporta [Errno 2] pe calea din Roaming. Deci calea tradusa
# are prioritate, chiar daca testul pe cea primita ar trece.
#
# Cand aplicatia reuseste sa puna plugin-ul pe calea scurta din Temp, prin symlink,
# tiparul nu se potriveste, traducerea nu schimba nimic si ramane calea primita.
alt=$(printf '%s' "$d" | sed 's#[Aa]pp[Dd]ata[/\\][Rr]oaming[/\\][Cc]laude[/\\]#AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude/#')
if [ -f "$alt/$s" ]; then
  d=$alt
elif [ ! -f "$d/$s" ]; then
  # Scriptul nu exista nicaieri, deci nu avem ce rula. Iesire curata, fara zgomot.
  exit 0
fi

for p in python3 python py; do
  if command -v "$p" >/dev/null 2>&1; then
    exec "$p" "$d/$s" "$@"
  fi
done
exit 0
"""


def citeste_json(cale: Path):
    return json.loads(cale.read_text(encoding="utf-8"))


def hookuri_din_settings(settings: dict) -> tuple[dict, set[str]]:
    """Rescrie comenzile pe cai portabile si intoarce si scripturile referite."""
    rezultat = {}
    scripturi: set[str] = set()
    for eveniment, reguli in settings.get("hooks", {}).items():
        reguli_noi = []
        for regula in reguli:
            intrari = []
            for h in regula.get("hooks", []):
                cmd = h.get("command", "")
                m = re.search(r"([\w_]+\.py)", cmd)
                if not m:
                    continue
                script = m.group(1)
                if script in HOOKS_EXCLUSE:
                    continue
                scripturi.add(script)
                intrari.append({
                    "type": "command",
                    "command": f'sh "${{CLAUDE_PLUGIN_ROOT}}/hooks/ruleaza.sh" {script}',
                    **({"timeout": h["timeout"]} if "timeout" in h else {}),
                })
            if intrari:
                reguli_noi.append({"matcher": regula.get("matcher", ".*"), "hooks": intrari})
        if reguli_noi:
            rezultat[eveniment] = reguli_noi
    return rezultat, scripturi


def copiaza_arbore(sursa: Path, tinta: Path) -> int:
    if tinta.exists():
        shutil.rmtree(tinta)
    shutil.copytree(sursa, tinta, ignore=IGNORA)
    return sum(1 for _ in tinta.rglob("*") if _.is_file())


def intoarce_in_repo(instalate: Path, in_repo: Path) -> list:
    """Aduce in repo skill-urile modificate direct in ~/.claude/skills.

    Bucla avea doua capete care aratau in directii opuse. Constructorul citeste
    skill-urile instalate, iar sync-claude.ps1 le scrie in sens invers, din repo peste
    cele instalate. O modificare facuta in ~/.claude si nepusa in repo supravietuia deci
    pana la prima sincronizare de dupa un git pull, care o stergea in tacere.

    Verificat pe 30 iulie 2026: regulile despre sintact adaugate in source-pack-grounding
    si verificare-citari-gate erau numai in copia instalata, iar in repo statea versiunea
    din 27 iulie.

    Compararea se face pe continut normalizat, ca diferentele de sfarsit de linie sa nu
    treaca drept modificari.
    """
    def normal(cale: Path) -> bytes:
        date = cale.read_bytes()
        return date.replace(b"\r\n", b"\n") if cale.suffix in (".md", ".py", ".json", ".txt") else date

    aduse = []
    for f in instalate.rglob("*"):
        if f.is_dir() or "__pycache__" in str(f) or f.suffix == ".pyc":
            continue
        tinta = in_repo / f.relative_to(instalate)
        if tinta.exists() and normal(tinta) == normal(f):
            continue
        tinta.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, tinta)
        aduse.append(str(f.relative_to(instalate)))
    if aduse:
        print("  skill-uri aduse din ~/.claude in repo: %s" % ", ".join(aduse[:6])
              + (" si inca %d" % (len(aduse) - 6) if len(aduse) > 6 else ""))
    return aduse


def main() -> int:
    doar_verifica = "--verifica" in sys.argv

    skills_sursa = ACASA / "skills"
    agents_sursa = ACASA / "agents"
    hooks_sursa = REPO / "hooks"
    settings = citeste_json(ACASA / "settings.json")

    skilluri = sorted(d.name for d in skills_sursa.iterdir()
                      if d.is_dir() and (d / "SKILL.md").exists())
    agenti = sorted(f.name for f in agents_sursa.glob("*.md"))
    hooks_cfg, scripturi = hookuri_din_settings(settings)

    print(f"skill-uri: {len(skilluri)}")
    print(f"subagenti: {len(agenti)}")
    print(f"hook-uri:  {sum(len(v) for v in hooks_cfg.values())} pe {len(hooks_cfg)} evenimente")
    print(f"scripturi de hook: {', '.join(sorted(scripturi))}")

    if doar_verifica:
        print(f"\n(verificare, nu am scris nimic in {IESIRE})")
        return 0

    if IESIRE.exists():
        shutil.rmtree(IESIRE)
    (IESIRE / ".claude-plugin").mkdir(parents=True)

    n_sk = copiaza_arbore(skills_sursa, IESIRE / "skills")
    intoarce_in_repo(skills_sursa, REPO / "skills")
    (IESIRE / "agents").mkdir()
    for a in agenti:
        shutil.copy2(agents_sursa / a, IESIRE / "agents" / a)

    # hooks: intreg directorul, fiindca scripturile se importa intre ele
    tinta_hooks = IESIRE / "hooks"
    tinta_hooks.mkdir()
    for f in hooks_sursa.iterdir():
        if f.name in HOOKS_EXCLUSE or f.name.startswith(".") or f.is_dir():
            continue
        if f.suffix in (".py", ".json", ".md"):
            shutil.copy2(f, tinta_hooks / f.name)

    (tinta_hooks / "ruleaza.sh").write_text(SHIM, encoding="utf-8", newline="\n")
    (tinta_hooks / "hooks.json").write_text(json.dumps({
        "description": (
            "Stratul determinist anti-halucinare si anti-ton-AI al cabinetului. "
            "Verifica citarile juridice prin surse primare, semnaleaza sursele-fantoma, "
            "prinde erorile de ordin de marime si scoreaza naturaletea textului scris. "
            "Hook-urile sunt consultative si fail-open."
        ),
        "hooks": hooks_cfg,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    (IESIRE / ".claude-plugin" / "plugin.json").write_text(json.dumps({
        "name": NUME,
        "version": VERSIUNE,
        "description": (
            "Toolkit juridic si academic in limba romana: redactare pe surse primare, "
            "verificarea citarilor, redline pe .docx cu modificari urmarite, audit de stil "
            "anti-ton-AI si poarta de calitate inainte de livrare. Destinat suprafetelor "
            "unde ~/.claude nu se citeste, Claude Desktop si Cowork."
        ),
        "author": {"name": "Adrian Zamfir"},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    marketplace = REPO / ".claude-plugin"
    marketplace.mkdir(exist_ok=True)
    (marketplace / "marketplace.json").write_text(json.dumps({
        "name": "toolkit-juridic-ro",
        "description": "Toolkit juridic romanesc pentru redactare verificata pe surse primare.",
        "owner": {"name": "Adrian Zamfir"},
        "plugins": [{
            "name": NUME,
            "description": "Skill-uri, subagenti de audit si hook-uri anti-halucinare.",
            "author": {"name": "Adrian Zamfir"},
            "category": "legal",
            "source": "./plugin",
        }],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    rupte = docx_rupte(IESIRE)
    if rupte:
        print("\nPACHETUL NU A FOST ARHIVAT. Sabloane .docx pe care Word le refuza:",
              file=sys.stderr)
        for r in rupte:
            print("  -", r, file=sys.stderr)
        print("Repara cu: python skills/docx-footnotes/scripts/repara_pachet.py "
              "repara --input <fisier>", file=sys.stderr)
        return 1

    # Arhiva pentru "Upload plugin" din Claude Desktop, care cere un fisier, nu un
    # director. Radacina arhivei este chiar radacina plugin-ului, deci `.claude-plugin`
    # sta la primul nivel, asa cum arata un director de plugin pe disc.
    dist = REPO / "dist"
    dist.mkdir(exist_ok=True)
    arhiva = dist / f"{NUME}.zip"
    if arhiva.exists():
        arhiva.unlink()
    shutil.make_archive(str(arhiva.with_suffix("")), "zip", root_dir=IESIRE)

    n_ag = len(agenti)
    n_hk = sum(1 for _ in tinta_hooks.iterdir())
    print(f"\nscris in {IESIRE}")
    print(f"  skills/  {n_sk} fisiere, {len(skilluri)} skill-uri")
    print(f"  agents/  {n_ag} fisiere")
    print(f"  hooks/   {n_hk} fisiere")
    print(f"  marketplace: {marketplace / 'marketplace.json'}")
    print(f"  arhiva:      {arhiva}  ({arhiva.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
