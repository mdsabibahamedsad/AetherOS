import {
  $jarvisGatewayDetail,
  mapSocketToGatewayState,
  updateJarvisGatewayDetail,
  updateJarvisSystemStatus
} from '@/store/jarvis-mode'
import { $connection, $gatewayState } from '@/store/session'
import { $healthStatus } from '@/store/system'

let started = false

/**
 * Mirror the real gateway/backend lifecycle into the Jarvis status store.
 *
 * Root cause fixed: $jarvisSystemStatus.gateway was only ever written at
 * declaration time ('disconnected') — no poller or subscriber ever updated
 * it, so Mission Control permanently rendered "GATEWAY disconnected" even
 * with a healthy open socket. This sync derives the user-facing lifecycle
 * from the live atoms ($gatewayState, $connection, $healthStatus) fed by
 * use-gateway-boot and the main-process health IPC.
 */
export function startJarvisGatewaySync(): () => void {
  if (started) {return () => undefined}
  started = true

  const sync = () => {
    const socket = String($gatewayState.get() ?? 'idle')
    const conn = $connection.get()
    const health = $healthStatus.get()
    const prev = $jarvisGatewayDetail.get()

    // Backend: process health from main; unknown before first report.
    const backendRunning = health
      ? health.services.some(s => s.status === 'running') || health.overall === 'healthy'
      : Boolean(conn)

    updateJarvisSystemStatus({
      backend: backendRunning ? 'running' : conn ? 'starting' : 'stopped'
    })

    // Gateway lifecycle from socket + boot context.
    const reconnectAttempt = socket === 'open' || socket === 'connected' ? 0 : prev.reconnectAttempt

    const gateway = mapSocketToGatewayState(socket, {
      bootCompleted: Boolean(conn),
      reconnectAttempt,
      healthOk: health ? health.overall === 'healthy' : null
    })

    updateJarvisSystemStatus({ gateway })

    updateJarvisGatewayDetail({
      lastHeartbeat: socket === 'open' || socket === 'connected' ? Date.now() : prev.lastHeartbeat,
      reconnectAttempt: gateway === 'reconnecting' ? reconnectAttempt + 1 : reconnectAttempt,
      error:
        gateway === 'connected'
          ? null
          : (prev.error ?? (gateway === 'error' ? 'Gateway socket reported an error.' : null))
    })
  }

  const offs = [$gatewayState.subscribe(sync), $connection.subscribe(sync), $healthStatus.subscribe(sync)]
  sync()

  return () => {
    offs.forEach(off => off())
    started = false
  }
}

export function reportJarvisGatewayError(message: string): void {
  updateJarvisGatewayDetail({ error: message })
  updateJarvisSystemStatus({ gateway: 'error' })
}

export function reportJarvisGatewayLatency(latencyMs: number, version?: string | null): void {
  const patch: Partial<ReturnType<typeof $jarvisGatewayDetail.get>> = {
    latencyMs,
    lastHeartbeat: Date.now(),
    error: null
  }

  if (version !== undefined) {patch.version = version}
  updateJarvisGatewayDetail(patch)
}
