import { atom, computed } from 'nanostores'

export interface Problem {
  id: string
  type: 'error' | 'warning' | 'info'
  message: string
  file: string
  line: number
  column: number
  source: string
  code: string
}

export interface ProblemsPanelState {
  problems: Problem[]
  selectedProblemId: string
  showErrors: boolean
  showWarnings: boolean
  showInfo: boolean
  filter: string
}

export const $problemsPanel = atom<ProblemsPanelState>({
  problems: [],
  selectedProblemId: '',
  showErrors: true,
  showWarnings: true,
  showInfo: false,
  filter: '',
})

export const $filteredProblems = computed($problemsPanel, (s) => {
  let p = s.problems

  if (!s.showErrors) {p = p.filter(x => x.type !== 'error')}

  if (!s.showWarnings) {p = p.filter(x => x.type !== 'warning')}

  if (!s.showInfo) {p = p.filter(x => x.type !== 'info')}

  if (s.filter) {
    const f = s.filter.toLowerCase()
    p = p.filter(x => x.message.toLowerCase().includes(f) || x.file.toLowerCase().includes(f))
  }

  return p
})

export const $problemSummary = computed($problemsPanel, (s) => ({
  errors: s.problems.filter(x => x.type === 'error').length,
  warnings: s.problems.filter(x => x.type === 'warning').length,
  info: s.problems.filter(x => x.type === 'info').length,
}))

export function setProblems(problems: Problem[]) {
  const state = $problemsPanel.get()
  $problemsPanel.set({ ...state, problems })
}

export function addProblem(problem: Problem) {
  const state = $problemsPanel.get()
  $problemsPanel.set({ ...state, problems: [...state.problems, problem] })
}

export function clearProblems() {
  const state = $problemsPanel.get()
  $problemsPanel.set({ ...state, problems: [], selectedProblemId: '' })
}

export function selectProblem(problemId: string) {
  const state = $problemsPanel.get()
  $problemsPanel.set({ ...state, selectedProblemId: problemId })
}

export function setProblemFilter(filter: string) {
  const state = $problemsPanel.get()
  $problemsPanel.set({ ...state, filter })
}

export function toggleProblemType(type: 'error' | 'warning' | 'info') {
  const state = $problemsPanel.get()

  if (type === 'error') {$problemsPanel.set({ ...state, showErrors: !state.showErrors })}
  else if (type === 'warning') {$problemsPanel.set({ ...state, showWarnings: !state.showWarnings })}
  else if (type === 'info') {$problemsPanel.set({ ...state, showInfo: !state.showInfo })}
}
