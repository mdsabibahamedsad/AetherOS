import { useCallback, useEffect, useMemo, useState } from "react";
import { Shield, ShieldCheck, ShieldX, Plus, Trash2, Search, X, Filter, Clock, User, Ban, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@nous-research/ui/ui/components/dialog";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useI18n } from "@/i18n";
import { useAgentStore } from "@/store/agent-store";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { cn } from "@/lib/utils";
import type { AgentPermission, Agent } from "@/lib/api";

function formatTime(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function isExpired(expires_at: string | null): boolean {
  if (!expires_at) return false;
  return new Date(expires_at).getTime() < Date.now();
}

export default function AgentPermissionsPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { t } = useI18n();
  const { toast } = useToast();
  const { permissions, agents, fetchPermissions, fetchAgents, grantPermission, revokePermission, loading } = useAgentStore();
  const [localLoading, setLocalLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState<string>("all");
  const [filterResource, setFilterResource] = useState<string>("");
  const [filterEffect, setFilterEffect] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [grantOpen, setGrantOpen] = useState(false);
  const [granting, setGranting] = useState(false);

  const [formAgentId, setFormAgentId] = useState("");
  const [formResource, setFormResource] = useState("");
  const [formAction, setFormAction] = useState("");
  const [formEffect, setFormEffect] = useState<"allow" | "deny">("allow");
  const [formExpiry, setFormExpiry] = useState("");

  const [revokeConfirm, setRevokeConfirm] = useState<AgentPermission | null>(null);
  const [revoking, setRevoking] = useState(false);

  useEffect(() => {
    setTitle("Agent Permissions");
    setDescription("Manage agent access permissions");
  }, [setTitle, setDescription]);

  const load = useCallback(async () => {
    setLocalLoading(true);
    setError(null);
    try {
      await Promise.all([fetchPermissions(), fetchAgents()]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLocalLoading(false);
    }
  }, [fetchPermissions, fetchAgents]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    return permissions.filter((p) => {
      if (filterAgent !== "all" && p.agent_id !== filterAgent) return false;
      if (filterEffect !== "all" && p.effect !== filterEffect) return false;
      if (filterResource && !p.resource.toLowerCase().includes(filterResource.toLowerCase())) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!p.resource.toLowerCase().includes(q) && !p.action.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [permissions, filterAgent, filterEffect, filterResource, searchQuery]);

  const allowed = filtered.filter((p) => p.effect === "allow");
  const denied = filtered.filter((p) => p.effect === "deny");

  const resetForm = () => {
    setFormAgentId("");
    setFormResource("");
    setFormAction("");
    setFormEffect("allow");
    setFormExpiry("");
  };

  const handleGrant = async () => {
    if (!formAgentId || !formResource || !formAction) {
      toast({ title: "Agent, resource, and action are required", variant: "destructive" });
      return;
    }
    setGranting(true);
    try {
      await grantPermission({
        id: "",
        agent_id: formAgentId,
        resource: formResource,
        action: formAction,
        effect: formEffect,
        granted_by: "dashboard",
        created_at: new Date().toISOString(),
        expires_at: formExpiry || null,
      });
      toast({ title: "Permission granted", variant: "success" });
      setGrantOpen(false);
      resetForm();
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setGranting(false);
    }
  };

  const handleRevoke = async () => {
    if (!revokeConfirm) return;
    setRevoking(true);
    try {
      await revokePermission(revokeConfirm.id);
      toast({ title: "Permission revoked", variant: "success" });
      setRevokeConfirm(null);
    } catch (err) {
      toast({ title: `Failed: ${(err as Error).message}`, variant: "destructive" });
    } finally {
      setRevoking(false);
    }
  };

  const agentMap = new Map(agents.map((a: Agent) => [a.id, a]));
  const resources = Array.from(new Set(permissions.map((p) => p.resource))).sort();

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
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Total</span>
              <Shield className="h-4 w-4 text-midground" />
            </div>
            <div className="mt-1 text-2xl font-bold">{permissions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Allow</span>
              <CheckCircle2 className="h-4 w-4 text-success" />
            </div>
            <div className="mt-1 text-2xl font-bold">{permissions.filter((p) => p.effect === "allow").length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Deny</span>
              <Ban className="h-4 w-4 text-destructive" />
            </div>
            <div className="mt-1 text-2xl font-bold">{permissions.filter((p) => p.effect === "deny").length}</div>
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[180px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input className="h-8 pl-8 pr-7 text-xs" placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
            {searchQuery && (
              <Button ghost size="xs" className="absolute right-1 top-1/2 -translate-y-1/2" onClick={() => setSearchQuery("")}>
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs">Agent</Label>
            <Select value={filterAgent} onValueChange={setFilterAgent}>
              <SelectOption value="all">All</SelectOption>
              {agents.map((a: Agent) => (
                <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs">Effect</Label>
            <Select value={filterEffect} onValueChange={setFilterEffect}>
              <SelectOption value="all">All</SelectOption>
              <SelectOption value="allow">Allow</SelectOption>
              <SelectOption value="deny">Deny</SelectOption>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-xs">Resource</Label>
            <Select value={filterResource} onValueChange={setFilterResource}>
              <SelectOption value="">All</SelectOption>
              {resources.map((r) => (
                <SelectOption key={r} value={r}>{r}</SelectOption>
              ))}
            </Select>
          </div>
        </div>
        <Button size="sm" onClick={() => setGrantOpen(true)} prefix={<Plus className="h-4 w-4" />}>
          Grant Permission
        </Button>
      </div>

      {filtered.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No permissions match the current filters.
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-success" />
              Allow Rules
            </CardTitle>
            <Badge tone="secondary" className="text-xs">{allowed.length}</Badge>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {allowed.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">No allow rules.</p>
          ) : (
            <div className="space-y-1">
              {allowed.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-2 px-3 border border-border rounded text-xs">
                  <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
                  <span className="font-mono-ui text-success font-medium">{p.action}</span>
                  <span className="text-muted-foreground">on</span>
                  <code className="font-mono-ui">{p.resource}</code>
                  <span className="text-muted-foreground">for</span>
                  <span className="font-medium">{agentMap.get(p.agent_id)?.name ?? p.agent_id}</span>
                  <span className="text-muted-foreground ml-auto text-[10px]">by {p.granted_by}</span>
                  {p.expires_at && (
                    <span className={cn("text-[10px] flex items-center gap-1", isExpired(p.expires_at) ? "text-destructive" : "text-muted-foreground")}>
                      <Clock className="h-3 w-3" />
                      {isExpired(p.expires_at) ? "Expired" : formatTime(p.expires_at)}
                    </span>
                  )}
                  <Button aria-label="Revoke" ghost size="icon" destructive onClick={() => setRevokeConfirm(p)} title="Revoke">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldX className="h-4 w-4 text-destructive" />
              Deny Rules
            </CardTitle>
            <Badge tone="secondary" className="text-xs">{denied.length}</Badge>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {denied.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">No deny rules.</p>
          ) : (
            <div className="space-y-1">
              {denied.map((p) => (
                <div key={p.id} className="flex items-center gap-3 py-2 px-3 border border-border rounded text-xs">
                  <Ban className="h-3.5 w-3.5 text-destructive shrink-0" />
                  <span className="font-mono-ui text-destructive font-medium">{p.action}</span>
                  <span className="text-muted-foreground">on</span>
                  <code className="font-mono-ui">{p.resource}</code>
                  <span className="text-muted-foreground">for</span>
                  <span className="font-medium">{agentMap.get(p.agent_id)?.name ?? p.agent_id}</span>
                  <span className="text-muted-foreground ml-auto text-[10px]">by {p.granted_by}</span>
                  {p.expires_at && (
                    <span className={cn("text-[10px] flex items-center gap-1", isExpired(p.expires_at) ? "text-destructive" : "text-muted-foreground")}>
                      <Clock className="h-3 w-3" />
                      {isExpired(p.expires_at) ? "Expired" : formatTime(p.expires_at)}
                    </span>
                  )}
                  <Button aria-label="Revoke" ghost size="icon" destructive onClick={() => setRevokeConfirm(p)} title="Revoke">
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={grantOpen} onOpenChange={(o) => { if (!o) setGrantOpen(false); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Grant Permission</DialogTitle>
            <DialogDescription>Define a new permission rule for an agent.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="perm-agent">Agent</Label>
              <Select id="perm-agent" value={formAgentId} onValueChange={setFormAgentId}>
                <SelectOption value="">Select agent...</SelectOption>
                {agents.map((a: Agent) => (
                  <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>
                ))}
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="perm-resource">Resource</Label>
              <Input id="perm-resource" placeholder="e.g. files, memory, network" value={formResource} onChange={(e) => setFormResource(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="perm-action">Action</Label>
              <Input id="perm-action" placeholder="e.g. read, write, execute" value={formAction} onChange={(e) => setFormAction(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="perm-effect">Effect</Label>
              <Select id="perm-effect" value={formEffect} onValueChange={(v) => setFormEffect(v as "allow" | "deny")}>
                <SelectOption value="allow">Allow</SelectOption>
                <SelectOption value="deny">Deny</SelectOption>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="perm-expiry">Expires At (optional)</Label>
              <Input id="perm-expiry" type="datetime-local" value={formExpiry} onChange={(e) => setFormExpiry(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGrantOpen(false)}>Cancel</Button>
            <Button onClick={handleGrant} disabled={granting} prefix={granting ? <Spinner /> : undefined}>
              {granting ? "Granting..." : "Grant"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!revokeConfirm} onOpenChange={() => setRevokeConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke Permission</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke this permission? This will immediately remove access for the agent.
            </DialogDescription>
          </DialogHeader>
          {revokeConfirm && (
            <div className="border border-border rounded p-3 text-xs space-y-1">
              <div><span className="text-muted-foreground">Agent:</span> {agentMap.get(revokeConfirm.agent_id)?.name ?? revokeConfirm.agent_id}</div>
              <div><span className="text-muted-foreground">Resource:</span> {revokeConfirm.resource}</div>
              <div><span className="text-muted-foreground">Action:</span> {revokeConfirm.action}</div>
              <div><span className="text-muted-foreground">Effect:</span> {revokeConfirm.effect}</div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevokeConfirm(null)}>Cancel</Button>
            <Button destructive onClick={handleRevoke} disabled={revoking} prefix={revoking ? <Spinner /> : undefined}>
              {revoking ? "Revoking..." : "Revoke"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
