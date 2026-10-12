import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusDot } from '@/components/ui/status-dot'
import { Tooltip } from '@/components/ui/tooltip'
import { TooltipContent } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { $busy, $currentModel, $currentProvider, $gatewayState } from '@/store/session'
import { $messages } from '@/store/session'

export function AgentWorkspaceView() {
  const gatewayState = useStore($gatewayState)
  const busy = useStore($busy)
  const messages = useStore($messages)
  const currentModel = useStore($currentModel)
  const currentProvider = useStore($currentProvider)

  const [executionState, setExecutionState] = useState<'idle' | 'running' | 'paused' | 'completed' | 'error'>('idle')
  const [currentStep, setCurrentStep] = useState<number>(0)
  const [totalSteps, setTotalSteps] = useState<number>(0)
  const [planSteps, setPlanSteps] = useState<Array<{ id: number; description: string; tool?: string; target?: string; approved?: boolean }>>([])
  const [artifacts, setArtifacts] = useState<any[]>([])
  const [approvalRequests, setApprovalRequests] = useState<any[]>([])
  const [context, setContext] = useState<any[]>([])
  const [elapsedTime, setElapsedTime] = useState<number>(0)

  // Track start time when agent becomes active
  useEffect(() => {
    if (gatewayState === 'open' && busy) {
      const start = Date.now()

      const timer = setInterval(() => {
        setElapsedTime(Date.now() - start)
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [gatewayState, busy])

  // Update plan steps from messages or gateway state
  useEffect(() => {
    updatePlanFromMessages(messages)
  }, [messages])

  function updatePlanFromMessages(msgList: any[]) {
    // Extract plan steps from assistant messages
    const steps: Array<{ id: number; description: string; tool?: string; target?: string; approved?: boolean }> = []
    
    msgList
      .filter((m: any) => m.role === 'assistant')
      .filter((m: any) => m.content && typeof m.content === 'string')
      .forEach((m: any, i) => {
        // Look for step markers in the content
        const content = m.content
        const stepMatches = content.match(/Step \d+ of \d+:?\s*(.+)/gi)

        if (stepMatches) {
          stepMatches.forEach((match: string, idx: number) => {
            const stepNum = idx + 1
            const description = match.replace(/Step \d+ of \d+:?\s*/i, '').trim()
            steps.push({
              id: stepNum,
              description,
              approved: true // default to approved unless marked otherwise
            })
          })
        }
      })

    setPlanSteps(steps.length > 0 ? steps : [])
  }

  function getStepStatus(stepId: number): 'queued' | 'running' | 'waiting' | 'approved' | 'completed' | 'failed' | 'skipped' | 'cancelled' {
    const step = planSteps.find(s => s.id === stepId)

    return step ? (step.approved !== undefined ? (step.approved ? 'approved' : 'waiting') : 'running') : 'queued'
  }

  // Compute progress based on actual state
  const progress = totalSteps > 0 ? Math.min(100, Math.round((currentStep / totalSteps) * 100)) : 0

  // Human-readable event summaries - never raw technical logs
  const recentEvents = computeRecentEvents(messages)

  function computeRecentEvents(msgList: any[]): Array<{ summary: string; timestamp: number; technical?: string; status: 'success' | 'error' | 'pending' }> {
    const events: Array<{ summary: string; timestamp: number; technical?: string; status: 'success' | 'error' | 'pending' }> = []

    msgList
      .filter((m: any) => m.role === 'tool')
      .forEach((m: any) => {
        const name = m.name || 'unknown'
        const result = m.result || m.content || ''
        
        let summary: string
        let technical: string | undefined
        let status: 'success' | 'error' | 'pending' = 'pending'

        if (m.status === 'completed') {
          status = 'success'
          summary = formatToolResultSummary(name, result)
          technical = formatToolTechnicalDetails(name, result)
        } else if (m.status === 'error') {
          status = 'error'
          summary = `Error in ${name}`
          technical = m.error || 'Unknown error'
        } else {
          summary = `Running ${name}`
          status = 'pending'
        }

        events.push({ summary, timestamp: m.timestamp || Date.now(), technical, status })
      })

    // Sort by timestamp, newest first
    return events.sort((a, b) => b.timestamp - a.timestamp).slice(0, 10)
  }

  function formatToolResultSummary(tool: string, result: any): string {
    if (!result) {return `${tool} completed`}
    
    const r = typeof result === 'string' ? JSON.parse(result) : result
    
    if (typeof r === 'object') {
      if (r.success) {return `${tool}: ${r.success}`}

      if (r.data) {
        if (typeof r.data === 'string' && r.data.length > 100) {
          return `${tool}: ${r.data.substring(0, 100)}...`
        }

        return `${tool}: ${JSON.stringify(r.data).substring(0, 100)}...`
      }

      return `${tool}: completed`
    }
    
    return `${tool}: ${String(r).substring(0, 80)}`
  }

  function formatToolTechnicalDetails(tool: string, result: any): string | undefined {
    if (!result) {return undefined}
    
    const r = typeof result === 'string' ? JSON.parse(result) : result
    
    if (typeof r === 'object' && r !== null) {
      // Strip out large data fields for UI display
      const display = { ...r }

      if (display.data && typeof display.data === 'string') {
        display.data = display.data.substring(0, 200) + (display.data.length > 200 ? '...' : '')
      }

      if (display.result && typeof display.result === 'string') {
        display.result = display.result.substring(0, 200) + (display.result.length > 200 ? '...' : '')
      }

      return JSON.stringify(display)
    }
    
    return undefined
  }

  // Security state display
  const securityIndicators = [
    { name: 'Sandbox', status: gatewayState === 'open' ? 'active' : 'inactive', critical: false },
    { name: 'Approval', status: approvalRequests.length > 0 ? 'pending' : 'none', critical: approvalRequests.length > 0 },
    { name: 'Browser', status: 'active', critical: false },
    { name: 'Terminal', status: 'active', critical: false },
  ]

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <header className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) pb-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {busy ? 'AetherOS' : 'Agent Workspace'}
            </h1>
            <p className="mt-1 text-sm text-(--ui-text-tertiary)">
              {busy ? 'AI Agent Execution' : ''}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <StatusDot size="sm" status={busy ? 'running' : 'idle'} />
              <span className="text-xs font-medium text-(--ui-text-tertiary)">
                {busy ? 'Working' : 'Idle'}
              </span>
            </div>
            <Button
              aria-label="Open plan view"
              className="p-1.5 rounded-hover:bg-(--ui-surface-hover)"
              onClick={() => {}}
              size="icon"
            >
              <span className="codicon codicon-list" />
            </Button>
            <Button
              aria-label="Open context"
              className="p-1.5 rounded-hover:bg-(--ui-surface-hover)"
              onClick={() => {}}
              size="icon"
            >
              <span className="codicon codicon-folder" />
            </Button>
          </div>
        </header>

        {/* Live Execution Visualization */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Live Execution</h2>

          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-(--ui-text-tertiary) mb-1">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-(--ui-surface) overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  progress > 0 ? 'bg-(--ui-accent)' : 'bg-(--ui-disabled)',
                  'w-0'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Current step */}
          {totalSteps > 0 && (
            <div className="mb-4 p-3 bg-(--ui-surface-secondary) rounded">
              <div className="flex items-center gap-2 text-(--ui-text-tertiary)">
                <span className="codicon codicon-arrow-down text-[10px]" />
                <span>Step {currentStep + 1} of {totalSteps}</span>
              </div>
              <p className="mt-1 text-sm">{planSteps[currentStep]?.description || 'Loading step...'}</p>
            </div>
          )}

          {/* Security indicators */}
          <div className="grid grid-cols-4 gap-2 text-xs mb-4">
            {securityIndicators.map((ind, i) => (
              <div className={cn(
                'flex items-center gap-1 px-2 py-1 rounded',
                ind.critical ? 'bg-red-500/10 text-red-400' : 'bg-(--ui-surface-secondary) text-(--ui-text-tertiary)'
              )} key={i}>
                <span className="codicon codicon-dot" />
                <span>{ind.name}</span>
                <span className={`text-(--ui-accent) ${ind.status === 'pending' ? 'animate-pulse' : ''}`} />
              </div>
            ))}
          </div>
        </Card>

        {/* Plan View */}
        {planSteps.length > 0 && (
          <Card className="p-4 sm:p-6">
            <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Execution Plan</h2>
            <div className="space-y-1">
              {planSteps.map((step, i) => (
                <div
                  className={cn(
                    'flex items-center gap-2 p-2 rounded',
                    currentStep === i ? 'bg-(--ui-surface-secondary)' : ''
                  )}
                  key={step.id}
                >
                  <span className="font-medium text-(--ui-text)">{step.id}</span>
                  <span className="flex-1 truncate">{step.description}</span>
                  <StatusDot
                    className="text-[8px]"
                    size="xs"
                    status={getStepStatus(step.id)}
                  />
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Context & Artifacts */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <ArtifactsPanel artifacts={artifacts} setArtifacts={setArtifacts} />
          <ContextPanel context={context} setContext={setContext} />
        </div>

        {/* Approvals Center */}
        {approvalRequests.length > 0 && (
          <ApprovalCenterPanel approvalRequests={approvalRequests} onApprove={() => {}} onDeny={() => {}} />
        )}

        {/* Recent Events / Tool Activity */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Recent Activity</h2>
          <div className="h-48 overflow-auto text-xs">
            {recentEvents.map((event, i) => (
              <div
                className={cn(
                  'flex items-center gap-2 px-2 py-1.5 border-b border-(--ui-border) last:border-0',
                  event.status === 'success' ? 'text-(--ui-text)' : event.status === 'error' ? 'text-red-400' : 'text-(--ui-text-tertiary)'
                )}
                key={i}
              >
                <StatusDot size="xs" status={event.status} />
                <span className="truncate flex-1">{event.summary}</span>
                {event.technical && (
                  <Tooltip>
                    <TooltipContent>{event.technical}</TooltipContent>
                  </Tooltip>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </ScrollArea>
  )
}

function ArtifactsPanel({ artifacts, setArtifacts }: { artifacts: any[]; setArtifacts: any }) {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Artifacts</h3>
      {artifacts.length === 0 ? (
        <div className="text-(--ui-text-tertiary) py-4">
          No artifacts yet. Artifacts will appear as the agent creates files, images, reports, etc.
        </div>
      ) : (
        artifacts.map((artifact, i) => (
          <div
            className="flex items-center gap-2 px-2 py-1.5 text-(--ui-text-tertiary) hover:bg-(--ui-surface-hover) rounded cursor-pointer"
            key={i}
          >
            <Badge variant="muted">{artifact.type || 'artifact'}</Badge>
            <span className="truncate flex-1 max-w-xs">{artifact.name || 'Untitled'}</span>
            <span className="text-[10px]">{artifact.size ? `${artifact.size} KB` : ''}</span>
          </div>
        ))
      )}
    </Card>
  )
}

function ContextPanel({ context, setContext }: { context: any[]; setContext: any }) {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Context</h3>
      <div className="h-48 overflow-auto text-xs">
        {context.length === 0 ? (
          <div className="py-4 text-(--ui-text-tertiary)">
            No saved context. Context is captured from previous sessions to inform future tasks.
          </div>
        ) : (
          context.map((c, i) => (
            <div
              className="flex items-center gap-2 px-2 py-1.5 text-(--ui-text-tertiary) hover:bg-(--ui-surface-hover) rounded cursor-pointer"
              key={i}
            >
              <span className="codicon codicon-info-small" />
              <span className="truncate flex-1 max-w-xs line-clamp-1">{c.title || c.topic || 'Context'}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}

function ApprovalCenterPanel({ approvalRequests, onApprove, onDeny }: {
  approvalRequests: any[]
  onApprove: any
  onDeny: any
}) {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Approval Required</h3>
      <div className="space-y-2 h-48 overflow-auto">
        {approvalRequests.length === 0 ? (
          <div className="py-4 text-(--ui-text-tertiary)">
            No pending approvals.
          </div>
        ) : (
          approvalRequests.map((req, i) => (
            <div
              className="flex items-center gap-2 px-2 py-1.5 text-xs border-b border-(--ui-border) last:border-0"
              key={i}
            >
              <div className="flex-1 truncate">{req.action || 'Unnamed action'}</div>
              <div className="text-(--ui-text-tertiary)">
                <button
                  className="text-emerald-400 hover:text-emerald-300"
                  onClick={() => onApprove(req.id)}
                >
                  ✓
                </button>
                <button
                  className="text-red-400 hover:text-red-300"
                  onClick={() => onDeny(req.id)}
                >
                  ✗
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  )
}