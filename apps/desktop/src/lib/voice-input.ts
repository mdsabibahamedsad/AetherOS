export interface VoiceInputOptions {
  deviceId?: string
  noiseSuppression?: boolean
  echoCancellation?: boolean
  autoGainControl?: boolean
  silenceThreshold?: number
  silenceTimeoutMs?: number
  maxDurationMs?: number
  onLevel?: (level: number) => void
  onSilence?: () => void
}

export interface VoiceInputResult {
  audioBlob: Blob
  durationMs: number
  sampleRate: number
  levels: Float32Array
}

let audioContext: AudioContext | null = null
let mediaRecorder: MediaRecorder | null = null
let analyserNode: AnalyserNode | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let mediaStream: MediaStream | null = null
let animationFrameId: number | null = null

function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  }

  return audioContext
}

export async function startVoiceInput(options: VoiceInputOptions = {}): Promise<MediaStream> {
  const constraints: MediaStreamConstraints = {
    audio: {
      deviceId: options.deviceId ? { exact: options.deviceId } : undefined,
      noiseSuppression: options.noiseSuppression ?? true,
      echoCancellation: options.echoCancellation ?? true,
      autoGainControl: options.autoGainControl ?? true,
    }
  }

  const stream = await navigator.mediaDevices.getUserMedia(constraints)
  mediaStream = stream

  const ctx = getAudioContext()
  sourceNode = ctx.createMediaStreamSource(stream)
  analyserNode = ctx.createAnalyser()
  analyserNode.fftSize = 256
  sourceNode.connect(analyserNode)

  const recorder = new MediaRecorder(stream, {
    mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'
  })

  mediaRecorder = recorder

  const chunks: BlobPart[] = []

  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) {chunks.push(e.data)}
  }

  recorder.start(100)

  const bufferLength = analyserNode.frequencyBinCount
  const dataArray = new Uint8Array(bufferLength)

  const levelCallback = () => {
    if (!analyserNode) {return}
    analyserNode.getByteFrequencyData(dataArray)
    const sum = dataArray.reduce((a, b) => a + b, 0)
    const level = sum / (bufferLength * 255)
    options.onLevel?.(level)
    animationFrameId = requestAnimationFrame(levelCallback)
  }

  animationFrameId = requestAnimationFrame(levelCallback)

  return stream
}

export function stopVoiceInput(): VoiceInputResult | null {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  if (!mediaRecorder || !mediaStream) {return null}

  return new Promise((resolve) => {
    const recorder = mediaRecorder!
    const chunks: BlobPart[] = []
    const originalPush = recorder.ondataavailable

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {chunks.push(e.data)}
      originalPush?.call(recorder, e)
    }

    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: recorder.mimeType })
      cleanup()

      resolve({
        audioBlob: blob,
        durationMs: 0,
        sampleRate: audioContext?.sampleRate || 48000,
        levels: new Float32Array()
      } as VoiceInputResult)
    }

    recorder.stop()
  }) as unknown as VoiceInputResult
}

export function cancelVoiceInput() {
  cleanup()
}

function cleanup() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop())
    mediaStream = null
  }

  if (sourceNode) {
    sourceNode.disconnect()
    sourceNode = null
  }

  if (analyserNode) {
    analyserNode.disconnect()
    analyserNode = null
  }

  mediaRecorder = null
}

export async function enumerateAudioDevices(): Promise<MediaDeviceInfo[]> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()

    return devices.filter(d => d.kind === 'audioinput')
  } catch {
    return []
  }
}

export function isVoiceInputSupported(): boolean {
  return !!(
    navigator.mediaDevices?.getUserMedia != null &&
    typeof (window.MediaRecorder ?? (window as any).MediaRecorder) === 'function'
  )
}
