import type { GatewayRequester } from './yolo-session'

export interface ExtRecord {
  id: string
  manifest: Record<string, unknown>
  source: string
  state: string
  installed_version: string
  available_version: string
  trust_level: string
  grants: Record<string, unknown>[]
  health: Record<string, unknown>
}

export async function extensionList(
  requestGateway: GatewayRequester,
  opts: { query?: string; type?: string; state?: string } = {},
): Promise<ExtRecord[]> {
  const res = await requestGateway<{ extensions?: ExtRecord[] }>('extension.list', { ...opts })

  return res.extensions ?? []
}

export async function extensionInfo(requestGateway: GatewayRequester, id: string): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ extension?: Record<string, unknown> }>('extension.info', { id })

  return res.extension ?? {}
}

export async function extensionInstall(requestGateway: GatewayRequester, source: string): Promise<Record<string, unknown>> {
  return requestGateway<Record<string, unknown>>('extension.install', { source })
}

export async function extensionUninstall(requestGateway: GatewayRequester, id: string): Promise<Record<string, unknown>> {
  return requestGateway<Record<string, unknown>>('extension.uninstall', { id })
}

export async function extensionEnable(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('extension.enable', { id })
}

export async function extensionDisable(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('extension.disable', { id })
}

export async function extensionVerify(requestGateway: GatewayRequester, id: string): Promise<Record<string, unknown>> {
  return requestGateway<Record<string, unknown>>('extension.verify', { id })
}

export async function extensionPermissions(requestGateway: GatewayRequester, id: string): Promise<Record<string, unknown>> {
  return requestGateway<Record<string, unknown>>('extension.permissions', { id })
}

export async function extensionRevoke(requestGateway: GatewayRequester, id: string): Promise<void> {
  await requestGateway('extension.revoke', { id })
}

export async function extensionQuarantine(requestGateway: GatewayRequester, id: string, reason: string): Promise<void> {
  await requestGateway('extension.quarantine', { id, reason })
}

export async function extensionEvents(requestGateway: GatewayRequester): Promise<Record<string, unknown>[]> {
  const res = await requestGateway<{ events?: Record<string, unknown>[] }>('extension.events', {})

  return res.events ?? []
}
