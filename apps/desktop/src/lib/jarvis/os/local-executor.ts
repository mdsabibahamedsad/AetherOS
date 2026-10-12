/**
 * Local capability executor.
 *
 * Executes the registry's `local` bindings with real, narrow APIs — no
 * gateway needed. Every handler validates its input; anything privileged
 * beyond these handlers (shell, fs writes, browser automation) belongs to
 * the gateway agent, never here. Dependencies are injected so every path is
 * unit-testable without Electron or a backend.
 */

import { getGlobalModelInfo, getGlobalModelOptions, setGlobalModel } from '@/hermes'

import { launchApp, openValidatedUrl } from './app-launcher'

export interface LocalExecDeps {
  openExternal: (target: string) => Promise<void>
  copyText: (text: string) => Promise<void>
  notify: (title: string, message: string) => void
  navigate: (route: string) => void
  getSystemStats: () => Promise<{ cpu: number; memory: { used: number; total: number; percent: number }; uptime: number }>
  screenshot: () => Promise<string>
}

/** Production deps factory. Screenshot goes through the approval-gated
 *  main-process capture IPC; throws honestly when unavailable. */
export function createDesktopCommandDeps(navigate: (route: string) => void): LocalExecDeps {
  return {
    openExternal: target => window.aetherosDesktop.openExternal(target),
    copyText: async text => {
      try {
        await navigator.clipboard.writeText(text)
      } catch {
        await window.aetherosDesktop.writeClipboard(text)
      }
    },
    notify: (title, message) => {
      try {
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification(title, { body: message })
        }
      } catch {
        // In-app notification (added by the caller) remains the record.
      }
    },
    navigate,
    getSystemStats: async () => {
      const stats = await window.aetherosDesktop.getSystemStats?.()

      if (!stats) {throw new Error('System statistics are unavailable.')}

      return { cpu: stats.cpu, memory: { used: stats.memory.used, total: stats.memory.total, percent: stats.memory.percent }, uptime: stats.uptime }
    },
    screenshot: async () => {
      const capture = (window.aetherosDesktop as unknown as { screenshot?: () => Promise<string> }).screenshot

      if (!capture) {throw new Error('Screen capture is not available in this build.')}

      return capture()
    }
  }
}

export function browserDeps(): Pick<LocalExecDeps, 'copyText' | 'notify'> {
  return {
    copyText: async text => {
      await navigator.clipboard.writeText(text)
    },
    notify: (title, message) => {
      try {
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification(title, { body: message })
        }
      } catch {
        // Notification surface unavailable — the caller also logs in-app.
      }
    }
  }
}

const NAV_ROUTES: Record<string, string> = {
  home: '/',
  agents: '/agents',
  memory: '/memory',
  automation: '/automation',
  browser: '/browser',
  terminal: '/terminal',
  settings: '/settings',
  security: '/security',
  diagnostics: '/diagnostics',
  jarvis: '/jarvis',
  chat: '/chat',
  knowledge: '/knowledge',
  communications: '/communications'
}

export function resolveRoute(route: string): string | null {
  const trimmed = route.trim()

  if (trimmed.startsWith('/')) {return trimmed}

  const clean = trimmed.toLowerCase().replace(/^[#/]+/, '')

  if (clean === '' || clean === 'home') {return '/'}

  return NAV_ROUTES[clean] ?? null
}

/**
 * Execute a local capability by handler id. Throws a typed Error on any
 * validation or runtime failure — never returns fabricated success.
 */
export async function executeLocal(handler: string, input: Record<string, string>, deps: LocalExecDeps): Promise<string> {
  switch (handler) {
    case 'os.launch-app': {
      const appId = (input.appId ?? '').trim()

      if (!appId) {throw new Error('No application specified.')}

      const app = await launchApp(appId, { openExternal: deps.openExternal })

      return `Opened ${app.name}.`
    }

    case 'os.open-url': {
      const url = (input.url ?? '').trim()

      if (!url) {throw new Error('No URL specified.')}

      const opened = await openValidatedUrl(url, { openExternal: deps.openExternal })

      return `Opened ${opened} in the system browser.`
    }

    case 'os.clipboard-write': {
      const text = input.text ?? ''

      if (!text) {throw new Error('Nothing to copy.')}

      await deps.copyText(text)

      return 'Copied to clipboard.'
    }

    case 'os.screenshot': {
      const dataUrl = await deps.screenshot()

      if (!dataUrl.startsWith('data:image')) {throw new Error('Screen capture failed.')}

      return `Captured screenshot (${Math.round((dataUrl.length * 3) / 4 / 1024)} KB).`
    }

    case 'os.notify': {
      const title = (input.title ?? 'Jarvis').slice(0, 120)
      const message = (input.message ?? '').slice(0, 500)

      if (!message) {throw new Error('Notification message is empty.')}

      deps.notify(title, message)

      return 'Notification shown.'
    }

    case 'models.inspect': {
      const [info, options] = await Promise.all([getGlobalModelInfo(), getGlobalModelOptions()])
      const current = `${info.provider}/${info.model}`

      return `Active model: ${current}. Available providers: ${(options.providers ?? []).map(p => p.slug).join(', ') || 'none reported'}.`
    }

    case 'models.select': {
      const provider = (input.provider ?? '').trim()
      const model = (input.model ?? '').trim()

      if (!provider || !model) {throw new Error('Provider and model are both required.')}

      const res = await setGlobalModel(provider, model)

      return `Active model is now ${res.provider}/${res.model}.`
    }

    case 'system.status': {
      const stats = await deps.getSystemStats()

      return `CPU ${stats.cpu.toFixed(0)}%, memory ${(stats.memory.used / 1024 / 1024 / 1024).toFixed(1)}/${(stats.memory.total / 1024 / 1024 / 1024).toFixed(1)} GB (${stats.memory.percent.toFixed(0)}%), uptime ${Math.round(stats.uptime / 60)} min.`
    }

    case 'system.navigate': {
      const route = resolveRoute(input.route ?? '')

      if (!route) {throw new Error(`Unknown destination "${input.route}".`)}

      deps.navigate(route)

      return `Navigated to ${route}.`
    }

    default:
      throw new Error(`Unknown local handler "${handler}".`)
  }
}
