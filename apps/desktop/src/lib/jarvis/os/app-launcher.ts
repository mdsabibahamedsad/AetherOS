/**
 * Allowlisted external application launcher.
 *
 * Jarvis may only open applications/URLs on this list. The renderer never
 * passes executable paths or shell commands — it sends an `appId` (or an
 * https URL for `open-url`), validated here, then handed to the existing
 * narrow `openExternal` main-process IPC, which enforces its own scheme
 * allowlist (https + the two bare custom schemes below). Anything not on
 * the list is rejected with a typed error the UI can display.
 *
 * File Explorer / System Settings are intentionally NOT here: they cannot
 * pass the main-process URL validation. Use the gateway agent (terminal
 * tool + approvals) for file-manager tasks instead.
 */

export interface AllowedApp {
  id: string
  name: string
  kind: 'external-url' | 'system-handler'
  /** Exact target. Custom schemes must be bare (no path/query/credentials). */
  target: string
}

const ALLOWLIST: AllowedApp[] = [
  { id: 'chrome', name: 'Google Chrome', kind: 'external-url', target: 'https://www.google.com/' },
  { id: 'youtube', name: 'YouTube', kind: 'external-url', target: 'https://www.youtube.com/' },
  { id: 'vscode', name: 'VS Code', kind: 'system-handler', target: 'vscode://' },
  { id: 'spotify', name: 'Spotify', kind: 'system-handler', target: 'spotify://' }
]

export function listAllowedApps(): AllowedApp[] {
  return [...ALLOWLIST]
}

export function resolveApp(appId: string): AllowedApp | null {
  const id = appId.trim().toLowerCase()

  return ALLOWLIST.find(a => a.id === id) ?? null
}

/** Only https URLs may be opened. Everything else is rejected. */
export function validateOpenUrl(url: string): { ok: true; url: string } | { ok: false; error: string } {
  const trimmed = url.trim()

  let parsed: URL

  try {
    parsed = new URL(trimmed)
  } catch {
    return { ok: false, error: 'That is not a valid URL.' }
  }

  if (parsed.protocol !== 'https:') {return { ok: false, error: 'Only https URLs can be opened.' }}

  return { ok: true, url: parsed.toString() }
}

export interface LauncherDeps {
  openExternal: (target: string) => Promise<void>
}

export async function launchApp(appId: string, deps: LauncherDeps): Promise<AllowedApp> {
  const app = resolveApp(appId)

  if (!app) {
    throw new Error(`"${appId}" is not an allowlisted application. Allowed: ${ALLOWLIST.map(a => a.id).join(', ')}.`)
  }

  if (app.kind === 'system-handler') {
    // Bare custom scheme only — the main process rejects anything with
    // credentials, query strings or unexpected paths.
    const parsed = new URL(app.target)

    if (parsed.username || parsed.password || parsed.search || (parsed.pathname !== '' && parsed.pathname !== '/')) {
      throw new Error(`Misconfigured allowlist target for "${appId}".`)
    }
  }

  await deps.openExternal(app.target)

  return app
}

export async function openValidatedUrl(url: string, deps: LauncherDeps): Promise<string> {
  const checked = validateOpenUrl(url)

  if (!checked.ok) {throw new Error(checked.error)}

  await deps.openExternal(checked.url)

  return checked.url
}
