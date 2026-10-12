const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status: number };

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  const url = `${BASE_URL}${path}`;
  const { method = "GET", body, headers, signal } = options;

  try {
    const res = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "unknown error");
      return { ok: false, error: text, status: res.status };
    }

    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "network error",
      status: 0,
    };
  }
}

export async function healthCheck() {
  return apiFetch<{ status: string; checks: Record<string, string> }>(
    "/api/v1/health",
    { method: "GET" },
  );
}
