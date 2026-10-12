import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  $automation,
  addVariable,
  deleteVariable,
  setShowVariablesPanel,
  type VariableScope,
  type WorkflowVariable,
} from '@/store/automation'

export function VariablesPanel() {
  const state = useStore($automation)
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)
  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newScope, setNewScope] = useState<VariableScope>('workflow')
  const [newType, setNewType] = useState<WorkflowVariable['type']>('string')
  const [newValue, setNewValue] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)

  if (!workflow) {return null}

  const handleAdd = () => {
    if (!newName.trim()) {return}
    addVariable({
      id: `var-${Date.now()}`,
      name: newName.trim(),
      scope: newScope,
      type: newType,
      value: newValue,
      description: '',
      encrypted: newScope === 'secret',
    })
    setNewName('')
    setNewValue('')
    setShowNew(false)
  }

  const SCOPE_ICONS: Record<VariableScope, string> = {
    workflow: 'type-hierarchy',
    global: 'globe',
    session: 'comment-discussion',
    environment: 'terminal',
    secret: 'lock',
    output: 'output',
    input: 'input',
  }

  return (
    <div className="flex w-72 flex-col border-l border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background)">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary)">Variables</span>
        <div className="flex items-center gap-1">
          <button className="rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setShowNew(true)} type="button">
            <Codicon name="add" size="0.875rem" />
          </button>
          <button className="rounded p-0.5 text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setShowVariablesPanel(false)} type="button">
            <Codicon name="close" size="0.875rem" />
          </button>
        </div>
      </div>

      {showNew && (
        <div className="border-b border-(--ui-stroke-tertiary) p-3 space-y-2">
          <input
            autoFocus
            className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
            onChange={e => setNewName(e.target.value)}
            placeholder="Variable name"
            type="text"
            value={newName}
          />
          <select
            className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground focus:outline-none"
            onChange={e => setNewScope(e.target.value as VariableScope)}
            value={newScope}
          >
            <option value="workflow">Workflow</option>
            <option value="global">Global</option>
            <option value="session">Session</option>
            <option value="environment">Environment</option>
            <option value="secret">Secret</option>
            <option value="output">Output</option>
            <option value="input">Input</option>
          </select>
          <select
            className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground focus:outline-none"
            onChange={e => setNewType(e.target.value as WorkflowVariable['type'])}
            value={newType}
          >
            <option value="string">String</option>
            <option value="number">Number</option>
            <option value="boolean">Boolean</option>
            <option value="object">Object</option>
            <option value="array">Array</option>
            <option value="any">Any</option>
          </select>
          <input
            className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
            onChange={e => setNewValue(e.target.value)}
            placeholder={newScope === 'secret' ? '••••••••' : 'Default value'}
            type="text"
            value={newValue}
          />
          <div className="flex justify-end gap-1">
            <Button onClick={() => setShowNew(false)} size="sm" variant="ghost">Cancel</Button>
            <Button onClick={handleAdd} size="sm">Add</Button>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="space-y-1 p-2">
          {workflow.variables.length === 0 && (
            <p className="py-6 text-center text-xs text-(--ui-text-tertiary)">No variables yet</p>
          )}
          {workflow.variables.map(v => (
            <div className="group rounded-lg border border-transparent px-2 py-1.5 transition-colors hover:border-(--ui-stroke-tertiary)" key={v.id}>
              <div className="flex items-center gap-2">
                <Codicon className={cn(
                  'shrink-0',
                  v.scope === 'secret' ? 'text-amber-400' : 'text-(--ui-text-tertiary)'
                )} name={SCOPE_ICONS[v.scope] as any} size="0.75rem" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1">
                    <span className="truncate text-xs font-medium text-foreground">{v.name}</span>
                    <span className="shrink-0 text-[9px] text-(--ui-text-tertiary)">{v.type}</span>
                  </div>
                  <div className="truncate text-[10px] text-(--ui-text-tertiary)">
                    {v.encrypted ? '••••••••' : String(v.value ?? '')}
                  </div>
                </div>
                <button
                  className="shrink-0 rounded p-0.5 text-(--ui-text-tertiary) opacity-0 group-hover:opacity-100 hover:text-destructive"
                  onClick={() => deleteVariable(v.id)}
                  type="button"
                >
                  <Codicon name="trash" size="0.75rem" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
