/**
 * OS-global Jarvis hotkey management (renderer side).
 *
 * The accelerator is user-configurable (default CommandOrControl+Space),
 * persisted locally, and registered through the narrow main-process IPC.
 * Registration failures surface as typed errors for the settings UI —
 * never silent. The main process focuses the window and emits
 * `aetheros:jarvis:focus`; the app shell navigates to /jarvis and focuses
 * the composer.
 */

import { addJarvisNotification } from '@/store/jarvis-mode'

export const DEFAULT_JARVIS_HOTKEY = 'CommandOrControl+Space'
const STORAGE_KEY = 'aetheros.jarvis.hotkey.v1'

export function getJarvisHotkey(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_JARVIS_HOTKEY
  } catch {
    return DEFAULT_JARVIS_HOTKEY
  }
}

export function setJarvisHotkeySetting(accelerator: string) {
  try {
    localStorage.setItem(STORAGE_KEY, accelerator)
  } catch {
    // Private mode — the registration below still applies for this session.
  }
}

export async function applyJarvisHotkey(accelerator: string): Promise<{ ok: boolean; error?: string }> {
  const api = window.aetherosDesktop?.jarvisHotkey

  if (!api) {
    return { ok: false, error: 'Global shortcuts are not supported in this build.' }
  }

  try {
    const res = await api.set(accelerator)

    return { ok: res.ok }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Shortcut registration failed.'
    addJarvisNotification({ title: 'Hotkey unavailable', message, type: 'warning' })

    return { ok: false, error: message }
  }
}

export async function clearJarvisHotkey(): Promise<void> {
  try {
    await window.aetherosDesktop?.jarvisHotkey?.clear()
  } catch {
    // Best effort on teardown.
  }
}
