import { useCallback, useEffect, useMemo, useState } from "react";
import { Brain, Search, X, Clock, Star, Eye, BookOpen, Zap, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { AgentMemoryEntry, Agent } from "@/lib/api";

const MEMORY_TYPES = ["episodic", "semantic", "working"] as const;
type MemoryType = typeof MEMORY_TYPES[number];

const TYPE_CONFIG: Record<MemoryType, { tone: "info" | "success" | "warning"; icon: typeof BookOpen; label: string }> = {
  episodic: { tone: "info", icon: BookOpen, label: "Episodic" },
  semantic: { tone: "success", icon: Layers, label: "Semantic" },
  working: { tone: "warning", icon: Zap, label: "Working" },
};

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function truncateContent(content: string, maxLength: number = 150): string {
  return content.length > maxLength ? content.slice(0, maxLength) + "..." : content;
}

function importanceColor(score: number): string {
  if (score >= 8) return "text-destructive";
  if (score >= 5) return "text-warning";
  return "text-muted-foreground";
}

export default function AgentMemoryPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { memories, agents, fetchMemories, searchMemories, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [memoryType, setMemoryType] = useState<MemoryType>("episodic");
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState(false);

  useEffect(() => {
    setTitle("Agent Memory");
    setDescription("Browse and search agent memories");
  }, [setTitle, setDescription]);

  const loadAllAgents = useCallback(async () => {
    try {
      const { fetchAgents } = useAgentStore.getState();
      await fetchAgents();
    } catch {
      /* non-critical */
    }
  }, []);

  const loadMemories = useCallback(async (agentId?: string) => {
    setLocalLoading(true);
    setError(null);
    try {
      if (agentId) {
        await fetchMemories(agentId);
      } else {
        const state = useAgentStore.getState();
        if (state.agents.length > 0) {
          await fetchMemories(state.agents[0].id);
        }
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchMemories]);

  useEffect(() => {
    loadAllAgents();
  }, [loadAllAgents]);

  useEffect(() => {
    loadMemories(agentFilter || undefined);
  }, [loadMemories, agentFilter]);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchMode(false);
      loadMemories(agentFilter || undefined);
      return;
    }
    setSearchMode(true);
    setLocalLoading(true);
    try {
      await searchMemories(searchQuery.trim());
    } catch (err) {
      toast({ title: `Search failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setLocalLoading(false);
    }
  }, [searchQuery, searchMemories, loadMemories, agentFilter, toast]);

  const filteredMemories = useMemo(() => {
    let result = memories;
    if (!searchMode) {
      result = result.filter((m) => m.type === memoryType);
    }
    return result;
  }, [memories, memoryType, searchMode]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  if (localLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card>
          <CardContent className="py-8 px-6 text-center">
            <p className="text-destructive text-sm">{error}</p>
            <Button className="mt-4" size="sm" onClick={() => loadMemories(agentFilter || undefined)}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 pr-16 text-xs"
            placeholder="Search memories (semantic)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {searchQuery && (
              <Button ghost size="xs" onClick={() => { setSearchQuery(""); setSearchMode(false); }}>
                <X className="h-3 w-3" />
              </Button>
            )}
            <Button ghost size="xs" onClick={handleSearch}>
              <Search className="h-3 w-3" />
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Label className="text-xs">Agent</Label>
          <Select value={agentFilter} onValueChange={setAgentFilter}>
            <SelectOption value="">First agent</SelectOption>
            {agents.map((a: Agent) => (
              <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
            ))}
          </Select>
        </div>
      </div>

      {!searchMode && (
        <div className="flex gap-1 border border-border rounded p-1 w-fit">
          {MEMORY_TYPES.map((type) => {
            const config = TYPE_CONFIG[type];
            const Icon = config.icon;
            const isActive = memoryType === type;
            return (
              <button
                key={type}
                onClick={() => setMemoryType(type)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors",
                  isActive ? "bg-midground/10 text-midground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {config.label}
              </button>
            );
          })}
        </div>
      )}

      {searchMode && (
        <div className="flex items-center gap-2">
          <Badge tone="info" className="text-xs">Semantic search results</Badge>
          <span className="text-xs text-muted-foreground">{filteredMemories.length} results for "{searchQuery}"</span>
        </div>
      )}

      {filteredMemories.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {searchMode ? "No results found." : "No memories of this type."}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {filteredMemories.map((entry) => {
          const config = TYPE_CONFIG[entry.type as MemoryType] ?? TYPE_CONFIG.episodic;
          const Icon = config.icon;
          return (
            <Card key={entry.id}>
              <CardContent className="py-4 px-5">
                <div className="flex items-start gap-4">
                  <div className="rounded-lg bg-midground/10 p-2 mt-0.5">
                    <Icon className="h-4 w-4 text-midground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge tone={config.tone} className="text-[10px]">{config.label}</Badge>
                      {entry.agent_id && (
                        <Badge tone="outline" className="text-[10px]">
                          {agents.find((a: Agent) => a.id === entry.agent_id)?.name ?? entry.agent_id}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed">{truncateContent(entry.content)}</p>
                    <div className="flex items-center gap-4 mt-2 text-[10px] text-muted-foreground">
                      <span className={cn("flex items-center gap-1", importanceColor(entry.importance))}>
                        <Star className="h-3 w-3" />
                        Importance: {entry.importance.toFixed(1)}
                      </span>
                      <span className="flex items-center gap-1">
                        <Eye className="h-3 w-3" />
                        Accessed {entry.access_count} times
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Created: {formatTime(entry.created_at)}
                      </span>
                      {entry.last_accessed && (
                        <span>Last accessed: {formatTime(entry.last_accessed)}</span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
