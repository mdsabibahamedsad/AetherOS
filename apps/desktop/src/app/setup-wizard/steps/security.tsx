import { useStore } from '@nanostores/react'

import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { $setupWizard, updateSecurity } from '@/store/setup-wizard'

const SECURITY_OPTIONS = [
  { id: 'encryption' as const, label: 'Encryption', description: 'Encrypt all stored data at rest' },
  { id: 'secureStorage' as const, label: 'Secure Storage', description: 'Use OS-level secure storage for credentials' },
  { id: 'autoLock' as const, label: 'Auto Lock', description: 'Lock the app after inactivity' },
  { id: 'biometricLock' as const, label: 'Biometric Lock', description: 'Use fingerprint or face ID to unlock' },
  { id: 'permissionSystem' as const, label: 'Permission System', description: 'Granular permission controls for tools and data' },
  { id: 'sandbox' as const, label: 'Sandbox', description: 'Run agent operations in isolated sandbox' },
  { id: 'workspaceIsolation' as const, label: 'Workspace Isolation', description: 'Isolate workspaces from each other' },
  { id: 'backupEncryption' as const, label: 'Backup Encryption', description: 'Encrypt backup archives' }
]

export function SecurityStep() {
  const security = useStore($setupWizard).security

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Security</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure security preferences
        </p>
      </div>

      <div className="space-y-3">
        {SECURITY_OPTIONS.map(opt => (
          <div className="flex items-center justify-between rounded-lg border p-4" key={opt.id}>
            <div>
              <Label className="text-base">{opt.label}</Label>
              <p className="text-sm text-muted-foreground">{opt.description}</p>
            </div>
            <Switch
              checked={security[opt.id]}
              onCheckedChange={v => updateSecurity({ [opt.id]: v })}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
