import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { USER_AGENT, MAX_RETRIES, RETRY_BASE_DELAY, DEFAULT_TIMEOUT } from "./constants.js";

export interface ApiClientOptions {
  baseURL: string;
  timeout?: number;
  rateLimit?: number;
  headers?: Record<string, string>;
}

export class ApiClient {
  private client: AxiosInstance;
  private lastRequest: number = 0;
  private minInterval: number;

  constructor(options: ApiClientOptions) {
    this.minInterval = options.rateLimit ? 1000 / options.rateLimit : 0;
    this.client = axios.create({
      baseURL: options.baseURL,
      timeout: options.timeout ?? DEFAULT_TIMEOUT,
      headers: { "User-Agent": USER_AGENT, ...options.headers },
    });
  }

  private async rateLimit(): Promise<void> {
    if (this.minInterval <= 0) return;
    const now = Date.now();
    const wait = Math.max(0, this.minInterval - (now - this.lastRequest));
    if (wait > 0) await new Promise(r => setTimeout(r, wait));
    this.lastRequest = Date.now();
  }

  async get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.requestWithRetry<T>("get", url, config);
  }

  async post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.requestWithRetry<T>("post", url, { ...config, data });
  }

  private async requestWithRetry<T>(method: string, url: string, config?: AxiosRequestConfig & { data?: unknown }): Promise<AxiosResponse<T>> {
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        await this.rateLimit();
        const resp = method === "post"
          ? await this.client.post<T>(url, config?.data, config)
          : await this.client.get<T>(url, config);
        return resp;
      } catch (error) {
        if (attempt < MAX_RETRIES && axios.isAxiosError(error)) {
          const status = error.response?.status ?? 0;
          if (status >= 500 || status === 429 || error.code === "ECONNABORTED") {
            const delay = RETRY_BASE_DELAY * Math.pow(2, attempt);
            console.error(`[api-client] Retry ${attempt + 1}/${MAX_RETRIES} after ${delay}ms (${status || error.code})`);
            await new Promise(r => setTimeout(r, delay));
            continue;
          }
        }
        throw error;
      }
    }
    throw new Error("Max retries exceeded");
  }
}
