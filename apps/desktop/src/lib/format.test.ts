import { describe, expect, it } from 'vitest'

import { formatBytes } from './format-bytes'
import { formatRelativeTime, formatTimestamp } from './format-timestamp'

describe('formatBytes', () => {
  it('formats bytes and kilobytes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(1536)).toContain('KB')
    expect(formatBytes(1536)).toContain('1.5')
    expect(formatBytes(5 * 1024 * 1024)).toContain('MB')
  })

  it('never fabricates values for missing input', () => {
    expect(formatBytes(null)).toBe('—')
    expect(formatBytes(undefined)).toBe('—')
    expect(formatBytes(Number.NaN)).toBe('—')
    expect(formatBytes(-1)).toBe('—')
  })
})

describe('formatTimestamp', () => {
  it('renders locale dates for epoch millis and ISO strings', () => {
    const out = formatTimestamp(1720000000000)
    expect(out).toContain('2024')
    expect(formatTimestamp(new Date(1720000000000).toISOString())).toContain('2024')
  })

  it('never fabricates values for missing input', () => {
    expect(formatTimestamp(null)).toBe('—')
    expect(formatTimestamp('not-a-date')).toBe('—')
  })

  it('relative time stays honest', () => {
    expect(formatRelativeTime(Date.now() - 60_000)).toMatch(/minute/)
    expect(formatRelativeTime(null)).toBe('—')
  })
})
