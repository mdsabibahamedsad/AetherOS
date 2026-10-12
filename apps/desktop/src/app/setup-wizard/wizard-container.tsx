import { useStore } from '@nanostores/react'
import { useCallback, useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  $setupWizard, completeSetupWizard, goToStep, nextStep, prevStep, saveDraftAndExit,
  setWizardError
} from '@/store/setup-wizard'

import { AgentStep } from './steps/agent'
import { AuthenticationStep } from './steps/authentication'
import { ExtensionsStep } from './steps/extensions'
import { FinishStep } from './steps/finish'
import { InitializationStep } from './steps/initialization'
import { KnowledgeStep } from './steps/knowledge'
import { LocalAiStep } from './steps/local-ai'
import { MemoryStep } from './steps/memory'
import { ModelsStep } from './steps/models'
import { ProfileStep } from './steps/profile'
import { ProvidersStep } from './steps/providers'
import { SecurityStep } from './steps/security'
import { ServicesStep } from './steps/services'
import { SummaryStep } from './steps/summary'
import { WelcomeStep } from './steps/welcome'
import { WorkspaceStep } from './steps/workspace'

export const STEP_LABELS = [
  'Welcome',
  'Profile',
  'Workspace',
  'Providers',
  'Models',
  'Authentication',
  'Local AI',
  'Services',
  'Memory',
  'Security',
  'Extensions',
  'Knowledge',
  'Agent',
  'Summary',
  'Initialize',
  'Finish'
]

const STEP_ICONS = [
  '◈', '👤', '📁', '☁', '🧠', '🔑', '💻', '🔗', '🧩', '🛡', '🧰', '📚', '🤖', '📋', '⚙', '✓'
]

function ProgressBar({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  const progress = Math.round((currentStep / (totalSteps - 1)) * 100)

  return (
    <div className="mb-8">
      <div className="mb-2 flex items-center justify-between px-1 text-xs text-muted-foreground">
        <span>Step {Math.min(currentStep + 1, totalSteps)} of {totalSteps}</span>
        <span>{progress}%</span>
      </div>
      <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}

function StepIndicator({ currentStep }: { currentStep: number }) {
  const visible = useMemo(() => {
    const range: number[] = []

    for (let i = Math.max(0, currentStep - 2); i <= Math.min(STEP_LABELS.length - 1, currentStep + 2); i++) {
      range.push(i)
    }

    return range
  }, [currentStep])

  return (
    <div className="flex items-center justify-center gap-2 py-2">
      {visible[0] > 0 && <span className="text-xs text-muted-foreground">...</span>}
      {visible.map(step => (
        <button
          className={cn(
            'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition-all',
            step === currentStep
              ? 'bg-primary text-primary-foreground font-medium'
              : step < currentStep
                ? 'bg-muted text-muted-foreground hover:bg-accent'
                : 'text-muted-foreground/50 hover:text-muted-foreground'
          )}
          key={step}
          onClick={() => goToStep(step)}
          type="button"
        >
          <span className={cn('text-[10px]', step === currentStep ? 'opacity-80' : 'opacity-40')}>{STEP_ICONS[step]}</span>
          {STEP_LABELS[step]}
        </button>
      ))}
      {visible[visible.length - 1] < STEP_LABELS.length - 1 && <span className="text-xs text-muted-foreground">...</span>}
    </div>
  )
}

interface WizardContainerProps {
  onComplete: () => void
}

export function WizardContainer({ onComplete }: WizardContainerProps) {
  const state = useStore($setupWizard)
  const step = state.currentStep
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleFinish = useCallback(() => {
    completeSetupWizard()
    onComplete()
  }, [onComplete])

  const validateStep = (): boolean => {
    setValidationError(null)
    setWizardError(null)

    switch (step) {
      case 1: {
        if (!state.profile.displayName.trim()) {
          setValidationError('Please enter your display name')

          return false
        }

        if (!state.profile.workspaceName.trim()) {
          setValidationError('Please enter a workspace name')

          return false
        }

        return true
      }

      case 3: {
        if (state.providers.length === 0) {
          setValidationError('Please select at least one AI provider')

          return false
        }

        return true
      }

      case 5: {
        const unauthenticated = state.providers.filter(
          p => p.authType === 'api_key' && !p.authenticated
        )

        if (unauthenticated.length > 0) {
          setValidationError('Please configure API keys for all selected providers')

          return false
        }

        return true
      }

      default:
        return true
    }
  }

  const handleNext = () => {
    if (!validateStep()) {return}
    nextStep()
  }

  const renderStep = () => {
    switch (step) {
      case 0: return <WelcomeStep onNavigate={() => nextStep()} />

      case 1: return <ProfileStep />

      case 2: return <WorkspaceStep />

      case 3: return <ProvidersStep />

      case 4: return <ModelsStep />

      case 5: return <AuthenticationStep />

      case 6: return <LocalAiStep />

      case 7: return <ServicesStep />

      case 8: return <MemoryStep />

      case 9: return <SecurityStep />

      case 10: return <ExtensionsStep />

      case 11: return <KnowledgeStep />

      case 12: return <AgentStep />

      case 13: return <SummaryStep />

      case 14: return <InitializationStep onComplete={() => nextStep()} />

      case 15: return (
        <FinishStep
          onCreateProject={handleFinish}
          onOpenWorkspace={handleFinish}
          onStartChat={handleFinish}
          onViewDocs={handleFinish}
        />
      )

      default: return null
    }
  }

  const canGoBack = step > 1
  const isWelcome = step === 0
  const isInit = step === 14
  const isFinish = step === 15
  const showNav = !isWelcome && !isFinish

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-8 py-6">
        {!isWelcome && !isFinish && <ProgressBar currentStep={step} totalSteps={16} />}
        {!isWelcome && !isFinish && <StepIndicator currentStep={step} />}
        <div className="flex min-h-0 flex-1 items-center justify-center">
          {renderStep()}
        </div>
      </div>

      {showNav && (
        <div className="flex items-center justify-between border-t px-8 py-4">
          <div className="flex gap-2">
            {canGoBack && (
              <Button onClick={prevStep} variant="ghost">
                Back
              </Button>
            )}
          </div>

          <div className="flex flex-col items-end gap-1">
            {validationError && (
              <p className="text-xs text-destructive">{validationError}</p>
            )}
            <div className="flex gap-2">
              {step === 13 && (
                <Button className="px-8" onClick={() => goToStep(14)} variant="default">
                  Initialize
                </Button>
              )}
              {step > 0 && step < 13 && (
                <Button className="px-8" onClick={handleNext} variant="default">
                  {step === 11 || step === 12 ? 'Continue' : 'Next'}
                </Button>
              )}
              {step > 0 && step < 13 && (
                <Button className="text-sm text-muted-foreground" onClick={saveDraftAndExit} variant="outline">
                  Save & Exit
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
