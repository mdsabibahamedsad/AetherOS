// Typed SDK errors + bounded retry/timeout policies. No secrets in messages.
export interface SDKErrorShape {
  code: string;
  message: string;
  category: string;
  retryable: boolean;
  requestId: string;
  remediation: string;
  status: number;
}

export class SDKError extends Error implements SDKErrorShape {
  code: string;
  category: string;
  retryable: boolean;
  requestId: string;
  remediation: string;
  status: number;

  constructor(init: Partial<SDKErrorShape> & { message: string }) {
    super(init.message);
    this.name = "SDKError";
    this.code = init.code ?? "INTERNAL_ERROR";
    this.category = init.category ?? "INTERNAL_ERROR";
    this.retryable = init.retryable ?? false;
    this.requestId = init.requestId ?? "";
    this.remediation = init.remediation ?? "";
    this.status = init.status ?? 500;
  }

  static fromResponse(status: number, payload: unknown): SDKError {
    if (payload && typeof payload === "object") {
      const p = payload as Record<string, unknown>;
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

export interface RetryPolicy {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  jitter: boolean;
}

export const defaultRetry: RetryPolicy = {
  maxAttempts: 4,
  baseDelayMs: 500,
  maxDelayMs: 8000,
  jitter: true,
};

export function retryDelay(policy: RetryPolicy, attempt: number): number {
  const d = Math.min(policy.maxDelayMs, policy.baseDelayMs * 2 ** attempt);
  return policy.jitter ? d * (0.5 + Math.random() * 0.5) : d;
}

export interface TimeoutPolicy {
  requestMs: number;
  streamIdleMs: number;
  totalDeadlineMs: number;
}

export const defaultTimeout: TimeoutPolicy = {
  requestMs: 30000,
  streamIdleMs: 30000,
  totalDeadlineMs: 300000,
};

const RETRY_STATUS = new Set([429, 502, 503, 504]);
export function isRetryStatus(status: number): boolean {
  return RETRY_STATUS.has(status);
}
