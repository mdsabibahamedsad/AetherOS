import type { GatewayRequester } from './yolo-session'

export interface NetworkAgent {
  agent_id: string
  trust: string
  health: string
  source: string
  latency_ms: number | null
  removed: boolean
}

export interface NetworkTask {
  task_id: string
  target_agent: string
  purpose: string
  status: string
  data_scope: string
  created_at: number
  updated_at: number
}

export async function networkList(requestGateway: GatewayRequester): Promise<NetworkAgent[]> {
  const res = await requestGateway<{ agents?: NetworkAgent[] }>('agent.network.list', {})

  return res.agents ?? []
}

export async function networkDiscover(
  requestGateway: GatewayRequester,
  url: string,
): Promise<{ ok: boolean; agent_id?: string; errors?: string[]; warnings?: string[] }> {
  return requestGateway('agent.network.discover', { url })
}

export async function networkInfo(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('agent.network.info', { id })
}

export async function networkVerify(
  requestGateway: GatewayRequester,
  id: string,
): Promise<{ label: string; errors: string[]; warnings: string[] }> {
  return requestGateway('agent.network.verify', { id })
}

export async function networkTrust(
  requestGateway: GatewayRequester,
  id: string,
  level: string,
): Promise<{ trust: string }> {
  return requestGateway('agent.network.trust', { id, level })
}

export async function networkBlock(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('agent.network.block', { id })
}

export async function networkRevoke(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('agent.network.revoke', { id })
}

export async function networkConnect(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('agent.network.connect', { id })
}

export async function networkDelegate(
  requestGateway: GatewayRequester,
  id: string,
  task: string,
  permissions: string[] = ['agent.task.submit'],
  data_scope = 'internal',
): Promise<{ task_id: string; status: string }> {
  return requestGateway('agent.network.delegate', { id, task, permissions, data_scope })
}

export async function networkTasks(
  requestGateway: GatewayRequester,
): Promise<{ tasks: NetworkTask[]; queue: Record<string, unknown> }> {
  return requestGateway('agent.network.tasks', {})
}

export async function networkCancel(requestGateway: GatewayRequester, task: string): Promise<void> {
  await requestGateway('agent.network.cancel', { task })
}

export async function networkActivity(
  requestGateway: GatewayRequester,
  limit = 100,
): Promise<Record<string, unknown>[]> {
  const res = await requestGateway<{ events?: Record<string, unknown>[] }>('agent.network.activity', { limit })

  return res.events ?? []
}

export async function networkSecurity(
  requestGateway: GatewayRequester,
): Promise<Record<string, unknown>> {
  return requestGateway('agent.network.security', {})
}
