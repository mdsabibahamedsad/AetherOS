import { describe, expect, it, vi } from 'vitest'

import { GatewaySttProvider, GatewayTtsProvider, getSttProvider, getTtsProvider, LocalTtsProvider, WebSpeechSttProvider } from '@/lib/jarvis/voice/speech'

vi.mock('@/hermes', () => ({
  transcribeAudio: vi.fn(async () => ({ ok: true, transcript: 'open chrome', provider: 'test' })),
  speakText: vi.fn(async () => ({ ok: true, data_url: 'data:audio/mpeg;base64,AAA', mime_type: 'audio/mpeg' }))
}))

describe('speech providers', () => {
  it('exposes gateway + browser STT and gateway + local TTS', () => {
    expect(getSttProvider('gateway')).toBeInstanceOf(GatewaySttProvider)
    expect(getSttProvider('webspeech')).toBeInstanceOf(WebSpeechSttProvider)
    expect(getTtsProvider('gateway')).toBeInstanceOf(GatewayTtsProvider)
    expect(getTtsProvider('local')).toBeInstanceOf(LocalTtsProvider)
  })

  it('reports honest unavailability outside a capture-capable browser', async () => {
    // jsdom has no mic capture, MediaRecorder or speechSynthesis.
    const gw = await new GatewaySttProvider().checkAvailable()
    expect(gw.ok).toBe(false)
    expect(gw.reason).toBeTruthy()

    const ws = await new WebSpeechSttProvider().checkAvailable()
    expect(ws.ok).toBe(false)

    const tts = await new LocalTtsProvider().checkAvailable()
    expect(tts.ok).toBe(false)
  })

  it('gateway TTS availability reflects audio playback support', async () => {
    // jsdom ships an Audio constructor, so playback support is reported;
    // backend synthesis failures still surface as typed errors at speak time
    // with fallback to the local voice.
    const gtts = await new GatewayTtsProvider().checkAvailable()
    expect(gtts.ok).toBe(true)
  })

  it('gateway STT throws a typed error when recording is impossible', () => {
    expect(() => new GatewaySttProvider().listen({ stream: {} as MediaStream, language: 'en-US' }))
      .toThrow()
  })
})
