import { atom } from 'nanostores'

export type MultimodalInputType =
  | 'text'
  | 'image'
  | 'audio'
  | 'video'
  | 'code'
  | 'document'
  | 'mixed'

export type ProcessingStatus = 'idle' | 'processing' | 'success' | 'error'

export type CameraStatus = 'idle' | 'opening' | 'active' | 'error'

export type ScreenCaptureStatus = 'idle' | 'selecting' | 'active' | 'error'

export interface CameraInfo {
  deviceId: string
  label: string
  facingMode?: 'user' | 'environment' | 'left' | 'right'
}

export interface ScreenCaptureState {
  status: ScreenCaptureStatus
  permissionGranted: boolean
  activeWindow?: string
  region?: { x: number; y: number; width: number; height: number }
  lastCapture?: string
}

export interface PrivacyIndicatorState {
  micActive: boolean
  cameraActive: boolean
  screenActive: boolean
  dataSentToCloud: boolean
}

export interface ProcessingState {
  image: ProcessingStatus
  audio: ProcessingStatus
  video: ProcessingStatus
  document: ProcessingStatus
  voice: ProcessingStatus
}

export interface ModelRoutingState {
  detectedInputType: MultimodalInputType
  requiredCapabilities: string[]
  selectedModelId: string | null
  selectedProvider: string | null
  autoRouted: boolean
}

export interface MultimodalState {
  cameras: CameraInfo[]
  selectedCameraId: string | null
  cameraStatus: CameraStatus
  cameraStream: MediaStream | null
  screenCapture: ScreenCaptureState
  privacy: PrivacyIndicatorState
  processing: ProcessingState
  routing: ModelRoutingState
  ttsEnabled: boolean
  sttEnabled: boolean
  visionEnabled: boolean
  localMode: boolean
  preferredVoice: string
  audioInputDeviceId: string
  audioOutputDeviceId: string
}

export const $multimodal = atom<MultimodalState>({
  cameras: [],
  selectedCameraId: null,
  cameraStatus: 'idle',
  cameraStream: null,
  screenCapture: {
    status: 'idle',
    permissionGranted: false
  },
  privacy: {
    micActive: false,
    cameraActive: false,
    screenActive: false,
    dataSentToCloud: false
  },
  processing: {
    image: 'idle',
    audio: 'idle',
    video: 'idle',
    document: 'idle',
    voice: 'idle'
  },
  routing: {
    detectedInputType: 'text',
    requiredCapabilities: [],
    selectedModelId: null,
    selectedProvider: null,
    autoRouted: true
  },
  ttsEnabled: true,
  sttEnabled: true,
  visionEnabled: true,
  localMode: false,
  preferredVoice: 'default',
  audioInputDeviceId: '',
  audioOutputDeviceId: ''
})

const patch = (update: Partial<MultimodalState>) =>
  $multimodal.set({ ...$multimodal.get(), ...update })

export function setCameras(cameras: CameraInfo[]) {
  patch({ cameras })
}

export function setSelectedCameraId(deviceId: string | null) {
  patch({ selectedCameraId: deviceId })
}

export function setCameraStatus(status: CameraStatus) {
  patch({ cameraStatus: status })
}

export function setCameraStream(stream: MediaStream | null) {
  const current = $multimodal.get().cameraStream

  if (current && current !== stream) {
    current.getTracks().forEach(t => t.stop())
  }

  patch({ cameraStream: stream })
}

export function setScreenCaptureState(state: Partial<ScreenCaptureState>) {
  patch({
    screenCapture: { ...$multimodal.get().screenCapture, ...state }
  })
}

export function setPrivacyIndicator(indicator: Partial<PrivacyIndicatorState>) {
  patch({
    privacy: { ...$multimodal.get().privacy, ...indicator }
  })
}

export function setProcessingStatus(modality: keyof ProcessingState, status: ProcessingStatus) {
  patch({
    processing: { ...$multimodal.get().processing, [modality]: status }
  })
}

export function setModelRoutingState(update: Partial<ModelRoutingState>) {
  patch({
    routing: { ...$multimodal.get().routing, ...update }
  })
}

export function setTtsEnabled(enabled: boolean) {
  patch({ ttsEnabled: enabled })
}

export function setSttEnabled(enabled: boolean) {
  patch({ sttEnabled: enabled })
}

export function setVisionEnabled(enabled: boolean) {
  patch({ visionEnabled: enabled })
}

export function setLocalMode(local: boolean) {
  patch({ localMode: local })
}

export function setPreferredVoice(voice: string) {
  patch({ preferredVoice: voice })
}

export function setAudioInputDeviceId(deviceId: string) {
  patch({ audioInputDeviceId: deviceId })
}

export function setAudioOutputDeviceId(deviceId: string) {
  patch({ audioOutputDeviceId: deviceId })
}

export function resetCamera() {
  setCameraStream(null)
  setCameraStatus('idle')
  setSelectedCameraId(null)
  setPrivacyIndicator({ cameraActive: false })
}

export function resetScreenCapture() {
  setScreenCaptureState({
    status: 'idle',
    permissionGranted: false,
    activeWindow: undefined,
    region: undefined,
    lastCapture: undefined
  })
  setPrivacyIndicator({ screenActive: false })
}

export function resetPrivacyIndicators() {
  patch({
    privacy: { micActive: false, cameraActive: false, screenActive: false, dataSentToCloud: false }
  })
}

export async function enumerateCameras(): Promise<CameraInfo[]> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()

    const cameras = devices
      .filter(d => d.kind === 'videoinput')
      .map(d => ({
        deviceId: d.deviceId,
        label: d.label || `Camera ${d.deviceId.slice(0, 8)}`
      }))

    setCameras(cameras)

    return cameras
  } catch {
    return []
  }
}

export async function openCamera(deviceId?: string): Promise<MediaStream | null> {
  try {
    setCameraStatus('opening')

    const constraints: MediaStreamConstraints = {
      video: deviceId ? { deviceId: { exact: deviceId } } : true
    }

    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    setCameraStream(stream)
    setCameraStatus('active')
    setPrivacyIndicator({ cameraActive: true })

    if (deviceId) {setSelectedCameraId(deviceId)}

    return stream
  } catch {
    setCameraStatus('error')

    return null
  }
}

export function captureCameraFrame(): string | null {
  const stream = $multimodal.get().cameraStream

  if (!stream) {return null}

  const video = document.createElement('video')
  video.srcObject = stream
  video.play()

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')

  if (!ctx) {return null}

  ctx.drawImage(video, 0, 0)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.9)

  video.pause()
  video.srcObject = null

  return dataUrl
}
