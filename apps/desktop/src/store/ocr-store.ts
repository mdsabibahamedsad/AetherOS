import { atom } from 'nanostores'

export type OCRProviderType = 'tesseract' | 'windows_ocr' | 'azure' | 'google_cloud' | 'aws_textract' | 'vision_llm'
export type OCRStatus = 'idle' | 'processing' | 'success' | 'error'

export interface OCRResult {
  text: string
  confidence: number
  language: string
  pages: { pageNumber: number; text: string; confidence: number }[]
  processingTimeMs: number
  provider: string
  error?: string
  blocks?: { text: string; bbox: { x: number; y: number; width: number; height: number } }[]
}

export interface OCRState {
  provider: OCRProviderType
  language: string
  supportedLanguages: string[]
  status: OCRStatus
  lastResult: OCRResult | null
  autoDetectLanguage: boolean
  enhanceImage: boolean
  deskewImage: boolean
  psmMode: number
  confidenceThreshold: number
  error: string | null
}

export const $ocr = atom<OCRState>({
  provider: 'tesseract',
  language: 'eng',
  supportedLanguages: ['eng'],
  status: 'idle',
  lastResult: null,
  autoDetectLanguage: true,
  enhanceImage: true,
  deskewImage: true,
  psmMode: 3,
  confidenceThreshold: 0.0,
  error: null
})

const patch = (u: Partial<OCRState>) => $ocr.set({ ...$ocr.get(), ...u })

export function setOCRProvider(p: OCRProviderType) { patch({ provider: p }) }

export function setOCRLanguage(l: string) { patch({ language: l }) }

export function setSupportedLanguages(l: string[]) { patch({ supportedLanguages: l }) }

export function setOCRStatus(s: OCRStatus) { patch({ status: s }) }

export function setOCRResult(r: OCRResult | null) { patch({ lastResult: r }) }

export function setAutoDetectLanguage(a: boolean) { patch({ autoDetectLanguage: a }) }

export function setEnhanceImage(e: boolean) { patch({ enhanceImage: e }) }

export function setDeskewImage(d: boolean) { patch({ deskewImage: d }) }

export function setPsmMode(p: number) { patch({ psmMode: p }) }

export function setConfidenceThreshold(c: number) { patch({ confidenceThreshold: c }) }

export function setOCRError(e: string | null) { patch({ error: e }) }
