import type { WorkspaceContext } from '../types'

// ─── Workspace Context Manager ────────────────────────────────────────────────

let currentContext: WorkspaceContext = {
  cwd: '',
  openFiles: [],
  recentCommands: []
}

const contextListeners: Array<(ctx: WorkspaceContext) => void> = []

export function getWorkspaceContext(): WorkspaceContext {
  return { ...currentContext }
}

export function updateWorkspaceContext(updates: Partial<WorkspaceContext>) {
  currentContext = { ...currentContext, ...updates }
  contextListeners.forEach(fn => fn(currentContext))
}

export function onWorkspaceContextChange(fn: (ctx: WorkspaceContext) => void): () => void {
  contextListeners.push(fn)

  return () => {
    const idx = contextListeners.indexOf(fn)

    if (idx >= 0) {contextListeners.splice(idx, 1)}
  }
}

// ─── Detect Project Type ──────────────────────────────────────────────────────

export function detectProjectType(cwd: string): { type?: string; framework?: string; language?: string } {
  const lower = cwd.toLowerCase()

  // Language detection via file extensions (would read actual files in production)
  if (lower.includes('python') || lower.includes('.py')) {return { language: 'python', type: 'python' }}

  if (lower.includes('node') || lower.includes('npm')) {return { language: 'typescript', type: 'node' }}

  if (lower.includes('rust') || lower.includes('cargo')) {return { language: 'rust', type: 'rust' }}

  if (lower.includes('go')) {return { language: 'go', type: 'go' }}

  return { language: undefined, type: undefined, framework: undefined }
}

// ─── File Tracking ────────────────────────────────────────────────────────────

export function trackOpenFile(path: string) {
  if (!currentContext.openFiles.includes(path)) {
    currentContext.openFiles = [...currentContext.openFiles, path].slice(-20)
    contextListeners.forEach(fn => fn(currentContext))
  }
}

export function untrackOpenFile(path: string) {
  currentContext.openFiles = currentContext.openFiles.filter(f => f !== path)
  contextListeners.forEach(fn => fn(currentContext))
}

// ─── Command Tracking ─────────────────────────────────────────────────────────

export function trackCommand(command: string) {
  currentContext.recentCommands = [command, ...currentContext.recentCommands.filter(c => c !== command)].slice(0, 20)
  contextListeners.forEach(fn => fn(currentContext))
}

// ─── Context Building for AI ──────────────────────────────────────────────────

export function buildContextPrompt(): string {
  const ctx = currentContext
  const parts: string[] = []

  if (ctx.cwd) {parts.push(`Working directory: ${ctx.cwd}`)}

  if (ctx.gitRoot) {parts.push(`Git root: ${ctx.gitRoot}`)}

  if (ctx.branch) {parts.push(`Branch: ${ctx.branch}`)}

  if (ctx.projectType) {parts.push(`Project type: ${ctx.projectType}`)}

  if (ctx.framework) {parts.push(`Framework: ${ctx.framework}`)}

  if (ctx.language) {parts.push(`Language: ${ctx.language}`)}

  if (ctx.openFiles.length > 0) {parts.push(`Open files: ${ctx.openFiles.join(', ')}`)}

  if (ctx.recentCommands.length > 0) {parts.push(`Recent commands: ${ctx.recentCommands.slice(0, 5).join('; ')}`)}

  return parts.length > 0 ? `Workspace context:\n${parts.join('\n')}` : ''
}

// ─── Auto-Detect from Electron ────────────────────────────────────────────────

export async function autoDetectWorkspace() {
  try {
    const settings = await window.aetherosDesktop?.settings?.getDefaultProjectDir?.()

    if (settings?.dir) {
      updateWorkspaceContext({ cwd: settings.dir })
    }
  } catch { /* ignore */ }
}
