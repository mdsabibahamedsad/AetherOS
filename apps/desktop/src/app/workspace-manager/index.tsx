import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import {
  Activity,
  FolderOpen,
  Layers3,
  Plus,
  SearchIcon as Search,
  Trash2,
  Users,
  Wrench
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  $workspaceManager,
  addLayout,
  removeGroup,
  removeLayout,
  setActiveLayout,
  setWorkspaceSearch,
  setWorkspaceTab
} from '@/store/workspace-manager'
import type { WorkspaceLayout } from '@/store/workspace-manager'

const TYPE_ICONS: Record<string, any> = {
  session: Activity,
  file: Codicon,
  terminal: Wrench,
  preview: Activity,
  settings: Wrench
}

const TYPE_LABELS: Record<string, string> = {
  session: 'Chat Session',
  file: 'File',
  terminal: 'Terminal',
  preview: 'Preview',
  settings: 'Settings'
}

export function WorkspaceManagerView() {
  const state = useStore($workspaceManager)

  const tabs = [
    { id: 'layouts' as const, label: 'Layouts', icon: Layers3 },
    { id: 'sessions' as const, label: 'Session Groups', icon: Users },
    { id: 'shortcuts' as const, label: 'Shortcuts', icon: FolderOpen }
  ]

  const filteredShortcuts = useMemo(() => {
    const q = state.searchQuery.toLowerCase()

    if (!q) {return state.shortcuts}

    return state.shortcuts.filter(s => s.name.toLowerCase().includes(q) || s.path.toLowerCase().includes(q))
  }, [state.shortcuts, state.searchQuery])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Workspace Manager</PageTitle>
            <PageDescription>Manage layouts, session groups, and workspace shortcuts</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-0">
        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {tabs.map(tab => {
            const Icon = tab.icon

            return (
              <button
                className={cn(
                  'flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors',
                  state.selectedTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setWorkspaceTab(tab.id)}
                type="button"
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {state.selectedTab === 'layouts' && (
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {state.layouts.map(layout => (
                <LayoutCard isActive={layout.id === state.activeLayoutId} key={layout.id} layout={layout} />
              ))}
            </div>
            <Button
              className="w-full"
              onClick={() => {
                const id = `layout-${Date.now()}`
                addLayout({
                  id, name: 'New Layout', tabs: [{ id: `tab-${id}`, title: 'New Tab', type: 'session' }], activeTabId: null
                })
                notify({ kind: 'success', title: 'Layout', message: 'New layout created' })
              }}
              size="xs"
              variant="text"
            >
              <Plus className="size-3 mr-1" /> New Layout
            </Button>
          </div>
        )}

        {state.selectedTab === 'sessions' && (
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {state.groups.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">No session groups created</p>
            ) : state.groups.map(group => (
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4" key={group.id}>
                <div className="flex items-center gap-3">
                  <div className="size-3 rounded-full shrink-0" style={{ backgroundColor: group.color }} />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-foreground">{group.name}</div>
                    <div className="text-[0.6rem] text-muted-foreground">{group.sessionIds.length} sessions</div>
                  </div>
                  <Button
                    className="text-muted-foreground hover:text-red-500"
                    onClick={() => { removeGroup(group.id); notify({ kind: 'info', title: 'Group', message: 'Group removed' }) }}
                    size="icon-xs"
                    variant="ghost"
                  >
                    <Trash2 className="size-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {state.selectedTab === 'shortcuts' && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
              <Search className="size-3 text-muted-foreground" />
              <input
                className="min-w-0 flex-1 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground/60"
                onChange={e => setWorkspaceSearch(e.target.value)}
                placeholder="Search shortcuts..."
                value={state.searchQuery}
              />
            </div>
            <div className="flex-1 space-y-1 overflow-y-auto p-4">
              {filteredShortcuts.length === 0 ? (
                <p className="py-8 text-center text-xs text-muted-foreground">
                  {state.searchQuery ? 'No shortcuts match your search' : 'No workspace shortcuts'}
                </p>
              ) : filteredShortcuts.map(sc => (
                <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-xs transition-colors hover:bg-accent/60" key={sc.id}>
                  <FolderOpen className="size-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-foreground">{sc.name}</div>
                    <div className="text-muted-foreground">{sc.path}</div>
                  </div>
                  <Badge variant="secondary">{sc.type}</Badge>
                  {sc.lastOpened && (
                    <span className="shrink-0 text-muted-foreground/60">{formatRelative(sc.lastOpened)}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}

function LayoutCard({ layout, isActive }: { layout: WorkspaceLayout; isActive: boolean }) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-colors cursor-pointer',
        isActive ? 'border-primary/40 bg-accent/30' : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
      )}
      onClick={() => { setActiveLayout(layout.id); notify({ kind: 'info', title: 'Layout', message: `Switched to "${layout.name}" layout` }) }
    }
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-xs font-semibold text-foreground">{layout.name}</h4>
        {isActive && <Badge className="bg-primary/10 text-primary" variant="secondary">Active</Badge>}
      </div>
      <div className="mt-2 space-y-1">
        {layout.tabs.map(tab => {
          const Icon = TYPE_ICONS[tab.type] || Activity

          return (
            <div className="flex items-center gap-2 text-[0.6rem] text-muted-foreground" key={tab.id}>
              <Icon className="size-2.5 shrink-0" />
              <span className="truncate">{tab.title}</span>
              <span className="ml-auto text-muted-foreground/60">{TYPE_LABELS[tab.type]}</span>
            </div>
          )
        })}
      </div>
      {layout.splitDirection && (
        <div className="mt-2 text-[0.55rem] text-muted-foreground/60">
          Split: {layout.splitDirection} ({layout.splitPosition}%)
        </div>
      )}
      <div className="mt-3 flex gap-1">
        <Button
          className="text-muted-foreground hover:text-red-500"
          onClick={e => { e.stopPropagation(); removeLayout(layout.id); notify({ kind: 'info', title: 'Layout', message: 'Layout removed' }) }}
          size="icon-xs"
          variant="ghost"
        >
          <Trash2 className="size-3" />
        </Button>
      </div>
    </div>
  )
}

function formatRelative(ts: number): string {
  const diff = Date.now() - ts

  if (diff < 60000) {return 'now'}

  if (diff < 3600000) {return `${Math.floor(diff / 60000)}m ago`}

  if (diff < 86400000) {return `${Math.floor(diff / 3600000)}h ago`}

  return `${Math.floor(diff / 86400000)}d ago`
}
