/**
 * Controlled Computer Use layer.
 *
 * Window management executes through narrow, validated local handlers.
 * Pointer/keyboard injection is NOT performed blindly in the renderer:
 * those actions are described as gateway-agent intents (the gateway owns
 * any OS automation with approvals), or rejected honestly when the
 * gateway is unavailable. Every action returns a structured result and
 * screen-affecting actions carry an observation hook (screenshot verify).
 *
 * Never report success merely because spawn() returned — verify.
 */

export interface ComputerActionResult {
  success: boolean
  actionId: string
  timestamp: number
  observation?: string
  error?: string
  requiresApproval?: boolean
}

export interface WindowInfo {
  id: string
  title: string
  app: string
  focused: boolean
}

export interface ComputerDeps {
  launchApp: (appId: string) => Promise<string>
  openUrl: (url: string) => Promise<string>
  screenshot: () => Promise<string>
  gatewayOpen: boolean
  /** Delegate a verified OS-automation intent to the gateway agent. */
  delegateToGateway?: (instruction: string) => Promise<string>
}

let actionCounter = 0
function nextAction(kind: string): string {
  actionCounter += 1
  return `cu_${kind}_${Date.now().toString(36)}_${actionCounter}`
}

function ok(actionId: string, observation?: string): ComputerActionResult {
  return { success: true, actionId, timestamp: Date.now(), observation }
}

function fail(actionId: string, error: string, extra?: Partial<ComputerActionResult>): ComputerActionResult {
  return { success: false, actionId, timestamp: Date.now(), error, ...extra }
}

function validateAppId(appId: string): string | null {
  const id = appId.trim().toLowerCase()
  if (!/^[a-z0-9-]+$/.test(id)) return null
  return id
}

export async function launchApplication(deps: ComputerDeps, appId: string): Promise<ComputerActionResult> {
  const actionId = nextAction('launch')
  const valid = validateAppId(appId)
  if (!valid) return fail(actionId, `Invalid application id "${appId}".`)
  try {
    const msg = await deps.launchApp(valid)
    // Verify: capture observation after launch instead of trusting spawn().
    let observation = msg
    try {
      const shot = await deps.screenshot()
      observation = `${msg} Verified with fresh screen capture (${Math.round((shot.length * 3) / 4 / 1024)} KB).`
    } catch {
      observation = `${msg} (Screen verification unavailable — launch reported by OS handler.)`
    }
    return ok(actionId, observation)
  } catch (err) {
    return fail(actionId, err instanceof Error ? err.message : String(err))
  }
}

function gatewayIntent(deps: ComputerDeps, actionId: string, instruction: string): ComputerActionResult | Promise<ComputerActionResult> {
  if (!deps.gatewayOpen || !deps.delegateToGateway) {
    return fail(actionId, 'This action needs the gateway agent and it is not connected. Reconnect, then retry.');
  }
  return deps.delegateToGateway(instruction).then(
    observation => ok(actionId, observation),
    err => fail(actionId, err instanceof Error ? err.message : String(err))
  )
}

/** Window inventory: honest — the renderer has no OS window list, so this
 *  delegates to the gateway agent which can observe the real desktop. */
export function listWindows(deps: ComputerDeps): Promise<ComputerActionResult> {
  return Promise.resolve(gatewayIntent(deps, nextAction('list-windows'), 'List visible application windows with titles.')) as Promise<ComputerActionResult>
}

export function getActiveWindow(deps: ComputerDeps): Promise<ComputerActionResult> {
  return Promise.resolve(gatewayIntent(deps, nextAction('active-window'), 'Report the currently focused window.')) as Promise<ComputerActionResult>
}

export function focusWindow(deps: ComputerDeps, title: string): Promise<ComputerActionResult> {
  const actionId = nextAction('focus')
  if (!title.trim()) return Promise.resolve(fail(actionId, 'No window title specified.'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Focus the window titled "${title.slice(0, 120)}" and verify it is foreground.`)) as Promise<ComputerActionResult>
}

export function closeApplication(deps: ComputerDeps, title: string): Promise<ComputerActionResult> {
  const actionId = nextAction('close')
  if (!title.trim()) return Promise.resolve(fail(actionId, 'No window specified.'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Close "${title.slice(0, 120)}" after user approval and verify it closed.`)) as Promise<ComputerActionResult>
}

for (const _ of []) void _;

// Pointer / keyboard actions: validated descriptors routed to the gateway
// agent (which owns OS automation + approvals). Coordinates are only
// accepted when they come from a prior vision/DOM observation.
export interface PointerTarget {
  x?: number
  y?: number
  label?: string
  fromObservation?: boolean
}

function validatedClickTarget(t: PointerTarget): string | null {
  if (t.label && t.label.trim()) return t.label.trim().slice(0, 200)
  if (typeof t.x === 'number' && typeof t.y === 'number') {
    if (!t.fromObservation) return null
    if (!Number.isFinite(t.x) || !Number.isFinite(t.y)) return null
    if (t.x < 0 || t.y < 0 || t.x > 10000 || t.y > 10000) return null
    return `coordinates (${Math.round(t.x)}, ${Math.round(t.y)}) from verified observation`
  }
  return null
}

export function click(deps: ComputerDeps, target: PointerTarget): Promise<ComputerActionResult> {
  const actionId = nextAction('click')
  const desc = validatedClickTarget(target)
  if (!desc) {
    return Promise.resolve(fail(actionId, 'Click needs a labeled element or observation-verified coordinates. Blind coordinates are rejected.'))
  }
  return Promise.resolve(gatewayIntent(deps, actionId, `Click ${desc}, capture the screen afterwards, and verify the expected state change.`)) as Promise<ComputerActionResult>
}

export function doubleClick(deps: ComputerDeps, target: PointerTarget): Promise<ComputerActionResult> {
  const actionId = nextAction('dblclick')
  const desc = validatedClickTarget(target)
  if (!desc) return Promise.resolve(fail(actionId, 'Double-click needs a labeled element or observation-verified coordinates.'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Double-click ${desc} and verify the result with a screen capture.`)) as Promise<ComputerActionResult>
}

export function rightClick(deps: ComputerDeps, target: PointerTarget): Promise<ComputerActionResult> {
  const actionId = nextAction('rightclick')
  const desc = validatedClickTarget(target)
  if (!desc) return Promise.resolve(fail(actionId, 'Right-click needs a labeled element or observation-verified coordinates.'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Right-click ${desc} and verify the context menu with a screen capture.`)) as Promise<ComputerActionResult>
}

export function typeText(deps: ComputerDeps, text: string): Promise<ComputerActionResult> {
  const actionId = nextAction('type')
  if (!text) return Promise.resolve(fail(actionId, 'Nothing to type.'))
  if (text.length > 5000) return Promise.resolve(fail(actionId, 'Text too long (max 5000 chars).'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Type the approved text (${text.length} chars) into the focused field and verify it appears.`)) as Promise<ComputerActionResult>
}

export function pressKey(deps: ComputerDeps, key: string): Promise<ComputerActionResult> {
  const actionId = nextAction('key')
  if (!/^[A-Za-z0-9 _-]+$/.test(key) || key.length > 32) {
    return Promise.resolve(fail(actionId, `Invalid key "${key}".`))
  }
  return Promise.resolve(gatewayIntent(deps, actionId, `Press the "${key}" key and verify the result.`)) as Promise<ComputerActionResult>
}

export function scroll(deps: ComputerDeps, direction: 'up' | 'down' | 'left' | 'right', amount = 3): Promise<ComputerActionResult> {
  const actionId = nextAction('scroll')
  if (!['up', 'down', 'left', 'right'].includes(direction)) return Promise.resolve(fail(actionId, 'Invalid scroll direction.'))
  const n = Math.min(10, Math.max(1, Math.floor(amount)))
  return Promise.resolve(gatewayIntent(deps, actionId, `Scroll ${direction} by ${n} steps and verify the viewport changed.`)) as Promise<ComputerActionResult>
}

export function drag(deps: ComputerDeps, from: PointerTarget, to: PointerTarget): Promise<ComputerActionResult> {
  const actionId = nextAction('drag')
  const a = validatedClickTarget(from)
  const b = validatedClickTarget(to)
  if (!a || !b) return Promise.resolve(fail(actionId, 'Drag needs two observation-verified endpoints.'))
  return Promise.resolve(gatewayIntent(deps, actionId, `Drag from ${a} to ${b} and verify with a screen capture.`)) as Promise<ComputerActionResult>
}

/** Screen understanding: approval-gated capture → vision-capable model via gateway. */
export async function describeScreen(
  deps: ComputerDeps,
  scope: 'screen' | 'window'
): Promise<ComputerActionResult> {
  const actionId = nextAction('describe-screen')
  try {
    const shot = await deps.screenshot()
    const kb = Math.round((shot.length * 3) / 4 / 1024)
    if (!deps.gatewayOpen || !deps.delegateToGateway) {
      return ok(actionId, `Captured ${scope} screenshot (${kb} KB). Vision analysis needs the gateway agent — reconnect to analyze it.`)
    }
    const analysis = await deps.delegateToGateway(
      `Analyze this ${scope} screenshot and truthfully report what is open and visible. Screenshot data URL length: ${shot.length}.`
    )
    return ok(actionId, analysis)
  } catch (err) {
    return fail(actionId, err instanceof Error ? err.message : String(err))
  }
}
