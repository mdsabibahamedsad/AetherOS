import { useStore } from '@nanostores/react'
import { useEffect } from 'react'
import { $route, $bootstrap, initialize } from './store'
import Welcome from './routes/welcome'
import SystemCheck from './routes/system-check'
import Location from './routes/location'
import Components from './routes/components'
import Runtimes from './routes/runtimes'
import Progress from './routes/progress'
import Success from './routes/success'
import Failure from './routes/failure'
import Complete from './routes/complete'
import About from './routes/about'
import Connectors from './routes/connectors'

/*
 * App shell — Aetheros Setup.
 *
 * No header chrome (the OS title bar already says "Aetheros Setup"; an
 * in-window repeat of the H mark + words was redundant slop).
 *
 * Route state lives in a single $route atom — 4 screens, no react-router.
 */
export default function App() {
  const route = useStore($route)
  const bootstrap = useStore($bootstrap)

  useEffect(() => {
    void initialize()
  }, [])

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-background text-foreground">
      <main className="relative z-10 flex flex-1 flex-col overflow-hidden">
        {route === 'welcome' && <Welcome />}
        {route === 'system-check' && <SystemCheck />}
        {route === 'location' && <Location />}
        {route === 'components' && <Components />}
        {route === 'runtimes' && <Runtimes />}
        {route === 'progress' && <Progress bootstrap={bootstrap} />}
        {route === 'success' && <Success />}
        {route === 'failure' && <Failure bootstrap={bootstrap} />}
        {route === 'complete' && <Complete />}
        {route === 'about' && <About />}
        {route === 'connectors' && <Connectors />}
      </main>
    </div>
  )
}
