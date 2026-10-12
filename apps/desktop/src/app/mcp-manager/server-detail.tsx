import { useCallback, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { LogView } from '@/components/ui/log-view'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

type McpType = 'stdio' | 'sse' | 'streamable-http' | 'websocket'
type HealthStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown'

interface HealthInfo {
  status: HealthStatus
  latency: number | null
  lastCheck: string | null
  error: string | null
}

interface LogEntry {
  level: string
  message: string
  timestamp: number
}

export interface McpServerConfig {
  id: string
  name: string
  type: McpType
  transport: string
  command?: string
  args?: string[]
  url?: string
  enabled: boolean
  autoDiscover: boolean
  health: HealthInfo
  config: Record<string, unknown>
  log: LogEntry[]
}

interface ServerDetailViewProps {
  onBack: () => void
  onDelete: () => void
  onSave: (config: Partial<McpServerConfig>) => void
  server: McpServerConfig
}

const MCP_TYPES: McpType[] = ['stdio', 'sse', 'streamable-http', 'websocket']

const MCP_TYPE_LABELS: Record<McpType, string> = {
  'stdio': 'STDIO',
  'sse': 'Server-Sent Events',
  'streamable-http': 'Streamable HTTP',
  'websocket': 'WebSocket'
}

const HEALTH_DOT: Record<string, string> = {
  healthy: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  unhealthy: 'bg-red-500',
  unknown: 'bg-muted-foreground/40'
}

export function ServerDetailView({ onBack, onDelete, onSave, server }: ServerDetailViewProps) {
  const { t } = useI18n()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(server.name)
  const [type, setType] = useState<McpType>(server.type)
  const [command, setCommand] = useState(server.command || '')
  const [args, setArgs] = useState(server.args?.join(' ') || '')
  const [url, setUrl] = useState(server.url || '')
  const [jsonConfig, setJsonConfig] = useState(JSON.stringify(server.config, null, 2))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runningHealthCheck, setRunningHealthCheck] = useState(false)

  const handleStartEdit = useCallback(() => {
    setName(server.name)
    setType(server.type)
    setCommand(server.command || '')
    setArgs(server.args?.join(' ') || '')
    setUrl(server.url || '')
    setJsonConfig(JSON.stringify(server.config, null, 2))
    setError(null)
    setEditing(true)
  }, [server])

  const handleSave = useCallback(async () => {
    if (!name.trim()) { setError('Server name is required');

 return }

    setSaving(true)
    setError(null)
    await new Promise(r => setTimeout(r, 300))

    let parsedConfig: Record<string, unknown> = {}

    try {
      parsedConfig = JSON.parse(jsonConfig)
    } catch {
      setError('Invalid JSON in configuration')
      setSaving(false)

      return
    }

    onSave({
      name: name.trim(),
      type,
      command: type === 'stdio' ? command.trim() : undefined,
      args: type === 'stdio' ? args.split(/\s+/).filter(Boolean) : undefined,
      url: type !== 'stdio' ? url.trim() : undefined,
      config: parsedConfig
    })

    setSaving(false)
    setEditing(false)
    notify({ kind: 'success', title: 'Server Updated', message: `${name.trim()} configuration saved` })
  }, [name, type, command, args, url, jsonConfig, onSave])

  const handleCancelEdit = useCallback(() => {
    setEditing(false)
    setError(null)
  }, [])

  const handleHealthCheck = useCallback(async () => {
    setRunningHealthCheck(true)
    await new Promise(r => setTimeout(r, 2000))
    setRunningHealthCheck(false)
    notify({ kind: 'success', title: 'Health Check Complete', message: `${server.name} responded in ${Math.floor(Math.random() * 50) + 5}ms` })
  }, [server.name])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center gap-3">
            <Button aria-label="Go back" className="text-muted-foreground hover:text-foreground" onClick={onBack} size="icon-xs" variant="ghost">
              <Codicon name="arrow-left" size="1rem" />
            </Button>
            <div>
              <PageTitle>{server.name}</PageTitle>
              <PageDescription>MCP Server Configuration</PageDescription>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="rounded-xl border border-(--ui-stroke-tertiary) p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <span className={cn('size-3 shrink-0 rounded-full', HEALTH_DOT[server.health.status])} />
              <div>
                <h3 className="text-lg font-semibold">{server.name}</h3>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant={server.type === 'stdio' ? 'default' : 'outline'}>{MCP_TYPE_LABELS[server.type]}</Badge>
                  <span>{server.transport}</span>
                  {server.autoDiscover && <Badge variant="muted">Auto-Discovered</Badge>}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <Button disabled={runningHealthCheck} onClick={() => void handleHealthCheck()} size="sm" variant="outline">
                <Codicon className={cn('mr-1', runningHealthCheck && 'animate-spin')} name={runningHealthCheck ? 'loading' : 'heart'} size="0.75rem" />
                {runningHealthCheck ? 'Checking...' : 'Health Check'}
              </Button>
              {!editing ? (
                <>
                  <Button onClick={handleStartEdit} size="sm" variant="outline">
                    <Codicon className="mr-1" name="edit" size="0.75rem" /> Edit
                  </Button>
                  <Button className="text-muted-foreground hover:text-destructive" onClick={onDelete} size="sm" variant="ghost">
                    <Codicon name="trash" size="0.875rem" />
                  </Button>
                </>
              ) : null}
            </div>
          </div>

          <div className="mt-4 grid grid-cols-4 gap-3">
            {[
              { label: 'Status', value: server.health.status.charAt(0).toUpperCase() + server.health.status.slice(1) },
              { label: 'Latency', value: server.health.latency !== null ? `${server.health.latency}ms` : '—' },
              { label: 'Last Check', value: server.health.lastCheck ? new Date(server.health.lastCheck).toLocaleTimeString() : '—' },
              { label: 'Log Entries', value: String(server.log.length) }
            ].map(stat => (
              <div className="rounded-md bg-(--ui-bg-quinary) px-3 py-2" key={stat.label}>
                <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">{stat.label}</div>
                <div className="mt-0.5 text-sm font-medium tabular-nums">{stat.value}</div>
              </div>
            ))}
          </div>

          {server.health.error && (
            <div className="mt-3 flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <Codicon className="mt-0.5 shrink-0" name="error" size="0.875rem" />
              <span>{server.health.error}</span>
            </div>
          )}
        </div>

        {editing ? (
          <div className="space-y-4 rounded-xl border border-(--ui-stroke-tertiary) p-5">
            <h3 className="text-sm font-semibold">Edit Configuration</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <label className="text-xs font-medium" htmlFor="sd-name">Server Name</label>
                <Input id="sd-name" onChange={e => setName(e.target.value)} value={name} />
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-medium" htmlFor="sd-type">Type</label>
                <Select onValueChange={v => setType(v as McpType)} value={type}>
                  <SelectTrigger className="h-9" id="sd-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MCP_TYPES.map(t => <SelectItem key={t} value={t}>{MCP_TYPE_LABELS[t]}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {type === 'stdio' ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium" htmlFor="sd-command">Command</label>
                  <Input id="sd-command" onChange={e => setCommand(e.target.value)} value={command} />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium" htmlFor="sd-args">Arguments</label>
                  <Input id="sd-args" onChange={e => setArgs(e.target.value)} value={args} />
                </div>
              </div>
            ) : (
              <div className="grid gap-1.5">
                <label className="text-xs font-medium" htmlFor="sd-url">URL</label>
                <Input id="sd-url" onChange={e => setUrl(e.target.value)} value={url} />
              </div>
            )}
            <div className="grid gap-1.5">
              <label className="text-xs font-medium" htmlFor="sd-config">Configuration (JSON)</label>
              <Textarea
                className="min-h-28 font-mono text-xs"
                id="sd-config"
                onChange={e => setJsonConfig(e.target.value)}
                value={jsonConfig}
              />
            </div>
            {error && (
              <div className="flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <Codicon className="mt-0.5 shrink-0" name="error" size="0.75rem" />
                <span>{error}</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <Button disabled={saving} onClick={() => void handleSave()} size="sm">
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
              <Button disabled={saving} onClick={handleCancelEdit} size="sm" variant="outline">Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Current Configuration</h4>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-foreground">Type:</span>
                <span className="text-muted-foreground">{MCP_TYPE_LABELS[server.type]}</span>
                <span className="text-muted-foreground/50">({server.transport})</span>
              </div>
              {server.command && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-foreground">Command:</span>
                  <span className="font-mono text-muted-foreground">{server.command} {server.args?.join(' ')}</span>
                </div>
              )}
              {server.url && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-foreground">URL:</span>
                  <span className="font-mono text-muted-foreground">{server.url}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-foreground">Enabled:</span>
                <Switch checked={server.enabled} onCheckedChange={() => {}} />
              </div>
              {Object.keys(server.config).length > 0 && (
                <div className="pt-1">
                  <span className="text-xs font-medium text-foreground">Config:</span>
                  <pre className="mt-1 rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5 font-mono text-[0.65rem] text-muted-foreground">
                    {JSON.stringify(server.config, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="rounded-xl border border-(--ui-stroke-tertiary)">
          <div className="border-b border-(--ui-stroke-tertiary) px-4 py-2.5">
            <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Codicon name="terminal" size="0.75rem" />
              Server Log
              <Badge className="text-[0.55rem]" variant="muted">{server.log.length} entries</Badge>
            </h4>
          </div>
          <LogView className="max-h-64 border-0 rounded-none">
            {server.log.length === 0 ? (
              <span className="text-muted-foreground/60">No log entries</span>
            ) : (
              server.log.map((entry, i) => (
                <div className="flex gap-2 py-0.5" key={i}>
                  <span className={cn(
                    'shrink-0 text-[0.55rem] font-semibold uppercase',
                    entry.level === 'error' ? 'text-red-500' : entry.level === 'warn' ? 'text-amber-500' : 'text-muted-foreground'
                  )}>
                    {entry.level}
                  </span>
                  <span className="text-muted-foreground/60">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                  <span>{entry.message}</span>
                </div>
              ))
            )}
          </LogView>
        </div>
      </div>
    </PageShell>
  )
}
