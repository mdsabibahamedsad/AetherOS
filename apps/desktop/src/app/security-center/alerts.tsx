import { useStore } from '@nanostores/react'
import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify } from '@/store/notifications'
import type { AlertCategory, AlertSeverity } from '@/store/security'

// Security alerts are DERIVED from real signals only:
//  - gateway connection state ($gateway null = disconnected)
//  - backend log lines matching denial/failure/signature patterns
//    (verbatim line shown as evidence; severity is a display heuristic
//    over the real line, never a synthesized incident).
// Previously this view rendered hardcoded sample incidents (including a
// fabricated brute-force report) — removed.
const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  info: 'bg-blue-500/10 text-blue-600',
  warning: 'bg-amber-500/10 text-amber-600',
  error: 'bg-orange-500/10 text-orange-600',
  critical: 'bg-red-500/10 text-red-600',
}

const SEVERITY_ICONS: Record<AlertSeverity, string> = {
  info: 'info',
  warning: 'warning',
  error: 'error',
  critical: 'error',
}

const CATEGORY_LABELS: Record<AlertCategory, string> = {
  'repeated-failures': 'Repeated Failures',
  'suspicious-tool-usage': 'Suspicious Tool Usage',
  'unexpected-network': 'Unexpected Network Access',
  'permission-escalation': 'Permission Escalation',
  'untrusted-plugin': 'Untrusted Plugin',
  'invalid-signature': 'Invalid Signature',
  'credential-failure': 'Credential Failure',
  'brute-force': 'Brute Force',
  'abnormal-activity': 'Abnormal Activity',
}

interface DerivedAlert {
  category: AlertCategory
  count: number
  evidence: string
  id: string
  severity: AlertSeverity
  source: string
  title: string
}

function classifyLine(line: string): { category: AlertCategory; severity: AlertSeverity } | null {
  const l = line.toLowerCase()

  if (/brute.?force|intrusion|breach/.test(l)) {return { category: 'brute-force', severity: 'critical' }}

  if (/signature.*(fail|invalid|mismatch)|invalid signature/.test(l)) {return { category: 'invalid-signature', severity: 'error' }}

  if (/credential|auth.*fail|token.*(expired|revoked|invalid)|login fail/.test(l)) {return { category: 'credential-failure', severity: 'error' }}

  if (/denied|blocked|violation|policy denied|forbidden/.test(l)) {return { category: 'permission-escalation', severity: 'error' }}

  if (/unexpected|allowlist|not in.*allow/.test(l)) {return { category: 'unexpected-network', severity: 'warning' }}

  if (/suspicious|anomal|untrusted/.test(l)) {return { category: 'suspicious-tool-usage', severity: 'warning' }}

  if (/fail|error|exception|traceback/.test(l)) {return { category: 'repeated-failures', severity: 'warning' }}

  return null
}

function deriveAlerts(lines: string[]): DerivedAlert[] {
  const byKey = new Map<string, DerivedAlert>()

  for (const raw of lines) {
    const line = raw.trim()

    if (!line) {continue}
    const hit = classifyLine(line)

    if (!hit) {continue}
    const key = `${hit.category}:${line.slice(0, 160)}`
    const existing = byKey.get(key)

    if (existing) {
      existing.count += 1
    } else {
      byKey.set(key, {
        category: hit.category,
        count: 1,
        evidence: line.slice(0, 500),
        id: `log-${byKey.size}`,
        severity: hit.severity,
        source: 'Backend log',
        title:
          hit.category === 'invalid-signature'
            ? 'Signature verification failure'
            : hit.category === 'credential-failure'
              ? 'Credential failure'
              : hit.category === 'permission-escalation'
                ? 'Blocked / denied action'
                : hit.category === 'brute-force'
                  ? 'Possible intrusion signal'
                  : 'Suspicious backend event',
      })
    }
  }

  return [...byKey.values()].slice(0, 50)
}

export function SecurityAlertsView() {
  const gateway = useStore($gateway)
  const [lines, setLines] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [unavailable, setUnavailable] = useState(false)
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  useEffect(() => {
    let live = true

    ;(async () => {
      try {
        const recent = await window.aetherosDesktop?.getRecentLogs?.()

        if (!live) {return}

        if (recent?.lines) {
          setLines(recent.lines)
        } else {
          setUnavailable(true)
        }
      } catch {
        if (live) {setUnavailable(true)}
      } finally {
        if (live) {setLoading(false)}
      }
    })()

    return () => {
      live = false
    }
  }, [])

  const alerts = useMemo(() => {
    const derived = deriveAlerts(lines)

    if (!gateway) {
      derived.unshift({
        category: 'abnormal-activity',
        count: 1,
        evidence: 'Gateway client is not connected; live approval and event flow are unavailable.',
        id: 'gateway-disconnected',
        severity: 'warning',
        source: 'Connection monitor',
        title: 'Gateway disconnected',
      })
    }

    return derived.filter(a => !dismissed.has(a.id))
  }, [lines, gateway, dismissed])

  const filtered = useMemo(
    () =>
      alerts.filter(a => {
        if (severityFilter !== 'all' && a.severity !== severityFilter) {return false}

        if (categoryFilter !== 'all' && a.category !== categoryFilter) {return false}

        return true
      }),
    [alerts, severityFilter, categoryFilter]
  )

  const categories = [...new Set(alerts.map(a => a.category))]

  function dismiss(id: string, label: string) {
    setDismissed(prev => new Set(prev).add(id))
    notify({ kind: 'info', title: label, message: 'Alert dismissed from this view (log lines unchanged).' })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <Select onValueChange={v => setSeverityFilter(v)} value={severityFilter}>
          <SelectTrigger className="h-7 w-32 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severity</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="info">Info</SelectItem>
          </SelectContent>
        </Select>
        <Select onValueChange={v => setCategoryFilter(v)} value={categoryFilter}>
          <SelectTrigger className="h-7 w-44 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map(c => (
              <SelectItem key={c} value={c}>
                {CATEGORY_LABELS[c]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="ml-auto text-xs text-muted-foreground">{filtered.length} alerts</div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-1.5 p-4">
          {loading ? (
            <p className="py-8 text-center text-xs text-muted-foreground">Scanning backend signals…</p>
          ) : unavailable && alerts.length === 0 ? (
            <div className="py-8 text-center">
              <EmptyState
                description="Backend logs could not be read, so there is nothing to assess. Reconnect the backend instead of assuming safety."
                icon="shield"
                title="Monitoring unavailable"
              />
            </div>
          ) : (
            filtered.map(alert => (
              <div
                className={cn('flex items-start gap-3 rounded-lg border px-4 py-3 text-xs transition-colors', SEVERITY_COLORS[alert.severity])}
                key={alert.id}
              >
                <Codicon
                  className={cn('mt-0.5 shrink-0', alert.severity === 'critical' || alert.severity === 'error' ? 'text-red-500' : 'text-amber-500')}
                  name={SEVERITY_ICONS[alert.severity]}
                  size="1rem"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{alert.title}</span>
                    {alert.count > 1 && (
                      <Badge className="text-[0.5rem]" variant="muted">
                        {alert.count}x
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 font-mono text-[0.65rem] break-words text-muted-foreground">{alert.evidence}</p>
                  <div className="mt-1 flex items-center gap-2 text-[0.6rem] text-muted-foreground/60">
                    <span className="capitalize">{CATEGORY_LABELS[alert.category]}</span>
                    <span>&middot;</span>
                    <span>{alert.source}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button className="text-xs" onClick={() => dismiss(alert.id, 'Alert dismissed')} size="sm" variant="ghost">
                    Dismiss
                  </Button>
                </div>
              </div>
            ))
          )}
          {!loading && !(unavailable && alerts.length === 0) && filtered.length === 0 && (
            <div className="px-4 py-12 text-center text-xs text-muted-foreground">
              <Codicon className="mx-auto mb-2 text-muted-foreground/40" name="check" size="2rem" />
              {alerts.length === 0 ? 'No security signals in recent backend output' : 'No alerts match your filters'}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
