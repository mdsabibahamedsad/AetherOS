import { atom } from 'nanostores'

export type VoiceActivationMode = 'push_to_talk' | 'voice_activation' | 'always_on' | 'disabled'
export type VoiceProcessingState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
export type MicrophoneState = 'unavailable' | 'available' | 'active' | 'muted' | 'error'

export interface MicrophoneDevice {
  deviceId: string
  label: string
  groupId: string
  isDefault: boolean
}

export interface SpeakerDevice {
  deviceId: string
  label: string
  groupId: string
  isDefault: boolean
}

export interface NoiseSuppressionConfig {
  enabled: boolean
  mode: 'standard' | 'aggressive' | 'low'
  echoCancellation: boolean
  autoGainControl: boolean
  silenceDetection: boolean
  silenceThreshold: number
  silenceTimeoutMs: number
}

export interface VoiceAssistantState {
  activationMode: VoiceActivationMode
  processingState: VoiceProcessingState
  microphoneState: MicrophoneState
  microphones: MicrophoneDevice[]
  selectedMicrophoneId: string | null
  speakers: SpeakerDevice[]
  selectedSpeakerId: string | null
  noiseSuppression: NoiseSuppressionConfig
  pushToTalkKey: string
  voiceActivationKeyword: string
  voiceActivationSensitivity: number
  transcriptionEnabled: boolean
  ttsEnabled: boolean
  ttsSpeed: number
  ttsVoice: string
  sttProvider: string
  ttsProvider: string
  autoRespond: boolean
  interruptEnabled: boolean
  showFloatingAssistant: boolean
  floatingAssistantPosition: { x: number; y: number }
  assistantMinimized: boolean
  assistantSize: 'compact' | 'normal' | 'expanded'
  volumeLevel: number
  isListening: boolean
  transcriptBuffer: string
  lastCommand: string | null
  error: string | null
  latency: number
}

export const $voiceAssistant = atom<VoiceAssistantState>({
  activationMode: 'push_to_talk',
  processingState: 'idle',
  microphoneState: 'unavailable',
  microphones: [],
  selectedMicrophoneId: null,
  speakers: [],
  selectedSpeakerId: null,
  noiseSuppression: {
    enabled: true,
    mode: 'standard',
    echoCancellation: true,
    autoGainControl: true,
    silenceDetection: true,
    silenceThreshold: 0.05,
    silenceTimeoutMs: 1500
  },
  pushToTalkKey: 'Space',
  voiceActivationKeyword: 'hey aether',
  voiceActivationSensitivity: 0.5,
  transcriptionEnabled: true,
  ttsEnabled: true,
  ttsSpeed: 1.0,
  ttsVoice: 'default',
  sttProvider: 'whisper',
  ttsProvider: 'edge',
  autoRespond: true,
  interruptEnabled: true,
  showFloatingAssistant: false,
  floatingAssistantPosition: { x: 80, y: 80 },
  assistantMinimized: false,
  assistantSize: 'normal',
  volumeLevel: 0,
  isListening: false,
  transcriptBuffer: '',
  lastCommand: null,
  error: null,
  latency: 0
})

const patch = (update: Partial<VoiceAssistantState>) =>
  $voiceAssistant.set({ ...$voiceAssistant.get(), ...update })

export function setActivationMode(mode: VoiceActivationMode) { patch({ activationMode: mode }) }

export function setProcessingState(state: VoiceProcessingState) { patch({ processingState: state }) }

export function setMicrophoneState(state: MicrophoneState) { patch({ microphoneState: state }) }

export function setMicrophones(mics: MicrophoneDevice[]) { patch({ microphones: mics }) }

export function setSelectedMicrophoneId(id: string | null) { patch({ selectedMicrophoneId: id }) }

export function setSpeakers(speakers: SpeakerDevice[]) { patch({ speakers }) }

export function setSelectedSpeakerId(id: string | null) { patch({ selectedSpeakerId: id }) }

export function setNoiseSuppression(config: Partial<NoiseSuppressionConfig>) {
  patch({ noiseSuppression: { ...$voiceAssistant.get().noiseSuppression, ...config } })
}

export function setPushToTalkKey(key: string) { patch({ pushToTalkKey: key }) }

export function setVoiceActivationKeyword(keyword: string) { patch({ voiceActivationKeyword: keyword }) }

export function setVoiceActivationSensitivity(s: number) { patch({ voiceActivationSensitivity: s }) }

export function setTranscriptionEnabled(e: boolean) { patch({ transcriptionEnabled: e }) }

export function setTtsEnabled(e: boolean) { patch({ ttsEnabled: e }) }

export function setTtsSpeed(s: number) { patch({ ttsSpeed: s }) }

export function setTtsVoice(v: string) { patch({ ttsVoice: v }) }

export function setSttProvider(p: string) { patch({ sttProvider: p }) }

export function setTtsProvider(p: string) { patch({ ttsProvider: p }) }

export function setAutoRespond(a: boolean) { patch({ autoRespond: a }) }

export function setInterruptEnabled(i: boolean) { patch({ interruptEnabled: i }) }

export function setShowFloatingAssistant(s: boolean) { patch({ showFloatingAssistant: s }) }

export function setFloatingAssistantPosition(p: { x: number; y: number }) { patch({ floatingAssistantPosition: p }) }

export function setAssistantMinimized(m: boolean) { patch({ assistantMinimized: m }) }

export function setAssistantSize(s: 'compact' | 'normal' | 'expanded') { patch({ assistantSize: s }) }

export function setVolumeLevel(l: number) { patch({ volumeLevel: l }) }

export function setIsListening(l: boolean) { patch({ isListening: l }) }

export function setTranscriptBuffer(t: string) { patch({ transcriptBuffer: t }) }

export function setLastCommand(c: string | null) { patch({ lastCommand: c }) }

export function setVoiceError(e: string | null) { patch({ error: e }) }

export function setLatency(l: number) { patch({ latency: l }) }

export async function enumerateMicrophones(): Promise<MicrophoneDevice[]> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()

    const mics = devices
      .filter(d => d.kind === 'audioinput')
      .map(d => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${d.deviceId.slice(0, 8)}`,
        groupId: d.groupId,
        isDefault: d.deviceId === 'default'
      }))

    setMicrophones(mics)

    return mics
  } catch { return [] }
}

export async function enumerateSpeakers(): Promise<SpeakerDevice[]> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()

    const speakers = devices
      .filter(d => d.kind === 'audiooutput')
      .map(d => ({
        deviceId: d.deviceId,
        label: d.label || `Speaker ${d.deviceId.slice(0, 8)}`,
        groupId: d.groupId,
        isDefault: d.deviceId === 'default'
      }))

    setSpeakers(speakers)

    return speakers
  } catch { return [] }
}
