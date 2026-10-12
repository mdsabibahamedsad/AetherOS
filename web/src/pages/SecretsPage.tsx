import { useEffect, useState } from "react";
import {
  KeyRound,
  Plus,
  Trash2,
  RefreshCw,
  Eye,
  EyeOff,
  Copy,
  Check,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Button } from "@nous-research/ui/ui/components/button";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface SecretEntry {
  name: string;
  category: string;
  description: string;
  created_at: number;
  updated_at: number;
  expires_at: number;
}

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<SecretEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newCategory, setNewCategory] = useState("generic");
  const [newDesc, setNewDesc] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(null);
    return () => setEnd(null);
  }, [setEnd]);

  const fetchSecrets = () => {
    setLoading(true);
    api.listSecrets()
      .then((data) => setSecrets(data.secrets ?? []))
      .catch(() => showToast("Failed to load secrets", "error"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchSecrets(); }, []);

  const handleStore = async () => {
    if (!newName || !newValue) return;
    try {
      await api.storeSecret(newName, newValue, newCategory, newDesc);
      showToast(`Secret "${newName}" stored`, "success");
      setNewName("");
      setNewValue("");
      setNewDesc("");
      setShowForm(false);
      fetchSecrets();
    } catch (e) {
      showToast(`Failed to store secret: ${e}`, "error");
    }
  };

  const handleDelete = async (name: string) => {
    try {
      await api.deleteSecret(name);
      showToast(`Secret "${name}" deleted`, "success");
      fetchSecrets();
    } catch (e) {
      showToast(`Failed to delete: ${e}`, "error");
    }
  };

  const handleReveal = async (name: string) => {
    if (revealed[name]) return;
    try {
      const result = await api.retrieveSecret(name);
      setRevealed((prev) => ({ ...prev, [name]: result.value }));
      setTimeout(() => {
        setRevealed((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
      }, 30000);
    } catch (e) {
      showToast(`Failed to retrieve: ${e}`, "error");
    }
  };

  const handleCopy = async (name: string) => {
    const val = revealed[name];
    if (!val) return;
    try {
      await navigator.clipboard.writeText(val);
      setCopiedId(name);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      showToast("Failed to copy", "error");
    }
  };

  const categoryBadge = (cat: string) => {
    const tones: Record<string, "warning" | "success" | "secondary" | "info"> = {
      api_key: "warning",
      oauth_token: "info",
      password: "destructive",
      ssh_key: "info",
    };
    return <Badge tone={tones[cat] ?? "secondary"} className="text-[10px]">{cat.replace(/_/g, " ")}</Badge>;
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
          <KeyRound className="h-5 w-5 text-midground" />
          <h1 className="text-lg font-bold">Secrets Manager</h1>
          <Badge tone="secondary" className="text-xs">{secrets.length} stored</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button aria-label="Refresh" ghost size="icon" onClick={fetchSecrets} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={() => setShowForm(!showForm)} prefix={<Plus className="h-3.5 w-3.5" />}>
            Add Secret
          </Button>
        </div>
      </div>

      {secrets.length === 0 && !showForm && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-sm text-muted-foreground">
            <KeyRound className="h-8 w-8 mb-3 opacity-30" />
            <p>No secrets stored yet.</p>
            <p className="text-xs mt-1">Click "Add Secret" to securely store API keys, tokens, and passwords.</p>
          </CardContent>
        </Card>
      )}

      {/* Store form */}
      {showForm && (
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Store New Secret
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input placeholder="Secret name (e.g. github_token)" value={newName} onChange={(e) => setNewName(e.target.value)} />
              <select
                className="flex h-9 w-full bg-transparent border border-border px-3 py-1 text-sm focus:outline-none"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              >
                <option value="api_key">API Key</option>
                <option value="oauth_token">OAuth Token</option>
                <option value="password">Password</option>
                <option value="ssh_key">SSH Key</option>
                <option value="jwt_token">JWT Token</option>
                <option value="generic">Generic</option>
              </select>
            </div>
            <Input placeholder="Secret value" type="password" value={newValue} onChange={(e) => setNewValue(e.target.value)} />
            <Input placeholder="Description (optional)" value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
            <div className="flex justify-end gap-2">
              <Button ghost size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
              <Button size="sm" onClick={handleStore} disabled={!newName || !newValue}>Store</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Secrets list */}
      <div className="space-y-2">
        {secrets.map((secret) => (
          <div key={secret.name} className="flex items-center gap-3 border border-border bg-muted/20 px-4 py-3 hover:bg-muted/40 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm truncate">{secret.name}</span>
                {categoryBadge(secret.category)}
                {secret.expires_at > 0 && secret.expires_at < Date.now() / 1000 && (
                  <AlertTriangle className="h-3 w-3 text-destructive shrink-0" title="Expired" />
                )}
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                {secret.description && <span className="truncate">{secret.description}</span>}
                <span>Updated {new Date(secret.updated_at * 1000).toLocaleDateString()}</span>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {revealed[secret.name] ? (
                <>
                  <code className="text-xs font-mono bg-muted px-2 py-1 max-w-[120px] truncate">{revealed[secret.name]}</code>
                  <Button aria-label="Copy" ghost size="icon" onClick={() => handleCopy(secret.name)} title="Copy">
                    {copiedId === secret.name ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                  </Button>
                  <Button aria-label="Hide" ghost size="icon" onClick={() => setRevealed((prev) => { const n = { ...prev }; delete n[secret.name]; return n; })} title="Hide">
                    <EyeOff className="h-3.5 w-3.5" />
                  </Button>
                </>
              ) : (
                <Button aria-label="Reveal" ghost size="icon" onClick={() => handleReveal(secret.name)} title="Reveal">
                  <Eye className="h-3.5 w-3.5" />
                </Button>
              )}
              <Button aria-label="Delete" ghost size="icon" onClick={() => handleDelete(secret.name)} title="Delete">
                <Trash2 className="h-3.5 w-3.5 text-destructive/70 hover:text-destructive" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
