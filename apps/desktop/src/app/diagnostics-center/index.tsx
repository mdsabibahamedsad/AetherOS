import { useStore } from '@nanostores/react'
import { useCallback, useMemo } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle2, Cpu, Monitor as HardDrive, Loader2, Lock, Globe as Network, Zap as Shield, Wrench } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  $diagnostics,
  addReport,
  resetChecks,
  setDiagnosticCategory,
  setRunningAll,
  updateCheck,
  updateRepair
} from '@/store/diagnostics-center'
import type { CheckCategory, CheckSeverity, DiagnosticCheck, RepairAction } from '@/store/diagnostics-center'
import { notify } from '@/store/notifications'

const CATEGORY_ICONS: Record<CheckCategory, any> = {
  system: Cpu,
  network: Network,
  storage: HardDrive,
  plugins: Wrench,
  security: Lock,
  performance: Shield
}

const CATEGORY_LABELS: Record<CheckCategory | 'all', string> = {
  all: 'All',
  system: 'System',
  network: 'Network',
  storage: 'Storage',
  plugins: 'Plugins',
  security: 'Security',
  performance: 'Performance'
}

const SEVERITY_COLORS: Record<CheckSeverity, string> = {
  info: 'bg-sky-500/10 text-sky-500',
  warning: 'bg-amber-500/10 text-amber-500',
  error: 'bg-red-500/10 text-red-500'
}

const STATUS_ICONS: Record<string, any> = {
  pending: Loader2,
  running: Loader2,
  passed: CheckCircle2,
  failed: Shield,
  warning: Shield
}

async function runCheck(check: DiagnosticCheck): Promise<void> {
  updateCheck(check.id, { status: 'running' })
  await new Promise(r => setTimeout(r, 800 + Math.random() * 1200))
  const outcomes: Array<'passed' | 'failed' | 'warning'> = ['passed', 'passed', 'passed', 'passed', 'warning', 'failed']
  const status = outcomes[Math.floor(Math.random() * outcomes.length)]

  const messages: Record<string, string> = {
    'sys-cpu': 'CPU temperature normal, load within limits',
    'sys-memory': 'RAM 78% utilized, swap 12% utilized',
    'sys-uptime': 'System has been running for 14 days',
    'net-connectivity': 'Gateway reachable, latency 23ms',
    'net-dns': 'DNS resolution working for all endpoints',
    'net-latency': 'API latency: avg 45ms, max 120ms',
    'st-capacity': 'Disk /: 65% used, Disk /home: 72% used',
    'st-permissions': 'All config directories have correct permissions',
    'st-config': 'config.yaml parsed successfully',
    'pl-compatibility': '3/4 plugins compatible with current runtime',
    'pl-dependencies': 'All plugin dependencies resolved',
    'pl-hooks': '8 hooks registered, no conflicts detected',
    'sec-keys': '4 API keys configured, 2 missing',
    'sec-env': 'No exposed secrets in environment',
    'sec-permissions': 'Permission boundaries correctly configured',
    'perf-cache': 'Cache hit rate: 78.3%',
    'perf-loop': 'Average agent loop: 3.2 turns per task',
    'perf-memory': 'No memory leaks detected'
  }

  updateCheck(check.id, { status, message: messages[check.id] ?? 'Check completed', duration: Math.floor(Math.random() * 500 + 100) })
}

async function runRepair(repair: RepairAction): Promise<void> {
  updateRepair(repair.id, { status: 'running', output: '' })
  await new Promise(r => setTimeout(r, 1000 + Math.random() * 2000))

  const outputs: Record<string, string> = {
    'rep-clear-cache': 'Cache cleared (2.3 MB freed)',
    'rep-restart-gateway': 'Gateway restarted successfully',
    'rep-validate-config': 'Config validated: no issues found',
    'rep-reindex-plugins': 'Plugins reindexed: 4 found, 0 errors',
    'rep-clean-temp': 'Temporary files cleaned (156 MB freed)',
    'rep-reset-network': 'Network stack reset, connections re-established'
  }

  const status = Math.random() > 0.2 ? 'completed' as const : 'failed' as const
  updateRepair(repair.id, { status, output: outputs[repair.id] ?? '' })
  notify({ kind: status === 'completed' ? 'success' : 'error', title: status === 'completed' ? 'Repair Completed' : 'Repair Failed', message: outputs[repair.id] ?? '' })
}

export function DiagnosticsCenterView() {
  const state = useStore($diagnostics)

  const categories: Array<CheckCategory | 'all'> = ['all', 'system', 'network', 'storage', 'plugins', 'security', 'performance']

  const filteredChecks = useMemo(() => {
    if (state.selectedCategory === 'all') {return state.checks}

    return state.checks.filter(c => c.category === state.selectedCategory)
  }, [state.checks, state.selectedCategory])

  const passedCount = state.checks.filter(c => c.status === 'passed').length
  const failedCount = state.checks.filter(c => c.status === 'failed').length
  const warningCount = state.checks.filter(c => c.status === 'warning').length

  const handleRunAll = useCallback(async () => {
    setRunningAll(true)
    resetChecks()

    for (const check of state.checks) {
      await runCheck(check)
    }

    setRunningAll(false)
    const passed = state.checks.filter(c => c.status === 'passed').length
    const total = state.checks.length
    const score = Math.round((passed / total) * 100)
    addReport({
      id: `report-${Date.now()}`,
      timestamp: Date.now(),
      score,
      checks: state.checks,
      summary: `${score}% health score — ${passed}/${total} checks passed`
    })
    notify({ kind: score > 80 ? 'success' : 'warning', title: 'Diagnostics Complete', message: `${score}% health score` })
  }, [state.checks])

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Diagnostics Center</PageTitle>
            <PageDescription>System health checks, diagnostics, and repair tools</PageDescription>
          </div>
          <Button
            disabled={state.runningAll}
            onClick={handleRunAll}
            size="xs"
            variant="textStrong"
          >
            {state.runningAll ? 'Running...' : 'Run All Checks'}
          </Button>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-4 p-4 pt-0">
        <div className="grid shrink-0 grid-cols-4 gap-3">
          <StatCard color="text-foreground" label="Checks" value={state.checks.length.toString()} />
          <StatCard color="text-emerald-500" label="Passed" value={passedCount.toString()} />
          <StatCard color="text-amber-500" label="Warnings" value={warningCount.toString()} />
          <StatCard color="text-red-500" label="Failed" value={failedCount.toString()} />
        </div>

        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {categories.map(cat => (
            <button
              className={cn(
                'border-b-2 px-3 py-2 text-xs font-medium transition-colors',
                state.selectedCategory === cat ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              key={cat}
              onClick={() => setDiagnosticCategory(cat)}
              type="button"
            >
              {CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>

        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {filteredChecks.length === 0 ? (
            <p className="py-8 text-center text-xs text-muted-foreground">No checks match the selected category</p>
          ) : filteredChecks.map(check => (
            <DiagnosticCheckRow check={check} key={check.id} onRun={() => void runCheck(check)} />
          ))}
        </div>

        <div className="shrink-0 border-t border-(--ui-stroke-tertiary) pt-3">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Repair Actions</h4>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {state.repairs.filter(r => state.checks.find(c => c.id === r.checkId)?.status === 'failed').map(repair => (
              <RepairCard key={repair.id} onRun={() => void runRepair(repair)} repair={repair} />
            ))}
          </div>
        </div>
      </div>
    </PageShell>
  )
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
      <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn('mt-0.5 text-lg font-semibold tabular-nums', color)}>{value}</div>
    </div>
  )
}

function DiagnosticCheckRow({ check, onRun }: { check: DiagnosticCheck; onRun: () => void }) {
  const CategoryIcon = CATEGORY_ICONS[check.category]
  const isRunning = check.status === 'running'

  return (
    <div className="flex items-center gap-3 rounded-lg border border-transparent px-3 py-2 text-xs transition-colors hover:border-(--ui-stroke-tertiary)">
      <CategoryIcon className="size-3.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="font-medium text-foreground">{check.name}</div>
        <div className="text-muted-foreground">{check.description}</div>
        {check.message && <div className="mt-0.5 text-muted-foreground/70">{check.message}</div>}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {check.duration && <span className="text-[0.55rem] text-muted-foreground/60">{check.duration}ms</span>}
        <Badge className={SEVERITY_COLORS[check.severity]} variant="secondary">{check.severity}</Badge>
        {check.status === 'pending' && (
          <Button aria-label="Run check" className="text-muted-foreground" onClick={onRun} size="icon-xs" variant="ghost">
            <Shield className="size-3" />
          </Button>
        )}
        {check.status === 'running' && <Loader2 className="size-3 animate-spin text-primary" />}
        {check.status === 'passed' && <CheckCircle2 className="size-3 text-emerald-500" />}
        {check.status === 'failed' && <Shield className="size-3 text-red-500" />}
        {check.status === 'warning' && <Shield className="size-3 text-amber-500" />}
      </div>
    </div>
  )
}

function RepairCard({ repair, onRun }: { repair: RepairAction; onRun: () => void }) {
  const isRunning = repair.status === 'running'

  return (
    <div className={cn(
      'rounded-xl border p-3',
      repair.status === 'completed' ? 'border-emerald-500/30 bg-emerald-500/5' :
      repair.status === 'failed' ? 'border-red-500/30 bg-red-500/5' :
      'border-(--ui-stroke-tertiary)'
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-xs font-medium text-foreground">{repair.name}</div>
          <div className="mt-0.5 text-[0.6rem] text-muted-foreground">{repair.description}</div>
        </div>
        <Button
          disabled={isRunning || repair.status === 'completed'}
          onClick={onRun}
          size="icon-xs"
          variant="ghost"
        >
          {isRunning ? <Loader2 className="size-3 animate-spin" /> : <Wrench className="size-3" />}
        </Button>
      </div>
      {repair.output && (
        <div className="mt-2 rounded bg-(--ui-bg-quinary) px-2 py-1 font-mono text-[0.55rem] text-muted-foreground">
          {repair.output}
        </div>
      )}
      {repair.requiresRestart && (
        <div className="mt-1 text-[0.55rem] text-amber-500">Requires restart</div>
      )}
    </div>
  )
}
