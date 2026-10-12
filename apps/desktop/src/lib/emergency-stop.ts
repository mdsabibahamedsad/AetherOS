// Global emergency stop: interrupts every live agent session, kills
// background processes, and halts automations + swarms through REAL
// backend methods. Every leg reports its own result — nothing is hidden,
// and nothing succeeds silently.

export type StopRequest = <T>(method: string, params?: Record<string, unknown>) => Promise<T>

export interface StopLeg {
  detail: string
  leg: 'sessions' | 'processes' | 'automations' | 'swarm'
  ok: boolean
}

export interface StopReport {
  legs: StopLeg[]
  stoppedSessions: number
}

async function tryCall<T>(request: StopRequest, method: string, params: Record<string, unknown>): Promise<{ ok: boolean; detail: string; value?: T }> {
  try {
    const value = await request<T>(method, params)

    return { detail: 'ok', ok: true, value }
  } catch (e) {
    return { detail: e instanceof Error ? e.message : String(e), ok: false }
  }
}

export async function emergencyStopAll(request: StopRequest): Promise<StopReport> {
  const legs: StopLeg[] = []
  let stoppedSessions = 0

  // 1. Interrupt every live session (stops the agent loop and denies any
  // pending approval/clarify/sudo/secret prompt for that session).
  const sessions = await tryCall<{ sessions?: Array<{ id?: string }> }>(request, 'session.active_list', {})

  if (sessions.ok) {
    const ids = (sessions.value?.sessions ?? []).map(s => s.id).filter((id): id is string => typeof id === 'string' && id.length > 0)

    for (const id of ids) {
      const r = await tryCall(request, 'session.interrupt', { session_id: id })

      if (r.ok) {
        stoppedSessions += 1
      } else {
        legs.push({ detail: `${id.slice(0, 8)}: ${r.detail}`, leg: 'sessions', ok: false })
      }
    }

    legs.push({ detail: `${stoppedSessions}/${ids.length} sessions interrupted`, leg: 'sessions', ok: stoppedSessions === ids.length })
  } else {
    legs.push({ detail: `session list failed: ${sessions.detail}`, leg: 'sessions', ok: false })
  }

  // 2. Kill background processes.
  const procs = await tryCall<{ killed?: number }>(request, 'process.stop', {})
  legs.push({
    detail: procs.ok ? `${procs.value?.killed ?? 0} background processes killed` : `process.stop failed: ${procs.detail}`,
    leg: 'processes',
    ok: procs.ok,
  })

  // 3. Halt automations.
  const autos = await tryCall(request, 'automation.stop_all', {})
  legs.push({ detail: autos.ok ? 'automations halted' : `automation.stop_all failed: ${autos.detail}`, leg: 'automations', ok: autos.ok })

  // 4. Stop the swarm runner (empty run_id = current/default run).
  const swarm = await tryCall(request, 'swarm.stop', {})
  legs.push({ detail: swarm.ok ? 'swarm stopped' : `swarm.stop failed: ${swarm.detail}`, leg: 'swarm', ok: swarm.ok })

  return { legs, stoppedSessions }
}
