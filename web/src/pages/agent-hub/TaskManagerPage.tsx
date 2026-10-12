import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ListChecks,
  Play,
  X,
  Search,
  Plus,
  ChevronDown,
  ChevronRight,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Ban,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@nous-research/ui/ui/components/dialog";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import type { TaskDefinition, Agent } from "@/lib/api";

const PRIORITY_TONES: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  running: "warning",
  completed: "success",
  failed: "destructive",
  cancelled: "outline",
  pending: "secondary",
};

function formatTime(iso?: string | null): string {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleString();
}

export default function TaskManagerPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const { tasks, loading, fetchTasks, createTask, updateTask } = useAgentStore();
  const { toast, showToast } = useToast();

  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [filterAgent, setFilterAgent] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [agents, setAgents] = useState<Agent[]>([]);

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newAgentId, setNewAgentId] = useState("");
  const [newPriority, setNewPriority] = useState<TaskDefinition["priority"]>("medium");
  const [newInput, setNewInput] = useState("");
  const [newSchedule, setNewSchedule] = useState("");

  useEffect(() => {
    setTitle("Task Manager");
    setDescription("Manage and monitor agent tasks");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchTasks();
    api.getAgents().then((res) => setAgents(res.agents ?? [])).catch(() => {});
  }, [fetchTasks]);

  const toggleExpanded = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return tasks.filter((task) => {
      if (q && !task.name.toLowerCase().includes(q) && !task.description.toLowerCase().includes(q)) return false;
      if (filterStatus !== "all" && task.status !== filterStatus) return false;
      if (filterPriority !== "all" && task.priority !== filterPriority) return false;
      if (filterAgent !== "all" && task.agent_id !== filterAgent) return false;
      return true;
    });
  }, [tasks, search, filterStatus, filterPriority, filterAgent]);

  const stats = useMemo(() => ({
    total: tasks.length,
    running: tasks.filter((t) => t.status === "running").length,
    completed: tasks.filter((t) => t.status === "completed").length,
    failed: tasks.filter((t) => t.status === "failed").length,
  }), [tasks]);

  const handleCancel = async (task: TaskDefinition) => {
    if (task.status !== "running" && task.status !== "pending") return;
    try {
      await updateTask(task.id, { ...task, status: "cancelled" });
      showToast(`Task "${task.name}" cancelled`, "success");
    } catch {
      showToast(`Failed to cancel "${task.name}"`, "error");
    }
  };

  const handleCreate = async () => {
    if (!newName.trim() || !newAgentId) {
      showToast("Name and agent are required", "error");
      return;
    }
    setCreating(true);
    try {
      await createTask({
        name: newName.trim(),
        description: newDescription.trim(),
        agent_id: newAgentId,
        priority: newPriority,
        input: newInput.trim() ? JSON.parse(newInput) : {},
        status: "pending",
        progress: 0,
        scheduled_at: newSchedule || null,
        tags: [],
      });
      showToast(`Task "${newName}" created`, "success");
      setCreateOpen(false);
      setNewName("");
      setNewDescription("");
      setNewAgentId("");
      setNewPriority("medium");
      setNewInput("");
      setNewSchedule("");
    } catch (err) {
      showToast(`Failed to create task: ${err}`, "error");
    } finally {
      setCreating(false);
    }
  };

  if (loading && tasks.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">Total</span>
              <ListChecks className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">Running</span>
              <Play className="h-4 w-4 text-warning" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats.running}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">Completed</span>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats.completed}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase">Failed</span>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats.failed}</div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input className="h-8 pl-8 text-xs" placeholder="Search tasks..." value={search} onChange={(e) => setSearch(e.target.value)} />
          {search && (
            <Button ghost size="xs" className="absolute right-1.5 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectOption value="all">All statuses</SelectOption>
          <SelectOption value="pending">Pending</SelectOption>
          <SelectOption value="running">Running</SelectOption>
          <SelectOption value="completed">Completed</SelectOption>
          <SelectOption value="failed">Failed</SelectOption>
          <SelectOption value="cancelled">Cancelled</SelectOption>
        </Select>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectOption value="all">All priorities</SelectOption>
          <SelectOption value="critical">Critical</SelectOption>
          <SelectOption value="high">High</SelectOption>
          <SelectOption value="medium">Medium</SelectOption>
          <SelectOption value="low">Low</SelectOption>
        </Select>
        <Select value={filterAgent} onValueChange={setFilterAgent}>
          <SelectOption value="all">All agents</SelectOption>
          {agents.map((a) => (
            <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
          ))}
        </Select>
        <Button size="sm" onClick={() => setCreateOpen(true)} prefix={<Plus className="h-3.5 w-3.5" />}>
          New Task
        </Button>
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            {search || filterStatus !== "all" || filterPriority !== "all" || filterAgent !== "all"
              ? "No tasks match the current filters"
              : "No tasks yet"}
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-1">
        {filtered.map((task) => {
          const isExpanded = expanded.has(task.id);
          return (
            <Card key={task.id} className="rounded-none">
              <CardContent className="p-0">
                <button
                  type="button"
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/20 transition-colors"
                  onClick={() => toggleExpanded(task.id)}
                >
                  <div className="text-muted-foreground">
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0 grid grid-cols-5 gap-3 items-center text-sm">
                    <span className="font-medium truncate">{task.name}</span>
                    <span className="text-xs text-muted-foreground truncate">
                      {agents.find((a) => a.id === task.agent_id)?.name ?? task.agent_id}
                    </span>
                    <Badge tone={PRIORITY_TONES[task.priority] ?? "outline"} className="text-xs w-fit">
                      {task.priority}
                    </Badge>
                    <Badge tone={STATUS_TONES[task.status] ?? "outline"} className="text-xs w-fit">
                      {task.status}
                    </Badge>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all",
                            task.status === "completed" && "bg-success",
                            task.status === "failed" && "bg-destructive",
                            task.status === "running" && "bg-warning",
                            task.status === "pending" && "bg-muted-foreground/30",
                          )}
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-xs tabular-nums text-muted-foreground w-8 text-right">{task.progress}%</span>
                    </div>
                  </div>
                </button>
                {isExpanded && (
                  <div className="border-t border-border px-4 py-3 grid grid-cols-2 gap-3 text-xs text-muted-foreground bg-muted/10">
                    <div><span className="font-medium text-foreground">ID:</span> {task.id}</div>
                    <div><span className="font-medium text-foreground">Created:</span> {formatTime(task.created_at)}</div>
                    <div><span className="font-medium text-foreground">Started:</span> {formatTime(task.started_at)}</div>
                    <div><span className="font-medium text-foreground">Completed:</span> {formatTime(task.completed_at)}</div>
                    {task.error && (
                      <div className="col-span-2 text-destructive">
                        <span className="font-medium">Error:</span> {task.error}
                      </div>
                    )}
                    <div className="col-span-2">
                      <span className="font-medium text-foreground">Input:</span>
                      <pre className="mt-1 bg-background/50 border border-border p-2 overflow-auto max-h-32 font-mono">
                        {JSON.stringify(task.input, null, 2)}
                      </pre>
                    </div>
                    {task.output && (
                      <div className="col-span-2">
                        <span className="font-medium text-foreground">Output:</span>
                        <pre className="mt-1 bg-background/50 border border-border p-2 overflow-auto max-h-32 font-mono">
                          {JSON.stringify(task.output, null, 2)}
                        </pre>
                      </div>
                    )}
                    <div className="col-span-2 flex justify-end">
                      {(task.status === "running" || task.status === "pending") && (
                        <Button size="xs" destructive onClick={() => handleCancel(task)} prefix={<Ban className="h-3 w-3" />}>
                          Cancel Task
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={createOpen} onOpenChange={(o: boolean) => !o && setCreateOpen(false)}>
        <DialogContent className="max-w-lg rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Create Task
            </DialogTitle>
            <DialogDescription>Define a new task for an agent to execute.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <div className="grid gap-2">
              <Label htmlFor="task-name">Name</Label>
              <Input id="task-name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Task name" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="task-desc">Description</Label>
              <textarea
                id="task-desc"
                className="flex min-h-[60px] w-full border border-border bg-background/40 px-3 py-2 text-sm placeholder:text-muted-foreground"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label htmlFor="task-agent">Agent</Label>
                <Select value={newAgentId} onValueChange={setNewAgentId}>
                  {agents.map((a) => (
                    <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
                  ))}
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="task-priority">Priority</Label>
                <Select value={newPriority} onValueChange={(v) => setNewPriority(v as TaskDefinition["priority"])}>
                  <SelectOption value="low">Low</SelectOption>
                  <SelectOption value="medium">Medium</SelectOption>
                  <SelectOption value="high">High</SelectOption>
                  <SelectOption value="critical">Critical</SelectOption>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="task-input">Input JSON (optional)</Label>
              <textarea
                id="task-input"
                className="flex min-h-[80px] w-full border border-border bg-background/40 px-3 py-2 text-sm font-mono placeholder:text-muted-foreground"
                value={newInput}
                onChange={(e) => setNewInput(e.target.value)}
                placeholder='{"key": "value"}'
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="task-schedule">Schedule (optional)</Label>
              <Input
                id="task-schedule"
                value={newSchedule}
                onChange={(e) => setNewSchedule(e.target.value)}
                placeholder="ISO timestamp or cron expression"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <Button ghost size="sm" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating} prefix={creating ? <Spinner /> : undefined}>
              {creating ? "Creating..." : "Create Task"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
