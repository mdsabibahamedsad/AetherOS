import { useStore } from '@nanostores/react'
import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { AUTOMATION_CENTER_ROUTE, KNOWLEDGE_ROUTE, NEW_CHAT_ROUTE, sessionRoute } from '@/app/routes'
import { BrandMark } from '@/components/brand-mark'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { BRAND_TAGLINE, BRAND_WORDMARK } from '@/lib/brand'
import { sessionTitle } from '@/lib/chat-runtime'
import { buildContextChain, scopeDescription } from '@/lib/context-model'
import { cn } from '@/lib/utils'
import { openCommandPalette } from '@/store/command-palette'
import { stashSessionDraft } from '@/store/composer'
import { $cronJobs } from '@/store/cron'
import { $gatewayState } from '@/store/session'
import { $healthStatus, $systemStats, $tokenUsage } from '@/store/system'
import { $activeProfile } from '@/store/profile'
import { $allApprovalRequests } from '@/store/prompts'
import { $gateway } from '@/store/gateway'
import {
  $activeSessionId,
  $currentModel,
  $sessions,
  $workingSessionIds,
} from '@/store/session'

/**
 * Home — Command center for AetherOS.
 *
 * Every state originates from live atoms fed by the gateway/IPC layer.
 * When the gateway is offline, panels say so explicitly instead of
 * rendering decorative zeros. Every major state carries a real action
 * wired to runtime methods — never a dead button.
 */
export function HomeView() {
  const navigate = useNavigate()
  const gatewayState = useStore($gatewayState)
  const sessions = useStore($sessions)
  const workingIds = useStore($workingSessionIds)
  const activeSessionId = useStore($activeSessionId)
  const approvals = useStore($allApprovalRequests)
  const cronJobs = useStore($cronJobs)
  const stats = useStore($systemStats)
  const health = useStore($healthStatus)
  const tokens = useStore($tokenUsage)
  const model = useStore($currentModel)

  const offline = gatewayState !== 'open' && gatewayState !== 'connected'
  const pendingApprovalSessions = useMemo(() => Object.keys(approvals), [approvals])

  const runningSessions = useMemo(
    () => sessions.filter(s => workingIds.includes(s.id)),
    [sessions, workingIds],
  )

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        {/* Hero — the central command workspace */}
        <IntentSection offline={offline} />

        {/* Quick actions — every card navigates to a real feature */}
        <QuickActionsSection offline={offline} />

        {/* Active work */}
        <ActiveWorkSection
          activeSessionId={activeSessionId}
          offline={offline}
          runningSessions={runningSessions}
        />

        {/* Recent work — real sessions only, honest empty state */}
        <RecentWorkSection offline={offline} />

        {/* System + model status */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="p-4">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
              System Health
            </h3>
            <SystemHealthBody health={health} offline={offline} stats={stats} />
          </Card>
          <Card className="p-4">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
              Model
            </h3>
            <ModelBody model={model} offline={offline} tokens={tokens} />
          </Card>
          <Card className="p-4">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
              Automations
            </h3>
            <AutomationsBody cronJobs={cronJobs} offline={offline} />
          </Card>
        </div>
      </div>
    </ScrollArea>
  )
}

/* ── Intent — the central interaction point ────────────────────────── */

function daypart(): string {
  const h = new Date().getHours()

  if (h < 5) {
    return 'Good night'
  }

  if (h < 12) {
    return 'Good morning'
  }

  if (h < 18) {
    return 'Good afternoon'
  }

  return 'Good evening'
}

interface Suggestion {
  description: string
  icon: string
  id: string
  label: string
  run: () => void
}

/**
 * Intent-first workspace header: contextual greeting, universal intent
 * input, and suggested actions derived from REAL state. Submitting hands
 * the text to the chat composer as a new-session draft (the agent loop
 * itself runs there) — Home never pretends to execute anything.
 */
function IntentSection({ offline }: { offline: boolean }) {
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const approvals = useStore($allApprovalRequests)
  const cronJobs = useStore($cronJobs)
  const sessions = useStore($sessions)
  const workingIds = useStore($workingSessionIds)
  const profile = useStore($activeProfile)

  const pendingCount = Object.keys(approvals).length
  const runningCount = sessions.filter(s => workingIds.includes(s.id)).length
  const scope = scopeDescription(buildContextChain({ profile }))

  const submit = useCallback(() => {
    const value = text.trim()

    if (!value || offline) {
      return
    }

    stashSessionDraft(null, value, [])
    setText('')
    navigate('/')
  }, [navigate, offline, text])

  // Navigating to Files/Jarvis unmounts Home and drops local `text`.
  // Stash it as a new-session draft first so nothing the user typed is lost.
  const stashAndGo = useCallback((route: string) => {
    if (text.trim()) {
      stashSessionDraft(null, text, [])
      setText('')
    }
    navigate(route)
  }, [navigate, text])

  const suggestions = useMemo<Suggestion[]>(() => {
    const items: Suggestion[] = []

    if (pendingCount > 0) {
      items.push({
        description: `${pendingCount} waiting for a decision`,
        icon: 'shield',
        id: 'review-approvals',
        label: 'Review approvals',
        run: () => navigate('/security'),
      })
    }

    if (runningCount > 0) {
      items.push({
        description: `${runningCount} active right now`,
        icon: 'pulse',
        id: 'inspect-agents',
        label: 'Inspect running agents',
        run: () => navigate('/agents'),
      })
    }

    const recent = sessions[0]

    if (recent) {
      items.push({
        description: sessionTitle(recent),
        icon: 'history',
        id: 'resume-work',
        label: 'Resume recent work',
        run: () => navigate(sessionRoute(recent.id)),
      })
    }

    if (cronJobs.length === 0) {
      items.push({
        description: 'Let AetherOS do recurring work',
        icon: 'zap',
        id: 'create-automation',
        label: 'Create an automation',
        run: () => navigate('/automation-center'),
      })
    }

    items.push({
      description: 'Files, apps, agents, commands',
      icon: 'search',
      id: 'command-palette',
      label: 'Search everything',
      run: () => openCommandPalette(),
    })

    return items.slice(0, 4)
  }, [cronJobs.length, navigate, pendingCount, runningCount, sessions])

  return (
    <Card className="overflow-hidden p-5 sm:p-8">
      <div className="flex items-center gap-4">
        <BrandMark className="size-14 shrink-0 rounded-[14px]" />
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-(--ui-text-tertiary)">
            {BRAND_WORDMARK} · {BRAND_TAGLINE}
          </p>
          <h2 className="mt-1 truncate text-xl font-semibold tracking-tight sm:text-2xl">
            {daypart()}
          </h2>
          <p className="mt-0.5 truncate text-sm text-(--ui-text-tertiary)">
            What would you like to accomplish?
          </p>
          <p className="mt-1 truncate text-sm text-(--ui-text-tertiary)" role="status">
            {offline
              ? 'Gateway offline — cached state only.'
              : runningCount > 0
                ? `${runningCount} agent${runningCount === 1 ? '' : 's'} working · ${pendingCount} approval${pendingCount === 1 ? '' : 's'} waiting`
                : pendingCount > 0
                  ? `${pendingCount} approval${pendingCount === 1 ? '' : 's'} waiting for you`
                  : 'Ask AetherOS to research, build, automate, organize, analyze, or execute.'}
          </p>
          {scope ? (
            <p className="mt-0.5 truncate text-xs text-(--ui-text-tertiary)">
              Using context from: {scope}
            </p>
          ) : null}
        </div>
      </div>

      <form
        className="mt-5"
        onSubmit={e => {
          e.preventDefault()
          submit()
        }}
      >
        <label className="mb-2 block text-sm font-medium" htmlFor="home-intent-input">
          What would you like AetherOS to do?
        </label>
        <div className="rounded-2xl border-2 border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/40 px-4 py-3 shadow-sm transition-all focus-within:border-(--dt-ring) focus-within:shadow-md focus-within:ring-2 focus-within:ring-(--dt-ring)/20">
          <label className="sr-only" htmlFor="home-intent-input">
            What would you like AetherOS to do?
          </label>
          <textarea
            aria-label="What would you like AetherOS to do?"
            className="max-h-40 min-h-12 w-full resize-y bg-transparent text-[0.9375rem] outline-none placeholder:text-(--ui-text-tertiary) disabled:cursor-not-allowed disabled:opacity-60"
            disabled={offline}
            id="home-intent-input"
            onChange={e => setText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder={offline ? 'What would you like AetherOS to do? (unavailable offline)' : 'What would you like AetherOS to do?'}
            rows={3}
            value={text}
          />
          <div className="mt-2 flex items-center gap-1.5">
            <span className="mr-auto hidden text-[0.6875rem] text-(--ui-text-tertiary) sm:inline">
              Enter to send · Shift+Enter for a new line
            </span>
            <Button
              aria-label="Attach files (opens Files)"
              className="size-8"
              disabled={offline}
              onClick={() => stashAndGo('/files')}
              size="icon-sm"
              title="Attach files (opens Files)"
              type="button"
              variant="ghost"
            >
              <span aria-hidden className="codicon codicon-attach" />
            </Button>
            <Button
              aria-label="Voice command (opens Jarvis)"
              className="size-8"
              disabled={offline}
              onClick={() => stashAndGo('/jarvis')}
              size="icon-sm"
              title="Voice command (opens Jarvis)"
              type="button"
              variant="ghost"
            >
              <span aria-hidden className="codicon codicon-mic" />
            </Button>
            <Button disabled={offline || !text.trim()} size="sm" type="submit">
              Send
            </Button>
          </div>
        </div>
      </form>

      <div aria-label="Suggested actions" className="mt-3 flex flex-wrap gap-2" role="list">
        {suggestions.map(s => (
          <button
            className="group flex items-center gap-2 rounded-lg border border-(--ui-stroke-tertiary) px-2.5 py-1.5 text-left text-xs transition-colors hover:border-(--dt-ring) hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-(--dt-ring)"
            key={s.id}
            onClick={s.run}
            role="listitem"
            type="button"
          >
            <span aria-hidden className={`codicon codicon-${s.icon} text-(--ui-text-tertiary) group-hover:text-foreground`} />
            <span>
              <span className="block font-medium">{s.label}</span>
              <span className="block text-(--ui-text-tertiary)">{s.description}</span>
            </span>
          </button>
        ))}
      </div>
    </Card>
  )
}

/* ── Quick actions — every card routes to a real feature ──────────── */

interface QuickAction {
  description: string
  icon: string
  id: string
  route: string
  title: string
}

export const QUICK_ACTIONS: QuickAction[] = [
  { id: 'qa-research', title: 'Research', description: 'Search and synthesize information', icon: 'book', route: KNOWLEDGE_ROUTE },
  { id: 'qa-create', title: 'Create', description: 'Start a new chat to create anything', icon: 'add', route: NEW_CHAT_ROUTE },
  { id: 'qa-code', title: 'Code', description: 'Inspect and modify projects', icon: 'symbol-method', route: '/projects' },
  { id: 'qa-browse', title: 'Browse', description: 'Browse the web with the agent', icon: 'globe', route: '/browser' },
  { id: 'qa-files', title: 'Files', description: 'Find, organize and inspect files', icon: 'file-directory', route: '/files' },
  { id: 'qa-automate', title: 'Automate', description: 'Create scheduled workflows', icon: 'zap', route: AUTOMATION_CENTER_ROUTE },
]

function QuickActionsSection({ offline }: { offline: boolean }) {
  const navigate = useNavigate()

  return (
    <section aria-label="Quick actions">
      <h2 className="mb-2 text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
        Quick actions
      </h2>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {QUICK_ACTIONS.map(action => (
          <button
            className="group flex flex-col items-start gap-2 rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-secondary)/40 p-3 text-left transition-all hover:-translate-y-px hover:border-(--dt-ring) hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--dt-ring) disabled:cursor-not-allowed disabled:opacity-60"
            disabled={offline}
            key={action.id}
            onClick={() => navigate(action.route)}
            title={offline ? 'Unavailable while offline' : action.description}
            type="button"
          >
            <span aria-hidden className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-(--ui-bg-tertiary)/60 transition-colors group-hover:bg-(--ui-control-hover-background)">
              <span className={`codicon codicon-${action.icon} text-(--ui-text-tertiary) group-hover:text-foreground`} />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{action.title}</span>
              <span className="block truncate text-xs text-(--ui-text-tertiary)">{action.description}</span>
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}

/* ── Active work ─────────────────────────────────────────────────── */

function ActiveWorkSection({
  activeSessionId,
  offline,
  runningSessions,
}: {
  activeSessionId: string | null
  offline: boolean
  runningSessions: ReturnType<typeof useStore<typeof $sessions>>
}) {
  const navigate = useNavigate()
  const gateway = useStore($gateway)

  const stopSession = useCallback(
    async (sessionId: string) => {
      if (!gateway) {
        return
      }

      try {
        await gateway.request('session.interrupt', { session_id: sessionId })
      } catch (e) {
        console.error(`Failed to stop session ${sessionId.slice(0, 8)}`, e)
      }
    },
    [gateway],
  )

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
          Active Work
        </h2>
        <span className="text-xs text-(--ui-text-tertiary)" role="status">
          {offline ? 'Paused — offline' : `Live · ${runningSessions.length} running`}
        </span>
      </div>
      {runningSessions.length === 0 ? (
        <div className="py-4 text-center">
          <p className="text-sm text-(--ui-text-tertiary)">
            {offline
              ? 'Live agent state is unavailable while offline.'
              : 'No agents running. Start a chat or create a task to put agents to work.'}
          </p>
          {!offline && (
            <div className="mt-3 flex justify-center gap-2">
              <Button onClick={() => navigate('/')} size="sm" variant="outline">
                New Chat
              </Button>
              <Button onClick={() => navigate('/tasks')} size="sm" variant="outline">
                Create Task
              </Button>
            </div>
          )}
        </div>
      ) : (
        <ul className="space-y-2">
          {runningSessions.map(session => (
            <li
              className={cn(
                'flex flex-wrap items-center gap-2 rounded-xl border p-3',
                session.id === activeSessionId
                  ? 'border-(--dt-ring)'
                  : 'border-(--ui-stroke-tertiary)',
              )}
              key={session.id}
            >
              <span aria-hidden className="size-2 shrink-0 rounded-full bg-blue-500" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{sessionTitle(session)}</div>
                <div className="truncate font-mono text-xs text-(--ui-text-tertiary)">
                  {session.id}
                  {session.id === activeSessionId ? ' · this session' : ''}
                </div>
              </div>
              <Button onClick={() => navigate(sessionRoute(session.id))} size="sm" variant="outline">
                Inspect
              </Button>
              <Button
                disabled={offline}
                onClick={() => stopSession(session.id)}
                size="sm"
                title={offline ? 'Unavailable while offline' : 'Interrupt this session'}
                variant="outline"
              >
                Stop
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

/* ── Recent work — real sessions, honest empty state ──────────────── */

function RecentWorkSection({ offline }: { offline: boolean }) {
  const navigate = useNavigate()
  const sessions = useStore($sessions)
  const recent = useMemo(() => sessions.slice(0, 5), [sessions])

  return (
    <section aria-label="Recent work">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
          Recent
        </h2>
        {recent.length > 0 && (
          <Button onClick={() => navigate('/history')} size="sm" variant="ghost">
            View all
          </Button>
        )}
      </div>
      {recent.length === 0 ? (
        <Card className="p-6 text-center">
          <p className="text-sm font-medium">No recent sessions</p>
          <p className="mt-1 text-sm text-(--ui-text-tertiary)">
            {offline
              ? 'Session history will appear here once the gateway reconnects.'
              : 'Start your first session to put AetherOS to work.'}
          </p>
          {!offline && (
            <Button className="mt-3" onClick={() => navigate(NEW_CHAT_ROUTE)} size="sm">
              Start your first session
            </Button>
          )}
        </Card>
      ) : (
        <ul className="space-y-1.5">
          {recent.map(session => (
            <li key={session.id}>
              <button
                className="flex w-full items-center gap-3 rounded-xl border border-(--ui-stroke-tertiary) p-2.5 text-left transition-colors hover:border-(--dt-ring) hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--dt-ring)"
                onClick={() => navigate(sessionRoute(session.id))}
                type="button"
              >
                <span aria-hidden className="codicon codicon-history shrink-0 text-(--ui-text-tertiary)" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{sessionTitle(session)}</span>
                  <span className="block truncate font-mono text-xs text-(--ui-text-tertiary)">{session.id}</span>
                </span>
                <span className="shrink-0 text-xs text-(--ui-text-tertiary)">Open</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/* ── System health (real stores, honest freshness) ───────────────── */

function SystemHealthBody({
  health,
  offline,
  stats,
}: {
  health: ReturnType<typeof useStore<typeof $healthStatus>>
  offline: boolean
  stats: ReturnType<typeof useStore<typeof $systemStats>>
}) {
  if (offline) {
    return <p className="text-sm text-(--ui-text-tertiary)">Unavailable — gateway offline.</p>
  }

  if (!stats && !health) {
    return (
      <div aria-label="Loading system health" className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-32" />
      </div>
    )
  }

  return (
    <dl className="space-y-3">
      <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
        <dt className="text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">CPU</dt>
        <dd className="mt-1 text-lg font-semibold tracking-tight">
          {stats ? `${stats.cpu}%` : 'Not reported'}
        </dd>
        {stats && <dd className="text-xs text-(--ui-text-tertiary)">{stats.platform}</dd>}
      </div>
      <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
        <dt className="text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Memory</dt>
        <dd className="mt-1 text-lg font-semibold tracking-tight">
          {stats
            ? `${Math.round(stats.memory.used / 1024)}GB / ${Math.round(stats.memory.total / 1024)}GB`
            : 'Not reported'}
        </dd>
      </div>
      <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
        <dt className="text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Status</dt>
        <dd className="mt-1 text-lg font-semibold tracking-tight">
          {health ? (health.overall === 'healthy' ? 'All Systems Go' : health.overall) : 'Not reported'}
        </dd>
        {health && (
          <dd className="text-xs text-(--ui-text-tertiary)">
            {health.services.length} service{health.services.length === 1 ? '' : 's'} reporting
          </dd>
        )}
      </div>
    </dl>
  )
}

function ModelBody({
  model,
  offline,
  tokens,
}: {
  model: string
  offline: boolean
  tokens: ReturnType<typeof useStore<typeof $tokenUsage>>
}) {
  const navigate = useNavigate()

  if (offline) {
    return <p className="text-sm text-(--ui-text-tertiary)">Unavailable — gateway offline.</p>
  }

  return (
    <div className="space-y-3">
      <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
        <div className="text-xs font-medium uppercase tracking-wider text-(--ui-text-tertiary)">
          Current Model
        </div>
        <div className="mt-1 text-lg font-semibold tracking-tight">{model || 'Not configured'}</div>
        <div className="mt-0.5 text-xs text-(--ui-text-tertiary)">
          {tokens.total > 0
            ? `${tokens.total.toLocaleString()} tokens this session (${tokens.input} in / ${tokens.output} out)`
            : 'No usage recorded this session'}
        </div>
      </div>
      <Button onClick={() => navigate('/models')} size="sm" variant="outline">
        {model ? 'Switch Model' : 'Choose Model'}
      </Button>
    </div>
  )
}

function AutomationsBody({
  cronJobs,
  offline,
}: {
  cronJobs: ReturnType<typeof useStore<typeof $cronJobs>>
  offline: boolean
}) {
  const navigate = useNavigate()

  if (offline) {
    return <p className="text-sm text-(--ui-text-tertiary)">Unavailable — gateway offline.</p>
  }

  if (cronJobs.length === 0) {
    return (
      <div className="py-2 text-center">
        <p className="text-sm text-(--ui-text-tertiary)">No scheduled automations.</p>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">
          Create an automation to let AetherOS perform recurring work for you.
        </p>
        <Button className="mt-3" onClick={() => navigate('/automation-center')} size="sm" variant="outline">
          Create Automation
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-sm" role="status">
        {cronJobs.length} scheduled automation{cronJobs.length === 1 ? '' : 's'}
        {' · '}
        {cronJobs.filter(j => j.enabled).length} active
      </p>
      <ul className="space-y-1.5">
        {cronJobs.slice(0, 4).map(job => (
          <li
            className="truncate rounded-lg border border-(--ui-stroke-tertiary) px-2.5 py-1.5 text-sm"
            key={job.id}
          >
            {job.name || job.id}
            {!job.enabled ? (
              <span className="ml-2 text-xs text-(--ui-text-tertiary)">disabled</span>
            ) : null}
          </li>
        ))}
      </ul>
      <Button onClick={() => navigate('/automation-center')} size="sm" variant="outline">
        Open Automations
      </Button>
    </div>
  )
}