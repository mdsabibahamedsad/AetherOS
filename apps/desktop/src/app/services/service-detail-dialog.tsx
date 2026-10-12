import { StatusDot } from '@/components/status-dot'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { ExternalLink } from '@/lib/icons'
import type { ConnectedServiceInfo } from '@/store/services'

interface ServiceDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  service: ConnectedServiceInfo | null
  onToggle?: (id: string, name: string, enabled: boolean) => void
  saving?: string | null
}

export function ServiceDetailDialog({ open, onOpenChange, service, onToggle, saving }: ServiceDetailDialogProps) {
  if (!service) {return null}

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span
              className="inline-grid size-9 shrink-0 place-items-center rounded-lg text-sm font-medium"
              style={{
                backgroundColor: `color-mix(in srgb, ${service.color} 16%, transparent)`,
                color: service.color
              }}
            >
              <Codicon name="plug" size="1.25rem" />
            </span>
            <div>
              <DialogTitle>{service.name}</DialogTitle>
              <DialogDescription>{service.description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          <Section title="Status">
            <div className="flex flex-wrap items-center gap-2">
              <StatusDot tone={service.connected ? 'good' : service.enabled ? 'warn' : 'muted'} />
              <span className="text-sm capitalize">
                {service.connected ? 'Connected' : service.enabled ? 'Pending' : 'Disabled'}
              </span>
              <Badge variant={service.connected ? 'default' : 'muted'}>
                State: {service.state || 'unknown'}
              </Badge>
              {service.configured && <Badge variant="default">Configured</Badge>}
            </div>
          </Section>

          {service.error && (
            <Section title="Error">
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <Codicon name="error" size="1rem" />
                <span>{service.error}</span>
              </div>
            </Section>
          )}

          <Section title="Details">
            <div className="space-y-1 text-sm">
              <Row label="Service ID" value={service.id} />
              <Row label="Category" value={service.category} />
              {service.lastSync && (
                <Row label="Last Sync" value={new Date(service.lastSync).toLocaleString()} />
              )}
              {service.dataCount !== undefined && (
                <Row label="Data Items" value={String(service.dataCount)} />
              )}
            </div>
          </Section>

          <Section title="Quick Actions">
            <div className="flex flex-wrap gap-2">
              <Button asChild size="xs" variant="outline">
                <a href={`/messaging?platform=${service.id}`}>
                  <Codicon name="settings" size="0.875rem" />
                  Configure
                </a>
              </Button>
              <Button asChild size="xs" variant="outline">
                <a href={`/logs?service=${service.id}`}>
                  <Codicon name="output" size="0.875rem" />
                  View Logs
                </a>
              </Button>
              <Button asChild size="xs" variant="ghost">
                <a href={`https://opencode.ai/docs/platforms/${service.id}`} rel="noreferrer" target="_blank">
                  <ExternalLink className="size-3" />
                  Docs
                </a>
              </Button>
            </div>
          </Section>
        </div>

        <DialogFooter>
          {onToggle && (
            <div className="flex w-full items-center justify-between">
              <span className="text-sm text-(--ui-text-tertiary)">Enable service</span>
              <Switch
                aria-label={`${service.enabled ? 'Disable' : 'Enable'} ${service.name}`}
                checked={service.enabled}
                disabled={saving === `enabled:${service.id}`}
                onCheckedChange={checked => onToggle(service.id, service.name, checked)}
                size="xs"
              />
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Section({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <div>
      <h4 className="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{title}</h4>
      {children}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-(--ui-text-tertiary)">{label}</span>
      <span className="font-mono text-xs">{value}</span>
    </div>
  )
}
