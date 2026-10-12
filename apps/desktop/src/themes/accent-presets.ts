export interface AccentPreset {
  name: string
  label: string
  color: string
  darkColor?: string
}

export const ACCENT_PRESETS: AccentPreset[] = [
  { name: 'blue', label: 'Blue', color: '#0053fd' },
  { name: 'indigo', label: 'Indigo', color: '#4f46e5' },
  { name: 'violet', label: 'Violet', color: '#7c3aed' },
  { name: 'purple', label: 'Purple', color: '#a855f7' },
  { name: 'pink', label: 'Pink', color: '#ec4899' },
  { name: 'rose', label: 'Rose', color: '#f43f5e' },
  { name: 'orange', label: 'Orange', color: '#f97316' },
  { name: 'amber', label: 'Amber', color: '#f59e0b' },
  { name: 'green', label: 'Green', color: '#10b981' },
  { name: 'emerald', label: 'Emerald', color: '#059669' },
  { name: 'teal', label: 'Teal', color: '#14b8a6' },
  { name: 'cyan', label: 'Cyan', color: '#06b6d4' },
  { name: 'slate', label: 'Slate', color: '#64748b' },
  { name: 'neutral', label: 'Neutral', color: '#737373' },
  { name: 'aether', label: 'AetherOS', color: '#6366f1', darkColor: '#818cf8' }
]
