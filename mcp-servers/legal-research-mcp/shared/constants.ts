export const CHARACTER_LIMIT = 25000;
export const DEFAULT_TIMEOUT = 30000;
export const SPARQL_TIMEOUT = 60000;
export const MAX_RETRIES = 3;
export const RETRY_BASE_DELAY = 1000;

export const RATE_LIMITS = {
  eurlex: 1,    // 1 req/s
  hudoc: 0.5,   // 1 req per 2s
  zotero: 5,    // 5 req/s
} as const;

export const USER_AGENT = "LegalResearchMCP/1.0 (academic-research)";
