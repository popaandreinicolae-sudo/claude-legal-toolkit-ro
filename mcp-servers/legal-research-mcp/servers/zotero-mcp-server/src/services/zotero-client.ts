import axios, { AxiosInstance } from "axios";

const MAX_RETRIES = 3;

export class ZoteroClient {
  private client: AxiosInstance;
  private userId: string;

  constructor() {
    const apiKey = process.env.ZOTERO_API_KEY ?? "";
    this.userId = process.env.ZOTERO_USER_ID ?? "";
    if (!apiKey) console.error("[zotero] WARNING: ZOTERO_API_KEY not set");
    if (!this.userId) console.error("[zotero] WARNING: ZOTERO_USER_ID not set");

    this.client = axios.create({
      baseURL: "https://api.zotero.org",
      timeout: 30000,
      headers: {
        "Zotero-API-Key": apiKey,
        "Zotero-API-Version": "3",
        "Content-Type": "application/json",
      },
    });
  }

  private userPath(path: string): string {
    return `/users/${this.userId}${path}`;
  }

  private async retry<T>(fn: () => Promise<T>): Promise<T> {
    for (let i = 0; i <= MAX_RETRIES; i++) {
      try {
        return await fn();
      } catch (e: unknown) {
        if (i < MAX_RETRIES && axios.isAxiosError(e)) {
          const backoff = e.response?.headers?.["backoff"] ?? e.response?.headers?.["retry-after"];
          const delay = backoff ? parseInt(backoff as string, 10) * 1000 : 1000 * Math.pow(2, i);
          console.error(`[zotero] Retry ${i + 1} after ${delay}ms`);
          await new Promise(r => setTimeout(r, delay));
          continue;
        }
        throw e;
      }
    }
    throw new Error("Max retries exceeded");
  }

  async searchItems(params: Record<string, string | number>): Promise<{ items: Record<string, unknown>[]; total: number }> {
    return this.retry(async () => {
      const resp = await this.client.get(this.userPath("/items"), { params });
      const total = parseInt(resp.headers["total-results"] ?? "0", 10);
      return { items: resp.data as Record<string, unknown>[], total };
    });
  }

  async createItem(itemData: Record<string, unknown>[]): Promise<Record<string, unknown>> {
    return this.retry(async () => {
      const resp = await this.client.post(this.userPath("/items"), itemData);
      return resp.data as Record<string, unknown>;
    });
  }

  async getItem(key: string): Promise<Record<string, unknown>> {
    return this.retry(async () => {
      const resp = await this.client.get(this.userPath(`/items/${key}`));
      return resp.data as Record<string, unknown>;
    });
  }

  async updateItem(key: string, data: Record<string, unknown>, version: number): Promise<void> {
    return this.retry(async () => {
      await this.client.patch(this.userPath(`/items/${key}`), data, {
        headers: { "If-Unmodified-Since-Version": String(version) },
      });
    });
  }

  async listCollections(parentKey?: string): Promise<Record<string, unknown>[]> {
    return this.retry(async () => {
      const path = parentKey
        ? this.userPath(`/collections/${parentKey}/collections`)
        : this.userPath("/collections");
      const resp = await this.client.get(path);
      return resp.data as Record<string, unknown>[];
    });
  }

  async getBibliography(params: Record<string, string | number>): Promise<string> {
    return this.retry(async () => {
      const resp = await this.client.get(this.userPath("/items"), {
        params: { ...params, format: "bib" },
        headers: { Accept: "text/html" },
      });
      return resp.data as string;
    });
  }

  async getCollectionItems(collectionKey: string, params: Record<string, string | number>): Promise<{ items: Record<string, unknown>[]; total: number }> {
    return this.retry(async () => {
      const resp = await this.client.get(this.userPath(`/collections/${collectionKey}/items`), { params });
      const total = parseInt(resp.headers["total-results"] ?? "0", 10);
      return { items: resp.data as Record<string, unknown>[], total };
    });
  }
}
