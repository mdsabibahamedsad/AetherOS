import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Codicon } from '@/components/ui/codicon'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  type PrivacyMode,
  setOfflineMode,
  setPrivacyMode,
  setTelemetryEnabled,
} from '@/store/security'

const PRIVACY_MODES: { id: PrivacyMode; label: string; description: string; icon: string }[] = [
  { id: 'offline', label: 'Offline Mode', description: 'Disable all network access for agents and plugins. No external connections allowed.', icon: 'globe' },
  { id: 'local-only', label: 'Local-Only Mode', description: 'Only allow connections to localhost and local network. Internet access blocked.', icon: 'home' },
  { id: 'no-telemetry', label: 'No Telemetry Mode', description: 'Disable all usage analytics, error reporting, and anonymous data collection.', icon: 'eye-closed' },
  { id: 'private', label: 'Private Mode', description: 'Maximum privacy. No data leaves your device. Local processing only.', icon: 'shield' },
  { id: 'strict-sandbox', label: 'Strict Sandbox Mode', description: 'All executions run in read-only sandboxes with no persistent storage.', icon: 'lock' },
]

export function PrivacySettings() {
  const [activeMode, setActiveMode] = useState<PrivacyMode | null>(null)
  const [offlineEnabled, setOfflineEnabled] = useState(false)
  const [telemetryEnabled, setTelemetry] = useState(false)

  const handleModeToggle = (mode: PrivacyMode) => {
    const newMode = activeMode === mode ? null : mode
    setActiveMode(newMode)
    setPrivacyMode(newMode)

    if (newMode) {
      notify({ kind: 'success', title: `${PRIVACY_MODES.find(m => m.id === newMode)?.label || newMode} Enabled`, message: 'Privacy mode has been activated' })
    } else {
      notify({ kind: 'info', title: 'Privacy Mode Disabled', message: 'Standard privacy settings restored' })
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="space-y-1">
        <h3 className="text-lg font-semibold">Privacy Settings</h3>
        <p className="text-sm text-muted-foreground">
          Control how AetherOS handles your data, network access, and telemetry. Privacy modes are enforced across all agents, plugins, and services.
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3.5">
          <div className="flex items-center gap-3">
            <Codicon name="plug" size="1rem" />
            <div>
              <div className="text-sm font-medium">Offline Mode</div>
              <div className="text-xs text-muted-foreground">Block all network connections. Agents run entirely offline.</div>
            </div>
          </div>
          <Switch
            checked={offlineEnabled}
            onCheckedChange={checked => {
              setOfflineEnabled(checked)
              setOfflineMode(checked)
              notify({ kind: 'info', title: checked ? 'Offline Mode Enabled' : 'Offline Mode Disabled', message: checked ? 'All network access blocked' : 'Network access restored' })
            }}
          />
        </div>

        <div className="flex items-center justify-between rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3.5">
          <div className="flex items-center gap-3">
            <Codicon name="graph" size="1rem" />
            <div>
              <div className="text-sm font-medium">Telemetry</div>
              <div className="text-xs text-muted-foreground">Send anonymous usage data to help improve AetherOS.</div>
            </div>
          </div>
          <Switch
            checked={telemetryEnabled}
            onCheckedChange={checked => {
              setTelemetry(checked)
              setTelemetryEnabled(checked)
              notify({ kind: 'info', title: checked ? 'Telemetry Enabled' : 'Telemetry Disabled', message: checked ? 'Anonymous usage data will be collected' : 'Telemetry collection stopped' })
            }}
          />
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <Codicon name="shield" size="1rem" />
          Privacy Modes
        </h4>
        <div className="space-y-2">
          {PRIVACY_MODES.map(mode => (
            <button
              className={cn(
                'flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-all',
                activeMode === mode.id ? 'border-primary/50 bg-primary/5' : 'border-(--ui-stroke-tertiary) hover:bg-accent/30'
              )}
              key={mode.id}
              onClick={() => handleModeToggle(mode.id)}
              type="button"
            >
              <Codicon
                className={cn('mt-0.5', activeMode === mode.id ? 'text-primary' : 'text-muted-foreground')}
                name={mode.icon}
                size="1rem"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{mode.label}</span>
                  {activeMode === mode.id && (
                    <Badge className="text-[0.5rem]" variant="default">Active</Badge>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{mode.description}</p>
              </div>
              <div className={cn(
                'mt-0.5 size-4 shrink-0 rounded-full border-2 transition-colors',
                activeMode === mode.id ? 'border-primary bg-primary' : 'border-muted-foreground/30'
              )}>
                {activeMode === mode.id && (
                  <Codicon className="block text-primary-foreground" name="check" size="0.75rem" />
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      <Separator />

      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
        <div className="flex items-start gap-2">
          <Codicon className="mt-0.5 shrink-0 text-amber-500" name="info" size="1rem" />
          <div className="text-xs text-amber-700">
            <strong>Privacy Note:</strong> When privacy modes are active, some features may be limited. Cloud sync, remote agent access, and certain provider APIs require network connectivity. Strict modes may prevent plugin installation and updates.
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-(--ui-stroke-tertiary) px-4 py-3">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Data Handling Policy</h4>
        <ul className="space-y-1 text-xs text-muted-foreground">
          <li className="flex items-start gap-2">
            <Codicon className="mt-0.5 shrink-0 text-emerald-500" name="check" size="0.75rem" />
            All secrets are encrypted at rest using AES-256-GCM
          </li>
          <li className="flex items-start gap-2">
            <Codicon className="mt-0.5 shrink-0 text-emerald-500" name="check" size="0.75rem" />
            Credentials are never written to logs or prompts
          </li>
          <li className="flex items-start gap-2">
            <Codicon className="mt-0.5 shrink-0 text-emerald-500" name="check" size="0.75rem" />
            No data is sent to external servers unless explicitly configured
          </li>
          <li className="flex items-start gap-2">
            <Codicon className="mt-0.5 shrink-0 text-emerald-500" name="check" size="0.75rem" />
            Audit logs are stored locally and never exfiltrated
          </li>
        </ul>
      </div>
    </div>
  )
}
