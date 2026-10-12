import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ApprovalRequest } from '@/store/task-orchestrator'

interface Props {
  requests: ApprovalRequest[]
  onRespond: (id: string, response: 'approved' | 'denied') => void
}

const ACTION_LABELS: Record<string, string> = {
  dangerous_action: 'Dangerous Action',
  destructive_action: 'Destructive Action',
  sensitive_data: 'Sensitive Data',
  external_communication: 'External Communication',
  payment: 'Payment',
  account_change: 'Account Change',
  permission_escalation: 'Permission Escalation',
  uncertain_decision: 'Uncertain Decision',
  file_write: 'File Write',
  file_delete: 'File Delete',
  network_access: 'Network Access',
  code_execution: 'Code Execution',
}

const ACTION_EMOJIS: Record<string, string> = {
  dangerous_action: '⚠️', destructive_action: '💥', sensitive_data: '🔒',
  external_communication: '📤', payment: '💰', account_change: '🔄',
  permission_escalation: '⬆️', uncertain_decision: '❓',
  file_write: '✏️', file_delete: '🗑️', network_access: '🌐', code_execution: '⚡',
}

export function ApprovalPanel({ requests, onRespond }: Props) {
  const pending = requests.filter(r => r.status === 'pending')
  const history = requests.filter(r => r.status !== 'pending')

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {pending.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">No pending approval requests</p>
            <p className="mt-1 text-xs text-muted-foreground">Approvals are requested when tasks require user permission</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Pending Approvals ({pending.length})
          </h3>
          {pending.map(req => (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4" key={req.id}>
              <div className="flex items-start gap-3">
                <span className="text-xl">🔔</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">Approval Required</span>
                    <Badge className="text-yellow-600 border-yellow-500/30" variant="outline">Pending</Badge>
                  </div>
                  <p className="mt-1 text-sm">{req.description}</p>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {req.actions.map(action => (
                      <Badge className="gap-1 text-xs" key={action} variant="outline">
                        <span>{ACTION_EMOJIS[action] ?? '🔴'}</span>
                        {ACTION_LABELS[action] ?? action}
                      </Badge>
                    ))}
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-4 text-xs text-muted-foreground">
                    <div>
                      <span className="font-medium text-foreground">Agent:</span> {req.agentName} ({req.agentRole})
                    </div>
                    <div>
                      <span className="font-medium text-foreground">Task:</span> {req.taskName.slice(0, 60)}
                    </div>
                    <div>
                      <span className="font-medium text-foreground">Requested:</span> {new Date(req.createdAt).toLocaleString()}
                    </div>
                  </div>

                  {Object.keys(req.details).length > 0 && (
                    <div className="mt-2 rounded-lg bg-muted/50 p-2">
                      <div className="text-xs font-medium text-muted-foreground mb-1">Details</div>
                      <pre className="text-xs text-muted-foreground overflow-auto max-h-24">
                        {JSON.stringify(req.details, null, 2)}
                      </pre>
                    </div>
                  )}

                  <div className="mt-4 flex items-center gap-2">
                    <Button
                      className="bg-green-600 hover:bg-green-700 text-white"
                      onClick={() => onRespond(req.id, 'approved')}
                      size="sm"
                    >
                      ✓ Approve Once
                    </Button>
                    <Button
                      className="border-green-500/30 text-green-600"
                      onClick={() => onRespond(req.id, 'approved')}
                      size="sm"
                      variant="outline"
                    >
                      Approve Session
                    </Button>
                    <Button
                      className="border-purple-500/30 text-purple-600"
                      onClick={() => onRespond(req.id, 'approved')}
                      size="sm"
                      variant="outline"
                    >
                      Always Allow
                    </Button>
                    <Button
                      className="border-red-500/30 text-red-600"
                      onClick={() => onRespond(req.id, 'denied')}
                      size="sm"
                      variant="outline"
                    >
                      ✗ Deny
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Approval History ({history.length})
          </h4>
          <div className="space-y-1">
            {history.slice(-20).reverse().map(req => (
              <div className="flex items-center gap-3 rounded-lg border p-2 text-sm" key={req.id}>
                <span className={cn('text-base', req.status === 'approved' ? '' : '')}>
                  {req.status === 'approved' ? '✓' : '✗'}
                </span>
                <span className={cn('text-xs font-medium', req.status === 'approved' ? 'text-green-600' : 'text-red-600')}>
                  {req.status}
                </span>
                <span className="flex-1 text-xs text-muted-foreground truncate">{req.description.slice(0, 80)}</span>
                <span className="text-[10px] text-muted-foreground">{new Date(req.createdAt).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
