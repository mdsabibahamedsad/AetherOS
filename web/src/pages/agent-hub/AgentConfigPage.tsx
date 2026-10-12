import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Settings, Terminal, Brain, BookOpen, Toolbox, Cpu,
  Workflow, Shield, Lock, ScrollText, BarChart3,
  Save, ChevronDown, ChevronRight, RefreshCw, Plus, X,
  Globe, Puzzle, Server, Clock, AlertTriangle, HelpCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Textarea } from "@/components/Textarea";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useAgentStore } from "@/store/agent-store";
import { useAgentHubLocal, KNOWLEDGE_SOURCE_TYPES, type KnowledgeSourceType } from "@/store/agent-hub-local";
import { cn } from "@/lib/utils";
import type { AgentConfig } from "@/lib/api";

type EditorTab =
  | "general" | "prompt" | "memory" | "knowledge" | "tools"
  | "models" | "automation" | "security" | "permissions" | "logs" | "analytics";

interface TabDef {
  key: EditorTab;
  label: string;
  icon: typeof Settings;
}

const TABS: TabDef[] = [
  { key: "general", label: "General", icon: Settings },
  { key: "prompt", label: "Prompt", icon: Terminal },
  { key: "memory", label: "Memory", icon: Brain },
  { key: "knowledge", label: "Knowledge", icon: BookOpen },
  { key: "tools", label: "Tools", icon: Toolbox },
  { key: "models", label: "Models", icon: Cpu },
  { key: "automation", label: "Automation", icon: Workflow },
  { key: "security", label: "Security", icon: Shield },
  { key: "permissions", label: "Permissions", icon: Lock },
  { key: "logs", label: "Logs", icon: ScrollText },
  { key: "analytics", label: "Analytics", icon: BarChart3 },
];

const DEFAULT_CONFIG: AgentConfig = {
  agent_id: "", model: "", provider: "", temperature: 0.7,
  max_iterations: 30, system_prompt: "", toolsets: [],
  memory_enabled: false, memory_provider: "",
  timeout_seconds: 300, max_concurrent_tasks: 5,
  allowed_tools: [], disabled_tools: [],
  environment_vars: {}, mcp_servers: [],
  plugin_configs: {}, automation_rules: [],
};

export default function AgentConfigPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { fetchConfig, saveConfig, configs, agents } = useAgentStore();
  const { getSecuritySettings, updateSecuritySettings, getAnalytics, updateAnalytics, addKnowledgeAttachment, knowledge } = useAgentHubLocal();
  const { toast, showToast } = useToast();
  const { setTitle } = usePageHeader();

  const [activeTab, setActiveTab] = useState<EditorTab>("general");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<AgentConfig>(DEFAULT_CONFIG);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newEnvKey, setNewEnvKey] = useState("");
  const [newEnvValue, setNewEnvValue] = useState("");
  const [newMcpServer, setNewMcpServer] = useState("");
  const [newAllowedTool, setNewAllowedTool] = useState("");
  const [newDisabledTool, setNewDisabledTool] = useState("");

  const security = id ? getSecuritySettings(id) : null;
  const analytics = id ? getAnalytics(id) : null;
  const agentKnowledge = id ? (knowledge[id] || []) : [];
  const agent = agents.find((a: { id: string }) => a.id === id);

  useEffect(() => {
    setTitle(agent ? `Config: ${agent.name}` : "Agent Configuration");
  }, [setTitle, agent]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true); setError(null);
    fetchConfig(id)
      .catch((err: unknown) => { if (!cancelled) setError((err as Error).message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id, fetchConfig]);

  useEffect(() => {
    if (id && configs[id]) setConfig(configs[id]);
  }, [id, configs]);

  const updateConfig = useCallback(<K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }, []);

  const addEnvVar = useCallback(() => {
    if (!newEnvKey.trim()) return;
    updateConfig("environment_vars", { ...config.environment_vars, [newEnvKey.trim()]: newEnvValue });
    setNewEnvKey(""); setNewEnvValue("");
  }, [newEnvKey, newEnvValue, config.environment_vars, updateConfig]);

  const removeEnvVar = useCallback((key: string) => {
    const { [key]: _, ...rest } = config.environment_vars;
    updateConfig("environment_vars", rest);
  }, [config.environment_vars, updateConfig]);

  const handleSave = useCallback(async () => {
    if (!id) return;
    setSaving(true);
    try {
      await saveConfig(id, config);
      showToast("Configuration saved", "success");
    } catch { showToast("Failed to save configuration", "error"); }
    finally { setSaving(false); }
  }, [id, config, saveConfig, showToast]);

  if (loading) return <div className="flex min-h-[60vh] items-center justify-center"><Spinner /></div>;
  if (error) return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader><CardTitle className="text-destructive text-sm">Error</CardTitle><CardDescription className="text-xs">{error}</CardDescription></CardHeader>
        <CardContent><Button size="sm" onClick={() => id && fetchConfig(id)} prefix={<RefreshCw />}>Retry</Button></CardContent>
      </Card>
    </div>
  );

  return (
    <div className="flex flex-col gap-4">
      <Toast toast={toast} />

      {/* Tab bar */}
      <div className="flex flex-wrap gap-px border-b border-border pb-px overflow-x-auto">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button key={key} type="button" onClick={() => setActiveTab(key)}
            className={cn("flex items-center gap-1.5 px-3 py-2 text-xs transition-colors border-b-2 -mb-px whitespace-nowrap shrink-0",
              activeTab === key ? "border-foreground text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="max-w-4xl">
        {activeTab === "general" && (
          <div className="flex flex-col gap-4">
            <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Agent Identity</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2"><Label className="text-xs">Agent ID</Label><Input value={id || ""} disabled className="text-xs font-mono" /></div>
                <div className="grid gap-2"><Label className="text-xs">Name</Label><Input value={agent?.name || ""} disabled className="text-xs" /></div>
                <div className="grid gap-2"><Label className="text-xs">Status</Label><Input value={agent?.status || ""} disabled className="text-xs" /></div>
                <div className="grid gap-2"><Label className="text-xs">Role</Label><Input value={agent?.role || ""} disabled className="text-xs" /></div>
              </CardContent>
            </Card>
            <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Timeouts & Concurrency</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2"><Label className="text-xs">Timeout (seconds)</Label>
                  <Input type="number" min={1} max={3600} value={config.timeout_seconds} onChange={(e) => updateConfig("timeout_seconds", parseInt(e.target.value) || 300)} className="text-xs" /></div>
                <div className="grid gap-2"><Label className="text-xs">Max Concurrent Tasks</Label>
                  <Input type="number" min={1} max={100} value={config.max_concurrent_tasks} onChange={(e) => updateConfig("max_concurrent_tasks", parseInt(e.target.value) || 5)} className="text-xs" /></div>
              </CardContent>
            </Card>
            <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Environment Variables</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="flex flex-col gap-2 mb-3">
                  {Object.keys(config.environment_vars).length === 0 && <span className="text-xs text-muted-foreground">No environment variables set.</span>}
                  {Object.entries(config.environment_vars).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-2 text-xs font-mono">
                      <span className="text-foreground">{key}</span><span>=</span>
                      <span className="text-muted-foreground truncate flex-1">{val}</span>
                      <button type="button" onClick={() => removeEnvVar(key)} className="text-destructive hover:text-destructive/80"><X className="h-3 w-3" /></button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="Key" value={newEnvKey} onChange={(e) => setNewEnvKey(e.target.value)} className="text-xs font-mono flex-1" />
                  <Input placeholder="Value" value={newEnvValue} onChange={(e) => setNewEnvValue(e.target.value)} className="text-xs font-mono flex-1" />
                  <Button size="sm" outlined onClick={addEnvVar}><Plus /></Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "prompt" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">System Prompt</CardTitle>
            <CardDescription className="text-xs">Define the core behavior and personality of this agent</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4">
              <Textarea value={config.system_prompt} onChange={(e) => updateConfig("system_prompt", e.target.value)}
                placeholder="You are a helpful AI agent..." className="min-h-[300px] font-mono text-xs" />
            </CardContent>
          </Card>
        )}

        {activeTab === "memory" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Memory Configuration</CardTitle>
            <CardDescription className="text-xs">Control how this agent stores and retrieves information</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4 space-y-4">
              <div className="flex items-center gap-3">
                <Switch checked={config.memory_enabled} onCheckedChange={(v: boolean) => updateConfig("memory_enabled", v)} />
                <div><Label>Enable Memory</Label><p className="text-xs text-muted-foreground">Allow agent to remember past conversations</p></div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2"><Label className="text-xs">Memory Provider</Label>
                  <Select value={config.memory_provider} onValueChange={(v: string) => updateConfig("memory_provider", v)}>
                    <SelectOption value="">Default</SelectOption>
                    <SelectOption value="honcho">Honcho</SelectOption>
                    <SelectOption value="mem0">Mem0</SelectOption>
                    <SelectOption value="supermemory">SuperMemory</SelectOption>
                    <SelectOption value="byterover">ByteRover</SelectOption>
                    <SelectOption value="hindsight">Hindsight</SelectOption>
                    <SelectOption value="holographic">Holographic</SelectOption>
                    <SelectOption value="retaindb">RetainDB</SelectOption>
                  </Select>
                </div>
                <div className="grid gap-2"><Label className="text-xs">Memory Types</Label>
                  <div className="flex flex-wrap gap-2">
                    {["conversation", "long_term", "workspace", "project"].map((type) => (
                      <Badge key={type} tone="secondary" className="text-[10px] cursor-pointer hover:bg-midground/20">{type}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "knowledge" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Knowledge Sources</CardTitle>
            <CardDescription className="text-xs">{agentKnowledge.length} source(s) attached to this agent</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4">
              {agentKnowledge.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-8">No knowledge sources. Add sources in the Knowledge page.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {agentKnowledge.map((k) => (
                    <div key={k.id} className="flex items-center gap-3 border border-border p-2 text-xs">
                      <Badge tone="secondary" className="text-[10px]">{k.type}</Badge>
                      <span className="font-medium truncate flex-1">{k.name}</span>
                      <Badge tone={k.status === "ready" ? "success" : k.status === "error" ? "destructive" : "warning"} className="text-[10px]">{k.status}</Badge>
                      <span className="text-muted-foreground">{k.chunkCount} chunks</span>
                    </div>
                  ))}
                </div>
              )}
              <Button size="sm" outlined className="mt-3" onClick={() => navigate("/agent-hub/knowledge")} prefix={<BookOpen />}>
                Manage Knowledge
              </Button>
            </CardContent>
          </Card>
        )}

        {activeTab === "tools" && (
          <div className="flex flex-col gap-4">
            <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Toolsets</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="flex flex-wrap gap-2 mb-3">
                  {config.toolsets.length === 0 && <span className="text-xs text-muted-foreground">No toolsets selected.</span>}
                  {config.toolsets.map((ts) => (
                    <Badge key={ts} tone="secondary" className="text-xs flex items-center gap-1">
                      {ts}
                      <button type="button" onClick={() => updateConfig("toolsets", config.toolsets.filter((t) => t !== ts))} className="hover:text-foreground"><X className="h-3 w-3" /></button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Select value="" onValueChange={(v: string) => { if (v && !config.toolsets.includes(v)) updateConfig("toolsets", [...config.toolsets, v]); }}>
                    <SelectOption value="">Add toolset...</SelectOption>
                    <SelectOption value="browser">Browser</SelectOption>
                    <SelectOption value="terminal">Terminal</SelectOption>
                    <SelectOption value="file">File</SelectOption>
                    <SelectOption value="web">Web</SelectOption>
                    <SelectOption value="search">Search</SelectOption>
                    <SelectOption value="code_execution">Code Execution</SelectOption>
                    <SelectOption value="memory">Memory</SelectOption>
                    <SelectOption value="delegation">Delegation</SelectOption>
                    <SelectOption value="vision">Vision</SelectOption>
                    <SelectOption value="messaging">Messaging</SelectOption>
                    <SelectOption value="cronjob">Cron Jobs</SelectOption>
                    <SelectOption value="kanban">Kanban</SelectOption>
                  </Select>
                </div>
              </CardContent>
            </Card>
            <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">MCP Servers</CardTitle></CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="flex flex-wrap gap-2 mb-3">
                  {config.mcp_servers.length === 0 && <span className="text-xs text-muted-foreground">No MCP servers configured.</span>}
                  {config.mcp_servers.map((s) => (
                    <Badge key={s} tone="secondary" className="text-xs flex items-center gap-1">
                      {s}
                      <button type="button" onClick={() => updateConfig("mcp_servers", config.mcp_servers.filter((x) => x !== s))} className="hover:text-foreground"><X className="h-3 w-3" /></button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="Add MCP server..." value={newMcpServer} onChange={(e) => setNewMcpServer(e.target.value)} className="text-xs font-mono"
                    onKeyDown={(e) => { if (e.key === "Enter" && newMcpServer.trim()) { updateConfig("mcp_servers", [...config.mcp_servers, newMcpServer.trim()]); setNewMcpServer(""); } }} />
                  <Button size="sm" outlined onClick={() => { if (newMcpServer.trim()) { updateConfig("mcp_servers", [...config.mcp_servers, newMcpServer.trim()]); setNewMcpServer(""); } }}><Plus /></Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "models" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Model Assignment</CardTitle>
            <CardDescription className="text-xs">Configure the AI model and provider for this agent</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2"><Label className="text-xs">Model</Label>
                <Select value={config.model} onValueChange={(v: string) => updateConfig("model", v)}>
                  <SelectOption value="">Select model...</SelectOption>
                  <SelectOption value="gpt-4o">GPT-4o</SelectOption>
                  <SelectOption value="gpt-4o-mini">GPT-4o Mini</SelectOption>
                  <SelectOption value="claude-3-5-sonnet">Claude 3.5 Sonnet</SelectOption>
                  <SelectOption value="claude-3-opus">Claude 3 Opus</SelectOption>
                  <SelectOption value="claude-3-haiku">Claude 3 Haiku</SelectOption>
                  <SelectOption value="deepseek-v3">DeepSeek V3</SelectOption>
                  <SelectOption value="gemini-2.5-pro">Gemini 2.5 Pro</SelectOption>
                </Select>
              </div>
              <div className="grid gap-2"><Label className="text-xs">Provider</Label>
                <Select value={config.provider} onValueChange={(v: string) => updateConfig("provider", v)}>
                  <SelectOption value="">Select provider...</SelectOption>
                  <SelectOption value="openai">OpenAI</SelectOption>
                  <SelectOption value="anthropic">Anthropic</SelectOption>
                  <SelectOption value="deepseek">DeepSeek</SelectOption>
                  <SelectOption value="google">Google</SelectOption>
                  <SelectOption value="openrouter">OpenRouter</SelectOption>
                </Select>
              </div>
              <div className="grid gap-2"><Label className="text-xs">Temperature ({config.temperature})</Label>
                <Input type="range" min={0} max={2} step={0.1} value={config.temperature} onChange={(e) => updateConfig("temperature", parseFloat(e.target.value) || 0)} className="text-xs" />
              </div>
              <div className="grid gap-2"><Label className="text-xs">Max Iterations</Label>
                <Input type="number" min={1} max={500} value={config.max_iterations} onChange={(e) => updateConfig("max_iterations", parseInt(e.target.value) || 30)} className="text-xs" />
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "automation" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Automation Rules</CardTitle>
            <CardDescription className="text-xs">{config.automation_rules.length} rule(s) configured</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4">
              {config.automation_rules.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-8">No automation rules. Create rules in the Automation Builder.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {config.automation_rules.map((rule, i) => (
                    <div key={i} className="flex items-center gap-3 border border-border p-2 text-xs">
                      <Badge tone="info" className="text-[10px]">{rule.trigger.type}</Badge>
                      <span className="text-muted-foreground flex-1">{rule.conditions.length} condition(s)</span>
                      <span className="text-muted-foreground">{rule.actions.length} action(s)</span>
                      <Badge tone={rule.enabled ? "success" : "secondary"} className="text-[10px]">{rule.enabled ? "Active" : "Disabled"}</Badge>
                    </div>
                  ))}
                </div>
              )}
              <Button size="sm" outlined className="mt-3" onClick={() => navigate("/agent-hub/automation")} prefix={<Workflow />}>
                Automation Builder
              </Button>
            </CardContent>
          </Card>
        )}

        {activeTab === "security" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Security Settings</CardTitle>
            <CardDescription className="text-xs">Sandbox, access control, and resource limits</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4 space-y-4">
              {security ? (
                <>
                  <div className="flex items-center gap-3">
                    <Switch checked={security.sandboxEnabled} onCheckedChange={(v: boolean) => id && updateSecuritySettings(id, { sandboxEnabled: v })} />
                    <div><Label>Sandbox</Label><p className="text-xs text-muted-foreground">Isolate agent execution</p></div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {["isolated", "restricted", "standard"].map((mode) => (
                      <button key={mode} type="button" onClick={() => id && updateSecuritySettings(id, { sandboxMode: mode as typeof security.sandboxMode })}
                        className={cn("p-3 border text-left text-xs transition-colors", security.sandboxMode === mode ? "border-foreground bg-foreground/5" : "border-border")}>
                        <div className="font-medium capitalize mb-1">{mode}</div>
                        <div className="text-muted-foreground">{mode === "isolated" ? "No network/FS" : mode === "restricted" ? "Limited access" : "Full + audit"}</div>
                      </button>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="flex items-center gap-3"><Switch checked={security.networkAccess} onCheckedChange={(v: boolean) => id && updateSecuritySettings(id, { networkAccess: v })} /><Label>Network Access</Label></div>
                    <div className="flex items-center gap-3"><Switch checked={security.filesystemAccess} onCheckedChange={(v: boolean) => id && updateSecuritySettings(id, { filesystemAccess: v })} /><Label>Filesystem Access</Label></div>
                  </div>
                </>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-8">Configure security in the Security page</p>
              )}
              <Button size="sm" outlined onClick={() => navigate("/agent-hub/security")} prefix={<Shield />}>
                Full Security Settings
              </Button>
            </CardContent>
          </Card>
        )}

        {activeTab === "permissions" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Tool Permissions</CardTitle>
            <CardDescription className="text-xs">Allowed tools: {config.allowed_tools.length} | Disabled tools: {config.disabled_tools.length}</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs mb-2 block">Allowed Tools</Label>
                <div className="flex flex-wrap gap-1 mb-2">
                  {config.allowed_tools.length === 0 && <span className="text-xs text-muted-foreground">All tools allowed (unless disabled).</span>}
                  {config.allowed_tools.map((t) => (
                    <Badge key={t} tone="success" className="text-[10px] flex items-center gap-1">
                      {t}
                      <button type="button" onClick={() => updateConfig("allowed_tools", config.allowed_tools.filter((x) => x !== t))}><X className="h-2.5 w-2.5" /></button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="tool_name" value={newAllowedTool} onChange={(e) => setNewAllowedTool(e.target.value)} className="text-xs font-mono" />
                  <Button size="sm" outlined onClick={() => { if (newAllowedTool.trim()) { updateConfig("allowed_tools", [...config.allowed_tools, newAllowedTool.trim()]); setNewAllowedTool(""); } }}><Plus /></Button>
                </div>
              </div>
              <div>
                <Label className="text-xs mb-2 block">Disabled Tools</Label>
                <div className="flex flex-wrap gap-1 mb-2">
                  {config.disabled_tools.length === 0 && <span className="text-xs text-muted-foreground">No tools disabled.</span>}
                  {config.disabled_tools.map((t) => (
                    <Badge key={t} tone="destructive" className="text-[10px] flex items-center gap-1">
                      {t}
                      <button type="button" onClick={() => updateConfig("disabled_tools", config.disabled_tools.filter((x) => x !== t))}><X className="h-2.5 w-2.5" /></button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input placeholder="tool_name" value={newDisabledTool} onChange={(e) => setNewDisabledTool(e.target.value)} className="text-xs font-mono" />
                  <Button size="sm" outlined onClick={() => { if (newDisabledTool.trim()) { updateConfig("disabled_tools", [...config.disabled_tools, newDisabledTool.trim()]); setNewDisabledTool(""); } }}><Plus /></Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "logs" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Agent Logs</CardTitle>
            <CardDescription className="text-xs">View runtime logs for this agent</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4">
              <Button size="sm" outlined onClick={() => navigate(`/agent-hub/logs?agent=${id}`)} prefix={<ScrollText />}>
                Open Log Viewer
              </Button>
            </CardContent>
          </Card>
        )}

        {activeTab === "analytics" && (
          <Card><CardHeader className="py-3 px-4"><CardTitle className="text-sm">Agent Analytics</CardTitle>
            <CardDescription className="text-xs">Usage metrics and performance data</CardDescription></CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              {analytics && analytics.totalSessions > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="border border-border p-3 text-center">
                    <p className="text-2xl font-bold">{analytics.totalSessions}</p>
                    <p className="text-xs text-muted-foreground">Sessions</p>
                  </div>
                  <div className="border border-border p-3 text-center">
                    <p className="text-2xl font-bold">${analytics.totalCost.toFixed(2)}</p>
                    <p className="text-xs text-muted-foreground">Total Cost</p>
                  </div>
                  <div className="border border-border p-3 text-center">
                    <p className="text-2xl font-bold">{(analytics.avgResponseTime / 1000).toFixed(1)}s</p>
                    <p className="text-xs text-muted-foreground">Avg Response</p>
                  </div>
                  <div className="border border-border p-3 text-center">
                    <p className="text-2xl font-bold">{analytics.topTools.length}</p>
                    <p className="text-xs text-muted-foreground">Tools Used</p>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-8">No analytics data yet. Visit the Analytics page for detailed metrics.</p>
              )}
              <Button size="sm" outlined onClick={() => navigate("/agent-hub/analytics")} prefix={<BarChart3 />}>
                Full Analytics Dashboard
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Save */}
      <div className="flex justify-end sticky bottom-4">
        <Button onClick={handleSave} disabled={saving} prefix={saving ? <Spinner /> : <Save />}>
          {saving ? "Saving..." : "Save Configuration"}
        </Button>
      </div>
    </div>
  );
}
