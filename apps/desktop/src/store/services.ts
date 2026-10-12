import { atom } from 'nanostores'

export type ServiceCategory = 'messaging' | 'automation' | 'storage' | 'developer-tools' | 'productivity' | 'ai-models'

export interface ConnectorCatalogEntry {
  id: string
  name: string
  description: string
  category: ServiceCategory
  icon: string
  color: string
  docsUrl: string
  setupGuide: string
  popular: boolean
  beta?: boolean
  authType: 'token' | 'oauth' | 'webhook' | 'none'
}

export interface ConnectedServiceInfo {
  id: string
  name: string
  description: string
  category: ServiceCategory
  icon: string
  color: string
  enabled: boolean
  configured: boolean
  connected: boolean
  state: string | null
  error?: string | null
  lastSync?: string | null
  dataCount?: number
}

export interface SyncJobInfo {
  id: string
  name: string
  serviceId: string
  status: 'idle' | 'syncing' | 'success' | 'error'
  lastRun: string | null
  nextRun: string | null
  interval: string
  itemsProcessed: number
  errorMessage?: string | null
}

export interface IntegrationFlow {
  id: string
  name: string
  description: string
  sourceService: string
  targetService: string
  status: 'active' | 'paused' | 'error'
  lastRun: string | null
}

export interface ServiceHubState {
  connectedServices: ConnectedServiceInfo[]
  syncJobs: SyncJobInfo[]
  integrationFlows: IntegrationFlow[]
  activeTab: 'dashboard' | 'connected' | 'marketplace' | 'sync' | 'settings'
  searchQuery: string
  selectedServiceId: string | null
  selectedCategory: ServiceCategory | 'all'
  loading: boolean
}

export const CONNECTOR_CATALOG: ConnectorCatalogEntry[] = [
  { id: 'telegram', name: 'Telegram', description: 'Connect your Telegram bot for two-way messaging', category: 'messaging', icon: 'send', color: '#26A5E4', docsUrl: 'https://opencode.ai/docs/platforms/telegram', setupGuide: 'In Telegram, talk to @BotFather, run /newbot, and copy the token.', popular: true, authType: 'token' },
  { id: 'discord', name: 'Discord', description: 'Bridge your Discord server with Aetheros', category: 'messaging', icon: 'message-circle', color: '#5865F2', docsUrl: 'https://opencode.ai/docs/platforms/discord', setupGuide: 'Create a Discord app, add a Bot, then copy its token and invite it.', popular: true, authType: 'token' },
  { id: 'slack', name: 'Slack', description: 'Connect Slack workspace channels', category: 'messaging', icon: 'message-square-text', color: '#4A154B', docsUrl: 'https://opencode.ai/docs/platforms/slack', setupGuide: 'Create a Slack app, enable Socket Mode, install it, then copy tokens.', popular: true, authType: 'token' },
  { id: 'whatsapp', name: 'WhatsApp', description: 'Send and receive WhatsApp messages', category: 'messaging', icon: 'message-circle', color: '#25D366', docsUrl: 'https://opencode.ai/docs/platforms/whatsapp', setupGuide: 'Start the WhatsApp bridge, scan the QR code, then enable the platform.', popular: true, authType: 'token' },
  { id: 'signal', name: 'Signal', description: 'Signal private messaging bridge', category: 'messaging', icon: 'message-circle', color: '#3A76F0', docsUrl: 'https://opencode.ai/docs/platforms/signal', setupGuide: 'Run a signal-cli REST bridge and point Aetheros at the URL.', popular: false, authType: 'token' },
  { id: 'matrix', name: 'Matrix', description: 'Federated open messaging protocol', category: 'messaging', icon: 'layers-3', color: '#000000', docsUrl: 'https://opencode.ai/docs/platforms/matrix', setupGuide: 'Sign in with the bot account, copy the access token and homeserver URL.', popular: false, authType: 'token' },
  { id: 'mattermost', name: 'Mattermost', description: 'Self-hosted team communication', category: 'messaging', icon: 'message-square-text', color: '#0058CC', docsUrl: 'https://opencode.ai/docs/platforms/mattermost', setupGuide: 'Create a bot account, then paste the server URL and token.', popular: false, authType: 'token' },
  { id: 'email', name: 'Email (IMAP/SMTP)', description: 'Send and receive emails through Aetheros', category: 'messaging', icon: 'mail', color: '#EA4335', docsUrl: 'https://opencode.ai/docs/platforms/email', setupGuide: 'Use a dedicated mailbox with app password for Gmail/Workspace.', popular: true, authType: 'token' },
  { id: 'sms', name: 'SMS (Twilio)', description: 'SMS messaging via Twilio', category: 'messaging', icon: 'message-square-text', color: '#F43F5E', docsUrl: 'https://opencode.ai/docs/platforms/sms', setupGuide: 'Get your Twilio Account SID and Auth Token from the console.', popular: false, authType: 'token' },
  { id: 'homeassistant', name: 'Home Assistant', description: 'Control smart home devices', category: 'automation', icon: 'home', color: '#18BCF2', docsUrl: 'https://opencode.ai/docs/platforms/homeassistant', setupGuide: 'Create a long-lived access token in your HA profile and paste it here.', popular: true, authType: 'token' },
  { id: 'webhook', name: 'Webhook Server', description: 'Receive incoming webhooks from any service', category: 'developer-tools', icon: 'link', color: '#71717A', docsUrl: 'https://opencode.ai/docs/platforms/webhook', setupGuide: 'Run an HTTP server that other tools can POST to.', popular: true, authType: 'webhook' },
  { id: 'api_server', name: 'API Server', description: 'Expose an OpenAI-compatible API endpoint', category: 'developer-tools', icon: 'terminal', color: '#64748B', docsUrl: 'https://opencode.ai/docs/platforms/api-server', setupGuide: 'Set an auth key, then point Open WebUI / LobeChat at the host:port.', popular: true, authType: 'token' },
  { id: 'bluebubbles', name: 'BlueBubbles', description: 'iMessage bridge for macOS', category: 'messaging', icon: 'message-circle', color: '#0BD318', docsUrl: 'https://opencode.ai/docs/platforms/bluebubbles', setupGuide: 'Run BlueBubbles Server on a Mac, expose its API, then point Aetheros at it.', popular: false, authType: 'token' },
  { id: 'dingtalk', name: 'DingTalk', description: 'Alibaba DingTalk enterprise messaging', category: 'messaging', icon: 'message-circle', color: '#1677FF', docsUrl: 'https://opencode.ai/docs/platforms/dingtalk', setupGuide: 'Create a DingTalk app, copy the Client ID and Client Secret.', popular: false, authType: 'token' },
  { id: 'feishu', name: 'Feishu / Lark', description: 'ByteDance enterprise collaboration', category: 'messaging', icon: 'message-circle', color: '#3370FF', docsUrl: 'https://opencode.ai/docs/platforms/feishu', setupGuide: 'Create a Feishu app, configure bot capability, copy App ID and secret.', popular: false, authType: 'token' },
  { id: 'wecom', name: 'WeCom (Group Robot)', description: 'Tencent WeCom group bot messaging', category: 'messaging', icon: 'message-circle', color: '#07C160', docsUrl: 'https://opencode.ai/docs/platforms/wecom', setupGuide: 'Add a group robot in WeCom and copy its webhook key.', popular: false, authType: 'webhook' },
  { id: 'wecom_callback', name: 'WeCom (App)', description: 'Two-way WeCom self-built app', category: 'messaging', icon: 'message-circle', color: '#07C160', docsUrl: 'https://opencode.ai/docs/platforms/wecom-callback', setupGuide: 'Set up a WeCom self-built app with callback URL and AES key.', popular: false, beta: true, authType: 'token' },
  { id: 'weixin', name: 'WeChat', description: 'WeChat Official Account messaging', category: 'messaging', icon: 'message-circle', color: '#07C160', docsUrl: 'https://opencode.ai/docs/platforms/weixin', setupGuide: 'Sign in to the WeChat Official Account platform, copy AppID and Token.', popular: false, authType: 'token' },
  { id: 'qqbot', name: 'QQ Bot', description: 'Tencent QQ platform bot', category: 'messaging', icon: 'message-circle', color: '#EB1923', docsUrl: 'https://opencode.ai/docs/platforms/qqbot', setupGuide: 'Register an app on the QQ Open Platform, copy App ID and Client Secret.', popular: false, authType: 'token' },
  { id: 'yuanbao', name: 'Yuanbao', description: 'Tencent Yuanbao assistant bridge', category: 'messaging', icon: 'message-circle', color: '#FB7299', docsUrl: 'https://opencode.ai/docs/platforms/yuanbao', setupGuide: 'Configure Yuanbao bot access credentials.', popular: false, beta: true, authType: 'token' },
]

export const SERVICE_CATEGORIES: { id: ServiceCategory; label: string }[] = [
  { id: 'messaging', label: 'Messaging' },
  { id: 'automation', label: 'Automation' },
  { id: 'developer-tools', label: 'Developer Tools' },
  { id: 'storage', label: 'Storage' },
  { id: 'productivity', label: 'Productivity' },
  { id: 'ai-models', label: 'AI Models' }
]

const initialServiceHubState: ServiceHubState = {
  connectedServices: [],
  syncJobs: [],
  integrationFlows: [],
  activeTab: 'dashboard',
  searchQuery: '',
  selectedServiceId: null,
  selectedCategory: 'all',
  loading: false
}

export const $serviceHub = atom<ServiceHubState>(initialServiceHubState)

const patch = (update: Partial<ServiceHubState>) =>
  $serviceHub.set({ ...$serviceHub.get(), ...update })

export function setServiceHubTab(tab: ServiceHubState['activeTab']) { patch({ activeTab: tab }) }

export function setServiceHubSearch(query: string) { patch({ searchQuery: query }) }

export function setServiceHubCategory(category: ServiceCategory | 'all') { patch({ selectedCategory: category }) }

export function setServiceHubLoading(loading: boolean) { patch({ loading }) }

export function selectService(id: string | null) { patch({ selectedServiceId: id }) }

export function setConnectedServices(services: ConnectedServiceInfo[]) {
  patch({ connectedServices: services })
}

export function updateConnectedService(id: string, update: Partial<ConnectedServiceInfo>) {
  const services = $serviceHub.get().connectedServices.map(s =>
    s.id === id ? { ...s, ...update } : s
  )

  patch({ connectedServices: services })
}

export function setSyncJobs(jobs: SyncJobInfo[]) {
  patch({ syncJobs: jobs })
}

export function updateSyncJob(id: string, update: Partial<SyncJobInfo>) {
  const syncJobs = $serviceHub.get().syncJobs.map(j =>
    j.id === id ? { ...j, ...update } : j
  )

  patch({ syncJobs })
}

export function setIntegrationFlows(flows: IntegrationFlow[]) {
  patch({ integrationFlows: flows })
}

export function categorizeConnectors(catalog: ConnectorCatalogEntry[], category: ServiceCategory | 'all'): ConnectorCatalogEntry[] {
  if (category === 'all') {return catalog}

  return catalog.filter(c => c.category === category)
}

export function connectorFromPlatform(platform: { id: string; name: string; description: string }): ConnectorCatalogEntry | undefined {
  return CONNECTOR_CATALOG.find(c => c.id === platform.id)
}
