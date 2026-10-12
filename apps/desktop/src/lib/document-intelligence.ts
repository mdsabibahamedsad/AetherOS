export interface DocumentInfo {
  fileName: string
  fileSize: number
  mimeType: string
  pageCount?: number
  textContent?: string
  error?: string
}

export interface ExtractedText {
  text: string
  confidence: number
  error?: string
  pages?: { pageNumber: number; text: string }[]
  metadata?: Record<string, string>
}

const TEXT_MIME_TYPES = new Set([
  'text/plain',
  'text/markdown',
  'text/csv',
  'text/html',
  'text/xml',
  'application/json',
  'application/xml',
  'text/yaml',
  'text/x-yaml',
  'text/toml',
  'text/x-java-source',
  'text/x-python',
  'text/x-typescript',
  'text/x-javascript',
  'text/css',
  'text/x-scss',
  'text/x-less',
  'text/x-sh',
  'text/x-bat',
  'text/x-ps1',
  'text/x-sql'
])

export function isTextBased(mimeType: string, fileName: string): boolean {
  if (TEXT_MIME_TYPES.has(mimeType)) {return true}
  const ext = fileName.split('.').pop()?.toLowerCase()

  const textExts = new Set([
    'txt', 'md', 'markdown', 'csv', 'tsv', 'json', 'xml', 'yaml', 'yml',
    'toml', 'ini', 'cfg', 'conf', 'log', 'env', 'gitignore', 'dockerfile',
    'js', 'ts', 'jsx', 'tsx', 'py', 'rb', 'go', 'rs', 'java', 'c', 'cpp',
    'h', 'hpp', 'cs', 'swift', 'kt', 'scala', 'php', 'pl', 'r', 'm',
    'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'sql', 'html', 'css',
    'scss', 'less', 'tex', 'bib', 'makefile'
  ])

  return textExts.has(ext || '')
}

export function isOfficeDocument(mimeType: string, fileName: string): boolean {
  const officeMimes = new Set([
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/rtf'
  ])

  if (officeMimes.has(mimeType)) {return true}
  const ext = fileName.split('.').pop()?.toLowerCase()

  return ext ? ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'rtf'].includes(ext) : false
}

export function estimatePageCount(fileSizeBytes: number, mimeType: string): number {
  if (mimeType === 'application/pdf') {
    return Math.max(1, Math.round(fileSizeBytes / 15000))
  }

  const textPages = Math.max(1, Math.round(fileSizeBytes / 3000))

  return textPages
}

export async function extractDocumentText(
  file: File | Blob,
  fileName: string
): Promise<ExtractedText> {
  const mimeType = file.type || 'application/octet-stream'

  if (isTextBased(mimeType, fileName)) {
    try {
      const text = await file.text()

      return {
        text,
        confidence: 1.0,
        pages: [{ pageNumber: 1, text }],
        metadata: { source: fileName, type: 'text' }
      }
    } catch (e) {
      return { text: '', confidence: 0, metadata: { error: String(e) } }
    }
  }

  if (mimeType === 'application/pdf' || fileName.endsWith('.pdf')) {
    try {
      const text = await file.text()

      if (text && text.length > 50) {
        const cleaned = text
          .replace(/<<[\s\S]*?>>/g, '')
          .replace(/\/[\w.]+\s*<<[\s\S]*?>>/g, '')
          .replace(/endobj|endstream|stream|obj|\d+ \d+ obj|\d+ \d+ endobj/g, '')
          .replace(/\n{3,}/g, '\n\n')
          .trim()

        if (cleaned.length > 100) {
          return {
            text: cleaned,
            confidence: 0.7,
            metadata: { source: fileName, type: 'pdf', note: 'Basic text extraction' }
          }
        }
      }
    } catch {
      // Fall through to extraction note
    }

    return {
      text: `[Document: ${fileName} — PDF, ${Math.round(file.size / 1024)} KB]`,
      confidence: 0.3,
      metadata: { source: fileName, type: 'pdf', note: 'Full extraction requires PDF parser' }
    }
  }

  if (isOfficeDocument(mimeType, fileName)) {
    const ext = fileName.split('.').pop()?.toUpperCase() || 'DOC'

    return {
      text: `[Document: ${fileName} — ${ext}, ${Math.round(file.size / 1024)} KB]`,
      confidence: 0.3,
      metadata: { source: fileName, type: ext.toLowerCase(), note: 'Full extraction requires backend service' }
    }
  }

  return {
    text: `[File: ${fileName} — ${(file.size / 1024).toFixed(1)} KB]`,
    confidence: 0.1,
    metadata: { source: fileName, type: 'unknown' }
  }
}

export async function extractDocumentTextByPath(path: string): Promise<ExtractedText> {
  try {
    const response = await fetch(path)
    const blob = await response.blob()
    const fileName = path.split('/').pop() || path.split('\\').pop() || 'document'

    return extractDocumentText(blob, fileName)
  } catch {
    return {
      text: `[Document: ${path}]`,
      confidence: 0.1,
      metadata: { error: 'Could not read file' }
    }
  }
}

export function getDocumentIcon(mimeType: string, fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase()

  const icons: Record<string, string> = {
    pdf: 'file-pdf',
    doc: 'file-word',
    docx: 'file-word',
    xls: 'file-excel',
    xlsx: 'file-excel',
    ppt: 'file-pptx',
    pptx: 'file-pptx',
    txt: 'file-text',
    csv: 'file-csv',
    json: 'file-code',
    xml: 'file-code',
    md: 'file-markdown',
    rtf: 'file-text',
    html: 'file-code',
    htm: 'file-code'
  }

  return icons[ext || ''] || 'file'
}

export function getDocumentColor(mimeType: string, fileName: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase()

  const colors: Record<string, string> = {
    pdf: '#e74c3c',
    doc: '#2b579a',
    docx: '#2b579a',
    xls: '#217346',
    xlsx: '#217346',
    ppt: '#d04526',
    pptx: '#d04526'
  }

  return colors[ext || ''] || '#6b7280'
}
