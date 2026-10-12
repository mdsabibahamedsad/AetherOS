import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Server,
  Power,
  RefreshCw,
  Trash2,
  Play,
  Logs,
  Activity,
  Plus,
  Download,
  Upload,
  Search,
  Check,
  X,
  AlertTriangle,
  Clock,
  Wifi,
  WifiOff,
  Eye,
  EyeOff,
  Terminal,
  FileText,
  ExternalLink,
  Database,
  GitBranch,
  Globe,
  Monitor,
  MessageSquare,
  Cpu,
  HardDrive,
  Smartphone,
  BookOpen,
  Cloud,
  Mail,
  Zap,
  Package,
  Settings,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Select, SelectOption } from "@aetheros/ui/ui/components/select";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { useModalBehavior } from "@/hooks/useModalBehavior";
import { api } from "@/lib/api";
import type {
  McpServer,
  McpServerCreate,
  McpServerStatus,
  McpServerLog,
  McpHealthResult,
  McpAutoDiscovery,
} from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

type Transport = "http" | "stdio";

const STATUS_CONFIG: Record<string, { color: string; icon: typeof Activity; label: string }> = {
  healthy: { color: "text-emerald-400", icon: Check, label: "Healthy" },
  warning: { color: "text-amber-400", icon: AlertTriangle, label: "Warning" },
  error: { color: "text-red-400", icon: X, label: "Error" },
  unknown: { color: "text-muted-foreground", icon: AlertTriangle, label: "Unknown" },
};

const MCP_TYPE_ICONS: Record<string, typeof Server> = {
  filesystem: HardDrive,
  git: GitBranch,
  github: GitBranch,
  browser: Monitor,
  docker: Server,
  python: Terminal,
  sqlite: Database,
  postgres: Database,
  mysql: Database,
  redis: Database,
  slack: MessageSquare,
  discord: MessageSquare,
  telegram: MessageSquare,
  "google-drive": Cloud,
  notion: BookOpen,
};

export default function McpManagerPage() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [statuses, setStatuses] = useState<Record<string, McpServerStatus>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [viewLogs, setViewLogs] = useState<string | null>(null);
  const [logs, setLogs] = useState<McpServerLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [healthRunning, setHealthRunning] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [discovered, setDiscovered] = useState<McpAutoDiscovery[]>([]);
  const [showDiscovery, setShowDiscovery] = useState(false);
  const [yamlImport, setYamlImport] = useState("");
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const addModalRef = useModalBehavior({ open: showAddModal, onClose: () => setShowAddModal(false) });

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [serversRes, statusRes] = await Promise.all([
        api.getMcpServers(),
        api.getMcpServersStatus().catch(() => ({ servers: [] })),
      ]);
      setServers(serversRes.servers);
      const statusMap: Record<string, McpServerStatus> = {};
      statusRes.servers.forEach((s) => { statusMap[s.name] = s; });
      setStatuses(statusMap);
    } catch (e) {
      showToast(`Failed to load MCP servers: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadAll(); }, [loadAll]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={() => setShowDiscovery(true)}>
          <Search className="h-4 w-4 mr-1" />
          Discover
        </Button>
        <Button ghost size="sm" onClick={() => setShowImportModal(true)}>
          <Upload className="h-4 w-4 mr-1" />
          Import
        </Button>
        <Button size="sm" onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Add Server
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd]);

  const handleHealthCheck = async (name: string) => {
    setHealthRunning(name);
    try {
      const result = await api.runMcpHealthCheck(name);
      setStatuses((prev) => ({
        ...prev,
        [name]: {
          ...prev[name],
          name,
          status: result.ok ? "healthy" : "error",
          latency_ms: result.latency_ms,
          last_health_check: result.timestamp,
          error_message: result.error,
          tools_count: result.tools.length,
        },
      }));
      showToast(
        result.ok
          ? `${name}: ${result.latency_ms}ms · ${result.tools.length} tools`
          : `${name}: ${result.error ?? "Failed"}`,
        result.ok ? "success" : "error",
      );
    } catch (e) {
      showToast(`Health check failed: ${e}`, "error");
    } finally {
      setHealthRunning(null);
    }
  };

  const handleToggleEnabled = async (server: McpServer) => {
    const next = !server.enabled;
    setToggling(server.name);
    try {
      await api.setMcpServerEnabled(server.name, next);
      setServers((prev) =>
        prev.map((s) => (s.name === server.name ? { ...s, enabled: next } : s)),
      );
    } catch (e) {
      showToast(`Failed: ${e}`, "error");
    } finally {
      setToggling(null);
    }
  };

  const handleRestart = async (name: string) => {
    try {
      await api.restartMcpServer(name);
      showToast(`${name} restarted`, "success");
    } catch (e) {
      showToast(`Restart failed: ${e}`, "error");
    }
  };

  const handleViewLogs = async (name: string) => {
    setViewLogs(name);
    setLogsLoading(true);
    try {
      const res = await api.getMcpServerLogs(name, 100);
      setLogs(res.logs);
    } catch (e) {
      showToast(`Failed to load logs: ${e}`, "error");
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleDiscovery = async () => {
    try {
      const res = await api.discoverLocalMcpServers();
      setDiscovered(res.servers);
    } catch (e) {
      showToast(`Discovery failed: ${e}`, "error");
    }
  };

  const handleImport = async () => {
    if (!yamlImport.trim()) {
      showToast("YAML content required", "error");
      return;
    }
    try {
      const res = await api.importMcpConfig(yamlImport);
      showToast(`Imported ${res.imported} server(s)`, "success");
      setShowImportModal(false);
      setYamlImport("");
      void loadAll();
    } catch (e) {
      showToast(`Import failed: ${e}`, "error");
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await api.removeMcpServer(name);
      setServers((prev) => prev.filter((s) => s.name !== name));
      showToast(`${name} removed`, "success");
    } catch (e) {
      showToast(`Delete failed: ${e}`, "error");
    }
  };

  const filteredServers = useMemo(() => {
    if (!search) return servers;
    const q = search.toLowerCase();
    return servers.filter((s) => s.name.toLowerCase().includes(q));
  }, [servers, search]);

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search servers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : filteredServers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No MCP servers configured
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {filteredServers.map((server) => {
            const status = statuses[server.name];
            const statusCfg = STATUS_CONFIG[status?.status ?? "unknown"];
            const StatusIcon = statusCfg.icon;

            return (
              <Card key={server.name} className={cn(!server.enabled && "opacity-60")}>
                <CardContent className="py-4 px-5">
                  <div className="flex items-start gap-4">
                    <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
                      <Server className="h-4 w-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-medium text-sm">{server.name}</span>
                        <Badge tone={server.transport === "http" ? "success" : "warning"}>
                          {server.transport}
                        </Badge>
                        {status && (
                          <Badge
                            tone={status.status === "healthy" ? "success" : status.status === "error" ? "destructive" : "warning"}
                          >
                            <StatusIcon className="h-2.5 w-2.5 mr-1 inline" />
                            {statusCfg.label}
                          </Badge>
                        )}
                        {!server.enabled && <Badge tone="outline">Disabled</Badge>}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="font-mono truncate">
                          {server.transport === "http"
                            ? server.url
                            : [server.command, ...(server.args ?? [])].filter(Boolean).join(" ")}
                        </span>
                        {status && (
                          <>
                            {status.latency_ms != null && (
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {status.latency_ms}ms
                              </span>
                            )}
                            <span>{status.tools_count} tool(s)</span>
                          </>
                        )}
                      </div>
                      {status?.error_message && (
                        <p className="text-xs text-destructive mt-1">{status.error_message}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        ghost
                        size="icon"
                        onClick={() => handleToggleEnabled(server)}
                        disabled={toggling === server.name}
                        title={server.enabled ? "Disable" : "Enable"}
                      >
                        {toggling === server.name ? (
                          <Spinner />
                        ) : (
                          <Power className={cn("h-3.5 w-3.5", server.enabled && "text-success")} />
                        )}
                      </Button>
                      <Button
                        ghost
                        size="icon"
                        onClick={() => handleHealthCheck(server.name)}
                        disabled={healthRunning === server.name}
                        title="Health check"
                      >
                        {healthRunning === server.name ? <Spinner /> : <Activity className="h-3.5 w-3.5" />}
                      </Button>
                      <Button
                        ghost
                        size="icon"
                        onClick={() => handleRestart(server.name)}
                        title="Restart"
                      >
                        <RotateCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        ghost
                        size="icon"
                        onClick={() => handleViewLogs(server.name)}
                        title="View logs"
                      >
                        <FileText className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        ghost
                        destructive
                        size="icon"
                        onClick={() => handleDelete(server.name)}
                        title="Remove"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {/* Log viewer */}
                  {viewLogs === server.name && (
                    <div className="mt-4 pt-4 border-t border-border/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium font-mono">Logs: {server.name}</span>
                        <Button aria-label="Close logs" ghost size="icon" onClick={() => setViewLogs(null)}>
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      {logsLoading ? (
                        <div className="flex items-center justify-center py-8">
                          <Spinner />
                        </div>
                      ) : logs.length === 0 ? (
                        <p className="text-xs text-muted-foreground py-4 text-center">No log entries</p>
                      ) : (
                        <div className="max-h-64 overflow-y-auto font-mono text-[11px] bg-black/20 p-3 rounded border border-border/20">
                          {logs.map((log, i) => (
                            <div key={i} className={cn(
                              "py-0.5",
                              log.level === "error" && "text-red-400",
                              log.level === "warn" && "text-amber-400",
                              log.level === "info" && "text-muted-foreground",
                              log.level === "debug" && "text-muted-foreground/50",
                            )}>
                              <span className="text-muted-foreground/50">[{log.timestamp}]</span>{" "}
                              <span className="uppercase font-bold">[{log.level}]</span>{" "}
                              {log.message}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Server Modal */}
      {showAddModal && (
        <AddServerModal
          ref={addModalRef}
          onClose={() => setShowAddModal(false)}
          onCreated={() => { setShowAddModal(false); void loadAll(); }}
          showToast={showToast}
        />
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/85 backdrop-blur-sm p-4"
          onClick={(e) => e.target === e.currentTarget && setShowImportModal(false)}
        >
          <div className={cn(themedBody, "relative w-full max-w-lg border border-border bg-card shadow-2xl flex flex-col")}>
            <Button aria-label="Close" ghost size="icon" onClick={() => setShowImportModal(false)} className="absolute right-2 top-2 text-muted-foreground hover:text-foreground">
              <X />
            </Button>
            <header className="p-5 pb-3 border-b border-border">
              <h2 className="font-mondwest text-display text-base tracking-wider">Import MCP Config</h2>
            </header>
            <div className="p-5 grid gap-4">
              <textarea
                className="flex min-h-[200px] w-full border border-border bg-background/40 px-3 py-2 text-sm font-courier shadow-sm"
                placeholder={"Paste MCP YAML configuration here..."}
                value={yamlImport}
                onChange={(e) => setYamlImport(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <Button ghost size="sm" onClick={() => setShowImportModal(false)}>Cancel</Button>
                <Button className="uppercase" size="sm" onClick={handleImport}>Import</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Auto-Discovery Modal */}
      {showDiscovery && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-background/85 backdrop-blur-sm p-4"
          onClick={(e) => e.target === e.currentTarget && setShowDiscovery(false)}
        >
          <div className={cn(themedBody, "relative w-full max-w-xl border border-border bg-card shadow-2xl flex flex-col max-h-[80vh]")}>
            <Button aria-label="Close" ghost size="icon" onClick={() => setShowDiscovery(false)} className="absolute right-2 top-2 text-muted-foreground hover:text-foreground">
              <X />
            </Button>
            <header className="p-5 pb-3 border-b border-border">
              <h2 className="font-mondwest text-display text-base tracking-wider">Auto-Discover MCP Servers</h2>
            </header>
            <div className="p-5 overflow-y-auto">
              <Button className="mb-4 uppercase" size="sm" onClick={handleDiscovery}>
                <Search className="h-4 w-4 mr-1" />
                Scan for local MCP servers
              </Button>
              {discovered.length === 0 ? (
                <p className="text-xs text-muted-foreground">Click scan to discover MCP servers installed on your system.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {discovered.map((d, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 border border-border/20 rounded">
                      <Server className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{d.name}</p>
                        <p className="text-xs text-muted-foreground font-mono truncate">
                          {d.command} {d.args.join(" ")}
                        </p>
                        {d.description && (
                          <p className="text-xs text-muted-foreground/60">{d.description}</p>
                        )}
                      </div>
                      <Badge tone="outline">{d.source}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AddServerModal({
  ref,
  onClose,
  onCreated,
  showToast,
}: {
  ref: React.RefObject<HTMLDivElement | null>;
  onClose: () => void;
  onCreated: () => void;
  showToast: (msg: string, variant: "success" | "error") => void;
}) {
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<Transport>("http");
  const [url, setUrl] = useState("");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [env, setEnv] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) { showToast("Name required", "error"); return; }
    if (transport === "http" && !url.trim()) { showToast("URL required", "error"); return; }
    if (transport === "stdio" && !command.trim()) { showToast("Command required", "error"); return; }

    setCreating(true);
    try {
      const body: McpServerCreate = { name: name.trim() };
      if (transport === "http") {
        body.url = url.trim();
      } else {
        body.command = command.trim();
        const argList = args.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
        if (argList.length) body.args = argList;
      }
      const envMap: Record<string, string> = {};
      env.split("\n").map((l) => l.trim()).filter(Boolean).forEach((line) => {
        const idx = line.indexOf("=");
        if (idx >= 0) envMap[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
      });
      if (Object.keys(envMap).length) body.env = envMap;

      await api.addMcpServer(body);
      showToast("Server added", "success");
      onCreated();
    } catch (e) {
      showToast(`Failed: ${e}`, "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div
      ref={ref}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-background/85 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
    >
      <div className={cn(themedBody, "relative w-full max-w-lg border border-border bg-card shadow-2xl flex flex-col")}>
        <Button aria-label="Close" ghost size="icon" onClick={onClose} className="absolute right-2 top-2 text-muted-foreground hover:text-foreground">
          <X />
        </Button>
        <header className="p-5 pb-3 border-b border-border">
          <h2 className="font-mondwest text-display text-base tracking-wider">Add MCP Server</h2>
        </header>
        <div className="p-5 grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="mcp-name">Name</Label>
            <Input id="mcp-name" autoFocus placeholder="my-server" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="mcp-transport">Transport</Label>
            <Select value={transport} onValueChange={(v) => setTransport(v as Transport)}>
              <SelectOption value="http">HTTP/SSE</SelectOption>
              <SelectOption value="stdio">stdio</SelectOption>
            </Select>
          </div>
          {transport === "http" ? (
            <div className="grid gap-2">
              <Label htmlFor="mcp-url">URL</Label>
              <Input id="mcp-url" placeholder="https://example.com/mcp" value={url} onChange={(e) => setUrl(e.target.value)} />
            </div>
          ) : (
            <>
              <div className="grid gap-2">
                <Label htmlFor="mcp-command">Command</Label>
                <Input id="mcp-command" placeholder="npx" value={command} onChange={(e) => setCommand(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="mcp-args">Args</Label>
                <Input id="mcp-args" placeholder="-y @modelcontextprotocol/server-foo" value={args} onChange={(e) => setArgs(e.target.value)} />
              </div>
            </>
          )}
          <div className="grid gap-2">
            <Label htmlFor="mcp-env">Environment (KEY=VALUE per line)</Label>
            <textarea
              id="mcp-env"
              className="flex min-h-[80px] w-full border border-border bg-background/40 px-3 py-2 text-sm font-courier shadow-sm"
              placeholder="API_KEY=secret"
              value={env}
              onChange={(e) => setEnv(e.target.value)}
            />
          </div>
          <div className="flex justify-end">
            <Button className="uppercase" size="sm" onClick={handleCreate} disabled={creating} prefix={creating ? <Spinner /> : undefined}>
              {creating ? "Adding..." : "Add"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
