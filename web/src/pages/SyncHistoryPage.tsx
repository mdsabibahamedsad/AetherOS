import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  History,
  Search,
  Filter,
  Download,
  Trash2,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { SyncEvent, SyncScope } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const PAGE_SIZE = 25;

const SCOPE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All Scopes" },
  ...["settings", "agents", "workflows", "knowledge", "memory", "tools", "automations", "files", "skills"].map((s) => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) })),
];

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "success", label: "Success" },
  { value: "failed", label: "Failed" },
  { value: "conflict", label: "Conflict" },
];

export default function SyncHistoryPage() {
  const [events, setEvents] = useState<SyncEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [scopeFilter, setScopeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getSyncHistory({
        limit: PAGE_SIZE,
        offset,
        scope: scopeFilter || undefined,
        status: statusFilter || undefined,
      });
      setEvents(res.events);
      setTotal(res.total);
    } catch (e) {
      showToast(`Failed to load history: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [offset, scopeFilter, statusFilter, showToast]);

  useEffect(() => { void loadHistory(); }, [loadHistory]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={handleExport}>
          <Download className="h-4 w-4 mr-1" />
          Export
        </Button>
        <Button ghost size="sm" destructive onClick={handleClear}>
          <Trash2 className="h-4 w-4 mr-1" />
          Clear
        </Button>
        <Button ghost size="sm" onClick={() => void loadHistory()}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, loadHistory]);

  const handleExport = async () => {
    try {
      const res = await api.exportSyncHistory();
      showToast("History exported", "success");
    } catch (e) {
      showToast(`Export failed: ${e}`, "error");
    }
  };

  const handleClear = async () => {
    try {
      await api.clearSyncHistory();
      setEvents([]);
      setTotal(0);
      showToast("History cleared", "success");
    } catch (e) {
      showToast(`Clear failed: ${e}`, "error");
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const filteredEvents = useMemo(() => {
    if (!search) return events;
    const q = search.toLowerCase();
    return events.filter((e) =>
      e.file_key.toLowerCase().includes(q) ||
      e.device.toLowerCase().includes(q) ||
      e.scope.toLowerCase().includes(q) ||
      e.action.toLowerCase().includes(q),
    );
  }, [events, search]);

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Total count */}
      <div className="text-xs text-muted-foreground">
        {total} event(s) · Page {currentPage} of {totalPages}
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search events..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={scopeFilter} onValueChange={(v) => { setScopeFilter(v); setOffset(0); }}>
          {SCOPE_OPTIONS.map((o) => (
            <SelectOption key={o.value} value={o.value}>{o.label}</SelectOption>
          ))}
        </Select>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setOffset(0); }}>
          {STATUS_OPTIONS.map((o) => (
            <SelectOption key={o.value} value={o.value}>{o.label}</SelectOption>
          ))}
        </Select>
        <Button ghost size="sm" onClick={() => { setScopeFilter(""); setStatusFilter(""); setSearch(""); setOffset(0); }}>
          <Filter className="h-4 w-4 mr-1" />
          Clear Filters
        </Button>
      </div>

      {/* Event List */}
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : filteredEvents.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No events found
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-4 px-5">
            <div className="flex flex-col">
              {/* Header */}
              <div className="grid grid-cols-6 gap-4 px-3 py-2 text-xs text-muted-foreground font-medium border-b border-border/20">
                <span className="col-span-1">Time</span>
                <span className="col-span-1">Scope</span>
                <span className="col-span-1">Action</span>
                <span className="col-span-1">File / Key</span>
                <span className="col-span-1">Device</span>
                <span className="col-span-1 text-right">Status</span>
              </div>
              <div className="max-h-[600px] overflow-y-auto">
                {filteredEvents.map((evt) => (
                  <div
                    key={evt.id}
                    className="grid grid-cols-6 gap-4 px-3 py-2.5 text-xs border-b border-border/10 last:border-0 hover:bg-black/10 items-center"
                  >
                    <span className="font-mono text-muted-foreground col-span-1">{isoTimeAgo(evt.timestamp)}</span>
                    <span className="capitalize col-span-1">{evt.scope}</span>
                    <span className="col-span-1">
                      <Badge tone="outline" className="text-[10px] uppercase">{evt.action}</Badge>
                    </span>
                    <span className="font-mono text-muted-foreground truncate col-span-1" title={evt.file_key}>
                      {evt.file_key}
                    </span>
                    <span className="text-muted-foreground col-span-1 truncate">{evt.device}</span>
                    <span className="col-span-1 text-right">
                      {evt.status === "success" ? (
                        <Badge tone="success"><CheckCircle2 className="h-2.5 w-2.5 mr-1 inline" />Success</Badge>
                      ) : evt.status === "conflict" ? (
                        <Badge tone="warning"><AlertTriangle className="h-2.5 w-2.5 mr-1 inline" />Conflict</Badge>
                      ) : (
                        <Badge tone="destructive"><XCircle className="h-2.5 w-2.5 mr-1 inline" />Failed</Badge>
                      )}
                    </span>
                    {evt.detail && (
                      <p className="col-span-6 text-muted-foreground/50 mt-1">{evt.detail}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            ghost
            size="sm"
            onClick={() => setOffset((p) => Math.max(0, p - PAGE_SIZE))}
            disabled={offset === 0}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            ghost
            size="sm"
            onClick={() => setOffset((p) => Math.min(total - PAGE_SIZE, p + PAGE_SIZE))}
            disabled={offset + PAGE_SIZE >= total}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
