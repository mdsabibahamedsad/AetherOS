// Typed AetherOS developer client. Works in Node.js 18+ (global fetch) and
// browsers. Secure defaults: TLS verification is the platform default,
// bounded retries/timeouts, idempotency keys on mutations.
import type {
  Agent,
  AgentResult,
  Page,
  Skill,
} from "./generated.js";
import {
  SDKError,
  defaultRetry,
  defaultTimeout,
  isRetryStatus,
  retryDelay,
  type RetryPolicy,
  type TimeoutPolicy,
} from "./errors.js";

export interface ClientOptions {
  retry?: Partial<RetryPolicy>;
  timeout?: Partial<TimeoutPolicy>;
  fetchFn?: typeof fetch;
}

export interface TaskInput {
  capability: string;
  tool?: string;
  args?: Record<string, unknown>;
  [k: string]: unknown;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export class Client {
  private baseUrl: string;
  private apiKey: string;
  private retry: RetryPolicy;
  private timeout: TimeoutPolicy;
  private fetchFn: typeof fetch;

  constructor(baseUrl: string, apiKey: string, opts: ClientOptions = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
    this.retry = { ...defaultRetry, ...(opts.retry ?? {}) };
    this.timeout = { ...defaultTimeout, ...(opts.timeout ?? {}) };
    this.fetchFn =
      opts.fetchFn ?? (globalThis.fetch as typeof fetch | undefined) ?? fetch;
    if (!this.fetchFn) throw new Error("no fetch implementation available");
  }

  private headers(idempotencyKey = ""): Record<string, string> {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": this.apiKey,
      "X-Request-Id": `ts_${Math.random().toString(36).slice(2, 12)}`,
    };
    if (idempotencyKey) h["Idempotency-Key"] = idempotencyKey;
    return h;
  }

  private async req<T>(
    method: string,
    path: string,
    body?: unknown,
    idempotencyKey = "",
  ): Promise<T> {
    const deadline = Date.now() + this.timeout.totalDeadlineMs;
    let last: SDKError | null = null;
    for (let attempt = 0; attempt < this.retry.maxAttempts; attempt++) {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), this.timeout.requestMs);
      try {
        const resp = await this.fetchFn(this.baseUrl + path, {
          method,
          headers: this.headers(idempotencyKey),
          body: body === undefined ? undefined : JSON.stringify(body),
          signal: ctrl.signal,
        });
        const text = await resp.text();
        let payload: unknown = text;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch {
          /* keep text */
        }
        if (isRetryStatus(resp.status) && attempt + 1 < this.retry.maxAttempts) {
          last = SDKError.fromResponse(resp.status, payload);
          await sleep(retryDelay(this.retry, attempt));
          continue;
        }
        if (resp.status >= 400) throw SDKError.fromResponse(resp.status, payload);
        return payload as T;
      } catch (e) {
        if (e instanceof SDKError) throw e;
        last = new SDKError({
          message: e instanceof Error ? e.message.slice(0, 300) : String(e),
          category: "NETWORK_ERROR",
          retryable: true,
        });
        if (Date.now() > deadline) break;
        await sleep(retryDelay(this.retry, attempt));
      } finally {
        clearTimeout(timer);
      }
    }
    throw last ?? new SDKError({ message: "request failed" });
  }

  createAgent(manifest: Agent): Promise<{ agentId: string; state: string }> {
    return this.req("POST", "/api/v1/agents", manifest,
      `agent:${manifest.name}:${manifest.version}`);
  }

  listAgents(limit = 20): Promise<Page<Record<string, unknown>>> {
    return this.req("GET", `/api/v1/agents?limit=${limit}`);
  }

  createTask(agentId: string, input: TaskInput): Promise<AgentResult> {
    return this.req("POST", "/api/v1/tasks", { agent: agentId, input },
      `task:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`);
  }

  getTask(taskId: string): Promise<AgentResult> {
    return this.req("GET", `/api/v1/tasks/${taskId}`);
  }

  cancelTask(taskId: string): Promise<{ taskId: string; state: string }> {
    return this.req("POST", `/api/v1/tasks/${taskId}/cancel`);
  }

  invokeTool(
    name: string,
    args: Record<string, unknown>,
    grants: string[] = [],
  ): Promise<{ ok: boolean; result: unknown }> {
    return this.req("POST", `/api/v1/tools/${name}/invoke`, { args, grants });
  }

  registerSkill(manifest: Skill): Promise<Skill & { _digest: string }> {
    return this.req("POST", "/api/v1/skills", manifest,
      `skill:${manifest.name}:${manifest.version}`);
  }

  memoryWrite(content: string, scope = "user"): Promise<unknown> {
    return this.req("POST", "/api/v1/memory/records", { content, scope });
  }

  memorySearch(q: string): Promise<{ items: unknown[] }> {
    return this.req(
      "GET", `/api/v1/memory/search?q=${encodeURIComponent(q)}`);
  }

  artifactCreate(
    dataBase64: string,
    filename = "",
    classification = "internal",
  ): Promise<Record<string, unknown>> {
    return this.req("POST", "/api/v1/artifacts",
      { dataBase64, filename, classification });
  }

  artifactGet(artifactId: string): Promise<{ artifactId: string; dataBase64: string }> {
    return this.req("GET", `/api/v1/artifacts/${artifactId}`);
  }

  automationCreate(
    name: string,
    trigger: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    return this.req("POST", "/api/v1/automations", { name, trigger });
  }

  webhookRegister(
    url: string,
    events: string[],
  ): Promise<Record<string, unknown>> {
    return this.req("POST", "/api/v1/webhooks", { url, events });
  }

  agentCard(): Promise<Record<string, unknown>> {
    return this.req("GET", "/api/v1/a2a/card");
  }

  async *streamTaskEvents(
    taskId: string,
  ): AsyncGenerator<Record<string, unknown>, void, void> {
    const resp = await this.fetchFn(
      `${this.baseUrl}/api/v1/tasks/${taskId}/events`,
      { headers: this.headers() },
    );
    if (!resp.ok || !resp.body) {
      throw SDKError.fromResponse(resp.status, await resp.text());
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const frame = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const data = frame
          .split("\n")
          .filter((l) => l.startsWith("data:"))
          .map((l) => l.slice(5))
          .join("");
        if (data.trim().startsWith("{")) {
          yield JSON.parse(data) as Record<string, unknown>;
        }
      }
    }
  }
}

export { SDKError };
export type { Agent, AgentResult, Page, Skill };
