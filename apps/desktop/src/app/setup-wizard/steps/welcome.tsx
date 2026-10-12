import { useStore } from '@nanostores/react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { $setupWizard, resumeSetupWizard, saveDraftAndExit, startSetupWizard } from '@/store/setup-wizard'

interface WelcomeStepProps {
  onNavigate: () => void
}

const SCRAMBLE_CHARS = 'アイウエオカキクケコサシスセソタチツテト'
const VERSION = '0.16.0'

function ScrambleText({ text }: { text: string }) {
  const [display, setDisplay] = useState(text)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (done) {return}
    let frame = 0
    const maxFrames = 40

    const interval = setInterval(() => {
      frame++

      if (frame >= maxFrames) {
        setDisplay(text)
        setDone(true)
        clearInterval(interval)

        return
      }

      setDisplay(
        text
          .split('')
          .map((ch, i) => {
            if (i < Math.floor((frame / maxFrames) * text.length)) {return ch}

            return SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)]
          })
          .join('')
      )
    }, 40)

    return () => clearInterval(interval)
  }, [text, done])

  return <span className="font-mono tracking-widest">{display}</span>
}

interface WizardButtonProps {
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'link'
  children: React.ReactNode
  onClick?: () => void
  className?: string
  icon?: string
}

function WizardButton({ variant = 'default', children, onClick, className = '', icon }: WizardButtonProps) {
  return (
    <Button className={`h-12 px-8 text-base font-medium ${className}`} onClick={onClick} variant={variant}>
      {icon && <span className="mr-2">{icon}</span>}
      {children}
    </Button>
  )
}

export function WelcomeStep({ onNavigate }: WelcomeStepProps) {
  const state = useStore($setupWizard)
  const hasDraft = state.currentStep > 0 && !state.completed

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center justify-center gap-10 py-16 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/20">
          <svg className="h-12 w-12 text-primary" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="20" strokeOpacity="0.3" />
            <path d="M24 8v8M24 32v8M8 24h8M32 24h8" strokeLinecap="round" />
            <circle cx="24" cy="24" fill="currentColor" fillOpacity="0.2" r="6" stroke="none" />
          </svg>
        </div>
        <h1 className="text-5xl font-bold tracking-tight">
          <ScrambleText text="AetherOS" />
        </h1>
        <p className="text-lg text-muted-foreground">
          Your personal AI operating system
        </p>
        <div className="flex items-center gap-2 rounded-full bg-muted px-4 py-1.5 text-xs text-muted-foreground">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-500" />
          Version {VERSION}
        </div>
      </div>

      <p className="max-w-lg leading-relaxed text-muted-foreground">
        Welcome to AetherOS — a self-improving AI agent that works across your desktop, 
        terminal, and messaging platforms. Let's get you set up in just a few steps.
      </p>

      <div className="flex flex-col gap-3">
        <WizardButton onClick={() => { startSetupWizard(); onNavigate() }}>
          Get Started
        </WizardButton>
        {hasDraft && (
          <WizardButton onClick={() => { resumeSetupWizard(); onNavigate() }} variant="secondary">
            Resume Setup
          </WizardButton>
        )}
        <WizardButton onClick={() => saveDraftAndExit()} variant="outline">
          Import Configuration
        </WizardButton>
        <WizardButton className="text-sm text-muted-foreground" variant="ghost">
          Restore Backup
        </WizardButton>
        <WizardButton className="text-sm" variant="link">
          Learn More
        </WizardButton>
      </div>
    </div>
  )
}
