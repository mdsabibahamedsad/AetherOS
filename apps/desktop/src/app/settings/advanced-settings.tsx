import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

import { SettingSection } from './primitives'

export function AdvancedSettings() {
  const [hardwareAccel, setHardwareAccel] = useState(true)
  const [autoUpdates, setAutoUpdates] = useState(true)
  const [telemetry, setTelemetry] = useState(false)

  return (
    <div className="space-y-6">
      <SettingSection description="Performance and hardware settings" title="Performance">
        <div className="flex items-center justify-between">
          <div>
            <Label>Hardware Acceleration</Label>
            <p className="text-xs text-(--ui-text-tertiary)">Use GPU for rendering when available</p>
          </div>
          <Switch checked={hardwareAccel} onCheckedChange={setHardwareAccel} />
        </div>
      </SettingSection>

      <SettingSection description="Update preferences" title="Updates">
        <div className="flex items-center justify-between">
          <div>
            <Label>Automatic Updates</Label>
            <p className="text-xs text-(--ui-text-tertiary)">Automatically download and install updates</p>
          </div>
          <Switch checked={autoUpdates} onCheckedChange={setAutoUpdates} />
        </div>
      </SettingSection>

      <SettingSection description="Privacy and data collection" title="Privacy">
        <div className="flex items-center justify-between">
          <div>
            <Label>Telemetry</Label>
            <p className="text-xs text-(--ui-text-tertiary)">Send anonymous usage data to improve AetherOS</p>
          </div>
          <Switch checked={telemetry} onCheckedChange={setTelemetry} />
        </div>
      </SettingSection>

      <SettingSection description="Data management" title="Data">
        <div className="flex gap-2">
          <Button className="text-xs" onClick={() => {}} size="sm" variant="outline">
            Clear Cache
          </Button>
          <Button className="text-xs" onClick={() => {}} size="sm" variant="outline">
            Reset All Settings
          </Button>
          <Button className="text-xs text-destructive" onClick={() => {}} size="sm" variant="outline">
            Factory Reset
          </Button>
        </div>
      </SettingSection>
    </div>
  )
}
