import { atom } from 'nanostores'

import type { SttProviderId, TtsProviderId } from '@/lib/jarvis/voice/speech'

/** Voice pipeline state. The microphone is NEVER treated as active unless
 *  state is LISTENING — the UI binds its indicator strictly to this atom. */
export type VoiceState =
  | 'IDLE'
  | 'REQUESTING_PERMISSION'
  | 'LISTENING'
  | 'TRANSCRIBING'
  | 'TRANSCRIPT_READY'
  | 'PROCESSING'
  | 'EXECUTING'
  | 'SPEAKING'
  | 'ERROR'
  | 'CANCELLED'

export type MicPermission = 'granted' | 'denied' | 'restricted' | 'not-determined' | 'unknown'

export type VoiceResponseMode = 'always' | 'voice-only' | 'errors-only' | 'off'

export interface VoiceSettings {
  sttProvider: SttProviderId
  ttsProvider: TtsProviderId
  language: string
  responseMode: VoiceResponseMode
  rate: number
  volume: number
  voiceURI: string
  interruptible: boolean
  wakeWordEnabled: boolean
}

const SETTINGS_KEY = 'aetheros.jarvis.voice.v1'

const DEFAULTS: VoiceSettings = {
  sttProvider: 'gateway',
  ttsProvider: 'gateway',
  language: 'en-US',
  responseMode: 'voice-only',
  rate: 1,
  volume: 0.9,
  voiceURI: '',
  interruptible: true,
  // Wake word is an explicit opt-in. The mic is never hot unless the user
  // turns this on AND starts listening.
  wakeWordEnabled: false
}

function loadSettings(): VoiceSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)

    if (!raw) {return { ...DEFAULTS }}

    const parsed = JSON.parse(raw) as Partial<VoiceSettings>

    return {
      ...DEFAULTS,
      ...parsed,
      rate: typeof parsed.rate === 'number' ? Math.min(2, Math.max(0.5, parsed.rate)) : DEFAULTS.rate,
      volume: typeof parsed.volume === 'number' ? Math.min(1, Math.max(0, parsed.volume)) : DEFAULTS.volume,
      wakeWordEnabled: parsed.wakeWordEnabled === true
    }
  } catch {
    return { ...DEFAULTS }
  }
}

export const $voiceState = atom<VoiceState>('IDLE')
export const $micPermission = atom<MicPermission>('unknown')
export const $voiceError = atom<string | null>(null)
export const $voiceInterim = atom('')
export const $voiceSettings = atom<VoiceSettings>(loadSettings())

export function setVoiceState(state: VoiceState, error?: string | null) {
  $voiceState.set(state)
  $voiceError.set(state === 'ERROR' ? (error ?? 'Voice failed.') : null)

  if (state === 'IDLE' || state === 'LISTENING') {$voiceInterim.set('')}
}

export function setMicPermission(permission: MicPermission) {
  $micPermission.set(permission)
}

export function setVoiceInterim(text: string) {
  $voiceInterim.set(text)
}

export function updateVoiceSettings(patch: Partial<VoiceSettings>) {
  const next: VoiceSettings = {
    ...$voiceSettings.get(),
    ...patch,
    wakeWordEnabled: patch.wakeWordEnabled === undefined ? $voiceSettings.get().wakeWordEnabled : patch.wakeWordEnabled === true
  }

  $voiceSettings.set(next)

  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(next))
  } catch {
    // Private mode etc. — settings still hold in memory for this session.
  }
}

/** Active only while actually capturing. Bind mic indicators to this. */
export function isMicLive(state: VoiceState): boolean {
  return state === 'LISTENING'
}
