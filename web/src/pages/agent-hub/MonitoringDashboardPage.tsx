import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  Cpu,
  MemoryStick,
  CpuIcon,
  Bot,
  ListChecks,
  Wifi,
  WifiOff,
  Brain,
  Database,
  DollarSign,
  RefreshCw,
  Terminal,
  AlertCircle,
  Info,
  AlertTriangle,
  Bug,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Label } from "@nous-research/ui/ui/components/label";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { api } from "@/lib/api";
import type { MonitoringData, AgentLogEntry } from "@/lib/api";

const LOG_ICONS: Record<string, typeof Info> = {
  debug: Bug,
  info: Info,
  warn: AlertTriangle,
  error: AlertCircle,
};

const LOG_COLORS: Record<string, string> = {
  debug: "text-muted-foreground",
  info: "text-foreground",
  warn: "text-warning",
  error: "text-destructive",
};

function GaugeBar({ value, label, color }: { value: number; label: string; color: string }) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground w-12 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className="text-xs tabular-nums font-mono w-12 text-right">{clamped}%</span>
    </div>
  );
}

export default function MonitoringDashboardPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const [data, setData] = useState<MonitoringData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.getMonitoringData();
      setData(res);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load monitoring data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setTitle("Monitoring Dashboard");
    setDescription("Real-time system monitoring and metrics");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [data?.logs]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center py-24">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button size="sm" onClick={fetchData}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge tone={autoRefresh ? "success" : "outline"} className="text-xs">
            <RefreshCw className={cn("h-3 w-3 mr-1", autoRefresh && "animate-spin")} />
            Auto-refresh
          </Badge>
          <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
        </div>
        <Button size="xs" outlined onClick={fetchData} prefix={<RefreshCw className="h-3 w-3" />}>
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">CPU</span>
              <Cpu className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-2">
              <GaugeBar value={data.cpu_percent} label="Usage" color="bg-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">RAM</span>
              <MemoryStick className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-2">
              <GaugeBar value={data.memory_percent} label="Usage" color="bg-primary" />
            </div>
            <div className="mt-1 text-xs text-muted-foreground font-mono">
              {data.memory_used_mb.toFixed(0)} MB / {data.memory_total_mb.toFixed(0)} MB
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">GPU</span>
              <CpuIcon className="h-4 w-4 text-primary" />
            </div>
            {data.gpu_percent != null ? (
              <>
                <div className="mt-2">
                  <GaugeBar value={data.gpu_percent} label="Usage" color="bg-primary" />
                </div>
                {data.gpu_memory_mb != null && (
                  <div className="mt-1 text-xs text-muted-foreground font-mono">
                    {data.gpu_memory_mb.toFixed(0)} MB VRAM
                  </div>
                )}
              </>
            ) : (
              <div className="mt-2 text-xs text-muted-foreground">No GPU available</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">Memory</span>
              <Database className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-2">
              <GaugeBar value={data.memory_usage_percent} label="Usage" color="bg-warning" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3 flex items-center gap-3">
            <Bot className="h-5 w-5 text-primary" />
            <div>
              <div className="text-xs text-muted-foreground">Running Agents</div>
              <div className="text-lg font-bold">{data.running_agents} / {data.total_agents}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 flex items-center gap-3">
            <ListChecks className="h-5 w-5 text-primary" />
            <div>
              <div className="text-xs text-muted-foreground">Running Tasks</div>
              <div className="text-lg font-bold">{data.running_tasks} / {data.total_tasks}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 flex items-center gap-3">
            {data.providers_online === data.providers_total ? (
              <Wifi className="h-5 w-5 text-success" />
            ) : (
              <WifiOff className="h-5 w-5 text-destructive" />
            )}
            <div>
              <div className="text-xs text-muted-foreground">Provider Status</div>
              <div className="text-lg font-bold">{data.providers_online} / {data.providers_total} online</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3 flex items-center gap-3">
            <Brain className="h-5 w-5 text-primary" />
            <div>
              <div className="text-xs text-muted-foreground">Models Available</div>
              <div className="text-lg font-bold">{data.models_available}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs font-mono uppercase tracking-wider flex items-center gap-2">
              <DollarSign className="h-3.5 w-3.5" />
              Token Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="border border-border p-2">
                <div className="text-xs text-muted-foreground">Input</div>
                <div className="text-sm font-mono font-bold">{data.token_usage.input.toLocaleString()}</div>
              </div>
              <div className="border border-border p-2">
                <div className="text-xs text-muted-foreground">Output</div>
                <div className="text-sm font-mono font-bold">{data.token_usage.output.toLocaleString()}</div>
              </div>
              <div className="border border-border p-2">
                <div className="text-xs text-muted-foreground">Total</div>
                <div className="text-sm font-mono font-bold">{data.token_usage.total.toLocaleString()}</div>
              </div>
              <div className="border border-border p-2">
                <div className="text-xs text-muted-foreground">Cost</div>
                <div className="text-sm font-mono font-bold">${data.token_usage.cost.toFixed(4)}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs font-mono uppercase tracking-wider flex items-center gap-2">
              <Activity className="h-3.5 w-3.5" />
              Provider Status
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="flex items-center gap-2">
              <Badge tone={data.providers_online === data.providers_total ? "success" : "warning"} className="text-xs">
                {data.providers_online} online
              </Badge>
              <Badge tone="outline" className="text-xs">{data.providers_total - data.providers_online} offline</Badge>
            </div>
            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  data.providers_online === data.providers_total ? "bg-success" : "bg-warning",
                )}
                style={{ width: `${(data.providers_online / Math.max(data.providers_total, 1)) * 100}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-xs font-mono uppercase tracking-wider flex items-center gap-2">
            <Terminal className="h-3.5 w-3.5" />
            Live Logs
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="max-h-64 overflow-y-auto border border-border bg-background/50 font-mono text-xs">
            {(data.logs ?? []).length === 0 ? (
              <div className="p-3 text-muted-foreground">No log entries</div>
            ) : (
              data.logs.map((entry) => {
                const LogIcon = LOG_ICONS[entry.level] ?? Info;
                return (
                  <div key={entry.id} className={cn("flex items-start gap-2 px-3 py-1.5 border-b border-border/50 hover:bg-muted/20", LOG_COLORS[entry.level])}>
                    <LogIcon className="h-3 w-3 mt-0.5 shrink-0" />
                    <span className="shrink-0 text-muted-foreground">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="shrink-0 uppercase text-[0.6rem] tracking-wider text-muted-foreground">
                      [{entry.level}]
                    </span>
                    <span className="shrink-0 text-muted-foreground">{entry.component}:</span>
                    <span className="break-words">{entry.message}</span>
                  </div>
                );
              })
            )}
            <div ref={logsEndRef} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
