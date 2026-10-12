import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AuditLogView } from './audit'

function bridge(lines: string[] | null) {
  Object.defineProperty(window, 'aetherosDesktop', {
    configurable: true,
    value: {
      getRecentLogs: lines === null ? vi.fn().mockRejectedValue(new Error('down')) : vi.fn().mockResolvedValue({ path: '/tmp/backend.log', lines }),
      revealLogs: vi.fn(),
    },
    writable: true,
  })
}

afterEach(() => {
  cleanup()
  // @ts-expect-error test cleanup
  delete window.aetherosDesktop
})

describe('AuditLogView (real backend logs)', () => {
  it('renders verbatim log lines with their source', async () => {
    bridge(['2026-09-09 INFO gateway up', '2026-09-09 WARN slow tool'])
    render(<AuditLogView />)
    await waitFor(() => {
      expect(screen.getByText('2026-09-09 INFO gateway up')).toBeTruthy()
    })
  })

  it('filters lines by search without inventing entries', async () => {
    bridge(['alpha event here', 'beta event here'])
    render(<AuditLogView />)
    await waitFor(() => {
      expect(screen.getByText('alpha event here')).toBeTruthy()
    })
    fireEvent.change(screen.getByPlaceholderText('Filter log lines...'), { target: { value: 'beta' } })
    expect(screen.queryByText('alpha event here')).toBeNull()
    expect(screen.getByText('beta event here')).toBeTruthy()
  })

  it('reports unavailability honestly when the stream cannot be read', async () => {
    bridge(null)
    render(<AuditLogView />)
    await waitFor(() => {
      expect(screen.getByText('Logs unavailable')).toBeTruthy()
    })
  })
})
