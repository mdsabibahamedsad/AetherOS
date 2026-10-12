import { useStore } from '@nanostores/react'
import { lazy, Suspense, useEffect, useState } from 'react'

import { $backdropSettings, $radiusScalar } from './backdrop-store'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

const DevLevaPanel = lazy(() => import('./BackdropLeva'))

export function Backdrop() {
  const [controlsOpen, setControlsOpen] = useState(false)
  const settings = useStore($backdropSettings)
  const radiusScalar = useStore($radiusScalar)

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return
    }

    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null

      const editing =
        target?.isContentEditable ||
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement

      if (editing || event.repeat || event.altKey || event.ctrlKey || event.metaKey) {
        return
      }

      if (event.shiftKey && event.code === 'KeyY') {
        setControlsOpen(open => !open)
      }
    }

    window.addEventListener('keydown', onKeyDown)

    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    document.documentElement.style.setProperty('--radius-scalar', String(radiusScalar))
  }, [radiusScalar])

  return (
    <>
      {import.meta.env.DEV && (
        <Suspense fallback={null}>
          {controlsOpen && <DevLevaPanel />}
        </Suspense>
      )}

      {settings.enabled && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-2"
          style={{
            mixBlendMode: settings.blendMode as React.CSSProperties['mixBlendMode'],
            opacity: settings.opacity,
          }}
        >
          <img
            alt=""
            className="w-auto min-w-dvw object-cover"
            fetchPriority="low"
            src={assetPath('ds-assets/filler-bg0.jpg')}
            style={{
              height: `${settings.scale}dvh`,
              objectPosition: settings.objectPosition,
              filter: `invert(calc(${settings.invert ? 1 : 0} * var(--backdrop-invert-mul, 1))) saturate(${settings.saturate}) brightness(${settings.brightness})`,
            }}
          />
        </div>
      )}
    </>
  )
}
