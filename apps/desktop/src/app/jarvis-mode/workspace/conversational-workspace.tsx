import { AnimatePresence, motion } from 'motion/react'
import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Codicon } from '@/components/ui/codicon'
import { initializeAutomation } from '@/lib/jarvis/automation/automation-engine'
import { ApprovalRequiredError, submitJarvisCommand } from '@/lib/jarvis/core/command-gateway'
import { getMemoryStats } from '@/lib/jarvis/memory/memory-graph'
import { seedMemoryGraph } from '@/lib/jarvis/memory/memory-graph'
import { assessSystemHealth, initializeMonitoring } from '@/lib/jarvis/monitoring/health-monitor'
import { createDesktopCommandDeps } from '@/lib/jarvis/os/local-executor'
import type { ExecutionPlan, ExecutionPlanStep } from '@/lib/jarvis/types'
import { buildContextPrompt, getWorkspaceContext } from '@/lib/jarvis/workspace/workspace-awareness'
import { addJarvisNotification, setJarvisLeftSection, setJarvisThinkingStage } from '@/store/jarvis-mode'

import { CommandInput } from '../command-center/command-input'
import { GlassPanel } from '../shared/glass-panel'

import { LiveThinking } from './live-thinking'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  plan?: ExecutionPlan
  modelUsed?: { provider: string; model: string }
}

function PlanStepBar({ step, index }: { step: ExecutionPlanStep; index: number }) {
  const statusIcon = {
    pending: 'circle-outline', planning: 'loading', running: 'loading',
    queued: 'clock', paused: 'debug-pause', completed: 'pass',
    failed: 'error', cancelled: 'close'
  } as const

  const statusColor = {
    pending: 'text-white/20', planning: 'text-[#00d4ff]', running: 'text-[#00d4ff]',
    queued: 'text-white/30', paused: 'text-amber-400', completed: 'text-emerald-400',
    failed: 'text-red-400', cancelled: 'text-white/30'
  } as const

  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-2 py-1"
      initial={{ opacity: 0, x: -10 }}
      transition={{ delay: index * 0.05 }}
    >
      <Codicon
        className={`size-3.5 shrink-0 ${statusColor[step.status] ?? 'text-white/20'} ${step.status === 'running' ? 'animate-spin' : ''}`}
        name={statusIcon[step.status] ?? 'circle-outline'}
      />
      <span className={`text-[12px] ${
        step.status === 'completed' ? 'text-white/50 line-through' :
        step.status === 'running' ? 'text-white/80' :
        step.status === 'failed' ? 'text-red-400' :
        'text-white/30'
      }`}>
        {step.label}
      </span>
      {step.status === 'running' && step.progress > 0 && (
        <div className="flex-1 h-1 rounded-full bg-white/[0.06] overflow-hidden ml-2 max-w-[100px]">
          <motion.div
            animate={{ width: `${step.progress}%` }}
            className="h-full rounded-full bg-gradient-to-r from-[#0066ff] to-[#00d4ff]"
            transition={{ duration: 0.3 }}
          />
        </div>
      )}
    </motion.div>
  )
}

function PlanVisualization({ plan }: { plan: ExecutionPlan }) {
  const totalSteps = plan.steps.length
  const completedSteps = plan.steps.filter(s => s.status === 'completed').length
  const failedSteps = plan.steps.filter(s => s.status === 'failed').length

  const elapsed = plan.endTime
    ? ((plan.endTime - plan.startTime) / 1000).toFixed(1)
    : ((Date.now() - plan.startTime) / 1000).toFixed(1)

  return (
    <motion.div
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      initial={{ opacity: 0, height: 0 }}
    >
    <GlassPanel className="mx-auto max-w-3xl mb-4 p-4 rounded-xl" glow="blue" intensity="light"
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="flex items-center justify-center size-6 rounded-md bg-[#00d4ff]/10">
          <Codicon className="size-3.5 text-[#00d4ff]" name="list-flat" />
        </div>
        <span className="text-[11px] font-medium text-white/40 uppercase tracking-wider">
          Execution Plan — {totalSteps} steps
        </span>
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-[10px] text-white/25">{completedSteps}/{totalSteps} · {elapsed}s</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
            plan.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
            plan.status === 'running' ? 'bg-[#00d4ff]/20 text-[#00d4ff]' :
            failedSteps > 0 ? 'bg-red-500/20 text-red-400' :
            'bg-white/[0.06] text-white/30'
          }`}>
            {plan.status}
          </span>
        </div>
      </div>

      <div className="space-y-0.5">
        {plan.steps.map((step, i) => (
          <PlanStepBar index={i} key={step.id} step={step} />
        ))}
      </div>

      {plan.intent && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/[0.04]">
          <span className="text-[10px] text-white/20">Intent: {plan.intent.type}</span>
          <span className="text-[10px] text-white/20">Confidence: {(plan.intent.confidence * 100).toFixed(0)}%</span>
          {plan.intent.requiresTools.length > 0 && (
            <span className="text-[10px] text-white/20">Tools: {plan.intent.requiresTools.join(', ')}</span>
          )}
        </div>
      )}
    </GlassPanel>
    </motion.div>
  )
}

function SystemBanner() {
  const ctx = getWorkspaceContext()

  if (!ctx.cwd && !ctx.gitRoot) {return null}

  return (
    <div className="mx-auto max-w-3xl mb-4 p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
      <div className="flex items-center gap-3 text-[11px] text-white/30">
        <Codicon className="size-3.5 text-[#00d4ff]" name="repo" />
        {ctx.gitRoot && <span className="truncate">{ctx.gitRoot.replace(/^.*[/\\]/, '')}</span>}
        {ctx.branch && (
          <span className="flex items-center gap-1">
            <Codicon className="size-3" name="git-branch" />
            {ctx.branch}
          </span>
        )}
        {ctx.cwd && <span className="text-white/20 truncate">{ctx.cwd}</span>}
      </div>
    </div>
  )
}

function WelcomeSuggestions() {
  const memoryStats = getMemoryStats()

  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
    <GlassPanel className="p-8 rounded-2xl" glow="cyan" intensity="medium">
      <motion.div
        animate={{ opacity: 1 }}
        className="space-y-6"
        initial={{ opacity: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="relative mx-auto size-20">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[#0066ff] via-[#00d4ff] to-[#9933ff] opacity-30 blur-xl" />
          <div className="relative flex items-center justify-center size-20 rounded-2xl bg-gradient-to-br from-[#0066ff] to-[#00d4ff] border border-white/[0.15]">
            <Codicon className="size-10 text-white" name="hubot" />
          </div>
        </div>

        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-white via-white/90 to-white/70 bg-clip-text text-transparent">
            How can I help you?
          </h1>
          <p className="text-sm text-white/30 mt-2 max-w-md">
            I can research, code, browse, automate, and coordinate across your entire workspace.
            {memoryStats.total > 0 && ` I remember ${memoryStats.total} things about your work.`}
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
          {[
            'Build a SaaS landing page',
            'Research this company',
            'Fix the bug in main.py',
            'Deploy to production',
            'Summarize my GitHub notifications'
          ].map(prompt => (
            <GlassPanel border={false} className="overflow-hidden" glow="none" intensity="light" key={prompt}>
              <span
                className="block px-3 py-1.5 rounded-lg text-[12px] text-white/30 hover:text-white/60 cursor-pointer transition-all"
                onClick={() => setJarvisLeftSection('chat')}
              >
                {prompt}
              </span>
            </GlassPanel>
          ))}
        </div>

        <div className="flex items-center justify-center gap-4 text-[11px] text-white/15">
          <span className="flex items-center gap-1">
            <Codicon className="size-3" name="database" />
            {memoryStats.total} memories
          </span>
          <span className="flex items-center gap-1">
            <Codicon className="size-3" name="hubot" />
            {memoryStats.totalRelations} connections
          </span>
          <span className="flex items-center gap-1">
            <Codicon className="size-3" name="dashboard" />
            {memoryStats.byType.project ?? 0} projects
          </span>
        </div>
      </motion.div>
    </GlassPanel>
    </div>
  )
}

function ConversationalWorkspaceComponent() {
  const [messages, setMessages] = useState<Message[]>([])
  const [activePlan, setActivePlan] = useState<ExecutionPlan | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    initializeMonitoring()
    initializeAutomation()
    seedMemoryGraph()
    assessSystemHealth()
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, activePlan])

  const handleCommand = useCallback(async (command: string) => {
    if (isProcessing) {return}
    setIsProcessing(true)

    const context = buildContextPrompt()

    const userMsg: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: command,
      timestamp: Date.now()
    }

    setMessages(prev => [...prev, userMsg])

    try {
      // Same universal gateway as the MissionControl composer — no second path.
      const result = await submitJarvisCommand(command, {
        inputType: 'text',
        deps: createDesktopCommandDeps(navigate),
        onStepUpdate: (stepId, status, progress, stepResult) => {
          setActivePlan(prev => {
            if (!prev) {
              const plan: ExecutionPlan = {
                id: `plan-${Date.now()}`,
                intent: { type: 'unknown', confidence: 0, entities: {}, context: [], requiresTools: [] },
                steps: [],
                status: 'running',
                startTime: Date.now()
              }

              return plan
            }

            return {
              ...prev,
              steps: prev.steps.map(s =>
                s.id === stepId ? { ...s, status, progress, result: stepResult ?? s.result } : s
              ),
              status: status === 'running' ? 'running' : (
                prev.steps.every(s => s.status === 'completed') ? 'completed' : prev.status
              )
            }
          })
        },
        onThinkingStage: (stage, label) => {
          setJarvisThinkingStage(stage as 'understanding', label)
        }
      })

      const assistantMsg: Message = {
        id: `msg-${Date.now()}-resp`,
        role: 'assistant',
        content: result.response,
        timestamp: Date.now()
      }

      setMessages(prev => [...prev, assistantMsg])
      setActivePlan(null)
      setJarvisThinkingStage('idle', '')
    } catch (err) {
      if (err instanceof ApprovalRequiredError) {
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}-approval`,
          role: 'system',
          content: `Approval required: ${err.message} Reply "allow once" is not supported here — use the MissionControl composer for approvals.`,
          timestamp: Date.now()
        }])
      } else {
        const errorMsg: Message = {
          id: `msg-${Date.now()}-err`,
          role: 'system',
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
          timestamp: Date.now()
        }

        setMessages(prev => [...prev, errorMsg])
      }

      addJarvisNotification({ title: 'Pipeline Error', message: String(err), type: 'error' })
    } finally {
      setIsProcessing(false)
      setTimeout(() => setJarvisThinkingStage('idle', ''), 1000)
    }
  }, [isProcessing, navigate])

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 scrollbar-dt" ref={scrollRef}>
        {messages.length === 0 ? (
          <WelcomeSuggestions />
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            <SystemBanner />

            {activePlan && activePlan.steps.length > 0 && (
              <PlanVisualization plan={activePlan} />
            )}

            <AnimatePresence>
              {messages.map(msg => (
                <motion.div
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  initial={{ opacity: 0, y: 10 }}
                  key={msg.id}
                >
                  <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-[#0066ff]/20 to-[#00d4ff]/20 border border-[#0066ff]/20 text-white/90 backdrop-blur-xl'
                      : msg.role === 'system'
                      ? 'bg-red-500/10 border border-red-500/20 text-red-400/80 backdrop-blur-xl'
                      : 'bg-white/[0.04] border border-white/[0.06] text-white/70 backdrop-blur-xl'
                  }`}>
                    {msg.role === 'assistant' && (
                      <div className="flex items-center gap-1.5 mb-2">
                        <Codicon className="size-3.5 text-[#00d4ff]" name="hubot" />
                        <span className="text-[10px] text-[#00d4ff]/60 font-medium">AetherOS</span>
                        {msg.modelUsed && (
                          <span className="text-[9px] text-white/15 ml-auto">
                            {msg.modelUsed.provider}/{msg.modelUsed.model}
                          </span>
                        )}
                      </div>
                    )}
                    <div className="text-[13px] leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                    <div className="text-[10px] text-white/15 mt-2">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Live thinking indicator */}
      <LiveThinking />

      {/* Command input */}
      <div className="px-6 pb-6 pt-2">
        <CommandInput onCommand={handleCommand} />
      </div>
    </div>
  )
}

export const ConversationalWorkspace = memo(ConversationalWorkspaceComponent)
