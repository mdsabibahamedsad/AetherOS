import { useStore } from '@nanostores/react'
import { memo, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import {
  $jarvisActiveAgentCount,
  $jarvisDisplayMode,
  $jarvisRunningJobCount,
  $jarvisSystemStatus,
  $jarvisThinkingStage,
  $jarvisUnreadCount,
  type JarvisDisplayMode,
  setJarvisDisplayMode,
  type ThinkingStage
} from '@/store/jarvis-mode'
import { $voiceState } from '@/store/jarvis-voice'

function StatusDot({ color }: { color: string }) {
  return (
    <span
      className="inline-block size-1.5 rounded-full"
      style={{
        backgroundColor: color,
        boxShadow: `0 0 6px ${color}`
      }}
    />
  )
}

const STAGE_LABELS: Record<ThinkingStage, string> = {
  idle: 'Idle',
  understanding: 'Understanding',
  planning: 'Planning',
  searching: 'Searching',
  'using-tools': 'Using Tools',
  executing: 'Executing',
  validating: 'Validating',
  complete: 'Complete'
}

function StatusBarIndicator({
  icon,
  label,
  value,
  color,
  glow
}: {
  icon: string
  label: string
  value: string | number
  color: string
  glow?: boolean
}) {
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
      <Codicon className="size-3.5" name={icon} style={{ color }} />
      <span className="text-[10px] text-white/40 uppercase tracking-wider">{label}</span>
      <span className="text-[11px] font-medium text-white/80" style={glow ? { color, textShadow: `0 0 8px ${color}40` } : undefined}>
        {value}
      </span>
    </div>
  )
}

function JarvisStatusBarComponent() {
  const status = useStore($jarvisSystemStatus)
  const agentCount = useStore($jarvisActiveAgentCount)
  const jobCount = useStore($jarvisRunningJobCount)
  const unreadCount = useStore($jarvisUnreadCount)
  const thinkingStage = useStore($jarvisThinkingStage)
  const voiceState = useStore($voiceState)
  const displayMode = useStore($jarvisDisplayMode)
  const navigate = useNavigate()
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000)

    return () => clearInterval(interval)
  }, [])

  const gatewayColor = status.gateway === 'connected' ? '#22c55e' : status.gateway === 'connecting' ? '#f59e0b' : '#ef4444'
  const backendColor = status.backend === 'running' ? '#22c55e' : status.backend === 'starting' ? '#f59e0b' : '#ef4444'
  const thinkingColor = thinkingStage === 'idle' ? '#64748b' : thinkingStage === 'complete' ? '#22c55e' : '#00d4ff'

  return (
    <div className="flex items-center justify-between px-4 py-1.5 border-b border-white/[0.06] bg-black/30 backdrop-blur-xl">
      {/* Left: AI Status */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.06]">
          <StatusDot color={thinkingColor} />
          <span className="text-[10px] text-white/40 uppercase tracking-wider">AI</span>
          <span className="text-[11px] font-medium text-white/80">{STAGE_LABELS[thinkingStage]}</span>
        </div>

        {status.model && (
          <StatusBarIndicator color="#00d4ff" icon="symbol-method" label="Model" value={status.model} />
        )}
      </div>

      {/* Center: System */}
      <div className="flex items-center gap-1.5">
        <StatusBarIndicator color={status.cpu > 80 ? '#ef4444' : '#22c55e'} icon="dashboard" label="CPU" value={`${Math.round(status.cpu)}%`} />
        <StatusBarIndicator color={status.memory.percent > 80 ? '#ef4444' : '#22c55e'} icon="database" label="RAM" value={`${Math.round(status.memory.percent)}%`} />

        {status.gpu && (
          <StatusBarIndicator color="#a78bfa" icon="gpu" label="GPU" value={`${Math.round(status.gpu.percent)}%`} />
        )}

        <div className="w-px h-3 bg-white/10 mx-1" />

        <StatusBarIndicator color={gatewayColor} glow={status.gateway === 'connected'} icon="server" label="Gateway" value={status.gateway} />
        <StatusBarIndicator color={backendColor} glow={status.backend === 'running'} icon="server-process" label="Backend" value={status.backend} />
      </div>

      {/* Right: Tasks, Notifications, Time */}
      <div className="flex items-center gap-1.5">
        {voiceState === 'LISTENING' && (
          <StatusBarIndicator color="#34d399" glow icon="microphone" label="Mic" value="live" />
        )}
        {voiceState === 'SPEAKING' && (
          <StatusBarIndicator color="#00d4ff" glow icon="unmute" label="Voice" value="speaking" />
        )}
        {agentCount > 0 && (
          <StatusBarIndicator color="#00d4ff" glow icon="robot" label="Agents" value={agentCount} />
        )}
        {jobCount > 0 && (
          <StatusBarIndicator color="#f59e0b" glow icon="run-all" label="Jobs" value={jobCount} />
        )}
        {unreadCount > 0 && (
          <StatusBarIndicator color="#ef4444" glow icon="bell" label="" value={unreadCount} />
        )}

        <div className="w-px h-3 bg-white/10 mx-1" />

        {/* Overlay density: compact / expanded / fullscreen */}
        <div aria-label="Jarvis display mode" className="flex items-center rounded-md bg-white/[0.03] border border-white/[0.06] overflow-hidden" role="group">
          {(Object.keys({ compact: 1, expanded: 1, fullscreen: 1 }) as JarvisDisplayMode[]).map(mode => (
            <button
              className={`px-2 py-1 text-[10px] uppercase tracking-wider transition-all ${displayMode === mode ? 'text-[#00d4ff] bg-[#00d4ff]/10' : 'text-white/30 hover:text-white/60'}`}
              key={mode}
              onClick={() => setJarvisDisplayMode(mode)}
              title={`Jarvis ${mode} mode`}
            >
              {mode === 'compact' ? 'Mini' : mode === 'expanded' ? 'Float' : 'Full'}
            </button>
          ))}
        </div>

        <span className="text-[11px] font-mono text-white/30">
          {time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>

        <div className="w-px h-3 bg-white/10 mx-1" />

        {/* Exit Jarvis: returns Home. Gateway, sessions and
            background tasks keep running — nothing is torn down. */}
        <button
          aria-label="Exit Jarvis mode and return Home"
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.06] text-[10px] text-white/40 uppercase tracking-wider hover:text-white/80 hover:bg-white/[0.08] transition-all"
          onClick={() => navigate('/home')}
          title="Exit Jarvis mode and return Home (running tasks continue in the background)"
        >
          <Codicon className="size-3.5" name="sign-out" />
          Exit Jarvis
        </button>
      </div>
    </div>
  )
}

export const JarvisStatusBar = memo(JarvisStatusBarComponent)
