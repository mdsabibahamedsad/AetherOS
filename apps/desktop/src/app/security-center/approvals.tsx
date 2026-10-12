import { useStore } from '@nanostores/react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { EmptyState } from '@/components/ui/empty-state'
import { SearchField } from '@/components/ui/search-field'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify, notifyError } from '@/store/notifications'
import {
  $allApprovalRequests,
  clearApprovalRequest,
  type ApprovalRequest as GatewayApproval,
} from '@/store/prompts'

// Approvals Center renders ONLY live pending approvals parked by the
// gateway event stream (`approval.request` per session, see
// store/prompts.ts). The backend sends command + description only —
// risk/agent/target metadata is deliberately NOT shown because the
// backend does not provide it, and the backend retains no approval
// history (one in-flight approval per session). Fabricating either
// would violate the platform's no-simulation rule.
type ApprovalChoice = 'once' | 'session' | 'always' | 'deny'

interface Row {
  allowPermanent: boolean
  command: string
  description: string
  sessionKey: string
  sessionId: string | null
}

function shortSession(id: string | null): string {
  if (!id) {return 'current session'}

  return id.length > 12 ? `${id.slice(0, 8)}…` : id
}

export function ApprovalCenter() {
  const all = useStore($allApprovalRequests)
  const gateway = useStore($gateway)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<ApprovalChoice | null>(null)
  const [armAlways, setArmAlways] = useState(false)

  const rows: Row[] = useMemo(
    () =>
      Object.entries(all).map(([sessionKey, req]: [string, GatewayApproval]) => ({
        allowPermanent: req.allowPermanent !== false,
        command: req.command,
        description: req.description,
        sessionKey,
        sessionId: req.sessionId,
      })),
    [all]
  )

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()

    if (!q) {return rows}

    return rows.filter(
      r =>
        r.command.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        r.sessionKey.toLowerCase().includes(q)
    )
  }, [rows, searchQuery])

  const selected = filtered.find(r => r.sessionKey === selectedKey) ?? null

  async function respond(row: Row, choice: ApprovalChoice) {
    if (submitting || !gateway) {
      if (!gateway) {notifyError(new Error('Gateway disconnected'), 'Cannot send approval response')}

      return
    }

    setSubmitting(choice)

    try {
      await gateway.request<{ resolved?: boolean }>('approval.respond', {
        choice,
        session_id: row.sessionId ?? undefined,
      })
      clearApprovalRequest(row.sessionId)
      notify({
        kind: choice === 'deny' ? 'info' : 'success',
        title: choice === 'deny' ? 'Request denied' : 'Request approved',
        message:
          choice === 'deny'
            ? 'The action was blocked.'
            : choice === 'once'
              ? 'Approved for this action only.'
              : choice === 'session'
                ? 'Approved for this session.'
                : 'Permanently allow-listed.',
      })
      setSelectedKey(null)
      setArmAlways(false)
    } catch (error) {
      notifyError(error, 'Approval response failed')
    } finally {
      setSubmitting(null)
    }
  }

  if (!gateway) {
    return (
      <div className="grid h-full place-items-center p-6">
        <EmptyState
          description="Connect the gateway to review live approval requests."
          icon="checklist"
          title="Gateway disconnected"
        />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <div className="w-80 shrink-0 border-r border-(--ui-stroke-tertiary) p-4">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Approval Requests</span>
            {rows.length > 0 && (
              <Badge className="text-[0.55rem]" variant="warn">
                {rows.length} pending
              </Badge>
            )}
          </div>
          <SearchField
            containerClassName="w-full"
            onChange={setSearchQuery}
            placeholder="Search requests..."
            value={searchQuery}
          />
          <div aria-label="Pending approval requests" className="space-y-0.5" role="list">
            {filtered.map(req => (
              <button
                className={cn(
                  'flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors',
                  selected?.sessionKey === req.sessionKey ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/60'
                )}
                key={req.sessionKey}
                onClick={() => {
                  setSelectedKey(req.sessionKey)
                  setArmAlways(false)
                }}
                role="listitem"
                type="button"
              >
                <span aria-hidden className="mt-0.5 size-2 shrink-0 rounded-full bg-amber-500" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-medium">{shortSession(req.sessionId)}</span>
                    <Badge className="bg-amber-500/10 text-[0.5rem] text-amber-600" variant="muted">
                      pending
                    </Badge>
                  </div>
                  <div className="truncate text-xs text-muted-foreground">{req.description}</div>
                  {req.command.trim() && (
                    <div className="mt-0.5 truncate font-mono text-[0.6rem] text-muted-foreground/60">{req.command}</div>
                  )}
                </div>
              </button>
            ))}
            {filtered.length === 0 && (
              <div className="px-2 py-6 text-center">
                <div className="text-xs text-muted-foreground">No pending approvals</div>
                <div className="mt-1 text-[0.65rem] text-muted-foreground/60">
                  Requests appear here when a running agent needs a decision.
                </div>
              </div>
            )}
          </div>
          <p className="px-1 text-[0.6rem] leading-snug text-muted-foreground/60">
            Terminal and code-execution gate. The backend keeps one in-flight request per session and no history.
          </p>
        </div>
      </div>

      <div className="min-w-0 flex-1 overflow-y-auto p-4">
        {selected ? (
          <div className="space-y-4">
            <div className="rounded-xl border-2 border-amber-500/30 bg-amber-500/10 p-4">
              <div className="flex items-center gap-3">
                <Codicon className="text-amber-500" name="warning" size="1.25rem" />
                <div>
                  <h3 className="text-lg font-semibold">{selected.description}</h3>
                  <p className="text-xs text-muted-foreground">
                    Session <strong className="font-mono">{shortSession(selected.sessionId)}</strong>
                  </p>
                </div>
              </div>
            </div>

            {selected.command.trim() && (
              <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
                <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Command</div>
                <pre className="mt-1 overflow-x-auto rounded bg-muted/30 p-2 font-mono text-xs">{selected.command}</pre>
              </div>
            )}

            <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
              <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">Scope</div>
              <div className="mt-1 text-sm">Terminal / code execution in this session only. Nothing else is granted.</div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                className="text-xs"
                disabled={submitting !== null}
                onClick={() => void respond(selected, 'once')}
                size="sm"
              >
                <Codicon className="mr-1" name="check" size="0.75rem" />
                {submitting === 'once' ? 'Sending…' : 'Allow Once'}
              </Button>
              <Button
                className="text-xs"
                disabled={submitting !== null}
                onClick={() => void respond(selected, 'session')}
                size="sm"
                variant="secondary"
              >
                <Codicon className="mr-1" name="clock" size="0.75rem" /> Allow Session
              </Button>
              {selected.allowPermanent && (
                <Button
                  className="text-xs"
                  disabled={submitting !== null}
                  onClick={() => {
                    if (armAlways) {void respond(selected, 'always')}
                    else {setArmAlways(true)}
                  }}
                  size="sm"
                  variant="outline"
                >
                  <Codicon className="mr-1" name="lock" size="0.75rem" />
                  {armAlways ? 'Click again to confirm permanent allow' : 'Always Allow'}
                </Button>
              )}
              <Button
                className="ml-auto text-xs"
                disabled={submitting !== null}
                onClick={() => void respond(selected, 'deny')}
                size="sm"
                variant="destructive"
              >
                <Codicon className="mr-1" name="x" size="0.75rem" />
                {submitting === 'deny' ? 'Sending…' : 'Deny'}
              </Button>
            </div>
            {armAlways && (
              <p className="text-xs text-amber-600">
                Permanent allow writes to configuration. Deny keeps the agent blocked on this action.
              </p>
            )}
          </div>
        ) : (
          <div className="grid min-h-52 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="checklist" size="2rem" />
              <div className="mt-2 text-sm font-medium text-muted-foreground">Select a request</div>
              <div className="mt-1 text-xs text-muted-foreground/60">Choose a pending approval to review details</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
