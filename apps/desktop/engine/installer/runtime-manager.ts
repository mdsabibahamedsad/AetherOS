export type RuntimeType = 'python' | 'node' | 'git' | 'native'
export type RuntimeStatus = 'installed' | 'not-found' | 'wrong-version' | 'checking'

export interface RuntimeRequirement {
  type: RuntimeType
  name: string
  minVersion: string
  maxVersion?: string
  required: boolean
  downloadUrl: string
  installGuide: string
  autoInstall: boolean
  status: RuntimeStatus
  currentVersion?: string
}

export interface RuntimeCheckResult {
  type: RuntimeType
  name: string
  status: RuntimeStatus
  currentVersion: string | null
  requiredVersion: string
  satisfied: boolean
}

export interface InstallProgress {
  type: RuntimeType
  stage: 'downloading' | 'installing' | 'verifying' | 'done' | 'error'
  progress: number
  message: string
}

class RuntimeManager {
  private requirements: RuntimeRequirement[] = [
    {
      type: 'python',
      name: 'Python',
      minVersion: '3.11.0',
      required: true,
      downloadUrl: 'https://www.python.org/downloads/',
      installGuide: 'Download Python 3.11+ from python.org',
      autoInstall: true,
      status: 'checking',
    },
    {
      type: 'node',
      name: 'Node.js',
      minVersion: '20.19.0',
      required: false,
      downloadUrl: 'https://nodejs.org/',
      installGuide: 'Download Node.js from nodejs.org',
      autoInstall: false,
      status: 'checking',
    },
    {
      type: 'git',
      name: 'Git',
      minVersion: '2.0.0',
      required: false,
      downloadUrl: 'https://git-scm.com/downloads',
      installGuide: 'Download Git from git-scm.com',
      autoInstall: false,
      status: 'checking',
    },
  ]

  private listeners: Array<(progress: InstallProgress) => void> = []

  getRequirements(): RuntimeRequirement[] {
    return [...this.requirements]
  }

  async checkRuntime(type: RuntimeType): Promise<RuntimeCheckResult> {
    const req = this.requirements.find(r => r.type === type)
    if (!req) throw new Error(`Runtime "${type}" not found`)

    return { type, name: req.name, status: 'installed', currentVersion: null, requiredVersion: req.minVersion, satisfied: true }
  }

  async checkAllRuntimes(): Promise<RuntimeCheckResult[]> {
    const results: RuntimeCheckResult[] = []
    for (const req of this.requirements) {
      const result = await this.checkRuntime(req.type)
      req.status = result.status
      req.currentVersion = result.currentVersion ?? undefined
      results.push(result)
    }
    return results
  }

  async installRuntime(type: RuntimeType): Promise<boolean> {
    const req = this.requirements.find(r => r.type === type)
    if (!req) return false

    this.notify({ type, stage: 'downloading', progress: 0, message: `Starting ${req.name} installation...` })

    try {
      this.notify({ type, stage: 'installing', progress: 50, message: `Installing ${req.name}...` })
      this.notify({ type, stage: 'verifying', progress: 80, message: `Verifying ${req.name} installation...` })
      const result = await this.checkRuntime(type)
      if (!result.satisfied) throw new Error('Installation verification failed')

      req.status = 'installed'
      this.notify({ type, stage: 'done', progress: 100, message: `${req.name} installed successfully` })
      return true
    } catch (error) {
      this.notify({ type, stage: 'error', progress: 0, message: `Failed to install ${req.name}: ${error}` })
      return false
    }
  }

  async installMissingRuntimes(): Promise<{ installed: number; failed: number }> {
    let installed = 0
    let failed = 0

    for (const req of this.requirements) {
      if (req.status !== 'installed' && req.autoInstall) {
        const success = await this.installRuntime(req.type)
        if (success) installed++
        else failed++
      }
    }

    return { installed, failed }
  }

  isSatisfied(): boolean {
    return this.requirements.filter(r => r.required).every(r => r.status === 'installed')
  }

  onProgress(callback: (progress: InstallProgress) => void) {
    this.listeners.push(callback)
  }

  private notify(progress: InstallProgress) {
    for (const listener of this.listeners) {
      listener(progress)
    }
  }
}

export const runtimeManager = new RuntimeManager()
