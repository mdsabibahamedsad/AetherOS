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
import { Plus } from '@/lib/icons'
import type { ConnectorCatalogEntry } from '@/store/services'

interface ConnectWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  connector: ConnectorCatalogEntry | null
}

export function ConnectWizard({ open, onOpenChange, connector }: ConnectWizardProps) {
  if (!connector) {return null}

  const authLabels: Record<string, string> = {
    token: 'API Token',
    oauth: 'OAuth',
    webhook: 'Webhook URL',
    none: 'No Authentication'
  }

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <span
              className="inline-grid size-10 shrink-0 place-items-center rounded-lg text-base font-medium"
              style={{
                backgroundColor: `color-mix(in srgb, ${connector.color} 16%, transparent)`,
                color: connector.color
              }}
            >
              <Codicon name="plug" size="1.5rem" />
            </span>
            <div>
              <DialogTitle>Connect {connector.name}</DialogTitle>
              <DialogDescription>{connector.description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            {connector.popular && <Badge variant="default">Popular</Badge>}
            {connector.beta && <Badge variant="warn">Beta</Badge>}
            <Badge variant="outline">{authLabels[connector.authType]}</Badge>
            <Badge variant="muted">{connector.category.replace('-', ' ')}</Badge>
          </div>

          <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/30 p-4">
            <h4 className="mb-2 text-sm font-semibold">Setup Guide</h4>
            <p className="text-sm leading-relaxed text-(--ui-text-secondary)">{connector.setupGuide}</p>
          </div>

          {connector.authType !== 'none' && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
              <div className="flex items-start gap-2">
                <Codicon className="mt-0.5 shrink-0 text-amber-500" name="info" size="1rem" />
                <div>
                  <p className="text-sm font-medium text-amber-600 dark:text-amber-400">Authentication Required</p>
                  <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">
                    You will need to provide {connector.authType === 'oauth' ? 'OAuth credentials' : connector.authType === 'webhook' ? 'a webhook URL' : 'an API token'} during setup.
                    {connector.authType === 'token' && ' The token will be stored securely in your local environment.'}
                    {connector.authType === 'oauth' && ' The OAuth flow will open your browser for authorization.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div>
            <h4 className="mb-2 text-sm font-semibold">Steps</h4>
            <ol className="ml-4 list-decimal space-y-1 text-sm text-(--ui-text-secondary)">
              <li>Open the configuration page for {connector.name}</li>
              <li>Enter your {authLabels[connector.authType].toLowerCase()} credentials</li>
              <li>Enable the service and restart the gateway</li>
              <li>Verify the connection status shows "Connected"</li>
            </ol>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} size="sm" variant="ghost">
            Cancel
          </Button>
          <Button asChild size="sm">
            <a href={`/messaging?platform=${connector.id}`}>
              <Plus className="size-3.5" />
              Open Setup
            </a>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
