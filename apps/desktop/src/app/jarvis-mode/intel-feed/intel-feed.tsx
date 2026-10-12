import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useState } from 'react'

import {
  $jarvisAgents,
  $jarvisAutomationJobs,
  $jarvisNotifications,
  $jarvisOrbState,
  $jarvisSystemStatus,
  $jarvisUnreadCount,
  clearNotifications,
  type JarvisAgent,
  type JarvisAutomationJob,
  type JarvisNotification,
  markNotificationRead
} from '@/store/jarvis-mode'


type IntelTab = 'agents' | 'jobs' | 'notifications' | 'system'

const TABS: { id: IntelTab; label: string; icon: string }[] = [
  { id: 'agents', label: 'Agents', icon: 'hubot' },
  { id: 'jobs', label: 'Jobs', icon: 'run-all' },
  { id: 'notifications', label: 'Alerts', icon: 'bell' },
  { id: 'system', label: 'System', icon: 'dashboard' },
]

function AgentCardSmall({ agent }: { agent: JarvisAgent }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
      <div className={`size-2 rounded-full ${agent.status === 'running' ? 'bg-emerald-400 animate-pulse' : agent.status === 'error' ? 'bg-red-400' : 'bg-white/20'}`}
        style={agent.status === 'running' ? { boxShadow: '0 0 6px rgba(52, 211, 153, 0.5)' } : undefined} />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium text-white/60 truncate">{agent.name}</div>
        {agent.currentTask && <div className="text-[9px] text-white/20 truncate">{agent.currentTask}</div>}
      </div>
      {(agent.progress ?? 0) > 0 && (
        <div className="w-12 h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-[#0066ff] to-[#00d4ff]" style={{ width: `${agent.progress}%` }} />
        </div>
      )}
    </div>
  )
}

function JobCardSmall({ job }: { job: JarvisAutomationJob }) {
  const statusColor = {
    running: '#22c55e', queued: '#f59e0b', completed: '#3b82f6', failed: '#ef4444', paused: '#64748b'
  }[job.status]

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
      <div className="size-2 rounded-full" style={{ backgroundColor: statusColor }} />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium text-white/60 truncate">{job.name}</div>
        {job.eta && <div className="text-[9px] text-white/20">ETA: {Math.round(job.eta / 1000)}s</div>}
      </div>
    </div>
  )
}

function NotificationCardSmall({ notif }: { notif: JarvisNotification }) {
  const typeIcon = { info: 'info', success: 'pass', warning: 'warning', error: 'error' }[notif.type]
  const typeColor = { info: '#00d4ff', success: '#22c55e', warning: '#f59e0b', error: '#ef4444' }[notif.type]

  return (
    <div
      className={`flex items-start gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all
        ${notif.read ? 'bg-white/[0.01] opacity-60' : 'bg-white/[0.03] border border-white/[0.06]'}`}
      onClick={() => markNotificationRead(notif.id)}
    >
      <span className={`codicon codicon-${typeIcon} text-sm mt-0.5`} style={{ color: typeColor }} />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium text-white/70 truncate">{notif.title}</div>
        <div className="text-[9px] text-white/30 line-clamp-1">{notif.message}</div>
      </div>
      <span className="text-[8px] text-white/15 mt-0.5">
        {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  )
}

function SystemFeed() {
  const status = useStore($jarvisSystemStatus)
  const orbState = useStore($jarvisOrbState)

  const checks = [
    { label: 'Gateway', value: status.gateway, ok: status.gateway === 'connected' },
    { label: 'Backend', value: status.backend, ok: status.backend === 'running' },
    { label: 'Orb State', value: orbState, ok: orbState !== 'error' },
    { label: 'CPU', value: `${Math.round(status.cpu)}%`, ok: status.cpu < 80 },
    { label: 'RAM', value: `${Math.round(status.memory.percent)}%`, ok: status.memory.percent < 80 },
    { label: 'Uptime', value: `${Math.floor(status.uptime / 60)}m ${Math.floor(status.uptime % 60)}s`, ok: true },
  ]

  return (
    <div className="space-y-1 px-3">
      {checks.map(check => (
        <div className="flex items-center gap-2 py-1.5" key={check.label}>
          <div className={`size-1.5 rounded-full ${check.ok ? 'bg-emerald-400' : 'bg-red-400'}`}
            style={check.ok ? { boxShadow: '0 0 4px rgba(52, 211, 153, 0.5)' } : undefined} />
          <span className="text-[10px] text-white/30 flex-1">{check.label}</span>
          <span className={`text-[10px] font-medium ${check.ok ? 'text-white/50' : 'text-red-400'}`}>{check.value}</span>
        </div>
      ))}
    </div>
  )
}

export function IntelFeedComponent() {
  const [activeTab, setActiveTab] = useState<IntelTab>('agents')
  const agents = useStore($jarvisAgents)
  const jobs = useStore($jarvisAutomationJobs)
  const notifications = useStore($jarvisNotifications)
  const unreadCount = useStore($jarvisUnreadCount)

  return (
    <div className="h-full flex flex-col w-[280px] relative">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-2xl border-l border-white/[0.04]" />
      <div className="absolute inset-0 bg-gradient-to-l from-[#0066ff]/[0.02] to-transparent pointer-events-none" />
      {/* Tab bar */}
      <div className="flex border-b border-white/[0.04]">
        {TABS.map(tab => (
          <button
            className={`flex-1 flex items-center justify-center gap-1.5 py-3 text-[10px] font-medium transition-all relative
              ${activeTab === tab.id ? 'text-white/70' : 'text-white/20 hover:text-white/40'}`}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className={`codicon codicon-${tab.icon} text-sm`} />
            <span className="hidden sm:inline">{tab.label}</span>
            {tab.id === 'notifications' && unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 size-3.5 rounded-full bg-red-500 text-white text-[7px] font-bold flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
            {activeTab === tab.id && (
              <motion.div
                className="absolute bottom-0 left-2 right-2 h-0.5 rounded-full bg-gradient-to-r from-[#0066ff] to-[#00d4ff]"
                layoutId="intel-tab-indicator"
              />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="relative flex-1 overflow-y-auto py-2 scrollbar-dt">
        <AnimatePresence mode="wait">
          {activeTab === 'agents' && (
            <motion.div animate={{ opacity: 1 }} className="space-y-1 px-2" exit={{ opacity: 0 }} initial={{ opacity: 0 }} key="agents">
              {agents.length === 0 ? (
                <div className="flex flex-col items-center py-8 text-center">
                  <span className="codicon codicon-hubot text-2xl text-white/[0.06] mb-2" />
                  <span className="text-[11px] text-white/15">No active agents</span>
                  <span className="text-[9px] text-white/10 mt-1">Spawn agents from Mission Nav</span>
                </div>
              ) : (
                agents.map(a => <AgentCardSmall agent={a} key={a.id} />)
              )}
            </motion.div>
          )}

          {activeTab === 'jobs' && (
            <motion.div animate={{ opacity: 1 }} className="space-y-1 px-2" exit={{ opacity: 0 }} initial={{ opacity: 0 }} key="jobs">
              {jobs.length === 0 ? (
                <div className="flex flex-col items-center py-8 text-center">
                  <span className="codicon codicon-run-all text-2xl text-white/[0.06] mb-2" />
                  <span className="text-[11px] text-white/15">No running jobs</span>
                </div>
              ) : (
                jobs.map(j => <JobCardSmall job={j} key={j.id} />)
              )}
            </motion.div>
          )}

          {activeTab === 'notifications' && (
            <motion.div animate={{ opacity: 1 }} exit={{ opacity: 0 }} initial={{ opacity: 0 }} key="notifications">
              <div className="flex items-center justify-between px-4 py-1">
                <span className="text-[9px] text-white/15">{notifications.length} notifications</span>
                {notifications.length > 0 && (
                  <button className="text-[9px] text-white/20 hover:text-white/40 transition-colors" onClick={clearNotifications}>Clear all</button>
                )}
              </div>
              <div className="space-y-0.5 px-2">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center py-8 text-center">
                    <span className="codicon codicon-bell text-2xl text-white/[0.06] mb-2" />
                    <span className="text-[11px] text-white/15">No notifications</span>
                  </div>
                ) : (
                  notifications.map(n => <NotificationCardSmall key={n.id} notif={n} />)
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'system' && (
            <motion.div animate={{ opacity: 1 }} exit={{ opacity: 0 }} initial={{ opacity: 0 }} key="system">
              <div className="px-4 py-2 text-[9px] uppercase tracking-[0.15em] text-white/15 font-medium">Live Checks</div>
              <SystemFeed />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export const IntelFeed = memo(IntelFeedComponent)
