import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { getAetherosConfigRecord, saveAetherosConfig } from '@/aetheros'
import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { LogView } from '@/components/ui/log-view'
import { SearchField } from '@/components/ui/search-field'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify, notifyError } from '@/store/notifications'

type McpType = 'stdio' | 'sse' | 'streamable-http' | 'websocket'

interface McpServerHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  latency: number | null
  lastCheck: string | null
  error: string | null
}

interface McpServer {
  id: string
  name: string
  type: McpType
  transport: string
  command?: string
  args?: string[]
  url?: string
  enabled: boolean
  autoDiscover: boolean
  health: McpServerHealth
  config: Record<string, unknown>
  log: { level: string; message: string; timestamp: number }[]
}

const UNKNOWN_HEALTH: McpServerHealth = { status: 'unknown', latency: null, lastCheck: null, error: null }

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function coerceType(value: unknown): McpType {
  return value === 'sse' || value === 'streamable-http' || value === 'websocket' || value === 'stdio'
    ? value
    : 'stdio'
}

/**
 * Derive the server list from the live gateway config (`mcp_servers`).
 * Health is `unknown` until a real probe reports otherwise — the manager
 * never invents latency or timestamps. Empty config renders as
 * "Not configured", a failed load as "Unavailable".
 */
function serversFromConfig(record: Record<string, unknown>): McpServer[] {
  const raw = asRecord(record['mcp_servers'])

  return Object.keys(raw).sort().map(id => {
    const entry = asRecord(raw[id])
    const type = coerceType(entry['type'] ?? entry['transport'])
    const command = typeof entry['command'] === 'string' ? entry['command'] as string : undefined

    const args = Array.isArray(entry['args'])
      ? (entry['args'] as unknown[]).filter((a): a is string => typeof a === 'string')
      : undefined

    const url = typeof entry['url'] === 'string' ? entry['url'] as string : undefined
    const name = typeof entry['name'] === 'string' ? entry['name'] as string : id

    return {
      id,
      name,
      type,
      transport: typeof entry['transport'] === 'string' ? entry['transport'] as string : type,
      command,
      args,
      url,
      enabled: entry['enabled'] !== false,
      autoDiscover: entry['autoDiscover'] === true,
      health: { ...UNKNOWN_HEALTH },
      config: entry,
      log: [{ level: 'info', message: 'Loaded from gateway config', timestamp: Date.now() }],
    }
  })
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

export function McpManagerView() {
  const { t } = useI18n()
  // Servers come from the live gateway config — never sample data. Health
  // stays `unknown` until a real probe reports otherwise.
  const [servers, setServers] = useState<McpServer[]>([])
  const [configLoaded, setConfigLoaded] = useState(false)
  const [configError, setConfigError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [filterHealth, setFilterHealth] = useState<'all' | 'healthy' | 'degraded' | 'unhealthy' | 'unknown'>('all')
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null)
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [expandedLogServer, setExpandedLogServer] = useState<string | null>(null)

  // Live mirror for async handlers (import runs inside a file-input callback
  // where the closed-over `servers` value may be stale).
  const serversRef = useRef(servers)
  serversRef.current = servers

  const reloadFromConfig = useCallback(async () => {
    try {
      const record = await getAetherosConfigRecord() as unknown as Record<string, unknown>
      setServers(serversFromConfig(record))
      setConfigError(null)
    } catch (e) {
      setConfigError(e instanceof Error ? e.message : String(e))
    } finally {
      setConfigLoaded(true)
    }
  }, [])

  useEffect(() => {
    void reloadFromConfig()
  }, [reloadFromConfig])

  const filteredServers = useMemo(() => {
    const q = query.trim().toLowerCase()

    return servers.filter(s => {
      if (q && !s.name.toLowerCase().includes(q) && !s.id.toLowerCase().includes(q) && !s.type.includes(q)) {return false}

      if (typeFilter !== 'all' && s.type !== typeFilter) {return false}

      if (filterHealth !== 'all' && s.health.status !== filterHealth) {return false}

      return true
    })
  }, [servers, query, typeFilter, filterHealth])

  const selectedServer = useMemo(
    () => servers.find(s => s.id === selectedServerId) ?? filteredServers[0] ?? null,
    [servers, selectedServerId, filteredServers]
  )

  useEffect(() => {
    if (selectedServer && !filteredServers.find(s => s.id === selectedServer.id)) {
      setSelectedServerId(filteredServers[0]?.id ?? null)
    }
  }, [filteredServers, selectedServer])

  const persistServers = useCallback(async (next: McpServer[]) => {
    const record = await getAetherosConfigRecord() as unknown as Record<string, unknown>
    const mcp = { ...asRecord(record['mcp_servers']) }

    for (const s of next) {
      mcp[s.id] = {
        ...asRecord(mcp[s.id]),
        name: s.name,
        type: s.type,
        transport: s.transport,
        ...(s.command !== undefined ? { command: s.command } : {}),
        ...(s.args !== undefined ? { args: s.args } : {}),
        ...(s.url !== undefined ? { url: s.url } : {}),
        enabled: s.enabled,
      }
    }

    await saveAetherosConfig({ ...record, mcp_servers: mcp })
  }, [])

  const handleToggle = useCallback(async (serverId: string, enabled: boolean) => {
    const prev = servers
    const next = prev.map(s => s.id === serverId ? { ...s, enabled } : s)
    setServers(next)

    try {
      await persistServers(next)
      notify({ kind: 'success', title: enabled ? 'Server Enabled' : 'Server Disabled', message: `${serverId} ${enabled ? 'enabled' : 'disabled'}` })
    } catch (e) {
      setServers(prev)
      notifyError(e, `Failed to ${enabled ? 'enable' : 'disable'} ${serverId} — change not saved`)
    }
  }, [persistServers, servers])

  const handleRefresh = useCallback(async (serverId: string) => {
    // No live health-probe endpoint exists yet, so refresh re-reads the
    // gateway config (the authoritative state) instead of fabricating
    // latency. Health remains `unknown` until a real probe reports.
    await reloadFromConfig()
    setServers(current => current.map(s => s.id === serverId ? {
      ...s,
      log: [...s.log, { level: 'info', message: 'Re-read from gateway config — live health probing not available', timestamp: Date.now() }]
    } : s))
    notify({ kind: 'info', title: 'Config Reloaded', message: `${serverId} re-read from gateway config` })
  }, [reloadFromConfig])

  const handleAddServer = useCallback(async (server: Partial<McpServer>) => {
    const newServer: McpServer = {
      id: server.id || `mcp-${Date.now()}`,
      name: server.name || 'New Server',
      type: server.type || 'stdio',
      transport: server.transport || (server.type === 'stdio' ? 'stdio' : 'sse'),
      command: server.command,
      args: server.args,
      url: server.url,
      enabled: true,
      autoDiscover: false,
      health: { ...UNKNOWN_HEALTH },
      config: {},
      log: [{ level: 'info', message: 'Server added — saved to gateway config', timestamp: Date.now() }]
    }

    const next = [...servers, newServer]
    setServers(next)

    try {
      await persistServers(next)
      setShowAddDialog(false)
      notify({ kind: 'success', title: 'Server Added', message: `${newServer.name} saved to gateway config` })
    } catch (e) {
      setServers(servers)
      notifyError(e, `Failed to save ${newServer.name} — change not saved`)
    }
  }, [persistServers, servers])

  const handleRemoveServer = useCallback(async (serverId: string) => {
    const prev = servers
    const next = prev.filter(s => s.id !== serverId)
    setServers(next)

    if (selectedServerId === serverId) {setSelectedServerId(null)}

    try {
      const record = await getAetherosConfigRecord() as unknown as Record<string, unknown>
      const mcp = { ...asRecord(record['mcp_servers']) }
      delete mcp[serverId]
      await saveAetherosConfig({ ...record, mcp_servers: mcp })
      notify({ kind: 'success', title: 'Server Removed', message: `Server ${serverId} removed from gateway config` })
    } catch (e) {
      setServers(prev)
      notifyError(e, `Failed to remove ${serverId} — change not saved`)
    }
  }, [selectedServerId, servers])

  const handleExportConfig = useCallback(() => {
    const config = servers.map(s => ({
      name: s.name,
      type: s.type,
      transport: s.transport,
      command: s.command,
      args: s.args,
      url: s.url,
      enabled: s.enabled,
      config: s.config
    }))

    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mcp-servers.json'
    a.click()
    URL.revokeObjectURL(url)
    notify({ kind: 'success', title: 'Config Exported', message: 'MCP server config exported' })
  }, [servers])

  const handleImportConfig = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'

    input.onchange = async e => {
      const file = (e.target as HTMLInputElement).files?.[0]

      if (!file) {return}

      try {
        const text = await file.text()
        const imported = JSON.parse(text)

        if (Array.isArray(imported)) {
          const incoming: McpServer[] = imported.map((s: Record<string, unknown>) => ({
            id: `mcp-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            name: s.name as string || 'Imported Server',
            type: s.type as McpType || 'stdio',
            transport: s.transport as string || 'stdio',
            command: s.command as string,
            args: s.args as string[],
            url: s.url as string,
            enabled: s.enabled as boolean ?? true,
            autoDiscover: false,
            health: { status: 'unknown' as const, latency: null, lastCheck: null, error: null },
            config: s.config as Record<string, unknown> || {},
            log: [{ level: 'info' as const, message: 'Imported from config', timestamp: Date.now() }]
          }))
          const prev = serversRef.current
          const next = [...prev, ...incoming]

          setServers(next)

          try {
            await persistServers(next)
            notify({ kind: 'success', title: 'Config Imported', message: `${imported.length} server(s) imported and saved` })
          } catch (err) {
            setServers(prev)
            notifyError(err, 'Import parsed but saving failed — change not saved')
          }
        } else {
          notifyError(new Error('Invalid format'), 'Expected an array of server configs')
        }
      } catch (err) {
        notifyError(err, 'Failed to import config')
      }
    }

    input.click()
  }, [persistServers])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>MCP Manager</PageTitle>
            <PageDescription>Manage Model Context Protocol servers and connections</PageDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button className="text-xs" onClick={handleImportConfig} size="sm" variant="outline">
              <Codicon className="mr-1" name="file" size="0.75rem" /> Import
            </Button>
            <Button className="text-xs" onClick={handleExportConfig} size="sm" variant="outline">
              <Codicon className="mr-1" name="export" size="0.75rem" /> Export
            </Button>
            <Button className="text-xs" onClick={() => setShowAddDialog(true)} size="sm">
              <Codicon className="mr-1" name="plus" size="0.75rem" /> Add Server
            </Button>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full gap-4">
        <div className="w-72 shrink-0 space-y-3">
          <SearchField
            containerClassName="w-full"
            onChange={setQuery}
            placeholder="Search servers..."
            value={query}
          />
          <div className="flex gap-2">
            <Select onValueChange={v => setTypeFilter(v)} value={typeFilter}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {MCP_TYPES.map(t => <SelectItem key={t} value={t}>{MCP_TYPE_LABELS[t]}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select onValueChange={v => setFilterHealth(v as typeof filterHealth)} value={filterHealth}>
              <SelectTrigger className="h-7 flex-1 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Health</SelectItem>
                <SelectItem value="healthy">Healthy</SelectItem>
                <SelectItem value="degraded">Degraded</SelectItem>
                <SelectItem value="unhealthy">Unhealthy</SelectItem>
                <SelectItem value="unknown">Unknown</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-0.5">
            {filteredServers.map(server => (
              <button
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                  selectedServer?.id === server.id ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                )}
                key={server.id}
                onClick={() => setSelectedServerId(server.id)}
                type="button"
              >
                <span className={cn('size-2 shrink-0 rounded-full', HEALTH_DOT[server.health.status])} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-medium">{server.name}</span>
                    {!server.enabled && <Badge className="text-[0.55rem]" variant="muted">Off</Badge>}
                  </div>
                  <div className="flex items-center gap-1.5 text-[0.6rem] text-muted-foreground">
                    <Badge className="text-[0.55rem]" variant="outline">{MCP_TYPE_LABELS[server.type]}</Badge>
                    {server.health.latency !== null && <span>{server.health.latency}ms</span>}
                  </div>
                </div>
              </button>
            ))}
            {filteredServers.length === 0 && (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                {!configLoaded
                  ? 'Loading gateway config…'
                  : configError
                    ? `Unavailable — gateway config could not be loaded (${configError})`
                    : query
                      ? 'No servers match your search'
                      : 'Not configured — no MCP servers in gateway config'}
              </div>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1 overflow-y-auto">
          {selectedServer ? (
            <div className="space-y-4">
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className={cn('mt-1 size-3 shrink-0 rounded-full', HEALTH_DOT[selectedServer.health.status])} />
                    <div>
                      <h3 className="text-lg font-semibold">{selectedServer.name}</h3>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="outline">{MCP_TYPE_LABELS[selectedServer.type]}</Badge>
                        <span>{selectedServer.transport}</span>
                        {selectedServer.command && <span className="font-mono">{selectedServer.command} {selectedServer.args?.join(' ')}</span>}
                        {selectedServer.url && <span className="font-mono">{selectedServer.url}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button
                      onClick={() => void handleRefresh(selectedServer.id)}
                      size="sm"
                      title="Re-read this server from the gateway config (live health probing is not available)"
                      variant="outline"
                    >
                      <Codicon className="mr-1" name="refresh" size="0.75rem" />
                      Refresh
                    </Button>
                    <Button
                      className="text-muted-foreground hover:text-destructive"
                      onClick={() => void handleRemoveServer(selectedServer.id)}
                      size="sm"
                      variant="ghost"
                    >
                      <Codicon name="trash" size="0.875rem" />
                    </Button>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3">
                  <div className="rounded-md bg-(--ui-bg-quinary) px-3 py-2">
                    <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Status</div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-sm font-medium">
                      <span className={cn('size-2 rounded-full', HEALTH_DOT[selectedServer.health.status])} />
                      {selectedServer.health.status.charAt(0).toUpperCase() + selectedServer.health.status.slice(1)}
                    </div>
                  </div>
                  <div className="rounded-md bg-(--ui-bg-quinary) px-3 py-2">
                    <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Latency</div>
                    <div className="mt-0.5 text-sm font-medium tabular-nums">
                      {selectedServer.health.latency !== null ? `${selectedServer.health.latency}ms` : '—'}
                    </div>
                  </div>
                  <div className="rounded-md bg-(--ui-bg-quinary) px-3 py-2">
                    <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Last Check</div>
                    <div className="mt-0.5 text-sm font-medium tabular-nums">
                      {selectedServer.health.lastCheck ? new Date(selectedServer.health.lastCheck).toLocaleTimeString() : '—'}
                    </div>
                  </div>
                </div>

                {selectedServer.health.error && (
                  <div className="mt-3 flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                    <Codicon className="mt-0.5 shrink-0" name="error" size="0.875rem" />
                    <span>{selectedServer.health.error}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                <div className="flex items-center gap-3">
                  <Codicon name="server" size="1rem" />
                  <div>
                    <span className="text-sm font-medium">{selectedServer.name}</span>
                    <div className="text-xs text-muted-foreground">{selectedServer.autoDiscover ? 'Auto-discovered' : 'Manual configuration'}</div>
                  </div>
                </div>
                <Switch
                  checked={selectedServer.enabled}
                  onCheckedChange={checked => void handleToggle(selectedServer.id, checked)}
                />
              </div>

              <div className="rounded-xl border border-(--ui-stroke-tertiary)">
                <button
                  className="flex w-full items-center justify-between px-4 py-2.5 text-left"
                  onClick={() => setExpandedLogServer(expandedLogServer === selectedServer.id ? null : selectedServer.id)}
                  type="button"
                >
                  <div className="flex items-center gap-2">
                    <Codicon name="terminal" size="0.875rem" />
                    <span className="text-sm font-medium">Server Log</span>
                    <Badge className="text-[0.55rem]" variant="muted">{selectedServer.log.length} entries</Badge>
                  </div>
                  <Codicon
                    className="text-muted-foreground transition-transform"
                    name="chevron-down"
                    size="0.875rem"
                    style={{ transform: expandedLogServer === selectedServer.id ? 'rotate(180deg)' : undefined }}
                  />
                </button>
                {expandedLogServer === selectedServer.id && (
                  <LogView className="max-h-48 border-0 border-t border-(--ui-stroke-tertiary) rounded-none">
                    {selectedServer.log.map((entry, i) => (
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
                    ))}
                  </LogView>
                )}
              </div>

              {Object.keys(selectedServer.config).length > 0 && (
                <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Configuration</h4>
                  <div className="space-y-1.5">
                    {Object.entries(selectedServer.config).map(([key, value]) => (
                      <div className="flex items-center gap-2 text-xs" key={key}>
                        <span className="font-medium text-foreground">{key}:</span>
                        <span className="text-muted-foreground">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="grid min-h-52 place-items-center text-center">
              <div>
                <Codicon className="text-muted-foreground/40" name="server" size="2rem" />
                <div className="mt-2 text-sm font-medium text-muted-foreground">No server selected</div>
                <div className="mt-1 text-xs text-muted-foreground/60">Select a server or add a new one</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <AddServerDialog
        onAdd={handleAddServer}
        onClose={() => setShowAddDialog(false)}
        open={showAddDialog}
      />
    </PageShell>
  )
}

function AddServerDialog({
  onAdd,
  onClose,
  open
}: {
  onAdd: (server: Partial<McpServer>) => void
  onClose: () => void
  open: boolean
}) {
  const [name, setName] = useState('')
  const [type, setType] = useState<McpType>('stdio')
  const [command, setCommand] = useState('')
  const [args, setArgs] = useState('')
  const [url, setUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setName(''); setType('stdio'); setCommand(''); setArgs(''); setUrl(''); setError(null)
    }
  }, [open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) { setError('Server name is required');

 return }

    if (type === 'stdio' && !command.trim()) { setError('Command is required for STDIO servers');

 return }

    if (type !== 'stdio' && !url.trim()) { setError('URL is required for this server type');

 return }

    setSaving(true)
    onAdd({
      id: `mcp-${name.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`,
      name: name.trim(),
      type,
      transport: type === 'stdio' ? 'stdio' : type === 'websocket' ? 'ws' : type === 'sse' ? 'sse' : 'http',
      command: type === 'stdio' ? command.trim() : undefined,
      args: type === 'stdio' ? args.split(/\s+/).filter(Boolean) : undefined,
      url: type !== 'stdio' ? url.trim() : undefined
    })
    setSaving(false)
  }

  return (
    <Dialog onOpenChange={v => !v && !saving && onClose()} open={open}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add MCP Server</DialogTitle>
          <DialogDescription>Configure a new Model Context Protocol server</DialogDescription>
        </DialogHeader>
        <form className="grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-1.5">
            <label className="text-xs font-medium text-foreground" htmlFor="mcp-name">Server Name</label>
            <Input autoFocus id="mcp-name" onChange={e => setName(e.target.value)} placeholder="My Server" value={name} />
          </div>
          <div className="grid gap-1.5">
            <label className="text-xs font-medium text-foreground" htmlFor="mcp-type">Server Type</label>
            <Select onValueChange={v => setType(v as McpType)} value={type}>
              <SelectTrigger className="h-9" id="mcp-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MCP_TYPES.map(t => <SelectItem key={t} value={t}>{MCP_TYPE_LABELS[t]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {type === 'stdio' ? (
            <>
              <div className="grid gap-1.5">
                <label className="text-xs font-medium text-foreground" htmlFor="mcp-command">Command</label>
                <Input id="mcp-command" onChange={e => setCommand(e.target.value)} placeholder="npx" value={command} />
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-medium text-foreground" htmlFor="mcp-args">Arguments</label>
                <Input id="mcp-args" onChange={e => setArgs(e.target.value)} placeholder="-y @modelcontextprotocol/server-filesystem" value={args} />
              </div>
            </>
          ) : (
            <div className="grid gap-1.5">
              <label className="text-xs font-medium text-foreground" htmlFor="mcp-url">Server URL</label>
              <Input id="mcp-url" onChange={e => setUrl(e.target.value)} placeholder={type === 'websocket' ? 'ws://localhost:8080/mcp' : 'http://localhost:3000/mcp'} value={url} />
            </div>
          )}
          {error && (
            <div className="flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <Codicon className="mt-0.5 shrink-0" name="error" size="0.75rem" />
              <span>{error}</span>
            </div>
          )}
          <DialogFooter>
            <Button disabled={saving} onClick={onClose} type="button" variant="outline">Cancel</Button>
            <Button disabled={saving} type="submit">{saving ? 'Adding...' : 'Add Server'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
