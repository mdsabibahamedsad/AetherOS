import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Search,
  X,
  Pause,
  Play,
  RotateCcw,
  Copy,
  GitBranch,
  Trash2,
  Plus,
  RefreshCw,
  Star,
  Download,
  Upload,
  CheckCircle2,
  FileJson,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@nous-research/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { useAgentHubLocal } from "@/store/agent-hub-local";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/api";

const STATUS_TONES: Record<string, "success" | "warning" | "destructive" | "secondary" | "outline"> = {
  running: "success",
  idle: "secondary",
  paused: "warning",
  error: "destructive",
  restarting: "warning",
  stopped: "outline",
};

function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function AgentListPage() {
  const navigate = useNavigate();
  const { agents, loading, error, fetchAgents, pauseAgent, resumeAgent, restartAgent, duplicateAgent, cloneAgent, deleteAgent } = useAgentStore();
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  const [search, setSearch] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importing, setImporting] = useState(false);
  const { toggleFavorite, isFavorite } = useAgentHubLocal();

  const debouncedSearch = useDebounce(search, 300);

  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    agents.forEach((a) => a.tags?.forEach((tag) => tagSet.add(tag)));
    return [...tagSet].sort();
  }, [agents]);

  const filteredAgents = useMemo(() => {
    let list = agents;
    if (debouncedSearch) {
      const lower = debouncedSearch.toLowerCase();
      list = list.filter(
        (a) =>
          a.name.toLowerCase().includes(lower) ||
          a.description.toLowerCase().includes(lower) ||
          a.role.toLowerCase().includes(lower) ||
          a.model.toLowerCase().includes(lower),
      );
    }
    if (selectedTags.length > 0) {
      list = list.filter((a) => selectedTags.some((tag) => a.tags?.includes(tag)));
    }
    return list;
  }, [agents, debouncedSearch, selectedTags]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2 w-full">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            className="h-8 pl-8 pr-7 text-xs"
            placeholder="Search agents…"
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
        <Button aria-label="Export" ghost size="icon" title="Export" onClick={() => setShowExportDialog(true)}>
          <Download className="h-3.5 w-3.5" />
        </Button>
        <Button aria-label="Import" ghost size="icon" title="Import" onClick={() => setShowImportDialog(true)}>
          <Upload className="h-3.5 w-3.5" />
        </Button>
        <Button size="sm" onClick={() => navigate("/agents/new")} prefix={<Plus />}>
          New Agent
        </Button>
      </div>,
    );
    return () => { setEnd(null); };
  }, [setEnd, search, navigate]);

  const handleExport = useCallback(async (agentId: string) => {
    setExportingId(agentId);
    setExporting(true);
    try {
      const data = await useAgentStore.getState().exportAgent(agentId);
      const blob = new Blob([typeof data === "string" ? data : JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agent-${agentId}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Agent exported successfully", "success");
    } catch {
      showToast("Failed to export agent", "error");
    } finally {
      setExporting(false);
      setExportingId(null);
    }
  }, [showToast]);

  const handleImport = useCallback(async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      setImporting(true);
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        const formData = new FormData();
        formData.append("file", new Blob([JSON.stringify(data)], { type: "application/json" }), file.name);
        await useAgentStore.getState().importAgent(formData);
        showToast("Agent imported successfully", "success");
        setShowImportDialog(false);
      } catch {
        showToast("Failed to import agent", "error");
      } finally {
        setImporting(false);
      }
    };
    input.click();
  }, [showToast]);

  const handleAction = useCallback(async (id: string, action: string, fn: () => Promise<void>) => {
    setActionLoading((prev) => ({ ...prev, [`${id}:${action}`]: true }));
    try {
      await fn();
      showToast(`Agent ${action}d successfully`, "success");
    } catch {
      showToast(`Failed to ${action} agent`, "error");
    } finally {
      setActionLoading((prev) => ({ ...prev, [`${id}:${action}`]: false }));
    }
  }, [showToast]);

  const handleDelete = useCallback(async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await deleteAgent(deleteConfirm);
      showToast("Agent deleted", "success");
      setDeleteConfirm(null);
    } catch {
      showToast("Failed to delete agent", "error");
    } finally {
      setDeleting(false);
    }
  }, [deleteConfirm, deleteAgent, showToast]);

  if (loading && agents.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (error && agents.length === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button onClick={() => fetchAgents()} prefix={<RefreshCw />}>
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

      {/* Tag filter chips */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-muted-foreground mr-1">Tags:</span>
          {allTags.map((tag) => {
            const active = selectedTags.includes(tag);
            return (
              <button
                key={tag}
                type="button"
                onClick={() =>
                  setSelectedTags((prev) =>
                    active ? prev.filter((t) => t !== tag) : [...prev, tag],
                  )
                }
                className={cn(
                  "px-2 py-0.5 text-xs border transition-colors",
                  active
                    ? "border-foreground bg-foreground/10 text-foreground"
                    : "border-border text-muted-foreground hover:border-foreground/30",
                )}
              >
                {tag}
              </button>
            );
          })}
          {selectedTags.length > 0 && (
            <button
              type="button"
              onClick={() => setSelectedTags([])}
              className="text-xs text-muted-foreground hover:text-foreground ml-1"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {filteredAgents.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {search || selectedTags.length > 0
              ? "No agents match your search criteria."
              : "No agents yet. Create your first agent to get started."}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filteredAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              actionLoading={actionLoading}
              onAction={handleAction}
              onDelete={() => setDeleteConfirm(agent.id)}
              onNavigate={() => navigate(`/agents/${agent.id}`)}
            />
          ))}
        </div>
      )}

      {/* Export dialog */}
      <Dialog open={showExportDialog} onOpenChange={(o: boolean) => { if (!o) setShowExportDialog(false); }}>
        <DialogContent className="max-w-sm rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm">Export Agent</DialogTitle>
            <DialogDescription className="text-xs">Select an agent to export its configuration</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
            {agents.map((a: Agent) => (
              <button key={a.id} type="button" onClick={() => handleExport(a.id)}
                disabled={exporting && exportingId === a.id}
                className="flex items-center gap-3 w-full text-left p-2 border border-border hover:border-foreground/30 text-xs transition-colors"
              >
                <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="flex-1 truncate font-medium">{a.name}</span>
                <span className="text-muted-foreground">{a.model}</span>
                {exporting && exportingId === a.id ? <Spinner className="h-3 w-3" /> : <Download className="h-3 w-3 text-muted-foreground" />}
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Import dialog */}
      <Dialog open={showImportDialog} onOpenChange={(o: boolean) => { if (!o) setShowImportDialog(false); }}>
        <DialogContent className="max-w-sm rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm">Import Agent</DialogTitle>
            <DialogDescription className="text-xs">Import an agent from a JSON file</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center gap-4 py-4">
            <FileJson className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-xs text-muted-foreground text-center">Select a JSON file exported from another Aetheros instance</p>
            <Button onClick={handleImport} disabled={importing} prefix={importing ? <Spinner /> : <Upload />}>
              {importing ? "Importing..." : "Choose File"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete confirm dialog */}
      <Dialog open={!!deleteConfirm} onOpenChange={(o: boolean) => { if (!o) setDeleteConfirm(null); }}>
        <DialogContent className="max-w-sm rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm">Delete Agent</DialogTitle>
            <DialogDescription className="text-xs">
              Are you sure you want to delete this agent? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-2">
            <Button ghost size="sm" onClick={() => setDeleteConfirm(null)}>
              Cancel
            </Button>
            <Button
              destructive
              size="sm"
              onClick={handleDelete}
              disabled={deleting}
              prefix={deleting ? <Spinner /> : <Trash2 />}
            >
              {deleting ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function AgentCard({
  agent,
  actionLoading,
  onAction,
  onDelete,
  onNavigate,
}: {
  agent: Agent;
  actionLoading: Record<string, boolean>;
  onAction: (id: string, action: string, fn: () => Promise<void>) => void;
  onDelete: () => void;
  onNavigate: () => void;
}) {
  const { toggleFavorite, isFavorite } = useAgentHubLocal();
  const fav = isFavorite(agent.id);
  const store = useAgentStore();

  const isPaused = agent.status === "paused";
  const isRunning = agent.status === "running";

  return (
    <Card className="rounded-none group hover:border-foreground/20 transition-colors">
      <CardContent className="p-4">
        <button type="button" onClick={onNavigate} className="w-full text-left">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="text-sm font-medium truncate">{agent.name}</span>
                <button type="button" onClick={(e) => { e.stopPropagation(); toggleFavorite(agent.id); }}
                  className="shrink-0 hover:scale-110 transition-transform"
                  title={fav ? "Remove from favorites" : "Add to favorites"}
                >
                  <Star className={cn("h-3.5 w-3.5", fav ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30 hover:text-amber-400/50")} />
                </button>
              </div>
              <Badge tone={STATUS_TONES[agent.status] ?? "secondary"} className="text-[10px] shrink-0 ml-2">
                {agent.status}
              </Badge>
            </div>
          <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{agent.description}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-mono">{agent.model}</span>
            <span>·</span>
            <span className="capitalize">{agent.role}</span>
          </div>
        </button>

        {agent.tags && agent.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {agent.tags.map((tag) => (
              <span key={tag} className="text-[10px] font-mono text-text-tertiary border border-border px-1 py-px">
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1 mt-3 pt-2 border-t border-border">
          {isPaused ? (
            <ActionButton
              icon={<Play />}
              tooltip="Resume"
              loading={actionLoading[`${agent.id}:resume`]}
              onClick={() => onAction(agent.id, "resume", () => store.resumeAgent(agent.id))}
            />
          ) : (
            <ActionButton
              icon={<Pause />}
              tooltip="Pause"
              loading={actionLoading[`${agent.id}:pause`]}
              onClick={() => onAction(agent.id, "pause", () => store.pauseAgent(agent.id))}
            />
          )}
          <ActionButton
            icon={<RotateCcw />}
            tooltip="Restart"
            loading={actionLoading[`${agent.id}:restart`]}
            onClick={() => onAction(agent.id, "restart", () => store.restartAgent(agent.id))}
          />
          <ActionButton
            icon={<Copy />}
            tooltip="Duplicate"
            loading={actionLoading[`${agent.id}:duplicate`]}
            onClick={() => onAction(agent.id, "duplicate", () => store.duplicateAgent(agent.id))}
          />
          <ActionButton
            icon={<GitBranch />}
            tooltip="Clone"
            loading={actionLoading[`${agent.id}:clone`]}
            onClick={() => onAction(agent.id, "clone", () => store.cloneAgent(agent.id))}
          />
          <div className="flex-1" />
          <ActionButton
            icon={<Trash2 />}
            tooltip="Delete"
            destructive
            onClick={onDelete}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function ActionButton({
  icon,
  tooltip,
  loading,
  destructive,
  onClick,
}: {
  icon: React.ReactNode;
  tooltip: string;
  loading?: boolean;
  destructive?: boolean;
  onClick: () => void;
}) {
  return (
    <Button
      ghost
      size="icon"
      title={tooltip}
      aria-label={tooltip}
      onClick={onClick}
      disabled={loading}
      className={cn("h-7 w-7", destructive && "hover:text-destructive")}
    >
      {loading ? <Spinner className="h-3 w-3" /> : icon}
    </Button>
  );
}
