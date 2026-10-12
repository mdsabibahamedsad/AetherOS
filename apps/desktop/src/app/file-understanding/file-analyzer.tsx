import { useStore } from '@nanostores/react'
import { useCallback, useRef, useState } from 'react'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  $fileUnderstanding,
  addRecentAnalysis,
  setActiveAnalysis,
  setAnalyzeClipboardImages,
  setAutoAnalyzeOnDrop,
  setMaxFileSizeMB,
  setOfficeHandling,
  setPdfExtractionMethod
} from '@/store/file-understanding'
import type { DocumentType, FileAnalysisResult } from '@/store/file-understanding'

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'Word' },
  { value: 'xlsx', label: 'Excel' },
  { value: 'pptx', label: 'PowerPoint' },
  { value: 'md', label: 'Markdown' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'xml', label: 'XML' },
  { value: 'zip', label: 'ZIP' },
  { value: 'image', label: 'Images' },
  { value: 'video', label: 'Videos' },
  { value: 'audio', label: 'Audio' }
]

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {return `${bytes} B`}

  if (bytes < 1048576) {return `${(bytes / 1024).toFixed(1)} KB`}

  return `${(bytes / 1048576).toFixed(1)} MB`
}

function getTypeLabel(type: DocumentType): string {
  return DOCUMENT_TYPES.find(d => d.value === type)?.label ?? type
}

export function FileAnalyzer() {
  const state = useStore($fileUnderstanding)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleFileSelected = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) {return}
    const file = files[0]

    if (file.size > state.maxFileSizeMB * 1048576) {
      return
    }

    setAnalyzing(true)
    const startTime = Date.now()

    const result: FileAnalysisResult = {
      fileName: file.name,
      filePath: file.name,
      documentType: inferDocumentType(file.name, file.type),
      fileSizeBytes: file.size,
      textContent: await file.text().catch(() => `[Binary file: ${file.name}]`),
      metadata: {
        mimeType: file.type,
        lastModified: new Date(file.lastModified).toISOString()
      },
      processingTimeMs: Date.now() - startTime,
      status: 'done'
    }

    addRecentAnalysis(result)
    setActiveAnalysis(result)
    setAnalyzing(false)
  }, [state.maxFileSizeMB])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFileSelected(e.dataTransfer.files)
  }, [handleFileSelected])

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">File Understanding</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Analyze documents, spreadsheets, presentations, and media files
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Upload File</h3>

        <div
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
            dragOver
              ? 'border-primary bg-primary/5'
              : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
          }`}
          onClick={() => fileInputRef.current?.click()}
          onDragLeave={() => setDragOver(false)}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDrop={handleDrop}
          onKeyDown={e => { if (e.key === 'Enter') {fileInputRef.current?.click()} }}
          role="button"
          tabIndex={0}
        >
          <svg className="mb-2 size-8 text-(--ui-text-tertiary)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
          </svg>
          <p className="text-sm text-(--ui-text-secondary)">
            Drop a file here or click to browse
          </p>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">
            Supports PDF, Word, Excel, PowerPoint, Markdown, CSV, JSON, XML, images, video, audio
          </p>
          <input
            className="hidden"
            onChange={e => handleFileSelected(e.target.files)}
            ref={fileInputRef}
            type="file"
          />
        </div>
      </section>

      {analyzing && (
        <div className="flex items-center gap-2 rounded-lg bg-(--ui-bg-quaternary) px-3 py-2 text-sm text-(--ui-text-secondary)">
          <svg className="size-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" />
          </svg>
          Analyzing file...
        </div>
      )}

      {state.activeAnalysis && !analyzing && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-(--ui-text-secondary)">Analysis Result</h3>
          <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{state.activeAnalysis.fileName}</p>
                <p className="text-xs text-(--ui-text-tertiary)">
                  {getTypeLabel(state.activeAnalysis.documentType)} · {formatFileSize(state.activeAnalysis.fileSizeBytes)}
                </p>
              </div>
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                {state.activeAnalysis.processingTimeMs}ms
              </span>
            </div>
            {state.activeAnalysis.textContent && (
              <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded bg-(--ui-bg-quinary) p-2 text-xs text-(--ui-text-secondary)">
                {state.activeAnalysis.textContent.slice(0, 5000)}
                {state.activeAnalysis.textContent.length > 5000 && '...'}
              </pre>
            )}
          </div>
        </section>
      )}

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Processing</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">PDF Extraction</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Method for PDF text extraction</div>
          </div>
          <Select onValueChange={v => setPdfExtractionMethod(v as 'ocr' | 'text' | 'vision')} value={state.pdfExtractionMethod}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="text">Text</SelectItem>
              <SelectItem value="ocr">OCR</SelectItem>
              <SelectItem value="vision">Vision</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Office Documents</div>
            <div className="text-xs text-(--ui-text-tertiary)}">How .docx/.xlsx/.pptx are handled</div>
          </div>
          <Select onValueChange={v => setOfficeHandling(v as 'convert' | 'ocr' | 'vision')} value={state.officeHandling}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="convert">Convert</SelectItem>
              <SelectItem value="ocr">OCR</SelectItem>
              <SelectItem value="vision">Vision</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Auto-Analyze on Drop</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Analyze files when dropped</div>
          </div>
          <Switch checked={state.autoAnalyzeOnDrop} onCheckedChange={setAutoAnalyzeOnDrop} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Clipboard Images</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Analyze images from clipboard</div>
          </div>
          <Switch checked={state.analyzeClipboardImages} onCheckedChange={setAnalyzeClipboardImages} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Max File Size</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Maximum file size for analysis</div>
          </div>
          <Select
            onValueChange={v => setMaxFileSizeMB(Number(v))}
            value={String(state.maxFileSizeMB)}
          >
            <SelectTrigger className="w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5">5 MB</SelectItem>
              <SelectItem value="10">10 MB</SelectItem>
              <SelectItem value="25">25 MB</SelectItem>
              <SelectItem value="50">50 MB</SelectItem>
              <SelectItem value="100">100 MB</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Supported Formats</h3>
        <div className="flex flex-wrap gap-1.5">
          {DOCUMENT_TYPES.map(dt => (
            <span
              className="rounded-full bg-(--ui-background-tertiary) px-2 py-0.5 text-xs text-(--ui-text-secondary)"
              key={dt.value}
            >
              {dt.label}
            </span>
          ))}
        </div>
      </section>

      {state.recentAnalyses.length > 0 && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-medium text-(--ui-text-secondary)">Recent Analyses</h3>
          <div className="flex flex-col gap-2">
            {state.recentAnalyses.slice(0, 5).map((analysis, i) => (
              <button
                className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2 text-left transition-colors hover:bg-(--ui-bg-quaternary)"
                key={i}
                onClick={() => setActiveAnalysis(analysis)}
                type="button"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-(--ui-bg-tertiary)">
                  <svg className="size-4 text-(--ui-text-secondary)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium">{analysis.fileName}</p>
                  <p className="text-xs text-(--ui-text-tertiary)">
                    {getTypeLabel(analysis.documentType)} · {formatFileSize(analysis.fileSizeBytes)}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function inferDocumentType(fileName: string, mimeType: string): DocumentType {
  const ext = fileName.split('.').pop()?.toLowerCase()

  if (ext === 'pdf') {return 'pdf'}

  if (['doc', 'docx'].includes(ext ?? '')) {return 'docx'}

  if (['xls', 'xlsx'].includes(ext ?? '')) {return 'xlsx'}

  if (['ppt', 'pptx'].includes(ext ?? '')) {return 'pptx'}

  if (ext === 'md') {return 'md'}

  if (ext === 'csv') {return 'csv'}

  if (ext === 'json') {return 'json'}

  if (['xml', 'html', 'svg'].includes(ext ?? '')) {return 'xml'}

  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext ?? '')) {return 'zip'}

  if (mimeType.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext ?? '')) {return 'image'}

  if (mimeType.startsWith('video/') || ['mp4', 'avi', 'mkv', 'mov', 'wmv'].includes(ext ?? '')) {return 'video'}

  if (mimeType.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac', 'aac'].includes(ext ?? '')) {return 'audio'}

  return 'unknown'
}
