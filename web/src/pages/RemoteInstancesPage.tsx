import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Server,
  Plug,
  PlugZap,
  RefreshCw,
  Trash2,
  Edit3,
  Plus,
  Wifi,
  WifiOff,
  AlertTriangle,
  Clock,
  Activity,
  Gauge,
  ChevronDown,
  ChevronRight,
  X,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { useModalBehavior } from "@/hooks/useModalBehavior";
import { api } from "@/lib/api";
import type { RemoteInstance } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const STATUS_CONFIG: Record<string, { color: string; icon: typeof Activity; label: string }> = {
  online: { color: "text-emerald-400", icon: CheckCircle2, label: "Online" },
  offline: { color: "text-muted-foreground", icon: WifiOff, label: "Offline" },
  error: { color: "text-red-400", icon: AlertTriangle, label: "Error" },
  connecting: { color: "text-blue-400", icon: Activity, label: "Connecting..." },
};

export default function RemoteInstancesPage() {
  const [instances, setInstances] = useState<RemoteInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const addModalRef = useModalBehavior({ open: showAddModal, onClose: () => setShowAddModal(false) });

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listRemoteInstances();
      setInstances(res.instances);
    } catch (e) {
      showToast(`Failed to load instances: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadAll(); }, [loadAll]);

  useLayoutEffect(() => {
    setEnd(
      <Button size="sm" onClick={() => setShowAddModal(true)}>
        <Plus className="h-4 w-4 mr-1" />
        Add Instance
      </Button>,
    );
    return () => setEnd(null);
  }, [setEnd]);

  const handleConnect = async (instance: RemoteInstance) => {
    setConnecting(instance.id);
    try {
      if (instance.connected) {
        await api.disconnectRemoteInstance(instance.id);
      } else {
        await api.connectRemoteInstance(instance.id);
      }
      void loadAll();
      showToast(instance.connected ? "Disconnected" : "Connected", "success");
    } catch (e) {
      showToast(`Operation failed: ${e}`, "error");
    } finally {
      setConnecting(null);
    }
  };

  const handleReconnect = async (instanceId: string) => {
    try {
      await api.reconnectRemoteInstance(instanceId);
      void loadAll();
      showToast("Reconnecting...", "success");
    } catch (e) {
      showToast(`Reconnect failed: ${e}`, "error");
    }
  };

  const handleRemove = async (instance: RemoteInstance) => {
    try {
      await api.removeRemoteInstance(instance.id);
      setInstances((prev) => prev.filter((i) => i.id !== instance.id));
      showToast(`${instance.name} removed`, "success");
    } catch (e) {
      showToast(`Remove failed: ${e}`, "error");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : instances.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No remote instances configured
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {instances.map((instance) => {
            const cfg = STATUS_CONFIG[instance.status] ?? STATUS_CONFIG.offline;
            const StatusIcon = cfg.icon;

            return (
              <Card key={instance.id}>
                <CardContent className="py-4 px-5">
                  <div className="flex items-start gap-4">
                    <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center border border-border/20",
                      cfg.color.replace("text-", "bg-").replace("400", "400/20"),
                    )}>
                      <Server className={cn("h-4 w-4", cfg.color)} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-medium text-sm">{instance.name}</span>
                        <Badge tone={instance.status === "online" ? "success" : instance.status === "error" ? "destructive" : "warning"}>
                          <StatusIcon className="h-2.5 w-2.5 mr-1 inline" />
                          {cfg.label}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="font-mono truncate">{instance.url}</span>
                        {instance.version && <span>v{instance.version}</span>}
                        {instance.latency_ms != null && (
                          <span className="flex items-center gap-1">
                            <Gauge className="h-3 w-3" />
                            {instance.latency_ms}ms
                          </span>
                        )}
                        {instance.uptime_seconds != null && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {Math.floor(instance.uptime_seconds / 3600)}h
                          </span>
                        )}
                      </div>
                      {instance.error_message && (
                        <p className="text-xs text-destructive mt-1">{instance.error_message}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        ghost
                        size="icon"
                        onClick={() => handleConnect(instance)}
                        disabled={connecting === instance.id}
                        title={instance.connected ? "Disconnect" : "Connect"}
                      >
                        {connecting === instance.id ? <Spinner /> : instance.connected ? <PlugZap className="h-3.5 w-3.5 text-emerald-400" /> : <Plug className="h-3.5 w-3.5" />}
                      </Button>
                      <Button aria-label="Reconnect" ghost size="icon" onClick={() => handleReconnect(instance.id)} title="Reconnect">
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button aria-label="Details" ghost size="icon" onClick={() => setExpanded(expanded === instance.id ? null : instance.id)} title="Details">
                        {expanded === instance.id ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                      </Button>
                      <Button aria-label="Remove" ghost destructive size="icon" onClick={() => handleRemove(instance)} title="Remove">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {expanded === instance.id && instance.health && (
                    <div className="mt-4 pt-4 border-t border-border/20 text-xs">
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <span className="text-muted-foreground">Health</span>
                          <p className={cn("mt-0.5", instance.health.ok ? "text-emerald-400" : "text-red-400")}>
                            {instance.health.ok ? "Healthy" : "Unhealthy"}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Latency</span>
                          <p className="mt-0.5">{instance.health.latency_ms}ms</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Checked</span>
                          <p className="mt-0.5">{isoTimeAgo(instance.health.timestamp)}</p>
                        </div>
                      </div>
                      {instance.health.error && (
                        <p className="text-red-400 mt-2">{instance.health.error}</p>
                      )}
                    </div>
                  )}

                  {expanded === instance.id && !instance.health && (
                    <div className="mt-4 pt-4 border-t border-border/20 text-xs text-muted-foreground">
                      No health data available
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Instance Modal */}
      {showAddModal && (
        <AddInstanceModal
          ref={addModalRef}
          onClose={() => setShowAddModal(false)}
          onCreated={() => { setShowAddModal(false); void loadAll(); }}
          showToast={showToast}
        />
      )}
    </div>
  );
}

function AddInstanceModal({
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
  const [url, setUrl] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [testing, setTesting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; latency_ms: number; error?: string } | null>(null);

  const handleTest = async () => {
    if (!url.trim()) { showToast("URL required", "error"); return; }
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection(url.trim(), authToken.trim() || undefined);
      setTestResult(res);
      showToast(res.ok ? `Connection OK · ${res.latency_ms}ms` : `Connection failed: ${res.error}`, res.ok ? "success" : "error");
    } catch (e) {
      showToast(`Test failed: ${e}`, "error");
    } finally {
      setTesting(false);
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) { showToast("Name required", "error"); return; }
    if (!url.trim()) { showToast("URL required", "error"); return; }
    setCreating(true);
    try {
      await api.addRemoteInstance({
        name: name.trim(),
        url: url.trim(),
        auth_token: authToken.trim() || undefined,
      });
      showToast("Instance added", "success");
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
          <h2 className="font-mondwest text-display text-base tracking-wider">Add Remote Instance</h2>
        </header>
        <div className="p-5 grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="ri-name">Name</Label>
            <Input id="ri-name" autoFocus placeholder="My Server" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="ri-url">URL</Label>
            <Input id="ri-url" placeholder="https://aetheros.example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="ri-token">Auth Token (optional)</Label>
            <Input id="ri-token" placeholder="token-xxx" value={authToken} onChange={(e) => setAuthToken(e.target.value)} />
          </div>
          <Button ghost size="sm" onClick={handleTest} disabled={testing}>
            {testing ? <Spinner className="h-4 w-4 mr-1" /> : <Activity className="h-4 w-4 mr-1" />}
            Test Connection
          </Button>
          {testResult && (
            <div className={cn("text-xs px-3 py-2 rounded border", testResult.ok ? "bg-emerald-400/10 border-emerald-400/20 text-emerald-400" : "bg-red-400/10 border-red-400/20 text-red-400")}>
              {testResult.ok ? `Connected: ${testResult.latency_ms}ms` : `Error: ${testResult.error}`}
            </div>
          )}
          <div className="flex justify-end gap-2 mt-2">
            <Button ghost size="sm" onClick={onClose}>Cancel</Button>
            <Button className="uppercase" size="sm" onClick={handleCreate} disabled={creating}>
              {creating ? "Adding..." : "Add Instance"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
