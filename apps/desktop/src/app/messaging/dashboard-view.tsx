import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { StatusDot, type StatusTone } from '@/components/status-dot'
import { Activity, AlertTriangle, BarChart3, MessageCircle, MessageSquareText, Zap } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  $communications,
  type ActivityEntry,
  getAllPlatformMeta,
  getCommsStats,
  type PlatformConnection,
  setPlatformStatus
} from '@/store/communications'

const STAT_CARDS: { key: keyof ReturnType<typeof getCommsStats>; icon: typeof BarChart3; label: string }[] = [
  { key: 'connectedAccounts', icon: MessageCircle, label: 'Connected Accounts' },
  { key: 'onlineStatus', icon: Zap, label: 'Online' },
  { key: 'messagesToday', icon: MessageSquareText, label: 'Messages Today' },
  { key: 'aiReplies', icon: BarChart3, label: 'AI Replies' },
  { key: 'queuedMessages', icon: Activity, label: 'Queued' },
  { key: 'failedMessages', icon: AlertTriangle, label: 'Failed' }
]

function statTone(key: string, value: number): StatusTone {
  if (key === 'failedMessages') {return value > 0 ? 'bad' : 'good'}

  if (key === 'queuedMessages') {return value > 0 ? 'warn' : 'good'}

  if (key === 'aiReplies') {return 'good'}

  return value > 0 ? 'good' : 'muted'
}

export function DashboardView() {
  const state = useStore($communications)
  const stats = useMemo(() => getCommsStats(), [state])
  const platforms = useMemo(() => getAllPlatformMeta(), [])
  const connections = useMemo(() => state.platformConnections, [state.platformConnections])

  return (
    <div className="mx-auto flex h-full min-w-0 max-w-5xl flex-col gap-6 overflow-y-auto p-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {STAT_CARDS.map(card => (
              <StatCard
                icon={card.icon}
                key={card.key}
                label={card.label}
                tone={statTone(card.key, stats[card.key])}
                value={stats[card.key]}
              />
        ))}
      </div>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Platforms</h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {platforms.map(meta => {
            const conn = connections.find(c => c.id === meta.id)

            return (
              <PlatformCard connection={conn} key={meta.id} meta={meta} />
            )
          })}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Recent Activity</h3>
        <div className="space-y-1">
          {state.activityFeed.length === 0 && (
            <p className="py-8 text-center text-xs text-(--ui-text-tertiary)">No recent activity</p>
          )}
          {state.activityFeed.slice(0, 20).map(entry => (
            <ActivityRow entry={entry} key={entry.id} />
          ))}
        </div>
      </section>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, tone }: { icon: typeof BarChart3; label: string; value: number | string; tone: StatusTone }) {
  return (
    <div className="rounded-lg border border-(--ui-stroke-tertiary) px-3 py-3">
      <div className="flex items-center justify-between">
        <Icon className="size-4 text-(--ui-text-tertiary)" />
        <StatusDot tone={tone} />
      </div>
      <p className="mt-1 text-xl font-semibold tracking-tight">{value}</p>
      <p className="text-xs text-(--ui-text-tertiary)">{label}</p>
    </div>
  )
}

function PlatformCard({ connection, meta }: { connection?: PlatformConnection; meta: { id: string; name: string; icon: string; color: string } }) {
  const connected = connection?.connected ?? false
  const online = connection?.online ?? false

  return (
    <button
      className={cn(
        'flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5 text-left transition-colors',
        connected ? 'hover:bg-(--chrome-action-hover)' : 'opacity-60'
      )}
      onClick={() => {
        if (!connected) {
          setPlatformStatus(meta.id as any, true, true)
        }
      }}
      type="button"
    >
      <span
        className="inline-grid size-8 shrink-0 place-items-center rounded-md text-sm font-medium"
        style={{
          backgroundColor: `color-mix(in srgb, ${meta.color} 16%, transparent)`,
          color: meta.color
        }}
      >
        <span className="text-xs font-bold">{meta.name[0]}</span>
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{meta.name}</span>
          <StatusDot tone={online ? 'good' : connected ? 'warn' : 'muted'} />
        </div>
        <p className="text-xs text-(--ui-text-tertiary)">
          {connected ? (online ? 'Online' : 'Connecting...') : 'Disconnected'}
        </p>
      </div>
    </button>
  )
}

const ACTIVITY_ICONS: Record<ActivityEntry['type'], typeof Activity> = {
  message: MessageSquareText,
  connection: Zap,
  ai_reply: BarChart3,
  error: AlertTriangle,
  broadcast: MessageCircle
}

const ACTIVITY_TONES: Record<ActivityEntry['type'], StatusTone> = {
  message: 'good',
  connection: 'good',
  ai_reply: 'good',
  error: 'bad',
  broadcast: 'warn'
}

function ActivityRow({ entry }: { entry: ActivityEntry }) {
  const Icon = ACTIVITY_ICONS[entry.type]

  return (
    <div className="flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-(--chrome-action-hover)">
      <span className="inline-flex size-6 items-center justify-center rounded-full bg-(--ui-row-active-background)">
        <Icon className="size-3 text-(--ui-text-secondary)" />
      </span>
      <span className="min-w-0 flex-1 truncate text-sm">{entry.description}</span>
      <span className="shrink-0 text-xs text-(--ui-text-tertiary)">{formatRelativeTime(entry.timestamp)}</span>
    </div>
  )
}

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(diff / 60000)

  if (mins < 1) {return 'now'}

  if (mins < 60) {return `${mins}m ago`}
  const hours = Math.floor(mins / 60)

  if (hours < 24) {return `${hours}h ago`}
  const days = Math.floor(hours / 24)

  return `${days}d ago`
}
