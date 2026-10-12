import { useStore } from '@nanostores/react'

import { $communications, setPlatformStatus, updateAIConfig, updateNotificationConfig, updateSecurity } from '@/store/communications'
import { $contacts } from '@/store/communications-contacts'

const PLATFORM_NAMES: Record<string, string> = {
  telegram: 'Telegram', whatsapp: 'WhatsApp', discord: 'Discord',
  slack: 'Slack', gmail: 'Gmail', outlook: 'Outlook', teams: 'Microsoft Teams',
  signal: 'Signal', sms: 'SMS Gateway', webhook: 'Webhook', 'custom-rest': 'Custom REST API',
}

const PLATFORM_AUTH: Record<string, { method: string; description: string }> = {
  telegram: { method: 'Bot Token or Account', description: 'Connect via bot token from @BotFather or official account linking' },
  whatsapp: { method: 'Business API', description: 'Connect via WhatsApp Business API (official)' },
  discord: { method: 'Bot Token', description: 'Connect via Discord bot token from Developer Portal' },
  slack: { method: 'OAuth', description: 'Connect via Slack OAuth with required scopes' },
  gmail: { method: 'OAuth 2.0', description: 'Connect via Google OAuth with Gmail API scopes' },
  sms: { method: 'API Key', description: 'Connect via SMS gateway provider API key' },
}

export function CommsSettings() {
  const comms = useStore($communications)
  const contacts = useStore($contacts)

  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="mx-auto max-w-2xl space-y-6">
        {/* Provider Accounts */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">Connected Accounts</h2>
          <div className="space-y-2">
            {comms.platformConnections.map(pc => (
              <div className="flex items-center justify-between rounded-lg border border-(--ui-stroke-tertiary) p-3" key={pc.id}>
                <div className="flex items-center gap-3">
                  <div className="flex size-8 items-center justify-center rounded-full" style={{ backgroundColor: pc.color + '20' }}>
                    <span className={`codicon codicon-${pc.icon} text-sm`} style={{ color: pc.color }} />
                  </div>
                  <div>
                    <p className="text-xs font-medium">{pc.name}</p>
                    <p className="text-[10px] text-(--ui-text-tertiary)">
                      {pc.connected ? `Connected • ${pc.messagesToday} msgs today` : 'Not connected'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {pc.connected ? (
                    <>
                      <span className={`flex items-center gap-1 text-[10px] ${pc.online ? 'text-green-500' : 'text-(--ui-text-tertiary)'}`}>
                        <span className="codicon codicon-primitive-dot" />
                        {pc.online ? 'Online' : 'Offline'}
                      </span>
                      <button className="rounded-md bg-red-500/10 px-2.5 py-1 text-xs text-red-500" onClick={() => setPlatformStatus(pc.id, false, false)}>
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <button className="rounded-md bg-primary px-2.5 py-1 text-xs text-white" onClick={() => setPlatformStatus(pc.id, true, true)}>
                      Connect
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Auth Methods */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">Authentication Methods</h2>
          <div className="space-y-2">
            {Object.entries(PLATFORM_AUTH).map(([id, auth]) => (
              <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3" key={id}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium">{PLATFORM_NAMES[id] || id}</p>
                    <p className="text-[10px] text-(--ui-text-tertiary)">{auth.method}</p>
                  </div>
                  <span className="text-[10px] text-(--ui-text-tertiary)">{auth.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* AI Config */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">AI Processing</h2>
          <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
            <ToggleRow
              checked={comms.aiConfig.smartSuggestions}
              description="Suggest AI replies for incoming messages"
              label="Smart Suggestions"
              onChange={v => updateAIConfig({ smartSuggestions: v })}
            />
            <ToggleRow
              checked={comms.aiConfig.autoReply}
              description="Automatically reply to messages based on rules"
              label="Auto Reply"
              onChange={v => updateAIConfig({ autoReply: v })}
            />
            <ToggleRow
              checked={comms.aiConfig.sentimentAnalysis}
              description="Detect message sentiment automatically"
              label="Sentiment Analysis"
              onChange={v => updateAIConfig({ sentimentAnalysis: v })}
            />
            <ToggleRow
              checked={comms.aiConfig.priorityDetection}
              description="Classify messages by urgency automatically"
              label="Priority Detection"
              onChange={v => updateAIConfig({ priorityDetection: v })}
            />
            <ToggleRow
              checked={comms.aiConfig.taskExtraction}
              description="Extract action items and tasks from messages"
              label="Task Extraction"
              onChange={v => updateAIConfig({ taskExtraction: v })}
            />
            <ToggleRow
              checked={comms.aiConfig.summarizeEnabled}
              description="Generate conversation summaries"
              label="Summarize Enabled"
              onChange={v => updateAIConfig({ summarizeEnabled: v })}
            />
          </div>
        </section>

        {/* Notifications */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">Notification Preferences</h2>
          <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
            <ToggleRow
              checked={comms.notificationConfig.desktopNotifications}
              description="Show desktop notifications for new messages"
              label="Desktop Notifications"
              onChange={v => updateNotificationConfig({ desktopNotifications: v })}
            />
            <ToggleRow
              checked={comms.notificationConfig.soundEnabled}
              description="Play notification sounds"
              label="Sound"
              onChange={v => updateNotificationConfig({ soundEnabled: v })}
            />
            <ToggleRow
              checked={comms.notificationConfig.doNotDisturb}
              description="Silence all notifications"
              label="Do Not Disturb"
              onChange={v => updateNotificationConfig({ doNotDisturb: v })}
            />
            <ToggleRow
              checked={comms.notificationConfig.priorityMode}
              description="Only show high priority and urgent notifications"
              label="Priority Mode"
              onChange={v => updateNotificationConfig({ priorityMode: v })}
            />
          </div>
        </section>

        {/* Security */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">Security & Privacy</h2>
          <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
            <ToggleRow
              checked={comms.security.encryptedTokens}
              description="Encrypt stored OAuth tokens and credentials"
              label="Encrypted Token Storage"
              onChange={v => updateSecurity({ encryptedTokens: v })}
            />
            <ToggleRow
              checked={comms.security.credentialVault}
              description="Use system credential vault for password storage"
              label="Credential Vault"
              onChange={v => updateSecurity({ credentialVault: v })}
            />
            <ToggleRow
              checked={comms.security.permissionManager}
              description="Require permission checks for sensitive operations"
              label="Permission Manager"
              onChange={v => updateSecurity({ permissionManager: v })}
            />
            <ToggleRow
              checked={comms.security.auditLog}
              description="Log all communications activity for review"
              label="Audit Log"
              onChange={v => updateSecurity({ auditLog: v })}
            />
          </div>
        </section>

        {/* Data */}
        <section>
          <h2 className="mb-3 text-sm font-semibold">Data Management</h2>
          <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-4">
            <p className="text-xs text-(--ui-text-tertiary)">
              {comms.messages.length} messages stored | {comms.conversations.length} conversations | {contacts.contacts.length} contacts
            </p>
            <div className="flex gap-2">
              <button className="rounded-md bg-(--ui-bg-quaternary) px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:text-foreground">
                Export Data
              </button>
              <button className="rounded-md bg-red-500/10 px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/20">
                Clear All Data
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function ToggleRow({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium">{label}</p>
        <p className="text-[10px] text-(--ui-text-tertiary)">{description}</p>
      </div>
      <label className="relative ml-3 inline-flex cursor-pointer items-center">
        <input checked={checked} className="peer sr-only" onChange={e => onChange(e.target.checked)} type="checkbox" />
        <div className="h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" />
      </label>
    </div>
  )
}
