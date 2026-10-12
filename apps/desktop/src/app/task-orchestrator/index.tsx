import { useStore } from '@nanostores/react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import {
  $currentExecutionState, $currentPlan, $orchestrator,
  $pendingApprovals, $runningAgentActivities,
  createPlan, removePlan, setCurrentPlan,
} from '@/store/task-orchestrator'

import { AgentActivityFeed } from './agent-activity'
import { ApprovalPanel } from './approval-panel'
import { CheckpointView } from './checkpoint-view'
import { ExecutionGraphView } from './execution-graph'
import { PlanView } from './plan-view'

type TabId = 'overview' | 'plan' | 'graph' | 'activity' | 'checkpoints' | 'approvals'

const TABS: { id: TabId; label: string; badge?: (state: ReturnType<typeof $orchestrator.get>) => number }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'plan', label: 'Plan' },
  { id: 'graph', label: 'Graph' },
  { id: 'activity', label: 'Activity' },
  { id: 'checkpoints', label: 'Checkpoints' },
  { id: 'approvals', label: 'Approvals', badge: s => s.approvalRequests.filter(r => r.status === 'pending').length },
]

export function TaskOrchestrator() {
  const state = useStore($orchestrator)
  const currentPlan = useStore($currentPlan)
  const executionState = useStore($currentExecutionState)
  const runningAgents = useStore($runningAgentActivities)
  const pendingApprovals = useStore($pendingApprovals)
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [newGoal, setNewGoal] = useState('')
  const [showNewPlan, setShowNewPlan] = useState(false)

  const stats = useMemo(() => {
    const all = state.plans

    const active = all.filter(p => {
      const es = state.executionStates[p.id]

      return es && !es.cancelled && es.completedTasks.length > 0
    })

    return {
      total: all.length,
      active: active.length,
      running: runningAgents.length,
      pendingApprovals: pendingApprovals.length,
      totalCost: all.reduce((sum, p) => sum + p.estimatedCost, 0),
    }
  }, [state.plans, state.executionStates, runningAgents.length, pendingApprovals.length])

  const handleCreatePlan = () => {
    if (newGoal.trim()) {
      createPlan(newGoal.trim())
      setNewGoal('')
      setShowNewPlan(false)
      setActiveTab('plan')
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div>
          <h2 className="text-lg font-semibold">Task Orchestrator</h2>
          <p className="text-xs text-muted-foreground">Autonomous agent orchestration and task management</p>
        </div>
        <div className="flex items-center gap-2">
          {state.offlineMode && <Badge className="text-yellow-600 border-yellow-300" variant="outline">Offline</Badge>}
          <Button onClick={() => setShowNewPlan(true)} size="sm">New Plan</Button>
        </div>
      </div>

      {showNewPlan && (
        <div className="border-b p-4">
          <div className="mx-auto max-w-lg space-y-3">
            <Label>Describe your objective</Label>
            <Input
              onChange={e => setNewGoal(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreatePlan()}
              placeholder="e.g., Research AI providers, compare pricing, create a report, and save it as PDF"
              value={newGoal}
            />
            <div className="flex justify-end gap-2">
              <Button onClick={() => setShowNewPlan(false)} size="sm" variant="outline">Cancel</Button>
              <Button onClick={handleCreatePlan} size="sm">Create & Analyze</Button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-4 gap-3 border-b px-6 py-3">
        <StatCard label="Total Plans" value={stats.total} />
        <StatCard color="text-blue-600" label="Active Agents" value={stats.running} />
        <StatCard color="text-yellow-600" label="Pending Approvals" value={stats.pendingApprovals} />
        <StatCard color="text-green-600" label="Est. Total Cost" value={`$${stats.totalCost.toFixed(2)}`} />
      </div>

      <div className="flex gap-1 border-b px-6">
        {TABS.map(tab => {
          const badge = tab.badge?.(state)

          return (
            <button
              className={cn(
                'relative px-4 py-2 text-sm font-medium transition-colors',
                activeTab === tab.id ? 'text-foreground border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'
              )}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              {tab.label}
              {badge !== undefined && badge > 0 && (
                <span className="ml-1.5 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">{badge}</span>
              )}
            </button>
          )
        })}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'overview' && (
          <OverviewView
            activities={state.agentActivities}
            currentPlanId={state.currentPlanId}
            executionStates={state.executionStates}
            onRemovePlan={removePlan}
            onSelectPlan={id => { setCurrentPlan(id); setActiveTab('plan') }}
            plans={state.plans}
          />
        )}
        {activeTab === 'plan' && (
          <PlanView
            executionState={executionState}
            plan={currentPlan}
          />
        )}
        {activeTab === 'graph' && (
          <ExecutionGraphView
            executionState={executionState}
            plan={currentPlan}
          />
        )}
        {activeTab === 'activity' && (
          <AgentActivityFeed
            activities={state.agentActivities}
          />
        )}
        {activeTab === 'checkpoints' && (
          <CheckpointView
            checkpoints={state.checkpoints}
            planId={state.currentPlanId}
          />
        )}
        {activeTab === 'approvals' && (
          <ApprovalPanel
            onRespond={(id, resp) => {
              const { respondApproval } = require('@/store/task-orchestrator')
              respondApproval(id, resp)
            }}
            requests={state.approvalRequests}
          />
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg border p-3 text-center">
      <div className={cn('text-xl font-bold', color ?? 'text-foreground')}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}

function OverviewView({
  plans, executionStates, activities, currentPlanId, onSelectPlan, onRemovePlan
}: {
  plans: ReturnType<typeof $orchestrator.get>['plans']
  executionStates: ReturnType<typeof $orchestrator.get>['executionStates']
  activities: ReturnType<typeof $orchestrator.get>['agentActivities']
  currentPlanId: string | null
  onSelectPlan: (id: string) => void
  onRemovePlan: (id: string) => void
}) {
  const recentActivities = activities.slice(-20).reverse()

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">Recent Plans</h3>
        {plans.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No plans yet. Create one to get started.</p>
        ) : (
          <div className="space-y-2">
            {plans.slice(-10).reverse().map(plan => {
              const es = executionStates[plan.id]
              const isActive = plan.id === currentPlanId
              const status = es?.cancelled ? 'cancelled' : es?.completedTasks.length === plan.subtasks.length ? 'completed' : es ? 'running' : 'pending'

              return (
                <div className={cn('flex items-center justify-between rounded-lg border p-3 transition-colors', isActive && 'border-primary/50 bg-primary/5')} key={plan.id}>
                  <button className="flex-1 text-left" onClick={() => onSelectPlan(plan.id)} type="button">
                    <div className="flex items-center gap-2">
                      <StatusDot status={status} />
                      <span className="font-medium text-sm truncate">{plan.goal.slice(0, 80)}</span>
                      <RiskBadge level={plan.riskLevel} />
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {plan.subtasks.length} tasks · {plan.estimatedTime}s est. · ${plan.estimatedCost.toFixed(2)}
                    </div>
                  </button>
                  <Button className="text-destructive" onClick={() => onRemovePlan(plan.id)} size="sm" variant="ghost">
                    Remove
                  </Button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {recentActivities.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">Recent Activity</h3>
          <div className="space-y-1">
            {recentActivities.slice(0, 10).map(a => (
              <div className="flex items-center gap-2 text-sm" key={a.agentId + a.startedAt}>
                <ActivityStatusDot status={a.status} />
                <span className="font-medium">{a.name}</span>
                <span className="text-muted-foreground">{a.message || a.status}</span>
                <span className="text-xs text-muted-foreground">{a.model}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-400', running: 'bg-blue-500 animate-pulse', completed: 'bg-green-500',
    failed: 'bg-red-500', cancelled: 'bg-gray-400', paused: 'bg-yellow-500'
  }

  return <span className={cn('h-2 w-2 shrink-0 rounded-full', colors[status] ?? 'bg-gray-400')} />
}

function ActivityStatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: 'bg-gray-400', running: 'bg-blue-500 animate-pulse', thinking: 'bg-purple-500 animate-pulse',
    tool_called: 'bg-orange-500', waiting: 'bg-yellow-500', completed: 'bg-green-500',
    failed: 'bg-red-500', retrying: 'bg-orange-500 animate-pulse'
  }

  return <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', colors[status] ?? 'bg-gray-400')} />
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-500/10 text-green-600 border-green-500/30',
    medium: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/30',
    high: 'bg-orange-500/10 text-orange-600 border-orange-500/30',
    critical: 'bg-red-500/10 text-red-600 border-red-500/30'
  }

  return <Badge className={cn('text-[10px] h-5 px-1.5', colors[level] ?? '')} variant="outline">{level}</Badge>
}
