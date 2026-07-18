#!/usr/bin/env python3
"""
Helper scripts pentru optimizarea costurilor Anthropic API.

3 capabilitati:
1. Prompt caching, reducere 80-95% cost input pe skill-uri repetitiv incarcate
2. Files API, upload tratate juridice mari o singura data, reutilizare permanenta
3. Citations API, integrare native pentru raspunsuri source-grounded

Necesita: ANTHROPIC_API_KEY in env var.
Instalare: pip install anthropic
"""

import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Instaleaza SDK: pip install anthropic", file=sys.stderr)
    sys.exit(1)


def get_client() -> "anthropic.Anthropic":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY nu este setat in env var.", file=sys.stderr)
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def upload_file_to_files_api(file_path: Path) -> str:
    """Upload PDF, DOCX, sau CSV la Files API. Returneaza file_id permanent."""
    client = get_client()

    if not file_path.exists():
        raise FileNotFoundError(f"Fisierul nu exista: {file_path}")

    with file_path.open("rb") as f:
        result = client.files.create(
            file=(file_path.name, f, "application/octet-stream"),
            extra_headers={"anthropic-beta": "files-api-2025-04-14"},
        )

    print(f"Upload reusit: {file_path.name}")
    print(f"file_id: {result.id}")
    print(f"  - reutilizeaza prin: \"source\": {{\"type\": \"file\", \"file_id\": \"{result.id}\"}}")
    return result.id


def message_with_caching(system_prompt: str, user_message: str, files: list[str] | None = None) -> dict:
    """
    Trimite mesaj cu prompt caching activ pe system prompt.
    Reducere cost: 80-95% pentru cache hits dupa primul apel.
    """
    client = get_client()

    system_blocks = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    content = [{"type": "text", "text": user_message}]
    if files:
        for fid in files:
            content.insert(0, {"type": "document", "source": {"type": "file", "file_id": fid}})

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=system_blocks,
        messages=[{"role": "user", "content": content}],
    )

    print(f"Input tokens: {response.usage.input_tokens}")
    print(f"Cache read tokens: {getattr(response.usage, 'cache_read_input_tokens', 0)}")
    print(f"Cache create tokens: {getattr(response.usage, 'cache_creation_input_tokens', 0)}")
    print(f"Output tokens: {response.usage.output_tokens}")

    return response.model_dump()


def message_with_citations(system_prompt: str, user_message: str, source_files: list[str]) -> dict:
    """
    Trimite mesaj cu Citations API activ.
    Fiecare afirmatie din raspuns este legata de fragment sursa.
    Util pentru research juridic plus rapoarte cu cifre verificabile.
    """
    client = get_client()

    content = []
    for fid in source_files:
        content.append({
            "type": "document",
            "source": {"type": "file", "file_id": fid},
            "citations": {"enabled": True},
        })
    content.append({"type": "text", "text": user_message})

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )

    return response.model_dump()


def upload_legal_corpus_batch(corpus_dir: Path, output_manifest: Path) -> dict:
    """
    Upload bulk al unui corpus juridic (PDF-uri tratate, decizii) in Files API.
    Genereaza manifest cu file_id-uri permanente pentru reutilizare.
    """
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Directorul corpus nu exista: {corpus_dir}")

    manifest = {"uploaded_at": "", "files": []}
    for f in sorted(corpus_dir.glob("*")):
        if f.suffix.lower() not in {".pdf", ".docx", ".csv", ".txt", ".md"}:
            continue
        try:
            file_id = upload_file_to_files_api(f)
            manifest["files"].append({
                "filename": f.name,
                "file_id": file_id,
                "size_bytes": f.stat().st_size,
            })
        except Exception as e:
            print(f"Eroare upload {f.name}: {e}", file=sys.stderr)

    output_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifest salvat: {output_manifest}")
    print(f"Total fisiere uploadate: {len(manifest['files'])}")
    return manifest


def estimate_caching_savings(system_prompt_tokens: int, calls_per_session: int, opus_input_rate: float = 5.0) -> dict:
    """
    Estimeaza economiile prin prompt caching.
    Rate: 5 USD per Mtok input pentru Opus 4.8, 0.50 USD cache read (90% off).
    """
    write_cost_per_mtok = opus_input_rate * 1.25
    read_cost_per_mtok = opus_input_rate * 0.10

    no_cache_cost = (system_prompt_tokens * calls_per_session / 1_000_000) * opus_input_rate
    with_cache_first = (system_prompt_tokens / 1_000_000) * write_cost_per_mtok
    with_cache_repeat = (system_prompt_tokens * (calls_per_session - 1) / 1_000_000) * read_cost_per_mtok
    with_cache_total = with_cache_first + with_cache_repeat

    return {
        "system_prompt_tokens": system_prompt_tokens,
        "calls_per_session": calls_per_session,
        "no_cache_cost_usd": round(no_cache_cost, 4),
        "with_cache_cost_usd": round(with_cache_total, 4),
        "savings_usd": round(no_cache_cost - with_cache_total, 4),
        "savings_pct": round(100 * (1 - with_cache_total / no_cache_cost), 1) if no_cache_cost > 0 else 0,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Helper Anthropic API, caching plus Files plus Citations")
    sub = parser.add_subparsers(dest="cmd")

    p_up = sub.add_parser("upload", help="Upload single file la Files API")
    p_up.add_argument("file", type=Path)

    p_batch = sub.add_parser("upload-batch", help="Upload bulk corpus")
    p_batch.add_argument("dir", type=Path)
    p_batch.add_argument("--manifest", type=Path, default=Path("files-manifest.json"))

    p_est = sub.add_parser("estimate-savings", help="Estimeaza economii cu prompt caching")
    p_est.add_argument("--tokens", type=int, required=True, help="Tokens system prompt")
    p_est.add_argument("--calls", type=int, default=10, help="Apeluri per sesiune")

    args = parser.parse_args()

    if args.cmd == "upload":
        upload_file_to_files_api(args.file)
    elif args.cmd == "upload-batch":
        upload_legal_corpus_batch(args.dir, args.manifest)
    elif args.cmd == "estimate-savings":
        result = estimate_caching_savings(args.tokens, args.calls)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
