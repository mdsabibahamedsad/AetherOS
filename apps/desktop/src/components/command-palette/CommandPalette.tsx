import { useStore } from '@nanostores/react'
import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Kbd } from '@/components/ui/kbd'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { NAV_SECTIONS } from '@/store/navigation'
import { $commandPaletteOpen, closeCommandPalette, openCommandPalette } from '@/store/command-palette'
import { $sessions } from '@/store/session'
import { $activeProfile } from '@/store/profile'

interface CommandItem {
  id: string
  label: string
  description: string
  icon: string
  category: string
  action: () => void
  keywords: string[]
  shortcut?: string
  recent?: boolean
}

const RECENT_COMMANDS_KEY = 'aetheros.command-palette.recent'
const MAX_RECENT = 5

function getRecentCommands(): string[] {
  try {
    const stored = localStorage.getItem(RECENT_COMMANDS_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function addRecentCommand(commandId: string): void {
  try {
    const recent = getRecentCommands()
    const filtered = recent.filter(id => id !== commandId)
    filtered.unshift(commandId)
    localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(filtered.slice(0, MAX_RECENT)))
  } catch {
    // ignore
  }
}

export function CommandPalette() {
  const isOpen = useStore($commandPaletteOpen)
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const sessions = useStore($sessions)
  const profile = useStore($activeProfile)
  const [recentCommandIds, setRecentCommandIds] = useState<string[]>([])

  // Load recent commands on mount
  useEffect(() => {
    setRecentCommandIds(getRecentCommands())
  }, [])

  const commands = useMemo<CommandItem[]>(() => {
    const items: CommandItem[] = []

    // Navigation commands from sidebar
    NAV_SECTIONS.forEach(section => {
      const shortcut = getNavigationShortcut(section.id)
      items.push({
        id: `nav-${section.id}`,
        label: section.label,
        description: `Open ${section.label}`,
        icon: section.icon,
        category: 'Navigation',
        action: () => {
          navigate(section.route)
          closeCommandPalette()
          addRecentCommand(`nav-${section.id}`)
        },
        keywords: [section.label.toLowerCase(), section.route.slice(1), section.group],
        shortcut,
      })
    })

    // Quick actions
    const quickActions = [
      { id: 'new-chat', label: 'New Chat', description: 'Start a new conversation', icon: 'add', category: 'Actions', route: '/', keywords: ['new', 'chat', 'start', 'conversation'], shortcut: '⌘N' },
      { id: 'jarvis', label: 'Jarvis Mode', description: 'Command AetherOS with natural language', icon: 'hubot', category: 'Actions', route: '/jarvis', keywords: ['jarvis', 'voice', 'command', 'assistant'], shortcut: '⌘J' },
      { id: 'command-palette', label: 'Command Palette', description: 'Search everything', icon: 'search', category: 'Actions', route: '#', keywords: ['search', 'find', 'command', 'palette'], shortcut: '⌘K' },
    ]

    quickActions.forEach(action => {
      items.push({
        id: action.id,
        label: action.label,
        description: action.description,
        icon: action.icon,
        category: action.category,
        action: () => {
          if (action.route !== '#') {
            navigate(action.route)
          }
          closeCommandPalette()
          addRecentCommand(action.id)
        },
        keywords: action.keywords,
        shortcut: action.shortcut,
      })
    })

    // Recent sessions
    sessions.slice(0, 10).forEach(session => {
      items.push({
        id: `session-${session.id}`,
        label: sessionTitle(session),
        description: `Session ${session.id.slice(0, 8)}`,
        icon: 'history',
        category: 'Sessions',
        action: () => {
          navigate(`/session/${session.id}`)
          closeCommandPalette()
          addRecentCommand(`session-${session.id}`)
        },
        keywords: ['session', 'chat', 'history', 'recent', session.id.slice(0, 8)],
      })
    })

    // Settings categories
    const settingsCategories = [
      { id: 'settings-general', label: 'General Settings', description: 'Appearance, behavior, startup', icon: 'gear', category: 'Settings', route: '/settings', keywords: ['settings', 'preferences', 'general', 'appearance'] },
      { id: 'settings-models', label: 'Models', description: 'Configure AI models and providers', icon: 'symbol-method', category: 'Settings', route: '/models', keywords: ['models', 'providers', 'ai', 'llm'] },
      { id: 'settings-keys', label: 'API Keys', description: 'Manage credentials and tokens', icon: 'key', category: 'Settings', route: '/settings/keys', keywords: ['keys', 'api', 'tokens', 'credentials', 'secrets'] },
      { id: 'settings-security', label: 'Security', description: 'Permissions, sandbox, approvals', icon: 'shield', category: 'Settings', route: '/security', keywords: ['security', 'permissions', 'approvals', 'sandbox'] },
    ]

    settingsCategories.forEach(setting => {
      items.push({
        id: setting.id,
        label: setting.label,
        description: setting.description,
        icon: setting.icon,
        category: setting.category,
        action: () => {
          navigate(setting.route)
          closeCommandPalette()
          addRecentCommand(setting.id)
        },
        keywords: setting.keywords,
      })
    })

    // Tools & Utilities
    const tools = [
      { id: 'files', label: 'File Explorer', description: 'Browse and manage files', icon: 'file-directory', category: 'Tools', route: '/files', keywords: ['files', 'explorer', 'browse', 'find'] },
      { id: 'computer', label: 'Computer Use', description: 'Run commands and control the system', icon: 'terminal', category: 'Tools', route: '/computer', keywords: ['terminal', 'shell', 'command', 'bash', 'cli', 'computer'] },
      { id: 'browser', label: 'Web Browser', description: 'Browse the web', icon: 'globe', category: 'Tools', route: '/browser', keywords: ['browser', 'web', 'search', 'internet'] },
      { id: 'memory', label: 'Memory', description: 'View and manage memories', icon: 'database', category: 'Tools', route: '/memory', keywords: ['memory', 'recall', 'remember', 'store'] },
      { id: 'tasks', label: 'Tasks', description: 'Manage background tasks', icon: 'checklist', category: 'Tools', route: '/tasks', keywords: ['tasks', 'jobs', 'background', 'automation'] },
      { id: 'orchestrator', label: 'Task Orchestrator', description: 'Multi-agent workflows', icon: 'graph', category: 'Tools', route: '/task-orchestrator', keywords: ['orchestrator', 'workflow', 'multi-agent', 'plan'] },
      { id: 'diagnostics', label: 'Diagnostics', description: 'System health and logs', icon: 'check', category: 'Tools', route: '/diagnostics', keywords: ['diagnostics', 'health', 'logs', 'debug', 'troubleshoot'] },
    ]

    tools.forEach(tool => {
      items.push({
        id: tool.id,
        label: tool.label,
        description: tool.description,
        icon: tool.icon,
        category: tool.category,
        action: () => {
          navigate(tool.route)
          closeCommandPalette()
          addRecentCommand(tool.id)
        },
        keywords: tool.keywords,
      })
    })

    return items
  }, [navigate, sessions])

  const filteredCommands = useMemo(() => {
    if (!query.trim()) {
      // Show recent commands at top when no query
      if (recentCommandIds.length > 0) {
        const recentItems = recentCommandIds
          .map(id => commands.find(c => c.id === id))
          .filter(Boolean) as CommandItem[]
        const otherItems = commands.filter(c => !recentCommandIds.includes(c.id))
        return [...recentItems.map(c => ({ ...c, recent: true })), ...otherItems]
      }
      return commands
    }

    const terms = query.toLowerCase().split(/\s+/).filter(Boolean)

    return commands
      .map(cmd => {
        const searchText = `${cmd.label} ${cmd.description} ${cmd.category} ${cmd.keywords.join(' ')}`.toLowerCase()
        const matches = terms.every(term => searchText.includes(term))
        return matches ? cmd : null
      })
      .filter(Boolean) as CommandItem[]
  }, [commands, query, recentCommandIds])

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus()
    }
  }, [isOpen])

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeCommandPalette()
        setQuery('')
        return
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1))
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, 0))
      }

      if (e.key === 'Enter') {
        e.preventDefault()
        const selected = filteredCommands[selectedIndex]
        if (selected) {
          selected.action()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, filteredCommands, selectedIndex])

  if (!isOpen) return null

  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {}
    const categoryOrder = ['Recent', 'Actions', 'Navigation', 'Sessions', 'Tools', 'Settings']
    
    filteredCommands.forEach(cmd => {
      const category = cmd.recent ? 'Recent' : cmd.category
      if (!groups[category]) {
        groups[category] = []
      }
      groups[category].push(cmd)
    })

    // Sort groups by categoryOrder
    const sortedGroups: Record<string, CommandItem[]> = {}
    categoryOrder.forEach(cat => {
      if (groups[cat] && groups[cat].length > 0) {
        sortedGroups[cat] = groups[cat]
      }
    })
    // Add any remaining categories not in order
    Object.keys(groups).forEach(cat => {
      if (!sortedGroups[cat]) {
        sortedGroups[cat] = groups[cat]
      }
    })

    return sortedGroups
  }, [filteredCommands])

  return (
    <div
      className="fixed inset-0 z-[800] flex items-start justify-center pt-16"
      onClick={closeCommandPalette}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl bg-(--ui-bg-secondary) border border-(--ui-stroke-tertiary) rounded-xl shadow-[0_4px_12px_rgb(0_0_0/0.32),0_16px_48px_rgb(0_0_0/0.28)] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-(--ui-stroke-tertiary) p-3">
          <Codicon name="search" size="1rem" className="text-(--ui-text-tertiary)" />
          <Input
            ref={inputRef}
            aria-label="Search commands"
            className="flex-1 bg-transparent border-none text-base placeholder:text-(--ui-text-tertiary) focus-visible:ring-0"
            onChange={e => setQuery(e.target.value)}
            placeholder="Type a command or search…"
            value={query}
          />
          <Kbd className="text-[0.625rem] text-(--ui-text-tertiary)">⎋</Kbd>
        </div>

        <ScrollArea className="max-h-[60vh]">
          {filteredCommands.length === 0 ? (
            <div className="p-8 text-center text-(--ui-text-tertiary)">
              <Codicon name="search" size="1.5rem" className="mx-auto mb-2 opacity-50" />
              <p>No commands found for "{query}"</p>
            </div>
          ) : (
            <div className="p-2">
              {Object.entries(groupedCommands).map(([category, cmds]) => (
                <div key={category} className="space-y-1">
                  <h3 className="px-2 py-1.5 text-[0.625rem] font-semibold uppercase tracking-widest text-(--ui-text-tertiary)">
                    {category}
                  </h3>
                  {cmds.map((cmd, index) => {
                    const globalIndex = filteredCommands.findIndex(c => c.id === cmd.id)
                    const isSelected = globalIndex === selectedIndex
                    return (
                      <button
                        key={cmd.id}
                        className={cn(
                          'flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)',
                          isSelected
                            ? 'bg-(--ui-control-hover-background) text-foreground'
                            : 'text-(--ui-text-secondary) hover:bg-(--ui-control-hover-background) hover:text-foreground'
                        )}
                        onClick={cmd.action}
                        onMouseEnter={() => setSelectedIndex(globalIndex)}
                        type="button"
                      >
                        <Codicon className={cn('shrink-0 size-5', isSelected && 'text-foreground')} name={cmd.icon as any} />
                        <div className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{cmd.label}</span>
                          <span className="block truncate text-xs text-(--ui-text-tertiary)">{cmd.description}</span>
                        </div>
                        {cmd.shortcut && (
                          <Kbd className="shrink-0 text-[0.625rem] text-(--ui-text-tertiary) opacity-70 px-1.5 py-0.5 rounded bg-(--ui-bg-tertiary)/50">
                            {cmd.shortcut}
                          </Kbd>
                        )}
                        {cmd.recent && (
                          <span className="shrink-0 text-[0.625rem] text-emerald-500 font-medium">Recent</span>
                        )}
                      </button>
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        <div className="border-t border-(--ui-stroke-tertiary) p-2 text-center">
          <span className="text-xs text-(--ui-text-tertiary)">
            <Kbd className="mr-1">↑</Kbd><Kbd className="mx-1">↓</Kbd> navigate · <Kbd className="mx-1">⏎</Kbd> select · <Kbd className="mx-1">⎋</Kbd> close
          </span>
        </div>
      </div>
    </div>
  )
}

function getNavigationShortcut(sectionId: string): string | undefined {
  const shortcuts: Record<string, string> = {
    'home': '⌘1',
    'chat': '⌘2',
    'jarvis-mode': '⌘J',
    'projects': '⌘3',
    'agents': '⌘4',
    'models': '',
    'memory': '',
    'knowledge': '',
    'files': '',
    'browser': '',
    'automation': '',
    'tasks': '',
    'task-orchestrator': '',
    'extensions': '',
    'mcp': '',
    'security': '',
    'services': '',
    'diagnostics': '',
  }
  return shortcuts[sectionId] || undefined
}

function sessionTitle(session: { id: string; title: string | null; last_active: number }): string {
  if (session.title) return session.title
  const date = session.last_active ? new Date(session.last_active).toLocaleDateString() : 'Unknown date'
  return `Session ${date}`
}

export { openCommandPalette, closeCommandPalette }