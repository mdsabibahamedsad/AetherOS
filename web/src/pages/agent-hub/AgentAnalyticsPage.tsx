import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  MessageSquare,
  Activity,
  Clock,
  Zap,
  Brain,
  Cpu,
  PieChart,
  ArrowUp,
  ArrowDown,
  Minus,
  Calendar,
  RefreshCw,
  Download,
  Bot,
  Toolbox,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Label } from "@nous-research/ui/ui/components/label";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { useAgentHubLocal, type AgentAnalyticsData } from "@/store/agent-hub-local";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/api";

const DAY_RANGES = [
  { value: 7, label: "7 days" },
  { value: 14, label: "14 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
];

const METRIC_COLORS = [
  "bg-blue-500", "bg-green-500", "bg-yellow-500", "bg-red-500",
  "bg-purple-500", "bg-pink-500", "bg-indigo-500", "bg-teal-500",
];

function formatCost(n: number): string {
  if (n >= 1) return `$${n.toFixed(2)}`;
  if (n >= 0.01) return `$${n.toFixed(4)}`;
  return `${(n * 100).toFixed(2)}¢`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function getTrend(current: number, previous: number): "up" | "down" | "stable" {
  if (previous === 0) return "stable";
  const ratio = current / previous;
  if (ratio > 1.05) return "up";
  if (ratio < 0.95) return "down";
  return "stable";
}

const TREND_ICONS = { up: ArrowUp, down: ArrowDown, stable: Minus } as const;
const TREND_COLORS = { up: "text-green-500", down: "text-red-500", stable: "text-muted-foreground" } as const;

function MiniBar({ data, height = 32 }: { data: number[]; height?: number }) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-[2px]" style={{ height }}>
      {data.map((v, i) => (
        <div key={i} className="flex-1 bg-primary/20 rounded-t" style={{ height: `${(v / max) * 100}%` }} />
      ))}
    </div>
  );
}

export default function AgentAnalyticsPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { agents, fetchAgents } = useAgentStore();
  const { getAnalytics, updateAnalytics } = useAgentHubLocal();
  const { toast, showToast } = useToast();

  const [agentId, setAgentId] = useState("");
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const analytics = useMemo(() => agentId ? getAnalytics(agentId) : null, [agentId, getAnalytics]);

  useEffect(() => {
    setTitle("Agent Analytics");
    setDescription("Detailed usage metrics and performance analytics per agent");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const refreshAnalytics = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    const sampleData: AgentAnalyticsData = {
      agentId,
      dailyStats: Array.from({ length: days }, (_, i) => ({
        date: new Date(Date.now() - (days - 1 - i) * 86400000).toISOString().slice(0, 10),
        messages: Math.floor(Math.random() * 50) + 5,
        tokenInput: Math.floor(Math.random() * 50000) + 1000,
        tokenOutput: Math.floor(Math.random() * 30000) + 500,
        cost: Math.random() * 2 + 0.1,
        toolCalls: Math.floor(Math.random() * 20) + 1,
      })),
      topTools: [
        { name: "terminal", count: Math.floor(Math.random() * 100) + 20 },
        { name: "web_search", count: Math.floor(Math.random() * 80) + 10 },
        { name: "read_file", count: Math.floor(Math.random() * 60) + 5 },
        { name: "write_file", count: Math.floor(Math.random() * 40) + 3 },
        { name: "delegate_task", count: Math.floor(Math.random() * 20) + 1 },
      ],
      topModels: [
        { name: "claude-3-5-sonnet", count: Math.floor(Math.random() * 200) + 50 },
        { name: "gpt-4o", count: Math.floor(Math.random() * 100) + 20 },
        { name: "claude-3-opus", count: Math.floor(Math.random() * 40) + 5 },
      ],
      avgResponseTime: Math.random() * 3000 + 500,
      totalSessions: Math.floor(Math.random() * 50) + 5,
      totalCost: Math.random() * 50 + 5,
    };
    await new Promise((r) => setTimeout(r, 500));
    updateAnalytics(agentId, sampleData);
    setLoading(false);
    showToast("Analytics refreshed", "success");
  }, [agentId, days, updateAnalytics, showToast]);

  const totals = useMemo(() => {
    if (!analytics) return null;
    return analytics.dailyStats.reduce(
      (acc, d) => ({
        messages: acc.messages + d.messages,
        tokenInput: acc.tokenInput + d.tokenInput,
        tokenOutput: acc.tokenOutput + d.tokenOutput,
        cost: acc.cost + d.cost,
        toolCalls: acc.toolCalls + d.toolCalls,
      }),
      { messages: 0, tokenInput: 0, tokenOutput: 0, cost: 0, toolCalls: 0 },
    );
  }, [analytics]);

  const half = Math.floor((analytics?.dailyStats.length || 0) / 2);
  const recentStats = analytics?.dailyStats.slice(half) || [];
  const olderStats = analytics?.dailyStats.slice(0, half) || [];
  const recentTotals = recentStats.reduce((a, d) => ({ messages: a.messages + d.messages, cost: a.cost + d.cost }), { messages: 0, cost: 0 });
  const olderTotals = olderStats.reduce((a, d) => ({ messages: a.messages + d.messages, cost: a.cost + d.cost }), { messages: 0, cost: 0 });

  const metricCards = useMemo(() => {
    if (!totals || !analytics) return [];
    return [
      { label: "Total Messages", value: formatNumber(totals.messages), icon: MessageSquare, color: "text-blue-500", trend: getTrend(recentTotals.messages, olderTotals.messages || 1) },
      { label: "Avg Response Time", value: `${(analytics.avgResponseTime / 1000).toFixed(1)}s`, icon: Clock, color: "text-yellow-500", trend: "stable" as const },
      { label: "Tool Calls", value: formatNumber(totals.toolCalls), icon: Toolbox, color: "text-purple-500", trend: "stable" as const },
      { label: "Sessions", value: formatNumber(analytics.totalSessions), icon: Activity, color: "text-green-500", trend: "stable" as const },
      { label: "Total Cost", value: formatCost(totals.cost), icon: DollarSign, color: "text-red-500", trend: getTrend(recentTotals.cost, olderTotals.cost || 0.01) },
    ];
  }, [totals, analytics, recentTotals, olderTotals]);

  if (!agentId) {
    return (
      <div className="flex flex-col gap-6">
        <Card><CardContent className="p-6">
          <div className="flex flex-col items-center gap-4 py-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">Select an agent to view analytics</p>
            <Select value={agentId} onValueChange={setAgentId}>
              <SelectOption value="">Choose an agent...</SelectOption>
              {agents.map((a: Agent) => <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>)}
            </Select>
          </div>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select value={agentId} onValueChange={setAgentId} className="max-w-xs">
          {agents.map((a: Agent) => <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>)}
        </Select>
        <div className="flex gap-1 border border-border rounded p-0.5">
          {DAY_RANGES.map((r) => (
            <button key={r.value} type="button" onClick={() => setDays(r.value)}
              className={cn("px-2.5 py-1 text-xs transition-colors", days === r.value ? "bg-midground/10 text-midground" : "text-muted-foreground hover:text-foreground")}
            >{r.label}</button>
          ))}
        </div>
        <Button size="sm" outlined onClick={refreshAnalytics} disabled={loading} prefix={loading ? <Spinner /> : <RefreshCw />}>
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      {!analytics || analytics.dailyStats.length === 0 ? (
        <Card><CardContent className="py-12 text-center">
          <p className="text-sm text-muted-foreground mb-3">No analytics data yet for this agent</p>
          <Button size="sm" onClick={refreshAnalytics} prefix={<RefreshCw />}>Load Analytics</Button>
        </CardContent></Card>
      ) : (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {metricCards.map(({ label, value, icon: Icon, color, trend }) => {
              const TrendIcon = TREND_ICONS[trend];
              return (
                <Card key={label}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">{label}</span>
                      <Icon className={cn("h-4 w-4", color)} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xl font-bold">{value}</span>
                      <TrendIcon className={cn("h-4 w-4", TREND_COLORS[trend])} />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Token Usage Chart */}
          <Card>
            <CardHeader className="py-3 px-4">
              <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-muted-foreground" />
                <CardTitle className="text-sm">Token Usage (Daily)</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="flex gap-6 mb-4">
                <div><span className="text-xs text-muted-foreground">Total Input</span><p className="text-lg font-bold">{formatNumber(totals?.tokenInput || 0)}</p></div>
                <div><span className="text-xs text-muted-foreground">Total Output</span><p className="text-lg font-bold">{formatNumber(totals?.tokenOutput || 0)}</p></div>
              </div>
              <div className="flex items-end gap-1 h-24">
                {analytics.dailyStats.map((d, i) => {
                  const maxTokens = Math.max(...analytics.dailyStats.map((x) => x.tokenInput + x.tokenOutput), 1);
                  const totalHeight = ((d.tokenInput + d.tokenOutput) / maxTokens) * 100;
                  const inputRatio = d.tokenInput / (d.tokenInput + d.tokenOutput || 1);
                  return (
                    <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5" title={`${d.date}: ${formatNumber(d.tokenInput)} in / ${formatNumber(d.tokenOutput)} out`}>
                      <div className="w-full rounded-t" style={{ height: `${totalHeight}%`, background: `linear-gradient(to top, rgba(59,130,246,0.3) ${inputRatio * 100}%, rgba(34,197,94,0.3) 0%)` }} />
                      {i % Math.max(1, Math.floor(analytics.dailyStats.length / 7)) === 0 && (
                        <span className="text-[8px] text-muted-foreground">{d.date.slice(5)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Top Tools & Models */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <Toolbox className="h-4 w-4 text-purple-500" />
                  <CardTitle className="text-sm">Top Tools</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {analytics.topTools.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No tool data</p>
                ) : (
                  <div className="space-y-2">
                    {analytics.topTools.map((tool, i) => {
                      const maxCount = Math.max(...analytics.topTools.map((t) => t.count), 1);
                      return (
                        <div key={tool.name} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-5">{i + 1}</span>
                          <div className="flex-1">
                            <div className="flex justify-between text-xs mb-0.5">
                              <span className="font-mono">{tool.name}</span>
                              <span className="text-muted-foreground">{tool.count}</span>
                            </div>
                            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                              <div className={cn("h-full rounded-full", METRIC_COLORS[i % METRIC_COLORS.length])} style={{ width: `${(tool.count / maxCount) * 100}%` }} />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-blue-500" />
                  <CardTitle className="text-sm">Top Models</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                {analytics.topModels.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No model data</p>
                ) : (
                  <div className="space-y-2">
                    {analytics.topModels.map((model, i) => {
                      const maxCount = Math.max(...analytics.topModels.map((m) => m.count), 1);
                      return (
                        <div key={model.name} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-5">{i + 1}</span>
                          <div className="flex-1">
                            <div className="flex justify-between text-xs mb-0.5">
                              <span className="font-mono">{model.name}</span>
                              <span className="text-muted-foreground">{model.count} calls</span>
                            </div>
                            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                              <div className={cn("h-full rounded-full", METRIC_COLORS[(i + 4) % METRIC_COLORS.length])} style={{ width: `${(model.count / maxCount) * 100}%` }} />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Cost trend */}
          <Card>
            <CardHeader className="py-3 px-4">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-red-500" />
                <CardTitle className="text-sm">Cost Trend</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="flex items-end gap-1 h-20">
                {analytics.dailyStats.map((d, i) => {
                  const maxCost = Math.max(...analytics.dailyStats.map((x) => x.cost), 0.01);
                  return (
                    <div key={d.date} className="flex-1 flex flex-col items-center gap-0.5" title={`${d.date}: ${formatCost(d.cost)}`}>
                      <div className="w-full bg-red-500/40 rounded-t" style={{ height: `${(d.cost / maxCost) * 100}%` }} />
                      {i % Math.max(1, Math.floor(analytics.dailyStats.length / 7)) === 0 && (
                        <span className="text-[8px] text-muted-foreground">{d.date.slice(5)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-3">Total: {formatCost(totals?.cost || 0)} over {days} days</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
