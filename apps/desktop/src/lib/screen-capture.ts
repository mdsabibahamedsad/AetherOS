import { setPrivacyIndicator, setScreenCaptureState } from '@/store/multimodal'

export interface CaptureSource {
  id: string
  name: string
  type: 'screen' | 'window' | 'region'
  thumbnail?: string
}

export interface CaptureResult {
  dataUrl: string
  source: CaptureSource
  width: number
  height: number
  timestamp: number
}

let mediaStream: MediaStream | null = null

export async function getScreenSources(): Promise<CaptureSource[]> {
  const sources: CaptureSource[] = []

  try {
    if (typeof window !== 'undefined' && 'electronAPI' in window) {
      const electronSources = await (window as any).electronAPI?.getScreenSources?.()

      if (electronSources) {
        for (const s of electronSources) {
          sources.push({
            id: s.id,
            name: s.name,
            type: s.type === 'window' ? 'window' : 'screen',
            thumbnail: s.thumbnailURL
          })
        }

        return sources
      }
    }

    if (typeof navigator.mediaDevices?.getDisplayMedia === 'function') {
      sources.push({
        id: 'display',
        name: 'Entire Screen',
        type: 'screen'
      })
    }

    return sources
  } catch {
    return sources
  }
}

export async function captureScreen(source?: CaptureSource): Promise<CaptureResult | null> {
  try {
    setScreenCaptureState({ status: 'active' })
    setPrivacyIndicator({ screenActive: true })

    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: {
        displaySurface: source?.type === 'window' ? 'window' : 'monitor'
      },
      audio: false
    })

    mediaStream = stream

    const track = stream.getVideoTracks()[0]
    const settings = track.getSettings()
    const width = settings.width || 1920
    const height = settings.height || 1080

    const video = document.createElement('video')
    video.srcObject = stream
    await video.play()

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')

    if (!ctx) {
      stopScreenCapture()

      return null
    }

    ctx.drawImage(video, 0, 0)
    const dataUrl = canvas.toDataURL('image/png')

    video.pause()
    video.srcObject = null
    stopScreenCapture()

    const result: CaptureResult = {
      dataUrl,
      source: source || { id: 'display', name: 'Full Screen', type: 'screen' },
      width,
      height,
      timestamp: Date.now()
    }

    setScreenCaptureState({ lastCapture: dataUrl, status: 'idle' })

    return result
  } catch {
    setScreenCaptureState({ status: 'idle', permissionGranted: false })
    setPrivacyIndicator({ screenActive: false })

    return null
  }
}

export function stopScreenCapture() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }

  setScreenCaptureState({ status: 'idle', permissionGranted: false })
  setPrivacyIndicator({ screenActive: false })
}
