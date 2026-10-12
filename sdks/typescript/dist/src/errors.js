export class SDKError extends Error {
    code;
    category;
    retryable;
    requestId;
    remediation;
    status;
    constructor(init) {
        super(init.message);
        this.name = "SDKError";
        this.code = init.code ?? "INTERNAL_ERROR";
        this.category = init.category ?? "INTERNAL_ERROR";
        this.retryable = init.retryable ?? false;
        this.requestId = init.requestId ?? "";
        this.remediation = init.remediation ?? "";
        this.status = init.status ?? 500;
    }
    static fromResponse(status, payload) {
        if (payload && typeof payload === "object") {
            const p = payload;
            return new SDKError({
                code: String(p.code ?? `HTTP_${status}`),
                message: String(p.message ?? "").slice(0, 500),
                category: String(p.category ?? "INTERNAL_ERROR"),
                retryable: Boolean(p.retryable ?? false),
                requestId: String(p.requestId ?? ""),
                remediation: String(p.remediation ?? ""),
                status,
            });
        }
        return new SDKError({ message: String(payload).slice(0, 500), status });
    }
}
export const defaultRetry = {
    maxAttempts: 4,
    baseDelayMs: 500,
    maxDelayMs: 8000,
    jitter: true,
};
export function retryDelay(policy, attempt) {
    const d = Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** attempt);
    return policy.jitter ? d * (0.5 + Math.random() * 0.5) : d;
}
export const defaultTimeout = {
    requestMs: 30000,
    streamIdleMs: 30000,
    totalDeadlineMs: 300000,
};
const RETRY_STATUS = new Set([429, 502, 503, 504]);
export function isRetryStatus(status) {
    return RETRY_STATUS.has(status);
}
//# sourceMappingURL=errors.js.map