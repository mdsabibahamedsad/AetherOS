import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Bot,
  Activity,
  Clock,
  DollarSign,
  FileText,
  Settings,
  ListChecks,
  Brain,
  ScrollText,
  Shield,
  Pencil,
  Check,
  X,
  RefreshCw,
  AlertTriangle,
  Zap,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { cn } from "@/lib/utils";
import type { AgentLogEntry, AgentMemoryEntry, AgentPermission } from "@/lib/api";
import { api } from "@/lib/api";

type Tab = "overview" | "config" | "tasks" | "memory" | "logs" | "permissions";

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  running: "success",
  idle: "secondary",
  paused: "warning",
  error: "destructive",
  restarting: "warning",
  stopped: "outline",
};

const TABS: { key: Tab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: "overview", label: "Overview", icon: Activity },
  { key: "config", label: "Config", icon: Settings },
  { key: "tasks", label: "Tasks", icon: ListChecks },
  { key: "memory", label: "Memory", icon: Brain },
  { key: "logs", label: "Logs", icon: ScrollText },
  { key: "permissions", label: "Permissions", icon: Shield },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatCost(n: number): string {
  return `$${n.toFixed(4)}`;
}

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { agent, loading, error, fetchAgent, updateAgent } = useAgentStore();
  const { toast, showToast } = useToast();
  const { setTitle } = usePageHeader();

  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editTags, setEditTags] = useState("");
  const [saving, setSaving] = useState(false);

  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [memories, setMemories] = useState<AgentMemoryEntry[]>([]);
  const [memoriesLoading, setMemoriesLoading] = useState(false);
  const [permissions, setPermissions] = useState<AgentPermission[]>([]);
  const [permissionsLoading, setPermissionsLoading] = useState(false);

  useEffect(() => {
    if (id) {
      fetchAgent(id);
      setTitle("Agent Details");
    }
  }, [id, fetchAgent, setTitle]);

  useEffect(() => {
    if (!id || !agent) return;
    setTitle(agent.name);
  }, [agent?.name, setTitle]);

  const fetchLogs = useCallback(async () => {
    if (!id) return;
    setLogsLoading(true);
    try {
      const res = await api.getAgentLogs(id);
      setLogs(res.logs ?? []);
    } catch {
      /* silent */
    } finally {
      setLogsLoading(false);
    }
  }, [id]);

  const fetchMemories = useCallback(async () => {
    if (!id) return;
    setMemoriesLoading(true);
    try {
      const res = await api.getAgentMemories(id);
      setMemories(res.memories ?? []);
    } catch {
      /* silent */
    } finally {
      setMemoriesLoading(false);
    }
  }, [id]);

  const fetchPermissions = useCallback(async () => {
    if (!id) return;
    setPermissionsLoading(true);
    try {
      const res = await api.getAgentPermissions(id);
      setPermissions(res.permissions ?? []);
    } catch {
      /* silent */
    } finally {
      setPermissionsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!id || !agent) return;
    if (activeTab === "logs") fetchLogs();
    if (activeTab === "memory") fetchMemories();
    if (activeTab === "permissions") fetchPermissions();
  }, [activeTab, id, agent, fetchLogs, fetchMemories, fetchPermissions]);

  const startEditing = useCallback(() => {
    if (!agent) return;
    setEditName(agent.name);
    setEditDescription(agent.description);
    setEditTags((agent.tags ?? []).join(", "));
    setEditing(true);
  }, [agent]);

  const cancelEditing = useCallback(() => {
    setEditing(false);
  }, []);

  const saveEditing = useCallback(async () => {
    if (!agent || !id) return;
    setSaving(true);
    try {
      await updateAgent(id, {
        name: editName,
        description: editDescription,
        tags: editTags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      showToast("Agent updated", "success");
      setEditing(false);
    } catch {
      showToast("Failed to update agent", "error");
    } finally {
      setSaving(false);
    }
  }, [agent, id, editName, editDescription, editTags, updateAgent, showToast]);

  if (loading && !agent) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error && !agent) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => id && fetchAgent(id)} prefix={<RefreshCw />}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!agent) return null;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Agent info header */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="rounded-lg bg-midground/10 p-2 shrink-0">
                <Bot className="h-5 w-5 text-midground" />
              </div>
              <div className="min-w-0 flex-1">
                {editing ? (
                  <div className="flex flex-col gap-2 max-w-lg">
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Name" className="text-sm" />
                    <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder="Description" className="text-xs" />
                    <Input value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder="Tags (comma-separated)" className="text-xs" />
                    <div className="flex gap-2 mt-1">
                      <Button size="xs" onClick={saveEditing} disabled={saving} prefix={saving ? <Spinner /> : <Check />}>
                        {saving ? "Saving…" : "Save"}
                      </Button>
                      <Button ghost size="xs" onClick={cancelEditing} prefix={<X />}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-base font-medium">{agent.name}</span>
                      <Badge tone={STATUS_TONES[agent.status] ?? "secondary"}>{agent.status}</Badge>
                      <Button ghost size="xs" onClick={startEditing} className="text-muted-foreground">
                        <Pencil className="h-3 w-3" />
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">{agent.description || "No description"}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                      <span className="font-mono">{agent.model}</span>
                      <span>·</span>
                      <span>{agent.provider}</span>
                      <span>·</span>
                      <span className="capitalize">{agent.role}</span>
                      {agent.memory_enabled && (
                        <>
                          <span>·</span>
                          <Badge tone="secondary" className="text-[10px]">Memory</Badge>
                        </>
                      )}
                    </div>
                    {agent.tags && agent.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {agent.tags.map((tag) => (
                          <span key={tag} className="text-[10px] font-mono text-text-tertiary border border-border px-1 py-px">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">
                      Created {new Date(agent.created_at).toLocaleDateString()} · Updated {new Date(agent.updated_at).toLocaleDateString()}
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-border pb-px">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-2 text-xs transition-colors border-b-2 -mb-px",
              activeTab === key
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && <OverviewTab agent={agent} />}
      {activeTab === "config" && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            <Button onClick={() => navigate(`/agents/${id}/config`)} prefix={<Settings />}>
              Open Config Editor
            </Button>
          </CardContent>
        </Card>
      )}
      {activeTab === "tasks" && <TasksTab agentId={id!} />}
      {activeTab === "memory" && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Memory ({memories.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {memoriesLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : memories.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No memory entries.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {memories.slice(0, 20).map((mem) => (
                  <div key={mem.id} className="border border-border p-2 text-xs">
                    <p className="text-muted-foreground">{mem.content ?? JSON.stringify(mem.data)}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
      {activeTab === "logs" && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <ScrollText className="h-4 w-4" />
              Logs ({logs.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {logsLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : logs.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No logs available.</p>
            ) : (
              <div className="flex flex-col gap-1 max-h-96 overflow-y-auto">
                {logs.map((log, i) => (
                  <div key={log.id ?? i} className="flex items-start gap-2 text-xs py-1 font-mono">
                    <span className="text-muted-foreground shrink-0">{new Date(log.timestamp ?? Date.now()).toLocaleTimeString()}</span>
                    <Badge
                      tone={log.level === "error" ? "destructive" : log.level === "warn" ? "warning" : "secondary"}
                      className="text-[10px] shrink-0"
                    >
                      {log.level ?? "info"}
                    </Badge>
                    <span className="text-muted-foreground">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
      {activeTab === "permissions" && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Permissions ({permissions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {permissionsLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : permissions.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No permissions configured.</p>
            ) : (
              <div className="flex flex-col gap-1">
                {permissions.map((perm) => (
                  <div key={perm.id} className="flex items-center justify-between border border-border p-2 text-xs">
                    <span className="font-mono">{perm.resource ?? perm.action}</span>
                    <Badge tone={perm.granted ? "success" : "destructive"}>
                      {perm.granted ? "Granted" : "Denied"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function OverviewTab({ agent }: { agent: NonNullable<ReturnType<typeof useAgentStore.getState>["agent"]> }) {
  const { stats } = agent;
  const statCards = [
    { label: "Tasks Completed", value: formatNumber(stats.tasks_completed ?? 0), icon: Zap, color: "text-success" },
    { label: "Tasks Failed", value: formatNumber(stats.tasks_failed ?? 0), icon: AlertTriangle, color: "text-destructive" },
    { label: "Avg Duration", value: stats.avg_duration || "—", icon: Clock, color: "text-muted-foreground" },
    { label: "Total Tokens", value: formatNumber(stats.total_tokens ?? 0), icon: Activity, color: "text-primary" },
    { label: "Total Cost", value: formatCost(stats.total_cost ?? 0), icon: DollarSign, color: "text-warning" },
  ];

  return (
    <div className="grid gap-3">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
                <Icon className={cn("h-4 w-4", color)} />
              </div>
              <span className="text-xl font-bold">{value}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">Toolsets</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {agent.toolsets && agent.toolsets.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {agent.toolsets.map((ts) => (
                <Badge key={ts} tone="secondary" className="text-xs">{ts}</Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No toolsets assigned.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">Last Active</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <p className="text-sm text-muted-foreground">
            {agent.last_active ? new Date(agent.last_active).toLocaleString() : "Never"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function TasksTab({ agentId }: { agentId: string }) {
  const [tasks, setTasks] = useState<Awaited<ReturnType<typeof api.getTasks>>["tasks"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.getTasks()
      .then((res) => { if (!cancelled) setTasks(res.tasks ?? []); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [agentId]);

  const agentTasks = tasks.filter((t) => t.agent_id === agentId);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm flex items-center gap-2">
          <ListChecks className="h-4 w-4" />
          Tasks ({agentTasks.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        {loading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : agentTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">No tasks for this agent.</p>
        ) : (
          <div className="flex flex-col gap-1">
            {agentTasks.map((task) => (
              <div key={task.id} className="flex items-center justify-between border border-border p-2 text-xs">
                <div className="min-w-0 flex-1">
                  <span className="font-medium truncate block">{task.name}</span>
                  <span className="text-muted-foreground">{task.description}</span>
                </div>
                <Badge
                  tone={task.status === "completed" ? "success" : task.status === "failed" ? "destructive" : task.status === "running" ? "warning" : "secondary"}
                  className="text-[10px] ml-2"
                >
                  {task.status}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
