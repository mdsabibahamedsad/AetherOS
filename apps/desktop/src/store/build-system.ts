import { atom, computed } from 'nanostores'

export interface BuildTask {
  id: string
  name: string
  command: string
  type: string
  manager: string
}

export interface BuildResult {
  id: string
  taskName: string
  status: 'running' | 'completed' | 'failed' | 'timeout'
  output: string
  error: string
  exitCode: number | null
  startedAt: number
  completedAt: number
  duration: number
}

export interface BuildSystemState {
  tasks: BuildTask[]
  currentBuild: BuildResult | null
  buildHistory: BuildResult[]
  isRunning: boolean
  autoDetect: boolean
  selectedTaskId: string
}

export const $buildSystem = atom<BuildSystemState>({
  tasks: [],
  currentBuild: null,
  buildHistory: [],
  isRunning: false,
  autoDetect: true,
  selectedTaskId: '',
})

export const $buildTasks = computed($buildSystem, (s) => s.tasks)
export const $buildStatus = computed($buildSystem, (s) => s.currentBuild?.status ?? 'idle')

export function setBuildTasks(tasks: BuildTask[]) {
  const state = $buildSystem.get()
  $buildSystem.set({ ...state, tasks })
}

export function setCurrentBuild(build: BuildResult | null) {
  const state = $buildSystem.get()
  $buildSystem.set({
    ...state, currentBuild: build, isRunning: build?.status === 'running',
    buildHistory: build ? [build, ...state.buildHistory].slice(0, 50) : state.buildHistory,
  })
}

export function updateBuildOutput(output: string) {
  const state = $buildSystem.get()

  if (state.currentBuild) {
    $buildSystem.set({ ...state, currentBuild: { ...state.currentBuild, output: state.currentBuild.output + output } })
  }
}

export function selectBuildTask(taskId: string) {
  const state = $buildSystem.get()
  $buildSystem.set({ ...state, selectedTaskId: taskId })
}

export function setAutoDetect(auto: boolean) {
  const state = $buildSystem.get()
  $buildSystem.set({ ...state, autoDetect: auto })
}

export function clearBuildHistory() {
  const state = $buildSystem.get()
  $buildSystem.set({ ...state, buildHistory: [] })
}
