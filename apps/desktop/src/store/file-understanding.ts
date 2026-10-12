import { atom } from 'nanostores'

export type DocumentType = 'pdf' | 'docx' | 'xlsx' | 'pptx' | 'md' | 'csv' | 'json' | 'xml' | 'zip' | 'image' | 'video' | 'audio' | 'unknown'
export type ProcessingStatus = 'idle' | 'extracting' | 'analyzing' | 'done' | 'error'

export interface FileAnalysisResult {
  fileName: string
  filePath: string
  documentType: DocumentType
  fileSizeBytes: number
  pageCount?: number
  textContent?: string
  summary?: string
  metadata: Record<string, string>
  extractedImages?: string[]
  ocrResults?: { page: number; text: string }[]
  processingTimeMs: number
  status: ProcessingStatus
  error?: string
}

export interface FileUnderstandingState {
  recentAnalyses: FileAnalysisResult[]
  activeAnalysis: FileAnalysisResult | null
  pdfExtractionMethod: 'ocr' | 'text' | 'vision'
  officeHandling: 'convert' | 'ocr' | 'vision'
  autoAnalyzeOnDrop: boolean
  analyzeClipboardImages: boolean
  supportedTypes: DocumentType[]
  maxFileSizeMB: number
}

const SUPPORTED: DocumentType[] = ['pdf', 'docx', 'xlsx', 'pptx', 'md', 'csv', 'json', 'xml', 'zip', 'image', 'video', 'audio']

export const $fileUnderstanding = atom<FileUnderstandingState>({
  recentAnalyses: [],
  activeAnalysis: null,
  pdfExtractionMethod: 'ocr',
  officeHandling: 'convert',
  autoAnalyzeOnDrop: true,
  analyzeClipboardImages: true,
  supportedTypes: SUPPORTED,
  maxFileSizeMB: 50
})

const patch = (u: Partial<FileUnderstandingState>) =>
  $fileUnderstanding.set({ ...$fileUnderstanding.get(), ...u })

export function setActiveAnalysis(a: FileAnalysisResult | null) { patch({ activeAnalysis: a }) }

export function addRecentAnalysis(a: FileAnalysisResult) {
  patch({ recentAnalyses: [a, ...$fileUnderstanding.get().recentAnalyses].slice(0, 25) })
}

export function setPdfExtractionMethod(m: 'ocr' | 'text' | 'vision') { patch({ pdfExtractionMethod: m }) }

export function setOfficeHandling(h: 'convert' | 'ocr' | 'vision') { patch({ officeHandling: h }) }

export function setAutoAnalyzeOnDrop(a: boolean) { patch({ autoAnalyzeOnDrop: a }) }

export function setAnalyzeClipboardImages(a: boolean) { patch({ analyzeClipboardImages: a }) }

export function setMaxFileSizeMB(s: number) { patch({ maxFileSizeMB: s }) }

export function getDocumentTypeIcon(type: DocumentType): string {
  const icons: Record<DocumentType, string> = {
    pdf: 'file-text', docx: 'file-text', xlsx: 'table', pptx: 'presentation',
    md: 'markdown', csv: 'table', json: 'braces', xml: 'code',
    zip: 'archive', image: 'photo', video: 'video', audio: 'music',
    unknown: 'file'
  }

  return icons[type]
}
