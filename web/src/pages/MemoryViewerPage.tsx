import { useCallback, useEffect, useState } from "react";
import { Sparkles, Brain, Database, Clock, BookOpen, Cpu, Lock, Activity, RefreshCw, Sliders } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

interface MemoryStats {
  short_term: { entries: number; capacity: number };
  long_term: { entries: number; capacity: number };
  semantic: { entries: number };
  episodic: { entries: number };
  working: { current: number; max: number };
  enabled: boolean;
  learning_enabled: boolean;
}

interface MemoryDetail {
  id: string;
  type: string;
  content: string;
  timestamp: string;
  importance: number;
}

const MEMORY_TYPES = ["short_term", "long_term", "semantic", "episodic", "working"] as const;
const MEMORY_LABELS: Record<string, string> = {
  short_term: "Short-term",
  long_term: "Long-term",
  semantic: "Semantic",
  episodic: "Episodic",
  working: "Working",
};
const MEMORY_ICONS: Record<string, typeof Brain> = {
  short_term: Brain,
  long_term: Database,
  semantic: BookOpen,
  episodic: Clock,
  working: Cpu,
};
const MEMORY_COLORS: Record<string, string> = {
  short_term: "from-blue-500/20 to-blue-500/5",
  long_term: "from-emerald-500/20 to-emerald-500/5",
  semantic: "from-purple-500/20 to-purple-500/5",
  episodic: "from-amber-500/20 to-amber-500/5",
  working: "from-rose-500/20 to-rose-500/5",
};

export default function MemoryViewerPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [entries, setEntries] = useState<MemoryDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Memory Viewer");
    setDescription("Browse and manage memory stores");
  }, [setTitle, setDescription]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getIntelligenceMemory();
      setStats(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memory data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Spinner />
          <span>Loading memory…</span>
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
      {/* Status Summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-midground" />
          <span className="text-sm text-muted-foreground">
            Memory system {stats?.enabled ? "active" : "disabled"}
            {stats?.learning_enabled ? " — Learning enabled" : " — Learning disabled"}
          </span>
        </div>
        <Button aria-label="Refresh" onClick={fetchData} variant="ghost" size="icon" className="text-muted-foreground hover:text-midground">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Memory Type Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {MEMORY_TYPES.map((type) => {
          if (!stats) return null;
          const info = stats[type];
          if (!info) return null;
          const Icon = MEMORY_ICONS[type] ?? Brain;
          const color = MEMORY_COLORS[type] ?? "from-midground/10 to-midground/5";
          const hasCapacity = "capacity" in info;
          const pct = hasCapacity ? Math.round(((info as { entries: number; capacity: number }).entries / (info as { entries: number; capacity: number }).capacity) * 100) : 0;

          return (
            <Card key={type} className="group relative overflow-hidden">
              <div className={`absolute inset-0 bg-gradient-to-br ${color} opacity-40`} />
              <CardContent className="relative p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-midground/10 p-1.5">
                      <Icon className="h-4 w-4 text-midground" />
                    </div>
                    <span className="text-sm font-medium">{MEMORY_LABELS[type] ?? type}</span>
                  </div>
                  <span className="text-lg font-bold">{info.entries}</span>
                </div>
                {hasCapacity && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>Capacity</span>
                      <span>{info.entries}/{info.capacity} ({pct}%)</span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-midground/10">
                      <div
                        className="h-full rounded-full bg-midground/40 transition-all"
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Memory Detail Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Activity className="h-4 w-4 text-midground" />
            Recent Memory Activity
          </CardTitle>
          <CardDescription>Recent memory operations and entries</CardDescription>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-sm text-muted-foreground">
              <Database className="h-8 w-8 opacity-30" />
              <span>No recent memory entries</span>
              <span className="text-xs">Memory will populate as the system learns from interactions</span>
            </div>
          ) : (
            <div className="space-y-2">
              {entries.map((entry) => (
                <div key={entry.id} className="flex items-start gap-3 rounded-lg bg-midground/5 p-2">
                  <Badge variant="outline" className="shrink-0 text-[10px]">{entry.type}</Badge>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs truncate">{entry.content}</p>
                    <p className="text-[10px] text-muted-foreground">{entry.timestamp}</p>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <Sliders className="h-3 w-3" />
                    {entry.importance.toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Memory Controls */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Lock className="h-4 w-4 text-midground" />
            Privacy & Learning Controls
          </CardTitle>
          <CardDescription>Manage how the system learns and stores information</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm">Learning Mode</div>
                <div className="text-xs text-muted-foreground">
                  {stats?.learning_enabled
                    ? "System may learn from approved interactions"
                    : "Learning is disabled — no new memories created"}
                </div>
              </div>
              <Badge variant={stats?.learning_enabled ? "default" : "secondary"}>
                {stats?.learning_enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm">Memory Persistence</div>
                <div className="text-xs text-muted-foreground">
                  {stats?.enabled ? "All memory types active" : "Memory system disabled"}
                </div>
              </div>
              <Badge variant={stats?.enabled ? "default" : "secondary"}>
                {stats?.enabled ? "Active" : "Inactive"}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
