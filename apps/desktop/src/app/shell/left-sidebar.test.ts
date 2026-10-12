import { describe, expect, it } from 'vitest'

import { navIdForPathname } from './left-sidebar'

// The sidebar highlight must follow the real route — refresh, deep links,
// back/forward — not just the last clicked item (Master 58361 F-2).
describe('navIdForPathname', () => {
  it('maps exact nav routes to their sections', () => {
    expect(navIdForPathname('/home')).toBe('home')
    expect(navIdForPathname('/')).toBe('chat')
    expect(navIdForPathname('/jarvis')).toBe('jarvis-mode')
    expect(navIdForPathname('/projects')).toBe('projects')
    expect(navIdForPathname('/models')).toBe('models')
    expect(navIdForPathname('/files')).toBe('files')
    expect(navIdForPathname('/tasks')).toBe('tasks')
    expect(navIdForPathname('/security')).toBe('security')
    expect(navIdForPathname('/settings')).toBe('settings')
  })

  it('maps session routes to chat (they are not nav destinations)', () => {
    expect(navIdForPathname('/abc123')).toBe('chat')
    expect(navIdForPathname('/some-session-id')).toBe('chat')
  })

  it('maps non-nav views to their closest section', () => {
    expect(navIdForPathname('/task-orchestrator')).toBe('task-orchestrator')
    expect(navIdForPathname('/mcp-manager')).toBe('mcp')
    expect(navIdForPathname('/diagnostics')).toBe('diagnostics')
    expect(navIdForPathname('/communications')).toBe('communications')
  })

  it('returns null for overlay views with no sidebar entry', () => {
    expect(navIdForPathname('/command-center')).toBeNull()
    expect(navIdForPathname('/cron')).toBeNull()
    expect(navIdForPathname('/profiles')).toBeNull()
  })

  it('keeps overlay views that do have a sidebar entry highlighted', () => {
    expect(navIdForPathname('/agents')).toBe('agents')
    expect(navIdForPathname('/settings')).toBe('settings')
  })
})
