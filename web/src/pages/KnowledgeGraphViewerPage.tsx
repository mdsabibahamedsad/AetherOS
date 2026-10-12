import { useCallback, useEffect, useState } from "react";
import { Network, Search, Circle, ArrowRight, RefreshCw, BookOpen, Globe, FileText, Database, ExternalLink } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Button } from "@aetheros/ui/ui/components/button";
import { Input } from "@aetheros/ui/ui/components/input";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";

interface KnowledgeStats {
  total_entities: number;
  total_relationships: number;
  last_indexed: string | null;
  sources: string[];
}

interface SearchResult {
  source: string;
  title: string;
  content: string;
  url: string;
  relevance: number;
}

const SOURCE_ICONS: Record<string, typeof Globe> = {
  web: Globe,
  docs: BookOpen,
  github: FileText,
  knowledge: Database,
  files: FileText,
};

export default function KnowledgeGraphViewerPage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Knowledge Graph");
    setDescription("Explore the knowledge graph and semantic search");
  }, [setTitle, setDescription]);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getIntelligenceKnowledgeStats();
      setStats(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load knowledge stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await api.getIntelligenceKnowledgeSearch(query.trim(), 10);
      setResults(res.results ?? []);
    } catch (err) {
      console.error("Knowledge search failed:", err);
    } finally {
      setSearching(false);
    }
  }, [query]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  }, [handleSearch]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <Spinner />
          <span>Loading knowledge graph…</span>
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
      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Entities</span>
              <Network className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats?.total_entities.toLocaleString() ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Relationships</span>
              <ArrowRight className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats?.total_relationships.toLocaleString() ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Sources</span>
              <Database className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{stats?.sources.length ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Last Indexed</span>
              <RefreshCw className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-sm font-medium truncate">{stats?.last_indexed ?? "Never"}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search the knowledge graph…"
                className="pl-9"
              />
            </div>
            <Button onClick={handleSearch} disabled={searching || !query.trim()}>
              {searching ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
              Search
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Sources */}
      <div className="flex flex-wrap gap-2">
        {stats?.sources.map((source) => {
          const Icon = SOURCE_ICONS[source] ?? Globe;
          return (
            <Badge key={source} variant="outline" className="flex items-center gap-1.5 py-1 text-xs">
              <Icon className="h-3 w-3" />
              {source}
            </Badge>
          );
        })}
      </div>

      {/* Results */}
      {searching ? (
        <div className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <Spinner />
            <span>Searching knowledge graph…</span>
          </div>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">
            Results ({results.length})
          </div>
          {results.map((result, i) => {
            const Icon = SOURCE_ICONS[result.source] ?? Globe;
            return (
              <Card key={i} className="group hover:border-midground/30 transition-colors">
                <CardContent className="p-3">
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-midground/10 p-1.5 shrink-0">
                      <Icon className="h-3.5 w-3.5 text-midground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{result.title}</span>
                        <Badge variant="outline" className="text-[10px] shrink-0">{result.source}</Badge>
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{result.content}</p>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>Relevance: {(result.relevance * 100).toFixed(0)}%</span>
                        {result.url && (
                          <a href={result.url} target="_blank" rel="noopener noreferrer"
                            className="flex items-center gap-0.5 hover:text-midground transition-colors">
                            <ExternalLink className="h-3 w-3" />
                            Source
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : query && !searching ? (
        <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted-foreground">
          <Search className="h-8 w-8 opacity-30" />
          <span>No results found</span>
          <span className="text-xs">Try a different search query</span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 py-12 text-sm text-muted-foreground">
          <Network className="h-10 w-10 opacity-30" />
          <span>Enter a query to search the knowledge graph</span>
          <span className="text-xs">Search across web, docs, GitHub, knowledge base, and local files</span>
        </div>
      )}
    </div>
  );
}
