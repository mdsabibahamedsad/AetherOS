import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Workflow,
  Play,
  Plus,
  Search,
  X,
  History,
  ToggleLeft,
  ArrowRight,
  GitFork,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Loader2,
  Zap,
  Shield,
  Repeat,
  FileOutput,
  Layers,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Switch } from "@nous-research/ui/ui/components/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@nous-research/ui/ui/components/dialog";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import type { WorkflowDefinition, WorkflowNode } from "@/lib/api";

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  active: "success",
  running: "warning",
  completed: "success",
  failed: "destructive",
  draft: "outline",
};

const NODE_ICONS: Record<string, typeof Zap> = {
  trigger: Zap,
  condition: Shield,
  action: Play,
  loop: Repeat,
  subworkflow: GitFork,
  output: FileOutput,
};

const NODE_LABELS: Record<string, string> = {
  trigger: "Trigger",
  condition: "Condition",
  action: "Action",
  loop: "Loop",
  subworkflow: "Sub-Workflow",
  output: "Output",
};

const NODE_COLORS: Record<string, string> = {
  trigger: "border-l-primary",
  condition: "border-l-warning",
  action: "border-l-success",
  loop: "border-l-info",
  subworkflow: "border-l-secondary",
  output: "border-l-muted-foreground",
};

function formatTime(iso?: string | null): string {
  if (!iso) return "\u2014";
  return new Date(iso).toLocaleString();
}

export default function WorkflowRunnerPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const { workflows, loading, fetchWorkflows, createWorkflow, runWorkflow } = useAgentStore();
  const { toast, showToast } = useToast();

  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [running, setRunning] = useState<Set<string>>(new Set());
  const [showHistory, setShowHistory] = useState<WorkflowDefinition | null>(null);

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");

  useEffect(() => {
    setTitle("Workflow Runner");
    setDescription("Design and execute multi-step agent workflows");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return workflows.filter(
      (w) =>
        w.name.toLowerCase().includes(q) ||
        w.description.toLowerCase().includes(q),
    );
  }, [workflows, search]);

  const handleRun = async (wf: WorkflowDefinition) => {
    setRunning((prev) => new Set(prev).add(wf.id));
    try {
      await runWorkflow(wf.id);
      showToast(`Workflow "${wf.name}" started`, "success");
      fetchWorkflows();
    } catch (err) {
      showToast(`Failed to run "${wf.name}": ${err}`, "error");
    } finally {
      setRunning((prev) => {
        const next = new Set(prev);
        next.delete(wf.id);
        return next;
      });
    }
  };

  const handleToggle = async (wf: WorkflowDefinition) => {
    try {
      await createWorkflow({ ...wf, enabled: !wf.enabled });
      fetchWorkflows();
      showToast(`${wf.name} ${wf.enabled ? "disabled" : "enabled"}`, "success");
    } catch {
      showToast(`Failed to toggle ${wf.name}`, "error");
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      showToast("Name is required", "error");
      return;
    }
    setCreating(true);
    try {
      await createWorkflow({
        name: newName.trim(),
        description: newDescription.trim(),
        nodes: [],
        edges: [],
        variables: {},
        tags: [],
        enabled: true,
        status: "draft",
      });
      showToast(`Workflow "${newName}" created`, "success");
      setCreateOpen(false);
      setNewName("");
      setNewDescription("");
    } catch (err) {
      showToast(`Failed to create: ${err}`, "error");
    } finally {
      setCreating(false);
    }
  };

  if (loading && workflows.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="flex items-center justify-between gap-4">
        <div className="relative w-full max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input className="h-8 pl-8 text-xs" placeholder="Search workflows..." value={search} onChange={(e) => setSearch(e.target.value)} />
          {search && (
            <Button ghost size="xs" className="absolute right-1.5 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)} prefix={<Plus className="h-3.5 w-3.5" />}>
          New Workflow
        </Button>
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            {search ? "No workflows match your search" : "No workflows yet. Create your first one."}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {filtered.map((wf) => (
          <Card key={wf.id} className="rounded-none">
            <CardContent className="p-4">
              <div className="flex items-start gap-4">
                <div className="pt-0.5">
                  <Switch checked={wf.enabled} onCheckedChange={() => handleToggle(wf)} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">{wf.name}</span>
                    <Badge tone={STATUS_TONES[wf.status] ?? "outline"} className="text-xs">{wf.status}</Badge>
                    <Badge tone="secondary" className="text-xs">{wf.nodes.length} nodes</Badge>
                  </div>
                  {wf.description && (
                    <p className="text-xs text-muted-foreground mb-2">{wf.description}</p>
                  )}
                  <div className="text-xs text-muted-foreground">
                    Last run: {formatTime(wf.last_run)}
                  </div>

                  <div className="mt-3 flex items-center gap-1.5 overflow-x-auto py-1">
                    {wf.nodes.map((node, idx) => {
                      const NodeIcon = NODE_ICONS[node.type] ?? Layers;
                      return (
                        <div key={node.id} className="flex items-center gap-1.5 shrink-0">
                          {idx > 0 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
                          <div className={cn("flex items-center gap-1 px-2 py-1 border border-border border-l-2 text-xs", NODE_COLORS[node.type])}>
                            <NodeIcon className="h-3 w-3 text-muted-foreground" />
                            <span className="truncate max-w-20">{node.label || NODE_LABELS[node.type]}</span>
                          </div>
                        </div>
                      );
                    })}
                    {wf.nodes.length === 0 && (
                      <span className="text-xs text-muted-foreground italic">No nodes configured</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    size="xs"
                    outlined
                    onClick={() => setShowHistory(wf)}
                    title="Execution history"
                    prefix={<History className="h-3 w-3" />}
                  >
                    History
                  </Button>
                  <Button
                    size="xs"
                    onClick={() => handleRun(wf)}
                    disabled={running.has(wf.id) || !wf.enabled}
                    prefix={running.has(wf.id) ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                  >
                    {running.has(wf.id) ? "Running..." : "Run"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={createOpen} onOpenChange={(o: boolean) => !o && setCreateOpen(false)}>
        <DialogContent className="max-w-lg rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm flex items-center gap-2">
              <Workflow className="h-4 w-4" />
              Create Workflow
            </DialogTitle>
            <DialogDescription>Define a new multi-step workflow.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-3">
            <div className="grid gap-2">
              <Label htmlFor="wf-name">Name</Label>
              <Input id="wf-name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="My workflow" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="wf-desc">Description</Label>
              <textarea
                id="wf-desc"
                className="flex min-h-[60px] w-full border border-border bg-background/40 px-3 py-2 text-sm placeholder:text-muted-foreground"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Optional description"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <Button ghost size="sm" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating} prefix={creating ? <Spinner /> : undefined}>
              {creating ? "Creating..." : "Create Workflow"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {showHistory && (
        <Dialog open onOpenChange={(o: boolean) => !o && setShowHistory(null)}>
          <DialogContent className="max-w-lg rounded-none">
            <DialogHeader>
              <DialogTitle className="text-sm flex items-center gap-2">
                <History className="h-4 w-4" />
                {showHistory.name} - Execution History
              </DialogTitle>
            </DialogHeader>
            <div className="text-xs text-muted-foreground space-y-2">
              <div className="grid grid-cols-2 gap-2 border border-border p-2">
                <div><span className="font-medium text-foreground">Status:</span> {showHistory.status}</div>
                <div><span className="font-medium text-foreground">Nodes:</span> {showHistory.nodes.length}</div>
                <div><span className="font-medium text-foreground">Created:</span> {formatTime(showHistory.created_at)}</div>
                <div><span className="font-medium text-foreground">Last Run:</span> {formatTime(showHistory.last_run)}</div>
              </div>
              <p className="italic">Full execution history with detailed logs will be available in a future update.</p>
            </div>
            <div className="flex justify-end pt-3 border-t border-border">
              <Button size="sm" ghost onClick={() => setShowHistory(null)}>Close</Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
