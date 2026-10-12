import { useStore } from '@nanostores/react'
import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { cancelJarvisPipeline, GatewayUnavailableError } from '@/lib/jarvis/core/ai-core'
import { ApprovalRequiredError, submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { startJarvisGatewaySync } from '@/lib/jarvis/gateway-sync'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'
import { useJarvisVoice } from '@/lib/jarvis/voice/use-jarvis-voice'
import {
  $jarvisCommandLog,
  $jarvisDisplayMode,
  $jarvisExecution,
  $jarvisGatewayDetail,
  $jarvisLeftPanelSection,
  $jarvisMissionView,
  $jarvisSystemStatus,
  addJarvisNotification,
  isJarvisExecutingState,
  resetJarvisExecution,
  setJarvisMissionView,
  setJarvisOrbState,
  setJarvisThinkingStage,
  updateJarvisSystemStatus,
} from '@/store/jarvis-mode'
import { $activeSessionId, $gatewayState, $sessions, $workingSessionIds } from '@/store/session'

import { BackgroundSystem } from '../backgrounds/background-system'
import { CommandBar } from '../command-bar/command-bar'
import { CommandPalette, setPaletteCommandSink } from '../command-center/command-palette'
import { IntelFeed } from '../intel-feed/intel-feed'
import { MissionNav } from '../mission-nav/mission-nav'
import { NotificationCenter } from '../notifications/notification-center'
import { AiOrb } from '../orb/ai-orb'
import { AgentOrchestra } from '../orchestra/agent-orchestra'
import { SectionContent } from '../panels/section-content'
import { JarvisStatusBar } from '../status-bar/jarvis-status-bar'
import { ExecutionTimeline } from '../timeline/execution-timeline'

const QUICK_ACTIONS = [
  { id: 'agents', label: 'Run Agent', icon: 'hubot', hint: 'Create + run a live agent task' },
  { id: 'browser', label: 'Browse', icon: 'globe', hint: 'Open browser automation' },
  { id: 'files', label: 'Files', icon: 'file-directory', hint: 'Search + manage files' },
  { id: 'terminal', label: 'Terminal', icon: 'terminal', hint: 'Run a real shell command' },
  { id: 'knowledge', label: 'Knowledge', icon: 'book', hint: 'Search indexed knowledge' },
  { id: 'memory', label: 'Memory', icon: 'database', hint: 'Recall stored memory' },
  { id: 'automation', label: 'Automate', icon: 'run-all', hint: 'Create a scheduled task' },
  { id: 'communication', label: 'Comm', icon: 'comment-discussion', hint: 'Messaging providers' },
] as const

function GatewayBanner() {
  const status = useStore($jarvisSystemStatus)
  const detail = useStore($jarvisGatewayDetail)
  const socket = useStore($gatewayState)

  if (status.gateway === 'connected') {return null}

  const label =
    status.gateway === 'connecting' ? 'Gateway connecting…'
    : status.gateway === 'reconnecting' ? `Gateway reconnecting… (attempt ${detail.reconnectAttempt})`
    : status.gateway === 'starting' ? 'Starting backend…'
    : status.gateway === 'degraded' ? 'Gateway degraded — socket open, health check failing'
    : status.gateway === 'error' ? `Gateway error${detail.error ? ` — ${detail.error}` : ''}`
    : status.gateway === 'stopped' ? 'Gateway stopped'
    : `Gateway disconnected (socket: ${socket})${detail.error ? ` — ${detail.error}` : ''}`

  return (
    <div
      className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/[0.06] px-4 py-2.5"
      role="alert"
    >
      <span className="codicon codicon-warning text-amber-400" />
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium text-amber-200">{label}</div>
        <div className="text-[11px] text-white/30">
          Commands queue as UNAVAILABLE until the gateway reconnects. The socket auto-reconnects with backoff.
        </div>
      </div>
    </div>
  )
}

function ExecutionBanner() {
  const exec = useStore($jarvisExecution)

  if (exec.state === 'IDLE' || exec.state === 'COMPLETED') {return null}

  const label =
    exec.state === 'FAILED' ? `Failed — ${exec.error ?? 'unknown error'}`
    : exec.state === 'TIMEOUT' ? `Timed out — ${exec.error ?? 'no response in time'}`
    : exec.state === 'UNAVAILABLE' ? `Unavailable — ${exec.error ?? 'gateway is not connected'}`
    : exec.state === 'CANCELLED' ? 'Cancelled'
    : exec.state === 'AWAITING_PERMISSION' ? 'Waiting for approval…'
    : exec.state === 'STREAMING' ? 'Streaming live agent output…'
    : `${exec.state.charAt(0)}${exec.state.slice(1).toLowerCase()}…`

  const tone =
    exec.state === 'FAILED' || exec.state === 'TIMEOUT' || exec.state === 'UNAVAILABLE'
      ? 'border-red-500/30 bg-red-500/[0.06] text-red-200'
      : 'border-[#00d4ff]/30 bg-[#00d4ff]/[0.06] text-[#00d4ff]'

  return (
    <div className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 ${tone}`} role="status">
      <span
        className={`codicon ${exec.state === 'FAILED' || exec.state === 'TIMEOUT' || exec.state === 'UNAVAILABLE' ? 'codicon-error' : 'codicon-loading'} ${exec.state === 'EXECUTING' || exec.state === 'STREAMING' ? 'animate-spin' : ''}`}
      />
      <div className="min-w-0 flex-1 text-[12px] font-medium">{label}</div>
      {(exec.state === 'EXECUTING' || exec.state === 'STREAMING' || exec.state === 'PLANNING') && (
        <button
          className="rounded-lg border border-white/10 px-2.5 py-1 text-[11px] text-white/50 hover:bg-white/[0.06] hover:text-white/80"
          onClick={() => cancelJarvisPipeline()}
        >
          Cancel (Esc)
        </button>
      )}
    </div>
  )
}

function HomeDashboard() {
  const status = useStore($jarvisSystemStatus)
  const sessions = useStore($sessions)
  const workingIds = useStore($workingSessionIds)
  const activeSessionId = useStore($activeSessionId)
  const commandLog = useStore($jarvisCommandLog)

  const running = sessions.filter(s => workingIds.includes(s.id))
  const recent = sessions.slice(0, 5)

  return (
    <div className="size-full overflow-y-auto scrollbar-dt">
      <div className="mx-auto max-w-5xl space-y-4 p-6">
        <GatewayBanner />
        <ExecutionBanner />

        {/* Welcome / command center */}
        <div className="rounded-2xl border border-white/[0.06] bg-black/40 p-5 backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <div aria-hidden className="relative size-14 shrink-0">
              <AiOrb />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-[17px] font-semibold text-white/85">What do you want to accomplish?</h1>
              <p className="mt-0.5 text-[12px] text-white/35">
                Type below — commands execute against the live gateway
                ({status.gateway === 'connected' ? 'connected' : status.gateway}
                {' · '}backend {status.backend}
                {status.model ? ` · ${status.model}` : ''}). Use Enter to send, Esc to cancel.
              </p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {QUICK_ACTIONS.map(action => (
              <button
                aria-label={`${action.label}: ${action.hint}`}
                className="group rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-left transition-all hover:border-[#00d4ff]/30 hover:bg-[#00d4ff]/[0.05]"
                key={action.id}
                onClick={() => setJarvisMissionView(action.id as never)}
                title={action.hint}
              >
                <span className={`codicon codicon-${action.icon} text-base text-white/40 group-hover:text-[#00d4ff]`} />
                <div className="mt-1 text-[12px] font-medium text-white/70">{action.label}</div>
                <div className="truncate text-[10px] text-white/25">{action.hint}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Active work — real sessions only */}
        <div className="rounded-2xl border border-white/[0.06] bg-black/40 p-5 backdrop-blur-xl">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-white/30">Active work</h2>
            <span className="text-[11px] text-white/25">{running.length} running</span>
          </div>
          {running.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 px-4 py-5 text-center">
              <div className="text-[12px] text-white/40">No active work</div>
              <div className="mt-1 text-[11px] text-white/25">Run an agent or send a command to see it here.</div>
            </div>
          ) : (
            <div className="space-y-2">
              {running.map(session => (
                <div
                  className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] px-3 py-2"
                  key={session.id}
                >
                  <span className="size-2 shrink-0 animate-pulse rounded-full bg-emerald-400" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[12px] font-medium text-white/75">
                      {session.title || session.id.slice(0, 12)}
                    </div>
                    <div className="text-[10px] text-white/30">
                      {session.id === activeSessionId ? 'Active session · ' : ''}Running
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent activity — real command + session data, never samples */}
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-white/[0.06] bg-black/40 p-5 backdrop-blur-xl">
            <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-white/30">Recent sessions</h2>
            {recent.length === 0 ? (
              <div className="text-[12px] text-white/30">
                No sessions yet. <span className="text-white/45">Start a chat to create one.</span>
              </div>
            ) : (
              <div className="space-y-1.5">
                {recent.map(session => (
                  <div className="flex items-center gap-2 text-[12px]" key={session.id}>
                    <span className={`size-1.5 rounded-full ${workingIds.includes(session.id) ? 'bg-emerald-400' : 'bg-white/20'}`} />
                    <span className="min-w-0 flex-1 truncate text-white/60">{session.title || session.id.slice(0, 16)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-white/[0.06] bg-black/40 p-5 backdrop-blur-xl">
            <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.15em] text-white/30">Recent commands</h2>
            {commandLog.length === 0 ? (
              <div className="text-[12px] text-white/30">
                No commands yet. <span className="text-white/45">Every Jarvis command is recorded here with status.</span>
              </div>
            ) : (
              <div className="space-y-1.5">
                {commandLog.slice(0, 5).map(record => (
                  <div className="flex items-center gap-2 text-[12px]" key={record.id}>
                    <span
                      className={`size-1.5 rounded-full ${record.status === 'COMPLETED' ? 'bg-emerald-400' : record.status === 'FAILED' || record.status === 'TIMEOUT' || record.status === 'UNAVAILABLE' ? 'bg-red-400' : 'bg-amber-400'}`}
                    />
                    <span className="min-w-0 flex-1 truncate text-white/60">{record.input}</span>
                    <span className="shrink-0 text-[10px] text-white/25">{record.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function MissionControlComponent() {
  const activeView = useStore($jarvisMissionView)
  const leftSection = useStore($jarvisLeftPanelSection)
  const displayMode = useStore($jarvisDisplayMode)
  const isOrbView = activeView === 'orb'
  const navigate = useNavigate()
  const voice = useJarvisVoice(navigate)
  const [pendingApproval, setPendingApproval] = useState<{ input: string; message: string } | null>(null)

  // Keep Jarvis status synced with the real gateway lifecycle for the life of
  // this view. Navigation between Jarvis ↔ Home must not reset runtime state —
  // this subscription only mirrors, it never destroys sessions or sockets.
  useEffect(() => {
    const stop = startJarvisGatewaySync()

    return () => stop()
  }, [])

  // Esc cancels the in-flight command AND any live voice capture/speech
  // without tearing down the view. Ctrl+Space focuses the composer.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        voice.cancel()
        cancelJarvisPipeline()
      }

      if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('jarvis:focus-composer'))
      }
    }

    window.addEventListener('keydown', onKey)

    return () => window.removeEventListener('keydown', onKey)
  }, [voice])

  // OS-global hotkey (main process) lands here when already in Jarvis.
  useEffect(() => {
    const desktop = window.aetherosDesktop as unknown as { onJarvisFocus?: (cb: () => void) => () => void }

    if (typeof desktop.onJarvisFocus !== 'function') {return}

    return desktop.onJarvisFocus(() => {
      window.dispatchEvent(new CustomEvent('jarvis:focus-composer'))
    })
  }, [])

  const runCommand = useCallback((command: string, approved: boolean) => {
    // Duplicate-submit guard BEFORE the reset: resetting first would mask the
    // in-flight state and let a double-Enter spawn two gateway sessions.
    // Allow-once resubmits bypass (the gated command reset to IDLE already).
    if (!approved && isJarvisExecutingState($jarvisExecution.get().state)) {
      addJarvisNotification({ title: 'Already running', message: 'A Jarvis command is already running — press Esc to cancel it first.', type: 'info' })

      return
    }

    const startedAt = Date.now()
    resetJarvisExecution()
    setJarvisThinkingStage('understanding', 'Analyzing command...')
    setJarvisOrbState('thinking')

    submitJarvisCommand(command, {
      inputType: 'text',
      approved,
      deps: createDesktopCommandDeps(navigate),
      onStepUpdate: (stepId: string, status: string) => {
        if (status === 'running') {
          const stageMap: Record<string, 'understanding' | 'planning' | 'searching' | 'executing' | 'validating'> = {
            understand: 'understanding', plan: 'planning', search: 'searching',
            execute: 'executing', code: 'executing', validate: 'validating'
          }

          const stage = stageMap[stepId.split('-')[0]] || 'executing'
          setJarvisThinkingStage(stage, `${stepId}...`)
        }
      },
      onThinkingStage: (stage: string, label: string) => {
        setJarvisThinkingStage(stage as 'understanding', label)
      }
    }).then(result => {
      const runtimeMs = Date.now() - startedAt
      void runtimeMs
      addJarvisNotification({ title: 'Task Complete', message: result.response?.slice(0, 100) ?? 'Command processed', type: 'success' })
      setJarvisOrbState('success')
      setTimeout(() => setJarvisOrbState('idle'), 2000)
      setJarvisThinkingStage('complete', 'Complete')
    }).catch((err: Error) => {
      if (err instanceof ApprovalRequiredError) {
        // Destructive or gated action: show explicit Allow once / Cancel.
        // Nothing has executed yet.
        setPendingApproval({ input: err.input, message: err.message })
        setJarvisThinkingStage('idle', '')
        setJarvisOrbState('idle')
        resetJarvisExecution()

        return
      }

      if (err instanceof GatewayUnavailableError) {
        addJarvisNotification({
          title: 'Gateway unavailable',
          message: 'Reconnect the gateway, then retry the command. Nothing was executed.',
          type: 'error'
        })
      } else {
        addJarvisNotification({ title: 'Task Failed', message: err.message, type: 'error' })
      }

      setJarvisOrbState('error')
      setTimeout(() => setJarvisOrbState('idle'), 3000)
    })
  }, [navigate])

  const handleCommand = useCallback((command: string) => {
    setPendingApproval(null)
    runCommand(command, false)
  }, [runCommand])

  // Palette agent actions delegate through the same gateway.
  useEffect(() => {
    setPaletteCommandSink(handleCommand)

    return () => setPaletteCommandSink(null)
  }, [handleCommand])

  const rootClass =
    displayMode === 'compact'
      ? 'fixed inset-x-4 bottom-4 top-[22%] z-[9999] flex flex-col bg-[#05050a] overflow-hidden rounded-2xl border border-white/10 shadow-2xl'
      : displayMode === 'expanded'
        ? 'fixed inset-4 z-[9999] flex flex-col bg-[#05050a] overflow-hidden rounded-2xl border border-white/10 shadow-2xl'
        : 'fixed inset-0 z-[9999] flex flex-col bg-[#05050a] overflow-hidden'

  return (
    <div className={rootClass}>
      <BackgroundSystem />

      <div className="relative z-20">
        <JarvisStatusBar />
      </div>

      <div className="relative z-10 flex flex-1 min-h-0">
        <MissionNav />

        {/* Center stage */}
        <div className="flex-1 min-w-0 relative">
          <div className="absolute inset-0">
            <AnimatePresence mode="wait">
              <motion.div
                animate={{ opacity: 1, scale: 1 }}
                className="size-full"
                exit={{ opacity: 0, scale: 0.98 }}
                initial={{ opacity: 0, scale: 0.98 }}
                key={activeView}
                transition={{ duration: 0.3 }}
              >
                {isOrbView ? <HomeDashboard /> : <SectionContent />}
              </motion.div>
            </AnimatePresence>
          </div>

          <ExecutionTimeline />
          <AgentOrchestra />
        </div>

        <IntelFeed />
      </div>

      <div className="relative z-20">
        {/* Explicit approval gate: nothing has executed yet. Allow once
            resubmits this exact command; Cancel drops it. */}
        <AnimatePresence>
          {pendingApproval && (
            <motion.div
              animate={{ opacity: 1, y: 0 }}
              className="mx-4 mb-2 rounded-xl border border-amber-500/40 bg-amber-500/[0.08] px-4 py-3"
              exit={{ opacity: 0, y: 8 }}
              initial={{ opacity: 0, y: 8 }}
              role="alertdialog"
            >
              <div className="text-[12px] font-medium text-amber-200">Approval required</div>
              <div className="mt-0.5 text-[11px] text-white/50">{pendingApproval.message}</div>
              <div className="mt-1 max-h-16 overflow-auto font-mono text-[11px] text-white/70">
                {pendingApproval.input}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  className="rounded-lg bg-amber-500/20 px-3 py-1 text-[11px] font-medium text-amber-200 hover:bg-amber-500/30"
                  onClick={() => {
                    const approved = pendingApproval.input
                    setPendingApproval(null)
                    runCommand(approved, true)
                  }}
                >
                  Allow once
                </button>
                <button
                  className="rounded-lg border border-white/10 px-3 py-1 text-[11px] text-white/50 hover:bg-white/[0.06] hover:text-white/80"
                  onClick={() => setPendingApproval(null)}
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <CommandBar onCommand={handleCommand} />
      </div>

      <CommandPalette />
      <NotificationCenter />

      <SystemStatusPoller />
    </div>
  )
}

function SystemStatusPoller() {
  const poll = useCallback(async () => {
    try {
      const stats = await window.aetherosDesktop?.getSystemStats?.()

      if (stats) {
        updateJarvisSystemStatus({ cpu: stats.cpu, memory: stats.memory, gpu: stats.gpu, uptime: stats.uptime })
      }
    } catch { /* ignore */ }

    // Gateway/backend lifecycle is mirrored by startJarvisGatewaySync (live
    // atom subscription). This poll only refreshes slow-moving facts (model)
    // so the two never fight over the gateway field.
    try {
      const gateway = (await import('@/store/gateway')).activeGateway()

      if (gateway?.connectionState === 'open') {
        const info = await gateway
          .request<{ model?: string; provider?: string }>('session.info', {})
          .catch(() => null)

        if (info && (info.model || info.provider)) {
          updateJarvisSystemStatus({
            ...(info.model ? { model: info.model } : {}),
            ...(info.provider ? { provider: info.provider } : {})
          })
        }
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    poll(); const id = setInterval(poll, 15000)

    return () => clearInterval(id)
  }, [poll])

  return null
}

export const MissionControl = memo(MissionControlComponent)
