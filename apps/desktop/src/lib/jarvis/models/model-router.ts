import type { IntentType, ModelCapability, ModelRoute } from '../types'

// ─── Model Registry ───────────────────────────────────────────────────────────

interface ModelEntry {
  provider: string
  model: string
  capabilities: ModelCapability[]
  costPer1kInput: number
  costPer1kOutput: number
  maxTokens: number
  speed: 'fast' | 'medium' | 'slow'
  available: boolean
}

const MODEL_REGISTRY: ModelEntry[] = [
  // OpenAI
  { provider: 'openai', model: 'gpt-4o', capabilities: ['coding', 'reasoning', 'vision'], costPer1kInput: 0.0025, costPer1kOutput: 0.01, maxTokens: 128000, speed: 'medium', available: true },
  { provider: 'openai', model: 'gpt-4o-mini', capabilities: ['coding', 'fast'], costPer1kInput: 0.00015, costPer1kOutput: 0.0006, maxTokens: 128000, speed: 'fast', available: true },
  { provider: 'openai', model: 'o3', capabilities: ['reasoning', 'coding'], costPer1kInput: 0.01, costPer1kOutput: 0.04, maxTokens: 200000, speed: 'slow', available: true },
  { provider: 'openai', model: 'o3-mini', capabilities: ['reasoning', 'coding', 'fast'], costPer1kInput: 0.0011, costPer1kOutput: 0.0044, maxTokens: 200000, speed: 'medium', available: true },

  // Anthropic
  { provider: 'anthropic', model: 'claude-sonnet-4-20250514', capabilities: ['coding', 'reasoning', 'long-context'], costPer1kInput: 0.003, costPer1kOutput: 0.015, maxTokens: 200000, speed: 'medium', available: true },
  { provider: 'anthropic', model: 'claude-3-5-haiku-20241022', capabilities: ['coding', 'fast'], costPer1kInput: 0.0008, costPer1kOutput: 0.004, maxTokens: 200000, speed: 'fast', available: true },

  // Google
  { provider: 'google', model: 'gemini-2.5-pro', capabilities: ['reasoning', 'vision', 'long-context', 'coding'], costPer1kInput: 0.00125, costPer1kOutput: 0.01, maxTokens: 1000000, speed: 'medium', available: true },
  { provider: 'google', model: 'gemini-2.5-flash', capabilities: ['fast', 'reasoning'], costPer1kInput: 0.000075, costPer1kOutput: 0.0003, maxTokens: 1000000, speed: 'fast', available: true },

  // DeepSeek
  { provider: 'deepseek', model: 'deepseek-coder', capabilities: ['coding'], costPer1kInput: 0.00014, costPer1kOutput: 0.00028, maxTokens: 128000, speed: 'fast', available: true },
  { provider: 'deepseek', model: 'deepseek-reasoner', capabilities: ['reasoning'], costPer1kInput: 0.00055, costPer1kOutput: 0.0022, maxTokens: 64000, speed: 'medium', available: true },

  // Groq (fast inference)
  { provider: 'groq', model: 'llama-3.3-70b-versatile', capabilities: ['fast', 'coding'], costPer1kInput: 0.00059, costPer1kOutput: 0.00079, maxTokens: 128000, speed: 'fast', available: true },
  { provider: 'groq', model: 'mixtral-8x7b-32768', capabilities: ['fast'], costPer1kInput: 0.00024, costPer1kOutput: 0.00024, maxTokens: 32768, speed: 'fast', available: true },

  // OpenRouter
  { provider: 'openrouter', model: 'auto', capabilities: ['search', 'fast'], costPer1kInput: 0, costPer1kOutput: 0, maxTokens: 200000, speed: 'fast', available: true },

  // Local
  { provider: 'local', model: 'llama-3.1-8b', capabilities: ['offline', 'fast'], costPer1kInput: 0, costPer1kOutput: 0, maxTokens: 8192, speed: 'fast', available: false },
]

// ─── Intent → Capability Mapping ──────────────────────────────────────────────

const INTENT_CAPABILITY_MAP: Record<IntentType, ModelCapability[]> = {
  code: ['coding'],
  research: ['search', 'reasoning'],
  deploy: ['coding'],
  automate: ['fast'],
  search: ['search'],
  'file-operation': ['fast'],
  terminal: ['fast'],
  browser: ['vision', 'reasoning'],
  database: ['coding'],
  'memory-query': ['fast'],
  system: ['fast'],
  chat: ['reasoning'],
  unknown: ['reasoning']
}

// ─── Smart Router ─────────────────────────────────────────────────────────────

export function selectModel(intentType: IntentType, requireVision = false): ModelRoute {
  const capabilities = requireVision
    ? ['vision' as ModelCapability, ...INTENT_CAPABILITY_MAP[intentType]]
    : INTENT_CAPABILITY_MAP[intentType]

  const candidates = MODEL_REGISTRY.filter(m => m.available)

  // Score each model
  const scored = candidates.map(m => {
    let score = 0

    for (const cap of capabilities) {
      if (m.capabilities.includes(cap)) {score += 10}
    }

    // Prefer fast models for simple tasks
    if (m.speed === 'fast') {score += 2}

    if (m.speed === 'slow') {score -= 1}
    // Prefer cheaper models
    score -= m.costPer1kInput * 100

    return { model: m, score }
  })

  scored.sort((a, b) => b.score - a.score)
  const best = scored[0]

  return {
    capability: capabilities[0],
    provider: best.model.provider,
    model: best.model.model,
    priority: 1,
    available: true
  }
}

export function getModelFallbackChain(primary: ModelRoute): ModelRoute[] {
  const chain: ModelRoute[] = [primary]

  // Add fallbacks based on capability
  const fallbacks = MODEL_REGISTRY.filter(m =>
    m.available &&
    m.provider !== primary.provider &&
    m.capabilities.includes(primary.capability)
  ).sort((a, b) => a.costPer1kInput - b.costPer1kInput)

  for (const fb of fallbacks) {
    if (chain.length >= 4) {break}
    chain.push({
      capability: primary.capability,
      provider: fb.provider,
      model: fb.model,
      priority: chain.length + 1,
      available: true
    })
  }

  return chain
}

export function getModelInfo(provider: string, model: string): ModelEntry | undefined {
  return MODEL_REGISTRY.find(m => m.provider === provider && m.model === model)
}

export function listAvailableModels(): ModelEntry[] {
  return MODEL_REGISTRY.filter(m => m.available)
}

export function isModelAvailable(provider: string, model: string): boolean {
  const entry = getModelInfo(provider, model)

  return entry?.available ?? false
}
