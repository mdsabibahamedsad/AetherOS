import { atom } from 'nanostores'

export interface QuickAction {
  id: string
  label: string
  icon: string
  shortcut?: string
  action: () => void
}

export const $quickActions = atom<QuickAction[]>([])
export const $searchQuery = atom('')
export const $commandPaletteOpen = atom(false)

export function registerQuickAction(action: QuickAction) {
  const current = $quickActions.get()

  if (!current.some(a => a.id === action.id)) {
    $quickActions.set([...current, action])
  }
}

export function unregisterQuickAction(id: string) {
  $quickActions.set($quickActions.get().filter(a => a.id !== id))
}

export function setSearchQuery(query: string) {
  $searchQuery.set(query)
}

export function toggleCommandPalette() {
  $commandPaletteOpen.set(!$commandPaletteOpen.get())
}
