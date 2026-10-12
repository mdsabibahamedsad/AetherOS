/**
 * useJarvisVoice — the ONLY voice controller in Jarvis.
 *
 * Both the command composer mic button and the voice panel use this hook, so
 * voice and text share one execution path: the final transcript is submitted
 * to `submitJarvisCommand` with `inputType: 'voice'`, exactly like typed
 * text. State (IDLE → … → SPEAKING / ERROR / CANCELLED) lives in
 * `store/jarvis-voice.ts`; the mic is only "live" while LISTENING.
 *
 * Interrupt (Esc / Stop / "stop") halts recognition, speech output and the
 * running pipeline — never the application.
 */

import { useCallback, useEffect, useRef } from 'react'

import { cancelJarvisPipeline } from '@/lib/jarvis/core/ai-core'
import { type JarvisInputType, submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'
import {
  createLevelMeter,
  getSttProvider,
  getTtsProvider,
  type LevelMeter,
  type SttController,
  type TtsController
} from '@/lib/jarvis/voice/speech'
import {
  $jarvisVoiceMode,
  addJarvisCommand,
  setJarvisOrbState,
  setJarvisVoiceMode,
  setJarvisVoiceTranscript
} from '@/store/jarvis-mode'
import {
  $voiceSettings,
  $voiceState,
  setMicPermission,
  setVoiceInterim,
  setVoiceState
} from '@/store/jarvis-voice'

export interface VoiceHandle {
  /** Begin a single utterance: listen → transcribe → execute → (speak). */
  start: () => Promise<void>
  stop: () => void
  cancel: () => void
  speak: (text: string, inputType?: JarvisInputType) => Promise<void>
}

/** Live mic level for visualization. 0 unless a capture is active. */
let activeMeter: LevelMeter | null = null

export function getVoiceMicLevel(): number {
  try {
    return activeMeter?.getLevel() ?? 0
  } catch {
    return 0
  }
}

function disposeMeter() {
  try { activeMeter?.dispose() } catch { /* noop */ }
  activeMeter = null
}

async function resolveMicPermission(): Promise<boolean> {  // Platform permission first (macOS prompt lives in main).
  try {
    const granted = await window.aetherosDesktop.requestMicrophoneAccess?.()

    if (granted === false) {
      setMicPermission('denied')

      return false
    }
  } catch {
    // No main-process gate on this platform — fall through to getUserMedia.
  }

  try {
    const query = (navigator as Navigator & { permissions?: { query: (q: { name: string }) => Promise<{ state: string }> } }).permissions

    if (query) {
      const status = await query.query({ name: 'microphone' as PermissionName })

      if (status.state === 'granted') {setMicPermission('granted')}
      else if (status.state === 'denied') {
        setMicPermission('denied')

        return false
      } else {setMicPermission('not-determined')}
    }
  } catch {
    setMicPermission('unknown')
  }

  return true
}

/** Opt-in wake-word gate ("hey jarvis" / "hey aetheros").
 *  Browser-recognition only, continuous low-overhead listener that resolves
 *  with the utterance following the keyword. Never enabled by default and
 *  never silent: the UI shows the armed state while waiting. */
const WAKE_WORDS = ['hey jarvis', 'hey aetheros', 'ok jarvis']

function waitForWakeWord(language: string, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    const w = window as unknown as Record<string, unknown>

    const Ctor = (w.SpeechRecognition ?? w.webkitSpeechRecognition) as (new () => {
      lang: string; interimResults: boolean; continuous: boolean
      onresult: ((e: { results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null
      onerror: ((e: { error: string }) => void) | null
      onend: (() => void) | null
      start: () => void; stop: () => void; abort: () => void
    }) | undefined

    if (typeof Ctor !== 'function') {
      reject(new Error('Wake word needs browser speech recognition. Select it as the input provider, or turn wake word off.'))

      return
    }

    const rec = new Ctor()
    rec.lang = language
    rec.interimResults = true
    rec.continuous = true
    let settled = false

    const done = (fn: () => void) => { if (!settled) { settled = true;

 try { rec.stop() } catch { /* noop */ } fn() } }

    signal.addEventListener('abort', () => done(() => reject(new Error('Listening cancelled.'))), { once: true })

    rec.onresult = event => {
      const text = Array.from(event.results).map(r => r[0]?.transcript ?? '').join(' ').toLowerCase()
      const hit = WAKE_WORDS.find(k => text.includes(k))

      if (hit) {
        const after = text.slice(text.indexOf(hit) + hit.length).trim()
        done(() => resolve(after))
      }
    }

    rec.onerror = e => done(() => reject(new Error(`Wake-word listener failed (${e.error}).`)))

    rec.onend = () => { if (!settled) { try { rec.start() } catch { done(() => reject(new Error('Wake-word listener ended.'))) } } }

    try { rec.start() }
    catch { reject(new Error('Wake-word listener could not start.')) }
  })
}

export function useJarvisVoice(navigate: (route: string) => void): VoiceHandle {
  const sttRef = useRef<SttController | null>(null)
  const ttsRef = useRef<TtsController | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const navRef = useRef(navigate)
  navRef.current = navigate

  const stopTracks = useCallback(() => {
    disposeMeter()
    streamRef.current?.getTracks().forEach(t => {
      try { t.stop() } catch { /* already stopped */ }
    })
    streamRef.current = null
  }, [])

  const stopTts = useCallback(() => {
    try { ttsRef.current?.stop() } catch { /* already stopped */ }
    ttsRef.current = null
  }, [])

  useEffect(() => () => {
    try { sttRef.current?.cancel() } catch { /* noop */ }
    stopTts()
    stopTracks()
  }, [stopTts, stopTracks])

  const speak = useCallback(async (text: string, inputType: JarvisInputType = 'voice') => {
    const settings = $voiceSettings.get()
    const isError = text.startsWith('Error:') || text.startsWith('Blocked')

    const want =
      settings.responseMode === 'always' ||
      (settings.responseMode === 'voice-only' && inputType === 'voice') ||
      (settings.responseMode === 'errors-only' && isError)

    if (!want || settings.responseMode === 'off' || !text.trim()) {return}

    const provider = getTtsProvider(settings.ttsProvider)
    const availability = await provider.checkAvailable()

    if (!availability.ok) {
      // Honest fallback: server voice missing → local voice; both missing → text only.
      if (settings.ttsProvider !== 'local') {
        const local = getTtsProvider('local')

        if ((await local.checkAvailable()).ok) {
          return void speakWith(local, text, settings)
        }
      }

      return
    }

    return void speakWith(provider, text, settings)
  }, [])

  const start = useCallback(async () => {
    const state = $voiceState.get()

    if (state === 'LISTENING' || state === 'TRANSCRIBING' || state === 'PROCESSING' || state === 'EXECUTING') {return}

    const settings = $voiceSettings.get()
    const stt = getSttProvider(settings.sttProvider)
    const availability = await stt.checkAvailable()

    if (!availability.ok) {
      setVoiceState('ERROR', availability.reason)

      return
    }

    setVoiceState('REQUESTING_PERMISSION')
    setJarvisOrbState('listening')

    const permitted = await resolveMicPermission()

    if (!permitted) {
      setVoiceState('ERROR', 'Microphone access is disabled. Open system privacy settings and allow microphone access for AetherOS.')
      setJarvisOrbState('error')

      return
    }

    // Opt-in wake word: arm the keyword listener first. The mic IS live while
    // armed, and the UI says so ("Say hey Jarvis...").
    if (settings.wakeWordEnabled) {
      if (settings.sttProvider !== 'webspeech') {
        setVoiceState('ERROR', 'Wake word needs browser speech recognition as the input provider.')
        setJarvisOrbState('error')

        return
      }

      setVoiceState('LISTENING')
      setVoiceInterim('Say "hey Jarvis"...')
      const wakeAbort = new AbortController()
      let rejectWake!: (err: Error) => void
      const wakeDone = new Promise<string>((_, reject) => { rejectWake = reject })
      // Swallow the inevitable rejection when the listener is superseded —
      // the waitForWakeWord outcome below is authoritative.
      wakeDone.catch(() => undefined)
      sttRef.current = {
        stop: () => {
          wakeAbort.abort()
          rejectWake(new Error('Listening cancelled.'))
        },
        cancel: () => {
          wakeAbort.abort()
          rejectWake(new Error('Listening cancelled.'))
        },
        done: wakeDone
      }

      try {
        const trailing = await waitForWakeWord(settings.language, wakeAbort.signal)
        sttRef.current = null

        if (trailing) {
          // Keyword + command in one breath: submit directly, no re-capture.
          setVoiceState('TRANSCRIPT_READY')
          setJarvisVoiceTranscript(trailing)
          addJarvisCommand(trailing)
          setVoiceState('EXECUTING')
          setJarvisOrbState('thinking')

          const outcome = await submitJarvisCommand(trailing, {
            inputType: 'voice',
            deps: createDesktopCommandDeps(navRef.current),
            onResult: (text, type) => void speak(text, type)
          })

          setVoiceState('SPEAKING')
          setJarvisOrbState('speaking')
          await speak(outcome.response, 'voice')
          setVoiceState('IDLE')
          setJarvisOrbState('idle')

          return
        }
      } catch (err) {
        sttRef.current = null
        const message = err instanceof Error ? err.message : 'Wake-word listener failed.'

        if (/cancelled/i.test(message)) {
          setVoiceState('CANCELLED')
        } else {
          setVoiceState('ERROR', message)
          setJarvisOrbState('error')
        }

        setJarvisOrbState('idle')

        return
      }
    }

    let stream: MediaStream

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      disposeMeter()
      activeMeter = createLevelMeter(stream)
      setMicPermission('granted')
    } catch {
      setMicPermission('denied')
      setVoiceState('ERROR', 'Microphone access is disabled. Open system privacy settings and allow microphone access for AetherOS.')
      setJarvisOrbState('error')

      return
    }

    setVoiceState('LISTENING')
    setJarvisVoiceMode('push-to-talk')
    setJarvisOrbState('listening')

    const controller = stt.listen({
      stream,
      language: settings.language,
      onInterim: text => setVoiceInterim(text)
    })

    sttRef.current = controller

    let transcript = ''

    try {
      transcript = (await controller.done).trim()
    } catch (err) {
      stopTracks()
      const message = err instanceof Error ? err.message : 'Listening failed.'

      if (/cancelled/i.test(message)) {
        setVoiceState('CANCELLED')
      } else {
        // Latched: stays ERROR (with message) until the next start/cancel.
        setVoiceState('ERROR', message)
        setJarvisOrbState('error')
        await speak(`Error: ${message}`, 'voice')
      }

      setJarvisOrbState('idle')

      return
    }

    stopTracks()
    sttRef.current = null

    if (!transcript) {
      setVoiceState('IDLE')
      setJarvisOrbState('idle')

      return
    }

    setVoiceState('TRANSCRIPT_READY')
    setJarvisVoiceTranscript(transcript)
    addJarvisCommand(transcript)
    setVoiceState('PROCESSING')
    setJarvisOrbState('thinking')

    try {
      setVoiceState('EXECUTING')

      const outcome = await submitJarvisCommand(transcript, {
        inputType: 'voice',
        deps: createDesktopCommandDeps(navRef.current),
        onThinkingStage: (stage, label) => {
          void stage
          void label
        },
        onResult: (text, type) => void speak(text, type)
      })

      setVoiceState('SPEAKING')
      setJarvisOrbState('speaking')
      await speak(outcome.response, 'voice')
      setVoiceState('IDLE')
      setJarvisOrbState('idle')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Command failed.'
      // Latched ERROR — the message stays visible until the next command.
      setVoiceState('ERROR', message)
      setJarvisOrbState('error')
      await speak(`Error: ${message}`, 'voice')
      setJarvisOrbState('idle')
    }
  }, [speak, stopTracks])

  const stop = useCallback(() => {
    // End capture; the provider still transcribes what was recorded.
    if ($voiceState.get() === 'LISTENING') {setVoiceState('TRANSCRIBING')}

    try { sttRef.current?.stop() } catch { /* already ended */ }
  }, [])

  const cancel = useCallback(() => {
    try { sttRef.current?.cancel() } catch { /* noop */ }
    stopTts()
    stopTracks()
    cancelJarvisPipeline()

    try { window.speechSynthesis?.cancel() } catch { /* noop */ }
    setVoiceState('CANCELLED')
    setJarvisOrbState('idle')
    $jarvisVoiceMode.set('off')
  }, [stopTts, stopTracks])

  return { start, stop, cancel, speak }
}

async function speakWith(
  provider: { speak: (text: string, opts: { rate: number; volume: number; voiceURI?: string }) => TtsController },
  text: string,
  settings: { rate: number; volume: number; voiceURI: string }
): Promise<void> {
  const controller = provider.speak(text, { rate: settings.rate, volume: settings.volume, voiceURI: settings.voiceURI || undefined })

  try {
    await controller.done
  } catch {
    // Spoken result is best-effort; the text result already stands.
  }
}

// Re-exported for tests: the mic is live in exactly one state.
export function isListeningState(state: string): boolean {
  return state === 'LISTENING'
}
