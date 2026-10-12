import type { GatewayRequester } from './yolo-session'

export interface MemorySearchHit {
  id: string
  type: string
  scope: string
  score: number
  confidence: number
  confidence_band: string
  status: string
  summary: string
  content: string
  project_id: string
  conflicted: boolean
  explanation: string
}

export interface MemoryHealth {
  health: { score: number; total: number; issues: number }
  metrics: Record<string, number>
  graph: { entities: number; relationships: number }
  records: number
}

export async function memorySearch(
  requestGateway: GatewayRequester,
  query: string,
  opts: { project_id?: string; top_k?: number; mode?: string } = {},
): Promise<MemorySearchHit[]> {
  const res = await requestGateway<{ included?: MemorySearchHit[] }>('memory2.search', {
    query,
    top_k: opts.top_k ?? 8,
    mode: opts.mode ?? 'hybrid',
    ...(opts.project_id ? { project_id: opts.project_id } : {}),
  })

  return res.included ?? []
}

export async function memoryTimeline(
  requestGateway: GatewayRequester,
  opts: { project_id?: string; days?: number; limit?: number } = {},
): Promise<unknown[]> {
  const res = await requestGateway<{ items?: unknown[] }>('memory2.timeline', {
    days: opts.days ?? 30,
    limit: opts.limit ?? 100,
    ...(opts.project_id ? { project_id: opts.project_id } : {}),
  })

  return res.items ?? []
}

export async function memoryHealth(requestGateway: GatewayRequester): Promise<MemoryHealth> {
  return requestGateway<MemoryHealth>('memory2.health', {})
}

export async function memoryProject(
  requestGateway: GatewayRequester,
  projectId: string,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ project?: Record<string, unknown> }>('memory2.project', {
    project_id: projectId,
  })

  return res.project ?? {}
}

export async function memoryExplain(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  const res = await requestGateway<{ explanation?: Record<string, unknown> }>('memory2.explain', {
    id,
  })

  return res.explanation ?? {}
}

export async function memoryForget(
  requestGateway: GatewayRequester,
  opts: { id?: string; topic?: string; project_id?: string; all?: boolean },
): Promise<{ removed: number }> {
  return requestGateway<{ removed: number }>('memory2.forget', { ...opts })
}
