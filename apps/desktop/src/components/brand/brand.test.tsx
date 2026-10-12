import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { BRAND_LOGO_RULES } from '@/lib/brand'

import { BrandLockup } from './brand-lockup'
import { WOLF_CUTOUT_PATHS, WOLF_FUR_PATH, WOLF_VIEWBOX, WolfMark } from './wolf-mark'

describe('WolfMark master', () => {
  it('exposes one stable geometry for every configuration', () => {
    expect(WOLF_VIEWBOX).toBe('0 0 32 32')
    expect(WOLF_FUR_PATH).toContain('M16 0')
    expect(WOLF_CUTOUT_PATHS).toHaveLength(3)
  })

  it('renders the brand colorway as an image with unique gradient ids', () => {
    const { container } = render(
      <>
        <WolfMark />
        <WolfMark />
      </>
    )

    const svgs = container.querySelectorAll('svg[role="img"]')
    expect(svgs).toHaveLength(2)
    const ids = [...container.querySelectorAll('linearGradient')].map(g => g.getAttribute('id'))
    expect(new Set(ids).size).toBe(ids.length)
    expect(screen.getAllByRole('img', { name: 'AetherOS wolf' })).toHaveLength(2)
  })

  it('renders mono as a single currentColor silhouette', () => {
    const { container } = render(<WolfMark colorway="mono" />)
    expect(container.querySelector('linearGradient')).toBeNull()
    expect(container.querySelector('path')?.getAttribute('fill')).toBe('currentColor')
  })
})

describe('BrandLockup', () => {
  it('builds every official configuration from the master', () => {
    const { rerender } = render(<BrandLockup layout="mark-only" size={16} />)
    expect(document.querySelector('svg[role="img"]')).toBeTruthy()

    rerender(<BrandLockup layout="horizontal" size={32} />)
    expect(screen.getByText('AetherOS')).toBeTruthy()

    rerender(<BrandLockup layout="stacked" size={64} tagline />)
    expect(screen.getByText('AI Operating System')).toBeTruthy()
  })

  it('mono lockups inherit text color (white/black configs via CSS)', () => {
    const { container } = render(
      <BrandLockup className="text-white" colorway="mono" layout="mark-only" size={24} />
    )

    expect(container.querySelector('path')?.getAttribute('fill')).toBe('currentColor')
  })

  it('honors the minimum-size rule', () => {
    expect(BRAND_LOGO_RULES.minSizePx).toBe(16)
    const { container } = render(<BrandLockup layout="mark-only" size={BRAND_LOGO_RULES.minSizePx} />)
    const tile = container.querySelector('span > span') as HTMLElement | null
    expect(tile?.style.width).toBe('16px')
  })
})
