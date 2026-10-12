import { describe, expect, it } from 'vitest'

import { APP_ROUTES } from '@/app/routes'
import { BRAND_TAGLINE, BRAND_WORDMARK } from '@/lib/brand'

import { QUICK_ACTIONS } from './index'

describe('home quick actions (every card must work)', () => {
  it('renders the single canonical brand wordmark (no duplicated branding)', () => {
    expect(BRAND_WORDMARK).toBe('AetherOS')
    expect(BRAND_WORDMARK).not.toContain('AetherOSAetherOS')
    expect(BRAND_TAGLINE.length).toBeGreaterThan(0)
  })

  it('every quick action routes to a registered route', () => {
    expect(QUICK_ACTIONS.length).toBeGreaterThan(0)
    const paths: Set<string> = new Set(APP_ROUTES.map(r => r.path))

    for (const action of QUICK_ACTIONS) {
      expect(action.title.length, `${action.id} needs a title`).toBeGreaterThan(0)
      expect(action.description.length, `${action.id} needs a description`).toBeGreaterThan(0)
      expect(paths.has(action.route), `${action.id} -> ${action.route} is not registered`).toBe(true)
    }
  })

  it('quick action ids are unique', () => {
    const ids = QUICK_ACTIONS.map(a => a.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})
