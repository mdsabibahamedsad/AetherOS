import { Leva, useControls } from 'leva'
import { useEffect } from 'react'

import { $backdropSettings, $radiusScalar } from './backdrop-store'

const BLEND_MODES = [
  'normal', 'multiply', 'screen', 'overlay', 'darken', 'lighten',
  'color-dodge', 'color-burn', 'hard-light', 'soft-light', 'difference',
  'exclusion', 'hue', 'saturation', 'color', 'luminosity',
] as const

type BlendMode = (typeof BLEND_MODES)[number]

export default function BackdropLeva() {
  const shape = useControls(
    'UI / Shape',
    { radiusScalar: { value: 0.2, min: 0, max: 2, step: 0.1, label: 'radius scalar' } },
    { collapsed: true },
  )

  const statue = useControls(
    'Backdrop / Statue',
    {
      enabled: { value: true, label: 'on' },
      opacity: { value: 0.025, min: 0, max: 1, step: 0.005 },
      blendMode: { value: 'difference' as BlendMode, options: [...BLEND_MODES], label: 'blend' },
      invert: { value: true, label: 'invert color' },
      saturate: { value: 1, min: 0, max: 3, step: 0.05, label: 'saturate' },
      brightness: { value: 1, min: 0, max: 2, step: 0.05, label: 'brightness' },
      objectPosition: {
        value: 'top left',
        options: ['top left', 'top right', 'bottom left', 'bottom right', 'center', 'top', 'bottom', 'left', 'right'],
        label: 'position',
      },
      scale: { value: 160, min: 100, max: 300, step: 5, label: 'height (dvh)' },
    },
    { collapsed: true },
  )

  useEffect(() => {
    $radiusScalar.set(shape.radiusScalar)
  }, [shape.radiusScalar])

  useEffect(() => {
    $backdropSettings.set({
      enabled: statue.enabled,
      opacity: statue.opacity,
      blendMode: statue.blendMode,
      invert: statue.invert,
      saturate: statue.saturate,
      brightness: statue.brightness,
      objectPosition: statue.objectPosition,
      scale: statue.scale,
    })
  }, [statue])

  return <Leva collapsed hidden titleBar={{ title: 'backdrop', drag: true }} />
}
