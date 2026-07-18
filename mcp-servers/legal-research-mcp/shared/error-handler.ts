import { AxiosError } from "axios";

interface McpError {
  message: string;
  suggestion: string;
  code: string;
}

export function handleApiError(error: unknown, source: string): McpError {
  if (error instanceof AxiosError) {
    const status = error.response?.status;
    switch (status) {
      case 400: return { message: `${source}: Cerere invalidă.`, suggestion: "Verificați parametrii de căutare.", code: "BAD_REQUEST" };
      case 401: return { message: `${source}: Autentificare eșuată.`, suggestion: "Verificați cheia API sau credențialele.", code: "AUTH_ERROR" };
      case 403: return { message: `${source}: Acces interzis.`, suggestion: "Verificați permisiunile cheii API.", code: "FORBIDDEN" };
      case 404: return { message: `${source}: Documentul nu a fost găsit.`, suggestion: "Verificați identificatorul documentului.", code: "NOT_FOUND" };
      case 429: return { message: `${source}: Limita de cereri depășită.`, suggestion: "Așteptați câteva secunde și reîncercați.", code: "RATE_LIMIT" };
      case 500: case 502: case 503:
        return { message: `${source}: Serverul nu răspunde.`, suggestion: "Reîncercați peste câteva momente.", code: "SERVER_ERROR" };
      default:
        if (error.code === "ECONNABORTED") {
          return { message: `${source}: Timeout — serverul nu a răspuns la timp.`, suggestion: "Reîncercați cu o căutare mai specifică.", code: "TIMEOUT" };
        }
        return { message: `${source}: Eroare de rețea (${error.message}).`, suggestion: "Verificați conexiunea la internet.", code: "NETWORK_ERROR" };
    }
  }
  return { message: `${source}: Eroare neașteptată.`, suggestion: "Reîncercați operația.", code: "UNKNOWN" };
}

export function formatErrorResponse(error: unknown, source: string): string {
  const err = handleApiError(error, source);
  return JSON.stringify({ error: err.message, suggestion: err.suggestion, code: err.code });
}
