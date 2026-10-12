import { atom, computed } from 'nanostores'

export interface ManagedProcess {
  id: string
  name: string
  command: string
  cwd: string
  pid: number | null
  status: 'running' | 'stopped' | 'exited' | 'failed'
  startedAt: number
  cpu: number
  memory: number
  outputLines: number
  sandboxKey: string
}

export interface ProcessManagerState {
  processes: ManagedProcess[]
  selectedProcessId: string
  maxProcesses: number
}

export const $processManager = atom<ProcessManagerState>({
  processes: [],
  selectedProcessId: '',
  maxProcesses: 50,
})

export const $runningProcesses = computed($processManager, (s) => s.processes.filter(p => p.status === 'running'))
export const $selectedProcess = computed($processManager, (s) => s.processes.find(p => p.id === s.selectedProcessId) ?? null)

export function setProcesses(processes: ManagedProcess[]) {
  const state = $processManager.get()
  $processManager.set({ ...state, processes })
}

export function addProcess(process: ManagedProcess) {
  const state = $processManager.get()
  $processManager.set({ ...state, processes: [...state.processes, process] })
}

export function updateProcessStatus(processId: string, status: ManagedProcess['status']) {
  const state = $processManager.get()
  const processes = state.processes.map(p => p.id === processId ? { ...p, status } : p)
  $processManager.set({ ...state, processes })
}

export function removeProcess(processId: string) {
  const state = $processManager.get()
  $processManager.set({
    ...state,
    processes: state.processes.filter(p => p.id !== processId),
    selectedProcessId: state.selectedProcessId === processId ? '' : state.selectedProcessId,
  })
}

export function selectProcess(processId: string) {
  const state = $processManager.get()
  $processManager.set({ ...state, selectedProcessId: processId })
}

export function clearCompletedProcesses() {
  const state = $processManager.get()
  $processManager.set({ ...state, processes: state.processes.filter(p => p.status === 'running') })
}
