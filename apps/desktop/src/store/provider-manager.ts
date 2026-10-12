import { atom } from 'nanostores'

export type HealthStatus = 'unknown' | 'online' | 'offline' | 'auth_failed' | 'quota_exceeded' | 'slow' | 'unavailable'
export type ProviderCategory = 'cloud' | 'local' | 'custom'

export interface ManagerProvider {
  slug: string
  name: string
  category: ProviderCategory
  authType: 'api_key' | 'oauth' | 'local' | 'aws_sdk' | 'external'
  authenticated: boolean
  connected: boolean
  health: HealthStatus
  latencyMs: number | null
  modelCount: number
  version: string | null
  lastSync: string | null
  usage: ProviderUsage | null
  capabilities: string[]
  keyEnv: string | null
  baseUrl: string | null
}

export interface ProviderUsage {
  dailyTokens: number
  monthlyTokens: number
  dailyCost: number
  monthlyCost: number
  creditsRemaining: number | null
}

export interface ManagerModel {
  id: string
  provider: string
  providerName: string
  name: string
  contextLength: number | null
  maxTokens: number | null
  pricing: ModelPricingInfo | null
  capabilities: ModelCapabilitiesInfo
  favorite: boolean
  pinned: boolean
  hidden: boolean
  roles: ModelRole[]
  latencyMs: number | null
  speed: 'fast' | 'medium' | 'slow' | null
}

export interface ModelPricingInfo {
  input: string
  output: string
  cache: string | null
  free: boolean
}

export interface ModelCapabilitiesInfo {
  vision: boolean
  audio: boolean
  functionCalling: boolean
  reasoning: boolean
  streaming: boolean
  embedding: boolean
  toolSupport: boolean
}

export type ModelRole =
  | 'default'
  | 'coding'
  | 'reasoning'
  | 'vision'
  | 'embedding'
  | 'speech'
  | 'fast'
  | 'long-context'

export const ROLE_LABELS: Record<ModelRole, string> = {
  default: 'Default',
  coding: 'Coding',
  reasoning: 'Reasoning',
  vision: 'Vision',
  embedding: 'Embedding',
  speech: 'Speech',
  fast: 'Fast',
  'long-context': 'Long Context'
}

export interface HealthEvent {
  provider: string
  status: HealthStatus
  latencyMs: number
  timestamp: string
  error: string | null
}

export interface RouterRule {
  task: string
  taskLabel: string
  provider: string | null
  model: string | null
  enabled: boolean
  priority: number
}

export const ROUTER_TASKS = [
  { id: 'default', label: 'Default Chat' },
  { id: 'coding', label: 'Coding' },
  { id: 'reasoning', label: 'Reasoning' },
  { id: 'vision', label: 'Vision' },
  { id: 'embedding', label: 'Embedding' },
  { id: 'voice', label: 'Voice' },
  { id: 'automation', label: 'Automation' },
  { id: 'research', label: 'Research' }
]

export interface TesterResult {
  prompt: string
  model: string
  provider: string
  latencyMs: number
  tokensIn: number
  tokensOut: number
  tokensPerSecond: number
  streaming: boolean
  error: string | null
  timestamp: string
}

export interface ProviderSettings {
  timeout: number
  retries: number
  fallbackProvider: string | null
  preferredProvider: string | null
  streaming: boolean
  parallelRequests: boolean
  caching: boolean
  compression: boolean
  maxConcurrency: number
}

export interface ProviderManagerState {
  providers: ManagerProvider[]
  models: ManagerModel[]
  healthHistory: HealthEvent[]
  routerRules: RouterRule[]
  testerResults: TesterResult[]
  settings: ProviderSettings
  selectedProvider: string | null
  searchQuery: string
  modelFilterProvider: string | null
  modelFilterRole: ModelRole | null
  modelSort: 'name' | 'provider' | 'context' | 'latency'
  sortAsc: boolean
  showHiddenModels: boolean
  localScanning: boolean
  localModels: string[]
}

const DEFAULT_SETTINGS: ProviderSettings = {
  timeout: 30000,
  retries: 3,
  fallbackProvider: null,
  preferredProvider: null,
  streaming: true,
  parallelRequests: false,
  caching: true,
  compression: true,
  maxConcurrency: 5
}

export const $providerManager = atom<ProviderManagerState>({
  providers: [],
  models: [],
  healthHistory: [],
  routerRules: ROUTER_TASKS.map(t => ({
    task: t.id,
    taskLabel: t.label,
    provider: null,
    model: null,
    enabled: true,
    priority: ROUTER_TASKS.findIndex(x => x.id === t.id)
  })),
  testerResults: [],
  settings: DEFAULT_SETTINGS,
  selectedProvider: null,
  searchQuery: '',
  modelFilterProvider: null,
  modelFilterRole: null,
  modelSort: 'name',
  sortAsc: true,
  showHiddenModels: false,
  localScanning: false,
  localModels: []
})

const patch = (update: Partial<ProviderManagerState>) =>
  $providerManager.set({ ...$providerManager.get(), ...update })

export function setProviders(providers: ManagerProvider[]) {
  patch({ providers })
}

export function updateProvider(slug: string, update: Partial<ManagerProvider>) {
  const providers = $providerManager.get().providers.map(p =>
    p.slug === slug ? { ...p, ...update } : p
  )

  patch({ providers })
}

export function setSelectedProvider(slug: string | null) {
  patch({ selectedProvider: slug })
}

export function setModels(models: ManagerModel[]) {
  patch({ models })
}

export function updateModel(modelId: string, update: Partial<ManagerModel>) {
  const models = $providerManager.get().models.map(m =>
    m.id === modelId ? { ...m, ...update } : m
  )

  patch({ models })
}

export function toggleModelFavorite(modelId: string) {
  const models = $providerManager.get().models.map(m =>
    m.id === modelId ? { ...m, favorite: !m.favorite } : m
  )

  patch({ models })
}

export function toggleModelPin(modelId: string) {
  const models = $providerManager.get().models.map(m =>
    m.id === modelId ? { ...m, pinned: !m.pinned } : m
  )

  patch({ models })
}

export function toggleModelHidden(modelId: string) {
  const models = $providerManager.get().models.map(m =>
    m.id === modelId ? { ...m, hidden: !m.hidden, pinned: false } : m
  )

  patch({ models })
}

export function setModelRoles(modelId: string, roles: ModelRole[]) {
  const models = $providerManager.get().models.map(m =>
    m.id === modelId ? { ...m, roles } : m
  )

  patch({ models })
}

export function setSearchQuery(query: string) {
  patch({ searchQuery: query })
}

export function setModelFilterProvider(slug: string | null) {
  patch({ modelFilterProvider: slug })
}

export function setModelFilterRole(role: ModelRole | null) {
  patch({ modelFilterRole: role })
}

export function setModelSort(sort: 'name' | 'provider' | 'context' | 'latency') {
  patch({ modelSort: sort })
}

export function toggleSortAsc() {
  patch({ sortAsc: !$providerManager.get().sortAsc })
}

export function setShowHiddenModels(show: boolean) {
  patch({ showHiddenModels: show })
}

export function addHealthEvent(event: HealthEvent) {
  const history = [$providerManager.get().healthHistory, event].flat().slice(-100)
  patch({ healthHistory: history })
  updateProvider(event.provider, { health: event.status, latencyMs: event.latencyMs })
}

export function updateRouterRule(task: string, update: Partial<RouterRule>) {
  const rules = $providerManager.get().routerRules.map(r =>
    r.task === task ? { ...r, ...update } : r
  )

  patch({ routerRules: rules })
}

export function addTesterResult(result: TesterResult) {
  const results = [$providerManager.get().testerResults, result].flat().slice(-50)
  patch({ testerResults: results })
}

export function updateSettings(update: Partial<ProviderSettings>) {
  patch({ settings: { ...$providerManager.get().settings, ...update } })
}

export function setLocalScanning(scanning: boolean) {
  patch({ localScanning: scanning })
}

export function setLocalModels(models: string[]) {
  patch({ localModels: models })
}
