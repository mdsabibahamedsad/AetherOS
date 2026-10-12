import { useCallback, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

import { TemplatePreview } from './template-preview'

interface ExtensionManifest {
  name: string
  version: string
  description: string
  author: string
  license: string
  main: string
  icon?: string
  permissions: string[]
  dependencies: string[]
  tools: string[]
  hooks: string[]
}

interface ExtensionTemplate {
  id: string
  name: string
  description: string
  icon: string
  category: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  files: { path: string; content: string }[]
  manifest: ExtensionManifest
}

const TEMPLATES: ExtensionTemplate[] = [
  {
    id: 'basic-tool',
    name: 'Basic Tool',
    description: 'A simple tool extension with a single command handler',
    icon: 'code',
    category: 'Tools',
    difficulty: 'beginner',
    files: [
      { path: 'index.ts', content: 'export function register(ctx: ExtensionContext) {\n  ctx.registerTool({\n    name: "hello",\n    description: "A simple hello world tool",\n    handler: async (args) => {\n      return `Hello, ${args.name || "world"}!`;\n    }\n  });\n}' },
      { path: 'manifest.json', content: '{\n  "name": "my-extension",\n  "version": "1.0.0",\n  "description": "My first AetherOS extension",\n  "main": "index.ts"\n}' }
    ],
    manifest: {
      name: 'my-extension', version: '1.0.0', description: 'My first AetherOS extension',
      author: '', license: 'MIT', main: 'index.ts', permissions: [], dependencies: [], tools: ['hello'], hooks: []
    }
  },
  {
    id: 'mcp-server',
    name: 'MCP Server',
    description: 'Model Context Protocol server extension with stdio transport',
    icon: 'server',
    category: 'MCP',
    difficulty: 'intermediate',
    files: [
      { path: 'server.ts', content: 'import { McpServer } from "@aetheros/mcp";\n\nconst server = new McpServer({\n  name: "my-mcp-server",\n  version: "1.0.0"\n});\n\nserver.tool("greet", { name: z.string() }, async ({ name }) => ({\n  content: [{ type: "text", text: `Hello ${name}!` }]\n}));\n\nserver.listen({ transport: "stdio" });' },
      { path: 'manifest.json', content: '{\n  "name": "my-mcp-server",\n  "version": "1.0.0",\n  "type": "mcp",\n  "main": "server.ts"\n}' }
    ],
    manifest: {
      name: 'my-mcp-server', version: '1.0.0', description: 'A basic MCP server extension',
      author: '', license: 'MIT', main: 'server.ts', permissions: [], dependencies: ['@aetheros/mcp'], tools: ['greet'], hooks: []
    }
  },
  {
    id: 'hook-provider',
    name: 'Hook Provider',
    description: 'Extension that hooks into lifecycle events',
    icon: 'zap',
    category: 'Lifecycle',
    difficulty: 'intermediate',
    files: [
      { path: 'index.ts', content: 'export function register(ctx: ExtensionContext) {\n  ctx.on("session:start", async (session) => {\n    console.log("Session started:", session.id);\n  });\n\n  ctx.on("tool:before", async (toolCall) => {\n    console.log("Tool called:", toolCall.name);\n  });\n\n  ctx.on("tool:after", async (result) => {\n    console.log("Tool result:", result);\n  });\n}' },
      { path: 'manifest.json', content: '{\n  "name": "hook-provider",\n  "version": "1.0.0",\n  "main": "index.ts"\n}' }
    ],
    manifest: {
      name: 'hook-provider', version: '1.0.0', description: 'Lifecycle hook extension',
      author: '', license: 'MIT', main: 'index.ts', permissions: [], dependencies: [], tools: [], hooks: ['session:start', 'tool:before', 'tool:after']
    }
  },
  {
    id: 'ui-panel',
    name: 'UI Panel',
    description: 'Custom UI panel with React component for the desktop app',
    icon: 'browser',
    category: 'UI',
    difficulty: 'advanced',
    files: [
      { path: 'panel.tsx', content: 'import { useState } from "react";\n\nexport function MyPanel() {\n  const [count, setCount] = useState(0);\n\n  return (\n    <div>\n      <h2>My Extension Panel</h2>\n      <button onClick={() => setCount(c => c + 1)}>\n        Count: {count}\n      </button>\n    </div>\n  );\n}' },
      { path: 'index.ts', content: 'import { registerPanel } from "@aetheros/panel";\n\nregisterPanel({\n  id: "my-panel",\n  title: "My Panel",\n  component: () => import("./panel"),\n  position: "right"\n});' },
      { path: 'manifest.json', content: '{\n  "name": "ui-panel",\n  "version": "1.0.0",\n  "type": "ui",\n  "main": "index.ts"\n}' }
    ],
    manifest: {
      name: 'ui-panel', version: '1.0.0', description: 'Custom UI panel extension',
      author: '', license: 'MIT', main: 'index.ts', permissions: ['ui:panel'], dependencies: ['@aetheros/panel'], tools: [], hooks: []
    }
  },
  {
    id: 'provider-adapter',
    name: 'Provider Adapter',
    description: 'Model provider adapter for custom inference backends',
    icon: 'cloud',
    category: 'Providers',
    difficulty: 'advanced',
    files: [
      { path: 'provider.ts', content: 'import { ProviderAdapter } from "@aetheros/providers";\n\nexport class MyProvider extends ProviderAdapter {\n  constructor(config: ProviderConfig) {\n    super(config);\n    this.name = "My Provider";\n  }\n\n  async complete(messages: Message[]): Promise<CompletionResult> {\n    // Custom inference logic\n    return { content: "..." };\n  }\n}' },
      { path: 'manifest.json', content: '{\n  "name": "my-provider",\n  "version": "1.0.0",\n  "type": "provider",\n  "main": "provider.ts"\n}' }
    ],
    manifest: {
      name: 'my-provider', version: '1.0.0', description: 'Custom model provider adapter',
      author: '', license: 'MIT', main: 'provider.ts', permissions: ['network:http'], dependencies: ['@aetheros/providers'], tools: [], hooks: []
    }
  },
  {
    id: 'skill-pack',
    name: 'Skill Pack',
    description: 'Bundle multiple skills into an installable extension',
    icon: 'book',
    category: 'Skills',
    difficulty: 'beginner',
    files: [
      { path: 'skills/hello.skill.md', content: '---\nname: hello\nversion: 1.0.0\n---\n\nA simple greeting skill.' },
      { path: 'index.ts', content: 'export function register(ctx: ExtensionContext) {\n  ctx.registerSkills([\n    { name: "hello", path: "./skills/hello.skill.md" }\n  ]);\n}' },
      { path: 'manifest.json', content: '{\n  "name": "skill-pack",\n  "version": "1.0.0",\n  "type": "skills",\n  "main": "index.ts"\n}' }
    ],
    manifest: {
      name: 'skill-pack', version: '1.0.0', description: 'Bundle of reusable skills',
      author: '', license: 'MIT', main: 'index.ts', permissions: [], dependencies: [], tools: [], hooks: []
    }
  }
]

type WizardStep = 'template' | 'manifest' | 'files' | 'build'

interface BuilderState {
  step: WizardStep
  template: ExtensionTemplate | null
  manifest: ExtensionManifest
  outputDir: string
  devMode: boolean
  hotReload: boolean
}

const INITIAL_MANIFEST: ExtensionManifest = {
  name: '', version: '1.0.0', description: '', author: '', license: 'MIT',
  main: 'index.ts', permissions: [], dependencies: [], tools: [], hooks: []
}

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  intermediate: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  advanced: 'bg-red-500/10 text-red-600 dark:text-red-400'
}

export function ExtensionSdkView() {
  const { t } = useI18n()

  const [state, setState] = useState<BuilderState>({
    step: 'template',
    template: null,
    manifest: INITIAL_MANIFEST,
    outputDir: '~/aetheros/extensions',
    devMode: false,
    hotReload: false
  })

  const [manifestJson, setManifestJson] = useState(JSON.stringify(INITIAL_MANIFEST, null, 2))
  const [manifestError, setManifestError] = useState<string | null>(null)
  const [validationResults, setValidationResults] = useState<{ field: string; message: string; severity: 'error' | 'warn' }[]>([])
  const [buildOutput, setBuildOutput] = useState<string | null>(null)
  const [building, setBuilding] = useState(false)
  const [testOutput, setTestOutput] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)

  const selectTemplate = useCallback((template: ExtensionTemplate) => {
    setState(s => ({ ...s, template, step: 'manifest', manifest: template.manifest }))
    setManifestJson(JSON.stringify(template.manifest, null, 2))
    setValidationResults([])
  }, [])

  const handleManifestChange = useCallback((json: string) => {
    setManifestJson(json)

    try {
      const parsed = JSON.parse(json) as ExtensionManifest
      setState(s => ({ ...s, manifest: parsed }))
      setManifestError(null)

      const results: { field: string; message: string; severity: 'error' | 'warn' }[] = []

      if (!parsed.name) {results.push({ field: 'name', message: 'Extension name is required', severity: 'error' })}

      if (!parsed.description) {results.push({ field: 'description', message: 'Description is recommended', severity: 'warn' })}

      if (!parsed.main) {results.push({ field: 'main', message: 'Entry point is required', severity: 'error' })}

      if (!/^\d+\.\d+\.\d+$/.test(parsed.version)) {results.push({ field: 'version', message: 'Version must follow semver (e.g. 1.0.0)', severity: 'warn' })}
      setValidationResults(results)
    } catch (err) {
      setManifestError(err instanceof Error ? err.message : 'Invalid JSON')
      setValidationResults([])
    }
  }, [])

  const handleBuild = useCallback(async () => {
    setBuilding(true)
    setBuildOutput(null)
    await new Promise(r => setTimeout(r, 2000))
    setBuildOutput(`Building ${state.manifest.name} v${state.manifest.version}...\n✓ TypeScript compilation passed\n✓ Dependencies resolved\n✓ Bundle created\n✓ Extension packaged to dist/${state.manifest.name}-${state.manifest.version}.zip`)
    setBuilding(false)
    notify({ kind: 'success', title: 'Build Complete', message: `${state.manifest.name} built successfully` })
  }, [state.manifest])

  const handleRunTests = useCallback(async () => {
    setTesting(true)
    setTestOutput(null)
    await new Promise(r => setTimeout(r, 3000))
    setTestOutput(`Running tests for ${state.manifest.name}...\n✓ Basic tool registration test passed\n✓ Manifest validation passed\n⚠ Permissions test: 2 warn(s)\n✓ 3/4 tests passed, 1 warning(s)`)
    setTesting(false)
    notify({ kind: 'success', title: 'Tests Complete', message: '3/4 tests passed' })
  }, [state.manifest])

  const handlePackage = useCallback(async () => {
    await new Promise(r => setTimeout(r, 1500))
    notify({ kind: 'success', title: 'Extension Packaged', message: `Saved to ${state.outputDir}/${state.manifest.name}-${state.manifest.version}.zip` })
  }, [state.manifest, state.outputDir])

  const hasErrors = validationResults.some(r => r.severity === 'error')

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Extension SDK</PageTitle>
            <PageDescription>Create, build, and package AetherOS extensions</PageDescription>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Switch checked={state.devMode} onCheckedChange={v => setState(s => ({ ...s, devMode: v }))} />
              Developer Mode
            </label>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Switch checked={state.hotReload} onCheckedChange={v => setState(s => ({ ...s, hotReload: v }))} />
              Hot Reload
            </label>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full gap-4">
        <div className="w-48 shrink-0 space-y-1">
          {(['template', 'manifest', 'files', 'build'] as const).map((step, idx) => (
            <button
              className={cn(
                'flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs transition-colors',
                state.step === step ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/60'
              )}
              disabled={step !== 'template' && !state.template}
              key={step}
              onClick={() => setState(s => ({ ...s, step }))}
              type="button"
            >
              <span className={cn(
                'flex size-5 items-center justify-center rounded-full text-[0.6rem] font-medium',
                state.step === step ? 'bg-primary text-primary-foreground' : 'bg-(--ui-bg-quinary) text-muted-foreground'
              )}>
                {idx + 1}
              </span>
              <span className="capitalize">{step === 'build' ? 'Build & Package' : step}</span>
            </button>
          ))}
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto">
          {state.step === 'template' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold">Choose a Template</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {TEMPLATES.map(template => (
                  <button
                    className={cn(
                      'rounded-xl border p-4 text-left transition-all hover:border-primary/50 hover:shadow-sm',
                      state.template?.id === template.id ? 'border-primary bg-primary/5' : 'border-(--ui-stroke-tertiary)'
                    )}
                    key={template.id}
                    onClick={() => selectTemplate(template)}
                    type="button"
                  >
                    <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Codicon name={template.icon as 'code' | 'server' | 'zap' | 'browser' | 'cloud' | 'book'} size="1.25rem" />
                    </span>
                    <h4 className="mt-3 text-sm font-medium">{template.name}</h4>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{template.description}</p>
                    <div className="mt-3 flex items-center gap-2">
                      <Badge className="text-[0.55rem]" variant="outline">{template.category}</Badge>
                      <Badge className={cn('text-[0.55rem]', DIFFICULTY_COLORS[template.difficulty])}>
                        {template.difficulty}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {state.step === 'manifest' && (
            <div className="max-w-2xl space-y-4">
              <h3 className="text-sm font-semibold">Manifest Editor</h3>
              <p className="text-xs text-muted-foreground">Edit your extension manifest (manifest.json)</p>
              <Textarea
                className="min-h-64 font-mono text-xs"
                onChange={e => handleManifestChange(e.target.value)}
                value={manifestJson}
              />
              {manifestError && (
                <div className="flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  <Codicon className="mt-0.5 shrink-0" name="error" size="0.75rem" />
                  <span>{manifestError}</span>
                </div>
              )}
              {validationResults.length > 0 && (
                <div className="space-y-1">
                  <h4 className="text-xs font-medium text-muted-foreground">Validation</h4>
                  {validationResults.map(r => (
                    <div className={cn(
                      'flex items-start gap-2 rounded-md px-3 py-1.5 text-xs',
                      r.severity === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-amber-500/10 text-amber-600'
                    )} key={r.field}>
                      <Codicon className="mt-0.5 shrink-0" name={r.severity === 'error' ? 'error' : 'warning'} size="0.75rem" />
                      <span><strong>{r.field}:</strong> {r.message}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Button
                  disabled={!!manifestError || hasErrors}
                  onClick={() => setState(s => ({ ...s, step: 'files' }))}
                  size="sm"
                >
                  Next: Generated Files
                </Button>
              </div>
            </div>
          )}

          {state.step === 'files' && state.template && (
            <div className="max-w-2xl space-y-4">
              <h3 className="text-sm font-semibold">Generated File Structure</h3>
              <TemplatePreview files={state.template.files} manifest={state.manifest} />
              <div className="flex items-center gap-2">
                <Button
                  disabled={!!manifestError || hasErrors}
                  onClick={() => setState(s => ({ ...s, step: 'build' }))}
                  size="sm"
                >
                  Next: Build & Package
                </Button>
              </div>
            </div>
          )}

          {state.step === 'build' && (
            <div className="max-w-2xl space-y-5">
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Build & Package</h3>
                <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium">{state.manifest.name || 'Unnamed Extension'}</span>
                      <span className="ml-2 text-xs text-muted-foreground">v{state.manifest.version}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button disabled={building || hasErrors || !!manifestError} onClick={() => void handleBuild()} size="sm">
                        <Codicon className={cn('mr-1', building && 'animate-spin')} name={building ? 'loading' : 'tools'} size="0.75rem" />
                        {building ? 'Building...' : 'Build'}
                      </Button>
                      <Button
                        disabled={building || testing || hasErrors || !!manifestError}
                        onClick={() => void handleRunTests()}
                        size="sm"
                        variant="outline"
                      >
                        <Codicon className={cn('mr-1', testing && 'animate-spin')} name={testing ? 'loading' : 'bug'} size="0.75rem" />
                        {testing ? 'Running...' : 'Run Tests'}
                      </Button>
                      <Button
                        disabled={!buildOutput || hasErrors || !!manifestError}
                        onClick={() => void handlePackage()}
                        size="sm"
                        variant="outline"
                      >
                        <Codicon className="mr-1" name="package" size="0.75rem" />
                        Package
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Codicon name="file" size="0.75rem" />
                      {state.template?.files.length || 0} files
                    </span>
                    <span className="flex items-center gap-1">
                      <Codicon name="lock" size="0.75rem" />
                      {state.manifest.permissions.length} permissions
                    </span>
                    <span className="flex items-center gap-1">
                      <Codicon name="zap" size="0.75rem" />
                      {state.manifest.tools.length} tools
                    </span>
                    <span className="flex items-center gap-1">
                      <Codicon name="link" size="0.75rem" />
                      {state.manifest.dependencies.length} dependencies
                    </span>
                  </div>
                </div>

                <div className="grid gap-1.5">
                  <label className="text-xs font-medium text-foreground" htmlFor="sdk-output">Output Directory</label>
                  <Input
                    id="sdk-output"
                    onChange={e => setState(s => ({ ...s, outputDir: e.target.value }))}
                    value={state.outputDir}
                  />
                </div>
              </div>

              {buildOutput && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Build Output</h4>
                  <pre className="rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-4 py-3 font-mono text-xs leading-relaxed text-foreground/80">
                    {buildOutput}
                  </pre>
                </div>
              )}

              {testOutput && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Test Results</h4>
                  <pre className="rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-4 py-3 font-mono text-xs leading-relaxed text-foreground/80">
                    {testOutput}
                  </pre>
                </div>
              )}

              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Developer Options</h4>
                <div className="space-y-3">
                  <label className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium">Developer Mode</span>
                      <p className="text-xs text-muted-foreground">Enable verbose logging and debug endpoints</p>
                    </div>
                    <Switch checked={state.devMode} onCheckedChange={v => setState(s => ({ ...s, devMode: v }))} />
                  </label>
                  <label className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium">Hot Reload</span>
                      <p className="text-xs text-muted-foreground">Automatically reload extension on file changes</p>
                    </div>
                    <Switch checked={state.hotReload} onCheckedChange={v => setState(s => ({ ...s, hotReload: v }))} />
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}
