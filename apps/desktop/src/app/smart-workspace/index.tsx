import { useStore } from '@nanostores/react'
import {
  IconHierarchy2,
  IconLayoutDashboard,
  IconLayoutGrid,
  IconList,
  IconNotebook,
  IconPaint,
  IconPencil,
  IconPlus,
  IconTimeline
} from '@tabler/icons-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { SearchField } from '@/components/ui/search-field'
import { cn } from '@/lib/utils'
import { $smartWorkspace, setNotesView, setSearchQuery } from '@/store/smart-workspace'

import { AICanvas } from './ai-canvas'
import { MindMap } from './mind-map'
import { Notes } from './notes'
import { Scratchpad } from './scratchpad'
import { Whiteboard } from './whiteboard'

type WorkspaceTab = 'canvas' | 'scratchpad' | 'notes' | 'whiteboard' | 'mindmap'

const TABS: { id: WorkspaceTab; label: string; icon: typeof IconLayoutDashboard }[] = [
  { id: 'canvas', label: 'AI Canvas', icon: IconLayoutDashboard },
  { id: 'scratchpad', label: 'Scratchpad', icon: IconPencil },
  { id: 'notes', label: 'Notes', icon: IconNotebook },
  { id: 'whiteboard', label: 'Whiteboard', icon: IconPaint },
  { id: 'mindmap', label: 'Mind Map', icon: IconHierarchy2 }
]

const VIEW_OPTIONS = [
  { id: 'grid' as const, label: 'Grid', icon: IconLayoutGrid },
  { id: 'list' as const, label: 'List', icon: IconList },
  { id: 'timeline' as const, label: 'Timeline', icon: IconTimeline }
]

export function SmartWorkspaceView() {
  const state = useStore($smartWorkspace)
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('canvas')

  return (
    <div className="flex h-full flex-col">
      <header className="flex shrink-0 items-center gap-3 border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <nav className="flex items-center gap-1">
          {TABS.map(tab => {
            const Icon = tab.icon

            return (
              <button
                aria-selected={activeTab === tab.id}
                className={cn(
                  'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-accent text-foreground shadow-xs'
                    : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                type="button"
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <SearchField
            containerClassName="min-w-48"
            onChange={setSearchQuery}
            placeholder="Search workspace..."
            value={state.searchQuery}
          />
          {activeTab === 'notes' && (
            <div className="flex items-center gap-0.5 rounded-md bg-(--ui-bg-tertiary) p-0.5">
              {VIEW_OPTIONS.map(opt => {
                const ViewIcon = opt.icon

                return (
                  <button
                    aria-label={opt.label}
                    className={cn(
                      'rounded px-1.5 py-1 text-muted-foreground transition-colors hover:text-foreground',
                      state.notesView === opt.id && 'bg-background text-foreground shadow-xs'
                    )}
                    key={opt.id}
                    onClick={() => setNotesView(opt.id)}
                    type="button"
                  >
                    <ViewIcon className="size-3.5" />
                  </button>
                )
              })}
            </div>
          )}
          <Button onClick={() => {}} size="sm">
            <IconPlus className="size-3.5" />
            New
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1">
        {activeTab === 'canvas' && <AICanvas />}
        {activeTab === 'scratchpad' && <Scratchpad />}
        {activeTab === 'notes' && <Notes />}
        {activeTab === 'whiteboard' && <Whiteboard />}
        {activeTab === 'mindmap' && <MindMap />}
      </div>
    </div>
  )
}
