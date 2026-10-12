import type { GatewayRequester } from './yolo-session'

export interface AutomationDef {
  id: string
  name: string
  description: string
  enabled: boolean
  auto_type: string
  version: number
  next_run: number
  last_run: number
}

export async function automationSearch(
  requestGateway: GatewayRequester,
  opts: { query?: string; status?: string; trigger?: string } = {},
): Promise<AutomationDef[]> {
  const res = await requestGateway<{ automations?: AutomationDef[] }>('automation.search', { ...opts })

  return res.automations ?? []
}

export async function automationPreview(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ preview?: Record<string, unknown> }>('automation.preview', { id })

  return res.preview ?? {}
}

export async function automationEnable(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('automation.enable', { id })
}

export async function automationDisable(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('automation.disable', { id })
}

export async function automationDelete(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('automation.delete', { id })
}

export async function automationRun(
  requestGateway: GatewayRequester,
  id: string,
  dryRun = false,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ run?: Record<string, unknown> }>('automation.run', { id, dry_run: dryRun })

  return res.run ?? {}
}

export async function automationRuns(
  requestGateway: GatewayRequester,
  id = '',
  limit = 50,
): Promise<Record<string, unknown>[]> {
  const res = await requestGateway<{ runs?: Record<string, unknown>[] }>('automation.runs', { id, limit })

  return res.runs ?? []
}

export async function automationBuild(
  requestGateway: GatewayRequester,
  text: string,
): Promise<Record<string, unknown>> {
  return requestGateway<Record<string, unknown>>('automation.build', { text })
}

export async function automationHealth(
  requestGateway: GatewayRequester,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ health?: Record<string, unknown>; metrics?: Record<string, unknown> }>('automation.health', {})

  return { ...(res.health ?? {}), metrics: res.metrics ?? {} }
}

export async function automationStopAll(requestGateway: GatewayRequester): Promise<void> {
  await requestGateway('automation.stop_all', {})
}
