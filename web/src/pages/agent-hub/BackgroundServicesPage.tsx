import { useCallback, useEffect, useState } from "react";
import { Activity, Cpu, HardDrive, Play, Square, RefreshCw, RotateCcw, X, Server, AlertCircle, CheckCircle2, Pause } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Label } from "@aetheros/ui/ui/components/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@aetheros/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { BackgroundService, Agent } from "@/lib/api";

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

const STATUS_CONFIG: Record<string, { tone: "success" | "warning" | "destructive" | "secondary" | "info"; icon: typeof Activity }> = {
  running: { tone: "success", icon: Activity },
  stopped: { tone: "secondary", icon: Pause },
  error: { tone: "destructive", icon: AlertCircle },
  starting: { tone: "info", icon: RefreshCw },
};

const TYPE_TONES: Record<string, "info" | "warning" | "secondary" | "success" | "destructive"> = {
  watcher: "info",
  listener: "secondary",
  monitor: "warning",
  sync: "success",
  maintenance: "destructive",
};

export default function BackgroundServicesPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { backgrounds, agents, fetchBackgrounds, fetchAgents, startBackground, stopBackground, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedService, setSelectedService] = useState<BackgroundService | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [restartingId, setRestartingId] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Background Services");
    setDescription("Manage background agent services");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await Promise.all([fetchBackgrounds(), fetchAgents()]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchBackgrounds, fetchAgents]);

  useEffect(() => { load(); }, [load]);

  const handleStart = async (id: string) => {
    setActionLoading(id);
    try {
      await startBackground(id);
      toast({ title: "Service started", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (id: string) => {
    setActionLoading(id);
    try {
      await stopBackground(id);
      toast({ title: "Service stopped", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setActionLoading(null);
    }
  };

  const handleRestart = async (svc: BackgroundService) => {
    setRestartingId(svc.id);
    try {
      if (svc.status === "running") {
        await stopBackground(svc.id);
      }
      await startBackground(svc.id);
      toast({ title: "Service restarted", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setRestartingId(null);
    }
  };

  const handleAutoRestart = async (svc: BackgroundService, value: boolean) => {
    try {
      await api.updateBackgroundService(svc.id, { auto_restart: value });
      await fetchBackgrounds();
      toast({ title: value ? "Auto-restart enabled" : "Auto-restart disabled", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  const agentMap = new Map(agents.map((a: Agent) => [a.id, a]));
  const running = backgrounds.filter((s) => s.status === "running").length;
  const stopped = backgrounds.filter((s) => s.status === "stopped").length;
  const errored = backgrounds.filter((s) => s.status === "error").length;

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
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Running</span>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </div>
            <div className="mt-1 text-2xl font-bold">{running}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Stopped</span>
              <Pause className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stopped}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Error</span>
              <AlertCircle className="h-4 w-4 text-destructive" />
            </div>
            <div className="mt-1 text-2xl font-bold">{errored}</div>
          </CardContent>
        </Card>
      </div>

      {backgrounds.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No background services.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {backgrounds.map((svc) => {
          const StatusIcon = STATUS_CONFIG[svc.status]?.icon ?? Activity;
          const agent = svc.agent_id ? agentMap.get(svc.agent_id) : null;
          const isLoading = actionLoading === svc.id;
          const isRestarting = restartingId === svc.id;
          return (
            <Card key={svc.id} className="cursor-pointer transition-colors hover:border-midground/30" onClick={() => { setSelectedService(svc); setDetailOpen(true); }}>
              <CardContent className="py-4 px-5">
                <div className="flex items-start gap-4">
                  <StatusIcon className={cn("h-5 w-5 mt-0.5", STATUS_CONFIG[svc.status]?.tone === "success" ? "text-success" : STATUS_CONFIG[svc.status]?.tone === "destructive" ? "text-destructive" : "text-muted-foreground")} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm truncate">{svc.name}</span>
                      <Badge tone={TYPE_TONES[svc.type] ?? "secondary"} className="text-[10px]">{svc.type}</Badge>
                      <Badge tone={STATUS_CONFIG[svc.status]?.tone ?? "secondary"} className="text-[10px]">{svc.status}</Badge>
                    </div>
                    {svc.description && (
                      <p className="text-xs text-muted-foreground truncate mb-1">{svc.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      {agent && <span>Agent: {agent.name}</span>}
                      <span>Uptime: {formatUptime(svc.uptime)}</span>
                      <span className="flex items-center gap-1"><Cpu className="h-3 w-3" />{svc.cpu_percent.toFixed(1)}%</span>
                      <span className="flex items-center gap-1"><HardDrive className="h-3 w-3" />{svc.memory_mb.toFixed(0)} MB</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-2 mr-2">
                      <Label htmlFor={`ar-${svc.id}`} className="text-[10px] cursor-pointer">Auto</Label>
                      <Switch id={`ar-${svc.id}`} checked={svc.auto_restart} onCheckedChange={(v) => handleAutoRestart(svc, v)} />
                    </div>
                    {svc.status === "running" ? (
                      <Button aria-label="Stop" ghost size="icon" disabled={isLoading} onClick={() => handleStop(svc.id)} title="Stop">
                        {isLoading ? <Spinner /> : <Square className="h-4 w-4" />}
                      </Button>
                    ) : (
                      <Button aria-label="Start" ghost size="icon" disabled={isLoading} onClick={() => handleStart(svc.id)} title="Start">
                        {isLoading ? <Spinner /> : <Play className="h-4 w-4" />}
                      </Button>
                    )}
                    <Button aria-label="Restart" ghost size="icon" disabled={isRestarting} onClick={() => handleRestart(svc)} title="Restart">
                      {isRestarting ? <Spinner /> : <RotateCcw className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedService?.name}</DialogTitle>
            <DialogDescription>Service details and status.</DialogDescription>
          </DialogHeader>
          {selectedService && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-border rounded p-3">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">PID</div>
                  <div className="text-sm font-mono mt-1">{selectedService.pid ?? "—"}</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Memory</div>
                  <div className="text-sm font-mono mt-1">{selectedService.memory_mb.toFixed(0)} MB</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">CPU</div>
                  <div className="text-sm font-mono mt-1">{selectedService.cpu_percent.toFixed(1)}%</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Uptime</div>
                  <div className="text-sm font-mono mt-1">{formatUptime(selectedService.uptime)}</div>
                </div>
              </div>
              <div className="border border-border rounded p-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">Last Heartbeat</div>
                <div className="text-sm mt-1">{selectedService.last_heartbeat ? new Date(selectedService.last_heartbeat).toLocaleString() : "—"}</div>
              </div>
              {selectedService.error && (
                <div className="border border-destructive/30 bg-destructive/5 rounded p-3">
                  <div className="text-[10px] text-destructive uppercase tracking-wider">Error</div>
                  <div className="text-sm text-destructive mt-1 font-mono">{selectedService.error}</div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
