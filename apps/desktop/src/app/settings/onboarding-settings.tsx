import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  getMessagingPlatforms,
  testMessagingPlatform,
  validateProviderCredential
} from '@/hermes'
import { Check, ChevronRight, ExternalLink, Loader2 } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { startManualOnboarding } from '@/store/onboarding'

export function OnboardingSettings() {
  const [testingProviders, setTestingProviders] = useState(false)
  const [testingIntegrations, setTestingIntegrations] = useState(false)
  const [results, setResults] = useState<{ providers: number; integrations: number } | null>(null)

  const handleRerun = () => {
    startManualOnboarding('Re-run the onboarding wizard to update your configuration.')
  }

  const handleDiagnoseAll = async () => {
    setTestingProviders(true)
    setTestingIntegrations(true)
    setResults(null)

    let providerOk = 0
    let integrationOk = 0

    const providerKeys = [
      'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY',
      'OPENROUTER_API_KEY', 'GROQ_API_KEY', 'MISTRAL_API_KEY',
      'DEEPSEEK_API_KEY', 'TOGETHER_API_KEY', 'XAI_API_KEY',
      'NOVITA_API_KEY', 'DASHSCOPE_API_KEY'
    ]

    for (const key of providerKeys) {
      try {
        const result = await validateProviderCredential(key, 'probe', '')

        if (result.ok && result.reachable) {
          providerOk++
        }
      } catch { }
    }

    try {
      const platforms = await getMessagingPlatforms()

      for (const platform of platforms.platforms) {
        if (platform.configured && platform.enabled) {
          try {
            const test = await testMessagingPlatform(platform.id)

            if (test.ok) {
              integrationOk++
            }
          } catch { }
        }
      }
    } catch { }

    setResults({ providers: providerOk, integrations: integrationOk })
    setTestingProviders(false)
    setTestingIntegrations(false)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight">Onboarding &amp; Setup</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Re-run the onboarding wizard or diagnose your current configuration.
        </p>
      </div>

      <div className="space-y-4">
        <div className="rounded-lg border border-border bg-card/30 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Re-run Onboarding Wizard</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Go through the full setup process again to configure providers, gateway, and integrations.
              </p>
            </div>
            <Button onClick={handleRerun} size="sm">
              Open Wizard
              <ChevronRight className="size-4 ml-1" />
            </Button>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/30 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Diagnose Connections</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Test all configured provider keys and messaging integrations.
              </p>
            </div>
            <Button
              disabled={testingProviders || testingIntegrations}
              onClick={() => void handleDiagnoseAll()}
              size="sm"
              variant="outline"
            >
              {(testingProviders || testingIntegrations)
                ? <Loader2 className="size-3 animate-spin mr-1" />
                : null}
              Run Diagnostics
            </Button>
          </div>

          {results && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Check className={cn('size-4', results.providers > 0 ? 'text-emerald-500' : 'text-muted-foreground')} />
                <span>{results.providers} active provider{results.providers !== 1 ? 's' : ''}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Check className={cn('size-4', results.integrations > 0 ? 'text-emerald-500' : 'text-muted-foreground')} />
                <span>{results.integrations} active integration{results.integrations !== 1 ? 's' : ''}</span>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card/30 p-5">
          <p className="text-sm font-medium mb-2">Quick Actions</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <QuickAction
              description="Add or switch AI providers"
              label="Manage Providers"
              onClick={startManualOnboarding}
            />
            <QuickAction
              description="View and edit all API keys"
              href="#"
              label="Manage API Keys"
            />
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card/30 p-5">
          <p className="text-sm font-medium mb-3">Supported Providers</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { name: 'OpenAI', url: 'https://platform.openai.com/api-keys' },
              { name: 'Anthropic', url: 'https://console.anthropic.com/settings/keys' },
              { name: 'Google Gemini', url: 'https://aistudio.google.com/app/apikey' },
              { name: 'OpenRouter', url: 'https://openrouter.ai/keys' },
              { name: 'Groq', url: 'https://console.groq.com/keys' },
              { name: 'Mistral', url: 'https://console.mistral.ai/api-keys' },
              { name: 'DeepSeek', url: 'https://platform.deepseek.com/api_keys' },
              { name: 'Together AI', url: 'https://api.together.ai/settings/api-keys' },
              { name: 'Azure OpenAI', url: 'https://portal.azure.com/' },
              { name: 'xAI', url: 'https://console.x.ai/' },
              { name: 'Novita', url: 'https://novita.ai/settings/api-keys' },
            ].map(p => (
              <a
                className="inline-flex items-center gap-1.5 rounded-lg border border-border/50 bg-card/20 px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all"
                href={p.url}
                key={p.name}
                rel="noopener noreferrer"
                target="_blank"
              >
                {p.name}
                <ExternalLink className="size-3" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function QuickAction({ label, description, onClick, href }: {
  label: string
  description: string
  onClick?: () => void
  href?: string
}) {
  const content = (
    <div className="rounded-lg border border-border/50 bg-card/20 p-3 hover:bg-card/40 hover:border-primary/30 transition-all cursor-pointer">
      <p className="text-sm font-medium">{label}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
    </div>
  )

  if (href) {
    return <a href={href}>{content}</a>
  }

  return <button onClick={onClick} type="button">{content}</button>
}
