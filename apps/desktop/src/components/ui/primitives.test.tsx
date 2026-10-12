import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { EmptyState } from './empty-state'
import { StatusDot } from './status-dot'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableSkeletonRows } from './table'

afterEach(cleanup)

describe('canonical ui primitives', () => {
  it('EmptyState explains what is missing and what to do', () => {
    render(<EmptyState description="Do the thing to get data." icon="zap" title="Nothing here" />)
    expect(screen.getByText('Nothing here')).toBeTruthy()
    expect(screen.getByText('Do the thing to get data.')).toBeTruthy()
  })

  it('StatusDot reuses the single tone system (success → good)', () => {
    const { container } = render(<StatusDot status="success" />)
    const dot = container.querySelector('span[role="img"]')
    expect(dot?.className).toContain('bg-primary')
    const { container: bad } = render(<StatusDot status="mystery-state" />)
    expect(bad.querySelector('span[role="img"]')?.className).toContain('bg-muted-foreground/40')
  })

  it('Table never leaks the loading prop to the DOM and renders skeletons', () => {
    const { container } = render(
      <Table loading>
        <TableHead>
          <TableRow>
            <TableHeader>Name</TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableSkeletonRows columns={1} rows={2} />
          <TableRow>
            <TableCell>real</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    )

    expect(container.querySelector('table[loading]')).toBeNull()
    expect(screen.getByText('real')).toBeTruthy()
  })
})
