import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $multimodal,
  enumerateCameras,
  setAudioInputDeviceId,
  setAudioOutputDeviceId,
  setLocalMode,
  setPreferredVoice,
  setSttEnabled,
  setTtsEnabled,
  setVisionEnabled
} from '@/store/multimodal'
import { $ocr, setOCRProvider } from '@/store/ocr-store'
import type { OCRProviderType } from '@/store/ocr-store'
import {
  setActivationMode,
  setSttProvider,
  setTtsProvider,
  setVoiceActivationKeyword
} from '@/store/voice-assistant'
import { $voiceAssistant } from '@/store/voice-assistant'

export function EnhancedMultimodalSettings() {
  const state = useStore($multimodal)
  const voice = useStore($voiceAssistant)
  const ocr = useStore($ocr)
  const [scanningCameras, setScanningCameras] = useState(false)

  const handleScanCameras = async () => {
    setScanningCameras(true)

    try {
      await enumerateCameras()
    } finally {
      setScanningCameras(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold">Enhanced Multimodal Settings</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Extended multimodal configuration for vision, voice, screen, and files
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Vision</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Image Understanding</div>
            <div className="text-xs text-(--ui-text-tertiary)">Enable vision model analysis of images</div>
          </div>
          <Switch checked={state.visionEnabled} onCheckedChange={setVisionEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Default Vision Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Primary provider for image analysis</div>
          </div>
          <Select
            onValueChange={v => {
              const r = $multimodal.get().routing
              $multimodal.set({ ...$multimodal.get(), routing: { ...r, selectedProvider: v || null } })
            }}
            value={state.routing.selectedProvider ?? ''}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Auto" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Auto</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="anthropic">Anthropic</SelectItem>
              <SelectItem value="google">Google</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Vision Model</div>
            <div className="text-xs text-(--ui-text-tertiary)">Model for image analysis tasks</div>
          </div>
          <Select
            onValueChange={v => {
              const r = $multimodal.get().routing
              $multimodal.set({ ...$multimodal.get(), routing: { ...r, selectedModelId: v || null } })
            }}
            value={state.routing.selectedModelId ?? ''}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Default</SelectItem>
              <SelectItem value="gpt-4o">GPT-4o</SelectItem>
              <SelectItem value="claude-3.5-sonnet">Claude 3.5 Sonnet</SelectItem>
              <SelectItem value="gemini-2.0-flash">Gemini 2.0 Flash</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto-Routing</div>
            <div className="text-xs text-(--ui-text-tertiary)">Automatically select best provider per task</div>
          </div>
          <Switch
            checked={state.routing.autoRouted}
            onCheckedChange={v => {
              const r = $multimodal.get().routing
              $multimodal.set({ ...$multimodal.get(), routing: { ...r, autoRouted: v } })
            }}
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Voice</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Speech-to-Text</div>
            <div className="text-xs text-(--ui-text-tertiary)">Transcribe voice input to text</div>
          </div>
          <Switch checked={state.sttEnabled} onCheckedChange={setSttEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">STT Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Speech recognition engine</div>
          </div>
          <Select onValueChange={setSttProvider} value={voice.sttProvider}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="whisper">Whisper</SelectItem>
              <SelectItem value="deepgram">Deepgram</SelectItem>
              <SelectItem value="azure">Azure</SelectItem>
              <SelectItem value="google">Google</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Text-to-Speech</div>
            <div className="text-xs text-(--ui-text-tertiary)">Read responses aloud</div>
          </div>
          <Switch checked={state.ttsEnabled} onCheckedChange={setTtsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">TTS Provider</div>
            <div className="text-xs text-(--ui-text-tertiary)">Speech synthesis engine</div>
          </div>
          <Select onValueChange={setTtsProvider} value={voice.ttsProvider}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="edge">Edge</SelectItem>
              <SelectItem value="elevenlabs">ElevenLabs</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="google">Google</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Preferred Voice</div>
            <div className="text-xs text-(--ui-text-tertiary)">TTS voice selection</div>
          </div>
          <Select onValueChange={setPreferredVoice} value={state.preferredVoice}>
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
            <div className="text-sm font-medium">Wake Word</div>
            <div className="text-xs text-(--ui-text-tertiary)">Voice activation keyword</div>
          </div>
          <input
            className="w-40 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-1.5 text-xs outline-none focus:border-(--ui-stroke-secondary)"
            onChange={e => setVoiceActivationKeyword(e.target.value)}
            value={voice.voiceActivationKeyword}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Voice Activation</div>
            <div className="text-xs text-(--ui-text-tertiary)">How voice assistant is triggered</div>
          </div>
          <Select onValueChange={v => setActivationMode(v as typeof voice.activationMode)} value={voice.activationMode}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="push_to_talk">Push to Talk</SelectItem>
              <SelectItem value="voice_activation">Voice Activation</SelectItem>
              <SelectItem value="always_on">Always On</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Screen Understanding</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto-Analyze Screenshots</div>
            <div className="text-xs text-(--ui-text-tertiary)">Automatically analyze captured screenshots</div>
          </div>
          <Switch
            checked={state.screenCapture.status !== 'idle'}
            onCheckedChange={v => {
              $multimodal.set({
                ...$multimodal.get(),
                screenCapture: { ...$multimodal.get().screenCapture, status: v ? 'selecting' : 'idle' }
              })
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Extract Text by Default</div>
            <div className="text-xs text-(--ui-text-tertiary)">Run OCR on every screenshot automatically</div>
          </div>
          <Switch
            checked={ocr.autoDetectLanguage}
            onCheckedChange={v => $ocr.set({ ...$ocr.get(), autoDetectLanguage: v })}
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">File Understanding</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">PDF Extraction Method</div>
            <div className="text-xs text-(--ui-text-tertiary)">How PDFs are processed</div>
          </div>
          <Select
            defaultValue="ocr"
            onValueChange={v => setOCRProvider(v as OCRProviderType)}
            value={ocr.provider}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tesseract">Tesseract OCR</SelectItem>
              <SelectItem value="azure">Azure Vision</SelectItem>
              <SelectItem value="google_cloud">Google Cloud Vision</SelectItem>
              <SelectItem value="aws_textract">AWS Textract</SelectItem>
              <SelectItem value="vision_llm">Vision LLM</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Office Doc Handling</div>
            <div className="text-xs text-(--ui-text-tertiary)">Processing for .docx/.xlsx/.pptx files</div>
          </div>
          <Select defaultValue="convert">
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="convert">Convert to text</SelectItem>
              <SelectItem value="ocr">OCR rendering</SelectItem>
              <SelectItem value="vision">Vision analysis</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Input & Monitoring</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Clipboard Monitoring</div>
            <div className="text-xs text-(--ui-text-tertiary)">Watch clipboard for images and content</div>
          </div>
          <Switch defaultChecked={false} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Drag & Drop Handling</div>
            <div className="text-xs text-(--ui-text-tertiary)">Process dropped files automatically</div>
          </div>
          <Switch defaultChecked />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Devices</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Cameras</div>
            <div className="text-xs text-(--ui-text-tertiary)">{state.cameras.length} device(s) detected</div>
          </div>
          <Button
            disabled={scanningCameras}
            onClick={handleScanCameras}
            variant="secondary"
          >
            {scanningCameras ? 'Scanning...' : 'Scan for Cameras'}
          </Button>
        </div>

        {state.cameras.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {state.cameras.map(camera => (
              <span
                className="rounded-full bg-(--ui-background-tertiary) px-2 py-0.5 text-xs text-(--ui-text-secondary)"
                key={camera.deviceId}
              >
                {camera.label}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Audio Input Device</div>
            <div className="text-xs text-(--ui-text-tertiary)">Microphone for voice input</div>
          </div>
          <Select onValueChange={setAudioInputDeviceId} value={state.audioInputDeviceId}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="System default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">System default</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Audio Output Device</div>
            <div className="text-xs text-(--ui-text-tertiary)">Speaker for voice responses</div>
          </div>
          <Select onValueChange={setAudioOutputDeviceId} value={state.audioOutputDeviceId}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="System default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">System default</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Processing Mode Per Modality</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Local Processing</div>
            <div className="text-xs text-(--ui-text-tertiary)">
              Process audio, images, and documents locally when possible
            </div>
          </div>
          <Switch checked={state.localMode} onCheckedChange={setLocalMode} />
        </div>

        <div className="space-y-2">
          {(['image', 'audio', 'video', 'document', 'voice'] as const).map(modality => (
            <div className="flex items-center justify-between rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) px-3 py-2" key={modality}>
              <span className="text-sm capitalize">{modality}</span>
              <Select
                onValueChange={v => {
                  const p = $multimodal.get().processing
                  $multimodal.set({
                    ...$multimodal.get(),
                    processing: { ...p, [modality]: v as 'idle' | 'processing' | 'success' | 'error' }
                  })
                }}
                value={state.processing[modality] === 'idle' ? 'auto' : state.processing[modality]}
              >
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="local">Local</SelectItem>
                  <SelectItem value="cloud">Cloud</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
