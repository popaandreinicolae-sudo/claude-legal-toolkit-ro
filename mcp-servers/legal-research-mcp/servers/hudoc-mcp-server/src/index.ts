import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { HudocClient } from "./services/hudoc-client.js";

const CHARACTER_LIMIT = 25000;
const server = new Server({ name: "hudoc-mcp-server", version: "1.0.0" }, { capabilities: { tools: {} } });
const hudoc = new HudocClient();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "hudoc_search_cases",
      description: "Caută cauze CEDO pe HUDOC. Suportă filtrare după articol, stat, importanță, violare, perioadă.",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Text de căutare" },
          respondent_country: { type: "string", description: "Codul ISO3 al statului (ex: ROU, FRA, GBR)" },
          article: { type: "string", description: "Articolul CEDO (ex: 8, 10, 6-1)" },
          importance: { type: "string", enum: ["1", "2", "3", "all"], description: "Nivel importanță: 1=Key, 2=Important, 3=Standard" },
          date_from: { type: "string", description: "Data minimă (YYYY-MM-DD)" },
          date_to: { type: "string", description: "Data maximă (YYYY-MM-DD)" },
          violation: { type: "string", enum: ["yes", "no", "all"], description: "Doar cauze cu/fără violare" },
          collection: { type: "string", enum: ["GRANDCHAMBER", "CHAMBER", "COMMITTEE", "all"], description: "Formația completului" },
          language: { type: "string", enum: ["ENG", "FRE"], description: "Limba (default: ENG)" },
          limit: { type: "number", description: "Rezultate maxime (default: 20)" },
          offset: { type: "number", description: "Offset paginare" },
        },
        required: ["query"],
      },
    },
    {
      name: "hudoc_get_judgment",
      description: "Obține textul integral al unei hotărâri CEDO. Păstrează numerotarea paragrafelor (§).",
      inputSchema: {
        type: "object" as const,
        properties: {
          item_id: { type: "string", description: "HUDOC item ID (format: 001-XXXXXX)" },
          application_number: { type: "string", description: "Nr. cerere (alternativ, ex: 35252/08)" },
        },
      },
    },
    {
      name: "hudoc_search_by_article",
      description: "Căutare specializată pe articol CEDO — optimizată pentru cercetare constituțională.",
      inputSchema: {
        type: "object" as const,
        properties: {
          article: { type: "string", description: "Articolul CEDO (ex: 8, 10)" },
          respondent_country: { type: "string", description: "Stat pârât (ISO3)" },
          keywords: { type: "array", items: { type: "string" }, description: "Cuvinte cheie suplimentare" },
          violation_only: { type: "boolean", description: "Doar cauze cu constatare de violare (default: false)" },
          importance: { type: "string", enum: ["1", "2", "3", "all"], description: "Nivel importanță" },
          limit: { type: "number", description: "Rezultate maxime (default: 20)" },
          offset: { type: "number", description: "Offset paginare" },
        },
        required: ["article"],
      },
    },
    {
      name: "hudoc_exec_search",
      description: "Cauta in HUDOC-EXEC, baza de date a Comitetului Ministrilor privind executarea hotararilor CEDO. Arata daca o hotarare a fost efectiv implementata de statul parat (supraveghere inchisa/deschisa, numar rezolutie CM/ResDH). Nu returneaza text integral, doar metadate de status si link catre pagina oficiala.",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Text liber de cautare (nume cauza, tema)" },
          respondent_country: { type: "string", description: "Codul ISO3 al statului (ex: ROU, FRA)" },
          application_number: { type: "string", description: "Nr. cerere CEDO (ex: 4200/25)" },
          only_final_resolutions: { type: "boolean", description: "Doar rezolutii finale (executare incheiata), exclude cauze doar comunicate/pendinte (default: false)" },
          date_from: { type: "string", description: "Data minima (YYYY-MM-DD)" },
          date_to: { type: "string", description: "Data maxima (YYYY-MM-DD)" },
          limit: { type: "number", description: "Rezultate maxime (default: 20)" },
          offset: { type: "number", description: "Offset paginare" },
        },
      },
    },
    {
      name: "hudoc_exec_case_status",
      description: "Verifica rapid stadiul executarii unei hotarari CEDO dupa numarul cererii: supraveghere inchisa sau deschisa, numar si data rezolutie CM/ResDH.",
      inputSchema: {
        type: "object" as const,
        properties: {
          application_number: { type: "string", description: "Nr. cerere CEDO (ex: 4200/25)" },
        },
        required: ["application_number"],
      },
    },
    {
      name: "hudoc_get_case_citations",
      description: "Extrage rețeaua de citări a unei cauze — ce cauze citează și care o citează pe ea.",
      inputSchema: {
        type: "object" as const,
        properties: {
          item_id: { type: "string", description: "HUDOC item ID (001-XXXXXX)" },
          case_name: { type: "string", description: "Numele cauzei (alternativ)" },
        },
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "hudoc_search_cases": {
        const a = args as Record<string, unknown>;
        const queryStr = (a.query as string | undefined) ?? "";
        const appNoMatch = queryStr.match(/^\s*(\d{1,5}\/\d{2,4})\s*$/);
        const query = hudoc.buildQuery({
          freeText: appNoMatch ? undefined : queryStr,
          appno: appNoMatch ? appNoMatch[1] : (a.application_number as string | undefined),
          article: a.article as string | undefined,
          respondent: a.respondent_country as string | undefined,
          dateFrom: a.date_from as string | undefined,
          dateTo: a.date_to as string | undefined,
          violation: a.violation as string | undefined,
          importance: a.importance as string | undefined,
          collection: a.collection as string | undefined,
          language: a.language as string | undefined ?? "ENG",
        });
        const result = await hudoc.searchCases(query, Number(a.offset ?? 0), Number(a.limit ?? 20));
        return { content: [{ type: "text", text: JSON.stringify({ results: result.results, total: result.total }, null, 2) }] };
      }

      case "hudoc_get_judgment": {
        const a = args as Record<string, unknown>;
        let itemId = a.item_id as string | undefined;
        let caseName = "judgment";
        if (!itemId && a.application_number) {
          const found = await hudoc.findItemIdByAppNo(a.application_number as string);
          if (found) itemId = found;
        }
        if (!itemId) return { content: [{ type: "text", text: JSON.stringify({ error: "Cauza nu a fost gasita. Specificati item_id (001-XXXXXX) sau application_number (ex: 11798/85). Daca eroarea persista, accesati direct https://hudoc.echr.coe.int/eng" }) }] };
        // Extrage caseName din item ID prin search rapid (pentru filename)
        try {
          const meta = await hudoc.searchCases(`itemid:"${itemId}"`, 0, 1);
          if (meta.results.length > 0) caseName = String(meta.results[0].caseName || "judgment");
        } catch { /* ignore — folosim default */ }
        let text = await hudoc.getJudgmentText(itemId, caseName);
        const totalChars = text.length;
        let truncated = false;
        if (totalChars > CHARACTER_LIMIT) {
          text = text.slice(0, Math.floor(CHARACTER_LIMIT * 0.75)) + "\n\n[...TRUNCAT...]\n\n" + text.slice(-(CHARACTER_LIMIT - Math.floor(CHARACTER_LIMIT * 0.75) - 30));
          truncated = true;
        }
        return { content: [{ type: "text", text: JSON.stringify({ itemId, text, totalChars, truncated, url: `https://hudoc.echr.coe.int/eng?i=${itemId}` }, null, 2) }] };
      }

      case "hudoc_search_by_article": {
        const a = args as Record<string, unknown>;
        const keywords = (a.keywords as string[] | undefined) ?? [];
        const freeText = keywords.length > 0 ? keywords.join(" ") : undefined;
        const query = hudoc.buildQuery({
          freeText,
          article: a.article as string,
          respondent: a.respondent_country as string | undefined,
          violation: (a.violation_only as boolean) ? "YES" : undefined,
          importance: a.importance as string | undefined,
        });
        const result = await hudoc.searchCases(query, Number(a.offset ?? 0), Number(a.limit ?? 20));
        const withViolation = result.results.filter(r => String(r.conclusion ?? "").toLowerCase().includes("violation"));
        const withoutViolation = result.results.filter(r => !String(r.conclusion ?? "").toLowerCase().includes("violation"));
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              article: a.article,
              total: result.total,
              withViolation: { count: withViolation.length, cases: withViolation },
              withoutViolation: { count: withoutViolation.length, cases: withoutViolation },
            }, null, 2),
          }],
        };
      }

      case "hudoc_exec_search": {
        const a = args as Record<string, unknown>;
        const query = hudoc.buildExecQuery({
          freeText: a.query as string | undefined,
          respondent: a.respondent_country as string | undefined,
          appno: a.application_number as string | undefined,
          onlyFinalResolutions: a.only_final_resolutions as boolean | undefined,
          dateFrom: a.date_from as string | undefined,
          dateTo: a.date_to as string | undefined,
        });
        const result = await hudoc.searchExecution(query, Number(a.offset ?? 0), Number(a.limit ?? 20));
        return { content: [{ type: "text", text: JSON.stringify({ results: result.results, total: result.total }, null, 2) }] };
      }

      case "hudoc_exec_case_status": {
        const a = args as Record<string, unknown>;
        const appNo = a.application_number as string;
        const query = hudoc.buildExecQuery({ appno: appNo });
        const result = await hudoc.searchExecution(query, 0, 5);
        if (result.results.length === 0) {
          return { content: [{ type: "text", text: JSON.stringify({ application_number: appNo, status: "NEGASIT_IN_HUDOC_EXEC", note: "Nu apare in baza de executare, posibil cauza inca pendinte la Curte sau nu a ajuns la faza de supraveghere a Comitetului Ministrilor." }) }] };
        }
        return { content: [{ type: "text", text: JSON.stringify({ application_number: appNo, entries: result.results }, null, 2) }] };
      }

      case "hudoc_get_case_citations": {
        const a = args as Record<string, unknown>;
        let itemId = a.item_id as string | undefined;
        if (!itemId && a.case_name) {
          const caseName = a.case_name as string;
          const appNoMatch = caseName.match(/(\d{1,5}\/\d{2,4})/);
          if (appNoMatch) {
            const found = await hudoc.findItemIdByAppNo(appNoMatch[1]);
            if (found) itemId = found;
          }
          if (!itemId) {
            const query = hudoc.buildQuery({ freeText: caseName });
            const search = await hudoc.searchCases(query, 0, 1);
            if (search.results.length > 0) itemId = search.results[0].itemid as string;
          }
        }
        if (!itemId) return { content: [{ type: "text", text: JSON.stringify({ error: "Cauza nu a fost gasita. Specificati item_id (001-XXXXXX) sau case_name (cu application number ex 11798/85)." }) }] };
        const text = await hudoc.getJudgmentText(itemId);  // citations don't need filename
        const citations = hudoc.extractCitations(text);
        return { content: [{ type: "text", text: JSON.stringify({ itemId, citationsFound: citations.length, citations, url: `https://hudoc.echr.coe.int/eng?i=${itemId}` }, null, 2) }] };
      }

      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[hudoc] Tool ${name} error:`, msg);
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          error: msg,
          suggestion: "HUDOC nu are API oficial. Dacă eroarea persistă, accesați direct https://hudoc.echr.coe.int/eng",
        }),
      }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[hudoc-mcp-server] Running on stdio");
}
main().catch(e => { console.error(e); process.exit(1); });
