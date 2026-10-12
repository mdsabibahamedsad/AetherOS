import { useStore } from '@nanostores/react'
import { useCallback } from 'react'

import { $desktopOnboarding, dismissFirstRunOnboarding } from '@/store/onboarding'
import { $setupWizard } from '@/store/setup-wizard'

import { WizardContainer } from './wizard-container'

export function SetupWizardOverlay() {
  const onboarding = useStore($desktopOnboarding)
  const wizard = useStore($setupWizard)

  const showWizard = wizard.started || (wizard.needed && onboarding.configured === false)

  const handleComplete = useCallback(() => {
    dismissFirstRunOnboarding()
  }, [])

  if (!showWizard) {return null}

  return (
    <div className="fixed inset-0 z-[1500] flex flex-col overflow-hidden bg-background">
      <div className="flex flex-1 flex-col">
        <WizardContainer onComplete={handleComplete} />
      </div>
    </div>
  )
}
