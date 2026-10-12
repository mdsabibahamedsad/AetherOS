import { describe, expect, it } from 'vitest'

import { APP_ROUTES } from '@/app/routes'

import { NAV_GROUP_META, NAV_SECTIONS } from './navigation'

describe('sidebar navigation groups (progressive disclosure)', () => {
  it('every section belongs to a known group', () => {
    const groupIds = new Set(NAV_GROUP_META.map(g => g.id))

    for (const section of NAV_SECTIONS) {
      expect(groupIds.has(section.group), `${section.id} has unknown group`).toBe(true)

      for (const child of section.children ?? []) {
        expect(child.group, `${child.id} group must match parent`).toBe(section.group)
      }
    }
  })

  it('every section route resolves to a registered route (no dead destinations)', () => {
    const paths: Set<string> = new Set(APP_ROUTES.map(r => r.path))

    for (const section of NAV_SECTIONS) {
      expect(paths.has(section.route), `${section.id} -> ${section.route} is not registered`).toBe(true)

      for (const child of section.children ?? []) {
        expect(paths.has(child.route), `${child.id} -> ${child.route} is not registered`).toBe(true)
      }
    }
  })

  it('section and child ids are unique', () => {
    const ids = NAV_SECTIONS.flatMap(s => [s.id, ...(s.children ?? []).map(c => c.id)])
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('all four disclosure groups are populated', () => {
    for (const group of NAV_GROUP_META) {
      const count = NAV_SECTIONS.filter(s => s.group === group.id).length
      expect(count, `group ${group.id} is empty`).toBeGreaterThan(0)
    }
  })
})
