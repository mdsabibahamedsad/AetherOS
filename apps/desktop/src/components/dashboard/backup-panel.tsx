import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { $backupState, setBackupState } from '@/store/dashboard'

export function BackupPanel() {
  const backup = useStore($backupState)

  const statusColor: Record<string, 'default' | 'secondary' | 'muted' | 'destructive' | 'warn'> = {
    idle: 'secondary',
    running: 'default',
    success: 'default',
    error: 'destructive'
  }

  const statusLabel: Record<string, string> = {
    idle: 'Idle',
    running: 'Running…',
    success: 'Success',
    error: 'Error'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backup Status</CardTitle>
        <Badge variant={statusColor[backup.status]}>{statusLabel[backup.status]}</Badge>
      </CardHeader>
      <CardContent>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-(--ui-text-tertiary)">Schedule</dt>
            <dd className="font-medium capitalize">{backup.schedule}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-(--ui-text-tertiary)">Last Backup</dt>
            <dd className="font-medium">{backup.lastBackup ? formatTimestamp(backup.lastBackup) : 'Never'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-(--ui-text-tertiary)">Next Backup</dt>
            <dd className="font-medium">{backup.nextBackup ? formatTimestamp(backup.nextBackup) : 'Not scheduled'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-(--ui-text-tertiary)">Total Size</dt>
            <dd className="font-medium">{backup.totalSize}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-(--ui-text-tertiary)">Location</dt>
            <dd className="max-w-[200px] truncate font-mono text-xs">{backup.location}</dd>
          </div>
        </dl>
        <div className="mt-4 flex items-center gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3">
          <Button onClick={() => setBackupState({ status: 'running' })} size="sm">
            Backup Now
          </Button>
          <Button size="sm" variant="outline">
            Restore…
          </Button>
          <Button size="sm" variant="ghost">
            Configure
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  if (diff < 3600000) {return `${Math.floor(diff / 60000)}m ago`}

  if (diff < 86400000) {return `${Math.floor(diff / 3600000)}h ago`}

  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
