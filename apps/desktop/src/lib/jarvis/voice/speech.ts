/**
 * Jarvis speech providers (STT in, TTS out).
 *
 * Jarvis is never hard-coded to one speech vendor. Input and output each
 * have a provider abstraction with two honest implementations:
 *
 * STT:
 * - `gateway`: records the microphone with MediaRecorder and transcribes via
 *   the live backend (`POST /api/audio/transcribe` → real STT tool chain).
 *   Requires mic permission + a reachable backend with an STT provider.
 * - `webspeech`: on-device/in-browser SpeechRecognition with interim
 *   results. Requires a Chromium speech recognizer; reports unavailable
 *   with a reason when absent.
 *
 * TTS:
 * - `gateway`: synthesizes via the backend (`POST /api/audio/speak` →
 *   configured TTS chain) and plays the returned audio data URL.
 * - `local`: the OS voice via `speechSynthesis`. Always local, interruptible.
 *
 * Every provider reports honest availability first — the UI disables what is
 * missing and says why instead of silently failing.
 */

import { speakText, transcribeAudio } from '@/hermes'

export type SttProviderId = 'gateway' | 'webspeech'
export type TtsProviderId = 'gateway' | 'local'

export interface AvailabilityCheck {
  ok: boolean
  reason: string | null
}

export interface SttController {
  stop: () => void
  cancel: () => void
  done: Promise<string>
}

export interface SttProvider {
  readonly id: SttProviderId
  readonly label: string
  checkAvailable(): Promise<AvailabilityCheck>
  /**
   * Start listening. Resolves the final transcript via `done`; rejects on
   * permission denial, capture failure or transcription failure. `onInterim`
   * receives partial transcripts for live display.
   */
  listen(opts: {
    stream: MediaStream
    language: string
    onInterim?: (text: string) => void
    signal?: AbortSignal
  }): SttController
}

export interface TtsController {
  stop: () => void
  done: Promise<void>
}

export interface TtsProvider {
  readonly id: TtsProviderId
  readonly label: string
  checkAvailable(): Promise<AvailabilityCheck>
  speak(text: string, opts: { rate: number; volume: number; voiceURI?: string }): TtsController
}

export function blobToDataUrl(blob: Blob): Promise<string> {  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('Could not read the recording.'))
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : '')
    reader.readAsDataURL(blob)
  })
}

function pickMimeType(): string {
  if (typeof MediaRecorder !== 'undefined' && typeof MediaRecorder.isTypeSupported === 'function') {
    for (const mime of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']) {
      try {
        if (MediaRecorder.isTypeSupported(mime)) {return mime}
      } catch {
        // Ignore and try the next candidate.
      }
    }
  }

  return 'audio/webm'
}

/** Gateway STT: MediaRecorder capture → backend transcription (real STT). */
export class GatewaySttProvider implements SttProvider {
  readonly id: SttProviderId = 'gateway'
  readonly label = 'AetherOS voice service'

  async checkAvailable(): Promise<AvailabilityCheck> {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      return { ok: false, reason: 'This environment cannot capture microphone audio.' }
    }

    if (typeof MediaRecorder === 'undefined') {
      return { ok: false, reason: 'Audio recording is not supported in this browser.' }
    }

    return { ok: true, reason: null }
  }

  listen({ stream, onInterim, signal }: {
    stream: MediaStream
    language: string
    onInterim?: (text: string) => void
    signal?: AbortSignal
  }): SttController {
    const mimeType = pickMimeType()
    const recorder = new MediaRecorder(stream, { mimeType })
    const chunks: Blob[] = []
    let settled = false
    let rejectDone!: (err: Error) => void
    let resolveDone!: (transcript: string) => void
    const done = new Promise<string>((resolve, reject) => { resolveDone = resolve; rejectDone = reject })

    const fail = (err: Error) => {
      if (settled) {return}
      settled = true

      try { recorder.stream.getTracks().forEach(t => t.stop()) } catch { /* already stopped */ }
      rejectDone(err)
    }

    recorder.ondataavailable = event => {
      if (event.data && event.data.size > 0) {chunks.push(event.data)}
    }

    recorder.onerror = () => fail(new Error('Microphone recording failed.'))

    recorder.onstop = () => {
      if (settled) {return}
      settled = true

      if (chunks.length === 0) {
        rejectDone(new Error('No audio was captured.'))

        return
      }

      const type = recorder.mimeType || mimeType
      void blobToDataUrl(new Blob(chunks, { type })).then(
        dataUrl => transcribeAudio(dataUrl, type).then(
          res => {
            const transcript = (res.transcript ?? '').trim()

            if (!transcript) {rejectDone(new Error('Nothing was transcribed — try speaking closer to the microphone.'))}
            else {resolveDone(transcript)}
          },
          err => rejectDone(err instanceof Error ? err : new Error('Transcription failed.'))
        ),
        err => rejectDone(err instanceof Error ? err : new Error('Could not read the recording.'))
      )
    }

    signal?.addEventListener('abort', () => fail(new Error('Listening cancelled.')), { once: true })
    onInterim?.('')
    recorder.start(250)

    return {
      stop: () => {
        if (recorder.state !== 'inactive') {recorder.stop()}
      },
      cancel: () => fail(new Error('Listening cancelled.')),
      done
    }
  }
}

interface WebSpeechRecognitionInstance {
  lang: string
  interimResults: boolean
  continuous: boolean
  maxAlternatives: number
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

type WebSpeechCtor = new () => WebSpeechRecognitionInstance

function getWebSpeechCtor(): WebSpeechCtor | null {
  if (typeof window === 'undefined') {return null}
  const w = window as unknown as Record<string, unknown>
  const ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition

  return (typeof ctor === 'function' ? ctor : null) as WebSpeechCtor | null
}

/** Browser STT: SpeechRecognition with interim results (real recognizer). */
export class WebSpeechSttProvider implements SttProvider {
  readonly id: SttProviderId = 'webspeech'
  readonly label = 'Browser speech recognition'

  async checkAvailable(): Promise<AvailabilityCheck> {
    if (!getWebSpeechCtor()) {
      return { ok: false, reason: 'Browser speech recognition is not available here. Use the AetherOS voice service.' }
    }

    return { ok: true, reason: null }
  }

  listen({ language, onInterim, signal }: {
    stream: MediaStream
    language: string
    onInterim?: (text: string) => void
    signal?: AbortSignal
  }): SttController {
    void signal
    const Ctor = getWebSpeechCtor()

    if (!Ctor) {throw new Error('Browser speech recognition is not available.')}

    const rec = new Ctor()
    rec.lang = language
    rec.interimResults = true
    rec.continuous = false
    rec.maxAlternatives = 1

    let settled = false
    let rejectDone!: (err: Error) => void
    let resolveDone!: (transcript: string) => void
    const done = new Promise<string>((resolve, reject) => { resolveDone = resolve; rejectDone = reject })
    let finalText = ''

    const fail = (err: Error) => {
      if (settled) {return}
      settled = true

      try { rec.abort() } catch { /* already ended */ }
      rejectDone(err)
    }

    rec.onresult = event => {
      let interim = ''

      for (const result of Array.from(event.results)) {
        const alt = result[0]

        if (!alt) {continue}

        if (result.isFinal) {finalText += alt.transcript}
        else {interim += alt.transcript}
      }

      onInterim?.((finalText + interim).trim())
    }

    rec.onerror = event => fail(new Error(event.error === 'not-allowed' ? 'Microphone access was denied.' : `Recognition failed (${event.error}).`))

    rec.onend = () => {
      if (settled) {return}
      settled = true
      const text = finalText.trim()

      if (text) {resolveDone(text)}
      else {rejectDone(new Error('Nothing was recognized.'))}
    }

    rec.start()

    return {
      stop: () => {
        try { rec.stop() } catch { /* already ended */ }
      },
      cancel: () => fail(new Error('Listening cancelled.')),
      done
    }
  }
}

/** Local TTS: OS voice via speechSynthesis (real, interruptible). */
export class LocalTtsProvider implements TtsProvider {
  readonly id: TtsProviderId = 'local'
  readonly label = 'System voice'

  async checkAvailable(): Promise<AvailabilityCheck> {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      return { ok: false, reason: 'System speech synthesis is not available here.' }
    }

    return { ok: true, reason: null }
  }

  speak(text: string, opts: { rate: number; volume: number; voiceURI?: string }): TtsController {
    const synth = window.speechSynthesis
    synth.cancel()

    let resolveDone!: () => void
    let rejectDone!: (err: Error) => void
    const done = new Promise<void>((resolve, reject) => { resolveDone = resolve; rejectDone = reject })

    const utter = new SpeechSynthesisUtterance(text.slice(0, 1000))
    utter.rate = Math.min(2, Math.max(0.5, opts.rate))
    utter.volume = Math.min(1, Math.max(0, opts.volume))

    if (opts.voiceURI) {
      const voice = synth.getVoices().find(v => v.voiceURI === opts.voiceURI)

      if (voice) {utter.voice = voice}
    }

    utter.onend = () => resolveDone()
    utter.onerror = () => rejectDone(new Error('Speech playback failed.'))
    synth.speak(utter)

    return {
      stop: () => {
        synth.cancel()
        resolveDone()
      },
      done
    }
  }
}

/** Gateway TTS: backend synthesis chain → data-URL audio playback (real). */
export class GatewayTtsProvider implements TtsProvider {
  readonly id: TtsProviderId = 'gateway'
  readonly label = 'AetherOS voice service'

  async checkAvailable(): Promise<AvailabilityCheck> {
    if (typeof Audio === 'undefined') {
      return { ok: false, reason: 'Audio playback is not available here.' }
    }

    return { ok: true, reason: null }
  }

  speak(text: string, opts: { rate: number; volume: number; voiceURI?: string }): TtsController {
    void opts
    const audio = new Audio()
    let stopped = false
    let rejectDone!: (err: Error) => void
    let resolveDone!: () => void
    const done = new Promise<void>((resolve, reject) => { resolveDone = resolve; rejectDone = reject })

    audio.onended = () => resolveDone()

    audio.onerror = () => {
      if (!stopped) {rejectDone(new Error('Voice playback failed.'))}
    }

    void speakText(text.slice(0, 1000)).then(
      res => {
        if (stopped) {return}

        if (!res.ok || !res.data_url.startsWith('data:audio')) {
          rejectDone(new Error('Voice synthesis returned no audio.'))

          return
        }

        audio.src = res.data_url
        void audio.play().catch(() => rejectDone(new Error('Voice playback was blocked.')))
      },
      err => rejectDone(err instanceof Error ? err : new Error('Voice synthesis failed.'))
    )

    return {
      stop: () => {
        stopped = true

        try { audio.pause() } catch { /* not playing */ }
        resolveDone()
      },
      done
    }
  }
}

export const STT_PROVIDERS: SttProvider[] = [new GatewaySttProvider(), new WebSpeechSttProvider()]
export const TTS_PROVIDERS: TtsProvider[] = [new GatewayTtsProvider(), new LocalTtsProvider()]

export function getSttProvider(id: SttProviderId): SttProvider {
  return STT_PROVIDERS.find(p => p.id === id) ?? STT_PROVIDERS[0]
}

export function getTtsProvider(id: TtsProviderId): TtsProvider {
  return TTS_PROVIDERS.find(p => p.id === id) ?? TTS_PROVIDERS[0]
}

export interface LevelMeter {
  /** Current input level 0..1 from live mic analysis. 0 when unavailable. */
  getLevel: () => number
  dispose: () => void
}

/**
 * Real microphone level meter for voice visualization. Returns 0 when the
 * Web Audio path is unavailable — the UI must render an idle state then,
 * never a fake animated waveform.
 */
export function createLevelMeter(stream: MediaStream): LevelMeter {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext

    if (!Ctx) {return { getLevel: () => 0, dispose: () => undefined }}

    const ctx = new Ctx()
    const source = ctx.createMediaStreamSource(stream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)
    const data = new Uint8Array(analyser.frequencyBinCount)
    let disposed = false

    return {
      getLevel: () => {
        if (disposed) {return 0}

        try {
          analyser.getByteTimeDomainData(data)
          let sum = 0

          for (let i = 0; i < data.length; i++) {
            const v = (data[i] - 128) / 128
            sum += v * v
          }

          return Math.min(1, Math.sqrt(sum / data.length) * 3)
        } catch {
          return 0
        }
      },
      dispose: () => {
        disposed = true

        try { source.disconnect() } catch { /* noop */ }
        void ctx.close().catch(() => undefined)
      }
    }
  } catch {
    return { getLevel: () => 0, dispose: () => undefined }
  }
}
