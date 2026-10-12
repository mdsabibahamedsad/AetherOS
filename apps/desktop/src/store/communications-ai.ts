import { atom } from 'nanostores'

import type { UnifiedMessage } from './communications'

export type ReplyStyle = 'professional' | 'casual' | 'friendly' | 'short' | 'detailed' | 'custom'
export type AssistantMode = 'suggest' | 'draft' | 'summarize' | 'analyze' | 'compose'

export interface DraftResult {
  content: string
  style: ReplyStyle
  toneNotes: string
  translationFrom: string
  translationTo: string
  requiresApproval: boolean
}

export interface ConversationSummary {
  summary: string
  keyPoints: string[]
  actionItems: string[]
  sentiment: string
  participants: string[]
  messageCount: number
}

export interface AssistantSuggestion {
  id: string
  text: string
  type: 'reply' | 'action' | 'insight'
  confidence: number
}

export interface CommsAIState {
  mode: AssistantMode
  draftResult: DraftResult | null
  currentSummary: ConversationSummary | null
  suggestions: AssistantSuggestion[]
  selectedStyle: ReplyStyle
  customInstructions: string
  targetLanguage: string
  loading: boolean
  history: { role: 'user' | 'assistant'; content: string; timestamp: string }[]
}

const initialState: CommsAIState = {
  mode: 'suggest',
  draftResult: null,
  currentSummary: null,
  suggestions: [],
  selectedStyle: 'professional',
  customInstructions: '',
  targetLanguage: '',
  loading: false,
  history: [],
}

export const $commsAI = atom<CommsAIState>(initialState)

const patch = (update: Partial<CommsAIState>) =>
  $commsAI.set({ ...$commsAI.get(), ...update })

export function setAssistantMode(mode: AssistantMode) { patch({ mode }) }

export function setDraftStyle(style: ReplyStyle) { patch({ selectedStyle: style }) }

export function setCustomInstructions(instructions: string) { patch({ customInstructions: instructions }) }

export function setTargetLanguage(lang: string) { patch({ targetLanguage: lang }) }

export function setAssistantLoading(loading: boolean) { patch({ loading }) }

export function generateDraft(messages: UnifiedMessage[], style: ReplyStyle = 'professional', customInstructions = '', language = '') {
  const lastMsg = messages[messages.length - 1]

  const draft: DraftResult = {
    content: generateDraftText(lastMsg?.content || '', lastMsg?.senderName || '', style, customInstructions),
    style,
    toneNotes: getToneNotes(style, customInstructions),
    translationFrom: '',
    translationTo: language,
    requiresApproval: true,
  }

  patch({ draftResult: draft, mode: 'draft', selectedStyle: style, customInstructions, targetLanguage: language })
  addHistory('assistant', `Drafted a ${style} reply: "${draft.content.substring(0, 60)}..."`)
}

export function generateSummary(messages: UnifiedMessage[]) {
  if (!messages.length) {
    patch({ currentSummary: { summary: 'No messages to summarize.', keyPoints: [], actionItems: [], sentiment: 'neutral', participants: [], messageCount: 0 } })

    return
  }

  const participants = [...new Set(messages.map(m => m.senderName))]
  const contentText = messages.map(m => m.content).join(' ')
  const keyPoints = extractKeyPoints(contentText)
  const actionItems = extractActionItems(contentText)
  const sentiment = detectSentiment(contentText)

  const summary: ConversationSummary = {
    summary: `Conversation with ${participants.join(', ')} (${messages.length} messages).${contentText.includes('?') ? ' Contains questions needing responses.' : ''}${actionItems.length ? ` ${actionItems.length} action items identified.` : ''}`,
    keyPoints,
    actionItems,
    sentiment,
    participants,
    messageCount: messages.length,
  }

  patch({ currentSummary: summary, mode: 'summarize' })
  addHistory('assistant', `Generated summary for ${messages.length} messages (${sentiment} sentiment)`)
}

export function detectPendingRequests(messages: UnifiedMessage[]): string[] {
  const patterns = [
    /(?:can|could|would|will)\s+(?:you|someone)\s+(.+?)\?/gi,
    /(?:please|pls)\s+(.+?)(?:\.|$)/gi,
    /(?:need|require|request)\s+(.+?)(?:\.|$)/gi,
  ]

  const requests: string[] = []

  for (const msg of messages) {
    for (const pattern of patterns) {
      const matches = msg.content.matchAll(pattern)

      for (const m of matches) {
        requests.push(`${m[1].trim()} — from ${msg.senderName}`)
      }
    }
  }

  return requests
}

export function classifyPriority(messages: UnifiedMessage[]): { urgent: UnifiedMessage[]; important: UnifiedMessage[]; normal: UnifiedMessage[]; spam: UnifiedMessage[] } {
  const result: { urgent: UnifiedMessage[]; important: UnifiedMessage[]; normal: UnifiedMessage[]; spam: UnifiedMessage[] } = { urgent: [], important: [], normal: [], spam: [] }

  for (const msg of messages) {
    const c = msg.content.toLowerCase()

    if (/urgent|asap|emergency|critical/i.test(c)) {result.urgent.push(msg)}
    else if (/important|deadline|required|must/i.test(c)) {result.important.push(msg)}
    else if (/spam|unsubscribe|offer|discount|free.*click/i.test(c)) {result.spam.push(msg)}
    else {result.normal.push(msg)}
  }

  return result
}

export function extractTasks(messages: UnifiedMessage[]): { task: string; from: string; messageId: string }[] {
  const tasks: { task: string; from: string; messageId: string }[] = []

  const patterns = [
    /(?:I\s+(?:will|need to|have to|must)\s+)(.+?)(?:\.|,|$)/gi,
    /(?:please|pls)\s+(.+?)(?:\.|,|$)/gi,
    /(?:action\s*item[s]?[:\s]+)(.+?)(?:\.|$)/gi,
    /(?:todo|to-do|to do)[:\s]+(.+?)(?:\.|,|$)/gi,
  ]

  for (const msg of messages) {
    for (const pattern of patterns) {
      const matches = msg.content.matchAll(pattern)

      for (const m of matches) {
        if (m[1].trim().length > 5) {
          tasks.push({ task: m[1].trim(), from: msg.senderName, messageId: msg.id })
        }
      }
    }
  }

  return tasks
}

export function addHistory(role: 'user' | 'assistant', content: string) {
  const history = $commsAI.get().history
  patch({ history: [...history, { role, content, timestamp: new Date().toISOString() }].slice(-50) })
}

export function clearAssistantHistory() {
  patch({ draftResult: null, currentSummary: null, suggestions: [], history: [] })
}

function generateDraftText(content: string, sender: string, style: ReplyStyle, custom: string): string {
  const cl = content.toLowerCase()
  const isQuestion = content.includes('?')
  const isMeeting = /meet|schedule|call|appointment/i.test(cl)
  const isUrgent = /urgent|asap|important|deadline/i.test(cl)
  const isThankYou = /thanks|thank you|appreciate/i.test(cl)

  if (style === 'short') {
    if (isQuestion) {return `Thanks for your message, ${sender}. I'll look into this and get back to you shortly.`}

    return `Got it, ${sender}. I'll take care of this.`
  }

  if (style === 'professional') {
    if (isMeeting) {return `Dear ${sender},\n\nThank you for reaching out. I would be happy to schedule a meeting. Please let me know what time works best for you.\n\nBest regards`}

    if (isUrgent) {return `Dear ${sender},\n\nThank you for bringing this to my attention. I understand the urgency and will prioritize this matter.\n\nBest regards`}

    if (isThankYou) {return `Dear ${sender},\n\nYou're welcome! Happy to help. Let me know if there's anything else I can assist with.\n\nBest regards`}

    return `Dear ${sender},\n\nThank you for your message. I will review the details and get back to you promptly.\n\nBest regards`
  }

  if (style === 'friendly') {
    if (isThankYou) {return `Hey ${sender}!\n\nYou're very welcome! Always happy to help out. Talk soon!`}

    if (isMeeting) {return `Hey ${sender}!\n\nSounds great! I'd love to meet up. Just let me know when works for you!`}

    return `Hey ${sender}!\n\nThanks for reaching out! I'll get back to you as soon as I can.`
  }

  if (style === 'casual') {
    if (isQuestion) {return `Hey ${sender},\n\nGood question! Let me check on that and get back to you.`}

    return `Hey ${sender},\n\nThanks for the message. I'll handle it!`
  }

  if (style === 'detailed') {
    const parts = [`Hello ${sender},`]

    if (isQuestion) {
      parts.push(`\n\nThank you for your detailed question. I have reviewed the information you provided and would like to address each point. I will conduct a thorough review and provide a comprehensive response.`)
    } else {
      parts.push(`\n\nThank you for reaching out. I have carefully reviewed your message and will take the appropriate actions.`)
    }

    parts.push(`\n\nPlease don't hesitate to reach out if you have any additional questions.`)
    parts.push(`\n\nBest regards`)

    return parts.join('')
  }

  return `Hi ${sender},\n\nThank you for your message. I will get back to you shortly.`
}

function getToneNotes(style: ReplyStyle, custom: string): string {
  const notes: Record<ReplyStyle, string> = {
    professional: 'Use formal language, proper salutations, and professional closing.',
    casual: 'Use conversational language, contractions, and a relaxed tone.',
    friendly: 'Use warm, personal language with positive expressions.',
    short: 'Keep response under 2-3 sentences. Direct and concise.',
    detailed: 'Provide comprehensive response with examples and context.',
    custom: 'Follow custom instructions.',
  }

  let base = notes[style] || 'Natural conversational tone.'

  if (custom) {base += ` Additional instructions: ${custom}`}

  return base
}

function extractKeyPoints(text: string): string[] {
  const points: string[] = []
  const sentences = text.split(/[.!?]+/)

  for (const s of sentences) {
    const st = s.trim()

    if (st.length > 20 && /important|key|critical|note|remember|significant|must|required/i.test(st)) {
      points.push(st)
    }
  }

  return points.slice(0, 5)
}

function extractActionItems(text: string): string[] {
  const items: string[] = []

  const patterns = [
    /(?:I\s+(?:will|need to|have to|must)\s+)(.+?)(?:\.|,|$)/gi,
    /(?:please|pls)\s+(.+?)(?:\.|,|$)/gi,
    /(?:action\s*item[s]?[:\s]+)(.+?)(?:\.|$)/gi,
    /(?:todo|to-do|to do)[:\s]+(.+?)(?:\.|$)/gi,
    /(?:don't forget|remember)\s+to\s+(.+?)(?:\.|,|$)/gi,
  ]

  for (const pattern of patterns) {
    const matches = text.matchAll(pattern)

    for (const m of matches) {
      if (m[1].trim().length > 5) {items.push(m[1].trim())}
    }
  }

  return items.slice(0, 8)
}

function detectSentiment(text: string): string {
  const positive = ['great', 'awesome', 'happy', 'thanks', 'love', 'excellent', 'perfect', 'wonderful', 'amazing', 'good']
  const negative = ['bad', 'terrible', 'awful', 'hate', 'angry', 'frustrated', 'disappointed', 'poor', 'worst', 'unacceptable']
  const tl = text.toLowerCase()
  const pos = positive.filter(w => tl.includes(w)).length
  const neg = negative.filter(w => tl.includes(w)).length

  if (pos > neg) {return 'positive'}

  if (neg > pos) {return 'negative'}

  return 'neutral'
}
