import { useCallback, useEffect, useState } from "react";
import { ListChecks, Brain, CheckCircle2, Circle, Clock, AlertCircle, ArrowRight, Target, Layers, RefreshCw, Plus, Zap } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Button } from "@aetheros/ui/ui/components/button";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

interface PlanStep {
  strategy: string;
  output: string;
  confidence: number;
  verified: boolean;
  duration: number;
}

interface PlanResult {
  answer: string;
  confidence: number;
  steps: PlanStep[];
  alternatives: { title: string; description: string; tradeoffs: string }[];
  total_duration: number;
}

interface Plan {
  plan_id: string;
  goal: string;
  status: string;
  steps: PlanStep[];
  progress: number;
  result?: PlanResult;
}

export default function PlanningViewPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [goalInput, setGoalInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Planning");
    setDescription("Task planning and goal decomposition");
  }, [setTitle, setDescription]);

  const fetchPlans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getIntelligencePlans();
      setPlans(res.plans ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load plans");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlans();
  }, [fetchPlans]);

  const handleCreatePlan = useCallback(async () => {
    if (!goalInput.trim()) return;
    setCreating(true);
    try {
      const res = await api.createIntelligencePlan(goalInput.trim());
      const newPlan: Plan = {
        plan_id: res.plan_id,
        goal: res.goal,
        status: "created",
        steps: res.result?.steps ?? [],
        progress: 0,
        result: res.result,
      };
      setPlans((prev) => [newPlan, ...prev]);
      setGoalInput("");
    } catch (err) {
      console.error("Failed to create plan:", err);
    } finally {
      setCreating(false);
    }
  }, [goalInput]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleCreatePlan();
  }, [handleCreatePlan]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Spinner />
          <span>Loading plans…</span>
        </div>
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
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Create Plan */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Target className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="What do you want to plan? e.g., Deploy a microservice with CI/CD…"
                className="w-full rounded-md border border-midground/20 bg-transparent py-2 pl-9 pr-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-midground/40"
              />
            </div>
            <Button onClick={handleCreatePlan} disabled={creating || !goalInput.trim()}>
              {creating ? <Spinner className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              Plan
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Plans List */}
      {plans.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted-foreground">
          <ListChecks className="h-10 w-10 opacity-30" />
          <span>No plans yet</span>
          <span className="text-xs">Create a plan by typing a goal above</span>
        </div>
      ) : (
        <div className="space-y-3">
          {plans.map((plan) => (
            <Card key={plan.plan_id} className="group hover:border-midground/30 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <ListChecks className="h-4 w-4 text-midground" />
                    <div>
                      <div className="text-sm font-medium">{plan.goal}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{plan.plan_id}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={plan.status === "completed" ? "default" : "secondary"} className="text-[10px]">
                      {plan.status}
                    </Badge>
                    {plan.result && (
                      <Badge variant="outline" className="text-[10px]">
                        {(plan.result.confidence * 100).toFixed(0)}% confidence
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Steps */}
                {plan.result?.steps && plan.result.steps.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {plan.result.steps.map((step, i) => (
                      <div key={i} className="flex items-start gap-2 rounded-lg bg-midground/5 p-2">
                        <div className="mt-0.5">
                          {step.verified ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                          ) : (
                            <Circle className="h-3.5 w-3.5 text-muted-foreground" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium capitalize">{step.strategy.replace(/_/g, " ")}</span>
                            <span className="text-[10px] text-muted-foreground">{(step.confidence * 100).toFixed(0)}%</span>
                            <span className="text-[10px] text-muted-foreground">{step.duration.toFixed(1)}s</span>
                          </div>
                          <p className="text-xs text-muted-foreground line-clamp-1">{step.output}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Alternatives */}
                {plan.result?.alternatives && plan.result.alternatives.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="text-[10px] text-muted-foreground">Alternatives:</span>
                    {plan.result.alternatives.slice(0, 3).map((alt, i) => (
                      <Badge key={i} variant="outline" className="text-[10px] flex items-center gap-1">
                        <Zap className="h-2.5 w-2.5" />
                        {alt.title}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
