/**
 * LiveChatPage — real-time AI chat interface.
 *
 * Three-panel layout with live WebSocket sync to the terminal agent.
 * One conversation, one session, two interfaces.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, Bot, ChevronLeft, ChevronRight, Cpu, Database,
  FileText, FolderOpen, GitBranch, HardDrive, History,
  MessageSquare, PanelRightClose, PanelRightOpen, Plug,
  Send, Terminal, Users, Zap,
} from "lucide-react";
import { liveClient } from "@/lib/liveClient";

interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: number;
  tool_name?: string;
}

interface SystemStatus {
  model: string;
  context: number;
  tasks: number;
  cpu: number;
  ram: number;
  git?: string;
  connection: "connected" | "disconnected" | "connecting";
  tokens: number;
  runtime: string;
}

function simpleMarkdown(text: string): string {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g,
    (_, lang, code) => '<pre><code class="lang-' + (lang || "none") + '">' + code + "</code></pre>"
  );
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/\n/g, "<br>");
  return html;
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === "tool") {
    return (
      <div className="flex gap-2 px-4 py-1">
        <div className="flex items-center gap-2 rounded-lg bg-blue-500/10 px-3 py-1.5 text-xs text-blue-300">
          <Zap className="h-3 w-3 shrink-0" />
          <span className="font-medium">{msg.tool_name || "tool"}</span>
          <span className="text-blue-400/60">\u00b7</span>
          <span className="truncate max-w-md text-blue-400/70">
            {msg.content.slice(0, 120)}
          </span>
        </div>
      </div>
    );
  }
  const isUser = msg.role === "user";
  return (
    <div className={"flex " + (isUser ? "justify-end" : "justify-start") + " px-4 py-1"}>
      <div className={
        "max-w-[80%] rounded-2xl px-4 py-2.5 " +
        (isUser
          ? "bg-blue-600 text-white"
          : "border border-zinc-700/50 bg-zinc-800/50 text-zinc-100")
      }>
        {isUser ? (
          <p className="text-sm leading-relaxed">{msg.content}</p>
        ) : (
          <div
            className="prose prose-invert prose-sm max-w-none leading-relaxed [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-zinc-900 [&_pre]:p-3 [&_code]:text-blue-300"
            dangerouslySetInnerHTML={{ __html: simpleMarkdown(msg.content) }}
          />
        )}
        <div className={"mt-1 text-[10px] " + (isUser ? "text-blue-200" : "text-zinc-500")}>
          {new Date(msg.timestamp * 1000).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

const NAV_ITEMS = [
  { icon: MessageSquare, label: "Sessions" },
  { icon: History, label: "History" },
  { icon: FolderOpen, label: "Projects" },
  { icon: Bot, label: "Agents" },
  { icon: FileText, label: "Files" },
  { icon: Database, label: "Memory" },
  { icon: Plug, label: "Plugins" },
];

function LeftSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside className={
      "flex flex-col border-r border-zinc-800 bg-zinc-900/50 transition-all duration-200 " +
      (collapsed ? "w-14" : "w-56")
    }>
      <div className="flex h-12 items-center justify-between border-b border-zinc-800 px-3">
        {!collapsed && (<span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">AetherOS</span>)}
        <button onClick={onToggle} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300">
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV_ITEMS.map((item) => (
          <button key={item.label} className={
            "flex w-full items-center gap-3 px-3 py-2 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors " +
            (collapsed ? "justify-center" : "")
          }>
            <item.icon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>
      {!collapsed && (
        <div className="border-t border-zinc-800 px-3 py-2">
          <button className="flex w-full items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-500 transition-colors">
            <Terminal className="h-3.5 w-3.5 shrink-0" />Open Terminal
          </button>
        </div>
      )}
    </aside>
  );
}

function RightSidebar({ collapsed, onToggle, status }: { collapsed: boolean; onToggle: () => void; status: SystemStatus }) {
  const items = [
    { icon: Bot, label: "Model", value: status.model || "\u2014" },
    { icon: Activity, label: "Context", value: status.context ? status.context.toLocaleString() + " tokens" : "\u2014" },
    { icon: Users, label: "Tasks", value: status.tasks + " running" },
    { icon: Cpu, label: "CPU", value: status.cpu + "%" },
    { icon: HardDrive, label: "RAM", value: status.ram + "%" },
    { icon: GitBranch, label: "Git", value: status.git || "\u2014" },
    { icon: FileText, label: "Logs", value: "\u2014" },
  ];
  return (
    <aside className={
      "flex flex-col border-l border-zinc-800 bg-zinc-900/50 transition-all duration-200 " +
      (collapsed ? "w-0 overflow-hidden" : "w-64")
    }>
      <div className="flex h-12 items-center justify-between border-b border-zinc-800 px-3">
        {!collapsed && (<span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">System</span>)}
        <button onClick={onToggle} className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300">
          {collapsed ? <ChevronLeft className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3 p-3">
        {items.map((item) => (
          <div key={item.label} className="space-y-0.5">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500">
              <item.icon className="h-3 w-3" /><span>{item.label}</span>
            </div>
            <div className="truncate text-sm text-zinc-200">{item.value}</div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function StatusBar({ status }: { status: SystemStatus }) {
  const dotColor = status.connection === "connected"
    ? "bg-green-500" : status.connection === "connecting"
    ? "bg-yellow-500" : "bg-red-500";
  return (
    <footer className="flex h-8 items-center justify-between border-t border-zinc-800 bg-zinc-900 px-4 text-[11px] text-zinc-500">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className={"h-1.5 w-1.5 rounded-full " + dotColor} />
          <span>{status.connection}</span>
        </div>
        <span>{status.tokens.toLocaleString()} tokens</span>
        <span>{status.runtime}</span>
      </div>
      <div className="flex items-center gap-3">
        <span>CPU {status.cpu}%</span><span>RAM {status.ram}%</span>
      </div>
    </footer>
  );
}

export default function LiveChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [status, setStatus] = useState<SystemStatus>({
    model: "", context: 0, tasks: 0, cpu: 0, ram: 0,
    connection: "disconnected", tokens: 0, runtime: "0m",
  });
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    liveClient.connect();
    const unsubs = [
      liveClient.on("connected", () => {
        setConnected(true);
        setStatus(s => ({ ...s, connection: "connected" }));
      }),
      liveClient.on("conversation_history", (msg) => {
        const history = (msg.data?.messages as Array<Record<string, unknown>>) || [];
        setMessages(history.map((m: any) => ({
          id: String(m.id || Math.random()),
          role: m.role || "user",
          content: String(m.content || ""),
          timestamp: Number(m.timestamp || Date.now() / 1000),
          tool_name: m.tool_name,
        })));
      }),
      liveClient.on("user_message", (msg) => {
        const text = msg.data?.text as string;
        if (text) setMessages(p => [...p, {
          id: "user-" + Date.now(), role: "user",
          content: text, timestamp: Date.now() / 1000,
        }]);
      }),
      liveClient.on("message.delta", (msg) => {
        const c = msg.data?.content as string;
        if (c) setStreamingContent(c);
      }),
      liveClient.on("message.complete", (msg) => {
        const content = msg.data?.content as string;
        if (content) {
          setMessages(p => [...p, {
            id: "msg-" + Date.now(),
            role: (msg.data?.role as any) || "assistant",
            content, timestamp: Date.now() / 1000,
          }]);
          setStreamingContent("");
        }
      }),
      liveClient.on("tool.start", (msg) => {
        const name = msg.data?.name as string;
        if (name) setMessages(p => [...p, {
          id: "tool-" + Date.now(), role: "tool",
          content: "Running " + name + "...",
          timestamp: Date.now() / 1000, tool_name: name,
        }]);
      }),
      liveClient.on("status", (msg) => {
        const s = msg.data as any;
        if (s) setStatus(p => ({
          ...p, model: s.model || p.model,
          context: s.context || p.context,
          tasks: s.tasks || p.tasks,
          tokens: s.tokens || p.tokens,
        }));
      }),
    ];
    return () => { unsubs.forEach(fn => fn()); };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    liveClient.sendMessage(text);
    setMessages(p => [...p, {
      id: "user-" + Date.now(), role: "user",
      content: text, timestamp: Date.now() / 1000,
    }]);
    setInput("");
  }, [input]);

  return (
    <div className="flex h-full flex-col bg-zinc-950 text-zinc-100">
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <LeftSidebar collapsed={leftCollapsed}
          onToggle={() => setLeftCollapsed(!leftCollapsed)} />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto py-4">
            {messages.length === 0 && !streamingContent && (
              <div className="flex h-full items-center justify-center">
                <div className="space-y-2 text-center">
                  <Bot className="mx-auto h-10 w-10 text-zinc-600" />
                  <h2 className="text-lg font-semibold text-zinc-400">
                    {connected ? "Connected to AetherOS" : "Connecting..."}
                  </h2>
                  <p className="text-sm text-zinc-600">
                    Messages sync in real time between terminal and browser.
                  </p>
                </div>
              </div>
            )}
            {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
            {streamingContent && (
              <div className="flex justify-start px-4 py-1">
                <div className="max-w-[80%] rounded-2xl border border-zinc-700/50 bg-zinc-800/50 px-4 py-2.5">
                  <div className="prose prose-invert prose-sm max-w-none"
                    dangerouslySetInnerHTML={{
                      __html: simpleMarkdown(streamingContent),
                    }} />
                  <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-blue-400" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="border-t border-zinc-800 p-3">
            <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-zinc-700 bg-zinc-800/50 p-2 focus-within:border-blue-500/50">
              <textarea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder="Type a message..." rows={1}
                className="min-h-[2rem] flex-1 resize-none bg-transparent text-sm text-zinc-100 outline-none placeholder:text-zinc-500" />
              <button onClick={handleSend} disabled={!input.trim()}
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
        <RightSidebar collapsed={rightCollapsed}
          onToggle={() => setRightCollapsed(!rightCollapsed)} status={status} />
      </div>
      <StatusBar status={status} />
    </div>
  );
}
