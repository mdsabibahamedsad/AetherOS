import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Smartphone,
  Monitor,
  Laptop,
  Tablet,
  Trash2,
  Edit3,
  Eye,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Fingerprint,
  Key,
  Calendar,
  Plus,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Copy,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { DeviceInfo } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const DEVICE_ICONS: Record<string, typeof Smartphone> = {
  desktop: Monitor,
  laptop: Laptop,
  tablet: Tablet,
  smartphone: Smartphone,
  cli: Monitor,
  server: Monitor,
};

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadDevices = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listDevices();
      setDevices(res.devices);
    } catch (e) {
      showToast(`Failed to load devices: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadDevices(); }, [loadDevices]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={() => void loadDevices()}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, loadDevices]);

  const filtered = useMemo(() => {
    if (!search) return devices;
    const q = search.toLowerCase();
    return devices.filter((d) => d.name.toLowerCase().includes(q) || d.os.toLowerCase().includes(q) || d.id.toLowerCase().includes(q));
  }, [devices, search]);

  const handleRevoke = async (device: DeviceInfo) => {
    try {
      await api.revokeDevice(device.id);
      setDevices((prev) => prev.filter((d) => d.id !== device.id));
      showToast(`${device.name} revoked`, "success");
    } catch (e) {
      showToast(`Revoke failed: ${e}`, "error");
    }
  };

  const handleRename = async (deviceId: string) => {
    if (!renameValue.trim()) { showToast("Name required", "error"); return; }
    try {
      await api.renameDevice(deviceId, renameValue.trim());
      setDevices((prev) => prev.map((d) => d.id === deviceId ? { ...d, name: renameValue.trim() } : d));
      setRenaming(null);
      setRenameValue("");
      showToast("Device renamed", "success");
    } catch (e) {
      showToast(`Rename failed: ${e}`, "error");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search devices..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {search ? "No devices match your search" : "No devices registered"}
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((device) => {
            const Icon = DEVICE_ICONS[device.device_type] ?? Smartphone;
            const isCurrent = device.current;

            return (
              <Card key={device.id} className={cn(isCurrent && "ring-1 ring-primary/30")}>
                <CardContent className="py-4 px-5">
                  <div className="flex items-start gap-4">
                    <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center text-sm shrink-0 border border-border/20",
                      isCurrent ? "bg-primary/20" : "bg-card",
                    )}>
                      <Icon className="h-4 w-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        {renaming === device.id ? (
                          <div className="flex items-center gap-2">
                            <Input
                              autoFocus
                              className="h-7 text-sm max-w-[200px]"
                              value={renameValue}
                              onChange={(e) => setRenameValue(e.target.value)}
                              onKeyDown={(e) => { if (e.key === "Enter") void handleRename(device.id); if (e.key === "Escape") { setRenaming(null); setRenameValue(""); } }}
                            />
                            <Button size="sm" ghost onClick={() => void handleRename(device.id)}>Save</Button>
                            <Button size="sm" ghost onClick={() => { setRenaming(null); setRenameValue(""); }}>Cancel</Button>
                          </div>
                        ) : (
                          <>
                            <span className="font-medium text-sm">{device.name}</span>
                            {isCurrent && <Badge tone="success">Current Device</Badge>}
                            <Badge tone={device.online ? "success" : "outline"}>
                              {device.online ? "Online" : "Offline"}
                            </Badge>
                            {device.sync_status !== "online" && (
                              <Badge tone={device.sync_status === "error" ? "destructive" : "warning"}>
                                {device.sync_status}
                              </Badge>
                            )}
                          </>
                        )}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{device.os}</span>
                        <span>v{device.version}</span>
                        {device.last_active && <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{isoTimeAgo(device.last_active)}</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <Button aria-label="Rename" ghost size="icon" onClick={() => { setRenaming(device.id); setRenameValue(device.name); }} title="Rename">
                        <Edit3 className="h-3.5 w-3.5" />
                      </Button>
                      <Button aria-label="Details" ghost size="icon" onClick={() => setExpanded(expanded === device.id ? null : device.id)} title="Details">
                        {expanded === device.id ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                      </Button>
                      <Button aria-label="Revoke" ghost destructive size="icon" onClick={() => handleRevoke(device)} title="Revoke">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>

                  {/* Expanded Detail */}
                  {expanded === device.id && (
                    <div className="mt-4 pt-4 border-t border-border/20">
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-muted-foreground">Device ID</span>
                          <p className="font-mono text-foreground/80 mt-0.5 break-all">{device.device_id}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Device Type</span>
                          <p className="capitalize mt-0.5">{device.device_type}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground flex items-center gap-1"><Key className="h-3 w-3" /> Public Key</span>
                          <p className="font-mono text-foreground/80 mt-0.5 break-all text-[10px]">
                            {device.public_key_fingerprint ?? "N/A"}
                          </p>
                        </div>
                        <div>
                          <span className="text-muted-foreground flex items-center gap-1"><Calendar className="h-3 w-3" /> Created</span>
                          <p className="mt-0.5">{new Date(device.created_at).toLocaleDateString()}</p>
                        </div>
                        <div className="col-span-2">
                          <span className="text-muted-foreground">Permissions</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {device.permissions.length === 0 ? (
                              <span className="text-muted-foreground/50">No permissions assigned</span>
                            ) : (
                              device.permissions.map((p) => (
                                <Badge key={p} tone="outline" className="text-[10px]">{p}</Badge>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Registration Info */}
      <Card>
        <CardHeader>
          <CardTitle>Register a New Device</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>Run the following command on the device you want to register:</p>
          <div className="flex items-center gap-2 p-3 bg-black/20 rounded border border-border/20 font-mono text-xs">
            <span>aetheros remote register --name my-device</span>
            <Button aria-label="Copy registration command" ghost size="icon" onClick={() => { void navigator.clipboard.writeText("aetheros remote register --name my-device"); showToast("Copied", "success"); }}>
              <Copy className="h-3 w-3" />
            </Button>
          </div>
          <p>Or use the <code className="text-foreground/80">aetheros remote</code> command to pair this dashboard with a remote AetherOS instance.</p>
        </CardContent>
      </Card>
    </div>
  );
}
