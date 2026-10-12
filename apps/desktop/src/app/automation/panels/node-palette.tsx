import { useStore } from '@nanostores/react'
import { type DragEvent, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  $automation,
  getActionConfigs,
  getConditionConfigs,
  getTriggerConfigs,
  type NodeType,
} from '@/store/automation'

type PaletteTab = 'triggers' | 'actions' | 'conditions'

const PALETTE_TABS: { id: PaletteTab; label: string; icon: string }[] = [
  { id: 'triggers', label: 'Triggers', icon: 'zap' },
  { id: 'actions', label: 'Actions', icon: 'run-all' },
  { id: 'conditions', label: 'Conditions', icon: 'git-branch' },
]

const CATEGORY_LABELS: Record<string, string> = {
  communication: 'Communication',
  file: 'File Operations',
  code: 'Code Execution',
  git: 'Git',
  ai: 'AI & Models',
  web: 'Web',
  data: 'Data',
  flow: 'Flow Control',
  integration: 'Integration',
}

export function NodePalette() {
  const state = useStore($automation)
  const [activeTab, setActiveTab] = useState<PaletteTab>('triggers')
  const [searchQuery, setSearchQuery] = useState('')
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(new Set())

  const triggers = getTriggerConfigs()
  const actions = getActionConfigs()
  const conditions = getConditionConfigs()

  const filteredTriggers = triggers.filter(t =>
    t.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredActions = actions.filter(a =>
    a.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredConditions = conditions.filter(c =>
    c.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const groupedActions = filteredActions.reduce<Record<string, typeof filteredActions>>((acc, a) => {
    const cat = a.category || 'other'

    if (!acc[cat]) {acc[cat] = []}
    acc[cat].push(a)

    return acc
  }, {})

  const handleDragStart = (e: DragEvent, type: NodeType, kind: string, label: string) => {
    e.dataTransfer.setData('application/aetheros-node', JSON.stringify({ type, kind, label }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  const toggleCategory = (cat: string) => {
    const next = new Set(collapsedCategories)

    if (next.has(cat)) {next.delete(cat)}
    else {next.add(cat)}

    setCollapsedCategories(next)
  }

  return (
    <div className="flex w-64 flex-col border-r border-(--ui-stroke-tertiary) bg-(--ui-sidebar-surface-background)">
      <div className="flex items-center gap-0.5 border-b border-(--ui-stroke-tertiary) px-2 py-1.5">
        {PALETTE_TABS.map(tab => (
          <button
            className={cn(
              'flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors',
              activeTab === tab.id
                ? 'bg-(--ui-control-hover-background) text-foreground'
                : 'text-(--ui-text-tertiary) hover:text-foreground'
            )}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <Codicon name={tab.icon as any} size="0.75rem" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="border-b border-(--ui-stroke-tertiary) px-2 py-1.5">
        <input
          className="w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-control-hover-background) px-2 py-1 text-xs text-foreground placeholder:text-(--ui-text-tertiary) focus:outline-none focus:ring-1 focus:ring-primary"
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search nodes..."
          type="text"
          value={searchQuery}
        />
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-0.5 p-2">
          {activeTab === 'triggers' && filteredTriggers.map(trigger => (
            <DraggableNodeButton
              description={trigger.description}
              icon={trigger.icon}
              key={trigger.kind}
              kind={trigger.kind}
              label={trigger.label}
              onDragStart={handleDragStart}
              type="trigger"
            />
          ))}

          {activeTab === 'actions' && Object.entries(groupedActions).map(([cat, catActions]) => (
            <div key={cat}>
              <button
                className="flex w-full items-center gap-1 px-1 py-1 text-[10px] font-semibold uppercase tracking-wider text-(--ui-text-tertiary)"
                onClick={() => toggleCategory(cat)}
                type="button"
              >
                <Codicon name={collapsedCategories.has(cat) ? 'chevron-right' : 'chevron-down'} size="0.625rem" />
                {CATEGORY_LABELS[cat] || cat}
              </button>
              {!collapsedCategories.has(cat) && catActions.map(action => (
                <DraggableNodeButton
                  description={action.description}
                  icon={action.icon}
                  key={action.kind}
                  kind={action.kind}
                  label={action.label}
                  onDragStart={handleDragStart}
                  type="action"
                />
              ))}
            </div>
          ))}

          {activeTab === 'conditions' && filteredConditions.map(condition => (
            <DraggableNodeButton
              description={condition.description}
              icon={condition.icon}
              key={condition.kind}
              kind={condition.kind}
              label={condition.label}
              onDragStart={handleDragStart}
              type="condition"
            />
          ))}

          {activeTab === 'actions' && Object.keys(groupedActions).length === 0 && (
            <p className="py-4 text-center text-[11px] text-(--ui-text-tertiary)">No actions found</p>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

function DraggableNodeButton({
  type,
  kind,
  label,
  description,
  icon,
  onDragStart,
}: {
  type: NodeType
  kind: string
  label: string
  description: string
  icon: string
  onDragStart: (e: DragEvent, type: NodeType, kind: string, label: string) => void
}) {
  return (
    <div
      className="group cursor-grab rounded-lg border border-transparent px-2 py-1.5 transition-colors hover:border-(--ui-stroke-tertiary) hover:bg-(--ui-control-hover-background) active:cursor-grabbing"
      draggable
      onDragStart={e => onDragStart(e, type, kind, label)}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm text-(--ui-text-tertiary) group-hover:text-foreground">
          <Codicon name={icon as any} size="0.875rem" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-medium text-foreground">{label}</div>
          <div className="truncate text-[10px] text-(--ui-text-tertiary)">{description}</div>
        </div>
      </div>
    </div>
  )
}
