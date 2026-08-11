import axios, { AxiosInstance } from "axios";
import * as cheerio from "cheerio";

const HUDOC_SEARCH = "https://hudoc.echr.coe.int/app/query/results";
// HUDOC-EXEC: baza de date a Comitetului Ministrilor privind executarea hotararilor CEDO
// (acelasi motor de cautare ca HUDOC principal, index separat, verificat live iulie 2026).
// Spre deosebire de HUDOC principal, NU cere "contentsitename" in query si textul integral
// al rezolutiilor nu e disponibil prin /app/conversion (404 constant la testare), doar
// metadatele de status (execsupervision, execisclosed, execresolutionnumber etc.).
const HUDOC_EXEC_SEARCH = "https://hudoc.exec.coe.int/app/query/results";
const HUDOC_EXEC_PAGE = "https://hudoc.exec.coe.int/eng";
const EXEC_SELECT_FIELDS = "itemid,docname,appno,respondent,doctype,kpdateastext,conclusion,execsupervision,execisclosed,execresolutionnumber,execfinalresolutiondateastext,exectype,execviolations,execcmmeetingnumber";
// Endpointul /app/conversion/docx/html/body/{id} returneaza 404 din 2025+
// Endpointul corect cere parametrii library, id, filename in query string
const HUDOC_DOC_HTML = "https://hudoc.echr.coe.int/app/conversion/docx/html/body";
const HUDOC_DOC_HTML_FULL = "https://hudoc.echr.coe.int/app/conversion/docx/html";
const HUDOC_DOC_DOCX = "https://hudoc.echr.coe.int/app/conversion/docx";
const HUDOC_PAGE = "https://hudoc.echr.coe.int/eng";
const MAX_RETRIES = 3;
const SELECT_FIELDS = "itemid,applicant,doctypebranch,ecli,importance,judgmentdate,languageisocode,originatingbody,respondent,article,conclusion,separateopinion,kpthesaurus,docname,appno";

interface HudocResult {
  columns: string[];
  results: Array<Record<string, string | string[]>>;
  resultcount: number;
}

export class HudocClient {
  private client: AxiosInstance;
  private lastRequest = 0;

  constructor() {
    this.client = axios.create({
      timeout: 30000,
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://hudoc.echr.coe.int/eng",
        "Origin": "https://hudoc.echr.coe.int",
      },
    });
  }

  private async rateLimit(): Promise<void> {
    const wait = Math.max(0, 2000 - (Date.now() - this.lastRequest));
    if (wait > 0) await new Promise(r => setTimeout(r, wait));
    this.lastRequest = Date.now();
  }

  private async retry<T>(fn: () => Promise<T>): Promise<T> {
    for (let i = 0; i <= MAX_RETRIES; i++) {
      try { return await fn(); } catch (e) {
        if (i < MAX_RETRIES) { await new Promise(r => setTimeout(r, 2000 * Math.pow(2, i))); continue; }
        throw e;
      }
    }
    throw new Error("Max retries");
  }

  buildQuery(params: {
    freeText?: string; article?: string; respondent?: string;
    dateFrom?: string; dateTo?: string; violation?: string;
    importance?: string; collection?: string; language?: string;
    appno?: string;
  }): string {
    // Sintaxa HUDOC corecta (verificata live, iunie 2026):
    //   - contentsitename:ECHR (FARA ghilimele) + clauza NOT obligatorie pentru doctype
    //     altfel API-ul intoarce resultcount 0 la orice interogare;
    //   - campurile de filtrare folosesc ":" fara ghilimele (respondent:ROU, importance:1);
    //   - completul foloseste documentcollectionid="X" (egal, cu ghilimele);
    //   - intervalul de date foloseste kpdate:[FROM TO TO] cu timestamp ISO Z.
    // Parantezele trebuie sa ramana LITERALE in URL (vezi paramsSerializer din searchCases).
    const parts: string[] = [
      "contentsitename:ECHR",
      "(NOT (doctype=PR OR doctype=HFCOMOLD OR doctype=HECOMOLD))",
    ];
    if (params.freeText) parts.push(params.freeText.trim());
    if (params.appno) parts.push(`appno:${params.appno}`);
    if (params.article) parts.push(`article:${params.article}`);
    if (params.respondent) parts.push(`respondent:${params.respondent.toUpperCase()}`);
    if (params.dateFrom || params.dateTo) {
      const from = params.dateFrom || "1950-01-01";
      const to = params.dateTo || "2100-12-31";
      parts.push(`kpdate:[${from}T00:00:00.0Z TO ${to}T00:00:00.0Z]`);
    }
    if (params.importance && params.importance !== "all") parts.push(`importance:${params.importance}`);
    if (params.collection && params.collection !== "all") parts.push(`documentcollectionid="${params.collection.toUpperCase()}"`);
    if (params.language) parts.push(`languageisocode:${params.language}`);
    return parts.join(" AND ");
  }

  // Interogarea pe numele cauzei: fiecare cuvant semnificativ primeste propriul
  // prefix docname:. Verificat live (august 2026): "docname:Barbulescu AND
  // docname:Romania" urca respectiva cauza pe primul loc (30 rezultate), in timp ce
  // acelasi text cautat full-text o ingroapa sub cauzele recente care o citeaza
  // (281 rezultate, ordonate de modelul de ranking dupa recenta). Forma
  // docname:(W1 W2) NU functioneaza — degenereaza in ~200k rezultate. Indexul
  // face diacritic folding in ambele sensuri, deci Barbulescu = Bărbulescu.
  buildDocnameClause(freeText: string): string | null {
    const STOP = new Set(["v", "c", "vs", "and", "of", "the", "la", "le", "contre", "against", "case", "affaire", "si", "et"]);
    const words = freeText
      .split(/\s+/)
      .map(w => w.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, ""))
      .filter(w => w.length >= 2 && !STOP.has(w.toLowerCase()));
    if (words.length === 0) return null;
    return words.map(w => `docname:${w}`).join(" AND ");
  }

  buildExecQuery(params: {
    freeText?: string; respondent?: string; appno?: string;
    onlyFinalResolutions?: boolean; dateFrom?: string; dateTo?: string;
  }): string {
    const parts: string[] = [];
    if (params.freeText) parts.push(params.freeText.trim());
    if (params.appno) parts.push(`appno:${params.appno}`);
    if (params.respondent) parts.push(`respondent:${params.respondent.toUpperCase()}`);
    if (params.onlyFinalResolutions) parts.push("doctype:HFRES54");
    if (params.dateFrom || params.dateTo) {
      const from = params.dateFrom || "1950-01-01";
      const to = params.dateTo || "2100-12-31";
      parts.push(`kpdate:[${from}T00:00:00.0Z TO ${to}T00:00:00.0Z]`);
    }
    return parts.length > 0 ? parts.join(" AND ") : "*";
  }

  async searchExecution(query: string, start: number = 0, length: number = 20): Promise<{ results: Array<Record<string, unknown>>; total: number }> {
    await this.rateLimit();
    return this.retry(async () => {
      const enc = (s: string) => encodeURIComponent(s).replace(/%5B/g, "[").replace(/%5D/g, "]");
      const qs = [
        `query=${enc(query)}`,
        `select=${EXEC_SELECT_FIELDS}`,
        `sort=`,
        `start=${start}`,
        `length=${length}`,
        `rankingModelId=11111111-0000-0000-0000-000000000000`,
      ].join("&");
      const resp = await this.client.get<HudocResult>(`${HUDOC_EXEC_SEARCH}?${qs}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = resp.data;
      const results = (data.results ?? []).map(r => ({
        itemid: this.val(r, "itemid"),
        caseName: this.val(r, "docname"),
        applicationNumber: this.val(r, "appno"),
        respondent: this.val(r, "respondent"),
        doctype: this.val(r, "doctype"),
        date: this.val(r, "kpdateastext"),
        conclusion: this.val(r, "conclusion"),
        supervisionStatus: this.val(r, "execsupervision") || null,
        isClosed: this.val(r, "execisclosed") || null,
        resolutionNumber: this.val(r, "execresolutionnumber") || null,
        finalResolutionDate: this.val(r, "execfinalresolutiondateastext") || null,
        executionType: this.val(r, "exectype") || null,
        violations: this.val(r, "execviolations") || null,
        cmMeetingNumber: this.val(r, "execcmmeetingnumber") || null,
        pageUrl: `${HUDOC_EXEC_PAGE}?i=${this.val(r, "itemid")}`,
      }));
      return { results, total: data.resultcount ?? 0 };
    });
  }

  async findItemIdByAppNo(appNo: string): Promise<string | null> {
    const query = this.buildQuery({ appno: appNo, language: "ENG" });
    const result = await this.searchCases(query, 0, 5);
    if (result.results.length > 0) return result.results[0].itemid as string;
    const queryFre = this.buildQuery({ appno: appNo, language: "FRE" });
    const resultFre = await this.searchCases(queryFre, 0, 5);
    if (resultFre.results.length > 0) return resultFre.results[0].itemid as string;
    return null;
  }

  async searchCases(query: string, start: number = 0, length: number = 20): Promise<{ results: Array<Record<string, unknown>>; total: number }> {
    await this.rateLimit();
    return this.retry(async () => {
      // Construim URL-ul manual: HUDOC cere parantezele LITERALE (nu decodeaza
      // %28/%29), iar serializarea default axios le encodeaza -> resultcount 0.
      // encodeURIComponent lasa () literale; restauram [ ] pentru intervalul kpdate.
      const enc = (s: string) => encodeURIComponent(s).replace(/%5B/g, "[").replace(/%5D/g, "]");
      const qs = [
        `query=${enc(query)}`,
        `select=${SELECT_FIELDS}`,
        // sort gol: "judgmentdate Descending" nu e un camp de sortare valid si
        // face API-ul sa intoarca 0; rezultatele vin in ordinea de relevanta.
        `sort=`,
        `start=${start}`,
        `length=${length}`,
        // rankingModelId corect — cel vechi (...-1111) intoarce 0 la orice interogare.
        `rankingModelId=11111111-0000-0000-0000-000000000000`,
      ].join("&");
      const resp = await this.client.get<HudocResult>(`${HUDOC_SEARCH}?${qs}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = resp.data;
      const results = (data.results ?? []).map(r => ({
        itemid: this.val(r, "itemid"),
        caseName: this.val(r, "docname"),
        applicationNumber: this.val(r, "appno"),
        date: this.val(r, "judgmentdate"),
        respondent: this.val(r, "respondent"),
        articles: ((r as Record<string, unknown>).columns as Record<string, unknown> ?? r)?.article ?? [],
        conclusion: this.val(r, "conclusion"),
        ecli: this.val(r, "ecli"),
        importance: this.val(r, "importance"),
        separateOpinion: this.val(r, "separateopinion"),
      }));
      return { results, total: data.resultcount ?? 0 };
    });
  }

  private val(r: Record<string, unknown>, key: string): string {
    // HUDOC intoarce campurile sub r.columns; cadem inapoi pe r pentru compatibilitate.
    const cols = (r.columns as Record<string, unknown>) ?? r;
    const v = cols[key];
    return Array.isArray(v) ? (v[0] as string) ?? "" : (v as string) ?? "";
  }

  async getJudgmentText(itemId: string, caseName: string = "judgment"): Promise<string> {
    if (!/^001-\d+$/.test(itemId)) throw new Error(`Invalid HUDOC item ID format: ${itemId}. Expected: 001-XXXXXX`);
    await this.rateLimit();
    const safeFilename = encodeURIComponent(caseName.replace(/[^A-Za-z0-9 .-]/g, "")) + ".docx";

    // Lista de URL-uri de probat in ordine (cele mai recente endpoint-uri HUDOC)
    const urlCandidates = [
      `${HUDOC_DOC_HTML_FULL}?library=ECHR&id=${itemId}&filename=${safeFilename}`,
      `${HUDOC_DOC_HTML}?library=ECHR&id=${itemId}&filename=${safeFilename}`,
      `${HUDOC_DOC_HTML}/${itemId}`,
      `${HUDOC_PAGE}?i=${itemId}`,
    ];

    let lastError: Error | null = null;
    for (const url of urlCandidates) {
      try {
        const resp = await this.retry(() => this.client.get<string>(url, {
          headers: { Accept: "text/html,application/xhtml+xml" },
          responseType: "text",
        }));
        if (!resp.data || resp.data.length < 200) continue;

        const $ = cheerio.load(resp.data);
        $("script, style, nav, header, footer, .site-header, .site-footer").remove();

        let text = "";
        // HUDOC docx-as-html pune fiecare paragraf in <p> sau <div class='Para'>
        const paraSelector = $("p").length > 5 ? "p" : ".Para, p, div";
        $(paraSelector).each((_, el) => {
          const pText = $(el).text().trim();
          if (pText && pText.length > 2) text += pText + "\n\n";
        });

        if (text.length > 500) return text;
        // Fallback: tot textul (mai noisy dar prinde si content)
        const allText = $.root().text().replace(/\s+/g, " ").trim();
        if (allText.length > 500) return allText;
      } catch (e) {
        lastError = e instanceof Error ? e : new Error(String(e));
      }
    }
    throw lastError ?? new Error(`HUDOC: nu s-a putut obtine textul pentru ${itemId} dupa probare la ${urlCandidates.length} endpoint-uri`);
  }

  extractCitations(text: string): string[] {
    const patterns = [
      /(\d{4,5}\/\d{2,4})/g,
      /((?:v\.|c\.)\s+[A-Z][a-zA-Z\s]+)/g,
    ];
    const citations = new Set<string>();
    for (const p of patterns) {
      const matches = text.matchAll(p);
      for (const m of matches) citations.add(m[1].trim());
    }
    return Array.from(citations).slice(0, 50);
  }
}
