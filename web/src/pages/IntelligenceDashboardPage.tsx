import { useCallback, useEffect, useState } from "react";
import { Brain, Cpu, Lightbulb, Search, Network, Activity, Sparkles, BookOpen, ListChecks, ArrowRight, Bot, FileSearch } from "lucide-react";
import { Button } from "@aetheros/ui/ui/components/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Typography } from "@aetheros/ui/ui/components/typography/index";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useNavigate } from "react-router-dom";

interface IntelStatus {
  version: string;
  initialized: boolean;
  reasoning?: string;
  research?: string;
  project_understanding?: string;
  explainability?: string;
  subsystems?: Record<string, boolean>;
}

interface AgentSummary {
  role: string;
  class: string;
  description: string;
  enabled: boolean;
  status: string;
}

interface MemoryStats {
  short_term: { entries: number; capacity: number };
  long_term: { entries: number; capacity: number };
  semantic: { entries: number };
  episodic: { entries: number };
  working: { current: number; max: number };
  enabled: boolean;
  learning_enabled: boolean;
}

interface KnowledgeStats {
  total_entities: number;
  total_relationships: number;
  last_indexed: string | null;
  sources: string[];
}

export default function IntelligenceDashboardPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { setTitle, setDescription } = usePageHeader();
  const [status, setStatus] = useState<IntelStatus | null>(null);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [memory, setMemory] = useState<MemoryStats | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Intelligence");
    setDescription("AetherOS Intelligence Engine Dashboard");
  }, [setTitle, setDescription]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, agentsRes, memoryRes, knowledgeRes] = await Promise.all([
        api.getIntelligenceStatus(),
        api.getIntelligenceAgents(),
        api.getIntelligenceMemory(),
        api.getIntelligenceKnowledgeStats(),
      ]);
      setStatus(statusRes);
      setAgents(agentsRes.agents ?? []);
      setMemory(memoryRes);
      setKnowledge(knowledgeRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load intelligence data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const quickActions = [
    { title: "Plan", description: "Create a new plan from a goal", icon: ListChecks, path: "/planning", color: "from-blue-500/20 to-blue-500/5" },
    { title: "Think", description: "Reason about a problem", icon: Brain, path: "/think", color: "from-purple-500/20 to-purple-500/5" },
    { title: "Research", description: "Multi-source research", icon: Search, path: "/research", color: "from-cyan-500/20 to-cyan-500/5" },
    { title: "Analyze", description: "Analyze a project", icon: FileSearch, path: "/analyze", color: "from-amber-500/20 to-amber-500/5" },
    { title: "Agents", description: "Monitor AI agents", icon: Bot, path: "/agent-monitor", color: "from-emerald-500/20 to-emerald-500/5" },
    { title: "Knowledge", description: "Query knowledge graph", icon: Network, path: "/knowledge-graph", color: "from-rose-500/20 to-rose-500/5" },
  ];

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Spinner />
          <span>Loading intelligence engine…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <Activity className="h-5 w-5" />
              Connection Error
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={fetchData} variant="outline" className="w-full">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const subsystemEntries = status?.subsystems
    ? Object.entries(status.subsystems)
    : [];

  return (
    <div className="space-y-6">
      {/* Engine Status Bar */}
      <Card className="border-midground/10">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-midground" />
              <span className="text-muted-foreground">Intelligence Engine</span>
              <span className="font-medium">{status?.version ?? "—"}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${status?.initialized ? "bg-success" : "bg-warning"}`} />
              <span className="text-muted-foreground">{status?.initialized ? "Online" : "Initializing"}</span>
            </div>
            {subsystemEntries.map(([name, active]) => (
              <div key={name} className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-success" : "bg-muted-foreground"}`} />
                <span className="text-xs text-muted-foreground capitalize">{name.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions Grid */}
      <div>
        <Typography variant="h4" className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Quick Actions
        </Typography>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {quickActions.map((action) => (
            <button
              key={action.path}
              onClick={() => navigate(action.path)}
              className="group relative overflow-hidden rounded-lg border border-midground/10 p-4 text-left transition-all duration-200 hover:border-midground/30 hover:bg-midground/5"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${action.color} opacity-50 transition-opacity group-hover:opacity-100`} />
              <div className="relative z-10">
                <div className="mb-2 flex items-center gap-2">
                  <action.icon className="h-4 w-4 text-midground" />
                  <span className="text-sm font-medium">{action.title}</span>
                </div>
                <p className="text-xs text-muted-foreground">{action.description}</p>
              </div>
              <ArrowRight className="absolute right-3 top-3 h-3.5 w-3.5 text-midground/30 transition-transform group-hover:translate-x-0.5" />
            </button>
          ))}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Agents */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Bot className="h-4 w-4 text-midground" />
              Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agents.length}</div>
            <p className="text-xs text-muted-foreground">
              {agents.filter((a) => a.enabled).length} enabled
            </p>
            <div className="mt-2 flex flex-wrap gap-1">
              {agents.slice(0, 6).map((a) => (
                <span key={a.role} className="inline-flex items-center rounded-full bg-midground/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-midground/70">
                  {a.role}
                </span>
              ))}
              {agents.length > 6 && (
                <span className="inline-flex items-center rounded-full bg-midground/10 px-2 py-0.5 text-[10px] text-muted-foreground">
                  +{agents.length - 6}
                </span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Memory */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Sparkles className="h-4 w-4 text-midground" />
              Memory
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {memory && (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Short-term</span>
                    <span className="font-medium">{memory.short_term.entries}/{memory.short_term.capacity}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Long-term</span>
                    <span className="font-medium">{memory.long_term.entries}/{memory.long_term.capacity}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Learning</span>
                    <span className={`font-medium ${memory.learning_enabled ? "text-success" : "text-muted-foreground"}`}>
                      {memory.learning_enabled ? "Active" : "Off"}
                    </span>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Knowledge Graph */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Network className="h-4 w-4 text-midground" />
              Knowledge Graph
            </CardTitle>
          </CardHeader>
          <CardContent>
            {knowledge ? (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Entities</span>
                  <span className="font-medium">{knowledge.total_entities.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Relationships</span>
                  <span className="font-medium">{knowledge.total_relationships.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Sources</span>
                  <span className="font-medium">{knowledge.sources.length}</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner className="h-3 w-3" />
                Loading…
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Subsystem Status */}
      {subsystemEntries.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Cpu className="h-4 w-4 text-midground" />
              Subsystems
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {subsystemEntries.map(([name, active]) => (
                <div key={name} className="flex items-center gap-2 rounded-lg bg-midground/5 p-2">
                  <span className={`h-2 w-2 rounded-full ${active ? "bg-success" : "bg-warning"}`} />
                  <span className="text-xs capitalize">{name.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
