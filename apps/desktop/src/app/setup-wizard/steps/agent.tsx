import { useStore } from '@nanostores/react'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { $setupWizard, updateAgent } from '@/store/setup-wizard'

const EXPERTISE_OPTIONS = [
  { value: 'coding', label: 'Coding' },
  { value: 'writing', label: 'Writing' },
  { value: 'research', label: 'Research' },
  { value: 'data', label: 'Data Science' },
  { value: 'design', label: 'Design' },
  { value: 'devops', label: 'DevOps' },
  { value: 'business', label: 'Business' },
  { value: 'creative', label: 'Creative' }
]

const PERSONALITY_OPTIONS = [
  { value: 'balanced', label: 'Balanced', description: 'Professional and adaptable' },
  { value: 'precise', label: 'Precise', description: 'Concise and technical' },
  { value: 'creative', label: 'Creative', description: 'Imaginative and exploratory' },
  { value: 'supportive', label: 'Supportive', description: 'Encouraging and helpful' },
  { value: 'analytical', label: 'Analytical', description: 'Logical and methodical' }
]

export function AgentStep() {
  const agent = useStore($setupWizard).agent

  const toggleExpertise = (value: string) => {
    const current = agent.expertise

    const updated = current.includes(value)
      ? current.filter(e => e !== value)
      : [...current, value]

    updateAgent({ expertise: updated })
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Your First Agent</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure your primary AI agent. You can change these settings later.
        </p>
      </div>

      {agent.autoCreate && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="agentName">Agent Name</Label>
            <Input
              className="font-mono text-sm"
              id="agentName"
              onChange={e => updateAgent({ name: e.target.value })}
              placeholder="AetherOS"
              value={agent.name}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="agentDescription">Description</Label>
            <Input
              className="font-mono text-sm"
              id="agentDescription"
              onChange={e => updateAgent({ description: e.target.value })}
              placeholder="Your personal AI assistant"
              value={agent.description}
            />
          </div>

          <div className="space-y-2">
            <Label>Personality</Label>
            <div className="grid grid-cols-1 gap-2">
              {PERSONALITY_OPTIONS.map(opt => (
                <button
                  className={`flex items-center gap-3 rounded-lg border p-3 text-left transition-all ${
                    agent.personality === opt.value
                      ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
                      : 'border-border hover:border-muted-foreground/30'
                  }`}
                  key={opt.value}
                  onClick={() => updateAgent({ personality: opt.value })}
                  type="button"
                >
                  <div className={`h-4 w-4 shrink-0 rounded-full border-2 ${
                    agent.personality === opt.value ? 'border-primary bg-primary' : 'border-muted-foreground/30'
                  }`}>
                    {agent.personality === opt.value && (
                      <div className="h-full w-full rounded-full bg-primary" />
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-medium">{opt.label}</div>
                    <div className="text-xs text-muted-foreground">{opt.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <Label>Areas of Expertise</Label>
            <div className="flex flex-wrap gap-2">
              {EXPERTISE_OPTIONS.map(opt => (
                <button
                  className={`rounded-full px-3 py-1.5 text-xs font-medium transition-all ${
                    agent.expertise.includes(opt.value)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-accent'
                  }`}
                  key={opt.value}
                  onClick={() => toggleExpertise(opt.value)}
                  type="button"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between rounded-lg border p-4">
        <div>
          <Label className="text-base">Create Agent on Setup</Label>
          <p className="text-sm text-muted-foreground">Automatically create your agent when setup completes</p>
        </div>
        <Switch
          checked={agent.autoCreate}
          onCheckedChange={v => updateAgent({ autoCreate: v })}
        />
      </div>
    </div>
  )
}