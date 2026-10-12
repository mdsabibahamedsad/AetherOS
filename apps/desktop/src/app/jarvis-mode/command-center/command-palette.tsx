import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { AGENT_DEFINITIONS } from '@/lib/jarvis/orchestrator/agent-orchestrator'
import type { AgentType } from '@/lib/jarvis/types'
import {
  $jarvisCommandHistory,
  addJarvisNotification,
  setJarvisActivePanel,
  setJarvisLeftSection,
  setJarvisRightSection
} from '@/store/jarvis-mode'

import { GlassPanel } from '../shared/glass-panel'

interface CommandGroup {
  name: string
  commands: PaletteCommand[]
}

interface PaletteCommand {
  id: string
  label: string
  description: string
  icon: string
  keywords: string[]
  action: () => void
}

interface CommandPaletteProps {
  onCommand?: (command: string) => void
}

const BUILTIN_GROUPS: CommandGroup[] = [
  {
    name: 'Navigation',
    commands: [
      { id: 'nav-chat', label: 'Open Chat', description: 'Return to conversational workspace', icon: 'comment-discussion', keywords: ['chat', 'talk', 'converse'], action: () => setJarvisLeftSection('chat') },
      { id: 'nav-projects', label: 'Open Projects', description: 'View and manage projects', icon: 'project', keywords: ['project', 'workspace'], action: () => { setJarvisLeftSection('projects'); setJarvisActivePanel('left') } },
      { id: 'nav-memory', label: 'Open Memory', description: 'Browse memory graph', icon: 'database', keywords: ['memory', 'remember'], action: () => { setJarvisLeftSection('memory'); setJarvisActivePanel('left') } },
      { id: 'nav-agents', label: 'Open Agents', description: 'Spawn and monitor agents', icon: 'hubot', keywords: ['agent', 'spawn'], action: () => { setJarvisLeftSection('agents'); setJarvisActivePanel('left') } },
      { id: 'nav-automation', label: 'Open Automation', description: 'Manage background jobs', icon: 'run-all', keywords: ['automation', 'jobs', 'background'], action: () => { setJarvisLeftSection('automation'); setJarvisActivePanel('left') } },
      { id: 'nav-settings', label: 'Open Settings', description: 'Jarvis Mode configuration', icon: 'gear', keywords: ['settings', 'config', 'preferences'], action: () => { setJarvisLeftSection('settings'); setJarvisActivePanel('left') } },
      { id: 'nav-files', label: 'Open Files', description: 'Workspace file explorer', icon: 'file-directory', keywords: ['files', 'explorer', 'browse'], action: () => { setJarvisLeftSection('files'); setJarvisActivePanel('left') } },
      { id: 'nav-terminal', label: 'Open Terminal', description: 'Command line interface', icon: 'terminal', keywords: ['terminal', 'shell', 'command'], action: () => { setJarvisLeftSection('terminal'); setJarvisActivePanel('left') } },
      { id: 'nav-browser', label: 'Open Browser', description: 'Web browsing agent', icon: 'globe', keywords: ['browser', 'web', 'internet', 'url'], action: () => { setJarvisLeftSection('browser'); setJarvisActivePanel('left') } },
      { id: 'nav-communications', label: 'Open Communications', description: 'Unified inbox', icon: 'comment-discussion', keywords: ['communications', 'messages', 'inbox'], action: () => { setJarvisLeftSection('communications'); setJarvisActivePanel('left') } },
      { id: 'nav-mcp', label: 'Open MCP Servers', description: 'Manage MCP connections', icon: 'server', keywords: ['mcp', 'servers', 'connections'], action: () => { setJarvisLeftSection('mcp'); setJarvisActivePanel('left') } },
      { id: 'nav-knowledge', label: 'Open Knowledge', description: 'Documentation and reference', icon: 'book', keywords: ['knowledge', 'docs', 'documentation'], action: () => { setJarvisLeftSection('knowledge'); setJarvisActivePanel('left') } },
    ]
  },
  {
    name: 'Agents',
    commands: [
      { id: 'spawn-research', label: 'Spawn Research Agent', description: 'Web research and analysis', icon: 'search', keywords: ['research', 'spawn', 'agent'], action: () => spawnAgent('research') },
      { id: 'spawn-coding', label: 'Spawn Coding Agent', description: 'Write and review code', icon: 'code', keywords: ['coding', 'spawn', 'agent', 'code'], action: () => spawnAgent('coding') },
      { id: 'spawn-browser', label: 'Spawn Browser Agent', description: 'Navigate and extract web content', icon: 'globe', keywords: ['browser', 'spawn', 'agent'], action: () => spawnAgent('browser') },
      { id: 'spawn-planning', label: 'Spawn Planning Agent', description: 'Task decomposition and scheduling', icon: 'list-flat', keywords: ['planning', 'spawn', 'agent', 'plan'], action: () => spawnAgent('planning') },
      { id: 'spawn-automation', label: 'Spawn Automation Agent', description: 'Create and manage workflows', icon: 'run-all', keywords: ['automation', 'spawn', 'agent'], action: () => spawnAgent('automation') },
    ]
  },
  {
    name: 'System',
    commands: [
      { id: 'sys-status', label: 'Show System Status', description: 'View health and performance', icon: 'dashboard', keywords: ['status', 'health', 'performance', 'system'], action: () => { setJarvisRightSection('notifications'); setJarvisActivePanel('right') } },
      { id: 'sys-agents', label: 'Show Active Agents', description: 'Monitor running agents', icon: 'robot', keywords: ['agents', 'monitor', 'active'], action: () => { setJarvisRightSection('agents'); setJarvisActivePanel('right') } },
      { id: 'sys-automations', label: 'Show Running Jobs', description: 'View background tasks', icon: 'run-all', keywords: ['jobs', 'automations', 'background'], action: () => { setJarvisRightSection('automations'); setJarvisActivePanel('right') } },
      { id: 'sys-notifications', label: 'Show Notifications', description: 'View recent alerts', icon: 'bell', keywords: ['notifications', 'alerts', 'bell'], action: () => { setJarvisRightSection('notifications'); setJarvisActivePanel('right') } },
    ]
  },
]

function spawnAgent(type: AgentType) {
  const def = AGENT_DEFINITIONS[type]

  if (!def) {return}

  // Real delegation through the universal gateway (the palette's onCommand
  // sink, wired by the host view). Never a simulated agent.
  if (paletteCommandSink) {
    paletteCommandSink(`Delegate to a ${def.label}: report when it is running and stream its progress.`)
  } else {
    addJarvisNotification({ title: 'Commander offline', message: 'Type the delegation in the Jarvis composer instead.', type: 'warning' })
  }
}

/** Host view wires its command handler here so palette actions execute for real. */
let paletteCommandSink: ((command: string) => void) | null = null

export function setPaletteCommandSink(sink: ((command: string) => void) | null) {
  paletteCommandSink = sink
}

function CommandPaletteComponent({ onCommand }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(prev => !prev)
        setQuery('')
        setSelectedIdx(0)
      }

      if (e.key === 'Escape' && open) {
        setOpen(false)
        setQuery('')
      }
    }

    window.addEventListener('keydown', handler)

    return () => window.removeEventListener('keydown', handler)
  }, [open])

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const allCommands = useMemo(() => BUILTIN_GROUPS.flatMap(g => g.commands), [])

  const filtered = useMemo(() => {
    if (!query.trim()) {return BUILTIN_GROUPS}
    const q = query.toLowerCase()

    const matches = allCommands.filter(c =>
      c.label.toLowerCase().includes(q) ||
      c.description.toLowerCase().includes(q) ||
      c.keywords.some(k => k.includes(q))
    )

    return matches.length > 0 ? [{ name: 'Results', commands: matches }] : []
  }, [query, allCommands])

  const flatFiltered = useMemo(() => filtered.flatMap(g => g.commands), [filtered])

  useEffect(() => {
    setSelectedIdx(0)
  }, [query])

  useEffect(() => {
    if (listRef.current && flatFiltered[selectedIdx]) {
      const el = listRef.current.children[selectedIdx] as HTMLElement
      el?.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIdx, flatFiltered])

  const executeSelected = useCallback(() => {
    const cmd = flatFiltered[selectedIdx]

    if (!cmd) {return}
    cmd.action()
    addJarvisCommand(cmd.label)
    setOpen(false)
    setQuery('')
  }, [flatFiltered, selectedIdx])

  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(prev => Math.min(prev + 1, flatFiltered.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      executeSelected()
    } else if (e.key === 'Escape') {
      setOpen(false)
      setQuery('')
    }
  }, [flatFiltered, executeSelected])

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-[10000] flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          onMouseDown={e => e.target === e.currentTarget && setOpen(false)}
        >
          <GlassPanel
            className="w-full max-w-[560px] rounded-2xl overflow-hidden shadow-2xl"
            glow="none"
            intensity="heavy"
          >
            <motion.div
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            {/* Search input */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
              <Codicon className="size-4 text-white/20 shrink-0" name="search" />
              <input
                className="flex-1 bg-transparent text-[14px] text-white/80 placeholder:text-white/20 outline-none"
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Search commands..."
                ref={inputRef}
                value={query}
              />
              <div className="flex items-center gap-1 text-[10px] text-white/20">
                <span className="px-1.5 py-0.5 rounded bg-white/[0.06]">ESC</span>
                <span>close</span>
              </div>
            </div>

            {/* Results */}
            <div className="max-h-[360px] overflow-y-auto p-2 scrollbar-dt" ref={listRef}>
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center py-8 text-center">
                  <Codicon className="size-8 text-white/[0.06] mb-2" name="search" />
                  <span className="text-[13px] text-white/20">No results for "{query}"</span>
                </div>
              ) : (
                filtered.map(group => (
                  <div className="mb-2 last:mb-0" key={group.name}>
                    {!query && (
                      <div className="px-2 py-1.5 text-[10px] text-white/20 uppercase tracking-wider">{group.name}</div>
                    )}
                    {group.commands.map((cmd, i) => {
                      const globalIdx = flatFiltered.indexOf(cmd)

                      return (
                        <button
                          className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-left transition-all ${
                            globalIdx === selectedIdx
                              ? 'bg-white/[0.08] text-white'
                              : 'text-white/50 hover:bg-white/[0.04] hover:text-white/70'
                          }`}
                          key={cmd.id}
                          onClick={() => { cmd.action(); addJarvisCommand(cmd.label); setOpen(false); setQuery('') }}
                          onMouseEnter={() => setSelectedIdx(globalIdx)}
                        >
                          <Codicon className="size-4 text-white/30 shrink-0" name={cmd.icon} />
                          <div className="flex-1 min-w-0">
                            <div className="text-[13px] font-medium truncate">{cmd.label}</div>
                            <div className="text-[11px] text-white/25 truncate">{cmd.description}</div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </GlassPanel>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function addJarvisCommand(label: string) {
  const history = $jarvisCommandHistory.get()

  const next = [label, ...history.filter(c => c !== label)].slice(0, 50)

  ;($jarvisCommandHistory as any).set(next)
}

export const CommandPalette = memo(CommandPaletteComponent)
