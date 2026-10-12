import type { GatewayRequester } from './yolo-session'

export interface MarketServiceHit {
  service_id: string
  agent_id: string
  source: string
  exact: boolean
  keyword_score: number
  reasons: string[]
  service: Record<string, unknown>
}

export interface MarketMetric {
  value: number
  confidence: number
  sample_count: number
  time_window_days: number
  provenance: string
}

export interface RankedCandidate {
  agent_id: string
  service_id: string
  source: string
  score: number
  breakdown: Record<string, unknown>
  eligible: boolean
  rejection: string
}

export interface DelegationResult {
  status: string
  delegation_id?: string
  contract_id?: string
  transaction_id?: string
  network_task_id?: string
  correlation_id?: string
  tier?: string
  amount_minor?: number
  currency?: string
}

export async function marketSearch(
  requestGateway: GatewayRequester,
  query: string,
  opts: { capabilities?: string[]; max_price_minor?: number; data_class?: string; limit?: number } = {},
): Promise<{ hits: MarketServiceHit[]; query: string }> {
  return requestGateway('marketplace.search', { query, ...opts })
}

export async function marketAgent(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.agent.get', { id })
}

export async function marketService(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.service.get', { id })
}

export async function marketCompare(
  requestGateway: GatewayRequester,
  agent_ids: string[],
  query = '',
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.compare', { agent_ids, query })
}

export async function marketQuote(
  requestGateway: GatewayRequester,
  quote: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.quote', { quote })
}

export async function marketContractCreate(
  requestGateway: GatewayRequester,
  contract: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.contract.create', { contract })
}

export async function marketContractApprove(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.contract.approve', { id })
}

export async function marketDelegate(
  requestGateway: GatewayRequester,
  task: Record<string, unknown>,
  selection: Record<string, unknown>,
  approved_by = '',
  auto = false,
): Promise<DelegationResult> {
  return requestGateway('marketplace.delegate', { task, selection, approved_by, auto })
}

export async function marketTaskStatus(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.task.status', { id })
}

export async function marketTransactions(
  requestGateway: GatewayRequester,
  contract_id = '',
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.transaction.get', { contract_id })
}

export async function marketReputation(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.reputation.get', { id })
}

export async function marketTrust(
  requestGateway: GatewayRequester,
  id: string,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.trust.get', { id })
}

export async function marketBudget(
  requestGateway: GatewayRequester,
  scope = 'user',
  scope_id = '',
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.budget.get', { scope, scope_id })
}

export async function marketPolicy(
  requestGateway: GatewayRequester,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.policy.get', {})
}

export async function marketPolicyUpdate(
  requestGateway: GatewayRequester,
  preferences: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.policy.update', { preferences })
}

export async function marketDispute(
  requestGateway: GatewayRequester,
  dispute: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return requestGateway('marketplace.dispute.create', { dispute })
}
