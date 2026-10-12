import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { addActivityEvent } from '@/store/dashboard'

import { healthEngine } from '../../../engine/self-healing/health-engine'
import { type RepairAction, type RepairLevel, repairSystem } from '../../../engine/self-healing/repair-system'

const LEVEL_LABELS: Record<RepairLevel, string> = { quick: 'Quick', full: 'Full', deep: 'Deep' }

export function AutoRepairPanel() {
  const [running, setRunning] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, { success: boolean; message: string }>>({})
  const [confirmReset, setConfirmReset] = useState(false)

  const actions = repairSystem.getAllActions()
  const isBusy = repairSystem.isBusy()

  async function handleRun(action: RepairAction) {
    setRunning(action.id)
    setResults(prev => ({ ...prev, [action.id]: { success: false, message: 'Running…' } }))
    const result = await repairSystem.run(action.id)
    setResults(prev => ({ ...prev, [action.id]: { success: result.success, message: result.message } }))
    setRunning(null)

    addActivityEvent({
      id: `repair-${action.id}-${Date.now()}`,
      type: 'system',
      message: `Auto-repair "${action.name}": ${result.success ? 'succeeded' : 'failed'} — ${result.message}`,
      timestamp: Date.now(),
      status: result.success ? 'success' : 'error'
    })
  }

  async function handleRunAllHealthChecks() {
    setRunning('__all_checks__')
    await healthEngine.runAllChecks()
    setRunning(null)
  }

  const healthActions = actions.filter(a => a.level === 'quick')
  const systemActions = actions.filter(a => a.level === 'full' || a.level === 'deep')

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Auto-Repair</CardTitle>
          <Button disabled={isBusy} onClick={handleRunAllHealthChecks} size="sm" variant="outline">
            {running === '__all_checks__' ? 'Checking…' : 'Run All Checks'}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="mb-3">
            <div className="mb-2 text-[0.625rem] font-medium uppercase tracking-widest text-(--ui-text-tertiary)">Quick Repairs</div>
            <div className="space-y-1">
              {healthActions.map(action => (
                <RepairActionRow
                  action={action}
                  isBusy={isBusy}
                  key={action.id}
                  onRun={() => handleRun(action)}
                  result={results[action.id]}
                  running={running === action.id}
                />
              ))}
            </div>
          </div>
          <div>
            <div className="mb-2 text-[0.625rem] font-medium uppercase tracking-widest text-(--ui-text-tertiary)">System Actions</div>
            <div className="space-y-1">
              {systemActions.map(action => {
                if (action.id === 'reset-all') {
                  return (
                    <RepairActionRow
                      action={action}
                      destructive
                      isBusy={isBusy}
                      key={action.id}
                      onRun={() => setConfirmReset(true)}
                      result={results[action.id]}
                      running={running === action.id}
                    />
                  )
                }

                return (
                  <RepairActionRow
                    action={action}
                    isBusy={isBusy}
                    key={action.id}
                    onRun={() => handleRun(action)}
                    result={results[action.id]}
                    running={running === action.id}
                  />
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        confirmLabel="Factory Reset"
        description="This will reset all application state including config, workspaces, extensions, and preferences. This action cannot be undone."
        destructive
        onClose={() => setConfirmReset(false)}
        onConfirm={async () => {
          setConfirmReset(false)
          await handleRun(repairSystem.getAction('reset-all')!)
        }}
        open={confirmReset}
        title="Factory Reset?"
      />
    </>
  )
}

interface RepairActionRowProps {
  action: RepairAction
  isBusy: boolean
  onRun: () => void
  result?: { success: boolean; message: string }
  running: boolean
  destructive?: boolean
}

function RepairActionRow({ action, isBusy, onRun, result, running, destructive }: RepairActionRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{action.name}</span>
          <span className="rounded bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[0.625rem] text-(--ui-text-tertiary)">
            {LEVEL_LABELS[action.level]}
          </span>
        </div>
        <div className="truncate text-xs text-(--ui-text-tertiary)">{action.description}</div>
        {result && !running && (
          <div className={`mt-0.5 text-[0.625rem] ${result.success ? 'text-emerald-500' : 'text-red-500'}`}>
            {result.message}
          </div>
        )}
      </div>
      <Button disabled={isBusy} onClick={onRun} size="sm" variant={destructive ? 'destructive' : 'outline'}>
        {running ? 'Running…' : 'Run'}
      </Button>
    </div>
  )
}
