import { atom, computed } from 'nanostores'

export interface DependencyInfo {
  name: string
  version: string
  type: 'production' | 'development'
}

export interface PackageManagerInfo {
  name: string
  files: string[]
  dependencies?: number
  packageCount?: number
}

export interface DependencyManagerState {
  managers: PackageManagerInfo[]
  dependencies: DependencyInfo[]
  auditResults: string
  isInstalling: boolean
  selectedManager: string
  installError: string | null
}

export const $dependencyManager = atom<DependencyManagerState>({
  managers: [],
  dependencies: [],
  auditResults: '',
  isInstalling: false,
  selectedManager: '',
  installError: null,
})

export const $selectedManagerData = computed($dependencyManager, (s) => s.managers.find(m => m.name === s.selectedManager) ?? null)

export function setPackageManagers(managers: PackageManagerInfo[]) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, managers, selectedManager: managers[0]?.name ?? '' })
}

export function setDependencies(deps: DependencyInfo[]) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, dependencies: deps })
}

export function setSelectedManager(manager: string) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, selectedManager: manager })
}

export function setInstalling(installing: boolean) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, isInstalling: installing })
}

export function setInstallError(error: string | null) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, installError: error })
}

export function setAuditResults(results: string) {
  const state = $dependencyManager.get()
  $dependencyManager.set({ ...state, auditResults: results })
}
