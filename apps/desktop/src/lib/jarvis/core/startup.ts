import { startAutonomy, stopAutonomy } from './autonomy'
import { checkHealth, connectToBackend } from './backend-bridge'
import { startEngine, stopEngine } from './engine'
import { seedCoreMemory } from './memory'
import { notify } from './notifications'
import { startObserver, stopObserver } from './observer'
import { seedDefaultJobs, startScheduler, stopScheduler } from './scheduler'
import { loadBuiltinSkills } from './skills'

let initialized = false
let useBackend = false

export async function initializeJarvisEngine(): Promise<void> {
  if (initialized) {return}

  console.log('[Jarvis] Initializing engine...')

  const health = await checkHealth()

  if (health && health.status === 'healthy') {
    useBackend = true
    console.log('[Jarvis] Connected to Python backend')
    const connected = await connectToBackend()

    if (connected) {
      initialized = true
      notify('Jarvis Engine', 'Connected to AI Engine backend', 'success', 'system')

      return
    }
  }

  console.log('[Jarvis] Backend not available, using local simulation')

  try {
    seedCoreMemory()
    console.log('[Jarvis] Core memory seeded')
  } catch (e) {
    console.error('[Jarvis] Memory seed failed:', e)
  }

  try {
    loadBuiltinSkills()
    console.log('[Jarvis] Built-in skills loaded')
  } catch (e) {
    console.error('[Jarvis] Skills load failed:', e)
  }

  try {
    seedDefaultJobs()
    startScheduler()
    console.log('[Jarvis] Scheduler started')
  } catch (e) {
    console.error('[Jarvis] Scheduler failed:', e)
  }

  try {
    startObserver()
    console.log('[Jarvis] Observer started')
  } catch (e) {
    console.error('[Jarvis] Observer failed:', e)
  }

  try {
    startAutonomy()
    console.log('[Jarvis] Autonomy started')
  } catch (e) {
    console.error('[Jarvis] Autonomy failed:', e)
  }

  try {
    startEngine()
    console.log('[Jarvis] Engine started')
  } catch (e) {
    console.error('[Jarvis] Engine failed:', e)
  }

  initialized = true
  notify('Jarvis Engine', 'AI Operating System initialized successfully', 'success', 'system')
}

export async function shutdownJarvisEngine(): Promise<void> {
  if (!initialized) {return}

  stopEngine()
  stopAutonomy()
  stopScheduler()
  stopObserver()

  initialized = false
  console.log('[Jarvis] Engine shutdown complete')
}

export function isEngineInitialized(): boolean {
  return initialized
}
