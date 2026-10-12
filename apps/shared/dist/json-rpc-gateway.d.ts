export type GatewayEventName = 'gateway.ready' | 'session.info' | 'message.start' | 'message.delta' | 'message.complete' | 'thinking.delta' | 'reasoning.delta' | 'reasoning.available' | 'status.update' | 'tool.start' | 'tool.progress' | 'tool.complete' | 'tool.generating' | 'clarify.request' | 'approval.request' | 'sudo.request' | 'secret.request' | 'background.complete' | 'error' | 'skin.changed' | (string & {});
export interface GatewayEvent<P = unknown> {
    payload?: P;
    session_id?: string;
    type: GatewayEventName;
}
export type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';
export type GatewayRequestId = number | string;
export interface JsonRpcFrame {
    error?: {
        message?: string;
    };
    id?: GatewayRequestId | null;
    method?: string;
    params?: GatewayEvent;
    result?: unknown;
}
export type WebSocketLike = WebSocket;
export interface GatewayClientOptions {
    closedErrorMessage?: string;
    connectErrorMessage?: string;
    connectTimeoutMs?: number;
    createRequestId?: (nextId: number) => GatewayRequestId;
    requestIdPrefix?: string;
    requestTimeoutMs?: number;
    socketFactory?: (url: string) => WebSocketLike;
    notConnectedErrorMessage?: string;
}
export declare class JsonRpcGatewayClient {
    private nextId;
    private pending;
    private socket;
    private state;
    private readonly eventHandlers;
    private readonly stateHandlers;
    private readonly options;
    constructor(options?: GatewayClientOptions);
    get connectionState(): ConnectionState;
    connect(wsUrl: string): Promise<void>;
    close(): void;
    on<P = unknown>(type: GatewayEventName, handler: (event: GatewayEvent<P>) => void): () => void;
    onAny(handler: (event: GatewayEvent) => void): () => void;
    onEvent(handler: (event: GatewayEvent) => void): () => void;
    onState(handler: (state: ConnectionState) => void): () => void;
    request<T>(method: string, params?: Record<string, unknown>, timeoutMs?: number): Promise<T>;
    private handleMessage;
    private clearPending;
    private dispatchEvent;
    private rejectAllPending;
    private setState;
}
//# sourceMappingURL=json-rpc-gateway.d.ts.map