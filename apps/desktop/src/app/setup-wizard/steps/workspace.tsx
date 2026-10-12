import { useStore } from '@nanostores/react'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { $setupWizard, updateWorkspace } from '@/store/setup-wizard'

const DEFAULT_PATHS = {
  workspaceFolder: '',
  projectsFolder: '',
  downloads: '',
  memoryStorage: '',
  cache: '',
  backups: ''
}

export function WorkspaceStep() {
  const w = useStore($setupWizard).workspace

  const browseFolder = (field: keyof typeof DEFAULT_PATHS) => {
    const dir = ''  // In real app, use Electron dialog.showOpenDialog

    if (dir) {updateWorkspace({ [field]: dir })}
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Workspace</h2>
        <p className="mt-1 text-sm text-muted-foreground">Configure your workspace directories</p>
      </div>

      <div className="space-y-4">
        {[
          { key: 'workspaceFolder' as const, label: 'Workspace Folder', placeholder: '~/aetheros' },
          { key: 'projectsFolder' as const, label: 'Projects Folder', placeholder: '~/aetheros/projects' },
          { key: 'downloads' as const, label: 'Downloads', placeholder: '~/aetheros/downloads' },
          { key: 'memoryStorage' as const, label: 'Memory Storage', placeholder: '~/aetheros/memory' },
          { key: 'cache' as const, label: 'Cache', placeholder: '~/aetheros/cache' },
          { key: 'backups' as const, label: 'Backups', placeholder: '~/aetheros/backups' }
        ].map(({ key, label, placeholder }) => (
          <div className="space-y-2" key={key}>
            <Label htmlFor={key}>{label}</Label>
            <div className="flex gap-2">
              <Input
                className="flex-1 font-mono text-sm"
                id={key}
                onChange={e => updateWorkspace({ [key]: e.target.value })}
                placeholder={placeholder}
                value={w[key]}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
