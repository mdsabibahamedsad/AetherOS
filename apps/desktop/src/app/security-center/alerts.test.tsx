import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AetherosGateway } from '@/aetheros'
import { $gateway } from '@/store/gateway'

import { SecurityAlertsView } from './alerts'

function bridge(lines: string[]) {
  Object.defineProperty(window, 'aetherosDesktop', {
    configurable: true,
    value: { getRecentLogs: vi.fn().mockResolvedValue({ path: '/tmp/backend.log', lines }) },
    writable: true,
  })
  $gateway.set({} as unknown as AetherosGateway)
}

afterEach(() => {
  cleanup()
  $gateway.set(null)
  // @ts-expect-error test cleanup
  delete window.aetherosDesktop
})

describe('SecurityAlertsView (log-derived signals)', () => {
  it('derives an alert from a real denial line with verbatim evidence', async () => {
    bridge(['2026-09-09 ERROR policy denied terminal.execute for agent-x'])
    render(<SecurityAlertsView />)
    await waitFor(() => {
      expect(screen.getByText('Blocked / denied action')).toBeTruthy()
    })
    expect(screen.getByText('2026-09-09 ERROR policy denied terminal.execute for agent-x')).toBeTruthy()
  })

  it('stays empty (honestly) when logs carry no security signals', async () => {
    bridge(['2026-09-09 INFO gateway up', '2026-09-09 INFO session saved'])
    render(<SecurityAlertsView />)
    await waitFor(() => {
      expect(screen.getByText('No security signals in recent backend output')).toBeTruthy()
    })
  })
})
