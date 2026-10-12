import { renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { isListeningState, useJarvisVoice } from '@/lib/jarvis/voice/use-jarvis-voice'
import { $voiceError, $voiceState, setVoiceState } from '@/store/jarvis-voice'

vi.mock('@/lib/jarvis/core/command-gateway', () => ({
  submitJarvisCommand: vi.fn(async () => ({
    kind: 'gateway',
    capabilityId: null,
    response: 'done',
    sessionId: null,
    toolsUsed: [],
    durationMs: 0
  }))
}))

describe('voice state helpers', () => {
  it('mic is live in exactly one state', () => {
    expect(isListeningState('LISTENING')).toBe(true)

    for (const s of ['IDLE', 'TRANSCRIBING', 'SPEAKING', 'ERROR', 'CANCELLED', 'PROCESSING']) {
      expect(isListeningState(s)).toBe(false)
    }
  })
})

describe('useJarvisVoice', () => {
  beforeEach(() => setVoiceState('IDLE'))

  it('reports an honest error when capture is unavailable', async () => {
    const { result } = renderHook(() => useJarvisVoice(vi.fn()))
    await result.current.start()
    expect($voiceState.get()).toBe('ERROR')
    expect($voiceError.get()).toBeTruthy()
  })

  it('cancel parks in CANCELLED without a live capture', () => {
    const { result } = renderHook(() => useJarvisVoice(vi.fn()))
    result.current.cancel()
    expect($voiceState.get()).toBe('CANCELLED')
  })
})
