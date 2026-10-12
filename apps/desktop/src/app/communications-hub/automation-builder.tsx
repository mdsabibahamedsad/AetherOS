import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $communications, addActivity, addAutomationRule, removeAutomationRule, updateAutomationRule } from '@/store/communications'
import type { AutomationRule, CommsPlatformId } from '@/store/communications'

const TRIGGER_OPTIONS = [
  { value: 'message_received', label: 'Message Received' },
  { value: 'keyword_detected', label: 'Keyword Detected' },
  { value: 'sender_match', label: 'Sender Match' },
  { value: 'schedule', label: 'Schedule' },
]

const ACTION_OPTIONS = [
  { value: 'send_reply', label: 'Send Reply' },
  { value: 'generate_response', label: 'Generate Response' },
  { value: 'search_knowledge', label: 'Search Knowledge' },
  { value: 'notify', label: 'Notify User' },
  { value: 'run_agent', label: 'Run Agent' },
]

const PLATFORM_OPTIONS = [
  { value: 'all', label: 'All Platforms' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'discord', label: 'Discord' },
  { value: 'slack', label: 'Slack' },
  { value: 'gmail', label: 'Gmail' },
  { value: 'sms', label: 'SMS' },
]

export function AutomationBuilder() {
  const comms = useStore($communications)
  const [showBuilder, setShowBuilder] = useState(false)
  const [name, setName] = useState('')
  const [trigger, setTrigger] = useState('message_received')
  const [action, setAction] = useState('send_reply')
  const [platform, setPlatform] = useState('all')
  const [condition, setCondition] = useState('')
  const [requireApproval, setRequireApproval] = useState(true)
  const [keywords, setKeywords] = useState('')

  const handleCreate = () => {
    if (!name.trim()) {return}
    const triggerConfig: Record<string, unknown> = {}

    if (trigger === 'keyword_detected' && keywords.trim()) {
      triggerConfig.keywords = keywords.split(',').map(k => k.trim())
    }

    addAutomationRule({
      name: name.trim(),
      platform: platform as CommsPlatformId | 'all',
      trigger: trigger as any,
      condition,
      action: action as any,
      requireApproval,
      enabled: true,
    })
    addActivity({ type: 'ai_reply', platform: platform as any, description: `Automation rule created: ${name}`, platformName: platform === 'all' ? 'All' : platform })
    setName(''); setCondition(''); setKeywords('')
    setShowBuilder(false)
  }

  const ruleExecutions = comms.activityFeed.filter(a => a.type === 'ai_reply').slice(0, 5)

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <h2 className="text-sm font-semibold">Message Automation</h2>
        <button className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs text-white" onClick={() => setShowBuilder(!showBuilder)}>
          <span className="codicon codicon-add" />
          New Rule
        </button>
      </div>

      {/* Builder Panel */}
      {showBuilder && (
        <div className="shrink-0 border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Rule Name</label>
              <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setName(e.target.value)} placeholder="e.g., Away Message" type="text" value={name} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Platform</label>
              <select className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setPlatform(e.target.value)} value={platform}>
                {PLATFORM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Trigger</label>
              <select className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setTrigger(e.target.value)} value={trigger}>
                {TRIGGER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Action</label>
              <select className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setAction(e.target.value)} value={action}>
                {ACTION_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            {trigger === 'keyword_detected' && (
              <div className="col-span-2 space-y-1">
                <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Keywords (comma-separated)</label>
                <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setKeywords(e.target.value)} placeholder="urgent, help, question" type="text" value={keywords} />
              </div>
            )}
          </div>
          <div className="mt-2 space-y-1">
            <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Condition</label>
            <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setCondition(e.target.value)} placeholder="e.g., contains 'urgent' OR sender is 'John'" type="text" value={condition} />
          </div>
          <div className="mt-2 flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs">
              <input checked={requireApproval} className="rounded" onChange={e => setRequireApproval(e.target.checked)} type="checkbox" />
              Require approval before executing
            </label>
            <div className="flex gap-2">
              <button className="rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={() => setShowBuilder(false)}>Cancel</button>
              <button className="rounded-md bg-primary px-3 py-1.5 text-xs text-white" onClick={handleCreate}>Create Rule</button>
            </div>
          </div>
        </div>
      )}

      {/* Rules List */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {comms.automationRules.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)">
            <div className="text-center">
              <span className="codicon codicon-run-all text-3xl text-(--ui-text-tertiary)" />
              <p className="mt-2">No automation rules yet</p>
              <p className="text-xs">Create rules to automate repetitive communication</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-(--ui-stroke-tertiary)">
            {comms.automationRules.map(rule => (
              <AutomationRuleRow key={rule.id} rule={rule} />
            ))}
          </div>
        )}
      </div>

      {/* Recent Executions */}
      {ruleExecutions.length > 0 && (
        <div className="shrink-0 border-t border-(--ui-stroke-tertiary) p-3">
          <h3 className="text-[10px] font-medium text-(--ui-text-tertiary)">Recent Automation Activity</h3>
          <div className="mt-1 space-y-1">
            {ruleExecutions.map((a, i) => (
              <div className="flex items-center gap-2 text-[10px] text-(--ui-text-tertiary)" key={i}>
                <span className="codicon codicon-sparkle text-xs" />
                <span className="truncate">{a.description}</span>
                <span className="ml-auto shrink-0">{new Date(a.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AutomationRuleRow({ rule }: { rule: AutomationRule }) {
  const [isEnabled, setIsEnabled] = useState(rule.enabled)

  const handleToggle = () => {
    updateAutomationRule(rule.id, { enabled: !isEnabled })
    setIsEnabled(!isEnabled)
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className={`size-2 shrink-0 rounded-full ${isEnabled ? 'bg-green-500' : 'bg-(--ui-text-tertiary)'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">{rule.name}</span>
          <span className="rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)">{rule.platform === 'all' ? 'All' : rule.platform}</span>
          <span className="rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)">{rule.trigger}</span>
        </div>
        <p className="mt-0.5 text-[10px] text-(--ui-text-tertiary)">
          {rule.action} {rule.condition ? `| ${rule.condition}` : ''}
          {rule.requireApproval ? ' | Requires approval' : ''}
        </p>
      </div>
      <label className="relative inline-flex cursor-pointer items-center">
        <input checked={isEnabled} className="peer sr-only" onChange={handleToggle} type="checkbox" />
        <div className="h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" />
      </label>
      <button className="rounded p-1 text-xs text-(--ui-text-tertiary) hover:text-red-500" onClick={() => removeAutomationRule(rule.id)}>
        <span className="codicon codicon-trash" />
      </button>
    </div>
  )
}
