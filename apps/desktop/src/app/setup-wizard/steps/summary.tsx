import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { $setupWizard } from '@/store/setup-wizard'

function SummarySection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border p-4">
      <h3 className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wider">{title}</h3>
      {children}
    </div>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || '—'}</span>
    </div>
  )
}

export function SummaryStep() {
  const state = useStore($setupWizard)
  const p = state.profile
  const w = state.workspace

  return (
    <div className="mx-auto max-w-2xl space-y-6 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Review Your Settings</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Everything looks good? You can go back to make changes.
        </p>
      </div>

      <SummarySection title="Profile">
        <SummaryRow label="Display Name" value={p.displayName} />
        <SummaryRow label="Workspace" value={p.workspaceName} />
        <SummaryRow label="Language" value={p.language} />
        <SummaryRow label="Timezone" value={p.timezone} />
        <SummaryRow label="Theme" value={p.theme} />
        <SummaryRow label="Developer Mode" value={p.developerMode ? 'Enabled' : 'Disabled'} />
      </SummarySection>

      <SummarySection title="Workspace">
        {Object.entries(w).map(([key, val]) => (
          <SummaryRow key={key} label={key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())} value={val || 'Default'} />
        ))}
      </SummarySection>

      <SummarySection title="AI Providers">
        {state.providers.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {state.providers.map(p => (
              <Badge className="gap-1" key={p.slug} variant="secondary">
                {p.name}
                {p.authenticated && <span className="text-green-500">✓</span>}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No providers selected</p>
        )}
      </SummarySection>

      <SummarySection title="Models">
        {state.models.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {state.models.slice(0, 6).map(m => (
              <Badge className="font-mono text-xs" key={m.id} variant="outline">{m.name.split('/').pop()}</Badge>
            ))}
            {state.models.length > 6 && (
              <Badge variant="outline">+{state.models.length - 6} more</Badge>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No models selected</p>
        )}
      </SummarySection>

      <SummarySection title="Services">
        <div className="flex flex-wrap gap-2">
          {state.services.filter(s => s.enabled).length > 0 ? (
            state.services.filter(s => s.enabled).map(s => (
              <Badge key={s.id} variant="secondary">{s.name}</Badge>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No services enabled</p>
          )}
        </div>
      </SummarySection>

      <SummarySection title="Security">
        {Object.entries(state.security).filter(([, v]) => v).map(([key]) => (
          <Badge className="mr-1" key={key} variant="outline">{key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}</Badge>
        ))}
      </SummarySection>

      <SummarySection title="Extensions">
        {Object.entries(state.extensions).filter(([, v]) => v).length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {Object.entries(state.extensions).filter(([, v]) => v).map(([key]) => (
              <Badge key={key} variant="secondary">{key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())}</Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No extensions selected</p>
        )}
      </SummarySection>
    </div>
  )
}
