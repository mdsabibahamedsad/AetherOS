import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'

const STEPS = [
  { id: 'type', label: 'Type', icon: 'plug' },
  { id: 'config', label: 'Config', icon: 'gear' },
  { id: 'scope', label: 'Scope', icon: 'checklist' },
  { id: 'encryption', label: 'Encryption', icon: 'lock' },
  { id: 'test', label: 'Test', icon: 'beaker' },
  { id: 'summary', label: 'Summary', icon: 'check' },
] as const

type ConnectionType = 'direct' | 'relay' | 'lan' | 'vpn'
type EncryptionType = 'tls' | 'mtls' | 'psk' | 'none'

interface WizardState {
  connectionType: ConnectionType | null
  host: string
  port: string
  instanceName: string
  scopes: string[]
  encryption: EncryptionType
  psk: string
  autoReconnect: boolean
  tested: boolean
}

const INITIAL_WIZARD: WizardState = {
  connectionType: null,
  host: '',
  port: '9443',
  instanceName: '',
  scopes: ['messages', 'sessions', 'memory', 'files'],
  encryption: 'tls',
  psk: '',
  autoReconnect: true,
  tested: false,
}

const ALL_SCOPES = [
  { id: 'messages', label: 'Messages', desc: 'Conversation history and messages' },
  { id: 'sessions', label: 'Sessions', desc: 'Active session state' },
  { id: 'memory', label: 'Memory', desc: 'Agent memory and context' },
  { id: 'files', label: 'Files', desc: 'Workspace files' },
  { id: 'config', label: 'Config', desc: 'Settings and preferences' },
  { id: 'plugins', label: 'Plugins', desc: 'Plugin installations' },
  { id: 'skills', label: 'Skills', desc: 'Skill definitions' },
] as const

const connectionTypes: { id: ConnectionType; label: string; desc: string; icon: string }[] = [
  { id: 'direct', label: 'Direct Connection', desc: 'Connect directly via IP/hostname', icon: 'plug' },
  { id: 'relay', label: 'Relayed', desc: 'Connect through a relay server', icon: 'broadcast' },
  { id: 'lan', label: 'Local Network', desc: 'Auto-discover on the local network', icon: 'organization' },
  { id: 'vpn', label: 'VPN Tunnel', desc: 'Connect through encrypted tunnel', icon: 'shield' },
]

export function ConnectionWizardView() {
  const [currentStep, setCurrentStep] = useState(0)
  const [wizard, setWizard] = useState<WizardState>(INITIAL_WIZARD)

  const stepId = STEPS[currentStep].id
  const isFirst = currentStep === 0
  const isLast = currentStep === STEPS.length - 1

  const canProceed = useMemo(() => {
    switch (stepId) {
      case 'type': return wizard.connectionType !== null

      case 'config': return wizard.host.trim().length > 0 && wizard.instanceName.trim().length > 0

      case 'scope': return wizard.scopes.length > 0

      case 'encryption': return true

      case 'test': return true

      case 'summary': return true
    }
  }, [stepId, wizard])

  const handleNext = useCallback(() => {
    if (isLast) {
      notify({ kind: 'success', title: 'Connection Created', message: `Connection "${wizard.instanceName}" has been configured` })
      setCurrentStep(0)
      setWizard(INITIAL_WIZARD)

      return
    }

    if (canProceed) {
      setCurrentStep(s => Math.min(s + 1, STEPS.length - 1))
    }
  }, [isLast, canProceed, wizard])

  const handleBack = useCallback(() => {
    setCurrentStep(s => Math.max(s - 1, 0))
  }, [])

  const handleTest = useCallback(() => {
    setTimeout(() => {
      setWizard(w => ({ ...w, tested: true }))
      notify({ kind: 'success', title: 'Test Passed', message: `Successfully connected to ${wizard.host}:${wizard.port}` })
    }, 1500)
  }, [wizard.host, wizard.port])

  const toggleScope = useCallback((scopeId: string) => {
    setWizard(w => ({
      ...w,
      scopes: w.scopes.includes(scopeId)
        ? w.scopes.filter(s => s !== scopeId)
        : [...w.scopes, scopeId],
    }))
  }, [])

  const renderStep = () => {
    switch (stepId) {
      case 'type':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Choose Connection Type</h3>
            <div className="grid gap-2">
              {connectionTypes.map(ct => (
                <button
                  className={cn(
                    'flex items-center gap-3 rounded-lg border p-3 text-left transition-all',
                    wizard.connectionType === ct.id
                      ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
                      : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary) hover:bg-accent/30'
                  )}
                  key={ct.id}
                  onClick={() => setWizard(w => ({ ...w, connectionType: ct.id }))}
                  type="button"
                >
                  <span className={cn(
                    'flex size-9 items-center justify-center rounded-lg',
                    wizard.connectionType === ct.id ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                  )}>
                    <Codicon name={ct.icon} size="1rem" />
                  </span>
                  <div>
                    <p className="text-sm font-medium">{ct.label}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{ct.desc}</p>
                  </div>
                  {wizard.connectionType === ct.id && (
                    <Codicon className="ml-auto text-primary" name="check" size="1rem" />
                  )}
                </button>
              ))}
            </div>
          </div>
        )

      case 'config':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Connection Configuration</h3>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Instance Name</label>
              <Input
                onChange={e => setWizard(w => ({ ...w, instanceName: e.target.value }))}
                placeholder="My Remote Agent"
                value={wizard.instanceName}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Host</label>
              <Input
                onChange={e => setWizard(w => ({ ...w, host: e.target.value }))}
                placeholder="remote.example.com"
                value={wizard.host}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Port</label>
              <Input
                onChange={e => setWizard(w => ({ ...w, port: e.target.value }))}
                placeholder="9443"
                value={wizard.port}
              />
            </div>
            <div className="flex items-center justify-between rounded-md bg-(--ui-bg-quinary) px-3 py-2">
              <div>
                <p className="text-xs font-medium">Auto-Reconnect</p>
                <p className="text-[0.6rem] text-muted-foreground">Automatically reconnect on disconnect</p>
              </div>
              <Switch
                checked={wizard.autoReconnect}
                onCheckedChange={v => setWizard(w => ({ ...w, autoReconnect: v }))}
              />
            </div>
          </div>
        )

      case 'scope':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Select Sync Scopes</h3>
            <p className="text-xs text-muted-foreground">Choose which data scopes to synchronize with this connection</p>
            <div className="space-y-1.5">
              {ALL_SCOPES.map(scope => (
                <div
                  className={cn(
                    'flex items-center justify-between rounded-md border px-3 py-2 transition-colors',
                    wizard.scopes.includes(scope.id)
                      ? 'border-primary/30 bg-primary/5'
                      : 'border-(--ui-stroke-tertiary)'
                  )}
                  key={scope.id}
                >
                  <div>
                    <p className="text-xs font-medium">{scope.label}</p>
                    <p className="text-[0.6rem] text-muted-foreground">{scope.desc}</p>
                  </div>
                  <Switch checked={wizard.scopes.includes(scope.id)} onCheckedChange={() => toggleScope(scope.id)} />
                </div>
              ))}
            </div>
          </div>
        )

      case 'encryption':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Encryption Settings</h3>
            <div className="space-y-2">
              {([
                { id: 'tls' as EncryptionType, label: 'TLS', desc: 'Standard TLS encryption', icon: 'lock' },
                { id: 'mtls' as EncryptionType, label: 'mTLS', desc: 'Mutual TLS with client certificates', icon: 'verified' },
                { id: 'psk' as EncryptionType, label: 'Pre-Shared Key', desc: 'Symmetric key encryption', icon: 'key' },
                { id: 'none' as EncryptionType, label: 'None', desc: 'Unencrypted (not recommended)', icon: 'unlock' },
              ]).map(enc => (
                <button
                  className={cn(
                    'flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-all',
                    wizard.encryption === enc.id
                      ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/20'
                      : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
                  )}
                  key={enc.id}
                  onClick={() => setWizard(w => ({ ...w, encryption: enc.id }))}
                  type="button"
                >
                  <span className={cn(
                    'flex size-8 items-center justify-center rounded-lg',
                    wizard.encryption === enc.id ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                  )}>
                    <Codicon name={enc.icon} size="0.85rem" />
                  </span>
                  <div className="flex-1">
                    <p className="text-xs font-medium">{enc.label}</p>
                    <p className="text-[0.6rem] text-muted-foreground">{enc.desc}</p>
                  </div>
                  {wizard.encryption === enc.id && (
                    <Codicon className="text-primary" name="check" size="0.85rem" />
                  )}
                </button>
              ))}
            </div>
            {wizard.encryption === 'psk' && (
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Pre-Shared Key</label>
                <Input
                  onChange={e => setWizard(w => ({ ...w, psk: e.target.value }))}
                  placeholder="Enter shared key"
                  type="password"
                  value={wizard.psk}
                />
              </div>
            )}
          </div>
        )

      case 'test':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Test Connection</h3>
            <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Host</span>
                <span>{wizard.host}:{wizard.port}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Type</span>
                <span className="capitalize">{wizard.connectionType}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Encryption</span>
                <span>{wizard.encryption === 'none' ? 'None' : wizard.encryption.toUpperCase()}</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Scopes</span>
                <span>{wizard.scopes.length} selected</span>
              </div>
            </div>

            <Button className="w-full" disabled={wizard.tested} onClick={handleTest}>
              <Codicon name="beaker" size="0.85rem" />
              {wizard.tested ? 'Test Passed' : 'Run Connection Test'}
            </Button>

            {wizard.tested && (
              <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 px-3 py-2">
                <Codicon className="text-emerald-500" name="check" size="0.85rem" />
                <span className="text-xs text-emerald-600">Connection successful — latency 12ms</span>
              </div>
            )}
          </div>
        )

      case 'summary':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Connection Summary</h3>
            <div className="space-y-2 rounded-lg border border-(--ui-stroke-tertiary) p-3">
              {([
                { label: 'Name', value: wizard.instanceName },
                { label: 'Host', value: `${wizard.host}:${wizard.port}` },
                { label: 'Type', value: wizard.connectionType ?? '--' },
                { label: 'Encryption', value: wizard.encryption === 'none' ? 'None' : wizard.encryption.toUpperCase() },
                { label: 'Scopes', value: `${wizard.scopes.length} selected` },
                { label: 'Auto-Reconnect', value: wizard.autoReconnect ? 'Yes' : 'No' },
              ]).map(item => (
                <div className="flex items-center justify-between py-0.5 text-xs" key={item.label}>
                  <span className="text-muted-foreground">{item.label}</span>
                  <span className="font-medium">{item.value}</span>
                </div>
              ))}
            </div>
            <Badge className="w-full justify-center py-1" variant={wizard.tested ? 'default' : 'outline'}>
              {wizard.tested ? 'Connection verified' : 'Not tested'}
            </Badge>
          </div>
        )
    }
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>New Connection</PageTitle>
            <PageDescription>Set up a new remote connection step by step</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <div className="mx-auto max-w-lg">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            {STEPS.map((step, i) => (
              <div className="flex items-center" key={step.id}>
                <div className="flex flex-col items-center">
                  <span className={cn(
                    'flex size-8 items-center justify-center rounded-full text-xs font-medium transition-all',
                    i === currentStep
                      ? 'bg-primary text-primary-foreground ring-2 ring-primary/30'
                      : i < currentStep
                        ? 'bg-primary/20 text-primary'
                        : 'bg-muted text-muted-foreground'
                  )}>
                    {i < currentStep ? (
                      <Codicon name="check" size="0.75rem" />
                    ) : (
                      <Codicon name={step.icon} size="0.75rem" />
                    )}
                  </span>
                  <span className={cn(
                    'mt-1 text-[0.55rem]',
                    i === currentStep ? 'font-medium text-foreground' : 'text-muted-foreground'
                  )}>
                    {step.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={cn(
                    'mx-2 h-px w-8 sm:w-12',
                    i < currentStep ? 'bg-primary/40' : 'bg-(--ui-stroke-tertiary)'
                  )} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-4">
          {renderStep()}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <Button disabled={isFirst} onClick={handleBack} size="sm" variant="outline">
            <Codicon name="arrow-left" size="0.85rem" />
            Back
          </Button>
          <Button disabled={!canProceed} onClick={handleNext} size="sm">
            {isLast ? 'Finish' : 'Next'}
            {!isLast && <Codicon name="arrow-right" size="0.85rem" />}
          </Button>
        </div>
      </div>
    </PageShell>
  )
}
