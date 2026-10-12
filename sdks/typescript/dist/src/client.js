import { SDKError, defaultRetry, defaultTimeout, isRetryStatus, retryDelay, } from "./errors.js";
function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}
export class Client {
    baseUrl;
    apiKey;
    retry;
    timeout;
    fetchFn;
    constructor(baseUrl, apiKey, opts = {}) {
        this.baseUrl = baseUrl.replace(/\/$/, "");
        this.apiKey = apiKey;
        this.retry = { ...defaultRetry, ...(opts.retry ?? {}) };
        this.timeout = { ...defaultTimeout, ...(opts.timeout ?? {}) };
        this.fetchFn =
            opts.fetchFn ?? globalThis.fetch ?? fetch;
        if (!this.fetchFn)
            throw new Error("no fetch implementation available");
    }
    headers(idempotencyKey = "") {
        const h = {
            "Content-Type": "application/json",
            "X-API-Key": this.apiKey,
            "X-Request-Id": `ts_${Math.random().toString(36).slice(2, 12)}`,
        };
        if (idempotencyKey)
            h["Idempotency-Key"] = idempotencyKey;
        return h;
    }
    async req(method, path, body, idempotencyKey = "") {
        const deadline = Date.now() + this.timeout.totalDeadlineMs;
        let last = null;
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
                let payload = text;
                try {
                    payload = text ? JSON.parse(text) : null;
                }
                catch {
                    /* keep text */
                }
                if (isRetryStatus(resp.status) && attempt + 1 < this.retry.maxAttempts) {
                    last = SDKError.fromResponse(resp.status, payload);
                    await sleep(retryDelay(this.retry, attempt));
                    continue;
                }
                if (resp.status >= 400)
                    throw SDKError.fromResponse(resp.status, payload);
                return payload;
            }
            catch (e) {
                if (e instanceof SDKError)
                    throw e;
                last = new SDKError({
                    message: e instanceof Error ? e.message.slice(0, 300) : String(e),
                    category: "NETWORK_ERROR",
                    retryable: true,
                });
                if (Date.now() > deadline)
                    break;
                await sleep(retryDelay(this.retry, attempt));
            }
            finally {
                clearTimeout(timer);
            }
        }
        throw last ?? new SDKError({ message: "request failed" });
    }
    createAgent(manifest) {
        return this.req("POST", "/api/v1/agents", manifest, `agent:${manifest.name}:${manifest.version}`);
    }
    listAgents(limit = 20) {
        return this.req("GET", `/api/v1/agents?limit=${limit}`);
    }
    createTask(agentId, input) {
        return this.req("POST", "/api/v1/tasks", { agent: agentId, input }, `task:${Date.now()}:${Math.random().toString(36).slice(2, 8)}`);
    }
    getTask(taskId) {
        return this.req("GET", `/api/v1/tasks/${taskId}`);
    }
    cancelTask(taskId) {
        return this.req("POST", `/api/v1/tasks/${taskId}/cancel`);
    }
    invokeTool(name, args, grants = []) {
        return this.req("POST", `/api/v1/tools/${name}/invoke`, { args, grants });
    }
    registerSkill(manifest) {
        return this.req("POST", "/api/v1/skills", manifest, `skill:${manifest.name}:${manifest.version}`);
    }
    memoryWrite(content, scope = "user") {
        return this.req("POST", "/api/v1/memory/records", { content, scope });
    }
    memorySearch(q) {
        return this.req("GET", `/api/v1/memory/search?q=${encodeURIComponent(q)}`);
    }
    artifactCreate(dataBase64, filename = "", classification = "internal") {
        return this.req("POST", "/api/v1/artifacts", { dataBase64, filename, classification });
    }
    artifactGet(artifactId) {
        return this.req("GET", `/api/v1/artifacts/${artifactId}`);
    }
    automationCreate(name, trigger) {
        return this.req("POST", "/api/v1/automations", { name, trigger });
    }
    webhookRegister(url, events) {
        return this.req("POST", "/api/v1/webhooks", { url, events });
    }
    agentCard() {
        return this.req("GET", "/api/v1/a2a/card");
    }
    async *streamTaskEvents(taskId) {
        const resp = await this.fetchFn(`${this.baseUrl}/api/v1/tasks/${taskId}/events`, { headers: this.headers() });
        if (!resp.ok || !resp.body) {
            throw SDKError.fromResponse(resp.status, await resp.text());
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        for (;;) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buf += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buf.indexOf("\n\n")) >= 0) {
                const frame = buf.slice(0, idx);
                buf = buf.slice(idx + 2);
                const data = frame
                    .split("\n")
                    .filter((l) => l.startsWith("data:"))
                    .map((l) => l.slice(5))
                    .join("");
                if (data.trim().startsWith("{")) {
                    yield JSON.parse(data);
                }
            }
        }
    }
}
export { SDKError };
//# sourceMappingURL=client.js.map