import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Play, Pause, XCircle, RotateCw,
  Clock, AlertTriangle, CheckCircle2, Bot, GitBranch,
  Layers, ListChecks, FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@aetheros/ui/ui/components/tabs";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useTaskStore } from "@/store/task-store";
import { TaskGraphView } from "@/components/tasks/TaskGraphView";
import { AgentActivityFeed } from "@/components/tasks/AgentActivityFeed";
import { TaskTimeline } from "@/os/TaskTimeline";

function formatTime(ts?: number): string {
  if (!ts) return "\u2014";
  return new Date(ts * 1000).toLocaleString();
}

function formatDuration(seconds: number): string {
  if (!seconds) return "\u2014";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  completed: "success", running: "warning", failed: "destructive",
  cancelled: "outline", pending: "secondary", paused: "outline",
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { setTitle, setDescription } = usePageHeader();
  const { showToast } = useToast();
  const {
    currentPlan, loading, events, activeAgents,
    fetchPlan, fetchGraph, graph, fetchEvents,
    pausePlan, resumePlan, cancelPlan, retryTask,
  } = useTaskStore();

  const [activeTab, setActiveTab] = useState("tasks");

  useEffect(() => {
    if (id) {
      fetchPlan(id);
      fetchGraph(id);
      fetchEvents();
    }
  }, [id]);

  useEffect(() => {
    if (currentPlan) {
      setTitle(currentPlan.goal?.slice(0, 60) || "Task Detail");
      setDescription(`Plan ${currentPlan.id} - ${currentPlan.status}`);
    }
  }, [currentPlan, setTitle, setDescription]);

  const handlePause = useCallback(async () => {
    if (!id) return;
    const ok = await pausePlan(id);
    if (ok) showToast({ title: "Paused", description: "Plan paused" });
  }, [id, pausePlan, showToast]);

  const handleResume = useCallback(async () => {
    if (!id) return;
    const ok = await resumePlan(id);
    if (ok) showToast({ title: "Resumed", description: "Plan resumed" });
  }, [id, resumePlan, showToast]);

  const handleCancel = useCallback(async () => {
    if (!id) return;
    const ok = await cancelPlan(id);
    if (ok) showToast({ title: "Cancelled", description: "Plan cancelled" });
  }, [id, cancelPlan, showToast]);

  const handleRetry = useCallback(async (taskId: string) => {
    if (!id) return;
    const ok = await retryTask(id, taskId);
    if (ok) showToast({ title: "Retrying", description: `Task ${taskId} queued for retry` });
  }, [id, retryTask, showToast]);

  if (loading && !currentPlan) return <Spinner className="m-8" />;
  if (!currentPlan) return <div className="p-8 text-muted-foreground">Plan not found</div>;

  const totalTasks = currentPlan.tasks.length;
  const completedTasks = currentPlan.tasks.filter(t => t.status === "completed").length;
  const failedTasks = currentPlan.tasks.filter(t => t.status === "failed").length;
  const runningTasks = currentPlan.tasks.filter(t => t.status === "running").length;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Button aria-label="Go back" variant="ghost" size="icon" onClick={() => navigate("/tasks")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold">{currentPlan.goal?.slice(0, 80)}</h1>
            <Badge variant={STATUS_TONES[currentPlan.status] ?? "secondary"}>{currentPlan.status}</Badge>
            {currentPlan.risk_level && (
              <Badge variant="outline">{currentPlan.risk_level}</Badge>
            )}
          </div>
          <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
            <span>ID: {currentPlan.id}</span>
            <span>{totalTasks} tasks</span>
            <span>Est: {formatDuration(currentPlan.estimated_time)}</span>
            <span>Created: {formatTime(currentPlan.created_at)}</span>
          </div>
        </div>
        <div className="flex gap-2">
          {currentPlan.status === "running" && (
            <Button variant="outline" onClick={handlePause}><Pause className="mr-1 h-4 w-4" /> Pause</Button>
          )}
          {currentPlan.status === "paused" && (
            <Button variant="outline" onClick={handleResume}><Play className="mr-1 h-4 w-4" /> Resume</Button>
          )}
          {(currentPlan.status === "running" || currentPlan.status === "paused") && (
            <Button variant="destructive" onClick={handleCancel}><XCircle className="mr-1 h-4 w-4" /> Cancel</Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Total</CardTitle></CardHeader>
          <CardContent><span className="text-xl font-bold">{totalTasks}</span></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Running</CardTitle></CardHeader>
          <CardContent><span className="text-xl font-bold text-yellow-600">{runningTasks}</span></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Completed</CardTitle></CardHeader>
          <CardContent><span className="text-xl font-bold text-green-600">{completedTasks}</span></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Failed</CardTitle></CardHeader>
          <CardContent><span className="text-xl font-bold text-red-600">{failedTasks}</span></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Progress</CardTitle></CardHeader>
          <CardContent>
            <span className="text-xl font-bold">
              {totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0}%
            </span>
          </CardContent></Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-3">
          {currentPlan.tasks.map(task => (
            <TaskCard key={task.id} task={task} onRetry={handleRetry} />
          ))}
        </TabsContent>

        <TabsContent value="timeline">
          <TaskTimeline plan={currentPlan} events={events} />
        </TabsContent>

        <TabsContent value="graph">
          <Card>
            <CardContent className="pt-4">
              {graph ? <TaskGraphView graph={graph} /> : <Spinner />}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader><CardTitle>Live Activity</CardTitle></CardHeader>
            <CardContent>
              <AgentActivityFeed events={events} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents">
          <div className="space-y-2">
            {activeAgents.filter(a => currentPlan.tasks.some(t => t.id === a.current_task_id)).map(a => (
              <div key={a.id} className="flex items-center justify-between p-3 rounded border">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4" />
                  <span className="font-medium">{a.name}</span>
                  <Badge variant="outline">{a.role}</Badge>
                </div>
                <Badge variant={a.status === "running" ? "warning" : "secondary"}>{a.status}</Badge>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function TaskCard({ task, onRetry }: { task: any; onRetry: (id: string) => void }) {
  return (
    <Card>
      <CardContent className="pt-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {task.task_type === "parallel" ? (
                <Layers className="h-4 w-4 text-blue-500" />
              ) : (
                <ListChecks className="h-4 w-4" />
              )}
              <span className="font-medium">{task.name || task.description?.slice(0, 60)}</span>
              <Badge variant={STATUS_TONES[task.status] ?? "secondary"}>{task.status}</Badge>
              <Badge variant="outline">{task.agent_role}</Badge>
            </div>
            {task.description && (
              <p className="text-sm text-muted-foreground mt-1">{task.description}</p>
            )}
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span>{task.task_type}</span>
              <span>Retries: {task.retry_count}/{task.max_retries ?? 3}</span>
              {task.estimated_duration > 0 && <span>Est: {formatDuration(task.estimated_duration)}</span>}
            </div>
          </div>
          <div className="flex gap-1">
            {task.status === "failed" && (
              <Button size="sm" variant="outline" onClick={() => onRetry(task.id)}>
                <RotateCw className="h-3 w-3 mr-1" /> Retry
              </Button>
            )}
          </div>
        </div>
        {task.progress > 0 && (
          <div className="mt-2 h-1 bg-secondary rounded-full overflow-hidden">
            <div className="h-full bg-primary rounded-full" style={{ width: `${task.progress}%` }} />
          </div>
        )}
        {task.error && (
          <div className="mt-1 flex items-center gap-1 text-xs text-red-500">
            <AlertTriangle className="h-3 w-3" /> {task.error}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
