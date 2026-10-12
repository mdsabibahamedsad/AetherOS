import { addJarvisNotification as addToast, setAutonomyState, syncEngineState, updateEngineStats } from '@/store/jarvis-mode'

const BACKEND_URL = 'http://127.0.0.1:9789'
const WS_URL = 'ws://127.0.0.1:9789/api/jarvis/ws'

type MessageHandler = (data: any) => void

class JarvisBackendBridge {
  private ws: WebSocket | null = null
  private connected = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private handlers = new Map<string, MessageHandler[]>()
  private pendingRequests = new Map<string, { resolve: Function; reject: Function; timeout: ReturnType<typeof setTimeout> }>()

  get isConnected() { return this.connected }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {this.handlers.set(type, [])}
    this.handlers.get(type)!.push(handler)

    return () => {
      const arr = this.handlers.get(type)

      if (arr) {
        const idx = arr.indexOf(handler)

        if (idx >= 0) {arr.splice(idx, 1)}
      }
    }
  }

  private emit(type: string, data: any) {
    const arr = this.handlers.get(type)

    if (arr) {arr.forEach(h => { try { h(data) } catch {} })}
    const wildcard = this.handlers.get('*')

    if (wildcard) {wildcard.forEach(h => { try { h({ type, data }) } catch {} })}
  }

  async connect(): Promise<boolean> {
    if (this.connected) {return true}

    if (this.ws) {
      try { this.ws.close() } catch {}
    }

    return new Promise(resolve => {
      try {
        const ws = new WebSocket(WS_URL)

        ws.onopen = () => {
          this.connected = true
          this.ws = ws
          console.log('[Jarvis] Connected to backend')
          resolve(true)
        }

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)

            if (msg.type === 'pong' && msg.id && this.pendingRequests.has(msg.id)) {
              const pending = this.pendingRequests.get(msg.id)!
              clearTimeout(pending.timeout)
              pending.resolve(msg.data)
              this.pendingRequests.delete(msg.id)
            } else {
              this.emit(msg.type, msg.data)
            }
          } catch {}
        }

        ws.onclose = () => {
          this.connected = false
          this.ws = null
          console.log('[Jarvis] Disconnected from backend')
          this.scheduleReconnect()
          resolve(false)
        }

        ws.onerror = () => {
          this.connected = false
          resolve(false)
        }
      } catch {
        resolve(false)
      }
    })
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {return}
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, 5000)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      try { this.ws.close() } catch {}
      this.ws = null
    }

    this.connected = false
  }

  send(type: string, data: any = {}) {
    if (this.ws && this.connected) {
      this.ws.send(JSON.stringify({ type, data }))
    }
  }

  private requestId = 0

  async request(type: string, data: any = {}): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.ws || !this.connected) {
        reject(new Error('Not connected'))

        return
      }

      const id = `req_${++this.requestId}`

      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id)
        reject(new Error('Request timeout'))
      }, 30000)

      this.pendingRequests.set(id, { resolve, reject, timeout })
      this.ws.send(JSON.stringify({ type, data, id }))
    })
  }

  async fetchAPI<T = any>(path: string, options: RequestInit = {}): Promise<T | null> {
    try {
      const res = await fetch(`${BACKEND_URL}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers as any },
        ...options,
      })

      if (!res.ok) {return null}

      return await res.json() as T
    } catch {
      return null
    }
  }
}

export const jarvisBridge = new JarvisBackendBridge()

export async function connectToBackend() {
  const connected = await jarvisBridge.connect()

  if (connected) {
    jarvisBridge.on('engine:state', (state: any) => {
      syncEngineState({
        phase: state.phase || 'idle',
        cycleCount: state.cycleCount || 0,
        isRunning: state.isRunning || false,
      })
    })

    jarvisBridge.on('notification', (notif: any) => {
      addToast({
        title: notif.title,
        message: notif.message,
        type: notif.level === 'error' ? 'error' : notif.level === 'warning' ? 'warning' : notif.level === 'success' ? 'success' : 'info',
      })
    })

    const stats = await jarvisBridge.fetchAPI<any>('/api/jarvis/stats')

    if (stats) {
      updateEngineStats({
        tasks: stats.tasks,
        notifications: stats.notifications?.unread ?? 0,
        skills: stats.skills?.total ?? 0,
        memory: stats.memory?.total ?? 0,
      })
    }

    const status = await jarvisBridge.fetchAPI<any>('/api/jarvis/status')

    if (status) {
      syncEngineState({
        phase: status.engine?.phase || 'idle',
        cycleCount: status.engine?.cycleCount || 0,
        isRunning: status.engine?.isRunning || false,
      })

      if (status.autonomy) {
        setAutonomyState(status.autonomy.enabled, status.autonomy.level)
      }
    }
  }

  return connected
}

export async function sendCommand(command: string) {
  return jarvisBridge.fetchAPI('/api/jarvis/command', {
    method: 'POST',
    body: JSON.stringify({ command }),
  })
}

export async function startEngine() {
  return jarvisBridge.fetchAPI('/api/jarvis/engine/start', { method: 'POST' })
}

export async function stopEngine() {
  return jarvisBridge.fetchAPI('/api/jarvis/engine/stop', { method: 'POST' })
}

export async function pauseEngine() {
  return jarvisBridge.fetchAPI('/api/jarvis/engine/pause', { method: 'POST' })
}

export async function resumeEngine() {
  return jarvisBridge.fetchAPI('/api/jarvis/engine/resume', { method: 'POST' })
}

export async function setAutonomy(enabled: boolean, level: string = 'suggestions') {
  return jarvisBridge.fetchAPI('/api/jarvis/autonomy', {
    method: 'POST',
    body: JSON.stringify({ enabled, level }),
  })
}

export async function getMemory(query: string = '', type: string = '') {
  return jarvisBridge.fetchAPI(`/api/jarvis/memory?query=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`)
}

export async function addMemory(key: string, content: any, type: string = 'fact', tags: string[] = []) {
  return jarvisBridge.fetchAPI('/api/jarvis/memory', {
    method: 'POST',
    body: JSON.stringify({ key, content, type, tags }),
  })
}

export async function getNotifications() {
  return jarvisBridge.fetchAPI('/api/jarvis/notifications')
}

export async function getGraphs() {
  return jarvisBridge.fetchAPI('/api/jarvis/planner/graphs')
}

export async function getPendingSuggestions() {
  return jarvisBridge.fetchAPI('/api/jarvis/autonomy/pending')
}

export async function acceptSuggestion(index: number) {
  return jarvisBridge.fetchAPI('/api/jarvis/autonomy/accept', {
    method: 'POST',
    body: JSON.stringify({ index }),
  })
}

export async function rejectSuggestion(index: number) {
  return jarvisBridge.fetchAPI('/api/jarvis/autonomy/reject', {
    method: 'POST',
    body: JSON.stringify({ index }),
  })
}

export async function getContext() {
  return jarvisBridge.fetchAPI('/api/jarvis/context')
}

export async function getExecutorTasks() {
  return jarvisBridge.fetchAPI('/api/jarvis/executor/tasks')
}

export async function getObserverEvents() {
  return jarvisBridge.fetchAPI('/api/jarvis/observer/events')
}

export async function getSchedulerJobs() {
  return jarvisBridge.fetchAPI('/api/jarvis/scheduler/jobs')
}

export async function checkHealth() {
  return jarvisBridge.fetchAPI('/api/jarvis/health')
}
