import { atom, computed } from 'nanostores'

// --- Jarvis Mode Toggle ---
export const $jarvisMode = atom<boolean>(false)

export function setJarvisMode(enabled: boolean) {
  $jarvisMode.set(enabled)
}

export function toggleJarvisMode() {
  $jarvisMode.set(!$jarvisMode.get())
}

// --- UI State ---
export type JarvisPanel = 'left' | 'right' | null
export const $jarvisActivePanel = atom<JarvisPanel>(null)
export const $jarvisLeftPanelSection = atom<string>('chat')
export const $jarvisRightPanelSection = atom<string>('agents')

export function setJarvisActivePanel(panel: JarvisPanel) {
  $jarvisActivePanel.set(panel)
}

export function setJarvisLeftSection(section: string) {
  $jarvisLeftPanelSection.set(section)
}

export function setJarvisRightSection(section: string) {
  $jarvisRightPanelSection.set(section)
}

// --- System Status ---
// Full gateway lifecycle — the UI must never collapse these to a binary
// connected/disconnected pair. `starting` = backend spawn in progress,
// `connecting` = WS handshake in flight, `reconnecting` = backoff retry after
// an unexpected drop, `degraded` = socket open but a health probe failed,
// `error`/`stopped` carry a detail string in $jarvisGatewayDetail.
export type JarvisGatewayState =
  | 'starting'
  | 'connecting'
  | 'connected'
  | 'degraded'
  | 'disconnected'
  | 'reconnecting'
  | 'error'
  | 'stopped'

export type JarvisBackendState = 'running' | 'stopped' | 'starting'

export interface JarvisSystemStatus {
  cpu: number
  memory: { used: number; total: number; percent: number }
  gpu: { name: string; percent: number; used: number; total: number } | null
  gateway: JarvisGatewayState
  backend: JarvisBackendState
  model: string
  provider: string
  activeTasks: number
  uptime: number
}

export const $jarvisSystemStatus = atom<JarvisSystemStatus>({
  cpu: 0,
  memory: { used: 0, total: 0, percent: 0 },
  gpu: null,
  gateway: 'starting',
  backend: 'starting',
  model: '',
  provider: '',
  activeTasks: 0,
  uptime: 0
})

export function updateJarvisSystemStatus(partial: Partial<JarvisSystemStatus>) {
  $jarvisSystemStatus.set({ ...$jarvisSystemStatus.get(), ...partial })
}

// Structured gateway health surfaced to the UI. Never includes credentials.
export interface JarvisGatewayDetail {
  latencyMs: number | null
  lastHeartbeat: number | null
  version: string | null
  capabilities: string[]
  error: string | null
  reconnectAttempt: number
}

export const $jarvisGatewayDetail = atom<JarvisGatewayDetail>({
  latencyMs: null,
  lastHeartbeat: null,
  version: null,
  capabilities: [],
  error: null,
  reconnectAttempt: 0
})

export function updateJarvisGatewayDetail(partial: Partial<JarvisGatewayDetail>) {
  $jarvisGatewayDetail.set({ ...$jarvisGatewayDetail.get(), ...partial })
}

/** Map the low-level socket state to the user-facing lifecycle. */
export function mapSocketToGatewayState(
  socket: string,
  opts: { bootCompleted: boolean; reconnectAttempt: number; healthOk: boolean | null } = {
    bootCompleted: false,
    reconnectAttempt: 0,
    healthOk: null
  }
): JarvisGatewayState {
  if (socket === 'open' || socket === 'connected') {
    if (opts.healthOk === false) {return 'degraded'}

    return 'connected'
  }

  if (socket === 'connecting') {return opts.reconnectAttempt > 0 || opts.bootCompleted ? 'reconnecting' : 'connecting'}

  if (socket === 'error') {return 'error'}

  if (socket === 'closed' || socket === 'disconnected') {
    if (opts.reconnectAttempt > 0) {return 'reconnecting'}

    return opts.bootCompleted ? 'disconnected' : 'starting'
  }

  if (socket === 'idle') {return opts.bootCompleted ? 'disconnected' : 'starting'}

  return 'disconnected'
}

// --- Jarvis command execution state machine ---
// IDLE → SUBMITTED → PARSING → PLANNING → AWAITING_PERMISSION → EXECUTING →
// STREAMING → COMPLETED, with FAILED / CANCELLED / TIMEOUT / UNAVAILABLE exits.
export type JarvisExecutionState =
  | 'IDLE'
  | 'SUBMITTED'
  | 'PARSING'
  | 'PLANNING'
  | 'AWAITING_PERMISSION'
  | 'EXECUTING'
  | 'STREAMING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'TIMEOUT'
  | 'UNAVAILABLE'

export interface JarvisExecution {
  state: JarvisExecutionState
  commandId: string | null
  sessionId: string | null
  startedAt: number | null
  error: string | null
}

export const $jarvisExecution = atom<JarvisExecution>({
  state: 'IDLE',
  commandId: null,
  sessionId: null,
  startedAt: null,
  error: null
})

export function setJarvisExecution(next: Partial<JarvisExecution>) {
  $jarvisExecution.set({ ...$jarvisExecution.get(), ...next })
}

export function resetJarvisExecution() {
  $jarvisExecution.set({ state: 'IDLE', commandId: null, sessionId: null, startedAt: null, error: null })
}

// In-flight = a pipeline is alive and owns the gateway session. Terminal +
// IDLE + AWAITING_PERMISSION (local gate: nothing executed yet) accept a new
// command. Used by every submit entry point to prevent duplicate execution.
const JARVIS_IN_FLIGHT_STATES: ReadonlySet<JarvisExecutionState> = new Set([
  'SUBMITTED',
  'PARSING',
  'PLANNING',
  'EXECUTING',
  'STREAMING'
])

export function isJarvisExecutingState(state: JarvisExecutionState): boolean {
  return JARVIS_IN_FLIGHT_STATES.has(state)
}

// --- Real Jarvis command history (never sample data) ---
export type JarvisInputType = 'text' | 'voice' | 'system'
export interface JarvisCommandRecord {
  id: string
  timestamp: number
  sessionId: string | null
  input: string
  /** How the command entered Jarvis — voice transcripts use the same pipeline as text. */
  inputType: JarvisInputType
  intent: string
  status: JarvisExecutionState
  durationMs: number
  toolsUsed: string[]
  result: string | null
  error: string | null
}

export const $jarvisCommandLog = atom<JarvisCommandRecord[]>([])

export function appendJarvisCommandLog(record: JarvisCommandRecord) {
  $jarvisCommandLog.set([record, ...$jarvisCommandLog.get()].slice(0, 100))
}

// --- AI Thinking State ---
export type ThinkingStage =
  | 'idle'
  | 'understanding'
  | 'planning'
  | 'searching'
  | 'using-tools'
  | 'executing'
  | 'validating'
  | 'complete'

export const $jarvisThinkingStage = atom<ThinkingStage>('idle')
export const $jarvisThinkingLabel = atom<string>('')

export function setJarvisThinkingStage(stage: ThinkingStage, label?: string) {
  $jarvisThinkingStage.set(stage)
  $jarvisThinkingLabel.set(label ?? stage)
}

// --- Active Agents ---
export interface JarvisAgent {
  id: string
  name: string
  type: 'research' | 'coding' | 'browser' | 'planning' | 'memory' | 'automation' | 'custom' | 'file' | 'communication' | 'data' | 'terminal' | 'database' | 'vision' | 'voice'
  status: 'running' | 'idle' | 'error' | 'completed'
  progress?: number
  currentTask?: string
  startedAt?: number
  sessionId?: string
}

export const $jarvisAgents = atom<JarvisAgent[]>([])
export const $jarvisActiveAgentCount = computed($jarvisAgents, agents => agents.filter(a => a.status === 'running').length)

export function updateJarvisAgent(id: string, update: Partial<JarvisAgent>) {
  const agents = $jarvisAgents.get().map(a => a.id === id ? { ...a, ...update } : a)
  $jarvisAgents.set(agents)
}

export function addJarvisAgent(agent: JarvisAgent) {
  $jarvisAgents.set([...$jarvisAgents.get(), agent])
}

export function removeJarvisAgent(id: string) {
  $jarvisAgents.set($jarvisAgents.get().filter(a => a.id !== id))
}

// --- Automation Jobs ---
export interface JarvisAutomationJob {
  id: string
  name: string
  status: 'running' | 'queued' | 'completed' | 'failed' | 'paused'
  progress?: number
  eta?: number
  startedAt?: number
  completedAt?: number
  error?: string
  type: 'scheduled' | 'triggered' | 'background'
}

export const $jarvisAutomationJobs = atom<JarvisAutomationJob[]>([])
export const $jarvisRunningJobCount = computed($jarvisAutomationJobs, jobs => jobs.filter(j => j.status === 'running').length)

export function updateJarvisJob(id: string, update: Partial<JarvisAutomationJob>) {
  const jobs = $jarvisAutomationJobs.get().map(j => j.id === id ? { ...j, ...update } : j)
  $jarvisAutomationJobs.set(jobs)
}

export function addJarvisJob(job: JarvisAutomationJob) {
  $jarvisAutomationJobs.set([...$jarvisAutomationJobs.get(), job])
}

// --- Notifications ---
export interface JarvisNotification {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  timestamp: number
  read: boolean
  action?: { label: string; onClick: string }
}

export const $jarvisNotifications = atom<JarvisNotification[]>([])
export const $jarvisUnreadCount = computed($jarvisNotifications, notifs => notifs.filter(n => !n.read).length)

export function addJarvisNotification(notif: Omit<JarvisNotification, 'id' | 'timestamp' | 'read'>) {
  const newNotif: JarvisNotification = {
    ...notif,
    id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: Date.now(),
    read: false
  }

  $jarvisNotifications.set([newNotif, ...$jarvisNotifications.get()].slice(0, 100))
}

export function markNotificationRead(id: string) {
  $jarvisNotifications.set(
    $jarvisNotifications.get().map(n => n.id === id ? { ...n, read: true } : n)
  )
}

export function clearNotifications() {
  $jarvisNotifications.set([])
}

// --- Voice Mode ---
export type VoiceMode = 'off' | 'push-to-talk' | 'continuous' | 'wake-word'
export const $jarvisVoiceMode = atom<VoiceMode>('off')
export const $jarvisVoiceListening = atom(false)
export const $jarvisVoiceTranscript = atom('')

export function setJarvisVoiceTranscript(transcript: string) {
  $jarvisVoiceTranscript.set(transcript)
}

export function setJarvisVoiceMode(mode: VoiceMode) {
  $jarvisVoiceMode.set(mode)
}

// --- Layout ---
export const $jarvisFullscreen = atom(true)

/** Overlay density. Fullscreen covers the workspace; expanded leaves a
 *  margin; compact is a bottom-docked console. State only — same pipeline. */
export type JarvisDisplayMode = 'compact' | 'expanded' | 'fullscreen'
export const $jarvisDisplayMode = atom<JarvisDisplayMode>('fullscreen')

export function setJarvisDisplayMode(mode: JarvisDisplayMode) {
  $jarvisDisplayMode.set(mode)
}

// --- Command History ---
export const $jarvisCommandHistory = atom<string[]>([])
export const $jarvisCommandIndex = atom(-1)

export function addJarvisCommand(cmd: string) {
  const history = $jarvisCommandHistory.get()
  $jarvisCommandHistory.set([cmd, ...history].slice(0, 50))
  $jarvisCommandIndex.set(-1)
}

// --- Phase 3: Orb State ---
export type OrbState = 'idle' | 'listening' | 'thinking' | 'planning' | 'executing' | 'speaking' | 'searching' | 'coding' | 'error' | 'success'

export const $jarvisOrbState = atom<OrbState>('idle')

export function setJarvisOrbState(state: OrbState) {
  $jarvisOrbState.set(state)
}

// --- Phase 3: AI Orchestra ---
export interface OrchestraModel {
  id: string
  name: string
  provider: string
  model: string
  capability: string
  status: 'idle' | 'working' | 'completed' | 'error'
  task: string
  startedAt: number
  tokensUsed: number
  runtime: number
  selectedReason: string
}

export const $jarvisOrchestra = atom<OrchestraModel[]>([])
export const $jarvisOrchestraActive = computed($jarvisOrchestra, models => models.filter(m => m.status === 'working').length)

export function addOrchestraModel(model: OrchestraModel) {
  $jarvisOrchestra.set([...$jarvisOrchestra.get(), model])
}

export function updateOrchestraModel(id: string, update: Partial<OrchestraModel>) {
  const models = $jarvisOrchestra.get().map(m => m.id === id ? { ...m, ...update } : m)
  $jarvisOrchestra.set(models)
}

export function clearOrchestra() {
  $jarvisOrchestra.set([])
}

// --- Phase 3: Active Mission View ---
export type MissionView = 'orb' | 'projects' | 'agents' | 'knowledge' | 'memory' | 'files' | 'automation' | 'browser' | 'terminal' | 'database' | 'communication' | 'marketplace' | 'settings'

export const $jarvisMissionView = atom<MissionView>('orb')

export function setJarvisMissionView(view: MissionView) {
  $jarvisMissionView.set(view)
}

// --- Phase 3: Toast Notifications ---
export interface JarvisToast {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  timestamp: number
  duration: number
  dismissing: boolean
}

export const $jarvisToasts = atom<JarvisToast[]>([])

export function addJarvisToast(toast: Omit<JarvisToast, 'id' | 'timestamp' | 'dismissing'>) {
  const newToast: JarvisToast = {
    ...toast,
    id: `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: Date.now(),
    dismissing: false
  }

  $jarvisToasts.set([...$jarvisToasts.get(), newToast])

  if (toast.duration > 0) {
    setTimeout(() => dismissJarvisToast(newToast.id), toast.duration)
  }
}

export function dismissJarvisToast(id: string) {
  $jarvisToasts.set(
    $jarvisToasts.get().map(t => t.id === id ? { ...t, dismissing: true } : t)
  )
  setTimeout(() => {
    $jarvisToasts.set($jarvisToasts.get().filter(t => t.id !== id))
  }, 300)
}

// --- Phase 3: Floating Workspace Windows ---
export interface FloatingWindow {
  id: string
  type: 'browser' | 'terminal' | 'editor' | 'database' | 'artifacts' | 'preview' | 'whiteboard' | 'canvas'
  title: string
  x: number
  y: number
  width: number
  height: number
  zIndex: number
  minimized: boolean
  focused: boolean
}

export const $jarvisFloatingWindows = atom<FloatingWindow[]>([])
let _windowZCounter = 10

export function addFloatingWindow(window: Omit<FloatingWindow, 'id' | 'zIndex' | 'minimized' | 'focused'>) {
  const newWindow: FloatingWindow = {
    ...window,
    id: `float-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    zIndex: ++_windowZCounter,
    minimized: false,
    focused: true
  }

  $jarvisFloatingWindows.set([
    ...$jarvisFloatingWindows.get().map(w => ({ ...w, focused: false })),
    newWindow
  ])
}

export function closeFloatingWindow(id: string) {
  $jarvisFloatingWindows.set($jarvisFloatingWindows.get().filter(w => w.id !== id))
}

export function focusFloatingWindow(id: string) {
  $jarvisFloatingWindows.set(
    $jarvisFloatingWindows.get().map(w => ({
      ...w,
      focused: w.id === id,
      zIndex: w.id === id ? ++_windowZCounter : w.zIndex
    }))
  )
}

export function updateFloatingWindow(id: string, update: Partial<FloatingWindow>) {
  $jarvisFloatingWindows.set(
    $jarvisFloatingWindows.get().map(w => w.id === id ? { ...w, ...update } : w)
  )
}

export function toggleMinimizeFloatingWindow(id: string) {
  $jarvisFloatingWindows.set(
    $jarvisFloatingWindows.get().map(w => w.id === id ? { ...w, minimized: !w.minimized } : w)
  )
}

// --- Phase 4: Jarvis Engine State ---
export type EnginePhase = 'idle' | 'observing' | 'thinking' | 'planning' | 'executing' | 'learning' | 'error'

export const $jarvisEnginePhase = atom<EnginePhase>('idle')
export const $jarvisEngineCycleCount = atom(0)
export const $jarvisEngineActive = atom(false)
export const $jarvisAutonomyEnabled = atom(false)
export const $jarvisAutonomyLevel = atom<'off' | 'suggestions' | 'semi' | 'full'>('off')

export function syncEngineState(state: { phase: EnginePhase; cycleCount: number; isRunning: boolean }) {
  $jarvisEnginePhase.set(state.phase)
  $jarvisEngineCycleCount.set(state.cycleCount)
  $jarvisEngineActive.set(state.isRunning)
}

export function setAutonomyState(enabled: boolean, level: 'off' | 'suggestions' | 'semi' | 'full') {
  $jarvisAutonomyEnabled.set(enabled)
  $jarvisAutonomyLevel.set(level)
}

// --- Phase 4: Engine Task Stats ---
export const $jarvisEngineTaskStats = atom({ total: 0, running: 0, queued: 0, completed: 0, failed: 0, paused: 0 })
export const $jarvisEngineNotificationCount = atom(0)
export const $jarvisEngineSkillsCount = atom(0)
export const $jarvisEngineMemoryCount = atom(0)

export function updateEngineStats(stats: Partial<{
  tasks: { total: number; running: number; queued: number; completed: number; failed: number; paused: number }
  notifications: number
  skills: number
  memory: number
}>) {
  if (stats.tasks) {$jarvisEngineTaskStats.set(stats.tasks)}

  if (stats.notifications !== undefined) {$jarvisEngineNotificationCount.set(stats.notifications)}

  if (stats.skills !== undefined) {$jarvisEngineSkillsCount.set(stats.skills)}

  if (stats.memory !== undefined) {$jarvisEngineMemoryCount.set(stats.memory)}
}
