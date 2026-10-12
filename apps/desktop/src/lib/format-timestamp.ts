// Locale-aware timestamp formatting (i18n-ready: honors the runtime locale,
// never hardcodes date order). Accepts epoch ms, ISO strings, or Dates.
export function formatTimestamp(value: number | string | Date | null | undefined): string {
  if (value === null || value === undefined || value === '') {return '—'}
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {return '—'}

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function formatRelativeTime(value: number | string | Date | null | undefined): string {
  if (value === null || value === undefined || value === '') {return '—'}
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {return '—'}
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)

  const divisions: Array<[number, Intl.RelativeTimeFormatUnit]> = [
    [60, 'minutes'],
    [60, 'hours'],
    [24, 'days'],
    [7, 'weeks'],
    [4.345, 'months'],
    [12, 'years'],
    [Number.POSITIVE_INFINITY, 'years'],
  ]

  let duration = seconds
  let unit: Intl.RelativeTimeFormatUnit = 'seconds'

  for (const [amount, next] of divisions) {
    if (Math.abs(duration) < amount) {break}
    duration /= amount
    unit = next
  }

  return new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(Math.round(duration), unit)
}
