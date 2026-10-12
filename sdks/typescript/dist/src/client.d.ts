import type { Agent, AgentResult, Page, Skill } from "./generated.js";
import { SDKError, type RetryPolicy, type TimeoutPolicy } from "./errors.js";
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
export declare class Client {
    private baseUrl;
    private apiKey;
    private retry;
    private timeout;
    private fetchFn;
    constructor(baseUrl: string, apiKey: string, opts?: ClientOptions);
    private headers;
    private req;
    createAgent(manifest: Agent): Promise<{
        agentId: string;
        state: string;
    }>;
    listAgents(limit?: number): Promise<Page<Record<string, unknown>>>;
    createTask(agentId: string, input: TaskInput): Promise<AgentResult>;
    getTask(taskId: string): Promise<AgentResult>;
    cancelTask(taskId: string): Promise<{
        taskId: string;
        state: string;
    }>;
    invokeTool(name: string, args: Record<string, unknown>, grants?: string[]): Promise<{
        ok: boolean;
        result: unknown;
    }>;
    registerSkill(manifest: Skill): Promise<Skill & {
        _digest: string;
    }>;
    memoryWrite(content: string, scope?: string): Promise<unknown>;
    memorySearch(q: string): Promise<{
        items: unknown[];
    }>;
    artifactCreate(dataBase64: string, filename?: string, classification?: string): Promise<Record<string, unknown>>;
    artifactGet(artifactId: string): Promise<{
        artifactId: string;
        dataBase64: string;
    }>;
    automationCreate(name: string, trigger: Record<string, unknown>): Promise<Record<string, unknown>>;
    webhookRegister(url: string, events: string[]): Promise<Record<string, unknown>>;
    agentCard(): Promise<Record<string, unknown>>;
    streamTaskEvents(taskId: string): AsyncGenerator<Record<string, unknown>, void, void>;
}
export { SDKError };
export type { Agent, AgentResult, Page, Skill };
