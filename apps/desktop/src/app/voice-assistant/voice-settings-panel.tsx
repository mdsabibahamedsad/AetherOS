import { useStore } from '@nanostores/react'
import { useCallback } from 'react'

import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $voiceAssistant,
  enumerateMicrophones,
  enumerateSpeakers,
  setActivationMode,
  setAssistantSize,
  setNoiseSuppression,
  setPushToTalkKey,
  setSelectedMicrophoneId,
  setSelectedSpeakerId,
  setShowFloatingAssistant,
  setSttProvider,
  setTranscriptionEnabled,
  setTtsEnabled,
  setTtsProvider,
  setTtsSpeed,
  setTtsVoice,
  setVoiceActivationKeyword,
  setVoiceActivationSensitivity
} from '@/store/voice-assistant'
import type { VoiceActivationMode } from '@/store/voice-assistant'

const STT_PROVIDERS = [
  { value: 'whisper', label: 'OpenAI Whisper' },
  { value: 'whisper.cpp', label: 'Whisper.cpp' },
  { value: 'faster-whisper', label: 'Faster-Whisper' },
  { value: 'azure', label: 'Azure Speech' },
  { value: 'google', label: 'Google Speech' },
  { value: 'deepgram', label: 'Deepgram' },
  { value: 'assemblyai', label: 'AssemblyAI' },
  { value: 'custom', label: 'Custom Provider' }
]

const TTS_PROVIDERS = [
  { value: 'edge', label: 'Edge (Windows Native)' },
  { value: 'openai', label: 'OpenAI TTS' },
  { value: 'azure', label: 'Azure TTS' },
  { value: 'google', label: 'Google TTS' },
  { value: 'elevenlabs', label: 'ElevenLabs' },
  { value: 'custom', label: 'Custom Provider' }
]

const ACTIVATION_MODES: { value: VoiceActivationMode; label: string }[] = [
  { value: 'push_to_talk', label: 'Push to Talk' },
  { value: 'voice_activation', label: 'Voice Activation' },
  { value: 'always_on', label: 'Always On' },
  { value: 'disabled', label: 'Disabled' }
]

const ASSISTANT_SIZES = [
  { value: 'compact', label: 'Compact' },
  { value: 'normal', label: 'Normal' },
  { value: 'expanded', label: 'Expanded' }
]

interface VoiceSettingsPanelProps {
  onClose?: () => void
}

export function VoiceSettingsPanel({ onClose }: VoiceSettingsPanelProps) {
  const state = useStore($voiceAssistant)

  const handleScanDevices = useCallback(async () => {
    await enumerateMicrophones()
    await enumerateSpeakers()
  }, [])

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Voice Assistant</h2>
          <p className="text-sm text-(--ui-text-tertiary)">
            Configure speech recognition, synthesis, and voice interaction
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleScanDevices} size="sm" variant="outline">
            Scan Devices
          </Button>
          <Button
            onClick={() => setShowFloatingAssistant(!state.showFloatingAssistant)}
            size="sm"
            variant={state.showFloatingAssistant ? 'default' : 'outline'}
          >
            {state.showFloatingAssistant ? 'Hide Assistant' : 'Show Assistant'}
          </Button>
        </div>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Activation</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Activation Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)">How the voice assistant is triggered</div>
          </div>
          <Select onValueChange={v => setActivationMode(v as VoiceActivationMode)} value={state.activationMode}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACTIVATION_MODES.map(m => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {state.activationMode === 'push_to_talk' && (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">Push-to-Talk Key</div>
              <div className="text-xs text-(--ui-text-tertiary)">Key to hold while speaking</div>
            </div>
            <input
              className="w-24 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5 text-center text-xs font-mono outline-none focus:border-(--ui-stroke-secondary)"
              onChange={e => setPushToTalkKey(e.target.value)}
              value={state.pushToTalkKey}
            />
          </div>
        )}

        {state.activationMode === 'voice_activation' && (
          <>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Wake Word</div>
                <div className="text-xs text-(--ui-text-tertiary)">Keyword to activate listening</div>
              </div>
              <input
                className="w-40 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5 text-xs outline-none focus:border-(--ui-stroke-secondary)"
                onChange={e => setVoiceActivationKeyword(e.target.value)}
                value={state.voiceActivationKeyword}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Sensitivity</div>
                <div className="text-xs text-(--ui-text-tertiary)}">Wake word detection sensitivity</div>
              </div>
              <input
                className="w-32"
                max={1}
                min={0}
                onChange={e => setVoiceActivationSensitivity(Number(e.target.value))}
                step={0.05}
                type="range"
                value={state.voiceActivationSensitivity}
              />
            </div>
          </>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Speech-to-Text</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">STT Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Speech recognition engine</div>
          </div>
          <Select onValueChange={setSttProvider} value={state.sttProvider}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STT_PROVIDERS.map(p => (
                <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Transcription</div>
            <div className="text-xs text-(--ui-text-tertiary)">Convert speech to text</div>
          </div>
          <Switch checked={state.transcriptionEnabled} onCheckedChange={setTranscriptionEnabled} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Text-to-Speech</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">TTS Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Speech synthesis engine</div>
          </div>
          <Select onValueChange={setTtsProvider} value={state.ttsProvider}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TTS_PROVIDERS.map(p => (
                <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Speech Output</div>
            <div className="text-xs text-(--ui-text-tertiary)">Read responses aloud</div>
          </div>
          <Switch checked={state.ttsEnabled} onCheckedChange={setTtsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Voice</div>
            <div className="text-xs text-(--ui-text-tertiary)">TTS voice selection</div>
          </div>
          <Select onValueChange={setTtsVoice} value={state.ttsVoice}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default</SelectItem>
              <SelectItem value="alloy">Alloy</SelectItem>
              <SelectItem value="echo">Echo</SelectItem>
              <SelectItem value="fable">Fable</SelectItem>
              <SelectItem value="nova">Nova</SelectItem>
              <SelectItem value="shimmer">Shimmer</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Speed</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Speech rate</div>
          </div>
          <input
            className="w-32"
            max={2}
            min={0.25}
            onChange={e => setTtsSpeed(Number(e.target.value))}
            step={0.25}
            type="range"
            value={state.ttsSpeed}
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Audio Processing</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Noise Suppression</div>
            <div className="text-xs text-(--ui-text-tertiary)">Filter background noise</div>
          </div>
          <Switch
            checked={state.noiseSuppression.enabled}
            onCheckedChange={v => setNoiseSuppression({ enabled: v })}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Noise Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)">Suppression strength</div>
          </div>
          <Select
            onValueChange={v => setNoiseSuppression({ mode: v as 'standard' | 'aggressive' | 'low' })}
            value={state.noiseSuppression.mode}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="standard">Standard</SelectItem>
              <SelectItem value="aggressive">Aggressive</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Echo Cancellation</div>
            <div className="text-xs text-(--ui-text-tertiary)">Remove echo from audio input</div>
          </div>
          <Switch
            checked={state.noiseSuppression.echoCancellation}
            onCheckedChange={v => setNoiseSuppression({ echoCancellation: v })}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto Gain Control</div>
            <div className="text-xs text-(--ui-text-tertiary)">Automatically adjust microphone level</div>
          </div>
          <Switch
            checked={state.noiseSuppression.autoGainControl}
            onCheckedChange={v => setNoiseSuppression({ autoGainControl: v })}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Silence Detection</div>
            <div className="text-xs text-(--ui-text-tertiary)">Auto-stop on silence</div>
          </div>
          <Switch
            checked={state.noiseSuppression.silenceDetection}
            onCheckedChange={v => setNoiseSuppression({ silenceDetection: v })}
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Devices</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Microphone</div>
            <div className="text-xs text-(--ui-text-tertiary)">{state.microphones.length} device(s) detected</div>
          </div>
          <Select
            onValueChange={v => setSelectedMicrophoneId(v || null)}
            value={state.selectedMicrophoneId ?? ''}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="System default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">System default</SelectItem>
              {state.microphones.map(mic => (
                <SelectItem key={mic.deviceId} value={mic.deviceId}>{mic.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Speaker</div>
            <div className="text-xs text-(--ui-text-tertiary)">{state.speakers.length} device(s) detected</div>
          </div>
          <Select
            onValueChange={v => setSelectedSpeakerId(v || null)}
            value={state.selectedSpeakerId ?? ''}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="System default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">System default</SelectItem>
              {state.speakers.map(spk => (
                <SelectItem key={spk.deviceId} value={spk.deviceId}>{spk.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Assistant Display</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Assistant Size</div>
            <div className="text-xs text-(--ui-text-tertiary)">Floating assistant window size</div>
          </div>
          <Select onValueChange={v => setAssistantSize(v as 'compact' | 'normal' | 'expanded')} value={state.assistantSize}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ASSISTANT_SIZES.map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </section>
    </div>
  )
}
