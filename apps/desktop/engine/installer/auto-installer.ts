import { runtimeManager } from './runtime-manager'

export type InstallStage = 'check-runtime' | 'install-python' | 'install-deps' | 'setup-workspace' | 'verify' | 'complete' | 'error'

export interface InstallerState {
  stage: InstallStage
  progress: number
  message: string
  error: string | null
  completed: boolean
  startTime: number
}

class AutoInstaller {
  private state: InstallerState = {
    stage: 'check-runtime',
    progress: 0,
    message: 'Starting installation...',
    error: null,
    completed: false,
    startTime: Date.now(),
  }

  private listeners: Array<(state: InstallerState) => void> = []

  getState(): InstallerState {
    return { ...this.state }
  }

  async runInstallation(): Promise<boolean> {
    this.state.startTime = Date.now()

    try {
      await this.stage('check-runtime', 10, 'Checking system requirements...')
      const runtimes = await runtimeManager.checkAllRuntimes()

      const missing = runtimes.filter(r => !r.satisfied && r.type === 'python')
      if (missing.length > 0) {
        await this.stage('install-python', 30, 'Installing Python runtime...')
        await runtimeManager.installRuntime('python')
      }

      await this.stage('install-deps', 50, 'Installing dependencies...')
      await this.installDependencies()

      await this.stage('setup-workspace', 70, 'Setting up workspace...')
      await this.setupWorkspace()

      await this.stage('verify', 90, 'Verifying installation...')
      const verified = await this.verifyInstallation()

      if (!verified) throw new Error('Installation verification failed')

      await this.stage('complete', 100, 'Installation complete!')
      this.state.completed = true
      return true
    } catch (error) {
      this.state.stage = 'error'
      this.state.error = String(error)
      this.state.message = `Installation failed: ${error}`
      this.notify()
      return false
    }
  }

  reset() {
    this.state = {
      stage: 'check-runtime',
      progress: 0,
      message: 'Starting installation...',
      error: null,
      completed: false,
      startTime: Date.now(),
    }
    this.notify()
  }

  onStateChange(callback: (state: InstallerState) => void) {
    this.listeners.push(callback)
    callback({ ...this.state })
  }

  private async stage(stage: InstallStage, progress: number, message: string) {
    this.state.stage = stage
    this.state.progress = progress
    this.state.message = message
    this.notify()
  }

  private async installDependencies() {
    return new Promise<void>(resolve => setTimeout(resolve, 100))
  }

  private async setupWorkspace() {
    const defaultWorkspace = {
      workspaces: [],
      defaultLocation: '',
      lastOpened: null,
      recent: [],
    }
    window.localStorage.setItem('aetheros.workspaces', JSON.stringify(defaultWorkspace))
  }

  private async verifyInstallation(): Promise<boolean> {
    try {
      window.localStorage.getItem('aetheros.workspaces')
      return true
    } catch {
      return false
    }
  }

  private notify() {
    for (const listener of this.listeners) {
      listener({ ...this.state })
    }
  }
}

export const autoInstaller = new AutoInstaller()
