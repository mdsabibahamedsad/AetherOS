import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Package,
  Code,
  Server,
  FileText,
  Wrench,
  Link,
  Plus,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  RotateCw,
  Settings,
  Play,
  BookOpen,
  Zap,
  ExternalLink,
  Download,
  Clipboard,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Wand2,
  Layers,
  TestTube,
  FileCode,
  Hammer,
  Eye,
  EyeOff,
  Terminal,
  Lightbulb,
  ArrowRight,
  Loader,
} from "lucide-react";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Button } from "@aetheros/ui/ui/components/button";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { Label } from "@aetheros/ui/ui/components/label";
import { Switch } from "@aetheros/ui/ui/components/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@aetheros/ui/ui/components/tabs";
import { Toast } from "@aetheros/ui/ui/components/toast";
import { useToast } from "@aetheros/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { ExtensionTemplate, BuildResult, ValidationResult, ValidationMessage } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, themedBody } from "@/lib/utils";

const TEMPLATE_ICONS: Record<string, typeof Package> = {
  plugin: Package,
  tool: Wrench,
  mcp_server: Server,
  skill: BookOpen,
  provider: Link,
  hook: Zap,
};

const TEMPLATE_TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  plugin: { color: "from-violet-500 to-purple-600", label: "Plugin" },
  tool: { color: "from-blue-500 to-cyan-600", label: "Tool" },
  mcp_server: { color: "from-emerald-500 to-teal-600", label: "MCP Server" },
  skill: { color: "from-amber-500 to-orange-600", label: "Skill" },
  provider: { color: "from-pink-500 to-rose-600", label: "Provider" },
  hook: { color: "from-slate-500 to-gray-600", label: "Hook" },
};

type WizardStep = "template" | "config" | "manifest" | "build" | "test";

export default function ExtensionSdkPage() {
  const [templates, setTemplates] = useState<ExtensionTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<WizardStep>("template");
  const [selectedTemplate, setSelectedTemplate] = useState<ExtensionTemplate | null>(null);
  const [extName, setExtName] = useState("");
  const [extDescription, setExtDescription] = useState("");
  const [manifest, setManifest] = useState<Record<string, unknown>>({});
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [testOutput, setTestOutput] = useState<string>("");
  const [building, setBuilding] = useState(false);
  const [testing, setTesting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [hotReload, setHotReload] = useState(false);
  const [devMode, setDevMode] = useState(false);
  const [createdExt, setCreatedExt] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getExtensionTemplates();
      setTemplates(res.templates);
    } catch (e) {
      showToast(`Failed to load templates: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { void loadTemplates(); }, [loadTemplates]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 mr-3">
          <span className="text-xs text-muted-foreground">Hot Reload</span>
          <Switch checked={hotReload} onCheckedChange={async (v) => {
            try {
              await api.setHotReload(v);
              setHotReload(v);
            } catch { showToast("Failed to toggle hot reload", "error"); }
          }} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Dev Mode</span>
          <Switch checked={devMode} onCheckedChange={async (v) => {
            try {
              await api.setDevMode(v);
              setDevMode(v);
            } catch { showToast("Failed to toggle dev mode", "error"); }
          }} />
        </div>
        <Button ghost size="sm" onClick={() => void loadTemplates()}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, hotReload, devMode, showToast, loadTemplates]);

  const handleSelectTemplate = (template: ExtensionTemplate) => {
    setSelectedTemplate(template);
    setExtName("");
    setExtDescription("");
    setManifest({});
    setBuildResult(null);
    setValidationResult(null);
    setTestOutput("");
    setCreatedExt(null);
    setStep("config");
  };

  const handleCreate = async () => {
    if (!selectedTemplate || !extName.trim()) {
      showToast("Name is required", "error");
      return;
    }
    setBuilding(true);
    try {
      const res = await api.createExtension(selectedTemplate.id, extName.trim(), {
        description: extDescription.trim() || undefined,
      });
      setCreatedExt(res.name);
      showToast(`Created ${res.name}`, "success");
      setStep("manifest");
    } catch (e) {
      showToast(`Failed to create: ${e}`, "error");
    } finally {
      setBuilding(false);
    }
  };

  const handleValidate = async () => {
    if (!createdExt) return;
    setValidating(true);
    try {
      const res = await api.validateExtension(createdExt);
      setValidationResult(res);
    } catch (e) {
      showToast(`Validation failed: ${e}`, "error");
    } finally {
      setValidating(false);
    }
  };

  const handleBuild = async () => {
    if (!createdExt) return;
    setBuilding(true);
    try {
      const res = await api.buildExtension(createdExt);
      setBuildResult(res);
      if (res.success) {
        showToast("Build successful", "success");
        setStep("test");
      } else {
        showToast(`Build failed: ${res.errors.length} error(s)`, "error");
      }
    } catch (e) {
      showToast(`Build failed: ${e}`, "error");
    } finally {
      setBuilding(false);
    }
  };

  const handleTest = async () => {
    if (!createdExt) return;
    setTesting(true);
    try {
      const res = await api.runExtensionTests(createdExt);
      setTestOutput(res.output);
      showToast(
        `${res.passed} passed, ${res.failed} failed, ${res.skipped} skipped`,
        res.failed > 0 ? "error" : "success",
      );
    } catch (e) {
      showToast(`Tests failed: ${e}`, "error");
    } finally {
      setTesting(false);
    }
  };

  const handleGenerateDocs = async () => {
    if (!createdExt) return;
    try {
      const res = await api.generateExtensionDocs(createdExt);
      showToast(`Docs generated at ${res.path}`, "success");
    } catch (e) {
      showToast(`Failed to generate docs: ${e}`, "error");
    }
  };

  const handleReset = () => {
    setStep("template");
    setSelectedTemplate(null);
    setCreatedExt(null);
    setBuildResult(null);
    setValidationResult(null);
    setTestOutput("");
  };

  const STEPS: { id: WizardStep; label: string; icon: typeof Package }[] = [
    { id: "template", label: "Template", icon: Sparkles },
    { id: "config", label: "Configure", icon: Settings },
    { id: "manifest", label: "Manifest", icon: FileCode },
    { id: "build", label: "Build", icon: Hammer },
    { id: "test", label: "Test", icon: TestTube },
  ];

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Wizard steps */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const currentIdx = STEPS.findIndex((x) => x.id === step);
          const isActive = s.id === step;
          const isDone = i < currentIdx;
          return (
            <button
              key={s.id}
              onClick={() => isDone && setStep(s.id)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded text-xs font-medium whitespace-nowrap transition-colors",
                isActive && "bg-muted/30 text-foreground",
                isDone && "text-emerald-400 cursor-pointer hover:bg-muted/20",
                !isActive && !isDone && "text-muted-foreground/50",
              )}
            >
              {isDone ? <Check className="h-3 w-3" /> : <Icon className="h-3 w-3" />}
              {s.label}
              {i < STEPS.length - 1 && <ChevronRight className="h-3 w-3 text-muted-foreground/30 ml-1" />}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : step === "template" ? (
        /* Template Gallery */
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Wand2 className="h-4 w-4 text-primary" />
            <h3 className="font-mondwest text-display text-xs tracking-[0.12em] text-muted-foreground uppercase">
              Choose a Template
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {templates.map((tmpl) => {
              const Icon = TEMPLATE_ICONS[tmpl.type] ?? Package;
              const cfg = TEMPLATE_TYPE_CONFIG[tmpl.type] ?? { color: "from-neutral-500 to-slate-600", label: tmpl.type };
              return (
                <button
                  key={tmpl.id}
                  onClick={() => handleSelectTemplate(tmpl)}
                  className={cn(
                    "text-left group relative border border-border/30 bg-card/60 backdrop-blur-sm p-4",
                    "hover:border-border/60 hover:bg-card/80 transition-all duration-200",
                  )}
                >
                  <div className={cn("h-10 w-10 rounded-lg bg-gradient-to-br flex items-center justify-center mb-3 border border-border/20", cfg.color)}>
                    <Icon className="h-5 w-5 text-white" />
                  </div>
                  <h4 className="font-medium text-sm mb-1">{tmpl.name}</h4>
                  <p className="text-xs text-muted-foreground mb-2 line-clamp-2">{tmpl.description}</p>
                  <Badge tone="outline" className="text-[10px]">{cfg.label}</Badge>
                </button>
              );
            })}
          </div>
        </div>
      ) : step === "config" ? (
        /* Project Configuration */
        <Card>
          <CardHeader>
            <CardTitle>Configure Extension</CardTitle>
            <p className="text-xs text-muted-foreground">
              {selectedTemplate?.name} — {selectedTemplate?.description}
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid gap-2">
              <Label htmlFor="ext-name">Extension Name</Label>
              <Input
                id="ext-name"
                placeholder="my-awesome-plugin"
                value={extName}
                onChange={(e) => setExtName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ext-desc">Description (optional)</Label>
              <Input
                id="ext-desc"
                placeholder="A brief description of your extension"
                value={extDescription}
                onChange={(e) => setExtDescription(e.target.value)}
              />
            </div>
            {selectedTemplate && (
              <div className="flex flex-col gap-2">
                <p className="text-xs text-muted-foreground">Files to be created:</p>
                <div className="flex flex-wrap gap-1">
                  {selectedTemplate.files.map((f) => (
                    <Badge key={f} tone="outline" className="text-[10px] font-mono">{f}</Badge>
                  ))}
                </div>
              </div>
            )}
            <div className="flex justify-between mt-2">
              <Button ghost size="sm" onClick={handleReset}>
                Back
              </Button>
              <Button className="uppercase" size="sm" onClick={handleCreate} disabled={building} prefix={building ? <Spinner /> : undefined}>
                {building ? "Creating..." : "Create Extension"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : step === "manifest" ? (
        /* Manifest Editor */
        <Card>
          <CardHeader>
            <CardTitle>Manifest Editor</CardTitle>
            <p className="text-xs text-muted-foreground">
              Review and edit the extension manifest for {createdExt}
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="font-mono text-xs border border-border/30 bg-black/20 p-4 rounded max-h-80 overflow-y-auto">
              <pre>{JSON.stringify(manifest, null, 2) || "{ }"}</pre>
            </div>

            {validationResult && (
              <ValidationResultDisplay result={validationResult} />
            )}

            <div className="flex justify-between">
              <div className="flex gap-2">
                <Button ghost size="sm" onClick={() => setStep("config")}>
                  Back
                </Button>
                <Button ghost size="sm" onClick={handleValidate} disabled={validating} prefix={validating ? <Spinner /> : undefined}>
                  Validate
                </Button>
                <Button ghost size="sm" onClick={handleGenerateDocs}>
                  Generate Docs
                </Button>
              </div>
              <Button className="uppercase" size="sm" onClick={handleBuild} disabled={building} prefix={building ? <Spinner /> : undefined}>
                {building ? "Building..." : "Build"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : step === "build" ? (
        /* Build & Package */
        <Card>
          <CardHeader>
            <CardTitle>Build Results</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {buildResult ? (
              <>
                <div className={cn(
                  "flex items-center gap-3 p-4 rounded border",
                  buildResult.success ? "border-emerald-400/30 bg-emerald-400/5" : "border-red-400/30 bg-red-400/5",
                )}>
                  {buildResult.success ? (
                    <Check className="h-5 w-5 text-emerald-400" />
                  ) : (
                    <X className="h-5 w-5 text-red-400" />
                  )}
                  <div>
                    <p className="text-sm font-medium">
                      {buildResult.success ? "Build Successful" : "Build Failed"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Duration: {buildResult.duration_ms}ms
                      {buildResult.size_bytes && ` · Size: ${(buildResult.size_bytes / 1024).toFixed(1)} KB`}
                      {buildResult.output_path && ` · ${buildResult.output_path}`}
                    </p>
                  </div>
                </div>

                {buildResult.warnings.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-amber-400 mb-2">Warnings ({buildResult.warnings.length})</p>
                    {buildResult.warnings.map((w, i) => (
                      <p key={i} className="text-xs text-amber-400/80 py-0.5">{w}</p>
                    ))}
                  </div>
                )}

                {buildResult.errors.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-red-400 mb-2">Errors ({buildResult.errors.length})</p>
                    {buildResult.errors.map((e, i) => (
                      <p key={i} className="text-xs text-red-400/80 py-0.5">{e}</p>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="py-8 text-center text-sm text-muted-foreground">
                <Button className="uppercase" size="sm" onClick={handleBuild} disabled={building} prefix={building ? <Spinner /> : undefined}>
                  {building ? "Building..." : "Start Build"}
                </Button>
              </div>
            )}

            <div className="flex justify-between">
              <Button ghost size="sm" onClick={() => setStep("manifest")}>Back</Button>
              <div className="flex gap-2">
                <Button ghost size="sm" onClick={handleBuild} disabled={building} prefix={building ? <Spinner /> : undefined}>
                  Rebuild
                </Button>
                {buildResult?.success && (
                  <Button className="uppercase" size="sm" onClick={() => setStep("test")}>
                    Continue to Test
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : step === "test" ? (
        /* Test Runner */
        <Card>
          <CardHeader>
            <CardTitle>Test Runner</CardTitle>
            <p className="text-xs text-muted-foreground">Run tests for {createdExt}</p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {testOutput ? (
              <div className="font-mono text-xs bg-black/20 p-4 rounded max-h-80 overflow-y-auto border border-border/20">
                <pre className="whitespace-pre-wrap">{testOutput}</pre>
              </div>
            ) : (
              <div className="py-8 text-center">
                <Button className="uppercase" size="sm" onClick={handleTest} disabled={testing} prefix={testing ? <Spinner /> : <Play />}>
                  {testing ? "Running..." : "Run Tests"}
                </Button>
              </div>
            )}

            <div className="flex justify-between">
              <Button ghost size="sm" onClick={() => setStep("build")}>Back</Button>
              <div className="flex gap-2">
                <Button ghost size="sm" onClick={handleTest} disabled={testing} prefix={testing ? <Spinner /> : undefined}>
                  Re-run
                </Button>
                <Button ghost size="sm" onClick={handleGenerateDocs}>
                  Generate Docs
                </Button>
                <Button ghost size="sm" onClick={handleReset}>
                  <Sparkles className="h-3.5 w-3.5 mr-1" />
                  New Extension
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Quick Start Guide */}
      <Card className="bg-card/40 border-dashed border-border/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="h-4 w-4 text-amber-400" />
            <h4 className="text-xs font-medium">Quick Start Guide</h4>
          </div>
          <ol className="text-xs text-muted-foreground space-y-1 ml-5 list-decimal">
            <li>Choose a template that matches your extension type</li>
            <li>Configure your extension name and description</li>
            <li>Review and edit the auto-generated manifest</li>
            <li>Build your extension (validates and packages it)</li>
            <li>Run tests to verify everything works</li>
            <li>Enable Hot Reload for instant development feedback</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}

function ValidationResultDisplay({ result }: { result: ValidationResult }) {
  if (!result.errors.length && !result.warnings.length) {
    return (
      <div className="flex items-center gap-2 text-emerald-400 text-xs">
        <Check className="h-3.5 w-3.5" />
        Manifest is valid
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {result.errors.map((err, i) => (
        <ValidationMessageRow key={`err-${i}`} msg={err} type="error" />
      ))}
      {result.warnings.map((warn, i) => (
        <ValidationMessageRow key={`warn-${i}`} msg={warn} type="warning" />
      ))}
      {result.info.map((inf, i) => (
        <ValidationMessageRow key={`info-${i}`} msg={inf} type="info" />
      ))}
    </div>
  );
}

function ValidationMessageRow({ msg, type }: { msg: ValidationMessage; type: "error" | "warning" | "info" }) {
  const iconMap = {
    error: X,
    warning: AlertTriangle,
    info: AlertTriangle,
  };
  const colorMap = {
    error: "text-red-400 border-red-400/20 bg-red-400/5",
    warning: "text-amber-400 border-amber-400/20 bg-amber-400/5",
    info: "text-blue-400 border-blue-400/20 bg-blue-400/5",
  };
  const Icon = iconMap[type];

  return (
    <div className={cn("flex items-start gap-2 p-2 rounded border text-xs", colorMap[type])}>
      <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0" />
      <div>
        <span className="font-medium">{msg.code}</span>
        {msg.file && (
          <span className="ml-1 opacity-70">{msg.file}:{msg.line}:{msg.column}</span>
        )}
        <p>{msg.message}</p>
      </div>
    </div>
  );
}
