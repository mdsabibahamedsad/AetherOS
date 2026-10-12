import { atom } from 'nanostores'

export type CaptureMode = 'fullscreen' | 'window' | 'region' | 'browser-tab'
export type CaptureStatus = 'idle' | 'selecting' | 'capturing' | 'analyzing' | 'done' | 'error'

export interface CaptureResult {
  dataUrl: string
  mode: CaptureMode
  timestamp: number
  windowTitle?: string
  region?: { x: number; y: number; width: number; height: number }
  ocrText?: string
  analysis?: string
}

export interface ScreenUnderstandingState {
  captureMode: CaptureMode
  status: CaptureStatus
  lastCapture: CaptureResult | null
  captureHistory: CaptureResult[]
  ocrEnabled: boolean
  autoAnalyze: boolean
  selectedWindow: string | null
  availableWindows: { id: string; title: string; app: string }[]
  regionSelection: { x: number; y: number; width: number; height: number } | null
  askBeforeCapture: boolean
  showOverlay: boolean
  overlayPosition: { x: number; y: number }
}

export const $screenUnderstanding = atom<ScreenUnderstandingState>({
  captureMode: 'region',
  status: 'idle',
  lastCapture: null,
  captureHistory: [],
  ocrEnabled: true,
  autoAnalyze: true,
  selectedWindow: null,
  availableWindows: [],
  regionSelection: null,
  askBeforeCapture: true,
  showOverlay: false,
  overlayPosition: { x: 16, y: 16 }
})

const patch = (u: Partial<ScreenUnderstandingState>) =>
  $screenUnderstanding.set({ ...$screenUnderstanding.get(), ...u })

export function setCaptureMode(m: CaptureMode) { patch({ captureMode: m }) }

export function setCaptureStatus(s: CaptureStatus) { patch({ status: s }) }

export function setLastCapture(c: CaptureResult | null) { patch({ lastCapture: c }) }

export function addCaptureToHistory(c: CaptureResult) {
  patch({ captureHistory: [c, ...$screenUnderstanding.get().captureHistory].slice(0, 50) })
}

export function setOcrEnabled(e: boolean) { patch({ ocrEnabled: e }) }

export function setAutoAnalyze(a: boolean) { patch({ autoAnalyze: a }) }

export function setSelectedWindow(w: string | null) { patch({ selectedWindow: w }) }

export function setAvailableWindows(w: { id: string; title: string; app: string }[]) { patch({ availableWindows: w }) }

export function setRegionSelection(r: { x: number; y: number; width: number; height: number } | null) { patch({ regionSelection: r }) }

export function setAskBeforeCapture(a: boolean) { patch({ askBeforeCapture: a }) }

export function setScreenOverlayVisible(v: boolean) { patch({ showOverlay: v }) }

export function setScreenOverlayPosition(p: { x: number; y: number }) { patch({ overlayPosition: p }) }

export function resetScreenCapture() {
  patch({
    status: 'idle',
    lastCapture: null,
    regionSelection: null,
    selectedWindow: null
  })
}
