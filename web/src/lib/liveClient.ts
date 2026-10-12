/**
 * Live Chat WebSocket client.
 * Connects to the session server on port 8080 for real-time conversation sync.
 */

export type LiveEvent =
  | "connected"
  | "conversation_history"
  | "user_message"
  | "message.delta"
  | "message.complete"
  | "tool.start"
  | "tool.complete"
  | "status"
  | "input_received"
  | "pong";

export interface LiveMessage {
  event: LiveEvent;
  data: Record<string, unknown>;
  timestamp: number;
}

export type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

export class LiveClient {
  private ws: WebSocket | null = null;
  private _state: ConnectionState = "idle";
  private listeners = new Map<string, Set<(msg: LiveMessage) => void>>();
  private stateListeners = new Set<(s: ConnectionState) => void>();
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _url: string;

  constructor(port = 8080) {
    this._url = `ws://localhost:${port}/ws`;
  }

  get state(): ConnectionState {
    return this._state;
  }

  private setState(s: ConnectionState) {
    if (this._state === s) return;
    this._state = s;
    for (const cb of this.stateListeners) cb(s);
  }

  onState(cb: (s: ConnectionState) => void): () => void {
    this.stateListeners.add(cb);
    cb(this._state);
    return () => this.stateListeners.delete(cb);
  }

  on(event: LiveEvent | "*", cb: (msg: LiveMessage) => void): () => void {
    let set = this.listeners.get(event);
    if (!set) {
      set = new Set();
      this.listeners.set(event, set);
    }
    set.add(cb);
    return () => set!.delete(cb);
  }

  async connect(): Promise<void> {
    if (this._state === "open" || this._state === "connecting") return;
    this.setState("connecting");

    try {
      const ws = new WebSocket(this._url);
      this.ws = ws;

      ws.addEventListener("message", (ev) => {
        try {
          const msg = JSON.parse(ev.data) as LiveMessage;
          this.dispatch(msg);
        } catch { /* skip malformed */ }
      });

      ws.addEventListener("close", () => {
        this.setState("closed");
        this.scheduleReconnect();
      });

      ws.addEventListener("error", () => {
        this.setState("error");
        this.scheduleReconnect();
      });

      await new Promise<void>((resolve, reject) => {
        const onOpen = () => {
          ws.removeEventListener("error", onError);
          this.setState("open");
          resolve();
        };
        const onError = () => {
          ws.removeEventListener("open", onOpen);
          reject(new Error("Connection failed"));
        };
        ws.addEventListener("open", onOpen, { once: true });
        ws.addEventListener("error", onError, { once: true });
      });
    } catch {
      this.setState("error");
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this._reconnectTimer) return;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, 3000);
  }

  close() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.setState("closed");
  }

  send(event: string, data: Record<string, unknown> = {}) {
    if (this._state !== "open" || !this.ws) return;
    this.ws.send(JSON.stringify({ event, data }));
  }

  sendMessage(text: string) {
    this.send("user_message", { text });
  }

  private dispatch(msg: LiveMessage) {
    for (const cb of this.listeners.get(msg.event) ?? []) cb(msg);
    for (const cb of this.listeners.get("*") ?? []) cb(msg);
  }
}

export const liveClient = new LiveClient();
