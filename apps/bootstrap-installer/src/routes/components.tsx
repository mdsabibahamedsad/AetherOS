import { useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { Button } from '../components/button'
import { FeatureCard } from '../components/feature-card'
import { StepIndicator } from '../components/progress-bar'
import { $route, $installConfig, startInstall } from '../store'
import { ArrowRight, Download } from 'lucide-react'

const INSTALL_STEPS = [
  { label: 'Welcome' },
  { label: 'Requirements' },
  { label: 'Location' },
  { label: 'Components' },
  { label: 'Runtimes' },
  { label: 'Install' },
]

interface ComponentDef {
  id: string
  name: string
  description: string
  icon?: string
  required?: boolean
  defaultSelected?: boolean
}

const AVAILABLE_COMPONENTS: ComponentDef[] = [
  {
    id: 'desktop',
    name: 'Desktop Application',
    description:
      'The full Aetheros desktop app with chat interface, settings, and system tray integration.',
    icon: 'desktop',
    defaultSelected: true,
  },
  {
    id: 'cli',
    name: 'CLI Tools',
    description:
      'Command-line interface for interacting with Aetheros from your terminal.',
    icon: 'cli',
    defaultSelected: true,
  },
  {
    id: 'shortcuts',
    name: 'Desktop Shortcuts',
    description:
      'Start menu and desktop shortcuts for quick access to Aetheros.',
    icon: 'shortcuts',
    defaultSelected: true,
  },
  {
    id: 'auto_launch',
    name: 'Auto-launch on startup',
    description:
      'Automatically start Aetheros when you log into your computer.',
    icon: 'auto_launch',
    defaultSelected: false,
  },
]

export default function Components() {
  const [selections, setSelections] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {}
    for (const comp of AVAILABLE_COMPONENTS) {
      initial[comp.id] = comp.defaultSelected ?? true
    }
    return initial
  })

  async function handleSelection(id: string, selected: boolean) {
    const next = { ...selections, [id]: selected }
    setSelections(next)
    $installConfig.setKey('install_desktop_app', next.desktop ?? true)
    $installConfig.setKey('install_cli', next.cli ?? true)
    $installConfig.setKey('create_shortcuts', next.shortcuts ?? true)
  }

  async function handleInstall() {
    await invoke('set_components', {
      desktopApp: selections.desktop ?? true,
      cli: selections.cli ?? true,
      shortcuts: selections.shortcuts ?? true,
      autoLaunch: selections.auto_launch ?? false,
    })
    await startInstall()
  }

  return (
    <div className="aetheros-fade-in flex h-full flex-col px-12 py-8">
      <StepIndicator steps={INSTALL_STEPS} current={3} className="mb-8" />

      <div className="flex-1">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">
            Choose Components
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Select the Aetheros components you want to install.
          </p>
        </div>

        <div className="space-y-3">
          {AVAILABLE_COMPONENTS.map((comp) => (
            <FeatureCard
              key={comp.id}
              id={comp.id}
              name={comp.name}
              description={comp.description}
              icon={comp.icon}
              selected={selections[comp.id] ?? true}
              required={comp.required}
              onChange={handleSelection}
            />
          ))}
        </div>

        <div className="mt-4 rounded-lg border border-border bg-card/50 px-4 py-3">
          <p className="text-xs text-muted-foreground/70">
            All components can be toggled later via the settings panel inside
            Aetheros.
          </p>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" onClick={() => $route.set('location')}>
          Back
        </Button>
        <Button
          onClick={() => void handleInstall()}
          className="inline-flex items-center gap-2"
        >
          <Download size={16} />
          Install
          <ArrowRight size={16} />
        </Button>
      </div>
    </div>
  )
}
