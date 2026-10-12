import { useStore } from '@nanostores/react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  $agentHub,
  type AgentTemplate,
  createAgent,
  deleteAgent,
  duplicateAgent,
  setAgentStatus,
  setEditingAgent,
  setFilterStatus,
  setFilterTemplate,
  setSearchQuery,
  TEMPLATE_DEFAULTS,
  TEMPLATE_LABELS
} from '@/store/agent-hub'

const STATUS_GLYPH: Record<string, { color: string; label: string }> = {
  running: { color: 'bg-green-500', label: 'Running' },
  stopped: { color: 'bg-gray-400', label: 'Stopped' },
  paused: { color: 'bg-yellow-500', label: 'Paused' },
  error: { color: 'bg-red-500', label: 'Error' },
  created: { color: 'bg-blue-400', label: 'Created' }
}

const TEMPLATES = Object.entries(TEMPLATE_LABELS) as [AgentTemplate, string][]

const TEMPLATE_ICONS: Record<string, string> = {
  coding: '</>',
  research: '🔍',
  writing: '✎',
  automation: '⚡',
  'data-analyst': '📊',
  devops: '🔧',
  browser: '🌐',
  'file-manager': '📁',
  support: '💬',
  assistant: '👤',
  'social-media': '📱',
  email: '📧',
  knowledge: '📚',
  voice: '🎤',
  vision: '👁',
  custom: '✦'
}

export function AgentList() {
  const state = useStore($agentHub)
  const [showCreate, setShowCreate] = useState(false)

  const filtered = useMemo(() => {
    let list = state.agents

    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase()
      list = list.filter(a => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q))
    }

    if (state.filterStatus !== 'all') {
      list = list.filter(a => a.status === state.filterStatus)
    }

    if (state.filterTemplate !== 'all') {
      list = list.filter(a => a.template === state.filterTemplate)
    }

    return list
  }, [state.agents, state.searchQuery, state.filterStatus, state.filterTemplate])

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-3 border-b px-6 py-3">
        <Input
          className="max-w-xs font-mono text-sm"
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search agents..."
          value={state.searchQuery}
        />
        <Select onValueChange={v => setFilterStatus(v as typeof state.filterStatus)} value={state.filterStatus}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="stopped">Stopped</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="created">Created</SelectItem>
          </SelectContent>
        </Select>
        <Select onValueChange={v => setFilterTemplate(v as typeof state.filterTemplate)} value={state.filterTemplate}>
          <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {TEMPLATES.map(([key, label]) => <SelectItem key={key} value={key}>{label}</SelectItem>)}
          </SelectContent>
        </Select>
        <div className="ml-auto flex gap-2">
          <Button onClick={() => setShowCreate(!showCreate)} size="sm" variant="default">
            Create Agent
          </Button>
        </div>
      </div>

      {showCreate && (
        <div className="grid grid-cols-4 gap-2 border-b p-4">
          {TEMPLATES.map(([key, label]) => (
            <button
              className="flex items-center gap-3 rounded-lg border p-3 text-left text-sm transition-all hover:border-primary/50 hover:bg-accent"
              key={key}
              onClick={() => { createAgent(key); setShowCreate(false) }}
              type="button"
            >
              <span className="text-lg">{TEMPLATE_ICONS[key] || '✦'}</span>
              <div>
                <div className="font-medium">{label}</div>
                <div className="text-xs text-muted-foreground truncate">{TEMPLATE_DEFAULTS[key].description}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No agents found. Create one to get started.</p>
          ) : (
            filtered.map(agent => {
              const glyph = STATUS_GLYPH[agent.status] || STATUS_GLYPH.created

              return (
                <div className="flex items-center gap-4 rounded-xl border p-4 transition-all hover:bg-accent/30" key={agent.id}>
                  <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/10 text-sm font-bold')}>
                    {TEMPLATE_ICONS[agent.template] || agent.avatar}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{agent.name}</span>
                      <span className={cn('h-2 w-2 rounded-full', glyph.color)} />
                      <span className="text-xs text-muted-foreground">{glyph.label}</span>
                      <Badge className="text-[10px] h-5" variant="outline">{TEMPLATE_LABELS[agent.template]}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {agent.description} · {agent.runCount} runs · Last: {agent.lastRunAt ? new Date(agent.lastRunAt).toLocaleDateString() : 'Never'}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    {agent.status === 'running' ? (
                      <Button onClick={() => setAgentStatus(agent.id, 'stopped')} size="sm" variant="outline">Stop</Button>
                    ) : agent.status === 'paused' ? (
                      <Button onClick={() => setAgentStatus(agent.id, 'running')} size="sm" variant="outline">Resume</Button>
                    ) : (
                      <Button className="bg-green-600 hover:bg-green-700" onClick={() => setAgentStatus(agent.id, 'running')} size="sm" variant="default">Run</Button>
                    )}
                    <Button onClick={() => setEditingAgent(agent)} size="sm" variant="ghost">Config</Button>
                    <Button onClick={() => duplicateAgent(agent.id)} size="sm" title="Duplicate" variant="ghost">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <rect height="13" rx="2" width="13" x="9" y="9" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                      </svg>
                    </Button>
                    <Button className="text-destructive hover:text-destructive" onClick={() => deleteAgent(agent.id)} size="sm" variant="ghost">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                      </svg>
                    </Button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
