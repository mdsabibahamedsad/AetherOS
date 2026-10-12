import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApprovalRequiredError, JarvisBusyError, matchLocalIntent, submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import type { LocalExecDeps } from '@/lib/jarvis/os/local-executor'
import { isJarvisExecutingState, resetJarvisExecution, setJarvisExecution } from '@/store/jarvis-mode'

vi.mock('@/lib/jarvis/core/ai-core', () => ({
  executePipeline: vi.fn(async (input: string) => ({
    plan: { status: 'completed', steps: [], intent: { type: 'chat' } },
    response: `agent says: ${input}`,
    artifacts: [],
    memoryUpdates: [],
    reflection: null,
    suggestions: [],
    modelUsed: { provider: 'gateway', model: 'default' }
  }))
}))

vi.mock('@/store/gateway', () => ({
  activeGateway: () => ({ connectionState: 'open' })
}))

vi.mock('@/hermes', () => ({
  getGlobalModelInfo: async () => ({ provider: 'p', model: 'm' }),
  getGlobalModelOptions: async () => ({ providers: [{ slug: 'p' }] }),
  setGlobalModel: async (provider: string, model: string) => ({ ok: true, provider, model })
}))

function deps(overrides: Partial<LocalExecDeps> = {}): LocalExecDeps {
  return {
    openExternal: vi.fn(async () => undefined),
    copyText: vi.fn(async () => undefined),
    notify: vi.fn(),
    navigate: vi.fn(),
    getSystemStats: vi.fn(async () => ({ cpu: 10, memory: { used: 1024, total: 8192, percent: 12 }, uptime: 60 })),
    screenshot: vi.fn(async () => 'data:image/png;base64,AAA'),
    ...overrides
  }
}

describe('matchLocalIntent', () => {
  it('routes exit phrasing locally', () => {
    for (const text of ['exit jarvis', 'exit jarvis mode', 'go back', 'return home', 'go home', 'leave jarvis']) {
      const m = matchLocalIntent(text)
      expect(m?.input.route).toBe('/')
    }
  })

  it('routes in-app navigation locally', () => {
    expect(matchLocalIntent('open memory')?.input.route).toBe('/memory')
    expect(matchLocalIntent('go to agents')?.input.route).toBe('/agents')
    expect(matchLocalIntent('show me security center')?.input.route).toBe('/security')
  })

  it('routes exact allowlisted app opens locally', () => {
    expect(matchLocalIntent('open chrome')).toMatchObject({ handler: 'os.launch-app', input: { appId: 'chrome' } })
    expect(matchLocalIntent('open vs code')).toMatchObject({ input: { appId: 'vscode' } })
  })

  it('sends compound or unknown commands to the gateway', () => {
    expect(matchLocalIntent('open chrome and search for docs')).toBeNull()
    expect(matchLocalIntent('open evil-app')).toBeNull()
    expect(matchLocalIntent('research agent frameworks')).toBeNull()
  })

  it('routes exact https URL opens locally', () => {
    expect(matchLocalIntent('open https://example.com/x')).toMatchObject({ handler: 'os.open-url' })
  })
})

describe('submitJarvisCommand', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetJarvisExecution()
  })

  it('classifies in-flight vs settled execution states', () => {
    for (const s of ['SUBMITTED', 'PARSING', 'PLANNING', 'EXECUTING', 'STREAMING'] as const) {
      expect(isJarvisExecutingState(s)).toBe(true)
    }

    for (const s of ['IDLE', 'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT', 'UNAVAILABLE', 'AWAITING_PERMISSION'] as const) {
      expect(isJarvisExecutingState(s)).toBe(false)
    }
  })

  it('executes local navigation without the gateway', async () => {
    const d = deps()
    const out = await submitJarvisCommand('exit jarvis mode', { inputType: 'text', deps: d })
    expect(out.kind).toBe('local')
    expect(d.navigate).toHaveBeenCalledWith('/')
  })

  it('launches allowlisted apps locally', async () => {
    const d = deps()
    const out = await submitJarvisCommand('open youtube', { inputType: 'voice', deps: d })
    expect(out.kind).toBe('local')
    expect(d.openExternal).toHaveBeenCalledWith('https://www.youtube.com/')
  })

  it('sends free-form commands to the gateway pipeline', async () => {
    const { executePipeline } = await import('@/lib/jarvis/core/ai-core')
    const onResult = vi.fn()
    const out = await submitJarvisCommand('research agent frameworks', { inputType: 'text', deps: deps(), onResult })
    expect(out.kind).toBe('gateway')
    expect(executePipeline).toHaveBeenCalled()
    expect(onResult).toHaveBeenCalledWith(expect.stringContaining('agent says'), 'text')
  })

  it('requires approval for destructive phrasing on both channels', async () => {
    const { executePipeline } = await import('@/lib/jarvis/core/ai-core')

    for (const inputType of ['text', 'voice'] as const) {
      await expect(submitJarvisCommand('delete all 24 files', { inputType, deps: deps() }))
        .rejects.toBeInstanceOf(ApprovalRequiredError)
    }

    expect(executePipeline).not.toHaveBeenCalled()

    // Allow once proceeds to the pipeline.
    const out = await submitJarvisCommand('delete all 24 files', { inputType: 'text', deps: deps(), approved: true })
    expect(out.kind).toBe('gateway')
  })

  it('rejects empty commands', async () => {
    await expect(submitJarvisCommand('   ', { inputType: 'text', deps: deps() })).rejects.toThrow(/empty/i)
  })

  it('rejects a duplicate submit while a pipeline is in flight', async () => {
    const { executePipeline } = await import('@/lib/jarvis/core/ai-core')
    setJarvisExecution({ state: 'EXECUTING' })

    await expect(submitJarvisCommand('research agent frameworks', { inputType: 'text', deps: deps() }))
      .rejects.toBeInstanceOf(JarvisBusyError)
    expect(executePipeline).not.toHaveBeenCalled()
  })

  it('still allows exit/navigation while a pipeline is in flight', async () => {
    const d = deps()
    setJarvisExecution({ state: 'STREAMING' })
    const out = await submitJarvisCommand('exit jarvis', { inputType: 'text', deps: d })
    expect(out.kind).toBe('local')
    expect(d.navigate).toHaveBeenCalledWith('/')
  })

  it('lets an explicit Allow-once resubmit through mid-flight', async () => {
    setJarvisExecution({ state: 'EXECUTING' })
    const out = await submitJarvisCommand('delete all 24 files', { inputType: 'text', deps: deps(), approved: true })
    expect(out.kind).toBe('gateway')
  })
})
