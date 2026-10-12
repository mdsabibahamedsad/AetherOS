import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Clock, CheckCircle2, XCircle, Ban, AlertTriangle, Search,
  ArrowUpDown, FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useTaskStore } from "@/store/task-store";

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  completed: "success", running: "warning", failed: "destructive",
  cancelled: "outline", pending: "secondary", paused: "outline",
};

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

export default function TaskHistoryPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { setTitle, setDescription } = usePageHeader();
  const { plans, loading, fetchPlans, stats } = useTaskStore();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");

  useEffect(() => {
    setTitle("Task History");
    setDescription("Completed, failed, and cancelled task plans");
    fetchPlans();
  }, []);

  const filtered = useMemo(() => {
    let list = plans.filter(p =>
      p.status === "completed" || p.status === "failed" || p.status === "cancelled"
    );
    if (statusFilter !== "all") list = list.filter(p => p.status === statusFilter);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.goal.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      const aTime = a.completed_at || a.created_at;
      const bTime = b.completed_at || b.created_at;
      return sortOrder === "newest" ? bTime - aTime : aTime - bTime;
    });
    return list;
  }, [plans, search, statusFilter, sortOrder]);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Task History</h1>
          <p className="text-muted-foreground">Review completed and failed task plans</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Total History</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold">{stats?.completed_plans + stats?.failed_plans || 0}</span></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Completed</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold text-green-600">{stats?.completed_plans || 0}</span></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Failed</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold text-red-600">{stats?.failed_plans || 0}</span></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs">Avg Duration</CardTitle></CardHeader>
          <CardContent><span className="text-2xl font-bold">{formatDuration(stats?.avg_duration || 0)}</span></CardContent>
        </Card>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Search history..."
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
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSortOrder(sortOrder === "newest" ? "oldest" : "newest")}
        >
          <ArrowUpDown className="mr-1 h-3 w-3" />
          {sortOrder === "newest" ? "Newest" : "Oldest"}
        </Button>
      </div>

      {loading && <Spinner />}

      <div className="space-y-3">
        {filtered.map(plan => (
          <Card
            key={plan.id}
            className="cursor-pointer hover:border-primary"
            onClick={() => navigate(`/tasks/${plan.id}`)}
          >
            <CardContent className="pt-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {plan.status === "completed" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                    {plan.status === "failed" && <XCircle className="h-4 w-4 text-red-500" />}
                    {plan.status === "cancelled" && <Ban className="h-4 w-4 text-gray-500" />}
                    <span className="font-medium">{plan.goal?.slice(0, 80)}</span>
                    <Badge variant={STATUS_TONES[plan.status] ?? "secondary"}>{plan.status}</Badge>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                    <span>ID: {plan.id}</span>
                    <span>{plan.tasks?.length || 0} tasks</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {formatDuration(plan.estimated_time)}
                    </span>
                    <span>Started: {formatTime(plan.started_at)}</span>
                    <span>Completed: {formatTime(plan.completed_at)}</span>
                  </div>
                  {plan.error && (
                    <div className="flex items-center gap-1 mt-1 text-xs text-red-500">
                      <AlertTriangle className="h-3 w-3" /> {plan.error}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {!loading && filtered.length === 0 && (
          <p className="text-center text-muted-foreground py-8">No history found</p>
        )}
      </div>
    </div>
  );
}
