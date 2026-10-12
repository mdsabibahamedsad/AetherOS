import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify } from '@/store/notifications'
import { $allApprovalRequests } from '@/store/prompts'
import { $securityState, updateSecurityState } from '@/store/security'

import { SecurityAlertsView } from './alerts'
import { ApprovalCenter } from './approvals'
import { AuditLogView } from './audit'
import { OverviewDashboard } from './overview'
import { PermissionManager } from './permissions'
import { PrivacySettings } from './privacy'
import { SandboxManager } from './sandbox'
import { SecretsManager } from './secrets'

const TABS = [
  { id: 'overview', label: 'Overview', icon: 'dashboard' },
  { id: 'permissions', label: 'Permissions', icon: 'lock' },
  { id: 'approvals', label: 'Approvals', icon: 'checklist' },
  { id: 'sandbox', label: 'Sandbox', icon: 'container' },
  { id: 'audit', label: 'Audit Log', icon: 'history' },
  { id: 'alerts', label: 'Alerts', icon: 'alert' },
  { id: 'secrets', label: 'Secrets', icon: 'key' },
  { id: 'privacy', label: 'Privacy', icon: 'shield' },
] as const

type TabId = (typeof TABS)[number]['id']

export function SecurityCenterView() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [checking, setChecking] = useState(false)
  const state = useStore($securityState)
  const gateway = useStore($gateway)
  const pendingApprovals = Object.keys(useStore($allApprovalRequests)).length

  // Real integrity check: gateway reachability + backend log readability.
  // Never reports "Secure" without performing the checks.
  async function runIntegrityCheck() {
    if (checking) {return}
    setChecking(true)
    const findings: string[] = []

    if (!gateway) {findings.push('gateway disconnected')}

    try {
      const recent = await window.aetherosDesktop?.getRecentLogs?.()

      if (!recent?.lines) {findings.push('backend logs unreadable')}
    } catch {
      findings.push('backend logs unreadable')
    }

    const integrity = findings.length === 0 ? 'passed' : findings.length === 1 ? 'warning' : 'failed'
    updateSecurityState({ initialized: true, systemIntegrity: integrity })
    notify({
      kind: integrity === 'passed' ? 'success' : integrity === 'warning' ? 'info' : 'error',
      title: integrity === 'passed' ? 'Integrity check passed' : 'Integrity issues found',
      message: integrity === 'passed' ? 'Gateway reachable, backend logs readable.' : findings.join('; '),
    })
    setChecking(false)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      <header className="flex shrink-0 items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">Security Center</h1>
              <Badge className="text-[0.6rem]" variant={state.systemIntegrity === 'passed' ? 'default' : state.systemIntegrity === 'warning' ? 'warn' : 'destructive'}>
                {state.systemIntegrity === 'passed' ? 'Secure' : state.systemIntegrity === 'warning' ? 'Warning' : 'Compromised'}
              </Badge>
              {state.zeroTrust && <Badge className="text-[0.6rem]" variant="outline">Zero Trust</Badge>}
            </div>
            <p className="text-sm text-muted-foreground">
              {state.alerts.length} alerts &middot; {state.grants.length} grants &middot; {pendingApprovals} pending approvals &middot; {state.sandboxes.length} sandboxes
            </p>
          </div>
        </div>
        <Button className="text-xs" disabled={checking} onClick={() => void runIntegrityCheck()} size="sm" variant="outline">
          <Codicon className="mr-1" name="check" size="0.75rem" /> {checking ? 'Checking…' : 'Verify Integrity'}
        </Button>
      </header>

      <div className="flex shrink-0 items-center gap-1 border-b px-4">
        {TABS.map(tab => (
          <button
            className={cn(
              'flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <Codicon className="text-xs" name={tab.icon} size="0.75rem" />
            {tab.label}
            {tab.id === 'approvals' && pendingApprovals > 0 && (
              <Badge className="ml-1 text-[0.5rem]" variant="warn">{pendingApprovals}</Badge>
            )}
            {tab.id === 'alerts' && state.activeAlertsCount > 0 && (
              <Badge className="ml-1 text-[0.5rem]" variant="destructive">{state.activeAlertsCount}</Badge>
            )}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'overview' && <OverviewDashboard />}
        {activeTab === 'permissions' && <PermissionManager />}
        {activeTab === 'approvals' && <ApprovalCenter />}
        {activeTab === 'sandbox' && <SandboxManager />}
        {activeTab === 'audit' && <AuditLogView />}
        {activeTab === 'alerts' && <SecurityAlertsView />}
        {activeTab === 'secrets' && <SecretsManager />}
        {activeTab === 'privacy' && <PrivacySettings />}
      </div>
    </div>
  )
}
