import type { ComposerAttachment } from '@/store/composer'
import type { ModelRole } from '@/store/provider-manager'
import { $providerManager } from '@/store/provider-manager'

import { mediaKind } from './media'

export interface ModelRouteResult {
  modelId: string
  provider: string
  role: ModelRole
  confidence: number
  autoRouted: boolean
}

export interface InputTypeAnalysis {
  primaryType: InputCategory
  types: Set<InputCategory>
  requiredCapabilities: Set<string>
  hasCode: boolean
  hasImages: boolean
  hasAudio: boolean
  hasVideo: boolean
  hasDocuments: boolean
  attachmentCount: number
}

export type InputCategory = 'text' | 'code' | 'image' | 'audio' | 'video' | 'document' | 'mixed'

const MIME_TO_CATEGORY: Record<string, InputCategory> = {
  'text/': 'document',
  'application/pdf': 'document',
  'application/msword': 'document',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
  'application/vnd.ms-excel': 'document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'document',
  'application/vnd.ms-powerpoint': 'document',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'document',
  'text/csv': 'document',
  'text/plain': 'document',
  'application/rtf': 'document'
}

function extensionToCategory(path: string): InputCategory | null {
  const ext = path.split('.').pop()?.toLowerCase()

  if (!ext) {return null}

  const imgExts = new Set(['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'])
  const audioExts = new Set(['mp3', 'wav', 'ogg', 'flac', 'm4a', 'opus', 'aac'])
  const videoExts = new Set(['mp4', 'webm', 'avi', 'mov', 'mkv'])
  const docExts = new Set(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'csv', 'rtf', 'txt'])
  const codeExts = new Set(['js', 'ts', 'jsx', 'tsx', 'py', 'rb', 'go', 'rs', 'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'swift', 'kt', 'scala', 'php', 'pl', 'r', 'm', 'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'sql', 'graphql', 'html', 'css', 'scss', 'less', 'json', 'yaml', 'yml', 'xml', 'toml', 'ini', 'cfg', 'conf', 'md', 'markdown', 'tex', 'bib', 'dockerfile', 'makefile'])

  if (imgExts.has(ext)) {return 'image'}

  if (audioExts.has(ext)) {return 'audio'}

  if (videoExts.has(ext)) {return 'video'}

  if (docExts.has(ext)) {return 'document'}

  if (codeExts.has(ext)) {return 'code'}

  return null
}

export function detectInputTypes(
  text: string,
  attachments: ComposerAttachment[]
): InputTypeAnalysis {
  const types = new Set<InputCategory>()
  const requiredCapabilities = new Set<string>()

  types.add('text')

  const hasCodePattern = /```[\s\S]*?```|`[^`]+`/g

  if (hasCodePattern.test(text)) {
    types.add('code')
    requiredCapabilities.add('functionCalling')
  }

  let hasImages = false
  let hasAudio = false
  let hasVideo = false
  let hasDocuments = false

  for (const attachment of attachments) {
    const cat = extensionToCategory(attachment.path || attachment.label)
    const kind = mediaKind(attachment.path || attachment.label)

    if (attachment.kind === 'image' || kind === 'image' || cat === 'image') {
      types.add('image')
      hasImages = true
      requiredCapabilities.add('vision')
    } else if (kind === 'audio' || cat === 'audio') {
      types.add('audio')
      hasAudio = true
      requiredCapabilities.add('audio')
    } else if (kind === 'video' || cat === 'video') {
      types.add('video')
      hasVideo = true
      requiredCapabilities.add('vision')
    } else if (cat === 'document') {
      types.add('document')
      hasDocuments = true
    } else if (cat === 'code') {
      types.add('code')
      requiredCapabilities.add('functionCalling')
    }
  }

  const typeArray = [...types]

  const primaryType: InputCategory =
    typeArray.length === 1
      ? typeArray[0]
      : typeArray.length > 1
        ? 'mixed'
        : 'text'

  return {
    primaryType,
    types,
    requiredCapabilities,
    hasCode: hasCodePattern.test(text),
    hasImages,
    hasAudio,
    hasVideo,
    hasDocuments,
    attachmentCount: attachments.length
  }
}

export function bestModelForInputType(analysis: InputTypeAnalysis): ModelRouteResult {
  const state = $providerManager.get()
  const models = state.models
  const rules = state.routerRules

  if (models.length === 0) {
    return {
      modelId: '',
      provider: '',
      role: 'default',
      confidence: 0,
      autoRouted: false
    }
  }

  const requiredVision = analysis.requiredCapabilities.has('vision')
  const requiredAudio = analysis.requiredCapabilities.has('audio')
  const requiredFunctionCalling = analysis.requiredCapabilities.has('functionCalling')

  let targetRole: ModelRole = 'default'

  if (analysis.primaryType === 'image' || requiredVision) {
    targetRole = 'vision'
  } else if (analysis.primaryType === 'audio' || requiredAudio) {
    targetRole = 'speech'
  } else if (analysis.primaryType === 'code') {
    targetRole = 'coding'
  } else if (analysis.primaryType === 'document') {
    targetRole = 'long-context'
  }

  const userRule = rules.find(
    r => r.task === targetRole || (targetRole === 'vision' && r.task === 'vision')
  )

  if (userRule?.enabled && userRule.model) {
    const ruleModel = models.find(m => m.id === userRule.model)

    if (ruleModel) {
      return {
        modelId: ruleModel.id,
        provider: ruleModel.provider,
        role: targetRole,
        confidence: 0.95,
        autoRouted: true
      }
    }
  }

  const candidates = models.filter(m => {
    const roles = m.roles
    const hasTargetRole = targetRole === 'default' || roles.includes('default') || roles.includes(targetRole)

    if (requiredVision && !m.capabilities.vision) {return false}

    if (requiredAudio && !m.capabilities.audio) {return false}

    if (requiredFunctionCalling && !m.capabilities.functionCalling) {return false}

    if (!m.capabilities.streaming) {return false}

    return hasTargetRole && !m.hidden && (m.pinned || m.favorite || true)
  })

  if (candidates.length === 0) {
    const fallback = models.find(m => !m.hidden && m.capabilities.streaming)

    if (fallback) {
      return {
        modelId: fallback.id,
        provider: fallback.provider,
        role: 'default',
        confidence: 0.5,
        autoRouted: true
      }
    }

    return {
      modelId: models[0]?.id || '',
      provider: models[0]?.provider || '',
      role: 'default',
      confidence: 0.3,
      autoRouted: true
    }
  }

  candidates.sort((a, b) => {
    const aScore = (a.favorite ? 10 : 0) + (a.pinned ? 5 : 0) + (a.roles.includes(targetRole) ? 3 : 0)
    const bScore = (b.favorite ? 10 : 0) + (b.pinned ? 5 : 0) + (b.roles.includes(targetRole) ? 3 : 0)

    return bScore - aScore
  })

  const best = candidates[0]

  return {
    modelId: best.id,
    provider: best.provider,
    role: targetRole,
    confidence: best.favorite ? 0.9 : 0.7,
    autoRouted: true
  }
}

export function formatModelRouteResult(result: ModelRouteResult): string {
  if (!result.modelId) {return 'No model selected'}

  const label = result.autoRouted ? 'auto-routed' : 'manually selected'

  return `${result.modelId} (${result.provider}) — ${result.role} [${label}]`
}
