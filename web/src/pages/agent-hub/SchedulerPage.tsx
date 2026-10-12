import { useCallback, useEffect, useState } from "react";
import { Calendar, Clock, Play, Plus, RefreshCw, Trash2, ToggleLeft, ToggleRight, History, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Select, SelectOption } from "@aetheros/ui/ui/components/select";
import { Textarea } from "@/components/Textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@aetheros/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { SchedulerJob, Agent } from "@/lib/api";

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

const SCHEDULE_TYPES = ["cron", "interval", "once"] as const;

function getScheduleLabel(type: string): string {
  const labels: Record<string, string> = { cron: "Cron", interval: "Interval", once: "Once" };
  return labels[type] ?? type;
}

export default function SchedulerPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { schedulers, agents, fetchSchedulers, fetchAgents, createScheduler, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<SchedulerJob | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<Array<{ ran_at: string; status: string; duration: string; error?: string }>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formAgentId, setFormAgentId] = useState("");
  const [formScheduleType, setFormScheduleType] = useState<string>("cron");
  const [formSchedule, setFormSchedule] = useState("");
  const [formAction, setFormAction] = useState("");
  const [formCronMinute, setFormCronMinute] = useState("*");
  const [formCronHour, setFormCronHour] = useState("*");
  const [formCronDay, setFormCronDay] = useState("*");
  const [formCronMonth, setFormCronMonth] = useState("*");
  const [formCronWeekday, setFormCronWeekday] = useState("*");
  const [formIntervalValue, setFormIntervalValue] = useState("30");
  const [formIntervalUnit, setFormIntervalUnit] = useState("minutes");
  const [formOnceDate, setFormOnceDate] = useState("");

  const [deleteConfirm, setDeleteConfirm] = useState<SchedulerJob | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setTitle("Job Scheduler");
    setDescription("Manage scheduled jobs for agents");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await Promise.all([fetchSchedulers(), fetchAgents()]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchSchedulers, fetchAgents]);

  useEffect(() => { load(); }, [load]);

  const resetForm = () => {
    setFormName("");
    setFormDesc("");
    setFormAgentId("");
    setFormScheduleType("cron");
    setFormSchedule("");
    setFormAction("");
    setFormCronMinute("*");
    setFormCronHour("*");
    setFormCronDay("*");
    setFormCronMonth("*");
    setFormCronWeekday("*");
    setFormIntervalValue("30");
    setFormIntervalUnit("minutes");
    setFormOnceDate("");
  };

  const buildScheduleString = () => {
    if (formScheduleType === "cron") {
      return `${formCronMinute} ${formCronHour} ${formCronDay} ${formCronMonth} ${formCronWeekday}`;
    }
    if (formScheduleType === "interval") {
      return `every ${formIntervalValue} ${formIntervalUnit}`;
    }
    return formOnceDate;
  };

  const handleCreate = async () => {
    if (!formAction.trim()) {
      toast({ title: "Action is required", variant: "destructive" });
      return;
    }
    setCreating(true);
    try {
      await createScheduler({
        name: formName.trim() || undefined,
        description: formDesc.trim() || undefined,
        agent_id: formAgentId || undefined,
        schedule_type: formScheduleType as SchedulerJob["schedule_type"],
        schedule: buildScheduleString(),
        action: formAction.trim(),
      });
      toast({ title: "Job created", variant: "success" });
      setCreateOpen(false);
      resetForm();
    } catch (err) {
      toast({ title: `Failed to create: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (job: SchedulerJob) => {
    try {
      await api.updateSchedulerJob(job.id, { enabled: !job.enabled });
      await fetchSchedulers();
      toast({ title: job.enabled ? "Job disabled" : "Job enabled", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await api.deleteSchedulerJob(deleteConfirm.id);
      await fetchSchedulers();
      toast({ title: "Job deleted", variant: "success" });
      setDeleteConfirm(null);
    } catch (err) {
      toast({ title: `Failed to delete: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const handleTrigger = async (job: SchedulerJob) => {
    try {
      await api.triggerSchedulerJob(job.id);
      toast({ title: "Job triggered", variant: "success" });
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    }
  };

  const openHistory = async (job: SchedulerJob) => {
    setSelectedJob(job);
    setHistoryLoading(true);
    try {
      const res = await api.getSchedulerJobHistory(job.id);
      setHistory(res.runs ?? []);
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
      setHistoryOpen(true);
    }
  };

  const agentMap = new Map(agents.map((a: Agent) => [a.id, a]));

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-midground" />
          <span className="text-sm text-muted-foreground">{schedulers.length} jobs</span>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)} prefix={<Plus className="h-4 w-4" />}>
          Create Job
        </Button>
      </div>

      {schedulers.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No scheduled jobs. Create one to get started.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {schedulers.map((job) => {
          const agent = job.agent_id ? agentMap.get(job.agent_id) : null;
          return (
            <Card key={job.id}>
              <CardContent className="py-4 px-5">
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm truncate">{job.name || job.action}</span>
                      <Badge tone={job.enabled ? "success" : "secondary"}>{job.enabled ? "Active" : "Disabled"}</Badge>
                      <Badge tone="outline">{getScheduleLabel(job.schedule_type)}</Badge>
                    </div>
                    {job.description && (
                      <p className="text-xs text-muted-foreground truncate mb-1">{job.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="font-mono-ui">{job.schedule}</span>
                      {agent && <span>Agent: {agent.name}</span>}
                      <span>Next: {formatTime(job.next_run)}</span>
                      <span>Last: {formatTime(job.last_run)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button aria-label={job.enabled ? "Disable" : "Enable"} ghost size="icon" onClick={() => handleToggle(job)} title={job.enabled ? "Disable" : "Enable"}>
                      {job.enabled ? <ToggleRight className="h-4 w-4 text-success" /> : <ToggleLeft className="h-4 w-4 text-muted-foreground" />}
                    </Button>
                    <Button aria-label="Run now" ghost size="icon" onClick={() => handleTrigger(job)} title="Run now">
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button aria-label="History" ghost size="icon" onClick={() => openHistory(job)} title="History">
                      <History className="h-4 w-4" />
                    </Button>
                    <Button aria-label="Delete" ghost size="icon" destructive onClick={() => setDeleteConfirm(job)} title="Delete">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {createOpen && (
        <Dialog open={createOpen} onOpenChange={(o) => { if (!o) setCreateOpen(false); }}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Scheduled Job</DialogTitle>
              <DialogDescription>Configure a new job to run on a schedule.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="job-name">Name</Label>
                <Input id="job-name" placeholder="Optional name" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="job-desc">Description</Label>
                <Textarea id="job-desc" placeholder="Optional description" value={formDesc} onChange={(e) => setFormDesc(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="job-agent">Agent</Label>
                <Select id="job-agent" value={formAgentId} onValueChange={setFormAgentId}>
                  <SelectOption value="">No agent (system)</SelectOption>
                  {agents.map((a: Agent) => (
                    <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
                  ))}
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="job-schedule-type">Schedule Type</Label>
                <Select id="job-schedule-type" value={formScheduleType} onValueChange={setFormScheduleType}>
                  {SCHEDULE_TYPES.map((st) => (
                    <SelectOption key={st} value={st}>{getScheduleLabel(st)}</SelectOption>
                  ))}
                </Select>
              </div>
              {formScheduleType === "cron" && (
                <div className="grid grid-cols-5 gap-2">
                  <div className="grid gap-1">
                    <Label className="text-xs">Minute</Label>
                    <Input value={formCronMinute} onChange={(e) => setFormCronMinute(e.target.value)} placeholder="*" />
                  </div>
                  <div className="grid gap-1">
                    <Label className="text-xs">Hour</Label>
                    <Input value={formCronHour} onChange={(e) => setFormCronHour(e.target.value)} placeholder="*" />
                  </div>
                  <div className="grid gap-1">
                    <Label className="text-xs">Day</Label>
                    <Input value={formCronDay} onChange={(e) => setFormCronDay(e.target.value)} placeholder="*" />
                  </div>
                  <div className="grid gap-1">
                    <Label className="text-xs">Month</Label>
                    <Input value={formCronMonth} onChange={(e) => setFormCronMonth(e.target.value)} placeholder="*" />
                  </div>
                  <div className="grid gap-1">
                    <Label className="text-xs">Weekday</Label>
                    <Input value={formCronWeekday} onChange={(e) => setFormCronWeekday(e.target.value)} placeholder="*" />
                  </div>
                </div>
              )}
              {formScheduleType === "interval" && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="grid gap-2">
                    <Label>Every</Label>
                    <Input type="number" min={1} value={formIntervalValue} onChange={(e) => setFormIntervalValue(e.target.value)} />
                  </div>
                  <div className="grid gap-2">
                    <Label>Unit</Label>
                    <Select value={formIntervalUnit} onValueChange={setFormIntervalUnit}>
                      <SelectOption value="minutes">Minutes</SelectOption>
                      <SelectOption value="hours">Hours</SelectOption>
                      <SelectOption value="days">Days</SelectOption>
                    </Select>
                  </div>
                </div>
              )}
              {formScheduleType === "once" && (
                <div className="grid gap-2">
                  <Label>Run At</Label>
                  <Input type="datetime-local" value={formOnceDate} onChange={(e) => setFormOnceDate(e.target.value)} />
                </div>
              )}
              <div className="grid gap-2">
                <Label htmlFor="job-action">Action</Label>
                <Textarea id="job-action" placeholder="What should this job do?" value={formAction} onChange={(e) => setFormAction(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={creating} prefix={creating ? <Spinner /> : undefined}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {deleteConfirm && (
        <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Job</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete "{deleteConfirm.name || deleteConfirm.action}"? This cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
              <Button destructive onClick={handleDelete} disabled={deleting} prefix={deleting ? <Spinner /> : undefined}>
                {deleting ? "Deleting..." : "Delete"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Run History</DialogTitle>
            <DialogDescription>{selectedJob?.name || selectedJob?.action}</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 overflow-y-auto">
            {historyLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : history.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-8">No runs yet.</p>
            ) : (
              <div className="space-y-2">
                {history.map((run, i) => (
                  <div key={i} className="flex items-center gap-3 py-2 px-3 border border-border rounded text-xs">
                    <Badge tone={run.status === "success" ? "success" : run.status === "failed" ? "destructive" : "secondary"}>
                      {run.status}
                    </Badge>
                    <span className="text-muted-foreground">{formatTime(run.ran_at)}</span>
                    <span className="text-muted-foreground">{run.duration}</span>
                    {run.error && <span className="text-destructive truncate">{run.error}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
