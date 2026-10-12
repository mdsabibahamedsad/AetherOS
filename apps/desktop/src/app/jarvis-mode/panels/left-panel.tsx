import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback } from 'react'

import { Codicon } from '@/components/ui/codicon'
import {
  $jarvisActivePanel,
  $jarvisLeftPanelSection,
  setJarvisActivePanel,
  setJarvisLeftSection
} from '@/store/jarvis-mode'

const CHAT_SECTION = 'chat'

interface NavItem {
  id: string
  label: string
  icon: string
  section?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'projects', label: 'Projects', icon: 'project' },
  { id: 'memory', label: 'Memory', icon: 'database' },
  { id: 'knowledge', label: 'Knowledge', icon: 'book' },
  { id: 'files', label: 'Files', icon: 'file-directory' },
  { id: 'skills', label: 'Skills', icon: 'Extensions' },
  { id: 'mcp', label: 'MCP Servers', icon: 'server' },
  { id: 'automation', label: 'Automation', icon: 'run-all' },
  { id: 'communications', label: 'Communications', icon: 'comment-discussion' },
  { id: 'agents', label: 'Agents', icon: 'hubot' },
]

const BOTTOM_ITEMS: NavItem[] = [
  { id: 'terminal', label: 'Terminal', icon: 'terminal' },
  { id: 'browser', label: 'Browser', icon: 'globe' },
  { id: 'settings', label: 'Settings', icon: 'gear' },
]

function NavButton({ item, isActive, onClick }: { item: NavItem; isActive: boolean; onClick: () => void }) {
  return (
    <button
      className={`group relative flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-left transition-all duration-200 ${
        isActive
          ? 'bg-white/[0.08] text-white border border-white/[0.1]'
          : 'text-white/40 hover:text-white/70 hover:bg-white/[0.04] border border-transparent'
      }`}
      onClick={onClick}
    >
      {isActive && (
        <motion.div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-[#00d4ff]"
          layoutId="jarvis-nav-indicator"
          style={{ boxShadow: '0 0 8px #00d4ff60' }}
        />
      )}
      <Codicon className="size-4 shrink-0" name={item.icon} />
      <span className="text-[13px] font-medium truncate">{item.label}</span>
    </button>
  )
}

function LeftPanelComponent() {
  const activeSection = useStore($jarvisLeftPanelSection)
  const activePanel = useStore($jarvisActivePanel)
  const isOpen = activePanel === 'left'

  const handleToggle = useCallback(() => {
    setJarvisActivePanel(isOpen ? null : 'left')
  }, [isOpen])

  const handleNav = useCallback((id: string) => {
    setJarvisLeftSection(id)
  }, [])

  const handleBackToChat = useCallback(() => {
    setJarvisLeftSection(CHAT_SECTION)
  }, [])

  return (
    <>
      <button
        aria-label="Toggle navigation panel"
        className="fixed left-3 top-1/2 -translate-y-1/2 z-50 flex items-center justify-center size-8 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white/40 hover:text-white/80 hover:bg-white/[0.1] transition-all"
        onClick={handleToggle}
        title="Toggle navigation"
      >
        <Codicon className="size-4" name={isOpen ? 'chrome-close' : 'list-flat'} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            animate={{ x: 0, opacity: 1 }}
            className="fixed left-0 top-0 bottom-0 w-[240px] z-40 flex flex-col border-r border-white/[0.06] bg-black/60 backdrop-blur-2xl"
            exit={{ x: -260, opacity: 0 }}
            initial={{ x: -260, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            {/* Header - clickable to return to chat */}
            <button
              className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] hover:bg-white/[0.03] transition-colors w-full text-left group"
              onClick={handleBackToChat}
            >
              <div className="flex items-center justify-center size-7 rounded-lg bg-gradient-to-br from-[#0066ff] to-[#00d4ff] group-hover:shadow-lg group-hover:shadow-[#00d4ff]/20 transition-shadow">
                <Codicon className="size-4 text-white" name="hubot" />
              </div>
              <div>
                <div className="text-[13px] font-semibold text-white/90">AetherOS</div>
                <div className="text-[10px] text-white/30">Jarvis Mode</div>
              </div>
              {activeSection !== CHAT_SECTION && (
                <div className="ml-auto flex items-center gap-1 text-[10px] text-[#00d4ff]/60">
                  <Codicon className="size-3" name="arrow-left" />
                  Chat
                </div>
              )}
            </button>

            <nav className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5 scrollbar-dt">
              {NAV_ITEMS.map(item => (
                <NavButton
                  isActive={activeSection === item.id}
                  item={item}
                  key={item.id}
                  onClick={() => handleNav(item.id)}
                />
              ))}
            </nav>

            <div className="px-2 py-2 border-t border-white/[0.06] space-y-0.5">
              {BOTTOM_ITEMS.map(item => (
                <NavButton
                  isActive={activeSection === item.id}
                  item={item}
                  key={item.id}
                  onClick={() => handleNav(item.id)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export const JarvisLeftPanel = memo(LeftPanelComponent)
