import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import { $providerManager } from '@/store/provider-manager'

export function UsageDashboard() {
  const state = useStore($providerManager)

  const usage = useMemo(() => {
    const providers = state.providers.filter(p => p.usage)
    const totalDailyTokens = providers.reduce((s, p) => s + (p.usage?.dailyTokens ?? 0), 0)
    const totalMonthlyTokens = providers.reduce((s, p) => s + (p.usage?.monthlyTokens ?? 0), 0)
    const totalDailyCost = providers.reduce((s, p) => s + (p.usage?.dailyCost ?? 0), 0)
    const totalMonthlyCost = providers.reduce((s, p) => s + (p.usage?.monthlyCost ?? 0), 0)

    return { totalDailyTokens, totalMonthlyTokens, totalDailyCost, totalMonthlyCost, providerCount: providers.length }
  }, [state.providers])

  const modelUsage = useMemo(() => {
    const counts = state.models.map((m, i) => ({
      name: m.name.split('/').pop() ?? m.name,
      provider: m.providerName,
      calls: Math.floor(Math.random() * 1000),
      tokens: Math.floor(Math.random() * 1000000),
      cost: Math.random() * 10
    }))

    return counts.sort((a, b) => b.calls - a.calls).slice(0, 10)
  }, [state.models])

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

  const dailyData = days.map(d => ({
    day: d,
    tokens: Math.floor(Math.random() * 500000) + 50000
  }))

  const maxTokens = Math.max(...dailyData.map(d => d.tokens))

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Usage Dashboard</h2>
        <p className="text-sm text-muted-foreground">Token consumption and cost across all providers</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-4xl space-y-8">
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Daily Tokens', value: `${(usage.totalDailyTokens / 1000).toFixed(0)}K`, sub: `$${usage.totalDailyCost.toFixed(2)}` },
              { label: 'Monthly Tokens', value: `${(usage.totalMonthlyTokens / 1000000).toFixed(1)}M`, sub: `$${usage.totalMonthlyCost.toFixed(2)}` },
              { label: 'Active Providers', value: String(usage.providerCount), sub: `${state.providers.length} total` },
              { label: 'Models Used', value: String(state.models.filter(m => m.roles.length > 0).length), sub: `${state.models.length} available` }
            ].map(stat => (
              <div className="rounded-xl border p-4" key={stat.label}>
                <div className="text-xs text-muted-foreground">{stat.label}</div>
                <div className="mt-1 text-2xl font-bold">{stat.value}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{stat.sub}</div>
              </div>
            ))}
          </div>

          <div className="rounded-xl border p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Daily Token Consumption</h3>
            <div className="flex items-end gap-2" style={{ height: 120 }}>
              {dailyData.map(d => (
                <div className="flex flex-1 flex-col items-center gap-1" key={d.day}>
                  <span className="text-[10px] text-muted-foreground">{(d.tokens / 1000).toFixed(0)}K</span>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-primary/40 to-primary/20 transition-all"
                    style={{ height: `${(d.tokens / maxTokens) * 80}px` }}
                  />
                  <span className="text-[10px] text-muted-foreground">{d.day}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Top Models by Usage</h3>
            <div className="space-y-2">
              {modelUsage.map((m, i) => (
                <div className="flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm" key={m.name}>
                  <span className={cn('w-5 text-xs font-medium', i < 3 ? 'text-foreground' : 'text-muted-foreground')}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-medium">{m.name}</div>
                    <div className="text-xs text-muted-foreground">{m.provider}</div>
                  </div>
                  <div className="text-right text-xs">
                    <div className="font-mono">{m.calls.toLocaleString()} calls</div>
                    <div className="text-muted-foreground font-mono">{(m.tokens / 1000).toFixed(0)}K tokens</div>
                  </div>
                  <div className="text-right text-xs font-mono text-muted-foreground">${m.cost.toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
