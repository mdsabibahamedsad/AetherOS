import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { $setupWizard, toggleService } from '@/store/setup-wizard'

const SERVICE_ICONS: Record<string, string> = {
  github: 'GH',
  gitlab: 'GL',
  telegram: 'TG',
  discord: 'DC',
  slack: 'SL',
  gmail: 'GM',
  'google-drive': 'GD',
  onedrive: 'OD',
  dropbox: 'DB',
  notion: 'NT',
  calendar: 'CL',
  whatsapp: 'WA'
}

const SERVICE_GRADIENTS: Record<string, string> = {
  github: 'from-gray-700/30 to-gray-700/10',
  gitlab: 'from-orange-600/30 to-orange-600/10',
  telegram: 'from-sky-500/30 to-sky-500/10',
  discord: 'from-indigo-500/30 to-indigo-500/10',
  slack: 'from-purple-500/30 to-purple-500/10',
  gmail: 'from-red-500/30 to-red-500/10',
  'google-drive': 'from-green-500/30 to-green-500/10',
  onedrive: 'from-blue-500/30 to-blue-500/10',
  dropbox: 'from-blue-600/30 to-blue-600/10',
  notion: 'from-gray-600/30 to-gray-600/10',
  calendar: 'from-blue-400/30 to-blue-400/10',
  whatsapp: 'from-green-600/30 to-green-600/10'
}

export function ServicesStep() {
  const services = useStore($setupWizard).services

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Services</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Connect your accounts to enable integrations
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {services.map(service => (
          <div
            className={cn(
              'flex items-center gap-3 rounded-xl border p-4 transition-all',
              service.enabled ? 'border-primary/30 bg-primary/[0.03]' : 'border-border'
            )}
            key={service.id}
          >
            <div className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ring-1 ring-white/10',
              SERVICE_GRADIENTS[service.id] || 'from-gray-500/20 to-gray-500/5'
            )}>
              <span className="text-xs font-bold">{SERVICE_ICONS[service.id] || service.id.slice(0, 2).toUpperCase()}</span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{service.name}</div>
              <div className="flex items-center gap-2">
                {service.connected ? (
                  <Badge className="h-5 px-1.5 text-[10px] text-green-600 border-green-500/30" variant="outline">Connected</Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">Not connected</span>
                )}
              </div>
            </div>
            <Switch checked={service.enabled} onCheckedChange={() => toggleService(service.id)} />
          </div>
        ))}
      </div>
    </div>
  )
}
