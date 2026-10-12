import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback } from 'react'

import { Codicon } from '@/components/ui/codicon'
import {
  $jarvisActivePanel,
  $jarvisAgents,
  $jarvisAutomationJobs,
  $jarvisNotifications,
  $jarvisRightPanelSection,
  $jarvisUnreadCount,
  clearNotifications,
  type JarvisAgent,
  type JarvisAutomationJob,
  type JarvisNotification,
  markNotificationRead,
  setJarvisActivePanel,
  setJarvisRightSection
} from '@/store/jarvis-mode'

const SECTIONS = [
  { id: 'agents', label: 'Live Agents', icon: 'robot' },
  { id: 'automations', label: 'Automations', icon: 'run-all' },
  { id: 'notifications', label: 'Notifications', icon: 'bell' },
] as const

const STATUS_COLORS: Record<string, string> = {
  running: '#22c55e', idle: '#64748b', error: '#ef4444',
  completed: '#22c55e', queued: '#f59e0b', failed: '#ef4444', paused: '#f59e0b',
}

const TYPE_ICONS: Record<string, string> = {
  research: 'search', coding: 'code', browser: 'globe',
  planning: 'list-flat', memory: 'database', automation: 'run-all',
  custom: 'hubot', file: 'file-directory', communication: 'comment-discussion',
  data: 'graph', terminal: 'terminal', database: 'database',
  vision: 'eye', voice: 'mic',
}

function AgentCard({ agent }: { agent: JarvisAgent }) {
  const color = STATUS_COLORS[agent.status] ?? '#64748b'

  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors"
      exit={{ opacity: 0, height: 0 }}
      initial={{ opacity: 0, x: 10 }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div className="flex items-center justify-center size-6 rounded-md bg-white/[0.06]">
          <Codicon className="size-3.5 text-white/60" name={TYPE_ICONS[agent.type] ?? 'hubot'} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-medium text-white/80 truncate">{agent.name}</div>
          <div className="text-[10px] text-white/30 capitalize">{agent.type} Agent</div>
        </div>
        <div className="flex items-center gap-1.5">
          <motion.span
            animate={agent.status === 'running' ? { scale: [1, 1.3, 1] } : undefined}
            className="size-1.5 rounded-full"
            style={{ backgroundColor: color, boxShadow: agent.status === 'running' ? `0 0 6px ${color}` : undefined }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className="text-[10px] text-white/40 capitalize">{agent.status}</span>
        </div>
      </div>
      {agent.currentTask && (
        <div className="text-[11px] text-white/40 truncate mt-1">{agent.currentTask}</div>
      )}
      {agent.progress !== undefined && agent.status === 'running' && (
        <div className="mt-2 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            animate={{ width: `${agent.progress}%` }}
            className="h-full rounded-full bg-gradient-to-r from-[#0066ff] to-[#00d4ff]"
            initial={{ width: 0 }}
            transition={{ duration: 0.5 }}
          />
        </div>
      )}
    </motion.div>
  )
}

function JobCard({ job }: { job: JarvisAutomationJob }) {
  const color = STATUS_COLORS[job.status] ?? '#64748b'

  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors"
      exit={{ opacity: 0, height: 0 }}
      initial={{ opacity: 0, x: 10 }}
    >
      <div className="flex items-center gap-2 mb-1">
        <Codicon
          className="size-3.5 text-white/40"
          name={job.type === 'scheduled' ? 'calendar' : job.type === 'background' ? 'server-process' : 'zap'}
        />
        <div className="flex-1 min-w-0">
          <div className="text-[12px] font-medium text-white/80 truncate">{job.name}</div>
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full capitalize" style={{ backgroundColor: `${color}15`, color }}>
          {job.status}
        </span>
      </div>
      {job.progress !== undefined && job.status === 'running' && (
        <div className="mt-2 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            animate={{ width: `${job.progress}%` }}
            className="h-full rounded-full bg-gradient-to-r from-[#f59e0b] to-[#ef4444]"
            initial={{ width: 0 }}
            transition={{ duration: 0.5 }}
          />
        </div>
      )}
      {job.error && <div className="mt-1 text-[10px] text-red-400/60 truncate">{job.error}</div>}
      {job.eta && (
        <div className="mt-1 text-[10px] text-white/20">ETA: {new Date(job.eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      )}
    </motion.div>
  )
}

function NotificationCard({ notif }: { notif: JarvisNotification }) {
  const iconMap = { info: 'info', success: 'pass', warning: 'warning', error: 'error' } as const
  const colorMap = { info: '#00d4ff', success: '#22c55e', warning: '#f59e0b', error: '#ef4444' } as const

  return (
    <button
      className={`w-full text-left p-3 rounded-lg border transition-all ${
        notif.read
          ? 'bg-white/[0.02] border-white/[0.04] opacity-50'
          : 'bg-white/[0.04] border-white/[0.08] hover:bg-white/[0.06]'
      }`}
      onClick={() => markNotificationRead(notif.id)}
    >
      <div className="flex items-center gap-2 mb-1">
        <Codicon className="size-3.5 shrink-0" name={iconMap[notif.type]} style={{ color: colorMap[notif.type] }} />
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[12px] font-medium text-white/80 truncate">{notif.title}</span>
          {!notif.read && <span className="size-1.5 rounded-full bg-[#00d4ff] shrink-0" />}
        </div>
        <span className="ml-auto text-[10px] text-white/20 shrink-0">
          {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <div className="text-[11px] text-white/40 line-clamp-2">{notif.message}</div>
    </button>
  )
}

function RightPanelComponent() {
  const activeSection = useStore($jarvisRightPanelSection)
  const activePanel = useStore($jarvisActivePanel)
  const agents = useStore($jarvisAgents)
  const jobs = useStore($jarvisAutomationJobs)
  const notifications = useStore($jarvisNotifications)
  const unreadCount = useStore($jarvisUnreadCount)
  const isOpen = activePanel === 'right'

  const handleToggle = useCallback(() => {
    setJarvisActivePanel(isOpen ? null : 'right')
  }, [isOpen])

  const runningAgents = agents.filter(a => a.status === 'running').length

  const renderContent = () => {
    switch (activeSection) {
      case 'agents':
        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-white/25 uppercase tracking-wider">
                {runningAgents > 0 ? `${runningAgents} active` : 'No active agents'}
              </span>
              {agents.length > 0 && (
                <span className="text-[10px] text-white/20">{agents.length} total</span>
              )}
            </div>
            <AnimatePresence>
              {agents.length === 0 ? (
                <EmptyState icon="robot" label="No active agents" sublabel="Spawn agents from the Agents panel" />
              ) : (
                agents.map(a => <AgentCard agent={a} key={a.id} />)
              )}
            </AnimatePresence>
          </div>
        )
      case 'automations': {
        const runningJobs = jobs.filter(j => j.status === 'running').length

        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-white/25 uppercase tracking-wider">
                {runningJobs > 0 ? `${runningJobs} running` : 'No running jobs'}
              </span>
              {jobs.length > 0 && (
                <span className="text-[10px] text-white/20">{jobs.length} total</span>
              )}
            </div>
            <AnimatePresence>
              {jobs.length === 0 ? (
                <EmptyState icon="run-all" label="No running jobs" sublabel="Create automations from the Automation panel" />
              ) : (
                jobs.map(j => <JobCard job={j} key={j.id} />)
              )}
            </AnimatePresence>
          </div>
        )
      }

      case 'notifications':
        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-white/25 uppercase tracking-wider">
                {unreadCount > 0 ? `${unreadCount} unread` : 'All clear'}
              </span>
              {notifications.length > 0 && (
                <button className="text-[10px] text-white/20 hover:text-white/40 transition-colors" onClick={clearNotifications}>
                  Clear all
                </button>
              )}
            </div>
            <AnimatePresence>
              {notifications.length === 0 ? (
                <EmptyState icon="bell" label="No notifications" sublabel="Notifications appear here as tasks progress" />
              ) : (
                notifications.map(n => <NotificationCard key={n.id} notif={n} />)
              )}
            </AnimatePresence>
          </div>
        )
    }
  }

  return (
    <>
      <button
        aria-label="Toggle monitor panel"
        className="fixed right-3 top-1/2 -translate-y-1/2 z-50 flex items-center justify-center size-8 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white/40 hover:text-white/80 hover:bg-white/[0.1] transition-all"
        onClick={handleToggle}
        title="Toggle monitor"
      >
        <Codicon className="size-4" name={isOpen ? 'chrome-close' : 'panel-right'} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            animate={{ x: 0, opacity: 1 }}
            className="fixed right-0 top-0 bottom-0 w-[280px] z-40 flex flex-col border-l border-white/[0.06] bg-black/60 backdrop-blur-2xl"
            exit={{ x: 280, opacity: 0 }}
            initial={{ x: 280, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            <div className="flex border-b border-white/[0.06]">
              {SECTIONS.map(s => (
                <button
                  className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-[11px] font-medium transition-colors border-b-2 relative ${
                    activeSection === s.id
                      ? 'text-white/80 border-[#00d4ff]'
                      : 'text-white/30 border-transparent hover:text-white/50'
                  }`}
                  key={s.id}
                  onClick={() => setJarvisRightSection(s.id)}
                >
                  <Codicon className="size-3.5" name={s.icon} />
                  {s.label}
                  {(s.id === 'notifications' && unreadCount > 0) && (
                    <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-[#00d4ff]" />
                  )}
                  {(s.id === 'agents' && runningAgents > 0) && (
                    <span className="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-emerald-400" />
                  )}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-3 scrollbar-dt">
              {renderContent()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function EmptyState({ icon, label, sublabel }: { icon: string; label: string; sublabel?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Codicon className="size-8 text-white/[0.08] mb-3" name={icon} />
      <span className="text-[13px] text-white/25">{label}</span>
      {sublabel && <span className="text-[11px] text-white/15 mt-1 max-w-[180px]">{sublabel}</span>}
    </div>
  )
}

export const JarvisRightPanel = memo(RightPanelComponent)
