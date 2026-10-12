import { useCallback, useEffect, useState } from "react";
import { Tags, Plus, Trash2, Pencil, X, Palette } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@nous-research/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { api } from "@/lib/api";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { TagDefinition } from "@/lib/api";

const PRESET_COLORS = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#06b6d4", "#3b82f6", "#6366f1", "#a855f7", "#ec4899",
  "#78716c", "#a1a1aa",
];

export default function AgentTagsPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { tags, fetchTags, createTag, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [editingTag, setEditingTag] = useState<TagDefinition | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<TagDefinition | null>(null);

  const [formName, setFormName] = useState("");
  const [formColor, setFormColor] = useState(PRESET_COLORS[0]);
  const [formDescription, setFormDescription] = useState("");

  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setTitle("Agent Tags");
    setDescription("Manage tags for agent organization");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await fetchTags();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchTags]);

  useEffect(() => { load(); }, [load]);

  const resetForm = () => {
    setFormName("");
    setFormColor(PRESET_COLORS[0]);
    setFormDescription("");
  };

  const handleCreate = async () => {
    if (!formName.trim()) {
      toast({ title: "Name is required", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      await createTag({
        name: formName.trim(),
        color: formColor,
        description: formDescription.trim(),
      });
      toast({ title: "Tag created", variant: "success" });
      setCreateOpen(false);
      resetForm();
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingTag || !formName.trim()) return;
    setSaving(true);
    try {
      await api.updateTag(editingTag.id, {
        name: formName.trim(),
        color: formColor,
        description: formDescription.trim(),
      });
      await fetchTags();
      toast({ title: "Tag updated", variant: "success" });
      setEditingTag(null);
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await api.deleteTag(deleteConfirm.id);
      await fetchTags();
      toast({ title: "Tag deleted", variant: "success" });
      setDeleteConfirm(null);
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const openEdit = (tag: TagDefinition) => {
    setEditingTag(tag);
    setFormName(tag.name);
    setFormColor(tag.color);
    setFormDescription(tag.description);
  };

  const totalAgentCount = tags.reduce((sum, t) => sum + t.agent_count, 0);

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
            <Button className="mt-4" size="sm" onClick={load}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Tags</span>
              <Tags className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{tags.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Total Tags Applied</span>
              <Tags className="h-4 w-4 text-info" />
            </div>
            <div className="mt-1 text-2xl font-bold">{totalAgentCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Avg Per Tag</span>
              <Tags className="h-4 w-4 text-warning" />
            </div>
            <div className="mt-1 text-2xl font-bold">{tags.length > 0 ? (totalAgentCount / tags.length).toFixed(1) : "0"}</div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{tags.length} tags</span>
        </div>
        <Button size="sm" onClick={() => { resetForm(); setCreateOpen(true); }} prefix={<Plus className="h-4 w-4" />}>
          Create Tag
        </Button>
      </div>

      {tags.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No tags yet. Create one to organize your agents.
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {tags.map((tag) => (
          <Card key={tag.id} className="group transition-colors hover:border-midground/30">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-6 w-6 rounded border border-border/50" style={{ backgroundColor: tag.color }} />
                  <div>
                    <div className="text-sm font-medium">{tag.name}</div>
                    {tag.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{tag.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button aria-label="Edit" ghost size="icon" onClick={() => openEdit(tag)} title="Edit">
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button aria-label="Delete" ghost size="icon" destructive onClick={() => setDeleteConfirm(tag)} title="Delete">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <Badge tone="secondary" className="text-[10px]">{tag.agent_count} agent{tag.agent_count !== 1 ? "s" : ""}</Badge>
                <span className="text-[10px] text-muted-foreground">Created {new Date(tag.created_at).toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={createOpen} onOpenChange={(o) => { if (!o) setCreateOpen(false); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create Tag</DialogTitle>
            <DialogDescription>Add a new tag for organizing agents.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="tag-name">Name</Label>
              <Input id="tag-name" placeholder="Tag name" value={formName} onChange={(e) => setFormName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Color</Label>
              <div className="flex flex-wrap gap-2">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setFormColor(c)}
                    className={cn(
                      "h-7 w-7 rounded border border-border/50 transition-transform",
                      formColor === c && "ring-2 ring-foreground scale-110",
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tag-desc">Description</Label>
              <textarea id="tag-desc" placeholder="Optional description" value={formDescription} onChange={(e) => setFormDescription(e.target.value)} className="flex min-h-[60px] w-full border border-midground/15 bg-background/40 px-3 py-2 font-courier text-sm transition-colors placeholder:text-midground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-midground/30 focus-visible:border-midground/25" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={saving} prefix={saving ? <Spinner /> : undefined}>
              {saving ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editingTag} onOpenChange={() => setEditingTag(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Tag</DialogTitle>
            <DialogDescription>Update the tag properties.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-tag-name">Name</Label>
              <Input id="edit-tag-name" value={formName} onChange={(e) => setFormName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label>Color</Label>
              <div className="flex flex-wrap gap-2">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setFormColor(c)}
                    className={cn(
                      "h-7 w-7 rounded border border-border/50 transition-transform",
                      formColor === c && "ring-2 ring-foreground scale-110",
                    )}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-tag-desc">Description</Label>
              <textarea id="edit-tag-desc" value={formDescription} onChange={(e) => setFormDescription(e.target.value)} className="flex min-h-[60px] w-full border border-midground/15 bg-background/40 px-3 py-2 font-courier text-sm transition-colors placeholder:text-midground/50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-midground/30 focus-visible:border-midground/25" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingTag(null)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={saving} prefix={saving ? <Spinner /> : undefined}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Tag</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteConfirm?.name}"? This will remove it from <strong>{deleteConfirm?.agent_count}</strong> agent{deleteConfirm?.agent_count !== 1 ? "s" : ""}. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
            <Button destructive onClick={handleDelete} disabled={deleting} prefix={deleting ? <Spinner /> : undefined}>
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
