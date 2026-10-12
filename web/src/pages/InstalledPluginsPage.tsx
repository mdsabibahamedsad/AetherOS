import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Package,
  Search,
  Settings,
  Power,
  Trash2,
  Download,
  RefreshCw,
  ExternalLink,
  FileText,
  Shield,
  Check,
  X,
  AlertTriangle,
  ArrowUp,
  MoreHorizontal,
  FolderOpen,
  Book,
  Code,
  Bot,
  Workflow,
  Globe,
  Cpu,
  Mail,
  MessageSquare,
  Lock,
  Database,
  Cloud,
  Mic,
  Monitor,
  Wrench,
  Zap,
  Languages,
  Smartphone,
  HardDrive,
  Search as SearchIcon,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Select, SelectOption } from "@aetheros/ui/ui/components/select";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Card, CardContent } from "@aetheros/ui/ui/components/card";
import { ConfirmDialog } from "@aetheros/ui/ui/components/confirm-dialog";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { PluginMarketEntry } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";

const CATEGORY_ICONS: Record<string, typeof Package> = {
  ai: Bot, coding: Code, productivity: Zap, automation: Workflow,
  research: SearchIcon, "developer-tools": Wrench, security: Lock,
  vision: Monitor, speech: Mic, translation: Languages,
  database: Database, cloud: Cloud, email: Mail,
  communication: MessageSquare, filesystem: FolderOpen, utilities: Package,
};

export default function InstalledPluginsPage() {
  const navigate = useNavigate();
  const [plugins, setPlugins] = useState<PluginMarketEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [toggling, setToggling] = useState<string | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [confirmRemove, setConfirmRemove] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setAfterTitle } = usePageHeader();

  const loadPlugins = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getInstalledPlugins();
      setPlugins(res.plugins);
    } catch (e) {
      showToast(`Failed to load plugins: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadPlugins(); }, [loadPlugins]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Button
        ghost
        size="icon"
        className="shrink-0 text-muted-foreground hover:text-foreground"
        disabled={loading}
        onClick={() => void loadPlugins()}
      >
        <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
      </Button>,
    );
    return () => setAfterTitle(null);
  }, [loading, loadPlugins, setAfterTitle]);

  const handleToggle = async (plugin: PluginMarketEntry) => {
    const next = !plugin.enabled;
    setToggling(plugin.id);
    try {
      await api.setPluginEnabled(plugin.id, next);
      setPlugins((prev) =>
        prev.map((p) => (p.id === plugin.id ? { ...p, enabled: next } : p)),
      );
      showToast(next ? "Plugin enabled" : "Plugin disabled", "success");
    } catch (e) {
      showToast(`Failed: ${e}`, "error");
    } finally {
      setToggling(null);
    }
  };

  const handleRemove = async (id: string) => {
    setRemoving(id);
    try {
      await api.removeMarketplacePlugin(id);
      setPlugins((prev) => prev.filter((p) => p.id !== id));
      showToast("Plugin removed", "success");
    } catch (e) {
      showToast(`Failed to remove: ${e}`, "error");
    } finally {
      setRemoving(null);
      setConfirmRemove(null);
    }
  };

  const handleOpenDetail = (plugin: PluginMarketEntry) => {
    navigate(`/marketplace/${encodeURIComponent(plugin.id)}`);
  };

  const filteredPlugins = useMemo(() => {
    let list = plugins;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.author.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q)),
      );
    }
    if (statusFilter === "enabled") list = list.filter((p) => p.enabled);
    else if (statusFilter === "disabled") list = list.filter((p) => !p.enabled);
    else if (statusFilter === "updates") list = list.filter((p) => p.has_update);
    return list;
  }, [plugins, search, statusFilter]);

  const groupedPlugins = useMemo(() => {
    const groups: Record<string, PluginMarketEntry[]> = {};
    filteredPlugins.forEach((p) => {
      const cat = p.category || "uncategorized";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    });
    return groups;
  }, [filteredPlugins]);

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search installed plugins..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectOption value="all">All</SelectOption>
          <SelectOption value="enabled">Enabled</SelectOption>
          <SelectOption value="disabled">Disabled</SelectOption>
          <SelectOption value="updates">Updates Available</SelectOption>
        </Select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : filteredPlugins.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Package className="h-8 w-8 mx-auto mb-3 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">No installed plugins found</p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          {Object.entries(groupedPlugins).map(([category, catPlugins]) => (
            <div key={category} className="flex flex-col gap-2">
              <h3 className="font-mondwest text-display text-xs tracking-[0.12em] text-muted-foreground uppercase flex items-center gap-2">
                {ReactCategoryIcon(category)}
                {category} ({catPlugins.length})
              </h3>
              {catPlugins.map((plugin) => (
                <InstalledPluginRow
                  key={plugin.id}
                  plugin={plugin}
                  toggling={toggling}
                  removing={removing}
                  onToggle={handleToggle}
                  onRemove={() => setConfirmRemove(plugin.id)}
                  onDetail={() => handleOpenDetail(plugin)}
                />
              ))}
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!confirmRemove}
        onCancel={() => setConfirmRemove(null)}
        onConfirm={() => confirmRemove && handleRemove(confirmRemove)}
        title="Remove Plugin"
        description="This will uninstall the plugin. Are you sure?"
        destructive
        confirmLabel="Remove"
      />
    </div>
  );
}

function ReactCategoryIcon(category: string) {
  const Icon = CATEGORY_ICONS[category] ?? Package;
  return <Icon className="h-3 w-3" />;
}

function InstalledPluginRow({
  plugin,
  toggling,
  removing,
  onToggle,
  onRemove,
  onDetail,
}: {
  plugin: PluginMarketEntry;
  toggling: string | null;
  removing: string | null;
  onToggle: (p: PluginMarketEntry) => void;
  onRemove: () => void;
  onDetail: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isBusy = toggling === plugin.id || removing === plugin.id;

  return (
    <Card className={cn(isBusy && "opacity-70")}>
      <CardContent className="flex items-center gap-4 py-3 px-4">
        <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-sm shrink-0 border border-border/20">
          {plugin.icon || <Package className="h-4 w-4" />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <button onClick={onDetail} className="font-medium text-sm truncate hover:text-foreground/80 transition-colors">
              {plugin.name}
            </button>
            {plugin.has_update && (
              <Badge tone="warning" className="text-[10px] flex items-center gap-0.5">
                <ArrowUp className="h-2.5 w-2.5" />
                Update
              </Badge>
            )}
            {!plugin.enabled && (
              <Badge tone="outline" className="text-[10px]">Disabled</Badge>
            )}
            {plugin.official && <Badge tone="secondary" className="text-[10px]">Official</Badge>}
          </div>
          <p className="text-xs text-muted-foreground truncate">{plugin.description}</p>
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-0.5">
            <span>v{plugin.installed_version || plugin.version}</span>
            <span>by {plugin.author}</span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <Switch
            checked={plugin.enabled}
            onCheckedChange={() => onToggle(plugin)}
            disabled={isBusy}
          />

          <div className="relative">
            <Button
              ghost
              size="icon"
              className="h-8 w-8"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 z-50 min-w-[160px] border border-border/40 bg-card/95 backdrop-blur-sm shadow-xl py-1">
                  <button
                    onClick={() => { setMenuOpen(false); onDetail(); }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-muted/20 text-left"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Details
                  </button>
                  <button
                    onClick={() => { setMenuOpen(false); /* navigate to config */ }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-muted/20 text-left"
                  >
                    <Settings className="h-3 w-3" />
                    Configure
                  </button>
                  <button
                    onClick={() => { setMenuOpen(false); /* navigate to permissions */ }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-muted/20 text-left"
                  >
                    <Shield className="h-3 w-3" />
                    Permissions
                  </button>
                  <button
                    onClick={() => { setMenuOpen(false); /* navigate to docs */ }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-muted/20 text-left"
                  >
                    <Book className="h-3 w-3" />
                    Documentation
                  </button>
                  <div className="border-t border-border/20 my-1" />
                  <button
                    onClick={() => { setMenuOpen(false); onRemove(); }}
                    className="flex items-center gap-2 w-full px-3 py-2 text-xs hover:bg-destructive/10 text-destructive text-left"
                  >
                    <Trash2 className="h-3 w-3" />
                    Uninstall
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
