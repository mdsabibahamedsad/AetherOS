/**
 * Extension SDK store — scaffolding, building, validation, and dev-mode toggles.
 */
import { atom } from 'nanostores'

export type ExtensionType = 'plugin' | 'tool' | 'mcpServer' | 'skill' | 'provider' | 'hook'

export interface ExtensionTemplate {
  id: string
  name: string
  description: string
  type: ExtensionType
  icon: string
}

export interface ExtensionManifest {
  name: string
  version: string
  description: string
  author: string
  license: string
  type: ExtensionType
  entry: string
  dependencies: Record<string, string>
}

export interface ExtensionProject {
  path: string
  name: string
  type: ExtensionType
  manifest: ExtensionManifest
  devMode: boolean
  hotReload: boolean
}

export interface BuildResult {
  success: boolean
  path: string
  size: number
  errors: string[]
  warnings: string[]
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  hints: string[]
}

export interface WizardConfig {
  templateId: string | null
  name: string
  description: string
  author: string
  type: ExtensionType
  targetDir: string
}

export const $templates = atom<ExtensionTemplate[]>([])
export const $projects = atom<ExtensionProject[]>([])
export const $activeProject = atom<ExtensionProject | null>(null)
export const $buildResults = atom<BuildResult[]>([])
export const $validationResults = atom<ValidationResult[]>([])
export const $devMode = atom<boolean>(false)
export const $hotReload = atom<boolean>(false)
export const $sdkLoading = atom<boolean>(false)
export const $wizardStep = atom<number>(0)
export const $wizardConfig = atom<WizardConfig>({
  templateId: null,
  name: '',
  description: '',
  author: '',
  type: 'plugin',
  targetDir: ''
})

export function scaffoldProject(project: ExtensionProject) {
  const existing = $projects.get().find(p => p.path === project.path)

  if (existing) {return}
  $projects.set([...$projects.get(), project])
}

export function buildProject(result: BuildResult) {
  $buildResults.set([...$buildResults.get(), result].slice(-50))
}

export function validateProject(result: ValidationResult) {
  $validationResults.set([...$validationResults.get(), result].slice(-50))
}

export function enableDevMode() {
  $devMode.set(true)
  const active = $activeProject.get()

  if (active) {
    $activeProject.set({ ...active, devMode: true })
  }
}

export function disableDevMode() {
  $devMode.set(false)
  const active = $activeProject.get()

  if (active) {
    $activeProject.set({ ...active, devMode: false })
  }
}

export function toggleHotReload() {
  const next = !$hotReload.get()
  $hotReload.set(next)
  const active = $activeProject.get()

  if (active) {
    $activeProject.set({ ...active, hotReload: next })
  }
}

export function runTests(results: BuildResult) {
  $buildResults.set([...$buildResults.get(), results])
}

export function generateDocs(result: BuildResult) {
  $buildResults.set([...$buildResults.get(), result])
}

export function setActiveProject(project: ExtensionProject | null) {
  $activeProject.set(project)

  if (project) {
    $devMode.set(project.devMode)
    $hotReload.set(project.hotReload)
  }
}

export function setWizardStep(step: number) {
  $wizardStep.set(step)
}

export function setWizardConfig(config: Partial<WizardConfig>) {
  $wizardConfig.set({ ...$wizardConfig.get(), ...config })
}

export function resetWizard() {
  $wizardStep.set(0)
  $wizardConfig.set({
    templateId: null,
    name: '',
    description: '',
    author: '',
    type: 'plugin',
    targetDir: ''
  })
}

export function setTemplates(templates: ExtensionTemplate[]) {
  $templates.set(templates)
}

export function setProjects(projects: ExtensionProject[]) {
  $projects.set(projects)
}

export function clearBuildResults() {
  $buildResults.set([])
}

export function clearValidationResults() {
  $validationResults.set([])
}
