import { atom, computed } from 'nanostores'

export interface ReviewFinding {
  ruleId: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  message: string
  file: string
  line: number
  match: string
}

export interface CodeReviewState {
  findings: ReviewFinding[]
  totalFiles: number
  totalFindings: number
  stats: { critical: number; high: number; medium: number; low: number; info: number }
  isReviewing: boolean
  selectedCategory: string
  selectedSeverity: string
  showOnlySelected: boolean
  sortBy: 'severity' | 'file' | 'category' | 'line'
}

export const $codeReview = atom<CodeReviewState>({
  findings: [],
  totalFiles: 0,
  totalFindings: 0,
  stats: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
  isReviewing: false,
  selectedCategory: '',
  selectedSeverity: '',
  showOnlySelected: false,
  sortBy: 'severity',
})

export const $filteredFindings = computed($codeReview, (s) => {
  let f = s.findings

  if (s.selectedSeverity) {f = f.filter(x => x.severity === s.selectedSeverity)}

  if (s.selectedCategory) {f = f.filter(x => x.category === s.selectedCategory)}

  if (s.sortBy === 'severity') {
    const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    f = [...f].sort((a, b) => order[a.severity] - order[b.severity])
  } else if (s.sortBy === 'file') {
    f = [...f].sort((a, b) => a.file.localeCompare(b.file))
  } else if (s.sortBy === 'category') {
    f = [...f].sort((a, b) => a.category.localeCompare(b.category))
  }

  return f
})

export function setFindings(findings: ReviewFinding[], totalFiles: number) {
  const state = $codeReview.get()
  const stats = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }

  for (const f of findings) {
    if (stats[f.severity] !== undefined) {stats[f.severity]++}
  }

  $codeReview.set({ ...state, findings, totalFiles, totalFindings: findings.length, stats, isReviewing: false })
}

export function setReviewing(reviewing: boolean) {
  const state = $codeReview.get()
  $codeReview.set({ ...state, isReviewing: reviewing })
}

export function setSelectedCategory(category: string) {
  const state = $codeReview.get()
  $codeReview.set({ ...state, selectedCategory: category })
}

export function setSelectedSeverity(severity: string) {
  const state = $codeReview.get()
  $codeReview.set({ ...state, selectedSeverity: severity })
}

export function setSortBy(sortBy: CodeReviewState['sortBy']) {
  const state = $codeReview.get()
  $codeReview.set({ ...state, sortBy })
}

export function clearReview() {
  $codeReview.set({
    findings: [], totalFiles: 0, totalFindings: 0,
    stats: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
    isReviewing: false, selectedCategory: '', selectedSeverity: '',
    showOnlySelected: false, sortBy: 'severity',
  })
}
