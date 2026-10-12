import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { clearCrashRecord, hardReset, reloadApp } from '@/lib/crash-recovery'

interface CrashRecoveryProps {
  children: ReactNode
}

interface CrashRecoveryState {
  error: Error | null
  crashCount: number
}

export class CrashRecoveryBoundary extends Component<CrashRecoveryProps, CrashRecoveryState> {
  state: CrashRecoveryState = { error: null, crashCount: 0 }

  static getDerivedStateFromError(error: Error): Partial<CrashRecoveryState> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState(prev => ({ crashCount: prev.crashCount + 1 }))
    console.error('[crash-recovery]', error, info.componentStack)

    try {
      const record = JSON.parse(localStorage.getItem('aetheros.desktop.crashRecovery') || '{}')
      record.attempts = (record.attempts || 0) + 1
      record.lastCrash = Date.now()
      localStorage.setItem('aetheros.desktop.crashRecovery', JSON.stringify(record))
    } catch {
      // Non-fatal
    }
  }

  handleReset = () => {
    this.setState({ error: null })
    clearCrashRecord()
  }

  handleHardReset = () => {
    hardReset()
  }

  handleReload = () => {
    reloadApp()
  }

  render() {
    if (!this.state.error) {return this.props.children}

    const { crashCount } = this.state

    return (
      <div className="fixed inset-0 z-[1500] grid place-items-center bg-(--ui-chat-surface-background) p-6">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-destructive/10">
            <Codicon className="text-destructive" name="error" size="1.5rem" />
          </div>

          <div className="space-y-2">
            <h2 className="text-lg font-semibold tracking-tight">
              {crashCount > 1 ? 'Repeated Crash Detected' : 'Something went wrong'}
            </h2>
            <p className="text-sm text-(--ui-text-tertiary)">
              {crashCount > 1
                ? 'The application has crashed multiple times. A recovery option is available.'
                : this.state.error.message || 'An unexpected error occurred.'}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Button onClick={this.handleReload} size="lg">
              <Codicon className="mr-2" name="refresh" size="1rem" />
              Reload Application
            </Button>
            <Button onClick={this.handleHardReset} variant="outline">
              <Codicon className="mr-2" name="trash" size="1rem" />
              Hard Reset & Restart
            </Button>
            <Button
              onClick={() => window.aetherosDesktop?.revealLogs?.()?.catch(() => undefined)}
              variant="ghost"
            >
              <Codicon className="mr-2" name="output" size="1rem" />
              Open Logs
            </Button>
          </div>
        </div>
      </div>
    )
  }
}
