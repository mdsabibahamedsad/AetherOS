import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import type { OrchestrationEvent, PlanData } from "@/store/task-store";

interface Row {
  ts: number;
  kind: string;
  label: string;
}

function eventLabel(e: OrchestrationEvent): string {
  const d = e.data ?? {};
  const pick = ["goal", "task_name", "agent_name", "tool_name", "status", "message", "error", "artifact_name"] as const;
  for (const k of pick) {
    const v = d[k];
    if (typeof v === "string" && v) return `${e.event} — ${v.slice(0, 120)}`;
  }
  return e.event;
}

/**
 * Structured execution timeline + verification/result framing.
 * Derived strictly from real plan + event records — never synthesizes progress.
 */
export function TaskTimeline({ plan, events }: { plan: PlanData; events: OrchestrationEvent[] }) {
  const rows = useMemo<Row[]>(() => {
    const list: Row[] = (plan.tasks ?? []).flatMap((t: Record<string, unknown>) => {
      const out: Row[] = [];
      if (typeof t.created_at === "number" && t.created_at)
        out.push({ ts: t.created_at, kind: "task", label: `Task queued — ${String(t.name ?? t.description ?? t.id).slice(0, 100)}` });
      if (typeof t.started_at === "number" && t.started_at)
        out.push({ ts: t.started_at, kind: "agent", label: `Started — ${String(t.agent_role ?? "agent")} · ${String(t.name ?? t.id).slice(0, 80)}` });
      if (typeof t.completed_at === "number" && t.completed_at)
        out.push({ ts: t.completed_at, kind: t.status === "failed" ? "failed" : "done", label: `${String(t.status ?? "finished")} — ${String(t.name ?? t.id).slice(0, 80)}` });
      return out;
    });
    for (const e of events ?? []) {
      if (typeof e.timestamp === "number") list.push({ ts: e.timestamp, kind: "event", label: eventLabel(e) });
    }
    if (typeof plan.created_at === "number" && plan.created_at)
      list.push({ ts: plan.created_at, kind: "task", label: `Plan created — ${String(plan.goal ?? "").slice(0, 100)}` });
    return list.sort((a, b) => a.ts - b.ts);
  }, [plan, events]);

  const verified = (plan.tasks ?? []).filter((t: Record<string, unknown>) => t.status === "completed").length;
  const total = (plan.tasks ?? []).length;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><CardTitle>Execution timeline</CardTitle></CardHeader>
        <CardContent>
          {rows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No execution events recorded yet. Events appear here as the plan runs — nothing is synthesized.
            </p>
          ) : (
            <ol className="space-y-2">
              {rows.map((r, i) => (
                <li key={`${r.ts}-${i}`} className="flex items-start gap-3 text-sm">
                  <span className="text-xs text-muted-foreground whitespace-nowrap pt-0.5">
                    {new Date(r.ts * 1000).toLocaleTimeString()}
                  </span>
                  <Badge variant={r.kind === "failed" ? "destructive" : r.kind === "done" ? "success" : "secondary"}>
                    {r.kind}
                  </Badge>
                  <span>{r.label}</span>
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Verification & result</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            Completed subtasks: <strong>{verified}/{total}</strong>. A plan is complete only
            when its success criteria verify — an agent stopping or a tool returning is not
            completion by itself.
          </p>
          <p className="text-muted-foreground">
            Status: <strong>{plan.status}</strong>
            {plan.risk_level ? <> · Risk: <strong>{plan.risk_level}</strong></> : null}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
