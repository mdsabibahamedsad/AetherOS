import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Zap,
  Plus,
  Search,
  X,
  Clock,
  Webhook,
  FileText,
  Activity,
  BarChart3,
  Bot,
  Bell,
  Workflow,
  Globe,
  Settings,
  MessageSquare,
  RefreshCw,
  ToggleLeft,
  Variable,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
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
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import type { AutomationBlueprint2, AutomationTrigger, AutomationCondition, AutomationAction } from "@/lib/api";

const TRIGGER_LABELS: Record<string, string> = {
  schedule: "Schedule",
  event: "Event",
  webhook: "Webhook",
  file_change: "File Change",
  agent_status: "Agent Status",
  metric_threshold: "Metric Threshold",
};

const TRIGGER_ICONS: Record<string, typeof Clock> = {
  schedule: Clock,
  event: Zap,
  webhook: Webhook,
  file_change: FileText,
  agent_status: Activity,
  metric_threshold: BarChart3,
};

const ACTION_LABELS: Record<string, string> = {
  run_agent: "Run Agent",
  send_notification: "Send Notification",
  execute_workflow: "Execute Workflow",
  call_webhook: "Call Webhook",
  update_config: "Update Config",
  log_message: "Log Message",
};

const ACTION_ICONS: Record<string, typeof Bot> = {
  run_agent: Bot,
  send_notification: Bell,
  execute_workflow: Workflow,
  call_webhook: Globe,
  update_config: Settings,
  log_message: MessageSquare,
};

const OPERATORS = [
  { value: "eq", label: "Equals" },
  { value: "neq", label: "Not equals" },
  { value: "gt", label: "Greater than" },
  { value: "gte", label: "Greater or equal" },
  { value: "lt", label: "Less than" },
  { value: "lte", label: "Less or equal" },
  { value: "contains", label: "Contains" },
  { value: "matches", label: "Matches" },
  { value: "exists", label: "Exists" },
];

export default function AutomationBuilderPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const { automations, loading, fetchAutomations, createAutomation } = useAgentStore();
  const { toast, showToast } = useToast();

  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editAutomation, setEditAutomation] = useState<AutomationBlueprint2 | null>(null);

  const [newName, setNewName] = useState("");
  const [newTrigger, setNewTrigger] = useState<AutomationTrigger["type"]>("schedule");
  const [newConditions, setNewConditions] = useState<AutomationCondition[]>([]);
  const [newActions, setNewActions] = useState<AutomationAction[]>([]);
  const [newRetryMax, setNewRetryMax] = useState(3);
  const [newRetryDelay, setNewRetryDelay] = useState(60);
  const [newBackground, setNewBackground] = useState(false);
  const [newVariables, setNewVariables] = useState<Record<string, string>>({});
  const [newVarKey, setNewVarKey] = useState("");
  const [newVarValue, setNewVarValue] = useState("");

  const [conditionField, setConditionField] = useState("");
  const [conditionOp, setConditionOp] = useState<AutomationCondition["operator"]>("eq");
  const [conditionVal, setConditionVal] = useState("");
  const [actionType, setActionType] = useState<AutomationAction["type"]>("run_agent");
  const [actionTimeout, setActionTimeout] = useState(30);

  useEffect(() => {
    setTitle("Automation Builder");
    setDescription("Create visual workflow automations with triggers, conditions, and actions");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchAutomations();
  }, [fetchAutomations]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return automations.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        a.description.toLowerCase().includes(q) ||
        a.trigger.type.toLowerCase().includes(q),
    );
  }, [automations, search]);

  const addCondition = () => {
    if (!conditionField) return;
    setNewConditions([
      ...newConditions,
      { field: conditionField, operator: conditionOp, value: conditionVal },
    ]);
    setConditionField("");
    setConditionVal("");
  };

  const removeCondition = (idx: number) => {
    setNewConditions(newConditions.filter((_, i) => i !== idx));
  };

  const addAction = () => {
    setNewActions([
      ...newActions,
      { type: actionType, config: {}, timeout: actionTimeout },
    ]);
    setActionTimeout(30);
  };

  const removeAction = (idx: number) => {
    setNewActions(newActions.filter((_, i) => i !== idx));
  };

  const addVariable = () => {
    if (!newVarKey) return;
    setNewVariables({ ...newVariables, [newVarKey]: newVarValue });
    setNewVarKey("");
    setNewVarValue("");
  };

  const removeVariable = (key: string) => {
    const next = { ...newVariables };
    delete next[key];
    setNewVariables(next);
  };

  const resetForm = () => {
    setNewName("");
    setNewTrigger("schedule");
    setNewConditions([]);
    setNewActions([]);
    setNewRetryMax(3);
    setNewRetryDelay(60);
    setNewBackground(false);
    setNewVariables({});
    setConditionField("");
    setConditionOp("eq");
    setConditionVal("");
    setActionType("run_agent");
    setActionTimeout(30);
    setNewVarKey("");
    setNewVarValue("");
  };

  const handleCreate = async () => {
    if (!newName.trim()) {
      showToast("Name is required", "error");
      return;
    }
    if (newActions.length === 0) {
      showToast("At least one action is required", "error");
      return;
    }
    setCreating(true);
    try {
      await createAutomation({
        name: newName.trim(),
        description: "",
        trigger: { type: newTrigger, config: {} },
        conditions: newConditions,
        actions: newActions,
        variables: newVariables,
        background: newBackground,
        retry_policy: { max_retries: newRetryMax, delay_seconds: newRetryDelay },
        enabled: true,
        category: "user",
        tags: [],
      });
      showToast(`Automation "${newName}" created`, "success");
      setCreateOpen(false);
      resetForm();
    } catch (err) {
      showToast(`Failed to create: ${err}`, "error");
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (auto: AutomationBlueprint2) => {
    try {
      await createAutomation({
        ...auto,
        enabled: !auto.enabled,
      });
      fetchAutomations();
      showToast(`${auto.name} ${auto.enabled ? "disabled" : "enabled"}`, "success");
    } catch {
      showToast(`Failed to toggle ${auto.name}`, "error");
    }
  };

  if (loading && automations.length === 0) {
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
          <Input
            className="h-8 pl-8 text-xs"
            placeholder="Search automations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <Button
              ghost
              size="xs"
              className="absolute right-1.5 top-1/2 -translate-y-1/2"
              onClick={() => setSearch("")}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
        <Button size="sm" onClick={() => { resetForm(); setCreateOpen(true); }} prefix={<Plus className="h-3.5 w-3.5" />}>
          New Automation
        </Button>
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            {search ? "No automations match your search" : "No automations yet. Create your first one."}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-2">
        {filtered.map((auto) => {
          const TriggerIcon = TRIGGER_ICONS[auto.trigger.type] ?? Clock;
          return (
            <Card key={auto.id} className="rounded-none transition-colors hover:bg-muted/20">
              <CardContent className="flex items-start gap-4 py-3">
                <div className="flex items-center gap-2 pt-0.5">
                  <Switch
                    checked={auto.enabled}
                    onCheckedChange={() => handleToggle(auto)}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-sm">{auto.name}</span>
                    <Badge tone={auto.enabled ? "success" : "outline"} className="text-xs">
                      {auto.enabled ? "Active" : "Disabled"}
                    </Badge>
                    <Badge tone="secondary" className="text-xs gap-1">
                      <TriggerIcon className="h-3 w-3" />
                      {TRIGGER_LABELS[auto.trigger.type] ?? auto.trigger.type}
                    </Badge>
                  </div>
                  {auto.description && (
                    <p className="text-xs text-muted-foreground mb-1">{auto.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{auto.conditions.length} condition{auto.conditions.length !== 1 ? "s" : ""}</span>
                    <span>{auto.actions.length} action{auto.actions.length !== 1 ? "s" : ""}</span>
                    {auto.background && <Badge tone="warning" className="text-xs">Background</Badge>}
                    <span>Retry: {auto.retry_policy.max_retries}x</span>
                  </div>
                </div>
                <Button aria-label="Settings" ghost size="icon" className="text-muted-foreground" onClick={() => setEditAutomation(auto)}>
                  <Settings className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={createOpen} onOpenChange={(o: boolean) => !o && setCreateOpen(false)}>
        <DialogContent className="max-w-2xl rounded-none max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm">
              <Zap className="h-4 w-4" />
              New Automation Blueprint
            </DialogTitle>
            <DialogDescription>Define triggers, conditions, and actions for your automation.</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="auto-name">Name</Label>
              <Input id="auto-name" placeholder="My automation" value={newName} onChange={(e) => setNewName(e.target.value)} />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="auto-trigger">Trigger</Label>
              <Select id="auto-trigger" value={newTrigger} onValueChange={(v) => setNewTrigger(v as AutomationTrigger["type"])}>
                {Object.entries(TRIGGER_LABELS).map(([val, label]) => (
                  <SelectOption key={val} value={val}>{label}</SelectOption>
                ))}
              </Select>
            </div>

            <div className="grid gap-2 border border-border p-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-mono uppercase tracking-wider">Conditions</Label>
              </div>
              {newConditions.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-xs bg-muted/20 px-2 py-1">
                  <span className="font-mono">{c.field}</span>
                  <span className="text-muted-foreground">{c.operator}</span>
                  <span className="font-mono">{String(c.value)}</span>
                  <Button ghost size="xs" className="ml-auto text-destructive" onClick={() => removeCondition(i)}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <Label className="text-xs">Field</Label>
                  <Input className="h-7 text-xs" value={conditionField} onChange={(e) => setConditionField(e.target.value)} placeholder="e.g. status" />
                </div>
                <div className="w-24">
                  <Label className="text-xs">Op</Label>
                  <Select value={conditionOp} onValueChange={(v) => setConditionOp(v as AutomationCondition["operator"])}>
                    {OPERATORS.map((o) => (
                      <SelectOption key={o.value} value={o.value}>{o.label}</SelectOption>
                    ))}
                  </Select>
                </div>
                <div className="flex-1">
                  <Label className="text-xs">Value</Label>
                  <Input className="h-7 text-xs" value={conditionVal} onChange={(e) => setConditionVal(e.target.value)} placeholder="value" />
                </div>
                <Button size="xs" onClick={addCondition} disabled={!conditionField}>Add</Button>
              </div>
            </div>

            <div className="grid gap-2 border border-border p-3">
              <Label className="text-xs font-mono uppercase tracking-wider">Actions</Label>
              {newActions.map((a, i) => {
                const ActionIcon = ACTION_ICONS[a.type] ?? Bot;
                return (
                  <div key={i} className="flex items-center gap-2 text-xs bg-muted/20 px-2 py-1">
                    <ActionIcon className="h-3 w-3" />
                    <span>{ACTION_LABELS[a.type] ?? a.type}</span>
                    <span className="text-muted-foreground">({a.timeout}s)</span>
                    <Button ghost size="xs" className="ml-auto text-destructive" onClick={() => removeAction(i)}>
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                );
              })}
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <Label className="text-xs">Type</Label>
                  <Select value={actionType} onValueChange={(v) => setActionType(v as AutomationAction["type"])}>
                    {Object.entries(ACTION_LABELS).map(([val, label]) => (
                      <SelectOption key={val} value={val}>{label}</SelectOption>
                    ))}
                  </Select>
                </div>
                <div className="w-20">
                  <Label className="text-xs">Timeout (s)</Label>
                  <Input type="number" className="h-7 text-xs" value={actionTimeout} onChange={(e) => setActionTimeout(Number(e.target.value))} />
                </div>
                <Button size="xs" onClick={addAction}>Add</Button>
              </div>
            </div>

            <div className="grid gap-2">
              <Label>Retry Policy</Label>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <Label className="text-xs">Max retries</Label>
                  <Input type="number" className="h-7 text-xs" value={newRetryMax} onChange={(e) => setNewRetryMax(Number(e.target.value))} />
                </div>
                <div className="flex-1">
                  <Label className="text-xs">Delay (seconds)</Label>
                  <Input type="number" className="h-7 text-xs" value={newRetryDelay} onChange={(e) => setNewRetryDelay(Number(e.target.value))} />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch checked={newBackground} onCheckedChange={setNewBackground} />
              <Label className="text-xs">Background execution</Label>
            </div>

            <div className="grid gap-2 border border-border p-3">
              <Label className="text-xs font-mono uppercase tracking-wider flex items-center gap-1">
                <Variable className="h-3 w-3" /> Variables
              </Label>
              {Object.entries(newVariables).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 text-xs bg-muted/20 px-2 py-1">
                  <span className="font-mono text-primary">{k}</span>
                  <span className="text-muted-foreground">=</span>
                  <span className="font-mono">{v}</span>
                  <Button ghost size="xs" className="ml-auto text-destructive" onClick={() => removeVariable(k)}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              <div className="flex items-end gap-2">
                <div className="flex-1">
                  <Label className="text-xs">Key</Label>
                  <Input className="h-7 text-xs" value={newVarKey} onChange={(e) => setNewVarKey(e.target.value)} placeholder="var_name" />
                </div>
                <div className="flex-1">
                  <Label className="text-xs">Value</Label>
                  <Input className="h-7 text-xs" value={newVarValue} onChange={(e) => setNewVarValue(e.target.value)} placeholder="value" />
                </div>
                <Button size="xs" onClick={addVariable} disabled={!newVarKey}>Add</Button>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 border-t border-border pt-3">
            <Button ghost size="sm" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating || !newName.trim()} prefix={creating ? <Spinner /> : undefined}>
              {creating ? "Creating..." : "Create Automation"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {editAutomation && (
        <Dialog open onOpenChange={(o: boolean) => !o && setEditAutomation(null)}>
          <DialogContent className="max-w-lg rounded-none">
            <DialogHeader>
              <DialogTitle className="text-sm flex items-center gap-2">
                <Settings className="h-4 w-4" />
                {editAutomation.name}
              </DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div className="grid gap-1">
                <Label className="text-xs">Trigger</Label>
                <Badge tone="secondary" className="text-xs w-fit">{TRIGGER_LABELS[editAutomation.trigger.type]}</Badge>
              </div>
              <div className="grid gap-1">
                <Label className="text-xs">Conditions ({editAutomation.conditions.length})</Label>
                <pre className="text-xs bg-muted/20 p-2 font-mono overflow-auto max-h-24">
                  {JSON.stringify(editAutomation.conditions, null, 2)}
                </pre>
              </div>
              <div className="grid gap-1">
                <Label className="text-xs">Actions ({editAutomation.actions.length})</Label>
                <pre className="text-xs bg-muted/20 p-2 font-mono overflow-auto max-h-24">
                  {JSON.stringify(editAutomation.actions, null, 2)}
                </pre>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>Retry: {editAutomation.retry_policy.max_retries}x / {editAutomation.retry_policy.delay_seconds}s</span>
                {editAutomation.background && <Badge tone="warning">Background</Badge>}
              </div>
            </div>
            <div className="flex justify-end pt-3 border-t border-border">
              <Button size="sm" ghost onClick={() => setEditAutomation(null)}>Close</Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
