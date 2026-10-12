import { atom } from 'nanostores'

export type CommsPlatformId =
  | 'telegram'
  | 'whatsapp'
  | 'discord'
  | 'slack'
  | 'gmail'
  | 'outlook'
  | 'teams'
  | 'signal'
  | 'sms'
  | 'webhook'
  | 'custom-rest'

export type CommsHubTab =
  | 'dashboard'
  | 'platforms'
  | 'inbox'
  | 'ai'
  | 'automation'
  | 'voice'
  | 'media'
  | 'notifications'
  | 'settings'

export type InboxFilter = 'all' | 'unread' | 'important' | 'pinned' | 'ai-only' | 'archived'

export type MessageDirection = 'incoming' | 'outgoing'
export type MessageStatus = 'sent' | 'delivered' | 'read' | 'failed'
export type VoiceProvider = 'whisper' | 'deepgram' | 'openai-voice' | 'local-stt'

export interface MessageAttachment {
  type: 'image' | 'video' | 'audio' | 'document' | 'pdf'
  url: string
  name: string
  size?: number
}

export interface UnifiedMessage {
  id: string
  platform: CommsPlatformId
  conversationId: string
  senderId: string
  senderName: string
  content: string
  timestamp: string
  direction: MessageDirection
  status: MessageStatus
  attachments: MessageAttachment[]
  aiReplied: boolean
  aiResponse: string | null
  pinned: boolean
  archived: boolean
  important: boolean
  read: boolean
  sentiment?: 'positive' | 'negative' | 'neutral'
  priority?: 'low' | 'normal' | 'high' | 'urgent'
  category?: 'general' | 'support' | 'sales' | 'meeting' | 'task' | 'spam'
}

export interface Conversation {
  id: string
  platform: CommsPlatformId
  participants: { id: string; name: string; avatar?: string }[]
  lastMessage: UnifiedMessage | null
  unreadCount: number
  pinned: boolean
  archived: boolean
  muted: boolean
  updatedAt: string
}

export interface AIConfig {
  autoReply: boolean
  smartSuggestions: boolean
  rewriteEnabled: boolean
  translateEnabled: boolean
  summarizeEnabled: boolean
  sentimentAnalysis: boolean
  priorityDetection: boolean
  spamDetection: boolean
  meetingDetection: boolean
  taskExtraction: boolean
}

export interface VoiceConfig {
  enabled: boolean
  provider: VoiceProvider
  pushToTalk: boolean
  voiceCommands: boolean
  voiceReply: boolean
}

export interface MediaConfig {
  ocrEnabled: boolean
  visionEnabled: boolean
  captionEnabled: boolean
  summarizeMedia: boolean
  autoDownload: boolean
  maxFileSize: number
}

export interface NotificationConfig {
  desktopNotifications: boolean
  soundEnabled: boolean
  silentMode: boolean
  silentModeStart: string
  silentModeEnd: string
  priorityMode: boolean
  doNotDisturb: boolean
}

export interface PlatformConnection {
  id: CommsPlatformId
  name: string
  connected: boolean
  online: boolean
  messagesToday: number
  aiReplies: number
  queued: number
  failed: number
  lastActivity: string | null
  icon: string
  color: string
}

export interface ActivityEntry {
  id: string
  type: 'message' | 'connection' | 'ai_reply' | 'error' | 'broadcast'
  platform: CommsPlatformId
  description: string
  timestamp: string
  platformName: string
}

export interface AutomationRule {
  id: string
  name: string
  platform: CommsPlatformId | 'all'
  trigger: 'message_received' | 'keyword_detected' | 'sender_match' | 'schedule'
  condition: string
  action: 'run_agent' | 'search_memory' | 'search_knowledge' | 'generate_response' | 'send_reply'
  requireApproval: boolean
  enabled: boolean
}

export interface CommsStats {
  connectedAccounts: number
  onlineStatus: number
  messagesToday: number
  aiReplies: number
  queuedMessages: number
  failedMessages: number
  automations: number
}

export interface CommsSecurity {
  encryptedTokens: boolean
  localStorage: boolean
  credentialVault: boolean
  permissionManager: boolean
  auditLog: boolean
}

export interface MediaItem {
  id: string
  platform: CommsPlatformId
  type: 'image' | 'video' | 'audio' | 'document' | 'pdf'
  url: string
  name: string
  size: number
  timestamp: string
  conversationId: string
  messageId: string
  processed: boolean
}

export interface MessageTemplate {
  id: string
  name: string
  content: string
  platform: CommsPlatformId | 'all'
  variables: string[]
  category: string
  createdAt: string
}

export interface CommunicationsState {
  activeTab: CommsHubTab
  selectedPlatform: CommsPlatformId | null
  platformConnections: PlatformConnection[]
  conversations: Conversation[]
  messages: UnifiedMessage[]
  aiConfig: AIConfig
  voiceConfig: VoiceConfig
  mediaConfig: MediaConfig
  notificationConfig: NotificationConfig
  security: CommsSecurity
  automationRules: AutomationRule[]
  activityFeed: ActivityEntry[]
  mediaItems: MediaItem[]
  templates: MessageTemplate[]
  inboxFilter: InboxFilter
  inboxSearch: string
  selectedConversation: string | null
  selectedPlatformFilter: CommsPlatformId | 'all'
  searchQuery: string
  loading: boolean
}

const DEFAULT_AI_CONFIG: AIConfig = {
  autoReply: false,
  smartSuggestions: false,
  rewriteEnabled: false,
  translateEnabled: false,
  summarizeEnabled: false,
  sentimentAnalysis: false,
  priorityDetection: false,
  spamDetection: false,
  meetingDetection: false,
  taskExtraction: false
}

const DEFAULT_VOICE_CONFIG: VoiceConfig = {
  enabled: false,
  provider: 'whisper',
  pushToTalk: true,
  voiceCommands: false,
  voiceReply: false
}

const DEFAULT_MEDIA_CONFIG: MediaConfig = {
  ocrEnabled: false,
  visionEnabled: false,
  captionEnabled: false,
  summarizeMedia: false,
  autoDownload: true,
  maxFileSize: 25000000
}

const DEFAULT_NOTIFICATION_CONFIG: NotificationConfig = {
  desktopNotifications: true,
  soundEnabled: true,
  silentMode: false,
  silentModeStart: '22:00',
  silentModeEnd: '07:00',
  priorityMode: false,
  doNotDisturb: false
}

const DEFAULT_SECURITY: CommsSecurity = {
  encryptedTokens: true,
  localStorage: true,
  credentialVault: false,
  permissionManager: false,
  auditLog: false
}

const PLATFORM_META: { id: CommsPlatformId; name: string; icon: string; color: string }[] = [
  { id: 'telegram', name: 'Telegram', icon: 'send', color: '#26A5E4' },
  { id: 'whatsapp', name: 'WhatsApp', icon: 'message-circle', color: '#25D366' },
  { id: 'discord', name: 'Discord', icon: 'message-circle', color: '#5865F2' },
  { id: 'slack', name: 'Slack', icon: 'message-square-text', color: '#4A154B' },
  { id: 'gmail', name: 'Gmail', icon: 'mail', color: '#EA4335' },
  { id: 'outlook', name: 'Outlook', icon: 'mail', color: '#0078D4' },
  { id: 'teams', name: 'Microsoft Teams', icon: 'people', color: '#6264A7' },
  { id: 'signal', name: 'Signal', icon: 'lock', color: '#3A76F0' },
  { id: 'sms', name: 'SMS Gateway', icon: 'message-square-text', color: '#F43F5E' },
  { id: 'webhook', name: 'Webhook', icon: 'link', color: '#71717A' },
  { id: 'custom-rest', name: 'Custom REST API', icon: 'terminal', color: '#64748B' }
]

const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const initialState: CommunicationsState = {
  activeTab: 'dashboard',
  selectedPlatform: null,
  platformConnections: PLATFORM_META.map(p => ({
    ...p,
    connected: false,
    online: false,
    messagesToday: 0,
    aiReplies: 0,
    queued: 0,
    failed: 0,
    lastActivity: null
  })),
  conversations: [],
  messages: [],
  aiConfig: DEFAULT_AI_CONFIG,
  voiceConfig: DEFAULT_VOICE_CONFIG,
  mediaConfig: DEFAULT_MEDIA_CONFIG,
  notificationConfig: DEFAULT_NOTIFICATION_CONFIG,
  security: DEFAULT_SECURITY,
  automationRules: [],
  activityFeed: [],
  mediaItems: [],
  templates: [],
  inboxFilter: 'all',
  inboxSearch: '',
  selectedConversation: null,
  selectedPlatformFilter: 'all',
  searchQuery: '',
  loading: false
}

export const $communications = atom<CommunicationsState>(initialState)

const patch = (update: Partial<CommunicationsState>) =>
  $communications.set({ ...$communications.get(), ...update })

export function setCommsTab(tab: CommsHubTab) { patch({ activeTab: tab }) }

export function setCommsSearch(query: string) { patch({ searchQuery: query }) }

export function setCommsLoading(loading: boolean) { patch({ loading }) }

export function setInboxFilter(filter: InboxFilter) { patch({ inboxFilter: filter }) }

export function setInboxSearch(search: string) { patch({ inboxSearch: search }) }

export function setPlatformFilter(filter: CommsPlatformId | 'all') { patch({ selectedPlatformFilter: filter }) }

export function selectConversation(id: string | null) { patch({ selectedConversation: id }) }

export function selectPlatform(id: CommsPlatformId | null) { patch({ selectedPlatform: id }) }

export function setPlatformConnection(id: CommsPlatformId, update: Partial<PlatformConnection>) {
  const connections = $communications.get().platformConnections.map(p =>
    p.id === id ? { ...p, ...update } : p
  )

  patch({ platformConnections: connections })
}

export function setPlatformStatus(id: CommsPlatformId, connected: boolean, online: boolean) {
  setPlatformConnection(id, { connected, online })
  addActivity({
    type: connected ? 'connection' : 'error',
    platform: id,
    description: `${PLATFORM_META.find(p => p.id === id)?.name ?? id} ${connected ? 'connected' : 'disconnected'}`,
    platformName: PLATFORM_META.find(p => p.id === id)?.name ?? id
  })
}

export function incrementPlatformStats(id: CommsPlatformId, field: 'messagesToday' | 'aiReplies' | 'queued' | 'failed') {
  const connection = $communications.get().platformConnections.find(p => p.id === id)

  if (connection) {
    setPlatformConnection(id, { [field]: connection[field] + 1 })
  }
}

export function updatePlatformLastActivity(id: CommsPlatformId) {
  setPlatformConnection(id, { lastActivity: new Date().toISOString() })
}

export function addActivity(entry: Omit<ActivityEntry, 'id' | 'timestamp'>) {
  const newEntry: ActivityEntry = { ...entry, id: generateId(), timestamp: new Date().toISOString() }
  const feed = $communications.get().activityFeed
  patch({ activityFeed: [newEntry, ...feed].slice(0, 100) })
}

export function clearActivity() { patch({ activityFeed: [] }) }

export function addMessage(msg: Omit<UnifiedMessage, 'id' | 'read' | 'timestamp'>) {
  const newMsg: UnifiedMessage = {
    ...msg,
    id: generateId(),
    read: false,
    timestamp: new Date().toISOString()
  }

  const messages = $communications.get().messages
  patch({ messages: [newMsg, ...messages].slice(0, 500) })
  updatePlatformLastActivity(msg.platform)
  incrementPlatformStats(msg.platform, 'messagesToday')
  addActivity({
    type: 'message',
    platform: msg.platform,
    description: `New ${msg.direction} message from ${msg.senderName}`,
    platformName: PLATFORM_META.find(p => p.id === msg.platform)?.name ?? msg.platform
  })
}

export function markMessageRead(id: string) {
  const messages = $communications.get().messages.map(m =>
    m.id === id ? { ...m, read: true } : m
  )

  patch({ messages })
}

export function markConversationRead(conversationId: string) {
  const messages = $communications.get().messages.map(m =>
    m.conversationId === conversationId ? { ...m, read: true } : m
  )

  const conversations = $communications.get().conversations.map(c =>
    c.id === conversationId ? { ...c, unreadCount: 0 } : c
  )

  patch({ messages, conversations })
}

export function togglePinMessage(id: string) {
  const messages = $communications.get().messages.map(m =>
    m.id === id ? { ...m, pinned: !m.pinned } : m
  )

  patch({ messages })
}

export function toggleImportantMessage(id: string) {
  const messages = $communications.get().messages.map(m =>
    m.id === id ? { ...m, important: !m.important } : m
  )

  patch({ messages })
}

export function archiveMessage(id: string) {
  const messages = $communications.get().messages.map(m =>
    m.id === id ? { ...m, archived: true } : m
  )

  patch({ messages })
}

export function setAIReplied(messageId: string, response: string) {
  const messages = $communications.get().messages.map(m =>
    m.id === messageId ? { ...m, aiReplied: true, aiResponse: response } : m
  )

  patch({ messages })
  const msg = messages.find(m => m.id === messageId)

  if (msg) {
    incrementPlatformStats(msg.platform, 'aiReplies')
    addActivity({
      type: 'ai_reply',
      platform: msg.platform,
      description: `AI replied to ${msg.senderName}`,
      platformName: PLATFORM_META.find(p => p.id === msg.platform)?.name ?? msg.platform
    })
  }
}

export function updateAIConfig(update: Partial<AIConfig>) {
  patch({ aiConfig: { ...$communications.get().aiConfig, ...update } })
}

export function updateVoiceConfig(update: Partial<VoiceConfig>) {
  patch({ voiceConfig: { ...$communications.get().voiceConfig, ...update } })
}

export function updateMediaConfig(update: Partial<MediaConfig>) {
  patch({ mediaConfig: { ...$communications.get().mediaConfig, ...update } })
}

export function updateNotificationConfig(update: Partial<NotificationConfig>) {
  patch({ notificationConfig: { ...$communications.get().notificationConfig, ...update } })
}

export function updateSecurity(update: Partial<CommsSecurity>) {
  patch({ security: { ...$communications.get().security, ...update } })
}

export function addAutomationRule(rule: Omit<AutomationRule, 'id'>) {
  const newRule: AutomationRule = { ...rule, id: generateId() }
  patch({ automationRules: [...$communications.get().automationRules, newRule] })
}

export function updateAutomationRule(id: string, update: Partial<AutomationRule>) {
  const rules = $communications.get().automationRules.map(r =>
    r.id === id ? { ...r, ...update } : r
  )

  patch({ automationRules: rules })
}

export function removeAutomationRule(id: string) {
  patch({ automationRules: $communications.get().automationRules.filter(r => r.id !== id) })
}

export function addConversation(conv: Omit<Conversation, 'id' | 'updatedAt'>) {
  const newConv: Conversation = { ...conv, id: generateId(), updatedAt: new Date().toISOString() }
  patch({ conversations: [...$communications.get().conversations, newConv] })
}

export function addMediaItem(item: Omit<MediaItem, 'id'>) {
  const newItem: MediaItem = { ...item, id: generateId() }
  patch({ mediaItems: [...$communications.get().mediaItems, newItem] })
}

export function addTemplate(tpl: Omit<MessageTemplate, 'id' | 'createdAt'>) {
  const newTpl: MessageTemplate = { ...tpl, id: generateId(), createdAt: new Date().toISOString() }
  patch({ templates: [...$communications.get().templates, newTpl] })
}

export function removeTemplate(id: string) {
  patch({ templates: $communications.get().templates.filter(t => t.id !== id) })
}

export function getFilteredMessages(): UnifiedMessage[] {
  const state = $communications.get()
  let msgs = state.messages
  const filter = state.inboxFilter
  const platformFilter = state.selectedPlatformFilter
  const search = state.inboxSearch.toLowerCase().trim()

  if (platformFilter !== 'all') {
    msgs = msgs.filter(m => m.platform === platformFilter)
  }

  switch (filter) {
    case 'unread': msgs = msgs.filter(m => !m.read);

 break

    case 'important': msgs = msgs.filter(m => m.important);

 break

    case 'pinned': msgs = msgs.filter(m => m.pinned);

 break

    case 'ai-only': msgs = msgs.filter(m => m.aiReplied);

 break

    case 'archived': msgs = msgs.filter(m => m.archived);

 break

    default: msgs = msgs.filter(m => !m.archived);

 break
  }

  if (search) {
    msgs = msgs.filter(m =>
      m.content.toLowerCase().includes(search) ||
      m.senderName.toLowerCase().includes(search)
    )
  }

  return msgs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}

export function getCommsStats(): CommsStats {
  const state = $communications.get()

  return {
    connectedAccounts: state.platformConnections.filter(p => p.connected).length,
    onlineStatus: state.platformConnections.filter(p => p.online).length,
    messagesToday: state.platformConnections.reduce((s, p) => s + p.messagesToday, 0),
    aiReplies: state.platformConnections.reduce((s, p) => s + p.aiReplies, 0),
    queuedMessages: state.platformConnections.reduce((s, p) => s + p.queued, 0),
    failedMessages: state.platformConnections.reduce((s, p) => s + p.failed, 0),
    automations: state.automationRules.filter(r => r.enabled).length
  }
}

export function getPlatformMeta(id: CommsPlatformId) {
  return PLATFORM_META.find(p => p.id === id)
}

export function getAllPlatformMeta() { return PLATFORM_META }
