import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusDot } from '@/components/ui/status-dot'
import { Tooltip } from '@/components/ui/tooltip'
import { TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { $busy, $currentModel, $currentProvider, $gatewayState } from '@/store/session'
import { $messages } from '@/store/session'

export function ComputerUseView() {
  const gatewayState = useStore($gatewayState)
  const busy = useStore($busy)
  const messages = useStore($messages)
  const currentModel = useStore($currentModel)
  const currentProvider = useStore($currentProvider)

  const [isPreviewing, setIsPreviewing] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [targetWindow, setTargetWindow] = useState<'any' | 'active' | 'focus'>('any')
  const [actionTimeline, setActionTimeline] = useState<Array<{ id: number; action: string; timestamp: number; safeSummary: string; technical?: string }>>([])
  const [securityState, setSecurityState] = useState<'protected' | 'approval-required' | 'restricted' | 'blocked' | 'offline'>('protected')

  // Security indicators
  const securityIndicators = [
    { name: 'Sandbox', status: 'active', critical: false },
    { name: 'Approval', status: 'none', critical: false },
    { name: 'Clipboard', status: 'active', critical: false },
    { name: 'File System', status: 'active', critical: false },
    { name: 'Terminal', status: 'active', critical: false },
  ]

  // Human-readable action summaries - never raw chain-of-thought
  const recentActions = computeRecentActions(messages)

  function computeRecentActions(msgList: any[]): Array<{ id: number; action: string; timestamp: number; safeSummary: string; technical?: string }> {
    const actions: Array<{ id: number; action: string; timestamp: number; safeSummary: string; technical?: string }> = []

    msgList
      .filter((m: any) => m.role === 'tool')
      .forEach((m: any, i) => {
        const name = m.name || 'unknown'
        const result = m.result || m.content || ''

        let safeSummary: string
        let technical: string | undefined

        // Generate safe user-facing summaries, never internal reasoning
        if (name.includes('mouse') || name.includes('click')) {
          safeSummary = 'Clicking interface element'
          technical = m.details || undefined
        } else if (name.includes('keyboard') || name.types) {
          safeSummary = 'Sending keystrokes'
          technical = m.details || undefined
        } else if (name.includes('browser') || name.includes('page')) {
          safeSummary = `Viewing ${m.target || 'web page'}`
          technical = m.url || undefined
        } else if (name.includes('terminal') || name.exec) {
          safeSummary = 'Executing command'
          technical = m.command || undefined
        } else if (name.includes('file') || name.read || name.write) {
          safeSummary = `Operating on ${m.target || 'file'}`
          technical = m.path || undefined
        } else {
          safeSummary = `Running ${name}`
          technical = undefined
        }

        actions.push({
          id: i,
          action: name,
          timestamp: m.timestamp || Date.now(),
          safeSummary,
          technical,
        })
      })

    return actions
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, 10)
  }

  // Toggle pause
  const togglePause = () => {
    setIsPaused(prev => !prev)

    // Notify backend to pause/resume
    if (gatewayState === 'open') {
      // In a full impl, this would IPC to the backend
    }
  }

  // Stop execution
  const stopExecution = () => {
    setIsPreviewing(false)
    setIsPaused(false)
    setSecurityState('blocked')
    // In a full impl, this would IPC to the backend to stop
  }

  // elapsed time when agent is active
  useEffect(() => {
    if (gatewayState === 'open' && busy) {
      const start = Date.now()

      const timer = setInterval(() => {
        // elapsed time is tracked via CSS/visual, not state poll
      }, 1000)

      return () => clearInterval(timer)
    }
  }, [gatewayState, busy])

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <header className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) pb-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {busy ? 'Computer Use' : 'AetherOS'}
            </h1>
            <p className="mt-1 text-sm text-(--ui-text-tertiary)">
              {busy ? 'Control your desktop' : ''}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <StatusDot size="sm" status={busy ? 'running' : 'idle'} />
              <span className="text-xs font-medium text-(--ui-text-tertiary)">
                {busy ? 'Active' : 'Idle'}
              </span>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <button aria-label="Pause" className="p-2 rounded hover:bg-(--ui-surface-secondary)">
                  <span className="codicon codicon-pause" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Pause agent execution
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button aria-label="Stop" className="p-2 rounded hover:bg-(--ui-surface-secondary)">
                  <span className="codicon codicon-stop" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Stop current operation
              </TooltipContent>
            </Tooltip>
          </div>
        </header>

        {/* Live Screen Preview */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Live Screen</h2>

          <div className="relative h-64 w-full rounded-lg overflow-hidden bg-(--ui-surface) mb-4">
            {isPreviewing ? (
              <div className="absolute inset-0 bg-(--ui-surface-secondary) flex items-center justify-center text-(--ui-text-tertiary)">
                <span className="codicon codicon-video" style={{ fontSize: '2rem' }} />
                <span>Previewing screen...</span>
              </div>
            ) : (
              <div className="h-full w-full bg-(--ui-surface-secondary) rounded-lg">
                {/* Screen preview would be rendered here via IPC or canvas */}
                <div className="h-full w-full flex items-center justify-center text-(--ui-text-tertiary)">
                  <span className="codicon codicon-display" style={{ fontSize: '2rem' }} />
                  <span>Screen preview</span>
                </div>
              </div>
            )}
          </div>

          {/* Cursor position indicator */}
          {isPreviewing && (
            <div className="absolute inset-0 pointer-events-none">
              <div className="w-2 h-2 rounded-full bg-(--ui-accent) transform origin-top-left" />
            </div>
          )}

          {/* Window/app identity */}
          <div className="mt-3 pt-3 border-t border-(--ui-border) flex flex-col gap-1 text-xs text-(--ui-text-tertiary)">
            <span>Target: {targetWindow || 'Any window'}</span>
            <span>Mode: {isPaused ? 'Paused' : 'Active'}</span>
          </div>
        </Card>

        {/* Action Timeline */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Action Timeline</h2>

          <div className="h-48 overflow-auto text-xs">
            {actionTimeline.length === 0 ? (
              <div className="py-4 text-(--ui-text-tertiary)">
                No actions recorded yet. Agent activity will appear here as operations complete.
              </div>
            ) : (
              actionTimeline.map((action, i) => (
                <div
                  className={cn(
                    'flex items-center gap-2 px-2 py-1.5 border-b border-(--ui-border) last:border-0',
                    i % 2 === 0 ? 'bg-(--ui-surface)' : ''
                  )}
                  key={action.id}
                >
                  <StatusDot size="xs" status="success" />
                  <span className="truncate flex-1 max-w-xs">{action.safeSummary}</span>
                  {action.technical && (
                    <Tooltip>
                      <TooltipContent>{action.technical}</TooltipContent>
                    </Tooltip>
                  )}
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Security State */}
        <Card className="p-4 sm:p-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Security State</h2>

          <div className="grid grid-cols-2 gap-2 text-xs mb-4">
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

          <div>
            <span className="font-medium">Current State:</span>
            <Badge
              variant={securityState === 'blocked' ? 'destructive' : securityState === 'approval-required' ? 'warn' : 'default'}
            >
              {securityState}
            </Badge>
          </div>
        </Card>

        {/* Control Bar */}
        <Card className="p-4 sm:p-6 border-t border-(--ui-stroke-tertiary)">
          <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary) mb-3">Control</h2>

          <div className="flex gap-3">
            <Button
              className={cn('flex-1', isPaused ? 'bg-(--ui-accent)' : 'bg-(--ui-surface) text-(--ui-text)')}
              disabled={!isPreviewing}
              onClick={togglePause}
            >
              {isPaused ? 'Resume' : 'Pause'}
            </Button>
            <Button
              className={cn('flex-1', 'bg-red-500/20 text-red-400')}
              onClick={stopExecution}
            >
              Stop
            </Button>
          </div>
        </Card>
      </div>
    </ScrollArea>
  )
}