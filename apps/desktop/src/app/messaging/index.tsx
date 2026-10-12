import { useStore } from '@nanostores/react'
import type * as React from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { StatusDot, type StatusTone } from '@/components/status-dot'
import { Button } from '@/components/ui/button'
import { DisclosureCaret } from '@/components/ui/disclosure-caret'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  getMessagingPlatforms,
  type MessagingEnvVarInfo,
  type MessagingPlatformInfo,
  updateMessagingPlatform
} from '@/hermes'
import { Activity, AlertTriangle, AudioLines, BarChart3, ExternalLink, ImageIcon, MessageCircle, MessageSquareText, Save, Settings, Trash2, Volume2, Zap } from '@/lib/icons'
import { cn } from '@/lib/utils'
import {
  $communications,
  clearActivity,
  type CommsHubTab,
  getAllPlatformMeta,
  getCommsStats,
  setCommsTab,
  setPlatformConnection,
  setPlatformStatus
} from '@/store/communications'
import { notify, notifyError } from '@/store/notifications'

import { useRefreshHotkey } from '../hooks/use-refresh-hotkey'
import { PageSearchShell } from '../page-search-shell'
import { CREDENTIAL_CONTROL_CLASS } from '../settings/credential-key-ui'
import { ListRow } from '../settings/primitives'
import type { SetStatusbarItemGroup } from '../shell/statusbar-controls'

import { AIFeaturesPanel, AutomationCommsPanel, MediaPanel, NotificationsPanel, SettingsSecurityPanel, VoicePanel } from './comms-panels'
import { DashboardView } from './dashboard-view'
import { PlatformAvatar } from './platform-icon'
import { UnifiedInbox } from './unified-inbox'

interface MessagingViewProps extends React.ComponentProps<'section'> {
  setStatusbarItemGroup?: SetStatusbarItemGroup
}

type EditMap = Record<string, Record<string, string>>

const TAB_ICONS: Record<CommsHubTab, typeof MessageCircle> = {
  dashboard: BarChart3,
  platforms: MessageCircle,
  inbox: MessageSquareText,
  ai: Zap,
  automation: BarChart3,
  voice: AudioLines,
  media: ImageIcon,
  notifications: Volume2,
  settings: Settings
}

const PILL_TONE: Record<StatusTone, string> = {
  good: 'bg-primary/10 text-primary',
  muted: 'bg-muted text-muted-foreground',
  warn: 'bg-amber-500/10 text-amber-600 dark:text-amber-300',
  bad: 'bg-destructive/10 text-destructive'
}

const stateLabel = (state: null | string | undefined) => state ? state.replace(/_/g, ' ') : 'unknown'

function stateTone({ enabled, state }: MessagingPlatformInfo): StatusTone {
  if (!enabled) {return 'muted'}

  if (state === 'connected') {return 'good'}

  if (state === 'fatal' || state === 'startup_failed') {return 'bad'}

  return 'warn'
}

const trimEdits = (edits: Record<string, string>): Record<string, string> =>
  Object.fromEntries(
    Object.entries(edits)
      .map(([k, v]) => [k, v.trim()])
      .filter(([, v]) => v)
  )

const FIELD_COPY: Record<string, { advanced?: boolean }> = {
  TELEGRAM_PROXY: { advanced: true },
  DISCORD_REPLY_TO_MODE: { advanced: true },
  DISCORD_ALLOW_ALL_USERS: { advanced: true },
  DISCORD_HOME_CHANNEL: { advanced: true },
  DISCORD_HOME_CHANNEL_NAME: { advanced: true },
  BLUEBUBBLES_ALLOW_ALL_USERS: { advanced: true },
  MATTERMOST_ALLOW_ALL_USERS: { advanced: true },
  MATTERMOST_HOME_CHANNEL: { advanced: true },
  QQ_ALLOW_ALL_USERS: { advanced: true },
  QQBOT_HOME_CHANNEL: { advanced: true },
  QQBOT_HOME_CHANNEL_NAME: { advanced: true },
  WHATSAPP_ENABLED: { advanced: true },
  WHATSAPP_MODE: { advanced: true }
}

function fieldCopy(field: MessagingEnvVarInfo): { label: string; help?: string; placeholder: string; advanced: boolean } {
  const copy = FIELD_COPY[field.key] || {}

  return {
    label: field.prompt || field.key,
    help: field.description,
    placeholder: field.prompt || '',
    advanced: Boolean(copy.advanced || field.advanced)
  }
}

const TABS: { id: CommsHubTab; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'platforms', label: 'Platforms' },
  { id: 'inbox', label: 'Inbox' },
  { id: 'ai', label: 'AI Features' },
  { id: 'automation', label: 'Automation' },
  { id: 'voice', label: 'Voice' },
  { id: 'media', label: 'Media' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'settings', label: 'Settings' }
]

export function MessagingView({ setStatusbarItemGroup: _setStatusbarItemGroup, ...props }: MessagingViewProps) {
  const [platforms, setPlatforms] = useState<MessagingPlatformInfo[] | null>(null)
  const [edits, setEdits] = useState<EditMap>({})
  const [query, setQuery] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [saving, setSaving] = useState<string | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const hubTab = useStore($communications).activeTab
  const connectState = useStore($communications)

  const platformIds = useMemo(() => platforms?.map(p => p.id) ?? [], [platforms])
  const [selectedId, setSelectedId] = useState<string>(platformIds[0] ?? '')

  const refreshPlatforms = useCallback(async (silent = false) => {
    if (!silent) {setRefreshing(true)}

    try {
      const result = await getMessagingPlatforms()
      setPlatforms(result.platforms)
      const meta = getAllPlatformMeta()

      for (const p of result.platforms) {
        const m = meta.find(m => m.id === p.id)

        if (m) {
          setPlatformConnection(m.id, {
            connected: p.state === 'connected',
            online: p.state === 'connected',
            name: m.name,
            icon: m.icon,
            color: m.color
          })
        }
      }
    } catch (err) {
      if (!silent) {notifyError(err, 'Failed to load platforms')}
    } finally {
      if (!silent) {setRefreshing(false)}
    }
  }, [])

  useRefreshHotkey(() => void refreshPlatforms())

  useEffect(() => { void refreshPlatforms() }, [refreshPlatforms])

  useEffect(() => {
    let cancelled = false

    function tick() {
      if (cancelled || document.hidden) {return}
      void refreshPlatforms(true)
    }

    const id = window.setInterval(tick, 10000)

    return () => { cancelled = true; window.clearInterval(id) }
  }, [refreshPlatforms])

  const visiblePlatforms = useMemo(() => {
    if (!platforms) {return []}
    const q = query.trim().toLowerCase()

    if (!q) {return platforms}

    return platforms.filter(p =>
      [p.id, p.name, p.description, p.state]
        .filter(Boolean)
        .some(v => String(v).toLowerCase().includes(q))
    )
  }, [platforms, query])

  const selected = useMemo(() => {
    if (!platforms) {return null}

    return platforms.find(p => p.id === selectedId) || platforms[0] || null
  }, [platforms, selectedId])

  useEffect(() => {
    if (platformIds.length > 0 && !platformIds.includes(selectedId)) {
      setSelectedId(platformIds[0])
    }
  }, [platformIds, selectedId])

  async function handleToggle(platform: MessagingPlatformInfo, enabled: boolean) {
    setSaving(`enabled:${platform.id}`)

    try {
      await updateMessagingPlatform(platform.id, { enabled })
      setPlatforms(current =>
        current?.map(row =>
          row.id === platform.id
            ? { ...row, enabled, state: enabled ? (row.configured ? 'pending_restart' : 'not_configured') : 'disabled' }
            : row
        ) ?? current
      )
      setPlatformStatus(platform.id as any, enabled, enabled)
      notify({ kind: 'success', title: enabled ? `${platform.name} enabled` : `${platform.name} disabled`, message: 'Restart gateway to apply' })
    } catch (err) {
      notifyError(err, `Failed to update ${platform.name}`)
    } finally {
      setSaving(null)
    }
  }

  async function handleSave(platform: MessagingPlatformInfo) {
    const env = trimEdits(edits[platform.id] || {})

    if (Object.keys(env).length === 0) {return}
    setSaving(`env:${platform.id}`)

    try {
      await updateMessagingPlatform(platform.id, { env })
      setEdits(current => ({ ...current, [platform.id]: {} }))
      await refreshPlatforms()
      notify({ kind: 'success', title: `Configuration saved for ${platform.name}`, message: 'Restart gateway to reconnect' })
    } catch (err) {
      notifyError(err, `Failed to save ${platform.name}`)
    } finally {
      setSaving(null)
    }
  }

  async function handleClear(platform: MessagingPlatformInfo, key: string) {
    setSaving(`clear:${key}`)

    try {
      await updateMessagingPlatform(platform.id, { clear_env: [key] })
      setEdits(current => ({
        ...current,
        [platform.id]: { ...(current[platform.id] || {}), [key]: '' }
      }))
      await refreshPlatforms()
      notify({ kind: 'success', title: `Cleared ${key}`, message: 'Configuration updated' })
    } catch (err) {
      notifyError(err, `Failed to clear ${key}`)
    } finally {
      setSaving(null)
    }
  }

  return (
    <PageSearchShell
      {...props}
      onSearchChange={setQuery}
      searchHidden={(platforms?.length ?? 0) === 0 || hubTab !== 'platforms'}
      searchPlaceholder="Search platforms..."
      searchValue={query}
    >
      <div className="flex h-full min-w-0 flex-col overflow-hidden bg-(--ui-chat-surface-background)">
        <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Communications Hub</h1>
            <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">
              {connectState.platformConnections.filter(p => p.connected).length} connected · {getCommsStats().messagesToday} messages today
            </p>
          </div>
          <div className="flex items-center gap-2">
            {hubTab === 'dashboard' && (
              <Button onClick={() => clearActivity()} size="xs" variant="ghost">Clear Activity</Button>
            )}
            <Button disabled={refreshing} onClick={() => void refreshPlatforms()} size="sm" variant="ghost">
              <Activity className={cn('size-3.5', refreshing && 'animate-spin')} />
            </Button>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-(--ui-stroke-tertiary) px-3">
          {TABS.map((tab: { id: CommsHubTab; label: string }) => {
            const Icon = TAB_ICONS[tab.id] || MessageCircle

            return (
              <button
                className={cn(
                  'flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                  hubTab === tab.id
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-(--ui-text-secondary) hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setCommsTab(tab.id)}
                type="button"
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="min-h-0 flex-1">
          {hubTab === 'dashboard' && <DashboardView />}

          {hubTab === 'platforms' && (
            <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[14rem_minmax(0,1fr)]">
              <aside className="min-h-0 overflow-y-auto border-r border-(--ui-stroke-tertiary) p-2">
                <ul className="space-y-1">
                  {visiblePlatforms.map(platform => (
                    <li key={platform.id}>
                      <button
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors',
                          selected?.id === platform.id
                            ? 'bg-(--ui-row-active-background) text-foreground'
                            : 'text-(--ui-text-secondary) hover:bg-(--ui-row-hover-background) hover:text-foreground'
                        )}
                        onClick={() => setSelectedId(platform.id)}
                        type="button"
                      >
                        <PlatformAvatar platformId={platform.id} platformName={platform.name} />
                        <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
                          <span className="truncate text-sm font-normal">{platform.name}</span>
                          <StatusDot tone={stateTone(platform)} />
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </aside>

              <main className="min-h-0 overflow-hidden">
                {selected && (
                  <PlatformDetail
                    edits={edits[selected.id] || {}}
                    onClear={key => void handleClear(selected, key)}
                    onEdit={(key, value) =>
                      setEdits(current => ({
                        ...current,
                        [selected.id]: { ...(current[selected.id] || {}), [key]: value }
                      }))
                    }
                    onSave={() => void handleSave(selected)}
                    onShowAdvanced={setShowAdvanced}
                    onToggle={enabled => void handleToggle(selected, enabled)}
                    platform={selected}
                    saving={saving}
                    showAdvanced={showAdvanced}
                  />
                )}
              </main>
            </div>
          )}

          {hubTab === 'inbox' && <UnifiedInbox />}
          {hubTab === 'ai' && <AIFeaturesPanel />}
          {hubTab === 'automation' && <AutomationCommsPanel />}
          {hubTab === 'voice' && <VoicePanel />}
          {hubTab === 'media' && <MediaPanel />}
          {hubTab === 'notifications' && <NotificationsPanel />}
          {hubTab === 'settings' && <SettingsSecurityPanel />}
        </div>
      </div>
    </PageSearchShell>
  )
}

function PlatformDetail({
  edits,
  onClear,
  onEdit,
  onSave,
  onToggle,
  platform,
  saving,
  showAdvanced,
  onShowAdvanced
}: {
  edits: Record<string, string>
  onClear: (key: string) => void
  onEdit: (key: string, value: string) => void
  onSave: () => void
  onToggle: (enabled: boolean) => void
  platform: MessagingPlatformInfo
  saving: string | null
  showAdvanced: boolean
  onShowAdvanced: (v: boolean) => void
}) {
  const hasEdits = Object.keys(trimEdits(edits)).length > 0
  const requiredFields = platform.env_vars.filter((f: MessagingEnvVarInfo) => f.required)
  const optionalFields = platform.env_vars.filter((f: MessagingEnvVarInfo) => !f.required && !fieldCopy(f).advanced)
  const advancedFields = platform.env_vars.filter((f: MessagingEnvVarInfo) => !f.required && fieldCopy(f).advanced)
  const hiddenCount = advancedFields.length
  const isSavingEnv = saving === `env:${platform.id}`

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl space-y-5 px-5 py-4">
          <header className="flex items-start gap-3">
            <PlatformAvatar platformId={platform.id} platformName={platform.name} />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold tracking-tight">{platform.name}</h3>
              <p className="mt-1 text-xs leading-relaxed text-(--ui-text-tertiary)">{platform.description}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Pill tone={stateTone(platform)}>{stateLabel(platform.state)}</Pill>
                <SetupPill active={platform.configured}>
                  {platform.configured ? 'Credentials Set' : 'Needs Setup'}
                </SetupPill>
                {!platform.gateway_running && <SetupPill active={false}>Gateway Stopped</SetupPill>}
              </div>
            </div>
          </header>

          {platform.error_message && (
            <div className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
              <span>{platform.error_message}</span>
            </div>
          )}

          <section>
            <SectionTitle>Credentials</SectionTitle>
            <div className="mt-3">
              <Button asChild size="sm" variant="textStrong">
                <a href={platform.docs_url} rel="noreferrer" target="_blank">
                  Setup Guide
                  <ExternalLink className="size-3.5" />
                </a>
              </Button>
            </div>
          </section>

          <section>
            <SectionTitle>Required</SectionTitle>
            <div className="mt-3 grid gap-1">
          {requiredFields.length > 0 ? requiredFields.map((field: MessagingEnvVarInfo) => (
            <MessagingField
              edits={edits}
              field={field}
              key={field.key}
              onClear={onClear}
              onEdit={onEdit}
              saving={saving}
            />
          )) : (
                <p className="text-xs text-(--ui-text-tertiary)">No credentials needed</p>
              )}
            </div>
          </section>

          {optionalFields.length > 0 && (
            <section>
              <SectionTitle>Optional</SectionTitle>
              <div className="mt-3 grid gap-1">
                {optionalFields.map((field: MessagingEnvVarInfo) => (
                  <MessagingField
                    edits={edits}
                    field={field}
                    key={field.key}
                    onClear={onClear}
                    onEdit={onEdit}
                    saving={saving}
                  />
                ))}
              </div>
            </section>
          )}

          {hiddenCount > 0 && (
            <section>
              <button
                className="flex w-full items-center justify-between gap-2 py-0.5 text-left text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => onShowAdvanced(!showAdvanced)}
                type="button"
              >
                <span>Advanced ({hiddenCount})</span>
                <DisclosureCaret open={showAdvanced} size="0.875rem" />
              </button>
              {showAdvanced && (
                <div className="mt-3 grid gap-1">
                  {advancedFields.map((field: MessagingEnvVarInfo) => (
                    <MessagingField
                      edits={edits}
                      field={field}
                      key={field.key}
                      onClear={onClear}
                      onEdit={onEdit}
                      saving={saving}
                    />
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </div>

      <footer className="bg-(--ui-chat-surface-background) px-5 py-2.5">
        <div className="mx-auto flex max-w-2xl flex-wrap items-center gap-2">
          <Switch
            aria-label={platform.enabled ? `Disable ${platform.name}` : `Enable ${platform.name}`}
            checked={platform.enabled}
            disabled={saving === `enabled:${platform.id}`}
            onCheckedChange={onToggle}
            size="xs"
          />
          <div className="ml-auto flex items-center gap-2">
            {hasEdits && <span className="text-xs text-muted-foreground">Unsaved changes</span>}
            <Button disabled={!hasEdits || isSavingEnv} onClick={onSave} size="sm">
              <Save />
              {isSavingEnv ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}

function MessagingField({
  edits,
  field,
  onClear,
  onEdit,
  saving
}: {
  edits: Record<string, string>
  field: MessagingEnvVarInfo
  onClear: (key: string) => void
  onEdit: (key: string, value: string) => void
  saving: string | null
}) {
  const copy = fieldCopy(field)
  const fieldId = `messaging-field-${field.key}`

  return (
    <ListRow
      action={
        <div className="flex items-center gap-2">
          <Input
            className={CREDENTIAL_CONTROL_CLASS}
            id={fieldId}
            onChange={event => onEdit(field.key, event.target.value)}
            placeholder={field.is_set ? field.redacted_value || 'Replace value' : copy.placeholder}
            type={field.is_password ? 'password' : 'text'}
            value={edits[field.key] || ''}
          />
          {field.url && (
            <Button asChild className="size-8 shrink-0" variant="ghost">
              <a href={field.url} rel="noreferrer" target="_blank">
                <ExternalLink className="size-3.5" />
              </a>
            </Button>
          )}
          {field.is_set && (
            <Button
              className="size-8 shrink-0"
              disabled={saving === `clear:${field.key}`}
              onClick={() => onClear(field.key)}
              variant="ghost"
            >
              <Trash2 className="size-3.5" />
            </Button>
          )}
        </div>
      }
      description={copy.help}
      title={
        <span className="flex flex-wrap items-center gap-2">
          <label htmlFor={fieldId}>{copy.label}</label>
          {field.is_set && <span className="text-[0.66rem] font-medium text-primary">Saved</span>}
        </span>
      }
    />
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h4 className="text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{children}</h4>
}

function Pill({ children, tone }: { children: string; tone: StatusTone }) {
  return (
    <span className={cn('inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[0.66rem] font-medium', PILL_TONE[tone])}>
      <StatusDot tone={tone} />
      {children}
    </span>
  )
}

function SetupPill({ active, children }: { active: boolean; children: string }) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-[0.66rem] font-medium', PILL_TONE[active ? 'good' : 'muted'])}>
      {children}
    </span>
  )
}
