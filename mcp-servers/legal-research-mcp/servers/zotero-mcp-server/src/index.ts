import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { ZoteroClient } from "./services/zotero-client.js";

const server = new Server({ name: "zotero-mcp-server", version: "1.0.0" }, { capabilities: { tools: {} } });
const zotero = new ZoteroClient();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "zotero_search_items",
      description: "Caută referințe bibliografice în biblioteca Zotero. Suportă căutare full-text sau după titlu/autor/an.",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Termeni de căutare" },
          search_mode: { type: "string", enum: ["fulltext", "titleCreatorYear"], description: "Mod de căutare (default: titleCreatorYear)" },
          item_type: { type: "string", description: "Tip: case, statute, journalArticle, book, bookSection, thesis, all" },
          tag: { type: "string", description: "Filtrare după tag" },
          collection_key: { type: "string", description: "Filtrare după colecție (collection key)" },
          limit: { type: "number", description: "Număr maxim rezultate (default 25)" },
          offset: { type: "number", description: "Offset paginare" },
        },
        required: ["query"],
      },
    },
    {
      name: "zotero_add_item",
      description: "Adaugă o referință bibliografică nouă în Zotero (articol, carte, decizie, legislație etc.).",
      inputSchema: {
        type: "object" as const,
        properties: {
          item_type: { type: "string", description: "Tip: case, statute, journalArticle, book, bookSection, thesis, report, webpage" },
          title: { type: "string", description: "Titlul lucrării" },
          creators: { type: "array", items: { type: "object", properties: { firstName: { type: "string" }, lastName: { type: "string" }, creatorType: { type: "string" } } }, description: "Lista autorilor" },
          date: { type: "string", description: "Data publicării" },
          abstract: { type: "string", description: "Rezumat" },
          url: { type: "string", description: "URL sursă" },
          tags: { type: "array", items: { type: "string" }, description: "Etichete" },
          collection_key: { type: "string", description: "Colecția în care se adaugă" },
          extra_fields: { type: "object", description: "Câmpuri suplimentare: DOI, ISSN, volume, pages, court, docketNumber etc." },
        },
        required: ["item_type", "title"],
      },
    },
    {
      name: "zotero_list_collections",
      description: "Listează colecțiile din biblioteca Zotero (ierarhic).",
      inputSchema: {
        type: "object" as const,
        properties: {
          parent_collection_key: { type: "string", description: "Cheia colecției părinte (opțional — listează sub-colecțiile)" },
        },
      },
    },
    {
      name: "zotero_get_bibliography",
      description: "Generează bibliografie formatată pentru referințe selectate sau o colecție întreagă.",
      inputSchema: {
        type: "object" as const,
        properties: {
          item_keys: { type: "array", items: { type: "string" }, description: "Cheile itemelor (alternativ la collection_key)" },
          collection_key: { type: "string", description: "Cheia colecției (alternativ la item_keys)" },
          citation_style: { type: "string", description: "Stil CSL (default: chicago-fullnote-bibliography)" },
          locale: { type: "string", description: "Limba (default: ro-RO)" },
        },
      },
    },
    {
      name: "zotero_manage_tags",
      description: "Adaugă, elimină sau listează etichete pe referințe Zotero.",
      inputSchema: {
        type: "object" as const,
        properties: {
          action: { type: "string", enum: ["add", "remove", "list"], description: "Acțiunea: add, remove, list" },
          item_key: { type: "string", description: "Cheia itemului (necesar pentru add/remove)" },
          tags: { type: "array", items: { type: "string" }, description: "Etichetele de adăugat/eliminat" },
        },
        required: ["action"],
      },
    },
    {
      name: "zotero_add_note",
      description: "Adaugă o notă de cercetare la o referință Zotero existentă.",
      inputSchema: {
        type: "object" as const,
        properties: {
          parent_item_key: { type: "string", description: "Cheia referinței părinte" },
          note_content: { type: "string", description: "Conținutul notei (suportă HTML)" },
          tags: { type: "array", items: { type: "string" }, description: "Etichete pentru notă" },
        },
        required: ["parent_item_key", "note_content"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "zotero_search_items": {
        const a = args as Record<string, unknown>;
        const params: Record<string, string | number> = {
          q: String(a.query ?? ""),
          qmode: String(a.search_mode ?? "titleCreatorYear"),
          limit: Number(a.limit ?? 25),
          start: Number(a.offset ?? 0),
        };
        if (a.item_type && a.item_type !== "all") params.itemType = String(a.item_type);
        if (a.tag) params.tag = String(a.tag);
        const result = a.collection_key
          ? await zotero.getCollectionItems(String(a.collection_key), params)
          : await zotero.searchItems(params);
        const items = result.items.map((item: Record<string, unknown>) => {
          const data = item.data as Record<string, unknown> | undefined;
          return {
            key: data?.key ?? item.key,
            title: data?.title ?? "",
            itemType: data?.itemType ?? "",
            date: data?.date ?? "",
            creators: data?.creators ?? [],
            tags: data?.tags ?? [],
            url: data?.url ?? "",
          };
        });
        return { content: [{ type: "text", text: JSON.stringify({ items, total: result.total }, null, 2) }] };
      }

      case "zotero_add_item": {
        const a = args as Record<string, unknown>;
        const itemData: Record<string, unknown> = {
          itemType: a.item_type,
          title: a.title,
          date: a.date ?? "",
          abstractNote: a.abstract ?? "",
          url: a.url ?? "",
          creators: (a.creators as Array<Record<string, string>> | undefined) ?? [],
          tags: ((a.tags as string[]) ?? []).map(t => ({ tag: t })),
          ...(a.extra_fields as Record<string, unknown> ?? {}),
        };
        if (a.collection_key) {
          itemData.collections = [a.collection_key];
        }
        const result = await zotero.createItem([itemData]);
        return { content: [{ type: "text", text: JSON.stringify({ success: true, result }, null, 2) }] };
      }

      case "zotero_list_collections": {
        const a = args as Record<string, unknown>;
        const collections = await zotero.listCollections(a.parent_collection_key as string | undefined);
        const formatted = collections.map((c: Record<string, unknown>) => {
          const data = c.data as Record<string, unknown> | undefined;
          return {
            key: data?.key ?? c.key,
            name: data?.name ?? "",
            parentCollection: data?.parentCollection ?? false,
            numItems: (c.meta as Record<string, unknown>)?.numItems ?? 0,
          };
        });
        return { content: [{ type: "text", text: JSON.stringify(formatted, null, 2) }] };
      }

      case "zotero_get_bibliography": {
        const a = args as Record<string, unknown>;
        const style = String(a.citation_style ?? "chicago-fullnote-bibliography");
        const locale = String(a.locale ?? "ro-RO");
        const params: Record<string, string | number> = { style, locale };
        if (a.item_keys) {
          params.itemKey = (a.item_keys as string[]).join(",");
        }
        let bib: string;
        if (a.collection_key) {
          const items = await zotero.getCollectionItems(String(a.collection_key), { limit: 100 });
          const keys = items.items.map((i: Record<string, unknown>) => (i.data as Record<string, unknown>)?.key ?? i.key).filter(Boolean);
          params.itemKey = (keys as string[]).join(",");
          bib = await zotero.getBibliography(params);
        } else {
          bib = await zotero.getBibliography(params);
        }
        return { content: [{ type: "text", text: bib }] };
      }

      case "zotero_manage_tags": {
        const a = args as Record<string, unknown>;
        const action = String(a.action);
        if (action === "list") {
          const item = await zotero.getItem(String(a.item_key ?? ""));
          const data = (item as Record<string, unknown>).data as Record<string, unknown>;
          return { content: [{ type: "text", text: JSON.stringify({ tags: data?.tags ?? [] }, null, 2) }] };
        }
        const item = await zotero.getItem(String(a.item_key));
        const data = (item as Record<string, unknown>).data as Record<string, unknown>;
        const version = (item as Record<string, unknown>).version as number;
        let tags = (data.tags as Array<{ tag: string }>) ?? [];
        const inputTags = (a.tags as string[]) ?? [];
        if (action === "add") {
          const existing = new Set(tags.map(t => t.tag));
          for (const t of inputTags) { if (!existing.has(t)) tags.push({ tag: t }); }
        } else if (action === "remove") {
          tags = tags.filter(t => !inputTags.includes(t.tag));
        }
        await zotero.updateItem(String(a.item_key), { tags }, version);
        return { content: [{ type: "text", text: JSON.stringify({ success: true, tags }, null, 2) }] };
      }

      case "zotero_add_note": {
        const a = args as Record<string, unknown>;
        const noteData = {
          itemType: "note",
          parentItem: String(a.parent_item_key),
          note: String(a.note_content),
          tags: ((a.tags as string[]) ?? []).map(t => ({ tag: t })),
        };
        const result = await zotero.createItem([noteData]);
        return { content: [{ type: "text", text: JSON.stringify({ success: true, result }, null, 2) }] };
      }

      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[zotero] Tool ${name} error:`, msg);
    return { content: [{ type: "text", text: JSON.stringify({ error: msg, suggestion: "Verificați cheia API și ID-ul utilizatorului Zotero." }) }], isError: true };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[zotero-mcp-server] Running on stdio");
}
main().catch(e => { console.error(e); process.exit(1); });
