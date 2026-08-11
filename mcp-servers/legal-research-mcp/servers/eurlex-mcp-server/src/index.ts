import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { EurLexClient } from "./services/eurlex-client.js";

const CHARACTER_LIMIT = 25000;
const server = new Server({ name: "eurlex-mcp-server", version: "1.0.0" }, { capabilities: { tools: {} }, instructions: "Dreptul Uniunii Europene si jurisprudenta CJUE, luate direct din EUR-Lex. Foloseste-l ori de cate ori raspunsul atinge o directiva, un regulament, o decizie UE sau o cauza CJUE, inclusiv cand verifici transpunerea in dreptul romanesc. Ruleaza check_in_force inainte de a cita un act: citarea unui act abrogat ca temei in vigoare este eroarea cea mai costisitoare. Pentru legislatie si jurisprudenta romaneasca mergi la legal-verificator-ro, care tine si harta de rutare a intregului toolkit juridic." });
const eurlex = new EurLexClient();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "eurlex_search_legislation",
      description: "Caută legislație UE (directive, regulamente, decizii) pe EUR-Lex prin SPARQL. Returnează CELEX, titlu, dată, tip, ELI.",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Termeni de căutare (în engleză)" },
          document_type: { type: "string", enum: ["directive", "regulation", "decision", "all"], description: "Tip document (default: all)" },
          year_from: { type: "number", description: "An minim (default: 2000)" },
          year_to: { type: "number", description: "An maxim (default: 2026)" },
          limit: { type: "number", description: "Rezultate maxime (default: 20)" },
          offset: { type: "number", description: "Offset paginare (default: 0)" },
        },
        required: ["query"],
      },
    },
    {
      name: "eurlex_get_document",
      description: "Obține metadate și/sau textul unui document EUR-Lex după numărul CELEX (ex: 32022L2555 = NIS2).",
      inputSchema: {
        type: "object" as const,
        properties: {
          celex_number: { type: "string", description: "Număr CELEX (ex: 32022L2555, 62018CJ0311)" },
          content_type: { type: "string", enum: ["metadata", "text", "full"], description: "Ce să returneze (default: full)" },
          language: { type: "string", description: "Limba: EN, RO, FR (default: EN)" },
        },
        required: ["celex_number"],
      },
    },
    {
      name: "eurlex_search_caselaw",
      description: "Caută jurisprudență CJUE pe EUR-Lex. Returnează cauze cu ECLI, dată, părți.",
      inputSchema: {
        type: "object" as const,
        properties: {
          query: { type: "string", description: "Termeni de căutare" },
          case_number: { type: "string", description: "Număr cauză (ex: C-311/18)" },
          year_from: { type: "number", description: "An minim" },
          year_to: { type: "number", description: "An maxim" },
          limit: { type: "number", description: "Rezultate maxime (default: 20)" },
          offset: { type: "number", description: "Offset paginare" },
        },
        required: ["query"],
      },
    },
    {
      name: "eurlex_get_celex",
      description: "Căutare rapidă după CELEX — returnează informații structurate pentru citare academică.",
      inputSchema: {
        type: "object" as const,
        properties: {
          celex_number: { type: "string", description: "Număr CELEX" },
        },
        required: ["celex_number"],
      },
    },
    {
      name: "check_in_force",
      description: "Verifică dacă un act UE (directivă, regulament, decizie) este ÎN VIGOARE sau ABROGAT. Esențial pentru a nu cita ca temei un act abrogat (ex: Directiva 2009/73/CE, abrogată, înlocuită de 2024/1788). Acceptă referință (2009/73/CE, 347/2013) sau CELEX brut. Când referința nu precizează tipul actului, se probează directiva, regulamentul și decizia cu același număr, iar răspunsul spune ce s-a găsit; preferă totuși referința cu tip (\"Regulamentul 2016/679\"), fiindcă același număr și an pot fi purtate de acte diferite.",
      inputSchema: {
        type: "object" as const,
        properties: {
          reference: { type: "string", description: "Referință act UE (ex: 2009/73/CE, Directiva 2024/1788, Regulamentul 347/2013) sau CELEX (ex: 32009L0073)" },
        },
        required: ["reference"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    switch (name) {
      case "eurlex_search_legislation": {
        const a = args as Record<string, unknown>;
        const results = await eurlex.searchLegislation(
          String(a.query), String(a.document_type ?? "all"),
          Number(a.year_from ?? 2000), Number(a.year_to ?? 2026),
          Number(a.limit ?? 20), Number(a.offset ?? 0),
        );
        const formatted = results.map(r => ({
          celex: r.celex, title: r.title, date: r.date, type: r.type ?? "", eli: r.eli ?? "",
          url: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:${r.celex}`,
        }));
        return { content: [{ type: "text", text: JSON.stringify({ results: formatted, count: formatted.length }, null, 2) }] };
      }

      case "eurlex_get_document": {
        const a = args as Record<string, unknown>;
        const celex = String(a.celex_number);
        const contentType = String(a.content_type ?? "full");
        const language = String(a.language ?? "EN");
        const meta = await eurlex.getDocumentByCelex(celex);
        if (!meta.title) return { content: [{ type: "text", text: JSON.stringify({ error: `Document CELEX ${celex} nu a fost găsit.` }) }] };

        let text = "";
        if (contentType === "text" || contentType === "full") {
          text = await eurlex.fetchDocumentHtml(celex, language);
          if (text.length > CHARACTER_LIMIT) {
            text = text.slice(0, CHARACTER_LIMIT) + "\n\n[...TRUNCAT — " + text.length + " caractere total...]";
          }
        }
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              celex, title: meta.title, date: meta.date, type: meta.type ?? "", eli: meta.eli ?? "",
              url: `https://eur-lex.europa.eu/legal-content/${language}/TXT/?uri=CELEX:${celex}`,
              text: contentType !== "metadata" ? text : undefined,
            }, null, 2),
          }],
        };
      }

      case "eurlex_search_caselaw": {
        const a = args as Record<string, unknown>;
        const queryStr = String(a.query ?? "");
        const caseNumStr = a.case_number ? String(a.case_number) : "";
        // Detect case number in query string itself (ex: "C-83/14 CHEZ Razpredelenie")
        const queryCaseMatch = queryStr.match(/([CTF]-\d+\/\d{2,4})/i);
        const directCaseNumber = caseNumStr || (queryCaseMatch ? queryCaseMatch[1] : "");

        // Strategy 1: If we have a case number, try CELEX direct lookup first
        if (directCaseNumber) {
          const direct = await eurlex.findCaseByNumber(directCaseNumber);
          if (direct) {
            return {
              content: [{
                type: "text",
                text: JSON.stringify({
                  results: [{
                    celex: direct.celex, title: direct.title, date: direct.date, ecli: direct.ecli ?? "",
                    url: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:${direct.celex}`,
                    matched_via: "case_number_to_celex",
                  }],
                  count: 1,
                }, null, 2),
              }],
            };
          }
        }

        // Strategy 2: Title keyword search (fallback)
        const keywordOnly = queryStr.replace(/[CTF]-\d+\/\d{2,4}\s*/gi, "").trim();
        const keyword = keywordOnly || queryStr;
        const results = await eurlex.searchCaselaw(
          keyword, Number(a.year_from ?? 1950), Number(a.year_to ?? 2026),
          Number(a.limit ?? 20), Number(a.offset ?? 0),
        );
        const formatted = results.map(r => ({
          celex: r.celex, title: r.title, date: r.date, ecli: r.ecli ?? "",
          url: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:${r.celex}`,
        }));
        return { content: [{ type: "text", text: JSON.stringify({ results: formatted, count: formatted.length, query_used: keyword }, null, 2) }] };
      }

      case "eurlex_get_celex": {
        const celex = String((args as Record<string, unknown>).celex_number);
        const meta = await eurlex.getDocumentByCelex(celex);
        if (!meta.title) return { content: [{ type: "text", text: JSON.stringify({ error: `CELEX ${celex} nu a fost găsit.` }) }] };
        const sector = celex.charAt(0);
        const sectorName = sector === "3" ? "Legislație" : sector === "6" ? "Jurisprudență" : sector === "1" ? "Tratat" : "Altele";
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              celex, sector: sectorName, title: meta.title, date: meta.date, eli: meta.eli ?? "",
              citation: `${meta.title} (CELEX: ${celex})`,
              url: `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:${celex}`,
            }, null, 2),
          }],
        };
      }

      case "check_in_force": {
        const ref = String((args as Record<string, unknown>).reference);
        const result = await eurlex.checkInForce(ref);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    console.error(`[eurlex] Tool ${name} error:`, msg);
    return { content: [{ type: "text", text: JSON.stringify({ error: msg, suggestion: "Încercați cu termeni de căutare mai specifici sau verificați numărul CELEX." }) }], isError: true };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("[eurlex-mcp-server] Running on stdio");
}
main().catch(e => { console.error(e); process.exit(1); });
