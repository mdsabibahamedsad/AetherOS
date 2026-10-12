import { atom } from 'nanostores'

export const $activityDrawerOpen = atom(false)

export function openActivityDrawer(): void {
  $activityDrawerOpen.set(true)
}

export function closeActivityDrawer(): void {
  $activityDrawerOpen.set(false)
}

export function toggleActivityDrawer(): void {
  $activityDrawerOpen.set(!$activityDrawerOpen.get())
}

export function setActivityDrawerOpen(open: boolean): void {
  $activityDrawerOpen.set(open)
}