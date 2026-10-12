import { useStore } from '@nanostores/react'
import { useCallback, useState } from 'react'

import { emergencyStopAll, type StopReport } from '@/lib/emergency-stop'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify, notifyError } from '@/store/notifications'
import { $gatewayState } from '@/store/session'
import { $healthStatus } from '@/store/system'

export type GlobalStatusLevel = 'operational' | 'degraded' | 'offline'

/**
 * Subtle global status indicator (Master 63 §109) + emergency stop (§56, §180).
 *
 * Freshness-first: status derives from live stores — gateway connection state
 * and the health atom — never from static markup. "Operational" requires an
 * open gateway AND a healthy report; anything else degrades honestly.
 * STOP ALL AGENTS drives `emergencyStopAll` (real session.interrupt /
 * process.stop / automation.stop_all / swarm.stop legs) and reports per-leg
 * results. It never merely hides UI.
 */
export function useGlobalStatus(): { level: GlobalStatusLevel; label: string; degradedSystems: number } {
  const gatewayState = useStore($gatewayState)
  const health = useStore($healthStatus)

  if (gatewayState !== 'open' && gatewayState !== 'connected') {
    return { level: 'offline', label: 'Offline', degradedSystems: 0 }
  }

  if (!health) {
    // Connected but no health report yet: honest degraded, not fake green.
    return { level: 'degraded', label: 'Connecting', degradedSystems: 0 }
  }

  if (health.overall === 'healthy') {
    return { level: 'operational', label: 'Operational', degradedSystems: 0 }
  }

  const bad = health.services.filter(s => s.status !== 'running').length

  return {
    level: 'degraded',
    label: `${bad} system${bad === 1 ? '' : 's'} degraded`,
    degradedSystems: bad,
  }
}

const DOT: Record<GlobalStatusLevel, string> = {
  operational: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  offline: 'bg-red-500',
}

export function GlobalStatusIndicator({ className }: { className?: string }) {
  const status = useGlobalStatus()

  return (
    <span
      aria-label={`System status: ${status.label}`}
      className={cn('inline-flex items-center gap-1.5 text-xs text-muted-foreground', className)}
      data-testid="global-status"
      role="status"
    >
      <span aria-hidden className={cn('size-2 rounded-full', DOT[status.level])} />
      {status.level === 'operational' ? '● Operational' : `● ${status.label}`}
    </span>
  )
}

export function StopAllAgentsButton({ className }: { className?: string }) {
  const gateway = useStore($gateway)
  const [stopping, setStopping] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const run = useCallback(async () => {
    if (!gateway) {
      notifyError(new Error('Gateway is not connected'), 'STOP ALL unavailable while offline')

      return
    }

    setStopping(true)

    try {
      const report: StopReport = await emergencyStopAll((method, params) =>
        gateway.request(method, params ?? {}),
      )

      const failed = report.legs.filter(l => !l.ok)

      if (failed.length === 0) {
        notify({
          kind: 'success',
          title: 'All agents stopped',
          message: `${report.stoppedSessions} session(s) interrupted; processes, automations, swarm halted.`,
        })
      } else {
        notifyError(
          new Error(failed.map(l => `${l.leg}: ${l.detail}`).join('; ')),
          'STOP ALL partially completed — inspect each leg',
        )
      }
    } catch (e) {
      notifyError(e, 'STOP ALL failed')
    } finally {
      setStopping(false)
      setConfirming(false)
    }
  }, [gateway])

  if (!confirming) {
    return (
      <button
        aria-label="Stop all agents"
        className={cn(
          'rounded-md border border-red-500/40 px-2.5 py-1 text-xs font-semibold text-red-500 transition-colors hover:bg-red-500/10 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-40',
          className,
        )}
        data-testid="stop-all-agents"
        disabled={stopping || !gateway}
        onClick={() => setConfirming(true)}
        title={gateway ? 'Interrupt all live sessions, processes, automations, and swarms' : 'Unavailable while gateway is offline'}
        type="button"
      >
        STOP ALL
      </button>
    )
  }

  return (
    <span aria-label="Confirm stop all agents" className={cn('inline-flex items-center gap-2', className)} role="alertdialog">
      <span className="text-xs text-muted-foreground">Stop everything?</span>
      <button
        className="rounded-md px-2 py-1 text-xs font-semibold text-muted-foreground hover:bg-accent"
        disabled={stopping}
        onClick={() => setConfirming(false)}
        type="button"
      >
        Cancel
      </button>
      <button
        className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-40"
        data-testid="stop-all-confirm"
        disabled={stopping}
        onClick={run}
        type="button"
      >
        {stopping ? 'Stopping…' : 'Stop all agents'}
      </button>
    </span>
  )
}
