import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useState } from 'react'

import { type CaptureResult, captureScreen, type CaptureSource, getScreenSources, stopScreenCapture } from '@/lib/screen-capture'
import { cn } from '@/lib/utils'
import { $multimodal } from '@/store/multimodal'

import { Button } from './button'
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle } from './dialog'

export interface ScreenCaptureProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCapture: (result: CaptureResult) => void
}

export function ScreenCapture({ open, onOpenChange, onCapture }: ScreenCaptureProps) {
  const state = useStore($multimodal)
  const [sources, setSources] = useState<CaptureSource[]>([])
  const [selectedSource, setSelectedSource] = useState<CaptureSource | null>(null)
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      getScreenSources().then(setSources)
    }
  }, [open])

  const handleCapture = useCallback(async () => {
    setLoading(true)

    try {
      const result = await captureScreen(selectedSource || undefined)

      if (result) {
        setPreview(result.dataUrl)
        onCapture(result)
        onOpenChange(false)
      }
    } finally {
      setLoading(false)
    }
  }, [selectedSource, onCapture, onOpenChange])

  const handleCancel = useCallback(() => {
    stopScreenCapture()
    onOpenChange(false)
  }, [onOpenChange])

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Screen Capture</DialogTitle>
          <DialogClose />
        </DialogHeader>
        <div className="flex flex-col gap-3">
          {state.screenCapture.lastCapture && (
            <div className="mb-3 overflow-hidden rounded-lg border">
              <img
                alt="Last screen capture"
                className="h-auto w-full object-contain"
                src={state.screenCapture.lastCapture}
              />
            </div>
          )}

          {sources.length === 0 && !state.screenCapture.lastCapture && (
            <div className="flex flex-col items-center gap-2 py-8 text-(--ui-text-tertiary)">
              <svg fill="currentColor" height="32" opacity={0.4} viewBox="0 0 16 16" width="32">
                <path d="M0 2.5A1.5 1.5 0 011.5 1h13A1.5 1.5 0 0116 2.5v8a1.5 1.5 0 01-1.5 1.5H10l-.5 2H12v1H4v-1h2.5l-.5-2H1.5A1.5 1.5 0 010 10.5v-8z" />
              </svg>
              <span className="text-sm">Screen capture requires screen sharing permission</span>
              <Button onClick={handleCapture} variant="default">
                Start Capture
              </Button>
            </div>
          )}

          {sources.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {sources.map(source => (
                <button
                  className={cn(
                    'flex flex-col items-center gap-1 rounded-lg border p-2 transition-colors',
                    selectedSource?.id === source.id
                      ? 'border-(--ui-accent, #6366f1) bg-(--ui-accent-background, rgba(99,102,241,0.1))'
                      : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
                  )}
                  key={source.id}
                  onClick={() => setSelectedSource(source)}
                  type="button"
                >
                  {source.thumbnail ? (
                    <img
                      alt={source.name}
                      className="h-20 w-full rounded object-cover"
                      src={source.thumbnail}
                    />
                  ) : (
                    <div className="flex h-20 w-full items-center justify-center rounded bg-(--ui-background-secondary)">
                      <svg fill="currentColor" height="24" opacity={0.4} viewBox="0 0 16 16" width="24">
                        <path d="M0 2.5A1.5 1.5 0 011.5 1h13A1.5 1.5 0 0116 2.5v8a1.5 1.5 0 01-1.5 1.5H10l-.5 2H12v1H4v-1h2.5l-.5-2H1.5A1.5 1.5 0 010 10.5v-8z" />
                      </svg>
                    </div>
                  )}
                  <span className="truncate text-xs">{source.name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button onClick={handleCancel} variant="ghost">
            Cancel
          </Button>
          <Button
            disabled={loading || sources.length === 0}
            onClick={handleCapture}
            variant="default"
          >
            {loading ? 'Capturing...' : 'Capture'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
