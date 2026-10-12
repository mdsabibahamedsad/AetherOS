import { atom } from 'nanostores'

export interface WorkspaceTab {
  id: string
  title: string
  type: 'session' | 'file' | 'terminal' | 'preview' | 'settings'
  icon?: string
  pinned?: boolean
}

export interface WorkspaceLayout {
  id: string
  name: string
  tabs: WorkspaceTab[]
  activeTabId: string | null
  splitDirection?: 'horizontal' | 'vertical'
  splitPosition?: number
}

export interface SessionGroup {
  id: string
  name: string
  sessionIds: string[]
  color?: string
}

export interface WorkspaceShortcut {
  id: string
  name: string
  path: string
  type: 'project' | 'folder' | 'file' | 'tool'
  lastOpened?: number
}

export interface WorkspaceManagerState {
  layouts: WorkspaceLayout[]
  activeLayoutId: string | null
  groups: SessionGroup[]
  shortcuts: WorkspaceShortcut[]
  selectedTab: 'layouts' | 'sessions' | 'shortcuts'
  searchQuery: string
}

export const $workspaceManager = atom<WorkspaceManagerState>({
  layouts: [
    {
      id: 'default', name: 'Default Layout',
      tabs: [
        { id: 'tab-chat', title: 'Chat', type: 'session', icon: 'comment-discussion', pinned: true },
        { id: 'tab-terminal', title: 'Terminal', type: 'terminal', icon: 'terminal' },
        { id: 'tab-files', title: 'Files', type: 'file', icon: 'file-directory' }
      ],
      activeTabId: 'tab-chat'
    },
    {
      id: 'dev', name: 'Development',
      tabs: [
        { id: 'dev-editor', title: 'Editor', type: 'session', icon: 'code', pinned: true },
        { id: 'dev-terminal', title: 'Terminal', type: 'terminal', icon: 'terminal', pinned: true },
        { id: 'dev-preview', title: 'Preview', type: 'preview', icon: 'browser' }
      ],
      activeTabId: 'dev-editor',
      splitDirection: 'horizontal',
      splitPosition: 50
    },
    {
      id: 'monitor', name: 'Monitoring',
      tabs: [
        { id: 'mon-logs', title: 'Logs', type: 'session', icon: 'output', pinned: true },
        { id: 'mon-metrics', title: 'Metrics', type: 'file', icon: 'dashboard' },
        { id: 'mon-terminal', title: 'Terminal', type: 'terminal', icon: 'terminal' }
      ],
      activeTabId: 'mon-logs'
    }
  ],
  activeLayoutId: 'default',
  groups: [
    { id: 'work', name: 'Work', sessionIds: [], color: '#3B82F6' },
    { id: 'personal', name: 'Personal', sessionIds: [], color: '#10B981' },
    { id: 'research', name: 'Research', sessionIds: [], color: '#8B5CF6' }
  ],
  shortcuts: [
    { id: 'sc-proj', name: 'Main Project', path: '/home/user/projects/main', type: 'project', lastOpened: Date.now() },
    { id: 'sc-docs', name: 'Documentation', path: '/home/user/docs', type: 'folder', lastOpened: Date.now() - 86400000 },
    { id: 'sc-config', name: 'Config Editor', path: '/home/user/.aetheros/config.yaml', type: 'file', lastOpened: Date.now() - 172800000 }
  ],
  selectedTab: 'layouts',
  searchQuery: ''
})

const patch = (u: Partial<WorkspaceManagerState>) =>
  $workspaceManager.set({ ...$workspaceManager.get(), ...u })

export function setWorkspaceTab(tab: WorkspaceManagerState['selectedTab']) { patch({ selectedTab: tab }) }

export function setWorkspaceSearch(q: string) { patch({ searchQuery: q }) }

export function setActiveLayout(id: string | null) { patch({ activeLayoutId: id }) }

export function addLayout(layout: WorkspaceLayout) {
  patch({ layouts: [...$workspaceManager.get().layouts, layout] })
}

export function removeLayout(id: string) {
  patch({ layouts: $workspaceManager.get().layouts.filter(l => l.id !== id) })
}

export function addGroup(group: SessionGroup) {
  patch({ groups: [...$workspaceManager.get().groups, group] })
}

export function removeGroup(id: string) {
  patch({ groups: $workspaceManager.get().groups.filter(g => g.id !== id) })
}

export function addShortcut(sc: WorkspaceShortcut) {
  patch({ shortcuts: [...$workspaceManager.get().shortcuts, sc] })
}

export function removeShortcut(id: string) {
  patch({ shortcuts: $workspaceManager.get().shortcuts.filter(s => s.id !== id) })
}

export function updateShortcutLastOpened(id: string) {
  const shortcuts = $workspaceManager.get().shortcuts.map(s =>
    s.id === id ? { ...s, lastOpened: Date.now() } : s
  )

  patch({ shortcuts })
}
