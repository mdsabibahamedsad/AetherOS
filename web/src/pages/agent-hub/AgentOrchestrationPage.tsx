import { useCallback, useEffect, useMemo, useState } from "react";
import {
  GitBranch,
  Play,
  Square,
  RefreshCw,
  Plus,
  X,
  Users,
  Layers,
  Share2,
  MessageSquare,
  Vote,
  Clock,
  Bot,
  AlertTriangle,
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
import { Label } from "@nous-research/ui/ui/components/label";
import { Textarea } from "@/components/Textarea";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@nous-research/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { cn } from "@/lib/utils";
import type { AgentOrchestration } from "@/lib/api";
import { api } from "@/lib/api";

const STRATEGY_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }>; description: string }> = {
  sequential: { label: "Sequential", icon: Layers, description: "Agents run one after another in order" },
  parallel: { label: "Parallel", icon: Share2, description: "All agents run simultaneously" },
  fan_out: { label: "Fan-out", icon: GitBranch, description: "Input broadcast to all agents, results aggregated" },
  debate: { label: "Debate", icon: MessageSquare, description: "Agents debate to reach consensus" },
  voting: { label: "Voting", icon: Vote, description: "Each agent votes, majority decides output" },
  hierarchical: { label: "Hierarchical", icon: GitBranch, description: "Manager agent coordinates worker agents" },
};

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary"> = {
  running: "warning",
  completed: "success",
  failed: "destructive",
  idle: "secondary",
};

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function AgentOrchestrationPage() {
  const { orchestrations, fetchOrchestrations, createOrchestration, agents } = useAgentStore();
  const { toast, showToast } = useToast();
  const { setTitle } = usePageHeader();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedOrch, setSelectedOrch] = useState<AgentOrchestration | null>(null);
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // Create form
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newStrategy, setNewStrategy] = useState<string>("sequential");
  const [newAgents, setNewAgents] = useState<string[]>([]);
  const [newMaxConcurrent, setNewMaxConcurrent] = useState(5);
  const [newTimeout, setNewTimeout] = useState(300);
  const [newInputTemplate, setNewInputTemplate] = useState("");
  const [newOutputAggregator, setNewOutputAggregator] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setTitle("Orchestrations");
  }, [setTitle]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchOrchestrations()
      .catch((err: unknown) => {
        if (!cancelled) setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [fetchOrchestrations]);

  const handleStartStop = useCallback(async (orch: AgentOrchestration) => {
    try {
      if (orch.status === "running") {
        await api.createOrchestration({ ...orch, enabled: false });
        showToast("Orchestration stopped", "success");
      } else {
        await api.createOrchestration({ ...orch, enabled: true });
        showToast("Orchestration started", "success");
      }
      fetchOrchestrations();
    } catch {
      showToast("Failed to update orchestration", "error");
    }
  }, [fetchOrchestrations, showToast]);

  const handleCreate = useCallback(async () => {
    if (!newName.trim()) {
      showToast("Name is required", "error");
      return;
    }
    setSubmitting(true);
    try {
      await createOrchestration({
        name: newName.trim(),
        description: newDescription.trim(),
        strategy: newStrategy as AgentOrchestration["strategy"],
        agents: newAgents,
        max_concurrent: newMaxConcurrent,
        timeout: newTimeout,
        input_template: newInputTemplate,
        output_aggregator: newOutputAggregator,
        enabled: true,
        status: "idle",
      });
      showToast("Orchestration created", "success");
      setCreateOpen(false);
      resetForm();
    } catch {
      showToast("Failed to create orchestration", "error");
    } finally {
      setSubmitting(false);
    }
  }, [newName, newDescription, newStrategy, newAgents, newMaxConcurrent, newTimeout, newInputTemplate, newOutputAggregator, createOrchestration, showToast]);

  const resetForm = useCallback(() => {
    setNewName("");
    setNewDescription("");
    setNewStrategy("sequential");
    setNewAgents([]);
    setNewMaxConcurrent(5);
    setNewTimeout(300);
    setNewInputTemplate("");
    setNewOutputAggregator("");
  }, []);

  const toggleAgentSelection = useCallback((agentId: string) => {
    setNewAgents((prev) =>
      prev.includes(agentId) ? prev.filter((id) => id !== agentId) : [...prev, agentId],
    );
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => fetchOrchestrations()} prefix={<RefreshCw />}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const StrategyIcon = STRATEGY_META[selectedOrch?.strategy ?? "sequential"]?.icon ?? GitBranch;

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {orchestrations.length} orchestration{orchestrations.length !== 1 ? "s" : ""}
        </p>
        <Button onClick={() => setCreateOpen(true)} prefix={<Plus />}>
          Create Orchestration
        </Button>
      </div>

      {orchestrations.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No orchestrations yet. Create one to coordinate multiple agents.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {orchestrations.map((orch) => {
            const meta = STRATEGY_META[orch.strategy] ?? STRATEGY_META.sequential;
            const StratIcon = meta.icon;
            return (
              <Card key={orch.id} className="rounded-none">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <StratIcon className="h-4 w-4 text-muted-foreground" />
                        <button
                          type="button"
                          onClick={() => setSelectedOrch(selectedOrch?.id === orch.id ? null : orch)}
                          className="text-sm font-medium hover:underline text-left"
                        >
                          {orch.name}
                        </button>
                        <Badge tone={STATUS_TONES[orch.status] ?? "secondary"}>
                          {orch.status}
                        </Badge>
                        <Badge tone="secondary" className="text-xs">
                          {meta.label}
                        </Badge>
                      </div>
                      {orch.description && (
                        <p className="text-xs text-muted-foreground mb-1">{orch.description}</p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Bot className="h-3 w-3" />
                          {orch.agents?.length ?? 0} agents
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Timeout: {orch.timeout ?? 300}s
                        </span>
                        {orch.last_run && (
                          <span>Last run: {formatTime(orch.last_run)}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0 ml-4">
                      <Button
                        ghost
                        size="icon"
                        title={orch.status === "running" ? "Stop" : "Start"}
                        aria-label={orch.status === "running" ? "Stop" : "Start"}
                        onClick={() => handleStartStop(orch)}
                        className={orch.status === "running" ? "text-destructive" : "text-success"}
                      >
                        {orch.status === "running" ? <Square /> : <Play />}
                      </Button>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {selectedOrch?.id === orch.id && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                        <div>
                          <Label className="text-xs text-muted-foreground">Strategy</Label>
                          <p className="flex items-center gap-2 mt-1">
                            <StratIcon className="h-4 w-4" />
                            <span className="font-medium">{meta.label}</span>
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">{meta.description}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Max Concurrent</Label>
                          <p className="mt-1">{orch.max_concurrent ?? 5}</p>
                        </div>
                        {orch.input_template && (
                          <div className="sm:col-span-2">
                            <Label className="text-xs text-muted-foreground">Input Template</Label>
                            <pre className="mt-1 text-xs font-mono text-muted-foreground bg-background/50 border border-border p-2 whitespace-pre-wrap">
                              {orch.input_template}
                            </pre>
                          </div>
                        )}
                        {orch.output_aggregator && (
                          <div className="sm:col-span-2">
                            <Label className="text-xs text-muted-foreground">Output Aggregator</Label>
                            <p className="mt-1 text-xs font-mono text-muted-foreground">{orch.output_aggregator}</p>
                          </div>
                        )}
                        <div>
                          <Label className="text-xs text-muted-foreground">Created</Label>
                          <p className="mt-1 text-xs">{formatTime(orch.created_at)}</p>
                        </div>
                      </div>

                      {orch.agents && orch.agents.length > 0 && (
                        <div className="mt-4">
                          <Label className="text-xs text-muted-foreground mb-2 block">Assigned Agents</Label>
                          <div className="flex flex-wrap gap-2">
                            {orch.agents.map((agentId) => {
                              const agent = agents.find((a) => a.id === agentId);
                              return (
                                <Badge key={agentId} tone="secondary" className="text-xs">
                                  {agent?.name ?? agentId}
                                </Badge>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Strategy legend */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">Strategy Types</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(STRATEGY_META).map(([key, { label, icon: Icon, description }]) => (
              <div key={key} className="flex items-start gap-2 text-xs">
                <Icon className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
                <div>
                  <span className="font-medium">{label}</span>
                  <p className="text-muted-foreground">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={(o: boolean) => { if (!o) { setCreateOpen(false); resetForm(); } }}>
        <DialogContent className="max-w-lg rounded-none max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-sm flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              New Orchestration
            </DialogTitle>
            <DialogDescription className="text-xs">
              Configure a multi-agent orchestration workflow.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 mt-2">
            <div className="grid gap-2">
              <Label htmlFor="orch-name">Name *</Label>
              <Input id="orch-name" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="My orchestration" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="orch-desc">Description</Label>
              <Textarea id="orch-desc" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} placeholder="What does this orchestration do?" className="min-h-[60px]" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="orch-strategy">Strategy</Label>
              <Select value={newStrategy} onValueChange={(v) => setNewStrategy(v)}>
                {Object.entries(STRATEGY_META).map(([key, { label }]) => (
                  <SelectOption key={key} value={key}>{label}</SelectOption>
                ))}
              </Select>
              {newStrategy && (
                <p className="text-xs text-muted-foreground">{STRATEGY_META[newStrategy]?.description}</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label>Agents</Label>
              {agents.length === 0 ? (
                <p className="text-xs text-muted-foreground">No agents available. Create agents first.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {agents.map((agent) => {
                    const selected = newAgents.includes(agent.id);
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        onClick={() => toggleAgentSelection(agent.id)}
                        className={cn(
                          "px-2 py-1 text-xs border transition-colors",
                          selected
                            ? "border-foreground bg-foreground/10 text-foreground"
                            : "border-border text-muted-foreground hover:border-foreground/30",
                        )}
                      >
                        {agent.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="orch-concurrent">Max Concurrent</Label>
                <Input id="orch-concurrent" type="number" min={1} max={50} value={newMaxConcurrent} onChange={(e) => setNewMaxConcurrent(parseInt(e.target.value) || 5)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="orch-timeout">Timeout (s)</Label>
                <Input id="orch-timeout" type="number" min={1} max={3600} value={newTimeout} onChange={(e) => setNewTimeout(parseInt(e.target.value) || 300)} />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="orch-input">Input Template</Label>
              <Textarea id="orch-input" value={newInputTemplate} onChange={(e) => setNewInputTemplate(e.target.value)} placeholder="Template for processing input to each agent…" className="min-h-[60px] font-mono text-xs" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="orch-output">Output Aggregator</Label>
              <Input id="orch-output" value={newOutputAggregator} onChange={(e) => setNewOutputAggregator(e.target.value)} placeholder="How results are combined…" />
            </div>
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <Button ghost size="sm" onClick={() => { setCreateOpen(false); resetForm(); }}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleCreate} disabled={submitting || !newName.trim()} prefix={submitting ? <Spinner /> : <Plus />}>
              {submitting ? "Creating…" : "Create"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
