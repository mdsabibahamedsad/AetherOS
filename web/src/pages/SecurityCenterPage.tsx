import { useEffect, useState } from "react";
import {
  Shield,
  KeyRound,
  FileSearch,
  Terminal,
  Lock,
  Activity,
  Users,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface SecurityStatus {
  zero_trust: boolean;
  initialized: boolean;
  version: string;
  permission_count?: number;
  active_sandboxes?: number;
  audit_entry_count?: number;
  threat_alerts?: number;
  secrets_count?: number;
}

interface AuditStats {
  total_entries: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
}

interface ThreatSummary {
  total_alerts: number;
  by_level: Record<string, number>;
  by_category: Record<string, number>;
  recent_count: number;
}

interface PermissionStats {
  total_permissions: number;
  total_grants: number;
  rules: number;
  pending_requests: number;
}

export default function SecurityCenterPage() {
  const [status, setStatus] = useState<SecurityStatus | null>(null);
  const [auditStats, setAuditStats] = useState<AuditStats | null>(null);
  const [threats, setThreats] = useState<ThreatSummary | null>(null);
  const [permStats, setPermStats] = useState<PermissionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(null);
    return () => setEnd(null);
  }, [setEnd]);

  useEffect(() => {
    Promise.all([
      api.getSecurityStatus().catch(() => null),
      api.getAuditStats().catch(() => null),
      api.getThreatSummary().catch(() => null),
      api.getPermissionStats().catch(() => null),
    ]).then(([s, a, th, p]) => {
      setStatus(s);
      setAuditStats(a);
      setThreats(th);
      setPermStats(p);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  const severityColor = (sev: string) => {
    switch (sev) {
      case "critical": return "text-destructive";
      case "error":
      case "high": return "text-destructive";
      case "warning":
      case "medium": return "text-warning";
      case "info":
      case "low": return "text-info";
      default: return "text-muted-foreground";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Shield className="h-5 w-5 text-midground" />
        <div>
          <h1 className="text-lg font-bold">Security Center</h1>
          <p className="text-xs text-muted-foreground">
            {status?.zero_trust ? "Zero Trust enabled" : "Standard security"} &middot; v{status?.version ?? "?"}
          </p>
        </div>
        <div className="ml-auto">
          <Badge tone={status?.initialized ? "success" : "warning"}>
            {status?.initialized ? "Active" : "Not Initialized"}
          </Badge>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs flex items-center gap-2 text-muted-foreground">
              <Lock className="h-3.5 w-3.5" />
              Permissions
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="text-2xl font-bold">{permStats?.total_grants ?? 0}</div>
            <div className="text-xs text-muted-foreground">
              {permStats?.total_permissions ?? 0} categories &middot; {permStats?.pending_requests ?? 0} pending
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs flex items-center gap-2 text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              Audit Log
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="text-2xl font-bold">{auditStats?.total_entries ?? 0}</div>
            <div className="text-xs text-muted-foreground">
              {auditStats?.by_severity?.error ?? 0} errors &middot; {auditStats?.by_severity?.warning ?? 0} warnings
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs flex items-center gap-2 text-muted-foreground">
              <AlertTriangle className="h-3.5 w-3.5" />
              Threat Alerts
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className={`text-2xl font-bold ${(threats?.total_alerts ?? 0) > 0 ? "text-destructive" : ""}`}>
              {threats?.total_alerts ?? 0}
            </div>
            <div className="text-xs text-muted-foreground">
              {threats?.recent_count ?? 0} in last hour
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs flex items-center gap-2 text-muted-foreground">
              <KeyRound className="h-3.5 w-3.5" />
              Secrets
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="text-2xl font-bold">{status?.secrets_count ?? 0}</div>
            <div className="text-xs text-muted-foreground">Securely stored</div>
          </CardContent>
        </Card>
      </div>

      {/* Threat alerts section */}
      {threats && threats.total_alerts > 0 && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-destructive" />
              Active Threats
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            <div className="space-y-2">
              {Object.entries(threats.by_level ?? {}).map(([level, count]) => (
                <div key={level} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    {level === "critical" || level === "high" ? (
                      <XCircle className={`h-3.5 w-3.5 ${severityColor(level)}`} />
                    ) : (
                      <AlertTriangle className={`h-3.5 w-3.5 ${severityColor(level)}`} />
                    )}
                    <span className="capitalize">{level}</span>
                  </span>
                  <Badge tone={level === "critical" || level === "high" ? "warning" : "secondary"}>
                    {count}
                  </Badge>
                </div>
              ))}
              {threats.by_category && Object.keys(threats.by_category).length > 0 && (
                <>
                  <div className="border-t border-border my-2" />
                  {Object.entries(threats.by_category).map(([cat, count]) => (
                    <div key={cat} className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="capitalize">{cat.replace(/_/g, " ")}</span>
                      <span>{count}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick actions grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <QuickActionCard
          icon={<KeyRound className="h-4 w-4" />}
          title="Permissions"
          description="Manage granular permissions for plugins, agents, and tasks"
          href="/permissions"
        />
        <QuickActionCard
          icon={<Lock className="h-4 w-4" />}
          title="Secrets"
          description="Securely store and manage API keys, tokens, and passwords"
          href="/secrets"
        />
        <QuickActionCard
          icon={<FileText className="h-4 w-4" />}
          title="Audit Log"
          description="View tamper-evident audit log of all security events"
          href="/audit-log"
        />
        <QuickActionCard
          icon={<Activity className="h-4 w-4" />}
          title="Threat Monitor"
          description="Monitor for suspicious activity and security threats"
          href="/threat-monitor"
        />
        <QuickActionCard
          icon={<Terminal className="h-4 w-4" />}
          title="Sandbox Manager"
          description="Manage isolated execution sandboxes"
          href="/sandbox-manager"
        />
        <QuickActionCard
          icon={<FileSearch className="h-4 w-4" />}
          title="Security Scan"
          description="Run scans for vulnerabilities and sensitive data"
          href="/scan"
        />
      </div>
    </div>
  );
}

function QuickActionCard({
  icon,
  title,
  description,
  href,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="group block border border-border bg-muted/20 hover:bg-muted/40 transition-colors p-4"
      onClick={(e) => {
        e.preventDefault();
        window.location.hash = href;
      }}
    >
      <div className="flex items-center gap-3">
        <div className="shrink-0 text-midground/60 group-hover:text-midground transition-colors">
          {icon}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{title}</div>
          <div className="text-xs text-muted-foreground line-clamp-2">{description}</div>
        </div>
      </div>
    </a>
  );
}
