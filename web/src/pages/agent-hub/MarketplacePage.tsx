import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ShoppingBag,
  Search,
  X,
  Star,
  Download,
  CheckCircle2,
  ArrowUpCircle,
  Package,
  Workflow,
  Zap,
  Wrench,
  Globe,
  User,
  Tag,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@aetheros/ui/ui/components/card";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Tabs, TabsList, TabsTrigger } from "@aetheros/ui/ui/components/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@aetheros/ui/ui/components/dialog";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { cn } from "@/lib/utils";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import type { MarketplaceListing } from "@/lib/api";

const TAB_OPTIONS = [
  { value: "all", label: "All" },
  { value: "agent_template", label: "Agent Templates" },
  { value: "workflow_template", label: "Workflow Templates" },
  { value: "automation_blueprint", label: "Automation Blueprints" },
  { value: "toolset", label: "Toolset" },
];

const TYPE_ICONS: Record<string, typeof Package> = {
  agent_template: Package,
  workflow_template: Workflow,
  automation_blueprint: Zap,
  toolset: Wrench,
};

const CATEGORIES = [
  "All",
  "MLOps",
  "Security",
  "Productivity",
  "Development",
  "Data",
  "Communication",
  "DevOps",
  "Research",
  "Creative",
];

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={cn("h-3 w-3", i <= Math.round(rating) ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30")}
        />
      ))}
      <span className="text-xs text-muted-foreground ml-1">({rating.toFixed(1)})</span>
    </div>
  );
}

export default function MarketplacePage() {
  const { t } = useI18n();
  const { setTitle, setDescription } = usePageHeader();
  const { marketplaces, loading, fetchMarketplace, installMarketplace } = useAgentStore();
  const { toast, showToast } = useToast();

  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("all");
  const [category, setCategory] = useState("All");
  const [detail, setDetail] = useState<MarketplaceListing | null>(null);
  const [installing, setInstalling] = useState<Set<string>>(new Set());

  useEffect(() => {
    setTitle("Marketplace");
    setDescription("Browse and install agent templates, workflows, and toolsets");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchMarketplace();
  }, [fetchMarketplace]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return marketplaces.filter((item) => {
      if (tab !== "all" && item.type !== tab) return false;
      if (category !== "All" && !item.category.toLowerCase().includes(category.toLowerCase())) return false;
      if (q && !item.name.toLowerCase().includes(q) && !item.description.toLowerCase().includes(q) && !item.author.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [marketplaces, search, tab, category]);

  const handleInstall = async (item: MarketplaceListing) => {
    setInstalling((prev) => new Set(prev).add(item.id));
    try {
      await installMarketplace(item.id);
      showToast(`"${item.name}" installed successfully`, "success");
      setDetail(null);
    } catch (err) {
      showToast(`Failed to install "${item.name}": ${err}`, "error");
    } finally {
      setInstalling((prev) => {
        const next = new Set(prev);
        next.delete(item.id);
        return next;
      });
    }
  };

  if (loading && marketplaces.length === 0) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 text-xs"
            placeholder="Search marketplace..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <Button ghost size="xs" className="absolute right-1.5 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          {TAB_OPTIONS.map((opt) => (
            <TabsTrigger key={opt.value} value={opt.value}>{opt.label}</TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="flex flex-wrap items-center gap-1.5">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setCategory(cat)}
            className={cn(
              "px-2.5 py-1 text-xs border transition-colors",
              category === cat
                ? "border-foreground/40 bg-foreground/10 text-foreground"
                : "border-border text-muted-foreground hover:border-muted-foreground/40",
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No listings match your criteria
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map((item) => {
          const TypeIcon = TYPE_ICONS[item.type] ?? Package;
          return (
            <Card key={item.id} className="rounded-none transition-colors hover:bg-muted/20 group">
              <CardContent className="p-4">
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setDetail(item)}
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-muted/20 p-2">
                      <TypeIcon className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm truncate">{item.name}</span>
                        {item.installed && (
                          <Badge tone="success" className="text-xs shrink-0">Installed</Badge>
                        )}
                        {item.has_update && (
                          <Badge tone="warning" className="text-xs shrink-0">Update available</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{item.description}</p>
                    </div>
                  </div>
                </button>

                <div className="flex flex-wrap items-center gap-1.5 mb-2">
                  <Badge tone="secondary" className="text-xs gap-1">
                    <User className="h-3 w-3" />
                    {item.author}
                  </Badge>
                  <Badge tone="outline" className="text-xs">v{item.version}</Badge>
                  <Badge tone="outline" className="text-xs gap-1">
                    <Download className="h-3 w-3" />
                    {item.downloads}
                  </Badge>
                </div>

                <StarRating rating={item.rating} />

                <div className="flex flex-wrap items-center gap-1 mt-2">
                  {item.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="text-[0.6rem] font-mono text-text-tertiary border border-border px-1 py-px">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-3 flex items-center gap-2">
                  <Button size="xs" outlined className="flex-1" onClick={() => setDetail(item)}>
                    Details
                  </Button>
                  {item.installed ? (
                    <Button size="xs" ghost disabled className="flex-1" prefix={<CheckCircle2 className="h-3 w-3" />}>
                      Installed
                    </Button>
                  ) : (
                    <Button
                      size="xs"
                      className="flex-1"
                      onClick={() => handleInstall(item)}
                      disabled={installing.has(item.id)}
                      prefix={installing.has(item.id) ? <Spinner /> : <Download className="h-3 w-3" />}
                    >
                      {installing.has(item.id) ? "Installing..." : "Install"}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {detail && (
        <Dialog open onOpenChange={(o: boolean) => !o && setDetail(null)}>
          <DialogContent className="max-w-2xl rounded-none max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-sm">
                {(() => {
                  const Icon = TYPE_ICONS[detail.type] ?? Package;
                  return <Icon className="h-4 w-4" />;
                })()}
                {detail.name}
                {detail.installed && <Badge tone="success" className="text-xs">Installed</Badge>}
                {detail.has_update && <Badge tone="warning" className="text-xs">Update available</Badge>}
              </DialogTitle>
              <DialogDescription>{detail.description}</DialogDescription>
            </DialogHeader>

            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge tone="secondary" className="text-xs gap-1">
                <User className="h-3 w-3" /> {detail.author}
              </Badge>
              <Badge tone="outline" className="text-xs">v{detail.version}</Badge>
              <Badge tone="outline" className="text-xs gap-1">
                <Download className="h-3 w-3" /> {detail.downloads} downloads
              </Badge>
              <StarRating rating={detail.rating} />
            </div>

            <div className="flex flex-wrap items-center gap-1">
              {detail.tags.map((tag) => (
                <span key={tag} className="text-[0.6rem] font-mono text-text-tertiary border border-border px-1 py-px">
                  <Tag className="h-2.5 w-2.5 inline mr-0.5" />
                  {tag}
                </span>
              ))}
            </div>

            <div className="border-t border-border pt-3 mt-1">
              <h4 className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">README</h4>
              <div className="bg-background/50 border border-border p-3 max-h-64 overflow-auto">
                <pre className="whitespace-pre-wrap text-xs font-sans leading-relaxed">
                  {detail.readme || "No documentation available."}
                </pre>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-border pt-3">
              <Button size="sm" ghost onClick={() => setDetail(null)}>Close</Button>
              {!detail.installed && (
                <Button
                  size="sm"
                  onClick={() => handleInstall(detail)}
                  disabled={installing.has(detail.id)}
                  prefix={installing.has(detail.id) ? <Spinner /> : <Download className="h-3.5 w-3.5" />}
                >
                  {installing.has(detail.id) ? "Installing..." : "Install"}
                </Button>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
