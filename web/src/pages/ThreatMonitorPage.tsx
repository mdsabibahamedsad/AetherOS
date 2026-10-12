import { useEffect, useState } from "react";
import {
  Activity,
  ShieldAlert,
  AlertTriangle,
  Info,
  AlertCircle,
  RefreshCw,
  Shield,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Button } from "@aetheros/ui/ui/components/button";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface ThreatAlert {
  alert_id: string;
  category: string;
  level: string;
  title: string;
  description: string;
  timestamp: number;
  source: string;
  recommendations: string[];
}

interface ThreatSummary {
  total_alerts: number;
  by_level: Record<string, number>;
  by_category: Record<string, number>;
  recent_count: number;
}

const LEVEL_CONFIG: Record<string, { icon: React.ReactNode; color: string; bg: string }> = {
  critical: { icon: <ShieldAlert className="h-4 w-4" />, color: "text-destructive", bg: "bg-destructive/10 border-destructive/30" },
  high: { icon: <AlertCircle className="h-4 w-4" />, color: "text-destructive", bg: "bg-destructive/5 border-destructive/20" },
  medium: { icon: <AlertTriangle className="h-4 w-4" />, color: "text-warning", bg: "bg-warning/5 border-warning/20" },
  low: { icon: <Info className="h-4 w-4" />, color: "text-info", bg: "bg-info/5 border-info/20" },
  info: { icon: <Info className="h-4 w-4" />, color: "text-muted-foreground", bg: "bg-transparent border-border" },
};

export default function ThreatMonitorPage() {
  const [alerts, setAlerts] = useState<ThreatAlert[]>([]);
  const [summary, setSummary] = useState<ThreatSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(null);
    return () => setEnd(null);
  }, [setEnd]);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.getThreatAlerts({ limit: 50 }).catch(() => ({ alerts: [] })),
      api.getThreatSummary().catch(() => null),
    ]).then(([a, s]) => {
      setAlerts(a.alerts ?? []);
      setSummary(s);
      setLoading(false);
    });
  };

  useEffect(() => { fetchData(); }, []);

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    const delta = Math.floor((Date.now() - ts * 1000) / 1000);
    if (delta < 60) return "Just now";
    if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
    if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
    return d.toLocaleDateString();
  };

  const highThreatCount = (summary?.by_level?.critical ?? 0) + (summary?.by_level?.high ?? 0);

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
          <Activity className="h-5 w-5 text-midground" />
          <h1 className="text-lg font-bold">Threat Monitor</h1>
          {highThreatCount > 0 && (
            <Badge tone="warning" className="text-xs">{highThreatCount} active</Badge>
          )}
        </div>
        <Button aria-label="Refresh" ghost size="icon" onClick={fetchData} title="Refresh">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card>
            <CardContent className="px-4 py-3">
              <div className="text-2xl font-bold">{summary.total_alerts}</div>
              <div className="text-[10px] text-muted-foreground">Total Alerts</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="px-4 py-3">
              <div className={`text-2xl font-bold ${highThreatCount > 0 ? "text-destructive" : ""}`}>{highThreatCount}</div>
              <div className="text-[10px] text-muted-foreground">High / Critical</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="px-4 py-3">
              <div className="text-2xl font-bold">{summary.recent_count}</div>
              <div className="text-[10px] text-muted-foreground">Last Hour</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="px-4 py-3">
              <div className="text-2xl font-bold">{Object.keys(summary.by_category ?? {}).length}</div>
              <div className="text-[10px] text-muted-foreground">Categories</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* By level breakdown */}
      {summary && Object.keys(summary.by_level).length > 0 && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Threat Levels
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="space-y-2">
              {Object.entries(summary.by_level).map(([level, count]) => {
                const cfg = LEVEL_CONFIG[level] ?? LEVEL_CONFIG.info;
                const pct = summary.total_alerts > 0 ? Math.round((count / summary.total_alerts) * 100) : 0;
                return (
                  <div key={level} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className={`flex items-center gap-1.5 capitalize ${cfg.color}`}>
                        {cfg.icon}
                        {level}
                      </span>
                      <span>{count} ({pct}%)</span>
                    </div>
                    <div className="h-1.5 bg-muted/30 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-500 ${level === "critical" || level === "high" ? "bg-destructive" : level === "medium" ? "bg-warning" : "bg-midground/30"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alerts list */}
      <div className="space-y-2">
        {alerts.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-sm text-muted-foreground">
              <Shield className="h-8 w-8 mb-3 opacity-30" />
              <p>No threat alerts.</p>
              <p className="text-xs mt-1">All systems operating normally.</p>
            </CardContent>
          </Card>
        ) : (
          alerts.map((alert) => {
            const cfg = LEVEL_CONFIG[alert.level] ?? LEVEL_CONFIG.info;
            return (
              <div key={alert.alert_id} className={`border ${cfg.bg} px-4 py-3`}>
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 shrink-0 ${cfg.color}`}>{cfg.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{alert.title}</span>
                      <Badge tone={alert.level === "critical" || alert.level === "high" ? "warning" : "secondary"} className="text-[9px] capitalize">
                        {alert.level}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground">{formatTime(alert.timestamp)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{alert.description}</p>
                    <div className="text-[10px] text-muted-foreground mt-1 space-x-2">
                      {alert.source && <span>Source: {alert.source}</span>}
                      <span className="capitalize">· {alert.category.replace(/_/g, " ")}</span>
                    </div>
                    {alert.recommendations.length > 0 && (
                      <details className="mt-2">
                        <summary className="text-[10px] text-muted-foreground cursor-pointer hover:text-foreground">Recommendations</summary>
                        <ul className="mt-1 space-y-0.5">
                          {alert.recommendations.map((r, i) => (
                            <li key={i} className="text-[10px] text-muted-foreground">· {r}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
