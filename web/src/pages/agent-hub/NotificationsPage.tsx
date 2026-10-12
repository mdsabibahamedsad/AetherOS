import { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, BellOff, CheckCheck, Info, AlertTriangle, AlertCircle, CheckCircle2, X, Mail, MailOpen, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Label } from "@nous-research/ui/ui/components/label";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { AgentNotification } from "@/lib/api";

const TYPE_CONFIG: Record<string, { tone: "info" | "warning" | "destructive" | "success"; icon: typeof Info }> = {
  info: { tone: "info", icon: Info },
  warning: { tone: "warning", icon: AlertTriangle },
  error: { tone: "destructive", icon: AlertCircle },
  success: { tone: "success", icon: CheckCircle2 },
};

const NOTIFICATION_TYPES = ["info", "warning", "error", "success"] as const;

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return d.toLocaleDateString();
}

function groupByDate(notifications: AgentNotification[]): Map<string, AgentNotification[]> {
  const groups = new Map<string, AgentNotification[]>();
  for (const n of notifications) {
    const date = new Date(n.created_at).toLocaleDateString();
    const existing = groups.get(date) ?? [];
    existing.push(n);
    groups.set(date, existing);
  }
  return groups;
}

export default function NotificationsPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { notifications, fetchNotifications, markNotificationRead, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Notifications");
    setDescription("Agent notification center");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await fetchNotifications();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchNotifications]);

  useEffect(() => { load(); }, [load]);

  const handleMarkRead = async (id: string) => {
    setActionLoading(id);
    try {
      await markNotificationRead(id);
      toast({ title: "Marked as read", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setActionLoading(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllAgentNotificationsRead();
      await fetchNotifications();
      toast({ title: "All marked as read", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  const handleClearAll = async () => {
    try {
      await api.clearAgentNotifications();
      await fetchNotifications();
      toast({ title: "All notifications cleared", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  const filtered = useMemo(() => {
    if (typeFilter === "all") return notifications;
    return notifications.filter((n) => n.type === typeFilter);
  }, [notifications, typeFilter]);

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);
  const unreadCount = notifications.filter((n) => !n.read).length;

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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-midground" />
            <span className="text-sm font-medium">Notifications</span>
            {unreadCount > 0 && (
              <Badge tone="destructive" className="text-xs">{unreadCount} unread</Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs">Type</Label>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectOption value="all">All</SelectOption>
              {NOTIFICATION_TYPES.map((t) => (
                <SelectOption key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</SelectOption>
              ))}
            </Select>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <Button ghost size="sm" onClick={handleMarkAllRead} prefix={<CheckCheck className="h-4 w-4" />}>
              Mark all read
            </Button>
          )}
          {notifications.length > 0 && (
            <Button ghost size="sm" destructive onClick={handleClearAll} prefix={<Trash2 className="h-4 w-4" />}>
              Clear all
            </Button>
          )}
        </div>
      </div>

      {notifications.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <BellOff className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No notifications yet.</p>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {Array.from(grouped.entries()).map(([date, items]) => (
          <div key={date}>
            <div className="text-xs text-muted-foreground font-medium mb-2 uppercase tracking-wider">{date}</div>
            <div className="space-y-1">
              {items.map((notification) => {
                const config = TYPE_CONFIG[notification.type] ?? TYPE_CONFIG.info;
                const Icon = config.icon;
                const isActionLoading = actionLoading === notification.id;
                return (
                  <Card key={notification.id} className={cn("transition-colors", !notification.read && "border-l-2 border-l-midground")}>
                    <CardContent className="py-3 px-4">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">
                          <Icon className={cn("h-4 w-4", config.tone === "info" ? "text-info" : config.tone === "success" ? "text-success" : config.tone === "warning" ? "text-warning" : "text-destructive")} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{notification.title}</span>
                            <Badge tone={config.tone} className="text-[10px]">{notification.type}</Badge>
                            {!notification.read && (
                              <span className="h-2 w-2 rounded-full bg-midground" />
                            )}
                          </div>
                          {notification.message && (
                            <p className="text-xs text-muted-foreground mt-0.5">{notification.message}</p>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-muted-foreground">{formatTime(notification.created_at)}</span>
                            {notification.agent_id && (
                              <Badge tone="outline" className="text-[10px]">Agent</Badge>
                            )}
                          </div>
                        </div>
                        {!notification.read && (
                          <Button
                            ghost
                            size="icon"
                            className="shrink-0"
                            disabled={isActionLoading}
                            onClick={() => handleMarkRead(notification.id)}
                            title="Mark as read"
                          >
                            {isActionLoading ? <Spinner /> : <CheckCheck className="h-4 w-4 text-muted-foreground" />}
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
