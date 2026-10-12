import { captureScreen, type CaptureSource } from '@/lib/screen-capture'
import { setPrivacyIndicator, setProcessingStatus } from '@/store/multimodal'

export interface ScreenAnalysisRequest {
  imageData: string
  query?: string
  mode: 'full_screen' | 'window' | 'region'
  extractText?: boolean
  explain?: boolean
  ocrOnly?: boolean
}

export interface ScreenAnalysisResult {
  description: string
  elements: { type: string; text: string; position: { x: number; y: number } }[]
  text: string
  error: string | null
  processingTimeMs: number
}

export async function captureAndAnalyzeScreen(options?: {
  source?: CaptureSource
  query?: string
  mode?: 'full_screen' | 'window' | 'region'
}): Promise<ScreenAnalysisResult | null> {
  setProcessingStatus('image', 'processing')
  setPrivacyIndicator({ screenActive: true })

  try {
    const capture = await captureScreen(options?.source)

    if (!capture) {
      setProcessingStatus('image', 'error')

      return null
    }

    const result = await analyzeScreenImage({
      imageData: capture.dataUrl,
      query: options?.query,
      mode: options?.mode || 'full_screen',
      extractText: true,
      explain: true
    })

    setProcessingStatus('image', result ? 'success' : 'error')
    setPrivacyIndicator({ screenActive: false })

    return result
  } catch {
    setProcessingStatus('image', 'error')
    setPrivacyIndicator({ screenActive: false })

    return null
  }
}

export async function analyzeScreenImage(request: ScreenAnalysisRequest): Promise<ScreenAnalysisResult | null> {
  try {
    const result = await window.aetherosDesktop.api<ScreenAnalysisResult>({
      path: 'screen.analyze',
      body: request
    })

    return result
  } catch {
    return null
  }
}

export async function extractTextFromScreen(region?: { x: number; y: number; width: number; height: number }): Promise<string | null> {
  try {
    const capture = await captureScreen()

    if (!capture) {return null}

    const result = await window.aetherosDesktop.api<{ text?: string }>({
      path: 'screen.ocr',
      body: {
        imageData: capture.dataUrl,
        region
      }
    })

    return result?.text || null
  } catch {
    return null
  }
}

export async function explainScreenElement(elementQuery: string): Promise<string | null> {
  setPrivacyIndicator({ screenActive: true })

  try {
    const capture = await captureScreen()

    if (!capture) {return null}

    const result = await window.aetherosDesktop.api<{ explanation?: string }>({
      path: 'screen.explain',
      body: {
        imageData: capture.dataUrl,
        query: elementQuery
      }
    })

    return result?.explanation || null
  } catch {
    return null
  } finally {
    setPrivacyIndicator({ screenActive: false })
  }
}
