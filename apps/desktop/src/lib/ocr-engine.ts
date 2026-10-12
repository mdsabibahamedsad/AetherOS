import { setOCRError, setOCRResult, setOCRStatus } from '@/store/ocr-store'
import type { OCRProviderType, OCRResult } from '@/store/ocr-store'

export interface OCRRequest {
  imageData: string
  provider?: OCRProviderType
  language?: string
  enhance?: boolean
  deskew?: boolean
  psmMode?: number
}

export async function performOCR(request: OCRRequest): Promise<OCRResult | null> {
  setOCRStatus('processing')

  try {
    const raw = await window.aetherosDesktop.api<{ success: boolean; text: string; confidence: number; language: string; pages: { pageNumber: number; text: string; confidence: number }[]; error?: string; processingTimeMs?: number; provider?: string }>({
      path: 'ocr.perform',
      body: request
    })

    if (raw?.success) {
      const result: OCRResult = {
        text: raw.text,
        confidence: raw.confidence ?? 0,
        language: raw.language ?? 'eng',
        pages: raw.pages ?? [],
        processingTimeMs: raw.processingTimeMs ?? 0,
        provider: raw.provider ?? 'unknown',
        error: raw.error
      }

      setOCRResult(result)
      setOCRStatus('success')

      return result
    }

    setOCRError(raw?.error || 'OCR failed')
    setOCRStatus('error')

    return null
  } catch (e) {
    setOCRError(String(e))
    setOCRStatus('error')

    return null
  }
}

export async function performScreenOCR(dataUrl: string): Promise<OCRResult | null> {
  return performOCR({ imageData: dataUrl, enhance: true, deskew: true })
}

export async function extractTextFromImageFile(file: File): Promise<OCRResult | null> {
  return new Promise((resolve) => {
    const reader = new FileReader()

    reader.onload = async () => {
      const result = await performOCR({ imageData: reader.result as string, enhance: true })
      resolve(result)
    }

    reader.onerror = () => {
      setOCRError('Failed to read file')
      setOCRStatus('error')
      resolve(null)
    }

    reader.readAsDataURL(file)
  })
}

export async function getSupportedLanguages(): Promise<string[]> {
  try {
    const result = await window.aetherosDesktop.api<{ languages?: string[] }>({
      path: 'ocr.languages',
      body: {}
    })

    return result?.languages || ['eng']
  } catch {
    return ['eng']
  }
}
