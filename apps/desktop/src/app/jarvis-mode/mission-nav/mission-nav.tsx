import { useStore } from '@nanostores/react'
import { motion } from 'motion/react'
import { memo, useState } from 'react'

import { $jarvisOrbState } from '@/store/jarvis-mode'
import {
  $jarvisActiveAgentCount,
  $jarvisMissionView,
  $jarvisRunningJobCount,
  $jarvisUnreadCount,
  type MissionView,
  setJarvisActivePanel,
  setJarvisLeftSection,
  setJarvisMissionView
} from '@/store/jarvis-mode'


interface NavSection {
  name: string
  items: { id: MissionView; label: string; icon: string; badge?: 'agents' | 'jobs' | 'unread' }[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    name: 'Mission',
    items: [
      { id: 'orb', label: 'Dashboard', icon: 'dashboard' },
      { id: 'projects', label: 'Projects', icon: 'project' },
      { id: 'agents', label: 'Agents', icon: 'hubot', badge: 'agents' },
      { id: 'knowledge', label: 'Knowledge', icon: 'book' },
      { id: 'memory', label: 'Memory', icon: 'database' },
      { id: 'files', label: 'Files', icon: 'file-directory' },
      { id: 'automation', label: 'Automation', icon: 'run-all', badge: 'jobs' },
    ]
  },
  {
    name: 'Tools',
    items: [
      { id: 'browser', label: 'Browser', icon: 'globe' },
      { id: 'terminal', label: 'Terminal', icon: 'terminal' },
      { id: 'database', label: 'Database', icon: 'server' },
      { id: 'communication', label: 'Comm', icon: 'comment-discussion', badge: 'unread' },
    ]
  },
  {
    name: 'System',
    items: [
      { id: 'marketplace', label: 'Marketplace', icon: 'package' },
      { id: 'settings', label: 'Settings', icon: 'gear' },
    ]
  }
]

const SECTION_MAP: Partial<Record<MissionView, string>> = {
  projects: 'projects', agents: 'agents', knowledge: 'knowledge',
  memory: 'memory', files: 'files', automation: 'automation',
  browser: 'browser', terminal: 'terminal', database: 'memory',
  communication: 'communications', settings: 'settings'
}

function navigateTo(view: MissionView) {
  setJarvisMissionView(view)
  const section = SECTION_MAP[view]

  if (section) {
    setJarvisLeftSection(section)
    setJarvisActivePanel('left')
  }
}

function BadgePulse({ active }: { active: boolean }) {
  return active ? (
    <motion.span
      animate={{ scale: [1, 1.5, 1], opacity: [0.7, 0, 0.7] }}
      className="absolute -top-0.5 -right-0.5 size-2"
      transition={{ duration: 2, repeat: Infinity }}
    >
      <span className="block size-full rounded-full bg-emerald-400" />
    </motion.span>
  ) : null
}

function MissionNavItem({ item, active, collapsed }: { item: NavSection['items'][0]; active: boolean; collapsed: boolean }) {
  const agentCount = useStore($jarvisActiveAgentCount)
  const jobCount = useStore($jarvisRunningJobCount)
  const unreadCount = useStore($jarvisUnreadCount)

  const badgeValue = item.badge === 'agents' ? agentCount : item.badge === 'jobs' ? jobCount : item.badge === 'unread' ? unreadCount : 0
  const showBadge = badgeValue > 0

  return (
    <button
      aria-label={collapsed ? `Open ${item.label}` : item.label}
      className={`relative flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-left transition-all duration-200 group
        ${active ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]'}`}
      onClick={() => navigateTo(item.id)}
    >
      {active && (
        <motion.div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-gradient-to-b from-[#0066ff] to-[#00d4ff]"
          layoutId="nav-active-indicator"
          style={{ boxShadow: '0 0 8px rgba(0, 212, 255, 0.4)' }}
        />
      )}
      <div className={`flex items-center justify-center size-7 rounded-lg transition-all duration-200
        ${active ? 'bg-[#00d4ff]/10 text-[#00d4ff]' : 'text-white/30 group-hover:text-white/50 group-hover:bg-white/[0.04]'}`}>
        <span className={`codicon codicon-${item.icon} ${collapsed ? 'text-lg' : 'text-base'}`} />
      </div>
      {!collapsed && (
        <>
          <span className={`flex-1 text-[12px] font-medium transition-colors duration-200
            ${active ? 'text-white/80' : 'text-white/40 group-hover:text-white/60'}`}>
            {item.label}
          </span>
          {showBadge && (
            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full
              ${item.badge === 'unread' ? 'bg-red-500/20 text-red-400' : 'bg-[#00d4ff]/15 text-[#00d4ff]'}`}>
              {badgeValue > 99 ? '99+' : badgeValue}
            </span>
          )}
        </>
      )}
    </button>
  )
}

export function MissionNavComponent() {
  const [collapsed, setCollapsed] = useState(false)
  const activeView = useStore($jarvisMissionView)
  const orbState = useStore($jarvisOrbState)

  return (
    <motion.nav
      animate={{ width: collapsed ? 64 : 228 }}
      className="relative h-full flex flex-col overflow-hidden"
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-2xl border-r border-white/[0.04]" />
      <div className="absolute inset-0 bg-gradient-to-b from-[#0066ff]/[0.02] to-transparent pointer-events-none" />

      {/* Header */}
      <div className="relative flex items-center justify-between px-4 py-4 border-b border-white/[0.04]">
        {!collapsed && (
          <motion.div
            animate={{ opacity: 1 }}
            className="flex items-center gap-2"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
          >
            <button
              className="relative size-7 rounded-lg bg-gradient-to-br from-[#0066ff] to-[#00d4ff] flex items-center justify-center hover:shadow-[0_0_12px_rgba(0,102,255,0.4)] transition-shadow"
              onClick={() => navigateTo('orb')}
            >
              <span className="text-white text-[10px] font-bold">A</span>
              <BadgePulse active={orbState !== 'idle' && orbState !== 'error'} />
            </button>
            <span className="text-[12px] font-semibold text-white/60 tracking-wide">AetherOS</span>
          </motion.div>
        )}
        <button
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          className="flex items-center justify-center size-7 rounded-lg hover:bg-white/[0.06] text-white/30 hover:text-white/60 transition-all"
          onClick={() => setCollapsed(!collapsed)}
        >
          <span className={`codicon codicon-${collapsed ? 'panel-right' : 'chrome-close'} text-sm`} />
        </button>
      </div>

      {/* Navigation sections */}
      <div className="relative flex-1 overflow-y-auto px-2 py-3 space-y-4 scrollbar-dt">
        {NAV_SECTIONS.map(section => (
          <div key={section.name}>
            {!collapsed && (
              <div className="px-3 py-1 text-[9px] uppercase tracking-[0.2em] text-white/15 font-medium">
                {section.name}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map(item => (
                <MissionNavItem
                  active={activeView === item.id}
                  collapsed={collapsed}
                  item={item}
                  key={item.id}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom branding */}
      {!collapsed && (
        <div className="relative px-4 py-3 border-t border-white/[0.04]">
          <div className="text-[9px] text-white/10 text-center">
            Mission Control v3.0
          </div>
        </div>
      )}
    </motion.nav>
  )
}

export const MissionNav = memo(MissionNavComponent)
