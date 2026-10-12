// Locale-aware byte formatting (1024-based, one decimal, no trailing zeros).
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) {return '—'}

  if (bytes < 0) {return '—'}

  if (bytes < 1024) {return `${bytes} B`}
  const units = ['KB', 'MB', 'GB', 'TB', 'PB']
  let value = bytes / 1024
  let unit = units[0]

  for (const next of units) {
    unit = next

    if (value < 1024 || next === 'PB') {break}
    value /= 1024
  }

  const rounded = Math.round(value * 10) / 10

  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(rounded)} ${unit}`
}
