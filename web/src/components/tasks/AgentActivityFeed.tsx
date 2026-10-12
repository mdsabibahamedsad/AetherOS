import { useMemo } from "react";
import { Activity, Zap, Bot, CheckCircle2, XCircle, Clock, AlertTriangle, Play, Pause } from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";

const EVENT_META: Record<string, { icon: any; label: string; color: string }> = {
  "orchestrator.started": { icon: Zap, label: "Orchestrator Started", color: "text-blue-500" },
  "orchestrator.stopped": { icon: XCircle, label: "Orchestrator Stopped", color: "text-gray-500" },
  "plan.execution_started": { icon: Play, label: "Plan Execution Started", color: "text-blue-500" },
  "plan.completed": { icon: CheckCircle2, label: "Plan Completed", color: "text-green-500" },
  "plan.paused": { icon: Pause, label: "Plan Paused", color: "text-yellow-500" },
  "plan.resumed": { icon: Activity, label: "Plan Resumed", color: "text-blue-500" },
  "plan.cancelled": { icon: XCircle, label: "Plan Cancelled", color: "text-gray-500" },
  "task.started": { icon: Play, label: "Task Started", color: "text-blue-500" },
  "task.completed": { icon: CheckCircle2, label: "Task Completed", color: "text-green-500" },
  "task.failed": { icon: XCircle, label: "Task Failed", color: "text-red-500" },
  "task.waiting_approval": { icon: Clock, label: "Awaiting Approval", color: "text-yellow-500" },
  "task.notification": { icon: AlertTriangle, label: "Task Notification", color: "text-orange-500" },
  "agent.assigned": { icon: Bot, label: "Agent Assigned", color: "text-purple-500" },
  "approval.requested": { icon: Clock, label: "Approval Requested", color: "text-yellow-500" },
  "approval.responded": { icon: CheckCircle2, label: "Approval Responded", color: "text-green-500" },
};

function EventIcon({ event, color }: { event: string; color: string }) {
  const meta = EVENT_META[event];
  if (meta) {
    const Icon = meta.icon;
    return <Icon className={`h-4 w-4 ${meta.color}`} />;
  }
  return <Activity className={`h-4 w-4 ${color}`} />;
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString();
}

interface ActivityEvent {
  event: string;
  data?: Record<string, unknown>;
  timestamp: number;
}

export function AgentActivityFeed({ events, limit = 100 }: { events: ActivityEvent[]; limit?: number }) {
  const display = useMemo(() => events.slice(-limit).reverse(), [events, limit]);

  if (display.length === 0) {
    return <div className="text-sm text-muted-foreground py-8 text-center">No activity yet</div>;
  }

  return (
    <div className="space-y-1">
      {display.map((evt, i) => {
        const meta = EVENT_META[evt.event];
        const label = meta?.label || evt.event;
        const detail = getEventDetail(evt);

        return (
          <div key={`${evt.timestamp}-${i}`} className="flex items-start gap-3 py-1.5 text-sm border-b border-border/50 last:border-0">
            <div className="mt-0.5 shrink-0">
              <EventIcon event={evt.event} color="text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px] px-1 py-0 font-normal">
                  {formatTime(evt.timestamp)}
                </Badge>
                <span className="font-medium text-xs">{label}</span>
              </div>
              {detail && (
                <p className="text-xs text-muted-foreground truncate mt-0.5">{detail}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function getEventDetail(evt: ActivityEvent): string {
  if (!evt.data) return "";
  const d = evt.data;
  if (d.plan_id) return `Plan: ${(d.plan_id as string).slice(0, 20)}`;
  if (d.task_id) return `Task: ${(d.task_id as string).slice(0, 20)}`;
  if (d.agent_id) return `Agent: ${(d.agent_id as string).slice(0, 20)}`;
  if (d.request_id) return `Approval: ${(d.request_id as string).slice(0, 20)}`;
  if (d.action) return `Action: ${d.action as string}`;
  if (d.message) return `Message: ${(d.message as string).slice(0, 60)}`;
  return "";
}
