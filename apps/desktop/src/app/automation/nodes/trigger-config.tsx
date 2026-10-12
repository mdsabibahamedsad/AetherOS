import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  $automation,
  getTriggerConfigByKind,
  getTriggerConfigs,
  setEditingNode,
  updateNodeConfig,
} from '@/store/automation'

interface TriggerConfigModalProps {
  nodeId: string
}

export function TriggerConfigModal({ nodeId }: TriggerConfigModalProps) {
  const state = useStore($automation)
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)
  const node = workflow?.nodes.find(n => n.id === nodeId)
  const config = node ? getTriggerConfigByKind(node.kind as any) : null

  const [label, setLabel] = useState(() => node?.config.label || config?.label || '')
  const [description, setDescription] = useState(() => node?.config.description || '')
  const [configValues, setConfigValues] = useState<Record<string, unknown>>(() => (node?.config as any) || {})

  if (!node || !config || !workflow) {return null}

  const handleSave = () => {
    updateNodeConfig(nodeId, { label, description, ...configValues })
    setEditingNode(null)
  }

  const allTriggers = getTriggerConfigs()

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setEditingNode(null)}>
      <div className="flex max-h-[80vh] w-[520px] flex-col rounded-xl border bg-background shadow-xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-5 py-3">
          <div className="flex items-center gap-2">
            <Codicon className="text-emerald-400" name="zap" size="1rem" />
            <h2 className="text-base font-semibold">Configure Trigger</h2>
          </div>
          <button className="text-(--ui-text-tertiary) hover:text-foreground" onClick={() => setEditingNode(null)} type="button">
            <Codicon name="close" size="1rem" />
          </button>
        </div>

        <ScrollArea className="flex-1">
          <div className="space-y-4 p-5">
            <div>
              <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Trigger Type</label>
              <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-2">
                <Codicon className="text-emerald-400" name={config.icon as any} size="1rem" />
                <span className="text-sm font-medium text-foreground">{config.label}</span>
                <span className="text-xs text-(--ui-text-tertiary)">— {config.description}</span>
              </div>
            </div>

            <Separator />

            <div>
              <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Display Label</label>
              <input
                className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                onChange={e => setLabel(e.target.value)}
                type="text"
                value={label}
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">Description</label>
              <textarea
                className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
                onChange={e => setDescription(e.target.value)}
                rows={2}
                value={description}
              />
            </div>

            {config.configFields.length > 0 && (
              <>
                <Separator />
                <p className="text-xs font-medium text-(--ui-text-tertiary)">Configuration</p>
                {config.configFields.map(field => (
                  <div key={field.name}>
                    <label className="mb-1 block text-xs font-medium text-(--ui-text-tertiary)">
                      {field.label}
                      {field.required && <span className="ml-1 text-red-400">*</span>}
                    </label>
                    {field.type === 'text' && (
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setConfigValues({ ...configValues, [field.name]: e.target.value })}
                        placeholder={field.placeholder}
                        type="text"
                        value={(configValues[field.name] as string) ?? ''}
                      />
                    )}
                    {field.type === 'number' && (
                      <input
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setConfigValues({ ...configValues, [field.name]: parseFloat(e.target.value) })}
                        placeholder={field.placeholder}
                        type="number"
                        value={(configValues[field.name] as number) ?? (field.defaultValue as number) ?? 0}
                      />
                    )}
                    {field.type === 'boolean' && (
                      <label className="flex items-center gap-2">
                        <input
                          checked={(configValues[field.name] as boolean) ?? (field.defaultValue as boolean) ?? false}
                          className="rounded border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) text-primary focus:ring-primary"
                          onChange={e => setConfigValues({ ...configValues, [field.name]: e.target.checked })}
                          type="checkbox"
                        />
                        <span className="text-xs text-(--ui-text-tertiary)">{field.label}</span>
                      </label>
                    )}
                    {field.type === 'select' && (
                      <select
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setConfigValues({ ...configValues, [field.name]: e.target.value })}
                        value={(configValues[field.name] as string) ?? ''}
                      >
                        <option value="">Select...</option>
                        {field.options?.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    )}
                    {field.type === 'textarea' && (
                      <textarea
                        className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-3 py-1.5 text-sm text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
                        onChange={e => setConfigValues({ ...configValues, [field.name]: e.target.value })}
                        placeholder={field.placeholder}
                        rows={3}
                        value={(configValues[field.name] as string) ?? ''}
                      />
                    )}
                    {field.description && (
                      <p className="mt-0.5 text-[10px] text-(--ui-text-tertiary)">{field.description}</p>
                    )}
                  </div>
                ))}
              </>
            )}
          </div>
        </ScrollArea>

        <div className="flex items-center justify-end gap-2 border-t px-5 py-3">
          <Button onClick={() => setEditingNode(null)} size="sm" variant="ghost">Cancel</Button>
          <Button onClick={handleSave} size="sm">Save</Button>
        </div>
      </div>
    </div>
  )
}
