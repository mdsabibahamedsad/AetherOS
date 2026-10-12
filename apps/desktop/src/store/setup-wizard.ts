import { atom } from 'nanostores'

export interface WizardUserProfile {
  displayName: string
  workspaceName: string
  language: string
  country: string
  timezone: string
  theme: string
  accentColor: string
  avatar: string
  developerMode: boolean
  accessibility: boolean
}

export interface WizardWorkspace {
  workspaceFolder: string
  projectsFolder: string
  downloads: string
  memoryStorage: string
  cache: string
  backups: string
}

export interface WizardProvider {
  slug: string
  name: string
  authType: 'api_key' | 'oauth' | 'local'
  authenticated: boolean
  apiKey?: string
  baseUrl?: string
  models: WizardModel[]
}

export interface WizardModel {
  id: string
  name: string
  favorite: boolean
  isDefault: boolean
  isCoding: boolean
  isReasoning: boolean
  isFast: boolean
  isVision: boolean
  isLongContext: boolean
}

export interface WizardService {
  id: string
  name: string
  enabled: boolean
  connected: boolean
  configured: boolean
}

export interface WizardMemory {
  conversationMemory: boolean
  longTermMemory: boolean
  workspaceMemory: boolean
  knowledgeBase: boolean
  vectorDatabase: boolean
  searchIndex: boolean
  compression: boolean
}

export interface WizardSecurity {
  encryption: boolean
  secureStorage: boolean
  autoLock: boolean
  biometricLock: boolean
  permissionSystem: boolean
  sandbox: boolean
  workspaceIsolation: boolean
  backupEncryption: boolean
}

export interface WizardExtensions {
  developer: boolean
  coding: boolean
  research: boolean
  writing: boolean
  automation: boolean
  dataScience: boolean
  productivity: boolean
}

export interface WizardInitProgress {
  phase: string
  progress: number
  message: string
}

export interface WizardKnowledge {
  importDocuments: boolean
  importConversations: boolean
  importProjects: boolean
  importBookmarks: boolean
  importNotes: boolean
  importCode: boolean
  autoSync: boolean
}

export interface WizardAgent {
  name: string
  description: string
  personality: string
  expertise: string[]
  autoCreate: boolean
}

export interface SetupWizardState {
  needed: boolean
  started: boolean
  completed: boolean
  currentStep: number
  totalSteps: number

  profile: WizardUserProfile
  workspace: WizardWorkspace
  providers: WizardProvider[]
  models: WizardModel[]
  services: WizardService[]
  memory: WizardMemory
  security: WizardSecurity
  extensions: WizardExtensions
  knowledge: WizardKnowledge
  agent: WizardAgent
  initProgress: WizardInitProgress | null

  draftSaved: boolean
  error: string | null
}

const DEFAULT_PROFILE: WizardUserProfile = {
  displayName: '',
  workspaceName: '',
  language: 'en',
  country: '',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  theme: 'aetheros',
  accentColor: '',
  avatar: '',
  developerMode: false,
  accessibility: false
}

const DEFAULT_WORKSPACE: WizardWorkspace = {
  workspaceFolder: '',
  projectsFolder: '',
  downloads: '',
  memoryStorage: '',
  cache: '',
  backups: ''
}

const DEFAULT_MEMORY: WizardMemory = {
  conversationMemory: true,
  longTermMemory: true,
  workspaceMemory: true,
  knowledgeBase: false,
  vectorDatabase: false,
  searchIndex: false,
  compression: true
}

const DEFAULT_SECURITY: WizardSecurity = {
  encryption: true,
  secureStorage: true,
  autoLock: false,
  biometricLock: false,
  permissionSystem: true,
  sandbox: false,
  workspaceIsolation: true,
  backupEncryption: false
}

const DEFAULT_KNOWLEDGE: WizardKnowledge = {
  importDocuments: false,
  importConversations: true,
  importProjects: false,
  importBookmarks: false,
  importNotes: false,
  importCode: false,
  autoSync: true
}

const DEFAULT_AGENT: WizardAgent = {
  name: '',
  description: '',
  personality: 'balanced',
  expertise: [],
  autoCreate: true
}

const DEFAULT_EXTENSIONS: WizardExtensions = {
  developer: false,
  coding: false,
  research: false,
  writing: false,
  automation: false,
  dataScience: false,
  productivity: false
}

function loadDraft(): Partial<SetupWizardState> | null {
  try {
    const raw = localStorage.getItem('aetheros-setup-wizard-v1')

    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveDraft(state: SetupWizardState) {
  try {
    localStorage.setItem('aetheros-setup-wizard-v1', JSON.stringify({
      currentStep: state.currentStep,
      profile: state.profile,
      workspace: state.workspace,
      providers: state.providers,
      services: state.services,
      memory: state.memory,
      security: state.security,
      extensions: state.extensions
    }))
  } catch {
    // localStorage unavailable
  }
}

function clearDraft() {
  try {
    localStorage.removeItem('aetheros-setup-wizard-v1')
  } catch {
    // ignore
  }
}

const draft = loadDraft()

export const $setupWizard = atom<SetupWizardState>({
  needed: false,
  started: false,
  completed: false,
  currentStep: draft?.currentStep ?? 0,
  totalSteps: 16,

  profile: (draft?.profile as WizardUserProfile) ?? DEFAULT_PROFILE,
  workspace: (draft?.workspace as WizardWorkspace) ?? DEFAULT_WORKSPACE,
  providers: draft?.providers ?? [],
  models: [],
  services: draft?.services ?? [
    { id: 'github', name: 'GitHub', enabled: false, connected: false, configured: false },
    { id: 'gitlab', name: 'GitLab', enabled: false, connected: false, configured: false },
    { id: 'telegram', name: 'Telegram', enabled: false, connected: false, configured: false },
    { id: 'discord', name: 'Discord', enabled: false, connected: false, configured: false },
    { id: 'slack', name: 'Slack', enabled: false, connected: false, configured: false },
    { id: 'gmail', name: 'Gmail', enabled: false, connected: false, configured: false },
    { id: 'google-drive', name: 'Google Drive', enabled: false, connected: false, configured: false },
    { id: 'onedrive', name: 'OneDrive', enabled: false, connected: false, configured: false },
    { id: 'dropbox', name: 'Dropbox', enabled: false, connected: false, configured: false },
    { id: 'notion', name: 'Notion', enabled: false, connected: false, configured: false },
    { id: 'calendar', name: 'Calendar', enabled: false, connected: false, configured: false },
    { id: 'whatsapp', name: 'WhatsApp Business', enabled: false, connected: false, configured: false }
  ],
  memory: draft?.memory as WizardMemory ?? DEFAULT_MEMORY,
  security: draft?.security as WizardSecurity ?? DEFAULT_SECURITY,
  extensions: draft?.extensions as WizardExtensions ?? DEFAULT_EXTENSIONS,
  knowledge: draft?.knowledge as WizardKnowledge ?? DEFAULT_KNOWLEDGE,
  agent: draft?.agent as WizardAgent ?? DEFAULT_AGENT,
  initProgress: null,

  draftSaved: false,
  error: null
})

const patch = (update: Partial<SetupWizardState>) =>
  $setupWizard.set({ ...$setupWizard.get(), ...update })

export function startSetupWizard() {
  patch({ needed: false, started: true })
}

export function resumeSetupWizard() {
  patch({ needed: false, started: true, draftSaved: false })
}

export function goToStep(step: number) {
  const state = $setupWizard.get()

  if (step >= 0 && step < state.totalSteps) {
    patch({ currentStep: step, error: null })
  }
}

export function nextStep() {
  const state = $setupWizard.get()

  if (state.currentStep < state.totalSteps - 1) {
    goToStep(state.currentStep + 1)
  }
}

export function prevStep() {
  goToStep($setupWizard.get().currentStep - 1)
}

export function saveDraftAndExit() {
  saveDraft($setupWizard.get())
  patch({ draftSaved: true, started: false, needed: true })
}

export function updateProfile(update: Partial<WizardUserProfile>) {
  patch({ profile: { ...$setupWizard.get().profile, ...update } })
}

export function updateWorkspace(update: Partial<WizardWorkspace>) {
  patch({ workspace: { ...$setupWizard.get().workspace, ...update } })
}

export function setProviders(providers: WizardProvider[]) {
  patch({ providers })
}

export function addProvider(provider: WizardProvider) {
  const current = $setupWizard.get().providers

  if (!current.find(p => p.slug === provider.slug)) {
    patch({ providers: [...current, provider] })
  }
}

export function removeProvider(slug: string) {
  patch({ providers: $setupWizard.get().providers.filter(p => p.slug !== slug) })
}

export function updateProviderModels(slug: string, models: WizardModel[]) {
  const providers = $setupWizard.get().providers.map(p =>
    p.slug === slug ? { ...p, models } : p
  )

  patch({ providers })
}

export function updateProviderAuth(slug: string, auth: { apiKey?: string; baseUrl?: string }) {
  const providers = $setupWizard.get().providers.map(p =>
    p.slug === slug ? { ...p, ...auth, authenticated: true } : p
  )

  patch({ providers })
}

export function setModels(models: WizardModel[]) {
  patch({ models })
}

export function toggleModelFavorite(modelId: string) {
  const models = $setupWizard.get().models.map(m =>
    m.id === modelId ? { ...m, favorite: !m.favorite } : m
  )

  patch({ models })
}

export function updateService(id: string, update: Partial<WizardService>) {
  const services = $setupWizard.get().services.map(s =>
    s.id === id ? { ...s, ...update } : s
  )

  patch({ services })
}

export function toggleService(id: string) {
  const services = $setupWizard.get().services.map(s =>
    s.id === id ? { ...s, enabled: !s.enabled } : s
  )

  patch({ services })
}

export function updateMemory(update: Partial<WizardMemory>) {
  patch({ memory: { ...$setupWizard.get().memory, ...update } })
}

export function updateSecurity(update: Partial<WizardSecurity>) {
  patch({ security: { ...$setupWizard.get().security, ...update } })
}

export function updateExtensions(update: Partial<WizardExtensions>) {
  patch({ extensions: { ...$setupWizard.get().extensions, ...update } })
}

export function updateKnowledge(update: Partial<WizardKnowledge>) {
  patch({ knowledge: { ...$setupWizard.get().knowledge, ...update } })
}

export function updateAgent(update: Partial<WizardAgent>) {
  patch({ agent: { ...$setupWizard.get().agent, ...update } })
}

export function setInitProgress(progress: WizardInitProgress | null) {
  patch({ initProgress: progress })
}

/** Persist wizard settings to the actual backend stores */
function persistWizardSettings(state: SetupWizardState): void {
  try {
    const config: Record<string, unknown> = {
      'display.theme': state.profile.theme,
      'display.accent': state.profile.accentColor,
      'display.language': state.profile.language,
      'display.timezone': state.profile.timezone,
      'profile.name': state.profile.displayName,
      'profile.workspace': state.profile.workspaceName,
      'profile.developer_mode': state.profile.developerMode,
      'profile.accessibility': state.profile.accessibility,
      'workspace.folder': state.workspace.workspaceFolder,
      'workspace.projects': state.workspace.projectsFolder,
      'memory.conversation': state.memory.conversationMemory,
      'memory.long_term': state.memory.longTermMemory,
      'memory.vector_db': state.memory.vectorDatabase,
      'memory.compression': state.memory.compression,
      'security.encryption': state.security.encryption,
      'security.auto_lock': state.security.autoLock,
      'security.sandbox': state.security.sandbox,
      'knowledge': state.knowledge,
      'agent': state.agent
    }

    try {
      window.aetherosDesktop?.api?.({ path: '/api/config/set', method: 'POST', body: config }).catch(() => undefined)
    } catch {
      // Backend may not be available
    }

    try {
      localStorage.setItem('aetheros-wizard-config', JSON.stringify(config))
    } catch {
      // localStorage unavailable
    }
  } catch {
    // Silently fail — persistence is best-effort during setup
  }
}

export function completeSetupWizard() {
  const state = $setupWizard.get()
  clearDraft()

  persistWizardSettings(state)

  patch({
    started: false,
    completed: true,
    currentStep: 0,
    initProgress: null,
    error: null
  })
}

export function setWizardError(error: string | null) {
  patch({ error })
}
