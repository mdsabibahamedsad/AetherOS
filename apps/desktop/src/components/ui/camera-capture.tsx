import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
import { captureCameraFrame, openCamera, resetCamera, setSelectedCameraId } from '@/store/multimodal'
import { $multimodal, enumerateCameras } from '@/store/multimodal'

import { Button } from './button'
import { Codicon } from './codicon'
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle } from './dialog'

export interface CameraCaptureProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCapture: (dataUrl: string) => void
}

export function CameraCapture({ open, onOpenChange, onCapture }: CameraCaptureProps) {
  const state = useStore($multimodal)
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      enumerateCameras()
      openCamera(state.selectedCameraId || undefined).catch(e => setError(String(e)))
    } else {
      resetCamera()
      setError(null)
    }
  }, [open, state.selectedCameraId])

  useEffect(() => {
    if (videoRef.current && state.cameraStream) {
      videoRef.current.srcObject = state.cameraStream
    }
  }, [state.cameraStream])

  const handleCapture = useCallback(() => {
    const dataUrl = captureCameraFrame()

    if (dataUrl && state.cameraStream) {
      onCapture(dataUrl)
      onOpenChange(false)
    } else {
      setError('Failed to capture camera frame')
    }
  }, [onCapture, onOpenChange, state.cameraStream])

  const handleSwitchCamera = useCallback(async () => {
    if (state.cameras.length < 2) {return}
    const currentIndex = state.cameras.findIndex(c => c.deviceId === state.selectedCameraId)
    const nextIndex = (currentIndex + 1) % state.cameras.length
    const nextCamera = state.cameras[nextIndex]

    if (nextCamera) {
      resetCamera()
      setSelectedCameraId(nextCamera.deviceId)
      await openCamera(nextCamera.deviceId)
    }
  }, [state.cameras, state.selectedCameraId])

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Camera Capture</DialogTitle>
          <DialogClose />
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-black">
            {state.cameraStatus === 'opening' && (
              <div className="flex flex-col items-center gap-2 text-white/60">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                <span className="text-xs">Opening camera...</span>
              </div>
            )}

            {state.cameraStatus === 'error' && (
              <div className="flex flex-col items-center gap-2 text-red-400">
                <Codicon name="error" size="1.5rem" />
                <span className="text-sm">Camera access denied or unavailable</span>
              </div>
            )}

            {state.cameraStatus === 'active' && (
              <video
                autoPlay
                className="h-full w-full object-cover"
                muted
                playsInline
                ref={videoRef}
              />
            )}

            <div className="absolute inset-x-0 bottom-2 flex items-center justify-center gap-2">
              {state.cameras.length > 1 && (
                <button
                  className="rounded-full bg-black/50 p-2 text-white/80 backdrop-blur-sm hover:text-white"
                  onClick={handleSwitchCamera}
                  type="button"
                >
                  <svg fill="currentColor" height="16" viewBox="0 0 16 16" width="16">
                    <path d="M10 3L7 1v2H4a1 1 0 00-1 1v5l2-2V4.5h2v2L10 3zM6 13l3 2v-2h3a1 1 0 001-1V7l-2 2v2.5H8v-2L6 13z" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-2 rounded bg-(--ui-error-background, #fef2f2) px-2 py-1 text-xs text-(--ui-error)">
              {error}
            </div>
          )}

          {state.cameras.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {state.cameras.map(camera => (
                <button
                  className={cn(
                    'rounded-full px-2 py-0.5 text-xs transition-colors',
                    camera.deviceId === state.selectedCameraId
                      ? 'bg-(--ui-accent, #6366f1) text-white'
                      : 'bg-(--ui-stroke-tertiary) text-(--ui-text-tertiary) hover:bg-(--ui-stroke-secondary)'
                  )}
                  key={camera.deviceId}
                  onClick={() => {
                    resetCamera()
                    setSelectedCameraId(camera.deviceId)
                    openCamera(camera.deviceId)
                  }}
                  type="button"
                >
                  {camera.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} variant="ghost">
            Cancel
          </Button>
          <Button
            disabled={state.cameraStatus !== 'active'}
            onClick={handleCapture}
            variant="default"
          >
            Capture Photo
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
