/**
 * Jarvis capability registry.
 *
 * Every capability Jarvis can perform is declared here with a typed contract.
 * There are exactly two execution bindings — nothing executes anywhere else:
 *
 * - `gateway-agent`: executed by the live Aetheros gateway agent
 *   (session.create + prompt.submit + streaming tool events). These are only
 *   `available` when the gateway socket is open. The registry never claims a
 *   result — results come back as real gateway events.
 * - `local`: executed in the desktop renderer/main process through a narrow,
 *   validated IPC or router action (navigation, system stats, allowlisted app
 *   launch, clipboard, notifications). Each local capability names its handler
 *   id; handlers live in `lib/jarvis/os/*` or the router and MUST validate
 *   input before touching any privileged API.
 *
 * `available` is computed from live state, never hardcoded true: gateway
 * capabilities require an open gateway, local ones require their underlying
 * API to exist. UI must render unavailable capabilities as disabled with the
 * reason from `unavailableReason`, never as working.
 */

export type CapabilityCategory =
  | 'computer'
  | 'browser'
  | 'terminal'
  | 'files'
  | 'code'
  | 'memory'
  | 'knowledge'
  | 'automation'
  | 'communications'
  | 'agents'
  | 'models'
  | 'system'

export type CapabilityPermission =
  | 'read'
  | 'write'
  | 'execute'
  | 'network'
  | 'communicate'
  | 'system'
  | 'destructive'

export type CapabilityRisk = 'low' | 'medium' | 'high' | 'critical'

export type CapabilityBinding =
  | { via: 'gateway-agent' }
  | { via: 'local'; handler: string }

export interface CapabilitySchema {
  /** JSON-schema-ish descriptor of the accepted input. Kept minimal on purpose. */
  type: 'object'
  properties: Record<string, { type: string; description: string }>
  required: string[]
}

export interface Capability {
  id: string
  name: string
  description: string
  category: CapabilityCategory
  inputSchema: CapabilitySchema
  outputSchema: CapabilitySchema
  permissions: CapabilityPermission[]
  riskLevel: CapabilityRisk
  supportsStreaming: boolean
  supportsCancellation: boolean
  supportsApproval: boolean
  binding: CapabilityBinding
}

export interface ResolvedCapability extends Capability {
  available: boolean
  unavailableReason: string | null
}

function schema(
  properties: Record<string, { type: string; description: string }>,
  required: string[] = []
): CapabilitySchema {
  return { type: 'object', properties, required }
}

const TEXT_OUT = schema({ text: { type: 'string', description: 'Human-readable result' } })
const OK_OUT = schema({ ok: { type: 'boolean', description: 'Whether the action succeeded' } })

function gw(
  id: string,
  name: string,
  description: string,
  category: CapabilityCategory,
  permissions: CapabilityPermission[],
  riskLevel: CapabilityRisk,
  inputProps: Record<string, { type: string; description: string }>,
  required: string[] = [],
  flags: Partial<Pick<Capability, 'supportsStreaming' | 'supportsCancellation' | 'supportsApproval'>> = {}
): Capability {
  return {
    id,
    name,
    description,
    category,
    inputSchema: schema(inputProps, required),
    outputSchema: TEXT_OUT,
    permissions,
    riskLevel,
    supportsStreaming: true,
    supportsCancellation: true,
    supportsApproval: riskLevel === 'high' || riskLevel === 'critical',
    binding: { via: 'gateway-agent' },
    ...flags
  }
}

function local(
  id: string,
  name: string,
  description: string,
  category: CapabilityCategory,
  handler: string,
  permissions: CapabilityPermission[],
  riskLevel: CapabilityRisk,
  inputProps: Record<string, { type: string; description: string }>,
  required: string[] = []
): Capability {
  return {
    id,
    name,
    description,
    category,
    inputSchema: schema(inputProps, required),
    outputSchema: OK_OUT,
    permissions,
    riskLevel,
    supportsStreaming: false,
    supportsCancellation: false,
    supportsApproval: riskLevel === 'high' || riskLevel === 'critical',
    binding: { via: 'local', handler }
  }
}

export const CAPABILITIES: Capability[] = [
  // ---- COMPUTER (local, allowlisted + validated) ----
  // launch-app / open-url carry no permission gate: the allowlist + https-only
  // validation IS the safety boundary (no executable paths, no shell, no
  // arbitrary targets ever reach the main process). Screenshot stays gated.
  local('computer.launch-app', 'Open application', 'Launch an allowlisted desktop application or URL.', 'computer', 'os.launch-app', [], 'low', {
    appId: { type: 'string', description: 'Allowlisted application id, e.g. "vscode", "chrome", "spotify", "explorer".' }
  }, ['appId']),
  local('computer.open-url', 'Open URL', 'Open an https URL in the system browser after validation.', 'computer', 'os.open-url', [], 'low', {
    url: { type: 'string', description: 'https URL to open.' }
  }, ['url']),
  local('computer.clipboard-write', 'Copy to clipboard', 'Write text to the OS clipboard.', 'computer', 'os.clipboard-write', ['write'], 'low', {
    text: { type: 'string', description: 'Text to copy.' }
  }, ['text']),
  local('computer.screenshot', 'Screenshot', 'Capture the screen or a window. Requires explicit per-capture approval.', 'computer', 'os.screenshot', ['read', 'system'], 'high', {
    source: { type: 'string', description: '"screen" or "window". Defaults to "screen".' }
  }),
  gw('computer.window', 'Window control', 'List, focus, close or verify application windows via the gateway agent with observation.', 'computer', ['execute'], 'medium', {
    action: { type: 'string', description: 'One of: list, focus, close, verify.' },
    title: { type: 'string', description: 'Window title for focus/close/verify.' }
  }, ['action']),
  gw('computer.input', 'Pointer and keyboard', 'Validated click/type/scroll/keypress executed by the gateway agent with screen verification. Always requires approval.', 'computer', ['execute', 'system'], 'high', {
    action: { type: 'string', description: 'One of: click, double-click, right-click, type, key, scroll, drag.' },
    target: { type: 'string', description: 'Labeled element or observation-verified coordinates.' }
  }, ['action', 'target']),
  local('computer.notify', 'Notify', 'Show a desktop notification with a result or status.', 'computer', 'os.notify', [], 'low', {
    title: { type: 'string', description: 'Notification title.' },
    message: { type: 'string', description: 'Notification body.' }
  }, ['title', 'message']),

  // ---- BROWSER (gateway agent drives the real browser tool) ----
  gw('browser.navigate', 'Navigate browser', 'Navigate the automated browser to a URL and report what loaded.', 'browser', ['network', 'read'], 'low', {
    url: { type: 'string', description: 'URL to navigate to.' }
  }, ['url']),
  gw('browser.search-web', 'Search web', 'Search the web and return cited sources.', 'browser', ['network', 'read'], 'low', {
    query: { type: 'string', description: 'Search query.' }
  }, ['query']),
  gw('browser.interact', 'Interact with page', 'Click, type, scroll, select, upload or download on the current page.', 'browser', ['network', 'write'], 'medium', {
    action: { type: 'string', description: 'One of: click, type, scroll, select, upload, download.' },
    target: { type: 'string', description: 'Selector or description of the page element.' },
    value: { type: 'string', description: 'Text to type or value to select, if applicable.' }
  }, ['action', 'target']),
  gw('browser.extract', 'Extract page content', 'Inspect the page and extract structured content.', 'browser', ['network', 'read'], 'low', {
    instruction: { type: 'string', description: 'What to extract from the current page.' }
  }, ['instruction']),
  gw('browser.task', 'Multi-step browser task', 'Execute a multi-step browser workflow and report each step.', 'browser', ['network', 'write'], 'medium', {
    goal: { type: 'string', description: 'End goal of the browser workflow.' }
  }, ['goal']),

  // ---- TERMINAL (gateway agent owns shell execution + approvals) ----
  gw('terminal.execute', 'Execute command', 'Run a shell command and return stdout, stderr and exit code.', 'terminal', ['execute'], 'medium', {
    command: { type: 'string', description: 'Shell command to run.' },
    cwd: { type: 'string', description: 'Working directory. Defaults to the agent workspace.' }
  }, ['command']),
  gw('terminal.task', 'Long-running process', 'Start a supervised long-running process with streamed output.', 'terminal', ['execute'], 'medium', {
    command: { type: 'string', description: 'Command to supervise.' }
  }, ['command']),

  // ---- FILES ----
  gw('files.search', 'Search files', 'Search the workspace filesystem by name or content.', 'files', ['read'], 'low', {
    query: { type: 'string', description: 'Filename fragment or content query.' }
  }, ['query']),
  gw('files.read', 'Read file', 'Read a workspace file and return its content.', 'files', ['read'], 'low', {
    path: { type: 'string', description: 'Workspace-relative file path.' }
  }, ['path']),
  gw('files.write', 'Write file', 'Create or overwrite a workspace file. Destructive targets need approval.', 'files', ['write'], 'medium', {
    path: { type: 'string', description: 'Workspace-relative file path.' },
    content: { type: 'string', description: 'Full file content to write.' }
  }, ['path', 'content']),
  gw('files.organize', 'Organize files', 'Move, copy, rename or archive files per a confirmed plan.', 'files', ['write'], 'medium', {
    plan: { type: 'string', description: 'Describe which files go where.' }
  }, ['plan']),
  gw('files.delete', 'Delete files', 'Delete files. Always requires explicit approval.', 'files', ['destructive'], 'critical', {
    paths: { type: 'string', description: 'Comma-separated workspace-relative paths.' }
  }, ['paths']),

  // ---- CODE ----
  gw('code.inspect', 'Inspect repository', 'Inspect repo layout, package scripts and entry points.', 'code', ['read'], 'low', {
    path: { type: 'string', description: 'Repository path. Defaults to workspace root.' }
  }),
  gw('code.search', 'Search source', 'Search source code for symbols, patterns or usages.', 'code', ['read'], 'low', {
    query: { type: 'string', description: 'Symbol or pattern to find.' }
  }, ['query']),
  gw('code.edit', 'Edit source', 'Apply a source edit or patch and verify it parses.', 'code', ['write'], 'medium', {
    instruction: { type: 'string', description: 'Describe the edit to make and where.' }
  }, ['instruction']),
  gw('code.test', 'Run tests', 'Run the project test suite and report real pass/fail output.', 'code', ['execute'], 'medium', {
    scope: { type: 'string', description: 'Optional test scope or file filter.' }
  }),
  gw('code.build', 'Run build', 'Run the project build and report success or the real error.', 'code', ['execute'], 'medium', {
    target: { type: 'string', description: 'Optional build target.' }
  }),
  gw('code.git', 'Inspect git', 'Report git status, branches, diff or log.', 'code', ['read'], 'low', {
    action: { type: 'string', description: 'One of: status, diff, log, branches.' }
  }, ['action']),

  // ---- MEMORY ----
  gw('memory.remember', 'Remember', 'Store a user-approved fact in long-term memory.', 'memory', ['write'], 'low', {
    fact: { type: 'string', description: 'Fact to remember.' }
  }, ['fact']),
  gw('memory.recall', 'Recall', 'Recall relevant memories for a query.', 'memory', ['read'], 'low', {
    query: { type: 'string', description: 'What to recall.' }
  }, ['query']),
  gw('memory.forget', 'Forget', 'Remove a stored memory on request.', 'memory', ['write'], 'medium', {
    query: { type: 'string', description: 'Which memory to remove.' }
  }, ['query']),

  // ---- KNOWLEDGE ----
  gw('knowledge.search', 'Search knowledge', 'Search indexed knowledge and documents.', 'knowledge', ['read'], 'low', {
    query: { type: 'string', description: 'Knowledge query.' }
  }, ['query']),
  gw('knowledge.summarize', 'Summarize sources', 'Summarize documents or passages with source references.', 'knowledge', ['read'], 'low', {
    instruction: { type: 'string', description: 'What to summarize and from where.' }
  }, ['instruction']),

  // ---- AUTOMATION ----
  gw('automation.schedule', 'Schedule task', 'Create a scheduled or recurring background task.', 'automation', ['write', 'execute'], 'medium', {
    instruction: { type: 'string', description: 'What to run and when (e.g. "tomorrow 9am", "every monday").' }
  }, ['instruction']),
  gw('automation.manage', 'Manage tasks', 'List, pause, resume, trigger or cancel scheduled tasks.', 'automation', ['write'], 'low', {
    action: { type: 'string', description: 'One of: list, pause, resume, trigger, cancel.' },
    jobId: { type: 'string', description: 'Job id for pause/resume/trigger/cancel.' }
  }, ['action']),

  // ---- COMMUNICATIONS ----
  gw('communications.send', 'Send message', 'Send an email or platform message. Always requires approval.', 'communications', ['communicate'], 'high', {
    channel: { type: 'string', description: 'Destination channel or address.' },
    message: { type: 'string', description: 'Message to send.' }
  }, ['channel', 'message']),
  gw('communications.history', 'Communication history', 'Show recent notifications and message history.', 'communications', ['read'], 'low', {}),

  // ---- AGENTS ----
  gw('agents.delegate', 'Delegate task', 'Spawn a specialized subagent for a task and collect its result.', 'agents', ['execute'], 'medium', {
    task: { type: 'string', description: 'Task to delegate.' },
    kind: { type: 'string', description: 'Specialist kind: research, coding, browser, file, automation, monitor, communication.' }
  }, ['task']),
  gw('agents.status', 'Agent status', 'Report running agents, sessions and background tasks.', 'agents', ['read'], 'low', {}),

  // ---- MODELS ----
  local('models.inspect', 'Inspect models', 'List available models/providers from the live backend.', 'models', 'models.inspect', ['read'], 'low', {}),
  local('models.select', 'Select model', 'Switch the active model via the backend model API.', 'models', 'models.select', ['write'], 'low', {
    provider: { type: 'string', description: 'Provider id.' },
    model: { type: 'string', description: 'Model id.' }
  }, ['provider', 'model']),

  // ---- SYSTEM ----
  local('system.status', 'System status', 'Read live CPU, memory, storage and backend health.', 'system', 'system.status', ['read'], 'low', {}),
  local('system.navigate', 'Navigate AetherOS', 'Navigate the desktop app to a route (home, agents, memory, ...).', 'system', 'system.navigate', [], 'low', {
    route: { type: 'string', description: 'App route, e.g. "/", "/jarvis", "/agents".' }
  }, ['route'])
]

const BY_ID = new Map(CAPABILITIES.map(c => [c.id, c]))

export function getCapability(id: string): Capability | null {
  return BY_ID.get(id) ?? null
}

export function capabilitiesByCategory(category: CapabilityCategory): Capability[] {
  return CAPABILITIES.filter(c => c.category === category)
}

export interface Availability {
  gatewayOpen: boolean
  localHandlers: Set<string>
}

/**
 * Resolve live availability. Gateway-bound capabilities require an open
 * gateway; local ones require their handler to be registered. Anything else
 * is reported unavailable with a reason — never executed blind.
 */
export function resolveAvailability(avail: Availability): ResolvedCapability[] {
  return CAPABILITIES.map(cap => {
    if (cap.binding.via === 'gateway-agent') {
      return {
        ...cap,
        available: avail.gatewayOpen,
        unavailableReason: avail.gatewayOpen ? null : 'Gateway disconnected — reconnect to enable agent capabilities.'
      }
    }

    const ok = avail.localHandlers.has(cap.binding.handler)

    return {
      ...cap,
      available: ok,
      unavailableReason: ok ? null : `Local handler "${cap.binding.handler}" is not registered.`
    }
  })
}

/** Gateway tool names the agent may report, mapped to capability ids for the timeline. */
const TOOL_TO_CAPABILITY: Array<{ match: RegExp; capabilityId: string }> = [
  { match: /browser/i, capabilityId: 'browser.task' },
  { match: /web_search|web_extract|search/i, capabilityId: 'browser.search-web' },
  { match: /terminal|execute_code|shell/i, capabilityId: 'terminal.execute' },
  { match: /read_file|write_file|search_files|patch/i, capabilityId: 'files.read' },
  { match: /memory/i, capabilityId: 'memory.recall' },
  { match: /cron/i, capabilityId: 'automation.schedule' },
  { match: /delegate/i, capabilityId: 'agents.delegate' },
  { match: /skill/i, capabilityId: 'knowledge.search' }
]

export function capabilityForTool(toolName: string): string | null {
  for (const { match, capabilityId } of TOOL_TO_CAPABILITY) {
    if (match.test(toolName)) {return capabilityId}
  }

  return null
}
