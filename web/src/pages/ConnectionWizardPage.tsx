import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Check,
  Home,
  Cloud,
  Server,
  Settings,
  Wifi,
  Shield,
  List,
  TestTube,
  FileCheck,
  Globe,
  Lock,
  Key,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { api } from "@/lib/api";
import { cn, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const STEPS = [
  { id: "type", label: "Connection Type", icon: Wifi },
  { id: "config", label: "Configuration", icon: Settings },
  { id: "scope", label: "Sync Scopes", icon: List },
  { id: "encryption", label: "Encryption", icon: Lock },
  { id: "test", label: "Test Connection", icon: TestTube },
  { id: "finish", label: "Summary", icon: FileCheck },
];

const CONNECTION_TYPES = [
  { id: "local", label: "Local Only", description: "Sync between processes on this machine", icon: Home },
  { id: "cloud", label: "Cloud Sync", description: "Sync via Aetheros Cloud relay", icon: Cloud },
  { id: "self_hosted", label: "Self-Hosted", description: "Your own sync server", icon: Server },
  { id: "custom", label: "Custom Server", description: "Any compatible sync endpoint", icon: Globe },
  { id: "remote", label: "Remote AetherOS Instance", description: "Connect to another AetherOS agent", icon: Settings },
];

const SYNC_SCOPES = [
  "settings", "agents", "workflows", "knowledge", "memory", "tools", "automations", "files", "skills",
];

export default function ConnectionWizardPage() {
  const [step, setStep] = useState(0);
  const [connType, setConnType] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [credentials, setCredentials] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [encryption, setEncryption] = useState(true);
  const [passphrase, setPassphrase] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; latency_ms: number; error?: string } | null>(null);
  const [completing, setCompleting] = useState(false);
  const { toast, showToast } = useToast();

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) => prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]);
  };

  const canNext = (): boolean => {
    switch (step) {
      case 0: return connType !== null;
      case 1: return connType === "local" || url.trim().length > 0;
      case 2: return selectedScopes.length > 0;
      case 3: return !encryption || passphrase.trim().length >= 8;
      default: return true;
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testConnection(url.trim() || "http://localhost");
      setTestResult(res);
      showToast(res.ok ? `Connection OK · ${res.latency_ms}ms` : `Failed: ${res.error}`, res.ok ? "success" : "error");
    } catch (e) {
      showToast(`Test failed: ${e}`, "error");
    } finally {
      setTesting(false);
    }
  };

  const handleFinish = async () => {
    setCompleting(true);
    try {
      await api.startSync();
      showToast("Connection configured successfully", "success");
      setStep(STEPS.length - 1);
    } catch (e) {
      showToast(`Failed to apply: ${e}`, "error");
    } finally {
      setCompleting(false);
    }
  };

  const StepIcon = STEPS[step].icon;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Progress Indicator */}
      <Card>
        <CardContent className="py-4 px-5">
          <div className="flex items-center justify-between">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const isActive = i === step;
              const isDone = i < step;
              return (
                <div key={s.id} className="flex items-center gap-2">
                  <button
                    onClick={() => { if (i < step) setStep(i); }}
                    className={cn(
                      "flex items-center gap-2 text-xs transition-colors",
                      isActive ? "text-foreground" : isDone ? "text-emerald-400 cursor-pointer hover:text-emerald-300" : "text-muted-foreground cursor-default",
                    )}
                    disabled={i > step}
                  >
                    <div className={cn(
                      "h-7 w-7 rounded-full flex items-center justify-center border",
                      isActive ? "border-primary bg-primary/10" :
                      isDone ? "border-emerald-400 bg-emerald-400/10" :
                      "border-border/30",
                    )}>
                      {isDone ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                    </div>
                    <span className="hidden sm:inline">{s.label}</span>
                  </button>
                  {i < STEPS.length - 1 && (
                    <div className={cn("w-8 h-px mx-1", i < step ? "bg-emerald-400/50" : "bg-border/30")} />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <StepIcon className="h-4 w-4" />
            Step {step + 1}: {STEPS[step].label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Step 1: Connection Type */}
          {step === 0 && (
            <div className="grid gap-3">
              {CONNECTION_TYPES.map((t) => {
                const Icon = t.icon;
                const isSelected = connType === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setConnType(t.id)}
                    className={cn(
                      "flex items-center gap-4 p-4 rounded-lg border text-left transition-all",
                      isSelected ? "border-primary bg-primary/5" : "border-border/20 hover:border-border/50",
                    )}
                  >
                    <div className={cn("h-10 w-10 rounded-lg flex items-center justify-center border border-border/20",
                      isSelected ? "bg-primary/20" : "bg-card",
                    )}>
                      <Icon className={cn("h-5 w-5", isSelected ? "text-primary" : "text-muted-foreground")} />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{t.label}</p>
                      <p className="text-xs text-muted-foreground">{t.description}</p>
                    </div>
                    {isSelected && (
                      <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center">
                        <Check className="h-3.5 w-3.5 text-primary-foreground" />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}

          {/* Step 2: Configuration */}
          {step === 1 && (
            <div className="grid gap-4 max-w-lg">
              {connType !== "local" && (
                <div className="grid gap-2">
                  <Label htmlFor="wizard-url">Server URL</Label>
                  <Input id="wizard-url" placeholder="https://sync.example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
                </div>
              )}
              <div className="grid gap-2">
                <Label htmlFor="wizard-creds">Credentials / Auth Token (optional)</Label>
                <Input id="wizard-creds" placeholder="token-xxx" value={credentials} onChange={(e) => setCredentials(e.target.value)} type="password" />
              </div>
              {connType === "local" && (
                <div className="text-xs text-muted-foreground p-3 bg-black/20 rounded border border-border/20">
                  Local-only mode: syncing will occur between processes on this machine. No network configuration needed.
                </div>
              )}
            </div>
          )}

          {/* Step 3: Sync Scopes */}
          {step === 2 && (
            <div className="grid gap-2 max-w-lg">
              {SYNC_SCOPES.map((scope) => (
                <button
                  key={scope}
                  onClick={() => toggleScope(scope)}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border text-left text-sm",
                    selectedScopes.includes(scope) ? "border-primary bg-primary/5" : "border-border/20",
                  )}
                >
                  <Switch checked={selectedScopes.includes(scope)} readOnly />
                  <span className="capitalize">{scope}</span>
                </button>
              ))}
              {selectedScopes.length === 0 && (
                <p className="text-xs text-muted-foreground">Select at least one scope to sync</p>
              )}
            </div>
          )}

          {/* Step 4: Encryption */}
          {step === 3 && (
            <div className="grid gap-4 max-w-lg">
              <div className="flex items-center gap-3">
                <Switch checked={encryption} onCheckedChange={setEncryption} />
                <div>
                  <p className="text-sm font-medium">Enable end-to-end encryption</p>
                  <p className="text-xs text-muted-foreground">All sync data will be encrypted before transmission</p>
                </div>
              </div>
              {encryption && (
                <div className="grid gap-2">
                  <Label htmlFor="wizard-passphrase">Encryption Passphrase (min 8 characters)</Label>
                  <Input id="wizard-passphrase" type="password" placeholder="••••••••" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} />
                  <p className="text-xs text-muted-foreground">
                    This passphrase will be used to derive encryption keys. Keep it secure.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 5: Test Connection */}
          {step === 4 && (
            <div className="grid gap-4 max-w-lg">
              <Button onClick={handleTest} disabled={testing}>
                {testing ? <Spinner className="h-4 w-4 mr-1" /> : <TestTube className="h-4 w-4 mr-1" />}
                {testing ? "Testing..." : "Run Connection Test"}
              </Button>
              {testResult && (
                <div className={cn(
                  "p-4 rounded-lg border text-sm",
                  testResult.ok ? "bg-emerald-400/10 border-emerald-400/20 text-emerald-400" : "bg-red-400/10 border-red-400/20 text-red-400",
                )}>
                  <div className="flex items-center gap-2 mb-1">
                    {testResult.ok ? <Check className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                    <span className="font-medium">{testResult.ok ? "Connection Successful" : "Connection Failed"}</span>
                  </div>
                  {testResult.ok ? (
                    <p className="text-xs">Latency: {testResult.latency_ms}ms</p>
                  ) : (
                    <p className="text-xs">{testResult.error}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Step 6: Summary */}
          {step === 5 && (
            <div className="grid gap-4 max-w-lg">
              <div className="p-4 rounded-lg border border-border/20 bg-black/10">
                <h3 className="text-sm font-medium mb-3">Configuration Summary</h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-muted-foreground">Connection Type</span>
                    <p className="capitalize font-medium">{connType?.replace("_", " ") ?? "Not set"}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Server URL</span>
                    <p className="font-mono">{url || "Local only"}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Scopes</span>
                    <p>{selectedScopes.length} of {SYNC_SCOPES.length} selected</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Encryption</span>
                    <p>{encryption ? "Enabled" : "Disabled"}</p>
                  </div>
                  {testResult && (
                    <div className="col-span-2">
                      <span className="text-muted-foreground">Test Result</span>
                      <p className={testResult.ok ? "text-emerald-400" : "text-red-400"}>
                        {testResult.ok ? `${testResult.latency_ms}ms latency` : testResult.error}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          ghost
          size="sm"
          onClick={() => setStep((p) => Math.max(0, p - 1))}
          disabled={step === 0}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button size="sm" onClick={() => setStep((p) => p + 1)} disabled={!canNext()}>
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        ) : (
          <Button size="sm" onClick={handleFinish} disabled={completing}>
            {completing ? <Spinner className="h-4 w-4 mr-1" /> : <Check className="h-4 w-4 mr-1" />}
            {completing ? "Applying..." : "Finish"}
          </Button>
        )}
      </div>
    </div>
  );
}
