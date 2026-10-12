import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { cn } from '@/lib/utils'
import { $agentHub, setEditingAgent } from '@/store/agent-hub'

import { AgentConfigPanel } from './agent-config'
import { AgentList } from './agent-list'
import { AutomationBuilder } from './automation-builder'
import { Marketplace } from './marketplace'
import { MonitoringDashboard } from './monitoring-dashboard'
import { MultiAgentWorkflow } from './multi-agent'
import { TaskManager } from './task-manager'

const TABS = [
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'workflows', label: 'Workflows', icon: '↗' },
  { id: 'automation', label: 'Automation', icon: '⚡' },
  { id: 'tasks', label: 'Tasks', icon: '📋' },
  { id: 'monitor', label: 'Monitor', icon: '📊' },
  { id: 'marketplace', label: 'Marketplace', icon: '🏪' }
] as const

type TabId = (typeof TABS)[number]['id']

interface AgentHubViewProps {
  onClose?: () => void
}

export function AgentHubView({ onClose }: AgentHubViewProps) {
  const state = useStore($agentHub)
  const [activeTab, setActiveTab] = useState<TabId>('agents')

  const editing = state.editingAgent

  if (editing) {
    return <AgentConfigPanel agent={editing} onBack={() => setEditingAgent(null)} />
  }

  const runningCount = state.agents.filter(a => a.status === 'running').length
  const activeTasks = state.tasks.filter(t => t.status === 'running' || t.status === 'queued').length

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      <header className="flex shrink-0 items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-xl font-semibold">Agent Hub</h1>
            <p className="text-sm text-muted-foreground">
              {state.agents.length} agents · {runningCount} running · {activeTasks} active tasks · {state.workflows.length} workflows
            </p>
          </div>
        </div>
        {onClose && (
          <button className="text-muted-foreground hover:text-foreground" onClick={onClose} type="button">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </header>

      <div className="flex shrink-0 items-center gap-1 border-b px-4">
        {TABS.map(tab => (
          <button
            className={cn(
              'flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <span className="text-xs">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'agents' && <AgentList />}
      {activeTab === 'workflows' && <MultiAgentWorkflow />}
      {activeTab === 'automation' && <AutomationBuilder />}
      {activeTab === 'tasks' && <TaskManager />}
      {activeTab === 'monitor' && <MonitoringDashboard />}
      {activeTab === 'marketplace' && <Marketplace />}
    </div>
  )
}


