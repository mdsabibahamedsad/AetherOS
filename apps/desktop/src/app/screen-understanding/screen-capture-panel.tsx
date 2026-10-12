import { useStore } from '@nanostores/react'
import { useCallback, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { requestPermission } from '@/store/privacy-store'
import { $privacy } from '@/store/privacy-store'
import {
  $screenUnderstanding,
  addCaptureToHistory,
  setAskBeforeCapture,
  setAutoAnalyze,
  setCaptureMode,
  setCaptureStatus,
  setLastCapture,
  setOcrEnabled,
  setScreenOverlayVisible
} from '@/store/screen-understanding'
import type { CaptureMode, CaptureResult } from '@/store/screen-understanding'

const CAPTURE_MODES: { value: CaptureMode; label: string; icon: string }[] = [
  { value: 'fullscreen', label: 'Full Screen', icon: 'M4 4h16v16H4z' },
  { value: 'window', label: 'Window', icon: 'M3 5h14v12H3z' },
  { value: 'region', label: 'Region', icon: 'M5 5h6v6H5z' },
  { value: 'browser-tab', label: 'Browser Tab', icon: 'M7 3h10v14H7z' }
]

export function ScreenCapturePanel() {
  const state = useStore($screenUnderstanding)
  const privacy = useStore($privacy)
  const [capturing, setCapturing] = useState(false)

  const handleCapture = useCallback(async () => {
    if (privacy.requireConsentForScreen && privacy.screen.state !== 'granted') {
      const granted = await requestPermission('screen')

      if (!granted) {return}
    }

    setCapturing(true)
    setCaptureStatus('capturing')

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: state.captureMode === 'window' ? 'window' :
                         state.captureMode === 'browser-tab' ? 'browser' : 'monitor'
        }
      } as MediaStreamConstraints)

      const track = stream.getVideoTracks()[0]
      const imageCapture = new (ImageCapture as any)(track)
      const bitmap = await (imageCapture as any).grabFrame()

      const canvas = document.createElement('canvas')
      canvas.width = bitmap.width
      canvas.height = bitmap.height
      const ctx = canvas.getContext('2d')

      if (!ctx) { stream.getTracks().forEach(t => t.stop());

 return }

      ctx.drawImage(bitmap, 0, 0)
      const dataUrl = canvas.toDataURL('image/png')

      stream.getTracks().forEach(t => t.stop())

      const result: CaptureResult = {
        dataUrl,
        mode: state.captureMode,
        timestamp: Date.now(),
        windowTitle: track.label || undefined
      }

      setLastCapture(result)
      addCaptureToHistory(result)
      setCaptureStatus('done')
      setScreenOverlayVisible(true)
    } catch {
      setCaptureStatus('error')
    } finally {
      setCapturing(false)
    }
  }, [state.captureMode, privacy])

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">Screen Understanding</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Capture and analyze screen content with AI
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Capture</h3>

        <div className="flex gap-2">
          {CAPTURE_MODES.map(mode => (
            <button
              className={`flex flex-1 flex-col items-center gap-1.5 rounded-lg border p-3 transition-colors ${
                state.captureMode === mode.value
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-(--ui-stroke-tertiary) text-(--ui-text-secondary) hover:border-(--ui-stroke-secondary)'
              }`}
              key={mode.value}
              onClick={() => setCaptureMode(mode.value)}
              type="button"
            >
              <svg className="size-5" fill="none" stroke="currentColor" viewBox={`0 0 24 24`}>
                <path d={mode.icon} strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
              </svg>
              <span className="text-xs font-medium">{mode.label}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Button
            disabled={capturing}
            onClick={handleCapture}
          >
            {capturing ? 'Capturing...' : 'Capture Screen'}
          </Button>
          {privacy.screen.state !== 'granted' && (
            <span className="text-xs text-(--ui-text-tertiary)">
              Screen permission required
            </span>
          )}
        </div>
      </section>

      {state.lastCapture && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-(--ui-text-secondary)">Last Capture</h3>
          <div className="overflow-hidden rounded-lg border border-(--ui-stroke-tertiary)">
            <img
              alt="Screen capture"
              className="max-h-64 w-full object-contain"
              src={state.lastCapture.dataUrl}
            />
          </div>
          {state.lastCapture.windowTitle && (
            <p className="text-xs text-(--ui-text-tertiary)">
              Window: {state.lastCapture.windowTitle}
            </p>
          )}
        </section>
      )}

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Analysis</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto-Analyze</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Analyze captures with AI automatically</div>
          </div>
          <Switch checked={state.autoAnalyze} onCheckedChange={setAutoAnalyze} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Extract Text (OCR)</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Run OCR on captured screens</div>
          </div>
          <Switch checked={state.ocrEnabled} onCheckedChange={setOcrEnabled} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Privacy</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Ask Before Capture</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Require confirmation before capturing</div>
          </div>
          <Switch checked={state.askBeforeCapture} onCheckedChange={setAskBeforeCapture} />
        </div>
      </section>

      {state.captureHistory.length > 0 && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-(--ui-text-secondary)">History</h3>
          <div className="grid grid-cols-4 gap-2">
            {state.captureHistory.slice(0, 8).map((capture, i) => (
              <button
                className="overflow-hidden rounded-lg border border-(--ui-stroke-tertiary) transition-opacity hover:opacity-80"
                key={i}
                onClick={() => setLastCapture(capture)}
                type="button"
              >
                <img alt={`Capture ${i + 1}`} className="aspect-video w-full object-cover" src={capture.dataUrl} />
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
