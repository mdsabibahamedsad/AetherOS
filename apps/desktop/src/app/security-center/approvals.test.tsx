import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AetherosGateway } from '@/aetheros'
import { $gateway } from '@/store/gateway'
import { clearAllPrompts, setApprovalRequest } from '@/store/prompts'

import { ApprovalCenter } from './approvals'

function mockGateway() {
  const request = vi.fn().mockResolvedValue({ resolved: true })
  $gateway.set({ request } as unknown as AetherosGateway)

  return request
}

afterEach(() => {
  cleanup()
  clearAllPrompts()
  $gateway.set(null)
})

describe('ApprovalCenter (live gateway state)', () => {
  it('shows an honest empty state when nothing is pending', () => {
    mockGateway()
    render(<ApprovalCenter />)
    expect(screen.getByText('No pending approvals')).toBeTruthy()
  })

  it('shows gateway-disconnected instead of fake data when offline', () => {
    render(<ApprovalCenter />)
    expect(screen.getByText('Gateway disconnected')).toBeTruthy()
  })

  it('lists the real pending request with its command', () => {
    mockGateway()
    setApprovalRequest({ command: 'rm -rf /tmp/a', description: 'Clean scratch dir', sessionId: 'sess-9' })
    render(<ApprovalCenter />)
    expect(screen.getByText('Clean scratch dir')).toBeTruthy()
    expect(screen.getByText('rm -rf /tmp/a')).toBeTruthy()
  })

  it('Allow Once sends approval.respond and clears the request', async () => {
    const request = mockGateway()
    setApprovalRequest({ command: 'rm -rf /tmp/a', description: 'Clean scratch dir', sessionId: 'sess-9' })
    render(<ApprovalCenter />)
    fireEvent.click(screen.getByText('Clean scratch dir'))
    fireEvent.click(screen.getByRole('button', { name: /Allow Once/ }))
    await waitFor(() => {
      expect(request).toHaveBeenCalledWith('approval.respond', { choice: 'once', session_id: 'sess-9' })
    })
    await waitFor(() => {
      expect(screen.getByText('No pending approvals')).toBeTruthy()
    })
  })

  it('Deny blocks the action', async () => {
    const request = mockGateway()
    setApprovalRequest({ command: 'sudo reboot', description: 'Restart host', sessionId: 'sess-9' })
    render(<ApprovalCenter />)
    fireEvent.click(screen.getByText('Restart host'))
    fireEvent.click(screen.getByRole('button', { name: 'Deny' }))
    await waitFor(() => {
      expect(request).toHaveBeenCalledWith('approval.respond', { choice: 'deny', session_id: 'sess-9' })
    })
  })
})
