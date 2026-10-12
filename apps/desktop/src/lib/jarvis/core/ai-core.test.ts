import { describe, expect, it, vi } from 'vitest'

import { analyzeIntent, executePipeline, GatewayUnavailableError } from '@/lib/jarvis/core/ai-core'

vi.mock('@/store/gateway', () => ({
  activeGateway: () => null
}))

describe('analyzeIntent', () => {
  it('is deterministic — same input, same type and confidence', () => {
    const a = analyzeIntent('browse to https://example.com and fetch the page')
    const b = analyzeIntent('browse to https://example.com and fetch the page')
    expect(a.type).toBe(b.type)
    expect(a.confidence).toBe(b.confidence)
    expect(a.type).toBe('browser')
  })

  it('falls back to chat for plain conversation', () => {
    expect(analyzeIntent('hello, how are you today?').type).toBe('chat')
  })
})

describe('executePipeline without gateway', () => {
  it('reports UNAVAILABLE instead of fake success', async () => {
    await expect(
      executePipeline(
        'open chrome',
        () => undefined,
        () => undefined
      )
    ).rejects.toBeInstanceOf(GatewayUnavailableError)
  })
})
