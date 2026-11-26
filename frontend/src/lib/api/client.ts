import type { ApiErrorPayload } from "@/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiRequestError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let accessToken: string | null = null;
let refreshHandler: (() => Promise<string | null>) | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setRefreshHandler(handler: (() => Promise<string | null>) | null): void {
  refreshHandler = handler;
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as T;
}

async function toApiError(response: Response): Promise<ApiRequestError> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload?.error?.message) {
      return new ApiRequestError(
        response.status,
        payload.error.code || "http_error",
        payload.error.message,
        payload.error.details,
      );
    }
  } catch {
    // ignore parse errors
  }
  return new ApiRequestError(
    response.status,
    "http_error",
    `Request failed with status ${response.status}`,
  );
}

export interface ApiRequestOptions extends RequestInit {
  skipAuth?: boolean;
  skipRefresh?: boolean;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { skipAuth = false, skipRefresh = false, headers, ...init } = options;
  const requestHeaders = new Headers(headers || {});

  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;
  if (!isFormData && !requestHeaders.has("Content-Type") && init.body !== undefined) {
    requestHeaders.set("Content-Type", "application/json");
  }
  if (!skipAuth && accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(buildUrl(path), {
    ...init,
    headers: requestHeaders,
    credentials: "include",
  });

  if (response.status === 401 && !skipAuth && !skipRefresh && refreshHandler) {
    const newToken = await refreshHandler();
    if (newToken) {
      const retryHeaders = new Headers(headers || {});
      if (!isFormData && !retryHeaders.has("Content-Type") && init.body !== undefined) {
        retryHeaders.set("Content-Type", "application/json");
      }
      retryHeaders.set("Authorization", `Bearer ${newToken}`);
      const retryResponse = await fetch(buildUrl(path), {
        ...init,
        headers: retryHeaders,
        credentials: "include",
      });
      if (!retryResponse.ok) {
        throw await toApiError(retryResponse);
      }
      return parseResponse<T>(retryResponse);
    }
    unauthorizedHandler?.();
    throw await toApiError(response);
  }

  if (!response.ok) {
    if (response.status === 401 && !skipRefresh) {
      unauthorizedHandler?.();
    }
    throw await toApiError(response);
  }

  return parseResponse<T>(response);
}

export const apiClient = {
  getHealth: () => apiRequest<{ status: string }>("/health", { skipAuth: true }),
};
