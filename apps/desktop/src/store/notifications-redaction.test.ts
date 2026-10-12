import { afterEach, describe, expect, it } from 'vitest'

import { $notifications, clearNotifications, notifyError } from './notifications'

afterEach(() => clearNotifications())

describe('notifyError secret handling (red-team)', () => {
  it('masks credentials in both message and detail', () => {
    notifyError(new Error('Provider rejected request: api_key=sk-abcdefghij1234567890'), 'Request failed')

    const [latest] = $notifications.get()
    expect(latest).toBeDefined()
    expect(`${latest?.message} ${latest?.detail ?? ''}`).not.toContain('sk-abcdefghij1234567890')
    expect(latest?.message).toContain('[redacted]')
  })

  it('leaves benign errors fully readable', () => {
    notifyError(new Error('file not found: /workspace/aetheros/src/index.ts'), 'Read failed')

    const [latest] = $notifications.get()
    expect(latest?.message).toContain('/workspace/aetheros/src/index.ts')
  })

  it('masks JWT-shaped tokens from gateway failures', () => {
    notifyError(
      'auth failed for eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_X7yA',
      'Auth failed',
    )

    const [latest] = $notifications.get()
    expect(`${latest?.message} ${latest?.detail ?? ''}`).not.toContain('eyJhbGciOi')
  })
})
