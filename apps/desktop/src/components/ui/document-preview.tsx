import { useEffect, useState } from 'react'

import { extractDocumentText, type ExtractedText, getDocumentColor, getDocumentIcon } from '@/lib/document-intelligence'
import { cn } from '@/lib/utils'

export interface DocumentPreviewProps {
  file?: File
  url?: string
  fileName: string
  mimeType: string
  fileSize?: number
  className?: string
  maxPreviewLength?: number
}

export function DocumentPreview({
  file,
  url,
  fileName,
  mimeType,
  fileSize,
  className,
  maxPreviewLength = 5000
}: DocumentPreviewProps) {
  const [extracted, setExtracted] = useState<ExtractedText | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const docColor = getDocumentColor(mimeType, fileName)
  const docIcon = getDocumentIcon(mimeType, fileName)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)

      try {
        let result: ExtractedText

        if (file) {
          result = await extractDocumentText(file, fileName)
        } else if (url) {
          const response = await fetch(url)
          const blob = await response.blob()
          result = await extractDocumentText(blob, fileName)
        } else {
          result = { text: '', confidence: 0 }
        }

        if (!cancelled) {setExtracted(result)}
      } catch {
        if (!cancelled) {setExtracted({ text: '', confidence: 0, error: 'Failed to extract' })}
      } finally {
        if (!cancelled) {setLoading(false)}
      }
    }

    load()

    return () => { cancelled = true }
  }, [file, url, fileName])

  const text = extracted?.text || ''
  const displayText = expanded ? text : text.slice(0, maxPreviewLength)
  const hasMore = text.length > maxPreviewLength

  const confidenceLabel = extracted
    ? extracted.confidence >= 0.8
      ? 'High confidence'
      : extracted.confidence >= 0.5
        ? 'Medium confidence'
        : 'Low confidence'
    : ''

  return (
    <div className={cn('flex flex-col gap-2 rounded-lg border p-3', className)}>
      <div className="flex items-center gap-2">
        <div
          className="flex h-8 w-8 items-center justify-center rounded"
          style={{ backgroundColor: `${docColor}20`, color: docColor }}
        >
          <svg fill="currentColor" height="16" viewBox="0 0 16 16" width="16">
            <path d="M4 1h5.5L13 4.5V14a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1zm5 0v3.5h3.5" />
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{fileName}</div>
          <div className="text-xs text-(--ui-text-tertiary)">
            {fileSize ? `${(fileSize / 1024).toFixed(1)} KB` : ''}
            {fileSize && mimeType ? ' · ' : ''}
            {mimeType}
            {confidenceLabel && ` · ${confidenceLabel}`}
          </div>
        </div>
        {loading && (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-(--ui-stroke-tertiary) border-t-(--ui-accent, #6366f1)" />
        )}
      </div>

      {extracted?.metadata?.note && (
        <div className="rounded bg-(--ui-warning-background, #fef3c7) px-2 py-1 text-xs text-(--ui-warning, #d97706)">
          {extracted.metadata.note}
        </div>
      )}

      {text && (
        <div className="max-h-48 overflow-y-auto rounded bg-(--ui-background-secondary) p-2">
          <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-(--ui-text-secondary)">
            {displayText}
          </pre>
          {hasMore && !expanded && (
            <button
              className="mt-1 text-xs text-(--ui-accent, #6366f1) hover:underline"
              onClick={() => setExpanded(true)}
              type="button"
            >
              Show all ({text.length.toLocaleString()} chars)
            </button>
          )}
          {expanded && hasMore && (
            <button
              className="mt-1 text-xs text-(--ui-accent, #6366f1) hover:underline"
              onClick={() => setExpanded(false)}
              type="button"
            >
              Show less
            </button>
          )}
        </div>
      )}

      {extracted?.error && (
        <div className="text-xs text-(--ui-error)">Error: {extracted.error}</div>
      )}
    </div>
  )
}
