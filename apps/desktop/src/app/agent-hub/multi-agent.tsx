import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import {
  $agentHub,
  addWorkflowAgent,
  createWorkflow,
  deleteWorkflow,
  getWorkflowAgentRoles,
  removeWorkflowAgent,
  updateWorkflow,
  type WorkflowType
} from '@/store/agent-hub'

const WORKFLOW_TYPE_LABELS: Record<WorkflowType, string> = {
  sequential: 'Sequential',
  parallel: 'Parallel',
  coordinator: 'Coordinator'
}

const WORKFLOW_TYPE_DESCS: Record<WorkflowType, string> = {
  sequential: 'Agents run one after another, each building on the previous result',
  parallel: 'Agents run simultaneously, results merged at the end',
  coordinator: 'A coordinator agent delegates to specialist sub-agents'
}

export function MultiAgentWorkflow() {
  const state = useStore($agentHub)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState<WorkflowType>('sequential')

  const roles = getWorkflowAgentRoles()
  const availableAgents = state.agents.filter(a => a.status !== 'error')

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Multi-Agent Workflows</h2>
          <p className="text-sm text-muted-foreground">Coordinate multiple agents to work together</p>
        </div>
        <Button onClick={() => setCreating(true)} size="sm">New Workflow</Button>
      </div>

      {creating && (
        <div className="border-b p-4">
          <div className="mx-auto max-w-lg space-y-4">
            <h3 className="font-medium">Create Workflow</h3>
            <div className="space-y-2">
              <Label>Name</Label>
              <Input onChange={e => setNewName(e.target.value)} placeholder="My Workflow" value={newName} />
            </div>
            <div className="space-y-2">
              <Label>Type</Label>
              <div className="grid grid-cols-3 gap-2">
                {(Object.entries(WORKFLOW_TYPE_LABELS) as [WorkflowType, string][]).map(([key, label]) => (
                  <button
                    className={cn('rounded-lg border p-3 text-left text-sm transition-all', newType === key ? 'border-primary/50 bg-primary/5' : '')}
                    key={key}
                    onClick={() => setNewType(key)}
                    type="button"
                  >
                    <div className="font-medium">{label}</div>
                    <div className="text-xs text-muted-foreground mt-1">{WORKFLOW_TYPE_DESCS[key]}</div>
                  </button>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setCreating(false)} variant="outline">Cancel</Button>
              <Button onClick={() => { if (newName.trim()) { createWorkflow(newName.trim(), newType); setCreating(false); setNewName('') } }}>Create</Button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl space-y-4">
          {state.workflows.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No workflows yet. Create one to coordinate multiple agents.</p>
          ) : (
            state.workflows.map(wf => (
              <div className="rounded-xl border p-5" key={wf.id}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-lg',
                      wf.type === 'coordinator' ? 'bg-purple-500/20 text-purple-600' :
                      wf.type === 'parallel' ? 'bg-blue-500/20 text-blue-600' :
                      'bg-green-500/20 text-green-600'
                    )}>
                      {wf.type === 'coordinator' ? 'C' : wf.type === 'parallel' ? '∥' : '→'}
                    </div>
                    <div>
                      <h3 className="font-medium">{wf.name}</h3>
                      <p className="text-xs text-muted-foreground">{WORKFLOW_TYPE_LABELS[wf.type]} · {wf.agents.length} agents · {wf.steps.length} steps</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch checked={wf.enabled} onCheckedChange={v => updateWorkflow(wf.id, { enabled: v })} />
                    <Button className="text-destructive" onClick={() => deleteWorkflow(wf.id)} size="sm" variant="ghost">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                      </svg>
                    </Button>
                  </div>
                </div>

                {wf.agents.length === 0 ? (
                  <div className="mt-4 space-y-2">
                    <p className="text-sm text-muted-foreground">Add agents to this workflow</p>
                    <div className="flex flex-wrap gap-2">
                      {roles.map(role => {
                        const assigned = availableAgents.find(a => wf.agents.some(wa => wa.role === role.role && wa.agentId === a.id))

                        return (
                          <button
                            className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs hover:bg-accent"
                            key={role.role}
                            onClick={() => {
                              const agent = availableAgents.find(a => !wf.agents.some(wa => wa.agentId === a.id))

                              if (agent) {addWorkflowAgent(wf.id, role.role, agent.id)}
                            }}
                            type="button"
                          >
                            <span className="font-medium">{role.label}</span>
                            <span className="text-muted-foreground">— {role.description}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 flex items-center gap-2">
                    {wf.agents.map((wa, i) => {
                      const agent = state.agents.find(a => a.id === wa.agentId)
                      const role = roles.find(r => r.role === wa.role)

                      return (
                        <div className="flex items-center gap-2" key={wa.agentId}>
                          {i > 0 && <span className={cn('text-muted-foreground', wf.type === 'parallel' ? 'mx-1' : 'mx-2')}>{wf.type === 'parallel' ? '∥' : '→'}</span>}
                          <div className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm">
                            <div className="h-6 w-6 rounded bg-primary/10 flex items-center justify-center text-xs font-bold">{agent?.name?.charAt(0) || '?'}</div>
                            <div>
                              <div className="text-xs font-medium">{agent?.name || 'Unknown'}</div>
                              <div className="text-[10px] text-muted-foreground">{role?.label || wa.role}</div>
                            </div>
                            <button className="text-muted-foreground hover:text-destructive ml-1" onClick={() => removeWorkflowAgent(wf.id, wa.agentId)} type="button">
                              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12" /></svg>
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
