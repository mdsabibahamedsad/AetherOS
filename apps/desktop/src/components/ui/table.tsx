import type { ComponentProps } from 'react'

import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// Canonical data table primitives. `Table loading` renders skeleton rows so
// loading is explicit structure (never a bare spinner, never fake rows).
export function Table({ children, className, loading: _loading, ...props }: ComponentProps<'table'> & { loading?: boolean }) {
  // `loading` is accepted so callers can branch on it (e.g. render
  // <TableSkeletonRows />); it is intentionally not forwarded to the DOM.
  void _loading

  return (
    <table className={cn('w-full text-sm', className)} {...props}>
      {children}
    </table>
  )
}

export function TableHead({ children, className, ...props }: ComponentProps<'thead'>) {
  return (
    <thead className={cn('[&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium [&_th]:uppercase [&_th]:tracking-wider [&_th]:text-muted-foreground', className)} {...props}>
      {children}
    </thead>
  )
}

export function TableBody({ children, className, ...props }: ComponentProps<'tbody'>) {
  return (
    <tbody className={cn('[&_td]:border-t [&_td]:border-(--ui-stroke-tertiary) [&_td]:px-3 [&_td]:py-2', className)} {...props}>
      {children}
    </tbody>
  )
}

export function TableRow({ children, className, ...props }: ComponentProps<'tr'>) {
  return (
    <tr className={className} {...props}>
      {children}
    </tr>
  )
}

export function TableHeader({ children, className, ...props }: ComponentProps<'th'>) {
  return (
    <th className={className} scope="col" {...props}>
      {children}
    </th>
  )
}

export function TableCell({ children, className, ...props }: ComponentProps<'td'>) {
  return (
    <td className={className} {...props}>
      {children}
    </td>
  )
}

export function TableSkeletonRows({ columns = 3, rows = 5 }: { columns?: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <TableRow key={r}>
          {Array.from({ length: columns }).map((_, c) => (
            <TableCell key={c}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
