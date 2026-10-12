import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { AgiActivityList } from './agi-activity'

afterEach(() => cleanup())

describe('AgiActivityList', () => {
  it('renders every state with an accessible label, no chain-of-thought', () => {
    render(
      <AgiActivityList
        rows={[
          { id: 'a', state: 'done', label: 'Analyzed project' },
          { id: 'b', state: 'done', label: 'Located relevant files', detail: '12 files' },
          { id: 'c', state: 'active', label: 'Preparing changes' },
          { id: 'd', state: 'pending', label: 'Validation' },
        ]}
        subtitle="Working on your request"
        title="AetherOS"
      />
    )

    expect(screen.getByText('AetherOS')).toBeTruthy()
    expect(screen.getByText('Working on your request')).toBeTruthy()
    expect(screen.getByText('Analyzed project')).toBeTruthy()
    expect(screen.getByText(/12 files/)).toBeTruthy()
    expect(screen.getAllByRole('img').map(e => e.getAttribute('aria-label'))).toEqual([
      'done',
      'done',
      'active',
      'pending',
    ])
  })

  it('renders failure distinctly', () => {
    render(
      <AgiActivityList
        rows={[{ id: 'x', state: 'failed', label: 'Build failed', detail: 'exit 1' }]}
        title="AetherOS"
      />
    )

    expect(screen.getByRole('img').getAttribute('aria-label')).toBe('failed')
    expect(screen.getByText(/exit 1/)).toBeTruthy()
  })
})
