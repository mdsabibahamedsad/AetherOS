import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { CREDENTIAL_CONTROL_CLASS } from '@/app/settings/credential-key-ui'
import { ListRow } from '@/app/settings/primitives'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import {
  $communications,
  addAutomationRule,
  addTemplate,
  type AutomationRule,
  type MessageTemplate,
  removeAutomationRule,
  removeTemplate,
  updateAIConfig,
  updateAutomationRule,
  updateMediaConfig,
  updateNotificationConfig,
  updateSecurity,
  updateVoiceConfig
} from '@/store/communications'

export function AIFeaturesPanel() {
  const aiConfig = useStore($communications).aiConfig

  const features: { key: keyof typeof aiConfig; label: string; description: string }[] = [
    { key: 'autoReply', label: 'Auto Reply', description: 'Automatically reply to incoming messages using AI' },
    { key: 'smartSuggestions', label: 'Smart Suggestions', description: 'Suggest contextual replies as you type' },
    { key: 'rewriteEnabled', label: 'Rewrite', description: 'Reword messages for clarity and tone' },
    { key: 'translateEnabled', label: 'Translate', description: 'Translate messages between languages' },
    { key: 'summarizeEnabled', label: 'Summarize', description: 'Summarize long conversations and emails' },
    { key: 'sentimentAnalysis', label: 'Sentiment Analysis', description: 'Detect emotional tone of messages' },
    { key: 'priorityDetection', label: 'Priority Detection', description: 'Flag urgent and high-priority messages' },
    { key: 'spamDetection', label: 'Spam Detection', description: 'Identify and filter spam messages' },
    { key: 'meetingDetection', label: 'Meeting Detection', description: 'Detect meeting requests and calendar events' },
    { key: 'taskExtraction', label: 'Task Extraction', description: 'Extract action items and tasks from messages' }
  ]

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h3 className="text-sm font-semibold">AI Features</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">Configure AI-powered features for your communications</p>
      </div>

      <div className="space-y-1">
        {features.map(f => (
          <ListRow
            action={
              <Switch
                checked={aiConfig[f.key] as boolean}
                onCheckedChange={checked => updateAIConfig({ [f.key]: checked })}
                size="xs"
              />
            }
            description={f.description}
            key={f.key}
            title={f.label}
          />
        ))}
      </div>
    </div>
  )
}

const VOICE_PROVIDERS = [
  { id: 'whisper', label: 'Whisper (Local)' },
  { id: 'deepgram', label: 'Deepgram' },
  { id: 'openai-voice', label: 'OpenAI Voice' },
  { id: 'local-stt', label: 'Local STT' }
] as const

export function VoicePanel() {
  const voiceConfig = useStore($communications).voiceConfig

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h3 className="text-sm font-semibold">Voice Settings</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">Configure speech recognition and voice features</p>
      </div>

      <ListRow
        action={<Switch checked={voiceConfig.enabled} onCheckedChange={c => updateVoiceConfig({ enabled: c })} size="xs" />}
        description="Enable voice features across all platforms"
        title="Voice Enabled"
      />

      {voiceConfig.enabled && (
        <>
          <section>
            <h4 className="mb-2 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Provider</h4>
            <div className="flex flex-wrap gap-2">
              {VOICE_PROVIDERS.map(p => (
                <button
                  className={cn(
                    'rounded-lg border px-3 py-2 text-sm transition-colors',
                    voiceConfig.provider === p.id
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-(--ui-stroke-tertiary) text-(--ui-text-secondary) hover:text-foreground'
                  )}
                  key={p.id}
                  onClick={() => updateVoiceConfig({ provider: p.id as any })}
                  type="button"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </section>

          <div className="space-y-1">
            <ListRow
              action={<Switch checked={voiceConfig.pushToTalk} onCheckedChange={c => updateVoiceConfig({ pushToTalk: c })} size="xs" />}
              description="Hold a key to record voice input"
              title="Push to Talk"
            />
            <ListRow
              action={<Switch checked={voiceConfig.voiceCommands} onCheckedChange={c => updateVoiceConfig({ voiceCommands: c })} size="xs" />}
              description="Control the app with voice commands"
              title="Voice Commands"
            />
            <ListRow
              action={<Switch checked={voiceConfig.voiceReply} onCheckedChange={c => updateVoiceConfig({ voiceReply: c })} size="xs" />}
              description="Reply to messages using voice"
              title="Voice Reply"
            />
          </div>
        </>
      )}
    </div>
  )
}

export function MediaPanel() {
  const mediaConfig = useStore($communications).mediaConfig
  const mediaItems = useStore($communications).mediaItems

  return (
    <div className="mx-auto flex h-full min-h-0 max-w-4xl flex-col gap-6 p-6">
      <div>
        <h3 className="text-sm font-semibold">Media Settings</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">Configure media handling across all platforms</p>
      </div>

      <div className="space-y-1">
        <ListRow
          action={<Switch checked={mediaConfig.ocrEnabled} onCheckedChange={c => updateMediaConfig({ ocrEnabled: c })} size="xs" />}
          description="Extract text from images using OCR"
          title="OCR"
        />
        <ListRow
          action={<Switch checked={mediaConfig.visionEnabled} onCheckedChange={c => updateMediaConfig({ visionEnabled: c })} size="xs" />}
          description="Analyze images with computer vision"
          title="Vision"
        />
        <ListRow
          action={<Switch checked={mediaConfig.captionEnabled} onCheckedChange={c => updateMediaConfig({ captionEnabled: c })} size="xs" />}
          description="Auto-generate captions for images"
          title="Caption"
        />
        <ListRow
          action={<Switch checked={mediaConfig.summarizeMedia} onCheckedChange={c => updateMediaConfig({ summarizeMedia: c })} size="xs" />}
          description="Generate summaries of media content"
          title="Summarize Media"
        />
        <ListRow
          action={<Switch checked={mediaConfig.autoDownload} onCheckedChange={c => updateMediaConfig({ autoDownload: c })} size="xs" />}
          description="Automatically download media files"
          title="Auto Download"
        />
      </div>

      {mediaItems.length > 0 && (
        <section>
          <h4 className="mb-3 text-sm font-semibold">Recent Media ({mediaItems.length})</h4>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            {mediaItems.slice(0, 12).map(item => (
              <div className="rounded-lg border border-(--ui-stroke-tertiary) p-2" key={item.id}>
                <div className="flex items-center justify-center rounded bg-(--ui-row-active-background) py-6 text-xs text-(--ui-text-tertiary)">
                  {item.type.toUpperCase()}
                </div>
                <p className="mt-1 truncate text-xs">{item.name}</p>
                <p className="text-[0.55rem] text-(--ui-text-tertiary)">{formatSize(item.size)}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

export function NotificationsPanel() {
  const notifConfig = useStore($communications).notificationConfig

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h3 className="text-sm font-semibold">Notification Settings</h3>
        <p className="mt-1 text-xs text-(--ui-text-tertiary)">Configure how and when you get notified</p>
      </div>

      <div className="space-y-1">
        <ListRow
          action={<Switch checked={notifConfig.desktopNotifications} onCheckedChange={c => updateNotificationConfig({ desktopNotifications: c })} size="xs" />}
          description="Show desktop notifications for new messages"
          title="Desktop Notifications"
        />
        <ListRow
          action={<Switch checked={notifConfig.soundEnabled} onCheckedChange={c => updateNotificationConfig({ soundEnabled: c })} size="xs" />}
          description="Play notification sounds"
          title="Sound"
        />
        <ListRow
          action={<Switch checked={notifConfig.silentMode} onCheckedChange={c => updateNotificationConfig({ silentMode: c })} size="xs" />}
          description="Mute notifications during specified hours"
          title="Silent Mode"
        />
        {notifConfig.silentMode && (
          <div className="flex items-center gap-3 px-4 py-2">
            <span className="text-xs text-(--ui-text-secondary)">From</span>
            <Input
              className={cn('h-7 w-20 text-xs', CREDENTIAL_CONTROL_CLASS)}
              onChange={e => updateNotificationConfig({ silentModeStart: e.target.value })}
              type="time"
              value={notifConfig.silentModeStart}
            />
            <span className="text-xs text-(--ui-text-secondary)">To</span>
            <Input
              className={cn('h-7 w-20 text-xs', CREDENTIAL_CONTROL_CLASS)}
              onChange={e => updateNotificationConfig({ silentModeEnd: e.target.value })}
              type="time"
              value={notifConfig.silentModeEnd}
            />
          </div>
        )}
        <ListRow
          action={<Switch checked={notifConfig.priorityMode} onCheckedChange={c => updateNotificationConfig({ priorityMode: c })} size="xs" />}
          description="Only show notifications from priority contacts"
          title="Priority Mode"
        />
        <ListRow
          action={<Switch checked={notifConfig.doNotDisturb} onCheckedChange={c => updateNotificationConfig({ doNotDisturb: c })} size="xs" />}
          description="Mute all notifications"
          title="Do Not Disturb"
        />
      </div>
    </div>
  )
}

export function SettingsSecurityPanel() {
  const security = useStore($communications).security
  const [showTokens, setShowTokens] = useState(false)

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6">
      <section>
        <h3 className="mb-3 text-sm font-semibold">Security</h3>
        <div className="space-y-1">
          <ListRow
            action={<Switch checked={security.encryptedTokens} onCheckedChange={c => updateSecurity({ encryptedTokens: c })} size="xs" />}
            description="Encrypt all tokens and credentials at rest"
            title="Encrypted Tokens"
          />
          <ListRow
            action={<Switch checked={security.localStorage} onCheckedChange={c => updateSecurity({ localStorage: c })} size="xs" />}
            description="Store credentials in local secure storage"
            title="Local Storage"
          />
          <ListRow
            action={<Switch checked={security.credentialVault} onCheckedChange={c => updateSecurity({ credentialVault: c })} size="xs" />}
            description="Use system credential vault for secrets"
            title="Credential Vault"
          />
          <ListRow
            action={<Switch checked={security.permissionManager} onCheckedChange={c => updateSecurity({ permissionManager: c })} size="xs" />}
            description="Granular permission controls per platform"
            title="Permission Manager"
          />
          <ListRow
            action={<Switch checked={security.auditLog} onCheckedChange={c => updateSecurity({ auditLog: c })} size="xs" />}
            description="Log all access and configuration changes"
            title="Audit Log"
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Data Management</h3>
        <div className="space-y-1">
          <ListRow
            action={<Button size="xs" variant="textStrong">Export</Button>}
            description="Export all communications configuration"
            title="Export Configuration"
          />
          <ListRow
            action={<Button size="xs" variant="textStrong">Import</Button>}
            description="Import communications configuration from file"
            title="Import Configuration"
          />
          <ListRow
            action={<Button size="xs" variant="destructive">Clear All</Button>}
            description="Remove all platform connections and data"
            title="Delete All Connections"
          />
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold">Connection Management</h3>
        <div className="space-y-1">
          <ListRow
            action={<Button size="xs" variant="outline">Reconnect</Button>}
            description="Attempt to reconnect all disconnected platforms"
            title="Reconnect All"
          />
          <ListRow
            action={<Button size="xs" variant="outline">Backup</Button>}
            description="Create a backup of all connection configurations"
            title="Backup"
          />
          <ListRow
            action={<Button size="xs" variant="ghost">View Logs</Button>}
            description="View connection and communication logs"
            title="Communication Logs"
          />
        </div>
      </section>
    </div>
  )
}

export function AutomationCommsPanel() {
  const rules = useStore($communications).automationRules
  const [showNewForm, setShowNewForm] = useState(false)

  const [newRule, setNewRule] = useState<Omit<AutomationRule, 'id'>>({
    name: '',
    platform: 'all',
    trigger: 'message_received',
    condition: '',
    action: 'run_agent',
    requireApproval: false,
    enabled: true
  })

  const handleAdd = () => {
    if (!newRule.name.trim()) {return}
    addAutomationRule({ ...newRule, name: newRule.name.trim() })
    setNewRule({
      name: '',
      platform: 'all',
      trigger: 'message_received',
      condition: '',
      action: 'run_agent',
      requireApproval: false,
      enabled: true
    })
    setShowNewForm(false)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Communication Automations</h3>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Automate responses and actions across platforms</p>
        </div>
        <Button onClick={() => setShowNewForm(!showNewForm)} size="sm" variant="textStrong">
          + New Rule
        </Button>
      </div>

      {showNewForm && (
        <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
          <Input
            className="h-7 text-xs"
            onChange={e => setNewRule(r => ({ ...r, name: e.target.value }))}
            placeholder="Rule name..."
            value={newRule.name}
          />
          <div className="flex flex-wrap gap-2">
            <select
              className={CREDENTIAL_CONTROL_CLASS}
              onChange={e => setNewRule(r => ({ ...r, platform: e.target.value as any }))}
              value={newRule.platform}
            >
              <option value="all">All Platforms</option>
              <option value="telegram">Telegram</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="discord">Discord</option>
              <option value="slack">Slack</option>
              <option value="gmail">Gmail</option>
            </select>
            <select
              className={CREDENTIAL_CONTROL_CLASS}
              onChange={e => setNewRule(r => ({ ...r, trigger: e.target.value as any }))}
              value={newRule.trigger}
            >
              <option value="message_received">Message Received</option>
              <option value="keyword_detected">Keyword Detected</option>
              <option value="sender_match">Sender Match</option>
              <option value="schedule">Schedule</option>
            </select>
            <select
              className={CREDENTIAL_CONTROL_CLASS}
              onChange={e => setNewRule(r => ({ ...r, action: e.target.value as any }))}
              value={newRule.action}
            >
              <option value="run_agent">Run Agent</option>
              <option value="search_memory">Search Memory</option>
              <option value="search_knowledge">Search Knowledge</option>
              <option value="generate_response">Generate Response</option>
              <option value="send_reply">Send Reply</option>
            </select>
          </div>
          <Input
            className="h-7 text-xs"
            onChange={e => setNewRule(r => ({ ...r, condition: e.target.value }))}
            placeholder="Condition (e.g. contains 'urgent', from: user123)..."
            value={newRule.condition}
          />
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs">
              <Switch
                checked={newRule.requireApproval}
                onCheckedChange={c => setNewRule(r => ({ ...r, requireApproval: c }))}
                size="xs"
              />
              Require approval before sending
            </label>
            <div className="flex gap-2">
              <Button onClick={() => setShowNewForm(false)} size="xs" variant="ghost">Cancel</Button>
              <Button onClick={handleAdd} size="xs" variant="textStrong">Add Rule</Button>
            </div>
          </div>
        </div>
      )}

      {rules.length === 0 && !showNewForm && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-xs text-(--ui-text-tertiary)">No automation rules configured</p>
          <p className="mt-1 text-[0.65rem] text-(--ui-text-tertiary)">Create rules to automate responses across platforms</p>
        </div>
      )}

      <div className="space-y-1">
        {rules.map(rule => (
          <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={rule.id}>
            <Switch
              checked={rule.enabled}
              onCheckedChange={c => updateAutomationRule(rule.id, { enabled: c })}
              size="xs"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{rule.name}</span>
                <Badge className="px-1 py-0 text-[0.55rem]" variant="muted">{rule.trigger.replace(/_/g, ' ')}</Badge>
                <Badge className="px-1 py-0 text-[0.55rem]" variant="muted">{rule.action.replace(/_/g, ' ')}</Badge>
              </div>
              <p className="text-xs text-(--ui-text-tertiary)">{rule.platform === 'all' ? 'All platforms' : rule.platform} · {rule.condition || 'No condition'}</p>
            </div>
            <Button onClick={() => removeAutomationRule(rule.id)} size="xs" variant="ghost">×</Button>
          </div>
        ))}
      </div>
    </div>
  )
}

export function TemplatesPanel() {
  const templates = useStore($communications).templates
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [content, setContent] = useState('')
  const [platform, setPlatform] = useState<MessageTemplate['platform']>('all')

  const handleAdd = () => {
    if (!name.trim() || !content.trim()) {return}
    addTemplate({ name: name.trim(), content: content.trim(), platform, variables: [], category: 'custom' })
    setName('')
    setContent('')
    setShowForm(false)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Message Templates</h3>
          <p className="mt-1 text-xs text-(--ui-text-tertiary)">Reusable message templates for quick replies</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} size="sm" variant="textStrong">
          + New Template
        </Button>
      </div>

      {showForm && (
        <div className="space-y-3 rounded-lg border border-(--ui-stroke-tertiary) p-4">
          <Input
            className="h-7 text-xs"
            onChange={e => setName(e.target.value)}
            placeholder="Template name..."
            value={name}
          />
          <textarea
            className={cn('min-h-[80px] w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1.5 text-xs', CREDENTIAL_CONTROL_CLASS)}
            onChange={e => setContent(e.target.value)}
            placeholder="Template content..."
            value={content}
          />
          <div className="flex items-center justify-between">
            <select className={CREDENTIAL_CONTROL_CLASS} onChange={e => setPlatform(e.target.value as any)} value={platform}>
              <option value="all">All Platforms</option>
              <option value="telegram">Telegram</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="discord">Discord</option>
              <option value="slack">Slack</option>
              <option value="gmail">Gmail</option>
            </select>
            <div className="flex gap-2">
              <Button onClick={() => setShowForm(false)} size="xs" variant="ghost">Cancel</Button>
              <Button onClick={handleAdd} size="xs" variant="textStrong">Save</Button>
            </div>
          </div>
        </div>
      )}

      {templates.length === 0 && !showForm && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-xs text-(--ui-text-tertiary)">No templates yet</p>
        </div>
      )}

      <div className="space-y-1">
        {templates.map(tpl => (
          <div className="flex items-center gap-3 rounded-lg border border-(--ui-stroke-tertiary) px-3 py-2.5" key={tpl.id}>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{tpl.name}</span>
                <Badge className="px-1 py-0 text-[0.55rem]" variant="muted">{tpl.platform}</Badge>
              </div>
              <p className="mt-0.5 truncate text-xs text-(--ui-text-tertiary)">{tpl.content}</p>
            </div>
            <Button onClick={() => removeTemplate(tpl.id)} size="xs" variant="ghost">×</Button>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) {return `${bytes} B`}

  if (bytes < 1048576) {return `${(bytes / 1024).toFixed(1)} KB`}

  return `${(bytes / 1048576).toFixed(1)} MB`
}
