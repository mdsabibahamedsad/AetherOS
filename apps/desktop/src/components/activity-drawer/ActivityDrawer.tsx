import { useStore } from '@nanostores/react'
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { sessionRoute } from '@/app/routes'
import { sessionTitle } from '@/lib/chat-runtime'
import { $activityDrawerOpen, closeActivityDrawer, openActivityDrawer } from '@/store/activity-drawer'
import { $allApprovalRequests } from '@/store/prompts'
import { $backgroundTaskCount } from '@/store/system'
import {
  $activeSessionId,
  $sessions,
  $workingSessionIds,
  $gatewayState,
} from '@/store/session'
import { $gateway } from '@/store/gateway'

export function ActivityDrawer() {
  const isOpen = useStore($activityDrawerOpen)
  const navigate = useNavigate()
  const drawerRef = useRef<HTMLDivElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  const approvals = useStore($allApprovalRequests)
  const backgroundTasks = useStore($backgroundTaskCount)
  const sessions = useStore($sessions)
  const workingIds = useStore($workingSessionIds)
  const activeSessionId = useStore($activeSessionId)
  const gatewayState = useStore($gatewayState)
  const gateway = useStore($gateway)

  const pendingApprovalSessions = Object.keys(approvals)
  const runningSessions = sessions.filter(s => workingIds.includes(s.id))
  const gatewayConnected = gatewayState === 'open' || gatewayState === 'connected'

  const stopSession = async (sessionId: string) => {
    if (!gateway) return
    try {
      await gateway.request('session.interrupt', { session_id: sessionId })
    } catch (e) {
      console.error(`Failed to stop session ${sessionId.slice(0, 8)}`, e)
    }
  }

  const handleApproval = (sessionId: string, approve: boolean) => {
    if (!gateway) return
    gateway.request('approval.respond', { session_id: sessionId, approve })
  }

  // Focus management
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
      drawerRef.current?.focus()
    } else if (previousActiveElement.current) {
      previousActiveElement.current.focus()
    }
  }, [isOpen])

  // Trap focus within drawer
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeActivityDrawer()
        return
      }

      if (e.key === 'Tab') {
        const focusableElements = drawerRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (!focusableElements || focusableElements.length === 0) return

        const firstElement = focusableElements[0]
        const lastElement = focusableElements[focusableElements.length - 1]

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault()
          lastElement.focus()
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault()
          firstElement.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[800] flex items-center justify-end"
      onClick={closeActivityDrawer}
      role="dialog"
      aria-modal="true"
      aria-label="Activity"
    >
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        ref={drawerRef}
        tabIndex={-1}
        className="relative w-full max-w-md h-full bg-(--ui-bg-secondary) border-l border-(--ui-stroke-tertiary) shadow-[0_4px_12px_rgb(0_0_0/0.32),0_16px_48px_rgb(0_0_0/0.28)] flex flex-col animate-slide-in-right"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) p-3">
          <h2 className="text-sm font-semibold">Activity</h2>
          <Button
            aria-label="Close activity drawer"
            className="size-7"
            onClick={closeActivityDrawer}
            size="icon-sm"
            variant="ghost"
          >
            <Codicon name="close" size="1rem" />
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-3 space-y-4">
            {/* System Status */}
            <div className="flex items-center gap-2 p-2 rounded-lg bg-(--ui-bg-tertiary)/50">
              <span
                className={cn(
                  'size-2 rounded-full',
                  gatewayConnected ? 'bg-emerald-500' : 'bg-amber-500'
                )}
              />
              <span className="text-sm font-medium">
                {gatewayConnected ? 'Connected' : 'Disconnected'}
              </span>
              <span className="ml-auto text-xs text-(--ui-text-tertiary)">
                Gateway
              </span>
            </div>

            {/* Active Work */}
            {runningSessions.length > 0 && (
              <section>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary)">
                    Active Work
                  </h3>
                  <span className="text-xs text-(--ui-text-tertiary)">{runningSessions.length} running</span>
                </div>
                <div className="space-y-1.5">
                  {runningSessions.map(session => (
                    <Card key={session.id} className="p-3">
                      <div className="flex items-start gap-2">
                        <span
                          className={cn(
                            'size-2 shrink-0 rounded-full mt-1.5',
                            session.id === activeSessionId ? 'bg-blue-500' : 'bg-emerald-500'
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium">{sessionTitle(session)}</div>
                          <div className="truncate font-mono text-xs text-(--ui-text-tertiary)">{session.id}</div>
                        </div>
                        <Button
                          onClick={() => navigate(sessionRoute(session.id))}
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2"
                        >
                          Open
                        </Button>
                      </div>
                      <div className="mt-2 flex gap-1">
                        <Button
                          onClick={() => stopSession(session.id)}
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-xs"
                        >
                          <Codicon name="debug-stop" size="0.75rem" className="mr-1" />
                          Stop
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </section>
            )}

            {/* Approvals */}
            {pendingApprovalSessions.length > 0 && (
              <section>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary)">
                    Approvals Waiting
                  </h3>
                  <span className="text-xs text-amber-500">{pendingApprovalSessions.length} pending</span>
                </div>
                <div className="space-y-1.5">
                  {pendingApprovalSessions.map(sessionId => {
                    const approval = approvals[sessionId]
                    const session = sessions.find(s => s.id === sessionId)
                    return (
                      <Card key={sessionId} className="p-3 border-amber-500/30 bg-amber-500/5">
                        <div className="flex items-center gap-2">
                          <Codicon name="shield" className="text-amber-500" size="1rem" />
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-medium">Approval Required</div>
                            <div className="truncate font-mono text-xs text-(--ui-text-tertiary)">
                              {session ? sessionTitle(session) : sessionId}
                            </div>
                          </div>
                        </div>
                        <div className="mt-2 flex gap-2">
                          <Button
                            onClick={() => handleApproval(sessionId, true)}
                            size="sm"
                            variant="outline"
                            className="flex-1 h-6 px-2"
                          >
                            Allow
                          </Button>
                          <Button
                            onClick={() => handleApproval(sessionId, false)}
                            size="sm"
                            variant="outline"
                            className="flex-1 h-6 px-2 border-red-500/30 text-red-500 hover:bg-red-500/10"
                          >
                            Deny
                          </Button>
                        </div>
                      </Card>
                    )
                  })}
                </div>
              </section>
            )}

            {/* Background Tasks */}
            {backgroundTasks > 0 && (
              <section>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-(--ui-text-tertiary) mb-2">
                  Background Tasks
                </h3>
                <Card className="p-3">
                  <div className="flex items-center gap-2">
                    <Codicon name="checklist" className="text-(--ui-text-tertiary)" size="1rem" />
                    <span className="text-sm">{backgroundTasks} task{backgroundTasks === 1 ? '' : 's'} running</span>
                    <Button
                      onClick={() => navigate('/tasks')}
                      size="sm"
                      variant="ghost"
                      className="ml-auto h-6 px-2"
                    >
                      View All
                    </Button>
                  </div>
                </Card>
              </section>
            )}

            {/* Empty State */}
            {runningSessions.length === 0 && pendingApprovalSessions.length === 0 && backgroundTasks === 0 && (
              <div className="py-8 text-center">
                <Codicon name="check-all" size="2rem" className="mx-auto mb-2 text-emerald-500" />
                <p className="text-sm font-medium">All caught up</p>
                <p className="mt-1 text-xs text-(--ui-text-tertiary)">
                  No active work, approvals, or background tasks.
                </p>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t border-(--ui-stroke-tertiary) p-2">
          <Button
            onClick={() => navigate('/tasks')}
            className="w-full"
            size="sm"
            variant="outline"
          >
            <Codicon name="checklist" size="0.875rem" className="mr-1" />
            Open Tasks
          </Button>
        </div>
      </div>
    </div>
  )
}

export { openActivityDrawer, closeActivityDrawer }