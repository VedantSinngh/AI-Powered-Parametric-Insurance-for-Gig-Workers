const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

type HttpMethod = "GET" | "POST" | "PATCH";

async function apiRequest<TResponse>(
  method: HttpMethod,
  path: string,
  token?: string,
  body?: unknown,
): Promise<TResponse> {
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(buildUrl(path), {
    method,
    headers,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Request failed";
    throw new ApiError(detail, response.status);
  }

  return data as TResponse;
}

export async function apiPost<TResponse>(
  path: string,
  body: unknown,
  token?: string,
): Promise<TResponse> {
  return apiRequest<TResponse>("POST", path, token, body);
}

export async function apiGet<TResponse>(path: string, token?: string): Promise<TResponse> {
  return apiRequest<TResponse>("GET", path, token);
}

export async function apiPatch<TResponse>(
  path: string,
  body?: unknown,
  token?: string,
): Promise<TResponse> {
  return apiRequest<TResponse>("PATCH", path, token, body);
}
