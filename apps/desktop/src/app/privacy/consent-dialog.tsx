import { useStore } from '@nanostores/react'
import { useCallback, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import {
  $privacy,
  setAskBeforeUpload,
  setCameraPermission,
  setClipboardPermission,
  setEncryptedStorage,
  setFilePermission,
  setMicrophonePermission,
  setOfflineMode,
  setProcessingMode,
  setScreenPermission,
  setShowPrivacyIndicator
} from '@/store/privacy-store'
import type { ProcessingMode } from '@/store/privacy-store'

interface ConsentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  resource: 'microphone' | 'camera' | 'screen' | 'clipboard' | 'files'
  onConsent: (granted: boolean) => void
}

const RESOURCE_LABELS: Record<string, { icon: string; title: string; description: string }> = {
  microphone: {
    icon: 'M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z',
    title: 'Microphone Access',
    description: 'AetherOS needs access to your microphone for voice commands and speech-to-text.'
  },
  camera: {
    icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z',
    title: 'Camera Access',
    description: 'AetherOS needs access to your camera for capturing images and video analysis.'
  },
  screen: {
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    title: 'Screen Access',
    description: 'AetherOS needs screen access to analyze content and provide contextual assistance.'
  },
  clipboard: {
    icon: 'M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2',
    title: 'Clipboard Access',
    description: 'AetherOS needs clipboard access to process copied text and images.'
  },
  files: {
    icon: 'M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h6a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z',
    title: 'File Access',
    description: 'AetherOS needs file access to analyze documents, images, and other files.'
  }
}

export function ConsentDialog({ open, onOpenChange, resource, onConsent }: ConsentDialogProps) {
  const info = RESOURCE_LABELS[resource]
  const [rememberChoice, setRememberChoice] = useState(false)

  const handleAllow = useCallback(() => {
    if (rememberChoice) {
      if (resource === 'screen') {setScreenPermission({ state: 'granted', lastAccess: Date.now() })}
    }

    onConsent(true)
    onOpenChange(false)
  }, [rememberChoice, resource, onConsent, onOpenChange])

  const handleDeny = useCallback(() => {
    onConsent(false)
    onOpenChange(false)
  }, [onConsent, onOpenChange])

  if (!info) {return null}

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <svg className="size-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d={info.icon} strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
            </svg>
          </div>
          <DialogTitle className="text-center">{info.title}</DialogTitle>
          <p className="mt-1 text-center text-sm text-(--ui-text-tertiary)">
            {info.description}
          </p>
        </DialogHeader>

        <div className="flex flex-col gap-3 py-2">
          <div className="rounded-lg bg-(--ui-bg-quaternary) px-3 py-2">
            <div className="flex items-start gap-2">
              <svg className="mt-0.5 size-4 shrink-0 text-(--ui-text-tertiary)" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                <path clipRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" fillRule="evenodd" />
              </svg>
              <div className="text-xs text-(--ui-text-tertiary)">
                {resource === 'microphone' && 'You will be able to use voice commands, speech-to-text, and voice conversation.'}
                {resource === 'camera' && 'You will be able to capture photos, scan documents, and use video features.'}
                {resource === 'screen' && 'You will be able to capture screen content, share windows, and use contextual AI assistance.'}
                {resource === 'clipboard' && 'You will be able to paste and process text and images from your clipboard.'}
                {resource === 'files' && 'You will be able to analyze documents, images, and media files with AI.'}
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-xs text-(--ui-text-tertiary)">Remember my choice</div>
            <Switch checked={rememberChoice} onCheckedChange={setRememberChoice} />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:justify-center">
          <Button onClick={handleDeny} variant="outline">Deny</Button>
          <Button onClick={handleAllow}>Allow</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function PrivacySettingsPanel() {
  const state = useStore($privacy)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-lg font-semibold">Privacy & Security</h2>
        <p className="text-sm text-(--ui-text-tertiary)">
          Control how AetherOS accesses your data and devices
        </p>
      </div>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Processing Mode</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Processing Location</div>
            <div className="text-xs text-(--ui-text-tertiary)">Where voice/image data is processed</div>
          </div>
          <div className="flex gap-1 rounded-lg bg-(--ui-bg-tertiary) p-0.5">
            {(['local', 'hybrid', 'cloud'] as ProcessingMode[]).map(mode => (
              <button
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  state.processingMode === mode
                    ? 'bg-background text-foreground shadow-xs'
                    : 'text-(--ui-text-tertiary) hover:text-foreground'
                }`}
                key={mode}
                onClick={() => setProcessingMode(mode)}
                type="button"
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Ask Before Upload</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Confirm before sending data to cloud</div>
          </div>
          <Switch checked={state.askBeforeUpload} onCheckedChange={setAskBeforeUpload} />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Offline Mode</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Process everything locally</div>
          </div>
          <Switch checked={state.offlineMode} onCheckedChange={setOfflineMode} />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Permissions</h3>

        {([
          { key: 'microphone' as const, label: 'Microphone', icon: 'M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z' },
          { key: 'camera' as const, label: 'Camera', icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' },
          { key: 'screen' as const, label: 'Screen', icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
          { key: 'clipboard' as const, label: 'Clipboard', icon: 'M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1' },
          { key: 'files' as const, label: 'Files', icon: 'M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h6a2 2 0 012 2v1' }
        ]).map(perm => (
          <div className="flex items-center justify-between" key={perm.key}>
            <div className="flex items-center gap-2">
              <svg className="size-4 text-(--ui-text-tertiary)" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d={perm.icon} strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} />
              </svg>
              <div>
                <div className="text-sm font-medium">{perm.label}</div>
                <div className="text-xs text-(--ui-text-tertiary)">
                  {state[perm.key].state === 'granted' ? 'Granted' :
                   state[perm.key].state === 'denied' ? 'Denied' :
                   state[perm.key].state === 'ask' ? 'Ask each time' : 'Not determined'}
                </div>
              </div>
            </div>
            <button
              className={`rounded-md px-2 py-1 text-xs font-medium ${
                state[perm.key].state === 'granted'
                  ? 'bg-green-500/10 text-green-500'
                  : 'bg-(--ui-bg-tertiary) text-(--ui-text-tertiary)'
              }`}
              onClick={() => {
                const p = state[perm.key]

                const setter = perm.key === 'microphone' ? setMicrophonePermission :
                              perm.key === 'camera' ? setCameraPermission :
                              perm.key === 'screen' ? setScreenPermission :
                              perm.key === 'clipboard' ? setClipboardPermission : setFilePermission

                setter({ state: p.state === 'granted' ? 'denied' : 'granted', lastAccess: Date.now() })
              }}
              type="button"
            >
              {state[perm.key].state === 'granted' ? 'Revoke' : 'Grant'}
            </button>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-4">
        <h3 className="text-sm font-medium text-(--ui-text-secondary)">Data Management</h3>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Encrypted Storage</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Encrypt locally stored data</div>
          </div>
          <Switch
            checked={state.encryptedStorage}
            onCheckedChange={setEncryptedStorage}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Privacy Indicators</div>
            <div className="text-xs text-(--ui-text-tertiary)}">Show mic/camera/screen indicators</div>
          </div>
          <Switch
            checked={state.showPrivacyIndicator}
            onCheckedChange={setShowPrivacyIndicator}
          />
        </div>
      </section>
    </div>
  )
}
