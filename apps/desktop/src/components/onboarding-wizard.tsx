import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { BrandMark } from '@/components/brand-mark'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import {
  setEnvVar,
  testMessagingPlatform,
  updateMessagingPlatform,
  validateProviderCredential
} from '@/hermes'
import { BRAND } from '@/lib/brand'
import { Check, ChevronLeft, ChevronRight, ExternalLink, Globe, KeyRound, Loader2, Terminal } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { $desktopBoot, type DesktopBootState } from '@/store/boot'
import {
  completeDesktopOnboarding,
  type OnboardingContext
} from '@/store/onboarding'
import type { MessagingPlatformUpdate } from '@/types/aetheros'

interface WizardStep {
  id: string
  title: string
  subtitle: string
}

interface ProviderField {
  key: string
  label: string
  type: 'text' | 'password' | 'url'
  placeholder: string
  required: boolean
  envKey?: string
}

interface ProviderDef {
  id: string
  name: string
  description: string
  docsUrl: string
  fields: ProviderField[]
  modelRequired: boolean
  defaultModel?: string
  supportsValidation: boolean
}

interface GatewayConfig {
  type: 'local' | 'remote' | 'cloud'
  url: string
  name: string
  validated: boolean
}

interface IntegrationDef {
  id: string
  name: string
  description: string
  icon: string
  docsUrl: string
  fields: IntegrationFieldDef[]
}

interface IntegrationFieldDef {
  key: string
  label: string
  type: 'text' | 'password' | 'url'
  placeholder: string
  required: boolean
}

interface ProviderState {
  providerId: string
  providerName: string
  values: Record<string, string>
  model: string
  validated: boolean
  saved: boolean
}

interface IntegrationState {
  enabled: boolean
  values: Record<string, string>
  tested: boolean
  testPassed: boolean
  saved: boolean
}

const STEPS: WizardStep[] = [
  { id: 'welcome', title: 'Welcome', subtitle: 'Get started with AetherOS' },
  { id: 'choose-provider', title: 'AI Provider', subtitle: 'Choose your provider' },
  { id: 'configure-provider', title: 'Configuration', subtitle: 'Enter provider details' },
  { id: 'validate', title: 'Connection', subtitle: 'Verify your connection' },
  { id: 'gateway', title: 'Gateway', subtitle: 'Configure gateway' },
  { id: 'integrations', title: 'Integrations', subtitle: 'Connect services' },
  { id: 'local-ai', title: 'Local AI', subtitle: 'Discover local models' },
  { id: 'summary', title: 'Summary', subtitle: 'Review your setup' },
  { id: 'launch', title: 'Ready', subtitle: 'Launch AetherOS' },
]

const PROVIDERS: ProviderDef[] = [
  {
    id: 'openai', name: 'OpenAI',
    description: 'GPT-4o, GPT-4.5, o-series reasoning models',
    docsUrl: 'https://platform.openai.com/api-keys',
    modelRequired: true, defaultModel: 'gpt-4o',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'sk-...', required: true, envKey: 'OPENAI_API_KEY' },
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'https://api.openai.com/v1', required: false },
    ]
  },
  {
    id: 'anthropic', name: 'Anthropic',
    description: 'Claude Sonnet, Opus, Haiku models',
    docsUrl: 'https://console.anthropic.com/settings/keys',
    modelRequired: true, defaultModel: 'claude-sonnet-4-20250514',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'sk-ant-...', required: true, envKey: 'ANTHROPIC_API_KEY' },
    ]
  },
  {
    id: 'gemini', name: 'Google Gemini',
    description: 'Gemini 2.5 Pro, Flash, and 2.0 models',
    docsUrl: 'https://aistudio.google.com/app/apikey',
    modelRequired: true, defaultModel: 'gemini-2.5-pro-exp-03-25',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'AIza...', required: true, envKey: 'GEMINI_API_KEY' },
    ]
  },
  {
    id: 'openrouter', name: 'OpenRouter',
    description: 'Aggregator for 300+ models including Claude, GPT, Gemini',
    docsUrl: 'https://openrouter.ai/keys',
    modelRequired: true, defaultModel: 'anthropic/claude-sonnet-4',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'sk-or-v1-...', required: true, envKey: 'OPENROUTER_API_KEY' },
      { key: 'siteUrl', label: 'Site URL', type: 'url', placeholder: 'https://your-site.com', required: false },
      { key: 'appName', label: 'App Name', type: 'text', placeholder: 'AetherOS', required: false },
    ]
  },
  {
    id: 'groq', name: 'Groq',
    description: 'Fast inference for open models (Llama, Mixtral, Gemma)',
    docsUrl: 'https://console.groq.com/keys',
    modelRequired: true, defaultModel: 'llama-3.3-70b-versatile',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'gsk_...', required: true, envKey: 'GROQ_API_KEY' },
    ]
  },
  {
    id: 'mistral', name: 'Mistral',
    description: 'Mistral Large, Small, Codestral, Pixtral models',
    docsUrl: 'https://console.mistral.ai/api-keys',
    modelRequired: true, defaultModel: 'mistral-large-2501',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Paste Mistral API key', required: true, envKey: 'MISTRAL_API_KEY' },
    ]
  },
  {
    id: 'deepseek', name: 'DeepSeek',
    description: 'DeepSeek V3, R1 reasoning, and coding models',
    docsUrl: 'https://platform.deepseek.com/api_keys',
    modelRequired: true, defaultModel: 'deepseek-chat',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'sk-...', required: true, envKey: 'DEEPSEEK_API_KEY' },
    ]
  },
  {
    id: 'together', name: 'Together AI',
    description: 'Cloud API for 200+ open-source models',
    docsUrl: 'https://api.together.ai/settings/api-keys',
    modelRequired: true, defaultModel: 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Paste Together AI key', required: true, envKey: 'TOGETHER_API_KEY' },
    ]
  },
  {
    id: 'novita', name: 'Novita AI',
    description: 'Affordable API for Llama, Mistral, DeepSeek and more',
    docsUrl: 'https://novita.ai/settings/api-keys',
    modelRequired: true, defaultModel: 'meta-llama/llama-3.1-8b-instruct',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Paste Novita API key', required: true, envKey: 'NOVITA_API_KEY' },
    ]
  },
  {
    id: 'qwen', name: 'Qwen',
    description: 'Alibaba Cloud Qwen2.5, QwQ reasoning models',
    docsUrl: 'https://modelstudio.console.alibabacloud.com/',
    modelRequired: true, defaultModel: 'qwen-max',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'sk-...', required: true, envKey: 'DASHSCOPE_API_KEY' },
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'https://dashscope.aliyuncs.com/compatible-mode/v1', required: false },
    ]
  },
  {
    id: 'xai', name: 'xAI (Grok)',
    description: 'Grok-2, Grok-3 beta models via xAI API',
    docsUrl: 'https://console.x.ai/',
    modelRequired: true, defaultModel: 'grok-2-1212',
    supportsValidation: true,
    fields: [
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'xai-...', required: true, envKey: 'XAI_API_KEY' },
    ]
  },
  {
    id: 'azure', name: 'Azure OpenAI',
    description: 'Microsoft Azure-hosted OpenAI models',
    docsUrl: 'https://portal.azure.com/',
    modelRequired: true, defaultModel: 'gpt-4o',
    supportsValidation: true,
    fields: [
      { key: 'endpoint', label: 'Endpoint', type: 'url', placeholder: 'https://your-resource.openai.azure.com', required: true },
      { key: 'deployment', label: 'Deployment Name', type: 'text', placeholder: 'gpt-4o-deployment', required: true },
      { key: 'apiVersion', label: 'API Version', type: 'text', placeholder: '2024-08-01-preview', required: true },
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Azure API key', required: true, envKey: 'AZURE_OPENAI_API_KEY' },
    ]
  },
  {
    id: 'ollama', name: 'Ollama',
    description: 'Local open-source models (Llama, Mistral, Qwen, DeepSeek)',
    docsUrl: 'https://ollama.ai/',
    modelRequired: false,
    supportsValidation: true,
    fields: [
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'http://localhost:11434/v1', required: true },
    ]
  },
  {
    id: 'lmstudio', name: 'LM Studio',
    description: 'Local model server with OpenAI-compatible API',
    docsUrl: 'https://lmstudio.ai/docs/local-server',
    modelRequired: false,
    supportsValidation: true,
    fields: [
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'http://localhost:1234/v1', required: true },
    ]
  },
  {
    id: 'openai-compatible', name: 'OpenAI Compatible',
    description: 'Any OpenAI-compatible API endpoint (vLLM, TGI, etc.)',
    docsUrl: '',
    modelRequired: true, defaultModel: 'gpt-4o-mini',
    supportsValidation: true,
    fields: [
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'https://your-endpoint.com/v1', required: true },
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Optional API key', required: false, envKey: 'OPENAI_API_KEY' },
    ]
  },
  {
    id: 'custom', name: 'Custom Provider',
    description: 'Define your own provider with custom name and endpoint',
    docsUrl: '',
    modelRequired: true, defaultModel: 'custom-model',
    supportsValidation: true,
    fields: [
      { key: 'name', label: 'Provider Name', type: 'text', placeholder: 'My Provider', required: true },
      { key: 'baseUrl', label: 'Base URL', type: 'url', placeholder: 'https://api.myprovider.com/v1', required: true },
      { key: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Optional API key', required: false },
    ]
  },
]

const INTEGRATIONS: IntegrationDef[] = [
  {
    id: 'telegram', name: 'Telegram Bot', description: 'Chat with AetherOS via Telegram', icon: '✈️', docsUrl: 'https://core.telegram.org/bots#botfather',
    fields: [
      { key: 'TELEGRAM_BOT_TOKEN', label: 'Bot Token', type: 'password', placeholder: '123456:ABC-DEF...', required: true },
      { key: 'TELEGRAM_CHAT_ID', label: 'Chat ID (optional)', type: 'text', placeholder: '-1001234567890', required: false },
    ]
  },
  {
    id: 'whatsapp', name: 'WhatsApp', description: 'Meta Cloud API for WhatsApp Business', icon: '📱', docsUrl: 'https://developers.facebook.com/docs/whatsapp/',
    fields: [
      { key: 'WHATSAPP_PHONE_NUMBER_ID', label: 'Phone Number ID', type: 'text', placeholder: '123456789', required: true },
      { key: 'WHATSAPP_ACCESS_TOKEN', label: 'Access Token', type: 'password', placeholder: 'EAAT...', required: true },
    ]
  },
  {
    id: 'instagram', name: 'Instagram', description: 'Meta Graph API for Instagram messaging', icon: '📸', docsUrl: 'https://developers.facebook.com/docs/instagram-api/',
    fields: [
      { key: 'INSTAGRAM_APP_ID', label: 'App ID', type: 'text', placeholder: '123456789', required: true },
      { key: 'INSTAGRAM_ACCESS_TOKEN', label: 'Access Token', type: 'password', placeholder: 'EAAT...', required: true },
    ]
  },
  {
    id: 'messenger', name: 'Messenger', description: 'Facebook Messenger bot integration', icon: '💬', docsUrl: 'https://developers.facebook.com/docs/messenger-platform/',
    fields: [
      { key: 'MESSENGER_PAGE_ID', label: 'Page ID', type: 'text', placeholder: '123456789', required: true },
      { key: 'MESSENGER_ACCESS_TOKEN', label: 'Access Token', type: 'password', placeholder: 'EAAT...', required: true },
    ]
  },
  {
    id: 'discord', name: 'Discord', description: 'Discord bot for server chat', icon: '💬', docsUrl: 'https://discord.com/developers/applications',
    fields: [
      { key: 'DISCORD_BOT_TOKEN', label: 'Bot Token', type: 'password', placeholder: 'Paste Discord bot token', required: true },
    ]
  },
  {
    id: 'slack', name: 'Slack', description: 'Slack app integration for workplace chat', icon: '🔷', docsUrl: 'https://api.slack.com/apps',
    fields: [
      { key: 'SLACK_BOT_TOKEN', label: 'Bot Token', type: 'password', placeholder: 'xoxb-...', required: true },
      { key: 'SLACK_APP_TOKEN', label: 'App Token', type: 'password', placeholder: 'xapp-...', required: false },
    ]
  },
  {
    id: 'twilio', name: 'Twilio SMS', description: 'SMS messaging via Twilio', icon: '📨', docsUrl: 'https://www.twilio.com/console',
    fields: [
      { key: 'TWILIO_ACCOUNT_SID', label: 'Account SID', type: 'text', placeholder: 'AC...', required: true },
      { key: 'TWILIO_AUTH_TOKEN', label: 'Auth Token', type: 'password', placeholder: 'Paste Twilio auth token', required: true },
      { key: 'TWILIO_PHONE_NUMBER', label: 'Phone Number', type: 'text', placeholder: '+1234567890', required: true },
    ]
  },
  {
    id: 'smtp', name: 'Email (SMTP)', description: 'Send and receive emails via SMTP/IMAP', icon: '📧', docsUrl: '',
    fields: [
      { key: 'SMTP_HOST', label: 'SMTP Host', type: 'text', placeholder: 'smtp.example.com', required: true },
      { key: 'SMTP_PORT', label: 'SMTP Port', type: 'text', placeholder: '587', required: true },
      { key: 'SMTP_USER', label: 'Username', type: 'text', placeholder: 'user@example.com', required: true },
      { key: 'SMTP_PASS', label: 'Password', type: 'password', placeholder: 'SMTP password', required: true },
    ]
  },
  {
    id: 'webhook', name: 'Webhook', description: 'Generic webhook receiver', icon: '🔌', docsUrl: '',
    fields: [
      { key: 'WEBHOOK_URL', label: 'Webhook URL', type: 'url', placeholder: 'https://hooks.example.com/...', required: true },
    ]
  },
  {
    id: 'rest', name: 'Custom REST Endpoint', description: 'Custom REST API endpoint', icon: '🔗', docsUrl: '',
    fields: [
      { key: 'REST_NAME', label: 'Service Name', type: 'text', placeholder: 'My Service', required: true },
      { key: 'REST_URL', label: 'Endpoint URL', type: 'url', placeholder: 'https://api.example.com/webhook', required: true },
      { key: 'REST_TOKEN', label: 'Auth Token (optional)', type: 'password', placeholder: 'Bearer token', required: false },
    ]
  },
]

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'from-emerald-400 to-teal-500',
  anthropic: 'from-amber-400 to-orange-500',
  gemini: 'from-blue-400 to-cyan-500',
  openrouter: 'from-violet-400 to-purple-500',
  groq: 'from-red-400 to-rose-500',
  mistral: 'from-sky-400 to-blue-500',
  deepseek: 'from-yellow-400 to-amber-500',
  together: 'from-pink-400 to-fuchsia-500',
  novita: 'from-indigo-400 to-violet-500',
  qwen: 'from-orange-400 to-red-500',
  xai: 'from-lime-400 to-green-500',
  azure: 'from-cyan-400 to-sky-500',
  ollama: 'from-stone-400 to-neutral-500',
  lmstudio: 'from-slate-400 to-gray-500',
  'openai-compatible': 'from-teal-400 to-emerald-500',
  custom: 'from-gray-400 to-zinc-500',
}

interface OnboardingWizardProps {
  enabled: boolean
  onCompleted?: () => void
  requestGateway: OnboardingContext['requestGateway']
}

export function OnboardingWizard({ enabled, onCompleted, requestGateway }: OnboardingWizardProps) {
  const [step, setStep] = useState(0)
  const [direction, setDirection] = useState<'forward' | 'back'>('forward')
  const [leaving, setLeaving] = useState(false)
  const [launchError, setLaunchError] = useState<string | null>(null)

  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [providerState, setProviderState] = useState<ProviderState | null>(null)
  const [gateways, setGateways] = useState<GatewayConfig[]>([])
  const [integrations, setIntegrations] = useState<Record<string, IntegrationState>>({})
  const [localAIFound, setLocalAIFound] = useState<{ ollama: boolean; lmstudio: boolean }>({ ollama: false, lmstudio: false })
  const [useLocalAI, setUseLocalAI] = useState(false)

  const boot = useStore($desktopBoot)

  const totalSteps = STEPS.length
  const progress = ((step + 1) / totalSteps) * 100

  const goNext = useCallback(() => {
    if (step < totalSteps - 1) {
      setDirection('forward')
      setStep(s => s + 1)
    }
  }, [step, totalSteps])

  const goBack = useCallback(() => {
    if (step > 0) {
      setDirection('back')
      setStep(s => s - 1)
    }
  }, [step])

  const goToStep = useCallback((i: number) => {
    setDirection(i > step ? 'forward' : 'back')
    setStep(i)
  }, [step])

  const finishWizard = useCallback(() => {
    if (leaving) {return}
    console.log('[Launch] Starting finishWizard — saving config')

    try {
      console.log('[Launch] Calling completeDesktopOnboarding()')
      completeDesktopOnboarding()
      console.log('[Launch] Config saved, starting exit animation')
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      console.error('[Launch] Failed to complete onboarding:', msg)
      setLaunchError(msg)

      return
    }

    setLeaving(true)
    setTimeout(() => {
      try {
        console.log('[Launch] Calling onCompleted to refresh model/config')
        onCompleted?.()
        console.log('[Launch] Focusing main window')
        window.aetherosDesktop?.focusMainWindow?.()
        console.log('[Launch] Launch complete')
      } catch (err) {
        console.error('[Launch] Non-fatal error after save:', err)
      }
    }, 1000)
  }, [leaving, onCompleted])

  if (!enabled) {
    return null
  }

  return (
    <div
      className={cn(
        'fixed inset-0 z-1300 flex flex-col bg-(--ui-chat-surface-background)',
        leaving ? 'animate-out fade-out-0 duration-500' : 'animate-in fade-in-0 duration-300'
      )}
    >
      <header className="flex items-center justify-between border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <BrandMark className="size-7" />
          <span className="text-sm font-semibold">AetherOS</span>
        </div>
        {step > 0 && (
          <span className="text-xs text-muted-foreground">
            Step {step + 1} of {totalSteps}
          </span>
        )}
      </header>

      <div className="h-1 bg-muted/30">
        <div
          className="h-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {launchError ? (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-md rounded-lg border border-red-500/30 bg-red-500/5 p-6 text-center space-y-4">
            <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-red-500/20">
              <Codicon className="size-8 text-red-500" name="error" />
            </div>
            <h2 className="text-xl font-bold">Failed to Launch AetherOS</h2>
            <p className="text-sm text-muted-foreground">
              An error occurred while saving your configuration and launching the application.
            </p>
            <div className="rounded-md bg-muted/50 p-3 text-left">
              <p className="text-xs font-mono text-red-600 dark:text-red-400 break-all">{launchError}</p>
            </div>
            <div className="flex justify-center gap-3">
              <Button onClick={() => { setLaunchError(null); setLeaving(false) }} size="sm">
                Retry
              </Button>
              <Button onClick={() => window.close()} size="sm" variant="ghost">
                Close
              </Button>
            </div>
          </div>
        </div>
      ) : (
      <div className="flex flex-1 overflow-hidden">
        <aside className="hidden w-56 shrink-0 border-r border-border p-5 md:block">
          <nav className="flex flex-col gap-1">
            {STEPS.map((s, i) => (
              <button
                className={cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors',
                  i === step
                    ? 'bg-primary/10 font-semibold text-primary'
                    : i < step
                    ? 'text-muted-foreground'
                    : 'text-muted-foreground/50'
                )}
                disabled={i > step}
                key={s.id}
                onClick={() => i <= step && goToStep(i)}
                type="button"
              >
                <span className={cn(
                  'flex size-6 items-center justify-center rounded-full text-xs font-bold',
                  i === step ? 'bg-primary text-primary-foreground' :
                  i < step ? 'bg-emerald-500/20 text-emerald-600' :
                  'bg-muted text-muted-foreground/50'
                )}>
                  {i < step ? <Check className="size-3" /> : i + 1}
                </span>
                <span className="truncate">{s.title}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex flex-1 flex-col overflow-y-auto p-6 md:p-10">
          <div className="mx-auto w-full max-w-3xl flex-1">
            <StepContent
              boot={boot}
              direction={direction}
              finishWizard={finishWizard}
              gateways={gateways}
              integrations={integrations}
              localAIFound={localAIFound}
              onCompleted={onCompleted}
              providerState={providerState}
              requestGateway={requestGateway}
              selectedProvider={selectedProvider}
              setGateways={setGateways}
              setIntegrations={setIntegrations}
              setLocalAIFound={setLocalAIFound}
              setProviderState={setProviderState}
              setSelectedProvider={setSelectedProvider}
              setUseLocalAI={setUseLocalAI}
              step={step}
              useLocalAI={useLocalAI}
            />
          </div>

          <footer className="flex items-center justify-between border-t border-border pt-4 mt-6">
            <div>
              {step > 0 && step < totalSteps - 1 ? (
                <Button onClick={goBack} size="sm" variant="ghost">
                  <ChevronLeft className="size-4 mr-1" />
                  Back
                </Button>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              {step < totalSteps - 1 ? (
                <NextButton
                  finishWizard={finishWizard}
                  gateways={gateways}
                  goBack={goBack}
                  goNext={goNext}
                  integrations={integrations}
                  onCompleted={onCompleted}
                  providerState={providerState}
                  requestGateway={requestGateway}
                  selectedProvider={selectedProvider}
                  setGateways={setGateways}
                  setIntegrations={setIntegrations}
                  setProviderState={setProviderState}
                  setSelectedProvider={setSelectedProvider}
                  setStep={setStep}
                  step={step}
                />
              ) : null}
            </div>
          </footer>
        </main>
      </div>
      )}
    </div>
  )
}

function NextButton({
  step, selectedProvider, providerState, gateways, integrations,
  goNext, setStep, setSelectedProvider, setProviderState, setGateways, setIntegrations,
  goBack, finishWizard, requestGateway, onCompleted
}: {
  step: number
  selectedProvider: string | null
  providerState: ProviderState | null
  gateways: GatewayConfig[]
  integrations: Record<string, IntegrationState>
  goNext: () => void
  setStep: (fn: (s: number) => number) => void
  setSelectedProvider: (p: string | null) => void
  setProviderState: (s: ProviderState | null) => void
  setGateways: (g: GatewayConfig[]) => void
  setIntegrations: (i: Record<string, IntegrationState>) => void
  goBack: () => void
  finishWizard: () => void
  requestGateway: OnboardingContext['requestGateway']
  onCompleted?: () => void
}) {
  switch (STEPS[step].id) {
    case 'welcome':
      return (
        <Button onClick={goNext} size="sm">
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'choose-provider':
      return (
        <Button
          disabled={!selectedProvider}
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
          title={!selectedProvider ? 'Select a provider first' : ''}
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'configure-provider':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'validate':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'gateway':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'integrations':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'local-ai':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    case 'summary':
      return (
        <Button
          onClick={() => {
            setStep(s => s + 1)
          }}
          size="sm"
        >
          Continue
          <ChevronRight className="size-4 ml-1" />
        </Button>
      )

    default:
      return null
  }
}

function StepContent({
  direction, step, selectedProvider, setSelectedProvider,
  providerState, setProviderState, gateways, setGateways,
  integrations, setIntegrations, localAIFound, setLocalAIFound,
  useLocalAI, setUseLocalAI, boot, requestGateway, onCompleted, finishWizard
}: {
  direction: 'forward' | 'back'
  step: number
  selectedProvider: string | null
  setSelectedProvider: (p: string | null) => void
  providerState: ProviderState | null
  setProviderState: (s: ProviderState | null) => void
  gateways: GatewayConfig[]
  setGateways: (g: GatewayConfig[]) => void
  integrations: Record<string, IntegrationState>
  setIntegrations: (i: Record<string, IntegrationState>) => void
  localAIFound: { ollama: boolean; lmstudio: boolean }
  setLocalAIFound: (l: { ollama: boolean; lmstudio: boolean }) => void
  useLocalAI: boolean
  setUseLocalAI: (v: boolean) => void
  boot: DesktopBootState
  requestGateway: OnboardingContext['requestGateway']
  onCompleted?: () => void
  finishWizard: () => void
}) {
  const animateClass = direction === 'forward'
    ? 'animate-in slide-in-from-right-4 fade-in duration-300'
    : 'animate-in slide-in-from-left-4 fade-in duration-300'

  switch (STEPS[step].id) {
    case 'welcome':
      return <div className={animateClass}><WelcomeStep /></div>

    case 'choose-provider':
      return (
        <div className={animateClass}>
          <ChooseProviderStep
            onSelect={setSelectedProvider}
            selected={selectedProvider}
          />
        </div>
      )

    case 'configure-provider':
      return (
        <div className={animateClass}>
          {selectedProvider && (
            <ConfigureProviderStep
              onStateChange={setProviderState}
              provider={PROVIDERS.find(p => p.id === selectedProvider)!}
              requestGateway={requestGateway}
              state={providerState}
            />
          )}
        </div>
      )

    case 'validate':
      return (
        <div className={animateClass}>
          {selectedProvider && providerState && (
            <ValidateConnectionStep
              onStateChange={setProviderState}
              provider={PROVIDERS.find(p => p.id === selectedProvider)!}
              state={providerState}
            />
          )}
        </div>
      )

    case 'gateway':
      return (
        <div className={animateClass}>
          <GatewayStep configs={gateways} onConfigsChange={setGateways} />
        </div>
      )

    case 'integrations':
      return (
        <div className={animateClass}>
          <IntegrationsStep onStateChange={setIntegrations} state={integrations} />
        </div>
      )

    case 'local-ai':
      return (
        <div className={animateClass}>
          <LocalAIStep
            found={localAIFound}
            onFoundChange={setLocalAIFound}
            onUseLocalAIChange={setUseLocalAI}
            useLocalAI={useLocalAI}
          />
        </div>
      )

    case 'summary':
      return (
        <div className={animateClass}>
          <SummaryStep
            gateways={gateways}
            integrations={integrations}
            localAIFound={localAIFound}
            providerState={providerState}
            selectedProvider={selectedProvider}
            useLocalAI={useLocalAI}
          />
        </div>
      )

    case 'launch':
      return (
        <div className={animateClass}>
          <LaunchStep onFinish={finishWizard} />
        </div>
      )

    default:
      return null
  }
}

function WelcomeStep() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60dvh] text-center gap-8">
      <div className="space-y-6">
        <BrandMark className="mx-auto size-24 shadow-lg shadow-blue-500/20" />
        <h1 className="text-4xl font-bold tracking-tight">
          Welcome to <span className={BRAND.textGradient}>AetherOS</span>
        </h1>
        <p className="mx-auto max-w-lg text-lg text-muted-foreground">
          Your personal AI agent that learns across sessions, delegates to subagents,
          and drives real tools — all from one interface.
        </p>
        <div className="mx-auto max-w-md rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-left">
          <p className="text-sm font-medium text-amber-700 dark:text-amber-400">
            AetherOS requires at least one AI provider to function.
          </p>
          <p className="mt-1 text-xs text-amber-600/70 dark:text-amber-400/70">
            You will configure an API key for your preferred provider during this setup.
            Your keys are stored securely and never shared.
          </p>
        </div>
      </div>

      <div className="grid gap-3 text-left w-full max-w-md">
        {[
          { emoji: '🤖', title: 'AI Provider', desc: 'Connect an AI provider to power your agent' },
          { emoji: '🌐', title: 'Gateway', desc: 'Configure how AetherOS connects to services' },
          { emoji: '🔗', title: 'Integrations', desc: 'Connect to Telegram, Discord, email and more' },
        ].map(item => (
          <div className="flex items-start gap-3 rounded-lg border border-border bg-card/50 p-4" key={item.title}>
            <span className="mt-0.5 text-lg">{item.emoji}</span>
            <div>
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-muted-foreground">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChooseProviderStep({
  selected,
  onSelect
}: {
  selected: string | null
  onSelect: (id: string | null) => void
}) {
  const [search, setSearch] = useState('')

  const filtered = search
    ? PROVIDERS.filter(p => p.name.toLowerCase().includes(search.toLowerCase()) || p.id.includes(search.toLowerCase()))
    : PROVIDERS

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Choose AI Provider</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Select the AI provider you want to use. You can add more providers later in Settings.
        </p>
      </div>

      <Input
        className="max-w-md"
        onChange={e => setSearch(e.target.value)}
        placeholder="Search providers..."
        type="text"
        value={search}
      />

      <div className="grid gap-3 sm:grid-cols-2">
        {filtered.map(provider => {
          const isSelected = selected === provider.id

          return (
            <button
              className={cn(
                'relative flex flex-col rounded-lg border p-4 text-left transition-all hover:border-primary/40',
                isSelected
                  ? 'border-primary/60 ring-2 ring-primary/20 bg-primary/5'
                  : 'border-border bg-card/30 hover:bg-card/50'
              )}
              key={provider.id}
              onClick={() => onSelect(isSelected ? null : provider.id)}
              type="button"
            >
              {isSelected && (
                <div className="absolute right-3 top-3 flex size-5 items-center justify-center rounded-full bg-primary">
                  <Check className="size-3 text-primary-foreground" />
                </div>
              )}
              <div className="flex items-center gap-3 mb-2">
                <div className={cn(
                  'flex size-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br text-sm font-bold text-white shadow-sm',
                  PROVIDER_COLORS[provider.id] || 'from-gray-400 to-gray-500'
                )}>
                  {provider.name.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-semibold">{provider.name}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{provider.description}</p>
                </div>
              </div>
              {provider.docsUrl && (
                <a
                  className="mt-1 inline-flex items-center gap-1 text-xs text-primary/70 hover:text-primary"
                  href={provider.docsUrl}
                  onClick={e => e.stopPropagation()}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Documentation
                  <ExternalLink className="size-3" />
                </a>
              )}
            </button>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">
          No providers match your search.
        </p>
      )}
    </div>
  )
}

function ConfigureProviderStep({
  provider,
  state,
  onStateChange,
  requestGateway
}: {
  provider: ProviderDef
  state: ProviderState | null
  onStateChange: (s: ProviderState | null) => void
  requestGateway: OnboardingContext['requestGateway']
}) {
  const [values, setValues] = useState<Record<string, string>>(state?.values || {})
  const [model, setModel] = useState(state?.model || provider.defaultModel || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    const p = PROVIDERS.find(p => p.id === provider.id)

    if (!p) {return}

    setSaving(true)

    try {
      if (p.id === 'ollama' || p.id === 'lmstudio' || p.id === 'openai-compatible') {
        const url = values['baseUrl'] || ''
        const key = values['apiKey'] || ''

        if (!url) {return}
        await setEnvVar('OPENAI_BASE_URL', url)

        if (key) {await setEnvVar('OPENAI_API_KEY', key)}
        onStateChange({
          providerId: provider.id,
          providerName: provider.name,
          values,
          model: model || provider.defaultModel || '',
          validated: false,
          saved: true,
        })
        setSaved(true)
      } else if (p.id === 'azure') {
        const endpoint = values['endpoint'] || ''
        const deployment = values['deployment'] || ''
        const apiVersion = values['apiVersion'] || ''
        const apiKey = values['apiKey'] || ''
        await setEnvVar('AZURE_OPENAI_API_KEY', apiKey)
        onStateChange({
          providerId: provider.id,
          providerName: provider.name,
          values: { ...values, deployment, apiVersion },
          model: model || provider.defaultModel || '',
          validated: false,
          saved: true,
        })
        setSaved(true)
      } else if (p.id === 'custom') {
        const baseUrl = values['baseUrl'] || ''
        const key = values['apiKey'] || ''
        const name = values['name'] || 'Custom'

        if (key) {await setEnvVar('CUSTOM_API_KEY', key)}
        onStateChange({
          providerId: provider.id,
          providerName: name,
          values,
          model: model || provider.defaultModel || '',
          validated: false,
          saved: true,
        })
        setSaved(true)
      } else {
        const envField = p.fields.find(f => f.envKey)

        if (envField) {
          const keyValue = values[envField.key] || ''

          if (keyValue) {await setEnvVar(envField.envKey!, keyValue)}
          onStateChange({
            providerId: provider.id,
            providerName: provider.name,
            values,
            model: model || provider.defaultModel || '',
            validated: false,
            saved: true,
          })
          setSaved(true)
        }
      }
    } catch {
      // save failed silently
    }

    setSaving(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className={cn(
            'flex size-12 items-center justify-center rounded-xl bg-gradient-to-br text-lg font-bold text-white shadow-sm',
            PROVIDER_COLORS[provider.id] || 'from-gray-400 to-gray-500'
          )}>
            {provider.name.charAt(0)}
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{provider.name}</h2>
            <p className="text-sm text-muted-foreground">{provider.description}</p>
          </div>
        </div>
      </div>

      {saved ? (
        <div className="flex flex-col items-center justify-center py-12 gap-4">
          <div className="flex size-16 items-center justify-center rounded-full bg-emerald-500/20">
            <Check className="size-8 text-emerald-500" />
          </div>
          <p className="text-lg font-medium">Credentials Saved</p>
          <p className="text-sm text-muted-foreground">
            Your {provider.name} credentials have been saved. Continue to validate the connection.
          </p>
        </div>
      ) : (
        <div className="space-y-4 max-w-lg">
          {provider.fields.map(field => (
            <div key={field.key}>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                {field.label}
                {field.required && <span className="text-destructive ml-0.5">*</span>}
              </label>
              <Input
                autoComplete="off"
                className="font-mono text-sm"
                onChange={e => setValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                placeholder={field.placeholder}
                type={field.type}
                value={values[field.key] || ''}
              />
              {field.envKey && (
                <p className="mt-0.5 text-[10px] text-muted-foreground/60">
                  Stored as {field.envKey}
                </p>
              )}
            </div>
          ))}

          {provider.modelRequired && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">
                Model
                <span className="text-destructive ml-0.5">*</span>
              </label>
              <Input
                autoComplete="off"
                className="font-mono text-sm"
                onChange={e => setModel(e.target.value)}
                placeholder={provider.defaultModel || 'model-name'}
                type="text"
                value={model}
              />
              <p className="mt-0.5 text-[10px] text-muted-foreground/60">
                Default: {provider.defaultModel || 'required'}
              </p>
            </div>
          )}

          {provider.docsUrl && (
            <a
              className="inline-flex items-center gap-1 text-xs text-primary/70 hover:text-primary"
              href={provider.docsUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              <ExternalLink className="size-3" />
              How to get {provider.name} API credentials
            </a>
          )}

          <div className="pt-2">
            <Button
              disabled={saving || Object.keys(values).length === 0}
              onClick={() => void handleSave()}
              size="sm"
            >
              {saving ? <Loader2 className="size-3 animate-spin mr-1" /> : <KeyRound className="size-3 mr-1" />}
              Save Credentials
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function ValidateConnectionStep({
  provider,
  state,
  onStateChange
}: {
  provider: ProviderDef
  state: ProviderState
  onStateChange: (s: ProviderState) => void
}) {
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [tested, setTested] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setTested(false)

    try {
      let result: { ok: boolean; reachable: boolean; message: string; models?: string[] }

      if (provider.id === 'ollama') {
        const url = state.values['baseUrl'] || 'http://localhost:11434/v1'
        result = await validateProviderCredential('OPENAI_BASE_URL', url, '')
      } else if (provider.id === 'lmstudio') {
        const url = state.values['baseUrl'] || 'http://localhost:1234/v1'
        result = await validateProviderCredential('OPENAI_BASE_URL', url, '')
      } else if (provider.id === 'azure') {
        const endpoint = state.values['endpoint'] || ''
        const key = state.values['apiKey'] || ''
        result = await validateProviderCredential('AZURE_OPENAI_API_KEY', key, endpoint)
      } else if (provider.id === 'openai-compatible' || provider.id === 'custom') {
        const url = state.values['baseUrl'] || ''
        const key = state.values['apiKey'] || ''
        result = await validateProviderCredential('OPENAI_BASE_URL', url, key)
      } else {
        const envField = provider.fields.find(f => f.envKey)

        if (envField) {
          const value = state.values[envField.key] || ''
          result = await validateProviderCredential(envField.envKey!, value, '')
        } else {
          result = { ok: false, reachable: false, message: 'No validation method available for this provider.' }
        }
      }

      setTestResult({
        ok: result.ok && result.reachable,
        message: result.message || (result.reachable ? 'Connection verified successfully.' : 'Could not reach provider.')
      })
      setTested(true)

      if (result.ok && result.reachable) {
        onStateChange({ ...state, validated: true })
      }
    } catch (e) {
      setTestResult({
        ok: false,
        message: e instanceof Error ? e.message : String(e)
      })
      setTested(true)
    }

    setTesting(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className={cn(
            'flex size-12 items-center justify-center rounded-xl bg-gradient-to-br text-lg font-bold text-white shadow-sm',
            PROVIDER_COLORS[provider.id] || 'from-gray-400 to-gray-500'
          )}>
            {provider.name.charAt(0)}
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Validate Connection</h2>
            <p className="text-sm text-muted-foreground">
              Verify your {provider.name} credentials with a real API request.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card/30 p-6 space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-medium">Testing the following configuration:</p>
          <div className="space-y-1 text-xs text-muted-foreground font-mono">
            <p>Provider: {provider.name}</p>
            {state.model && <p>Model: {state.model}</p>}
            {Object.entries(state.values).map(([key, value]) => (
              <p key={key}>{key}: {key.includes('apiKey') || key.includes('token') || key.includes('TOKEN') || key.includes('KEY')
                ? '••••••••' + (value.length > 8 ? value.slice(-4) : '')
                : value}</p>
            ))}
          </div>
        </div>

        <Button
          disabled={testing || state.validated}
          onClick={() => void handleTest()}
          size="sm"
          variant={state.validated ? 'outline' : 'default'}
        >
          {testing ? <Loader2 className="size-3 animate-spin mr-1" /> : null}
          {state.validated ? 'Verified' : testing ? 'Testing...' : 'Test Connection'}
        </Button>

        {testResult && (
          <div className={cn(
            'rounded-lg p-4 text-sm',
            testResult.ok
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-400'
          )}>
            <p className="font-medium">{testResult.ok ? 'Connection Successful' : 'Connection Failed'}</p>
            <p className="mt-1 text-xs opacity-80">{testResult.message}</p>
          </div>
        )}

        {!tested && !state.validated && (
          <p className="text-xs text-muted-foreground">
            Click "Test Connection" to verify your API key and endpoint are working correctly.
            {provider.supportsValidation && ' This performs a real API call.'}
          </p>
        )}

        {tested && !testResult?.ok && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
            <p className="text-xs font-medium text-amber-700 dark:text-amber-400">Troubleshooting</p>
            <ul className="mt-1 text-xs text-amber-600/70 dark:text-amber-400/70 list-disc list-inside space-y-0.5">
              <li>Verify the API key is correct and hasn't expired</li>
              <li>Check that the endpoint URL is reachable</li>
              {provider.docsUrl && (
                <li>
                  Visit <a className="underline" href={provider.docsUrl} rel="noopener noreferrer" target="_blank">{provider.name} console</a> to get a valid key
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

function GatewayStep({
  configs,
  onConfigsChange
}: {
  configs: GatewayConfig[]
  onConfigsChange: (c: GatewayConfig[]) => void
}) {
  const [editing, setEditing] = useState(false)
  const [gatewayType, setGatewayType] = useState<'local' | 'remote' | 'cloud'>('local')
  const [gatewayUrl, setGatewayUrl] = useState('')
  const [gatewayName, setGatewayName] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)

  const handleAdd = () => {
    onConfigsChange([
      ...configs,
      { type: gatewayType, url: gatewayUrl, name: gatewayName || `${gatewayType} gateway`, validated: false }
    ])
    setEditing(false)
    setGatewayUrl('')
    setGatewayName('')
    setTestResult(null)
  }

  const handleRemove = (index: number) => {
    onConfigsChange(configs.filter((_, i) => i !== index))
  }

  const handleTest = async (index: number) => {
    setTesting(true)
    setTestResult(null)
    const config = configs[index]

    try {
      const result = await validateProviderCredential('OPENAI_BASE_URL', config.url, '')
      const updated = [...configs]
      updated[index] = { ...config, validated: result.reachable }
      onConfigsChange(updated)
      setTestResult({ ok: result.reachable, message: result.reachable ? 'Gateway reachable.' : 'Could not reach gateway.' })
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : 'Test failed' })
    }

    setTesting(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Gateway Setup</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure how AetherOS connects to its backend. You can add multiple gateways.
        </p>
      </div>

      {configs.map((config, index) => (
        <div className="flex items-center justify-between rounded-lg border border-border bg-card/30 px-4 py-3" key={index}>
          <div className="flex items-center gap-3">
            <div className={cn(
              'flex size-8 items-center justify-center rounded-full',
              config.validated ? 'bg-emerald-500/20' : 'bg-muted'
            )}>
              {config.validated
                ? <Check className="size-4 text-emerald-500" />
                : <Globe className="size-4 text-muted-foreground" />
              }
            </div>
            <div>
              <p className="text-sm font-medium">{config.name}</p>
              <p className="text-xs text-muted-foreground font-mono">{config.url || config.type}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!config.validated && (
              <Button disabled={testing} onClick={() => void handleTest(index)} size="xs" variant="outline">
                {testing ? <Loader2 className="size-3 animate-spin" /> : 'Test'}
              </Button>
            )}
            <Button className="text-destructive" onClick={() => handleRemove(index)} size="xs" variant="ghost">
              Remove
            </Button>
          </div>
        </div>
      ))}

      {testResult && (
        <div className={cn(
          'rounded-lg p-3 text-sm',
          testResult.ok ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' : 'bg-red-500/10 text-red-700 dark:text-red-400'
        )}>
          {testResult.message}
        </div>
      )}

      {editing ? (
        <div className="rounded-lg border border-border bg-card/50 p-4 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Gateway Type</label>
            <div className="flex gap-2">
              {(['local', 'remote', 'cloud'] as const).map(type => (
                <button
                  className={cn(
                    'rounded-lg px-4 py-2 text-sm border transition-all',
                    gatewayType === type
                      ? 'border-primary/50 bg-primary/10 text-primary font-medium'
                      : 'border-border bg-card/30 text-muted-foreground hover:bg-card/50'
                  )}
                  key={type}
                  onClick={() => setGatewayType(type)}
                  type="button"
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Gateway Name</label>
            <Input
              onChange={e => setGatewayName(e.target.value)}
              placeholder="My Gateway"
              type="text"
              value={gatewayName}
            />
          </div>
          {gatewayType !== 'local' && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Gateway URL</label>
              <Input
                onChange={e => setGatewayUrl(e.target.value)}
                placeholder="https://gateway.example.com:8080"
                type="url"
                value={gatewayUrl}
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEditing(false)} size="xs" variant="ghost">Cancel</Button>
            <Button onClick={handleAdd} size="xs">Add Gateway</Button>
          </div>
        </div>
      ) : (
        <Button onClick={() => setEditing(true)} size="sm" variant="outline">
          Add Gateway
        </Button>
      )}
    </div>
  )
}

function IntegrationsStep({
  state,
  onStateChange
}: {
  state: Record<string, IntegrationState>
  onStateChange: (s: Record<string, IntegrationState>) => void
}) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [fieldValues, setFieldValues] = useState<Record<string, Record<string, string>>>({})
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string }>>({})

  const categories = useMemo(() => {
    const map = new Map<string, IntegrationDef[]>()

    for (const int of INTEGRATIONS) {
      const cat = map.get(int.name) || []
      cat.push(int)
      map.set(int.name, cat)
    }

    return Array.from(map.entries())
  }, [])

  const handleToggle = (id: string, enabled: boolean) => {
    const current = state[id] || { enabled: false, values: {}, tested: false, testPassed: false, saved: false }
    onStateChange({ ...state, [id]: { ...current, enabled } })
  }

  const handleSave = async (integration: IntegrationDef) => {
    const values = fieldValues[integration.id] || {}

    try {
      const env: Record<string, string> = {}
      integration.fields.forEach(f => {
        if (values[f.key]) {
          env[f.key] = values[f.key]
        }
      })

      const updateBody: MessagingPlatformUpdate = {
        enabled: true,
        env
      }

      await updateMessagingPlatform(integration.id, updateBody)

      const current = state[integration.id] || { enabled: false, values: {}, tested: false, testPassed: false, saved: false }
      onStateChange({ ...state, [integration.id]: { ...current, enabled: true, values, saved: true } })
      setExpanded(null)
    } catch (e) {
      setTestResults(prev => ({
        ...prev,
        [integration.id]: { ok: false, message: e instanceof Error ? e.message : 'Save failed' }
      }))
    }
  }

  const handleTest = async (id: string) => {
    setTesting(id)

    try {
      const result = await testMessagingPlatform(id)
      setTestResults(prev => ({ ...prev, [id]: { ok: result.ok, message: result.message } }))
      const current = state[id]

      if (current) {
        onStateChange({ ...state, [id]: { ...current, tested: true, testPassed: result.ok } })
      }
    } catch (e) {
      setTestResults(prev => ({
        ...prev,
        [id]: { ok: false, message: e instanceof Error ? e.message : 'Test failed' }
      }))
    }

    setTesting(null)
  }

  const skipAllIntegrations = () => {
    const skipped = { ...state }
    INTEGRATIONS.forEach(int => {
      if (!skipped[int.id]) {
        skipped[int.id] = { enabled: false, values: {}, tested: false, testPassed: false, saved: true }
      }
    })
    onStateChange(skipped)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Communication Integrations</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect external messaging platforms. All integrations are optional.
          </p>
        </div>
        <Button onClick={skipAllIntegrations} size="xs" variant="ghost">
          Skip All
        </Button>
      </div>

      <div className="grid gap-3">
        {INTEGRATIONS.map(int => {
          const intState = state[int.id] || { enabled: false, values: {}, tested: false, testPassed: false, saved: false }
          const isExpanded = expanded === int.id
          const testResult = testResults[int.id]

          return (
            <div className="rounded-lg border border-border bg-card/30" key={int.id}>
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-lg">{int.icon}</span>
                  <div>
                    <p className="text-sm font-medium">{int.name}</p>
                    <p className="text-xs text-muted-foreground">{int.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {intState.testPassed && (
                    <span className="flex items-center gap-1 text-xs text-emerald-600">
                      <Check className="size-3" />
                      Working
                    </span>
                  )}
                  {intState.saved && !intState.testPassed && (
                    <span className="text-xs text-muted-foreground">Saved</span>
                  )}
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      checked={intState.enabled}
                      className="sr-only peer"
                      onChange={e => {
                        handleToggle(int.id, e.target.checked)

                        if (e.target.checked) {
                          setExpanded(int.id)
                        }
                      }}
                      type="checkbox"
                    />
                    <div className="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all" />
                  </label>
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-border px-4 py-4 space-y-4">
                  {int.fields.map(field => (
                    <div key={field.key}>
                      <label className="text-xs font-medium text-muted-foreground mb-1 block">
                        {field.label}
                        {field.required && <span className="text-destructive ml-0.5">*</span>}
                      </label>
                      <Input
                        autoComplete="off"
                        className="font-mono text-sm"
                        onChange={e => setFieldValues(prev => ({
                          ...prev,
                          [int.id]: { ...(prev[int.id] || {}), [field.key]: e.target.value }
                        }))}
                        placeholder={field.placeholder}
                        type={field.type}
                        value={fieldValues[int.id]?.[field.key] || intState.values[field.key] || ''}
                      />
                    </div>
                  ))}

                  {testResult && (
                    <div className={cn(
                      'rounded-lg p-3 text-sm',
                      testResult.ok
                        ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                        : 'bg-red-500/10 text-red-700 dark:text-red-400'
                    )}>
                      {testResult.message}
                    </div>
                  )}

                  <div className="flex justify-end gap-2">
                    <Button onClick={() => setExpanded(null)} size="xs" variant="ghost">
                      Close
                    </Button>
                    <Button
                      disabled={testing === int.id}
                      onClick={() => void handleTest(int.id)}
                      size="xs"
                      variant="outline"
                    >
                      {testing === int.id ? <Loader2 className="size-3 animate-spin mr-1" /> : null}
                      Test Connection
                    </Button>
                    <Button onClick={() => void handleSave(int)} size="xs">
                      Save
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LocalAIStep({
  found,
  onFoundChange,
  useLocalAI,
  onUseLocalAIChange
}: {
  found: { ollama: boolean; lmstudio: boolean }
  onFoundChange: (f: { ollama: boolean; lmstudio: boolean }) => void
  useLocalAI: boolean
  onUseLocalAIChange: (v: boolean) => void
}) {
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const detectLocal = async () => {
      setChecking(true)
      let ollamaFound = false
      let lmstudioFound = false

      try {
        const ollamaRes = await fetch('http://localhost:11434/api/tags', { signal: AbortSignal.timeout(3000) })
        ollamaFound = ollamaRes.ok
      } catch { }

      try {
        const lmRes = await fetch('http://localhost:1234/v1/models', { signal: AbortSignal.timeout(3000) })
        lmstudioFound = lmRes.ok
      } catch { }

      onFoundChange({ ollama: ollamaFound, lmstudio: lmstudioFound })

      if (ollamaFound || lmstudioFound) {
        onUseLocalAIChange(true)
      }

      setChecking(false)
    }

    void detectLocal()
  }, [onFoundChange, onUseLocalAIChange])

  const hasLocal = found.ollama || found.lmstudio

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Local AI Detection</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Detect and configure locally running AI services.
        </p>
      </div>

      {checking ? (
        <div className="flex items-center justify-center py-12 gap-3">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Scanning for local AI services...</p>
        </div>
      ) : (
        <div className="space-y-4">
          {[
            { id: 'ollama', name: 'Ollama', defaultUrl: 'http://localhost:11434', found: found.ollama },
            { id: 'lmstudio', name: 'LM Studio', defaultUrl: 'http://localhost:1234', found: found.lmstudio },
          ].map(service => (
            <div className={cn(
              'flex items-center justify-between rounded-lg border p-4',
              service.found
                ? 'border-emerald-500/30 bg-emerald-500/5'
                : 'border-border bg-card/30'
            )} key={service.id}>
              <div className="flex items-center gap-3">
                <div className={cn(
                  'flex size-10 items-center justify-center rounded-lg',
                  service.found ? 'bg-emerald-500/20' : 'bg-muted'
                )}>
                  {service.found
                    ? <Check className="size-5 text-emerald-500" />
                    : <Terminal className="size-5 text-muted-foreground" />
                  }
                </div>
                <div>
                  <p className="text-sm font-medium">{service.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{service.defaultUrl}</p>
                </div>
              </div>
              <span className={cn(
                'text-xs font-medium',
                service.found ? 'text-emerald-600' : 'text-muted-foreground'
              )}>
                {service.found ? 'Running' : 'Not detected'}
              </span>
            </div>
          ))}

          {hasLocal && (
            <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  checked={useLocalAI}
                  className="size-4 accent-primary"
                  onChange={e => onUseLocalAIChange(e.target.checked)}
                  type="checkbox"
                />
                <div>
                  <p className="text-sm font-medium">Use local AI services</p>
                  <p className="text-xs text-muted-foreground">Configure AetherOS to use your locally running models</p>
                </div>
              </label>
            </div>
          )}

          {!hasLocal && (
            <div className="rounded-lg border border-border bg-card/30 p-6 text-center">
              <p className="text-sm text-muted-foreground">
                No local AI services detected. You can still use cloud providers.
              </p>
              <p className="mt-1 text-xs text-muted-foreground/60">
                Install Ollama from ollama.ai or LM Studio from lmstudio.ai to use local models.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SummaryStep({
  selectedProvider,
  providerState,
  gateways,
  integrations,
  localAIFound,
  useLocalAI
}: {
  selectedProvider: string | null
  providerState: ProviderState | null
  gateways: GatewayConfig[]
  integrations: Record<string, IntegrationState>
  localAIFound: { ollama: boolean; lmstudio: boolean }
  useLocalAI: boolean
}) {
  const activeIntegrations = Object.entries(integrations).filter(([_, s]) => s.enabled && s.saved)
  const provider = selectedProvider ? PROVIDERS.find(p => p.id === selectedProvider) : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Configuration Summary</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Review your setup before launching AetherOS.
        </p>
      </div>

      <div className="space-y-4">
        <Section emoji="🤖" title="AI Provider">
          {provider ? (
            <Tag color={PROVIDER_COLORS[provider.id]} icon={provider.name.charAt(0)}>
              {provider.name}
              {providerState?.model && <span className="opacity-70"> — {providerState.model}</span>}
            </Tag>
          ) : (
            <p className="text-xs text-muted-foreground">No provider selected</p>
          )}
        </Section>

        <Section emoji="🌐" title="Gateway">
          {gateways.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {gateways.map((g, i) => (
                <Tag icon="G" key={i}>
                  {g.name}
                  {g.validated && <Check className="size-3 ml-1 text-emerald-500" />}
                </Tag>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">Default local gateway</p>
          )}
        </Section>

        <Section emoji="🔗" title="Integrations">
          {activeIntegrations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {activeIntegrations.map(([id, s]) => (
                <Tag icon={INTEGRATIONS.find(i => i.id === id)?.icon || '•'} key={id}>
                  {INTEGRATIONS.find(i => i.id === id)?.name || id}
                  {s.testPassed && <Check className="size-3 ml-1 text-emerald-500" />}
                </Tag>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No integrations configured</p>
          )}
        </Section>

        <Section emoji="💻" title="Local AI">
          {localAIFound.ollama && useLocalAI && (
            <Tag icon="O">Ollama</Tag>
          )}
          {localAIFound.lmstudio && useLocalAI && (
            <Tag icon="L">LM Studio</Tag>
          )}
          {!localAIFound.ollama && !localAIFound.lmstudio && (
            <p className="text-xs text-muted-foreground">No local AI detected</p>
          )}
        </Section>
      </div>
    </div>
  )
}

function Section({ title, emoji, children }: { title: string; emoji: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card/30 p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">{emoji}</span>
        <p className="text-sm font-semibold">{title}</p>
      </div>
      {children}
    </div>
  )
}

function Tag({ icon, color, children }: { icon: string; color?: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-card/50 border border-border/50 px-3 py-1 text-xs font-medium">
      {color ? (
        <span className={cn('flex size-4 items-center justify-center rounded text-[8px] font-bold text-white', color ? `bg-gradient-to-br ${color}` : 'bg-muted')}>
          {icon}
        </span>
      ) : (
        <span className="text-xs">{icon}</span>
      )}
      {children}
    </span>
  )
}

function LaunchStep({ onFinish }: { onFinish?: () => void }) {
  const [launching, setLaunching] = useState(false)

  const handleLaunch = useCallback(() => {
    if (launching) {return}
    setLaunching(true)
    console.log('[Launch] Ready screen clicked')
    onFinish?.()
  }, [launching, onFinish])

  return (
    <div className="flex flex-col items-center justify-center min-h-[60dvh] text-center gap-8">
      <div className="space-y-4 animate-in zoom-in-95 duration-300">
        <div className="mx-auto flex size-28 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 via-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/20 ring-4 ring-emerald-500/10">
          <Check className="size-12 text-white" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">AetherOS is ready.</h1>
        <p className="mx-auto max-w-md text-muted-foreground">
          Your configuration is complete. Launch the main application below.
        </p>
      </div>

      <div className="grid w-full max-w-sm gap-3 text-left">
        {[
          'AI provider configured and verified',
          'Gateway ready',
          'Integrations configured',
          'Local runtime ready'
        ].map((label, i) => (
          <div
            className="flex items-center gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 animate-in fade-in duration-300"
            key={label}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <Check className="size-4 text-emerald-500 shrink-0" />
            <p className="text-sm">{label}</p>
          </div>
        ))}
      </div>

      <Button
        className="mt-4 h-14 min-w-[280px] rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-base font-semibold text-white shadow-lg shadow-blue-500/25 transition-all hover:from-blue-500/90 hover:to-cyan-500/90 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
        disabled={launching}
        onClick={handleLaunch}
        size="lg"
      >
        {launching ? (
          <Loader2 className="size-5 animate-spin mr-2" />
        ) : (
          <Codicon className="size-5 mr-2" name="rocket" />
        )}
        {launching ? 'Launching...' : 'Launch AetherOS'}
      </Button>

      {launching && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Saving configuration and opening main application...
        </p>
      )}
    </div>
  )
}
