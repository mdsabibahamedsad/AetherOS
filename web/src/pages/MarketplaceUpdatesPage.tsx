import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Download,
  RefreshCw,
  ArrowUp,
  Clock,
  Check,
  ChevronDown,
  ChevronUp,
  RotateCw,
  Package,
  Sparkles,
  AlertTriangle,
  FileText,
  ExternalLink,
  Settings,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { PluginMarketEntry } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";

interface PluginWithUpdate extends PluginMarketEntry {
  installed_version: string;
}

export default function MarketplaceUpdatesPage() {
  const [updates, setUpdates] = useState<PluginWithUpdate[]>([]);
  const [recentlyUpdated, setRecentlyUpdated] = useState<PluginMarketEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [updatingAll, setUpdatingAll] = useState(false);
  const [autoUpdate, setAutoUpdate] = useState(false);
  const [expandedChangelog, setExpandedChangelog] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [updatesRes, autoRes] = await Promise.all([
        api.getPluginUpdates(),
        api.searchPluginMarketplace({ sort: "latest", page_size: 5 }),
      ]);
      setUpdates(updatesRes.updates || []);
      setRecentlyUpdated((autoRes.entries || []).slice(0, 5));
    } catch (e) {
      showToast(`Failed to load updates: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadData(); }, [loadData]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button
          ghost
          size="icon"
          disabled={loading}
          onClick={() => void loadData()}
        >
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [loading, loadData, setEnd]);

  const handleUpdate = async (plugin: PluginWithUpdate) => {
    setUpdating(plugin.id);
    try {
      await api.updateMarketplacePlugin(plugin.id);
      showToast(`${plugin.name} updated to v${plugin.version}`, "success");
      setUpdates((prev) => prev.filter((p) => p.id !== plugin.id));
    } catch (e) {
      showToast(`Update failed: ${e}`, "error");
    } finally {
      setUpdating(null);
    }
  };

  const handleUpdateAll = async () => {
    setUpdatingAll(true);
    try {
      const res = await api.updateAllPlugins();
      showToast(
        `Updated ${res.updated} plugin(s)${res.failed.length > 0 ? `, ${res.failed.length} failed` : ""}`,
        res.failed.length > 0 ? "error" : "success",
      );
      await loadData();
    } catch (e) {
      showToast(`Update all failed: ${e}`, "error");
    } finally {
      setUpdatingAll(false);
    }
  };

  const handleAutoUpdate = async (enabled: boolean) => {
    try {
      const res = await api.setAutoUpdate(enabled);
      setAutoUpdate(res.auto_update);
      showToast(`Auto-update ${res.auto_update ? "enabled" : "disabled"}`, "success");
    } catch (e) {
      showToast(`Failed: ${e}`, "error");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Auto-update toggle */}
      <Card>
        <CardContent className="flex items-center justify-between py-4 px-4">
          <div className="flex items-center gap-3">
            <Settings className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Auto-update plugins</p>
              <p className="text-xs text-muted-foreground">
                Automatically install plugin updates when available
              </p>
            </div>
          </div>
          <Switch checked={autoUpdate} onCheckedChange={handleAutoUpdate} />
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : (
        <>
          {/* Available updates */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowUp className="h-4 w-4 text-amber-400" />
                <h3 className="font-mondwest text-display text-xs tracking-[0.12em] text-amber-400/80 uppercase">
                  Available Updates ({updates.length})
                </h3>
              </div>
              {updates.length > 0 && (
                <Button
                  className="uppercase"
                  size="sm"
                  disabled={updatingAll}
                  onClick={handleUpdateAll}
                  prefix={updatingAll ? <Spinner /> : <Download />}
                >
                  {updatingAll ? "Updating..." : "Update All"}
                </Button>
              )}
            </div>

            {updates.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Check className="h-8 w-8 mx-auto mb-3 text-emerald-400/60" />
                  <p className="text-sm text-muted-foreground">All plugins are up to date</p>
                </CardContent>
              </Card>
            ) : (
              <div className="flex flex-col gap-2">
                {updates.map((plugin) => {
                  const isUpdating = updating === plugin.id;
                  const expanded = expandedChangelog === plugin.id;
                  return (
                    <Card key={plugin.id} className={cn(isUpdating && "opacity-70")}>
                      <CardContent className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
                            {plugin.icon || <Package className="h-4 w-4" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{plugin.name}</span>
                              <Badge tone="warning" className="text-[10px]">
                                v{plugin.installed_version} → v{plugin.version}
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground truncate">{plugin.description}</p>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <Button
                              ghost
                              size="sm"
                              onClick={() => setExpandedChangelog(expanded ? null : plugin.id)}
                            >
                              <FileText className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              className="uppercase"
                              size="sm"
                              disabled={isUpdating}
                              onClick={() => handleUpdate(plugin)}
                              prefix={isUpdating ? <Spinner /> : <ArrowUp />}
                            >
                              {isUpdating ? "..." : "Update"}
                            </Button>
                          </div>
                        </div>
                        {expanded && (
                          <div className="mt-3 pt-3 border-t border-border/20">
                            <p className="text-xs font-medium mb-1">Changelog (v{plugin.version})</p>
                            <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                              {plugin.readme || "No changelog available."}
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          {/* Recently updated */}
          {recentlyUpdated.length > 0 && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <h3 className="font-mondwest text-display text-xs tracking-[0.12em] text-muted-foreground uppercase">
                  Recently Updated
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {recentlyUpdated.map((plugin) => (
                  <Card key={plugin.id}>
                    <CardContent className="flex items-center gap-3 py-3 px-4">
                      <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
                        {plugin.icon || <Package className="h-4 w-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">{plugin.name}</p>
                        <p className="text-[11px] text-muted-foreground">
                          v{plugin.version} · {isoTimeAgo(plugin.updated_at)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
