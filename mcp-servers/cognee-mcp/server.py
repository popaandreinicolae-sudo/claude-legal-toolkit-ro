#!/usr/bin/env python3
"""
Cognee MCP Server pentru Claude Desktop si Code.

Expune Cognee ca MCP cu 4 tools pentru memorie cross-session:
- cognify, adauga continut in knowledge graph
- search, query knowledge graph cu intrebari natural language
- prune, sterge knowledge graph (reset)
- get_datasets, listeaza dataset-urile existente

Folosit pentru research juridic doctoral cu memorie persistenta intre sesiuni.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

os.environ.setdefault("COGNEE_DATA_PATH", str(Path.home() / ".cognee"))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import cognee

app = Server("cognee-legal")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="cognify",
            description=(
                "Adauga continut in knowledge graph-ul cognee. "
                "Foloseste pentru a memora research juridic, decizii CCR analizate, citate doctrinari, "
                "rezumate hotarari CEDO pentru reutilizare in sesiuni viitoare."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Textul de adaugat in knowledge graph",
                    },
                    "dataset": {
                        "type": "string",
                        "default": "legal-research",
                        "description": "Nume dataset, separa domenii (legal-research, doctorat, proiect-A, etc.)",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search",
            description=(
                "Cauta in knowledge graph cu intrebare natural language. "
                "Returneaza fragmente relevante plus relatiile dintre ele."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Intrebare in limba naturala despre continutul memorat",
                    },
                    "dataset": {"type": "string", "default": "legal-research"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="prune",
            description="Sterge knowledge graph (reset). Folosit cu atentie, sterge ireversibil.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_datasets",
            description="Listeaza dataset-urile existente in knowledge graph local.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "cognify":
            content = arguments.get("content", "")
            dataset = arguments.get("dataset", "legal-research")
            await cognee.add(content, dataset_name=dataset)
            await cognee.cognify([dataset])
            return [TextContent(type="text", text=f"OK adaugat in dataset '{dataset}', {len(content)} caractere indexate.")]

        if name == "search":
            query = arguments.get("query", "")
            dataset = arguments.get("dataset", "legal-research")
            results = await cognee.search(query_text=query, datasets=[dataset])
            if not results:
                return [TextContent(type="text", text="Niciun rezultat in knowledge graph.")]
            output = [f"Rezultate cautare '{query}' in {dataset}:\n"]
            for i, r in enumerate(results[:10], 1):
                output.append(f"{i}. {str(r)[:300]}")
            return [TextContent(type="text", text="\n".join(output))]

        if name == "prune":
            await cognee.prune.prune_data()
            await cognee.prune.prune_system(metadata=True)
            return [TextContent(type="text", text="Knowledge graph reset complet.")]

        if name == "get_datasets":
            data_path = Path(os.environ["COGNEE_DATA_PATH"])
            if not data_path.exists():
                return [TextContent(type="text", text="Niciun dataset existent inca.")]
            datasets = [d.name for d in data_path.iterdir() if d.is_dir()]
            return [TextContent(type="text", text=f"Datasets active: {', '.join(datasets) if datasets else 'niciunul'}")]

        return [TextContent(type="text", text=f"Tool necunoscut: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"EROARE: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
