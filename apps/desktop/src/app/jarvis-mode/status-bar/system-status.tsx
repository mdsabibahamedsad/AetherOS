import { useStore } from '@nanostores/react'
import { motion } from 'motion/react'
import { memo } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { getSystemHealth } from '@/lib/jarvis/monitoring/health-monitor'
import { $jarvisAgents, $jarvisAutomationJobs, $jarvisSystemStatus } from '@/store/jarvis-mode'

function SystemStatusComponent() {
  const status = useStore($jarvisSystemStatus)
  const agents = useStore($jarvisAgents)
  const jobs = useStore($jarvisAutomationJobs)

  const health = getSystemHealth()
  const runningAgents = agents.filter(a => a.status === 'running').length
  const runningJobs = jobs.filter(j => j.status === 'running').length
  const failedJobs = jobs.filter(j => j.status === 'failed').length

  const overallHealth = status.backend === 'running' ? 'healthy' : status.backend === 'starting' ? 'degraded' : 'critical'
  const healthColor = overallHealth === 'healthy' ? '#22c55e' : overallHealth === 'degraded' ? '#f59e0b' : '#ef4444'

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <motion.div
            animate={overallHealth === 'healthy' ? undefined : { scale: [1, 1.3, 1] }}
            className="size-2 rounded-full"
            style={{ backgroundColor: healthColor, boxShadow: `0 0 8px ${healthColor}` }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <span className="text-[13px] font-medium capitalize text-white/70">{overallHealth}</span>
        </div>
        <span className="text-[10px] text-white/20 font-mono">{health.recoveryAttempts > 0 ? `${health.recoveryAttempts} recoveries` : ''}</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <StatusTile color={status.cpu > 80 ? '#ef4444' : status.cpu > 50 ? '#f59e0b' : '#22c55e'} icon="dashboard" label="CPU" value={`${Math.round(status.cpu)}%`} />
        <StatusTile color={status.memory.percent > 80 ? '#ef4444' : status.memory.percent > 50 ? '#f59e0b' : '#22c55e'} icon="database" label="RAM" value={`${Math.round(status.memory.percent)}%`} />
        <StatusTile color={runningAgents > 0 ? '#00d4ff' : '#64748b'} icon="hubot" label="Agents" value={`${runningAgents}/${agents.length}`} />
        <StatusTile color={runningJobs > 0 ? '#f59e0b' : failedJobs > 0 ? '#ef4444' : '#64748b'} icon="run-all" label="Jobs" value={`${runningJobs} running`} />
      </div>

      {status.gpu && (
        <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Codicon className="size-3.5 text-[#a78bfa]" name="gpu" />
            <span className="text-[11px] text-white/50">{status.gpu.name}</span>
          </div>
          <span className="text-[11px] font-mono text-white/60">{Math.round(status.gpu.percent)}%</span>
        </div>
      )}

      <div className="space-y-1">
        <HealthCheckRow label="Gateway" status={status.gateway === 'connected' ? 'healthy' : 'down'} />
        <HealthCheckRow label="Backend" status={status.backend === 'running' ? 'healthy' : status.backend === 'starting' ? 'degraded' : 'critical'} />
        <HealthCheckRow label="Agents" status={runningAgents > 0 || agents.length === 0 ? 'healthy' : 'degraded'} />
        <HealthCheckRow label="Memory" status="healthy" />
      </div>
    </div>
  )
}

function StatusTile({ label, value, icon, color }: { label: string; value: string; icon: string; color: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
      <Codicon className="size-3.5 shrink-0" name={icon} style={{ color }} />
      <div className="min-w-0">
        <div className="text-[10px] text-white/30 uppercase tracking-wider">{label}</div>
        <div className="text-[12px] font-medium text-white/70 font-mono">{value}</div>
      </div>
    </div>
  )
}

function HealthCheckRow({ label, status }: { label: string; status: 'healthy' | 'degraded' | 'critical' | 'down' }) {
  const color = status === 'healthy' ? '#22c55e' : status === 'degraded' ? '#f59e0b' : '#ef4444'

  return (
    <div className="flex items-center justify-between px-2 py-1">
      <span className="text-[11px] text-white/40">{label}</span>
      <div className="flex items-center gap-1.5">
        <motion.span animate={status === 'healthy' ? undefined : { scale: [1, 1.3, 1] }} className="size-1.5 rounded-full" style={{ backgroundColor: color }} transition={{ duration: 2, repeat: Infinity }} />
        <span className="text-[10px] capitalize" style={{ color }}>{status}</span>
      </div>
    </div>
  )
}

export const SystemStatus = memo(SystemStatusComponent)
