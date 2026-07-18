import axios, { AxiosInstance } from "axios";
import * as cheerio from "cheerio";

const SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql";
const EURLEX_BASE = "https://eur-lex.europa.eu";
const MAX_RETRIES = 3;

const PREFIXES = `
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
`;

interface SparqlBinding {
  value: string;
  type: string;
}

interface SparqlResult {
  results: { bindings: Array<Record<string, SparqlBinding>> };
}

export class EurLexClient {
  private client: AxiosInstance;
  private lastRequest = 0;

  constructor() {
    // Cellar SPARQL e lent; timeout generos ca sa nu primim raspuns gol pe timeout intern.
    this.client = axios.create({ timeout: 90000, headers: { "User-Agent": "LegalResearchMCP/1.0" } });
  }

  /**
   * Ruleaza un SPARQL care ar TREBUI sa intoarca rezultate si reincearca daca lista
   * vine goala. Endpointul Cellar raspunde uneori HTTP 200 cu 0 binding-uri cand
   * expira intern — exact cauza "count 0" intermitent. Reincercarea o corecteaza.
   */
  private async executeSparqlExpectingResults(query: string, attempts = 3): Promise<Array<Record<string, string>>> {
    let last: Array<Record<string, string>> = [];
    for (let i = 0; i < attempts; i++) {
      last = await this.executeSparql(query);
      if (last.length > 0) return last;
      if (i < attempts - 1) await new Promise(r => setTimeout(r, 1500 * (i + 1)));
    }
    return last;
  }

  private async rateLimit(): Promise<void> {
    const wait = Math.max(0, 1000 - (Date.now() - this.lastRequest));
    if (wait > 0) await new Promise(r => setTimeout(r, wait));
    this.lastRequest = Date.now();
  }

  private async retry<T>(fn: () => Promise<T>): Promise<T> {
    for (let i = 0; i <= MAX_RETRIES; i++) {
      try { return await fn(); } catch (e) {
        if (i < MAX_RETRIES) { await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i))); continue; }
        throw e;
      }
    }
    throw new Error("Max retries");
  }

  async executeSparql(query: string): Promise<Array<Record<string, string>>> {
    await this.rateLimit();
    return this.retry(async () => {
      const fullQuery = PREFIXES + query;
      const resp = await this.client.get<SparqlResult>(SPARQL_ENDPOINT, {
        params: { query: fullQuery },
        headers: { Accept: "application/sparql-results+json" },
      });
      return resp.data.results.bindings.map(binding => {
        const row: Record<string, string> = {};
        for (const [key, val] of Object.entries(binding)) { row[key] = val.value; }
        return row;
      });
    });
  }

  async searchLegislation(keyword: string, docType: string, yearFrom: number, yearTo: number, limit: number, offset: number): Promise<Array<Record<string, string>>> {
    const typeFilter = docType === "all" ? "" : `FILTER(CONTAINS(LCASE(STR(?type)), "${docType.toLowerCase()}"))`;
    const query = `
SELECT DISTINCT ?celex ?title ?date ?type ?eli WHERE {
  ?work cdm:resource_legal_id_celex ?celex .
  ?work cdm:work_date_document ?date .
  OPTIONAL { ?work cdm:resource_legal_type ?type }
  OPTIONAL { ?work cdm:resource_legal_eli ?eli }
  ?exp cdm:expression_belongs_to_work ?work .
  ?exp cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  ?exp cdm:expression_title ?title .
  FILTER(STRSTARTS(?celex, "3"))
  FILTER(CONTAINS(LCASE(?title), LCASE("${keyword}")))
  FILTER(?date >= "${yearFrom}-01-01"^^xsd:date)
  FILTER(?date <= "${yearTo}-12-31"^^xsd:date)
  ${typeFilter}
}
ORDER BY DESC(?date)
LIMIT ${limit}
OFFSET ${offset}`;
    return this.executeSparqlExpectingResults(query);
  }

  async searchCaselaw(keyword: string, yearFrom: number, yearTo: number, limit: number, offset: number): Promise<Array<Record<string, string>>> {
    const query = `
SELECT DISTINCT ?celex ?title ?date ?ecli WHERE {
  ?work cdm:resource_legal_id_celex ?celex .
  ?work cdm:work_date_document ?date .
  OPTIONAL { ?work cdm:case_law_ecli ?ecli }
  ?exp cdm:expression_belongs_to_work ?work .
  ?exp cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  ?exp cdm:expression_title ?title .
  FILTER(STRSTARTS(?celex, "6"))
  FILTER(CONTAINS(LCASE(?title), LCASE("${keyword}")))
  FILTER(?date >= "${yearFrom}-01-01"^^xsd:date)
  FILTER(?date <= "${yearTo}-12-31"^^xsd:date)
}
ORDER BY DESC(?date)
LIMIT ${limit}
OFFSET ${offset}`;
    return this.executeSparqlExpectingResults(query);
  }

  /**
   * Convert ECJ case number (e.g. "C-83/14", "T-419/03") to CELEX format.
   * Tries multiple document types: CJ (Judgment), CC (AG Opinion), CO (Order).
   * Returns ARRAY of candidate CELEX numbers to probe.
   */
  caseNumberToCelexCandidates(caseNumber: string): string[] {
    // Match: C-83/14, T-419/03, F-1/05, C-83/14 P (P for appeal stays in case_no)
    const match = caseNumber.match(/([CTFcftCT]+)\s*-?\s*(\d+)\s*\/\s*(\d{2,4})/);
    if (!match) return [];
    const [, courtRaw, caseNoRaw, yearRaw] = match;
    const court = courtRaw.toUpperCase();
    const caseNo = caseNoRaw.padStart(4, "0");
    let year = yearRaw;
    if (year.length === 2) {
      const n = parseInt(year);
      year = (n >= 50 ? "19" : "20") + year;
    }
    const courtPrefix = court === "C" ? ["CJ", "CC", "CO"] : court === "T" ? ["TJ", "TO"] : court === "F" ? ["FJ", "FO"] : ["CJ"];
    return courtPrefix.map(t => `6${year}${t}${caseNo}`);
  }

  /**
   * Find a CJEU case by case number (e.g. "C-83/14") — tries CELEX candidates one by one.
   */
  async findCaseByNumber(caseNumber: string): Promise<Record<string, string> | null> {
    const candidates = this.caseNumberToCelexCandidates(caseNumber);
    for (const celex of candidates) {
      const meta = await this.getDocumentByCelex(celex);
      if (meta.title) return { ...meta, celex };
    }
    return null;
  }

  async getDocumentByCelex(celexNumber: string): Promise<Record<string, string>> {
    const query = `
SELECT ?title ?date ?type ?eli WHERE {
  ?work cdm:resource_legal_id_celex "${celexNumber}" .
  ?work cdm:work_date_document ?date .
  OPTIONAL { ?work cdm:resource_legal_type ?type }
  OPTIONAL { ?work cdm:resource_legal_eli ?eli }
  ?exp cdm:expression_belongs_to_work ?work .
  ?exp cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  ?exp cdm:expression_title ?title .
}
LIMIT 1`;
    const results = await this.executeSparql(query);
    return results[0] ?? {};
  }

  /**
   * Converteste o referinta (ex. "2009/73/CE", "2009/73", "347/2013", CELEX brut)
   * la numar CELEX. Directivele sunt AN/NUMAR, regulamentele NUMAR/AN.
   */
  referenceToCelex(reference: string): string {
    const ref = reference.trim().toUpperCase();
    // CELEX brut: incepe cu cifra de sector si contine o litera de tip.
    if (/^[1-9]\d{3,4}[A-Z]\d{2,4}/.test(ref.replace(/\s/g, ""))) {
      return ref.replace(/\s/g, "");
    }
    const m = ref.match(/(\d{1,4})\s*\/\s*(\d{1,4})/);
    if (!m) return "";
    let a = parseInt(m[1], 10);
    let b = parseInt(m[2], 10);
    let year: number, num: number, typeLetter: string;
    if (a >= 1900) {
      // AN/NUMAR -> directiva (L)
      year = a; num = b; typeLetter = "L";
    } else {
      // NUMAR/AN -> regulament (R)
      num = a; year = b; typeLetter = "R";
    }
    if (/REGULAMENT/.test(ref)) typeLetter = "R";
    if (/DIRECTIV/.test(ref)) typeLetter = "L";
    if (/DECIZIA|DECISION/.test(ref)) typeLetter = "D";
    return `3${year}${typeLetter}${String(num).padStart(4, "0")}`;
  }

  /**
   * Verifica daca un act UE este in vigoare sau abrogat, citind indicatorul de
   * status de pe pagina EUR-Lex. Esential pentru a evita citarea de directive
   * abrogate ca temei (ex. Directiva 2009/73/CE inlocuita de 2024/1788).
   */
  async checkInForce(reference: string): Promise<Record<string, unknown>> {
    const celex = this.referenceToCelex(reference);
    if (!celex) return { reference, error: "Nu am putut deriva CELEX din referinta." };
    await this.rateLimit();
    return this.retry(async () => {
      const url = `${EURLEX_BASE}/legal-content/EN/ALL/?uri=CELEX:${celex}`;
      const resp = await this.client.get<string>(url, { responseType: "text" });
      const $ = cheerio.load(resp.data);
      const body = $("body").text().replace(/\s+/g, " ");
      const noLonger = /No longer in force/i.test(body);
      const endValidity = body.match(/Date of end of validity:\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})/i);
      const repealedBy = body.match(/Repealed by[:\s]*([0-9A-Z]{8,})/i);
      const inForceFlag = /\bIn force\b/i.test(body) && !noLonger;
      const status = noLonger ? "ABROGAT / NO LONGER IN FORCE" : (inForceFlag ? "IN VIGOARE" : "NECUNOSCUT");
      return {
        reference,
        celex,
        in_force: !noLonger && inForceFlag ? true : (noLonger ? false : null),
        status,
        end_of_validity: endValidity ? endValidity[1] : null,
        repealed_by: repealedBy ? repealedBy[1] : null,
        url: `${EURLEX_BASE}/legal-content/EN/ALL/?uri=CELEX:${celex}`,
      };
    });
  }

  async fetchDocumentHtml(celexNumber: string, language: string = "EN"): Promise<string> {
    await this.rateLimit();
    return this.retry(async () => {
      const url = `${EURLEX_BASE}/legal-content/${language}/TXT/HTML/?uri=CELEX:${celexNumber}`;
      const resp = await this.client.get<string>(url);
      const $ = cheerio.load(resp.data);
      $("script, style, nav, header, footer").remove();
      const text = $("body").text().replace(/\s+/g, " ").trim();
      return text;
    });
  }
}
