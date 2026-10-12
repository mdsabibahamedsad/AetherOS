import { useState } from 'react'

import { AudioPlayer } from '@/components/ui/audio-player'
import { DocumentPreview } from '@/components/ui/document-preview'
import { VideoPlayer } from '@/components/ui/video-player'
import { useMediaQuery } from '@/hooks/use-media-query'
import { isOfficeDocument, isTextBased } from '@/lib/document-intelligence'
import { mediaKind } from '@/lib/media'
import { cn } from '@/lib/utils'

export interface MediaAttachmentProps {
  url: string
  fileName: string
  mimeType?: string
  className?: string
}

export function MediaAttachment({ url, fileName, mimeType, className }: MediaAttachmentProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const kind = mimeType ? mediaKindByMime(mimeType, fileName) : mediaKind(fileName)

  switch (kind) {
    case 'audio':
      return (
        <AudioPlayer
          className={cn('max-w-md', className)}
          fileName={fileName}
          src={url}
        />
      )

    case 'video':
      return (
        <VideoPlayer
          className={cn('max-w-2xl', className)}
          fileName={fileName}
          src={url}
        />
      )

    case 'image':
      return (
        <a
          className={cn(
            'group relative inline-block max-w-xs overflow-hidden rounded-lg border',
            isDesktop && 'max-w-sm',
            className
          )}
          href={url}
          rel="noreferrer"
          target="_blank"
        >
          <img
            alt={fileName}
            className="h-auto w-full object-cover transition-transform group-hover:scale-105"
            src={url}
          />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 transition-opacity group-hover:opacity-100">
            <span className="text-xs text-white">{fileName}</span>
          </div>
        </a>
      )

    case 'file':
      if (mimeType && (isOfficeDocument(mimeType, fileName) || isTextBased(mimeType, fileName))) {
        return (
          <DocumentPreview
            className={cn('max-w-lg', className)}
            fileName={fileName}
            mimeType={mimeType}
            url={url}
          />
        )
      }

      return (
        <a
          className={cn(
            'flex items-center gap-2 rounded-lg border p-3 text-sm transition-colors hover:bg-(--ui-background-secondary)',
            className
          )}
          href={url}
          rel="noreferrer"
          target="_blank"
        >
          <svg className="shrink-0 text-(--ui-text-tertiary)" fill="currentColor" height="16" viewBox="0 0 16 16" width="16">
            <path d="M4 1h5.5L13 4.5V14a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1zm5 0v3.5h3.5" />
          </svg>
          <span className="min-w-0 truncate">{fileName}</span>
          <svg className="ml-auto shrink-0 text-(--ui-text-tertiary)" fill="none" height="14" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 16 16" width="14">
            <path d="M5 3l5 5-5 5" />
          </svg>
        </a>
      )

    default:
      return null
  }
}

function mediaKindByMime(mime: string, fileName: string): 'audio' | 'video' | 'image' | 'file' {
  if (mime.startsWith('audio/')) {return 'audio'}

  if (mime.startsWith('video/')) {return 'video'}

  if (mime.startsWith('image/')) {return 'image'}

  return 'file'
}

export interface AttachmentGalleryProps {
  attachments: Array<{
    url: string
    fileName: string
    mimeType?: string
  }>
  className?: string
  maxVisible?: number
}

export function AttachmentGallery({ attachments, className, maxVisible = 4 }: AttachmentGalleryProps) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? attachments : attachments.slice(0, maxVisible)
  const remaining = attachments.length - maxVisible

  const imageAttachments = visible.filter(a => {
    const kind = a.mimeType
      ? a.mimeType.startsWith('image/')
      : mediaKind(a.fileName) === 'image'

    return kind
  })

  const nonImageAttachments = visible.filter(a => {
    const kind = a.mimeType
      ? !a.mimeType.startsWith('image/')
      : mediaKind(a.fileName) !== 'image'

    return kind
  })

  if (attachments.length === 0) {return null}

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {imageAttachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {imageAttachments.map((att, i) => (
            <MediaAttachment key={`${att.fileName}-${i}`} {...att} />
          ))}
          {!showAll && remaining > 0 && (
            <button
              className="flex h-20 w-20 items-center justify-center rounded-lg border text-sm font-medium text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-background-secondary)"
              onClick={() => setShowAll(true)}
              type="button"
            >
              +{remaining}
            </button>
          )}
        </div>
      )}
      {nonImageAttachments.map((att, i) => (
        <MediaAttachment key={`${att.fileName}-${i}`} {...att} />
      ))}
    </div>
  )
}

export interface ProcessingBadgeProps {
  status: 'processing' | 'success' | 'error'
  label?: string
  className?: string
}

export function ProcessingBadge({ status, label, className }: ProcessingBadgeProps) {
  const config = {
    processing: { bg: 'bg-blue-500/10 text-blue-500', icon: 'M12 2a10 10 0 110 20 10 10 0 010-20z', spin: true },
    success: { bg: 'bg-green-500/10 text-green-500', icon: 'M10 14l4-4-4-4m-4 4h10', spin: false },
    error: { bg: 'bg-red-500/10 text-red-500', icon: 'M6 6l12 12M18 6l-12 12', spin: false }
  }[status]

  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', config.bg, className)}>
      <svg
        className={cn('h-3 w-3', config.spin && 'animate-spin')}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        viewBox="0 0 24 24"
      >
        <path d={config.icon} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label || status}
    </span>
  )
}

export interface ModelTagProps {
  modelId: string
  provider?: string
  className?: string
}

export function ModelTag({ modelId, provider, className }: ModelTagProps) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full bg-(--ui-background-tertiary) px-2 py-0.5 text-[10px] text-(--ui-text-tertiary)', className)}>
      <svg fill="currentColor" height="10" viewBox="0 0 16 16" width="10">
        <path d="M8 0a8 8 0 110 16A8 8 0 018 0zm0 2a6 6 0 100 12A6 6 0 008 2zm0 2a4 4 0 110 8 4 4 0 010-8z" />
      </svg>
      {modelId}
      {provider && <> · {provider}</>}
    </span>
  )
}
