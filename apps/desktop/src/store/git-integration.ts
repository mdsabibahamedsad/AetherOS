import { atom, computed } from 'nanostores'

export interface GitChange {
  status: string
  file: string
}

export interface GitBranch {
  name: string
  current: boolean
  remote: boolean
}

export interface GitCommit {
  hash: string
  fullHash: string
  author: string
  email: string
  timestamp: number
  message: string
}

export interface GitIntegrationState {
  isRepo: boolean
  branch: string
  branches: GitBranch[]
  changes: GitChange[]
  stagedChanges: GitChange[]
  commits: GitCommit[]
  ahead: number
  behind: number
  stashes: Array<{ index: number; message: string }>
  isFetching: boolean
  commitMessage: string
  diffContent: string
  showDiff: boolean
  currentDiffFile: string
  mergeConflict: boolean
  mergeConflictFiles: string[]
}

export const $gitIntegration = atom<GitIntegrationState>({
  isRepo: false,
  branch: '',
  branches: [],
  changes: [],
  stagedChanges: [],
  commits: [],
  ahead: 0,
  behind: 0,
  stashes: [],
  isFetching: false,
  commitMessage: '',
  diffContent: '',
  showDiff: false,
  currentDiffFile: '',
  mergeConflict: false,
  mergeConflictFiles: [],
})

export const $gitBranch = computed($gitIntegration, (s) => s.branch)
export const $gitChanges = computed($gitIntegration, (s) => s.changes)
export const $gitUnstagedCount = computed($gitIntegration, (s) => s.changes.length)

export function setGitRepoStatus(status: { isRepo: boolean; branch: string; changes: GitChange[]; ahead: number; behind: number }) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, ...status, isFetching: false })
}

export function setGitBranches(branches: GitBranch[]) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, branches })
}

export function setGitCommits(commits: GitCommit[]) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, commits })
}

export function setCommitMessage(message: string) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, commitMessage: message })
}

export function setDiffContent(content: string, filePath: string) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, diffContent: content, showDiff: true, currentDiffFile: filePath })
}

export function closeDiff() {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, showDiff: false, diffContent: '', currentDiffFile: '' })
}

export function setGitFetching(fetching: boolean) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, isFetching: fetching })
}

export function setMergeConflict(files: string[]) {
  const state = $gitIntegration.get()
  $gitIntegration.set({ ...state, mergeConflict: files.length > 0, mergeConflictFiles: files })
}

export function commitChanges() {
  const state = $gitIntegration.get()

  if (!state.commitMessage.trim()) {return}
  $gitIntegration.set({ ...state, commitMessage: '', changes: [], stagedChanges: [] })
}

export function clearGitState() {
  $gitIntegration.set({
    isRepo: false, branch: '', branches: [], changes: [], stagedChanges: [], commits: [],
    ahead: 0, behind: 0, stashes: [], isFetching: false, commitMessage: '', diffContent: '',
    showDiff: false, currentDiffFile: '', mergeConflict: false, mergeConflictFiles: [],
  })
}
