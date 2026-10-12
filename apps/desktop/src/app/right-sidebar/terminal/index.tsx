import '@xterm/xterm/css/xterm.css'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Loader } from '@/components/ui/loader'
import { StatusDot } from '@/components/ui/status-dot'
import { Tip } from '@/components/ui/tooltip'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'

import { setTerminalTakeover } from '../store'

import { addSelectionShortcutLabel } from './selection'
import { useTerminalSession } from './use-terminal-session'

interface TerminalTabProps {
  cwd: string
  onAddSelectionToChat: (text: string, label?: string) => void
}

export function TerminalTab({ cwd, onAddSelectionToChat }: TerminalTabProps) {
  const { t } = useI18n()

  const { addSelectionToChat, hostRef, selection, selectionStyle, shellName, status, riskLevel, policyViolation } = useTerminalSession({
    cwd,
    onAddSelectionToChat
  })

  const label = t.rightSidebar.terminalHide

  const riskLabels: Record<string, string> = {
    safe: 'SAFE',
    warning: 'WARNING',
    high: 'HIGH RISK',
    blocked: 'BLOCKED'
  }

  const riskColors: Record<string, string> = {
    safe: 'text-emerald-400 bg-emerald-500/10',
    warning: 'text-amber-400 bg-amber-500/10',
    high: 'text-red-400 bg-red-500/10',
    blocked: 'text-gray-400 bg-gray-500/10'
  }

  return (
    <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex h-8 shrink-0 items-center gap-2 px-2.5">
        <span className="text-(--ui-text-secondary)! font-medium">{shellName}</span>
        {riskLevel && (
          <StatusDot
            className={cn('ml-2', riskColors[riskLevel])}
            size="sm"
            status={riskLevel as any}
          />
        )}
        <Tip label={label}>
          <Button
            aria-label={label}
            className="ml-auto size-6 rounded-md text-(--ui-text-secondary)!"
            onClick={() => setTerminalTakeover(false)}
            size="icon"
            type="button"
            variant="ghost"
          >
            <Codicon name="close" size="0.875rem" />
          </Button>
        </Tip>
      </div>
      <div className="relative min-h-0 flex-1 bg-(--ui-editor-surface-background) p-2">
        {status === 'starting' && (
          <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center">
            <Loader
              className="size-8 text-(--ui-text-tertiary)"
              pathSteps={180}
              strokeScale={0.68}
              type="spiral-search"
            />
          </div>
        )}
        {policyViolation && (
          <div className="absolute top-2 right-2 bg-red-500/20 border border-red-500/20 rounded p-2 text-xs text-red-400">
            <span className="codicon codicon-alert" />
            <span>Policy violation: {policyViolation}</span>
          </div>
        )}
        {selection.trim() && (
          <div className="absolute z-50 flex items-center gap-1" style={selectionStyle ?? { right: 12, top: 8 }}>
            <Button
              className="h-6 rounded-md px-2 text-[0.68rem] shadow-md backdrop-blur-md"
              onClick={event => event.preventDefault()}
              onMouseDown={event => {
                event.preventDefault()
                event.stopPropagation()
                addSelectionToChat()
              }}
              type="button"
              variant="secondary"
            >
              {t.rightSidebar.addToChat}
              <span className="ml-1 text-[0.6rem] text-(--ui-text-tertiary)">{addSelectionShortcutLabel()}</span>
            </Button>
          </div>
        )}
        {/* Outer div paints terminal inset; inner div is the xterm host so the
            canvas sizes to the content area and p-2 stays as terminal padding.
            Screen/viewport inherit the live skin surface so the terminal blends
            with the app and follows light/dark; the xterm canvas itself is
            painted the resolved surface color in use-terminal-session. */}
        <div
          className="h-full min-h-0 overflow-hidden text-(--ui-text-secondary) [&_.xterm]:h-full [&_.xterm-screen]:bg-(--ui-editor-surface-background)!
          [&_.xterm-viewport]:bg-(--ui-editor-surface-background)!"
          ref={hostRef}
        />
      </div>
    </div>
  )
}