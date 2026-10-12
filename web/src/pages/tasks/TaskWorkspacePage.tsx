import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  GitBranch,
  Play,
  Pause,
  XCircle,
  RotateCw,
  ListChecks,
  Plus,
  Search,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Ban,
  FileText,
  Bot,
  Workflow,
  Zap,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@nous-research/ui/ui/components/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@nous-research/ui/ui/components/dialog";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useTaskStore, type PlanData, type TaskItem } from "@/store/task-store";
import { AgentActivityFeed } from "@/components/tasks/AgentActivityFeed";

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  completed: "success",
  running: "warning",
  failed: "destructive",
  cancelled: "outline",
  pending: "secondary",
  paused: "outline",
};

const RISK_TONES: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

function formatDuration(seconds: number): string {
  if (!seconds) return "\u2014";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function formatTime(ts?: number): string {
  if (!ts) return "\u2014";
  return new Date(ts * 1000).toLocaleString();
}

function TaskStatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONES[status] ?? "secondary";
  return <Badge variant={tone}>{status}</Badge>;
}

export default function TaskWorkspacePage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { setTitle, setDescription } = usePageHeader();
  const {
    plans, loading, stats, events, agents, activeAgents, templates, pendingApprovals,
    fetchPlans, fetchStats, fetchEvents, fetchAgents, fetchActiveAgents,
    fetchTemplates, fetchPendingApprovals, submitGoal, executeNL, pausePlan,
    resumePlan, cancelPlan, retryTask, clearCurrentPlan,
  } = useTaskStore();
  const { toast, showToast } = useToast();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [goalInput, setGoalInput] = useState("");
  const [nlInput, setNLInput] = useState("");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    setTitle("Task Orchestrator");
    setDescription("Advanced autonomous task orchestration workspace");
    fetchPlans();
    fetchStats();
    fetchEvents();
    fetchAgents();
    fetchActiveAgents();
    fetchTemplates();
    fetchPendingApprovals();
    const interval = setInterval(() => {
      fetchPlans();
      fetchStats();
      fetchEvents();
      fetchActiveAgents();
      fetchPendingApprovals();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredPlans = useMemo(() => {
    let list = plans;
    if (statusFilter !== "all") {
      list = list.filter(p => p.status === statusFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.goal.toLowerCase().includes(q));
    }
    return list;
  }, [plans, search, statusFilter]);

  const handleSubmitGoal = useCallback(async () => {
    if (!goalInput.trim()) return;
    setSubmitting(true);
    try {
      const plan = await submitGoal(goalInput.trim());
      if (plan) {
        showToast({ title: "Plan created", description: `Plan ${plan.id} is being executed` });
        setGoalInput("");
        setSubmitOpen(false);
      }
    } finally {
      setSubmitting(false);
    }
  }, [goalInput, submitGoal, showToast]);

  const handleNLSubmit = useCallback(async () => {
    if (!nlInput.trim()) return;
    setSubmitting(true);
    try {
      const plan = await executeNL(nlInput.trim());
      if (plan) {
        showToast({ title: "Task created", description: `Plan ${plan.id} created from natural language` });
        setNLInput("");
      }
    } finally {
      setSubmitting(false);
    }
  }, [nlInput, executeNL, showToast]);

  const handlePause = useCallback(async (planId: string) => {
    const ok = await pausePlan(planId);
    if (ok) showToast({ title: "Paused", description: `Plan ${planId} paused` });
  }, [pausePlan, showToast]);

  const handleResume = useCallback(async (planId: string) => {
    const ok = await resumePlan(planId);
    if (ok) showToast({ title: "Resumed", description: `Plan ${planId} resumed` });
  }, [resumePlan, showToast]);

  const handleCancel = useCallback(async (planId: string) => {
    const ok = await cancelPlan(planId);
    if (ok) showToast({ title: "Cancelled", description: `Plan ${planId} cancelled` });
  }, [cancelPlan, showToast]);

  const handleRetry = useCallback(async (planId: string, taskId: string) => {
    const ok = await retryTask(planId, taskId);
    if (ok) showToast({ title: "Retrying", description: `Task ${taskId} queued for retry` });
  }, [retryTask, showToast]);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Task Orchestrator</h1>
          <p className="text-muted-foreground">Advanced autonomous task orchestration workspace</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
            <Button onClick={() => setSubmitOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> New Task
            </Button>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Task</DialogTitle>
                <DialogDescription>Describe what you want to accomplish</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Goal (structured)</label>
                  <Input
                    placeholder="Research AI providers, compare pricing, create a report..."
                    value={goalInput}
                    onChange={e => setGoalInput(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleSubmitGoal} disabled={!goalInput.trim() || submitting}>
                    {submitting ? <Spinner className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
                    Submit Goal
                  </Button>
                </div>
                <hr />
                <div>
                  <label className="text-sm font-medium">Natural Language</label>
                  <Input
                    placeholder="Every Monday, research AI news and send me a summary..."
                    value={nlInput}
                    onChange={e => setNLInput(e.target.value)}
                  />
                </div>
                <Button onClick={handleNLSubmit} disabled={!nlInput.trim() || submitting} variant="secondary">
                  <Zap className="mr-2 h-4 w-4" /> Parse & Execute
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Total Plans</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{stats?.total_plans ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Completed</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-green-600">{stats?.completed_plans ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Running</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-yellow-600">{stats?.running_plans ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Failed</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold text-red-600">{stats?.failed_plans ?? 0}</div></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Active Agents</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.agent_stats?.active ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="plans">Plans</TabsTrigger>
          <TabsTrigger value="live">Live Activity</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="approvals">Approvals ({pendingApprovals.length})</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle className="text-lg">Recent Activity</CardTitle></CardHeader>
              <CardContent>
                <AgentActivityFeed events={events.slice(0, 20)} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-lg">Active Agents</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {activeAgents.length === 0 && <p className="text-sm text-muted-foreground">No active agents</p>}
                  {activeAgents.map(a => (
                    <div key={a.id} className="flex items-center justify-between p-2 rounded border">
                      <div className="flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        <span className="text-sm font-medium">{a.name}</span>
                        <Badge variant="outline">{a.role}</Badge>
                      </div>
                      <Badge variant={a.status === "running" ? "warning" : "secondary"}>{a.status}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="plans" className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Search plans..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="max-w-xs"
            />
            <select
              className="border rounded px-2 py-1 text-sm"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
            >
              <option value="all">All Status</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
              <option value="paused">Paused</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {loading && <Spinner />}

          <div className="space-y-3">
            {filteredPlans.map(plan => (
              <PlanCard
                key={plan.id}
                plan={plan}
                onPause={handlePause}
                onResume={handleResume}
                onCancel={handleCancel}
                onRetry={handleRetry}
                onClick={() => {
                  clearCurrentPlan();
                  navigate(`/tasks/${plan.id}`);
                }}
              />
            ))}
            {!loading && filteredPlans.length === 0 && (
              <p className="text-center text-muted-foreground py-8">No plans found</p>
            )}
          </div>
        </TabsContent>

        <TabsContent value="live">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Live Agent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <AgentActivityFeed events={events} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Agent Definitions</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {agents.map(a => (
                    <div key={a.role} className="p-2 rounded border">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Bot className="h-4 w-4" />
                          <span className="font-medium">{a.name}</span>
                          <Badge variant="outline">{a.role}</Badge>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{a.description}</p>
                      <div className="flex gap-1 mt-1">
                        {a.tools.slice(0, 4).map(t => (
                          <Badge key={t} variant="secondary" className="text-xs">{t}</Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Active Instances</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {activeAgents.map(a => (
                    <div key={a.id} className="flex items-center justify-between p-2 rounded border">
                      <div>
                        <div className="flex items-center gap-2">
                          <Bot className="h-4 w-4" />
                          <span className="font-medium">{a.name}</span>
                          <Badge variant="outline">{a.role}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">Task: {a.current_task_id?.slice(0, 16) || "\u2014"}</p>
                      </div>
                      <Badge variant={a.status === "running" ? "warning" : "secondary"}>{a.status}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="approvals">
          <Card>
            <CardHeader><CardTitle>Pending Approvals</CardTitle></CardHeader>
            <CardContent>
              {pendingApprovals.length === 0 && <p className="text-muted-foreground">No pending approvals</p>}
              <div className="space-y-3">
                {pendingApprovals.map(req => (
                  <ApprovalCard key={req.id} request={req} store={useTaskStore} />
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="templates">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map(tpl => (
              <Card key={tpl.id} className="cursor-pointer hover:border-primary"
                onClick={() => navigate(`/tasks?template=${tpl.id}`)}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{tpl.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">{tpl.description}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" /> {formatDuration(tpl.estimated_duration)}
                    {tpl.is_builtin && <Badge variant="outline" className="text-xs">Built-in</Badge>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PlanCard({
  plan, onPause, onResume, onCancel, onRetry, onClick,
}: {
  plan: PlanData;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string, taskId: string) => void;
  onClick: () => void;
}) {
  const completedTasks = plan.tasks.filter(t => t.status === "completed").length;
  const failedTasks = plan.tasks.filter(t => t.status === "failed").length;
  const totalTasks = plan.tasks.length;

  return (
    <Card className="hover:border-primary cursor-pointer" onClick={onClick}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{plan.goal?.slice(0, 80)}</span>
              <TaskStatusBadge status={plan.status} />
              <Badge variant={RISK_TONES[plan.risk_level] ?? "outline"}>{plan.risk_level}</Badge>
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span>{totalTasks} tasks ({completedTasks} done, {failedTasks} failed)</span>
              <span>Est: {formatDuration(plan.estimated_time)}</span>
              {plan.started_at > 0 && <span>Started: {formatTime(plan.started_at)}</span>}
            </div>
          </div>
          <div className="flex gap-1" onClick={e => e.stopPropagation()}>
            {plan.status === "running" && (
              <Button size="sm" variant="outline" onClick={() => onPause(plan.id)}>
                <Pause className="h-3 w-3" />
              </Button>
            )}
            {plan.status === "paused" && (
              <Button size="sm" variant="outline" onClick={() => onResume(plan.id)}>
                <Play className="h-3 w-3" />
              </Button>
            )}
            {(plan.status === "running" || plan.status === "paused") && (
              <Button size="sm" variant="outline" onClick={() => onCancel(plan.id)}>
                <XCircle className="h-3 w-3" />
              </Button>
            )}
            {plan.status === "failed" && (
              <Button size="sm" variant="outline" onClick={() => onCancel(plan.id)}>
                <Ban className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
        {totalTasks > 0 && (
          <div className="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${(completedTasks / totalTasks) * 100}%` }}
            />
          </div>
        )}
        {failedTasks > 0 && (
          <div className="mt-1 flex items-center gap-1 text-xs text-red-500">
            <AlertTriangle className="h-3 w-3" /> {failedTasks} task(s) failed
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ApprovalCard({ request, store }: { request: any; store: any }) {
  const { approveRequest } = store();

  return (
    <div className="p-3 rounded border">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{request.action}</span>
            <Badge variant={request.risk_level === "critical" ? "destructive" : "warning"}>{request.risk_level}</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">{request.description}</p>
          <p className="text-xs text-muted-foreground mt-1">Reason: {request.reason}</p>
        </div>
      </div>
      <div className="flex gap-2 mt-2">
        <Button size="sm" onClick={() => approveRequest(request.id, true, "user", "once")}>
          <CheckCircle2 className="mr-1 h-3 w-3" /> Approve
        </Button>
        <Button size="sm" variant="outline" onClick={() => approveRequest(request.id, true, "user", "session")}>
          Approve Session
        </Button>
        <Button size="sm" variant="destructive" onClick={() => approveRequest(request.id, false, "user", "once")}>
          <XCircle className="mr-1 h-3 w-3" /> Deny
        </Button>
      </div>
    </div>
  );
}
