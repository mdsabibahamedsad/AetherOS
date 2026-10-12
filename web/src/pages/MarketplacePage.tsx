import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Search,
  Star,
  Download,
  ArrowUpDown,
  Filter,
  Grid3X3,
  List,
  TrendingUp,
  Award,
  Shield,
  Users,
  Package,
  Sparkles,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Zap,
  ExternalLink,
  RotateCw,
  Clock,
  Tag,
  Check,
  Plus,
  BookOpen,
  Globe,
  Code,
  Bot,
  Workflow,
  Lock,
  Cpu,
  Mail,
  MessageSquare,
  FolderOpen,
  Wrench,
  Database,
  Cloud,
  Mic,
  Languages,
  Search as SearchIcon,
  Monitor,
  HardDrive,
  Smartphone,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Card, CardContent } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { PluginMarketEntry, MarketplaceCategory, MarketplaceSearchResponse } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, timeAgo, themedBody } from "@/lib/utils";

const CATEGORIES: { id: string; name: string; icon: typeof Package; color: string }[] = [
  { id: "ai", name: "AI", icon: Bot, color: "from-violet-500 to-purple-600" },
  { id: "coding", name: "Coding", icon: Code, color: "from-blue-500 to-cyan-600" },
  { id: "productivity", name: "Productivity", icon: Zap, color: "from-amber-500 to-orange-600" },
  { id: "automation", name: "Automation", icon: Workflow, color: "from-emerald-500 to-teal-600" },
  { id: "research", name: "Research", icon: SearchIcon, color: "from-pink-500 to-rose-600" },
  { id: "developer-tools", name: "Developer Tools", icon: Wrench, color: "from-slate-500 to-gray-600" },
  { id: "security", name: "Security", icon: Lock, color: "from-red-500 to-red-700" },
  { id: "vision", name: "Vision", icon: Monitor, color: "from-indigo-500 to-violet-600" },
  { id: "speech", name: "Speech", icon: Mic, color: "from-teal-500 to-cyan-600" },
  { id: "translation", name: "Translation", icon: Languages, color: "from-green-500 to-emerald-600" },
  { id: "database", name: "Database", icon: Database, color: "from-blue-600 to-blue-800" },
  { id: "cloud", name: "Cloud", icon: Cloud, color: "from-sky-500 to-blue-600" },
  { id: "email", name: "Email", icon: Mail, color: "from-yellow-500 to-amber-600" },
  { id: "communication", name: "Communication", icon: MessageSquare, color: "from-cyan-500 to-blue-600" },
  { id: "filesystem", name: "Filesystem", icon: FolderOpen, color: "from-stone-500 to-stone-700" },
  { id: "utilities", name: "Utilities", icon: Package, color: "from-neutral-500 to-slate-600" },
];

const SORT_OPTIONS = [
  { value: "popularity", label: "Popularity", icon: TrendingUp },
  { value: "downloads", label: "Downloads", icon: Download },
  { value: "latest", label: "Latest", icon: Clock },
  { value: "rating", label: "Rating", icon: Star },
  { value: "verified", label: "Verified", icon: Shield },
  { value: "official", label: "Official", icon: Award },
];

const ICON_MAP: Record<string, typeof Package> = {
  ai: Bot, coding: Code, productivity: Zap, automation: Workflow,
  research: SearchIcon, "developer-tools": Wrench, security: Lock,
  vision: Monitor, speech: Mic, translation: Languages,
  database: Database, cloud: Cloud, email: Mail,
  communication: MessageSquare, filesystem: FolderOpen, utilities: Package,
};

function CategoryIcon({ id, className }: { id: string; className?: string }) {
  const Icon = ICON_MAP[id] ?? Package;
  return <Icon className={cn("h-4 w-4", className)} />;
}

export default function MarketplacePage() {
  const [data, setData] = useState<MarketplaceSearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState("popularity");
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [installing, setInstalling] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd, setAfterTitle } = usePageHeader();

  const pageSize = 20;

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.searchPluginMarketplace({
        q: search || undefined,
        category: selectedCategory || undefined,
        sort: sortBy,
        page,
        page_size: pageSize,
      });
      setData(result);
    } catch (e) {
      showToast(`Failed to load marketplace: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [search, selectedCategory, sortBy, page, showToast]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Button
        ghost
        size="icon"
        className="shrink-0 text-muted-foreground hover:text-foreground"
        disabled={loading}
        onClick={() => void loadData()}
      >
        <RotateCw className={cn("h-4 w-4", loading && "animate-spin")} />
      </Button>,
    );
    return () => setAfterTitle(null);
  }, [loading, loadData, setAfterTitle]);

  const featuredPlugins = useMemo(() => data?.featured ?? [], [data]);
  const allPlugins = useMemo(() => data?.entries ?? [], [data]);
  const categories = useMemo(() => data?.categories ?? [], [data]);
  const totalPages = useMemo(() => {
    if (!data) return 1;
    return Math.ceil(data.total / data.page_size);
  }, [data]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    categories.forEach((c) => { counts[c.slug] = c.count; });
    return counts;
  }, [categories]);

  const handleInstall = async (entry: PluginMarketEntry) => {
    setInstalling(entry.id);
    try {
      const res = await api.installMarketplacePlugin(entry.id);
      showToast(`${res.name ?? entry.name} installed successfully`, "success");
      await loadData();
    } catch (e) {
      showToast(`Failed to install: ${e}`, "error");
    } finally {
      setInstalling(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Search and sort bar */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search plugins..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 border border-border rounded px-1">
            <Button
              ghost
              size="icon"
              className={cn("h-8 w-8", viewMode === "grid" && "bg-muted/30")}
              onClick={() => setViewMode("grid")}
            >
              <Grid3X3 className="h-3.5 w-3.5" />
            </Button>
            <Button
              ghost
              size="icon"
              className={cn("h-8 w-8", viewMode === "list" && "bg-muted/30")}
              onClick={() => setViewMode("list")}
            >
              <List className="h-3.5 w-3.5" />
            </Button>
          </div>
          <div className="relative">
            <select
              className={cn(
                "h-9 rounded border border-border bg-background px-3 pr-8 text-xs",
                "appearance-none cursor-pointer outline-none",
              )}
              value={sortBy}
              onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <ArrowUpDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
          </div>
        </div>
      </div>

      <div className="flex gap-6">
        {/* Category sidebar */}
        <aside className="hidden lg:flex flex-col w-56 shrink-0 gap-1">
          <button
            onClick={() => { setSelectedCategory(null); setPage(1); }}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded text-xs text-left transition-colors",
              "hover:bg-muted/30",
              !selectedCategory && "bg-muted/20 text-foreground font-medium",
            )}
          >
            <Package className="h-3.5 w-3.5" />
            <span className="flex-1">All Plugins</span>
            <span className="text-muted-foreground">{data?.total ?? 0}</span>
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => { setSelectedCategory(cat.id); setPage(1); }}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded text-xs text-left transition-colors",
                "hover:bg-muted/30",
                selectedCategory === cat.id && "bg-muted/20 text-foreground font-medium",
              )}
            >
              <CategoryIcon id={cat.id} />
              <span className="flex-1">{cat.name}</span>
              <span className="text-muted-foreground">
                {categoryCounts[cat.id] ?? 0}
              </span>
            </button>
          ))}
        </aside>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {loading && (
            <div className="flex items-center justify-center py-24">
              <Spinner className="text-2xl text-primary" />
            </div>
          )}

          {!loading && (
            <>
              {/* Featured plugins */}
              {featuredPlugins.length > 0 && page === 1 && !search && !selectedCategory && (
                <div className="mb-8">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    <h3 className="font-mondwest text-display text-xs tracking-[0.12em] text-amber-400/80 uppercase">
                      Featured Plugins
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {featuredPlugins.map((plugin) => (
                      <FeaturedPluginCard
                        key={plugin.id}
                        plugin={plugin}
                        installing={installing}
                        onInstall={handleInstall}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Plugin grid / list */}
              {allPlugins.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Package className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
                    <p className="text-sm text-muted-foreground">No plugins found</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      Try adjusting your search or filters
                    </p>
                  </CardContent>
                </Card>
              ) : viewMode === "grid" ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {allPlugins.map((plugin) => (
                    <PluginCard
                      key={plugin.id}
                      plugin={plugin}
                      installing={installing}
                      onInstall={handleInstall}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {allPlugins.map((plugin) => (
                    <PluginListItem
                      key={plugin.id}
                      plugin={plugin}
                      installing={installing}
                      onInstall={handleInstall}
                    />
                  ))}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 mt-8">
                  <Button
                    ghost
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    ghost
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function FeaturedPluginCard({
  plugin,
  installing,
  onInstall,
}: {
  plugin: PluginMarketEntry;
  installing: string | null;
  onInstall: (p: PluginMarketEntry) => void;
}) {
  const isInstalling = installing === plugin.id;
  return (
    <div
      className={cn(
        "relative group flex flex-col border border-border/40 bg-card/80 backdrop-blur-sm",
        "hover:border-border/80 transition-all duration-200 overflow-hidden",
      )}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />
      <div className="relative p-4 flex flex-col gap-3 flex-1">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-lg shrink-0 border border-border/30">
            {plugin.icon || <Package className="h-5 w-5" />}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm truncate">{plugin.name}</h4>
            <p className="text-xs text-muted-foreground truncate">by {plugin.author}</p>
          </div>
          {plugin.verified && (
            <Shield className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-1" />
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {plugin.description}
        </p>
        <div className="flex items-center gap-3 text-xs text-muted-foreground mt-auto">
          <span className="flex items-center gap-1">
            <Star className="h-3 w-3 text-amber-400" />
            {plugin.rating.toFixed(1)}
          </span>
          <span className="flex items-center gap-1">
            <Download className="h-3 w-3" />
            {plugin.downloads >= 1000 ? `${(plugin.downloads / 1000).toFixed(1)}k` : plugin.downloads}
          </span>
          <span className="flex items-center gap-1">
            <Tag className="h-3 w-3" />
            v{plugin.version}
          </span>
        </div>
        <Button
          className="w-full mt-1 uppercase"
          size="sm"
          disabled={isInstalling || plugin.installed}
          onClick={() => onInstall(plugin)}
          prefix={isInstalling ? <Spinner /> : plugin.installed ? <Check /> : <Plus />}
        >
          {isInstalling ? "Installing..." : plugin.installed ? "Installed" : "Install"}
        </Button>
      </div>
    </div>
  );
}

function PluginCard({
  plugin,
  installing,
  onInstall,
}: {
  plugin: PluginMarketEntry;
  installing: string | null;
  onInstall: (p: PluginMarketEntry) => void;
}) {
  const isInstalling = installing === plugin.id;
  const cat = CATEGORIES.find((c) => c.id === plugin.category);
  return (
    <div
      className={cn(
        "relative group flex flex-col border border-border/30 bg-card/60 backdrop-blur-sm",
        "hover:border-border/60 hover:bg-card/80 transition-all duration-200",
      )}
    >
      <div className="p-3 flex flex-col gap-2.5 flex-1">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "h-9 w-9 rounded-lg flex items-center justify-center text-base shrink-0 border border-border/20",
              cat && `bg-gradient-to-br ${cat.color} bg-opacity-20`,
            )}
          >
            {plugin.icon ? (
              <span className="text-lg">{plugin.icon}</span>
            ) : (
              <Package className="h-4 w-4 text-white/80" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <h4 className="font-medium text-xs truncate">{plugin.name}</h4>
              {plugin.official && <Award className="h-3 w-3 text-amber-400 shrink-0" />}
              {plugin.verified && <Shield className="h-3 w-3 text-emerald-400 shrink-0" />}
            </div>
            <p className="text-[11px] text-muted-foreground truncate">{plugin.author}</p>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground/80 line-clamp-2 leading-relaxed">
          {plugin.description}
        </p>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-auto">
          <span className="flex items-center gap-0.5">
            <Star className="h-2.5 w-2.5 text-amber-400" />
            {plugin.rating.toFixed(1)}
          </span>
          <span className="flex items-center gap-0.5">
            <Download className="h-2.5 w-2.5" />
            {plugin.downloads >= 1000 ? `${(plugin.downloads / 1000).toFixed(1)}k` : plugin.downloads}
          </span>
          {plugin.tags.slice(0, 2).map((tag) => (
            <Badge key={tag} tone="outline" className="text-[10px] px-1 py-0">{tag}</Badge>
          ))}
        </div>
      </div>
      <div className="px-3 pb-3">
        <Button
          className="w-full uppercase text-[11px]"
          size="sm"
          disabled={isInstalling || plugin.installed}
          onClick={() => onInstall(plugin)}
          prefix={isInstalling ? <Spinner /> : undefined}
        >
          {isInstalling ? "Installing..." : plugin.installed ? "Installed" : "Install"}
        </Button>
      </div>
    </div>
  );
}

function PluginListItem({
  plugin,
  installing,
  onInstall,
}: {
  plugin: PluginMarketEntry;
  installing: string | null;
  onInstall: (p: PluginMarketEntry) => void;
}) {
  const isInstalling = installing === plugin.id;
  return (
    <div className={cn(
      "flex items-center gap-4 px-4 py-3 border border-border/30 bg-card/40 backdrop-blur-sm",
      "hover:border-border/60 hover:bg-card/60 transition-all duration-200",
    )}>
      <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
        {plugin.icon || <Package className="h-4 w-4" />}
      </div>
      <div className="flex-1 min-w-0 flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{plugin.name}</span>
            {plugin.official && <Award className="h-3 w-3 text-amber-400 shrink-0" />}
            {plugin.verified && <Shield className="h-3 w-3 text-emerald-400 shrink-0" />}
          </div>
          <p className="text-xs text-muted-foreground truncate">{plugin.description}</p>
        </div>
        <div className="hidden md:flex items-center gap-3 text-xs text-muted-foreground shrink-0">
          <span>v{plugin.version}</span>
          <span className="flex items-center gap-1">
            <Star className="h-3 w-3 text-amber-400" />
            {plugin.rating.toFixed(1)}
          </span>
          <span>{plugin.downloads >= 1000 ? `${(plugin.downloads / 1000).toFixed(1)}k` : plugin.downloads} downloads</span>
        </div>
        <div className="shrink-0">
          {plugin.tags.slice(0, 2).map((tag) => (
            <Badge key={tag} tone="outline" className="text-[10px] mr-1">{tag}</Badge>
          ))}
        </div>
      </div>
      <Button
        className="uppercase shrink-0"
        size="sm"
        disabled={isInstalling || plugin.installed}
        onClick={() => onInstall(plugin)}
        prefix={isInstalling ? <Spinner /> : undefined}
      >
        {isInstalling ? "..." : plugin.installed ? "✓" : "Install"}
      </Button>
    </div>
  );
}
