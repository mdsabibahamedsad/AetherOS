import { useEffect, useState } from "react";
import {
  FileText,
  Search,
  X,
  Download,
  RefreshCw,
  AlertTriangle,
  Info,
  AlertCircle,
  ShieldAlert,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Button } from "@nous-research/ui/ui/components/button";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { ListItem } from "@nous-research/ui/ui/components/list-item";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface AuditEntry {
  event_type: string;
  timestamp: number;
  severity: string;
  user: string;
  source: string;
  details: Record<string, unknown>;
  message: string;
}

interface AuditStats {
  total_entries: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_user: Record<string, number>;
}

const SEVERITY_CONFIG: Record<string, { icon: React.ReactNode; color: string }> = {
  critical: { icon: <ShieldAlert className="h-3.5 w-3.5" />, color: "text-destructive" },
  error: { icon: <AlertCircle className="h-3.5 w-3.5" />, color: "text-destructive" },
  warning: { icon: <AlertTriangle className="h-3.5 w-3.5" />, color: "text-warning" },
  info: { icon: <Info className="h-3.5 w-3.5" />, color: "text-info" },
};

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(
      <div className="relative w-full min-w-0 sm:max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          className="h-8 pl-8 pr-7 text-xs"
          placeholder="Search audit log..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <Button ghost size="xs" className="absolute right-1.5 top-1/2 -translate-y-1/2" onClick={() => setSearchQuery("")}>
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
    return () => setEnd(null);
  }, [searchQuery, setEnd]);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.getAuditLog({ limit: 200 }).catch(() => ({ entries: [] })),
      api.getAuditStats().catch(() => null),
    ]).then(([e, s]) => {
      setEntries(e.entries ?? []);
      setStats(s);
      setLoading(false);
    });
  };

  useEffect(() => { fetchData(); }, []);

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleString();
  };

  const severityLabel = (sev: string) => {
    const labels: Record<string, string> = { critical: "Critical", error: "Error", warning: "Warning", info: "Info" };
    return labels[sev] ?? sev;
  };

  const filtered = entries.filter((e) => {
    if (searchQuery && !e.event_type.toLowerCase().includes(searchQuery.toLowerCase()) && !(e.message ?? "").toLowerCase().includes(searchQuery.toLowerCase()) && !e.user.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (severityFilter && e.severity !== severityFilter) return false;
    if (selectedType && e.event_type !== selectedType) return false;
    return true;
  });

  const severityCounts = entries.reduce((acc, e) => { acc[e.severity] = (acc[e.severity] ?? 0) + 1; return acc; }, {} as Record<string, number>);
  const typeCounts = entries.reduce((acc, e) => { acc[e.event_type] = (acc[e.event_type] ?? 0) + 1; return acc; }, {} as Record<string, number>);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-midground" />
          <h1 className="text-lg font-bold">Audit Log</h1>
          <Badge tone="secondary" className="text-xs">{stats?.total_entries ?? entries.length} entries</Badge>
        </div>
        <Button aria-label="Refresh" ghost size="icon" onClick={fetchData} title="Refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Filters sidebar */}
        <aside className="lg:w-48 shrink-0">
          <div className="border border-border bg-muted/20">
            <div className="px-3 py-2 border-b border-border flex items-center gap-2">
              <Filter className="h-3 w-3 text-text-tertiary" />
              <span className="font-mondwest text-display text-xs tracking-[0.12em] text-text-secondary">Filters</span>
            </div>
            {/* Severity */}
            <div className="px-3 pt-2 pb-1 font-mondwest text-display text-[10px] tracking-[0.12em] text-text-tertiary">Severity</div>
            <div className="p-2 space-y-px">
              {["critical", "error", "warning", "info"].map((sev) => (
                <ListItem
                  key={sev}
                  active={severityFilter === sev}
                  onClick={() => setSeverityFilter(severityFilter === sev ? null : sev)}
                  className="text-xs px-2 py-1"
                >
                  <span className={SEVERITY_CONFIG[sev]?.color ?? ""}>
                    {SEVERITY_CONFIG[sev]?.icon ?? <Info className="h-3.5 w-3.5" />}
                  </span>
                  <span className="flex-1 capitalize">{sev}</span>
                  <span className="text-text-tertiary text-[10px]">{severityCounts[sev] ?? 0}</span>
                </ListItem>
              ))}
            </div>
            {/* Event types */}
            <div className="px-3 pt-2 pb-1 font-mondwest text-display text-[10px] tracking-[0.12em] text-text-tertiary border-t border-border mt-1">Event Types</div>
            <div className="p-2 space-y-px max-h-[200px] overflow-y-auto">
              {Object.entries(typeCounts).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([type, count]) => (
                <ListItem
                  key={type}
                  active={selectedType === type}
                  onClick={() => setSelectedType(selectedType === type ? null : type)}
                  className="text-[10px] px-2 py-1"
                >
                  <span className="flex-1 truncate">{type.replace(/_/g, " ")}</span>
                  <span className="text-text-tertiary">{count}</span>
                </ListItem>
              ))}
            </div>
          </div>
        </aside>

        {/* Entries list */}
        <div className="flex-1 min-w-0 space-y-1">
          {filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground text-center py-12">No audit entries match the filter.</div>
          ) : (
            filtered.map((entry, i) => {
              const sev = SEVERITY_CONFIG[entry.severity] ?? { icon: <Info className="h-3.5 w-3.5" />, color: "text-muted-foreground" };
              return (
                <div key={`${entry.timestamp}-${i}`} className="flex items-start gap-3 py-2 px-3 border border-transparent hover:border-border hover:bg-muted/20 transition-colors text-sm">
                  <span className={`mt-0.5 shrink-0 ${sev.color}`}>{sev.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium capitalize">{entry.event_type.replace(/_/g, " ")}</span>
                      <Badge tone={entry.severity === "critical" || entry.severity === "error" ? "warning" : "secondary"} className="text-[9px]">
                        {severityLabel(entry.severity)}
                      </Badge>
                      {entry.user && <span className="text-[10px] text-muted-foreground font-mono">{entry.user}</span>}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">
                      {formatTime(entry.timestamp)}
                      {entry.message && <span className="ml-2">· {entry.message}</span>}
                    </div>
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <details className="mt-1">
                        <summary className="text-[10px] text-muted-foreground cursor-pointer hover:text-foreground">Details</summary>
                        <pre className="mt-1 text-[9px] text-muted-foreground font-mono bg-muted/30 p-2 overflow-x-auto">
                          {JSON.stringify(entry.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
