import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { $setupWizard, updateExtensions } from '@/store/setup-wizard'

const EXTENSION_CATEGORIES = [
  {
    id: 'developer',
    name: 'Developer',
    description: 'Git, Docker, VS Code integration, debugging tools',
    icon: '{}'
  },
  {
    id: 'coding',
    name: 'Coding',
    description: 'Code generation, review, refactoring assistants',
    icon: '</>'
  },
  {
    id: 'research',
    name: 'Research',
    description: 'Web search, paper analysis, data gathering',
    icon: '🔍'
  },
  {
    id: 'writing',
    name: 'Writing',
    description: 'Content creation, editing, translation',
    icon: '✎'
  },
  {
    id: 'automation',
    name: 'Automation',
    description: 'Workflow automation, scheduled tasks, scripts',
    icon: '⚡'
  },
  {
    id: 'data-science',
    name: 'Data Science',
    description: 'Analysis, visualization, ML pipeline tools',
    icon: '📊'
  },
  {
    id: 'productivity',
    name: 'Productivity',
    description: 'Calendar, email, task management integration',
    icon: '✓'
  }
] as const

const RECOMMENDED_EXTENSIONS = [
  { name: 'GitHub Actions', category: 'developer', downloads: '120K' },
  { name: 'Docker Manager', category: 'developer', downloads: '85K' },
  { name: 'Code Assistant Pro', category: 'coding', downloads: '200K' },
  { name: 'Web Research Kit', category: 'research', downloads: '65K' },
  { name: 'Content Writer', category: 'writing', downloads: '45K' },
  { name: 'Workflow Builder', category: 'automation', downloads: '90K' },
  { name: 'Data Analyzer', category: 'data-science', downloads: '55K' },
  { name: 'Task Manager', category: 'productivity', downloads: '150K' }
]

export function ExtensionsStep() {
  const extensions = useStore($setupWizard).extensions
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<string | null>(null)

  const categoryKey = (id: string) => id.replace('-', '') as keyof typeof extensions
  const isSelected = (id: string) => extensions[categoryKey(id)]

  const filteredExtensions = RECOMMENDED_EXTENSIONS.filter(ext => {
    if (filter && ext.category !== filter) {return false}

    if (search && !ext.name.toLowerCase().includes(search.toLowerCase())) {return false}

    return true
  })

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Extensions</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose extension categories to install. You can add more later.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {EXTENSION_CATEGORIES.map(cat => (
          <button
            className={cn(
              'rounded-xl border p-4 text-left transition-all',
              isSelected(cat.id)
                ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
                : 'border-border hover:border-muted-foreground/30 hover:bg-accent/50'
            )}
            key={cat.id}
            onClick={() => updateExtensions({ [categoryKey(cat.id)]: !isSelected(cat.id) })}
            type="button"
          >
            <div className="mb-2 text-lg">{cat.icon}</div>
            <div className="text-sm font-medium">{cat.name}</div>
            <div className="mt-1 text-xs text-muted-foreground">{cat.description}</div>
          </button>
        ))}
      </div>

      <div>
        <h3 className="mb-3 text-sm font-medium text-muted-foreground">Popular Extensions</h3>
        <Input
          className="mb-3 font-mono text-sm"
          onChange={e => setSearch(e.target.value)}
          placeholder="Search extensions..."
          value={search}
        />
        <div className="space-y-2">
          {filteredExtensions.map(ext => (
            <div className="flex items-center justify-between rounded-lg border px-4 py-3" key={ext.name}>
              <div>
                <div className="text-sm font-medium">{ext.name}</div>
                <div className="text-xs text-muted-foreground capitalize">{ext.category} · {ext.downloads} downloads</div>
              </div>
              <Badge variant="secondary">Available</Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
