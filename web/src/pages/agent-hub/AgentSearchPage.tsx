import { useCallback, useEffect, useMemo, useState } from "react";
import { Search, X, Clock, ArrowRight, Bot, FileText, Brain, Activity, ExternalLink, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";

interface SearchResult {
  category: "agent" | "task" | "memory" | "log";
  id: string;
  title: string;
  snippet: string;
  relevance: number;
  source: string;
  link?: string;
}

const CATEGORY_CONFIG: Record<string, { icon: typeof Bot; color: string }> = {
  agent: { icon: Bot, color: "text-info" },
  task: { icon: FileText, color: "text-warning" },
  memory: { icon: Brain, color: "text-success" },
  log: { icon: Activity, color: "text-muted-foreground" },
};

const MAX_RECENT_SEARCHES = 10;

function loadRecentSearches(): string[] {
  try {
    return JSON.parse(sessionStorage.getItem("agentSearchRecent") ?? "[]");
  } catch {
    return [];
  }
}

function saveRecentSearches(searches: string[]): void {
  try {
    sessionStorage.setItem("agentSearchRecent", JSON.stringify(searches.slice(0, MAX_RECENT_SEARCHES)));
  } catch { /* ignore */ }
}

export default function AgentSearchPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { agents, fetchAgents } = useAgentStore();
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [recentSearches, setRecentSearches] = useState<string[]>(loadRecentSearches);

  useEffect(() => {
    setTitle("Agent Search");
    setDescription("Search across agents, tasks, memories, and logs");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const groupedResults = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {};
    for (const r of results) {
      const list = groups[r.category] ?? [];
      list.push(r);
      groups[r.category] = list;
    }
    return groups;
  }, [results]);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setSearched(true);
    try {
      const [agentResults, taskResults, memoryResults, logResults] = await Promise.all([
        api.searchAgents(q).catch(() => ({ results: [] as SearchResult[] })),
        api.searchAgentTasks(q).catch(() => ({ results: [] as SearchResult[] })),
        api.searchAgentMemories(q).catch(() => ({ memories: [] as any[] })),
        api.searchAgentLogs(q).catch(() => ({ results: [] as SearchResult[] })),
      ]);

      const combined: SearchResult[] = [
        ...(agentResults.results ?? []).map((r: any) => ({ ...r, category: "agent" as const })),
        ...(taskResults.results ?? []).map((r: any) => ({ ...r, category: "task" as const })),
        ...(memoryResults.memories ?? []).map((m: any) => ({
          id: m.id,
          title: "Memory",
          snippet: m.content ?? "",
          relevance: m.importance ?? 0,
          source: m.agent_id ?? "",
          category: "memory" as const,
        })),
        ...(logResults.results ?? []).map((r: any) => ({ ...r, category: "log" as const })),
      ];

      setResults(combined);
      const updated = [q, ...recentSearches.filter((s) => s !== q)].slice(0, MAX_RECENT_SEARCHES);
      setRecentSearches(updated);
      saveRecentSearches(updated);
    } catch (err) {
      toast({ title: `Search failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setSearching(false);
    }
  }, [query, recentSearches, toast]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const handleRecentClick = (q: string) => {
    setQuery(q);
  };

  const clearRecent = () => {
    setRecentSearches([]);
    saveRecentSearches([]);
  };

  const clearResults = () => {
    setResults([]);
    setSearched(false);
  };

  return (
    <div className="space-y-6">
      <div className="relative max-w-2xl mx-auto">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="h-10 pl-10 pr-20 text-sm"
          placeholder="Search agents, tasks, memories, logs..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {query && (
            <Button ghost size="xs" onClick={() => { setQuery(""); clearResults(); }}>
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button size="sm" onClick={handleSearch} disabled={searching || !query.trim()} prefix={searching ? <Spinner /> : undefined}>
            Search
          </Button>
        </div>
      </div>

      {!searched && recentSearches.length > 0 && (
        <div className="max-w-2xl mx-auto w-full">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Clock className="h-3 w-3" /> Recent Searches
            </span>
            <Button ghost size="xs" onClick={clearRecent}>
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {recentSearches.map((q) => (
              <button
                key={q}
                onClick={() => handleRecentClick(q)}
                className="text-xs px-2 py-1 border border-border rounded hover:bg-muted/30 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {searching && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!searching && searched && results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No results found for "{query}".</p>
          </CardContent>
        </Card>
      )}

      {!searching && searched && results.length > 0 && (
        <div className="space-y-6">
          {(["agent", "task", "memory", "log"] as const).map((category) => {
            const items = groupedResults[category];
            if (!items || items.length === 0) return null;
            const config = CATEGORY_CONFIG[category];
            const Icon = config.icon;
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={cn("h-4 w-4", config.color)} />
                  <span className="text-sm font-medium capitalize">{category}s</span>
                  <Badge tone="secondary" className="text-xs">{items.length}</Badge>
                </div>
                <div className="space-y-1">
                  {items.map((result) => (
                    <Card key={`${result.category}-${result.id}`} className="group cursor-pointer transition-colors hover:border-midground/30">
                      <CardContent className="py-3 px-4">
                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">{result.title}</span>
                              <Badge tone="outline" className="text-[10px]">{result.category}</Badge>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{result.snippet}</p>
                            <div className="flex items-center gap-3 mt-1 text-[10px] text-muted-foreground">
                              <span>Source: {result.source || "unknown"}</span>
                              <span className={cn(result.relevance >= 0.7 ? "text-success" : result.relevance >= 0.4 ? "text-warning" : "text-muted-foreground")}>
                                Relevance: {(result.relevance * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1 shrink-0" />
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
