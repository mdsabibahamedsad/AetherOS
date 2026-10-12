import { atom, computed } from 'nanostores'

export interface TestResult {
  id: string
  name: string
  file: string
  suite: string
  status: 'passed' | 'failed' | 'skipped' | 'running' | 'pending'
  duration: number
  errorMessage: string
  stackTrace: string
  output: string
}

export interface TestSuite {
  id: string
  name: string
  file: string
  framework: string
  status: 'passed' | 'failed' | 'running' | 'pending'
  total: number
  passed: number
  failed: number
  skipped: number
  duration: number
  tests: TestResult[]
  expanded: boolean
}

export interface TestRunnerState {
  suites: TestSuite[]
  isRunning: boolean
  lastRun: number | null
  selectedSuiteId: string | null
  selectedTestId: string | null
  showOnlyFailed: boolean
  coverageAvailable: boolean
  coverage: { lines: number; branches: number; functions: number; statements: number } | null
}

export const $testRunner = atom<TestRunnerState>({
  suites: [],
  isRunning: false,
  lastRun: null,
  selectedSuiteId: null,
  selectedTestId: null,
  showOnlyFailed: false,
  coverageAvailable: false,
  coverage: null,
})

export const $testSummary = computed($testRunner, (s) => ({
  total: s.suites.reduce((a, su) => a + su.total, 0),
  passed: s.suites.reduce((a, su) => a + su.passed, 0),
  failed: s.suites.reduce((a, su) => a + su.failed, 0),
  skipped: s.suites.reduce((a, su) => a + su.skipped, 0),
}))

export const $filteredSuites = computed($testRunner, (s) => {
  if (s.showOnlyFailed) {
    return s.suites.map(su => ({ ...su, tests: su.tests.filter(t => t.status === 'failed'), expanded: true })).filter(su => su.failed > 0)
  }

  return s.suites
})

export function setTestSuites(suites: TestSuite[]) {
  const state = $testRunner.get()
  $testRunner.set({ ...state, suites })
}

export function setTestRunning(running: boolean) {
  const state = $testRunner.get()
  $testRunner.set({ ...state, isRunning: running, lastRun: running ? state.lastRun : Date.now() })
}

export function selectTestSuite(suiteId: string | null) {
  const state = $testRunner.get()
  $testRunner.set({ ...state, selectedSuiteId: suiteId })
}

export function selectTest(testId: string | null) {
  const state = $testRunner.get()
  $testRunner.set({ ...state, selectedTestId: testId })
}

export function toggleSuite(suiteId: string) {
  const state = $testRunner.get()
  const suites = state.suites.map(su => su.id === suiteId ? { ...su, expanded: !su.expanded } : su)
  $testRunner.set({ ...state, suites })
}

export function toggleShowOnlyFailed() {
  const state = $testRunner.get()
  $testRunner.set({ ...state, showOnlyFailed: !state.showOnlyFailed })
}

export function setCoverage(coverage: { lines: number; branches: number; functions: number; statements: number }) {
  const state = $testRunner.get()
  $testRunner.set({ ...state, coverage, coverageAvailable: true })
}

export function clearTestResults() {
  $testRunner.set({
    suites: [], isRunning: false, lastRun: null, selectedSuiteId: null, selectedTestId: null,
    showOnlyFailed: false, coverageAvailable: false, coverage: null,
  })
}
