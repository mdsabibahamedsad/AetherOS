import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Shield,
  ShieldCheck,
  ShieldOff,
  Globe,
  FolderOpen,
  Cpu,
  MemoryStick,
  Clock,
  CheckCircle2,
  AlertTriangle,
  X,
  Plus,
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  Network,
  Lock,
  Unlock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { useAgentHubLocal } from "@/store/agent-hub-local";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/api";

const SANDBOX_MODES = [
  { value: "isolated", label: "Isolated", description: "No network or filesystem access" },
  { value: "restricted", label: "Restricted", description: "Limited to allowed domains and paths" },
  { value: "standard", label: "Standard", description: "Full access with audit logging" },
] as const;

const APPROVAL_ACTIONS = [
  "web_search", "file_write", "terminal_exec", "network_request",
  "code_execution", "browser_navigate", "deploy", "delete_file",
  "install_package", "modify_config",
];

export default function AgentSecurityPage() {
  const { setTitle, setDescription } = usePageHeader();
  const { agents, fetchAgents } = useAgentStore();
  const { getSecuritySettings, updateSecuritySettings } = useAgentHubLocal();
  const { toast, showToast } = useToast();

  const [agentId, setAgentId] = useState("");
  const [saving, setSaving] = useState(false);
  const [newDomain, setNewDomain] = useState("");
  const [newBlockDomain, setNewBlockDomain] = useState("");
  const [newApproval, setNewApproval] = useState("");

  const settings = useMemo(() => agentId ? getSecuritySettings(agentId) : null, [agentId, getSecuritySettings]);

  useEffect(() => {
    setTitle("Agent Security");
    setDescription("Configure security, sandbox, and permission settings per agent");
  }, [setTitle, setDescription]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const handleSave = useCallback(async () => {
    if (!agentId || !settings) return;
    setSaving(true);
    try {
      await new Promise((r) => setTimeout(r, 300));
      showToast("Security settings saved", "success");
    } catch {
      showToast("Failed to save security settings", "error");
    } finally {
      setSaving(false);
    }
  }, [agentId, settings, showToast]);

  const updateField = useCallback(<K extends keyof typeof settings>(key: K, value: (typeof settings)[K]) => {
    if (!agentId) return;
    updateSecuritySettings(agentId, { [key]: value });
  }, [agentId, updateSecuritySettings]);

  if (!agentId || !settings) {
    return (
      <div className="flex flex-col gap-6">
        <Card><CardContent className="p-6">
          <div className="flex flex-col items-center gap-4 py-12">
            <Shield className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">Select an agent to configure security settings</p>
            <Select value={agentId} onValueChange={setAgentId}>
              <SelectOption value="">Choose an agent...</SelectOption>
              {agents.map((a: Agent) => <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>)}
            </Select>
          </div>
        </CardContent></Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <Toast toast={toast} />

      <div className="flex items-center gap-3">
        <Select value={agentId} onValueChange={setAgentId} className="max-w-xs">
          {agents.map((a: Agent) => <SelectOption key={a.id} value={a.id}>{a.name}</SelectOption>)}
        </Select>
        <Badge tone={settings.sandboxEnabled ? "success" : "secondary"} className="text-xs">
          {settings.sandboxEnabled ? "Sandbox Active" : "Sandbox Disabled"}
        </Badge>
      </div>

      {/* Sandbox */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-green-500" />
            <CardTitle className="text-sm">Sandbox Configuration</CardTitle>
          </div>
          <CardDescription className="text-xs">Isolate agent execution in a sandboxed environment</CardDescription>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-4">
          <div className="flex items-center gap-3">
            <Switch checked={settings.sandboxEnabled} onCheckedChange={(v: boolean) => updateField("sandboxEnabled", v)} />
            <Label>Enable Sandbox</Label>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {SANDBOX_MODES.map((mode) => (
              <button key={mode.value} type="button" onClick={() => updateField("sandboxMode", mode.value)}
                className={cn("p-3 border text-left text-xs transition-colors", settings.sandboxMode === mode.value ? "border-foreground bg-foreground/5" : "border-border hover:border-muted-foreground/40")}
              >
                <div className="font-medium mb-1">{mode.label}</div>
                <div className="text-muted-foreground">{mode.description}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Access Control */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-blue-500" />
            <CardTitle className="text-sm">Access Control</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="flex items-center gap-3">
              <Switch checked={settings.networkAccess} onCheckedChange={(v: boolean) => updateField("networkAccess", v)} />
              <div>
                <Label>Network Access</Label>
                <p className="text-xs text-muted-foreground">Allow outbound network requests</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={settings.filesystemAccess} onCheckedChange={(v: boolean) => updateField("filesystemAccess", v)} />
              <div>
                <Label>Filesystem Access</Label>
                <p className="text-xs text-muted-foreground">Allow reading and writing files</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label className="text-xs mb-2 block">Allowed Domains</Label>
              <div className="flex flex-wrap gap-1 mb-2">
                {settings.allowedDomains.length === 0 && <span className="text-xs text-muted-foreground">All domains allowed</span>}
                {settings.allowedDomains.map((d) => (
                  <Badge key={d} tone="success" className="text-[10px] flex items-center gap-1">
                    {d}
                    <button aria-label={`Remove ${d}`} type="button" onClick={() => updateField("allowedDomains", settings.allowedDomains.filter((x: string) => x !== d))}><X className="h-2.5 w-2.5" /></button>
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input value={newDomain} onChange={(e) => setNewDomain(e.target.value)} placeholder="example.com" className="text-xs font-mono" onKeyDown={(e) => { if (e.key === "Enter" && newDomain.trim()) { updateField("allowedDomains", [...settings.allowedDomains, newDomain.trim()]); setNewDomain(""); } }} />
                <Button aria-label="Add allowed domain" ghost size="icon" onClick={() => { if (newDomain.trim()) { updateField("allowedDomains", [...settings.allowedDomains, newDomain.trim()]); setNewDomain(""); } }}><Plus className="h-3.5 w-3.5" /></Button>
              </div>
            </div>
            <div>
              <Label className="text-xs mb-2 block">Blocked Domains</Label>
              <div className="flex flex-wrap gap-1 mb-2">
                {settings.blockedDomains.length === 0 && <span className="text-xs text-muted-foreground">No blocked domains</span>}
                {settings.blockedDomains.map((d) => (
                  <Badge key={d} tone="destructive" className="text-[10px] flex items-center gap-1">
                    {d}
                    <button aria-label={`Remove ${d}`} type="button" onClick={() => updateField("blockedDomains", settings.blockedDomains.filter((x: string) => x !== d))}><X className="h-2.5 w-2.5" /></button>
                  </Badge>
                ))}
              </div>
              <div className="flex gap-2">
                <Input value={newBlockDomain} onChange={(e) => setNewBlockDomain(e.target.value)} placeholder="malware.com" className="text-xs font-mono" onKeyDown={(e) => { if (e.key === "Enter" && newBlockDomain.trim()) { updateField("blockedDomains", [...settings.blockedDomains, newBlockDomain.trim()]); setNewBlockDomain(""); } }} />
                <Button aria-label="Add blocked domain" ghost size="icon" onClick={() => { if (newBlockDomain.trim()) { updateField("blockedDomains", [...settings.blockedDomains, newBlockDomain.trim()]); setNewBlockDomain(""); } }}><Plus className="h-3.5 w-3.5" /></Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Resource Limits */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-yellow-500" />
            <CardTitle className="text-sm">Resource Limits</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="grid gap-2">
            <Label className="text-xs">Max Memory (MB)</Label>
            <Input type="number" min={64} max={16384} step={64} value={settings.maxMemoryMb} onChange={(e) => updateField("maxMemoryMb", parseInt(e.target.value) || 512)} className="text-xs" />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs">Max CPU (%)</Label>
            <Input type="number" min={1} max={100} value={settings.maxCpuPercent} onChange={(e) => updateField("maxCpuPercent", parseInt(e.target.value) || 50)} className="text-xs" />
          </div>
          <div className="grid gap-2">
            <Label className="text-xs">Execution Timeout (s)</Label>
            <Input type="number" min={5} max={3600} value={settings.executionTimeout} onChange={(e) => updateField("executionTimeout", parseInt(e.target.value) || 300)} className="text-xs" />
          </div>
        </CardContent>
      </Card>

      {/* Approval Required */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-red-500" />
            <CardTitle className="text-sm">Approval Required Actions</CardTitle>
          </div>
          <CardDescription className="text-xs">These actions require manual approval before execution</CardDescription>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 mb-4">
            {APPROVAL_ACTIONS.map((action) => {
              const isRequired = settings.requireApprovalFor.includes(action);
              return (
                <button key={action} type="button" onClick={() => {
                  const next = isRequired ? settings.requireApprovalFor.filter((a: string) => a !== action) : [...settings.requireApprovalFor, action];
                  updateField("requireApprovalFor", next);
                }}
                  className={cn("flex items-center gap-1.5 p-2 border text-xs transition-colors text-left", isRequired ? "border-red-500/40 bg-red-500/10 text-red-500" : "border-border text-muted-foreground hover:border-muted-foreground/40")}
                >
                  {isRequired ? <Lock className="h-3 w-3 shrink-0" /> : <Unlock className="h-3 w-3 shrink-0" />}
                  <span className="truncate">{action.replace(/_/g, " ")}</span>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Audit & Secrets */}
      <Card>
        <CardHeader className="py-3 px-4">
          <div className="flex items-center gap-2">
            <Eye className="h-4 w-4 text-purple-500" />
            <CardTitle className="text-sm">Audit & Secrets</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <Switch checked={settings.auditLogging} onCheckedChange={(v: boolean) => updateField("auditLogging", v)} />
            <div>
              <Label>Audit Logging</Label>
              <p className="text-xs text-muted-foreground">Log all agent actions for review</p>
            </div>
          </div>
          <div className="grid gap-2">
            <Label className="text-xs">Secrets Scope</Label>
            <Select value={settings.secretsScope} onValueChange={(v: string) => updateField("secretsScope", v as typeof settings.secretsScope)}>
              <SelectOption value="agent">Agent-only</SelectOption>
              <SelectOption value="profile">Profile-wide</SelectOption>
              <SelectOption value="global">Global</SelectOption>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Save */}
      <div className="flex justify-end sticky bottom-4">
        <Button onClick={handleSave} disabled={saving} prefix={saving ? <Spinner /> : <Save />}>
          {saving ? "Saving..." : "Save Security Settings"}
        </Button>
      </div>
    </div>
  );
}
