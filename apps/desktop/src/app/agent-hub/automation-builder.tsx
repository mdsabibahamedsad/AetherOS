import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import {
  $agentHub,
  createAutomation,
  deleteAutomation,
  type TriggerType,
  updateAutomation
} from '@/store/agent-hub'

const TRIGGER_LABELS: Record<TriggerType, string> = {
  manual: 'Manual',
  schedule: 'Schedule',
  'file-change': 'File Change',
  webhook: 'Webhook',
  'git-commit': 'Git Commit',
  email: 'Email',
  startup: 'Startup',
  shutdown: 'Shutdown'
}

const TRIGGER_ICONS: Record<TriggerType, string> = {
  manual: '▶',
  schedule: '⏰',
  'file-change': '📁',
  webhook: '🔗',
  'git-commit': '📝',
  email: '📧',
  startup: '🟢',
  shutdown: '🔴'
}

const TRIGGER_DESCS: Record<TriggerType, string> = {
  manual: 'Triggered manually by the user',
  schedule: 'Runs on a cron schedule',
  'file-change': 'Triggers when files are created or modified',
  webhook: 'Triggered by an incoming webhook',
  'git-commit': 'Runs on new git commits',
  email: 'Triggered by incoming email',
  startup: 'Runs when AetherOS starts',
  shutdown: 'Runs when AetherOS shuts down'
}

export function AutomationBuilder() {
  const state = useStore($agentHub)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newTrigger, setNewTrigger] = useState<TriggerType>('manual')

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Automation</h2>
          <p className="text-sm text-muted-foreground">Trigger agents and workflows automatically</p>
        </div>
        <Button onClick={() => setCreating(true)} size="sm">New Rule</Button>
      </div>

      {creating && (
        <div className="border-b p-4">
          <div className="mx-auto max-w-lg space-y-4">
            <h3 className="font-medium">Create Automation Rule</h3>
            <div className="grid grid-cols-4 gap-3">
              {(Object.entries(TRIGGER_LABELS) as [TriggerType, string][]).map(([key, label]) => (
                <button
                  className={cn('flex flex-col items-center gap-1 rounded-lg border p-3 text-sm transition-all', newTrigger === key ? 'border-primary/50 bg-primary/5' : '')}
                  key={key}
                  onClick={() => setNewTrigger(key)}
                  type="button"
                >
                  <span className="text-lg">{TRIGGER_ICONS[key]}</span>
                  <span className="text-xs font-medium">{label}</span>
                  <span className="text-[10px] text-muted-foreground text-center">{TRIGGER_DESCS[key]}</span>
                </button>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setCreating(false)} variant="outline">Cancel</Button>
              <Button onClick={() => { if (newName.trim()) { createAutomation(newName.trim(), newTrigger); setCreating(false); setNewName('') } }}>Create</Button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-3">
          {state.automations.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No automation rules yet. Create one to automate your workflows.</p>
          ) : (
            state.automations.map(rule => {
              const linkedWorkflow = state.workflows.find(w => w.id === rule.workflowId)

              return (
                <div className="flex items-center gap-4 rounded-xl border p-4 transition-all hover:bg-accent/30" key={rule.id}>
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/10 text-lg">
                    {TRIGGER_ICONS[rule.trigger]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{rule.name}</span>
                      <Badge className="text-[10px] h-5" variant="outline">{TRIGGER_LABELS[rule.trigger]}</Badge>
                      {linkedWorkflow && <Badge className="text-[10px] h-5" variant="secondary">{linkedWorkflow.name}</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {TRIGGER_DESCS[rule.trigger]}
                      {rule.lastTriggeredAt && <> · Last triggered: {new Date(rule.lastTriggeredAt).toLocaleString()}</>}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Select
                      onValueChange={v => updateAutomation(rule.id, { workflowId: v || null })}
                      value={rule.workflowId ?? ''}
                    >
                      <SelectTrigger className="w-36"><SelectValue placeholder="Link workflow" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">None</SelectItem>
                        {state.workflows.map(w => <SelectItem key={w.id} value={w.id}>{w.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Switch
                      checked={rule.enabled}
                      onCheckedChange={v => updateAutomation(rule.id, { enabled: v })}
                    />
                    <Button className="text-destructive" onClick={() => deleteAutomation(rule.id)} size="sm" variant="ghost">
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
