import React, { useState, useEffect } from 'react'
import { backupEngine, type BackupEntry, type RestorePlan, type BackupConfig } from './backup-engine'

export function BackupSettings() {
  const [config, setConfig] = useState<BackupConfig>(backupEngine.getConfig())
  const [backups, setBackups] = useState<BackupEntry[]>([])
  const [restoring, setRestoring] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    setBackups(backupEngine.getBackups())
  }, [])

  const handleCreateBackup = async () => {
    setStatus('Creating backup...')
    const manifest = await backupEngine.createFullBackup()
    setBackups(backupEngine.getBackups())
    setStatus(`Backup created: ${manifest.name}`)
  }

  const handleRestore = async (id: string) => {
    setRestoring(id)
    setStatus('Analyzing backup...')
    try {
      const plan = await backupEngine.analyzeRestore(id)
      setStatus(`Restore plan: ${plan.steps.length} steps, ${plan.requiresRestart ? 'restart required' : 'no restart needed'}`)
      const result = await backupEngine.restore(id, plan)
      setStatus(result.success ? 'Restore completed successfully' : `Restore failed: ${result.details}`)
    } catch (e) {
      setStatus(`Restore error: ${e}`)
    }
    setRestoring(null)
  }

  const handleDeleteBackup = async (id: string) => {
    await backupEngine.deleteBackup(id)
    setBackups(backupEngine.getBackups())
    setStatus('Backup deleted')
  }

  const handleConfigChange = (updates: Partial<BackupConfig>) => {
    backupEngine.updateConfig(updates)
    setConfig(backupEngine.getConfig())
  }

  const summary = backupEngine.getSummary()

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Backup & Restore</h2>
        <button
          onClick={handleCreateBackup}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Create Backup
        </button>
      </div>

      {status && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm">
          {status}
        </div>
      )}

      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
          <div className="text-2xl font-bold">{summary.totalBackups}</div>
          <div className="text-sm text-gray-500">Total Backups</div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
          <div className="text-2xl font-bold">{formatSize(summary.totalSize)}</div>
          <div className="text-sm text-gray-500">Storage Used</div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
          <div className="text-2xl font-bold">{summary.lastBackup ? new Date(summary.lastBackup).toLocaleDateString() : 'Never'}</div>
          <div className="text-sm text-gray-500">Last Backup</div>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
          <div className="text-2xl font-bold">{formatSize(summary.storageAvailable - summary.storageUsed)}</div>
          <div className="text-sm text-gray-500">Available Space</div>
        </div>
      </div>

      <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
        <h3 className="text-lg font-semibold mb-4">Settings</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={config.autoBackup} onChange={e => handleConfigChange({ autoBackup: e.target.checked })} />
            Automatic backups
          </label>
          {config.autoBackup && (
            <select value={config.schedule} onChange={e => handleConfigChange({ schedule: e.target.value as BackupConfig['schedule'] })} className="ml-6 p-1 border rounded">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          )}
          <div className="flex items-center gap-2">
            <label>Max backups:</label>
            <input type="number" value={config.maxBackups} min={1} max={50}
              onChange={e => handleConfigChange({ maxBackups: parseInt(e.target.value) || 10 })}
              className="w-20 p-1 border rounded" />
          </div>
        </div>
      </div>

      <div className="p-4 bg-white dark:bg-gray-800 rounded shadow">
        <h3 className="text-lg font-semibold mb-4">Backup History</h3>
        {backups.length === 0 ? (
          <p className="text-gray-500 text-sm">No backups yet. Click "Create Backup" to start.</p>
        ) : (
          <div className="space-y-2">
            {backups.map(backup => (
              <div key={backup.manifest.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded">
                <div>
                  <div className="font-medium">{backup.manifest.name}</div>
                  <div className="text-sm text-gray-500">
                    {backup.date.toLocaleString()} · {formatSize(backup.size)} · {backup.manifest.scope.join(', ')}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleRestore(backup.manifest.id)}
                    disabled={restoring === backup.manifest.id}
                    className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {restoring === backup.manifest.id ? 'Restoring...' : 'Restore'}
                  </button>
                  <button
                    onClick={() => handleDeleteBackup(backup.manifest.id)}
                    className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}
