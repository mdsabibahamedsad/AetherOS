export { createRule, deleteRule, executeRule, getRule, initializeAutomation, listRules, parseNaturalLanguageRule, updateRule } from './automation/automation-engine'

export { cancelJob, completeJob, createBackgroundJob, failJob, getAllJobs, getJob, getJobCount, getRunningJobs, pauseJob, resumeJob, retryJob, startJob, updateJobProgress } from './background/job-manager'
export { analyzeIntent, executePipeline } from './core/ai-core'

export type { PipelineResult } from './core/ai-core'

export { acceptSuggestion, clearSuggestions, getAutonomyLevel, getAutonomyState, getPendingSuggestions, isAutonomous, rejectSuggestion, setAutonomy, startAutonomy, stopAutonomy } from './core/autonomy'
export type { AutonomyLevel } from './core/autonomy'

// --- Backend Bridge ---
export {
  addMemory, acceptSuggestion as bridgeAcceptSuggestion, getContext as bridgeGetContext, getMemory as bridgeGetMemory, getNotifications as bridgeGetNotifications,
  getPendingSuggestions as bridgeGetPendingSuggestions, pauseEngine as bridgePauseEngine, rejectSuggestion as bridgeRejectSuggestion, resumeEngine as bridgeResumeEngine,
  setAutonomy as bridgeSetAutonomy, startEngine as bridgeStartEngine,
  stopEngine as bridgeStopEngine, checkHealth,
  connectToBackend, getExecutorTasks,
  getGraphs, getObserverEvents,
  getSchedulerJobs, jarvisBridge,
  sendCommand,
} from './core/backend-bridge'

export { getContext, logAction, markIdle, resetContext, updateContext } from './core/context'

export type { JarvisContext } from './core/context'

export { executeCommand, getEngineState, onStateChange, pauseEngine, resumeEngine, startEngine, stopEngine } from './core/engine'

export type { EnginePhase as JarvisEnginePhase } from './core/engine'

export { cancelTask as cancelExecutorTask, completeTask as completeExecutorTask, executeTask, failTask as failExecutorTask, getActiveTasks, getAllTasks as getAllExecutorTasks, getCapabilityAvailability, getTask, isCapabilityAvailable, setCapabilityAvailable } from './core/executor'

export type { ExecutorCapability, ExecutorTask } from './core/executor'

export { clearMemory, forget, getAllMemory, getMemoryStats as getCoreMemoryStats, recall, remember, searchMemory as searchCoreMemory, seedCoreMemory } from './core/memory'

export { clearNotifications as clearEngineNotifications, getNotifications, getNotificationStats, getUnreadCount, markAllRead, markRead, notify, onNotification } from './core/notifications'
export type { JarvisNotification, NotificationLevel, NotificationSource } from './core/notifications'
export { emitEvent, getRecentEvents, onEvent, recordUserActivity, simulateEvent, startObserver, stopObserver } from './core/observer'
export type { ObserverEvent, ObserverEventType, ObserverHandler } from './core/observer'
export { addNode, cancelGraph, createCodePlan, createDeployPlan, createGraph, createResearchPlan, getAllGraphs, getGraph, getGraphStatus, getReadyNodes, pauseNode, resumeNode, retryNode, startGraph, updateNodeProgress, updateNodeStatus } from './core/planner'
export type { TaskStatus as PlannerTaskStatus, TaskGraph, TaskNode } from './core/planner'
export { getReasoningRules, reason } from './core/reasoning'
export type { ReasoningResult, ReasoningSuggestion as ReasoningSuggestionResult } from './core/reasoning'
export { disableJob, enableJob, getJobs, getJob as getScheduledJob, onTick, runJobNow, schedule, seedDefaultJobs, startScheduler, stopScheduler, unschedule } from './core/scheduler'
export type { ScheduledJob } from './core/scheduler'
export { disableSkill, enableSkill, getAllSkills, getSkill, getSkillsByCategory, getSkillStats, loadBuiltinSkills } from './core/skills'
export type { Skill } from './core/skills'
// --- Phase 4: Jarvis Engine ---
export { initializeJarvisEngine, isEngineInitialized, shutdownJarvisEngine } from './core/startup'
export { cancelTask as cancelBgTask, completeTask as completeBgTask, createTask as createBackgroundTask, failTask as failBgTask, getAllTasks as getAllBgTasks, getTask as getBgTask, getQueuedTasks, getRunningTasks, getTaskStats, pauseTask as pauseBgTask, resumeTask as resumeBgTask, retryTask as retryBgTask, updateProgress as updateBgProgress } from './core/task-manager'
export type { BackgroundTask, BackgroundTaskStatus, BackgroundTaskType } from './core/task-manager'
export {
  canTransition,
  classifyError,
  createTask as createJarvisTask,
  forceTransition,
  MAX_SELF_REPAIR_RETRIES,
  transition as transitionJarvisTask
} from './core/task-state-machine'
export type {
  ApprovalRequest as JarvisTaskApproval,
  CancellationState as JarvisTaskCancellation,
  JarvisTask,
  JarvisTaskStatus,
  TaskError as JarvisTaskError,
  TaskInput as JarvisTaskInput,
  TaskResult as JarvisTaskResult,
  TaskStep as JarvisTaskStep
} from './core/task-state-machine'
export { runOrchestratedTask } from './core/orchestrator'
export { decideApproval, levelForCapability, levelForDestructiveInput, pendingApprovals, requestApproval } from './core/approval-engine'
export type { ApprovalLevel, ApprovalTicket } from './core/approval-engine'
export { routeCommand, validateToolCall } from './core/tool-router'
export { clearDiagnostics, createTimer, recentDiagnostics, recordDiagnostic } from './core/observability'
export type { LatencyBreakdown, TaskDiagnostic } from './core/observability'
export { clearStoredTasks, persistTask, recoverTasks } from './core/task-persistence'
export { stopJarvis } from './core/emergency-stop'
export {
  click as computerClick,
  describeScreen,
  doubleClick as computerDoubleClick,
  drag as computerDrag,
  focusWindow as computerFocusWindow,
  launchApplication as computerLaunch,
  listWindows as computerListWindows,
  pressKey as computerPressKey,
  rightClick as computerRightClick,
  scroll as computerScroll,
  typeText as computerType
} from './computer/computer-use'
export { addRelation, createMemory, deleteMemory, findPath, getMemory, getMemoryStats, getRelatedNodes, listMemories, removeRelation, searchMemory, seedMemoryGraph, updateMemory } from './memory/memory-graph'
export { getModelFallbackChain, getModelInfo, isModelAvailable, listAvailableModels, selectModel } from './models/model-router'
export { assessSystemHealth, fetchSystemStatus, getAllHealthChecks, getSystemHealth, initializeMonitoring, registerHealthCheck, registerRecoveryHandler, updateHealthCheck } from './monitoring/health-monitor'
export { AGENT_DEFINITIONS, cancelAgentTask, canSpawnAgent, completeAgentTask, createAgentTask, failAgentTask, getActiveAgents, getAgentDefinition, selectAgentForStep, updateAgentProgress } from './orchestrator/agent-orchestrator'
export { createExecutionPlan, estimateCompletion, getNextPendingSteps, getPlanSummary, hasParallelSteps } from './planner/execution-planner'
export { analyzeContext, generateSmartSuggestion, generateSuggestions, reflectOnExecution, validateStep } from './reasoner/reasoner'
export type { ReasoningContext, ReasoningSuggestion } from './reasoner/reasoner'
export { approvePermission, denyPermission, getAuditLog, getPendingRequests, getSecurityPolicy, requestPermission, updateSecurityPolicy } from './security/security-manager'
export type * from './types'

export { autoDetectWorkspace, buildContextPrompt, getWorkspaceContext, onWorkspaceContextChange, trackCommand, trackOpenFile, updateWorkspaceContext } from './workspace/workspace-awareness'
