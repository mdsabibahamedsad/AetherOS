import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { enumerateCameras } from '@/store/multimodal'
import {
  $multimodal,
  setAudioInputDeviceId,
  setAudioOutputDeviceId,
  setLocalMode,
  setPreferredVoice,
  setSttEnabled,
  setTtsEnabled,
  setVisionEnabled
} from '@/store/multimodal'

export function MultimodalSettings() {
  const state = useStore($multimodal)
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
        <h2 className="text-lg font-semibold">Multimodal Settings</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Configure voice, vision, and document processing capabilities
        </p>
      </div>

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
            <div className="text-sm font-medium">Text-to-Speech</div>
            <div className="text-xs text-(--ui-text-tertiary)">Read responses aloud</div>
          </div>
          <Switch checked={state.ttsEnabled} onCheckedChange={setTtsEnabled} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Preferred Voice</div>
            <div className="text-xs text-(--ui-text-tertiary)">TTS voice selection</div>
          </div>
          <Select
            onValueChange={setPreferredVoice}
            value={state.preferredVoice}
          >
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
            <div className="text-sm font-medium">Audio Input Device</div>
            <div className="text-xs text-(--ui-text-tertiary)">Microphone for voice input</div>
          </div>
          <Select
            onValueChange={setAudioInputDeviceId}
            value={state.audioInputDeviceId}
          >
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
          <Select
            onValueChange={setAudioOutputDeviceId}
            value={state.audioOutputDeviceId}
          >
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
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Vision</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Image Understanding</div>
            <div className="text-xs text-(--ui-text-tertiary)">Analyze images with vision models</div>
          </div>
          <Switch checked={state.visionEnabled} onCheckedChange={setVisionEnabled} />
        </div>

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
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Processing</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Local Processing Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)">
              Process audio, images, and documents locally when possible
            </div>
          </div>
          <Switch checked={state.localMode} onCheckedChange={setLocalMode} />
        </div>
      </section>
    </div>
  )
}
