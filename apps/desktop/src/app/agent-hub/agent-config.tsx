import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { type AgentConfig, type AgentTemplate, saveAgentConfig, TEMPLATE_LABELS } from '@/store/agent-hub'

interface AgentConfigPanelProps {
  agent: AgentConfig
  onBack: () => void
}

const MODEL_PROVIDERS = [
  { slug: '', name: 'Auto (use default)' },
  { slug: 'openai', name: 'OpenAI' },
  { slug: 'anthropic', name: 'Anthropic' },
  { slug: 'gemini', name: 'Google Gemini' },
  { slug: 'openrouter', name: 'OpenRouter' },
  { slug: 'deepseek', name: 'DeepSeek' },
  { slug: 'mistral', name: 'Mistral' },
  { slug: 'groq', name: 'Groq' },
  { slug: 'ollama', name: 'Ollama' },
  { slug: 'local', name: 'Local' }
]

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  '': [],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-sonnet-4', 'claude-haiku-3.5', 'claude-opus-4'],
  gemini: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
  openrouter: ['auto'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  mistral: ['mistral-large', 'mistral-medium', 'mistral-small'],
  groq: ['mixtral-8x7b', 'llama3-70b', 'llama3-8b'],
  ollama: ['llama3', 'mistral', 'codellama', 'mixtral'],
  local: ['custom-model']
}

export function AgentConfigPanel({ agent, onBack }: AgentConfigPanelProps) {
  const [config, setConfig] = useState<AgentConfig>({ ...agent })
  const [activeSection, setActiveSection] = useState<string>('general')

  const update = (update: Partial<AgentConfig>) => setConfig({ ...config, ...update })

  const providerModels = MODELS_BY_PROVIDER[config.model.provider] || []

  const sections = [
    { id: 'general', label: 'General' },
    { id: 'prompt', label: 'System Prompt' },
    { id: 'model', label: 'Model' },
    { id: 'memory', label: 'Memory' },
    { id: 'tools', label: 'Tools' },
    { id: 'permissions', label: 'Permissions' },
    { id: 'workspace', label: 'Workspace' }
  ]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 border-b px-6 py-3">
        <button className="text-muted-foreground hover:text-foreground" onClick={onBack} type="button">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1">
          <h2 className="font-semibold">{config.name}</h2>
          <p className="text-xs text-muted-foreground">{TEMPLATE_LABELS[config.template]} · {config.status}</p>
        </div>
        <Button onClick={onBack} size="sm" variant="outline">Cancel</Button>
        <Button onClick={() => { saveAgentConfig(config); onBack() }} size="sm">Save</Button>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav className="w-44 shrink-0 space-y-1 border-r p-3">
          {sections.map(s => (
            <button
              className={cn('w-full rounded-lg px-3 py-2 text-left text-sm transition-colors', activeSection === s.id ? 'bg-accent font-medium' : 'text-muted-foreground hover:bg-accent/50')}
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              type="button"
            >
              {s.label}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-2xl space-y-6">
            {activeSection === 'general' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">General</h3>
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input onChange={e => update({ name: e.target.value })} value={config.name} />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input onChange={e => update({ description: e.target.value })} value={config.description} />
                </div>
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select onValueChange={v => update({ template: v as AgentTemplate })} value={config.template}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(TEMPLATE_LABELS).map(([key, label]) => (
                        <SelectItem key={key} value={key}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {activeSection === 'prompt' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">System Prompt</h3>
                <div className="space-y-2">
                  <Label>System Prompt</Label>
                  <p className="text-xs text-muted-foreground">Defines the agent's behavior, personality, and constraints</p>
                  <Textarea
                    className="font-mono text-sm resize-none"
                    onChange={e => update({ systemPrompt: e.target.value })}
                    rows={12}
                    value={config.systemPrompt}
                  />
                </div>
              </div>
            )}

            {activeSection === 'model' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Model Configuration</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Provider</Label>
                    <Select onValueChange={v => update({ model: { ...config.model, provider: v, model: '' } })} value={config.model.provider}>
                      <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                      <SelectContent>
                        {MODEL_PROVIDERS.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Select onValueChange={v => update({ model: { ...config.model, model: v } })} value={config.model.model}>
                      <SelectTrigger><SelectValue placeholder={config.model.provider ? 'Select model' : 'Select provider first'} /></SelectTrigger>
                      <SelectContent>
                        {providerModels.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Fallback Model</Label>
                    <Select onValueChange={v => update({ model: { ...config.model, fallbackModel: v || null } })} value={config.model.fallbackModel ?? ''}>
                      <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                      <SelectContent>
                        {providerModels.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Reasoning Level</Label>
                    <Select onValueChange={v => update({ model: { ...config.model, reasoningLevel: v as AgentConfig['model']['reasoningLevel'] } })} value={config.model.reasoningLevel}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Temperature</Label>
                    <Input className="font-mono" max={2} min={0} onChange={e => update({ model: { ...config.model, temperature: parseFloat(e.target.value) || 0.7 } })} step={0.1} type="number" value={config.model.temperature} />
                  </div>
                  <div className="space-y-2">
                    <Label>Max Tokens</Label>
                    <Input className="font-mono" max={128000} min={256} onChange={e => update({ model: { ...config.model, maxTokens: parseInt(e.target.value) || 4096 } })} step={256} type="number" value={config.model.maxTokens} />
                  </div>
                </div>
              </div>
            )}

            {activeSection === 'memory' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Memory</h3>
                <div className="space-y-3">
                  {([
                    ['workingMemory', 'Working Memory', 'Retain context during active conversations'],
                    ['longTermMemory', 'Long-term Memory', 'Remember information across sessions'],
                    ['knowledgeBase', 'Knowledge Base', 'Build and query a searchable knowledge base'],
                    ['conversationHistory', 'Conversation History', 'Store and reference past conversations'],
                    ['projectMemory', 'Project Memory', 'Maintain project-specific context']
                  ] as const).map(([key, label, desc]) => (
                    <div className="flex items-center justify-between rounded-lg border p-4" key={key}>
                      <div><Label className="text-base">{label}</Label><p className="text-sm text-muted-foreground">{desc}</p></div>
                      <Switch checked={config.memory[key]} onCheckedChange={v => update({ memory: { ...config.memory, [key]: v } })} />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeSection === 'tools' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Allowed Tools</h3>
                <div className="grid grid-cols-2 gap-3">
                  {([
                    ['fileSystem', 'File System'],
                    ['browser', 'Browser'],
                    ['git', 'Git'],
                    ['shell', 'Shell'],
                    ['python', 'Python'],
                    ['search', 'Search'],
                    ['codeEditing', 'Code Editing'],
                    ['mcpTools', 'MCP Tools'],
                    ['plugins', 'Plugins']
                  ] as const).map(([key, label]) => (
                    <div className="flex items-center justify-between rounded-lg border p-3" key={key}>
                      <Label className="text-sm">{label}</Label>
                      <Switch checked={config.tools[key]} onCheckedChange={v => update({ tools: { ...config.tools, [key]: v } })} />
                    </div>
                  ))}
                </div>
                {config.tools.customTools.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {config.tools.customTools.map(t => <Badge key={t} variant="secondary">{t}</Badge>)}
                  </div>
                )}
              </div>
            )}

            {activeSection === 'permissions' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Permissions</h3>
                <div className="space-y-3">
                  {([
                    ['internetAccess', 'Internet Access', 'Allow network requests and API calls'],
                    ['filesystemAccess', 'Filesystem Access', 'Allow reading and writing files'],
                    ['terminalAccess', 'Terminal Access', 'Allow executing shell commands'],
                    ['browserAccess', 'Browser Access', 'Allow automated web browsing'],
                    ['pluginAccess', 'Plugin Access', 'Allow loading and using plugins'],
                    ['sandbox', 'Sandbox', 'Run in isolated sandbox environment']
                  ] as const).map(([key, label, desc]) => (
                    <div className="flex items-center justify-between rounded-lg border p-4" key={key}>
                      <div><Label className="text-base">{label}</Label><p className="text-sm text-muted-foreground">{desc}</p></div>
                      <Switch checked={config.permissions[key]} onCheckedChange={v => update({ permissions: { ...config.permissions, [key]: v } })} />
                    </div>
                  ))}
                  <div className="space-y-2 pt-2">
                    <Label>Execution Limit (calls per run)</Label>
                    <Input className="font-mono max-w-[200px]" max={1000} min={1} onChange={e => update({ permissions: { ...config.permissions, executionLimit: parseInt(e.target.value) || 100 } })} type="number" value={config.permissions.executionLimit} />
                  </div>
                </div>
              </div>
            )}

            {activeSection === 'workspace' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Workspace</h3>
                <div className="space-y-2">
                  <Label>Workspace Path</Label>
                  <Input className="font-mono text-sm" onChange={e => update({ workspace: { ...config.workspace, path: e.target.value } })} placeholder="~/aetheros/agents/my-agent" value={config.workspace.path} />
                </div>
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div><Label className="text-base">Isolated Workspace</Label><p className="text-sm text-muted-foreground">Keep agent files separate from other agents</p></div>
                  <Switch checked={config.workspace.isolated} onCheckedChange={v => update({ workspace: { ...config.workspace, isolated: v } })} />
                </div>
                <div className="space-y-2">
                  <Label>Max Storage (MB)</Label>
                  <Input className="font-mono max-w-[200px]" onChange={e => update({ workspace: { ...config.workspace, maxStorageMb: parseInt(e.target.value) || 500 } })} type="number" value={config.workspace.maxStorageMb} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
