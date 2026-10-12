import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Terminal,
  FileText,
  Activity,
  AlertTriangle,
  Bug,
  RotateCw,
  RefreshCw,
  Cpu,
  MemoryStick,
  HardDrive,
  Package,
  Search,
  Trash2,
  Eye,
  EyeOff,
  Play,
  StopCircle,
  Zap,
  Clock,
  BarChart3,
  AlertCircle,
  Info,
  Wrench,
  ExternalLink,
  Code,
  Server,
  Check,
  X,
  ChevronDown,
  ChevronRight,
  Filter,
  Download,
  Smartphone,
  Monitor,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Select, SelectOption } from "@aetheros/ui/ui/components/select";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@aetheros/ui/ui/components/tabs";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type {
  PluginLogEntry,
  PerformanceMetrics,
  DebugConsoleMessage,
  InspectorPluginData,
} from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";

type DevTab = "console" | "logs" | "performance" | "inspector" | "projects";

export default function DeveloperToolsPage() {
  const [activeTab, setActiveTab] = useState<DevTab>("console");
  const [consoleMessages, setConsoleMessages] = useState<DebugConsoleMessage[]>([]);
  const [consoleLoading, setConsoleLoading] = useState(false);
  const [consoleInput, setConsoleInput] = useState("");
  const [logs, setLogs] = useState<PluginLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [inspectorData, setInspectorData] = useState<InspectorPluginData | null>(null);
  const [inspectorPlugin, setInspectorPlugin] = useState("");
  const [inspectorLoading, setInspectorLoading] = useState(false);
  const [projects, setProjects] = useState<Array<{ name: string; path: string; type: string; version: string }>>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [logFilter, setLogFilter] = useState("all");
  const [logPlugin, setLogPlugin] = useState("all");
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadConsole = useCallback(async () => {
    setConsoleLoading(true);
    try {
      const res = await api.getDebugConsole(200);
      setConsoleMessages(res.messages);
    } catch (e) {
      showToast(`Failed to load console: ${e}`, "error");
    } finally {
      setConsoleLoading(false);
    }
  }, [showToast]);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const params: { level?: string; plugin?: string } = {};
      if (logFilter !== "all") params.level = logFilter;
      if (logPlugin !== "all") params.plugin = logPlugin;
      const res = await api.getPluginLogs(params);
      setLogs(res.logs);
    } catch (e) {
      showToast(`Failed to load logs: ${e}`, "error");
    } finally {
      setLogsLoading(false);
    }
  }, [showToast, logFilter, logPlugin]);

  const loadMetrics = useCallback(async () => {
    setMetricsLoading(true);
    try {
      const res = await api.getPerformanceMetrics();
      setMetrics(res);
    } catch (e) {
      showToast(`Failed to load metrics: ${e}`, "error");
    } finally {
      setMetricsLoading(false);
    }
  }, [showToast]);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    try {
      const res = await api.getExtensionProjects();
      setProjects(res.projects);
    } catch (e) {
      showToast(`Failed to load projects: ${e}`, "error");
    } finally {
      setProjectsLoading(false);
    }
  }, [showToast]);

  const handleInspect = async () => {
    if (!inspectorPlugin.trim()) {
      showToast("Plugin name required", "error");
      return;
    }
    setInspectorLoading(true);
    try {
      const res = await api.inspectPlugin(inspectorPlugin.trim());
      setInspectorData(res);
    } catch (e) {
      showToast(`Inspection failed: ${e}`, "error");
    } finally {
      setInspectorLoading(false);
    }
  };

  const handleSendCommand = async () => {
    if (!consoleInput.trim()) return;
    try {
      const res = await api.sendDebugCommand(consoleInput.trim());
      setConsoleMessages((prev) => [
        {
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          level: "log",
          source: "user",
          message: consoleInput.trim(),
        },
        {
          id: crypto.randomUUID(),
          timestamp: new Date().toISOString(),
          level: "info",
          source: "system",
          message: res.output,
          data: undefined,
        },
        ...prev,
      ]);
      setConsoleInput("");
    } catch (e) {
      showToast(`Command failed: ${e}`, "error");
    }
  };

  useEffect(() => {
    if (activeTab === "console") void loadConsole();
    else if (activeTab === "logs") void loadLogs();
    else if (activeTab === "performance") void loadMetrics();
    else if (activeTab === "projects") void loadProjects();
  }, [activeTab, loadConsole, loadLogs, loadMetrics, loadProjects]);

  useLayoutEffect(() => {
    setEnd(
      <Button
        ghost
        size="sm"
        onClick={() => {
          if (activeTab === "console") void loadConsole();
          else if (activeTab === "logs") void loadLogs();
          else if (activeTab === "performance") void loadMetrics();
          else if (activeTab === "projects") void loadProjects();
        }}
      >
        <RefreshCw className="h-4 w-4 mr-1" />
        Refresh
      </Button>,
    );
    return () => setEnd(null);
  }, [setEnd, activeTab, loadConsole, loadLogs, loadMetrics, loadProjects]);

  const TABS: { id: DevTab; label: string; icon: typeof Terminal }[] = [
    { id: "console", label: "Debug Console", icon: Terminal },
    { id: "logs", label: "Plugin Logs", icon: FileText },
    { id: "performance", label: "Performance", icon: Activity },
    { id: "inspector", label: "Inspector", icon: Bug },
    { id: "projects", label: "Extension Projects", icon: Package },
  ];

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Tabs */}
      <div className="flex border-b border-border/30 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "console" && (
        <DebugConsole
          messages={consoleMessages}
          loading={consoleLoading}
          input={consoleInput}
          onInputChange={setConsoleInput}
          onSend={handleSendCommand}
        />
      )}

      {activeTab === "logs" && (
        <PluginLogsView
          logs={logs}
          loading={logsLoading}
          logFilter={logFilter}
          logPlugin={logPlugin}
          onFilterChange={setLogFilter}
          onPluginChange={setLogPlugin}
        />
      )}

      {activeTab === "performance" && (
        <PerformanceView metrics={metrics} loading={metricsLoading} />
      )}

      {activeTab === "inspector" && (
        <InspectorView
          pluginName={inspectorPlugin}
          data={inspectorData}
          loading={inspectorLoading}
          onPluginChange={setInspectorPlugin}
          onInspect={handleInspect}
        />
      )}

      {activeTab === "projects" && (
        <ProjectsView projects={projects} loading={projectsLoading} />
      )}
    </div>
  );
}

function DebugConsole({
  messages,
  loading,
  input,
  onInputChange,
  onSend,
}: {
  messages: DebugConsoleMessage[];
  loading: boolean;
  input: string;
  onInputChange: (v: string) => void;
  onSend: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardContent className="p-0">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border/20 bg-muted/10">
            <Terminal className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium font-mono">Debug Console</span>
            <span className="text-xs text-muted-foreground ml-auto">
              {messages.length} messages
            </span>
          </div>
          <div className="max-h-80 overflow-y-auto font-mono text-[11px] p-2">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner />
              </div>
            ) : messages.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground">
                No console messages
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={cn(
                  "py-1 px-2 rounded hover:bg-muted/10",
                  msg.level === "error" && "text-red-400",
                  msg.level === "warn" && "text-amber-400",
                  msg.level === "info" && "text-cyan-400",
                  msg.level === "debug" && "text-muted-foreground/60",
                  msg.source === "user" && "text-emerald-400",
                )}>
                  <span className="text-muted-foreground/40">[{msg.timestamp.split("T")[1]?.split(".")[0]}]</span>{" "}
                  <span className="uppercase font-bold">[{msg.level}]</span>{" "}
                  <span className="text-muted-foreground/60">[{msg.source}]</span>{" "}
                  {msg.message}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-mono shrink-0">$</span>
        <Input
          className="font-mono text-xs"
          placeholder="Enter debug command..."
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
        />
        <Button aria-label="Execute" ghost size="icon" onClick={onSend}>
          <Play className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

function PluginLogsView({
  logs,
  loading,
  logFilter,
  logPlugin,
  onFilterChange,
  onPluginChange,
}: {
  logs: PluginLogEntry[];
  loading: boolean;
  logFilter: string;
  logPlugin: string;
  onFilterChange: (v: string) => void;
  onPluginChange: (v: string) => void;
}) {
  const uniquePlugins = useMemo(() => {
    const set = new Set(logs.map((l) => l.plugin));
    return Array.from(set);
  }, [logs]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <Select value={logFilter} onValueChange={onFilterChange} className="pl-7">
            <SelectOption value="all">All Levels</SelectOption>
            <SelectOption value="error">Error</SelectOption>
            <SelectOption value="warn">Warning</SelectOption>
            <SelectOption value="info">Info</SelectOption>
            <SelectOption value="debug">Debug</SelectOption>
          </Select>
        </div>
        <Select value={logPlugin} onValueChange={onPluginChange}>
          <SelectOption value="all">All Plugins</SelectOption>
          {uniquePlugins.map((p) => (
            <SelectOption key={p} value={p}>{p}</SelectOption>
          ))}
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-y-auto font-mono text-[11px]">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner />
              </div>
            ) : logs.length === 0 ? (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No log entries
              </div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className={cn(
                  "flex items-start gap-3 px-4 py-2 border-b border-border/10 last:border-0 hover:bg-muted/10",
                  log.level === "error" && "bg-red-400/5",
                  log.level === "warn" && "bg-amber-400/5",
                )}>
                  <Badge
                    className="text-[10px] shrink-0 mt-0.5"
                    tone={log.level === "error" ? "destructive" : log.level === "warn" ? "warning" : "outline"}
                  >
                    {log.level}
                  </Badge>
                  <span className="text-muted-foreground/50 shrink-0 mt-0.5">
                    {isoTimeAgo(log.timestamp)}
                  </span>
                  <span className="text-muted-foreground/70 shrink-0 mt-0.5 font-semibold">
                    [{log.plugin}]
                  </span>
                  <span className="text-muted-foreground mt-0.5 break-words flex-1">
                    {log.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PerformanceView({
  metrics,
  loading,
}: {
  metrics: PerformanceMetrics | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (!metrics) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          <Button className="uppercase" size="sm" onClick={() => {}}>
            Load Metrics
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* System metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Card>
          <CardContent className="flex items-center gap-3 py-4 px-4">
            <div className="h-9 w-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <Cpu className="h-4 w-4 text-blue-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">CPU Usage</p>
              <p className="text-lg font-semibold">{metrics.cpu_percent.toFixed(1)}%</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4 px-4">
            <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <MemoryStick className="h-4 w-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Memory</p>
              <p className="text-lg font-semibold">{metrics.memory_mb.toFixed(0)} MB</p>
              <p className="text-[11px] text-muted-foreground">{metrics.memory_percent.toFixed(1)}%</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4 px-4">
            <div className="h-9 w-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Uptime</p>
              <p className="text-lg font-semibold">
                {metrics.uptime_seconds >= 3600
                  ? `${(metrics.uptime_seconds / 3600).toFixed(1)}h`
                  : metrics.uptime_seconds >= 60
                    ? `${Math.floor(metrics.uptime_seconds / 60)}m`
                    : `${metrics.uptime_seconds}s`}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Per-plugin metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Plugin Resource Usage</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(metrics.plugin_cpu).length === 0 ? (
            <p className="text-xs text-muted-foreground py-4 text-center">No plugin resource data available</p>
          ) : (
            <div className="flex flex-col gap-2">
              {Object.keys(metrics.plugin_cpu).map((plugin) => (
                <div key={plugin} className="flex items-center gap-4 py-2 border-b border-border/10 last:border-0">
                  <Package className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="text-xs font-medium flex-1">{plugin}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-muted-foreground">
                      CPU: {metrics.plugin_cpu[plugin]?.toFixed(1) ?? "—"}%
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Mem: {metrics.plugin_memory[plugin]?.toFixed(1) ?? "—"} MB
                    </span>
                  </div>
                  <div className="w-24 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary/50 rounded-full"
                      style={{ width: `${Math.min(100, metrics.plugin_cpu[plugin] ?? 0)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function InspectorView({
  pluginName,
  data,
  loading,
  onPluginChange,
  onInspect,
}: {
  pluginName: string;
  data: InspectorPluginData | null;
  loading: boolean;
  onPluginChange: (v: string) => void;
  onInspect: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Plugin name..."
            value={pluginName}
            onChange={(e) => onPluginChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onInspect()}
          />
        </div>
        <Button className="uppercase" size="sm" onClick={onInspect} disabled={loading} prefix={loading ? <Spinner /> : <Bug />}>
          {loading ? "Inspecting..." : "Inspect"}
        </Button>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <InspectorSection title="General" data={{ name: data.name, version: data.version }} />
          <InspectorSection title="Hooks" data={data.hooks} />
          <InspectorSection title="Tools" data={data.tools} />
          <InspectorSection title="Permissions" data={data.permissions} />
          <InspectorSection title="Routes" data={data.routes} />
          <InspectorSection title="Slots" data={data.slots} />
          <div className="md:col-span-2">
            <InspectorSection title="State" data={data.state} />
          </div>
        </div>
      )}
    </div>
  );
}

function InspectorSection({ title, data }: { title: string; data: unknown }) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <Card>
      <CardContent className="p-0">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 w-full px-4 py-3 border-b border-border/10 text-left"
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          <span className="text-xs font-medium">{title}</span>
          <span className="text-xs text-muted-foreground ml-auto">
            {Array.isArray(data) ? data.length : typeof data === "object" && data ? Object.keys(data as Record<string, unknown>).length : 0}
          </span>
        </button>
        {!collapsed && (
          <div className="p-3 max-h-48 overflow-y-auto">
            {Array.isArray(data) ? (
              data.length === 0 ? (
                <p className="text-xs text-muted-foreground/60 italic">Empty</p>
              ) : (
                data.map((item, i) => (
                  <div key={i} className="text-xs font-mono text-muted-foreground py-0.5">{item}</div>
                ))
              )
            ) : typeof data === "object" && data ? (
              <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                {JSON.stringify(data, null, 2)}
              </pre>
            ) : (
              <p className="text-xs text-muted-foreground">{String(data)}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ProjectsView({
  projects,
  loading,
}: {
  projects: Array<{ name: string; path: string; type: string; version: string }>;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner />
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Package className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No extension projects found</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Create a new extension in the Extension SDK tab
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {projects.map((proj) => (
        <Card key={proj.name}>
          <CardContent className="flex items-center gap-4 py-3 px-4">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
              <Code className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{proj.name}</span>
                <Badge tone="outline" className="text-[10px]">{proj.type}</Badge>
                <Badge tone="secondary" className="text-[10px]">v{proj.version}</Badge>
              </div>
              <p className="text-xs text-muted-foreground font-mono truncate">{proj.path}</p>
            </div>
            <Button ghost size="sm">
              <ExternalLink className="h-3.5 w-3.5 mr-1" />
              Open
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
