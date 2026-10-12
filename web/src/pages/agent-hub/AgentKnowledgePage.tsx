import { useCallback, useEffect, useMemo, useState } from "react";
import {
  FileText,
  File,
  FileType,
  Globe,
  GitBranch,
  FolderOpen,
  Image,
  BookOpen,
  Search,
  Trash2,
  RefreshCw,
  Upload,
  Plus,
  X,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@nous-research/ui/ui/components/dialog";
import { Tabs, TabsList, TabsTrigger } from "@nous-research/ui/ui/components/tabs";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { useAgentHubLocal, KNOWLEDGE_SOURCE_TYPES, type KnowledgeSourceType, type KnowledgeAttachment } from "@/store/agent-hub-local";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/api";

const TYPE_ICONS: Record<string, typeof FileText> = {
  pdf: FileText, markdown: FileText, word: FileType, text: File,
  website: Globe, git: GitBranch, folder: FolderOpen, images: Image,
};

const TYPE_COLORS: Record<string, string> = {
  pdf: "border-l-red-500", markdown: "border-l-blue-500", word: "border-l-blue-400", text: "border-l-gray-400",
  website: "border-l-green-500", git: "border-l-orange-500", folder: "border-l-yellow-500", images: "border-l-purple-500",
};

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  indexing: { icon: Loader2, color: "text-blue-500", label: "Indexing" },
  ready: { icon: CheckCircle2, color: "text-green-500", label: "Ready" },
  error: { icon: AlertCircle, color: "text-red-500", label: "Error" },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function AgentKnowledgePage() {
  const { setTitle, setDescription } = usePageHeader();
  const { agents, fetchAgents } = useAgentStore();
  const {
    knowledge, addKnowledgeAttachment, removeKnowledgeAttachment,
    updateKnowledgeStatus, selectedKnowledgeAgentId, setSelectedKnowledgeAgentId,
  } = useAgentHubLocal();
  const { toast, showToast } = useToast();

  const [agentFilter, setAgentFilter] = useState(selectedKnowledgeAgentId || "");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addType, setAddType] = useState<KnowledgeSourceType>("pdf");
  const [addName, setAddName] = useState("");
  const [addPath, setAddPath] = useState("");
  const [addUrl, setAddUrl] = useState("");
  const [addBranch, setAddBranch] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    setTitle("Agent Knowledge");
    setDescription("Manage knowledge sources attached to your agents");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    if (selectedKnowledgeAgentId && !agentFilter) {
      setAgentFilter(selectedKnowledgeAgentId);
    }
  }, [selectedKnowledgeAgentId, agentFilter]);

  const allAttachments = useMemo(() => {
    const result: Array<KnowledgeAttachment & { agentName?: string }> = [];
    const agentMap = new Map(agents.map((a: Agent) => [a.id, a.name]));
    if (agentFilter) {
      const list = knowledge[agentFilter] || [];
      list.forEach((a) => result.push({ ...a, agentName: agentMap.get(a.agentId) }));
    } else {
      Object.entries(knowledge).forEach(([agentId, list]) => {
        list.forEach((a) => result.push({ ...a, agentName: agentMap.get(agentId) }));
      });
    }
    return result;
  }, [knowledge, agentFilter, agents]);

  const filtered = useMemo(() => {
    let list = allAttachments;
    if (typeFilter !== "all") list = list.filter((a) => a.type === typeFilter);
    if (search) {
      const lower = search.toLowerCase();
      list = list.filter((a) => a.name.toLowerCase().includes(lower));
    }
    return list;
  }, [allAttachments, typeFilter, search]);

  const stats = useMemo(() => ({
    total: allAttachments.length,
    ready: allAttachments.filter((a) => a.status === "ready").length,
    indexing: allAttachments.filter((a) => a.status === "indexing").length,
    error: allAttachments.filter((a) => a.status === "error").length,
    totalChunks: allAttachments.reduce((sum, a) => sum + a.chunkCount, 0),
  }), [allAttachments]);

  const handleAddKnowledge = useCallback(async () => {
    if (!agentFilter) { showToast("Please select an agent first", "error"); return; }
    if (!addName.trim()) { showToast("Please enter a name", "error"); return; }
    setAdding(true);
    const attachment: KnowledgeAttachment = {
      id: `knowledge-${Date.now()}`,
      agentId: agentFilter,
      type: addType,
      name: addName.trim(),
      path: addPath || addUrl || `/knowledge/${addName.trim().replace(/\s+/g, "-")}`,
      size: 0,
      status: "indexing",
      chunkCount: 0,
      createdAt: new Date().toISOString(),
      metadata: addBranch ? { branch: addBranch } : {},
    };
    addKnowledgeAttachment(attachment);
    setTimeout(() => {
      updateKnowledgeStatus(agentFilter, attachment.id, "ready", undefined);
      showToast(`"${attachment.name}" indexed successfully`, "success");
    }, 1500);
    setAddName("");
    setAddPath("");
    setAddUrl("");
    setAddBranch("");
    setAdding(false);
    setShowAddDialog(false);
  }, [agentFilter, addType, addName, addPath, addUrl, addBranch, addKnowledgeAttachment, updateKnowledgeStatus, showToast]);

  const handleRemove = useCallback((agentId: string, attachmentId: string, name: string) => {
    removeKnowledgeAttachment(agentId, attachmentId);
    showToast(`"${name}" removed`, "success");
  }, [removeKnowledgeAttachment, showToast]);

  const handleReindex = useCallback((agentId: string, attachmentId: string) => {
    updateKnowledgeStatus(agentId, attachmentId, "indexing");
    setTimeout(() => {
      updateKnowledgeStatus(agentId, attachmentId, "ready", undefined);
      showToast("Knowledge re-indexed successfully", "success");
    }, 1000);
  }, [updateKnowledgeStatus, showToast]);

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Total Sources</span>
            <Database className="h-4 w-4 text-muted-foreground" />
          </div>
          <span className="text-2xl font-bold">{stats.total}</span>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Ready</span>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </div>
          <span className="text-2xl font-bold text-green-500">{stats.ready}</span>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Indexing</span>
            <Loader2 className="h-4 w-4 text-blue-500" />
          </div>
          <span className="text-2xl font-bold text-blue-500">{stats.indexing}</span>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Errors</span>
            <AlertCircle className="h-4 w-4 text-red-500" />
          </div>
          <span className="text-2xl font-bold text-red-500">{stats.error}</span>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider">Total Chunks</span>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </div>
          <span className="text-2xl font-bold">{stats.totalChunks}</span>
        </CardContent></Card>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Label className="text-xs whitespace-nowrap">Agent</Label>
          <Select value={agentFilter} onValueChange={(v) => { setAgentFilter(v); setSelectedKnowledgeAgentId(v); }}>
            <SelectOption value="">All Agents</SelectOption>
            {agents.map((a: Agent) => (
              <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
            ))}
          </Select>
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input className="h-8 pl-8 text-xs" placeholder="Search knowledge..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Button size="sm" onClick={() => setShowAddDialog(true)} prefix={<Plus />}>
          Add Knowledge
        </Button>
      </div>

      {/* Type filter */}
      <div className="flex flex-wrap gap-1">
        <button type="button" onClick={() => setTypeFilter("all")} className={cn("px-2.5 py-1 text-xs border transition-colors", typeFilter === "all" ? "border-foreground/40 bg-foreground/10 text-foreground" : "border-border text-muted-foreground hover:border-muted-foreground/40")}>
          All Types
        </button>
        {KNOWLEDGE_SOURCE_TYPES.map((st) => {
          const Icon = TYPE_ICONS[st.type] || FileText;
          const isActive = typeFilter === st.type;
          return (
            <button key={st.type} type="button" onClick={() => setTypeFilter(isActive ? "all" : st.type)}
              className={cn("flex items-center gap-1.5 px-2.5 py-1 text-xs border transition-colors", isActive ? "border-foreground/40 bg-foreground/10 text-foreground" : "border-border text-muted-foreground hover:border-muted-foreground/40")}
            >
              <Icon className="h-3 w-3" />
              {st.label}
            </button>
          );
        })}
      </div>

      {/* Knowledge list */}
      {filtered.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-sm text-muted-foreground">
          {agentFilter ? "No knowledge sources attached to this agent." : "No knowledge sources found. Add a source to get started."}
        </CardContent></Card>
      ) : (
        <div className="grid gap-3">
          {filtered.map((item) => {
            const TypeIcon = TYPE_ICONS[item.type] || FileText;
            const statusConfig = STATUS_CONFIG[item.status] || STATUS_CONFIG.ready;
            const StatusIcon = statusConfig.icon;
            return (
              <Card key={item.id} className={cn("border-l-2", TYPE_COLORS[item.type] || "border-l-gray-400")}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-4">
                    <div className="rounded-lg bg-muted/20 p-2 shrink-0">
                      <TypeIcon className="h-5 w-5 text-midground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium truncate">{item.name}</span>
                        <Badge tone="secondary" className="text-[10px]">{item.type.toUpperCase()}</Badge>
                        <span className={cn("flex items-center gap-1 text-xs", statusConfig.color)}>
                          <StatusIcon className={cn("h-3 w-3", item.status === "indexing" && "animate-spin")} />
                          {statusConfig.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{item.path}</span>
                        {item.size > 0 && <span>{formatBytes(item.size)}</span>}
                        <span>{item.chunkCount} chunks</span>
                        <span>Added {formatDate(item.createdAt)}</span>
                      </div>
                      {!agentFilter && item.agentName && (
                        <Badge tone="outline" className="text-[10px] mt-1">{item.agentName}</Badge>
                      )}
                      {item.error && (
                        <p className="text-xs text-red-500 mt-1">{item.error}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button aria-label="Re-index" ghost size="icon" title="Re-index" onClick={() => handleReindex(item.agentId, item.id)}>
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button aria-label="Remove" ghost size="icon" title="Remove" className="hover:text-destructive" onClick={() => handleRemove(item.agentId, item.id, item.name)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={showAddDialog} onOpenChange={(o: boolean) => { if (!o) setShowAddDialog(false); }}>
        <DialogContent className="max-w-lg rounded-none">
          <DialogHeader>
            <DialogTitle className="text-sm">Add Knowledge Source</DialogTitle>
            <DialogDescription className="text-xs">Attach a knowledge source to the selected agent</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Label className="text-xs w-16">Agent</Label>
              <Select value={agentFilter} onValueChange={setAgentFilter} className="flex-1">
                {agents.map((a: Agent) => (
                  <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
                ))}
              </Select>
            </div>

            <div>
              <Label className="text-xs mb-2 block">Source Type</Label>
              <div className="grid grid-cols-4 gap-2">
                {KNOWLEDGE_SOURCE_TYPES.map((st) => {
                  const Icon = TYPE_ICONS[st.type] || FileText;
                  const isSelected = addType === st.type;
                  return (
                    <button key={st.type} type="button" onClick={() => setAddType(st.type)}
                      className={cn("flex flex-col items-center gap-1 p-2 border text-xs transition-colors text-center", isSelected ? "border-foreground bg-foreground/10" : "border-border hover:border-muted-foreground/40")}
                    >
                      <Icon className="h-4 w-4" />
                      {st.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="know-name" className="text-xs">Name</Label>
              <Input id="know-name" value={addName} onChange={(e) => setAddName(e.target.value)} placeholder="My Knowledge Source" className="text-xs" />
            </div>

            {(addType === "website") ? (
              <div className="grid gap-2">
                <Label htmlFor="know-url" className="text-xs">URL</Label>
                <Input id="know-url" value={addUrl} onChange={(e) => setAddUrl(e.target.value)} placeholder="https://example.com/docs" className="text-xs font-mono" />
              </div>
            ) : (addType === "git") ? (
              <div className="grid gap-2">
                <Label htmlFor="know-git" className="text-xs">Repository URL</Label>
                <Input id="know-git" value={addPath} onChange={(e) => setAddPath(e.target.value)} placeholder="https://github.com/user/repo" className="text-xs font-mono" />
                <Label htmlFor="know-branch" className="text-xs">Branch (optional)</Label>
                <Input id="know-branch" value={addBranch} onChange={(e) => setAddBranch(e.target.value)} placeholder="main" className="text-xs font-mono" />
              </div>
            ) : (addType === "folder") ? (
              <div className="grid gap-2">
                <Label htmlFor="know-folder" className="text-xs">Folder Path</Label>
                <Input id="know-folder" value={addPath} onChange={(e) => setAddPath(e.target.value)} placeholder="/path/to/documents" className="text-xs font-mono" />
              </div>
            ) : (
              <div className="grid gap-2">
                <Label htmlFor="know-path" className="text-xs">File Path</Label>
                <div className="flex items-center gap-2">
                  <Input id="know-path" value={addPath} onChange={(e) => setAddPath(e.target.value)} placeholder="/path/to/file" className="text-xs font-mono flex-1" />
                  <Button ghost size="icon" title="Browse" outlined><Upload className="h-3.5 w-3.5" /></Button>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 mt-2">
              <Button ghost size="sm" onClick={() => setShowAddDialog(false)}>Cancel</Button>
              <Button size="sm" onClick={handleAddKnowledge} disabled={adding || !agentFilter} prefix={adding ? <Spinner /> : <Plus />}>
                {adding ? "Adding..." : "Add Source"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
