import { useEffect, useState } from "react";
import { Zap, Activity, Clock, Bot, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useTaskStore } from "@/store/task-store";
import { AgentActivityFeed } from "@/components/tasks/AgentActivityFeed";

const EVENT_ICONS: Record<string, any> = {
  "plan.execution_started": Play,
  "plan.completed": CheckCircle2,
  "plan.paused": Pause,
  "plan.resumed": Activity,
  "plan.cancelled": XCircle,
  "task.started": Play,
  "task.completed": CheckCircle2,
  "task.failed": XCircle,
  "task.waiting_approval": Clock,
  "agent.assigned": Bot,
  "orchestrator.started": Zap,
};

function Play() { return null; }
function Pause() { return null; }

function EventIcon({ event }: { event: string }) {
  const Icon = EVENT_ICONS[event] ?? Activity;
  return <Icon className="h-4 w-4" />;
}

export default function LiveActivityPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const { events, loading, fetchEvents } = useTaskStore();
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    setTitle("Live Agent Activity");
    setDescription("Real-time agent execution monitoring");
    fetchEvents();
    const interval = setInterval(() => {
      if (!paused) fetchEvents();
    }, 2000);
    return () => clearInterval(interval);
  }, [paused]);

  const eventTypes = Array.from(new Set(events.map(e => e.event)));
  const filteredEvents = filter === "all" ? events : events.filter(e => e.event === filter);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Agent Activity</h1>
          <p className="text-muted-foreground">Real-time monitoring of agent execution</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="border rounded px-2 py-1 text-sm"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          >
            <option value="all">All Events</option>
            {eventTypes.map(et => (
              <option key={et} value={et}>{et}</option>
            ))}
          </select>
          <Badge variant={paused ? "outline" : "success"}>
            {paused ? "Paused" : "Live"}
          </Badge>
          <Button
            size="sm"
            variant={paused ? "default" : "outline"}
            onClick={() => setPaused(!paused)}
          >
            {paused ? "Resume" : "Pause"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Total Events</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold">{events.length}</span></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Task Events</CardTitle></CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{events.filter(e => e.event.startsWith("task.")).length}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Agent Events</CardTitle></CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{events.filter(e => e.event.startsWith("agent.")).length}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Unique Types</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold">{eventTypes.length}</span></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Event Stream</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && events.length === 0 ? (
            <Spinner />
          ) : (
            <AgentActivityFeed events={filteredEvents} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
