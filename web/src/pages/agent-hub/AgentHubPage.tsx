import { useCallback, useEffect, useState } from "react";
import {
  Bot,
  Play,
  Pause,
  AlertTriangle,
  Activity,
  Plus,
  Download,
  LayoutTemplate,
  Clock,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import type { AgentLogEntry } from "@/lib/api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function getTimeAgo(iso?: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  running: "success",
  idle: "secondary",
  paused: "warning",
  error: "destructive",
  restarting: "warning",
  stopped: "outline",
};

export default function AgentHubPage() {
  const navigate = useNavigate();
  const { agents, loading, error, fetchAgents } = useAgentStore();
  const { toast, showToast } = useToast();
  const { setTitle } = usePageHeader();
  const [recentLogs, setRecentLogs] = useState<AgentLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);

  useEffect(() => {
    setTitle("Agent Hub");
  }, [setTitle]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    let cancelled = false;
    setLogsLoading(true);
    api.getAgentLogs()
      .then((res) => { if (!cancelled) setRecentLogs(res.logs ?? []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLogsLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const handleImport = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,.yaml,.yml";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("file", file);
      try {
        await useAgentStore.getState().importAgent(formData);
        showToast("Agent imported successfully", "success");
      } catch {
        showToast("Failed to import agent", "error");
      }
    };
    input.click();
  }, [showToast]);

  const stats = {
    total: agents.length,
    running: agents.filter((a) => a.status === "running").length,
    paused: agents.filter((a) => a.status === "paused").length,
    error: agents.filter((a) => a.status === "error").length,
    idle: agents.filter((a) => a.status === "idle").length,
  };

  if (loading && agents.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error && agents.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => fetchAgents()} prefix={<RefreshCw />}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Total Agents</span>
              <Bot className="h-4 w-4 text-muted-foreground" />
            </div>
            <span className="text-2xl font-bold">{stats.total}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Running</span>
              <Activity className="h-4 w-4 text-success" />
            </div>
            <span className="text-2xl font-bold text-success">{stats.running}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Idle</span>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </div>
            <span className="text-2xl font-bold">{stats.idle}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Paused</span>
              <Pause className="h-4 w-4 text-warning" />
            </div>
            <span className="text-2xl font-bold text-warning">{stats.paused}</span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Errors</span>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </div>
            <span className="text-2xl font-bold text-destructive">{stats.error}</span>
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => navigate("/agents/new")} prefix={<Plus />}>
          Create Agent
        </Button>
        <Button onClick={handleImport} outlined prefix={<Download />}>
          Import Agent
        </Button>
        <Button onClick={() => navigate("/agents/templates")} outlined prefix={<LayoutTemplate />}>
          Browse Templates
        </Button>
        <Button onClick={() => navigate("/agents")} outlined>
          View All Agents
        </Button>
      </div>

      {/* Agent status breakdown */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">Agent Status Overview</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {agents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No agents created yet. Click "Create Agent" to get started.
            </p>
          ) : (
            <div className="grid gap-2">
              {agents.slice(0, 8).map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => navigate(`/agents/${agent.id}`)}
                  className="flex items-center gap-3 w-full text-left px-3 py-2 rounded-none hover:bg-muted/40 transition-colors group"
                >
                  <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{agent.name}</span>
                      <Badge tone={STATUS_TONES[agent.status] ?? "secondary"} className="text-[10px]">
                        {agent.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {agent.model} · {agent.role}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
              {agents.length > 8 && (
                <Button
                  ghost
                  size="sm"
                  onClick={() => navigate("/agents")}
                  className="text-xs text-muted-foreground"
                >
                  View all {agents.length} agents
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Recent Activity</CardTitle>
            {logsLoading && <Spinner className="h-3 w-3" />}
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {logsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner className="text-primary" />
            </div>
          ) : recentLogs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No recent activity to show.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {recentLogs.slice(0, 10).map((log, i) => (
                <div key={log.id ?? i} className="flex items-start gap-2 px-2 py-1.5 text-xs">
                  <span className="text-muted-foreground shrink-0 font-mono">
                    {getTimeAgo(log.timestamp)}
                  </span>
                  <Badge
                    tone={log.level === "error" ? "destructive" : log.level === "warn" ? "warning" : "secondary"}
                    className="text-[10px] shrink-0"
                  >
                    {log.level ?? "info"}
                  </Badge>
                  <span className="text-muted-foreground truncate">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
