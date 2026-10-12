import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import {
  Cloud,
  CloudOff,
  RefreshCw,
  PauseCircle,
  Settings,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Wifi,
  WifiOff,
  Server,
  Home,
  Smartphone,
  Activity,
  ChevronRight,
  List,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { CloudSyncStatus, SyncScopeStatus, SyncEvent } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  online: { color: "text-emerald-400", label: "Online" },
  offline: { color: "text-muted-foreground", label: "Offline" },
  syncing: { color: "text-blue-400", label: "Syncing" },
  error: { color: "text-red-400", label: "Error" },
};

const CONNECTION_ICONS: Record<string, typeof Wifi> = {
  local: Home,
  cloud: Cloud,
  self_hosted: Server,
  custom: Settings,
};

export default function SyncDashboardPage() {
  const [status, setStatus] = useState<CloudSyncStatus | null>(null);
  const [events, setEvents] = useState<SyncEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, historyRes] = await Promise.all([
        api.getSyncStatus(),
        api.getSyncHistory({ limit: 20 }),
      ]);
      setStatus(statusRes);
      setEvents(historyRes.events);
    } catch (e) {
      showToast(`Failed to load sync status: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadAll(); }, [loadAll]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={() => void loadAll()}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
        <Button size="sm" onClick={() => { setSyncing(true); api.startSync().catch((e) => showToast(`Sync failed: ${e}`, "error")).finally(() => { setSyncing(false); void loadAll(); }); }} disabled={syncing}>
          {syncing ? <Spinner className="h-4 w-4 mr-1" /> : <Cloud className="h-4 w-4 mr-1" />}
          Sync Now
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, loadAll, showToast, syncing]);

  const handleToggleScope = async (scope: SyncScopeStatus) => {
    setToggling(scope.scope);
    try {
      await api.startSync(scope.scope);
      setStatus((prev) => prev ? {
        ...prev,
        scopes: prev.scopes.map((s) => s.scope === scope.scope ? { ...s, enabled: !s.enabled } : s),
      } : prev);
    } catch (e) {
      showToast(`Failed to toggle ${scope.scope}: ${e}`, "error");
    } finally {
      setToggling(null);
    }
  };

  const cfg = status ? STATUS_CONFIG[status.status] ?? STATUS_CONFIG.offline : STATUS_CONFIG.offline;
  const ConnectionIcon = status ? CONNECTION_ICONS[status.connection_type] ?? Wifi : Wifi;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : !status ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No sync status available
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Status Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center border border-border/20", cfg.color.replace("text-", "bg-").replace("400", "400/20"))}>
                    {status.status === "online" ? <CheckCircle2 className={cn("h-4 w-4", cfg.color)} /> :
                     status.status === "syncing" ? <Activity className={cn("h-4 w-4 animate-pulse", cfg.color)} /> :
                     status.status === "error" ? <AlertTriangle className={cn("h-4 w-4", cfg.color)} /> :
                     <CloudOff className={cn("h-4 w-4", cfg.color)} />}
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Sync Status</p>
                    <p className={cn("text-sm font-medium", cfg.color)}>{cfg.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center border border-border/20">
                    <Smartphone className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Connected Devices</p>
                    <p className="text-sm font-medium">{status.connected_devices}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-amber-400/10 flex items-center justify-center border border-border/20">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Conflicts</p>
                    <p className={cn("text-sm font-medium", status.conflict_count > 0 ? "text-amber-400" : "text-muted-foreground")}>
                      {status.conflict_count}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-blue-400/10 flex items-center justify-center border border-border/20">
                    <Clock className="h-4 w-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Offline Queue</p>
                    <p className={cn("text-sm font-medium", status.offline_queue_count > 0 ? "text-blue-400" : "text-muted-foreground")}>
                      {status.offline_queue_count}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sync Progress & Connection Type */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Sync Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 mb-2">
                  <span className="text-xs text-muted-foreground">Overall progress</span>
                  <span className="text-xs font-mono">{status.progress}%</span>
                </div>
                <div className="w-full h-2 bg-border/30 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all duration-500", status.status === "error" ? "bg-red-400" : "bg-primary")}
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
                {status.last_sync_at && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Last sync: {isoTimeAgo(status.last_sync_at)}
                  </p>
                )}
                {status.error_message && (
                  <p className="text-xs text-destructive mt-2">{status.error_message}</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Connection</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3 mb-3">
                  <ConnectionIcon className="h-5 w-5 text-primary" />
                  <span className="text-sm font-medium capitalize">{status.connection_type.replace("_", " ")}</span>
                </div>
                <div className="flex items-center gap-2">
                  {status.connected_devices > 0 ? (
                    <Wifi className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <WifiOff className="h-3.5 w-3.5 text-muted-foreground" />
                  )}
                  <span className="text-xs text-muted-foreground">
                    {status.connected_devices > 0 ? `${status.connected_devices} device(s) connected` : "No devices connected"}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sync Scopes */}
          <Card>
            <CardHeader>
              <CardTitle>Sync Scopes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-2">
                {status.scopes.map((scope) => {
                  const scopeCfg = STATUS_CONFIG[scope.status] ?? STATUS_CONFIG.offline;
                  return (
                    <div key={scope.scope} className="flex items-center gap-4 py-2 px-3 rounded-lg border border-border/20">
                      <Switch
                        checked={scope.enabled}
                        onCheckedChange={() => handleToggleScope(scope)}
                        disabled={toggling === scope.scope}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium capitalize">{scope.scope}</p>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span className={cn("capitalize", scopeCfg.color)}>{scopeCfg.label}</span>
                          {scope.pending_changes > 0 && <span>{scope.pending_changes} pending</span>}
                          {scope.last_sync_at && <span>{isoTimeAgo(scope.last_sync_at)}</span>}
                        </div>
                        {scope.error_message && (
                          <p className="text-xs text-destructive mt-0.5">{scope.error_message}</p>
                        )}
                      </div>
                      {toggling === scope.scope && <Spinner />}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Sync Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No recent activity</p>
              ) : (
                <div className="flex flex-col gap-1 max-h-80 overflow-y-auto">
                  {events.map((evt) => (
                    <div key={evt.id} className="flex items-center gap-3 py-2 px-3 rounded text-xs border-b border-border/10 last:border-0">
                      <div className={cn("h-6 w-6 rounded flex items-center justify-center",
                        evt.status === "success" ? "bg-emerald-400/10" :
                        evt.status === "conflict" ? "bg-amber-400/10" : "bg-red-400/10",
                      )}>
                        {evt.status === "success" ? <CheckCircle2 className="h-3 w-3 text-emerald-400" /> :
                         evt.status === "conflict" ? <AlertTriangle className="h-3 w-3 text-amber-400" /> :
                         <AlertTriangle className="h-3 w-3 text-red-400" />}
                      </div>
                      <span className="text-muted-foreground font-mono shrink-0">{isoTimeAgo(evt.timestamp)}</span>
                      <Badge tone={evt.status === "success" ? "success" : evt.status === "conflict" ? "warning" : "destructive"} className="shrink-0">
                        {evt.action}
                      </Badge>
                      <span className="text-muted-foreground truncate">{evt.file_key}</span>
                      <span className="text-muted-foreground/50 shrink-0">{evt.device}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => showToast("Sync paused", "success")}>
              <PauseCircle className="h-4 w-4 mr-1" />
              Pause Sync
            </Button>
            <Button ghost size="sm" onClick={() => showToast("Configure", "success")}>
              <Settings className="h-4 w-4 mr-1" />
              Configure
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
