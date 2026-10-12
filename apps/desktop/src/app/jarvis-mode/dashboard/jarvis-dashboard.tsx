import { useStore } from '@nanostores/react'
import { motion } from 'motion/react'
import { memo, useEffect, useRef } from 'react'

import { getEngineState } from '@/lib/jarvis/core/engine'
import { getMemoryStats } from '@/lib/jarvis/core/memory'
import { getUnreadCount } from '@/lib/jarvis/core/notifications'
import { getSkillStats } from '@/lib/jarvis/core/skills'
import { getTaskStats } from '@/lib/jarvis/core/task-manager'
import {
  $jarvisActiveAgentCount,
  $jarvisAutonomyEnabled,
  $jarvisAutonomyLevel,
  $jarvisEngineActive,
  $jarvisEngineCycleCount,
  $jarvisEngineMemoryCount,
  $jarvisEngineNotificationCount,
  $jarvisEnginePhase,
  $jarvisEngineSkillsCount,
  $jarvisEngineTaskStats,
  $jarvisRunningJobCount,
  $jarvisSystemStatus,
  type EnginePhase,
  syncEngineState,
  updateEngineStats
} from '@/store/jarvis-mode'

import { GlassPanel } from '../shared/glass-panel'

const SPARKLINE_WIDTH = 200
const SPARKLINE_HEIGHT = 48

function CpuSparkline() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pointsRef = useRef<number[]>([])
  const status = useStore($jarvisSystemStatus)

  useEffect(() => {
    pointsRef.current.push(status.cpu)

    if (pointsRef.current.length > 60) {pointsRef.current = pointsRef.current.slice(-60)}
    const canvas = canvasRef.current

    if (!canvas) {return}
    const ctx = canvas.getContext('2d')

    if (!ctx) {return}
    const dpr = window.devicePixelRatio || 1
    canvas.width = SPARKLINE_WIDTH * dpr
    canvas.height = SPARKLINE_HEIGHT * dpr
    ctx.scale(dpr, dpr)
    ctx.clearRect(0, 0, SPARKLINE_WIDTH, SPARKLINE_HEIGHT)

    const pts = pointsRef.current

    if (pts.length < 2) {return}
    const step = SPARKLINE_WIDTH / 60

    ctx.beginPath()
    pts.forEach((p, i) => {
      const x = (i / 60) * SPARKLINE_WIDTH
      const y = SPARKLINE_HEIGHT - (p / 100) * SPARKLINE_HEIGHT * 0.8
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
    })
    ctx.strokeStyle = status.cpu > 80 ? '#ef4444' : '#22c55e'
    ctx.lineWidth = 1.5
    ctx.shadowColor = status.cpu > 80 ? '#ef4444' : '#22c55e'
    ctx.shadowBlur = 4
    ctx.stroke()
    ctx.shadowBlur = 0
  }, [status.cpu])

  return <canvas ref={canvasRef} style={{ width: SPARKLINE_WIDTH, height: SPARKLINE_HEIGHT }} />
}

const PHASE_LABELS: Record<EnginePhase, string> = {
  idle: 'Idle', observing: 'Observing', thinking: 'Thinking',
  planning: 'Planning', executing: 'Executing', learning: 'Learning', error: 'Error'
}

const PHASE_COLORS: Record<EnginePhase, string> = {
  idle: '#64748b', observing: '#00d4ff', thinking: '#a78bfa',
  planning: '#0066ff', executing: '#22c55e', learning: '#f59e0b', error: '#ef4444'
}

function StatTile({ label, value, color, icon, subtitle }: { label: string; value: string | number; color: string; icon: string; subtitle?: string }) {
  return (
    <GlassPanel className="p-3 rounded-xl" glow="none" intensity="light">
      <motion.div whileHover={{ scale: 1.02 }}>
        <div className="flex items-center gap-2 mb-2">
          <div className="size-2 rounded-full" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />
          <span className="text-[9px] uppercase tracking-[0.15em] text-white/20 font-medium">{label}</span>
        </div>
        <div className="text-xl font-bold text-white/80" style={{ color }}>{value}</div>
        {subtitle && <div className="text-[9px] text-white/15 mt-1">{subtitle}</div>}
      </motion.div>
    </GlassPanel>
  )
}

function PhaseIndicator({ phase }: { phase: EnginePhase }) {
  return (
    <div className="flex items-center gap-2">
      <motion.div
        animate={{
          scale: phase === 'idle' ? [1, 1, 1] : [1, 1.5, 1],
          opacity: phase === 'idle' ? [0.3, 0.3, 0.3] : [0.8, 0.4, 0.8]
        }}
        className="size-2.5 rounded-full"
        style={{ backgroundColor: PHASE_COLORS[phase], boxShadow: `0 0 8px ${PHASE_COLORS[phase]}` }}
        transition={{ duration: 1.5, repeat: Infinity }}
      />
      <span className="text-[13px] font-medium text-white/60">{PHASE_LABELS[phase]}</span>
    </div>
  )
}

function HealthRow({ label, ok, value }: { label: string; ok: boolean; value: string }) {
  return (
    <div className="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-white/[0.02]">
      <div className={`size-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`}
        style={ok ? { boxShadow: '0 0 4px rgba(52,211,153,0.5)' } : undefined} />
      <span className="text-[11px] text-white/30 flex-1">{label}</span>
      <span className={`text-[11px] font-medium ${ok ? 'text-white/50' : 'text-red-400'}`}>{value}</span>
    </div>
  )
}

export function JarvisDashboardComponent() {
  const phase = useStore($jarvisEnginePhase)
  const cycleCount = useStore($jarvisEngineCycleCount)
  const engineActive = useStore($jarvisEngineActive)
  const autonomyEnabled = useStore($jarvisAutonomyEnabled)
  const autonomyLevel = useStore($jarvisAutonomyLevel)
  const taskStats = useStore($jarvisEngineTaskStats)
  const notifCount = useStore($jarvisEngineNotificationCount)
  const skillsCount = useStore($jarvisEngineSkillsCount)
  const memCount = useStore($jarvisEngineMemoryCount)
  const status = useStore($jarvisSystemStatus)
  const agentCount = useStore($jarvisActiveAgentCount)
  const jobCount = useStore($jarvisRunningJobCount)

  useEffect(() => {
    const interval = setInterval(() => {
      try {
        const es = getEngineState()
        syncEngineState(es)
        const ts = getTaskStats()
        const nc = getUnreadCount()
        const ss = getSkillStats()
        const ms = getMemoryStats()
        updateEngineStats({
          tasks: ts,
          notifications: nc,
          skills: ss.enabled,
          memory: ms.total
        })
      } catch { /* ignore */ }
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="size-full overflow-y-auto p-6 scrollbar-dt">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-lg font-semibold text-white/70">Jarvis Engine</h1>
          <p className="text-[11px] text-white/20 mt-1">AI Operating System — Autonomous Core</p>
        </div>

        {/* Engine Status */}
        <GlassPanel className="p-4 rounded-2xl" glow="cyan" intensity="medium">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <PhaseIndicator phase={phase} />
            </div>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-white/20">Cycle #{cycleCount}</span>
              <span className={`px-2 py-0.5 rounded-full ${engineActive ? 'bg-emerald-500/15 text-emerald-400' : 'bg-white/[0.04] text-white/30'}`}>
                {engineActive ? 'Running' : 'Stopped'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {(['idle', 'observing', 'thinking', 'planning', 'executing', 'learning'] as EnginePhase[]).map((p, i) => (
              <div className="flex items-center gap-1" key={p}>
                <div className={`px-2 py-0.5 rounded text-[9px] font-medium transition-all
                  ${phase === p ? 'bg-white/[0.1] text-white/80 border border-white/[0.1]' :
                    ['idle', 'observing', 'thinking', 'planning', 'executing', 'learning'].indexOf(phase) > i ? 'opacity-50 text-white/40' : 'opacity-20 text-white/20'}`}>
                  {PHASE_LABELS[p]}
                </div>
                {i < 5 && <div className="w-2 h-px bg-white/[0.08]" />}
              </div>
            ))}
          </div>

          <div className="mt-3 flex items-center gap-4">
            <div>
              <div className="text-[9px] uppercase tracking-wider text-white/15 mb-1">CPU</div>
              <CpuSparkline />
            </div>
            <div className="text-[9px] text-white/20">
              {Math.round(status.cpu)}% · {Math.round(status.memory.percent)}% RAM
            </div>
          </div>
        </GlassPanel>

        {/* Stats Grid */}
        <div className="grid grid-cols-4 gap-3">
          <StatTile color="#00d4ff" icon="hubot" label="Agents" subtitle="Active agents" value={agentCount} />
          <StatTile color="#22c55e" icon="run-all" label="Tasks" subtitle={`${taskStats.queued} queued`} value={`${taskStats.running}/${taskStats.total}`} />
          <StatTile color="#f59e0b" icon="clock" label="Jobs" subtitle="Background jobs" value={jobCount} />
          <StatTile color="#a78bfa" icon="database" label="Memory" subtitle="Memory entries" value={memCount} />
          <StatTile color="#0066ff" icon="book" label="Skills" subtitle="Skills loaded" value={skillsCount} />
          <StatTile color="#f59e0b" icon="bell" label="Notifications" subtitle="Unread" value={notifCount} />
          <StatTile color={status.cpu > 80 ? '#ef4444' : '#22c55e'} icon="dashboard" label="CPU" subtitle={`${Math.round(status.memory.percent)}% RAM`} value={`${Math.round(status.cpu)}%`} />
          <StatTile color={autonomyEnabled ? '#22c55e' : '#64748b'} icon="hubot" label="Autonomy" subtitle={autonomyEnabled ? 'Proactive mode' : 'Manual mode'} value={autonomyEnabled ? autonomyLevel : 'Off'} />
        </div>

        {/* Task Status */}
        <GlassPanel className="p-4 rounded-2xl" glow="blue" intensity="medium">
          <div className="text-[9px] uppercase tracking-[0.15em] text-white/15 font-medium mb-3">Task Queue</div>
          <div className="flex gap-4">
            {(['total', 'running', 'queued', 'completed', 'failed', 'paused'] as const).map(key => (
              <div className="flex-1 text-center p-2 rounded-lg bg-white/[0.02]" key={key}>
                <div className={`text-lg font-bold ${
                  key === 'failed' ? 'text-red-400' :
                  key === 'completed' ? 'text-emerald-400' :
                  key === 'running' ? 'text-[#00d4ff]' :
                  key === 'queued' ? 'text-amber-400' :
                  'text-white/50'
                }`}>{taskStats[key]}</div>
                <div className="text-[8px] uppercase tracking-wider text-white/20 mt-1">{key}</div>
              </div>
            ))}
          </div>
        </GlassPanel>

        {/* System Health */}
        <GlassPanel className="p-4 rounded-2xl" glow="none" intensity="medium">
          <div className="text-[9px] uppercase tracking-[0.15em] text-white/15 font-medium mb-2">System Health</div>
          <HealthRow label="Engine" ok={engineActive} value={engineActive ? 'Running' : 'Stopped'} />
          <HealthRow label="Autonomy" ok={autonomyEnabled} value={autonomyEnabled ? `${autonomyLevel}` : 'Disabled'} />
          <HealthRow label="Gateway" ok={status.gateway === 'connected'} value={status.gateway} />
          <HealthRow label="Backend" ok={status.backend === 'running'} value={status.backend} />
          <HealthRow label="Current Model" ok={!!status.model} value={status.model || 'None'} />
          <HealthRow label="Provider" ok={!!status.provider} value={status.provider || 'None'} />
        </GlassPanel>
      </div>
    </div>
  )
}

export const JarvisDashboard = memo(JarvisDashboardComponent)
