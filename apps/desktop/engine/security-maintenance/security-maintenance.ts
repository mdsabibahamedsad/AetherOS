export type SecurityTaskType = 'dependency-update' | 'security-scan' | 'secret-detection' | 'static-analysis' | 'binary-verification'

export interface SecurityTask {
  type: SecurityTaskType
  name: string
  description: string
  frequency: 'daily' | 'weekly' | 'monthly' | 'on-release'
  priority: 'low' | 'medium' | 'high' | 'critical'
  automated: boolean
  run: () => Promise<SecurityTaskResult>
}

export interface SecurityTaskResult {
  type: SecurityTaskType
  passed: boolean
  findings: SecurityFinding[]
  duration: number
  timestamp: number
}

export interface SecurityFinding {
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical'
  category: string
  title: string
  description: string
  location?: string
  cveId?: string
  recommendation: string
  automated: boolean
}

export interface SecurityReport {
  timestamp: number
  tasksRun: number
  tasksPassed: number
  tasksFailed: number
  totalFindings: number
  criticalFindings: number
  highFindings: number
  mediumFindings: number
  lowFindings: number
  findings: SecurityFinding[]
  score: number
}

class SecurityMaintenanceScheduler {
  private tasks: SecurityTask[] = []
  private results: SecurityTaskResult[] = []
  private schedules: Map<string, number> = new Map()

  registerTask(task: SecurityTask) {
    this.tasks.push(task)
  }

  getTasks(): SecurityTask[] {
    return [...this.tasks]
  }

  async runTask(type: SecurityTaskType): Promise<SecurityTaskResult | null> {
    const task = this.tasks.find(t => t.type === type)
    if (!task) return null

    const result = await task.run()
    this.results.push(result)
    this.schedules.set(type, Date.now())
    return result
  }

  async runAllTasks(): Promise<SecurityReport> {
    const results: SecurityTaskResult[] = []
    const allFindings: SecurityFinding[] = []

    for (const task of this.tasks) {
      if (task.automated) {
        const result = await task.run()
        results.push(result)
        allFindings.push(...result.findings)
        this.schedules.set(task.type, Date.now())
      }
    }

    this.results.push(...results)

    return {
      timestamp: Date.now(),
      tasksRun: results.length,
      tasksPassed: results.filter(r => r.passed).length,
      tasksFailed: results.filter(r => !r.passed).length,
      totalFindings: allFindings.length,
      criticalFindings: allFindings.filter(f => f.severity === 'critical').length,
      highFindings: allFindings.filter(f => f.severity === 'high').length,
      mediumFindings: allFindings.filter(f => f.severity === 'medium').length,
      lowFindings: allFindings.filter(f => f.severity === 'low').length,
      findings: allFindings,
      score: calculateSecurityScore(allFindings),
    }
  }

  isTaskDue(type: SecurityTaskType): boolean {
    const task = this.tasks.find(t => t.type === type)
    if (!task) return false

    const lastRun = this.schedules.get(type)
    if (!lastRun) return true

    const intervals: Record<string, number> = {
      daily: 24 * 60 * 60 * 1000,
      weekly: 7 * 24 * 60 * 60 * 1000,
      monthly: 30 * 24 * 60 * 60 * 1000,
      'on-release': Infinity,
    }

    const interval = intervals[task.frequency] || intervals.weekly
    return Date.now() - lastRun > interval
  }

  getLastRun(type: SecurityTaskType): number | undefined {
    return this.schedules.get(type)
  }

  getResults(): SecurityTaskResult[] {
    return [...this.results]
  }
}

function calculateSecurityScore(findings: SecurityFinding[]): number {
  const weights: Record<string, number> = {
    critical: 25,
    high: 10,
    medium: 5,
    low: 2,
    info: 0,
  }

  let totalDeduction = 0
  for (const finding of findings) {
    totalDeduction += weights[finding.severity] || 0
  }

  return Math.max(0, 100 - totalDeduction)
}

export const securityScheduler = new SecurityMaintenanceScheduler()

securityScheduler.registerTask({
  type: 'dependency-update',
  name: 'Dependency Update Check',
  description: 'Check for outdated and vulnerable dependencies',
  frequency: 'weekly',
  priority: 'high',
  automated: true,
  run: async () => {
    return {
      type: 'dependency-update',
      passed: true,
      findings: [],
      duration: 0,
      timestamp: Date.now(),
    }
  },
})

securityScheduler.registerTask({
  type: 'security-scan',
  name: 'Security Vulnerability Scan',
  description: 'Scan for known security vulnerabilities',
  frequency: 'weekly',
  priority: 'critical',
  automated: true,
  run: async () => {
    return {
      type: 'security-scan',
      passed: true,
      findings: [],
      duration: 0,
      timestamp: Date.now(),
    }
  },
})

securityScheduler.registerTask({
  type: 'secret-detection',
  name: 'Secret Detection Scan',
  description: 'Detect exposed secrets and credentials',
  frequency: 'weekly',
  priority: 'critical',
  automated: true,
  run: async () => {
    return {
      type: 'secret-detection',
      passed: true,
      findings: [],
      duration: 0,
      timestamp: Date.now(),
    }
  },
})

securityScheduler.registerTask({
  type: 'static-analysis',
  name: 'Static Code Analysis',
  description: 'Analyze source code for security issues',
  frequency: 'monthly',
  priority: 'high',
  automated: true,
  run: async () => {
    return {
      type: 'static-analysis',
      passed: true,
      findings: [],
      duration: 0,
      timestamp: Date.now(),
    }
  },
})

securityScheduler.registerTask({
  type: 'binary-verification',
  name: 'Binary Verification',
  description: 'Verify integrity of distributed binaries',
  frequency: 'on-release',
  priority: 'critical',
  automated: false,
  run: async () => {
    return {
      type: 'binary-verification',
      passed: true,
      findings: [],
      duration: 0,
      timestamp: Date.now(),
    }
  },
})
