import { describe, expect, it } from 'vitest'

import { APP_ROUTES } from '@/app/routes'

import { CANONICAL_NAV, canonicalNavEntry, primaryNavEntries } from './canonical'

describe('canonical navigation registry', () => {
  it('every entry points at a real registered route (no dead destinations)', () => {
    const paths: Set<string> = new Set(APP_ROUTES.map(r => r.path))

    // '/' doubles as new-chat/session route; both are live views.
    for (const group of CANONICAL_NAV) {
      for (const entry of group.entries) {
        expect(paths.has(entry.path), `${entry.id} -> ${entry.path} is not a registered route`).toBe(true)
      }
    }
  })

  it('entry ids are unique and agent-readable (stable kebab-case)', () => {
    const ids = CANONICAL_NAV.flatMap(g => g.entries.map(e => e.id))
    expect(new Set(ids).size).toBe(ids.length)

    for (const id of ids) {
      expect(id).toMatch(/^[a-z0-9-]+$/)
    }
  })

  it('primary surface stays small (progressive disclosure)', () => {
    // Primary nav must not expose every internal subsystem.
    expect(primaryNavEntries().length).toBeLessThanOrEqual(12)
    expect(primaryNavEntries().length).toBeGreaterThan(0)
  })

  it('canonicalNavEntry resolves known ids and null otherwise', () => {
    expect(canonicalNavEntry('home')?.path).toBe('/home')
    expect(canonicalNavEntry('security')?.path).toBe('/security')
    expect(canonicalNavEntry('nope')).toBeNull()
  })
})
