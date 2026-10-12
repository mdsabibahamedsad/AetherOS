import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FileText,
  GitBranch,
  History,
  RotateCcw,
  Check,
  X,
  Code2,
  ArrowLeftRight,
  Layers,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { SyncConflict } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

export default function ConflictResolutionPage() {
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [resolved, setResolved] = useState<SyncConflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showResolved, setShowResolved] = useState(false);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, rRes] = await Promise.all([
        api.getConflicts(),
        api.getResolvedConflicts(),
      ]);
      setConflicts(cRes.conflicts);
      setResolved(rRes.conflicts);
    } catch (e) {
      showToast(`Failed to load conflicts: ${e}`, "error");
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
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, loadAll]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === conflicts.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(conflicts.map((c) => c.id)));
    }
  };

  const handleResolve = async (conflict: SyncConflict, resolution: string) => {
    try {
      await api.resolveConflict(conflict.id, resolution);
      setConflicts((prev) => prev.filter((c) => c.id !== conflict.id));
      showToast(`Resolved: ${resolution}`, "success");
      void loadAll();
    } catch (e) {
      showToast(`Resolution failed: ${e}`, "error");
    }
  };

  const handleBatchResolve = async (resolution: string) => {
    if (selected.size === 0) { showToast("No conflicts selected", "error"); return; }
    try {
      const res = await api.batchResolveConflicts(Array.from(selected), resolution);
      showToast(`Resolved ${res.resolved} conflict(s)`, "success");
      setSelected(new Set());
      void loadAll();
    } catch (e) {
      showToast(`Batch resolve failed: ${e}`, "error");
    }
  };

  const unresolvedCount = conflicts.length;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : (
        <>
          {/* Header Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="py-4 px-5 flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-amber-400/10 flex items-center justify-center border border-border/20">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Unresolved</p>
                  <p className="text-sm font-medium">{unresolvedCount}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4 px-5 flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-emerald-400/10 flex items-center justify-center border border-border/20">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Resolved</p>
                  <p className="text-sm font-medium">{resolved.length}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4 px-5 flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-blue-400/10 flex items-center justify-center border border-border/20">
                  <History className="h-4 w-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">History</p>
                  <button className="text-sm font-medium text-blue-400 hover:underline" onClick={() => setShowResolved(!showResolved)}>
                    {showResolved ? "Hide History" : "View History"}
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Batch Actions */}
          {selected.size > 0 && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-primary/5 border border-primary/20">
              <span className="text-sm text-muted-foreground">{selected.size} selected</span>
              <Button ghost size="sm" onClick={() => handleBatchResolve("local")}>
                <Check className="h-3.5 w-3.5 mr-1" />
                Keep Local
              </Button>
              <Button ghost size="sm" onClick={() => handleBatchResolve("remote")}>
                <ArrowLeftRight className="h-3.5 w-3.5 mr-1" />
                Keep Remote
              </Button>
              <Button ghost size="sm" onClick={() => handleBatchResolve("latest")}>
                <Layers className="h-3.5 w-3.5 mr-1" />
                Latest Version
              </Button>
              <Button ghost size="sm" onClick={() => setSelected(new Set())}>
                <X className="h-3.5 w-3.5 mr-1" />
                Clear
              </Button>
            </div>
          )}

          {/* Conflict List */}
          <div className="flex flex-col gap-3">
            {(showResolved ? resolved : conflicts).length === 0 && (
              <Card>
                <CardContent className="py-12 text-center text-sm text-muted-foreground">
                  {showResolved ? "No resolved conflicts" : "No unresolved conflicts"}
                </CardContent>
              </Card>
            )}
            {(showResolved ? resolved : conflicts).map((conflict) => {
              const isActive = active === conflict.id;

              return (
                <Card key={conflict.id}>
                  <CardContent className="py-4 px-5">
                    <div className="flex items-start gap-4">
                      <div className="pt-1">
                        <input
                          type="checkbox"
                          checked={selected.has(conflict.id)}
                          onChange={() => toggleSelect(conflict.id)}
                          className="h-4 w-4 rounded border-border/40"
                        />
                      </div>
                      <div className="h-9 w-9 rounded-lg bg-amber-400/10 flex items-center justify-center border border-border/20 shrink-0">
                        <GitBranch className="h-4 w-4 text-amber-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="font-mono text-sm font-medium">{conflict.file_key}</span>
                          <Badge tone="warning">Conflict</Badge>
                          <span className="text-xs text-muted-foreground">{isoTimeAgo(conflict.timestamp)}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>
                            Local: <span className="font-mono">{conflict.local_version.device}</span>
                          </span>
                          <span>
                            Remote: <span className="font-mono">{conflict.remote_version.device}</span>
                          </span>
                        </div>
                        {conflict.resolved && (
                          <p className="text-xs text-emerald-400 mt-1">
                            Resolved: {conflict.resolution} · {conflict.resolved_at && isoTimeAgo(conflict.resolved_at)}
                          </p>
                        )}
                      </div>
                      <Button aria-label="Toggle diff" ghost size="icon" onClick={() => setActive(isActive ? null : conflict.id)} title="Toggle diff">
                        {isActive ? <X className="h-3.5 w-3.5" /> : <Code2 className="h-3.5 w-3.5" />}
                      </Button>
                    </div>

                    {/* Diff View */}
                    {isActive && (
                      <div className="mt-4 pt-4 border-t border-border/20">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <Badge tone="outline" className="text-[10px]">LOCAL</Badge>
                              <span className="text-xs text-muted-foreground font-mono">{conflict.local_version.device} · {conflict.local_version.modified_at}</span>
                            </div>
                            <div className="max-h-64 overflow-y-auto font-mono text-[11px] bg-black/20 p-3 rounded border border-border/20 whitespace-pre-wrap">
                              {conflict.local_content ?? "No content available"}
                            </div>
                          </div>
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <Badge tone="outline" className="text-[10px]">REMOTE</Badge>
                              <span className="text-xs text-muted-foreground font-mono">{conflict.remote_version.device} · {conflict.remote_version.modified_at}</span>
                            </div>
                            <div className="max-h-64 overflow-y-auto font-mono text-[11px] bg-black/20 p-3 rounded border border-border/20 whitespace-pre-wrap">
                              {conflict.remote_content ?? "No content available"}
                            </div>
                          </div>
                        </div>
                        {!conflict.resolved && (
                          <div className="flex items-center gap-2 mt-4">
                            <Button size="sm" ghost onClick={() => handleResolve(conflict, "local")}>
                              <Check className="h-3.5 w-3.5 mr-1" />
                              Keep Local
                            </Button>
                            <Button size="sm" ghost onClick={() => handleResolve(conflict, "remote")}>
                              <ArrowLeftRight className="h-3.5 w-3.5 mr-1" />
                              Keep Remote
                            </Button>
                            <Button size="sm" ghost onClick={() => handleResolve(conflict, "latest")}>
                              <Layers className="h-3.5 w-3.5 mr-1" />
                              Latest Version
                            </Button>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
