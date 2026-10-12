import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  $automation,
  addSecret,
  deleteSecret,
} from '@/store/automation'

export function SecretsPanel() {
  const state = useStore($automation)
  const [showNew, setShowNew] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newValue, setNewValue] = useState('')

  const handleAdd = () => {
    if (!newName.trim() || !newValue.trim()) {return}
    addSecret(newName.trim(), newDescription.trim())
    setNewName('')
    setNewDescription('')
    setNewValue('')
    setShowNew(false)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3">
        <div className="flex items-center gap-2">
          <Codicon className="text-amber-400" name="lock" size="1rem" />
          <h2 className="text-base font-semibold">Secrets Manager</h2>
        </div>
        <Button onClick={() => setShowNew(true)} size="sm">
          <Codicon className="mr-1" name="add" size="0.875rem" />
          Add Secret
        </Button>
      </div>

      {showNew && (
        <div className="border-b border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) p-6">
          <div className="mx-auto max-w-lg space-y-3">
            <h3 className="text-sm font-medium">New Secret</h3>
            <input
              autoFocus
              className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
              onChange={e => setNewName(e.target.value)}
              placeholder="Secret name (e.g., API_KEY)"
              type="text"
              value={newName}
            />
            <input
              className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
              onChange={e => setNewDescription(e.target.value)}
              placeholder="Description (optional)"
              type="text"
              value={newDescription}
            />
            <div>
              <input
                className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
                onChange={e => setNewValue(e.target.value)}
                placeholder="Secret value"
                type="password"
                value={newValue}
              />
              <p className="mt-1 text-[10px] text-(--ui-text-tertiary)">Value is encrypted at rest and never exposed in the UI</p>
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => { setShowNew(false); setNewName(''); setNewDescription(''); setNewValue('') }} size="sm" variant="ghost">Cancel</Button>
              <Button onClick={handleAdd} size="sm">Save Secret</Button>
            </div>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-2xl space-y-2 p-6">
          {state.secrets.length === 0 && (
            <div className="py-12 text-center">
              <Codicon className="mx-auto mb-3 text-(--ui-text-tertiary)" name="lock" size="2rem" />
              <p className="text-sm text-(--ui-text-tertiary)">No secrets stored</p>
              <p className="text-xs text-(--ui-text-tertiary) mt-1">Add API keys, passwords, and tokens securely</p>
            </div>
          )}
          {state.secrets.map(secret => (
            <div className="flex items-center gap-3 rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3" key={secret.id}>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
                <Codicon className="text-amber-400" name="lock" size="1rem" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{secret.name}</span>
                  <span className="rounded bg-(--ui-stroke-tertiary) px-1.5 py-0.5 text-[9px] font-medium text-(--ui-text-tertiary)">ENCRYPTED</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-(--ui-text-tertiary)">
                  <span>{secret.maskedValue}</span>
                  <span>·</span>
                  <span>Created {new Date(secret.createdAt).toLocaleDateString()}</span>
                </div>
              </div>
              <button
                className="rounded p-1.5 text-(--ui-text-tertiary) hover:text-destructive"
                onClick={() => deleteSecret(secret.id)}
                type="button"
              >
                <Codicon name="trash" size="0.875rem" />
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
