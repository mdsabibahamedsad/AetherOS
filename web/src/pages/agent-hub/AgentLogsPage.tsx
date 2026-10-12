import { useCallback, useEffect, useRef, useState } from "react";
import { Search, X, RefreshCw, Trash2, Filter, Clock, Bug, AlertTriangle, Info, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Select, SelectOption } from "@aetheros/ui/ui/components/select";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { AgentLogEntry, Agent } from "@/lib/api";

const LEVEL_ORDER = ["debug", "info", "warn", "error"] as const;
type LogLevel = typeof LEVEL_ORDER[number];

const LEVEL_CONFIG: Record<LogLevel, { tone: "secondary" | "info" | "warning" | "destructive"; icon: typeof Bug; color: string }> = {
  debug: { tone: "secondary", icon: Bug, color: "text-text-tertiary" },
  info: { tone: "info", icon: Info, color: "text-foreground" },
  warn: { tone: "warning", icon: AlertTriangle, color: "text-warning" },
  error: { tone: "destructive", icon: AlertCircle, color: "text-destructive" },
};

const LEVELS: LogLevel[] = ["debug", "info", "warn", "error"];

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

export default function AgentLogsPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { logs, agents, fetchLogs, fetchAgents, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState<LogLevel | "all">("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [componentFilter, setComponentFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTitle("Agent Logs");
    setDescription("Centralized log viewer for all agents");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchLogs(agentFilter === "all" ? undefined : agentFilter),
        fetchAgents(),
      ]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchLogs, fetchAgents, agentFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchLogs(agentFilter === "all" ? undefined : agentFilter);
    }, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchLogs, agentFilter]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const components = Array.from(new Set(logs.map((l) => l.component).filter(Boolean))).sort();

  const filteredLogs = logs.filter((entry) => {
    if (levelFilter !== "all" && entry.level !== levelFilter) return false;
    if (componentFilter && entry.component !== componentFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (!entry.message.toLowerCase().includes(q) && !entry.component?.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  const handleClear = async () => {
    try {
      const apiModule = await import("@/lib/api");
      await apiModule.api.clearAgentLogs();
      await fetchLogs();
      toast({ title: "Logs cleared", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  if (localLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card>
          <CardContent className="py-8 px-6 text-center">
            <p className="text-destructive text-sm">{error}</p>
            <Button className="mt-4" size="sm" onClick={load}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 pr-8 text-xs"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <Button ghost size="xs" className="absolute right-1 top-1/2 -translate-y-1/2" onClick={() => setSearchQuery("")}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Label className="text-xs">Level</Label>
          <Select value={levelFilter} onValueChange={(v) => setLevelFilter(v as LogLevel | "all")}>
            <SelectOption value="all">All</SelectOption>
            {LEVELS.map((l) => (
              <SelectOption key={l} value={l}>{l.toUpperCase()}</SelectOption>
            ))}
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Label className="text-xs">Agent</Label>
          <Select value={agentFilter} onValueChange={setAgentFilter}>
            <SelectOption value="all">All</SelectOption>
            {agents.map((a: Agent) => (
              <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
            ))}
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Label className="text-xs">Component</Label>
          <Select value={componentFilter} onValueChange={setComponentFilter}>
            <SelectOption value="">All</SelectOption>
            {components.map((c) => (
              <SelectOption key={c} value={c}>{c}</SelectOption>
            ))}
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Switch id="log-auto-refresh" checked={autoRefresh} onCheckedChange={setAutoRefresh} />
          <Label htmlFor="log-auto-refresh" className="text-xs cursor-pointer">Auto-refresh</Label>
          {autoRefresh && (
            <Select value={String(refreshInterval)} onValueChange={(v) => setRefreshInterval(Number(v))}>
              <SelectOption value="5">5s</SelectOption>
              <SelectOption value="10">10s</SelectOption>
              <SelectOption value="30">30s</SelectOption>
              <SelectOption value="60">60s</SelectOption>
            </Select>
          )}
        </div>

        <Button aria-label="Refresh" ghost size="icon" onClick={load} title="Refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button aria-label="Clear logs" ghost size="icon" onClick={handleClear} title="Clear logs">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Log Entries
            </CardTitle>
            <Badge tone="secondary" className="text-xs">{filteredLogs.length} entries</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div ref={scrollRef} className="max-h-[calc(100vh-280px)] overflow-auto">
            {filteredLogs.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-12">No log entries match the current filters.</p>
            )}
            {filteredLogs.map((entry) => {
              const config = LEVEL_CONFIG[entry.level as LogLevel] ?? LEVEL_CONFIG.info;
              const Icon = config.icon;
              return (
                <div key={entry.id} className="flex items-start gap-3 px-4 py-2 border-b border-border/50 hover:bg-muted/20 text-xs">
                  <Icon className={cn("h-3.5 w-3.5 mt-0.5 shrink-0", config.color)} />
                  <span className="text-muted-foreground shrink-0 w-36 font-mono-ui">{formatTimestamp(entry.timestamp)}</span>
                  <Badge tone={config.tone} className="text-[10px] shrink-0 w-12 justify-center">{entry.level.toUpperCase()}</Badge>
                  {entry.component && (
                    <span className="text-muted-foreground font-mono-ui shrink-0 max-w-[120px] truncate">{entry.component}</span>
                  )}
                  <span className={cn("flex-1 break-words min-w-0", config.color)}>{entry.message}</span>
                  {entry.agent_id && (
                    <Badge tone="outline" className="text-[10px] shrink-0">{agents.find((a: Agent) => a.id === entry.agent_id)?.name ?? entry.agent_id}</Badge>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
