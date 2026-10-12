import { useEffect, useState } from "react";
import {
  Terminal,
  Plus,
  Trash2,
  RefreshCw,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Button } from "@nous-research/ui/ui/components/button";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { ConfirmDialog } from "@nous-research/ui/ui/components/confirm-dialog";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface SandboxInfo {
  name: string;
  active: boolean;
  backend: string;
  mode: string;
}

interface SandboxStats {
  total_sandboxes: number;
  active_sandboxes: number;
  backend: string;
}

export default function SandboxManagerPage() {
  const [sandboxes, setSandboxes] = useState<SandboxInfo[]>([]);
  const [stats, setStats] = useState<SandboxStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newBackend, setNewBackend] = useState("restricted_python");
  const [newMode, setNewMode] = useState("standard");
  const [newNetwork, setNewNetwork] = useState(false);
  const [destroyTarget, setDestroyTarget] = useState<string | null>(null);
  const [execTarget, setExecTarget] = useState<string | null>(null);
  const [execCommand, setExecCommand] = useState("");
  const [execOutput, setExecOutput] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(null);
    return () => setEnd(null);
  }, [setEnd]);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      api.getSandboxes().catch(() => ({ sandboxes: [] })),
      api.getSandboxStats().catch(() => null),
    ]).then(([s, st]) => {
      setSandboxes(s.sandboxes ?? []);
      setStats(st);
      setLoading(false);
    });
  };

  useEffect(() => { fetchData(); }, []);

  const handleCreate = async () => {
    if (!newName) return;
    try {
      await api.createSandbox(newName, newBackend, newMode, newNetwork);
      showToast(`Sandbox "${newName}" created`, "success");
      setNewName("");
      setShowCreate(false);
      fetchData();
    } catch (e) {
      showToast(`Failed to create: ${e}`, "error");
    }
  };

  const handleDestroy = async () => {
    if (!destroyTarget) return;
    try {
      await api.destroySandbox(destroyTarget);
      showToast(`Sandbox "${destroyTarget}" destroyed`, "success");
      setDestroyTarget(null);
      fetchData();
    } catch (e) {
      showToast(`Failed to destroy: ${e}`, "error");
    }
  };

  const handleExecute = async () => {
    if (!execTarget || !execCommand) return;
    try {
      const result = await api.executeSandbox(execTarget, execCommand);
      setExecOutput(result.output ?? result.error ?? "(no output)");
    } catch (e) {
      setExecOutput(`Error: ${e}`);
    }
  };

  const backendLabel = (b: string) => {
    const labels: Record<string, string> = {
      firejail: "Firejail",
      docker: "Docker",
      podman: "Podman",
      windows_sandbox: "Windows Sandbox",
      macos_sandbox: "macOS Sandbox",
      restricted_python: "Restricted Python",
      none: "None",
    };
    return labels[b] ?? b;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="h-5 w-5 text-midground" />
          <h1 className="text-lg font-bold">Sandbox Manager</h1>
          {stats && (
            <Badge tone={stats.active_sandboxes > 0 ? "success" : "secondary"} className="text-xs">
              {stats.active_sandboxes} active / {stats.total_sandboxes} total
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button aria-label="Refresh" ghost size="icon" onClick={fetchData} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} prefix={<Plus className="h-3.5 w-3.5" />}>
            Create Sandbox
          </Button>
        </div>
      </div>

      {/* Backend info */}
      {stats && (
        <div className="text-xs text-muted-foreground">
          Backend: <span className="font-mono">{backendLabel(stats.backend)}</span>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Plus className="h-4 w-4" />
              New Sandbox
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <Input placeholder="Sandbox name" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select className="flex h-9 w-full bg-transparent border border-border px-3 py-1 text-sm focus:outline-none" value={newBackend} onChange={(e) => setNewBackend(e.target.value)}>
                <option value="restricted_python">Restricted Python</option>
                <option value="firejail">Firejail (Linux)</option>
                <option value="docker">Docker</option>
                <option value="podman">Podman</option>
                <option value="none">None (no isolation)</option>
              </select>
              <select className="flex h-9 w-full bg-transparent border border-border px-3 py-1 text-sm focus:outline-none" value={newMode} onChange={(e) => setNewMode(e.target.value)}>
                <option value="standard">Standard</option>
                <option value="full">Full Isolation</option>
                <option value="relaxed">Relaxed</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={newNetwork} onChange={(e) => setNewNetwork(e.target.checked)} className="accent-midground" />
              Enable network access
            </label>
            <div className="flex justify-end gap-2">
              <Button ghost size="sm" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={!newName}>Create</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sandbox list */}
      {sandboxes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-sm text-muted-foreground">
            <Terminal className="h-8 w-8 mb-3 opacity-30" />
            <p>No sandboxes created yet.</p>
            <p className="text-xs mt-1">Click "Create Sandbox" to get started.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {sandboxes.map((sb) => (
            <div key={sb.name} className="border border-border bg-muted/20 px-4 py-3 hover:bg-muted/40 transition-colors">
              <div className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{sb.name}</span>
                    <Badge tone={sb.active ? "success" : "secondary"} className="text-[9px]">
                      {sb.active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground mt-0.5">
                    <span>{backendLabel(sb.backend)}</span>
                    <span className="capitalize">· {sb.mode} mode</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button aria-label="Execute command" ghost size="icon" onClick={() => { setExecTarget(sb.name); setExecCommand(""); setExecOutput(null); }} title="Execute command">
                    <Play className="h-3.5 w-3.5" />
                  </Button>
                  <Button aria-label="Destroy" ghost size="icon" onClick={() => setDestroyTarget(sb.name)} title="Destroy">
                    <Trash2 className="h-3.5 w-3.5 text-destructive/70 hover:text-destructive" />
                  </Button>
                </div>
              </div>

              {/* Execute panel */}
              {execTarget === sb.name && (
                <div className="mt-3 pt-3 border-t border-border space-y-2">
                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Enter command..."
                      value={execCommand}
                      onChange={(e) => setExecCommand(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleExecute(); }}
                      className="text-xs font-mono"
                    />
                    <Button size="sm" onClick={handleExecute} disabled={!execCommand}>
                      Run
                    </Button>
                  </div>
                  {execOutput !== null && (
                    <pre className="text-[10px] font-mono bg-black/40 text-green-400/80 p-3 max-h-[200px] overflow-auto whitespace-pre-wrap">
                      {execOutput}
                    </pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={!!destroyTarget}
        onCancel={() => setDestroyTarget(null)}
        onConfirm={handleDestroy}
        title={`Destroy sandbox "${destroyTarget}"?`}
        description="This will terminate all running processes in the sandbox and clean up its resources. This action cannot be undone."
        destructive
        confirmLabel="Destroy"
      />
    </div>
  );
}
