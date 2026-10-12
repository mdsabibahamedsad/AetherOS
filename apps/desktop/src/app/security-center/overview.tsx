import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { $allApprovalRequests } from '@/store/prompts'
import { $securityState } from '@/store/security'

export function OverviewDashboard() {
  // Reactive: header numbers must update when live state changes.
  const state = useStore($securityState)
  // Live pending approvals from the gateway event stream (session-keyed).
  // Counters the backend does not feed (blocked actions, audit totals,
  // alert feed) are NOT shown — a permanent zero would masquerade as
  // "nothing ever blocked". See the Audit Log and Alerts tabs for the
  // real log-backed views.
  const pendingEntries = Object.entries(useStore($allApprovalRequests))
  const pendingApprovals = pendingEntries.length
  const runningSandboxes = state.sandboxes.filter(s => s.status === 'running')

  return (
    <ScrollArea>
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            color="blue"
            icon="lock"
            label="Active Permissions"
            sub={`${PERMISSION_DEFS.length} categories`}
            value={state.grants.length}
          />
          <StatCard
            color="amber"
            icon="checklist"
            label="Pending Approvals"
            sub="Live across sessions"
            value={pendingApprovals}
          />
          <StatCard
            color="purple"
            icon="container"
            label="Running Sandboxes"
            sub={`${state.sandboxes.length} total`}
            value={runningSandboxes.length}
          />
          <StatCard
            color="indigo"
            icon="device-desktop"
            label="Connected Devices"
            sub="Active sessions"
            value={state.sessions.length}
          />
        </div>

        <div className="space-y-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <Codicon name="checklist" size="1rem" />
            Pending Approvals
          </h3>
          {pendingApprovals === 0 ? (
            <div className="rounded-lg border border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
              No pending approval requests
            </div>
          ) : (
            <div className="space-y-1.5">
              {pendingEntries.slice(0, 5).map(([sessionKey, req]) => (
                <div className="flex items-center gap-3 rounded-lg border px-3 py-2 text-xs" key={sessionKey}>
                  <Codicon className="shrink-0 text-amber-500" name="question" size="1rem" />
                  <div className="min-w-0 flex-1">
                    <span className="font-medium">{req.description}</span>
                    {req.command.trim() && (
                      <span className="ml-2 font-mono text-muted-foreground/60">{req.command.slice(0, 80)}</span>
                    )}
                  </div>
                  <Badge className="shrink-0 text-[0.55rem]" variant="warn">
                    {sessionKey.length > 12 ? `${sessionKey.slice(0, 8)}…` : sessionKey}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <Codicon name="server" size="1rem" />
            Running Sandboxes
          </h3>
          {runningSandboxes.length === 0 ? (
            <div className="rounded-lg border border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
              No sandboxes are currently running
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
              {runningSandboxes.map(sb => (
                <div className="rounded-lg border px-3 py-2 text-xs" key={sb.id}>
                  <div className="flex items-center gap-2 font-medium">
                    <span className={cn('size-2 rounded-full', sb.status === 'running' ? 'bg-emerald-500' : 'bg-amber-500')} />
                    {sb.name}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-muted-foreground">
                    <Codicon name="symbol-misc" size="0.75rem" />
                    <span className="capitalize">{sb.mode}</span>
                    <span className="text-muted-foreground/40">&middot;</span>
                    <span className="capitalize">{sb.type}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <Separator />

        <div className="pb-4 text-center text-[0.6rem] text-muted-foreground">
          Security Center v{state.version} &middot; {state.zeroTrust ? 'Zero Trust enabled' : 'Standard security'} &middot; Last checked: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </ScrollArea>
  )
}

const PERMISSION_DEFS = [
  { id: 'filesystem', icon: 'file-directory', label: 'Filesystem' },
  { id: 'network', icon: 'globe', label: 'Network' },
  { id: 'browser', icon: 'globe', label: 'Browser' },
  { id: 'clipboard', icon: 'clippy', label: 'Clipboard' },
  { id: 'terminal', icon: 'terminal', label: 'Terminal' },
  { id: 'docker', icon: 'container', label: 'Docker' },
  { id: 'python', icon: 'symbol-misc', label: 'Python' },
  { id: 'database', icon: 'database', label: 'Database' },
  { id: 'cloud', icon: 'cloud', label: 'Cloud' },
]

function StatCard({ icon, label, value, sub, color }: { icon: string; label: string; value: number; sub: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: 'text-blue-500 bg-blue-500/10',
    green: 'text-emerald-500 bg-emerald-500/10',
    amber: 'text-amber-500 bg-amber-500/10',
    red: 'text-red-500 bg-red-500/10',
    purple: 'text-purple-500 bg-purple-500/10',
    slate: 'text-slate-500 bg-slate-500/10',
    indigo: 'text-indigo-500 bg-indigo-500/10',
  }

  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
      <div className="flex items-center gap-2 text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">
        <Codicon name={icon} size="0.875rem" />
        {label}
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-bold tabular-nums">{value}</span>
        <span className="text-xs text-muted-foreground">{sub}</span>
      </div>
    </div>
  )
}
