import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutTemplate,
  Search,
  X,
  Bot,
  Sparkles,
  RefreshCw,
  Plus,
  Filter,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { cn } from "@/lib/utils";
import type { AgentTemplate } from "@/lib/api";

const ROLE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  assistant: Bot,
  researcher: Search,
  coder: Bot,
  writer: Bot,
  analyst: Bot,
  coordinator: Bot,
};

function getRoleIcon(role: string) {
  const lower = role.toLowerCase();
  for (const [key, icon] of Object.entries(ROLE_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return Bot;
}

const CATEGORY_COLORS: Record<string, string> = {
  productivity: "from-blue-500/20 to-blue-500/5",
  research: "from-cyan-500/20 to-cyan-500/5",
  development: "from-emerald-500/20 to-emerald-500/5",
  writing: "from-amber-500/20 to-amber-500/5",
  analysis: "from-purple-500/20 to-purple-500/5",
  automation: "from-teal-500/20 to-teal-500/5",
  communication: "from-pink-500/20 to-pink-500/5",
  security: "from-red-500/20 to-red-500/5",
  data: "from-violet-500/20 to-violet-500/5",
  default: "from-midground/10 to-midground/5",
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category.toLowerCase()] ?? CATEGORY_COLORS.default;
}

export default function AgentTemplatesPage() {
  const navigate = useNavigate();
  const { templates, fetchTemplates } = useAgentStore();
  const { toast, showToast } = useToast();
  const { setTitle } = usePageHeader();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Agent Templates");
  }, [setTitle]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchTemplates()
      .catch((err: unknown) => {
        if (!cancelled) setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [fetchTemplates]);

  const categories = useMemo(() => {
    const catSet = new Set<string>();
    templates.forEach((t) => { if (t.category) catSet.add(t.category); });
    return [...catSet].sort();
  }, [templates]);

  const filteredTemplates = useMemo(() => {
    let list = templates;
    if (search) {
      const lower = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.name.toLowerCase().includes(lower) ||
          t.description.toLowerCase().includes(lower) ||
          t.tags?.some((tag) => tag.toLowerCase().includes(lower)),
      );
    }
    if (selectedCategory) {
      list = list.filter((t) => t.category === selectedCategory);
    }
    return list;
  }, [templates, search, selectedCategory]);

  const handleCreateFromTemplate = async (template: AgentTemplate) => {
    try {
      const agent = await useAgentStore.getState().createAgent({
        name: template.name,
        description: template.description,
        role: template.role,
        tags: template.tags,
        config: template.default_config,
      });
      showToast(`Created agent from "${template.name}" template`, "success");
      navigate(`/agents/${agent.id}`);
    } catch {
      showToast("Failed to create agent from template", "error");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="text-2xl text-primary" />
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
          <CardContent>
            <Button onClick={() => { setLoading(true); setError(null); fetchTemplates().finally(() => setLoading(false)); }} prefix={<RefreshCw />}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      {/* Search + filter */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 pr-7 text-xs"
            placeholder="Search templates…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <Button
              ghost
              size="xs"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              onClick={() => setSearch("")}
            >
              <X />
            </Button>
          )}
        </div>
        <Button ghost size="xs" onClick={() => setSelectedCategory(null)} className={cn(!selectedCategory && "text-foreground")}>
          All
        </Button>
        {categories.map((cat) => (
          <Button
            key={cat}
            ghost
            size="xs"
            onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
            className={cn(selectedCategory === cat && "text-foreground")}
          >
            {cat}
          </Button>
        ))}
      </div>

      {filteredTemplates.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {search || selectedCategory
              ? "No templates match your criteria."
              : "No templates available."}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredTemplates.map((template) => {
            const Icon = getRoleIcon(template.role);
            const color = getCategoryColor(template.category);
            return (
              <Card key={template.id} className="group relative overflow-hidden rounded-none transition-all hover:border-foreground/30">
                <div className={`absolute inset-0 bg-gradient-to-br ${color} opacity-30`} />
                <CardContent className="relative p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="rounded-lg bg-midground/10 p-1.5">
                      <Icon className="h-4 w-4 text-midground" />
                    </div>
                    {template.category && (
                      <Badge tone="secondary" className="text-[10px]">{template.category}</Badge>
                    )}
                  </div>
                  <h3 className="text-sm font-medium mb-1">{template.name}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {template.description}
                  </p>
                  {template.tags && template.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {template.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="text-[10px] font-mono text-text-tertiary border border-border px-1 py-px">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
                    <span className="capitalize">{template.role}</span>
                    {template.recommended_toolsets && template.recommended_toolsets.length > 0 && (
                      <>
                        <span>·</span>
                        <span>{template.recommended_toolsets.length} toolsets</span>
                      </>
                    )}
                  </div>
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => handleCreateFromTemplate(template)}
                    prefix={<Plus />}
                  >
                    Create from template
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
