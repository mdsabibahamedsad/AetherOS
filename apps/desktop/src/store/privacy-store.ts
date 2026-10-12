import { atom } from 'nanostores'

export type ProcessingMode = 'cloud' | 'local' | 'hybrid'
export type PermissionState = 'granted' | 'denied' | 'ask' | 'not_determined'

export interface MicrophonePermission { state: PermissionState; lastAccess: number | null }
export interface CameraPermission { state: PermissionState; lastAccess: number | null }
export interface ScreenPermission { state: PermissionState; lastAccess: number | null }
export interface ClipboardPermission { state: PermissionState; lastAccess: number | null }
export interface FilePermission { state: PermissionState; lastAccess: number | null }

export interface PrivacyState {
  processingMode: ProcessingMode
  askBeforeUpload: boolean
  offlineMode: boolean
  microphone: MicrophonePermission
  camera: CameraPermission
  screen: ScreenPermission
  clipboard: ClipboardPermission
  files: FilePermission
  dataCollectionEnabled: boolean
  anonymizeData: boolean
  retainHistory: boolean
  historyRetentionDays: number
  autoClearHistory: boolean
  showPrivacyIndicator: boolean
  requireConsentForVoice: boolean
  requireConsentForScreen: boolean
  requireConsentForCamera: boolean
  requireConsentForClipboard: boolean
  consentTimeoutMs: number
  allowedDomains: string[]
  blockedDomains: string[]
  encryptedStorage: boolean
}

export const $privacy = atom<PrivacyState>({
  processingMode: 'hybrid',
  askBeforeUpload: true,
  offlineMode: false,
  microphone: { state: 'not_determined', lastAccess: null },
  camera: { state: 'not_determined', lastAccess: null },
  screen: { state: 'not_determined', lastAccess: null },
  clipboard: { state: 'not_determined', lastAccess: null },
  files: { state: 'not_determined', lastAccess: null },
  dataCollectionEnabled: false,
  anonymizeData: true,
  retainHistory: true,
  historyRetentionDays: 30,
  autoClearHistory: false,
  showPrivacyIndicator: true,
  requireConsentForVoice: true,
  requireConsentForScreen: true,
  requireConsentForCamera: true,
  requireConsentForClipboard: true,
  consentTimeoutMs: 30000,
  allowedDomains: [],
  blockedDomains: [],
  encryptedStorage: true
})

const patch = (u: Partial<PrivacyState>) =>
  $privacy.set({ ...$privacy.get(), ...u })

export function setProcessingMode(m: ProcessingMode) { patch({ processingMode: m }) }

export function setAskBeforeUpload(a: boolean) { patch({ askBeforeUpload: a }) }

export function setOfflineMode(o: boolean) { patch({ offlineMode: o }) }

export function setMicrophonePermission(p: Partial<MicrophonePermission>) {
  patch({ microphone: { ...$privacy.get().microphone, ...p } })
}

export function setCameraPermission(p: Partial<CameraPermission>) {
  patch({ camera: { ...$privacy.get().camera, ...p } })
}

export function setScreenPermission(p: Partial<ScreenPermission>) {
  patch({ screen: { ...$privacy.get().screen, ...p } })
}

export function setClipboardPermission(p: Partial<ClipboardPermission>) {
  patch({ clipboard: { ...$privacy.get().clipboard, ...p } })
}

export function setFilePermission(p: Partial<FilePermission>) {
  patch({ files: { ...$privacy.get().files, ...p } })
}

export function setDataCollectionEnabled(e: boolean) { patch({ dataCollectionEnabled: e }) }

export function setAnonymizeData(a: boolean) { patch({ anonymizeData: a }) }

export function setRetainHistory(r: boolean) { patch({ retainHistory: r }) }

export function setHistoryRetentionDays(d: number) { patch({ historyRetentionDays: d }) }

export function setAutoClearHistory(a: boolean) { patch({ autoClearHistory: a }) }

export function setShowPrivacyIndicator(s: boolean) { patch({ showPrivacyIndicator: s }) }

export function setEncryptedStorage(e: boolean) { patch({ encryptedStorage: e }) }

export async function requestPermission(kind: 'microphone' | 'camera' | 'screen'): Promise<boolean> {
  try {
    if (kind === 'microphone') {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(t => t.stop())
      setMicrophonePermission({ state: 'granted', lastAccess: Date.now() })

      return true
    }

    if (kind === 'camera') {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      stream.getTracks().forEach(t => t.stop())
      setCameraPermission({ state: 'granted', lastAccess: Date.now() })

      return true
    }

    if (kind === 'screen') {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
      stream.getTracks().forEach(t => t.stop())
      setScreenPermission({ state: 'granted', lastAccess: Date.now() })

      return true
    }

    return false
  } catch {
    if (kind === 'microphone') {setMicrophonePermission({ state: 'denied' })}
    else if (kind === 'camera') {setCameraPermission({ state: 'denied' })}
    else if (kind === 'screen') {setScreenPermission({ state: 'denied' })}

    return false
  }
}
