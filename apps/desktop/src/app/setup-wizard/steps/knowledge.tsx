import { useStore } from '@nanostores/react'

import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { $setupWizard, updateKnowledge } from '@/store/setup-wizard'

const KNOWLEDGE_OPTIONS = [
  { id: 'importConversations' as const, label: 'Conversation History', description: 'Import past conversations for context and learning' },
  { id: 'importDocuments' as const, label: 'Documents', description: 'Import documents from your workspace folders' },
  { id: 'importProjects' as const, label: 'Projects', description: 'Import existing project files and configurations' },
  { id: 'importBookmarks' as const, label: 'Bookmarks', description: 'Import bookmarks and saved resources' },
  { id: 'importNotes' as const, label: 'Notes', description: 'Import notes and personal knowledge base' },
  { id: 'importCode' as const, label: 'Code Repositories', description: 'Import code repositories and snippets' },
  { id: 'autoSync' as const, label: 'Auto Sync', description: 'Automatically sync new content as it is added' }
]

export function KnowledgeStep() {
  const knowledge = useStore($setupWizard).knowledge

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Knowledge Import</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Import existing data so AetherOS can learn from your history
        </p>
      </div>

      <div className="space-y-3">
        {KNOWLEDGE_OPTIONS.map(opt => (
          <div className="flex items-center justify-between rounded-lg border p-4" key={opt.id}>
            <div>
              <Label className="text-base">{opt.label}</Label>
              <p className="text-sm text-muted-foreground">{opt.description}</p>
            </div>
            <Switch
              checked={knowledge[opt.id]}
              onCheckedChange={v => updateKnowledge({ [opt.id]: v })}
            />
          </div>
        ))}
      </div>
    </div>
  )
}