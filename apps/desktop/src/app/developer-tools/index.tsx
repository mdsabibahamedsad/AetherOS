import { useCallback, useEffect, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { LogView } from '@/components/ui/log-view'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

interface LogEntry {
  id: string
  timestamp: number
  level: 'debug' | 'info' | 'warn' | 'error'
  source: string
  message: string
  data?: unknown
}

interface MetricPoint {
  label: string
  value: number
  unit: string
  max: number
}

interface InspectorNode {
  id: string
  name: string
  type: 'plugin' | 'tool' | 'hook' | 'store'
  value?: string
  children?: InspectorNode[]
}

const INITIAL_LOGS: LogEntry[] = [
  { id: 'l1', timestamp: Date.now() - 5000, level: 'info', source: 'core', message: 'Session manager initialized' },
  { id: 'l2', timestamp: Date.now() - 4000, level: 'info', source: 'gateway', message: 'Gateway connection established' },
  { id: 'l3', timestamp: Date.now() - 3000, level: 'warn', source: 'plugin:code-analyzer', message: 'Deprecated API used: readFileSync' },
  { id: 'l4', timestamp: Date.now() - 2000, level: 'debug', source: 'mcp:filesystem', message: 'List directory: /home/user/projects' },
  { id: 'l5', timestamp: Date.now() - 1000, level: 'error', source: 'plugin:search-assistant', message: 'Rate limit exceeded, retrying in 30s' },
  { id: 'l6', timestamp: Date.now(), level: 'info', source: 'core', message: 'Plugin marketplace index updated' }
]

const INITIAL_METRICS: MetricPoint[] = [
  { label: 'Memory', value: 342, unit: 'MB', max: 1024 },
  { label: 'CPU', value: 12, unit: '%', max: 100 },
  { label: 'Extensions', value: 5, unit: 'running', max: 20 },
  { label: 'MCP Servers', value: 3, unit: 'connected', max: 10 }
]

const INITIAL_INSPECTOR: InspectorNode = {
  id: 'root', name: 'AetherOS Runtime', type: 'store',
  children: [
    {
      id: 'plugins', name: 'Plugins', type: 'store',
      children: [
        { id: 'p1', name: 'Code Analyzer', type: 'plugin', value: 'v2.1.0 • enabled' },
        { id: 'p2', name: 'Search Assistant', type: 'plugin', value: 'v1.3.2 • disabled' },
        { id: 'p3', name: 'Task Automation', type: 'plugin', value: 'v3.0.1 • enabled' }
      ]
    },
    {
      id: 'tools', name: 'Registered Tools', type: 'store',
      children: [
        { id: 't1', name: 'read_file', type: 'tool', value: 'core' },
        { id: 't2', name: 'write_file', type: 'tool', value: 'core' },
        { id: 't3', name: 'web_search', type: 'tool', value: 'core' },
        { id: 't4', name: 'terminal', type: 'tool', value: 'core' },
        { id: 't5', name: 'mcp_call', type: 'tool', value: 'mcp-bridge' },
        { id: 't6', name: 'analyze_code', type: 'tool', value: 'plugin:code-analyzer' }
      ]
    },
    {
      id: 'hooks', name: 'Registered Hooks', type: 'store',
      children: [
        { id: 'h1', name: 'session:start', type: 'hook', value: '2 handlers' },
        { id: 'h2', name: 'session:end', type: 'hook', value: '1 handler' },
        { id: 'h3', name: 'tool:before', type: 'hook', value: '3 handlers' },
        { id: 'h4', name: 'tool:after', type: 'hook', value: '3 handlers' },
        { id: 'h5', name: 'message:send', type: 'hook', value: '1 handler' }
      ]
    },
    {
      id: 'stores', name: 'State Stores', type: 'store',
      children: [
        { id: 's1', name: 'session', type: 'store', value: '1 active session' },
        { id: 's2', name: 'plugins', type: 'store', value: '3 plugins tracked' },
        { id: 's3', name: 'mcp', type: 'store', value: '5 servers tracked' },
        { id: 's4', name: 'cron', type: 'store', value: '8 jobs scheduled' }
      ]
    }
  ]
}

const LOG_LEVEL_COLORS: Record<string, string> = {
  debug: 'text-muted-foreground',
  info: 'text-sky-500',
  warn: 'text-amber-500',
  error: 'text-red-500'
}

export function DeveloperToolsView() {
  const { t } = useI18n()
  const [activeTab, setActiveTab] = useState<'console' | 'metrics' | 'inspector'>('console')
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS)
  const [logFilter, setLogFilter] = useState<'all' | 'debug' | 'info' | 'warn' | 'error'>('all')
  const [logSource, setLogSource] = useState<string>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [metrics, setMetrics] = useState<MetricPoint[]>(INITIAL_METRICS)
  const [expandedInspector, setExpandedInspector] = useState<Set<string>>(new Set(['root', 'plugins', 'tools', 'hooks', 'stores']))
  const [liveReload, setLiveReload] = useState(false)

  useEffect(() => {
    if (!liveReload) {return}

    const interval = setInterval(() => {
      setMetrics(current => current.map(m => ({
        ...m,
        value: m.label === 'Memory' ? Math.floor(Math.random() * 512) + 128 :
               m.label === 'CPU' ? Math.floor(Math.random() * 40) + 2 :
               m.label === 'Extensions' ? Math.floor(Math.random() * 8) + 2 :
               Math.floor(Math.random() * 5) + 1
      })))
      setLogs(current => [...current.slice(-50), {
        id: `l-${Date.now()}`,
        timestamp: Date.now(),
        level: (['debug', 'info', 'warn', 'error'] as const)[Math.floor(Math.random() * 4)],
        source: ['core', 'gateway', 'plugin:code-analyzer', 'mcp:filesystem'][Math.floor(Math.random() * 4)],
        message: `Live metric sample at ${new Date().toLocaleTimeString()}`
      }])
    }, 3000)

    return () => clearInterval(interval)
  }, [liveReload])

  const filteredLogs = useMemo(() => {
    return logs.filter(l => {
      if (logFilter !== 'all' && l.level !== logFilter) {return false}

      if (logSource !== 'all' && l.source !== logSource) {return false}

      return true
    })
  }, [logs, logFilter, logSource])

  const logSources = useMemo(() => {
    const sources = new Set(logs.map(l => l.source))

    return Array.from(sources).sort()
  }, [logs])

  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = {}

    for (const l of logs) {
      counts[l.source] = (counts[l.source] || 0) + 1
    }

    return counts
  }, [logs])

  const handleClearLogs = useCallback(() => {
    setLogs([])
    notify({ kind: 'success', title: 'Console Cleared', message: 'Log buffer cleared' })
  }, [])

  const toggleInspector = useCallback((id: string) => {
    setExpandedInspector(prev => {
      const next = new Set(prev)

      if (next.has(id)) {next.delete(id)}
      else {next.add(id)}

      return next
    })
  }, [])

  const renderInspectorNode = (node: InspectorNode, depth: number = 0): React.ReactNode => {
    const hasChildren = node.children && node.children.length > 0
    const isExpanded = expandedInspector.has(node.id)

    const typeIcon: Record<string, string> = {
      plugin: 'extensions',
      tool: 'zap',
      hook: 'link',
      store: 'database'
    }

    return (
      <div key={node.id}>
        <div
          className={cn(
            'flex items-center gap-1.5 rounded-sm px-1 py-0.5 text-xs hover:bg-accent/60',
            depth > 0 && 'ml-4'
          )}
          style={{ paddingLeft: `${depth * 12 + 4}px` }}
        >
          {hasChildren ? (
            <button
              className="flex items-center text-muted-foreground hover:text-foreground"
              onClick={() => toggleInspector(node.id)}
              type="button"
            >
              <Codicon
                className="transition-transform"
                name="chevron-right"
                size="0.6rem"
                style={{ transform: isExpanded ? 'rotate(90deg)' : undefined }}
              />
            </button>
          ) : (
            <span className="w-3" />
          )}
          <Codicon className={cn(
            'shrink-0',
            node.type === 'plugin' ? 'text-primary' :
            node.type === 'tool' ? 'text-sky-500' :
            node.type === 'hook' ? 'text-amber-500' :
            'text-muted-foreground'
          )} name={typeIcon[node.type] || 'circle'} size="0.75rem" />
          <span className="font-medium">{node.name}</span>
          {node.value && <span className="text-muted-foreground">— {node.value}</span>}
        </div>
        {hasChildren && isExpanded && node.children!.map(child => renderInspectorNode(child, depth + 1))}
      </div>
    )
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Developer Tools</PageTitle>
            <PageDescription>Debug, inspect, and monitor AetherOS internals</PageDescription>
          </div>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Switch checked={liveReload} onCheckedChange={setLiveReload} />
            Live Refresh
          </label>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-0">
        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {(['console', 'metrics', 'inspector'] as const).map(tab => (
            <button
              className={cn(
                'flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors',
                activeTab === tab ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              key={tab}
              onClick={() => setActiveTab(tab)}
              type="button"
            >
              <Codicon
                name={tab === 'console' ? 'terminal' : tab === 'metrics' ? 'chart' : 'search'}
                size="0.875rem"
              />
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {activeTab === 'console' && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
              <div className="flex gap-1">
                {(['all', 'debug', 'info', 'warn', 'error'] as const).map(level => (
                  <button
                    className={cn(
                      'rounded-md px-2 py-0.5 text-[0.6rem] font-medium transition-colors',
                      logFilter === level ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                    )}
                    key={level}
                    onClick={() => setLogFilter(level)}
                    type="button"
                  >
                    {level === 'all' ? 'All' : level.charAt(0).toUpperCase() + level.slice(1)}
                  </button>
                ))}
              </div>
              <div className="ml-auto flex items-center gap-1.5">
                <label className="flex items-center gap-1 text-[0.6rem] text-muted-foreground">
                  <Switch checked={autoScroll} onCheckedChange={setAutoScroll} />
                  Auto-scroll
                </label>
                <Button aria-label="Clear logs" className="text-[0.6rem] text-muted-foreground" onClick={handleClearLogs} size="icon-xs" variant="ghost">
                  <Codicon name="trash" size="0.75rem" />
                </Button>
              </div>
            </div>
            <div className="flex min-h-0 flex-1">
              <div className="w-36 shrink-0 border-r border-(--ui-stroke-tertiary) px-2 py-1">
                <div className="mb-1 text-[0.55rem] font-semibold uppercase tracking-wider text-muted-foreground">Sources</div>
                <button
                  className={cn(
                    'flex w-full items-center justify-between rounded-sm px-1.5 py-0.5 text-[0.6rem] transition-colors',
                    logSource === 'all' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  onClick={() => setLogSource('all')}
                  type="button"
                >
                  <span>All Sources</span>
                  <span className="text-muted-foreground/60">{logs.length}</span>
                </button>
                {logSources.map(source => (
                  <button
                    className={cn(
                      'flex w-full items-center justify-between rounded-sm px-1.5 py-0.5 text-[0.6rem] transition-colors',
                      logSource === source ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                    )}
                    key={source}
                    onClick={() => setLogSource(source)}
                    type="button"
                  >
                    <span className="truncate">{source}</span>
                    <span className="text-muted-foreground/60">{sourceCounts[source]}</span>
                  </button>
                ))}
              </div>
              <LogView className="flex-1 border-0 rounded-none max-h-full">
                {filteredLogs.length === 0 ? (
                  <span className="text-muted-foreground/60">No log entries match the filter</span>
                ) : (
                  filteredLogs.map(log => (
                    <div className="flex gap-2 py-0.5" key={log.id}>
                      <span className={cn('shrink-0 text-[0.55rem] font-semibold uppercase', LOG_LEVEL_COLORS[log.level])}>
                        {log.level}
                      </span>
                      <span className="shrink-0 text-[0.55rem] text-muted-foreground/60 tabular-nums">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="shrink-0 text-[0.55rem] text-muted-foreground/40">[{log.source}]</span>
                      <span className="text-foreground/80">{log.message}</span>
                    </div>
                  ))
                )}
              </LogView>
            </div>
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {metrics.map(metric => (
                <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4" key={metric.label}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">{metric.label}</span>
                    <Codicon
                      name={metric.label === 'Memory' ? 'database' : metric.label === 'CPU' ? 'cpu' : metric.label === 'Extensions' ? 'extensions' : 'server'}
                      size="0.875rem"
                    />
                  </div>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-semibold tabular-nums">{metric.value}</span>
                    <span className="text-xs text-muted-foreground">{metric.unit}</span>
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        metric.value / metric.max > 0.8 ? 'bg-red-500' :
                        metric.value / metric.max > 0.5 ? 'bg-amber-500' :
                        'bg-emerald-500'
                      )}
                      style={{ width: `${Math.min((metric.value / metric.max) * 100, 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 text-right text-[0.55rem] text-muted-foreground">
                    {metric.max} {metric.unit} max
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Error Rate</h4>
                <div className="flex items-end gap-1" style={{ height: 80 }}>
                  {[12, 8, 15, 5, 3, 9, 7, 4, 6, 2, 1, 3, 5, 8, 4, 2, 6, 3, 1, 0, 2, 4, 3, 1].map((v, i) => (
                    <div
                      className={cn(
                        'flex-1 rounded-t-sm transition-all',
                        v > 10 ? 'bg-red-500' : v > 5 ? 'bg-amber-500' : 'bg-emerald-500'
                      )}
                      key={i}
                      style={{ height: `${(v / 15) * 100}%` }}
                      title={`${v} errors`}
                    />
                  ))}
                </div>
                <div className="mt-1 text-[0.55rem] text-muted-foreground">Last 24 hours (hourly)</div>
              </div>

              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Plugin Activity</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="w-28 truncate text-xs text-muted-foreground">Code Analyzer</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                      <div className="h-full rounded-full bg-primary" style={{ width: '80%' }} />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">80%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 truncate text-xs text-muted-foreground">Search Assistant</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                      <div className="h-full rounded-full bg-primary" style={{ width: '45%' }} />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">45%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 truncate text-xs text-muted-foreground">Task Automation</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                      <div className="h-full rounded-full bg-primary" style={{ width: '30%' }} />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">30%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-28 truncate text-xs text-muted-foreground">MCP Servers</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                      <div className="h-full rounded-full bg-primary" style={{ width: '60%' }} />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">60%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'inspector' && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mx-auto max-w-2xl rounded-xl border border-(--ui-stroke-tertiary) px-3 py-2">
              {renderInspectorNode(INITIAL_INSPECTOR)}
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}
