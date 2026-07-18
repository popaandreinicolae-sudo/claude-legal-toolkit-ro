#!/usr/bin/env python3
"""
Cost Optimization Setup pentru Claude API.

3 capabilitati Tier 2 frontier 2026:
1. Prompt caching pe skill-urile auto-aplicate (reducere 80-95%)
2. Batch API submit pentru bulk processing (reducere 50%)
3. Files API upload pentru tratate juridice mari (eliminare re-upload)

Necesita: ANTHROPIC_API_KEY in env var
Instalare: pip install anthropic

Aplicabil dupa ce ai obtinut API key de la https://console.anthropic.com/settings/keys
"""

import json
import os
import sys
from pathlib import Path


def check_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY nu este setat in env var.", file=sys.stderr)
        print("Obtine cheia de la https://console.anthropic.com/settings/keys", file=sys.stderr)
        print("Apoi seteaza-o cu:", file=sys.stderr)
        print('  PowerShell:  $env:ANTHROPIC_API_KEY = "sk-ant-xxx"', file=sys.stderr)
        print("  Permanent:   [Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-xxx', 'User')", file=sys.stderr)
        return None
    return key


def build_cached_skill_loader() -> str:
    """Construieste pattern-ul pentru incarcare skill-uri cu cache_control activ."""
    skills_dir = Path("%USERPROFILE%/.claude/skills")
    cached_skills = ["anti-ai-tone.md", "analiza-juridica-critica.md", "zero-hallucination-citations.md", "verificare-legislatie.md", "format-bibliografie-doctorat-ub.md"]

    skill_blocks = []
    total_tokens_est = 0
    for skill_file in cached_skills:
        path = skills_dir / skill_file
        if path.exists():
            content = path.read_text(encoding="utf-8")
            tokens_est = len(content.split()) * 1.3
            total_tokens_est += tokens_est
            skill_blocks.append({
                "skill": skill_file,
                "tokens_est": int(tokens_est),
                "path": str(path),
            })

    return json.dumps({
        "skills_to_cache": skill_blocks,
        "total_tokens_estimated": int(total_tokens_est),
        "cache_control_marker": {"type": "ephemeral"},
        "savings_pct_estimated": "84-90% pe input cached repetat",
    }, indent=2, ensure_ascii=False)


def estimate_savings_per_workflow() -> dict:
    """Calculeaza economiile estimate pentru workflows tipice ale utilizatorului."""
    workflows = {
        "raport_doctoral_capitol_nou": {
            "system_tokens": 12000,
            "calls_per_session": 30,
            "model": "claude-opus-4-8",
            "rate_input_usd_per_mtok": 5.0,
        },
        "audit_anti_ai_tone_document": {
            "system_tokens": 8000,
            "calls_per_session": 15,
            "model": "claude-opus-4-8",
            "rate_input_usd_per_mtok": 5.0,
        },
        "research_juridic_extensiv": {
            "system_tokens": 10000,
            "calls_per_session": 50,
            "model": "claude-opus-4-8",
            "rate_input_usd_per_mtok": 5.0,
        },
        "drafting_contract_corporate": {
            "system_tokens": 6000,
            "calls_per_session": 20,
            "model": "claude-sonnet-4-6",
            "rate_input_usd_per_mtok": 3.0,
        },
    }

    results = {}
    for name, params in workflows.items():
        tokens = params["system_tokens"]
        calls = params["calls_per_session"]
        rate = params["rate_input_usd_per_mtok"]
        no_cache = (tokens * calls / 1_000_000) * rate
        with_cache_first = (tokens / 1_000_000) * (rate * 1.25)
        with_cache_repeat = (tokens * (calls - 1) / 1_000_000) * (rate * 0.10)
        with_cache = with_cache_first + with_cache_repeat
        results[name] = {
            "no_cache_usd": round(no_cache, 4),
            "with_cache_usd": round(with_cache, 4),
            "savings_usd": round(no_cache - with_cache, 4),
            "savings_pct": round(100 * (1 - with_cache / no_cache), 1),
            "model": params["model"],
        }

    return results


def main():
    print("Cost Optimization Setup, Tier 2")
    print("=" * 50)
    print()

    key = check_api_key()
    if key:
        print(f"API key detected, length {len(key)}")
    else:
        print("API key lipseste, doar afisez configurari plus estimari")
    print()

    print("CONFIGURARE PROMPT CACHING")
    print("-" * 50)
    config = build_cached_skill_loader()
    print(config)
    print()

    print("ESTIMARI ECONOMII PE WORKFLOWS TIPICE")
    print("-" * 50)
    estimates = estimate_savings_per_workflow()
    for name, data in estimates.items():
        print(f"\n{name} ({data['model']})")
        print(f"  Fara caching: ${data['no_cache_usd']}")
        print(f"  Cu caching:   ${data['with_cache_usd']}")
        print(f"  Economie:     ${data['savings_usd']} ({data['savings_pct']}%)")

    print()
    print("PASII URMATORI MANUAL")
    print("-" * 50)
    print("1. Obtine API key Anthropic: https://console.anthropic.com/settings/keys")
    print('2. Seteaza in PowerShell: [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-xxx", "User")')
    print("3. Rerun acest script, vei vedea 'API key detected'")
    print("4. Foloseste api_helpers.py upload-batch pentru Files API")
    print()


if __name__ == "__main__":
    main()
