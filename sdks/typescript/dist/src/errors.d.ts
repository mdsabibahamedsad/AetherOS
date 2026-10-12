export interface SDKErrorShape {
    code: string;
    message: string;
    category: string;
    retryable: boolean;
    requestId: string;
    remediation: string;
    status: number;
}
export declare class SDKError extends Error implements SDKErrorShape {
    code: string;
    category: string;
    retryable: boolean;
    requestId: string;
    remediation: string;
    status: number;
    constructor(init: Partial<SDKErrorShape> & {
        message: string;
    });
    static fromResponse(status: number, payload: unknown): SDKError;
}
export interface RetryPolicy {
    maxAttempts: number;
    baseDelayMs: number;
    maxDelayMs: number;
    jitter: boolean;
}
export declare const defaultRetry: RetryPolicy;
export declare function retryDelay(policy: RetryPolicy, attempt: number): number;
export interface TimeoutPolicy {
    requestMs: number;
    streamIdleMs: number;
    totalDeadlineMs: number;
}
export declare const defaultTimeout: TimeoutPolicy;
export declare function isRetryStatus(status: number): boolean;
