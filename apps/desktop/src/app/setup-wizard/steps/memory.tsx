import { useStore } from '@nanostores/react'

import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { $setupWizard, updateMemory } from '@/store/setup-wizard'

const MEMORY_OPTIONS = [
  { id: 'conversationMemory' as const, label: 'Conversation Memory', description: 'Remember context within active conversations' },
  { id: 'longTermMemory' as const, label: 'Long-term Memory', description: 'Retain knowledge across sessions over time' },
  { id: 'workspaceMemory' as const, label: 'Workspace Memory', description: 'Remember workspace state and file context' },
  { id: 'knowledgeBase' as const, label: 'Knowledge Base', description: 'Build a searchable knowledge base from interactions' },
  { id: 'vectorDatabase' as const, label: 'Vector Database', description: 'Enable semantic search across all memory' },
  { id: 'searchIndex' as const, label: 'Search Index', description: 'Full-text search across conversations and knowledge' },
  { id: 'compression' as const, label: 'Compression', description: 'Compress old memories to save space' }
]

export function MemoryStep() {
  const memory = useStore($setupWizard).memory

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Memory</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure how AetherOS remembers and learns
        </p>
      </div>

      <div className="space-y-3">
        {MEMORY_OPTIONS.map(opt => (
          <div className="flex items-center justify-between rounded-lg border p-4" key={opt.id}>
            <div>
              <Label className="text-base">{opt.label}</Label>
              <p className="text-sm text-muted-foreground">{opt.description}</p>
            </div>
            <Switch
              checked={memory[opt.id]}
              onCheckedChange={v => updateMemory({ [opt.id]: v })}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
