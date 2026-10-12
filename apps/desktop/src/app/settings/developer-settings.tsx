import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

import { SettingSection } from './primitives'

export function DeveloperSettings() {
  const [devMode, setDevMode] = useState(false)
  const [logLevel, setLogLevel] = useState('info')
  const [reactQueryDev, setReactQueryDev] = useState(false)

  return (
    <div className="space-y-6">
      <SettingSection description="Enable developer features and tools" title="Developer Mode">
        <div className="flex items-center justify-between">
          <div>
            <Label>Developer Mode</Label>
            <p className="text-xs text-(--ui-text-tertiary)">Enable developer tools and debug features</p>
          </div>
          <Switch checked={devMode} onCheckedChange={setDevMode} />
        </div>
      </SettingSection>

      <SettingSection description="Control log verbosity" title="Logging">
        <div className="space-y-2">
          <Label>Log Level</Label>
          <div className="flex gap-2">
            {['debug', 'info', 'warn', 'error'].map(level => (
              <Button
                className="text-xs capitalize"
                key={level}
                onClick={() => setLogLevel(level)}
                size="sm"
                variant={logLevel === level ? 'default' : 'outline'}
              >
                {level}
              </Button>
            ))}
          </div>
        </div>
      </SettingSection>

      <SettingSection description="Developer diagnostics tools" title="Diagnostics">
        <div className="flex items-center justify-between">
          <div>
            <Label>React Query Devtools</Label>
            <p className="text-xs text-(--ui-text-tertiary)">Show React Query devtools panel</p>
          </div>
          <Switch checked={reactQueryDev} onCheckedChange={setReactQueryDev} />
        </div>
        <div className="flex gap-2">
          <Button className="text-xs" onClick={() => window.location.reload()} size="sm" variant="outline">
            Reload Renderer
          </Button>
          <Button
            className="text-xs"
            onClick={() => window.aetherosDesktop?.revealLogs?.()?.catch(() => undefined)}
            size="sm"
            variant="outline"
          >
            Reveal Logs
          </Button>
        </div>
      </SettingSection>
    </div>
  )
}
