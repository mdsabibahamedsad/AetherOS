import { describe, expect, it } from 'vitest'

import { APP_ROUTES, routeSessionId } from '@/app/routes'

import { NAV_SECTIONS, type NavSection } from './navigation'

// Sidebar/topbar navigation must never point at an unregistered path:
// routeSessionId() swallows unknown single-segment paths as session ids,
// so a wrong route silently opens a bogus session instead of a screen.
describe('navigation routes', () => {
  const registered: Set<string> = new Set(APP_ROUTES.map(r => r.path))

  const flatten = (sections: NavSection[]): NavSection[] =>
    sections.flatMap(s => [s, ...flatten(s.children ?? [])])

  it('every nav route resolves to a registered route or the chat root', () => {
    for (const section of flatten(NAV_SECTIONS)) {
      const ok = section.route === '/' || registered.has(section.route)
      expect(ok, `${section.id} -> ${section.route} is not a registered route`).toBe(true)
    }
  })

  it('no nav route is captured as a session id', () => {
    for (const section of flatten(NAV_SECTIONS)) {
      if (section.route === '/') {
        continue
      }

      expect(routeSessionId(section.route), `${section.route} would open a bogus session`).toBeNull()
    }
  })

  it('home and chat land on distinct real destinations', () => {
    const byId = new Map(flatten(NAV_SECTIONS).map(s => [s.id, s.route]))
    expect(byId.get('home')).toBe('/home')
    expect(byId.get('chat')).toBe('/')
  })
})
