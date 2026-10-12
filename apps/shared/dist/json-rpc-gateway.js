const ANY = '*';
const DEFAULT_REQUEST_TIMEOUT_MS = 120_000;
// A reconnect after sleep/wake must not hang forever in 'connecting' (which
// keeps the composer disabled and stuck on "Starting Aetheros..."). If the open
// handshake doesn't land in this window, fail to 'error' so callers can retry.
const DEFAULT_CONNECT_TIMEOUT_MS = 15_000;
export class JsonRpcGatewayClient {
    nextId = 0;
    pending = new Map();
    socket = null;
    state = 'idle';
    eventHandlers = new Map();
    stateHandlers = new Set();
    options;
    constructor(options = {}) {
        this.options = {
            closedErrorMessage: options.closedErrorMessage ?? 'WebSocket closed',
            connectErrorMessage: options.connectErrorMessage ?? 'WebSocket connection failed',
            connectTimeoutMs: options.connectTimeoutMs ?? DEFAULT_CONNECT_TIMEOUT_MS,
            createRequestId: options.createRequestId ?? ((nextId) => `${options.requestIdPrefix ?? 'r'}${nextId}`),
            notConnectedErrorMessage: options.notConnectedErrorMessage ?? 'gateway not connected',
            requestIdPrefix: options.requestIdPrefix ?? 'r',
            requestTimeoutMs: options.requestTimeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS,
            socketFactory: options.socketFactory
        };
    }
    get connectionState() {
        return this.state;
    }
    async connect(wsUrl) {
        if (this.socket?.readyState === WebSocket.OPEN || this.state === 'connecting') {
            return;
        }
        this.setState('connecting');
        const socket = this.options.socketFactory?.(wsUrl) ?? new WebSocket(wsUrl);
        this.socket = socket;
        socket.addEventListener('message', message => {
            if (this.socket !== socket) {
                return;
            }
            this.handleMessage(message.data);
        });
        socket.addEventListener('close', () => {
            if (this.socket !== socket) {
                return;
            }
            this.socket = null;
            this.setState('closed');
            this.rejectAllPending(new Error(this.options.closedErrorMessage));
        });
        await new Promise((resolve, reject) => {
            let settled = false;
            let timer;
            const cleanup = () => {
                if (timer !== undefined) {
                    clearTimeout(timer);
                }
                socket.removeEventListener('open', onOpen);
                socket.removeEventListener('error', onError);
            };
            const onOpen = () => {
                if (settled || this.socket !== socket) {
                    return;
                }
                settled = true;
                cleanup();
                this.setState('open');
                resolve();
            };
            const onError = () => {
                if (settled || this.socket !== socket) {
                    return;
                }
                settled = true;
                cleanup();
                this.setState('error');
                reject(new Error(this.options.connectErrorMessage));
            };
            socket.addEventListener('open', onOpen, { once: true });
            socket.addEventListener('error', onError, { once: true });
            if (this.options.connectTimeoutMs > 0) {
                timer = setTimeout(() => {
                    if (settled) {
                        return;
                    }
                    settled = true;
                    cleanup();
                    // Drop the half-open socket so the next connect() starts clean
                    // instead of short-circuiting on a zombie 'connecting' state.
                    if (this.socket === socket) {
                        try {
                            socket.close();
                        }
                        catch {
                            // ignore
                        }
                        this.socket = null;
                    }
                    this.setState('error');
                    reject(new Error(this.options.connectErrorMessage));
                }, this.options.connectTimeoutMs);
            }
        });
    }
    close() {
        this.socket?.close();
        this.socket = null;
    }
    on(type, handler) {
        let handlers = this.eventHandlers.get(type);
        if (!handlers) {
            handlers = new Set();
            this.eventHandlers.set(type, handlers);
        }
        handlers.add(handler);
        return () => handlers?.delete(handler);
    }
    onAny(handler) {
        return this.on(ANY, handler);
    }
    onEvent(handler) {
        return this.onAny(handler);
    }
    onState(handler) {
        this.stateHandlers.add(handler);
        handler(this.state);
        return () => this.stateHandlers.delete(handler);
    }
    request(method, params = {}, timeoutMs = this.options.requestTimeoutMs) {
        const socket = this.socket;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            return Promise.reject(new Error(this.options.notConnectedErrorMessage));
        }
        const id = this.options.createRequestId(++this.nextId);
        return new Promise((resolve, reject) => {
            const pending = {
                reject,
                resolve: value => resolve(value)
            };
            if (timeoutMs > 0) {
                pending.timer = setTimeout(() => {
                    if (this.pending.delete(id)) {
                        reject(new Error(`request timed out: ${method}`));
                    }
                }, timeoutMs);
            }
            this.pending.set(id, pending);
            try {
                socket.send(JSON.stringify({
                    jsonrpc: '2.0',
                    id,
                    method,
                    params
                }));
            }
            catch (error) {
                this.clearPending(id);
                reject(error instanceof Error ? error : new Error(String(error)));
            }
        });
    }
    handleMessage(raw) {
        const text = typeof raw === 'string' ? raw : String(raw);
        let frame;
        try {
            frame = JSON.parse(text);
        }
        catch {
            return;
        }
        if (frame.id !== undefined && frame.id !== null) {
            const call = this.pending.get(frame.id);
            if (!call) {
                return;
            }
            this.clearPending(frame.id);
            if (frame.error) {
                call.reject(new Error(frame.error.message || 'Aetheros RPC failed'));
            }
            else {
                call.resolve(frame.result);
            }
            return;
        }
        if (frame.method === 'event' && frame.params?.type) {
            this.dispatchEvent(frame.params);
        }
    }
    clearPending(id) {
        const call = this.pending.get(id);
        if (call?.timer) {
            clearTimeout(call.timer);
        }
        this.pending.delete(id);
    }
    dispatchEvent(event) {
        for (const handler of this.eventHandlers.get(event.type) ?? []) {
            handler(event);
        }
        for (const handler of this.eventHandlers.get(ANY) ?? []) {
            handler(event);
        }
    }
    rejectAllPending(error) {
        for (const [id, call] of this.pending) {
            if (call.timer) {
                clearTimeout(call.timer);
            }
            call.reject(error);
            this.pending.delete(id);
        }
    }
    setState(state) {
        if (this.state === state) {
            return;
        }
        this.state = state;
        for (const handler of this.stateHandlers) {
            handler(state);
        }
    }
}
//# sourceMappingURL=json-rpc-gateway.js.map