import type { GatewayRequester } from './yolo-session'

export interface SwarmRunView {
  run_id: string
  goal: string
  status: string
  topology: string
  mode: string
  roles: string[]
  tasks: { id: string; goal: string; state: string; role: string; agent: string; deps: string[]; error: string }[]
  agents: { id: string; role: string; status: string; tools: string[]; tokens: number; cost: number; current_action: string; errors: string[] }[]
  final: Record<string, unknown> | null
}

export interface SwarmRunEvent {
  seq: number
  kind: string
  task_id: string
  agent_id: string
  at: number
  detail: Record<string, unknown>
}

export async function swarmStart(
  requestGateway: GatewayRequester,
  goal: string,
  opts: { force_single?: boolean; execute?: boolean; project_id?: string } = {},
): Promise<SwarmRunView> {
  return requestGateway<SwarmRunView>('swarm.start', { goal, ...opts })
}

export async function swarmStatus(
  requestGateway: GatewayRequester,
  runId: string,
): Promise<SwarmRunView> {
  return requestGateway<SwarmRunView>('swarm.status', { run_id: runId })
}

export async function swarmStop(requestGateway: GatewayRequester, runId: string): Promise<void> {
  await requestGateway('swarm.stop', { run_id: runId })
}

export async function swarmEvents(
  requestGateway: GatewayRequester,
  runId: string,
  afterSeq = 0,
): Promise<SwarmRunEvent[]> {
  const res = await requestGateway<{ events?: SwarmRunEvent[] }>('swarm.events', {
    run_id: runId,
    after_seq: afterSeq,
  })

  return res.events ?? []
}

export async function swarmTrace(
  requestGateway: GatewayRequester,
  runId: string,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ trace?: Record<string, unknown> }>('swarm.trace', {
    run_id: runId,
  })

  return res.trace ?? {}
}

export async function swarmApprove(
  requestGateway: GatewayRequester,
  requestId: string,
  approved: boolean,
): Promise<void> {
  await requestGateway('swarm.approve', { request_id: requestId, approved })
}
