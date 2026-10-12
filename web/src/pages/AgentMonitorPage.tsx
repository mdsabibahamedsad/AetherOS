import { useCallback, useEffect, useState } from "react";
import { Bot, Activity, Circle, Clock, Shield, Code, Search, FileText, BookOpen, Globe, Zap, Cpu, ListChecks } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

interface AgentDetail {
  role: string;
  class: string;
  description: string;
  enabled: boolean;
  status: string;
}

const ROLE_ICONS: Record<string, typeof Bot> = {
  planner: ListChecks,
  researcher: Search,
  coder: Code,
  reviewer: FileText,
  debugger: Code,
  tester: Shield,
  writer: BookOpen,
  browser: Globe,
  automation: Zap,
  security: Shield,
  knowledge: BookOpen,
  voice: Zap,
  coordinator: Cpu,
};

const ROLE_COLORS: Record<string, string> = {
  planner: "from-blue-500/20 to-blue-500/5",
  researcher: "from-cyan-500/20 to-cyan-500/5",
  coder: "from-emerald-500/20 to-emerald-500/5",
  reviewer: "from-amber-500/20 to-amber-500/5",
  debugger: "from-orange-500/20 to-orange-500/5",
  tester: "from-purple-500/20 to-purple-500/5",
  writer: "from-pink-500/20 to-pink-500/5",
  browser: "from-indigo-500/20 to-indigo-500/5",
  automation: "from-teal-500/20 to-teal-500/5",
  security: "from-red-500/20 to-red-500/5",
  knowledge: "from-violet-500/20 to-violet-500/5",
  voice: "from-rose-500/20 to-rose-500/5",
  coordinator: "from-sky-500/20 to-sky-500/5",
};

export default function AgentMonitorPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const [agents, setAgents] = useState<AgentDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Agent Monitor");
    setDescription("Monitor and manage specialized AI agents");
  }, [setTitle, setDescription]);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getIntelligenceAgents();
      setAgents(res.agents ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Spinner />
          <span>Loading agents…</span>
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

  const enabledCount = agents.filter((a) => a.enabled).length;

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Total</span>
              <Bot className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{agents.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Enabled</span>
              <Activity className="h-4 w-4 text-success" />
            </div>
            <div className="mt-1 text-2xl font-bold">{enabledCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Idle</span>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{agents.filter((a) => a.status === "idle").length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Active</span>
              <Circle className="h-4 w-4 text-success" />
            </div>
            <div className="mt-1 text-2xl font-bold">{agents.filter((a) => a.status !== "idle").length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {agents.map((agent) => {
          const Icon = ROLE_ICONS[agent.role] ?? Bot;
          const color = ROLE_COLORS[agent.role] ?? "from-midground/10 to-midground/5";
          return (
            <Card key={agent.role} className="group relative overflow-hidden transition-all hover:border-midground/30">
              <div className={`absolute inset-0 bg-gradient-to-br ${color} opacity-40`} />
              <CardContent className="relative p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="rounded-lg bg-midground/10 p-1.5">
                      <Icon className="h-4 w-4 text-midground" />
                    </div>
                    <div>
                      <div className="text-sm font-medium capitalize">{agent.role}</div>
                      <div className="text-[10px] text-muted-foreground">{agent.class}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${agent.enabled ? "bg-success" : "bg-muted-foreground"}`} />
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      {agent.enabled ? (agent.status === "idle" ? "Idle" : agent.status) : "Disabled"}
                    </span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {agent.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
